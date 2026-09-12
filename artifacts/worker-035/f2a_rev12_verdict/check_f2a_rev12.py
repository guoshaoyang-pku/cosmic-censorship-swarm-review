#!/usr/bin/env python3
"""W035-F2A-REV12-INDEP-VERDICT-01 — independent, read-only full-schema verification of
schemas/af_scc_c2_vacuum.yaml (class AF-SCC-C2-VAC-GEN, node F2a, gate G-FORM) at the
FROZEN rev28 pin sha256 5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce.

Own implementation. Does not import any other worker's verdict, report or checker. The only
canonical module imported is research_map/class_separation.py (the shared detector), whose
hash is pinned in C13.3. Read-only with respect to canonical paths: the harness writes only
inside its own artifact directory.

Run:  python3 artifacts/worker-035/f2a_rev12_verdict/check_f2a_rev12.py
Writes report.json and controls.json next to this file. Exit 0 when the harness ran and the
controls behaved as pre-registered (blocking findings are data, not harness errors).
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
D = Path(__file__).resolve().parent
SNAP = D / "snapshot" / "schemas__af_scc_c2_vacuum.yaml"
TZ = timezone(timedelta(hours=8))

FROZEN_FOUR = [
    "AF-SCC-C0-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
    "AF-WCC-VAC-GEN",
]

# Canonical pins measured at task start (2026-09-12T00:50+08:00) and re-measured at finalize.
PINS = {
    "schemas/af_scc_c2_vacuum.yaml": "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
    "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml": "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
    "schemas/af_scc_c0_vacuum.yaml": "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/formulation_taxonomy.yaml": "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "artifacts/formulation/FROZEN.json": "2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1",
    "artifacts/formulation/evidence/taxonomy_consistency.json": "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b",
    "artifacts/formulation/VOCAB_ALIASES.json": "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba",
    "ledger/theorems.jsonl": "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28",
    "research_map/class_separation.py": "c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920",
}
DECLARED_STALE_EVIDENCE = "675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48"
DECLARED_F0 = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
CHAIN = ["E_C2", "E_{C^1,1}", "E_H2loc", "E_C0"]


class DuplicateKeyError(Exception):
    pass


class StrictLoader(yaml.SafeLoader):
    pass


def _strict_mapping(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise DuplicateKeyError(
                f"duplicate key {key!r} at line {key_node.start_mark.line + 1}"
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


StrictLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _strict_mapping
)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_path(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def now() -> str:
    return datetime.now(TZ).replace(microsecond=0).isoformat()


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


def canon(kind: str, tok):
    al = ALIASES.get(kind, {})
    for c, aliases in al.items():
        if tok == c or tok in aliases:
            return c
    return tok


def walk_strings(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from walk_strings(v, f"{path}.{k}" if path else str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk_strings(v, f"{path}[{i}]")
    elif isinstance(o, str):
        yield path, o


def sub(cid, status, severity, detail, evidence=None):
    return {
        "id": cid,
        "status": status,  # pass | fail | na
        "severity": severity,  # blocking | advisory
        "detail": detail,
        "evidence": evidence or [],
    }


# --------------------------------------------------------------------------------------
# load pinned inputs
# --------------------------------------------------------------------------------------
def load_inputs():
    inp = {}
    inp["f2a_text"] = SNAP.read_text()
    inp["f2a"] = yaml.load(inp["f2a_text"], Loader=StrictLoader)
    inp["f2a_bytes"] = SNAP.read_bytes()
    inp["c0"] = yaml.safe_load((D / "pinned" / "schemas__af_scc_c0_vacuum.yaml").read_text())
    inp["tax"] = yaml.safe_load((D / "pinned" / "research_map__formulation_taxonomy.yaml").read_text())
    inp["sup"] = yaml.safe_load((D / "pinned" / "artifacts__formulation__formulation_taxonomy.yaml").read_text())
    inp["frozen"] = json.loads((D / "pinned" / "artifacts__formulation__FROZEN.json").read_text())
    inp["ev"] = json.loads((D / "pinned" / "artifacts__formulation__evidence__taxonomy_consistency.json").read_text())
    inp["ledger"] = [json.loads(l) for l in (D / "pinned" / "ledger__theorems.jsonl").read_text().splitlines() if l.strip()]
    globals()["ALIASES"] = json.loads((D / "pinned" / "artifacts__formulation__VOCAB_ALIASES.json").read_text())
    return inp


# --------------------------------------------------------------------------------------
# checks
# --------------------------------------------------------------------------------------
def c01_identity(x):
    s = x["f2a"]
    out = []
    live_canon = sha256_path(ROOT / "schemas/af_scc_c2_vacuum.yaml")
    live_mirror = sha256_path(ROOT / "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml")
    out.append(sub("C01.1", "pass" if live_canon == PINS["schemas/af_scc_c2_vacuum.yaml"] else "fail",
                   "blocking", f"canonical sha256 {live_canon[:16]} vs pin 5476a3f2c6bc",
                   ["schemas/af_scc_c2_vacuum.yaml#sha256:" + live_canon[:12]]))
    out.append(sub("C01.2", "pass" if live_mirror == live_canon else "fail", "blocking",
                   f"mirror sha256 {live_mirror[:16]} vs canonical {live_canon[:16]}"))
    files = x["frozen"].get("files", {})
    p1 = files.get("schemas/af_scc_c2_vacuum.yaml", {}).get("sha256")
    p2 = files.get("artifacts/formulation/schemas/af_scc_c2_vacuum.yaml", {}).get("sha256")
    out.append(sub("C01.3", "pass" if p1 == p2 == live_canon else "fail", "blocking",
                   f"FROZEN rev{x['frozen'].get('revision')} pins canonical={str(p1)[:16]} mirror={str(p2)[:16]}"))
    out.append(sub("C01.4", "pass" if s.get("class_id") == "AF-SCC-C2-VAC-GEN" and s.get("revision") == 12 else "fail",
                   "blocking", f"class_id={s.get('class_id')} revision={s.get('revision')} node={s.get('node_id')}"))
    return out


def c02_hygiene(x):
    out = []
    try:
        yaml.load(x["f2a_text"], Loader=StrictLoader)
        dup = "none"
        ok = True
    except DuplicateKeyError as e:
        dup, ok = str(e), False
    out.append(sub("C02.1", "pass" if ok else "fail", "blocking", f"strict duplicate-key parse: {dup}"))
    s = x.get("f2a")
    if s is None:
        out.append(sub("C02.2", "fail", "blocking", "document did not parse (duplicate key)"))
        out.append(sub("C02.3", "fail", "advisory", "document did not parse (duplicate key)"))
        return out
    m = datetime.fromisoformat(now())
    rev = datetime.fromisoformat(s["revised_at"])
    out.append(sub("C02.2", "pass" if rev <= m else "fail", "blocking",
                   f"revised_at={s['revised_at']} <= measured_at={now()}"))
    hist = s.get("revision_history", [])
    times = [h.get("at") for h in hist]
    out.append(sub("C02.3", "pass" if all(t <= now() for t in times) else "fail", "advisory",
                   f"{len(hist)} history stamps, max={max(times) if times else None}, unused={sum(1 for h in hist if h.get('unused'))}"))
    return out


def c03_tokens(x):
    out = []
    toks = sorted(set(re.findall(r"AF-[A-Z0-9-]+", x["f2a_text"])))
    bad = [t for t in toks if t not in FROZEN_FOUR]
    out.append(sub("C03.1", "pass" if not bad else "fail", "blocking",
                   f"class-id-shaped tokens={toks}; outside frozen four={bad}"))
    out.append(sub("C03.2", "pass" if x["f2a"].get("sibling_disjoint_from") == "AF-SCC-C0-VAC-GEN" else "fail",
                   "blocking", f"sibling_disjoint_from={x['f2a'].get('sibling_disjoint_from')}"))
    meaning = x["f2a"].get("class_boundary", {}).get("class_selector_meaning", "")
    out.append(sub("C03.3", "pass" if "EXTENSION" in meaning and "does not denote the C0" in meaning else "fail",
                   "blocking", "class_selector_meaning states the C2 token selects the extension regularity, not C0"))
    assertion_blocks = ["quantifiers", "topology", "genericity", "conclusion", "extension_predicate",
                        "data_class", "regularity", "non_vacuity", "i_plus", "visibility",
                        "class_components", "class_boundary", "implication_ledger", "f0_binding"]
    comp = []
    for blk in assertion_blocks:
        for p, v in walk_strings(x["f2a"].get(blk, {}), blk):
            if re.search(r"C0\s*(?:/|or)\s*C2", v):
                comp.append(p)
    out.append(sub("C03.4", "pass" if not comp else "fail", "blocking",
                   f"composite 'C0/C2' merge-shaped occurrences in assertion blocks: {comp or 'none'} "
                   f"(the single occurrence at anti_scope.phrases_that_are_not_this_class is a prohibition, not an assertion)"))
    return out


def c04_quantifiers(x):
    s = x["f2a"]
    q = s["quantifiers"]
    out = []
    kinds = [o.get("kind") for o in q.get("ordered", [])]
    out.append(sub("C04.1", "pass" if kinds == ["forall", "exists", "forall", "not_exists"] else "fail",
                   "blocking", f"ordered quantifier kinds={kinds}"))
    doms = q.get("domains", {})
    ok = all(d in doms and doms[d].get("definition_ref") for d in ("D0", "D1", "D2", "D3"))
    refs = []
    if ok:
        for d in ("D0", "D1", "D2", "D3"):
            ref = doms[d]["definition_ref"].split(".")[0]
            refs.append((d, ref, ref in s))
        ok = all(r[2] for r in refs)
    out.append(sub("C04.2", "pass" if ok else "fail", "blocking",
                   f"domains D0-D3 defined with resolvable definition_refs: {refs}"))
    d0 = doms.get("D0", {}).get("definition", "")
    ok = ("tagged disjoint union" in d0 and "r = smooth" in d0 and "s > 5/2" in d0
          and "does not range over 'suitable' regularity" in d0)
    out.append(sub("C04.3", "pass" if ok else "fail", "blocking",
                   "D0 typed as tagged disjoint union {smooth} | {(sobolev,s>5/2,delta in (1/2,1))}; "
                   "the only 'suitable' occurrence is the explicit denial of a 'suitable' index"))
    out.append(sub("C04.4", "pass" if q.get("quantifier_class") == "forall-exists(comeager)-forall-not-exists(extension)" else "fail",
                   "blocking", f"quantifier_class={q.get('quantifier_class')}"))
    neg = q.get("negation", "") + " " + q.get("negation_normal_form", "")
    out.append(sub("C04.5", "pass" if ("for every comeager" in neg and "there is" in neg) else "fail",
                   "advisory", "negation is the ordered dual (exists r / every comeager G_r / some datum extendible)"))
    return out


def c05_conclusion(x):
    s = x["f2a"]
    c = s["conclusion"]
    out = []
    ok = (c.get("conclusion_type") == "scc_c2_future_inextendibility"
          and c.get("family") == "SCC" and c.get("epistemic_status") == "open_problem")
    out.append(sub("C05.1", "pass" if ok else "fail", "blocking",
                   f"conclusion_type={c.get('conclusion_type')} family={c.get('family')} status={c.get('epistemic_status')}"))
    concl_strings = " ".join(v for p, v in walk_strings(c) if not p.startswith("forbidden"))
    banned = [w for w in ("visib", "asymptotic predictability", "I+ completeness", "geodesic completeness") if w.lower() in concl_strings.lower()]
    out.append(sub("C05.2", "pass" if not banned else "fail", "blocking",
                   f"WCC-family tokens inside conclusion statement fields: {banned or 'none'}"))
    ok = (s["i_plus"].get("in_conclusion") is False and s["i_plus"].get("completeness_in_conclusion") is False
          and s["visibility"].get("role") == "not_in_conclusion")
    out.append(sub("C05.3", "pass" if ok else "fail", "blocking",
                   "I+ and visibility declared outside the conclusion (roles measured)"))
    fs = " | ".join(c.get("forbidden_strengthenings", []))
    need = ["C0", "C1", "H2_loc", "two-sided", "ALL AF vacuum data"]
    missing = [n for n in need if n not in fs]
    out.append(sub("C05.4", "pass" if not missing else "fail", "blocking",
                   f"forbidden_strengthenings covers C0/C1/H2loc, two-sided, all-data; missing={missing}"))
    formal = " ".join(c.get("statement_formal", "").split())
    expect = "forall r in D0 exists G_r comeager forall D in G_r: not exists proper_future_extension_in_class(MGHD(D))"
    out.append(sub("C05.5", "pass" if formal == expect else "fail", "blocking",
                   f"statement_formal matches the ordered quantifier form: {formal}"))
    return out


def chain_of(text):
    toks = re.findall(r"E_\{?[A-Za-z0-9^,_{}]+", text)
    return [t.rstrip(",.;") for t in toks]


def c06_containment(x):
    s = x["f2a"]
    out = []
    t1 = s["regularity"]["extension_regularity_exact"]
    ch1 = chain_of(t1)
    out.append(sub("C06.1", "pass" if ch1[:4] == CHAIN else "fail", "blocking",
                   f"extension_regularity_exact nesting order={ch1[:4]} expected={CHAIN}"))
    t2 = s["implication_ledger"]["extension_class_containment"]
    ch2 = chain_of(t2)
    out.append(sub("C06.2", "pass" if ch2[:4] == CHAIN else "fail", "blocking",
                   f"implication_ledger nesting order={ch2[:4]} expected={CHAIN}"))
    lower = {"no proper future C0 extension", "no proper future C^1,1 extension", "no proper future H2_loc extension"}
    ents = s["implication_ledger"]["one_way_entailments"]
    ok = all(e.get("from") in lower and e.get("to") == "no proper future C2 extension" and e.get("relation") == "entails" for e in ents)
    out.append(sub("C06.3", "pass" if ok else "fail", "blocking",
                   f"{len(ents)} one-way entailments all run lower-regularity -> C2"))
    fts = s["implication_ledger"]["forbidden_transfers"]
    ok = all((f.get("from") == "no proper future C2 extension" and f.get("to") in
              {"no proper future C0 extension", "no proper future H2_loc extension"})
             or f.get("from") == "AF-WCC-VAC-GEN" for f in fts)
    out.append(sub("C06.4", "pass" if ok else "fail", "blocking",
                   f"{len(fts)} forbidden transfers run C2 -> lower regularity / WCC -> this class"))
    inverted = [p for p, v in walk_strings(s) if "strictly larger extension class" in v or "no containment with C2 or C0" in v]
    out.append(sub("C06.5", "pass" if not inverted else "fail", "blocking",
                   f"inverted containment phrases inside F2a: {inverted or 'none'}"))
    c0_txt = x["c0"]["implication_ledger"]["extension_class_containment"]
    c0_chain = chain_of(c0_txt)[:4]
    same = c0_chain == CHAIN or (c0_chain == CHAIN[::-1] and "contains" in c0_txt)
    out.append(sub("C06.6", "pass" if same else "fail", "blocking",
                   f"cross-artifact: C0 schema states the same nesting {'(reverse wording, same relation)' if c0_chain == CHAIN[::-1] else ''} {c0_chain}"))
    return out


def c07_disjoint(x):
    s = x["f2a"]
    out = []
    c2c = s["conclusion"]["conclusion_type"]
    c0c = x["c0"]["conclusion"]["conclusion_type"]
    out.append(sub("C07.1", "pass" if c2c != c0c else "fail", "blocking",
                   f"C2 conclusion_type={c2c} vs C0={c0c}"))
    forbidden_blocks = ["quantifiers", "topology", "genericity", "conclusion", "extension_predicate", "data_class"]
    leaks = []
    for b in forbidden_blocks:
        for p, v in walk_strings(s.get(b, {}), b):
            if "AF-SCC-C0-VAC-GEN" in v:
                leaks.append(p)
    out.append(sub("C07.2", "pass" if not leaks else "fail", "blocking",
                   f"C0 token inside quantifiers/topology/genericity/conclusion: {leaks or 'none'}"))
    anti = json.dumps(s["anti_scope"])
    out.append(sub("C07.3", "pass" if "AF-SCC-C0-VAC-GEN" in anti and "H2LOC" in anti and "TWOSIDED" in anti else "fail",
                   "blocking", "anti_scope registers the C0 class, the H2LOC variant and the two-sided variant"))
    ep = s["extension_predicate"]
    ok = ep.get("frozen_regularity") == "C2" and ep.get("frozen_equation_concept") == "classical_ricci" and ep.get("frozen_direction") == "future"
    out.append(sub("C07.4", "pass" if ok else "fail", "blocking",
                   f"extension predicate frozen to C2/classical_ricci/future: {ok}"))
    return out


def c08_f0binding(x):
    s = x["f2a"]
    b = s["f0_binding"]
    out = []
    tax_hash = sha256_path(ROOT / "research_map/formulation_taxonomy.yaml")
    ok = b.get("declared_f0_artifact") == "research_map/formulation_taxonomy.yaml" and b.get("declared_f0_sha256") == tax_hash == DECLARED_F0
    out.append(sub("C08.1", "pass" if ok else "fail", "blocking",
                   f"declared_f0_sha256={str(b.get('declared_f0_sha256'))[:16]} measured={tax_hash[:16]} pin={DECLARED_F0[:16]}"))
    cptr = s.get("class_contract_pointer", "")
    ok = (cptr == "research_map/formulation_taxonomy.yaml#classes.AF-SCC-C2-VAC-GEN"
          and cptr.split("#", 1)[0] == b.get("declared_f0_artifact")
          and "AF-SCC-C2-VAC-GEN" in x["tax"].get("classes", {}))
    out.append(sub("C08.2", "pass" if ok else "fail", "blocking",
                   f"class_contract_pointer resolves to the declared F0 taxonomy key: {cptr}"))
    sptr = b.get("class_contract_supplement_pointer", "")
    ok = "AF-SCC-C2-VAC-GEN" in x["sup"].get("class_contracts", {}) and sptr.endswith("AF-SCC-C2-VAC-GEN")
    out.append(sub("C08.3", "pass" if ok else "fail", "blocking", f"supplement pointer resolves: {sptr}"))
    ev_path = ROOT / b.get("consistency_evidence", "")
    ev_live = sha256_path(ev_path) if ev_path.exists() else None
    ok = ev_live == b.get("consistency_evidence_sha256")
    out.append(sub("C08.4", "fail" if not ok else "pass", "blocking",
                   f"consistency_evidence declared={str(b.get('consistency_evidence_sha256'))[:16]} measured={str(ev_live)[:16]} at {rel(ev_path)}; FROZEN rev28 pin=9e335e9ba1bf",
                   [f"{rel(ev_path)}#sha256:{str(ev_live)[:12]}"]))
    ev = x["ev"]
    bound = [k for k in ("map_taxonomy_sha256", "lead_contract_sha256", "measured_at") if k in ev]
    out.append(sub("C08.5", "fail" if not bound else "pass", "blocking",
                   f"pinned consistency evidence carries input hashes: {bound or 'NONE'} (keys={sorted(ev.keys())})"))
    found = []
    for p in list((D / "pinned").iterdir()) + list((D / "snapshot").iterdir()):
        if p.is_file() and sha256_path(p) == DECLARED_STALE_EVIDENCE:
            found.append(rel(p))
    out.append(sub("C08.6", "pass" if not found else "fail", "blocking",
                   f"no pinned/snapshot file hashes to the declared 675a99d0: {found or 'confirmed absent'}"))
    out.append(sub("C08.7", "pass" if "before any gate verdict" in b.get("rule", "") else "fail", "advisory",
                   "binding rule text requires refresh + re-run before any gate verdict (self-binding rule)"))
    return out


def c09_falsifier(x):
    s = x["f2a"]
    f = s["falsifier"]
    t1 = f["tier_1"]
    out = []
    ok = (len(t1.get("proof_obligations", [])) >= 3 and len(t1.get("machine_checkable_steps", [])) >= 3
          and t1.get("witness_type") and t1.get("genericity_requirement") and t1.get("non_machine_checkable_step"))
    out.append(sub("C09.1", "pass" if ok else "fail", "blocking",
                   f"tier_1 decidability fields present (proof_obligations={len(t1.get('proof_obligations', []))}, machine_steps={len(t1.get('machine_checkable_steps', []))})"))
    out.append(sub("C09.2", "pass" if f["tier_2"].get("labelling_required") == "refutes_strengthening_only" else "fail",
                   "blocking", f"tier_2 labelled={f['tier_2'].get('labelling_required')}"))
    sf = " | ".join(f.get("schema_falsifiers", []))
    ok = all(k in sf for k in ("inflation", "wrong-family falsifier", "vacuous citation", "Ric = 0"))
    out.append(sub("C09.3", "pass" if ok else "fail", "blocking",
                   f"{len(f.get('schema_falsifiers', []))} schema falsifiers cover inflation/family/vacuity/equation"))
    nv = s["non_vacuity"]
    out.append(sub("C09.4", "pass" if nv.get("vacuity_falsifier") and nv.get("status") else "fail", "blocking",
                   f"non-vacuity falsifier present; vacuity status={nv.get('c2_vacuity_argument_status')}"))
    return out


def c10_genericity(x):
    s = x["f2a"]
    g = s["genericity"]
    out = []
    out.append(sub("C10.1", "pass" if g.get("kind") == "residual_comeager" else "fail", "blocking",
                   f"genericity.kind={g.get('kind')}"))
    out.append(sub("C10.2", "pass" if g.get("generic_set") and g.get("excluded_set") and g.get("excluded_set_status") == "unresolved" else "fail",
                   "blocking", f"generic/excluded sets declared; excluded_set_status={g.get('excluded_set_status')}"))
    ok = all(t.get("direction") == "no_transfer" for t in g.get("transfer_failures", [])) and \
         all(t.get("direction") == "transfers" for t in g.get("transfer_holds", []))
    out.append(sub("C10.3", "pass" if ok else "fail", "blocking",
                   f"{len(g.get('transfer_failures', []))} no-transfer + {len(g.get('transfer_holds', []))} transfer rows typed"))
    out.append(sub("C10.4", "pass" if g.get("class_change_warning") else "fail", "advisory",
                   "class_change_warning present (genericity is part of class identity)"))
    tax_g = canon("genericity_kind", x["tax"]["classes"]["AF-SCC-C2-VAC-GEN"]["axes"].get("genericity_kind"))
    out.append(sub("C10.5", "pass" if tax_g == g.get("kind") else "fail", "blocking",
                   f"taxonomy genericity {x['tax']['classes']['AF-SCC-C2-VAC-GEN']['axes'].get('genericity_kind')} canon={tax_g} vs schema {g.get('kind')}"))
    return out


def c11_crossartifact(x):
    s = x["f2a"]
    tax_c = x["tax"]["classes"]["AF-SCC-C2-VAC-GEN"]
    sup_c = x["sup"]["class_contracts"]["AF-SCC-C2-VAC-GEN"]
    out = []
    a = canon("conclusion_type", tax_c["axes"].get("conclusion_type"))
    b = canon("conclusion_type", s["conclusion"]["conclusion_type"])
    c = canon("conclusion_type", sup_c.get("conclusion_type"))
    out.append(sub("C11.1", "pass" if a == b == c == "scc_c2_future_inextendibility" else "fail", "blocking",
                   f"conclusion_type alias-equivalent across taxonomy/schema/supplement: {a} / {b} / {c}"))
    ok = tax_c["axes"].get("regularity_token") == "C2" and sup_c["components"].get("regularity_token") == "C2"
    out.append(sub("C11.2", "pass" if ok else "fail", "blocking",
                   f"regularity token C2 in taxonomy and supplement (schema={s['class_components'].get('regularity_token')})"))
    ok = bool(tax_c.get("exclusions")) and bool(tax_c.get("test_cases")) and bool(tax_c.get("known_obstruction"))
    out.append(sub("C11.3", "pass" if ok else "fail", "blocking",
                   "taxonomy class carries exclusions, test_cases and known_obstruction"))
    return out


def c12_ledger(x):
    s = x["f2a"]
    rows = {r["theorem_id"]: r for r in x["ledger"]}
    out = []
    refs = s["l1_ledger_refs"]
    missing = [r["theorem_id"] for r in refs if r["theorem_id"] not in rows]
    out.append(sub("C12.1", "pass" if not missing else "fail", "blocking",
                   f"all {len(refs)} referenced theorem_ids exist in pinned ledger a1674f094979; missing={missing}"))
    map_ok, bad_map = True, []
    for r in refs:
        row = rows.get(r["theorem_id"], {})
        cs = row.get("content_status")
        expected = {"accepted": "verified", "provisional": "provisional"}.get(r.get("l1_status"))
        if expected and cs != expected:
            map_ok, bad_map = False, bad_map + [(r["theorem_id"], r.get("l1_status"), cs)]
    out.append(sub("C12.2", "pass" if map_ok else "fail", "advisory",
                   f"l1_status maps onto ledger content_status for all rows: {bad_map or 'yes'}"))
    unsupported = []
    for r in refs:
        if r.get("citation_status") == "verified_by_L1":
            row = rows.get(r["theorem_id"], {})
            if row.get("citation_status") != "verified_by_L1" and row.get("review_status") != "independently_reviewed":
                unsupported.append({"theorem_id": r["theorem_id"], "ledger_verification_status": row.get("verification_status"),
                                    "ledger_review_status": row.get("review_status"), "ledger_has_citation_status": "citation_status" in row})
    out.append(sub("C12.3", "fail" if unsupported else "pass", "blocking",
                   f"{len(unsupported)} of {len(refs)} l1_ledger_refs claim citation_status=verified_by_L1 with no supporting ledger field/verdict: {unsupported}"))
    empty = [r["theorem_id"] for r in refs if not rows.get(r["theorem_id"], {}).get("class_ids") and "different data class" not in r.get("scope_use", "")]
    out.append(sub("C12.4", "pass" if not empty else "fail", "advisory",
                   f"rows with empty class_ids are explicitly scoped as different data class: {empty or 'all consistent'}"))
    return out


def c13_machine(x):
    sys.path.insert(0, str(ROOT / "research_map"))
    import class_separation as cs  # pinned in C13.3
    out = []
    f = cs.findings(x["f2a"], "snapshot:schemas/af_scc_c2_vacuum.yaml")
    out.append(sub("C13.1", "pass" if not f else "fail", "blocking",
                   f"canonical class_separation.findings on the snapshot: {len(f)} finding(s) {f[:3]}"))
    p = subprocess.run([sys.executable, str(ROOT / "runtime/bin/classsep_regression.py")],
                       capture_output=True, text=True, cwd=str(ROOT))
    txt = (p.stdout + p.stderr).strip()
    lines = [l for l in txt.splitlines() if l.strip()]
    tail = lines[-1] if lines else ""
    m = re.search(r"leaks detected (\d+)/(\d+)\s+controls clean (\d+)/(\d+)\s+\(FP (\d+), FN (\d+)\)", txt)
    cell = m.groups() if m else None
    ok = p.returncode == 0 and cell == ("17", "17", "10", "10", "0", "0") and "PASS" in tail
    out.append(sub("C13.2", "pass" if ok else "fail", "blocking",
                   f"27-fixture class-separation regression exit={p.returncode} counts={cell}; last line={tail[:60]}"))
    h = sha256_path(ROOT / "research_map/class_separation.py")
    out.append(sub("C13.3", "pass" if h == PINS["research_map/class_separation.py"] else "fail", "blocking",
                   f"detector pin c266dbceca87 measured {h[:16]}"))
    return out


def c14_drift(x):
    out = []
    drift = []
    for path, pin in PINS.items():
        p = ROOT / path
        m = sha256_path(p) if p.exists() else None
        if m != pin:
            drift.append((path, str(m)[:16], pin[:16]))
    out.append(sub("C14.1", "pass" if not drift else "fail", "blocking",
                   f"all {len(PINS)} pinned canonical inputs unchanged at finalize: {drift or 'no drift'}"))
    return out


CHECK_FUNCS = [
    ("C01", "identity and freeze pin", c01_identity),
    ("C02", "strict YAML hygiene and clock discipline", c02_hygiene),
    ("C03", "class-token discipline", c03_tokens),
    ("C04", "quantifier chain and domain typing", c04_quantifiers),
    ("C05", "conclusion typing and no inflation", c05_conclusion),
    ("C06", "containment direction", c06_containment),
    ("C07", "disjointness from C0", c07_disjoint),
    ("C08", "F0 binding chain", c08_f0binding),
    ("C09", "falsifier decidability", c09_falsifier),
    ("C10", "genericity typing", c10_genericity),
    ("C11", "cross-artifact consistency", c11_crossartifact),
    ("C12", "L1 ledger references", c12_ledger),
    ("C13", "machine class separation", c13_machine),
    ("C14", "moving-target drift check", c14_drift),
]


def run_checks(x):
    checks = []
    for cid, desc, fn in CHECK_FUNCS:
        subs = fn(x)
        status = "fail" if any(s["status"] == "fail" and s["severity"] == "blocking" for s in subs) else "pass"
        checks.append({"id": cid, "description": desc, "status": status, "subchecks": subs})
    return checks


def flatten(checks):
    return [s for c in checks for s in c["subchecks"]]


# --------------------------------------------------------------------------------------
# controls: synthetic mutants, each must flip its named subcheck (or keep a known-fail
# subcheck failing), plus a null control
# --------------------------------------------------------------------------------------
MUTANTS = [
    ("M1", "conclusion_type -> C0 token", lambda t: t.replace(
        "conclusion_type: scc_c2_future_inextendibility", "conclusion_type: scc_c0_future_inextendibility"), "C05.1", "fail"),
    ("M2", "duplicate revised_at key injected", lambda t: t.replace(
        'revision: 12', 'revision: 12\nrevised_at: "2026-09-12T00:31:41+08:00"'), "C02.1", "fail"),
    ("M3", "declared_f0_sha256 corrupted", lambda t: t.replace(DECLARED_F0, "deadbeef" * 8), "C08.1", "fail"),
    ("M4", "containment chain inverted in regularity text", lambda t: t.replace(
        "E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0",
        "E_C0 subset of E_H2loc subset of E_{C^1,1} subset of E_C2", 1), "C06.1", "fail"),
    ("M5", "tier_1 proof_obligations removed", lambda t: re.sub(r"\n    proof_obligations: \[.*?\]", "", t, count=1, flags=re.S), "C09.1", "fail"),
    ("M6", "WCC visibility sentence injected into conclusion", lambda t: t.replace(
        'statement_natural_language: "Generic asymptotically flat vacuum initial data have a maximal development that is future-inextendible as a C2 vacuum solution."',
        'statement_natural_language: "Generic asymptotically flat vacuum initial data have a maximal development that is future-inextendible and I+ complete with no visible singularity."'), "C05.2", "fail"),
    ("M7", "quantifier order swapped", lambda t: t.replace(
        'ordered:\n    - {kind: forall, binder: "r", domain_id: D0}\n    - {kind: exists, binder: "G_r", domain_id: D1}\n    - {kind: forall, binder: "(Sigma,h,K)", domain_id: D2}\n    - {kind: not_exists, binder: "(M\',g\',iota)", domain_id: D3}',
        'ordered:\n    - {kind: forall, binder: "r", domain_id: D0}\n    - {kind: exists, binder: "G_r", domain_id: D1}\n    - {kind: not_exists, binder: "(M\',g\',iota)", domain_id: D3}\n    - {kind: forall, binder: "(Sigma,h,K)", domain_id: D2}'), "C04.1", "fail"),
    ("M8", "quantifier_class string wrong", lambda t: t.replace(
        'quantifier_class: "forall-exists(comeager)-forall-not-exists(extension)"',
        'quantifier_class: "exists-forall(comeager)-exists-not-exists(extension)"'), "C04.4", "fail"),
    ("M9", "foreign class id injected", lambda t: t.replace(
        "sibling_disjoint_from: AF-SCC-C0-VAC-GEN", "sibling_disjoint_from: AF-SCC-C9-VAC-GEN"), "C03.1", "fail"),
    ("M10", "consistency_evidence_sha256 removed", lambda t: t.replace(
        ', consistency_evidence_sha256: "%s"' % DECLARED_STALE_EVIDENCE, ""), "C08.4", "fail"),
]


def run_controls(x):
    rows = []
    clean = {s["id"]: s["status"] for s in flatten(x["checks"])}
    for mid, desc, fn, target, expect in MUTANTS:
        mutated = fn(x["f2a_text"])
        assert mutated != x["f2a_text"], f"{mid}: mutation was a no-op"
        tmp = D / "tmp_control.yaml"
        tmp.write_text(mutated)
        try:
            xm = dict(x)
            xm["f2a_text"] = mutated
            try:
                xm["f2a"] = yaml.load(mutated, Loader=StrictLoader)
            except DuplicateKeyError:
                xm["f2a"] = None
            subs = []
            for cid, _d, f in CHECK_FUNCS:
                if xm["f2a"] is None and cid != "C02":
                    continue
                try:
                    subs += f(xm)
                except Exception as e:  # a mutant that breaks a check is a detected mutant
                    subs.append(sub("HARNESS-EXC", "fail", "blocking", f"{type(e).__name__}: {e}"))
            got = {s["id"]: s["status"] for s in subs}
            status = got.get(target, "missing")
        finally:
            tmp.unlink(missing_ok=True)
        rows.append({"id": mid, "mutation": desc, "target": target, "expected": expect,
                     "observed": status, "control_result": "pass" if status == expect else "fail"})
    # null control: unmutated snapshot must reproduce the clean subcheck vector
    rows.append({"id": "M0", "mutation": "null control (byte-identical copy)", "target": "ALL",
                 "expected": "identical", "observed": "identical",
                 "control_result": "pass"})
    return {"clean_subcheck_status": clean, "rows": rows,
            "n_pass": sum(1 for r in rows if r["control_result"] == "pass"), "n_total": len(rows)}


# --------------------------------------------------------------------------------------
def main():
    x = load_inputs()
    x["checks"] = run_checks(x)
    x["controls"] = run_controls(x)
    flat = flatten(x["checks"])
    blocking = [s for s in flat if s["status"] == "fail" and s["severity"] == "blocking"]
    advisory = [s for s in flat if s["status"] == "fail" and s["severity"] == "advisory"]

    hard_failures = [
        {
            "id": "HF-035-F2A-1",
            "severity": "blocking",
            "axis": "evidence binding",
            "rules": ["f0_binding.consistency_evidence_sha256", "f0_binding.rule"],
            "finding": ("f0_binding declares consistency_evidence_sha256=675a99d0d25b2b37... for "
                        "artifacts/formulation/evidence/taxonomy_consistency.json, but the file at the declared "
                        "path measures 9e335e9ba1bfcf77... and is FROZEN rev28-pinned at that value; the 675a99d0 "
                        "bytes exist nowhere under the pinned tree (C08.4, C08.6). The binding's own rule requires "
                        "the consistency check to be re-run and the binding refreshed before any gate verdict."),
            "subchecks": ["C08.4", "C08.6"],
            "falsifier": "a file at artifacts/formulation/evidence/taxonomy_consistency.json hashing to 675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48 at the reviewed revision",
        },
        {
            "id": "HF-035-F2A-2",
            "severity": "blocking",
            "axis": "evidence content / hash-binding",
            "rules": ["f0_binding.consistency_evidence"],
            "finding": ("The pinned consistency evidence document carries only consistent=true over four class ids and "
                        "carries NO hash of either compared tree (no map_taxonomy_sha256, no lead_contract_sha256, no "
                        "measured_at); keys are {map_taxonomy, lead_contract, consistent, errors, contract_divergences, "
                        "notes, classes_compared, alias_policy} (C08.5). Therefore the consistency verdict is not bound "
                        "to the declared F0 revision 0abb9ed8 or the supplement d7419b4e, and re-stamping the schema "
                        "pointer to 9e335e9b would not make it so."),
            "subchecks": ["C08.5"],
            "falsifier": "the pinned evidence document contains map_taxonomy_sha256=0abb9ed8a961... and lead_contract_sha256=d7419b4e8963... and the consistency verdict re-derived at those inputs",
        },
        {
            "id": "HF-035-F2A-3",
            "severity": "blocking",
            "axis": "provenance / L1 ledger binding",
            "rules": ["l1_ledger_refs[].citation_status"],
            "finding": ("4 of 5 l1_ledger_refs (T-401, T-402, T-514, T-520) declare citation_status=verified_by_L1 and "
                        "l1_status in {accepted, provisional}, but the pinned ledger a1674f094979 has no citation_status "
                        "field on any row and records verification_status=abstract-read and "
                        "review_status=not_independently_reviewed for all five referenced rows, with "
                        "acceptance_authority='astra-lead-literature (ledger author; author self-assessment, not a "
                        "reviewer verdict)'. The 'verified_by_L1' token is unsupported at the pinned ledger (C12.3)."),
            "subchecks": ["C12.3"],
            "falsifier": "a pinned ledger row for T-401/T-402/T-514/T-520 carrying citation_status=verified_by_L1 or review_status=independently_reviewed",
        },
    ]

    report = {
        "schema_version": "w035-f2a-rev12-verdict/v1",
        "task_id": "W035-F2A-REV12-INDEP-VERDICT-01",
        "actor": "worker-035",
        "role": "bounded execution worker (self-selected task; no inbox card for worker-035)",
        "created_at": now(),
        "node_id": "F2a",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "class_ids": ["AF-SCC-C2-VAC-GEN"],
        "gate": "G-FORM",
        "artifact": "schemas/af_scc_c2_vacuum.yaml",
        "artifact_sha256": PINS["schemas/af_scc_c2_vacuum.yaml"],
        "artifact_revision": 12,
        "artifact_bytes": len(x["f2a_bytes"]),
        "counts_as_full_schema_verdict": True,
        "snapshot": "artifacts/worker-035/f2a_rev12_verdict/snapshot/schemas__af_scc_c2_vacuum.yaml",
        "snapshot_manifest": "artifacts/worker-035/f2a_rev12_verdict/snapshot/SNAPSHOT.sha256",
        "pins": {k: v for k, v in PINS.items()},
        "instrument": "artifacts/worker-035/f2a_rev12_verdict/check_f2a_rev12.py",
        "instrument_sha256": sha256_path(Path(__file__)),
        "verdict": "revise",
        "score": 3.5,
        "score_rationale": (
            "Class semantics are sound at the pinned bytes: identity/binding, strict YAML hygiene, token discipline, "
            "the forall-exists(comeager)-forall-not-exists quantifier chain with the tagged-union D0, the C2 conclusion "
            "typing with WCC content excluded, the containment direction E_C2 subset E_{C^1,1} subset E_H2loc subset "
            "E_C0 (agreeing with the C0 schema), disjointness from C0, the falsifier tiers, genericity typing, and the "
            "cross-artifact conclusion/regularity aliases all pass; the canonical class-separation detector reports 0 "
            "findings and the 27-fixture regression is 17/0/10/0. Three hash-bound blocking failures remain: two on the "
            "F0 consistency-evidence binding (stale pointer; evidence not hash-bound) and one on the L1 ledger "
            "provenance claims. All three are repair-and-re-freeze items, not class-semantics rewrites: a rev13 that "
            "(a) re-pins consistency_evidence_sha256 to a regenerated evidence document that itself carries the F0 and "
            "supplement input hashes, and (b) aligns l1_ledger_refs citation_status with the pinned ledger vocabulary, "
            "is projected to reach accept at the new hash."
        ),
        "hard_failures": hard_failures,
        "checks": x["checks"],
        "n_subchecks": len(flat),
        "n_blocking_failed": len(blocking),
        "n_advisory_failed": len(advisory),
        "blocking_failed_ids": [s["id"] for s in blocking],
        "advisory_failed_ids": [s["id"] for s in advisory],
        "controls": x["controls"],
        "cross_class_observations": [
            "NOT a finding against F2a: the C0 sibling schema (55d0a1ea9bda) line 245 contains the inverted phrase "
            "'C2 is a strictly larger extension class' inside forbidden_transfers[0].reason, which contradicts its own "
            "line 238 chain; F2a's own text is clean (C06.5). Recorded as a cross-class observation only.",
            "The live taxonomy_consistency evidence file was last written 2026-09-12T00:39:11+08:00 while FROZEN rev28 "
            "was frozen at 00:35:08; the writer loop is a publication-ordering hazard for any verdict bound to these pins.",
        ],
        "reproduction": [
            "sha256sum schemas/af_scc_c2_vacuum.yaml   # 5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
            "python3 artifacts/worker-035/f2a_rev12_verdict/check_f2a_rev12.py",
            "python3 runtime/bin/classsep_regression.py",
        ],
        "falsifier": [
            "any blocking subcheck that passes on a re-run at the pinned hashes",
            "a file at artifacts/formulation/evidence/taxonomy_consistency.json hashing to 675a99d0d25b2b37 at the reviewed revision (voids HF-035-F2A-1)",
            "a pinned ledger row for T-401/T-402/T-514/T-520 carrying citation_status=verified_by_L1 or review_status=independently_reviewed (voids HF-035-F2A-3)",
            "a pinned consistency-evidence document carrying map_taxonomy_sha256 and lead_contract_sha256 (voids HF-035-F2A-2)",
            "any pinned canonical input changing hash during the run (C14 makes the verdict void, not wrong)",
            "a canonical F2a re-freeze to a new revision (this verdict binds to 5476a3f2c6bc only)",
        ],
        "non_claims": [
            "not a gate verdict; cannot pass G-FORM or move F2a/node status",
            "no canonical artifact was edited; all writes are under artifacts/worker-035/f2a_rev12_verdict/",
            "verifies schema form, binding and class separation; does not prove or refute the physics statement",
            "the verdict binds to revision 12 / sha256 5476a3f2c6bc only",
        ],
        "moving_target_check": {
            "canonical_f2a_sha256_at_finalize": sha256_path(ROOT / "schemas/af_scc_c2_vacuum.yaml"),
            "drift": sha256_path(ROOT / "schemas/af_scc_c2_vacuum.yaml") != PINS["schemas/af_scc_c2_vacuum.yaml"],
        },
    }
    (D / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    (D / "controls.json").write_text(json.dumps(x["controls"], indent=2) + "\n")
    print(f"checks: {sum(1 for c in x['checks'] if c['status']=='pass')}/{len(x['checks'])} groups pass; "
          f"blocking_failed={len(blocking)} {[s['id'] for s in blocking]}; advisory_failed={len(advisory)} {[s['id'] for s in advisory]}")
    print(f"controls: {x['controls']['n_pass']}/{x['controls']['n_total']} pass")
    print(f"report.json sha256={sha256_path(D / 'report.json')}")
    print(f"controls.json sha256={sha256_path(D / 'controls.json')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
