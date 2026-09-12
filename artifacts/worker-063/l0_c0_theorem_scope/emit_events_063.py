#!/usr/bin/env python3
"""Emit W063-L0-C0-THEOREM-01 events + worker-local checkpoint (idempotent by event_id).

Writes:
  artifacts/worker-063/l0_c0_theorem_scope/entry_hashes.json
  comms/outbox/worker-063.jsonl                (append; skips existing event_ids)
  runtime/state/worker-063_l0_c0_theorem_checkpoint.json
  runtime/state/w063_checkpoints.jsonl         (append)
No canonical / frozen file is written.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]
DIR = pathlib.Path(__file__).resolve().parent
TASK = "W063-L0-C0-THEOREM-01"
ACTOR = "worker-063"
NODE = "L0"
GATE = "G-LIT"
CLASS_IDS = ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"]
NOW = datetime.datetime.now().astimezone().replace(microsecond=0)
TS = NOW.isoformat()
STAMP = NOW.strftime("%Y%m%dT%H%M%S")
CKPT_ID = f"w063-ckpt-{STAMP}"
OUTBOX = ROOT / "comms/outbox/worker-063.jsonl"


def sha256_file(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


report = json.loads((DIR / "report.json").read_text(encoding="utf-8"))
hashes = {
    str(p.relative_to(ROOT)): sha256_file(p)
    for p in sorted(DIR.iterdir())
    if p.is_file() and p.name != "entry_hashes.json"
}
(DIR / "entry_hashes.json").write_text(
    json.dumps({"task_id": TASK, "actor": ACTOR, "created_at": TS, "sha256": hashes}, indent=1)
    + "\n",
    encoding="utf-8",
)

rep_ref = f"artifacts/worker-063/l0_c0_theorem_scope/report.json#{hashes['artifacts/worker-063/l0_c0_theorem_scope/report.json'][:12]}"
readme_ref = f"artifacts/worker-063/l0_c0_theorem_scope/README.md#{hashes['artifacts/worker-063/l0_c0_theorem_scope/README.md'][:12]}"
script_ref = f"artifacts/worker-063/l0_c0_theorem_scope/run_l0_c0_theorem_063.py#{hashes['artifacts/worker-063/l0_c0_theorem_scope/run_l0_c0_theorem_063.py'][:12]}"

evidence = [
    "ledger/theorems.jsonl#a1674f094979",
    "evaluation_rubric.yaml#d748a9e3574e",
    "ledger/citation_audit.csv#315c19145065",
    "artifacts/audit/audit_lib.py#ae573db84631",
    "artifacts/audit/audit_run.py#3b27dd3fef7f",
    "research_map/class_separation.py#a8c04fc31e4a",
    "comms/outbox/astra-lead-literature.jsonl#lit-l7-20260912-004",
    rep_ref,
]

falsifier = (
    "Re-run artifacts/worker-063/l0_c0_theorem_scope/run_l0_c0_theorem_063.py at the pinned "
    "hashes: falsified if any pinned input drifts; if the C0-bound row census or the three "
    "theorem rows {T-302,T-303,T-526} change; if any canonical module flags the three rows for "
    "the C0-status pattern; if any control M1-M8 stops reproducing; or if the two core runs differ."
)

events = [
    {
        "event_id": f"w063-l0c0-{STAMP}-artifact-report",
        "event_type": "artifact",
        "created_at": TS,
        "actor": ACTOR,
        "node_id": NODE,
        "gate": GATE,
        "class_id": CLASS_IDS[0],
        "class_ids": CLASS_IDS,
        "artifact_type": "scope_adjudication_input",
        "path": "artifacts/worker-063/l0_c0_theorem_scope/report.json",
        "sha256": hashes["artifacts/worker-063/l0_c0_theorem_scope/report.json"],
        "validation_status": "unverified",
        "artifact_refs": [readme_ref, script_ref],
        "evidence_refs": evidence,
        "note": (
            "Independent read-only measurement of the C0 status_risk clause vs the three "
            "conclusion_type=theorem rows at L0 a1674f094979. Status MEASURED, determinism "
            "digest e77521c41eec, 8/8 controls, zero pin drift. No gate verdict, no node status, "
            "no class-binding repair."
        ),
        "falsifier": falsifier,
    },
    {
        "event_id": f"w063-l0c0-{STAMP}-status",
        "event_type": "status",
        "created_at": TS,
        "actor": ACTOR,
        "node_id": NODE,
        "gate": GATE,
        "class_id": CLASS_IDS[0],
        "class_ids": CLASS_IDS,
        "status": "active",
        "hours": 0.35,
        "summary": (
            "W063-L0-C0-THEOREM-01 delivered unverified: one class-bound bounded task (L0 / "
            "G-LIT+G-AUDIT) covering the new clause of lit-l7-20260912-004. C02: 11 C0-bound rows, "
            "exactly {T-302,T-303,T-526} typed theorem. C04: canonical stack routes 62/62 ledger "
            "rows to records (0 claims), check_self_certification=0, class_separation flags none of "
            "the three rows and 0 for the whole ledger text -> the finding is not produced by "
            "canonical tooling. C05: zero explicit class-status fields exist. C06: clause condition "
            "'until L1 binds the exact hypotheses' is unresolved (T-301 unresolved; SRC-097 "
            "unresolved). Six decision inputs D1-D6 recorded; no ruling. Live movement recorded: "
            "research_map/class_separation.py c266dbceca87 -> a8c04fc31e4a at 00:52:00."
        ),
        "evidence_refs": evidence,
        "next_falsifier": falsifier,
    },
    {
        "event_id": f"w063-l0c0-{STAMP}-blocker",
        "event_type": "blocker",
        "created_at": TS,
        "actor": ACTOR,
        "node_id": NODE,
        "gate": GATE,
        "class_id": CLASS_IDS[0],
        "class_ids": CLASS_IDS,
        "description": (
            "L0 needs an A0/controller owner ruling on whether the AF-SCC-C0-VAC-GEN status_risk "
            "clause (evaluation_rubric.yaml:100-104) constrains per-row conclusion_type or only an "
            "explicit class-status record. Measured split: D1 field-literal fires HF-02 on 3 rows; "
            "D2 row-vs-class finds no class-status record in the ledger at all (0 rows carry any "
            "class-status field); D3 canonical tooling produces 0 findings for the pattern and "
            "routes ledger rows to records, never claims; D4 HF-02's 'conclusion_type not allowed "
            "for class' has no machine-readable per-class denylist. The clause's own antecedent "
            "('until L1 binds the exact hypotheses') is unresolved at the pinned L1 hash. Either "
            "ruling moves the L0 accept path: D1 means a hash-moving content repair, D2 means the "
            "three rows are not the blocker and G-LIT should be adjudicated on the remaining items."
        ),
        "needed_to_unblock": (
            "A0/controller scope ruling (D1 vs D2) at the pinned hashes, plus a machine-readable "
            "allowed/forbidden conclusion_type list per frozen class if D1 is adopted. Do not "
            "patch the ledger to make a detector green; a class_ids/conclusion_type repair moves "
            "the ledger hash and voids all current L0 verdicts."
        ),
        "evidence_refs": evidence,
        "falsifier": (
            "A canonical-tooling run at the pinned hashes that does flag the three rows; a ledger "
            "revision where the three rows are no longer theorem-typed; or an L1 binding of the "
            "Dafermos-Luk exact hypotheses that discharges the clause antecedent."
        ),
    },
]

existing = set()
if OUTBOX.exists():
    for line in OUTBOX.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            existing.add(json.loads(line).get("event_id"))
        except json.JSONDecodeError:
            pass
new = [e for e in events if e["event_id"] not in existing]
with OUTBOX.open("a", encoding="utf-8") as fh:
    for e in new:
        fh.write(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n")

map_sha = sha256_file(ROOT / "research_map/research_map.json")
checkpoint = {
    "actor": ACTOR,
    "worker": ACTOR,
    "task_id": TASK,
    "checkpoint_id": CKPT_ID,
    "created_at": TS,
    "node_id": NODE,
    "gate": GATE,
    "class_ids": CLASS_IDS,
    "assignment_received": False,
    "assignment_ref": (
        "lit-l7-20260912-004 open queue item (astra-lead-literature); no card in "
        "comms/inbox for worker-063"
    ),
    "artifact_hashes": hashes,
    "checks": (
        "MEASURED; determinism digest e77521c41eec; 8/8 mutation controls; zero pin drift "
        "(6 pins before==after); C02 11 C0 rows / {T-302,T-303,T-526} theorem; C04 canonical "
        "tooling 0 findings; C05 0 class-status fields; C06 clause antecedent unresolved"
    ),
    "result": (
        "scope_adjudication_input delivered unverified: six decision inputs D1-D6 for the C0 "
        "status_risk vs conclusion_type question; no gate verdict, no node status, no repair"
    ),
    "next_falsifier": falsifier,
    "events": [e["event_id"] for e in events],
    "outbox": "comms/outbox/worker-063.jsonl",
    "map_sha256_measured_at_checkpoint": map_sha,
    "global_checkpoint_untouched": True,
    "exit_code": 0,
}
(ROOT / "runtime/state/worker-063_l0_c0_theorem_checkpoint.json").write_text(
    json.dumps(checkpoint, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
)
with (ROOT / "runtime/state/w063_checkpoints.jsonl").open("a", encoding="utf-8") as fh:
    fh.write(json.dumps(checkpoint, ensure_ascii=False, sort_keys=True) + "\n")

print(json.dumps({
    "events_appended": [e["event_id"] for e in new],
    "events_skipped_existing": [e["event_id"] for e in events if e not in new],
    "entry_hashes": hashes,
    "checkpoint": "runtime/state/worker-063_l0_c0_theorem_checkpoint.json",
    "map_sha256": map_sha,
}, indent=1))
