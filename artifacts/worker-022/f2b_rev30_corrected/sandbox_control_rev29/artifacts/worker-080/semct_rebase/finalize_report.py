#!/usr/bin/env python3
"""Annotate the raw harness report with the probe-B root cause. Measurements untouched."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


raw = HERE / "report.json"
raw_copy = HERE / "report_raw_harness.json"
if not raw_copy.exists():
    shutil.copy2(raw, raw_copy)
rep = json.loads(raw_copy.read_text())
probe = json.loads((HERE / "r03_probe_report.json").read_text())
rep["annotation"] = {
    "annotated_by": "worker-080",
    "note": ("Raw harness measurements are untouched (report_raw_harness.json). This section "
             "resolves the two falsified R2 rows; the R3a/R3b/R4/R5 rows were met as registered."),
    "raw_harness_report_sha256": sha(raw_copy),
    "probe_report_sha256": sha(HERE / "r03_probe_report.json"),
    "falsified_rows": rep["expectation_failures"],
    "root_cause": probe["conclusion"],
    "probe_expectations_met": probe["expectations_met"],
    "task_question_answered": (
        "ADJ-CONTROL-STALENESS: YES, resolvable mechanically. After only the three canonical "
        "pin rebinds plus two minimal comment-preserving control edits (delete the duplicated "
        "finite_codimension_complement -> residual_comeager row from transfer_failures; delete "
        "the now-unknown revised_at_unused key), 3/3 frozen controls are accepted by all three "
        "stages (R2, R5) with the 32-mutant corpus byte-untouched and identical mutant counts. "
        "R3a/R3b show each edit is necessary; R4 shows the structural gate still rejects the "
        "stale row when re-inserted."),
    "remaining_blocker_after_rebase": (
        "valid_for_calibration is still false at FROZEN rev28 for an independent reason: the "
        "conforming-canonical control SCT-K03 (schemas/af_wcc_vacuum.yaml, cce9c601, rev12) is "
        "rejected by both semantic stages on R03 because the literal binder token '(q,t0)' does "
        "not occur in quantifiers.formal, which spells the pair out as 'q in I+ and t0 in [0,T)'. "
        "Probe B shows this is lexical, not semantic: rev11 (binder 'q') and the pre-rev11 "
        "snapshot are accepted, a notation-only rewrite to the D5-relative form clears R03 with "
        "every other check unchanged, and a scratch absent-token mutant still fails R03. The "
        "binding structural gate passes rev12. The runner's validity.blocking_adjudication list "
        "is empty in this case, so the failure is not routed to any named adjudication item "
        "(runner gap: only the frozen-control basis is named there)."),
    "owner_routing": {
        "ADJ-CONTROL-STALENESS implementation": "astra-lead-formulation (adopt patch or pin gate revision)",
        "canonical F1 rev12 R03 lexical false positive": "astra-lead-formulation (authoring) + lead-audit (checker calibration); CF-4 policy: checker flags, never authors",
        "runner blocking_adjudication gap": "lead-audit / suite owner deepseek-flash-06",
    },
}
(HERE / "report.json").write_text(json.dumps(rep, indent=1) + "\n")
print(json.dumps({"annotated": True, "raw_sha256": sha(raw_copy),
                  "final_sha256": sha(HERE / "report.json"),
                  "task_question_answered": True,
                  "expectations_met_raw": rep["expectations_met"]}, indent=1))
