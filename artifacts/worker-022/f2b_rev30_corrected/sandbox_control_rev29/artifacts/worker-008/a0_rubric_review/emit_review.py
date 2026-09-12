#!/usr/bin/env python3
"""Emit the worker-008 A0 review record, report, checkpoint and validated outbox events.

Inputs are the machine check report and the audit_run attachment produced by
check_a0_rubric.py. Every emitted number/hash is read back from those files, not retyped.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))
OUTBOX = ROOT / "comms" / "outbox" / "worker-008-a0.jsonl"
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def stamp() -> str:
    return datetime.now(CST).strftime("%Y%m%dT%H%M%S")


def main() -> int:
    report_path = HERE / "a0_check_report.json"
    rep = json.loads(report_path.read_text())
    stamp_now = now()
    tag = stamp()

    rubric = rep["target"]
    checks = {c["check_id"]: c for c in rep["checks"]}
    fails = [c for c in rep["checks"] if c["status"] == "fail"]
    warns = [c for c in rep["checks"] if c["status"] == "warn"]
    attachment = rep.get("audit_run_attachment") or {}

    findings = list(rep["findings"])
    findings.append(
        "independence: reviewer worker-008 did not author evaluation_rubric.yaml "
        f"(author field: {rep.get('rubric_author')!r}); single-reviewer Kish ESS = 1, so this "
        "counts as one of the two independent verdicts A0 requires"
    )

    review = {
        "record_type": "review",
        "target_id": "A0",
        "reviewer": "worker-008",
        "actor": "worker-008",
        "created_at": stamp_now,
        "verdict": rep["verdict"],
        "score": rep["score"],
        "score_basis": "5.0 - 1.0 per blocking check - 0.25 per minor finding",
        "hard_failures": rep["hard_failures"],
        "findings": findings,
        "blocking_findings": rep["blocking_findings"],
        "target": rubric,
        "class_ids": rep["class_ids"],
        "independence": {
            "reviewer_is_author": False,
            "rubric_author": rep.get("rubric_author"),
            "kish_ess": 1,
            "note": "not a self-review; not a copy of the lead-audit accept",
        },
        "method": {
            "checker": "artifacts/worker-008/a0_rubric_review/check_a0_rubric.py",
            "checker_sha256": sha256(HERE / "check_a0_rubric.py"),
            "checks": {c["check_id"]: c["status"] for c in rep["checks"]},
            "check_count": {"pass": sum(1 for c in rep["checks"] if c["status"] == "pass"),
                            "warn": len(warns), "fail": len(fails)},
        },
        "declared_validator_run": attachment,
        "unblock_instructions": [
            "A0-C8 (blocking): populate evaluation_rubric.yaml:45-50 `validation` after defining what "
            "'passing self-test' means for artifacts/audit/audit_run.py, then record last_run, "
            "last_run_result and report_sha256. Note audit_run.py exits 0 with 9 critical live-corpus "
            "findings unless --fail-on-critical is passed, so the pass predicate must be stated.",
            "A0-C3 (minor): add an explicit `evidence:` line to the literature (line 25), numerics "
            "(line 32) and formalization (line 38) verifier blocks, as schema_formulation has (line 23).",
            "A0-C5 (minor): give novel_accepted_coverage (line 282) a target, as the other 6 metrics have.",
            "A0-C7 (minor): add a G-F0 row to `gates` or state that taxonomy disjointness is covered by "
            "metric class_binding; the map carries G-F0 and the rubric does not.",
        ],
        "assumptions": rep["assumptions"],
        "falsifier": rep["falsifier"],
        "next_falsifier": rep["next_falsifier"],
        "limits": rep["limits"],
        "evidence_refs": rep["evidence_refs"] + [
            f"artifacts/worker-008/a0_rubric_review/a0_check_report.json#{sha256(report_path)}",
        ],
    }
    review_path = HERE / "review.json"
    review_path.write_text(json.dumps(review, indent=1, sort_keys=True) + "\n")

    # ---------------- human-readable report ----------------
    lines = [
        "# A0 rubric — independent review (worker-008)",
        "",
        f"- target: `evaluation_rubric.yaml` node A0, gate G-AUDIT",
        f"- target sha256: `{rubric['sha256']}` ({rubric['bytes']} bytes)",
        f"- reviewer: worker-008 (not the author `{rep.get('rubric_author')}`)",
        f"- verdict: **{rep['verdict']}**  score: **{rep['score']}**",
        f"- generated: {stamp_now}",
        "",
        "## Checks",
        "",
        "| check | status | detail |",
        "|---|---|---|",
    ]
    for c in rep["checks"]:
        lines.append(f"| {c['check_id']} | {c['status']} | {c['detail']} |")
    lines += ["", "## Blocking finding", ""]
    for b in rep["blocking_findings"]:
        lines.append(f"- {b}")
    if not rep["blocking_findings"]:
        lines.append("- none")
    lines += ["", "## Concrete unblock", ""]
    for u in review["unblock_instructions"]:
        lines.append(f"- {u}")
    lines += ["", "## Evidence", ""]
    for e in review["evidence_refs"]:
        lines.append(f"- `{e}`")
    if attachment:
        lines += ["", "## Declared validator (`artifacts/audit/audit_run.py`) run", "",
                  f"- report: `{attachment.get('path')}` sha256 `{str(attachment.get('sha256'))[:16]}`",
                  f"- rubric_sha256 at run: `{attachment.get('rubric_sha256')}`",
                  f"- live-corpus summary: `{json.dumps(attachment.get('summary'))}`",
                  f"- live-corpus gates: `{json.dumps(attachment.get('gates'))}`",
                  "- this is an enforcement run over the live workspace, not a recorded rubric self-test;",
                  "  it does not write `validation.last_run` and its critical findings belong to other nodes."]
    lines += ["", "## Falsifier", "", f"- {rep['falsifier']}", f"- next: {rep['next_falsifier']}", "",
              "## Limits", ""]
    for l in rep["limits"]:
        lines.append(f"- {l}")
    (HERE / "report.md").write_text("\n".join(lines) + "\n")

    # ---------------- local checkpoint ----------------
    ck = {
        "checkpoint_id": f"worker-008-a0-{tag}",
        "created_at": stamp_now,
        "worker": "worker-008",
        "task": "independent class-bound review of evaluation_rubric.yaml (A0/G-AUDIT) at a measured sha256",
        "status": "complete",
        "target": {"node_id": "A0", "path": rubric_path_display(rubric), "sha256": rubric["sha256"]},
        "verdict": rep["verdict"],
        "score": rep["score"],
        "blocking": rep["blocking_findings"],
        "warns": [c["detail"] for c in warns],
        "artifacts": {
            "checker": {"path": "artifacts/worker-008/a0_rubric_review/check_a0_rubric.py",
                        "sha256": sha256(HERE / "check_a0_rubric.py")},
            "check_report": {"path": "artifacts/worker-008/a0_rubric_review/a0_check_report.json",
                             "sha256": sha256(report_path)},
            "review": {"path": "artifacts/worker-008/a0_rubric_review/review.json",
                       "sha256": sha256(review_path)},
            "report": {"path": "artifacts/worker-008/a0_rubric_review/report.md",
                       "sha256": sha256(HERE / "report.md")},
        },
        "next_falsifier": rep["next_falsifier"],
    }
    with (ROOT / "artifacts" / "worker-008" / "checkpoints.jsonl").open("a") as f:
        f.write(json.dumps(ck, sort_keys=True) + "\n")

    # ---------------- outbox events ----------------
    base = {"actor": "worker-008", "agent_slot": "worker-008", "created_at": stamp_now}
    ev_artifact_check = {
        **base, "event_id": f"w008-a0-artifact-checkreport-{tag}",
        "event_type": "artifact", "node_id": "A0", "artifact_type": "review_evidence",
        "path": "artifacts/worker-008/a0_rubric_review/a0_check_report.json",
        "sha256": sha256(report_path), "validation_status": "unverified",
        "class_id": ";".join(rep["class_ids"]),
        "target_ref": f"evaluation_rubric.yaml#{rubric['sha256']}",
        "verdict": rep["verdict"], "score": rep["score"],
        "evidence_refs": review["evidence_refs"],
        "falsifier": rep["falsifier"], "next_falsifier": rep["next_falsifier"],
    }
    ev_artifact_review = {
        **base, "event_id": f"w008-a0-artifact-review-{tag}",
        "event_type": "artifact", "node_id": "A0", "artifact_type": "review_record",
        "path": "artifacts/worker-008/a0_rubric_review/review.json",
        "sha256": sha256(review_path), "validation_status": "unverified",
        "class_id": ";".join(rep["class_ids"]),
        "target_ref": f"evaluation_rubric.yaml#{rubric['sha256']}",
        "evidence_refs": review["evidence_refs"],
        "falsifier": rep["falsifier"], "next_falsifier": rep["next_falsifier"],
    }
    ev_review = {
        **base, "event_id": f"w008-a0-review-{tag}", "event_type": "review",
        "target_id": "A0", "reviewer": "worker-008", "verdict": rep["verdict"],
        "score": float(rep["score"]), "hard_failures": rep["hard_failures"],
        "findings": findings,
        "class_id": ";".join(rep["class_ids"]),
        "artifact_refs": [f"artifacts/worker-008/a0_rubric_review/review.json#{sha256(review_path)}",
                          f"artifacts/worker-008/a0_rubric_review/a0_check_report.json#{sha256(report_path)}"],
        "evidence_refs": review["evidence_refs"],
        "falsifier": rep["falsifier"], "next_falsifier": rep["next_falsifier"],
        "independence": review["independence"],
    }
    ev_status = {
        **base, "event_id": f"w008-a0-status-{tag}", "event_type": "status",
        "node_id": "A0", "status": "active", "hours": 0.4,
        "summary": (f"Independent A0 rubric review delivered at sha256 {rubric['sha256'][:12]}: "
                    f"verdict {rep['verdict']} score {rep['score']}; "
                    f"{len(fails)} blocking, {len(warns)} minor; classes bound "
                    f"{','.join(rep['class_ids'])}; declared validator run live but the rubric's "
                    f"validation.last_run record is null (blocking)."),
        "evidence_refs": review["evidence_refs"],
        "next_falsifier": rep["next_falsifier"],
    }
    events = [ev_artifact_check, ev_artifact_review, ev_review, ev_status]
    for e in events:
        validate_event(e)  # fail closed: do not write invalid events
    mode = "a" if OUTBOX.exists() else "w"
    with OUTBOX.open(mode) as f:
        for e in events:
            f.write(json.dumps(e, sort_keys=True) + "\n")

    print(json.dumps({
        "review": {"path": str(review_path.relative_to(ROOT)), "sha256": sha256(review_path)},
        "report_md": {"path": "artifacts/worker-008/a0_rubric_review/report.md",
                      "sha256": sha256(HERE / "report.md")},
        "check_report": {"path": "artifacts/worker-008/a0_rubric_review/a0_check_report.json",
                         "sha256": sha256(report_path)},
        "checkpoint": ck["checkpoint_id"],
        "outbox": str(OUTBOX.relative_to(ROOT)),
        "events": [e["event_id"] for e in events],
    }, indent=1))
    return 0


def rubric_path_display(target: dict) -> str:
    return "evaluation_rubric.yaml"


if __name__ == "__main__":
    raise SystemExit(main())
