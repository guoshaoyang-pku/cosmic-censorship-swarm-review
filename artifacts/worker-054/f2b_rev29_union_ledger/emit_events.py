#!/usr/bin/env python3
"""Emit W054-F2B-REV29-UNION-LEDGER-01 events to comms/outbox/worker-054.jsonl.

Idempotent: re-running skips event_ids already present in the outbox.
Reads report.json + MANIFEST.json; writes only the outbox.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUTBOX = ROOT / "comms/outbox/worker-054.jsonl"
CREATED = "2026-09-12T01:13:00+08:00"
TASK = "W054-F2B-REV29-UNION-LEDGER-01"
CLASSES = ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"]
NODE = "F2b"
GATE = "G-FORM"
NOT_CLAIMED = ["no gate verdict", "no node status", "no canonical artifact written",
               "no repair adopted", "not a mathematics claim"]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ev(eid: str, etype: str, **kw) -> dict:
    return {"actor": "worker-054", "created_at": CREATED, "event_id": eid,
            "event_type": etype, "task_id": TASK, **kw}


def main() -> int:
    rep = json.loads((HERE / "report.json").read_text())
    man = json.loads((HERE / "MANIFEST.json").read_text())
    pinned = json.loads((HERE / "PINNED.json").read_text())["pins"]
    # internal body hash (report_sha256 covers the report body without that field)
    body = {k: v for k, v in rep.items() if k != "report_sha256"}
    assert rep["report_sha256"] == hashlib.sha256(
        json.dumps(body, indent=1, sort_keys=True).encode()).hexdigest(), "body hash mismatch"
    # on-disk file hash, used for path#sha256-prefix evidence refs
    REP_FILE = sha(HERE / "report.json")

    files = {"checker.py": "code", "PINNED.json": "hash_manifest",
             "report.json": "measurement_report", "controls.json": "control_table",
             "README.md": "method_note", "MANIFEST.json": "hash_manifest",
             "emit_events.py": "event_emitter"}
    prefix = "w054-f2bunion-20260912T0113"
    events: list[dict] = []

    for name, atype in files.items():
        p = HERE / name
        h = sha(p)
        events.append(ev(f"{prefix}-artifact-{name.replace('.', '-')}", "artifact",
                         artifact_type=atype, path=str(p.relative_to(ROOT)),
                         sha256=h, validation_status="unverified",
                         class_ids=CLASSES, node_id=NODE, gate=GATE,
                         not_claimed=NOT_CLAIMED))

    ev_refs = [f"artifacts/worker-054/f2b_rev29_union_ledger/{n}#{sha(HERE / n)[:12]}"
               for n in ("report.json", "controls.json", "PINNED.json", "checker.py", "README.md")]

    events.append(ev(f"{prefix}-claim", "claim",
                     class_id="AF-SCC-C0-VAC-GEN", class_ids=CLASSES, node_id=NODE, gate=GATE,
                     conclusion_type="formal_model",
                     statement=(
                         "Union ledger of the reported F2b rev29 defect claims, re-measured from primary "
                         "bytes at schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe (FROZEN rev29 "
                         "artifacts/formulation/FROZEN.json#815e08079aef): 8/8 claims reproduced, 10/10 "
                         "controls. Exactly 2 are OPERATIVE binding-text contradictions in required "
                         "normative slots - :152 regularity.must_not_conflate[0] denies a containment "
                         "the same file asserts at :239, and :246 forbidden_transfers[0].reason inverts "
                         "the extension-set size premise against the same chain. 1 claim (D3 "
                         "conclusion_type) is alias-resolved non-blocking; 4 are binding hygiene; 1 is "
                         "an instrument blind spot: the canonical gate returns pass for the defective "
                         "bytes, for a nonsense H1 reason and for a fully reversed containment chain, "
                         "and fails only when a required slot is emptied (R01). Both available two-edit "
                         "candidate repairs close both carriers with the gate still passing; neither is "
                         "adopted here. Consequence for G-FORM r3: a second independent non-author "
                         "accept at rev29 is not justified at these bytes."),
                     assumptions=[
                         "all 12 inputs pinned by sha256 in PINNED.json; measured == declared at start and exit (drift false)",
                         "the claim inventory is the union of six reviewers' reported carriers; each was re-decided by this instrument, not taken on trust",
                         "materiality taxonomy pre-registered in report.json.materiality_rule",
                         "class semantics beyond the named carriers, mathematics, and F2a/F1 correctness are out of scope; F2a/F1 are controls only"],
                     falsifier=rep["next_falsifier"],
                     evidence_refs=ev_refs + [
                         "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
                         "artifacts/formulation/FROZEN.json#815e08079aef",
                         "artifacts/formulation/tools/check_class_schema.py#000e09e46b2f",
                         "artifacts/worker-002/f2b_containment_adjudication/candidate/af_scc_c0_vacuum.repair2edit.yaml#84b5d3fa29a6",
                         "artifacts/worker-083/f2b_live_defect_ledger/candidate/af_scc_c0_vacuum.yaml#1315427fbc92"],
                     artifact_refs=[f"artifacts/worker-054/f2b_rev29_union_ledger/report.json#{REP_FILE[:12]}"],
                     not_claimed=NOT_CLAIMED))

    events.append(ev(f"{prefix}-review", "review", reviewer="worker-054",
                     target_id="F2b@b2ab6acb2bbe (FROZEN rev29 815e08079aef)",
                     verdict="revise", score=3.0, gate=GATE, class_ids=CLASSES, node_id=NODE,
                     findings=[
                         "H1 :246 forbidden_transfers[0].reason states 'C2 is a strictly larger extension class' while the file's own chain at :239 makes E_C2 the innermost/smallest admissible-extension set; the row's from/to and conclusion are correct, the stated premise is false (reported by worker-017 B17-R13-01, worker-018 C18, worker-053 C10, worker-066 H1, worker-083 D1).",
                         "H2 :152 regularity.must_not_conflate[0] states 'No containment with C2 or C0 is asserted here' while the same file asserts that containment at :239 with four derived one-way entailments; the F2a sibling carries the corrected nesting wording and no denial (worker-017 B17-R13-02, worker-018 C17, worker-066 H2, worker-083 D2).",
                         "D3 conclusion_type scc_c0_future_inextendibility is outside F0's field_vocabulary.conclusion_type.allowed but is a canonical key in the frozen VOCAB_ALIASES.json and is consistent with frozen AMB-10 precedent: premise confirmed, severity non-blocking (worker-066 adjudication, independently re-derived here).",
                         "HYGIENE: revision_history is non-monotone in index order (index 9 at 23:30:35 precedes index 8 at 00:30:00) and names no row carrying the live declared F0 hash 0abb9ed8; side pins schemas/af_scc_c0_vacuum.yaml.sha256 and entry_hashes.json still declare 1bb78ce9; the nested provenance block at :75 carries worker_sha256 0150bfdf with a self-referential harvested_from and no on-disk referent in a bounded artifacts/ *.yaml scan; f0_binding names class_contract_supplement without a class_contract_supplement_sha256 pin.",
                         "INSTRUMENT: the canonical gate check_class_schema.py#000e09e46b2f returns pass for the defective bytes, for a nonsense H1 reason and for a fully reversed containment chain, and fails only when must_not_conflate is emptied (R01); a gate PASS cannot certify either carrier.",
                         "CANDIDATES (verified, not adopted): worker-002 repair2edit#84b5d3fa29a6 and worker-083 candidate#1315427fbc92 each close both carriers, keep the chain intact, and still pass the gate.",
                         "ADVISORY ONLY: this is a worker-level union ledger, not a full-schema verdict and not a gate verdict; G-FORM r3 owns the adjudication."],
                     hard_failures=[
                         {"id": "W054-F2BUNION-H1", "severity": "blocking-for-clean-accept",
                          "field": "implication_ledger.forbidden_transfers[0].reason", "line": 246,
                          "falsifier": "corrected bytes at :246 in a new F2b revision, or a containment-respecting model where E_C2 is strictly larger than E_C0"},
                         {"id": "W054-F2BUNION-H2", "severity": "blocking-for-clean-accept",
                          "field": "regularity.must_not_conflate[0]", "line": 152,
                          "falsifier": "corrected bytes at :152 in a new F2b revision, or an F2b revision that removes the asserted containment chain that contradicts the denial"}],
                     next_falsifier=rep["next_falsifier"],
                     evidence_refs=ev_refs + ["schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
                                              "artifacts/formulation/FROZEN.json#815e08079aef"],
                     not_claimed=NOT_CLAIMED))

    events.append(ev(f"{prefix}-blocker", "blocker", node_id=NODE, gate=GATE, class_ids=CLASSES,
                     description=("F2b cannot reach two independent non-author accepts at rev29 "
                                  "b2ab6acb2bbe: the only live non-author accept is worker-001, while the "
                                  "union ledger reproduces two operative binding-text contradictions in "
                                  "required normative slots (:152, :246) that the canonical gate cannot "
                                  "detect. The rev13 delta is binding-only, so both carriers are carried "
                                  "over from rev12."),
                     needed_to_unblock=("Formulation owner lands the two carrier edits (either verified "
                                        "candidate closes both), re-freezes as a new revision, and one "
                                        "re-review round binds to the new hash. Any repair voids all "
                                        "verdicts bound to b2ab6acb, including this ledger."),
                     evidence_refs=ev_refs + ["schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe"],
                     not_claimed=NOT_CLAIMED))

    events.append(ev(f"{prefix}-status", "status", status="active", hours=0.5,
                     node_id=NODE, gate=GATE, class_ids=CLASSES,
                     summary=("W054-F2B-REV29-UNION-LEDGER-01 complete at worker level (one bounded "
                              "class-bound task self-selected; no card existed for worker-054; not a node "
                              "done and not a gate verdict). Union ledger at F2b b2ab6acb2bbe / FROZEN "
                              "rev29 815e08079aef: 8/8 reported claims reproduced, 10/10 controls, 0 drift; "
                              "2 operative binding-text carriers (:152, :246), 1 alias-resolved "
                              "non-blocking, 4 hygiene, 1 instrument blind spot. Both available candidate "
                              "repairs verified to close both carriers without gate regression; none "
                              "adopted. Checkpoint at runtime/state/checkpoints/w054-f2b-rev29-union-ledger.json."),
                     next_falsifier=rep["next_falsifier"],
                     evidence_refs=ev_refs, not_claimed=NOT_CLAIMED))

    existing = set()
    if OUTBOX.exists():
        for ln in OUTBOX.read_text(encoding="utf-8").splitlines():
            ln = ln.strip()
            if ln.startswith("{"):
                try:
                    existing.add(json.loads(ln).get("event_id"))
                except Exception:
                    pass
    new = [e for e in events if e["event_id"] not in existing]
    with open(OUTBOX, "a", encoding="utf-8") as fh:
        for e in new:
            fh.write(json.dumps(e, sort_keys=True) + "\n")
    print(json.dumps({"appended": len(new), "skipped_existing": len(events) - len(new),
                      "outbox": str(OUTBOX)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
