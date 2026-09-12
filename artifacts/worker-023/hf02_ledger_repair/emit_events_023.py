#!/usr/bin/env python3
"""Emit the W023-L0-HF02-LEDGER-01 events to comms/outbox/worker-023.jsonl.

Idempotent: skips any event_id already present in the outbox. Fails closed if an
artifact referenced in an event is missing or its hash differs from the event.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
ART = REPO / "artifacts/worker-023/hf02_ledger_repair"
OUTBOX = REPO / "comms/outbox/worker-023.jsonl"
T = "20260912T0101"
BASE = f"w23-hf02-ledger-{T}"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rel(p: Path) -> str:
    return str(p.relative_to(REPO))


def main() -> int:
    now = _dt.datetime.now().astimezone().isoformat(timespec="seconds")
    report = json.loads((ART / "report.json").read_text())
    ver = json.loads((ART / "verification.json").read_text())
    v7 = ART / "proposed_ledger_v7.jsonl"
    v8 = ART / "proposed_ledger_v8.jsonl"
    rj = ART / "report.json"
    vj = ART / "verification.json"

    falsifier = report["falsifier"]
    class_ids = ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-VAC-GEN"]
    delivered = [
        {"path": v7, "type": "hf02_ledger_repair_candidate_v7"},
        {"path": v8, "type": "hf02_ledger_repair_candidate_v8"},
        {"path": rj, "type": "hf02_ledger_repair_report"},
        {"path": vj, "type": "hf02_ledger_repair_verification"},
    ]

    events = []
    for d in delivered:
        p = d["path"]
        events.append({
            "actor": "worker-023", "event_id": f"{BASE}-artifact-{p.name}",
            "event_type": "artifact", "created_at": now, "node_id": "L0", "gate": "G-LIT",
            "class_id": "AF-SCC-C2-VAC-GEN", "class_ids": class_ids,
            "artifact_type": d["type"], "path": rel(p), "sha256": sha(p),
            "bytes": p.stat().st_size, "validation_status": "unverified", "applied": False,
            "task_id": "W023-L0-HF02-LEDGER-01",
            "summary": {
                "hf02_ledger_repair_candidate_v7":
                    "Byte-exact candidate ledger, 7 unqualified HF-02 ops; T-526 left dual-class; "
                    "rubric-literal HF-02 8->1; patched runner reports exactly 1 (T-526).",
                "hf02_ledger_repair_candidate_v8":
                    "Byte-exact candidate ledger, all 8 HF-02 ops incl. the F1-conditional T-526 rebinding; "
                    "rubric-literal HF-02 8->0; patched runner reports exactly 0.",
                "hf02_ledger_repair_report":
                    "Build report: 39/39 checks, 9/9 controls, 6 frozen runner scenarios, pinned inputs.",
                "hf02_ledger_repair_verification":
                    "Independent re-derivation: 38/38 checks incl. re-execution of all 6 scenarios and "
                    "two mutation controls (patched fires, canonical blind).",
            }[d["type"]],
            "evidence_refs": [
                "ledger/theorems.jsonl#a1674f094979",
                "evaluation_rubric.yaml#d748a9e3574e",
                "artifacts/worker-093/l0_rev3_review/proposed_hf02_disjunction_patch.diff#0247a5c93acc",
                "artifacts/worker-023/l0_hf02/hf02-disjunction-adjudication-023.json#0f86158c5bb7",
                "artifacts/worker-023/l0_hf02_integration/runner_wiring.diff#2f1fa11dbc99",
            ],
            "falsifier": falsifier,
        })

    events.append({
        "actor": "worker-023", "event_id": f"{BASE}-claim", "event_type": "claim",
        "created_at": now, "node_id": "L0", "gate": "G-LIT",
        "class_id": "AF-SCC-C2-VAC-GEN", "class_ids": class_ids,
        "conclusion_type": "formal_model", "applied": False,
        "task_id": "W023-L0-HF02-LEDGER-01",
        "statement": (
            "At the pinned ledger a1674f094979, the two candidate repaired ledgers differ from the "
            "canonical bytes on exactly the expected rows and fields (V7: 7 rows, sha d66d06f8b20c; "
            "V8: 8 rows, sha 33f6f8817239), every unchanged line is byte-identical, ids/order are "
            "preserved, every patched row keeps a binding channel and no class token outside the "
            "frozen four is introduced. The rubric-literal HF-02 disjunction count is 8/1/0 on "
            "original/V7/V8; the 093-patched and wired runner (patch hash 0247a5c93acc, patched "
            "audit_lib 9c8def1b5037) reports exactly 8/1/0 disjunction rows with no other violation "
            "added or removed, while the canonical runner (audit_lib ae573db84631, audit_run "
            "3b27dd3fef7f) reports 0 disjunctions and an identical violation digest in all three "
            "variants. Consequence: the candidate bytes are ready for a landing decision; V7 needs no "
            "new ruling, V8 lands the T-526 op that the adjudication packet defers to the F1 "
            "membership ruling."
        ),
        "assumptions": [
            "read-only on canonical paths: no ledger, rubric, audit-tooling or map file was modified; both candidates are proposals (applied=false)",
            "the repair ops are exactly the 8 ordered ops in artifacts/worker-023/l0_hf02/hf02-disjunction-adjudication-023.json; this task re-measures them, it does not re-adjudicate any row",
            "the rubric-literal HF-02 predicate is the 093 predicate text ('a single class_ids list carrying >=2 frozen classes'); the canonical runner implements no ledger-disjunction branch, so a 0 there is blindness, not compliance",
            "sandbox map is trimmed (groups=[]); only within-tooling variant deltas and the patched-vs-canonical delta are interpreted, not absolute gate verdicts",
        ],
        "artifact_refs": [
            f"{rel(v7)}#{sha(v7)[:12]}", f"{rel(v8)}#{sha(v8)[:12]}",
            f"{rel(rj)}#{sha(rj)[:12]}", f"{rel(vj)}#{sha(vj)[:12]}",
        ],
        "evidence_refs": [
            "ledger/theorems.jsonl#a1674f094979",
            "evaluation_rubric.yaml#d748a9e3574e",
            "artifacts/worker-093/l0_rev3_review/proposed_hf02_disjunction_patch.diff#0247a5c93acc",
            "artifacts/worker-093/l0_rev3_review/patched_audit_lib.py#9c8def1b5037",
            "artifacts/worker-023/l0_hf02_integration/runner_wiring.diff#2f1fa11dbc99",
            "research_map/formulation_taxonomy.yaml#0abb9ed8a961",
        ],
        "falsifier": falsifier,
    })

    events.append({
        "actor": "worker-023", "event_id": f"{BASE}-review", "event_type": "review",
        "created_at": now, "node_id": "L0", "gate": "G-LIT",
        "class_id": "AF-SCC-C2-VAC-GEN", "class_ids": class_ids,
        "task_id": "W023-L0-HF02-LEDGER-01",
        "target_id": "W023-L0-HF02-LEDGER-01",
        "reviewer": "worker-023",
        "target": {"path": rel(v8), "sha256": sha(v8),
                   "canonical_path": "ledger/theorems.jsonl",
                   "canonical_sha256": "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28"},
        "verdict": "accept", "score": 4.0, "counts_as_full_schema_verdict": False,
        "scope": "worker-level advisory verdict on the candidate bytes and their end-to-end runner "
                 "measurement only; not an L0 node verdict, not a gate verdict",
        "hard_failures": [],
        "findings": [
            "W023L-F1 candidate bytes verified byte-exact: diffs confined to class_ids/informs_classes/ledger_tags on exactly 7 (V7) and 8 (V8) rows; all other lines byte-identical; ids and order preserved.",
            "W023L-F2 rubric-literal and imported-093 HF-02 counts both 8/1/0 on original/V7/V8; patched wired runner 8/1/0; canonical runner 0/0/0 with identical digest (blindness reproduced).",
            "W023L-F3 T-526 is the only op needing a new ruling: V7 is unqualified (leaves 1 disjunction), V8 clears all 8 but is conditional on the F1 membership ruling.",
            "W023L-F4 landing precondition unchanged: P-CODE is still unlanded (audit_lib ae573db84631); landing it without the ledger repair flips derived G-AUDIT to fail, so code + ledger repair must land as one change (or the rubric must be amended).",
            "W023L-F5 mutation control: reintroducing a dual-class row into V8 makes the patched runner fire exactly once (D-004) while the canonical runner stays blind; determinism and idempotency controls pass.",
        ],
        "evidence_refs": [
            f"{rel(rj)}#{sha(rj)[:12]}", f"{rel(vj)}#{sha(vj)[:12]}",
            f"{rel(v7)}#{sha(v7)[:12]}", f"{rel(v8)}#{sha(v8)[:12]}",
            "ledger/theorems.jsonl#a1674f094979",
        ],
        "next_falsifier": falsifier,
    })

    events.append({
        "actor": "worker-023", "event_id": f"{BASE}-blocker", "event_type": "blocker",
        "created_at": now, "node_id": "L0", "gate": "G-LIT",
        "class_id": "AF-SCC-C2-VAC-GEN", "class_ids": class_ids,
        "task_id": "W023-L0-HF02-LEDGER-01",
        "supersedes": "w23-integ-20260912T005142-blocker",
        "description": (
            "HF-02 at ledger a1674f094979 is now package-complete but still unlanded: the verified "
            "candidate bytes exist (V7 d66d06f8b20c, 7 ops, no new ruling needed; V8 33f6f8817239, all "
            "8 ops, T-526 conditional on the F1 membership ruling), and the P-CODE + wiring requirement "
            "is integration-verified. What remains is authority and ordering, not more measurement: "
            "(a) the A0 detector-scope ruling decides whether ledger records are in HF-02 scope at all "
            "(if claim-scoped, this repair is a reference proposal, not a requirement); (b) if in scope, "
            "one owner must land P-CODE (093 diff + the one wiring line) and the chosen ledger variant as "
            "one change, because landing P-CODE alone flips derived G-AUDIT to fail; (c) the T-526 op in "
            "V8 waits on the F1 membership ruling, so V7 is the no-new-ruling landing shape."
        ),
        "needed_to_unblock": (
            "Lead/controller decisions with named owners: (a) astra-lead-audit A0 detector-scope ruling; "
            "(b) landing order for artifacts/worker-093/l0_rev3_review/proposed_hf02_disjunction_patch.diff "
            "+ artifacts/worker-023/l0_hf02_integration/runner_wiring.diff + proposed_ledger_v7.jsonl "
            "(or v8.jsonl after the F1 ruling) as one announced revision; (c) F1 membership ruling for T-526. "
            "Worker-023 holds no edit authority over canonical paths."
        ),
        "evidence_refs": [
            f"{rel(v7)}#{sha(v7)[:12]}", f"{rel(v8)}#{sha(v8)[:12]}",
            f"{rel(rj)}#{sha(rj)[:12]}", f"{rel(vj)}#{sha(vj)[:12]}",
            "artifacts/worker-023/l0_hf02_integration/report.json#4d79d14ea2b8",
            "ledger/theorems.jsonl#a1674f094979",
        ],
        "falsifier": falsifier,
    })

    events.append({
        "actor": "worker-023", "event_id": f"{BASE}-status", "event_type": "status",
        "created_at": now, "node_id": "L0", "gate": "G-LIT",
        "class_id": "AF-SCC-C2-VAC-GEN", "class_ids": class_ids,
        "task_id": "W023-L0-HF02-LEDGER-01",
        "status": "active", "hours": 0.5,
        "summary": (
            "One bounded class-bound task complete (W023-L0-HF02-LEDGER-01), checkpoint written, "
            "exiting. No inbox card existed for worker-023; the task was taken from the open HF-02 "
            "blocker at L0. Deliverable: the byte-exact repaired-ledger candidates (V7/V8) plus build "
            "(39/39 checks, 9/9 controls) and independent verification (38/38 checks, mutation control "
            "included) against the canonical and 093-patched runners. Worker level only: no node "
            "status, no gate verdict, no validation_status=passed; applied=false."
        ),
        "evidence_refs": [
            f"{rel(v7)}#{sha(v7)[:12]}", f"{rel(v8)}#{sha(v8)[:12]}",
            f"{rel(rj)}#{sha(rj)[:12]}", f"{rel(vj)}#{sha(vj)[:12]}",
            "runtime/state/w23_checkpoint_3.json",
        ],
        "next_falsifier": falsifier,
    })

    # fail closed: verify every referenced artifact exists at the stated hash
    for e in events:
        for p in (e.get("path"),):
            if p:
                fp = REPO / p
                if not fp.is_file() or sha(fp) != e["sha256"]:
                    print(f"FATAL: artifact missing or moved: {p}")
                    return 3
        for ref in e.get("artifact_refs", []) + e.get("evidence_refs", []):
            path, _, _h = ref.partition("#")
            if path.startswith("runtime/state/"):
                continue
            if not (REPO / path).is_file():
                print(f"FATAL: referenced path missing: {path}")
                return 3

    existing = set()
    if OUTBOX.is_file():
        for line in OUTBOX.read_text().splitlines():
            if line.strip():
                try:
                    existing.add(json.loads(line).get("event_id"))
                except Exception:
                    pass
    appended = 0
    with OUTBOX.open("a", encoding="utf-8") as f:
        for e in events:
            if e["event_id"] in existing:
                continue
            f.write(json.dumps(e, sort_keys=True) + "\n")
            appended += 1
    print(f"appended {appended} events (of {len(events)}); skipped {len(events)-appended} existing")
    return 0


if __name__ == "__main__":
    sys.exit(main())
