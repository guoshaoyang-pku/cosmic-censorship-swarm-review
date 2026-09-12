#!/usr/bin/env python3
"""Emit the W011-GFORM-COVERAGE-RECONCILE-01 result: SHA256SUMS, outbox events, checkpoint.

Append-only and idempotent by event_id. Writes only:
  artifacts/worker-011/gform_coverage_reconcile/SHA256SUMS
  comms/outbox/worker-011.jsonl
  runtime/state/w011_checkpoint_6.json
  runtime/state/w011_checkpoints.jsonl
"""
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUTBOX = ROOT / "comms" / "outbox" / "worker-011.jsonl"
STATE = ROOT / "runtime" / "state"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST)
STAMP = NOW.strftime("%Y%m%dT%H%M%S")
PINS = {
    "F1": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "F2a": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "F2b": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
}
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


def main() -> int:
    arts = {
        "preregistration.json": HERE / "preregistration.json",
        "reconcile_coverage.py": HERE / "reconcile_coverage.py",
        "report.json": HERE / "report.json",
        "README.md": HERE / "README.md",
    }
    hashes = {rel(p): sha(p) for p in arts.values()}
    (HERE / "SHA256SUMS").write_text(
        "".join(f"{h}  {n}\n" for n, h in sorted(hashes.items())))
    rep = json.loads((HERE / "report.json").read_text())

    def ev(eid, etype, **kw):
        e = {"event_id": eid, "event_type": etype, "created_at": NOW.isoformat(),
             "actor": "worker-011", "task_id": "W011-GFORM-COVERAGE-RECONCILE-01",
             "node_id": "F1,F2a,F2b", "class_ids": CLASS_IDS, "gate": "G-FORM",
             "run_id": "w011-gform-coverage-reconcile-01"}
        e.update(kw)
        return e

    H = {k: v for k, v in hashes.items()}
    evs = [
        ev("w011-cr-20260912-art-prereg", "artifact", artifact_type="preregistration",
           path=rel(arts["preregistration.json"]), sha256=H[rel(arts["preregistration.json"])],
           validation_status="unverified",
           summary="CF-31 reconciliation pre-registration: pins, R/S method definitions, factors V1-V6, controls K1-K10, decision rule, falsifier; written before the measurement run."),
        ev("w011-cr-20260912-art-instrument", "artifact", artifact_type="instrument",
           path=rel(arts["reconcile_coverage.py"]), sha256=H[rel(arts["reconcile_coverage.py"])],
           validation_status="unverified",
           summary="Independent stdlib-only reimplementation of R (astra_lifecycle.review_coverage) and S (lead census), epoch-correct count reconstruction, X1-X8 exclusion probe, K1-K10 controls, double-run determinism; no import of astra_lifecycle."),
        ev("w011-cr-20260912-art-report", "artifact", artifact_type="measurement_report",
           path=rel(arts["report.json"]), sha256=H[rel(arts["report.json"])],
           validation_status="unverified",
           evidence_refs=[f"{rel(arts['report.json'])}#{H[rel(arts['report.json'])][:12]}"],
           summary="Verdict UNRECONCILED_CENSUS_CLAUSE: scan reproduced at its 01:16:26 epoch; S at its stated 01:10 instant yields F2b [worker-090], not 0; no documented exclusion reduces R's F2b accepts to 0; 12-row CV-02 pin-bound/target-unresolved census; controls 10/10; deterministic."),
        ev("w011-cr-20260912-art-readme", "artifact", artifact_type="documentation",
           path=rel(arts["README.md"]), sha256=H[rel(arts["README.md"])],
           validation_status="unverified",
           summary="Findings F-011-CR-01..06, measured tables, caveats, falsifier, reproduction, non-claims."),
        ev("w011-cr-20260912-review-coverage-method", "review",
           target_id="G-FORM-review-coverage-method", reviewer="worker-011",
           verdict="revise", score=3.0,
           counts_as_full_schema_verdict=False, counts_as_independent_verdict=False,
           hard_failures=["F-011-CR-03"],
           findings=[
               "F-011-CR-01 (accept-quality): the controller scan R reproduces exactly at the 01:16:26 epoch on all three pins; controls 10/10; double run byte-identical.",
               "F-011-CR-02 (revise): F1 has a genuine rule divergence at one instant (R=4 vs S=6): worker-011's scoped accept (flag=false, 'NOT a full-schema verdict') and worker-089's path-target accept (CV-02) are counted by S and excluded by R.",
               "F-011-CR-03 (blocking-for-census): the published F2b '0 accepts / 7 revise' is not reproducible by the stated census method at its stated instant: S(01:10:00) = [worker-090] (mtime 01:08:56, full pin, flag=true). No single documented exclusion (X1-X6, X8) yields 0; reaching 0 needs an independence-cluster rule that no frozen artifact defines (X7 not measurable).",
               "F-011-CR-04 (advisory): the accepted-event channel is a superset (F2b [052,061,071,072,090,16]) containing scoped, superseded and cross-target records; event counts need supersession/scope/target discipline.",
               "F-011-CR-05 (info): V3 flag-strict is the only live factor (F1 drops 052/085, F2b drops 052); V4/V5/V6 are inert on the live R-admitted set.",
               "F-011-CR-06 (advisory): 12 pin-bound review files have targets R cannot resolve (CV-02), including two accepts (worker-089/F1, worker-018/F2a).",
           ],
           falsifier="Re-run reconcile_coverage.py at the five frozen pins: any failure of the epoch scan reproduction, any control K1-K10 not firing, S(01:10:00).F2b == [], a frozen independence-cluster rule reducing the R-admitted F2b accepts to 0, or non-identical double-run output falsifies this measurement.",
           evidence_refs=[f"{rel(arts['report.json'])}#{H[rel(arts['report.json'])][:12]}",
                          f"{rel(arts['preregistration.json'])}#{H[rel(arts['preregistration.json'])][:12]}"],
           note="Measurement of counting methods only; not a schema verdict, not a gate verdict, not a node status."),
        ev("w011-cr-20260912-claim-reconcile", "claim",
           class_id="AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
           conclusion_type="verification_result", claims_theorem_status=False,
           statement=("At frozen pins F1 d9cebb9404b2 / F2a e9a27996dfd3 / F2b b2ab6acb2bbe under FROZEN rev29 815e08079aef, "
                      "the controller review scan reproduces exactly at its 01:16:26 epoch (F1 [052,072,075,085], F2a [017,072], F2b [052,071,090]); "
                      "applying the formulation lead's stated pin-only census method at its stated instant 01:10:00 yields F2b [worker-090], not the published [], "
                      "and no single documented exclusion rule reduces the scan's F2b accepts to 0, so the published F2b=0 requires either an instant before 01:08:56 "
                      "(contradicting the stated 're-read at 01:10') or an unstated non-independence exclusion that no frozen artifact defines. "
                      "F1's published difference (scan 4 vs census 5) is a genuine rule divergence: scope-flag semantics (worker-011, flag=false) plus CV-02 path-target invisibility (worker-089). "
                      "12 pin-bound review files are invisible to the scan's node-id target resolution, including two accepts."),
           assumptions=["reviews/*.json bytes and mtimes are the measurement substrate; no review byte changed during the run",
                        "the controller scan and the lead census method definitions are taken from their published sources, not re-interpreted",
                        "the epoch reconstruction (mtime <= publication instant) is valid unless a file was rewritten in place with an older mtime before the run",
                        "counting-method measurement only; no schema content is assessed"],
           falsifier="Re-run artifacts/worker-011/gform_coverage_reconcile/reconcile_coverage.py at the five frozen pins; falsified by any failed epoch scan reproduction, any control not firing, S(01:10:00).F2b == [], a frozen independence-cluster definition that reduces the R-admitted F2b accepts to 0, or a non-identical double run.",
           evidence_refs=[f"{rel(arts['report.json'])}#{H[rel(arts['report.json'])][:12]}",
                          f"{rel(arts['reconcile_coverage.py'])}#{H[rel(arts['reconcile_coverage.py'])][:12]}"],
           artifact_refs=[f"{rel(arts['report.json'])}#{H[rel(arts['report.json'])][:12]}"],
           note="Worker measurement; validation_status remains lead/audit authority."),
        ev("w011-cr-20260912-blocker-census", "blocker",
           description=("CF-31 F2b clause is not a scan defect: the published census count 'F2b 0 accepts / 7 revise' at b2ab6acb2bbe is not reproducible "
                        "from the census's own stated method at its stated instant (S(01:10:00) = [worker-090], file mtime 01:08:56, full 64-hex pin, flag=true). "
                        "Reducing the R-admitted accepts [052,071,090] to 0 requires an author/independence-cluster rule that no frozen artifact defines."),
           needed_to_unblock=("Audit lead (astra-life05-verify-gform-r3 / A1 adjudication) to rule the binding coverage rule: (1) does a scoped accept "
                              "(flag=false or text-disclaimed) count? (2) does a path-target accept count (CV-02)? (3) what is the machine-readable "
                              "independence-cluster definition? Until (3) exists, no coverage count at b2ab6acb2bbe is reproducible to 0."),
           evidence_refs=[f"{rel(arts['report.json'])}#{H[rel(arts['report.json'])][:12]}",
                          "reviews/F2b-rev13-full-090.json#345f74bb73f4",
                          "reviews/F2b-review-rev13-worker-071.json#e5a313894f7c",
                          "reviews/F2b-review-rev13-052.json#c3f720292e47",
                          "reviews/F1-review-worker-089.json"],
           falsifier="A frozen independence-cluster definition under which the R-admitted F2b accepts reduce to 0, or a census method statement whose instant precedes 01:08:56."),
        ev(f"w011-cr-{STAMP}-status-complete", "status", status="active",
           claims_completion=True, completion_scope="worker task only; no node done, no validation_status, no gate verdict",
           hours=0.6,
           summary=("W011-GFORM-COVERAGE-RECONCILE-01 complete at worker level, one bounded class-bound task. Verdict UNRECONCILED_CENSUS_CLAUSE: "
                    "scan reproduced at its epoch (true), controls 10/10, deterministic; the lead's F2b=0 census clause is not reproducible by its documented "
                    "method/instant and needs an independence-cluster rule that no frozen artifact defines. H1 (F2b not temporal alone) SUPPORTED; H2 (F1 rule "
                    "divergence) SUPPORTED. No canonical/frozen/review byte written. Checkpoint runtime/state/w011_checkpoint_6.json follows."),
           evidence_refs=[f"{rel(arts['report.json'])}#{H[rel(arts['report.json'])][:12]}",
                          f"{rel(arts['README.md'])}#{H[rel(arts['README.md'])][:12]}",
                          "runtime/state/w011_checkpoint_6.json"],
           next_falsifier=("Re-run reconcile_coverage.py at the five frozen pins; or the audit lead publishes a machine-readable independence rule and coverage "
                           "is recomputed: the census clause flips to reproducible only if that rule reduces the R-admitted F2b accepts to 0, or if the census "
                           "instant is shown to precede 01:08:56."),
           gate_effect="none"),
        ev(f"w011-cr-{STAMP}-checkpoint-6", "status", status="active", checkpoint=6,
           summary="checkpoint 6: artifacts+hashes written, events emitted, exit planned; task-completion claim only.",
           evidence_refs=[f"{rel(arts['report.json'])}#{H[rel(arts['report.json'])][:12]}",
                          "runtime/state/w011_checkpoint_6.json"]),
    ]

    # Replace (not duplicate) this task's previously written events; append-only for all others.
    # Safe only because the previous write of this task's ids has not been ingested
    # (verified: 0 hits in research_map/events.jsonl and comms/rejected.jsonl). Once ingested,
    # protocol requires a new artifact event with the new sha256 instead of an in-place rewrite.
    kept = []
    if OUTBOX.is_file():
        for line in OUTBOX.read_text().splitlines():
            try:
                e = json.loads(line)
                if str(e.get("event_id", "")).startswith("w011-cr-"):
                    continue
            except Exception:
                pass
            kept.append(line)
    added = 0
    with OUTBOX.open("w") as fh:
        for line in kept:
            fh.write(line + "\n")
        for e in evs:
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
            added += 1

    ck = {
        "worker": "worker-011", "checkpoint": 6, "at": NOW.isoformat(),
        "task_id": "W011-GFORM-COVERAGE-RECONCILE-01",
        "node_id": "F1,F2a,F2b", "class_ids": CLASS_IDS, "gate": "G-FORM",
        "verdict": rep["verdict"], "status": "task_complete_no_gate_verdict",
        "target_pins": PINS,
        "frozen_pin": "artifacts/formulation/FROZEN.json#815e08079aef",
        "scan_reproduced_at_epoch": rep["scan_reproduced_at_epoch"],
        "f2b_S_at_011000": rep["summary"]["S_lead_census_at_011000"]["F2b"],
        "f2b_R_at_scan_epoch": rep["summary"]["R_controller_scan_at_011626"]["F2b"],
        "controls_pass": rep["controls_pass"],
        "determinism": rep["determinism"],
        "artifacts": hashes,
        "events_added": added,
        "falsifier": ("Re-run reconcile_coverage.py at the five frozen pins: epoch scan reproduction failure, a control not firing, "
                      "S(01:10:00).F2b == [], a frozen independence rule reducing F2b accepts to 0, or non-identical double run falsifies."),
        "next_falsifier": ("Audit-lead ruling on the binding coverage rule (scope flag, CV-02 path targets, independence cluster); then recompute at the same pins."),
    }
    STATE.mkdir(parents=True, exist_ok=True)
    (STATE / "w011_checkpoint_6.json").write_text(json.dumps(ck, ensure_ascii=False, indent=1) + "\n")
    ckline = {"checkpoint": 6, "at": NOW.isoformat(), "worker": "worker-011",
              "task": "W011-GFORM-COVERAGE-RECONCILE-01", "node_id": "F1,F2a,F2b",
              "gate": "G-FORM", "verdict": rep["verdict"],
              "report_sha256": H[rel(arts["report.json"])],
              "scan_reproduced_at_epoch": rep["scan_reproduced_at_epoch"],
              "controls_pass": rep["controls_pass"]}
    ckpath = STATE / "w011_checkpoints.jsonl"
    old = []
    if ckpath.is_file():
        for line in ckpath.read_text().splitlines():
            try:
                d = json.loads(line)
                if d.get("checkpoint") == 6 and d.get("worker") == "worker-011" and \
                        d.get("task") == "W011-GFORM-COVERAGE-RECONCILE-01":
                    continue
            except Exception:
                pass
            old.append(line)
    with ckpath.open("w") as fh:
        for line in old:
            fh.write(line + "\n")
        fh.write(json.dumps(ckline, ensure_ascii=False) + "\n")

    print(json.dumps({"events_added": added, "event_ids": [e["event_id"] for e in evs],
                      "sha256sums": hashes, "checkpoint": str(STATE / "w011_checkpoint_6.json")},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
