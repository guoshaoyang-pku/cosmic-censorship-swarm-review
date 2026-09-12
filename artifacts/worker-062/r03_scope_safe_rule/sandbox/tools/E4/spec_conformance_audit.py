#!/usr/bin/env python3
"""W06 conformance auditor for FORM-RULE-SPEC 1.0 (canonical formulation rule spec).

Purpose
-------
Give the semantic-fixture corpus a machine-checkable harness. This is NOT the F2 gate:
it is a worker-side auditor that decides the *mechanically decidable* parts of R01-R16
and explicitly reports what it cannot decide. A fixture that this auditor accepts while
carrying a real leak, and whose leak is honestly reported in blindspot_report.json, is
a documented blind spot (per the assign-FORM-LEAK-03 falsifier) -- not a fake pass.

Usage:
  python3 spec_conformance_audit.py SCHEMA [--spec PATH] [--expect-class CLASS] [--json OUT]
  python3 spec_conformance_audit.py --selftest      # audit the semantic fixture corpus

Exit: 0 accept, 1 reject, 2 usage/input error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
DEFAULT_SPEC = ROOT / "artifacts" / "formulation" / "rule_spec.json"
SEMANTIC = HERE / "semantic_fixtures"
CST = timezone(timedelta(hours=8))

VAGUE_WORDS = ["suitable", "appropriate", "reasonable", "sufficiently regular",
               "as needed", "and so on", "etc.", "some topology", "the usual"]
# Foreign-family tokens for the R12 block scan. Deliberately narrow: standard WCC usage
# ("future-inextendible causal geodesic") is NOT SCC content, and explanatory/exclusion
# sub-fields inside a block are exempt per FORM-RULE-SPEC R12 ("occurrences inside
# anti_scope/variants are exempt but must be tagged").
FAMILY_CONCLUSION_TOKENS = {
    "WCC": ["scc_c0_future_inextendibility", "scc_c2_future_inextendibility",
            "proper future c0 metric extension", "proper future c2 metric extension",
            "extendible as a lorentzian manifold", "af-scc-c0-vac-gen", "af-scc-c2-vac-gen"],
    "SCC": ["weak_cosmic_censorship", "asymptotic_predictab", "visible_from_i+",
            "af-wcc-vac-gen", "af-wcc-scalar-sph"],
}
BLOCK_SUBPATH_EXEMPT = ("forbidden", "anti_scope", "anti-scope", "not_", "exclude",
                        "must_not", "schema_falsifier", "contrast", "note", "why", "reason")
COMPOSITE_REGEXES = [
    r"c\s*\^?\s*0\s*(?:or|and|/|,|&)\s*c\s*\^?\s*2",
    r"c\s*\^?\s*2\s*(?:or|and|/|,|&)\s*c\s*\^?\s*0",
    r"c\s*\^?\s*0\s*(?:or|and|/|,|&)\s*2",
    r"c\s*\^?\s*2\s*(?:or|and|/|,|&)\s*0",
]
EXEMPT_PATH_MARKERS = ("anti_scope", "variants", "composite_regularity_lint",
                       "phrases_that_are_not_this_class", "quoted_forbidden_phrase")


def now():
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_text(t):
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def load_yaml(path: Path):
    import yaml
    raw = path.read_text(encoding="utf-8", errors="replace")
    return yaml.safe_load(raw), raw


def walk(x, prefix=""):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from walk(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from walk(v, f"{prefix}[{i}]")
    else:
        yield prefix, x


def leaves(doc):
    return dict(walk(doc))


def sub(doc, path):
    """Fetch a nested path like 'conclusion.falsifier' or 'a[0].b'; raises KeyError."""
    cur = doc
    for part in path.split("."):
        m = re.match(r"^([^\[]+)(?:\[(\d+)\])?$", part)
        if not m:
            raise KeyError(path)
        key, idx = m.group(1), m.group(2)
        cur = cur[key]
        if idx is not None:
            cur = cur[int(idx)]
    return cur


def has(doc, path):
    try:
        sub(doc, path)
        return True
    except (KeyError, IndexError, TypeError):
        return False


def block_text(doc, path):
    try:
        b = sub(doc, path)
    except (KeyError, IndexError, TypeError):
        return ""
    return json.dumps(b, ensure_ascii=False).lower()


class Audit:
    def __init__(self, spec, hardened=False):
        self.spec = spec
        self.results = []
        self.class_family = spec["class_family"]
        self.vocab = spec["vocabularies"]
        self.hardened = hardened

    def fail(self, rule, detail):
        self.results.append({"rule": rule, "verdict": "fail", "detail": detail})

    def ok(self, rule, detail="ok"):
        self.results.append({"rule": rule, "verdict": "pass", "detail": detail})

    def undecided(self, rule, detail):
        self.results.append({"rule": rule, "verdict": "undecided", "detail": detail})

    def run(self, doc, source=None):
        sp = self.spec
        cid = (doc or {}).get("class_id") if isinstance(doc, dict) else None
        family = self.class_family.get(cid)

        # R01 identity block
        req = ["schema_version", "artifact_kind", "class_id", "node_id", "owner", "epistemic_status"]
        miss = [k for k in req if not (isinstance(doc, dict) and doc.get(k))]
        if not isinstance(doc, dict) or miss:
            self.fail("R01", f"missing identity fields: {miss}")
            return self.results
        if doc.get("artifact_kind") != "class_schema":
            self.fail("R01", f"artifact_kind={doc.get('artifact_kind')!r} != class_schema")
        elif cid not in sp["frozen_classes"]:
            self.fail("R01", f"class_id {cid!r} not frozen")
        else:
            self.ok("R01", f"class_id={cid}")

        # R02 components
        comp = doc.get("class_components")
        if not isinstance(comp, dict):
            self.fail("R02", "class_components missing")
        else:
            missing = [k for k in ("asymptotics", "censorship", "matter", "genericity", "regularity_token") if not comp.get(k)]
            tok = comp.get("regularity_token")
            if missing:
                self.fail("R02", f"class_components missing {missing}")
            elif family == "SCC" and tok not in ("C0", "C2"):
                self.fail("R02", f"SCC regularity_token {tok!r} not exactly one of C0/C2")
            elif family == "WCC" and tok not in (None, "", "none"):
                self.fail("R02", f"WCC carries regularity token {tok!r}")
            elif family == "SCC" and tok != cid.split("-")[2]:
                self.fail("R02", f"regularity_token {tok!r} disagrees with class_id {cid}")
            else:
                ptr = str(doc.get("class_contract_pointer", ""))
                if self.hardened and ptr and not ptr.rstrip().endswith(str(cid)):
                    self.fail("R02", f"class_contract_pointer {ptr!r} does not end at class_id {cid!r}")
                else:
                    self.ok("R02", f"token={tok}")

        # R03 quantifiers
        q = doc.get("quantifiers") or {}
        ordered = q.get("ordered")
        if not isinstance(ordered, list) or len(ordered) < 2:
            self.fail("R03", "quantifiers.ordered missing or <2 entries")
        else:
            doms = q.get("domains") or {}
            bad = []
            binders = []
            for i, e in enumerate(ordered):
                if not isinstance(e, dict):
                    bad.append(f"[{i}] not a mapping"); continue
                if e.get("kind") not in ("forall", "exists", "exists_unique", "not_exists"):
                    bad.append(f"[{i}].kind={e.get('kind')!r}")
                for k in ("binder", "domain_id"):
                    if not e.get(k):
                        bad.append(f"[{i}].{k} missing")
                did = e.get("domain_id")
                if did and did not in doms:
                    bad.append(f"[{i}].domain_id={did!r} unresolved")
                if not e.get("domain") and not (isinstance(doms.get(did), dict) and doms[did].get("definition")):
                    bad.append(f"[{i}] has neither .domain nor domains[{did}].definition")
                if e.get("binder"):
                    binders.append(str(e["binder"]))
                d = doms.get(did)
                if isinstance(d, dict):
                    defn = str(d.get("definition", ""))
                    if any(w in defn.lower() for w in VAGUE_WORDS) and not d.get("definition_ref") and not re.search(r"\d", defn):
                        bad.append(f"domain {did} vague without definition_ref/numeric content")
                elif did:
                    bad.append(f"domain {did} not a mapping")
            formal = q.get("formal")
            if not isinstance(formal, str) or not formal.strip():
                bad.append("quantifiers.formal missing")
            else:
                # --- E4 scope-aware binder check (W062 sandbox candidate) ---
                _quant_re = re.compile(r"\b(not\s+exists|exists\s+unique|exists|forall)\b")
                _seg_terms = (" with ", " such that ", " so that ", ":")
                _segs = []
                for _m in _quant_re.finditer(formal):
                    _end = len(formal)
                    for _t in _seg_terms:
                        _j = formal.find(_t, _m.end())
                        if _j != -1:
                            _end = min(_end, _j)
                    _segs.append((_m.group(1).replace(" ", "_"), formal[_m.start():_end]))
                _aligned = len(_segs) == len(binders)
                for _bi, _b in enumerate(binders):
                    if _b in formal:
                        continue
                    _parts = [p.strip() for p in _b.strip("()").split(",") if p.strip()]
                    _ent = ordered[_bi] if _bi < len(ordered) and isinstance(ordered[_bi], dict) else {}
                    if _aligned and _parts and _bi < len(_segs):
                        _kind, _seg = _segs[_bi]
                        if _kind == _ent.get("kind") and all(
                            re.search(r"(?<![A-Za-z0-9_])" + re.escape(p) + r"(?![A-Za-z0-9_])", _seg)
                            for p in _parts
                        ):
                            continue
                    bad.append(f"binder {_b!r} absent from formal sentence (E4 scope-aware)")
            kinds = {e.get("kind") for e in ordered if isinstance(e, dict)}
            if "forall" not in kinds:
                bad.append("no forall quantifier")
            if not ({"exists", "not_exists", "exists_unique"} & kinds):
                bad.append("no existential/negated-existential quantifier")
            if bad:
                self.fail("R03", "; ".join(bad))
            else:
                self.ok("R03", f"{len(ordered)} ordered quantifiers, all domains resolved")

        # R04 topology
        t = doc.get("topology") or {}
        tb = json.dumps(t).lower()
        tbad = []
        if t.get("spacetime_dimension") != 4:
            tbad.append("spacetime_dimension != 4")
        sl = str(t.get("slice_topology", "")).lower()
        for word in ("connected", "complete", "one asymptotically flat end"):
            if word not in sl:
                tbad.append(f"slice_topology lacks {word!r}")
        cb = json.dumps(t.get("conformal_boundary", "")).lower()
        for tok in ("i+", "i-", "i0"):
            if tok not in cb:
                tbad.append(f"conformal_boundary lacks {tok}")
        if "rxs^2" not in str(t.get("I_plus_topology", "")).lower().replace(" ", ""):
            tbad.append("I_plus_topology != R x S^2")
        forb = json.dumps(t.get("forbidden", "")).lower()
        if "closed" not in forb or "periodic" not in forb:
            tbad.append("forbidden does not name closed and periodic slices")
        self._verdict("R04", tbad, "topology complete")

        # R05 data class
        dc = doc.get("data_class") or {}
        dbad = []
        if dc.get("matter") not in ("none", None) or (dc.get("matter") is None and family):
            dbad.append(f"matter={dc.get('matter')!r}")
        if dc.get("cosmological_constant") != 0:
            dbad.append("cosmological_constant != 0")
        cons = dc.get("constraints") or {}
        for k in ("hamiltonian", "momentum"):
            if not cons.get(k):
                dbad.append(f"constraints.{k} missing")
        if not (dc.get("adm_mass") or {}).get("exists"):
            dbad.append("adm_mass.exists not declared")
        decay = json.dumps(dc.get("asymptotic_decay", "")).lower()
        if not re.search(r"o\(r\^?\{?-?\d", decay):
            dbad.append("asymptotic_decay lacks numeric O(r^-k) rates")
        rc = json.dumps(dc.get("regularity_class", "")).lower()
        if not re.search(r"\bs\b|s >", rc) or "delta" not in rc:
            dbad.append("regularity_class lacks named s and delta")
        self._verdict("R05", dbad, "data_class complete")

        # R06 regularity separation
        rg = doc.get("regularity") or {}
        rbad = []
        for k in ("data_regularity", "solution_regularity", "i_plus_regularity",
                  "extension_regularity", "extension_solution_concept"):
            if k not in rg:
                rbad.append(f"regularity.{k} missing")
        if family == "SCC":
            tok = str(rg.get("extension_regularity", "")).strip()
            expect = (doc.get("class_components") or {}).get("regularity_token")
            if tok != expect:
                rbad.append(f"extension_regularity {tok!r} != class token {expect!r}")
        if not rg.get("must_not_conflate"):
            rbad.append("must_not_conflate empty")
        if self.hardened and family == "SCC":
            ep = doc.get("extension_predicate") or {}
            for req_key in ("frozen_regularity", "frozen_equation_concept", "frozen_direction"):
                if not str(ep.get(req_key, "")).strip():
                    rbad.append(f"extension_predicate.{req_key} missing or empty")
            known = {"data_regularity", "solution_regularity", "i_plus_regularity",
                     "extension_regularity", "extension_regularity_exact", "extension_solution_concept"}
            cls_tok = str((doc.get("class_components") or {}).get("regularity_token", ""))
            for k, v in rg.items():
                if k in known or "must_not_conflate" in k:
                    continue
                if re.search(r"c1|c2|c\^1|c\^2|twice|smooth|h2|lipschitz|differentiab", str(v).lower()):
                    rbad.append(f"extra regularity-axis key {k!r} asserts a different differentiability class")
            frozen_reg = str(ep.get("frozen_regularity", ""))
            if frozen_reg and cls_tok and frozen_reg != cls_tok:
                rbad.append(f"extension_predicate.frozen_regularity {frozen_reg!r} != class token {cls_tok!r}")
            dirn = str(ep.get("frozen_direction", ""))
            if dirn and dirn != "future":
                rbad.append(f"extension_predicate.frozen_direction {dirn!r} != future")
            esc, fec = str(rg.get("extension_solution_concept", "")), str(ep.get("frozen_equation_concept", ""))
            if esc and fec and esc != fec:
                rbad.append(f"extension_solution_concept {esc!r} contradicts frozen_equation_concept {fec!r}")
        self._verdict("R06", rbad, "regularity slots separated")

        # R07 genericity
        g = doc.get("genericity") or {}
        gbad = []
        if g.get("kind") not in self.vocab["genericity_kind"]:
            gbad.append(f"kind={g.get('kind')!r} not in vocabulary")
        for k in ("ambient_space", "topology_or_measure", "generic_set", "excluded_set"):
            if not g.get(k):
                gbad.append(f"genericity.{k} missing")
        if not g.get("transfer_failures"):
            gbad.append("transfer_failures empty")
        if g.get("is_part_of_class") is not True:
            gbad.append("is_part_of_class is not true")
        if not g.get("class_change_warning"):
            gbad.append("class_change_warning missing")
        if self.hardened:
            if g.get("kind") == "none":
                if g.get("is_part_of_class") is not False:
                    gbad.append("kind='none' but is_part_of_class is not false")
                qd = doc.get("quantifiers") or {}
                if any(isinstance(e, dict) and e.get("domain_id") == "D1" for e in qd.get("ordered", [])):
                    gbad.append("kind='none' but the formal still fixes a comeager set (D1 binder present)")
            elif g.get("kind") == "residual_comeager":
                gs = str(g.get("generic_set", "")).lower()
                if not any(w in gs for w in ("intersection", "meager", "complement", "comeager", "residual")):
                    gbad.append("kind=residual_comeager but generic_set is not expressed as a comeager/residual condition")
            elif g.get("kind") == "full_measure":
                gs = str(g.get("generic_set", "")).lower()
                if not any(w in gs for w in ("measure", "null")):
                    gbad.append("kind=full_measure but generic_set names no measure condition")
                if any(w in gs for w in ("comeager", "intersection", "meager")):
                    gbad.append("kind=full_measure but generic_set still states a comeager/residual condition (non-transferable)")
        self._verdict("R07", gbad, "genericity specified")

        # R08 non-vacuity
        nv = doc.get("non_vacuity") or {}
        nbad = [k for k in ("condition", "witness_type") if not nv.get(k)]
        if self.hardened:
            wt = str(nv.get("witness_type", "")).strip().lower()
            if wt in ("none", "none required", "n/a", "trivial", "not needed"):
                nbad.append("non_vacuity.witness_type is vacuous")
            cond = str(nv.get("condition", "")).lower()
            vacuous = re.search(r"every development has|trivially true|always satisfied|no condition|any boundary|some future boundary|interesting enough|nonempty", cond)
            marker = any(w in cond for w in ("incomplete", "trapped", "cauchy horizon", "singular",
                                             "not future geodesically complete", "geodesically incomplete",
                                             "boundary that is not", "non-regular", "inextendib"))
            if vacuous or len(cond) < 20:
                nbad.append("non_vacuity.condition is vacuous/trivial")
            elif not marker:
                nbad.append("non_vacuity.condition names no incompleteness/trapped-surface/boundary marker (prose leak)")
            for path, val in walk(doc):
                lp = path.lower()
                if any(x in lp for x in ("must_not_conflate", "forbidden", "anti_scope", "reason", "lint", "note")):
                    continue
                if re.search(r"curvature|kretschmann|weyl|ricci_scalar", lp) and "constraint" not in lp and "equations" not in lp:
                    nbad.append(f"curvature-invariant hypothesis in a C0 class at {path}")
        self._verdict("R08", [f"non_vacuity.{k} missing" if k in ("condition", "witness_type") else k for k in nbad], "non-vacuity declared")

        # R09 i_plus role
        ip = doc.get("i_plus") or {}
        ibad = []
        if ip.get("role") not in self.vocab["i_plus_role"]:
            ibad.append(f"role={ip.get('role')!r} not in vocabulary")
        if family == "SCC":
            if ip.get("in_conclusion") is not False:
                ibad.append("SCC i_plus.in_conclusion is not false")
            if ip.get("completeness_in_conclusion") is True:
                ibad.append("SCC asserts I+ completeness in the conclusion")
        if family == "WCC" and ip.get("role") != "conclusion":
            ibad.append("WCC i_plus.role != conclusion")
        if self.hardened and family == "SCC" and isinstance(ip, dict):
            for k, val in ip.items():
                if k == "forbidden":
                    continue
                vs = str(val).lower()
                if re.search(r"rul(?:e|es) out|used in the conclusion|used to conclude|hence the conclusion|part of the conclusion|drives the conclusion", vs):
                    ibad.append(f"i_plus.{k} imports I+ into the conclusion")
                if "completeness_definition" in k.lower() or (re.search(r"i\+.*(is|be)\s+complete|complete.*conformal", vs) and ip.get("in_conclusion") is not True and "forbidden" not in k.lower()):
                    ibad.append(f"i_plus.{k} asserts I+ completeness while the class excludes it from the conclusion")
        self._verdict("R09", ibad, "I+ role correct for family")

        # R10 visibility role
        v = doc.get("visibility") or {}
        vbad = []
        if v.get("role") not in self.vocab["visibility_role"]:
            vbad.append(f"role={v.get('role')!r} not in vocabulary")
        if family == "SCC":
            if v.get("role") != "not_in_conclusion":
                vbad.append("SCC visibility.role != not_in_conclusion")
            if not v.get("reason"):
                vbad.append("visibility.reason missing")
            if not (v.get("visible_singularity_is_wcc") is True or "wcc" in json.dumps(v).lower()):
                vbad.append("no explicit statement that a visible-singularity falsifier belongs to WCC")
        self._verdict("R10", vbad, "visibility role correct")

        # R11 conclusion typing
        c = doc.get("conclusion") or {}
        cbad = []
        expect_ct = self.vocab["class_conclusion_type"].get(cid)
        if c.get("conclusion_type") != expect_ct:
            cbad.append(f"conclusion_type={c.get('conclusion_type')!r} != vocabulary {expect_ct!r}")
        if c.get("epistemic_status") not in self.vocab["epistemic_status"]:
            cbad.append(f"epistemic_status={c.get('epistemic_status')!r} not in vocabulary")
        if not c.get("forbidden_strengthenings"):
            cbad.append("forbidden_strengthenings empty")
        ctext = json.dumps(c).lower()
        theorem_labelled = (
            c.get("epistemic_status") == "theorem"
            or "theorem" in str(c.get("conclusion_type", "")).lower()
            or bool(re.search(r"\b(prove|proves|proved|establish(?:es|ed)?)\b[^.\n]{0,40}\btheorem\b", ctext))
        )
        if theorem_labelled and not (doc.get("artifact_refs") or c.get("artifact_refs")):
            cbad.append("conclusion labelled theorem without artifact_refs")
        if self.hardened:
            for path, val in walk(c):
                lp = path.lower()
                if any(x in lp for x in ("forbidden", "anti_scope", "must_not", "lint", "note", "claim_promotion")):
                    continue
                if "af-scc-c2-vac-gen" in str(val).lower() or re.search(r"inherit(?:ed|s|ance)?_from|from_sibling|sibling_conclusion", lp):
                    cbad.append(f"conclusion block inherits from the sibling at {path}")
                if re.search(r"twice[- ]differentiab", str(val).lower()):
                    cbad.append(f"conclusion block states a C2-level conclusion at {path}")
        self._verdict("R11", cbad, "conclusion typing correct")

        # R12 lexical leakage over designated blocks only
        lbad = []
        own_type = str((doc.get("conclusion") or {}).get("conclusion_type", "")).lower()
        # dict key = schema family, value = tokens foreign to that family
        foreign = [t for t in FAMILY_CONCLUSION_TOKENS[family]
                   if t not in (str(cid).lower(), own_type)]
        for block in self.spec["leakage_scan_blocks"]:
            try:
                bobj = sub(doc, block)
            except (KeyError, IndexError, TypeError):
                continue
            for path, val in walk(bobj):
                lp = path.lower()
                if any(x in lp for x in BLOCK_SUBPATH_EXEMPT):
                    continue
                for tok in foreign:
                    if tok in str(val).lower():
                        lbad.append(f"{block}.{path} contains foreign-family token {tok!r}")
        if family == "WCC":
            bt = block_text(doc, "i_plus")
            if "completeness" not in bt:
                lbad.append("WCC i_plus block lacks a completeness definition")
        if self.hardened and family == "SCC":
            extra = ["seen by an observer at infinity", "observable from infinity",
                     "seen from infinity", "endpoint at infinity", "visible from infinity"]
            for block in ("conclusion", "falsifier"):
                bt = block_text(doc, block)
                for tok in extra:
                    if tok in bt:
                        lbad.append(f"{block} contains visibility paraphrase {tok!r} in an SCC schema")
        self._verdict("R12", lbad, "no foreign-family token in leakage blocks")

        # R13 composite regularity, respecting exemptions.
        # Gate-design decision (recorded in blindspot_report.json): scan only fields that
        # DECLARE a regularity/class token, not explanatory prose. Scanning all prose produces
        # false positives on legitimate contrasts such as "H2_loc lies between C2 and C0".
        declare_paths = re.compile(r"regularity|class_components|conclusion_type|scope_statement|formal")
        prose_exempt = re.compile(r"must_not_conflate|forbidden|anti_scope|variants|lint|phrases|excluded|reason|why_|note")
        hits = []
        for path, val in walk(doc):
            if any(m in path for m in EXEMPT_PATH_MARKERS) or prose_exempt.search(path):
                continue
            if not declare_paths.search(path):
                continue
            s = str(val).lower()
            for rx in COMPOSITE_REGEXES:
                for m in re.finditer(rx, s):
                    hits.append(f"{path}: {m.group(0)}")
        self._verdict("R13", [f"composite regularity at {h}" for h in hits], "no composite regularity declaration")

        # R14 falsifier
        f = doc.get("falsifier") or {}
        t1 = f.get("tier_1") or {}
        t2 = f.get("tier_2") or {}
        fbad = []
        if t1.get("refutes") != cid:
            fbad.append(f"tier_1.refutes={t1.get('refutes')!r} != {cid}")
        for k in ("witness_type", "genericity_requirement", "machine_checkable_steps"):
            if not t1.get(k):
                fbad.append(f"tier_1.{k} missing")
        if not t2.get("labelling_required"):
            fbad.append("tier_2.labelling_required missing")
        if family == "SCC" and "extension" not in json.dumps(t1).lower():
            fbad.append("SCC tier_1 witness does not mention an extension witness")
        self._verdict("R14", fbad, "falsifier tiered and family-correct")

        # R15 provenance
        p = doc.get("provenance") or {}
        pbad = []
        if p.get("citation_status") not in self.vocab["citation_status"]:
            pbad.append(f"citation_status={p.get('citation_status')!r} not in vocabulary")
        if p.get("citation_status") == "verified":
            srcs = p.get("sources") or []
            if not any(s.get("identifier") and s.get("retrieval_date") for s in srcs if isinstance(s, dict)):
                pbad.append("verified citation without identifier+retrieval_date")
        if not p.get("unresolved_citations"):
            pbad.append("unresolved_citations empty")
        for s in (p.get("sources") or []):
            if isinstance(s, dict) and s.get("establishes_class_conclusion"):
                pbad.append("a source is presented as establishing the class conclusion")
        if self.hardened:
            for s in (p.get("sources") or []) + (p.get("candidate_anchors") or []):
                if not isinstance(s, dict):
                    continue
                stext = " ".join(str(v) for v in s.values()).lower()
                if re.search(r"establish(?:es|ed)?\s+(?:the\s+)?(?:class|conclusion)|proves?\s+(?:the\s+)?(?:class|conclusion)|settles?\s+(?:the\s+)?(?:class|conclusion)|confirms?\s+(?:the\s+)?(?:class|conclusion)", stext):
                    pbad.append("a source entry claims to establish/prove/settle the class conclusion (source overclaim)")
        self._verdict("R15", pbad, "citation status honest")

        # R16 implication ledger (SCC only)
        if family == "SCC":
            il = doc.get("implication_ledger") or {}
            one_way = json.dumps(il.get("one_way_entailments", "")).lower()
            ft = json.dumps(il.get("forbidden_transfers", "")).lower()
            ibad = []
            if "c2" not in one_way or "c0" not in one_way:
                ibad.append("one_way_entailments lacks the C2-subset-C0 statement")
            if "c2" not in ft or "wcc" not in ft:
                ibad.append("forbidden_transfers lacks the C2 converse and/or WCC transfer")
            if not il.get("cross_family"):
                ibad.append("cross_family statement missing")
            if self.hardened:
                for e in (il.get("one_way_entailments") or []):
                    if not isinstance(e, dict):
                        continue
                    frm, to = str(e.get("from", "")).lower(), str(e.get("to", "")).lower()
                    if re.search(r"c2", frm) and re.search(r"c0", to) and "distributional" not in to:
                        ibad.append("one_way_entailments contains the forbidden converse C2 => C0 implication")
                    if re.search(r"wcc|visibility|visible", frm + " " + to):
                        ibad.append("one_way_entailments contains a WCC transfer")
            self._verdict("R16", ibad, "implication ledger present")

        # Undecidable items, always reported
        self.undecided("SEM-1", "non-meagerness of the extendible set (R14 tier_1 non-machine-checkable step)")
        self.undecided("SEM-2", "whether a real 'leak' changes the mathematical class rather than only the wording")
        self.undecided("SEM-3", "truth, non-vacuity and physical correctness of the class (out of scope for any structural gate)")
        return self.results

    def _verdict(self, rule, problems, okdetail):
        if problems:
            self.fail(rule, "; ".join(problems))
        else:
            self.ok(rule, okdetail)


def audit_file(path: Path, spec, expect_class=None, hardened=False):
    doc, raw = load_yaml(path)
    a = Audit(spec, hardened=hardened)
    checks = a.run(doc)
    failed = sorted({c["rule"] for c in checks if c["verdict"] == "fail"})
    undecided = [c["rule"] for c in checks if c["verdict"] == "undecided"]
    verdict = "reject" if failed else "accept"
    if expect_class and isinstance(doc, dict) and doc.get("class_id") != expect_class:
        failed = sorted(set(failed) | {"EXPECT"})
        verdict = "reject"
    return {
        "tool": "worker-06/spec_conformance_audit.py",
        "spec": spec.get("spec_id"),
        "spec_version": spec.get("schema_version"),
        "hardened": hardened,
        "audited_at": now(),
        "source": str(path),
        "doc_sha256": sha256_text(raw),
        "verdict": verdict,
        "failed_rules": failed,
        "undecided_rules": undecided,
        "checks": checks,
    }


def selftest(spec, hardened=False):
    fixtures = sorted(p for p in SEMANTIC.glob("*.yaml") if not p.name.startswith("._"))
    manifest = {}
    mpath = SEMANTIC / "manifest.json"
    if mpath.exists():
        manifest = json.loads(mpath.read_text())
    entries = {e["fixture"]: e for e in manifest.get("fixtures", [])}
    results = []
    caught = missed = 0
    for p in fixtures:
        meta = entries.get(p.name, {})
        rep = audit_file(p, spec, hardened=hardened)
        expected = meta.get("expected_verdict", "reject")
        hit_expected_rule = bool(set(meta.get("expected_rules", [])) & set(rep["failed_rules"]))
        caught_flag = (rep["verdict"] == "reject" and (not meta.get("expected_rules") or hit_expected_rule))
        if expected == "accept":
            caught_flag = rep["verdict"] == "accept"
        results.append({
            "fixture": p.name,
            "leak": meta.get("leak"),
            "expected_verdict": expected,
            "expected_rules": meta.get("expected_rules", []),
            "actual_verdict": rep["verdict"],
            "failed_rules": rep["failed_rules"],
            "caught": caught_flag,
        })
        if expected == "reject":
            caught += 1 if caught_flag else 0
            missed += 0 if caught_flag else 1
    controls = classify_controls(spec, hardened=hardened)
    return {
        "tool": "worker-06/spec_conformance_audit.py --selftest",
        "hardened": hardened,
        "audited_at": now(),
        "fixtures": len(results),
        "leaking_fixtures": sum(1 for r in results if r["expected_verdict"] == "reject"),
        "caught": caught,
        "missed": missed,
        "controls": controls,
        "results": results,
    }


def classify_controls(spec, hardened=False):
    ctl_dir = SEMANTIC / "controls"
    out = []
    if ctl_dir.exists():
        for p in sorted(ctl_dir.glob("*.yaml")):
            rep = audit_file(p, spec, hardened=hardened)
            out.append({"control": p.name, "verdict": rep["verdict"], "failed_rules": rep["failed_rules"]})
    return {"positive_controls": out}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("schema", nargs="?")
    ap.add_argument("--spec", default=str(DEFAULT_SPEC))
    ap.add_argument("--expect-class")
    ap.add_argument("--json")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--hardened", action="store_true",
                    help="enable the repaired rule set proposed in blindspot_report.json")
    a = ap.parse_args(argv)
    spec = json.loads(Path(a.spec).read_text())
    if a.selftest:
        rep = selftest(spec, hardened=a.hardened)
        code = 0 if rep["missed"] == 0 else 1
    else:
        if not a.schema:
            ap.error("provide a schema or --selftest")
        rep = audit_file(Path(a.schema), spec, a.expect_class, hardened=a.hardened)
        code = 0 if rep["verdict"] == "accept" else 1
    text = json.dumps(rep, indent=2, ensure_ascii=False)
    if a.json:
        Path(a.json).write_text(text + "\n")
    print(text if not a.json else json.dumps({k: v for k, v in rep.items() if k != "checks"}))
    return code


if __name__ == "__main__":
    sys.exit(main())
