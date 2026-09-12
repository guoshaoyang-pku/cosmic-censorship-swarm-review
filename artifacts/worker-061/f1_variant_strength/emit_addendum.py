#!/usr/bin/env python3
"""Append the W061-F1-VARSTRENGTH-05 addendum events (post-repair drift recheck)."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, ROOT)
from research_map.schemas import validate_event  # noqa: E402

CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")
TAG = "w061-varstrength-20260912T0055"
A = "artifacts/worker-061/f1_variant_strength"


def sha256(rel: str) -> str:
    h = hashlib.sha256()
    with open(os.path.join(ROOT, rel), "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


H = {k: sha256(f"{A}/{k}") for k in ("post_repair_recheck.py", "post_repair_recheck.json")}
R = json.load(open(os.path.join(ROOT, f"{A}/post_repair_recheck.json"), encoding="utf-8"))

EV = [
    {
        "event_id": f"{TAG}-addendum-artifact-recheck-script",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-061",
        "task_id": "W061-F1-VARSTRENGTH-05",
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "artifact_type": "addendum_probe_script",
        "path": f"{A}/post_repair_recheck.py",
        "sha256": H["post_repair_recheck.py"],
        "validation_status": "unverified",
        "note": "Targeted post-repair wording recheck. Locally patches the direction parser to take the FIRST direction token, because the rev13 line quotes the superseded token in its revision bracket; the rev12 pinned readings are unaffected (single-token lines). Not a review verdict at the new bytes.",
    },
    {
        "event_id": f"{TAG}-addendum-artifact-recheck-output",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-061",
        "task_id": "W061-F1-VARSTRENGTH-05",
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "artifact_type": "machine_probe_output",
        "path": f"{A}/post_repair_recheck.json",
        "sha256": H["post_repair_recheck.json"],
        "validation_status": "unverified",
        "note": "Measured drift: F1 cce9c60146d6 -> d9cebb9404b2, F2b 55d0a1ea9bda -> b2ab6acb2bbe, FROZEN 2f358f6722d9 -> e1a8aaa394eb (rev29); registry 5eb42f9a384a and both deltas unchanged.",
    },
    {
        "event_id": f"{TAG}-addendum-status",
        "event_type": "status",
        "created_at": NOW,
        "actor": "worker-061",
        "task_id": "W061-F1-VARSTRENGTH-05",
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "status": "active",
        "hours": 0.2,
        "summary": (
            "ADDENDUM (drift, not a new verdict). astra-life05-evidence-binding-repair landed mid-task: F1 "
            "cce9c60146d6 -> d9cebb9404b2 (rev13), F2b 55d0a1ea9bda -> b2ab6acb2bbe, FROZEN -> e1a8aaa394eb "
            "(rev29) at 00:53:20-00:54:39; registry and both deltas unchanged. The original claim/review bind "
            "only to the rev12 pins. Targeted recheck with the same semantics: HF-W061-VAR-01 is REPAIRED at "
            "the new F1 bytes (variant SET relation now 'strictly WEAKER', with tail=>union and the omega-chain "
            "separation in the rationale, exactly the predicate-level correction the probe derived); "
            "HF-W061-VAR-02 PERSISTS because the SET delta is byte-unchanged and still says the predicate 'is "
            "implied by, and strictly stronger than' the tail predicate - this matches the lead's residual "
            "blocker L-FORM-03 (registry:57, delta:11,22, F0 taxonomy:200, D1 ledger:176); F-W061-VAR-03 (CH "
            "soft pronoun/conditionality wording) also persists at the unchanged F2b:292 text. The recheck is "
            "not a review verdict at the new bytes and does not bind the pass-05 r3 blind round."
        ),
        "evidence_refs": [
            f"{A}/post_repair_recheck.json#sha256:{H['post_repair_recheck.json'][:12]}",
            f"{A}/post_repair_recheck.py#sha256:{H['post_repair_recheck.py'][:12]}",
            "schemas/af_wcc_vacuum.yaml#sha256:d9cebb9404b2",
            "schemas/af_scc_c0_vacuum.yaml#sha256:b2ab6acb2bbe",
            "artifacts/formulation/FROZEN.json#sha256:e1a8aaa394eb",
            "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json#sha256:45b9b6a8d192",
            "artifacts/formulation/VARIANT_REGISTRY.json#sha256:5eb42f9a384a",
        ],
        "next_falsifier": "Re-measure the six live hashes and re-run post_repair_recheck.py: the addendum is falsified if the SET delta is repaired (contradiction cleared) or if the F1 rev13 label is changed away from 'strictly WEAKER' without an explicit two-level statement. Any further F1/F2b/registry/delta byte change requires a fresh pin.",
    },
]

for e in EV:
    validate_event(e)
with open(os.path.join(ROOT, "comms/outbox/worker-061.jsonl"), "a", encoding="utf-8") as f:
    for e in EV:
        f.write(json.dumps(e, ensure_ascii=False) + "\n")
print(json.dumps({"appended": len(EV), "recheck_sha256": H["post_repair_recheck.json"],
                  "now": NOW}, indent=1))
