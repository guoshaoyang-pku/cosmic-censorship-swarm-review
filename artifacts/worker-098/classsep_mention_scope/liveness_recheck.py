#!/usr/bin/env python3
"""W098-CLASSSEP-MENTION-SCOPE-01 liveness recheck after the 01:00 cycle.

The live map moved 262da6979857 -> 083d3bfa7da4 (claims 320 -> 375) after the pinned report was
written. Re-measures the two decisive batteries (mandatory-clean and mandatory-fire controls) and
the hard-finding count on the CURRENT map for all four arms. Read-only; writes
raw/liveness_recheck.json. Does not touch report.json (which stays pinned to its map hash).
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"

CLEAN = [
    ("FP1_live_neg", "so no C0/C2 merge exists at the formal surface."),
    ("FP2_live_split", "2 SPLIT_REQUIRED (TC-F0-N14 merged C0/C2 regularities; the two rows require a split)"),
    ("FP3_live_mention", "R1's merge pattern matches only bare C0/C2 composites"),
    ("FP4_live_nonmerge", "This is a class separation check: independent C0/C2 non-merge evidence."),
    ("FP5_rather_than", "This is a single-frozen-data-class question rather than a C2/C0 merge."),
    ("FP6_quoted_mention", "the same slot carrying 'C0 or C2 are one class' is flagged"),
    ("FP7_rejected_hypothesis", "We analysed the C0/C2 unified class only as a rejected hypothesis."),
    ("FP8_counting_prose", "This note measures how often the C0/C2 combined pattern appears in review prose."),
]
FIRE = [
    ("FN1_meta_case", "The C0/C2 merged class is the only case we consider."),
    ("FN2_meta_test", "We test that the C0/C2 unified class is the right unit."),
    ("FN3_meta_corpus", "This corpus treats the C0/C2 as one class."),
    ("FN4_meta_independent", "The independent C0/C2 merged class is our unit of analysis."),
    ("FN5_meta_pattern", "The C0/C2 combined pattern is the portfolio's chosen unit."),
    ("FN6_neg_scope", "It is not the case that the classes are separate; the C0/C2 are one class."),
    ("AX1_interjection_affirm", "No, the C0/C2 are one class."),
    ("AX2_not_distinct_but", "The C0/C2 are not distinct but one merged class."),
    ("AX3_detector_flags_right_unit", "The detector flags the C0/C2 as one class, which is the right unit."),
    ("AX4_pattern_is_right_unit", "The C0/C2 merged pattern is the right unit of analysis."),
    ("AX5_no_question_idiom", "There is no question that the C0/C2 are one class."),
    ("AX6_contrast_yet", "The classes are separate, yet the C0/C2 are one class."),
]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def fires(mod, text):
    out = []
    mod._scan_composite(text, "probe", out, mode="prose")
    return out


def map_hard(mod, m):
    hard = [x for x in mod.findings_for_map(m) if not str(x).startswith("CLASSSEP-SOFT:")]
    for g in m.get("groups", []):
        for n in g.get("nodes", []):
            art = n.get("artifact")
            p = ROOT / art if art else None
            if p and p.is_file() and p.stat().st_size < 2_000_000:
                hard += [x for x in mod.findings_for_text(p.read_text(errors="replace"),
                                                          f"{n['id']} artifact {art}")
                         if not str(x).startswith("CLASSSEP-SOFT:")]
    return hard


def main():
    live_map_path = ROOT / "research_map/research_map.json"
    live_map = json.loads(live_map_path.read_text())
    mods = {
        "live": load("w098_lr_live", ROOT / "research_map/class_separation.py"),
        "staged": load("w098_lr_staged", ROOT / "proposed/class_separation.py"),
        "v1": load("w098_lr_v1", HERE / "candidate_class_separation.py"),
        "v2": load("w098_lr_v2", HERE / "candidate_class_separation.v2.py"),
        "v3": load("w098_lr_v3", HERE / "candidate_class_separation.v3.py"),
    }
    out = {"recheck_at": "2026-09-12T01:04:00+08:00", "live_map_sha256": sha(live_map_path),
           "live_map_claims": len(live_map.get("claims", [])), "arms": {}}
    for name, mod in mods.items():
        rec = {
            "clean_fires": [n for n, t in CLEAN if fires(mod, t)],
            "fire_missing": [n for n, t in FIRE if not fires(mod, t)],
        }
        rec["map_hard"] = len(map_hard(mod, live_map))
        if name == "v3":
            rec["map_findings"] = [x[:220] for x in map_hard(mod, live_map)]
        out["arms"][name] = rec
    (RAW / "liveness_recheck.json").write_text(json.dumps(out, indent=2, sort_keys=True))
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
