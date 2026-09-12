#!/usr/bin/env python3
"""W010-CBR-01: class-binding / coverage-matrix reconciliation audit (read-only).

Bounded task on the four frozen cosmic-censorship classes.  It reconciles three
artifacts at pinned hashes and classifies every ledger binding's content relation
to the class conclusion by deterministic phrase rules:

  (a) ledger/theorems.jsonl                 a1674f094979
  (b) ledger/class_coverage.csv             abbaee54a5a3
  (c) the four class contracts              cce9c60146d6 / 5476a3f2c6bc /
                                            55d0a1ea9bda / 0abb9ed8a961 (F0)

It does NOT re-adjudicate the ledger and does NOT repair it.  It reports where a
binding's own words are contrary to the class conclusion, where the coverage
matrix's grade label disagrees with the ledger's own conclusion_type, and where
cell counts are being used as if they were binding counts.

Outputs a JSON report to stdout (redirected by the caller); deterministic given
the snapshots.  Run:  python3 binding_reconcile_audit.py > report.json
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
SNAP = HERE / "snapshots"
REPORT_ID = "W010-CBR-01"

# --------------------------------------------------------------------------
# pinned inputs (sha256 measured 2026-09-12; snapshots frozen alongside)
# --------------------------------------------------------------------------
PINNED = {
    "ledger": ("snapshots/theorems.a1674f094979.jsonl",
               "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28"),
    "coverage": ("snapshots/class_coverage.abbaee54a5a3.csv",
                 "abbaee54a5a3c82b70a6b4e646edd29ff6d6daa3e2d82844296dfba8afc3a724"),
    # frozen at 00:53:39-00:59:33; the schema snapshots hold the rev13 bytes
    # (the file names keep the revision label they were copied under)
    "f1_wcc": ("snapshots/af_wcc_vacuum.d9cebb9404b2.yaml",
               "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d"),
    "f2a_c2": ("snapshots/af_scc_c2_vacuum.e9a27996dfd3.yaml",
               "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe"),
    "f2b_c0": ("snapshots/af_scc_c0_vacuum.b2ab6acb2bbe.yaml",
               "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"),
    "f0_taxonomy": ("snapshots/formulation_taxonomy.0abb9ed8a961.yaml",
                    "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"),
}

CLASSES = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
FAMILY = {"AF-WCC-VAC-GEN": "WCC", "AF-WCC-SCALAR-SPH": "WCC",
          "AF-SCC-C2-VAC-GEN": "SCC", "AF-SCC-C0-VAC-GEN": "SCC"}

# --------------------------------------------------------------------------
# contract every class is audited against (declared, then used mechanically)
# --------------------------------------------------------------------------
CONTRACT = {
    "AF-SCC-C0-VAC-GEN": {
        "statement": "generic AF vacuum data have an MGHD that is future-inextendible as a C0 Lorentzian manifold",
        "conclusion_type": "scc_c0_future_inextendibility",
        "contrary_axis": "extendibility at C0 (a continuous proper future extension exists, or a C0-extendible family is constructed)",
        "support_axis": "no proper future continuous extension exists (C0/C1/C2/H2_loc-inextendibility, spacelike-diameter obstructions)",
        "scope_requirements": ["comeager/residual genericity over AF vacuum data is part of the class"],
        "csv_cells": None,
    },
    "AF-SCC-C2-VAC-GEN": {
        "statement": "generic AF vacuum data have an MGHD that is future-inextendible as a C2 vacuum solution",
        "conclusion_type": "scc_c2_future_inextendibility",
        "contrary_axis": "extendibility at C2 or above (a C2/C-infinity proper future extension exists)",
        "support_axis": "no proper future C2 extension exists (C2-inextendibility or the stronger C0/H2_loc results)",
        "scope_requirements": ["comeager/residual genericity over AF vacuum data is part of the class"],
        "csv_cells": None,
    },
    "AF-WCC-VAC-GEN": {
        "statement": "generic AF vacuum data have a complete future null infinity and no singularity visible from I+",
        "conclusion_type": "weak_cosmic_censorship",
        "contrary_axis": "a naked singularity / incomplete I+ is exhibited, or the extendible set is non-meager in a fixed topology",
        "support_axis": "no visible singularity: I+ complete, trapped-surface plus completeness arguments, stability results",
        "scope_requirements": ["genericity notion in a named topology is part of the class"],
        "csv_cells": None,
    },
    "AF-WCC-SCALAR-SPH": {
        "statement": "in spherical symmetry with a massless scalar field, generic data have complete I+ and no visible singularity",
        "conclusion_type": "weak_cosmic_censorship",
        "contrary_axis": "a naked singularity / incomplete I+ is exhibited in the spherically symmetric scalar model, or the naked-singularity set is non-generic to generic",
        "support_axis": "instability of naked singularities, completeness of I+, no visible singularity in the scalar model",
        "scope_requirements": ["spherical symmetry and scalar matter are hypotheses, not choices"],
        "csv_cells": None,
    },
}

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
# Evidence forms.  Each form is an explicit, quoted pattern class.  The audit
# records which forms an entry's own ASSERTION text (label + statement_exact)
# carries; it does not decide the entry's mathematics:
#
#   EXT_ASSERT      the entry asserts that a C0/C2 extension EXISTS or that the
#                   development IS extendible -> negation-side of the SCC class
#   NAKED_EXIST     the entry asserts that a naked singularity EXISTS in a
#                   constructed family -> negation-side of the WCC class
#   INEXT_ASSERT    the entry asserts inexTendibility / no extension -> SCC side
#   COMPLETE_I      the entry asserts completeness of I+ or no visible singularity
#   STABILITY_OF    stability of the exterior/solution -> WCC side
# A form matched in a negated clause, or only in a does_not_imply / unresolved
# caveat, is reported separately and never counted as an assertion.
# --------------------------------------------------------------------------
ASSERT_FIELDS = ("label", "statement_exact")
CAVEAT_FIELDS = ("scope_caveats", "does_not_imply", "unresolved")
GENERIC_FIELD = "genericity"

FORMS = {
    "EXT_ASSERT": re.compile(
        r"\bmetric\s+extends\s+continuously\b"
        r"|\bcan\s+be\s+extended\s+across\b"
        r"|\bextended\s+across\s+(?:a|the|its)\b"
        r"|\bC\s*\^?0[-\s]?extendib(?:le|ility)\b"
        r"|\bC\s*\^?2[-\s]?extendib(?:le|ility)\b"
        r"|\badmits?\s+(?:a|an)\s+(?:proper\s+future\s+)?C\s*\^?[012]\s*(?:metric\s+)?extension\b"
        r"|\bcontinuous\s+(?:metric\s+)?extension\s+exists\b", re.I),
    "NAKED_EXIST": re.compile(
        r"\bform(?:s|ing)?\s+naked\s+singularit"
        r"|\bexist(?:ence|s|ing)?\b[^.]{0,80}?\bnaked\s+singularit"
        r"|\bnaked\s+singularit(?:y|ies)\b[^.]{0,40}?\b(?:exist|constructed|arise|form)\b", re.I),
    "INEXT_ASSERT": re.compile(r"\binextendib(?:le|ility)\b", re.I),
    "COMPLETE_I": re.compile(r"\bcomplete\s+future\s+null\s+infinity\b|\bI\+\s+(?:is\s+)?complete\b"
                             r"|\bno\s+(?:visible\s+)?singularity\s+is\s+visible\b", re.I),
    "STABILITY_OF": re.compile(r"\bstability\s+of\s+(?:the\s+)?(?:Kerr\s+)?(?:exterior|solution|spacetime|development)\b"
                               r"|\bsettle\s+down\b|\bglobal\s+nonlinear\s+stability\b", re.I),
}
NEG_CUE = re.compile(r"\bdoes\s+not\s+(?:prove|prove|imply|settle|establish|give|demand|cover|address|decide)\b"
                     r"|\bno\s+peer-reviewed\s+(?:theorem|result|proof)\b|\bnot\s+located\b|\bnot\s+found\b"
                     r"|\bnot\s+proved\b|\bneither\s+proves?\b|\bnor\s+does\b", re.I)
# forms on the negation-side of each family's conclusion
SCC_NEG_FORMS = {"EXT_ASSERT"}
WCC_NEG_FORMS = {"NAKED_EXIST"}
SCC_POS_FORMS = {"INEXT_ASSERT"}
WCC_POS_FORMS = {"COMPLETE_I", "STABILITY_OF"}


# role vocabulary in the coverage matrix and what it honestly can mean
ROLE_GRADES = {
    "theorem": "establishes",
    "supporting": "contributes",
    "supporting_conditional": "contributes_conditionally",
    "definition": "records_definition",
    "open_problem": "records_open_problem",
    "falsifier": "refutes_or_threatens",
    "numerical_evidence": "numerical_only",
}
# ledger conclusion_type -> what the entry actually establishes
CT_GRADE = {
    "theorem": "establishes",
    "conditional_theorem": "contributes_conditionally",
    "counterexample": "refutes_or_threatens",
    "stability_result": "contributes",
    "numerical_evidence": "numerical_only",
    "open_problem": "records_open_problem",
    "formal_model": "records_definition",
    "definition": "records_definition",
    "literature_status": "records_open_problem",
}
GRADE_RANK = {"records_definition": 0, "numerical_only": 1, "records_open_problem": 1,
              "contributes_conditional": 2, "contributes": 3, "establishes": 4,
              "refutes_or_threatens": 4}


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load() -> dict:
    loaded = {}
    for key, (rel, expected) in PINNED.items():
        p = HERE / rel
        actual = sha256(p)
        loaded[key] = {"path": rel, "expected_sha256": expected, "measured_sha256": actual,
                       "pin_match": actual == expected,
                       "bytes": p.stat().st_size}
    loaded["ledger_rows"] = [json.loads(l) for l in (HERE / PINNED["ledger"][0]).read_text().splitlines() if l.strip()]
    with (HERE / PINNED["coverage"][0]).open(newline="") as f:
        loaded["coverage_rows"] = list(csv.DictReader(f))
    return loaded


def split_pipe(s) -> list[str]:
    return [x.strip() for x in str(s or "").split("|") if x.strip()]


def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.;:!?])\s+|\n+", text) if s.strip()]


def _form_hits(text: str, form: str) -> list[dict]:
    """Form matches with a local negation flag (cue earlier in the same sentence)."""
    out = []
    for sent in _sentences(text):
        for m in FORMS[form].finditer(sent):
            prefix = sent[: m.start()]
            out.append({"form": form, "matched": m.group(0)[:80],
                        "sentence": sent.strip()[:220],
                        "negated_locally": bool(NEG_CUE.search(prefix))})
    return out


def _entry_scopes(e: dict) -> dict:
    """Assertion text vs caveat text, kept separate so a caveat cannot assert."""
    assertion = " \n ".join(str(e.get(k) or "") for k in ASSERT_FIELDS)
    caveat = " \n ".join(str(e.get(k) or "") for k in CAVEAT_FIELDS)
    return {"assertion": assertion, "caveat": caveat}


def classify_relation(entry: dict, cls: str) -> dict:
    """Direction of the entry's ASSERTION text relative to the class conclusion.

    Mechanical, form-based and conservative: an assertion match in a negated
    clause flips side; caveat-only matches are reported but do not set direction.
    For the SCC classes EXT_ASSERT is the negation-side and INEXT_ASSERT the
    conclusion-side; for C2, a C0-only extension assertion is recorded as a scope
    cue (C0-extendibility is weaker than C2-extendibility).  For WCC classes
    NAKED_EXIST is the negation-side; COMPLETE_I and STABILITY_OF are the
    conclusion-side.  direction is 'contrary', 'support', 'both', or 'neutral'.
    """
    scopes = _entry_scopes(entry)
    a_hits = {f: _form_hits(scopes["assertion"], f) for f in FORMS}
    c_hits = {f: _form_hits(scopes["caveat"], f) for f in FORMS}
    if FAMILY[cls] == "SCC":
        neg_forms, pos_forms = SCC_NEG_FORMS, SCC_POS_FORMS
    else:
        neg_forms, pos_forms = WCC_NEG_FORMS, WCC_POS_FORMS

    def side(forms, wanted):
        out = []
        for f in forms:
            for h in a_hits[f]:
                if f == "EXT_ASSERT" and cls == "AF-SCC-C2-VAC-GEN" and "C0" in h["matched"].upper():
                    continue  # scope cue, not the C2 contrary axis
                out.append(h)
        return out

    neg = [h for h in side(neg_forms, True) if not h["negated_locally"]]
    pos = [h for h in side(pos_forms, True) if not h["negated_locally"]]
    # a negated negation-side assertion is a conclusion-side assertion
    for h in side(neg_forms, True):
        if h["negated_locally"]:
            pos.append({**h, "form": "NEGATED_" + h["form"]})
    for h in side(pos_forms, True):
        if h["negated_locally"]:
            neg.append({**h, "form": "NEGATED_" + h["form"]})
    if neg and pos:
        direction = "both"
    elif neg:
        direction = "contrary"
    elif pos:
        direction = "support"
    else:
        direction = "neutral"
    return {
        "direction": direction,
        "assertion_forms": [h for f in FORMS for h in a_hits[f]],
        "negation_side_hits": neg,
        "conclusion_side_hits": pos,
        "caveat_form_hits": [h for f in FORMS for h in c_hits[f]],
    }


def main() -> int:
    data = load()
    ledger = {e["theorem_id"]: e for e in data["ledger_rows"]}
    cells = [r for r in data["coverage_rows"] if r["coverage"] in ("covered", "partial")]
    all_cells = data["coverage_rows"]

    # ---- A. pin check -----------------------------------------------------
    checks = []
    for key in PINNED:
        checks.append({"check": f"pin:{key}", "result": "pass" if data[key]["pin_match"] else "FAIL",
                       "measured_sha256": data[key]["measured_sha256"][:12]})

    # ---- B. entry-level bindings and their relations ----------------------
    bindings = []
    for tid, e in ledger.items():
        for cls in e.get("class_ids") or []:
            rel = classify_relation(e, cls)
            bindings.append({
                "theorem_id": tid,
                "class_id": cls,
                "conclusion_type": e.get("conclusion_type"),
                "entry_kind": e.get("entry_kind"),
                "evidence_level": e.get("evidence_level"),
                "content_status": e.get("content_status"),
                "direction": rel["direction"],
                "negation_side_hits": rel["negation_side_hits"],
                "conclusion_side_hits": rel["conclusion_side_hits"],
                "caveat_only_forms": [h for h in rel["caveat_form_hits"]
                                      if h["form"] not in {x["form"] for x in rel["assertion_forms"]}],
                "class_id_known": cls in CLASSES,
            })
    bindings.sort(key=lambda b: (b["class_id"], b["theorem_id"]))

    # ---- C. coverage cells vs ledger bindings -----------------------------
    by_src = defaultdict(list)
    for e in data["ledger_rows"]:
        for s in (e.get("source_ids") or []):
            by_src[s].append(e)
    cell_findings = []
    cell_grade_mismatch = []
    for r in cells:
        sid, cid = r["source_id"], r["class_id"]
        ents = [e for e in by_src.get(sid, []) if cid in (e.get("class_ids") or [])]
        cts = split_pipe(r.get("conclusion_types"))
        eks = split_pipe(r.get("entry_kinds"))
        role = r["role"].strip()
        role_grade = ROLE_GRADES.get(role, "unknown_role")
        max_rank = max((GRADE_RANK.get(CT_GRADE.get(ct, "records_open_problem"), 1) for ct in cts), default=0)
        role_rank = GRADE_RANK.get(role_grade, 0)
        if not ents:
            cell_findings.append({"row_id": r["row_id"], "source_id": sid, "class_id": cid,
                                  "finding": "cell has no ledger entry bound to that class"})
            continue
        if max_rank and role_rank > max_rank:
            cell_grade_mismatch.append({
                "row_id": r["row_id"], "source_id": sid, "class_id": cid,
                "coverage": r["coverage"], "role": role, "role_grade": role_grade,
                "ledger_conclusion_types": cts, "ledger_max_grade_rank": max_rank,
                "gap": role_rank - max_rank,
            })
        # direction of the cell against the class, using the entry relations
        rels = {classify_relation(e, cid)["direction"] for e in ents}
        if ({"contrary", "both"} & rels) and role_grade in ("establishes", "contributes"):
            cell_findings.append({
                "row_id": r["row_id"], "source_id": sid, "class_id": cid, "coverage": r["coverage"],
                "finding": "grade label asserts support while an entry bound to this cell is contrary to the class conclusion",
                "theorem_ids": [e["theorem_id"] for e in ents],
                "role": role,
            })

    # ---- D. coverage accounting: cells vs unique entries ------------------
    per_class = {}
    for cls in CLASSES:
        ent_ids = sorted(t for t, e in ledger.items() if cls in (e.get("class_ids") or []))
        cls_cells = [r for r in cells if r["class_id"] == cls]
        cls_all = [r for r in all_cells if r["class_id"] == cls]
        per_class[cls] = {
            "unique_bound_entries": len(ent_ids),
            "bound_entry_ids": ent_ids,
            "assessed_cells": len(cls_cells),
            "cells_total": len(cls_all),
            "cell_rows_by_coverage": dict(Counter(r["coverage"] for r in cls_all)),
            "cell_ids": [r["row_id"] for r in cls_cells],
            "cell_to_entry_ratio": round(len(cls_cells) / max(len(ent_ids), 1), 2),
        }

    # ---- E. per-entry summary of multi-class bindings ---------------------
    multi = []
    for tid, e in ledger.items():
        cls = e.get("class_ids") or []
        if len(cls) > 1:
            multi.append({"theorem_id": tid, "class_ids": cls,
                          "conclusion_type": e.get("conclusion_type"),
                          "directions": {c: classify_relation(e, c)["direction"] for c in cls}})

    # ---- F. direction findings --------------------------------------------
    direction_findings = []
    for b in bindings:
        if b["direction"] in ("contrary", "both"):
            csv_roles = sorted({r["role"].strip() for r in cells
                                if r["class_id"] == b["class_id"]
                                and b["theorem_id"] in split_pipe(r.get("theorem_ids"))})
            support_roles = sorted(r for r in csv_roles if ROLE_GRADES.get(r) in ("establishes", "contributes"))
            entry = ledger[b["theorem_id"]]
            caveat_text = " ".join(str(entry.get(k) or "") for k in CAVEAT_FIELDS)
            scope_scoped = bool(re.search(r"not\s+generic|non-generic|non\s+generic|not\s+a\s+generic|"
                                          r"does\s+not\s+prove|does\s+not\s+settle|does\s+not\s+imply|"
                                          r"conditional|interior", caveat_text, re.I))
            direction_findings.append({
                "theorem_id": b["theorem_id"], "class_id": b["class_id"],
                "ledger_conclusion_type": b["conclusion_type"],
                "direction": b["direction"],
                "negation_side_forms": [h["form"] for h in b["negation_side_hits"]],
                "matched_text": [h["matched"] for h in b["negation_side_hits"]],
                "matched_sentence": [h["sentence"] for h in b["negation_side_hits"]],
                "caveat_only_forms": b["caveat_only_forms"],
                "coverage_matrix_roles": csv_roles,
                "role_conflict": bool(support_roles),
                "self_disclaimed_in_caveats": scope_scoped,
                "finding": ("binding's own assertion text is the negation-side of the class conclusion"
                            + ("; the coverage matrix labels this cell support-grade" if support_roles else
                               "; the coverage matrix does not label it support-grade")
                            + ("; the entry's own caveats already scope it (non-generic/conditional/interior), "
                               "so this is a role-label reading question, not a hidden overclaim"
                               if scope_scoped else
                               "; the entry's caveats do NOT already scope the claim, so the role label "
                               "should be read before citing this cell as support")),
            })
    # extra: self-disclaimed class conclusion (does_not_imply names the class axis)
    disclaimers = []
    for tid, e in ledger.items():
        for c in (e.get("class_ids") or []):
            for d in (e.get("does_not_imply") or []):
                if re.search(r"C\^?0|C\^?2|SCC|WCC|generic", d, re.I):
                    disclaimers.append({"theorem_id": tid, "class_id": c, "does_not_imply": d})
                    break

    # ---- summary ----------------------------------------------------------
    summary = {
        "n_ledger_entries": len(ledger),
        "n_bound_entries": sum(1 for e in ledger.values() if e.get("class_ids")),
        "n_unbound_entries": sum(1 for e in ledger.values() if not e.get("class_ids")),
        "n_bindings": len(bindings),
        "n_bindings_unknown_class": sum(1 for b in bindings if not b["class_id_known"]),
        "n_bindings_contrary": sum(1 for b in bindings if b["direction"] == "contrary"),
        "n_bindings_contrary_or_both": len(direction_findings),
        "n_bindings_support": sum(1 for b in bindings if b["direction"] == "support"),
        "n_bindings_neutral": sum(1 for b in bindings if b["direction"] == "neutral"),
        "n_bindings_both": sum(1 for b in bindings if b["direction"] == "both"),
        "n_assessed_cells": len(cells),
        "n_cells_without_ledger_entry": len([f for f in cell_findings if f["finding"].startswith("cell has no")]),
        "n_cells_role_overgrade": len(cell_grade_mismatch),
        "n_cells_direction_conflict": len([f for f in cell_findings if "contrary" in f["finding"]]),
        "n_multi_class_entries": len(multi),
        "cell_to_entry_ratio_global": round(len(cells) / max(sum(1 for e in ledger.values() if e.get("class_ids")), 1), 2),
    }

    report = {
        "report_id": REPORT_ID,
        "task": "class-binding / coverage-matrix reconciliation at pinned hashes",
        "actor": "worker-010",
        "gate": "G-LIT",
        "node_id": "L1",
        "class_ids": CLASSES,
        "method": ("read-only reconciliation of ledger, coverage matrix and four class contracts; "
                   "content relation classified by declared phrase rules; no ledger or matrix edit"),
        "inputs": {k: data[k] for k in PINNED},
        "checks": checks,
        "class_contracts_used": {c: {"statement": CONTRACT[c]["statement"],
                                     "conclusion_type": CONTRACT[c]["conclusion_type"],
                                     "contrary_axis": CONTRACT[c]["contrary_axis"]} for c in CLASSES},
        "coverage_accounting_per_class": per_class,
        "bindings": bindings,
        "direction_findings": direction_findings,
        "cell_grade_mismatches": sorted(cell_grade_mismatch, key=lambda x: -x["gap"]),
        "cell_findings": cell_findings,
        "multi_class_entries": multi,
        "class_conclusion_disclaimers": disclaimers,
        "summary": summary,
        "limitations": [
            "token rules are deterministic but lexical: a negated token is flipped by a negation cue earlier in the same sentence, which fails on double negation or on cues in a previous sentence",
            "for WCC classes a naked-singularity *instability* theorem and a naked-singularity *existence* theorem both match the same token; the quoted sentence is the discriminator and must be read",
            "no ledger entry is re-adjudicated; conclusion_type/class_ids are inherited as written",
            "the coverage matrix role vocabulary is not defined in-repo; ROLE_GRADES is this audit's declared reading",
            "the C0-extendibility token is deliberately ignored for the C2 class (C0-extendibility is weaker than C2-extendibility, so it is a scope cue there, not the contrary axis)",
        ],
    }
    json.dump(report, __import__("sys").stdout, indent=1, sort_keys=False)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
