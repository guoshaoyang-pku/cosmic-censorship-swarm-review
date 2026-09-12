#!/usr/bin/env python3
"""W068-FORM-POLARITY-11 runner (worker-068, bounded task).

Runs the two pinned class-binding stages over the pinned shadow pipeline:

  stage A (structural): <shadow>/artifacts/formulation/tools/check_class_schema.py --json FIXTURE
  stage B (semantic)  : <shadow>/artifacts/worker-06/spec_conformance_audit.py FIXTURE --spec <shadow>/artifacts/formulation/rule_spec.json

A probe "escapes" iff BOTH stages accept it. The WCC arm is INFORMATIVE iff the
unmutated identity control is accepted by both stages. Validity requires: no drift in
the five pinned shadow inputs, no fixture tamper against manifest.json, and every
known-rejected liveness control rejected by at least one stage.

The live tree is read for context only (canonical WCC + live KEY_MANIFEST hashes
before and after the run); the measurement itself never reads live pipeline inputs.

Writes raw_verdicts.json, report.json, checkpoint.json. Never sets a map gate
verdict or a node status.

Usage: python3 run_polarity11.py
Exit: 0 run completed (valid or not); 2 precondition failure.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
CST = timezone(timedelta(hours=8))
MANIFEST = HERE / "manifest.json"
SHADOW = HERE / "shadow"
PY = sys.executable

STAGE_A = SHADOW / "artifacts" / "formulation" / "tools" / "check_class_schema.py"
STAGE_B = SHADOW / "artifacts" / "worker-06" / "spec_conformance_audit.py"
SPEC = SHADOW / "artifacts" / "formulation" / "rule_spec.json"
KEY_MANIFEST = SHADOW / "artifacts" / "formulation" / "KEY_MANIFEST.json"
BASE = SHADOW / "schemas" / "af_wcc_vacuum.yaml"
SHADOW_INPUTS = [STAGE_A, STAGE_B, SPEC, KEY_MANIFEST, BASE]

LIVE_CONTEXT = [
    "schemas/af_wcc_vacuum.yaml",
    "artifacts/formulation/KEY_MANIFEST.json",
]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run_cmd(args, timeout=180):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout, cwd=str(ROOT))
        return {"exit": p.returncode, "stdout": p.stdout, "stderr": p.stderr[-2000:]}
    except subprocess.TimeoutExpired:
        return {"exit": 124, "stdout": "", "stderr": f"timeout after {timeout}s"}


def parse_json(text):
    try:
        return json.loads(text)
    except Exception:
        return None


def stage_a(fixture: Path) -> dict:
    r = run_cmd([PY, str(STAGE_A), "--json", str(fixture)])
    j = parse_json(r["stdout"]) or {}
    return {
        "tool": str(STAGE_A.relative_to(ROOT)),
        "exit": r["exit"],
        "verdict": j.get("verdict"),
        "failed_rules": j.get("failed_rules", []),
        "failures": [{"rule": f.get("rule"), "msg": str(f.get("msg"))[:300]} for f in j.get("failures", [])],
        "parse_ok": bool(j),
        "stderr": r["stderr"],
    }


def stage_b(fixture: Path) -> dict:
    r = run_cmd([PY, str(STAGE_B), str(fixture), "--spec", str(SPEC)])
    j = parse_json(r["stdout"]) or {}
    rule_verdicts = {}
    for c in j.get("checks", []) or []:
        rule_verdicts[str(c.get("rule"))] = c.get("verdict")
    return {
        "tool": str(STAGE_B.relative_to(ROOT)),
        "exit": r["exit"],
        "verdict": j.get("verdict"),
        "failed_rules": j.get("failed_rules", []),
        "rule_verdicts": rule_verdicts,
        "fail_details": [c for c in (j.get("checks", []) or []) if c.get("verdict") == "fail"][:8],
        "parse_ok": bool(j),
        "stderr": r["stderr"],
    }


def main() -> int:
    manifest_sha = sha256_file(MANIFEST)
    m = json.loads(MANIFEST.read_text())
    invalid = []

    shadow_before = {str(p.relative_to(ROOT)): sha256_file(p) for p in SHADOW_INPUTS}
    for rel, expected in m["shadow_pins"].items():
        measured = shadow_before.get(rel)
        if measured != expected["sha256"]:
            invalid.append(f"pinned shadow input drift at start: {rel} {expected['sha256'][:12]} -> {str(measured)[:12]}")
    live_before = {rel: sha256_file(ROOT / rel) for rel in LIVE_CONTEXT}

    results = []
    for fx in m["fixtures"]:
        path = ROOT / fx["fixture"]
        if not path.is_file():
            invalid.append(f"missing fixture {fx['fixture']}")
            continue
        if sha256_file(path) != fx["sha256"]:
            invalid.append(f"fixture hash mismatch (tamper): {fx['fixture']}")
        a = stage_a(path)
        b = stage_b(path)
        escaped = (a["verdict"] == "pass" and b["verdict"] == "accept")
        reject_stage = None
        if a["verdict"] != "pass":
            reject_stage = "A"
        elif b["verdict"] != "accept":
            reject_stage = "B"
        results.append({
            "fixture": fx["fixture"],
            "file": fx["file"],
            "family": fx["family"],
            "op_id": fx["op_id"],
            "expectation": fx["expectation"],
            "expected_catcher_rules": fx["expected_catcher_rules"],
            "leak_claim": fx["leak_claim"],
            "sha256": fx["sha256"],
            "stage_a": a,
            "stage_b": b,
            "escaped": escaped,
            "reject_stage": reject_stage,
            "catch_rules": (a["failed_rules"] + b["failed_rules"]),
        })

    shadow_after = {str(p.relative_to(ROOT)): sha256_file(p) for p in SHADOW_INPUTS}
    live_after = {rel: sha256_file(ROOT / rel) for rel in LIVE_CONTEXT}
    for rel, h in shadow_after.items():
        if shadow_before[rel] != h:
            invalid.append(f"pinned shadow input changed during run: {rel}")

    def by_expectation(kind):
        return [r for r in results if r["expectation"] == kind]

    probes = by_expectation("should_be_caught")
    conforming = by_expectation("must_be_accepted")
    known_rejected = by_expectation("known_rejected_positive_control")

    identity = next((r for r in conforming if r["family"] == "identity-roundtrip"), None)
    informative = bool(identity and identity["escaped"])

    escapes = [r for r in probes if r["escaped"]]
    caught = [r for r in probes if not r["escaped"]]
    escape_rate = (len(escapes) / len(probes)) if probes else None

    liveness_dead = [r["fixture"] for r in known_rejected if r["escaped"]]
    conforming_rejected = [r["fixture"] for r in conforming if not r["escaped"]]

    if liveness_dead:
        invalid.append(f"known-rejected liveness control escaped: {liveness_dead}")
    if not informative:
        invalid.append("identity control rejected by at least one stage: WCC arm non-informative")

    findings = []
    if informative and escapes:
        findings.append({
            "finding_id": "W068-P11-F1",
            "kind": "blind-spot-confirmed-WCC",
            "statement": (f"On the pinned shadow pipeline, {len(escapes)}/{len(probes)} WCC conclusion-"
                          f"polarity/content probes are accepted by BOTH stages while the unmutated base is "
                          f"also accepted. Neither stage compares conclusion.statement_formal / "
                          f"statement_natural_language content against the frozen WCC conclusion."),
            "evidence": [r["fixture"] for r in escapes],
            "falsifier": "An independent re-run of the pinned shadow pipeline that rejects any of these probes, or a pin-aware stage revision that compares conclusion content.",
        })
    if informative and caught:
        findings.append({
            "finding_id": "W068-P11-F2",
            "kind": "partial-detection",
            "statement": (f"{len(caught)}/{len(probes)} WCC probes are caught; the catching rules are "
                          f"{sorted({r_ for r in caught for r_ in r['catch_rules']})}. These are vocabulary/structure checks, not conclusion-content checks."),
            "evidence": [{"fixture": r["fixture"], "catch_rules": r["catch_rules"]} for r in caught],
            "falsifier": "A re-run in which a caught probe is accepted or an escaping probe is caught.",
        })
    if conforming_rejected:
        findings.append({
            "finding_id": "W068-P11-F3",
            "kind": "format-sensitivity",
            "statement": f"Conforming controls rejected by at least one stage: {conforming_rejected}. Probe readings for those controls are false-positive-dominated.",
            "evidence": conforming_rejected,
            "falsifier": "A re-run in which every conforming control is accepted by both stages.",
        })
    if not informative:
        findings.append({
            "finding_id": "W068-P11-F0",
            "kind": "arm-non-informative",
            "statement": "The identity control is rejected by at least one stage in the pinned shadow, so all probe verdicts are base-rejection artifacts and no polarity reading is licensed.",
            "evidence": [identity["fixture"]] if identity else [],
            "falsifier": "A pinned-shadow re-run in which the identity control is accepted by both stages.",
        })

    binding = {
        "shadow_root": str(SHADOW.relative_to(ROOT)),
        "pinned_shadow_inputs": {k: {"sha256": v, "provenance": m["shadow_pins"][k]["provenance"]} for k, v in shadow_before.items()},
        "shadow_inputs_unchanged_during_run": all(shadow_before[k] == shadow_after[k] for k in shadow_before),
        "live_context_before": live_before,
        "live_context_after": live_after,
        "live_context_changed_during_run": {k: [live_before[k], live_after[k]] for k in live_before if live_before[k] != live_after[k]},
        "base_self_declared": {"class_id": "AF-WCC-VAC-GEN", "sha256": shadow_before[str(BASE.relative_to(ROOT))],
                               "note": "archived pre-rev12 base; live canonical is cce9c60146d6 and is rejected by stage B R03 before any probe"},
        "op_source": m["op_source"],
    }

    report = {
        "corpus_id": m["corpus_id"],
        "task_id": m["task_id"],
        "worker": m["worker"],
        "node_id": "A1",
        "gate": "G-CLASSBIND (folded into G-AUDIT as calibration evidence)",
        "class_ids": ["AF-WCC-VAC-GEN"],
        "question": m["question"],
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "manifest_sha256": manifest_sha,
        "valid": not invalid,
        "invalid_reasons": invalid,
        "binding": binding,
        "measurement": {
            "probes_total": len(probes),
            "informative": informative,
            "escapes": [r["fixture"] for r in escapes],
            "escape_count": len(escapes),
            "escape_rate": escape_rate,
            "escape_families": sorted({r["family"] for r in escapes}),
            "caught": [{"fixture": r["fixture"], "catch_rules": r["catch_rules"]} for r in caught],
            "conforming_controls_total": len(conforming),
            "conforming_controls_accepted": len(conforming) - len(conforming_rejected),
            "conforming_controls_rejected": conforming_rejected,
            "known_rejected_controls_total": len(known_rejected),
            "known_rejected_controls_rejected": len(known_rejected) - len(liveness_dead),
            "per_fixture": [{
                "fixture": r["fixture"], "family": r["family"], "sha256": r["sha256"],
                "stage_a": r["stage_a"]["verdict"], "stage_b": r["stage_b"]["verdict"],
                "escaped": r["escaped"], "reject_stage": r["reject_stage"], "catch_rules": r["catch_rules"],
            } for r in results],
        },
        "findings": findings,
        "limitations": [
            "Measurement is on an ARCHIVED pre-rev12 WCC base (9a8bd4c96800) under a pinned earlier KEY_MANIFEST (fce91948ba3a), because live rev12 cce9c60146d6 is rejected by stage B R03 and the archived base is rejected by stage A under the live KEY_MANIFEST. This is a detector-blind-spot measurement, not a statement about live rev12 content.",
            "The two stage tools are the pinned objects under test; their bytes are hash-verified but not re-implemented.",
            "Acceptance by both stages is evidence about the pipeline only, not a class-truth claim.",
            "Method continuation of worker-068's own FORM-POLARITY-10 harness: not an author-independent replication. An independent executor should re-run the pinned shadow.",
        ],
        "falsifier": m["falsifier"],
        "next_falsifier": ("An independent executor (not worker-068) re-runs this pinned shadow and reproduces the per-probe "
                           "verdicts, or a pin-aware stage revision that compares conclusion content catches a probe reported "
                           "as escaping here, or the live F1 R03 defect is repaired and the WCC arm is re-measured on rev12."),
        "non_claims": m["non_claims"] + [
            "This worker does not claim node completion, validation_status=passed, or any gate verdict.",
        ],
        "evidence_refs": [
            f"artifacts/worker-068/polarity11/manifest.json#{manifest_sha[:12]}",
            f"artifacts/worker-068/polarity11/build_corpus11.py#{sha256_file(HERE / 'build_corpus11.py')[:12]}",
            f"artifacts/worker-068/polarity11/run_polarity11.py#{sha256_file(HERE / 'run_polarity11.py')[:12]}",
        ] + [f"{r['fixture']}#{r['sha256'][:12]}" for r in results],
    }

    raw = {
        "corpus_id": m["corpus_id"],
        "task_id": m["task_id"],
        "manifest_sha256": manifest_sha,
        "generated_at": report["generated_at"],
        "shadow_inputs_before": shadow_before,
        "shadow_inputs_after": shadow_after,
        "live_context_before": live_before,
        "live_context_after": live_after,
        "results": results,
    }
    (HERE / "raw_verdicts.json").write_text(json.dumps(raw, indent=2, sort_keys=False) + "\n")
    (HERE / "report.json").write_text(json.dumps(report, indent=2, sort_keys=False) + "\n")

    checkpoint = {
        "checkpoint": 1,
        "at": report["generated_at"],
        "worker": m["worker"],
        "task_id": m["task_id"],
        "corpus_id": m["corpus_id"],
        "node_id": "A1",
        "gate": report["gate"],
        "class_ids": report["class_ids"],
        "hours_spent_estimate": 0.4,
        "status": {"delivered": True, "validation_status": "unverified",
                   "no_completion_claim": "worker cannot set done/passed/gate verdict"},
        "binding": binding,
        "measurement": {k: v for k, v in report["measurement"].items() if k != "per_fixture"},
        "valid": report["valid"],
        "invalid_reasons": invalid,
        "findings": [f["finding_id"] for f in findings],
        "artifacts": {
            "artifacts/worker-068/polarity11/manifest.json": {"sha256": manifest_sha},
            "artifacts/worker-068/polarity11/raw_verdicts.json": {"sha256": sha256_file(HERE / "raw_verdicts.json")},
            "artifacts/worker-068/polarity11/report.json": {"sha256": sha256_file(HERE / "report.json")},
            "artifacts/worker-068/polarity11/build_corpus11.py": {"sha256": sha256_file(HERE / "build_corpus11.py")},
            "artifacts/worker-068/polarity11/run_polarity11.py": {"sha256": sha256_file(HERE / "run_polarity11.py")},
        },
        "limitations": report["limitations"],
        "falsifier": report["falsifier"],
        "next_falsifier": report["next_falsifier"],
        "non_claims": report["non_claims"],
    }
    (HERE / "checkpoint.json").write_text(json.dumps(checkpoint, indent=2, sort_keys=False) + "\n")

    print(json.dumps({
        "valid": report["valid"],
        "invalid_reasons": invalid,
        "informative": informative,
        "probes": len(probes),
        "escapes": len(escapes),
        "escape_rate": escape_rate,
        "caught": [(r["fixture"], r["catch_rules"]) for r in caught],
        "conforming_rejected": conforming_rejected,
        "liveness_dead": liveness_dead,
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
