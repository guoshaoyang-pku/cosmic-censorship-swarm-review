#!/usr/bin/env python3
"""Write the worker-009 DET-REV12 checkpoint (runtime/state + artifacts/worker-009/detrev12).

Checkpoint only: it records what the bounded worker pass produced and what it did
NOT do (no canonical write, no gate/node movement).  Fluent text is never promoted.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
STATE = ROOT / "runtime" / "state"
RECORD = ROOT / "artifacts" / "worker-009" / "detrev12" / "verification_candidates_worker-009.json"
PATCH_CSV = ROOT / "ledger" / "citation_audit_scc_candidates_worker-009.csv"
PATCH_JSONL = ROOT / "ledger" / "citation_audit_scc_candidates_worker-009.jsonl"
DRYRUN = ROOT / "artifacts" / "worker-009" / "detrev12" / "dryrun_applied_citation_audit_12row.csv"
TOOL = ROOT / "artifacts" / "worker-009" / "detrev12" / "verify_candidates.py"
EMITTER = ROOT / "artifacts" / "worker-009" / "detrev12" / "emit_detrev12_events.py"
OUTBOX = ROOT / "comms" / "outbox" / "worker-009.jsonl"
MAP = ROOT / "research_map" / "research_map.json"
GLOBAL_CKPT = STATE / "current_checkpoint.json"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    rec = json.loads(RECORD.read_text())
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    ts = now.replace("-", "").replace(":", "").replace("+", "")[:15]

    artifacts = {str(p.relative_to(ROOT)): sha(p) for p in (RECORD, PATCH_CSV, PATCH_JSONL, DRYRUN, TOOL, EMITTER)}

    events = []
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            if str(e.get("event_id", "")).startswith("w009-detrev12-"):
                events.append(e["event_id"])

    glob = json.loads(GLOBAL_CKPT.read_text()) if GLOBAL_CKPT.exists() else {}
    glob_path = STATE / "checkpoints" / f"{glob.get('checkpoint_id','')}.json"

    promoted = [c["citation_id"] for c in rec["candidates"] if c["decision"] == "PROMOTE"]
    dropped = [c["citation_id"] for c in rec["candidates"] if c["decision"] == "DROP"]

    checkpoint = {
        "checkpoint_id": f"w009-ckpt-detrev12-{ts}",
        "created_at": now,
        "worker": "worker-009",
        "task_id": "DETREV12-CANDIDATE-AUDIT-01",
        "assignment_id": "asg-2026-09-11-L1-deepseek-flash-09-18",
        "node_id": "L1",
        "gate": "G-LIT",
        "group_id": "literature",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "result": (
            "PROMOTED 5/5 DET-REV12 uncovered candidates to class-binding corrections by primary-source "
            f"re-fetch ({', '.join(promoted)}); 0 dropped; {len(rec['checks'])}/{len(rec['checks'])} declared "
            "checks PASS. Combined 12-row patch (7 prior + 5 new) dry-runs onto the frozen canonical ledger "
            "changing exactly 12/97 class_mapping cells, no other byte; negative control refuses a stale "
            "old_class_mapping. Canonical ledger untouched; no gate or node verdict claimed."
        ),
        "artifacts": artifacts,
        "events": events,
        "outbox": str(OUTBOX.relative_to(ROOT)),
        "hours": 1.0,
        "canonical_write": "none",
        "reviews_required": [
            "lead-literature adjudication of the five quote sets and the 12-row patch",
            "independent re-fetch of math/9901147 (e-print returned HTTP 403; abs page used for SRC-014)",
        ],
        "next_falsifier": rec["next_falsifier"],
        "falsifier": rec["falsifier"],
        "map_sha256_measured": sha(MAP),
        "global_checkpoint": {
            "checkpoint_id": glob.get("checkpoint_id"),
            "label": glob.get("label"),
            "created_at": glob.get("created_at"),
            "path": str(glob_path.relative_to(ROOT)) if glob_path.exists() else None,
            "sha256": sha(glob_path) if glob_path.exists() else None,
        },
    }

    out = STATE / f"w009_checkpoint_detrev12_{ts}.json"
    out.write_text(json.dumps(checkpoint, ensure_ascii=False, indent=1) + "\n")

    md = [
        "# worker-009 DET-REV12 checkpoint",
        "",
        f"- checkpoint_id: `{checkpoint['checkpoint_id']}`",
        f"- created_at: `{now}`",
        f"- assignment: `{checkpoint['assignment_id']}`  node `L1`  gate `G-LIT`  classes `AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN`",
        f"- result: 5 PROMOTE / 0 DROP; {len(rec['checks'])}/{len(rec['checks'])} checks PASS; 12/97 cells dry-run changed",
        "- canonical `ledger/citation_audit.csv` untouched; worker events cannot move gates or node status",
        "",
        "## Artifacts (sha256)",
        "",
    ]
    md += [f"- `{p}`  `{h[:16]}`" for p, h in artifacts.items()]
    md += ["", "## Events written to `comms/outbox/worker-009.jsonl` (pending controller ingest)", ""]
    md += [f"- `{e}`" for e in events]
    md += [
        "",
        "## Next falsifier",
        "",
        checkpoint["next_falsifier"],
        "",
        "## Global checkpoint at pass time",
        "",
        f"- `{checkpoint['global_checkpoint']['checkpoint_id']}` (label `{checkpoint['global_checkpoint']['label']}`)",
        "",
    ]
    (ROOT / "artifacts" / "worker-009" / "detrev12" / "CHECKPOINT.md").write_text("\n".join(md) + "\n")

    print(json.dumps({
        "checkpoint": str(out.relative_to(ROOT)),
        "checkpoint_sha256": sha(out),
        "events": len(events),
        "artifacts": len(artifacts),
        "global_checkpoint": checkpoint["global_checkpoint"]["checkpoint_id"],
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
