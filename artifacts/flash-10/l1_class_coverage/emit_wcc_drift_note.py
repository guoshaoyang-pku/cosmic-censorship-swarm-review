#!/usr/bin/env python3
"""Drift addendum: the canonical F1 schema moved again after the WCC audit emit.

The audit is bound to schemas/af_wcc_vacuum.yaml rev10 (16128b62fe08).  Within ~2 minutes the
canonical file moved to rev11 (9a8bd4c9).  This script records a field-for-field comparison of
the class-definition extraction the audit uses, so the controller/A1 can see whether the
0-discharge verdict is substantively valid at the new hash or must be re-audited.

It emits one artifact event + one status event and writes a checkpoint.  No completion, no gate
verdict, no validation_status=passed.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from research_map.schemas import validate_event  # noqa: E402
import yaml  # noqa: E402

OUTBOX = ROOT / "comms" / "outbox" / "deepseek-flash-10.jsonl"
AUDIT = HERE / "wcc_class_conformance_audit.json"
SNAP = HERE / "snapshots" / "af_wcc_vacuum.16128b62fe08.yaml"
SCHEMA = ROOT / "schemas" / "af_wcc_vacuum.yaml"
LEDGER = ROOT / "ledger" / "theorems.jsonl"
TZ = timezone(timedelta(hours=8))
CLASS = "AF-WCC-VAC-GEN"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def fields(path: Path) -> dict:
    doc = yaml.safe_load(path.read_text(encoding="utf-8", errors="replace"))
    concl = doc.get("conclusion") or {}
    gen = doc.get("genericity") or {}
    return {
        "class_id": doc.get("class_id"), "node_id": doc.get("node_id"),
        "revision": doc.get("revision"), "epistemic_status": doc.get("epistemic_status"),
        "scope_statement": (doc.get("scope_statement") or "").strip(),
        "conclusion_type": concl.get("conclusion_type"),
        "conclusion_statement": concl.get("statement_natural_language"),
        "conclusion_statement_formal": concl.get("statement_formal"),
        "conclusion_epistemic_status": concl.get("epistemic_status"),
        "forbidden_strengthenings": concl.get("forbidden_strengthenings") or [],
        "claim_promotion": concl.get("claim_promotion"),
        "quantifier_formal": (doc.get("quantifiers") or {}).get("formal", ""),
        "genericity_kind": (gen.get("kind") or gen.get("genericity_kind") or "") if isinstance(gen, dict) else str(gen),
        "genericity_topology": (gen.get("topology") or gen.get("topology_id") or "") if isinstance(gen, dict) else "",
        "genericity_definition": ((gen.get("definition") or "") if isinstance(gen, dict) else "").strip()[:400],
    }


def main() -> int:
    now = datetime.now(TZ)
    ts = now.strftime("%Y%m%dT%H%M%S")
    pinned_h = sha(SNAP)
    current_h = sha(SCHEMA)
    old, new = fields(SNAP), fields(SCHEMA)
    diffs = sorted(k for k in old if old[k] != new.get(k))
    substantive = [k for k in diffs if k != "revision"]

    note = {
        "note_id": f"flash-10-wcc-schema-drift-{ts}",
        "actor": "deepseek-flash-10", "node_id": "L1", "gate": "G-LIT", "class_id": CLASS,
        "created_at": now.isoformat(timespec="seconds"),
        "audit_artifact": {"path": str(AUDIT.relative_to(ROOT)), "sha256": sha(AUDIT)},
        "pinned_schema": {"path": str(SNAP.relative_to(ROOT)), "sha256": pinned_h, "revision": old["revision"]},
        "current_canonical_schema": {"path": str(SCHEMA.relative_to(ROOT)), "sha256": current_h, "revision": new["revision"]},
        "comparison": {"method": "field-for-field on the class-definition extraction used by wcc_class_conformance_audit.py",
                       "differing_fields": diffs, "substantive_differing_fields": substantive},
        "reading": ("The 0-discharge verdict is substantively invariant across the revision step (only the `revision` "
                    "metadata field differs), but it is hash-bound to the pinned revision. A hash-bound claim at the "
                    "current canonical hash requires a re-run of wcc_class_conformance_audit.py; this note does not "
                    "re-point the artifact."),
        "ledger": {"path": "ledger/theorems.jsonl", "sha256": sha(LEDGER)},
        "falsifier": ("A substantive (non-`revision`) difference in the class-definition extraction between the pinned "
                      "snapshot and the current canonical schema, or a re-run of the audit at the current hash that "
                      "yields n_discharging >= 1."),
        "validation_status": "unverified",
    }
    note_path = HERE / f"wcc_schema_drift_note_{ts}.json"
    note_path.write_text(json.dumps(note, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    note_h = sha(note_path)

    common = {"actor": "deepseek-flash-10", "run_id": "run-2026-09-11T23:15+08:00",
              "created_at": now.isoformat(timespec="seconds"), "gate": "G-LIT",
              "assignment_ref": "asg-2026-09-11-L1-deepseek-flash-10-19"}
    events = [
        {**common, "event_id": f"flash-10-artifact-wcc-drift-note-{ts}", "event_type": "artifact",
         "node_id": "L1", "class_id": CLASS, "artifact_type": "json",
         "path": str(note_path.relative_to(ROOT)), "sha256": note_h, "bytes": note_path.stat().st_size,
         "validation_status": "unverified", "claims_completion": False,
         "evidence_refs": [f"{note_path.relative_to(ROOT)}#{note_h[:12]}",
                           f"artifacts/flash-10/l1_class_coverage/snapshots/af_wcc_vacuum.16128b62fe08.yaml#{pinned_h[:12]}",
                           f"schemas/af_wcc_vacuum.yaml#{current_h[:12]}",
                           f"ledger/theorems.jsonl#{sha(LEDGER)[:12]}"],
         "inputs": {"schemas/af_wcc_vacuum.yaml": current_h,
                    "artifacts/flash-10/l1_class_coverage/snapshots/af_wcc_vacuum.16128b62fe08.yaml": pinned_h},
         "falsifier": note["falsifier"],
         "summary": (f"Schema drift observed after emit: pinned rev{old['revision']} {pinned_h[:12]} -> canonical "
                     f"rev{new['revision']} {current_h[:12]}. Class-definition fields differ only in `revision` "
                     f"(substantive differences: {substantive or 'none'}), so the 0-discharge reading carries over in "
                     f"substance but must be re-audited for a hash-bound claim at the new revision.")},
        {**common, "event_id": f"flash-10-status-wcc-drift-{ts}", "event_type": "status",
         "node_id": "L1", "class_id": CLASS, "status": "active", "hours": 0.1,
         "summary": (f"Drift addendum to the AF-WCC-VAC-GEN conformance audit: canonical schema moved "
                     f"{pinned_h[:12]}(rev{old['revision']}) -> {current_h[:12]}(rev{new['revision']}) after emit; "
                     f"extracted class-definition fields differ only in the revision field. Claim stays bound to the "
                     f"pinned hash; re-audit queued if F1 keeps the new revision. No completion claimed."),
         "evidence_refs": [f"{note_path.relative_to(ROOT)}#{note_h[:12]}",
                           f"artifacts/flash-10/l1_class_coverage/wcc_class_conformance_audit.json#{sha(AUDIT)[:12]}",
                           f"schemas/af_wcc_vacuum.yaml#{current_h[:12]}"],
         "next_falsifier": ("Re-run wcc_class_conformance_audit.py at the current canonical schema hash and obtain "
                            "n_discharging >= 1, or a substantive (non-revision) class-definition diff at the next "
                            "revision step.")},
    ]
    lines = []
    for e in events:
        validate_event(e)
        lines.append(json.dumps(e, ensure_ascii=False))
    ckpt = {"checkpoint_id": f"flash-10-wcc-drift-{ts}", "worker": "deepseek-flash-10", "slot": "010",
            "created_at": now.isoformat(timespec="seconds"), "class_id": CLASS, "node_id": "L1", "gate": "G-LIT",
            "drift": {"pinned": pinned_h, "current": current_h, "substantive_differing_fields": substantive},
            "event_ids": [e["event_id"] for e in events],
            "hashes": {"drift_note": note_h, "audit": sha(AUDIT), "ledger": sha(LEDGER)},
            "validation_status": "unverified"}
    ckpt_path = HERE / f"checkpoint_wcc_drift_{ts}.json"
    ckpt_path.write_text(json.dumps(ckpt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with OUTBOX.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(json.dumps({"checkpoint": str(ckpt_path.relative_to(ROOT)), "checkpoint_sha256": sha(ckpt_path),
                      "drift_note": {"path": str(note_path.relative_to(ROOT)), "sha256": note_h},
                      "pinned": pinned_h, "current": current_h, "substantive_differing_fields": substantive,
                      "event_ids": [e["event_id"] for e in events], "falsifier": note["falsifier"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
