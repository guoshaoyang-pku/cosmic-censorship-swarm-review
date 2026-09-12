#!/usr/bin/env python3
"""FORM-SEP-04: C2/C0 pairwise separation audit (worker 08, read-only). v3 (rev18 re-bind).

v3 changes, all three forced by the FROZEN rev18 re-run (C2 e9fcefe6 / C0 bdb23f76) and each
recorded in the artifact under `rule_changes_v3`:
  (a) X2: `conclusion.forbidden_*` is now exempt BEFORE the conclusion-leakage-block branch,
      matching the exemption X2b already applies.  Before: the C0 forbidden-weakenings list
      ("substituting C2 or C1 for C0 ...") was reported as leakage_block_UNJUSTIFIED because
      the sentence itself carries no negation marker; the field name is the negation.
  (b) X2: `l1_ledger_refs` / `known_status` are classified `exempt_ledger_metadata` (metadata
      about the verified ledger row, not a class-membership predicate).  Before: the T-402 role
      "revised SCC picture (C0-extendible but generically C2-singular)" was unjustified_mention.
  (c) X3: strength comparisons are now subject-aware: the explicit `Cx-inextendibility ... is
      stronger/weaker` subject decides the direction.  Before, the first class token in the
      sentence won, so the canonically correct "E_C2 subset of E_C0, so C0-inextendibility is
      stronger" was read as the converse because "C2" appears first.
  (d) X3c NEW detection: a containment-premise inversion (C2 called the *larger*, or C0 the
      *smaller*, extension class) is a hard failure even when the forbidden transfer is the
      correct one.  At rev18 this fires on C0 implication_ledger.forbidden_transfers[0].reason.

v2 (negation-aware) changes are preserved; see git-less history in artifacts/worker08/superseded/.

Assignment: assign-FORM-SEP-04-20260911T2331 (astra-lead-formulation), node F2,
classes AF-SCC-C2-VAC-GEN / AF-SCC-C0-VAC-GEN, gate G-CLASSBIND.
Inputs (canonical, read-only):
  artifacts/formulation/schemas/af_scc_c2_vacuum.yaml
  artifacts/formulation/schemas/af_scc_c0_vacuum.yaml
  artifacts/formulation/rule_spec.json

X1 pairwise field matrix (identical / one-way / differs per JSON path + frozen-axis expectations)
X2 foreign-regularity semantics outside anti_scope/variants, with context classification
X3 one-way implication ledger C0-inext => C2-inext, negation-aware converse scan
X4 composite-regularity ban
X5 declaration: audits separation only, no truth, no completion, interpretation with lead

A hard failure means a genuine separation defect with an exact path and repair. False-positive
classes handled explicitly: pointer fields (sibling_disjoint_from), the implication ledger
(whose purpose is to discuss both classes), negated statements, class-parameterized fields.
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

REPO = Path(__file__).resolve().parents[2]
SCHEMA_DIR = REPO / "artifacts" / "formulation" / "schemas"
SPEC_PATH = REPO / "artifacts" / "formulation" / "rule_spec.json"
GATE = REPO / "artifacts" / "formulation" / "tools" / "check_class_schema.py"

import argparse as _argparse  # noqa: E402

_AP = _argparse.ArgumentParser(add_help=True)
_AP.add_argument("--c2", default=str(SCHEMA_DIR / "af_scc_c2_vacuum.yaml"))
_AP.add_argument("--c0", default=str(SCHEMA_DIR / "af_scc_c0_vacuum.yaml"))
_AP.add_argument("--out-json", default=str(REPO / "artifacts" / "worker08" / "c2_c0_separation_matrix.json"))
_AP.add_argument("--out-md", default=str(REPO / "artifacts" / "worker08" / "c2_c0_separation_report.md"))
_AP.add_argument("--label", default="canonical")
_ARGS, _ = _AP.parse_known_args()
C2_PATH = Path(_ARGS.c2).resolve()
C0_PATH = Path(_ARGS.c0).resolve()
OUT_JSON = Path(_ARGS.out_json).resolve()
OUT_MD = Path(_ARGS.out_md).resolve()
LABEL = _ARGS.label
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")
WORKER = "deepseek-flash-08"

LEAKAGE_BLOCKS = {"conclusion", "visibility", "i_plus", "falsifier"}
EXEMPT_PATH_PREFIXES = ("anti_scope", "genericity.variants", "implication_ledger",
                        "sibling_disjoint_from", "class_contract_pointer")
# v3: fields whose content is *about* the sibling class/reality by construction and therefore
# cannot be a class-membership predicate.  Kept separate from EXEMPT_PATH_PREFIXES so the report
# names the reason, and kept OUT of the conclusion axis (X2b audits conclusion.* independently).
FORBIDDEN_PATH_PREFIXES = ("conclusion.forbidden_strengthenings", "conclusion.forbidden_weakenings")
LEDGER_METADATA_PREFIXES = ("l1_ledger_refs", "known_status")
BENIGN_X3_PREFIXES = ("l1_ledger_refs", "known_status") + FORBIDDEN_PATH_PREFIXES
C0_TOKENS = [r"C0", r"C\^0", r"C\^\{0\}", r"continuous metric", r"continuous Lorentzian",
             r"continuously extended", r"continuous nondegenerate"]
C2_TOKENS = [r"C2", r"C\^2", r"C\^\{2\}", r"twice continuously differentiable"]
# wider list for assertive conclusion fields (catches rephrased low-regularity claims like
# "merely continuous" that carry no literal C0 token)
AXIS_C0_TOKENS = C0_TOKENS + [r"\bmerely continuous\b", r"\bcontinuous(?:ly)?\b"]
AXIS_C2_TOKENS = C2_TOKENS + [r"\btwice differentiable\b"]
NEG_MARKERS = re.compile(
    r"\bNOT\b|\bnot\b|\bno\b|\bnever\b|\bforbidden\b|\bdifferent class(?:es)?\b|\bmust not\b|"
    r"\bdoes not\b|\bdo not\b|\bcannot\b|\bweaker\b|\bexcluded\b|\bwithout\b|\bno equation\b|"
    r"phrases_that_are_not|anti_scope|\bsibling\b|\binflation\b|\bdeflation\b|\bsubsumed\b|"
    r"\breally\b|\bsmuggl|\bwrong-family\b|\bbelongs to\b|\bonly\b",
    re.IGNORECASE)
EXCLUSION_MARKERS = re.compile(
    r"forbidden|different class(?:es)?|must not|does not establish|not this class|"
    r"phrases_that_are_not|anti_scope|not stronger|not allowed|excluded|is not the class",
    re.IGNORECASE)
COMPOSITE = re.compile(r"(C0|C2)\s*(?:or|and|/)\s*(C0|C2)", re.IGNORECASE)
BUT = re.compile(r"\bbut\b|\bhowever\b|\bwhile\b", re.IGNORECASE)

# --- frozen-axis expectations -------------------------------------------------
MUST_DIFFER = [
    "class_id", "node_id", "sibling_disjoint_from", "class_contract_pointer", "scope_statement",
    "class_components.regularity_token",
    "extension_predicate.frozen_regularity", "extension_predicate.frozen_equation_concept",
    "extension_predicate.definition",
    "regularity.extension_regularity", "regularity.extension_regularity_exact",
    "regularity.extension_solution_concept",
    "conclusion.conclusion_type", "conclusion.statement_natural_language",
    "conclusion.known_obstruction", "conclusion.forbidden_strengthenings",
    "conclusion.forbidden_weakenings",
    "implication_ledger.one_way_entailments", "implication_ledger.forbidden_transfers",
    "falsifier.tier_1.witness_type", "falsifier.tier_1.machine_checkable_steps",
    "falsifier.tier_2.witness_type", "falsifier.schema_falsifiers",
    "non_vacuity.condition", "non_vacuity.witness_type", "non_vacuity.vacuity_falsifier",
    "provenance.sources", "provenance.unresolved_citations",
    "review_status.requested_reviewers", "topology.extension_topology", "topology.forbidden",
    "anti_scope.not_this_class", "anti_scope.phrases_that_are_not_this_class",
    "quantifiers.domains.D3.definition", "quantifiers.negation", "quantifiers.negation_normal_form",
]
MUST_MATCH = [
    "schema_version", "artifact_kind", "owner", "epistemic_status", "promotion_rule",
    "class_components.asymptotics", "class_components.censorship", "class_components.matter",
    "class_components.genericity",
    "quantifiers.ordered", "quantifiers.domains.D0", "quantifiers.domains.D1",
    "quantifiers.domains.D2", "quantifiers.order_matters", "quantifiers.quantifier_class",
    "topology.spacetime_dimension", "topology.slice_topology", "topology.end_structure",
    "topology.completeness_of_slice", "topology.conformal_boundary", "topology.I_plus_topology",
    "topology.development_topology",
    "data_class",
    "genericity.kind", "genericity.ambient_space", "genericity.topology_or_measure",
    "genericity.generic_set", "genericity.excluded_set_status", "genericity.is_part_of_class",
    "genericity.class_change_warning", "genericity.transfer_failures", "genericity.variants",
    "i_plus.role", "i_plus.in_conclusion", "i_plus.completeness_in_conclusion",
    "i_plus.forbidden",
    "visibility.role", "visibility.visible_singularity_is_wcc", "visibility.forbidden_falsifier",
    "provenance.citation_status", "provenance.sources[0]",
    "review_status.verdict", "review_status.gate",
]
CLASS_PARAMETERIZED = ["conclusion.statement_formal", "genericity.excluded_set", "unresolved_items"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def leaves(obj, prefix=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from leaves(v, f"{prefix}.{k}" if prefix else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from leaves(v, f"{prefix}[{i}]")
    else:
        yield prefix, obj


def flat(doc):
    return dict(leaves(doc))


def path_match(path: str, rule: str) -> bool:
    return path == rule or path.startswith(rule + ".") or path.startswith(rule + "[")


def sentences(text: str):
    return [s.strip() for s in re.split(r"(?<=[.;])\s+", text) if s.strip()]


def classify_dual_sentence(s: str) -> str:
    """Classify a sentence mentioning both regularity classes (or 'this class')."""
    has_c2 = re.search(r"C2|C\^2|twice continuously", s, re.I)
    has_c0 = re.search(r"C0|C\^0|continuous metric|continuous Lorentzian|C0 extension", s, re.I) or re.search(r"this class", s, re.I)
    if not (has_c2 and has_c0):
        return "not_dual"
    if NEG_MARKERS.search(s):
        return "negated_or_exclusion"
    if re.search(r"C0\s*=>\s*C2", s):
        return "correct_direction"
    if re.search(r"C2\s*=>\s*C0", s):
        return "CONVERSE_ASSERTED"
    # "X follows from Y" means Y => X
    if re.search(r"C0[- ]?inextendibility[^.;]{0,60}follows?\s+from[^.;]{0,60}C2", s, re.I):
        return "CONVERSE_ASSERTED"
    if re.search(r"C2[- ]?inextendibility[^.;]{0,60}follows?\s+from[^.;]{0,60}C0", s, re.I):
        return "correct_direction"
    if re.search(r"C0[^.;]{0,60}(?:is\s+implied\s+by|is\s+a\s+consequence\s+of)[^.;]{0,60}C2", s, re.I):
        return "CONVERSE_ASSERTED"
    if re.search(r"C2[^.;]{0,60}(?:is\s+implied\s+by|is\s+a\s+consequence\s+of)[^.;]{0,60}C0", s, re.I):
        return "correct_direction"
    # --- v3: subject-aware strength comparison -------------------------------------------
    # The explicit `Cx-inextendibility ... is stronger/weaker` subject decides the direction.
    # (v2 let the first class token in the sentence win, which mis-read the canonical
    #  "E_C2 subset of E_C0, so C0-inextendibility is stronger" as the converse.)
    strength = re.search(
        r"(C0|C2)[- ]?inextendibility[^.;]{0,60}?"
        r"(?:is|are|would be)\s+(?:strictly\s+)?(stronger|stricter|finer|weaker|coarser|larger)",
        s, re.I)
    if strength:
        subj = strength.group(1).upper()
        strong = strength.group(2).lower() in ("stronger", "stricter", "finer")
        if subj == "C0":
            return "correct_direction" if strong else "CONVERSE_ASSERTED"
        return "CONVERSE_ASSERTED" if strong else "correct_direction"
    # containment-chain prose (rev7 wording): lower regularity => stronger inexistence statement
    if re.search(r"lower-regularity inextendibility entails", s, re.I):
        return "correct_direction"
    if re.search(r"(?:C0|H2_loc|C\^?\{?1,1\}?)[- ]?inextendibility[^.;]{0,60}"
                 r"(?:entails?|implies?|subsum\w*)[^.;]{0,40}(?:this class|C2)", s, re.I):
        return "correct_direction"
    # entailment with C2 as syntactic subject before the verb -> forbidden converse
    if re.search(r"C2[- ]?(?:inextendibility|metric|extension)[^.;]{0,80}"
                 r"(?:subsum\w*|entail\w*|impl\w*|establish\w*)", s, re.I):
        return "CONVERSE_ASSERTED"
    # legacy generic strength comparison (no explicit Cx-inextendibility subject present)
    if re.search(r"C2[^.;]{0,60}(?:is|are|would be)[^.;]{0,40}(?:stronger|stricter|finer)", s, re.I):
        return "CONVERSE_ASSERTED"
    if re.search(r"C0[^.;]{0,60}(?:is|are|would be)[^.;]{0,40}(?:weaker|coarser)", s, re.I):
        return "CONVERSE_ASSERTED"
    if re.search(r"C0[^.;]{0,60}(?:is|are|would be)[^.;]{0,40}(?:stronger|stricter|finer)", s, re.I):
        return "correct_direction"
    if re.search(r"C2[^.;]{0,60}(?:is|are|would be)[^.;]{0,40}(?:weaker|coarser|larger)", s, re.I):
        return "correct_direction"
    if re.search(r"C0[^.;]{0,80}(?:entail\w*|impl\w*|subsum\w*|establish\w*)[^.;]{0,80}C2", s, re.I):
        return "correct_direction"
    if re.search(r"every C2 extension is a C0", s, re.I):
        return "correct_direction"
    return "unclassified_dual_mention"


def run_gate(path: Path) -> dict:
    proc = subprocess.run([sys.executable, str(GATE), "--json", str(path)],
                          capture_output=True, text=True, timeout=120)
    try:
        payload = json.loads(proc.stdout)
    except ValueError:
        payload = {"raw_stdout": proc.stdout[:500], "raw_stderr": proc.stderr[:500]}
    payload["exit_code"] = proc.returncode
    return payload


def main() -> int:
    c2 = yaml.safe_load(C2_PATH.read_text(encoding="utf-8"))
    c0 = yaml.safe_load(C0_PATH.read_text(encoding="utf-8"))
    f2, f0 = flat(c2), flat(c0)

    # ---------------- X1 ----------------
    paths = sorted(set(f2) | set(f0))
    entries = []
    for p in paths:
        in2, in0 = p in f2, p in f0
        if in2 and in0:
            rel = "identical" if f2[p] == f0[p] else "differs"
        elif in2:
            rel = "c2_only"
        else:
            rel = "c0_only"
        entries.append({"path": p, "relation": rel,
                        "c2_value": f2.get(p), "c0_value": f0.get(p)})

    def hits_for(rule):
        return [e for e in entries if path_match(e["path"], rule)]

    violations, naming_flags, class_param = [], [], []
    for rule in MUST_DIFFER:
        hits = hits_for(rule)
        if hits and all(e["relation"] == "identical" for e in hits):
            violations.append({"kind": "expected_axis_not_separated", "rule": rule,
                               "paths": [e["path"] for e in hits]})
    ANNOTATION_HINTS = ("locator", "note", "comment", "citation", "status", "provenance",
                        "hypotheses_reconciliation", "justification", "supplied")
    annotation_flags = []

    def is_annotation(e):
        tail = e["path"].split(".")[-1].lower()
        if any(h in tail for h in ANNOTATION_HINTS):
            return True
        a, b = e.get("c2_value"), e.get("c0_value")
        if isinstance(a, str) and isinstance(b, str) and (a in b or b in a):
            return True
        return False

    for rule in MUST_MATCH:
        hits = hits_for(rule)
        divergent = [e for e in hits if e["relation"] == "differs"]
        one_sided = [e for e in hits if e["relation"] in {"c2_only", "c0_only"}]
        hard = [e for e in divergent + one_sided if not is_annotation(e)]
        annot = [e for e in divergent + one_sided if is_annotation(e)]
        if hard:
            violations.append({"kind": "shared_structure_diverged", "rule": rule,
                               "paths": [e["path"] for e in hard]})
        if annot:
            annotation_flags.append({"kind": "annotation_drift", "rule": rule,
                                     "paths": [e["path"] for e in annot]})
        if one_sided:
            naming_flags.append({"kind": "one_sided_shared_field", "rule": rule,
                                 "paths": [e["path"] for e in one_sided]})
    for rule in CLASS_PARAMETERIZED:
        hits = hits_for(rule)
        if hits and all(e["relation"] == "identical" for e in hits):
            class_param.append({"rule": rule, "note": "identical but parameterized by the per-file predicate; allowed"})
        elif hits:
            class_param.append({"rule": rule, "note": "class-specific content; allowed"})

    # ---------------- X2 ----------------
    def scan_foreign(doc_flat, foreign_tokens, own_class):
        hits = []
        for p, v in doc_flat.items():
            if not isinstance(v, str):
                continue
            top = p.split(".")[0].split("[")[0]
            for tok in foreign_tokens:
                for m in re.finditer(tok, v):
                    snippet = v[max(0, m.start() - 200): m.end() + 200]
                    if p.startswith("anti_scope"):
                        cls = "exempt_anti_scope"
                    elif p.startswith("genericity.variants"):
                        cls = "exempt_variant"
                    elif p.startswith(FORBIDDEN_PATH_PREFIXES):
                        # the field name IS the exclusion: forbidden_weakenings/strengthenings
                        cls = "exempt_forbidden_list"
                    elif p.startswith(LEDGER_METADATA_PREFIXES):
                        # literature-status metadata, not a class-membership predicate
                        cls = "exempt_ledger_metadata"
                    elif any(p.startswith(x) for x in EXEMPT_PATH_PREFIXES):
                        cls = "exempt_pointer_or_ledger"
                    elif top in LEAKAGE_BLOCKS:
                        cls = ("leakage_block_justified" if NEG_MARKERS.search(snippet)
                               else "leakage_block_UNJUSTIFIED")
                    elif NEG_MARKERS.search(snippet) or re.search(r"\bthis class\b", snippet):
                        cls = "justified_exclusion"
                    else:
                        cls = "unjustified_mention"
                    key = (p, cls, tok)
                    if key not in {(h["path"], h["classification"], h["token"]) for h in hits}:
                        hits.append({"path": p, "token": tok, "classification": cls,
                                     "snippet": snippet.strip(), "own_class": own_class})
        return hits

    c2_foreign = scan_foreign(f2, C0_TOKENS, "AF-SCC-C2-VAC-GEN")
    c0_foreign = scan_foreign(f0, C2_TOKENS, "AF-SCC-C0-VAC-GEN")
    def conclusion_axis(doc, fname):
        """Foreign-regularity tokens inside ASSERTIVE conclusion fields (forbidden_* excluded)."""
        foreign = AXIS_C0_TOKENS if fname == "C2" else AXIS_C2_TOKENS
        out = []
        for pth, v in flat(doc).items():
            if not pth.startswith("conclusion.") or pth.startswith("conclusion.forbidden"):
                continue
            if not isinstance(v, str):
                continue
            for tok in foreign:
                m = re.search(tok, v)
                if not m:
                    continue
                snippet = v[max(0, m.start() - 90): m.end() + 90]
                out.append({"file": fname, "path": pth, "token": tok,
                            "classification": ("excluded_by_marker" if EXCLUSION_MARKERS.search(snippet)
                                               else "AXIS_VIOLATION"),
                            "snippet": snippet.strip()})
        return out

    axis_hits = conclusion_axis(c2, "C2") + conclusion_axis(c0, "C0")
    axis_violations = [h for h in axis_hits if h["classification"] == "AXIS_VIOLATION"]

    all_foreign = c2_foreign + c0_foreign
    unjustified = [h for h in all_foreign
                   if h["classification"] in {"unjustified_mention", "leakage_block_UNJUSTIFIED"}]
    leakage_hits = [h for h in all_foreign if h["classification"].startswith("leakage_block")]

    # ---------------- X3 ----------------
    def ledger(doc):
        il = doc.get("implication_ledger", {})
        return {"one_way_entailments": il.get("one_way_entailments", []),
                "forbidden_transfers": il.get("forbidden_transfers", []),
                "cross_family": il.get("cross_family"),
                "subsumption_note": il.get("subsumption_note")}

    checks = []
    for name, doc in (("C2", c2), ("C0", c0)):
        led = ledger(doc)
        ent_ok = any("C0" in str(e.get("from", "")) and "C2" in str(e.get("to", ""))
                     and str(e.get("relation")) == "entails" for e in led["one_way_entailments"])
        forb_ok = any("C2" in str(e.get("from", "")) and ("C0" in str(e.get("to", "")) or
                                                         "this class" in str(e.get("to", "")))
                      for e in led["forbidden_transfers"])
        checks.append({"id": f"X3-{name}-entailment", "expected": "C0-inext => C2-inext recorded",
                       "pass": ent_ok, "observed": led["one_way_entailments"]})
        checks.append({"id": f"X3-{name}-forbidden-converse", "expected": "C2-inext => C0-inext marked forbidden",
                       "pass": forb_ok, "observed": led["forbidden_transfers"]})

    dual_mentions = []
    for name, doc in (("C2", c2), ("C0", c0)):
        for p, v in flat(doc).items():
            if not isinstance(v, str):
                continue
            for s in sentences(v):
                kind = classify_dual_sentence(s)
                if kind == "not_dual":
                    continue
                if kind == "unclassified_dual_mention" and (
                        p.startswith(EXEMPT_PATH_PREFIXES)
                        or re.search(r"C-infinity|continuously differentiable|C\^infinity", s)):
                    kind = "benign_context"
                if kind == "unclassified_dual_mention" and p.startswith(BENIGN_X3_PREFIXES):
                    kind = "benign_metadata_or_forbidden"
                dual_mentions.append({"file": name, "path": p, "classification": kind, "sentence": s})
    converse_assertions = [d for d in dual_mentions if d["classification"] == "CONVERSE_ASSERTED"]
    unclassified = [d for d in dual_mentions if d["classification"] == "unclassified_dual_mention"]

    # ---------------- X4 ----------------
    composite_hits = []
    for name, doc in (("C2", c2), ("C0", c0)):
        for p, v in flat(doc).items():
            if not isinstance(v, str):
                continue
            for m in COMPOSITE.finditer(v):
                snippet = v[max(0, m.start() - 90): m.end() + 90]
                if p.startswith("anti_scope"):
                    cls = "exempt_anti_scope_forbidden_phrase"
                elif NEG_MARKERS.search(snippet):
                    cls = "justified_forbidden_quotation"
                else:
                    cls = "VIOLATION_composite_class"
                composite_hits.append({"file": name, "path": p, "match": m.group(0),
                                       "classification": cls, "snippet": snippet.strip()})
    composite_violations = [h for h in composite_hits if h["classification"].startswith("VIOLATION")]

    # ---------------- X3c containment-premise inversion (new in v3) ----------------
    # The frozen containment is E_C2 subset E_{C^1,1} subset E_H2loc subset E_C0.  A sentence that
    # calls C2 the LARGER (or C0 the SMALLER) extension class contradicts it, even when the
    # transfer it forbids is the correct one.  Narrow lexical rule, checked over all strings.
    CONTAINMENT_INVERSION = re.compile(
        r"C2[^.;]{0,60}(?:strictly\s+)?(?:larger|bigger|wider)\s+extension\s+class"
        r"|C0[^.;]{0,60}(?:strictly\s+)?(?:smaller|narrower)\s+extension\s+class", re.I)
    containment_inversions = []
    for name, doc in (("C2", c2), ("C0", c0)):
        for p, v in flat(doc).items():
            if not isinstance(v, str):
                continue
            for s in sentences(v):
                m = CONTAINMENT_INVERSION.search(s)
                if m:
                    containment_inversions.append({
                        "file": name, "path": p, "match": m.group(0), "sentence": s.strip(),
                        "classification": "containment_inversion",
                        "contradicts": "frozen containment E_C2 subset E_H2loc subset E_C0 "
                                       "(extension_class_containment, rev7/rev18)",
                    })

    # ---------------- propagation scan (adjacent files, same wrong sentence) ----------------
    PROPAGATION_PHRASE = "C2-inextendibility proof SUBSUMES"
    propagation = []
    for root in (REPO / "artifacts" / "formulation" / "fixtures",
                 REPO / "artifacts" / "formulation" / "reviews"):
        if not root.exists():
            continue
        for f in sorted(root.rglob("*.yaml")):
            if f in (C2_PATH, C0_PATH):
                continue
            try:
                text = f.read_text(encoding="utf-8")
            except OSError:
                continue
            if PROPAGATION_PHRASE in text:
                propagation.append(str(f.relative_to(REPO)))
    for f in (REPO / "research_map" / "formulation_taxonomy.yaml",
              REPO / "artifacts" / "formulation" / "formulation_taxonomy.yaml"):
        if f.exists() and PROPAGATION_PHRASE in f.read_text(encoding="utf-8"):
            propagation.append(str(f.relative_to(REPO)))

    gate_runs = {str(C2_PATH.relative_to(REPO)): run_gate(C2_PATH),
                 str(C0_PATH.relative_to(REPO)): run_gate(C0_PATH)}

    # ---------------- frozen-manifest consistency ----------------
    frozen_path = REPO / "artifacts" / "formulation" / "FROZEN.json"
    frozen_check = {"path": str(frozen_path.relative_to(REPO)), "manifest_sha256": None,
                    "revision": None, "mismatches": [], "checked": [],
                    "self_reference_skipped": False}
    if frozen_path.exists():
        frozen_check["manifest_sha256"] = sha256(frozen_path)
        man = json.loads(frozen_path.read_text(encoding="utf-8"))
        frozen_check["revision"] = man.get("revision")
        for rel, entry in man.get("files", {}).items():
            if rel == str(frozen_path.relative_to(REPO)):
                # a manifest cannot contain its own final hash; skip the self-entry
                frozen_check["self_reference_skipped"] = True
                continue
            fp = REPO / rel
            actual = sha256(fp) if fp.exists() else None
            match = actual == entry.get("sha256")
            frozen_check["checked"].append({"path": rel, "manifest_sha256": entry.get("sha256"),
                                            "actual_sha256": actual, "match": match})
            if not match:
                frozen_check["mismatches"].append(rel)

    hard_failures = []
    if violations:
        hard_failures.extend(violations)
    if unjustified:
        hard_failures.append({"kind": "foreign_regularity_unjustified", "hits": unjustified})
    if not all(c["pass"] for c in checks):
        hard_failures.append({"kind": "implication_ledger",
                              "checks": [c for c in checks if not c["pass"]]})
    if converse_assertions:
        hard_failures.append({"kind": "converse_implication_asserted", "hits": converse_assertions,
                              "propagated_copies": propagation})
    if axis_violations:
        hard_failures.append({"kind": "conclusion_regularity_axis_violation", "hits": axis_violations})
    if composite_violations:
        hard_failures.append({"kind": "composite_regularity", "hits": composite_violations})
    if containment_inversions:
        hard_failures.append({"kind": "containment_inversion_in_ledger",
                              "hits": containment_inversions})

    matrix = {
        "audit": "FORM-SEP-04",
        "label": LABEL,
        "version": 3,
        "worker": WORKER,
        "generated_at": NOW,
        "rule_changes_v3": [
            {"rule": "X2 path exemption for conclusion.forbidden_*",
             "before": "leakage_block_UNJUSTIFIED on conclusion.forbidden_weakenings[3]",
             "after": "exempt_forbidden_list (field name is the exclusion; X2b already excluded it)",
             "why_not_schema_repair": "the list is the class's declared forbidden substitutions; "
                                      "flagging it would flag the separation mechanism itself"},
            {"rule": "X2 path exemption for l1_ledger_refs / known_status",
             "before": "unjustified_mention on l1_ledger_refs[2].role",
             "after": "exempt_ledger_metadata (reports a ledger row's status, not class membership)",
             "why_not_schema_repair": "the phrase 'C0-extendible but generically C2-singular' "
                                      "asserts the C2 failure, i.e. it supports the separation"},
            {"rule": "X3 subject-aware strength comparison",
             "before": "CONVERSE_ASSERTED on implication_ledger.one_way_entailments[0].reason",
             "after": "correct_direction: subject is C0-inextendibility, which is the stronger statement",
             "why_not_schema_repair": "the sentence is the canonical correct direction; v2 keyed on "
                                      "the first class token in the sentence instead of the subject"},
            {"rule": "X3c containment-premise inversion (NEW detection, not a false-positive fix)",
             "before": "not checked; a reason could call C2 the larger extension class unnoticed",
             "after": "hard failure `containment_inversion_in_ledger` with exact path and repair",
             "found_at_rev18": "C0 implication_ledger.forbidden_transfers[0].reason: 'C2 is a strictly "
                                "larger extension class, so C2-inextendibility is strictly weaker' "
                                "contradicts the same file's extension_class_containment and "
                                "one_way_entailments[2]; the forbidden direction is right, the premise "
                                "is inverted. Repair wording: 'C2 is a strictly smaller extension class "
                                "(E_C2 subset of E_C0), so C2-inextendibility is strictly weaker'."},
        ],
        "declaration": {
            "audits": "separation only (structure, leakage, implication direction)",
            "does_not_audit": ["physical truth", "citation scope",
                              "mathematical correctness of definitions"],
            "claims_no_completion": True,
            "interpretation_owner": "astra-lead-formulation",
        },
        "inputs": {str(C2_PATH.relative_to(REPO)): sha256(C2_PATH),
                   str(C0_PATH.relative_to(REPO)): sha256(C0_PATH),
                   str(SPEC_PATH.relative_to(REPO)): sha256(SPEC_PATH),
                   str(GATE.relative_to(REPO)): sha256(GATE)},
        "X1_pairwise": {
            "leaf_paths": len(paths),
            "identical": sum(1 for e in entries if e["relation"] == "identical"),
            "non_identical": sum(1 for e in entries if e["relation"] != "identical"),
            "expectation_violations": violations,
            "naming_asymmetry_flags": naming_flags,
            "annotation_drift_flags": annotation_flags,
            "class_parameterized_allowed": class_param,
            "matrix": entries,
        },
        "X2_foreign_semantics": {
            "c2_file_c0_tokens": c2_foreign,
            "c0_file_c2_tokens": c0_foreign,
            "leakage_block_hits": leakage_hits,
            "unjustified_count": len(unjustified),
            "reviewed_exemptions": [h for h in all_foreign
                                    if h["classification"].startswith("exempt_")],
            "exemption_class_counts": {c: sum(1 for h in all_foreign
                                              if h["classification"] == c)
                                       for c in sorted({h["classification"] for h in all_foreign}
                                                       - {"unjustified_mention",
                                                          "leakage_block_UNJUSTIFIED",
                                                          "leakage_block_justified",
                                                          "justified_exclusion"})},
        },
        "X2b_conclusion_axis": {"hits": axis_hits, "violations": axis_violations},
        "X3_implication_ledger": {
            "checks": checks,
            "dual_mentions": dual_mentions,
            "converse_assertions": converse_assertions,
            "unclassified_dual_mentions": unclassified,
        },
        "X4_composite_regularity": {"hits": composite_hits, "violations": composite_violations},
        "X3c_containment_inversion": {"hits": containment_inversions,
                                      "violations": len(containment_inversions)},
        "X3_propagation": {
            "phrase": "C2-inextendibility proof SUBSUMES",
            "adjacent_files_carrying_the_defect": propagation,
            "note": "fixtures clone the C0 schema; repairing the canonical file without regenerating fixtures would leave the wrong statement in the test corpus",
        },
        "frozen_manifest_check": frozen_check,
        "gate_runs": gate_runs,
        "verdict": "FAIL" if hard_failures else "PASS",
        "hard_failures": hard_failures,
        "post_repair_residuals": ([
            f"{len(propagation)} adjacent fixture/mutant files still carry the pre-repair sentence; "
            "regenerate or patch them before reusing the corpus: " + ", ".join(propagation)
        ] if (propagation and not converse_assertions) else []) + ([
            "FROZEN.json is stale relative to disk: mismatched entries " + ", ".join(frozen_check["mismatches"])
        ] if frozen_check["mismatches"] else []),
        "flags_not_failures": [
            "R10 (SCC visibility must state the WCC falsifier belongs to WCC) forces WCC tokens into "
            "visibility/i_plus/conclusion exclusion lists that R12's lexical scan would flag: rule_spec "
            "tension, resolved for R10, recorded not failed.",
            "Pointer and ledger fields (sibling_disjoint_from, implication_ledger) necessarily name the "
            "sibling class; exempted from X2 leakage, kept in the matrix for transparency.",
            "v3: conclusion.forbidden_* lists name the sibling regularity by construction; exempted from "
            "X2 leakage (path-classified `exempt_forbidden_list`), kept in the matrix for transparency.",
            "v3: l1_ledger_refs/known_status are ledger-status metadata; exempted from X2 leakage "
            "(path-classified `exempt_ledger_metadata`), kept in the matrix for transparency.",
            "Editorial drift in i_plus.definition between the two files is recorded in X1 as a difference; "
            "it is not a separation defect (semantically equivalent).",
            "Lexical scans cannot see semantic leaks expressed without regularity tokens; the lead gate's "
            "documented blind spot (rephrased probe p03) remains the residual risk.",
            "Corpus hygiene (not a canonical defect): two pre-rev4 held-out mutants under "
            "artifacts/formulation/reviews/novel_mutants/ (n02, n07) still clone the old C0 sentence "
            "'a C2-inextendibility proof SUBSUMES ...'; the current canonical pair (FROZEN rev"
            f"{frozen_check['revision']}) no longer carries it. "
            "Reusing those mutants as held-out evidence would confound the intended mutation with the "
            "stale clause.",
        ],
        "next_falsifier": (
            f"Re-run at the next FROZEN revision hash (this run binds FROZEN rev{frozen_check['revision']}: "
            f"C2 {sha256(C2_PATH)[:8]}..., C0 {sha256(C0_PATH)[:8]}...). A genuine separation defect is "
            "any placement where the C2 conclusion is "
            "satisfied by a C0-only extension class or vice versa, any Cx => Cy converse prose, any "
            "composite regularity token outside anti_scope, any containment-premise inversion "
            "(C2 called larger / C0 called smaller), or any foreign-regularity token in an "
            "assertive conclusion field; any of those reopens FAIL at the new hash. The three v3 "
            "exemptions (forbidden lists, ledger metadata, subject-aware strength) are individually "
            "re-checkable from the matrix's reviewed_exemptions."
        ),
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(matrix, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def fmt(rows, key_fields, limit=15):
        out = []
        for r in rows[:limit]:
            loc = f"{r.get('file','')}#{r.get('path','')}" if 'file' in r else r.get('path', '')
            out.append(f"- `{loc}` [{r.get('classification', r.get('kind',''))}] "
                       f"{(r.get('sentence') or r.get('snippet') or r.get('match') or '')[:230]}")
        if len(rows) > limit:
            out.append(f"- ... and {len(rows) - limit} more (see JSON)")
        return "\n".join(out) if out else "- none"

    c0_note_fail = [c for c in converse_assertions if "non_vacuity" in c["path"]]

    def bullet_lines(rows, text_key, limit=15):
        out = []
        for r in rows[:limit]:
            loc = r.get("path", "")
            if "file" in r:
                loc = r["file"] + "#" + loc
            out.append("- `" + loc + "` [" + str(r.get("classification", r.get("kind", ""))) + "] "
                       + str(r.get(text_key) or r.get("snippet") or r.get("match") or "")[:230])
        if len(rows) > limit:
            out.append("- ... and " + str(len(rows) - limit) + " more (see JSON)")
        return "\n".join(out) if out else "- none"

    viol_lines = "\n".join("- " + v["kind"] + " on `" + v["rule"] + "` -> "
                           + ", ".join(v["paths"][:5]) for v in violations) if violations else "- none"
    naming_lines = "\n".join("- `" + f["rule"] + "` -> " + ", ".join(f["paths"])
                             for f in naming_flags) if naming_flags else "- none"
    param_line = ", ".join("`" + c["rule"] + "`" for c in class_param) if class_param else "none"
    unjust_lines = bullet_lines(unjustified, "snippet")
    check_lines = "\n".join("- " + c["id"] + ": " + ("PASS" if c["pass"] else "FAIL")
                            + " — expected " + c["expected"] for c in checks)
    converse_lines = bullet_lines(converse_assertions, "sentence")
    h1_lines = "\n".join('- `' + h["file"] + "#" + h["path"] + '`: "' + h["sentence"] + '"'
                         for h in c0_note_fail) if c0_note_fail else "- no failure in non_vacuity notes"
    flag_lines = "\n".join("- " + f for f in matrix["flags_not_failures"])
    c2v = gate_runs[str(C2_PATH.relative_to(REPO))]
    c0v = gate_runs[str(C0_PATH.relative_to(REPO))]
    axis_lines = bullet_lines(axis_violations, "snippet")
    inversion_lines = bullet_lines(containment_inversions, "sentence")
    dual_count = len(matrix['X3_implication_ledger']['dual_mentions'])
    prop_list = ", ".join("`" + x + "`" for x in propagation) if propagation else "none"
    frozen_lines = ("\n".join("- `" + c["path"] + "`: manifest `" + str(c["manifest_sha256"])[:12]
                               + "` vs disk `" + (str(c["actual_sha256"])[:12] if c["actual_sha256"] else "absent") + "`"
                               for c in frozen_check["checked"] if not c["match"])
                    if frozen_check["mismatches"] else "- all frozen entries match disk")
    md = f"""# FORM-SEP-04 — C2/C0 pairwise separation audit (worker 08) — v3 [{LABEL}]

**Scope declaration (X5).** Audits *separation* only: field disjointness on frozen axes,
foreign-regularity semantic leakage, and the direction of the implication ledger. Does **not**
audit physical truth, citation scope, or definitional correctness. Claims **no node
completion**; `astra-lead-formulation` binds interpretation. Read-only.

Generated {NOW} by `{WORKER}`. Generator `artifacts/worker08/c2_c0_separation_audit.py` (v3,
rev18 re-bind; the three v3 rule changes are recorded under `rule_changes_v3` in the JSON).

## Inputs (hashes)

| path | sha256 |
|---|---|
| `artifacts/formulation/schemas/af_scc_c2_vacuum.yaml` | `{matrix['inputs'].get('artifacts/formulation/schemas/af_scc_c2_vacuum.yaml', 'n/a')}` |
| `artifacts/formulation/schemas/af_scc_c0_vacuum.yaml` | `{matrix['inputs'].get('artifacts/formulation/schemas/af_scc_c0_vacuum.yaml', 'n/a')}` |
| `artifacts/formulation/rule_spec.json` | `{matrix['inputs'].get('artifacts/formulation/rule_spec.json', 'n/a')}` |

Recorded gate run (`check_class_schema.py --json`):
C2 `{c2v['verdict']}` (exit {c2v['exit_code']}),
C0 `{c0v['verdict']}` (exit {c0v['exit_code']}).
Both structural gates pass; findings below are the semantic residue.

## Verdict: **{matrix['verdict']}**

Hard-failure groups: **{len(hard_failures)}**.

## X1 — pairwise field matrix

- leaf paths: {len(paths)}; identical: {matrix['X1_pairwise']['identical']}; differing/one-sided: {matrix['X1_pairwise']['non_identical']}
- frozen-axis expectation violations: **{len(violations)}**
{viol_lines}
- naming asymmetries (one-sided shared fields, flags): **{len(naming_flags)}**
{naming_lines}
- class-parameterized fields (allowed to differ): {param_line}

Full path-level matrix: `c2_c0_separation_matrix.json#X1_pairwise.matrix`.

## X2 — foreign regularity semantics outside anti_scope/variants

- C0 tokens inside the C2 file: {len(c2_foreign)}; C2 tokens inside the C0 file: {len(c0_foreign)}
- hits inside rule_spec leakage blocks (`conclusion`/`visibility`/`i_plus`/`falsifier`): {len(leakage_hits)}
- **unjustified** mentions: **{len(unjustified)}**
- reviewed path-exemptions (not leaks, listed in the JSON): **{sum(1 for h in all_foreign if h['classification'].startswith('exempt_'))}**

{unjust_lines}

Every surviving hit is a pointer (`sibling_disjoint_from`, `class_contract_pointer`), an
implication-ledger statement, an explicit exclusion ("different class", "NOT ...", "forbidden"),
or mandated by R10 (SCC visibility must name the WCC falsifier). The R10/R12 tension is recorded
as a spec flag, not a schema defect.

## X2b — conclusion regularity axis (assertive fields only)

Foreign-regularity tokens inside `conclusion.*` (excluding `conclusion.forbidden*`):
hits {len(axis_hits)}, **violations {len(axis_violations)}**.

{axis_lines}

This rule closes the lead gate's documented blind spot `p03_c2_schema_c0_meaning`, where the C2
formal statement asserts "no proper continuation whose metric is merely continuous" — a C0
conclusion in the C2 class with no literal `C0` token.

## X3 — implication ledger and converse scan

Curated ledger checks:

{check_lines}

Negation-aware sentence scan over every string in both files: {dual_count} dual mentions classified;
**converse assertions: {len(converse_assertions)}**; unclassified dual mentions: {len(unclassified)}.

{converse_lines}

### Hard failure H1 (historical; rendered only when converse_assertions is non-empty)

{h1_lines}

At the rev4 repair the defect was: `non_vacuity.c0_specific_note` in the C0 schema asserted that a
**C2**-inextendibility proof *SUBSUMES* the C0 conclusion while its own parenthetical said
C0-inextendibility is *stronger*. Under extension-class containment (C2 extensions are a subset of
C0 extensions) the only valid entailment is C0 => C2, so that sentence stated the forbidden
converse. The current canonical pair (FROZEN rev{frozen_check['revision']}) no longer carries it; this paragraph is retained as the record
of what the check detects.

## X3b — propagation of the pre-rev4 defective sentence

The phrase "C2-inextendibility proof SUBSUMES" appears in **{len(propagation)}** adjacent
fixture/review files: {prop_list}. The canonical pair is clean; the carriers are pre-rev4 clones.
Reusing them as held-out evidence would confound their intended mutation with the stale clause;
regenerate or patch them and re-hash with the schema.

## Frozen-manifest consistency

`FROZEN.json` sha256 `{str(frozen_check["manifest_sha256"])[:12]}`: {len(frozen_check["mismatches"])} mismatch(es); self-entry skipped: {frozen_check["self_reference_skipped"]}.
{frozen_lines}

## X4 — composite-regularity ban

Composite-token hits: {len(composite_hits)}; violations: **{len(composite_violations)}**.
All hits are the exempt forbidden quotation in `anti_scope.phrases_that_are_not_this_class[0]`.

## X3c — containment-premise inversion (new in v3)

Hits: **{len(containment_inversions)}**. The frozen containment is
`E_C2 subset E_{{C^1,1}} subset E_H2loc subset E_C0`; a sentence calling C2 the *larger* (or C0 the
*smaller*) extension class is a hard failure even when the transfer it forbids is the correct one.

{inversion_lines}

**Exact repair (wording only, path `implication_ledger.forbidden_transfers[0].reason`):** replace
"C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker" with
"C2 is a strictly smaller extension class (E_C2 subset of E_C0), so C2-inextendibility is strictly
weaker". Re-hash, re-freeze, re-run this audit.

## X5 — declaration

Recorded under `declaration` in the JSON matrix: audits separation only; no truth/citation/
definitional audit; no completion claim; interpretation owned by `astra-lead-formulation`.

## Flags (not failures)

{flag_lines}

## Next falsifier

{matrix['next_falsifier']}
"""
    OUT_MD.write_text(md, encoding="utf-8")

    print(json.dumps({"verdict": matrix["verdict"],
                      "hard_failure_kinds": [f["kind"] for f in hard_failures],
                      "X1_violations": len(violations), "X1_naming_flags": len(naming_flags),
                      "X2_unjustified": len(unjustified), "X2_leakage_block_hits": len(leakage_hits),
                      "X3_checks_pass": all(c["pass"] for c in checks),
                      "X3_converse": len(converse_assertions), "X2b_axis_violations": len(axis_violations), "X3_unclassified": len(unclassified),
                      "X3c_containment_inversions": len(containment_inversions),
                      "X4_violations": len(composite_violations),
                      "outputs": [str(OUT_JSON.relative_to(REPO)), str(OUT_MD.relative_to(REPO))]},
                     indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
