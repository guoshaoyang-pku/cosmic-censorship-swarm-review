#!/usr/bin/env python3
"""FORM-QNF-06 - quantifier normal-form (QNF) extractor + negation well-formedness.

Task  : assign-FORM-QNF-06-20260911T2331 (astra-lead-formulation -> flash-17)
Gate  : G-CLASSBIND
Scope : AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN

What this tool does (acceptance tests Q1-Q5 of the assignment):

  Q1  extract quantifiers.ordered into a normal form
      (index, kind, binder, domain_id) + conclusion predicate + free variables
  Q2  emit a MACHINE-GENERATED negation of the quantifier prefix and check that
      no free variable escapes its binder; the negation must name the witness a
      falsifier has to exhibit
  Q3  check that quantifier ORDER is asserted non-commutative where it matters
      (the comeager-set witness is fixed before/independently of the data)
  Q4  check witness typing: SCC negation must be an EXTENSION witness, WCC
      negation a VISIBLE INCOMPLETE CAUSAL GEODESIC
  Q5  emit per-schema {qnf_ok, negation_ok, order_flag, mismatch_paths}

Non-duplication: FORM-GATE-01 (artifacts/formulation/tools/run_gate_tests.py,
check_class_schema.py R03/R27) asserts that quantifier fields exist and are
ordered.  This tool is the semantic layer on top: it *extracts* the normal form,
*generates* the negation mechanically, cross-checks the declared
negation/quantifier_class/normal-form against that machine form, and runs the
trivial-witness falsifier of the assignment.

Falsifier of this task (from the assignment card):
  "If the extracted negation of a canonical schema is satisfiable by a trivial
   witness (e.g. 'no data exist'), the schema is vacuous; report the path."
  -> implemented as check C7 (trivial_witness_excluded); a failure is reported
     in mismatch_paths with the exact YAML path.

Honesty contract: the report carries validation_status="draft_unverified" and
claims nothing about the mathematics; it is a machine check of schema syntax
and of the declared negation against the machine-generated one.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.stderr.write("PyYAML is required\n")
    raise

TOOL_VERSION = "1.1.0"  # 1.1.0: C2k accepts the literal domain id as naming the
# domain a quantifier ranges over (rev12 renamed the D0 binder from "(s,delta)"
# to the tagged index "r", so "there exists r in D0" is a correct domain naming).
CST = timezone(timedelta(hours=8))
ROOT = Path(__file__).resolve().parents[3]  # .../workdir/ai4math-swarm
DEFAULT_SCHEMAS = [
    "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
]

# ---------------------------------------------------------------------------
# Declared vocabularies.  Anything in these sets is NOT reported as a free
# variable; the sets are echoed into the report so a reviewer can audit them.
# ---------------------------------------------------------------------------
CONTEXT_SYMBOLS = {
    # ambient space / data
    "X", "AF", "vac", "MGHD", "D",
    # boundary and causal operators
    "I", "I+", "I-", "i0", "J", "J+", "J-", "B",
    # manifolds and fields that are introduced by "letting" or by the class
    "M", "g", "Mtilde", "gtilde", "Omega", "iota",
    # carriers
    "R", "S",
    # domains
    "D0", "D1", "D2", "D3", "D4", "D5",
}
# statement_formal uses D for the data set while quantifiers.ordered names it
# (Sigma,h,K); this alias is declared, not inferred.
DECLARED_ALIASES = {"D": "data-set alias for the (Sigma,h,K) binder (domain D2)"}
STOPWORDS = {
    "forall", "exists", "not", "and", "or", "in", "be", "is", "are", "such",
    "that", "the", "a", "an", "with", "of", "for", "every", "some", "there",
    "letting", "let", "comeager", "meager", "non", "empty", "complete",
    "class", "data", "set", "space", "if", "then", "iff", "where", "which",
    "whose", "holds", "has", "have", "it", "its", "by", "at", "on", "to",
}
KIND_FLIP = {"forall": "exists", "exists": "forall", "not_exists": "exists"}
VALID_KINDS = set(KIND_FLIP)

# Per-family required witness vocabulary for the declared negation (Q4).
WITNESS_VOCAB = {
    "WCC": {
        "must_contain": ["visible", "geodesic", "finite affine"],
        "witness_name": "visible incomplete causal geodesic",
    },
    "SCC": {
        "must_contain": ["extension"],
        "witness_name": "proper future extension",
    },
}

# Concepts a declared negation must name for each domain of the machine prefix
# (check C2k).  D3 is family-dependent: a completion for WCC, an extension for
# SCC.  These are checked against the lowercased declared negation text.
DOMAIN_CONCEPT = {
    "D0": ["(s,delta)", "s,delta", "s, delta"],
    "D1": ["comeager"],
    "D2": ["(sigma,h,k)", "data"],
    "D3": {"WCC": ["completion"], "SCC": ["extension"],
           "default": ["completion", "extension"]},
    "D4": ["geodesic"],
    "D5": ["i+", "q"],
}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def now_iso() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def norm_kind(s: str) -> str:
    return s.strip().lower().replace("-", "_").replace(" ", "_")


def norm_class_string(s: str) -> str:
    """Normalise a quantifier_class string for comparison with the machine one.

    'forall-exists(comeager)-forall-not-exists(extension)'
      -> 'forall-exists-forall-not-exists'
    """
    s = re.sub(r"\([^)]*\)", "", s.lower())
    s = s.replace("_", "-")
    return "-".join(t for t in s.split("-") if t)


def normalize_var(v: str) -> str:
    return v.strip().strip("()").strip()


def parse_binder(binder: str):
    """Return (vars, indices) for a binder string.

    '(s,delta)' -> (['s','delta'], [])
    'G_{s,delta}' -> (['G'], ['s','delta'])
    "gamma" -> (['gamma'], [])
    """
    b = binder.strip()
    indices: list[str] = []
    m = re.search(r"_\{([^}]*)\}", b)
    if m:
        indices = [x.strip() for x in m.group(1).split(",") if x.strip()]
        b = b[: m.start()] + b[m.end():]
    b = b.strip()
    if b.startswith("(") and b.endswith(")"):
        parts = [x.strip() for x in b[1:-1].split(",")]
    else:
        parts = [b]
    return [p.strip() for p in parts if p.strip()], indices


def tokenize(text: str):
    """Identifier tokens, keeping subscripted names as one token.

    The trailing optional group keeps 'G_{s,delta}' and 'AF_{I+}' intact; an
    earlier greedy form returned 'G_' / 'AF_' and produced false free-variable
    escapes (caught by self-test M3).
    """
    return re.findall(r"[A-Za-z][A-Za-z0-9_'+\-]*(?:\{[^}]*\})?", text or "")


def split_subscript(tok: str):
    m = re.match(r"^([A-Za-z][A-Za-z0-9_'+\-]*?)_(?:\{([^}]*)\}|([A-Za-z0-9'+\-]+))$", tok)
    if not m:
        return tok, []
    base, a, b = m.group(1), m.group(2), m.group(3)
    idx = a if a is not None else b
    return base, [x.strip() for x in idx.split(",") if x.strip()]


def collect_predicates(d: dict) -> set[str]:
    preds = set()
    for path in (
        ("visibility", "predicate_name"),
        ("extension_predicate", "name"),
        ("conclusion", "conclusion_type"),
    ):
        node = d
        for k in path:
            node = node.get(k) if isinstance(node, dict) else None
        if isinstance(node, str) and node:
            preds.add(node)
    return preds


def let_bound_names(formal: str) -> set[str]:
    names: set[str] = set()
    for m in re.finditer(r"letting\s*\(([^)]*)\)\s*be", formal):
        names.update(x.strip() for x in m.group(1).split(",") if x.strip())
    for m in re.finditer(r"letting\s+([A-Za-z][A-Za-z0-9_'+\-]*)\s+be", formal):
        names.add(m.group(1))
    return names


def classify_free_variables(d: dict, qnf: list[dict]) -> dict:
    """Q1/Q2: classify every variable-like token of conclusion.statement_formal."""
    formal = str((d.get("conclusion") or {}).get("statement_formal") or "")
    qformal = str((d.get("quantifiers") or {}).get("formal") or "")
    bound: set[str] = set()
    for q in qnf:
        vs, idxs = parse_binder(q["binder"])
        bound.update(vs)
        bound.update(idxs)
    letb = let_bound_names(qformal) | let_bound_names(formal)
    preds = collect_predicates(d)
    escapes, classified = [], []
    for tok in tokenize(formal):
        if tok in STOPWORDS:
            continue
        base, idxs = split_subscript(tok)
        if tok in bound or base in bound or tok in letb or tok in DECLARED_ALIASES:
            kind = "bound" if (tok in bound or base in bound) else ("let_bound" if tok in letb else "alias")
        elif base in CONTEXT_SYMBOLS and all(i in bound or i in CONTEXT_SYMBOLS for i in idxs):
            kind = "derived" if idxs else "context"
        elif tok in preds or (re.search(re.escape(tok) + r"\s*\(", formal) and base not in CONTEXT_SYMBOLS):
            kind = "predicate"
        elif base in CONTEXT_SYMBOLS:
            kind = "context"
        else:
            kind = "escape"
            escapes.append({"token": tok, "path": "conclusion.statement_formal"})
        classified.append({"token": tok, "class": kind})
    return {
        "bound": sorted(bound),
        "let_bound": sorted(letb),
        "aliases": DECLARED_ALIASES,
        "predicates": sorted(preds),
        "context_vocabulary": sorted(CONTEXT_SYMBOLS),
        "tokens": classified,
        "escapes": escapes,
        "free_variables_ok": not escapes,
    }


def machine_negation(qnf: list[dict]) -> dict:
    """Q2: mechanically negate the quantifier prefix (flip each kind)."""
    flipped = [
        {"index": q["index"], "kind": KIND_FLIP[q["kind"]], "binder": q["binder"], "domain_id": q["domain_id"]}
        for q in qnf
    ]
    signature = " > ".join(f"{q['kind']}({q['binder']})@{q['domain_id']}" for q in flipped)
    compact = " > ".join(f"{q['kind'][0].upper()}{q['index']}" for q in flipped)
    return {"flipped_prefix": flipped, "signature": signature, "compact_signature": compact}


def _find_quantifier(qnf, *, kind=None, domain=None, binder_startswith=None):
    for q in qnf:
        if kind and q["kind"] != kind:
            continue
        if domain and q["domain_id"] != domain:
            continue
        if binder_startswith and not normalize_var(q["binder"]).startswith(binder_startswith):
            continue
        return q
    return None


def check_order(qnf: list[dict], d: dict) -> dict:
    """Q3: the comeager witness must precede and not depend on the data."""
    mismatches = []
    order_matters = (d.get("quantifiers") or {}).get("order_matters") is True
    if not order_matters:
        mismatches.append({"path": "quantifiers.order_matters", "check": "C4a",
                           "expected": True, "found": (d.get("quantifiers") or {}).get("order_matters")})
    first = qnf[0] if qnf else None
    if first and not (first["kind"] == "forall" and first["domain_id"] == "D0"):
        mismatches.append({"path": "quantifiers.ordered[0]", "check": "C4j",
                           "expected": "the class-parameter forall (s,delta) over D0 comes first",
                           "found": f"{first['kind']} {first['binder']}@{first['domain_id']}"})
    comeager = _find_quantifier(qnf, kind="exists", domain="D1") or _find_quantifier(qnf, kind="exists", binder_startswith="G")
    data = _find_quantifier(qnf, kind="forall", domain="D2")
    if comeager is None:
        mismatches.append({"path": "quantifiers.ordered", "check": "C4b", "expected": "exists G (comeager, D1)", "found": None})
    if data is None:
        mismatches.append({"path": "quantifiers.ordered", "check": "C4c", "expected": "forall data (D2)", "found": None})
    if comeager and data and not comeager["index"] < data["index"]:
        mismatches.append({"path": "quantifiers.ordered", "check": "C4d",
                           "expected": "comeager-set quantifier before data quantifier",
                           "found": f"comeager@{comeager['index']} after data@{data['index']}"})
    # family-specific tail ordering
    family = ((d.get("conclusion") or {}).get("family") or "").upper()
    if family == "SCC":
        ext = _find_quantifier(qnf, domain="D3")
        if data and ext and not data["index"] < ext["index"]:
            mismatches.append({"path": "quantifiers.ordered", "check": "C4e",
                               "expected": "extension quantifier after the data quantifier",
                               "found": f"ext@{ext['index']} before data@{data['index']}"})
    if family == "WCC":
        comp = _find_quantifier(qnf, domain="D3")
        gam = _find_quantifier(qnf, domain="D4")
        qpt = _find_quantifier(qnf, domain="D5")
        pairs = [(data, comp, "C4f", "completion after data"), (comp, gam, "C4g", "geodesic after completion"),
                 (gam, qpt, "C4h", "I+ point after geodesic")]
        for a, b, cid, msg in pairs:
            if a and b and not a["index"] < b["index"]:
                mismatches.append({"path": "quantifiers.ordered", "check": cid, "expected": msg,
                                   "found": f"{a['binder']}@{a['index']} vs {b['binder']}@{b['index']}"})
    note = str((d.get("quantifiers") or {}).get("order_note") or "")
    if not note:
        mismatches.append({"path": "quantifiers.order_note", "check": "C4i", "expected": "non-empty", "found": ""})
    return {"order_flag": not mismatches, "mismatches": mismatches}


def check_declared_negation(d: dict, qnf: list[dict]) -> dict:
    """Q2/Q4: cross-check the human-written negation against the machine form."""
    mismatches = []
    q = d.get("quantifiers") or {}
    decl = str(q.get("negation") or "")
    nnf = str(q.get("negation_normal_form") or "")
    qclass = str(q.get("quantifier_class") or "")
    family = ((d.get("conclusion") or {}).get("family") or "").upper()
    low = decl.lower()

    # (a) first quantifier of the machine negation
    first = qnf[0]
    if first["kind"] == "exists":
        if not re.search(r"\bthere (exists|is)\b", low) or normalize_var(first["binder"]).split(",")[0] not in low:
            mismatches.append({"path": "quantifiers.negation", "check": "C2a",
                               "expected": f"starts with 'there exists {first['binder']}'",
                               "found": decl[:90]})
    # (b) the universal comeager quantifier must survive the negation
    if not re.search(r"(for every|for all|every)\s+(comeager|residual)", low):
        mismatches.append({"path": "quantifiers.negation", "check": "C2b",
                           "expected": "universal comeager quantifier (for every comeager G)",
                           "found": decl[:120]})
    # (c) the data existential must survive the negation
    data = _find_quantifier(qnf, kind="forall", domain="D2")
    if data and not re.search(r"there (is|exists)[^.;]{0,120}?(data|\(sigma)", low):
        mismatches.append({"path": "quantifiers.negation", "check": "C2c",
                           "expected": f"existential over data after the comeager universal ({data['binder']})",
                           "found": decl[:120]})
    # (d) witness vocabulary naming what a falsifier exhibits (Q4)
    vocab = WITNESS_VOCAB.get(family)
    if vocab:
        missing = [t for t in vocab["must_contain"] if t not in low]
        if missing:
            mismatches.append({"path": "quantifiers.negation", "check": "C2d",
                               "expected": f"{family} negation names the {vocab['witness_name']}; missing {missing}",
                               "found": decl[:160]})
    # (e) normal form must be the set-level non-meagerness form
    for token, cid in (("non-meager", "C2e"), ("non-empty", "C2f"), ("D0", "C2g")):
        if token not in nnf:
            mismatches.append({"path": "quantifiers.negation_normal_form", "check": cid,
                               "expected": token, "found": nnf[:120]})
    # (f) declared quantifier_class must equal the machine one
    machine = "-".join(("not-exists" if x["kind"] == "not_exists" else x["kind"]) for x in qnf)
    qclass_head = re.split(r"[;.]", qclass)[0]
    if norm_class_string(qclass_head) != machine:
        mismatches.append({"path": "quantifiers.quantifier_class", "check": "C2h",
                           "expected": machine, "found": qclass})
    # (k) every quantifier of the machine prefix must be named by the declared
    #     negation (binder or the domain concept it ranges over)
    for x in qnf:
        concepts = DOMAIN_CONCEPT.get(x["domain_id"])
        if isinstance(concepts, dict):
            concepts = concepts.get(family) or concepts["default"]
        # Naming the domain itself (e.g. "for every ... in D0") satisfies the
        # "names the domain it ranges over" half of C2k.  Added in tool 1.1.0
        # after the rev12 F-2 repair renamed the D0 binder "(s,delta)" -> "r".
        if x["domain_id"].lower() in low:
            continue
        if not concepts:
            continue
        if not any(c in low for c in concepts):
            mismatches.append({"path": "quantifiers.negation", "check": "C2k",
                               "expected": f"negation names quantifier {x['kind']} {x['binder']}@{x['domain_id']} "
                                           f"(one of {concepts})",
                               "found": decl[:160]})
    # (g) the formal string must mention the binders in the declared order
    formal = str(q.get("formal") or "")
    pos, order_ok = -1, True
    for x in qnf:
        i = formal.find(x["binder"])
        if i < 0 or i < pos:
            order_ok = False
            mismatches.append({"path": "quantifiers.formal", "check": "C2i",
                               "expected": f"binder {x['binder']!r} in declared order",
                               "found": f"position {i} (previous {pos})"})
            break
        pos = i
    return {"negation_ok": not mismatches, "mismatches": mismatches,
            "machine_class_string": machine, "declared_class_string": qclass,
            "formal_binder_order_ok": order_ok}


def check_witness_typing(d: dict) -> dict:
    """Q4: SCC -> extension witness; WCC -> visible incomplete causal geodesic."""
    mismatches = []
    family = ((d.get("conclusion") or {}).get("family") or "").upper()
    cls = str(d.get("class_id") or "")
    tier1 = ((d.get("falsifier") or {}).get("tier_1") or {})
    if family == "WCC":
        vis = d.get("visibility") or {}
        if vis.get("in_conclusion") is not True:
            mismatches.append({"path": "visibility.in_conclusion", "check": "C5a", "expected": True, "found": vis.get("in_conclusion")})
        if not vis.get("predicate_name"):
            mismatches.append({"path": "visibility.predicate_name", "check": "C5b", "expected": "non-empty", "found": ""})
        dtext = (str(vis.get("definition") or "") + " " + str(vis.get("singularity_definition") or "")).lower()
        for token, cid in (("finite affine", "C5c"), ("future-inextendible", "C5d"), ("visible", "C5e")):
            if token not in dtext:
                mismatches.append({"path": "visibility.definition", "check": cid, "expected": token, "found": dtext[:100]})
        if "visible" not in str(tier1.get("witness_type") or "").lower():
            mismatches.append({"path": "falsifier.tier_1.witness_type", "check": "C5f",
                               "expected": "visible incomplete causal geodesic", "found": tier1.get("witness_type")})
    elif family == "SCC":
        ext = d.get("extension_predicate") or {}
        if not str(ext.get("name") or "").startswith("proper_future_extension"):
            mismatches.append({"path": "extension_predicate.name", "check": "C5g",
                               "expected": "proper_future_extension_in_class", "found": ext.get("name")})
        if str(ext.get("frozen_direction") or "").lower() != "future":
            mismatches.append({"path": "extension_predicate.frozen_direction", "check": "C5h", "expected": "future", "found": ext.get("frozen_direction")})
        # expected regularity is derived from conclusion_type, not hardcoded per file
        ctype = str((d.get("conclusion") or {}).get("conclusion_type") or "")
        m = re.search(r"scc_(c\d(?:_\d)?)_", ctype)
        expected_reg = m.group(1).upper() if m else None
        found_reg = str(ext.get("frozen_regularity") or "")
        if expected_reg and found_reg.upper() != expected_reg:
            mismatches.append({"path": "extension_predicate.frozen_regularity", "check": "C5i",
                               "expected": expected_reg, "found": found_reg})
        if "extension" not in str(tier1.get("witness_type") or "").lower():
            mismatches.append({"path": "falsifier.tier_1.witness_type", "check": "C5j",
                               "expected": "explicit extension witness", "found": tier1.get("witness_type")})
        vis = d.get("visibility") or {}
        wcc_excluded = vis.get("in_conclusion") is False or vis.get("role") == "not_in_conclusion"
        if not wcc_excluded or vis.get("visible_singularity_is_wcc") is not True:
            mismatches.append({"path": "visibility", "check": "C5k",
                               "expected": "WCC predicate explicitly not in this conclusion "
                                           "(in_conclusion:false or role:not_in_conclusion)",
                               "found": {k: vis.get(k) for k in ("role", "in_conclusion", "visible_singularity_is_wcc")}})
    else:
        mismatches.append({"path": "conclusion.family", "check": "C5l", "expected": "WCC|SCC", "found": family})
    return {"witness_typing_ok": not mismatches, "mismatches": mismatches,
            "family": family, "class_id": cls}


def check_trivial_witness(d: dict) -> dict:
    """Assignment falsifier: negation must not be satisfiable by a trivial witness.

    A trivial witness is 'no data exist' / 'every datum disperses' / a witness
    that carries no non-vacuity marker.  The machine check requires the schema
    to declare (i) an ambient space that is non-empty (Baire) so comeagerness is
    non-vacuous, (ii) a non-empty generic set, (iii) a non-vacuity condition and
    witness, and (iv) a vacuity falsifier.
    """
    mismatches = []
    gen = d.get("genericity") or {}
    nv = d.get("non_vacuity") or {}
    ambient = str(gen.get("ambient_space") or "")
    gset = str(gen.get("generic_set") or "")
    for token, cid in (("baire", "C7a"), ("non-empty", "C7b")):
        if token not in ambient.lower():
            mismatches.append({"path": "genericity.ambient_space", "check": cid,
                               "expected": f"declares {token} (blocks the 'no data exist' witness)",
                               "found": ambient[:140]})
    if not gset:
        mismatches.append({"path": "genericity.generic_set", "check": "C7c", "expected": "non-empty", "found": ""})
    nvtext = (str(nv.get("condition") or "") + " " + str(nv.get("witness_type") or "")).lower()
    if not any(t in nvtext for t in ("incomplete", "trapped surface")):
        mismatches.append({"path": "non_vacuity", "check": "C7d",
                           "expected": "non-vacuity marker (incompleteness or trapped surface)",
                           "found": nvtext[:140]})
    if not nv.get("vacuity_falsifier"):
        mismatches.append({"path": "non_vacuity.vacuity_falsifier", "check": "C7e", "expected": "non-empty", "found": ""})
    return {"trivial_witness_excluded": not mismatches, "mismatches": mismatches}


def build_qnf(d: dict) -> dict:
    q = d.get("quantifiers") or {}
    ordered = q.get("ordered") or []
    domains = q.get("domains") or {}
    mismatches = []
    qnf = []
    for i, entry in enumerate(ordered):
        kind = norm_kind(str(entry.get("kind") or ""))
        binder = str(entry.get("binder") or "")
        dom = str(entry.get("domain_id") or "")
        if kind not in VALID_KINDS:
            mismatches.append({"path": f"quantifiers.ordered[{i}].kind", "check": "C1a",
                               "expected": sorted(VALID_KINDS), "found": entry.get("kind")})
        if not binder:
            mismatches.append({"path": f"quantifiers.ordered[{i}].binder", "check": "C1b", "expected": "non-empty", "found": ""})
        if not dom:
            mismatches.append({"path": f"quantifiers.ordered[{i}].domain_id", "check": "C1c", "expected": "non-empty", "found": ""})
        elif dom not in domains:
            mismatches.append({"path": f"quantifiers.ordered[{i}].domain_id", "check": "C1d",
                               "expected": f"declared in quantifiers.domains ({sorted(domains)})", "found": dom})
        qnf.append({
            "index": i, "kind": kind, "binder": binder, "domain_id": dom,
            "domain_definition": (domains.get(dom) or {}).get("definition") if isinstance(domains.get(dom), dict) else None,
            "domain_definition_ref": (domains.get(dom) or {}).get("definition_ref") if isinstance(domains.get(dom), dict) else None,
            "flipped_kind": KIND_FLIP.get(kind),
        })
    if not ordered:
        mismatches.append({"path": "quantifiers.ordered", "check": "C1e", "expected": "non-empty", "found": []})
    if not q.get("formal"):
        mismatches.append({"path": "quantifiers.formal", "check": "C1f", "expected": "non-empty", "found": ""})
    return qnf, mismatches


def analyze_schema(path: Path) -> dict:
    raw = path.read_bytes()
    sha = sha256_bytes(raw)
    d = yaml.safe_load(raw)
    qnf, qnf_mismatches = build_qnf(d)
    free = classify_free_variables(d, qnf)
    order = check_order(qnf, d)
    decl = check_declared_negation(d, qnf)
    wit = check_witness_typing(d)
    triv = check_trivial_witness(d)
    neg = machine_negation(qnf)
    family = wit["family"]
    vocab = WITNESS_VOCAB.get(family, {})
    neg["required_witness"] = vocab.get("witness_name", "unclassified")
    neg["readable"] = " ; ".join(
        f"{x['kind']} {x['binder']} in {x['domain_id']}" for x in neg["flipped_prefix"]
    )

    mismatch_paths = []
    for group in (qnf_mismatches, order["mismatches"], decl["mismatches"], wit["mismatches"], triv["mismatches"]):
        mismatch_paths.extend(group)
    if free["escapes"]:
        mismatch_paths.extend({"path": e["path"], "check": "C2j", "expected": "bound or let-bound variable",
                               "found": e["token"]} for e in free["escapes"])

    conclusion = d.get("conclusion") or {}
    return {
        "report_item_id": f"qnf-{d.get('class_id')}",
        "class_id": d.get("class_id"),
        "node_id": d.get("node_id"),
        "schema_path": str(path.relative_to(ROOT)),
        "schema_sha256": sha,
        "schema_revision": d.get("revision"),
        "evidence_ref": f"{path.relative_to(ROOT)}#sha256:{sha[:12]}",
        "qnf": qnf,
        "conclusion_predicate": {
            "name": (d.get("visibility") or {}).get("predicate_name") if family == "WCC"
                    else (d.get("extension_predicate") or {}).get("name"),
            "conclusion_type": conclusion.get("conclusion_type"),
            "statement_formal": conclusion.get("statement_formal"),
        },
        "free_variables": free,
        "machine_negation": neg,
        "declared_negation": {
            "negation": (d.get("quantifiers") or {}).get("negation"),
            "negation_normal_form": (d.get("quantifiers") or {}).get("negation_normal_form"),
            "quantifier_class": (d.get("quantifiers") or {}).get("quantifier_class"),
            "order_note": (d.get("quantifiers") or {}).get("order_note"),
        },
        "qnf_ok": not qnf_mismatches and free["free_variables_ok"],
        "negation_ok": decl["negation_ok"],
        "order_flag": order["order_flag"],
        "witness_typing_ok": wit["witness_typing_ok"],
        "trivial_witness_excluded": triv["trivial_witness_excluded"],
        "mismatch_paths": mismatch_paths,
        "checks": {
            "C1_qnf_extraction": not qnf_mismatches,
            "C2_negation_wellformed": decl["negation_ok"],
            "C3_free_variable_capture": free["free_variables_ok"],
            "C4_order_noncommutative": order["order_flag"],
            "C5_witness_typing": wit["witness_typing_ok"],
            "C7_trivial_witness_excluded": triv["trivial_witness_excluded"],
        },
    }


# ---------------------------------------------------------------------------
# Self-test mutants: prove each check can fail (the report is only evidence if
# the instrument is falsifiable).
# ---------------------------------------------------------------------------
def _mutants(d: dict):
    m1 = copy.deepcopy(d); o = m1["quantifiers"]["ordered"]; o[1], o[2] = o[2], o[1]
    yield "M1_swap_comeager_and_data", m1, lambda r: r["order_flag"] is False
    m1b = copy.deepcopy(d); ob = m1b["quantifiers"]["ordered"]; ob[0], ob[1] = ob[1], ob[0]
    yield "M1b_swap_classparam_and_comeager", m1b, lambda r: r["order_flag"] is False
    m2 = copy.deepcopy(d); m2["quantifiers"]["ordered"][0]["domain_id"] = "D99"
    yield "M2_unresolvable_domain", m2, lambda r: r["qnf_ok"] is False
    m3 = copy.deepcopy(d)
    m3["conclusion"]["statement_formal"] = str(m3["conclusion"]["statement_formal"]) + " and visible_from(Z_extra)"
    # Z is not a quantifier binder, a let-binding, an index, a predicate or a
    # declared context symbol; K would NOT work here because K is the second
    # fundamental form bound by the (Sigma,h,K) binder.
    yield "M3_free_variable_escape", m3, lambda r: any(e["token"] == "Z_extra" for e in r["free_variables"]["escapes"])
    m4 = copy.deepcopy(d); m4["genericity"]["ambient_space"] = "the empty space"
    yield "M4_trivial_no_data_witness", m4, lambda r: r["trivial_witness_excluded"] is False
    m5 = copy.deepcopy(d); m5["quantifiers"]["quantifier_class"] = "forall-forall"
    yield "M5_quantifier_class_mismatch", m5, lambda r: r["negation_ok"] is False
    m6 = copy.deepcopy(d); m6["quantifiers"]["negation"] = "No data exist, so the statement is vacuously true."
    yield "M6_declared_negation_trivialised", m6, lambda r: r["negation_ok"] is False


def self_test(d: dict) -> list[dict]:
    out = []
    for name, mutant, predicate in _mutants(d):
        try:
            r = analyze_schema_dict(mutant, Path("SELFTEST"))
            ok = bool(predicate(r))
        except Exception as exc:  # a crash is a failed mutant check, not a pass
            ok, r = False, {"error": f"{type(exc).__name__}: {exc}"}
        out.append({"mutant": name, "expected_detection": True, "detected": ok,
                    "mismatch_paths": r.get("mismatch_paths", [])[:2] if isinstance(r, dict) else []})
    return out


def analyze_schema_dict(d: dict, path: Path) -> dict:
    """Same as analyze_schema but from an in-memory document (self-test)."""
    tmp = dict(d)
    raw = yaml.safe_dump(tmp, sort_keys=True).encode()
    sha = sha256_bytes(raw)
    qnf, qnf_mismatches = build_qnf(tmp)
    free = classify_free_variables(tmp, qnf)
    order = check_order(qnf, tmp)
    decl = check_declared_negation(tmp, qnf)
    wit = check_witness_typing(tmp)
    triv = check_trivial_witness(tmp)
    mismatch_paths = []
    for group in (qnf_mismatches, order["mismatches"], decl["mismatches"], wit["mismatches"], triv["mismatches"]):
        mismatch_paths.extend(group)
    if free["escapes"]:
        mismatch_paths.extend({"path": e["path"], "check": "C2j", "found": e["token"]} for e in free["escapes"])
    return {"schema_sha256": sha, "qnf_ok": not qnf_mismatches and free["free_variables_ok"],
            "negation_ok": decl["negation_ok"], "order_flag": order["order_flag"],
            "witness_typing_ok": wit["witness_typing_ok"],
            "trivial_witness_excluded": triv["trivial_witness_excluded"],
            "free_variables": free, "mismatch_paths": mismatch_paths}


def freeze_binding(items: list[dict]) -> dict:
    """Compare each measured schema hash with the last frozen manifest.

    The gate protocol binds verdicts to sha256, never to the path alone.  If a
    canonical file has been written after the last FROZEN.json freeze, that is
    reported as drift: the verdict above still holds for the measured hash, but
    it must be re-bound when the manifest is bumped.
    """
    manifest_path = ROOT / "artifacts" / "formulation" / "FROZEN.json"
    out = {"manifest_path": "artifacts/formulation/FROZEN.json", "manifest_sha256": None,
           "manifest_revision": None, "manifest_frozen_at": None, "per_schema": [], "drift": []}
    if not manifest_path.exists():
        out["drift"].append({"path": out["manifest_path"], "reason": "manifest missing"})
        return out
    mraw = manifest_path.read_bytes()
    man = json.loads(mraw)
    out["manifest_sha256"] = sha256_bytes(mraw)
    out["manifest_revision"] = man.get("revision")
    out["manifest_frozen_at"] = man.get("frozen_at")
    for s in items:
        if "schema_sha256" not in s:
            continue
        entry = man.get("files", {}).get(s["schema_path"], {})
        frozen = entry.get("sha256")
        match = frozen == s["schema_sha256"]
        out["per_schema"].append({"schema_path": s["schema_path"], "measured_sha256": s["schema_sha256"],
                                  "frozen_sha256": frozen, "frozen_match": match})
        if not match:
            out["drift"].append({"path": s["schema_path"], "measured_sha256": s["schema_sha256"],
                                 "frozen_sha256": frozen,
                                 "reason": "file written after the last FROZEN.json freeze" if frozen
                                           else "path not present in FROZEN.json"})
    out["binding_note"] = ("verdicts are bound to the measured sha256, not the path; drift entries must be "
                           "re-bound to the next FROZEN.json revision before gate adjudication")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--schema", action="append", default=None, help="schema path (repeatable)")
    ap.add_argument("--out", default=str(Path(__file__).with_name("qnf_report.json")))
    ap.add_argument("--self-test", action="store_true", help="run mutant self-tests and include them")
    args = ap.parse_args()

    schema_paths = [Path(p) if Path(p).is_absolute() else ROOT / p for p in (args.schema or DEFAULT_SCHEMAS)]
    tool_path = Path(__file__).resolve()
    items = []
    for p in schema_paths:
        if not p.exists():
            items.append({"schema_path": str(p), "error": "missing"})
            continue
        items.append(analyze_schema(p))

    report = {
        "report_id": f"qnf-form-{datetime.now(CST).strftime('%Y%m%dT%H%M%S%z')}",
        "task_id": "FORM-QNF-06",
        "assignment_event_id": "assign-FORM-QNF-06-20260911T2331",
        "gate": "G-CLASSBIND",
        "assignee": "deepseek-flash-17",
        "worker_slot": 17,
        "generated_at": now_iso(),
        "tool": {"path": str(tool_path.relative_to(ROOT)), "sha256": sha256_file(tool_path), "version": TOOL_VERSION},
        "acceptance_map": {
            "Q1_qnf_extraction": "schemas[].qnf + schemas[].conclusion_predicate + schemas[].free_variables",
            "Q2_machine_negation": "schemas[].machine_negation + schemas[].free_variables.escapes",
            "Q3_order": "schemas[].order_flag + mismatch_paths checks C4*",
            "Q4_witness_typing": "schemas[].witness_typing_ok + machine_negation.required_witness",
            "Q5_per_schema_verdicts": "schemas[].{qnf_ok,negation_ok,order_flag,mismatch_paths}",
            "falsifier_trivial_witness": "schemas[].trivial_witness_excluded + checks.C7",
        },
        "schemas": items,
        "result_summary": {
            "schemas_checked": len([s for s in items if "class_id" in s]),
            "qnf_ok": len([s for s in items if s.get("qnf_ok")]),
            "negation_ok": len([s for s in items if s.get("negation_ok")]),
            "order_flag": len([s for s in items if s.get("order_flag")]),
            "witness_typing_ok": len([s for s in items if s.get("witness_typing_ok")]),
            "trivial_witness_excluded": len([s for s in items if s.get("trivial_witness_excluded")]),
        },
        "self_test": self_test(yaml.safe_load(schema_paths[0].read_bytes())) if args.self_test else None,
        "validation_status": "draft_unverified",
        "not_claimed": [
            "no node completion", "no theorem", "no physics result",
            "no gate verdict (worker events cannot set gates)",
        ],
        "falsifier": ("If any extracted negation is satisfiable by a trivial witness such as "
                      "'no data exist', the schema is vacuous: the failing path is reported in "
                      "that schema's mismatch_paths under check C7."),
    }
    report["freeze_binding"] = freeze_binding(items)
    report["result_summary"]["freeze_drift"] = [d["path"] for d in report["freeze_binding"]["drift"]]
    if report["self_test"]:
        report["result_summary"]["self_test_detected"] = f"{sum(1 for t in report['self_test'] if t['detected'])}/{len(report['self_test'])}"
    out = Path(args.out) if Path(args.out).is_absolute() else ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({
        "report_id": report["report_id"],
        "out": str(out.relative_to(ROOT)),
        "schemas": [{"class_id": s.get("class_id"), "qnf_ok": s.get("qnf_ok"),
                     "negation_ok": s.get("negation_ok"), "order_flag": s.get("order_flag"),
                     "witness_typing_ok": s.get("witness_typing_ok"),
                     "trivial_witness_excluded": s.get("trivial_witness_excluded"),
                     "n_mismatch": len(s.get("mismatch_paths") or [])} for s in items],
        "self_test": report["self_test"],
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
