#!/usr/bin/env python3
"""Freeze the W023-F2B-DIR-GUARD-01 fixture set (copies + derived mutants).

Read-only on every canonical path: this script copies bytes into ./fixtures/ and derives
mutants by literal string substitution (it fails closed if an anchor is absent). It never
writes to schemas/, research_map/, artifacts/formulation/ or any other worker's tree.

    python3 make_fixtures.py      # writes fixtures/*.yaml + fixtures/MANIFEST.json
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
FIX = HERE / "fixtures"
TZ = timezone(timedelta(hours=8))
NOW = lambda: datetime.now(TZ).isoformat(timespec="seconds")  # noqa: E731

# name -> (source path relative to repo root, expected sha256 prefix)
SOURCES = {
    "f00_live_c0": ("schemas/af_scc_c0_vacuum.yaml", "b2ab6acb2bbe"),
    "f01_live_c2": ("schemas/af_scc_c2_vacuum.yaml", "e9a27996dfd3"),
    "f02_live_wcc": ("schemas/af_wcc_vacuum.yaml", "d9cebb9404b2"),
    "f03_repair_066": ("artifacts/worker-023/f2b_dir_review/proposed_af_scc_c0_vacuum_v1_066.yaml",
                       "84b5d3fa29a6"),
    "f04_composed_044": ("artifacts/worker-044/f2b_live_closure_01/sandbox/schemas/af_scc_c0_vacuum.yaml",
                         "48cadb72e507"),
    "f05_corrected_023": ("artifacts/worker-023/f2b_dir_review/proposed_af_scc_c0_vacuum_v2_corrected.yaml",
                          "9ab32ee39d00"),
    "f06_corrected_080": ("artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_corrected.yaml",
                          None),
}

# mutant name -> (base fixture, literal anchor, replacement, expectation)
MUTANTS = {
    "m07_nonsense": (
        "f05_corrected_023",
        "so this class's conclusion ENTAILS H2_loc-inextendibility and C2-inextendibility, never the reverse;",
        "H2_loc-inextendibility is a banana;",
        {"inverted": 0, "unclassified_contains": "banana"},
    ),
    "m08_negated": (
        "f05_corrected_023",
        "so this class's conclusion ENTAILS H2_loc-inextendibility and C2-inextendibility, never the reverse;",
        "it is NOT the case that H2_loc-inextendibility ENTAILS this class's conclusion;",
        {"inverted": 0, "neutral_present": True},
    ),
    "m09_reversed_corrected": (
        "f05_corrected_023",
        "so this class's conclusion ENTAILS H2_loc-inextendibility and C2-inextendibility, never the reverse;",
        "so H2_loc-inextendibility ENTAILS this class's conclusion;",
        {"inverted": 1},
    ),
    "m10_arrow_inverted": (
        "f00_live_c0",
        "the implication runs C0 => C2 only",
        "the implication runs C2 => C0 only",
        {"inverted": 1},
    ),
    "m11_unsupported_label": (
        "f05_corrected_023",
        "so this class's conclusion ENTAILS H2_loc-inextendibility and C2-inextendibility, never the reverse;",
        "so this class's conclusion ENTAILS W^{1,2}-inextendibility;",
        {"inverted": 0, "unsupported": 1},
    ),
}


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main() -> int:
    FIX.mkdir(parents=True, exist_ok=True)
    man = {"task_id": "W023-F2B-DIR-GUARD-01", "created_at": NOW(),
           "actor": "worker-023", "fixtures": {}, "mutants": {}}
    for name, (rel, prefix) in SOURCES.items():
        src = ROOT / rel
        if not src.exists():
            print(f"MISSING SOURCE {rel}")
            return 2
        b = src.read_bytes()
        h = sha(b)
        if prefix and not h.startswith(prefix):
            print(f"HASH DRIFT {rel}: {h[:12]} != {prefix}")
            return 2
        dst = FIX / f"{name}.yaml"
        shutil.copyfile(src, dst)
        man["fixtures"][name] = {"source": rel, "sha256": h, "bytes": len(b)}
        print(f"pinned {name} <- {rel} {h[:12]}")
    for name, (base, anchor, repl, expect) in MUTANTS.items():
        b = (FIX / f"{base}.yaml").read_bytes()
        if b.count(anchor.encode()) != 1:
            print(f"ANCHOR MISS {name}: {b.count(anchor.encode())} occurrences in {base}")
            return 2
        mb = b.replace(anchor.encode(), repl.encode(), 1)
        (FIX / f"{name}.yaml").write_bytes(mb)
        man["mutants"][name] = {"base": base, "anchor": anchor, "replacement": repl,
                                "expect": expect, "sha256": sha(mb), "bytes": len(mb)}
        print(f"derived {name} from {base} {sha(mb)[:12]} expect={expect}")
    (FIX / "MANIFEST.json").write_text(json.dumps(man, indent=2, sort_keys=True))
    print(f"manifest written: {len(man['fixtures'])} fixtures, {len(man['mutants'])} mutants")
    return 0


if __name__ == "__main__":
    sys.exit(main())
