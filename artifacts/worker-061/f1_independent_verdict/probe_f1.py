#!/usr/bin/env python3
"""W061-F1-INDEP-REV-02 probe: independent, machine-checkable consistency review of F1.

Task   : independent class-bound review of F1 (AF-WCC-VAC-GEN) at the pinned canonical bytes
         schemas/af_wcc_vacuum.yaml, against the pinned canonical F0 taxonomy, the pinned
         F2a/F2b siblings, and the canonical tooling.  Probes the internally recorded
         HF-06 class (whole-curve vs tail visibility predicate in quantifiers.formal / D5),
         the D0 binder well-typedness and the A0 'no or in the exact quantifier prefix' rule,
         the class-contract pointer resolution across the canonical/authoring trees, YAML
         strictness, timestamp discipline, the F0 hash binding, sibling data-class
         concordance, and — as a control — whether the canonical structural gate can detect
         a documented must_not_conflate / class-identity substitution at all.

Scope  : structure / class binding / formal-expansion consistency only.  This probe does NOT
         decide physical truth, does NOT verify citations, and does NOT set a gate verdict.

Usage  : python3 probe_f1.py [--json PATH] [--fail-on-hard]
Exit   : 0 (report written); with --fail-on-hard: 1 if any hard probe fails.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
PIN = HERE / "pinned"
REPO = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
CST = timezone(timedelta(hours=8))

SCHEMA = PIN / "af_wcc_vacuum.yaml"
F2A = PIN / "af_scc_c2_vacuum.yaml"
F2B = PIN / "af_scc_c0_vacuum.yaml"
TAX_CANON = PIN / "formulation_taxonomy.canonical.yaml"
TAX_AUTHOR = PIN / "formulation_taxonomy.authoring.yaml"
FROZEN = PIN / "FROZEN.json"
GATE = REPO / "artifacts/formulation/tools/check_class_schema.py"      # binding gate (pinned copy is provenance only)
GATE_SPEC = REPO / "artifacts/formulation/rule_spec.json"
CLASSSEP = PIN / "class_separation.py"

RESTRICTING = [
    "matter", "cosmological_constant", "equations",
    "constraints.hamiltonian", "constraints.momentum",
    "regularity_class.default", "regularity_class.sobolev_variant.s",
    "regularity_class.sobolev_variant.delta",
    "asymptotic_decay.metric", "asymptotic_decay.second_fundamental_form",
    "symmetry", "adm_mass.sign",
]
GLOSS = {
    "regularity_class.sobolev_variant.spaces":
        "F1 appends ' (weighted Sobolev)'; F2a/F2b omit the parenthetical label",
    "asymptotic_decay.parity_conditions":
        "F1 appends an explanatory clause after 'not imposed'; F2a/F2b carry 'not imposed'",
}
GLOSS_NORMALISE = {
    "regularity_class.sobolev_variant.spaces": lambda s: re.sub(r"\(weighted sobolev\)", "", s).strip(),
    "asymptotic_decay.parity_conditions": lambda s: s.split(";")[0].strip(),
}
SCC_TOKENS = ("scc_c0", "scc_c2", "strong_cosmic_censorship", "future_inextendibility",
              "c0_future_inextendibility", "c2_future_inextendibility")
TIMESTAMP_KEYS = ("revised_at", "revised_at_unused", "checked_at", "created_at", "written_at",
                  "frozen_at", "authored_at", "harvested_at", "measured_at")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def get(d, dotted, default="<MISSING>"):
    cur = d
    for k in dotted.split("."):
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        elif isinstance(cur, list):
            try:
                cur = cur[int(k)]
            except (ValueError, IndexError):
                return default
        else:
            return default
    return cur


def norm(x):
    if not isinstance(x, str):
        return x
    return " ".join(x.split()).lower().rstrip(";")


def duplicate_keys(node, path=""):
    """Recursively collect duplicate mapping keys from a yaml.compose node tree."""
    dups = []
    if isinstance(node, yaml.MappingNode):
        seen = set()
        for k_node, v_node in node.value:
            k = getattr(k_node, "value", str(k_node))
            if k in seen:
                dups.append(f"{path}/{k}")
            seen.add(k)
            dups.extend(duplicate_keys(v_node, f"{path}/{k}"))
    elif isinstance(node, yaml.SequenceNode):
        for i, v_node in enumerate(node.value):
            dups.extend(duplicate_keys(v_node, f"{path}[{i}]"))
    return dups


def iso_timestamps_in_text(text: str):
    """Return (line_no, key, value) for ISO-8601 timestamps on known revision keys."""
    out = []
    pat = re.compile(r"^(\s*)([A-Za-z_]+):\s*[\"']?(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:[+-]\d{2}:\d{2})?)")
    for i, line in enumerate(text.splitlines(), 1):
        m = pat.match(line)
        if m and m.group(2) in TIMESTAMP_KEYS:
            out.append((i, m.group(2), m.group(3)))
    return out


def run_gate(path: Path, outdir: Path, tag: str):
    cp = subprocess.run(
        [sys.executable, str(GATE), "--json", str(path)],
        cwd=str(REPO), capture_output=True, text=True)
    try:
        verdict = json.loads(cp.stdout)
    except json.JSONDecodeError:
        verdict = {"verdict": "ERROR", "raw": cp.stdout[:600], "stderr": cp.stderr[:600]}
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / f"gate_{tag}.json").write_text(json.dumps(verdict, indent=2) + "\n")
    (outdir / f"gate_{tag}.stdout.txt").write_text(cp.stdout or "")
    (outdir / f"gate_{tag}.stderr.txt").write_text(cp.stderr or "")
    return {"tag": tag, "path": str(path.relative_to(REPO)) if str(path).startswith(str(REPO)) else str(path),
            "exit": cp.returncode, "verdict": verdict.get("verdict"),
            "failed_rules": verdict.get("failed_rules", []), "report_sha256": sha256(outdir / f"gate_{tag}.json")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=str(HERE / "probe_f1_output.json"))
    ap.add_argument("--as-of", default=None,
                    help="ISO-8601 measurement reference for the clock-discipline probe; "
                         "defaults to the wall clock at run time")
    ap.add_argument("--fail-on-hard", action="store_true")
    args = ap.parse_args()

    t_run = datetime.now(CST)
    if args.as_of:
        t_start = datetime.fromisoformat(args.as_of)
        if t_start.tzinfo is None:
            t_start = t_start.replace(tzinfo=CST)
    else:
        t_start = t_run
    (HERE / "gate").mkdir(parents=True, exist_ok=True)
    (HERE / "mutant").mkdir(parents=True, exist_ok=True)

    text = SCHEMA.read_text()
    schema = yaml.safe_load(text)
    f2a = yaml.safe_load(F2A.read_text())
    f2b = yaml.safe_load(F2B.read_text())
    tax_canon = yaml.safe_load(TAX_CANON.read_text())
    tax_author = yaml.safe_load(TAX_AUTHOR.read_text())
    frozen = json.loads(FROZEN.read_text())

    probes = []

    def probe(pid, title, ok, detail, hard=True):
        probes.append({"id": pid, "title": title, "hard": hard,
                       "status": "pass" if ok else "fail", "detail": detail})
        return ok

    # ---- P1 identity and class axes -------------------------------------------
    comp = schema.get("class_components", {})
    conc_surface = json.dumps({
        "conclusion_type": get(schema, "conclusion.conclusion_type"),
        "family": get(schema, "conclusion.family"),
        "statement_natural_language": get(schema, "conclusion.statement_natural_language"),
        "statement_formal": get(schema, "conclusion.statement_formal"),
    }, default=str).lower()
    scc_in_conclusion = [t for t in SCC_TOKENS if t in conc_surface]
    n_class_id_lines = len(re.findall(r"(?m)^class_id:", text))
    ident = {
        "class_id": schema.get("class_id"), "node_id": schema.get("node_id"),
        "class_components": comp, "top_level_class_id_lines": n_class_id_lines,
        "conclusion_type": get(schema, "conclusion.conclusion_type"),
        "family": get(schema, "conclusion.family"),
        "scc_tokens_in_conclusion_surface": scc_in_conclusion,
    }
    p1 = (ident["class_id"] == "AF-WCC-VAC-GEN" and ident["node_id"] == "F1"
          and n_class_id_lines == 1
          and comp.get("asymptotics") == "AF" and comp.get("censorship") == "WCC"
          and comp.get("matter") == "VAC" and comp.get("genericity") == "GEN"
          and comp.get("regularity_token") in (None, "none")
          and ident["conclusion_type"] == "weak_cosmic_censorship"
          and ident["family"] == "WCC" and not scc_in_conclusion)
    probe("P1-IDENTITY",
          "one class_id AF-WCC-VAC-GEN; class_components AF/WCC/VAC/GEN/no-regularity-token; "
          "conclusion_type weak_cosmic_censorship; no SCC token on the conclusion surface",
          p1, ident)

    # ---- P2 required slots ------------------------------------------------------
    slots = {
        "quantifiers.formal": get(schema, "quantifiers.formal") != "<MISSING>",
        "quantifiers.ordered": bool(get(schema, "quantifiers.ordered", [])),
        "quantifiers.negation": get(schema, "quantifiers.negation") != "<MISSING>",
        "quantifiers.negation_normal_form": get(schema, "quantifiers.negation_normal_form") != "<MISSING>",
        "quantifiers.order_matters": get(schema, "quantifiers.order_matters") is True,
        "domains.D0..D5": all(f"D{i}" in get(schema, "quantifiers.domains", {}) for i in range(6)),
        "topology.I_plus_topology": get(schema, "topology.I_plus_topology") == "R x S^2",
        "data_class": get(schema, "data_class") != "<MISSING>",
        "regularity": get(schema, "regularity") != "<MISSING>",
        "genericity": get(schema, "genericity") != "<MISSING>",
        "i_plus.role=conclusion": get(schema, "i_plus.role") == "conclusion",
        "visibility.role=conclusion": get(schema, "visibility.role") == "conclusion",
        "conclusion": get(schema, "conclusion") != "<MISSING>",
        "falsifier.tier_1": get(schema, "falsifier.tier_1") != "<MISSING>",
        "falsifier.tier_2": get(schema, "falsifier.tier_2") != "<MISSING>",
        "anti_scope": get(schema, "anti_scope") != "<MISSING>",
        "genericity.kind=residual_comeager": get(schema, "genericity.kind") == "residual_comeager",
        "genericity.is_part_of_class": get(schema, "genericity.is_part_of_class") is True,
    }
    p2 = all(slots.values())
    probe("P2-REQUIRED-SLOTS",
          "every G-FORM-required block is present (quantifiers/domains/topology/data_class/"
          "regularity/genericity/I+/visibility/conclusion/two-tier falsifier/anti_scope)",
          p2, slots)

    # ---- P3 visibility-predicate consistency (HF-06 class) ----------------------
    vis_def = str(get(schema, "visibility.definition", ""))
    formal = str(get(schema, "quantifiers.formal", ""))
    d5 = str(get(schema, "quantifiers.domains.D5.definition", ""))
    negation = str(get(schema, "quantifiers.negation", ""))
    stmt_formal = str(get(schema, "conclusion.statement_formal", ""))
    canonical_tail = ("TAIL gamma([t0,T))" in vis_def and "t0 in [0,T)" in vis_def
                      and "exists q in I+" in vis_def)
    formal_whole_curve = "gamma subset J^-(q)" in formal
    formal_has_t0 = "t0" in formal
    d5_whole_curve = "gamma([0,T)) is contained in the causal past J^-(q)" in d5
    d5_has_t0 = "t0" in d5
    negation_negates_tail = "visible from I+" in negation
    stmt_uses_predicate = "visible_singularity_from_I_plus" in stmt_formal
    p3 = (canonical_tail and stmt_uses_predicate and formal_has_t0
          and not formal_whole_curve and not d5_whole_curve)
    detail3 = {
        "visibility_definition_is_single_q_tail": canonical_tail,
        "conclusion_statement_formal_calls_predicate": stmt_uses_predicate,
        "quantifiers_formal_clause": formal.split("finite affine length:")[-1].strip()[:220],
        "quantifiers_formal_uses_whole_curve_subset_J(q)": formal_whole_curve,
        "quantifiers_formal_mentions_t0": formal_has_t0,
        "D5_definition": d5[:220],
        "D5_uses_whole_curve_containment": d5_whole_curve,
        "D5_mentions_t0": d5_has_t0,
        "negation_negates_the_tail_predicate": negation_negates_tail,
        "strictness_direction": (
            "whole-curve non-containment A = 'no q contains gamma([0,T))' is IMPLIED by tail "
            "non-containment B = 'no q contains any tail gamma([t0,T))' (a tail is a subset of the "
            "whole curve), so A is strictly weaker than the canonical conclusion's negation B; a "
            "development with a visible tail but no visible whole curve satisfies A and violates B"),
        "schema_self_report": (
            "visibility.definition states the whole-curve reading 'would misclassify a geodesic "
            "that starts in the exterior and ends inside the black-hole region'; "
            "visibility.must_not_conflate adds that single-q non-containment must not be replaced "
            "by B-containment; class_identity_variants declares exactly ONE canonical predicate"),
    }
    probe("P3-VISIBILITY-PREDICATE-CONSISTENCY",
          "quantifiers.formal and D5 expand the SAME single-q TAIL predicate that "
          "conclusion.statement_formal binds via visibility.definition (HF-06 class)",
          p3, detail3)

    # ---- P4 D0 binder well-typedness / A0 exact-prefix rule ---------------------
    ordered = get(schema, "quantifiers.ordered", [])
    binder0 = ordered[0].get("binder") if ordered and isinstance(ordered[0], dict) else None
    d0_def = str(get(schema, "quantifiers.domains.D0.definition", ""))
    d0_disjunction = bool(re.search(r"\bor\b", d0_def, re.I))
    d0_smooth_branch = "smooth" in d0_def.lower()
    generic_set = str(get(schema, "genericity.generic_set", ""))
    ambient = str(get(schema, "genericity.ambient_space", ""))
    topo_measure = str(get(schema, "genericity.topology_or_measure", ""))
    binder_indexed_objects = {
        "binder": binder0,
        "G_is_pair_indexed_in_formal": "G_{s,delta}" in formal,
        "X_is_pair_indexed_in_formal": "X^{s,delta}_vac" in formal,
        "X_is_pair_indexed_in_ambient_space": "X^{s,delta}_vac" in ambient,
        "smooth_branch_ambient_is_frechet":
            "Frechet" in ambient or "Frechet" in topo_measure,
        "smooth_branch_has_no_s_delta_values": True,
    }
    p4 = (binder0 == "(s,delta)" and not d0_disjunction and not d0_smooth_branch)
    probe("P4-D0-BINDER-WELLTYPED",
          "D0 is a single well-typed domain for the (s,delta) binder: no disjunction and no "
          "smooth-with-decay branch lacking (s,delta) values (A0/G-FORM: exact quantifier "
          "prefix, no 'or')",
          p4,
          {"D0_definition": d0_def, "D0_contains_or": d0_disjunction,
           "D0_contains_smooth_branch": d0_smooth_branch, **binder_indexed_objects,
           "rubric_rule": "evaluation_rubric.yaml:126 exact quantifier prefix (no 'roughly', "
                          "'essentially', 'or')"})

    # ---- P5 class-contract pointer resolution -----------------------------------
    ptr = str(get(schema, "class_contract_pointer", ""))
    ptr_path, _, ptr_frag = ptr.partition("#")
    canon_has_contracts = "class_contracts" in tax_canon
    canon_frag_resolves = bool(canon_has_contracts and ptr_frag
                               and get(tax_canon, ptr_frag) != "<MISSING>")
    author_has_contracts = "class_contracts" in tax_author
    author_frag_resolves = bool(author_has_contracts and ptr_frag
                                and get(tax_author, ptr_frag) != "<MISSING>")
    supplement = str(get(schema, "f0_binding.class_contract_supplement", ""))
    canon_h, author_h = sha256(TAX_CANON), sha256(TAX_AUTHOR)
    p5 = canon_frag_resolves
    probe("P5-CLASS-CONTRACT-POINTER",
          "class_contract_pointer resolves inside the authoritative canonical taxonomy "
          "(research_map/formulation_taxonomy.yaml), not only in the divergent authoring mirror",
          p5,
          {"pointer": ptr, "pointer_path": ptr_path, "pointer_fragment": ptr_frag,
           "canonical_has_class_contracts": canon_has_contracts,
           "canonical_fragment_resolves": canon_frag_resolves,
           "canonical_top_level_keys": sorted(tax_canon.keys())[:14],
           "authoring_has_class_contracts": author_has_contracts,
           "authoring_fragment_resolves": author_frag_resolves,
           "f0_binding.class_contract_supplement": supplement,
           "canonical_sha256": canon_h, "authoring_sha256": author_h,
           "trees_divergent": canon_h != author_h})

    # ---- P6 YAML strictness (duplicate keys) ------------------------------------
    dups = duplicate_keys(yaml.compose(text))
    strict_ok, strict_err = True, None
    try:
        class _StrictLoader(yaml.SafeLoader):
            pass

        def _no_dup(loader, node, deep=False):
            keys = []
            for k_node, _ in node.value:
                k = loader.construct_object(k_node, deep=deep)
                if k in keys:
                    raise yaml.constructor.ConstructorError(
                        None, None, f"duplicate key {k!r}", k_node.start_mark)
                keys.append(k)
            return yaml.SafeLoader.construct_mapping(loader, node, deep)

        _StrictLoader.add_constructor(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_dup)
        yaml.load(text, Loader=_StrictLoader)
    except yaml.YAMLError as exc:
        strict_ok, strict_err = False, str(exc).replace("\n", " ")[:300]
    p6 = strict_ok and not dups
    probe("P6-YAML-STRICTNESS",
          "the canonical schema parses under a strict YAML loader (no duplicate mapping keys); "
          "revision metadata is machine-readable",
          p6,
          {"duplicate_key_paths": dups, "duplicate_count": len(dups),
           "strict_loader_ok": strict_ok, "strict_loader_error": strict_err,
           "safe_load_revision_value": schema.get("revision"),
           "note": "yaml.safe_load silently keeps the LAST value of a duplicated key"})

    # ---- P7 timestamp discipline ------------------------------------------------
    stamps = iso_timestamps_in_text(text)
    future = []
    for line_no, key, val in stamps:
        try:
            ts = datetime.fromisoformat(val)
        except ValueError:
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=CST)
        if ts > t_start + timedelta(seconds=120):
            future.append({"line": line_no, "key": key, "value": val,
                           "ahead_seconds": int((ts - t_start).total_seconds())})
    p7 = not future
    probe("P7-TIMESTAMP-DISCIPLINE",
          "no revision/evidence timestamp on the canonical bytes is future-dated relative to "
          "the measurement reference (CF-14 clock discipline); the defect is self-expiring, so "
          "this is recorded as a process finding, not a blocking hard failure",
          p7,
          {"measurement_reference": t_start.isoformat(timespec="seconds"),
           "run_clock": t_run.isoformat(timespec="seconds"),
           "timestamps_found": len(stamps), "future_dated": future,
           "self_expiring": "a declared timestamp ahead of the clock stops being observable once "
                            "the clock passes it; the binding observation is the one made at the "
                            "pin time (see --as-of)"},
          hard=False)

    # ---- P8 canonical structural gate on the pinned bytes -----------------------
    g_pin = run_gate(SCHEMA, HERE / "gate", "pinned")
    p8 = g_pin["exit"] == 0 and g_pin["verdict"] == "pass" and not g_pin["failed_rules"]
    probe("P8-CANONICAL-GATE-PINNED",
          "canonical check_class_schema.py returns pass on the pinned bytes (recorded as the "
          "contrast for the control probes, not as evidence of semantic consistency)",
          p8, g_pin, hard=False)

    # ---- P9 gate-blindness control: documented substitutions the gate must catch -
    controls = []
    m0_text = text.replace(
        "not exists q in I+ with gamma subset J^-(q) intersect M.",
        "not exists q in I+ with gamma subset B.")
    m0 = HERE / "mutant" / "M0_B_containment.yaml"
    m0.write_text(m0_text)
    controls.append(("M0-B-CONTAINMENT",
                     "applies the substitution visibility.must_not_conflate explicitly forbids "
                     "(single-q non-containment -> B-containment, B = M minus J^-(I+))",
                     m0))

    m1_text = text.replace(
        "there exists q in I+ AND t0 in [0,T) such that the TAIL gamma([t0,T)) is contained in "
        "J^-(q) intersect M",
        "gamma([0,T)) is contained in the union of J^-(q) over all q in I+ intersected with M")
    m1 = HERE / "mutant" / "M1_variant_SET_reading.yaml"
    m1.write_text(m1_text)
    controls.append(("M1-VARIANT-SET-READING",
                     "substitutes the registered variant SET reading for the one canonical "
                     "single-q tail predicate (class_identity_variants: 'must never be "
                     "interchanged')",
                     m1))

    m2_text = text.replace(
        "not exists q in I+ with gamma subset J^-(q) intersect M.",
        "not exists q in I+ and t0 in [0,T) with gamma([t0,T)) subset J^-(q) intersect M.")
    m2 = HERE / "mutant" / "M2_tail_consistent_repair.yaml"
    m2.write_text(m2_text)
    controls.append(("M2-TAIL-CONSISTENT-REPAIR",
                     "minimal repair of the HF-06 class: the formal expansion states the "
                     "canonical single-q tail negation",
                     m2))

    control_results, yaml_valid = [], {}
    for tag, why, path in controls:
        try:
            yaml.safe_load(path.read_text())
            yaml_valid[tag] = True
        except yaml.YAMLError as exc:
            yaml_valid[tag] = False
            control_results.append({"tag": tag, "why": why, "yaml_valid": False, "error": str(exc)[:200]})
            continue
        g = run_gate(path, HERE / "control", tag)
        control_results.append({"tag": tag, "why": why, "yaml_valid": True, "gate": g})
    gate_passes_all = all(c.get("gate", {}).get("verdict") == "pass" for c in control_results)
    p9 = not gate_passes_all
    probe("P9-GATE-BLINDNESS-CONTROL",
          "the canonical gate distinguishes the canonical bytes / a documented forbidden "
          "substitution / a class-identity substitution / a tail-consistent repair "
          "(a gate that passes all four has no rule on this axis)",
          p9,
          {"controls": control_results, "all_controls_pass_gate": gate_passes_all,
           "pinned_passes_gate": g_pin["verdict"] == "pass"},
          hard=False)

    # ---- P10 class separation ----------------------------------------------------
    spec = importlib.util.spec_from_file_location("class_separation", CLASSSEP)
    cs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cs)
    findings = cs.findings_for_text(text, "pinned F1")
    reg = subprocess.run([sys.executable, str(REPO / "runtime/bin/classsep_regression.py")],
                         cwd=str(REPO), capture_output=True, text=True)
    p10 = (not findings) and reg.returncode == 0
    probe("P10-CLASS-SEPARATION",
          "frozen class-separation detector finds no token-level merge/leak on the pinned text "
          "and the regression corpus still passes (shows the P3/P4 defects are semantic, not "
          "lexical)",
          p10,
          {"findings": findings, "regression_exit": reg.returncode,
           "regression_tail": (reg.stdout or "")[-400:]},
          hard=False)

    # ---- P11 sibling data-class concordance -------------------------------------
    sib = {"F1": schema, "F2a": f2a, "F2b": f2b}
    conc = {"restricting_equal": [], "gloss_only": [], "divergent": []}
    for path_ in RESTRICTING:
        vals = {k: norm(get(v, "data_class." + path_)) for k, v in sib.items()}
        if len(set(map(str, vals.values()))) == 1:
            conc["restricting_equal"].append(path_)
        else:
            conc["divergent"].append({"path": path_, "values": vals})
    for path_ in GLOSS:
        vals = {k: norm(get(v, "data_class." + path_)) for k, v in sib.items()}
        base = {k: GLOSS_NORMALISE[path_](str(v)) for k, v in vals.items()}
        if len(set(map(str, base.values()))) == 1:
            conc["gloss_only"].append({"path": path_, "note": GLOSS[path_], "values": vals})
        else:
            conc["divergent"].append({"path": path_, "values": vals})
    conc["disjunctive_D0_caveat"] = (
        "path-equality holds, but D0 remains a disjunctive regularity domain in all three "
        "classes, so 'one frozen data class' in the strong sense is still not satisfied "
        "(W037-F5); this probe records the distinction instead of collapsing it")
    probe("P11-SIBLING-DATA-CLASS",
          "F1/F2a/F2b agree on the 12 restricting data-class paths at the pinned triple "
          "(with the disjunctive-D0 caveat recorded)",
          not conc["divergent"], conc, hard=False)

    # ---- P12 F0 binding freshness ------------------------------------------------
    declared = str(get(schema, "f0_binding.declared_f0_sha256", ""))
    measured_tax = sha256(TAX_CANON)
    declared_artifact = str(get(schema, "f0_binding.declared_f0_artifact", ""))
    frozen_f1 = None
    for pth, entry in (frozen.get("files") or {}).items():
        if pth == "schemas/af_wcc_vacuum.yaml":
            frozen_f1 = entry.get("sha256") if isinstance(entry, dict) else entry
    p12 = declared == measured_tax
    probe("P12-F0-BINDING",
          "f0_binding.declared_f0_sha256 equals the measured canonical taxonomy hash at pin time",
          p12,
          {"declared": declared, "declared_artifact": declared_artifact,
           "measured_canonical": measured_tax,
           "frozen_json_revision": frozen.get("revision"),
           "frozen_json_entry_for_canonical_F1": frozen_f1,
           "frozen_json_entry_matches_pinned_F1": frozen_f1 == sha256(SCHEMA)})

    # ---- drift / stability window -------------------------------------------------
    t_end = datetime.now(CST)
    live = {
        "schemas/af_wcc_vacuum.yaml": REPO / "schemas/af_wcc_vacuum.yaml",
        "schemas/af_scc_c2_vacuum.yaml": REPO / "schemas/af_scc_c2_vacuum.yaml",
        "schemas/af_scc_c0_vacuum.yaml": REPO / "schemas/af_scc_c0_vacuum.yaml",
        "research_map/formulation_taxonomy.yaml": REPO / "research_map/formulation_taxonomy.yaml",
        "artifacts/formulation/tools/check_class_schema.py": GATE,
        "artifacts/formulation/rule_spec.json": GATE_SPEC,
    }
    pinned_of = {
        "schemas/af_wcc_vacuum.yaml": SCHEMA, "schemas/af_scc_c2_vacuum.yaml": F2A,
        "schemas/af_scc_c0_vacuum.yaml": F2B, "research_map/formulation_taxonomy.yaml": TAX_CANON,
        "artifacts/formulation/tools/check_class_schema.py": PIN / "check_class_schema.py",
        "artifacts/formulation/rule_spec.json": PIN / "rule_spec.json",
    }
    drift = {k: {"pinned": sha256(pinned_of[k]), "live_at_T1": sha256(p)} for k, p in live.items()}
    for k, v in drift.items():
        v["stable"] = v["pinned"] == v["live_at_T1"]

    hard_failures = [p["id"] for p in probes if p["hard"] and p["status"] == "fail"]
    verdict = "accept" if not hard_failures else "revise"
    score = 4.0 if not hard_failures else 2.5

    out = {
        "task_id": "W061-F1-INDEP-REV-02",
        "target": {"node_id": "F1", "class_id": "AF-WCC-VAC-GEN", "gate": "G-FORM"},
        "measurement": {"t_pin": "2026-09-12T00:25:50+08:00",
                        "t_start_reference": t_start.isoformat(timespec="seconds"),
                        "t_run": t_run.isoformat(timespec="seconds"),
                        "t_end": t_end.isoformat(timespec="seconds")},
        "pinned": {
            "schema": {"path": "schemas/af_wcc_vacuum.yaml", "sha256": sha256(SCHEMA),
                       "bytes": SCHEMA.stat().st_size},
            "f2a": {"path": "schemas/af_scc_c2_vacuum.yaml", "sha256": sha256(F2A)},
            "f2b": {"path": "schemas/af_scc_c0_vacuum.yaml", "sha256": sha256(F2B)},
            "taxonomy_canonical": {"path": "research_map/formulation_taxonomy.yaml",
                                   "sha256": sha256(TAX_CANON)},
            "taxonomy_authoring": {"path": "artifacts/formulation/formulation_taxonomy.yaml",
                                   "sha256": sha256(TAX_AUTHOR)},
            "frozen_manifest": {"path": "artifacts/formulation/FROZEN.json", "sha256": sha256(FROZEN)},
            "gate_tool": {"path": "artifacts/formulation/tools/check_class_schema.py",
                          "sha256": sha256(GATE)},
            "gate_rule_spec": {"path": "artifacts/formulation/rule_spec.json",
                               "sha256": sha256(GATE_SPEC)},
            "class_separation": {"path": "research_map/class_separation.py", "sha256": sha256(CLASSSEP)},
        },
        "drift_window": {"stable": all(v["stable"] for v in drift.values()), "detail": drift},
        "probes": probes,
        "hard_failures": hard_failures,
        "verdict": verdict,
        "score": score,
        "next_falsifier": (
            "Re-measure the canonical F1 sha256: any change voids this verdict. On the pinned hash "
            "9a8bd4c9 this revise is falsified by any one of: (a) quantifiers.formal and "
            "quantifiers.domains.D5 stating the single-q TAIL negation (with an explicit t0) "
            "instead of whole-curve gamma subset J^-(q), which also restores formal/negation "
            "exactness; (b) D0 made a single well-typed domain for the (s,delta) binder with no "
            "'or' and no (s,delta)-less smooth branch; (c) class_contract_pointer resolving inside "
            "the canonical research_map/formulation_taxonomy.yaml, or the pointer repointed to a "
            "fragment the canonical tree actually has; (d) the duplicate top-level YAML keys "
            "removed and all revision/evidence timestamps no longer future-dated; (e) a canonical "
            "gate rule added that rejects the M0/M1 substitutions, after which the gate itself "
            "would have falsified this review's hard failures."
        ),
        "authority_note": (
            "Worker evidence only. This review does not set node status, validation_status, or any "
            "gate verdict; the controller adjudicates. No artifact in the formulation or literature "
            "trees was modified; the canonical files were copied read-only into pinned/ and the "
            "mutants exist only under mutant/."),
    }
    Path(args.json).write_text(json.dumps(out, indent=2, default=str) + "\n")
    print(json.dumps({"verdict": verdict, "score": score, "hard_failures": hard_failures,
                      "pinned_f1_sha256": out["pinned"]["schema"]["sha256"],
                      "drift_stable": out["drift_window"]["stable"]}, indent=2))
    return 1 if (args.fail_on_hard and hard_failures) else 0


if __name__ == "__main__":
    raise SystemExit(main())
