#!/usr/bin/env python3
"""make_regression.py -- negative-control fixture for the F0 closure verifier.

Builds `regression_check.yaml` = the current canonical F0 taxonomy with the historical
(pre-rev5) AF-WCC-SCALAR-SPH conclusion text restored from
`fixtures/conclusion_bad_setbased.txt`.  The verifier must report CL1/CL2/CL3 (and CL4)
OPEN on this fixture; if it does not, the verifier has lost sensitivity and its CLOSED
verdict on the canonical file is void.

Line surgery only, no YAML re-dump; the edit is reversible and the semantic diff must be
exactly {classes.AF-WCC-SCALAR-SPH.conclusion.text}.

Exit codes: 0 fixture written and verified; 1 post-edit verification failed; 2 anchor/abort.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

import make_candidate as MC

CST = timezone(timedelta(hours=8))
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CANONICAL = ROOT / "research_map" / "formulation_taxonomy.yaml"
OUT = HERE / "regression_check.yaml"
EDITS = HERE / "regression_edits.json"
BAD = HERE / "fixtures" / "conclusion_bad_setbased.txt"
CLASS_KEY = '  "AF-WCC-SCALAR-SPH":'


def now() -> str:
    return datetime.now(CST).replace(microsecond=0).isoformat()


def build_regression(text: str) -> tuple[str, dict]:
    lines = text.splitlines(keepends=True)
    starts = [i for i, ln in enumerate(lines) if ln.rstrip("\n") == CLASS_KEY]
    if len(starts) != 1:
        raise ValueError(f"class key occurs {len(starts)} times (need 1)")
    start = starts[0]
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith('  "') and lines[i].rstrip("\n").endswith('":'):
            end = i
            break
    text_i = None
    for i in range(start, end):
        if lines[i].rstrip("\n") == "      text: >-":
            text_i = i
            break
    if text_i is None:
        raise ValueError("conclusion text block not found in the AF-WCC-SCALAR-SPH class")
    j = text_i + 1
    while j < end and not re.match(r"^      [A-Za-z_][A-Za-z0-9_]*:", lines[j]):
        j += 1
    bad_lines = ["        " + ln + "\n" for ln in BAD.read_text().rstrip("\n").split("\n")]
    new_lines = lines[:text_i] + ["      text: >-\n"] + bad_lines + lines[j:]
    region = {"replaced_1based_line_range": [text_i + 1, j], "new_block_lines": 1 + len(bad_lines)}
    return "".join(new_lines), region


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--canonical", default=str(CANONICAL))
    ap.add_argument("--pin", default=None)
    args = ap.parse_args(argv)

    canonical = Path(args.canonical).resolve()
    raw = canonical.read_bytes()
    sha = MC.sha256_bytes(raw)
    if args.pin and sha != args.pin:
        print(f"FAIL-CLOSED: canonical drifted: {sha} != {args.pin}", file=sys.stderr)
        return 2
    text = raw.decode("utf-8")
    try:
        regression, region = build_regression(text)
        before = yaml.safe_load(text)
        after = yaml.safe_load(regression)
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL-CLOSED: regression fixture not buildable: {exc}", file=sys.stderr)
        return 2

    problems = []
    changed = sorted(MC.semantic_diff(before, after))
    expected = {"classes.AF-WCC-SCALAR-SPH.conclusion.text"}
    if set(changed) != expected:
        problems.append(f"semantic diff mismatch: changed={changed}")
    if before["class_ids"] != after["class_ids"]:
        problems.append("class_ids changed")
    for cid, c in before["classes"].items():
        if c["axes"] != after["classes"][cid]["axes"]:
            problems.append(f"{cid}: axes changed")
    if problems:
        print(f"FAIL-CLOSED: post-edit verification failed: {problems}", file=sys.stderr)
        return 1

    OUT.write_text(regression)
    try:
        rel_out, rel_can = str(OUT.relative_to(ROOT)), str(canonical.relative_to(ROOT))
    except ValueError:
        rel_out, rel_can = str(OUT), str(canonical)
    EDITS.write_text(json.dumps({
        "task_id": "W087-F0-CLOSURE-CHECK-02",
        "generated_at": now(),
        "canonical": rel_can,
        "canonical_sha256": sha,
        "regression_fixture": rel_out,
        "regression_fixture_sha256": MC.sha256_bytes(regression.encode("utf-8")),
        "reintroduced_defect": "AF-WCC-SCALAR-SPH conclusion = fixtures/conclusion_bad_setbased.txt "
                               "(pre-rev5 set-based wording, bare generic quantifier, asserted equivalence)",
        "changed_semantic_paths": changed,
        "surgery": region,
        "expectation": "accept_f0_closure.py exits 3 with CL1, CL2, CL3 (and CL4) OPEN on this fixture",
    }, indent=2) + "\n")
    print(f"regression fixture written: {rel_out}")
    print(f"  canonical sha256: {sha}")
    print(f"  fixture sha256:   {MC.sha256_bytes(regression.encode('utf-8'))}")
    print(f"  surgery lines:    {region}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
