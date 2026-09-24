"""Opt-in local numeric telemetry. Never store source text or infer invoice savings."""

import argparse
import json
import math
import os
import sqlite3
import sys
import tempfile
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

import httpx


def directory():
    return Path(
        os.environ.get("JEV_STATS_DIR", Path.home() / ".local/share/jev-filter/stats")
    ).expanduser()


def stamp():
    return datetime.now(timezone.utc).isoformat()


def configure(
    model,
    counter,
    input_rate,
    jev_input_rate,
    jev_output_rate,
    *,
    encoding=None,
    price_source="user-supplied",
    price_date=None,
):
    if (
        not model.strip()
        or len(model) > 160
        or counter not in ("bytes", "tiktoken", "openai", "anthropic")
    ):
        raise ValueError("Specify a model and a supported counter")
    for rate in (input_rate, jev_input_rate, jev_output_rate):
        if rate is not None and (not math.isfinite(rate) or rate < 0):
            raise ValueError("Rates must be finite nonnegative USD per million tokens")
    if counter == "tiktoken":
        import tiktoken

        # No guessed model mapping; an explicit encoding is labeled as an encoding estimate.
        (tiktoken.get_encoding(encoding) if encoding else tiktoken.encoding_for_model(model))
    date = price_date or datetime.now(timezone.utc).date().isoformat()
    datetime.strptime(date, "%Y-%m-%d")
    config = dict(
        model=model,
        counter=counter,
        encoding=encoding,
        input_rate=input_rate,
        jev_input_rate=jev_input_rate,
        jev_output_rate=jev_output_rate,
        price_source=price_source,
        price_date=date,
        configured_at=stamp(),
    )
    root = directory()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(dir=root)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            json.dump(config, out)
        os.replace(name, root / "config.json")
    finally:
        if Path(name).exists():
            Path(name).unlink()
    return config


def count_pair(before, after, config):
    mode = config["counter"]
    if mode == "bytes":
        return (
            math.ceil(len(before.encode()) / 4),
            math.ceil(len(after.encode()) / 4),
            "utf8_bytes_div_4_estimate",
        )
    if mode == "tiktoken":
        import tiktoken

        enc = (
            tiktoken.get_encoding(config["encoding"])
            if config.get("encoding")
            else tiktoken.encoding_for_model(config["model"])
        )
        return (
            len(enc.encode(before, disallowed_special=())),
            len(enc.encode(after, disallowed_special=())),
            "tiktoken:"
            + enc.name
            + (":explicit_encoding_proxy" if config.get("encoding") else ":model_text_estimate"),
        )
    provider = "OPENAI" if mode == "openai" else "ANTHROPIC"
    key = os.environ.get(provider + "_API_KEY")
    if not key:
        raise ValueError("Counting API credential missing")
    if mode == "openai":
        url = "https://api.openai.com/v1/responses/input_tokens"
        headers = {"Authorization": "Bearer " + key}

        def body(text):
            return {"model": config["model"], "input": text}
    else:
        url = "https://api.anthropic.com/v1/messages/count_tokens"
        headers = {"x-api-key": key, "anthropic-version": "2023-06-01"}

        def body(text):
            return {"model": config["model"], "messages": [{"role": "user", "content": text}]}

    counts = []
    # Explicit opt-in at configure. No redirects, automatic retry, or content in errors.
    with httpx.Client(timeout=10, follow_redirects=False) as client:
        for text in (before, after):
            response = client.post(url, headers=headers, json=body(text))
            response.raise_for_status()
            value = response.json()["input_tokens"]
            if type(value) is not int or value < 0:
                raise ValueError("Invalid count")
            counts.append(value)
    return *counts, mode + ":isolated_message_count"


def connect():
    root = directory()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = root / "usage.sqlite3"
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    os.close(fd)
    conn = sqlite3.connect(path, timeout=10)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, time TEXT NOT NULL, model TEXT NOT NULL, payload TEXT NOT NULL)"
    )
    return conn


def record(tool, before, after, result, *, comparable=True):
    """Best effort; a telemetry failure must not repeat or fail a caller operation."""
    if os.environ.get("JEV_STATS_DISABLED") == "1":
        return None
    path = directory() / "config.json"
    if not path.exists():
        return None
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
        telemetry = result.get("telemetry", result)
        usage = telemetry.get("usage") or {}
        complete = result.get("ok", False) and result.get("complete", comparable)
        status = (
            "passthrough"
            if result.get("mode") == "passthrough"
            else "complete"
            if complete
            else "incomplete"
        )
        if not comparable:
            status = "uncompared"
        eligible = status == "complete" and comparable and before is not None
        b = a = None
        error = None
        method = "not_counted"
        if before is not None:
            try:
                b, a, method = count_pair(before, after, config)
            except Exception as exc:
                error = type(exc).__name__
        delta = b - a if eligible and b is not None else None
        known_usage = telemetry.get("usage_complete") is True and all(
            type(usage.get(k)) is int and usage[k] >= 0 for k in ("input_tokens", "output_tokens")
        )
        ji = usage.get("input_tokens") if type(usage.get("input_tokens")) is int else None
        jo = usage.get("output_tokens") if type(usage.get("output_tokens")) is int else None
        cost = (
            (ji * config["jev_input_rate"] + jo * config["jev_output_rate"]) / 1e6
            if known_usage
            and config["jev_input_rate"] is not None
            and config["jev_output_rate"] is not None
            else None
        )
        gross = (
            delta * config["input_rate"] / 1e6
            if delta is not None and config["input_rate"] is not None
            else None
        )
        row = dict(
            id=uuid.uuid4().hex,
            time=stamp(),
            model=config["model"],
            tool=tool,
            status=status,
            method=method,
            count_error=error,
            before_bytes=len(before.encode()) if before is not None else None,
            after_bytes=len(after.encode()),
            before_tokens=b,
            after_tokens=a,
            saved_tokens=delta,
            gross_usd=gross,
            jev_usd=cost,
            net_usd=gross - cost if gross is not None and cost is not None else None,
            jev_input_tokens=ji,
            jev_output_tokens=jo,
            usage_complete=known_usage,
            input_rate=config["input_rate"],
            jev_input_rate=config["jev_input_rate"],
            jev_output_rate=config["jev_output_rate"],
            price_source=config["price_source"],
            price_date=config["price_date"],
            elapsed_ms=result.get("elapsed_ms"),
            package_version=__import__("jev_context").__version__,
            basis="normalized_collection_json_vs_full_rendered_packet_once",
        )
        with closing(connect()) as conn, conn:
            conn.execute(
                "INSERT INTO events VALUES (?,?,?,?)",
                (row["id"], row["time"], row["model"], json.dumps(row)),
            )
        return row["id"]
    except Exception as exc:
        print(json.dumps({"stats_warning": type(exc).__name__, "recorded": False}), file=sys.stderr)
        return None


def summarize(rows):
    def total(key):
        vals = [r[key] for r in rows if r.get(key) is not None]
        return sum(vals) if vals else None

    return dict(
        runs=len(rows),
        comparable_runs=sum(r["saved_tokens"] is not None for r in rows),
        incomplete_runs=sum(r["status"] == "incomplete" for r in rows),
        unpriced_runs=sum(r["jev_usd"] is None for r in rows),
        saved_tokens=total("saved_tokens"),
        gross_usd=total("gross_usd"),
        jev_usd=total("jev_usd"),
        known_net_usd=total("net_usd"),
        net_usd=total("net_usd") if rows and all(r["net_usd"] is not None for r in rows) else None,
    )


def report(model=None, since=None, until=None):
    for value in (since, until):
        if value:
            datetime.strptime(value, "%Y-%m-%d")
    if since and until and since > until:
        raise ValueError("since must not follow until")
    rows = []
    if (directory() / "usage.sqlite3").exists():
        with closing(connect()) as conn, conn:
            rows = [
                json.loads(r[0])
                for r in conn.execute("SELECT payload FROM events ORDER BY time DESC")
            ]
    rows = [
        r
        for r in rows
        if (not model or r["model"] == model)
        and (not since or r["time"][:10] >= since)
        and (not until or r["time"][:10] <= until)
    ]
    return dict(
        schema_version=1,
        generated_at=stamp(),
        summary=summarize(rows),
        events=rows,
        scope="Local recorded calls only; UTC dates. Input-equivalent estimate, not invoice savings.",
        baseline="Normalized collected records versus full returned packet, once; not a whole-agent counterfactual.",
    )


def port_number(value):
    try:
        port = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("port must be an integer from 0 to 65535") from None
    if not 0 <= port <= 65535:
        raise argparse.ArgumentTypeError("port must be an integer from 0 to 65535")
    return port


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    cfg = sub.add_parser("configure", help="Enable recording; rates are USD per million tokens")
    cfg.add_argument("--model", required=True)
    cfg.add_argument(
        "--counter", choices=["bytes", "tiktoken", "openai", "anthropic"], default="bytes"
    )
    cfg.add_argument("--encoding")
    cfg.add_argument("--input-rate", type=float)
    cfg.add_argument("--jev-input-rate", type=float)
    cfg.add_argument("--jev-output-rate", type=float)
    cfg.add_argument("--price-source", default="user-supplied")
    cfg.add_argument("--price-date")
    for name in ("report", "dashboard"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--model")
        cmd.add_argument("--since")
        cmd.add_argument("--until")
        if name == "dashboard":
            cmd.add_argument(
                "--no-open", action="store_true", help="Print the URL without opening a browser"
            )
            cmd.add_argument(
                "--port",
                type=port_number,
                help="Explicit port (0 chooses an available port); default tries 8765 then an available port",
            )
            cmd.add_argument("--html", help="Export a self-contained snapshot instead of serving")
    sub.add_parser("disable", help="Disable recording; retain existing statistics")
    args = parser.parse_args(argv)
    if args.action == "configure":
        values = vars(args).copy()
        values.pop("action")
        print(json.dumps(configure(**values)))
    elif args.action == "disable":
        (directory() / "config.json").unlink(missing_ok=True)
        print(json.dumps({"recording": False}))
    elif args.action == "report":
        print(json.dumps(report(args.model, args.since, args.until), ensure_ascii=False, indent=2))
    else:
        from .dashboard import page, serve

        data = report(args.model, args.since, args.until)
        if args.html:
            fd = os.open(Path(args.html).expanduser(), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as out:
                out.write(page(data))
            print(json.dumps({"html": str(Path(args.html).resolve())}))
        else:
            return serve(
                args.port, args.model, args.since, args.until, open_browser=not args.no_open
            )
    return 0
