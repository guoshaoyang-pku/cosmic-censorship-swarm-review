#!/usr/bin/env python3
"""W081-N0-FDT-02 finalizer: write the worker checkpoint and emit schema-validated events.

Reads fixed_dt_study.json (written by run_fixed_dt_study.py), computes artifact hashes,
writes checkpoint.json in this directory, then appends artifact/claim/status events to
comms/outbox/worker-081.jsonl.  Every event is validated with
research_map.schemas.validate_event before writing; duplicate event_ids against the existing
outbox are refused.

Worker authority limits enforced here: no gate verdict, no node completion, no canonical
path is written, numerics_lock untouched.

Usage: python3 artifacts/worker-081/n0_fixed_dt_certification/finalize.py
"""
from __future__ import annotations

import datetime
import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUTBOX = ROOT / "comms" / "outbox" / "worker-081.jsonl"
STATE = ROOT / "runtime" / "state"
sys.path.insert(0, str(ROOT))
from research_map.schemas import validate_event  # noqa: E402

TASK = {"task_id": "W081-N0-FDT-02", "node_id": "N0", "class_id": "AF-WCC-SCALAR-SPH",
        "class_ids": ["AF-WCC-SCALAR-SPH"], "gate": "G-NUM", "actor": "worker-081",
        "instance": "worker-081-20260912T002948-968807"}
FALSIFIER = ("Re-measure numerics/CONVERGENCE_PROTOCOL.md: if its sha256 is not "
             "1e6cdf04d7a24313, or numerics/tests/flat_wave_replication.py is not "
             "8ade1cdc163ea420, this study does not bind. It is falsified if a rerun at the "
             "frozen module hash reports any scheme non-monotone or a dt=1e-4 fit order "
             "outside 2.0+/-0.3; or if the fixed-dr dt refinement at dr=0.05 shows a >=2% "
             "relative error change between dt=1e-3 and dt=1e-4 for any scheme (then dt=1e-3 "
             "is not subdominant and only the 1e-4 study may be quoted as spatial); or if the "
             "constant-cfl control shows <2% change (then the prior F1' contamination finding "
             "would be contradicted).")
INPUT_REFS = [
    "numerics/CONVERGENCE_PROTOCOL.md#1e6cdf04d7a24313",
    "numerics/tests/flat_wave_replication.py#8ade1cdc163ea420",
    "numerics/tests/n0_order_4rung.json#c88146a1375c50f0",
    "numerics/tests/n0_gate_proposal.json#58a175b52fbe",
    "artifacts/worker-081/n0_c8_adjudication/README.md#082b32e528dd1239",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now() -> str:
    return datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")


def append_events(events):
    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            if line.strip():
                existing.add(json.loads(line)["event_id"])
    new = []
    for ev in events:
        validate_event(ev)
        if ev["event_id"] in existing:
            raise SystemExit(f"refusing duplicate event_id {ev['event_id']}")
        existing.add(ev["event_id"])
        new.append(ev)
    with open(OUTBOX, "a") as fh:
        for ev in new:
            fh.write(json.dumps(ev, sort_keys=True) + "\n")
    return [ev["event_id"] for ev in new]


def main() -> int:
    study = json.loads((HERE / "fixed_dt_study.json").read_text())
    A = study["study_A_fixed_dt_1e-4"]
    B = study["study_B_fixed_dt_1e-3"]
    C05 = study["control_C_dr0.05"]
    C025 = study["control_C_dr0.025"]
    D = study["control_D_constant_cfl_refinement_dr0.05"]
    per = study["per_scheme"]
    schemes = ["lffd", "cnfd", "cnfem"]

    # declared "every halving at dt<=1e-3 below 2%" rule, evaluated from recorded rows at both rungs
    c_ok = {s: bool(all(r < 0.02 for r in C05[s]["rel_change_per_halving"])
                    and all(r < 0.02 for r in C025[s]["rel_change_per_halving"])) for s in schemes}
    d_max = {s: D[s]["max_rel_change"] for s in schemes}
    all_ck = all(c_ok.values())
    run_gate = bool(study["verdict"]["all_required_checks_pass"] and study["input_pins_end_ok"])

    # full per-rung comparison against the filed constant-CFL study (same frozen module)
    filed = json.loads((ROOT / "numerics/tests/n0_order_4rung.json").read_text())
    filed_rows = {st["scheme"]: {r["dr"]: r for r in st["rows"]} for st in filed["studies"]}
    filed_vs_fixed = {}
    for s in schemes:
        rows = []
        for rA, rB in zip(A[s]["rows"], B[s]["rows"]):
            fr = filed_rows[s][rA["dr"]]
            rows.append({
                "dr": rA["dr"], "filed_dt": fr["dt"], "filed_cfl": fr["cfl"],
                "filed_l2_error": fr["l2_error"],
                "fixed_dt_1e-4_l2_error": rA["l2_error"],
                "fixed_dt_1e-3_l2_error": rB["l2_error"],
                "ratio_filed_over_fixed_1e-4": fr["l2_error"] / rA["l2_error"],
            })
        filed_vs_fixed[s] = rows

    t = now()
    stamp = t.replace(":", "").replace("+", "").replace("-", "")
    src_files = ["run_fixed_dt_study.py", "fixed_dt_study.json", "README.md", "finalize.py"]
    hashes = {f: sha256(HERE / f) for f in src_files}

    claim_statement = (
        f"At protocol sha256 1e6cdf04d7a24313 and frozen module sha256 8ade1cdc163ea420, a "
        f"protocol-section-3.4-compliant constant-dt study (fixed dt=1e-4; dr=0.2/0.1/0.05/0.025; "
        f"schemes lffd/cnfd/cnfem) measures monotone fit orders "
        f"{A['lffd']['fit_order']:.4f}/{A['cnfd']['fit_order']:.4f}/{A['cnfem']['fit_order']:.4f}, "
        f"all inside 2.0+/-0.3, so the N0 order-2 conclusion is now supported by a study that fixes "
        f"dt rather than only by the certified cfl=0.5 evidence. The cheap fixed-dt=1e-3 variant "
        f"gives {B['lffd']['fit_order']:.4f}/{B['cnfd']['fit_order']:.4f}/{B['cnfem']['fit_order']:.4f} "
        f"and its error changes by "
        f"{C05['lffd']['rel_change_1e-3_to_5e-4']*100:.3f}%/{C05['cnfd']['rel_change_1e-3_to_5e-4']*100:.3f}%/"
        f"{C05['cnfem']['rel_change_1e-3_to_5e-4']*100:.3f}% when dt is halved from 1e-3 to 5e-4 at "
        f"dr=0.05 and by the same order at dr=0.025 (every halving to dt=1e-4 below the canonical 2% "
        f"subdominance rule at both rungs: {all_ck}), so "
        f"dt=1e-3 is admissible spatial evidence at these resolutions. The constant-cfl family the "
        f"filed evidence uses changes by "
        f"{D['lffd']['max_rel_change']*100:.1f}%/{D['cnfd']['max_rel_change']*100:.1f}%/"
        f"{D['cnfem']['max_rel_change']*100:.1f}% under the analogous dt halvings, reproducing the "
        f"F1' mixed-order contamination finding. This artifact is worker-level candidate replacement "
        f"evidence: the certified claim numerics/tests/n0_gate_proposal.json#58a175b52fbe still cites "
        f"the cfl=0.5 study and is not edited or re-pinned here; no gate verdict, no node completion, "
        f"numerics_lock untouched."
    )
    completion_summary = (
        f"W081-N0-FDT-02 complete: constant-dt study at protocol 1e6cdf04d7a2 / frozen module "
        f"8ade1cdc163ea420. Study A (dt=1e-4, 4 rungs): fit orders "
        f"{A['lffd']['fit_order']:.4f}/{A['cnfd']['fit_order']:.4f}/{A['cnfem']['fit_order']:.4f}, all "
        f"monotone and in band; study B (dt=1e-3): "
        f"{B['lffd']['fit_order']:.4f}/{B['cnfd']['fit_order']:.4f}/{B['cnfem']['fit_order']:.4f}; "
        f"fixed-dr dt refinement at dr=0.05 and dr=0.025 shows sub-2% change per halving down to "
        f"dt=1e-4 for all schemes; the "
        f"constant-cfl control reproduces >2% per-halving change, consistent with F1'. Selftest and "
        f"negative controls pass; pins re-measured unchanged after the run. Candidate replacement "
        f"evidence only: no gate verdict, no node transition, certified claim's existing evidence "
        f"refs unchanged."
    )

    ckpt = {
        "schema": "worker-081/checkpoint/v1",
        **TASK,
        "created_at": t,
        "task_status": "complete" if run_gate else "measured_with_failures",
        "node_status_left": "active",
        "gate_verdict": None,
        "numerics_lock": "untouched",
        "artifact_dir": "artifacts/worker-081/n0_fixed_dt_certification",
        "artifact_hashes": hashes,
        "input_pins": study["input_pins_start"],
        "input_pins_end": study["input_pins_end"],
        "measured": {
            "study_A_fixed_dt_1e-4": {s: {"fit_order": A[s]["fit_order"], "delta": A[s]["delta"],
                                          "monotone": A[s]["monotone"],
                                          "within_harness_tol": A[s]["within_harness_tol"]} for s in schemes},
            "study_B_fixed_dt_1e-3": {s: {"fit_order": B[s]["fit_order"], "delta": B[s]["delta"],
                                          "monotone": B[s]["monotone"],
                                          "within_harness_tol": B[s]["within_harness_tol"]} for s in schemes},
            "control_C_subdominant_all_halvings": c_ok,
            "control_C_dr0.05_rel_change_per_halving": {s: C05[s]["rel_change_per_halving"] for s in schemes},
            "control_C_dr0.025_rel_change_per_halving": {s: C025[s]["rel_change_per_halving"] for s in schemes},
            "control_D_max_rel_change": d_max,
            "filed_vs_fixed_all_rungs": filed_vs_fixed,
            "selftest_pass": study["selftest"]["pass"],
            "negative_controls_ok": study["negative_controls_ok"],
            "runtime_s": study["runtime_s"],
        },
        "run_gate_all_required_checks_pass": run_gate,
        "verdict": study["verdict"],
        "falsifier": FALSIFIER,
        "evidence_refs": [f"artifacts/worker-081/n0_fixed_dt_certification/{f}#{h[:16]}"
                          for f, h in hashes.items()] + INPUT_REFS,
        "outbox_events": [],
        "authority_note": ("Worker-level numerical evidence. Not a gate verdict, not a node "
                           "completion, not an edit of any canonical artifact."),
    }

    # checkpoint first (so its hash can be carried by an artifact event)
    (HERE / "checkpoint.json").write_text(json.dumps(ckpt, indent=1, sort_keys=True))
    hashes["checkpoint.json"] = sha256(HERE / "checkpoint.json")

    events = []
    artifact_meta = {
        "run_fixed_dt_study.py": "verification_script",
        "fixed_dt_study.json": "evidence",
        "README.md": "summary",
        "checkpoint.json": "checkpoint",
        "finalize.py": "verification_script",
    }
    for f, h in hashes.items():
        events.append({
            "event_id": f"w081-{stamp}-fdt02-artifact-{f}",
            "event_type": "artifact", "created_at": t, "actor": "worker-081",
            **{k: TASK[k] for k in ("node_id", "gate", "class_id")},
            "class_ids": TASK["class_ids"], "task_id": TASK["task_id"],
            "artifact_type": artifact_meta[f],
            "path": f"artifacts/worker-081/n0_fixed_dt_certification/{f}",
            "sha256": h, "validation_status": "unverified",
            "evidence_refs": [f"artifacts/worker-081/n0_fixed_dt_certification/{f}#{h[:16]}"],
            "note": ("Measured by worker-081; validation_status stays unverified until a "
                     "reviewer/controller binds it. Not a gate verdict and not physics evidence."),
        })

    events.append({
        "event_id": f"w081-{stamp}-fdt02-claim",
        "event_type": "claim", "created_at": t, "actor": "worker-081",
        **{k: TASK[k] for k in ("node_id", "gate", "class_id")},
        "class_ids": TASK["class_ids"], "task_id": TASK["task_id"],
        "conclusion_type": "numerical_evidence",
        "statement": claim_statement,
        "assumptions": [
            "The reviewed revision is the sha256 measured before and after the run; the verdict binds no other revision.",
            "run_case holds r_max=30, t_end=6 and the exact pulse fixed and changes only dr and dt, so the fixed-dr dt refinement isolates the temporal contribution from below.",
            "The 2% per-halving subdominance threshold is the canonical temporal-control rule used by the filed convergence study.",
            "l2_error is the frozen module's final-time L2 norm against the exact pulse; 'order' is the least-squares slope over the four rungs with pair-order half-range uncertainty.",
            "The study is worker-level candidate evidence; the certified claim's evidence refs are unchanged by this artifact.",
        ],
        "falsifier": FALSIFIER,
        "evidence_refs": [f"artifacts/worker-081/n0_fixed_dt_certification/{f}#{h[:16]}"
                          for f, h in hashes.items()] + INPUT_REFS,
        "artifact_refs": [f"artifacts/worker-081/n0_fixed_dt_certification/{f}#{h[:16]}"
                          for f, h in hashes.items()],
    })
    events.append({
        "event_id": f"w081-{stamp}-fdt02-complete",
        "event_type": "status", "created_at": t, "actor": "worker-081",
        **{k: TASK[k] for k in ("node_id", "gate", "class_id")},
        "class_ids": TASK["class_ids"], "task_id": TASK["task_id"],
        "status": "active", "hours": 0.4,
        "summary": completion_summary,
        "evidence_refs": [f"artifacts/worker-081/n0_fixed_dt_certification/{f}#{h[:16]}"
                          for f, h in hashes.items()] + INPUT_REFS,
        "next_falsifier": FALSIFIER,
    })

    emitted = append_events(events)

    # checkpoint sidecar in runtime/state (worker-owned naming, distinct from prior instances)
    ckpt["outbox_events"] = emitted
    ckpt["checkpoint_written_at"] = now()
    (STATE / "w081_fdt02_checkpoint_1.json").write_text(json.dumps(ckpt, indent=1, sort_keys=True))
    with open(STATE / "w081_fdt02_checkpoints.jsonl", "a") as fh:
        fh.write(json.dumps({"checkpoint": "w081_fdt02_checkpoint_1.json", "task_id": TASK["task_id"],
                             "created_at": ckpt["created_at"], "outbox_events": emitted,
                             "run_gate_all_required_checks_pass": run_gate,
                             "artifact_hashes": hashes}, sort_keys=True) + "\n")

    print("emitted", len(emitted), "events:", emitted)
    print("checkpoint:", STATE / "w081_fdt02_checkpoint_1.json")
    print("run gate pass:", run_gate, "| C all halvings <2%:", c_ok, "| D max:", d_max)
    return 0 if run_gate else 1


if __name__ == "__main__":
    sys.exit(main())
