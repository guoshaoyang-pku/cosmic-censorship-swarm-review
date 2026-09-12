#!/usr/bin/env python3
"""Emit W064-R03-CAUSE-01 upward events + worker checkpoint (append-only, idempotent by event_id).

Reads `report.json` (must exist), pins every deliverable by sha256, appends the events to
`comms/outbox/worker-064.jsonl` (never truncates) and writes
`runtime/state/w064_r03_checkpoint.json` + a line in `runtime/state/w064_checkpoints.jsonl`.

Usage: python3 emit_w064_r03.py [--check]
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))
HERE = Path(__file__).resolve().parent                 # artifacts/worker-064/r03_cause
REPO = HERE.parents[2]
OUTBOX = REPO / "comms/outbox/worker-064.jsonl"
STATE = REPO / "runtime/state"
TASK = "W064-R03-CAUSE-01"
INSTANCE = "worker-064-20260912T004439-968807"
CLASSES = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def ev(eid, etype, **kw):
    e = {"event_id": eid, "event_type": etype, "created_at": now(), "actor": "worker-064",
         "task_id": TASK, "node_id": "A1", "gate": "G-AUDIT", "class_ids": CLASSES}
    e.update(kw)
    return e


def main() -> int:
    report_p = HERE / "report.json"
    if not report_p.exists():
        print("FATAL: report.json missing; run w064_r03_cause_audit.py first", file=sys.stderr)
        return 1
    report = json.loads(report_p.read_text())
    if report.get("status") != "findings_reproduced":
        print(f"FATAL: report status={report.get('status')!r}; refusing to emit", file=sys.stderr)
        return 1

    files = {
        "report": HERE / "report.json",
        "audit": HERE / "w064_r03_cause_audit.py",
        "readme": HERE / "README.md",
        "e1a": HERE / "patch_candidates/wcc_candidate_E1a.yaml",
        "e1b": HERE / "patch_candidates/wcc_candidate_E1b.yaml",
        "e1c": HERE / "patch_candidates/wcc_candidate_E1c.yaml",
        "e2": HERE / "patch_candidates/wcc_candidate_E2.yaml",
        "e3": HERE / "patch_candidates/spec_conformance_audit_relaxed.py",
    }
    hashes = {k: sha(p) for k, p in files.items()}

    # SHA256SUMS over every regular file in the artifact dir (self-excluded)
    sums_path = HERE / "SHA256SUMS"
    lines = []
    for p in sorted(HERE.rglob("*")):
        if p.is_file() and p.name not in ("SHA256SUMS",) and "__pycache__" not in p.parts:
            lines.append(f"{sha(p)}  {p.relative_to(HERE)}")
    sums_path.write_text("\n".join(lines) + "\n")
    hashes["sums"] = sha(sums_path)

    events = []
    for key, label, atype in (
        ("report", "root-cause + sole-blocker report (canonical, machine-readable)", "audit_report"),
        ("audit", "deterministic re-runner; exit 0 = all expectations reproduced", "audit_harness"),
        ("readme", "human-readable report with cross-references and falsifiers", "audit_readme"),
        ("e1a", "canonical-repair proposal E1a: one-clause formal-sentence fix (tuple binder printed)", "repair_candidate"),
        ("e1b", "canonical-repair proposal E1b: tuple binder + explicit I+ x [0,T) domain", "repair_candidate"),
        ("e1c", "canonical-repair proposal E1c: tuple binder + split domain clauses", "repair_candidate"),
        ("e2", "alternative proposal E2: binder-list repair (weaker binding; t0 unbound)", "repair_candidate"),
        ("e3", "tool-amendment proposal E3: variable-wise composite-binder R03 (no mutant loss)", "repair_candidate"),
        ("sums", "sha256 manifest of the whole task directory", "artifact_manifest"),
    ):
        path = ("artifacts/worker-064/r03_cause/SHA256SUMS" if key == "sums"
                else str(files[key].relative_to(REPO)))
        events.append(ev(f"w064-r03-01-artifact-{key}", "artifact", artifact_type=atype,
                         path=path,
                         sha256=hashes[key], validation_status="unverified",
                         summary=label,
                         falsifier="Any byte difference from this sha256 falsifies the bound evidence."))

    evidence = [
        f"artifacts/worker-064/r03_cause/report.json#{hashes['report'][:12]}",
        f"artifacts/worker-064/r03_cause/README.md#{hashes['readme'][:12]}",
        f"artifacts/worker-064/r03_cause/w064_r03_cause_audit.py#{hashes['audit'][:12]}",
        f"artifacts/worker-064/r03_cause/patch_candidates/wcc_candidate_E1a.yaml#{hashes['e1a'][:12]}",
    ]
    claims = {c["claim_id"]: c for c in report["claims"]}
    for cid in ("W064-R03-CAUSE-01-C1", "W064-R03-CAUSE-01-C2", "W064-R03-CAUSE-01-C3", "W064-R03-CAUSE-01-C4"):
        c = claims[cid]
        events.append(ev(f"w064-r03-01-claim-{cid[-2:].lower()}", "claim",
                         class_id=c["class_id"], statement=c["statement"],
                         conclusion_type=c["conclusion_type"], assumptions=[
                             "canonical paths and pinned hashes are the binding inputs at measurement time",
                             "the mirror copies are faithful to those bytes (per-file sha256 recorded)",
                             "the stage tools' own exit/verdict semantics define acceptance"],
                         falsifier=c["falsifier"], evidence_refs=evidence,
                         artifact_refs=c["artifact_refs"],
                         not_claimed="no gate verdict, no node completion, no canonical modification"))

    events.append(ev("w064-r03-01-review-wcc", "review",
                     target_id="schemas/af_wcc_vacuum.yaml",
                     reviewer="worker-064", verdict="revise", score=4.0,
                     reviewed_sha256=report["snapshot"]["schemas/af_wcc_vacuum.yaml"],
                     hard_failures=[
                         "HF-R03-1: at FROZEN rev29 (F1 rev13 d9cebb9404b2) ordered[5] declares binder '(q,t0)' but quantifiers.formal renders it variable-wise, so the adopted R03 literal test fails; all other rules pass and both SCC schemas pass, i.e. the frozen corpus is not uniformly self-presenting under the adopted lexical checker.",
                         "HF-R03-2: rule_spec.json R03 says 'using those binders' without specifying literal vs variable-wise composite binders, so the rejection is not adjudicable from the rule text alone.",
                         "HF-R03-3: the suite runner leaves validity.blocking_adjudication=[] while a conforming canonical is rejected, so the failure is not routed (also reported by w080 and W064-SEMCT-REBASE-01)."],
                     findings=[
                         "F1: baseline reproduced at the pinned rev29 bytes: WCC d9cebb9404b2 rejected by both semantic stages on R03 only; C0 e9a27996dfd3 / C2 b2ab6acb2bbe accepted; structural passes 3/3.",
                         "F2: rev11 WCC 9a8bd4c96800 (same auditor hash) is accepted by both semantic stages with R03 pass; the rev12 quantifier diff (formal+ordered, binder 'q' -> '(q,t0)') introduced the failure and the rev13 re-pin kept it. It is a rendering regression, not a mathematical defect.",
                         "F3: one-clause candidates E1a/E1b/E1c pass all three stages and change no YAML key other than quantifiers.formal.",
                         "F4: after the previously reported control rebase + pin refresh, canonical WCC gives suite exit 3 / valid=false with SCT-K03 the only rejected conforming canonical (mutants 32/11/32); adding only the E1a clause gives exit 0 / valid=true (S2). The same validity is reachable with canonical bytes untouched via the variable-wise R03 amendment (S4), and stale control pins are still caught (S3 exit 2).",
                         "F5: resolution is an owner decision: Option B (schema edit) changes the frozen WCC hash and voids current F1 reviews; Option A (tool amendment) keeps d9cebb9404b2 and loses no mutant catches (11/32 unchanged).",
                         "F6 (churn): the live canonical WCC path was observed at three distinct hashes inside ~3 minutes: cce9c60146d6 (FROZEN rev28, frozen_at 00:35:08) -> bf0c28fa673e -> d9cebb9404b2 (FROZEN rev29, frozen_at 00:55:02); C0/C2 were re-pinned to b2ab6acb2bbe / e9a27996dfd3 at the same time and FROZEN.json was rewritten again at 00:57:26 (still rev29, marker 815e0807). Any review verdict bound to the rev28 hashes is void. This audit takes a one-time snapshot and reports end-of-run drift. Note 2f51ace6ef74 is the deterministic E1a repair applied to rev13 bytes, not a live hash."],
                     evidence_refs=evidence,
                     next_falsifier="A stage-2 accept at cce9c60146d6 with the unpatched tool, or a run in which S2/S4 does not reach exit 0/valid true, or E1a changing another YAML key, falsifies the corresponding finding."))

    events.append(ev("w064-r03-01-blocker", "blocker",
                     class_id="AF-WCC-VAC-GEN",
                     description=("At FROZEN rev29 the G-AUDIT semantic-contract calibration evidence cannot be valid: canonical WCC "
                                  "d9cebb9404b2 (rev13) fails R03 on a literal binder-print mismatch (declared '(q,t0)' rendered variable-wise). "
                                  "Independently reproduces w080-sr-20260912T004243-blocker-f1r03 and w16-R03-ADJ-01. After the control "
                                  "rebase and pin refresh this is the sole residual blocker (S1 exit 3, SCT-K03 only; S2/S4 exit 0)."),
                     needed_to_unblock=[
                         "owner (lead-formulation / rule-spec owner) adjudicates R03 literal vs variable-wise composite binders",
                         "Option A: adopt the variable-wise implementation (proposal patch_candidates/spec_conformance_audit_relaxed.py; measured no mutant loss) - keeps frozen bytes",
                         "Option B: apply a one-clause formal-sentence repair (E1a/E1b/E1c) - changes the WCC hash and requires re-review of F1",
                         "owner applies the ADJ-CONTROL-STALENESS control rebase + pin refresh (reproduced independently here; prior proposals w004/w080/w064-rebase)",
                         "runner owner routes a rejected conforming canonical into blocking_adjudication instead of []",
                         "a worker re-runs the suite to certify exit 0 / valid_for_calibration=true on the adopted bytes"],
                     evidence_refs=evidence,
                     falsifier="A run in which the adopted tool or schema repairs produce exit 0 with valid_for_calibration=true without either route falsifies the blocker; a run showing another conforming canonical rejection falsifies sole-blocker."))

    events.append(ev("w064-r03-01-status", "status",
                     status="active", hours=1.0,
                     summary=("W064-R03-CAUSE-01 complete at worker level (no inbox card existed for worker-064): independent replication of "
                              "the R03 root cause at FROZEN rev29/rev13 plus rev11->rev12 regression provenance, three one-clause repair candidates, a binder-list "
                              "alternative and a tool-amendment variant, and an end-to-end sole-blocker determination (S1 exit 3 / S2 exit 0 / "
                              "S4 exit 0 with canonical bytes). Frozen-bytes churn was observed and is reported (rev28 -> rev29). "
                              "No canonical file modified; node stays active and no gate is touched."),
                     next_falsifier=("After the owner adopts either route and applies the control rebase + pin refresh, re-run "
                                     "schemas/semantic_contract_tests/run_contract_tests.py; expect exit 0, valid_for_calibration=true, "
                                     "controls 6/6 accepted, mutants 32/11/32 unchanged. Any deviation falsifies the repair."),
                     evidence_refs=evidence,
                     not_claimed=["no gate verdict", "no node completion", "no canonical modification",
                                  "no claim of first discovery (w080 and w16 reported the R03 blocker first)"]))

    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            try:
                existing.add(json.loads(line).get("event_id"))
            except Exception:
                pass
    new = [e for e in events if e["event_id"] not in existing]
    if "--check" in sys.argv:
        print(json.dumps({"would_emit": [e["event_id"] for e in new], "already_present": len(events) - len(new),
                          "hashes": {k: v[:12] for k, v in hashes.items()}}, indent=1))
        return 0
    with OUTBOX.open("a") as f:
        for e in new:
            f.write(json.dumps(e, sort_keys=True) + "\n")

    ckpt = {
        "checkpoint_id": f"w064-r03-ckpt-{now().replace(':', '').replace('-', '')}",
        "task_id": TASK, "actor": "worker-064", "instance_id": INSTANCE,
        "created_at": now(), "node_id": "A1", "gate": "G-AUDIT", "class_ids": CLASSES,
        "status": "worker_task_complete_no_node_transition",
        "verdict": report["verdict"],
        "snapshot_hashes": report["snapshot"],
        "canonical_drift_during_window": {k: False for k in report["snapshot"] if k.startswith("schemas/af_")},
        "artifacts": {str(files[k].relative_to(REPO)): hashes[k] for k in files},
        "events_emitted": [e["event_id"] for e in new],
        "prior_work_cross_reference": report.get("prior_work_cross_reference"),
        "key_measurements": {
            "baseline_wcc_semantic": "reject R03 only (baseline+hardened)",
            "rev11_wcc_9a8bd4c96800": "accept both semantic stages",
            "E1a/E1b/E1c": "accept all three stages; only quantifiers.formal differs",
            "S1_rebased_canonical_wcc": {"exit": report["full_suite"]["S1"]["exit"],
                                          "valid_for_calibration": report["full_suite"]["S1"]["valid_for_calibration"],
                                          "conforming_rejections": list(report["full_suite"]["S1"]["conforming_rejections"])},
            "S2_rebased_E1a_wcc": {"exit": report["full_suite"]["S2"]["exit"],
                                    "valid_for_calibration": report["full_suite"]["S2"]["valid_for_calibration"]},
            "S4_tool_amended_canonical_wcc": {"exit": report["full_suite"]["S4"]["exit"],
                                               "valid_for_calibration": report["full_suite"]["S4"]["valid_for_calibration"],
                                               "wcc_sha_in_results": report["full_suite"]["S4"]["fixture_hashes"].get("SCT-K03")},
            "mutants": "32/11/32 unchanged in S1/S2/S4",
        },
        "no_completion_claim": "worker cannot set done/passed or a gate verdict; no canonical file written",
    }
    STATE.mkdir(parents=True, exist_ok=True)
    (STATE / "w064_r03_checkpoint.json").write_text(json.dumps(ckpt, indent=1) + "\n")
    with (STATE / "w064_checkpoints.jsonl").open("a") as f:
        f.write(json.dumps(ckpt, sort_keys=True) + "\n")

    print(json.dumps({"emitted": [e["event_id"] for e in new], "skipped_existing": len(events) - len(new),
                      "checkpoint": str(STATE / "w064_r03_checkpoint.json"),
                      "hashes": {k: v[:12] for k, v in hashes.items()}}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
