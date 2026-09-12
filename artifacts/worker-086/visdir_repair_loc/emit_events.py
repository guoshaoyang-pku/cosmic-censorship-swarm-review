#!/usr/bin/env python3
"""Emit W086-GFORM-VISDIR-RESIDUAL-01 deliverables: review record, events, checkpoint.

Idempotency guard: refuses to run if an outbox event with the w086-visdir-residual-
prefix already exists.  Writes only its own directory, reviews/, comms/outbox/worker-086.jsonl,
runtime/state/w086_visdir_repair_loc_checkpoint.json and runtime/state/worker-086_checkpoints.jsonl.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUTBOX = ROOT / "comms/outbox/worker-086.jsonl"
REVIEW_PATH = ROOT / "reviews/G-FORM-visdir-residual-086.json"
CKPT_PATH = ROOT / "runtime/state/w086_visdir_repair_loc_checkpoint.json"
CKPT_LOG = ROOT / "runtime/state/worker-086_checkpoints.jsonl"
TASK = "W086-GFORM-VISDIR-RESIDUAL-01"
CLASS_ID = "AF-WCC-VAC-GEN"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C0-VAC-GEN"]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    if OUTBOX.exists() and "w086-visdir-residual-" in OUTBOX.read_text(encoding="utf-8", errors="ignore"):
        print("already emitted; refusing duplicate")
        return 1
    ts = dt.datetime.now().astimezone().replace(microsecond=0).isoformat()
    tag = ts.replace("-", "").replace(":", "").replace("+", "p")

    report = json.loads((HERE / "report.json").read_text())
    verdict = report["verdict"]
    pins = {k: v["measured"] for k, v in report["measured_pins"].items() if v.get("measured")}
    residual = report["residual_census"]
    decisions = report["decision_items"]

    files = {
        "artifacts/worker-086/visdir_repair_loc/probe_visdir.py": "deterministic_probe",
        "artifacts/worker-086/visdir_repair_loc/report.json": "verification_report",
        "artifacts/worker-086/visdir_repair_loc/candidate/candidate_patch.json": "residual_patch_state",
        "artifacts/worker-086/visdir_repair_loc/patch_candidate.diff": "residual_patch_diff",
        "artifacts/worker-086/visdir_repair_loc/README.md": "summary",
        "artifacts/worker-086/visdir_repair_loc/emit_events.py": "event_emitter",
    }
    hashes = {rel: sha(ROOT / rel) for rel in files}

    # ---------------- review record
    findings = [
        {
            "id": "F-086-V1",
            "severity": "info",
            "kind": "verified",
            "statement": "Independent exhaustive order-theoretic check confirms the rev13 direction: fixed-q whole containment is EQUIVALENT to fixed-q tail containment (0/60598 violations over 389 preorders with <=4 points) and VIS_tail => VIS_set with an omega-chain separating VIS_set from VIS_tail; hence variant SET is strictly WEAKER than AF-WCC-VAC-GEN.",
            "evidence": ["artifacts/worker-086/visdir_repair_loc/report.json"],
        },
        {
            "id": "F-086-V2",
            "severity": "info",
            "kind": "verified",
            "statement": "At F1 rev13 (d9cebb9404b2e79e, canonical and mirror) the variant-SET relation reads strictly WEAKER, the D5 whole-vs-tail note proves EQUIVALENT, the unsound misclassification rationale is gone, and the negation-level and falsifier lines are correct. CH is correct in schemas/af_scc_c0_vacuum.yaml and VARIANT_REGISTRY.json.",
            "evidence": ["schemas/af_wcc_vacuum.yaml#d9cebb9404b2e79e", "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe7f86"],
        },
        {
            "id": "F-086-V3",
            "severity": "info",
            "kind": "verified",
            "statement": "Mechanical residual re-base verified: SET/CH deltas and VARIANT_REGISTRY.json re-based to the rev13 bases, SET strength flipped, 9/9 re-base assertions hold, check_variant_deltas and check_variant_registry both VALID, both evidence files match their FROZEN rev29 pins.",
            "evidence": ["artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json#64b8d6394a044686", "artifacts/formulation/VARIANT_REGISTRY.json#6bac9adea19e17ef"],
        },
        {
            "id": "F-086-V4",
            "severity": "major",
            "kind": "residual_decision",
            "statement": "research_map/formulation_taxonomy.yaml:200 still asserts the set-based reading 'is strictly stronger'. This is G-F0 canonical 0abb9ed8a961, frozen by REC-11: any write voids G-F0 and requires fresh independent accepts. Corroborates lead blocker L-FORM-03.",
            "evidence": ["research_map/formulation_taxonomy.yaml#0abb9ed8a961", "runtime/state/controller_verification/astra-lifecycle-05-decisions.json#REC-11"],
        },
        {
            "id": "F-086-V5",
            "severity": "minor",
            "kind": "residual_decision",
            "statement": "artifacts/formulation/formulation_taxonomy.yaml:176 (D1 ledger) labels the F0 exclusion reading '(strictly stronger)'. That attaches to not-SET, which IS strictly stronger than not-tail, so the row is negation-level and ambiguous rather than plainly inverted; propose clarification, not a flip. Corroborates L-FORM-03.",
            "evidence": ["artifacts/formulation/formulation_taxonomy.yaml#d7419b4e8963"],
        },
    ]
    review = {
        "schema": "review/0.1",
        "review_id": "G-FORM-visdir-residual-086",
        "created_at": ts,
        "reviewer": "worker-086",
        "node_id": "F1",
        "node_ids": ["F1", "F2b"],
        "class_id": CLASS_ID,
        "class_ids": CLASS_IDS,
        "gate": "G-FORM",
        "review_kind": "post_repair_direction_verification_and_residual_census",
        "scope": "REC-12 item 3 direction leg only: F1 variant-SET / whole-vs-tail strictness at rev13, CH cross-check, variant re-base state, exhaustive residual census. Not a full-schema content review of F1, F2a or F2b.",
        "counts_as_full_schema_verdict": False,
        "counts_as_independent": True,
        "target_id": "F1",
        "target_id_full": "F1 visibility strictness direction leg at schemas/af_wcc_vacuum.yaml d9cebb9404b2e79e (rev13) on FROZEN rev29",
        "target_sha256": pins.get("schemas/af_wcc_vacuum.yaml"),
        "verdict": "accept",
        "score": 4.0,
        "score_rationale": "The direction leg is verified at the pinned bytes by an independent exhaustive method and the mechanical residual carries are clean; two F0-level decision items (R1 canonical, R2 supplement) are outside this leg and remain with the controller.",
        "hard_failures": [],
        "open_items": [
            "R1 research_map/formulation_taxonomy.yaml:200 - G-F0-frozen inverted note; controller/Human-PI decision (edit + F0 re-round, or documented waiver)",
            "R2 artifacts/formulation/formulation_taxonomy.yaml:176 - negation-level ambiguity; clarify + consistency re-run + FROZEN re-pin",
            "L-FORM-04 (lead-reported, not measured here) schemas/f1_falsifier_tests.jsonl rows still bind F1 rev12",
        ],
        "findings": findings,
        "evidence_refs": [
            "artifacts/worker-086/visdir_repair_loc/report.json#" + hashes["artifacts/worker-086/visdir_repair_loc/report.json"][:12],
            "artifacts/worker-086/visdir_repair_loc/probe_visdir.py#" + hashes["artifacts/worker-086/visdir_repair_loc/probe_visdir.py"][:12],
            "schemas/af_wcc_vacuum.yaml#d9cebb9404b2e79e",
            "artifacts/formulation/schemas/af_wcc_vacuum.yaml#d9cebb9404b2e79e",
            "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe7f86",
            "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json#64b8d6394a044686",
            "artifacts/formulation/VARIANT_REGISTRY.json#6bac9adea19e17ef",
            "artifacts/formulation/FROZEN.json#815e08079aefbc16",
            "artifacts/formulation/evidence/variant_delta_check.json#fc6ee058dd961275",
            "artifacts/formulation/evidence/variant_registry_check.json#164a9a846e253616",
            "artifacts/formulation/tools/variant_rebase_rev29.py",
        ],
        "artifact_sha256": hashes["artifacts/worker-086/visdir_repair_loc/report.json"],
        "review_path": "reviews/G-FORM-visdir-residual-086.json",
        "falsifier": "An asserting live carrier of the inverted direction beyond the two F0 artifacts; a finite causal chain with VIS_set and not VIS_tail; a q with tail subset J^-(q) but whole not subset J^-(q); or a frozen pin that stops matching live bytes.",
    }
    REVIEW_PATH.write_text(json.dumps(review, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    review_hash = sha(REVIEW_PATH)

    # ---------------- manifest (excludes itself)
    manifest_lines = [f"{hashes[rel]}  {rel}" for rel in sorted(hashes)]
    manifest_lines.append(f"{review_hash}  reviews/G-FORM-visdir-residual-086.json")
    manifest_path = HERE / "MANIFEST.sha256"
    manifest_path.write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
    manifest_hash = sha(manifest_path)

    base = {"actor": "worker-086", "created_at": ts, "node_id": "F1", "node_ids": ["F1", "F2b"],
            "gate": "G-FORM", "class_id": CLASS_ID, "class_ids": CLASS_IDS}
    events = []
    events.append({**base, "event_id": f"w086-visdir-residual-{tag}-task", "event_type": "status",
                   "status": "active", "hours": 0.7,
                   "summary": "Took one bounded class-bound task W086-GFORM-VISDIR-RESIDUAL-01 (no inbox card): post-rev13 verification of the F1 variant-SET/CH visibility strictness direction (REC-12 item 3), independent exhaustive direction proof, exhaustive residual-carrier census, and state of the mechanical variant re-base. Verdict " + verdict + ".",
                   "evidence_refs": ["artifacts/worker-086/visdir_repair_loc/report.json"],
                   "next_falsifier": "Re-run probe_visdir.py at the next F1/registry/taxonomy/FROZEN revision; a changed sha256 voids the snapshot."})
    for rel, kind in files.items():
        events.append({**base, "event_id": f"w086-visdir-residual-{tag}-art-{kind}", "event_type": "artifact",
                       "artifact_type": kind, "path": rel, "sha256": hashes[rel], "validation_status": "unverified",
                       "summary": f"{kind} for {TASK} at F1 rev13 d9cebb9404b2e79e / FROZEN rev29."})
    events.append({**base, "event_id": f"w086-visdir-residual-{tag}-art-review", "event_type": "artifact",
                   "artifact_type": "review_record", "path": "reviews/G-FORM-visdir-residual-086.json",
                   "sha256": review_hash, "validation_status": "unverified",
                   "summary": "Independent direction-leg review: accept 4.0 (counts_as_full_schema_verdict=false); R1/R2 F0 decisions open."})
    events.append({**base, "event_id": f"w086-visdir-residual-{tag}-art-manifest", "event_type": "artifact",
                   "artifact_type": "manifest", "path": "artifacts/worker-086/visdir_repair_loc/MANIFEST.sha256",
                   "sha256": manifest_hash, "validation_status": "unverified",
                   "summary": "sha256 of every file in the deliverable directory plus the review record."})
    events.append({**base, "event_id": f"w086-visdir-residual-{tag}-claim", "event_type": "claim",
                   "conclusion_type": "stability_result",
                   "statement": ("Artifact-and-checker measurement, not a mathematics or physics claim, at F1 rev13 d9cebb9404b2e79e / FROZEN rev29 815e08079aefbc16: "
                                 "(a) the REC-12 item-3 direction repair is verified - variant SET is strictly WEAKER than AF-WCC-VAC-GEN, proved by exhaustive finite-preorder checks "
                                 "(389 preorders, 60598 chain x Q evaluations, 0 violations of L1/L2/L3/L5) plus an omega-chain strictness certificate, and the rev12 'strictly STRONGER' "
                                 "labels at F1 lines 72/234 are corrected at the live bytes with the unsound misclassification rationale removed; CH is correct in schema and registry; "
                                 "(b) the mechanical residual re-base landed 00:57:02 and is verified 9/9 (delta bases at rev13, changes[1].from == live F1 definition, SET strength/definition "
                                 "weaker, w076 evidence ref, check_variant_deltas and check_variant_registry VALID, both evidence files matching FROZEN pins); (c) the exhaustive live-carrier census "
                                 "leaves exactly one asserting carrier of the inverted direction, research_map/formulation_taxonomy.yaml:200, which is G-F0 canonical 0abb9ed8a961 frozen by REC-11, "
                                 "plus one negation-level ambiguity at artifacts/formulation/formulation_taxonomy.yaml:176 - both are controller/Human-PI decisions and corroborate lead blocker L-FORM-03."),
                   "assumptions": ["The pinned schema, registry, delta, taxonomy and FROZEN bytes are the intended rev13/rev29 publication set.",
                                   "J^-(q) is past-closed and gamma is future-directed causal in the order-theoretic reading of the visibility predicates, as the class text asserts.",
                                   "Event records, tool OLD-constants, worker snapshots and reviews are mentions/history, not live assertions to be edited."],
                   "falsifier": review["falsifier"],
                   "evidence_refs": review["evidence_refs"],
                   "artifact_refs": ["artifacts/worker-086/visdir_repair_loc/report.json#" + hashes["artifacts/worker-086/visdir_repair_loc/report.json"][:12],
                                     "reviews/G-FORM-visdir-residual-086.json#" + review_hash[:12]]})
    events.append({**base, "event_id": f"w086-visdir-residual-{tag}-review", "event_type": "review",
                   "reviewer": "worker-086", "independent": True, "counts_as_full_schema_verdict": False,
                   "target_id": "F1", "target_id_full": review["target_id_full"], "target_sha256": review["target_sha256"],
                   "verdict": "accept", "score": 4.0, "hard_failures": [], "findings": [f["id"] for f in findings],
                   "open_items": review["open_items"], "review_path": review["review_path"], "review_sha256": review_hash,
                   "artifact_sha256": hashes["artifacts/worker-086/visdir_repair_loc/report.json"],
                   "summary": "Direction leg verified at F1 rev13; mechanical residual carries clean; R1 (G-F0 canonical :200) and R2 (supplement D1 :176) left to a controller ruling.",
                   "falsifier": review["falsifier"]})
    events.append({**base, "event_id": f"w086-visdir-residual-{tag}-status", "event_type": "status",
                   "status": "active", "hours": 0.7,
                   "summary": "W086-GFORM-VISDIR-RESIDUAL-01 complete at worker level and exiting. Verdict " + verdict + "; direction verified by exhaustive finite check + omega certificate; residual census 1 assertion (G-F0 canonical :200), 1 negation-level decision (supplement :176); node status deliberately unchanged (worker events cannot set done/passed/gate verdict). Checkpoint runtime/state/w086_visdir_repair_loc_checkpoint.json.",
                   "evidence_refs": review["evidence_refs"],
                   "artifact_refs": ["artifacts/worker-086/visdir_repair_loc/report.json#" + hashes["artifacts/worker-086/visdir_repair_loc/report.json"][:12]],
                   "next_falsifier": review["falsifier"]})

    with OUTBOX.open("a", encoding="utf-8") as fh:
        for e in events:
            fh.write(json.dumps(e, sort_keys=True) + "\n")

    checkpoint = {
        "checkpoint_id": f"w086-visdir-residual-ckpt-{tag}",
        "task_id": TASK,
        "worker": "worker-086",
        "node_id": "F1",
        "node_ids": ["F1", "F2b"],
        "class_ids": CLASS_IDS,
        "gate": "G-FORM",
        "created_at": ts,
        "status": "complete",
        "verdict": verdict,
        "result": "Direction repair verified (exhaustive 389-preorder check + omega certificate, 0 violations); rev13 bytes carry the corrected weaker/equivalence text; mechanical variant re-base verified 9/9; residual census: 1 asserting carrier (research_map/formulation_taxonomy.yaml:200, G-F0 frozen), 1 negation-level decision (artifacts/formulation/formulation_taxonomy.yaml:176); L-FORM-04 noted as lead-reported and out of scope.",
        "checks": "math L1/L2/L3/L5 0 failures, L4 omega separation; 9/9 re-base assertions; census 1/1/3/11/2 (assertion/negation/tool-constant/event-mention/historical); checkers VALID; pins 10/10 match.",
        "artifacts": {**hashes, "reviews/G-FORM-visdir-residual-086.json": review_hash,
                      "artifacts/worker-086/visdir_repair_loc/MANIFEST.sha256": manifest_hash},
        "pinned_targets": pins,
        "open_items": review["open_items"],
        "falsifier": review["falsifier"],
        "next_falsifier": "Re-run artifacts/worker-086/visdir_repair_loc/probe_visdir.py after any F1/registry/taxonomy/FROZEN revision.",
    }
    CKPT_PATH.write_text(json.dumps(checkpoint, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    with CKPT_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(checkpoint, sort_keys=True) + "\n")

    print(json.dumps({"events": len(events), "review_sha256": review_hash, "manifest_sha256": manifest_hash,
                      "checkpoint": str(CKPT_PATH), "verdict": verdict}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
