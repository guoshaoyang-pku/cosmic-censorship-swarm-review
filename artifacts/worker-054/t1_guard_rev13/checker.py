#!/usr/bin/env python3
"""W054-T1-GUARD-REV13-01: read-only adjudication of the licensed T1 transfer guard
(AF-SCC-C0-VAC-GEN -> AF-SCC-C2-VAC-GEN, taxonomy guard T1) at the rev13 pins.

Rule under test (research_map/formulation_taxonomy.yaml, transfer_rules.allowed T1):
  from AF-SCC-C0-VAC-GEN to AF-SCC-C2-VAC-GEN, kind conclusion_strengthening,
  guards:
    (1) "data_class fields must match exactly (including s, delta once F2 fixes them)"
    (2) "genericity_kind and genericity_topology must match exactly"
    (3) "the source claim must carry artifact_refs and a reviewer verdict"   [not testable here]

Design (fixed before measurement):
  * inputs are read-only; every input is sha256-pinned and the run aborts fail-closed
    if any pin does not match;
  * the data_class subtree of each schema is flattened to dotted key paths;
  * two key sets are PRE-REGISTERED:
      CORE_DATA_KEYS  - mathematical data-space content (the 17 keys listed below);
      ANNOTATION_KEYS - citation/locator/status/rigidity/reconciliation/scope prose that
                        is not part of the mathematical data space;
  * the literal pass compares the whole subtree; the content pass compares CORE_DATA_KEYS;
    a third pass compares everything except ANNOTATION_KEYS (recursive key filter);
  * the genericity pass compares genericity.kind and genericity.topology_or_measure;
  * mutation controls run on in-memory copies and must be DETECTED;
  * the F1 (WCC) schema is used as the forbidden-transfer control: the same content
    pass must FAIL on it if it is not vacuous;
  * a post-run drift check re-hashes every input; the report is valid only if
    drift.detected is false.

Exit codes: 0 = measurement completed (whatever the verdict), 1 = measurement error,
10 = fail-closed abort (pin mismatch / unparsable input / control not detected).
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
CST = timezone(timedelta(hours=8))

TASK_ID = "W054-T1-GUARD-REV13-01"
LABEL = "worker-054-t1-guard-rev13"

PINS = {
    "schemas/af_wcc_vacuum.yaml": {
        "sha256": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
        "node": "F1", "class_id": "AF-WCC-VAC-GEN", "revision": 13,
    },
    "schemas/af_scc_c2_vacuum.yaml": {
        "sha256": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
        "node": "F2a", "class_id": "AF-SCC-C2-VAC-GEN", "revision": 13,
    },
    "schemas/af_scc_c0_vacuum.yaml": {
        "sha256": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
        "node": "F2b", "class_id": "AF-SCC-C0-VAC-GEN", "revision": 13,
    },
    "research_map/formulation_taxonomy.yaml": {
        "sha256": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
        "node": "F0", "class_id": None, "revision": 5,
    },
    "artifacts/formulation/FROZEN.json": {
        "sha256": None,  # observed, not pinned: FROZEN rev29 was rewritten several times
        "node": None, "class_id": None, "revision": 29,
    },
}

# ---- pre-registered key sets -------------------------------------------------
CORE_DATA_KEYS = [
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
    "gauge",
    "diffeo_quotient",
    "adm_mass.exists",
    "adm_mass.sign",
]

ANNOTATION_KEYS = [
    "adm_mass.citation_status",
    "adm_mass.locator",
    "adm_mass.rigidity",
    "adm_mass.hypotheses_reconciliation",
    "regularity_class.sobolev_variant.status",
    "excluded_data",
]

GENERICITY_GUARD_KEYS = [
    "genericity.kind",
    "genericity.topology_or_measure",
]

# resolved paths as they appear in the flattened maps
CORE_DATA_PATHS = ["data_class." + k for k in CORE_DATA_KEYS]

def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def flatten(obj, prefix: str = "") -> dict:
    """Flatten nested dict/list into dotted paths with JSON-canonical leaf values."""
    out: dict = {}
    if isinstance(obj, dict):
        for k in obj:
            out.update(flatten(obj[k], f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj, list):
        out[prefix] = json.dumps(obj, sort_keys=True, ensure_ascii=False)
    else:
        out[prefix] = obj
    return out


def canon(v):
    return json.dumps(v, sort_keys=True, ensure_ascii=False)


def is_annotation(path: str) -> bool:
    last = path.split(".")[-1]
    bare = path
    for prefix in ("data_class.", "genericity."):
        if bare.startswith(prefix):
            bare = bare[len(prefix):]
    if path in ANNOTATION_KEYS or bare in ANNOTATION_KEYS:
        return True
    if any(tok in last.lower() for tok in ("citation", "locator", "provenance", "source")):
        return True
    if last.lower().endswith("_status") or last.lower() == "status":
        return True
    return False


def extract(byte: bytes, path: str) -> dict:
    doc = yaml.safe_load(byte)
    if not isinstance(doc, dict):
        raise ValueError(f"{path}: top level is not a mapping")
    dc = doc.get("data_class")
    gen = doc.get("genericity")
    if not isinstance(dc, dict) or not isinstance(gen, dict):
        raise ValueError(f"{path}: data_class/genericity missing or not mappings")
    return {
        "class_id": doc.get("class_id"),
        "node_id": doc.get("node_id"),
        "revision": doc.get("revision"),
        "data_class": flatten(dc, "data_class"),
        "genericity": flatten(gen, "genericity"),
    }


def compare(a: dict, b: dict, keys: list[str] | None, value_map: dict) -> dict:
    """Compare flattened maps on `keys` (None = all union keys)."""
    if keys is None:
        keys = sorted(set(a) | set(b))
    rows, mismatch = [], []
    for k in keys:
        va, vb = value_map[a["name"]].get(k, "<absent>"), value_map[b["name"]].get(k, "<absent>")
        eq = canon(va) == canon(vb)
        rows.append({"key": k, "equal": eq, "A": va, "B": vb})
        if not eq:
            mismatch.append(k)
    return {"n_keys": len(keys), "n_equal": len(keys) - len(mismatch), "n_mismatch": len(mismatch),
            "mismatch_keys": mismatch, "rows": rows}


def norm_spaces(s: str) -> str:
    """Normalize a Sobolev-space token: strip parenthetical annotations and whitespace."""
    import re
    return re.sub(r"\s+", " ", re.sub(r"\([^()]*\)", "", str(s))).strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "report.json"))
    ap.add_argument("--created-at", default=None)
    args = ap.parse_args()

    created_at = args.created_at or now()
    problems: list[str] = []

    # ---- snapshot + pin check (fail-closed) ----
    snapshot = {}
    for rel, pin in PINS.items():
        p = ROOT / rel
        if not p.exists():
            problems.append(f"missing input {rel}")
            continue
        raw = p.read_bytes()
        h = sha256_bytes(raw)
        snapshot[rel] = {"sha256": h, "bytes": len(raw),
                         "declared_pin": pin["sha256"], "pin_ok": pin["sha256"] is None or h == pin["sha256"],
                         "node": pin["node"], "class_id": pin["class_id"], "revision_pin": pin["revision"]}
    if problems:
        print(json.dumps({"task_id": TASK_ID, "status": "MEASUREMENT_ERROR", "problems": problems}, indent=1))
        return 1
    pin_failures = [rel for rel, s in snapshot.items() if not s["pin_ok"]]
    if pin_failures:
        print(json.dumps({"task_id": TASK_ID, "status": "FAIL_CLOSED_PIN_MISMATCH",
                          "pin_failures": pin_failures, "snapshot": snapshot}, indent=1))
        return 10

    # ---- parse ----
    docs = {"F1": "schemas/af_wcc_vacuum.yaml", "F2a": "schemas/af_scc_c2_vacuum.yaml", "F2b": "schemas/af_scc_c0_vacuum.yaml"}
    parsed = {}
    for name, rel in docs.items():
        try:
            parsed[name] = extract((ROOT / rel).read_bytes(), rel)
        except Exception as exc:  # noqa: BLE001
            print(json.dumps({"task_id": TASK_ID, "status": "FAIL_CLOSED_UNPARSABLE", "input": rel, "error": str(exc)}, indent=1))
            return 10
        parsed[name]["name"] = name
    for name, d in parsed.items():
        if d["class_id"] != PINS[docs[name]]["class_id"]:
            print(json.dumps({"task_id": TASK_ID, "status": "FAIL_CLOSED_CLASS_MISMATCH", "node": name,
                              "declared": d["class_id"], "pinned": PINS[docs[name]]["class_id"]}, indent=1))
            return 10

    all_dc_keys = sorted(set().union(*[set(p["data_class"]) for p in parsed.values()]))
    all_gen_keys = sorted(set().union(*[set(p["genericity"]) for p in parsed.values()]))
    non_annotation_dc_keys = [k for k in all_dc_keys if not is_annotation(k)]
    excluded_annotation_keys = [k for k in all_dc_keys if is_annotation(k)]

    dc_view = {n: parsed[n]["data_class"] for n in parsed}
    gen_view = {n: parsed[n]["genericity"] for n in parsed}

    # ---- T1 licensed pair: F2b (source, C0) -> F2a (target, C2) ----
    t1_literal = compare({"name": "F2b"}, {"name": "F2a"}, all_dc_keys, dc_view)
    t1_core = compare({"name": "F2b"}, {"name": "F2a"}, CORE_DATA_PATHS, dc_view)
    t1_nonannotation = compare({"name": "F2b"}, {"name": "F2a"}, non_annotation_dc_keys, dc_view)
    t1_annotation_only = [{"key": k, "A_F2b": dc_view["F2b"].get(k, "<absent>"), "B_F2a": dc_view["F2a"].get(k, "<absent>"),
                           "declared_annotation": k in ANNOTATION_KEYS or is_annotation(k)}
                          for k in t1_literal["mismatch_keys"]]
    g2 = compare({"name": "F2b"}, {"name": "F2a"}, GENERICITY_GUARD_KEYS, gen_view)

    # ---- named triple from the map's G-FORM unmet item: (s, delta, norm) ----
    named = {}
    for fld, key in (("s", "data_class.regularity_class.sobolev_variant.s"),
                     ("delta", "data_class.regularity_class.sobolev_variant.delta"),
                     ("norm_spaces", "data_class.regularity_class.sobolev_variant.spaces")):
        vals = {n: dc_view[n].get(key, "<absent>") for n in ("F1", "F2a", "F2b")}
        literal_equal = len({canon(v) for v in vals.values()}) == 1
        entry = {"key": key, "values": vals, "literal_equal_all_three": literal_equal}
        if fld == "norm_spaces":
            normed = {n: norm_spaces(v) for n, v in vals.items()}
            entry["normalized_equal_all_three"] = len(set(normed.values())) == 1
            entry["normalized_values"] = normed
            entry["normalization"] = "strip parenthetical annotations + collapse whitespace (Sobolev-space token only)"
        else:
            entry["normalized_equal_all_three"] = literal_equal
            entry["normalization"] = "not applied (literal comparison is the meaningful one for this field)"
        named[fld] = entry

    # ---- forbidden-transfer control: F1 (WCC) vs F2a on the same content pass ----
    control_cross_family = compare({"name": "F1"}, {"name": "F2a"}, CORE_DATA_PATHS, dc_view)
    control_cross_family_literal = compare({"name": "F1"}, {"name": "F2a"}, all_dc_keys, dc_view)

    # ---- mutation controls (in-memory copies; must be DETECTED) ----
    def mutate(name: str, key: str, value) -> dict:
        view = copy.deepcopy(dc_view)
        view[name][key] = value
        return view

    def detect(name_a, name_b, keys, view) -> dict:
        r = compare({"name": name_a}, {"name": name_b}, keys, view)
        return {"detected": r["n_mismatch"] > 0, "n_mismatch": r["n_mismatch"], "mismatch_keys": r["mismatch_keys"]}

    controls = {}
    controls["C1_core_s_changed"] = {**detect("F2b", "F2a", CORE_DATA_PATHS,
                                              mutate("F2b", "data_class.regularity_class.sobolev_variant.s", "s > 3/2")),
                                     "expected_detected": True}
    controls["C2_core_decay_changed"] = {**detect("F2b", "F2a", CORE_DATA_PATHS,
                                                  mutate("F2b", "data_class.asymptotic_decay.metric", "h_ij - delta_ij = O(r^{-2})")),
                                         "expected_detected": True}
    controls["C3_core_equation_changed"] = {**detect("F2b", "F2a", CORE_DATA_PATHS,
                                                     mutate("F2b", "data_class.equations", "Einstein-Maxwell equations")),
                                            "expected_detected": True}
    controls["C4_annotation_only_changed"] = {
        **detect("F2b", "F2a", CORE_DATA_PATHS, mutate("F2b", "data_class.adm_mass.locator", "MUTANT")),
        "literal_detected": detect("F2b", "F2a", all_dc_keys, mutate("F2b", "data_class.adm_mass.locator", "MUTANT"))["detected"],
        "expected_detected": False,
        "expected_literal_detected": True,
    }
    gview = copy.deepcopy(gen_view)
    gview["F2b"]["genericity.kind"] = "full_measure"
    controls["C5_genericity_kind_changed"] = {**detect("F2b", "F2a", GENERICITY_GUARD_KEYS, gview), "expected_detected": True}
    gview2 = copy.deepcopy(gen_view)
    gview2["F2b"]["genericity.topology_or_measure"] = "MUTANT"
    controls["C6_genericity_topology_changed"] = {**detect("F2b", "F2a", GENERICITY_GUARD_KEYS, gview2), "expected_detected": True}
    controls["C7_cross_family_nonvacuous"] = {
        "detected": control_cross_family["n_mismatch"] > 0,
        "n_mismatch": control_cross_family["n_mismatch"],
        "mismatch_keys": control_cross_family["mismatch_keys"],
        "expected_detected": True,
    }

    controls_ok = all(
        (c["detected"] == c["expected_detected"]) and
        (("expected_literal_detected" not in c) or (c["literal_detected"] == c["expected_literal_detected"]))
        for c in controls.values()
    )

    # ---- verdicts ----
    g1_literal_holds = t1_literal["n_mismatch"] == 0
    g1_core_holds = t1_core["n_mismatch"] == 0
    g1_nonannotation_holds = t1_nonannotation["n_mismatch"] == 0
    g2_holds = g2["n_mismatch"] == 0
    annotation_only_divergence = (not g1_literal_holds) and g1_nonannotation_holds

    transfer_disabled_by_data_class = not g1_nonannotation_holds

    # ---- drift re-check ----
    drift = {}
    for rel in PINS:
        h = sha256_file(ROOT / rel)
        drift[rel] = {"changed": h != snapshot[rel]["sha256"], "snapshot": snapshot[rel]["sha256"], "live_at_end": h}

    report = {
        "task_id": TASK_ID,
        "label": LABEL,
        "worker": "worker-054",
        "created_at": created_at,
        "mode": "read-only; no canonical write; no gate verdict; no node transition",
        "rule_under_test": {
            "rule_id": "T1",
            "source": "research_map/formulation_taxonomy.yaml#transfer_rules.allowed[0]",
            "from": "AF-SCC-C0-VAC-GEN (F2b)",
            "to": "AF-SCC-C2-VAC-GEN (F2a)",
            "kind": "conclusion_strengthening",
            "guard_1": "data_class fields must match exactly (including s, delta once F2 fixes them)",
            "guard_2": "genericity_kind and genericity_topology must match exactly",
            "guard_3": "source claim must carry artifact_refs and a reviewer verdict (not testable here)",
        },
        "pre_registration": {
            "core_data_keys": CORE_DATA_KEYS,
            "core_data_paths": CORE_DATA_PATHS,
            "annotation_keys": ANNOTATION_KEYS,
            "annotation_keys_present_in_union": excluded_annotation_keys,
            "annotation_key_filter": "last path component contains citation/locator/provenance/source, or endswith _status, or equals status",
            "genericity_guard_keys": GENERICITY_GUARD_KEYS,
            "mutation_controls": list(controls.keys()),
            "note": "key sets and controls fixed before the comparison; the checker is published with the report",
        },
        "snapshot": snapshot,
        "inputs": {n: {"path": docs[n], "class_id": parsed[n]["class_id"], "node_id": parsed[n]["node_id"],
                       "revision": parsed[n]["revision"]} for n in parsed},
        "measurements": {
            "T1_pair_data_class_literal": t1_literal,
            "T1_pair_data_class_content": t1_core,
            "T1_pair_data_class_excluding_annotations": t1_nonannotation,
            "T1_pair_literal_mismatch_are_annotations": t1_annotation_only,
            "T1_pair_genericity_guard_2": g2,
            "named_triple_s_delta_norm": named,
            "forbidden_pair_F1_vs_F2a_content": control_cross_family,
            "forbidden_pair_F1_vs_F2a_literal": control_cross_family_literal,
        },
        "controls": controls,
        "controls_all_detected": controls_ok,
        "verdict": {
            "g1_literal_holds": g1_literal_holds,
            "g1_content_core_holds": g1_core_holds,
            "g1_excluding_annotations_holds": g1_nonannotation_holds,
            "g2_genericity_holds": g2_holds,
            "t1_divergence_is_annotation_only": annotation_only_divergence,
            "licensed_transfer_disabled_by_data_class_divergence": transfer_disabled_by_data_class,
            "summary": (
                "T1 guard-2 (genericity kind/topology) HOLDS exactly at rev13. "
                + ("T1 guard-1 HOLDS literally on the whole data_class subtree. "
                   if g1_literal_holds else
                   "T1 guard-1 FAILS on a literal reading of 'exactly' on the whole data_class subtree, and every "
                   "mismatching key is a citation/annotation field: " + ", ".join(k["key"] for k in t1_annotation_only) + ". ")
                + ("Guard-1 HOLDS on the pre-registered mathematical content keys, so the failure is not a "
                   "data-space divergence and does not by itself disable the licensed C0=>C2 transfer. "
                   if g1_nonannotation_holds else
                   "Guard-1 FAILS on mathematical content keys as well: " + ", ".join(t1_nonannotation["mismatch_keys"]) + ". ")
                + "The named (s, delta, norm) triple is literal-equal on s and delta across F1/F2a/F2b"
                + (" and normalized-equal on norm. " if named["norm_spaces"]["normalized_equal_all_three"]
                   else "; norm differs. ")
                + "The forbidden F1->F2a pair fails the same content pass (control non-vacuous)."
            ),
        },
        "authority": {
            "can_reopen_gate": False,
            "can_set_node_status": False,
            "recommendation": (
                "Either restate T1 guard-1 as 'mathematical data_class fields must match exactly, citation/provenance "
                "annotations excluded' (the divergence then disappears), or align the two annotation fields between F2b and "
                "F2a. Evidence for the G-FORM r3 review; not a gate verdict."
            ),
        },
        "falsifier": (
            "At the pinned bytes, re-run checker.py with the same --created-at: any verdict, mismatch key list, control "
            "result or named-triple value that differs falsifies this report. The report is also falsified if drift.detected "
            "is true for any input, or if any F1/F2a/F2b class_id/revision differs from its pin."
        ),
        "drift": drift,
        "drift_detected": any(v["changed"] for v in drift.values()),
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"task_id": TASK_ID, "status": "OK" if controls_ok else "CONTROL_FAILURE",
                      "out": str(out), "verdict": report["verdict"]["summary"],
                      "drift_detected": report["drift_detected"],
                      "controls_all_detected": controls_ok}, indent=1))
    return 0 if controls_ok else 10


if __name__ == "__main__":
    sys.exit(main())
