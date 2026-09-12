#!/usr/bin/env python3
"""Class-binding conformance linter for cosmic-censorship formulation schemas.

DRAFT / UNVERIFIED breadth artifact by execution worker flash-11. Not a gate.
Proposed node anchor: F1 (AF-WCC-VAC-GEN), supporting F2 and A1 review.
Proposed canonical home: verification/class_binding/ (owner: lead-formulation).

WHY THIS EXISTS
----------------
Hard decision #1 (ASTRA_HANDOFF.md) requires AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN,
AF-SCC-C0-VAC-GEN and AF-WCC-SCALAR-SPH to stay separate classes, and F1/F2 must
produce schemas with exact quantifiers, topology, weighted data class, genericity,
I+/visibility and an explicit conclusion type. Nothing in the repo currently
machine-checks a formulation schema: `research_map/validate_map.py` validates the
map DAG, not the class content of an artifact. This linter is a *proposal* for
that acceptance test, with a positive/negative fixture corpus and a falsification
campaign. It is deliberately conservative and lexical/deterministic: it can only
reject schemas that use known leaky tokens or omit required sections. Its escape
rate is measured, not assumed (see adversarial.py and README.md).

SCOPE (exact)
-------------
IN : one YAML/JSON schema document per run; class ids restricted to the four
     frozen classes; checks CLASS_ID, CONJUNCTION, QUANTIFIERS, TOPOLOGY,
     DATA_CLASS, MATTER, GENERICITY, I_PLUS, INEXTENDIBILITY, CONCLUSION_TYPE,
     SCOPE_SEPARATION, FILENAME_CLASS.
OUT: it does not judge physical correctness, does not prove a schema is
     well-posed, and does not replace lead/audit review (A1). ACCEPT here means
     "no known leak/omission pattern matched", nothing more.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - environment guard
    yaml = None

ALLOWED_CLASSES = {
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
}
ALLOWED_CONCLUSION_TYPES = {
    "theorem",
    "conditional_theorem",
    "stability_result",
    "counterexample",
    "numerical_evidence",
    "formal_model",
    "open_problem",
}

VAGUE_TERMS = [
    "some suitable",
    "suitable",
    "appropriate",
    "reasonable",
    "sufficiently generic",
    "sufficiently small",  # allowed only if a rate/constant is given; see note
    "etc.",
    "and so on",
    "maybe",
    "possibly",
    "roughly",
    "as needed",
    "if necessary",
]

REGULARITY_RE = re.compile(
    r"(C\s*\^?\s*(\d+|\\infty|infty|∞)|H\s*\^?\s*\d|W\s*\^?\{?\d|Sobolev|BV\b|L\s*\^?p|smooth|analytic)",
    re.IGNORECASE,
)
WEIGHT_RE = re.compile(r"(weight|weighted|decay|norm|mass|asymptotic|fall[- ]?off)", re.IGNORECASE)
QUANT_FORALL_RE = re.compile(r"(for all|for every|for any|∀)")
QUANT_EXISTS_RE = re.compile(r"(there exists|there is|∃)")
DISJUNCTION_RE = re.compile(r"(C\s*\^?\s*0\s*(or|/|,)\s*C\s*\^?\s*2|C\s*\^?\s*2\s*(or|/|,)\s*C\s*\^?\s*0|C0\s*or\s*C2|C2\s*or\s*C0|\beither\b[^.\n]{0,40}C\s*\^?\s*[02])", re.IGNORECASE)

SCC_ONLY_TOKENS = [
    "inextendib",
    "inextendable",
    "maximal development cannot be extended",
    "isometrically embedded",
    "cannot be extended",
    "admits no extension",
    "no extension",
    "cauchy horizon",
]
WCC_ONLY_TOKENS = [
    "visible from i+",
    "visible to i+",
    "visible from future null infinity",
    "visible to future null infinity",
    "observers at i+",
    "see no singularity",
    "no naked singularity",
    "not visible",
    "escapes to infinity",
]


def _get(doc: dict, *names: str) -> Any:
    """Case/alias tolerant lookup of the first present key."""
    lower = {str(k).lower().replace("-", "_"): v for k, v in doc.items()}
    for n in names:
        if n in lower:
            return lower[n]
    return None


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _is_mapping(value: Any) -> bool:
    return isinstance(value, dict)


class Result:
    def __init__(self, path: str):
        self.path = path
        self.checks: list[dict] = []
        self.class_id: str | None = None

    def add(self, code: str, ok: bool, detail: str) -> None:
        self.checks.append({"code": code, "ok": bool(ok), "detail": detail})

    @property
    def codes(self) -> list[str]:
        return [c["code"] for c in self.checks if not c["ok"]]

    @property
    def verdict(self) -> str:
        return "ACCEPT" if not self.codes else "REJECT"

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "verdict": self.verdict,
            "class_id": self.class_id,
            "failed_codes": self.codes,
            "checks": self.checks,
        }


def load_document(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return None
    if path.suffix.lower() in {".yaml", ".yml"}:
        if yaml is None:
            raise RuntimeError("PyYAML required for .yaml input")
        return yaml.safe_load(text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        if yaml is not None:
            return yaml.safe_load(text)
        raise


def check(document: Any, path: str) -> Result:
    res = Result(path)
    if not _is_mapping(document):
        res.add("DOC_SHAPE", False, "document is not a non-empty mapping (vacuous/garbage input)")
        return res

    doc: dict = document
    raw_class = _as_text(_get(doc, "class_id", "class", "formulation_class")).strip()
    res.class_id = raw_class or None

    # 1. CLASS_ID -- exactly one frozen class, no multi-class union.
    class_tokens = [c for c in ALLOWED_CLASSES if c in raw_class]
    if not raw_class:
        res.add("CLASS_ID", False, "no class_id declared")
    elif len(class_tokens) != 1 or raw_class not in ALLOWED_CLASSES:
        res.add("CLASS_ID", False, f"class_id {raw_class!r} is not exactly one of the four frozen classes")
    else:
        res.add("CLASS_ID", True, f"class_id={raw_class}")

    # 2. CONJUNCTION -- hard decision #1: never "C0 or C2".
    conclusion = _get(doc, "conclusion") or {}
    conj_scope = " ".join(
        [
            raw_class,
            _as_text(conclusion),
            _as_text(_get(doc, "quantifiers")),
            _as_text(_get(doc, "inextendibility", "extension")),
        ]
    )
    m = DISJUNCTION_RE.search(conj_scope)
    res.add(
        "CONJUNCTION",
        m is None,
        "no C0/C2 disjunction found" if m is None else f"disjunction token {m.group(0)!r} found",
    )

    # 3. QUANTIFIERS -- explicit forall + exists, no vagueness lexicon.
    quant = _get(doc, "quantifiers", "quantification")
    quant_text = _as_text(quant)
    ok_q = _is_mapping(quant) and bool(QUANT_FORALL_RE.search(quant_text)) and bool(QUANT_EXISTS_RE.search(quant_text))
    detail_q = "explicit forall+exists present"
    if not ok_q:
        detail_q = "quantifiers section missing explicit forall and exists"
    vague_hits = [t for t in VAGUE_TERMS if t in _as_text(doc).lower()]
    # "sufficiently small" is legitimate when accompanied by an explicit rate/constant.
    if "sufficiently small" in vague_hits and re.search(r"(constant|rate|exponent|epsilon|ε|bound)", _as_text(doc), re.IGNORECASE):
        vague_hits.remove("sufficiently small")
    res.add("QUANTIFIERS", ok_q and not vague_hits, detail_q + (f"; vague terms {vague_hits}" if vague_hits else ""))

    # 4. TOPOLOGY -- dimension + one structural descriptor.
    topo = _get(doc, "topology", "setting")
    topo_text = _as_text(topo)
    ok_topo = _is_mapping(topo) and bool(re.search(r"\b4\b|four[- ]dimensional", topo_text)) and bool(
        re.search(r"(symmetric|asymptotically flat|manifold|lorentzian|globally hyperbolic|spacetime)", topo_text, re.IGNORECASE)
    )
    res.add("TOPOLOGY", ok_topo, "dimension 4 + structural descriptor" if ok_topo else "topology missing dimension-4 or structural descriptor")

    # 5. DATA_CLASS -- regularity symbol in the regularity field itself + weight/decay statement.
    data = _get(doc, "data_class", "initial_data", "data")
    data_text = _as_text(data)
    data_reg = _as_text(_get(data, "regularity", "smoothness", "differentiability")) if _is_mapping(data) else ""
    ok_reg = bool(REGULARITY_RE.search(data_reg))
    ok_weight = bool(WEIGHT_RE.search(data_text))
    res.add(
        "DATA_CLASS",
        _is_mapping(data) and ok_reg and ok_weight,
        f"regularity field={'yes' if ok_reg else 'no'}, weight/decay={'yes' if ok_weight else 'no'}",
    )

    # 6. MATTER -- vacuum classes must not import scalar matter and vice versa.
    matter = _as_text(_get(doc, "matter", "matter_model", "field_content")).lower()
    if "VAC" in raw_class:
        ok_matter = bool(matter) and bool(re.search(r"(vacuum|ricci[- ]?flat|t\s*=\s*0|t_?\{?mu)", matter)) and not re.search(r"scalar", matter)
        detail_m = "vacuum matter content declared" if ok_matter else "vacuum class without vacuum matter declaration, or scalar leakage"
    elif "SCALAR" in raw_class:
        ok_matter = bool(matter) and "scalar" in matter and bool(re.search(r"potential|self[- ]interact|v\s*\(", matter))
        detail_m = "scalar matter + potential declared" if ok_matter else "scalar class without scalar/potential matter declaration"
    else:
        ok_matter = bool(matter)
        detail_m = "matter field present" if ok_matter else "matter field absent"
    res.add("MATTER", ok_matter, detail_m)

    # 7. GENERICITY -- kind + named parameter space (no bare "generic").
    gen = _get(doc, "genericity")
    gen_text = _as_text(gen).lower()
    ok_gen = _is_mapping(gen) and bool(re.search(r"(open[- ]dense|full[- ]measure|baire|residual|comeagre)", gen_text)) and bool(
        re.search(r"(parameter|data|initial|space|family|set)", gen_text)
    )
    res.add("GENERICITY", ok_gen, "genericity kind + parameter space" if ok_gen else "genericity missing open-dense/full-measure kind or named parameter space")

    # 8. I_PLUS vs 9. INEXTENDIBILITY -- class-appropriate conclusion channel.
    iplus = _as_text(_get(doc, "i_plus", "iplus", "scri_plus", "future_null_infinity"))
    inext = _get(doc, "inextendibility", "extension", "extendibility")
    inext_text = _as_text(inext)
    if raw_class.startswith("AF-WCC"):
        ok_i = bool(iplus) and bool(re.search(r"(visible|complete|censored|naked|i\+|null infinity)", iplus, re.IGNORECASE))
        res.add("I_PLUS", ok_i, "I+/visibility declared" if ok_i else "WCC class without I+/visibility declaration")
    else:
        res.add("I_PLUS", True, "not required for SCC class")

    if raw_class.startswith("AF-SCC"):
        want = "0" if raw_class == "AF-SCC-C0-VAC-GEN" else "2"
        other = "2" if want == "0" else "0"
        want_re = re.compile(rf"C\s*\^?\s*{want}(?!\d)")
        other_re = re.compile(rf"C\s*\^?\s*{other}(?!\d)")
        has_want = bool(want_re.search(inext_text)) or bool(want_re.search(_as_text(conclusion)))
        has_other = bool(other_re.search(inext_text))
        ok_inext = _is_mapping(inext) and bool(re.search(r"(inextendib|no extension|cannot be extended|maximal)", inext_text, re.IGNORECASE)) and has_want and not has_other
        res.add("INEXTENDIBILITY", ok_inext, f"SCC-C{want} inextendibility declared, no C{other} mixing" if ok_inext else f"SCC-C{want} inextendibility/regularity declaration missing or mixed with C{other}")
    else:
        res.add("INEXTENDIBILITY", True, "not required for WCC class")

    # 10. CONCLUSION_TYPE -- explicit, allowed, non-empty statement.
    ctype = ""
    statement = ""
    if _is_mapping(conclusion):
        ctype = _as_text(_get(conclusion, "type", "conclusion_type")).strip().lower()
        statement = _as_text(_get(conclusion, "statement", "claim"))
    ok_ctype = ctype in ALLOWED_CONCLUSION_TYPES and bool(statement.strip())
    res.add("CONCLUSION_TYPE", ok_ctype, f"type={ctype!r}, statement_len={len(statement)}" if ok_ctype else f"conclusion type {ctype!r} invalid or statement empty")

    # 11. SCOPE_SEPARATION -- no cross-class conclusion leakage.
    leak = ""
    if raw_class.startswith("AF-WCC"):
        hit = next((t for t in SCC_ONLY_TOKENS if t in statement.lower()), None)
        if hit:
            leak = f"WCC statement contains SCC-only token {hit!r}"
    elif raw_class.startswith("AF-SCC"):
        hit = next((t for t in WCC_ONLY_TOKENS if t in statement.lower()), None)
        if hit:
            leak = f"SCC statement contains WCC-only token {hit!r}"
    res.add("SCOPE_SEPARATION", not leak, leak or "no cross-class conclusion token found")

    # 12. FILENAME_CLASS -- filename must not advertise a different class.
    stem = Path(path).stem.lower().replace("-", "_")
    if raw_class:
        # af_wcc_vac_gen -> af-wcc-vac-gen
        wanted = raw_class.lower().replace("-", "_")
        if "af_" in stem and wanted not in stem:
            res.add("FILENAME_CLASS", False, f"filename {Path(path).name!r} does not contain {wanted}")
        else:
            res.add("FILENAME_CLASS", True, "filename consistent or non-class-bearing")

    return res


# ---------------------------------------------------------------------------
# Canonical-layout mode (FORM-DIFF-02): an INDEPENDENT implementation of the
# rules in artifacts/formulation/rule_spec.json (R01-R16). It shares no code
# with flash-13's or the formulation lead's gates. It is deliberately tolerant
# in layout (dotted lookup) but strict about the rule text. Where the rule text
# is ambiguous, the interpretation is documented in README.md and in the detail
# strings, and deviations are reported rather than hidden.
# ---------------------------------------------------------------------------
EXPECTED_CONCLUSION_TYPE = {
    "AF-WCC-VAC-GEN": "weak_cosmic_censorship",
    "AF-SCC-C2-VAC-GEN": "scc_c2_future_inextendibility",
    "AF-SCC-C0-VAC-GEN": "scc_c0_future_inextendibility",
    "AF-WCC-SCALAR-SPH": "weak_cosmic_censorship",
}
CANON_EPISTEMIC = {"open_problem", "formal_model", "conditional_theorem"}
CANON_GENERICITY = {"residual_comeager", "full_measure", "open_dense_escape", "finite_codimension_complement", "none"}
CANON_CITATION = {"unverified", "unresolved", "verified"}
COMPOSITE_RE = re.compile(r"C\s*\^?\s*([02])\s*(?:or|and|/|,)\s*C\s*\^?\s*([02])", re.IGNORECASE)
# R12 context-anchored leakage patterns. A bare "inextendib" is NOT SCC leakage:
# the WCC schema legitimately defines singular geodesics as "future-inextendible
# causal geodesics". This was found as differential finding FD-03 and fixed here.
SCC_LEAK_PATTERNS = [
    r"inextendib\w*\s+(?:spacetime|development|metric|manifold|extension)",
    r"(?:spacetime|development|metric|manifold)\s+(?:is|be)\s+\w*inextendib",
    r"proper\s+future\s+c[012]",
    r"cauchy\s+horizon",
    r"extension_predicate",
    r"no\s+(?:proper\s+)?(?:future\s+)?c[012]\s+(?:vacuum\s+)?extension",
]
WCC_LEAK_PATTERNS = [
    r"visible\s+(?:from|to)\s+i\+",
    r"no\s+naked\s+singularity",
    r"visible_singularity_from_i_plus",
    r"not\s+visible\s+from",
]


def _dig(doc: Any, dotted: str) -> Any:
    cur: Any = doc
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def _nonempty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) > 0
    return True


def _contains(text: str, needles: list[str]) -> str | None:
    low = text.lower()
    return next((n for n in needles if n in low), None)


_NEG_RE = re.compile(r"\b(no|not|never|without|cannot|forbidden|absent|refrain|fails? to|does not|do not|must not|may not)\b", re.IGNORECASE)
OVERCLAIM_RE = re.compile(r"(establishes|proves|proof of|settles)\s+the\s+(class\s+)?(conclusion|conjecture|statement)", re.IGNORECASE)


def _sentences(text: str) -> list[str]:
    if not text:
        return []
    return [s for s in re.split(r"(?<=[.;:!?])\s+|\n+", text) if s.strip()]


def _strings_at(doc: Any, path: tuple[str, ...]) -> list[str]:
    """Collect every string under a dotted path (dicts/lists traversed)."""
    cur = [doc]
    for part in path:
        nxt = []
        for node in cur:
            if isinstance(node, dict) and part in node:
                nxt.append(node[part])
            elif isinstance(node, list):
                for item in node:
                    if isinstance(item, dict) and part in item:
                        nxt.append(item[part])
        cur = nxt
    out: list[str] = []

    def walk(x: Any) -> None:
        if isinstance(x, str):
            out.append(x)
        elif isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    for node in cur:
        walk(node)
    return out


def check_canonical(document: Any, path: str) -> Result:
    """Independent R01-R16 gate for the canonical class-schema layout."""
    res = Result(path)
    if not _is_mapping(document):
        res.add("R01", False, "unparseable or non-mapping document")
        return res
    doc: dict = document
    cid = str(doc.get("class_id") or "").strip()
    res.class_id = cid or None
    fam = "WCC" if cid.startswith("AF-WCC") else ("SCC" if cid.startswith("AF-SCC") else "")
    is_vac = "VAC" in cid

    # R01 identity block
    ok = (
        _nonempty(doc.get("schema_version"))
        and doc.get("artifact_kind") == "class_schema"
        and cid in ALLOWED_CLASSES
        and _nonempty(doc.get("node_id"))
        and _nonempty(doc.get("owner"))
        and doc.get("epistemic_status") in CANON_EPISTEMIC
    )
    res.add("R01", ok, "identity block complete" if ok else "missing/wrong schema_version, artifact_kind, class_id, node_id, owner, or epistemic_status")

    # R02 class_components
    cc = doc.get("class_components")
    if _is_mapping(cc):
        reg = str(cc.get("regularity_token", "")).strip().upper()
        reg_ok = (reg == ("C2" if "C2" in cid else "C0")) if fam == "SCC" else reg in ("", "NONE")
        matter_ok = (str(cc.get("matter", "")).upper() == "VAC") if is_vac else (str(cc.get("matter", "")).upper() == "SCALAR")
        ok = (
            str(cc.get("asymptotics", "")).upper() == "AF"
            and str(cc.get("censorship", "")).upper() == fam
            and matter_ok
            and str(cc.get("genericity", "")).upper() == "GEN"
            and reg_ok
        )
        detail = f"components={cc}" if ok else f"class_components inconsistent with {cid}: {cc}"
    else:
        ok, detail = False, "class_components missing or not a mapping"
    res.add("R02", ok, detail)

    # R03 quantifiers
    q = doc.get("quantifiers")
    q_ok = False
    detail = "quantifiers missing or not a mapping"
    if _is_mapping(q):
        ordered = q.get("ordered")
        domains = q.get("domains")
        if isinstance(ordered, list) and ordered and isinstance(domains, dict):
            items_ok = all(
                isinstance(it, dict)
                and it.get("kind") in {"forall", "exists", "exists_unique", "not_exists"}
                and _nonempty(it.get("binder"))
                and it.get("domain_id") in domains
                for it in ordered
            )
            formal_ok = _nonempty(q.get("formal"))
            vague = [t for t in VAGUE_TERMS if t in _as_text(domains).lower() or t in _as_text(q.get("formal")).lower()]
            vague_ok = all(
                "definition_ref" in (_dig(domains, k) or {}) if isinstance(_dig(domains, k), dict) else False
                for k in domains
            ) or not vague
            q_ok = items_ok and formal_ok and vague_ok
            detail = f"ordered={len(ordered)} domains={len(domains)} vague={vague}" if not q_ok else "ordered quantifiers resolve"
    res.add("R03", q_ok, detail)

    # R04 topology
    topo = doc.get("topology")
    if _is_mapping(topo):
        slice_txt = _as_text(topo.get("slice_topology")) + " " + _as_text(topo.get("end_structure"))
        cb = _as_text(topo.get("conformal_boundary"))
        forbidden = _as_text(topo.get("forbidden")).lower()
        ok = (
            topo.get("spacetime_dimension") == 4
            and "connected" in slice_txt.lower()
            and "complete" in slice_txt.lower()
            and "asymptotically flat" in slice_txt.lower()
            and ("one" in slice_txt.lower())
            and "i+" in cb.lower()
            and "s^2" in _as_text(topo.get("I_plus_topology", topo.get("i_plus_topology"))).lower()
            and ("closed" in forbidden or "periodic" in forbidden)
        )
        detail = "dimension 4, complete one-ended AF slice, I+=R x S^2, closed/periodic forbidden" if ok else "topology incomplete or admits closed/periodic slice"
    else:
        ok, detail = False, "topology missing or not a mapping"
    res.add("R04", ok, detail)

    # R05 data_class
    dcl = doc.get("data_class")
    if _is_mapping(dcl):
        constraints = _as_text(dcl.get("constraints")).lower()
        decay = _as_text(dcl.get("asymptotic_decay"))
        reg = _as_text(dcl.get("regularity_class"))
        numeric = bool(re.search(r"(r\s*\^|O\(r|\\d)", decay)) or bool(re.search(r"\d", decay))
        sobolev = ("H^s" in reg or "sobolev" in reg.lower()) and ("delta" in reg.lower())
        matter_ok = (str(dcl.get("matter", "")).lower() in {"none", "vacuum"}) if is_vac else ("scalar" in str(dcl.get("matter", "")).lower())
        ok = (
            matter_ok
            and dcl.get("cosmological_constant") == 0
            and "hamiltonian" in constraints
            and "momentum" in constraints
            and _nonempty(dcl.get("adm_mass"))
            and numeric
            and sobolev
        )
        detail = "matter/constraints/ADM/decay/Sobolev declared" if ok else "data_class missing matter, constraints, ADM, numeric decay, or Sobolev s/delta"
    else:
        ok, detail = False, "data_class missing or not a mapping"
    res.add("R05", ok, detail)

    # R06 regularity slots
    regd = doc.get("regularity")
    if _is_mapping(regd):
        slots = all(_nonempty(regd.get(k)) for k in ("data_regularity", "solution_regularity", "i_plus_regularity"))
        sep = _nonempty(regd.get("must_not_conflate"))
        if fam == "SCC":
            want = "C2" if "C2" in cid else "C0"
            ext_ok = str(regd.get("extension_regularity", "")).strip().upper() == want and _nonempty(regd.get("extension_solution_concept"))
        else:
            ext_ok = regd.get("extension_regularity") in (None, "", "none") and regd.get("extension_solution_concept") in (None, "")
        ok = slots and sep and ext_ok
        detail = "regularity slots separated and extension regularity class-correct" if ok else "regularity slots merged or extension regularity mismatched/conflated"
    else:
        ok, detail = False, "regularity missing or not a mapping"
    res.add("R06", ok, detail)

    # R07 genericity
    gen = doc.get("genericity")
    if _is_mapping(gen):
        ok = (
            gen.get("kind") in CANON_GENERICITY
            and _nonempty(gen.get("ambient_space"))
            and _nonempty(gen.get("topology_or_measure"))
            and _nonempty(gen.get("generic_set"))
            and "excluded_set" in gen
            and _nonempty(gen.get("transfer_failures"))
            and gen.get("is_part_of_class") is True
            and _nonempty(gen.get("class_change_warning"))
        )
        detail = "genericity kind+ambient+set+transfer failures present" if ok else "genericity underspecified or treated as free parameter"
    else:
        ok, detail = False, "genericity missing or not a mapping"
    res.add("R07", ok, detail)

    # R08 non-vacuity
    nv = doc.get("non_vacuity")
    ok = _is_mapping(nv) and _nonempty(nv.get("condition")) and _nonempty(nv.get("witness_type"))
    res.add("R08", ok, "non-vacuity condition+witness present" if ok else "non_vacuity missing condition or witness_type")

    # R09 I+ (rev4: negation-aware for SCC)
    ip = doc.get("i_plus")
    if _is_mapping(ip):
        if fam == "WCC":
            ok = ip.get("role") == "conclusion" and ip.get("in_conclusion") is True and _nonempty(ip.get("completeness_definition"))
            detail = "I+ role correct for family" if ok else "I+ role wrong for family or SCC asserts I+ completeness"
        else:
            ok = ip.get("in_conclusion") is False and ip.get("role") == "assumption" and ip.get("completeness_in_conclusion") is not True
            positive = []
            for key in ("definition", "required_properties", "completeness_definition"):
                for sentence in _sentences(_as_text(ip.get(key))):
                    if re.search(r"complete", sentence, re.IGNORECASE) and not _NEG_RE.search(sentence):
                        positive.append(sentence.strip()[:120])
            if positive:
                ok = False
            detail = ("SCC I+ role correct and no positive completeness assertion" if ok
                      else f"SCC i_plus asserts completeness: {positive[:2]}" if positive
                      else "I+ role wrong for family or SCC asserts I+ completeness")
    else:
        ok, detail = False, "i_plus missing or not a mapping"
    res.add("R09", ok, detail)

    # R10 visibility role
    vis = doc.get("visibility")
    if _is_mapping(vis):
        if fam == "WCC":
            ok = vis.get("role") == "conclusion" and _nonempty(vis.get("predicate_name")) and _nonempty(vis.get("definition")) and _nonempty(vis.get("negation_conclusion"))
        else:
            ok = vis.get("role") == "not_in_conclusion" and _nonempty(vis.get("reason")) and vis.get("visible_singularity_is_wcc") is True
        detail = "visibility role correct for family" if ok else "visibility missing or applied to wrong family"
    else:
        ok, detail = False, "visibility missing or not a mapping"
    res.add("R10", ok, detail)

    # R11 conclusion
    con = doc.get("conclusion")
    if _is_mapping(con):
        ctype = str(con.get("conclusion_type", ""))
        no_theorem = not (ctype == "theorem" and not _nonempty(con.get("artifact_refs")))
        ok = (
            ctype == EXPECTED_CONCLUSION_TYPE.get(cid)
            and con.get("epistemic_status") in CANON_EPISTEMIC
            and con.get("family") == fam
            and _nonempty(con.get("forbidden_strengthenings"))
            and no_theorem
        )
        detail = f"type={ctype!r} family={con.get('family')!r}" if ok else f"conclusion type/family inflated or mismatched (type={ctype!r})"
    else:
        ok, detail = False, "conclusion missing or not a mapping"
    res.add("R11", ok, detail)

    # R12 rev4: assertive paths only, sentence-local geodesic guard for inextendibility.
    # Path list is this worker's independent reading of "assertive content"; it includes the
    # paths the rev4 calibration widened to.
    ASSERTIVE_CANON = [
        ("conclusion", "statement_natural_language"), ("conclusion", "statement_formal"),
        ("conclusion", "conclusion_type"), ("conclusion", "equivalent_standard_formulation", "predicate"),
        ("conclusion", "equivalent_rephrasings"),
        ("visibility", "predicate_name"), ("visibility", "definition"),
        ("visibility", "negation_conclusion"), ("visibility", "visible_singularity_exists"),
        ("i_plus", "definition"), ("i_plus", "completeness_definition"), ("i_plus", "required_properties"),
        ("falsifier", "tier_1", "refutes"), ("falsifier", "tier_1", "witness_type"),
        ("falsifier", "tier_2", "refutes"), ("falsifier", "tier_2", "witness_type"),
        ("non_vacuity", "condition"), ("non_vacuity", "witness_type"),
        ("genericity", "generic_set"),
        ("extension_predicate", "definition"), ("extension_predicate", "frozen_regularity"),
    ]
    leaks: list[str] = []
    for p in ASSERTIVE_CANON:
        for s in _strings_at(doc, p):
            for sentence in _sentences(s):
                low = sentence.lower()
                if fam == "WCC":
                    hit = next((pat for pat in SCC_LEAK_PATTERNS if re.search(pat, sentence, re.IGNORECASE)), None)
                    if hit is None and "inextendib" in low and "geodesic" not in low:
                        hit = "inextendib(non-geodesic)"
                    if hit:
                        leaks.append(f"{'.'.join(p)}: {hit}")
                        break
                else:
                    hit = next((pat for pat in WCC_LEAK_PATTERNS if re.search(pat, sentence, re.IGNORECASE)), None)
                    if hit:
                        leaks.append(f"{'.'.join(p)}: {hit}")
                        break
    res.add("R12", not leaks, "no foreign-family token in assertive paths" if not leaks else f"foreign-family leak(s): {leaks[:3]}")

    # R13 composite regularity
    comp_scope = " ".join(
        [
            _as_text(_dig(doc, "class_components.regularity_token")),
            _as_text(_dig(doc, "regularity.extension_regularity")),
            _as_text(_dig(doc, "conclusion.conclusion_type")),
            _as_text(_dig(doc, "conclusion.statement_formal")),
        ]
    )
    m = COMPOSITE_RE.search(comp_scope) or ("C0" in comp_scope.upper() and "C2" in comp_scope.upper() and "REGULARITY_TOKEN" in comp_scope.upper())
    res.add("R13", not m, "no composite C0/C2 regularity" if not m else "composite/mixed C0-C2 regularity token present")

    # R14 falsifier structure
    fal = doc.get("falsifier")
    if _is_mapping(fal):
        t1, t2 = fal.get("tier_1"), fal.get("tier_2")
        t1_ok = _is_mapping(t1) and _nonempty(t1.get("witness_type")) and _nonempty(t1.get("machine_checkable_steps"))
        t2_ok = _is_mapping(t2) and _nonempty(t2.get("witness_type")) and (_nonempty(t2.get("labelling_required")) or "strengthen" in _as_text(t2.get("refutes")).lower())
        fam_ok = True
        if t1_ok:
            wt = _as_text(t1.get("witness_type")).lower()
            fam_ok = ("extension" in wt) if fam == "SCC" else ("visible" in wt or "geodesic" in wt)
        ok = t1_ok and t2_ok and fam_ok
        detail = "tier_1/tier_2 present and family-appropriate" if ok else "falsifier tiers missing, unlabelled, or wrong family"
    else:
        ok, detail = False, "falsifier missing or not a mapping"
    res.add("R14", ok, detail)

    # R15 provenance (rev4: overclaim clause)
    prov = doc.get("provenance")
    if _is_mapping(prov):
        cs = prov.get("citation_status")
        srcs = prov.get("sources")
        ok = cs in CANON_CITATION and "unresolved_citations" in prov
        if cs == "verified":
            ok = ok and isinstance(srcs, list) and len(srcs) > 0 and all(_nonempty(s.get("identifier")) for s in srcs if isinstance(s, dict))
        overclaims = []
        for s in (srcs or []) if isinstance(srcs, list) else []:
            blob = json.dumps(s, ensure_ascii=False, sort_keys=True)
            for sentence in _sentences(blob):
                m = OVERCLAIM_RE.search(sentence)
                if m and not _NEG_RE.search(sentence):
                    overclaims.append(m.group(0))
        if overclaims:
            ok = False
        detail = ("provenance status + unresolved list present, no overclaim" if ok
                  else f"source presented as establishing the class conclusion: {overclaims[:2]}" if overclaims
                  else "provenance citation_status invalid or verified without identified sources")
    else:
        ok, detail = False, "provenance missing or not a mapping"
    res.add("R15", ok, detail)

    # R16 SCC implication ledger (rev4: direction checks)
    if fam == "SCC":
        il = doc.get("implication_ledger")
        ok = _is_mapping(il) and _nonempty(il.get("one_way_entailments")) and _nonempty(il.get("forbidden_transfers"))
        direction: list[str] = []

        def _tokens(text: Any) -> str:
            t = str(text)
            out = ""
            if re.search(r"\bC0\b|C\^?0|continuous", t, re.IGNORECASE):
                out += "C0"
            if re.search(r"\bC2\b|C\^?2|twice", t, re.IGNORECASE):
                out += "C2"
            return out

        if _is_mapping(il):
            for e in il.get("one_way_entailments") or []:
                if isinstance(e, dict) and _tokens(e.get("from", "")) == "C2" and _tokens(e.get("to", "")) == "C0":
                    direction.append("one_way_entailments asserts forbidden converse C2=>C0")
            for e in il.get("forbidden_transfers") or []:
                if isinstance(e, dict) and _tokens(e.get("from", "")) == "C0" and _tokens(e.get("to", "")) == "C2":
                    direction.append("forbidden_transfers forbids the required C0=>C2 entailment")
        if direction:
            ok = False
        res.add("R16", ok, "implication ledger present, direction correct" if ok else (f"ledger direction error: {direction[:2]}" if direction else "implication_ledger missing one-way entailments or forbidden transfers"))
    else:
        res.add("R16", True, "not applicable to WCC")

    return res


def detect_layout(doc: Any) -> str:
    if not _is_mapping(doc):
        return "canonical"
    if doc.get("artifact_kind") == "class_schema" or _is_mapping(doc.get("class_components")):
        return "canonical"
    if _is_mapping(doc.get("quantifiers")) and "ordered" in doc["quantifiers"]:
        return "canonical"
    # worker-06 flat layout: deliberately routed to canonical to test spec conformance
    if "conclusion_type" in doc and isinstance(doc.get("topology"), str):
        return "canonical"
    return "own"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="class-binding conformance linter (draft, unverified)")
    ap.add_argument("paths", nargs="+", help="schema YAML/JSON files")
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    ap.add_argument("--layout", choices=["auto", "own", "canonical"], default="auto",
                    help="own = flash-11 fixture layout; canonical = FORM-RULE-SPEC R01-R16; auto detects")
    args = ap.parse_args(argv)

    exit_code = 0
    results = []
    for p in args.paths:
        path = Path(p)
        try:
            doc = load_document(path)
        except Exception as exc:  # noqa: BLE001 - report parse failures explicitly
            results.append({"path": str(path), "verdict": "ERROR", "layout": "-", "class_id": None, "failed_codes": ["LOAD_ERROR"], "checks": [{"code": "LOAD_ERROR", "ok": False, "detail": str(exc)}]})
            exit_code = max(exit_code, 2)
            continue
        layout = detect_layout(doc) if args.layout == "auto" else args.layout
        r = check_canonical(doc, str(path)) if layout == "canonical" else check(doc, str(path))
        record = r.to_dict()
        record["layout"] = layout
        results.append(record)
        exit_code = max(exit_code, 0 if r.verdict == "ACCEPT" else 1)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            mark = "ACCEPT" if r["verdict"] == "ACCEPT" else f"REJECT[{','.join(r['failed_codes'])}]"
            print(f"{mark:48s} [{r.get('layout','?')}] {r['path']}  class={r['class_id']}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
