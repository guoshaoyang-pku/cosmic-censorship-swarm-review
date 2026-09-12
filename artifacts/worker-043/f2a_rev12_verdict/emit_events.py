#!/usr/bin/env python3
"""Emit the W043C event batch to comms/outbox/worker-043.jsonl.

Every event is validated against research_map/schemas.py:validate_event before
it is appended; --dry-run validates and prints without writing.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

OUT = ROOT / "comms/outbox/worker-043.jsonl"
D = ROOT / "artifacts/worker-043/f2a_rev12_verdict"
TASK = "W043C-F2A-REV12-VERDICT-01"
CLASS = "AF-SCC-C2-VAC-GEN"
F2A_SHA = "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce"
FROZEN_SHA = "2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1"
CONS_SHA = "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b"
STALE = "675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--at", default=None, help="fixed created_at for reproducibility")
    args = ap.parse_args()
    now = args.at or dt.datetime.now().astimezone().isoformat(timespec="seconds")

    report_sha = sha(D / "report.json")
    checker_sha = sha(D / "check_f2a_rev12.py")
    review_sha = sha(ROOT / "reviews/F2a-review-043.json")
    raw_sha = sha(D / "raw/check_selftest.json")
    cf_sha = sha(D / "raw/counterfactual_repair.json")
    snap_sha = sha(D / "snapshot/SNAPSHOT_MANIFEST.json")
    readme_sha = sha(D / "README.md")

    ev = []
    ev.append({
        "event_id": "w043c-20260912T0041-status-claim",
        "event_type": "status", "created_at": now, "actor": "worker-043",
        "node_id": "F2a", "node_ids": ["F2a", "F1", "F2b"], "class_id": CLASS,
        "class_ids": [CLASS], "gate": "G-FORM", "status": "active", "hours": 0.7,
        "task_id": TASK,
        "summary": ("Claim and complete one bounded class-bound task: independent full-schema verdict for "
          f"AF-SCC-C2-VAC-GEN (F2a) at the FROZEN rev28 hash {F2A_SHA[:16]} — the class with zero verdicts at "
          "that hash in reviews/G-FORM-final-verify.json B-GFORM-1. Verdict revise 3.0: 14/14 content checks PASS; "
          "HF-043-1 stale embedded consistency_evidence_sha256 (675a99d0 vs frozen 9e335e9b, bytes absent); "
          "HF-043-2 frozen consistency evidence is not hash-bound. No node/gate authority claimed."),
        "evidence_refs": [f"artifacts/worker-043/f2a_rev12_verdict/report.json#{report_sha[:12]}",
                          f"reviews/F2a-review-043.json#{review_sha[:12]}",
                          f"schemas/af_scc_c2_vacuum.yaml#{F2A_SHA[:12]}",
                          f"artifacts/formulation/FROZEN.json#{FROZEN_SHA[:12]}"],
        "next_falsifier": ("Any byte change of the reviewed files voids the review. HF-043-1 clears only when the embedded "
          "hash equals a hash-bound, re-frozen consistency evidence (ordering P-043-1); HF-043-2 clears when "
          "map_taxonomy_sha256/lead_contract_sha256 are present and correct in the frozen evidence."),
    })
    for eid, path, sha256, atype, note in [
        ("checker", "artifacts/worker-043/f2a_rev12_verdict/check_f2a_rev12.py", checker_sha,
         "independent_checker", "Deterministic 16-check full-schema checker; 7-mutant + exact-fail-set control battery."),
        ("report", "artifacts/worker-043/f2a_rev12_verdict/report.json", report_sha,
         "review_report", "Full review record: checks, hard failures, adjudications, pre-registered acceptance."),
        ("review", "reviews/F2a-review-043.json", review_sha,
         "review_verdict", "Corpus review verdict bound to schemas/af_scc_c2_vacuum.yaml#5476a3f2c6bc."),
        ("snapshot", "artifacts/worker-043/f2a_rev12_verdict/snapshot/SNAPSHOT_MANIFEST.json", snap_sha,
         "snapshot_manifest", "Byte snapshot manifest of the 11 reviewed/frozen files with mtimes."),
        ("raw-selftest", "artifacts/worker-043/f2a_rev12_verdict/raw/check_selftest.json", raw_sha,
         "test_evidence", "Checker output with controls on the live root."),
        ("raw-counterfactual", "artifacts/worker-043/f2a_rev12_verdict/raw/counterfactual_repair.json", cf_sha,
         "test_evidence", "Pre-registered acceptance: repairs A+B + re-freeze -> accept / 0 FAIL."),
        ("readme", "artifacts/worker-043/f2a_rev12_verdict/README.md", readme_sha,
         "report_summary", "Human-readable summary, reproduce commands, authority note."),
    ]:
        ev.append({
            "event_id": f"w043c-20260912T0041-artifact-{eid}",
            "event_type": "artifact", "created_at": now, "actor": "worker-043",
            "node_id": "F2a", "class_id": CLASS, "class_ids": [CLASS], "gate": "G-FORM",
            "artifact_type": atype, "path": path, "sha256": sha256,
            "bytes": (ROOT / path).stat().st_size, "summary": note,
            "validation_status": "unverified",
            "evidence_refs": [f"{path}#{sha256[:12]}"],
        })
    ev.append({
        "event_id": "w043c-20260912T0041-claim-f2a",
        "event_type": "claim", "created_at": now, "actor": "worker-043",
        "node_id": "F2a", "class_id": CLASS, "class_ids": [CLASS], "gate": "G-FORM",
        "conclusion_type": "formal_model",
        "statement": (f"At the FROZEN rev28 bytes (schemas/af_scc_c2_vacuum.yaml {F2A_SHA[:16]}, FROZEN "
          f"{FROZEN_SHA[:16]}, taxonomy_consistency.json {CONS_SHA[:16]}), F2a AF-SCC-C2-VAC-GEN passes every content "
          "criterion of a full-schema review (identity, strict YAML, freeze pin and mirror, clock, quantifier chain and "
          "domain typing, SCC conclusion with visibility excluded, C2 classical-Ric extension predicate, regularity and "
          "composite ban, ledger direction, falsifier decidability, no inflation, pointer resolution, declared gate), "
          f"but the frozen revision is not binding-coherent: f0_binding.consistency_evidence_sha256 is the stale "
          f"{STALE[:16]} whose bytes exist nowhere, while the named evidence file measures {CONS_SHA[:16]}; and that "
          "evidence carries no map_taxonomy_sha256/lead_contract_sha256, regressing the rev27 hash-binding closure. "
          "Verdict revise 3.0 (advisory). This is an artifact-consistency result, not a mathematical claim."),
        "assumptions": ["canonical path schemas/*.yaml is authoritative and the authoring mirror was byte-identical at measurement time",
                        "hash bindings are evaluated against the measured bytes at the snapshot instant, not against FROZEN revision numbers",
                        "the schema's own extension_class_containment sentence is the reference order for the ledger check",
                        "worker verdicts cannot set node status, validation_status or a gate verdict"],
        "artifact_refs": [f"artifacts/worker-043/f2a_rev12_verdict/report.json#{report_sha[:12]}",
                          f"reviews/F2a-review-043.json#{review_sha[:12]}",
                          f"schemas/af_scc_c2_vacuum.yaml#{F2A_SHA[:12]}"],
        "evidence_refs": [f"artifacts/worker-043/f2a_rev12_verdict/raw/check_selftest.json#{raw_sha[:12]}",
                          f"artifacts/worker-043/f2a_rev12_verdict/raw/counterfactual_repair.json#{cf_sha[:12]}",
                          f"artifacts/formulation/evidence/taxonomy_consistency.json#{CONS_SHA[:12]}",
                          f"artifacts/formulation/FROZEN.json#{FROZEN_SHA[:12]}"],
        "falsifier": (f"HF-043-1 is falsified by a file at the named path hashing to {STALE[:16]}; HF-043-2 by "
          "map_taxonomy_sha256/lead_contract_sha256 present and equal to the measured F0 hashes in the frozen evidence. "
          "The counterfactual acceptance is falsified if the two repairs plus re-freeze do not produce accept / 0 FAIL."),
    })
    ev.append({
        "event_id": "w043c-20260912T0041-review-f2a",
        "event_type": "review", "created_at": now, "actor": "worker-043",
        "reviewer": "worker-043", "target_id": "F2a", "node_id": "F2a",
        "class_id": CLASS, "class_ids": [CLASS], "gate": "G-FORM",
        "artifact": "schemas/af_scc_c2_vacuum.yaml", "artifact_sha256": F2A_SHA,
        "artifact_revision": 12, "counts_as_full_schema_verdict": True,
        "verdict": "revise", "score": 3.0,
        "hard_failures": [
            {"id": "HF-043-1", "severity": "blocking", "axis": "evidence binding",
             "finding": (f"f0_binding.consistency_evidence_sha256={STALE[:16]} but the named evidence file measures "
                         f"{CONS_SHA[:16]} and is FROZEN rev28-pinned at that hash; the stale bytes exist nowhere on disk"),
             "repair": "repair the evidence first (HF-043-2), set the embedded hash to the repaired evidence hash, re-freeze"},
            {"id": "HF-043-2", "severity": "major", "axis": "evidence regression (rev27 closure item (e))",
             "finding": ("frozen taxonomy_consistency.json carries no map_taxonomy_sha256/lead_contract_sha256, so it does not "
                         "bind the F0 trees it reports on (F1-review-090 F090-05 / F1-review-19 F-4 regressed)"),
             "repair": "regenerate the evidence with both tree hashes and re-freeze"},
        ],
        "findings": [
            "14/14 content checks PASS at the frozen bytes; strict YAML parse has 0 duplicate keys",
            "quantifier chain forall r in D0 / comeager G_r / forall data / not-exists extension with all four domains typed and resolving",
            "O-GFORM-1 adjudicated non-blocking: F2a/F2b data_class key-identity is intended (the token selects the extension class)",
            "O-043-1 cross-reference: the F2 index regularities.yaml is stale and duplicate-keyed (owned by F2 index; worker-005 blocker 00:34:22)",
            "pre-registered acceptance: repairs A+B + re-freeze -> accept / 0 FAIL; ordering P-043-1 (A after B) verified",
        ],
        "gate_eligible": True,
        "authority_note": ("Advisory worker verdict. counts_as_full_schema_verdict=true is a coverage assertion only; it cannot "
                           "set node status, validation_status=passed or a gate verdict."),
        "evidence_refs": [f"reviews/F2a-review-043.json#{review_sha[:12]}",
                          f"artifacts/worker-043/f2a_rev12_verdict/report.json#{report_sha[:12]}",
                          f"schemas/af_scc_c2_vacuum.yaml#{F2A_SHA[:12]}"],
    })
    ev.append({
        "event_id": "w043c-20260912T0041-blocker-binding",
        "event_type": "blocker", "created_at": now, "actor": "worker-043",
        "node_id": "F2a", "node_ids": ["F2a", "F1", "F2b"], "class_id": CLASS, "class_ids": [CLASS],
        "gate": "G-FORM",
        "description": (f"F2a/F1/F2b embed consistency_evidence_sha256={STALE[:16]} at FROZEN rev28 while the named file "
          f"artifacts/formulation/evidence/taxonomy_consistency.json measures {CONS_SHA[:16]} and is frozen at that hash; "
          "the declared evidence bytes no longer exist (0 hits on disk). The frozen evidence is also hashless "
          "(no map_taxonomy_sha256/lead_contract_sha256), regressing the rev27 closure item (e)."),
        "needed_to_unblock": ("lead-formulation: (1) regenerate taxonomy_consistency.json with map_taxonomy_sha256 and "
          "lead_contract_sha256 (rev27 close_findings_rev27.py:379-380 behaviour); (2) set f0_binding.consistency_evidence_sha256 "
          "in F1/F2a/F2b to the hash of that repaired file (ordering P-043-1: A after B); (3) publish mirrors byte-identically and "
          "re-freeze; then re-run the W043C checker at the new hashes for an accept. Controller: do not count F2a as accepted at "
          "this hash until then."),
        "evidence_refs": [f"schemas/af_scc_c2_vacuum.yaml:291", f"artifacts/formulation/evidence/taxonomy_consistency.json#{CONS_SHA[:12]}",
                          f"artifacts/formulation/FROZEN.json#{FROZEN_SHA[:12]}",
                          f"artifacts/worker-043/f2a_rev12_verdict/raw/check_selftest.json#{raw_sha[:12]}"],
        "falsifier": "a file at the named path hashing to 675a99d0, or a frozen evidence carrying both tree hashes equal to the measured F0 hashes",
    })
    ev.append({
        "event_id": "w043c-20260912T0041-status-complete",
        "event_type": "status", "created_at": now, "actor": "worker-043",
        "node_id": "F2a", "node_ids": ["F2a", "F1", "F2b"], "class_id": CLASS, "class_ids": [CLASS],
        "gate": "G-FORM", "status": "active", "hours": 0.7, "task_id": TASK,
        "summary": ("W043C-F2A-REV12-VERDICT-01 complete at worker level: 8 artifacts on disk and hash-pinned, checker controls "
          "8/8, pre-registered acceptance PASS, checkpoint runtime/state/w043_checkpoint_3.json. Delivered one of the two "
          "independent F2a verdicts required by B-GFORM-1 (verdict revise 3.0). Completion claim only; no node transition, "
          "no gate verdict, no canonical byte changed."),
        "evidence_refs": [f"artifacts/worker-043/f2a_rev12_verdict/report.json#{report_sha[:12]}",
                          f"reviews/F2a-review-043.json#{review_sha[:12]}",
                          "runtime/state/w043_checkpoint_3.json"],
        "next_falsifier": ("The two repairs plus re-freeze must flip the checker to accept/0 FAIL (pre-registered); a byte change of any "
          "reviewed file after this emission voids the whole review and requires re-issue at the new hashes."),
    })

    for e in ev:
        validate_event(e)
    if args.dry_run:
        print(json.dumps(ev, indent=1)[:4000])
        print(f"\nDRY-RUN OK: {len(ev)} events validated")
        return 0
    with OUT.open("a") as fh:
        for e in ev:
            fh.write(json.dumps(e, sort_keys=True) + "\n")
    print(f"appended {len(ev)} validated events to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
