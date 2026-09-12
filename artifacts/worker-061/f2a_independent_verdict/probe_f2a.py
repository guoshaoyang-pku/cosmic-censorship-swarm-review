#!/usr/bin/env python3
"""W061-F2A-INDEP-REV-01 probe: independent, machine-checkable review of F2a.

Task   : independent class-bound verification of F2a (AF-SCC-C2-VAC-GEN) at the pinned
         canonical bytes, against the pinned canonical F0 taxonomy (rev4) and the pinned
         F1/F2b siblings; probes the previously recorded hard failures HF-A1 (dangling
         extension_predicate) and HF-A2 (disjunctive-domain residue), the canonical
         structural gate, the F0 hash binding, class separation, and sibling data-class
         concordance on the restricting projection.

Scope  : structure / class binding / scope only.  This probe does NOT decide physical
         truth, does not verify citations, and does not accept any gate verdict.

Usage  : python3 probe_f2a.py [--json PATH]
Exit   : 0 all probes pass (verdict accept candidate), 1 any hard probe fails.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
PIN = HERE / "pinned"

SCHEMA = PIN / "af_scc_c2_vacuum.yaml"
TAXONOMY = PIN / "formulation_taxonomy.canonical.yaml"
F1 = PIN / "af_wcc_vacuum.yaml"
F2B = PIN / "af_scc_c0_vacuum.yaml"
GATE = PIN / "check_class_schema.py"
CLASSSEP = PIN / "class_separation.py"
REPO = Path("/data3/guoshaoyang/workdir/ai4math-swarm")

RESTRICTING = [
    "matter", "cosmological_constant", "equations",
    "constraints.hamiltonian", "constraints.momentum",
    "regularity_class.default", "regularity_class.sobolev_variant.s",
    "regularity_class.sobolev_variant.delta",
    "asymptotic_decay.metric", "asymptotic_decay.second_fundamental_form",
    "symmetry", "adm_mass.sign",
]
# fields whose declared difference is a gloss only (operative content identical)
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

C2_CONCLUSION_TOKENS = ("scc_c2", "strong_cosmic_censorship_c2", "c2_future_inextendibility")
C0_CONCLUSION_TOKENS = ("scc_c0", "strong_cosmic_censorship_c0", "c0_future_inextendibility")


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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=str(HERE / "probe_f2a_output.json"))
    ap.add_argument("--schema", default=None, help="override schema path (drift checks)")
    ap.add_argument("--taxonomy", default=None)
    ap.add_argument("--f1", default=None)
    ap.add_argument("--f2b", default=None)
    ap.add_argument("--outdir", default=None)
    args = ap.parse_args()

    global SCHEMA, TAXONOMY, F1, F2B
    if args.schema:
        SCHEMA = Path(args.schema)
    if args.taxonomy:
        TAXONOMY = Path(args.taxonomy)
    if args.f1:
        F1 = Path(args.f1)
    if args.f2b:
        F2B = Path(args.f2b)
    outdir = Path(args.outdir) if args.outdir else HERE
    (outdir / "gate").mkdir(parents=True, exist_ok=True)

    schema = yaml.safe_load(SCHEMA.read_text())
    tax = yaml.safe_load(TAXONOMY.read_text())
    f1 = yaml.safe_load(F1.read_text())
    f2b = yaml.safe_load(F2B.read_text())
    cid = "AF-SCC-C2-VAC-GEN"
    contract = tax["classes"][cid]
    axes = contract["axes"]

    probes = []

    def probe(pid, title, ok, detail, hard=True):
        probes.append({"id": pid, "title": title, "hard": hard,
                       "status": "pass" if ok else "fail", "detail": detail})
        return ok

    # ---- P1 identity and class axes -------------------------------------------
    d = schema
    ident = {
        "class_id": d.get("class_id"),
        "node_id": d.get("node_id"),
        "class_components": d.get("class_components"),
        "data_axes": {
            "matter": get(d, "data_class.matter"),
            "cosmological_constant": get(d, "data_class.cosmological_constant"),
            "symmetry": get(d, "data_class.symmetry"),
        },
        "conclusion_type": get(d, "conclusion.conclusion_type"),
        "epistemic_status": d.get("epistemic_status"),
    }
    exp = {"censorship": axes["family"], "matter": "VAC", "asymptotics": "AF",
           "regularity_token": axes["regularity_token"], "genericity": "GEN"}
    p1 = (ident["class_id"] == cid and ident["node_id"] == "F2a"
          and ident["class_components"] == exp
          and ident["data_axes"]["matter"] == "none"
          and ident["data_axes"]["cosmological_constant"] == 0
          and ident["data_axes"]["symmetry"] == axes["symmetry"]
          and any(tok in str(ident["conclusion_type"]).lower() for tok in C2_CONCLUSION_TOKENS))
    ident["expected_class_components"] = exp
    probe("P1-IDENTITY",
          "class_id/node/vacuum/Lambda/symmetry and the C2 conclusion vocabulary",
          p1, ident)

    # ---- P2 extension predicate (HF-A1) ---------------------------------------
    ep = d.get("extension_predicate") or {}
    clause_letters = [c for c in "abcdef" if f"({c})" in str(ep.get("definition", ""))]
    refs = {
        "quantifiers.domains.D3.definition_ref": get(d, "quantifiers.domains.D3.definition_ref"),
        "conclusion.statement_formal mentions predicate": "proper_future_extension_in_class"
        in str(get(d, "conclusion.statement_formal", "")),
        "falsifier tier_1 refutes": str(get(d, "falsifier.tier_1.refutes", ""))[:160],
    }
    p2 = (bool(ep) and ep.get("frozen_direction") == "future"
          and ep.get("frozen_regularity") == "C2"
          and ep.get("frozen_equation_concept") == "classical_ricci"
          and len(clause_letters) == 6 and refs["quantifiers.domains.D3.definition_ref"] == "extension_predicate")
    probe("P2-EXTENSION-PREDICATE-HF-A1",
          "extension_predicate defined with frozen (future,C2,classical_ricci) and clauses (a)-(f)",
          p2, {"clause_letters": clause_letters, "keys": sorted(ep.keys()), "refs": refs})

    # ---- P3 quantifier coherence (HF-A2) --------------------------------------
    ordered = get(d, "quantifiers.ordered", [])
    domains = get(d, "quantifiers.domains", {})
    unresolved_domains = [b.get("domain_id") for b in ordered if b.get("domain_id") not in domains]
    d0_def = str(get(d, "quantifiers.domains.D0.definition", ""))
    canonical_form = "for every admissible (s,delta)" in contract["conclusion"]["text"].lower()
    formal = str(get(d, "quantifiers.formal", ""))
    stmt = str(get(d, "conclusion.statement_formal", ""))
    binder_consistent = ("(s,delta)" in formal and "(s,delta)" in stmt and "D0" in formal and "D0" in stmt)
    disjunction_declared = (" or " in d0_def.lower()) or ("admissible regularity pairs" in d0_def.lower())
    p3 = (not unresolved_domains and canonical_form and binder_consistent and disjunction_declared)
    probe("P3-QUANTIFIER-COHERENCE-HF-A2",
          "D0 binder matches the pinned canonical F0 class statement ('for every admissible (s,delta)'); "
          "every ordered domain_id resolves; no undefined domain",
          p3,
          {"unresolved_domains": unresolved_domains, "canonical_form_matches": canonical_form,
           "D0_definition": d0_def, "formal_uses_s_delta_D0": binder_consistent})

    # ---- P4 canonical structural gate on pinned bytes -------------------------
    cp = subprocess.run([sys.executable, str(REPO / "artifacts/formulation/tools/check_class_schema.py"),
                         "--json", str(SCHEMA)],
                        cwd=str(REPO), capture_output=True, text=True)
    try:
        gate = json.loads(cp.stdout)
    except json.JSONDecodeError:
        gate = {"verdict": "ERROR", "raw": cp.stdout[:400], "stderr": cp.stderr[:400]}
    (outdir / "gate" / "check_class_schema_pinned.json").write_text(json.dumps(gate, indent=2) + "\n")
    (outdir / "gate" / "check_class_schema_pinned.stdout.txt").write_text(cp.stdout)
    p4 = cp.returncode == 0 and gate.get("verdict") == "pass" and not gate.get("failed_rules")
    probe("P4-CANONICAL-GATE",
          "canonical check_class_schema.py returns pass on the pinned bytes",
          p4, {"exit": cp.returncode, "gate": gate})

    # ---- P5 F0 binding freshness ----------------------------------------------
    declared = get(d, "f0_binding.declared_f0_sha256")
    measured_tax = sha256(TAXONOMY)
    p5 = declared == measured_tax
    probe("P5-F0-BINDING",
          "declared_f0_sha256 equals the pinned canonical F0 taxonomy hash",
          p5, {"declared": declared, "measured": measured_tax,
               "declared_path": get(d, "f0_binding.declared_f0_artifact")})

    # ---- P6 class separation ---------------------------------------------------
    spec = importlib.util.spec_from_file_location("class_separation", CLASSSEP)
    cs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cs)
    findings = cs.findings_for_text(SCHEMA.read_text(), "pinned F2a")
    reg = subprocess.run([sys.executable, str(REPO / "runtime/bin/classsep_regression.py")],
                         cwd=str(REPO), capture_output=True, text=True)
    p6 = (not findings) and reg.returncode == 0
    probe("P6-CLASS-SEPARATION",
          "frozen detector finds no class merge/leak on the pinned text; regression corpus still passes",
          p6, {"findings": findings, "regression_exit": reg.returncode,
               "regression_tail": (reg.stdout or "")[-400:]})

    # ---- P7 sibling data-class concordance on the restricting projection -------
    sib = {"F1": f1, "F2a": schema, "F2b": f2b}
    conc = {"restricting_equal": [], "gloss_only": [], "divergent": []}
    for path in RESTRICTING:
        vals = {k: norm(get(v, "data_class." + path)) for k, v in sib.items()}
        if len(set(map(str, vals.values()))) == 1:
            conc["restricting_equal"].append(path)
        else:
            conc["divergent"].append({"path": path, "values": vals})
    for path in GLOSS:
        vals = {k: norm(get(v, "data_class." + path)) for k, v in sib.items()}
        base = {k: GLOSS_NORMALISE[path](str(v)) for k, v in vals.items()}
        if len(set(map(str, base.values()))) == 1:
            conc["gloss_only"].append({"path": path, "note": GLOSS[path], "values": vals})
        else:
            conc["divergent"].append({"path": path, "values": vals})
    p7 = not conc["divergent"]
    probe("P7-SIBLING-DATA-CLASS",
          "F1/F2a/F2b share one data class on the restricting projection (the map's G-FORM unmet is stale here)",
          p7, conc)

    # ---- P8 no conclusion inflation / no WCC content in the conclusion ---------
    # assertive conclusion surfaces only; forbidden_* keys are prohibitions, not assertions
    assertive = {
        "conclusion_type": get(d, "conclusion.conclusion_type"),
        "family": get(d, "conclusion.family"),
        "statement_natural_language": get(d, "conclusion.statement_natural_language"),
        "statement_formal": get(d, "conclusion.statement_formal"),
        "equivalent_rephrasings": get(d, "conclusion.equivalent_rephrasings"),
    }
    conc_text = json.dumps(assertive, default=str).lower()
    wcc_in_conclusion = bool(re.search(r"visible|visibility|weak cosmic|wcc", conc_text))
    c0_asserted = any(tok in str(get(d, "conclusion.conclusion_type", "")).lower()
                      for tok in C0_CONCLUSION_TOKENS)
    p8 = (not wcc_in_conclusion) and (not c0_asserted)
    probe("P8-CONCLUSION-DIRECTION",
          "conclusion carries no WCC/visibility content and no C0 conclusion token",
          p8, {"wcc_tokens_in_conclusion": wcc_in_conclusion, "c0_token_asserted": c0_asserted})

    hard_failures = [p["id"] for p in probes if p["hard"] and p["status"] == "fail"]
    verdict = "accept" if not hard_failures else "revise"
    score = 4.0 if not hard_failures else 2.0
    out = {
        "task_id": "W061-F2A-INDEP-REV-01",
        "target": {"node_id": "F2a", "class_id": cid},
        "pinned": {
            "schema": {"path": "schemas/af_scc_c2_vacuum.yaml", "sha256": sha256(SCHEMA)},
            "taxonomy": {"path": "research_map/formulation_taxonomy.yaml", "sha256": sha256(TAXONOMY)},
            "f1": {"path": "schemas/af_wcc_vacuum.yaml", "sha256": sha256(F1)},
            "f2b": {"path": "schemas/af_scc_c0_vacuum.yaml", "sha256": sha256(F2B)},
            "gate_tool": {"path": "artifacts/formulation/tools/check_class_schema.py", "sha256": sha256(GATE)},
            "class_separation": {"path": "research_map/class_separation.py", "sha256": sha256(CLASSSEP)},
        },
        "probes": probes,
        "hard_failures": hard_failures,
        "verdict": verdict,
        "score": score,
        "next_falsifier": (
            "Re-measure the canonical F2a sha256: any change voids this verdict. On the pinned hash "
            "4b3dfd76 this accept is falsified by (a) a definition_ref that does not resolve, "
            "(b) conclusion.statement_formal losing the D0/(s,delta) binder while the canonical F0 "
            "statement keeps 'for every admissible (s,delta)', (c) a restricting data-class field in "
            "F1/F2a/F2b ceasing to agree, (d) check_class_schema.py returning fail, or (e) the "
            "class-separation detector flagging the file."
        ),
    }
    Path(args.json).write_text(json.dumps(out, indent=2, default=str) + "\n")
    print(json.dumps({"verdict": verdict, "score": score, "hard_failures": hard_failures,
                      "pinned_schema_sha256": out["pinned"]["schema"]["sha256"]}, indent=2))
    return 0 if not hard_failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
