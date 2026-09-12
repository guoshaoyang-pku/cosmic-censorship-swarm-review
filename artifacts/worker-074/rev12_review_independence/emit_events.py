#!/usr/bin/env python3
"""Emit W074-A1-REV12-INDEP-01 events to comms/outbox/worker-074.jsonl and checkpoint 4.

Append-only; every event is validated with research_map/schemas.py::validate_event before
it is written.  Worker events cannot set a gate verdict or node status.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CST = timezone(timedelta(hours=8))
OUT_DIR = Path(__file__).resolve().parent
AGENT = "worker-074"
TASK_ID = "W074-A1-REV12-INDEP-01"
CLASS_ID = "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
NODE_ID = "F0,F1,F2a,F2b,L0"
GATE = "G-AUDIT"


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_validator():
    spec = importlib.util.spec_from_file_location("map_schemas", ROOT / "research_map" / "schemas.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["map_schemas"] = mod
    spec.loader.exec_module(mod)
    return mod.validate_event


def main() -> int:
    report_p = OUT_DIR / "report.json"
    script_p = OUT_DIR / "audit_rev12_review_independence.py"
    readme_p = OUT_DIR / "README.md"
    manifest_p = OUT_DIR / "snapshot_manifest.json"
    raw_p = OUT_DIR / "raw" / "scan_output.txt"
    for p in (report_p, script_p, readme_p, manifest_p, raw_p):
        if not p.is_file():
            print(json.dumps({"error": f"missing artifact {p}"}))
            return 2

    report = json.loads(report_p.read_text())
    h = {p.name: sha256_file(p) for p in (report_p, script_p, readme_p, manifest_p, raw_p)}
    target_summary = {
        t: {
            "sha256": v["measured"]["sha256"],
            "controller_full_accepts": len(v["controller_scan"]["full_accept_files"]),
            "controller_distinct_accept_reviewers": v["controller_scan"]["distinct_full_accept_reviewers"],
            "effective_accept_clusters": v["census"]["effective_accept_clusters"],
            "clean_accept_clusters": v["census"]["clean_accept_clusters"],
            "criterion": v["census"]["criterion_two_clean_independent_accepts"],
            "blocking_conflicts": len(v["blocking_conflicts_at_hash"]),
        }
        for t, v in report["targets"].items()
    }
    map_sha = sha256_file(ROOT / "research_map" / "research_map.json")
    frozen_sha = sha256_file(ROOT / "artifacts" / "formulation" / "FROZEN.json")
    corpus_digest = report["corpus"]["corpus_digest_sha256"]

    stamp = datetime.now(CST).strftime("%Y%m%dT%H%M%S")
    created = now()
    ref_report = f"artifacts/worker-074/rev12_review_independence/report.json#{h['report.json'][:12]}"
    ref_script = f"artifacts/worker-074/rev12_review_independence/audit_rev12_review_independence.py#{h['audit_rev12_review_independence.py'][:12]}"
    ref_readme = f"artifacts/worker-074/rev12_review_independence/README.md#{h['README.md'][:12]}"
    ref_manifest = f"artifacts/worker-074/rev12_review_independence/snapshot_manifest.json#{h['snapshot_manifest.json'][:12]}"
    ref_raw = f"artifacts/worker-074/rev12_review_independence/raw/scan_output.txt#{h['scan_output.txt'][:12]}"
    ref_map = f"research_map/research_map.json#{map_sha[:12]}"
    ref_frozen = f"artifacts/formulation/FROZEN.json#{frozen_sha[:12]}"

    falsifier = report["falsifier"]
    next_falsifier = (
        "Re-run artifacts/worker-074/rev12_review_independence/audit_rev12_review_independence.py: "
        "the census is void if any measured target sha256 (F0 0abb9ed8, F1 cce9c601, F2a 5476a3f2, "
        "F2b 55d0a1ea, L0 a1674f09) differs, if the same corpus digest 6eb16416389600f7 yields "
        "different clusters, if any control C1-C4 fails, or if a counted clean accept is shown to "
        "be a re-send of another reviewer's text."
    )

    events = [
        {
            "event_id": f"w074-{stamp}-a1rev12indep-status",
            "event_type": "status",
            "created_at": created,
            "actor": AGENT,
            "task_id": TASK_ID,
            "class_id": CLASS_ID,
            "class_ids": CLASS_IDS,
            "node_id": NODE_ID,
            "gate": GATE,
            "status": "active",
            "hours": 0.35,
            "summary": (
                "Took one class-bound task with no inbox card: W074-A1-REV12-INDEP-01, A1 independence census of the "
                "rev12 review corpus at the measured canonical hashes F0 0abb9ed8 / F1 cce9c601 / F2a 5476a3f2 / "
                "F2b 55d0a1ea / L0 a1674f09, replaying the controller scan rule (astra_lifecycle.py::review_coverage) "
                "and deduplicating bound full accepts by reviewer identity, review-document bytes, findings-text "
                "shingles and evidence channel. Result at the pinned snapshot (corpus digest 6eb16416389600f7): "
                "F0 has 4 clean independent accepts (2-accept criterion MET on the review-count axis); F1 has 1 "
                "controller accept but 0 clean (worker-088 accept coexists with worker-088's own amended hard-failure "
                "revise at the same hash) and 4 hard-failure revises; F2a has 0 accepts and 3 hard-failure revises; "
                "F2b has 1 clean accept (worker-098) and 2 hard-failure revises; L0 has 0 accepts and 1 hard-failure "
                "revise. Controls C1-C4 pass. Worker evidence only; no gate verdict, no node status, no correctness "
                "re-adjudication."
            ),
            "evidence_refs": [ref_report, ref_manifest, ref_raw, ref_frozen, ref_map],
            "next_falsifier": next_falsifier,
        },
        {
            "event_id": f"w074-{stamp}-a1rev12indep-artifact-report",
            "event_type": "artifact",
            "created_at": created,
            "actor": AGENT,
            "task_id": TASK_ID,
            "class_id": CLASS_ID,
            "class_ids": CLASS_IDS,
            "node_id": NODE_ID,
            "gate": GATE,
            "artifact_type": "a1_review_independence_census",
            "path": "artifacts/worker-074/rev12_review_independence/report.json",
            "sha256": h["report.json"],
            "validation_status": "unverified",
            "falsifier": falsifier,
            "note": (
                "Per-target controller scan replay, identity/text accept clusters, clean-vs-conflicted accept "
                "counts, evidence-channel signatures, hard-failure conflict map, controls C1-C4 and the pinned "
                "corpus manifest digest."
            ),
        },
        {
            "event_id": f"w074-{stamp}-a1rev12indep-artifact-instrument",
            "event_type": "artifact",
            "created_at": created,
            "actor": AGENT,
            "task_id": TASK_ID,
            "class_id": CLASS_ID,
            "class_ids": CLASS_IDS,
            "node_id": NODE_ID,
            "gate": GATE,
            "artifact_type": "audit_instrument",
            "path": "artifacts/worker-074/rev12_review_independence/audit_rev12_review_independence.py",
            "sha256": h["audit_rev12_review_independence.py"],
            "validation_status": "unverified",
            "falsifier": (
                "Falsified if the script depends on wall-clock or filesystem order for cluster assignment, reads or "
                "writes any canonical path outside its own output directory, or fails to exit 3 when a control "
                "C1-C4 fails."
            ),
            "note": "Deterministic, read-only, no network; writes only report.json, snapshot_manifest.json and raw/scan_output.txt in its own directory.",
        },
        {
            "event_id": f"w074-{stamp}-a1rev12indep-artifact-readme",
            "event_type": "artifact",
            "created_at": created,
            "actor": AGENT,
            "task_id": TASK_ID,
            "class_id": CLASS_ID,
            "class_ids": CLASS_IDS,
            "node_id": NODE_ID,
            "gate": GATE,
            "artifact_type": "audit_readme",
            "path": "artifacts/worker-074/rev12_review_independence/README.md",
            "sha256": h["README.md"],
            "validation_status": "unverified",
            "falsifier": falsifier,
            "note": "Human-readable decisive table, method, controls, falsifier and limits.",
        },
        {
            "event_id": f"w074-{stamp}-a1rev12indep-artifact-manifest",
            "event_type": "artifact",
            "created_at": created,
            "actor": AGENT,
            "task_id": TASK_ID,
            "class_id": CLASS_ID,
            "class_ids": CLASS_IDS,
            "node_id": NODE_ID,
            "gate": GATE,
            "artifact_type": "snapshot_manifest",
            "path": "artifacts/worker-074/rev12_review_independence/snapshot_manifest.json",
            "sha256": h["snapshot_manifest.json"],
            "validation_status": "unverified",
            "falsifier": (
                "Falsified if the listed per-file sha256 of any of the 100+ review documents does not match the file "
                "on disk at the recorded scan instant, or if the target hashes differ from the measured values."
            ),
            "note": f"Pins every review document scanned and the five target hashes; corpus digest {corpus_digest}.",
        },
        {
            "event_id": f"w074-{stamp}-a1rev12indep-artifact-rawscan",
            "event_type": "artifact",
            "created_at": created,
            "actor": AGENT,
            "task_id": TASK_ID,
            "class_id": CLASS_ID,
            "class_ids": CLASS_IDS,
            "node_id": NODE_ID,
            "gate": GATE,
            "artifact_type": "raw_scan_output",
            "path": "artifacts/worker-074/rev12_review_independence/raw/scan_output.txt",
            "sha256": h["scan_output.txt"],
            "validation_status": "unverified",
            "falsifier": "Falsified if any line cannot be regenerated by re-running the instrument at the same corpus digest.",
            "note": "One line per bound verdict: target | verdict | full-flag | reviewer | review file | explicit pins.",
        },
        {
            "event_id": f"w074-{stamp}-a1rev12indep-claim",
            "event_type": "claim",
            "created_at": created,
            "actor": AGENT,
            "task_id": TASK_ID,
            "class_id": CLASS_ID,
            "class_ids": CLASS_IDS,
            "node_id": NODE_ID,
            "gate": GATE,
            "conclusion_type": "formal_model",
            "statement": (
                "Instrument-and-provenance claim (not a mathematical or numerical result), bound to the pinned "
                f"corpus digest {corpus_digest} and target hashes F0 0abb9ed8a961 / F1 cce9c60146d6 / F2a "
                "5476a3f2c6bc / F2b 55d0a1ea9bda / L0 a1674f094979: after replaying the controller scan rule and "
                "deduplicating full accepts by reviewer identity, review-document bytes and findings-text shingles, "
                "F0 carries 4 clean independent accepts, F1 0, F2a 0, F2b 1 (worker-098), L0 0; F1's single "
                "controller accept (worker-088) is accompanied by worker-088's own amended hard-failure revise at the "
                "same hash and is therefore not counted clean. The G-AUDIT/A1 '2 independent verdicts per target' "
                "review-count criterion is met for F0 and not met for F1/F2a/F2b/L0 at this snapshot; correctness and "
                "hash-binding are not re-adjudicated."
            ),
            "assumptions": [
                "The controller scan set is reviews/*.json and the scan rule is research_map/astra_lifecycle.py::review_coverage (verdict in accept/revise/reject/inconclusive; target alias normalisation; explicit 12-hex pin match against the measured sha256; counts_as_full_schema_verdict is not False).",
                "Two accepts are independent unless they share a reviewer id, identical review-document sha256, or findings-text token 6-gram Jaccard >= 0.60.",
                "A cluster is CLEAN unless one of its reviewers also filed a hard-failure revise/reject at the same measured hash; scoped verdicts (counts_as_full_schema_verdict=false) never count as accepts.",
                "The corpus is a growing snapshot: the manifest digest pins the scanned bytes; verdicts written later are out of scope.",
            ],
            "falsifier": falsifier,
            "evidence_refs": [ref_report, ref_readme, ref_manifest, ref_frozen, ref_map],
            "artifact_refs": [ref_report, ref_script, ref_readme, ref_manifest, ref_raw],
        },
    ]

    validate = load_validator()
    out_path = ROOT / "comms" / "outbox" / f"{AGENT}.jsonl"
    before = out_path.read_text() if out_path.exists() else ""
    lines = []
    for e in events:
        validate(e)  # raises on any schema violation
        lines.append(json.dumps(e, ensure_ascii=False, sort_keys=True))
    with open(out_path, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    after = out_path.read_text()

    checkpoint = {
        "worker": AGENT,
        "checkpoint": 4,
        "task_id": TASK_ID,
        "at": created,
        "class_ids": CLASS_IDS,
        "node_id": NODE_ID,
        "gate": GATE,
        "assignment": (
            "no assignment card existed for worker-074 in this lifecycle; one class-bound task taken from the open "
            "A1/G-AUDIT queue: independence + conflict census of the rev12 review corpus at the measured canonical hashes."
        ),
        "authority_note": (
            "Worker-authored evidence only: this checkpoint/report sets no node status, no validation_status=passed, "
            "and no gate verdict."
        ),
        "hours_spent_estimate": 0.35,
        "snapshot": {
            "map_sha256": map_sha,
            "frozen_sha256": frozen_sha,
            "corpus_digest_sha256": corpus_digest,
            "n_review_docs": report["corpus"]["n_review_docs"],
            "targets": {t: v["measured"]["sha256"] for t, v in report["targets"].items()},
        },
        "result": {
            "per_target": target_summary,
            "controls": report["controls"],
            "drift": report["drift"],
            "criterion_two_clean_independent_accepts": report["finding"]["per_target_criterion"],
        },
        "artifacts": [
            {"path": "artifacts/worker-074/rev12_review_independence/report.json", "sha256": h["report.json"]},
            {"path": "artifacts/worker-074/rev12_review_independence/audit_rev12_review_independence.py", "sha256": h["audit_rev12_review_independence.py"]},
            {"path": "artifacts/worker-074/rev12_review_independence/README.md", "sha256": h["README.md"]},
            {"path": "artifacts/worker-074/rev12_review_independence/snapshot_manifest.json", "sha256": h["snapshot_manifest.json"]},
            {"path": "artifacts/worker-074/rev12_review_independence/raw/scan_output.txt", "sha256": h["scan_output.txt"]},
        ],
        "next_falsifier": next_falsifier,
        "status": {"delivered": True, "gate_effect": "none - worker cannot set a gate verdict or node status", "validation_status": "unverified"},
    }
    ckpt_p = ROOT / "runtime" / "state" / "w074_checkpoint_4.json"
    ckpt_p.write_text(json.dumps(checkpoint, indent=2, ensure_ascii=False) + "\n")
    ckpt_sha = sha256_file(ckpt_p)

    print(json.dumps({
        "outbox": str(out_path.relative_to(ROOT)),
        "events_appended": len(events),
        "outbox_bytes_before": len(before.encode()),
        "outbox_bytes_after": len(after.encode()),
        "checkpoint": str(ckpt_p.relative_to(ROOT)),
        "checkpoint_sha256": ckpt_sha,
        "artifact_hashes": h,
        "all_events_valid": True,
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
