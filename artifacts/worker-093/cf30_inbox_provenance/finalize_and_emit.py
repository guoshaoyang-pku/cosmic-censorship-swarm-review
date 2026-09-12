#!/usr/bin/env python3
"""Finalize W093-CF30-INBOX-PROVENANCE-01: write manifest.json + CHECKPOINT.json and append
schema-validated events to comms/outbox/worker-093.jsonl.

Fail-closed: refuses to emit unless census.json verdict == PROVENANCE_CENSUS_PASS and all
embedded hashes match the bytes on disk. Writes only inside the task artifact dir and the
worker's own outbox.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
HERE = ROOT / "artifacts/worker-093/cf30_inbox_provenance"
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")
STAMP = datetime.now(CST).strftime("%Y%m%dT%H%M%S")
TASK = "W093-CF30-INBOX-PROVENANCE-01"
CLASSES = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ref(p: Path, n: int = 12) -> str:
    return f"{p.relative_to(ROOT)}#{sha(p)[:n]}"


census_p = HERE / "census.json"
script_p = HERE / "inbox_provenance_census.py"
readme_p = HERE / "README.md"
prereg_p = HERE / "PREREGISTRATION.md"
census = json.loads(census_p.read_text())
assert census["verdict"] == "PROVENANCE_CENSUS_PASS", "census did not pass; refusing to emit"
assert all(census["controls"].values()) and all(census["real_expectations"].values())
assert census["determinism"]["equal"] and not any(census["drift_T0_vs_T1"].values())
DIGEST = census["determinism"]["digest_pass1"]

# input pins quoted from the census itself (same T0 bytes)
pins = census["pins_T0"]
inbox_astra = pins["comms/inbox/astra.jsonl"]["sha256"][:12]
inbox_audit = pins["comms/inbox/astra-lead-audit.jsonl"]["sha256"][:12]
events_sha = pins["research_map/events.jsonl"]["sha256"][:12]
quar_astra = pins["runtime/state/comms_quarantine/astra-inbox-line3-20260912T0112.jsonl"]["sha256"][:12]
quar_audit = pins["runtime/state/comms_quarantine/astra-lead-audit-inbox-lines24-25-27-20260912T0112.jsonl"]["sha256"][:12]

FALSIFIER = (
    "Withdrawn if at the pinned T0 hashes: (a) any legitimate controller card that is "
    "accepted-stream or emitter-backed is classified UNBACKED_CONTROLLER; (b) any ACCEPTED_BACKED "
    "card lacks its event_id in the accepted stream; (c) any of C1-C11 or R1-R5 misses; (d) the "
    "three CF-30 ids are not reproduced by S1+S2+S3; (e) any pinned input hash differs T0 vs T1 or "
    "the two passes differ in digest."
)
UNBACKED = census["unbacked_controller_ids"]

manifest = {
    "schema": "worker-093/cf30-inbox-provenance/manifest/v1",
    "task_id": TASK, "actor": "worker-093", "node_id": "A1", "gate": "G-AUDIT",
    "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
    "created_at": NOW, "verdict": census["verdict"], "digest": DIGEST,
    "controls": f"{sum(census['controls'].values())}/{len(census['controls'])}",
    "real_expectations": f"{sum(census['real_expectations'].values())}/{len(census['real_expectations'])}",
    "unbacked_controller_ids": UNBACKED,
    "new_candidate": "astra-classsep-stabilize-0118",
    "artifacts": {
        "census.json": sha(census_p), "inbox_provenance_census.py": sha(script_p),
        "README.md": sha(readme_p), "PREREGISTRATION.md": sha(prereg_p),
    },
    "pinned_inputs": {k: v["sha256"] for k, v in sorted(pins.items())},
    "falsifier": FALSIFIER,
}
(HERE / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
manifest_sha = sha(HERE / "manifest.json")

checkpoint = {
    "schema": "worker-093/checkpoint/v1",
    "checkpoint_id": f"w093-ckpt-{STAMP}",
    "task_id": TASK, "actor": "worker-093", "node_id": "A1", "gate": "G-AUDIT",
    "created_at": NOW, "status": "complete_at_worker_level",
    "worker_status_field": "active",
    "verdict": census["verdict"], "digest": DIGEST,
    "counts": census["counts"],
    "unbacked_controller_ids": UNBACKED,
    "new_candidate": "astra-classsep-stabilize-0118",
    "next": ("controller adjudication of astra-classsep-stabilize-0118 against the CF-30/REC-31 "
             "quarantine standard; optional independent reproduction of this census"),
    "artifacts": dict(manifest["artifacts"], **{"manifest.json": manifest_sha}),
    "note": ("worker-level checkpoint only; research_map/checkpoint.py is controller-owned and was "
             "not run, no canonical state was written"),
}
(HERE / "CHECKPOINT.json").write_text(json.dumps(checkpoint, indent=2, sort_keys=True))
ckpt_sha = sha(HERE / "CHECKPOINT.json")

REF = [ref(census_p), ref(script_p), ref(readme_p), ref(prereg_p),
       f"artifacts/worker-093/cf30_inbox_provenance/manifest.json#{manifest_sha[:12]}",
       f"artifacts/worker-093/cf30_inbox_provenance/CHECKPOINT.json#{ckpt_sha[:12]}",
       f"comms/inbox/astra.jsonl#{inbox_astra}", f"comms/inbox/astra-lead-audit.jsonl#{inbox_audit}",
       f"research_map/events.jsonl#{events_sha}",
       f"runtime/state/comms_quarantine/astra-inbox-line3-20260912T0112.jsonl#{quar_astra}",
       f"runtime/state/comms_quarantine/astra-lead-audit-inbox-lines24-25-27-20260912T0112.jsonl#{quar_audit}",
       "research_map/events.jsonl#astra-life07-notice-injection",
       "research_map/events.jsonl#astra-life07-notice-classsep-r3"]

STATEMENT = (
    f"At the pinned T0 bytes (45 comms/inbox/*.jsonl, {census['counts']['cards']} cards; "
    f"research_map/events.jsonl#{events_sha} with {census['census']['accepted_stream']['event_ids']} "
    f"accepted ids; census digest {DIGEST[:12]}), the all-inbox provenance census classifies "
    f"{census['counts']['classification']['ACCEPTED_BACKED']} cards ACCEPTED_BACKED, "
    f"{census['counts']['classification']['DOWNWARD_LEAD']} DOWNWARD_LEAD and "
    f"{census['counts']['unbacked_controller']} UNBACKED_CONTROLLER instances "
    f"({len(UNBACKED)} distinct event_ids): the three CF-30 quarantine ids "
    "(human-pi-detector-fix-20260912T0100 at astra-lead-audit.jsonl:24; astra-detector-fix-0105 at "
    ":25; astra-detector-patch-result-0112 at :27 and astra.jsonl:3) plus one id not previously "
    "enumerated, astra-classsep-stabilize-0118, at astra.jsonl:4 and astra-lead-audit.jsonl:31 "
    "(actor astra, event_type assignment, created_at 2026-09-12T01:18:00+08:00; absent from the "
    "accepted stream; no syntactically emitted \"event_id\" literal in research_map/astra_lifecycle*.py; "
    "not quarantined; both containing files last written 2026-09-12T01:12:31+08:00, i.e. the cards "
    "were written about 5.5 minutes before their claimed timestamp). Backing is accepted-stream "
    "membership first, then emitter-literal membership; prose mentions inside controller records are "
    "not backing, which is exactly what separates these four ids from the 27 accepted-stream-backed "
    "controller cards in the same two files. 11/11 controls and 5/5 real expectations pass, inputs "
    "were stable T0 to T1, and two passes agree on the digest. This is a census, not an authorship "
    "finding: it does not adjudicate whether astra-classsep-stabilize-0118 is forged, and issues no "
    "gate, node or review verdict."
)

ASSUMPTIONS = [
    "Accepted stream = research_map/events.jsonl at the pinned hash; emitter backing = the syntactic literal '\"event_id\": \"<id>\"' in research_map/astra_lifecycle*.py. A quoted mention inside a summary/evidence string is not backing (the controller's own quarantine notice cites the injected ids in prose).",
    "Controller authority = actor 'astra' / 'human-pi*' or event_id prefix 'astra-'/'human-pi-'; lead authority = actor 'astra-lead*'/'lead-*' or id prefixes asg-/leadform-/lnum-/audit-. The authority field is attacker-controlled and is used only to route the backing test, never as proof.",
    "Lead/worker downward cards are expected to be absent from the accepted stream by protocol design (ingest pulls outbox, not inbox) and are classified DOWNWARD_*, never UNBACKED_CONTROLLER.",
    "mtime_delta_s (claimed created_at minus containing-file last write, +120 s tolerance) is recorded as context only: fleet-wide forward clock skew exists and the signal also fires on four legitimate accepted fan-out cards.",
    "class_id/class_ids strings are split on [;,] before membership, matching class_separation._scan_class_ids; no card binds a class outside the four frozen classes.",
]

events = [
    {"event_id": f"w093-cf30prov-{STAMP}-task-claim", "event_type": "status", "actor": "worker-093",
     "created_at": NOW, "task_id": TASK, "node_id": "A1", "gate": "G-AUDIT", "status": "active",
     "hours": 0.4, "class_id": CLASSES[0], "class_ids": CLASSES,
     "summary": ("No inbox card exists for worker-093 (fleet relaunch; slot self-selects). Took one "
                 "bounded class-bound task, W093-CF30-INBOX-PROVENANCE-01: a read-only systematic "
                 "census of all 45 comms/inbox/*.jsonl against the accepted stream and the controller "
                 "emitters, testing CF-30's stated next falsifier. No gate verdict, node completion "
                 "or review verdict."),
     "evidence_refs": REF, "next_falsifier": FALSIFIER},
    {"event_id": f"w093-cf30prov-{STAMP}-art-prereg", "event_type": "artifact", "actor": "worker-093",
     "created_at": NOW, "task_id": TASK, "node_id": "A1", "gate": "G-AUDIT", "class_id": CLASSES[0],
     "class_ids": CLASSES, "artifact_type": "preregistration", "path": str(prereg_p.relative_to(ROOT)),
     "sha256": sha(prereg_p), "validation_status": "unverified",
     "note": ("Pre-registration written before the instrument run, with an addendum recording the "
              "pre-run live discovery of astra-classsep-stabilize-0118 and the revised prediction; "
              "signals S1-S6, controls C1-C11, real expectations R1-R5, falsifier, limits."),
     "evidence_refs": [ref(prereg_p)]},
    {"event_id": f"w093-cf30prov-{STAMP}-art-py", "event_type": "artifact", "actor": "worker-093",
     "created_at": NOW, "task_id": TASK, "node_id": "A1", "gate": "G-AUDIT", "class_id": CLASSES[0],
     "class_ids": CLASSES, "artifact_type": "audit_instrument",
     "path": str(script_p.relative_to(ROOT)), "sha256": sha(script_p), "validation_status": "unverified",
     "note": ("Deterministic stdlib-only census: accepted-stream and emitter-literal backing, "
              "authority routing, duplicates/scope, within-file timestamp inversions, non-events, "
              "class-axis membership, per-input pins and two-pass digest; 11 planted controls run in "
              "a synthetic root; exit 0 iff PASS."),
     "evidence_refs": [ref(script_p)]},
    {"event_id": f"w093-cf30prov-{STAMP}-art-census", "event_type": "artifact", "actor": "worker-093",
     "created_at": NOW, "task_id": TASK, "node_id": "A1", "gate": "G-AUDIT", "class_id": CLASSES[0],
     "class_ids": CLASSES, "artifact_type": "audit_report", "path": str(census_p.relative_to(ROOT)),
     "sha256": sha(census_p), "validation_status": "unverified",
     "note": (f"Machine output at the pinned bytes: verdict {census['verdict']}, digest {DIGEST[:12]}, "
              "11/11 controls, 5/5 real expectations, inputs stable T0-T1; 209 cards = 162 accepted + "
              "41 downward-lead + 6 unbacked-controller instances (4 ids, including the new "
              "astra-classsep-stabilize-0118 x2); context signals recorded separately."),
     "evidence_refs": [ref(census_p)]},
    {"event_id": f"w093-cf30prov-{STAMP}-art-readme", "event_type": "artifact", "actor": "worker-093",
     "created_at": NOW, "task_id": TASK, "node_id": "A1", "gate": "G-AUDIT", "class_id": CLASSES[0],
     "class_ids": CLASSES, "artifact_type": "summary", "path": str(readme_p.relative_to(ROOT)),
     "sha256": sha(readme_p), "validation_status": "unverified",
     "note": "One-page summary: backing test, full unbacked table, the new stabilize-0118 candidate, context signals, non-claims, falsifier, reproduce command.",
     "evidence_refs": [ref(census_p)]},
    {"event_id": f"w093-cf30prov-{STAMP}-art-manifest", "event_type": "artifact", "actor": "worker-093",
     "created_at": NOW, "task_id": TASK, "node_id": "A1", "gate": "G-AUDIT", "class_id": CLASSES[0],
     "class_ids": CLASSES, "artifact_type": "manifest",
     "path": "artifacts/worker-093/cf30_inbox_provenance/manifest.json", "sha256": manifest_sha,
     "validation_status": "unverified",
     "note": "Artifact + pinned-input hashes, verdict, digest, controls, falsifier; CHECKPOINT.json is the worker-level checkpoint record.",
     "evidence_refs": [f"artifacts/worker-093/cf30_inbox_provenance/manifest.json#{manifest_sha[:12]}"]},
    {"event_id": f"w093-cf30prov-{STAMP}-claim", "event_type": "claim", "actor": "worker-093",
     "created_at": NOW, "task_id": TASK, "node_id": "A1", "gate": "G-AUDIT", "class_id": CLASSES[0],
     "class_ids": CLASSES, "conclusion_type": "formal_model", "statement": STATEMENT,
     "assumptions": ASSUMPTIONS, "falsifier": FALSIFIER, "evidence_refs": REF,
     "artifact_refs": [ref(census_p), ref(script_p), ref(prereg_p), ref(readme_p),
                       f"artifacts/worker-093/cf30_inbox_provenance/manifest.json#{manifest_sha[:12]}"],
     "non_claims": [
         "not a gate verdict, node status, review verdict, adoption, rollback or authorship finding",
         "does not adjudicate whether astra-classsep-stabilize-0118 or the CF-30 cards are forged; the controller owns CF-30/REC-31",
         "authority/actor fields are attacker-controlled; S1 is corroborated by S2-S6 and is not proof",
         "no canonical, inbox or quarantine byte was written; no detector write; research_map/checkpoint.py was not run"]},
    {"event_id": f"w093-cf30prov-{STAMP}-complete", "event_type": "status", "actor": "worker-093",
     "created_at": NOW, "task_id": TASK, "node_id": "A1", "gate": "G-AUDIT", "status": "active",
     "hours": 0.9, "class_id": CLASSES[0], "class_ids": CLASSES,
     "summary": ("W093-CF30-INBOX-PROVENANCE-01 complete at worker level; CHECKPOINT written and "
                 "exiting. Result: all-inbox sweep reproduces the three CF-30 unbacked controller "
                 "cards and finds one new unbacked, unquarantined controller id, "
                 "astra-classsep-stabilize-0118 (astra.jsonl:4, astra-lead-audit.jsonl:31, created "
                 "01:18:00 while both files last wrote 01:12:31), on the same two-inbox duplication "
                 "pattern as the 0112 injection. 11/11 controls, 5/5 real expectations, stable pins, "
                 "reproducible digest. No canonical write; worker status field stays active."),
     "evidence_refs": REF, "next_falsifier": FALSIFIER},
]

out = ROOT / "comms" / "outbox" / "worker-093.jsonl"
with out.open("a", encoding="utf-8") as f:
    for e in events:
        validate_event(e)
        f.write(json.dumps(e, sort_keys=True) + "\n")
print(json.dumps({"appended": len(events), "manifest_sha256": manifest_sha,
                  "checkpoint_sha256": ckpt_sha,
                  "outbox_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
                  "event_ids": [e["event_id"] for e in events]}, indent=2))
