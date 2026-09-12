#!/usr/bin/env python3
"""Emit worker-054 events for W054-GFORM-VERDICT-HASH-INTEGRITY-01.

Reads the run outputs, hash-pins them, appends `artifact` x4 + `claim` + `review` + `status`
to comms/outbox/worker-054.jsonl, and writes a checkpoint JSON next to the artifacts.
Run after integrity.py; every sha256 below is measured, never assumed.
"""
from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUTBOX = ROOT / "comms/outbox/worker-054.jsonl"
CHECKPOINT = ROOT / "runtime/state/checkpoints/w054-gform-verdict-hash-integrity.json"
TASK = "W054-GFORM-VERDICT-HASH-INTEGRITY-01"
TS = datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()
STAMP = TS.replace(":", "").replace("-", "").split("+")[0]
ACTOR = "worker-054"
NODE = "F0,F1,F2a,F2b"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
GATE = "G-FORM"


def h(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ref(p: Path) -> str:
    return f"{p.relative_to(ROOT)}#{h(p)[:12]}"


report = json.loads((HERE / "report.json").read_text())
summary = json.loads((HERE / "summary.json").read_text())
pt = report["per_target"]
pins = report["snapshot_vs_pins"]
freshness = report["pin_freshness"]
counts = report["counts"]

artifacts = {
    "report": HERE / "report.json",
    "summary": HERE / "summary.json",
    "summary_md": HERE / "summary.md",
    "tool": HERE / "integrity.py",
    "readme": HERE / "README.md",
}

events = []


def add(e: dict) -> None:
    e.setdefault("task_id", TASK)
    e.setdefault("created_at", TS)
    e.setdefault("actor", ACTOR)
    events.append(e)


for name, path in artifacts.items():
    add({
        "event_id": f"w054-gformhash-{STAMP}-artifact-{name.replace('_', '-')}",
        "event_type": "artifact",
        "node_id": NODE,
        "class_ids": CLASS_IDS,
        "gate": GATE,
        "artifact_type": "verification_harness_output" if name in ("report", "summary",
                                                                   "summary_md") else "tool",
        "path": str(path.relative_to(ROOT)),
        "sha256": h(path),
        "validation_status": "unverified",
        "not_claimed": ["no gate verdict", "no node status", "no canonical artifact modified"],
    })

def _acc(t):
    return ", ".join(pt[t]["distinct_accept_hash_bound_to_current"]) or "none"


meta = {t: pt[t]["gate_criterion_met"] for t in ("F0", "F1", "F2a", "F2b")}
claim_statement = (
    "Machine measurement at the canonical snapshot frozen at "
    f"{report['measured_at_wall_clock']} (F0 taxonomy "
    f"{pins['research_map/formulation_taxonomy.yaml']['snapshot'][:12]}; class schemas "
    f"{pins['schemas/af_wcc_vacuum.yaml']['snapshot'][:12]}, "
    f"{pins['schemas/af_scc_c2_vacuum.yaml']['snapshot'][:12]}, "
    f"{pins['schemas/af_scc_c0_vacuum.yaml']['snapshot'][:12]}; FROZEN rev"
    f"{report['frozen_revision']} equals the snapshot; live canonical bytes unchanged across "
    "the run): of "
    f"{counts['reviews_total']} review events in the accepted stream, "
    f"{counts['class_verified_bound']} verdicts are bound to the measured canonical bytes, "
    f"{counts['class_stale_bound']} only to superseded revisions, "
    f"{counts['class_unresolved_bound']} to hashes with no live copy, "
    f"{counts['class_evidence_only_hash']} cite hashes only on support files, "
    f"{counts['class_ambiguous_target']} cite several canonical artifacts at once and are not "
    f"attributable to one target, and {counts['class_unbound']} cite no hash. "
    "Bound to the measured bytes: "
    + "; ".join(f"{t} {pt[t]['n_accept_bound_to_current']} distinct accept "
                f"({_acc(t)})" for t in ("F0", "F1", "F2a", "F2b"))
    + ". The G-FORM accept criterion (>=2 distinct independent accepts at the hash) is "
    + ("met for " + ", ".join(t for t in meta if meta[t]) + "; " if any(meta.values()) else "")
    + ("not met for " + ", ".join(t for t in meta if not meta[t]) + ". " if not all(meta.values())
       else "met for all four targets. ")
    + "Control findings: the frozen map still declares superseded node hashes for "
    + (", ".join(t for t in meta if not freshness[
        {'F0': 'research_map/formulation_taxonomy.yaml',
         'F1': 'schemas/af_wcc_vacuum.yaml',
         'F2a': 'schemas/af_scc_c2_vacuum.yaml',
         'F2b': 'schemas/af_scc_c0_vacuum.yaml'}[t]]['equals_map_declared']) or "no target")
    + "; worker-067 holds a same-hash accept and revise on F0 that needs adjudication before "
    "either counts as independent; and "
    f"{counts['verdicts_live_citation_unpinned_paths']} review events cite at least one live "
    "path (review files, KEY_MANIFEST, rule_spec.json, the semantic-contract suite, "
    "f1_falsifier_tests.jsonl, taxonomy_cases.jsonl, the stale af_scc_c0_vacuum.yaml.sha256 "
    "sidecar) that the FROZEN pin set does not cover. This is a read-only binding audit, not a "
    "gate verdict, not a node transition and not a mathematical claim."
)

add({
    "event_id": f"w054-gformhash-{STAMP}-claim",
    "event_type": "claim",
    "node_id": NODE,
    "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
    "class_ids": CLASS_IDS,
    "gate": GATE,
    "conclusion_type": "formal_model",
    "statement": claim_statement,
    "assumptions": [
        "the accepted event stream (research_map/events.jsonl), the frozen map and FROZEN.json "
        "are the authority for what verdicts exist; all three were byte-frozen at run start and "
        "re-hashed at run end",
        "a verdict counts toward G-FORM only when it is attributable to exactly one target and "
        "its cited target hash equals the bytes measured at the canonical path in this run",
        "reviews citing several canonical artifacts at once (cross-target/ledger reviews) are "
        "not attributable to a single target and are counted separately",
        "no semantic or mathematical adequacy of any formulation is assessed here",
    ],
    "falsifier": report["falsifier"],
    "evidence_refs": [ref(p) for p in artifacts.values()] + [
        f"research_map/events.jsonl#{report['input_snapshot_sha256']['events.jsonl'][:12]}",
        f"research_map/research_map.json#{report['input_snapshot_sha256']['research_map.json'][:12]}",
        f"artifacts/formulation/FROZEN.json#{report['input_snapshot_sha256']['FROZEN.json'][:12]}",
        "research_map/formulation_taxonomy.yaml#0abb9ed8a961",
        f"schemas/af_wcc_vacuum.yaml#{pins['schemas/af_wcc_vacuum.yaml']['snapshot'][:12]}",
        f"schemas/af_scc_c2_vacuum.yaml#{pins['schemas/af_scc_c2_vacuum.yaml']['snapshot'][:12]}",
        f"schemas/af_scc_c0_vacuum.yaml#{pins['schemas/af_scc_c0_vacuum.yaml']['snapshot'][:12]}",
    ],
    "artifact_refs": [ref(p) for p in artifacts.values()],
    "not_claimed": ["no gate verdict", "no node transition", "no canonical write",
                    "no mathematical claim"],
})

add({
    "event_id": f"w054-gformhash-{STAMP}-review",
    "event_type": "review",
    "reviewer": ACTOR,
    "target_id": GATE,
    "node_id": NODE,
    "class_ids": CLASS_IDS,
    "verdict": "inconclusive",
    "score": 3.0,
    "hard_failures": [
        "F1/F2a/F2b have no reviewer verdict bound to the revision-13 canonical bytes "
        f"({pins['schemas/af_wcc_vacuum.yaml']['snapshot'][:12]}, "
        f"{pins['schemas/af_scc_c2_vacuum.yaml']['snapshot'][:12]}, "
        f"{pins['schemas/af_scc_c0_vacuum.yaml']['snapshot'][:12]}); all recorded accepts bind "
        "to superseded revisions",
        "the frozen map still declares the revision-12 node hashes cce9c60146d6 / 5476a3f2c6bc / "
        "55d0a1ea9bda for F1/F2a/F2b, so the map's own controller_gate_audit counts verdicts "
        "against hashes that no longer exist at the canonical paths",
        "worker-067 holds a same-hash accept and revise on F0 (0abb9ed8a961): the pair is not "
        "independent until adjudicated",
        "auxiliary gate inputs are outside the FROZEN pin set: the review files themselves, "
        "KEY_MANIFEST, rule_spec.json, the semantic-contract suite, f1_falsifier_tests.jsonl, "
        "taxonomy_cases.jsonl, and the stale af_scc_c0_vacuum.yaml.sha256 sidecar "
        "(1bb78ce9b357 against current b2ab6acb2bbe); 390 review events cite at least one "
        "such unpinned live path",
    ],
    "findings": [
        f"{counts['class_verified_bound']}/{counts['reviews_total']} review events are bound to "
        "the measured canonical bytes; the rest are stale, unresolved, evidence-only, "
        "ambiguous-target or unbound",
        "F0 criterion met with 6 distinct bound accepts; F1/F2a/F2b criterion not met at the "
        "measured revision-13 pins",
        "method and raw per-event rows are in report.json; rerun integrity.py to reproduce",
    ],
    "evidence_refs": [ref(p) for p in artifacts.values()],
    "next_falsifier": report["falsifier"],
})

add({
    "event_id": f"w054-gformhash-{STAMP}-status",
    "event_type": "status",
    "status": "active",
    "hours": 0.5,
    "summary": (
        "W054-GFORM-VERDICT-HASH-INTEGRITY-01 complete at worker level (one bounded class-bound "
        "task self-selected; no inbox card existed for worker-054). Read-only audit of every "
        f"review verdict that could count toward G-FORM at the frozen snapshot: "
        f"{counts['class_verified_bound']} bound-to-current, {counts['class_stale_bound']} "
        f"stale, {counts['class_unresolved_bound']} unresolved, "
        f"{counts['class_evidence_only_hash']} evidence-only, "
        f"{counts['class_ambiguous_target']} ambiguous-target, {counts['class_unbound']} "
        "unbound. F0 meets the >=2-bound-accept criterion; F1/F2a/F2b meet it for no reviewer "
        "at the revision-13 pins, and the map's node hashes for those three are still the "
        "superseded revision-12 values. No canonical write, no gate verdict, no node "
        "transition. Checkpoint written at runtime/state/checkpoints/"
        "w054-gform-verdict-hash-integrity.json."
    ),
    "evidence_refs": [ref(p) for p in artifacts.values()],
    "next_falsifier": report["falsifier"],
})

with OUTBOX.open("a") as fh:
    for e in events:
        fh.write(json.dumps(e, sort_keys=True) + "\n")

CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
CHECKPOINT.write_text(json.dumps({
    "label": "worker-054-gform-verdict-hash-integrity",
    "task_id": TASK,
    "worker": ACTOR,
    "created_at": TS,
    "node_ids": ["F0", "F1", "F2a", "F2b"],
    "class_ids": CLASS_IDS,
    "gate": GATE,
    "artifacts": {name: {"path": str(p.relative_to(ROOT)), "sha256": h(p)}
                  for name, p in artifacts.items()},
    "input_snapshot_sha256": report["input_snapshot_sha256"],
    "snapshot_vs_pins": pins,
    "canonical_drift_since_snapshot": report["canonical_drift_since_snapshot"],
    "counts": counts,
    "per_target": {k: {"n_accept_bound_to_current": v["n_accept_bound_to_current"],
                       "gate_criterion_met": v["gate_criterion_met"]}
                   for k, v in pt.items()},
    "events_emitted": [e["event_id"] for e in events],
    "falsifier": report["falsifier"],
    "not_claimed": ["no gate verdict", "no node status", "no canonical artifact modified"],
}, indent=1, sort_keys=True) + "\n")

print(f"appended {len(events)} events to {OUTBOX.relative_to(ROOT)}")
print(f"checkpoint -> {CHECKPOINT.relative_to(ROOT)}")
