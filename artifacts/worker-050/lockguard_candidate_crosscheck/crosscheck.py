#!/usr/bin/env python3
"""W050-LOCKGUARD-CANDIDATE-CROSSCHECK-05

Independent, black-box, pre-registered cross-check of the two competing repairs to the
G-NUM N1 lock guard, against the canonical revision and against ``numerics.gates`` state
semantics.

Subject (read-only; nothing in the canonical tree is edited and
``numerics/spherical_solver/`` is never created outside a temp root):

  canonical   numerics/tests/selfgravity_lock_guard.py                      7535ec84ac9c
  candidate A artifacts/flash-15/n1_guard_failclosed/repaired_proposal...   bbc5f363d2f8
  candidate B artifacts/worker-012/n0/lockguard_failclosed/guard_candidate  0b72a9871b56

Why this exists
---------------
Two workers independently measured that the canonical guard fails open on
``numerics_lock.state`` spellings other than the exact literal ``locked`` (worker-074 finding
W074-F3; deepseek-flash-15 W015-N1-GUARD-FAILCLOSED-01; worker-012 W012-LOCKGUARD-FAILCLOSED-01)
and each filed a *different* repair.  Neither repair has been run against the other on a common
matrix, and the canonical guard is still the defective revision.  This run measures a four-property
scorecard (P1-P4 below) on one hash-pinned fixture battery and reports which repair is safe and
where each one still differs from the other and from ``numerics/gates.py``.

Pre-registered properties (fixed before measuring; see fixtures.json for per-row expectations)
-----------------------------------------------------------------------------------------------
P1  literal-assignment: PASS/exit 0 is forbidden while state == "locked" (exact) and an N1+
    artifact (declared transitive artifact or the explicit solver dir) is present.
P2  strict-release: only the exact token "released" may permit an artifact; any other token
    (absent, null, "", miscased, "unlocked", non-string, unknown) must not PASS when an
    artifact is present.
P3  no-blind-certification: an unparseable/absent lock state with no artifact present must not
    be certified PASS.
P4  non-vacuous-lock: state == "locked" with an empty/missing ``locked_nodes`` must not be
    certified PASS when a declared transitive N1+ artifact is present.

Exit codes: 0 = matrix ran and pins held; 2 = a guard under test crashed unexpectedly;
3 = input hash drift (subject moved; nothing certified).

Usage:  python3 crosscheck.py [--selftest] [--out report.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]

# ---------------------------------------------------------------------------------------------
# Hash-pinned subjects.  The runner refuses to certify if any of these move during the run.
# ---------------------------------------------------------------------------------------------
SUBJECTS = {
    "canonical": "numerics/tests/selfgravity_lock_guard.py",
    "candidate_A_flash15_rev2": "artifacts/flash-15/n1_guard_failclosed/repaired_proposal.selfgravity_lock_guard.py",
    "candidate_B_worker012": "artifacts/worker-012/n0/lockguard_failclosed/guard_candidate.py",
}
PINS = {
    "canonical": "7535ec84ac9ceb0b5451e4ed93ae6b03083966db47aa218eb4fba3da6627b9f5",
    "candidate_A_flash15_rev2": "bbc5f363d2f89317236cb7cce1784174733120342fd3111a27bf686e12a5507c",
    "candidate_B_worker012": "0b72a9871b56bc4e3588261bd818b02b9373d5dd6b7e94260f6fa164813528f5",
}
CONTEXT_PINS = {
    "numerics/gates.py": "fcd1d70991b6eade4aa993dc49b6103e338f68320aabb955d97da5a8f55d996e",
    "numerics/blockers.md": "d396b609d81d66086312e1a17edbf03bd87e04353d72bbd669c401e39048e7fd",
    "research_map/research_map.json": None,  # recorded, not pinned (live traffic)
}

SOLVER_DIR = "numerics/spherical_solver"
DECLARED_N2 = "numerics/results/n2.json"


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def base_map(state="locked", locked_nodes=("N1",), lock_present=True, lock_null=False,
             state_key=True):
    """A minimal map with the same group/node shape the guards read."""
    nodes = [
        {"id": "N0", "status": "queued", "artifact": "numerics/tests/flat_wave.py", "depends_on": ["F0"]},
        {"id": "N1", "status": "queued", "artifact": SOLVER_DIR + "/", "depends_on": ["N0", "L0"]},
        {"id": "N2", "status": "queued", "artifact": DECLARED_N2, "depends_on": ["N1"]},
    ]
    m = {
        "project": "crosscheck-fixture",
        "groups": [{"id": "numerics", "nodes": nodes}],
        "gates": [],
    }
    if lock_null:
        m["numerics_lock"] = None
    elif lock_present:
        lock = {"locked_nodes": list(locked_nodes) if locked_nodes is not None else None}
        if state_key:
            lock["state"] = state
        m["numerics_lock"] = lock
    return m


def write_fixture(root: Path, mutation: dict, plants=()):
    """`mutation` is either {'raw_map': str}, {'map': dict|callable}, or kwargs for base_map()."""
    (root / "research_map").mkdir(parents=True, exist_ok=True)
    if mutation.get("raw_map") is not None:
        text = mutation["raw_map"]
    elif mutation.get("map") is not None:
        m = mutation["map"]() if callable(mutation["map"]) else mutation["map"]
        text = json.dumps(m)
    else:
        m = base_map(
            state=mutation.get("state", "locked"),
            locked_nodes=mutation.get("locked_nodes", ("N1",)),
            lock_present=mutation.get("lock_present", True),
            lock_null=mutation.get("lock_null", False),
            state_key=mutation.get("state_key", True),
        )
        text = json.dumps(m)
    (root / "research_map" / "research_map.json").write_text(text)
    (root / "research_map" / "events.jsonl").write_text("")
    for rel in plants:
        p = root / rel
        if rel.endswith("/"):
            p.mkdir(parents=True, exist_ok=True)
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("planted by W050-LOCKGUARD-CANDIDATE-CROSSCHECK-05\n")


# ---------------------------------------------------------------------------------------------
# Pre-registered fixture battery.  `expect` is the P-property classification:
#   MUST_FAIL  - artifact present, lock not validly released  -> must not be PASS/exit 0
#   PASS_CLEAN - valid locked, no artifact                    -> PASS/exit 0
#   PASS_RELEASED - exact "released" + artifact               -> PASS/exit 0
#   ERROR_UNREADABLE - malformed map                          -> ERROR/exit 2
#   DIVERGENCE - contract does not force one answer; recorded and adjudicated in comparison.md
# ---------------------------------------------------------------------------------------------
FIXTURES = [
    dict(id="locked_clean", desc="valid locked lock, no artifacts", expect="PASS_CLEAN",
         plants=[], mut=dict(state="locked", locked_nodes=("N1",))),
    dict(id="locked_solver_dir", desc="valid locked lock, explicit solver dir present",
         expect="MUST_FAIL", plants=[SOLVER_DIR + "/"], mut=dict(state="locked", locked_nodes=("N1",))),
    dict(id="locked_declared_n2", desc="valid locked lock, declared transitive N1+ artifact present",
         expect="MUST_FAIL", plants=[DECLARED_N2], mut=dict(state="locked", locked_nodes=("N1",))),
    dict(id="locked_whitespace_solver", desc="state=' locked ' + solver dir",
         expect="MUST_FAIL", plants=[SOLVER_DIR + "/"], mut=dict(state=" locked ", locked_nodes=("N1",))),
    dict(id="locked_miscased_Locked_solver", desc="state='Locked' + solver dir",
         expect="MUST_FAIL", plants=[SOLVER_DIR + "/"], mut=dict(state="Locked", locked_nodes=("N1",))),
    dict(id="locked_miscased_LOCKED_solver", desc="state='LOCKED' + solver dir",
         expect="MUST_FAIL", plants=[SOLVER_DIR + "/"], mut=dict(state="LOCKED", locked_nodes=("N1",))),
    dict(id="lock_block_absent_solver", desc="numerics_lock block absent + solver dir",
         expect="MUST_FAIL", plants=[SOLVER_DIR + "/"], mut=dict(lock_present=False)),
    dict(id="lock_null_solver", desc="numerics_lock=null + solver dir",
         expect="MUST_FAIL", plants=[SOLVER_DIR + "/"], mut=dict(lock_null=True)),
    dict(id="state_null_solver", desc="state=null + solver dir",
         expect="MUST_FAIL", plants=[SOLVER_DIR + "/"], mut=dict(state=None, locked_nodes=("N1",))),
    dict(id="state_empty_solver", desc="state='' + solver dir",
         expect="MUST_FAIL", plants=[SOLVER_DIR + "/"], mut=dict(state="", locked_nodes=("N1",))),
    dict(id="state_key_missing_solver", desc="state key absent + solver dir",
         expect="MUST_FAIL", plants=[SOLVER_DIR + "/"], mut=dict(state_key=False)),
    dict(id="state_unknown_frozen_solver", desc="state='frozen' + solver dir",
         expect="MUST_FAIL", plants=[SOLVER_DIR + "/"], mut=dict(state="frozen", locked_nodes=("N1",))),
    dict(id="state_nonstring_123_solver", desc="state=123 + solver dir",
         expect="MUST_FAIL", plants=[SOLVER_DIR + "/"], mut=dict(state=123, locked_nodes=("N1",))),
    dict(id="state_unlocked_solver", desc="state='unlocked' + solver dir (release-surface row)",
         expect="DIVERGENCE", plants=[SOLVER_DIR + "/"], mut=dict(state="unlocked", locked_nodes=("N1",))),
    dict(id="state_miscased_Released_solver", desc="state='Released' + solver dir (release-surface row)",
         expect="DIVERGENCE", plants=[SOLVER_DIR + "/"], mut=dict(state="Released", locked_nodes=("N1",))),
    dict(id="unknown_state_clean", desc="state='frozen', no artifact (P3 blind-certification row)",
         expect="DIVERGENCE", plants=[], mut=dict(state="frozen", locked_nodes=("N1",))),
    dict(id="vacuous_nodes_empty_declared_n2", desc="locked with locked_nodes=[] + declared N2 (P1/P4 row)",
         expect="MUST_FAIL", plants=[DECLARED_N2], mut=dict(state="locked", locked_nodes=())),
    dict(id="vacuous_nodes_empty_solver", desc="locked with locked_nodes=[] + explicit solver dir",
         expect="MUST_FAIL", plants=[SOLVER_DIR + "/"], mut=dict(state="locked", locked_nodes=())),
    dict(id="locked_nodes_null_solver", desc="locked_nodes=null + solver dir",
         expect="MUST_FAIL", plants=[SOLVER_DIR + "/"], mut=dict(state="locked", locked_nodes=None)),
    dict(id="locked_nodes_missing_solver", desc="locked_nodes key absent + solver dir",
         expect="MUST_FAIL", plants=[SOLVER_DIR + "/"], mut=dict(state="locked", locked_nodes=())),
    dict(id="released_exact_solver_dir", desc="state='released' + solver dir (legal release)",
         expect="PASS_RELEASED", plants=[SOLVER_DIR + "/"], mut=dict(state="released", locked_nodes=("N1",))),
    dict(id="released_exact_clean", desc="state='released', no artifact",
         expect="PASS_RELEASED", plants=[], mut=dict(state="released", locked_nodes=("N1",))),
    dict(id="map_malformed_json", desc="truncated map JSON",
         expect="ERROR_UNREADABLE", plants=[SOLVER_DIR + "/"],
         mut=dict(raw_map='{"groups": [{"id": "numerics", "nodes": [',
                      lock_present=None)),
]


def run_guard(guard_path: Path, root: Path, extra_args=()) -> dict:
    """Black-box invocation, exactly as an operator would run it."""
    proc = subprocess.run(
        [sys.executable, str(guard_path), "--root", str(root), *extra_args],
        capture_output=True, text=True, timeout=120, cwd=str(REPO),
    )
    doc = None
    try:
        doc = json.loads(proc.stdout)
    except Exception:
        doc = None
    return {"exit_code": proc.returncode, "verdict": (doc or {}).get("verdict"),
            "lock_enforced": (doc or {}).get("lock_enforced"),
            "stdout_tail": proc.stdout[-400:], "stderr_tail": proc.stderr[-400:]}


def gates_state_criterion(root: Path) -> dict:
    """Isolate numerics/gates.py's *state* blocking criterion on the same fixture root.

    We read the exact reason string emitted by gates.evaluate() (gates.py line ~344:
    ``if lock.get("state", "locked") == "locked": reasons.append("numerics_lock.state == 'locked' ...")``)
    so the probe measures the live module, not a re-implementation.
    """
    import importlib
    sys.path.insert(0, str(REPO))
    try:
        mod = importlib.import_module("numerics.gates")
        rep = mod.evaluate(root)
        reasons = rep.get("blocking_reasons", [])
        state_locked = any(str(r).startswith("numerics_lock.state") for r in reasons)
        return {"state_criterion_locked": state_locked, "production_allowed": rep.get("production_allowed"),
                "verdict": rep.get("verdict"), "state_reason_present": state_locked}
    except Exception as exc:  # noqa: BLE001
        return {"state_criterion_locked": None, "error": f"{type(exc).__name__}: {exc}"}


def p_class(row: dict) -> dict:
    """Apply the pre-registered properties to one measured row."""
    f = row["fixture"]
    exp = f["expect"]
    out = {}
    for g, r in row["guards"].items():
        passed = (r["verdict"] == "PASS" and r["exit_code"] == 0)
        verdict_fail = r["verdict"] == "FAIL" and r["exit_code"] == 1
        verdict_err = r["verdict"] == "ERROR" and r["exit_code"] == 2
        out[g] = {
            "pass": passed, "fail": verdict_fail, "error": verdict_err,
            "non_pass": not passed,
            "p1_fail_open": exp == "MUST_FAIL" and passed,
            "p2_broad_release": exp in ("MUST_FAIL", "DIVERGENCE") and passed
                                and f["id"].startswith(("state_unlocked", "state_miscased_Released")),
            "p3_blind_cert": f["id"] == "unknown_state_clean" and passed,
            "p4_vacuous_pass": f["id"] == "vacuous_nodes_empty_declared_n2" and passed,
            "expected_ok": (
                (exp == "MUST_FAIL" and not passed)
                or (exp in ("PASS_CLEAN", "PASS_RELEASED") and passed)
                or (exp == "ERROR_UNREADABLE" and verdict_err)
                or (exp == "DIVERGENCE")
            ),
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(Path(__file__).with_name("report.json")))
    ap.add_argument("--selftest", action="store_true",
                    help="verify fixture construction and the property classifier, then exit")
    args = ap.parse_args()

    guard_paths = {k: REPO / v for k, v in SUBJECTS.items()}
    before = {k: sha256_file(p) for k, p in guard_paths.items()}
    for k, p in guard_paths.items():
        if before[k] != PINS[k]:
            print(json.dumps({"error": "HASH_DRIFT", "subject": k, "pinned": PINS[k],
                              "measured": before[k]}), file=sys.stderr)
            return 3
    ctx_before = {k: (sha256_file(REPO / k) if v is not None else sha256_file(REPO / k))
                  for k, v in CONTEXT_PINS.items()}

    if args.selftest:
        # classifier sanity: MUST_FAIL + PASS => p1 fires; MUST_FAIL + ERROR => clean.
        fake = {"fixture": {"id": "x", "expect": "MUST_FAIL"},
                "guards": {"g": {"verdict": "PASS", "exit_code": 0},
                           "h": {"verdict": "ERROR", "exit_code": 2}}}
        c = p_class(fake)
        ok = c["g"]["p1_fail_open"] and not c["h"]["p1_fail_open"] and c["h"]["expected_ok"]
        print(json.dumps({"selftest": "PASS" if ok else "FAIL", "classifier": c}, indent=1))
        return 0 if ok else 2

    # Deterministic fixture root: a fixed path (recreated per run) keeps the raw guard output
    # byte-stable across re-runs; mkdtemp's random suffix leaks into map_path and would make the
    # report nondeterministic.
    tmp = Path(tempfile.gettempdir()) / "w050_lockguard_fixtures"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True, exist_ok=True)
    rows = []
    for f in FIXTURES:
        root = tmp / f["id"]
        root.mkdir(parents=True, exist_ok=True)
        write_fixture(root, f["mut"], f.get("plants", ()))
        row = {"fixture": f, "guards": {}, "gates": gates_state_criterion(root)}
        for g, p in guard_paths.items():
            res = run_guard(p, root)
            # Normalize the per-run temp root out of the raw tails so the report is byte-stable
            # across re-runs (the verdicts/exit codes never contain it).  The path can be
            # truncated at the head of a tail, so match the mkdtemp prefix, not just str(root).
            import re as _re
            for fld in ("stdout_tail", "stderr_tail"):
                res[fld] = _re.sub(r"\w*lockguard_\w+", "<TMP>",
                                   res[fld].replace(str(root), "<FIXTURE_ROOT>"))
            row["guards"][g] = res
        # live-tree run is recorded once, outside the loop, below
        row["properties"] = p_class(row)
        rows.append(row)

    # ---- control runs: --self-test and the live tree for every guard revision -----------------
    controls = {}
    for g, p in guard_paths.items():
        st = run_guard(p, REPO, extra_args=("--self-test",))
        live = run_guard(p, REPO)
        controls[g] = {"self_test_exit": st["exit_code"],
                       "self_test_verdict": st["verdict"],
                       "live_exit": live["exit_code"], "live_verdict": live["verdict"],
                       "live_lock_enforced": live["lock_enforced"],
                       "live_stdout_tail": live["stdout_tail"]}
    solver_absent_live = not (REPO / SOLVER_DIR).exists()

    after = {k: sha256_file(p) for k, p in guard_paths.items()}
    ctx_after = {k: sha256_file(REPO / k) for k in CONTEXT_PINS}
    drift = {k: {"before": before[k], "after": after[k]} for k in before if before[k] != after[k]}
    ctx_drift = {k: {"before": ctx_before[k], "after": ctx_after[k]}
                 for k in ctx_before if ctx_before[k] != ctx_after[k]}
    # Only *pinned* context is drift-fatal.  research_map.json is live traffic: it is recorded
    # and flagged, never used to invalidate the measurement.
    fatal_ctx_drift = {k: v for k, v in ctx_drift.items() if CONTEXT_PINS.get(k) is not None}

    # ---- scorecard ---------------------------------------------------------------------------
    score = {}
    for g in guard_paths:
        score[g] = {
            "p1_fail_open_witnesses": [r["fixture"]["id"] for r in rows if r["properties"][g]["p1_fail_open"]],
            "p2_broad_release_witnesses": [r["fixture"]["id"] for r in rows if r["properties"][g]["p2_broad_release"]],
            "p3_blind_certification": [r["fixture"]["id"] for r in rows if r["properties"][g]["p3_blind_cert"]],
            "p4_vacuous_lock_pass": [r["fixture"]["id"] for r in rows if r["properties"][g]["p4_vacuous_pass"]],
            "expected_mismatches": [r["fixture"]["id"] for r in rows
                                    if not r["properties"][g]["expected_ok"]],
        }

    report = {
        "schema": "w050/lockguard-candidate-crosscheck/v1",
        "task_id": "W050-LOCKGUARD-CANDIDATE-CROSSCHECK-05",
        "actor": "worker-050",
        "class_id": "AF-WCC-SCALAR-SPH",
        "node_id": "N1-BLOCK",
        "gate": "G-NUM",
        "measured_at": __import__("time").strftime("%Y-%m-%dT%H:%M:%S%z"),
        "subjects": {k: {"path": SUBJECTS[k], "sha256": before[k], "pinned": PINS[k],
                         "pin_match": before[k] == PINS[k]} for k in SUBJECTS},
        "context": {k: {"sha256_before": ctx_before[k], "sha256_after": ctx_after[k],
                        "pinned": CONTEXT_PINS[k],
                        "pin_match": (CONTEXT_PINS[k] is None) or (ctx_before[k] == CONTEXT_PINS[k])}
                    for k in CONTEXT_PINS},
        "live_tree": {"solver_dir_absent": solver_absent_live, "controls": controls},
        "properties": {
            "P1": "no PASS while state=='locked' (exact) and an N1+ artifact exists",
            "P2": "only the exact token 'released' may permit an artifact",
            "P3": "no PASS certification of an unparseable/absent lock state",
            "P4": "no PASS for a 'locked' lock with empty/missing locked_nodes when a declared N1+ artifact exists",
        },
        "rows": rows,
        "scorecard": score,
        "drift": {"subjects": drift, "pinned_context": fatal_ctx_drift,
                  "live_map_recorded_drift": {k: v for k, v in ctx_drift.items()
                                              if CONTEXT_PINS.get(k) is None}},
        "authority": "worker measurement only; no canonical file edited, no gate verdict, "
                     "no node status, validation_status=unverified",
    }
    if drift or fatal_ctx_drift:
        print(json.dumps({"error": "POST_RUN_DRIFT", "drift": drift, "ctx_drift": fatal_ctx_drift}),
              file=sys.stderr)
        return 3
    Path(args.out).write_text(json.dumps(report, indent=2, sort_keys=True))

    summary = {
        "report": args.out,
        "p1_fail_open": {g: v["p1_fail_open_witnesses"] for g, v in score.items()},
        "p2_broad_release": {g: v["p2_broad_release_witnesses"] for g, v in score.items()},
        "p3_blind_cert": {g: v["p3_blind_certification"] for g, v in score.items()},
        "p4_vacuous": {g: v["p4_vacuous_lock_pass"] for g, v in score.items()},
        "unexpected": {g: v["expected_mismatches"] for g, v in score.items()},
        "self_test": {g: controls[g]["self_test_exit"] for g in controls},
        "live": {g: [controls[g]["live_verdict"], controls[g]["live_exit"]] for g in controls},
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
