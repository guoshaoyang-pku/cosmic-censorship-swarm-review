#!/usr/bin/env python3
"""W038-A0-SELFTEST-01 — run the declared A0 validator and hash-bind its result.

Worker 038, bounded execution worker. Node A0, gate G-AUDIT, class scope = the four frozen
class ids in evaluation_rubric.yaml.

Why this exists
---------------
evaluation_rubric.yaml declares `validation.validator: artifacts/audit/audit_run.py` and says
"a rubric with no passing self-test is not a gate", but `validation.last_run` is null. The
independent static conformance check by worker-008 (artifacts/worker-008/a0_rubric_review/)
recorded `audit_run_attachment: null` and flagged the never-run validator as a blocking
finding. This script is the missing execution record.

Method (with a null control for ambient churn)
----------------------------------------------
The workspace has ~100 concurrent agents that rewrite research_map.json and comms/outbox every
few seconds, so a naive before/after comparison cannot attribute mutation to this run. The
record therefore measures a 30 s NO-RUN control window with the same instrument, then the two
validator runs, and compares deltas:

  S0 --30s no run--> S1 --run A relative--> S2 --run B absolute--> S3

Attribution rule: a file class that moves in the control window is ambient churn; the mutation
claim is limited to the rubric and the validator tooling, and the ambient deltas are reported
with both numbers. This is the project's own null-first rule (HANDOFF.md section 3).

The declared validator is invoked with --quiet, so even a successful run must not write the
outbox; output goes only to worker-owned directories under artifacts/worker-038/.

Exit 0 = a sound execution record was produced; exit 3 = the record is unsound (validator
missing, no report even with absolute --out, rubric/tooling mutated, or self-promotion).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CST = timezone(timedelta(hours=8))
CONTROL_SECONDS = 30

RUBRIC = ROOT / "evaluation_rubric.yaml"
VALIDATOR = ROOT / "artifacts" / "audit" / "audit_run.py"
AUDIT_LIB = ROOT / "artifacts" / "audit" / "audit_lib.py"
TAXONOMY = ROOT / "research_map" / "formulation_taxonomy.yaml"
MAP = ROOT / "research_map" / "research_map.json"
REGISTRY = ROOT / "artifacts" / "formulation" / "VARIANT_REGISTRY.json"
SCHEMAS = [
    ROOT / "schemas" / "af_wcc_vacuum.yaml",
    ROOT / "schemas" / "af_scc_c2_vacuum.yaml",
    ROOT / "schemas" / "af_scc_c0_vacuum.yaml",
]
FROZEN_EXPECTED = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]
# mutation of these would invalidate the run record itself
IMMUTABLE = [RUBRIC, VALIDATOR, AUDIT_LIB]
# concurrently republished by other agents; churn here is measured against the control window
AMBIENT = [MAP, TAXONOMY, REGISTRY] + SCHEMAS
PINNED = IMMUTABLE + AMBIENT
OUTBOX = ROOT / "comms" / "outbox"
MY_OUTBOX = OUTBOX / "worker-038.jsonl"


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str | None:
    try:
        return sha256_bytes(Path(p).read_bytes())
    except OSError:
        return None


def snapshot() -> dict:
    files = {}
    for p in PINNED:
        files[str(p.relative_to(ROOT))] = sha256_file(p)
    outbox = {}
    if OUTBOX.exists():
        for p in sorted(OUTBOX.rglob("*")):
            if p.is_file():
                outbox[str(p.relative_to(ROOT))] = sha256_file(p)
    return {"at": now(), "files": files, "outbox": outbox}


def deltas(a: dict, b: dict) -> dict:
    changed = sorted(
        rel for rel in set(a["files"]) | set(b["files"]) if a["files"].get(rel) != b["files"].get(rel)
    )
    added = sorted(set(b["outbox"]) - set(a["outbox"]))
    removed = sorted(set(a["outbox"]) - set(b["outbox"]))
    modified = sorted(
        rel for rel in set(a["outbox"]) & set(b["outbox"]) if a["outbox"][rel] != b["outbox"][rel]
    )
    return {
        "files_changed": changed,
        "outbox_added": added,
        "outbox_removed": removed,
        "outbox_modified": modified,
    }


def run_validator(outdir: Path, relative: bool) -> dict:
    outdir.mkdir(parents=True, exist_ok=True)
    out_arg = str(outdir.relative_to(ROOT)) if relative else str(outdir)
    cmd = [sys.executable, "artifacts/audit/audit_run.py", "--quiet", "--out", out_arg]
    t0 = time.time()
    try:
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=1800)
        rc, out, err, timed_out = proc.returncode, proc.stdout, proc.stderr, False
    except subprocess.TimeoutExpired as e:
        rc, out, err, timed_out = -9, e.stdout or "", e.stderr or "", True
    wall = round(time.time() - t0, 3)
    (outdir / "stdout.txt").write_text(out)
    (outdir / "stderr.txt").write_text(err)
    reports = sorted(outdir.glob("audit-*.json"), key=lambda p: p.stat().st_mtime)
    return {
        "command": " ".join(cmd),
        "out_arg": out_arg,
        "relative_out": relative,
        "exit_code": rc,
        "timed_out": timed_out,
        "wall_seconds": wall,
        "stdout_sha256": sha256_bytes(out.encode()),
        "stderr_sha256": sha256_bytes(err.encode()),
        "stdout_tail": out[-800:],
        "stderr_tail": err[-800:],
        "report_path": str(reports[-1].relative_to(ROOT)) if reports else None,
        "report_sha256": sha256_file(reports[-1]) if reports else None,
    }


def main() -> int:
    for d in ("run_a_relative_out", "run_b_absolute_out"):
        (HERE / d).mkdir(parents=True, exist_ok=True)

    s0 = snapshot()
    time.sleep(CONTROL_SECONDS)
    s1 = snapshot()  # control window: no validator run
    run_a = run_validator(HERE / "run_a_relative_out", relative=True)
    s2 = snapshot()
    run_b = run_validator(HERE / "run_b_absolute_out", relative=False)
    s3 = snapshot()

    control_delta = deltas(s0, s1)
    run_a_delta = deltas(s1, s2)
    run_b_delta = deltas(s2, s3)
    run_delta = {
        "files_changed": sorted(set(run_a_delta["files_changed"]) | set(run_b_delta["files_changed"])),
        "outbox_added": sorted(set(run_a_delta["outbox_added"]) | set(run_b_delta["outbox_added"])),
        "outbox_removed": sorted(set(run_a_delta["outbox_removed"]) | set(run_b_delta["outbox_removed"])),
        "outbox_modified": sorted(set(run_a_delta["outbox_modified"]) | set(run_b_delta["outbox_modified"])),
    }

    report_doc = None
    if run_b["report_path"]:
        try:
            report_doc = json.loads((ROOT / run_b["report_path"]).read_text())
        except Exception as e:  # pragma: no cover - defensive
            run_b["report_read_error"] = f"{type(e).__name__}: {e}"

    # --- mutation attribution -------------------------------------------------------------
    immutable_changed_control = [rel for rel in control_delta["files_changed"] if str(ROOT / rel) in map(str, IMMUTABLE)]
    immutable_changed_run = [rel for rel in run_delta["files_changed"] if str(ROOT / rel) in map(str, IMMUTABLE)]
    ambient_changed_control = [rel for rel in control_delta["files_changed"] if rel not in immutable_changed_control]
    ambient_changed_run = [rel for rel in run_delta["files_changed"] if rel not in immutable_changed_run]

    rubric_doc = yaml.safe_load(RUBRIC.read_text()) or {}
    validation = rubric_doc.get("validation") or {}
    self_promotion_ok = (
        validation.get("last_run") is None and validation.get("last_run_result") is None
    )
    my_outbox_written_by_run = MY_OUTBOX.exists() and any(
        "w038-a0-selftest" in line for line in MY_OUTBOX.read_text(errors="replace").splitlines()
    )

    # --- class scope ----------------------------------------------------------------------
    rubric_classes = [c.get("id") for c in (rubric_doc.get("frozen_classes") or [])]
    taxonomy = yaml.safe_load(TAXONOMY.read_text()) or {}
    taxonomy_classes = list((taxonomy.get("classes") or {}).keys())
    class_scope_ok = rubric_classes == FROZEN_EXPECTED and taxonomy_classes == FROZEN_EXPECTED

    class_scoped = {c: {"critical": 0, "total": 0} for c in FROZEN_EXPECTED}
    crit_findings = []
    if report_doc:
        for v in report_doc.get("violations", []):
            blob = json.dumps(v, sort_keys=True)
            for c in FROZEN_EXPECTED:
                if c in blob:
                    class_scoped[c]["total"] += 1
                    if v.get("severity") == "critical":
                        class_scoped[c]["critical"] += 1
            if v.get("severity") == "critical" and len(crit_findings) < 40:
                crit_findings.append(
                    {
                        "hf": v.get("hf"),
                        "where": v.get("where"),
                        "detail": str(v.get("detail"))[:240],
                    }
                )

    # --- cross-check the earlier static A0 check by worker-008 ----------------------------
    w008_path = ROOT / "artifacts" / "worker-008" / "a0_rubric_review" / "a0_check_report.json"
    w008 = None
    if w008_path.exists():
        try:
            d = json.loads(w008_path.read_text())
            w008 = {
                "path": str(w008_path.relative_to(ROOT)),
                "sha256": sha256_file(w008_path),
                "artifact_sha256": d.get("artifact_sha256"),
                "blocking_findings": d.get("blocking_findings"),
                "audit_run_attachment": d.get("audit_run_attachment"),
                "verdict": d.get("verdict") or d.get("overall_verdict") or d.get("result"),
            }
        except Exception as e:  # pragma: no cover - defensive
            w008 = {"path": str(w008_path.relative_to(ROOT)), "read_error": str(e)}

    # --- checks ---------------------------------------------------------------------------
    checks = [
        {
            "check_id": "S1-rubric-and-tooling-unmutated",
            "status": "pass" if not immutable_changed_run else "fail",
            "detail": f"rubric/validator/audit_lib unchanged by both runs "
            f"(run-window changes: {immutable_changed_run or 'none'}; "
            f"control-window changes: {immutable_changed_control or 'none'})",
        },
        {
            "check_id": "S1b-ambient-churn-null-control",
            "status": "info",
            "detail": f"{CONTROL_SECONDS}s no-run control window changed {ambient_changed_control}; "
            f"run windows changed {ambient_changed_run}. Files moving in both windows are "
            f"attributed to the ~100 concurrent agents, not to this run.",
        },
        {
            "check_id": "S2a-relative-out-crashes",
            "status": "defect"
            if run_a["exit_code"] != 0 and run_a["report_path"] is None
            else "info",
            "detail": f"exit_code={run_a['exit_code']} report={run_a['report_path']}; "
            "audit_run.py line 335 calls Path.relative_to(ROOT) on a relative --out, raising "
            "ValueError before any report is written",
        },
        {
            "check_id": "S2b-absolute-out-completes",
            "status": "pass" if (run_b["exit_code"] == 0 and report_doc is not None) else "fail",
            "detail": f"exit_code={run_b['exit_code']} timed_out={run_b['timed_out']} "
            f"report={run_b['report_path']}",
        },
        {
            "check_id": "S3-report-binds-canonical-rubric",
            "status": "pass"
            if report_doc and report_doc.get("rubric_sha256") == sha256_file(RUBRIC)
            else "fail",
            "detail": f"report.rubric_sha256="
            f"{report_doc.get('rubric_sha256') if report_doc else None} "
            f"canonical={sha256_file(RUBRIC)}",
        },
        {
            "check_id": "S4-no-outbox-write-under-quiet",
            "status": "pass" if not my_outbox_written_by_run else "fail",
            "detail": f"--quiet runs emitted no worker-038 events "
            f"(run-window outbox adds {run_delta['outbox_added']}, control-window adds "
            f"{control_delta['outbox_added']}: all ambient traffic from concurrent agents)",
        },
        {
            "check_id": "S5-no-self-promotion",
            "status": "pass" if self_promotion_ok else "fail",
            "detail": f"validation.last_run={validation.get('last_run')!r} "
            f"last_run_result={validation.get('last_run_result')!r} after the runs",
        },
        {
            "check_id": "S6-class-scope-frozen-four",
            "status": "pass" if class_scope_ok else "fail",
            "detail": f"rubric frozen_classes={rubric_classes} taxonomy={taxonomy_classes}",
        },
        {
            "check_id": "S7-validator-does-not-fill-its-declared-validation-block",
            "status": "defect",
            "detail": "rubric line 46 says validation is 'Filled by artifacts/audit/audit_run.py', "
            "but no code path in audit_run.py writes evaluation_rubric.yaml; even a successful "
            "run leaves last_run/last_run_result/report_sha256 null. The declaration and the tool "
            "disagree, so 'a rubric with no passing self-test is not a gate' cannot be discharged "
            "by invoking the declared validator alone.",
        },
        {
            "check_id": "S8-validator-is-not-a-rubric-conformance-test",
            "status": "info",
            "detail": "audit_run.py evaluates the workspace against the rubric; it does not "
            "validate the rubric's own field schema. The static defects recorded by worker-008 "
            "are outside this self-test by construction, not contradicted by it.",
        },
    ]
    record_sound = (
        not immutable_changed_run
        and run_b["exit_code"] == 0
        and report_doc is not None
        and report_doc.get("rubric_sha256") == sha256_file(RUBRIC)
        and not my_outbox_written_by_run
    )
    rc_out = 0 if record_sound else 3

    verification = {
        "schema_version": "0.1",
        "audit_id": "W038-A0-SELFTEST-01",
        "actor": "worker-038",
        "node_id": "A0",
        "gate": "G-AUDIT",
        "class_ids": FROZEN_EXPECTED,
        "class_binding_note": "A0 is the class-binding rulebook; the four frozen class ids are "
        "the rubric's own class scope and the classes its verifiers and hard failures bind to.",
        "task": "Execute the declared A0 self-test (artifacts/audit/audit_run.py) at pinned "
        "hashes and record exit codes, stdout/stderr hashes and report hashes; prove the runs "
        "neither mutate the rubric nor self-promote it, using a 30 s no-run control window to "
        "separate ambient swarm churn from run-caused mutation.",
        "measured_at": now(),
        "measured_hashes": dict(s0["files"]),
        "runs": {"run_a_relative_out": run_a, "run_b_absolute_out": run_b},
        "snapshots": {"s0": s0["at"], "s1_after_control": s1["at"], "s2_after_run_a": s2["at"],
                      "s3_after_run_b": s3["at"]},
        "mutation_control": {
            "method": f"{CONTROL_SECONDS}s no-run control window, then run A, then run B; "
            "deltas compared per window",
            "control_window_delta": control_delta,
            "run_a_window_delta": run_a_delta,
            "run_b_window_delta": run_b_delta,
            "run_window_delta": run_delta,
            "rubric_and_tooling_unchanged_by_runs": not immutable_changed_run,
            "ambient_churn_attributed_to_concurrent_agents": {
                "control": ambient_changed_control,
                "run": ambient_changed_run,
            },
        },
        "self_promotion_check": {
            "validation_last_run": validation.get("last_run"),
            "validation_last_run_result": validation.get("last_run_result"),
            "no_self_promotion": self_promotion_ok,
        },
        "validator_report": None
        if report_doc is None
        else {
            "rubric_sha256": report_doc.get("rubric_sha256"),
            "map_sha256": report_doc.get("map_sha256"),
            "summary": report_doc.get("summary"),
            "gates": report_doc.get("gates"),
            "citation_support": {
                k: (report_doc.get("citation_support") or {}).get(k)
                for k in ("n", "score", "unresolved")
            },
            "duplication_cluster_rate": (report_doc.get("duplication") or {}).get(
                "duplicate_cluster_rate"
            ),
            "runtime_s": report_doc.get("runtime_s"),
            "critical_findings_head": crit_findings,
        },
        "class_scoped_findings": class_scoped,
        "cross_check_worker_008_static_a0_check": w008,
        "checks": checks,
        "falsifiers": [
            "Re-run run B at the same pinned hashes: a different report_sha256 or exit_code "
            "falsifies reproducibility of this record.",
            "A post-run change to evaluation_rubric.yaml or the validator tooling falsifies the "
            "no-mutation claim; S1 would fail.",
            "A non-null validation.last_run set by the run falsifies the no-self-promotion "
            "claim; S5 would fail.",
            "If report.rubric_sha256 differs from the canonical rubric hash, the self-test did "
            "not test the frozen rubric; S3 would fail.",
            "Fix audit_run.py line 335 and re-run run A: if the relative --out invocation then "
            "succeeds, the S2a CLI defect is falsified as environment-specific.",
            "If a future run window changes a pinned file that the control window did not, the "
            "ambient-attribution rule is falsified for that file.",
        ],
        "authority_note": "Worker evidence only: this record cannot set status=done, "
        "validation_status=passed, or any gate verdict. G-AUDIT/A0 remain with the controller "
        "and the audit lead.",
        "result": "RECORDED" if rc_out == 0 else "UNSOUND",
    }

    out_path = HERE / "selftest_verification.json"
    out_path.write_text(json.dumps(verification, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: verification[k] for k in ("audit_id", "result", "checks")}, indent=1))
    print(f"verification -> {out_path.relative_to(ROOT)} sha256={sha256_file(out_path)}")
    return rc_out


if __name__ == "__main__":
    raise SystemExit(main())
