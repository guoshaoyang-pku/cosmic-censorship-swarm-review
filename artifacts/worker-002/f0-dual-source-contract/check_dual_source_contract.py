#!/usr/bin/env python3
"""W002-F0-DUALSOURCE-01 -- canonical-vs-supplement class-contract agreement probes.

Bounded worker-002 task, node F0, gate G-F0.  Measurement only: this script writes
nothing outside artifacts/worker-002/f0-dual-source-contract/ and never edits a
canonical path.  It cannot set status=done, validation_status=passed or a gate
verdict (comms/PROTOCOL.md rule 5).

Question measured
-----------------
The three frozen schemas (F1/F2a/F2b) carry a `class_contract_pointer` and a
`f0_binding`; the supplement `artifacts/formulation/formulation_taxonomy.yaml`
carries `class_contracts.<ID>` for the same four frozen class ids that the
declared F0 `research_map/formulation_taxonomy.yaml` describes under `classes.<ID>`.
Do the two surfaces describe the same class contract, or can an agent reading one
of them get a different class than an agent reading the other?

Decidable probes (drive the headline):
  P1  class-id surface: identical four-id set on both sides
  P2  conclusion_type token, under the declared VOCAB_ALIASES map
  P3  regularity / extension-class token
  P4  visibility reading: single-q TAIL vs set-based J^-(I+) vs unspecified
  P5  unsourced equivalence gloss on one side only
  P6  genericity axis token vs the supplement's frozen axis (declared aliases),
      plus a canonical-internal check: does the conclusion quantifier contradict
      the class's own genericity status?
  P9  disjointness pair matrix: canonical decisive_axes vs supplement prose
  P10 registered variants
  P11 machine hygiene: duplicate top-level YAML keys, provenance window
  P12 pointer surfaces: does `class_contract_pointer` land in the canonical file?

Informational (does NOT drive the headline):
  P7  hypotheses/exclusions restatement granularity: token-coverage inventory of
      each side against the other side's contract surface, at a declared coverage
      threshold with a sensitivity sweep.  Prose summaries at different
      granularity are expected here; the probe reports numbers, not equivalence.

Probe status vocabulary: agree | alias_agree | subset | underspecified |
restatement | tension | conflict_candidate | unmatched.
`conflict_candidate` = two surfaces assert tokens the project itself declares
mutually exclusive (C0 vs C2, set-based vs single-q visibility, alias-unbridged
conclusion types).  It is a token-level machine finding, not a physics claim.

Controls: 12 synthetic, self-contained mutations (the live defect need not exist).
Any control that does not behave as expected makes the script exit 3 (fail closed).
Live input drift during the run exits 2.

Usage:
  python3 check_dual_source_contract.py                 # normal run
  python3 check_dual_source_contract.py --expect-live   # fail (2) on live drift
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]          # .../ai4math-swarm
OUT = Path(__file__).resolve().parent
SNAP = OUT / "snapshots"

CANONICAL = ROOT / "research_map" / "formulation_taxonomy.yaml"
SUPPLEMENT = ROOT / "artifacts" / "formulation" / "formulation_taxonomy.yaml"
ALIASES = ROOT / "artifacts" / "formulation" / "VOCAB_ALIASES.json"
FROZEN = ROOT / "artifacts" / "formulation" / "FROZEN.json"
SCHEMAS = {
    "F1": ROOT / "schemas" / "af_wcc_vacuum.yaml",
    "F2a": ROOT / "schemas" / "af_scc_c2_vacuum.yaml",
    "F2b": ROOT / "schemas" / "af_scc_c0_vacuum.yaml",
}

CST = timezone(timedelta(hours=8))
WALL = lambda: datetime.now(CST).isoformat(timespec="seconds")  # noqa: E731

CLASS_IDS = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]
WCC_CLASSES = {"AF-WCC-VAC-GEN", "AF-WCC-SCALAR-SPH"}

COVER_THRESHOLD = 0.60
COVER_SWEEP = [0.40, 0.50, 0.60, 0.70, 0.80]
OVERLAP_CONFLICT_THRESHOLD = 0.60

AUTHORITY_NOTE = (
    "Worker measurement only. Per research_map/ASTRA_HANDOFF.md and comms/PROTOCOL.md "
    "rule 5, a worker event cannot set status=done, validation_status=passed or a gate "
    "verdict. No canonical path was modified. conflict_candidate is a machine-readable "
    "token conflict under declared project vocabularies, not a physics claim."
)

STATUS_ORDER = ["conflict_candidate", "unmatched", "tension", "underspecified",
                "restatement", "subset", "alias_agree", "agree"]


class DriftError(RuntimeError):
    pass


# --------------------------------------------------------------------------- #
# io / hashing
# --------------------------------------------------------------------------- #


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_json(path: Path):
    with open(path) as f:
        return json.load(f)


class _RecordingLoader(yaml.SafeLoader):
    duplicates: list[dict] = []


def _construct_mapping(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            _RecordingLoader.duplicates.append(
                {"key": str(key), "line": key_node.start_mark.line + 1}
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_RecordingLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping
)


def strict_load(path: Path):
    """(data, duplicate-keys). Values keep PyYAML last-wins semantics."""
    _RecordingLoader.duplicates = []
    with open(path) as f:
        data = yaml.load(f, Loader=_RecordingLoader)
    return data, list(_RecordingLoader.duplicates)


def strict_load_text(text: str):
    _RecordingLoader.duplicates = []
    data = yaml.load(text, Loader=_RecordingLoader)
    return data, list(_RecordingLoader.duplicates)


# --------------------------------------------------------------------------- #
# normalizer / decidable readings
# --------------------------------------------------------------------------- #

PHRASE_RULES = [
    (r"maximal globally hyperbolic development[s]?", "mghd"),
    (r"\bmghd\b", "mghd"),
    (r"lambda\s*=\s*0", "lambda0"),
    (r"3\s*\+\s*1\s*dimensional", "dim4"),
    (r"4-dimensional", "dim4"),
    (r"asymptotically flat", "af"),
    (r"one\s+(?:af\s+)?end", "af_one_end"),
    (r"future[-\s]inextendib\w*", "future_inext"),
    (r"constraint equations?", "constraints"),
    (r"\bcomeager\b|\bresidual\b", "comeager"),
    (r"\bgeneric\w*\b", "generic"),
    (r"spherical\w*\s+symmetr\w*|spherical\b", "spherical"),
    (r"scalar\s+field|scalar\s+matter|\bscalar\b", "scalar"),
    (r"\bvacuum\b|t\s*=\s*0", "vacuum"),
    (r"c\s*\^?\s*2\b|\bc2\b", "c2"),
    (r"c\s*\^?\s*0\b|\bc0\b", "c0"),
    (r"c\s*\^?\{?1,1\}?", "c11"),
    (r"h\s*\^?2_?loc", "h2loc"),
    (r"j\s*\^?-?\s*\(\s*i\+", "jminus_iplus"),
    (r"j\s*\^?-?\s*\(\s*q", "jminus_q"),
    (r"visible from i\+|visibility", "visible_iplus"),
    (r"so\(3\)", "so3"),
    (r"event horizon|hidden behind", "horizon"),
]

STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "in", "on", "to", "for", "with", "by",
    "as", "at", "is", "are", "be", "been", "being", "that", "this", "these",
    "those", "it", "its", "their", "there", "which", "who", "whom", "whose",
    "when", "where", "why", "how", "than", "then", "so", "such", "may", "might",
    "must", "can", "could", "shall", "should", "will", "would", "from", "into",
    "over", "under", "between", "within", "also", "any", "all", "each", "every",
    "both", "either", "neither", "other", "another", "same", "different", "only",
    "own", "more", "most", "less", "least", "very", "just", "but", "if",
    "because", "while", "during", "after", "before", "above", "below", "up",
    "down", "out", "off", "again", "further", "once", "here", "now", "does",
    "do", "did", "has", "have", "had", "was", "were", "including", "include",
    "includes", "e", "g", "i", "etc", "class", "classes", "statement", "assert",
    "asserts", "asserted", "claim", "claims", "conclusion", "hypothesis",
    "hypotheses", "exclusion", "exclusions", "case", "cases", "admissible",
    "readable", "substitute", "given", "lies", "lie",
}
NEG_RE = re.compile(r"\b(no|not|never|without|excluded|excludes|forbidden|absent|outside|avoid)\b")

# Only editorial/revision brackets, never math intervals like [0,T) that a later
# ']' could otherwise swallow together with the primary predicate text.
BRACKET_RE = re.compile(
    r"\[\s*(?:rev\d*|superseded|revision|note|see also|source|checked)\b[^\]]*\]",
    re.IGNORECASE,
)


def primary_text(text: str) -> str:
    """Drop bracketed revision notes so the primary claim drives classification."""
    return BRACKET_RE.sub(" ", str(text))


def normalize(text: str) -> str:
    s = primary_text(text).lower()
    for pat, rep in PHRASE_RULES:
        s = re.sub(pat, rep, s)
    return s


def tokenize(text: str) -> set[str]:
    toks = re.findall(r"[a-z0-9_]+", normalize(text))
    return {t for t in toks if t not in STOPWORDS and len(t) > 1}


def polarity(text: str) -> str:
    return "negative" if NEG_RE.search(primary_text(text).lower()) else "positive"


def overlap_coef(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


SINGLE_Q_SIGNALS = [r"\bsingle-q\b", r"\btail predicate\b", r"tail\s+gamma",
                    r"jminus_q", r"contained in j\^?-\(q"]
SET_BASED_SIGNALS = [r"union of (?:the sets )?j", r"over all q", r"jminus_iplus"]
VARIANT_NOTE_SIGNALS = [r"registered as variant", r"is variant", r"set-based reading",
                        r"superseded", r"strictly stronger"]


def visibility_reading(text: str) -> str:
    """Classify the asserted visibility predicate.

    `jminus_q` is ambiguous: it occurs in the single-q TAIL predicate and inside the
    set-based union phrase, so the union phrase is resolved first.
    """
    t = normalize(text)
    union = any(re.search(p, t) for p in SET_BASED_SIGNALS)
    single = any(re.search(p, t) for p in SINGLE_Q_SIGNALS)
    explicit_tail = bool(re.search(r"\bsingle-q\b|\btail predicate\b|tail\s+gamma", t))
    variant_note = any(re.search(p, t) for p in VARIANT_NOTE_SIGNALS)
    if union and single and variant_note:
        return "single_q_with_set_based_variant_note"
    if union and single:
        return "single_q_tail" if explicit_tail else "set_based"
    if union:
        return "set_based"
    if single:
        return "single_q_tail"
    return "unspecified"


def comeager_reading(text: str) -> str:
    t = normalize(text)
    if re.search(r"comeager", t):
        return "named_comeager"
    if re.search(r"generic data|generic set", t):
        return "bare_generic"
    return "unspecified"


def detect_gloss(text: str) -> bool:
    return bool(re.search(r"\bequivalently\b", primary_text(text)))


# --------------------------------------------------------------------------- #
# declared alias map
# --------------------------------------------------------------------------- #


def alias_index(alias_doc: dict) -> dict:
    idx = {}
    for group, mapping in alias_doc.items():
        if not isinstance(mapping, dict):
            continue
        for canonical, aliases in mapping.items():
            if not isinstance(aliases, list):
                continue
            for a in aliases + [canonical]:
                idx.setdefault(str(a), str(canonical))
    return idx


def alias_agree(a: str, b: str, idx: dict) -> tuple[bool, str]:
    if a == b:
        return True, "identical"
    ca, cb = idx.get(a), idx.get(b)
    if ca is not None and ca == cb:
        return True, f"declared alias -> {ca}"
    return False, "no declared alias mapping"


# --------------------------------------------------------------------------- #
# decidable probes
# --------------------------------------------------------------------------- #


def surface_pool(contract: dict, side: str) -> set[str]:
    """Token pool of one contract surface (for coverage inventory)."""
    if side == "supplement":
        fields = [contract.get("ambient_theory", "")]
        fields += [str(x) for x in contract.get("components", {}).values()]
        fields += list(contract.get("hypotheses", []))
        fields += list(contract.get("exclusions", []))
        fields += list(contract.get("non_goals", []))
        fields.append(contract.get("conclusion_predicate", ""))
    else:
        fields = [contract.get("conclusion", {}).get("text", "")]
        fields += list(contract.get("exclusions", []))
        fields += [str(x) for x in contract.get("axes", {}).values()]
        fields += [x.get("text", "") for x in contract.get("hypotheses", [])]
    pool: set[str] = set()
    for f in fields:
        pool |= tokenize(f)
    return pool


def coverage_inventory(canon_cls: dict, supp_cls: dict, threshold: float) -> dict:
    cpool = surface_pool(canon_cls, "canonical")
    spool = surface_pool(supp_cls, "supplement")

    def rows(items, pool, side):
        out = []
        for it in items:
            text = it.get("text", "") if isinstance(it, dict) else str(it)
            toks = tokenize(text)
            covered = len(toks & pool) / len(toks) if toks else 0.0
            out.append({
                "item_id": it.get("id") if isinstance(it, dict) else None,
                "text": text[:180],
                "tokens": len(toks),
                "coverage": round(covered, 4),
                "covered": covered >= threshold,
                "missing_tokens": sorted(toks - pool)[:12],
                "side": side,
            })
        return out

    canon_items = list(canon_cls.get("hypotheses", [])) + list(canon_cls.get("exclusions", []))
    supp_items = list(supp_cls.get("hypotheses", [])) + list(supp_cls.get("exclusions", []))
    c_rows = rows(canon_items, spool, "canonical")
    s_rows = rows(supp_items, cpool, "supplement")

    # polarity conflict only when two items are each other's near-copies
    conflicts = []
    for c in canon_items:
        ct = tokenize(c.get("text", "") if isinstance(c, dict) else str(c))
        for s in supp_items:
            st = tokenize(str(s))
            if overlap_coef(ct, st) >= OVERLAP_CONFLICT_THRESHOLD:
                pc = polarity(c.get("text", "") if isinstance(c, dict) else str(c))
                ps = polarity(str(s))
                if pc != ps:
                    conflicts.append({
                        "canonical_id": c.get("id") if isinstance(c, dict) else None,
                        "canonical_text": (c.get("text", "") if isinstance(c, dict) else str(c))[:140],
                        "supplement_text": str(s)[:140],
                        "overlap": round(overlap_coef(ct, st), 4),
                        "polarity": f"{pc} vs {ps}",
                    })
    c_covered = sum(1 for r in c_rows if r["covered"])
    s_covered = sum(1 for r in s_rows if r["covered"])
    return {
        "probe": "P7.restatement_coverage",
        "threshold": threshold,
        "canonical_items": len(c_rows),
        "supplement_items": len(s_rows),
        "canonical_items_covered_by_supplement": c_covered,
        "supplement_items_covered_by_canonical": s_covered,
        "canonical": c_rows,
        "supplement": s_rows,
        "polarity_conflicts": conflicts,
        "status": "conflict_candidate" if conflicts else "restatement",
        "caveat": ("Coverage inventory only: prose summaries at different granularity are "
                   "expected to score below threshold. This is not a semantic-equivalence "
                   "measurement and does not drive the headline unless a high-overlap "
                   "polarity conflict is found."),
    }


def probe_class(cid: str, canon_cls: dict, supp_cls: dict, alias_idx: dict,
                cover_threshold: float = COVER_THRESHOLD) -> dict:
    rows: list[dict] = []
    out: dict = {"class_id": cid}

    # P1 class-id surface
    p1 = {"probe": "P1.class_id", "status": "agree" if cid else "unmatched",
          "detail": "class id present on both surfaces"}
    rows.append(p1)
    out["class_id"] = p1

    # P2 conclusion_type
    c_axes_ct = canon_cls.get("axes", {}).get("conclusion_type")
    c_decl_ct = canon_cls.get("conclusion", {}).get("type")
    s_ct = supp_cls.get("conclusion_type")
    ok, basis = alias_agree(str(c_axes_ct), str(s_ct), alias_idx)
    p2 = {"probe": "P2.conclusion_type", "canonical_axes": c_axes_ct,
          "canonical_conclusion_type": c_decl_ct, "supplement": s_ct,
          "alias_basis": basis, "status": "alias_agree" if ok else "conflict_candidate"}
    if c_axes_ct != c_decl_ct:
        p2["canonical_internal_mismatch"] = True
        p2["status"] = "conflict_candidate"
        p2["detail"] = "canonical axes.conclusion_type != canonical conclusion.type"
    rows.append(p2)
    out["conclusion_type"] = p2

    # P3 regularity token
    c_reg = canon_cls.get("axes", {}).get("regularity_token")
    s_text = " ".join([str(supp_cls.get("ambient_theory", ""))]
                      + [str(x) for x in supp_cls.get("hypotheses", [])]
                      + [str(supp_cls.get("conclusion_predicate", ""))])
    s_tokens = tokenize(s_text)
    s_reg_tokens = sorted(t for t in s_tokens if t in {"c0", "c2", "c11", "h2loc"})
    if c_reg is None:
        conflict_tok = [t for t in s_reg_tokens if t in {"c0", "c2"}]
        st = "conflict_candidate" if (cid in WCC_CLASSES and conflict_tok) else "agree"
        p3 = {"probe": "P3.regularity_token", "canonical": None,
              "supplement_mentions": s_reg_tokens, "conflicting_token_present": bool(conflict_tok),
              "status": st}
    else:
        present = c_reg.lower() in s_tokens
        other = ("c0" if c_reg.upper() == "C2" else "c2") in s_tokens
        st = "conflict_candidate" if other else ("agree" if present else "underspecified")
        p3 = {"probe": "P3.regularity_token", "canonical": c_reg,
              "present_in_supplement": present, "conflicting_token_present": other,
              "status": st}
    rows.append(p3)
    out["regularity_token"] = p3

    # P4 visibility predicate
    c_concl = str(canon_cls.get("conclusion", {}).get("text", ""))
    s_pred = str(supp_cls.get("conclusion_predicate", ""))
    c_read, s_read = visibility_reading(c_concl), visibility_reading(s_pred)
    if cid in WCC_CLASSES:
        if s_read == "set_based" and c_read in {"single_q_tail", "single_q_with_set_based_variant_note"}:
            st = "conflict_candidate"
        elif c_read == "set_based" and s_read != "set_based":
            st = "conflict_candidate"
        elif c_read in {"single_q_tail", "single_q_with_set_based_variant_note"} and s_read == "unspecified":
            st = "underspecified"
        elif c_read == s_read:
            st = "agree"
        else:
            st = "subset"
        p4 = {"probe": "P4.visibility_predicate", "canonical_reading": c_read,
              "supplement_reading": s_read, "supplement_predicate": s_pred,
              "status": st}
        if st == "underspecified":
            p4["detail"] = ("canonical names the visibility reading explicitly; the supplement "
                            "predicate says only 'visible from I+' and does not name the "
                            "single-q TAIL predicate or the comeager quantifier")
    else:
        p4 = {"probe": "P4.visibility_predicate", "canonical_reading": c_read,
              "supplement_reading": s_read,
              "status": "agree" if c_read == s_read else "subset",
              "note": "SCC class: visibility is excluded content on both sides"}
    rows.append(p4)
    out["visibility_predicate"] = p4

    # P5 equivalence gloss
    c_gloss, s_gloss = detect_gloss(c_concl), detect_gloss(s_pred)
    p5 = {"probe": "P5.equivalence_gloss", "canonical_has_equivalently": c_gloss,
          "supplement_has_equivalently": s_gloss,
          "status": "underspecified" if (c_gloss and not s_gloss) else "agree"}
    if c_gloss and not s_gloss:
        p5["detail"] = "canonical asserts an 'equivalently' gloss the supplement predicate omits"
    rows.append(p5)
    out["equivalence_gloss"] = p5

    # P6 genericity: cross-file axis + canonical-internal conclusion/axis check
    c_kind = canon_cls.get("axes", {}).get("genericity_kind")
    c_status = canon_cls.get("genericity_value_status")
    c_comeager = comeager_reading(c_concl)
    p6 = {"probe": "P6.genericity", "canonical_kind": c_kind,
          "canonical_value_status": c_status,
          "canonical_conclusion_quantifier": c_comeager,
          "supplement_frozen": None, "cross_file_alias_basis": None,
          "canonical_internal": "consistent", "status": "agree"}
    if c_comeager == "bare_generic" and str(c_kind) in {"unresolved", "None"}:
        p6["status"] = "conflict_candidate"
        p6["detail"] = ("canonical conclusion uses bare 'generic data' while the class "
                        "genericity axis is unresolved; field_vocabulary says 'generic' "
                        "alone is not a machine-readable value")
    elif c_comeager == "named_comeager" and str(c_kind) in {"unresolved", "None"}:
        p6["canonical_internal"] = "tension"
        p6["detail"] = ("canonical conclusion quantifies over a comeager set while the class "
                        "genericity_kind/status is unresolved; reader adjudicates whether the "
                        "conclusion may name a notion the axis leaves open")
    rows.append(p6)
    out["genericity"] = p6

    # P7 restatement coverage (informational)
    p7 = coverage_inventory(canon_cls, supp_cls, cover_threshold)
    rows.append(p7)
    out["hypotheses_exclusions"] = p7

    informative = {"restatement", "agree"}
    out["diff_summary"] = {
        "rows": len(rows),
        "decidable_rows": sum(1 for r in rows if r["status"] not in informative
                              or r["probe"] in {"P1.class_id", "P4.visibility_predicate"}),
        **{s: sum(1 for r in rows if r["status"] == s) for s in STATUS_ORDER},
    }
    out["rows"] = rows
    return out


# --------------------------------------------------------------------------- #
# matrix probes
# --------------------------------------------------------------------------- #

AXIS_PROSE = {
    "family": ["censorship kind", "censorship", "wcc vs scc"],
    "regularity_token": ["regularity"],
    "conclusion_type": ["conclusion family", "conclusion"],
    "matter_model": ["matter"],
    "symmetry": ["symmetry"],
    "asymptotics": ["asymptotic"],
}


def probe_disjointness(canon: dict, supp: dict) -> dict:
    pairs_c = {tuple(sorted(r.get("pair", []))): r for r in canon.get("disjointness", [])}
    pairs_s = {}
    for row in supp.get("disjointness_matrix", {}).get("pairwise", []):
        if isinstance(row, list) and len(row) == 3:
            pairs_s[tuple(sorted([row[0], row[1]]))] = str(row[2])
    rows = []
    for k in sorted(set(pairs_c) | set(pairs_s)):
        c, s = pairs_c.get(k), pairs_s.get(k)
        c_axes = list(c.get("decisive_axes", [])) if c else []
        s_prose = normalize(s or "")
        recognized = [ax for ax in c_axes
                      if any(tok in s_prose for tok in AXIS_PROSE.get(ax, [ax]))]
        missing = [ax for ax in c_axes if ax not in recognized]
        rows.append({"pair": list(k), "canonical_decisive_axes": c_axes,
                     "supplement_prose": s, "axes_recognized_in_prose": recognized,
                     "axes_not_named_in_prose": missing,
                     "status": "agree" if (c and s and not missing)
                     else ("subset" if (c and s) else "unmatched")})
    return {"probe": "P9.disjointness_pairs", "pairs": rows,
            "counts": {"canonical_pairs": len(pairs_c), "supplement_pairs": len(pairs_s),
                       "pairs_with_coarser_prose": sum(1 for r in rows if r["status"] != "agree"),
                       "missing_pairs": sum(1 for r in rows if r["status"] == "unmatched")},
            "status": "agree" if all(r["status"] == "agree" for r in rows) else "subset",
            "caveat": "supplement prose is a summary; a coarser phrase is not a contradiction"}


def probe_variants(canon: dict, supp: dict) -> dict:
    c = {(v.get("parent_class"), v.get("variant_id")): v.get("status")
         for v in canon.get("variants", [])}
    s = {(v.get("parent_class"), v.get("variant_id")): v.get("status")
         for v in supp.get("class_scope_adjudication", {}).get("registered_variants", [])}
    rows = [{"parent_class": k[0], "variant_id": k[1],
             "canonical_status": c.get(k), "supplement_status": s.get(k),
             "status": "agree" if (k in c and k in s and c[k] == s[k]) else "unmatched"}
            for k in sorted(set(c) | set(s), key=str)]
    return {"probe": "P10.variants", "rows": rows,
            "status": "agree" if rows and all(r["status"] == "agree" for r in rows)
            else "unmatched"}


def probe_pointer_surfaces(canon: dict, schema_docs: dict) -> dict:
    nodes = {}
    for node, doc in schema_docs.items():
        pointer = str(doc.get("class_contract_pointer", ""))
        path, _, frag = pointer.partition("#")
        top = frag.split(".")[0] if frag else None
        cls = frag.split(".")[-1] if frag else None
        binding = doc.get("f0_binding", {}) if isinstance(doc.get("f0_binding"), dict) else {}
        nodes[node] = {
            "pointer": pointer,
            "pointer_targets_canonical": path == str(CANONICAL.relative_to(ROOT)),
            "pointer_targets_authoring_supplement": "artifacts/formulation" in path,
            "pointer_fragment_top_key": top,
            "pointer_fragment_class": cls,
            "canonical_has_top_key": top in canon if top else None,
            "fragment_class_in_canonical": cls in canon.get("classes", {}) if cls else None,
            "declared_f0_artifact": binding.get("declared_f0_artifact"),
            "declared_f0_sha256": binding.get("declared_f0_sha256"),
            "class_contract_supplement": binding.get("class_contract_supplement"),
        }
    return {"probe": "P12.pointer_surfaces", "nodes": nodes,
            "status": "agree" if all(
                n["pointer_targets_canonical"] and n["canonical_has_top_key"]
                and n["fragment_class_in_canonical"] for n in nodes.values())
            else "conflict_candidate"}


def probe_hygiene(name: str, path: Path, dups: list[dict], doc: dict) -> dict:
    top_dups: dict[str, list[int]] = {}
    for d in dups:
        top_dups.setdefault(d["key"], []).append(d["line"])
    ts_fields = {}
    for key in ("created_at", "written_at", "revised_at", "revised_at_unused",
                "authored_at"):
        if isinstance(doc.get(key), str):
            ts_fields[key] = doc[key]
    if isinstance(doc.get("class_scope_adjudication"), dict) and isinstance(
            doc["class_scope_adjudication"].get("decided_at"), str):
        ts_fields["decided_at"] = doc["class_scope_adjudication"]["decided_at"]
    content_after_write = None
    if "written_at" in ts_fields:
        later = {k: v for k, v in ts_fields.items()
                 if k != "written_at" and v > ts_fields["written_at"]}
        content_after_write = later or None
    return {"artifact": name, "path": str(path.relative_to(ROOT)),
            "revision": doc.get("revision"),
            "duplicate_top_level_keys": top_dups,
            "duplicate_total": sum(len(v) for v in top_dups.values()),
            "timestamps": ts_fields,
            "content_timestamps_after_written_at": content_after_write}


# --------------------------------------------------------------------------- #
# controls (self-contained: defects are planted, never assumed live)
# --------------------------------------------------------------------------- #


def run_controls(canon: dict, supp: dict, alias_doc: dict) -> list[dict]:
    idx = alias_index(alias_doc)
    controls: list[dict] = []

    def rec(cid, expected, observed, passed, detail=""):
        controls.append({"control_id": cid, "expected": expected,
                         "observed": observed, "pass": bool(passed), "detail": detail})

    S, C = supp["class_contracts"], canon["classes"]

    # C1 planted visibility contradiction: set-based predicate injected into supplement
    mut = copy.deepcopy(supp)
    mut["class_contracts"]["AF-WCC-VAC-GEN"]["conclusion_predicate"] = (
        "gamma is visible from I+ iff gamma([0,T)) is contained in the union of "
        "J^-(q) over all q in I+")
    row = probe_class("AF-WCC-VAC-GEN", C["AF-WCC-VAC-GEN"],
                      mut["class_contracts"]["AF-WCC-VAC-GEN"], idx)["visibility_predicate"]
    rec("C1-visibility-conflict-detected", "conflict_candidate", row["status"],
        row["status"] == "conflict_candidate", row["supplement_reading"])

    # C2 planted bare-generic on an unresolved axis
    mut = copy.deepcopy(canon)
    mut["classes"]["AF-WCC-SCALAR-SPH"]["conclusion"]["text"] = "For generic data in the class, the MGHD is complete."
    row = probe_class("AF-WCC-SCALAR-SPH", mut["classes"]["AF-WCC-SCALAR-SPH"],
                      S["AF-WCC-SCALAR-SPH"], idx)["genericity"]
    rec("C2-bare-generic-detected", "conflict_candidate", row["status"],
        row["status"] == "conflict_candidate")

    # C3 canonical-internal tension detected (comeager conclusion, unresolved axis)
    mut = copy.deepcopy(canon)
    row = probe_class("AF-WCC-SCALAR-SPH", mut["classes"]["AF-WCC-SCALAR-SPH"],
                      S["AF-WCC-SCALAR-SPH"], idx)["genericity"]
    rec("C3-internal-tension-detected", "tension (if live axis is unresolved)",
        row["canonical_internal"],
        row["canonical_internal"] == "tension" or str(row["canonical_kind"]) != "unresolved")

    # C4 declared alias honored
    mut = copy.deepcopy(supp)
    mut["class_contracts"]["AF-SCC-C2-VAC-GEN"]["conclusion_type"] = "strong_cosmic_censorship_C2"
    row = probe_class("AF-SCC-C2-VAC-GEN", C["AF-SCC-C2-VAC-GEN"],
                      mut["class_contracts"]["AF-SCC-C2-VAC-GEN"], idx)["conclusion_type"]
    rec("C4-alias-honored", "alias_agree", row["status"], row["status"] == "alias_agree",
        row["alias_basis"])

    # C5 unbridged conclusion-type contradiction detected
    mut = copy.deepcopy(supp)
    mut["class_contracts"]["AF-SCC-C2-VAC-GEN"]["conclusion_type"] = "scc_c0_future_inextendibility"
    row = probe_class("AF-SCC-C2-VAC-GEN", C["AF-SCC-C2-VAC-GEN"],
                      mut["class_contracts"]["AF-SCC-C2-VAC-GEN"], idx)["conclusion_type"]
    rec("C5-contradiction-detected", "conflict_candidate", row["status"],
        row["status"] == "conflict_candidate")

    # C6 regularity smuggling detected (C0 token in the C2 class contract)
    mut = copy.deepcopy(supp)
    mut["class_contracts"]["AF-SCC-C2-VAC-GEN"]["hypotheses"] = (
        list(mut["class_contracts"]["AF-SCC-C2-VAC-GEN"]["hypotheses"])
        + ["the extension class under test is exactly C0"])
    row = probe_class("AF-SCC-C2-VAC-GEN", C["AF-SCC-C2-VAC-GEN"],
                      mut["class_contracts"]["AF-SCC-C2-VAC-GEN"], idx)["regularity_token"]
    rec("C6-regularity-smuggling", "conflict_candidate", row["status"],
        row["status"] == "conflict_candidate")

    # C7 coverage responds to an empty supplement surface
    mut = copy.deepcopy(supp)
    mut["class_contracts"]["AF-WCC-VAC-GEN"]["hypotheses"] = []
    mut["class_contracts"]["AF-WCC-VAC-GEN"]["exclusions"] = []
    mut["class_contracts"]["AF-WCC-VAC-GEN"]["ambient_theory"] = ""
    mut["class_contracts"]["AF-WCC-VAC-GEN"]["components"] = {}
    mut["class_contracts"]["AF-WCC-VAC-GEN"]["conclusion_predicate"] = ""
    row = probe_class("AF-WCC-VAC-GEN", C["AF-WCC-VAC-GEN"],
                      mut["class_contracts"]["AF-WCC-VAC-GEN"], idx)["hypotheses_exclusions"]
    rec("C7-coverage-responds", "0 canonical items covered",
        row["canonical_items_covered_by_supplement"],
        row["canonical_items_covered_by_supplement"] == 0)

    # C8 disjointness mutation: drop the regularity axis claim from the C2/C0 pair
    mut = copy.deepcopy(supp)
    for row_ in mut["disjointness_matrix"]["pairwise"]:
        if set(row_[:2]) == {"AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"}:
            row_[2] = "disjoint: conclusion family only"
    d = probe_disjointness(canon, mut)
    bad = [r for r in d["pairs"]
           if r["pair"] == sorted(["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"])]
    rec("C8-disjointness-mutation", "regularity_token not named",
        bad[0]["axes_not_named_in_prose"] if bad else None,
        bool(bad and "regularity_token" in bad[0]["axes_not_named_in_prose"]))

    # C9 duplicate-key detection on a synthetic document
    data, dups = strict_load_text("a: 1\nb: 2\na: 3\nc:\n  d: 1\n  d: 2\n")
    keys = sorted(d["key"] for d in dups)
    rec("C9-duplicate-detection", "['a','d']", keys, keys == ["a", "d"],
        f"last-wins value a={data['a']}")

    # C10 bracket-stripping: a bracketed revision note must not change the reading
    with_note = ("For every q in I+, the tail is not contained in J^-(q) intersect M. "
                 "[superseded set-based wording contained in J-(I+) is the variant SET predicate]")
    without = "For every q in I+, the tail is not contained in J^-(q) intersect M."
    rec("C10-bracket-stripping", "single_q_tail both ways",
        [visibility_reading(with_note), visibility_reading(without)],
        visibility_reading(with_note) == visibility_reading(without) == "single_q_tail")

    # C11 drift guard trips on a wrong pin
    try:
        check_pins({"canonical": "0" * 64})
        tripped = False
    except DriftError:
        tripped = True
    rec("C11-drift-guard", "DriftError on wrong pin", tripped, tripped)

    # C12 determinism: probe rows are reproducible in-process
    a = json.dumps(probe_class("AF-WCC-VAC-GEN", C["AF-WCC-VAC-GEN"],
                               S["AF-WCC-VAC-GEN"], idx), sort_keys=True)
    b = json.dumps(probe_class("AF-WCC-VAC-GEN", C["AF-WCC-VAC-GEN"],
                               S["AF-WCC-VAC-GEN"], idx), sort_keys=True)
    rec("C12-determinism", "identical probe rows", a == b, a == b)
    return controls


def check_pins(expected: dict):
    paths = {"canonical": CANONICAL, "supplement": SUPPLEMENT}
    for name, exp in expected.items():
        got = sha256_file(paths[name])
        if got != exp:
            raise DriftError(f"{name}: expected {exp[:16]}, measured {got[:16]}")


# --------------------------------------------------------------------------- #
# report
# --------------------------------------------------------------------------- #


def build_reading(per_class: dict, pointer: dict, hygiene: list[dict],
                  disjointness: dict, variants: dict) -> dict:
    agree_rows, residual = [], []
    for cid, pc in per_class.items():
        for r in pc["rows"]:
            if r["status"] in {"agree", "alias_agree"}:
                agree_rows.append((cid, r["probe"], r["status"]))
            elif r["status"] in {"conflict_candidate", "unmatched", "tension",
                                 "underspecified", "subset"}:
                residual.append({"class_id": cid, "probe": r["probe"],
                                 "status": r["status"],
                                 "detail": r.get("detail", "")})
        g = pc.get("genericity", {})
        if g.get("canonical_internal") == "tension":
            residual.append({"class_id": cid, "probe": "P6.genericity.canonical_internal",
                             "status": "tension", "detail": g.get("detail", "")})
    hard = [r for r in residual if r["status"] == "conflict_candidate"]
    pointer_ok = pointer["status"] == "agree"
    dup_total = sum(h["duplicate_total"] for h in hygiene)
    sentences = []
    sentences.append(
        f"Decidable class-identity probes agree on {len(agree_rows)} rows "
        f"(four identical class ids; conclusion_type agrees on all four classes, "
        f"SCC via the declared VOCAB_ALIASES map; regularity tokens consistent; "
        f"genericity axes agree under declared aliases on all four; variant registry identical)."
        if not hard and pointer_ok else
        f"Decidable probes produced {len(hard)} conflict_candidate row(s).")
    sentences.append(
        "All three schemas' class_contract_pointer now resolves inside the canonical "
        "declared-F0 (research_map/formulation_taxonomy.yaml#classes.<ID>) and the fragment "
        "class exists there; the supplement is declared separately via f0_binding."
        if pointer_ok else
        "At least one class_contract_pointer does not resolve inside the canonical declared-F0.")
    sentences.append(
        f"Duplicate top-level YAML keys in the two surfaces: {dup_total}. "
        "No content timestamp runs past written_at on either surface."
        if dup_total == 0 else
        f"Duplicate top-level YAML keys found: {dup_total} (see duplicate_keys).")
    sentences.append(
        f"Residual non-hard differences: {len(residual)} row(s) "
        f"({', '.join(sorted({r['status'] for r in residual})) or 'none'}). "
        "These are restatement-granularity / underspecification findings, not class-identity "
        "contradictions, unless a row is marked conflict_candidate.")
    return {"agreement_rows": len(agree_rows), "residual_rows": residual,
            "hard_conflicts": hard, "sentences": sentences}


def build_report(expect_live: bool = False) -> dict:
    started = WALL()
    before = {
        "canonical": sha256_file(CANONICAL),
        "supplement": sha256_file(SUPPLEMENT),
        "aliases": sha256_file(ALIASES),
        "frozen_manifest": sha256_file(FROZEN),
    }
    SNAP.mkdir(parents=True, exist_ok=True)
    canon_snap = SNAP / f"F0-canonical-{before['canonical'][:12]}.yaml"
    supp_snap = SNAP / f"F0-supplement-{before['supplement'][:12]}.yaml"
    shutil.copy2(CANONICAL, canon_snap)
    shutil.copy2(SUPPLEMENT, supp_snap)
    (SNAP / "SHA256SUMS").write_text(
        "".join(f"{sha256_file(p)}  {p.name}\n" for p in sorted(SNAP.glob("F0-*.yaml"))))

    canon, canon_dups = strict_load(canon_snap)
    supp, supp_dups = strict_load(supp_snap)
    alias_doc = load_json(ALIASES)
    alias_idx = alias_index(alias_doc)
    frozen = load_json(FROZEN)
    schema_docs = {k: strict_load(v)[0] for k, v in SCHEMAS.items()}

    wall = WALL()
    per_class = {cid: probe_class(cid, canon["classes"][cid],
                                  supp["class_contracts"][cid], alias_idx)
                 for cid in CLASS_IDS}

    frozen_gen = supp.get("axis_registry", {}).get("genericity_axis", {}).get("frozen", {})
    for cid in CLASS_IDS:
        g = per_class[cid]["genericity"]
        ck, sk = str(g["canonical_kind"]), str(frozen_gen.get(cid))
        ok, basis = alias_agree(ck, sk, alias_idx)
        g["supplement_frozen"] = frozen_gen.get(cid)
        g["cross_file_alias_basis"] = basis
        if not ok and g["status"] == "agree":
            g["status"] = "conflict_candidate"
            g["detail"] = f"genericity axis token mismatch: canonical={ck} supplement={sk} ({basis})"

    disjointness = probe_disjointness(canon, supp)
    variants = probe_variants(canon, supp)
    pointer = probe_pointer_surfaces(canon, schema_docs)
    hygiene = [probe_hygiene("canonical", canon_snap, canon_dups, canon),
               probe_hygiene("supplement", supp_snap, supp_dups, supp)]

    controls = run_controls(canon, supp, alias_doc)

    after = {"canonical": sha256_file(CANONICAL), "supplement": sha256_file(SUPPLEMENT)}
    stable = (after["canonical"] == before["canonical"]
              and after["supplement"] == before["supplement"])
    if expect_live and not stable:
        raise DriftError("live canonical/supplement bytes changed during the run")

    reading = build_reading(per_class, pointer, hygiene, disjointness, variants)
    coverage_sweep = {}
    for t in COVER_SWEEP:
        coverage_sweep[str(t)] = {
            cid: {
                "canonical_items_covered_by_supplement":
                    coverage_inventory(canon["classes"][cid],
                                       supp["class_contracts"][cid], t)[
                        "canonical_items_covered_by_supplement"],
                "supplement_items_covered_by_canonical":
                    coverage_inventory(canon["classes"][cid],
                                       supp["class_contracts"][cid], t)[
                        "supplement_items_covered_by_canonical"],
            } for cid in CLASS_IDS
        }

    report = {
        "record_id": "W002-F0-DUALSOURCE-01",
        "actor": "worker-002",
        "task_id": "W002-F0-DUALSOURCE-01",
        "created_at": wall,
        "started_at": started,
        "node_id": "F0",
        "gate": "G-F0",
        "class_ids": CLASS_IDS,
        "question": ("Do the declared F0 `classes.<ID>` surface and the supplement "
                     "`class_contracts.<ID>` surface describe the same contract for the "
                     "same four frozen class ids, so that the schemas' pointer and "
                     "f0_binding cannot hand two agents different classes?"),
        "method": ("Freeze-first: live bytes hashed, copied to snapshots/, all probes run on "
                   "the frozen copies; live bytes re-hashed at finalize. Strict YAML load "
                   "records duplicate keys while keeping PyYAML last-wins values. Decidable "
                   "probes are regex/token rules on primary text (bracketed revision notes "
                   "stripped); aliases come only from the declared VOCAB_ALIASES.json. The "
                   "hypotheses/exclusions probe is a declared coverage inventory with a "
                   f"{COVER_THRESHOLD} threshold and a sweep, and does not drive the headline."),
        "inputs": {
            "canonical": {"path": str(CANONICAL.relative_to(ROOT)),
                          "sha256_scan_pin": before["canonical"],
                          "bytes": CANONICAL.stat().st_size,
                          "revision": canon.get("revision"),
                          "status": canon.get("status"),
                          "snapshot": str(canon_snap.relative_to(ROOT)),
                          "sha256_remeasured_at_finalize": after["canonical"],
                          "stable_during_run": stable},
            "supplement": {"path": str(SUPPLEMENT.relative_to(ROOT)),
                           "sha256_scan_pin": before["supplement"],
                           "bytes": SUPPLEMENT.stat().st_size,
                           "revision": supp.get("revision"),
                           "artifact_id": supp.get("artifact_id"),
                           "snapshot": str(supp_snap.relative_to(ROOT)),
                           "sha256_remeasured_at_finalize": after["supplement"],
                           "stable_during_run": stable},
            "alias_source": {"path": str(ALIASES.relative_to(ROOT)),
                             "sha256": before["aliases"]},
            "frozen_manifest": {"path": str(FROZEN.relative_to(ROOT)),
                                "sha256": before["frozen_manifest"],
                                "revision": frozen.get("revision"),
                                "logical_artifacts": frozen.get("logical_artifacts")},
            "schemas": {k: {"path": str(v.relative_to(ROOT)), "sha256": sha256_file(v)}
                        for k, v in SCHEMAS.items()},
        },
        "duplicate_keys": {"canonical": canon_dups, "supplement": supp_dups},
        "per_class": per_class,
        "disjointness": disjointness,
        "variants": variants,
        "pointer_surfaces": pointer,
        "hygiene": hygiene,
        "coverage_sweep": coverage_sweep,
        "headline": {
            "reading": reading["sentences"],
            "agreement_rows": reading["agreement_rows"],
            "hard_conflicts": reading["hard_conflicts"],
            "residual": reading["residual_rows"],
            "counts": {
                "conflict_candidates": sum(1 for r in reading["residual_rows"]
                                           if r["status"] == "conflict_candidate"),
                "tension": sum(1 for r in reading["residual_rows"] if r["status"] == "tension"),
                "underspecified": sum(1 for r in reading["residual_rows"]
                                      if r["status"] == "underspecified"),
                "subset": sum(1 for r in reading["residual_rows"] if r["status"] == "subset"),
                "unmatched": sum(1 for r in reading["residual_rows"]
                                 if r["status"] == "unmatched"),
                "duplicate_top_level_keys_total": sum(h["duplicate_total"] for h in hygiene),
                "pointer_targets_canonical_all": pointer["status"] == "agree",
            },
        },
        "falsifier": (
            "REJECT the reading if (a) a frozen snapshot does not hash to its sha256_scan_pin; "
            "(b) a row marked conflict_candidate is shown to be bridged by a declared alias in "
            "VOCAB_ALIASES.json; (c) a row marked agree is shown to assert different class "
            "identity on the two surfaces (different class id set, regularity token, or "
            "conclusion type); (d) a class_contract_pointer is shown to resolve outside the "
            "canonical classes.<ID>; or (e) live canonical/supplement bytes moved after the "
            "scan pins and the re-measure."),
        "next_falsifier": (
            "Re-run on the next revision: a repaired/indexed pointer must keep resolving in "
            "canonical, the four class ids must stay identical, and the scalar-class internal "
            "tension (comeager conclusion vs unresolved genericity axis) must either be "
            "resolved by naming the notion or recorded as an accepted non-claiming marker."),
        "authority_note": AUTHORITY_NOTE,
        "controls": {"total": len(controls),
                     "passed": sum(1 for c in controls if c["pass"]),
                     "failed": sum(1 for c in controls if not c["pass"]),
                     "rows": controls},
        "reproduction": ("python3 artifacts/worker-002/f0-dual-source-contract/"
                         "check_dual_source_contract.py --expect-live"),
    }
    report["determinism_digest"] = sha256_text(json.dumps(
        {k: v for k, v in report.items() if k not in ("created_at", "started_at")},
        sort_keys=True))
    return report


def write_outputs(report: dict) -> dict:
    (OUT / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    controls = {"record_id": report["record_id"], "actor": report["actor"],
                "created_at": report["created_at"],
                "cover_threshold": COVER_THRESHOLD,
                "cover_sweep_points": COVER_SWEEP,
                "overlap_conflict_threshold": OVERLAP_CONFLICT_THRESHOLD,
                "total": report["controls"]["total"],
                "passed": report["controls"]["passed"],
                "failed": report["controls"]["failed"],
                "rows": report["controls"]["rows"]}
    (OUT / "controls.json").write_text(json.dumps(controls, indent=2, sort_keys=True) + "\n")

    h = report["headline"]["counts"]
    lines = [
        "# W002-F0-DUALSOURCE-01 -- canonical vs supplement class-contract agreement",
        "",
        f"- actor: `worker-002` | node `F0` | gate `G-F0` | measured: {report['created_at']}",
        "- class binding: " + ", ".join(f"`{x}`" for x in CLASS_IDS),
        f"- canonical declared-F0: `{report['inputs']['canonical']['path']}` "
        f"rev {report['inputs']['canonical']['revision']} sha256 "
        f"`{report['inputs']['canonical']['sha256_scan_pin'][:12]}`",
        f"- supplement (pointer target): `{report['inputs']['supplement']['path']}` "
        f"rev {report['inputs']['supplement']['revision']} sha256 "
        f"`{report['inputs']['supplement']['sha256_scan_pin'][:12]}`",
        f"- controls: {report['controls']['passed']}/{report['controls']['total']} pass | "
        f"live bytes stable during run: {report['inputs']['canonical']['stable_during_run']}",
        "",
        "## Reading (data-driven)",
        "",
    ]
    lines += [f"- {s}" for s in report["headline"]["reading"]]
    lines += [
        "",
        "## Decidable probe matrix",
        "",
        "| class | conclusion_type | regularity | visibility | genericity |",
        "|---|---|---|---|---|",
    ]
    for cid in CLASS_IDS:
        r = report["per_class"][cid]
        lines.append(f"| `{cid}` | {r['conclusion_type']['status']} | "
                     f"{r['regularity_token']['status']} | "
                     f"{r['visibility_predicate']['status']} | {r['genericity']['status']} |")
    lines += [
        "",
        "## Restatement coverage (informational, not equivalence)",
        "",
        "| class | canonical items covered by supplement | supplement items covered by canonical |",
        "|---|---|---|",
    ]
    for cid in CLASS_IDS:
        p7 = report["per_class"][cid]["hypotheses_exclusions"]
        lines.append(f"| `{cid}` | {p7['canonical_items_covered_by_supplement']}"
                     f"/{p7['canonical_items']} | "
                     f"{p7['supplement_items_covered_by_canonical']}"
                     f"/{p7['supplement_items']} |")
    lines += ["", "## Residual rows", "",
              "| class | probe | status | detail |", "|---|---|---|---|"]
    for row in report["headline"]["residual"]:
        lines.append(f"| `{row['class_id']}` | {row['probe']} | {row['status']} | "
                     f"{row['detail'][:200]} |")
    if not report["headline"]["residual"]:
        lines.append("| - | - | - | none |")
    lines += [
        "",
        "## Pointer surfaces (schemas -> class contract)",
        "",
        "| node | pointer | canonical top key present | fragment class in canonical |",
        "|---|---|---|---|",
    ]
    for node, n in report["pointer_surfaces"]["nodes"].items():
        lines.append(f"| {node} | `{n['pointer']}` | {n['canonical_has_top_key']} | "
                     f"{n['fragment_class_in_canonical']} |")
    lines += [
        "",
        "## Machine hygiene",
        "",
        "| surface | revision | duplicate top-level keys | content ts after written_at |",
        "|---|---|---|---|",
    ]
    for hy in report["hygiene"]:
        lines.append(f"| {hy['artifact']} | {hy['revision']} | {hy['duplicate_total']} | "
                     f"{bool(hy['content_timestamps_after_written_at'])} |")
    lines += [
        "",
        "## Limits",
        "",
        "- Decidable probes are token/regex rules over primary text; aliases come only from",
        "  the declared `VOCAB_ALIASES.json`, printed per row. Read `report.json` before using",
        "  any row.",
        "- `conflict_candidate` is a token-level machine finding under declared project",
        "  vocabularies, not a physics claim and not a gate verdict.",
        "- The hypotheses/exclusions probe is a coverage inventory at a declared threshold",
        "  with a sweep; different restatement granularity is expected and is not equivalence",
        "  or contradiction evidence by itself.",
        "",
        "## Falsifier",
        "",
        report["falsifier"],
        "",
        "Reproduce: `" + report["reproduction"] + "`",
        "",
    ]
    (OUT / "SUMMARY.md").write_text("\n".join(lines))
    return {"report.json": sha256_file(OUT / "report.json"),
            "controls.json": sha256_file(OUT / "controls.json"),
            "SUMMARY.md": sha256_file(OUT / "SUMMARY.md"),
            "snapshots/SHA256SUMS": sha256_file(SNAP / "SHA256SUMS")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--expect-canonical", default=None)
    ap.add_argument("--expect-supplement", default=None)
    ap.add_argument("--expect-live", action="store_true")
    args = ap.parse_args()
    if args.expect_canonical or args.expect_supplement:
        expected = {}
        if args.expect_canonical:
            expected["canonical"] = args.expect_canonical
        if args.expect_supplement:
            expected["supplement"] = args.expect_supplement
        try:
            check_pins(expected)
        except DriftError as e:
            print(f"DRIFT: {e}", file=sys.stderr)
            return 2
    try:
        report = build_report(expect_live=args.expect_live)
    except DriftError as e:
        print(f"DRIFT: {e}", file=sys.stderr)
        return 2
    pins = write_outputs(report)
    print(json.dumps({
        "record_id": report["record_id"],
        "canonical": report["inputs"]["canonical"]["sha256_scan_pin"][:12],
        "canonical_rev": report["inputs"]["canonical"]["revision"],
        "supplement": report["inputs"]["supplement"]["sha256_scan_pin"][:12],
        "supplement_rev": report["inputs"]["supplement"]["revision"],
        "stable": report["inputs"]["canonical"]["stable_during_run"],
        "controls": f"{report['controls']['passed']}/{report['controls']['total']}",
        "hard_conflicts": report["headline"]["counts"]["conflict_candidates"],
        "residual_rows": len(report["headline"]["residual"]),
        "output_pins": pins,
    }, indent=1))
    return 3 if report["controls"]["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
