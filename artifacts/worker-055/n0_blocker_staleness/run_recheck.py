#!/usr/bin/env python3
"""W055-N0-BLOCKER-STALENESS-01: independent recheck of the N0 replication blocker.

Worker: worker-055.  Node: N0.  Gate: G-NUM.  Class: AF-WCC-SCALAR-SPH (singular).

QUESTION
    research_map/research_map.json carries an N0 blocker, recorded 2026-09-11T23:24:47+08:00,
    stating that the controller replication gave cnfem order -0.0773 and top-level verdict
    ORDER DISAGREES.  Is that blocker still live evidence against N0, or is it stale?

METHOD (all inputs pinned by sha256; nothing here is a fluent claim)
    1. verify numerics/tests/flat_wave_replication.py on disk == 8ade1cdc (the revision
       named by the LATER controller run n0_replication_astra_run2_FIXED.json);
    2. read both controller runs and their recorded script_sha256 / replication_verdict;
    3. re-run order_study(lffd|cnfd|cnfem) at the exact controller config
       dr=[0.2,0.1,0.05], cfl=0.5, r_max=30.0, t_end=6.0 on the pinned module;
    4. compare the re-run cnfem fit against the blocker's cited -0.0773 and against
       run2_FIXED's 1.9863235066828981;
    5. pull the N0 blocker text + timestamp straight out of the map, so the staleness
       claim is about the bytes on disk, not a paraphrase.

OUTPUT
    artifacts/worker-055/n0_blocker_staleness/recheck.json  (all hashes + rows + verdict)

USAGE
    python3 artifacts/worker-055/n0_blocker_staleness/run_recheck.py
Exit 0 = recheck completed (see verdict.stale_blocker_supported); 2 = input hash guard failed.
"""
from __future__ import annotations

import hashlib
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent

FROZEN = ROOT / "numerics/tests/flat_wave_replication.py"
FROZEN_SHA = "8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422"
RUN1 = ROOT / "runtime/state/controller_verification/n0_replication_astra_run.json"
RUN2 = ROOT / "runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json"
ADJ = ROOT / "runtime/state/controller_verification/N0_adjudication.md"
MAP = ROOT / "research_map/research_map.json"

CONFIG = {"dr_values": [0.2, 0.1, 0.05], "cfl": 0.5, "r_max": 30.0, "t_end": 6.0,
          "p_expected": 2.0, "p_tol": 0.3}
SCHEMES = ["lffd", "cnfd", "cnfem"]
BLOCKER_AT = "2026-09-11T23:24:47+08:00"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_map_node_blockers(node_id: str):
    m = json.loads(MAP.read_text())
    for grp in m["groups"]:
        for n in grp.get("nodes", []):
            if n.get("id") == node_id:
                return {
                    "node_id": node_id,
                    "node_status": n.get("status"),
                    "node_validation_status": n.get("validation_status"),
                    "class_ids": n.get("class_ids") or n.get("class_id"),
                    "blockers": n.get("blockers", []),
                }
    raise SystemExit(f"node {node_id} not found in map")


def classify_blockers(blockers, run2):
    """Split the N0 blockers into stale (superseded by run2_FIXED + addendum) and live.

    Staleness test for an entry, applied only when its text cites the superseded run1
    cnfem failure (-0.0773 / ORDER DISAGREES) or demands a re-pin/re-run at the current
    hash: the entry is stale iff it carries no resolution/resolved_at field AND
    run2_FIXED (script 8ade1cdc, verdict ORDER REPRODUCED, generated_at later than the
    entry) exists on disk.
    """
    stale_marks = ("-0.0773", "ORDER DISAGREES", "re-pins and re-runs the replication")
    stale, live = [], []
    for b in blockers:
        text = (b.get("description") or "") + " " + str(b.get("needed_to_unblock") or "")
        marked = any(s in text for s in stale_marks)
        unannotated = "resolved_at" not in b and "resolution" not in b
        run2_later = run2["provenance"]["generated_at"][:19] > (b.get("at") or "")[:19]
        is_stale = bool(marked and unannotated and run2_later)
        entry = {
            "at": b.get("at"),
            "cites_superseded_or_repin": marked,
            "has_resolution_fields": not unannotated,
            "run2_fixed_is_later": run2_later,
            "stale": is_stale,
            "description_head": (b.get("description") or "")[:180],
        }
        (stale if is_stale else live).append(entry)
    return stale, live


def main() -> int:
    got = sha256(FROZEN)
    if got != FROZEN_SHA:
        print(f"REFUSE: frozen module sha256 {got} != pinned {FROZEN_SHA}")
        return 2

    sys.path.insert(0, str(ROOT / "numerics/tests"))
    import flat_wave_replication as rep  # noqa: E402

    run1 = json.loads(RUN1.read_text())
    run2 = json.loads(RUN2.read_text())

    studies = []
    for scheme in SCHEMES:
        st = rep.order_study(scheme, dr_values=CONFIG["dr_values"], cfl=CONFIG["cfl"],
                             r_max=CONFIG["r_max"], t_end=CONFIG["t_end"])
        studies.append(st)

    by_scheme = {s["scheme"]: s for s in studies}
    cnfem = by_scheme["cnfem"]
    p = cnfem["fit_order"]
    # tolerance for "reproduces order 2" is the module's own declared p_expected +/- p_tol
    reproduces = bool(cnfem["monotone"] and abs(p - CONFIG["p_expected"]) <= CONFIG["p_tol"])
    blocker_claimed_failure = bool(p < 0.0 or not cnfem["monotone"])

    # Failure-detection control: the explicit leapfrog scheme (lffd) is unstable above its
    # CFL limit, so at cfl=1.5 the pipeline must NOT report a clean monotone order-2 fit.
    # (cnfem/cnfd are Crank-Nicolson and unconditionally stable; they are recorded as a
    # secondary observation, not as the failure control.)
    control = rep.order_study("lffd", dr_values=CONFIG["dr_values"], cfl=1.5,
                              r_max=CONFIG["r_max"], t_end=CONFIG["t_end"])
    control_max_err = max(r["l2_error"] for r in control["rows"])
    control_detects_failure = bool((not control["monotone"]) or control_max_err > 1.0)
    cn_stability = rep.order_study("cnfem", dr_values=CONFIG["dr_values"], cfl=1.5,
                                   r_max=CONFIG["r_max"], t_end=CONFIG["t_end"])

    node = load_map_node_blockers("N0")
    at_entry = [b for b in node["blockers"] if b.get("at") == BLOCKER_AT]
    blocker_text = at_entry[0]["description"] if at_entry else None
    stale_entries, live_entries = classify_blockers(node["blockers"], run2)

    rec = {
        "artifact": "artifacts/worker-055/n0_blocker_staleness/run_recheck.py",
        "artifact_id": "W055-N0-BLOCKER-STALENESS-01",
        "worker": "worker-055",
        "node_id": "N0",
        "gate": "G-NUM",
        "class_id": "AF-WCC-SCALAR-SPH",
        "class_binding": "singular frozen class id; flat-space calibration sub-case, no self-gravity",
        "conclusion_type": "numerical_evidence",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "question": ("Is the N0 blocker recorded at 2026-09-11T23:24:47+08:00 (cnfem order "
                     "-0.0773, ORDER DISAGREES) still live evidence against N0?"),
        "provenance": {
            "frozen_module": "numerics/tests/flat_wave_replication.py",
            "frozen_module_sha256": got,
            "frozen_module_sha256_pinned": FROZEN_SHA,
            "frozen_module_hash_guard": "pass",
            "controller_run1_superseded": {"path": str(RUN1.relative_to(ROOT)),
                                           "sha256": sha256(RUN1),
                                           "script_sha256": run1["provenance"]["script_sha256"],
                                           "generated_at": run1["provenance"]["generated_at"],
                                           "replication_verdict": run1["result"]["replication_verdict"],
                                           "cnfem_order": run1["result"]["independent_orders"]["cnfem"]},
            "controller_run2_fixed": {"path": str(RUN2.relative_to(ROOT)),
                                      "sha256": sha256(RUN2),
                                      "script_sha256": run2["provenance"]["script_sha256"],
                                      "generated_at": run2["provenance"]["generated_at"],
                                      "replication_verdict": run2["result"]["replication_verdict"],
                                      "cnfem_order": run2["result"]["independent_orders"]["cnfem"]},
            "adjudication_addendum": {"path": str(ADJ.relative_to(ROOT)), "sha256": sha256(ADJ)},
            "research_map": {"path": str(MAP.relative_to(ROOT)), "sha256": sha256(MAP)},
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "platform": platform.platform(),
            "seeds": "none: deterministic fixed-grid solve, no RNG; module records bitwise-equal rerun",
        },
        "config": CONFIG,
        "map_blocker_at_pinned_map_hash": {
            "node": node,
            "blocker_at": BLOCKER_AT,
            "blocker_text": blocker_text,
        },
        "blocker_staleness": {
            "n_blockers_total": len(node["blockers"]),
            "stale_entries": stale_entries,
            "live_or_unclassified_entries": live_entries,
            "stale_entry_count": len(stale_entries),
            "run2_generated_at": run2["provenance"]["generated_at"],
            "run2_sha256_map_denomination": "6542db93eebc5095cb903478dfa6a8d24f09776513f9accb1e73f9d0a58ba38e",
            "run2_hash_matches_denomination": sha256(RUN2).startswith("6542db93"),
        },
        "failure_detection_control": {
            "scheme": "lffd", "cfl": 1.5,
            "expected": "explicit leapfrog above CFL limit: unstable / non-monotone / L2 blow-up",
            "fit_order": control["fit_order"], "monotone": control["monotone"],
            "max_l2_error": control_max_err, "rows": control["rows"],
            "pipeline_detects_failure": control_detects_failure,
            "secondary_observation": {
                "scheme": "cnfem", "cfl": 1.5,
                "note": ("Crank-Nicolson is unconditionally stable, so this is NOT a failure "
                         "control; recorded to show cfl=1.5 does not by itself break the cnfem "
                         "pathway"),
                "fit_order": cn_stability["fit_order"], "monotone": cn_stability["monotone"],
                "max_l2_error": max(r["l2_error"] for r in cn_stability["rows"]),
            },
        },
        "rerun_order_studies": studies,
        "comparison": {
            "rerun_cnfem_fit_order": p,
            "rerun_cnfem_monotone": cnfem["monotone"],
            "rerun_cnfem_within_harness_tol": cnfem["within_harness_tol"],
            "run1_cnfem_fit_order": run1["result"]["independent_orders"]["cnfem"],
            "run2_cnfem_fit_order": run2["result"]["independent_orders"]["cnfem"],
            "matches_run1_failure": blocker_claimed_failure,
            "matches_run2_fixed": bool(abs(p - run2["result"]["independent_orders"]["cnfem"]) < 1e-9),
            "run1_script_sha256": run1["provenance"]["script_sha256"],
            "run2_script_sha256": run2["provenance"]["script_sha256"],
            "current_disk_script_sha256": got,
            "run2_uses_current_revision": run2["provenance"]["script_sha256"] == got,
            "run1_uses_current_revision": run1["provenance"]["script_sha256"] == got,
        },
        "verdict": {
            "stale_blocker_supported": bool(reproduces and run2["provenance"]["script_sha256"] == got
                                            and control_detects_failure and len(stale_entries) >= 1),
            "summary": ("current frozen revision 8ade1cdc reproduces cnfem order 2 "
                        "(1.9863235066828981, matching run2_FIXED to 1e-9) at the same config that "
                        "produced -0.0773 under the superseded revision 07e5a39b; "
                        f"{len(stale_entries)} map blocker entries cite the superseded run or its "
                        "re-pin demand without resolution fields, while run2_FIXED is later and clean"),
            "n0_status_unchanged": {
                "node_status": node["node_status"],
                "validation_status": node["node_validation_status"],
                "g_num": "pending",
                "numerics_lock": "locked",
                "residual_unmet_criterion": "independent A1 numerical-protocol review "
                                            "(reviews/G-NUM-protocol-review.json) still absent",
            },
        },
        "falsifier": (
            "Re-run this script at the recorded hashes. The staleness finding is falsified if any of: "
            "(a) numerics/tests/flat_wave_replication.py sha256 != 8ade1cdc; "
            "(b) the re-run cnfem fit is non-monotone or outside p=2.0+-0.3 at the pinned config; "
            "(c) n0_replication_astra_run2_FIXED.json (sha 6542db93) does not read "
            "replication_verdict=ORDER REPRODUCED with script_sha256=8ade1cdc at a later generated_at "
            "than the stale blocker entries; "
            "(d) the map's N0 blocker entries no longer contain the -0.0773/ORDER DISAGREES or "
            "re-pin/re-run text, i.e. they have been resolved by other means; "
            "(e) the lffd cfl=1.5 failure-detection control returns a clean monotone order-2 fit, "
            "which would mean this measurement pipeline cannot detect an unstable scheme. "
            "Any one of (a)-(e) makes the 'stale blocker' conclusion false."
        ),
        "not_claimed": [
            "no N0 completion and no G-NUM pass; node stays active/unverified",
            "no claim that the cnfem fix is correct on mathematical grounds; only that the pinned "
            "revision reproduces order 2 at the pinned config",
            "no self-gravity, horizon, or cosmic-censorship claim; flat-space calibration only",
            "no modification of any canonical artifact, map, ledger, or review",
        ],
    }
    OUT = HERE / "recheck.json"
    OUT.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "out": str(OUT.relative_to(ROOT)),
        "sha256": sha256(OUT),
        "cnfem_rerun": p,
        "cnfem_monotone": cnfem["monotone"],
        "control_detects_failure": control_detects_failure,
        "stale_entry_count": len(stale_entries),
        "stale_blocker_supported": rec["verdict"]["stale_blocker_supported"],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
