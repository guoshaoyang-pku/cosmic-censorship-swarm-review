#!/usr/bin/env python3
"""Gate-evidence dependency / pin map for the two-stage acceptance pipeline.

Task: W076-GATE-EVIDENCE-PINMAP-01 (worker-076, self-assigned bounded worker task).
Motivating blocker: astra-lead-formulation `lead-form-20260912T011509-123`
  "the acceptance pipeline is only half hash-bound ... stage 2 ... is unpinned"
Question: which files can change a G-FORM acceptance verdict, and which of them are
pinned by artifacts/formulation/FROZEN.json (revision 29)?

Method (READ-ONLY over canonical bytes; writes only under the caller's --out dir):
  1. Seed the closure at artifacts/formulation/tools/run_acceptance.py (FROZEN-pinned).
  2. Extract path-like string constants from every Python file reached (AST, no import
     execution), resolve them against a fixed base list, and recurse into .py files.
     Directory references are expanded to their contained files.
  3. Measure sha256 of every resolved file and classify against FROZEN.files.
  4. Reverse audit: re-measure every FROZEN-pinned path.

Falsifier: falsified if (a) a file that the acceptance pipeline reads directly or
transitively is absent from dependencies[], or (b) any pin classification disagrees with
a byte re-measurement, or (c) re-running this script on the same pinned bytes yields a
different classification for any reported path.  A pin map is a claim about
reachability from the seed set; an omitted dependency is a hard failure, not a
rounding error.

Exit: 0 analysis written, 2 input missing / internal error.
"""
from __future__ import annotations

import ast
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

FROZEN_PATH = ROOT / "artifacts/formulation/FROZEN.json"
SEEDS = [
    "artifacts/formulation/tools/run_acceptance.py",
    "artifacts/formulation/evidence/semantic_escape_rebased.json",
]
KNOWN_EXT = {".py", ".json", ".yaml", ".yml", ".jsonl", ".csv"}
# Directories that bare filenames in the stage tools resolve against.
BASES = [
    ROOT,
    ROOT / "artifacts/formulation",
    ROOT / "artifacts/formulation/tools",
    ROOT / "artifacts/formulation/evidence",
    ROOT / "artifacts/worker-06",
    ROOT / "artifacts/worker-06/semantic_fixtures",
]
MAX_DEPTH = 5


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def path_like(s: str) -> bool:
    """Conservative filter for path-shaped string constants (no prose, no regexes)."""
    if not s or len(s) > 200 or len(s) < 3:
        return False
    if any(c in s for c in "\n\t\r"):
        return False
    if " " in s or "*" in s or "\\" in s:
        return False
    if s.startswith(("/", "http://", "https://")):
        return False
    if s.endswith(tuple(KNOWN_EXT)):
        return True
    # directory-like relative reference, e.g. artifacts/formulation/evidence/rebased_fixtures
    if "/" in s and "." not in s.rsplit("/", 1)[-1] and len(s) >= 8:
        return True
    return s.endswith("/") and "." not in s


def refs_from_python(p: Path) -> list[str]:
    try:
        tree = ast.parse(p.read_text(errors="replace"))
    except SyntaxError:
        return []
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and path_like(node.value):
            out.add(node.value)
    return sorted(out)


def resolve(ref: str, src: Path) -> Path | None:
    """First existing candidate, searched over source-relative then fixed bases."""
    ref = ref[2:] if ref.startswith("./") else ref
    bases = [src.parent, src.parent.parent, ROOT] + BASES
    seen: set[Path] = set()
    for b in bases:
        cand = (b / ref).resolve()
        if cand in seen:
            continue
        seen.add(cand)
        if cand.exists():
            return cand
    return None


def main(argv: list[str]) -> int:
    out_dir = Path(argv[1]).resolve() if len(argv) > 1 else HERE / "raw"
    out_dir.mkdir(parents=True, exist_ok=True)
    if not FROZEN_PATH.exists():
        print(f"missing {FROZEN_PATH}", file=sys.stderr)
        return 2
    frozen_bytes = FROZEN_PATH.read_bytes()
    frozen = json.loads(frozen_bytes)
    pinned: dict[str, str] = {k: v["sha256"] for k, v in frozen["files"].items()}

    visited: set[str] = set()
    edges: dict[str, set[str]] = {}          # dep rel path -> set(referrer rel path)
    unresolved: list[dict] = []

    def add_edge(target: Path, referrer: str) -> None:
        rel = str(target.relative_to(ROOT))
        edges.setdefault(rel, set()).add(referrer)

    def expand_dir(d: Path, referrer: str) -> int:
        """Expand a referenced directory, but only inside ROOT and with a hard cap."""
        try:
            d.relative_to(ROOT)
        except ValueError:
            unresolved.append({"ref": str(d), "in": referrer, "why": "directory outside ROOT"})
            return 0
        if d == ROOT:
            unresolved.append({"ref": str(d), "in": referrer, "why": "ROOT itself is not expanded"})
            return 0
        n = 0
        for f in sorted(d.rglob("*")):
            if f.is_file() and not f.name.startswith("._") and f.suffix in KNOWN_EXT:
                add_edge(f, referrer)
                n += 1
                if n > 500:
                    unresolved.append({"ref": str(d), "in": referrer, "why": "dir expansion capped at 500"})
                    break
        return n

    queue: list[tuple[Path, str, int]] = []
    for s in SEEDS:
        p = ROOT / s
        if p.exists():
            queue.append((p, "seed", 0))
    while queue:
        cur, referrer, depth = queue.pop(0)
        rel = str(cur.relative_to(ROOT))
        if rel in visited:
            continue
        visited.add(rel)
        add_edge(cur, referrer)
        if depth >= MAX_DEPTH:
            continue
        if cur.is_dir():
            expand_dir(cur, rel)
            continue
        if cur.suffix != ".py":
            continue
        for ref in refs_from_python(cur):
            r = resolve(ref, cur)
            if r is None:
                unresolved.append({"ref": ref, "in": rel})
                continue
            if r.is_dir():
                expand_dir(r, rel)
            else:
                add_edge(r, rel)
                if r.suffix == ".py":
                    queue.append((r, rel, depth + 1))

    deps = []
    counts = {"pinned_match": 0, "pinned_mismatch": 0, "unpinned": 0}
    for rel in sorted(edges):
        p = ROOT / rel
        if not p.exists():
            counts["unpinned"] += 1
            deps.append({"path": rel, "exists": False, "pin": "missing_at_measure",
                         "referenced_by": sorted(edges[rel])})
            continue
        h = sha256_file(p)
        if rel in pinned:
            match = pinned[rel] == h
            pin = "pinned_match" if match else "pinned_mismatch"
            counts[pin] += 1
            deps.append({"path": rel, "exists": True, "bytes": p.stat().st_size, "sha256": h,
                         "pin": pin, "frozen_sha256": pinned[rel],
                         "referenced_by": sorted(edges[rel])})
        else:
            counts["unpinned"] += 1
            deps.append({"path": rel, "exists": True, "bytes": p.stat().st_size, "sha256": h,
                         "pin": "unpinned", "referenced_by": sorted(edges[rel])})

    reverse = []
    frozen_problems = []
    for rel in sorted(pinned):
        p = ROOT / rel
        if not p.exists():
            reverse.append({"path": rel, "status": "missing", "declared_sha256": pinned[rel]})
            frozen_problems.append(rel)
            continue
        h = sha256_file(p)
        ok = h == pinned[rel]
        reverse.append({"path": rel, "status": "match" if ok else "mismatch",
                        "declared_sha256": pinned[rel], "measured_sha256": h})
        if not ok:
            frozen_problems.append(rel)

    pinmap = {
        "schema": "worker-076/gate-evidence-pinmap/v1",
        "task_id": "W076-GATE-EVIDENCE-PINMAP-01",
        "generated_at": now(),
        "root": str(ROOT),
        "seed_set": SEEDS,
        "frozen_revision": frozen.get("revision"),
        "frozen_sha256": hashlib.sha256(frozen_bytes).hexdigest(),
        "frozen_path_count": len(pinned),
        "summary": {
            "dependencies_resolved": len(deps),
            "pinned_match": counts["pinned_match"],
            "pinned_mismatch": counts["pinned_mismatch"],
            "unpinned": counts["unpinned"],
            "frozen_reverse_problems": len(frozen_problems),
            "unresolved_refs": len(unresolved),
        },
        "dependencies": deps,
        "unpinned_reachable": [d["path"] for d in deps if d["pin"] in ("unpinned", "missing_at_measure")],
        "reverse_audit": reverse,
        "frozen_problem_paths": frozen_problems,
        "unresolved_refs": unresolved,
        "falsifier": ("Falsified if a file read directly or transitively by the acceptance pipeline is absent from "
                      "dependencies[], or if any pin classification disagrees with a byte re-measurement, or if a "
                      "re-run on the same pinned bytes changes any classification."),
    }
    (out_dir / "pinmap.json").write_text(json.dumps(pinmap, indent=1, sort_keys=False) + "\n")
    print(json.dumps({"out": str(out_dir / "pinmap.json"), **pinmap["summary"]}, indent=1))
    for d in deps:
        if d["pin"] != "pinned_match":
            print(f"  {d['pin']:16s} {d['path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
