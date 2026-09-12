#!/usr/bin/env python3
"""W008-F2B-DUALREPAIR-01 — build the rebased 2-edit candidate and prove minimality.

Reads the canonical schemas/af_scc_c0_vacuum.yaml (rev11, hash-pinned),
applies exactly two wording repairs, and writes:
  candidate/af_scc_c0_vacuum.yaml
  evidence/minimality_diff.txt     unified diff, must be exactly 2 hunks
  evidence/minimality_report.json  structural YAML diff == exactly 2 leaf paths
The script fails closed (exit 3) on hash mismatch or if anything else changes.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
ROOT_REPO = ROOT.parents[2]
CANONICAL = ROOT_REPO / "schemas" / "af_scc_c0_vacuum.yaml"

EXPECT_C0 = "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508"

OLD_BULLET = (
    "- \"H2_loc (locally square-integrable curvature) is a distinct regularity-axis value "
    "phrased in terms of CURVATURE, not metric differentiability. No containment with C2 or C0 "
    "is asserted here; the informal phrase 'strictly between' is not used and must not be cited "
    "(worker-16 F2b-16-02 accepted).\""
)
NEW_BULLET = (
    "- \"H2_loc (locally square-integrable curvature) is a distinct regularity-axis value "
    "phrased in terms of CURVATURE, not metric differentiability. The extension sets are "
    "nonetheless nested: E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0 (see "
    "implication_ledger), so H2_loc-inextendibility ENTAILS this class's conclusion; the "
    "informal phrase 'strictly between' is not a class definition and must not be cited "
    "(worker-16 F2b-16-02 accepted). [R2 major: the earlier 'no containment with C2 or C0 is "
    "asserted here' was wrong]\""
)
OLD_REASON = (
    "reason: \"C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker\""
)
NEW_REASON = (
    "reason: \"C2 is a strictly smaller extension class (E_C2 subset of E_C0), so "
    "C2-inextendibility is strictly weaker\""
)
EXPECTED_PATHS = {
    "regularity.must_not_conflate[0]",
    "implication_ledger.forbidden_transfers[0].reason",
}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def struct_diff(a, b, path=""):
    """Return list of changed leaf paths between two YAML objects."""
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            p = f"{path}.{k}" if path else str(k)
            if k not in a or k not in b:
                out.append((p, "added/removed"))
            else:
                out += struct_diff(a[k], b[k], p)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append((path, f"list length {len(a)} -> {len(b)}"))
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                out += struct_diff(x, y, f"{path}[{i}]")
    elif a != b:
        out.append((path, "value changed"))
    return out


def main() -> int:
    canonical_text = CANONICAL.read_text()
    got = hashlib.sha256(canonical_text.encode()).hexdigest()
    if got != EXPECT_C0:
        print(json.dumps({"verdict": "FAIL-CLOSED",
                          "detail": f"canonical hash {got} != {EXPECT_C0}; re-snapshot required"}))
        return 3
    candidate_text = canonical_text
    for old, new, label in ((OLD_BULLET, NEW_BULLET, "must_not_conflate[0]"),
                            (OLD_REASON, NEW_REASON, "forbidden_transfers[0].reason")):
        n = candidate_text.count(old)
        if n != 1:
            print(json.dumps({"verdict": "FAIL-CLOSED",
                              "detail": f"expected exactly 1 occurrence of {label}, found {n}"}))
            return 3
        candidate_text = candidate_text.replace(old, new, 1)

    # exact unified diff
    diff = list(difflib.unified_diff(canonical_text.splitlines(keepends=True),
                                     candidate_text.splitlines(keepends=True),
                                     fromfile="schemas/af_scc_c0_vacuum.yaml (canonical rev11)",
                                     tofile="candidate/af_scc_c0_vacuum.yaml (2-edit repair)"))
    changed = [ln for ln in diff if (ln.startswith("+") or ln.startswith("-"))
               and not ln.startswith(("+++", "---"))]
    (ROOT / "evidence").mkdir(exist_ok=True)
    (ROOT / "evidence" / "minimality_diff.txt").write_text("".join(diff))

    # structural diff of parsed YAML
    a = yaml.safe_load(canonical_text)
    b = yaml.safe_load(candidate_text)
    changed_paths = struct_diff(a, b)
    # account for the duplicate revised_at keys: safe_load drops earlier ones, so
    # compare the raw changed-line count too
    ok = ({p for p, _ in changed_paths} == EXPECTED_PATHS and len(changed) == 4)
    report = {
        "task_id": "W008-F2B-DUALREPAIR-01",
        "canonical": {"path": str(CANONICAL.relative_to(ROOT_REPO)),
                      "sha256": got, "bytes": len(canonical_text.encode())},
        "candidate": {"path": "candidate/af_scc_c0_vacuum.yaml",
                      "sha256": sha256_text(candidate_text),
                      "bytes": len(candidate_text.encode())},
        "edits": [
            {"yaml_path": "regularity.must_not_conflate[0]",
             "change": "removes the false 'No containment with C2 or C0 is asserted here' denial; "
                       "states the declared nesting and keeps the 'do not cite strictly between' "
                       "warning; mirrors the already-corrected C2 sibling wording"},
            {"yaml_path": "implication_ledger.forbidden_transfers[0].reason",
             "change": "'C2 is a strictly larger extension class' -> 'C2 is a strictly smaller "
                       "extension class (E_C2 subset of E_C0)'; transfer direction and strength "
                       "consequent unchanged"},
        ],
        "unified_diff_changed_lines": len(changed),
        "structural_changed_leaf_paths": [p for p, _ in changed_paths],
        "structural_change_set_equals_expected": {p for p, _ in changed_paths} == EXPECTED_PATHS,
        "binding_fields_unchanged": {
            "f0_binding": a.get("f0_binding") == b.get("f0_binding"),
            "class_contract_pointer": a.get("class_contract_pointer") == b.get("class_contract_pointer"),
            "class_id": a.get("class_id") == b.get("class_id"),
            "revision": a.get("revision") == b.get("revision"),
        },
        "minimality_verdict": "PASS" if ok else "FAIL",
        "note": "revision/re-frozen metadata is owner-owned and deliberately untouched: the "
                "candidate is a byte-minimal wording patch on the frozen rev11 text.",
        "falsifier": "A structural change outside the two declared YAML paths, or a candidate "
                     "hash equal to the canonical hash, or any change to f0_binding/"
                     "class_contract_pointer/class_id/revision falsifies minimality.",
    }
    (ROOT / "candidate").mkdir(exist_ok=True)
    (ROOT / "candidate" / "af_scc_c0_vacuum.yaml").write_text(candidate_text)
    (ROOT / "evidence" / "minimality_report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print(json.dumps(report, indent=1, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
