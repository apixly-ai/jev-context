"""Configurable independent inference concurrency over the installed pooled transport."""

import concurrent.futures
import time

try:
    import resource
except ImportError:  # Windows has no descriptor soft limit to consult.
    resource = None


def worker_count(requests, requested="auto"):
    if not requests:
        return 0
    if requested == "auto":
        capacity = requests
        if resource is not None:
            soft, _ = resource.getrlimit(resource.RLIMIT_NOFILE)
            # Reserve descriptors for the host process; an OS-resource bound, not a model limit.
            if soft != resource.RLIM_INFINITY:
                capacity = max(1, (soft - 32) // 4)
        return min(requests, capacity, 30)
    if isinstance(requested, str):
        requested = int(requested)
    if type(requested) is not int or not 1 <= requested <= 30:
        raise ValueError("workers must be auto or 1..30")
    return min(requests, requested)


def run(items, workers="auto", cache=None):
    if cache is not None:
        raise ValueError("This CLI does not support inference caching")
    from .provider import Client, evaluate

    started = time.perf_counter()
    effective = worker_count(len(items), workers)
    with Client(pooled=True) as client:

        def one(item):
            try:
                return {"id": item["id"], **evaluate(item["request"], client, cache=None)}
            except Exception as exc:
                return {
                    "id": item["id"],
                    "ok": False,
                    "error_type": type(exc).__name__,
                    "usage_complete": False,
                }

        with concurrent.futures.ThreadPoolExecutor(max_workers=effective) as pool:
            results = list(pool.map(one, items))
        transport = dict(client.stats)
    return {
        "ok": all(r["ok"] for r in results),
        "results": results,
        "elapsed_ms": round((time.perf_counter() - started) * 1000),
        "usage": {
            k: sum(r.get("usage", {}).get(k, 0) for r in results)
            for k in ("input_tokens", "output_tokens")
        },
        "usage_complete": all(r["ok"] and r.get("usage_complete", False) for r in results),
        "cache_hit_questions": 0,
        "network_questions": sum(r.get("network_questions", 0) for r in results),
        "transport": transport,
        "workers": effective,
        "failed_requests": sum(not r["ok"] for r in results),
        # With cache disabled, each success accounts for exactly one returned usage envelope.
        # All other physical attempts (including retries on a failed request) lack usage.
        "unknown_usage_attempts": max(0, transport["requests"] - sum(r["ok"] for r in results)),
    }
