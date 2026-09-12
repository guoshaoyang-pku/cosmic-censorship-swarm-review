#!/usr/bin/env python3
"""W043H idempotent emitter: MANIFEST.json + outbox events + checkpoint. No canonical writes."""
import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
STAMP = "2026-09-12T01:30:00+08:00"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).replace(microsecond=0).isoformat()
TASK = "W043H-F2B-REV14-LANDING-INTEGRITY-01"
OUTBOX = ROOT / "comms/outbox/worker-043.jsonl"
CKPT = ROOT / "runtime/state/w043h_checkpoint.json"
FINAL_ID = "w043h-status-complete"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def hs(rel: str) -> str:
    return sha(HERE / rel)


deliverables = {
    "instrument": "check_landing_integrity.py",
    "emitter": "emit_events.py",
    "raw": "raw/landing_integrity_raw.json",
    "report": "report.json",
    "readme": "README.md",
}
manifest = {
    "schema_version": "1.0", "worker": "worker-043", "task_id": TASK,
    "class_id": "AF-SCC-C0-VAC-GEN", "node_id": "F2b", "gate": "G-FORM",
    "generated_at": STAMP,
    "files": {name: {"path": f"artifacts/worker-043/w043h_rev14_landing_integrity/{rel}",
                     "sha256": hs(rel), "bytes": (HERE / rel).stat().st_size}
              for name, rel in deliverables.items()},
    "reproduce": "python3 artifacts/worker-043/w043h_rev14_landing_integrity/check_landing_integrity.py",
    "falsifier": ("Any artifact hash listed here differing from the live bytes voids the manifest; any entry-pin drift "
                  "voids the measurement (instrument exit 2)."),
    "authority_note": "Worker evidence only; no gate verdict, no node status, no canonical byte written.",
}
(HERE / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
M = {k: v["sha256"] for k, v in manifest["files"].items()}
M["manifest"] = sha(HERE / "MANIFEST.json")
H = {k: v[:12] for k, v in M.items()}
raw = json.loads((HERE / "raw/landing_integrity_raw.json").read_text())

BASE = "artifacts/worker-043/w043h_rev14_landing_integrity"
refs = {
    "instrument": f"{BASE}/check_landing_integrity.py#{H['instrument']}",
    "emitter": f"{BASE}/emit_events.py#{H['emitter']}",
    "raw": f"{BASE}/raw/landing_integrity_raw.json#{H['raw']}",
    "report": f"{BASE}/report.json#{H['report']}",
    "readme": f"{BASE}/README.md#{H['readme']}",
    "manifest": f"{BASE}/MANIFEST.json#{H['manifest']}",
}
PINS = ["schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe", "artifacts/formulation/FROZEN.json#815e08079aef",
        "artifacts/formulation/evidence/taxonomy_consistency.json#9e335e9ba1bf",
        "artifacts/formulation/rule_spec.json#40f9bb9e657b"]
CAND_REFS = [
    "artifacts/worker-023/f2b_dir_review/proposed_af_scc_c0_vacuum_v2_corrected.yaml#9ab32ee39d00",
    "artifacts/worker-080/f2b_hf1_direction_census/snapshots/51c253c46306__cand_corrected_51c253c4.yaml#51c253c46306",
    "artifacts/worker-080/f2b_hf1_direction_census/snapshots/4951cc969803__cand_nesting_4951cc96.yaml#4951cc969803",
]
FALSIFIER = json.loads((HERE / "report.json").read_text())["falsifier"]

claim_statement = (
    "Artifact-and-checker measurement, not a mathematics claim. At the pinned rev29 bytes (F2b b2ab6acb2bbe, FROZEN "
    "815e08079aef, F0 0abb9ed8a961, supplement d7419b4e8963, evidence 9e335e9ba1bf, rule_spec 40f9bb9e657b), the three "
    "staged F2b rev14 candidates 9ab32ee39d00 / 51c253c46306 / 4951cc969803 all pass the two carrier predicates (D1 "
    "assertive containment denial absent, D2 inverted size premise absent with a direction-correct replacement), resolve "
    "their declared f0_binding chain 3/3, and pass the canonical structural gate check_class_schema.py (exit 0 each) and "
    "taxonomy consistency (exit 0, evidence 9e335e9b). None is landing-ready as staged bytes: all declare revision 13 with "
    "no rev14 revision_history row and the rev13 revised_at, and the history stays non-monotone at rows 8-9 with row 9 "
    "unused. A complete atomic landing must additionally move artifacts/formulation/FROZEN.json (b2ab6acb), "
    "schemas/af_scc_regularities.yaml (b2ab6acb) and refresh entry_hashes.json + schemas/af_scc_c0_vacuum.yaml.sha256 "
    "(already stale at 1bb78ce9), writing the canonical/mirror pair together."
)

task_event = {"event_id": "w043h-status-taken", "event_type": "status", "created_at": NOW, "actor": "worker-043",
              "node_id": "F2b", "node_ids": ["F2b"], "class_id": "AF-SCC-C0-VAC-GEN",
              "class_ids": ["AF-SCC-C0-VAC-GEN"], "gate": "G-FORM", "task_id": TASK, "status": "active",
              "hours": 0.5,
              "summary": ("No inbox card exists for worker-043. Took ONE bounded class-bound task: pre-landing "
                          "atomic-integrity audit of the three staged F2b rev14 candidates on the axes not covered by the "
                          "direction reviews: declared f0_binding chain, revision/history readiness, canonical structural "
                          "gate, taxonomy consistency, and the complete atomic write set. Read-only on canonical paths; "
                          "sandbox under tmp/w043h_sandbox/."),
              "evidence_refs": CAND_REFS + PINS,
              "next_falsifier": FALSIFIER}

art_events = [
    {"event_id": "w043h-artifact-instrument", "event_type": "artifact", "created_at": NOW, "actor": "worker-043",
     "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN", "gate": "G-FORM", "task_id": TASK,
     "artifact_type": "instrument", "path": f"{BASE}/check_landing_integrity.py", "sha256": M["instrument"],
     "bytes": manifest["files"]["instrument"]["bytes"], "validation_status": "unverified",
     "evidence_refs": [refs["instrument"]], "falsifier": FALSIFIER},
    {"event_id": "w043h-artifact-raw", "event_type": "artifact", "created_at": NOW, "actor": "worker-043",
     "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN", "gate": "G-FORM", "task_id": TASK,
     "artifact_type": "measurement_raw", "path": f"{BASE}/raw/landing_integrity_raw.json", "sha256": M["raw"],
     "bytes": manifest["files"]["raw"]["bytes"], "validation_status": "unverified",
     "evidence_refs": [refs["raw"]], "falsifier": FALSIFIER},
    {"event_id": "w043h-artifact-report", "event_type": "artifact", "created_at": NOW, "actor": "worker-043",
     "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN", "gate": "G-FORM", "task_id": TASK,
     "artifact_type": "report", "path": f"{BASE}/report.json", "sha256": M["report"],
     "bytes": manifest["files"]["report"]["bytes"], "validation_status": "unverified",
     "evidence_refs": [refs["report"]], "falsifier": FALSIFIER},
    {"event_id": "w043h-artifact-readme", "event_type": "artifact", "created_at": NOW, "actor": "worker-043",
     "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN", "gate": "G-FORM", "task_id": TASK,
     "artifact_type": "readme", "path": f"{BASE}/README.md", "sha256": M["readme"],
     "bytes": manifest["files"]["readme"]["bytes"], "validation_status": "unverified",
     "evidence_refs": [refs["readme"]], "falsifier": FALSIFIER},
    {"event_id": "w043h-artifact-manifest", "event_type": "artifact", "created_at": NOW, "actor": "worker-043",
     "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN", "gate": "G-FORM", "task_id": TASK,
     "artifact_type": "manifest", "path": f"{BASE}/MANIFEST.json", "sha256": M["manifest"],
     "bytes": (HERE / "MANIFEST.json").stat().st_size, "validation_status": "unverified",
     "evidence_refs": [refs["manifest"]], "falsifier": FALSIFIER},
]

claim = {"event_id": "w043h-claim-landing-integrity", "event_type": "claim", "created_at": NOW, "actor": "worker-043",
         "node_id": "F2b", "node_ids": ["F2b"], "class_id": "AF-SCC-C0-VAC-GEN",
         "class_ids": ["AF-SCC-C0-VAC-GEN"], "gate": "G-FORM", "task_id": TASK,
         "conclusion_type": "formal_model", "statement": claim_statement,
         "assumptions": ["the measured bytes did not change during the run (10/10 entry pins equal exit pins; drift list empty)",
                         "the canonical gate and taxonomy checker are used as-is and only in scratch/sandbox copies",
                         "the D1/D2 predicates are syntactic and mention-aware; they do not decide the mathematics, only that the "
                         "two recorded carriers are absent from the assertive text",
                         "worker verdicts cannot set node status, validation_status or a gate verdict"],
         "falsifier": FALSIFIER,
         "evidence_refs": [refs["report"], refs["raw"], refs["instrument"], refs["manifest"]] + CAND_REFS + PINS,
         "artifact_refs": [refs["report"], refs["raw"], refs["manifest"]],
         "non_claims": ["not a gate verdict", "not a full-schema accept", "no canonical byte written",
                        "does not re-adjudicate the direction axis owned by workers 100/080/029"]}

review = {"event_id": "w043h-review-landing-integrity", "event_type": "review", "created_at": NOW, "actor": "worker-043",
          "target_id": "staged F2b rev14 candidates 9ab32ee39d00 / 51c253c46306 / 4951cc969803 (landing-integrity axis)",
          "reviewer": "worker-043", "node_id": "F2b", "node_ids": ["F2b"], "class_id": "AF-SCC-C0-VAC-GEN",
          "class_ids": ["AF-SCC-C0-VAC-GEN"], "gate": "G-FORM", "task_id": TASK,
          "verdict": "revise", "score": 3.5, "counts_as_full_schema_verdict": False, "gate_eligible": False,
          "hard_failures": [
            {"id": "HF-W043H-1", "severity": "blocking-for-atomic-landing", "axis": "revision/history readiness",
             "finding": "All three candidates are rev13 bytes with no rev14 revision_history row and the rev13 revised_at; the "
                        "history is non-monotone at rows 8-9 and row 9 is unused:true. Landing any of them byte-identically would "
                        "publish rev14 content under a rev13 self-declaration and leave W043G H1/H4 open."},
            {"id": "HF-W043H-2", "severity": "blocking-for-atomic-landing", "axis": "declared-pointer write set",
             "finding": "Four declared pointers name superseded F2b bytes and must move in the same revision: "
                        "artifacts/formulation/FROZEN.json and schemas/af_scc_regularities.yaml (both b2ab6acb), plus "
                        "entry_hashes.json and schemas/af_scc_c0_vacuum.yaml.sha256 (already stale at 1bb78ce9). The "
                        "canonical/mirror pair must be written together."}],
          "findings": [
            "W043H-R-01 CLEAN: D1 and D2 carriers absent in all three candidates at their own bytes; mention-aware predicate "
            "avoids the bracketed-note false hit that a substring scan would produce.",
            "W043H-R-02 CLEAN: each candidate resolves its declared f0_binding 3/3 (0abb9ed8a961 / 9e335e9ba1bf / d7419b4e8963); "
            "no a03ba9c5/675a99d0 hazard in these lineages.",
            "W043H-R-03 CLEAN: canonical structural gate exit 0 for all three; taxonomy consistency exit 0 with evidence "
            "9e335e9ba1bf (the checker does not consume the schema, so this binds the F0 pair, not the candidate).",
            "W043H-R-04 DISCRIMINATION: 9ab32ee39d00 and 51c253c46306 assert a licensed direction in "
            "regularity.must_not_conflate[0]; 4951cc969803 is NEUTRAL_POINTER. All pass the instrument.",
            "W043H-R-05 CONTROLS: M1 live -> D1/D2 FAIL; M2 base 84b5d3fa -> entailment INVERTED (independently reproduces "
            "worker-080 HF1); M3/M4 mutations caught; M5 byte-identical rerun; 10/10 pins stable, zero drift."],
          "falsifier": FALSIFIER,
          "authority_note": ("Worker evidence only; cannot set a gate verdict, node status or validation_status; reviews the "
                             "landing-integrity axis of the staged candidates, not their mathematical content.")}

blocker = {"event_id": "w043h-blocker-atomic-landing", "event_type": "blocker", "created_at": NOW, "actor": "worker-043",
           "node_id": "F2b", "node_ids": ["F2b"], "class_id": "AF-SCC-C0-VAC-GEN", "class_ids": ["AF-SCC-C0-VAC-GEN"],
           "gate": "G-FORM", "task_id": TASK,
           "description": ("The staged candidates are content-clean but none is landing-ready as staged bytes, and the landing "
                           "is not a one-file write. Measured at the rev29 pins: each candidate declares revision 13 with no rev14 "
                           "history row and the rev13 revised_at (history non-monotone rows 8-9; row 9 unused), and four declared "
                           "pointers name superseded F2b hashes (FROZEN.json and af_scc_regularities.yaml at b2ab6acb; "
                           "entry_hashes.json and the .sha256 sidecar already stale at 1bb78ce9)."),
           "needed_to_unblock": ("astra-lead-formulation, in the ONE authorized rev14 revision: (1) land the chosen candidate "
                                 "with revision 13->14, a wall-clock revised_at and an appended rev14 revision_history row (or "
                                 "adopt the worker-043 W043G V2-style history repair); (2) write canonical and mirror together; "
                                 "(3) move FROZEN.json to rev30 with the new per-file pin and re-pin af_scc_regularities.yaml; "
                                 "(4) refresh entry_hashes.json and schemas/af_scc_c0_vacuum.yaml.sha256, which are stale even "
                                 "before this landing; (5) re-run the canonical gate and taxonomy consistency at the new bytes. "
                                 "Worker evidence only; the owner applies."),
           "evidence_refs": [refs["report"], refs["raw"], refs["manifest"]] + CAND_REFS + PINS}

final = {"event_id": FINAL_ID, "event_type": "status", "created_at": NOW, "actor": "worker-043",
         "node_id": "F2b", "node_ids": ["F2b"], "class_id": "AF-SCC-C0-VAC-GEN", "class_ids": ["AF-SCC-C0-VAC-GEN"],
         "gate": "G-FORM", "task_id": TASK, "status": "active", "hours": 0.5,
         "summary": ("W043H-F2B-REV14-LANDING-INTEGRITY-01 complete at worker level: one bounded class-bound task, 5 artifacts "
                     "on disk and hash-pinned, 5/5 pre-registered controls matched, 10/10 entry pins stable, deterministic rerun, "
                     "canonical tree unchanged, checkpoint runtime/state/w043h_checkpoint.json. Verdict revise 3.5 on the "
                     "landing-integrity axis: all three candidates content-clean and gate-passing, none landing-ready as staged "
                     "bytes (revision/history bump + 4-pointer atomic write set required). Completion claim only; no node "
                     "transition, no gate verdict, no canonical byte changed."),
         "evidence_refs": [refs["report"], refs["manifest"], "runtime/state/w043h_checkpoint.json"],
         "next_falsifier": FALSIFIER}

events = [task_event] + art_events + [claim, review, blocker, final]

R2 = "--repair" in sys.argv
existing = OUTBOX.read_text() if OUTBOX.exists() else ""
if R2:
    # correction pass: the first claim used conclusion_type=measurement, which the accepted-stream
    # schema rejects; re-emit it as formal_model and re-bind the manifest/emitter/checkpoint.
    claim["event_id"] = "w043h-claim-landing-integrity-r2"
    claim["corrects"] = "w043h-claim-landing-integrity (rejected pre-ingest: invalid conclusion_type 'measurement')"
    emitter_ev = {"event_id": "w043h-artifact-emitter-r2", "event_type": "artifact", "created_at": NOW,
                  "actor": "worker-043", "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN", "gate": "G-FORM",
                  "task_id": TASK, "artifact_type": "instrument", "path": f"{BASE}/emit_events.py",
                  "sha256": M["emitter"], "bytes": manifest["files"]["emitter"]["bytes"],
                  "validation_status": "unverified", "evidence_refs": [refs["emitter"]], "falsifier": FALSIFIER}
    man_ev = {"event_id": "w043h-artifact-manifest-r2", "event_type": "artifact", "created_at": NOW,
              "actor": "worker-043", "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN", "gate": "G-FORM",
              "task_id": TASK, "artifact_type": "manifest", "path": f"{BASE}/MANIFEST.json",
              "sha256": M["manifest"], "bytes": (HERE / "MANIFEST.json").stat().st_size,
              "validation_status": "unverified", "supersedes": "w043h-artifact-manifest",
              "evidence_refs": [refs["manifest"]], "falsifier": FALSIFIER}
    note = {"event_id": "w043h-status-claim-correction", "event_type": "status", "created_at": NOW, "actor": "worker-043",
            "node_id": "F2b", "node_ids": ["F2b"], "class_id": "AF-SCC-C0-VAC-GEN", "class_ids": ["AF-SCC-C0-VAC-GEN"],
            "gate": "G-FORM", "task_id": TASK, "status": "active", "hours": 0.05,
            "summary": ("Correction pass after ingest: w043h-claim-landing-integrity was rejected pre-ingest (invalid "
                        "conclusion_type 'measurement'; allowed set is theorem/conditional_theorem/stability_result/"
                        "counterexample/numerical_evidence/formal_model/open_problem). Re-emitted identically as "
                        "w043h-claim-landing-integrity-r2 with conclusion_type formal_model. The emitter fix changed "
                        "emit_events.py and MANIFEST.json, so both are re-bound by -r2 artifact events; report, raw, README and "
                        "instrument hashes are unchanged and the measurement, controls, verdict and falsifier are unchanged."),
            "evidence_refs": [refs["report"], refs["manifest"]], "next_falsifier": FALSIFIER}
    with OUTBOX.open("a") as f:
        for e in [emitter_ev, man_ev, note, claim]:
            f.write(json.dumps(e, sort_keys=True) + "\n")
    print("appended", 4, "correction events")
elif FINAL_ID in existing:
    print("already emitted; no-op")
else:
    with OUTBOX.open("a") as f:
        for e in events:
            f.write(json.dumps(e, sort_keys=True) + "\n")
    print("appended", len(events), "events")

checkpoint = {
    "schema_version": "1.0", "worker": "worker-043", "task_id": TASK, "class_id": "AF-SCC-C0-VAC-GEN",
    "node_id": "F2b", "gate": "G-FORM", "created_at": STAMP,
    "entry_pins": raw["entry_pins"], "exit_pins_sha256": {k: v["sha256"] for k, v in raw["exit_pins"].items()},
    "pin_drift": raw["pin_drift"],
    "result": {"verdict": "revise 3.5", "candidates_clean": 3, "candidates_landing_ready_as_staged": 0,
               "controls_all_match": raw["controls_all_match"], "deterministic_rerun": raw["deterministic_rerun"]},
    "artifact_hashes": M, "artifact_refs": refs,
    "stale_declared_pointers": raw["candidates"]["cand023_v2_9ab32ee39d00"]["C09_atomic_layer"]["_stale_on_landing"],
    "falsifier": FALSIFIER,
    "authority_note": "Worker evidence only; no canonical write, no gate verdict, no node status.",
}
CKPT.write_text(json.dumps(checkpoint, indent=2, sort_keys=True) + "\n")
print("checkpoint", sha(CKPT)[:12], "manifest", M["manifest"][:12], "report", M["report"][:12],
      "raw", M["raw"][:12], "instrument", M["instrument"][:12], "readme", M["readme"][:12])
