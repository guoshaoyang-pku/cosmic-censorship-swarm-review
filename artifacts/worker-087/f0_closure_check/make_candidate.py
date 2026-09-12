#!/usr/bin/env python3
"""make_candidate.py -- deterministic, minimal, anchored repair candidate for F0.

Task W087-F0-CLOSURE-CHECK-02 (bounded execution worker 087).

Reads the pinned canonical research_map/formulation_taxonomy.yaml and applies exactly
four anchored text replacements that discharge the three blocking findings:

  E1  AF-WCC-SCALAR-SPH conclusion -> single-q TAIL predicate, explicit named deferral
      of the unresolved genericity quantifier, no asserted equivalence  (B-16F0-1/W082-F-01)
  E2  class_scope_adjudication.resolved_divergences[D3] gains a scope_note recording the
      AF-WCC-SCALAR-SPH named deferral                                     (B-16F0-2)
  E3  AF-SCC-C2-VAC-GEN provenance.schema_owner -> F2a + canonical C2 schema  (B-16F0-3)
  E4  AF-SCC-C0-VAC-GEN provenance.schema_owner -> F2b + canonical C0 schema  (B-16F0-3)

Guarantees / fail-closed behaviour
  * refuses to run if the canonical hash != --pin (exit 2);
  * refuses if any anchor is not found exactly once (exit 2);
  * writes only inside this artifact directory;
  * after editing, proves the edit is reversible (inverse replacements reproduce the
    canonical bytes exactly), that class_ids / classes / every class axis / conclusion
    type are unchanged, and that the fixed conclusion equals fixtures/conclusion_fixed.txt;
  * does NOT touch the canonical path, the authoring mirror, FROZEN.json, the corpus or
    any schema.  Publication and re-pin remain lead-side acts.

Exit codes: 0 candidate written and verified; 1 post-edit verification failed; 2 drift/abort.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

CST = timezone(timedelta(hours=8))
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CANONICAL = ROOT / "research_map" / "formulation_taxonomy.yaml"
PIN = "276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc"
CANDIDATE = HERE / "formulation_taxonomy.candidate.yaml"
DIFF = HERE / "candidate.diff"
EDITS_JSON = HERE / "candidate_edits.json"
FIXED_CONCLUSION = HERE / "fixtures" / "conclusion_fixed.txt"

OLD_CONCLUSION = '''    conclusion:
      type: "weak_cosmic_censorship"
      text: >-
        For generic data in the class, the MGHD admits I+ and every future-inextendible causal
        geodesic contained in J-(I+) is complete; equivalently, the singularities that form are
        hidden behind an event horizon and no singularity is visible from I+.
      forbidden_inflation: "Does not assert inextendibility, and the spherical symmetry may not be dropped (that is a different, open class)."'''

OLD_D3 = '''    - id: D3
      status: resolved
      resolution: "the comeager quantifier is now stated explicitly in each class conclusion text and bound before the data"'''

OLD_C2_OWNER = '      schema_owner: "F2 (artifact schemas/af_scc_regularities.yaml, section C2)"'
OLD_C0_OWNER = '      schema_owner: "F2 (artifact schemas/af_scc_regularities.yaml, section C0)"'


def now() -> str:
    return datetime.now(CST).replace(microsecond=0).isoformat()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def flat(text: str) -> str:
    return " ".join(str(text).split())


EXPECTED_CHANGED_PATHS = {
    "classes.AF-WCC-SCALAR-SPH.conclusion.text",
    "classes.AF-WCC-SCALAR-SPH.conclusion.forbidden_inflation",
    "class_scope_adjudication.resolved_divergences[1].scope_note",
    "classes.AF-SCC-C2-VAC-GEN.provenance.schema_owner",
    "classes.AF-SCC-C0-VAC-GEN.provenance.schema_owner",
}


def semantic_diff(a, b, path: str = "") -> list[str]:
    """Leaf paths whose parsed value differs between two documents."""
    changed: list[str] = []

    def join(key: str) -> str:
        return f"{path}.{key}" if path else str(key)

    if type(a) is not type(b):
        return [path or "$"]
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                changed.append(join(k))
            else:
                changed += semantic_diff(a[k], b[k], join(k))
    elif isinstance(a, list):
        if len(a) != len(b):
            changed.append(path)
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                changed += semantic_diff(x, y, f"{path}[{i}]" if path else f"[{i}]")
    elif a != b:
        changed.append(path)
    return changed


def build_new_conclusion() -> str:
    body = FIXED_CONCLUSION.read_text().rstrip("\n")
    indented = "\n".join("        " + line if line else line for line in body.split("\n"))
    return (
        '    conclusion:\n'
        '      type: "weak_cosmic_censorship"\n'
        '      text: >-\n'
        f"{indented}\n"
        '      forbidden_inflation: "Does not assert inextendibility; the spherical symmetry may not be '
        'dropped (that is a different, open class); the genericity quantifier is explicitly deferred '
        'to L0/L1 and is not frozen."'
    )


def build_new_d3() -> str:
    return (
        OLD_D3
        + "\n"
        + "      scope_note: >-\n"
        + "        AF-WCC-SCALAR-SPH is exempt from the comeager spelling: its genericity_kind is `unresolved`\n"
        + "        (H4) and owned by L0/L1, so its conclusion binds the genericity datum explicitly as\n"
        + "        unresolved and bound before the data instead of asserting a comeager set; D3 is discharged\n"
        + "        for that class as a named deferral, not as a comeager assertion."
    )


NEW_C2_OWNER = '      schema_owner: "F2a (artifact schemas/af_scc_c2_vacuum.yaml)"'
NEW_C0_OWNER = '      schema_owner: "F2b (artifact schemas/af_scc_c0_vacuum.yaml)"'


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--canonical", default=str(CANONICAL))
    ap.add_argument("--pin", default=PIN)
    ap.add_argument("--out", default=str(CANDIDATE))
    args = ap.parse_args(argv)

    canonical = Path(args.canonical).resolve()
    out = Path(args.out).resolve()
    if HERE not in out.parents:
        print(f"FAIL-CLOSED: refusing to write outside {HERE}: {out}", file=sys.stderr)
        return 2

    raw = canonical.read_bytes()
    sha = sha256_bytes(raw)
    if args.pin and sha != args.pin:
        print(f"FAIL-CLOSED: canonical drifted: {sha} != {args.pin}", file=sys.stderr)
        return 2
    text = raw.decode("utf-8")

    edits = [
        {"id": "E1", "finding": "B-16F0-1 / W082-F-01", "anchor": OLD_CONCLUSION, "new": build_new_conclusion(),
         "where": "classes.AF-WCC-SCALAR-SPH.conclusion"},
        {"id": "E2", "finding": "B-16F0-2", "anchor": OLD_D3, "new": build_new_d3(),
         "where": "class_scope_adjudication.resolved_divergences[D3]"},
        {"id": "E3", "finding": "B-16F0-3", "anchor": OLD_C2_OWNER, "new": NEW_C2_OWNER,
         "where": "classes.AF-SCC-C2-VAC-GEN.provenance.schema_owner"},
        {"id": "E4", "finding": "B-16F0-3", "anchor": OLD_C0_OWNER, "new": NEW_C0_OWNER,
         "where": "classes.AF-SCC-C0-VAC-GEN.provenance.schema_owner"},
    ]

    candidate = text
    for e in edits:
        n = candidate.count(e["anchor"])
        if n != 1:
            print(f"FAIL-CLOSED: anchor {e['id']} occurs {n} times (need exactly 1): {e['where']}", file=sys.stderr)
            return 2
        candidate = candidate.replace(e["anchor"], e["new"])

    # Reversibility: inverse replacements must reproduce the canonical bytes exactly.
    inverse = candidate
    for e in reversed(edits):
        inverse = inverse.replace(e["new"], e["anchor"])
    if inverse != text:
        print("FAIL-CLOSED: edit is not reversible; aborting without writing", file=sys.stderr)
        return 1

    try:
        before = yaml.safe_load(text)
        after = yaml.safe_load(candidate)
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL-CLOSED: candidate does not parse: {exc}", file=sys.stderr)
        return 1

    problems = []
    if before["class_ids"] != after["class_ids"]:
        problems.append("class_ids changed")
    if list(before["classes"].keys()) != list(after["classes"].keys()):
        problems.append("class keys changed")
    for cid, c in before["classes"].items():
        if c["axes"] != after["classes"][cid]["axes"]:
            problems.append(f"{cid}: axes changed")
        if c["conclusion"]["type"] != after["classes"][cid]["conclusion"]["type"]:
            problems.append(f"{cid}: conclusion type changed")
    fixed = flat(FIXED_CONCLUSION.read_text())
    got = flat(after["classes"]["AF-WCC-SCALAR-SPH"]["conclusion"]["text"])
    if got != fixed:
        problems.append("SCALAR-SPH conclusion != fixtures/conclusion_fixed.txt")
    changed_paths = sorted(semantic_diff(before, after))
    if set(changed_paths) != EXPECTED_CHANGED_PATHS:
        problems.append(f"semantic diff mismatch: missing={sorted(EXPECTED_CHANGED_PATHS - set(changed_paths))} "
                        f"unexpected={sorted(set(changed_paths) - EXPECTED_CHANGED_PATHS)}")
    if problems:
        print(f"FAIL-CLOSED: post-edit verification failed: {problems}", file=sys.stderr)
        return 1

    out.write_bytes(candidate.encode("utf-8"))
    diff_lines = list(difflib.unified_diff(
        text.splitlines(keepends=True), candidate.splitlines(keepends=True),
        fromfile=f"a/{canonical.relative_to(ROOT)}",
        tofile=f"b/{out.relative_to(ROOT)}",
        n=3,
    ))
    DIFF.write_text("".join(diff_lines))

    try:
        rel_out = str(out.relative_to(ROOT))
        rel_can = str(canonical.relative_to(ROOT))
    except ValueError:
        rel_out, rel_can = str(out), str(canonical)

    edit_table = {
        "task_id": "W087-F0-CLOSURE-CHECK-02",
        "generated_at": now(),
        "canonical": rel_can,
        "canonical_sha256": sha,
        "candidate": rel_out,
        "candidate_sha256": sha256_bytes(candidate.encode("utf-8")),
        "candidate_bytes": len(candidate.encode("utf-8")),
        "reversible": True,
        "class_ids_unchanged": True,
        "axes_unchanged": True,
        "conclusion_types_unchanged": True,
        "changed_semantic_paths": changed_paths,
        "expected_semantic_paths": sorted(EXPECTED_CHANGED_PATHS),
        "edits": [
            {"id": e["id"], "finding": e["finding"], "where": e["where"],
             "anchor_occurrences": text.count(e["anchor"]),
             "anchor_sha256": sha256_bytes(e["anchor"].encode("utf-8")),
             "new_sha256": sha256_bytes(e["new"].encode("utf-8")),
             "anchor_lines": e["anchor"].count("\n") + 1,
             "new_lines": e["new"].count("\n") + 1}
            for e in edits
        ],
        "not_touched": [
            "research_map/formulation_taxonomy.yaml (canonical path)",
            "artifacts/formulation/formulation_taxonomy.yaml (authoring supplement)",
            "artifacts/formulation/FROZEN.json",
            "schemas/taxonomy_cases.jsonl",
            "schemas/af_*.yaml",
        ],
    }
    EDITS_JSON.write_text(json.dumps(edit_table, indent=2) + "\n")

    print(f"candidate written: {rel_out}")
    print(f"  canonical sha256: {sha}")
    print(f"  candidate sha256: {edit_table['candidate_sha256']}")
    print(f"  edits: {', '.join(e['id'] for e in edits)}; diff lines: {len(diff_lines)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
