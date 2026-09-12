#!/usr/bin/env python3
"""Emit W062-GFORM-R03-SCHEMA-REPAIR-CANDIDATE-01 events to comms/outbox/worker-062.jsonl.

Every event is validated with research_map.schemas.validate_event BEFORE anything is written.
Writes TASK/CHECKPOINT.json and runtime/state/w062_r03_schema_repair_checkpoint.json.
Refuses to run twice unless --force (idempotence guard on the w062-r03- prefix).
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TASK = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from research_map.schemas import validate_event  # noqa: E402

LABEL = "w062-r03-20260912T0115"
ACTOR = "worker-062"
OUTBOX = ROOT / "comms/outbox/worker-062.jsonl"
STATE = ROOT / "runtime/state/w062_r03_schema_repair_checkpoint.json"


def now_iso():
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ref(p: str, h: str) -> str:
    return f"{p}#{h[:12]}"


def main() -> int:
    force = "--force" in sys.argv
    if OUTBOX.exists() and not force and f'"{LABEL}' in OUTBOX.read_text(errors="replace"):
        print("REFUSING: events for this label already emitted; pass --force to append anyway")
        return 2

    rep = json.loads((TASK / "report.json").read_text())
    controls = json.loads((TASK / "controls.json").read_text())
    f1 = rep["t0_hashes"]["artifacts/formulation/schemas/af_wcc_vacuum.yaml"]
    c0 = rep["t0_hashes"]["artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"]
    ca = rep["candidates"]["CAND-A"]
    cb = rep["candidates"]["CAND-B"]
    k2 = rep["post_hoc_additions"]["K2_coverage_gap"]

    # repo-relative paths (protocol rule 4); the first emission used task-relative names and
    # was corrected by PATH_CORRECTION.json / the w062-r03-...-correction status addendum.
    prefix = "artifacts/worker-062/r03_schema_repair_candidate/"
    files = {
        "artifact_cand_a": prefix + "candidates/CAND-A_af_wcc_vacuum.yaml",
        "artifact_cand_b": prefix + "candidates/CAND-B_af_wcc_vacuum.yaml",
        "artifact_diff_a": prefix + "diffs/CAND-A.diff",
        "artifact_diff_b": prefix + "diffs/CAND-B.diff",
        "artifact_report": prefix + "report.json",
        "artifact_controls": prefix + "controls.json",
        "artifact_runner": prefix + "run_r03_repair_candidate.py",
        "artifact_prereg": prefix + "PREREGISTRATION.json",
        "artifact_readme": prefix + "README.md",
    }
    H = {k: sha256(ROOT / v) for k, v in files.items()}
    ev_hash = {k: ref(v, H[k]) for k, v in files.items()}
    entry_hashes = {
        "task_id": rep["task_id"], "label": LABEL, "created_at": now_iso(), "worker": ACTOR,
        "canonical_T0": rep["t0_hashes"], "canonical_T1": rep["t1_hashes"],
        "artifacts": {v: H[k] for k, v in files.items()},
        "candidate_sha256": {"CAND-A": ca["sha256"], "CAND-B": cb["sha256"]},
        "detector_tools": rep["detector_tools"],
    }
    (TASK / "entry_hashes.json").write_text(json.dumps(entry_hashes, indent=2) + "\n")
    H["artifact_entry_hashes"] = sha256(TASK / "entry_hashes.json")
    files["artifact_entry_hashes"] = prefix + "entry_hashes.json"
    ev_hash["artifact_entry_hashes"] = ref(files["artifact_entry_hashes"], H["artifact_entry_hashes"])

    base_evidence = [
        ev_hash["artifact_report"], ev_hash["artifact_cand_a"], ev_hash["artifact_cand_b"],
        ev_hash["artifact_diff_a"], ev_hash["artifact_diff_b"], ev_hash["artifact_controls"],
        ev_hash["artifact_prereg"], ev_hash["artifact_runner"], ev_hash["artifact_readme"],
        f"artifacts/formulation/FROZEN.json#815e08079aef",
        ref("artifacts/formulation/schemas/af_wcc_vacuum.yaml", f1),
        ref("artifacts/formulation/schemas/af_scc_c0_vacuum.yaml", c0),
    ]
    falsifier = rep["falsifier"]

    def artifact_event(key, atype, summary, node="F1"):
        return {
            "event_id": f"{LABEL}-" + key.replace("_", "-"), "event_type": "artifact", "created_at": now_iso(),
            "actor": ACTOR, "node_id": node, "nodes": rep["nodes"], "gate": rep["gate"],
            "task_id": rep["task_id"], "class_id": rep["class_id"], "class_ids": rep["class_ids"],
            "artifact_type": atype, "path": files[key], "sha256": H[key],
            "validation_status": "unverified", "artifact_refs": [ev_hash[key]],
            "evidence_refs": base_evidence, "falsifier": falsifier, "summary": summary,
        }

    events = [
        artifact_event("artifact_cand_a", "class_bound_schema_repair_candidate",
                       f"CAND-A formal product-notation repair candidate for F1 quantifiers.formal: full candidate schema bytes (sha256 {ca['sha256'][:12]}). Frozen pipeline PASS rc 0, union 31/31."),
        artifact_event("artifact_cand_b", "class_bound_schema_repair_candidate",
                       f"CAND-B ordered-binder minimal repair candidate for F1 quantifiers.ordered[5].binder (rev11 precedent): full candidate schema bytes (sha256 {cb['sha256'][:12]}). Frozen pipeline PASS rc 0, union 31/31."),
        artifact_event("artifact_diff_a", "unified_diff",
                       "One-line unified diff canonical F1 -> CAND-A (quantifiers.formal product notation)."),
        artifact_event("artifact_diff_b", "unified_diff",
                       "One-line unified diff canonical F1 -> CAND-B (binder '(q,t0)' -> 'q')."),
        artifact_event("artifact_report", "class_bound_repair_validation_report",
                       f"Machine report: baseline rc 1 FAIL F1 R03 (union 31/31); CAND-A and CAND-B each rc 0 PASS, 3/3 canonical ok, union 31/31; P1-P10 pass; K1/K2b/K3/K4/K5 pass; declared K2 miss recorded with instrument-coverage disposition; canonical pins stable T0->T1."),
        artifact_event("artifact_controls", "control_table",
                       "Control table incl. the pre-registered K2 miss (pipeline does not cover f0_binding.consistency_evidence_sha256) and the disclosed post-hoc K2b."),
        artifact_event("artifact_runner", "reproducible_runner",
                       "Deterministic harness: rebuilds the mirror sandbox, reproduces the stale-corpus preflight exit 3, rebases the corpus to C0 b2ab6acb2bbe, runs baseline + both candidates + controls, writes report/evidence; read-only on all canonical paths."),
        artifact_event("artifact_prereg", "preregistration",
                       "Predeclared checks P1-P10, controls K1-K5, decision and stop rules, written before the first run; frozen detector bytes pinned; worker-006 R03-v2 explicitly not used."),
        artifact_event("artifact_readme", "documentation",
                       "Human-readable summary: question, result table, exact one-line diffs, controls incl. the K2 coverage gap, recommendation, owner cascade and falsifier."),
        artifact_event("artifact_entry_hashes", "entry_hash_manifest",
                       "Entry hashes: canonical T0/T1 pins, deliverable sha256, candidate bytes, frozen detector pins."),
    ]

    findings = [
        {"id": "P-W062-R03-01", "severity": "positive",
         "finding": "Two independent one-line schema-side candidates each make the UNMODIFIED frozen two-stage pipeline exit 0 / PASS at the rev13-rebased corpus: CAND-A (formal product notation, bf1798b57997) and CAND-B (binder 'q', ebb8d6671614), both with 3/3 canonical rows ok, all pipeline controls ok and mutation-union 31/31. Candidate hashes were identical across three deterministic re-runs.",
         "evidence": [ev_hash["artifact_report"], ev_hash["artifact_cand_a"], ev_hash["artifact_cand_b"]]},
        {"id": "P-W062-R03-02", "severity": "positive",
         "finding": "The blocker is reproduced in a fresh sandbox and isolated: stale-corpus preflight rc 3; after rebase, baseline rc 1 FAIL with F1 structural=pass / semantic=fail(R03) while F2a and F2b pass and the union stays 31/31. The repair, not an auditor bypass, flips the verdict (K1).",
         "evidence": [ev_hash["artifact_report"], "evidence/acceptance_baseline.json"]},
        {"id": "A-W062-R03-01", "severity": "advisory",
         "finding": f"INSTRUMENT COVERAGE GAP (declared control K2 missed): corrupting f0_binding.consistency_evidence_sha256 (deadbeef... vs measured {k2['measured_evidence_sha256'][:12]}) still yields pipeline rc 0 / PASS. The frozen two-stage criterion does not cover the C06-class binding defect; a direct declared-vs-measured re-derivation catches it. Reviewers must not read pipeline PASS as evidence-binding-clean.",
         "evidence": [ev_hash["artifact_controls"], ev_hash["artifact_report"], "controls/K2_CAND-A_bad_consistency_hash.yaml"]},
        {"id": "A-W062-R03-02", "severity": "advisory",
         "finding": "Recommendation: CAND-B is minimum-risk (metadata-only, normative formal sentence byte-identical, rev11 precedent); CAND-A is equally pipeline-valid and preserves the pair-binder documentation in the ordered prefix via logically equivalent product notation. Either removes the need to adopt worker-006's FORM-R03-V2 tool change for this blocker; that adoption remains a separate owner decision.",
         "evidence": [ev_hash["artifact_report"], ev_hash["artifact_readme"]]},
        {"id": "A-W062-R03-03", "severity": "advisory",
         "finding": "Publishing F1 rev14 is an owner/controller cascade, not a worker action: apply one candidate, rebind schemas/f1_falsifier_tests.jsonl (open L-FORM-04 dependency; worker-031's validated patch), publish FROZEN rev30, then independent r3 re-review at the new bytes. Canonical bytes were not touched by this task.",
         "evidence": [ev_hash["artifact_readme"], "comms/outbox/worker-031.jsonl#w031-f1repin-blocker-20260912T010230"]},
    ]
    hard_failures = [
        {"id": "HF-W062-R03-01", "name": "canonical_f1_r03_not_repaired_at_published_bytes",
         "class_id": "AF-WCC-VAC-GEN", "severity": "blocking-until-owner-publishes",
         "finding": "At FROZEN rev29 / F1 rev13 d9cebb9404b2 the frozen stage-B auditor still rejects canonical F1 on R03, so run_acceptance.py cannot exit 0 at the published bytes; the validated one-line repair exists only as a proposal.",
         "falsifier": "Show run_acceptance.py rc 0 / PASS at F1 d9cebb9404b2 with the frozen detector bytes, or publish a repaired F1 (rev14) plus FROZEN rev30 and re-run this harness.",
         "mitigation_available": "Apply CAND-A (bf1798b57997) or CAND-B (ebb8d6671614) as F1 rev14 under the owner cascade; both were measured rc 0 / PASS / union 31/31 in a mirror sandbox with the frozen tools.",
         "evidence": [ev_hash["artifact_report"], ev_hash["artifact_cand_a"], ev_hash["artifact_cand_b"]]},
    ]
    events.append({
        "event_id": f"{LABEL}-claim", "event_type": "claim", "created_at": now_iso(), "actor": ACTOR,
        "node_id": "F1", "nodes": rep["nodes"], "gate": rep["gate"], "task_id": rep["task_id"],
        "class_id": rep["class_id"], "class_ids": rep["class_ids"],
        "conclusion_type": "formal_model",
        "statement": (f"Artifact-and-checker measurement (not a mathematics claim): at FROZEN rev29 / F1 rev13 "
                      f"d9cebb9404b2, in a fresh mirror sandbox with the frozen, unmodified tools "
                      f"(gate 000e09e46b2f, auditor c79d8ab8440a; worker-006 R03-v2 NOT used) and the corpus rebased to "
                      f"C0 b2ab6acb2bbe, the baseline pipeline exits 1 FAIL with F1 semantic=fail(R03) and union 31/31; "
                      f"two one-line schema-side candidates each make it exit 0 PASS with 3/3 canonical rows ok, all controls ok "
                      f"and union 31/31: CAND-A rewrites the single quantifiers.formal line to the logically equivalent product "
                      f"notation 'not exists (q,t0) in I+ x [0,T)' (sha256 bf1798b57997) and CAND-B changes only "
                      f"quantifiers.ordered[5].binder from '(q,t0)' to 'q' (sha256 ebb8d6671614). Parsed deltas are confined to "
                      f"the declared paths; class_id/revision/f0_binding/conclusion and all canonical pins are stable T0->T1. "
                      f"Separate recorded finding: the two-stage criterion does NOT cover the C06-class consistency-binding defect "
                      f"(corrupted consistency_evidence_sha256 still yields PASS)."),
        "assumptions": [
            "the FROZEN rev29 manifest and the three rev13 schemas are the binding reference at measurement time",
            "the canonical tools (check_class_schema.py, spec_conformance_audit.py, run_acceptance.py, measure_semantic_escape.py) are the declared acceptance machinery and were used unmodified",
            "the pipeline was reproduced only on a byte copy under ./sandbox; all canonical paths were read-only",
            "no ledger, schema, manifest, evidence file or detector was edited, repointed or adopted",
            "CAND-A's product notation is read as the joint quantifier over the independent domains I+ and [0,T), which is logically equivalent to the canonical independent-quantifier spelling",
        ],
        "falsifier": falsifier,
        "evidence_refs": base_evidence + [ev_hash["artifact_entry_hashes"]],
        "artifact_refs": [ev_hash["artifact_cand_a"], ev_hash["artifact_cand_b"], ev_hash["artifact_report"],
                          ev_hash["artifact_diff_a"], ev_hash["artifact_diff_b"], ev_hash["artifact_runner"]],
    })
    events.append({
        "event_id": f"{LABEL}-review", "event_type": "review", "created_at": now_iso(), "actor": ACTOR,
        "node_id": "F1", "nodes": rep["nodes"], "gate": rep["gate"], "task_id": rep["task_id"],
        "class_id": rep["class_id"], "class_ids": rep["class_ids"],
        "target_id": "F1@FROZEN-rev29-d9cebb9404b2", "reviewer": ACTOR,
        "reviewer_role": "bounded execution worker (not the schema author, not a full-schema r3 verdict)",
        "verdict": "revise", "score": 4.0,
        "counts_as_full_schema_verdict": False,
        "reviewed_sha256": f1,
        "summary": ("Repair-candidate review of the F1 R03 blocker: revise 4.0. The published F1 bytes still fail the frozen "
                    "stage-B R03 test, but two sandbox-validated one-line schema-side repairs each make the unmodified frozen "
                    "pipeline PASS end-to-end at the rev13-rebased corpus with union 31/31; one new instrument-coverage finding "
                    "recorded (pipeline does not bind consistency_evidence_sha256). Not a full-schema verdict."),
        "hard_failures": hard_failures, "findings": findings,
        "falsifier": falsifier,
        "evidence_refs": base_evidence + [ev_hash["artifact_entry_hashes"]],
    })
    events.append({
        "event_id": f"{LABEL}-status", "event_type": "status", "created_at": now_iso(), "actor": ACTOR,
        "node_id": "F1", "nodes": rep["nodes"], "gate": rep["gate"], "task_id": rep["task_id"],
        "class_id": rep["class_id"], "class_ids": rep["class_ids"],
        "status": "active", "hours": 0.5,
        "summary": ("CHECKPOINT + EXIT. W062-GFORM-R03-SCHEMA-REPAIR-CANDIDATE-01 complete at worker level: no inbox card; "
                    f"one bounded class-bound task. Baseline reproduces HF-W062-REV13-01 (rc 1, F1 R03, union 31/31); CAND-A "
                    f"bf1798b57997 and CAND-B ebb8d6671614 each give frozen pipeline rc 0 PASS, 3/3 canonical ok, union 31/31; "
                    f"P1-P10 pass; K1/K2b/K3/K4/K5 pass; declared K2 miss recorded as a two-stage coverage gap for "
                    f"consistency-evidence binding. Review revise 4.0, 1 hard failure (canonical bytes still unrepaired, "
                    f"mitigation available). No canonical write, no node status, no gate verdict."),
        "evidence_refs": base_evidence + [ev_hash["artifact_entry_hashes"]],
        "artifact_refs": [ev_hash[k] for k in ("artifact_cand_a", "artifact_cand_b", "artifact_report",
                                               "artifact_runner", "artifact_prereg", "artifact_controls",
                                               "artifact_readme", "artifact_entry_hashes")],
        "next_falsifier": ("Owner applies the recommended candidate as F1 rev14, rebinds schemas/f1_falsifier_tests.jsonl "
                           "(L-FORM-04 / worker-031) and publishes FROZEN rev30; an independent reviewer re-runs this harness "
                           "plus the r3 full-schema review at the new bytes. Any stage-B adoption (worker-006 R03-v2) is a "
                           "separate decision and is not needed for this blocker if a schema candidate is adopted."),
    })

    for e in events:
        validate_event(e)

    with open(OUTBOX, "a") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")

    checkpoint = {
        "checkpoint_id": f"{LABEL}-checkpoint",
        "task_id": rep["task_id"], "worker": ACTOR, "instance": rep["instance"],
        "created_at": now_iso(), "node_id": "F1", "nodes": rep["nodes"], "gate": rep["gate"],
        "class_id": rep["class_id"], "class_ids": rep["class_ids"],
        "status": "task_complete_pending_ingest",
        "verdict": {"value": rep["verdict"]["value"], "candidates_validated": rep["verdict"]["candidates_validated"],
                    "review_verdict": "revise 4.0", "hard_failure_ids": ["HF-W062-R03-01"],
                    "recommendation": rep["verdict"]["recommendation"]},
        "result": {"baseline": rep["baseline"],
                   "CAND-A": {k: ca[k] for k in ("gate_verdict", "sem_verdict", "pipe_rc", "pipe_verdict", "union", "sha256")},
                   "CAND-B": {k: cb[k] for k in ("gate_verdict", "sem_verdict", "pipe_rc", "pipe_verdict", "union", "sha256")},
                   "controls": {c["id"]: c["result"] for c in controls["controls"]},
                   "k2_coverage_gap": k2["finding"]},
        "artifacts": [{"path": v, "sha256": H[k]} for k, v in files.items()] + [
            {"path": "entry_hashes.json", "sha256": H["artifact_entry_hashes"]}],
        "events_emitted": [e["event_id"] for e in events],
        "canonical_T0": rep["t0_hashes"], "canonical_T1": rep["t1_hashes"],
        "authority_note": rep["authority_note"],
        "next_falsifier": events[-1]["next_falsifier"],
        "exit": "worker exits; no node status, validation_status=passed or gate verdict set",
    }
    (TASK / "CHECKPOINT.json").write_text(json.dumps(checkpoint, indent=2) + "\n")
    STATE.write_text(json.dumps(checkpoint, indent=2) + "\n")
    print(json.dumps({"events_emitted": len(events), "checkpoint": str(TASK / "CHECKPOINT.json"),
                      "state": str(STATE), "outbox": str(OUTBOX)}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
