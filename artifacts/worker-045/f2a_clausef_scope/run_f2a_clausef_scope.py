#!/usr/bin/env python3
"""W045-F2A-CLAUSEF-SCOPE-01 -- deterministic, read-only disposition of the F2a
clause-(f) interior-requirement gap after the rev14 landing.

Node F2a, class AF-SCC-C2-VAC-GEN, gate G-FORM.

Question
--------
r3 (reviews/G-FORM-final-verify-r3.json, pin d94dd2d5b778) requires, before a G-FORM
proposal for F2a: "a revision freezing manifold category and iota regularity, propagating
the clause-(f) interior requirement, and byte-binding taxonomy_consistency.json".
The rev14 authorization (astra-life08-formulation-rev14) enumerates exactly seven items and
its own falsifier voids any byte move outside them. rev14 landed at 01:25:42 with items 1-3.

This instrument measures, at the live bytes:
  1. whether F2a clause (f) carries the interior requirement ('int(M' minus iota(M)) is
     non-empty AND p in int(...)') that its C0 sibling F2b carries;
  2. whether the rev14 revision-history note for F2a claims the clause-(f) repair;
  3. whether the rev14 authorization contains that repair inside its enumerated scope;
  4. whether r3 names it as required before a G-FORM proposal;
  5. whether the R2 repair reason is regularity-independent, by finite-topology models of
     boundary-only and dense-open-complement additions (empty interior) vs a genuine
     interior addition.

Read-only: no canonical, frozen, ledger or numerics file is written. No gate or node
verdict is claimed. Output: report.json + controls.json next to this script.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from itertools import combinations
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # artifacts/worker-045/f2a_clausef_scope -> repo root

F2A = ROOT / "schemas" / "af_scc_c2_vacuum.yaml"
F2B = ROOT / "schemas" / "af_scc_c0_vacuum.yaml"
FROZEN = ROOT / "artifacts" / "formulation" / "FROZEN.json"
R3 = ROOT / "reviews" / "G-FORM-final-verify-r3.json"
MAP = ROOT / "research_map" / "research_map.json"
REV091 = ROOT / "reviews" / "F2a-review-rev29-b.json"

TASK_ID = "W045-F2A-CLAUSEF-SCOPE-01"
ACTOR = "worker-045"
CLASS_ID = "AF-SCC-C2-VAC-GEN"
NODE_ID = "F2a"
GATE = "G-FORM"

CLAUSE_RE = re.compile(r"(?m)^[ \t]*\(f\)[ \t]+the extension adds points to the future:(.*)$")
INTERIOR_TOKEN = "int(M' minus iota(M))"
R2_CLAIM_TOKEN = "clause (f) interior+chronological"
REV14_SCOPE_TOKEN = "clause (f)"
R3_REQUIRED_TOKEN = "propagating the clause-(f) interior requirement"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def line_of(text: str, needle: str) -> int | None:
    for i, line in enumerate(text.splitlines(), 1):
        if needle in line:
            return i
    return None


# --------------------------------------------------------------------------------------
# Finite-topology models (Alexandrov-style, computed exactly)
# --------------------------------------------------------------------------------------

def opens_of(basis: list[frozenset]) -> list[frozenset]:
    """All unions of basis elements (basis assumed non-empty and intersection-closed)."""
    out: set[frozenset] = set()
    n = len(basis)
    for r in range(n + 1):
        for combo in combinations(basis, r):
            u: frozenset = frozenset()
            for b in combo:
                u = u | b
            out.add(u)
    return sorted(out, key=lambda s: (len(s), sorted(s)))


def interior(universe: frozenset, opens: list[frozenset], s: frozenset) -> frozenset:
    acc: frozenset = frozenset()
    for o in opens:
        if o <= s:
            acc = acc | o
    return acc


def is_open(opens: list[frozenset], s: frozenset) -> bool:
    return s in opens


def is_connected(universe: frozenset, opens: list[frozenset]) -> bool:
    """No separation into two disjoint non-empty open sets."""
    nonempty = [o for o in opens if o and o != universe]
    for o in nonempty:
        comp = universe - o
        if comp in opens and comp:
            return False
    return True


def basis_closed_under_intersection(basis: list[frozenset]) -> bool:
    for a, b in combinations(basis, 2):
        if (a & b) not in basis:
            return False
    return True


def clause_uninteriored(mprim: frozenset, iota_m: frozenset, iplus: set[tuple]) -> bool:
    outside = mprim - iota_m
    return any(q in iota_m and p in outside for (q, p) in iplus)


def clause_interiored(mprim: frozenset, iota_m: frozenset, iplus: set[tuple],
                      opens: list[frozenset]) -> bool:
    comp = mprim - iota_m
    inner = interior(mprim, opens, comp)
    if not inner:
        return False
    return any(q in iota_m and p in inner for (q, p) in iplus)


def run_models() -> dict:
    """Three point-set models of the clause-(f) distinction.

    A: boundary-like added set (complement closed, empty interior) inside a connected M'.
    B: dense-open M (complement closed, empty interior, no boundary) -- survives even a
       SMOOTH boundaryless category pin, so item (3) alone cannot discharge the repair.
    C: genuine interior addition (complement has non-empty interior).
    """
    m = frozenset({"m1", "m2"})
    h = frozenset({"h1", "h2"})
    # A: basis closed under intersection; every open set meets M, so M' is connected and
    # the complement H has empty interior.
    basis_a = [m, m | {"h1"}, m | {"h2"}, m | h]
    u_a = m | h
    # B: no boundary; M is open and dense, complement H closed with empty interior.
    basis_b = [frozenset({"m1"}), frozenset({"m1", "h1"}), frozenset({"m1", "h2"}),
               frozenset({"m1", "h1", "h2"})]
    u_b = frozenset({"m1", "h1", "h2"})
    # C: genuine interior addition: N is open and non-empty.
    n = frozenset({"n1"})
    basis_c = [frozenset({"m1"}), n]
    u_c = frozenset({"m1"}) | n

    iplus = {("m1", "h1"), ("m1", "h2")}
    out = {}
    for name, u, mset, basis in (("A_boundary_like", u_a, m, basis_a),
                                 ("B_dense_open_complement", u_b, frozenset({"m1"}), basis_b),
                                 ("C_genuine_interior", u_c, frozenset({"m1"}), basis_c)):
        opens = opens_of(basis)
        comp = u - mset
        out[name] = {
            "universe": sorted(u),
            "iota_M": sorted(mset),
            "complement": sorted(comp),
            "basis_intersection_closed": basis_closed_under_intersection(basis),
            "iota_M_is_open": is_open(opens, mset),
            "iota_M_is_proper": mset != u and bool(mset),
            "Mprime_connected": is_connected(u, opens),
            "complement_interior": sorted(interior(u, opens, comp)),
            "complement_has_empty_interior": not interior(u, opens, comp),
            "clause_f_uninteriored": clause_uninteriored(u, mset, iplus),
            "clause_f_interiored": clause_interiored(u, mset, iplus, opens),
        }
    out["_expected"] = {
        "A_boundary_like": {"clause_f_uninteriored": True, "clause_f_interiored": False},
        "B_dense_open_complement": {"clause_f_uninteriored": True, "clause_f_interiored": False},
        "C_genuine_interior": {"clause_f_uninteriored": True, "clause_f_interiored": True},
    }
    return out


# --------------------------------------------------------------------------------------
# Mutations (in-memory controls)
# --------------------------------------------------------------------------------------

def classify_f2a(text: str) -> dict:
    hits = CLAUSE_RE.findall(text)
    if len(hits) != 1:
        return {"found": len(hits), "has_interior_requirement": None}
    clause = hits[0]
    return {
        "found": 1,
        "has_interior_requirement": INTERIOR_TOKEN in clause,
        "has_future_witness": "I^+(q; g')" in clause,
        "clause": clause.strip(),
    }


def rev14_note(text: str) -> str | None:
    """The last revision_history note mentioning rev14."""
    for line in reversed(text.splitlines()):
        if "rev14 delta" in line:
            return line.strip()
    return None


def scope_items(acceptance: str) -> list[str]:
    return re.findall(r"\((\d)\)\s", acceptance)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--now", default=None,
                    help="ISO timestamp to stamp (determinism control); default wall clock")
    ap.add_argument("--out", default=str(HERE))
    args = ap.parse_args()
    tz = timezone(timedelta(hours=8))
    now = args.now or datetime.now(tz).isoformat(timespec="seconds")

    f2a_text, f2b_text = read_text(F2A), read_text(F2B)
    r3 = json.loads(read_text(R3))
    mp = json.loads(read_text(MAP))
    rev091 = json.loads(read_text(REV091))

    pins = {
        "F2a_path": "schemas/af_scc_c2_vacuum.yaml",
        "F2a_sha256": sha256(F2A),
        "F2b_path": "schemas/af_scc_c0_vacuum.yaml",
        "F2b_sha256": sha256(F2B),
        "FROZEN_path": "artifacts/formulation/FROZEN.json",
        "FROZEN_sha256": sha256(FROZEN),
        "r3_path": "reviews/G-FORM-final-verify-r3.json",
        "r3_sha256": sha256(R3),
        "map_path": "research_map/research_map.json",
        "map_sha256": sha256(MAP),
        "review_091_path": "reviews/F2a-review-rev29-b.json",
        "review_091_sha256": sha256(REV091),
    }

    frozen = json.loads(read_text(FROZEN))
    rev14 = next((a for a in mp["assignments"]
                  if a.get("event_id") == "astra-life08-formulation-rev14"), None)

    m = {
        "f2a_revision": int(re.search(r"(?m)^revision:\s*(\d+)", f2a_text).group(1)),
        "f2b_revision": int(re.search(r"(?m)^revision:\s*(\d+)", f2b_text).group(1)),
        "frozen_revision": frozen.get("revision"),
        "clause_f": {
            "F2a": dict(classify_f2a(f2a_text), line=line_of(f2a_text, "(f) the extension adds points")),
            "F2b": dict(classify_f2a(f2b_text), line=line_of(f2b_text, "(f) the extension adds points")),
        },
        "revision_history": {
            "F2a_r2_claim_present": R2_CLAIM_TOKEN in f2a_text,
            "F2b_r2_claim_present": R2_CLAIM_TOKEN in f2b_text,
            "F2a_rev14_note": rev14_note(f2a_text),
            "F2b_rev14_note": rev14_note(f2b_text),
            "F2a_rev14_note_mentions_clause_f": bool(
                rev14_note(f2a_text) and REV14_SCOPE_TOKEN in rev14_note(f2a_text)),
        },
        "r3_requirement": {
            "r3_required_before_proposal_mentions_clause_f": R3_REQUIRED_TOKEN in
            json.dumps(r3.get("gate_result", {})),
            "r3_named_finding_ids": [f.get("id") for row in r3.get("coverage_table", [])
                                     if row.get("class") == "F2a"
                                     for f in row.get("named_open_findings", [])],
            "r3_f2a_adjudicated_verdict": next((row.get("adjudicated_verdict")
                                                for row in r3.get("coverage_table", [])
                                                if row.get("class") == "F2a"), None),
        },
        "rev14_scope": {
            "assignment_found": rev14 is not None,
            "enumerated_items": scope_items(rev14["acceptance"]) if rev14 else [],
            "clause_f_in_scope": bool(rev14 and re.search(r"clause\s*\(f\)", rev14["acceptance"])),
            "falsifier_forbids_out_of_scope_moves": bool(
                rev14 and "outside the seven-item scope" in rev14["falsifier"]),
        },
        "review_091": {
            "verdict": rev091.get("verdict", {}).get("verdict"),
            "score": rev091.get("verdict", {}).get("score"),
            "hf_091_02_subitem_c": next(
                (sub for h in rev091.get("hard_failures", []) if h.get("id") == "HF-091-02"
                 for sub in h.get("sub_items", []) if sub.startswith("(c)")), None),
        },
    }

    models = run_models()
    controls = {
        "C1_determinism_same_now": None,  # filled by the second run comparison outside
        "C2_f2a_plus_interior_flips": classify_f2a(
            f2a_text.replace("(f) the extension adds points to the future: there exist",
                             "(f) the extension adds points to the future: "
                             + INTERIOR_TOKEN + " is non-empty AND there exist"))[
            "has_interior_requirement"],
        "C3_f2b_minus_interior_flips": classify_f2a(
            f2b_text.replace(INTERIOR_TOKEN + " is non-empty AND ", ""))[
            "has_interior_requirement"],
        "C4_r2_claim_detector_on_stripped_text": R2_CLAIM_TOKEN in re.sub(
            r"clause \(f\) interior\+chronological", "", f2a_text),
        "C5_scope_detector_with_synthetic_item8": bool(re.search(
            r"clause\s*\(f\)",
            (rev14["acceptance"] if rev14 else "") +
            " (8) propagate the clause (f) interior requirement into F2a")),
        "C6_r3_detector_on_stripped_report": R3_REQUIRED_TOKEN in json.dumps(
            {k: v for k, v in r3.get("gate_result", {}).items()
             if k != "required_before_proposal"}),
        "C7_model_sensitivity_interior_always_true": clause_interiored(
            frozenset({"m1", "h1", "h2"}), frozenset({"m1"}), {("m1", "h1")},
            [frozenset({"m1"}), frozenset({"m1", "h1", "h2"})]),
        "C8_basis_closed_all_models": all(
            models[k]["basis_intersection_closed"]
            for k in ("A_boundary_like", "B_dense_open_complement", "C_genuine_interior")),
    }

    findings = []
    gap_persists = (m["clause_f"]["F2a"]["has_interior_requirement"] is False
                    and m["clause_f"]["F2b"]["has_interior_requirement"] is True)
    if gap_persists:
        findings.append({
            "id": "W045-CF-01", "severity": "major", "status": "confirmed_at_live_bytes",
            "finding": ("F2a clause (f) still omits the interior requirement while F2b carries it; "
                        "the rev14 landing did not propagate it."),
            "evidence": ["schemas/af_scc_c2_vacuum.yaml#" + pins["F2a_sha256"][:12] + ":"
                         + str(m["clause_f"]["F2a"]["line"]),
                         "schemas/af_scc_c0_vacuum.yaml#" + pins["F2b_sha256"][:12] + ":"
                         + str(m["clause_f"]["F2b"]["line"])],
        })
    if not m["rev14_scope"]["clause_f_in_scope"]:
        findings.append({
            "id": "W045-CF-02", "severity": "major", "status": "authorization_gap",
            "finding": ("The rev14 authorization enumerates exactly "
                        + str(len(m["rev14_scope"]["enumerated_items"]))
                        + " items and contains no clause-(f) repair; its falsifier voids bytes "
                          "outside that scope. rev14 therefore cannot close the r3 F2a "
                          "requirement."
                          ),
            "evidence": ["research_map/research_map.json#" + pins["map_sha256"][:12]
                         + " (assignments[astra-life08-formulation-rev14].acceptance)"],
        })
    if m["revision_history"]["F2a_r2_claim_present"] and not m["clause_f"]["F2a"]["has_interior_requirement"]:
        findings.append({
            "id": "W045-CF-03", "severity": "minor", "status": "history_content_inconsistency",
            "finding": ("F2a revision_history[index 4] asserts the R2 'clause (f) "
                        "interior+chronological' correction, but the live F2a clause (f) does not "
                        "carry the interior requirement; the identical claim string is present in "
                        "F2b, whose bytes do carry it."),
            "evidence": ["schemas/af_scc_c2_vacuum.yaml#" + pins["F2a_sha256"][:12] + ":13",
                         "schemas/af_scc_c0_vacuum.yaml#" + pins["F2b_sha256"][:12] + ":13"],
        })
    findings.append({
        "id": "W045-CF-04", "severity": "info", "status": "model_result",
        "finding": ("The R2 escapability reason is regularity-independent at the point-set level: "
                    "both a boundary-like addition (model A) and a dense-open complement (model B) "
                    "satisfy the un-interiored clause (f) while int(M' minus iota(M)) is empty, and "
                    "model B has no boundary, so pinning the category SMOOTH/boundaryless (rev14 "
                    "item 3) does not remove the need for the interior requirement."),
        "evidence": ["artifacts/worker-045/f2a_clausef_scope/report.json (model_check)"],
    })
    findings.append({
        "id": "W045-CF-05", "severity": "info", "status": "prior_reviewers_agree",
        "finding": ("The gap is already named independently by worker-060 (HF-060-EXT-01) and "
                    "worker-091 (HF-091-02(c)); this task adds the post-rev14 byte state, the "
                    "authorization-scope measurement, and the regularity-independence model."),
        "evidence": ["reviews/G-FORM-final-verify-r3.json#" + pins["r3_sha256"][:12],
                     "reviews/F2a-review-rev29-b.json#" + pins["review_091_sha256"][:12]],
    })

    report = {
        "schema": "worker-task-report/1",
        "task_id": TASK_ID,
        "actor": ACTOR,
        "node_id": NODE_ID,
        "class_id": CLASS_ID,
        "gate": GATE,
        "created_at": now,
        "verdict": {
            "code": "CLAUSEF_GAP_PERSISTS_OUT_OF_REV14_SCOPE" if gap_persists
                    else "CLAUSEF_GAP_NOT_REPRODUCED",
            "worker_level_only": True,
            "no_gate_verdict": True,
            "summary": ("At the live post-rev14 bytes F2a clause (f) lacks the interior "
                        "requirement that F2b carries; the rev14 authorization does not include "
                        "the repair; r3 requires it before a G-FORM proposal. A bounded successor "
                        "authorization is needed before r3 can pass F2a."),
        },
        "pins": pins,
        "measurements": m,
        "model_check": models,
        "findings": findings,
        "recommended_fix_path": [
            "Controller issues a bounded successor authorization (rev15 or a REC-36 amendment) "
            "whose scope is exactly: replace F2a clause (f) with the F2b interior wording "
            "'int(M' minus iota(M)) is non-empty AND there exist q in iota(M) and p in "
            "int(M' minus iota(M)) with p in I^+(q; g')', with mutation controls, byte-identical "
            "mirrors, a FROZEN bump and fresh non-author verdicts.",
            "Do not import F2b's C0-specific CONVENTION CAVEAT verbatim: it concerns merely "
            "continuous metrics; the interior requirement itself is the part whose R2 reason is "
            "regularity-independent (models A/B).",
            "Until the new bytes land, r3 must not propose G-FORM for F2a; the current F2a "
            "verdicts are void at the post-rev14 pins in any case.",
        ],
        "falsifier": (
            "Falsified if any of: (a) at the recorded F2a pin the clause (f) text contains an "
            "interior requirement int(M' minus iota(M)) non-empty; (b) the R2 'clause (f) was "
            "escapable' rationale is regularity-specific -- i.e. under F2a's declared (a)-(e) a "
            "proper extension whose added set has empty interior cannot satisfy the un-interiored "
            "clause (f); (c) the rev14 authorization (astra-life08-formulation-rev14) contains the "
            "clause-(f) interior repair inside its enumerated scope; (d) reviews/G-FORM-final-"
            "verify-r3.json does not require the clause-(f) propagation before a G-FORM proposal; "
            "(e) any pinned input hash differs at re-run time (drift voids the corresponding "
            "finding)."),
        "limitations": [
            "The finite-topology models establish the point-set content of the clause distinction; "
            "they do not claim metric realizability (Ric(g')=0, C2 g') of any model.",
            "The physical instance of a boundary-only addition (a Cauchy horizon included as "
            "boundary of an extended vacuum development) is cited as standard, not re-proved.",
            "The rev14 mirrors and FROZEN rev30 were in flight at measurement time; the report "
            "binds to the measured schema bytes and records the FROZEN state separately.",
        ],
        "authority_note": ("Worker event: advisory evidence for the r3 verifier and the controller. "
                           "No canonical write, no node transition, no gate verdict, no "
                           "validation_status=passed."),
    }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n",
                                     encoding="utf-8")
    (out / "controls.json").write_text(json.dumps(
        {"task_id": TASK_ID, "created_at": now, "controls": controls,
         "expected": {"C2_f2a_plus_interior_flips": False,
                      "C3_f2b_minus_interior_flips": False,
                      "C4_r2_claim_detector_on_stripped_text": False,
                      "C5_scope_detector_with_synthetic_item8": True,
                      "C6_r3_detector_on_stripped_report": False,
                      "C7_model_sensitivity_interior_always_true": True,
                      "C8_basis_closed_all_models": True}}, indent=1, sort_keys=True) + "\n",
        encoding="utf-8")

    # drift guard: re-measure after the analysis
    post = {k: sha256(p) for k, p in (("F2a_sha256", F2A), ("F2b_sha256", F2B),
                                      ("FROZEN_sha256", FROZEN), ("r3_sha256", R3),
                                      ("map_sha256", MAP),
                                      ("review_091_sha256", REV091))}
    drift = {k: (pins[k], post[k]) for k in post if pins[k] != post[k]}
    print(json.dumps({
        "verdict": report["verdict"]["code"],
        "F2a_sha256": pins["F2a_sha256"], "F2a_clause_f_has_interior":
            m["clause_f"]["F2a"]["has_interior_requirement"],
        "F2b_clause_f_has_interior": m["clause_f"]["F2b"]["has_interior_requirement"],
        "rev14_items": m["rev14_scope"]["enumerated_items"],
        "clause_f_in_rev14_scope": m["rev14_scope"]["clause_f_in_scope"],
        "r3_requires_it": m["r3_requirement"]["r3_required_before_proposal_mentions_clause_f"],
        "drift": drift,
        "report_sha256": hashlib.sha256((out / "report.json").read_bytes()).hexdigest(),
        "controls_sha256": hashlib.sha256((out / "controls.json").read_bytes()).hexdigest(),
    }, indent=1))
    return 0 if not drift else 2


if __name__ == "__main__":
    sys.exit(main())
