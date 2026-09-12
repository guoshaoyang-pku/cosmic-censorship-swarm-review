#!/usr/bin/env python3
"""W038-F2B-REV13-INDEP-02 — independent read-only G-FORM conformance review of F2b.

Target: schemas/af_scc_c0_vacuum.yaml @ sha256 b2ab6acb2bbe... (rev13, class AF-SCC-C0-VAC-GEN)
Manifest: artifacts/formulation/FROZEN.json revision 29 @ sha256 815e08079aef...

Written for this task only. No owner checker/tool is imported or executed in the canonical tree;
the only re-execution of third-party code is out of scope here (this instrument parses bytes
itself and re-derives every predicate from the primary files).  Read-only: the canonical tree is
never written.  `--controls` writes mutants into a tempdir only.

Usage:
  python3 check_f2b_rev13.py                     # canonical run + control battery
  python3 check_f2b_rev13.py --schema P --json-out O --no-controls
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

CST = timezone(timedelta(hours=8))
ROOT = Path(__file__).resolve().parents[3]
SELF = Path(__file__).resolve()

TARGET = "schemas/af_scc_c0_vacuum.yaml"
TARGET_SHA = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"
MIRROR = "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
FROZEN = "artifacts/formulation/FROZEN.json"
FROZEN_SHA = "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"
F0_CANON = "research_map/formulation_taxonomy.yaml"
F0_CANON_SHA = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
F0_SUPP = "artifacts/formulation/formulation_taxonomy.yaml"
F0_SUPP_SHA = "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1"
CONSISTENCY = "artifacts/formulation/evidence/taxonomy_consistency.json"
CONSISTENCY_SHA = "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b"
VOCAB = "artifacts/formulation/VOCAB_ALIASES.json"
REGISTRY = "artifacts/formulation/VARIANT_REGISTRY.json"
C2 = "schemas/af_scc_c2_vacuum.yaml"
WCC = "schemas/af_wcc_vacuum.yaml"
MAP = "research_map/research_map.json"
W087_SUMMARY = "artifacts/worker-087/gform_independence_r2/summary.json"

EXPECTED_PINS = {
    TARGET: TARGET_SHA,
    MIRROR: TARGET_SHA,
    FROZEN: FROZEN_SHA,
    F0_CANON: F0_CANON_SHA,
    F0_SUPP: F0_SUPP_SHA,
    CONSISTENCY: CONSISTENCY_SHA,
    C2: "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    WCC: "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
}

CLASS_ID = "AF-SCC-C0-VAC-GEN"
SIBLING = "AF-SCC-C2-VAC-GEN"
WCC_CLASS = "AF-WCC-VAC-GEN"
SCALAR_CLASS = "AF-WCC-SCALAR-SPH"

# ---------------------------------------------------------------- helpers


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text())


def load_json(path: Path):
    return json.loads(path.read_text())


def find_line(lines: list[str], needle: str) -> int | None:
    for i, ln in enumerate(lines, 1):
        if needle in ln:
            return i
    return None


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s)).strip()


class Review:
    def __init__(self, root: Path, schema_path: Path):
        self.root = root
        self.schema_path = schema_path
        self.text = schema_path.read_text()
        self.lines = self.text.splitlines()
        self.d = load_yaml(schema_path)
        self.pins = {p: sha256(root / p) for p in EXPECTED_PINS}
        self.checks: list[dict] = []

    def add(self, cid, name, status, detail, evidence=None, falsifier=None):
        self.checks.append({
            "id": cid, "name": name, "status": status, "detail": norm(detail),
            "evidence": evidence or [], "falsifier": falsifier or "",
        })

    # ------------------------------------------------------------ checks

    def c01_target(self):
        h = sha256(self.schema_path)
        mirror = self.root / MIRROR
        mh = sha256(mirror) if mirror.exists() else "MISSING"
        ok = h == TARGET_SHA and mh == TARGET_SHA
        self.add("C01_target_pin", "target bytes and mirror identity", "PASS" if ok else "FAIL",
                 f"canonical {h[:12]} mirror {mh[:12]} (expected {TARGET_SHA[:12]})",
                 [f"{TARGET}#{h}", f"{MIRROR}#{mh}"],
                 "a live re-measure of either path returns a different sha256")

    def c02_manifest(self):
        fp = self.root / FROZEN
        fh = sha256(fp)
        m = load_json(fp)
        rev = m.get("revision")
        files = m.get("files", {})
        c0 = files.get(TARGET, {}).get("sha256")
        mirror = files.get(MIRROR, {}).get("sha256")
        drift = []
        for p, rec in files.items():
            rp = self.root / p
            if not rp.exists():
                drift.append(f"{p}:MISSING")
            elif sha256(rp) != rec.get("sha256"):
                drift.append(f"{p}:MISMATCH")
        ok = (fh == FROZEN_SHA and rev == 29 and c0 == TARGET_SHA == mirror
              and len(files) == 50 and not drift)
        self.add("C02_frozen_manifest", "FROZEN rev29 pins both C0 copies; 50/50 live pins match",
                 "PASS" if ok else "FAIL",
                 f"revision={rev} sha={fh[:12]} pins={len(files)} c0={str(c0)[:12]} mirror={str(mirror)[:12]} drift={drift or 'none'}",
                 [f"{FROZEN}#{fh}"],
                 "any of the 50 pinned files differs from its declared sha256, or FROZEN is not revision 29 at 815e08079aef")

    def c03_identity(self):
        d = self.d
        comp = d.get("class_components", {})
        want = {"asymptotics": "AF", "censorship": "SCC", "matter": "VAC",
                "genericity": "GEN", "regularity_token": "C0"}
        ident = {k: comp.get(k) for k in want}
        ok = (d.get("class_id") == CLASS_ID and d.get("node_id") == "F2b" and ident == want
              and d.get("sibling_disjoint_from") == SIBLING)
        c2_leak = [k for k, v in ident.items() if "C2" in str(v)]
        self.add("C03_class_identity", "class id / node / five component tokens exact; no C2 token in identity",
                 "PASS" if (ok and not c2_leak) else "FAIL",
                 f"class_id={d.get('class_id')} node={d.get('node_id')} components={ident} sibling={d.get('sibling_disjoint_from')}",
                 [f"{TARGET}#{TARGET_SHA}"],
                 "a component token or class id is changed, or a C2 token appears among the identity components")

    def c04_f0_binding(self):
        d = self.d
        b = d.get("f0_binding", {})
        canon = self.root / F0_CANON
        supp = self.root / F0_SUPP
        cons = self.root / CONSISTENCY
        fb = b.get("declared_f0_artifact") == F0_CANON and b.get("declared_f0_sha256") == F0_CANON_SHA
        fb = fb and b.get("class_contract_supplement") == F0_SUPP
        fb = fb and b.get("consistency_evidence") == CONSISTENCY
        fb = fb and b.get("consistency_evidence_sha256") == CONSISTENCY_SHA
        fb = fb and bool(b.get("rule")) and bool(b.get("checked_at"))
        self.add("C04_f0_binding_chain", "F0 canonical + supplement + consistency evidence resolve at live bytes",
                 "PASS" if fb else "FAIL",
                 f"declared_f0={b.get('declared_f0_sha256','?')[:12]} live={sha256(canon)[:12]} "
                 f"consistency={b.get('consistency_evidence_sha256','?')[:12]} live={sha256(cons)[:12]} "
                 f"supplement_live={sha256(supp)[:12]}",
                 [f"{F0_CANON}#{F0_CANON_SHA}", f"{CONSISTENCY}#{CONSISTENCY_SHA}"],
                 "the declared F0 artifact moves off 0abb9ed8a961 while this binding is not refreshed")

    def c05_pointers(self):
        d = self.d
        ptr = d.get("class_contract_pointer", "")
        spr = d.get("class_contract_supplement_pointer", "")
        res = {}
        try:
            p, frag = ptr.split("#", 1)
            node = load_yaml(self.root / p)
            for key in frag.split("."):
                node = node[key]
            res["canonical"] = node
        except Exception as e:  # noqa: BLE001
            res["canonical"] = f"ERROR {e}"
        try:
            p, frag = spr.split("#", 1)
            node = load_yaml(self.root / p)
            for key in frag.split("."):
                node = node[key]
            res["supplement"] = node
        except Exception as e:  # noqa: BLE001
            res["supplement"] = f"ERROR {e}"
        c = res["canonical"] if isinstance(res["canonical"], dict) else {}
        f0 = load_yaml(self.root / F0_CANON)
        f0cls = f0.get("classes", {}).get(CLASS_ID, {})
        axes = f0cls.get("axes", {})
        ok = (isinstance(res["canonical"], dict) and isinstance(res["supplement"], dict)
              and c.get("axes", {}).get("regularity_token") == "C0"
              and f0cls.get("axes", {}).get("regularity_token") == "C0")
        self.add("C05_pointer_resolution", "canonical pointer hits classes.*; supplement pointer hits class_contracts.*; F0 axes carry C0",
                 "PASS" if ok else "FAIL",
                 f"canonical_resolves={isinstance(res['canonical'], dict)} supplement_resolves={isinstance(res['supplement'], dict)} "
                 f"f0_axes={axes}",
                 [f"{F0_CANON}#{F0_CANON_SHA}"],
                 "either pointer fails to resolve or the two pointers resolve inside the same file/key space")

    def c06_quantifiers(self):
        d = self.d
        q = d.get("quantifiers", {})
        ordered = q.get("ordered", [])
        kinds = [(o.get("kind"), o.get("binder"), o.get("domain_id")) for o in ordered]
        want = [("forall", "r", "D0"), ("exists", "G_r", "D1"),
                ("forall", "(Sigma,h,K)", "D2"), ("not_exists", "(M',g',iota)", "D3")]
        formal = norm(q.get("formal", ""))
        ok = (kinds == want and q.get("order_matters") is True
              and "forall r in D0" in formal and "exists G_r" in formal
              and "not exists a proper future C0 metric extension" in formal)
        self.add("C06_quantifier_chain", "ordered quantifier chain exact (forall r / exists comeager G_r / forall data / not_exists extension)",
                 "PASS" if ok else "FAIL", f"ordered={kinds} order_matters={q.get('order_matters')}",
                 [f"{TARGET}#{TARGET_SHA}"],
                 "any quantifier kind/domain/order changes, or the comeager existential becomes universal")

    def c07_domains(self):
        d = self.d
        doms = d.get("quantifiers", {}).get("domains", {})
        d0 = norm(doms.get("D0", {}).get("definition", ""))
        ok = ("tagged disjoint union" in d0 and "s > 5/2" in d0 and "delta in (1/2,1)" in d0
              and "ranges over exactly D0" in d0 and "comeager" in norm(doms.get("D1", {}).get("definition", ""))
              and "constraint equations" in norm(doms.get("D2", {}).get("definition", ""))
              and "proper future C0 metric extensions" in norm(doms.get("D3", {}).get("definition", "")))
        self.add("C07_domain_typing", "D0 tagged disjoint union (smooth | (sobolev,s,delta)), D1 comeager, D2 data, D3 extensions",
                 "PASS" if ok else "FAIL", d0[:220],
                 [f"{TARGET}#{TARGET_SHA}"],
                 "D0 stops excluding 'suitable regularity' or the Sobolev bounds change")

    def c08_topology(self):
        d = self.d
        t = d.get("topology", {})
        forb = " ".join(map(str, t.get("forbidden", [])))
        ok = (t.get("spacetime_dimension") == 4 and "one AF end" in norm(t.get("end_structure", ""))
              and "I+" in " ".join(map(str, t.get("conformal_boundary", [])))
              and t.get("I_plus_topology") == "R x S^2"
              and "one asymptotically flat end" in norm(t.get("slice_topology", ""))
              and "closed or periodic" in forb and "more than one asymptotically flat end" in forb)
        self.add("C08_topology", "4d, one AF end, Sigma ~ R^3, I+ = R x S^2, forbidden topologies present",
                 "PASS" if ok else "FAIL", f"dim={t.get('spacetime_dimension')} end={t.get('end_structure')} I+={t.get('I_plus_topology')}",
                 [f"{TARGET}#{TARGET_SHA}"], "a topology field admits a closed slice, a second end, or drops I+")

    def c09_regularity(self):
        d = self.d
        r = d.get("regularity", {})
        ok = (r.get("extension_regularity") == "C0"
              and "continuous (C0) nondegenerate Lorentzian metric" in norm(r.get("extension_regularity_exact", ""))
              and "no differentiability assumed" in norm(r.get("extension_regularity_exact", ""))
              and r.get("extension_solution_concept") == "none"
              and r.get("i_plus_regularity", "").startswith("gtilde extends to I+"))
        self.add("C09_extension_regularity", "frozen extension regularity is exactly C0 with no equation requirement",
                 "PASS" if ok else "FAIL",
                 f"extension_regularity={r.get('extension_regularity')} solution_concept={r.get('extension_solution_concept')}",
                 [f"{TARGET}#{TARGET_SHA}"],
                 "extension_regularity is upgraded to C1/C2/H2_loc or an equation concept appears")

    def c10_genericity(self):
        d = self.d
        g = d.get("genericity", {})
        var = {v.get("kind"): v.get("statement_strength") for v in g.get("variants", [])}
        amb = norm(g.get("ambient_space", "")).lower()
        ok = (g.get("kind") == "residual_comeager" and g.get("is_part_of_class") is True
              and "subspace topology" in amb
              and "baire" in amb
              and "countable intersection of open dense" in norm(g.get("generic_set", "")).lower()
              and var.get("open_dense_escape") == "strictly_stronger"
              and var.get("dense_escape") == "strictly_weaker"
              and var.get("full_measure") == "incomparable")
        self.add("C10_genericity", "comeager class identity; variant strength table direction-correct",
                 "PASS" if ok else "FAIL", f"kind={g.get('kind')} part_of_class={g.get('is_part_of_class')} variants={var}",
                 [f"{TARGET}#{TARGET_SHA}"],
                 "genericity is silently strengthened/weakened, or a variant strength is inverted")

    def c11_iplus_visibility(self):
        d = self.d
        ip = d.get("i_plus", {})
        vis = d.get("visibility", {})
        concl = d.get("conclusion", {})
        operative = " ".join(norm(concl.get(k, "")) for k in
                             ("conclusion_type", "statement_formal", "statement_natural_language")).lower()
        ok = (ip.get("role") == "assumption" and ip.get("in_conclusion") is False
              and ip.get("completeness_in_conclusion") is False
              and vis.get("role") == "not_in_conclusion"
              and vis.get("visible_singularity_is_wcc") is True
              and "WCC falsifier" in norm(vis.get("forbidden_falsifier", ""))
              and "i+ completeness" not in operative and "visibility" not in operative
              and "predictability" not in operative)
        self.add("C11_iplus_visibility_scope", "I+ and visibility are assumptions only; WCC predicate excluded from conclusion",
                 "PASS" if ok else "FAIL",
                 f"i_plus.role={ip.get('role')} in_conclusion={ip.get('in_conclusion')} visibility.role={vis.get('role')}",
                 [f"{TARGET}#{TARGET_SHA}"],
                 "I+ completeness or visibility enters the conclusion/falsifier, i.e. a WCC merge")

    def c12_conclusion(self):
        d = self.d
        c = d.get("conclusion", {})
        s = norm(c.get("statement_formal", ""))
        fs = " ".join(map(str, c.get("forbidden_strengthenings", [])))
        fw = " ".join(map(str, c.get("forbidden_weakenings", [])))
        ok = (c.get("conclusion_type") and c.get("family") == "SCC"
              and c.get("epistemic_status") == "open_problem"
              and "forall r in D0" in s and "not exists proper_future_extension_in_class" in s
              and "for ALL AF vacuum data" in fs and "I+ completeness" in fs
              and "substituting C2 or C1 for C0" in fw
              and "theorem requires artifact_refs" in norm(c.get("claim_promotion", "")))
        self.add("C12_conclusion_inflation_guards", "conclusion typed/formally quantified; all-data, WCC and C2/C1 substitutions forbidden",
                 "PASS" if ok else "FAIL",
                 f"type={c.get('conclusion_type')} family={c.get('family')} status={c.get('epistemic_status')}",
                 [f"{TARGET}#{TARGET_SHA}"],
                 "a forbidden strengthening/weakening entry is removed or the promotion rule is weakened")

    def c13a_containment_larger(self):
        d = self.d
        ft = d.get("implication_ledger", {}).get("forbidden_transfers", [])
        row = next((r for r in ft if r.get("from") == "no proper future C2 extension" and r.get("to") == "this class"), {})
        reason = norm(row.get("reason", ""))
        chain = norm(d.get("implication_ledger", {}).get("extension_class_containment", ""))
        inverted = "strictly larger" in reason and "E_C2" in chain and "contains E_C2" in chain
        self.add("C13a_containment_premise", "forbidden-transfer premise must agree with the containment chain (E_C2 smallest)",
                 "FAIL" if inverted else "PASS",
                 f"reason={reason!r}; chain says {chain[:150]!r} -> 'strictly larger' for C2 is inverted",
                 [f"{TARGET}#{TARGET_SHA}"],
                 "repair the premise to 'strictly smaller' (or equivalent); the check then passes and the transfer direction itself stays correct")

    def c13b_containment_denial(self):
        d = self.d
        mlist = d.get("regularity", {}).get("must_not_conflate", [])
        denial = [m for m in mlist if "No containment with C2 or C0 is asserted here" in str(m)]
        chain = norm(d.get("implication_ledger", {}).get("extension_class_containment", ""))
        contradictory = bool(denial) and "contains E_C2" in chain and "contains E_H2loc" in chain
        self.add("C13b_containment_denial", "the H2_loc 'no containment' denial must not contradict the asserted chain",
                 "FAIL" if contradictory else "PASS",
                 f"denial={norm(denial[0])[:180] if denial else 'absent'} vs chain={chain[:130]!r}",
                 [f"{TARGET}#{TARGET_SHA}"],
                 "scope or delete the denial (keep 'strictly between' forbidden); the check then passes")

    def c14_conclusion_vocab(self):
        d = self.d
        tok = d.get("conclusion", {}).get("conclusion_type")
        f0 = load_yaml(self.root / F0_CANON)
        allowed = f0.get("field_vocabulary", {}).get("conclusion_type", {}).get("allowed", [])
        aliases = load_json(self.root / VOCAB).get("conclusion_type", {})
        f0_axes = f0.get("classes", {}).get(CLASS_ID, {}).get("axes", {}).get("conclusion_type")
        eqclass = {}
        for canon, alist in aliases.items():
            for member in [canon] + list(alist):
                eqclass[member] = canon

        def eclass(tok):
            return eqclass.get(tok, tok)

        in_allowed = tok in allowed
        same_semantics = eclass(tok) == eclass(f0_axes)
        vocab_canonical = set(aliases.keys())
        f0_disagrees = bool(vocab_canonical - set(allowed))
        self.add("C14a_vocab_in_f0_allowed", "schema conclusion_type is a literal member of the F0 allowed vocabulary",
                 "PASS" if in_allowed else "FAIL",
                 f"token={tok!r} allowed={allowed}",
                 [f"{F0_CANON}#{F0_CANON_SHA}"],
                 "the F0 vocabulary is re-frozen to admit the token, or the schema is re-stamped to strong_cosmic_censorship_C0")
        self.add("C14b_vocab_alias_equivalent", "token and F0 class axes token lie in the same VOCAB_ALIASES equivalence class (direction-agnostic)",
                 "PASS" if same_semantics else "FAIL",
                 f"token={tok!r} f0_axes={f0_axes!r} class={eclass(tok)!r}",
                 [f"{VOCAB}#{sha256(self.root / VOCAB)[:12]}"],
                 "the alias equivalence classes are changed or the F0 class axes token changes")
        self.add("C14c_vocab_direction", "VOCAB_ALIASES canonical spelling agrees with the F0 declared vocabulary (no frozen-artifact disagreement)",
                 "PASS" if not f0_disagrees else "FAIL",
                 f"vocab_canonical={sorted(vocab_canonical)} f0_allowed={allowed} disagreement={sorted(vocab_canonical - set(allowed))}",
                 [f"{VOCAB}#{sha256(self.root / VOCAB)[:12]}", f"{F0_CANON}#{F0_CANON_SHA}"],
                 "one of the two artifacts is re-frozen so the canonical spelling agrees; the check then passes")

    def c15_falsifier(self):
        d = self.d
        f = d.get("falsifier", {})
        t1, t2 = f.get("tier_1", {}), f.get("tier_2", {})
        if isinstance(t1.get("refutes"), str):
            r1 = t1["refutes"]
        else:
            r1 = str(t1.get("refutes"))
        ok = (CLASS_ID in r1 or r1 == CLASS_ID)
        ok = ok and "non-meager" in norm(t1.get("genericity_requirement", ""))
        ok = ok and "One extendible datum is NOT sufficient" in norm(t1.get("genericity_requirement", ""))
        ok = ok and len(t1.get("machine_checkable_steps", [])) >= 4
        ok = ok and "non-meagerness" in norm(t1.get("non_machine_checkable_step", ""))
        ok = ok and t2.get("labelling_required") == "refutes_strengthening_only"
        ok = ok and "forall AF vacuum data" in norm(t2.get("refutes", ""))
        self.add("C15_falsifier_tiering", "tier_1 refutes this class with named non-mechanizable obligation; tier_2 only the all-data strengthening",
                 "PASS" if ok else "FAIL", f"tier1={norm(r1)[:70]} nonmech={t1.get('non_machine_checkable_step')!r}",
                 [f"{TARGET}#{TARGET_SHA}"],
                 "the non-meagerness obligation or the tier separation is removed/weakened")

    def c16_antiscope(self):
        d = self.d
        a = d.get("anti_scope", {})
        blob = json.dumps(a)
        ids = [x.get("class_id") for x in a.get("not_this_class", []) if isinstance(x, dict)]
        ok = (SIBLING in ids and WCC_CLASS in ids and SCALAR_CLASS in ids
              and "H2LOC" in blob and "DISTRIBUTIONAL" in blob
              and any("C0 or C2" in str(p) for p in a.get("phrases_that_are_not_this_class", []))
              and d.get("class_id") == CLASS_ID)
        # the composite phrase may only appear in the quoted phrase list, never as a field value
        composite_fields = [k for k, v in d.items() if "C0 or C2" in json.dumps(v) and k != "anti_scope"]
        self.add("C16_anti_scope", "sibling/WCC/scalar classes and both regularity/equation variants excluded; no composite token outside the quoted list",
                 "PASS" if (ok and not composite_fields) else "FAIL",
                 f"ids={ids} composite_fields_outside_antiscope={composite_fields}",
                 [f"{TARGET}#{TARGET_SHA}"],
                 "a sibling/variant entry is dropped, or 'C0 or C2' appears as an operative value")

    def c17_no_selfpromotion(self):
        d = self.d
        rs = d.get("review_status", {})
        ks = d.get("known_status", {})
        ok = (rs.get("independent_reviewers") == [] and rs.get("verdict") == "pending"
              and d.get("epistemic_status") == "open_problem"
              and "checked proof artifact" in norm(d.get("promotion_rule", ""))
              and "open_problem" in norm(ks.get("status", ""))
              and "quarantined to variant CH" in norm(ks.get("consequence", "")))
        self.add("C17_no_self_promotion", "schema claims no review, no theorem, no refutation status",
                 "PASS" if ok else "FAIL",
                 f"independent_reviewers={rs.get('independent_reviewers')} verdict={rs.get('verdict')} epistemic={d.get('epistemic_status')}",
                 [f"{TARGET}#{TARGET_SHA}"],
                 "the schema self-records a reviewer/verdict or a proved/refuted status")

    def c18_provenance(self):
        d = self.d
        p = d.get("provenance", {})
        ui = d.get("unresolved_items", [])
        l1 = d.get("l1_ledger_refs", [])
        t305 = next((r for r in l1 if r.get("theorem_id") == "T-305"), {})
        ok = (p.get("citation_status") == "unverified" and len(ui) >= 4
              and any("diffeomorphism-quotient" in str(x) for x in ui)
              and t305.get("l1_status") == "provisional" and t305.get("citation_status") == "unresolved")
        self.add("C18_provenance_honesty", "citations marked unverified; unresolved items retained; T-305 provisional/unresolved",
                 "PASS" if ok else "FAIL", f"citation_status={p.get('citation_status')} unresolved_items={len(ui)} t305={t305.get('l1_status')}",
                 [f"{TARGET}#{TARGET_SHA}"],
                 "an unresolved citation or item is silently promoted to verified")

    def c19_variants(self):
        d = self.d
        civ = d.get("class_identity_variants", {})
        ch = civ.get("horizon_localized_variant", {})
        reg = load_json(self.root / REGISTRY)
        chreg = next((v for v in reg.get("variants", []) if v.get("variant_id") == "CH"), {})
        ok = (ch.get("parent_class", CLASS_ID) == CLASS_ID and ch.get("is_this_class") is False
              and "strictly WEAKER" in norm(ch.get("relation", ""))
              and chreg.get("parent_class") == CLASS_ID
              and "quarantined to variant CH" in norm(d.get("known_status", {}).get("consequence", "")))
        self.add("C19_variant_binding", "variant CH is a non-class variant of this parent; the T-301 conditional refutation stays quarantined",
                 "PASS" if ok else "FAIL", f"ch_parent={chreg.get('parent_class')} ch_is_this_class={ch.get('is_this_class')} relation={norm(ch.get('relation',''))[:80]}",
                 [f"{REGISTRY}#{sha256(self.root / REGISTRY)[:12]}"],
                 "variant CH is promoted to the class or the quarantined refutation is recorded as settling the class")

    def c20_no_merge(self):
        d = self.d
        ident = json.dumps({"class_id": d.get("class_id"), "components": d.get("class_components"),
                            "conclusion_type": d.get("conclusion", {}).get("conclusion_type"),
                            "family": d.get("conclusion", {}).get("family")})
        bad = [t for t in ("C0 or C2", "C0/C2", "C2 or C0") if t in ident]
        self.add("C20_no_c0_c2_merge", "no composite regularity in identity or conclusion fields",
                 "PASS" if not bad else "FAIL", f"composite tokens in identity/conclusion: {bad or 'none'}",
                 [f"{TARGET}#{TARGET_SHA}"],
                 "a composite token appears in an operative identity/conclusion field")

    def c21_coverage(self):
        mp = self.root / MAP
        m = load_json(mp)
        revs = [r for r in m.get("reviews", []) if isinstance(r, dict)]
        bound = [r for r in revs if TARGET_SHA in json.dumps(r, default=str)]
        accepts = [r for r in bound if r.get("verdict") == "accept"]
        scoped, full = [], []
        for r in accepts:
            blob = json.dumps(r, default=str)
            scoped_marker = ("not the full schema" in blob or "does not substitute" in blob
                             or r.get("counts_as_full_schema_verdict") is False)
            (scoped if scoped_marker else full).append(r.get("event_id"))
        w087 = {}
        ws = self.root / W087_SUMMARY
        if ws.exists():
            w087 = load_json(ws).get("per_class", {}).get("F2b", {})
        claimed = w087.get("full_schema_accept_reviewers", [])
        ok = len(full) >= 2
        self.add("C21_accept_coverage", "recompute full-schema F2b accepts at the pinned rev13 bytes",
                 "PASS" if ok else "FAIL",
                 f"full_schema_accepts={full or []} scoped_or_advisory_accepts={scoped or []} "
                 f"w087_claimed={claimed} w087_clusters={w087.get('effective_independent_full_schema_accept_clusters')}",
                 [f"{MAP}#{sha256(mp)[:12]}", f"{W087_SUMMARY}#{sha256(ws)[:12]}" if ws.exists() else W087_SUMMARY],
                 "a genuinly full-schema accept bound to this sha256 from a separate cluster is produced; "
                 "the w087 count is then reconciled, not merely contradicted")

    def c22_stability(self):
        after = {p: sha256(self.root / p) for p in EXPECTED_PINS}
        ok = after == self.pins
        moved = {p: (self.pins[p][:12], after[p][:12]) for p in after if self.pins[p] != after[p]}
        self.add("C22_input_stability", "all pinned inputs unchanged across the run (moving-target stop rule)",
                 "PASS" if ok else "FAIL", f"moved={moved or 'none'}",
                 [f"{TARGET}#{after[TARGET]}"],
                 "any pinned input moves during the run: the verdict is void and must be re-bound")

    def run(self):
        for c in (self.c01_target, self.c02_manifest, self.c03_identity, self.c04_f0_binding,
                  self.c05_pointers, self.c06_quantifiers, self.c07_domains, self.c08_topology,
                  self.c09_regularity, self.c10_genericity, self.c11_iplus_visibility,
                  self.c12_conclusion, self.c13a_containment_larger, self.c13b_containment_denial,
                  self.c14_conclusion_vocab, self.c15_falsifier, self.c16_antiscope,
                  self.c17_no_selfpromotion, self.c18_provenance, self.c19_variants,
                  self.c20_no_merge, self.c21_coverage, self.c22_stability):
            try:
                c()
            except Exception as e:  # noqa: BLE001
                self.add(c.__name__, c.__name__, "FAIL", f"check raised {type(e).__name__}: {e}")
        return self.checks


# ---------------------------------------------------------------- controls

MUTANTS = {
    # ("anchor", "replacement", expected_check, expectation)
    #   expectation "pass": the check must flip FAIL->PASS (repair mutant)
    #   expectation "fail": the check must be FAIL in the mutant (tamper mutant)
    "M01_conclusion_token_repaired": (
        "conclusion_type: scc_c0_future_inextendibility",
        "conclusion_type: strong_cosmic_censorship_C0",
        ("C14a_vocab_in_f0_allowed", "C14b_vocab_alias_equivalent"), "pass"),
    "M02_containment_premise_repaired": (
        "C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker",
        "C2 is a strictly smaller extension class, so C2-inextendibility is strictly weaker",
        ("C13a_containment_premise",), "pass"),
    "M03_denial_scoped": (
        "No containment with C2 or C0 is asserted here",
        "This bullet asserts only that 'strictly between' is not used; the containment chain is stated in implication_ledger",
        ("C13b_containment_denial",), "pass"),
    "M04_quantifier_tamper": (
        '- {kind: exists, binder: "G_r", domain_id: D1}',
        '- {kind: forall, binder: "G_r", domain_id: D1}', ("C06_quantifier_chain",), "fail"),
    "M05_regularity_upgrade": (
        "extension_regularity: C0", "extension_regularity: C1", ("C09_extension_regularity",), "fail"),
    "M06_iplus_leak": (
        "  in_conclusion: false\n  completeness_in_conclusion: false",
        "  in_conclusion: true\n  completeness_in_conclusion: true", ("C11_iplus_visibility_scope",), "fail"),
    "M07_selfpromotion": (
        "independent_reviewers: []\n  verdict: pending",
        "independent_reviewers: [worker-038]\n  verdict: accept", ("C17_no_self_promotion",), "fail"),
    "M08_falsifier_strip": (
        'non_machine_checkable_step: "non-meagerness of the extendible set"',
        'non_machine_checkable_step: "none"', ("C15_falsifier_tiering",), "fail"),
    "M09_classid_tamper": (
        "class_id: AF-SCC-C0-VAC-GEN\nnode_id: F2b",
        "class_id: AF-SCC-C2-VAC-GEN\nnode_id: F2b", ("C03_class_identity",), "fail"),
    "M10_weakening_strip": (
        '    - "substituting C2 or C1 for C0, or citing a C2 result as evidence for this class"\n', '',
        ("C12_conclusion_inflation_guards",), "fail"),
}
IGNORE_IN_CONTROLS = {"C01_target_pin", "C22_input_stability"}


def controls(root: Path) -> dict:
    baseline_checks = Review(root, root / TARGET).run()
    baseline = {c["id"]: c["status"] for c in baseline_checks}
    results, td = [], tempfile.mkdtemp(prefix="w038_f2b_controls_")
    try:
        for name, (old, new, expect, expectation) in MUTANTS.items():
            src = (root / TARGET).read_text()
            if old not in src:
                results.append({"mutant": name, "status": "CONTROL_ERROR",
                                "detail": f"anchor not found: {old[:60]!r}"})
                continue
            mdir = Path(td) / name
            mdir.mkdir(parents=True)
            mp = mdir / "mutant.yaml"
            mp.write_text(src.replace(old, new, 1))
            out = mdir / "report.json"
            subprocess.run([sys.executable, str(SELF), "--schema", str(mp), "--json-out", str(out),
                            "--no-controls"], check=False, capture_output=True, text=True)
            rep = json.loads(out.read_text())
            st = {c["id"]: c["status"] for c in rep["checks"]}
            if expectation == "pass":
                fired = all(st.get(e) == "PASS" for e in expect)
                detail = f"{name}: {expect} " + ("flipped FAIL->PASS" if fired else
                                                 f"did not flip (mutant statuses {[st.get(e) for e in expect]})")
            else:
                fired = all(st.get(e) == "FAIL" for e in expect)
                detail = f"{name}: {expect} " + ("fired" if fired else
                                                 f"DID NOT fire (mutant statuses {[st.get(e) for e in expect]})")
            results.append({"mutant": name, "status": "PASS" if fired else "FAIL",
                            "expected_check": list(expect), "expectation": expectation,
                            "expected_fired": fired, "detail": detail})
        expected_baseline = {"C13a_containment_premise", "C13b_containment_denial",
                             "C14a_vocab_in_f0_allowed", "C14c_vocab_direction", "C21_accept_coverage"}
        extra = {k for k, v in baseline.items() if v == "FAIL"} - expected_baseline
        results.append({"mutant": "BASELINE_no_false_positives", "status": "PASS" if not extra else "FAIL",
                        "expected_check": "none beyond the five declared defect checks",
                        "expected_fired": not extra,
                        "detail": f"unexpected baseline failures={sorted(extra)}"})
    finally:
        shutil.rmtree(td, ignore_errors=True)
    passed = sum(1 for r in results if r["status"] == "PASS")
    return {"controls": results, "passed": passed, "total": len(results),
            "baseline_failures": sorted(k for k, v in baseline.items() if v == "FAIL")}


# ---------------------------------------------------------------- main

def build_report(root: Path, schema_path: Path, with_controls: bool) -> dict:
    rv = Review(root, schema_path)
    checks = rv.run()
    fails = [c for c in checks if c["status"] == "FAIL"]
    hard = [c["id"] for c in fails]
    findings = [
        {"id": "W038-F2B13-01", "severity": "H", "gate_blocking": True, "check": "C13a_containment_premise",
         "text": "implication_ledger.forbidden_transfers row (from 'no proper future C2 extension') justifies itself with "
                 "'C2 is a strictly larger extension class' while implication_ledger.extension_class_containment makes "
                 "E_C2 the smallest extension class (E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2). The transfer "
                 "conclusion is right; the stated premise is inverted.",
         "repair": "premise -> 'C2 is a strictly smaller extension class' (or restate as 'E_C2 is a subset of E_C0')."},
        {"id": "W038-F2B13-02", "severity": "H", "gate_blocking": True, "check": "C13b_containment_denial",
         "text": "regularity.must_not_conflate says of H2_loc 'No containment with C2 or C0 is asserted here' while the "
                 "implication ledger asserts exactly that containment chain; a reader can take either the denial or the "
                 "chain as operative. The bullet's legitimate function (no 'strictly between' phrasing) does not require "
                 "denying containment.",
         "repair": "scope the sentence to the phrase ban or delete the denial; keep the chain as the single operative statement."},
        {"id": "W038-F2B13-03", "severity": "H", "gate_blocking": True, "check": "C14a_vocab_in_f0_allowed + C14c_vocab_direction",
         "text": "conclusion.conclusion_type='scc_c0_future_inextendibility' is not a member of the F0 declared "
                 "field_vocabulary.conclusion_type.allowed ['weak_cosmic_censorship','strong_cosmic_censorship_C2',"
                 "'strong_cosmic_censorship_C0']; VOCAB_ALIASES.json declares the scc_* spellings canonical and the F0 "
                 "spellings aliases, so the two frozen artifacts disagree about which token is canonical (C14c) and the "
                 "canonical schema carries the alias-file spelling, not the F0-declared one (C14a). The token is "
                 "semantically the same class (C14b passes), so this is a spelling/direction adjudication, not a class "
                 "merge; but under the alias policy ('aliases ... must never appear in a new canonical artifact') the "
                 "canonical F2b artifact is non-conformant with the bound F0 vocabulary until one side is re-frozen.",
         "repair": "one adjudicated token; then re-stamp the losing artifact (F0 re-freeze voids G-F0 and must not be done "
                   "casually; re-stamping F2b to strong_cosmic_censorship_C0 is the lower-blast-radius repair and makes "
                   "C14a/C14c pass at the next hash)."},
        {"id": "W038-F2B13-04", "severity": "H", "gate_blocking": False, "check": "C21_accept_coverage",
         "text": "Coverage recomputation: the only 'accept' bound to b2ab6acb2bbe that the W087 independence measurement "
                 "counts as an F2b full-schema cluster is worker-061's event, whose own findings begin 'SCOPED: this verdict "
                 "covers ONLY the variant-CH strictness axis ... not the full schema; the blind full-schema F2b round remains "
                 "the binding coverage.' worker-053's accept is a CF-20 binding verification that says it 'does not move "
                 "G-FORM'. At the pinned bytes the recomputed number of valid full-schema accepts is 0, not 1; every "
                 "full-schema verdict on this hash that binds the whole schema is revise (workers 017, 018, 034, 035, 044, 062, "
                 "066, 075, 095, ...). The G-FORM F2b criterion is therefore not merely one accept short: it has no accept.",
         "repair": "owner repairs F2b to a rev14 and re-freezes; then two genuinely full-schema, blind-or-disclosed accepts "
                   "are required, and W087's cluster count must be recomputed with the scoped-accept exclusion."},
        {"id": "W038-F2B13-05", "severity": "N", "gate_blocking": False, "check": "C13a_containment_premise",
         "text": "conclusion_relation_to_sibling writes 'the one-way entailment C0 => C2 is recorded in implication_ledger'; "
                 "the ledger records the entailment between the inextendibility statements (no C0 extension => no C2 "
                 "extension), not a class-level arrow. Notation only; no semantic inversion."},
        {"id": "W038-F2B13-06", "severity": "N", "gate_blocking": False, "check": "C02_frozen_manifest",
         "text": "FROZEN rev29 is byte-stable at 815e08079aef and all 50 pins match disk across this run, but CF-27's "
                 "same-revision rewrite (3d9e3d77 00:55:02 -> 815e08079aef 00:57:26) means a verdict must cite the manifest "
                 "sha256, never 'rev29' alone. This verdict is bound to 815e08079aef and to b2ab6acb2bbe."},
    ]
    rep = {
        "schema_version": "1.0",
        "task_id": "W038-F2B-REV13-INDEP-02",
        "actor": "worker-038",
        "class_id": CLASS_ID,
        "node_id": "F2b",
        "gate": "G-FORM",
        "created_at": now(),
        "scope": "independent read-only full-schema G-FORM conformance review of F2b at the FROZEN rev29 pin; "
                 "no gate verdict, no node completion, no canonical write",
        "reviewer_independence": {
            "authored_target": False,
            "instrument": "written for this task; parses primary bytes only; imports no owner checker",
            "non_blind_disclosure": "adverse verdicts on this hash (workers 017/018/066/075) were read before writing this "
                                    "instrument; the two containment defects were re-derived from the target's own lines and "
                                    "independently encoded, and every other check is this instrument's own",
            "template_reuse": "none",
        },
        "target": {"path": TARGET, "sha256": sha256(root / TARGET)},
        "target_mirror": {"path": MIRROR, "sha256": sha256(root / MIRROR)},
        "manifest": {"path": FROZEN, "sha256": sha256(root / FROZEN), "revision": load_json(root / FROZEN).get("revision")},
        "pins_before": rv.pins,
        "checks": checks,
        "summary": {"passed": sum(1 for c in checks if c["status"] == "PASS"),
                    "failed": len([c for c in fails if c["status"] == "FAIL"]),
                    "notes": sum(1 for c in checks if c["status"] == "NOTE")},
        "hard_failures": hard,
        "findings": findings,
        "verdict": "revise" if hard else "accept",
        "score": 3.0 if hard else 4.0,
        "falsifier": "Any of: (a) the target or mirror moves off b2ab6acb2bbe / FROZEN moves off 815e08079aef before "
                     "ingest; (b) C13a/C13b/C14a is shown to be a misreading of the pinned bytes (quote the operative "
                     "sentence and show the containment chain agrees with it); (c) a valid full-schema accept at this hash "
                     "from a separate cluster is produced, which would falsify the coverage finding only, not the "
                     "containment findings; (d) a mutation control fails to fire on re-run.",
        "inputs_stable": rv.pins == {p: sha256(root / p) for p in EXPECTED_PINS},
    }
    rep["pins_after"] = {p: sha256(root / p) for p in EXPECTED_PINS}
    if with_controls:
        rep["controls"] = controls(root)
        rep["authority"] = ("worker evidence only; cannot set node status=done, validation_status=passed or a gate verdict")
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--schema", default=None)
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--no-controls", action="store_true")
    a = ap.parse_args()
    schema = Path(a.schema) if a.schema else ROOT / TARGET
    rep = build_report(ROOT, schema, with_controls=not a.no_controls)
    txt = json.dumps(rep, indent=2, sort_keys=True, default=str)
    if a.json_out:
        Path(a.json_out).write_text(txt)
    else:
        print(txt)
    print(json.dumps({k: rep[k] for k in ("verdict", "score", "hard_failures", "summary")}, indent=1))


if __name__ == "__main__":
    main()
