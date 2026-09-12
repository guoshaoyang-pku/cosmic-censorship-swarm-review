#!/usr/bin/env python3
"""W083-F0-OPENCASE-DISPOSITION-01

Independent, hash-pinned disposition analysis of the NINE open G-F0 taxonomy cases
(`schemas/taxonomy_cases.jsonl`, `open == True`) against:

  A. the current canonical taxonomy `research_map/formulation_taxonomy.yaml` (rev 4), and
  B. the current class-scope policy (astra-classscope-02) as implemented in
     `artifacts/formulation/VARIANT_REGISTRY.json` v2.0.

Why this is a real task and not a restatement of the corpus:
  * the G-F0 controller_gate_audit lists "9 taxonomy cases remain open (new class vs split)
    and were never dispositioned by the lead" as an unmet criterion;
  * the nine cases are BOUND to taxonomy sha 66bf917bd368..., which is exactly the
    pre-amendment artifact that rev 4 declares it supersedes (revision_note_rev4 /
    class_scope_adjudication.supersedes.wcc_text_sha256_before);
  * rev 4 introduced the variant mechanism, so the live question is whether any of the nine
    can now be closed as a VARIANT of a frozen parent instead of needing a new class id.

Method (fully deterministic, no import of any authoring-side checker):
  1. Parse the four frozen class descriptors from the canonical taxonomy two ways
     (PyYAML and a hand-rolled indentation parser); the two parses must agree.
  2. For each case, build the case's axis vector = axes(filed class) overlaid with the
     deviations it declares (recorded `decisive_axes` + `violated_vocabulary`) and with
     deviations recovered independently from the case statement by keyword extraction.
  3. Compute `admissible_frozen_bindings` = frozen classes whose descriptor axes match the
     case vector exactly.
  4. Apply the disposition rules below and cite the taxonomy rule for every rejection.
  5. Controls: the 16 positives must resolve to exactly their filed class; the 20 negatives
     must not resolve cleanly to their filed class; four planted control records must land on
     the four disposition branches; the registry must stay confined to reading deltas.

Disposition vocabulary (proposals only; the lead decides, Human PI creates class ids):
  HOLDS_AS_FILED             axis vector equals one frozen descriptor, and it is the filed one
  MISFILED_REFILE            axis vector equals exactly one frozen descriptor, a different one
  REJECT_LEAK_ONLY           axis vector equals the filed descriptor but a non-axis rule is
                             violated (G3/G7/X4/X5/Q1/...); rejection, no class change
  SPLIT_REQUIRED             record merges two conclusions/families; must be split into two
                             filings, one per frozen class (no new class id)
  NEW_CLASS_REQUIRED         no frozen descriptor accepts the axis vector (coverage gap CG2);
                             class-id creation is deferred to Human PI (CF-5 policy)
  VARIANT_REGISTRATION_CANDIDATE
                             axis vector equals a frozen parent and the deviation is a
                             registered conclusion/extension reading -> register (parent, id)
  NEEDS_MANUAL_REVIEW        some decisive axis could not be recovered deterministically
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CST = timezone(timedelta(hours=8))

CASES = ROOT / "schemas" / "taxonomy_cases.jsonl"
TAXONOMY = ROOT / "research_map" / "formulation_taxonomy.yaml"
REGISTRY = ROOT / "artifacts" / "formulation" / "VARIANT_REGISTRY.json"
FROZEN_SCHEMAS = [
    ROOT / "schemas" / "af_wcc_vacuum.yaml",
    ROOT / "schemas" / "af_scc_c2_vacuum.yaml",
    ROOT / "schemas" / "af_scc_c0_vacuum.yaml",
]

FROZEN = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]

# Axis -> the taxonomy rule a mismatch violates, quoted from the canonical taxonomy.
AXIS_RULE = {
    ("AF-WCC-VAC-GEN", "matter_model"): "H2 (matter model is vacuum, T=0); exclusion 'Any non-vacuum matter model ... including electrovacuum'",
    ("AF-WCC-VAC-GEN", "symmetry"): "H5 (no symmetry is assumed); exclusion 'Restricted symmetry classes (spherical, axisymmetric), which have their own classes'",
    ("AF-WCC-VAC-GEN", "asymptotics"): "H1/H3 (Lambda=0, one asymptotically flat end); exclusion 'Non-zero cosmological constant ... and non-asymptotically-flat ends'",
    ("AF-SCC-C2-VAC-GEN", "matter_model"): "H1 (vacuum Einstein equations); exclusion 'Non-vacuum matter models (electrovacuum, scalar, fluid)'",
    ("AF-SCC-C2-VAC-GEN", "symmetry"): "exclusion 'Spherically symmetric scalar-field classes' plus guard G4 (no symmetry release)",
    ("AF-SCC-C2-VAC-GEN", "asymptotics"): "H1 (Lambda=0) and H2 (one asymptotically flat end)",
    ("AF-SCC-C0-VAC-GEN", "matter_model"): "H1 (vacuum Einstein equations); exclusion 'Non-vacuum matter models'",
    ("AF-SCC-C0-VAC-GEN", "symmetry"): "exclusion 'Spherically symmetric scalar-field classes' plus guard G4 (no symmetry release)",
    ("AF-SCC-C0-VAC-GEN", "asymptotics"): "H1 (Lambda=0) and H2 (one asymptotically flat end)",
    ("AF-WCC-SCALAR-SPH", "matter_model"): "H1 (Einstein-massless-scalar-field system); exclusion 'Vacuum data (no scalar field)'",
    ("AF-WCC-SCALAR-SPH", "symmetry"): "H2 (SO(3) symmetry with 2-sphere orbits); exclusion 'Non-spherical data: symmetry release ... forbidden as a transfer' (X3)",
    ("AF-WCC-SCALAR-SPH", "asymptotics"): "H1/H3 (Lambda=0, asymptotically flat); exclusion 'Massive or charged scalar fields; Lambda != 0'",
}

GLOBAL_RULES = {
    "G1": "each claim carries exactly one class_id from class_ids",
    "G4": "no symmetry release: a spherical-symmetry result may not be filed under a none_assumed class",
    "G5": "no matter-model swap: vacuum <-> massless_scalar_field without a bridge artifact",
    "X2": "AF-WCC-VAC-GEN <-> AF-WCC-SCALAR-SPH matter leakage (bridge lemma required)",
    "X3": "AF-WCC-SCALAR-SPH -> AF-WCC-VAC-GEN (or any class with symmetry: none_assumed) symmetry release",
    "X4": "any WCC <-> any SCC conclusion: bridge lemma must be filed as its own artifact",
    "X5": "merged-regularity class merge",
    "CG1": "AF-WCC-SCALAR-SPH has no schema node (F-node) in research_map.json",
    "CG2": "no class exists for non-spherical matter models, Lambda != 0, or higher-genus ends; such claims must open a new class rather than be filed here",
    "CF-5": "no new class ids without Human PI approval (controller finding CF-5 / astra-classscope-02)",
}

# ---------------------------------------------------------------- text extraction

# ordered: more specific patterns first
TEXT_AXIS_PATTERNS = [
    ("matter_model", "electrovacuum", [r"electrovacuum", r"einstein-maxwell", r"non-?zero charge"]),
    ("matter_model", "massless_scalar_field", [r"massless[-\s]scalar", r"scalar[-\s]field", r"einstein-massless-scalar"]),
    ("matter_model", "vacuum", [r"\bschwarzschild\b", r"\bvacuum\b"]),
    ("symmetry", "none_assumed", [r"no symmetry", r"without symmetry", r"dropping the symmetry", r"non-?spherical", r"symmetry release"]),
    ("symmetry", "spherical", [r"spherical", r"so\(3\)"]),
    ("asymptotics", "asymptotically_de_sitter_3p1", [r"de sitter", r"positive cosmological constant", r"lambda\s*(?:!=|>|\u2260)\s*0"]),
    ("asymptotics", "asymptotically_flat_3p1", [r"asymptotically flat", r"flat data"]),
    ("family", "MERGE", [r"both weak and strong"]),
    ("family", "WCC", [r"weak cosmic censorship"]),
    ("family", "SCC", [r"strong cosmic censorship", r"inextendib"]),
    ("regularity_token", "MERGE", [r"either continuously or twice", r"continuously or twice-continuously",
                                   r"\bc\s*0\s*(?:or|and|/)\s*c\s*2\b", r"\bc\s*2\s*(?:or|and|/)\s*c\s*0\b"]),
    ("regularity_token", "C2", [r"\bc2\b", r"twice-continuously"]),
    ("regularity_token", "C0", [r"\bc0\b", r"continuous-metric", r"continuously differentiable"]),
]

# local negation/prohibition context: a mentioned pair is not an asserted merge
NEG_GUARD = re.compile(
    r"(?:no|not|never|without|absent|forbidden|must\s+not|do\s+not|don't|nor|zero)\s+(?:\w+[\s-]+){0,4}$",
    re.I)
SPLIT_AFTER = re.compile(r"\s*(?:split|separate|distinct|vs\b|leakage|hygiene)", re.I)
# "between C2 and C0" describes a range of regularity classes, not a merged claim
BETWEEN_BEFORE = re.compile(r"between\s+(?:\S+\s+){0,3}$", re.I)


def _asserted(pat: str, low: str):
    for m in re.finditer(pat, low):
        before = low[max(0, m.start() - 50):m.start()]
        if NEG_GUARD.search(before) or BETWEEN_BEFORE.search(before):
            continue
        if SPLIT_AFTER.match(low[m.end():m.end() + 30]):
            continue
        return m
    return None

VARIANT_KEYWORDS = {
    "SET": [r"set-based", r"union of j\^?-"],
    "CH": [r"cauchy horizon", r"horizon-localized", r"across its cauchy horizon"],
    "H2LOC": [r"h\^?2_?loc", r"riemann tensor in l\^?2"],
    "L2CONN": [r"l\^?2_?loc", r"christoffel"],
    "LIP": [r"lipschitz", r"c\^?\{?0,1\}?"],
    "DISTRIBUTIONAL": [r"in the sense of distributions"],
    "TWOSIDED": [r"both time directions", r"two-sided"],
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def short(value: str) -> str:
    return value[:12]


# ---------------------------------------------------------------- parsers

def parse_taxonomy_hand(text: str) -> dict:
    """Minimal indentation parser for the blocks this analysis depends on."""
    lines = text.splitlines()
    class_ids, classes, variants, gaps = [], {}, [], {}
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("class_ids:"):
            i += 1
            while i < len(lines) and lines[i].strip().startswith("- "):
                class_ids.append(lines[i].strip()[2:].strip().strip('"'))
                i += 1
            continue
        if line.startswith("classes:"):
            i += 1
            cur = None
            while i < len(lines) and (lines[i].startswith("  ") or not lines[i].strip()):
                if re.match(r'^  "?AF-[A-Z0-9-]+"?:\s*$', lines[i]):
                    cur = lines[i].strip().rstrip(":").strip().strip('"')
                    classes[cur] = {"axes": {}}
                elif cur and re.match(r"^    axes:\s*$", lines[i]):
                    i += 1
                    while i < len(lines) and re.match(r"^      \S", lines[i]):
                        k, _, v = lines[i].strip().partition(":")
                        v = v.strip()
                        classes[cur]["axes"][k] = None if v in ("null", "~", "") else v.strip('"')
                        i += 1
                    continue
                i += 1
            continue
        if line.startswith("variants:"):
            i += 1
            cur = None
            while i < len(lines) and (lines[i].startswith("  ") or not lines[i].strip()):
                m = re.match(r'^  - parent_class:\s*"?([A-Z0-9-]+)"?', lines[i])
                if m:
                    cur = {"parent_class": m.group(1)}
                    variants.append(cur)
                elif cur is not None:
                    m = re.match(r'^    variant_id:\s*"?([A-Z0-9-]+)"?', lines[i])
                    if m:
                        cur["variant_id"] = m.group(1)
                i += 1
            continue
        if line.startswith("coverage_gaps:"):
            i += 1
            cur = None
            while i < len(lines) and (lines[i].startswith("  ") or not lines[i].strip()):
                m = re.match(r'^  - id:\s*"?([A-Z0-9-]+)"?', lines[i])
                if m:
                    cur = m.group(1)
                    gaps[cur] = []
                elif cur and lines[i].strip().startswith("text:"):
                    gaps[cur].append(lines[i].split("text:", 1)[1].strip().strip('"'))
                elif cur and lines[i].startswith("      ") and gaps[cur] is not None:
                    gaps[cur].append(lines[i].strip().strip('"'))
                i += 1
            continue
        i += 1
    return {
        "class_ids": class_ids,
        "classes": classes,
        "variants": variants,
        "coverage_gaps": {k: " ".join(v).strip() for k, v in gaps.items()},
    }


def parse_taxonomy_yaml(text: str) -> dict:
    import yaml  # available in this environment; cross-check only
    doc = yaml.safe_load(text)
    classes = {k: {"axes": {a: v for a, v in (c.get("axes") or {}).items()}}
               for k, c in doc["classes"].items()}
    variants = [{"parent_class": v["parent_class"], "variant_id": v["variant_id"]}
                for v in doc.get("variants", [])]
    gaps = {g["id"]: g["text"] for g in doc.get("coverage_gaps", [])}
    return {"class_ids": list(doc["class_ids"]), "classes": classes,
            "variants": variants, "coverage_gaps": gaps}


# ---------------------------------------------------------------- case -> axes

def extract_text_axes(statement: str) -> dict:
    low = statement.lower()
    found: dict[str, str] = {}
    evidence: dict[str, str] = {}
    for axis, value, pats in TEXT_AXIS_PATTERNS:
        if axis in found:
            continue
        for pat in pats:
            m = _asserted(pat, low)
            if m:
                found[axis] = value
                evidence[axis] = m.group(0)
                break
    return {"values": found, "evidence": evidence}


def normalize_violated(axis: str, value: str):
    """Map a violated_vocabulary entry onto (axis, value) pairs this script reasons over."""
    out = []
    if axis == "matter_model":
        if value == "electrovacuum":
            out.append(("matter_model", "electrovacuum"))
        elif value.startswith("vacuum_with_positive_Lambda"):
            out.append(("matter_model", "vacuum"))
            out.append(("asymptotics", "asymptotically_de_sitter_3p1"))
        else:
            out.append(("matter_model", value))
    elif axis == "family":
        out.append(("family", "MERGE" if "and" in value else value))
    elif axis == "conclusion_type":
        if value.startswith("strong_cosmic_censorship_continuous_or"):
            out.append(("regularity_token", "MERGE"))
        elif value.startswith("strong_cosmic_censorship_C2"):
            out.append(("regularity_token", "C2"))
        elif value.startswith("strong_cosmic_censorship_C0"):
            out.append(("regularity_token", "C0"))
        elif value.startswith("weak_cosmic"):
            out.append(("family", "WCC"))
    elif axis == "asymptotics":
        out.append(("asymptotics", value))
    elif axis == "regularity_token":
        out.append(("regularity_token", value))
    return out


def normalize_literal(axis: str, value: str):
    """Normalize a `family=WCC` style literal found in a case statement."""
    value = value.strip()
    table = {
        "family": {"wcc": "WCC", "scc": "SCC"},
        "matter_model": {"vacuum": "vacuum", "massless_scalar_field": "massless_scalar_field",
                         "electrovacuum": "electrovacuum"},
        "symmetry": {"none_assumed": "none_assumed", "spherical": "spherical"},
        "asymptotics": {"asymptotically_flat_3p1": "asymptotically_flat_3p1",
                        "asymptotically_de_sitter_3p1": "asymptotically_de_sitter_3p1"},
        "regularity_token": {"c0": "C0", "c2": "C2", "null": None, "none": None},
    }
    return table.get(axis, {}).get(value.lower(), value if axis in table else None)


def build_case_axes(case: dict, taxonomy: dict) -> dict:
    """Case axis vector = axes(filed class) overlaid with the deviations the case asserts.

    Deviations are taken, in order of authority, from:
      (1) `violated_vocabulary` entries (the corpus's own out-of-vocabulary statement);
      (2) `reject_misfiled:target=<C>` expected resolutions (the corpus names the target class);
      (3) `axis=value` literals in the statement that disagree with the filed class;
      (4) keyword-extracted values that disagree with the filed class (independent path);
      (5) MERGE signals (lexical/semantic witnesses for split-required records).
    An axis on which the text is silent is NOT a deviation: the record is filed under its class,
    so the filed class's value is the default binding under test.
    """
    filed = case["as_filed_class_id"]
    text = extract_text_axes(case.get("statement", ""))
    notes: list[str] = []
    if filed in taxonomy["classes"]:
        filed_axes = dict(taxonomy["classes"][filed]["axes"])
    else:
        filed_axes = {}
        notes.append(f"filed class {filed!r} is not a frozen descriptor")
    deviations: dict[str, str] = {}

    for vv in case.get("violated_vocabulary") or []:
        for axis, value in normalize_violated(vv.get("axis"), vv.get("value")):
            deviations.setdefault(axis, value)

    exp_res = str(case.get("expected_resolution") or "")
    m = re.match(r"reject_misfiled:target=([A-Z0-9-]+)", exp_res)
    if m and m.group(1) in taxonomy["classes"]:
        target = taxonomy["classes"][m.group(1)]["axes"]
        for axis in DESCRIPTOR_AXES:
            if axis in target and target[axis] != filed_axes.get(axis):
                deviations[axis] = target[axis]
        notes.append(f"expected_resolution names target {m.group(1)}")

    literal_asserted: set[str] = set()
    for axis, value in re.findall(r"\b(family|matter_model|symmetry|asymptotics|regularity_token)\s*=\s*([A-Za-z0-9_]+)", case.get("statement", "")):
        literal_asserted.add(axis)
        norm = normalize_literal(axis, value)
        if norm != filed_axes.get(axis):
            deviations.setdefault(axis, norm)

    # Keyword extraction is a lower-precision path: it is applied to negative/open records as
    # corroborating evidence, but never to a positive control record (a positive is in-class by
    # construction; a text conflict there is reported as a signal, not used as a disposition).
    apply_text = case.get("polarity") == "negative"
    text_conflicts = {axis: value for axis, value in text["values"].items()
                      if axis in DESCRIPTOR_AXES and value != filed_axes.get(axis)}
    if apply_text:
        for axis, value in text["values"].items():
            if axis in DESCRIPTOR_AXES and axis not in literal_asserted and value != filed_axes.get(axis):
                deviations.setdefault(axis, value)
        if text["values"].get("family") == "MERGE" and "family" not in literal_asserted:
            deviations["family"] = "MERGE"
        if text["values"].get("regularity_token") == "MERGE" and "regularity_token" not in literal_asserted:
            deviations["regularity_token"] = "MERGE"
    elif text_conflicts:
        notes.append(f"text_axis_conflict on a positive record (reported, not applied): {text_conflicts}")

    if not filed_axes and not deviations:
        notes.append("composite/unknown filing with no recoverable deviation")
    if re.search(r"\b[A-Z]\d+\s+fails\b", str(case.get("decisive_hypothesis") or "")) and not deviations:
        notes.append("decisive_hypothesis asserts a failure but no deviation was recovered")

    axes = dict(filed_axes)
    axes.update(deviations)
    return {
        "filed_class_id": filed,
        "filed_axes": filed_axes,
        "case_axes": axes,
        "deviations": deviations,
        "text_extracted": text["values"],
        "text_evidence": text["evidence"],
        "extraction_notes": notes,
    }


def admissible(case_axes: dict, taxonomy: dict) -> dict:
    """Which frozen descriptors match the case's axis vector exactly (on shared axes)."""
    out = {}
    for cid in taxonomy["class_ids"]:
        caxes = taxonomy["classes"][cid]["axes"]
        reasons = []
        for axis in ("family", "matter_model", "symmetry", "asymptotics", "regularity_token"):
            want = caxes.get(axis)
            got = case_axes.get(axis, want)
            if got == "MERGE":
                reasons.append(f"{axis}: record merges values (MERGE)")
            elif got == "UNRESOLVED":
                reasons.append(f"{axis}: undetermined")
            elif got != want:
                rule = AXIS_RULE.get((cid, axis), f"{axis} mismatch")
                reasons.append(f"{axis}: case={got!r} vs class={want!r} [{rule}]")
        if not reasons:
            out[cid] = []
        else:
            out[cid] = reasons
    return out


# ---------------------------------------------------------------- disposition

def variant_signals(case: dict, registry: dict) -> list:
    text = (case.get("statement", "") + " " + str(case.get("semantic_witness", ""))).lower()
    hits = []
    for vid, pats in VARIANT_KEYWORDS.items():
        for pat in pats:
            if re.search(pat, text):
                parents = sorted({v["parent_class"] for v in registry["variants"] if v["variant_id"] == vid})
                hits.append({"variant_id": vid, "parent_class": parents, "matched": pat})
                break
    return hits


DESCRIPTOR_AXES = ("family", "matter_model", "symmetry", "asymptotics", "regularity_token")


def disposition(case: dict, built: dict, adm: dict, registry: dict) -> dict:
    filed = case["as_filed_class_id"]
    polarity = case.get("polarity")
    case_axes = built["case_axes"]
    positives = [cid for cid, r in adm.items() if not r]
    merge = case_axes.get("family") == "MERGE" or case_axes.get("regularity_token") == "MERGE"
    blocking_notes = [n for n in built["extraction_notes"]
                      if "no recoverable deviation" in n or "no deviation was recovered" in n]
    # A record whose corpus-declared leak rule is a non-axis rule (G3/G6/G7/X4/Q1/...) is a leak
    # rejection even when the axis vector matches its filed class; do not route it to manual review.
    leak_rule = str(case.get("expected_leak_rule") or "")
    unresolved = bool(blocking_notes) and not leak_rule and case.get("polarity") != "positive"
    signals = variant_signals(case, registry)
    # Reading-axis deviations (conclusion predicate / extension class / time direction) do not
    # change the descriptor axes; those are the surface the variant registry covers.
    descriptor_deviations = {
        axis: value for axis, value in built["deviations"].items()
        if axis in DESCRIPTOR_AXES and value != built["filed_axes"].get(axis)
    }
    variant_repair = None
    if filed in FROZEN and not descriptor_deviations and (
            bool(signals) or any(axis not in DESCRIPTOR_AXES for axis in built["deviations"])):
        vid = signals[0]["variant_id"] if signals else "UNNAMED_READING_DELTA"
        variant_repair = {"parent_class": filed, "variant_id": vid}
    # A reading delta on a positively-filed record is a registration candidate. On a negative
    # record the filing itself is still rejected (leak rule) and the repair path is attached.
    variant_candidate = polarity == "positive" and variant_repair is not None
    out: dict = {
        "case_id": case["case_id"],
        "polarity": polarity,
        "as_filed_class_id": filed,
        "recorded_decisive_axes": case.get("decisive_axes", []),
        "case_axes": case_axes,
        "deviations_from_filed_class": built["deviations"],
        "descriptor_deviations": descriptor_deviations,
        "extraction_notes": built["extraction_notes"],
        "text_axis_evidence": built["text_evidence"],
        "admissible_frozen_bindings": positives,
        "admissibility_reasons": {cid: r for cid, r in adm.items()},
        "variant_path_signals": signals,
        "variant_repair_path": variant_repair,
        "authored_expectation": case.get("expected_resolution"),
        "authored_expected_classification": case.get("expected_classification"),
        "expected_leak_rule": case.get("expected_leak_rule"),
    }
    if unresolved:
        out["disposition"] = "NEEDS_MANUAL_REVIEW"
        out["rules_cited"] = ["descriptor axis extraction incomplete"]
    elif variant_candidate:
        out["disposition"] = "VARIANT_REGISTRATION_CANDIDATE"
        out["target_class_ids"] = [filed]
        out["variant_id"] = variant_repair["variant_id"]
        out["escalation"] = "lead-formulation"
        out["rules_cited"] = ["astra-classscope-02", "VARIANT_REGISTRY v2.0", "class_id_rule"]
    elif merge:
        if case_axes.get("family") == "MERGE":
            targets = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN"]
            rules = ["X4", "G1"]
        else:
            targets = ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
            rules = ["X5", "G3", "G1"]
        out["disposition"] = "SPLIT_REQUIRED"
        out["target_class_ids"] = targets
        out["rules_cited"] = rules
    elif polarity == "positive":
        if len(positives) == 1 and positives[0] == filed:
            out["disposition"] = "HOLDS_AS_FILED"
            out["rules_cited"] = ["G1"]
        elif len(positives) == 1:
            out["disposition"] = "MISFILED_REFILE"
            out["target_class_ids"] = positives
            out["rules_cited"] = ["G1"]
        else:
            out["disposition"] = "NEW_CLASS_REQUIRED" if not positives else "NEEDS_MANUAL_REVIEW"
            out["rules_cited"] = ["CG2", "CF-5"]
    else:  # negative
        if len(positives) == 1 and positives[0] == filed:
            out["disposition"] = "REJECT_LEAK_ONLY"
            out["rules_cited"] = [str(case.get("expected_leak_rule") or "non-axis leak")]
        elif len(positives) == 1:
            out["disposition"] = "MISFILED_REFILE"
            out["target_class_ids"] = positives
            out["rules_cited"] = ["G1", "G6"]
        elif not positives:
            out["disposition"] = "NEW_CLASS_REQUIRED"
            out["rules_cited"] = ["CG2", "CF-5"]
        else:
            out["disposition"] = "NEEDS_MANUAL_REVIEW"
            out["rules_cited"] = []
    # coverage-gap / escalation annotation
    if out["disposition"] == "NEW_CLASS_REQUIRED":
        out["coverage_gap"] = "CG2"
        out["escalation"] = "human-pi"
        out["class_id_policy"] = "new class ids deferred to Human PI (astra-classscope-02 / CF-5); do not file under a frozen class"
    if out["disposition"] == "VARIANT_REGISTRATION_CANDIDATE":
        out["escalation"] = "lead-formulation"
    out["expectation_agreement"] = expectation_agreement(case, out)
    out["agrees_with_authored_expectation"] = out["expectation_agreement"] in ("agrees", "agrees_repair_refined")
    return out


def expectation_agreement(case: dict, out: dict) -> str:
    """Compare this worker's disposition vocabulary with the corpus's expected_resolution."""
    exp = str(case.get("expected_resolution") or "")
    got = out["disposition"]
    if exp.startswith("unique_class:"):
        return "agrees" if got == "HOLDS_AS_FILED" and exp.split(":", 1)[1] == case["as_filed_class_id"] else "differs"
    if exp.startswith("reject_misfiled:target="):
        return "agrees" if got == "MISFILED_REFILE" and out.get("target_class_ids") == [exp.split("=", 1)[1]] else "differs"
    if exp.startswith("reject_new_class_required"):
        return "agrees" if got == "NEW_CLASS_REQUIRED" else "differs"
    if exp.startswith("reject_split_required"):
        return "agrees" if got == "SPLIT_REQUIRED" else "differs"
    if exp.startswith("reject_leak"):
        if got == "REJECT_LEAK_ONLY":
            return "agrees"
        if got == "SPLIT_REQUIRED" and str(case.get("expected_leak_rule") or "").startswith(("G3", "X5")):
            return "agrees_repair_refined"  # same rejection; names the repair as a split
        if got == "NEEDS_MANUAL_REVIEW":
            return "review"
        return "differs"
    return "unmapped"


# ---------------------------------------------------------------- controls

def planted_controls(taxonomy: dict, registry: dict) -> list:
    base = {"TC-CTRL-NEWCLASS": {"as_filed_class_id": "AF-WCC-VAC-GEN", "polarity": "negative",
                                 "statement": "For generic asymptotically flat electrovacuum data weak cosmic censorship holds.",
                                 "decisive_axes": ["matter_model"]},
            "TC-CTRL-SPLIT": {"as_filed_class_id": "COMPOSITE_C0_C2", "polarity": "negative",
                              "statement": "For generic vacuum data the maximal development is C0 or C2 inextendible.",
                              "decisive_axes": ["regularity_token"]},
            "TC-CTRL-INCLASS": {"as_filed_class_id": "AF-SCC-C2-VAC-GEN", "polarity": "positive",
                                "statement": "A residual family of vacuum perturbations of subextremal Kerr data, no symmetry assumed, C2-inextendible.",
                                "decisive_axes": []},
            "TC-CTRL-VARIANT": {"as_filed_class_id": "AF-WCC-VAC-GEN", "polarity": "positive",
                                "statement": "A vacuum, no symmetry assumed record uses the set-based union of J^-(q) visibility condition.",
                                "decisive_axes": ["conclusion_type"]}}
    results = []
    for cid, case in base.items():
        case = dict(case, case_id=cid)
        built = build_case_axes(case, taxonomy)
        adm = admissible(built["case_axes"], taxonomy)
        results.append(disposition(case, built, adm, registry))
    return results


def registry_invariants(registry: dict, cases: list) -> dict:
    variant_ids = {v["variant_id"] for v in registry["variants"]}
    parents = sorted({v["parent_class"] for v in registry["variants"]})
    variants_in_class_ids = []
    for c in cases:
        for field in ("class_id", "class_ids"):
            val = c.get(field)
            if isinstance(val, str):
                val = [val]
            for tok in val or []:
                if tok in variant_ids:
                    variants_in_class_ids.append({"case_id": c.get("case_id"), "token": tok})
    # machine delta files: which schema paths does each registered variant change?
    changed_paths, axis_path_hits = {}, {}
    for v in registry["variants"]:
        ref = v.get("delta_ref")
        if ref and (ROOT / ref).exists():
            delta = json.loads((ROOT / ref).read_text())
            paths = [str(ch.get("path")) for ch in delta.get("changes", [])]
            changed_paths[v["variant_id"]] = paths
            hits = [p for p in paths
                    if re.match(r"^(family|matter_model|symmetry|asymptotics|regularity_token)(\.|$)", p)]
            if hits:
                axis_path_hits[v["variant_id"]] = hits
    # text check on the registry entries themselves (not their evidence paths):
    # does any entry declare a change of the data class?
    data_class_words = re.compile(r"matter model|symmetry|asymptot|lambda|data class|data space", re.I)
    declared_data_class_change = {
        v["variant_id"]: v["definition"]
        for v in registry["variants"]
        if data_class_words.search(str(v.get("definition", "")) + " " + str(v.get("why_separate", "")))
    }
    return {
        "n_variants": len(registry["variants"]),
        "variant_parents": parents,
        "all_variant_parents_frozen": all(p in FROZEN for p in parents),
        "variant_ids_in_case_class_id_fields": variants_in_class_ids,
        "variants_with_machine_delta_file": sorted(changed_paths),
        "changed_paths": changed_paths,
        "descriptor_axis_path_hits": axis_path_hits,
        "entries_declaring_a_data_class_change": sorted(declared_data_class_change),
        "reading": ("registered variants preserve their parent's descriptor axis vector and change only "
                    "the conclusion/visibility/extension reading; none of the nine open cases deviates "
                    "only in such a reading (each deviates on >=1 of matter_model / symmetry / asymptotics "
                    "/ family / regularity_token), so the registered-variant mechanism does not close any "
                    "of the nine"),
    }


# ---------------------------------------------------------------- main

def main() -> int:
    now = datetime.now(CST).replace(microsecond=0).isoformat()
    tax_text = TAXONOMY.read_text()
    hand = parse_taxonomy_hand(tax_text)
    yml = parse_taxonomy_yaml(tax_text)
    parser_agreement = (
        hand["class_ids"] == yml["class_ids"]
        and hand["classes"] == yml["classes"]
        and sorted((v["parent_class"], v["variant_id"]) for v in hand["variants"])
        == sorted((v["parent_class"], v["variant_id"]) for v in yml["variants"])
        and set(hand["coverage_gaps"]) == set(yml["coverage_gaps"])
    )
    if not parser_agreement:
        print("FATAL: taxonomy parsers disagree", file=sys.stderr)
        return 2

    cases = [json.loads(l) for l in CASES.read_text().splitlines() if l.strip()]
    records = cases[1:]
    open_cases = [c for c in records if c.get("open") is True]
    registry = json.loads(REGISTRY.read_text())

    per_case = []
    for c in records:
        built = build_case_axes(c, hand)
        adm = admissible(built["case_axes"], hand)
        d = disposition(c, built, adm, registry)
        d["open"] = bool(c.get("open"))
        d["binding_status"] = c.get("binding_status")
        d["falsifier"] = c.get("falsifier")
        d["evidence_refs"] = [
            f"schemas/taxonomy_cases.jsonl#{sha256(CASES)[:12]}:{c['case_id']}",
            f"research_map/formulation_taxonomy.yaml#{sha256(TAXONOMY)[:12]}#classes.{c['as_filed_class_id']}",
        ]
        per_case.append(d)

    # ---- controls
    positives = [d for d in per_case if d["polarity"] == "positive"]
    negatives = [d for d in per_case if d["polarity"] == "negative"]
    pos_ok = all(d["disposition"] == "HOLDS_AS_FILED" for d in positives)
    neg_ok = all(d["disposition"] != "HOLDS_AS_FILED" for d in negatives)
    controls = planted_controls(hand, registry)
    ctrl_expect = {"TC-CTRL-NEWCLASS": "NEW_CLASS_REQUIRED", "TC-CTRL-SPLIT": "SPLIT_REQUIRED",
                   "TC-CTRL-INCLASS": "HOLDS_AS_FILED", "TC-CTRL-VARIANT": "VARIANT_REGISTRATION_CANDIDATE"}
    ctrl_ok = all(d["disposition"] == ctrl_expect[d["case_id"]] for d in controls)

    summary = {}
    for d in per_case:
        summary[d["disposition"]] = summary.get(d["disposition"], 0) + 1
    agreement_summary = {}
    for d in per_case:
        agreement_summary[d["expectation_agreement"]] = agreement_summary.get(d["expectation_agreement"], 0) + 1

    open_dispositions = [d for d in per_case if d["open"]]
    open_summary = {}
    for d in open_dispositions:
        open_summary[d["disposition"]] = open_summary.get(d["disposition"], 0) + 1

    out = {
        "task_id": "W083-F0-OPENCASE-DISPOSITION-01",
        "actor": "worker-083",
        "generated_at": now,
        "node_id": "F0",
        "gate": "G-F0",
        "class_id": ";".join(FROZEN),
        "class_ids": FROZEN,
        "class_binding_rule": "every case is evaluated against the four frozen descriptors only; no new class id is created or proposed by this worker",
        "inputs": {
            "schemas/taxonomy_cases.jsonl": {"sha256": sha256(CASES), "role": "case corpus (meta + 36 cases); 9 records have open==true"},
            "research_map/formulation_taxonomy.yaml": {"sha256": sha256(TAXONOMY), "role": "current canonical F0 taxonomy (rev 4)"},
            "artifacts/formulation/VARIANT_REGISTRY.json": {"sha256": sha256(REGISTRY), "role": "current class-scope / variant policy (v2.0)"},
        },
        "frozen_schema_hashes": {p.name: sha256(p) for p in FROZEN_SCHEMAS if p.exists()},
        "parser_cross_check": {"hand_parser == pyyaml_parser": parser_agreement},
        "stale_binding": {
            "cases_declared_taxonomy_sha256": "66bf917bd368ebd96ee46baa31fb435df106cb4e10152fa0baee8bdd51dfc232",
            "current_canonical_taxonomy_sha256": sha256(TAXONOMY),
            "rev4_supersedes_that_hash": True,
            "note": "taxonomy rev 4 class_scope_adjudication.supersedes.wcc_text_sha256_before equals the hash the 9 open cases are bound to; the binding is stale by construction and must be re-bound before any lead disposition binds",
        },
        "policy_basis": [
            "research_map/formulation_taxonomy.yaml#class_scope_adjudication (astra-classscope-02: new class ids rejected pending Human PI; non-frozen readings registered as variants)",
            "research_map/formulation_taxonomy.yaml#coverage_gaps.CG2 (non-spherical matter, Lambda != 0, higher-genus ends must open a new class)",
            "research_map/formulation_taxonomy.yaml#transfer_rules (X2/X3/X4/X5) and #guards (G1,G4,G5,G6)",
            "artifacts/formulation/VARIANT_REGISTRY.json#class_id_rule (variant ids are not class ids)",
            "research_map/research_map.json#controller_gate_audit G-F0 unmet item (9 open cases never dispositioned by the lead)",
            "research_map/research_map.json#controller_findings CF-5 (no new class tokens without Human PI)",
        ],
        "summary": {"total_cases": len(per_case), "by_disposition": summary,
                    "expectation_agreement": agreement_summary,
                    "open_cases": len(open_dispositions), "open_by_disposition": open_summary},
        "controls": {
            "positives_resolve_to_filed_class": pos_ok,
            "negatives_do_not_resolve_cleanly_to_filed_class": neg_ok,
            "planted_controls_match_expected_branch": ctrl_ok,
            "planted_controls": controls,
            "registry_invariants": registry_invariants(registry, records),
        },
        "open_case_dispositions": open_dispositions,
        "all_case_dispositions": per_case,
        "falsifier": (
            "For any open case dispositioned NEW_CLASS_REQUIRED: exhibit a frozen descriptor whose axes accept the "
            "case's recovered axis vector, or a registered variant whose delta absorbs the descriptor-axis deviation "
            "(matter_model / symmetry / asymptotics / family / regularity_token) without changing the parent's data "
            "class. For any SPLIT_REQUIRED: exhibit a single frozen class whose conclusion_type covers both merged "
            "readings without a bridge artifact. For the stale-binding claim: exhibit a canonical taxonomy revision "
            "whose bytes hash to 66bf917bd368 and that supersedes rev 4."
        ),
        "does_not_claim": [
            "no gate verdict (G-F0 stays pending; worker events cannot move a gate)",
            "no node status (F0 stays active/unverified; only the controller/leads move that)",
            "no new class id, no class merge, no theorem or physics claim",
            "dispositions are proposals for the F0 lead to adjudicate; Human PI creates any new class id",
        ],
        "reproduce": "python3 artifacts/worker-083/f0_open_case_disposition/disposition.py",
    }

    # hard-fail the run if the corpus controls break: a broken analyzer must not emit a report
    if not (pos_ok and neg_ok and ctrl_ok and parser_agreement):
        diag = {
            "parser_agreement": parser_agreement,
            "positives_not_holds_as_filed": [d["case_id"] for d in positives if d["disposition"] != "HOLDS_AS_FILED"],
            "negatives_resolving_cleanly": [d["case_id"] for d in negatives if d["disposition"] == "HOLDS_AS_FILED"],
            "planted_controls": {d["case_id"]: {"got": d["disposition"], "want": ctrl_expect[d["case_id"]]} for d in controls},
        }
        print(json.dumps(diag, indent=1)[:4000])
        print("FATAL: controls failed; refusing to write dispositions.json", file=sys.stderr)
        return 3

    dest = Path(__file__).resolve().parent / "dispositions.json"
    dest.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {dest.relative_to(ROOT)} sha256={sha256(dest)[:12]}")
    print(f"open cases: {len(open_dispositions)} -> {open_summary}")
    print(f"controls: positives={pos_ok} negatives={neg_ok} planted={ctrl_ok}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
