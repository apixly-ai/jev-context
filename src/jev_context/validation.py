"""Strict JSON request/response boundaries for TypeSafe's typed primitives."""

import json
import math
from typing import Any


def number(value: Any, low: float = 0, high: float = 1) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and low <= value <= high


def validate_request(body: dict[str, Any]) -> None:
    if not isinstance(body, dict) or not isinstance(body.get("state"), (str, dict, list)):
        raise ValueError("state must be text, an object or an array")
    json.dumps(body, allow_nan=False)
    if not isinstance(body.get("model"), str) or not body["model"]:
        raise ValueError("model must be a nonempty string")
    qs = body.get("questions")
    if not isinstance(qs, dict) or not qs:
        raise ValueError("questions must be a nonempty object")
    for name, q in qs.items():
        if not isinstance(name, str) or not name or not isinstance(q, dict):
            raise ValueError("invalid question")
        if q.get("type") not in ("choice", "noul", "score") or not isinstance(
            q.get("instructions"), (str, dict, list)
        ):
            raise ValueError("invalid question type/instructions")
        criteria = q.get("criteria")
        if q["type"] == "choice" and (
            not isinstance(criteria, dict)
            or not 1 <= len(criteria) <= 255
            or any(not isinstance(k, str) or not k for k in criteria)
        ):
            raise ValueError("Choice requires 1..255 named options")
        if q["type"] == "score" and (
            not isinstance(criteria, list) or not 2 <= len(criteria) <= 10
        ):
            raise ValueError("Score requires 2..10 levels")
        if (
            q["type"] == "noul"
            and criteria is not None
            and (not isinstance(criteria, dict) or set(criteria) - {"true", "false"})
        ):
            raise ValueError("Noul criteria may contain true/false only")


def validate_response(body: dict[str, Any], result: dict[str, Any]) -> None:
    if not isinstance(result, dict) or not isinstance(result.get("model"), str):
        raise ValueError("invalid response")
    answers = result.get("answers")
    if not isinstance(answers, dict) or set(answers) != set(body["questions"]):
        raise ValueError("question IDs do not match")
    for qid, q in body["questions"].items():
        a = answers[qid]
        if not isinstance(a, dict) or a.get("type") != q["type"]:
            raise ValueError("answer type mismatch")
        if q["type"] == "noul":
            if not number(a.get("noul")):
                raise ValueError("invalid Noul probability")
            continue
        keys = (
            set(q["criteria"])
            if q["type"] == "choice"
            else {str(i) for i in range(len(q["criteria"]))}
        )
        distribution = a.get("probabilities")
        if (
            not isinstance(distribution, dict)
            or set(distribution) != keys
            or not all(number(v) for v in distribution.values())
            or abs(sum(distribution.values()) - 1) > 0.03
            or not number(a.get("confidence"))
        ):
            raise ValueError("invalid answer distribution")
        if q["type"] == "choice":
            choice = a.get("choice")
            if choice not in keys or distribution[choice] < max(distribution.values()) - 1e-6:
                raise ValueError("invalid selected option")
        else:
            if (
                not number(a.get("score"), 0, len(keys) - 1)
                or not isinstance(a.get("legend"), dict)
                or set(a["legend"]) != keys
            ):
                raise ValueError("invalid score")
    usage = result.get("usage")
    if not isinstance(usage, dict) or any(
        type(usage.get(k)) is not int or usage[k] < 0 for k in ("input_tokens", "output_tokens")
    ):
        raise ValueError("invalid usage")
