"""Run exactly the caller's argv once and capture bounded output. No model execution."""

import json
import os
import queue
import re
import selectors
import signal
import subprocess
import threading
import time

_POSIX = os.name == "posix"


def _popen(argv, cwd):
    """Start the collector in its own session/process group so the whole tree can be killed."""
    extra = (
        {"start_new_session": True}
        if _POSIX
        else {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    )
    return subprocess.Popen(
        argv,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        **extra,
    )


def _kill_tree(proc):
    """Kill the command's whole process tree, including pipe-holding children."""
    if _POSIX:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        return
    if proc.poll() is not None:
        return
    # taskkill /T is the Windows equivalent of killing the process group; proc.kill() alone
    # would leave grandchildren holding the pipes open.
    subprocess.run(
        ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    try:
        proc.kill()
    except OSError:
        pass


def _chunks_posix(proc, remaining):
    with selectors.DefaultSelector() as selector:
        selector.register(proc.stdout, selectors.EVENT_READ, "stdout")
        selector.register(proc.stderr, selectors.EVENT_READ, "stderr")
        while selector.get_map():
            left = remaining()
            if left <= 0:
                yield "timeout", None
                return
            for key, _ in selector.select(min(left, 0.1)):
                block = os.read(key.fileobj.fileno(), 65536)
                if not block:
                    selector.unregister(key.fileobj)
                    continue
                yield key.data, block


def _chunks_threads(proc, remaining):
    # select() only works on sockets on Windows, so pipes are drained by reader threads.
    pending = queue.Queue()

    def pump(stream, name):
        try:
            while True:
                block = os.read(stream.fileno(), 65536)
                if not block:
                    break
                pending.put((name, block))
        except OSError:
            pass
        finally:
            pending.put((name, None))

    for stream, name in ((proc.stdout, "stdout"), (proc.stderr, "stderr")):
        threading.Thread(target=pump, args=(stream, name), daemon=True).start()
    open_streams = 2
    while open_streams:
        left = remaining()
        if left <= 0:
            yield "timeout", None
            return
        try:
            name, block = pending.get(timeout=min(left, 0.1))
        except queue.Empty:
            continue
        if block is None:
            open_streams -= 1
            continue
        yield name, block


_chunks = _chunks_posix if _POSIX else _chunks_threads


def collect_command(
    argv, cwd=None, timeout=30, max_bytes=2_000_000, split="lines", accept_exit=(0,)
):
    if not argv or not all(isinstance(s, str) for s in argv):
        raise ValueError("exec requires command argv after --")
    if (
        timeout <= 0
        or max_bytes < 1
        or split not in ("auto", "paragraphs", "lines", "whole", "json")
    ):
        raise ValueError("Invalid command limits or split mode")
    started = time.perf_counter()
    proc = _popen(argv, cwd)
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    total, stop_reason = 0, None

    def remaining():
        return timeout - (time.perf_counter() - started)

    try:
        for name, block in _chunks(proc, remaining):
            if name == "timeout":
                stop_reason = "timeout"
                break
            take = min(len(block), max_bytes - total)
            buffers[name].extend(block[:take])
            total += take
            if take < len(block):
                stop_reason = "output_limit"
                break
        if not stop_reason:
            try:
                proc.wait(timeout=max(0.001, remaining()))
            except subprocess.TimeoutExpired:
                stop_reason = "timeout"
    except BaseException:
        _kill_tree(proc)
        raise
    finally:
        # Kill this command's process tree on timeout/overflow, including pipe-holding children.
        if stop_reason or proc.poll() is None:
            _kill_tree(proc)
        proc.wait()
        proc.stdout.close()
        proc.stderr.close()
    stdout, stderr = (
        bytes(buffers[k]).decode("utf-8", errors="replace") for k in ("stdout", "stderr")
    )
    meta = {
        "argv": argv,
        "cwd": os.path.abspath(cwd or os.curdir),
        "exit_code": proc.returncode,
        "ok": stop_reason is None and proc.returncode in accept_exit,
        "stop_reason": stop_reason,
        "elapsed_ms": round((time.perf_counter() - started) * 1000),
        "stderr": stderr,
        "captured_bytes": total,
        "truncated": stop_reason is not None,
        "scope": "stdout of one caller-supplied command; stderr is retained separately",
    }
    if split == "auto":
        try:
            parsed = json.loads(stdout)
            candidate = parsed.get("records") if isinstance(parsed, dict) else parsed
            split = (
                "json"
                if isinstance(candidate, list)
                and all(isinstance(r, dict) and isinstance(r.get("text"), str) for r in candidate)
                else "paragraphs"
            )
        except json.JSONDecodeError:
            split = "paragraphs"
    meta["split"] = split
    if split == "json" and meta["ok"]:
        try:
            records = json.loads(stdout)
            candidate = records.get("records") if isinstance(records, dict) else records
            if not isinstance(candidate, list) or any(
                not isinstance(r, dict) or not isinstance(r.get("text"), str) for r in candidate
            ):
                meta["ok"] = False
                meta["parse_error"] = "stdout JSON must contain records with text fields"
                records = [{"id": "stdout", "text": stdout, "truncated": False}]
        except json.JSONDecodeError:
            meta["ok"] = False
            meta["parse_error"] = "stdout is not valid JSON"
            records = [{"id": "stdout", "text": stdout, "truncated": True}]
    elif split == "paragraphs":
        paragraphs = re.findall(r".*?(?:\n[ \t]*\n|$)", stdout, re.S)
        records = [
            {"id": f"block-{i}", "text": text, "truncated": meta["truncated"]}
            for i, text in enumerate((t for t in paragraphs if t), 1)
        ]
    elif split == "whole" or split == "json":
        records = [{"id": "stdout", "text": stdout, "truncated": meta["truncated"]}]
    else:
        records = [
            {"id": f"line-{i}", "line": i, "text": line, "truncated": meta["truncated"]}
            for i, line in enumerate(stdout.splitlines(keepends=True), 1)
        ]
    return records, meta
