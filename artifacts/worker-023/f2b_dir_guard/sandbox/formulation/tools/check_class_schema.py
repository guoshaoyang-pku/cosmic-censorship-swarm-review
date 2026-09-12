#!/usr/bin/env python3
"""Canonical structural gate for class-bound formulation schemas (FORM-RULE-SPEC R01-R16).

Owner: astra-lead-formulation.  This is the binding gate implementation for F1/F2a/F2b.

WHAT IT DECIDES: structure only. It rejects a schema that omits a required class-bound
slot, conflates the frozen axes, merges C0/C2, puts foreign-family content in the
ASSERTED blocks, or promotes a conclusion. It does NOT decide physical correctness,
truth, or the scope of any cited source.

KNOWN BLIND SPOTS (measured, not assumed):
  * lexical leakage scan covers ASSERTIVE_PATHS only; a semantic leak expressed purely in
    un-scanned prose fields passes (worker-06 FORM-LEAK-03 owns the rephrased corpus);
  * no check that the mathematics in a definition is correct, only that it is present,
    non-vague (numeric or referenced), and class-consistent;
  * citation scope is not verified; `unresolved` is accepted at face value.

USAGE
  python3 check_class_schema.py SCHEMA.yaml            # exit 0 pass / 1 fail / 2 usage
  python3 check_class_schema.py --json SCHEMA.yaml     # machine report on stdout
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("PyYAML required", file=sys.stderr)
    sys.exit(2)

SPEC = Path(__file__).resolve().parents[1] / "rule_spec.json"
KEY_MANIFEST = Path(__file__).resolve().parents[1] / "KEY_MANIFEST.json"
EXT_DEFAULT = {"AF-WCC-VAC-GEN": None, "AF-SCC-C2-VAC-GEN": {"direction": "future", "regularity": "C2", "concept": "classical_ricci"},
               "AF-SCC-C0-VAC-GEN": {"direction": "future", "regularity": "C0", "concept": "none"}}
FROZEN_GENERICITY = "residual_comeager"
SPEC_D = json.loads(SPEC.read_text())
CLASSES = SPEC_D["frozen_classes"]
FAMILY = SPEC_D["class_family"]
CONC = SPEC_D["vocabularies"]["class_conclusion_type"]
EXT_CONCEPT = {"AF-SCC-C2-VAC-GEN": "classical_ricci", "AF-SCC-C0-VAC-GEN": "none"}

# keys whose subtree is negative/prescriptive: leakage tokens there are legitimate
EXEMPT_KEY = re.compile(
    r"^(forbidden|must_not|anti_scope|not_|excluded|variants|phrases_that_are_not|why_|reason$|"
    r"sibling_|derived_|visible_singularity_is_wcc$|no_|never_|c0_uniqueness_caveat$|"
    r"composite_regularity_ban$|terminology_disambiguation$|schema_falsifiers$|vacuity_falsifier$|"
    r"class_change_warning$|subsumption_note$|observability_note$|equivalence_claim$|"
    r"non_goals$|forbidden_strengthenings$|forbidden_weakenings$|forbidden_transfers$)", re.I)

# assertive content only: foreign-family content here is leakage
ASSERTIVE_PATHS = [
    ("conclusion", "statement_natural_language"),
    ("conclusion", "statement_formal"),
    ("conclusion", "conclusion_type"),
    ("conclusion", "equivalent_standard_formulation", "predicate"),
    ("conclusion", "equivalent_rephrasings"),
    ("visibility", "predicate_name"),
    ("visibility", "definition"),
    ("visibility", "negation_conclusion"),
    ("visibility", "visible_singularity_exists"),
    ("i_plus", "definition"),
    ("i_plus", "completeness_definition"),
    ("i_plus", "required_properties"),
    ("falsifier", "tier_1", "refutes"),
    ("falsifier", "tier_1", "witness_type"),
    ("non_vacuity", "condition"),
    ("non_vacuity", "witness_type"),
    ("genericity", "generic_set"),
    ("falsifier", "tier_2", "refutes"),
    ("falsifier", "tier_2", "witness_type"),
    ("extension_predicate", "definition"),
    ("extension_predicate", "frozen_regularity"),
    ("scope_statement",),
]
# CALIBRATION (measured, 2026-09-12T00:05+08:00): a bare /inextendib/ token produced 3
# false positives on the canonical WCC schema, because WCC legitimately quantifies over
# future-inextendible causal GEODESICS. The token is now conditional: SCC-style
# inextendibility is flagged only when the same assertive string does not speak of geodesics.
FOREIGN = {
    "WCC": [r"strong cosmic censorship", r"cauchy horizon", r"extension[_ ]regularity",
            r"\bC0\b.{0,20}extension", r"\bC2\b.{0,20}extension", "INEXTENDIB_NON_GEODESIC"],
    "SCC": [r"visible", r"visibilit", r"asymptotic[_ ]predictab", r"hidden from", r"weak cosmic censorship"],
}
INEXTENDIB = re.compile(r"inextendib", re.I)
GEODESIC = re.compile(r"geodesic", re.I)
VAGUE = re.compile(r"\b(suitable|appropriate|reasonable|nice|admissible enough|sufficiently generic|some)\b", re.I)
COMPOSITE = re.compile(r"(C0|C2|C\^?0|C\^?2)\s*(or|and|/)\s*(C0|C2|C\^?0|C\^?2)", re.I)
# prose form of a merged regularity class (held-out family h01/h19): word tokens, optional comma
COMPOSITE_PROSE = re.compile(
    r"\b(C0|C2|continuous|twice[- ]differentiable|Lipschitz|H2_loc)\b\s*,?\s*(or|and|/|alternatively)\s*"
    r"(?:\w+\s+){0,2}\b(C0|C2|continuous|twice[- ]differentiable|Lipschitz|H2_loc)\b", re.I)


def get(d, *path, default=None):
    cur = d
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return default
        cur = cur[p]
    return cur


def strings_at(doc, path):
    v = get(doc, *path)
    out = []
    if isinstance(v, str):
        out.append(v)
    elif isinstance(v, list):
        for x in v:
            if isinstance(x, str):
                out.append(x)
            elif isinstance(x, dict):
                out.extend(str(y) for y in x.values() if isinstance(y, str))
    elif isinstance(v, dict):
        out.extend(str(y) for y in v.values() if isinstance(y, str))
    return out


def scan_composite(node, path, hits):
    if isinstance(node, dict):
        for k, v in node.items():
            if EXEMPT_KEY.match(str(k)):
                continue
            scan_composite(v, f"{path}.{k}", hits)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            scan_composite(v, f"{path}[{i}]", hits)
    elif isinstance(node, str) and (COMPOSITE.search(node) or COMPOSITE_PROSE.search(node)):
        hits.append(path)


class Gate:
    def __init__(self, doc, path):
        self.doc = doc
        self.path = path
        self.fails = []
        self.notes = []

    def fail(self, rule, msg):
        self.fails.append({"rule": rule, "msg": msg})

    def run(self):
        d = self.doc
        cid = d.get("class_id")
        fam = FAMILY.get(cid)
        # R01 identity
        for k in ("schema_version", "artifact_kind", "class_id", "node_id", "owner", "epistemic_status"):
            if not d.get(k):
                self.fail("R01", f"missing {k}")
        if d.get("artifact_kind") != "class_schema":
            self.fail("R01", "artifact_kind != class_schema")
        if cid not in CLASSES:
            self.fail("R01", f"class_id {cid} not frozen")
            return self.fails
        # R02 components
        comp = d.get("class_components") or {}
        want = {"asymptotics": "AF", "matter": "VAC", "genericity": "GEN"}
        for k, v in want.items():
            if comp.get(k) != v:
                self.fail("R02", f"class_components.{k}={comp.get(k)} != {v}")
        if comp.get("censorship") != fam:
            self.fail("R02", f"class_components.censorship={comp.get('censorship')} != {fam}")
        tok = comp.get("regularity_token")
        if fam == "SCC" and tok not in ("C0", "C2"):
            self.fail("R02", f"SCC regularity_token {tok!r} must be exactly one of C0/C2")
        if fam == "WCC" and tok not in (None, "none"):
            self.fail("R02", "WCC must carry no regularity_token")
        if fam == "SCC" and tok and tok not in cid:
            self.fail("R02", "regularity_token absent from class_id")
        # R03 quantifiers
        q = d.get("quantifiers") or {}
        ordered = q.get("ordered")
        if not isinstance(ordered, list) or not ordered:
            self.fail("R03", "quantifiers.ordered missing/empty")
        else:
            domains = q.get("domains") or {}
            seen = set()
            for i, e in enumerate(ordered):
                for k in ("kind", "binder", "domain_id"):
                    if not isinstance(e, dict) or not e.get(k):
                        self.fail("R03", f"quantifiers.ordered[{i}] missing {k}")
                did = e.get("domain_id") if isinstance(e, dict) else None
                if did not in domains:
                    self.fail("R03", f"domain_id {did} unresolved")
                else:
                    seen.add(did)
                    body = json.dumps(domains[did])
                    if VAGUE.search(body) and not domains[did].get("definition_ref") and not re.search(r"\d", body):
                        self.fail("R03", f"domain {did} vague and unreferenced")
            if not q.get("formal"):
                self.fail("R03", "quantifiers.formal missing")
            if q.get("order_matters") is not True:
                self.fail("R03", "quantifiers.order_matters must be true")
            if not q.get("negation"):
                self.fail("R03", "quantifiers.negation missing")
        # R04 topology
        t = d.get("topology") or {}
        if t.get("spacetime_dimension") != 4:
            self.fail("R04", "spacetime_dimension != 4")
        if not t.get("slice_topology"):
            self.fail("R04", "slice_topology missing")
        if t.get("completeness_of_slice") is not True:
            self.fail("R04", "completeness_of_slice must be true")
        cb = t.get("conformal_boundary")
        if not isinstance(cb, list) or not all(any(x.split()[0] in s for s in cb) for x in ("I+", "I-", "i0")):
            self.fail("R04", "conformal_boundary must name I+, I-, i0")
        if "R x S^2" not in str(t.get("I_plus_topology", "")):
            self.fail("R04", "I_plus_topology must be R x S^2")
        forb = " ".join(t.get("forbidden") or []).lower()
        if "closed" not in forb or "periodic" not in forb:
            self.fail("R04", "closed/periodic slices must be forbidden explicitly")
        # R05 data class
        dc = d.get("data_class") or {}
        blob = json.dumps(dc).lower()
        if dc.get("matter") not in ("none", None):
            self.fail("R05", "matter must be none for VAC")
        if str(dc.get("cosmological_constant")) not in ("0", "0.0"):
            self.fail("R05", "cosmological_constant must be 0")
        cons = dc.get("constraints") or {}
        if set(cons) < {"hamiltonian", "momentum"}:
            self.fail("R05", "both constraint equations must be named")
        if not dc.get("asymptotic_decay") or not dc.get("adm_mass") or not dc.get("regularity_class"):
            self.fail("R05", "asymptotic_decay / adm_mass / regularity_class missing")
        if dc.get("regularity_class", {}).get("sobolev_variant", {}).get("s") is None:
            self.fail("R05", "named Sobolev index s missing")
        if not re.search(r"\d", blob):
            self.fail("R05", "no numeric content in data_class")
        # R06 regularity
        r = d.get("regularity") or {}
        for k in ("data_regularity", "solution_regularity", "i_plus_regularity", "must_not_conflate"):
            if not r.get(k):
                self.fail("R06", f"regularity.{k} missing")
        if not r.get("must_not_conflate"):
            self.fail("R06", "must_not_conflate empty")
        er, esc = r.get("extension_regularity"), r.get("extension_solution_concept")
        if fam == "SCC":
            if er != tok:
                self.fail("R06", f"SCC extension_regularity {er!r} != class token {tok!r}")
            if esc != EXT_CONCEPT.get(cid):
                self.fail("R06", f"SCC extension_solution_concept {esc!r} != {EXT_CONCEPT.get(cid)!r}")
        else:
            if er is not None or esc is not None:
                self.fail("R06", "WCC must not assert extension_regularity/extension_solution_concept")
        # R31 containment/entailment direction (PROPOSED, W023-F2B-DIR-GUARD-01).
        # R06 certifies that regularity.must_not_conflate is present and non-empty; it does
        # not certify that its sentences agree with this file's own implication_ledger.
        # Measured: an inverted H1/H2 repair clause passes R06 (worker-023 review, worker-080
        # audit).  Fail closed if the predicate module cannot run.
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            import containment_direction_lint as _cdl
            _dirrep = _cdl.scan_document(d)
            for _c in _dirrep.get("claims", []):
                if _c.get("verdict") == "inverted":
                    self.fail("R31", "direction-reversed slot content at %s: required %r, "
                                     "sentence %r [W023F-DIR]" % (_c.get("slot"),
                                                                 _c.get("required_edge"),
                                                                 _c.get("excerpt", "")[:110]))
        except Exception as _e:  # noqa: BLE001 - a broken direction lint must not pass
            self.fail("R31", "containment_direction_lint error: %s" % _e)
        # R07 genericity
        g = d.get("genericity") or {}
        if g.get("kind") not in SPEC_D["vocabularies"]["genericity_kind"]:
            self.fail("R07", f"genericity.kind {g.get('kind')!r} not in vocabulary")
        for k in ("ambient_space", "topology_or_measure", "generic_set", "excluded_set"):
            if not g.get(k):
                self.fail("R07", f"genericity.{k} missing")
        if not g.get("transfer_failures"):
            self.fail("R07", "genericity.transfer_failures empty")
        if g.get("is_part_of_class") is not True:
            self.fail("R07", "genericity.is_part_of_class must be true")
        if not g.get("class_change_warning"):
            self.fail("R07", "genericity.class_change_warning missing")
        # R08 non-vacuity
        nv = d.get("non_vacuity") or {}
        if not nv.get("condition") or not nv.get("witness_type"):
            self.fail("R08", "non_vacuity.condition/witness_type missing")
        # R09 I+
        ip = d.get("i_plus") or {}
        if ip.get("role") not in SPEC_D["vocabularies"]["i_plus_role"]:
            self.fail("R09", f"i_plus.role {ip.get('role')!r} invalid")
        if fam == "WCC":
            if ip.get("role") != "conclusion":
                self.fail("R09", "WCC i_plus.role must be conclusion")
            if not ip.get("completeness_definition"):
                self.fail("R09", "WCC completeness_definition missing")
        else:
            if ip.get("role") != "assumption" or ip.get("in_conclusion") is not False:
                self.fail("R09", "SCC i_plus.role must be assumption with in_conclusion=false")
            leaked = [s for k in ("definition", "required_properties", "completeness_definition")
                      for s in strings_at(ip, (k,))]
            for s in leaked:
                if re.search(r"complete", s, re.I) and not re.search(
                        r"\b(no|not|never|without|cannot|forbidden|absent|refrain)\b", s, re.I):
                    self.fail("R09", "SCC i_plus asserts completeness (negation-aware scan of definition/"
                                     "required_properties/completeness_definition) [R3 n07]")
        # R10 visibility
        v = d.get("visibility") or {}
        if v.get("role") not in SPEC_D["vocabularies"]["visibility_role"]:
            self.fail("R10", f"visibility.role {v.get('role')!r} invalid")
        if fam == "WCC":
            for k in ("predicate_name", "definition", "negation_conclusion"):
                if not v.get(k):
                    self.fail("R10", f"WCC visibility.{k} missing")
        else:
            if v.get("role") != "not_in_conclusion" or not v.get("reason"):
                self.fail("R10", "SCC visibility must be not_in_conclusion with a reason")
            if v.get("visible_singularity_is_wcc") is not True:
                self.fail("R10", "SCC visibility must mark visible singularity as WCC")
        # R11 conclusion
        c = d.get("conclusion") or {}
        if c.get("conclusion_type") != CONC[cid]:
            self.fail("R11", f"conclusion_type {c.get('conclusion_type')!r} != {CONC[cid]!r}")
        if c.get("epistemic_status") not in SPEC_D["vocabularies"]["epistemic_status"]:
            self.fail("R11", "epistemic_status invalid/absent")
        if not c.get("forbidden_strengthenings"):
            self.fail("R11", "forbidden_strengthenings empty")
        if not c.get("statement_formal") or not c.get("statement_natural_language"):
            self.fail("R11", "conclusion statements missing")
        # R12 lexical leakage in assertive content
        for p in ASSERTIVE_PATHS:
            for s in strings_at(d, p):
                for pat in FOREIGN[fam]:
                    if pat == "INEXTENDIB_NON_GEODESIC":
                        if INEXTENDIB.search(s) and not GEODESIC.search(s):
                            self.fail("R12", f"SCC-style inextendibility in {'.'.join(p)}")
                        continue
                    if re.search(pat, s, re.I):
                        self.fail("R12", f"foreign {fam} token /{pat}/ in {'.'.join(p)}")
        # R13 composite regularity anywhere non-exempt
        hits = []
        scan_composite(d, "$", hits)
        for h in hits:
            self.fail("R13", f"composite regularity wording at {h}")
        # R14 falsifier
        f = d.get("falsifier") or {}
        t1, t2 = f.get("tier_1") or {}, f.get("tier_2") or {}
        for name, tier in (("tier_1", t1), ("tier_2", t2)):
            for k in ("refutes", "witness_type"):
                if not tier.get(k):
                    self.fail("R14", f"falsifier.{name}.{k} missing")
        if not t1.get("machine_checkable_steps"):
            self.fail("R14", "falsifier.tier_1.machine_checkable_steps empty")
        if t2.get("labelling_required") != "refutes_strengthening_only":
            self.fail("R14", "falsifier.tier_2 must be labelled refutes_strengthening_only")
        if fam == "WCC" and "visible" not in str(t1.get("witness_type", "")).lower():
            self.fail("R14", "WCC tier_1 witness must be a visible incomplete geodesic")
        if fam == "SCC" and "extension" not in str(t1.get("witness_type", "")).lower():
            self.fail("R14", "SCC tier_1 witness must be an extension witness")
        # R15 provenance
        pr = d.get("provenance") or {}
        if pr.get("citation_status") not in SPEC_D["vocabularies"]["citation_status"]:
            self.fail("R15", "provenance.citation_status invalid/absent")
        if pr.get("citation_status") == "verified":
            srcs = pr.get("sources") or []
            if not srcs or not all(s.get("identifier") for s in srcs):
                self.fail("R15", "citation_status=verified requires identified sources")
        if "unresolved_citations" not in pr:
            self.fail("R15", "provenance.unresolved_citations missing")
        for s in (pr.get("sources") or []):
            blob = json.dumps(s)
            if re.search(r"(establishes|proves|proof of|settles)\s+the\s+(class\s+)?(conclusion|conjecture|statement)", blob, re.I):
                self.fail("R15", "a source is presented as establishing the class conclusion [R3 n08]")
        # R16 SCC implication ledger
        if fam == "SCC":
            il = d.get("implication_ledger") or {}
            owe, ft = il.get("one_way_entailments") or [], il.get("forbidden_transfers") or []
            if not owe or not ft:
                self.fail("R16", "implication_ledger must record one-way entailments and forbidden transfers")
            tok = lambda s: (("C0" if re.search(r"\bC0\b|C\^?0|continuous|continuity", str(s)) else "")
                             + ("C2" if re.search(r"\bC2\b|C\^?2|twice", str(s)) else ""))
            for e in owe:
                if tok(e.get("from", "")) == "C2" and tok(e.get("to", "")) == "C0":
                    self.fail("R16", "one_way_entailments asserts the forbidden converse C2 => C0 [R3 n06]")
            for e in ft:
                if tok(e.get("from", "")) == "C0" and tok(e.get("to", "")) == "C2":
                    self.fail("R16", "forbidden_transfers forbids the required C0 => C2 entailment")
            # prose converse check: worker-08 found a C2-subsumes-C0 sentence in an unscanned field
            fwd = re.compile(r"(C2[^.]{0,100}?)\b(subsumes|implies|entails|establishes|gives|yields)\b"
                             r"([^.]{0,60}(C0|continuity|this class|our class|the class))", re.I)
            rev = re.compile(r"(C0[^.]{0,80}?)\b(follows from|is implied by|is entailed by)\b"
                             r"([^.]{0,50}C2)", re.I)
            neg = re.compile(r"\b(not|never|no|cannot|fails to|does not|do not|must not|may not)\b", re.I)
            for key in ("non_vacuity", "c0_specifics", "regularity", "anti_scope", "implication_ledger"):
                for txt in strings_at(d, (key,)):
                    for m in list(fwd.finditer(txt)) + list(rev.finditer(txt)):
                        if neg.search(m.group(1)):   # negated mention is the REQUIRED phrasing
                            continue
                        self.fail("R16", f"prose converse C2 => C0 asserted inside {key} [worker-08]")
                        break
        # ---------------- R17-R25: semantic-leak family ----------------
        # Added after the re-based corpus measurement (semantic_escape_rebased.json) showed the
        # structural gate escaping 19/32 class-level mutations. Each rule is a class-level
        # invariant, not a corpus-specific string match.
        if fam == "SCC":
            ep = d.get("extension_predicate") or {}
            want = EXT_DEFAULT[cid]
            if ep.get("frozen_direction") != want["direction"]:
                self.fail("R17", f"extension direction {ep.get('frozen_direction')!r} != frozen {want['direction']!r} (two-sided is a different class) [sem09]")
            if ep.get("frozen_regularity") != want["regularity"]:
                self.fail("R18", f"extension_predicate.frozen_regularity {ep.get('frozen_regularity')!r} != class token {want['regularity']!r} (H2_loc is a different class) [sem10]")
            if "frozen_equation_concept" not in ep or ep.get("frozen_equation_concept") != want["concept"]:
                self.fail("R18", f"extension_predicate.frozen_equation_concept must be present and == {want['concept']!r} [struct10]")
        ptr = str(d.get("class_contract_pointer", ""))
        if cid not in ptr:
            self.fail("R19", f"class_contract_pointer does not name this class ({ptr[:70]!r}) [sem11]")
        stmt = strings_at(d, ("conclusion", "statement_natural_language")) + \
               strings_at(d, ("conclusion", "statement_formal"))
        for txt in stmt:
            if re.search(r"\b(we prove|we establish|is proved|is established|theorem)\b", txt, re.I) and \
               not re.search(r"\b(not|never|no|cannot|may not|must not)\b", txt, re.I):
                self.fail("R20", "conclusion statement promotes a theorem without a proof artifact [sem12]")
        g2 = d.get("genericity") or {}
        if g2.get("kind") != FROZEN_GENERICITY and not d.get("class_variant_of_genericity"):
            self.fail("R21", f"genericity.kind {g2.get('kind')!r} != frozen class default {FROZEN_GENERICITY!r} [sem04/sem13]")
        if not re.search(r"(comeager|intersection)", str(g2.get("generic_set", "")), re.I):
            self.fail("R25", "genericity.generic_set is not stated as a countable-intersection comeager set [sem03/sem20]")
        nv2 = d.get("non_vacuity") or {}
        cond = str(nv2.get("condition", ""))
        tautology = re.search(r"\bevery (development|data|datum|spacetime)\b|\balways\b", cond, re.I)
        nontrivial = re.search(r"(incomplete|not future geodesically complete|not a regular|singular|failure of extendibility)", cond, re.I)
        if tautology or not nontrivial:
            self.fail("R23", "non_vacuity.condition is a tautology or does not gate on a non-regular/future-incomplete development [sem15/sem19]")
        wt = str(nv2.get("witness_type", ""))
        if not wt or re.search(r"\b(none|not required|n/?a|trivial|any datum|no witness)\b", wt, re.I):
            self.fail("R24", f"non_vacuity.witness_type is trivial or absent: {wt[:60]!r} [struct09]")
        if KEY_MANIFEST.exists():
            allowed = set(json.loads(KEY_MANIFEST.read_text())["allowed_keys"])
            unknown = set()
            def walk_keys(n, under_ext=False):
                if isinstance(n, dict):
                    for k, v in n.items():
                        if under_ext or k == "extensions":
                            continue
                        if str(k) not in allowed:
                            unknown.add(str(k))
                        walk_keys(v, under_ext)
                elif isinstance(n, list):
                    for v in n:
                        walk_keys(v, under_ext)
            walk_keys(d)
            if unknown:
                self.fail("R22", f"unknown keys (add to KEY_MANIFEST or place under `extensions:`): {sorted(unknown)[:6]} [sem01/02/05/07/14]")
        st = str(t.get("slice_topology", ""))
        if not re.search(r"\bone\b|exactly one", st, re.I) or re.search(r"\btwo\b|multiple ends", st, re.I):
            self.fail("R04", f"slice topology is not declared as exactly one AF end: {st[:70]!r} [struct08]")
        # ---------------- R26-R30: held-out hardening (spec-mandated invariants) ----------------
        # R26: extensions: is an R22 key-allowlist escape hatch ONLY; content rules still apply.
        # (enforced by construction: scan_composite and the string scans do not skip extensions)
        # R27 quantifier order
        qo = (d.get("quantifiers") or {}).get("ordered") or []
        kinds = [e.get("kind") for e in qo if isinstance(e, dict)]
        if kinds and kinds[-1] != "not_exists":
            self.fail("R27", f"last quantifier is {kinds[-1]!r}, expected the negated existence [h26]")
        def idx(pred):
            for i, e in enumerate(qo):
                if isinstance(e, dict) and pred(e): return i
            return None
        ig = idx(lambda e: e.get("binder", "").startswith("G_") or "comeager" in str(e.get("domain_id", "")))
        idata = idx(lambda e: "(Sigma" in str(e.get("binder", "")) or e.get("binder") == "D")
        if ig is None:
            self.fail("R27", "no comeager-set (exists G) quantifier present: an all-data strengthening has been substituted [h15]")
        elif idata is not None and ig > idata:
            self.fail("R27", "the comeager-set quantifier must precede the data quantifier [h26]")
        if fam == "SCC":
            iext = idx(lambda e: e.get("kind") == "not_exists")
            if iext is not None and idata is not None and iext < idata:
                self.fail("R27", "the extension quantifier must follow the data quantifier [h26]")
        # R28 canonical truth table for genericity transfer rows
        TRUTH = {("residual_comeager", "full_measure"): "no_transfer",
                 ("full_measure", "residual_comeager"): "no_transfer",
                 ("residual_comeager", "open_dense_escape"): "no_transfer",
                 ("open_dense_escape", "residual_comeager"): "transfers",
                 ("finite_codimension_complement", "residual_comeager"): "transfers",
                 ("residual_comeager", "finite_codimension_complement"): "no_transfer",
                 ("residual_comeager", "dense_escape"): "transfers",
                 ("dense_escape", "residual_comeager"): "no_transfer"}
        for container in ("transfer_failures", "transfer_holds"):
            for row in (g2.get(container) or []):
                if not isinstance(row, dict): continue
                p = row.get("pair")
                if isinstance(p, list) and len(p) == 2:
                    want = TRUTH.get((str(p[0]), str(p[1])))
                    if want and row.get("direction") != want:
                        self.fail("R28", f"{container} row {p} direction {row.get('direction')!r} contradicts the truth table ({want}) [h08]")
                    if want == "transfers" and container == "transfer_failures":
                        self.fail("R28", f"a 'transfers' row sits in transfer_failures: {p} [R2-17]")
                    if want == "no_transfer" and container == "transfer_holds":
                        self.fail("R28", f"a 'no_transfer' row sits in transfer_holds: {p}")
        # R29 C0 curvature hypotheses (negation-aware)
        if cid == "AF-SCC-C0-VAC-GEN":
            curse = re.compile(r"(Kretschmann|curvature invariant|Ricci scalar|bounded curvature|curvature bound)", re.I)
            negc = re.compile(r"(undefined|unavailable|not |no |never|must not|may not|cannot|forbidden)", re.I)
            def scan_curv(node, path="$", key=None):
                if key is not None and EXEMPT_KEY.match(str(key)): return
                if isinstance(node, dict):
                    for k, v in node.items(): scan_curv(v, f"{path}.{k}", k)
                elif isinstance(node, list):
                    for i, v in enumerate(node): scan_curv(v, f"{path}[{i}]", key)
                elif isinstance(node, str) and curse.search(node) and not negc.search(node):
                    self.fail("R29", f"C0 class carries a curvature-based hypothesis at {path} [h22]")
            scan_curv(d)
        # R30 symmetry consistency
        dcs = []
        def collect(node, key=None):
            if key is not None and EXEMPT_KEY.match(str(key)): return
            if isinstance(node, dict):
                for k, v in node.items(): collect(v, k)
            elif isinstance(node, list):
                for v in node: collect(v, key)
            elif isinstance(node, str): dcs.append(node)
        collect(d.get("data_class"))
        if str((d.get("data_class") or {}).get("symmetry")) == "none_assumed":
            symre = re.compile(r"\b(spherical|axisymmetric|Killing|SO\(3\))\b", re.I)
            negsym = re.compile(r"(not assumed|none assumed|no symmetry|forbidden|not imposed)", re.I)
            for one in dcs:
                if symre.search(one) and not negsym.search(one):
                    self.fail("R30", f"data_class claims none_assumed but states a symmetry restriction: {one[:70]!r} [h14]")
                    break
        # R31 foreign-regularity tokens in assertive prose (h19/h24)
        foreign_reg = {"AF-SCC-C0-VAC-GEN": re.compile(r"\btwice[- ]differentiable\b|\bC\^?2\b|\bH2_loc\b|\bLipschitz\b|\bC\^?\{?1,1\}?\b", re.I),
                       "AF-SCC-C2-VAC-GEN": re.compile(r"\bmerely continuous\b|\bcontinuous metric\b|\bH2_loc\b|\bLipschitz\b", re.I)}
        if cid in foreign_reg:
            # Path-scoped, NOT sentence-negation-scoped: "no extension with a twice-differentiable
            # metric exists" is an ASSERTION of the sibling regularity class, not a negation of it.
            apaths = [("conclusion", "statement_natural_language"), ("conclusion", "statement_formal"),
                      ("scope_statement",), ("falsifier", "tier_1", "witness_type"), ("i_plus", "definition"),
                      ("visibility", "definition"), ("visibility", "negation_conclusion")]
            for ap in apaths:
                for txt in strings_at(d, ap):
                    if foreign_reg[cid].search(txt):
                        self.fail("R31", f"foreign regularity content in {'.'.join(ap)}: {txt[:70]!r} [h19/h24]")
            # extension_predicate subtree, excluding negative/prescriptive keys
            ep_strings = []
            def collect_ep(node, key=None):
                if key is not None and EXEMPT_KEY.match(str(key)): return
                if isinstance(node, dict):
                    for k, v in node.items(): collect_ep(v, k)
                elif isinstance(node, list):
                    for v in node: collect_ep(v, key)
                elif isinstance(node, str): ep_strings.append(node)
            collect_ep(d.get("extension_predicate"))
            for txt in ep_strings:
                if foreign_reg[cid].search(txt):
                    self.fail("R31", f"foreign regularity content in extension_predicate: {txt[:70]!r} [h19]")
        return self.fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("schema")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    p = Path(a.schema)
    if not p.exists():
        print(f"usage: schema not found {p}", file=sys.stderr)
        return 2
    try:
        doc = yaml.safe_load(p.read_text())
    except Exception as e:  # noqa: BLE001 - unparseable input is a structured rejection
        doc = None
    if not isinstance(doc, dict):
        fails = [{"rule": "R01", "msg": "document is empty or not a mapping"}]
    else:
        try:
            fails = Gate(doc, str(p)).run()
        except Exception as e:  # noqa: BLE001 - robustness: never traceback on a malformed schema
            # flash-11's differential matrix found 26/52 fixtures crashing the gate (gate_robustness_crash).
            # A gate that crashes cannot be counted as a rejection; it must return a structured failure.
            fails = [{"rule": "R01", "msg": f"gate exception {type(e).__name__}: {str(e)[:160]} "
                                             f"(structured rejection, not a crash)"}]
    rep = {"schema": str(p), "class_id": (doc or {}).get("class_id") if isinstance(doc, dict) else None,
           "verdict": "pass" if not fails else "fail",
           "failed_rules": sorted({f["rule"] for f in fails}), "failures": fails}
    if a.json:
        print(json.dumps(rep, indent=2))
    else:
        print(f"{rep['verdict'].upper()} {p} class={rep['class_id']} failed_rules={rep['failed_rules']}")
        for f in fails:
            print(f"  {f['rule']}: {f['msg']}")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
