#!/usr/bin/env python3
"""W068-CLASSBIND-XSCOPE-16 runner (worker-068, bounded class-bound task).

Cross-artifact axis-level disjointness/freeze consistency census for the four frozen
formulation classes. Read-only on every canonical path; the only writes are this task's
own artifacts under artifacts/worker-068/xscope16/.

Rules R1-R6, phrase table, predictions and falsifier are fixed in PREREGISTRATION.json
before this runner was first executed.  Fail-closed: exit 2 on any pin drift.

Usage:
  python3 run_xscope16.py            # preflight -> census -> write raw_census/controls/report
  python3 run_xscope16.py --selftest # planted controls only (no canonical read, no writes)
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PREREG = HERE / "PREREGISTRATION.json"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def norm(v):
    """Normalize an axis value for equality comparison (None/null/false are distinct)."""
    if v is None:
        return "__NULL__"
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


# ---------------------------------------------------------------- core checks
def pair_key(a: str, b: str):
    return tuple(sorted((a, b)))


def r2_declared_decisive(axes_by_class: dict, row: dict) -> list:
    a, b = row["pair"]
    cells = []
    for axis in row.get("decisive_axes", []):
        va = axes_by_class.get(a, {}).get(axis, "__ABSENT__")
        vb = axes_by_class.get(b, {}).get(axis, "__ABSENT__")
        if va == "__ABSENT__" or vb == "__ABSENT__":
            verdict = "MISSING_AXIS"
        elif norm(va) != norm(vb):
            verdict = "DIFFERS"
        else:
            verdict = "EQUAL"
        cells.append({"axis": axis, "a": None if va == "__ABSENT__" else va,
                      "b": None if vb == "__ABSENT__" else vb, "verdict": verdict})
    return cells


def r3_undeclared(axes_by_class: dict, row: dict) -> list:
    a, b = row["pair"]
    declared = set(row.get("decisive_axes", []))
    keys = sorted(set(axes_by_class.get(a, {})) | set(axes_by_class.get(b, {})))
    out = []
    for axis in keys:
        if axis in declared:
            continue
        va = axes_by_class.get(a, {}).get(axis)
        vb = axes_by_class.get(b, {}).get(axis)
        if norm(va) != norm(vb):
            out.append({"axis": axis, "a": va, "b": vb})
    return out


def map_basis(basis: str, phrase_table: dict) -> list:
    low = basis.lower()
    axis_set, composites = set(), set()
    # longest phrases first so 'extension regularity token' wins over 'regularity token'
    for phrase in sorted(phrase_table, key=len, reverse=True):
        if phrase in low:
            target = phrase_table[phrase]
            if target == "__composite__":
                composites.add(phrase)
            else:
                axis_set.add(target)
    return sorted(axis_set), sorted(composites)


def r4_basis(declared: list, basis: str, phrase_table: dict) -> dict:
    mapped, composites = map_basis(basis, phrase_table)
    d, m = set(declared), set(mapped)
    if not m:
        verdict = "EMPTY"
    elif m == d:
        verdict = "SUBSET" if m <= d else "SUPERSET"
    elif m < d:
        verdict = "SUBSET"
    elif m > d:
        verdict = "SUPERSET"
    elif m & d:
        verdict = "CROSS"
    else:
        verdict = "DISJOINT_NONEMPTY"
    return {"basis": basis, "mapped_axes": mapped, "composite_phrases": composites,
            "declared_axes": declared, "verdict": verdict}


def r5_registry(axes_by_class: dict, registry: dict, key_map: dict) -> list:
    out = []
    for reg_key, canonical_axis in key_map.items():
        entry = registry.get(reg_key) or {}
        frozen = entry.get("frozen") or {}
        for cid, frozen_val in sorted(frozen.items()):
            canonical_val = axes_by_class.get(cid, {}).get(canonical_axis, "__ABSENT__")
            if canonical_val == "__ABSENT__":
                verdict = "ABSENT"
            elif norm(frozen_val) == norm(canonical_val):
                verdict = "MATCH"
            else:
                verdict = "TOKEN_DIFFERS"
            out.append({"registry_key": reg_key, "canonical_axis": canonical_axis,
                        "class_id": cid, "frozen_value": frozen_val,
                        "canonical_value": None if canonical_val == "__ABSENT__" else canonical_val,
                        "verdict": verdict})
    return out


# ---------------------------------------------------------------- planted controls
def _census_from_fixture(axes_by_class, canon_rows, supp_rows, registry, phrase_table, key_map):
    canon_rows = [dict(r) for r in canon_rows]
    pairs_c = {pair_key(*r["pair"]) for r in canon_rows}
    pairs_s = {pair_key(r[0], r[1]) for r in supp_rows}
    r1 = {"canonical_pairs": sorted(pairs_c), "supplement_pairs": sorted(pairs_s),
          "missing_in_supplement": sorted(pairs_c - pairs_s),
          "extra_in_supplement": sorted(pairs_s - pairs_c),
          "verdict": "EQUAL" if pairs_c == pairs_s else "PAIR_SET_MISMATCH"}
    basis_by_pair = {pair_key(r[0], r[1]): r[2] for r in supp_rows}
    rows = []
    for r in canon_rows:
        cells = r2_declared_decisive(axes_by_class, r)
        rows.append({"pair": r["pair"], "decisive_axes": r.get("decisive_axes", []),
                     "cells": cells,
                     "undeclared_separators": r3_undeclared(axes_by_class, r),
                     "basis": r4_basis(r.get("decisive_axes", []),
                                       basis_by_pair.get(pair_key(*r["pair"]), ""), phrase_table)})
    return {"R1": r1, "rows": rows, "R5": r5_registry(axes_by_class, registry, key_map)}


def selftest(phrase_table) -> int:
    key_map = {"regularity_axis": "regularity_token", "genericity_axis": "genericity_kind"}
    results = []

    def check(cid, ok, detail):
        results.append({"control": cid, "pass": bool(ok), "detail": detail})

    # K1: declared decisive axis with equal values -> EQUAL
    fx = _census_from_fixture({"A": {"x": 1}, "B": {"x": 1}},
                              [{"pair": ["A", "B"], "decisive_axes": ["x"]}],
                              [["A", "B", "x"]], {}, phrase_table, key_map)
    check("K1", any(c["verdict"] == "EQUAL" for c in fx["rows"][0]["cells"]),
          "declared-but-equal axis fires EQUAL")

    # K2: all declared axes differ -> DIFFERS
    fx = _census_from_fixture({"A": {"x": 1, "y": 2}, "B": {"x": 3, "y": 4}},
                              [{"pair": ["A", "B"], "decisive_axes": ["x", "y"]}],
                              [["A", "B", "x and y"]], {}, phrase_table, key_map)
    check("K2", all(c["verdict"] == "DIFFERS" for c in fx["rows"][0]["cells"]),
          "all declared axes differ -> DIFFERS")

    # K3: differing undeclared axis -> UNDECLARED_SEPARATOR
    fx = _census_from_fixture({"A": {"x": 1, "z": 1}, "B": {"x": 2, "z": 9}},
                              [{"pair": ["A", "B"], "decisive_axes": ["x"]}],
                              [["A", "B", "x"]], {}, phrase_table, key_map)
    check("K3", [u["axis"] for u in fx["rows"][0]["undeclared_separators"]] == ["z"],
          "undeclared differing axis recorded")

    # K4: basis names an axis outside the declared set -> SUPERSET
    fx = _census_from_fixture({"A": {"symmetry": 1, "matter_model": 1},
                               "B": {"symmetry": 2, "matter_model": 2}},
                              [{"pair": ["A", "B"], "decisive_axes": ["symmetry"]}],
                              [["A", "B", "symmetry and matter"]], {}, phrase_table, key_map)
    check("K4", fx["rows"][0]["basis"]["verdict"] == "SUPERSET",
          "basis superset of declared axes fires SUPERSET")

    # K5: pair missing in supplement -> PAIR_SET_MISMATCH
    fx = _census_from_fixture({"A": {"x": 1}, "B": {"x": 2}, "C": {"x": 3}},
                              [{"pair": ["A", "B"], "decisive_axes": ["x"]},
                               {"pair": ["A", "C"], "decisive_axes": ["x"]}],
                              [["A", "B", "x"]], {}, phrase_table, key_map)
    check("K5", fx["R1"]["verdict"] == "PAIR_SET_MISMATCH"
          and fx["R1"]["missing_in_supplement"] == [("A", "C")],
          "missing supplement pair detected")

    # K6: registry token mismatch -> TOKEN_DIFFERS
    fx = _census_from_fixture({"A": {"genericity_kind": "provisional_baire_residual"}},
                              [{"pair": ["A", "A"], "decisive_axes": ["genericity_kind"]}],
                              [["A", "A", "nothing"]],
                              {"genericity_axis": {"frozen": {"A": "residual_comeager"}}},
                              phrase_table, key_map)
    check("K6", any(r["verdict"] == "TOKEN_DIFFERS" for r in fx["R5"]),
          "registry-vs-canonical token mismatch detected")

    print(json.dumps({"controls": results,
                      "passed": sum(r["pass"] for r in results), "total": len(results)}, indent=1))
    return 0 if all(r["pass"] for r in results) else 3


# ---------------------------------------------------------------- main
def main() -> int:
    prereg = json.loads(PREREG.read_text())
    phrase_table = prereg["phrase_table"]

    if "--selftest" in sys.argv:
        return selftest(phrase_table)

    pins = prereg["pins"]
    measured, drift = {}, []
    for rel, meta in pins.items():
        p = ROOT / rel
        got = {"sha256": sha256_file(p), "bytes": p.stat().st_size}
        measured[rel] = got
        if got["sha256"] != meta["sha256"] or got["bytes"] != meta["bytes"]:
            drift.append({"path": rel, "registered": meta, "measured": got})
    if drift:
        print(json.dumps({"exit": 2, "reason": "PIN_DRIFT", "drift": drift}, indent=1))
        return 2

    canon = yaml.safe_load((ROOT / "research_map/formulation_taxonomy.yaml").read_text())
    supp = yaml.safe_load((ROOT / "artifacts/formulation/formulation_taxonomy.yaml").read_text())

    class_ids = canon["class_ids"]
    axes_by_class = {cid: (canon["classes"][cid].get("axes") or {}) for cid in class_ids}
    gen_status = {cid: canon["classes"][cid].get("genericity_value_status") for cid in class_ids}

    canon_rows = canon["disjointness"]
    supp_pairs = supp["disjointness_matrix"]["pairwise"]
    registry = supp["axis_registry"]
    key_map = {"regularity_axis": "regularity_token", "genericity_axis": "genericity_kind"}

    census = _census_from_fixture(axes_by_class, canon_rows, supp_pairs, registry,
                                  phrase_table, key_map)

    # ---- predictions
    preds = []
    for p in prereg["predictions"]:
        pid = p["id"]
        if pid == "P1":
            ok = census["R1"]["verdict"] == "EQUAL"
        elif pid == "P2":
            ok = all(c["verdict"] == "DIFFERS"
                     for row in census["rows"] for c in row["cells"])
        elif pid == "P3":
            ok = any(row["undeclared_separators"] for row in census["rows"])
        elif pid == "P4":
            hits = [r for r in census["R5"] if r["verdict"] == "TOKEN_DIFFERS"
                    and r["registry_key"] == "genericity_axis"]
            ok = len(hits) == 3 and all(r["frozen_value"] == "residual_comeager"
                                        and r["canonical_value"] == "provisional_baire_residual"
                                        for r in hits)
        elif pid == "P5":
            ok = all(row["basis"]["verdict"] in ("SUBSET", "EMPTY") for row in census["rows"])
        elif pid == "P6":
            ok = not any(c["verdict"] == "MISSING_AXIS"
                         for row in census["rows"] for c in row["cells"])
        else:
            ok = None
        preds.append({"id": pid, "prediction": p["prediction"], "matched": ok})

    findings = []
    for row in census["rows"]:
        for c in row["cells"]:
            if c["verdict"] != "DIFFERS":
                findings.append({"id": f"W068-X16-R2-{'-'.join(row['pair'])}-{c['axis']}",
                                 "rule": "R2", "kind": c["verdict"], "pair": row["pair"],
                                 "axis": c["axis"], "a": c["a"], "b": c["b"]})
        for u in row["undeclared_separators"]:
            findings.append({"id": f"W068-X16-R3-{'-'.join(row['pair'])}-{u['axis']}",
                             "rule": "R3", "kind": "UNDECLARED_SEPARATOR", "pair": row["pair"],
                             "axis": u["axis"], "a": u["a"], "b": u["b"]})
        if row["basis"]["verdict"] not in ("SUBSET", "EMPTY"):
            findings.append({"id": f"W068-X16-R4-{'-'.join(row['pair'])}", "rule": "R4",
                             "kind": row["basis"]["verdict"], "pair": row["pair"],
                             "basis": row["basis"]})
    for r in census["R5"]:
        if r["verdict"] == "TOKEN_DIFFERS":
            findings.append({"id": f"W068-X16-R5-{r['class_id']}-{r['registry_key']}",
                             "rule": "R5", "kind": "TOKEN_DIFFERS", "registry_key": r["registry_key"],
                             "class_id": r["class_id"], "frozen_value": r["frozen_value"],
                             "canonical_value": r["canonical_value"]})

    raw = {"task_id": "W068-CLASSBIND-XSCOPE-16",
           "measured_pins": measured,
           "class_ids": class_ids,
           "axes_by_class": axes_by_class,
           "genericity_value_status": gen_status,
           "canonical_disjointness": canon_rows,
           "supplement_pairwise": supp_pairs,
           "canonical_disjointness_scope": canon.get("disjointness_scope"),
           "census": census,
           "predictions": preds,
           "findings": findings}

    ctrl_code = selftest(phrase_table)
    controls = {"selftest_exit": ctrl_code}
    if ctrl_code != 0:
        print(json.dumps({"exit": 4, "reason": "CONTROL_FAILURE"}, indent=1))
        return 4

    (HERE / "raw_census.json").write_text(json.dumps(raw, indent=1) + "\n")
    (HERE / "controls.json").write_text(json.dumps(controls, indent=1) + "\n")

    n_cells = sum(len(r["cells"]) for r in census["rows"])
    report = {
        "task_id": "W068-CLASSBIND-XSCOPE-16",
        "actor": "worker-068", "node_id": "A1",
        "gate": prereg["gate"], "class_ids": class_ids,
        "authority": prereg["authority"],
        "created_at": "2026-09-12T01:30:00+08:00",
        "pins": measured,
        "question": prereg["question"],
        "result": {
            "pairs": len(census["rows"]),
            "axis_cells": n_cells,
            "R1_verdict": census["R1"]["verdict"],
            "R2": {v: sum(1 for r in census["rows"] for c in r["cells"] if c["verdict"] == v)
                   for v in ("DIFFERS", "EQUAL", "MISSING_AXIS")},
            "R3_undeclared_separators": sum(len(r["undeclared_separators"]) for r in census["rows"]),
            "R4_verdicts": {r["pair"][0] + "|" + r["pair"][1]: r["basis"]["verdict"]
                            for r in census["rows"]},
            "R5_verdicts": {r["class_id"] + "|" + r["registry_key"]: r["verdict"]
                            for r in census["R5"]},
            "predictions_matched": {p["id"]: p["matched"] for p in preds},
            "findings": findings,
        },
        "falsifier": prereg["falsifier"],
        "non_claims": prereg["non_claims"],
        "artifact_hashes": {
            "PREREGISTRATION.json": sha256_file(PREREG),
            "run_xscope16.py": sha256_file(Path(__file__).resolve()),
        },
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=1) + "\n")

    print(json.dumps({"exit": 0, "pairs": len(census["rows"]), "axis_cells": n_cells,
                      "R1": census["R1"]["verdict"], "R2": report["result"]["R2"],
                      "R3": report["result"]["R3_undeclared_separators"],
                      "R4": report["result"]["R4_verdicts"],
                      "R5": report["result"]["R5_verdicts"],
                      "predictions": report["result"]["predictions_matched"],
                      "findings": len(findings)}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
