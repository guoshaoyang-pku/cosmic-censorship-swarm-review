#!/usr/bin/env python3
"""Emit W092-F2A-CLASSBIND-REVIEW-01 events to comms/outbox/worker-092.jsonl and write the checkpoint.

Every event is validated with research_map.schemas.validate_event before it is appended.
Worker events deliberately do NOT set gate verdicts, node status=done, or validation_status=passed.
"""
from __future__ import annotations
import hashlib, json, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from research_map.schemas import validate_event  # noqa: E402

TZ = timezone(timedelta(hours=8))
TS = datetime.now(TZ).isoformat(timespec="seconds")
TAG = datetime.now(TZ).strftime("%Y%m%dT%H%M%S")
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
h12 = lambda p: sha(p)[:12]

PIN = "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce"
R = lambda p: str(Path(p).relative_to(ROOT))

review_path = ROOT / "reviews/F2a-review-rev27-c.json"
review = json.loads(review_path.read_text())
files = {f: {"path": R(HERE / f), "sha256": sha(HERE / f)} for f in
         ["report.json", "verify_f2a.py", "make_verdict.py", "controls.json",
          "acceptance_run.log", "README.md", "manifest.json"]}
ev_path = ROOT / "comms/outbox/worker-092.jsonl"

events = [
    {
        "event_id": f"w092-{TAG}-f2a-task-claim",
        "event_type": "status", "created_at": TS, "actor": "worker-092",
        "node_id": "F2a", "class_id": "AF-SCC-C2-VAC-GEN", "gate": "G-FORM",
        "status": "active", "hours": 0.9,
        "summary": ("No assignment card exists in comms/inbox for worker-092 (fleet 2026-09-12T00:44). "
                    "Taking ONE bounded class-bound task: independent blind G-FORM review of F2a "
                    "(AF-SCC-C2-VAC-GEN) at the FROZEN rev28 pin "
                    "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce, because F2a carries "
                    "0 distinct accepts and blocks both G-FORM and G-AUDIT. Read-only instrument; separate "
                    "verdict file reviews/F2a-review-rev27-c.json so carded reviewers are not overwritten."),
        "evidence_refs": [f"schemas/af_scc_c2_vacuum.yaml#{PIN[:12]}",
                          f"reviews/F2a-review-rev27-c.json#{h12(review_path)}"],
        "next_falsifier": ("Re-run verify_f2a.py at the same pins; falsified if any check flips, a control is "
                           "missed, or the schema/mirror hash moves off the pin."),
    },
]

# ---- artifact events
art_types = {
    "report.json": "f2a_classbind_review_report",
    "verify_f2a.py": "independent_review_instrument",
    "make_verdict.py": "verdict_generator",
    "controls.json": "negative_controls",
    "acceptance_run.log": "acceptance_log",
    "README.md": "readme",
    "manifest.json": "manifest",
}
for f, meta in files.items():
    events.append({
        "event_id": f"w092-{TAG}-f2a-artifact-{f.replace('.', '-')}",
        "event_type": "artifact", "created_at": TS, "actor": "worker-092",
        "node_id": "F2a", "class_id": "AF-SCC-C2-VAC-GEN", "gate": "G-FORM",
        "artifact_type": art_types[f], "path": meta["path"], "sha256": meta["sha256"],
        "validation_status": "unverified",
        "note": "W092-F2A-CLASSBIND-REVIEW-01 worker-level measurement; no gate authority.",
        "evidence_refs": [f"{meta['path']}#{meta['sha256'][:12]}"],
    })
events.append({
    "event_id": f"w092-{TAG}-f2a-artifact-verdict",
    "event_type": "artifact", "created_at": TS, "actor": "worker-092",
    "node_id": "F2a", "class_id": "AF-SCC-C2-VAC-GEN", "gate": "G-FORM",
    "artifact_type": "independent_review_verdict", "path": R(review_path),
    "sha256": sha(review_path), "validation_status": "unverified",
    "note": "revise 3.5; counts_as_full_schema_verdict=true; worker-level verdict, not a gate verdict.",
    "evidence_refs": [f"{R(review_path)}#{h12(review_path)}"],
})

# ---- one review event
events.append({
    "event_id": f"w092-{TAG}-f2a-review",
    "event_type": "review", "created_at": TS, "actor": "worker-092",
    "reviewer": "worker-092", "target_id": "F2a", "node_id": "F2a",
    "class_id": "AF-SCC-C2-VAC-GEN", "gate": "G-FORM",
    "verdict": "revise", "score": 3.5,
    "reviewed_path": "schemas/af_scc_c2_vacuum.yaml", "reviewed_sha256": PIN,
    "counts_as_full_schema_verdict": True, "hash_stable_during_review": True,
    "hard_failures": [{
        "id": "HF-W092-F2A-01",
        "detail": ("f0_binding declares consistency evidence 675a99d0, canonical path holds 9e335e9b which is "
                   "also the FROZEN rev28 pin: declared evidence unresolvable at the frozen revision. Live "
                   "bytes are a strict superset (adds map_taxonomy_sha256, lead_contract_sha256, measured_at), "
                   "so class semantics are unaffected."),
        "repair_preserving_pins": ("restore 675a99d0 bytes at the canonical path (copy: "
                                   "artifacts/worker-086/gform_rev12/pinned/taxonomy_consistency.675a99d0d25b.json) "
                                   "and re-freeze the evidence pin"),
    }],
    "findings": [
        "S01 PASS: C2/C0 separation is content-carried (distinct conclusion_type, extension_regularity C2 vs C0, equation signature classical_ricci vs none, asymmetric implication ledger).",
        "R03 PASS: D0 is a tagged disjoint union {smooth,(sobolev,s,delta)} s>5/2 delta in (1/2,1); binder instantiable on both disjuncts.",
        "R11/R14/R15 PASS: no conclusion inflation; epistemic_status=open_problem; vacuity argument marked unverified_proof_obligation.",
        "29 PASS / 3 DEFECT / 0 FAIL; 3/3 negative controls detected; entry==exit hashes for 9 pinned inputs; author checker also pass.",
        "Soft: canonical F0 contract uses an aliased conclusion token (S02b, F0-owned).",
        "Soft: Baire justification cites Banach for the Frechet smooth branch (R07b).",
    ],
    "evidence_refs": [f"schemas/af_scc_c2_vacuum.yaml#{PIN[:12]}",
                      f"{R(review_path)}#{h12(review_path)}",
                      f"artifacts/worker-092/f2a_review/report.json#{h12(HERE/'report.json')}"],
})

# ---- one claim (structural verification result, not a class conclusion)
events.append({
    "event_id": f"w092-{TAG}-f2a-claim",
    "event_type": "claim", "created_at": TS, "actor": "worker-092",
    "node_id": "F2a", "class_id": "AF-SCC-C2-VAC-GEN", "gate": "G-FORM",
    "conclusion_type": "formal_model",
    "statement": ("At FROZEN rev28 pin 5476a3f2c6bc, the AF-SCC-C2-VAC-GEN class contract passes all 16 structural "
                  "rules of rule_spec.json, separates from AF-SCC-C0-VAC-GEN by content (not naming), and is not "
                  "inflated to a theorem; it cannot receive a clean accept because f0_binding declares a "
                  "consistency-evidence hash (675a99d0) that does not resolve at the canonical path, whose bytes "
                  "(9e335e9b) are the FROZEN pin."),
    "assumptions": [
        "structural acceptance under rule_spec.json R01-R16; no judgement of physical truth",
        "reviewer is not an author of the target; no F2a verdict was read before this one was written",
        "pin discipline: entry==exit sha256 for all nine pinned inputs, zero drift",
    ],
    "falsifier": ("sha256(artifacts/formulation/evidence/taxonomy_consistency.json) becomes 675a99d0d25b at an "
                  "unchanged schema pin, or any of the 29 PASS checks flips on re-run of verify_f2a.py at the "
                  "same pins, or a control is no longer detected."),
    "evidence_refs": [f"schemas/af_scc_c2_vacuum.yaml#{PIN[:12]}",
                      f"reviews/F2a-review-rev27-c.json#{h12(review_path)}",
                      f"artifacts/formulation/evidence/taxonomy_consistency.json#9e335e9ba1bf",
                      f"artifacts/worker-092/f2a_review/report.json#{h12(HERE/'report.json')}"],
})

# ---- blocker for the hard finding
events.append({
    "event_id": f"w092-{TAG}-f2a-blocker",
    "event_type": "blocker", "created_at": TS, "actor": "worker-092",
    "node_id": "F2a", "class_id": "AF-SCC-C2-VAC-GEN", "gate": "G-FORM",
    "description": ("F2a at pin 5476a3f2c6bc cannot receive a clean accept: f0_binding.consistency_evidence_sha256 "
                    "= 675a99d0d25b does not resolve at artifacts/formulation/evidence/taxonomy_consistency.json, "
                    "which measures 9e335e9ba1bf and equals the FROZEN rev28 pin. Third independent measurement of "
                    "the rev12 binding defect; F2a-specific review verdict delivered as revise 3.5."),
    "needed_to_unblock": ("Owner restores the declared 675a99d0 bytes at the canonical evidence path (hash-verified "
                          "copy at artifacts/worker-086/gform_rev12/pinned/taxonomy_consistency.675a99d0d25b.json) "
                          "and re-freezes the evidence pin, OR re-stamps the declared hash to 9e335e9b in all three "
                          "schemas and accepts that every rev12-bound verdict is retired and must be re-run."),
    "evidence_refs": [f"schemas/af_scc_c2_vacuum.yaml#{PIN[:12]}",
                      f"reviews/F2a-review-rev27-c.json#{h12(review_path)}",
                      f"artifacts/worker-092/f2a_review/report.json#{h12(HERE/'report.json')}",
                      "artifacts/formulation/evidence/taxonomy_consistency.json#9e335e9ba1bf",
                      "artifacts/worker-086/gform_rev12/pinned/taxonomy_consistency.675a99d0d25b.json#675a99d0d25b",
                      "artifacts/worker-092/evbind/report.json#9a74243441ca"],
})

# ---- worker-level checkpoint receipt
events.append({
    "event_id": f"w092-{TAG}-f2a-status-complete",
    "event_type": "status", "created_at": TS, "actor": "worker-092",
    "node_id": "F2a", "class_id": "AF-SCC-C2-VAC-GEN", "gate": "G-FORM",
    "status": "active", "hours": 0.9,
    "summary": ("CHECKPOINT W092-F2A-REVIEW-01 complete (worker level): independent read-only F2a review delivered "
                "as revise 3.5 with counted full-schema verdict; 29 PASS / 3 DEFECT / 0 FAIL; 3/3 controls "
                "detected; 0 drift. HF-W092-F2A-01 = declared consistency-evidence hash unresolved at the FROZEN "
                "pin. Node status deliberately unchanged (worker events carry no authority)."),
    "evidence_refs": [f"artifacts/worker-092/f2a_review/manifest.json#{h12(HERE/'manifest.json')}",
                      f"reviews/F2a-review-rev27-c.json#{h12(review_path)}",
                      "runtime/state/worker-092_F2a_checkpoint.json"],
    "next_falsifier": ("Any rewrite of F0/F1/F2a/F2b, of the canonical evidence path, or of the checker retires "
                       "this review for the affected bytes; re-run verify_f2a.py at the new pins. The revise clears "
                       "when sha256(artifacts/formulation/evidence/taxonomy_consistency.json) matches the hash the "
                       "schema declares at an unchanged schema pin."),
})

# ---- validate + append
lines, bad = [], []
for e in events:
    try:
        validate_event(e)
        lines.append(json.dumps(e, sort_keys=True))
    except Exception as exc:  # noqa
        bad.append((e.get("event_id"), str(exc)))
if bad:
    print("REJECTED EVENTS (not written):", bad)
    sys.exit(1)
with ev_path.open("a") as f:
    for ln in lines:
        f.write(ln + "\n")

# ---- checkpoint file
ckpt = {
    "checkpoint_id": "W092-F2A-REVIEW-01",
    "created_at": TS,
    "worker": "worker-092",
    "task": ("No card in comms/inbox for worker-092; self-selected ONE bounded class-bound task: independent "
             "blind G-FORM review of F2a (AF-SCC-C2-VAC-GEN) at the FROZEN rev28 pin."),
    "target": {"node_id": "F2a", "class_id": "AF-SCC-C2-VAC-GEN", "gate": "G-FORM",
               "path": "schemas/af_scc_c2_vacuum.yaml", "sha256": PIN, "frozen_revision": 28},
    "result": {"verdict": review["verdict"], "score": review["score"],
               "counts_as_full_schema_verdict": review["counts_as_full_schema_verdict"],
               "counts": review["counts"], "controls": review["controls"],
               "hard_failures": [h["id"] for h in review["hard_failures"]],
               "non_pass_checks": [c["id"] for c in review["non_pass_checks"]]},
    "artifacts": {**{k: v for k, v in files.items()},
                  "verdict": {"path": R(review_path), "sha256": sha(review_path)}},
    "evidence_refs": review["evidence_refs"],
    "falsifier": review["falsifier"],
    "events": [json.loads(l)["event_id"] for l in lines],
    "budget_agent_hours": 0.9,
    "authority_note": ("worker events cannot set status=done, validation_status=passed, or any gate verdict; "
                       "this checkpoint is a worker-level receipt."),
    "next_action": ("Owner repairs HF-W092-F2A-01 (restore declared bytes or re-stamp+refreeze), then re-run "
                    "artifacts/worker-092/f2a_review/verify_f2a.py at the resulting pins."),
    "exit": "worker exits after this checkpoint",
}
ck_path = ROOT / "runtime/state/worker-092_F2a_checkpoint.json"
ck_path.write_text(json.dumps(ckpt, indent=1, sort_keys=True))
print("validated events:", len(lines), "->", R(ev_path))
for ln in lines:
    o = json.loads(ln)
    print("  ", o["event_id"], o["event_type"])
print("checkpoint:", R(ck_path), "sha256", sha(ck_path)[:12])
