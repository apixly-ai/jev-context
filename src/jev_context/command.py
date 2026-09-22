"""Run exactly the caller's argv once and capture bounded output. No model execution."""

import json
import os
import re
import selectors
import signal
import subprocess
import time


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
    proc = subprocess.Popen(
        argv,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    total, stop_reason = 0, None
    with selectors.DefaultSelector() as selector:
        selector.register(proc.stdout, selectors.EVENT_READ, "stdout")
        selector.register(proc.stderr, selectors.EVENT_READ, "stderr")
        try:
            while selector.get_map():
                remaining = timeout - (time.perf_counter() - started)
                if remaining <= 0:
                    stop_reason = "timeout"
                    break
                for key, _ in selector.select(min(remaining, 0.1)):
                    block = os.read(key.fileobj.fileno(), 65536)
                    if not block:
                        selector.unregister(key.fileobj)
                        continue
                    take = min(len(block), max_bytes - total)
                    buffers[key.data].extend(block[:take])
                    total += take
                    if take < len(block):
                        stop_reason = "output_limit"
                        break
                if stop_reason:
                    break
            if not stop_reason:
                try:
                    proc.wait(timeout=max(0.001, timeout - (time.perf_counter() - started)))
                except subprocess.TimeoutExpired:
                    stop_reason = "timeout"
        except BaseException:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            raise
        finally:
            # Kill this command's process group on timeout/overflow, including pipe-holding children.
            if stop_reason or proc.poll() is None:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
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
