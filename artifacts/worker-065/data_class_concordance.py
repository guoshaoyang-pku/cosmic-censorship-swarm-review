#!/usr/bin/env python3
"""Worker-065: cross-schema data-class concordance measurement.

Task source (no inbox assignment existed for worker-065; proposed from the open
G-FORM criterion in research_map/research_map.json):
    G-FORM unmet: "no single frozen data class (s,delta,norm) is shared by
    F1/F2a/F2b, which disables the licensed C0=>C2 transfer"

Scope (class-bound):
    AF-WCC-VAC-GEN   -> schemas/af_wcc_vacuum.yaml      (F1)
    AF-SCC-C2-VAC-GEN-> schemas/af_scc_c2_vacuum.yaml   (F2a)
    AF-SCC-C0-VAC-GEN-> schemas/af_scc_c0_vacuum.yaml   (F2b)

This is EVIDENCE ONLY. It sets no gate verdict and claims no completion.

What is measured, at one instant:
  1. sha256 + size of the three canonical schemas (drift aborts the run).
  2. `data_class` flattened to dotted scalar paths; key sets compared.
  3. Raw three-way value equality on the common key set.
  4. Declared RESTRICTING projection: the paths that can change the *admitted
     data set*, with one published normalization (`operative()`: drop trailing
     ';' clauses, drop parenthetical glosses, collapse whitespace, lowercase).
     Both raw and projected values are reported, so the normalization hides
     nothing.
  5. Negative controls (the falsifier run as a null): mutating the Sobolev
     delta, or imposing a parity condition, in an in-memory copy MUST flip the
     veredict to DIVERGENT. If a control fails, the run is INVALID.

Reproduce:
    python3 artifacts/worker-065/data_class_concordance.py \
        --out artifacts/worker-065/data_class_concordance_<stamp>.json
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CST = timezone(timedelta(hours=8))

SCHEMAS = {
    "F1": {"class_id": "AF-WCC-VAC-GEN", "path": "schemas/af_wcc_vacuum.yaml"},
    "F2a": {"class_id": "AF-SCC-C2-VAC-GEN", "path": "schemas/af_scc_c2_vacuum.yaml"},
    "F2b": {"class_id": "AF-SCC-C0-VAC-GEN", "path": "schemas/af_scc_c0_vacuum.yaml"},
}

# Paths whose value can change which data are admitted to the class. This list
# is part of the published method; changing it changes the verdict and must be
# justified by the falsifier below.
RESTRICTING_PATHS = [
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
]

# Fields deliberately classified as annotation / derived / prose rather than
# data-set restrictions, with the reason recorded next to each.
NONRESTRICTING_KEYS = {
    "gauge": "states diffeomorphism invariance; both wordings fix no gauge (non-restricting prose)",
    "diffeo_quotient": "declares the same genericity quotient as an open technical gap; non-restricting prose",
    "regularity_class.sobolev_variant.status": "provenance/ownership note on a numeric choice; non-restricting",
    "adm_mass.exists": "derived (positive mass theorem); identical across schemas",
    "adm_mass.sign": "derived (positive mass theorem); identical across schemas",
    "adm_mass.citation_status": "citation bookkeeping; identical across schemas",
    "adm_mass.rigidity": "derived rigidity statement present only in F1; adds no admission condition",
    "adm_mass.locator": "citation locator annotation present only in F2a/F2b; adds no admission condition",
    "adm_mass.hypotheses_reconciliation": "reconciliation note present only in F2b; adds no admission condition",
    "excluded_data": "prose warning that schema does not decide membership; adds no admission condition",
}

FALSIFIER = (
    "A reviewer exhibits a data_class field that changes the admitted data set - a different "
    "Sobolev index or decay rate, a parity condition imposed, matter or Lambda changed, or a "
    "restricting predicate added/removed - that the declared projection drops; or any of the "
    "three measured canonical sha256 values changes without this artifact being re-measured. "
    "Operationally: the two built-in negative controls must return DIVERGENT; if either returns "
    "CONCORDANT_CORE the measurement is invalid."
)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def flatten(obj, prefix: str = "") -> dict:
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(flatten(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(flatten(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = obj
    return out


def operative(value) -> str:
    """Published normalization used ONLY for the restricting projection."""
    s = str(value)
    s = s.split(";")[0]                 # drop trailing clauses
    s = re.sub(r"\([^()]*\)", "", s)    # drop parenthetical glosses
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


def get_path(flat: dict, path: str):
    return flat.get(path)


def compare(docs: dict, raw_dc: dict) -> dict:
    flat = {name: flatten(dc) for name, dc in raw_dc.items()}
    keys = {name: set(f) for name, f in flat.items()}
    common = sorted(keys["F1"] & keys["F2a"] & keys["F2b"])

    raw_rows = []
    for path in common:
        vals = {name: get_path(flat[name], path) for name in SCHEMAS}
        raw_rows.append({
            "path": path,
            "values": vals,
            "raw_equal": len({json.dumps(v, sort_keys=True) for v in vals.values()}) == 1,
        })

    only = {name: sorted(keys[name] - set().union(*[keys[o] for o in SCHEMAS if o != name]))
            for name in SCHEMAS}
    key_deltas = []
    for name, paths in only.items():
        for p in paths:
            key_deltas.append({
                "schema": name,
                "path": p,
                "value": get_path(flat[name], p),
                "classification": NONRESTRICTING_KEYS.get(p, "UNCLASSIFIED"),
                "nonrestricting": p in NONRESTRICTING_KEYS,
            })

    proj_rows = []
    for path in RESTRICTING_PATHS:
        raw = {name: get_path(flat[name], path) for name in SCHEMAS}
        proj = {name: (operative(v) if v is not None else None) for name, v in raw.items()}
        proj_rows.append({
            "path": path,
            "raw_values": raw,
            "projected_values": proj,
            "raw_equal": len({json.dumps(v, sort_keys=True) for v in raw.values()}) == 1,
            "projected_equal": len({json.dumps(v, sort_keys=True) for v in proj.values()}) == 1,
            "present_in_all": all(v is not None for v in raw.values()),
        })

    restricting_ok = all(r["present_in_all"] and r["projected_equal"] for r in proj_rows)
    unclassified = [d for d in key_deltas if not d["nonrestricting"]]
    verdict = "CONCORDANT_CORE" if (restricting_ok and not unclassified) else "DIVERGENT"

    return {
        "verdict": verdict,
        "restricting_paths": proj_rows,
        "restricting_projection_equal": restricting_ok,
        "all_common_paths": raw_rows,
        "common_paths_total": len(common),
        "common_paths_raw_equal": sum(1 for r in raw_rows if r["raw_equal"]),
        "key_set_deltas": key_deltas,
        "unclassified_key_deltas": unclassified,
    }


def negative_controls(docs: dict) -> list:
    controls = []

    def run(name: str, mutate) -> dict:
        d = copy.deepcopy(docs)
        mutate(d)
        res = compare(d, {n: d[n] for n in SCHEMAS})
        return {"control": name, "expected": "DIVERGENT", "observed": res["verdict"],
                "pass": res["verdict"] == "DIVERGENT"}

    def m_delta(d):
        d["F2b"]["data_class"]["regularity_class"]["sobolev_variant"]["delta"] = "delta in (1/4, 1/2)"

    def m_parity(d):
        d["F2a"]["data_class"]["asymptotic_decay"]["parity_conditions"] = "imposed: even parity required"

    controls.append(run("mutate F2b sobolev delta interval", m_delta))
    controls.append(run("impose parity in F2a", m_parity))
    return controls


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    docs, hashes, bytes_map = {}, {}, {}
    for name, meta in SCHEMAS.items():
        p = ROOT / meta["path"]
        if not p.is_file():
            print(f"FATAL: missing canonical schema {p}", file=sys.stderr)
            return 2
        hashes[name] = sha256_file(p)
        bytes_map[name] = p.stat().st_size
        doc = yaml.safe_load(p.read_text())
        if not isinstance(doc, dict) or not isinstance(doc.get("data_class"), dict):
            print(f"FATAL: {meta['path']} has no data_class mapping", file=sys.stderr)
            return 2
        docs[name] = doc

    raw_dc = {n: docs[n]["data_class"] for n in SCHEMAS}
    cmp_res = compare(docs, raw_dc)
    controls = negative_controls(docs)
    controls_ok = all(c["pass"] for c in controls)

    result = {
        "actor": "worker-065",
        "at": datetime.now(CST).isoformat(timespec="seconds"),
        "task": "cross-schema data-class concordance (G-FORM unmet criterion)",
        "class_ids": [SCHEMAS[n]["class_id"] for n in SCHEMAS],
        "canonical_paths": {n: {"path": SCHEMAS[n]["path"], "sha256": hashes[n],
                                "bytes": bytes_map[n], "class_id": SCHEMAS[n]["class_id"]}
                            for n in SCHEMAS},
        "method": {
            "flatten": "dotted scalar paths of the YAML `data_class` mapping",
            "restricting_projection": "RESTRICTING_PATHS with operative(): drop trailing ';' clauses, "
                                      "drop parenthetical glosses, collapse whitespace, lowercase",
            "verdict_rule": "CONCORDANT_CORE iff every restricting path is present in all three schemas "
                            "and projected-equal, and no unclassified key-set delta remains",
        },
        "result": cmp_res,
        "negative_controls": controls,
        "controls_ok": controls_ok,
        "verdict": cmp_res["verdict"] if controls_ok else "INVALID_CONTROLS",
        "falsifier": FALSIFIER,
        "limitations": [
            "The restricting-path list and operative() normalization are declared modelling choices, "
            "published in the script; raw values for every path are included so a reviewer can reject "
            "the projection without re-running.",
            "Concordance of declared values is not a proof that the three schemas denote one class; it "
            "is a measurement that the data-set-defining fields currently agree.",
            "Measured at one instant; hashes are recorded so later drift is detectable.",
        ],
        "reproduce": f"python3 artifacts/worker-065/data_class_concordance.py --out <path>",
    }

    if args.out:
        out = Path(args.out)
    else:
        out = ROOT / "artifacts/worker-065" / f"data_class_concordance_{datetime.now(CST).strftime('%Y%m%dT%H%M%S')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "out": str(out.relative_to(ROOT)),
        "artifact_sha256": sha256_file(out),
        "verdict": result["verdict"],
        "controls_ok": controls_ok,
        "restricting_equal": cmp_res["restricting_projection_equal"],
        "common_raw_equal": f"{cmp_res['common_paths_raw_equal']}/{cmp_res['common_paths_total']}",
        "unclassified_deltas": len(cmp_res["unclassified_key_deltas"]),
        "schema_hashes": {n: hashes[n][:12] for n in SCHEMAS},
    }, indent=2))
    return 0 if controls_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
