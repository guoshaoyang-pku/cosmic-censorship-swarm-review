#!/usr/bin/env python3
"""Emit the W012-GNUM-ERRFIELD-VERIFY-01 checkpoint and outbox events.

Idempotent: re-running appends only event_ids not already present in the outbox.
Writes: runtime/state/worker-012_gnum_errfield_verify_checkpoint.json and
comms/outbox/worker-012.jsonl (own files only).
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.dont_write_bytecode = True

TASK = "W012-GNUM-ERRFIELD-VERIFY-01"
CLASS_ID = "AF-WCC-SCALAR-SPH"
NODE, GATE = "N0", "G-NUM"
OUTBOX = REPO / "comms/outbox/worker-012.jsonl"
CHECKPOINT = REPO / "runtime/state/worker-012_gnum_errfield_verify_checkpoint.json"

DELIVERABLES = [
    "artifacts/worker-012/gnum_errfield_verify/PRE_REGISTRATION.md",
    "artifacts/worker-012/gnum_errfield_verify/verify_errfield.py",
    "artifacts/worker-012/gnum_errfield_verify/report.json",
    "artifacts/worker-012/gnum_errfield_verify/README.md",
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    eid_base = "w012-errfield-" + time.strftime("%Y%m%dT%H%M%S%z")
    report = json.loads((HERE / "report.json").read_text())
    hashes = {rel: sha(REPO / rel) for rel in DELIVERABLES}
    hashes["artifacts/worker-012/gnum_errfield_verify/emit_events.py"] = sha(HERE / "emit_events.py")

    # lock guard, read-only, recomputed here (no canonical writes)
    sys.path.insert(0, str(REPO))
    import numerics.gates as G  # noqa: E402
    guard = G.evaluate(REPO)
    lock_guard = {
        "verdict": guard["verdict"],
        "production_allowed": bool(guard["production_allowed"]),
        "lock_state": guard["lock"]["state"],
        "spherical_solver_dir_exists": (REPO / "numerics/spherical_solver").exists(),
        "protocol_review_contest": bool(guard["protocol_review"]["contest"]),
        "blocking_reason_count": len(guard["blocking_reasons"]),
    }

    preds = {k: bool(v["pass"]) for k, v in report["predictions"].items()}
    cert = {f"dr={c['dr']}": {"corr_cnfd_cnfem": c["pairwise"]["cnfd_vs_cnfem"]["corr"],
                              "sign_mass_cnfd_cnfem":
                                  c["pairwise"]["cnfd_vs_cnfem"]["sign_agreement_mass_fraction"],
                              "corr_lffd_cnfd": c["pairwise"]["lffd_vs_cnfd"]["corr"],
                              "spread_relative": c["spread_relative"]}
            for c in report["certified_regime_cases"]}

    checkpoint = {
        "schema": "worker-checkpoint/v1",
        "checkpoint_id": eid_base + "-checkpoint",
        "task_id": TASK,
        "agent": "worker-012",
        "created_at": stamp,
        "class_id": CLASS_ID,
        "node_id": NODE,
        "gate": GATE,
        "status": "done",
        "not_a_gate_verdict": True,
        "authority_note": ("Worker task checkpoint; it cannot set node status, validation_status or "
                           "a gate verdict. N0 stays active and G-NUM pending."),
        "verdict": report["verdict"],
        "headline": report["headline"],
        "predictions": preds,
        "certified_regime_extension": cert,
        "declared_regime_reproduction": {
            "l2_max_rel": 0.0,
            "corr_max_abs": max(v["corr_abs"] for c in report["predictions"]["P1_reproduction"]["detail"]["cases"]
                                for v in c["pairwise"].values()),
            "reading_match_all": all(c["reading_match"] for c in
                                     report["predictions"]["P1_reproduction"]["detail"]["cases"]),
        },
        "mechanism_symbol_slopes": {"fd": report["predictions"]["P3_mechanism_symbol_slopes"]["detail"]["fd_slope"],
                                    "fem": report["predictions"]["P3_mechanism_symbol_slopes"]["detail"]["fem_slope"]},
        "negative_control": report["predictions"]["P5_negative_control_planted_shared_field"]["detail"],
        "determinism": report["predictions"]["P6_determinism_bitwise"]["detail"],
        "cross_check_certification_rows": {
            "rows_matched_exactly": "9/12 (dr=0.2,0.1,0.05 x lffd/cnfd/cnfem)",
            "max_rel_deviation": 0.0,
            "unverified_rung": "dr=0.025",
        },
        "script_revision": report["script_revision"],
        "reviewed_hashes": report["reviewed_hashes"],
        "deliverables": hashes,
        "pins_stable": bool(report["pins_stable"]),
        "lock_guard": lock_guard,
        "falsifier": report["falsifier"],
        "next_falsifier": report["next_falsifier"],
        "hours": 0.4,
        "stop_rule": ("1 agent-hour; one bounded class-bound task, one report at pinned hashes, "
                      "one review/claim event set, one checkpoint, then exit."),
        "outbox": "comms/outbox/worker-012.jsonl",
        "open_items": [
            "OI-1 (controller/numerics): the certified-regime extension is not bound to any review tally; it is supporting evidence for the C8/independence reading.",
            "OI-2 (self): dr=0.025 and a second pulse family are not recomputed; named as the next falsifier.",
        ],
        "emitted_event_ids": [],
    }
    # fill the planned event ids before hashing so the checkpoint hash is the emitted one
    checkpoint["emitted_event_ids"] = [eid_base + "-" + s for s in (
        "status-start", "artifact-prereg", "artifact-instrument", "artifact-report",
        "artifact-readme", "artifact-checkpoint", "claim-errfield", "review-errfield",
        "status-complete")]
    CHECKPOINT.write_text(json.dumps(checkpoint, indent=2, sort_keys=True) + "\n")
    cp_sha = sha(CHECKPOINT)

    def ev(eid_suffix, typ, **kw):
        return {"event_id": eid_base + "-" + eid_suffix, "event_type": typ,
                "created_at": stamp, "actor": "worker-012", "task_id": TASK,
                "class_id": CLASS_ID, "node_id": NODE, "gate": GATE, **kw}

    events = [
        ev("status-start", "status", status="active", hours=0.05,
           summary=("Took ONE bounded class-bound task W012-GNUM-ERRFIELD-VERIFY-01: independent "
                    "read-only recomputation of the N0 scheme error-field orthogonality check "
                    "(target " + report["target_artifact"] + ") and its extension to the certified "
                    "fixed dt=1e-4 regime. Pre-registered before measurement; no inbox card existed."),
           evidence_refs=[report["target_artifact"],
                          "numerics/protocol/n0_fixed_dt_certification.json#1677822ceb9c",
                          "artifacts/worker-012/gnum_errfield_verify/PRE_REGISTRATION.md#" + hashes[DELIVERABLES[0]][:12]],
           next_falsifier=("Pin drift, a failed reproduction of the declared dt=1e-3 values, a lost "
                           "sign separation at dt=1e-4, or a non-detected planted shared field.")),
        ev("artifact-prereg", "artifact", artifact_type="prereg",
           path=DELIVERABLES[0], sha256=hashes[DELIVERABLES[0]], validation_status="unverified"),
        ev("artifact-instrument", "artifact", artifact_type="instrument",
           path=DELIVERABLES[1], sha256=hashes[DELIVERABLES[1]], validation_status="unverified"),
        ev("artifact-report", "artifact", artifact_type="report",
           path=DELIVERABLES[2], sha256=hashes[DELIVERABLES[2]], validation_status="unverified"),
        ev("artifact-readme", "artifact", artifact_type="readme",
           path=DELIVERABLES[3], sha256=hashes[DELIVERABLES[3]], validation_status="unverified"),
        ev("artifact-checkpoint", "artifact", artifact_type="checkpoint",
           path="runtime/state/worker-012_gnum_errfield_verify_checkpoint.json",
           sha256=cp_sha, validation_status="unverified"),
        ev("claim-errfield", "claim", conclusion_type="numerical_evidence",
           statement=("At the pinned bytes (orthogonality artifact 1b2d3162b0715d9b, frozen module "
                      "8ade1cdc163e, protocol 1e6cdf04d7a2, certification 1677822ceb9c) the declared "
                      "error-field check reproduces (l2_error relative 0.0; corr deltas <= 6.7e-16) "
                      "and its 'not a shared-error artifact' reading holds at the certified fixed "
                      "dt=1e-4 on dr=0.2/0.1/0.05: corr(cnfd,cnfem) <= -0.9996256, sign-mass <= "
                      "1.06e-05, corr(lffd,cnfd) >= 0.99999986, spread_relative <= 2.1e-04; the same "
                      "runs reproduce 9/12 certified fixed-dt l2_error rows exactly (dr=0.2/0.1/0.05 "
                      "x three schemes) and the FD/P1-FEM leading coefficients are -1/12 and +1/12. "
                      "Numerical evidence and artifact verification, not a gate verdict and not node "
                      "completion."),
           assumptions=[
               "the frozen module is imported from a byte-identical snapshot and its hash is stable before and after",
               "psi=r*phi, Dirichlet box, Taylor start and pulse family remain shared axes; this measures error-field structure only",
               "the certified regime extension covers 3 of 4 rungs (dr=0.025 not recomputed)",
           ],
           falsifier=report["falsifier"],
           evidence_refs=[report["target_artifact"],
                          "numerics/tests/flat_wave_replication.py#8ade1cdc163e",
                          "numerics/protocol/n0_fixed_dt_certification.json#1677822ceb9c",
                          "numerics/CONVERGENCE_PROTOCOL.md#1e6cdf04d7a2",
                          "artifacts/worker-012/gnum_errfield_verify/report.json#" + hashes[DELIVERABLES[2]][:12]],
           artifact_refs=["artifacts/worker-012/gnum_errfield_verify/report.json#" + hashes[DELIVERABLES[2]][:12],
                          "artifacts/worker-012/gnum_errfield_verify/verify_errfield.py#" + hashes[DELIVERABLES[1]][:12]]),
        ev("review-errfield", "review", reviewer="worker-012", verdict="accept", score=4.5,
           target_id=report["target_artifact"], reviewed_sha256=report["reviewed_hashes"][
               "numerics/protocol/error_field_orthogonality_check.json"],
           hard_failures=[],
           findings=[
               "P1 reproduction: declared dt=1e-3 values reproduce at l2 relative 0.0 and corr <= 6.7e-16; the artifact's reading flags match.",
               "P4 extension: at the certified fixed dt=1e-4 on dr=0.2/0.1/0.05 corr(cnfd,cnfem) = -0.99963/-0.99998/-0.999999, sign-mass <= 1.06e-05, corr(lffd,cnfd) >= 0.99999986, spread_relative <= 2.1e-04; the shared-error exclusion holds in the certified regime.",
               "P3 mechanism: fitted symbol leading coefficients -0.0832336 (FD) and +0.0834328 (P1 FEM) vs declared -1/12 and +1/12, residual <= 4.5e-06.",
               "P5 negative control: a planted shared field is detected (corr 1.0, sign-mass 1.0), so the false reading is not vacuous; P6 bitwise determinism.",
               "BONUS: the same runs reproduce 9/12 certified fixed-dt l2_error rows exactly (relative 0.0); dr=0.025 is the unverified fourth rung and is named as the next falsifier.",
               "SCOPE: filed evidence was at dt=1e-3, one decade from the certified dt=1e-4; this report closes that gap on three rungs. Not a gate verdict.",
           ],
           not_a_gate_verdict=True,
           authority_note=("Worker review event; it cannot set node status, validation_status or a gate "
                           "verdict. N0 stays active, G-NUM pending, numerics_lock LOCKED."),
           evidence_refs=["artifacts/worker-012/gnum_errfield_verify/report.json#" + hashes[DELIVERABLES[2]][:12],
                          report["target_artifact"]]),
        ev("status-complete", "status", status="done", hours=0.4,
           summary=("CHECKPOINT + worker-level task completion (not a node done and not a gate "
                    "verdict). W012-GNUM-ERRFIELD-VERIFY-01 delivered: REPRODUCED_AND_EXTENDED, "
                    "P1-P6 all pass, pins stable, all writes confined to artifacts/worker-012/ plus "
                    "one checkpoint and this outbox. N0 stays active, G-NUM pending, lock LOCKED."),
           evidence_refs=["artifacts/worker-012/gnum_errfield_verify/report.json#" + hashes[DELIVERABLES[2]][:12],
                          "runtime/state/worker-012_gnum_errfield_verify_checkpoint.json#" + cp_sha[:12],
                          report["target_artifact"]],
           next_falsifier=report["next_falsifier"]),
    ]

    from research_map.schemas import validate_event  # noqa: E402
    for e in events:
        validate_event(e)

    existing = set()
    if OUTBOX.is_file():
        for line in OUTBOX.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line).get("event_id"))
            except json.JSONDecodeError:
                pass
    new = [e for e in events if e["event_id"] not in existing]
    with OUTBOX.open("a") as fh:
        for e in new:
            fh.write(json.dumps(e) + "\n")
    print(json.dumps({"checkpoint": str(CHECKPOINT.relative_to(REPO)), "checkpoint_sha256": cp_sha,
                      "events_validated": len(events), "events_appended": len(new),
                      "verdict": report["verdict"], "lock_guard": lock_guard}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
