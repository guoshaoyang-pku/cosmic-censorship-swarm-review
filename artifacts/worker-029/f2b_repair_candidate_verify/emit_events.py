#!/usr/bin/env python3
"""W029 F2b repair-candidate verification: package evidence, emit protocol events, checkpoint.

Read-only on every canonical path. Worker events cannot set status=done, validation_status=passed
or any gate verdict.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "research_map"))
import schemas  # noqa: E402

TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ).isoformat(timespec="seconds")
STAMP = datetime.now(TZ).strftime("%Y%m%dT%H%M%S")
PREFIX = f"w029r7-{STAMP}"

CANON = {
    "c0_live": "schemas/af_scc_c0_vacuum.yaml",
    "c2_live": "schemas/af_scc_c2_vacuum.yaml",
    "f1_live": "schemas/af_wcc_vacuum.yaml",
    "frozen_rev29": "artifacts/formulation/FROZEN.json",
    "cand_corrected": "artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_corrected.yaml",
    "cand_nesting": "artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_nesting_only.yaml",
    "cand_circulating": "artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_84b5d3fa.yaml",
}
EXPECT = {
    "c0_live": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "c2_live": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "f1_live": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "frozen_rev29": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "cand_corrected": "51c253c463067e253dd32705f84d8ee089761439023acbbf1dd6660766191b7a",
    "cand_nesting": "4951cc96980329962829c2440c9e5c7f8ff5852eefd56aa48acfeeae8fb6505f",
    "cand_circulating": "84b5d3fa29a677ad157b924675bb5a9c08281395920be0221535465a5da44b40",
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    core_path = HERE / "report_core.json"
    core = json.loads(core_path.read_text())
    blast = json.loads((HERE / "blast_radius.json").read_text())

    # T1 live re-measurement: every source pin must still match its T0 value
    t1 = {}
    for key, rel in CANON.items():
        got = sha(ROOT / rel)
        t1[key] = {"path": rel, "sha256": got, "t0": EXPECT[key], "match": got == EXPECT[key]}
    drift = [k for k, v in t1.items() if not v["match"]]
    if drift:
        print(json.dumps({"status": "blocked_source_drift", "drift": drift}, indent=1))
        return 2

    artifacts = {
        "checker": HERE / "check_f2b_repair_candidates.py",
        "blast_script": HERE / "blast_radius.py",
        "report_core": core_path,
        "blast_radius": HERE / "blast_radius.json",
    }
    art_hashes = {k: {"path": str(v.relative_to(ROOT)), "sha256": sha(v)} for k, v in artifacts.items()}

    acceptance = core["acceptance"]
    verdict = "revise" if not all(acceptance.values()) else "revise"  # canonical F2b is still defective
    evidence = {
        "task_id": core["task_id"],
        "actor": "worker-029",
        "created_at": NOW,
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "authority": "worker evidence only; no gate verdict, node status or validation_status claimed",
        "target": "artifacts/worker-080/f2b_repair_entailment_audit/staged/{candidate_corrected,nesting_only,84b5d3fa} at live F2b rev13",
        "pins": core["pins"],
        "t1_live_remeasurement": t1,
        "acceptance": acceptance,
        "verdicts": {
            "live_c0_b2ab6acb": core["runs"]["live"]["kind_set"],
            "circulating_84b5d3fa": core["runs"]["circulating"]["kind_set"],
            "corrected_51c253c4": core["runs"]["corrected"]["kind_set"],
            "nesting_only_4951cc96": core["runs"]["nesting"]["kind_set"],
            "rev12_candidate_98f9ec83": core["runs"]["rev12_98f9ec83"]["kind_set"],
            "c2_sibling_e9a27996": core["runs"]["c2"]["kind_set"],
            "f1_sibling_d9cebb94": core["runs"]["f1"]["kind_set"],
        },
        "canonical_gate_rc": {k: v["rc"] for k, v in core["canonical_gate"].items()},
        "controls_matched": f"{sum(1 for c in core['controls'] if c['match'])}/{len(core['controls'])}",
        "hash_reproduction": core["hash_reproduction"],
        "conclusion": ("The circulating 84b5d3fa repair is NOT landable: it fixes H1/H2 but introduces an "
                       "entailment-direction inversion in C0 (class-relative sentence copied from C2). "
                       "candidate_corrected 51c253c4 and candidate_nesting 4951cc96 are finding-free under "
                       "the independent checker, reproduce from live+patch, and pass the canonical structural "
                       "gate (which is blind to all three defect kinds). Landing remains owner-only."),
        "falsifier": core["falsifier"],
        "artifacts": art_hashes,
        "blast_radius": {
            "canonical_normative_files": [h["path"] for h in blast["canonical_tree_hits"] if h["path"].startswith(("schemas/", "artifacts/formulation/schemas/"))],
            "fixture_hits": len(blast["fixture_hits"]),
            "counts_by_category": blast["counts_by_category"],
        },
    }

    report = {**evidence, "raw_core_sha256": sha(core_path), "nostr": None}
    del report["nostr"]
    (HERE / "evidence.json").write_text(json.dumps(evidence, indent=1, sort_keys=True) + "\n")
    (HERE / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")

    readme = f"""# W029-F2B-REPAIR-CANDIDATE-VERIFY-01

Worker `worker-029`, {NOW}. Node **F2b**, class **AF-SCC-C0-VAC-GEN**, gate **G-FORM**.
Read-only on every canonical path; no gate/node/validation status moved.

## Task
Independently verify the two F2b repair candidates staged by worker-080
(`candidate_corrected 51c253c4`, `candidate_nesting_only 4951cc96`) and the circulating
2-edit repair (`84b5d3fa`) at the live rev13 pin, with an independently written checker.

## Result
| target | sha256 | findings |
|---|---|---|
| live F2b rev13 | `b2ab6acb2bbe` | `false_containment_denial`, `size_premise_inverted` |
| circulating repair | `84b5d3fa29a6` | **`entailment_direction_inverted`** (repair-introduced) |
| corrected candidate | `51c253c46306` | none |
| nesting-only candidate | `4951cc969803` | none |
| rev12 candidate | `98f9ec83c487` | `entailment_direction_inverted` |
| C2 sibling | `e9a27996dfd3` | none |
| F1 sibling | `d9cebb9404b2` | no F2-style defect (no chain by design) |

- `live + patch_corrected.diff` reproduces `51c253c4` byte-exactly (`hash_reproduction: true`).
- `check_class_schema.py` returns rc 0 for live and all three candidates: the canonical
  structural gate is **blind** to all three defect kinds (independent confirmation of
  worker-017/worker-080).
- 14/14 pre-registered controls match, including class-relativity C13/C14: the same sentence
  `H2_loc-inextendibility entails this class's conclusion` is **accepted under own=C2 and
  rejected under own=C0**, so the checker is direction- and class-relative, not string-matching.
- Any pinned byte moving voids the report (`t1_live_remeasurement` in `evidence.json`).

## Landing requirements measured (owner-only)
1. Adopt `candidate_corrected 51c253c4` or `candidate_nesting 4951cc96`; do **not** land
   `84b5d3fa` as-is.
2. Bump revision, update `revised_at`, mirror to `artifacts/formulation/schemas/`, re-emit the
   FROZEN manifest, re-run the taxonomy-consistency evidence.
3. Fixture disposition: {len(blast['fixture_hits'])} semantic-contract fixtures still embed the
   stale strings (see `blast_radius.json`); canonical normative carriers are only
   `schemas/af_scc_c0_vacuum.yaml` and its authoring mirror.
4. Re-run `check_f2b_repair_candidates.py` after the bump; it fails closed on pin drift.

## Files
`check_f2b_repair_candidates.py`, `report_core.json` (deterministic), `report.json`,
`evidence.json`, `blast_radius.py` / `blast_radius.json`, `pinned/` (byte copies), `SHA256SUMS`.

## Falsifier
{core['falsifier']}
"""
    (HERE / "README.md").write_text(readme)
    art_hashes["readme"] = {"path": str((HERE / "README.md").relative_to(ROOT)), "sha256": sha(HERE / "README.md")}
    art_hashes["evidence"] = {"path": str((HERE / "evidence.json").relative_to(ROOT)), "sha256": sha(HERE / "evidence.json")}
    art_hashes["report"] = {"path": str((HERE / "report.json").relative_to(ROOT)), "sha256": sha(HERE / "report.json")}

    # SHA256SUMS for the package
    lines = []
    for p in sorted(HERE.rglob("*")):
        if p.is_file() and p.name != "SHA256SUMS":
            lines.append(f"{sha(p)}  {p.relative_to(HERE).as_posix()}")
    (HERE / "SHA256SUMS").write_text("\n".join(lines) + "\n")

    # advisory review record (worker authority, not a full-schema verdict)
    review = {
        "reviewer": "worker-029",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-WCC-VAC-GEN"],
        "gate": "G-FORM",
        "task_id": core["task_id"],
        "created_at": NOW,
        "target_id": "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe#repair-candidate-verify",
        "reviewed_sha256": EXPECT["c0_live"],
        "verdict": "revise",
        "score": 3.0,
        "counts_as_full_schema_verdict": False,
        "hard_failures": [
            "W029-R7-H1: canonical F2b b2ab6acb still carries the live containment denial at regularity.must_not_conflate[0] and the inverted size premise at implication_ledger.forbidden_transfers[0].reason",
            "W029-R7-H2: the circulating repair 84b5d3fa is not landable: its H2 replacement asserts H2_loc-inextendibility ENTAILS this class's conclusion inside the C0 file, contradicting the file's own chain and forbidden_weakenings row",
        ],
        "findings": [
            "candidate_corrected 51c253c4 reproduces byte-exactly from live+patch_corrected.diff and is finding-free under an independently written direction/class-relative checker (14/14 controls)",
            "candidate_nesting 4951cc96 is also finding-free; it makes no entailment claim at all, so it is the lower-risk landing if the owner prefers prose minimalism",
            "check_class_schema.py rc=0 on live and all three candidates: structural gate blindness to entailment direction confirmed independently",
            "class-relativity control: the identical sentence is accepted under own=C2 and rejected under own=C0, so the defect is 'true in the sibling, false here'",
            "blast radius: 2 canonical normative files (canonical + authoring mirror), 35 semantic-contract fixture copies; fixture disposition is an explicit landing decision",
        ],
        "evidence_refs": [
            f"artifacts/worker-029/f2b_repair_candidate_verify/evidence.json#{sha(HERE / 'evidence.json')[:12]}",
            f"artifacts/worker-029/f2b_repair_candidate_verify/report_core.json#{sha(core_path)[:12]}",
            "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
            "schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3",
            "artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_corrected.yaml#51c253c46306",
            "artifacts/formulation/FROZEN.json#815e08079aef",
        ],
        "next_falsifier": core["falsifier"],
    }
    review_path = ROOT / "reviews/F2b-repair-candidate-verify-worker-029.json"
    review_path.write_text(json.dumps(review, indent=1, sort_keys=True) + "\n")

    # checkpoint (worker-scoped; controller checkpoint.py is not touched)
    ckpt = {
        "task_id": core["task_id"],
        "actor": "worker-029",
        "created_at": NOW,
        "verdict": "revise",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "acceptance": acceptance,
        "pins_t0": core["pins"],
        "pins_t1_match": all(v["match"] for v in t1.values()),
        "report_core_sha256": sha(core_path),
        "evidence_sha256": sha(HERE / "evidence.json"),
        "review_path": str(review_path.relative_to(ROOT)),
        "artifacts": art_hashes,
        "next_falsifier": core["falsifier"],
    }
    ckpt_path = ROOT / "runtime/state/w029_f2b_repair_verify_checkpoint.json"
    ckpt_path.write_text(json.dumps(ckpt, indent=1, sort_keys=True) + "\n")
    with (ROOT / "runtime/state/w029_f2b_repair_verify_checkpoints.jsonl").open("a") as fh:
        fh.write(json.dumps(ckpt, sort_keys=True) + "\n")

    ev = []
    base = {"created_at": NOW, "actor": "worker-029", "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN",
            "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-WCC-VAC-GEN"], "gate": "G-FORM",
            "task_id": core["task_id"]}
    ev.append({**base, "event_id": f"{PREFIX}-status-start", "event_type": "status", "status": "active",
               "hours": 0.4,
               "summary": ("Claiming ONE bounded class-bound task on F2b/AF-SCC-C0-VAC-GEN: independent verification of the "
                           "F2b repair candidates staged by worker-080 at live rev13, with a fresh class-relative checker."),
               "evidence_refs": ["schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe", "artifacts/formulation/FROZEN.json#815e08079aef"],
               "next_falsifier": core["falsifier"]})
    for key, meta in art_hashes.items():
        ev.append({**base, "event_id": f"{PREFIX}-artifact-{key}", "event_type": "artifact",
                   "artifact_type": "report" if key in {"report", "report_core"} else ("evidence" if key in {"evidence", "blast_radius"} else ("readme" if key == "readme" else "script")),
                   "path": meta["path"], "sha256": meta["sha256"], "validation_status": "unverified",
                   "falsifier": core["falsifier"]})
    ev.append({**base, "event_id": f"{PREFIX}-review-candidates", "event_type": "review",
               "target_id": review["target_id"], "reviewer": "worker-029", "verdict": "revise", "score": 3.0,
               "hard_failures": review["hard_failures"], "findings": review["findings"],
               "counts_as_full_schema_verdict": False, "evidence_refs": review["evidence_refs"],
               "next_falsifier": core["falsifier"]})
    ev.append({**base, "event_id": f"{PREFIX}-claim-candidate", "event_type": "claim",
               "class_id": "AF-SCC-C0-VAC-GEN", "conclusion_type": "formal_model",
               "statement": ("At live F2b rev13 b2ab6acb, candidate_corrected 51c253c4 and candidate_nesting 4951cc96 are "
                             "finding-free under an independently written class-relative direction checker (14/14 controls, "
                             "hash-reproduced from live+patch); the circulating 84b5d3fa introduces entailment_direction_inverted; "
                             "check_class_schema.py is rc=0/blind on all four."),
               "assumptions": ["the file's own declared extension-class chain and one_way_entailments are the binding semantics",
                               "class-relativity of 'this class' is resolved via class_identity.class_id"],
               "falsifier": core["falsifier"],
               "evidence_refs": [f"artifacts/worker-029/f2b_repair_candidate_verify/report_core.json#{sha(core_path)[:12]}",
                                 f"artifacts/worker-029/f2b_repair_candidate_verify/evidence.json#{sha(HERE / 'evidence.json')[:12]}",
                                 "artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_corrected.yaml#51c253c46306"]})
    ev.append({**base, "event_id": f"{PREFIX}-blocker-landing", "event_type": "blocker",
               "description": ("F2b remains un-acceptable at rev13: live canonical carries both defects. The circulating repair "
                               "84b5d3fa must not be landed (repair-introduced entailment inversion). Two finding-free candidates "
                               "are staged and independently verified; landing is owner-only (canonical write + revision bump + "
                               "mirror + re-freeze + fixture disposition)."),
               "needed_to_unblock": ("astra-lead-formulation lands candidate_corrected 51c253c4 or candidate_nesting 4951cc96, "
                                     "bumps the revision, mirrors authoring->canonical, re-emits FROZEN, re-runs taxonomy "
                                     "consistency, and records the 35-fixture disposition; then re-run check_f2b_repair_candidates.py."),
               "evidence_refs": [f"artifacts/worker-029/f2b_repair_candidate_verify/evidence.json#{sha(HERE / 'evidence.json')[:12]}",
                                 "artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_corrected.yaml#51c253c46306",
                                 "artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_nesting_only.yaml#4951cc969803"]})
    ev.append({**base, "event_id": f"{PREFIX}-status-complete", "event_type": "status", "status": "active",
               "hours": 0.8,
               "summary": ("W029-F2B-REPAIR-CANDIDATE-VERIFY-01 complete at worker level: one bounded class-bound task, read-only. "
                           f"Acceptance {sum(1 for v in acceptance.values() if v)}/{len(acceptance)}; controls "
                           f"{sum(1 for c in core['controls'] if c['match'])}/{len(core['controls'])}; T1 pins unchanged; "
                           "no canonical edit, no gate or node status claimed."),
               "evidence_refs": [f"artifacts/worker-029/f2b_repair_candidate_verify/report_core.json#{sha(core_path)[:12]}",
                                 f"reviews/F2b-repair-candidate-verify-worker-029.json#{sha(review_path)[:12]}",
                                 f"runtime/state/w029_f2b_repair_verify_checkpoint.json#{sha(ckpt_path)[:12]}"],
               "next_falsifier": core["falsifier"]})

    outbox = ROOT / "comms/outbox/worker-029.jsonl"
    ok = 0
    import os
    if os.environ.get("W029_DRY"):
        for e in ev:
            schemas.validate_event(e)
            ok += 1
        print(json.dumps({"status": "dry_run_validated", "events": ok, "event_ids": [e["event_id"] for e in ev]}, indent=1))
        return 0
    with outbox.open("a") as fh:
        for e in ev:
            schemas.validate_event(e)
            fh.write(json.dumps(e, sort_keys=True) + "\n")
            ok += 1
    print(json.dumps({"status": "emitted", "events": ok, "checkpoint": str(ckpt_path.relative_to(ROOT)),
                      "review": str(review_path.relative_to(ROOT)), "acceptance": acceptance,
                      "t1_all_match": all(v["match"] for v in t1.values()),
                      "controls": f"{sum(1 for c in core['controls'] if c['match'])}/{len(core['controls'])}",
                      "event_ids": [e['event_id'] for e in ev]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
