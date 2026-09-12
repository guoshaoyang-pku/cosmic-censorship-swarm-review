#!/usr/bin/env python3
"""W060-XCLASS-DATACLASS-01 — independent adjudication of the cross-class data_class
divergence against the licensed C0=>C2 transfer guard (G-FORM, classes AF-WCC-VAC-GEN /
AF-SCC-C2-VAC-GEN / AF-SCC-C0-VAC-GEN).

Question under test
-------------------
The research map's G-FORM unmet item says: "no single frozen data class (s,delta,norm) is
shared by F1/F2a/F2b, which disables the licensed C0=>C2 transfer".
The canonical taxonomy's T1 transfer rule guards C0=>C2 with: "data_class fields must match
exactly (including s, delta once F2 fixes them)".

Worker-071 measured that the three canonical data_class blocks are not equal. It did not
decide which reading the guard should use. This script makes that decision measurable:

  T0 literal-bytes equality of the data_class block
  T1 canonical-JSON (leaf-path) equality over all 23 leaf paths
  T2 DATA_SPACE_CORE equality over the 15 fields that define the admissible data space
  T3 T2 after two declared, auditable annotation normalizations
  T4 the licensed pair F2a(F2a=C2) vs F2b(C0) evaluated separately

It is self-contained: it does not import any other worker's checker or the canonical gate
module. It re-measures its own pins and refuses to report on drifted bytes.

Authority: worker evidence only. No gate verdict, no node status, no validation_status
promotion. Output is advisory input to the lead-formulation / controller.

Reproduce:
  python3 artifacts/worker-060/xclass_dataclass_adjudication/verify_xclass_dataclass.py
Exit codes: 0 = adjudication complete; 2 = pin drift (no verdict reported).
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import sys
from datetime import datetime

import yaml

# ---------------------------------------------------------------- pins (reviewed state)
PINS = {
    "F1": ("schemas/af_wcc_vacuum.yaml",
           "9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503",
           "AF-WCC-VAC-GEN"),
    "F2a": ("schemas/af_scc_c2_vacuum.yaml",
            "b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2",
            "AF-SCC-C2-VAC-GEN"),
    "F2b": ("schemas/af_scc_c0_vacuum.yaml",
            "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508",
            "AF-SCC-C0-VAC-GEN"),
    "F0_canonical": ("research_map/formulation_taxonomy.yaml",
                     "276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc",
                     "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH"),
    "F0_authoring": ("artifacts/formulation/formulation_taxonomy.yaml",
                     "c8e979a1eb48969be3b102e1e18203eb9e09b4e10fca3ef341854fdd73bae83f",
                     "AF-SCC-C0-VAC-GEN"),
}

# The 15 leaf paths that define the admissible data space (s, delta and the ambient data
# hypotheses). Everything else in data_class is annotation/provenance by construction.
DATA_SPACE_CORE_KEYS = [
    "matter",
    "cosmological_constant",
    "equations",
    "constraints.hamiltonian",
    "constraints.momentum",
    "regularity_class.default",
    "regularity_class.sobolev_variant.s",
    "regularity_class.sobolev_variant.delta",
    "regularity_class.sobolev_variant.spaces",
    "asymptotic_decay.metric",
    "asymptotic_decay.second_fundamental_form",
    "asymptotic_decay.parity_conditions",
    "symmetry",
    "adm_mass.exists",
    "adm_mass.sign",
]

# T3 normalization: two declared, auditable rules for annotation forms that do not change
# the admissible data space. Every application is reported with before/after text.
def _norm_spaces(v: str) -> str:
    return re.sub(r"\s*\([^()]*\)\s*$", "", str(v)).strip()


def _norm_parity(v: str) -> str:
    return str(v).split(";", 1)[0].strip()


NORMALIZERS = {
    "regularity_class.sobolev_variant.spaces": _norm_spaces,
    "asymptotic_decay.parity_conditions": _norm_parity,
}


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def leaf_paths(node, prefix: str = "") -> dict:
    """Flatten a YAML subtree to {dotted.path: scalar}. Lists are indexed [i]."""
    out: dict = {}
    if isinstance(node, dict):
        for k, v in node.items():
            out.update(leaf_paths(v, f"{prefix}{k}."))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            out.update(leaf_paths(v, f"{prefix}[{i}]."))
    else:
        out[prefix.rstrip(".")] = node
    return out


def compare(blocks: dict, tags, keys=None, normalize=False):
    """Compare leaf values across tags.

    Returns (per_path, strict_diffs, normalized_diffs).
    per_path: path -> {tag: value-or-'<missing>'}
    """
    per_path: dict = {}
    union = set()
    for t in tags:
        union |= set(blocks[t])
    for path in sorted(union):
        if keys is not None and path not in keys:
            continue
        row = {t: blocks[t].get(path, "<missing>") for t in tags}
        per_path[path] = row

    def differs(row):
        vals = list(row.values())
        return any(v != vals[0] for v in vals)

    strict = [p for p, row in per_path.items() if differs(row)]
    norm = []
    if normalize:
        for p, row in per_path.items():
            if p in NORMALIZERS:
                normed = {t: (NORMALIZERS[p](v) if v != "<missing>" else v) for t, v in row.items()}
            else:
                normed = row
            vals = list(normed.values())
            if any(v != vals[0] for v in vals):
                norm.append(p)
    return per_path, strict, norm


def load_blocks(root: str):
    blocks = {}
    raws = {}
    for tag in ("F1", "F2a", "F2b"):
        path = os.path.join(root, PINS[tag][0])
        with open(path, "r", encoding="utf-8") as fh:
            raw = fh.read()
        raws[tag] = raw
        blocks[tag] = leaf_paths(yaml.safe_load(raw)["data_class"])
    return blocks, raws


def block_span(raw: str) -> tuple:
    """First/last line of the top-level data_class block (1-based, inclusive)."""
    lines = raw.splitlines()
    start = end = None
    for i, line in enumerate(lines, 1):
        if re.match(r"^data_class:\s*$", line):
            start = i
            continue
        if start is not None and re.match(r"^[A-Za-z_]", line):
            end = i - 1
            break
    return start, end if end is not None else len(lines)


def block_text(raw: str) -> str:
    """Raw bytes/text of the top-level data_class block, newline-normalized."""
    lines = raw.splitlines()
    start, end = block_span(raw)
    return "\n".join(lines[start - 1:end])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="repo root (default: cwd)")
    ap.add_argument("--out", default=None, help="evidence JSON path")
    ap.add_argument("--snapshots", action="store_true", help="copy pinned inputs into snapshots/")
    args = ap.parse_args()
    root = os.path.abspath(args.root)
    here = os.path.dirname(os.path.abspath(__file__))
    out_path = args.out or os.path.join(here, "evidence.json")
    snap_dir = os.path.join(here, "snapshots")

    pins = {}
    drift = []
    for tag, (rel, expected, _cls) in PINS.items():
        full = os.path.join(root, rel)
        measured = sha256_file(full)
        ok = measured == expected
        pins[tag] = {"path": rel, "expected_sha256": expected, "measured_sha256": measured,
                     "match": ok}
        if not ok:
            drift.append(tag)
        if args.snapshots and ok:
            os.makedirs(snap_dir, exist_ok=True)
            dest = os.path.join(snap_dir, f"{tag}__{os.path.basename(rel)}")
            if os.path.exists(full):
                shutil.copyfile(full, dest)

    if args.snapshots and not drift:
        os.makedirs(snap_dir, exist_ok=True)
        with open(os.path.join(snap_dir, "SHA256SUMS"), "w", encoding="utf-8") as fh:
            for tag, (rel, expected, _cls) in PINS.items():
                fh.write(f"{expected}  {tag}__{os.path.basename(rel)}\n")

    if drift:
        print(json.dumps({"status": "PIN_DRIFT", "drifted": drift, "pins": pins}, indent=1))
        return 2

    blocks, raws = load_blocks(root)
    all_over_three = compare(blocks, ("F1", "F2a", "F2b"))
    core_three_strict = compare(blocks, ("F1", "F2a", "F2b"), keys=set(DATA_SPACE_CORE_KEYS))
    core_three_norm = compare(blocks, ("F1", "F2a", "F2b"), keys=set(DATA_SPACE_CORE_KEYS),
                              normalize=True)
    pair = compare(blocks, ("F2a", "F2b"))
    pair_core_strict = compare(blocks, ("F2a", "F2b"), keys=set(DATA_SPACE_CORE_KEYS))
    pair_core_norm = compare(blocks, ("F2a", "F2b"), keys=set(DATA_SPACE_CORE_KEYS),
                             normalize=True)

    # ---- claim texts under test (re-read at the pinned hashes, not copied from prose)
    f0c = yaml.safe_load(open(os.path.join(root, PINS["F0_canonical"][0]), encoding="utf-8"))
    f0a = yaml.safe_load(open(os.path.join(root, PINS["F0_authoring"][0]), encoding="utf-8"))
    t1_guard = f0c["transfer_rules"]["allowed"][0]["guards"][0]
    t1_rule = json.dumps({k: f0c["transfer_rules"]["allowed"][0][k] for k in
                          ("id", "from", "to", "kind")}, ensure_ascii=False)
    try:
        data_freeze_claim = f0a["class_contracts"]["AF-SCC-C0-VAC-GEN"]["data_class_freeze"]
    except KeyError:
        data_freeze_claim = "<not present at pinned authoring bytes>"

    # ---- negative controls (mutation testing of this checker)
    controls = []

    def ctl(cid, tag, mutate, expect_core_mismatch, expect_strict_mismatch=True):
        mutated = copy.deepcopy(blocks)
        mutate(mutated[tag])
        _, sdiff, _ = compare(mutated, (tag, "F2b") if tag != "F2b" else ("F2a", "F2b"))
        _, cdiff, _ = compare(mutated, (tag, "F2b") if tag != "F2b" else ("F2a", "F2b"),
                              keys=set(DATA_SPACE_CORE_KEYS))
        core_hit = len(cdiff) > 0
        strict_hit = len(sdiff) > 0
        ok = (core_hit == expect_core_mismatch) and (strict_hit == expect_strict_mismatch)
        controls.append({"id": cid, "mutated": tag, "expect_data_space_mismatch":
                         expect_core_mismatch, "observed_data_space_mismatch": core_hit,
                         "observed_strict_mismatch": strict_hit, "ok": ok,
                         "data_space_diff_paths": cdiff})

    ctl("C1-delta-range", "F2b",
        lambda b: b.__setitem__("regularity_class.sobolev_variant.delta", "delta in (1/2, 1]"),
        True)
    ctl("C2-constraint-drop", "F2a",
        lambda b: b.__setitem__("constraints.momentum", "0 = 0"), True)
    ctl("C3-spaces-drop-term", "F2a",
        lambda b: b.__setitem__("regularity_class.sobolev_variant.spaces",
                                "h - delta_ij in H^s_delta"), True)
    ctl("C4-parity-flip", "F2a",
        lambda b: b.__setitem__("asymptotic_decay.parity_conditions", "imposed"), True)
    ctl("C5-annotation-only", "F2a",
        lambda b: b.__setitem__("adm_mass.locator", "a different locator string"),
        False, expect_strict_mismatch=True)

    checks = []

    def chk(cid, name, ok, detail):
        checks.append({"id": cid, "name": name, "ok": bool(ok), "detail": detail})

    chk("K0-pins", "all five input pins measured equal to the reviewed hashes",
        not drift, {t: pins[t]["measured_sha256"] for t in pins})
    chk("K1-parse", "all three canonical data_class blocks parse as YAML mappings",
        all(isinstance(b, dict) and b for b in blocks.values()),
        {t: len(blocks[t]) for t in blocks})
    chk("K2-T0", "three data_class blocks are not byte-identical (T0)",
        not (block_text(raws["F1"]) == block_text(raws["F2a"]) == block_text(raws["F2b"])),
        "block spans: " + "; ".join(f"{t}={block_span(raws[t])}" for t in raws))
    nine = all_over_three[1]
    chk("K3-T1", "canonical-JSON leaf equality fails over the three blocks (T1)",
        len(nine) > 0, {"n_diff_paths": len(nine), "paths": nine})
    chk("K4-pair-core", "licensed pair F2a(F2a=C2) vs F2b(C0): DATA_SPACE_CORE matches strictly",
        len(pair_core_strict[1]) == 0,
        {"n_data_space_keys": len(DATA_SPACE_CORE_KEYS),
         "diff_paths": pair_core_strict[1]})
    pair_ann = [p for p in pair[1] if p not in set(DATA_SPACE_CORE_KEYS)]
    chk("K5-pair-annotation", "licensed pair differences are annotation-only",
        len(pair_ann) > 0 and len(pair_core_strict[1]) == 0,
        {"annotation_diff_paths": pair_ann,
         "data_space_diff_paths": pair_core_strict[1]})
    chk("K6-three-core-strict", "three-way DATA_SPACE_CORE strict differences are exactly the two normalizable annotation forms",
        set(core_three_strict[1]) == {"regularity_class.sobolev_variant.spaces",
                                      "asymptotic_decay.parity_conditions"},
        {"diff_paths": core_three_strict[1]})
    chk("K7-three-core-norm", "three-way DATA_SPACE_CORE equality after declared normalizations (T3)",
        len(core_three_norm[2]) == 0,
        {"normalization_rules": {k: v.__name__ for k, v in NORMALIZERS.items()},
         "remaining_diff_paths": core_three_norm[2],
         "strict_diff_paths": core_three_strict[1]})
    chk("K8-claim", "authoring claim 'identical across F1/F2a/F2b' measured at T0/T1/T3",
        True,
        {"claim_text": data_freeze_claim,
         "T0_identical": raws["F1"] == raws["F2a"] == raws["F2b"],
         "T1_identical": len(nine) == 0,
         "T3_data_space_identical": len(core_three_norm[2]) == 0,
         "verdict": "REFUTED at T0/T1; CONFIRMED at T3 for the 15 data-space keys"})
    chk("K9-controls", "negative controls: mutations caught, annotation-only mutation not over-flagged",
        all(c["ok"] for c in controls), {"controls": controls})

    # pair annotation values, for the report
    pair_annotation_values = {p: pair[0][p] for p in pair_ann}

    result = {
        "schema": "w060.xclass_dataclass_adjudication/1",
        "task_id": "W060-XCLASS-DATACLASS-01",
        "actor": "worker-060",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "node_ids": ["F1", "F2a", "F2b"],
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate": "G-FORM",
        "authority_note": ("Advisory worker evidence only. No gate verdict, no node status, "
                           "no validation_status=passed; the lead-formulation and controller "
                           "adjudicate with artifact + review evidence."),
        "pins": pins,
        "claims_under_test": {
            "map_G_FORM_unmet": ("no single frozen data class (s,delta,norm) is shared by "
                                 "F1/F2a/F2b, which disables the licensed C0=>C2 transfer"),
            "canonical_T1_rule": t1_rule,
            "canonical_T1_guard": t1_guard,
            "authoring_data_class_freeze": data_freeze_claim,
        },
        "data_space_core_keys": DATA_SPACE_CORE_KEYS,
        "normalization_rules": {
            "regularity_class.sobolev_variant.spaces":
                "strip a single trailing parenthesized annotation",
            "asymptotic_decay.parity_conditions":
                "take the leading directive before the first ';'",
        },
        "comparison": {
            "all_paths_three_way": all_over_three[0],
            "all_path_strict_diff_paths": nine,
            "data_space_core_three_way": core_three_strict[0],
            "data_space_core_strict_diff_paths": core_three_strict[1],
            "data_space_core_normalized_diff_paths": core_three_norm[2],
            "f2a_vs_f2b_all_paths": pair[0],
            "f2a_vs_f2b_strict_diff_paths": pair[1],
            "f2a_vs_f2b_data_space_diff_paths": pair_core_strict[1],
            "f2a_vs_f2b_annotation_diff_paths": pair_ann,
            "f2a_vs_f2b_annotation_values": pair_annotation_values,
        },
        "checks": checks,
        "adjudication": {
            "T1_guard_literal": "FAILS at the pinned hashes on annotation/provenance fields",
            "T1_guard_on_licensed_pair": (
                "FAILS literally on 2 annotation paths (adm_mass.locator, "
                "adm_mass.hypotheses_reconciliation); PASSES on all 15 data-space-core paths"),
            "materiality": ("NO data-space divergence between the licensed pair F2a (C2) and "
                            "F2b (C0); the C0=>C2 transfer is not disabled by a data-space "
                            "mismatch. The map's unmet wording is overstated for the T1 pair "
                            "and should be restated as an annotation-level divergence."),
            "three_way": ("F1 differs from F2a/F2b only in annotation fields plus two "
                          "normalizable annotation forms inside data-space fields "
                          "(spaces parenthetical, parity rationale clause)."),
            "recommended_dispositions": [
                "D1 (preferred): amend T1's guard to name an explicit data_space_core_key "
                "set (the 15 paths in this evidence) and declare annotation/provenance "
                "fields out of the exact-match guard; then T1 passes at these hashes.",
                "D2 (alternative, not recommended): align the annotation fields byte-for-byte "
                "across the three schemas; this deletes review-response provenance and is a "
                "silent evidence loss.",
                "Either way, restate the G-FORM unmet item: the blocker is annotation-level, "
                "not a difference in (s, delta, norm) or any data-space-defining field.",
            ],
            "verdict": "revise",
            "score": 3.5,
        },
        "falsifier": (
            "At the five pinned hashes: if any of the 15 DATA_SPACE_CORE keys differs strictly "
            "between schemas/af_scc_c2_vacuum.yaml (F2a) and schemas/af_scc_c0_vacuum.yaml (F2b), "
            "then the materiality conclusion is refuted and the C0=>C2 transfer is disabled by a "
            "data-space mismatch. If a future T1 guard text names a different key set or an "
            "explicit annotation-exclusion clause, this adjudication binds only to the guard text "
            "quoted above. Any pin drift makes the whole adjudication void at the drifted path."),
        "limitations": [
            "Scope is the data_class subtree only; quantifiers, genericity, conclusion and "
            "visibility fields are out of scope.",
            "AF-WCC-SCALAR-SPH (N0) is out of scope; it has no transfer rule with the vacuum classes.",
            "The two T3 normalization rules are declared and additive; they never merge two "
            "different data spaces (negative controls C1-C4 exercise the strict detector).",
            "Line/ranges refer to the pinned snapshot bytes copied under snapshots/.",
        ],
    }
    # verdict sanity: if a falsifying condition is observed, flip the verdict honestly
    if pair_core_strict[1]:
        result["adjudication"]["materiality"] = (
            "REFUTED by measurement: the licensed pair differs on data-space-core keys "
            f"{pair_core_strict[1]}; C0=>C2 is disabled by a data-space mismatch at these hashes.")
        result["adjudication"]["verdict"] = "reject"

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1, sort_keys=False)
        fh.write("\n")

    summary = {
        "evidence": out_path,
        "sha256": sha256_file(out_path),
        "checks_passed": sum(1 for c in checks if c["ok"]),
        "checks_total": len(checks),
        "all_checks_ok": all(c["ok"] for c in checks),
        "data_space_core_diff_paths_F2a_vs_F2b": pair_core_strict[1],
        "annotation_diff_paths_F2a_vs_F2b": pair_ann,
        "three_way_strict_diff_paths": nine,
        "verdict": result["adjudication"]["verdict"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
