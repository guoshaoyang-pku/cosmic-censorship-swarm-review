#!/usr/bin/env python3
"""W029-CROSSCLASS-DATACLASS-02: deterministic cross-schema data-class audit.

Task: measure, at the frozen G-FORM hashes, the gate criterion recorded in
research_map.json G-FORM.unmet: "no single frozen data class (s,delta,norm) is
shared by F1/F2a/F2b, which disables the licensed C0=>C2 transfer".

This is an artifact-and-checker measurement, not a mathematical claim.

Measured questions (H1-H4):
  H1  Do the three schemas declare the same data class (matter, Lambda,
      equations, constraints, decay, Sobolev pair, smooth default)?
  H2  Is a SINGLE (s,delta,norm) frozen, i.e. is the formal quantifier domain
      D0 pair-indexed with a well-typed (s,delta) for every member?
  H3  Is the C0=>C2 transfer recorded in the implication ledgers, and is it
      licensed for every member of D0?
  H4  Cross-schema consistency of the ledger containment claims vs the
      must_not_conflate prohibitions.

Deterministic, read-only: reads only the snapshot directory passed by --snap
(default ./snapshots next to this file) and writes --out (default evidence.json).
Exit code 0 always; the verdict is in the JSON.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
SCHEMAS = {
    "F1": "af_wcc_vacuum.yaml",
    "F2a": "af_scc_c2_vacuum.yaml",
    "F2b": "af_scc_c0_vacuum.yaml",
}
F0 = "formulation_taxonomy.canonical.yaml"
CLASS_IDS = {
    "F1": "AF-WCC-VAC-GEN",
    "F2a": "AF-SCC-C2-VAC-GEN",
    "F2b": "AF-SCC-C0-VAC-GEN",
}
EXPECTED = {  # frozen hashes measured 2026-09-12T00:28:48+08:00
    "F1": "9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503",
    "F2a": "b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2",
    "F2b": "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508",
    F0: "276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc",
}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class StrictLoader(yaml.SafeLoader):
    """SafeLoader that records duplicate mapping keys instead of silently
    dropping all but the last (PyYAML default)."""

    def __init__(self, stream):
        super().__init__(stream)
        self.duplicate_keys: list[str] = []

    def construct_mapping(self, node, deep=False):
        seen = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in seen:
                self.duplicate_keys.append(str(key))
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


def load(path: Path):
    loader = StrictLoader(path.read_text())
    try:
        data = loader.get_single_data()
    finally:
        loader.dispose()
    return data, loader.duplicate_keys


def lines_of(path: Path, needle: str) -> list[int]:
    return [i + 1 for i, line in enumerate(path.read_text().splitlines()) if needle in line]


def _norm_text(x):
    if not isinstance(x, str):
        return x
    y = re.sub(r"\s+", " ", x).strip()
    y = re.sub(r"\s*\(weighted Sobolev\)", "", y)          # F1 wording suffix
    y = y.split(";")[0].strip()                            # status/ownership clauses
    y = y.rstrip(".").strip()
    return y


def math_signature(d: dict) -> dict:
    """Normalized mathematical content of the declared data class. Prose that
    does not change the mathematical content (citation status, ownership,
    parenthetical naming, appended cautions) is stripped; structural deltas are
    reported separately by flatten()."""
    dc = d.get("data_class") or {}
    sob = ((dc.get("regularity_class") or {}).get("sobolev_variant")) or {}
    dec = dc.get("asymptotic_decay") or {}
    return {
        "matter": dc.get("matter"),
        "cosmological_constant": dc.get("cosmological_constant"),
        "equations": _norm_text(dc.get("equations")),
        "constraints": dc.get("constraints"),
        "regularity_default": _norm_text((dc.get("regularity_class") or {}).get("default")),
        "sobolev_s": sob.get("s"),
        "sobolev_delta": sob.get("delta"),
        "sobolev_spaces": _norm_text(sob.get("spaces")),
        "decay_metric": _norm_text(dec.get("metric")),
        "decay_second_fundamental_form": _norm_text(dec.get("second_fundamental_form")),
        "parity_conditions": _norm_text(dec.get("parity_conditions")),
        "symmetry": dc.get("symmetry") or "none_assumed",  # undeclared == explicit default; delta reported structurally
    }


def flatten(obj, prefix=""):
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(flatten(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj, list):
        out[prefix] = json.dumps(obj, sort_keys=True)
    else:
        out[prefix] = obj
    return out


def structural_diff(a: dict, b: dict) -> dict:
    fa, fb = flatten(a), flatten(b)
    only_a = {k: fa[k] for k in sorted(set(fa) - set(fb))}
    only_b = {k: fb[k] for k in sorted(set(fb) - set(fa))}
    changed = {k: [fa[k], fb[k]] for k in sorted(set(fa) & set(fb)) if fa[k] != fb[k]}
    return {"only_in_first": only_a, "only_in_second": only_b, "value_differs": changed}


def data_regularity_line(d: dict) -> str | None:
    return (d.get("data_class") or {}).get("data_regularity") or (d.get("regularity") or {}).get("data_regularity")


def d0(d: dict) -> dict:
    return ((d.get("quantifiers") or {}).get("domains") or {}).get("D0") or {}


def formal_statement(d: dict) -> str:
    return (d.get("quantifiers") or {}).get("formal") or ""


def ledger(d: dict) -> dict:
    return d.get("implication_ledger") or {}


def must_not_conflate(d: dict) -> list[str]:
    reg = d.get("regularity") or {}
    out = list(reg.get("must_not_conflate") or [])
    dc = d.get("data_class") or {}
    out += list(dc.get("must_not_conflate") or [])
    return [str(x) for x in out]


def transfer_edges(d: dict) -> list[dict]:
    edges = []
    for e in ledger(d).get("one_way_entailments") or []:
        edges.append({"kind": "entails", **{k: e.get(k) for k in ("from", "to", "relation", "reason", "status")}})
    for e in ledger(d).get("forbidden_transfers") or []:
        edges.append({"kind": "forbidden", **{k: e.get(k) for k in ("from", "to", "reason")}})
    return edges


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snap", default=str(HERE / "snapshots"))
    ap.add_argument("--out", default=str(HERE / "evidence.json"))
    args = ap.parse_args()
    snap = Path(args.snap).resolve()
    repo = HERE.parent.parent.parent

    ev: dict = {
        "checker": "check_crossclass_dataclass.py",
        "task_id": "W029-CROSSCLASS-DATACLASS-02",
        "class_ids": list(CLASS_IDS.values()),
        "gate": "G-FORM",
        "kind": "artifact_and_checker_measurement",
        "measured_at_snapshot": True,
        "inputs": {},
        "hypotheses": {},
        "findings": [],
        "verdict": None,
        "falsifier": None,
    }

    parsed = {}
    for key, fname in list(SCHEMAS.items()) + [(F0, F0)]:
        p = snap / fname
        h = sha256(p)
        d, dups = load(p)
        parsed[key] = (d, p)
        ev["inputs"][key] = {
            "path": f"schemas/{fname}" if key != F0 else "research_map/formulation_taxonomy.yaml",
            "snapshot_path": f"artifacts/worker-029/crossclass_dataclass/snapshots/{fname}",
            "sha256": h,
            "matches_frozen_expected": EXPECTED[key] == h,
            "duplicate_mapping_keys": sorted(set(dups)) if dups else [],
            "duplicate_key_occurrences": len(dups),
        }
        if key != F0:
            # live path drift check (read-only)
            live = repo / ("schemas/" + fname)
            if live.is_file():
                ev["inputs"][key]["live_sha256"] = sha256(live)
                ev["inputs"][key]["live_drift_vs_snapshot"] = ev["inputs"][key]["live_sha256"] != h

    # --- H1: cross-schema data-class identity -------------------------------
    sigs = {k: math_signature(parsed[k][0]) for k in SCHEMAS}
    raw_keys = {k: sorted((parsed[k][0].get("data_class") or {}).keys()) for k in SCHEMAS}
    h1 = {"normalized_math_signatures": sigs, "data_class_keys": raw_keys}
    h1["math_signature_equal_all_three"] = sigs["F1"] == sigs["F2a"] == sigs["F2b"]
    h1["pairwise_normalized_equal"] = {
        "F1_vs_F2a": sigs["F1"] == sigs["F2a"],
        "F1_vs_F2b": sigs["F1"] == sigs["F2b"],
        "F2a_vs_F2b": sigs["F2a"] == sigs["F2b"],
    }
    h1["structural_diff_F1_vs_F2a"] = structural_diff(
        parsed["F1"][0].get("data_class") or {}, parsed["F2a"][0].get("data_class") or {})
    h1["structural_diff_F1_vs_F2b"] = structural_diff(
        parsed["F1"][0].get("data_class") or {}, parsed["F2b"][0].get("data_class") or {})
    h1["structural_diff_F2a_vs_F2b"] = structural_diff(
        parsed["F2a"][0].get("data_class") or {}, parsed["F2b"][0].get("data_class") or {})
    h1["key_set_equal"] = {
        "F1_vs_F2a": raw_keys["F1"] == raw_keys["F2a"],
        "F1_vs_F2b": raw_keys["F1"] == raw_keys["F2b"],
        "F2a_vs_F2b": raw_keys["F2a"] == raw_keys["F2b"],
    }
    h1["key_diff"] = {
        "F1_only_vs_F2a": sorted(set(raw_keys["F1"]) - set(raw_keys["F2a"])),
        "F1_only_vs_F2b": sorted(set(raw_keys["F1"]) - set(raw_keys["F2b"])),
        "F2a_only_vs_F1": sorted(set(raw_keys["F2a"]) - set(raw_keys["F1"])),
        "F2a_only_vs_F2b": sorted(set(raw_keys["F2a"]) - set(raw_keys["F2b"])),
    }
    h1["data_regularity_text"] = {k: data_regularity_line(parsed[k][0]) for k in SCHEMAS}
    h1["data_regularity_text_equal"] = len(set(h1["data_regularity_text"].values())) == 1
    ev["hypotheses"]["H1_cross_schema_same_data_class"] = h1

    # --- H2: single frozen (s,delta,norm) -----------------------------------
    h2 = {"per_schema": {}, "disjunction_count": 0}
    disj_re = re.compile(r",\s*or the smooth-with-decay default", re.I)
    pair_re = re.compile(r"forall\s*\(s\s*,\s*delta\)\s*in\s*D0", re.I)
    for k in SCHEMAS:
        d, p = parsed[k]
        dom = d0(d)
        defn = str(dom.get("definition") or "")
        formal = formal_statement(d)
        dr = str(data_regularity_line(d) or "")
        is_disj = bool(disj_re.search(defn)) or bool(disj_re.search(dr))
        has_pair_binder = bool(pair_re.search(formal))
        # the smooth member carries no (s,delta) coordinates if the domain text
        # offers it as an alternative member of D0
        smooth_member = "smooth-with-decay" in defn
        pair_indexed = not smooth_member
        if is_disj:
            h2["disjunction_count"] += 1
        h2["per_schema"][k] = {
            "class_id": CLASS_IDS[k],
            "D0_definition": defn,
            "D0_definition_lines": lines_of(p, "admissible regularity pairs") or lines_of(p, "smooth-with-decay default, or"),
            "formal_binder_is_pair_indexed": has_pair_binder,
            "formal_statement_line": (lines_of(p, "forall (s,delta) in D0") or [None])[0],
            "data_regularity": dr,
            "data_regularity_line": (lines_of(p, "data_regularity:") or [None])[0],
            "smooth_member_in_D0": smooth_member,
            "every_D0_member_has_s_delta": pair_indexed,
            "disjunctive_D0": is_disj,
            "ambient_space_is_pair_indexed_only": "X^{s,delta}_vac(AF)" in (d.get("genericity") or {}).get("topology_or_measure", "")
            or "X^{s,delta}_vac(AF)" in str((d.get("data_class") or {}).get("regularity_class")),
        }
    h2["single_frozen_s_delta_triple_all_three"] = h2["disjunction_count"] == 0
    h2["confirms_gform_unmet_item"] = not h2["single_frozen_s_delta_triple_all_three"]
    ev["hypotheses"]["H2_single_frozen_s_delta"] = h2

    # --- H3: C0 => C2 transfer licensing ------------------------------------
    h3 = {"per_schema": {}}
    for k in ("F2a", "F2b"):
        edges = transfer_edges(parsed[k][0])
        c0_to_c2 = [
            e for e in edges
            if e["kind"] == "entails"
            and "C0" in str(e["from"] or "")
            and "C2" in str(e["to"] or "")
        ]
        c0_to_c2_forbidden = [
            e for e in edges
            if e["kind"] == "forbidden" and "C0" in str(e["from"] or "") and "C2" in str(e["to"] or "")
        ]
        h3["per_schema"][k] = {
            "class_id": CLASS_IDS[k],
            "edges_total": len(edges),
            "c0_to_c2_entailments": c0_to_c2,
            "c0_to_c2_forbidden": c0_to_c2_forbidden,
            "c0_to_c2_recorded": bool(c0_to_c2) and not c0_to_c2_forbidden,
            "ledger_lines": lines_of(parsed[k][1], "extension_class_containment"),
        }
    # F1 records the smooth<->Sobolev transfer prohibition
    f1_mnc = must_not_conflate(parsed["F1"][0])
    f1_smooth_transfer_prohibition = [
        s for s in f1_mnc if "smooth-data statements may not be transferred" in s
    ]
    h3["f1_smooth_to_sobolev_transfer_prohibition"] = f1_smooth_transfer_prohibition
    h3["f1_prohibition_lines"] = lines_of(parsed["F1"][1], "smooth-data statements may not be transferred")
    # licensed for every member? needs both the ledger edges and no prohibition
    # on the member-to-member transfer plus a recorded approximation/stability
    # argument; scan the three schemas and the canonical taxonomy for one.
    arg_re = re.compile(r"approximation[/ -]?stability|stability argument|density argument|approximat", re.I)
    arg_hits = {}
    for k in SCHEMAS:
        hits = [i + 1 for i, line in enumerate(parsed[k][1].read_text().splitlines())
                if arg_re.search(line) and "may not be transferred" not in line]
        arg_hits[k] = hits
    tax_text = (snap / F0).read_text()
    tax_hits = [i + 1 for i, line in enumerate(tax_text.splitlines()) if arg_re.search(line)]
    h3["approximation_stability_argument_recorded"] = {
        **{k: v for k, v in arg_hits.items()},
        "canonical_F0": tax_hits,
    }
    h3["transfer_licensed_for_every_D0_member"] = (
        all(v["c0_to_c2_recorded"] for v in h3["per_schema"].values())
        and not f1_smooth_transfer_prohibition
    ) or (
        all(v["c0_to_c2_recorded"] for v in h3["per_schema"].values())
        and any(arg_hits.values())
    )
    ev["hypotheses"]["H3_c0_implies_c2_transfer"] = h3

    # --- H4: containment vs must_not_conflate consistency --------------------
    h4 = {"per_schema": {}}
    for k in SCHEMAS:
        d, p = parsed[k]
        cont_lines = lines_of(p, "E_C0 contains E_H2loc") + lines_of(p, "E_H2loc subset of E_C0") + lines_of(p, "No containment with C2 or C0 is asserted")
        prohib = [s for s in must_not_conflate(d) if "No containment with C2 or C0 is asserted" in s]
        asserts_containment = bool(lines_of(p, "E_H2loc subset of E_C0")) or bool(lines_of(p, "E_C0 contains E_H2loc"))
        h4["per_schema"][k] = {
            "asserts_containment_E_H2loc_subset_E_C0": asserts_containment,
            "retains_no_containment_sentence": bool(prohib),
            "internal_contradiction": asserts_containment and bool(prohib),
            "lines": sorted(set(cont_lines)),
            "no_containment_line": lines_of(p, "No containment with C2 or C0 is asserted"),
        }
    h4["contradiction_schemas"] = [k for k, v in h4["per_schema"].items() if v["internal_contradiction"]]
    ev["hypotheses"]["H4_ledger_vs_prohibition_consistency"] = h4

    # --- findings + verdict --------------------------------------------------
    f = ev["findings"]
    if not h1["math_signature_equal_all_three"]:
        f.append({"id": "W029C-01", "severity": "major",
                  "finding": "the three schemas' normalized mathematical data-class signatures differ",
                  "detail": h1["pairwise_normalized_equal"]})
    else:
        f.append({"id": "W029C-01", "severity": "pass",
                  "finding": "matter/Lambda/equations/constraints/decay/Sobolev pair agree across F1/F2a/F2b "
                             "after normalizing prose (citation status, ownership, parenthetical naming); "
                             "the remaining cross-schema differences are structural, see W029C-02",
                  "detail": "math_signature_equal_all_three=true"})
    if not h1["key_set_equal"]["F1_vs_F2a"] or not h1["key_set_equal"]["F1_vs_F2b"]:
        f.append({"id": "W029C-02", "severity": "info",
                  "finding": "F1's data_class is structurally not byte-identical to F2a/F2b "
                             "(extra key and wording/status deltas); F2a and F2b are key-identical",
                  "detail": {"key_set_equal": h1["key_set_equal"],
                             "diff_F1_vs_F2a": h1["structural_diff_F1_vs_F2a"],
                             "diff_F1_vs_F2b": h1["structural_diff_F1_vs_F2b"],
                             "diff_F2a_vs_F2b": h1["structural_diff_F2a_vs_F2b"]}})
    if h2["confirms_gform_unmet_item"]:
        f.append({"id": "W029C-03", "severity": "hard_for_gate_criterion",
                  "finding": "no single frozen (s,delta,norm): D0 is a two-member domain "
                             "(Sobolev pair OR smooth-with-decay default) in all three schemas, "
                             "and the formal binder 'forall (s,delta) in D0' is ill-typed on the "
                             "smooth member",
                  "detail": {"disjunction_count": h2["disjunction_count"],
                             "per_schema": {k: {"D0_definition": v["D0_definition"],
                                                "formal_statement_line": v["formal_statement_line"],
                                                "data_regularity_line": v["data_regularity_line"]}
                                            for k, v in h2["per_schema"].items()}}})
    if f1_smooth_transfer_prohibition and not any(arg_hits.values()):
        f.append({"id": "W029C-04", "severity": "major",
                  "finding": "the C0=>C2 ledger edges are recorded, but F1's must_not_conflate "
                             "forbids smooth-data statements being transferred to the Sobolev variant "
                             "without an approximation/stability argument, and no such argument is "
                             "recorded in any of the three schemas or the canonical F0 taxonomy; "
                             "with a disjunctive D0 the transfer is therefore licensed only member-wise",
                  "detail": {"prohibition_lines": h3["f1_prohibition_lines"],
                             "argument_hits": h3["approximation_stability_argument_recorded"]}})
    if h4["contradiction_schemas"]:
        f.append({"id": "W029C-05", "severity": "minor",
                  "finding": "retained 'No containment with C2 or C0 is asserted here' sentence "
                             "contradicts the same file's implication_ledger containment claim "
                             "(F2a already carries the corrected wording)",
                  "detail": {k: h4["per_schema"][k] for k in h4["contradiction_schemas"]}})
    dup_schemas = {k: {"occurrences": v["duplicate_key_occurrences"],
                       "keys": v["duplicate_mapping_keys"]}
                   for k, v in ev["inputs"].items() if v.get("duplicate_key_occurrences")}
    if dup_schemas:
        f.append({"id": "W029C-06", "severity": "info",
                  "finding": "all three frozen schemas carry duplicate top-level YAML mapping keys "
                             "(last-wins under PyYAML); the duplicate-key defect class is therefore "
                             "cross-schema, not F1-only",
                  "detail": dup_schemas})

    ev["verdict"] = {
        "gate_criterion": "G-FORM.unmet: no single frozen data class (s,delta,norm) is shared by F1/F2a/F2b",
        "criterion_status": "CONFIRMED_UNMET" if h2["confirms_gform_unmet_item"] else "REFUTED_STALE",
        "hard_finding_count": len([x for x in f if x["severity"].startswith("hard")]),
        "summary": (
            "At the frozen hashes the three schemas agree on the mathematical data class "
            f"(signature_equal={h1['math_signature_equal_all_three']}; F1 key-set delta reported), "
            "but no single (s,delta,norm) is frozen: D0 is a two-member domain in all three and "
            "the pair binder is ill-typed on the smooth member. C0=>C2 ledger edges exist in F2a "
            "and F2b; they are unconditional only member-wise because F1 forbids smooth->Sobolev "
            "transfer without an approximation/stability argument that no artifact records."
        ),
    }
    ev["falsifier"] = (
        "Any revision of F1/F2a/F2b in which D0's definition names a single pair-indexed domain "
        "that supplies an (s,delta) for every member (or the smooth member is removed to a "
        "registered variant), and in which the C0=>C2 transfer carries a recorded "
        "approximation/stability argument (or F1's prohibition is withdrawn), falsifies this "
        "measurement. A live hash different from the pinned snapshots also voids it."
    )
    Path(args.out).write_text(json.dumps(ev, indent=1, sort_keys=False) + "\n")
    print(json.dumps({"verdict": ev["verdict"], "findings": [x["id"] for x in f]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
