#!/usr/bin/env python3
"""Deterministic F1 frozen-revision review probe (worker-088, second task).

Verifies, from the bytes of the pinned F1 schema alone plus read-only sibling/map
reads, the four hash-bound F1 findings open in `research_map/ASTRA_HANDOFF.md`
pass 03 (duplicate/future-dated revision keys, non-canonical class_contract_pointer,
undefined AF_{I+} in the conclusion, quantifier clause vs declared tail predicate)
and the cross-schema single-frozen-data-class criterion (F1 vs F2a/F2b).

No network. No writes other than the --out JSON. Every finding in the accompanying
review `reviews/F1-review-088.json` is backed by a field of this report.

Usage:
  python3 artifacts/worker-088/f1_review/check_f1.py \
      --artifact schemas/af_wcc_vacuum.yaml \
      --out artifacts/worker-088/f1_review/f1_check.json
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
FROZEN_CLASSES = {"AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"}
SIBLINGS = {"F2a": "schemas/af_scc_c2_vacuum.yaml",
            "F2b": "schemas/af_scc_c0_vacuum.yaml"}
CANONICAL_F0 = "research_map/formulation_taxonomy.yaml"
AUTHORING_F0 = "artifacts/formulation/formulation_taxonomy.yaml"
CLASS_TOKEN = re.compile(r"AF-[A-Z0-9-]{3,}")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class DuplicateKeyLoader(yaml.SafeLoader):
    """SafeLoader that records duplicate mapping keys instead of silently last-winning."""


def load_yaml_strict(text: str):
    dupes: list[str] = []

    def construct_mapping(loader, node, deep=False):
        keys = []
        for k_node, _ in node.value:
            try:
                keys.append(loader.construct_object(k_node, deep=deep))
            except Exception:
                keys.append("<unhashable>")
        counts = Counter(k for k in keys if isinstance(k, str))
        dupes.extend(f"{k} x{n}" for k, n in counts.items() if n > 1)
        return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)

    DuplicateKeyLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping)
    doc = yaml.load(text, Loader=DuplicateKeyLoader)
    return doc, sorted(set(dupes))


def walk_strings(node, path="$"):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from walk_strings(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk_strings(v, f"{path}[{i}]")
    elif isinstance(node, str):
        yield path, node


def parse_iso(value):
    if not isinstance(value, str):
        return None
    try:
        return datetime.datetime.fromisoformat(value)
    except ValueError:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", default="schemas/af_wcc_vacuum.yaml")
    ap.add_argument("--out", default="artifacts/worker-088/f1_review/f1_check.json")
    args = ap.parse_args()

    art = (ROOT / args.artifact).resolve()
    text = art.read_text()
    h1 = sha256(art)
    doc, dupes = load_yaml_strict(text)
    h2 = sha256(art)
    now = datetime.datetime.now().astimezone()

    q = doc.get("quantifiers", {}) or {}
    domains = q.get("domains", {}) or {}
    ordered = q.get("ordered", []) or []
    gen = doc.get("genericity", {}) or {}
    dc = doc.get("data_class", {}) or {}
    reg = doc.get("regularity", {}) or {}
    concl = doc.get("conclusion", {}) or {}
    topo = doc.get("topology", {}) or {}
    ip = doc.get("i_plus", {}) or {}
    vis = doc.get("visibility", {}) or {}
    fals = doc.get("falsifier", {}) or {}
    nv = doc.get("non_vacuity", {}) or {}
    f0 = doc.get("f0_binding", {}) or {}

    # --- A. required-field matrix for the F1 acceptance axes ---
    required = {
        "quantifiers.formal": bool(q.get("formal")),
        "quantifiers.ordered": bool(ordered),
        "quantifiers.domains": bool(domains),
        "quantifiers.order_matters": q.get("order_matters") is True,
        "topology.spacetime_dimension==4": topo.get("spacetime_dimension") == 4,
        "topology.slice_topology": bool(topo.get("slice_topology")),
        "topology.conformal_boundary": bool(topo.get("conformal_boundary")),
        "topology.forbidden": bool(topo.get("forbidden")),
        "data_class.regularity_class": bool(dc.get("regularity_class")),
        "data_class.constraints": bool(dc.get("constraints")),
        "data_class.equations": bool(dc.get("equations")),
        "regularity.data_regularity": bool(reg.get("data_regularity")),
        "regularity.solution_regularity": bool(reg.get("solution_regularity")),
        "regularity.i_plus_regularity": bool(reg.get("i_plus_regularity")),
        "regularity.must_not_conflate": bool(reg.get("must_not_conflate")),
        "genericity.kind": bool(gen.get("kind")),
        "genericity.ambient_space": bool(gen.get("ambient_space")),
        "genericity.topology_or_measure": bool(gen.get("topology_or_measure")),
        "genericity.generic_set": bool(gen.get("generic_set")),
        "genericity.excluded_set": bool(gen.get("excluded_set")),
        "genericity.transfer_failures": bool(gen.get("transfer_failures")),
        "genericity.is_part_of_class": gen.get("is_part_of_class") is True,
        "genericity.class_change_warning": bool(gen.get("class_change_warning")),
        "i_plus.role": bool(ip.get("role")),
        "i_plus.in_conclusion==True": ip.get("in_conclusion") is True,
        "i_plus.completeness_definition": bool(ip.get("completeness_definition")),
        "visibility.role": bool(vis.get("role")),
        "visibility.in_conclusion==True": vis.get("in_conclusion") is True,
        "visibility.definition": bool(vis.get("definition")),
        "non_vacuity.condition": bool(nv.get("condition")),
        "non_vacuity.vacuity_falsifier": bool(nv.get("vacuity_falsifier")),
        "conclusion.conclusion_type": bool(concl.get("conclusion_type")),
        "conclusion.statement_formal": bool(concl.get("statement_formal")),
        "conclusion.statement_natural_language": bool(concl.get("statement_natural_language")),
        "falsifier.tier_1": bool(fals.get("tier_1")),
        "class_contract_pointer": bool(doc.get("class_contract_pointer")),
        "f0_binding": bool(f0),
    }

    # --- B. binder/domain resolution + D0 disjunction probe ---
    domain_ids = set(domains.keys())
    binder_rows = []
    for row in ordered:
        did = row.get("domain_id") if isinstance(row, dict) else None
        binder_rows.append({
            "kind": row.get("kind") if isinstance(row, dict) else None,
            "binder": row.get("binder") if isinstance(row, dict) else None,
            "domain_id": did,
            "resolves": did in domain_ids,
        })
    unresolved = [r for r in binder_rows if not r["resolves"]]

    d0_def = str((domains.get("D0") or {}).get("definition", ""))
    d0_disjuncts = [s.strip() for s in re.split(r",?\s+or\s+", d0_def) if s.strip()]
    smooth_branch = [s for s in d0_disjuncts if "smooth-with-decay" in s]
    sobolev_branch = [s for s in d0_disjuncts if "Sobolev" in s]
    smooth_supplies_params = bool(re.search(r"\bs\b\s*[><=]|\bdelta\b\s*(in|[><=])", smooth_branch[0])) if smooth_branch else None
    ambient = str(gen.get("ambient_space", ""))
    tom = str(gen.get("topology_or_measure", ""))
    ambient_defines_smooth_branch = "smooth" in ambient.lower()
    d0_tagged_union = bool(re.search(r"tagged disjoint union|\br\s*=\s*smooth", d0_def))
    d0_declares_per_branch_ambient = ("frechet" in d0_def.lower()
                                      and ("sobolev" in d0_def.lower() or "h^s" in d0_def.lower()))
    d0_branch_typed = d0_tagged_union and d0_declares_per_branch_ambient
    operative_binder = ordered[0].get("binder") if ordered and isinstance(ordered[0], dict) else None
    d0_probe = {
        "d0_definition": d0_def,
        "d0_disjunct_count": len(d0_disjuncts),
        "sobolev_branch": bool(sobolev_branch),
        "smooth_with_decay_branch": bool(smooth_branch),
        "smooth_branch_supplies_s_delta_pair": smooth_supplies_params,
        "operative_binder": operative_binder,
        "d0_tagged_union": d0_tagged_union,
        "d0_declares_per_branch_ambient": d0_declares_per_branch_ambient,
        "d0_branch_typed": d0_branch_typed,
        "fixed_at_these_values_clause": "fixed at these values" in d0_def,
        "formal_binder_is_s_delta": "(s,delta)" in str(q.get("formal", "")),
        "ordered_binder_is_s_delta": any(r.get("binder") == "(s,delta)" for r in binder_rows),
        "ambient_space_mentions_s_delta_index": "X^{s,delta}" in ambient,
        "ambient_space_mentions_r_index": "X^r" in ambient,
        "ambient_space_defines_smooth_branch": ambient_defines_smooth_branch,
        "topology_or_measure_mentions_smooth_frechet": ("frechet" in tom.lower() and "smooth" in tom.lower()),
        "conclusion_statement_formal": concl.get("statement_formal"),
        "conclusion_uses_d0": "D0" in str(concl.get("statement_formal", "")),
    }
    d0_ill_typed = (bool(smooth_branch) and smooth_supplies_params is False
                    and not ambient_defines_smooth_branch and not d0_branch_typed)

    # --- C. operative-statement vs declared-predicate consistency (unique probe) ---
    formal = str(q.get("formal", ""))
    vis_def = str(vis.get("definition", ""))
    vis_neg = str(vis.get("negation_conclusion", ""))
    clause_match = re.search(r"forall future-inextendible causal geodesics.*", formal, re.S)
    formal_clause = clause_match.group(0) if clause_match else ""
    formal_has_t0 = bool(re.search(r"\bt0\b", formal_clause))
    formal_has_tail_slice = bool(re.search(r"\[\s*t0\s*,\s*T\s*\)", formal_clause))
    formal_has_tail_word = "tail" in formal_clause.lower()
    tail_probe = {
        "formal_visibility_clause": formal_clause.strip(),
        "formal_clause_has_t0": formal_has_t0,
        "formal_clause_has_tail_slice": formal_has_tail_slice,
        "formal_clause_has_tail_word": formal_has_tail_word,
        "formal_clause_rejects_whole_geodesic_containment_only": bool(
            re.search(r"not\s+exists\s+q\s+in\s+I\+\s+with\s+gamma\s+subset\s+J\^\-\(q\)", formal_clause)),
        "declared_definition_has_t0": bool(re.search(r"\bt0\b", vis_def)),
        "declared_definition_has_tail": "tail" in vis_def.lower(),
        "declared_definition_rejects_whole_geodesic_containment": (
            "requiring the whole geodesic to lie in J^-(q) would misclassify" in vis_def),
        "negation_conclusion_rejects_whole_geodesic": "NOT equivalent to 'gamma is contained in B" in vis_neg,
        "predicate_name": vis.get("predicate_name"),
        "operator_precedence_note": (
            "whole-geodesic containment implies tail containment, so a formal clause that negates only "
            "whole-geodesic containment is strictly weaker than the declared predicate's negation of "
            "tail containment; the two are not interchangeable"),
        "formal_matches_declared_predicate": bool(
            formal_has_t0 and (formal_has_tail_word or formal_has_tail_slice)),
    }

    # --- D. symbol definedness in the operative statements ---
    def count(sym, where=None):
        return len(re.findall(re.escape(sym), where if where is not None else text))

    statement_formal = str(concl.get("statement_formal", ""))
    nnf = str(q.get("negation_normal_form", ""))

    def find_definition_leaf(symbol):
        """Leaves that define `symbol` (abbreviation/definition prose), excluding the use site."""
        hits = []
        for path, value in walk_strings(doc):
            if symbol not in value:
                continue
            if "statement_formal" in path or "revision_history" in path or path.endswith("provenance"):
                continue
            if re.search(r"abbreviat|is defined|definition of|abbreviates", value, re.I):
                hits.append(path)
        return sorted(set(hits))

    af_leaves = find_definition_leaf("AF_{I+}")
    complete_leaves = [p for p in find_definition_leaf("complete(")]
    symbol_probe = {
        "AF_{I+}": {
            "occurrences_whole_file": count("AF_{I+}"),
            "occurrences_in_statement_formal": count("AF_{I+}", statement_formal),
            "definition_leaf_found": bool(af_leaves),
            "definition_leaf": af_leaves[0] if af_leaves else None,
        },
        "complete(": {
            "occurrences_whole_file": count("complete("),
            "occurrences_in_statement_formal": count("complete(", statement_formal),
            "definition_leaf_found": bool(ip.get("completeness_definition")) or bool(complete_leaves),
            "definition_leaf": "i_plus.completeness_definition" if ip.get("completeness_definition") else (complete_leaves[0] if complete_leaves else None),
            "declared_as_named_predicate": bool(complete_leaves),
        },
        "visible_singularity_from_I_plus": {
            "occurrences_whole_file": count("visible_singularity_from_I_plus"),
            "occurrences_in_statement_formal": count("visible_singularity_from_I_plus", statement_formal),
            "definition_leaf_found": vis.get("predicate_name") == "visible_singularity_from_I_plus",
        },
        "P_WCC": {
            "occurrences_whole_file": count("P_WCC"),
            "occurrences_in_negation_normal_form": count("P_WCC", nnf),
            "definition_leaf_found": bool(find_definition_leaf("P_WCC")),
            "definition_leaf": (find_definition_leaf("P_WCC") or [None])[0],
        },
    }
    undefined_in_statement = [s for s, v in symbol_probe.items()
                              if v.get("occurrences_in_statement_formal", 0) > 0
                              and not v["definition_leaf_found"]]
    undefined_in_nnf = [s for s, v in symbol_probe.items()
                        if v.get("occurrences_in_negation_normal_form", 0) > 0
                        and not v["definition_leaf_found"]]

    # --- E. duplicate keys / future-dated provenance (CF-14) ---
    dates = {
        "revised_at(last-wins)": doc.get("revised_at"),
        "authored_at": doc.get("authored_at"),
        "f0_binding.checked_at": f0.get("checked_at"),
    }
    date_probe = {}
    for label, value in dates.items():
        dt = parse_iso(value)
        date_probe[label] = {
            "value": value,
            "parses": dt is not None,
            "delta_seconds_vs_probe_time": round((dt - now).total_seconds(), 1) if dt else None,
            "future_dated": bool(dt and (dt - now).total_seconds() > 60),
        }

    # --- F. class_contract_pointer resolution under the canonical-path policy ---
    ptr = str(doc.get("class_contract_pointer", ""))
    ptr_path, _, ptr_anchor = ptr.partition("#")
    ptr_top = ptr_anchor.split(".")[0] if ptr_anchor else ""
    ptr_target = ROOT / ptr_path if ptr_path else None
    ptr_exists = bool(ptr_target and ptr_target.is_file())

    def anchor_resolve(path: Path, anchor: str):
        """Walk a dotted anchor path; returns (resolves, missing_segment)."""
        if not (path and path.is_file()) or not anchor:
            return False, anchor or ""
        try:
            data = yaml.safe_load(path.read_text())
        except Exception:
            return False, "<unparseable>"
        cur = data
        for seg in anchor.split("."):
            if isinstance(cur, dict) and seg in cur:
                cur = cur[seg]
            else:
                return False, seg
        return True, None

    canonical = ROOT / CANONICAL_F0
    authoring = ROOT / AUTHORING_F0
    target_resolves, target_missing = anchor_resolve(ptr_target, ptr_anchor)
    canonical_resolves, canonical_missing = anchor_resolve(canonical, ptr_anchor)
    authoring_resolves, authoring_missing = anchor_resolve(authoring, ptr_anchor)
    supp = str(doc.get("class_contract_supplement_pointer", "") or "")
    supp_path, _, supp_anchor = supp.partition("#")
    supp_target = ROOT / supp_path if supp_path else None
    supp_resolves, supp_missing = anchor_resolve(supp_target, supp_anchor)
    pointer_probe = {
        "pointer": ptr,
        "path": ptr_path,
        "anchor": ptr_anchor,
        "anchor_top_segment": ptr_top,
        "target_exists": ptr_exists,
        "target_is_canonical_f0": bool(ptr_target and ptr_target.resolve() == canonical.resolve()),
        "anchor_resolves_in_target": target_resolves,
        "anchor_missing_segment_in_target": target_missing,
        "target_sha256": sha256(ptr_target) if ptr_exists else None,
        "canonical_f0": CANONICAL_F0,
        "canonical_f0_exists": canonical.is_file(),
        "canonical_f0_sha256": sha256(canonical) if canonical.is_file() else None,
        "canonical_f0_has_anchor": canonical_resolves,
        "canonical_f0_missing_segment": canonical_missing,
        "authoring_f0": AUTHORING_F0,
        "authoring_f0_exists": authoring.is_file(),
        "authoring_f0_sha256": sha256(authoring) if authoring.is_file() else None,
        "authoring_f0_has_anchor": authoring_resolves,
        "authoring_f0_missing_segment": authoring_missing,
        "supplement_pointer": supp,
        "supplement_path": supp_path,
        "supplement_anchor": supp_anchor,
        "supplement_exists": bool(supp_target and supp_target.is_file()),
        "supplement_anchor_resolves": supp_resolves,
        "supplement_anchor_missing_segment": supp_missing,
    }

    # --- G. f0_binding resolution (declared F0 hash and declared consistency evidence) ---
    f0_path = ROOT / str(f0.get("declared_f0_artifact", ""))
    f0_measured = sha256(f0_path) if f0_path.is_file() else None
    ce_path = ROOT / str(f0.get("consistency_evidence", ""))
    ce_measured = sha256(ce_path) if ce_path.is_file() else None
    ce_mtime_dt = (datetime.datetime.fromtimestamp(ce_path.stat().st_mtime).astimezone()
                   if ce_path.is_file() else None)
    ce_mtime = ce_mtime_dt.isoformat() if ce_mtime_dt else None
    binding_checked = parse_iso(f0.get("checked_at"))
    f0_probe = {
        "declared_artifact": f0.get("declared_f0_artifact"),
        "declared_sha256": f0.get("declared_f0_sha256"),
        "measured_sha256": f0_measured,
        "resolves": bool(f0_measured and f0.get("declared_f0_sha256") == f0_measured),
        "checked_at": f0.get("checked_at"),
        "consistency_evidence": f0.get("consistency_evidence"),
        "consistency_evidence_exists": ce_path.is_file(),
        "consistency_evidence_declared_sha256": f0.get("consistency_evidence_sha256"),
        "consistency_evidence_measured_sha256": ce_measured,
        "consistency_evidence_mtime": ce_mtime,
        "consistency_evidence_resolves": bool(
            ce_measured and f0.get("consistency_evidence_sha256") == ce_measured),
        "consistency_evidence_newer_than_binding": bool(
            ce_mtime_dt and binding_checked and ce_mtime_dt > binding_checked),
        "class_contract_supplement": f0.get("class_contract_supplement"),
        "class_contract_supplement_sha256": (
            sha256(ROOT / str(f0.get("class_contract_supplement")))
            if f0.get("class_contract_supplement") and (ROOT / str(f0.get("class_contract_supplement"))).is_file()
            else None),
    }

    # --- H. cross-schema single-frozen-data-class criterion ---
    def d0_of(d):
        return str((((d.get("quantifiers") or {}).get("domains") or {}).get("D0") or {}).get("definition", ""))

    def norm_text(s):
        s = re.sub(r"\[[^\]]*\]", " ", str(s))
        s = re.sub(r"\([^)]*\)", " ", s)
        return re.sub(r"\s+", " ", s).strip().lower()

    def d0_norm(d):
        return norm_text(d0_of(d))

    def deep_norm(x):
        if isinstance(x, dict):
            return {k: deep_norm(v) for k, v in x.items()}
        if isinstance(x, list):
            return [deep_norm(v) for v in x]
        if isinstance(x, str):
            return norm_text(x)
        return x

    def reg_contract(d):
        rc = d.get("regularity_class") or {}
        sv = rc.get("sobolev_variant") or {}
        return {"default": norm_text(rc.get("default")), "s": norm_text(sv.get("s")),
                "delta": norm_text(sv.get("delta")), "spaces": norm_text(sv.get("spaces"))}

    cross = {}
    sib_dcs = {}
    sib_docs = {}
    for node, rel in SIBLINGS.items():
        p = ROOT / rel
        if not p.is_file():
            cross[node] = {"present": False}
            continue
        sib = yaml.safe_load(p.read_text())
        sib_dc = sib.get("data_class", {}) or {}
        sib_dcs[node] = sib_dc
        sib_docs[node] = sib
        keys = sorted(set(sib_dc) | set(dc))
        differing = [k for k in keys
                     if json.dumps(sib_dc.get(k), sort_keys=True) != json.dumps(dc.get(k), sort_keys=True)]
        norm_differing = [k for k in keys
                          if json.dumps(deep_norm(sib_dc.get(k)), sort_keys=True)
                          != json.dumps(deep_norm(dc.get(k)), sort_keys=True)]
        cross[node] = {
            "present": True,
            "path": rel,
            "sha256": sha256(p),
            "data_class_keys": sorted(sib_dc.keys()),
            "data_class_key_diff_vs_this": sorted(set(sib_dc) ^ set(dc)),
            "data_class_differing_keys_vs_this": differing,
            "data_class_normalized_differing_keys_vs_this": norm_differing,
            "data_class_json_equal": not differing,
            "regularity_class_equal": sib_dc.get("regularity_class") == dc.get("regularity_class"),
            "regularity_numeric_contract_equal": reg_contract(sib_dc) == reg_contract(dc),
            "regularity_contract_diff_vs_this": sorted(k for k in reg_contract(dc)
                                                       if reg_contract(sib_dc).get(k) != reg_contract(dc).get(k)),
            "d0_definition": d0_of(sib),
            "d0_equal": d0_of(sib) == d0_def,
            "d0_equal_normalized": d0_norm(sib) == d0_norm(doc),
        }
    if len(sib_docs) == 2:
        (na, sa), (nb, sb) = list(sib_docs.items())
        (_, da), (_, db) = list(sib_dcs.items())
        pair_keys = sorted(set(da) | set(db))
        pair_diff = [k for k in pair_keys
                     if json.dumps(da.get(k), sort_keys=True) != json.dumps(db.get(k), sort_keys=True)]
        pair_norm_diff = [k for k in pair_keys
                          if json.dumps(deep_norm(da.get(k)), sort_keys=True)
                          != json.dumps(deep_norm(db.get(k)), sort_keys=True)]
        pairwise = {"pair": [na, nb], "data_class_differing_keys": pair_diff,
                    "data_class_normalized_differing_keys": pair_norm_diff,
                    "regularity_numeric_contract_equal": reg_contract(da) == reg_contract(db),
                    "d0_equal_normalized": d0_norm(sa) == d0_norm(sb)}
    else:
        pairwise = {}
    strict_all = (len(cross) == 2 and all(v.get("data_class_json_equal") for v in cross.values()))
    norm_all = (strict_all or (len(cross) == 2
                and all(not v.get("data_class_normalized_differing_keys_vs_this") for v in cross.values())
                and (not pairwise or not pairwise.get("data_class_normalized_differing_keys", []))))
    shared_d0_norm = (len(cross) == 2 and all(v.get("d0_equal_normalized") for v in cross.values())
                      and (not pairwise or pairwise.get("d0_equal_normalized", False)))
    shared_reg_contract = (len(cross) == 2 and all(v.get("regularity_numeric_contract_equal") for v in cross.values())
                           and (not pairwise or pairwise.get("regularity_numeric_contract_equal", False)))
    shared_reasons = []
    for node, v in cross.items():
        if not v.get("present"):
            shared_reasons.append(f"{node}: absent")
            continue
        if v["data_class_differing_keys_vs_this"]:
            shared_reasons.append(f"{node}: data_class keys differ {v['data_class_differing_keys_vs_this']}")
        if v.get("data_class_normalized_differing_keys_vs_this"):
            shared_reasons.append(
                f"{node}: also differ after annotation strip {v['data_class_normalized_differing_keys_vs_this']}")
    if pairwise and pairwise["data_class_differing_keys"]:
        shared_reasons.append(f"F2a/F2b: data_class keys differ {pairwise['data_class_differing_keys']}")
    if d0_ill_typed:
        shared_reasons.append("all three: D0 has an uninstantiable smooth branch")
    cross_summary = {
        "single_frozen_data_class_shared_by_F1_F2a_F2b": bool(strict_all),
        "strict_data_class_shared": bool(strict_all),
        "normalized_data_class_shared": bool(norm_all),
        "shared_d0_domain_normalized": bool(shared_d0_norm),
        "shared_regularity_numeric_contract": bool(shared_reg_contract),
        "d0_normalized_equal_all_three": bool(shared_d0_norm),
        "reasons_not_shared": shared_reasons,
        "pairwise_F2a_F2b": pairwise,
    }

    # --- I. class-id token scan, leakage/inflation guard ---
    tokens = Counter()
    for path, s in walk_strings(doc):
        for t in CLASS_TOKEN.findall(s):
            tokens[t] += 1
    unknown_tokens = sorted(t for t in tokens if t not in FROZEN_CLASSES)
    file_class = doc.get("class_id")
    inflation = {
        "conclusion_type": concl.get("conclusion_type"),
        "i_plus_role": ip.get("role"),
        "i_plus_in_conclusion": ip.get("in_conclusion"),
        "visibility_role": vis.get("role"),
        "visibility_in_conclusion": vis.get("in_conclusion"),
        "forbidden_strengthenings": concl.get("forbidden_strengthenings"),
        "scc_tokens_in_conclusion_block": sorted({t for t in CLASS_TOKEN.findall(json.dumps(concl))
                                                  if t != file_class}),
    }

    # --- J. frozen class-separation detector + regression corpus ---
    sys.path.insert(0, str(ROOT / "research_map"))
    import class_separation as cs  # noqa: E402
    sep_findings = cs.findings_for_text(text, args.artifact)
    reg_run = subprocess.run(
        [sys.executable, str(ROOT / "runtime/bin/classsep_regression.py")],
        cwd=str(ROOT), capture_output=True, text=True, timeout=120)
    classsep_report = {
        "findings": sep_findings,
        "regression_cmd": "python3 runtime/bin/classsep_regression.py",
        "regression_returncode": reg_run.returncode,
        "regression_stdout_tail": (reg_run.stdout or "").strip()[-500:],
        "regression_pass": reg_run.returncode == 0,
    }

    # --- K. frozen binding gate ---
    gate_script = ROOT / "artifacts/formulation/tools/check_class_schema.py"
    gate = subprocess.run(
        [sys.executable, str(gate_script), str(art)],
        cwd=str(ROOT), capture_output=True, text=True, timeout=120)
    gate_report = {"cmd": "python3 artifacts/formulation/tools/check_class_schema.py " + args.artifact,
                   "returncode": gate.returncode,
                   "stdout": gate.stdout.strip()[:2000],
                   "stderr": gate.stderr.strip()[:600],
                   "pass": gate.returncode == 0}

    # --- L. map declared-hash binding for node F1 ---
    map_path = ROOT / "research_map/research_map.json"
    map_sha = sha256(map_path) if map_path.is_file() else None
    node_report = {"map_sha256": map_sha, "node_found": False}
    if map_path.is_file():
        try:
            mp = json.loads(map_path.read_text())
        except Exception as exc:  # pragma: no cover - defensive
            mp = None
            node_report["map_parse_error"] = str(exc)
        if isinstance(mp, dict):
            for g in mp.get("groups", []) or []:
                for n in g.get("nodes", []) or []:
                    if isinstance(n, dict) and n.get("id") == "F1":
                        node_report.update({
                            "node_found": True,
                            "artifact": n.get("artifact"),
                            "status": n.get("status"),
                            "declared_sha256": n.get("declared_sha256"),
                            "declared_hash_present": bool(n.get("declared_sha256")),
                            "artifact_sha256_measured": n.get("artifact_sha256_measured"),
                            "declared_hash_matches_measured": n.get(
                                "declared_hash_matches_measured",
                                (bool(n.get("declared_sha256"))
                                 and n.get("declared_sha256") == n.get("artifact_sha256_measured"))),
                        })
    node_report["measured_matches_this_probe"] = (node_report.get("artifact_sha256_measured") == h1)

    # --- M. stability ---
    h3 = sha256(art)
    stability = {
        "sha256_before_read": h1,
        "sha256_after_parse": h2,
        "sha256_after_probes": h3,
        "drifted_during_read": not (h1 == h2 == h3),
        "stable": h1 == h2 == h3,
    }

    report = {
        "schema_version": "0.1",
        "artifact_type": "f1_review_probe",
        "node_id": "F1",
        "class_id": file_class,
        "gate": "G-FORM",
        "actor": "worker-088",
        "probe_time": now.isoformat(),
        "artifact": args.artifact,
        "artifact_sha256": h1,
        "artifact_bytes": art.stat().st_size,
        "artifact_mtime": art.stat().st_mtime,
        "review_history_present": "review_history" in doc,
        "yaml_duplicate_keys": dupes,
        "date_probe": date_probe,
        "required_fields": required,
        "required_fields_missing": sorted(k for k, v in required.items() if not v),
        "binder_domains": binder_rows,
        "unresolved_binder_domains": unresolved,
        "d0_probe": d0_probe,
        "d0_ill_typed_for_smooth_branch": d0_ill_typed,
        "tail_predicate_probe": tail_probe,
        "symbol_definedness": symbol_probe,
        "undefined_symbols_in_statement_formal": undefined_in_statement,
        "undefined_symbols_in_negation_normal_form": undefined_in_nnf,
        "class_contract_pointer": pointer_probe,
        "f0_binding": f0_probe,
        "cross_schema": cross,
        "cross_schema_summary": cross_summary,
        "class_tokens": dict(sorted(tokens.items())),
        "unknown_class_tokens": unknown_tokens,
        "inflation_probe": inflation,
        "class_separation": classsep_report,
        "binding_gate": gate_report,
        "map_node": node_report,
        "stability": stability,
        "unresolved_items": doc.get("unresolved_items"),
    }
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n")
    print(json.dumps({k: report.get(k) for k in (
        "artifact", "artifact_sha256", "yaml_duplicate_keys",
        "required_fields_missing", "d0_ill_typed_for_smooth_branch",
        "tail_predicate_probe", "undefined_symbols_in_statement_formal",
        "class_contract_pointer", "cross_schema_summary", "binding_gate",
        "map_node")}, indent=2, default=str))
    print(json.dumps({"stability": report["stability"], "class_separation_pass": classsep_report["regression_pass"],
                      "binding_gate_pass": gate_report["pass"]}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
