#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
W047-C2C0-PRED-CONTAINMENT-01 instrument.

Question
--------
At the pinned rev13 canonical bytes, do the two sibling extension predicates
(F2a AF-SCC-C2-VAC-GEN and F2b AF-SCC-C0-VAC-GEN) entail the containment
E_C2 subset of E_C0 that F2a's implication ledger, the F0 supplement, and
taxonomy transfer rule T1 all rely on?

Method
------
Deterministic, stdlib-only, no network. Read-only against every canonical and
mirror input (only this artifact directory is written). Clauses (c), (d), (f)
of both extension predicates are parsed from the pinned text; the three
containment-premise loci (F2a ledger, F0 supplement, taxonomy T1) are located
and their guard sets inspected. Nine synthetic single/dual-axis mutants are
run as controls; the instrument fails closed (exit 2) on any input drift and
fails calibration (exit 3) if a control does not flip exactly its pre-registered
checks.

Exit codes
----------
0  defect verified: >=1 contract check FAILs and all controls behaved as pre-registered
1  reserved (hard error while writing output)
2  input drift / missing / unreadable pinned input (fail closed)
3  control mis-calibration (fail closed)
4  clean: no contract check FAILs
5  a required clause or premise locus did not parse

Authority
---------
Worker evidence only. No gate verdict, no node status, no canonical write.
The verdict is bounded to the sha256 pins recorded in the report.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CST = timezone(timedelta(hours=8))

TASK_ID = "W047-C2C0-PRED-CONTAINMENT-01"
ACTOR = "worker-047"
CLASS_IDS = ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
NODE_IDS = ["F2a", "F2b", "F0", "A1"]

F2A = "schemas/af_scc_c2_vacuum.yaml"
F2B = "schemas/af_scc_c0_vacuum.yaml"
F1 = "schemas/af_wcc_vacuum.yaml"
F2A_M = "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"
F2B_M = "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
F1_M = "artifacts/formulation/schemas/af_wcc_vacuum.yaml"
TAX = "research_map/formulation_taxonomy.yaml"
SUP = "artifacts/formulation/formulation_taxonomy.yaml"
FROZEN = "artifacts/formulation/FROZEN.json"

PINS = {
    F2A: "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    F2B: "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    F1: "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    F2A_M: "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    F2B_M: "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    F1_M: "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    TAX: "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    SUP: "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    FROZEN: "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
}

# Pre-registered canonical expectations. The instrument reports observed
# status; these are the calibration targets for the controls, not assertions
# that force the canonical result.
CONTRACT_CHECKS = ["C01", "C02", "C03", "C04", "C05", "C06", "C07", "C08", "C09", "C10", "C11"]

MANIFOLD_CATEGORY_RE = re.compile(
    r"SMOOTH\s*\(C-?infinity\)|SMOOTH\s+4-manifold|smooth\s+4-manifold|C-?infinity\)\s+connected\s+4-manifold",
    re.IGNORECASE,
)
INTERIOR_RE = re.compile(r"\bint\s*\(|\binterior\b", re.IGNORECASE)
AXIS_GUARD_RE = re.compile(
    r"extension[_ ]predicate|extension[_ ]class|manifold\s+category|interior|clause\s*\(f\)|convention",
    re.IGNORECASE,
)
ALIGNMENT_DECL_RE = re.compile(
    r"predicate\s+(?:convention\s+)?align|aligned\s+extension\s+predicate|identical\s+extension\s+predicate|"
    r"same\s+manifold\s+category|shared\s+extension\s+predicate|convention[_ ]alignment",
    re.IGNORECASE,
)


def now_cst():
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(path):
    with open(path, "rb") as fh:
        return sha256_bytes(fh.read())


def read_text(path):
    with open(path, "rb") as fh:
        return fh.read().decode("utf-8")


def block_lines(lines, key, indent=0):
    """Return the raw lines of a top-level (or `indent`-spaced) `key:` block."""
    prefix = " " * indent + key + ":"
    start = None
    for i, line in enumerate(lines):
        if line.rstrip() == prefix:
            start = i
            break
    if start is None:
        return None
    out = [lines[start]]
    for line in lines[start + 1:]:
        if line.strip() == "":
            out.append(line)
            continue
        cur = len(line) - len(line.lstrip(" "))
        if cur <= indent:
            break
        out.append(line)
    return out


def sub_block(lines, key, indent):
    """Return lines of a nested `key:` block at `indent` spaces."""
    prefix = " " * indent + key + ":"
    start = None
    for i, line in enumerate(lines):
        if line.rstrip() == prefix:
            start = i
            break
    if start is None:
        return None
    out = [lines[start]]
    for line in lines[start + 1:]:
        if line.strip() == "":
            out.append(line)
            continue
        cur = len(line) - len(line.lstrip(" "))
        if cur <= indent:
            break
        out.append(line)
    return out


def extract_definition(ext_block):
    """Join the folded `definition: >-` scalar inside an extension_predicate block."""
    if ext_block is None:
        return None
    start = None
    for i, line in enumerate(ext_block):
        if re.match(r"^\s*definition:\s*>-?\s*$", line):
            start = i
            break
    if start is None:
        return None
    out = []
    for line in ext_block[start + 1:]:
        if line.strip() == "":
            continue
        cur = len(line) - len(line.lstrip(" "))
        if cur <= 2:
            break
        out.append(line.strip())
    return " ".join(out)


def clause(defn, letter):
    if not defn:
        return None
    m = re.search(r"\(" + letter + r"\)\s*(.*?)(?=\([a-z]\)|$)", defn, re.S)
    return m.group(1).strip() if m else None


def parse_axis_pack(texts):
    """Parse the clause and premise material this task is about from raw texts."""
    parsed = {}
    f2a_lines = texts[F2A].split("\n")
    f2b_lines = texts[F2B].split("\n")
    f2a_defn = extract_definition(block_lines(f2a_lines, "extension_predicate", 0))
    f2b_defn = extract_definition(block_lines(f2b_lines, "extension_predicate", 0))
    parsed["f2a_definition_parsed"] = f2a_defn is not None
    parsed["f2b_definition_parsed"] = f2b_defn is not None
    parsed["f2a_c"] = clause(f2a_defn, "c")
    parsed["f2a_d"] = clause(f2a_defn, "d")
    parsed["f2a_f"] = clause(f2a_defn, "f")
    parsed["f2b_c"] = clause(f2b_defn, "c")
    parsed["f2b_d"] = clause(f2b_defn, "d")
    parsed["f2b_f"] = clause(f2b_defn, "f")

    def topo(text):
        blk = block_lines(text.split("\n"), "topology", 0)
        if not blk:
            return None
        for line in blk:
            if line.strip().startswith("extension_topology:"):
                return line.strip()
        return None

    parsed["f2a_extension_topology"] = topo(texts[F2A])
    parsed["f2b_extension_topology"] = topo(texts[F2B])

    # F2a class_boundary.one_way_implication premise locus.
    parsed["f2a_one_way_implication"] = None
    for line in texts[F2A].split("\n"):
        if line.strip().startswith("one_way_implication:"):
            parsed["f2a_one_way_implication"] = line.strip()
            break

    # F2a implication-ledger containment row (C0 nonextendibility entails C2 nonextendibility).
    ledger = block_lines(f2a_lines, "implication_ledger", 0) or []
    row = None
    for line in ledger:
        if ('from: "no proper future C0 extension"' in line
                and 'to: "no proper future C2 extension"' in line):
            row = line.strip()
            break
    parsed["f2a_ledger_row"] = row
    if row:
        m = re.search(r'reason:\s*"([^"]*)"', row)
        parsed["f2a_ledger_reason"] = m.group(1) if m else None
    else:
        parsed["f2a_ledger_reason"] = None

    # F0 supplement containment premise (line ~191).
    sup_row = None
    for line in texts[SUP].split("\n"):
        if ('from: "AF-SCC-C0-VAC-GEN"' in line
                and 'to: "AF-SCC-C2-VAC-GEN"' in line
                and "entails" in line):
            sup_row = line.strip()
            break
    parsed["supplement_row"] = sup_row
    if sup_row:
        m = re.search(r'status:\s*"([^"]*)"', sup_row)
        parsed["supplement_reason"] = m.group(1) if m else sup_row
    else:
        parsed["supplement_reason"] = None

    # Taxonomy transfer rule T1 (allowed list: reason + guards).
    tax_lines = texts[TAX].split("\n")
    tr = block_lines(tax_lines, "transfer_rules", 0) or []
    t1_lines = []
    in_t1 = False
    for line in tr:
        if re.match(r"^\s*-\s*id:\s*\"T1\"\s*$", line):
            in_t1 = True
            t1_lines.append(line)
            continue
        if in_t1:
            if re.match(r"^\s*-\s*id:", line):
                break
            t1_lines.append(line)
    parsed["t1_lines"] = t1_lines
    parsed["t1_reason"] = None
    parsed["t1_guards"] = []
    for line in t1_lines:
        m = re.search(r"reason:\s*\"([^\"]*)\"", line)
        if m and parsed["t1_reason"] is None:
            parsed["t1_reason"] = m.group(1)
        if line.strip().startswith("- ") and "reason:" not in line and "id:" not in line:
            parsed["t1_guards"].append(line.strip()[2:].strip().strip('"'))

    # Explicit cross-class predicate-alignment declaration anywhere in the pins.
    parsed["alignment_hits"] = []
    for path in (F2A, F2B, TAX, SUP):
        for i, line in enumerate(texts[path].split("\n"), 1):
            if ALIGNMENT_DECL_RE.search(line):
                parsed["alignment_hits"].append({"path": path, "line": i, "text": line.strip()[:240]})

    # H2_loc predicate canonical definition present among the pinned canonical schemas?
    h2_hits = []
    for path in (F2A, F2B, F1):
        for i, line in enumerate(texts[path].split("\n"), 1):
            if re.search(r"H2_loc.*extension_predicate|extension_predicate.*H2_loc", line, re.IGNORECASE):
                h2_hits.append({"path": path, "line": i})
    parsed["h2loc_definition_hits"] = h2_hits

    # data_class / genericity block comparison between siblings.
    def blk(path, key):
        b = block_lines(texts[path].split("\n"), key, 0)
        return "\n".join(b) if b else ""

    def norm(s):
        s = re.sub(r"hypotheses_reconciliation:[^\n]*", "", s)
        s = re.sub(r"\s+", " ", s)
        return s.strip()

    def field_map(block):
        out = {}
        for line in block.split("\n"):
            mm = re.match(r"^  ([a-z_]+):\s*(.*)$", line)
            if mm:
                out[mm.group(1)] = re.sub(r"\s+", " ", mm.group(2)).strip()
        return out

    dc_a, dc_b = blk(F2A, "data_class"), blk(F2B, "data_class")
    fa, fb = field_map(dc_a), field_map(dc_b)
    parsed["data_class_diff_keys"] = sorted(k for k in set(fa) | set(fb) if fa.get(k) != fb.get(k))
    parsed["data_class_equal_modulo_admitted_prose"] = not parsed["data_class_diff_keys"]
    parsed["data_class_f2a"] = dc_a
    parsed["data_class_f2b"] = dc_b
    ga, gb = field_map(blk(F2A, "genericity")), field_map(blk(F2B, "genericity"))
    parsed["genericity_diff_keys"] = sorted(k for k in set(ga) | set(gb) if ga.get(k) != gb.get(k))
    parsed["genericity_equal"] = not parsed["genericity_diff_keys"]
    return parsed


def check(status, detail, evidence=None, expectation=None):
    out = {"status": status, "detail": detail}
    if evidence:
        out["evidence"] = evidence
    if expectation:
        out["expectation"] = expectation
    return out


def run_checks(texts):
    """Return {check_id: {...}} and a parse flag."""
    p = parse_axis_pack(texts)
    checks = {}

    def add(cid, status, detail, evidence=None, expectation=None):
        checks[cid] = check(status, detail, evidence, expectation)

    parse_ok = bool(p["f2a_definition_parsed"] and p["f2b_definition_parsed"]
                    and p["f2a_c"] and p["f2a_f"] and p["f2b_c"] and p["f2b_f"])

    # C01: F2a clause (c) declares a manifold category token.
    if p["f2a_c"] is None:
        add("C01", "UNPARSED", "F2a clause (c) not parsed")
    elif MANIFOLD_CATEGORY_RE.search(p["f2a_c"]) or (
            p["f2a_extension_topology"] and MANIFOLD_CATEGORY_RE.search(p["f2a_extension_topology"])):
        add("C01", "PASS", "F2a clause (c)/extension_topology declares a manifold category",
            p["f2a_c"][:300])
    else:
        add("C01", "FAIL",
            "F2a clause (c) declares no manifold category token (no SMOOTH/C-infinity); "
            "the extension predicate is category-silent",
            {"clause_c": p["f2a_c"][:300], "extension_topology": (p["f2a_extension_topology"] or "")[:300]})

    # C02: F2a clause (f) requires an interior witness.
    if p["f2a_f"] is None:
        add("C02", "UNPARSED", "F2a clause (f) not parsed")
    elif INTERIOR_RE.search(p["f2a_f"]):
        add("C02", "PASS", "F2a clause (f) carries the interior-witness requirement", p["f2a_f"][:300])
    else:
        add("C02", "FAIL",
            "F2a clause (f) admits a witness p in M' minus iota(M) with no interior requirement; "
            "boundary-only additions are not excluded",
            {"clause_f": p["f2a_f"][:300]})

    # C03: F2b clause (c) declares SMOOTH.
    if p["f2b_c"] is None:
        add("C03", "UNPARSED", "F2b clause (c) not parsed")
    elif MANIFOLD_CATEGORY_RE.search(p["f2b_c"]):
        add("C03", "PASS", "F2b clause (c) declares a SMOOTH (C-infinity) manifold category", p["f2b_c"][:300])
    else:
        add("C03", "FAIL", "F2b clause (c) lost the smooth-category token", p["f2b_c"][:300])

    # C04: F2b clause (f) requires the interior witness in both places.
    if p["f2b_f"] is None:
        add("C04", "UNPARSED", "F2b clause (f) not parsed")
    else:
        nonempty_int = bool(re.search(r"int\s*\(.*?\)\s*is\s+non-empty", p["f2b_f"], re.S))
        witness_int = len(re.findall(r"int\s*\(", p["f2b_f"])) >= 2
        if nonempty_int and witness_int:
            add("C04", "PASS", "F2b clause (f) requires non-empty interior and an interior witness", p["f2b_f"][:360])
        else:
            add("C04", "FAIL", "F2b clause (f) interior requirement incomplete",
                {"nonempty_int": nonempty_int, "witness_int": witness_int, "clause_f": p["f2b_f"][:360]})

    # C05: strictness of the sibling witness conditions (F2b strictly stronger than F2a).
    c02, c04 = checks["C02"]["status"], checks["C04"]["status"]
    if c02 == "FAIL" and c04 == "PASS":
        add("C05", "PASS",
            "F2b clause (f) is strictly stronger than F2a clause (f): F2a admits a boundary witness, "
            "F2b requires a witness in int(M' minus iota(M)) plus non-empty interior")
    elif c02 == "PASS" and c04 == "PASS":
        add("C05", "FAIL", "both siblings require the interior witness; strictness is gone")
    elif c02 == "FAIL" and c04 == "FAIL":
        add("C05", "FAIL", "neither sibling requires the interior witness; the rev13 repair is absent on both sides")
    else:
        add("C05", "INFO", "strictness not decidable from current parse",
            {"C02": c02, "C04": c04})

    # C06: F2a well-posedness of clause (d) given the declared manifold category.
    if p["f2a_d"] is None:
        add("C06", "UNPARSED", "F2a clause (d) not parsed")
    elif checks["C01"]["status"] == "PASS":
        add("C06", "PASS", "F2a declares the manifold category needed by its C2-metric clause (d)")
    else:
        add("C06", "FAIL",
            "F2a clause (d) requires g' to be a C2 Lorentzian metric on M' while clause (c) declares no "
            "smooth structure on M'; differentiability of a tensor field presupposes one, so the predicate "
            "is well-posed only under an undeclared convention",
            {"clause_c": (p["f2a_c"] or "")[:240], "clause_d": p["f2a_d"][:240]})

    # C07: F2a implication-ledger row asserts the containment premise.
    if p["f2a_ledger_row"]:
        reason = p["f2a_ledger_reason"] or ""
        if "E_C2 subset of E_C0" in reason:
            add("C07", "PASS",
                "F2a implication_ledger asserts C0-nonextendibility entails C2-nonextendibility with reason "
                "'E_C2 subset of E_C0'", {"row": p["f2a_ledger_row"][:320]})
        else:
            add("C07", "FAIL", "F2a ledger row present but reason no longer cites E_C2 subset of E_C0",
                {"row": p["f2a_ledger_row"][:320], "reason": reason[:240]})
    else:
        add("C07", "FAIL", "F2a implication_ledger C0->C2 entailment row not found")

    # C08: F0 supplement asserts the same premise.
    if p["supplement_reason"] and re.search(r"C2 extension is a C0 extension|extension-class containment", p["supplement_reason"], re.I):
        add("C08", "PASS", "F0 supplement asserts the containment premise (every C2 extension is a C0 extension)",
            {"row": (p["supplement_row"] or "")[:340]})
    else:
        add("C08", "FAIL", "F0 supplement containment premise not found in expected form",
            {"row": (p["supplement_row"] or "")[:340]})

    # C09: taxonomy T1 guards cover the extension-predicate convention axis.
    guard_hits = [g for g in p["t1_guards"] if AXIS_GUARD_RE.search(g)]
    if guard_hits:
        add("C09", "PASS", "T1 guard set names the extension-predicate convention axis", {"guards": guard_hits})
    else:
        add("C09", "FAIL",
            "taxonomy transfer rule T1 guards cover data_class and genericity only; no guard names the "
            "extension-predicate convention axis (manifold category / interior witness)",
            {"reason": (p["t1_reason"] or "")[:240], "guards": p["t1_guards"]})

    # C10: explicit cross-class predicate-alignment declaration present.
    if p["alignment_hits"]:
        add("C10", "PASS", "an explicit predicate-alignment declaration is present",
            {"hits": p["alignment_hits"][:5]})
    else:
        add("C10", "FAIL",
            "no pinned artifact declares that the F2a and F2b extension predicates share the manifold "
            "category and interior-witness conventions")

    # C11: is the declared containment licensed by the declared bytes?
    licensed_by_clauses = (checks["C01"]["status"] == "PASS" and checks["C02"]["status"] == "PASS"
                           and checks["C06"]["status"] == "PASS")
    licensed = licensed_by_clauses or checks["C10"]["status"] == "PASS"
    if licensed:
        add("C11", "PASS",
            "the declared containment E_C2 subset of E_C0 is licensed by the declared clauses "
            "(aligned categories/witness convention) or by an explicit alignment declaration")
    else:
        add("C11", "FAIL",
            "the declared containment E_C2 subset of E_C0 is NOT entailed by the declared clause pair: "
            "F2a clause (c) is category-silent and clause (f) admits a boundary witness, while F2b clause (c) "
            "requires SMOOTH M' and clause (f) requires an interior witness; the containment holds only under "
            "an unstated cross-class convention, so the F2a ledger reason, the supplement premise and T1 are "
            "not licensed by the pinned bytes",
            {"C01": checks["C01"]["status"], "C02": checks["C02"]["status"], "C06": checks["C06"]["status"],
             "C10": checks["C10"]["status"]})

    # C12 (INFO): H2_loc middle term canonical definition.
    if p["h2loc_definition_hits"]:
        add("C12", "INFO", "H2_loc extension predicate text located among canonical schemas",
            {"hits": p["h2loc_definition_hits"][:5]})
    else:
        add("C12", "INFO",
            "the H2_loc middle term of the declared chain is not defined by a canonical schema in the pinned "
            "set; it is a registry/variant-level class (not a defect claim here)")

    # C13 (INFO): data_class comparison.
    if p["data_class_diff_keys"]:
        add("C13", "INFO",
            "sibling data_class blocks: machine-checkable field names identical; textual differences confined to "
            + ", ".join(p["data_class_diff_keys"]) + " (F2b adm_mass locator adds a citation parenthetical)",
            {"diff_keys": p["data_class_diff_keys"]})
    else:
        add("C13", "INFO", "sibling data_class blocks are textually identical after normalization")

    # C14 (INFO): genericity comparison.
    if p["genericity_diff_keys"]:
        add("C14", "INFO",
            "sibling genericity blocks: differences confined to "
            + ", ".join(p["genericity_diff_keys"]) + " (F2b excluded_set prose adds '(hence C0)')",
            {"diff_keys": p["genericity_diff_keys"]})
    else:
        add("C14", "INFO", "sibling genericity blocks are textually identical after normalization")

    # C15 (INFO): F2a class_boundary.one_way_implication premise locus.
    if p["f2a_one_way_implication"]:
        add("C15", "INFO",
            "F2a class_boundary.one_way_implication asserts the same containment premise "
            "('every C2 extension is a C0 extension')",
            {"line": p["f2a_one_way_implication"][:300]})
    else:
        add("C15", "INFO", "F2a class_boundary.one_way_implication field not found")

    return checks, parse_ok, p


# ---------------------------------------------------------------------------
# Controls: mutate sandbox copies and require exactly the pre-registered flips.
# ---------------------------------------------------------------------------

def _patch_clause(text, letter, insert):
    """Insert `insert` at the end of clause (letter) inside the first extension_predicate definition."""
    lines = text.split("\n")
    blk = block_lines(lines, "extension_predicate", 0)
    if blk is None:
        return text
    joined = "\n".join(blk)
    m = re.search(r"(\(%s\)\s*.*?)(?=\([a-z]\)|$)" % letter, joined, re.S)
    if not m:
        return text
    return text.replace(m.group(1), m.group(1).rstrip() + " " + insert + "\n", 1)


def _patch_first(text, pattern, repl):
    return re.sub(pattern, repl, text, count=1)


def mutate(texts, kind):
    t = dict(texts)
    if kind == "K1_f2a_c_smooth":
        # add a smooth-category token to F2a clause (c)
        lines = t[F2A].split("\n")
        blk = block_lines(lines, "extension_predicate", 0)
        m = re.search(r"\(c\)\s*M' is connected and time-orientable", "\n".join(blk))
        if not m:
            return None
        new_blk = "\n".join(blk).replace(
            "(c) M' is connected and time-orientable",
            "(c) M' is a SMOOTH (C-infinity) connected time-orientable 4-manifold", 1)
        t[F2A] = t[F2A].replace("\n".join(blk), new_blk, 1)
    elif kind == "K2_f2a_f_interior":
        old = "there exist q in iota(M) and p in M' minus iota(M) with p in I^+(q; g')."
        new = ("int(M' minus iota(M)) is non-empty AND there exist q in iota(M) and "
               "p in int(M' minus iota(M)) with p in I^+(q; g').")
        if old not in t[F2A]:
            return None
        t[F2A] = t[F2A].replace(old, new, 1)
    elif kind == "K3_f2a_aligned":
        t = mutate(t, "K1_f2a_c_smooth")
        if t is None:
            return None
        t = mutate(t, "K2_f2a_f_interior")
        if t is None:
            return None
    elif kind == "K4_f2b_c_unsmooth":
        t[F2B] = re.sub(
            r"\(c\) M' is a SMOOTH \(C-infinity\) connected 4-manifold.*?tensor field\);",
            "(c) M' is connected and time-orientable, whose time orientation restricts to that of M;",
            t[F2B], count=1, flags=re.S)
        t[F2B] = t[F2B].replace(
            "M' a connected SMOOTH 4-manifold (the category in which the metric is a tensor field)",
            "M' a connected 4-manifold", 1)
    elif kind == "K5_f2b_f_nointerior":
        old = ("(f) the extension adds points to the future: int(M' minus iota(M)) is non-empty AND "
               "there exist q in iota(M) and p in int(M' minus iota(M)) with p in I^+(q; g')")
        new = ("(f) the extension adds points to the future: there exist q in iota(M) and "
               "p in M' minus iota(M) with p in I^+(q; g')")
        if old not in t[F2B]:
            return None
        t[F2B] = t[F2B].replace(old, new, 1)
    elif kind == "K6_t1_guard":
        old = '- "genericity_kind and genericity_topology must match exactly"'
        new = ('- "genericity_kind and genericity_topology must match exactly"\n'
               '        - "the extension_predicate conventions must match exactly (manifold category and clause (f) interior witness)"')
        if old not in t[TAX]:
            return None
        t[TAX] = t[TAX].replace(old, new, 1)
    elif kind == "K7_alignment_declared":
        t[F2A] = t[F2A].replace(
            "extension_predicate:\n  name: proper_future_extension_in_class",
            "extension_predicate:\n  predicate_convention_alignment: \"identical to AF-SCC-C0-VAC-GEN sibling (manifold category and interior witness)\"\n  name: proper_future_extension_in_class",
            1)
    elif kind == "K8_ledger_reversed":
        t[F2A] = t[F2A].replace("reason: \"E_C2 subset of E_C0, so C0-inextendibility is stronger\"",
                                "reason: \"E_C0 subset of E_C2, so C0-inextendibility is stronger\"", 1)
    elif kind == "K9_truncated_f2a":
        t[F2A] = t[F2A][: t[F2A].find("extension_predicate:") + 200]
    else:
        return None
    return t


CONTROLS = [
    ("K1_f2a_c_smooth", {"C01": "PASS", "C06": "PASS", "C11": "FAIL"}),
    ("K2_f2a_f_interior", {"C02": "PASS", "C05": "FAIL"}),
    ("K3_f2a_aligned", {"C01": "PASS", "C02": "PASS", "C06": "PASS", "C11": "PASS", "C05": "FAIL"}),
    ("K4_f2b_c_unsmooth", {"C03": "FAIL"}),
    ("K5_f2b_f_nointerior", {"C04": "FAIL", "C05": "FAIL"}),
    ("K6_t1_guard", {"C09": "PASS"}),
    ("K7_alignment_declared", {"C10": "PASS", "C11": "PASS"}),
    ("K8_ledger_reversed", {"C07": "FAIL"}),
    ("K9_truncated_f2a", {"PARSE": "UNPARSED"}),
]


def run_controls(texts):
    results = []
    for name, expected in CONTROLS:
        mutated = mutate(texts, name)
        if mutated is None:
            results.append({"control": name, "expected": expected, "observed": None,
                            "passed": False, "error": "mutation anchor not found"})
            continue
        checks, parse_ok, _ = run_checks(mutated)
        observed = {k: v["status"] for k, v in checks.items()}
        observed["PARSE"] = "OK" if parse_ok else "UNPARSED"
        passed = all(observed.get(k) == v for k, v in expected.items())
        results.append({"control": name, "expected": expected,
                        "observed": {k: observed.get(k) for k in expected},
                        "passed": passed})
    return results


def write_report(path, payload):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, sort_keys=False)
        fh.write("\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json-out", default=os.path.join(HERE, "report.json"))
    ap.add_argument("--controls-out", default=None)
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 if any contract check FAILs (used as a repair acceptance test)")
    args = ap.parse_args()

    started = now_cst()
    texts, pin_rows, pin_fail = {}, [], False
    for rel, want in PINS.items():
        p = os.path.join(ROOT, rel)
        if not os.path.isfile(p):
            pin_rows.append({"path": rel, "expected_sha256": want, "measured_sha256": None,
                             "status": "MISSING"})
            pin_fail = True
            continue
        got = sha256_file(p)
        ok = got == want
        pin_rows.append({"path": rel, "expected_sha256": want, "measured_sha256": got,
                         "status": "MATCH" if ok else "DRIFT"})
        if not ok:
            pin_fail = True
        else:
            texts[rel] = read_text(p)

    base = {
        "schema_version": "w047-c2c0-pred-containment/v1",
        "task_id": TASK_ID,
        "actor": ACTOR,
        "started_at": started,
        "node_ids": NODE_IDS,
        "class_ids": CLASS_IDS,
        "method": ("parse extension_predicate clauses (c),(d),(f) of the pinned F2a/F2b schemas; locate the "
                   "three containment-premise loci (F2a implication_ledger, F0 supplement, taxonomy T1); "
                   "test containment soundness and guard coverage; 9 synthetic controls"),
        "authority": "worker evidence only; no gate verdict, no node status, no canonical write",
    }

    if pin_fail:
        base.update({"status": "DRIFT", "pins": pin_rows, "checks": {}, "controls": [],
                     "summary": "fail closed: pinned input missing or drifted; no checks executed"})
        write_report(args.json_out, base)
        print(json.dumps({"status": "DRIFT", "pins": pin_rows}, indent=1))
        return 2

    checks, parse_ok, parsed = run_checks(texts)
    controls = run_controls(texts)
    controls_ok = all(c["passed"] for c in controls)

    defects = [cid for cid in CONTRACT_CHECKS if checks[cid]["status"] == "FAIL"]
    unparsed = [cid for cid, v in checks.items() if v["status"] == "UNPARSED"]

    findings = []
    if checks["C01"]["status"] == "FAIL" and checks["C02"]["status"] == "FAIL":
        findings.append({
            "id": "F-PC-1",
            "severity": "critical",
            "kind": "cross_class_justification_gap",
            "summary": ("the declared containment E_C2 subset of E_C0 is not entailed by the declared clause pair; "
                        "F2a clause (c) is manifold-category-silent and clause (f) admits a boundary witness while "
                        "F2b now requires SMOOTH M' and an interior witness"),
            "loci": ["schemas/af_scc_c2_vacuum.yaml#%s:98" % PINS[F2A][:12],
                     "schemas/af_scc_c0_vacuum.yaml#%s:94" % PINS[F2B][:12],
                     "schemas/af_scc_c2_vacuum.yaml#%s:239" % PINS[F2A][:12],
                     "artifacts/formulation/formulation_taxonomy.yaml#%s:191" % PINS[SUP][:12],
                     "research_map/formulation_taxonomy.yaml#%s:T1" % PINS[TAX][:12]],
            "consequence": ("the reason given for F2a's C0->C2 entailment row, the supplement's 'every C2 extension "
                            "is a C0 extension' premise, and taxonomy transfer rule T1 are all conditional on an "
                            "undeclared alignment of the two extension predicates"),
            "not_claimed": ("this is not a claim that the containment or the transfer is mathematically false, and "
                            "not a claim that a boundary-only extension exists; it is a justification-soundness "
                            "finding about the pinned bytes"),
        })
    if checks["C09"]["status"] == "FAIL":
        findings.append({
            "id": "F-PC-2",
            "severity": "major",
            "kind": "transfer_rule_guard_gap",
            "summary": ("T1's guard set covers data_class and genericity but not the extension-predicate convention "
                        "axis, so a claim transfer can pass every declared guard while the source and target "
                        "predicates disagree on manifold category / interior witness"),
            "locus": "research_map/formulation_taxonomy.yaml#%s:transfer_rules.allowed.T1" % PINS[TAX][:12],
        })
    if checks["C10"]["status"] == "FAIL":
        findings.append({
            "id": "F-PC-3",
            "severity": "major",
            "kind": "missing_alignment_declaration",
            "summary": ("no pinned artifact declares that the F2a and F2b extension predicates share the manifold "
                        "category and interior-witness conventions; the alignment is implicit"),
        })
    if parsed["f2a_ledger_row"]:
        findings.append({
            "id": "F-PC-4",
            "severity": "info",
            "kind": "premise_locus_inventory",
            "summary": "four independent loci rely on the containment premise at the pinned hashes",
            "loci": ["schemas/af_scc_c2_vacuum.yaml:78 class_boundary.one_way_implication",
                     "schemas/af_scc_c2_vacuum.yaml:239 implication_ledger",
                     "artifacts/formulation/formulation_taxonomy.yaml:191",
                     "research_map/formulation_taxonomy.yaml:495-503 transfer_rules.allowed.T1"],
        })
    findings.append({
        "id": "F-PC-5",
        "severity": "info",
        "kind": "corroboration_scope",
        "summary": ("corroborates HF-047-01 / HF-091-02 (F2a extension predicate under-frozen vs the C0 sibling) "
                    "and HF-091-01-family; the increment here is the containment/transfer-justification consequence "
                    "and the T1 guard gap, not the under-freezing observation itself"),
    })

    verdict = {
        "decision": "revise" if defects else "accept",
        "score": 3.5 if defects else 4.0,
        "target_id": "F2a",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "cross_class_ids": CLASS_IDS,
        "counts_as_full_schema_verdict": False,
        "counts_as_independent_second_verdict": False,
        "basis": ("focused cross-sibling predicate-containment verification; not a full-schema verdict and not "
                  "countable toward the two-accept G-FORM coverage"),
        "hard_failures": [f["summary"] for f in findings if f["severity"] == "critical"],
    }

    base.update({
        "completed_at": now_cst(),
        "status": "DEFECT" if defects else ("UNPARSED" if unparsed else "CLEAN"),
        "pins": pin_rows,
        "parsed_material": {
            "f2a_clause_c": parsed["f2a_c"],
            "f2a_clause_d": parsed["f2a_d"],
            "f2a_clause_f": parsed["f2a_f"],
            "f2b_clause_c": parsed["f2b_c"],
            "f2b_clause_f": parsed["f2b_f"],
            "f2a_extension_topology": parsed["f2a_extension_topology"],
            "f2b_extension_topology": parsed["f2b_extension_topology"],
            "f2a_one_way_implication": parsed["f2a_one_way_implication"],
            "f2a_ledger_row": parsed["f2a_ledger_row"],
            "supplement_row": parsed["supplement_row"],
            "t1_reason": parsed["t1_reason"],
            "t1_guards": parsed["t1_guards"],
            "alignment_hits": parsed["alignment_hits"],
            "data_class_equal_modulo_admitted_prose": parsed["data_class_equal_modulo_admitted_prose"],
            "genericity_equal": parsed["genericity_equal"],
        },
        "checks": checks,
        "controls": controls,
        "controls_passed": sum(1 for c in controls if c["passed"]),
        "controls_total": len(controls),
        "findings": findings,
        "verdict": verdict,
        "falsifier": ("At the pins in this report: (a) F2a clause (c) is shown to entail a smooth manifold category "
                      "(via a definition, taxonomy binding, or canonical convention note in the pinned artifacts); "
                      "(b) F2a clause (f) is shown to entail the interior-witness condition; (c) T1's guard set is "
                      "shown to include the extension-predicate convention axis; or (d) an explicit cross-class "
                      "predicate-alignment declaration is shown to exist in a pinned artifact. A later file write at "
                      "a new hash is not a falsifier; the new bytes must be measured and this instrument re-run."),
        "summary": ("%d contract FAIL / %d PASS / %d INFO; %d/%d controls; containment not entailed by the declared "
                    "clause pair; T1 guard gap recorded"
                    % (len(defects),
                       sum(1 for c in CONTRACT_CHECKS if checks[c]["status"] == "PASS"),
                       sum(1 for c, v in checks.items() if v["status"] == "INFO"),
                       sum(1 for c in controls if c["passed"]), len(controls))),
    })

    controls_path = args.controls_out or os.path.join(HERE, "controls", "control_results.json")
    os.makedirs(os.path.dirname(controls_path), exist_ok=True)
    write_report(controls_path, {"task_id": TASK_ID, "created_at": now_cst(), "controls": controls})
    base["controls_artifact"] = os.path.relpath(controls_path, ROOT)
    write_report(args.json_out, base)

    print(json.dumps({
        "status": base["status"],
        "defects": defects,
        "info": [c for c, v in checks.items() if v["status"] == "INFO"],
        "controls": "%d/%d" % (base["controls_passed"], base["controls_total"]),
        "report": os.path.relpath(args.json_out, ROOT),
    }, indent=1))

    if not controls_ok:
        return 3
    if not parse_ok:
        return 5
    if defects:
        return 1 if args.strict else 0
    return 4


if __name__ == "__main__":
    sys.exit(main())
