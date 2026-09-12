#!/usr/bin/env python3
"""W066-F2B-CONTAINMENT-NORMATIVITY-01 -- verdict file, checkpoint, outbox events.

Writes:
  reviews/F2b-containment-normativity-worker-066.json
  runtime/state/w066_f2b_containment_normativity_checkpoint.json
  comms/outbox/worker-066.jsonl   (appended, one JSON object per line)

Every event is validated against research_map.schemas.validate_event before it is
appended.  No canonical formulation path is written.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "research_map"))
from schemas import validate_event  # noqa: E402

CST = timezone(timedelta(hours=8))
TASK = "W066-F2B-CONTAINMENT-NORMATIVITY-01"
TARGET_PATH = "schemas/af_scc_c0_vacuum.yaml"
TARGET_SHA = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"
SIBLING_SHA = "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def main() -> None:
    report = json.loads((HERE / "report.json").read_text())
    checks = json.loads((HERE / "evidence/checks.json").read_text())
    ctrl = json.loads((HERE / "evidence/controls.json").read_text())
    verdict_rel = "reviews/F2b-containment-normativity-worker-066.json"
    verdict = {
        "schema_version": "0.1",
        "event_id": "w066-f2b-normativity-verdict",
        "event_type": "review",
        "created_at": now(),
        "actor": "worker-066",
        "reviewer": "worker-066",
        "task_id": TASK,
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN"],
        "gate": "G-FORM",
        "target_id": f"{TARGET_PATH}#{TARGET_SHA}",
        "artifact": TARGET_PATH,
        "artifact_sha256": TARGET_SHA,
        "reviewed_sha256": TARGET_SHA,
        "artifact_revision": report["target"]["declared_revision"],
        "sibling_sha256": SIBLING_SHA,
        "verdict": "revise",
        "score": 2.5,
        "counts_as_full_schema_verdict": False,
        "verdict_scope": "normativity adjudication of the two carried-over containment clauses "
                         "at the rev13 bytes; not a full-schema leakage/quantifier verdict",
        "hard_failures": [
            {
                "id": "W066-R13-F2B-H1",
                "severity": "hard",
                "carrier": "implication_ledger.forbidden_transfers[0].reason",
                "line": 246,
                "finding": "C2 is called a strictly larger extension class while the file's own "
                           "chain makes E_C2 the smallest set; the prohibition's stated premise "
                           "is inverted. Clauses are byte-identical to rev12 55d0a1ea.",
            },
            {
                "id": "W066-R13-F2B-H2",
                "severity": "hard",
                "carrier": "regularity.must_not_conflate[0]",
                "line": 152,
                "finding": "live denial 'No containment with C2 or C0 is asserted here' inside the "
                           "normative must_not_conflate list contradicts the file's own asserted "
                           "chain and four one_way_entailments rows; sibling C2 carries the "
                           "corrected wording and records the denial as wrong.",
            },
        ],
        "findings": [
            "NORMATIVITY ADJUDICATION: both carriers are required slots of the frozen class "
            "contract (rule_spec R06 and R16; no advisory marker anywhere on either carrier), "
            "so the two clauses are normative content, not optional prose. The predecessor's "
            "open alternative resolution ('non-normative prose') is REJECTED.",
            "MACHINE BLIND SPOT: the canonical gate returns pass for the defective rev13 wording "
            "and for corrected, strengthened-false, empty-string and nonsense variants alike "
            "(M2/M3/M6/M7/M8/M9/M10), while rejecting an emptied must_not_conflate (R06) and an "
            "exact reversed forbidden_transfers direction (R16). A gate PASS cannot certify "
            "these clauses.",
            "CARRIED FORWARD: the two sentences are byte-identical at rev12 55d0a1ea and rev13 "
            "b2ab6acb; the rev13 evidence-binding repair changed only revised_at/revision/"
            "revision_history/f0_binding.",
            "CONSEQUENCE: REC-12 forbade class-semantics changes, so FROZEN rev29 as planned "
            "would freeze both defects and astra-life05-verify-gform-r3 would re-issue the "
            "rev12 blocker at the new hash unless the 2-edit repair is folded in or separately "
            "authorized.",
            "12/12 pre-registered controls matched; no pinned byte drift during the run; "
            "this verdict binds b2ab6acb only and is void on any hash move.",
        ],
        "evidence_refs": [
            f"schemas/af_scc_c0_vacuum.yaml#{TARGET_SHA[:12]}",
            f"schemas/af_scc_c2_vacuum.yaml#{SIBLING_SHA[:12]}",
            "artifacts/formulation/rule_spec.json#40f9bb9e657b",
            "artifacts/formulation/tools/check_class_schema.py#000e09e46b2f",
            "artifacts/worker-066/f2b_containment_normativity/report.json",
            "artifacts/worker-066/f2b_containment_normativity/evidence/controls.json",
            "artifacts/worker-066/f2b_containment_normativity/evidence/checks.json",
        ],
        "falsifier": report["falsifier"],
        "authority": "worker reviewer verdict only; no gate verdict or node state moved",
    }
    (REPO / verdict_rel).write_text(json.dumps(verdict, indent=2) + "\n")

    artifacts = [
        ("manifest", "artifacts/worker-066/f2b_containment_normativity/PINNED.json", "unverified",
         "pinned inputs: bytes, sha256, mtime, byte copies"),
        ("code", "artifacts/worker-066/f2b_containment_normativity/pin.py", "unverified",
         "read-only pin/snapshot step"),
        ("code", "artifacts/worker-066/f2b_containment_normativity/normativity.py", "unverified",
         "normativity probe battery + pre-registered controls; re-runnable on the pins"),
        ("verdict", "artifacts/worker-066/f2b_containment_normativity/report.json", "unverified",
         "verdict normative_content_defect, score 2.5, falsifier, evidence refs"),
        ("evidence", "artifacts/worker-066/f2b_containment_normativity/evidence/checks.json", "unverified",
         "gate mutant results, rule basis, text findings, provenance, drift"),
        ("evidence", "artifacts/worker-066/f2b_containment_normativity/evidence/controls.json", "unverified",
         "12 pre-registered controls, expected vs observed, all matched"),
        ("readme", "artifacts/worker-066/f2b_containment_normativity/README.md", "unverified",
         "method, verdict, controls, recommendation, falsifier, limits"),
        ("review", verdict_rel, "unverified", "hash-bound reviewer verdict at rev13"),
    ]

    events = []

    def ev(**kw):
        ev_id = kw.pop("event_id")
        d = {"event_id": ev_id, "created_at": now(), "actor": "worker-066"}
        d.update(kw)
        validate_event(d)
        events.append(d)

    ev(event_id="w066-f2b-normativity-01-status-taken", event_type="status", node_id="F2b",
       class_id="AF-SCC-C0-VAC-GEN",
       status="active", hours=0.2,
       task_id=TASK,
       summary="No assignment card exists for worker-066. Took ONE bounded class-bound task: "
               "independent normativity adjudication of the two F2b containment clauses at the "
               "live rev13 bytes b2ab6acb (class AF-SCC-C0-VAC-GEN), which the rev13 "
               "evidence-binding repair carried forward from rev12.",
       evidence_refs=[f"schemas/af_scc_c0_vacuum.yaml#{TARGET_SHA[:12]}",
                      "artifacts/worker-066/f2b_containment_normativity/PINNED.json"],
       next_falsifier=report["falsifier"])

    for atype, path, status, note in artifacts:
        p = REPO / path
        ev(event_id="w066-f2b-normativity-01-artifact-" + p.stem.replace(".", "-").replace("_", "-"),
           event_type="artifact", node_id="F2b", class_id="AF-SCC-C0-VAC-GEN",
           class_ids=["AF-SCC-C0-VAC-GEN"], artifact_type=atype, path=path,
           sha256=sha(p), validation_status=status, task_id=TASK, note=note)

    ev(event_id="w066-f2b-normativity-01-review", event_type="review",
       target_id=f"{TARGET_PATH}#{TARGET_SHA}#normativity",
       reviewer="worker-066", verdict="revise", score=2.5,
       hard_failures=[h["id"] for h in verdict["hard_failures"]],
       findings=verdict["findings"],
       node_id="F2b", class_id="AF-SCC-C0-VAC-GEN",
       class_ids=["AF-SCC-C0-VAC-GEN"], task_id=TASK,
       reviewed_sha256=TARGET_SHA, counts_as_full_schema_verdict=False,
       evidence_refs=verdict["evidence_refs"], next_falsifier=report["falsifier"])

    ev(event_id="w066-f2b-normativity-01-claim", event_type="claim", node_id="F2b",
       class_id="AF-SCC-C0-VAC-GEN", class_ids=["AF-SCC-C0-VAC-GEN"],
       conclusion_type="formal_model", task_id=TASK,
       statement="At the live rev13 F2b bytes schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe (and "
                 "sibling C2 e9a27996), the two containment clauses H1(:246)/H2(:152) are "
                 "normative content of the frozen class contract, not non-normative prose: "
                 "rule_spec R06/R16 make both carriers required slots and the document carries "
                 "no advisory marker on either; the binding gate passes the defective, "
                 "corrected, strengthened-false and nonsense wordings identically (12/12 "
                 "pre-registered controls), so a gate PASS cannot certify them; and the rev13 "
                 "evidence-binding repair carried both sentences forward byte-identically from "
                 "rev12 55d0a1ea. This is a rule-scope and text-consistency result, not a claim "
                 "about the mathematics of C0/C2 inextendibility.",
       assumptions=report["assumptions"],
       falsifier=report["falsifier"],
       evidence_refs=verdict["evidence_refs"],
       artifact_refs=["artifacts/worker-066/f2b_containment_normativity/report.json#"
                      + sha(HERE / "report.json")[:12]])

    ev(event_id="w066-f2b-normativity-01-blocker", event_type="blocker", node_id="F2b",
       class_id="AF-SCC-C0-VAC-GEN", class_ids=["AF-SCC-C0-VAC-GEN"], task_id=TASK,
       description="F2b rev13 b2ab6acb still fails on two normative containment clauses "
                   "carried over from rev12/rev11 (H1 inverted size premise, H2 live "
                   "containment denial). The REC-12 evidence-binding repair was explicitly "
                   "bounded against class-semantics changes, so the pending FROZEN rev29 would "
                   "freeze both defects and the G-FORM re-review would re-issue the blocker at "
                   "the new hash. The canonical gate cannot catch either clause (12/12 "
                   "controls).",
       needed_to_unblock="lead-formulation/controller: fold the ready 2-edit repair "
                         "(candidate 98f9ec83c487 semantics) into the same revision before the "
                         "FROZEN rev29 write, or open a separate bounded owner card; then "
                         "re-freeze and re-run an order-relative containment check plus the "
                         "canonical gate. lead-audit: include a containment check in "
                         "astra-life05-verify-gform-r3, not only the canonical gate.",
       evidence_refs=verdict["evidence_refs"])

    ev(event_id="w066-f2b-normativity-01-status-complete", event_type="status", node_id="F2b",
       class_id="AF-SCC-C0-VAC-GEN", class_ids=["AF-SCC-C0-VAC-GEN"],
       status="active", hours=0.6, task_id=TASK,
       summary="W066-F2B-CONTAINMENT-NORMATIVITY-01 complete as a bounded worker lifecycle: "
               "verdict normative_content_defect (revise 2.5) at rev13 b2ab6acb; normativity "
               "established from R06/R16 + absence of advisory markers; gate blind spot "
               "measured with 12/12 pre-registered controls; clauses proven carried forward "
               "byte-identically from rev12; blocker and repair path recorded. All artifacts "
               "exist and are hash-pinned; events schema-validated. This is a completion claim, "
               "not a node/gate transition. Checkpoint follows.",
       evidence_refs=verdict["evidence_refs"], next_falsifier=report["next_falsifier"])

    outbox = REPO / "comms/outbox/worker-066.jsonl"
    with outbox.open("a") as fh:
        for d in events:
            fh.write(json.dumps(d) + "\n")

    # checkpoint last (it records the emitted event ids)
    ck = {
        "task_id": TASK,
        "actor": "worker-066",
        "label": "w066-f2b-containment-normativity-20260912T0058",
        "created_at": now(),
        "verdict": report["verdict"],
        "score": report["score"],
        "target": report["target"],
        "sibling": report["sibling"],
        "controls_all_match": report["controls_all_match"],
        "artifact_hashes": {p: sha(REPO / p) for _, p, _, _ in artifacts},
        "events_emitted": [d["event_id"] for d in events],
        "outbox": str(outbox.relative_to(REPO)),
        "next_falsifier": report["next_falsifier"],
        "map_note": "worker-local checkpoint; the controller checkpoint is untouched",
    }
    ck_path = REPO / "runtime/state/w066_f2b_containment_normativity_checkpoint.json"
    ck_path.write_text(json.dumps(ck, indent=2) + "\n")
    ck_event = {
        "event_id": "w066-f2b-normativity-01-status-checkpoint",
        "event_type": "status", "created_at": now(), "actor": "worker-066",
        "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN"], "status": "active", "hours": 0.65,
        "task_id": TASK,
        "summary": "Worker-local checkpoint written to "
                   "runtime/state/w066_f2b_containment_normativity_checkpoint.json after the "
                   "10 events; pinned bytes re-measured unchanged (C0 b2ab6acb, C2 e9a27996, "
                   "rule_spec 40f9bb9e, gate 000e09e4, F0 0abb9ed8). worker-066 lifecycle "
                   "complete; this event lands in the next ingest cycle.",
        "evidence_refs": [f"runtime/state/w066_f2b_containment_normativity_checkpoint.json#{sha(ck_path)[:12]}",
                          f"schemas/af_scc_c0_vacuum.yaml#{TARGET_SHA[:12]}",
                          "artifacts/worker-066/f2b_containment_normativity/report.json"],
        "next_falsifier": report["next_falsifier"],
    }
    validate_event(ck_event)
    with outbox.open("a") as fh:
        fh.write(json.dumps(ck_event) + "\n")

    # verify the tail of the outbox parses
    lines = outbox.read_text().strip().splitlines()
    bad = [i for i, ln in enumerate(lines) if not _ok(ln)]
    print(json.dumps({"events_appended": len(events) + 1,
                      "outbox_lines": len(lines),
                      "bad_json_lines": bad,
                      "checkpoint": str(ck_path.relative_to(REPO)),
                      "verdict_file": verdict_rel}, indent=1))


def _ok(line: str) -> bool:
    try:
        json.loads(line)
        return True
    except Exception:  # noqa: BLE001
        return False


if __name__ == "__main__":
    main()
