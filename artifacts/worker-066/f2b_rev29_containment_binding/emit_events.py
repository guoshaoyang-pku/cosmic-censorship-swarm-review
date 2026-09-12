#!/usr/bin/env python3
"""W066-F2B-REV29-CONTAINMENT-01 -- emit the upward event set (schema-validated) and the
worker-local checkpoint, then append the events to comms/outbox/worker-066.jsonl.

Append-only: refuses to emit an event_id that already exists in the outbox.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

TASK = "W066-F2B-REV29-CONTAINMENT-01"
STAMP = datetime.now(CST).strftime("%Y%m%dT%H%M%S")
EID = f"w066-f2b-rev29cb-{STAMP}"
NOW = datetime.now(CST).isoformat(timespec="seconds")
C0 = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"
FROZEN = "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"
FALSIFIER = ("Re-run rebind.py on the same pins: falsified if live C0 is not b2ab6acb2bbe, either defect clause "
             "is absent/changed at rev13, FROZEN rev29 815e0807 does not declare the measured hashes, the rebased "
             "live+2-edit text is not finding-free, a sibling carries either defect kind at its pin, any "
             "pre-registered control departs from its expectation, or a reviewer shows the two clauses "
             "non-normative at the bound hash.")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def find_line(text: str, needle: str):
    pos = text.find(needle)
    return text.count("\n", 0, pos) + 1 if pos >= 0 else None


def main() -> int:
    c0_path = ROOT / "schemas/af_scc_c0_vacuum.yaml"
    c0_text = c0_path.read_text()
    h2_line = find_line(c0_text, "No containment with C2 or C0 is asserted")
    h1_line = find_line(c0_text, "strictly larger extension class")

    # 1. human-readable review artifact at the canonical review path
    review_doc = {
        "reviewer": "worker-066",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
        "gate": "G-FORM",
        "task_id": TASK,
        "created_at": NOW,
        "target_id": f"schemas/af_scc_c0_vacuum.yaml#{C0}#containment-rebase",
        "reviewed_sha256": C0,
        "verdict": "revise",
        "score": 2.5,
        "counts_as_full_schema_verdict": False,
        "hard_failures": ["W066-R13-F2B-H1", "W066-R13-F2B-H2"],
        "findings": [
            (f"W066-R13-F2B-H1 [hard] regularity.must_not_conflate[0] (line {h2_line}) is a live containment denial "
             "('No containment with C2 or C0 is asserted here') in a file that asserts that containment at :238, "
             ":242-243 and :274; the sibling C2 rev13 carries the corrected nesting wording at the same slot. "
             "Byte-identical to rev12 55d0a1ea:157, so rev13 carried it over."),
            (f"W066-R13-F2B-H2 [hard] implication_ledger.forbidden_transfers[0].reason (line {h1_line}) says 'C2 is "
             "a strictly larger extension class'; the file's own chain is E_C0 contains E_H2loc contains E_{C^1,1} "
             "contains E_C2, so E_C2 is strictly SMALLER. Byte-identical to rev12 55d0a1ea:251."),
            ("RE-BASED TO THE CURRENT PINS: FROZEN rev29 third write 815e08079aef (frozen_at 00:57:26) declares "
             "exactly the measured canonical+mirror rev13 hashes, so both normative clauses (rule_spec R06/R16) are "
             "now freeze-bound; the earlier rev29 erratum bound 3d9e3d77 and is superseded."),
            ("REPAIR READY, NOT LANDED: live+2-reference-edits is finding-free at rebased candidate "
             "84b5d3fa29a677ad157b924675bb5a9c08281395920be0221535465a5da44b40; the repair is absent from live bytes "
             "and the rev12->rev13 delta touches only f0_binding/revised_at/revision/revision_history."),
            ("13/13 checks and 8/8 pre-registered controls matched on the pinned copies; C2 e9a27996 and F1 "
             "d9cebb94 carry neither defect kind; no pinned byte moved during the run. Verdict binds b2ab6acb and "
             "815e0807 only and is void on any hash move."),
        ],
        "evidence_refs": [
            f"artifacts/worker-066/f2b_rev29_containment_binding/report.json",
            f"artifacts/worker-066/f2b_rev29_containment_binding/evidence/checks.json",
            f"artifacts/worker-066/f2b_rev29_containment_binding/evidence/controls.json",
            f"artifacts/worker-066/f2b_rev29_containment_binding/evidence/freeze_binding.json",
            f"schemas/af_scc_c0_vacuum.yaml#{C0[:12]}",
            f"artifacts/formulation/FROZEN.json#{FROZEN[:12]}",
        ],
        "next_falsifier": FALSIFIER,
    }
    rv_path = ROOT / "reviews/F2b-rev29-containment-rebase-worker-066.json"
    rv_path.write_text(json.dumps(review_doc, indent=1) + "\n")

    art = {
        "pin": OUT / "pin.py",
        "rebind": OUT / "rebind.py",
        "readme": OUT / "README.md",
        "report": OUT / "report.json",
        "checks": OUT / "evidence/checks.json",
        "controls": OUT / "evidence/controls.json",
        "freeze_binding": OUT / "evidence/freeze_binding.json",
        "pins": OUT / "evidence/pins.json",
        "checkpoint_artifact": OUT / "CHECKPOINT.json",
        "review": rv_path,
    }
    h = {k: sha(v) for k, v in art.items()}

    # 2. worker-local checkpoint (referenced by the checkpoint status event)
    ckpt = {
        "checkpoint_id": f"w066-f2b-rev29cb-{STAMP}",
        "task_id": TASK,
        "created_at": NOW,
        "actor": "worker-066",
        "agent_slot": "worker-066",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
        "gate": "G-FORM",
        "status": "complete-worker-lifecycle",
        "verdict": "revise 2.5",
        "pins": {"c0": C0, "frozen": FROZEN, "c2": "e9a27996dfd3", "f1": "d9cebb9404b2",
                 "f0": "0abb9ed8a961", "consistency_evidence": "9e335e9ba1bf"},
        "rebased_candidate": "84b5d3fa29a677ad157b924675bb5a9c08281395920be0221535465a5da44b40",
        "defects_live": [
            {"clause": "regularity.must_not_conflate[0]", "line": h2_line, "kind": "false_containment_denial"},
            {"clause": "implication_ledger.forbidden_transfers[0].reason", "line": h1_line, "kind": "size_premise_inverted"},
        ],
        "checks": "13/13", "controls": "8/8", "pins_stable_entry_exit": True,
        "artifact_hashes": h,
        "next_falsifier": FALSIFIER,
    }
    ckpt_path = ROOT / f"runtime/state/w066_f2b_rev29_containment_binding_checkpoint.json"
    ckpt_path.write_text(json.dumps(ckpt, indent=1) + "\n")

    base_ev = {"created_at": NOW, "actor": "worker-066", "task_id": TASK,
               "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN",
               "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"]}
    events = []

    def add(e):
        e.update({k: v for k, v in base_ev.items() if k not in e})
        events.append(e)

    ev_refs = [f"schemas/af_scc_c0_vacuum.yaml#{C0[:12]}",
               f"artifacts/formulation/FROZEN.json#{FROZEN[:12]}",
               "artifacts/worker-066/f2b_rev29_containment_binding/report.json",
               "artifacts/worker-066/f2b_rev29_containment_binding/evidence/checks.json",
               "artifacts/worker-066/f2b_rev29_containment_binding/evidence/controls.json"]

    add({"event_id": f"{EID}-status-taken", "event_type": "status", "status": "active", "hours": 0.1,
         "summary": ("No assignment card exists for worker-066. Took ONE bounded class-bound task: independent "
                     "order-relative re-base of the F2b containment defects onto the current FROZEN rev29 pins "
                     "(C0 b2ab6acb, manifest 815e0807), class AF-SCC-C0-VAC-GEN. Reviewer verdict only."),
         "evidence_refs": ev_refs, "next_falsifier": FALSIFIER})

    for key, note in [
        ("pin", "read-only pin step; nine inputs hashed, copied, exit 2 on any mismatch"),
        ("rebind", "fresh order-relative checker + 8 pre-registered controls; re-runnable on the pins"),
        ("readme", "method, result table, consequence for G-FORM r3, falsifier, limits"),
        ("report", "verdict revise 2.5, live defects, repair status, freeze binding, falsifier"),
        ("checks", "13/13 checks with expected vs observed on the pinned copies"),
        ("controls", "8/8 pre-registered controls, expected vs observed"),
        ("freeze_binding", "FROZEN rev29 pin table + rev12->rev13 changed-leaf-path list"),
        ("pins", "sha256/bytes/mtime + byte copies of the nine inputs"),
        ("checkpoint_artifact", "task-level checkpoint record"),
        ("review", "hash-bound reviewer verdict at b2ab6acb, counts_as_full_schema_verdict=false"),
    ]:
        add({"event_id": f"{EID}-artifact-{key}", "event_type": "artifact",
             "artifact_type": {"pin": "code", "rebind": "code", "readme": "readme", "report": "verdict",
                               "checks": "evidence", "controls": "evidence", "freeze_binding": "evidence",
                               "pins": "manifest", "checkpoint_artifact": "manifest", "review": "review"}[key],
             "path": str(art[key].relative_to(ROOT)), "sha256": h[key],
             "validation_status": "unverified", "note": note})

    add({"event_id": f"{EID}-claim", "event_type": "claim", "conclusion_type": "formal_model",
         "statement": (f"At the live rev13 F2b bytes schemas/af_scc_c0_vacuum.yaml#{C0[:12]} and the third FROZEN "
                       f"rev29 write artifacts/formulation/FROZEN.json#{FROZEN[:12]} (frozen_at 00:57:26), a fresh "
                       "order-relative checker reproduces exactly two live containment defects: H1 inverted size "
                       f"premise at implication_ledger.forbidden_transfers[0].reason (line {h1_line}) and H2 live "
                       f"containment denial at regularity.must_not_conflate[0] (line {h2_line}). Both clauses are "
                       "byte-identical to superseded rev12 55d0a1ea, the rev12->rev13 delta touches only "
                       "f0_binding/revised_at/revision/revision_history, FROZEN rev29 declares exactly the measured "
                       "canonical+mirror rev13 hashes, applying the two reference edits to live yields a "
                       "finding-free rebased candidate 84b5d3fa29a6, siblings C2 e9a27996 and F1 d9cebb94 carry "
                       "neither defect kind, and 13/13 checks plus 8/8 pre-registered controls matched with no pin "
                       "drift. The ready repair is not landed, so the two clause carriers are freeze-bound "
                       "unrepaired. This is a text-consistency and binding result, not a claim about the "
                       "mathematics of C0/C2 inextendibility."),
         "assumptions": ["a verdict binds bytes, not paths; every check ran on pinned copies",
                         "the document's own extension_class_containment sentence is the reference order",
                         "'extension class' means the extension set E_X as the document defines it",
                         "bracketed corrections are withdrawn text, not live assertions",
                         "rule_spec R06/R16 make both carriers normative (established separately at rev13)"],
         "falsifier": FALSIFIER,
         "evidence_refs": [f"schemas/af_scc_c0_vacuum.yaml#{C0[:12]}",
                           f"artifacts/formulation/FROZEN.json#{FROZEN[:12]}",
                           "artifacts/worker-066/f2b_rev29_containment_binding/evidence/checks.json",
                           "artifacts/worker-066/f2b_rev29_containment_binding/evidence/controls.json",
                           "artifacts/worker-066/f2b_rev29_containment_binding/evidence/freeze_binding.json"],
         "artifact_refs": [f"artifacts/worker-066/f2b_rev29_containment_binding/report.json#{h['report'][:12]}"]})

    add({"event_id": f"{EID}-review", "event_type": "review", "reviewer": "worker-066",
         "target_id": f"schemas/af_scc_c0_vacuum.yaml#{C0}#containment-rebase",
         "reviewed_sha256": C0, "verdict": "revise", "score": 2.5,
         "counts_as_full_schema_verdict": False,
         "hard_failures": ["W066-R13-F2B-H1", "W066-R13-F2B-H2"],
         "findings": review_doc["findings"],
         "evidence_refs": review_doc["evidence_refs"], "next_falsifier": FALSIFIER})

    add({"event_id": f"{EID}-blocker", "event_type": "blocker",
         "description": ("F2b rev13 b2ab6acb still carries the two normative containment defects and FROZEN rev29 "
                         "815e0807 now freeze-binds those exact bytes, so a G-FORM r3 accept at this pin would "
                         "freeze them. The astra-life05 evidence-binding card was bounded against class-semantics "
                         "changes, so the ready 2-edit repair was not folded in."),
         "needed_to_unblock": ("lead-formulation (owner): apply artifacts/worker-066/f2b_repair_prereg/"
                               "proposed_patch.diff (or the rebased live+2-edit semantics 84b5d3fa) to "
                               "schemas/af_scc_c0_vacuum.yaml, bump revision, mirror byte-identically, re-freeze; "
                               "then re-run rebind.py and require the live target finding-free with C2 e9a27996 "
                               "unchanged. lead-audit: include an order-relative containment check in "
                               "astra-life05-verify-gform-r3."),
         "evidence_refs": ev_refs, "stop_rule": "live C0 revision with both clauses repaired + re-freeze + rebind.py PASS"})

    add({"event_id": f"{EID}-status-complete", "event_type": "status", "status": "active", "hours": 0.7,
         "summary": ("W066-F2B-REV29-CONTAINMENT-01 complete as a bounded worker lifecycle: verdict revise 2.5 at "
                     "the current rev29 pins; both defects re-based and proven carried over; freeze binding proven; "
                     "repair proven absent and rebased candidate proven clean; 13/13 checks, 8/8 controls, no pin "
                     "drift. This is a completion claim, not a node/gate transition. Checkpoint follows."),
         "evidence_refs": ["artifacts/worker-066/f2b_rev29_containment_binding/report.json",
                           f"reviews/F2b-rev29-containment-rebase-worker-066.json#{h['review'][:12]}",
                           f"schemas/af_scc_c0_vacuum.yaml#{C0[:12]}"],
         "next_falsifier": FALSIFIER})

    add({"event_id": f"{EID}-status-checkpoint", "event_type": "status", "status": "active", "hours": 0.75,
         "summary": (f"Checkpoint written to runtime/state/w066_f2b_rev29_containment_binding_checkpoint.json "
                     f"(w066-f2b-rev29cb-{STAMP}); pins re-measured unchanged after the run (C0 b2ab6acb, C2 "
                     "e9a27996, F1 d9cebb94, F0 0abb9ed8, FROZEN 815e0807); live pin drift none. worker-066 "
                     "lifecycle complete; this event lands in the next ingest cycle."),
         "evidence_refs": [f"runtime/state/w066_f2b_rev29_containment_binding_checkpoint.json#{sha(ckpt_path)[:12]}",
                           f"schemas/af_scc_c0_vacuum.yaml#{C0[:12]}",
                           "artifacts/worker-066/f2b_rev29_containment_binding/CHECKPOINT.json"],
         "next_falsifier": "any hash move of C0 b2ab6acb or FROZEN 815e0807, or a rev14 that folds in the 2-edit repair (supersedes this revise)"})

    for e in events:
        validate_event(e)

    outbox = ROOT / "comms/outbox/worker-066.jsonl"
    existing = outbox.read_text() if outbox.exists() else ""
    dupes = [e["event_id"] for e in events if f'"{e["event_id"]}"' in existing]
    if dupes:
        print("REFUSING duplicate event_ids:", dupes)
        return 2
    with outbox.open("a") as fh:
        for e in events:
            fh.write(json.dumps(e) + "\n")
    print(json.dumps({"appended": len(events), "outbox": str(outbox.relative_to(ROOT)),
                      "review": str(rv_path.relative_to(ROOT)), "review_sha256": h["review"],
                      "checkpoint": str(ckpt_path.relative_to(ROOT))}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
