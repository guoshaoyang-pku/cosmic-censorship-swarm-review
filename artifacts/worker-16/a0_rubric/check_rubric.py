#!/usr/bin/env python3
"""A0 rubric validator (worker-16, A0 main-author draft).

Enforces the acceptance criteria for evaluation_rubric.yaml structurally, so the rubric
cannot silently regress on the things the assignment names:

  V1 YAML parses, schema_version/artifact_id/owner present
  V2 task types T-SCHEMA, T-LIT, T-NUM, T-FORMAL present, each with a verifier that has
     machine_checkable AND reviewer_adjudicated parts and >=1 acceptance line
  V3 every acceptance line names an evidence_type that exists in evidence_types
  V4 every hard_failure_if references an existing HF id
  V5 no universal scalar score (no composite accept/reject key; metrics are diagnostic_only
     and forbidden to aggregate across classes)
  V6 every hard failure has severity+detector; every gate has criteria+task_type
  V7 every referenced class id is frozen or GLOBAL

Usage:
  python3 artifacts/worker-16/a0_rubric/check_rubric.py [rubric.yaml]
Exit 0 = all checks pass; 1 = failures listed.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
CST = timezone(timedelta(hours=8))
REQUIRED_TASK_TYPES = ["T-SCHEMA", "T-LIT", "T-NUM", "T-FORMAL"]
LINE_REQUIRED = ["id", "requirement", "evidence_type", "check", "pass_condition",
                 "hard_failure_if", "machine_checkable"]
SCALAR_FORBIDDEN_KEYS = re.compile(
    r"^(score|total_score|overall_score|aggregate_score|composite_score|weighted_score)$", re.I)
CLASS_TOKEN = re.compile(r"\bAF-[A-Z0-9]+(?:-[A-Z0-9]+)*\b")


def walk_strings(obj, path="$"):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk_strings(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_strings(v, f"{path}[{i}]")
    elif isinstance(obj, str):
        yield path, obj


def validate(rubric: dict, raw: str) -> list[str]:
    errs: list[str] = []

    # V1
    if not rubric.get("schema_version"):
        errs.append("V1: schema_version missing")
    for key in ("artifact_id", "owner", "status"):
        if not rubric.get(key):
            errs.append(f"V1: {key} missing")

    # V2
    tts = rubric.get("task_types") or {}
    for tt in REQUIRED_TASK_TYPES:
        node = tts.get(tt)
        if not node:
            errs.append(f"V2: task type {tt} missing")
            continue
        ver = node.get("verifier") or {}
        for part in ("machine_checkable", "reviewer_adjudicated"):
            if not ver.get(part):
                errs.append(f"V2: {tt}.verifier.{part} empty")
        lines = node.get("acceptance_lines") or []
        if not lines:
            errs.append(f"V2: {tt} has no acceptance_lines")
        if not node.get("owner_gate"):
            errs.append(f"V2: {tt}.owner_gate missing")

    # V3 / V4
    evidence_ids = {e["id"] for e in rubric.get("evidence_types", [])}
    hf_ids = {h["id"] for h in rubric.get("hard_failures", [])}
    for tt, node in tts.items():
        for line in node.get("acceptance_lines", []):
            for req in LINE_REQUIRED:
                if req not in line:
                    errs.append(f"V3: {tt}.{line.get('id','?')} missing field {req}")
            ev = line.get("evidence_type")
            if ev not in evidence_ids:
                errs.append(f"V3: {tt}.{line.get('id','?')} evidence_type {ev!r} not in catalog")
            hf = line.get("hard_failure_if")
            if hf not in hf_ids:
                errs.append(f"V4: {tt}.{line.get('id','?')} hard_failure_if {hf!r} not an HF id")

    # V5
    nss = rubric.get("no_universal_scalar_score") or {}
    if not isinstance(nss, dict) or nss.get("enforced") is not True:
        errs.append("V5: no_universal_scalar_score must be a mapping with enforced: true")
    for path, text in walk_strings(rubric):
        pass  # key scan below
    def scan_keys(obj, path="$"):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if SCALAR_FORBIDDEN_KEYS.match(k) and path != "$.metrics":
                    errs.append(f"V5: forbidden scalar key {k!r} at {path}")
                scan_keys(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                scan_keys(v, f"{path}[{i}]")
    scan_keys(rubric)
    for name, m in (rubric.get("metrics") or {}).items():
        if m.get("accept_reject_role") != "diagnostic_only":
            errs.append(f"V5: metric {name} is not diagnostic_only")
        if m.get("aggregation_across_classes") != "forbidden":
            errs.append(f"V5: metric {name} does not forbid cross-class aggregation")
        if not m.get("evidence_type"):
            errs.append(f"V5: metric {name} has no evidence_type")

    # V6
    for h in rubric.get("hard_failures", []):
        if not h.get("severity"):
            errs.append(f"V6: {h.get('id','?')} missing severity")
        if not h.get("detector"):
            errs.append(f"V6: {h.get('id','?')} missing detector")
    for g in rubric.get("gates", []):
        if not g.get("criteria"):
            errs.append(f"V6: gate {g.get('id','?')} has no criteria")
        if not g.get("task_type"):
            errs.append(f"V6: gate {g.get('id','?')} has no task_type")

    # V7
    frozen = {c["id"] for c in rubric.get("frozen_classes", [])}
    allowed = frozen | {"GLOBAL"}
    for path, text in walk_strings(rubric):
        for tok in CLASS_TOKEN.findall(text):
            if tok not in allowed:
                errs.append(f"V7: unknown class id {tok!r} at {path}")
    return errs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("rubric", nargs="?", default=str(ROOT / "evaluation_rubric.yaml"))
    ap.add_argument("--report", default=str(Path(__file__).resolve().parent / "validator_report.json"))
    a = ap.parse_args()
    path = Path(a.rubric)
    raw = path.read_text()
    rubric = yaml.safe_load(raw)
    errs = validate(rubric, raw)
    report = {
        "validator": "artifacts/worker-16/a0_rubric/check_rubric.py",
        "rubric_path": str(path),
        "rubric_sha256": __import__("hashlib").sha256(raw.encode()).hexdigest(),
        "checked_at": datetime.now(CST).isoformat(timespec="seconds"),
        "checks": {
            "V1_parse_and_identity": "pass" if not any(e.startswith("V1") for e in errs) else "fail",
            "V2_task_types_and_verifiers": "pass" if not any(e.startswith("V2") for e in errs) else "fail",
            "V3_evidence_types": "pass" if not any(e.startswith("V3") for e in errs) else "fail",
            "V4_hard_failure_refs": "pass" if not any(e.startswith("V4") for e in errs) else "fail",
            "V5_no_universal_scalar_score": "pass" if not any(e.startswith("V5") for e in errs) else "fail",
            "V6_hf_and_gate_shape": "pass" if not any(e.startswith("V6") for e in errs) else "fail",
            "V7_class_ids": "pass" if not any(e.startswith("V7") for e in errs) else "fail",
        },
        "errors": errs,
        "result": "PASS" if not errs else "FAIL",
    }
    Path(a.report).write_text(json.dumps(report, indent=2, sort_keys=True))
    print(json.dumps({"result": report["result"], "errors": errs}, indent=2))
    return 0 if not errs else 1


if __name__ == "__main__":
    sys.exit(main())
