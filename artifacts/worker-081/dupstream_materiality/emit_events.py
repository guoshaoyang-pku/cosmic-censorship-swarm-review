#!/usr/bin/env python3
"""Emit W081-DUPSTREAM-MATERIALITY-01 events to comms/outbox/worker-081.jsonl.

Idempotent: event ids are fixed from the report's measured_at tag; re-running
skips ids already present.  Self-validates every event with research_map.schemas
before appending.  Appends only to this worker's own outbox (PROTOCOL upward
channel); never touches comms/inbox or research_map/events.jsonl (CF-30 lesson).
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from research_map.schemas import validate_event  # noqa: E402

AD = "artifacts/worker-081/dupstream_materiality"
TAG = "20260912T012420"  # report measured_at tag
ACTOR = "worker-081"
CLASS_ID = "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH"


def sha(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def ref(rel: str) -> str:
    return f"{rel}#{sha(rel)[:12]}"


def build() -> list[dict]:
    rep = json.loads((ROOT / f"{AD}/report.json").read_text())
    created = __import__("time").strftime("%Y-%m-%dT%H:%M:%S%z")
    c = rep["census_primary_fingerprint"]
    v = rep["verdicts"]
    lead = rep["lead_batch_adjudication"]
    common = {
        "actor": ACTOR,
        "created_at": created,
        "node_id": "F0,F1,F2a,F2b,N0,L1",
        "gate": "G-FORM",
        "task_id": "W081-DUPSTREAM-MATERIALITY-01",
        "class_ids": CLASS_ID.split(";"),
    }
    ev: list[dict] = []

    ev.append(
        {
            **common,
            "event_id": f"w081-dupstream-{TAG}-status-claim",
            "event_type": "status",
            "class_id": CLASS_ID,
            "status": "active",
            "hours": 0.05,
            "summary": (
                "No assignment card existed for slot worker-081; took ONE bounded class-bound task "
                "(W081-DUPSTREAM-MATERIALITY-01): population census of content-duplicate accepted events and "
                "whether they materialise as duplicate map state. Read-only; no canonical write, no gate verdict. "
                f"Pinned corpora: events {rep['pins_start']['research_map/events.jsonl'][:12]}, map "
                f"{rep['pins_start']['research_map/research_map.json'][:12]}."
            ),
            "evidence_refs": [ref(f"{AD}/prereg.json")],
            "next_falsifier": rep["falsifier"],
        }
    )

    artifacts = [
        ("prereg", f"{AD}/prereg.json", "preregistration: question, declared fingerprint, controls, falsifier"),
        ("census_harness", f"{AD}/census_dupstream_081.py", "deterministic stdlib-only harness; --from-pinned replay mode"),
        ("census_report", f"{AD}/report.json", "primary evidence: pins, counts, doubled groups, controls, verdicts"),
        ("replay_check", f"{AD}/replay_check.json", "pinned replay matches primary on all core fields"),
        ("summary", f"{AD}/README.md", "human summary: method, measurements, verdicts, falsifier, limits"),
        ("manifest", f"{AD}/SHA256SUMS", "sha256 manifest of the task directory"),
        ("checkpoint", "runtime/state/w081_dupstream_checkpoint.json", "worker checkpoint with pins, counts, verdicts"),
    ]
    for i, (atype, rel, note) in enumerate(artifacts):
        e = {
            **common,
            "event_id": f"w081-dupstream-{TAG}-artifact-{i}-{Path(rel).name}",
            "event_type": "artifact",
            "class_id": CLASS_ID,
            "artifact_type": atype,
            "path": rel,
            "sha256": sha(rel),
            "validation_status": "unverified",
            "note": note,
            "evidence_refs": [ref(f"{AD}/report.json")],
        }
        ev.append(e)

    ev.append(
        {
            **common,
            "event_id": f"w081-dupstream-{TAG}-claim-census",
            "event_type": "claim",
            "class_id": CLASS_ID,
            "conclusion_type": "open_problem",
            "statement": (
                f"At the pinned corpus (events {rep['pins_start']['research_map/events.jsonl'][:12]}, map "
                f"{rep['pins_start']['research_map/research_map.json'][:12]}), {c['n_events']} accepted events contain "
                f"{c['n_duplicate_groups']} content-duplicate groups ({c['n_duplicate_ids']} ids) under the declared "
                f"fingerprint (exclude event_id/created_at/_received_at); {c['n_doubled_groups']} groups "
                f"({c['n_materialised_members_of_doubled_groups']} ids) are materialised as distinct map entries -- "
                f"6 claims, 8 reviews, 1 resource_request across F0/F1/F2a/F2b/N0/L1. The formulation lead's own duplicate "
                f"batch is contained (14/14 applied, 0 entry-level materialisations, all 7 pairs body-identical; one disclosed "
                f"textual mention at claims[531].supersedes_rejected), but its generalisation 'duplication is ledger "
                f"bookkeeping, not duplicated map state' is refuted population-wide: fresh event_ids defeat the event_id-keyed "
                f"idempotency ledger. Duplicate emission does NOT explain the CF-31 F2b accept/revise divergence (0 of the four "
                f"named reviewers' F2b-targeted ids are duplicate members), and "
                f"numerics/gates.py::_protocol_review is invariant under content dedup at the live bytes "
                f"(reviewed=true, contest=true, 5 accepting / 5 dissenting). This is an artifact measurement, not a "
                f"mathematical claim and not a gate verdict."
            ),
            "assumptions": [
                "content equivalence = identical canonical JSON modulo event_id/created_at/_received_at (emission/ingest metadata)",
                "materialised = a dict entry in a list-valued top-level map section carrying that event_id at top level",
                "census binds to the pinned snapshot bytes; the live map/stream move",
                "wrongly merged legitimate identical-text re-emissions would inflate counts only if both were also materialised; every reported doubled group is listed with its locations for inspection",
                "worker cannot set done/passed/gate verdicts; leads adjudicate",
            ],
            "falsifier": rep["falsifier"],
            "evidence_refs": [
                ref(f"{AD}/report.json"),
                ref(f"{AD}/census_dupstream_081.py"),
                ref(f"{AD}/replay_check.json"),
                ref(f"{AD}/README.md"),
            ],
            "artifact_refs": [f"{AD}/report.json#{sha(f'{AD}/report.json')[:12]}"],
        }
    )

    ev.append(
        {
            **common,
            "event_id": f"w081-dupstream-{TAG}-review-lead-dup-notice",
            "event_type": "review",
            "class_id": CLASS_ID,
            "reviewer": ACTOR,
            "target_id": "lead-form-life08-128-dup-notice",
            "verdict": "revise",
            "score": 3.0,
            "hard_failures": [],
            "findings": (
                "Batch-level containment CONFIRMED independently (14/14 accepted ids in applied_event_ids, 0 entry-level "
                "materialisations, 7/7 pairs body-identical, one disclosed textual mention at claims[531]). Verdict is revise, "
                "not accept, because the disposition is materially incomplete at population scale: 15 other content-duplicate "
                "groups (34 ids) ARE materialised as distinct map entries (claims/reviews/resource_requests across "
                "F0/F1/F2a/F2b/N0/L1), so distinct event_ids defeat the id-keyed ledger exactly as the notice warns, and the "
                "recommended fix (content-fingerprint dedup on ingest) must be extended to map materialisation and to "
                "review/claim coverage counters. Concrete examples: w038 F0 accept materialised 3x (reviews[312]/[324]/[327]); "
                "w090 F1 review 3x (reviews[121]/[125]/[129]); w040 F1 claim 2x (claims[229]/[230]); w092 F2a claim+review 2x. "
                "The notice's secondary finding (events.schema.json omits status/blocker from its oneOf) was not re-measured here."
            ),
            "evidence_refs": [
                ref(f"{AD}/report.json"),
                ref(f"{AD}/README.md"),
            ],
        }
    )

    ev.append(
        {
            **common,
            "event_id": f"w081-dupstream-{TAG}-status-complete",
            "event_type": "status",
            "class_id": CLASS_ID,
            "status": "active",
            "hours": 0.35,
            "summary": (
                "Worker lifecycle complete (one class-bound task, one checkpoint, exit). Deliverables: census harness + primary "
                "report + pinned replay + checkpoint, all hash-pinned. Verdicts: lead batch contained (V1); population "
                "generalisation refuted, 15 doubled groups (V2); CF-31 F2b divergence not explained by duplication (V3); "
                "gates._protocol_review invariant under content dedup (V4); named CF-31 reviewer worker-090 carries a tripled F1 "
                "review elsewhere (V5); 8/8 controls pass. No gate verdict, no node status, no validation_status, no canonical edit."
            ),
            "evidence_refs": [
                ref(f"{AD}/report.json"),
                ref(f"{AD}/README.md"),
                ref("runtime/state/w081_dupstream_checkpoint.json"),
            ],
            "next_falsifier": rep["falsifier"],
        }
    )
    return ev


def main() -> int:
    outbox = ROOT / "comms/outbox/worker-081.jsonl"
    existing = set()
    if outbox.exists():
        for line in outbox.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line).get("event_id"))
            except json.JSONDecodeError:
                continue
    events = build()
    fresh = []
    for e in events:
        validate_event(e)  # raises on schema violation
        if e["event_id"] in existing:
            continue
        fresh.append(e)
    with outbox.open("a", encoding="utf-8") as fh:
        for e in fresh:
            fh.write(json.dumps(e, sort_keys=True) + "\n")
    print(json.dumps({"validated": len(events), "appended": len(fresh), "outbox": str(outbox)}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
