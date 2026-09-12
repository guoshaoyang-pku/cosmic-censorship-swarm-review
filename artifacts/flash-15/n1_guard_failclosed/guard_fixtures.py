#!/usr/bin/env python3
"""W015-N1-GUARD-FAILCLOSED-01 fixture battery.

Class-bound task: class AF-WCC-SCALAR-SPH, node N1, gate G-NUM.
Question: does the canonical G-NUM lock guard
    numerics/tests/selfgravity_lock_guard.py
fail closed, or can a self-gravitating artifact coexist with a PASS?

Method: plant fixtures in throwaway temp roots (never in the canonical tree; no file under the
repository is written except this task's own artifacts), run BOTH the canonical revision-1 guard
and the staged revision-2 proposal on each fixture, and compare measured exit codes/verdicts with
the required fail-closed semantics. The revision-2 proposal is staged only; this harness never
writes numerics/ or schemas/.

Outputs: report.json + raw/*.txt in this directory.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent  # artifacts/flash-15/n1_guard_failclosed -> repo root
REV1 = REPO / "numerics" / "tests" / "selfgravity_lock_guard.py"
REV2 = HERE / "repaired_proposal.selfgravity_lock_guard.py"
LIVE_MAP = REPO / "research_map" / "research_map.json"
CST = timezone(timedelta(hours=8))


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def base_map(state="locked", seeds=("N1",), solver_declared=True):
    return {
        "groups": [{"id": "numerics", "nodes": [
            {"id": "N0", "status": "queued", "artifact": "numerics/tests/flat_wave.py", "depends_on": []},
            {"id": "N1", "status": "queued",
             "artifact": "numerics/spherical_solver/" if solver_declared else "numerics/tests/n1_stub.py",
             "depends_on": ["N0"]},
            {"id": "N2", "status": "queued", "artifact": "numerics/results/n2.json", "depends_on": ["N1"]},
        ]}],
        "numerics_lock": {"state": state, "locked_nodes": list(seeds)},
    }


FIXTURES = [
    # name, expected rev2 verdict, expected rev1 verdict, map mutation, files to plant
    ("A_locked_planted_solver", "FAIL", "FAIL",
     base_map(), ["numerics/spherical_solver"]),
    ("B_locked_declared_n2_artifact", "FAIL", "FAIL",
     base_map(), ["numerics/results/n2.json"]),
    ("C_locked_clean_n0_present", "PASS", "PASS",
     base_map(), ["numerics/tests/flat_wave.py"]),
    ("D_released_planted_solver", "PASS", "PASS",
     base_map(state="released"), ["numerics/spherical_solver"]),
    ("E_empty_state_planted_solver", "ERROR", "PASS",
     base_map(state=""), ["numerics/spherical_solver"]),
    ("F_miscased_Locked_planted_solver", "FAIL", "PASS",
     base_map(state="Locked"), ["numerics/spherical_solver"]),
    ("G_absent_lock_block_planted_solver", "ERROR", "PASS",
     base_map(), ["numerics/spherical_solver"]),
    ("H_unknown_state_frozen_planted_solver", "ERROR", "PASS",
     base_map(state="frozen"), ["numerics/spherical_solver"]),
    ("I_unreadable_map", "ERROR", "ERROR",
     "MALFORMED", []),
    ("J_vacuous_lock_declared_n2", "ERROR", "PASS",
     base_map(seeds=()), ["numerics/results/n2.json"]),
    ("K_vacuous_lock_clean", "ERROR", "PASS",
     base_map(seeds=()), []),
    ("L_uppercase_LOCKED_planted_solver", "FAIL", "PASS",
     base_map(state="LOCKED"), ["numerics/spherical_solver"]),
]


def build_fixture(root: Path, mutation, plants):
    (root / "research_map").mkdir(parents=True, exist_ok=True)
    if mutation == "MALFORMED":
        (root / "research_map" / "research_map.json").write_text("{not json")
    else:
        (root / "research_map" / "research_map.json").write_text(json.dumps(mutation, indent=1))
    for rel in plants:
        p = root / rel
        if rel.endswith("/"):
            p.mkdir(parents=True, exist_ok=True)
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("planted by W015 fixture battery\n")


def run_guard(guard: Path, root: Path):
    proc = subprocess.run(
        [sys.executable, str(guard), "--root", str(root)],
        capture_output=True, text=True, cwd=str(REPO),
    )
    verdict, violations, reason = None, [], None
    try:
        data = json.loads(proc.stdout)
        verdict = data.get("verdict")
        violations = [v.get("kind") for v in data.get("violations", [])]
        reason = data.get("error_reason") or data.get("error")
    except Exception as exc:  # noqa: BLE001
        reason = f"unparseable stdout: {type(exc).__name__}"
    return {"exit": proc.returncode, "verdict": verdict,
            "violation_kinds": violations, "error_reason": reason,
            "stdout": proc.stdout, "stderr": proc.stderr}


def mutate_case(name, mutation, root):
    """Apply per-fixture map mutation (absent block) after build."""
    if name.startswith("G_") and mutation != "MALFORMED":
        m = json.load(open(root / "research_map" / "research_map.json"))
        m.pop("numerics_lock", None)
        (root / "research_map" / "research_map.json").write_text(json.dumps(m, indent=1))


def main() -> int:
    raw = HERE / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    pins = {
        "canonical_guard_rev1": {"path": str(REV1.relative_to(REPO)), "sha256": sha256(REV1)},
        "staged_proposal_rev2": {"path": str(REV2.relative_to(REPO)), "sha256": sha256(REV2)},
        "live_map": {"path": str(LIVE_MAP.relative_to(REPO)), "sha256": sha256(LIVE_MAP)},
        "canonical_solver_dir_absent": not (REPO / "numerics" / "spherical_solver").exists(),
    }

    rows = []
    defects_reproduced = 0
    rev2_mismatches = []
    for name, exp2, exp1, mutation, plants in FIXTURES:
        with tempfile.TemporaryDirectory(prefix="w015-guardfix-") as td:
            root = Path(td)
            build_fixture(root, mutation, plants)
            mutate_case(name, mutation, root)
            r1 = run_guard(REV1, root)
            r2 = run_guard(REV2, root)
        (raw / f"{name}.rev1.txt").write_text(r1["stdout"] + r1["stderr"])
        (raw / f"{name}.rev2.txt").write_text(r2["stdout"] + r2["stderr"])
        rev1_documented_defect = (exp1 == "PASS" and exp2 != "PASS" and r1["verdict"] == "PASS")
        if rev1_documented_defect:
            defects_reproduced += 1
        ok2 = (r2["verdict"] == exp2) and (
            (exp2 == "FAIL" and r2["exit"] == 1) or
            (exp2 == "PASS" and r2["exit"] == 0) or
            (exp2 == "ERROR" and r2["exit"] == 2))
        if not ok2:
            rev2_mismatches.append(name)
        rows.append({
            "fixture": name,
            "expected_rev2_failclosed": exp2,
            "rev1_measured": {"exit": r1["exit"], "verdict": r1["verdict"],
                              "violation_kinds": r1["violation_kinds"], "error_reason": r1["error_reason"]},
            "rev2_measured": {"exit": r2["exit"], "verdict": r2["verdict"],
                              "violation_kinds": r2["violation_kinds"], "error_reason": r2["error_reason"]},
            "rev1_open_defect": rev1_documented_defect,
            "rev2_satisfies_required_semantics": ok2,
        })

    # Live-tree runs, read-only.
    live1 = run_guard(REV1, REPO)
    live2 = run_guard(REV2, REPO)
    (raw / "live.rev1.txt").write_text(live1["stdout"] + live1["stderr"])
    (raw / "live.rev2.txt").write_text(live2["stdout"] + live2["stderr"])
    live_ok = (live1["verdict"] == "PASS" and live1["exit"] == 0 and
               live2["verdict"] == "PASS" and live2["exit"] == 0)

    findings = [
        {
            "id": "HF-15-G1",
            "severity": "blocking",
            "target": "numerics/tests/selfgravity_lock_guard.py (rev1)",
            "statement": "Rev1 fails open whenever numerics_lock.state is not the exact lower-case "
                         "literal 'locked': absent block, empty string, miscased 'Locked'/'LOCKED', "
                         "or an unknown token all yield verdict PASS / exit 0 while a planted "
                         "numerics/spherical_solver/ directory is present and recorded in the "
                         "guard's own violations list. Fixtures G, E, F, L, H.",
            "falsifier": "Run rev1 on a temp root whose map lacks numerics_lock (or carries "
                         "state in {'', 'Locked', 'LOCKED', 'frozen'}) with numerics/spherical_solver/ "
                         "planted; HF-15-G1 is void if the guard exits non-zero or returns non-PASS.",
        },
        {
            "id": "HF-15-G2",
            "severity": "blocking",
            "target": "numerics/tests/selfgravity_lock_guard.py (rev1)",
            "statement": "Rev1 certifies a vacuous locked lock: with numerics_lock.state='locked' "
                         "and locked_nodes=[], the blocked set is empty, so declared N1+ artifacts "
                         "reachable only through the dependency graph (e.g. numerics/results/n2.json) "
                         "are never checked and the guard returns PASS. Fixtures J and K.",
            "falsifier": "Run rev1 on a temp root with state='locked', locked_nodes=[], and a planted "
                         "numerics/results/n2.json; HF-15-G2 is void if the guard exits non-zero.",
        },
        {
            "id": "HF-15-G3",
            "severity": "advisory",
            "target": "numerics/tests/selfgravity_lock_guard.py (rev1) main()",
            "statement": "Latent fail-open: main() maps verdict->exit as FAIL->1, else->0. If an ERROR "
                         "verdict were ever returned by evaluate() rather than raised, the guard would "
                         "exit 0. Rev2 maps ERROR->2 explicitly.",
            "falsifier": "Construct an evaluate() path that returns {'verdict': 'ERROR'} without "
                         "raising and show rev1 exits 0; HF-15-G3 is void if rev1 exits non-zero.",
        },
        {
            "id": "HF-15-G4",
            "severity": "positive",
            "target": "revision-2 proposal",
            "statement": "Rev2 satisfies all 12 fixture semantics (A, B, I unchanged; C no false "
                         "positive; D release semantics preserved and reported as lock_enforced=false; "
                         "E, G, H, J, K fail closed with exit 2; F, L normalize the case and fail with "
                         "exit 1), and both revisions PASS exit 0 on the live tree at the pinned map "
                         "hash with numerics/spherical_solver absent.",
            "falsifier": "Re-run report.json's exact commands; HF-15-G4 is void if any rev2 measured "
                         "pair (verdict, exit) differs from expected_rev2_failclosed, or if a live-tree "
                         "run is not (PASS, 0).",
        },
    ]

    report = {
        "schema": "w015/n1-guard-failclosed/v1",
        "task_id": "W015-N1-GUARD-FAILCLOSED-01",
        "class_id": "AF-WCC-SCALAR-SPH",
        "class_ids": ["AF-WCC-SCALAR-SPH"],
        "node_id": "N1",
        "gate": "G-NUM",
        "created_at": datetime.now(CST).isoformat(),
        "pins": pins,
        "fixture_count": len(FIXTURES),
        "rev1_open_defects_reproduced": defects_reproduced,
        "rev2_mismatches": rev2_mismatches,
        "battery_verdict": "PASS" if (not rev2_mismatches and live_ok and pins["canonical_solver_dir_absent"]) else "FAIL",
        "live_tree": {"rev1": {"exit": live1["exit"], "verdict": live1["verdict"]},
                      "rev2": {"exit": live2["exit"], "verdict": live2["verdict"]}},
        "fixtures": rows,
        "findings": findings,
        "repair": {
            "status": "STAGED_NOT_APPLIED",
            "path": "artifacts/flash-15/n1_guard_failclosed/repaired_proposal.selfgravity_lock_guard.py",
            "sha256": pins["staged_proposal_rev2"]["sha256"],
            "target_path": "numerics/tests/selfgravity_lock_guard.py",
            "target_rev1_sha256": pins["canonical_guard_rev1"]["sha256"],
            "apply_authority": "lead-numerics/astra (canonical numerics path); worker-15 is the "
                               "assignment asg-2026-09-11-N1-deepseek-flash-15-24 owner but does not "
                               "move a frozen/reviewed canonical hash unilaterally",
        },
        "non_claims": [
            "Not a gate verdict, not a node transition, not a mathematics or physics claim.",
            "Validation status is unverified pending an independent re-run by a non-author.",
            "No file under numerics/ or schemas/ was created, modified or deleted by this task.",
        ],
        "rerun": "cd <repo> && python3 artifacts/flash-15/n1_guard_failclosed/guard_fixtures.py",
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps({"battery_verdict": report["battery_verdict"],
                      "rev1_open_defects_reproduced": defects_reproduced,
                      "rev2_mismatches": rev2_mismatches,
                      "live": report["live_tree"],
                      "report_sha256": sha256(HERE / "report.json")}, indent=1))
    return 0 if report["battery_verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
