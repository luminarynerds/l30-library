# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Action:
    action_type: str
    payload: Dict[str, Any] = field(default_factory=dict)


def _coerce_number(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _evaluate_condition(answer: Any, condition: Dict[str, Any]) -> bool:
    op = condition.get("op")
    target = condition.get("value")

    if op == "missing":
        return answer is None or answer == "" or answer == []

    if answer is None:
        # All other ops on a missing answer are vacuously false.
        return False

    if op == "eq":
        return answer == target
    if op == "neq":
        return answer != target
    if op in ("gt", "gte", "lt", "lte"):
        a, b = _coerce_number(answer), _coerce_number(target)
        if a is None or b is None:
            return False
        return {
            "gt": a > b,
            "gte": a >= b,
            "lt": a < b,
            "lte": a <= b,
        }[op]
    if op == "in":
        if not isinstance(target, (list, tuple, set)):
            return False
        return answer in target
    if op == "not_in":
        if not isinstance(target, (list, tuple, set)):
            return False
        return answer not in target
    if op == "contains":
        if isinstance(answer, (list, tuple, set, str)):
            return target in answer
        return False

    # Unknown op: treat as no-match rather than raise. Lets staff add new
    # rules without breaking existing surveys mid-deploy.
    return False


def evaluate_question(answer: Any, rules: Optional[List[Dict[str, Any]]]) -> List[Action]:
    if not rules:
        return []
    out: List[Action] = []
    for rule in rules:
        condition = rule.get("if") or {}
        outcome = rule.get("then") or {}
        if not _evaluate_condition(answer, condition):
            continue
        action_type = outcome.get("action")
        if not action_type:
            continue
        payload = {k: v for k, v in outcome.items() if k != "action"}
        out.append(Action(action_type=action_type, payload=payload))
    return out


def evaluate_response(
    answers_by_qid: Dict[int, Any],
    rules_by_qid: Dict[int, Optional[List[Dict[str, Any]]]],
) -> List[Action]:
    out: List[Action] = []
    for qid, rules in rules_by_qid.items():
        out.extend(evaluate_question(answers_by_qid.get(qid), rules))
    return out


def score_scenario_answer(answer: Any, expected_flags: List[str]) -> int:
    if not isinstance(answer, list):
        return 0
    chosen = {str(x) for x in answer}
    return sum(1 for flag in expected_flags if flag in chosen)
