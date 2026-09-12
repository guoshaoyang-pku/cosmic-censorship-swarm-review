#!/usr/bin/env python3
"""Emit W093-GFORM-R3-REPLICATION-01 events into comms/outbox/worker-093.jsonl (idempotent)."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
D = Path(__file__).resolve().parent
OUTBOX = ROOT / "comms" / "outbox" / "worker-093.jsonl"
CST = timezone(timedelta(hours=8))
TS = datetime.now(CST).isoformat(timespec="seconds")
TASK = "W093-GFORM-R3-REPLICATION-01"


def sha(rel: str) -> str:
    return hashlib.sha256((D / rel).read_bytes()).hexdigest()


# Deterministic tag: stable across re-runs, unique to the report content, so the
# emitter is idempotent (event_id already present -> skipped).
TAG = "w093-r3repl-" + json.loads((D / "report.json").read_text())["digest"][:12]


def ref(rel: str) -> str:
    return f"artifacts/worker-093/gform_r3_replication/{rel}#{sha(rel)[:12]}"


report = json.loads((D / "report.json").read_text())
manifest = json.loads((D / "manifest.json").read_text())
r3 = manifest["pinned_inputs"]["reviews/G-FORM-final-verify-r3.json"]
falsifier = manifest["falsifier"]
r3_sha12 = r3["sha256"][:12]

ev = []
ev.append({"actor": "worker-093", "created_at": TS, "event_id": f"{TAG}-task-claim", "event_type": "status",
           "gate": "G-FORM", "gate_scope": ["G-FORM"], "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN",
           "class_ids": ["AF-SCC-C0-VAC-GEN"], "status": "active", "hours": 0.6, "task_id": TASK,
           "summary": ("W093-GFORM-R3-REPLICATION-01: no inbox card existed for worker-093; one bounded class-bound task "
                       "self-selected. Independent read-only replication of the F2b section and global pin claims of "
                       "reviews/G-FORM-final-verify-r3.json. Rules pre-registered before the run."),
           "evidence_refs": [ref("PREREGISTRATION.md"), f"reviews/G-FORM-final-verify-r3.json#{r3_sha12}"],
           "next_falsifier": falsifier})
for role, rel in [("preregistration", "PREREGISTRATION.md"), ("audit_instrument", "verify_r3_replication.py"),
                  ("audit_report", "report.json"), ("summary", "README.md"), ("manifest", "manifest.json"),
                  ("checkpoint", "CHECKPOINT.json"), ("pinned_input_archive", "pinned/INDEX.json"),
                  ("pinned_input_archive", "pinned/binding_rows.json"),
                  ("pinned_input_archive", "pinned/G-FORM-final-verify-r3.json")]:
    ev.append({"actor": "worker-093", "artifact_type": role, "created_at": TS, "event_id": f"{TAG}-art-{Path(rel).stem}",
               "event_type": "artifact", "gate": "G-FORM", "gate_scope": ["G-FORM"], "node_id": "F2b",
               "class_id": "AF-SCC-C0-VAC-GEN", "class_ids": ["AF-SCC-C0-VAC-GEN"], "task_id": TASK,
               "path": f"artifacts/worker-093/gform_r3_replication/{rel}", "sha256": sha(rel),
               "summary": f"W093-GFORM-R3-REPLICATION-01 {role}: {rel}", "validation_status": "unverified"})
ev.append({"actor": "worker-093", "created_at": TS, "event_id": f"{TAG}-claim", "event_type": "claim",
           "gate": "G-FORM", "gate_scope": ["G-FORM"], "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN",
           "class_ids": ["AF-SCC-C0-VAC-GEN"], "task_id": TASK, "conclusion_type": "formal_model",
           "statement": (f"At T0 2026-09-12T01:23+08:00, the F2b section of reviews/G-FORM-final-verify-r3.json "
                         f"({r3_sha12}) replicates: its schema/FROZEN pins equal measured disk bytes; its three "
                         "full-schema F2b accepts (worker-090, worker-071, worker-052) are reproduced identically by an "
                         "independent binder and by the shipped controller scan; worker-072's fourth accept "
                         "self-superseded to revise (7487f310d208 accept@01:10:13 -> 5db91bb0781d revise, event "
                         "01:15:24) and is correctly excluded; the r3-cited worker-066 disposition classifies "
                         "worker-090's accept SILENT on carriers C1-DENIAL and C2-PREMISE; both carrier quotes are "
                         "present verbatim at schema lines 152 and 246 with the containment chain at 239; and the "
                         "declared-hash layer is stale as reported (sidecar 256dd18d7944 and entry_hashes 09a5b37a190d "
                         "both declare 1bb78ce9b357). 10/10 checks, 12/12 controls. The aggregate claim "
                         "non_author_accepts_all=9 / revises=37 is NOT reproduced by any of the five pre-registered "
                         "universes (U1 3/8, U2 11/26, U3 15/46 events, U4 23/90, U5 136/309); this was pre-registered "
                         "as the expected outcome and is reported as an undefined-universe gap, not a false claim. The "
                         "'non-author' filter is not verifiable from disk (no F2b author field in FROZEN.json)."),
           "assumptions": ["r3 is the REC-39 per-file binding adjudication and is the artifact under replication; the rules "
                           "(strict binder, controller import, universes U1-U5) were fixed in PREREGISTRATION.md before the run",
                           "the live F2b pin is b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c and the FROZEN "
                           "rev29 pin is 815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0, both re-measured on disk",
                           "a review record binds F2b iff its top-level verdict is canonical, its target normalizes to F2b "
                           "(F2b/F2/AF-SCC-C0-VAC-GEN/af_scc_c0 path), and an explicit pin shares a 12-hex prefix with the live hash",
                           "counts are valid only at the T0 bytes; the review surface is mutable and the canonical schemas are "
                           "scheduled for a rev14/rev30 re-freeze"],
           "falsifier": falsifier,
           "evidence_refs": [ref("report.json"), ref("README.md"), ref("pinned/INDEX.json"), ref("pinned/binding_rows.json"),
                             f"reviews/G-FORM-final-verify-r3.json#{r3_sha12}",
                             "reviews/F2b-review-worker-072-rev29.json#5db91bb0781d",
                             "comms/outbox/worker-072.jsonl#w072-f2b-selfsupersede-review-20260912T011524",
                             "comms/outbox/worker-066.jsonl#w066-f2b-acceptdisp-20260912T011504-02-review",
                             "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe"],
           "artifact_refs": [ref("report.json"), ref("verify_r3_replication.py"), ref("manifest.json"), ref("CHECKPOINT.json")]})
ev.append({"actor": "worker-093", "created_at": TS, "event_id": f"{TAG}-review", "event_type": "review",
           "gate": "G-FORM", "gate_scope": ["G-FORM"], "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN",
           "class_ids": ["AF-SCC-C0-VAC-GEN"], "task_id": TASK,
           "target_id": f"reviews/G-FORM-final-verify-r3.json#{r3_sha12}", "reviewer": "worker-093",
           "verdict": "accept", "score": 4.5, "hard_failures": [],
           "findings": [
               {"field": "coverage_table[F2b].non_author_accepts_all / revises", "severity": "evidence",
                "finding": ("9/37 does not reproduce under any pre-registered universe (U1 3/8, U2 11/26, U3 15/46, "
                            "U4 23/90, U5 136/309); the universe behind the pair is not stated. Decision-relevant "
                            "full-accept set does reproduce exactly.")},
               {"field": "non_author filter", "severity": "soft",
                "finding": "not independently verifiable from disk: no F2b author field in FROZEN.json; reviewer-id level only"}],
           "evidence_refs": [ref("report.json"), ref("README.md"), f"reviews/G-FORM-final-verify-r3.json#{r3_sha12}"],
           "artifact_refs": [ref("report.json"), ref("pinned/INDEX.json")],
           "falsifier": falsifier,
           "note": "Worker review of an artifact at its pinned bytes; does not set node status or any gate verdict."})
ev.append({"actor": "worker-093", "created_at": TS, "event_id": f"{TAG}-complete", "event_type": "status",
           "gate": "G-FORM", "gate_scope": ["G-FORM"], "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN",
           "class_ids": ["AF-SCC-C0-VAC-GEN"], "status": "active", "hours": 0.6, "task_id": TASK,
           "summary": (f"W093-GFORM-R3-REPLICATION-01 complete at worker level: REPLICATION_PASS, 10/10 checks, 12/12 "
                       f"controls, digest {report['digest'][:12]}; T0 byte archive pinned; CHECKPOINT.json written and "
                       "exiting. No canonical write, no node done, no validation_status=passed, no gate verdict."),
           "evidence_refs": [ref("report.json"), ref("manifest.json"), ref("CHECKPOINT.json"), ref("pinned/INDEX.json")],
           "next_falsifier": falsifier})
ev.append({"actor": "worker-093", "created_at": TS, "event_id": f"{TAG}-checkpoint", "event_type": "status",
           "gate": "G-FORM", "gate_scope": ["G-FORM"], "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN",
           "class_ids": ["AF-SCC-C0-VAC-GEN"], "status": "active", "hours": 0.0, "task_id": TASK,
           "summary": ("Worker checkpoint checkpoint_id w093-gform-r3-replication-20260912T0123 written to "
                       "artifacts/worker-093/gform_r3_replication/CHECKPOINT.json; controller checkpoint.py was not run "
                       "(not worker authority). Exiting."),
           "evidence_refs": [ref("CHECKPOINT.json"), ref("manifest.json")],
           "next_falsifier": falsifier})

existing = set()
if OUTBOX.exists():
    for line in OUTBOX.read_text().splitlines():
        try:
            existing.add(json.loads(line).get("event_id"))
        except Exception:
            pass
added = 0
with open(OUTBOX, "a", encoding="utf-8") as fh:
    for e in ev:
        if e["event_id"] in existing:
            continue
        fh.write(json.dumps(e, sort_keys=True) + "\n")
        added += 1
print(json.dumps({"tag": TAG, "events_total": len(ev), "added": added, "outbox": str(OUTBOX.relative_to(ROOT))}, indent=1))
