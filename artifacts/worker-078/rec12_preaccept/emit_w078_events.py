#!/usr/bin/env python3
"""W078-REC12-PREACCEPT-01 emitter: checkpoint + review body + idempotent outbox events.

Fail-closed: refuses to emit unless report.json says the instrument ran clean (controls_ok) and the
measured pins in the report still equal the live bytes.  Re-running is a no-op (event ids are fixed,
not wall-clock derived).  Writes only:
  artifacts/worker-078/rec12_preaccept/{CHECKPOINT.json,SHA256SUMS.txt}
  runtime/state/w078_checkpoint_6_rec12_preaccept.json
  reviews/W078-REC12-acceptance-078.json
  comms/outbox/worker-078.jsonl   (append-only)
"""
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "artifacts/worker-078/rec12_preaccept"
TZ = timezone(timedelta(hours=8))
OUTBOX = ROOT / "comms/outbox/worker-078.jsonl"
CHECKPOINT = OUT / "CHECKPOINT.json"
CHECKPOINT_STATE = ROOT / "runtime/state/w078_checkpoint_6_rec12_preaccept.json"
REVIEW_BODY = ROOT / "reviews/W078-REC12-acceptance-078.json"
TASK_ID = "W078-REC12-PREACCEPT-01"
NOW = datetime.now(TZ).isoformat(timespec="seconds")
EVENT_IDS = [
    "w078-rec12-task-claim", "w078-rec12-artifact-harness", "w078-rec12-artifact-report",
    "w078-rec12-artifact-rerun", "w078-rec12-artifact-controls", "w078-rec12-artifact-readme",
    "w078-rec12-artifact-checkpoint", "w078-rec12-artifact-review-body",
    "w078-rec12-claim-acceptance", "w078-rec12-review-publication",
    "w078-rec12-blocker-f2b-scope", "w078-rec12-status-final",
]


def existing_ids() -> set:
    ids = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                ids.add(json.loads(line).get("event_id"))
            except json.JSONDecodeError:
                pass
    return ids


def sha256_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def m(rel):
    return {"path": rel, "sha256": sha256_file(ROOT / rel)}


def main() -> int:
    if set(EVENT_IDS) <= existing_ids() and CHECKPOINT.exists() and REVIEW_BODY.exists():
        print("no-op: all 12 events already emitted and checkpoint/review body present")
        return 0
    report = json.loads((OUT / "report.json").read_text())
    rerun = json.loads((OUT / "report_rerun.json").read_text())
    controls = json.loads((OUT / "controls.json").read_text())

    if not controls.get("controls_ok"):
        print("REFUSING to emit: controls not ok", file=sys.stderr)
        return 2
    if report.get("verdict") != "CARD_ITEMS_MET_AT_REV29":
        print(f"REFUSING to emit: verdict={report.get('verdict')}", file=sys.stderr)
        return 2
    if not report.get("deterministic_test_retest"):
        print("REFUSING to emit: report/report_rerun not deterministic", file=sys.stderr)
        return 2

    pins = report["binding"]["measured_pins"]
    live = {n: m(p)["sha256"] for n, p in
            (("F1", "schemas/af_wcc_vacuum.yaml"), ("F2a", "schemas/af_scc_c2_vacuum.yaml"),
             ("F2b", "schemas/af_scc_c0_vacuum.yaml"))}
    if pins != live:
        print(f"REFUSING to emit: pins moved {pins} != {live}", file=sys.stderr)
        return 2
    frozen_live = sha256_file(ROOT / "artifacts/formulation/FROZEN.json")
    if frozen_live != report["binding"]["frozen_sha256"]:
        print("REFUSING to emit: FROZEN.json moved", file=sys.stderr)
        return 2

    artifacts = {
        "artifacts/worker-078/rec12_preaccept/verify_rec12_preaccept.py": sha256_file(OUT / "verify_rec12_preaccept.py"),
        "artifacts/worker-078/rec12_preaccept/report.json": sha256_file(OUT / "report.json"),
        "artifacts/worker-078/rec12_preaccept/report_rerun.json": sha256_file(OUT / "report_rerun.json"),
        "artifacts/worker-078/rec12_preaccept/controls.json": sha256_file(OUT / "controls.json"),
        "artifacts/worker-078/rec12_preaccept/README.md": sha256_file(OUT / "README.md"),
        "artifacts/worker-078/rec12_preaccept/snapshot/SHA256SUMS.txt": sha256_file(OUT / "snapshot/SHA256SUMS.txt"),
    }

    review_body = {
        "review_id": "W078-REC12-acceptance-078",
        "reviewer": "worker-078",
        "created_at": NOW,
        "task_id": TASK_ID,
        "target_id": f"artifacts/formulation/FROZEN.json#{frozen_live[:12]}",
        "target_kind": "repair_card_publication",
        "node_id": "F1,F2a,F2b",
        "gate": "G-FORM",
        "class_ids": report["class_ids"],
        "verdict": "accept",
        "score": 4.0,
        "counts_as_full_schema_verdict": False,
        "counts_toward_gate_accept": False,
        "authority_note": "worker verdict on the REC-12 repair card only; cannot set node status=done, validation_status=passed or a gate verdict; the r3 class-semantics round is lead-audit's",
        "scope": "astra-life05-evidence-binding-repair acceptance (four card items) at the measured rev13/rev29 pins",
        "hard_failures": [],
        "findings": [
            f"20 PASS / 2 WARN / 0 FAIL across the four card items plus the card falsifier; "
            f"{controls['n']}/{controls['n']} seeded controls correct; report->rerun normalized digest identical "
            f"({report['normalized_sha256'][:16]}); zero drift inside the run.",
            "Item 1: 36/36 corpus rows bound to declared F0 rev5 0abb9ed8a961; canonical checker exit 0, PASS, "
            "11/11 controls; repo report binds the live corpus hash ccf7041b with mtime >= corpus.",
            "Item 2: all three schemas declare 9e335e9ba1bf == measured live evidence; isolated mirror of the "
            "canonical checker reproduces the live evidence bytes exactly (CONSISTENT, 4 classes, 0 divergences).",
            "Item 3: D5 and visibility.definition now say tail<->whole EQUIVALENT; variant SET relation now "
            "strictly WEAKER; the true 'B-containment is strictly stronger' sentence survives; VARIANT_REGISTRY "
            "and the SET delta labels were corrected to 'strictly weaker' during the measurement window "
            "(surviving 'strictly STRONGER' is a bracketed historical mention).",
            "Item 4: FROZEN rev29, 52/52 manifest pins match live bytes, all three moved schemas pinned, "
            "artifact events for the new hashes are in the accepted stream, and a before/after machine report exists.",
            "Card falsifier: F0 bytes unchanged vs the pinned rev12 baseline; no forbidden class-definition, "
            "hypothesis, conclusion-predicate or axis/genericity change; declared class-id sets unchanged; "
            "A5b/A5c discriminate on seeded mutations (controls C4/C4b/C5).",
        ],
        "residuals": [
            {"id": "S1", "severity": "hard", "class_id": "AF-SCC-C0-VAC-GEN",
             "finding": "F2b :245 forbidden_transfers[0].reason still asserts the inverted premise 'C2 is a strictly larger extension class' while :238's chain places E_C2 smallest; NOT among the four authorized repair items; the r3 F2b round is expected to reject unless repaired or dispositioned",
             "reporters": ["worker-066 W066-R12-F2B-H1", "worker-060 HF-060-CS-01", "worker-008 W008-CD CD-01"]},
            {"id": "S4", "severity": "moderate", "class_id": "ALL",
             "finding": "the refreshed consistency evidence records input paths only (no map_taxonomy_sha256 / lead_contract_sha256), so the r3 'refreshed consistency-evidence binding' cannot verify which F0/supplement bytes were compared (CF-20 / worker-047 CB-2)"},
            {"id": "S2", "severity": "info", "class_id": "AF-WCC-VAC-GEN",
             "finding": "the rev13 SET falsifier is unchanged and does not add worker-076's finiteness/dominating-member hypothesis; direction is correct, so this is a wording residual"},
        ],
        "evidence_refs": [
            f"artifacts/worker-078/rec12_preaccept/report.json#{artifacts['artifacts/worker-078/rec12_preaccept/report.json'][:12]}",
            f"artifacts/worker-078/rec12_preaccept/controls.json#{artifacts['artifacts/worker-078/rec12_preaccept/controls.json'][:12]}",
            f"schemas/af_wcc_vacuum.yaml#{pins['F1'][:12]}",
            f"schemas/af_scc_c2_vacuum.yaml#{pins['F2a'][:12]}",
            f"schemas/af_scc_c0_vacuum.yaml#{pins['F2b'][:12]}",
            f"artifacts/formulation/FROZEN.json#{frozen_live[:12]}",
            "artifacts/worker-076/gform_strictness_reconcile/probe_result.json#ae1740ac0b15",
        ],
        "falsifier": (
            "A byte move in any measured pin voids this acceptance. At the pinned bytes it is falsified by: "
            "a manifest-listed hash differing from live bytes; a corpus row or meta not bound to the live F0 rev5 hash; "
            "a schema whose declared consistency-evidence pin differs from the measured evidence; a forbidden "
            "class-definition/hypothesis/conclusion-predicate/axis change vs the rev12 baseline; or a seeded control "
            "that stops discriminating on re-run."
        ),
        "limits": [
            "repair-card acceptance only; class semantics, mathematics, non-vacuity and citation scope are not re-derived",
            "item-3 direction facts are worker-076's machine-checked table, encoded rather than re-proved",
            "baseline projection uses worker-086 pinned copies and worker-074's rev28 sandbox copy, both re-hashed before use",
        ],
    }
    REVIEW_BODY.write_text(json.dumps(review_body, indent=2, sort_keys=True) + "\n")
    review_sha = sha256_file(REVIEW_BODY)

    checkpoint = {
        "schema_version": "1.0",
        "artifact_type": "worker_checkpoint",
        "checkpoint_id": "w078-checkpoint-6-rec12-preaccept",
        "actor": "worker-078",
        "created_at": NOW,
        "task_id": TASK_ID,
        "node_id": "F1,F2a,F2b",
        "gate": "G-FORM",
        "class_ids": report["class_ids"],
        "status": "complete",
        "verdict": report["verdict"],
        "counts": report["status_counts"],
        "card_items_status": report["card_items_status"],
        "controls_ok": controls["controls_ok"],
        "controls_n": controls["n"],
        "deterministic_test_retest": report["deterministic_test_retest"],
        "normalized_sha256": report["normalized_sha256"],
        "pins": pins,
        "frozen_revision": report["binding"]["frozen_revision"],
        "frozen_sha256": frozen_live,
        "f0_sha256": report["binding"]["f0_sha256"],
        "evidence_sha256": report["binding"]["evidence_sha256"],
        "cases_sha256": report["binding"]["cases_sha256"],
        "baseline_recovery": report["baseline_recovery"],
        "baseline_projection_discriminating_checks": report["baseline_projection"]["checks_that_discriminate"],
        "advisory_findings": [{"id": a["id"], "severity": a["severity"], "node": a["node"]} for a in report["advisory_findings"]],
        "artifacts": artifacts,
        "review_body": "reviews/W078-REC12-acceptance-078.json",
        "review_body_sha256": review_sha,
        "non_claims": report["non_claims"],
        "next_falsifier": review_body["falsifier"],
        "map_at_write": m("research_map/research_map.json"),
    }
    CHECKPOINT.write_text(json.dumps(checkpoint, indent=2, sort_keys=True) + "\n")
    checkpoint_sha = sha256_file(CHECKPOINT)
    CHECKPOINT_STATE.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_STATE.write_text(CHECKPOINT.read_text())

    sums = [
        "verify_rec12_preaccept.py", "report.json", "report_rerun.json", "controls.json",
        "README.md", "CHECKPOINT.json", "snapshot/SHA256SUMS.txt",
    ]
    (OUT / "SHA256SUMS.txt").write_text(
        "\n".join(f"{sha256_file(OUT / f)}  {f}" for f in sums) + "\n")

    events = [
        {"event_id": "w078-rec12-task-claim", "event_type": "status", "created_at": NOW, "actor": "worker-078",
         "node_id": "F1,F2a,F2b", "gate": "G-FORM", "class_id": ";".join(report["class_ids"]),
         "task_id": TASK_ID, "status": "active", "hours": 0.6,
         "summary": "No assignment card exists in comms/inbox/worker-078.jsonl. Took ONE bounded class-bound task: "
                    "independent acceptance measurement of the astra-life05-evidence-binding-repair card (REC-12) at the "
                    "rev13/FROZEN rev29 pins, with a pre-registered deterministic harness, a recovered rev12/rev28 baseline "
                    "projection, 15 seeded controls and a byte-pinned test-retest. Read-only on canonical paths.",
         "evidence_refs": ["research_map/research_map.json#assignments.astra-life05-evidence-binding-repair",
                           "runtime/state/controller_verification/astra-lifecycle-05-decisions.json",
                           "artifacts/worker-076/gform_strictness_reconcile/probe_result.json#ae1740ac0b15"],
         "next_falsifier": "Re-measure the three schemas/FROZEN: any byte move voids this binding; at the pinned bytes a "
                           "failed check, a non-discriminating control, or a forbidden semantic change falsifies the acceptance.",
         "artifact": "artifacts/worker-078/rec12_preaccept/"},
        {"event_id": "w078-rec12-artifact-harness", "event_type": "artifact", "created_at": NOW, "actor": "worker-078",
         "node_id": "F1,F2a,F2b", "gate": "G-FORM", "class_id": ";".join(report["class_ids"]), "task_id": TASK_ID,
         "artifact_type": "verifier_code", "path": "artifacts/worker-078/rec12_preaccept/verify_rec12_preaccept.py",
         "sha256": artifacts["artifacts/worker-078/rec12_preaccept/verify_rec12_preaccept.py"],
         "validation_status": "unverified",
         "note": "Deterministic REC-12 acceptance harness: A1a-A5c kernels + baseline projection + 15 controls; fail-closed exit.",
         "evidence_refs": [f"artifacts/worker-078/rec12_preaccept/report.json#{artifacts['artifacts/worker-078/rec12_preaccept/report.json'][:12]}"]},
        {"event_id": "w078-rec12-artifact-report", "event_type": "artifact", "created_at": NOW, "actor": "worker-078",
         "node_id": "F1,F2a,F2b", "gate": "G-FORM", "class_id": ";".join(report["class_ids"]), "task_id": TASK_ID,
         "artifact_type": "audit_report", "path": "artifacts/worker-078/rec12_preaccept/report.json",
         "sha256": artifacts["artifacts/worker-078/rec12_preaccept/report.json"], "validation_status": "unverified",
         "note": "Primary evidence: CARD_ITEMS_MET_AT_REV29, 20 PASS / 2 WARN / 0 FAIL at F1 d9cebb9404b2 / F2a e9a27996dfd3 / F2b b2ab6acb2bbe / FROZEN rev29.",
         "evidence_refs": [f"schemas/af_wcc_vacuum.yaml#{pins['F1'][:12]}", f"schemas/af_scc_c2_vacuum.yaml#{pins['F2a'][:12]}",
                           f"schemas/af_scc_c0_vacuum.yaml#{pins['F2b'][:12]}", f"artifacts/formulation/FROZEN.json#{frozen_live[:12]}"]},
        {"event_id": "w078-rec12-artifact-rerun", "event_type": "artifact", "created_at": NOW, "actor": "worker-078",
         "node_id": "F1,F2a,F2b", "gate": "G-FORM", "class_id": ";".join(report["class_ids"]), "task_id": TASK_ID,
         "artifact_type": "audit_report", "path": "artifacts/worker-078/rec12_preaccept/report_rerun.json",
         "sha256": artifacts["artifacts/worker-078/rec12_preaccept/report_rerun.json"], "validation_status": "unverified",
         "note": f"Byte-pinned test-retest: normalized digest identical ({report['normalized_sha256'][:16]}).",
         "evidence_refs": [f"artifacts/worker-078/rec12_preaccept/report.json#{artifacts['artifacts/worker-078/rec12_preaccept/report.json'][:12]}"]},
        {"event_id": "w078-rec12-artifact-controls", "event_type": "artifact", "created_at": NOW, "actor": "worker-078",
         "node_id": "F1,F2a,F2b", "gate": "G-FORM", "class_id": ";".join(report["class_ids"]), "task_id": TASK_ID,
         "artifact_type": "controls_report", "path": "artifacts/worker-078/rec12_preaccept/controls.json",
         "sha256": artifacts["artifacts/worker-078/rec12_preaccept/controls.json"], "validation_status": "unverified",
         "note": f"{controls['n']}/{controls['n']} seeded controls correct (C2b/C7b/C9b positive, C1-C11 negative).",
         "evidence_refs": [f"artifacts/worker-078/rec12_preaccept/controls.json#{artifacts['artifacts/worker-078/rec12_preaccept/controls.json'][:12]}"]},
        {"event_id": "w078-rec12-artifact-readme", "event_type": "artifact", "created_at": NOW, "actor": "worker-078",
         "node_id": "F1,F2a,F2b", "gate": "G-FORM", "class_id": ";".join(report["class_ids"]), "task_id": TASK_ID,
         "artifact_type": "summary", "path": "artifacts/worker-078/rec12_preaccept/README.md",
         "sha256": artifacts["artifacts/worker-078/rec12_preaccept/README.md"], "validation_status": "unverified",
         "note": "Method, card crosswalk, result table, baseline projection, controls, residuals, limits.",
         "evidence_refs": [f"artifacts/worker-078/rec12_preaccept/report.json#{artifacts['artifacts/worker-078/rec12_preaccept/report.json'][:12]}"]},
        {"event_id": "w078-rec12-artifact-checkpoint", "event_type": "artifact", "created_at": NOW, "actor": "worker-078",
         "node_id": "F1,F2a,F2b", "gate": "G-FORM", "class_id": ";".join(report["class_ids"]), "task_id": TASK_ID,
         "artifact_type": "checkpoint", "path": "runtime/state/w078_checkpoint_6_rec12_preaccept.json",
         "sha256": checkpoint_sha, "validation_status": "unverified",
         "note": "Worker checkpoint: pins, counts, baseline recovery/projection, artifacts, non-claims, falsifier.",
         "evidence_refs": [f"artifacts/worker-078/rec12_preaccept/report.json#{artifacts['artifacts/worker-078/rec12_preaccept/report.json'][:12]}"]},
        {"event_id": "w078-rec12-artifact-review-body", "event_type": "artifact", "created_at": NOW, "actor": "worker-078",
         "node_id": "F1,F2a,F2b", "gate": "G-FORM", "class_id": ";".join(report["class_ids"]), "task_id": TASK_ID,
         "artifact_type": "review_body", "path": "reviews/W078-REC12-acceptance-078.json",
         "sha256": review_sha, "validation_status": "unverified",
         "note": "Review record: verdict accept, score 4.0, zero hard failures, three classified residuals.",
         "evidence_refs": [f"artifacts/worker-078/rec12_preaccept/report.json#{artifacts['artifacts/worker-078/rec12_preaccept/report.json'][:12]}"]},
        {"event_id": "w078-rec12-claim-acceptance", "event_type": "claim", "created_at": NOW, "actor": "worker-078",
         "node_id": "F1,F2a,F2b", "gate": "G-FORM", "class_id": ";".join(report["class_ids"]), "task_id": TASK_ID,
         "conclusion_type": "formal_model",
         "statement": "At the measured rev13 pins (F1 d9cebb9404b2, F2a e9a27996dfd3, F2b b2ab6acb2bbe) and FROZEN rev29 "
                      "(815e08079aef), the astra-life05-evidence-binding-repair card is met: corpus rows bound to F0 rev5 "
                      "0abb9ed8 (36/36, checker PASS 11/11 controls); all three schemas declare the live consistency evidence "
                      "9e335e9b and an isolated canonical-checker run reproduces it byte-for-byte; the F1 SET direction is "
                      "corrected to strictly WEAKER with D5/visibility equivalence; the rev29 manifest's 52 pins all match "
                      "live bytes and the moved paths carry artifact events. 20 PASS / 2 WARN / 0 FAIL, 15/15 controls, "
                      "zero drift, byte-pinned test-retest identical. No forbidden class-definition/hypothesis/conclusion/"
                      "axis change vs the rev12 baseline and no F0 write.",
         "assumptions": ["the four acceptance items are exactly those in map.assignments['astra-life05-evidence-binding-repair']",
                         "the rev12/rev28 baseline copies from worker-086/worker-074 are faithful (each re-hashed before use)",
                         "worker-076's strictness table is the direction authority for item 3"],
         "falsifier": review_body["falsifier"],
         "artifact_refs": [f"artifacts/worker-078/rec12_preaccept/report.json#{artifacts['artifacts/worker-078/rec12_preaccept/report.json'][:12]}",
                           f"artifacts/worker-078/rec12_preaccept/controls.json#{artifacts['artifacts/worker-078/rec12_preaccept/controls.json'][:12]}"],
         "evidence_refs": [f"schemas/af_wcc_vacuum.yaml#{pins['F1'][:12]}", f"schemas/af_scc_c2_vacuum.yaml#{pins['F2a'][:12]}",
                           f"schemas/af_scc_c0_vacuum.yaml#{pins['F2b'][:12]}", f"artifacts/formulation/FROZEN.json#{frozen_live[:12]}",
                           f"artifacts/formulation/evidence/taxonomy_consistency.json#{report['binding']['evidence_sha256'][:12]}",
                           f"schemas/taxonomy_cases.jsonl#{report['binding']['cases_sha256'][:12]}"]},
        {"event_id": "w078-rec12-review-publication", "event_type": "review", "created_at": NOW, "actor": "worker-078",
         "reviewer": "worker-078", "node_id": "F1,F2a,F2b", "gate": "G-FORM",
         "class_id": ";".join(report["class_ids"]), "task_id": TASK_ID,
         "target_id": f"artifacts/formulation/FROZEN.json#{frozen_live[:12]}",
         "target_kind": "repair_card_publication",
         "verdict": "accept", "score": 4.0,
         "counts_as_full_schema_verdict": False, "counts_toward_gate_accept": False,
         "reviewed_sha256": frozen_live,
         "binding": "rev13 schemas + rev29 manifest measured live at report time; pins re-checked before emission",
         "hard_failures": [],
         "findings": review_body["findings"],
         "residuals": review_body["residuals"],
         "evidence_refs": review_body["evidence_refs"],
         "falsifier": review_body["falsifier"]},
        {"event_id": "w078-rec12-blocker-f2b-scope", "event_type": "blocker", "created_at": NOW, "actor": "worker-078",
         "node_id": "F2b", "gate": "G-FORM", "class_id": "AF-SCC-C0-VAC-GEN", "task_id": TASK_ID,
         "description": "The authorized REC-12 repair is complete at rev29, but F2b :245 still asserts the inverted premise "
                        "'C2 is a strictly larger extension class' while the file's own chain at :238 places E_C2 smallest. "
                        "Three independent workers reported it (worker-066 W066-R12-F2B-H1, worker-060 HF-060-CS-01, "
                        "worker-008 W008-CD CD-01) and it is not among the four repair items; a rev29 F2b accept written "
                        "without a disposition would be written over a known hard failure.",
         "needed_to_unblock": "Astra either authorizes a bounded fifth repair item (assertion-direction wording only, new "
                              "schema bytes + FROZEN rev30) or records an explicit disposition that the inverted premise is "
                              "non-blocking for G-FORM; the r3 F2b reviewers then bind their verdicts to the resulting hash.",
         "evidence_refs": [f"schemas/af_scc_c0_vacuum.yaml#{pins['F2b'][:12]}", "schemas/af_scc_c0_vacuum.yaml:245",
                           "schemas/af_scc_c0_vacuum.yaml:238", "reviews/F2b-containment-normativity-worker-066.json",
                           f"artifacts/worker-078/rec12_preaccept/report.json#{artifacts['artifacts/worker-078/rec12_preaccept/report.json'][:12]}"],
         "falsifier": "the premise sentence is repaired at new bytes, or a controller disposition records it as non-blocking"},
        {"event_id": "w078-rec12-status-final", "event_type": "status", "created_at": NOW, "actor": "worker-078",
         "node_id": "F1,F2a,F2b", "gate": "G-FORM", "class_id": ";".join(report["class_ids"]), "task_id": TASK_ID,
         "status": "active", "hours": 0.6,
         "summary": "W078-REC12-PREACCEPT-01 complete at worker level (completion claim only; not a node transition and not "
                    "a gate verdict). Independent acceptance measurement of the REC-12 repair at F1 d9cebb9404b2 / F2a "
                    "e9a27996dfd3 / F2b b2ab6acb2bbe / FROZEN rev29 815e08079aef: 20 PASS / 2 WARN / 0 FAIL, 15/15 controls, "
                    "zero drift, byte-pinned test-retest identical; baseline projection shows A2a*/A3a/A4a firing on the "
                    "recovered rev12/rev28 bytes and clearing at rev29; residuals S1 (F2b :245, outside the four items), "
                    "S4 (evidence input-anchoring) and S2 (SET falsifier wording) recorded. Worker exits now.",
         "evidence_refs": [f"artifacts/worker-078/rec12_preaccept/report.json#{artifacts['artifacts/worker-078/rec12_preaccept/report.json'][:12]}",
                           f"reviews/W078-REC12-acceptance-078.json#{review_sha[:12]}",
                           f"runtime/state/w078_checkpoint_6_rec12_preaccept.json#{checkpoint_sha[:12]}",
                           f"schemas/af_wcc_vacuum.yaml#{pins['F1'][:12]}", f"artifacts/formulation/FROZEN.json#{frozen_live[:12]}"],
         "next_falsifier": review_body["falsifier"],
         "artifact": "artifacts/worker-078/rec12_preaccept/",
         "completion_scope": "worker lifecycle only; not a node done / gate verdict"},
    ]

    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line).get("event_id"))
            except json.JSONDecodeError:
                pass
    to_append = [e for e in events if e.get("event_id") not in existing]
    # schema sanity before writing
    for e in to_append:
        assert e["event_id"] and e["event_type"] and e["created_at"] and e["actor"], e
        json.dumps(e)
    if to_append:
        with OUTBOX.open("a") as f:
            for e in to_append:
                f.write(json.dumps(e) + "\n")

    print(f"checkpoint {checkpoint_sha[:16]} review {review_sha[:16]} events_appended={len(to_append)} "
          f"already_present={len(events) - len(to_append)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
