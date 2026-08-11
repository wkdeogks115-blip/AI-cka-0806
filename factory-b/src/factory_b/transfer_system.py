from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


def canonical_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def packet_hash(packet: dict) -> str:
    material = dict(packet)
    material.pop("packet_hash", None)
    return hashlib.sha256(canonical_json_bytes(material)).hexdigest()


@lru_cache(maxsize=None)
def load_schema(root: Path, name: str) -> dict:
    return json.loads((Path(root) / "transfer" / name).read_text(encoding="utf-8"))


def validate_schema(instance: dict, schema: dict) -> list[str]:
    errors = sorted(Draft202012Validator(schema).iter_errors(instance), key=lambda e: list(e.path))
    return [f"{'/'.join(str(x) for x in e.path) or '<root>'}: {e.message}" for e in errors]


def validate_packet(root: Path, packet: dict) -> list[str]:
    errors = validate_schema(packet, load_schema(root, "transfer_packet.schema.json"))
    if packet.get("packet_hash") and packet_hash(packet) != packet.get("packet_hash"):
        errors.append("packet_hash mismatch")
    return errors


def validate_receipt(root: Path, receipt: dict) -> list[str]:
    return validate_schema(receipt, load_schema(root, "agent_result_receipt.schema.json"))


def _path_in_scope(path: str, scopes: list[str]) -> bool:
    p = Path(path).as_posix().lstrip("./")
    for scope in scopes:
        s = Path(scope).as_posix().lstrip("./")
        if p == s or p.startswith(s.rstrip("/") + "/"):
            return True
    return False


def evaluate_receipt(root: Path, packet: dict, receipt: dict) -> dict:
    reasons: list[str] = []
    packet_errors = validate_packet(root, packet)
    receipt_errors = validate_receipt(root, receipt)
    integrity = not packet_errors and receipt.get("packet_hash") == packet.get("packet_hash") and receipt.get("task_id") == packet.get("task_id")
    if packet_errors:
        reasons.extend(f"packet: {x}" for x in packet_errors)
    if receipt_errors:
        reasons.extend(f"receipt: {x}" for x in receipt_errors)
    if receipt.get("packet_hash") != packet.get("packet_hash"):
        reasons.append("receipt is bound to a different packet_hash")
    if receipt.get("task_id") != packet.get("task_id"):
        reasons.append("receipt task_id mismatch")

    changed = receipt.get("changed_files", [])
    out_of_scope = [p for p in changed if not _path_in_scope(p, packet.get("allowed_write_scope", []))]
    scope_ok = not out_of_scope and not receipt.get("unrelated_changes", [])
    if out_of_scope:
        reasons.append("out-of-scope changed files: " + ", ".join(out_of_scope))
    if receipt.get("unrelated_changes"):
        reasons.append("agent reported unrelated changes")

    required_tests = packet.get("required_tests", [])
    returned_tests = {x.get("command"): x for x in receipt.get("tests", [])}
    covered = sum(1 for t in required_tests if t in returned_tests)
    test_coverage = covered / len(required_tests) if required_tests else 1.0
    if test_coverage < 1:
        reasons.append("required test evidence incomplete")
    statuses = [returned_tests[t].get("status") for t in required_tests if t in returned_tests]
    test_pass_rate = (sum(1 for s in statuses if s == "PASS") / len(required_tests)) if required_tests else 1.0
    if any(s != "PASS" for s in statuses) or len(statuses) < len(required_tests):
        reasons.append("not all required tests passed")

    acceptance = receipt.get("acceptance_results", [])
    if acceptance:
        acceptance_pass_rate = sum(1 for x in acceptance if x.get("status") == "PASS") / len(acceptance)
    else:
        acceptance_pass_rate = 0.0
    if acceptance_pass_rate < 1:
        reasons.append("acceptance criteria not fully evidenced as PASS")

    evidence_req = packet.get("evidence_required", [])
    refs = receipt.get("evidence_refs", [])
    evidence_completeness = min(1.0, len([r for r in refs if r]) / len(evidence_req)) if evidence_req else 1.0
    if evidence_completeness < 1:
        reasons.append("evidence references incomplete")

    clarifications = int(receipt.get("clarifications_count", 0))
    status = receipt.get("status")
    example_only = str(receipt.get("agent_label", "")).upper().startswith("EXAMPLE")
    if example_only:
        reasons.append("example/template receipt is not execution evidence")

    if example_only:
        verdict = "REJECT"
        independence = "UNVERIFIED"
    elif not integrity or not scope_ok:
        verdict = "REJECT"
        independence = "FAIL"
    elif status == "BLOCKED":
        verdict = "BLOCKED"
        independence = "FAIL" if clarifications > 0 else "UNVERIFIED"
    elif status != "COMPLETED":
        verdict = "REJECT"
        independence = "FAIL"
    elif test_coverage == 1 and test_pass_rate == 1 and acceptance_pass_rate == 1 and evidence_completeness == 1:
        verdict = "ACCEPT"
        independence = "PASS" if clarifications == 0 else "PARTIAL"
    else:
        verdict = "PATCH"
        independence = "PARTIAL" if clarifications == 0 else "FAIL"

    scorecard = {
        "task_id": packet.get("task_id", ""),
        "verdict": verdict,
        "packet_integrity": bool(integrity),
        "scope_compliance": bool(scope_ok),
        "required_tests_coverage": round(test_coverage, 6),
        "test_pass_rate": round(test_pass_rate, 6),
        "acceptance_pass_rate": round(acceptance_pass_rate, 6),
        "clarifications_count": clarifications,
        "unrelated_diff_count": len(out_of_scope) + len(receipt.get("unrelated_changes", [])),
        "evidence_completeness": round(evidence_completeness, 6),
        "handoff_independence_status": independence,
        "reasons": reasons,
    }
    score_errors = validate_schema(scorecard, load_schema(root, "evaluator_scorecard.schema.json"))
    if score_errors:
        raise ValueError("invalid scorecard generated: " + "; ".join(score_errors))
    return scorecard


def freeze_packet(packet_without_hash: dict) -> dict:
    packet = dict(packet_without_hash)
    packet["status"] = "FROZEN"
    packet["packet_hash"] = packet_hash(packet)
    return packet
