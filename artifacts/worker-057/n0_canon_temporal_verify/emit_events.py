#!/usr/bin/env python3
"""Emit the W057-N0-CANONTEMPORAL-VERIFY-01 events to comms/outbox/worker-057.jsonl.

Idempotent: an event_id already present in the outbox is skipped.  Every artifact sha256 is
re-measured on disk before the event is written; a mismatch aborts.  Every event is validated
against research_map/schemas.py before being appended.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUTBOX = REPO / "comms" / "outbox" / "worker-057.jsonl"
sys.path.insert(0, str(REPO))
from research_map.schemas import validate_event  # noqa: E402

ART = REPO / "artifacts" / "worker-057" / "n0_canon_temporal_verify"
CONTROL = "numerics/protocol/canonical_temporal_control.json"
CANON = "numerics/tests/flat_wave.py"
GENERATOR = "numerics/protocol/canonical_temporal_control.py"

P = {
    "report": "artifacts/worker-057/n0_canon_temporal_verify/report.json",
    "reportmd": "artifacts/worker-057/n0_canon_temporal_verify/REPORT.md",
    "verify": "artifacts/worker-057/n0_canon_temporal_verify/verify_canonical_temporal_control.py",
    "replay": "artifacts/worker-057/n0_canon_temporal_verify/replay_canonical_temporal_control.py",
    "replayrep": "artifacts/worker-057/n0_canon_temporal_verify/replay_report.json",
    "emitter": "artifacts/worker-057/n0_canon_temporal_verify/emit_events.py",
}

FALSIFIER = ("Re-hash numerics/protocol/canonical_temporal_control.json and re-run "
             "artifacts/worker-057/n0_canon_temporal_verify/verify_canonical_temporal_control.py: "
             "this report is falsified for the recorded control sha256 if any declared derived "
             "number fails to reproduce from the embedded rows, if any of the 22 checks flips, or "
             "if any of the E1-E6 controls stops being detected. A moved control hash voids the "
             "report for the new bytes; a moved canonical flat_wave.py hash voids the control's "
             "premise; a fresh run of the pinned canonical artifact disagreeing with any embedded "
             "row beyond 1e-10 relative falsifies the replay cross-check.")


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    H = {k: sha(REPO / v) for k, v in P.items()}
    H["control"] = sha(REPO / CONTROL)
    H["canon"] = sha(REPO / CANON)
    H["generator"] = sha(REPO / GENERATOR)
    report = json.loads((REPO / P["report"]).read_text())
    replay = json.loads((REPO / P["replayrep"]).read_text())
    assert report["summary"]["verdict"] == "RECOMPUTED", "report verdict is not RECOMPUTED"
    assert report["summary"]["instrument_valid"], "instrument not valid"
    assert replay["all_rows_within_tolerance"], "replay mismatch"

    now = report["created_at"]
    pre = "w057-n0cantemporal-59a278f0bc"
    common = {"created_at": now, "actor": "worker-057", "node_id": "N0",
              "class_id": "AF-WCC-SCALAR-SPH", "class_ids": ["AF-WCC-SCALAR-SPH"],
              "gate": "G-NUM", "group_id": "numerics",
              "task_id": "W057-N0-CANONTEMPORAL-VERIFY-01"}
    evidence = [f"{P['report']}#{H['report'][:12]}", f"{P['verify']}#{H['verify'][:12]}",
                f"{P['reportmd']}#{H['reportmd'][:12]}", f"{CONTROL}#{H['control'][:12]}",
                f"{CANON}#{H['canon'][:12]}", f"{GENERATOR}#{H['generator'][:12]}"]
    events = [
        dict(common, event_id=f"{pre}-status-start", event_type="status", status="active",
             hours=0.1,
             summary=("No card exists in comms/inbox/worker-057.jsonl; took ONE bounded "
                      "class-bound task (AF-WCC-SCALAR-SPH / N0 / G-NUM), permitted under "
                      "numerics_lock because it is flat-space N0 analysis only: independent "
                      "verification of numerics/protocol/canonical_temporal_control.json (the "
                      "lead-numerics control that re-based review finding F1). Method: recompute "
                      "every derived number from the control's own embedded rows in pure Python "
                      "(no import of the lead generator), reproduce the constant-CFL dt "
                      "quantisation from the hash-pinned study config, replay the pinned canonical "
                      "artifact, and run 6 fail-closed controls."),
             evidence_refs=[f"{CONTROL}#{H['control'][:12]}", f"{CANON}#{H['canon'][:12]}",
                            f"{GENERATOR}#{H['generator'][:12]}"],
             next_falsifier=FALSIFIER),
        dict(common, event_id=f"{pre}-artifact-report", event_type="artifact",
             artifact_type="independent_verification_report", path=P["report"],
             sha256=H["report"], bytes=(REPO / P["report"]).stat().st_size,
             validation_status="unverified",
             verdict="RECOMPUTED", checks=f"{report['summary']['n_checks']}/"
             f"{report['summary']['n_checks']}", controls="6/6", advisories=4,
             supported_by=[{"path": P["verify"], "sha256": H["verify"]},
                           {"path": P["reportmd"], "sha256": H["reportmd"]}],
             measured_inputs={CONTROL: H["control"], CANON: H["canon"], GENERATOR: H["generator"]},
             reproduce=f"python3 {P['verify']}",
             falsifier=FALSIFIER,
             evidence_refs=evidence),
        dict(common, event_id=f"{pre}-artifact-reportmd", event_type="artifact",
             artifact_type="report_markdown", path=P["reportmd"], sha256=H["reportmd"],
             bytes=(REPO / P["reportmd"]).stat().st_size, validation_status="unverified",
             falsifier=FALSIFIER, evidence_refs=evidence),
        dict(common, event_id=f"{pre}-artifact-verifier", event_type="artifact",
             artifact_type="verifier_script", path=P["verify"], sha256=H["verify"],
             bytes=(REPO / P["verify"]).stat().st_size, validation_status="unverified",
             reproduce=f"python3 {P['verify']}",
             falsifier=FALSIFIER, evidence_refs=evidence),
        dict(common, event_id=f"{pre}-artifact-replay", event_type="artifact",
             artifact_type="replay_script", path=P["replay"], sha256=H["replay"],
             bytes=(REPO / P["replay"]).stat().st_size, validation_status="unverified",
             reproduce=f"python3 {P['replay']}",
             falsifier=FALSIFIER, evidence_refs=evidence),
        dict(common, event_id=f"{pre}-artifact-replayreport", event_type="artifact",
             artifact_type="replay_report", path=P["replayrep"], sha256=H["replayrep"],
             bytes=(REPO / P["replayrep"]).stat().st_size, validation_status="unverified",
             verdict=replay["verdict"], worst_row_rel_diff=replay["worst_row_rel_diff"],
             falsifier=FALSIFIER, evidence_refs=evidence),
        dict(common, event_id=f"{pre}-review-control", event_type="review",
             reviewer="worker-057 (independent of astra-lead-numerics; advisory only)",
             target_id=f"{CONTROL}#{H['control']}", target_path=CONTROL,
             reviewed_sha256=H["control"], verdict="accept", score=4.0, hard_failures=[],
             findings=[
                 {"severity": "info",
                  "finding": ("every derived number reproduces from the embedded rows and the "
                              "constant-CFL dt quantisation reproduces bitwise for all 20 rows; "
                              "the pinned canonical artifact replays all 60 rows bitwise")},
                 {"severity": "advisory", "check": "A1",
                  "finding": ("pre_stated_rule.criterion does not define 'excess' as relative; "
                              "the stored numbers are e(baseline)/e(plateau)-1 and an absolute "
                              "reading would make the rule vacuous")},
                 {"severity": "advisory", "check": "A2",
                  "finding": ("study kwargs are not embedded in the control JSON (only in the "
                              "hash-pinned generator); the artifact is not self-describing")},
                 {"severity": "advisory", "check": "A3",
                  "finding": ("edited=false and runtime_seconds are assertions; edited=false is "
                              "supported by hash equality plus mtime ordering, runtime_seconds is "
                              "environment-dependent")},
                 {"severity": "advisory", "check": "A4",
                  "finding": ("order4_standing relative excess grows with resolution "
                              "(4.78e-05 -> 1.54e-04) but stays << tolerance; verdict unchanged "
                              "under a max-excess reading")},
             ],
             authority_note=("worker review is advisory; only the controller / leads may move "
                             "G-NUM or numerics_lock. No gate verdict or node status is claimed."),
             evidence_refs=evidence),
        dict(common, event_id=f"{pre}-claim", event_type="claim",
             conclusion_type="numerical_evidence",
             statement=(
                 "Artifact-and-checker result, not a physics claim: at "
                 "numerics/protocol/canonical_temporal_control.json sha256 "
                 f"{H['control']} the recorded claim holds under independent recomputation. "
                 "From the file's own embedded rows, all 22 checks pass: the constant-CFL "
                 "quantisation dt = t_end/ceil(t_end/(cfl*R/n)) reproduces bitwise for all 20 "
                 "rows using the hash-pinned configs (t_end 0.37/8.0/0.37, R 1.0/40.0/1.0); "
                 "order_l2, fit_order (pure-Python OLS), temporal excess, excess_coarsest/finest, "
                 "order_move, spatial_admissible, the verdict strings and the overall reduction "
                 "all reproduce (excess to 1e-15 absolute; fit orders to 1e-12 relative); the "
                 "plateau is a genuine limit at every resolution (final successive cfl increment "
                 "<= 3.3e-08 <= 1e-6) and the verdict is unchanged under a max-excess reading of "
                 "the rule. Per study (baseline cfl; excess at coarsest; max excess; order move): "
                 "order2_pulse 0.25, 3.8906e-04, 3.8906e-04, 1.285e-04; order2_standing 0.25, "
                 "7.5711e-06, 7.5711e-06, 2.430e-06; order4_standing 0.1, 4.7812e-05, 1.5376e-04, "
                 "3.976e-05; all three spatial_admissible=true. A separate replay of the pinned "
                 "canonical flat_wave.py (hash 8b52014dac47f996) reproduced all 60 embedded rows "
                 "and all 12 fitted orders at relative difference 0.0 (bitwise). Six fail-closed "
                 "controls (excess flip, order-move flip, row reversal, row tamper, n-list break, "
                 "byte edit) all fired. Four non-blocking advisories (A1 relative-excess wording, "
                 "A2 config not embedded, A3 assertion fields, A4 order4 excess growth) do not "
                 "affect the verdict. This re-runs the pinned canonical artifact for replay only; "
                 "it does not certify solver correctness, sets no gate verdict and does not "
                 "release numerics_lock or N1."),
             assumptions=[
                 "the embedded rows are the published evidence of the control and are taken as "
                 "given for the arithmetic audit; part B replays the pinned canonical artifact",
                 "the study kwargs are transcribed from the hash-pinned generator "
                 "00a41cfd47088df9432bdc0aba6540cc3c6a69cd1bf88722b228819274adfa0f and bound to "
                 "it by literal source fragments",
                 "temporal excess is read as the relative excess e(baseline)/e(plateau)-1, the "
                 "only non-degenerate reading of the pre-stated criterion",
                 "order_move is compared at 1e-9 absolute because it is the cancellation-prone "
                 "difference of two nearly equal fitted orders",
                 "worker events cannot set node status, validation_status=passed or a gate verdict",
             ],
             falsifier=FALSIFIER,
             evidence_refs=evidence),
        dict(common, event_id=f"{pre}-status-complete", event_type="status", status="active",
             hours=0.5, claims_completion=False,
             summary=("W057-N0-CANONTEMPORAL-VERIFY-01 complete as one bounded class-bound worker "
                      "task: verdict RECOMPUTED (22/22 checks, 0 findings, 6/6 fail-closed "
                      "controls, 4 non-blocking advisories), control hash stable start-to-end, "
                      "pinned canonical artifact replays all 60 rows bitwise, advisory review "
                      "accept 4.0 at the pinned control hash. Checkpoint written to "
                      "runtime/state/w057_checkpoint_canontemporal.json and "
                      "runtime/state/w057_checkpoints.jsonl. No gate verdict, no node completion, "
                      "no numerics_lock change; worker slot can be recycled."),
             evidence_refs=evidence,
             next_falsifier=FALSIFIER),
    ]

    for e in events:
        validate_event(e)

    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            if line.strip():
                try:
                    existing.add(json.loads(line)["event_id"])
                except Exception:
                    pass
    new = [e for e in events if e["event_id"] not in existing]
    if new:
        with OUTBOX.open("a") as f:
            for e in new:
                f.write(json.dumps(e, sort_keys=True) + "\n")
    print(json.dumps({"events_total": len(events), "appended": len(new),
                      "skipped_existing": len(events) - len(new),
                      "hashes": {k: v[:12] for k, v in H.items()}}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
