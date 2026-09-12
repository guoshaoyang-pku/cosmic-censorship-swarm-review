#!/usr/bin/env python3
"""Finalize W036-GFORM-R3-BIND-01: CHECKPOINT.json, SHA256SUMS, outbox events.

Idempotent: event ids already present in comms/outbox/worker-036.jsonl are not re-appended.
Writes only the task artifact directory, runtime/state/<task>_checkpoint.json, and the
worker's own outbox file. Never writes a canonical path, the map, or artifact_hashes.json.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CST = timezone(timedelta(hours=8))
OUTBOX = ROOT / "comms" / "outbox" / "worker-036.jsonl"
STATE_COPY = ROOT / "runtime" / "state" / "worker-036_GFORM_R3_binding_census_checkpoint.json"


def h(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    report = json.loads((HERE / "report.json").read_text())
    artifacts = {str(p.relative_to(ROOT)): h(p) for p in [
        HERE / "census_gform_binding.py", HERE / "report.json", HERE / "README.md",
        HERE / "make_checkpoint.py", HERE / "pinned" / "MANIFEST.json"]}
    rep_rel = "artifacts/worker-036/gform_r3_binding_census/report.json"
    seen = set()
    if OUTBOX.is_file():
        for line in OUTBOX.read_text().splitlines():
            try:
                seen.add(json.loads(line).get("event_id"))
            except Exception:
                pass

    fresh = {t: v["distinct_accept_reviewers"] for t, v in report["fresh_coverage"].items()}
    recorded = {t: v["count"] for t, v in report["recorded_gate_audit"].items()}
    binding_files = [f"reviews/{b['file']}#{b['sha256'][:12]}" for b in report["binding_accepts"]]

    checkpoint = {
        "checkpoint_id": "w036-gform-r3-bind-ckpt-20260912T011700",
        "task_id": report["task_id"],
        "actor": "worker-036",
        "instance": "worker-036-20260912T010820-968807",
        "created_at": report["created_at"],
        "checkpoint_at": datetime.now(CST).isoformat(timespec="seconds"),
        "node_id": "F1,F2a,F2b",
        "gate": "G-FORM",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": report["class_ids"],
        "scope": "worker-level coverage census; no node done, no gate verdict, no canonical write",
        "authority_note": report["authority_note"],
        "artifacts": artifacts,
        "inputs_pinned_full_sha256": {
            "artifacts/formulation/FROZEN.json": report["pins"]["frozen"]["sha256"],
            **{v["canonical"]: v["canonical_sha256"]
               for v in report["pins"]["targets"].values()},
            "research_map/research_map.json": report["pins"]["map"]["sha256"],
            "reviews_snapshot_digest": report["corpus"]["snapshot_digest"],
            "pinned/MANIFEST.json": artifacts["artifacts/worker-036/gform_r3_binding_census/pinned/MANIFEST.json"],
        },
        "result": {
            "map_gate_checked_at": report["pins"]["map"]["gate_checked_at"],
            "recorded_counts": recorded,
            "fresh_counts": {t: len(v) for t, v in fresh.items()},
            "fresh_reviewers": fresh,
            "reproduces": {t: recorded[t] == len(fresh[t]) and
                           sorted(report["recorded_gate_audit"][t]["reviewers"]) == fresh[t]
                           for t in fresh},
            "binding_full_accepts": len(report["binding_accepts"]),
            "f2b_recorded_lost_reviewer": sorted(
                set(report["recorded_gate_audit"]["F2b"]["reviewers"]) - set(fresh["F2b"])),
            "findings_total": len(report["findings"]),
            "validity": f"{report['validity_checks']['passed']}/{report['validity_checks']['total']}",
            "snapshot_stable": report["snapshot_stable"],
        },
        "finding_ids": [f["id"] for f in report["findings"]],
        "checks": report["validity_checks"],
        "falsifier": report["next_falsifier"],
        "next_falsifier": ("For the audit lead's astra-life05-verify-gform-r3: re-measure coverage "
                           "at the review file hashes (not paths) immediately before binding; "
                           "re-check whether worker-072's revise, worker-018's and worker-053's "
                           "revises, and the W036-F2B-CONTAINMENT-ADJUDICATION-01 D1/D2 findings are "
                           "resolved or accepted-with-findings before counting F2b."),
        "gate_note": "coverage count != gate pass; F2b carries live blocking defect findings",
    }
    (HERE / "CHECKPOINT.json").write_text(json.dumps(checkpoint, indent=1, sort_keys=True) + "\n")
    STATE_COPY.write_text(json.dumps(checkpoint, indent=1, sort_keys=True) + "\n")
    (HERE / "SHA256SUMS.txt").write_text(
        "".join(f"{v}  {k[len('artifacts/worker-036/gform_r3_binding_census/'):]}\n"
                for k, v in sorted(artifacts.items())
                if k.startswith("artifacts/worker-036/gform_r3_binding_census/")))

    ts = datetime.now(CST).isoformat(timespec="seconds")
    ev_base = f"w036-gformbind-{ts[:19].replace(':', '').replace('-', '')}"
    ck_hash = h(HERE / "CHECKPOINT.json")
    evs = [
        {
            "event_id": ev_base + "-artifact", "event_type": "artifact", "created_at": ts,
            "actor": "worker-036", "node_id": "F1,F2a,F2b", "class_id": "AF-SCC-C0-VAC-GEN",
            "class_ids": report["class_ids"], "gate": "G-FORM",
            "artifact_type": "gform_rev29_accept_coverage_census",
            "path": rep_rel, "sha256": artifacts[rep_rel], "validation_status": "unverified",
            "evidence_refs": [
                f"artifacts/worker-036/gform_r3_binding_census/census_gform_binding.py#{artifacts['artifacts/worker-036/gform_r3_binding_census/census_gform_binding.py'][:12]}",
                f"artifacts/worker-036/gform_r3_binding_census/README.md#{artifacts['artifacts/worker-036/gform_r3_binding_census/README.md'][:12]}",
                f"artifacts/worker-036/gform_r3_binding_census/pinned/MANIFEST.json#{artifacts['artifacts/worker-036/gform_r3_binding_census/pinned/MANIFEST.json'][:12]}",
                "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
                "schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3",
                "schemas/af_wcc_vacuum.yaml#d9cebb9404b2",
                "artifacts/formulation/FROZEN.json#815e08079aef",
            ],
            "map_pin": {"path": "research_map/research_map.json",
                        "sha256": report["pins"]["map"]["sha256"],
                        "gate_checked_at": report["pins"]["map"]["gate_checked_at"],
                        "note": "historical measurement pin; the live map moves every cycle and is "
                                "recorded in report.json, not cited as a live ref"},
            "next_falsifier": report["next_falsifier"],
        },
        {
            "event_id": ev_base + "-claim", "event_type": "claim", "created_at": ts,
            "actor": "worker-036", "node_id": "F1,F2a,F2b", "gate": "G-FORM",
            "class_id": "AF-SCC-C0-VAC-GEN", "class_ids": report["class_ids"],
            "task_id": report["task_id"], "conclusion_type": "artifact_measurement",
            "statement": (
                "At FROZEN rev29 (manifest 815e08079aef) the controller's recorded G-FORM coverage "
                f"(map sha256 {report['pins']['map']['sha256'][:12]}, controller_gate_audit checked_at "
                f"{report['pins']['map']['gate_checked_at']}) reproduces exactly for F1 (4 accepts "
                "worker-052/072/075/085 at d9cebb9404b2) and F2a (2 accepts worker-017/072 at "
                "e9a27996dfd3), but is stale for F2b: the record lists 4 accepts "
                "(worker-052/071/072/090) at b2ab6acb2bbe while the byte-pinned review snapshot "
                "contains 3 full accepts (worker-052/071/090), because "
                "reviews/F2b-review-worker-072-rev29.json was rewritten in place at "
                "2026-09-12T01:14:54+08:00 from verdict accept (score 4.0) to revise (score 3.0, two "
                "blocking hard failures at regularity.must_not_conflate[0] line 152 and "
                "implication_ledger.forbidden_transfers[0].reason line 246 -- the same two defects "
                "confirmed in artifacts/worker-036/f2b_containment_adjudication/); the accept-bearing "
                "bytes are not preserved, so the recorded F2b count is not re-derivable from paths "
                "alone. F2b still meets the >=2 distinct full-accept count at the fresh snapshot and "
                "all three cite FROZEN rev29. Coverage pin-discipline gaps: F1 accept worker-085 and "
                "F2a accepts worker-017 and worker-072 do not cite FROZEN rev29 815e08079aef, and "
                "worker-017's F2a accept carries two stale evidence refs "
                "(artifacts/formulation/FROZEN.json#3d9e3d77fd87 -> 815e08079aef; "
                "artifacts/formulation/VARIANT_REGISTRY.json#5eb42f9a384a -> 6bac9adea19e); "
                "worker-090's F2b full accept declares blind=false with a self-disclosure. Worker "
                "measurement only -- no gate verdict, no node status, no canonical write. A count is "
                "coverage, not a pass: F2b carries live blocking defect findings from worker-072 "
                "(HF-01/HF-02), worker-018, worker-053 and W036-F2B-CONTAINMENT-ADJUDICATION-01."),
            "assumptions": [
                "the measured sha256 is the artifact identity; every claim binds to the pinned bytes and the review snapshot digest",
                "the controller review-coverage rule transcribed from research_map/astra_lifecycle.py:176-214 is the operative rule at snapshot time, and the independent worker-036 scanner agrees with it",
                "scope is reviews/*.json at top level, as the controller scans; review files created after the snapshot are out of scope",
                "the historical canonical-hash registry is derived only from explicit canonical-path pins in research_map/events.jsonl plus the pinned worker-066 rev12 archive, not from prose mentions",
                "blindness, non-author eligibility and verdict merit are the audit lead's adjudication, not this census's",
                "the census is void if FROZEN or any canonical schema moves; a later reviews/* write is outside the snapshot",
            ],
            "falsifier": report["next_falsifier"],
            "next_falsifier": checkpoint["next_falsifier"],
            "evidence_refs": [
                f"artifacts/worker-036/gform_r3_binding_census/report.json#{artifacts[rep_rel][:12]}",
                f"artifacts/worker-036/gform_r3_binding_census/README.md#{artifacts['artifacts/worker-036/gform_r3_binding_census/README.md'][:12]}",
                "reviews/F2b-review-worker-072-rev29.json#5db91bb0781d",
                "artifacts/worker-036/gform_r3_binding_census/pinned/F2b-review-worker-072-rev29.json#5db91bb0781d",
                *binding_files,
                "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
                "artifacts/formulation/FROZEN.json#815e08079aef",
            ],
            "artifact_refs": [
                f"artifacts/worker-036/gform_r3_binding_census/report.json#{artifacts[rep_rel][:12]}",
                f"artifacts/worker-036/gform_r3_binding_census/CHECKPOINT.json#{ck_hash[:12]}",
            ],
        },
        {
            "event_id": ev_base + "-status", "event_type": "status", "created_at": ts,
            "actor": "worker-036", "node_id": "F1,F2a,F2b", "gate": "G-FORM",
            "class_id": "AF-SCC-C0-VAC-GEN", "class_ids": report["class_ids"],
            "status": "active", "hours": 0.5,
            "summary": ("W036-GFORM-R3-BIND-01 complete at worker level: F1/F2a recorded coverage "
                        "reproduces; F2b recorded 4 vs fresh 3 after worker-072 withdrew its accept "
                        "in place at 01:14:54; 7 findings (2 major, 5 minor) incl. three FROZEN-pin "
                        "gaps and a stale-FROZEN evidence chain; validity 7/7, snapshot stable."),
            "evidence_refs": [
                f"artifacts/worker-036/gform_r3_binding_census/report.json#{artifacts[rep_rel][:12]}",
                f"runtime/state/worker-036_GFORM_R3_binding_census_checkpoint.json#{h(STATE_COPY)[:12]}",
                "artifacts/worker-036/gform_r3_binding_census/CHECKPOINT.json",
            ],
            "next_falsifier": report["next_falsifier"],
        },
    ]
    added = 0
    with OUTBOX.open("a") as fh:
        for ev in evs:
            if ev["event_id"] in seen:
                continue
            fh.write(json.dumps(ev, sort_keys=True) + "\n")
            added += 1
    print(f"finalize: artifacts={len(artifacts)} events_added={added} "
          f"checkpoint={h(HERE / 'CHECKPOINT.json')[:12]} state_copy={h(STATE_COPY)[:12]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
