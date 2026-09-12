#!/usr/bin/env python3
"""W065-GFORM-PINBIND-RECHECK-05 event emitter + checkpoint writer.

Validates every event with the canonical `research_map/schemas.py` validator
(imported under -B so no bytecode is written), appends them to
`comms/outbox/worker-065.jsonl`, writes the artifact-dir checkpoint and the
runtime/state copy.  Idempotent-safe: refuses to append an event_id that already
exists in the outbox.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ART = ROOT / "artifacts/worker-065/gform_pinbind_recheck"
OUTBOX = ROOT / "comms/outbox/worker-065.jsonl"
RUNTIME_CKPT = ROOT / "runtime/state/worker-065_gform_pinbind_recheck_checkpoint.json"
sys.path.insert(0, str(ROOT))
from research_map.schemas import validate_event  # noqa: E402


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    report = json.loads((ART / "report.json").read_text())
    stamp = report["created_at"]
    # event-id stamp must be filesystem/sort friendly: 2026-09-12T01:19:16+0800 -> 20260912T011916
    core = stamp.replace("-", "").replace(":", "")
    es = core[:8] + "T" + core[9:15]

    art_paths = {
        "driver": "artifacts/worker-065/gform_pinbind_recheck/recheck.py",
        "pinned_checker": "artifacts/worker-065/gform_pinbind_recheck/pinned/check_sidepins.pinned.py",
        "report": "artifacts/worker-065/gform_pinbind_recheck/report.json",
        "controls": "artifacts/worker-065/gform_pinbind_recheck/controls.json",
        "readme": "artifacts/worker-065/gform_pinbind_recheck/README.md",
    }
    hashes = {k: sha256_file(ROOT / v) for k, v in art_paths.items()}
    assert hashes["driver"] == report["instrument"]["driver_sha256"], "driver hash drift"
    assert hashes["pinned_checker"] == report["instrument"]["checker_sha256"], "checker hash drift"

    classes = report["class_ids"]
    rs = report["result_summary"]
    ev = {
        "instrument": f"w065-pinbind-{es}-artifact-instrument",
        "report": f"w065-pinbind-{es}-artifact-report",
        "controls": f"w065-pinbind-{es}-artifact-controls",
        "readme": f"w065-pinbind-{es}-artifact-readme",
        "checkpoint": f"w065-pinbind-{es}-artifact-checkpoint",
        "claim": f"w065-pinbind-{es}-claim",
        "status": f"w065-pinbind-{es}-status",
        "blocker": f"w065-pinbind-{es}-blocker",
    }

    checkpoint = {
        "schema": "w065-checkpoint/1",
        "task_id": "W065-GFORM-PINBIND-RECHECK-05",
        "worker": "worker-065",
        "actor": "worker-065",
        "created_at": stamp,
        "gate": "G-FORM",
        "node_id": "F1,F2a,F2b",
        "class_id": report["primary_class_id"],
        "class_ids": classes,
        "task_origin": "self-selected (no inbox card for worker-065 at 2026-09-12T01:18+08:00); continues W065-CANON-SIDEPIN-CENSUS-04",
        "result_summary": rs,
        "per_class_verdicts": report["per_class_verdicts"],
        "window_status": report["window"]["status"],
        "window_paths_pinned": len(report["window"]["pre"]),
        "gate_relevant_defects": rs["gate_relevant_defects"],
        "defect_set_unchanged_since_census_04": rs["defect_set_unchanged_since_census_04"],
        "census_04_comparison": report["census_04_comparison"],
        "live_checker_rc": rs["live_checker_rc"],
        "controls": rs["controls_pass"],
        "citation_hazard_census": {
            "reviews_total": report["citation_hazard_census"]["reviews_total"],
            "snapshot_digest_sha256": report["citation_hazard_census"]["snapshot_digest_sha256"],
            "buckets": {c: report["citation_hazard_census"]["per_class"][c]["buckets"] for c in classes},
        },
        "artifacts": hashes,
        "artifact_paths": art_paths,
        "event_ids": list(ev.values()),
        "falsifier": report["falsifier"],
        "next_falsifier": ("Re-run this task after the next owner repair or at the r3 verification read: did any of "
                           "the 8 gate-relevant declared pins repair, and did the reviews snapshot digest move? "
                           "Verdicts are void if FROZEN rev29 or any class schema moves."),
        "authority_note": ("worker measurement only; sets no gate verdict, no node status, no "
                           "validation_status=passed; writes no canonical path."),
        "canonical_writes": "none (read-only on every canonical path; writes confined to artifacts/worker-065/gform_pinbind_recheck/, comms/outbox/worker-065.jsonl and the runtime checkpoint copy)",
        "self_hash_excluded": "checkpoint.json is excluded from artifacts{} by design: a manifest cannot contain its own post-write hash.",
    }
    (ART / "checkpoint.json").write_text(json.dumps(checkpoint, indent=1, sort_keys=True) + "\n")
    RUNTIME_CKPT.write_text(json.dumps(checkpoint, indent=1, sort_keys=True) + "\n")

    common = {
        "actor": "worker-065",
        "created_at": stamp,
        "class_id": report["primary_class_id"],
        "class_ids": classes,
        "gate": "G-FORM",
        "node_id": "F1,F2a,F2b",
        "task_id": "W065-GFORM-PINBIND-RECHECK-05",
        "authority_note": checkpoint["authority_note"],
    }
    evidence = [
        f"{art_paths['report']}#{hashes['report'][:12]}",
        f"{art_paths['controls']}#{hashes['controls'][:12]}",
        f"{art_paths['readme']}#{hashes['readme'][:12]}",
        f"artifacts/worker-065/canon_sidepin_census/sidepin_census.json#5b864c3c3339",
        f"runtime/state/worker-065_gform_pinbind_recheck_checkpoint.json",
        "schemas/af_wcc_vacuum.yaml#d9cebb9404b2",
        "schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3",
        "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
        "artifacts/formulation/FROZEN.json#815e08079aef",
    ]
    events = [
        dict(common, event_id=ev["instrument"], event_type="artifact",
             artifact_type="pinned_checker_copy",
             path=art_paths["pinned_checker"], sha256=hashes["pinned_checker"],
             validation_status="unverified",
             evidence_refs=[f"{art_paths['pinned_checker']}#{hashes['pinned_checker'][:12]}",
                            "artifacts/worker-065/canon_sidepin_census/check_sidepins.py#88b19be6d9a7"],
             note="Byte-identical copy of the census-04 checker; hash re-verified fail-closed before every run."),
        dict(common, event_id=ev["report"], event_type="artifact",
             artifact_type="per_class_pin_binding_recheck_report",
             path=art_paths["report"], sha256=hashes["report"], validation_status="unverified",
             evidence_refs=evidence,
             note="96 declared pins; 8 gate-relevant stale; per-class PIN_HAZARD x3; window STABLE; controls 5/5."),
        dict(common, event_id=ev["controls"], event_type="artifact",
             artifact_type="control_results",
             path=art_paths["controls"], sha256=hashes["controls"], validation_status="unverified",
             evidence_refs=[f"{art_paths['report']}#{hashes['report'][:12]}"],
             note="C1 clean shadow rc0; C2/C3/C5 stale mutations detected; C4 format-only clean."),
        dict(common, event_id=ev["readme"], event_type="artifact",
             artifact_type="task_readme",
             path=art_paths["readme"], sha256=hashes["readme"], validation_status="unverified",
             evidence_refs=[f"{art_paths['report']}#{hashes['report'][:12]}"],
             note="Method, per-class table, citation buckets, findings, falsifier, non-claims, reproduce command."),
        dict(common, event_id=ev["checkpoint"], event_type="artifact",
             artifact_type="worker_checkpoint",
             path="artifacts/worker-065/gform_pinbind_recheck/checkpoint.json",
             sha256=sha256_file(ART / "checkpoint.json"), validation_status="unverified",
             evidence_refs=[f"{art_paths['report']}#{hashes['report'][:12]}",
                            "runtime/state/worker-065_gform_pinbind_recheck_checkpoint.json"],
             note="Artifact hashes, per-class verdicts, window pins, controls, citation digest, event ids."),
        dict(common, event_id=ev["claim"], event_type="claim",
             conclusion_type="formal_model",
             statement=("At the G-FORM r3 verification window (report sha256 %s, window STABLE, 96 declared pins): all "
                        "three class schemas are PIN_HAZARD on declared registry pins — entry_hashes.json advertises "
                        "the superseded 9a8bd4c9 for F1 against live d9cebb94, b6123750 for F2a against live "
                        "e9a27996, 1bb78ce9 for F2b against live b2ab6acb, and the F2b sidecar advertises 1bb78ce9 — "
                        "while the FROZEN rev29 pins and the aggregator component pins match live bytes. The 8 "
                        "gate-relevant defect identities are unchanged since census-04; no repair landed. This is a "
                        "registry-layer binding gap shared by all three classes, not a property of the class "
                        "contents.") % hashes["report"][:12],
             assumptions=[
                 "the measured sha256 is the artifact identity; every statement binds only to the pinned bytes",
                 "the census-04 checker at 88b19be6d9a7761b281f34dc3b8b162efe42ab6951f790e62ff962788eb47d43 is the declared instrument and was hash-verified before measuring",
                 "entry_hashes.json and the F2b sidecar are the declared registry layer; FROZEN rev29 and the aggregator are the declared manifest layer",
                 "the citation census reads declared 64-hex strings only; it makes no claim about reviewer intent, independence or verdict merit",
                 "the review set moved by one file during the task; the census is bound to the recorded snapshot digest",
             ],
             falsifier=report["falsifier"],
             evidence_refs=evidence,
             artifact_refs=[f"{art_paths['report']}#{hashes['report'][:12]}",
                            f"{art_paths['controls']}#{hashes['controls'][:12]}"],
             findings=["F-065-PB-1 defects persist", "F-065-PB-2 registry-layer gap, manifest layer clean",
                       "F-065-PB-3 F2b sidecar trap live", "F-065-PB-4 citation exposure non-zero"]),
        dict(common, event_id=ev["status"], event_type="status", status="active", hours=0.5,
             summary=("W065-GFORM-PINBIND-RECHECK-05 complete at worker level (completion claim only: workers cannot "
                      "set done/passed or a gate verdict). One bounded class-bound task, self-selected: 96 declared "
                      "pins re-measured with the pinned census-04 instrument; 8 gate-relevant stale declared pins "
                      "unchanged since census-04; all three G-FORM classes PIN_HAZARD on registry pins with FROZEN/"
                      "aggregator pins live; window STABLE; controls 5/5; citation snapshot 229 records digest "
                      "42eeb6c0f3a3. No canonical write."),
             evidence_refs=evidence,
             next_falsifier=checkpoint["next_falsifier"]),
        dict(common, event_id=ev["blocker"], event_type="blocker",
             description=("G-FORM per-file pin binding is not clean at the r3 window: 8 gate-relevant declared pins "
                          "resolve to superseded bytes (F1/F2a/F2b entry_hashes.json rows, the F2b sidecar, the F0 "
                          "taxonomy and FROZEN entries, two flash-04 BUNDLE pins). All three class schemas are "
                          "PIN_HAZARD on declared registry pins."),
             needed_to_unblock=("Owner repair of entry_hashes.json (+ the F2b sidecar) to live bytes, or a declared "
                                "resolution rule that makes the advertised pins resolve correctly; then a re-run of "
                                "this recheck at the new bytes."),
             evidence_refs=evidence),
    ]

    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text(errors="ignore").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line).get("event_id"))
            except json.JSONDecodeError:
                continue
    for e in events:
        validate_event(e)
        if e["event_id"] in existing:
            print(f"SKIP duplicate {e['event_id']}")
            continue
        with OUTBOX.open("a") as f:
            f.write(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n")
        print(f"APPENDED {e['event_type']:9s} {e['event_id']}")

    print(json.dumps({"checkpoint": str(ART / 'checkpoint.json'),
                      "runtime_checkpoint": str(RUNTIME_CKPT),
                      "artifacts": hashes}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
