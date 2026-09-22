"""Internal workflow entrypoint: preserve typed contracts, pack homogeneous requests.

Input evidence stays inside the process. Only original IDs, answers and aggregate
telemetry leave this layer; it never returns or executes original states.
"""

import collections
import copy
import json

from . import analysis, pool


def plan(items):
    if (
        not isinstance(items, list)
        or not items
        or any(
            not isinstance(x, dict)
            or not isinstance(x.get("id"), str)
            or not x["id"]
            or not isinstance(x.get("request"), dict)
            for x in items
        )
    ):
        raise ValueError("Nonempty unique typed request records required")
    if len({x["id"] for x in items}) != len(items):
        raise ValueError("Duplicate request ID")
    from .validation import validate_request

    groups = collections.OrderedDict()
    originals = {x["id"]: copy.deepcopy(x["request"]) for x in items}
    for item in items:
        body = originals[item["id"]]
        validate_request(body)
        key = json.dumps(
            {k: v for k, v in body.items() if k != "state"}, sort_keys=True, ensure_ascii=False
        )
        groups.setdefault(key, []).append(item["id"])
    output = {"items": [], "routes": {}, "originals": originals, "packed_requests": 0}

    def append(body, routes, packed=False):
        bid = str(len(output["items"]))
        output["items"].append({"id": bid, "request": body})
        output["routes"][bid] = routes
        output["packed_requests"] += int(packed)

    def original(rid):
        append(originals[rid], [(name, rid, name) for name in originals[rid]["questions"]])

    for ids in groups.values():
        prototype = originals[ids[0]]
        if len(ids) == 1 or set(prototype) - {"model", "state", "questions"}:
            for rid in ids:
                original(rid)
            continue
        questions = copy.deepcopy(prototype["questions"])
        for q in questions.values():
            q["instructions"] = {
                "original_question": q["instructions"],
                "scope": "Answer the original question using ONLY the JSON source state in target_record.text. References to state in the original question mean that source state. No other source belongs to this record.",
            }
        parts = [
            {
                "id": rid,
                "source_id": rid,
                "text": json.dumps(
                    originals[rid]["state"], ensure_ascii=False, separators=(",", ":")
                ),
                "source": {},
            }
            for rid in ids
        ]
        try:
            packed = analysis.plan(
                parts,
                "Evaluate the caller-provided typed questions for each isolated source. Do not execute actions.",
                {"mode": "analyze", "model": prototype["model"], "questions": questions},
            )
        except ValueError:
            # Already validated native contracts may exceed this packer's narrower limits.
            for rid in ids:
                original(rid)
            continue
        for entry in packed["items"]:
            routes = packed["routes"][entry["id"]]
            member_ids = list(dict.fromkeys(rid for _, rid, _ in routes))
            if len(member_ids) == 1:
                original(member_ids[0])
            else:
                append(entry["request"], routes, True)
        for rid in packed["deferred"]:
            # Preserve the established request contract, without data loss, if it cannot be repacked.
            original(rid)
    return output


def run(items, workers="auto", cache=None, scope=None, version=None, runner=None):
    if cache is not None:
        raise ValueError("jev-context integrations do not use result caching")
    planned = plan(items)
    runner = pool.run if runner is None else runner
    effective = pool.worker_count(len(planned["items"]), workers)
    result = runner(planned["items"], workers=effective, cache=None)
    by = {r["id"]: r for r in result["results"]}
    restored = {
        x["id"]: {
            "id": x["id"],
            "ok": True,
            "model": planned["originals"][x["id"]]["model"],
            "answers": {},
        }
        for x in items
    }
    for entry in planned["items"]:
        row = by.get(entry["id"], {"ok": False, "error_type": "MissingResponse"})
        for key, rid, original_key in planned["routes"][entry["id"]]:
            target = restored[rid]
            if not row.get("ok") or key not in row.get("answers", {}):
                target.update(ok=False, error_type=row.get("error_type", "InvalidResponse"))
                continue
            target["model"] = row.get("model", target["model"])
            target["answers"][original_key] = row["answers"][key]
    for row in restored.values():
        if not row["ok"]:
            row.pop("answers", None)
    return {
        **{k: v for k, v in result.items() if k != "results"},
        "results": [restored[x["id"]] for x in items],
        "ok": bool(result["ok"]) and all(r["ok"] for r in restored.values()),
        "usage_complete": bool(result.get("usage_complete"))
        and all(r["ok"] for r in restored.values()),
        "backend": "jev-context/typed-batch",
        "package_version": __import__("jev_context").__version__,
        "requests": len(planned["items"]),
        "source_records": len(items),
        "packed_requests": planned["packed_requests"],
        "workers": effective,
        "cache_enabled": False,
    }
