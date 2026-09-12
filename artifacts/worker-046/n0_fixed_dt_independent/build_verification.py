#!/usr/bin/env python3
"""Build verification.json + MANIFEST.json for W046-N0-FIXEDDT-INDEP-01 (worker-046).

Reads the raw `results.json` produced by `independent_fixed_dt.py`, extracts the
pre-registered criteria outcomes and headline numbers, hash-binds every file in this
directory, and writes the verification record. `build_manifest` then writes MANIFEST.json.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results.json"
VERIFICATION = HERE / "verification.json"
MANIFEST = HERE / "MANIFEST.json"

FALSIFIER = (
    "Re-run `independent_fixed_dt.py` after any change to this script or to the three pinned "
    "inputs (frozen module 8ade1cdc, published n0_order_4rung.json c88146a1, protocol "
    "1e6cdf04): a scheme outside p = 2.0 +/- 0.3, non-monotone errors, dt != 1e-4 on any rung, "
    "an A8 control failing, an R5 disagreement with the published order, or any hash-guard "
    "mismatch falsifies or voids the result (hash mismatch exits 2 fail-closed). If the protocol "
    "hash measured at review time is not 1e6cdf04d7a2, the section-3.4 binding of this study is "
    "void even if the numbers reproduce."
)

NOT_CLAIMED = [
    "no gate verdict (G-NUM stays pending; authority Astra / lead-audit)",
    "no node completion (N0 stays active/unverified)",
    "no numerics_lock release (N1 stays queued/locked; no spherical_solver written)",
    "no physics / self-gravity / WCC / SCC claim",
    "no claim that worker-067 F1 is withdrawn: that is a reviewer/controller decision; this "
    "artifact supplies the evidence the F1 falsifier clause names",
]


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def build_verification() -> dict:
    r = json.loads(RESULTS.read_text())
    per = r["fixed_dt_study"]
    headline = {}
    for s, v in per.items():
        headline[s] = {
            "fit_order_fixed_dt": v["fit_order"],
            "delta_R5_fixed_dt": v["delta_R5"],
            "least_squares_se": v["least_squares_se"],
            "pair_orders": v["pair_orders"],
            "n_rungs": v["n_rungs"],
            "dt_all_fixed_1e-4": v["dt_all_fixed"],
            "monotone": v["monotone"],
            "published_fit_order_cfl_0.5": v["published_fit_order"],
            "published_delta_R5": v["published_delta_R5"],
            "abs_diff_vs_published": v["abs_diff_vs_published"],
            "r5_bound": v["r5_bound"],
            "r5_agrees": v["r5_agrees"],
        }
    controls = {
        "C1_same_object_reproduces_published": {
            s: {"fit_order": c["fit_order"], "published_fit_order": c["published_fit_order"],
                "rel_diff": c["rel_diff"], "reproduces_lt_1e-9": c["reproduces_lt_1e-9"],
                "monotone": c["monotone"], "n_rungs": c["n_rungs"]}
            for s, c in r["controls"]["C1_same_object_cfl_0.5"].items()},
        "C2_contamination_dt_dr_pow_half": {
            s: {"fit_order": c["fit_order"], "contamination_detected": c["contamination_detected"],
                "monotone": c["monotone"]}
            for s, c in r["controls"]["C2_contamination_dt_dr_pow_half"].items()},
        "C3_determinism_bitwise_equal": r["controls"]["C3_determinism_repeat"]["bitwise_equal"],
    }
    v = {
        "task_id": r["task_id"],
        "worker": r["worker"],
        "role": "bounded execution worker (no gate authority)",
        "class_id": r["class_id"],
        "node_id": r["node_id"],
        "gate": r["gate"],
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "verdict": r["verdict"],
        "verdict_rule": r["verdict_rule"],
        "criteria": r["criteria"],
        "criteria_outcomes": r["criteria_outcomes"],
        "failed_criteria": r["failed_criteria"],
        "headline": headline,
        "controls": controls,
        "f1_falsifier_clause_triggered": r["f1_falsifier_clause_triggered"],
        "f1_statement": r["f1_statement"],
        "inputs": r["inputs"],
        "protocol_hash_moved_during_run": r["protocol_hash_moved_during_run"],
        "published_declared": r["published_declared"],
        "run_started_at": r["started_at"],
        "run_finished_at": r["finished_at"],
        "evidence_refs": [
            "artifacts/worker-046/n0_fixed_dt_independent/independent_fixed_dt.py",
            "artifacts/worker-046/n0_fixed_dt_independent/results.json",
            "artifacts/worker-046/n0_fixed_dt_independent/verification.json",
            "artifacts/worker-046/n0_fixed_dt_independent/MANIFEST.json",
            "artifacts/worker-046/n0_fixed_dt_independent/README.md",
            "artifacts/worker-046/n0_fixed_dt_independent/CHECKPOINT.json",
            "numerics/tests/flat_wave_replication.py#8ade1cdc163e",
            "numerics/tests/n0_order_4rung.json#c88146a1375c",
            "numerics/CONVERGENCE_PROTOCOL.md#1e6cdf04d7a2",
            "artifacts/worker-067/g_num_protocol_review/review.json",
        ],
        "artifact_hashes": {},
        "falsifier": FALSIFIER,
        "not_claimed": NOT_CLAIMED,
        "validation_status": "unverified",
    }
    files = ["independent_fixed_dt.py", "run.log", "results.json"]
    v["artifact_hashes"] = {f: sha256_file(HERE / f) for f in files if (HERE / f).is_file()}
    VERIFICATION.write_text(json.dumps(v, indent=1, sort_keys=True) + "\n")
    return v


def build_manifest() -> dict:
    files = ["independent_fixed_dt.py", "build_verification.py", "run.log", "results.json",
             "verification.json", "README.md"]
    man = {
        "task_id": "W046-N0-FIXEDDT-INDEP-01",
        "worker": "worker-046",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "files": {f: sha256_file(HERE / f) for f in files if (HERE / f).is_file()},
        "pinned_inputs": {
            "numerics/tests/flat_wave_replication.py": "8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422",
            "numerics/tests/n0_order_4rung.json": "c88146a1375c50f0c87d2893109087ee6f08c55919a4812dc073750bd86f544a",
            "numerics/CONVERGENCE_PROTOCOL.md": "1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274",
        },
        "self_excluded": "MANIFEST.json (cannot contain its own hash) and CHECKPOINT.json "
                         "(written after the manifest; it carries the manifest hash)",
    }
    MANIFEST.write_text(json.dumps(man, indent=1, sort_keys=True) + "\n")
    return man


if __name__ == "__main__":
    v = build_verification()
    m = build_manifest()
    out = {"verdict": v["verdict"], "failed_criteria": v["failed_criteria"],
           "f1_falsifier_clause_triggered": v["f1_falsifier_clause_triggered"],
           "verification_sha256": sha256_file(VERIFICATION),
           "manifest_sha256": sha256_file(MANIFEST)}
    print(json.dumps(out, indent=2))
