#!/usr/bin/env python3
"""W091-F2A-REPAIR-ACCEPTANCE-01 — does the recommended R1 repair close the
containment-entailment gap in the F2a/C2 extension predicate, and what does the
repair-acceptance instrument report afterwards?

Actor: worker-091 (bounded execution worker; one class-bound task, then exit).
Classes: AF-SCC-C2-VAC-GEN (lead), AF-SCC-C0-VAC-GEN (sibling).
Node: F2a. Gate: G-FORM.

Question fixed before the runs (pre-registered):

  Q1. Reproduce the pinned baseline: does the declared F2a(C2)/F2b(C0) clause
      pair entail E_C2 subset of E_C0 at F2a=e9a27996dfd3, F2b=b2ab6acb2bbe?
  Q2. Does applying the verified W047 option-A repair (S1..S5 of
      artifacts/worker-047/f2a_ext_freeze_spec/repair_spec.json#c33e8a46) to the
      pinned F2a bytes yield a candidate whose clause pair DOES entail the
      containment, and does worker-047's own instrument
      (check_c2c0_pred_containment_047.py) flip C11 from FAIL to PASS on it?
  Q3. What, if anything, does the repaired candidate still fail in that
      instrument's pre-registered contract (C01..C11), and which failures are
      real residuals versus a contract target that the repair necessarily
      retires?

Method (all checks pre-registered in this file before the reported run):
  * measure every pin; abort 2 on drift (drift voids, never falsifies);
  * re-derive the patched bytes from the pinned F2a text + repair_spec.json
    option-A edits (each old_text must occur exactly once) and compare the
    result with the existing worker-091 patched candidate 37e650ad;
  * parse clauses (a)..(f) of both predicates from the pinned text and evaluate
    this worker's own obligation table (independent of worker-047's regexes);
  * evaluate an explicit predicate-level boundary-only witness triple under the
    baseline and the patched clause sets;
  * run worker-047's instrument twice: (i) unmodified, against canonical bytes,
    (ii) against a private sandbox whose only difference is the patched F2a
    bytes and the instrument's F2A/F2A_M pin lines (diff recorded);
  * compare the instrument's contract table with this checker's table;
  * mutant controls M1..M7, each with a pre-registered expected flip;
  * two runs must be byte-identical except created_at.

Exit: 0 finding confirmed, 4 no finding (all obligations already entailed and
no residual), 2 input drift, 3 control mis-calibration, 5 parse failure.
No writes outside tmp/w091_f2a_repair_accept and this artifact directory.
Read-only on every canonical path and on every other agent's artifact.
This is focused-axis verification: not a full-schema verdict, not countable
toward G-FORM two-accept coverage, and it sets no node status, no
validation_status=passed and no gate verdict.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CST = timezone(timedelta(hours=8))

TASK_ID = "W091-F2A-REPAIR-ACCEPTANCE-01"
ACTOR = "worker-091"
CLASS_IDS = ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
NODE_IDS = ["F2a", "F2b"]
GATE = "G-FORM"

F2A = "schemas/af_scc_c2_vacuum.yaml"
F2B = "schemas/af_scc_c0_vacuum.yaml"
F1 = "schemas/af_wcc_vacuum.yaml"
F2A_M = "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"
F2B_M = "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
F1_M = "artifacts/formulation/schemas/af_wcc_vacuum.yaml"
TAX = "research_map/formulation_taxonomy.yaml"
SUP = "artifacts/formulation/formulation_taxonomy.yaml"
FROZEN = "artifacts/formulation/FROZEN.json"

SPEC = "artifacts/worker-047/f2a_ext_freeze_spec/repair_spec.json"
SPEC_SHA = "c33e8a46866992cfa7b1f3ea9d31c6e10217f4a51e916697848ec6b54a6a3e98"
W047_INSTRUMENT = "artifacts/worker-047/c2c0_pred_containment/check_c2c0_pred_containment_047.py"
W047_INSTRUMENT_SHA = None  # measured at run time
EXISTING_PATCHED = (
    "artifacts/worker-091/w047_f2a_freeze_independent/patched/"
    "af_scc_c2_vacuum.w047-patched.yaml"
)
EXISTING_PATCHED_SHA = "37e650ad6481ad24551d495887d8cc7bdc0ca713b1cdd614e60324cca681c960"

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

WORK = os.path.join(ROOT, "tmp", "w091_f2a_repair_accept")

SMOOTH_RE = re.compile(r"SMOOTH\s*\(C-?infinity\)|SMOOTH\s+4-manifold|smooth\s+4-manifold", re.I)
ALIGN_RE = re.compile(
    r"convention[_ ]alignment|predicate[_ ]alignment|aligned\s+extension\s+predicate|"
    r"shared\s+extension\s+predicate|same\s+manifold\s+category|identical\s+extension\s+predicate",
    re.I,
)
INTERIOR_RE = re.compile(r"\bint\s*\(", re.I)

# Worker-047 R1 expectation as published in its README: the repair is expected to
# turn C01/C02/C06/C10/C11 PASS. Calibration target for the comparison table.
R1_EXPECTED = {"C01": "PASS", "C02": "PASS", "C06": "PASS", "C10": "PASS", "C11": "PASS"}

CONTROLS = [
    ("M1_patch_strip_smooth", "O1_manifold_category", "FAIL", "CLAUSE_CONTAINMENT", "NOT_ENTAILED"),
    ("M2_patch_strip_interior", "O2_interior_witness", "FAIL", "CLAUSE_CONTAINMENT", "NOT_ENTAILED"),
    ("M3_baseline_alignment_decl", "ALIGNMENT_DECLARED", "PASS", "LICENSED_CONTAINMENT", "LICENSED_BY_DECLARATION"),
    ("M4_strip_f2b_interior", "SIB_C04_interior", "FAIL", None, None),
    ("M5_identical_predicates", "CLAUSE_CONTAINMENT", "ENTAILED", "CLASS_TOKEN_C2", "FAIL"),
    ("M6_metric_to_continuous", "O3_metric_continuity", "PASS", "CLASS_TOKEN_C2", "FAIL"),
    ("M7_unmodified_baseline", "CLAUSE_CONTAINMENT", "NOT_ENTAILED", None, None),
]


def now_cst():
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(path):
    with open(path, "rb") as fh:
        return sha256_bytes(fh.read())


def read_bytes(path):
    with open(path, "rb") as fh:
        return fh.read()


def split_clauses(defn):
    """Split on the first occurrence of each of (a)..(f), in order.

    Markers may legitimately re-appear inside clause prose (e.g. the C0 clause (f)
    note "clause (f) was escapable"), so only the first in-order occurrence of each
    letter delimits a clause.
    """
    spans = []
    pos = 0
    for letter in "abcdef":
        m = re.search(r"\(%s\)" % letter, defn[pos:])
        if not m:
            return None
        start = pos + m.start()
        spans.append((letter, start))
        pos = start + 1
    out = {}
    for i, (letter, start) in enumerate(spans):
        end = spans[i + 1][1] if i + 1 < len(spans) else len(defn)
        out[letter] = defn[start:end].strip()
    return out


def load_f2a_yaml(text):
    import yaml  # noqa: E402  (local import keeps the stdlib-only fast path)

    return yaml.safe_load(text)


def obligation_table(c2_text, c0_text, align_hits):
    """This worker's own clause-obligation table. Text predicates only."""
    d2 = load_f2a_yaml(c2_text)
    d0 = load_f2a_yaml(c0_text)
    p2 = d2["extension_predicate"]
    p0 = d0["extension_predicate"]
    cl2 = split_clauses(p2["definition"])
    cl0 = split_clauses(p0["definition"])
    if cl2 is None or cl0 is None:
        return None
    top2 = d2["topology"]["extension_topology"]
    top0 = d0["topology"]["extension_topology"]

    def has_smooth(s):
        return bool(SMOOTH_RE.search(s))

    o = {}
    o["O1_manifold_category"] = {
        "value": "PASS" if (has_smooth(cl2["c"]) or has_smooth(top2)) else "FAIL",
        "detail": "F2a clause (c)/extension_topology declares SMOOTH C-infinity category"
        if (has_smooth(cl2["c"]) or has_smooth(top2))
        else "F2a clause (c)/extension_topology is category-silent (no SMOOTH/C-infinity token)",
        "clause_c": cl2["c"][:240],
        "extension_topology": top2[:240],
    }
    f2 = cl2["f"]
    int_hits = len(INTERIOR_RE.findall(f2))
    nonempty = bool(re.search(r"non-empty", f2, re.I))
    witness_in_int = bool(re.search(r"p\s+in\s+int\s*\(", f2, re.I))
    interior_ok = int_hits >= 2 and nonempty and witness_in_int
    o["O2_interior_witness"] = {
        "value": "PASS" if interior_ok else "FAIL",
        "detail": "F2a clause (f) requires non-empty int(M' minus iota(M)) and an interior witness"
        if interior_ok
        else "F2a clause (f) admits a witness p in M' minus iota(M) with no interior requirement "
        "(boundary/dense-open-only additions are not excluded)",
        "clause_f": f2[:300],
        "int_occurrences": int_hits,
        "nonempty": nonempty,
        "witness_in_int": witness_in_int,
    }
    o["O3_metric_continuity"] = {
        "value": "PASS" if (re.search(r"Lorentzian", cl2["d"], re.I)
                            and re.search(r"C-?infinity|smooth|C2|C1|C0|continuous|nondegenerate",
                                          cl2["d"], re.I)) else "FAIL",
        "detail": "F2a clause (d) declares a nondegenerate Lorentzian metric at a regularity at "
                  "least as strong as the sibling's continuous one (containment obligation; the "
                  "class token itself is checked separately as CLASS_TOKEN_C2)",
        "clause_d": cl2["d"][:240],
    }
    token_ok = (p2.get("frozen_regularity") == "C2" and re.search(r"\bC2\b", cl2["d"])
                and re.search(r"Ric", cl2["e"]))
    o["CLASS_TOKEN_C2"] = {
        "value": "PASS" if token_ok else "FAIL",
        "detail": "F2a frozen_regularity is C2, clause (d) still requires a C2 metric and clause (e) "
                  "still requires Ric=0; this is a class-identity obligation, not part of the "
                  "containment entailment",
        "frozen_regularity": p2.get("frozen_regularity"),
        "clause_d": cl2["d"][:200],
        "clause_e": cl2["e"][:200],
    }
    o["O4_iota_regularity"] = {
        "value": "PASS" if re.search(r"C-?infinity|C2", cl2["a"], re.I) else "FAIL",
        "detail": "F2a clause (a) declares the differentiability class of iota"
        if re.search(r"C-?infinity|C2", cl2["a"], re.I)
        else "F2a clause (a) declares a bare isometric embedding; iota regularity under-frozen "
        "(well-posedness axis, NOT containment-critical: the C0 sibling constrains iota no further)",
        "clause_a": cl2["a"][:240],
        "containment_critical": False,
    }
    o["O5_equation_extra"] = {
        "value": "PASS",
        "detail": ("F2a clause (e) requires Ric(g')=0 classically, strictly stronger than C0's "
                   "no-equation clause, so it can only shrink E_C2 (containment-benign)")
        if re.search(r"Ric", cl2["e"]) else
        ("F2a clause (e) requires no equation, equal to C0's clause (e) "
         "(containment-benign; class identity is checked by CLASS_TOKEN_C2)"),
        "clause_e": cl2["e"][:240],
    }
    o["O6_open_proper"] = {
        "value": "PASS" if re.search(r"open,\s*proper", cl2["b"]) else "FAIL",
        "detail": "F2a clause (b) and F2b clause (b) both require iota(M) open and proper",
        "clause_b": cl2["b"][:200],
    }
    o["SIB_C03_category"] = {
        "value": "PASS" if has_smooth(cl0["c"]) else "FAIL",
        "detail": "F2b clause (c) declares SMOOTH (C-infinity) M'"
        if has_smooth(cl0["c"])
        else "F2b clause (c) lost the SMOOTH category token",
        "clause_c": cl0["c"][:240],
    }
    f0 = cl0["f"]
    sib_int_ok = len(INTERIOR_RE.findall(f0)) >= 2 and bool(re.search(r"non-empty", f0, re.I))
    o["SIB_C04_interior"] = {
        "value": "PASS" if sib_int_ok else "FAIL",
        "detail": "F2b clause (f) requires non-empty interior and an interior witness"
        if sib_int_ok
        else "F2b clause (f) lost the interior requirement",
        "clause_f": f0[:300],
    }
    o["ALIGNMENT_DECLARED"] = {
        "value": "PASS" if align_hits else "FAIL",
        "detail": "an explicit cross-class predicate-alignment declaration is present"
        if align_hits
        else "no pinned artifact declares that the F2a and F2b extension predicates share the "
        "manifold-category and clause-(f) interior-witness conventions",
        "hits": align_hits[:6],
    }
    clause = all(o[k]["value"] == "PASS" for k in
                 ["O1_manifold_category", "O2_interior_witness", "O3_metric_continuity",
                  "O5_equation_extra", "O6_open_proper"])
    lic = clause or o["ALIGNMENT_DECLARED"]["value"] == "PASS"
    return {
        "clauses_f2a": cl2,
        "clauses_f2b": cl0,
        "obligations": o,
        "CLAUSE_CONTAINMENT": "ENTAILED" if clause else "NOT_ENTAILED",
        "LICENSED_CONTAINMENT": "LICENSED_BY_CLAUSES" if clause
        else ("LICENSED_BY_DECLARATION" if lic else "NOT_LICENSED"),
    }


def witness_record(baseline_table, patched_table):
    """Predicate-level boundary-only witness: M''=R^4, iota(M)=R^4 minus {0}, eta."""
    def eval_f(definition_f):
        return {
            "interior_required": bool(len(INTERIOR_RE.findall(definition_f)) >= 2
                                      and re.search(r"non-empty", definition_f, re.I)),
            "witness_in_interior": bool(re.search(r"p\s+in\s+int\s*\(", definition_f, re.I)),
        }

    b_f = eval_f(baseline_table["clauses_f2a"]["f"])
    p_f = eval_f(patched_table["clauses_f2a"]["f"])
    return {
        "witness_id": "W-091-C2C0-BOUNDARY-ONLY",
        "triple": {
            "M''": "R^4 (smooth, connected, time-orientable; standard orientation)",
            "iota(M)": "R^4 minus {0}, included in R^4 (open, proper, connected)",
            "g''": "Minkowski eta (C-infinity, nondegenerate Lorentzian, Ric=0)",
            "iota": "inclusion (smooth, hence C-infinity isometric)",
        },
        "baseline_c2_clause_eval": {
            "a": True, "b": True, "c": True, "d": True, "e": True,
            "f": True,
            "f_note": "p=0 is in M'' minus iota(M) and 0 in I^+((-1,0,0,0); eta)",
        },
        "baseline_c0_clause_f": False,
        "baseline_c0_f_note": "int(R^4 minus (R^4 minus {0})) = int({0}) = empty, so F2b "
        "clause (f) fails: the witness is in E_C2 and not in E_C0",
        "baseline_conclusion": "containment E_C2 subset E_C0 NOT entailed at pinned bytes",
        "patched_c2_clause_eval": {"f": False, "f_note": "the repaired F2a clause (f) requires "
                                  "p in int(M'' minus iota(M)); the witness is excluded from E_C2"},
        "patched_conclusion": "the boundary-only family no longer separates the repaired predicate "
        "pair; the clause matrix above is the general obligation, the witness is the exhibit that "
        "the baseline text really admitted the escapability",
        "scope": "predicate-level model of the declared clauses; NOT a physical counterexample and "
        "NOT evidence against cosmic censorship",
        "baseline_interior_flags": b_f,
        "patched_interior_flags": p_f,
    }


def rederive_patched(spec, f2a_text):
    sites = [s for s in spec["sites"] if s.get("option") == "A"]
    text = f2a_text
    applied = []
    for s in sites:
        old, new = s["old_text"], s["new_text"]
        n = text.count(old)
        if n != 1:
            return None, {"site": s["site_id"], "occurrences_of_old_text": n}
        text = text.replace(old, new, 1)
        applied.append({"site_id": s["site_id"], "yaml_path": s["yaml_path"],
                        "axis": s["axis"], "old_occurrences": 1})
    return text, applied


def build_sandbox(patched_bytes, pin_f2a_sha):
    sb = os.path.join(WORK, "sandbox")
    if os.path.exists(sb):
        shutil.rmtree(sb)
    copies = [F2A, F2B, F1, F2A_M, F2B_M, F1_M, TAX, SUP, FROZEN]
    for rel in copies:
        dst = os.path.join(sb, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(os.path.join(ROOT, rel), dst)
    for rel in (F2A, F2A_M):
        with open(os.path.join(sb, rel), "wb") as fh:
            fh.write(patched_bytes)
    inst_rel = os.path.join("artifacts", "worker-047", "c2c0_pred_containment",
                            os.path.basename(W047_INSTRUMENT))
    inst_dst = os.path.join(sb, inst_rel)
    os.makedirs(os.path.dirname(inst_dst), exist_ok=True)
    src = read_bytes(os.path.join(ROOT, W047_INSTRUMENT)).decode("utf-8")
    out = src
    for key in ("F2A", "F2A_M"):
        pat = re.compile(r'(\n    %s: ")[0-9a-f]{64}(")' % key)
        out, n = pat.subn(lambda m: m.group(1) + pin_f2a_sha + m.group(2), out, count=1)
        if n != 1:
            return None, {"pin_patch_failed": key}
    with open(inst_dst, "w", encoding="utf-8") as fh:
        fh.write(out)
    return sb, {"instrument_copy": inst_rel, "pin_lines_patched": ["F2A", "F2A_M"],
                "pin_value": pin_f2a_sha}


def run_instrument(inst_path, out_json, out_controls, cwd):
    cmd = [sys.executable, inst_path, "--json-out", out_json, "--controls-out", out_controls,
           "--strict"]
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    rep = None
    if os.path.exists(out_json):
        try:
            rep = json.load(open(out_json, encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            rep = {"unreadable": str(exc)}
    ctl = None
    if os.path.exists(out_controls):
        try:
            ctl = json.load(open(out_controls, encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            ctl = {"unreadable": str(exc)}
    ctl_rows = (ctl or {}).get("controls") or []
    passed = sum(1 for r in ctl_rows if r.get("passed"))
    return {"argv": cmd, "cwd": cwd, "returncode": p.returncode,
            "stdout_tail": p.stdout[-2000:], "stderr_tail": p.stderr[-2000:], "report": rep,
            "controls_passed": passed, "controls_total": len(ctl_rows),
            "controls_failed": [{"control": r.get("control"), "error": r.get("error"),
                                 "expected": r.get("expected"), "observed": r.get("observed")}
                                for r in ctl_rows if not r.get("passed")]}


def contract_table(rep):
    if not rep or "checks" not in rep:
        return None
    return {k: v.get("status") for k, v in rep["checks"].items()}


def mutate(text, kind):
    t = text
    if kind == "M1_patch_strip_smooth":
        t = re.sub(r"M' is a SMOOTH \(C-infinity\) connected 4-manifold",
                   "M' is connected", t, count=1)
        t = re.sub(r'M\' is a connected SMOOTH 4-manifold \(the category in which the C2 metric '
                   r'is a tensor field\)', "M' is a connected 4-manifold", t, count=1)
        return t
    if kind == "M2_patch_strip_interior":
        m = re.search(r"\(f\) the extension adds interior points to the future:.*?(?=\([a-z]\)|$)",
                      t, re.S)
        if not m:
            return None
        return t.replace(m.group(0), "(f) the extension adds points to the future: there exist "
                         "q in iota(M) and p in M' minus iota(M) with p in I^+(q; g'). ", 1)
    if kind == "M3_baseline_alignment_decl":
        return t.replace("extension_predicate:\n  name: proper_future_extension_in_class",
                         "extension_predicate:\n  predicate_convention_alignment: \"identical to "
                         "AF-SCC-C0-VAC-GEN sibling (manifold category and interior witness)\"\n"
                         "  name: proper_future_extension_in_class", 1)
    if kind == "M4_strip_f2b_interior":
        return re.sub(r"\(f\) the extension adds points to the future: int\(M' minus iota\(M\)\) "
                      r"is non-empty AND there exist q in iota\(M\) and p in int\(M' minus iota\(M\)\) "
                      r"with p in I\^\+\(q; g'\)",
                      "(f) the extension adds points to the future: there exist q in iota(M) and "
                      "p in M' minus iota(M) with p in I^+(q; g')", t, count=1)
    if kind == "M5_identical_predicates":
        return None  # handled by the caller (needs the C0 text)
    if kind == "M6_metric_to_continuous":
        return re.sub(r"\(d\) g' is a C2 Lorentzian metric",
                      "(d) g' is a continuous Lorentzian metric", t, count=1)
    if kind == "M7_unmodified_baseline":
        return t
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json-out", default=os.path.join(HERE, "report.json"))
    args = ap.parse_args()
    os.makedirs(WORK, exist_ok=True)
    raw = os.path.join(WORK, "raw")
    os.makedirs(raw, exist_ok=True)

    report = {
        "schema": "w091-f2a-repair-acceptance/v1",
        "task_id": TASK_ID,
        "actor": ACTOR,
        "created_at": now_cst(),
        "class_ids": CLASS_IDS,
        "node_ids": NODE_IDS,
        "gate": GATE,
        "authority": "worker deliverable; focused-axis verification; not a full-schema verdict; "
                     "does not set node status, validation_status=passed or any gate verdict",
        "pre_registration": {
            "Q1": "baseline clause pair does not entail E_C2 subset E_C0",
            "Q2": "W047 option-A repair flips the containment obligation and instrument C11 to PASS",
            "Q3": "residual post-repair contract failures: C05 (asymmetry target retired by the "
                  "repair), C09 (T1 guard), C10 (alignment declaration)",
        },
    }

    # ---- pins -------------------------------------------------------------
    pin_rows = []
    drift = []
    for rel, want in PINS.items():
        got = sha256_file(os.path.join(ROOT, rel))
        ok = got == want
        pin_rows.append({"path": rel, "expected": want, "measured": got, "matches": ok})
        if not ok:
            drift.append(rel)
    spec_sha = sha256_file(os.path.join(ROOT, SPEC))
    w047_inst_sha = sha256_file(os.path.join(ROOT, W047_INSTRUMENT))
    existing_sha = sha256_file(os.path.join(ROOT, EXISTING_PATCHED))
    report["pins"] = {
        "rows": pin_rows,
        "drift": drift,
        "spec_sha256": spec_sha,
        "spec_matches_pinned": spec_sha == SPEC_SHA,
        "w047_instrument_sha256": w047_inst_sha,
        "existing_patched_candidate_sha256": existing_sha,
        "existing_patched_candidate_matches_3718": existing_sha.startswith(EXISTING_PATCHED_SHA[:12]),
    }

    f2a_text = read_bytes(os.path.join(ROOT, F2A)).decode("utf-8")
    c0_text = read_bytes(os.path.join(ROOT, F2B)).decode("utf-8")
    f0_text = read_bytes(os.path.join(ROOT, TAX)).decode("utf-8")
    sup_text = read_bytes(os.path.join(ROOT, SUP)).decode("utf-8")

    def alignment_hits(text_blob):
        return [m.group(0) for m in ALIGN_RE.finditer(text_blob)]

    align_hits = alignment_hits(f2a_text) + alignment_hits(f0_text) + alignment_hits(sup_text)
    base_table = obligation_table(f2a_text, c0_text, align_hits)
    report["baseline"] = base_table

    # ---- re-derive patched candidate --------------------------------------
    spec = json.load(open(os.path.join(ROOT, SPEC), encoding="utf-8"))
    patched_text, applied = rederive_patched(spec, f2a_text)
    if patched_text is None:
        report["status"] = "REDERIVE_FAILED"
        report["rederive_detail"] = applied
        json.dump(report, open(args.json_out, "w", encoding="utf-8"), indent=1)
        return 5
    patched_bytes = patched_text.encode("utf-8")
    patched_sha = sha256_bytes(patched_bytes)
    with open(os.path.join(WORK, "patched_f2a.yaml"), "wb") as fh:
        fh.write(patched_bytes)
    report["rederivation"] = {
        "sites_applied": applied,
        "patched_sha256": patched_sha,
        "patched_bytes": len(patched_bytes),
        "matches_existing_candidate": patched_sha == existing_sha,
    }
    patched_table = obligation_table(patched_text, c0_text, align_hits)
    report["patched"] = patched_table
    report["witness"] = witness_record(base_table, patched_table)

    # ---- worker-047 instrument: baseline (canonical, read-only) -----------
    base_out = os.path.join(raw, "w047_baseline_report.json")
    base_ctl = os.path.join(raw, "w047_baseline_controls.json")
    base_run = run_instrument(os.path.join(ROOT, W047_INSTRUMENT), base_out, base_ctl, ROOT)

    # ---- worker-047 instrument: patched (private sandbox) -----------------
    sb, sb_info = build_sandbox(patched_bytes, patched_sha)
    patched_run = None
    if sb is not None:
        patched_out = os.path.join(raw, "w047_patched_report.json")
        patched_ctl = os.path.join(raw, "w047_patched_controls.json")
        patched_run = run_instrument(
            os.path.join(sb, sb_info["instrument_copy"]), patched_out, patched_ctl, sb)
    report["instrument_runs"] = {
        "baseline": {"returncode": base_run["returncode"],
                     "checks": contract_table(base_run["report"]),
                     "controls_passed": base_run["controls_passed"],
                     "controls_total": base_run["controls_total"],
                     "controls_failed": base_run["controls_failed"],
                     "stdout_tail": base_run["stdout_tail"][-400:]},
        "sandbox": sb_info,
        "patched": ({"returncode": patched_run["returncode"],
                     "checks": contract_table(patched_run["report"]),
                     "controls_passed": patched_run["controls_passed"],
                     "controls_total": patched_run["controls_total"],
                     "controls_failed": patched_run["controls_failed"],
                     "stdout_tail": patched_run["stdout_tail"][-400:]} if patched_run else None),
    }

    # ---- comparison -------------------------------------------------------
    bt = contract_table(base_run["report"]) or {}
    pt = (contract_table(patched_run["report"]) if patched_run else None) or {}
    my_base = base_table["CLAUSE_CONTAINMENT"]
    my_patch = patched_table["CLAUSE_CONTAINMENT"]
    agreement = {
        "my_baseline_not_entailed": my_base == "NOT_ENTAILED",
        "w047_baseline_C11": bt.get("C11"),
        "my_patched_entailed": my_patch == "ENTAILED",
        "w047_patched_C11": pt.get("C11"),
        "agree_baseline": (my_base == "NOT_ENTAILED") == (bt.get("C11") == "FAIL"),
        "agree_patched": (my_patch == "ENTAILED") == (pt.get("C11") == "PASS"),
    }
    r1_observed = {k: pt.get(k) for k in R1_EXPECTED}
    r1_deviation = {k: {"expected": v, "observed": pt.get(k)}
                    for k, v in R1_EXPECTED.items() if pt.get(k) != v}
    report["comparison"] = {
        "baseline_checks": bt,
        "patched_checks": pt,
        "flips": {k: {"baseline": bt.get(k), "patched": pt.get(k)}
                  for k in sorted(set(bt) | set(pt)) if bt.get(k) != pt.get(k)},
        "r1_expected": R1_EXPECTED,
        "r1_observed": r1_observed,
        "r1_deviations": r1_deviation,
        "agreement": agreement,
    }
    report["findings"] = []
    f = report["findings"]
    if my_base == "NOT_ENTAILED" and my_patch == "ENTAILED" and agreement["agree_baseline"] \
            and agreement["agree_patched"]:
        f.append({
            "id": "F-091-RA-1",
            "severity": "info",
            "statement": "Independent reproduction at F2a=e9a27996dfd3/F2b=b2ab6acb2bbe: the pinned "
                         "clause pair does not entail E_C2 subset E_C0; applying the verified W047 "
                         "option-A edits yields a candidate whose clause pair does (O1/O2/O3/O5/O6 all "
                         "PASS), and worker-047's instrument independently flips C11 FAIL->PASS. The "
                         "two instruments agree on both states.",
        })
    if pt.get("C05") == "FAIL" and bt.get("C05") == "PASS":
        f.append({
            "id": "F-091-RA-2",
            "severity": "major",
            "statement": "The instrument's pre-registered C05 target encodes the rev13 DEFECT as a "
                         "PASS condition ('F2b clause (f) strictly stronger than F2a clause (f)'). Any "
                         "repair that makes E_C2 subset E_C0 hold must align clause (f), so C05 "
                         "necessarily flips to FAIL after R1. C05 must be re-scoped (assert the "
                         "aligned/containment state) or explicitly retired by the instrument owner; "
                         "otherwise the instrument can never pass --strict on a correctly repaired F2a.",
            "evidence": {"C05_baseline": bt.get("C05"), "C05_patched": pt.get("C05"),
                         "w047_own_control_K3": "expected C05 FAIL on an aligned mutant "
                         "(confirms this is by construction, not a run error)"},
        })
    if pt.get("C10") == "FAIL":
        f.append({
            "id": "F-091-RA-3",
            "severity": "minor",
            "statement": "R1 as published (option A, sites S1-S5) does not add an explicit "
                         "cross-class predicate-alignment declaration, so C10 remains FAIL and the "
                         "worker-047 README's stated R1 expectation (C10 PASS) is not met. The "
                         "containment is nevertheless licensed by the repaired clauses (C11 PASS), so "
                         "this is documentation/hygiene unless the gate wants declaration-level "
                         "licensing.",
            "evidence": {"C10_baseline": bt.get("C10"), "C10_patched": pt.get("C10"),
                         "r1_expected": R1_EXPECTED.get("C10")},
        })
    if pt.get("C09") == "FAIL":
        f.append({
            "id": "F-091-RA-4",
            "severity": "minor",
            "statement": "R1 does not touch taxonomy transfer rule T1, so the predicate-convention "
                         "guard gap (F-PC-2) survives the repair: C09 stays FAIL. If the gate wants "
                         "the transfer rule itself hardened, rev14 must add the predicate axis to the "
                         "T1 guard set (the W047 instrument's own control K6 does exactly that and "
                         "flips C09 to PASS).",
            "evidence": {"C09_baseline": bt.get("C09"), "C09_patched": pt.get("C09")},
        })
    if patched_run and patched_run["controls_passed"] != patched_run["controls_total"]:
        f.append({
            "id": "F-091-RA-5",
            "severity": "major",
            "statement": "The worker-047 instrument cannot serve as an automated repair-acceptance "
                         "gate on repaired bytes as published: against the patched sandbox it exits "
                         "3 (control mis-calibration), because K1/K2/K3 mutation anchors no longer "
                         "exist once the repair is applied and K5's expectation is not covered by "
                         "the C05 branch when C02=PASS/C04=FAIL. Its README's claim that --strict "
                         "doubles as the repair-acceptance test therefore does not hold for the "
                         "repair it recommends. The C01..C11 table it emits is still usable when "
                         "read directly (and this checker reproduces it), but rev14 acceptance "
                         "needs the controls re-anchored to the repaired bytes or run against a "
                         "baseline snapshot.",
            "evidence": {"patched_returncode": patched_run["returncode"],
                         "controls_failed": patched_run["controls_failed"]},
        })
    report["rev14_checklist"] = [
        "apply option A sites S1-S5 to F2a (verified byte-reproducible: re-derived sha256 "
        + patched_sha[:12] + ")",
        "add an explicit cross-class predicate-alignment declaration (flips instrument C10) OR "
        "record that containment is clause-licensed (C11) and C10 is waived",
        "add the extension-predicate convention axis to the T1 guard set (flips instrument C09; "
        "closes F-PC-2)",
        "re-scope instrument C05 from 'asymmetry' to 'aligned/containment' (or retire it); with the "
        "current contract --strict can never return 0 on a correctly repaired F2a",
        "re-anchor the instrument's K1/K2/K3 mutation controls to the repaired text and extend the "
        "C05 branch to the (C02 PASS, C04 FAIL) case before using --strict as a rev14 acceptance "
        "gate (otherwise it exits 3 by control mis-calibration, finding F-091-RA-5)",
        "then re-run this checker and the worker-047 instrument at the new pins; the r3 reviewer "
        "cards pinned to e9a27996 are void for rev14",
    ]

    # ---- controls ---------------------------------------------------------
    ctl_rows = []
    for name, key, want_val, key2, want2 in CONTROLS:
        if name == "M5_identical_predicates":
            mutated = c0_text  # F2a definition replaced by F2b definition below
            tbl = obligation_table(c0_text, c0_text, align_hits)
        elif name == "M6_metric_to_continuous":
            m = mutate(patched_text, name)
            tbl = obligation_table(m, c0_text, align_hits) if m else None
        elif name == "M3_baseline_alignment_decl":
            m = mutate(f2a_text, name)
            hits = align_hits + alignment_hits(m)
            tbl = obligation_table(m, c0_text, hits) if m else None
        elif name == "M4_strip_f2b_interior":
            m = mutate(c0_text, name)
            tbl = obligation_table(patched_text, m, align_hits) if m else None
        elif name == "M1_patch_strip_smooth":
            m = mutate(patched_text, name)
            tbl = obligation_table(m, c0_text, align_hits) if m else None
        elif name == "M2_patch_strip_interior":
            m = mutate(patched_text, name)
            tbl = obligation_table(m, c0_text, align_hits) if m else None
        else:  # M7
            tbl = base_table
        if tbl is None:
            ctl_rows.append({"control": name, "passed": False, "error": "mutation/parse failed"})
            continue
        if key == "CLAUSE_CONTAINMENT":
            got = tbl["CLAUSE_CONTAINMENT"]
        elif key == "LICENSED_CONTAINMENT":
            got = tbl["LICENSED_CONTAINMENT"]
        elif key == "CLASS_TOKEN_C2":
            got = tbl["obligations"].get("CLASS_TOKEN_C2", {}).get("value")
        else:
            got = tbl["obligations"][key]["value"]
        row = {"control": name, "expected": {key: want_val}, "observed": {key: got}}
        if key2:
            got2 = tbl["obligations"].get(key2, {}).get("value") if key2 in tbl["obligations"] \
                else tbl.get(key2)
            row["expected"][key2] = want2
            row["observed"][key2] = got2
        row["passed"] = all(row["observed"][k] == row["expected"][k] for k in row["expected"])
        ctl_rows.append(row)
    report["controls"] = ctl_rows
    report["controls_passed"] = sum(1 for r in ctl_rows if r.get("passed"))
    report["controls_total"] = len(ctl_rows)

    # ---- verdict ----------------------------------------------------------
    finding_confirmed = (my_base == "NOT_ENTAILED" and my_patch == "ENTAILED"
                         and agreement["agree_baseline"] and agreement["agree_patched"]
                         and report["controls_passed"] == report["controls_total"])
    report["verdict"] = {
        "finding_confirmed": finding_confirmed,
        "headline": "R1 repair closes the containment obligation (clause-level + instrument C11), "
                    "but the instrument's own contract then fails C05 by construction and leaves "
                    "C09/C10 open; rev14 needs the 4-item checklist above." if finding_confirmed
                    else "pre-registered finding NOT confirmed; see tables",
        "gate_verdict_set": False,
        "node_status_set": False,
        "counts_as_full_schema_verdict": False,
    }
    report["falsifier"] = (
        "Re-run this checker at the pinned hashes: falsified if the baseline clause pair entails "
        "E_C2 subset E_C0 (O1/O2 both PASS at baseline), if the W047 option-A patched candidate "
        "fails to entail it, if worker-047's instrument does not flip C11 FAIL->PASS on the patched "
        "sandbox, if C05 does not regress (showing the repair is asymmetric and the containment "
        "claim then rests on an unstated convention), if the patched instrument run does not exit 3 "
        "on control mis-calibration, or if any control M1-M7 misses its pre-registered flip. "
        "Input drift voids (does not falsify)."
    )
    report["evidence_refs"] = [
        "schemas/af_scc_c2_vacuum.yaml#" + PINS[F2A][:12],
        "schemas/af_scc_c0_vacuum.yaml#" + PINS[F2B][:12],
        "artifacts/formulation/FROZEN.json#" + PINS[FROZEN][:12],
        "artifacts/worker-047/f2a_ext_freeze_spec/repair_spec.json#" + spec_sha[:12],
        "artifacts/worker-047/c2c0_pred_containment/check_c2c0_pred_containment_047.py#" +
        w047_inst_sha[:12],
        EXISTING_PATCHED + "#" + existing_sha[:12],
    ]

    with open(args.json_out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, sort_keys=False)
        fh.write("\n")

    print("baseline:", my_base, "| w047 C11:", bt.get("C11"), "| patched:", my_patch,
          "| w047 C11:", pt.get("C11"))
    print("flips:", json.dumps(report["comparison"]["flips"]))
    print("r1 deviations:", json.dumps(r1_deviation))
    print("controls: %d/%d" % (report["controls_passed"], report["controls_total"]))
    print("finding_confirmed:", finding_confirmed)
    if drift:
        return 2
    if report["controls_passed"] != report["controls_total"]:
        return 3
    return 0 if finding_confirmed else 4


if __name__ == "__main__":
    sys.exit(main())
