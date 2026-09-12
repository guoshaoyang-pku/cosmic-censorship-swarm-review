#!/usr/bin/env python3
"""Emit the W023-F2B-DIR-REVIEW-01 checkpoint and outbox events (idempotent by event_id)."""
import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
D = ROOT / "artifacts/worker-023/f2b_dir_review"
TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ).isoformat(timespec="seconds")
STAMP = "20260912T010900"
TASK = "W023-F2B-DIR-REVIEW-01"


def h(p):
    return hashlib.sha256((D / p).read_bytes()).hexdigest()


art = {p: h(p) for p in [
    "proposed_af_scc_c0_vacuum_v1_066.yaml",
    "proposed_af_scc_c0_vacuum_v2_corrected.yaml",
    "proposed_patch_v2_corrected.diff",
    "report.json",
    "verification.json",
    "reproduce_023.py",
    "verify_direction_023.py",
    "README.md",
    "evidence/checks.json",
    "evidence/canonical_gate.json",
    "evidence/probes.json",
    "emit_023.py",
]}
V1, V2 = art["proposed_af_scc_c0_vacuum_v1_066.yaml"], art["proposed_af_scc_c0_vacuum_v2_corrected.yaml"]
LIVE = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"
COMPOSED = "48cadb72e507cfcbc469f6519fcc0294bb83f083cc1733521610ff63e5f3c38a"
W008 = "98f9ec83c487d6920968f0bdf98e03974813376b6d222b617300525eb13feb1c"
REPORT = art["report.json"]
VERIF = art["verification.json"]

FALSIFIER = ("Re-run reproduce_023.py at the same pins. Falsified if: any pinned input hash "
             "differs (verdict void, exit 2); the worker-066 candidate does not reproduce to "
             "84b5d3fa29a6; either reviewed candidate lacks the clause 'H2_loc-inextendibility "
             "ENTAILS this class's conclusion'; the C0 document declares the H2_loc -> C0 edge; "
             "the C2 sibling sentence is shown invalid; the corrected variant fails the canonical "
             "gate; the diff is not confined to the two repair lines; or any control departs from "
             "expectation.")

EV = [
    {"event_id": f"w23-f2bdir-{STAMP}-artifact-v1", "event_type": "artifact", "created_at": NOW,
     "actor": "worker-023", "node_id": "F2b", "gate": "G-FORM",
     "class_id": "AF-SCC-C0-VAC-GEN", "class_ids": ["AF-SCC-C0-VAC-GEN"],
     "task_id": TASK, "artifact_type": "repair_candidate_reproduction",
     "path": "artifacts/worker-023/f2b_dir_review/proposed_af_scc_c0_vacuum_v1_066.yaml",
     "sha256": V1, "validation_status": "unverified", "applied": False,
     "summary": ("Byte-exact reproduction of worker-066's rebased F2b repair candidate "
                 "(84b5d3fa29a6) from the live rev13 bytes plus the published "
                 "f2b_repair_prereg/proposed_patch.diff, by two independent appliers and by "
                 "system patch; the declared candidate bytes are now on disk."),
     "evidence_refs": [f"schemas/af_scc_c0_vacuum.yaml#{LIVE[:12]}",
                       "artifacts/worker-066/f2b_repair_prereg/proposed_patch.diff#d777a8cb84aa"],
     "falsifier": FALSIFIER},
    {"event_id": f"w23-f2bdir-{STAMP}-artifact-v2", "event_type": "artifact", "created_at": NOW,
     "actor": "worker-023", "node_id": "F2b", "gate": "G-FORM",
     "class_id": "AF-SCC-C0-VAC-GEN", "class_ids": ["AF-SCC-C0-VAC-GEN"],
     "task_id": TASK, "artifact_type": "direction_corrected_repair_candidate",
     "path": "artifacts/worker-023/f2b_dir_review/proposed_af_scc_c0_vacuum_v2_corrected.yaml",
     "sha256": V2, "validation_status": "unverified", "applied": False,
     "summary": ("Corrected F2b rev14 containment repair: same two repair lines as 84b5d3fa "
                 "with must_not_conflate[0] direction fixed to the document's own order "
                 "('this class's conclusion ENTAILS H2_loc-inextendibility and "
                 "C2-inextendibility, never the reverse'). Passes the direction probe by "
                 "declared graph and by set ranks and the canonical gate; diff confined to "
                 "lines 152/246."),
     "evidence_refs": [f"schemas/af_scc_c0_vacuum.yaml#{LIVE[:12]}",
                       f"artifacts/worker-023/f2b_dir_review/report.json#{REPORT[:12]}"],
     "falsifier": FALSIFIER},
    {"event_id": f"w23-f2bdir-{STAMP}-artifact-patch", "event_type": "artifact", "created_at": NOW,
     "actor": "worker-023", "node_id": "F2b", "gate": "G-FORM",
     "class_id": "AF-SCC-C0-VAC-GEN", "class_ids": ["AF-SCC-C0-VAC-GEN"],
     "task_id": TASK, "artifact_type": "proposed_patch_direction_corrected",
     "path": "artifacts/worker-023/f2b_dir_review/proposed_patch_v2_corrected.diff",
     "sha256": art["proposed_patch_v2_corrected.diff"], "validation_status": "unverified",
     "applied": False,
     "summary": "Unified diff live rev13 b2ab6acb -> direction-corrected candidate 9ab32ee3; applies cleanly and reproduces the candidate bytes (runner check N2).",
     "evidence_refs": [f"artifacts/worker-023/f2b_dir_review/proposed_af_scc_c0_vacuum_v2_corrected.yaml#{V2[:12]}"],
     "falsifier": FALSIFIER},
    {"event_id": f"w23-f2bdir-{STAMP}-artifact-report", "event_type": "artifact", "created_at": NOW,
     "actor": "worker-023", "node_id": "F2b", "gate": "G-FORM",
     "class_id": "AF-SCC-C0-VAC-GEN", "class_ids": ["AF-SCC-C0-VAC-GEN"],
     "task_id": TASK, "artifact_type": "review_report",
     "path": "artifacts/worker-023/f2b_dir_review/report.json", "sha256": REPORT,
     "validation_status": "unverified", "applied": False,
     "summary": "32/32 checks: candidate reproduction, document-internal entailment-direction probe, controls, canonical-gate blindness matrix, change confinement, pin guard.",
     "evidence_refs": [f"artifacts/worker-023/f2b_dir_review/evidence/checks.json#{art['evidence/checks.json'][:12]}"],
     "falsifier": FALSIFIER},
    {"event_id": f"w23-f2bdir-{STAMP}-artifact-verification", "event_type": "artifact", "created_at": NOW,
     "actor": "worker-023", "node_id": "F2b", "gate": "G-FORM",
     "class_id": "AF-SCC-C0-VAC-GEN", "class_ids": ["AF-SCC-C0-VAC-GEN"],
     "task_id": TASK, "artifact_type": "independent_verification",
     "path": "artifacts/worker-023/f2b_dir_review/verification.json", "sha256": VERIF,
     "validation_status": "unverified", "applied": False,
     "summary": "37/37 independent checks (separate code path): system-patch reconstruction, rank-based direction rule, graph cross-check, v2 byte recomputation, gate re-execution, report consistency.",
     "evidence_refs": [f"artifacts/worker-023/f2b_dir_review/report.json#{REPORT[:12]}"],
     "falsifier": FALSIFIER},
    {"event_id": f"w23-f2bdir-{STAMP}-claim", "event_type": "claim", "created_at": NOW,
     "actor": "worker-023", "node_id": "F2b", "gate": "G-FORM",
     "class_id": "AF-SCC-C0-VAC-GEN", "class_ids": ["AF-SCC-C0-VAC-GEN"],
     "task_id": TASK, "conclusion_type": "formal_model",
     "artifact_refs": [f"artifacts/worker-023/f2b_dir_review/report.json#{REPORT[:12]}",
                       f"artifacts/worker-023/f2b_dir_review/proposed_af_scc_c0_vacuum_v2_corrected.yaml#{V2[:12]}"],
     "assumptions": [
         "read-only on canonical paths; both candidate files are proposals (applied=false)",
         "the direction predicate is the document's own declared one_way_entailments graph plus the declared extension-set containment order; no external mathematics is imported",
         "the canonical structural gate is the binding gate implementation; its blindness to this slot is measured, not assumed",
         "worker-level evidence: no node status, no gate verdict, no validation_status=passed"],
     "statement": (
         "At the pinned bytes (live F2b schemas/af_scc_c0_vacuum.yaml b2ab6acb2bbe; FROZEN "
         "rev29 815e0807), the standing F2b containment repair -- worker-066 candidate 84b5d3fa "
         "(reproduced byte-exactly here) and worker-044 composed rev14 candidate 48cadb72 -- "
         "fixes the reviewed size-premise defect but introduces in regularity.must_not_conflate[0] "
         "the sentence 'H2_loc-inextendibility ENTAILS this class's conclusion'. For "
         "AF-SCC-C0-VAC-GEN that entailment is false and is the reverse of the document's own "
         "declared graph (one_way_entailments declares C0-inextendibility -> H2_loc-inextendibility; "
         "forbidden_weakenings[2] says H2_loc-inextendibility 'is weaker and entails the C2 sibling, "
         "not this class'; subsumption_note says 'C0 => H2loc => C2, never the reverse'), because "
         "E_C0 is the largest extension set (ranks C2 0 < C^1,1 1 < H2loc 2 < C0 3). The sentence is "
         "correct in the C2 sibling and was copied verbatim from it; it licenses exactly the "
         "substitution the C0 file forbids. The canonical R06 gate returns pass for the defective "
         "candidates, for a direction-reversed mutant, for a nonsense clause and for an emptied "
         "single item; it fails only when the whole must_not_conflate list is emptied, so the gate "
         "cannot certify this slot. Corrected variant 9ab32ee3 (same two repair lines, direction "
         "reversed to the file's own order) passes the probe by declared graph and by set ranks, "
         "the canonical gate, and is byte-confined to lines 152/246."),
     "evidence_refs": [f"schemas/af_scc_c0_vacuum.yaml#{LIVE[:12]}",
                       f"schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3",
                       f"artifacts/formulation/rule_spec.json#40f9bb9e657b",
                       f"artifacts/formulation/tools/check_class_schema.py#000e09e46b2f",
                       f"artifacts/worker-044/f2b_live_closure_01/sandbox/schemas/af_scc_c0_vacuum.yaml#{COMPOSED[:12]}",
                       f"artifacts/worker-008/f2b_rev11_dualrepair/candidate_rev12/af_scc_c0_vacuum.yaml#{W008[:12]}",
                       f"artifacts/worker-023/f2b_dir_review/report.json#{REPORT[:12]}",
                       f"artifacts/worker-023/f2b_dir_review/verification.json#{VERIF[:12]}"],
     "falsifier": FALSIFIER},
    {"event_id": f"w23-f2bdir-{STAMP}-review", "event_type": "review", "created_at": NOW,
     "actor": "worker-023", "node_id": "F2b", "gate": "G-FORM",
     "class_id": "AF-SCC-C0-VAC-GEN", "class_ids": ["AF-SCC-C0-VAC-GEN"],
     "task_id": TASK, "reviewer": "worker-023",
     "target_id": f"artifacts/worker-044/f2b_live_closure_01/sandbox/schemas/af_scc_c0_vacuum.yaml#{COMPOSED[:12]}",
     "target": {"composed_044_sha256": COMPOSED, "worker_066_candidate_sha256": V1,
                "worker_008_candidate_sha256": W008, "live_sha256": LIVE,
                "clause_byte_identical_across_all_three": True},
     "verdict": "revise", "score": 2.0, "counts_as_full_schema_verdict": False,
     "scope": "containment-repair text review at the cited hashes; not a full-schema F2b verdict",
     "hard_failures": [{"id": "W023-F2B-DIR1",
                        "carrier": "regularity.must_not_conflate[0]", "line": 152,
                        "finding": "replacement sentence inverts the C0 entailment direction relative to the document's own one_way_entailments/forbidden_weakenings/subsumption_note and set ranks"}],
     "findings": [
         "W023D-F1 [hard] candidate 84b5d3fa reproduces byte-exactly from the published patch, and 48cadb72 carries the same clause byte-for-byte; both assert H2_loc-inextendibility ENTAILS the C0 class conclusion, which the C0 document itself denies (C0 => H2loc => C2, never the reverse).",
         "W023D-F2 [major] the sentence is valid in the C2 sibling (E_C2 subset of E_H2loc) and was copied verbatim; a class-relative direction check, not a keyword check, is required.",
         "W023D-F3 [major] gate gap reproduced: R06 passes a direction-reversed mutant, a nonsense item and an emptied single item; only an emptied list fails. The slot content is not machine-certified, so a G-FORM accept at these bytes would freeze the inversion.",
         "W023D-F4 [information] the size-premise fix (larger -> smaller, E_C2 subset of E_C0) is correct and is retained in the corrected variant.",
         "W023D-F5 [advisory] worker-044's composed candidate is otherwise ready (verify_frozen rc 0; the three schema gates rc 0); only the corrected clause blocks a clean F2b rev14 acceptance."],
     "evidence_refs": [f"artifacts/worker-023/f2b_dir_review/report.json#{REPORT[:12]}",
                       f"artifacts/worker-023/f2b_dir_review/verification.json#{VERIF[:12]}",
                       f"artifacts/worker-023/f2b_dir_review/proposed_patch_v2_corrected.diff#{art['proposed_patch_v2_corrected.diff'][:12]}",
                       f"schemas/af_scc_c0_vacuum.yaml#{LIVE[:12]}",
                       f"schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3"],
     "falsifier": FALSIFIER},
    {"event_id": f"w23-f2bdir-{STAMP}-blocker", "event_type": "blocker", "created_at": NOW,
     "actor": "worker-023", "node_id": "F2b", "gate": "G-FORM",
     "class_id": "AF-SCC-C0-VAC-GEN", "class_ids": ["AF-SCC-C0-VAC-GEN"],
     "task_id": TASK,
     "description": ("The standing F2b repair as written (worker-066 84b5d3fa, worker-044 composed "
                     "48cadb72) is not direction-finding-free: its must_not_conflate[0] replacement "
                     "asserts an entailment the C0 document itself denies. Landing it would freeze a "
                     "normative inversion in a required R06 slot that the canonical gate cannot see."),
     "needed_to_unblock": ("lead-formulation lands a direction-corrected rev14 clause (candidate "
                           "9ab32ee3 / proposed_patch_v2_corrected.diff, or equivalent wording that "
                           "puts the C0 => H2loc => C2 direction), then re-runs the F2b reviewers at "
                           "the new hash. Recommended alongside: add a containment/entailment-direction "
                           "predicate to check_class_schema.py so R06/R16 certify the slot content."),
     "evidence_refs": [f"artifacts/worker-023/f2b_dir_review/proposed_af_scc_c0_vacuum_v2_corrected.yaml#{V2[:12]}",
                       f"artifacts/worker-023/f2b_dir_review/report.json#{REPORT[:12]}",
                       f"artifacts/worker-023/f2b_dir_review/verification.json#{VERIF[:12]}",
                       f"schemas/af_scc_c0_vacuum.yaml#{LIVE[:12]}"],
     "falsifier": FALSIFIER},
    {"event_id": f"w23-f2bdir-{STAMP}-status", "event_type": "status", "created_at": NOW,
     "actor": "worker-023", "node_id": "F2b", "gate": "G-FORM",
     "class_id": "AF-SCC-C0-VAC-GEN", "class_ids": ["AF-SCC-C0-VAC-GEN"],
     "task_id": TASK, "status": "active", "hours": 0.4,
     "summary": ("One bounded class-bound task complete (W023-F2B-DIR-REVIEW-01), checkpoint "
                 "runtime/state/w023_checkpoint_4.json written, exiting. Task self-selected from the "
                 "open L-FORM-01/H1+H2 repair thread at F2b; no inbox card existed. Deliverable: "
                 "byte-exact candidate reproduction, direction hard finding with corrected variant, "
                 "32/32 runner checks and 37/37 independent checks. Worker level only: no node "
                 "status, no gate verdict, no validation_status=passed."),
     "evidence_refs": [f"artifacts/worker-023/f2b_dir_review/report.json#{REPORT[:12]}",
                       f"artifacts/worker-023/f2b_dir_review/verification.json#{VERIF[:12]}",
                       "runtime/state/w023_checkpoint_4.json"],
     "next_falsifier": FALSIFIER},
]

OUT = ROOT / "comms/outbox/worker-023.jsonl"
existing = set()
if OUT.exists():
    for line in OUT.read_text().splitlines():
        try:
            existing.add(json.loads(line).get("event_id"))
        except Exception:
            pass
new = [e for e in EV if e["event_id"] not in existing]
with OUT.open("a") as f:
    for e in new:
        f.write(json.dumps(e, sort_keys=True) + "\n")

ckpt = {
    "task_id": TASK, "actor": "worker-023", "node_id": "F2b", "gate": "G-FORM",
    "class_id": "AF-SCC-C0-VAC-GEN", "created_at": NOW,
    "status": "complete", "verdict": "revise", "score": 2.0,
    "hard_failure": "W023-F2B-DIR1",
    "pins": {"schemas/af_scc_c0_vacuum.yaml": LIVE,
             "schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
             "artifacts/formulation/FROZEN.json": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"},
    "artifacts": {k: v for k, v in art.items()},
    "artifacts_abs": {k: str((D / k)) for k in art},
    "runner": {"checks_passed": 32, "checks_total": 32},
    "verifier": {"checks_passed": 37, "checks_total": 37},
    "corrected_candidate_sha256": V2,
    "events_emitted": len(new),
    "non_claims": ["not a gate verdict", "not a node completion",
                   "not an applied canonical change"],
}
(ROOT / "runtime/state/w023_checkpoint_4.json").write_text(json.dumps(ckpt, indent=2, sort_keys=True))
print(f"emitted {len(new)} events; checkpoint written; artifacts={len(art)}")
