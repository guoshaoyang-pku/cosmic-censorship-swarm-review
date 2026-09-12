#!/usr/bin/env python3
"""Emit the W100-GLIT-UNIVERSE-REPL-01 upward events (validated, then appended).

Validates every event against research_map/schemas.py before writing. Appends to
comms/outbox/worker-100.jsonl; does not ingest (controller command).
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event, SchemaError  # noqa: E402

TASK = ROOT / "artifacts/worker-100/glit_universe_replication"
CKPT = ROOT / "runtime/state/w100_glit_universe_replication_checkpoint.json"
OUTBOX = ROOT / "comms/outbox/worker-100.jsonl"
TARGET = "artifacts/worker-075/source_meta_census/source_meta_census_075.json"
AT = "2026-09-12T01:22:40+08:00"
CLASS_ID = "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH"
TASK_ID = "W100-GLIT-UNIVERSE-REPL-01"


def h12(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


report = json.loads((TASK / "replication_report.json").read_text())
d = report["measurement_digest"]
D = {
    "prereg": TASK / "PREREGISTRATION.json",
    "instrument": TASK / "replicate_census_100.py",
    "report": TASK / "replication_report.json",
    "md": TASK / "REPLICATION.md",
    "pins": TASK / "raw/inputs_hashes_t0.json",
    "pins_t1": TASK / "raw/inputs_hashes_t1.json",
}

ev = []
ev.append({
    "event_id": "w100-glitrepl-20260912T0122-status-complete",
    "event_type": "status", "created_at": AT, "actor": "worker-100",
    "node_id": "L1", "gate": "G-LIT", "class_id": CLASS_ID, "task_id": TASK_ID,
    "status": "active", "hours": 0.6,
    "summary": ("W100-GLIT-UNIVERSE-REPL-01 complete at worker level (bounded execution worker; "
                "no node transition, no gate verdict, no validation_status=passed). Independent "
                "non-author replication of worker-075's source-meta census at 43/43 byte-stable "
                "pins: 9/9 headline universes reproduce (151 unique sources / 77 unique theorems / "
                "228 union / 388 class rows / 726 raw links / 183 unique link pairs), 0 records "
                "carry any of the five source_meta axes under depth<=2 and depth<=1, and the "
                "'201 citations' figure is not the size of any measured universe (named "
                "decompositions reproduce at 104 and 189 distinct ids; closest measured universe "
                "183). Per-class split reproduces exactly under the target's exact-';'-token rule "
                "(67/58/18/26/337) and differs under a substring reading only on qualified/negated "
                "tokens; 13/13 controls pass; deterministic --verify re-run identical. Verdict "
                "PARTIAL under the pre-registered rule, with no contradiction of the target found. "
                "Checkpoint runtime/state/w100_glit_universe_replication_checkpoint.json; exiting."),
    "evidence_refs": [f"{TASK.relative_to(ROOT)}/replication_report.json#sha256:{h12(D['report'])}",
                      f"{TASK.relative_to(ROOT)}/REPLICATION.md#sha256:{h12(D['md'])}",
                      f"{CKPT.relative_to(ROOT)}#sha256:{h12(CKPT)}",
                      f"{TARGET}#sha256:b816178b94f7"],
    "next_falsifier": report["next_falsifier"] if "next_falsifier" in report else (
        "Re-run replicate_census_100.py and --verify at the same tree state: falsified if any of the "
        "43 inputs re-hashes differently at T0/T1, any headline/per-class-B/record-kind value "
        "changes, any control flips, or an axis-free record is shown to carry a literal axis key "
        "within nested-dict depth <= 2 (or <= 1)."),
})

for key, eid, atype in [
    ("prereg", "w100-glitrepl-20260912T0122-artifact-prereg", "preregistration"),
    ("instrument", "w100-glitrepl-20260912T0122-artifact-instrument", "replication_instrument"),
    ("report", "w100-glitrepl-20260912T0122-artifact-report", "replication_report"),
    ("md", "w100-glitrepl-20260912T0122-artifact-replication-md", "replication_summary"),
    ("pins", "w100-glitrepl-20260912T0122-artifact-pins", "input_pin_manifest"),
]:
    p = D[key]
    ev.append({
        "event_id": eid, "event_type": "artifact", "created_at": AT, "actor": "worker-100",
        "node_id": "L1", "gate": "G-LIT", "class_id": CLASS_ID, "task_id": TASK_ID,
        "artifact_type": atype, "path": str(p.relative_to(ROOT)), "sha256": sha(p),
        "validation_status": "unverified",
        "evidence_refs": [f"{TARGET}#sha256:b816178b94f7",
                          f"ledger/theorems.jsonl#sha256:a1674f094979",
                          f"ledger/citation_audit.csv#sha256:315c19145065"],
    })

ev.append({
    "event_id": "w100-glitrepl-20260912T0122-claim-replication",
    "event_type": "claim", "created_at": AT, "actor": "worker-100",
    "node_id": "L1", "gate": "G-LIT", "class_id": CLASS_ID, "task_id": TASK_ID,
    "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
    "statement": (f"Artifact-and-instrument replication (not a mathematics claim), at 43/43 "
                  f"byte-stable pins: worker-075's recorded universes reproduce independently -- "
                  f"151 unique sources, 77 unique theorems, 228 union, 388 class rows, 726 raw "
                  f"citation links, 183 unique (theorem,source) pairs; 0/450, 0/151, 0/297, 0/77, "
                  f"0/747, 0/228 and 0/388 records carry any of matter_model, cosmological_constant, "
                  f"dimension, symmetry, formulation (depth<=2 and depth<=1 readings both zero); "
                  f"'201' equals no measured universe (named decompositions: 97+97+7=201 at 104 "
                  f"distinct ids; 97+62+12+15+15=201 at 189 distinct ids); the per-class split "
                  f"67/58/18/26/337 reproduces under exact-';'-token reading and 76/67/24/26/316 "
                  f"under a substring reading. Measurement digest {d}; 13/13 controls; "
                  f"deterministic re-run identical."),
    "conclusion_type": "formal_model",
    "assumptions": [
        "the 43 files recorded in the target's input_files are the full census surface at the pins",
        "axis-present = literal key at top level or nested dict depth <= 2 (strict depth<=1 reported as sensitivity)",
        "the target's implementation was not read or imported; both readings of the class-token rule are reported",
        "counts bind the recorded sha256 snapshot only; any later ledger move voids them until re-run",
        "worker cannot set done/passed/gate verdicts; G-LIT denominator choice is the gate owner's",
    ],
    "falsifier": ("Re-run artifacts/worker-100/glit_universe_replication/replicate_census_100.py at the "
                  "pinned tree state; falsified if any of the 43 inputs differs from its recorded "
                  "sha256, any listed universe or per-axis zero fails to reproduce, any control flips, "
                  "or a record counted as axis-free carries a literal axis key within depth <= 2 (or <= 1)."),
    "evidence_refs": [f"{TASK.relative_to(ROOT)}/replication_report.json#sha256:{h12(D['report'])}",
                      f"{TASK.relative_to(ROOT)}/PREREGISTRATION.json#sha256:{h12(D['prereg'])}",
                      f"{TASK.relative_to(ROOT)}/replicate_census_100.py#sha256:{h12(D['instrument'])}",
                      f"{TASK.relative_to(ROOT)}/raw/inputs_hashes_t0.json#sha256:{h12(D['pins'])}",
                      f"{TARGET}#sha256:b816178b94f7",
                      f"ledger/theorems.jsonl#sha256:a1674f094979",
                      f"ledger/citation_audit.csv#sha256:315c19145065",
                      f"ledger/class_coverage.csv#sha256:abbaee54a5a3"],
    "artifact_refs": [f"{TASK.relative_to(ROOT)}/replication_report.json#sha256:{h12(D['report'])}"],
    "does_not_claim": ["gate verdict", "node completion", "mathematics or physics claim",
                       "that the ledger content is correct", "adoption of any locator or class repair"],
})

ev.append({
    "event_id": "w100-glitrepl-20260912T0122-review-census",
    "event_type": "review", "created_at": AT, "actor": "worker-100",
    "node_id": "L1", "gate": "G-LIT", "class_id": CLASS_ID, "task_id": TASK_ID,
    "target_id": f"{TARGET}#sha256:b816178b94f7",
    "reviewer": "worker-100", "verdict": "accept", "score": 4.5,
    "reviewed_sha256": sha(ROOT / TARGET),
    "counts_as_gate_verdict": False, "counts_as_full_schema_verdict": False,
    "hard_failures": [],
    "findings": [
        "REPLICATED: all nine headline universes (450/151/297/77/747/228/388/726) reproduce exactly; per-file record-kind classification agrees on 43/43 files; 0-axis result holds under depth<=2 and depth<=1.",
        "CONFIRMED: '201 citations' is not the size of any measured universe; the two named decompositions reproduce (104 and 189 distinct record ids) and the closest measured universe is 183 unique pairs (18 away).",
        "F-W100-REPL-01 (info, scope): the recorded per-class U1 counts (67/58/18/26/337) reproduce only under an exact-';'-token rule; a substring reading gives 76/67/24/26/316 because qualified assignments such as 'AF-SCC-C0-VAC-GEN (definitional support)' are credited. No headline or 0-axis result depends on this; README documents the axis rule but not the class-token rule.",
        "Recommended gate-text denominators at these pins: 151 unique sources / 77 unique theorems / 228 union / 388 class rows / 726 raw links / 183 unique links; '201' should not be used as a denominator.",
        "Independent non-author: worker-100 is not an author of the target, the ledger, the registry or the protocol; target implementation not read before this worker's implementation was written.",
    ],
    "evidence_refs": [f"{TASK.relative_to(ROOT)}/replication_report.json#sha256:{h12(D['report'])}",
                      f"{TASK.relative_to(ROOT)}/REPLICATION.md#sha256:{h12(D['md'])}",
                      f"{TASK.relative_to(ROOT)}/replicate_census_100.py#sha256:{h12(D['instrument'])}",
                      f"{CKPT.relative_to(ROOT)}#sha256:{h12(CKPT)}"],
    "next_falsifier": ("Falsified by a re-run at the same pins yielding different universe counts, by a "
                       "record with a literal axis key at depth <= 2 (or <= 1) counted as axis-free, or by "
                       "a target re-issue whose bytes differ from b816178b94f7."),
})

for e in ev:
    try:
        validate_event(e)
    except SchemaError as exc:
        print(json.dumps({"invalid": e["event_id"], "reason": str(exc)}))
        sys.exit(1)

with open(OUTBOX, "a", encoding="utf-8") as f:
    for e in ev:
        f.write(json.dumps(e, ensure_ascii=False) + "\n")
print(json.dumps({"appended": [e["event_id"] for e in ev],
                  "outbox": str(OUTBOX.relative_to(ROOT)),
                  "checkpoint_sha256": sha(CKPT)}, indent=1))
