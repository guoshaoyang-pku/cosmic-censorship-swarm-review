#!/usr/bin/env python3
"""Emit worker-032's W032-MAPREG-REPL-01 outbox events (idempotent by event_id).

Appends status -> artifact x4 -> review -> claim -> status to
comms/outbox/worker-032.jsonl.  Self-checks schema-required fields per
research_map/events.schema.json and PROTOCOL.md rule 5 before writing.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ART = ROOT / "artifacts" / "worker-032" / "mapreg-repl"
OUTBOX = ROOT / "comms" / "outbox" / "worker-032.jsonl"
CST = timezone(timedelta(hours=8))
STAMP = "20260912T0030"

CLASS_IDS = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]
NODE = "A1"
GATE = "G-AUDIT"
TASK = "W032-MAPREG-REPL-01"

MAP_SHA = "4fd40d4d1e4fc3602192eb8533e9a9f5075aa63ac644bd5c2dab30357f68db6b"
EVENTS_SHA = "fc36f1a774c0645b0fd6cf6c0891a3745fa2523c0abd3c905a20deb08f1fe273"
W036_REPORT = "artifacts/worker-036/map_hash_registry_audit_report.json"
W036_REPORT_SHA = "73d1c1a690a51f8d97443fb7c3b1324a5041ff0ac62e1cc31abf1b83751a3ae5"

FALSIFIER = (
    "Re-run artifacts/worker-032/mapreg-repl/scan_mapreg.py against "
    "research_map/research_map.json#4fd40d4d1e4f and research_map/events.jsonl#fc36f1a774c0. "
    "Falsified if (a) any node listed as declared-malformed has a full64 declared value; "
    "(b) any mismatch/flag-inconsistency node is consistent; (c) any of the 11 listed defect "
    "events has a full64 sha256 at the pinned events hash; (d) any listed dedup-blocked event_id "
    "is absent from ingested_ids.json or its outbox copy lacks a full digest; (e) any active "
    "frozen entry fails to match fresh bytes; or (f) W036's recorded declared values are not "
    "16-hex + 48 zeros."
)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    now = datetime.now(CST).replace(microsecond=0).isoformat()
    scanner_sha = sha(ART / "scan_mapreg.py")
    report_sha = sha(ART / "report.json")
    readme_sha = sha(ART / "README.md")
    ckpt_sha = sha(ART / "CHECKPOINT.json")

    common = {
        "actor": "worker-032",
        "node_id": NODE,
        "gate": GATE,
        "task_id": TASK,
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": CLASS_IDS,
    }

    def ev(eid, etype, **kw):
        d = {"event_id": eid, "event_type": etype, "created_at": now}
        d.update(common)
        d.update(kw)
        return d

    evid = [
        f"artifacts/worker-032/mapreg-repl/scan_mapreg.py#{scanner_sha[:12]}",
        f"artifacts/worker-032/mapreg-repl/report.json#{report_sha[:12]}",
        f"research_map/research_map.json#{MAP_SHA[:12]}",
        f"research_map/events.jsonl#{EVENTS_SHA[:12]}",
    ]

    events = []

    events.append(ev(
        f"w032-mapreg-repl-{STAMP}-task-claim",
        "status",
        status="active",
        hours=0.1,
        summary=(
            "No assignment card exists in comms/inbox for worker-032 (this instance). Took ONE "
            "bounded class-bound task: W032-MAPREG-REPL-01 = independent replication of W036-MAPREG-01 "
            "and current-revision re-measurement of the map declared/measured hash side, the checkpoint "
            "registry, the frozen artifacts and the accepted artifact-event digest formats. Method: "
            "independent stdlib reimplementation of the canonical digest semantics "
            "(research_map/astra_lifecycle.py:56-74), 8 selftest controls, point-in-time sha256 pin, "
            "read-only on shared state. Output: artifacts/worker-032/mapreg-repl/ + review verdict on "
            "W036. No node completion, no gate verdict."
        ),
        evidence_refs=evid,
        next_falsifier=FALSIFIER,
    ))

    for label, path, digest, atype in [
        ("scanner", "artifacts/worker-032/mapreg-repl/scan_mapreg.py", scanner_sha, "audit_scanner"),
        ("report", "artifacts/worker-032/mapreg-repl/report.json", report_sha, "replication_report"),
        ("readme", "artifacts/worker-032/mapreg-repl/README.md", readme_sha, "deliverable_summary"),
        ("checkpoint", "artifacts/worker-032/mapreg-repl/CHECKPOINT.json", ckpt_sha, "checkpoint"),
    ]:
        events.append(ev(
            f"w032-mapreg-repl-{STAMP}-artifact-{label}",
            "artifact",
            artifact_type=atype,
            path=path,
            sha256=digest,
            validation_status="unverified",
            evidence_refs=evid,
            note=(
                "stdlib-only, deterministic, read-only; --selftest 8/8 PASS"
                if label == "scanner"
                else "pinned snapshot + findings with per-finding falsifiers"
                if label == "report"
                else "one-page method/results/falsifier summary"
                if label == "readme"
                else "task checkpoint: snapshot pins, residual defects, next falsifier"
            ),
        ))

    events.append(ev(
        f"w032-mapreg-repl-{STAMP}-review-w036",
        "review",
        target_id="W036-MAPREG-01",
        reviewer="worker-032",
        verdict="accept",
        score=4.0,
        hard_failures=[],
        findings=[
            "Independently reproduced: W036's recorded F0/F1/F2a/F2b declared values are 16-hex + 48 zeros (zero-padded prefixes, not digests) and its 11 malformed accepted artifact events are all still present in events.jsonl at fc36f1a774c0.",
            "Independently reproduced: 9 of the 11 defects have an outbox full-digest correction under the same event_id, blocked by event_id-keyed digest dedup at research_map/comms.py:346; 6 are superseded for the map by later full-digest events with new event_ids.",
            "Superseded portion: at the current revision (map 4fd40d4d1e4f) F0/F1/F2a/F2b declared values are full64 and equal to the fresh digests of the canonical paths; the node-level declared defect is repaired.",
            "Not byte-reproducible on demand: the a8a73f98 map bytes are not archived, so the snapshot-side finding is corroborated by W036's recorded values and by runtime/state/controller_verification/lifecycle_20260912-002155.json (map_sha256_before a8a73f98 -> after 7f8792f8), not re-scanned from the original bytes. This is a limitation, not a hard failure.",
            "Additional independent measurements not in W036: registry 220 entries / 0 malformed / 2 stale (live reviews/ dir + one edited review file); 2 active frozen entries / 0 mismatches; A1 declared != measured correctly flagged false; snapshot stability re-measured at end of scan (map and events did not move).",
        ],
        evidence_refs=[
            f"{W036_REPORT}#{W036_REPORT_SHA[:12]}",
            f"artifacts/worker-032/mapreg-repl/report.json#{report_sha[:12]}",
            f"research_map/research_map.json#{MAP_SHA[:12]}",
            f"research_map/events.jsonl#{EVENTS_SHA[:12]}",
            "runtime/state/controller_verification/lifecycle_20260912-002155.json",
            "research_map/comms.py#L346",
        ],
        scope=(
            "Replication of W036's recorded snapshot claim and independent re-measurement at map "
            "4fd40d4d1e4f / events fc36f1a774c0: node declared/measured/fresh binding, event digest "
            "formats, dedup-blocked corrections, checkpoint registry, frozen entries. Not a code review "
            "of W036's scanner and not a certification of any artifact's content."
        ),
        independence=(
            "not an author of W036; independent reimplementation; second verdict at this target "
            "(W036 had none); single-reviewer ESS=1"
        ),
    ))

    events.append(ev(
        f"w032-mapreg-repl-{STAMP}-claim",
        "claim",
        statement=(
            "At research_map/research_map.json#4fd40d4d1e4f (updated 2026-09-12T00:25:10+08:00) and "
            "research_map/events.jsonl#fc36f1a774c0, independently re-measured with an independent "
            "reimplementation: (1) W036-MAPREG-01's node-level finding is confirmed as a snapshot claim "
            "and is REPAIRED at this revision - F0/F1/F2a/F2b declared artifact_sha256 are full64 and "
            "equal to the fresh digests of research_map/formulation_taxonomy.yaml, schemas/af_wcc_vacuum.yaml, "
            "schemas/af_scc_c2_vacuum.yaml, schemas/af_scc_c0_vacuum.yaml; 10/12 nodes bound, A1 "
            "mismatched only because reviews/ is a live directory, N1 absent/queued, 0 declared-malformed, "
            "0 declared_hash_matches_measured inconsistencies, 0 active frozen mismatches, registry 220 "
            "entries with 0 malformed and 2 live/time-skewed stale. (2) W036's event-stream finding is "
            "UNCHANGED: 11 accepted artifact events carry a non-digest sha256 (9 zero_padded_prefix "
            "16-hex+48 zeros from astra-lead-formulation, 2 short_hex_len20 from deepseek-flash-16); all 11 "
            "were present in W036's snapshot, none resolved and none new; 9 have outbox full-digest "
            "corrections under the same event_id that event_id-keyed dedup (research_map/comms.py:346) "
            "keeps out of events.jsonl; 6 of the 9 are superseded for the map by later full-digest events "
            "with new event_ids, while 3 leadform paths and the 2 flash-16 paths have no later full-digest "
            "event. Verdict on W036-MAPREG-01: accept, score 4.0, no hard failures; map and events did not "
            "move during the scan."
        ),
        conclusion_type="mechanical_evidence",
        assumptions=[
            "digest semantics are the canonical ones in research_map/astra_lifecycle.py:56-74 (file sha256; directory sha256 over sorted relpath\\0filesha\\n skipping ._*)",
            "a 16-hex + 48-zero 64-char value is treated as malformed; a genuine sha256 with that shape has probability 2^-192",
            "the accepted-stream line order is the ingest order; 'later' full-digest event means a later line for the same path",
            "the a8a73f98 map revision is not archived, so W036's snapshot side is corroborated from its recorded values and the lifecycle-03 transition record, not re-scanned",
            "point-in-time: only the pinned sha256 values make this reproducible",
        ],
        falsifier=FALSIFIER,
        evidence_refs=evid + [
            f"{W036_REPORT}#{W036_REPORT_SHA[:12]}",
            "runtime/state/controller_verification/lifecycle_20260912-002155.json",
            "research_map/comms.py#L346",
        ],
        artifact_refs=[
            f"artifacts/worker-032/mapreg-repl/report.json#{report_sha[:12]}",
            f"artifacts/worker-032/mapreg-repl/scan_mapreg.py#{scanner_sha[:12]}",
            f"artifacts/worker-032/mapreg-repl/CHECKPOINT.json#{ckpt_sha[:12]}",
        ],
        claims_completion=False,
    ))

    events.append(ev(
        f"w032-mapreg-repl-{STAMP}-status-final",
        "status",
        status="active",
        hours=0.6,
        summary=(
            "CHECKPOINT + EXIT. W032-MAPREG-REPL-01 complete: one class-bound task, artifacts on disk and "
            "hash-pinned (scanner fe167cd038ef, report 78df4737b98b, README 405d7c98c32c, checkpoint), "
            "review verdict accept 4.0 on W036-MAPREG-01, claim emitted. Residual: 11 non-digest accepted "
            "artifact events (9 dedup-blocked corrections), A1 live-dir mismatch, 2 stale registry entries. "
            "No node status changed, no gate verdict, shared state untouched."
        ),
        evidence_refs=evid + [f"artifacts/worker-032/mapreg-repl/report.json#{report_sha[:12]}"],
        next_falsifier=FALSIFIER,
        completion_scope="worker lifecycle only; not a node done / gate verdict",
    ))

    # --- self-check: unique ids, schema-required fields, valid JSON -----------
    required = {
        "artifact": ["node_id", "artifact_type", "path", "sha256", "validation_status"],
        "claim": ["class_id", "statement", "conclusion_type", "assumptions", "falsifier", "evidence_refs"],
        "review": ["target_id", "reviewer", "verdict", "score", "hard_failures", "findings"],
    }
    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            if line.strip():
                try:
                    existing.add(json.loads(line).get("event_id"))
                except Exception:
                    pass
    seen = set()
    for e in events:
        assert e["event_id"] not in existing, f"duplicate event_id vs outbox: {e['event_id']}"
        assert e["event_id"] not in seen, f"duplicate within batch: {e['event_id']}"
        seen.add(e["event_id"])
        import re
        if e["event_type"] == "artifact":
            assert re.fullmatch(r"[0-9a-f]{64}", e["sha256"]), f"artifact sha not full64: {e['event_id']}"
        for field in required.get(e["event_type"], []):
            assert field in e, f"{e['event_id']} missing {field}"
        json.dumps(e)

    with open(OUTBOX, "a") as fh:
        for e in events:
            fh.write(json.dumps(e) + "\n")

    print(f"appended {len(events)} events to {OUTBOX.relative_to(ROOT)}")
    for e in events:
        print(" ", e["event_id"], "|", e["event_type"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
