#!/usr/bin/env python3
"""G-NUM lock guard: fail if self-gravitating (N1+) numerics exist while numerics_lock is locked.

Assignment: asg-2026-09-11-N1-deepseek-flash-15-24 (astra, gate G-NUM).
Acceptance (verbatim): "Test fails if numerics/spherical_solver/ exists or if any N1+ artifact
is present while numerics_lock.state==locked; reads the map file."

Design notes
------------
* The map is the sole authority. We read research_map/research_map.json and derive the blocked
  node set from numerics_lock.locked_nodes plus every node that transitively depends_on a
  locked node. Declared artifact paths of those nodes are the "N1+ artifacts".
* Exit codes: 0 = lock intact, 1 = VIOLATION, 2 = cannot evaluate (map unreadable) -- a guard
  that silently passes when it cannot read its evidence would itself be a lock bypass.
* Fail-closed state semantics: PASS requires that the lock is not closed.  The only state that
  permits a blocked-node artifact to exist is the exact string ``released``; an absent, null,
  miscased or otherwise unrecognised state is treated as ``locked``.  ``numerics_lock_state_raw``,
  ``state_key_present`` and ``state_recognised`` report the original value so a malformed map is
  visible.
* --root lets the acceptance test plant a fake workspace (including a fake solver directory)
  without touching the real tree; that is the falsifier demonstration for this guard.
* Reads only; writes nothing. Never creates numerics/spherical_solver/.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_MAP = "research_map/research_map.json"
EXPLICIT_FORBIDDEN = ["numerics/spherical_solver"]


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


def evaluate(root: Path, map_rel: str) -> dict:
    m, mpath = load_map(root, map_rel)
    nodes = {}
    for g in m.get("groups", []):
        for n in g.get("nodes", []):
            nodes[n["id"]] = n

    lock = m.get("numerics_lock") or {}
    # Fail-closed state derivation: only the exact string ``released`` (set by the release
    # authority, astra) permits N1+ artifacts to exist.  An absent, null, miscased or
    # otherwise unrecognised state is treated as ``locked``, mirroring numerics/gates.py.
    state_key_present = "state" in lock
    raw_state = lock.get("state")
    state_recognised = raw_state in ("locked", "released")
    state = raw_state if state_recognised else "locked"
    seeds = set(lock.get("locked_nodes", []))
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

    return {
        "guard": "selfgravity_lock_guard",
        "map_path": str(mpath),
        "map_sha256": __import__("hashlib").sha256(mpath.read_bytes()).hexdigest(),
        "numerics_lock_state": state,
        "numerics_lock_state_raw": raw_state,
        "state_key_present": state_key_present,
        "state_recognised": state_recognised,
        "locked_seeds": sorted(seeds),
        "blocked_nodes": sorted(blocked),
        "declared_artifacts_checked": declared,
        "explicit_forbidden_checked": explicit,
        "violations": violations,
        "verdict": "FAIL" if (state == "locked" and violations) else "PASS",
        "note": "PASS means no evidence of N1+ self-gravity artifacts while locked; it is not a proof of absence.",
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
    return 1 if report["verdict"] == "FAIL" else 0


def self_test() -> int:
    """Falsifier demonstration: clean fixture PASSes, planted solver FAILs."""
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
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "research_map").mkdir(parents=True)
        (root / "research_map" / "research_map.json").write_text(json.dumps(fake_map))
        r_clean = evaluate(root, DEFAULT_MAP)
        results.append({"fixture": "clean", "expected": "PASS", "got": r_clean["verdict"],
                        "blocked_nodes": r_clean["blocked_nodes"]})
        (root / "numerics" / "spherical_solver").mkdir(parents=True)
        r_dirty = evaluate(root, DEFAULT_MAP)
        results.append({"fixture": "planted_solver_dir", "expected": "FAIL", "got": r_dirty["verdict"],
                        "violations": [v["kind"] for v in r_dirty["violations"]]})
    ok = all(r["expected"] == r["got"] for r in results)
    print(json.dumps({"self_test": "PASS" if ok else "FAIL", "results": results}, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
