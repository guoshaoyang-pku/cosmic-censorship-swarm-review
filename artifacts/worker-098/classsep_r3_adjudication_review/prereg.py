#!/usr/bin/env python3
"""W098-CLASSSEP-ADJ-REVIEW-01 pre-registration.

Writes pre_registration.json: every pin this review binds to, plus expectations
E1-E12 fixed BEFORE any acceptance measurement is taken. Read-only on canonical.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
NOW = datetime.now().astimezone().isoformat(timespec="seconds")

PINS = {
    "adjudication": "reviews/CLASSSEP-calibration-adjudication.json",
    "adjudication_superseded": "reviews/CLASSSEP-calibration-adjudication-l05-superseded.json",
    "frozen_map_snapshot": "artifacts/audit/classsep_r3_map_snapshot_20260912T010324.json",
    "adjudication_tool": "artifacts/audit/classsep_r3_adjudication.py",
    "calibration_module": "artifacts/audit/classsep_calibration.py",
    "arm_APPLIED": "research_map/class_separation.py",
    "arm_PRE": "artifacts/worker-049/classsep_fn_audit/pinned/class_separation_c266_recovered.py",
    "arm_STAGED": "proposed/class_separation.py",
    "arm_PROSEFIX": "artifacts/worker-049/classsep_prose_fix/class_separation_prosefix.py",
    "arm_W098_V3": "artifacts/worker-098/classsep_mention_scope/candidate_class_separation.v3.py",
    "corpus_a_worker07_results": "artifacts/worker-07/class_separation_falsification/results.json",
    "corpus_a_worker07_dir": "artifacts/worker-07/class_separation_falsification/fixtures",
    "corpus_d_worker049": "artifacts/worker-049/classsep_fn_audit/corpus.json",
    "corpus_e_worker035": "artifacts/worker-049/classsep_prose_fix/worker035_controls.json",
    "canonical_detector": "research_map/class_separation.py",
    "canonical_map": "research_map/research_map.json",
    "frozen_manifest": "artifacts/formulation/FROZEN.json",
}

EXPECTATIONS = [
    {"id": "E1", "claim": "every cited path exists and its sha256 matches the adjudication's "
     "detectors / frozen_map_snapshot block and the outbox artifact events",
     "falsified_if": "any cited hash differs from the bytes on disk"},
    {"id": "E2", "claim": "corpus A (worker-07, 27 fixtures): all four cited arms PASS 17/0/10/0",
     "falsified_if": "any arm has fn>0 or fp>0"},
    {"id": "E3", "claim": "corpus C (16 labeled assertion/mention fixtures): APPLIED 4/6 sens "
     "3/10 spec; PRE 4/6, 1/10; STAGED 5/6, 1/10; PROSEFIX 4/6, 10/10",
     "falsified_if": "any per-arm tp/fn/fp/tn differs from the adjudication"},
    {"id": "E4", "claim": "corpus D (worker-049, 39 fixtures incl. 12 adversarial/twin pairs): "
     "APPLIED 30/1/6/2 with exactly 1 HIGH cue-induced FN (A04); PRE 31/0/6/2; "
     "STAGED 31/0/6/2; PROSEFIX 20/11/2/6 with 10 HIGH cue-induced FN",
     "falsified_if": "any aggregate class count or the HIGH cue-FN arm differs"},
    {"id": "E5", "claim": "corpus E (worker-035, 23 controls): APPLIED 13/23, PRE 11/23, "
     "STAGED 11/23, PROSEFIX 23/23",
     "falsified_if": "any pass count differs"},
    {"id": "E6", "claim": "corpus B on the FROZEN snapshot f344ed2aaea5: APPLIED hard 19 "
     "(17 labeled FP + 2 unlabeled claims[327],[336]); PRE 24; STAGED 25; PROSEFIX 1",
     "falsified_if": "any hard total differs or the unlabeled indices are not 327/336"},
    {"id": "E7", "claim": "no cited arm meets the declared adoption bar; decision (c) follows "
     "from the measured census alone", "falsified_if": "some arm meets all five bar clauses"},
    {"id": "E8", "claim": "the fifth (uncited) arm W098 v3 6f1a24c441fb also fails the bar: "
     "expected corpus A PASS, corpus C 6/6-10/10 or close, corpus D ~31/0/6/2, "
     "frozen-snapshot hard 1 at claims[327] (live_metalinguistic=0 fails), so decision (c) "
     "is robust to expanding the candidate pool",
     "falsified_if": "v3 meets all five bar clauses (this would defeat decision c)"},
    {"id": "E9", "claim": "no canonical/proposed/schema file was written by the adjudication: "
     "detector a8c04fc3, PRE c266dbec, STAGED e2d24b92 unchanged; FROZEN.json pins unchanged",
     "falsified_if": "any canonical hash differs from the cited/review-start bytes"},
    {"id": "E10", "claim": "the adjudication sets no gate verdict and no validation_status; "
     "G-AUDIT is still pending in the live map at review time",
     "falsified_if": "the adjudication carries a gate verdict or the map shows G-AUDIT != pending"},
    {"id": "E11", "claim": "the FN attribution correction is right: the 10-HIGH cue-FN belongs "
     "to PROSEFIX dc8aa0de3869, not to STAGED e2d24b92 (0 cue-FN)",
     "falsified_if": "STAGED shows >=1 HIGH cue-induced FN or PROSEFIX shows <10"},
    {"id": "E12", "claim": "the live map is a moving surface: at review time it is a different "
     "hash/more claims than the frozen snapshot, so every live count is snapshot-bound",
     "falsified_if": "the live map equals f344ed2aaea5 at review close (then the growth "
     "addendum is stale, not wrong)"},
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else "ABSENT"


def main() -> int:
    pins = {}
    for k, rel in PINS.items():
        p = ROOT / rel
        if p.is_dir():
            h = hashlib.sha256()
            for f in sorted(x for x in p.rglob("*") if x.is_file()):
                h.update(f.relative_to(ROOT).as_posix().encode())
                h.update(f.read_bytes())
            pins[k] = {"path": rel, "kind": "dir-merkle", "sha256": h.hexdigest()}
        else:
            pins[k] = {"path": rel, "kind": "file", "sha256": sha(p)}
    out = {
        "schema": "worker-098/classsep-r3-adjudication-review/v1",
        "task_id": "W098-CLASSSEP-ADJ-REVIEW-01",
        "actor": "worker-098",
        "node_id": "A1",
        "gate": "G-AUDIT",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "purpose": "Independent read-only review of reviews/CLASSSEP-calibration-adjudication.json "
                   "(r3-life06, decision c) at the frozen hashes: re-derive the four-arm census "
                   "with a worker-098 harness instead of the audit harness, test the adoption bar, "
                   "run a fifth uncited arm (W098 v3), and check the no-write / no-gate-pass "
                   "claims. Sets no gate verdict and writes no canonical file.",
        "created_at": NOW,
        "review_started_at": NOW,
        "pins": pins,
        "expectations_written_before_measurement": EXPECTATIONS,
        "falsifier_of_this_review": "Any cited hash not matching on disk; any per-arm census "
            "differing materially from the adjudication; or W098 v3 meeting all five adoption-bar "
            "clauses (which would defeat decision c).",
    }
    dest = HERE / "pre_registration.json"
    dest.write_text(json.dumps(out, indent=2) + "\n")
    print(f"wrote {dest.relative_to(ROOT)}")
    print(f"sha256={sha(dest)}")
    for k, v in pins.items():
        print(f"  {k:<28} {v['sha256'][:16]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
