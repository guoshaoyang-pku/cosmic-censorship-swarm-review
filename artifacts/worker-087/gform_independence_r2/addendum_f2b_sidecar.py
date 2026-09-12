#!/usr/bin/env python3
"""W087-GFORM-INDEP-05 addendum: the stale F2b sidecar as an evidence-binding trap.

Measured: schemas/af_scc_c0_vacuum.yaml is b2ab6acb2bbe (rev 13, mtime 00:53:20) but the
live sidecar schemas/af_scc_c0_vacuum.yaml.sha256 (mtime 00:19:14) still advertises the
revoked revision 1bb78ce9 as the file hash. Nine distinct F2b reviewers accepted at
1bb78ce9 before the rev-13 rewrite; all are void at the current pin, while F2b carries only
one accept at b2ab6acb2bbe. F1 and F2a have no such sidecar.

Writes addendum_f2b_sidecar.json, emits two idempotent outbox events (artifact + claim) and
updates events_emitted.json. Usage:
python3 addendum_f2b_sidecar.py --dir <r2-dir> --root <repo>
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))
STAMP = "w087-20260912T0112"
REVOKED = "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508"
TOKENS = ("f2b", "af-scc-c0", "af_scc_c0_vacuum", "af-scc-c0-vac-gen")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def review_accepts_at(root: Path, target: str, instrument_dir: Path) -> dict:
    """F2b accept records whose PRIMARY declared hash binds `target`, using the frozen
    instrument's own target/full-schema/primary-hash rules (no loose token matching)."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("w087_inst", instrument_dir / "audit_gform_independence.py")
    inst = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(inst)
    records, _sources, doc_index = inst.load_corpus(root)
    records = inst.dedupe_by_id(records)
    f2b = inst.PINS["F2b"]
    by_reviewer: dict[str, dict] = {}
    for r in records:
        if inst.norm_verdict(r.get("verdict")) != "accept":
            continue
        if not inst.target_matches(r, f2b):
            continue
        key, ph = inst.primary_hash(r)
        if not ph or not ph.startswith(target[:12]):
            continue
        full, full_reason = inst.is_full_schema_verdict(r, f2b)
        who = str(r.get("reviewer") or r.get("actor") or "unknown")
        cur = {
            "event_id": r.get("_id"),
            "created_at": str(r.get("created_at") or ""),
            "score": r.get("score"),
            "source": r.get("_src"),
            "primary_hash_key": key,
            "full_schema_verdict": full,
            "full_schema_reason": full_reason,
        }
        prev = by_reviewer.get(who)
        if prev is None or (cur["created_at"] or "") >= (prev.get("created_at") or ""):
            by_reviewer[who] = cur
    return by_reviewer


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--root", required=True)
    a = ap.parse_args()
    d = Path(a.dir).resolve()
    root = Path(a.root).resolve()
    sys.path.insert(0, str(root / "research_map"))
    from schemas import validate_event  # noqa: E402

    now = datetime.now(CST).isoformat(timespec="seconds")
    snap = d / "snapshot"
    summary = json.loads((d / "summary.json").read_text())
    report = json.loads((d / "snapshot_run3" / "report.json").read_text())

    sidecar_live = root / "schemas" / "af_scc_c0_vacuum.yaml.sha256"
    sidecar_snap = snap / "schemas" / "af_scc_c0_vacuum.yaml.sha256"
    live_sidecar_text = sidecar_live.read_text().strip() if sidecar_live.is_file() else None
    snap_sidecar_text = sidecar_snap.read_text().strip() if sidecar_snap.is_file() else None
    live_sidecar_hash = live_sidecar_text.split()[0] if live_sidecar_text else None
    canonical_live = sha256_file(root / "schemas" / "af_scc_c0_vacuum.yaml")
    frozen = json.loads((root / "artifacts/formulation/FROZEN.json").read_text())
    frozen_entry = frozen["files"]["schemas/af_scc_c0_vacuum.yaml"]["sha256"]

    revoked_accepts = review_accepts_at(snap, REVOKED[:12], d)
    current_accepts = report["coverage_at_measured_pins"]["F2b"]["full_schema_accept_reviewers"]

    f1f2a_sidecars = {
        "F1": (root / "schemas" / "af_wcc_vacuum.yaml.sha256").exists(),
        "F2a": (root / "schemas" / "af_scc_c2_vacuum.yaml.sha256").exists(),
        "F2b": sidecar_live.is_file(),
    }

    finding = {
        "task_id": "W087-GFORM-INDEP-05",
        "artifact_type": "evidence_binding_addendum",
        "actor": "worker-087",
        "created_at": now,
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "finding": (
            "The live canonical schemas/af_scc_c0_vacuum.yaml is b2ab6acb2bbe (rev 13) and FROZEN "
            f"rev 29 pins b2ab6acb2bbe, but the sidecar schemas/af_scc_c0_vacuum.yaml.sha256 "
            f"(mtime 2026-09-12T00:19:14+08:00) still advertises the revoked revision "
            f"{REVOKED[:12]} as the file hash. A reviewer or tool resolving the schema hash from this "
            "sidecar binds revoked bytes; under primary-hash binding such a verdict is excluded and "
            "cannot contribute to the F2b accept gap."),
        "live_measurement": {
            "sidecar_path": "schemas/af_scc_c0_vacuum.yaml.sha256",
            "sidecar_text": live_sidecar_text,
            "sidecar_sha256": sha256_file(sidecar_live) if sidecar_live.is_file() else None,
            "sidecar_mtime": datetime.fromtimestamp(sidecar_live.stat().st_mtime, CST).isoformat(timespec="seconds") if sidecar_live.is_file() else None,
            "canonical_path": "schemas/af_scc_c0_vacuum.yaml",
            "canonical_sha256": canonical_live,
            "frozen_rev29_entry_sha256": frozen_entry,
            "sidecar_matches_canonical": live_sidecar_hash == canonical_live,
        },
        "snapshot_measurement": {
            "manifest_digest_sha256": json.loads((snap / "MANIFEST.json").read_text())["manifest_digest_sha256"],
            "sidecar_text": snap_sidecar_text,
            "sidecar_sha256": sha256_file(sidecar_snap) if sidecar_snap.is_file() else None,
        },
        "impact": {
            "revoked_hash": REVOKED,
            "distinct_reviewers_accepting_f2b_at_revoked_hash": sorted(revoked_accepts),
            "n_distinct_reviewers_at_revoked_hash": len(revoked_accepts),
            "revoked_hash_accept_records": revoked_accepts,
            "current_f2b_accept_reviewers_at_b2ab6acb2bbe": current_accepts,
            "current_f2b_effective_accept_clusters": summary["per_class"]["F2b"]["effective_independent_full_schema_accept_clusters"],
            "interpretation": (
                f"the historical F2b accept mass ({len(revoked_accepts)} distinct reviewers) sits on the "
                "revoked hash while the current pin has "
                f"{summary['per_class']['F2b']['effective_independent_full_schema_accept_clusters']} cluster; the "
                "stale sidecar is a live trap that can keep sending re-binding reviewers to the revoked revision"),
            "not_proven": "no record is claimed to have used the sidecar; only that the sidecar advertises revoked bytes and is exposed at the canonical schema path",
        },
        "sidecar_presence_by_class": f1f2a_sidecars,
        "severity": "minor",
        "recommendation": (
            "owner (astra-lead-formulation) refreshes or removes schemas/af_scc_c0_vacuum.yaml.sha256; "
            "reviewers of F2b must bind the primary declared hash b2ab6acb2bbe, not the sidecar"),
        "falsifier": (
            "the sidecar is refreshed to b2ab6acb2bbe (or removed) and no post-rev-13 review record binds "
            "1bb78ce9; or it is shown that neither reviewers nor tooling resolve the schema hash from this "
            "sidecar; or the canonical F2b bytes and FROZEN rev-29 pin move."),
        "authority": ("worker evidence only; no review verdict on the schema, no node or gate verdict; "
                      "read-only against canonical inputs"),
    }
    out = d / "addendum_f2b_sidecar.json"
    out.write_text(json.dumps(finding, indent=1, sort_keys=True) + "\n")
    (d / "addendum_f2b_sidecar.json.sha256").write_text(f"{sha256_file(out)}  addendum_f2b_sidecar.json\n")

    ev = f"artifacts/worker-087/gform_independence_r2/addendum_f2b_sidecar.json#{sha256_file(out)[:12]}"
    refs = [
        ev,
        "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
        "schemas/af_scc_c0_vacuum.yaml.sha256",
        "artifacts/formulation/FROZEN.json#815e08079aef",
        f"artifacts/worker-087/gform_independence_r2/snapshot/MANIFEST.json#{json.loads((snap/'MANIFEST.json').read_text())['manifest_digest_sha256'][:12]}",
        "artifacts/worker-087/gform_independence_r2/summary.json",
    ]
    events = [
        {
            "event_id": f"{STAMP}-artifact-addendum-sidecar",
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-087",
            "task_id": "W087-GFORM-INDEP-05",
            "node_id": "F2b",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
            "gate": "G-FORM",
            "artifact_type": "evidence_binding_addendum",
            "path": "artifacts/worker-087/gform_independence_r2/addendum_f2b_sidecar.json",
            "sha256": sha256_file(out),
            "validation_status": "unverified",
            "note": ("stale F2b sidecar advertises revoked 1bb78ce9 while canonical/FROZEN rev 29 are "
                     f"b2ab6acb2bbe; {len(revoked_accepts)} distinct reviewers hold accepts at the revoked hash, "
                     "current pin has 1 cluster"),
            "evidence_refs": refs,
        },
        {
            "event_id": f"{STAMP}-claim-sidecar-trap",
            "event_type": "claim",
            "created_at": now,
            "actor": "worker-087",
            "task_id": "W087-GFORM-INDEP-05",
            "node_id": "F2b",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
            "gate": "G-FORM",
            "conclusion_type": "formal_model",
            "statement": (
                "Evidence-binding addendum (measurement, not a gate verdict): schemas/af_scc_c0_vacuum.yaml.sha256 "
                f"advertises revoked revision {REVOKED[:12]} while the canonical schema and the FROZEN rev-29 entry "
                "are b2ab6acb2bbe. "
                f"{len(revoked_accepts)} distinct reviewers "
                f"({', '.join(sorted(revoked_accepts))}) hold F2b accept records whose primary declared hash binds "
                "the revoked revision; all are void at the current pin, and F2b currently has "
                f"{summary['per_class']['F2b']['effective_independent_full_schema_accept_clusters']} effective accept "
                "cluster (worker-061). The stale sidecar is a live binding trap at the canonical schema path: a "
                "re-binding reviewer that resolves the hash from it binds revoked bytes. F1 and F2a have no such sidecar."),
            "assumptions": [
                "the sidecar is not covered by the FROZEN files map and is therefore not part of the pinned artifact set",
                "reviewers are expected to bind the declared sha256 in the review record, which is what the coverage audit measures",
                "the revoked-hash accept list is deduped per reviewer over the frozen snapshot corpus",
            ],
            "falsifier": finding["falsifier"],
            "evidence_refs": refs,
            "artifact_refs": [ev],
        },
    ]

    outbox = root / "comms" / "outbox" / "worker-087.jsonl"
    existing = set()
    if outbox.exists():
        for line in outbox.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line).get("event_id"))
            except ValueError:
                continue
    lines, emitted, skipped = [], [], []
    for e in events:
        validate_event(e)
        if e["event_id"] in existing:
            skipped.append(e["event_id"])
            continue
        line = json.dumps(e, sort_keys=True)
        lines.append(line)
        emitted.append({"event_id": e["event_id"], "event_type": e["event_type"], "sha256": hashlib.sha256(line.encode()).hexdigest()})
    if lines:
        with outbox.open("a") as fh:
            fh.write("\n".join(lines) + "\n")

    rec_path = d / "events_emitted.json"
    rec = json.loads(rec_path.read_text())
    rec.setdefault("addendum", {})
    rec["addendum"] = {
        "at": now,
        "artifact": "addendum_f2b_sidecar.json",
        "artifact_sha256": sha256_file(out),
        "event_ids": [e["event_id"] for e in emitted] or [e["event_id"] for e in events],
        "event_sha256": [e["sha256"] for e in emitted],
        "skipped_already_present": skipped,
        "revoked_hash": REVOKED,
        "n_reviewers_accepting_at_revoked_hash": len(revoked_accepts),
        "current_f2b_clusters": summary["per_class"]["F2b"]["effective_independent_full_schema_accept_clusters"],
    }
    rec_path.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
    (d / "events_emitted.json.sha256").write_text(f"{sha256_file(rec_path)}  events_emitted.json\n")

    print(json.dumps({
        "addendum": str(out),
        "sidecar_matches_canonical": finding["live_measurement"]["sidecar_matches_canonical"],
        "n_reviewers_accepting_at_revoked_hash": len(revoked_accepts),
        "emitted": [e["event_id"] for e in emitted],
        "skipped": skipped,
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
