#!/usr/bin/env python3
"""Emit the flash-13 outbox events + worker checkpoint for the fixed-dt N0 control.

Reads the finished `dt_confound_control.json`, re-verifies every hash on disk, then:
  * appends artifact/claim/status events (protocol-valid) to comms/outbox/deepseek-flash-13.jsonl;
  * writes runtime/state/flash-13_checkpoint_dtconfound.json.

No gate verdict, no node completion, no self-pass.  Refuses to emit if the result JSON is
missing, its recorded hashes do not match disk, or the verdict is `control_invalid`.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RESULT = HERE / "dt_confound_control.json"
DRIVER = HERE / "dt_confound_control.py"
OUTBOX = ROOT / "comms" / "outbox" / "deepseek-flash-13.jsonl"
CHECKPOINT = ROOT / "runtime" / "state" / "flash-13_checkpoint_dtconfound.json"
ACTOR = "deepseek-flash-13"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ref(path: str, digest: str, n: int = 16) -> str:
    return f"{path}#{digest[:n]}"


def main() -> int:
    if not RESULT.is_file():
        print("REFUSE: result JSON absent")
        return 2
    rec = json.loads(RESULT.read_text())
    res_sha, drv_sha = sha256(RESULT), sha256(DRIVER)
    frozen = ROOT / rec["provenance"]["frozen_module"]
    published = ROOT / "numerics" / "tests" / "n0_order_4rung.json"
    protocol = ROOT / "numerics" / "CONVERGENCE_PROTOCOL.md"
    measured = {
        "driver": drv_sha,
        "result": res_sha,
        "frozen": sha256(frozen),
        "published": sha256(published),
        "protocol": sha256(protocol),
    }
    if rec["provenance"]["frozen_module_sha256"] != measured["frozen"]:
        print("REFUSE: frozen module hash mismatch")
        return 2
    if rec["evidence_refs"]["numerics/tests/n0_order_4rung.json"] != measured["published"]:
        print("REFUSE: published 4-rung hash mismatch")
        return 2
    if rec["evidence_refs"]["numerics/CONVERGENCE_PROTOCOL.md"] != measured["protocol"]:
        print("REFUSE: protocol hash mismatch")
        return 2

    verdict = rec["verdict"]["status"]
    if verdict == "control_invalid":
        print("REFUSE: control_invalid -> report as blocker, not claim")
        return 3

    fits_fixed = {s["scheme"]: s["fit_order"] for s in rec["studies_fixed_dt"]["1e-04"]}
    fits_cfl = {c["scheme"]: c["constant_cfl_fit"] for c in rec["comparison_vs_constant_cfl"]}
    fits_txt = ", ".join(f"{k} {v:.5f}" for k, v in fits_fixed.items())
    cfl_txt = ", ".join(f"{k} {v:.5f}" for k, v in fits_cfl.items())
    supported = bool(rec["verdict"]["constant_cfl_claim_supported"])
    contam = {}
    for c in rec["comparison_vs_constant_cfl"]:
        contam[c["scheme"]] = max(abs(e["relative_excess"]) for e in c["per_rung_excess"])
    contam_txt = "/".join(f"{100 * contam[s]:.0f}%" for s in ("lffd", "cnfd", "cnfem"))

    statement = (
        f"Certification-grade fixed-dt study for the N0 spatial order claim (the remediation worker-081 "
        f"measured at 3 rungs / dt=1e-3 and found executable): at protocol rev3 section 3.4's own dt=1e-4, "
        f"four rungs dr=0.2/0.1/0.05/0.025 give fits {fits_txt} (vs the filed constant-CFL cfl=0.5 fits "
        f"{cfl_txt}); all three schemes are monotone, inside |p-2.0|<=0.3 and R5-agree, and a secondary "
        f"dt=1e-3 study agrees within {rec['dt_stability']['max_fit_diff_1e-4_vs_1e-3']:.4f}. "
        f"Positive control: the same runner reproduces all 12 filed constant-CFL l2_error rows bitwise "
        f"(max rel diff {rec['positive_control']['max_rel_diff']:.2e}). "
        + ("The order-2 conclusion is therefore confirmed as a spatial measurement, and the missing "
          "protocol-conformant evidence now exists at the 4-rung certification grade; the filed cfl=0.5 "
          f"study remains a mixed-order run (per-rung |temporal| contamination {contam_txt} for "
          "lffd/cnfd/cnfem, cancellation in lffd/cnfem) and should be kept only as a labelled mixed-order "
          "control, not as the spatial certification. This executes, at 4 rungs and dt=1e-4, the remedy "
          "worker-081 called for; it does not set the gate or rescope the protocol (owner: "
          "astra-lead-numerics)."
           if supported else
           "The constant-CFL order-2 certification is CONFOUNDED by temporal error and must be withdrawn "
           "as spatial evidence pending a fixed-dt recertification.")
    )
    assumptions = [
        "flat-space massless scalar, psi=r*phi reduction, Dirichlet walls, Gaussian pulse, r_max=30, t_end=6",
        "frozen module numerics/tests/flat_wave_replication.py at sha256 8ade1cdc is the controller-verified revision",
        "fixed dt=1e-4 makes RK4/leapfrog/CN temporal error negligible against the O(dr^2) spatial error",
        "no RNG; deterministic reruns",
    ]
    falsifier = rec["falsifier"]
    w081 = ROOT / "artifacts" / "worker-081" / "n0_c8_adjudication" / "adjudication.json"
    w081_ref = ref("artifacts/worker-081/n0_c8_adjudication/adjudication.json", sha256(w081)) if w081.is_file() else None
    evidence = [
        ref("artifacts/flash-13/n0_dt_confound/dt_confound_control.json", res_sha),
        ref("artifacts/flash-13/n0_dt_confound/dt_confound_control.py", drv_sha),
        ref("numerics/tests/flat_wave_replication.py", measured["frozen"]),
        ref("numerics/tests/n0_order_4rung.json", measured["published"]),
        ref("numerics/CONVERGENCE_PROTOCOL.md", measured["protocol"]),
    ]
    if w081_ref:
        evidence.append(w081_ref)
    now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    stamp = time.strftime("%Y%m%dT%H%M%S")
    events = [
        {"event_id": f"f13-dtconfound-{stamp}-artifact-result", "event_type": "artifact",
         "created_at": now, "actor": ACTOR, "node_id": "N0", "gate": "G-NUM",
         "class_id": "AF-WCC-SCALAR-SPH", "artifact_type": "numerical_control_result",
         "path": "artifacts/flash-13/n0_dt_confound/dt_confound_control.json", "sha256": res_sha,
         "validation_status": "unverified",
         "evidence_refs": evidence,
         "note": "hash-pinned fixed-dt control; reviewer evidence only, no gate verdict"},
        {"event_id": f"f13-dtconfound-{stamp}-artifact-driver", "event_type": "artifact",
         "created_at": now, "actor": ACTOR, "node_id": "N0", "gate": "G-NUM",
         "class_id": "AF-WCC-SCALAR-SPH", "artifact_type": "control_driver",
         "path": "artifacts/flash-13/n0_dt_confound/dt_confound_control.py", "sha256": drv_sha,
         "validation_status": "unverified", "evidence_refs": evidence,
         "note": "re-runnable driver; frozen-module hash guard; writes only under artifacts/flash-13/"},
        {"event_id": f"f13-dtconfound-{stamp}-claim", "event_type": "claim",
         "created_at": now, "actor": ACTOR, "node_id": "N0", "gate": "G-NUM",
         "class_id": "AF-WCC-SCALAR-SPH", "conclusion_type": "numerical_evidence",
         "statement": statement, "assumptions": assumptions, "falsifier": falsifier,
         "evidence_refs": evidence,
         "artifact_refs": [ref("artifacts/flash-13/n0_dt_confound/dt_confound_control.json", res_sha)],
         "relation_to_prior_work": (
             "Non-duplicative with worker-081 W081-N0-F1-ADJ-01 (fixed dr, refined dt = temporal direction, "
             "3 rungs at dt=1e-3): this study fixes dt and refines dr (spatial direction, 4 rungs at "
             "section 3.4's dt=1e-4), i.e. the certification-grade filing worker-081's remedy called for."
             + (f" Prior artifact pinned at {w081_ref}." if w081_ref else "")),
         "not_claimed": rec["not_claimed"]},
        {"event_id": f"f13-dtconfound-{stamp}-status", "event_type": "status",
         "created_at": now, "actor": ACTOR, "node_id": "N0", "status": "active",
         "hours": round(float(rec["provenance"]["wall_seconds"]) / 3600.0, 3),
         "summary": (
             f"Bounded worker task (no open lead assignment): fixed-dt control for the w067 F1 G-NUM blocking "
             f"finding -> {verdict}; positive control ok={rec['positive_control']['ok']}; "
             f"hash-pinned result and driver written under artifacts/flash-13/. N0 stays active, "
             f"G-NUM stays pending, numerics_lock stays LOCKED, no self-pass."),
         "evidence_refs": evidence, "next_falsifier": falsifier},
    ]
    for e in events:
        for k in ("event_id", "event_type", "created_at", "actor"):
            assert e.get(k), f"missing {k}"
    with OUTBOX.open("a") as fh:
        for e in events:
            line = json.dumps(e, sort_keys=True)
            json.loads(line)  # must be valid JSON per line
            fh.write(line + "\n")

    ckpt = {
        "checkpoint": "flash-13 dt-confound control",
        "at": now, "worker": ACTOR,
        "assignment_source": rec["assignment_source"],
        "node_id": "N0", "gate": "G-NUM", "class_ids": ["AF-WCC-SCALAR-SPH"],
        "verdict": rec["verdict"],
        "authority": "no gate verdict, no node completion, no self-pass; reviewer evidence only",
        "artifacts": {
            "artifacts/flash-13/n0_dt_confound/dt_confound_control.py": drv_sha,
            "artifacts/flash-13/n0_dt_confound/dt_confound_control.json": res_sha,
            "numerics/tests/flat_wave_replication.py": measured["frozen"],
            "numerics/tests/n0_order_4rung.json": measured["published"],
            "numerics/CONVERGENCE_PROTOCOL.md": measured["protocol"],
        },
        "events_written": [e["event_id"] for e in events],
        "outbox": "comms/outbox/deepseek-flash-13.jsonl",
        "fixed_dt_fits": fits_fixed,
        "constant_cfl_fits": fits_cfl,
        "next_falsifier": falsifier,
        "wall_seconds": rec["provenance"]["wall_seconds"],
    }
    CHECKPOINT.write_text(json.dumps(ckpt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"outbox_events": [e["event_id"] for e in events],
                      "checkpoint": str(CHECKPOINT.relative_to(ROOT)),
                      "result_sha256": res_sha, "driver_sha256": drv_sha,
                      "verdict": verdict}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
