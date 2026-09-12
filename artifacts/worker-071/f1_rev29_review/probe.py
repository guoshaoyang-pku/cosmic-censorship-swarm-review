#!/usr/bin/env python3
"""worker-071 independent machine probe of F1 (AF-WCC-VAC-GEN) at the FROZEN rev29 bytes.

Read-only with respect to canonical artifacts: opens schemas/af_wcc_vacuum.yaml and the
evidence it declares, measures hashes, runs the canonical structural gate as a subprocess,
and writes only under artifacts/worker-071/f1_rev29_review/.
"""
from __future__ import annotations
import hashlib
import itertools
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = ROOT / "schemas/af_wcc_vacuum.yaml"
MIRROR = ROOT / "artifacts/formulation/schemas/af_wcc_vacuum.yaml"
FROZEN = ROOT / "artifacts/formulation/FROZEN.json"
SUITE = ROOT / "schemas/f1_falsifier_tests.jsonl"
OUT = Path(__file__).resolve().parent / "probe.json"
PIN = "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d"
GATE = ROOT / "artifacts/formulation/tools/check_class_schema.py"
SEM = ROOT / "artifacts/worker-06/spec_conformance_audit.py"

import yaml  # noqa: E402


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def strict_load(text: str):
    class L(yaml.SafeLoader):
        pass

    dupes = []

    def cm(loader, node, deep=False):
        keys = []
        for k, _ in node.value:
            key = loader.construct_object(k, deep=deep)
            if key in keys:
                dupes.append(str(key))
            keys.append(key)
        return yaml.SafeLoader.construct_mapping(loader, node, deep)

    L.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, cm)
    return yaml.load(text, Loader=L), dupes


def get(doc, dotted, default=None):
    cur = doc
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
            cur = cur[int(part)]
        else:
            return default
    return cur


def finite_tail_whole_check(max_n=4):
    """Exhaustive check of the rev13 claim: for every finite preorder (causal set) and every
    future-directed chain gamma (i<j => g_i <= g_j), and every q:
        (exists t0: {g_t : t>=t0} subset J^-(q))  <=>  (whole chain subset J^-(q)).
    J^-(q) = {p : p <= q} is past-closed by transitivity."""
    total = 0
    checked = 0
    violations = []
    for n in range(1, max_n + 1):
        pairs = [(i, j) for i in range(n) for j in range(n) if i != j]
        # enumerate reflexive-transitive relations by transitive closure of subsets of i<j pairs
        strict_subsets = [s for r in range(len(pairs) + 1) for s in itertools.combinations(pairs, r)
                          if all(i < j for i, j in s)]
        for rel in strict_subsets:
            le = {(i, i) for i in range(n)} | set(rel)
            changed = True
            while changed:  # transitive closure
                changed = False
                for a, b in list(le):
                    for c, d in list(le):
                        if b == c and (a, d) not in le:
                            le.add((a, d))
                            changed = True
            total += 1
            for q in range(n):
                Jq = {p for p in range(n) if (p, q) in le}
                chains = []
                for L in range(1, n + 1):
                    for g in itertools.permutations(range(n), L):
                        if all((g[i], g[j]) in le for i in range(L) for j in range(i + 1, L)):
                            chains.append(g)
                for g in chains:
                    whole = set(g) <= Jq
                    tail = any(set(g[t0:]) <= Jq for t0 in range(len(g)))
                    checked += 1
                    if whole != tail:
                        violations.append({"n": n, "rel": sorted(le), "q": q, "gamma": list(g)})
    return {"preorders_tested": total, "chain_witness_checks": checked,
            "violations": violations[:5], "violations_total": len(violations),
            "conclusion": "equivalence holds on all finite preorders" if not violations else "EQUIVALENCE FAILS"}


def run(cmd):
    try:
        r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=180)
        return {"cmd": " ".join(str(c) for c in cmd[1:]), "rc": r.returncode,
                "stdout_tail": (r.stdout or "").strip()[-1200:], "stderr_tail": (r.stderr or "").strip()[-400:]}
    except Exception as exc:  # noqa: BLE001
        return {"cmd": " ".join(str(c) for c in cmd[1:]), "rc": None, "error": str(exc)}


def main():
    h_before = sha(SCHEMA)
    doc, dupes = strict_load(SCHEMA.read_text())
    h_after = sha(SCHEMA)
    frozen = json.loads(FROZEN.read_text())
    frozen_pin_schema = ((frozen.get("files") or {}).get("schemas/af_wcc_vacuum.yaml") or {}).get("sha256")
    frozen_pin_mirror = ((frozen.get("files") or {}).get("artifacts/formulation/schemas/af_wcc_vacuum.yaml") or {}).get("sha256")

    q = doc.get("quantifiers", {}) or {}
    domains = q.get("domains", {}) or {}
    ordered = q.get("ordered", []) or []
    topo = doc.get("topology", {}) or {}
    dc = doc.get("data_class", {}) or {}
    reg = doc.get("regularity", {}) or {}
    gen = doc.get("genericity", {}) or {}
    ip = doc.get("i_plus", {}) or {}
    vis = doc.get("visibility", {}) or {}
    nv = doc.get("non_vacuity", {}) or {}
    con = doc.get("conclusion", {}) or {}
    fal = doc.get("falsifier", {}) or {}
    f0 = doc.get("f0_binding", {}) or {}

    # --- acceptance axis matrix (F1 acceptance string + G-FORM rubric criteria) ---
    axes = {
        "class_id": bool(doc.get("class_id")),
        "quantifiers.formal": bool(q.get("formal")),
        "quantifiers.ordered": bool(ordered),
        "quantifiers.domains": bool(domains),
        "quantifiers.order_matters": q.get("order_matters") is True,
        "topology.spacetime_dimension==4": topo.get("spacetime_dimension") == 4,
        "topology.slice_topology": bool(topo.get("slice_topology")),
        "topology.end_structure": bool(topo.get("end_structure")),
        "topology.conformal_boundary": bool(topo.get("conformal_boundary")),
        "topology.forbidden": bool(topo.get("forbidden")),
        "data_class.matter": dc.get("matter") == "none",
        "data_class.cosmological_constant": dc.get("cosmological_constant") == 0,
        "data_class.equations": bool(dc.get("equations")),
        "data_class.constraints": bool(dc.get("constraints")),
        "data_class.regularity_class.s": bool(get(dc, "regularity_class.sobolev_variant.s")),
        "data_class.regularity_class.delta": bool(get(dc, "regularity_class.sobolev_variant.delta")),
        "data_class.asymptotic_decay": bool(dc.get("asymptotic_decay")),
        "data_class.symmetry": bool(dc.get("symmetry")),
        "regularity.data_regularity": bool(reg.get("data_regularity")),
        "regularity.solution_regularity": bool(reg.get("solution_regularity")),
        "regularity.i_plus_regularity": bool(reg.get("i_plus_regularity")),
        "regularity.must_not_conflate": bool(reg.get("must_not_conflate")),
        "genericity.kind": bool(gen.get("kind")),
        "genericity.ambient_space": bool(gen.get("ambient_space")),
        "genericity.topology_or_measure": bool(gen.get("topology_or_measure")),
        "genericity.generic_set": bool(gen.get("generic_set")),
        "genericity.excluded_set": bool(gen.get("excluded_set")),
        "genericity.membership_ruling": bool(gen.get("membership_ruling")),
        "genericity.transfer_failures": bool(gen.get("transfer_failures")),
        "genericity.is_part_of_class": gen.get("is_part_of_class") is True,
        "genericity.class_change_warning": bool(gen.get("class_change_warning")),
        "non_vacuity.condition": bool(nv.get("condition")),
        "non_vacuity.vacuity_falsifier": bool(nv.get("vacuity_falsifier")),
        "i_plus.role": ip.get("role") == "conclusion",
        "i_plus.in_conclusion": ip.get("in_conclusion") is True,
        "i_plus.definition": bool(ip.get("definition")),
        "i_plus.completeness_definition": bool(ip.get("completeness_definition")),
        "i_plus.required_properties": bool(ip.get("required_properties")),
        "visibility.role": vis.get("role") == "conclusion",
        "visibility.in_conclusion": vis.get("in_conclusion") is True,
        "visibility.definition": bool(vis.get("definition")),
        "visibility.negation_conclusion": bool(vis.get("negation_conclusion")),
        "visibility.witness_protocol": bool(vis.get("witness_protocol")),
        "conclusion.conclusion_type": bool(con.get("conclusion_type")),
        "conclusion.statement_formal": bool(con.get("statement_formal")),
        "conclusion.statement_natural_language": bool(con.get("statement_natural_language")),
        "conclusion.forbidden_strengthenings": bool(con.get("forbidden_strengthenings")),
        "falsifier.tier_1": bool(fal.get("tier_1")),
        "falsifier.tier_2": bool(fal.get("tier_2")),
        "falsifier.schema_falsifiers": bool(fal.get("schema_falsifiers")),
        "class_contract_pointer": bool(doc.get("class_contract_pointer")),
        "f0_binding": bool(f0),
        "promotion_rule": bool(doc.get("promotion_rule")),
        "epistemic_status": bool(doc.get("epistemic_status")),
    }
    missing = sorted(k for k, v in axes.items() if not v)

    # --- binder resolution + formal/ordered agreement ---
    binders = [{"kind": r.get("kind"), "binder": r.get("binder"), "domain_id": r.get("domain_id"),
                "resolves": r.get("domain_id") in domains} for r in ordered]
    unresolved = [b for b in binders if not b["resolves"]]
    formal = str(q.get("formal", ""))
    formal_sig = [k for k in ("forall r in D0", "exists G_r", "forall (Sigma,h,K)", "exists a conformal completion", "forall future-inextendible causal geodesics", "not exists q in I+")]
    ordered_sig = [b["kind"] for b in binders]
    d0_def = str((domains.get("D0") or {}).get("definition", ""))

    # --- conclusion / vocabulary ---
    vocab = json.loads((ROOT / "artifacts/formulation/VOCAB_ALIASES.json").read_text())
    ct = con.get("conclusion_type")
    ct_canonical = [k for k, v in (vocab.get("conclusion_type") or {}).items() if ct == k or ct in (v or [])]

    # --- pointers ---
    tax = yaml.safe_load((ROOT / "research_map/formulation_taxonomy.yaml").read_text())
    sup = yaml.safe_load((ROOT / "artifacts/formulation/formulation_taxonomy.yaml").read_text())
    ptr = str(doc.get("class_contract_pointer", ""))
    ptr_path, _, ptr_frag = ptr.partition("#")
    ptr_cls = None
    cur = tax
    for part in ptr_frag.split("."):
        cur = cur.get(part) if isinstance(cur, dict) else None
    if isinstance(cur, dict):
        ptr_cls = cur
    sup_ptr = str(doc.get("class_contract_supplement_pointer", ""))
    sup_path, _, sup_frag = sup_ptr.partition("#")
    cur2 = sup
    for part in sup_frag.split("."):
        cur2 = cur2.get(part) if isinstance(cur2, dict) else None
    sup_cls = cur2 if isinstance(cur2, dict) else None

    # --- f0 chain ---
    f0_art = ROOT / str(f0.get("declared_f0_artifact", ""))
    cons = ROOT / str(f0.get("consistency_evidence", ""))
    sup_file = ROOT / str(f0.get("class_contract_supplement", ""))
    cons_doc = json.loads(cons.read_text()) if cons.is_file() else None
    f0_chain = {
        "declared_f0_artifact": f0.get("declared_f0_artifact"),
        "declared_f0_sha256": f0.get("declared_f0_sha256"),
        "declared_f0_measured": sha(f0_art) if f0_art.is_file() else None,
        "declared_f0_resolved": f0_art.is_file() and sha(f0_art) == f0.get("declared_f0_sha256"),
        "consistency_evidence": f0.get("consistency_evidence"),
        "consistency_evidence_sha256": f0.get("consistency_evidence_sha256"),
        "consistency_evidence_measured": sha(cons) if cons.is_file() else None,
        "consistency_evidence_resolved": cons.is_file() and sha(cons) == f0.get("consistency_evidence_sha256"),
        "consistency_evidence_consistent": (cons_doc or {}).get("consistent"),
        "consistency_evidence_classes": (cons_doc or {}).get("classes_compared"),
        "class_contract_supplement_exists": sup_file.is_file(),
        "class_contract_supplement_pointer_resolves": sup_cls is not None,
        "checked_at": f0.get("checked_at"),
        "refresh_rule": f0.get("rule"),
        "refresh_rule_satisfied": (f0_art.is_file() and sha(f0_art) == f0.get("declared_f0_sha256")
                                   and cons.is_file() and sha(cons) == f0.get("consistency_evidence_sha256")),
    }

    # --- falsifier suite ---
    rows = [json.loads(l) for l in SUITE.read_text().splitlines() if l.strip()]
    bind_hashes = sorted({r.get("binding_sha256") for r in rows})
    suite = {
        "path": "schemas/f1_falsifier_tests.jsonl",
        "sha256": sha(SUITE),
        "frozen_pin": ((frozen.get("files") or {}).get("schemas/f1_falsifier_tests.jsonl") or {}).get("sha256"),
        "rows": len(rows),
        "distinct_binding_sha256": bind_hashes,
        "rows_binding_current_pin": sum(1 for r in rows if r.get("binding_sha256") == PIN),
        "rows_binding_superseded": sum(1 for r in rows if r.get("binding_sha256") != PIN),
        "binding_frozen_revision_schema_values": sorted({r.get("binding_frozen_revision_schema") for r in rows}),
        "binding_frozen_revision_values": sorted({r.get("binding_frozen_revision") for r in rows}),
    }
    # re-run the rows' own probes against the current bytes
    probe_rows = []
    for r in rows:
        res = []
        for p in r.get("probe_results", []) or []:
            path, kind, exp = p.get("path"), p.get("kind"), p.get("expected")
            val = get(doc, str(path), "__MISSING__")
            if kind == "equals":
                ok = str(val) == str(exp)
            elif kind == "contains":
                cands = [str(val)]
                if isinstance(val, (list, dict)):
                    cands.append(json.dumps(val, default=str))
                ok = any(exp is not None and str(exp) in c for c in cands)
                if not ok and exp is not None:
                    try:
                        ok = any(re.search(str(exp), c) is not None for c in cands)
                    except re.error:
                        ok = False
            elif kind == "is_none":
                ok = val is None
            elif kind == "is_true":
                ok = val is True
            elif kind == "path_exists":
                ok = val != "__MISSING__"
            elif kind == "nonnull":
                ok = val is not None and val != "__MISSING__"
            else:
                ok = None
            res.append({"path": path, "kind": kind, "pass_now": ok,
                        "expected": str(exp)[:80], "observed": str(val)[:80]})
        probe_rows.append({"test_id": r.get("test_id"), "probes": res,
                           "probes_failing_now": [x for x in res if x["pass_now"] is False]})
    suite["probe_rerun_rows_with_failures"] = [x["test_id"] for x in probe_rows if x["probes_failing_now"]]
    suite["probe_rerun_failure_count"] = sum(len(x["probes_failing_now"]) for x in probe_rows)
    suite["probe_rerun_failures"] = [{"test_id": x["test_id"], **f} for x in probe_rows for f in x["probes_failing_now"]]

    # --- leakage / class separation (own lexical scan of assertive blocks) ---
    scc_tokens = [r"strong cosmic censorship", r"cauchy horizon", r"extension[_ ]regularity",
                  r"\bC0\b.{0,20}extension", r"\bC2\b.{0,20}extension"]
    composite = re.compile(r"(C0|C2|C\^?0|C\^?2)\s*(or|and|/)\s*(C0|C2|C\^?0|C\^?2)", re.I)
    intext = re.compile(r"inextendib", re.I)
    assertive = [("scope_statement", doc.get("scope_statement")),
                 ("conclusion.statement_formal", con.get("statement_formal")),
                 ("conclusion.statement_natural_language", con.get("statement_natural_language")),
                 ("conclusion.conclusion_type", con.get("conclusion_type")),
                 ("visibility.definition", vis.get("definition")),
                 ("visibility.negation_conclusion", vis.get("negation_conclusion")),
                 ("i_plus.definition", ip.get("definition")),
                 ("i_plus.completeness_definition", ip.get("completeness_definition")),
                 ("falsifier.tier_1.refutes", get(fal, "tier_1.refutes")),
                 ("falsifier.tier_2.refutes", get(fal, "tier_2.refutes")),
                 ("non_vacuity.condition", nv.get("condition"))]
    leaks = []
    for where, txt in assertive:
        s = str(txt or "")
        for tok in scc_tokens:
            if re.search(tok, s, re.I):
                leaks.append({"where": where, "token": tok, "text": s[:120]})
        if composite.search(s):
            leaks.append({"where": where, "token": "COMPOSITE_C0_C2", "text": s[:120]})
        for m in intext.finditer(s):
            window = s[max(0, m.start() - 60):m.start() + 60]
            if not re.search(r"geodesic", window, re.I):
                leaks.append({"where": where, "token": "INEXTENDIB_NON_GEODESIC", "text": window})
    classsep = run([sys.executable, str(ROOT / "research_map/class_separation.py")]) if (ROOT / "research_map/class_separation.py").is_file() else None

    gate = run([sys.executable, str(GATE), "--json", "artifacts/formulation/schemas/af_wcc_vacuum.yaml"])
    try:
        gate_doc = json.loads(gate["stdout_tail"])
        gate_verdict, gate_failed = gate_doc.get("verdict"), gate_doc.get("failed_rules")
    except Exception:  # noqa: BLE001
        gate_verdict, gate_failed = None, None
    sem = run([sys.executable, str(SEM), "artifacts/formulation/schemas/af_wcc_vacuum.yaml"]) if SEM.is_file() else None
    sem_verdict, sem_failed, sem_undecided, sem_doc_sha = None, None, None, None
    if sem and sem.get("rc") is not None:
        try:
            r = subprocess.run([sys.executable, str(SEM), "artifacts/formulation/schemas/af_wcc_vacuum.yaml"],
                               cwd=str(ROOT), capture_output=True, text=True, timeout=180)
            sem_doc = json.loads(r.stdout)
            sem_verdict = sem_doc.get("verdict")
            sem_failed = sem_doc.get("failed_rules")
            sem_undecided = sem_doc.get("undecided_rules")
            sem_doc_sha = sem_doc.get("doc_sha256")
        except Exception as exc:  # noqa: BLE001
            sem_verdict = f"parse_error:{exc}"
    raw_text = SCHEMA.read_text()
    symbol_pwcc = {
        "P_WCC_occurrences_whole_file": len(re.findall(r"\bP_WCC\b", raw_text)),
        "P_WCC_definition_leaf_found": bool(re.search(r"^\s*P_WCC\s*:", raw_text, re.M))
        or bool(re.search(r"P_WCC\s*:=", raw_text)),
    }

    report = {
        "probe": "worker-071 F1 rev29 independent machine probe",
        "created_at_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "schema": "schemas/af_wcc_vacuum.yaml",
        "sha256_before_read": h_before,
        "sha256_after_read": h_after,
        "pin_expected": PIN,
        "pin_matches": h_before == h_after == PIN,
        "mirror_sha256": sha(MIRROR),
        "mirror_matches_schema": sha(MIRROR) == h_before,
        "frozen_rev29_schema_pin": frozen_pin_schema,
        "frozen_rev29_mirror_pin": frozen_pin_mirror,
        "frozen_pin_matches": frozen_pin_schema == h_before and frozen_pin_mirror == h_before,
        "duplicate_yaml_keys": dupes,
        "revision": doc.get("revision"),
        "revised_at": doc.get("revised_at"),
        "acceptance_axes_total": len(axes),
        "acceptance_axes_present": sum(1 for v in axes.values() if v),
        "acceptance_axes_missing": missing,
        "binders": binders,
        "unresolved_binder_domains": unresolved,
        "ordered_quantifier_signature": ordered_sig,
        "formal_contains_expected_prefix": {s: (s in formal) for s in formal_sig},
        "d0_tagged_union": bool(re.search(r"tagged disjoint union|r\s*=\s*smooth", d0_def)),
        "d0_formal_binder": "forall r in D0" in formal,
        "d0_binder_is_s_delta_pair": any(b.get("binder") == "(s,delta)" for b in binders),
        "conclusion_type": ct,
        "conclusion_type_canonical_entries": ct_canonical,
        "conclusion_type_is_scc": bool(ct_canonical and "scc" in ct_canonical[0]),
        "class_contract_pointer": ptr,
        "class_contract_pointer_resolves": ptr_cls is not None,
        "class_contract_taxonomy_conclusion_type": get(ptr_cls, "conclusion.type") if ptr_cls else None,
        "supplement_pointer": sup_ptr,
        "supplement_pointer_resolves": sup_cls is not None,
        "f0_binding_chain": f0_chain,
        "falsifier_suite": suite,
        "tail_whole_finite_check": finite_tail_whole_check(),
        "visibility_strictness": {
            "d5_states_equivalent": "EQUIVALENT to the tail form" in str(get(domains, "D5.definition")),
            "visibility_definition_states_equivalent": "EQUIVALENT" in str(vis.get("definition")),
            "variant_set_relation_states_weaker": "strictly WEAKER" in str(get(doc, "class_identity_variants.0.relation")),
            "d5_contains_rev12_stronger_claim": "strictly STRONGER" in str(get(domains, "D5.definition")),
            "visibility_definition_contains_rev12_stronger_claim": "strictly STRONGER" in str(vis.get("definition")),
            "variant_set_relation_contains_rev12_stronger_claim": "strictly STRONGER" in str(get(doc, "class_identity_variants.0.relation")),
        },
        "symbol_definedness": symbol_pwcc,
        "assertive_leak_scan": {"hits": leaks, "n": len(leaks)},
        "structural_gate": {"rc": gate["rc"], "verdict": gate_verdict, "failed_rules": gate_failed, "stdout_tail": gate["stdout_tail"]},
        "semantic_auditor": {"rc": sem["rc"] if sem else None, "verdict": sem_verdict,
                             "failed_rules": sem_failed, "undecided_rules": sem_undecided,
                             "doc_sha256": sem_doc_sha, "stdout_tail": sem["stdout_tail"] if sem else None},
    }
    h_final = sha(SCHEMA)
    report["sha256_after_all_probes"] = h_final
    report["bytes_stable_across_probe"] = h_final == h_before == PIN
    OUT.write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(json.dumps({k: report[k] for k in (
        "sha256_before_read", "pin_matches", "frozen_pin_matches", "duplicate_yaml_keys",
        "revision", "acceptance_axes_present", "acceptance_axes_total", "acceptance_axes_missing",
        "unresolved_binder_domains", "conclusion_type", "class_contract_pointer_resolves",
        "f0_binding_chain", "tail_whole_finite_check", "visibility_strictness",
        "assertive_leak_scan", "structural_gate", "semantic_auditor")}, indent=2, default=str))
    print("SUITE:", json.dumps({k: suite[k] for k in (
        "rows", "distinct_binding_sha256", "rows_binding_current_pin", "rows_binding_superseded",
        "binding_frozen_revision_schema_values", "probe_rerun_failure_count",
        "probe_rerun_rows_with_failures", "probe_rerun_failures")}, indent=2, default=str))
    print("bytes_stable_across_probe:", report["bytes_stable_across_probe"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
