#!/usr/bin/env python3
"""Emit worker-094's W094F-CF21-REV13-RECHECK-01 events to the outbox.

Validates each event against research_map.schemas before appending, so a
malformed event cannot enter the stream (the prior CLM-W094C reject is the
cautionary tale).  Append-only; never rewrites existing lines.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research_map"))
import schemas  # noqa: E402

CST = timezone(timedelta(hours=8))
TS = datetime.now(CST).replace(microsecond=0)
STAMP = TS.strftime("%Y%m%dT%H%M%S")
NOW = TS.isoformat()
OUTBOX = ROOT / "comms/outbox/worker-094.jsonl"
ACTOR = "worker-094"
TASK = "W094F-CF21-REV13-RECHECK-01"
CLASSES = ["AF-WCC-SCALAR-SPH", "AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
CLASS_STR = ";".join(CLASSES)
NODES = ["F0", "F1", "F2a", "F2b"]
TO = ["astra", "lead-formulation", "lead-audit"]

HERE = "artifacts/worker-094/cf21_rev13_recheck"
REPORT = f"{HERE}/run/report.json"
REPORT_SHA = "629a3232bb84fc8a77b60b782d6f6a3705e5277096d9391b3cb07abd97a0cea9"
DRIVER = f"{HERE}/run_cf21_rev13.py"
DRIVER_SHA = "bf57ff106264f15f3997decf87d828bb63f567e85b4784bee514bf35ea568fea"
README = f"{HERE}/README.md"
README_SHA = "5f0d872c4fccc849e3afc67d6a7b3da661c482a9ad873b6ebaa550e887c1e0e9"
MANIFEST = f"{HERE}/run/manifest.json"
MANIFEST_SHA = "21d273838fc930e6b4ce4848386a0221d8aab87d208a454909680f09a0fa0608"
PRIOR = "artifacts/worker-094/genericity_consistency/run/report.json"
PRIOR_SHA = "10a92ff3c9c1d4271a584b8fa6c79fe94ac505fcfe1db74189a256f76708f282"
CHECKER = "artifacts/worker-094/genericity_consistency/check_genericity_consistency.py"
CHECKER_SHA = "4adcfcbe98842c20d5ccaf236377e3bae3caccbdd1024c66956bf88ac887789c"

EVIDENCE = [
    f"{REPORT}#{REPORT_SHA[:12]}",
    f"{MANIFEST}#{MANIFEST_SHA[:12]}",
    f"{DRIVER}#{DRIVER_SHA[:12]}",
    f"{README}#{README_SHA[:12]}",
    f"{CHECKER}#{CHECKER_SHA[:12]}",
    f"{PRIOR}#{PRIOR_SHA[:12]}",
    "artifacts/formulation/FROZEN.json#815e08079aef",
    "research_map/formulation_taxonomy.yaml#0abb9ed8a961:393",
    "research_map/formulation_taxonomy.yaml#0abb9ed8a961:407",
    "research_map/formulation_taxonomy.yaml#0abb9ed8a961:414",
    "research_map/formulation_taxonomy.yaml#0abb9ed8a961:81",
]

FALSIFIER = (
    "Void on any pinned byte change (re-measure), on a control deviation, or on a live "
    "AF-WCC-SCALAR-SPH repair: declare a concrete/provisional genericity_kind with a binding "
    "schema (or an explicit provisional/blocked marker on the conclusion), clear or "
    "machine-readably block H4, and the declared checker 4adcfcbe9884 must return baseline PASS "
    "with 7/7 controls. A file rewrite alone is not a falsifier: the finding binds the sha256 "
    "values in report.json.inputs and must be re-run at any new bytes. The invariance sub-claim is "
    "falsified by any per-class finding differing from the rev12 report 10a92ff3c9c1d4 at the "
    "recorded rev13 pins."
)
NEXT_FALSIFIER = (
    "python3 artifacts/worker-094/cf21_rev13_recheck/run_cf21_rev13.py "
    "--out artifacts/worker-094/cf21_rev13_recheck/run/report.json ; exit 0 with "
    "CF21_LIVE_AT_REV13_INVARIANT re-confirms; baseline PASS + 7/7 controls voids CF-21; any "
    "pin change voids the invariance and requires re-pinning."
)


def artifact(event_id, artifact_type, path, sha, summary, bytes_=None, node_id="F0"):
    e = {
        "event_id": event_id,
        "event_type": "artifact",
        "created_at": NOW,
        "actor": ACTOR,
        "task_id": TASK,
        "class_id": CLASS_STR,
        "class_ids": CLASSES,
        "node_id": node_id,
        "node_ids": NODES,
        "gate": "G-F0",
        "artifact_type": artifact_type,
        "path": path,
        "sha256": sha,
        "validation_status": "unverified",
        "claims_completion": False,
        "summary": summary,
        "evidence_refs": EVIDENCE,
    }
    if bytes_ is not None:
        e["bytes"] = bytes_
    return e


def build():
    events = [
        artifact(
            f"w094f-cf21rev13-{STAMP}-artifact-report",
            "cf21_rev13_recheck_report", REPORT, REPORT_SHA,
            "CF-21 re-check report at live FROZEN rev29 pins: verdict "
            "CF21_LIVE_AT_REV13_INVARIANT; baseline FAIL with hard G2+G5 on AF-WCC-SCALAR-SPH only; "
            "7/7 declared controls PASS; 6/6 pins matched; no drift; per-class findings identical "
            "to the rev12-pinned run despite all three schemas moving rev12->rev13 and the "
            "taxonomy unchanged at 0abb9ed8a961. Advisory worker evidence, unverified.",
            bytes_=12784),
        artifact(
            f"w094f-cf21rev13-{STAMP}-artifact-driver",
            "cf21_rev13_recheck_instrument", DRIVER, DRIVER_SHA,
            "Re-check driver: imports the byte-identical declared CF-21 checker 4adcfcbe9884 "
            "(hash-gated, exit 5 on mismatch), applies its declared rules and 7 in-memory controls "
            "to the live pins, diffs per-class verdicts against the rev12-pinned report, and "
            "fail-closes on drift (exit 3) or pin mismatch (exit 4). Read-only on all pinned "
            "inputs; writes only under artifacts/worker-094/cf21_rev13_recheck/run/.",
            bytes_=13761),
        artifact(
            f"w094f-cf21rev13-{STAMP}-artifact-readme",
            "cf21_rev13_recheck_readme", README, README_SHA,
            "Task README: why the re-run exists (W094-GENERICITY-CONSISTENCY-01's declared "
            "next_falsifier), the eight measured pins, the result table, what the verdict does and "
            "does not say, the falsifier, and the authority note (no gate verdict, no node "
            "status, no canonical write).",
            bytes_=5676),
        artifact(
            f"w094f-cf21rev13-{STAMP}-artifact-manifest",
            "cf21_rev13_recheck_manifest", MANIFEST, MANIFEST_SHA,
            "sha256 manifest of the three deliverables, the pinned declared instrument "
            "4adcfcbe9884 and the six pinned inputs; carries the verdict, control status and "
            "drift record for one-glance audit.",
            bytes_=2570),
        {
            "event_id": f"w094f-cf21rev13-{STAMP}-claim",
            "event_type": "claim",
            "created_at": NOW,
            "actor": ACTOR,
            "task_id": TASK,
            "class_id": CLASS_STR,
            "class_ids": CLASSES,
            "node_id": "F0",
            "node_ids": NODES,
            "gate": "G-F0",
            "conclusion_type": "numerical_evidence",
            "statement": (
                "At the live FROZEN rev29 pins (FROZEN 815e08079aef, F1 rev13 d9cebb9404b2, F2a "
                "rev13 e9a27996dfd3, F2b rev13 b2ab6acb2bbe, F0 taxonomy 0abb9ed8a961, "
                "VOCAB_ALIASES 46cd9f1eb534; 6/6 pin match, 0 drift before/after), the declared "
                "CF-21 checker imported byte-identical at 4adcfcbe9884 returns baseline FAIL with "
                "hard failures G2 and G5 on AF-WCC-SCALAR-SPH only: axes.genericity_kind is "
                "'unresolved' (taxonomy:393) while conclusion.text asserts a comeager quantifier "
                "(:414) with no provisional/blocked marker, and hypothesis H4 (:407) is "
                "unresolved:true and states the genericity notion 'must be named before any claim "
                "is filed' with no machine-readable claim block; AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN "
                "and AF-SCC-C0-VAC-GEN PASS with only the shared soft G1b. All 7 declared controls "
                "behave as pre-registered. The per-class findings and the hard-rule set are "
                "identical to the rev12-pinned run (report 10a92ff3c9c1d4): taxonomy_unchanged="
                "true, all three schemas moved rev12->rev13, findings_identical=true. Therefore "
                "CF-21 -- the D3 record 'confirmed discharged for ALL FOUR classes' "
                "(taxonomy:81) is unsupported for AF-WCC-SCALAR-SPH, which has no binding F-node "
                "schema -- is invariant under the rev13 evidence-binding repair and remains live "
                "at the gate-relevant bytes. This is a declaration-level consistency measurement "
                "at pinned hashes, not a mathematical result, not a repair, and not a gate verdict."
            ),
            "assumptions": [
                "The declared checker 4adcfcbe9884 is the correct instrument for CF-21 and is imported without modification (the driver hash-gates it and exits 5 on mismatch).",
                "The rev12 reference report 10a92ff3c9c1d4 is the finding's own baseline; the invariance comparison presumes it is honest and is an exact structural equality of per_class dicts and hard-rule sets, not a byte-diff of schema content.",
                "The G-F0 pin 0abb9ed8a961 is the taxonomy the finding binds; any write to research_map/formulation_taxonomy.yaml voids G-F0 and this measurement with it.",
                "Worker events are advisory: the controller owns any G-F0/G-FORM transition and the disposition of CF-21.",
            ],
            "falsifier": FALSIFIER,
            "evidence_refs": EVIDENCE,
            "artifact_refs": [
                f"{REPORT}#{REPORT_SHA[:12]}",
                f"{MANIFEST}#{MANIFEST_SHA[:12]}",
                f"{DRIVER}#{DRIVER_SHA[:12]}",
                f"{README}#{README_SHA[:12]}",
            ],
        },
        {
            "event_id": f"w094f-cf21rev13-{STAMP}-review",
            "event_type": "review",
            "created_at": NOW,
            "actor": ACTOR,
            "to": TO,
            "task_id": TASK,
            "class_id": CLASS_STR,
            "class_ids": CLASSES,
            "node_id": "F0",
            "node_ids": NODES,
            "gate": "G-F0",
            "target_id": "CF21-genericity-consistency-094 (CF-21 @ FROZEN rev29)",
            "reviewer": ACTOR,
            "reviewed_artifact": REPORT,
            "reviewed_sha256": REPORT_SHA,
            "verdict": "accept",
            "score": 4.0,
            "hard_failures": [],
            "scope": (
                "CF-21 live-status at the FROZEN rev29 pins only; the declared instrument's own "
                "result re-measured on live bytes and diffed against its rev12 baseline. Not a "
                "gate verdict, not a full-schema review."
            ),
            "counts_as_full_schema_verdict": False,
            "findings": [
                "Re-measurement at live pins: baseline FAIL, hard G2+G5 on AF-WCC-SCALAR-SPH only, other three classes PASS (soft G1b shared); 7/7 controls as pre-registered; 6/6 pins matched; 0 drift.",
                "Invariance: taxonomy unchanged at 0abb9ed8a961 while all three schemas moved rev12->rev13 (d9cebb9404b2 / e9a27996dfd3 / b2ab6acb2bbe); per-class verdicts and hard-rule set byte-for-byte equal to the rev12-pinned report 10a92ff3c9c1d4.",
                "Consequence: CF-21 is not an artifact of superseded rev12 pins. It is an F0-taxonomy declaration inconsistency (axis + H4 vs conclusion) and not a G-FORM schema defect: F1/F2a/F2b all pass the genericity rules at rev13.",
                "Boundary: the instrument tests the F0 taxonomy axis against class conclusions; it does not re-adjudicate schema content and cannot certify or refute any mathematical statement.",
                "Decision surface for the controller: repair would require a taxonomy rev6, which voids G-F0 (0abb9ed8a961) and forces a full G-F0 re-run; a G-FORM promotion does not by itself resolve CF-21.",
            ],
            "next_falsifier": NEXT_FALSIFIER,
        },
        {
            "event_id": f"w094f-cf21rev13-{STAMP}-blocker",
            "event_type": "blocker",
            "created_at": NOW,
            "actor": ACTOR,
            "to": TO,
            "task_id": TASK,
            "class_id": CLASS_STR,
            "class_ids": CLASSES,
            "node_id": "F0",
            "node_ids": NODES,
            "gate": "G-F0",
            "description": (
                "CF-21 is re-confirmed live at the gate-relevant FROZEN rev29 bytes and cannot be "
                "repaired inside the current freeze: any write to research_map/formulation_taxonomy.yaml "
                "voids the G-F0 pass at 0abb9ed8a961. The D3 discharge record (taxonomy:81) "
                "overstates for AF-WCC-SCALAR-SPH, which has no binding F-node schema and whose "
                "axis/H4 contradict its own conclusion (G2+G5)."
            ),
            "needed_to_unblock": (
                "Controller decision: (a) commission a taxonomy rev6 repair of AF-WCC-SCALAR-SPH "
                "(name a concrete or provisional genericity_kind with a binding schema or an "
                "explicit provisional/blocked marker, and clear or machine-readably block H4) and "
                "re-run the full G-F0 checks, or (b) record explicit acceptance of residual CF-21 "
                "with a rationale. G-FORM promotion should not be read as resolving it."
            ),
            "expected_information_gain": (
                "Either repair path converts the D3 record from unsupported to machine-checkable, "
                "or the residual is accepted knowingly instead of being silently inherited."
            ),
            "evidence_refs": EVIDENCE,
        },
        {
            "event_id": f"w094f-cf21rev13-{STAMP}-status-complete",
            "event_type": "status",
            "created_at": NOW,
            "actor": ACTOR,
            "to": TO,
            "task_id": TASK,
            "class_id": CLASS_STR,
            "class_ids": CLASSES,
            "node_id": "F0",
            "node_ids": NODES,
            "gate": "G-F0",
            "status": "active",
            "hours": 0.4,
            "summary": (
                "W094F-CF21-REV13-RECHECK-01 complete at worker level (not a node done, not a gate "
                "verdict): one class-bound task taken from worker-094's own declared CF-21 "
                "next_falsifier; no inbox card. Imported the byte-identical declared checker "
                "(4adcfcbe9884) and re-ran it at the live FROZEN rev29 pins (6/6 matched, 0 "
                "drift): verdict CF21_LIVE_AT_REV13_INVARIANT -- baseline FAIL (G2+G5 on "
                "AF-WCC-SCALAR-SPH), 7/7 controls, findings identical to the rev12-pinned report "
                "10a92ff3c9c1d4 despite all three schemas moving rev12->rev13 and the taxonomy "
                "unchanged. 4 artifacts + claim + review + blocker emitted; checkpoint "
                "runtime/state/w094_cf21_rev13_checkpoint.json. No canonical write, no gate "
                "verdict, no node status; worker exits now."
            ),
            "evidence_refs": EVIDENCE,
            "next_falsifier": NEXT_FALSIFIER,
        },
    ]
    for e in events:
        schemas.validate_event(e)
    return events


def main() -> int:
    events = build()
    lines = [json.dumps(e, ensure_ascii=True) + "\n" for e in events]
    with OUTBOX.open("a") as fh:
        fh.writelines(lines)
    h = hashlib.sha256(OUTBOX.read_bytes()).hexdigest()
    print(json.dumps({
        "appended": len(events),
        "event_ids": [e["event_id"] for e in events],
        "outbox": str(OUTBOX),
        "outbox_sha256_after_append": h,
        "stamp": STAMP,
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
