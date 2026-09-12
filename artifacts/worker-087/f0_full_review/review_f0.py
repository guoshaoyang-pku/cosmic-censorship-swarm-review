#!/usr/bin/env python3
"""W087-F0-FULL-REVIEW-03: independent full-schema review instrument for F0 / gate G-F0.

Purpose
  Produce one independent reviewer verdict on the DECLARED F0 taxonomy at a pinned sha256,
  against the declared G-F0 criteria:
    (1) formulation_taxonomy.yaml exists;
    (2) exactly 4 separate class ids;
    (3) disjointness tests;
    (4) two independent reviewer verdicts (this instrument supplies one verdict, not two).
  The pre-rev5 findings (B-16F0-1/2/3, W082-F-01/02) are re-tested independently; the slot's
  earlier closure instrument is NOT imported or invoked.

Independence
  - Implements its own strict YAML loader (duplicate mapping keys are a hard error), its own
    normalization + merged-regularity scan, its own disjointness recomputation from parsed axes,
    its own cross-artifact resolution, and its own corpus checks.
  - Author-family tooling (artifacts/worker-01/validate_taxonomy.py,
    artifacts/flash-02/check_taxonomy_cases.py) is run only as recorded INPUT by the caller and
    is never imported; their outputs do not decide this verdict.
  - Fail-closed: a pin mismatch exits 2 and writes no report; a control failure exits 4.

Exit codes
  0 = all criterion (critical) checks pass  -> verdict accept
  2 = pin drift (expected pin != measured)  -> no report written
  3 = >=1 critical check failed             -> verdict revise
  4 = >=1 control failed                    -> report written, verdict withheld
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import itertools
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
CST = timezone(timedelta(hours=8))

TAX_PATH = "research_map/formulation_taxonomy.yaml"
RUBRIC_PATH = "evaluation_rubric.yaml"
CORPUS_PATH = "schemas/taxonomy_cases.jsonl"
FROZEN_PATH = "artifacts/formulation/FROZEN.json"
CATALOG_PATH = "artifacts/flash-02/leak_rule_catalog.json"

FROZEN_IDS = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]
SCHEMA_FOR_CLASS = {
    "AF-WCC-VAC-GEN": "schemas/af_wcc_vacuum.yaml",
    "AF-SCC-C2-VAC-GEN": "schemas/af_scc_c2_vacuum.yaml",
    "AF-SCC-C0-VAC-GEN": "schemas/af_scc_c0_vacuum.yaml",
}
SCHEMA_NODE = {
    "AF-WCC-VAC-GEN": "F1",
    "AF-SCC-C2-VAC-GEN": "F2a",
    "AF-SCC-C0-VAC-GEN": "F2b",
}
AXIS_NAMES = {
    "family",
    "matter_model",
    "symmetry",
    "asymptotics",
    "regularity_token",
    "genericity_kind",
    "conclusion_type",
}
CLASS_FILED_SENTINELS = {"COMPOSITE_C0_C2", "COMPOSITE_WCC_SCC"}
EXPECTED_CLASSIFICATION_SENTINELS = {"NO_CLASS_IN_TAXONOMY", "AMBIGUOUS_SPLIT_REQUIRED"}
MERGED_RE = re.compile(r"C0\s*(?:or|and|/|\+)\s*C2|C2\s*(?:or|and|/|\+)\s*C0", re.I)
HYP_RE = re.compile(r"([A-Z0-9-]+):(H\d+)")
SETBASED_MARKERS = (
    "contained in the union of j",
    "contained in j-(i+)",
    "contained-in-j-(i+)",
    "contained in j^-(i+)",
    "contained-in-j^-(i+)",
)
DISOWN_MARKERS = (
    "not a ",
    "not the ",
    "is not ",
    "are not ",
    "never ",
    "variant",
    "registered",
    "superseded",
    "withdrawn",
    "demoted",
    "rather than",
    "instead of",
    "strictly stronger",
    "no longer",
)
# Normalized (decoration-free) markers that excuse a merged-regularity token found in
# top-level prohibition/example/provenance text rather than in a class binding.
MERGED_EXEMPT_MARKERS = (
    "mustneverbemerged",
    "nomerge",
    "nosymmetryrelease",
    "suchas",
    "revisionnote",
    "distinctvalues",
    "schemaowner",
    "superseded",
    "downgrade",
    "notthisclass",
    "registeredasvariant",
    "withdrawn",
    "demoted",
)


def normalize_regularity(text: str) -> str:
    """Remove decoration that hides a merged regularity token (guards.G3 normalization)."""
    return re.sub(r"[\^_{}\s]", "", text)


def iter_strings(obj, path=()):
    """Yield (path, string) for every string nested anywhere inside obj."""
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from iter_strings(v, path + (str(k),))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from iter_strings(v, path + (str(i),))


class StrictLoader(yaml.SafeLoader):
    """SafeLoader that rejects duplicate mapping keys (silent shadowing is a real defect)."""


def _strict_mapping(loader: StrictLoader, node, deep=False):
    seen = []
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise yaml.constructor.ConstructorError(
                None, None, f"duplicate mapping key {key!r}", key_node.start_mark
            )
        seen.append(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


StrictLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _strict_mapping
)


def sha256_file(rel: str) -> str:
    p = ROOT / rel
    if not p.exists():
        return "MISSING"
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_yaml_text(text: str):
    return yaml.load(text, Loader=StrictLoader)


def parse_classification(raw: str):
    """Return ('class', id) | ('sentinel', token) | ('directive', text) | ('bad', raw)."""
    if not isinstance(raw, str):
        return ("bad", raw)
    for prefix, kind in (
        ("unique_class:", "class"),
        ("excluded_by:", "directive"),
        ("rejected_by:", "directive"),
    ):
        if raw.startswith(prefix):
            return (kind, raw[len(prefix):])
    if raw in EXPECTED_CLASSIFICATION_SENTINELS or raw in FROZEN_IDS:
        return ("class" if raw in FROZEN_IDS else "sentinel", raw)
    return ("bad", raw)


class Review:
    def __init__(self, tax, tax_text: str, ctx: dict):
        self.tax = tax
        self.tax_text = tax_text
        self.ctx = ctx
        self.checks: list[dict] = []

    def check(self, cid: str, group: str, ok: bool, detail: str, severity="critical"):
        self.checks.append(
            {"id": cid, "group": group, "severity": severity, "ok": bool(ok), "detail": detail}
        )
        return bool(ok)

    # ------------------------------------------------------------------ identity
    def run_identity(self):
        t = self.tax
        self.check("ID1", "identity", t.get("node_id") == "F0" and t.get("gate") == "G-F0",
                   f"node_id={t.get('node_id')!r} gate={t.get('gate')!r}")
        ids = t.get("class_ids")
        self.check("ID2", "identity", isinstance(ids, list) and len(ids) == 4 and len(set(ids)) == 4,
                   f"class_ids count/unique = {ids if not isinstance(ids, list) else (len(ids), len(set(ids)))}")
        self.check("ID3", "identity", sorted(ids or []) == sorted(FROZEN_IDS),
                   f"class_ids == frozen four: {sorted(ids or []) == sorted(FROZEN_IDS)}")
        classes = t.get("classes") or {}
        self.check("ID4", "identity", sorted(classes.keys()) == sorted(ids or []),
                   f"classes keys == class_ids; extra={sorted(set(classes)-set(ids or []))} missing={sorted(set(ids or [])-set(classes))}")
        # no class-id-like token admitted outside the frozen set
        variant_ids = {v.get("variant_id") for v in (t.get("variants") or [])}
        self.check("ID5", "identity", not (variant_ids & set(ids or [])),
                   f"no variant id is a class id (variants={sorted(variant_ids)})")
        self.check("ID6", "identity",
                   all(v.get("parent_class") in (ids or []) for v in (t.get("variants") or [])),
                   "every variant parent is a frozen class")
        rubric_ids = self.ctx.get("rubric_ids")
        self.check("ID7", "identity", rubric_ids is not None and sorted(rubric_ids) == sorted(ids or []),
                   f"evaluation_rubric.frozen_classes ids == taxonomy class_ids: {sorted(rubric_ids or [])}")
        corpus_ids = self.ctx.get("corpus_meta_ids")
        self.check("ID8", "identity", corpus_ids is not None and sorted(corpus_ids) == sorted(ids or []),
                   f"corpus meta class_ids == taxonomy class_ids: {sorted(corpus_ids or [])}")
        self.check("ID9", "identity",
                   t.get("claims_theorem_status") is False and t.get("status") == "draft_unverified",
                   f"no theorem status claim (claims_theorem_status={t.get('claims_theorem_status')!r}, status={t.get('status')!r})")

    # ------------------------------------------------------------------ structure
    def run_structure(self):
        t = self.tax
        required = ["label", "axes", "hypotheses", "conclusion", "exclusions", "test_cases", "provenance"]
        for cid in FROZEN_IDS:
            c = (t.get("classes") or {}).get(cid, {})
            missing = [k for k in required if k not in c]
            self.check(f"ST1.{cid}", "structure", not missing, f"{cid}: missing={missing}")
            hids = [h.get("id") for h in c.get("hypotheses", [])]
            self.check(f"ST2.{cid}", "structure", len(hids) == len(set(hids)) and all(hids),
                       f"{cid}: hypothesis ids={hids}")
            tc = c.get("test_cases") or {}
            self.check(f"ST3.{cid}", "structure",
                       "positive" in tc and "negative" in tc and all(
                           isinstance(tc[k], dict) and tc[k].get("expected_classification")
                           for k in ("positive", "negative")),
                       f"{cid}: test_cases keys={sorted(tc)}")
            owner = (c.get("provenance") or {}).get("schema_owner")
            self.check(f"ST4.{cid}", "structure", bool(owner), f"{cid}: schema_owner={owner!r}")
        for key in ("disjointness_scope", "disjointness_overlap_note"):
            self.check(f"ST5.{key}", "structure", bool(t.get(key)), f"{key} present={bool(t.get(key))}")

    # ------------------------------------------------------------------ vocabulary
    def run_vocab(self):
        t = self.tax
        fv = t.get("field_vocabulary") or {}
        for cid in FROZEN_IDS:
            axes = ((t.get("classes") or {}).get(cid) or {}).get("axes") or {}
            unknown = sorted(set(axes) - AXIS_NAMES)
            self.check(f"V1.{cid}", "vocabulary", not unknown, f"{cid}: unknown axes={unknown}")
            allowed_checks = {
                "family": fv.get("family", {}).get("allowed"),
                "matter_model": fv.get("matter_model", {}).get("allowed"),
                "symmetry": fv.get("symmetry", {}).get("allowed"),
                "asymptotics": fv.get("asymptotics", {}).get("allowed"),
                "regularity_token": fv.get("regularity_token", {}).get("allowed"),
                "genericity_kind": fv.get("genericity_kind", {}).get("allowed"),
                "conclusion_type": fv.get("conclusion_type", {}).get("allowed"),
            }
            bad = {k: axes.get(k) for k, allowed in allowed_checks.items()
                   if allowed is not None and axes.get(k) not in allowed}
            self.check(f"V2.{cid}", "vocabulary", not bad, f"{cid}: out-of-vocabulary axis values={bad}")
            conc = ((t.get("classes") or {}).get(cid) or {}).get("conclusion") or {}
            self.check(f"V3.{cid}", "vocabulary", conc.get("type") == axes.get("conclusion_type"),
                       f"{cid}: conclusion.type={conc.get('type')!r} axes.conclusion_type={axes.get('conclusion_type')!r}")
        top = fv.get("genericity_kind", {}).get("allowed") or []
        self.check("V4", "vocabulary", "unresolved" in top and "provisional_baire_residual" in top,
                   "genericity vocabulary declares unresolved and provisional_baire_residual")

    # ------------------------------------------------------------------ G2 / G3
    def run_guards_g2_g3(self):
        t = self.tax
        for cid in FROZEN_IDS:
            axes = ((t.get("classes") or {}).get(cid) or {}).get("axes") or {}
            fam, tok = axes.get("family"), axes.get("regularity_token")
            if fam == "SCC":
                ok = tok in ("C0", "C2")
            else:
                ok = tok is None
            self.check(f"G2.{cid}", "guards", ok, f"{cid}: family={fam!r} regularity_token={tok!r}")
        # G3 class-binding scan: no merged-regularity token anywhere under `classes:`
        bound_hits = [(path, s[:90]) for path, s in iter_strings(t.get("classes") or {})
                      if MERGED_RE.search(normalize_regularity(s))]
        self.check("G3.classbound", "guards", not bound_hits,
                   f"merged-regularity tokens in the classes subtree={bound_hits}")
        # G3 raw scan is retained for coverage, but a raw hit is excused only when it sits in
        # declared prohibition/example/provenance text (contexts are recorded for audit).
        raw = normalize_regularity(self.tax_text)
        raw_hits, bad_raw = [], []
        for m in MERGED_RE.finditer(raw):
            ctx = raw[max(0, m.start() - 170): m.end() + 170]
            exempt = any(marker in ctx for marker in MERGED_EXEMPT_MARKERS)
            raw_hits.append({"token": m.group(0), "exempt": exempt, "context": ctx})
            if not exempt:
                bad_raw.append(m.group(0))
        self.check("G3.raw", "guards", not bad_raw,
                   f"raw merged-token occurrences all in prohibition/provenance context "
                   f"(n={len(raw_hits)}, unexpected={bad_raw})")

    # ------------------------------------------------------------------ conclusions
    def run_conclusions(self):
        t = self.tax
        fam_map = {"WCC": {"weak_cosmic_censorship"},
                   "SCC": {"strong_cosmic_censorship_C2", "strong_cosmic_censorship_C0"}}
        for cid in FROZEN_IDS:
            c = (t.get("classes") or {}).get(cid) or {}
            axes = c.get("axes") or {}
            text = str((c.get("conclusion") or {}).get("text", ""))
            ntext = re.sub(r"\s+", " ", text)
            fam = axes.get("family")
            self.check(f"C1.{cid}", "conclusion",
                       (c.get("conclusion") or {}).get("type") in fam_map.get(fam, set()),
                       f"{cid}: conclusion type {axes.get('conclusion_type')!r} consistent with family {fam!r}")
            # comeager binder bound before the data reference
            low = ntext.lower()
            ci = low.find("comeager set")
            data_idx = min([i for i in (low.find("for every data set"), low.find("every member"),
                                        low.find("for every\n")) if i >= 0] or [-1])
            self.check(f"C2.{cid}", "conclusion", ci >= 0 and data_idx > ci,
                       f"{cid}: comeager binder at {ci}, data quantifier at {data_idx}")
            if fam == "WCC":
                tail = "tail" in low
                single_q = "single-q" in low and tail
                negated_tail = tail and ("not contained in j^-(q)" in low or "not contained in j-(q)" in low)
                self.check(f"C3.{cid}", "conclusion", single_q or negated_tail,
                           f"{cid}: canonical tail predicate present (single-q={single_q}, "
                           f"explicit negation={negated_tail})")
                hits = []
                for sent in re.split(r"(?<=[.;])\s+", ntext):
                    s = sent.lower()
                    if any(p in s for p in SETBASED_MARKERS):
                        hits.append({"sentence": sent[:150],
                                     "disowned": any(d in s for d in DISOWN_MARKERS)})
                assertive = [h for h in hits if not h["disowned"]]
                self.check(f"C4.{cid}", "conclusion", not assertive,
                           f"{cid}: no assertive set-based visibility predicate "
                           f"(mentions={len(hits)}, all_disowned={not assertive})")
            self.check(f"C5.{cid}", "conclusion",
                       bool((c.get("conclusion") or {}).get("forbidden_inflation")),
                       f"{cid}: forbidden_inflation present")

    # ------------------------------------------------------------------ disjointness
    def run_disjointness(self):
        t = self.tax
        rows = t.get("disjointness") or []
        pairs = [tuple(sorted(r.get("pair") or [])) for r in rows]
        expected = {tuple(sorted(p)) for p in itertools.combinations(FROZEN_IDS, 2)}
        self.check("D1", "disjointness", len(pairs) == 6 and set(pairs) == expected and len(set(pairs)) == 6,
                   f"exactly the 6 unordered frozen pairs (n={len(pairs)}, unique={len(set(pairs))})")
        diff_fail, axis_bad = [], []
        axes_by_class = {cid: ((t.get("classes") or {}).get(cid) or {}).get("axes") or {} for cid in FROZEN_IDS}
        for r in rows:
            pair = tuple(sorted(r.get("pair") or []))
            dec = r.get("decisive_axes") or []
            if not dec or not set(dec) <= AXIS_NAMES:
                axis_bad.append((pair, dec))
                continue
            a, b = axes_by_class.get(pair[0], {}), axes_by_class.get(pair[1], {})
            if not any(a.get(k) != b.get(k) for k in dec):
                diff_fail.append((pair, dec))
        self.check("D2", "disjointness", not axis_bad, f"every pair names valid decisive axes; bad={axis_bad}")
        self.check("D3", "disjointness", not diff_fail,
                   f"every pair differs on >=1 named decisive axis; failures={diff_fail}")

    # ------------------------------------------------------------------ transfer rules / guards
    def run_transfer_guards(self):
        t = self.tax
        tr = t.get("transfer_rules") or {}
        allowed = tr.get("allowed") or []
        forbidden = tr.get("forbidden") or []
        ok_allowed = all(a.get("from") in FROZEN_IDS and a.get("to") in FROZEN_IDS
                         and a.get("guards") for a in allowed)
        self.check("T1", "transfer", ok_allowed, f"allowed transfers class-bound with guards: {[(a.get('from'),a.get('to')) for a in allowed]}")
        self.check("T2", "transfer",
                   all(a.get("from") == "AF-SCC-C0-VAC-GEN" and a.get("to") == "AF-SCC-C2-VAC-GEN" for a in allowed),
                   "only sound direction C0 -> C2 is allowed")
        self.check("T3", "transfer",
                   {f.get("id") for f in forbidden} >= {"X1", "X2", "X3", "X4", "X5"},
                   f"forbidden leakage patterns present={sorted(f.get('id') for f in forbidden)}")
        guards = {g.get("id"): g.get("rule") for g in (t.get("guards") or [])}
        self.check("GU1", "guards", all(guards.get(f"G{i}") for i in range(1, 8)),
                   f"guards G1..G7 present={sorted(guards)}")

    # ------------------------------------------------------------------ cross-artifact
    def run_xref(self):
        t = self.tax
        schemas = self.ctx.get("schemas") or {}
        for cid, rel in SCHEMA_FOR_CLASS.items():
            d = schemas.get(cid)
            self.check(f"X1.{cid}", "xref", isinstance(d, dict),
                       f"{rel} parses: {isinstance(d, dict)}")
            if isinstance(d, dict):
                self.check(f"X2.{cid}", "xref",
                           d.get("class_id") == cid and d.get("node_id") == SCHEMA_NODE[cid],
                           f"{rel}: class_id={d.get('class_id')!r} node_id={d.get('node_id')!r}")
                fb = d.get("f0_binding") or {}
                self.check(f"X2b.{cid}", "xref",
                           fb.get("declared_f0_sha256") == self.ctx["measured"][TAX_PATH],
                           f"{rel}: f0_binding.declared_f0_sha256={str(fb.get('declared_f0_sha256'))[:12]} "
                           f"vs measured {self.ctx['measured'][TAX_PATH][:12]}")
        cases = self.ctx.get("corpus_cases") or []
        bad_filed, bad_hyp, bad_axis, bad_classref = [], [], [], []
        for c in cases:
            if c.get("as_filed_class_id") not in set(FROZEN_IDS) | CLASS_FILED_SENTINELS:
                bad_filed.append(c.get("case_id"))
            for cid_ref, hid in HYP_RE.findall(str(c.get("decisive_hypothesis", ""))):
                cids = (t.get("classes") or {}).get(cid_ref) or {}
                if not any(h.get("id") == hid for h in cids.get("hypotheses", [])):
                    bad_hyp.append((c.get("case_id"), f"{cid_ref}:{hid}"))
            if c.get("polarity") == "positive" and c.get("class_id") in axes_all(t):
                if c.get("axis_vector") != ((t.get("classes") or {}).get(c["class_id"]) or {}).get("axes"):
                    bad_axis.append(c.get("case_id"))
            kind, val = parse_classification(c.get("expected_classification"))
            if kind == "bad":
                bad_classref.append((c.get("case_id"), c.get("expected_classification")))
        self.check("X3", "xref", not bad_filed, f"corpus as_filed ids frozen-or-sentinel; bad={bad_filed}")
        self.check("X4", "xref", not bad_hyp, f"corpus hypothesis refs resolve; bad={bad_hyp}")
        self.check("X5", "xref", not bad_axis, f"positive corpus axis_vector equals class axes; bad={bad_axis}")
        self.check("X6", "xref", not bad_classref, f"corpus expected_classification parses; bad={bad_classref}")
        counts = self.ctx.get("corpus_counts") or {}
        self.check("X7", "xref", counts.get("positive") == 16 and counts.get("negative") == 20,
                   f"corpus polarity counts {counts}")
        # FROZEN rev pins both F0 logical artifacts explicitly
        frozen = self.ctx.get("frozen") or {}
        logical = frozen.get("logical_artifacts") or {}
        self.check("X8", "xref",
                   logical.get("F0-declared-taxonomy", {}).get("sha256") == self.ctx["measured"][TAX_PATH]
                   and bool(logical.get("F0-class-contract-supplement", {}).get("sha256")),
                   "FROZEN.logical_artifacts pins declared taxonomy at the measured hash and the supplement separately")

    # ------------------------------------------------------------------ binding hygiene (findings only)
    def run_binding(self):
        ctx = self.ctx
        prefix = ctx["measured"][TAX_PATH][:12]
        stale = [c.get("case_id") for c in (ctx.get("corpus_cases") or [])
                 if prefix not in str(c.get("binding_status", ""))]
        self.check("B1", "binding", not stale,
                   f"corpus per-row binding_status carries measured prefix {prefix}; stale rows={len(stale)}",
                   severity="finding")
        cat = ctx.get("catalog") or {}
        cat_ref = (cat.get("taxonomy_ref") or {}).get("sha256")
        self.check("B2", "binding", cat_ref == ctx["measured"][TAX_PATH],
                   f"leak_rule_catalog.taxonomy_ref={str(cat_ref)[:12]} vs measured {prefix}",
                   severity="finding")
        # scalar genericity deferral vs comeager binder
        scalar = ((self.tax.get("classes") or {}).get("AF-WCC-SCALAR-SPH") or {})
        axes = scalar.get("axes") or {}
        self.check("B3", "binding",
                   not (axes.get("genericity_kind") == "unresolved"
                        and "comeager set" in str((scalar.get("conclusion") or {}).get("text", "")).lower()),
                   "AF-WCC-SCALAR-SPH: axes.genericity_kind=unresolved while the conclusion uses a comeager binder "
                   "(declared deferral: genericity_value_status=unresolved_pending_L1, H4.unresolved, CG1/Q1; no F-node owns the class)",
                   severity="finding")
        open_cases = [c.get("case_id") for c in (ctx.get("corpus_cases") or []) if c.get("open")]
        self.check("B4", "binding", not open_cases,
                   f"corpus cases still open={len(open_cases)}",
                   severity="finding")
        supplement_sha = ctx["measured"].get(
            "artifacts/formulation/formulation_taxonomy.yaml",
            sha256_file("artifacts/formulation/formulation_taxonomy.yaml"),
        )
        pinners = []
        for cid, d in (ctx.get("schemas") or {}).items():
            fb = (d or {}).get("f0_binding") or {}
            pinned = str(fb.get("class_contract_supplement_sha256", "")) == supplement_sha
            pinners.append((cid, pinned))
        self.check("B5", "binding", all(p for _, p in pinners),
                   "every frozen schema pins the class-contract supplement sha256 in f0_binding "
                   f"(CF-7 open repair; per-schema={pinners}, supplement={supplement_sha[:12]})",
                   severity="finding")


def axes_all(t):
    return set((t.get("classes") or {}).keys())


# ---------------------------------------------------------------------- fixtures / controls
def fixture_duplicate_key(text: str):
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if ln.startswith("schema_version:"):
            lines.insert(i + 1, ln)
            return "\n".join(lines) + "\n"
    raise RuntimeError("no schema_version line")


def fixture_merged_regularity(tax):
    t = copy.deepcopy(tax)
    t["classes"]["AF-WCC-VAC-GEN"]["label"] += " (C0 or C2)"
    return t


def fixture_disjointness_collapse(tax):
    t = copy.deepcopy(tax)
    t["classes"]["AF-WCC-SCALAR-SPH"]["axes"]["matter_model"] = "vacuum"
    t["classes"]["AF-WCC-SCALAR-SPH"]["axes"]["symmetry"] = "none_assumed"
    return t


def fixture_setbased_conclusion(tax):
    t = copy.deepcopy(tax)
    t["classes"]["AF-WCC-SCALAR-SPH"]["conclusion"]["text"] = (
        "For a comeager set G of data in the class, every member's MGHD admits I+ and every "
        "future-inextendible causal geodesic is contained in J-(I+): it is visible from I+."
    )
    return t


def fixture_five_classes(tax):
    t = copy.deepcopy(tax)
    t["class_ids"].append("AF-EXTRA-CLASS")
    return t


def run_controls(tax, tax_text, ctx):
    out = []

    def add(name, ok, detail):
        out.append({"id": name, "ok": bool(ok), "detail": detail})

    # 1. duplicate key fixture must be rejected by the strict loader
    try:
        load_yaml_text(fixture_duplicate_key(tax_text))
        add("CTL-1-duplicate-key", False, "strict loader accepted a duplicated mapping key")
    except yaml.constructor.ConstructorError:
        add("CTL-1-duplicate-key", True, "strict loader rejected the duplicated key")
    except Exception as exc:  # noqa: BLE001
        add("CTL-1-duplicate-key", False, f"unexpected exception {type(exc).__name__}: {exc}")

    # 2. merged-regularity fixture must trip G3.classbound (and the raw scan)
    r = Review(fixture_merged_regularity(tax), tax_text, ctx)
    r.run_guards_g2_g3()
    add("CTL-2-merged-regularity",
        any(c["id"].startswith("G3") and not c["ok"] for c in r.checks),
        "merged-regularity fixture is detected by G3")

    # 3. collapsed-disjointness fixture must trip D3
    r = Review(fixture_disjointness_collapse(tax), tax_text, ctx)
    r.run_disjointness()
    add("CTL-3-disjointness-collapse",
        any(c["id"] == "D3" and not c["ok"] for c in r.checks),
        "collapsed-axis fixture is detected by D3")

    # 4. set-based scalar conclusion fixture must trip C4
    r = Review(fixture_setbased_conclusion(tax), tax_text, ctx)
    r.run_conclusions()
    add("CTL-4-setbased-conclusion",
        any(c["id"] == "C4.AF-WCC-SCALAR-SPH" and not c["ok"] for c in r.checks),
        "pre-rev5 set-based fixture is detected by C4")

    # 5. five-class fixture must trip the identity checks
    r = Review(fixture_five_classes(tax), tax_text, ctx)
    r.run_identity()
    add("CTL-5-five-classes",
        any(c["id"] in ("ID2", "ID3") and not c["ok"] for c in r.checks),
        "five-class fixture is detected by ID2/ID3")

    # 6. determinism: two runs over identical inputs produce identical check outcomes
    a = canonical_outcomes(Review(tax, tax_text, ctx))
    b = canonical_outcomes(Review(copy.deepcopy(tax), tax_text, ctx))
    add("CTL-6-determinism", a == b, "two in-process runs give identical check outcomes")

    # 7. specificity: the canonical disowned set-based mention must NOT be flagged by C4
    r = Review(tax, tax_text, ctx)
    r.run_conclusions()
    add("CTL-7-disowned-mention-not-flagged",
        all(c["ok"] for c in r.checks if c["id"].startswith("C4")),
        "canonical disowned set-based mentions pass C4 (over-flagging regression guard)")
    return out


def canonical_outcomes(review: Review):
    for fn in (review.run_identity, review.run_structure, review.run_vocab,
               review.run_guards_g2_g3, review.run_conclusions, review.run_disjointness,
               review.run_transfer_guards, review.run_xref, review.run_binding):
        fn()
    return json.dumps([(c["id"], c["ok"]) for c in review.checks], sort_keys=False)


# ---------------------------------------------------------------------- main
def build_context(expected_pin: str):
    measured = {TAX_PATH: sha256_file(TAX_PATH)}
    ctx = {"measured": measured}
    rubric = load_yaml_text((ROOT / RUBRIC_PATH).read_text())
    ctx["rubric_ids"] = [c.get("id") for c in rubric.get("frozen_classes", [])]
    rows = [json.loads(l) for l in (ROOT / CORPUS_PATH).read_text().splitlines() if l.strip()]
    meta = next(r for r in rows if r.get("record_type") == "meta")
    cases = [r for r in rows if r.get("record_type") == "case"]
    ctx["corpus_meta_ids"] = meta.get("class_ids")
    ctx["corpus_cases"] = cases
    ctx["corpus_counts"] = meta.get("counts") or {}
    ctx["corpus_meta_ref"] = (meta.get("taxonomy_ref") or {}).get("sha256")
    ctx["schemas"] = {}
    for rel in SCHEMA_FOR_CLASS.values():
        ctx["schemas"][next(k for k, v in SCHEMA_FOR_CLASS.items() if v == rel)] = load_yaml_text(
            (ROOT / rel).read_text()
        )
    ctx["frozen"] = json.loads((ROOT / FROZEN_PATH).read_text())
    ctx["catalog"] = json.loads((ROOT / CATALOG_PATH).read_text())
    return ctx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--expect-pin", required=True, help="expected sha256 of the declared F0 taxonomy")
    ap.add_argument("--report", default=str(Path(__file__).with_name("report.json")))
    args = ap.parse_args()

    tax_text = (ROOT / TAX_PATH).read_text()
    measured = sha256_file(TAX_PATH)
    if measured != args.expect_pin:
        print(f"DRIFT: measured {measured} != expected {args.expect_pin}", file=sys.stderr)
        return 2
    tax = load_yaml_text(tax_text)
    ctx = build_context(args.expect_pin)

    review = Review(tax, tax_text, ctx)
    for fn in (review.run_identity, review.run_structure, review.run_vocab,
               review.run_guards_g2_g3, review.run_conclusions, review.run_disjointness,
               review.run_transfer_guards, review.run_xref, review.run_binding):
        fn()
    controls = run_controls(tax, tax_text, ctx)

    critical_failed = [c for c in review.checks if c["severity"] == "critical" and not c["ok"]]
    findings = [c for c in review.checks if c["severity"] != "critical" and not c["ok"]]
    controls_failed = [c for c in controls if not c["ok"]]

    if controls_failed:
        verdict = "withheld_control_failure"
        reason = f"{len(controls_failed)} control(s) failed"
    elif critical_failed:
        verdict = "revise"
        reason = f"{len(critical_failed)} critical check(s) failed: {[c['id'] for c in critical_failed]}"
    else:
        verdict = "accept"
        reason = (f"all {len([c for c in review.checks if c['severity']=='critical'])} critical checks pass "
                  f"at the pinned bytes; {len(findings)} non-blocking finding(s) recorded")

    report = {
        "instrument": "w087-f0-full-review/1.0",
        "task_id": "W087-F0-FULL-REVIEW-03",
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "target": {"node_id": "F0", "gate_id": "G-F0", "path": TAX_PATH, "sha256": measured},
        "pins": {
            "rubric": {RUBRIC_PATH: sha256_file(RUBRIC_PATH)},
            "corpus": {CORPUS_PATH: sha256_file(CORPUS_PATH)},
            "frozen": {FROZEN_PATH: sha256_file(FROZEN_PATH)},
            "schemas": {rel: sha256_file(rel) for rel in SCHEMA_FOR_CLASS.values()},
        },
        "criteria": [
            "declared taxonomy exists and parses at the pinned sha256",
            "exactly the four frozen class ids, separate, cross-artifact consistent",
            "disjointness: the six pairs differ on recomputed named decisive axes",
            "one independent reviewer verdict (this instrument); two are required for G-F0",
        ],
        "checks": review.checks,
        "controls": controls,
        "findings": findings,
        "critical_failures": [c["id"] for c in critical_failed],
        "verdict": verdict,
        "verdict_reason": reason,
        "scope_limits": [
            "worker verdict, advisory: it cannot set node status, validation_status=passed, or a gate verdict",
            "no mathematical/citation correctness adjudicated; no theorem or class-semantics decision",
            "binds only the declared taxonomy sha256 above; the class-contract supplement is not reviewed here",
        ],
        "falsifier": (
            "Re-run review_f0.py --expect-pin " + measured + ": any critical check flipping to fail, any "
            "control failing, or the measured hash drifting voids the verdict. Independently: a reader who "
            "exhibits a merged C0/C2 or WCC/SCC class binding, a disjointness pair that shares all named "
            "decisive axis values, an assertive set-based visibility predicate in a WCC conclusion, or a "
            "non-frozen class id used as a class refutes the corresponding PASS."
        ),
    }
    Path(args.report).write_text(json.dumps(report, indent=1, sort_keys=False) + "\n")
    print(json.dumps({
        "verdict": verdict,
        "critical_failures": [c["id"] for c in critical_failed],
        "findings": [c["id"] for c in findings],
        "controls_failed": [c["id"] for c in controls_failed],
        "report": args.report,
    }, indent=1))
    return 4 if controls_failed else (3 if critical_failed else 0)


if __name__ == "__main__":
    sys.exit(main())
