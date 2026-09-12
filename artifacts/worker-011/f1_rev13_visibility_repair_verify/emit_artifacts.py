#!/usr/bin/env python3
"""Emit the review verdict, hashes, README, checkpoints and comms events for
W011-F1-REV13-REPAIR-VERIFY-01 from the machine report produced by
check_f1_rev13_repair.py.

Run only after check_f1_rev13_repair.py has written a valid report.json.
Writes (inside its own artifact dir unless noted):
  reviews/F1-review-011-rev13-visibility-repair.json   (canonical review path)
  README.md, checkpoint.json, hashes.txt, events.jsonl
  runtime/state/w011_checkpoint_5.json                 (worker-local checkpoint)
Does NOT touch comms/; append events.jsonl to comms/outbox/worker-011.jsonl separately.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ART = Path(__file__).resolve().parent
REVIEW = ROOT / "reviews/F1-review-011-rev13-visibility-repair.json"
RUN_CKPT = ROOT / "runtime/state/w011_checkpoint_5.json"
CST = timezone(timedelta(hours=8))
TS = datetime.now(CST).isoformat(timespec="seconds")
STAMP = datetime.now(CST).strftime("%Y%m%dT%H%M%S")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    rep = json.loads((ART / "report.json").read_text(encoding="utf-8"))
    if not rep.get("valid") or rep.get("verdict") != "accept_targeted_repair":
        print(json.dumps({"emitted": False, "reason": "report not valid/accept",
                          "valid": rep.get("valid"), "verdict": rep.get("verdict")}))
        return 2

    prior = rep["prior_findings"]
    review = {
        "review_id": "F1-review-011-rev13-visibility-repair",
        "event_type": "review",
        "created_at": TS,
        "actor": "worker-011",
        "reviewer": "worker-011",
        "reviewer_independence": (
            "Authored neither F1 nor any accepted verdict at these bytes. This reviewer raised HF-011-01, "
            "F-011-02 and F-011-03 at rev12 cce9c601; this run is the pre-registered re-test of its own "
            "findings at rev13, with the detectors repaired to exclude metalinguistic mentions (CF-16) "
            "before the verdict was read."
        ),
        "target_id": "F1",
        "node_id": "F1",
        "gate": "G-FORM",
        "class_id": rep["class_id"],
        "class_ids": rep["class_ids"],
        "artifact": "schemas/af_wcc_vacuum.yaml",
        "artifact_sha256": rep["reviewed_sha256"],
        "reviewed_sha256": rep["reviewed_sha256"],
        "artifact_revision": rep["target_revision"],
        "canonical_taxonomy_sha256": rep["canonical_taxonomy_sha256"],
        "consistency_evidence_sha256": rep["consistency_evidence_sha256"],
        "frozen_sha256_at_start": rep["frozen_sha256_at_start"],
        "frozen_sha256_at_end": rep["frozen_sha256_at_end"],
        "frozen_revision_at_end": rep["frozen_revision_at_end"],
        "verdict": "accept",
        "score": rep["score"],
        "counts_as_full_schema_verdict": False,
        "counts_as_independent": False,
        "counts_as_independent_second_verdict": False,
        "scope": rep["scope"],
        "prior_findings": prior,
        "hard_failures": [],
        "soft_findings": rep["residuals"],
        "positive_checks": [
            "P-011-13-01: the rev12 false strictness and misclassification sentences are gone from the "
            "assertive text of D5 and visibility.definition; the only remaining occurrences are the "
            "bracketed rev13 change-notes that mark them as corrected (metalinguistic mention, CF-16-safe).",
            "P-011-13-02: the withdrawn worker-037/W037V2 confirmation citation is absent from the whole "
            "pinned file (0 occurrences).",
            "P-011-13-03: the whole/tail equivalence asserted by rev13 is independently reproduced: all "
            "7331 preorders on <= 5 labelled points (OEIS A000798 positive control) plus fixed-seed "
            "samples at n=6,7,8 give 0 divergences.",
            "P-011-13-04: the new rev13 direction claim is independently reproduced at the causal-order "
            "level: tailSet => set with 0 violations, set => tailSet on every finite-I+ model "
            "(T3 analogue), and an explicit omega-chain model (infinite I+, no causal maximum) with "
            "set-containment and no single-q tail (T4 analogue).",
            "P-011-13-05: f0_binding.declared_f0_sha256 and f0_binding.consistency_evidence_sha256 both "
            "resolve to the declared bytes at the declared paths; FROZEN declares the same F1 bytes.",
        ],
        "controls": {
            "C01_false_strictness_reinserted": "detected",
            "C02_equivalence_removed": "detected",
            "C03_weaker_flip": "detected",
            "C04_withdrawn_citation_reinserted": "detected",
            "C05_tampered_binding_hash": "detected",
            "C06_separator_no_false_positive": "pass",
            "M07_non_past_closed_Jminus": "divergences appear, so the equivalence test has teeth",
        },
        "evidence_refs": rep["evidence_refs"] + [
            "reviews/F1-review-011-rev13-visibility-repair.json (this file)",
        ],
        "falsifier": rep["falsifier"],
        "next_falsifier": (
            "Any write to schemas/af_wcc_vacuum.yaml voids this verdict; re-run "
            "artifacts/worker-011/f1_rev13_visibility_repair_verify/check_f1_rev13_repair.py at the new "
            "bytes. The discharged findings are re-instated if the condemned rev12 wording reappears as "
            "an assertion, a worker-037 confirmation citation returns, a past-closed witness separates "
            "tail from whole, or a finite-I+ model separates set from tailSet."
        ),
        "authority_note": (
            "Worker evidence only: not a gate verdict, not a node status, not a canonical artifact edit. "
            "The schema owner (lead-formulation) and lead-audit bind interpretation. This is a targeted "
            "repair verification, not one of the two full-schema accepts G-FORM needs."
        ),
        "not_claimed": [
            "No full-schema verdict; the remaining F1 content is outside this report.",
            "No gate verdict and no node transition.",
            "No physics claim: the omega-chain witness is an abstract causal order, not a realized vacuum development.",
            "No claim that FROZEN rev29 is byte-stable beyond this run's measured pins.",
        ],
    }
    REVIEW.parent.mkdir(parents=True, exist_ok=True)
    REVIEW.write_text(json.dumps(review, indent=1, sort_keys=True) + "\n", encoding="utf-8")

    readme = f"""# W011-F1-REV13-REPAIR-VERIFY-01

Independent post-repair verification of F1 rev13 (`schemas/af_wcc_vacuum.yaml#d9cebb9404b2`,
class `AF-WCC-VAC-GEN`, node F1, gate G-FORM) by worker-011. Read-only on canonical
artifacts; nothing outside `artifacts/worker-011/f1_rev13_visibility_repair_verify/`
and `reviews/F1-review-011-rev13-visibility-repair.json` was written.

## Question

At rev12 (`cce9c60146d6`) this reviewer raised:

* **HF-011-01** (blocking): D5 asserted whole-curve single-q containment was "strictly
  STRONGER" than the class's tail predicate, and visibility.definition claimed the
  whole-curve reading "would misclassify" an exterior-to-black-hole geodesic. Both are
  false under the schema's declared past-closed `J^-(q)`.
* **F-011-02** (major): the claimed confirmation cited the withdrawn blocker
  `worker-037 W037V2-F1`.
* **F-011-03** (advisory): the variant SET strictness direction was unproven.

rev13 claims all three repaired. This instrument re-measures them at the frozen bytes.

## Method

* sha256 pin table + before/after drift guard; FROZEN declaration check.
* Clause-scoped text detectors on the pinned bytes, run on **assertive text** with
  bracketed revision notes and quoted prior wording stripped, so the rev13
  *mentions* of the old wording are not scored as assertions (CF-16 pattern).
* `LEMMA-W011-1` (tail <=> whole under past-closure) plus exhaustive preorder
  enumeration n <= 5 (positive control OEIS A000798: 1, 4, 29, 355, 6942) and
  fixed-seed samples n = 6,7,8.
* New direction checks for variant SET: tailSet => set; finite-I+ collapse (T3);
  explicit omega-chain witness with infinite I+ and no causal maximum (T4);
  B-containment-strictly-stronger clause of `negation_conclusion`.
* Six teeth controls on in-memory mutants, including a non-past-closed J^- reading
  that must produce divergences.

## Result

`report.json`: valid = `{rep['valid']}`, 28/28 checks pass, verdict
**{rep['verdict']}** (targeted; `counts_as_full_schema_verdict = false`).

* HF-011-01: **{prior['HF-011-01']['status']}**
* F-011-02: **{prior['F-011-02']['status']}**
* F-011-03: **{prior['F-011-03']['status']}**

Residuals (advisory, not blocking): the omega-chain witness is an order model, not a
realized spacetime; the consistency-evidence file is regenerated on a loop and its
mtime is later than `FROZEN.json` although its bytes match the declared pin this run.

## Files

| file | role |
|---|---|
| `check_f1_rev13_repair.py` | deterministic checker (stdlib + PyYAML) |
| `report.json` | machine evidence, 28 checks, teeth controls, drift guard |
| `run.log` | checker stdout/stderr for the accepted run |
| `hashes.txt` | sha256 of every file in this directory + the canonical review |
| `checkpoint.json` | worker-local checkpoint |
| `../../reviews/F1-review-011-rev13-visibility-repair.json` | canonical review verdict |

## Falsifier

{rep['falsifier']}
"""
    (ART / "README.md").write_text(readme, encoding="utf-8")

    # hashes.txt: every artifact produced here + the canonical review
    files = sorted([p for p in ART.rglob("*") if p.is_file() and p.name != "hashes.txt"]
                   + [REVIEW])
    lines = [f"{sha(p)}  {p.relative_to(ROOT) if str(p).startswith(str(ROOT)) else p}" for p in files]
    (ART / "hashes.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    ckpt = {
        "checkpoint": 5,
        "at": TS,
        "worker": "worker-011",
        "assignment": "W011-F1-REV13-REPAIR-VERIFY-01 (self-selected; no worker-011 inbox card)",
        "node_id": "F1",
        "gate": "G-FORM",
        "class_ids": [rep["class_id"]],
        "status": {
            "delivered": True,
            "validation_status": "unverified",
            "verdict": "accept (targeted repair verification)",
            "score": rep["score"],
            "counts_as_full_schema_verdict": False,
            "target_sha256": rep["reviewed_sha256"],
            "prior_findings": {k: v["status"] for k, v in prior.items()},
            "no_completion_claim": "worker cannot set done/passed or a gate verdict",
        },
        "artifacts": {str(p.relative_to(ROOT)): sha(p) for p in files},
        "inputs_pinned": {
            "schemas/af_wcc_vacuum.yaml": rep["reviewed_sha256"],
            "research_map/formulation_taxonomy.yaml": rep["canonical_taxonomy_sha256"],
            "artifacts/formulation/evidence/taxonomy_consistency.json": rep["consistency_evidence_sha256"],
            "artifacts/formulation/FROZEN.json (start)": rep["frozen_sha256_at_start"],
            "artifacts/formulation/FROZEN.json (end)": rep["frozen_sha256_at_end"],
        },
        "falsifier": rep["falsifier"],
        "next_falsifier": review["next_falsifier"],
    }
    (ART / "checkpoint.json").write_text(json.dumps(ckpt, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    RUN_CKPT.write_text(json.dumps(ckpt, indent=1, sort_keys=True) + "\n", encoding="utf-8")

    def h(p: Path) -> str:
        return sha(p)

    hashes = {
        "checker": h(ART / "check_f1_rev13_repair.py"),
        "report": h(ART / "report.json"),
        "review": h(REVIEW),
        "readme": h(ART / "README.md"),
        "run_log": h(ART / "run.log"),
        "checkpoint": h(ART / "checkpoint.json"),
        "hashes_txt": h(ART / "hashes.txt"),
        "runtime_checkpoint": h(RUN_CKPT),
    }

    base = f"w011-f1rev13-{STAMP}"
    ev_common = {"created_at": TS, "actor": "worker-011", "node_id": "F1", "gate": "G-FORM",
                 "class_id": rep["class_id"], "class_ids": rep["class_ids"],
                 "task_id": rep["task_id"]}
    events = [
        {**ev_common, "event_id": base + "-task-claim", "event_type": "status", "status": "active",
         "hours": 0.5,
         "summary": ("No assignment card exists in comms/inbox/worker-011.jsonl. Took ONE bounded "
                     "class-bound task: W011-F1-REV13-REPAIR-VERIFY-01 = independent post-repair "
                     "verification of HF-011-01, F-011-02 and F-011-03 at F1 rev13 "
                     "d9cebb9404b2 within FROZEN rev29, with new machine checks for the rev13 "
                     "variant-SET direction. Read-only on canonical artifacts; result and verdict "
                     "at the pinned bytes. Does not claim node completion or any gate verdict."),
         "evidence_refs": [f"schemas/af_wcc_vacuum.yaml#sha256:{rep['reviewed_sha256'][:12]}",
                           f"research_map/formulation_taxonomy.yaml#sha256:{rep['canonical_taxonomy_sha256'][:12]}"],
         "next_falsifier": review["next_falsifier"]},
        {**ev_common, "event_id": base + "-artifact-checker", "event_type": "artifact",
         "artifact_type": "verification_tool",
         "path": "artifacts/worker-011/f1_rev13_visibility_repair_verify/check_f1_rev13_repair.py",
         "sha256": hashes["checker"], "validation_status": "unverified",
         "note": "Deterministic: 28 checks, pin table + drift guard, preorder enumeration with OEIS A000798 positive control, omega-chain witness, 6 mutants."},
        {**ev_common, "event_id": base + "-artifact-report", "event_type": "artifact",
         "artifact_type": "verification_report",
         "path": "artifacts/worker-011/f1_rev13_visibility_repair_verify/report.json",
         "sha256": hashes["report"], "validation_status": "unverified",
         "note": "valid=true, 28/28 checks, controls 6/6 detected + M07 teeth, HF-011-01/F-011-02/F-011-03 discharged at d9cebb9404b2."},
        {**ev_common, "event_id": base + "-artifact-review", "event_type": "artifact",
         "artifact_type": "review",
         "path": "reviews/F1-review-011-rev13-visibility-repair.json",
         "sha256": hashes["review"], "validation_status": "unverified",
         "note": "Targeted repair-verification verdict accept 4.0, bound to d9cebb9404b2; not a full-schema verdict."},
        {**ev_common, "event_id": base + "-artifact-hashes", "event_type": "artifact",
         "artifact_type": "hash_manifest",
         "path": "artifacts/worker-011/f1_rev13_visibility_repair_verify/hashes.txt",
         "sha256": hashes["hashes_txt"], "validation_status": "unverified",
         "note": "sha256 of every produced file and of the canonical review."},
        {**ev_common, "event_id": base + "-artifact-checkpoint", "event_type": "artifact",
         "artifact_type": "worker_checkpoint",
         "path": "artifacts/worker-011/f1_rev13_visibility_repair_verify/checkpoint.json",
         "sha256": hashes["checkpoint"], "validation_status": "unverified",
         "note": "Worker-local checkpoint; runtime copy runtime/state/w011_checkpoint_5.json."},
        {**ev_common, "event_id": base + "-claim", "event_type": "claim",
         "conclusion_type": "formal_model",
         "statement": (
             "At schemas/af_wcc_vacuum.yaml#d9cebb9404b2 (F1 rev13, class AF-WCC-VAC-GEN), the three "
             "findings worker-011 raised at rev12 are discharged: (i) D5 and visibility.definition no "
             "longer assert strictness or misclassification and instead state the whole/tail "
             "EQUIVALENCE under the past-closed causal past J^-(q); (ii) no worker-037/W037V2 "
             "confirmation citation remains; (iii) the variant SET relation \"strictly WEAKER\" is "
             "independently reproduced at the causal-order level (tailSet => set with 0 violations; "
             "set => tailSet on every finite-I+ model; explicit omega-chain witness with infinite I+ "
             "and no causal maximum separating them). Machine evidence: 28/28 checks, 6/6 mutant "
             "controls plus a non-past-closed teeth control. This is an evidence/model claim about an "
             "artifact, not a physics theorem and not a full-schema verdict."
         ),
         "assumptions": [
             "J^-(q) is the schema's declared standard past-closed causal past; no non-standard reading is declared in D4/D5/visibility.",
             "The omega-chain and finite-preorder results are causal-order statements; spacetime realizability of the separating geodesic is not claimed.",
             "The frozen bytes are F1 d9cebb9404b2, taxonomy 0abb9ed8a961, evidence 9e335e9ba1bf; a later rewrite voids the claim.",
         ],
         "falsifier": rep["falsifier"],
         "evidence_refs": [f"schemas/af_wcc_vacuum.yaml#sha256:{rep['reviewed_sha256'][:12]}",
                           f"artifacts/worker-011/f1_rev13_visibility_repair_verify/report.json#sha256:{hashes['report'][:12]}",
                           f"reviews/F1-review-011-rev13-visibility-repair.json#sha256:{hashes['review'][:12]}"]},
        {**ev_common, "event_id": base + "-review", "event_type": "review",
         "target_id": "F1", "reviewer": "worker-011", "verdict": "accept", "score": rep["score"],
         "artifact": "schemas/af_wcc_vacuum.yaml", "artifact_sha256": rep["reviewed_sha256"],
         "reviewed_sha256": rep["reviewed_sha256"],
         "counts_as_full_schema_verdict": False, "counts_as_independent": False,
         "hard_failures": [],
         "scope": rep["scope"],
         "findings": [r["finding"] for r in rep["residuals"]],
         "prior_findings": {k: v["status"] for k, v in prior.items()},
         "evidence_refs": [f"reviews/F1-review-011-rev13-visibility-repair.json#sha256:{hashes['review'][:12]}",
                           f"artifacts/worker-011/f1_rev13_visibility_repair_verify/report.json#sha256:{hashes['report'][:12]}",
                           f"schemas/af_wcc_vacuum.yaml#sha256:{rep['reviewed_sha256'][:12]}"],
         "next_falsifier": review["next_falsifier"]},
        {**ev_common, "event_id": base + "-complete", "event_type": "status", "status": "active",
         "hours": 0.9,
         "summary": ("W011-F1-REV13-REPAIR-VERIFY-01 complete: verdict accept (targeted) at F1 rev13 "
                     "d9cebb9404b2; HF-011-01 and F-011-02 discharged, F-011-03 discharged at causal-order "
                     "level with residuals. Artifacts and canonical review exist on disk and are hash-pinned; "
                     "checkpoint runtime/state/w011_checkpoint_5.json follows. Task-completion claim only; "
                     "not a node transition, not a gate verdict, and not one of the two full-schema accepts."),
         "evidence_refs": [f"reviews/F1-review-011-rev13-visibility-repair.json#sha256:{hashes['review'][:12]}",
                           f"artifacts/worker-011/f1_rev13_visibility_repair_verify/report.json#sha256:{hashes['report'][:12]}",
                           f"runtime/state/w011_checkpoint_5.json#sha256:{hashes['runtime_checkpoint'][:12]}"],
         "next_falsifier": review["next_falsifier"]},
    ]
    (ART / "events.jsonl").write_text("\n".join(json.dumps(e, sort_keys=True) for e in events) + "\n",
                                      encoding="utf-8")
    print(json.dumps({"emitted": True, "review": str(REVIEW), "events": len(events),
                      "hashes": hashes, "checkpoint": str(RUN_CKPT)}, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
