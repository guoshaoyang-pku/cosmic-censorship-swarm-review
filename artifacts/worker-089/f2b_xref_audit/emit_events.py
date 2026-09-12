#!/usr/bin/env python3
"""Emit worker-089 outbox events for W089-F2B-XREF-01, schema-validated locally.

Reads artifacts/worker-089/f2b_xref_audit/xref_report.json, builds status/artifact/review
events, validates each with research_map.schemas.validate_event, and appends them to
comms/outbox/worker-089.jsonl. Exit 1 if any event is invalid (nothing is written).

Usage: python3 emit_events.py [--dry-run]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event, SchemaError  # noqa: E402

CST = timezone(timedelta(hours=8))
OUT = ROOT / "comms" / "outbox" / "worker-089.jsonl"
AUD = ROOT / "artifacts" / "worker-089" / "f2b_xref_audit"
REPORT = AUD / "xref_report.json"
SCRIPT = AUD / "check_f2b_xref.py"
README = AUD / "README.md"


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ref(path: str, digest: str) -> str:
    return f"{path}#{digest[:12]}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    r = json.loads(REPORT.read_text())
    ts = now()
    stamp = ts.replace("-", "").replace(":", "")[:15]
    tag = f"w089-{stamp}"
    sha_report, sha_script = sha(REPORT), sha(SCRIPT)
    sha_readme = sha(README) if README.is_file() else None
    snap = sorted((AUD / "pinned").glob("af_scc_c0_vacuum.*.yaml"))
    sha_snap = sha(snap[0]) if snap else None
    target = r["target_pin_sha256"]
    h12 = target[:12]

    events = []
    events.append({
        "event_id": f"{tag}-claim",
        "event_type": "status",
        "created_at": ts,
        "actor": "worker-089",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "status": "active",
        "hours": 0.4,
        "task_id": "W089-F2B-XREF-01",
        "summary": (
            "No assignment card existed for worker-089; took one bounded class-bound task: "
            "independent cross-artifact integrity audit of canonical F2b (AF-SCC-C0-VAC-GEN) at the "
            f"pinned hash {h12}, with 10 machine checks, 7 planted-defect controls + a no-false-positive "
            "control, and a 120 s hash-stability window. Mechanical scope only; does not claim a gate verdict."
        ),
        "evidence_refs": [ref("research_map/ASTRA_HANDOFF.md", sha(ROOT / "research_map/ASTRA_HANDOFF.md")),
                          ref("schemas/af_scc_c0_vacuum.yaml", target)],
        "next_falsifier": r["next_falsifier"],
    })
    for path, digest, atype, note in (
        ("artifacts/worker-089/f2b_xref_audit/check_f2b_xref.py", sha_script, "checker_code",
         "Deterministic stdlib+PyYAML checker; --controls plants 7 defects in-memory and writes them to controls/."),
        ("artifacts/worker-089/f2b_xref_audit/xref_report.json", sha_report, "audit_report",
         f"Result at pinned F2b hash {h12}: verdict={r['verdict']}, hard={len(r['hard_findings'])}, "
         f"soft={len(r['soft_findings'])}, controls_ok={all(c['status'] == 'pass' for c in r['controls'])}."),
    ):
        events.append({
            "event_id": f"{tag}-art-{atype}",
            "event_type": "artifact",
            "created_at": ts,
            "actor": "worker-089",
            "node_id": "F2b",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "gate": "G-FORM",
            "task_id": "W089-F2B-XREF-01",
            "artifact_type": atype,
            "path": path,
            "sha256": digest,
            "validation_status": "unverified",
            "note": note,
            "evidence_refs": [ref(path, digest), ref("schemas/af_scc_c0_vacuum.yaml", target)],
            "next_falsifier": r["next_falsifier"],
        })
    if sha_readme:
        events.append({
            "event_id": f"{tag}-art-readme",
            "event_type": "artifact",
            "created_at": ts,
            "actor": "worker-089",
            "node_id": "F2b",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "gate": "G-FORM",
            "task_id": "W089-F2B-XREF-01",
            "artifact_type": "summary",
            "path": "artifacts/worker-089/f2b_xref_audit/README.md",
            "sha256": sha_readme,
            "validation_status": "unverified",
            "note": "One-page summary: checks, controls, stability timeline, scope limits, re-run command.",
            "evidence_refs": [ref("artifacts/worker-089/f2b_xref_audit/README.md", sha_readme)],
            "next_falsifier": r["next_falsifier"],
        })
    if sha_snap:
        events.append({
            "event_id": f"{tag}-art-pinned-snapshot",
            "event_type": "artifact",
            "created_at": ts,
            "actor": "worker-089",
            "node_id": "F2b",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "gate": "G-FORM",
            "task_id": "W089-F2B-XREF-01",
            "artifact_type": "pinned_snapshot",
            "path": str(snap[0].relative_to(ROOT)),
            "sha256": sha_snap,
            "validation_status": "unverified",
            "note": f"Byte-exact copy of the audited canonical revision ({h12}); lets the report be reproduced after drift.",
            "evidence_refs": [ref(str(snap[0].relative_to(ROOT)), sha_snap)],
            "next_falsifier": "Snapshot hash differs from the report's target_pin_sha256: the report is mis-bound.",
        })
    findings = [
        f"Mechanical checks at pinned hash {h12}: " +
        ", ".join(f"{c['check_id']}={c['status']}" for c in r["checks"]) + ".",
        "Controls: " + ", ".join(f"{c['control_id']}={c['status']}" for c in r["controls"]) + ".",
        "Scope: mechanical cross-artifact integrity and class identity only; NOT a semantic sufficiency "
        "review and NOT a G-FORM gate accept. Worker-089 authored no canonical artifact.",
    ]
    if r.get("stability"):
        s = r["stability"]
        findings.append(
            f"Stability window {s['window_seconds']}s/{s['interval_seconds']}s: drift_detected={s['drift_detected']}; "
            + "; ".join(f"{k.split('/')[-1]}:{v['distinct_hashes']}h" for k, v in s["per_file"].items()) + "."
        )
    findings += list(r.get("informational", []))
    events.append({
        "event_id": f"{tag}-review",
        "event_type": "review",
        "created_at": ts,
        "actor": "worker-089",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "task_id": "W089-F2B-XREF-01",
        "target_id": f"schemas/af_scc_c0_vacuum.yaml#{h12}",
        "artifact": "schemas/af_scc_c0_vacuum.yaml",
        "artifact_sha256": target,
        "reviewer": "worker-089",
        "independence": "worker-089 authored no canonical artifact and no prior F2b review; the checker's 7 planted-defect controls are included so a pass is controlled.",
        "review_kind": "mechanical_cross_artifact_integrity",
        "counts_as_gate_accept": False,
        "scope": "mechanical xref/class-identity only; no semantic adjudication",
        "verdict": r["verdict"],
        "score": 4.0 if r["verdict"] == "accept" else 2.0,
        "hard_failures": list(r["hard_findings"]) if r["verdict"] == "revise" else [],
        "findings": findings,
        "evidence_refs": [ref("artifacts/worker-089/f2b_xref_audit/xref_report.json", sha_report),
                          ref("schemas/af_scc_c0_vacuum.yaml", target)],
        "next_falsifier": r["next_falsifier"],
    })
    events.append({
        "event_id": f"{tag}-done",
        "event_type": "status",
        "created_at": ts,
        "actor": "worker-089",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "status": "done",
        "hours": 0.4,
        "task_id": "W089-F2B-XREF-01",
        "summary": (
            f"Worker lifecycle complete (completion claim only; not a node done and not a gate verdict). "
            f"One class-bound task delivered: {r['verdict']} at pinned F2b {h12}. Artifacts under "
            "artifacts/worker-089/f2b_xref_audit/; checkpoint runtime/state/w089_checkpoint_1.json."
        ),
        "evidence_refs": [ref("artifacts/worker-089/f2b_xref_audit/xref_report.json", sha_report)],
        "next_falsifier": r["next_falsifier"],
    })

    bad = []
    for e in events:
        try:
            validate_event(e)
        except SchemaError as exc:
            bad.append((e.get("event_id"), str(exc)))
    if bad:
        for bid, msg in bad:
            print(f"INVALID {bid}: {msg}", file=sys.stderr)
        return 1
    if args.dry_run:
        print(json.dumps(events, indent=2, default=str))
        return 0
    with OUT.open("a") as f:
        for e in events:
            f.write(json.dumps(e, sort_keys=True) + "\n")
    print(f"wrote {len(events)} events -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
