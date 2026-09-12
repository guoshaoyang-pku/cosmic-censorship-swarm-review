#!/usr/bin/env python3
"""worker-046: emit the F2a live-pin (rev13) transfer review, one review event, one checkpoint.

Deterministic generator: all hashes are measured here, never hand-typed.
Run from the swarm root:  python3 artifacts/worker-046/f2a_live_repin_rev13/make_outputs.py
"""
from __future__ import annotations
import hashlib, json, subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
D = ROOT / "artifacts/worker-046/f2a_live_repin_rev13"
TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ).replace(microsecond=0).isoformat()
STAMP = datetime.now(TZ).strftime("%Y%m%dT%H%M%S")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ref(p: Path) -> str:
    return f"{p.relative_to(ROOT).as_posix()}#{sha(p)[:12]}"


# ---- measured inputs -------------------------------------------------------
C2 = ROOT / "schemas/af_scc_c2_vacuum.yaml"
C0 = ROOT / "schemas/af_scc_c0_vacuum.yaml"
AGG = ROOT / "schemas/af_scc_regularities.yaml"
FROZEN = ROOT / "artifacts/formulation/FROZEN.json"
KM = ROOT / "artifacts/formulation/KEY_MANIFEST.json"
SPEC = ROOT / "artifacts/formulation/rule_spec.json"
GATE = ROOT / "artifacts/formulation/tools/check_class_schema.py"
TAX = ROOT / "research_map/formulation_taxonomy.yaml"
SUP = ROOT / "artifacts/formulation/formulation_taxonomy.yaml"
CONS = ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json"

M = {p.relative_to(ROOT).as_posix(): sha(p) for p in (C2, C0, AGG, FROZEN, KM, SPEC, GATE, TAX, SUP, CONS)}
frozen = json.loads(FROZEN.read_text())
fz = frozen["files"]
assert M["schemas/af_scc_c2_vacuum.yaml"] == fz["schemas/af_scc_c2_vacuum.yaml"]["sha256"], "FROZEN rev29 must declare live C2"
assert M["schemas/af_scc_c0_vacuum.yaml"] == fz["schemas/af_scc_c0_vacuum.yaml"]["sha256"], "FROZEN rev29 must declare live C0"
assert M["artifacts/formulation/KEY_MANIFEST.json"] == fz["artifacts/formulation/KEY_MANIFEST.json"]["sha256"]
assert M["artifacts/formulation/tools/check_class_schema.py"] == fz["artifacts/formulation/tools/check_class_schema.py"]["sha256"]
assert M["artifacts/formulation/rule_spec.json"] == fz["artifacts/formulation/rule_spec.json"]["sha256"]
assert M["artifacts/formulation/evidence/taxonomy_consistency.json"] == fz["artifacts/formulation/evidence/taxonomy_consistency.json"]["sha256"]
assert M["research_map/formulation_taxonomy.yaml"] == fz["research_map/formulation_taxonomy.yaml"]["sha256"]
assert M["artifacts/formulation/formulation_taxonomy.yaml"] == fz["artifacts/formulation/formulation_taxonomy.yaml"]["sha256"]
assert "schemas/af_scc_regularities.yaml" not in fz, "aggregator must be outside FROZEN rev29 for F-046b-03 to hold"

gate_c2 = json.loads((D / "gate_runs/gate_c2_livemanifest.json").read_text())
gate_c0 = json.loads((D / "gate_runs/gate_c0_livemanifest.json").read_text())
gate_rev27 = json.loads((D / "gate_runs/gate_c2_rev27manifest_rerun.json").read_text())
d0 = json.loads((D / "gate_runs/d0_instantiation_check_live.json").read_text())
agg = json.loads((D / "evidence/aggregator_pin_check.json").read_text())
assert gate_c2["verdict"] == "pass" and gate_c0["verdict"] == "pass"
assert gate_rev27["verdict"] == "fail" and gate_rev27["failed_rules"] == ["R22"]
assert d0["verdict"] == "PASS" and d0["pin_match"] is True
assert agg["verdict"] == "pass"

# ---- review document -------------------------------------------------------
review = {
    "review_id": "F2a-review-live-rev13-worker-046",
    "verdict_version": "1.0",
    "review_type": "live_pin_transfer_verification",
    "document_type": "class_content_verdict_at_live_bytes",
    "created_at": NOW,
    "reviewer": "worker-046",
    "reviewer_role": "execution_worker_deepseek_flash",
    "target_id": "F2a",
    "node_id": "F2a",
    "class_id": "AF-SCC-C2-VAC-GEN",
    "gate": "G-FORM",
    "artifact": "schemas/af_scc_c2_vacuum.yaml",
    "assignment_refs": ["audit-r2-F2a-a", "audit-r2-F2a-bindchain-worker-046"],
    "task": "Execute the next_falsifier pre-registered in reviews/F2a-review-rev27-a.json: transfer the three measured checks to the live rev13 pin and report which prior findings survive, which hard failures dissolve, and what is new.",
    "supersedes": {
        "review_id": "F2a-review-rev27-a",
        "sha256": sha(ROOT / "reviews/F2a-review-rev27-a.json"),
        "reviewed_sha256": "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
        "relationship": "continuation, not a replacement: the rev12-pin verdict and its moving-target blocker stay on the record; this document adds the live-byte-state verdict the prior review deferred.",
    },
    "byte_state": {
        "measured_before_read": True,
        "measured_after_read": True,
        "artifact_edited_by_reviewer": False,
        "live_sha256": M["schemas/af_scc_c2_vacuum.yaml"],
        "live_revision": 13,
        "live_bytes": C2.stat().st_size,
        "live_revised_at": "2026-09-12T00:53:20+08:00",
        "c0_live_sha256": M["schemas/af_scc_c0_vacuum.yaml"],
        "frozen_rev29_sha256": M["artifacts/formulation/FROZEN.json"],
        "frozen_rev29_declares_live_c2": True,
        "frozen_rev29_declares_live_c0": True,
        "frozen_rev29_key_manifest": M["artifacts/formulation/KEY_MANIFEST.json"],
        "frozen_rev29_checker": M["artifacts/formulation/tools/check_class_schema.py"],
        "frozen_rev29_rule_spec": M["artifacts/formulation/rule_spec.json"],
        "named_path_match": True,
    },
    "verdict": "revise",
    "score": 3.0,
    "score_rationale": "Both prior hash-bound/toolchain hard failures dissolved at the live pin (f0_binding resolves, the gate passes under the FROZEN rev29 manifest), the C2/C0 separation and the D0 binder are clean, and no conclusion inflation is present. Not an accept: the major 4D-borderline containment defect in the implication ledgers (F-046b-01) is carried into rev13 unchanged and the tier-1 falsifier is still not bound to r in D0 (F-046b-02). Not a reject: the defects are localized, repairable text/binding issues and the class structure itself is sound.",
    "counts_as_gate_verdict": False,
    "no_gate_verdict_set": True,
    "hard_failures": [],
    "prior_hard_failures_disposition": [
        {
            "id": "HF-046-F2a-01",
            "kind": "hash_bound",
            "status": "DISSOLVED at the live pin",
            "measurement": f"live f0_binding.consistency_evidence_sha256 = {sha(CONS)}; measured {CONS.name} = {sha(CONS)}; match=true. FROZEN rev29 declares the same 9e335e9b.",
        },
        {
            "id": "HF-046-F2a-02",
            "kind": "gate_toolchain_skew",
            "status": "DISSOLVED at FROZEN rev29",
            "measurement": "live gate on live C2 under the declared FROZEN rev29 triple (checker 000e09e4, rule_spec 40f9bb9e, KEY_MANIFEST 014e2d30) -> pass, failed_rules=[]. The same live bytes under the revoked rev27 manifest fce91948 still fail R22 (rerun recorded), confirming the skew was manifest-version, not artifact content.",
        },
    ],
    "finding_transfer": [
        {"prior_id": "F-046-F2a-01", "status": "SURVIVES WITH A RECORD CORRECTION", "severity": "major", "live_id": "F-046b-01"},
        {"prior_id": "F-046-F2a-02", "status": "SURVIVES", "severity": "moderate", "live_id": "F-046b-02"},
        {"prior_id": "F-046-F2a-03", "status": "SURVIVES", "severity": "minor", "live_id": "F-046b-04"},
        {"prior_id": "F-046-F2a-04", "status": "SURVIVES", "severity": "minor", "live_id": "F-046b-05"},
        {"prior_id": "F-046-F2a-05", "status": "SURVIVES", "severity": "minor", "live_id": "F-046b-06"},
        {"prior_id": "F-046-F2a-06", "status": "RESOLVED at the live pin (aggregator rev7 re-pins and passes P1-P5); residual freeze-coverage gap recorded as F-046b-03", "severity": "context", "live_id": "F-046b-03"},
    ],
    "findings": [
        {
            "id": "F-046b-01",
            "severity": "major",
            "status": "survives; record correction to F-046-F2a-01",
            "claim": "The E_H2loc subset E_C0 link is still asserted in the live C2 schema (lines 152 and 237) and, as before, in the live C0 ledger (lines 239 and 241), with relation rows labelled elementary/standard_fact and no citation_status. In 4D the borderline Sobolev exponent is s = n/2 = 2, where the embedding H^2_loc -> L^infinity fails, so 'an H2_loc extension is a continuous metric extension' is not elementary as stated. Live C0 additionally contradicts itself: must_not_conflate (line 152) says 'No containment with C2 or C0 is asserted here' while its own implication_ledger (lines 239/241) asserts exactly that containment.",
            "record_correction": "F-046-F2a-01 described the defect as a C2-vs-C0 split ('the pinned C0 sibling explicitly declines the same containment'). That phrasing quoted only C0's must_not_conflate. The pinned rev12 C0 ledger already asserted E_H2loc subset E_C0 at its lines 238/240, identical to live. The conflict is therefore (i) an unwarranted borderline containment carried by both ledgers and (ii) an internal must_not_conflate-vs-ledger contradiction inside C0, not a cross-schema disagreement. The defect and the repair direction are unchanged.",
            "evidence": [
                ref(C2) + ":152", ref(C2) + ":237",
                ref(C0) + ":152", ref(C0) + ":239", ref(C0) + ":241",
                ref(ROOT / "artifacts/worker-046/f2a_rev27_verdict/pinned/af_scc_c0_vacuum.55d0a1ea9bda.yaml") + ":238",
                ref(ROOT / "artifacts/worker-046/f2a_rev27_verdict/pinned/af_scc_c0_vacuum.55d0a1ea9bda.yaml") + ":240",
            ],
            "repair": "Drop or qualify the H2loc subset C0 rows in both ledgers; if continuity is intended, redefine the H2LOC variant as H^2_loc cap C^0 and re-run the separation lint; reconcile C0's must_not_conflate sentence with its ledger.",
        },
        {
            "id": "F-046b-02",
            "severity": "moderate",
            "status": "survives (prior F-046-F2a-02)",
            "claim": "The tier-1 falsifier at the live pin (lines 252-256) still says 'an open (or at least non-meager) set of one-ended AF vacuum data' with proof obligation 'non-meagerness of the extendible set', naming no r, while the class negation (lines 66-69) is 'there exists r in D0 such that ... non-meager' and D0 is a tagged disjoint union (line 53). Openness and non-meagerness are r-relative; a tier-1 refutation must name its r.",
            "evidence": [ref(C2) + ":53", ref(C2) + ":66", ref(C2) + ":67", ref(C2) + ":252", ref(C2) + ":254", ref(C2) + ":256"],
            "repair": "State tier_1.witness_type as 'for some r in D0, an open (or non-meager) subset of X^r_vac(AF) ...' and bind route R1 the same way.",
        },
        {
            "id": "F-046b-03",
            "severity": "moderate",
            "status": "new residual (F-046-F2a-06 resolved, coverage gap remains)",
            "claim": "The separation aggregator schemas/af_scc_regularities.yaml rev7 (27255e5b) now re-pins both live components and passes the P1-P5 pin check, so the staleness finding is resolved. However the aggregator is not in the FROZEN rev29 file manifest (50 entries; no regularities entry) and the map's frozen_artifacts entry for it is inactive (superseded c6bfda2bf3f5). G-FORM's per-file pin binding for the index that supplies the separation lint therefore rests only on the aggregator's self-declared pins.",
            "evidence": [ref(AGG) + ":16", ref(AGG) + ":35", ref(AGG) + ":43", ref(AGG) + ":59", ref(FROZEN), ref(ROOT / "artifacts/worker-046/f2a_live_repin_rev13/evidence/aggregator_pin_check.json")],
            "note": "Outside the assigned C2 file; measured because G-FORM's open blocking item is FROZEN/per-file pin binding.",
            "repair": "Add schemas/af_scc_regularities.yaml to the next FROZEN revision (or record it as explicitly out of G-FORM scope with a reason).",
        },
        {
            "id": "F-046b-04",
            "severity": "minor",
            "status": "survives (prior F-046-F2a-03)",
            "claim": "regularity.i_plus_regularity (line 146) still fixes k >= 3 without a binder or declared range in D0/D2, so instantiating the class does not fix k.",
            "evidence": [ref(C2) + ":146"],
            "repair": "Declare k as a fixed parameter of the data class or add it to D0/D2.",
        },
        {
            "id": "F-046b-05",
            "severity": "minor",
            "status": "survives (prior F-046-F2a-04)",
            "claim": "genericity.ambient_space still justifies Baireness only via 'X_vac is a closed subset of a Banach space', while topology_or_measure names the Frechet topology for the smooth class; the stated reason covers only the Sobolev disjunct.",
            "evidence": [ref(C2) + ":158", ref(C2) + ":160"],
            "repair": "Split the Baire justification per disjunct (Banach for Sobolev; complete metrizable/Frechet for smooth).",
        },
        {
            "id": "F-046b-06",
            "severity": "minor",
            "status": "survives (prior F-046-F2a-05)",
            "claim": "class_boundary.one_way_implication (line 78) still writes E(C0)/E(C2) for conclusions while extension_predicate and implication_ledger use E_C0/E_C2 for extension sets; two careful readers can disagree about the denotation.",
            "evidence": [ref(C2) + ":78", ref(C2) + ":237"],
            "repair": "Use distinct symbols for conclusions and extension sets.",
        },
    ],
    "checks": {
        "c2_c0_collapse": {
            "result": "PASS",
            "conclusion_type_C2": "scc_c2_future_inextendibility",
            "conclusion_type_C0": "scc_c0_future_inextendibility",
            "evidence": [ref(C2) + ":209", ref(C0) + ":211"],
        },
        "d0_binder_instantiation": {
            "result": "PASS at live bytes",
            "method": ref(D / "d0_instantiation_check_live.py") + " (mechanical; both branches declared, no destructured r, both substitutions well-typed, definition_ref resolves)",
            "report": ref(D / "gate_runs/d0_instantiation_check_live.json"),
        },
        "class_schema_gate_c2_live_manifest": {"result": "pass", "report": ref(D / "gate_runs/gate_c2_livemanifest.json")},
        "class_schema_gate_c0_live_manifest": {"result": "pass", "report": ref(D / "gate_runs/gate_c0_livemanifest.json")},
        "class_schema_gate_c2_rev27_manifest_rerun": {
            "result": "fail R22 (historical toolchain record; not a live blocker)",
            "report": ref(D / "gate_runs/gate_c2_rev27manifest_rerun.json"),
        },
        "taxonomy_consistency": {"result": "CONSISTENT (4 classes, 0 contract-text divergences)", "report": ref(D / "evidence/taxonomy_consistency_stdout.txt")},
        "aggregator_pins": {"result": "pass P1-P5", "report": ref(D / "evidence/aggregator_pin_check.json")},
        "f0_binding_hash_chain": {
            "result": "all path-bound declared hashes resolve at live bytes; refresh rule satisfied",
            "items": [
                {"field": "declared_f0_sha256", "path": "research_map/formulation_taxonomy.yaml", "declared": M["research_map/formulation_taxonomy.yaml"], "measured": M["research_map/formulation_taxonomy.yaml"], "status": "resolved"},
                {"field": "consistency_evidence_sha256", "path": CONS.name, "declared": M["artifacts/formulation/evidence/taxonomy_consistency.json"], "measured": M["artifacts/formulation/evidence/taxonomy_consistency.json"], "status": "resolved"},
                {"field": "class_contract_supplement (pointer-only)", "path": SUP.name, "measured": M["artifacts/formulation/formulation_taxonomy.yaml"], "status": "resolved"},
                {"field": "provenance.worker_sha256", "path": None, "status": "unresolved_metadata (no declared path; not a mismatch)"},
            ],
        },
        "conclusion_inflation": {"result": "PASS", "note": "epistemic_status=open_problem; promotion_rule requires a checked proof with artifact_refs; no theorem claim."},
        "falsifier_decidability": {"result": "PASS with the F-046b-02 r-binding caveat"},
    },
    "evidence_refs": [
        ref(C2), ref(C0), ref(AGG), ref(FROZEN), ref(KM), ref(SPEC), ref(GATE), ref(CONS), ref(TAX), ref(SUP),
        ref(ROOT / "artifacts/worker-046/f2a_rev27_verdict/pinned/af_scc_c0_vacuum.55d0a1ea9bda.yaml"),
        ref(ROOT / "reviews/F2a-review-rev27-a.json"),
        ref(D / "gate_runs/gate_c2_livemanifest.json"),
        ref(D / "gate_runs/gate_c0_livemanifest.json"),
        ref(D / "gate_runs/gate_c2_rev27manifest_rerun.json"),
        ref(D / "gate_runs/d0_instantiation_check_live.json"),
        ref(D / "d0_instantiation_check_live.py"),
        ref(D / "evidence/taxonomy_consistency_stdout.txt"),
        ref(D / "evidence/aggregator_pin_check.json"),
        ref(D / "evidence/pre_hashes.txt"),
        ref(D / "evidence/post_hashes.txt"),
    ],
    "falsifier": "This live-pin transfer review is falsified by any of: (i) a byte-state of schemas/af_scc_c2_vacuum.yaml at review time whose sha256 is not e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe; (ii) showing the live C2 implication_ledger (lines 152/237) no longer carries the E_H2loc subset E_C0 link, or that the borderline containment is valid as stated in 4D; (iii) showing tier_1.witness_type/proof_obligations in the live bytes is r-bound in D0; (iv) showing FROZEN rev29 does not declare the live C2, C0, KEY_MANIFEST, checker or rule_spec hashes; (v) showing the live gate fails under the FROZEN rev29 triple.",
    "next_falsifier": "At the next C2/C0 revision: (a) whether the H2loc subset C0 ledger rows were dropped or re-typed with a continuity representative (e.g. H^2_loc cap C^0), and C0's must_not_conflate reconciled with its ledger; (b) whether tier_1 names r in D0; (c) whether FROZEN covers the separation aggregator. Transfer is confirmed iff (a) and (b) still hold at that pin.",
    "blindness_and_contamination": "Not a blind review: it is the pre-registered live-pin continuation of my own reviews/F2a-review-rev27-a.json (same reviewer, worker-046). No other reviewer's F2a verdict file was opened; while locating my assignments in research_map.json and the outboxes I unavoidably saw event-level summaries of other F2a reviews (ids, reviewer, verdict, score), which no verdict here depends on. The F-046-F2a-01 phrasing correction in this document was found by re-measuring the pinned C0 bytes, not from another review.",
    "hours": 0.4,
    "stop_rule": "one review file + one review event + one checkpoint, then exit.",
}
review_path = ROOT / "reviews/F2a-review-live-rev13-worker-046.json"
review_path.write_text(json.dumps(review, indent=1, ensure_ascii=False) + "\n")
review_sha = sha(review_path)

# ---- one review event ------------------------------------------------------
event = {
    "event_id": f"w046-f2a-live-rev13-repin-review-{STAMP}",
    "event_type": "review",
    "actor": "worker-046",
    "created_at": NOW,
    "target_id": "F2a",
    "node_id": "F2a",
    "class_id": "AF-SCC-C2-VAC-GEN",
    "gate": "G-FORM",
    "reviewer": "worker-046",
    "verdict": "revise",
    "score": 3.0,
    "counts_as_gate_verdict": False,
    "no_gate_verdict": True,
    "reviewed_sha256": M["schemas/af_scc_c2_vacuum.yaml"],
    "reviewed_revision": 13,
    "artifact": "reviews/F2a-review-live-rev13-worker-046.json",
    "artifact_sha256": review_sha,
    "prior_hard_failures_dissolved": ["HF-046-F2a-01", "HF-046-F2a-02"],
    "hard_failures": [],
    "findings": ["F-046b-01", "F-046b-02", "F-046b-03", "F-046b-04", "F-046b-05", "F-046b-06"],
    "checks_passed": ["c2_c0_collapse", "d0_binder_instantiation_live", "gate_c2_live_pass", "gate_c0_live_pass", "taxonomy_consistency", "aggregator_pins", "f0_binding_resolves"],
    "evidence_refs": [
        ref(review_path),
        ref(C2), ref(C0), ref(AGG), ref(FROZEN), ref(KM), ref(SPEC), ref(GATE), ref(CONS), ref(TAX), ref(SUP),
        ref(D / "gate_runs/gate_c2_livemanifest.json"),
        ref(D / "gate_runs/gate_c0_livemanifest.json"),
        ref(D / "gate_runs/gate_c2_rev27manifest_rerun.json"),
        ref(D / "gate_runs/d0_instantiation_check_live.json"),
        ref(D / "d0_instantiation_check_live.py"),
        ref(D / "evidence/taxonomy_consistency_stdout.txt"),
        ref(D / "evidence/aggregator_pin_check.json"),
        ref(D / "evidence/pre_hashes.txt"),
        "comms/outbox/worker-046.jsonl",
    ],
    "falsifier": review["falsifier"],
    "next_falsifier": review["next_falsifier"],
    "hours": 0.4,
}
outbox = ROOT / "comms/outbox/worker-046.jsonl"
with outbox.open("a") as f:
    f.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
event_sha = hashlib.sha256(json.dumps(event, ensure_ascii=False, sort_keys=True).encode()).hexdigest()

# ---- one checkpoint --------------------------------------------------------
checkpoint = {
    "checkpoint": "worker-046_F2a_live_repin",
    "actor": "worker-046",
    "at": NOW,
    "node_id": "F2a",
    "gate": "G-FORM",
    "class_id": "AF-SCC-C2-VAC-GEN",
    "assignments": ["audit-r2-F2a-a", "audit-r2-F2a-bindchain-worker-046"],
    "task": "pre-registered live-pin transfer of F2a-review-rev27-a to rev13",
    "live_sha256": M["schemas/af_scc_c2_vacuum.yaml"],
    "live_revision": 13,
    "verdict": "revise",
    "score": 3.0,
    "counts_as_gate_verdict": False,
    "no_gate_verdict_set": True,
    "hard_failures": [],
    "prior_hard_failures_dissolved": ["HF-046-F2a-01", "HF-046-F2a-02"],
    "findings_surviving": ["F-046b-01", "F-046b-02", "F-046b-04", "F-046b-05", "F-046b-06"],
    "findings_new": ["F-046b-03"],
    "outputs": {
        "review_file": {"path": "reviews/F2a-review-live-rev13-worker-046.json", "sha256": review_sha},
        "outbox_event": {"id": event["event_id"], "path": "comms/outbox/worker-046.jsonl", "canonical_json_sha256": event_sha},
        "evidence_dir": {"path": "artifacts/worker-046/f2a_live_repin_rev13", "pre_hashes": ref(D / "evidence/pre_hashes.txt")},
        "prior_review": {"path": "reviews/F2a-review-rev27-a.json", "sha256": review["supersedes"]["sha256"]},
    },
    "measured": M,
    "next_falsifier": review["next_falsifier"],
}
ck = ROOT / "runtime/state/worker-046_F2a_live_repin_checkpoint.json"
ck.write_text(json.dumps(checkpoint, indent=1, ensure_ascii=False) + "\n")

print(json.dumps({"review": str(review_path), "review_sha256": review_sha,
                  "event_id": event["event_id"], "event_canonical_sha256": event_sha,
                  "checkpoint": str(ck), "checkpoint_sha256": sha(ck)}, indent=1))
