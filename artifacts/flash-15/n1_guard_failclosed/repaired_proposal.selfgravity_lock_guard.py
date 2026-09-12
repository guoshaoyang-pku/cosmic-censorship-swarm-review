#!/usr/bin/env python3
"""G-NUM lock guard: fail if self-gravitating (N1+) numerics exist while numerics_lock is locked.

Assignment: asg-2026-09-11-N1-deepseek-flash-15-24 (astra, gate G-NUM).
Acceptance (verbatim): "Test fails if numerics/spherical_solver/ exists or if any N1+ artifact
is present while numerics_lock.state==locked; reads the map file."

REVISION 2 PROPOSAL -- STAGED, NOT APPLIED. Owner: deepseek-flash-15 (assignment asg-...-24).
Target of this revision: canonical `numerics/tests/selfgravity_lock_guard.py`
sha256 7535ec84ac9ceb0b5451e4ed93ae6b03083966db47aa218eb4fba3da6627b9f5 (revision 1).
Measured defect (confirmed independently at the revision-1 bytes by W015-N1-GUARD-FAILCLOSED-01,
and previously reported as W074-F3 by worker-074):
    revision 1 returns `verdict: PASS` / exit 0 whenever `numerics_lock.state` is anything other
    than the exact lower-case literal "locked" -- including a missing `numerics_lock` block,
    `state: ""`, `state: "Locked"` and unknown tokens. With a planted `numerics/spherical_solver/`
    directory, revision 1 therefore PASSes while carrying the violation in its own `violations`
    list. A lock guard that fails open on state spelling is not a guard.

Revision-2 semantics (fail-closed):
    * state == "locked"          -> violations decide FAIL/PASS (unchanged). Case/whitespace
      variants of a known token are normalized first, so "Locked"/" LOCKED " are still enforced.
    * state in {"released","unlocked"} -> PASS, but reported as `lock_enforced: false` with an
      explicit note; presence of a solver is legal only because the controller released the lock.
    * anything else (absent block, empty/whitespace, unknown token) -> ERROR, exit 2. The guard
      refuses to certify a lock it cannot parse.
    * state == "locked" but `locked_nodes` empty -> ERROR, exit 2 (a locked lock that blocks no
      node is vacuous and would silently skip declared N1+ artifacts).
    * an unreadable map -> ERROR, exit 2 (unchanged from revision 1).
Exit codes: 0 = lock intact / released, 1 = VIOLATION, 2 = cannot evaluate (fail-closed).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_MAP = "research_map/research_map.json"
EXPLICIT_FORBIDDEN = ["numerics/spherical_solver"]
LOCKED_STATES = {"locked"}
RELEASED_STATES = {"released", "unlocked"}


def load_map(root: Path, map_rel: str):
    p = root / map_rel
    return json.loads(p.read_text()), p


def direct_dependents(nodes: dict, seeds: set) -> set:
    """All node ids that depend (transitively) on any seed node."""
    blocked = set(seeds)
    changed = True
    while changed:
        changed = False
        for nid, node in nodes.items():
            if nid in blocked:
                continue
            if any(d in blocked for d in node.get("depends_on", [])):
                blocked.add(nid)
                changed = True
    return blocked


def declared_artifacts(node: dict) -> list:
    a = node.get("artifact")
    if a is None:
        return []
    if isinstance(a, str):
        return [a]
    if isinstance(a, (list, tuple)):
        return [x for x in a if isinstance(x, str)]
    return []


def error_report(mpath: Path, reason: str, extra: dict | None = None) -> dict:
    import hashlib
    report = {
        "guard": "selfgravity_lock_guard",
        "guard_revision": 2,
        "map_path": str(mpath),
        "map_sha256": hashlib.sha256(mpath.read_bytes()).hexdigest(),
        "error_reason": reason,
        "violations": [],
        "verdict": "ERROR",
        "note": "ERROR (fail-closed) means the lock state could not be interpreted; the guard "
                "refuses to certify anything until the map is repaired.",
    }
    if extra:
        report.update(extra)
    return report


def evaluate(root: Path, map_rel: str) -> dict:
    m, mpath = load_map(root, map_rel)
    nodes = {}
    for g in m.get("groups", []):
        for n in g.get("nodes", []):
            nodes[n["id"]] = n

    lock = m.get("numerics_lock")
    if not isinstance(lock, dict) or not lock:
        return error_report(mpath, "missing_or_invalid_numerics_lock_block")

    state = lock.get("state")
    state_norm = str(state).strip().lower() if state is not None else ""
    seeds = set(lock.get("locked_nodes") or [])

    blocked = direct_dependents(nodes, seeds)
    declared = []
    for nid in sorted(blocked):
        for art in declared_artifacts(nodes.get(nid, {})):
            declared.append({"node_id": nid, "path": art, "exists": (root / art).exists()})

    explicit = [{"path": p, "exists": (root / p).exists()} for p in EXPLICIT_FORBIDDEN]

    violations = []
    for d in declared:
        if d["exists"]:
            violations.append({"kind": "declared_n1plus_artifact_present", **d})
    for e in explicit:
        if e["exists"]:
            violations.append({"kind": "explicit_forbidden_path_present", **e})

    if state_norm not in LOCKED_STATES | RELEASED_STATES:
        return error_report(
            mpath, f"unrecognized_numerics_lock_state:{state!r}",
            {"numerics_lock_state_raw": state, "violations": violations},
        )
    if state_norm in LOCKED_STATES and not seeds:
        return error_report(
            mpath, "vacuous_locked_lock:locked_nodes_empty",
            {"numerics_lock_state_raw": state, "violations": violations},
        )

    enforced = state_norm in LOCKED_STATES
    return {
        "guard": "selfgravity_lock_guard",
        "guard_revision": 2,
        "map_path": str(mpath),
        "map_sha256": __import__("hashlib").sha256(mpath.read_bytes()).hexdigest(),
        "numerics_lock_state": lock.get("state"),
        "lock_enforced": enforced,
        "locked_seeds": sorted(seeds),
        "blocked_nodes": sorted(blocked),
        "declared_artifacts_checked": declared,
        "explicit_forbidden_checked": explicit,
        "violations": violations,
        "verdict": "FAIL" if (enforced and violations) else "PASS",
        "note": "PASS means no evidence of N1+ self-gravity artifacts while locked; it is not a "
                "proof of absence." if enforced else
                "PASS because numerics_lock is RELEASED: solver artifacts are legal in this state.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=".", help="workspace root (default: cwd)")
    ap.add_argument("--map", default=DEFAULT_MAP, help="map path relative to --root")
    ap.add_argument("--self-test", action="store_true", help="run planted-violation fixture in a temp dir")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    try:
        report = evaluate(Path(args.root), args.map)
    except Exception as exc:  # noqa: BLE001 - guard must report, not crash silently
        print(json.dumps({"guard": "selfgravity_lock_guard", "verdict": "ERROR",
                          "error": f"{type(exc).__name__}: {exc}"}, indent=2))
        return 2
    print(json.dumps(report, indent=2))
    if report["verdict"] == "FAIL":
        return 1
    if report["verdict"] == "ERROR":
        return 2
    return 0


def self_test() -> int:
    """Falsifier demonstration: clean fixture PASSes, planted solver FAILs, unknown state ERRORs."""
    import tempfile

    fake_map = {
        "groups": [{"id": "numerics", "nodes": [
            {"id": "N0", "status": "queued", "artifact": "numerics/tests/flat_wave.py", "depends_on": []},
            {"id": "N1", "status": "queued", "artifact": "numerics/spherical_solver/", "depends_on": ["N0"]},
            {"id": "N2", "status": "queued", "artifact": "numerics/results/n2.json", "depends_on": ["N1"]},
        ]}],
        "numerics_lock": {"state": "locked", "locked_nodes": ["N1"]},
    }
    results = []

    def run(fixture: str, expected: str, mutate=None) -> dict:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "research_map").mkdir(parents=True)
            m = json.loads(json.dumps(fake_map))
            if mutate:
                mutate(m, root)
            (root / "research_map" / "research_map.json").write_text(json.dumps(m))
            r = evaluate(root, DEFAULT_MAP)
            row = {"fixture": fixture, "expected": expected, "got": r["verdict"]}
            if r["verdict"] == "ERROR":
                row["reason"] = r.get("error_reason")
            results.append(row)
            return r

    run("clean", "PASS")
    run("planted_solver_dir", "FAIL", lambda m, r: (r / "numerics" / "spherical_solver").mkdir(parents=True))
    run("miscased_state_Locked_normalized_and_enforced", "FAIL",
        lambda m, r: (m["numerics_lock"].update(state="Locked"),
                      (r / "numerics" / "spherical_solver").mkdir(parents=True)))
    run("unknown_state_frozen", "ERROR",
        lambda m, r: (m["numerics_lock"].update(state="frozen"),
                      (r / "numerics" / "spherical_solver").mkdir(parents=True)))
    run("state_released", "PASS", lambda m, r: (m["numerics_lock"].update(state="released"),
                                                (r / "numerics" / "spherical_solver").mkdir(parents=True)))
    ok = all(row["expected"] == row["got"] for row in results)
    print(json.dumps({"self_test": "PASS" if ok else "FAIL", "results": results}, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
