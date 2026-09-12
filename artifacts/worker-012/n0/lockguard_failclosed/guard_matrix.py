#!/usr/bin/env python3
"""W012-LOCKGUARD-FAILCLOSED-01 -- read-only adversarial matrix for the canonical N1 lock guard.

Subject
-------
numerics/tests/selfgravity_lock_guard.py
  sha256 7535ec84ac9ceb0b5451e4ed93ae6b03083966db47aa218eb4fba3da6627b9f5

Task
----
Independently reproduce and adjudicate the unreplicated major finding W074-F3
(artifacts/worker-074/n1_block_audit/report.json, finding id W074-F3): the guard returns
``verdict=PASS`` / exit 0 while a planted ``numerics/spherical_solver/`` exists, whenever
``numerics_lock.state`` is missing or not exactly ``locked``.  Then measure a byte-minimal
repair candidate (guard_candidate.py) on the same matrix.

Contract under test (from the guard's own docstring and numerics/blockers.md "must fail closed")
----------------------------------------------------------------------------------------------
  * exit 0 / PASS  : lock intact -- only legitimate when no blocked-node artifact exists, OR the
                     lock state is the exact string ``released`` (release authority: astra);
  * exit 1 / FAIL  : blocked-node artifact exists while the lock is not released;
  * exit 2 / ERROR : cannot evaluate (map unreadable) -- must never silently pass.

Safety
------
Read-only with respect to the repository: the harness copies the guard bytes into temp fixture
roots and always runs with ``--root <tempdir>`` (plus one read-only run against the live repo
map).  It never writes under ``numerics/`` and never creates ``numerics/spherical_solver/`` in
the repository.  Canonical file hashes are measured before and after and must be identical.

Run: python3 guard_matrix.py
Exit 0 iff every contract row holds for the candidate, the canonical defect reproduces, the
worker-074 recorded fixtures agree, both self-tests pass, and no canonical byte changed.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
DEFAULT_MAP = "research_map/research_map.json"

CANONICAL = REPO / "numerics" / "tests" / "selfgravity_lock_guard.py"
CANDIDATE = HERE / "guard_candidate.py"
GATES = REPO / "numerics" / "gates.py"
BLOCKERS = REPO / "numerics" / "blockers.md"
LIVE_MAP = REPO / DEFAULT_MAP
W074_REPORT = REPO / "artifacts" / "worker-074" / "n1_block_audit" / "report.json"

PINNED_CANONICAL_SHA256 = (
    "7535ec84ac9ceb0b5451e4ed93ae6b03083966db47aa218eb4fba3da6627b9f5"
)

# state naming: (label, state_key_present, state_value)
STATES = [
    ("locked", True, "locked"),
    ("missing_key", False, None),
    ("LOCKED_upper", True, "LOCKED"),
    ("Locked_title", True, "Locked"),
    ("locked_leading_space", True, " locked"),
    ("empty_string", True, ""),
    ("json_null", True, None),
    ("integer", True, 123),
    ("unknown_word", True, "unknown"),
    ("unlocked_word", True, "unlocked"),
    ("released", True, "released"),
]

W074_EXPECTED = {
    "FX-A_state_key_missing": {"exit_code": 0, "verdict": "PASS"},
    "FX-B_state_case_LOCKED": {"exit_code": 0, "verdict": "PASS"},
    "FX-C_control_state_locked": {"exit_code": 1, "verdict": "FAIL"},
    "FX-D_control_clean_locked": {"exit_code": 0, "verdict": "PASS"},
    "FX-E_map_unreadable": {"exit_code": 2, "verdict": "ERROR"},
}


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def fixture_map(state_present: bool, state_value) -> dict:
    lock = {
        "locked_nodes": ["N1"],
        "allowed_nodes": ["N0"],
        "required_gates": ["G-FORM", "G-AUDIT"],
    }
    if state_present:
        lock["state"] = state_value
    return {
        "groups": [
            {
                "id": "numerics",
                "nodes": [
                    {"id": "N0", "artifact": "numerics/tests/flat_wave.py", "depends_on": []},
                    {"id": "N1", "artifact": "numerics/spherical_solver/", "depends_on": ["N0"]},
                ],
            }
        ],
        "numerics_lock": lock,
    }


def build_fixture(root: Path, state_present: bool, state_value, planted: bool) -> Path:
    (root / "research_map").mkdir(parents=True, exist_ok=True)
    (root / DEFAULT_MAP).write_text(json.dumps(fixture_map(state_present, state_value)))
    if planted:
        (root / "numerics" / "spherical_solver").mkdir(parents=True, exist_ok=True)
    return root


def build_no_lock_fixture(root: Path, as_null: bool, planted: bool) -> Path:
    """Map with the whole numerics_lock object absent (or explicitly null)."""
    m = fixture_map(True, "locked")
    if as_null:
        m["numerics_lock"] = None
    else:
        del m["numerics_lock"]
    (root / "research_map").mkdir(parents=True, exist_ok=True)
    (root / DEFAULT_MAP).write_text(json.dumps(m))
    if planted:
        (root / "numerics" / "spherical_solver").mkdir(parents=True, exist_ok=True)
    return root


def run_guard(guard_src: Path, root: Path, map_rel: str = DEFAULT_MAP) -> dict:
    """Copy guard bytes to a temp path and execute against root. Returns measurement dict."""
    with tempfile.TemporaryDirectory(prefix="w012_guard_run_") as td:
        gcopy = Path(td) / "guard_under_test.py"
        shutil.copyfile(guard_src, gcopy)
        gsha = sha256_file(gcopy)
        proc = subprocess.run(
            [sys.executable, str(gcopy), "--root", str(root), "--map", map_rel],
            capture_output=True,
            text=True,
            timeout=90,
            cwd=td,
        )
    verdict = None
    parsed = None
    try:
        parsed = json.loads(proc.stdout)
        verdict = parsed.get("verdict")
    except Exception:
        pass
    if verdict is None:
        verdict = {0: "PASS", 1: "FAIL"}.get(proc.returncode, "ERROR")
    return {
        "guard_sha256": gsha,
        "exit_code": proc.returncode,
        "verdict": verdict,
        "violations": (parsed or {}).get("violations", []),
        "numerics_lock_state": (parsed or {}).get("numerics_lock_state"),
        "numerics_lock_state_raw": (parsed or {}).get("numerics_lock_state_raw"),
        "state_key_present": (parsed or {}).get("state_key_present"),
        "state_recognised": (parsed or {}).get("state_recognised"),
        "stdout": proc.stdout.strip()[:4000],
        "stderr": proc.stderr.strip()[:1000],
        "parse_ok": parsed is not None,
    }


def run_self_test(guard_src: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix="w012_guard_st_") as td:
        gcopy = Path(td) / "guard_under_test.py"
        shutil.copyfile(guard_src, gcopy)
        proc = subprocess.run(
            [sys.executable, str(gcopy), "--self-test"],
            capture_output=True, text=True, timeout=90, cwd=td,
        )
    return {"exit_code": proc.returncode, "stdout": proc.stdout.strip()[:2000]}


def contract_expected(planted: bool, state_value, state_present: bool) -> str:
    if not planted:
        return "PASS"
    if state_present and state_value == "released":
        return "PASS"
    return "FAIL"


def main() -> int:
    if not CANONICAL.exists() or not CANDIDATE.exists():
        print("REFUSE: guard files missing")
        return 2
    canon_sha = sha256_file(CANONICAL)
    if canon_sha != PINNED_CANONICAL_SHA256:
        print(f"REFUSE: canonical guard sha256 {canon_sha} != pinned {PINNED_CANONICAL_SHA256}")
        return 2
    cand_sha = sha256_file(CANDIDATE)

    before = {
        "selfgravity_lock_guard.py": canon_sha,
        "gates.py": sha256_file(GATES),
        "blockers.md": sha256_file(BLOCKERS),
        "research_map.json": sha256_file(LIVE_MAP),
    }

    rows = []

    # --- live repo map (read-only) -------------------------------------------------------
    live = {}
    for label, src in (("canonical", CANONICAL), ("candidate", CANDIDATE)):
        live[label] = run_guard(src, REPO)
    rows.append({
        "id": "LIVE_repo_map",
        "fixture": "live repository map (state=locked, spherical_solver absent)",
        "planted": False,
        "expected": "PASS",
        "canonical": live["canonical"],
        "candidate": live["candidate"],
    })

    # --- unreadable map ------------------------------------------------------------------
    with tempfile.TemporaryDirectory(prefix="w012_nomap_") as td:
        empty_root = Path(td)
        rows.append({
            "id": "FX-E_map_unreadable",
            "fixture": "root without research_map/research_map.json",
            "planted": True,
            "expected": "ERROR(exit 2)",
            "canonical": run_guard(CANONICAL, empty_root),
            "candidate": run_guard(CANDIDATE, empty_root),
        })

    # --- state x planted matrix ----------------------------------------------------------
    for label, present, value in STATES:
        for planted in (True, False):
            with tempfile.TemporaryDirectory(prefix="w012_fx_") as td:
                root = build_fixture(Path(td), present, value, planted)
                rows.append({
                    "id": f"state={label}/planted={planted}",
                    "fixture": f"state={value!r} present={present} planted_solver={planted}",
                    "planted": planted,
                    "expected": contract_expected(planted, value, present),
                    "canonical": run_guard(CANONICAL, root),
                    "candidate": run_guard(CANDIDATE, root),
                })

    # --- whole lock object absent / null -------------------------------------------------
    for label, as_null in (("lock_object_absent", False), ("lock_object_null", True)):
        for planted in (True, False):
            with tempfile.TemporaryDirectory(prefix="w012_nolock_") as td:
                root = build_no_lock_fixture(Path(td), as_null, planted)
                rows.append({
                    "id": f"{label}/planted={planted}",
                    "fixture": f"numerics_lock={'null' if as_null else 'absent'} planted_solver={planted}",
                    "planted": planted,
                    "expected": contract_expected(planted, "locked", True),
                    "canonical": run_guard(CANONICAL, root),
                    "candidate": run_guard(CANDIDATE, root),
                })

    # --- worker-074 recorded fixture replication -----------------------------------------
    by_id = {}
    for r in rows:
        key = r["id"]
        if key == "state=missing_key/planted=True":
            by_id["FX-A_state_key_missing"] = r
        elif key == "state=LOCKED_upper/planted=True":
            by_id["FX-B_state_case_LOCKED"] = r
        elif key == "state=locked/planted=True":
            by_id["FX-C_control_state_locked"] = r
        elif key == "state=locked/planted=False":
            by_id["FX-D_control_clean_locked"] = r
        elif key == "FX-E_map_unreadable":
            by_id["FX-E_map_unreadable"] = r
    w074_replication = {}
    for fid, exp in W074_EXPECTED.items():
        row = by_id.get(fid)
        got = {
            "exit_code": row["canonical"]["exit_code"],
            "verdict": row["canonical"]["verdict"],
        }
        w074_replication[fid] = {
            "worker_074_recorded": exp,
            "w012_reproduced": got,
            "agrees": got["exit_code"] == exp["exit_code"] and got["verdict"] == exp["verdict"],
        }

    # --- candidate contract conformance --------------------------------------------------
    contract_failures = []
    defect_rows = []
    for r in rows:
        c = r["candidate"]
        exp = r["expected"]
        ok = (c["verdict"] == exp) or (exp.startswith("ERROR") and c["verdict"] == "ERROR")
        if not ok:
            contract_failures.append({"row": r["id"], "expected": exp, "candidate": c["verdict"]})
        if r["planted"] is True and r["id"] != "FX-E_map_unreadable":
            if r["canonical"]["verdict"] == "PASS" and r["expected"] == "FAIL":
                defect_rows.append(r["id"])

    self_tests = {
        "canonical": run_self_test(CANONICAL),
        "candidate": run_self_test(CANDIDATE),
    }

    after = {
        "selfgravity_lock_guard.py": sha256_file(CANONICAL),
        "gates.py": sha256_file(GATES),
        "blockers.md": sha256_file(BLOCKERS),
        "research_map.json": sha256_file(LIVE_MAP),
    }
    unchanged = before == after

    report = {
        "task_id": "W012-LOCKGUARD-FAILCLOSED-01",
        "class_id": "AF-WCC-SCALAR-SPH",
        "node_id": "N1-BLOCK",
        "gate": "G-NUM",
        "generated_at": __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds"),
        "subject": {
            "path": "numerics/tests/selfgravity_lock_guard.py",
            "canonical_sha256": canon_sha,
            "candidate_path": "artifacts/worker-012/n0/lockguard_failclosed/guard_candidate.py",
            "candidate_sha256": cand_sha,
        },
        "context_hashes": {
            "numerics/gates.py": before["gates.py"],
            "numerics/blockers.md": before["blockers.md"],
            "research_map/research_map.json": before["research_map.json"],
        },
        "contract": "PASS = no blocked-node artifact, or state exactly 'released'; FAIL = artifact while not released; ERROR(exit 2) = map unreadable",
        "verdict": "PASS" if (not contract_failures and unchanged) else "FAIL",
        "worker_074_finding": "W074-F3: guard fails OPEN (PASS/exit 0) with a planted solver when numerics_lock.state is missing or miscased",
        "worker_074_replication": w074_replication,
        "canonical_defect_witnesses": defect_rows,
        "candidate_contract_failures": contract_failures,
        "canonical_self_test": self_tests["canonical"],
        "candidate_self_test": self_tests["candidate"],
        "canonical_hashes_unchanged": unchanged,
        "rows": rows,
        "falsifier": (
            "REJECT W012-LOCKGUARD-FAILCLOSED-01 if any of: (a) the canonical guard at sha256 "
            "7535ec84ac9c fails to reproduce worker-074's five recorded fixtures (state missing / "
            "'LOCKED' with a planted solver -> PASS exit 0); (b) the candidate guard_candidate.py "
            "at its recorded sha256 does not return FAIL/exit 1 for every planted-solver fixture "
            "whose state is not exactly 'released'; (c) the candidate returns PASS for a planted "
            "solver with state 'released' absent an authoritative release; (d) the candidate "
            "breaks the canonical --self-test or fails the clean-map rows; (e) any canonical byte "
            "hash changed across this run; (f) a repaired canonical guard whose state handling "
            "matches the candidate lands and the defect witnesses above no longer reproduce."
        ),
        "authority_note": (
            "Worker-authored evidence and a repair candidate only. The canonical file is NOT "
            "edited; repair authority is lead-numerics (numerics/blockers.md owner). No gate "
            "verdict, no node completion, no validation_status=passed is claimed."
        ),
    }

    out = HERE / "matrix.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True))
    (HERE / "raw" / "matrix_stdout_canonical_live.txt").write_text(live["canonical"]["stdout"])
    (HERE / "raw" / "matrix_stdout_candidate_live.txt").write_text(live["candidate"]["stdout"])

    summary = {
        "verdict": report["verdict"],
        "canonical_sha256": canon_sha,
        "candidate_sha256": cand_sha,
        "rows": len(rows),
        "canonical_defect_witnesses": defect_rows,
        "candidate_contract_failures": contract_failures,
        "w074_agrees": all(v["agrees"] for v in w074_replication.values()),
        "canonical_self_test_exit": self_tests["canonical"]["exit_code"],
        "candidate_self_test_exit": self_tests["candidate"]["exit_code"],
        "canonical_hashes_unchanged": unchanged,
        "matrix_json": str(out.relative_to(REPO)),
        "matrix_json_sha256": sha256_file(out),
    }
    print(json.dumps(summary, indent=2))
    ok = (
        report["verdict"] == "PASS"
        and summary["w074_agrees"]
        and self_tests["canonical"]["exit_code"] == 0
        and self_tests["candidate"]["exit_code"] == 0
        and unchanged
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
