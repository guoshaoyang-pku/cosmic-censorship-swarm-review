#!/usr/bin/env python3
"""W029 F2b repair landing blast-radius measurement (read-only)."""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent

PATTERNS = {
    "size_premise": "C2 is a strictly larger extension class",
    "containment_denial_live": "No containment with C2 or C0 is asserted here",
}
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".cache"}
TEXT_SUFFIXES = {".yaml", ".yml", ".json", ".jsonl", ".md", ".txt", ".csv", ".diff", ".py", ".js"}


def category(rel: str) -> str:
    if rel.startswith("schemas/semantic_contract_tests/"):
        return "semantic_contract_fixtures"
    if rel.startswith("schemas/"):
        return "canonical_schemas"
    if rel.startswith("artifacts/formulation/"):
        return "formulation_authoring"
    if rel.startswith("research_map/"):
        return "map"
    if rel.startswith("reviews/"):
        return "reviews"
    if rel.startswith("tmp/") or rel.startswith("runtime/"):
        return "scratch_or_runtime"
    if rel.startswith("artifacts/worker-"):
        return "worker_artifacts"
    return "other"


def main() -> int:
    hits = defaultdict(list)
    scanned = 0
    for p in ROOT.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in TEXT_SUFFIXES:
            continue
        rel = p.relative_to(ROOT).as_posix()
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        scanned += 1
        try:
            txt = p.read_text(errors="ignore")
        except Exception:
            continue
        line = txt.find(PATTERNS["size_premise"])
        if line < 0:
            line = txt.find(PATTERNS["containment_denial_live"])
        if line < 0:
            continue
        lineno = txt.count("\n", 0, line) + 1
        kinds = [k for k, pat in PATTERNS.items() if pat in txt]
        hits[category(rel)].append({"path": rel, "line": lineno, "kinds": kinds})

    manifest = ROOT / "schemas/semantic_contract_tests/manifest.json"
    obs = ROOT / "schemas/semantic_contract_tests/observed_verdicts.json"
    manifest_info = {}
    if manifest.exists():
        m = json.loads(manifest.read_text())
        manifest_info = {
            "sha256_of_manifest": __import__("hashlib").sha256(manifest.read_bytes()).hexdigest(),
            "top_keys": sorted(m)[:20] if isinstance(m, dict) else f"list[{len(m)}]",
            "binds_fixture_paths": bool(re.search(r"fixtures/", manifest.read_text()[:200000])),
            "binds_sha256": "sha256" in manifest.read_text(),
        }
    out = {
        "task_id": "W029-F2B-REPAIR-CANDIDATE-VERIFY-01",
        "purpose": "which derived copies embed the two F2b defect strings, so a landing can be complete",
        "files_scanned": scanned,
        "pattern_strings": PATTERNS,
        "counts_by_category": {k: len(v) for k, v in sorted(hits.items())},
        "canonical_tree_hits": hits.get("canonical_schemas", []) + hits.get("formulation_authoring", []) + hits.get("map", []),
        "fixture_hits": hits.get("semantic_contract_fixtures", []),
        "manifest": manifest_info,
        "observed_verdicts_present": obs.exists(),
        "reading": ("Defect strings survive in frozen fixture copies. Fixtures are inputs to the semantic "
                    "contract tests, not normative carriers; the live denial string in canonical+mirror is "
                    "normative and must be repaired. Fixture regeneration is a landing decision for the owner: "
                    "either regenerate from the repaired canonical file or record them as intentionally stale "
                    "inputs (they are bound by the tests' own manifest, so a silent rewrite has its own risk)."),
    }
    (HERE / "blast_radius.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: out[k] for k in ("files_scanned", "counts_by_category", "canonical_tree_hits")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
