#!/usr/bin/env python3
"""Assemble W055-A0-HF01-FIRING-01 report.json from the measured pieces.

Read-only over canonical paths; re-measures every pin at assembly time and refuses
(exit 3) if anything moved after the census/probe runs.
"""
from __future__ import annotations

import glob
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
OUT = ROOT / "artifacts" / "worker-055" / "a0_hf01_firing"

PINS = {
    "ledger/theorems.jsonl":
        "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28",
    "evaluation_rubric.yaml":
        "d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885",
    "artifacts/audit/audit_run.py":
        "3b27dd3fef7f41488158099f888e3685dc8d9cca9f0507ad46c4d01f9bd2c411",
    "artifacts/audit/audit_lib.py":
        "ae573db84631b970caeea46e8821aee8af66166f6a5f16251e4a6c819a377c8c",
    "schemas/taxonomy_cases.jsonl":
        "ccf7041bd0ff3ce844c07a700a588b7fe8e3c90880674c5e595b21f6259a8f03",
}


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def lines(rel: str, start: int, end: int):
    src = (ROOT / rel).read_text().splitlines()
    return {str(n): src[n - 1].rstrip() for n in range(start, end + 1)}


def main() -> int:
    drift = []
    pins = {}
    for rel, want in PINS.items():
        got = sha(ROOT / rel)
        pins[rel] = got
        if got != want:
            drift.append({"path": rel, "declared": want, "measured": got})
    if drift:
        print(json.dumps({"status": "HASH_DRIFT", "drift": drift}, indent=2))
        return 3

    census = json.loads((OUT / "census.json").read_text())
    live = sorted(glob.glob(str(OUT / "canonical_live" / "audit-*.json")))[-1]
    ctrl = sorted(glob.glob(str(OUT / "canonical_controls" / "audit-*.json")))[-1]
    live_d = json.loads(Path(live).read_text())
    ctrl_d = json.loads(Path(ctrl).read_text())
    hf01_live = [v for v in live_d["violations"] if v["hf"] == "HF-01"]
    hf01_ctrl = [v for v in ctrl_d["violations"] if v["hf"] == "HF-01"]

    report = {
        "schema": "w055-adjudication/v1",
        "task_id": "W055-A0-HF01-FIRING-01",
        "actor": "worker-055",
        "node_id": "A0",
        "gate": "G-AUDIT",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN",
                      "AF-WCC-SCALAR-SPH"],
        "contested_finding": "A0-089-A (reviews/A0-review-worker-089.json, 2026-09-12T00:51:54+08:00)",
        "contested_text": ("HF-01 conformance (evaluation_rubric.yaml:174) reads "
                           "claim.artifact_refs, absent from all 62 ledger/theorems.jsonl rows "
                           "incl. the 30 theorem rows; audit_lib.py:189-191 + audit_run.py:216 "
                           "make that 30 false criticals and break the G-AUDIT hard_failure_rate "
                           "criterion (evaluation_rubric.yaml:149)."),
        "pins_measured_at_assembly": pins,
        "census_artifact": "artifacts/worker-055/a0_hf01_firing/census.json",
        "census_sha256": sha(OUT / "census.json"),
        "canonical_live_run": {
            "scope": "--scan ledger (the finding is scoped to ledger/theorems.jsonl rows)",
            "report_path": str(Path(live).relative_to(ROOT)),
            "report_sha256": sha(Path(live)),
            "corpus": live_d["corpus"],
            "rubric_sha256": live_d["rubric_sha256"],
            "summary": live_d["summary"],
            "hf01_count": len(hf01_live),
            "hf01_wheres": [v["where"] for v in hf01_live],
            "runner_internal_gates": live_d["gates"],
            "runner_internal_gates_note": ("computed by audit_run.gate_verdicts on the scoped "
                                           "corpus (claims=0), NOT a controller gate verdict "
                                           "and not citable as one."),
            "limitation": ("the full default scan over artifacts/ (524 MB, 5044 json/jsonl "
                           "files) exceeded a 10-minute worker bound and was stopped; the "
                           "contested finding is scoped to the canonical ledger, which this "
                           "run covers exactly."),
        },
        "canonical_control_run": {
            "scope": "--scan ledger tmp/w055_hf01_probe (labelled positive control)",
            "report_path": str(Path(ctrl).relative_to(ROOT)),
            "report_sha256": sha(Path(ctrl)),
            "corpus": ctrl_d["corpus"],
            "summary": ctrl_d["summary"],
            "hf01_count": len(hf01_ctrl),
            "hf01_wheres": [v["where"] for v in hf01_ctrl],
            "interpretation": ("end-to-end proof that the canonical pipeline emits HF-01 when a "
                               "claim object with conclusion_type=theorem and no artifact_refs "
                               "is present; the 62 ledger rows in the same run still contribute 0."),
        },
        "code_path_measurement": {
            "only_hf01_emitter": "artifacts/audit/audit_lib.py:189-191 (inside check_class_binding)",
            "only_caller": "artifacts/audit/audit_run.py:233, inside the loop over corpus['claims'] at :232",
            "routing_predicate": "artifacts/audit/audit_run.py:96-119 ('claims' requires claim_id, or class_id+statement for non-schema docs; ledger rows carry class_ids (plural) + statement_exact)",
            "worker_089_cited_line": "artifacts/audit/audit_run.py:216",
            "line_216_actual": lines("artifacts/audit/audit_run.py", 216, 216)["216"],
            "line_216_note": ("this is the argparse --scan default declaration, not an HF-01 "
                              "code path; the citation does not resolve to the claimed mechanism."),
            "cited_lines_excerpt": {
                "audit_lib.py:189-191": lines("artifacts/audit/audit_lib.py", 189, 191),
                "audit_run.py:216": lines("artifacts/audit/audit_run.py", 216, 216),
                "audit_run.py:232-233": lines("artifacts/audit/audit_run.py", 232, 233),
            },
        },
        "tiers": {
            "T0_canonical_routing": census["tier0_canonical_routing"],
            "T1_rubric_literal_count": census["tier1_rubric_literal"],
            "T2_detector_probes": census["tier2_detector_probes"],
        },
        "verdict": {
            "status": "A0-089-A_PARTIAL: COUNT CONFIRMED, MECHANISM REFUTED",
            "confirmed": ("30 of 62 ledger rows carry conclusion_type=theorem and no "
                          "artifact_refs field exists anywhere in the ledger; under a "
                          "rubric-literal reading that treats ledger records as claims, "
                          "HF-01's antecedent is satisfied 30 times."),
            "refuted": ("the canonical runner does not produce those 30 criticals: scan_corpus "
                        "routes 0/62 ledger rows to corpus['claims'] and 62/62 to "
                        "corpus['records'], and check_class_binding (the sole HF-01 emitter) is "
                        "called only over corpus['claims']. Measured canonical HF-01 count on "
                        "the pinned ledger is 0 (critical total 0) and 1 in the labelled control. "
                        "The cited audit_run.py:216 is the --scan argument, not an HF-01 path."),
            "consequence_for_A0": ("A0-089-A is not, as stated, a live false-critical defect in "
                                   "the canonical audit output; it is a rubric-text vs corpus-"
                                   "routing scope ambiguity. Whether HF-01 *should* cover "
                                   "theorem-typed ledger records is an owner scope decision for "
                                   "the A0 rubric text (cf. PROTOCOL rule 1, which governs "
                                   "claim events, not ledger records). No gate verdict, node "
                                   "status or validation_status is claimed here."),
        },
        "controls": {
            "positive_end_to_end": "HF-01=1 on PROBE-POS-W055 in canonical_controls run",
            "negative_end_to_end": "ledger rows in the same run contribute 0 HF-01",
            "detector_positive": "check_class_binding on theorem claim without refs -> HF-01 x1",
            "detector_negative": "with artifact_refs -> HF-01 x0",
            "routing_negative": "ledger row without singular class_id -> HF-02 unknown class_id, never HF-01",
            "hash_drift_guard": "census.py and assemble_report.py exit 3 on any pin drift",
        },
        "non_claims": [
            "no gate verdict (G-AUDIT stays pending; authority Astra/lead-audit)",
            "no node status change (A0 stays as the map has it)",
            "no validation_status=passed",
            "no mathematics or physics claim",
            "no claim that A0-089-A's other findings (B/C/D/E/F) are affected",
        ],
        "falsifier": census["falsifier"],
    }
    (OUT / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print("wrote", OUT / "report.json")
    print("verdict:", report["verdict"]["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
