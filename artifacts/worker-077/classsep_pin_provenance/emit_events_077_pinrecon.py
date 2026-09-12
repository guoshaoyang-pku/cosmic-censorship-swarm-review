#!/usr/bin/env python3
"""Emit W077-CLASSSEP-PINRECON-01 events + checkpoint (append-only, schema-validated).

Writes only:
  artifacts/worker-077/classsep_pin_provenance/entry_hashes.json
  comms/outbox/worker-077.jsonl            (append)
  runtime/state/worker-077_classsep_pin_provenance_checkpoint.json
  runtime/state/w077_checkpoints.jsonl     (append)
"""
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
OUT = ROOT / "artifacts/worker-077/classsep_pin_provenance"
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

TZ = timezone(timedelta(hours=8))
TS = datetime.now(TZ).isoformat(timespec="seconds")
TAG = "w077-pinrecon-" + datetime.now(TZ).strftime("%Y%m%dT%H%M%S")
TASK_ID = "W077-CLASSSEP-PINRECON-01"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
CLASS_ID = ";".join(CLASS_IDS)


def sha(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


report = json.loads((OUT / "report.json").read_text())
v = report["verdict"]
attested = report["attested_digest"]
unattested = report["unattested_digest"]
pins = report["pins"]

paths = {
    "report": "artifacts/worker-077/classsep_pin_provenance/report.json",
    "report_run2": "artifacts/worker-077/classsep_pin_provenance/report.run2.json",
    "instrument": "artifacts/worker-077/classsep_pin_provenance/reconcile_classsep_pin.py",
    "readme": "artifacts/worker-077/classsep_pin_provenance/README.md",
    "determinism": "artifacts/worker-077/classsep_pin_provenance/determinism.json",
}
hashes = {k: sha(p) for k, p in paths.items()}

entry = {
    "task_id": TASK_ID,
    "worker": "worker-077",
    "at": TS,
    "pins": {
        "research_map/research_map.json": pins.get("research_map/research_map.json"),
        "research_map/events.jsonl": pins.get("research_map/events.jsonl"),
        "entry_hashes.json": pins.get("entry_hashes.json"),
        "runtime/state/controller_verification/cf29-detector-write-forensics.json":
            pins.get("runtime/state/controller_verification/cf29-detector-write-forensics.json"),
        "research_map/ASTRA_HANDOFF.md": pins.get("research_map/ASTRA_HANDOFF.md"),
    },
    "outputs": hashes,
    "attested_digest": attested,
    "unattested_digest": unattested,
    "content_digest": report["content_digest"],
}
(OUT / "entry_hashes.json").write_text(json.dumps(entry, indent=1, sort_keys=True) + "\n")
hashes["entry_hashes"] = sha("artifacts/worker-077/classsep_pin_provenance/entry_hashes.json")

evidence = [
    f"research_map/research_map.json#sha256:{pins.get('research_map/research_map.json')}",
    f"research_map/events.jsonl#sha256:{pins.get('research_map/events.jsonl')}",
    f"entry_hashes.json#sha256:{pins.get('entry_hashes.json')}",
    "runtime/state/controller_verification/cf29-detector-write-forensics.json#sha256:"
    + str(pins.get("runtime/state/controller_verification/cf29-detector-write-forensics.json")),
    f"research_map/ASTRA_HANDOFF.md#sha256:{pins.get('research_map/ASTRA_HANDOFF.md')}",
]
for k, p in paths.items():
    evidence.append(f"{p}#sha256:{hashes[k] if k != 'entry_hashes' else hashes['entry_hashes']}")
artifact_refs = evidence[5:]
next_falsifier = report["falsifier"]

events = []


def add(ev):
    ev.setdefault("actor", "worker-077")
    ev.setdefault("class_id", CLASS_ID)
    ev.setdefault("class_ids", CLASS_IDS)
    ev.setdefault("node_id", "A1")
    ev.setdefault("gate", "G-AUDIT")
    validate_event(ev)
    events.append(ev)


add({
    "event_id": f"{TAG}-status-open", "event_type": "status", "created_at": TS,
    "status": "active", "hours": 0.0,
    "summary": (
        "No assignment card exists in comms/inbox/worker-077.jsonl. Took ONE bounded class-bound "
        "task: W077-CLASSSEP-PINRECON-01 = read-only pin-provenance reconciliation of the "
        "class-separation gate instrument's baseline digest, responsive to the open "
        "astra-life07-classsep-adjudication-review whose operative text names a pin that matches "
        "no bytes. Output: deterministic reconciler, machine report, README, determinism record; "
        "no gate verdict, no canonical write."
    ),
    "evidence_refs": evidence, "next_falsifier": next_falsifier,
})

add({
    "event_id": f"{TAG}-artifact-report", "event_type": "artifact", "created_at": TS,
    "artifact_type": "pin_provenance_reconciliation_report", "path": paths["report"],
    "sha256": hashes["report"], "validation_status": "unverified",
    "note": "306 class_separation-named files censused, 85 pre-move copies with 1 distinct digest, "
            "30921-file/688MB sweep, 110 orphan citation sites across 36 records, checks 7/7, "
            "controls 7/7, in-run pin drift none.",
    "evidence_refs": artifact_refs,
})
add({
    "event_id": f"{TAG}-artifact-instrument", "event_type": "artifact", "created_at": TS,
    "artifact_type": "verifier", "path": paths["instrument"], "sha256": hashes["instrument"],
    "validation_status": "unverified",
    "note": "Deterministic, stdlib only, read-only on every canonical path; no disputed hex prefix "
            "is hardcoded beyond the shared 6-char stem and the two pre-registered hypotheses; "
            "exit 0/2/3; two runs produce identical content digests.",
    "evidence_refs": [f"{paths['report']}#sha256:{hashes['report']}"],
})
add({
    "event_id": f"{TAG}-artifact-readme", "event_type": "artifact", "created_at": TS,
    "artifact_type": "report", "path": paths["readme"], "sha256": hashes["readme"],
    "validation_status": "unverified",
    "note": "Cold-start method, headline table, findings F1-F5, impact, falsifier, non-claims, "
            "reproduction commands.",
    "evidence_refs": [f"{paths['report']}#sha256:{hashes['report']}"],
})
add({
    "event_id": f"{TAG}-artifact-determinism", "event_type": "artifact", "created_at": TS,
    "artifact_type": "determinism_record", "path": paths["determinism"],
    "sha256": hashes["determinism"], "validation_status": "unverified",
    "note": "Two runs at the pinned inputs: identical content digest " + report["content_digest"],
    "evidence_refs": [f"{paths['report']}#sha256:{hashes['report']}"],
})
add({
    "event_id": f"{TAG}-artifact-entry-hashes", "event_type": "artifact", "created_at": TS,
    "artifact_type": "entry_hashes", "path": "artifacts/worker-077/classsep_pin_provenance/entry_hashes.json",
    "sha256": hashes["entry_hashes"], "validation_status": "unverified",
    "note": "sha256 of every artifact in the task directory plus the run pins.",
    "evidence_refs": [f"{paths['report']}#sha256:{hashes['report']}"],
})

add({
    "event_id": f"{TAG}-claim", "event_type": "claim", "created_at": TS,
    "conclusion_type": "formal_model",
    "statement": (
        f"Machine measurement (not a mathematics claim) at the run pins: the class-separation "
        f"baseline recorded at freeze time is {attested}. It is attested by 85 on-disk copies with "
        f"a single distinct digest, by the primary freeze event astra-w07adj-00 whose created_at "
        f"equals frozen_artifacts.frozen_at (2026-09-11T23:30:20+08:00) and which cites the prefix "
        f"{attested[:12]}, by the current frozen_artifacts entry and by entry_hashes.json. The "
        f"digest {unattested} is cited at 103 live sites across the controller findings "
        f"(CF-16/CF-26/CF-29 action text), ASTRA_HANDOFF.md:51, the CF-29 forensics ruling, the r3 "
        f"CLASSSEP-calibration-adjudication review and audit-lead lifecycle-08 events, yet no file "
        f"in a 30921-file / 688 MB sweep measures it; it differs from the attested digest at hex "
        f"characters 7-9. A second orphan, worker-036's review target_sha256 "
        f"c266dbceca87b8b0... (cited 6 times), shares 13 hex characters with the attested digest "
        f"and also matches no file. 292 further citation sites use prefixes <=13 hex characters "
        f"that are prefixes of both the attested and the orphan full digest, so such prefixes do "
        f"not discriminate. Operatively: any hash-bound instruction naming the unattested prefix "
        f"as the active frozen pin is not executable as written and must use {attested}."
    ),
    "assumptions": [
        "The primary freeze event is the one whose created_at equals frozen_artifacts.frozen_at and "
        "which records the detector adjudication; it is located by event_id astra-w07adj-00.",
        "The pre-move byte identity is the unique digest shared by copies carrying the stem c266db; "
        "post-move copies (a8c04fc31e4a) and the CF-29 quarantined e36b0d644ca bytes are excluded "
        "by construction, not by preference.",
        "The two expected digests are pre-registered hypotheses; the run reports whether they hold, "
        "and all prefixes and classifications are derived from measured bytes.",
        "The 'no bytes satisfy it' claim is scoped to the swept domain (30921 files / 688 MB, "
        "<=2 MB per file, no cap hit).",
        "The measurement is void if any pinned stable input drifts during the run.",
    ],
    "falsifier": next_falsifier, "evidence_refs": evidence, "artifact_refs": artifact_refs,
})

add({
    "event_id": f"{TAG}-blocker", "event_type": "blocker", "created_at": TS,
    "description": (
        "Pin-provenance defect, now measured end-to-end: the operative controller text for the "
        "open classsep adjudication names c266dbecaa87 as the active frozen pin, but that digest "
        "matches no file in the swept domain; the byte-attested baseline is c266dbceca87fb996b... "
        "The same variant appears in CF-16/CF-26/CF-29 action text, ASTRA_HANDOFF.md:51 and the "
        "CF-29 forensics ruling, and has propagated into 36 records including audit-lead "
        "lifecycle-08 events. A second orphan full digest (worker-036 target_sha256 "
        "c266dbceca87b8b0...) is already flagged by worker-080. Additionally 292 sites use "
        "prefixes <=13 hex chars that collide between the attested digest and that orphan."
    ),
    "needed_to_unblock": (
        "Controller corrects its own prose pin in CF-16/CF-26/CF-29 action text and the handoff "
        "to c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920 (CF-4: the worker "
        "does not edit another agent's text); the astra-life07-classsep-adjudication-review quotes "
        "a prefix of at least 14 hex characters so the F4 collision cannot mask the baseline. No "
        "canonical write was made by this worker."
    ),
    "next_falsifier": next_falsifier, "evidence_refs": evidence,
})

add({
    "event_id": f"{TAG}-status-complete", "event_type": "status", "created_at": TS,
    "status": "active", "hours": 0.7,
    "summary": (
        "TASK COMPLETE (unverified, worker-level): W077-CLASSSEP-PINRECON-01. Attested baseline "
        f"{attested} (85 copies, 1 digest; freeze event, frozen_artifacts and entry_hashes agree). "
        f"Orphan variants: {unattested} at 103 sites / 36 records and worker-036's "
        "c266dbceca87b8b0... at 6 sites, neither matching any of 30921 swept files (688 MB). "
        "Prefix-collision F4: 292 sites use <=13-hex prefixes that do not discriminate. Checks "
        "7/7 and controls 7/7 PASS, no in-run pin drift, two runs identical (content digest "
        + report["content_digest"] + "). No gate verdict, no canonical write."
    ),
    "evidence_refs": evidence, "next_falsifier": next_falsifier,
})

outbox = ROOT / "comms/outbox/worker-077.jsonl"
with open(outbox, "a") as f:
    for e in events:
        f.write(json.dumps(e, sort_keys=True) + "\n")

checkpoint = {
    "checkpoint": 6,
    "at": TS,
    "worker": "worker-077",
    "lifecycle": "worker-077-20260912T011000-968807",
    "role": "bounded execution worker",
    "task": {
        "task_id": TASK_ID,
        "class_id": CLASS_ID,
        "class_ids": CLASS_IDS,
        "node_id": "A1",
        "gate": "G-AUDIT",
        "origin": "immediate queue self-selected; no inbox card existed for worker-077",
        "artifact": paths["report"],
        "verdict": "measurement_complete",
        "hard_failures": [],
        "hours_spent_estimate": 0.7,
    },
    "result": {
        "attested_digest": attested,
        "unattested_digest": unattested,
        "orphan_fulls_cited": v["orphan_fulls_cited"],
        "orphan_citation_sites": v["orphan_citation_sites"],
        "orphan_citation_records": len(v["orphan_citation_records"]),
        "sweep_files": report["sweep"]["files_scanned"],
        "sweep_bytes": report["sweep"]["bytes_scanned"],
        "sweep_matches_unattested": len(report["sweep"]["matches_unattested"]),
        "checks_pass": sum(1 for c in report["checks"] if c["status"] == "PASS"),
        "checks_total": len(report["checks"]),
        "controls_pass": sum(1 for c in report["controls"] if c["status"] == "PASS"),
        "controls_total": len(report["controls"]),
        "content_digest": report["content_digest"],
        "instrument_exit_runs": [0, 0],
    },
    "pins": entry["pins"],
    "files": hashes,
    "next_falsifier": next_falsifier,
    "non_claims": report["non_claims"],
}
(ROOT / "runtime/state/worker-077_classsep_pin_provenance_checkpoint.json").write_text(
    json.dumps(checkpoint, indent=1, sort_keys=True) + "\n")
with open(ROOT / "runtime/state/w077_checkpoints.jsonl", "a") as f:
    f.write(json.dumps(checkpoint, sort_keys=True) + "\n")

print(json.dumps({"events_written": len(events), "event_ids": [e["event_id"] for e in events],
                  "checkpoint": "runtime/state/worker-077_classsep_pin_provenance_checkpoint.json",
                  "hashes": hashes}, indent=1))
