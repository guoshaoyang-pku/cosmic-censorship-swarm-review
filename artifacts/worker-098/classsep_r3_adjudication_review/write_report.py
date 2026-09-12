#!/usr/bin/env python3
"""W098-CLASSSEP-ADJ-REVIEW-01: turn raw measurements into report.json + README.md."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
NOW = datetime.now().astimezone().isoformat(timespec="seconds")

ADJ = ROOT / "reviews/CLASSSEP-calibration-adjudication.json"
CF29 = ROOT / "runtime/state/controller_verification/cf29-detector-write-forensics.json"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    m = json.loads((HERE / "raw/measurements.json").read_text())
    pre = json.loads((HERE / "pre_registration.json").read_text())
    adj = json.loads(ADJ.read_text())
    arm_rows = {}
    for a, v in m["measured"].items():
        arm_rows[a] = {
            "corpus_a_27fixtures": v["corpus_a"],
            "corpus_c_sens_spec": f"{v['sens']} / {v['spec']}",
            "corpus_d_tp_fn_fp_tn": v["d"]["class_summary"],
            "corpus_d_cue_fn_high": v["d"]["cue_fn_high"],
            "corpus_e_battery": f"{v['e']['passed']}/{v['e']['total']}",
            "corpus_b_frozen_hard": v["hard"],
            "meets_adoption_bar": v["meets_bar"],
        }
    hard_failures: list = []
    findings = [
        "W098-ADJ-01 (info): 12/12 pre-registered expectations PASS. All four cited arms "
        "reproduce the adjudication exactly on all five corpora: corpus A 17/0/0/10 PASS x4; "
        "corpus C 4/6-3/10, 4/6-1/10, 5/6-1/10, 4/6-10/10; corpus D 30/1/6/2, 31/0/6/2, "
        "31/0/6/2, 20/11/2/6; corpus E 13/23, 11/23, 11/23, 23/23; frozen-map hard 19, 24, "
        "25, 1. 20/20 comparison cells match; no material discrepancy found.",
        "W098-ADJ-02 (info): decision (c) is forced by the measured bar, not by preference. No "
        "arm meets 27-fixture PASS AND sens>=5/6 AND spec>=9/10 AND 0 HIGH cue-FN AND 0 live "
        "metalinguistic findings. The 27-fixture corpus PASSes for every one of the six "
        "detector arms measured here, so it can gate adoption but cannot select an arm.",
        "W098-ADJ-03 (info): the attribution correction is confirmed. PROSEFIX dc8aa0de3869 "
        "carries 10 HIGH cue-induced false negatives (corpus D 20/11/2/6); STAGED e2d24b927ee8 "
        "carries 0 (31/0/6/2). The assignment card's '10/10 to e2d24b92' is wrong as stated; "
        "the r3 correction is measured and should stand in the ledger.",
        "W098-ADJ-04 (info): expanding the candidate pool does not defeat (c). The uncited "
        "fifth arm W098 v3 6f1a24c441fb passes the 27-fixture corpus and improves corpus C "
        "specificity to 9/10 over APPLIED's 3/10, but fails 5 HIGH cue-induced FN on corpus D "
        "and still has 1 hard finding on the frozen snapshot (claims[327]); not adoptable under "
        "the same bar.",
        "W098-ADJ-05 (info, controller action): CF-29 detector churn during the REC-22 freeze. "
        "research_map/class_separation.py moved a8c04fc3 -> e36b0d64 at 01:06:12 (one-line "
        "regex widening of the meta-quotation skip) and back to a8c04fc3 at 01:08:14, restored "
        "from worker-073's pinned copy. This independent review ran at the restored cited hash, "
        "as CF-29 intends. The unauthorized arm was also measured and fails the bar "
        "(corpus C spec 4/10, frozen hard 16, 1 HIGH cue-FN). CF-29 quarantine refs verify at "
        "their recorded sha256.",
        "W098-ADJ-06 (info, hygiene): reviewed-instrument durability. The adjudicated APPLIED "
        "bytes survived the churn only because worker-owned pinned copies existed "
        "(worker-032/056/073/...). The live path was rewritten twice within five minutes of the "
        "adjudication and the review harness had to bind a recovered copy. A controller-side "
        "read-only pin (or content-addressed store) for every reviewed instrument hash would "
        "make the next independent review reproducible without depending on a worker pin.",
        "W098-ADJ-07 (info, ledger): the 17 labeled-FP figure assumes claim-level label "
        "inheritance for multi-finding claims 112/192/276 (4 findings beyond the recorded label "
        "lists). A strict reading yields 13 labeled FP + 6 unlabeled findings. Both readings "
        "keep hard_total=19 and unlabeled claims [327,336]; the ledger should state the "
        "inheritance rule so classsep_hard_calibrated stays reproducible.",
        "W098-ADJ-08 (info): live-surface status at review close: detector a8c04fc3 (cited, "
        "restored), map 5ab4bed18107 with 414 claims (moved +31 after the frozen snapshot "
        "f344ed2aaea5/383), G-AUDIT pending, adjudication carries no gate verdict. Every live "
        "count is snapshot-bound exactly as the adjudication states.",
    ]
    report = {
        "schema": "worker-098/classsep-r3-adjudication-review/report/v1",
        "task_id": "W098-CLASSSEP-ADJ-REVIEW-01",
        "actor": "worker-098", "node_id": "A1", "gate": "G-AUDIT",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "created_at": NOW,
        "reviewed_artifact": {
            "path": "reviews/CLASSSEP-calibration-adjudication.json",
            "sha256": sha(ADJ), "revision": adj.get("revision"),
            "decision": adj["decision"]["choice"]},
        "verdict": "accept", "score": 4.5,
        "counts_as_independent": True, "counts_as_full_schema_verdict": False,
        "hard_failures": hard_failures,
        "findings": findings,
        "expectations": m["expectations"],
        "adjudication_reproduced": m["adjudication_reproduced"],
        "reproduction_cells": m["reproduction"],
        "arms": arm_rows,
        "cf29_forensics": m["cf29_forensics"],
        "conclusion": m["conclusion"],
        "no_gate_self_pass": "This review sets no gate verdict and no validation_status; it "
        "writes no canonical, proposed, schema, ledger or claim file. G-AUDIT remains pending.",
        "falsifier": "Re-run artifacts/worker-098/classsep_r3_adjudication_review/run_review.py "
        "at the pins in pre_registration.json: FALSIFIED if any cited-arm cell differs from the "
        "adjudication's census, if any of the 12 expectations flips, if a further detector write "
        "moves research_map/class_separation.py off a8c04fc31e4a before ingest, or if the "
        "restored copy stops matching the adjudication's APPLIED citation.",
        "evidence_refs": [
            "reviews/CLASSSEP-calibration-adjudication.json#7714ffd5b467",
            "artifacts/audit/classsep_r3_map_snapshot_20260912T010324.json#f344ed2aaea5",
            "artifacts/audit/classsep_r3_adjudication.py#fc92f4eac503",
            "artifacts/worker-032/classsep-prose-01/pinned/class_separation.a8c04fc31e4a.py",
            "artifacts/worker-049/classsep_fn_audit/pinned/class_separation_c266_recovered.py#c266dbceca87",
            "proposed/class_separation.py#e2d24b927ee8",
            "artifacts/worker-049/classsep_prose_fix/class_separation_prosefix.py#dc8aa0de3869",
            "artifacts/worker-049/classsep_fn_audit/corpus.json#9eb2ea9e2743",
            "artifacts/worker-049/classsep_prose_fix/worker035_controls.json",
            "artifacts/worker-07/class_separation_falsification/results.json#d69ad58468be",
            "artifacts/audit/classsep_calibration.py",
            "artifacts/worker-098/classsep_mention_scope/candidate_class_separation.v3.py#6f1a24c441fb",
            "runtime/state/controller_verification/cf29-detector-write-forensics.json#b573dcfdcc20",
            "artifacts/worker-098/classsep_r3_adjudication_review/raw/measurements.json",
            "artifacts/worker-098/classsep_r3_adjudication_review/pre_registration.json",
            "artifacts/worker-098/classsep_r3_adjudication_review/run_review.py",
        ],
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=2) + "\n")

    rows = "\n".join(
        f"| {a} | {v['corpus_a_27fixtures']} | {v['corpus_c_sens_spec']} | "
        f"{v['corpus_d_tp_fn_fp_tn']} | {v['corpus_d_cue_fn_high']} | {v['corpus_e_battery']} | "
        f"{v['corpus_b_frozen_hard']} | {'no' if not v['meets_adoption_bar'] else 'YES'} |"
        for a, v in arm_rows.items())
    readme = f"""# W098-CLASSSEP-ADJ-REVIEW-01 — independent review of the r3 CLASSSEP adjudication

Verdict: **accept 4.5** on `reviews/CLASSSEP-calibration-adjudication.json` (r3-life06,
decision c), reviewed at sha256 `{sha(ADJ)[:12]}` and the frozen pins in
`pre_registration.json`. No gate verdict, no canonical write, no claim retirement.

Method: re-derived the four-arm census with a worker-098 harness (`run_review.py`) instead of
the audit harness, over the same hash-pinned corpora, plus two extra arms (W098 v3, CF-29
unauthorized bytes). 12/12 pre-registered expectations PASS; all 20 per-arm corpus cells
reproduce the adjudication exactly.

| arm | corpus A (27) | corpus C sens/spec | corpus D tp/fn/fp/tn | D cue-FN HIGH | battery E | frozen-map hard | bar |
|---|---|---|---|---|---|---|---|
{rows}

- **Decision (c) supported.** No arm meets 27-fixture PASS + sens >= 5/6 + spec >= 9/10 +
  0 HIGH cue-FN + 0 live metalinguistic findings. The 27-fixture corpus PASSes for all six
  arms, so it cannot license an adoption.
- **Attribution correction confirmed:** the 10 HIGH cue-FN belongs to PROSEFIX
  `dc8aa0de3869`, not to STAGED `e2d24b927ee8` (0 cue-FN).
- **Fifth arm does not change the decision:** W098 v3 `6f1a24c441fb` improves corpus C
  specificity to 9/10 but fails 5 HIGH cue-FN and still has 1 hard finding on the frozen
  snapshot (claims[327]).
- **CF-29 churn recorded:** detector a8c04fc3 -> e36b0d64 (01:06:12) -> a8c04fc3 (01:08:14,
  restored from worker-073's pin). The review ran at the restored cited hash; the
  unauthorized arm also fails the bar. Quarantine refs verify.
- **Residual live count:** 19 hard on frozen snapshot f344ed2aaea5 = 17 labeled metalinguistic
  FP + 2 unlabeled DETECTOR_SELF meta-claims (claims[327],[336]). Live map at review close
  5ab4bed18107 / 414 claims, so all live counts are snapshot-bound.

Falsifier: re-run `run_review.py` at the pins; falsified if any cited-arm cell differs, any
expectation flips, or a further write moves the detector off a8c04fc31e4a.
"""
    (HERE / "README.md").write_text(readme)
    print("wrote report.json", sha(HERE / "report.json")[:12])
    print("wrote README.md", sha(HERE / "README.md")[:12])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
