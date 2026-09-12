#!/usr/bin/env python3
"""W029-L0-REV3-VERDICT-05 — emit the worker-029 upward events (validated locally).

Appends to comms/outbox/worker-029.jsonl only. Validates every line against
research_map/schemas.validate_event and checks it for class-separation findings
before writing, so the controller's ingest should accept the batch.

Usage:
    python3 artifacts/worker-029/l0_rev3_verify/emit_events.py
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

CST = timezone(timedelta(hours=8))
TASK = "W029-L0-REV3-VERDICT-05"
FROZEN = "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH"
LEDGER = "ledger/theorems.jsonl"
LEDGER_SHA = "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28"
L1_SHA = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
HF02_ROWS = ["D-004", "D-005", "T-303", "T-305", "T-402", "T-515", "T-526", "T-528"]

spec = importlib.util.spec_from_file_location("cs", ROOT / "research_map" / "class_separation.py")
cs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cs)


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def art(rel: str) -> dict:
    p = ROOT / rel
    return {"path": rel, "sha256": sha(p), "bytes": p.stat().st_size}


def main() -> int:
    now = datetime.now(CST).isoformat(timespec="seconds")
    checker = art("artifacts/worker-029/l0_rev3_verify/check_l0_rev3.py")
    snap_script = art("artifacts/worker-029/l0_rev3_verify/snapshot_l0_rev3.py")
    report = art("artifacts/worker-029/l0_rev3_verify/report.json")
    core = art("artifacts/worker-029/l0_rev3_verify/report_core.json")
    evidence = art("artifacts/worker-029/l0_rev3_verify/evidence.json")
    review_md = art("artifacts/worker-029/l0_rev3_verify/REVIEW.md")
    manifest = art("artifacts/worker-029/l0_rev3_verify/snapshot_manifest.json")
    digest = json.loads((ROOT / core["path"]).read_text())["digest"]

    ref = (f"{report['path']}#{report['sha256'][:12]}")
    ev = []

    ev.append({
        "event_id": "w029L0-20260912T0055-status-start",
        "event_type": "status", "created_at": now, "actor": "worker-029",
        "node_id": "L0", "class_id": FROZEN, "gate": "G-LIT", "task_id": TASK,
        "status": "active", "hours": 0.1,
        "summary": ("One class-bound task: independent deterministic full-L0 verdict at the live "
                    "ledger a1674f094979, taken to fill the single blocker named by "
                    "reviews/A1-rebind-coverage.json (L0 has one independent verdict at the measured "
                    "hash; >=2 needed). Read-only over canonical artifacts; no canonical write."),
        "evidence_refs": [f"{LEDGER}#{LEDGER_SHA[:12]}", f"ledger/citation_audit.csv#{L1_SHA[:12]}",
                          "reviews/A1-rebind-coverage.json"],
        "next_falsifier": ("Re-run check_l0_rev3.py on the same snapshots: the verdict is falsified "
                           "if any of the 8 HF-02 rows has fewer than two frozen class ids, if the "
                           "canonical HF-14 predicate fires on the live bytes, if the rev3 content "
                           "comparison shows a diff, or if two runs differ in digest."),
    })

    for eid, atype, a, note in [
        ("checker", "checker_code", checker,
         "Deterministic checker + controls (10 checks); writes only report_core/report/evidence."),
        ("snapshot-script", "snapshot_script", snap_script,
         "Freezes the 15 review inputs under snapshots/ with a hash manifest."),
        ("report", "audit_report", report,
         "Full checker output at the frozen bytes and real wall-clock measurement."),
        ("core", "deterministic_core", core,
         f"Deterministic core; digest {digest}."),
        ("evidence", "evidence", evidence,
         "Per-row evidence: HF-02 row set, class-binding counts, HF-14 pre/post control, linkage."),
        ("review-md", "summary", review_md,
         "One-page human-readable verdict pinned to the frozen hashes."),
        ("manifest", "snapshot_manifest", manifest,
         "15 snapshots with sha256, bytes, mtime; all live paths re-verified matching."),
    ]:
        ev.append({
            "event_id": f"w029L0-20260912T0055-artifact-{eid}",
            "event_type": "artifact", "created_at": now, "actor": "worker-029",
            "node_id": "L0", "class_id": FROZEN, "gate": "G-LIT", "task_id": TASK,
            "artifact_type": atype, "path": a["path"], "sha256": a["sha256"],
            "bytes": a["bytes"], "validation_status": "unverified", "note": note,
            "evidence_refs": [f"{LEDGER}#{LEDGER_SHA[:12]}"],
        })

    ev.append({
        "event_id": "w029L0-20260912T0055-review-l0rev3",
        "event_type": "review", "created_at": now, "actor": "worker-029",
        "reviewer": "worker-029", "target_id": "L0", "class_id": FROZEN, "gate": "G-LIT",
        "task_id": TASK, "artifact_path": LEDGER, "reviewed_sha256": LEDGER_SHA,
        "verdict": "revise", "score": 3.5,
        "independent": True, "author_of_target": False, "counts_as_full_schema_verdict": True,
        "companion_artifact": {"path": "ledger/citation_audit.csv", "sha256": L1_SHA},
        "hard_failures": [{
            "id": "HF-02", "check_id": "C7", "severity": "hard",
            "finding": ("class_ids disjunction on 8 rows, each carrying two frozen class ids in one "
                        "list; the frozen-class registry allows only one exact frozen class_id or a "
                        "(parent_class, variant_id) pair, and the rubric names this branch critical. "
                        "Neither implemented detector flags it (ledger branch checks invented tokens "
                        "only; class_separation flags merged or unknown tokens only), which is the A1 "
                        "coverage gap the author records as BL-6 and leaves unfixed at this hash."),
            "rows": HF02_ROWS,
            "evidence": [f"{evidence['path']}#{evidence['sha256'][:12]}",
                         f"{LEDGER}#{LEDGER_SHA[:12]}",
                         "evaluation_rubric.yaml#HF-02", "artifacts/formulation/VARIANT_REGISTRY.json"],
            "falsifier": ("Show that the 8 rows no longer carry two frozen class ids at this hash, or "
                          "a controller/rubric ruling that a multi-class class_ids list is an allowed "
                          "binding form."),
        }],
        "findings": [
            {"id": "W029L0-01", "check_id": "C4", "severity": "closed",
             "finding": ("HF-14 closed at this hash: no row carries status/validation_status/"
                         "supports_claim; content_status + author_asserts_supports + review_status "
                         "present on 62/62; canonical predicate 0 violations here vs 60 at the "
                         "archived pre-rev3 bytes under the same code."),
             "evidence": [f"{evidence['path']}#{evidence['sha256'][:12]}"]},
            {"id": "W029L0-02", "check_id": "C5", "severity": "closed",
             "finding": ("rev3 rename is content-preserving and claim-lowering: 18 content keys, 62 "
                         "rows, 0 diffs and 0 rename mismatches against the archive."),
             "evidence": [f"{evidence['path']}#{evidence['sha256'][:12]}"]},
            {"id": "W029L0-03", "check_id": "C6", "severity": "info",
             "finding": ("HF-01 does not fire on ledger records: the detector is claim-scoped and 0 "
                         "ledger rows enter the canonical claim corpus; all 30 theorem rows carry "
                         "source_ids. Residual is the conclusion_type vocabulary collision recorded "
                         "by the author as BL-5. This disagrees with reviews/L0-review-093.json, "
                         "which listed HF-01 as a hard failure."),
             "evidence": ["evaluation_rubric.yaml#HF-01",
                          "artifacts/audit/audit_run.py:100-119",
                          f"reviews/L0-review-093.json"]},
            {"id": "W029L0-04", "check_id": "C3", "severity": "major",
             "finding": ("class-binding metric 26/62 = 0.4194 against the A0 target 1.0; 28 rows "
                         "carry no class binding. Same root as HF-02 and left for the formulation "
                         "ruling."),
             "evidence": [f"{evidence['path']}#{evidence['sha256'][:12]}"]},
            {"id": "W029L0-05", "check_id": "C8", "severity": "major",
             "finding": ("citation linkage holds: 92 cited sources, 0 missing audit rows, 0 "
                         "non-verified verdicts, 0 row classes uncovered by the source mapping; "
                         "97/97 audit rows resolved with HTTP 200."),
             "evidence": [f"ledger/citation_audit.csv#{L1_SHA[:12]}"]},
            {"id": "W029L0-06", "check_id": "C9", "severity": "info",
             "finding": ("G-LIT's four row-level criteria are met at this hash: verification_status "
                         "honest (61 abstract-read + 1 unverified, 0 rows above abstract-read), 62/62 "
                         "unresolved marked, 22 distinct spot-check reviewers across 33 files at the "
                         "L1 hash, locators resolved. G-LIT stays open on the L0 node verdict, not "
                         "on a row-level criterion."),
             "evidence": ["reviews/A1-rebind-coverage.json"]},
            {"id": "W029L0-07", "check_id": "C3", "severity": "minor",
             "finding": ("declaration-mode class_separation.py flags exactly one ledger field, "
                         "T-402.regularity, as a bare composite; prose mode 0. T-402 is already in "
                         "the HF-02 row set, so this is recorded as a soft finding, not a separate "
                         "hard failure."),
             "evidence": [f"{evidence['path']}#{evidence['sha256'][:12]}"]},
        ],
        "peer_work_at_same_hash": {
            "reviews/L0-review-093.json": {"verdict": "revise", "same_hf02_row_set": True},
            "artifacts/worker-023/l0_hf02/hf02-disjunction-adjudication-023.json": {
                "same_hf02_row_set": True, "patch_applied": False},
        },
        "evidence_refs": [ref, f"{core['path']}#{core['sha256'][:12]}",
                          f"{evidence['path']}#{evidence['sha256'][:12]}",
                          f"{review_md['path']}#{review_md['sha256'][:12]}"],
        "falsifier": ("Re-run check_l0_rev3.py on the same snapshots: falsified if any HF-02 row has "
                      "fewer than two frozen class ids, if any other row carries two or more, if the "
                      "canonical HF-14 predicate fires on the live bytes, if the rev3 content "
                      "comparison shows a diff, if a control fails, or if two runs differ in digest. "
                      "A moved ledger hash supersedes this verdict rather than falsifying it."),
    })

    ev.append({
        "event_id": "w029L0-20260912T0055-claim-l0rev3",
        "event_type": "claim", "created_at": now, "actor": "worker-029",
        "node_id": "L0", "class_id": FROZEN, "gate": "G-LIT", "task_id": TASK,
        "conclusion_type": "numerical_evidence",
        "artifact_refs": [f"{report['path']}#{report['sha256'][:12]}",
                          f"{core['path']}#{core['sha256'][:12]}",
                          f"{evidence['path']}#{evidence['sha256'][:12]}",
                          f"{checker['path']}#{checker['sha256'][:12]}"],
        "statement": (
            "Deterministic measurement at the frozen L0 rev3 bytes a1674f094979 (62 rows) with "
            "companion audit 315c19145065 (97 rows), verified live at emission: 9 of 10 checks PASS "
            "and exactly one hard check FAILS. Closed here: HF-14 (0 live predicate violations vs 60 "
            "at the pre-rev3 archive ce42d205e761 under the same canonical predicate), the rev3 "
            "rename is content-preserving on 62 rows and claim-lowering, the class-token census is "
            "frozen-four-only (42 class_ids tokens + 7 informs_classes values, 0 unknown), and "
            "citation linkage is complete (92 cited sources, 0 missing, 0 non-verified, 97/97 "
            "resolved). Open: HF-02 disjunction on 8 named rows (D-004, D-005, T-303, T-305, T-402, "
            "T-515, T-526, T-528) under the rubric's literal branch and the frozen-class registry's "
            "two allowed binding forms, with 0 hits from the two implemented detectors; class "
            "binding 26/62 = 0.4194. HF-01 is not applicable to ledger records (claim-scoped "
            "detector, 0 rows in the canonical claim corpus, all 30 theorem rows carry source_ids), "
            "disagreeing with reviews/L0-review-093.json. Verdict revise 3.5 at this hash. Worker "
            "evidence only: no gate verdict, node status, or validation_status is claimed."),
        "assumptions": [
            "The verdict binds only to the frozen snapshots under "
            "artifacts/worker-029/l0_rev3_verify/snapshots/ and their manifest hashes; all 15 live "
            "paths matched at emission.",
            "The A0 detector texts are read literally from the snapshotted evaluation_rubric.yaml "
            "d748a9e3574e.",
            "The frozen-class registry rule is read from the snapshotted "
            "artifacts/formulation/VARIANT_REGISTRY.json 5eb42f9a384a.",
            "The canonical HF-14 predicate and the ledger token check are reimplemented verbatim "
            "from the snapshotted audit_lib.py ae573db84631 / audit_run.py 3b27dd3fef7f and "
            "exercised on both live and archived bytes as controls.",
            "A worker review is evidence only: it cannot set a gate verdict, node status, or "
            "validation_status; lead-audit and the controller adjudicate.",
        ],
        "falsifier": ("Re-run check_l0_rev3.py on the same snapshots: the measurement is falsified "
                      "if any PASS check reports FAIL, if the HF-02 row set differs, if the HF-14 "
                      "positive control does not reproduce 60 pre-rev3 violations, or if two runs "
                      "differ in digest. A live ledger hash different from a1674f094979 supersedes "
                      "the measurement."),
        "evidence_refs": [f"{LEDGER}#{LEDGER_SHA[:12]}",
                          f"ledger/citation_audit.csv#{L1_SHA[:12]}",
                          f"{evidence['path']}#{evidence['sha256'][:12]}"],
    })

    ev.append({
        "event_id": "w029L0-20260912T0055-blocker-hf02",
        "event_type": "blocker", "created_at": now, "actor": "worker-029",
        "node_id": "L0", "class_id": FROZEN, "gate": "G-LIT", "task_id": TASK,
        "severity": "high",
        "description": (
            "L0 rev3 still carries the HF-02 class_ids disjunction on 8 rows at a1674f094979: "
            "D-004, D-005, T-303, T-305, T-402, T-515, T-526, T-528 each bind two frozen class ids "
            "in one class_ids list, which is neither of the two binding forms the frozen-class "
            "registry allows. The two implemented detectors report 0, so the defect is invisible to "
            "the current A1 tooling (author's BL-6, unfixed). The rev3 rename closed HF-14; HF-01 "
            "does not apply to ledger records (BL-5 vocabulary collision)."),
        "needed_to_unblock": (
            "Literature/formulation content decision, per row: keep one frozen class in class_ids "
            "and move the second to informs_classes or to a registered (parent_class, variant_id) "
            "reference, or record a formulation ruling that a row genuinely binding two frozen "
            "classes is an allowed form. In parallel, align the A1 detectors with the rubric's "
            "disjunction branch so this class of defect cannot be invisible again. No self-review: "
            "an independent verdict at the new hash is still required."),
        "evidence_refs": [f"{evidence['path']}#{evidence['sha256'][:12]}",
                          f"{LEDGER}#{LEDGER_SHA[:12]}",
                          "evaluation_rubric.yaml#HF-02"],
        "stop_rule": ("No further measurement from this worker on this hash. Any ledger revision "
                      "that changes a1674f094979 voids this verdict and needs a fresh snapshot."),
    })

    ev.append({
        "event_id": "w029L0-20260912T0055-status-complete",
        "event_type": "status", "created_at": now, "actor": "worker-029",
        "node_id": "L0", "class_id": FROZEN, "gate": "G-LIT", "task_id": TASK,
        "status": "active", "hours": 0.5,
        "summary": (
            "W029-L0-REV3-VERDICT-05 complete at worker level: second independent full-L0 verdict "
            "at a1674f094979, all artifacts exist on disk and are hash-pinned, two runs are "
            "byte-identical (digest 2895748700ac), all 15 snapshots and live paths match. Verdict "
            "revise 3.5, one hard failure HF-02 on 8 rows; HF-14 closed; HF-01 not applicable. "
            "Fills the single blocker in reviews/A1-rebind-coverage.json (L0 one independent verdict "
            "at the measured hash). This is a completion claim, not a node transition. Checkpoint: "
            "runtime/state/w029_l0_rev3_checkpoint.json."),
        "evidence_refs": [ref, f"{evidence['path']}#{evidence['sha256'][:12]}",
                          f"{review_md['path']}#{review_md['sha256'][:12]}"],
        "next_falsifier": ("Re-run check_l0_rev3.py on the same snapshots: falsified if any PASS "
                           "check reports FAIL, if the HF-02 row set differs, or if two runs differ "
                           "in digest; superseded if the live ledger hash moves."),
    })

    # validate + class-separation self-check, then append
    out = ROOT / "comms" / "outbox" / "worker-029.jsonl"
    lines, problems = [], []
    for e in ev:
        try:
            validate_event(dict(e))
        except Exception as ex:
            problems.append(f"{e['event_id']}: {ex}")
        f = cs.findings(e, e["event_id"])
        if f:
            problems.append(f"{e['event_id']}: classsep {f}")
        lines.append(json.dumps(e, ensure_ascii=False))
    if problems:
        print("VALIDATION FAILED:\n" + "\n".join(problems))
        return 2
    with out.open("a") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"appended {len(lines)} validated events to {out.relative_to(ROOT)}")
    for e in ev:
        print("  ", e["event_id"], e["event_type"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
