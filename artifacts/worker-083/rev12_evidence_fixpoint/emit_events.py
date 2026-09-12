#!/usr/bin/env python3
"""Emit the W083-REV12-CLOSURE-EVIDENCE-FIXPOINT-01 events and checkpoint.

Validates every event with research_map/schemas.py, re-verifies every artifact hash and
every frozen pin on disk at emit time, appends the events to
comms/outbox/worker-083.jsonl, writes runtime/state/w083_checkpoint_3.json and appends a
compact line to runtime/state/w083_checkpoints.jsonl.

Exit 0 iff all validations pass. Read-only with respect to canonical artifacts.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event, validate_artifact_hash  # noqa: E402

TASK = "W083-REV12-CLOSURE-EVIDENCE-FIXPOINT-01"
NODE = "F0,F1,F2a,F2b"
GATE = "G-FORM"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
CLASS_STR = ";".join(CLASS_IDS)
OUTBOX = ROOT / "comms/outbox/worker-083.jsonl"
CKPT_JSON = ROOT / "runtime/state/w083_checkpoint_3.json"
CKPT_JSONL = ROOT / "runtime/state/w083_checkpoints.jsonl"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    problems: list[str] = []
    manifest = json.loads((HERE / "MANIFEST.json").read_text())
    report = json.loads((HERE / "report.json").read_text())
    pins = json.loads((HERE / "pins.json").read_text())

    # 1. every deliverable hash still matches.
    for rel, rec in sorted(manifest["files"].items()):
        p = HERE / rel
        if not p.exists():
            problems.append(f"MISSING deliverable {rel}")
        elif sha256_file(p) != rec["sha256"]:
            problems.append(f"DRIFT deliverable {rel}")

    # 2. the frozen pins this audit binds to are unchanged at emit time.
    for rel, expect in pins["audited"]["canonical_bytes"].items():
        got = sha256_file(ROOT / rel)
        if got != expect:
            problems.append(f"MOVING TARGET {rel}: {got[:12]} != {expect[:12]}")
    for rel, expect in [("artifacts/formulation/FROZEN.json", pins["frozen"]["sha256"]),
                        ("artifacts/formulation/evidence/close_findings_rev27_report.json",
                         pins["audited"]["closure_record"]["sha256"]),
                        ("artifacts/formulation/tools/close_findings_rev27.py",
                         pins["audited"]["closure_procedure"]["sha256"]),
                        ("artifacts/formulation/evidence/gate_test_report.json",
                         pins["audited"]["cross_binding"]["artifacts/formulation/evidence/gate_test_report.json"])]:
        got = sha256_file(ROOT / rel)
        if got != expect:
            problems.append(f"MOVING TARGET {rel}: {got[:12]} != {expect[:12]}")

    if problems:
        print("EMIT ABORTED:")
        for p in problems:
            print("  " + p)
        return 1

    now = datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")
    stamp = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S")
    root_rel = "artifacts/worker-083/rev12_evidence_fixpoint"

    def art(name: str) -> dict:
        rel = manifest["files"][name]
        return {"path": f"{root_rel}/{name}", "sha256": rel["sha256"], "bytes": rel["bytes"]}

    checker = art("check_rev12_evidence_fixpoint.py")
    evidence = art("evidence.json")
    reportf = art("report.json")
    readme = art("REPORT.md")
    pinsf = art("pins.json")
    manifestf = {"path": f"{root_rel}/MANIFEST.json",
                 "sha256": sha256_file(HERE / "MANIFEST.json"),
                 "bytes": (HERE / "MANIFEST.json").stat().st_size}

    answers = report["report"]["answers"]
    finding = report["finding"]
    digest = report["canonical_digest_sha256"]
    falsifier = finding["falsifier"] + (" F3 (moving target): any canonical byte change voids this measurement; "
                                        f"re-run and compare canonical_digest_sha256 {digest[:12]}.")

    refs = [
        f"{reportf['path']}#{reportf['sha256']}",
        f"{evidence['path']}#{evidence['sha256']}",
        f"{checker['path']}#{checker['sha256']}",
        f"{root_rel}/pins.json#{pinsf['sha256']}",
        "artifacts/formulation/FROZEN.json#2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1",
        "artifacts/formulation/evidence/close_findings_rev27_report.json#dab1d49b9985416504239154fa8af0ec94147ee4ebae0cd7732001ccead69972",
        "artifacts/formulation/tools/close_findings_rev27.py#0234cd3cbda491ae353e4972dda8a8fe95ae39d2fe2b4968639dc2fcad845371",
        "artifacts/formulation/evidence/gate_test_report.json#6def01264a1dcbced0f698e951d1b200ffe35abfae01b184673c59741f364894",
        "schemas/af_wcc_vacuum.yaml#cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
        "schemas/af_scc_c2_vacuum.yaml#5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
        "schemas/af_scc_c0_vacuum.yaml#55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
        "research_map/formulation_taxonomy.yaml#0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    ]

    common = {"actor": "worker-083", "node_id": NODE, "gate": GATE, "class_id": CLASS_STR,
              "class_ids": CLASS_IDS, "task_id": TASK, "created_at": now}

    events = [
        dict(common, event_id=f"w083-{stamp}-task-claim", event_type="status", status="active", hours=0.2,
             summary=("No inbox card for worker-083; took ONE unclaimed class-bound task on the G-FORM "
                      "closure-evidence requirement: measure at the FROZEN rev28 pins (FROZEN 2f358f6722d9, "
                      "44/44 match disk) whether the pinned rev12 closure record "
                      "artifacts/formulation/evidence/close_findings_rev27_report.json#dab1d49b9985 binds the "
                      "frozen rev12 bytes, and whether the pinned closure procedure is reproducible there. "
                      "Result: 7/8 declared post-write hashes are unrecoverable intermediates; the pinned tool "
                      "exits 1 (ASSERT FAIL) in dry-run at the frozen bytes; the frozen outcome is nevertheless "
                      "bound by gate_test_report.json#6def0126 and FROZEN rev28. 7/7 controls pass. Worker "
                      "evidence only; no gate verdict."),
             evidence_refs=refs, next_falsifier=falsifier),
        dict(common, event_id=f"w083-{stamp}-artifact-checker", event_type="artifact",
             artifact_type="verification_tool", path=checker["path"], sha256=checker["sha256"],
             validation_status="unverified",
             note=("Deterministic read-only checker: FROZEN pin sweep, closure-report entry classification, "
                   "archive scan for intermediate bytes, pinned-tool dry-run with before/after hashes, delta "
                   "scan, cross-binding check, 7 controls. Exit 0 iff all controls pass.")),
        dict(common, event_id=f"w083-{stamp}-artifact-report", event_type="artifact",
             artifact_type="audit_report", path=reportf["path"], sha256=reportf["sha256"],
             validation_status="unverified",
             note=("Machine report: Q1 YES (44/44 pins), Q2 NO (7/8 stale), Q3 NO (tool fails closed), Q4 YES "
                   "(outcome bound by gate_test_report.json); per-entry table, controls, finding W083-REF-01 "
                   f"with falsifier; canonical digest {digest[:12]}.")),
        dict(common, event_id=f"w083-{stamp}-artifact-evidence", event_type="artifact",
             artifact_type="measurement_evidence", path=evidence["path"], sha256=evidence["sha256"],
             validation_status="unverified",
             note=("Raw evidence: report-entry audit with declared/pin/disk hashes, archive scan (0 copies of "
                   "each intermediate), tool dry-run transcript and read-only proof, delta scan, cross-binding "
                   "map, controls.")),
        dict(common, event_id=f"w083-{stamp}-artifact-REPORT", event_type="artifact",
             artifact_type="verification_report", path=readme["path"], sha256=readme["sha256"],
             validation_status="unverified",
             note=("Human-readable report: result table, defect table, non-recoverability argument, consequence "
                   "and a measure-only remedy proposal (not applied), controls, falsifiers, limits.")),
        dict(common, event_id=f"w083-{stamp}-artifact-pins", event_type="artifact",
             artifact_type="pin_manifest", path=pinsf["path"], sha256=pinsf["sha256"],
             validation_status="unverified",
             note=("Every sha256 this audit binds to, the four intermediate hashes the closure record declares, "
                   "and the fixed tool invocation.")),
        dict(common, event_id=f"w083-{stamp}-artifact-MANIFEST", event_type="artifact",
             artifact_type="artifact_manifest", path=manifestf["path"], sha256=manifestf["sha256"],
             validation_status="unverified",
             note=("Measured hashes and byte sizes of the 9 deliverable files (including frozen input copies).")),
        dict(common, event_id=f"w083-{stamp}-claim-001", event_type="claim",
             conclusion_type="stability_result",
             statement=(f"Artifact-and-checker result (not a mathematics or physics claim) at FROZEN rev28 "
                        f"2f358f6722d9 (44/44 pins match disk): the pinned closure record "
                        f"artifacts/formulation/evidence/close_findings_rev27_report.json#dab1d49b9985 declares 7 of "
                        f"8 post-write hashes that match neither the frozen rev12 pins nor current disk bytes - "
                        f"canonical schemas b474fbc4/a7ccae4d/b71ec02c vs frozen cce9c60146d6/5476a3f2c6bc/"
                        f"55d0a1ea9bda and taxonomy_consistency f3c119a8 vs frozen 9e335e9ba1bf - with the three "
                        f"canonical schema entries declaring the same revision 12 as the frozen bytes; no archived "
                        f"file hashes to any of the four intermediates (12,570 files scanned, 0 copies); and the "
                        f"pinned procedure artifacts/formulation/tools/close_findings_rev27.py#0234cd3c exits 1 with "
                        f"ASSERT FAIL in --dry-run at the frozen bytes, so the closure is not reproducible from its "
                        f"own pinned evidence+tool+bytes triple. The frozen outcome is nevertheless bound by "
                        f"artifacts/formulation/evidence/gate_test_report.json#6def0126 (declares all three frozen "
                        f"schema hashes) and by FROZEN rev28 itself, so the defect is stage-2 evidence-binding, not "
                        f"schema content. 7/7 controls pass; canonical digest {digest}. No gate verdict, node "
                        f"status or validation_status is claimed."),
             assumptions=[
                 "The FROZEN rev28 pins are the current canonical bytes (measured 44/44 at emit time).",
                 "sha256 binding is the evidence relation the protocol requires (PROTOCOL.md rules 2 and 4).",
                 "A --dry-run of the pinned read-only migration tool is an admissible reproducibility probe; it wrote nothing (control C5).",
                 "The intermediate bytes are unrecoverable because no archived copy exists in the scanned tree and no revision delta records the post-report rewrite.",
                 "A worker may measure and report but may not edit frozen artifacts or set gate/node status.",
             ],
             falsifier=falsifier,
             evidence_refs=refs,
             artifact_refs=[checker["path"], reportf["path"], evidence["path"], readme["path"], pinsf["path"]]),
        dict(common, event_id=f"w083-{stamp}-complete", event_type="status", status="active", hours=0.7,
             summary=(f"{TASK} complete as a bounded worker deliverable (completion claim for the artifact, not a "
                      f"node transition: workers cannot set done/passed; G-FORM/G-F0 stay pending). Result "
                      f"Q1=YES Q2=NO Q3=NO Q4=YES; 7/8 closure-report entries stale, 0 archived copies, tool fails "
                      f"closed at the frozen bytes, outcome bound by gate_test_report.json. Checkpoint "
                      f"runtime/state/w083_checkpoint_3.json. Next consumer: formulation lead / G-FORM r2 "
                      f"reviewers - do not validate the rev12 repair through the stale closure table; a "
                      f"measure-only addendum is proposed in REPORT.md section 4 and deliberately not applied."),
             evidence_refs=refs, next_falsifier=falsifier),
    ]

    # validate events + artifact hashes before writing anything
    for e in events:
        try:
            validate_event(e)
        except Exception as exc:  # SchemaError
            print(f"SCHEMA FAIL {e.get('event_id')}: {exc}")
            return 1
        if e["event_type"] == "artifact":
            if not validate_artifact_hash(str(ROOT / e["path"]), e["sha256"]):
                print(f"HASH FAIL {e['event_id']} {e['path']}")
                return 1

    with OUTBOX.open("a", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    checkpoint = {
        "checkpoint_id": "w083-ckpt-3",
        "task_id": TASK,
        "worker": "worker-083",
        "created_at": now,
        "node_ids": ["F0", "F1", "F2a", "F2b"],
        "gate": GATE,
        "class_ids": CLASS_IDS,
        "status": "active",
        "hours": 0.7,
        "summary": ("Bounded evidence audit at FROZEN rev28: closure evidence does not bind the frozen rev12 "
                    "bytes (7/8 declared hashes intermediate/unrecoverable) and the pinned closure tool fails "
                    "closed there; frozen outcome independently bound by gate_test_report.json and FROZEN rev28. "
                    "7/7 controls pass."),
        "result": {"Q1_frozen_matches_disk": answers["Q1_frozen_matches_disk"],
                   "Q2_closure_evidence_binds_frozen_rev12": answers["Q2_closure_evidence_binds_frozen_rev12"],
                   "Q3_closure_reproducible_at_frozen_bytes": answers["Q3_closure_reproducible_at_frozen_bytes"],
                   "Q4_outcome_bound_elsewhere": answers["Q4_outcome_bound_elsewhere"],
                   "stale_report_entries": report["report_entry_audit"]["stale_count"],
                   "intermediate_hashes": report["stale_hashes"],
                   "archived_copies": 0,
                   "controls_all_pass": report["controls_all_pass"],
                   "canonical_digest_sha256": digest},
        "artifact_hashes": {k: v["sha256"] for k, v in sorted(manifest["files"].items())},
        "frozen_pins": pins["audited"],
        "no_completion_claim": ("No gate verdict, no node status, no validation_status, no class-id change; the "
                                "remedy is a proposal and was not applied."),
        "next_falsifier": falsifier,
    }
    CKPT_JSON.write_text(json.dumps(checkpoint, indent=1) + "\n", encoding="utf-8")
    with CKPT_JSONL.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"checkpoint_id": checkpoint["checkpoint_id"], "task_id": TASK,
                            "created_at": now, "node_id": NODE, "gate": GATE, "status": "active",
                            "canonical_digest_sha256": digest,
                            "controls_ok": report["controls_all_pass"],
                            "result": checkpoint["result"]}, ensure_ascii=False) + "\n")

    print(f"emitted {len(events)} events -> {OUTBOX}")
    for e in events:
        print("  ", e["event_id"], e["event_type"])
    print(f"checkpoint -> {CKPT_JSON} ({sha256_file(CKPT_JSON)[:12]})")
    print("ALL VALIDATIONS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
