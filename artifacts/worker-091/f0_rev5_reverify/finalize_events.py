#!/usr/bin/env python3
"""Emit worker-091's F0 rev5 re-verification events and worker checkpoint.

Reads the final artifacts produced by verify_rev5.py, re-measures the canonical F0 hash at
emit time (binding check), validates every event through research_map/comms.normalize_event
and research_map/schemas.validate_event with ZERO auto-filled fields, appends to
comms/outbox/worker-091.jsonl (idempotent), and writes runtime/state/w091_checkpoint_f0rev5.json.

Never calls the controller-only ingest/checkpoint tools. Exit 3 = binding mismatch (nothing emitted).
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "research_map"))
import comms  # noqa: E402
import schemas  # noqa: E402

CST = timezone(timedelta(hours=8))
ACTOR = "worker-091"
OUTBOX = REPO / "comms/outbox/worker-091.jsonl"
STATE = REPO / "runtime/state"
F0_REL = "research_map/formulation_taxonomy.yaml"
CLASS_IDS = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]


def now_iso() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def event_hash(e: dict) -> str:
    return hashlib.sha256(json.dumps(e, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main() -> int:
    results = json.loads((HERE / "results.json").read_text())
    manifest = json.loads((HERE / "MANIFEST.json").read_text())
    validation = json.loads((HERE / "validation.json").read_text())

    measured = sha256_file(REPO / F0_REL)
    bound = results["target"]["sha256"]
    if measured != bound:
        print(json.dumps({"status": "BINDING_MISMATCH", "bound": bound, "measured": measured}))
        return 3
    if not validation.get("ok"):
        print(json.dumps({"status": "VALIDATION_FAILED"}))
        return 3

    ts = datetime.now(CST).strftime("%Y%m%dT%H%M")
    results_sha = sha256_file(HERE / "results.json")
    manifest_sha = sha256_file(HERE / "MANIFEST.json")
    snap_sha = sha256_file(HERE / "f0_rev5_snapshot.yaml")
    fals = results["falsifier"]
    ev = results["evidence_refs"]

    summary = (
        "F0 rev5 named-blocker re-verification at canonical research_map/formulation_taxonomy.yaml "
        f"sha256 {bound[:12]} (rev5, {results['target']['bytes']} B). Previous worker-091 run "
        "(f0_blocking_verify, revise 3.5 at 276009f4) recorded the falsifier 're-run K2-K5 at the new "
        "hash'; this run executes it and supplies an independent non-author verdict at the current pin "
        "(lead-audit B-GF0-1 asks for two). Result: accept 4.0, no blocking content defect among the "
        "measured items. K2/K3/K4/K5 named blockers REFUTED at rev5 (set-based sentence only survives as "
        "the labelled supersedes quotation line 84; no 'equivalently' token; comeager bound in all four "
        "conclusions; C2/C0 schema_owner point at F2a/F2b canonical schemas). K1a byte divergence is the "
        "declared two-artifact split (FROZEN rev28, mirrors NONE); K1b overwrite discharge REFUTED and "
        "left to controller REC-1/REC-2. K6/K7 non-blocking residuals; K8 shows FROZEN rev28 pins the live "
        "F0/F0-R/schema hashes (worker-038 stale-pin blocker discharged at manifest level); K9 no duplicate "
        "keys. Detector controls fire on injected mutants. Pre/post digests equal; no input drifted."
    )
    next_falsifier = (
        "An F0 accept that cites any hash other than "
        f"{bound}; or a mirror-equality claim treating {bound[:12]} and "
        f"{results['publication_counterpart']['sha256'][:12]} as one artifact; or a re-run of "
        "artifacts/worker-091/f0_rev5_reverify/verify_rev5.py that returns exit 3 (drift => UNMEASURED). "
        + fals
    )

    status_event = {
        "event_id": f"w091-{ts}-f0rev5-status",
        "event_type": "status",
        "created_at": now_iso(),
        "actor": ACTOR,
        "node_id": "F0",
        "gate": "G-F0",
        "class_id": CLASS_IDS[0],
        "class_ids": CLASS_IDS,
        "status": "active",
        "hours": 0.4,
        "summary": summary,
        "evidence_refs": ev + [f"artifacts/worker-091/f0_rev5_reverify/results.json#{results_sha[:12]}"],
        "next_falsifier": next_falsifier,
    }

    artifact_event = {
        "event_id": f"w091-{ts}-f0rev5-artifact",
        "event_type": "artifact",
        "created_at": now_iso(),
        "actor": ACTOR,
        "node_id": "F0",
        "gate": "G-F0",
        "class_id": CLASS_IDS[0],
        "class_ids": CLASS_IDS,
        "artifact_type": "f0_rev5_named_blocker_reverification",
        "path": "artifacts/worker-091/f0_rev5_reverify/results.json",
        "sha256": results_sha,
        "validation_status": "unverified",
        "evidence_refs": ev + [f"artifacts/worker-091/f0_rev5_reverify/MANIFEST.json#{manifest_sha[:12]}"],
        "falsifier": fals,
    }

    review_event = {
        "event_id": f"w091-{ts}-f0rev5-review",
        "event_type": "review",
        "created_at": now_iso(),
        "actor": ACTOR,
        "target_id": "F0",
        "reviewer": ACTOR,
        "reviewer_independence": {
            "authored_F0": False,
            "author_of_record": "deepseek-flash-01",
            "shared_text_with_reviewed_artifact": False,
            "independent_non_author_verdict_at_hash": True,
        },
        "verdict": "accept",
        "score": 4.0,
        "gate": "G-F0",
        "class_id": CLASS_IDS[0],
        "class_ids": CLASS_IDS,
        "artifact": F0_REL,
        "reviewed_sha256": results["reviewed_sha256"],
        "reviewed_bytes": {
            "F0": results["target"]["bytes"],
            "F0-R": results["publication_counterpart"]["bytes"],
        },
        "hard_failures": [],
        "blocking_open_items": [
            "K1b: FROZEN rev28 f0_mirror_adjudication_request is disposition-recorded-pending-controller-adjudication "
            "(REC-1 recommended). This accept is conditional on REC-1; REC-2 rewrites the artifact and voids it."
        ],
        "findings": [
            "K1a CONFIRMED_FACT (non-blocking): canonical 0abb9ed8 byte-divergent from authoring d7419b4e; FROZEN rev28 logical_artifacts declares two distinct logical artifacts, mirrors NONE, and refuses byte-identity as destructive. K8 confirms rev28 pins both live hashes; worker-038's rev26 stale-pin blocker is discharged at manifest level.",
            "K1b PENDING CONTROLLER: the 'publish one over the other' discharge method is REFUTED; underlying item is controller disposition REC-1/REC-2, not a schema-text defect.",
            "K2 REFUTED at rev5: the exact set-based sentence 'every future-inextendible causal geodesic contained in J-(I+) is complete' appears in NO class conclusion; its only surviving occurrence is the labelled historical quotation in class_scope_adjudication.supersedes.wcc_text_before (snapshot line 84); the registered SET variant is present.",
            "K3 REFUTED at rev5: 'equivalently' appears in no class conclusion; SPH is restated as the single-q tail predicate. Residual non-blocking: the line-418 gloss 'hidden behind an event horizon' is an unsourced physical restatement of the class's own no-visible-singularity predicate, not a J-(I+) completeness equivalence.",
            "K4 REFUTED at rev5: all four class conclusions carry a comeager quantifier bound before the data; the D3 resolution's ALL FOUR claim is mechanically supported.",
            "K5 REFUTED at rev5: C2 schema_owner -> F2a (schemas/af_scc_c2_vacuum.yaml), C0 -> F2b (schemas/af_scc_c0_vacuum.yaml); both files exist and are FROZEN-pinned; the legacy aggregator token remains only in the rev5 revision note (line 17) describing the fix.",
            "K6 CONFIRMED non-blocking (pre-existing): genericity_topology declared in field_vocabulary, carried by no class axes block.",
            "K7 CONFIRMED non-blocking: AF-WCC-SCALAR-SPH axes.genericity_kind=unresolved conflicts with its comeager conclusion; confirms lead-audit O-GF0-1.",
            "K9 REFUTED: no duplicate YAML mapping keys at rev5. Controls: the K2/K3 detectors fire on injected mutants and stay quiet on the real bytes, so 'fixed' is not a false negative.",
            "No canonical/authoring file was modified; pre/post digests equal; snapshot byte-identical; validation.json's 7 evidence refs hash-match disk.",
        ],
        "conditions": results["conditions"],
        "counts_as_full_schema_verdict": False,
        "counts_as_independent_second_verdict": True,
        "counts_as_independent_non_author_verdict": True,
        "counting_note": results["counting_note"],
        "evidence_refs": ev + [
            f"artifacts/worker-091/f0_rev5_reverify/results.json#{results_sha[:12]}",
            f"artifacts/worker-091/f0_rev5_reverify/f0_rev5_snapshot.yaml#{snap_sha[:12]}",
            "reviews/G-F0-final-verify.json",
        ],
        "falsifier": fals,
    }

    events = [status_event, artifact_event, review_event]
    existing_ids = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing_ids.add(json.loads(line).get("event_id"))
            except json.JSONDecodeError:
                pass

    validation_records = []
    to_append = []
    for e in events:
        norm = comms.normalize_event(e, source=str(OUTBOX))
        filled = norm.pop("_normalized", {})
        norm.pop("_source_file", None)
        try:
            schemas.validate_event(norm)
            schema_valid, schema_err = True, None
        except Exception as exc:  # SchemaError
            schema_valid, schema_err = False, str(exc)
        rec = {
            "event_id": e["event_id"],
            "event_type": e["event_type"],
            "schema_valid": schema_valid,
            "schema_error": schema_err,
            "auto_filled_fields": sorted(filled.keys()),
            "already_present": e["event_id"] in existing_ids,
            "event_sha256_12": event_hash(norm)[:12],
            "appended": False,
        }
        if schema_valid and not filled and not rec["already_present"]:
            to_append.append(norm)
            rec["appended"] = True
        validation_records.append(rec)

    if to_append:
        with OUTBOX.open("a") as fh:
            for e in to_append:
                fh.write(json.dumps(e, sort_keys=True) + "\n")

    checkpoint = {
        "checkpoint_id": f"w091-cp-f0rev5-{ts}",
        "actor": ACTOR,
        "created_at": now_iso(),
        "role": "bounded execution worker; one class-bound task then exit",
        "task": "Re-test the named F0 blocking findings K1a/K1b/K2-K5 at canonical F0 rev5, closing the previous worker-091 falsifier and supplying an independent non-author verdict at the pin.",
        "class_ids": CLASS_IDS,
        "node_id": "F0",
        "gate": "G-F0",
        "target": {
            "path": F0_REL,
            "sha256": bound,
            "bytes": results["target"]["bytes"],
            "revision": 5,
        },
        "verdict": results["verdict"],
        "score": results["score"],
        "content_blockers_standing": results["content_blockers_standing"],
        "integrity_failures": results["verification_integrity_failures"],
        "drift": results["drift"]["drifted"],
        "open_controller_item": "FROZEN rev28 f0_mirror_adjudication_request: REC-1 (recommended) or REC-2",
        "artifacts": {
            "artifacts/worker-091/f0_rev5_reverify/results.json": results_sha,
            "artifacts/worker-091/f0_rev5_reverify/MANIFEST.json": manifest_sha,
            "artifacts/worker-091/f0_rev5_reverify/f0_rev5_snapshot.yaml": snap_sha,
            "artifacts/worker-091/f0_rev5_reverify/validation.json": sha256_file(HERE / "validation.json"),
            "artifacts/worker-091/f0_rev5_reverify/verify_rev5.py": sha256_file(HERE / "verify_rev5.py"),
        },
        "manifest_files": manifest.get("files", {}),
        "events_emitted": [e["event_id"] for e in events],
        "event_validation": validation_records,
        "authority": "worker checkpoint; no status=done, no validation_status=passed, no gate verdict; controller ingests outbox and decides",
        "next_falsifier": next_falsifier,
        "evidence_refs": ev,
    }
    STATE.mkdir(parents=True, exist_ok=True)
    cp_path = STATE / "w091_checkpoint_f0rev5.json"
    cp_path.write_text(json.dumps(checkpoint, indent=1) + "\n")
    with (STATE / "w091_checkpoints.jsonl").open("a") as fh:
        fh.write(json.dumps({
            "checkpoint_id": checkpoint["checkpoint_id"],
            "created_at": checkpoint["created_at"],
            "actor": ACTOR,
            "node_id": "F0",
            "gate": "G-F0",
            "verdict": results["verdict"],
            "score": results["score"],
            "target_sha256": bound,
            "path": str(cp_path.relative_to(REPO)),
            "sha256": sha256_file(cp_path),
        }) + "\n")

    print(json.dumps({
        "status": "EMITTED",
        "bound_sha256": bound,
        "events": validation_records,
        "checkpoint": str(cp_path.relative_to(REPO)),
        "checkpoint_sha256_12": sha256_file(cp_path)[:12],
    }, indent=1))
    ok = all(r["schema_valid"] and not r["auto_filled_fields"] for r in validation_records)
    return 0 if ok else 3


if __name__ == "__main__":
    raise SystemExit(main())
