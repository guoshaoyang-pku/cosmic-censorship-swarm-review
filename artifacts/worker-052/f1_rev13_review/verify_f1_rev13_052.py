#!/usr/bin/env python3
"""W052-F1-REV13-REVIEW-01: independent, blind G-FORM review instrument for F1.

Target: schemas/af_wcc_vacuum.yaml (class AF-WCC-VAC-GEN) at the
FROZEN rev29 pin d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d.

The instrument is read-only with respect to the repository canonical tree. It reads
pinned snapshots under ../pinned/ (copied at 00:58 +08:00) and re-measures the live
paths only to detect drift. Every check is deterministic; the enumerated finite-preorder
control is exact (all 355 preorders on 4 labelled points).

Output: report.json (machine) next to this file. Exit 0 iff every hard check passes.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # artifacts/worker-052/f1_rev13_review -> repo root
PINNED = HERE / "pinned"

TARGET_REL = "schemas/af_wcc_vacuum.yaml"
TARGET_PIN = "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d"
F0_REL = "research_map/formulation_taxonomy.yaml"
F0_PIN = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
SUPP_REL = "artifacts/formulation/formulation_taxonomy.yaml"
EVID_REL = "artifacts/formulation/evidence/taxonomy_consistency.json"
EVID_PIN = "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b"
CASES_REL = "schemas/taxonomy_cases.jsonl"
FROZEN_REL = "artifacts/formulation/FROZEN.json"
CLASS_ID = "AF-WCC-VAC-GEN"
COMPOSITE = re.compile(r"c\s*0\s*(?:or|and|/|,|\+)\s*c\s*2|c\s*2\s*(?:or|and|/|,|\+)\s*c\s*0|c0c2|c2c0", re.I)
FROZEN_CLASSES = {
    "AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH",
}

checks: list[dict] = []
controls: list[dict] = []


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def add(cid: str, desc: str, expected, observed, ok: bool, evidence=None, hard: bool = True):
    checks.append({
        "id": cid, "description": desc, "expected": expected, "observed": observed,
        "pass": bool(ok), "hard": hard, "evidence": evidence or [],
    })


def load_yaml_strict(path: Path):
    """yaml.safe_load plus duplicate-key detection (prior F1 defect class)."""
    class DupLoader(yaml.SafeLoader):
        pass

    dups: list[str] = []

    def construct_mapping(loader, node, deep=False):
        seen = set()
        for k, _ in node.value:
            key = loader.construct_object(k, deep=deep)
            if key in seen:
                dups.append(str(key))
            seen.add(key)
        return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)

    DupLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping)
    doc = yaml.load(path.read_text(), Loader=DupLoader)
    return doc, dups


def walk_strings(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from walk_strings(v, f"{path}.{k}" if path else str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk_strings(v, f"{path}[{i}]")
    elif isinstance(o, str):
        yield path, o


def resolve_leaf(doc, dotted: str):
    """Resolve 'regularity.data_regularity' against the schema doc."""
    cur = doc
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


# ---------------------------------------------------------------------------
# preorders / causal finite model (independent reproduction of T1 and T2)
# ---------------------------------------------------------------------------
def all_preorders(n=4):
    """All reflexive-transitive relations on {0..n-1}; 355 for n=4."""
    pairs = [(i, j) for i in range(n) for j in range(n) if i != j]
    for bits in range(1 << len(pairs)):
        rel = {(i, i) for i in range(n)}
        for b, (i, j) in enumerate(pairs):
            if bits >> b & 1:
                rel.add((i, j))
        # transitive?
        if all((a, c) in rel for a, b in rel for x, c in rel if x == b):
            # reflexive by construction
            yield rel


def past(rel, q):
    return {p for p in range(4) if (p, q) in rel}


def chains(rel):
    """All non-empty causally ordered sequences (strictly increasing index, chain in rel)."""
    for L in range(1, 5):
        for seq in itertools.permutations(range(4), L):
            seq2 = list(seq)
            if all((seq2[i], seq2[i + 1]) in rel for i in range(L - 1)):
                yield seq2


# ---------------------------------------------------------------------------
def main() -> int:
    target = PINNED / "target_f1.yaml"
    f0 = PINNED / "f0_canonical.yaml"
    supp = PINNED / "supplement_taxonomy.yaml"
    evid = PINNED / "taxonomy_consistency.json"
    cases = PINNED / "taxonomy_cases.jsonl"
    frozen = PINNED / "frozen.json"

    doc, dups = load_yaml_strict(target)
    strict_doc, strict_dups = load_yaml_strict(f0) if f0.exists() else (None, [])
    supp_doc = yaml.safe_load(supp.read_text()) if supp.exists() else None

    # C01 pin stability of the snapshots themselves
    add("C01", "target snapshot hash equals the FROZEN rev29 pin",
        TARGET_PIN, sha(target), sha(target) == TARGET_PIN,
        [f"{TARGET_REL}#{TARGET_PIN}", "artifacts/formulation/FROZEN.json"])
    add("C02", "F0 snapshot hash equals the declared F0 pin and G-F0 canonical hash",
        F0_PIN, sha(f0), sha(f0) == F0_PIN, [f"{F0_REL}#{F0_PIN}"])
    add("C03", "companion consistency-evidence snapshot hash equals the declared pin",
        EVID_PIN, sha(evid), sha(evid) == EVID_PIN, [f"{EVID_REL}#{EVID_PIN}"])

    # C04 strict YAML: no duplicate keys anywhere in target or F0
    add("C04", "strict YAML parse: no duplicate mapping keys",
        {"target_dups": 0, "f0_dups": 0}, {"target_dups": dups, "f0_dups": strict_dups},
        not dups and not strict_dups, ["F1-review-090 HF duplicate-key defect class"])

    # C05 single frozen class identity
    cid = doc.get("class_id")
    comps = doc.get("class_components", {})
    comp_tokens = [str(v) for v in comps.values()]
    single_ok = cid == CLASS_ID and not any(COMPOSITE.search(t) for t in [str(cid)] + comp_tokens)
    add("C05", "exactly one frozen class id; no composite/unknown class token in identity fields",
        {"class_id": CLASS_ID, "composite_tokens": 0},
        {"class_id": cid, "components": comps}, single_ok,
        [f"{TARGET_REL}:3", f"{TARGET_REL}:24-29", f"known four: {sorted(FROZEN_CLASSES)}"])

    # C06 composite-token context census: every composite hit must sit in a
    # prohibition / negation / mention context, never a first-order merge assertion
    merge_assert = re.compile(
        r"are\s+one|is\s+one|one\s+class|single\s+class|one\s+schema|single\s+schema|unified|merged|"
        r"share[sd]?\s+one|combined|same\s+class|treated?\s+as\s+one|into\s+a\s+single|"
        r"strictly\s+(?:stronger|weaker)", re.I)
    prohibiting = re.compile(
        r"not\s+this\s+class|forbidden|must\s+not|never|no\s+artifact|composite regularity|"
        r"not\s+equivalent|is\s+NOT|anti_scope|phrases_that_are_not|is\s+registered\s+as|variant",
        re.I)
    composite_hits = []
    for path, s in walk_strings(doc):
        t = s.replace("^", "")
        for m in COMPOSITE.finditer(t):
            lo, hi = max(0, m.start() - 90), min(len(t), m.end() + 90)
            ctx = t[lo:hi]
            composite_hits.append({
                "path": path, "match": m.group(0), "context": ctx.strip(),
                "merge_assert": bool(merge_assert.search(ctx)),
                "prohibiting": bool(prohibiting.search(ctx)),
            })
    bad_hits = [h for h in composite_hits if h["merge_assert"] and not h["prohibiting"]]
    add("C06", "composite C0/C2 token census: all hits prohibitions/negations/mentions, none asserted as one class",
        {"hits": "n/a", "asserted_merges": 0},
        {"hits": len(composite_hits), "asserted_merges": len(bad_hits), "paths": sorted({h['path'] for h in composite_hits})},
        not bad_hits, [f"{TARGET_REL}:253,278,283-290 (prohibition contexts)"])

    # C07 quantifier structure
    q = doc.get("quantifiers", {})
    ordered = q.get("ordered", [])
    kinds = [b.get("kind") for b in ordered]
    expect_kinds = ["forall", "exists", "forall", "exists", "forall", "not_exists"]
    domains = q.get("domains", {})
    dom_ids = [b.get("domain_id") for b in ordered]
    q_ok = kinds == expect_kinds and all(d in domains and domains[d].get("definition") for d in dom_ids) \
        and q.get("order_matters") is True and bool(q.get("order_note")) and bool(q.get("negation")) \
        and bool(q.get("negation_normal_form"))
    add("C07", "ordered quantifier prefix (forall-exists-comesager-forall-exists-forall-not_exists), "
               "all domains defined, order_matters with rationale, negation stated",
        {"kinds": expect_kinds, "domains_defined": True, "order_matters": True},
        {"kinds": kinds, "domains": dom_ids, "order_matters": q.get("order_matters")},
        q_ok, [f"{TARGET_REL}:40-83"])

    # C08 domain definition_refs resolve to schema leaves
    refs = {d: domains[d].get("definition_ref") for d in domains if isinstance(domains.get(d), dict)}
    unresolved = {d: r for d, r in refs.items() if not r or resolve_leaf(doc, str(r)) is None}
    add("C08", "every quantifier domain definition_ref resolves to a schema leaf",
        {"unresolved": {}}, {"unresolved": unresolved, "refs": refs}, not unresolved,
        [f"{TARGET_REL}:56-74"])

    # C09 statement_formal symbol anchoring
    stmt = str(doc.get("conclusion", {}).get("statement_formal", ""))
    symbols = {
        "AF_{I+}": bool(re.search(r"AF_\{I\+\}", stmt)),
        "complete": bool(re.search(r"\bcomplete\(", stmt)),
        "visible_singularity_from_I_plus": bool(re.search(r"visible_singularity_from_I_plus", stmt)),
    }
    anchors = {
        "AF_{I+}": bool(doc.get("i_plus", {}).get("predicate_abbreviation")),
        "complete": bool(doc.get("i_plus", {}).get("completeness_definition")),
        "visible_singularity_from_I_plus": bool(doc.get("visibility", {}).get("predicate_name"))
        and bool(doc.get("visibility", {}).get("definition")),
    }
    dangling = [s for s in symbols if symbols[s] and not anchors[s]]
    add("C09", "every predicate symbol realized in statement_formal has a definition/abbreviation anchor "
               "(no dangling symbol); quantified binders folded into predicates are declared",
        {"dangling": []}, {"present": symbols, "anchored": anchors, "dangling": dangling}, not dangling,
        [f"{TARGET_REL}:194 (AF_{{I+}} abbreviation)", f"{TARGET_REL}:196 (completeness_definition)",
         f"{TARGET_REL}:212-214 (visibility predicate)"],
        hard=True)

    # C10 axes agreement with the frozen F0 class contract
    f0_cls = (strict_doc or {}).get("classes", {}).get(CLASS_ID, {})
    f0_axes = f0_cls.get("axes", {})
    concl = doc.get("conclusion", {})
    axes_ok = (f0_axes.get("family") == concl.get("family") == comps.get("censorship")) and \
        (f0_axes.get("conclusion_type") == concl.get("conclusion_type")) and \
        (f0_axes.get("regularity_token") in (None, "none") and comps.get("regularity_token") in (None, "none"))
    add("C10", "F1 axes/conclusion agree with the frozen F0 class contract (family WCC, "
               "conclusion_type weak_cosmic_censorship, regularity_token none)",
        {"family": "WCC", "conclusion_type": "weak_cosmic_censorship", "regularity_token": None},
        {"f0": {"family": f0_axes.get("family"), "conclusion_type": f0_axes.get("conclusion_type"),
                "regularity_token": f0_axes.get("regularity_token")},
         "f1": {"family": concl.get("family"), "conclusion_type": concl.get("conclusion_type"),
                "regularity_token": comps.get("regularity_token")}},
        axes_ok, [f"{F0_REL}#{F0_PIN}:161-180", f"{TARGET_REL}:24-29,240-246"])

    # C11 conclusion not inflated (no SCC content as conclusion)
    scc_concl = re.compile(r"inextendib|cauchy[\s_-]*horizon|strong[\s_-]*cosmic|extendib", re.I)
    conclusion_text = " ".join(str(x) for x in [concl.get("statement_natural_language"),
                                                 concl.get("statement_formal"),
                                                 concl.get("conclusion_type")])
    inflation = bool(scc_concl.search(conclusion_text))
    forbids_scc = any("inextendib" in str(x).lower() for x in concl.get("forbidden_strengthenings", []))
    add("C11", "conclusion_type is weak_cosmic_censorship, conclusion fields carry no SCC "
               "inextendibility content, and SCC content is listed as a forbidden strengthening",
        {"scc_tokens_in_conclusion": False, "scc_listed_forbidden": True},
        {"scc_tokens_in_conclusion": inflation, "scc_listed_forbidden": forbids_scc},
        (not inflation) and forbids_scc, [f"{TARGET_REL}:240-261"])

    # C12 topology / data_class / regularity required fields non-empty
    topo = doc.get("topology", {})
    dc = doc.get("data_class", {})
    reg = doc.get("regularity", {})
    need = {
        "topology.spacetime_dimension": topo.get("spacetime_dimension"),
        "topology.slice_topology": topo.get("slice_topology"),
        "topology.I_plus_topology": topo.get("I_plus_topology"),
        "data_class.equations": dc.get("equations"),
        "data_class.constraints": bool(dc.get("constraints")),
        "regularity.data_regularity": reg.get("data_regularity"),
        "regularity.solution_regularity": reg.get("solution_regularity"),
        "regularity.extension_regularity": "null-for-WCC" if reg.get("extension_regularity") is None else "PRESENT",
    }
    missing = [k for k, v in need.items() if v in (None, "", False)]
    add("C12", "topology / data_class / regularity required fields present and typed",
        {"missing": []}, {"fields": need, "missing": missing}, not missing, [f"{TARGET_REL}:85-139"])

    # C13 genericity block complete and non-vacuous
    gen = doc.get("genericity", {})
    gen_ok = gen.get("kind") == "residual_comeager" and bool(gen.get("ambient_space")) \
        and bool(gen.get("topology_or_measure")) and bool(gen.get("generic_set")) \
        and bool(gen.get("membership_ruling")) and gen.get("ambient_space_is_data_space") is True \
        and len(gen.get("transfer_failures", [])) >= 3 and len(gen.get("variants", [])) >= 3
    add("C13", "genericity is residual/comeager with named ambient space, subspace topology, "
               "membership ruling, transfer failures and variants",
        {"kind": "residual_comeager", "transfer_failures": ">=3", "variants": ">=3"},
        {"kind": gen.get("kind"), "transfer_failures": len(gen.get("transfer_failures", [])),
         "variants": len(gen.get("variants", []))}, gen_ok, [f"{TARGET_REL}:141-174"])

    # C14 i_plus and visibility blocks complete
    ip = doc.get("i_plus", {})
    vis = doc.get("visibility", {})
    ipv_ok = bool(ip.get("definition")) and bool(ip.get("predicate_abbreviation")) \
        and bool(ip.get("completeness_definition")) and bool(ip.get("required_properties")) \
        and bool(vis.get("predicate_name")) and bool(vis.get("definition")) \
        and bool(vis.get("negation_conclusion")) and bool(vis.get("must_not_conflate")) \
        and bool(vis.get("witness_protocol"))
    add("C14", "i_plus and visibility conclusion blocks complete: definition, predicate anchor, "
               "completeness, negation, conflation guards, witness protocol",
        {"i_plus": "complete", "visibility": "complete"},
        {"i_plus_keys": sorted(ip.keys()), "visibility_keys": sorted(vis.keys())}, ipv_ok,
        [f"{TARGET_REL}:190-223"])

    # C15 falsifier is decidable and correctly tiered
    fal = doc.get("falsifier", {})
    t1 = fal.get("tier_1", {})
    t2 = fal.get("tier_2", {})
    fal_ok = (t1.get("refutes") == CLASS_ID and bool(t1.get("witness_type"))
              and len(t1.get("machine_checkable_steps", [])) >= 4
              and bool(t1.get("proof_obligations")) and bool(t1.get("non_machine_checkable_step"))
              and t2.get("labelling_required") == "refutes_strengthening_only"
              and len(fal.get("schema_falsifiers", [])) >= 3)
    add("C15", "falsifier tiered and witness-shaped: tier_1 refutes the class with >=4 machine-checkable "
               "steps plus named proof obligations; tier_2 labelled strengthening-only",
        {"tier_1_machine_steps": ">=4", "tier_2": "refutes_strengthening_only", "schema_falsifiers": ">=3"},
        {"tier_1_steps": len(t1.get("machine_checkable_steps", [])),
         "tier_2_labelling": t2.get("labelling_required"),
         "schema_falsifiers": len(fal.get("schema_falsifiers", []))}, fal_ok, [f"{TARGET_REL}:263-279"])

    # C16 f0_binding chain resolves at the declared hashes
    bind = doc.get("f0_binding", {})
    f0_live = sha(ROOT / F0_REL)
    evid_live = sha(ROOT / EVID_REL)
    supp_live = sha(ROOT / SUPP_REL)
    bind_ok = (bind.get("declared_f0_sha256") == f0_live == F0_PIN) \
        and (bind.get("consistency_evidence_sha256") == evid_live == EVID_PIN) \
        and (bind.get("class_contract_supplement_pointer", "").split("#")[0] == SUPP_REL) \
        and resolve_leaf(strict_doc, f"classes.{CLASS_ID}") is not None \
        and resolve_leaf(supp_doc or {}, f"class_contracts.{CLASS_ID}") is not None \
        and bool(bind.get("checked_at"))
    add("C16", "evidence-binding chain resolves: declared F0 hash == live F0 == G-F0 pin; "
               "consistency_evidence hash == live companion evidence; both contract pointers resolve",
        {"f0": F0_PIN[:16], "evidence": EVID_PIN[:16], "pointers": "resolve"},
        {"declared_f0": str(bind.get("declared_f0_sha256"))[:16], "live_f0": f0_live[:16],
         "declared_evidence": str(bind.get("consistency_evidence_sha256"))[:16],
         "live_evidence": evid_live[:16], "checked_at": bind.get("checked_at"),
         "supp_live": supp_live[:16]},
        bind_ok, [f"{TARGET_REL}:305", f"{EVID_REL}#{EVID_PIN}", f"{SUPP_REL}"])

    # C17 FROZEN rev29 membership and reproducibility across the two canonical roots
    fz = json.loads(frozen.read_text())
    fz_files = fz.get("files", {})
    fz_entry = fz_files.get(TARGET_REL, {}).get("sha256")
    alt = ROOT / "artifacts/formulation/schemas/af_wcc_vacuum.yaml"
    alt_hash = sha(alt) if alt.exists() else None
    frozen_ok = fz_entry == TARGET_PIN and alt_hash == TARGET_PIN and fz.get("revision") == 29
    add("C17", "FROZEN rev29 lists the target at the pin; the two canonical schema roots are byte-identical",
        {"frozen_entry": TARGET_PIN, "alt_root": TARGET_PIN, "revision": 29},
        {"frozen_entry": fz_entry, "alt_root": alt_hash, "revision": fz.get("revision"),
         "frozen_at": fz.get("frozen_at")}, frozen_ok,
        [f"{FROZEN_REL}", "CF-12 one-canonical-path check"])

    # C18 taxonomy_cases corpus rebinding (CF-20 repair item 1)
    meta = None
    rows = []
    for line in cases.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        (rows if rec.get("record_type") != "meta" else [None])
        if rec.get("record_type") == "meta":
            meta = rec
        else:
            rows.append(rec)
    ref = (meta or {}).get("taxonomy_ref", {})
    unbound = [i for i, r in enumerate(rows) if F0_PIN[:12] not in json.dumps(r)]
    cases_ok = (ref.get("sha256") == F0_PIN and ref.get("revision") == 5 and len(rows) == 36
                and not unbound and (meta or {}).get("counts") == {"positive": 16, "negative": 20})
    add("C18", "taxonomy_cases.jsonl meta + all 36 rows bound to the frozen F0 rev5 hash",
        {"meta_hash": F0_PIN[:16], "rows": 36, "unbound": 0},
        {"meta_hash": str(ref.get("sha256"))[:16], "revision": ref.get("revision"),
         "rows": len(rows), "unbound": len(unbound)}, cases_ok,
        [f"{CASES_REL}#ccf7041b", "CF-20 repair item 1"])

    # C19 companion consistency evidence is the live one and scoped honestly
    ev = json.loads(evid.read_text())
    ev_ok = ev.get("consistent") is True and len(ev.get("classes_compared", [])) == 4 \
        and not ev.get("errors") and not ev.get("contract_divergences")
    add("C19", "companion taxonomy_consistency.json: consistent=true, four classes compared, no errors",
        True, {"consistent": ev.get("consistent"), "classes": len(ev.get("classes_compared", [])),
               "errors": ev.get("errors"), "contract_divergences": ev.get("contract_divergences")},
        ev_ok, [f"{EVID_REL}#{EVID_PIN}"], hard=False)

    # C20 live classsep detector is silent on the target and the pinned detector agrees
    sys.path.insert(0, str(HERE / "pinned"))
    import importlib.util
    cs_path = HERE / "pinned" / "classsep_a8c04fc3.py"
    spec = importlib.util.spec_from_file_location("cs_pinned", cs_path)
    cs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cs)
    live = cs.findings_for_text((ROOT / TARGET_REL).read_text(), "F1")
    cs_ok = live == []
    add("C20", "pinned class-separation detector (a8c04fc3) returns zero findings on the F1 text",
        [], live, cs_ok, ["research_map/class_separation.py#a8c04fc3", "a8c04fc3 classsep"])

    # C21 structural gate control (formulation's own checker) - read-only subprocess
    gate = ROOT / "artifacts/formulation/tools/check_class_schema.py"
    r = subprocess.run([sys.executable, str(gate), "--json", str(ROOT / TARGET_REL)],
                       capture_output=True, text=True)
    try:
        gout = json.loads(r.stdout)
    except ValueError:
        gout = {"verdict": "PARSE_ERROR", "stderr": r.stderr[-200:]}
    add("C21", "formulation structural gate check_class_schema.py passes at the live pin",
        "pass", gout.get("verdict"), gout.get("verdict") == "pass",
        [f"{TARGET_REL}#{TARGET_PIN}", "artifacts/formulation/tools/check_class_schema.py"])

    # C22 finite-preorder machine check of the rev13 strictness corrections (T1/T2)
    n_pre = 0
    t1_violations = []
    t2_violations = []
    set_separation_finite = []
    for rel in all_preorders(4):
        n_pre += 1
        for ch in chains(rel):
            whole_q = {}
            for qq in range(4):
                Jq = past(rel, qq)
                whole = all(pt in Jq for pt in ch)
                tail = any(all(pt in Jq for pt in ch[k:]) for k in range(len(ch)))
                whole_q[qq] = whole
                if whole != tail:
                    t1_violations.append({"rel": sorted(rel), "chain": ch, "q": qq})
                if tail and not whole:
                    t1_violations.append({"rel": sorted(rel), "chain": ch, "q": qq, "kind": "tail_not_whole"})
                # T2: tail => union
                union = any(pt in Jq for pt in ch)
                if tail and not union:
                    t2_violations.append({"rel": sorted(rel), "chain": ch, "q": qq})
            # SET-vs-tail separation: find a chain in the union but with no single-q tail
            union_all = all(any((pt, qq) in rel for qq in range(4)) for pt in ch)
            if union_all and not any(any(all(pt in past(rel, qq) for pt in ch[k:]) for k in range(len(ch)))
                                     for qq in range(4)):
                set_separation_finite.append({"rel": sorted(rel), "chain": ch})
    add("C22", "finite causal-model control: on all 355 preorders on 4 points, the single-q tail and "
               "whole-curve readings coincide (T1) and the tail entails the set/union reading (T2); "
               "no finite separation of the SET pair exists (T3/T4 need the infinite omega-chain)",
        {"preorders": 355, "t1_violations": 0, "t2_violations": 0},
        {"preorders": n_pre, "t1_violations": len(t1_violations), "t2_violations": len(t2_violations),
         "finite_set_separations": len(set_separation_finite)},
        n_pre == 355 and not t1_violations and not t2_violations,
        ["rev13 delta note: W076-GFORM-STRICTNESS-RECONCILE-06 T1/T2", f"{TARGET_REL}:73,214,235"])

    # C23 declared cross-artifact divergence L-FORM-03 (advisory; owner-declared)
    f0_text = str(resolve_leaf(strict_doc, f"variants") or "")
    f0_var = None
    for v in (strict_doc or {}).get("variants", []):
        if v.get("variant_id") == "SET":
            f0_var = v
    f0_dir = "stronger" if f0_var and "stronger" in str(f0_var.get("definition", "")) else "?"
    f1_dir = "weaker" if "strictly WEAKER" in str(vis.get("definition", "")) or \
        "strictly WEAKER" in json.dumps(doc.get("class_identity_variants", [])) else "?"
    blocker = None
    for line in (ROOT / "comms/outbox/astra-lead-formulation.jsonl").read_text().splitlines():
        if "L-FORM-03" in line:
            blocker = json.loads(line).get("event_id")
    add("C23", "cross-artifact SET strength label: F0-frozen says 'strictly stronger' (class-statement sense) "
               "while F1 rev13 says 'strictly weaker than ... predicate'; the owner declared it as blocker "
               "L-FORM-03 for a controller F0 erratum/reopen decision",
        {"declared_blocker": "L-FORM-03"},
        {"f0_label": f0_dir, "f1_label": f1_dir, "blocker_event": blocker},
        f0_dir == "stronger" and f1_dir == "weaker" and blocker is not None,
        [f"{F0_REL}#{F0_PIN}:200", f"{TARGET_REL}:235",
         "comms/outbox/astra-lead-formulation.jsonl#L-FORM-03"], hard=False)

    # C24 declared stale outbound corpus binding L-FORM-04 (advisory; owner-declared)
    ft_path = ROOT / "schemas/f1_falsifier_tests.jsonl"
    ft_rows = [json.loads(l) for l in ft_path.read_text().splitlines() if l.strip()]
    stale = [r for r in ft_rows if r.get("binding_sha256") == "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3"]
    add("C24", "f1_falsifier_tests.jsonl rows still bind F1 rev12 (cce9c601); they are not rev13 evidence "
               "until rebound (owner-declared blocker L-FORM-04)",
        {"rows_total": len(ft_rows), "stale_rows": 0},
        {"rows_total": len(ft_rows), "stale_rows": len(stale)}, len(stale) == 0,
        [f"{TARGET_REL}#{TARGET_PIN}", "schemas/f1_falsifier_tests.jsonl",
         "comms/outbox/astra-lead-formulation.jsonl#L-FORM-04"], hard=False)

    # C25 ledger references resolve by id (advisory: L1 owns verification depth)
    ledger = {}
    for line in (ROOT / "ledger/theorems.jsonl").read_text().splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        ledger[rec.get("theorem_id") or rec.get("id")] = rec
    cited = [r.get("theorem_id") for r in doc.get("l1_ledger_refs", [])]
    missing_ledger = [t for t in cited if t not in ledger]
    add("C25", "every theorem_id cited by l1_ledger_refs exists in ledger/theorems.jsonl",
        {"missing": []}, {"cited": cited, "missing": missing_ledger}, not missing_ledger,
        ["ledger/theorems.jsonl"], hard=False)

    # C26 review_status honesty at the reviewed pin
    rs = doc.get("review_status", {})
    add("C26", "review_status at the reviewed pin is pending with no self-declared independent verdicts",
        {"verdict": "pending", "independent_reviewers": []},
        {"verdict": rs.get("verdict"), "independent_reviewers": rs.get("independent_reviewers"),
         "gate": rs.get("gate")},
        rs.get("verdict") == "pending" and not rs.get("independent_reviewers"), [f"{TARGET_REL}:326-330"])

    # C28 citation-depth cross-check: schema l1_status vs ledger's own review depth (advisory)
    depth_rows = []
    over = []
    for r in doc.get("l1_ledger_refs", []):
        t = r.get("theorem_id")
        lrec = ledger.get(t, {})
        row = {
            "theorem_id": t,
            "schema_l1_status": r.get("l1_status"),
            "schema_citation_status": r.get("citation_status"),
            "ledger_content_status": lrec.get("content_status"),
            "ledger_verification_status": lrec.get("verification_status"),
            "ledger_review_status": lrec.get("review_status"),
            "ledger_acceptance_authority": str(lrec.get("acceptance_authority"))[:60],
        }
        depth_rows.append(row)
        if r.get("citation_status") and "verified" in str(r.get("citation_status")) \
                and str(lrec.get("review_status")) != "independently_reviewed":
            over.append(t)
    add("C28", "citation-depth cross-check: no l1_ledger_refs row claims a stronger verification depth "
               "than the ledger's own verification_status/review_status records (advisory; L1 owns depth)",
        {"overstated": []}, {"rows": depth_rows, "overstated": over}, not over,
        ["ledger/theorems.jsonl", f"{TARGET_REL}:292-303"], hard=False)

    # C27 live drift: the canonical paths still measure the reviewed pins at run time
    live_target = sha(ROOT / TARGET_REL)
    live_frozen = sha(ROOT / FROZEN_REL)
    add("C27", "no drift at run time: live target still measures the reviewed pin; live FROZEN recorded",
        {"live_target": TARGET_PIN, "live_frozen": "recorded"},
        {"live_target": live_target, "live_frozen": live_frozen}, live_target == TARGET_PIN,
        [f"{TARGET_REL}#{TARGET_PIN}", f"{FROZEN_REL}#{live_frozen[:12]}"])

    # ------------------------------------------------------------------
    # controls: mutants of the pinned target must be caught by hard checks
    # ------------------------------------------------------------------
    def target_copy() -> dict:
        return yaml.safe_load(target.read_text())

    def run_mutant(mid, desc, mutate, check_ids):
        d = target_copy()
        mutate(d)
        tmp = HERE / f"_mutant_{mid}.yaml"
        tmp.write_text(yaml.safe_dump(d, sort_keys=False, width=110))
        mdoc = yaml.safe_load(tmp.read_text())
        detected = {}
        # re-run the subset of review logic on the mutant
        if "C05" in check_ids:
            mc = mdoc.get("class_id")
            mc_ok = mc == CLASS_ID and not COMPOSITE.search(str(mc))
            detected["C05"] = not mc_ok
        if "C06" in check_ids:
            bad = 0
            for p, s in walk_strings(mdoc):
                for m in COMPOSITE.finditer(s):
                    ctx = s[max(0, m.start() - 90):m.end() + 90]
                    if merge_assert.search(ctx) and not prohibiting.search(ctx):
                        bad += 1
            detected["C06"] = bad > 0
        if "C07" in check_ids:
            detected["C07"] = not bool(mdoc.get("quantifiers", {}).get("ordered"))
        if "C16" in check_ids:
            detected["C16"] = mdoc.get("f0_binding", {}).get("declared_f0_sha256") != F0_PIN
        if "C11" in check_ids:
            detected["C11"] = not mdoc.get("conclusion", {}).get("conclusion_type")
        if "C20" in check_ids:
            detected["C20"] = cs.findings_for_text(tmp.read_text(), "F1") != []
        tmp.unlink()
        controls.append({"id": mid, "description": desc, "checks": check_ids,
                         "detected_by": detected, "detected": any(detected.values())})

    run_mutant("M1", "class_id replaced by a composite C0/C2 token", 
               lambda d: d.__setitem__("class_id", "AF-SCC-C0/C2-VAC-GEN"), ["C05", "C06"])
    run_mutant("M2", "quantifier prefix deleted", lambda d: d.__setitem__("quantifiers", {}), ["C07"])
    run_mutant("M3", "declared F0 binding hash corrupted",
               lambda d: d["f0_binding"].__setitem__("declared_f0_sha256", "0" * 64), ["C16"])
    run_mutant("M4", "first-order merge assertion inserted into the natural-language conclusion",
               lambda d: d["conclusion"].__setitem__(
                   "statement_natural_language", "C0 and C2 are one class in the declaration surface."),
               ["C06", "C20"])
    run_mutant("M5", "conclusion_type deleted", lambda d: d["conclusion"].pop("conclusion_type"), ["C11"])

    # null control: the pinned target itself must pass every hard check
    hard_fail = [c["id"] for c in checks if c["hard"] and not c["pass"]]
    controls.append({"id": "NULL", "description": "pinned F1 target passes every hard check",
                     "detected_by": {}, "detected": not hard_fail})
    controls_ok = all(c["detected"] for c in controls)

    verdict = "ACCEPT" if (not hard_fail and controls_ok) else "REVISE"
    report = {
        "task_id": "W052-F1-REV13-REVIEW-01",
        "reviewer": "worker-052",
        "blind": True,
        "target": {"path": TARGET_REL, "sha256": TARGET_PIN, "class_id": CLASS_ID, "revision": doc.get("revision")},
        "pins": {
            "f0_canonical": {"path": F0_REL, "sha256": F0_PIN},
            "companion_evidence": {"path": EVID_REL, "sha256": EVID_PIN},
            "supplement": {"path": SUPP_REL, "sha256": sha(supp) if supp.exists() else None},
            "taxonomy_cases": {"path": CASES_REL, "sha256": sha(cases)},
            "frozen": {"path": FROZEN_REL, "sha256": sha(frozen), "revision": fz.get("revision")},
            "detector": {"path": "research_map/class_separation.py", "sha256": sha(cs_path)},
        },
        "checks": checks,
        "controls": controls,
        "hard_failures": hard_fail,
        "non_blocking_findings": [c["id"] for c in checks if not c["hard"] and not c["pass"]] ,
        "advisory_declared_items": [
            {"id": "L-FORM-03", "check": "C23",
             "summary": "F0-frozen 'strictly stronger' (class-statement sense) vs F1 rev13 'strictly weaker than the predicate'; owner-declared, controller decision pending (F0 erratum, F0 reopen, or map erratum)."},
            {"id": "L-FORM-04", "check": "C24",
             "summary": "schemas/f1_falsifier_tests.jsonl (25 rows) still binds F1 rev12 cce9c601; not rev13 evidence until rebound."},
        ],
        "verdict_recommendation": verdict,
        "falsifier": ("Re-run this instrument at the same pin: any hard check flips, any control is not detected, "
                      "the target hash differs before/after reading, or a hard-check-accepted field is shown to be "
                      "false (e.g. a genuine C0/C2 merge in the class identity or conclusion)."),
        "authority_note": "worker evidence only; sets no gate verdict, no node status, no validation_status.",
        "created_at": "2026-09-12T01:02:00+08:00",
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=1, sort_keys=False))
    print(f"checks {sum(c['pass'] for c in checks)}/{len(checks)} pass; "
          f"hard failures {hard_fail}; controls {sum(c['detected'] for c in controls)}/{len(controls)} detected; "
          f"verdict recommendation {verdict}")
    return 0 if verdict == "ACCEPT" else 1


if __name__ == "__main__":
    raise SystemExit(main())
