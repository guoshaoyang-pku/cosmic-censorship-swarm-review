#!/usr/bin/env python3
"""W047-F2A-REV13-VERDICT-01 independent full-schema verifier.

Target: class AF-SCC-C2-VAC-GEN (node F2a), schemas/af_scc_c2_vacuum.yaml at the
live rev13 pin e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe
(FROZEN rev29).

Design rules
  * deterministic: report contains no wall-clock values; timestamps are read from
    the pinned inputs;
  * read-only outside this task's own directory;
  * every criterion is a pure function of the parsed pinned inputs and their raw
    text; all 16 mutation controls run on in-memory/text copies;
  * exit 0 = every hard+soft criterion passes (clean accept), 1 = hard failure(s)
    present (revise), 2 = pin drift, 3 = a control did not discriminate, 5 = parse
    error.

The verifier does NOT set node status, a gate verdict, or validation_status.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

PINS = {
    "schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "schemas/af_wcc_vacuum.yaml": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/formulation_taxonomy.yaml": "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "artifacts/formulation/evidence/taxonomy_consistency.json": "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b",
    "artifacts/formulation/VOCAB_ALIASES.json": "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba",
}
# The freeze manifest is a concurrently-rewritten log. It is pinned semantically:
# revision 29 and its entry for F2a must equal the live schema hash. Its own file
# hash is recorded and re-measured, but a manifest-file move within revision 29
# that keeps the F2a entry is REPORTED, not treated as content drift.
COMPANION = {"artifacts/formulation/FROZEN.json": {"revision": 29}}
CLASS_ID = "AF-SCC-C2-VAC-GEN"
NODE_ID = "F2a"

C = {}


def add(cid, axis, severity, ok, expected, observed, detail=""):
    C[cid] = {
        "id": cid,
        "axis": axis,
        "severity": severity,
        "ok": bool(ok),
        "expected": expected,
        "observed": observed,
        "detail": detail,
    }


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def dup_keys(path):
    """Return list of duplicate-key paths using the composed node tree."""
    dups = []

    def walk(node, prefix):
        if isinstance(node, yaml.MappingNode):
            seen = {}
            for k, v in node.value:
                key = getattr(k, "value", None)
                if key in seen:
                    dups.append(f"{prefix}.{key}")
                seen[key] = True
                walk(v, f"{prefix}.{key}")
        elif isinstance(node, yaml.SequenceNode):
            for i, v in enumerate(node.value):
                walk(v, f"{prefix}[{i}]")

    try:
        with open(path, "r", encoding="utf-8") as fh:
            walk(yaml.compose(fh), "")
    except Exception as exc:  # pragma: no cover
        dups.append(f"<compose-error:{exc}>")
    return dups


def clauses(text):
    return [c.strip() for c in re.split(r"[;\n]", text) if c.strip()]


def has_token(text, tokens):
    return [t for t in tokens if re.search(t, text, re.I)]


def load_model(root):
    m = {"root": root, "hashes": {}, "raw": {}}
    for rel in list(PINS) + list(COMPANION):
        p = os.path.join(root, rel)
        if not os.path.exists(p):
            raise FileNotFoundError(rel)
        m["hashes"][rel] = sha256_file(p)
        with open(p, "r", encoding="utf-8") as fh:
            m["raw"][rel] = fh.read()
    m["f2a"] = yaml.safe_load(m["raw"]["schemas/af_scc_c2_vacuum.yaml"])
    m["f2b"] = yaml.safe_load(m["raw"]["schemas/af_scc_c0_vacuum.yaml"])
    m["f1"] = yaml.safe_load(m["raw"]["schemas/af_wcc_vacuum.yaml"])
    m["f0"] = yaml.safe_load(m["raw"]["research_map/formulation_taxonomy.yaml"])
    m["supp"] = yaml.safe_load(m["raw"]["artifacts/formulation/formulation_taxonomy.yaml"])
    m["ev"] = json.loads(m["raw"]["artifacts/formulation/evidence/taxonomy_consistency.json"])
    m["frozen"] = json.loads(m["raw"]["artifacts/formulation/FROZEN.json"])
    m["alias"] = json.loads(m["raw"]["artifacts/formulation/VOCAB_ALIASES.json"])
    m["dups"] = dup_keys(os.path.join(root, "schemas/af_scc_c2_vacuum.yaml"))
    return m


def mprime_status(schema):
    """Clauses naming M' as a manifold, and those that fix its differentiable category."""
    d = schema.get("extension_predicate", {}).get("definition", "")
    topo_ext = schema.get("topology", {}).get("extension_topology", "")
    cs = [c for c in clauses(d) + clauses(topo_ext)
          if re.search(r"M'", c) and re.search(r"manifold|structure", c, re.I)]
    cat = [c for c in cs
           if has_token(c, [r"\bsmooth\b", r"C\^?\s*∞", r"C\^?\s*infinity",
                            r"C-infinity", r"C\^?\s*k", r"differentiab"])]
    return cs, cat


# --------------------------------------------------------------------------- #
# criteria
# --------------------------------------------------------------------------- #
def run_criteria(m):
    C.clear()
    s = m["f2a"]
    f0 = m["f0"]

    # ---- identity / contract ------------------------------------------------
    add("G01", "identity", "hard",
        s.get("class_id") == CLASS_ID and s.get("node_id") == NODE_ID,
        "class_id=AF-SCC-C2-VAC-GEN, node_id=F2a",
        f"class_id={s.get('class_id')}, node_id={s.get('node_id')}")

    comp = s.get("class_components", {})
    want_comp = {"asymptotics": "AF", "censorship": "SCC", "matter": "VAC",
                 "genericity": "GEN", "regularity_token": "C2"}
    reg_tokens = [k for k, v in comp.items() if re.search(r"regularity|token", k)]
    add("G02", "identity", "hard",
        comp == want_comp and len(reg_tokens) == 1,
        "exactly the five components with regularity_token=C2",
        f"components={comp}")

    def_slots = json.dumps({k: s.get(k) for k in
                            ("class_components", "quantifiers", "topology", "genericity",
                             "data_class", "extension_predicate", "conclusion")},
                           ensure_ascii=False)
    add("G03", "identity", "hard",
        not re.search(r"C0\s*(/|or|,)\s*C2|C2\s*(/|or|,)\s*C0", def_slots, re.I),
        "no C0/C2 composite token in class-defining slots",
        "composite C0/C2 token absent" if not re.search(r"C0\s*(/|or|,)\s*C2", def_slots, re.I)
        else "composite token present")

    ptr = s.get("class_contract_pointer", "")
    cls_id = s.get("class_id")
    cls = f0.get("classes", {}).get(cls_id, {})
    axes = cls.get("axes", {})
    ptr_ok = (ptr == f"research_map/formulation_taxonomy.yaml#classes.{cls_id}"
              and bool(cls)
              and axes.get("family") == "SCC"
              and axes.get("matter_model") == "vacuum"
              and axes.get("regularity_token") == "C2"
              and axes.get("asymptotics") == "asymptotically_flat_3p1")
    add("G04", "contract", "hard", ptr_ok,
        "pointer resolves in F0 and F0 axes are SCC/vacuum/C2/AF for the schema's own class_id",
        f"pointer={ptr}, class_id={cls_id}, axes={axes}")

    fb = s.get("f0_binding", {})
    add("G05", "contract", "hard",
        fb.get("declared_f0_sha256") == m["hashes"]["research_map/formulation_taxonomy.yaml"],
        "declared_f0_sha256 == measured F0 hash",
        f"declared={str(fb.get('declared_f0_sha256'))[:16]}, measured={m['hashes']['research_map/formulation_taxonomy.yaml'][:16]}")

    ev = m["ev"]
    ev_ok = (fb.get("consistency_evidence_sha256")
             == m["hashes"]["artifacts/formulation/evidence/taxonomy_consistency.json"]
             and ev.get("consistent") is True
             and CLASS_ID in ev.get("classes_compared", []))
    add("G06", "contract", "hard", ev_ok,
        "consistency_evidence_sha256 resolves; evidence consistent=true and lists this class",
        f"declared={str(fb.get('consistency_evidence_sha256'))[:16]}, measured={m['hashes']['artifacts/formulation/evidence/taxonomy_consistency.json'][:16]}, consistent={ev.get('consistent')}")

    mirror = m["hashes"]["artifacts/formulation/formulation_taxonomy.yaml"]
    add("G07", "contract", "hard",
        m["hashes"]["schemas/af_scc_c2_vacuum.yaml"] == PINS["schemas/af_scc_c2_vacuum.yaml"],
        "canonical == snapshot pin",
        f"canonical={m['hashes']['schemas/af_scc_c2_vacuum.yaml'][:16]}")

    frozen = m["frozen"]
    fpin = frozen.get("files", {}).get("schemas/af_scc_c2_vacuum.yaml", {}).get("sha256")
    add("G08", "contract", "hard",
        frozen.get("revision") == 29 and fpin == PINS["schemas/af_scc_c2_vacuum.yaml"],
        "FROZEN rev29 pins this schema at e9a27996",
        f"revision={frozen.get('revision')}, frozen_pin={str(fpin)[:16] if fpin else None}")

    add("G09", "hygiene", "hard", len(m["dups"]) == 0,
        "0 duplicate mapping keys at any depth", f"duplicates={m['dups']}")

    mtime = os.stat(os.path.join(m["root"], "schemas/af_scc_c2_vacuum.yaml")).st_mtime
    stamps = []
    for label, val in (("revised_at", s.get("revised_at")),
                       ("f0_binding.checked_at", fb.get("checked_at"))):
        if val is None:
            stamps.append((label, None, None))
            continue
        try:
            import datetime
            ts = datetime.datetime.fromisoformat(str(val)).timestamp()
        except Exception:
            ts = None
        stamps.append((label, val, ts))
    clock_ok = all(ts is not None and ts <= mtime + 1 for _, _, ts in stamps)
    hist = s.get("revision_history", []) or []
    idx_ok = (max([h.get("index", 0) for h in hist] or [0]) + 1 <= s.get("revision", -1))
    add("G10", "hygiene", "hard", clock_ok and idx_ok,
        "revised_at/checked_at not future-dated vs mtime and history indices < revision",
        f"stamps={[(l, v) for l, v, _ in stamps]}, revision={s.get('revision')}, max_history_index={max([h.get('index',0) for h in hist] or [0])}")

    rs = s.get("review_status", {})
    add("G11", "hygiene", "hard",
        not rs.get("independent_reviewers") and rs.get("verdict") == "pending"
        and bool(s.get("promotion_rule")),
        "no self-certification: reviewer list empty, verdict pending, promotion rule present",
        f"independent_reviewers={rs.get('independent_reviewers')}, verdict={rs.get('verdict')}")

    # ---- quantifiers --------------------------------------------------------
    q = s.get("quantifiers", {})
    concl = s.get("conclusion", {})
    formal = re.sub(r"\s+", " ", q.get("formal", "")).strip()
    stmt_formal = re.sub(r"\s+", " ", concl.get("statement_formal", "")).strip()
    skeleton_ok = (formal.startswith("forall r in D0")
                   and "exists G_r" in formal and "comeager" in formal
                   and re.search(r"forall\s*\(Sigma,h,K\)\s*in\s*G_r", formal)
                   and "not exists" in formal
                   and stmt_formal.startswith("forall r in D0")
                   and "exists G_r comeager" in stmt_formal
                   and "not exists" in stmt_formal)
    add("G12", "quantifier", "hard", skeleton_ok,
        "both renderings carry the same 4-quantifier skeleton (forall r / exists G_r / forall data / not exists extension)",
        f"quantifiers.formal[:90]={formal[:90]!r}; statement_formal={stmt_formal!r}")

    ordered = q.get("ordered", [])
    kinds = [o.get("kind") for o in ordered]
    binders = [o.get("binder") for o in ordered]
    add("G13", "quantifier", "hard",
        kinds == ["forall", "exists", "forall", "not_exists"]
        and binders == ["r", "G_r", "(Sigma,h,K)", "(M',g',iota)"]
        and q.get("order_matters") is True,
        "forall(r) -> exists(G_r) -> forall(data) -> not_exists(extension), order_matters",
        f"kinds={kinds}, binders={binders}, order_matters={q.get('order_matters')}")

    d0 = re.sub(r"\s+", " ", q.get("domains", {}).get("D0", {}).get("definition", ""))
    add("G14", "quantifier", "hard",
        "smooth" in d0 and "sobolev" in d0.lower() and "s > 5/2" in d0
        and "delta in (1/2,1)" in d0 and "does not range over" in d0,
        "D0 = tagged disjoint union {smooth, (sobolev,s,delta)} and explicitly not 'suitable' regularity",
        d0[:200])

    neg = q.get("negation", "")
    nnf = q.get("negation_normal_form", "")
    add("G15", "quantifier", "hard",
        "non-meager" in neg and "non-meager" in nnf and "exists r in D0" in neg,
        "negation is the correct dual (extendible set non-meager) with matching NNF",
        f"negation_len={len(neg)}, nnf={nnf[:120]}")

    # ---- conclusion ---------------------------------------------------------
    nat = concl.get("statement_natural_language", "")
    ctype = concl.get("conclusion_type", "")
    add("G17", "conclusion", "hard",
        concl.get("family") == "SCC"
        and "c2" in ctype.lower() and "c0" not in ctype.lower()
        and "generic" in nat.lower()
        and "comeager" in stmt_formal,
        "family SCC, C2-denoting conclusion_type and the generic/comeager quantifier in both renderings",
        f"family={concl.get('family')}, conclusion_type={ctype}, nat={nat[:80]}")

    stmt = json.dumps({k: concl.get(k) for k in
                       ("statement_natural_language", "statement_formal", "equivalent_rephrasings")},
                      ensure_ascii=False)
    add("G18", "conclusion", "hard",
        not re.search(r"I\+|visibility|predictab", stmt, re.I),
        "no WCC (I+/visibility) content in the conclusion statement",
        "clean" if not re.search(r"I\+|visibility|predictab", stmt, re.I) else "WCC content present")

    fs = json.dumps(concl.get("forbidden_strengthenings", []), ensure_ascii=False)
    fw = json.dumps(concl.get("forbidden_weakenings", []), ensure_ascii=False)
    add("G19", "conclusion", "hard",
        "C0" in fs and "H2_loc" in fs and "ALL AF" in fs.upper()
        and "I+" in fs and "generic" in fw.lower() and "globally hyperbolic" in fw.lower(),
        "forbidden strengthenings/weakenings cover C0/H2_loc/all-data/WCC and generic/GH-only",
        f"strengthenings_ok={('C0' in fs and 'H2_loc' in fs and 'I+' in fs)}, weakenings_ok={('generic' in fw.lower() and 'globally hyperbolic' in fw.lower())}")

    ko = concl.get("known_obstruction", "")
    add("G20", "conclusion", "hard",
        ("genericity" in ko.lower() or "generic" in ko.lower())
        and ("Kerr" in ko or "stationary" in ko.lower()),
        "known_obstruction keeps the genericity requirement and names the Kerr/stationary obstruction",
        ko[:120])

    # ---- extension predicate (incl. HF-091-02 adjudication) ------------------
    ep = s.get("extension_predicate", {})
    add("G21", "extension", "hard",
        ep.get("frozen_regularity") == "C2"
        and ep.get("frozen_direction") == "future"
        and ep.get("frozen_equation_concept") == "classical_ricci",
        "frozen_regularity=C2, direction=future, equation=classical_ricci",
        f"reg={ep.get('frozen_regularity')}, dir={ep.get('frozen_direction')}, eq={ep.get('frozen_equation_concept')}")

    d = ep.get("definition", "")
    clause_req = {
        "a": r"isometric embedding",
        "b": r"open,?\s*proper subset",
        "c": r"time-orientable",
        "d": r"C2 Lorentzian metric",
        "e": r"Ric\(g'\)\s*=\s*0.*classical",
        "f": r"I\^\+\(q",
    }
    missing = [k for k, rx in clause_req.items() if not re.search(rx, d, re.I | re.S)]
    add("G22", "extension", "hard", not missing,
        "clauses (a)-(f) present with required content", f"missing={missing}")

    # HF-091-02a: is the differentiable category of M' frozen?
    mprime_clauses, mprime_cat = mprime_status(s)
    add("G23", "extension", "hard", bool(mprime_cat),
        "the differentiable category of M' is frozen (smooth/C^k manifold or structure)",
        f"clauses_naming_M_prime={mprime_clauses or 'none'}; category_clauses={mprime_cat or 'NONE'}",
        "HF-091-02a independently reproduced: no clause fixes the differentiable category of M'")

    # HF-091-02b: is the regularity of iota frozen?
    iota_clauses = [c for c in clauses(d) if re.search(r"iota", c, re.I)]
    iota_re = [r"\b(?:C\^?\s*(?:1|2|k|∞|\\infty)|smooth)\s+(?:isometric\s+)?embedding",
               r"iota\s+(?:is|of\s+class|of\s+regularity)\s*(?:a\s*)?\bC\^?\s*(?:1|2|k|∞|\\infty)",
               r"iota_regularity"]
    iota_cat = [rx for rx in iota_re if re.search(rx, d, re.I)]
    add("G24", "extension", "hard", bool(iota_cat),
        "the regularity of the embedding iota is frozen (C^k/smooth qualifier attached to iota or its embedding)",
        f"iota_clauses={iota_clauses}; matching_patterns={iota_cat or 'NONE'}",
        "HF-091-02b independently reproduced: 'isometric embedding' carries no differentiability class")

    mnc = json.dumps(ep.get("must_not_conflate", []), ensure_ascii=False).lower()
    add("G25", "extension", "hard",
        "globally hyperbolic" in mnc and "ric" in mnc and "maximal development" in mnc,
        "must_not_conflate covers bare-metric, GH-requirement, MGHD-vs-inextendible",
        f"len={len(mnc)}")

    chain = "E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0"
    chain_locs = {
        "regularity.extension_regularity_exact": s.get("regularity", {}).get("extension_regularity_exact", ""),
        "regularity.must_not_conflate": " ".join(s.get("regularity", {}).get("must_not_conflate", [])),
        "implication_ledger.extension_class_containment": s.get("implication_ledger", {}).get("extension_class_containment", ""),
    }
    add("G26", "implication", "hard", all(chain in v for v in chain_locs.values()),
        "containment chain E_C2 <= E_{C^1,1} <= E_H2loc <= E_C0 in all three declared locations",
        json.dumps({k: (chain in v) for k, v in chain_locs.items()}))

    il = s.get("implication_ledger", {})
    ent = il.get("one_way_entailments", [])
    ent_from = {e.get("from", "") for e in ent}
    add("G27", "implication", "hard",
        any("C0" in x for x in ent_from) and any("H2_loc" in x for x in ent_from)
        and any("C^1,1" in x for x in ent_from),
        "one-way entailments from C0, C^1,1 and H2_loc to C2",
        f"from={sorted(ent_from)}")

    ft = json.dumps(il.get("forbidden_transfers", []), ensure_ascii=False)
    add("G28", "implication", "hard",
        "no proper future C0 extension" in ft and "H2_loc" in ft and "AF-WCC-VAC-GEN" in ft,
        "forbidden transfers include C2->C0, C2->H2_loc, WCC->this",
        f"forbidden_n={len(il.get('forbidden_transfers', []))}")

    # ---- genericity ---------------------------------------------------------
    gen = s.get("genericity", {})
    add("G29", "genericity", "hard",
        gen.get("kind") == "residual_comeager"
        and "constraint manifold" in gen.get("ambient_space", "")
        and "Baire" in gen.get("ambient_space", "")
        and "meager" in gen.get("excluded_set", "")
        and gen.get("is_part_of_class") is True
        and bool(gen.get("class_change_warning")),
        "kind residual_comeager on the Baire constraint manifold; part of class identity",
        f"kind={gen.get('kind')}, is_part_of_class={gen.get('is_part_of_class')}")

    tf = json.dumps(gen.get("transfer_failures", []), ensure_ascii=False)
    th = json.dumps(gen.get("transfer_holds", []), ensure_ascii=False)
    add("G30", "genericity", "hard",
        "full_measure" in tf and "open_dense_escape" in tf
        and "open_dense_escape" in th and "finite_codimension_complement" in th,
        "transfer failures (comeager->measure, comeager->open-dense) and holds recorded",
        f"failures={len(gen.get('transfer_failures', []))}, holds={len(gen.get('transfer_holds', []))}")

    add("G31", "genericity", "hard",
        all(v.get("is_this_class") is False for v in gen.get("variants", [])),
        "every genericity variant is marked is_this_class=false",
        f"variants={[(v.get('kind'), v.get('statement_strength')) for v in gen.get('variants', [])]}")

    # ---- topology / data class / I+ / visibility ----------------------------
    t = s.get("topology", {})
    dc = s.get("data_class", {})
    add("G32", "topology", "hard",
        t.get("spacetime_dimension") == 4
        and "R^3" in t.get("slice_topology", "")
        and "one" in t.get("end_structure", "").lower()
        and t.get("I_plus_topology") == "R x S^2"
        and "NOT assumed globally hyperbolic" in t.get("extension_topology", ""),
        "4d, slice R^3, one AF end, I+ = R x S^2, M' not assumed GH",
        f"dim={t.get('spacetime_dimension')}, I+={t.get('I_plus_topology')}")

    add("G33", "data_class", "hard",
        dc.get("matter") == "none" and dc.get("cosmological_constant") == 0
        and "Ric(g) = 0" in dc.get("equations", "")
        and "hamiltonian" in dc.get("constraints", {})
        and "momentum" in dc.get("constraints", {})
        and dc.get("symmetry") == "none_assumed"
        and "s > 5/2" in json.dumps(dc.get("regularity_class", {}))
        and "delta in (1/2, 1)" in json.dumps(dc.get("regularity_class", {})),
        "vacuum, Lambda=0, both constraints, no symmetry, s>5/2 and delta in (1/2,1)",
        f"matter={dc.get('matter')}, cc={dc.get('cosmological_constant')}, symmetry={dc.get('symmetry')}")

    ip = s.get("i_plus", {})
    vis = s.get("visibility", {})
    add("G34", "visibility", "hard",
        ip.get("role") == "assumption" and ip.get("in_conclusion") is False
        and vis.get("role") == "not_in_conclusion"
        and vis.get("visible_singularity_is_wcc") is True
        and bool(vis.get("forbidden_falsifier")),
        "I+ is an assumption (not in conclusion); visibility not in conclusion; visible singularity is a WCC falsifier",
        f"i_plus_role={ip.get('role')}, vis_role={vis.get('role')}")

    # ---- falsifier / anti-scope / status ------------------------------------
    fal = s.get("falsifier", {})
    add("G35", "falsifier", "hard",
        fal.get("tier_1", {}).get("refutes") == CLASS_ID
        and "non-meager" in fal.get("tier_1", {}).get("genericity_requirement", "")
        and fal.get("tier_2", {}).get("labelling_required") == "refutes_strengthening_only"
        and any("visible" in x for x in fal.get("schema_falsifiers", [])),
        "tier-1 non-meagerness falsifier, tier-2 labelled strengthening-only, wrong-family falsifier listed",
        f"tier1_refutes={fal.get('tier_1', {}).get('refutes')}, schema_falsifiers={len(fal.get('schema_falsifiers', []))}")

    anti = json.dumps(s.get("anti_scope", {}), ensure_ascii=False)
    add("G36", "anti_scope", "hard",
        "AF-SCC-C0-VAC-GEN" in anti and "AF-WCC-VAC-GEN" in anti
        and "AF-WCC-SCALAR-SPH" in anti and "C0 or C2" in anti.replace('"', ''),
        "anti_scope excludes the C0/WCC/scalar siblings and the composite phrase",
        f"anti_scope_len={len(anti)}")

    ks = s.get("known_status", {})
    add("G37", "status", "hard",
        ks.get("status") == "open_problem"
        and ks.get("no_peer_reviewed_theorem_for_this_class") == "T-401"
        and ks.get("source") == "ledger/theorems.jsonl"
        and len(s.get("l1_ledger_refs", [])) >= 4,
        "open_problem, no peer-reviewed theorem (T-401), ledger source, >=4 l1 refs",
        f"status={ks.get('status')}, l1_refs={len(s.get('l1_ledger_refs', []))}")

    nv = s.get("non_vacuity", {})
    add("G38", "status", "hard",
        nv.get("c2_vacuity_argument_status") == "unverified_proof_obligation"
        and bool(nv.get("vacuity_falsifier")),
        "vacuity argument honestly marked as an unverified proof obligation",
        f"vacuity_status={nv.get('c2_vacuity_argument_status')}")

    # ---- cross-artifact vocabulary conformance (worker-090 axis) ------------
    fv = f0.get("field_vocabulary", {})
    alias = m["alias"]

    def classify(axis, value):
        allowed = (fv.get(axis) or {}).get("allowed", []) if isinstance(fv.get(axis), dict) else []
        if value in allowed:
            return "exact", allowed
        groups = alias.get(axis, {})
        for canonical, alist in groups.items():
            if value == canonical and any(a in allowed for a in alist):
                return "alias_inverted", allowed
            if value in alist:
                if canonical in allowed:
                    return "alias_forward", allowed
        return "unregistered", allowed

    ct_cls, ct_allowed = classify("conclusion_type", concl.get("conclusion_type"))
    gk_cls, gk_allowed = classify("genericity_kind", gen.get("kind"))
    ptr_declared = "VOCAB_ALIASES" in m["raw"]["schemas/af_scc_c2_vacuum.yaml"]
    add("G39", "vocabulary", "hard",
        ct_cls == "exact" and gk_cls == "exact",
        "conclusion_type and genericity_kind are exact members of the F0 allowed lists",
        f"conclusion_type={concl.get('conclusion_type')} -> {ct_cls} (allowed={ct_allowed}); "
        f"genericity_kind={gen.get('kind')} -> {gk_cls} (allowed={gk_allowed})",
        "cross-artifact vocabulary inversion: the schema uses the VOCAB_ALIASES canonical while F0's allowed list holds only its alias")

    add("G40", "vocabulary", "hard", ptr_declared,
        "the schema declares the alias registry it depends on (VOCAB_ALIASES.json pointer)",
        "pointer present" if ptr_declared else "NO VOCAB_ALIASES pointer in the artifact",
        "F2a resolves conclusion_type/genericity_kind only through alias equivalence but declares no registry pointer (worker-090 W090-VOCAB-04 axis, independently re-measured)")

    return C


# --------------------------------------------------------------------------- #
# controls: mutate a deep copy / raw text and require the named checks to fail
# --------------------------------------------------------------------------- #
def mutate_copy(m, fn):
    m2 = dict(m)
    m2["f2a"] = copy.deepcopy(m["f2a"])
    m2["raw"] = dict(m["raw"])
    fn(m2)
    return m2


def set_path(d, path, value):
    cur = d
    for k in path[:-1]:
        cur = cur[k]
    cur[path[-1]] = value


CONTROLS = []


def control(cid, expect_fail, fn, desc):
    CONTROLS.append({"id": cid, "expect_fail": expect_fail, "fn": fn, "desc": desc})


control("C01", ["G01", "G04"], lambda m: set_path(m["f2a"], ["class_id"], "AF-SCC-C0-VAC-GEN"),
        "class id switched to the C0 sibling")
control("C02", ["G02"], lambda m: set_path(m["f2a"], ["class_components", "regularity_token"], "C0"),
        "regularity token switched to C0")
control("C03", ["G17", "G39"], lambda m: set_path(m["f2a"], ["conclusion", "conclusion_type"], "scc_c0_future_inextendibility"),
        "conclusion type switched to the C0 canonical")
control("C04", ["G14"], lambda m: set_path(m["f2a"], ["quantifiers", "domains", "D0", "definition"],
                                           m["f2a"]["quantifiers"]["domains"]["D0"]["definition"].replace("smooth", "regular")),
        "D0 smooth branch erased")
control("C05", ["G26"], lambda m: set_path(m["f2a"], ["regularity", "extension_regularity_exact"],
                                           m["f2a"]["regularity"]["extension_regularity_exact"].replace(
                                               "E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0",
                                               "E_C0 subset of E_H2loc subset of E_{C^1,1} subset of E_C2")),
        "extension containment chain reversed")
control("C06", ["G25"], lambda m: set_path(
    m["f2a"], ["extension_predicate", "must_not_conflate"],
    [x for x in m["f2a"]["extension_predicate"]["must_not_conflate"]
     if "globally hyperbolic" not in x.lower()]),
        "GH must_not_conflate entry deleted")
control("C07", ["G06"], lambda m: set_path(m["f2a"], ["f0_binding", "consistency_evidence_sha256"], "0" * 64),
        "declared consistency evidence hash broken")
control("C08", ["G18"], lambda m: set_path(m["f2a"], ["conclusion", "statement_natural_language"],
                                           m["f2a"]["conclusion"]["statement_natural_language"] + " The development is future null complete at I+."),
        "WCC I+ completeness injected into the conclusion")
control("C09", ["G21"], lambda m: set_path(m["f2a"], ["extension_predicate", "frozen_regularity"], "C1"),
        "frozen extension regularity switched to C1")
control("C11", ["G29"], lambda m: set_path(m["f2a"], ["genericity", "kind"], "full_measure"),
        "genericity kind switched to full_measure")
control("C12", ["G04"], lambda m: set_path(m["f2a"], ["class_contract_pointer"],
                                           "research_map/formulation_taxonomy.yaml#classes.NOPE"),
        "class contract pointer repointed at a missing class")
control("C15", ["G17", "G39"], lambda m: set_path(m["f2a"], ["conclusion", "conclusion_type"], "foo_bar_unregistered"),
        "unregistered conclusion token injected")
control("C16", ["G13"], lambda m: m["f2a"]["quantifiers"]["ordered"].reverse(),
        "quantifier order reversed")


def raw_text_controls(m):
    base = m["raw"]["schemas/af_scc_c2_vacuum.yaml"]
    out = []

    def apply_dup(text):
        return text.replace("schema_version:", "schema_version: \"1.0\"\nschema_version:", 1)

    def apply_clock(text):
        return re.sub(r'revised_at: "[^"]*"', 'revised_at: "2099-01-01T00:00:00+08:00"', text, count=1)

    out.append(("C13", ["G09"], "duplicate top-level key injected", apply_dup))
    out.append(("C14", ["G10"], "revised_at future-dated", apply_clock))
    return out


def positive_control(m):
    m2 = mutate_copy(m, lambda mm: set_path(
        mm["f2a"], ["extension_predicate", "definition"],
        mm["f2a"]["extension_predicate"]["definition"]
        + " M' is a SMOOTH (C-infinity) connected 4-manifold and iota: M -> M' is a C2 isometric embedding."))
    res = run_criteria(m2)
    return ("C10", res["G23"]["ok"] and res["G24"]["ok"],
            "positive control: M' smoothness and iota regularity added -> G23/G24 pass")


def run_controls(m):
    results = []
    base = dict(run_criteria(m))
    for ctl in CONTROLS:
        m2 = mutate_copy(m, ctl["fn"])
        res = run_criteria(m2)
        flipped = [cid for cid in ctl["expect_fail"] if not res[cid]["ok"]]
        untouched_hard = [cid for cid, r in base.items()
                          if r["severity"] == "hard" and r["ok"] and cid not in ctl["expect_fail"]
                          and not res[cid]["ok"]]
        ok = len(flipped) == len(ctl["expect_fail"]) and not untouched_hard
        results.append({"id": ctl["id"], "ok": ok, "desc": ctl["desc"],
                        "expected_fail": ctl["expect_fail"], "observed_fail": flipped,
                        "collateral_fail": untouched_hard})
    for cid, expect, desc, fn in raw_text_controls(m):
        mutated = fn(m["raw"]["schemas/af_scc_c2_vacuum.yaml"])
        tmp = os.path.join(HERE, "controls", f"_{cid}.yaml")
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(mutated)
        res = None
        try:
            m2 = dict(m)
            m2["f2a"] = yaml.safe_load(mutated)
            m2["dups"] = dup_keys(tmp)
            res = run_criteria(m2)
        finally:
            os.remove(tmp)
        flipped = [x for x in expect if not res[x]["ok"]]
        results.append({"id": cid, "ok": len(flipped) == len(expect), "desc": desc,
                        "expected_fail": expect, "observed_fail": flipped,
                        "collateral_fail": []})
    cid, ok, desc = positive_control(m)
    results.append({"id": cid, "ok": ok, "desc": desc, "expected_fail": [], "observed_fail": [],
                    "collateral_fail": []})
    return results


# --------------------------------------------------------------------------- #
def main():
    drift = {}
    for rel, want in PINS.items():
        got = sha256_file(os.path.join(ROOT, rel))
        drift[rel] = {"expected": want, "measured": got, "moved": got != want}
    companion = {}
    for rel, spec in COMPANION.items():
        got = sha256_file(os.path.join(ROOT, rel))
        man = json.loads(open(os.path.join(ROOT, rel), "r", encoding="utf-8").read())
        entry = man.get("files", {}).get("schemas/af_scc_c2_vacuum.yaml", {}).get("sha256")
        companion[rel] = {"revision": man.get("revision"), "frozen_at": man.get("frozen_at"),
                          "entry_sha256": entry, "file_sha256": got}
        if man.get("revision") != spec["revision"] or entry != PINS["schemas/af_scc_c2_vacuum.yaml"]:
            drift[rel] = {"expected": f"revision={spec['revision']} entry={PINS['schemas/af_scc_c2_vacuum.yaml'][:16]}",
                          "measured": f"revision={man.get('revision')} entry={str(entry)[:16]}", "moved": True}
    if any(v["moved"] for v in drift.values()):
        print(json.dumps({"verdict": "PIN_DRIFT", "drift": drift, "companion": companion}, indent=1))
        return 2

    try:
        m = load_model(ROOT)
    except Exception as exc:
        print(json.dumps({"verdict": "PARSE_ERROR", "error": str(exc)}, indent=1))
        return 5

    checks = dict(run_criteria(m))
    controls = run_controls(m)
    f2a_cs, f2a_cat = mprime_status(m["f2a"])
    f2b_cs, f2b_cat = mprime_status(m["f2b"])
    sibling_comparison = {
        "f2a_mprime_category_frozen": bool(f2a_cat),
        "f2b_mprime_category_frozen": bool(f2b_cat),
        "f2b_clause": f2b_cs,
        "note": "the C0 sibling F2b froze M' as a SMOOTH (C-infinity) 4-manifold after accepted repair F2b-16-03; F2a does not fix any category",
    }

    hard_fail = [c for c in checks.values() if c["severity"] == "hard" and not c["ok"]]
    soft_fail = [c for c in checks.values() if c["severity"] == "soft" and not c["ok"]]
    controls_ok = all(c["ok"] for c in controls)

    report = {
        "schema": "w047-f2a-rev13-verdict/v1",
        "task_id": "W047-F2A-REV13-VERDICT-01",
        "target": {"path": "schemas/af_scc_c2_vacuum.yaml", "class_id": CLASS_ID,
                   "node_id": NODE_ID, "sha256": PINS["schemas/af_scc_c2_vacuum.yaml"],
                   "revision": m["f2a"].get("revision")},
        "pins": {rel: {"sha256": h, "kind": ("content" if rel in PINS else "manifest-companion")}
                 for rel, h in m["hashes"].items()},
        "freeze_manifest": companion,
        "sibling_comparison": sibling_comparison,
        "frozen_revision": m["frozen"].get("revision"),
        "checks": [checks[k] for k in sorted(checks)],
        "summary": {
            "checks_total": len(checks),
            "checks_pass": sum(1 for c in checks.values() if c["ok"]),
            "hard_fail": [c["id"] for c in hard_fail],
            "soft_fail": [c["id"] for c in soft_fail],
        },
        "controls": controls,
        "controls_pass": controls_ok,
        "verdict": ("accept" if not hard_fail else "revise") if controls_ok else "INCONCLUSIVE_CONTROL_FAILURE",
        "authority_note": "worker evidence only; does not set validation_status, node status or a gate verdict",
    }
    if not controls_ok:
        rc = 3
    elif hard_fail:
        rc = 1
    else:
        rc = 0
    report["exit_code"] = rc
    out = os.path.join(HERE, "report.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(json.dumps({"verdict": report["verdict"], "hard_fail": report["summary"]["hard_fail"],
                      "controls_pass": controls_ok, "exit_code": rc}))
    return rc


if __name__ == "__main__":
    sys.exit(main())
