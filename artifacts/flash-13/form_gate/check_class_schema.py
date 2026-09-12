#!/usr/bin/env python3
"""FORM-GATE-01: canonical executable class-schema gate, parameterised per class.

Assignment : assign-FORM-GATE-01-20260911T2331 (lead-formulation)
Node/gate  : F1 / G-CLASSBIND (also intended for F2a, F2b)
Spec       : artifacts/formulation/rule_spec.json  (FORM-RULE-SPEC v1.0, R01-R16)
Deliverable: artifacts/flash-13/form_gate/check_class_schema.py  (primary implementation)

INDEPENDENCE (acceptance G5)
  This file was written from FORM-RULE-SPEC v1.0 only. It does not import, shell out to, or copy
  any other worker's gate or fixture. It has no third-party dependency beyond PyYAML.

WHAT IT DECIDES
  Structure only: does a class schema carry the fields the spec requires, with the family-specific
  roles the spec pins (WCC: I+ role=conclusion, visibility role=conclusion; SCC: I+ not in the
  conclusion, visibility cross-referenced to WCC, extension regularity exactly the class token).
  It never decides physical truth, never promotes a theorem, and never judges a citation.

CLI
  python3 check_class_schema.py SCHEMA [--class CLASS] [--json-out PATH]
  python3 check_class_schema.py --canonical [--canonical-dir DIR] [--json-out PATH]
  exit 0 = all rules pass; 1 = >=1 rule failure; 2 = usage/parse error;
  3 = canonical schema absent (explicitly NOT a pass)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

SPEC_ID = "FORM-RULE-SPEC"
SPEC_VERSION = "1.2"
GATE_ID = "FORM-GATE-01"
GATE_VERSION = "1.3"

#: revision 1.3 (2026-09-12): R03 becomes a *realization* test with two reported readings.
#: R03's published require is "quantifiers.formal is a single sentence using those binders".
#: Revision 1.2 implemented that as a whitespace-normalised literal-substring test and thereby
#: rejected the frozen rev13 canonical WCC exemplar d9cebb9404b2, whose ordered[5] declares the
#: tuple binder "(q,t0)" and whose formal sentence realises that single pair-choice variable-wise
#: ("not exists q in I+ and t0 in [0,T)").  Rejecting a schema the assignment names as a conforming
#: exemplar is a false positive of the test, not a defect of the exemplar: both declared variables
#: occur, bound after their quantifier.  Revision 1.3 therefore measures two readings and reports
#: both in every result (`r03_readings`):
#:   L (literal)  : the declared binder string occurs verbatim.  Preserved, not the pass criterion.
#:   S (semantic) : (a) the quantifier-keyword sequence of quantifiers.formal equals the `kind`
#:                  sequence of quantifiers.ordered, in order; (b) every variable named in every
#:                  declared binder occurs, whole-word, at or after its own quantifier keyword.
#: S is strictly stronger than L on scope errors and strictly more precise on tuple binders:
#: the R03 controls in fixtures_r03/ include mutants that L accepts and S rejects (kind reorder;
#: quantifier clause deleted while its variables remain in the body) and mutants both reject
#: (declared tuple variable never used -- the m25 case -- and all variables replaced by
#: placeholders while the keyword sequence is preserved).  The pass criterion is S; L is reported
#: so an owner who rules that the spec means literal occurrence can see the exact delta and
#: require the worker-064 E1a/E1b one-clause repair, which S also accepts.
#: This does not touch canonical bytes, does not set a gate verdict, and does not overrule the
#: `astra-life05-verify-gform-r3` / rule-owner adjudication recorded in the map.

#: revision 1.2 (2026-09-12): R03 declared-binder usage.  The published R03 require is that
#: quantifiers.formal is "a single sentence using those binders"; revision 1.1 only required the
#: formal sentence to contain *some* quantifier, so a declared tuple binder rendered variable-wise
#: escaped.  This was caught by the rev13 canonical WCC bytes d9cebb9404b2 (ordered[5] declares
#: "(q,t0)", formal renders "not exists q in I+ and t0 in [0,T) with ..."), independently of this
#: worker by the adopted semantic auditor (worker-064 W064-R03-CAUSE-01, auditor c79d8ab8440a).
#: The added test is a whitespace-normalised literal-usage test and is disclosed as such: it can
#: false-positive on a semantically equivalent alpha-renaming of a declared binder, and it is the
#: spec's literal wording that makes that a finding for adjudication rather than a silent pass.
#: Unchanged for every conforming fixture and every mutant whose binders occur literally.

#: revision 1.1 (2026-09-12): escape triage against the worker-06 frozen-base semantic corpus
#: (32 mutants; manifest sha256 c102445df3971109101e4d54b609ff1c5bfdf9147ddb1f1b099476a816030deb)
#: showed 13/32 caught at gate 8130652042b47952. The additions below close the in-scope escapes
#: that are derivable from the published rule text (R02/R06/R07/R08/R11/R12/R14/R15/R16) without
#: importing or copying any other implementation: unknown-key smuggling under regularity and
#: non_vacuity, foreign class_contract_pointer / inherited sibling conclusion, genericity kind
#: that the schema itself marks no-transfer, generic_set form, condition/witness substance,
#: extension_predicate equation/regularity/direction/solution-concept consistency, one-sided
#: extension direction, falsifier witness text (not the class-id token in `refutes`), source
#: overclaim phrasing, and an asserted C2=>C0 converse. Records `gate_revision` in every report.

FROZEN_CLASSES = {
    "AF-WCC-VAC-GEN": {
        "family": "WCC", "matter": "vacuum", "regularity_token": None,
        "conclusion_type": "weak_cosmic_censorship", "extension_solution_concept": None,
        "genericity_kind": "residual_comeager",
    },
    "AF-SCC-C2-VAC-GEN": {
        "family": "SCC", "matter": "vacuum", "regularity_token": "C2",
        "conclusion_type": "scc_c2_future_inextendibility",
        "extension_solution_concept": "classical_ricci",
        "genericity_kind": "residual_comeager",
    },
    "AF-SCC-C0-VAC-GEN": {
        "family": "SCC", "matter": "vacuum", "regularity_token": "C0",
        "conclusion_type": "scc_c0_future_inextendibility",
        "extension_solution_concept": "none",
        "genericity_kind": "residual_comeager",
    },
    "AF-WCC-SCALAR-SPH": {
        "family": "WCC", "matter": "scalar", "regularity_token": None,
        "conclusion_type": "weak_cosmic_censorship", "extension_solution_concept": None,
        "genericity_kind": None,
    },
}

#: revision 1.1 support sets -------------------------------------------------
REGULARITY_KNOWN_KEYS = {
    "data_regularity", "solution_regularity", "i_plus_regularity", "extension_regularity",
    "extension_regularity_exact", "extension_solution_concept", "must_not_conflate",
    "existence_theorem",
}
NON_VACUITY_KNOWN_KEYS = {
    "condition", "witness_type", "status", "vacuity_falsifier", "iota_regularity",
    "c0_specific_note", "c2_specific_note", "c2_vacuity_argument_status", "notes", "note",
}
SMUGGLE_MARKERS = ("assum", "hypothes", "smooth", "differentiab", "twice", "sobolev",
                   "curvature", "bounded", "require")
WITNESS_NAMING = ("family", "witness", "data", "development", "set", "geodesic",
                  "surface", "extension")
NULLISH = re.compile(r"^\s*(none|none required|n/?a|not required|no witness( required)?|"
                     r"optional|tbd|missing)\b", re.IGNORECASE)
THEOREM_PROMOTION = re.compile(r"\b(we prove|we establish|proved|theorem|q\.?e\.?d)\b",
                               re.IGNORECASE)
OVERCLAIM_RE = re.compile(
    r"(establish\w*[^.]{0,60}conclusion|prove[sd]?[^.]{0,40}conclusion|"
    r"rules? out[^.]{0,40}(extension|conclusion|theorem)|"
    r"evidence (that|for)[^.]{0,40}conclusion)", re.IGNORECASE)
CITE_USE_RE = re.compile(
    r"(establish|prove[sd]?|rules? out|settle[sd]?|evidence (that|for)|confirms?)",
    re.IGNORECASE)
#: sibling-class id that must not appear inside another class's conclusion/visibility/i_plus/falsifier
SIBLING_CLASS = {
    "AF-SCC-C0-VAC-GEN": "af-scc-c2-vac-gen",
    "AF-SCC-C2-VAC-GEN": "af-scc-c0-vac-gen",
}

EPISTEMIC = {"open_problem", "formal_model", "conditional_theorem"}
GENERICITY_KINDS = {
    "residual_comeager", "full_measure", "open_dense_escape",
    "finite_codimension_complement", "none",
}
I_PLUS_ROLES = {"assumption", "conclusion"}
VISIBILITY_ROLES = {"conclusion", "not_in_conclusion"}
CITATION_STATUS = {"unverified", "unresolved", "verified"}
QUANTIFIER_KINDS = {"forall", "exists", "exists_unique", "not_exists"}
SCAN_BLOCKS = ("conclusion", "visibility", "i_plus", "falsifier")
EXEMPT_KEYS = ("anti_scope", "variants", "forbidden_phrases", "exemptions")
PROHIBITION_MARKERS = ("forbidden", "must_not", "not_conflate", "anti_scope", "variants", "exempt")
EXEMPT_PATH_MARKERS = PROHIBITION_MARKERS + ("schema_falsifier",)
NEGATION_MARKERS = ("not", "no ", "never", "forbidden", "absent", "false", "without", "nowhere")

SCC_TOKENS = [
    # "inextendib" as a bare stem is deliberately NOT used: "future-inextendible null
    # generators of I+" (WCC completeness) and "future-inextendible causal geodesic"
    # (visible-singularity definition) are legitimate WCC language and were false positives.
    # Only spacetime/development-level occurrences are SCC leakage.
    "future-inextendibility of the maximal development",
    "spacetime is future-inextendible", "maximal development is future-inextendible",
    "spacetime is inextendible", "maximal development is inextendible",
    "inextendibility of the maximal development",
    "cauchy horizon", "mass inflation", "blue-shift", "blueshift",
    "strong cosmic censorship", "c^2-inextend", "c^0-inextend", "c2-inextend", "c0-inextend",
]
WCC_TOKENS = [
    "naked singularity", "nakedly singular", "visible incomplete", "visible singularity",
    "i+ is complete", "future null infinity is complete", "asymptotic predictability",
]
MATTER_TOKENS = [
    "scalar field", "klein-gordon", "maxwell", "electromagnetic", "perfect fluid",
    "stress-energy",
]
ASYMPTOTIC_TOKENS = [
    "closed universe", "compact without boundary", "periodic boundary", "de sitter",
    "kaluza-klein",
]
VAGUE_WORDS = [
    "suitable", "appropriate", "reasonable", "nice", "well-behaved", "sufficiently",
    "as needed", "generic enough", "small enough",
]
COMPOSITE_REGEX = re.compile(
    r"(C0|C2|C[\s-]?(two|zero))\s*(or|and|/)\s*(C0|C2|C[\s-]?(two|zero))", re.IGNORECASE)

CANONICAL = {
    "AF-WCC-VAC-GEN": "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
    "AF-SCC-C2-VAC-GEN": "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
    "AF-SCC-C0-VAC-GEN": "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
}
#: pre-freeze locations accepted as a fallback when the frozen tree is not present
CANONICAL_FALLBACK = {
    "AF-WCC-VAC-GEN": "schemas/af_wcc_vacuum.yaml",
    "AF-SCC-C2-VAC-GEN": "schemas/af_scc_c2_vacuum.yaml",
    "AF-SCC-C0-VAC-GEN": "schemas/af_scc_c0_vacuum.yaml",
}
FROZEN_MANIFEST = "artifacts/formulation/FROZEN.json"
ALIASES_PATH = Path(__file__).resolve().parents[3] / "artifacts" / "formulation" / "VOCAB_ALIASES.json"


def _load_aliases():
    """Load the lead-published VOCAB_ALIASES.json (canonical token first)."""
    try:
        data = json.loads(ALIASES_PATH.read_text())
    except Exception:
        return {}, {}
    def invert(block):
        out = {}
        for canonical, alts in (block or {}).items():
            for a in alts or []:
                out[str(a)] = canonical
        return out
    return invert(data.get("genericity_kind", {})), invert(data.get("conclusion_type", {}))


GENERICITY_ALIASES, CONCLUSION_ALIASES = _load_aliases()

#: spec-named top-level key -> older synonym observed in the repo. Purely diagnostic:
#: the rules stay strict about the published names, but the report names the likely alias
#: so a schema owner can see that a revision, not a rewrite, is what is required.
SYNONYMS = {
    "artifact_kind": "artifact_type",
    "owner": "owner_of_record",
    "class_components": "class_boundary",
    "quantifiers": "exact_quantifiers",
    "regularity": "metric_regularity",
    "i_plus": "future_null_infinity",
}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def get(doc, path, default=None):
    cur = doc
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return default
    return cur


def text_of(value):
    return value.strip() if isinstance(value, str) else ""


def iter_strings(obj, path="$"):
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from iter_strings(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from iter_strings(v, f"{path}[{i}]")


def contains_any(s, words):
    low = s.lower()
    return any(w in low for w in words)


def has_numeric_rate(s):
    return bool(re.search(r"\^?-?\d", s)) and bool(re.search(r"r\s*\^?\s*-?\d|O\(r", s, re.I))


def strip_exempt(obj):
    if isinstance(obj, dict):
        return {k: strip_exempt(v) for k, v in obj.items() if k not in ("variants", "anti_scope")}
    if isinstance(obj, list):
        return [strip_exempt(v) for v in obj]
    return obj


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# -- R03 readings (revision 1.3) ----------------------------------------------------------------
#: Keyword forms accepted in quantifiers.formal, longest first so "not exists" never degrades
#: to a bare "exists".  Only these explicit forms are counted; prose universal words such as
#: "every" inside the body (e.g. "every null geodesic generator of I+") are deliberately not
#: quantifier-prefix keywords and must not shift the sequence.
R03_KEYWORD_RE = re.compile(
    r"(?<![A-Za-z0-9_])(not\s+exists|exists\s+unique|unique\s+exists|there\s+exists|"
    r"forall|for\s+all|exists)(?![A-Za-z0-9_])")
R03_KEYWORD_KIND = {
    "not exists": "not_exists", "exists unique": "exists_unique", "unique exists": "exists_unique",
    "there exists": "exists", "forall": "forall", "for all": "forall", "exists": "exists",
}
R03_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_']*")


def r03_normalise(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def r03_declared_variables(binder: str):
    """Variables named by a declared binder: '(q,t0)' -> ['q','t0']; 'G_r' -> ['G_r']."""
    return R03_IDENT_RE.findall(binder or "")


def r03_keyword_sequence(formal: str):
    return [(m.group(0).replace("  ", " ").lower(), R03_KEYWORD_KIND[m.group(0).replace("  ", " ").lower()], m.start())
            for m in R03_KEYWORD_RE.finditer(formal or "")]


def r03_occurs(formal: str, var: str) -> bool:
    return re.search(rf"(?<![A-Za-z0-9_]){re.escape(var)}(?![A-Za-z0-9_])", formal or "") is not None


def r03_occurs_at_or_after(formal: str, var: str, pos: int) -> bool:
    return re.search(rf"(?<![A-Za-z0-9_]){re.escape(var)}(?![A-Za-z0-9_])", (formal or "")[pos:]) is not None


def r03_readings(ordered, formal):
    """Measure both disclosed readings of R03.  Pure function; no rule findings are raised here.

    Returns {"literal": {...}, "semantic": {...}, "kind_sequence": [...]}.
    """
    ordered = [it for it in ordered if isinstance(it, dict)] if isinstance(ordered, list) else []
    formal_norm = re.sub(r"\s+", "", r03_normalise(formal))
    literal_unused = []
    for i, item in enumerate(ordered):
        binder = text_of(item.get("binder"))
        if binder and re.sub(r"\s+", "", binder) not in formal_norm:
            literal_unused.append({"index": i, "binder": binder})
    literal = {"pass": not literal_unused, "unused": literal_unused}

    seq = r03_keyword_sequence(r03_normalise(formal))
    kinds_found = [k for (_kw, k, _pos) in seq]
    kinds_declared = [str(it.get("kind")) for it in ordered]
    kind_ok = kinds_found == kinds_declared
    missing_vars, unbound_vars = [], []
    if kind_ok:
        for i, item in enumerate(ordered):
            _kw, _kind, pos = seq[i]
            for var in r03_declared_variables(text_of(item.get("binder"))):
                if not r03_occurs(r03_normalise(formal), var):
                    missing_vars.append({"index": i, "binder": text_of(item.get("binder")), "variable": var})
                elif not r03_occurs_at_or_after(r03_normalise(formal), var, pos):
                    unbound_vars.append({"index": i, "binder": text_of(item.get("binder")), "variable": var})
    semantic = {
        "pass": kind_ok and not missing_vars and not unbound_vars,
        "kind_sequence_declared": kinds_declared,
        "kind_sequence_found": kinds_found,
        "kind_sequence_match": kind_ok,
        "missing_variables": missing_vars,
        "unbound_variables": unbound_vars,
    }
    return {"literal": literal, "semantic": semantic, "kind_sequence": kinds_found}


class Gate:
    def __init__(self, class_id: str, doc: dict, source: str, r03_mode: str = "semantic"):
        self.class_id = class_id
        self.spec = FROZEN_CLASSES[class_id]
        self.doc = doc if isinstance(doc, dict) else {}
        self.source = source
        self.r03_mode = r03_mode if r03_mode in ("semantic", "literal") else "semantic"
        self.r03_readings = None
        self.findings = {r: [] for r in self.rule_ids()}
        self.checked = []
        self.exempted = []
        self.alias_uses = []

    @staticmethod
    def rule_ids():
        return [f"R{i:02d}" for i in range(1, 17)]

    def fail(self, rule, path, detail):
        self.findings[rule].append({"path": path, "detail": detail})

    def ok(self, rule):
        return not self.findings[rule]

    # -- individual rules ---------------------------------------------------
    def r01_identity(self):
        d = self.doc
        for key in ("schema_version", "class_id", "node_id", "owner", "epistemic_status"):
            if not text_of(d.get(key)):
                self.fail("R01", key, f"missing identity field {key}")
        if d.get("artifact_kind") != "class_schema":
            self.fail("R01", "artifact_kind", "artifact_kind must be 'class_schema'")
        if text_of(d.get("class_id")) and d.get("class_id") not in FROZEN_CLASSES:
            self.fail("R01", "class_id", f"class_id {d.get('class_id')!r} not in frozen classes")

    def r02_class_components(self):
        comp = get(self.doc, "class_components")
        if not isinstance(comp, dict):
            self.fail("R02", "class_components", "class_components missing/not a mapping")
            return
        expected_tokens = self.class_id.split("-")
        tokens = comp.get("tokens")
        if isinstance(tokens, list):
            if [str(t) for t in tokens] != expected_tokens:
                self.fail("R02", "class_components.tokens",
                          f"tokens {tokens!r} != token-wise decomposition {expected_tokens!r}")
        else:
            # spec says "decomposes class_id token-wise"; the axes form used by the C0
            # canonical schema maps one axis per class-id token and is accepted as such.
            axes = {"asymptotics": "AF", "censorship": None, "matter": "VAC",
                    "genericity": "GEN", "regularity_token": self.spec["regularity_token"]}
            axes["censorship"] = self.spec["family"]
            problems = []
            for key, want in axes.items():
                got = comp.get(key)
                if got is None:
                    problems.append(f"{key} missing")
                elif want is not None and str(got) != want:
                    problems.append(f"{key}={got!r} != {want!r}")
            if problems:
                self.fail("R02", "class_components",
                          "no token list and axes decomposition invalid: " + "; ".join(problems))
        fam = str(comp.get("family", comp.get("censorship", ""))).upper()
        if fam != self.spec["family"]:
            self.fail("R02", "class_components.family",
                      f"family {fam!r} != {self.spec['family']}")
        matter = str(comp.get("matter_model", comp.get("matter", ""))).lower()
        want = self.spec["matter"]
        if (want == "vacuum" and matter not in {"vacuum", "none", "none (vacuum)", "vac"}) or \
           (want == "scalar" and "scalar" not in matter):
            self.fail("R02", "class_components.matter_model",
                      f"matter_model {matter!r} inconsistent with class")
        tok = comp.get("regularity_token")
        count = comp.get("regularity_token_count")
        if self.spec["regularity_token"] is None:
            if str(tok).strip().lower() not in {"none", "null", ""} or count not in (0, None):
                self.fail("R02", "class_components.regularity_token",
                          "WCC class must carry no regularity token (use 'none' or null)")
        else:
            if str(tok) != self.spec["regularity_token"]:
                self.fail("R02", "class_components.regularity_token",
                          f"SCC class requires token {self.spec['regularity_token']}, got {tok!r}")
            if count not in (1, None):
                self.fail("R02", "class_components.regularity_token_count",
                          f"SCC class requires exactly one regularity token, got {count!r}")
        # revision 1.1: a class-contract pointer is part of class binding; it may not point at
        # a sibling class's contract (escape sem11, worker-06 corpus).
        ptr = text_of(self.doc.get("class_contract_pointer"))
        if ptr:
            for cid in re.findall(r"AF-[A-Za-z0-9-]+", ptr):
                if cid != self.class_id:
                    self.fail("R02", "class_contract_pointer",
                              f"contract pointer names foreign class {cid!r}, not {self.class_id!r}")

    def r03_quantifiers(self):
        q = get(self.doc, "quantifiers")
        if not isinstance(q, dict):
            self.fail("R03", "quantifiers", "quantifiers missing/not a mapping")
            return
        ordered = q.get("ordered")
        if not isinstance(ordered, list) or not ordered:
            self.fail("R03", "quantifiers.ordered", "ordered quantifier list missing/empty")
        else:
            for i, item in enumerate(ordered):
                p = f"quantifiers.ordered[{i}]"
                if not isinstance(item, dict):
                    self.fail("R03", p, "quantifier entry is not a mapping")
                    continue
                if str(item.get("kind", "")) not in QUANTIFIER_KINDS:
                    self.fail("R03", f"{p}.kind", f"kind {item.get('kind')!r} invalid")
                for key in ("binder", "domain_id"):
                    if not text_of(item.get(key)):
                        self.fail("R03", f"{p}.{key}", f"{key} missing/empty")
                # the spec's own fail condition is an unresolved domain_id or a vague domain;
                # a redundant per-quantifier `domain` string is optional when domain_id resolves
                if not text_of(item.get("domain")) and not text_of(item.get("domain_id")):
                    self.fail("R03", f"{p}.domain", "neither domain nor domain_id is present")
        formal = text_of(q.get("formal"))
        if not formal:
            self.fail("R03", "quantifiers.formal", "formal statement missing/empty")
        elif not contains_any(formal, ["forall", "exists", "not_exists", "for all", "there exists"]):
            self.fail("R03", "quantifiers.formal", "formal statement has no quantifier")
        else:
            # revision 1.3: measure both readings of "a single sentence using those binders" and
            # report both; the pass criterion is the semantic realization reading (see header).
            # `--r03-mode literal` reproduces revision 1.2's literal-substring criterion exactly
            # (audit mode for the delta), and still reports the semantic reading.
            readings = r03_readings(ordered if isinstance(ordered, list) else [], formal)
            self.r03_readings = readings
            if self.r03_mode == "literal":
                for lit in readings["literal"]["unused"]:
                    self.fail("R03", f"quantifiers.ordered[{lit['index']}].binder",
                              f"declared binder {lit['binder']!r} does not occur in "
                              "quantifiers.formal (literal-usage test, revision 1.3 audit mode)")
            else:
                if not readings["semantic"]["kind_sequence_match"]:
                    self.fail("R03", "quantifiers.formal",
                              "quantifier-keyword sequence "
                              f"{readings['semantic']['kind_sequence_found']} != declared ordered kinds "
                              f"{readings['semantic']['kind_sequence_declared']} "
                              "(semantic realization test, revision 1.3)")
                for miss in readings["semantic"]["missing_variables"]:
                    self.fail("R03", f"quantifiers.ordered[{miss['index']}].binder",
                              f"declared binder {miss['binder']!r} variable {miss['variable']!r} "
                              "never occurs in quantifiers.formal (semantic realization test, "
                              "revision 1.3)")
                for unb in readings["semantic"]["unbound_variables"]:
                    self.fail("R03", f"quantifiers.ordered[{unb['index']}].binder",
                              f"declared binder {unb['binder']!r} variable {unb['variable']!r} occurs "
                              "only before its quantifier keyword (semantic realization test, "
                              "revision 1.3)")
        domains = q.get("domains")
        if not isinstance(domains, dict) or not domains:
            self.fail("R03", "quantifiers.domains", "domains mapping missing/empty")
            return
        used = {str(it.get("domain_id")) for it in ordered if isinstance(it, dict)}
        for did in sorted(used):
            if did not in domains:
                self.fail("R03", f"quantifiers.domains.{did}", f"domain_id {did!r} unresolved")
                continue
            entry = domains[did]
            definition = text_of(get(entry, "definition", ""))
            if not definition:
                self.fail("R03", f"quantifiers.domains.{did}.definition", "domain definition missing")
                continue
            if contains_any(definition, VAGUE_WORDS):
                has_ref = bool(text_of(get(entry, "definition_ref", "")))
                has_number = any(ch.isdigit() for ch in definition)
                if not (has_ref or has_number):
                    self.fail("R03", f"quantifiers.domains.{did}.definition",
                              "vague domain with neither definition_ref nor numeric content")

    def r04_topology(self):
        t = get(self.doc, "topology")
        if not isinstance(t, dict):
            self.fail("R04", "topology", "topology missing/not a mapping")
            return
        if t.get("spacetime_dimension") != 4:
            self.fail("R04", "topology.spacetime_dimension",
                      f"spacetime_dimension {t.get('spacetime_dimension')!r} != 4")
        slice_s = text_of(t.get("slice_topology")).lower()
        for need, label in (("connected", "connected"), ("complete", "complete"),
                            ("asymptotically flat", "asymptotically flat")):
            if need not in slice_s:
                self.fail("R04", "topology.slice_topology", f"slice_topology does not declare {label}")
        if not contains_any(slice_s + " " + text_of(t.get("end_structure")).lower(),
                            ["one-ended", "one end", "exactly one", "single end"]):
            self.fail("R04", "topology.slice_topology", "slice_topology does not declare one end")
        cb = t.get("conformal_boundary")
        iplus = ""
        if isinstance(cb, dict):
            for need in ("i_plus", "i_minus", "i0"):
                if not any(need in k.lower().replace("+", "_plus").replace("-", "_minus") for k in cb):
                    self.fail("R04", "topology.conformal_boundary", f"missing {need}")
            key = next((k for k in cb if "i_plus" in k.lower() or k.lower() == "i+"), None)
            iplus = text_of(cb.get(key, "")) if key else ""
        elif isinstance(cb, list):
            joined = " ".join(str(x) for x in cb).lower()
            for need, label in (("i+", "I+"), ("i-", "I-"), ("i0", "i0")):
                if need not in joined:
                    self.fail("R04", "topology.conformal_boundary", f"missing {label}")
            iplus = next((str(x) for x in cb if "i+" in str(x).lower()), "")
        else:
            self.fail("R04", "topology.conformal_boundary", "conformal_boundary missing")
        iplus = iplus or ""
        separate = text_of(t.get("I_plus_topology")) or text_of(t.get("i_plus_topology"))
        combined = (iplus + " " + separate).strip()
        if not combined or not re.search(r"R\s*[x×]\s*S\^?2", combined, re.I):
            self.fail("R04", "topology.conformal_boundary",
                      "I+ topology is not declared as R x S^2")
        forb = t.get("forbidden")
        if not isinstance(forb, list) or not forb or not contains_any(" ".join(map(str, forb)),
                                                                      ["closed", "periodic"]):
            self.fail("R04", "topology.forbidden",
                      "closed/periodic slices are not explicitly forbidden")

    def r05_data_class(self):
        dc = get(self.doc, "data_class")
        if not isinstance(dc, dict):
            self.fail("R05", "data_class", "data_class missing/not a mapping")
            return
        matter = str(dc.get("matter", "")).lower()
        if self.spec["matter"] == "vacuum" and not contains_any(matter, ["vacuum", "none"]):
            self.fail("R05", "data_class.matter", f"matter {dc.get('matter')!r} is not vacuum/none")
        if self.spec["matter"] == "scalar" and "scalar" not in matter:
            self.fail("R05", "data_class.matter", f"matter {dc.get('matter')!r} is not scalar")
        cc = dc.get("cosmological_constant")
        if str(cc) not in {"0", "0.0"}:
            self.fail("R05", "data_class.cosmological_constant",
                      f"cosmological_constant {cc!r} != 0 for an AF class")
        cons = dc.get("constraints")
        if not isinstance(cons, dict) or not text_of(cons.get("hamiltonian")) or \
           not text_of(cons.get("momentum")):
            self.fail("R05", "data_class.constraints",
                      "Hamiltonian and momentum constraints must both be named")
        adm = dc.get("adm_mass_status")
        if adm is None:
            adm = dc.get("adm_mass")
        if adm is None or (isinstance(adm, str) and not adm.strip()):
            self.fail("R05", "data_class.adm_mass_status", "ADM mass status missing")
        decay = dc.get("asymptotic_decay")
        if not isinstance(decay, dict) or not decay:
            self.fail("R05", "data_class.asymptotic_decay", "asymptotic_decay missing")
        else:
            rates = [s for _, s in iter_strings(decay)]
            if not any(has_numeric_rate(s) for s in rates):
                self.fail("R05", "data_class.asymptotic_decay",
                          "no numeric decay rate per derivative order")
        s = get(dc, "sobolev_index.s", get(dc, "regularity_class.sobolev_variant.s"))
        delta = get(dc, "weight.delta", get(dc, "regularity_class.sobolev_variant.delta"))
        smooth_class = contains_any(
            text_of(dc.get("regularity")) + text_of(dc.get("weighted_norm")) +
            text_of(get(dc, "regularity_class.default", "")) +
            text_of(get(dc, "regularity_class.name", "")),
            ["smooth", "c^inf", "cinf"])
        if not ((s is not None and str(s).strip()) and delta) and not (
                smooth_class and rates):
            self.fail("R05", "data_class.sobolev_index",
                      "neither (named Sobolev index s + weight delta) nor explicit smooth-with-decay class")

    def r06_regularity(self):
        reg = get(self.doc, "regularity")
        if not isinstance(reg, dict):
            self.fail("R06", "regularity", "regularity missing/not a mapping")
            return
        for key in ("data_regularity", "solution_regularity", "i_plus_regularity",
                    "extension_regularity", "extension_solution_concept"):
            if key not in reg:
                self.fail("R06", f"regularity.{key}", f"regularity slot {key} missing")
        mnc = reg.get("must_not_conflate")
        if not isinstance(mnc, list) or not mnc:
            self.fail("R06", "regularity.must_not_conflate", "must_not_conflate missing/empty")
        # revision 1.1: unknown regularity keys that assert a smoothness/differentiability
        # assumption smuggle a second regularity selector past the slot list (escape sem01).
        for k, v in reg.items():
            if k in REGULARITY_KNOWN_KEYS:
                continue
            blob = f"{k} {json.dumps(v)}".lower()
            if contains_any(blob, SMUGGLE_MARKERS):
                self.fail("R06", f"regularity.{k}",
                          "unknown regularity key asserting an extra smoothness/regularity "
                          "assumption (slot list is closed)")
        if self.spec["family"] == "SCC":
            ext = text_of(reg.get("extension_regularity"))
            if self.spec["regularity_token"] not in ext:
                self.fail("R06", "regularity.extension_regularity",
                          f"SCC extension_regularity must be exactly the class token "
                          f"{self.spec['regularity_token']}")
            concept = text_of(reg.get("extension_solution_concept")).lower()
            if not concept or concept in {"not asserted", "n/a", "tbd", "missing"}:
                self.fail("R06", "regularity.extension_solution_concept",
                          "SCC extension solution concept must be declared "
                          "('none' is a valid declaration meaning no field equations are imposed)")
            # revision 1.1: the declared solution concept is class data, not a free slot
            # (escape sem08: C0 with extension_solution_concept=distributional_ricci).
            expected_concept = self.spec.get("extension_solution_concept")
            if expected_concept is not None and concept and concept != expected_concept:
                self.fail("R06", "regularity.extension_solution_concept",
                          f"extension_solution_concept {concept!r} != class value "
                          f"{expected_concept!r}")
        # revision 1.1: the extension predicate carries the frozen equation concept, the class
        # regularity token and the one-sided direction. Deleting the equation requirement
        # (struct10) or swapping any of the three (sem09/sem10/sem08) leaks the class.
        ep = get(self.doc, "extension_predicate")
        if self.spec["family"] == "SCC":
            if not isinstance(ep, dict):
                self.fail("R06", "extension_predicate",
                          "extension_predicate missing/not a mapping")
            else:
                if not text_of(ep.get("frozen_equation_concept")):
                    self.fail("R06", "extension_predicate.frozen_equation_concept",
                              "frozen_equation_concept missing/empty (equation requirement omitted)")
                fr = text_of(ep.get("frozen_regularity")).upper().replace(" ", "")
                want_fr = self.spec["regularity_token"].upper()
                if fr != want_fr:
                    self.fail("R06", "extension_predicate.frozen_regularity",
                              f"frozen_regularity {fr!r} != class token {want_fr!r}")
                fd = text_of(ep.get("frozen_direction")).lower()
                if fd not in {"future", "one_sided_future", "one-sided future"}:
                    self.fail("R06", "extension_predicate.frozen_direction",
                              f"frozen_direction {fd!r} is not the one-sided future direction")

    def r07_genericity(self):
        g = get(self.doc, "genericity")
        if not isinstance(g, dict):
            self.fail("R07", "genericity", "genericity missing/not a mapping")
            return
        kind_raw = str(g.get("kind", ""))
        kind = GENERICITY_ALIASES.get(kind_raw, kind_raw)
        if kind not in GENERICITY_KINDS:
            self.fail("R07", "genericity.kind", f"kind {kind_raw!r} not in vocabulary")
        elif kind != kind_raw:
            self.alias_uses.append({"rule": "R07", "path": "genericity.kind",
                                   "alias": kind_raw, "canonical": kind})
        # revision 1.1: genericity is part of the class identity. 'none' treats it as optional
        # (sem04). The frozen contract pins the class kind (residual_comeager for all three
        # canonical classes); a no-transfer sibling notion (sem13: full_measure) is recorded by
        # the schema itself as not transferable from that kind.
        if kind == "none":
            self.fail("R07", "genericity.kind",
                      "genericity.kind='none' drops a genericity slot the class declares as "
                      "part of its identity")
        expected_kind = self.spec.get("genericity_kind")
        if expected_kind is not None and kind != expected_kind:
            self.fail("R07", "genericity.kind",
                      f"kind {kind_raw!r} != frozen class genericity kind {expected_kind!r}")
        tf_raw = g.get("transfer_failures")
        if isinstance(tf_raw, list):
            no_transfer = set()
            for item in tf_raw:
                if not isinstance(item, dict):
                    continue
                if str(item.get("direction", "")).lower().replace("-", "_") in {"no_transfer", "none"}:
                    for x in (item.get("pair") or []):
                        no_transfer.add(str(x))
            if expected_kind is not None and kind in no_transfer and kind != expected_kind:
                self.fail("R07", "genericity.kind",
                          f"kind {kind_raw!r} is recorded by this schema as a no-transfer "
                          f"notion, not the class kind")
        for key in ("ambient_space", "topology_or_measure", "generic_set", "excluded_set"):
            if not text_of(g.get(key)):
                self.fail("R07", f"genericity.{key}", f"{key} missing/empty")
        gs = text_of(g.get("generic_set"))
        # revision 1.1: R07 requires a set-builder or Baire formula, not a prose gesture at
        # 'open dense' (escape sem03).
        has_builder = ("{" in gs and "}" in gs)
        has_baire = bool(re.search(
            r"(countabl\w*|intersection|residual|comeager|baire|first category|meager complement)",
            gs, re.IGNORECASE)) and bool(re.search(r"open\s+(and\s+)?dense|dense\s+open", gs, re.IGNORECASE))
        has_baire = has_baire or bool(re.search(r"residual|comeager|baire", gs, re.IGNORECASE))
        if gs and kind != "none" and not (has_builder or has_baire):
            self.fail("R07", "genericity.generic_set",
                      "generic_set is not given as a set-builder or Baire formula")
        tf = g.get("transfer_failures")
        if not isinstance(tf, list) or not tf:
            self.fail("R07", "genericity.transfer_failures", "transfer_failures missing/empty")
        if g.get("is_part_of_class") is not True:
            self.fail("R07", "genericity.is_part_of_class", "is_part_of_class must be true")
        statement = text_of(g.get("is_part_of_class_statement")) or text_of(g.get("class_change_warning"))
        if not statement:
            self.fail("R07", "genericity.is_part_of_class_statement",
                      "statement that changing the notion yields a different class is missing")

    def r08_non_vacuity(self):
        nv = get(self.doc, "non_vacuity")
        if not isinstance(nv, dict):
            self.fail("R08", "non_vacuity", "non_vacuity missing/not a mapping")
            return
        cond = text_of(nv.get("condition"))
        if not cond:
            self.fail("R08", "non_vacuity.condition", "non-vacuity condition missing")
        # revision 1.1: the condition must be a substantive membership requirement on data,
        # not a trivially-true or vague sentence (escapes sem15/sem19).
        elif not contains_any(cond.lower(), [
                "must be applied to data", "must contain data", "must contain", "data whose",
                "witness", "non-empty", "nonempty", "exists a", "there exists", "exhibited",
                "at least one"]):
            self.fail("R08", "non_vacuity.condition",
                      "non-vacuity condition is not a substantive membership requirement "
                      "(no witness/data requirement)")
        elif contains_any(cond.lower(), VAGUE_WORDS + ["interesting", "enough to test"]):
            self.fail("R08", "non_vacuity.condition",
                      "non-vacuity condition uses vague/untestable language")
        witness = text_of(nv.get("witness_type"))
        if not witness:
            self.fail("R08", "non_vacuity.witness_type", "non-vacuity witness_type missing")
        else:
            # revision 1.1: a null-ish placeholder does not name a witness (struct09).
            if NULLISH.match(witness):
                self.fail("R08", "non_vacuity.witness_type",
                          f"witness_type {witness!r} is a null placeholder, not a witness")
            elif not contains_any(witness.lower(), WITNESS_NAMING):
                self.fail("R08", "non_vacuity.witness_type",
                          "witness_type does not name a witness/data family")
        # revision 1.1: unknown non_vacuity keys asserting extra hypotheses (sem05 curvature).
        for k, v in nv.items():
            if k in NON_VACUITY_KNOWN_KEYS:
                continue
            blob = f"{k} {json.dumps(v)}".lower()
            if contains_any(blob, SMUGGLE_MARKERS):
                self.fail("R08", f"non_vacuity.{k}",
                          "unknown non_vacuity key asserting an extra hypothesis")

    def r09_i_plus(self):
        ip = get(self.doc, "i_plus")
        if not isinstance(ip, dict):
            self.fail("R09", "i_plus", "i_plus missing/not a mapping")
            return
        role = str(ip.get("role", ""))
        if role not in I_PLUS_ROLES:
            self.fail("R09", "i_plus.role", f"role {role!r} not in vocabulary")
        if self.spec["family"] == "WCC":
            if role != "conclusion":
                self.fail("R09", "i_plus.role", "WCC requires i_plus.role=conclusion")
            if ip.get("in_conclusion") is not True:
                self.fail("R09", "i_plus.in_conclusion", "WCC requires i_plus.in_conclusion=true")
            if not text_of(ip.get("completeness_definition")):
                self.fail("R09", "i_plus.completeness_definition",
                          "WCC I+ completeness definition missing")
        else:
            if ip.get("in_conclusion") is not False:
                self.fail("R09", "i_plus.in_conclusion", "SCC requires i_plus.in_conclusion=false")
            if ip.get("completeness_in_conclusion") is True:
                self.fail("R09", "i_plus.completeness_in_conclusion",
                          "SCC must not put I+ completeness in the conclusion")
            # only *assertions* of completeness fail; negated/prohibited mentions are legitimate.
            # Clause-level: a negation elsewhere in the same string must not mask an assertion.
            bad = []
            for p, s in iter_strings(ip):
                if not contains_any(s, ["complete", "completeness"]):
                    continue
                if any(m in p.lower() for m in PROHIBITION_MARKERS):
                    continue
                for clause in re.split(r"[.;\n]", s):
                    if not contains_any(clause, ["complete", "completeness"]):
                        continue
                    if not contains_any(clause.lower(), NEGATION_MARKERS):
                        bad.append(p)
                        break
            if bad:
                self.fail("R09", bad[0], "SCC i_plus block asserts completeness")

    def r10_visibility(self):
        v = get(self.doc, "visibility")
        if not isinstance(v, dict):
            self.fail("R10", "visibility", "visibility missing/not a mapping")
            return
        role = str(v.get("role", ""))
        if role not in VISIBILITY_ROLES:
            self.fail("R10", "visibility.role", f"role {role!r} not in vocabulary")
        if self.spec["family"] == "WCC":
            if role != "conclusion":
                self.fail("R10", "visibility.role", "WCC requires visibility.role=conclusion")
            if not (text_of(v.get("predicate")) or text_of(v.get("predicate_name"))):
                self.fail("R10", "visibility.predicate", "predicate/predicate_name missing")
            for key in ("definition", "negation_conclusion"):
                if not text_of(v.get(key)):
                    self.fail("R10", f"visibility.{key}", f"{key} missing/empty")
        else:
            if role != "not_in_conclusion":
                self.fail("R10", "visibility.role", "SCC requires visibility.role=not_in_conclusion")
            reason = text_of(v.get("reason")) or text_of(v.get("reason_not_in_conclusion"))
            if not reason:
                self.fail("R10", "visibility.reason", "SCC visibility reason missing")
            joined = " ".join(s for _, s in iter_strings(v)).lower()
            if "wcc" not in joined:
                self.fail("R10", "visibility", "SCC visibility block must state that a "
                                               "visible-singularity falsifier belongs to WCC")

    def r11_conclusion(self):
        c = get(self.doc, "conclusion")
        if not isinstance(c, dict):
            self.fail("R11", "conclusion", "conclusion missing/not a mapping")
            return
        ctype_raw = str(c.get("conclusion_type", ""))
        ctype = CONCLUSION_ALIASES.get(ctype_raw, ctype_raw)
        if ctype != self.spec["conclusion_type"]:
            self.fail("R11", "conclusion.conclusion_type",
                      f"conclusion_type {ctype_raw!r} != {self.spec['conclusion_type']!r}")
        elif ctype != ctype_raw:
            self.alias_uses.append({"rule": "R11", "path": "conclusion.conclusion_type",
                                    "alias": ctype_raw, "canonical": ctype})
        epistemic = str(c.get("epistemic_status") or c.get("type") or self.doc.get("epistemic_status"))
        if epistemic == "theorem" or ctype == "theorem":
            refs = c.get("artifact_refs") or self.doc.get("artifact_refs")
            if not refs:
                self.fail("R11", "conclusion.epistemic_status",
                          "theorem label without artifact_refs")
        elif epistemic not in EPISTEMIC:
            self.fail("R11", "conclusion.epistemic_status",
                      f"epistemic status {epistemic!r} not in {sorted(EPISTEMIC)}")
        fs = c.get("forbidden_strengthenings")
        if not isinstance(fs, list) or not fs:
            self.fail("R11", "conclusion.forbidden_strengthenings",
                      "forbidden_strengthenings missing/empty")
        # revision 1.1: a conclusion may not be inherited from a sibling class (escape sem02).
        inh = c.get("inherited_from")
        if isinstance(inh, dict):
            src = text_of(inh.get("class_id"))
            if src and src != self.class_id:
                self.fail("R11", "conclusion.inherited_from",
                          f"conclusion inherited from sibling class {src!r}")
        # revision 1.1: theorem promotion in the conclusion prose, with no artifact_refs
        # (escape sem12). Only statement fields are scanned; the claim_promotion policy key is
        # explicitly about the prohibition, not an assertion.
        refs = c.get("artifact_refs") or self.doc.get("artifact_refs")
        if not refs:
            for key in ("statement_natural_language", "statement_formal"):
                s = text_of(c.get(key))
                if s:
                    m = THEOREM_PROMOTION.search(s)
                    if m:
                        self.fail("R11", f"conclusion.{key}",
                                  f"conclusion statement promotes a theorem ({m.group(0)!r}) "
                                  f"without artifact_refs")
            for i, r in enumerate(c.get("equivalent_rephrasings") or []):
                if isinstance(r, dict):
                    s = text_of(r.get("phrasing"))
                    if s and THEOREM_PROMOTION.search(s):
                        self.fail("R11", f"conclusion.equivalent_rephrasings[{i}].phrasing",
                                  "rephrasing promotes a theorem without artifact_refs")

    def _scan_block(self, block, tokens, label):
        node = get(self.doc, block)
        if node is None:
            return
        for path, s in iter_strings(node, path=block):
            low_path = path.lower()
            if any(f".{k}" in low_path for k in EXEMPT_KEYS) or \
               any(m in low_path for m in EXEMPT_PATH_MARKERS):
                if contains_any(s, tokens):
                    self.exempted.append({"rule": "R12", "path": path,
                                          "reason": "prohibition/exemption context, recorded not failed"})
                continue
            if contains_any(s, tokens):
                self.fail("R12", path, f"foreign {label} token in {block} block")

    def r12_leakage(self):
        # exemption hygiene: any exemption container must carry tagged entries
        for block in SCAN_BLOCKS:
            node = get(self.doc, block)
            if not isinstance(node, dict):
                continue
            for key in EXEMPT_KEYS:
                if key in node:
                    val = node[key]
                    if isinstance(val, list):
                        for i, item in enumerate(val):
                            if not isinstance(item, dict) or not (item.get("tag") or item.get("text")):
                                self.fail("R12", f"{block}.{key}[{i}]",
                                          "exemption entry must be tagged (tag/text)")
        if self.spec["family"] == "WCC":
            for block in SCAN_BLOCKS:
                self._scan_block(block, SCC_TOKENS, "SCC")
        else:
            for block in ("conclusion", "i_plus", "falsifier"):
                self._scan_block(block, WCC_TOKENS, "WCC")
        if self.spec["matter"] == "vacuum":
            for block in SCAN_BLOCKS:
                self._scan_block(block, MATTER_TOKENS, "matter")
        for block in SCAN_BLOCKS:
            self._scan_block(block, ASYMPTOTIC_TOKENS, "asymptotic")
        # revision 1.1: an SCC schema may not carry the sibling SCC class id inside a scanned
        # block (escape sem02: C0 conclusion.inherited_from pointing at AF-SCC-C2-VAC-GEN).
        if self.class_id in SIBLING_CLASS:
            for block in SCAN_BLOCKS:
                self._scan_block(block, [SIBLING_CLASS[self.class_id]], "sibling-class")

    def r13_composite_regularity(self):
        reg = get(self.doc, "regularity") or {}
        ext = text_of(reg.get("extension_regularity")) if isinstance(reg, dict) else ""
        if "C0" in ext and "C2" in ext:
            self.fail("R13", "regularity.extension_regularity",
                      f"mixed C0/C2 token in extension_regularity: {ext!r}")
        scan = {}
        for k, v in self.doc.items():
            if k in EXEMPT_KEYS:
                continue
            scan[k] = v
        for path, s in iter_strings(scan):
            low_path = path.lower()
            if any(f".{k}" in low_path for k in EXEMPT_KEYS) or \
               any(m in low_path for m in EXEMPT_PATH_MARKERS):
                continue
            m = COMPOSITE_REGEX.search(s)
            if m:
                self.fail("R13", path, f"composite regularity phrase {m.group(0)!r}")

    def r14_falsifier(self):
        f = get(self.doc, "falsifier")
        if not isinstance(f, dict):
            self.fail("R14", "falsifier", "falsifier missing/not a mapping")
            return
        t1 = f.get("tier_1")
        if not isinstance(t1, dict):
            self.fail("R14", "falsifier.tier_1", "tier_1 missing/not a mapping")
        else:
            stmt = (text_of(t1.get("statement")) or text_of(t1.get("witness_type"))
                    or text_of(t1.get("refutes")))
            if not stmt:
                self.fail("R14", "falsifier.tier_1.statement", "tier_1 statement missing")
            robust = (text_of(t1.get("robustness_requirement"))
                      or text_of(t1.get("genericity_requirement"))
                      or (contains_any(stmt, ["open set", "residual", "robust", "generic",
                                              "non-meager", "comeager"]) and stmt))
            if not robust:
                self.fail("R14", "falsifier.tier_1.robustness_requirement",
                          "tier_1 lacks a genericity/robustness requirement")
            # prefer the explicit family_witness_type; only fall back to the other fields when
            # it is absent, so a wrong-family witness cannot hide behind a correct prose field
            # revision 1.1: the family check reads the WITNESS text only. The old join included
            # `refutes`, whose class-id token ('...C0...') satisfied the SCC markers and let a
            # WCC-shaped witness through (escape sem06).
            fam_witness = (text_of(t1.get("family_witness_type"))
                           or text_of(t1.get("witness_type"))).lower()
            if self.spec["family"] == "WCC" and not contains_any(
                    fam_witness, ["visible", "causal geodesic"]):
                self.fail("R14", "falsifier.tier_1",
                          "WCC tier_1 witness must be a visible incomplete causal geodesic")
            if self.spec["family"] == "SCC" and not contains_any(
                    fam_witness, ["extension", "inextendib", "extendib"]):
                self.fail("R14", "falsifier.tier_1",
                          "SCC tier_1 witness must be an extension witness")
        t2 = f.get("tier_2")
        if not isinstance(t2, dict):
            self.fail("R14", "falsifier.tier_2", "tier_2 missing/not a mapping")
        elif not contains_any(" ".join(str(t2.get(k, "")) for k in
                                       ("refutes", "statement", "label", "labelling_required")),
                              ["strengthening", "stronger", "strengthening_only"]):
            self.fail("R14", "falsifier.tier_2", "tier_2 must be labelled as refuting a strengthening")
        if not text_of(f.get("witness_type")) and not text_of(get(f, "tier_1.witness_type")):
            self.fail("R14", "falsifier.witness_type", "witness_type missing")
        steps = f.get("machine_checkable_steps") or get(f, "tier_1.machine_checkable_steps")
        if not isinstance(steps, list) or not steps:
            self.fail("R14", "falsifier.machine_checkable_steps",
                      "machine_checkable_steps missing/empty")

    def r15_provenance(self):
        p = get(self.doc, "provenance")
        c = get(self.doc, "conclusion")
        if not isinstance(p, dict):
            self.fail("R15", "provenance", "provenance missing/not a mapping")
            return
        status = str(p.get("citation_status", ""))
        if status not in CITATION_STATUS:
            self.fail("R15", "provenance.citation_status",
                      f"citation_status {status!r} not in vocabulary")
        sources = p.get("sources")
        if status == "verified":
            ok = isinstance(sources, list) and any(
                isinstance(s, dict) and text_of(s.get("identifier")) and
                text_of(s.get("retrieval_date")) for s in sources)
            if not ok:
                self.fail("R15", "provenance.sources",
                          "citation_status=verified requires a source with identifier and retrieval date")
        if "unresolved_citations" not in p:
            self.fail("R15", "provenance.unresolved_citations", "unresolved_citations list missing")
        disclaimer = text_of(p.get("source_conclusion_disclaimer")).lower()
        overclaim = False
        path = None
        if isinstance(sources, list):
            for i, s in enumerate(sources):
                if not isinstance(s, dict):
                    continue
                if s.get("establishes_class_conclusion") is True:
                    overclaim = True
                    path = f"provenance.sources[{i}]"
                    break
                note = " ".join(str(v) for v in s.values()).lower()
                # revision 1.1: broader overclaim phrasing (escape sem18: "establishes the
                # conclusion of this class").
                m = OVERCLAIM_RE.search(note)
                if m:
                    overclaim = True
                    path = f"provenance.sources[{i}]"
                    break
        if overclaim and not disclaimer:
            self.fail("R15", path, "source presented as establishing the class conclusion")
        # revision 1.1: a citation embedded in the conclusion block and used as evidence for
        # the class conclusion is the same overclaim (escape sem14: conclusion.citation_use).
        if isinstance(c, dict):
            for k, v in c.items():
                if not re.search(r"citation|source", k, re.IGNORECASE):
                    continue
                for sub, s in iter_strings(v, path=f"conclusion.{k}"):
                    m = CITE_USE_RE.search(s)
                    if m:
                        self.fail("R15", sub,
                                  f"citation embedded in the conclusion is presented as "
                                  f"support for the class conclusion ({m.group(0)!r})")

    def r16_implication_ledger(self):
        if self.spec["family"] != "SCC":
            return
        led = get(self.doc, "implication_ledger")
        if not isinstance(led, dict):
            self.fail("R16", "implication_ledger", "SCC implication_ledger missing")
            return
        stmts = led.get("statements") or led.get("one_way_entailments")
        if not isinstance(stmts, list) or not stmts:
            self.fail("R16", "implication_ledger.statements", "statements missing/empty")
            return
        joined = " ".join(s for _, s in iter_strings(stmts)).lower()
        if not ("c2" in joined and "c0" in joined):
            self.fail("R16", "implication_ledger.statements", "ledger does not relate C2 and C0")
        if not contains_any(joined, ["subset", "contained", "⊂", "larger", "weaker", "stronger",
                                     "strictly", "every c2", "every c0"]):
            self.fail("R16", "implication_ledger.statements",
                      "one-way containment (C2 subset C0) not recorded")
        if not contains_any(joined, ["entail", "implies", "one-way"]):
            self.fail("R16", "implication_ledger.statements",
                      "C0-inextendibility entails C2-inextendibility not recorded")
        fu = led.get("forbidden_or_unresolved") or led.get("forbidden_transfers")
        if not isinstance(fu, list) or not fu:
            self.fail("R16", "implication_ledger.forbidden_or_unresolved",
                      "forbidden/unresolved transfers not recorded")
        else:
            fuj = " ".join(s for _, s in iter_strings(fu)).lower()
            if "wcc" not in fuj:
                self.fail("R16", "implication_ledger.forbidden_or_unresolved",
                          "WCC<->SCC transfer not marked forbidden_or_unresolved")
        # revision 1.1: the converse C2 => C0 must not be asserted as a one-way entailment;
        # it belongs in forbidden_or_unresolved (escape sem16 appended such a row).
        rows = led.get("one_way_entailments")
        if isinstance(rows, list):
            for i, row in enumerate(rows):
                if not isinstance(row, dict):
                    continue
                a = str(row.get("from", "")).lower()
                b = str(row.get("to", "")).lower()
                if re.search(r"\bc2\b", a) and re.search(r"\bc0\b", b):
                    self.fail("R16", f"implication_ledger.one_way_entailments[{i}]",
                              "converse C2 => C0 asserted as a one-way entailment; the "
                              "converse belongs in forbidden_or_unresolved")

    def run(self):
        for rule in self.rule_ids():
            self.checked.append(rule)
            getattr(self, f"r{rule[1:].lower()}_{self._rule_name(rule)}")()
        per_rule = {}
        for rule in self.rule_ids():
            if rule == "R16" and self.spec["family"] != "SCC":
                per_rule[rule] = {"status": "skip", "json_path": None,
                                  "detail": "R16 applies_to SCC only"}
                continue
            fs = self.findings[rule]
            per_rule[rule] = {
                "status": "pass" if not fs else "fail",
                "json_path": fs[0]["path"] if fs else None,
                "detail": "" if not fs else "; ".join(f"{f['path']}: {f['detail']}" for f in fs[:4]),
            }
        return per_rule

    @staticmethod
    def _rule_name(rule):
        return {
            "R01": "identity", "R02": "class_components", "R03": "quantifiers",
            "R04": "topology", "R05": "data_class", "R06": "regularity",
            "R07": "genericity", "R08": "non_vacuity", "R09": "i_plus",
            "R10": "visibility", "R11": "conclusion", "R12": "leakage",
            "R13": "composite_regularity", "R14": "falsifier",
            "R15": "provenance", "R16": "implication_ledger",
        }[rule]


def evaluate(path: Path, class_id: str | None = None, r03_mode: str = "semantic"):
    try:
        doc = yaml.safe_load(path.read_text()) if yaml else None
    except Exception as exc:
        return {"gate": GATE_ID, "target": str(path), "class_id": class_id,
                "verdict": "error", "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(doc, dict):
        return {"gate": GATE_ID, "target": str(path), "class_id": class_id,
                "verdict": "error", "error": "top level is not a mapping"}
    cid = class_id or doc.get("class_id")
    if cid not in FROZEN_CLASSES:
        return {"gate": GATE_ID, "target": str(path), "class_id": cid,
                "verdict": "error", "error": f"unknown class_id {cid!r}"}
    if class_id and doc.get("class_id") != class_id:
        gate = Gate(class_id, doc, str(path), r03_mode=r03_mode)
        gate.fail("R01", "class_id", f"document class_id {doc.get('class_id')!r} != --class {class_id!r}")
        per_rule = gate.run()
    else:
        gate = Gate(cid, doc, str(path), r03_mode=r03_mode)
        per_rule = gate.run()
    verdict = "pass" if all(v["status"] in ("pass", "skip") for v in per_rule.values()) else "fail"
    synonyms = {k: v for k, v in SYNONYMS.items() if v in doc and k not in doc}
    result = {
        "gate": GATE_ID, "gate_version": GATE_VERSION, "spec": f"{SPEC_ID} v{SPEC_VERSION}",
        "gate_revision": "1.3 semantic R03 realization (kind-sequence + variable coverage); "
                         "literal reading reported in r03_readings",
        "r03_mode": gate.r03_mode, "r03_readings": gate.r03_readings,
        "target": str(path), "class_id": cid, "sha256": sha256_file(path),
        "verdict": verdict, "per_rule": per_rule,
        "failed_rules": [r for r, v in per_rule.items() if v["status"] == "fail"],
        "rules_skipped": [r for r, v in per_rule.items() if v["status"] == "skip"],
        "exempted_mentions": gate.exempted,
        "alias_uses": gate.alias_uses,
        "possible_synonyms": synonyms,
        "scope": "structural only; no physical truth, no theorem promotion, no citation adjudication",
    }
    if synonyms:
        result["conformance_note"] = (
            "target lacks spec-named top-level keys and carries pre-spec synonyms "
            f"{synonyms}; rules are reported against the published names, so a vocabulary "
            "revision (not a rewrite) is what is required")
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=f"{GATE_ID} v{GATE_VERSION} ({SPEC_ID} v{SPEC_VERSION})")
    ap.add_argument("target", nargs="?", help="schema YAML/JSON to check")
    ap.add_argument("--class", dest="klass", default=None, help="expected class id")
    ap.add_argument("--canonical", action="store_true",
                    help="check the three canonical schema paths; exit 3 if any is absent")
    ap.add_argument("--canonical-dir", default=".")
    ap.add_argument("--r03-mode", dest="r03_mode", choices=("semantic", "literal"), default="semantic",
                    help="R03 pass criterion: semantic realization (default, revision 1.3) or the "
                         "revision-1.2 literal-substring audit reading; both are reported")
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args(argv)

    results = []
    if args.canonical:
        root = Path(args.canonical_dir)
        try:
            frozen = json.loads((root / FROZEN_MANIFEST).read_text()).get("files", {})
        except Exception:
            frozen = {}
        resolved, missing = {}, []
        for cid, rel in CANONICAL.items():
            if (root / rel).exists():
                resolved[cid] = rel
            elif (root / CANONICAL_FALLBACK[cid]).exists():
                resolved[cid] = CANONICAL_FALLBACK[cid]
            else:
                missing.append(rel)
        if missing:
            print(f"CANONICAL ABSENT (exit 3, not a pass): {', '.join(missing)}")
            if args.json_out:
                Path(args.json_out).write_text(json.dumps(
                    {"gate": GATE_ID, "mode": "canonical", "verdict": "absent",
                     "missing": missing}, indent=2) + "\n")
            return 3
        for cid, rel in resolved.items():
            res = evaluate(root / rel, cid, r03_mode=args.r03_mode)
            fmeta = frozen.get(rel)
            if fmeta:
                res["frozen_sha256"] = fmeta["sha256"]
                res["frozen_match"] = bool(res["sha256"] == fmeta["sha256"])
                res["frozen_prefix"] = fmeta["sha256"][:12]
            results.append(res)
    else:
        if not args.target:
            print("usage: check_class_schema.py TARGET [--class CLASS] | --canonical", file=sys.stderr)
            return 2
        p = Path(args.target)
        if not p.exists():
            print(f"INPUT ERROR: {p} does not exist", file=sys.stderr)
            return 2
        results.append(evaluate(p, args.klass, r03_mode=args.r03_mode))

    full_pass = True
    for res in results:
        if res.get("verdict") == "error":
            print(f"ERROR {res['target']}: {res['error']}")
            full_pass = False
            continue
        print(f"{res['target']} class={res['class_id']} verdict={res['verdict']} "
              f"sha256={res['sha256'][:16]}...")
        for rule, v in res["per_rule"].items():
            if v["status"] == "fail":
                print(f"  FAIL {rule}: {v['detail']}")
        if res["verdict"] != "pass":
            full_pass = False
        else:
            print(f"  all 16 rules pass ({len(res['rules_skipped'])} skipped: {res['rules_skipped']})")
    if args.json_out:
        payload = results[0] if len(results) == 1 else {
            "gate": GATE_ID, "mode": "canonical", "spec": f"{SPEC_ID} v{SPEC_VERSION}",
            "verdict": "pass" if full_pass else "fail", "results": results,
        }
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        print(f"wrote {args.json_out}")
    return 0 if full_pass else 1


if __name__ == "__main__":
    sys.exit(main())
