#!/usr/bin/env python3
"""W057-N0-CANONTEMPORAL-VERIFY-01, part B: replay the pinned canonical artifact.

Purpose
-------
`numerics/protocol/canonical_temporal_control.json` (lead-numerics, 00:30) embeds per-row
l2_error values for 3 studies x 4 cfl values, produced by importing the canonical N0
artifact `numerics/tests/flat_wave.py`.  Part A of this task recomputes every *derived*
number from the embedded rows (pure arithmetic, no import).  Part B, here, re-executes the
pinned canonical artifact at the same declared study configurations and compares the freshly
produced rows against the embedded rows.  This tests that the embedded numbers are a faithful
record of the pinned artifact's behaviour; it cannot and does not test the canonical solver's
mathematical correctness (that is the N0 gate chain's job).

Independence boundaries
-----------------------
* The canonical module is imported only after its sha256 equals the hash declared in the
  control artifact and in `research_map/research_map.json` / artifact registry, else the run
  aborts fail-closed with `hash_mismatch`.
* The study kwargs below are a transcription (not an import) of the hash-pinned generator
  `numerics/protocol/canonical_temporal_control.py`; the script checks the literal config
  fragments are present in that generator's source before running, so the transcription is
  bound to the pinned generator hash.
* numpy is used here (same as the generator) because this part is a replay, not the primary
  arithmetic audit; Part A is pure-Python.

Not claimed: no gate verdict, no node completion, no physics claim, no edit to the canonical
artifact.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[3]
CANON = REPO / "numerics" / "tests" / "flat_wave.py"
CONTROL_JSON = REPO / "numerics" / "protocol" / "canonical_temporal_control.json"
GENERATOR = REPO / "numerics" / "protocol" / "canonical_temporal_control.py"
OUT = REPO / "artifacts" / "worker-057" / "n0_canon_temporal_verify" / "replay_report.json"

EXPECTED_CANON_SHA = "8b52014dac47f99663c8bf46fb2e65a80db399860d586d63cd73dd1db1454a6c"
EXPECTED_GENERATOR_SHA = "00a41cfd47088df9432bdc0aba6540cc3c6a69cd1bf88722b228819274adfa0f"

# (label, kwargs, cfl ladder) -- transcribed from the pinned generator (STUDIES, lines 46-53)
STUDIES = [
    ("order2_standing", dict(order=2, family="standing", t_end=0.37),
     [0.25, 0.05, 0.01, 0.002]),
    ("order2_pulse", dict(order=2, family="pulse", R=40.0, t_end=8.0, r0=12.0, sigma=2.0),
     [0.25, 0.05, 0.01, 0.002]),
    ("order4_standing", dict(order=4, family="standing", t_end=0.37,
                             modes=((2, 1.0), (5, 0.5))),
     [0.1, 0.02, 0.004, 0.0008]),
]

# literal fragments that must occur in the pinned generator source for the transcription to bind
CONFIG_FRAGMENTS = [
    '("order2_standing", dict(order=2, family="standing", t_end=0.37), 0.25,',
    '[0.25, 0.05, 0.01, 0.002]),',
    '("order2_pulse", dict(order=2, family="pulse", R=40.0, t_end=8.0, r0=12.0, sigma=2.0),',
    '("order4_standing", dict(order=4, family="standing", t_end=0.37,',
    'modes=((2, 1.0), (5, 0.5))), 0.1, [0.1, 0.02, 0.004, 0.0008]),',
]


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rel(a: float, b: float) -> float:
    return abs(a - b) / max(abs(b), 1e-300)


def load_canonical():
    spec = importlib.util.spec_from_file_location("w057_pinned_flat_wave", CANON)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    t0 = time.time()
    out = {
        "schema": "w057-n0-canonical-temporal-replay/v1",
        "task": "W057-N0-CANONTEMPORAL-VERIFY-01B",
        "actor": "worker-057",
        "class_id": "AF-WCC-SCALAR-SPH",
        "node_id": "N0",
        "gate": "G-NUM",
        "purpose": ("Replay the pinned canonical flat_wave.py at the control's declared study "
                    "configurations and compare fresh rows to the embedded rows."),
        "not_claimed": ["no gate verdict", "no node completion", "no physics claim",
                        "no solver-correctness claim", "no edit to the canonical artifact"],
        "measured_hashes": {
            "numerics/tests/flat_wave.py": sha256_file(CANON),
            "numerics/protocol/canonical_temporal_control.json": sha256_file(CONTROL_JSON),
            "numerics/protocol/canonical_temporal_control.py": sha256_file(GENERATOR),
            "this_script": sha256_file(Path(__file__)),
        },
        "declared_hashes": {
            "canonical": EXPECTED_CANON_SHA,
            "generator": EXPECTED_GENERATOR_SHA,
        },
        "numpy": np.__version__,
        "python": sys.version.split()[0],
    }
    control = json.loads(CONTROL_JSON.read_text())

    # fail-closed hash gates
    gate_failures = []
    if out["measured_hashes"]["numerics/tests/flat_wave.py"] != EXPECTED_CANON_SHA:
        gate_failures.append("canonical flat_wave.py hash != declared control hash")
    if out["measured_hashes"]["numerics/protocol/canonical_temporal_control.py"] != EXPECTED_GENERATOR_SHA:
        gate_failures.append("generator hash != pinned generator hash")
    if control.get("canonical_artifact", {}).get("sha256") != EXPECTED_CANON_SHA:
        gate_failures.append("control artifact's declared canonical sha256 != expected")
    if control.get("canonical_artifact", {}).get("edited") is not False:
        gate_failures.append("control artifact does not declare edited=false")
    gen_src = GENERATOR.read_text()
    missing = [f for f in CONFIG_FRAGMENTS if f not in gen_src]
    if missing:
        gate_failures.append(f"transcribed config fragments missing from pinned generator: {missing}")
    out["hash_gate_failures"] = gate_failures
    if gate_failures:
        out["status"] = "hash_mismatch"
        out["aborted"] = True
        out["runtime_seconds"] = round(time.time() - t0, 2)
        OUT.write_text(json.dumps(out, indent=2) + "\n")
        print(json.dumps({"status": "hash_mismatch", "failures": gate_failures}, indent=1))
        return 2

    fw = load_canonical()
    out["status"] = "ran"
    out["studies"] = {}
    worst_rel = 0.0
    worst_where = None
    worst_fit_rel = 0.0
    for label, kwargs, cfls in STUDIES:
        emb = control["studies"][label]
        rec = {"cfl_ladder": cfls, "runs": {}}
        for cfl in cfls:
            st = fw.convergence_study(cfl=cfl, **kwargs)
            key = f"{cfl:g}"
            emb_run = emb["runs"][key]
            rows_new = [{"n": int(r["n"]), "dt": float(r["dt"]),
                         "dx": float(r["dx"]), "l2_error": float(r["l2_error"])}
                        for r in st["rows"]]
            fit_new = float(np.polyfit(np.log([r["dx"] for r in st["rows"]]),
                                       np.log([r["l2_error"] for r in st["rows"]]), 1)[0])
            emb_rows = emb_run["rows"]
            row_cmp = []
            run_worst = 0.0
            for a, b in zip(rows_new, emb_rows):
                if a["n"] != b["n"]:
                    row_cmp.append({"n_new": a["n"], "n_emb": b["n"], "match": False})
                    run_worst = float("inf")
                    continue
                r_dt = rel(a["dt"], b["dt"])
                r_e = rel(a["l2_error"], b["l2_error"])
                run_worst = max(run_worst, r_dt, r_e)
                row_cmp.append({"n": a["n"], "dt_rel": r_dt, "l2_rel": r_e,
                                "l2_new": a["l2_error"], "l2_emb": b["l2_error"]})
            fit_rel = rel(fit_new, float(emb_run["fit_order"]))
            worst_fit_rel = max(worst_fit_rel, fit_rel)
            gate_new = bool(st["order_gate"]["pass"])
            rec["runs"][key] = {
                "cfl": cfl,
                "rows": row_cmp,
                "max_rel_diff": run_worst,
                "fit_order_new": fit_new,
                "fit_order_emb": float(emb_run["fit_order"]),
                "fit_order_rel": fit_rel,
                "order_gate_pass_new": gate_new,
                "order_gate_pass_emb": bool(emb_run["order_gate_pass"]),
                "order_l2_rel_max": max(
                    [rel(x, y) for x, y in zip(st["order_l2"], emb_run["order_l2"])] or [0.0]),
            }
            if run_worst > worst_rel:
                worst_rel = run_worst
                worst_where = f"{label}/{key}"
        out["studies"][label] = rec

    # pass threshold: same machine/numpy => deterministic replay; 1e-10 is generous.
    REPLAY_TOL = 1e-10
    out["replay_tolerance"] = REPLAY_TOL
    out["worst_row_rel_diff"] = worst_rel
    out["worst_row_rel_diff_at"] = worst_where
    out["worst_fit_order_rel_diff"] = worst_fit_rel
    out["all_rows_within_tolerance"] = bool(worst_rel <= REPLAY_TOL)
    out["all_fit_orders_within_tolerance"] = bool(worst_fit_rel <= REPLAY_TOL)
    out["verdict"] = ("REPLAYED: fresh runs of the pinned canonical artifact reproduce every "
                      "embedded row and fitted order within {:g} relative".format(REPLAY_TOL)
                      if (out["all_rows_within_tolerance"]
                          and out["all_fit_orders_within_tolerance"])
                      else "REPLAY-MISMATCH: at least one embedded number is not reproduced")
    out["runtime_seconds"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({
        "status": out["status"], "verdict": out["verdict"],
        "worst_row_rel_diff": worst_rel, "worst_row_rel_diff_at": worst_where,
        "worst_fit_order_rel_diff": worst_fit_rel, "runtime_seconds": out["runtime_seconds"],
    }, indent=1))
    return 0 if (out["all_rows_within_tolerance"]
                 and out["all_fit_orders_within_tolerance"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
