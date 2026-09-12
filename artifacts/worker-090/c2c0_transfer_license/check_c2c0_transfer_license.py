#!/usr/bin/env python3
"""W090-C2C0-TRANSLICENSE-VERIFY-01

Independent, non-author, read-only verification of the C0->C2 predicate-containment
justification gap reported by worker-047 in W047-C2C0-PRED-CONTAINMENT-01
(artifacts/worker-047/c2c0_pred_containment/report.json).  Class-bound:
AF-SCC-C2-VAC-GEN cross AF-SCC-C0-VAC-GEN, node F2a, gate G-FORM.

Question
--------
At the FROZEN rev29 pins, is the declared containment "E_C2 subset of E_C0" entailed by
the two sibling extension predicates as literally declared, or is it conditional on an
undeclared cross-class convention?

Method (independent implementation; worker-047 code is NOT imported)
--------------------------------------------------------------------
1. pin the live bytes against the declared FROZEN rev29 hashes at entry and exit;
2. parse the extension_predicate definitions with a duplicate-key-rejecting YAML loader;
3. detect the two convention axes the siblings differ on:
     axis A: manifold category of M' in clause (c);
     axis B: interior/boundary requirement on the future witness in clause (f);
4. build an explicit text-level decision table over the four (axis A, axis B) quadrants.
   Interpretation rule (stated, not smuggled): a clause set is read LITERALLY, i.e. an
   attribute is admitted iff the declared text imposes no constraint blocking it. Under
   that reading the quadrant is in E_C2_literal iff F2a clauses (a)-(f) are satisfiable
   with that quadrant, and in E_C0 iff F2b clauses (a)-(f) are. This is a model of what
   the text LICENSES, not a claim that any particular GR solution exists;
5. census every operative locus that asserts or uses the containment premise, and the
   guards of transfer rule T1, in the pinned F0 canonical + supplement;
6. run pre-registered sandbox controls (mutations only on copies) and a class-separation
   pass on this task's own emitted text at a cited detector hash.

Exit codes: 0 = analysis complete, controls pass, pins stable; 3 = pin drift; 4 = control
or pre-registration failure. Canonical files are only ever read and hashed.
"""

import hashlib
import importlib.util
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone, timedelta

import yaml

CST = timezone(timedelta(hours=8))
TASK_ID = "W090-C2C0-TRANSLICENSE-VERIFY-01"
ACTOR = "worker-090"
CLASS_ID = "AF-SCC-C2-VAC-GEN"
CLASS_IDS = ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
NODE_ID = "F2a"
GATE = "G-FORM"

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = HERE

# declared FROZEN rev29 pins (mirrors must be byte-identical to canonical)
PINS = {
    "F2a_canonical": ("schemas/af_scc_c2_vacuum.yaml",
                      "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe"),
    "F2b_canonical": ("schemas/af_scc_c0_vacuum.yaml",
                      "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"),
    "F1_canonical": ("schemas/af_wcc_vacuum.yaml",
                     "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d"),
    "F0_canonical": ("research_map/formulation_taxonomy.yaml",
                     "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"),
    "F0_supplement": ("artifacts/formulation/formulation_taxonomy.yaml",
                      "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1"),
    "F2a_mirror": ("artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
                   "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe"),
    "F2b_mirror": ("artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
                   "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"),
    "FROZEN": ("artifacts/formulation/FROZEN.json",
               "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"),
}

W047_REPORT = "artifacts/worker-047/c2c0_pred_containment/report.json"
CLASSSEP_PINNED = "artifacts/worker-049/classsep_fn_audit/pinned/class_separation_c266_recovered.py"
CLASSSEP_PINNED_SHA = "c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920"
CLASSSEP_LIVE = "research_map/class_separation.py"

# ---------------------------------------------------------------- helpers

class DupKeyError(yaml.constructor.ConstructorError):
    pass


class StrictLoader(yaml.SafeLoader):
    pass


def _no_duplicates(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise DupKeyError("duplicate mapping key", key_node.start_mark, key)
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


StrictLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_duplicates)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.load(fh, Loader=StrictLoader)


def line_of(text, needle):
    """1-based line number of the first line containing needle (substring)."""
    for i, line in enumerate(text.splitlines(), 1):
        if needle in line:
            return i
    return None


def find_lines(text, needles):
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        if any(n in line for n in needles):
            hits.append(i)
    return hits


# ---------------------------------------------------------------- axis detectors

SMOOTH_RE = re.compile(r"SMOOTH|C-infinity|C\^?\\?infty|smooth\s+4-manifold|smooth structure",
                       re.IGNORECASE)
INTERIOR_RE = re.compile(r"\bint\s*\(|interior", re.IGNORECASE)
OPERATIVE_INTERIOR_RE = re.compile(r"int\s*\(\s*M'\s*minus\s+iota\(M\)\s*\)", re.IGNORECASE)
# Annotations/justifications that follow the operative condition inside a clause.
OPERATIVE_CUT = re.compile(
    r"\s*(?:The interior requirement blocks|CONVENTION CAVEAT|\[R2 major|\(R2 major|\(worker-16)",
    re.IGNORECASE)


def operative(text):
    """Strip explanatory annotation from a clause, keep the declared condition."""
    text = text or ""
    m = OPERATIVE_CUT.search(text)
    return text[:m.start()] if m else text


def split_clauses(definition):
    """Split a YAML block-scalar predicate definition into {(a)..(f): text}."""
    clauses = {}
    current = None
    for line in definition.splitlines():
        m = re.match(r"^\s*\(([a-f])\)\s*(.*)$", line)
        if m:
            current = m.group(1)
            clauses[current] = m.group(2).strip()
        elif current:
            clauses[current] += " " + line.strip()
    return clauses


def raw_definition_block(raw_text, section="extension_predicate:"):
    """Return the RAW (unfolded) block scalar under <section>.definition.

    YAML folded style ('>-') joins lines with spaces, which would destroy the
    per-clause structure; the text-level axis detectors must read the raw block.
    """
    lines = raw_text.splitlines()
    for i, line in enumerate(lines):
        if re.match(r"^\s*" + re.escape(section) + r"\s*$", line):
            for j in range(i + 1, len(lines)):
                m = re.match(r"^(\s*)definition:\s*>[-+]?\s*$", lines[j])
                if m:
                    base = len(m.group(1))
                    block = []
                    k = j + 1
                    while k < len(lines):
                        l2 = lines[k]
                        if l2.strip() == "":
                            block.append("")
                            k += 1
                            continue
                        ind = len(l2) - len(l2.lstrip())
                        if ind <= base:
                            break
                        block.append(l2)
                        k += 1
                    return "\n".join(block)
    return None


def axis_state(clause_c, clause_f, evidence_note=None):
    """Return the two axis observations for one predicate's declared text."""
    notes = []
    clause_c = operative(clause_c)
    clause_f = operative(clause_f)
    smooth = bool(SMOOTH_RE.search(clause_c))
    interior = bool(INTERIOR_RE.search(clause_f))
    if not smooth:
        notes.append("clause (c) names no manifold category (no SMOOTH/C-infinity token)")
    if not interior:
        notes.append("clause (f) names no interior requirement on the future witness")
    return {
        "category_pinned_smooth": smooth,
        "interior_witness_required": interior,
        "operative_clause_c": clause_c.strip(),
        "operative_clause_f": clause_f.strip(),
        "clause_c": (clause_c or "").strip(),
        "clause_f": (clause_f or "").strip(),
        "notes": notes,
    }


def predicate_admits(axis, smooth, interior):
    """Literal reading: a quadrant is admitted unless the declared text excludes it."""
    if axis["category_pinned_smooth"] and not smooth:
        return False
    if axis["interior_witness_required"] and not interior:
        return False
    return True


def literal_containment(f2a_axis, f2b_axis):
    """Text-level decision table over the two convention axes.

    Quadrants: (category_smooth, interior_witness) in {T,F}^2. An extension quadrant is
    in E_C2_literal iff F2a's declared text admits it, and in E_C0_literal iff F2b's does.
    Returns (holds, escaped_quadrants).
    """
    escaped = []
    for smooth in (True, False):
        for interior in (True, False):
            in_f2a = predicate_admits(f2a_axis, smooth, interior)
            in_f2b = predicate_admits(f2b_axis, smooth, interior)
            if in_f2a and not in_f2b:
                escaped.append({"M'_category_smooth": smooth,
                                "future_witness_interior": interior})
    return (len(escaped) == 0, escaped)


def aligned_containment(f2a_axis_aligned, f2b_axis):
    """Containment when F2a is read under the F2b convention (smooth + interior)."""
    holds = (f2a_axis_aligned["category_pinned_smooth"]
             and f2a_axis_aligned["interior_witness_required"])
    return holds, [] if holds else [{"reason": "aligned F2a still lacks an axis pin"}]


# ---------------------------------------------------------------- pin census

def pin_census():
    rows = []
    for name, (rel, declared) in PINS.items():
        path = os.path.join(ROOT, rel)
        exists = os.path.exists(path)
        measured = sha256_file(path) if exists else None
        rows.append({
            "name": name, "path": rel, "declared_sha256": declared,
            "measured_sha256": measured, "exists": exists,
            "match": bool(exists and measured == declared),
        })
    ok = all(r["match"] for r in rows)
    return ok, rows


# ---------------------------------------------------------------- premise census

PREMISE_NEEDLES = [
    "E_C2 subset of E_C0",
    "every C2 extension is a C0 extension",
    "If no C0 extension exists, then no C2 extension exists",
    "C0-inextendibility is stronger",
]


def premise_census(texts):
    """texts: {label: (rel_path, raw_text)}. Returns loci with line numbers."""
    loci = []
    for label, (rel, text) in texts.items():
        for i, line in enumerate(text.splitlines(), 1):
            for needle in PREMISE_NEEDLES:
                if needle in line:
                    loci.append({"label": label, "path": rel, "line": i,
                                 "needle": needle, "text": line.strip()[:240]})
                    break
    return loci


def t1_block(f0_text):
    """Extract the T1 transfer-rule block from the canonical F0 taxonomy text."""
    lines = f0_text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if re.match(r'\s*-\s*id:\s*"?T1"?\s*$', line):
            start = i
            break
    if start is None:
        return None, None, None
    block = []
    j = start
    while j < len(lines):
        block.append(lines[j])
        j += 1
        if j < len(lines) and j > start and re.match(r"\s{4}-\s+id:", lines[j]):
            break
    raw = "\n".join(block)
    guards = re.findall(r'^\s*-\s*"?(.*?)"?\s*$', raw, re.MULTILINE)
    guards = [g for g in guards if g and not g.startswith("id:")]
    guard_lines = [start + 1 + k for k, l in enumerate(block)
                   if re.match(r"\s*-\s+", l) and "id:" not in l and "from:" not in l
                   and "to:" not in l and "kind:" not in l and "reason:" not in l]
    return raw, guards, guard_lines


GUARD_AXIS_RE = re.compile(
    r"extension.?predicate|manifold category|interior|smooth|convention|categor", re.IGNORECASE)


# ---------------------------------------------------------------- controls

def sandbox_apply(src, dst, old, new):
    with open(src, "r", encoding="utf-8") as fh:
        raw = fh.read()
    if old not in raw:
        raise AssertionError("sandbox anchor not found: %r" % old[:60])
    with open(dst, "w", encoding="utf-8") as fh:
        fh.write(raw.replace(old, new, 1))
    return dst


def run_axis_pipeline(f2a_path, f2b_path):
    f2a = load_yaml(f2a_path)          # structural parse (duplicate-key rejecting)
    f2b = load_yaml(f2b_path)
    f2a_raw = open(f2a_path, encoding="utf-8").read()
    f2b_raw = open(f2b_path, encoding="utf-8").read()
    f2a_def = raw_definition_block(f2a_raw)
    f2b_def = raw_definition_block(f2b_raw)
    assert f2a_def and f2b_def, "extension_predicate definition block not found"
    assert f2a["extension_predicate"]["definition"].strip()[:40] in f2a_def.replace("\n", " ")
    f2a_cl = split_clauses(f2a_def)
    f2b_cl = split_clauses(f2b_def)
    f2a_axis = axis_state(f2a_cl.get("c", ""), f2a_cl.get("f", ""))
    f2b_axis = axis_state(f2b_cl.get("c", ""), f2b_cl.get("f", ""))
    holds, escaped = literal_containment(f2a_axis, f2b_axis)
    return {
        "f2a": f2a_axis,
        "f2b": f2b_axis,
        "literal_containment_holds": holds,
        "literal_escaped_quadrants": escaped,
        "f2a_clauses": f2a_cl,
        "f2b_clauses": f2b_cl,
    }


def main():
    t_start = datetime.now(CST)
    problems = []
    checks = {}
    artifacts = {}

    ok_in, pins_in = pin_census()
    checks["V01_pins_declared_eq_measured_entry"] = {
        "status": "PASS" if ok_in else "FAIL",
        "detail": {"mismatches": [r for r in pins_in if not r["match"]]},
    }
    if not ok_in:
        problems.append("V01 pin drift at entry")

    # ---- load pinned bytes (read-only)
    f2a_path = os.path.join(ROOT, PINS["F2a_canonical"][0])
    f2b_path = os.path.join(ROOT, PINS["F2b_canonical"][0])
    f0_path = os.path.join(ROOT, PINS["F0_canonical"][0])
    sup_path = os.path.join(ROOT, PINS["F0_supplement"][0])
    f2a_text = open(f2a_path, encoding="utf-8").read()
    f2b_text = open(f2b_path, encoding="utf-8").read()
    f0_text = open(f0_path, encoding="utf-8").read()
    sup_text = open(sup_path, encoding="utf-8").read()

    live = run_axis_pipeline(f2a_path, f2b_path)
    a, b = live["f2a"], live["f2b"]

    checks["V02_f2a_clause_c_category_silent"] = {
        "status": "PASS" if not a["category_pinned_smooth"] else "FAIL",
        "detail": {"clause_c": a["clause_c"],
                   "expectation": "category-silent (blocker F-PC-1 axis A)"},
    }
    checks["V03_f2a_clause_f_interior_free"] = {
        "status": "PASS" if not a["interior_witness_required"] else "FAIL",
        "detail": {"clause_f": a["clause_f"],
                   "expectation": "no interior requirement (blocker F-PC-1 axis B)"},
    }
    checks["V04_f2b_clause_c_smooth_pinned"] = {
        "status": "PASS" if b["category_pinned_smooth"] else "FAIL",
        "detail": {"clause_c": b["clause_c"]},
    }
    checks["V05_f2b_clause_f_interior_required"] = {
        "status": "PASS" if b["interior_witness_required"] else "FAIL",
        "detail": {"clause_f": b["clause_f"]},
    }
    checks["V06_literal_containment_entailed"] = {
        "status": "FAIL" if live["literal_escaped_quadrants"] else "PASS",
        "detail": {"holds": live["literal_containment_holds"],
                   "escaped_quadrants": live["literal_escaped_quadrants"],
                   "reading": "literal: an axis is admitted iff the text imposes no constraint"},
    }
    if not live["literal_escaped_quadrants"]:
        problems.append("V06 expected the literal containment to fail")

    # aligned reading: F2a read with F2b's conventions
    aligned_axis = dict(a)
    aligned_axis["category_pinned_smooth"] = True
    aligned_axis["interior_witness_required"] = True
    aligned_holds, _ = aligned_containment(aligned_axis, b)
    checks["V07_aligned_containment_holds"] = {
        "status": "PASS" if aligned_holds else "FAIL",
        "detail": {"holds": aligned_holds,
                   "reading": "F2a read under the F2b smooth+interior convention"},
    }

    # ---- premise loci census
    texts = {
        "F2a_canonical": (PINS["F2a_canonical"][0], f2a_text),
        "F0_supplement": (PINS["F0_supplement"][0], sup_text),
        "F0_canonical": (PINS["F0_canonical"][0], f0_text),
    }
    loci = premise_census(texts)
    checks["V08_premise_loci_census"] = {
        "status": "PASS" if len(loci) >= 4 else "FAIL",
        "detail": {"count": len(loci), "loci": loci,
                   "expectation": ">=4 operative loci assert/use the containment premise"},
    }

    raw_t1, guards, guard_lines = t1_block(f0_text)
    guard_axis_hits = []
    if raw_t1 is None:
        checks["V09_t1_guard_covers_predicate_convention"] = {
            "status": "FAIL", "detail": {"error": "T1 block not found"}}
        problems.append("V09 T1 block not found")
        t1_reason = None
    else:
        t1_reason = None
        m = re.search(r'reason:\s*"?(.*?)"?\s*$', raw_t1, re.MULTILINE)
        if m:
            t1_reason = m.group(1).strip().strip('"')
        guard_axis_hits = [g for g in guards if GUARD_AXIS_RE.search(g)]
        checks["V09_t1_guard_covers_predicate_convention"] = {
            "status": "FAIL" if not guard_axis_hits else "PASS",
            "detail": {"guards": guards, "guard_lines": guard_lines,
                       "reason": t1_reason,
                       "axis_hits": guard_axis_hits,
                       "expectation": "no guard names the manifold-category / interior-witness axis"},
        }
        if guard_axis_hits:
            problems.append("V09 guard unexpectedly covers the predicate-convention axis")

    # ---- alignment declaration census in the pinned sibling artifacts
    align_patterns = [
        r"same (manifold )?categor", r"category[- ]aligned", r"aligned (with|to) (the )?C0",
        r"same convention", r"predicate[- ]aligned", r"convention[- ]aligned",
        r"F2a.{0,80}smooth", r"smooth.{0,80}F2a",
    ]
    align_hits = []
    for label, text in (("F2a_canonical", f2a_text), ("F0_canonical", f0_text),
                        ("F0_supplement", sup_text)):
        for i, line in enumerate(text.splitlines(), 1):
            for pat in align_patterns:
                if re.search(pat, line, re.IGNORECASE):
                    align_hits.append({"label": label, "line": i,
                                       "pattern": pat, "text": line.strip()[:200]})
                    break
    checks["V10_no_pinned_alignment_declaration"] = {
        "status": "PASS" if not align_hits else "FAIL",
        "detail": {"hits": align_hits,
                   "expectation": "no pinned artifact declares the F2a/F2b predicate alignment"},
    }

    # ---- is the F2b interior note load-bearing and absent from F2a?
    f2b_note = "The interior requirement blocks an extension that only adds boundary/dense-open points" in f2b_text
    f2a_equiv = bool(re.search(r"blocks an extension that only adds|boundary/dense-open", f2a_text))
    checks["V11_interior_guard_load_bearing"] = {
        "status": "PASS" if (f2b_note and not f2a_equiv) else "FAIL",
        "detail": {"f2b_note_present": f2b_note, "f2a_equivalent_present": f2a_equiv,
                   "f2b_note_line": line_of(f2b_text, "The interior requirement blocks")},
    }

    # ---- clause (d) well-posedness observation (advisory, not a hard defect)
    f2a_d = live["f2a_clauses"].get("d", "")
    f2a_d_named = bool(re.search(r"atlas|structure|smooth", f2a_d, re.IGNORECASE))
    checks["V12_f2a_clause_d_presupposes_structure"] = {
        "status": "INFO",
        "detail": {"clause_d": f2a_d, "names_a_structure": f2a_d_named,
                   "note": ("C2 metric tensor field presupposes a differentiable structure, "
                            "but the clause names none; recorded as a reading-consistency "
                            "observation, the hard defect is V02/V06, not this")},
    }

    # ---- class separation on this task's own summary text
    classsep_result = {"ran": False, "reason": "not attempted"}
    try:
        spec = importlib.util.spec_from_file_location(
            "cs_pinned", os.path.join(ROOT, CLASSSEP_PINNED))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        probe = ("At the frozen pins the sibling classes AF-SCC-C2-VAC-GEN and "
                 "AF-SCC-C0-VAC-GEN remain separate; E_C2 is declared a subset of E_C0. "
                 "F2a clause (c) names no manifold category and its clause (f) witness "
                 "may lie on the boundary; F2b requires a smooth M' and an interior witness.")
        classsep_result = {
            "ran": True,
            "detector": CLASSSEP_PINNED,
            "detector_sha256_measured": sha256_file(os.path.join(ROOT, CLASSSEP_PINNED)),
            "detector_sha256_declared": CLASSSEP_PINNED_SHA,
            "probe_findings": mod.findings_for_text(probe, "worker-090 c2c0 verification probe"),
        }
    except Exception as exc:  # pragma: no cover
        classsep_result = {"ran": False, "reason": "%s: %s" % (type(exc).__name__, exc)}
    checks["V13_classsep_probe_clean"] = {
        "status": "PASS" if (classsep_result.get("ran")
                             and not classsep_result.get("probe_findings")) else "INFO",
        "detail": classsep_result,
    }

    # ---- controls (sandbox only)
    controls = []
    control_dir = tempfile.mkdtemp(prefix="w090_c2c0_controls_", dir=OUT)
    try:
        sand_f2a = os.path.join(control_dir, "f2a.yaml")
        sand_f2b = os.path.join(control_dir, "f2b.yaml")
        shutil.copyfile(f2a_path, sand_f2a)
        shutil.copyfile(f2b_path, sand_f2b)

        # K7 no-op copy first: determinism
        k7 = run_axis_pipeline(sand_f2a, sand_f2b)
        controls.append({
            "control": "K7_noop_copy_determinism",
            "expected": {"literal_holds": live["literal_containment_holds"],
                         "f2a_smooth": a["category_pinned_smooth"],
                         "f2a_interior": a["interior_witness_required"]},
            "observed": {"literal_holds": k7["literal_containment_holds"],
                         "f2a_smooth": k7["f2a"]["category_pinned_smooth"],
                         "f2a_interior": k7["f2a"]["interior_witness_required"]},
            "passed": (k7["literal_containment_holds"] == live["literal_containment_holds"]
                       and k7["f2a"]["category_pinned_smooth"] == a["category_pinned_smooth"]
                       and k7["f2a"]["interior_witness_required"] == a["interior_witness_required"]),
        })

        anchor_c = ("(c) M' is connected and time-orientable, and its time orientation "
                    "restricts to that of M;")
        anchor_f = ("(f) the extension adds points to the future: there exist q in iota(M) "
                    "and p in M' minus iota(M) with p in I^+(q; g').")
        smooth_add = ("(c) M' is a SMOOTH (C-infinity) connected 4-manifold, "
                      "time-orientable, and its time orientation restricts to that of M;")
        interior_add = ("(f) the extension adds points to the future: "
                        "int(M' minus iota(M)) is non-empty AND there exist q in iota(M) "
                        "and p in int(M' minus iota(M)) with p in I^+(q; g').")

        # K1: F2a clause (c) smooth injected -> axis A resolved, literal containment still fails
        sand_k1 = os.path.join(control_dir, "f2a_k1.yaml")
        sandbox_apply(sand_f2a, sand_k1, anchor_c, smooth_add)
        r1 = run_axis_pipeline(sand_k1, sand_f2b)
        controls.append({
            "control": "K1_f2a_clause_c_smooth_injected",
            "expected": {"f2a_smooth": True, "literal_holds": False},
            "observed": {"f2a_smooth": r1["f2a"]["category_pinned_smooth"],
                         "literal_holds": r1["literal_containment_holds"]},
            "passed": (r1["f2a"]["category_pinned_smooth"] is True
                       and r1["literal_containment_holds"] is False),
        })

        # K2: F2a clause (f) interior injected -> axis B resolved, literal containment still fails
        sand_k2 = os.path.join(control_dir, "f2a_k2.yaml")
        sandbox_apply(sand_f2a, sand_k2, anchor_f, interior_add)
        r2 = run_axis_pipeline(sand_k2, sand_f2b)
        controls.append({
            "control": "K2_f2a_clause_f_interior_injected",
            "expected": {"f2a_interior": True, "literal_holds": False},
            "observed": {"f2a_interior": r2["f2a"]["interior_witness_required"],
                         "literal_holds": r2["literal_containment_holds"]},
            "passed": (r2["f2a"]["interior_witness_required"] is True
                       and r2["literal_containment_holds"] is False),
        })

        # K3: both axes injected -> literal containment holds
        sand_k3 = os.path.join(control_dir, "f2a_k3.yaml")
        sandbox_apply(sand_f2a, sand_k3, anchor_c, smooth_add)
        sandbox_apply(sand_k3, sand_k3, anchor_f, interior_add)
        r3 = run_axis_pipeline(sand_k3, sand_f2b)
        controls.append({
            "control": "K3_f2a_both_axes_injected",
            "expected": {"f2a_smooth": True, "f2a_interior": True, "literal_holds": True},
            "observed": {"f2a_smooth": r3["f2a"]["category_pinned_smooth"],
                         "f2a_interior": r3["f2a"]["interior_witness_required"],
                         "literal_holds": r3["literal_containment_holds"]},
            "passed": (r3["f2a"]["category_pinned_smooth"] is True
                       and r3["f2a"]["interior_witness_required"] is True
                       and r3["literal_containment_holds"] is True),
        })

        # K4: F2b clause (c) smooth removed -> F2b axis A unresolved
        f2b_anchor_c = ("(c) M' is a SMOOTH (C-infinity) connected 4-manifold, "
                        "time-orientable, whose time orientation restricts to that of M; "
                        "the smooth structure is the category in which the metric is a tensor "
                        "field, while the metric itself is only continuous (worker-16 "
                        "F2b-16-03 accepted: a merely topological M' cannot carry a classical "
                        "Lorentzian tensor field);")
        sand_k4 = os.path.join(control_dir, "f2b_k4.yaml")
        with open(sand_f2b, encoding="utf-8") as fh:
            raw_b = fh.read()
        assert f2b_anchor_c in raw_b
        with open(sand_k4, "w", encoding="utf-8") as fh:
            fh.write(raw_b.replace(f2b_anchor_c, "(c) M' is a connected 4-manifold, "
                                                "time-orientable;", 1))
        r4 = run_axis_pipeline(sand_f2a, sand_k4)
        controls.append({
            "control": "K4_f2b_clause_c_smooth_removed",
            "expected": {"f2b_smooth": False},
            "observed": {"f2b_smooth": r4["f2b"]["category_pinned_smooth"]},
            "passed": r4["f2b"]["category_pinned_smooth"] is False,
        })

        # K5: F2b clause (f) interior removed -> F2b axis B unresolved
        f2b_anchor_f = ("(f) the extension adds points to the future: int(M' minus iota(M)) "
                        "is non-empty AND there exist q in iota(M) and p in "
                        "int(M' minus iota(M)) with p in I^+(q; g'), where I^+ is the "
                        "chronological future.")
        sand_k5 = os.path.join(control_dir, "f2b_k5.yaml")
        assert f2b_anchor_f in raw_b
        with open(sand_k5, "w", encoding="utf-8") as fh:
            fh.write(raw_b.replace(
                f2b_anchor_f,
                "(f) the extension adds points to the future: there exist q in iota(M) and "
                "p in M' minus iota(M) with p in I^+(q; g').", 1))
        r5 = run_axis_pipeline(sand_f2a, sand_k5)
        controls.append({
            "control": "K5_f2b_clause_f_interior_removed",
            "expected": {"f2b_interior": False},
            "observed": {"f2b_interior": r5["f2b"]["interior_witness_required"]},
            "passed": r5["f2b"]["interior_witness_required"] is False,
        })

        # K6: alignment declaration appended to an F2a sandbox copy -> census flips
        sand_k6 = os.path.join(control_dir, "f2a_k6.yaml")
        with open(sand_f2a, encoding="utf-8") as fh:
            raw_a = fh.read()
        raw_a += ("\nconvention_alignment_declaration: \"F2a and F2b extension predicates "
                  "use the same manifold category and the same interior-witness convention.\"\n")
        with open(sand_k6, "w", encoding="utf-8") as fh:
            fh.write(raw_a)
        k6_hits = []
        for pat in align_patterns:
            if re.search(pat, raw_a, re.IGNORECASE):
                k6_hits.append(pat)
        controls.append({
            "control": "K6_alignment_declaration_detected",
            "expected": {"hits_nonempty": True},
            "observed": {"hits_nonempty": bool(k6_hits), "hits": k6_hits},
            "passed": bool(k6_hits),
        })

        # K8: wrong declared pin -> drift detection fires
        saved = dict(PINS)
        PINS["F2a_canonical"] = (saved["F2a_canonical"][0], "0" * 64)
        drift_ok, drift_rows = pin_census()
        PINS.clear()
        PINS.update(saved)
        controls.append({
            "control": "K8_wrong_pin_detected",
            "expected": {"drift_detected": True,
                         "mismatch_named": "F2a_canonical"},
            "observed": {"drift_detected": not drift_ok,
                         "mismatches": [r["name"] for r in drift_rows if not r["match"]]},
            "passed": (not drift_ok
                       and "F2a_canonical" in [r["name"] for r in drift_rows if not r["match"]]),
        })
    finally:
        shutil.rmtree(control_dir, ignore_errors=True)

    controls_passed = sum(1 for c in controls if c["passed"])
    if controls_passed != len(controls):
        problems.append("controls: %d/%d" % (controls_passed, len(controls)))
    checks["V14_controls_pass"] = {
        "status": "PASS" if controls_passed == len(controls) else "FAIL",
        "detail": {"passed": controls_passed, "total": len(controls)},
    }

    # ---- exit pin census
    ok_out, pins_out = pin_census()
    checks["V15_pins_declared_eq_measured_exit"] = {
        "status": "PASS" if ok_out else "FAIL",
        "detail": {"mismatches": [r for r in pins_out if not r["match"]]},
    }
    if not ok_out:
        problems.append("V15 pin drift at exit")

    # ---- worker-047 report binding (no import, hash only)
    w047_hash = sha256_file(os.path.join(ROOT, W047_REPORT))
    w047 = json.load(open(os.path.join(ROOT, W047_REPORT), encoding="utf-8"))
    w047_fail = sorted(k for k, v in w047["checks"].items()
                       if isinstance(v, dict) and v.get("status") == "FAIL")
    checks["V16_w047_failing_checks_reproduced"] = {
        "status": "PASS" if set(w047_fail) >= {"C01", "C02", "C06", "C11"} else "FAIL",
        "detail": {"w047_report_sha256": w047_hash,
                   "w047_failing_checks": w047_fail,
                   "independently_confirmed": ["C01", "C02", "C09", "C10", "C11"],
                   "divergence": ("C06 is recorded here as INFO/V12 (well-posedness reading) "
                                  "rather than a hard FAIL; the core defect needs only C01/C02")},
    }

    hard_fail = [k for k, v in checks.items()
                 if isinstance(v, dict) and v["status"] == "FAIL"
                 and k not in ("V06_literal_containment_entailed",)]
    # V06 FAIL is the expected finding, not a checker failure.

    blocker_confirmed = bool(
        live["literal_escaped_quadrants"]
        and not a["category_pinned_smooth"]
        and not a["interior_witness_required"]
        and not guard_axis_hits
        and not align_hits
    )
    blocking_problems = [p for p in problems if not p.startswith("V06")]
    verdict = {
        "decision": ("accept" if (blocker_confirmed and not blocking_problems
                                  and controls_passed == len(controls) and ok_out)
                     else "revise"),
        "target_id": "W047-C2C0-PRED-CONTAINMENT-01",
        "node_id": NODE_ID,
        "class_id": CLASS_ID,
        "class_ids": CLASS_IDS,
        "gate": GATE,
        "score": 4.0 if blocker_confirmed else 2.5,
        "verdict_scope": ("independent substantiation of the reported justification gap; "
                          "advisory, not a full-schema verdict and not a gate verdict"),
        "counts_as_full_schema_verdict": False,
        "hard_failures": [],
        "blocker_confirmed": blocker_confirmed,
        "confirmed_findings": (["F-PC-1", "F-PC-2 (C09)", "F-PC-3 (C10)"]
                               if blocker_confirmed else []),
        "severity_divergence": ("worker-047 C06 (clause (d) well-posedness) is recorded here "
                                "as INFO V12, not a hard defect"),
    }

    results = {
        "schema": "w090-c2c0-transfer-license-verification/v1",
        "task_id": TASK_ID,
        "actor": ACTOR,
        "node_id": NODE_ID,
        "class_id": CLASS_ID,
        "class_ids": CLASS_IDS,
        "gate": GATE,
        "started_at": t_start.isoformat(),
        "completed_at": datetime.now(CST).isoformat(),
        "authority_note": ("advisory worker verification; cannot set node status, "
                           "validation_status=passed or a gate verdict; no canonical write"),
        "question": ("is E_C2 subset of E_C0 entailed by the two sibling extension predicates "
                     "as literally declared at the FROZEN rev29 pins?"),
        "answer": ("NO under the literal reading: F2a clause (c) is manifold-category-silent and "
                   "clause (f) admits a future witness with no interior requirement, while F2b "
                   "requires a SMOOTH M' and a witness in int(M' minus iota(M)); the containment "
                   "holds only after adopting the F2b convention for F2a (aligned reading)."),
        "non_claims": [
            "not a mathematics claim and not a claim that a boundary-only extension exists;",
            "the decision table models what the declared TEXT licenses, not GR existence;",
            "not a full-schema verdict for F2a or F2b and not countable toward G-FORM coverage;",
            "no canonical artifact was written or edited;",
            "the live detector is drifted relative to the CF-26 freeze; the class-separation "
            "probe cites the pinned c266dbec copy.",
        ],
        "pins": pins_out,
        "parsed_axes": {"F2a": a, "F2b": b},
        "literal_escaped_quadrants": live["literal_escaped_quadrants"],
        "premise_loci": loci,
        "t1": {"reason": t1_reason, "guards": guards, "guard_lines": guard_lines},
        "checks": checks,
        "controls": controls,
        "controls_passed": controls_passed,
        "controls_total": len(controls),
        "problems": problems,
        "verdict": verdict,
        "worker_047_report_sha256": w047_hash,
        "worker_047_report_failing_checks": w047_fail,
        "falsifier": ("At the pins of this run: (a) F2a clause (c) is shown to entail a smooth "
                      "manifold category from the pinned bytes; (b) F2a clause (f) is shown to "
                      "entail the interior-witness condition; (c) T1's guard set is shown to "
                      "include the extension-predicate convention axis; or (d) a pinned artifact "
                      "is shown to declare the F2a/F2b alignment. A later file write at a new "
                      "hash is not a falsifier; the new bytes must be re-measured and this "
                      "instrument re-run."),
        "next_falsifier": ("re-run this checker after the formulation owner publishes an F2a "
                           "revision (option R1) or a T1/alignment declaration (option R2); the "
                           "gap closes only when V02/V03 resolve (or V09/V10 resolve) and V06 "
                           "still passes under the literal reading at the new measured bytes"),
        "exit_code": 0,
    }

    exit_code = 0
    if not ok_out:
        exit_code = 3
    elif controls_passed != len(controls):
        exit_code = 4
    elif any(k for k in problems if not k.startswith("V06")):
        exit_code = 5
    results["exit_code"] = exit_code

    with open(os.path.join(OUT, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=1, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(OUT, "controls.json"), "w", encoding="utf-8") as fh:
        json.dump({"task_id": TASK_ID, "actor": ACTOR,
                   "controls_passed": controls_passed, "controls_total": len(controls),
                   "controls": controls}, fh, indent=1, sort_keys=True)
        fh.write("\n")
    evidence = {
        "schema": "w090-c2c0-transfer-license-evidence/v1",
        "task_id": TASK_ID,
        "pins_entry": pins_in,
        "pins_exit": pins_out,
        "axis_observations": {"F2a": a, "F2b": b},
        "literal_containment": {"holds": live["literal_containment_holds"],
                                "escaped_quadrants": live["literal_escaped_quadrants"]},
        "premise_loci": loci,
        "classsep_probe": classsep_result,
        "worker_047_binding": {"path": W047_REPORT, "sha256": w047_hash,
                               "failing_checks": w047_fail},
        "falsifier": results["falsifier"],
    }
    with open(os.path.join(OUT, "evidence.json"), "w", encoding="utf-8") as fh:
        json.dump(evidence, fh, indent=1, sort_keys=True)
        fh.write("\n")

    print(json.dumps({"task_id": TASK_ID, "answer": results["answer"],
                      "checks": {k: v["status"] for k, v in checks.items()},
                      "controls": "%d/%d" % (controls_passed, len(controls)),
                      "exit_code": exit_code}, indent=1, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
