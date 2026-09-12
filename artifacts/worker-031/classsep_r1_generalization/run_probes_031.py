#!/usr/bin/env python3
"""Targeted probes for the two failure modes the fresh battery exposed.

P1 quotation scope: a quoted composite token in one clause must not silence a
   genuine unity assertion in a later clause (the candidate's own docstring says
   a quoted mention is silent; the claim is that the silence is clause-local).
P2 negation scope: a denial in one clause must not manufacture a unity assertion,
   and litotes must not be read as a denial.
P3 live-like: sentences shaped like the project's actual claim prose (a genuine
   assertion carrying report/negation vocabulary in a second clause).
P4 substring hazard: the candidate's widened vocabulary must not fire on words
   that contain it.

Every probe is a MINIMAL PAIR: the two members differ only in the cue under test,
so a differing verdict is attributable to that cue.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARMS = {
    "CANON_a8c04": "class_separation.a8c04fc31e4a.py",
    "CAND_r1_42cdb": "class_separation.candidate_r1.42cdb683.py",
    "PFX_dc8aa0": "class_separation.prosefix_dc8aa0de.py",
}


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def hard(mod, text: str, where: str) -> int:
    return len([f for f in mod.findings_for_text(text, where) if not f.startswith("CLASSSEP-SOFT")])


PAIRS = [
    # id, expected (1=plainly asserts unity), [ (label, text) ... ] with member A the control
    ("P1a-quote-scope", 1, [
        ("assertion only", "We assert that C0 and C2 are one class."),
        ("quoted token + assertion (other clause)",
         "The quoted token 'C0/C2' appears in the header, and we assert that the two classes are one class."),
        ("reported denial + assertion (other clause)",
         "A referee wrote that no C0/C2 merge exists, yet our conclusion is that C0 and C2 are one class."),
    ]),
    ("P1b-metalinguistic-scope", 1, [
        ("assertion only", "C0 and C2 are one class."),
        ("metalinguistic prefix + assertion (other clause)",
         "0 genuine assertions that C0 and C2 are one class were found earlier; this claim asserts that C0 and C2 are one class."),
    ]),
    ("P2a-negation-scope", 0, [
        ("report only", "A referee wrote that C0 and C2 are one class."),
        ("report + denial (other clause)",
         "A referee wrote that C0 and C2 are one class, which is wrong."),
    ]),
    ("P2b-litotes", 1, [
        ("plain assertion", "We hold that C0 and C2 are one class."),
        ("litotes", "We do not deny that C0 and C2 are one class."),
    ]),
    ("P3a-live-like", 1, [
        ("bare assertion", "C0 and C2 are one class."),
        ("assertion + historical note",
         "C0 and C2 are one class; note that the earlier 'no C0/C2 merge' finding is superseded."),
        ("assertion + count report",
         "C0 and C2 are one class, so the census reports 0 hard findings."),
    ]),
    ("P4a-substring", 0, [
        ("mention", "The token C0/C2 is a composite."),
        ("substring carrier",
         "The C0/C2 column is a merged column in the spreadsheet export."),
    ]),
]


def main() -> int:
    mods = {a: load(a, HERE / "pinned" / f) for a, f in ARMS.items()}
    out = {"schema": "worker-031/classsep-r1-generalization/probes/v1",
           "task_id": "W031-CLASSSEP-R1-GENERALIZATION-01",
           "class_id": "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN", "probes": []}
    lines = []
    for pid, expected, members in PAIRS:
        rec = {"probe": pid, "expected_findings": expected, "members": []}
        lines.append(f"\n{pid} (expected_findings={expected})")
        for label, text in members:
            row = {"label": label, "text": text, "hard": {}}
            cells = []
            for arm, mod in mods.items():
                n = hard(mod, text, f"{pid}/{label}")
                row["hard"][arm] = n
                cells.append(f"{arm}={n}")
            rec["members"].append(row)
            lines.append(f"   {label:48s} " + "  ".join(cells))
        out["probes"].append(rec)
    (HERE / "out" / "probes.json").write_text(json.dumps(out, indent=1) + "\n")
    (HERE / "raw" / "probes.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
