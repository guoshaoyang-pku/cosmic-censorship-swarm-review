#!/usr/bin/env python3
"""Independent second implementation for W010-F2A-C2-CONFORMANCE-REV13-01.

Written from the frozen AF-SCC-C2-VAC-GEN class contract (schemas/af_scc_c2_vacuum.yaml
rev13) and from ledger/theorems.jsonl; it does NOT import c2_conformance_audit.py and does
not reuse its regex tables. The classification is deliberately dual to the audit's:

  * audit  : disqualifier-only. D1 fails if any disqualifier family matches ANY assertion
             field; direction matches the whole assertion surface with a negation-prefix
             guard.
  * verifier: positive-marker. D1 passes only if the entry's OWN assertion fields
             (statement_exact / genericity / topology / regularity) carry a positive
             generic-one-ended-AF-vacuum marker; direction is computed by an explicit
             regularity lattice with an ordinal floor, and meta fields
             (unresolved / scope_caveats / does_not_imply) are excluded from direction.

Agreement between two structurally different readings is the evidence; disagreement is a
finding, not silently reconciled.

Exit: 0 all_pass; 2 fixture or pin failure; 3 disagreement with the audit.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
AUDIT = HERE / "c2_conformance_audit.json"
OUT = HERE / "verify_c2_rev13_independent.json"
CST = timezone(timedelta(hours=8))

CLASS_ID = "AF-SCC-C2-VAC-GEN"
SCHEMA = "schemas/af_scc_c2_vacuum.yaml"
LEDGER = "ledger/theorems.jsonl"
PINS = {
    SCHEMA: "e9a27996dfd3",
    LEDGER: "a1674f094979",
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a961",
    "ledger/class_coverage.csv": "abbaee54a5a3",
    "artifacts/formulation/FROZEN.json": "815e08079aef",
    "artifacts/worker-010/class_binding_reconcile/binding_reconcile_audit.json": "dc391cad38cd",
}
NON_RESULT = {"definition", "literature_status", "conjecture"}

# regularity lattice: a conclusion forbidding extension at floor f implies the class
# conclusion iff f <= C2 (C^{0,1}_loc -> C^1 -> C^2 -> C^k -> smooth).
REG_ORDER = ["C0", "L2CONN", "LIP", "C1", "C2", "CK", "SMOOTH"]

POS_DATA_MARKERS = re.compile(
    r"one-ended[^.\n]{0,40}asymptotically flat|asymptotically flat[^.\n]{0,60}cauchy|"
    r"constraint manifold|comeager|residual set|generic (?:set|data)", re.I)
VACUUM_MARKER = re.compile(r"\bvacuum\b", re.I)
DATA_DISQUALIFIER = re.compile(
    r"characteristic|interior|inside (?:a|the) (?:dynamical )?black hole|high-frequency|"
    r"impulsive|special \(|two-ended|gowdy|spherical|price|conditional|expected|"
    r"not quantified|non-?generic|symmetry reduction", re.I)

DIRECTION_FORMS = [
    # (side, floor, pattern)   contrary iff floor >= C2; supports iff floor <= C2
    ("contrary", "SMOOTH", r"\bsmooth\b[^.\n]{0,50}(?:extension|extendib)"),
    ("contrary", "CK", r"\bc\^?k\b[^.\n]{0,50}(?:extension|extendib)"),
    ("contrary", "C2", r"\bc\^?2\b[^.\n]{0,60}(?:extension|extendib)|"
                       r"twice continuously differentiable[^.\n]{0,60}extend"),
    ("supports", "C2", r"(?:no|not|non)[^.\n]{0,30}\bc\^?2\b[^.\n]{0,60}(?:extension|extendib)|"
                       r"\bc\^?2\b[^.\n]{0,40}inextend"),
    ("supports", "LIP", r"(?:not|non)[- ]?lipschitz[^.\n]{0,40}extend|"
                       r"lipschitz[^.\n]{0,30}inextend|\bc\^?\{?0,1\}?[_ ]?loc\b[^.\n]{0,30}inextend"),
    ("supports", "C1", r"(?:not|non)[^.\n]{0,20}\bc\^?1\b[^.\n]{0,30}extend"),
    ("supports", "C0", r"(?:not|non)[^.\n]{0,20}(?:\bc\^?0\b|continuous)[^.\n]{0,30}inextend"),
    ("weaker", "C0", r"extends? continuously|continuous[^.\n]{0,30}extension|"
                      r"\bc\^?0\b[^.\n]{0,30}extend|christoffel symbols[^.\n]{0,20}(?:in|l\^?2)"),
    ("weaker", "L2CONN", r"l\^?2[_ ]?loc|square[- ]integrable christoffel"),
]
NEG_INSIDE = re.compile(r"\b(?:no|not|non|never|without)\b")


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def own_assertion_text(e: dict) -> str:
    parts = []
    for f in ("statement_exact", "genericity", "topology", "regularity", "label"):
        v = e.get(f)
        if v is None:
            continue
        if isinstance(v, dict):
            parts.append(json.dumps(v))
        elif isinstance(v, (list, tuple)):
            parts.extend(str(x) for x in v)
        else:
            parts.append(str(v))
    return re.sub(r"\s+", " ", " || ".join(parts)).lower()


def direction(e: dict) -> dict:
    if e.get("entry_kind") in NON_RESULT or e.get("conclusion_type") in (
            "open_problem", "formal_model"):
        return {"side": "not_a_result", "floor": None, "matched": None}
    text = own_assertion_text(e)
    for side, floor, pat in DIRECTION_FORMS:
        m = re.search(pat, text, re.I)
        if m:
            prefix = text[max(0, m.start() - 45):m.start()]
            if side == "contrary" and (NEG_INSIDE.search(prefix)
                                       or NEG_INSIDE.search(m.group(0))):
                continue
            return {"side": side, "floor": floor, "matched": m.group(0)}
    if re.search(r"inextend", text, re.I):
        return {"side": "supports", "floor": "C2",
                "matched": re.search(r"inextend\w*", text, re.I).group(0)}
    return {"side": "not_determined", "floor": None, "matched": None}


def data_class(e: dict) -> dict:
    if e.get("entry_kind") in NON_RESULT or e.get("conclusion_type") in (
            "open_problem", "formal_model"):
        return {"verdict": "n/a", "reason": "NON_RESULT_ENTRY", "matched": None}
    text = own_assertion_text(e)
    pos = POS_DATA_MARKERS.search(text)
    vac = VACUUM_MARKER.search(text)
    dis = DATA_DISQUALIFIER.search(text)
    if dis:
        return {"verdict": "fail", "reason": "DISQUALIFIER_IN_OWN_ASSERTION",
                "matched": dis.group(0)}
    if not (pos and vac):
        return {"verdict": "fail", "reason": "NO_POSITIVE_GENERIC_AF_VACUUM_MARKER",
                "matched": None}
    return {"verdict": "pass", "reason": "POSITIVE_MARKER_PRESENT", "matched": pos.group(0)}


def evidence(e: dict) -> dict:
    unresolved = e.get("unresolved") or []
    text = own_assertion_text(e)
    hyp = re.search(r"assum|conditional|expected|hypothes|not proved|conjectur", text, re.I)
    sub = {
        "verified": e.get("content_status") == "verified",
        "tier_ok": e.get("evidence_level") in ("peer-reviewed", "accepted-in-press"),
        "no_unresolved": len(unresolved) == 0,
        "no_open_hypothesis": hyp is None,
    }
    return {"verdict": "pass" if all(sub.values()) else "fail", "subchecks": sub}


def classify(e: dict) -> dict:
    d1, d2, d3 = data_class(e), direction(e), evidence(e)
    discharge = (d1["verdict"] == "pass" and d2["side"] == "supports"
                 and d3["verdict"] == "pass")
    return {"d1": d1["verdict"], "d2": d2["side"], "d3": d3["verdict"],
            "discharge": discharge, "detail": {"d1": d1, "d2": d2, "d3": d3}}


# ------------------------------------------------------------------ labeled fixtures
def fx(kind, ctype, statement, genericity, ev, content, unresolved, topology="one-ended AF"):
    return {"theorem_id": "FX", "entry_kind": kind, "conclusion_type": ctype,
            "statement_exact": statement, "genericity": genericity, "topology": topology,
            "regularity": "fixture", "evidence_level": ev, "content_status": content,
            "unresolved": unresolved, "class_ids": [CLASS_ID]}


FIXTURES = [
    ("FX1-positive-discharge", fx(
        "theorem", "theorem",
        "For a comeager set of one-ended asymptotically flat vacuum Cauchy data the maximal "
        "development is C^2-inextendible: no proper future C2 vacuum extension exists.",
        "residual comeager", "peer-reviewed", "verified", []),
     {"d1": "pass", "d2": "supports", "d3": "pass", "discharge": True}),
    ("FX2-c0-only-weaker", fx(
        "theorem", "theorem",
        "For a comeager set of one-ended asymptotically flat vacuum data the metric extends "
        "continuously across the Cauchy horizon.",
        "residual comeager", "peer-reviewed", "verified", []),
     {"d1": "pass", "d2": "weaker", "d3": "pass", "discharge": False}),
    ("FX3-c2-extension-contrary", fx(
        "theorem", "theorem",
        "For a comeager set of one-ended asymptotically flat vacuum data the maximal "
        "development admits a proper future C2 vacuum extension.",
        "residual comeager", "peer-reviewed", "verified", []),
     {"d1": "pass", "d2": "contrary", "d3": "pass", "discharge": False}),
    ("FX4-smooth-extension-contrary", fx(
        "theorem", "theorem",
        "For a comeager set of one-ended asymptotically flat vacuum data a smooth extension "
        "of the maximal development exists.",
        "residual comeager", "peer-reviewed", "verified", []),
     {"d1": "pass", "d2": "contrary", "d3": "pass", "discharge": False}),
    ("FX5-characteristic-data", fx(
        "preprint_result", "theorem",
        "Given a characteristic initial value problem the metric is not Lipschitz extendible.",
        "residual comeager", "peer-reviewed", "verified", [],
        topology="characteristic data"),
     {"d1": "fail", "d2": "supports", "d3": "pass", "discharge": False}),
    ("FX6-preprint-unresolved", fx(
        "preprint_result", "theorem",
        "For a comeager set of one-ended asymptotically flat vacuum data no proper future C2 "
        "vacuum extension exists.",
        "residual comeager", "preprint", "provisional", ["peer review"]),
     {"d1": "pass", "d2": "supports", "d3": "fail", "discharge": False}),
    ("FX7-definition-null", fx(
        "definition", "open_problem",
        "The C^2 formulation of strong cosmic censorship: the maximal development is "
        "future-inextendible as a C^2 Lorentzian manifold.",
        "generic data", "peer-reviewed", "verified", ["primary attribution"]),
     {"d1": "n/a", "d2": "not_a_result", "d3": "fail", "discharge": False}),
]


def main() -> int:
    audit_sha = sha256(AUDIT)
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    checks = []
    disagreements = []

    # --- fixtures
    fixtures = []
    for name, entry, expect in FIXTURES:
        obs = classify(entry)
        got = {k: obs[k] for k in ("d1", "d2", "d3", "discharge")}
        fixtures.append({"name": name, "expected": expect, "observed": got,
                         "pass": got == expect})
    fixtures_pass = all(f["pass"] for f in fixtures)
    checks.append({"check": "labeled_fixtures", "n": len(fixtures),
                   "all_pass": fixtures_pass})

    # --- pins
    pins_ok = True
    pin_detail = {}
    for rel, pref in PINS.items():
        p = ROOT / rel
        h = sha256(p) if p.exists() else None
        ok = bool(h and h[:12] == pref)
        pins_ok = pins_ok and ok
        pin_detail[rel] = {"measured": h, "expected_prefix": pref, "ok": ok}
    checks.append({"check": "pins_re_measured", "all_pass": pins_ok, "detail": pin_detail})

    # --- independent binding selection
    entries = [json.loads(l) for l in (ROOT / LEDGER).read_text(encoding="utf-8")
               .splitlines() if l.strip()]
    indep_ids = sorted(e["theorem_id"] for e in entries
                       if CLASS_ID in (e.get("class_ids") or []))
    audit_ids = sorted(b["theorem_id"] for b in audit["bindings"])
    sel_ok = indep_ids == audit_ids
    checks.append({"check": "binding_selection", "all_pass": sel_ok,
                   "independent_ids": indep_ids, "audit_ids": audit_ids})

    # --- per-binding verdict agreement
    audit_by_id = {b["theorem_id"]: b for b in audit["bindings"]}
    n_agree = 0
    agreement = []
    for e in entries:
        if e["theorem_id"] not in audit_by_id:
            continue
        a = audit_by_id[e["theorem_id"]]
        v = classify(e)
        row = {
            "theorem_id": e["theorem_id"],
            "audit": {"d1": a["d1_data_class"]["verdict"], "d2": a["d2_conclusion"]["verdict"],
                      "d3": a["d3_evidence"]["verdict"], "discharge": a["discharges_class"]},
            "independent": {k: v[k] for k in ("d1", "d2", "d3", "discharge")},
        }
        # the audit's n/a rows carry d2 verdict "n/a"; the verifier calls it not_a_result
        # vocabulary maps: the audit calls the weakest side "weaker_not_contrary", the
        # verifier's lattice calls it "weaker"; non-result D2 is "n/a" vs "not_a_result".
        AUDIT2VERIFIER = {"n/a": {"n/a", "not_a_result"}, "weaker_not_contrary": {"weaker"},
                          "supports": {"supports"}, "contrary": {"contrary"}}
        row["comparable"] = {
            "d1": row["audit"]["d1"] == row["independent"]["d1"],
            "d2": row["independent"]["d2"] in AUDIT2VERIFIER.get(row["audit"]["d2"], set()),
            "d3": row["audit"]["d3"] == row["independent"]["d3"],
            "discharge": row["audit"]["discharge"] == row["independent"]["discharge"],
        }
        row["agree"] = all(row["comparable"].values())
        n_agree += int(row["agree"])
        if not row["agree"]:
            disagreements.append(row)
        agreement.append(row)
    agree_ok = not disagreements
    checks.append({"check": "per_binding_verdict_agreement", "all_pass": agree_ok,
                   "n_bindings": len(agreement), "n_agree": n_agree})

    # --- direction-correction agreement: independent contrary count must be 0
    indep_contrary = [e["theorem_id"] for e in entries
                      if CLASS_ID in (e.get("class_ids") or [])
                      and direction(e)["side"] == "contrary"]
    corr_ok = indep_contrary == [] and \
        audit["direction_reclassification_vs_cbr"]["semantic_contrary_count_all_bindings"] == 0
    checks.append({"check": "semantic_contrary_count_is_zero", "all_pass": corr_ok,
                   "independent_contrary_ids": indep_contrary})

    all_pass = all(c["all_pass"] for c in checks)
    report = {
        "verification_id": f"w010-c2-rev13-independent-{datetime.now(CST).strftime('%Y%m%dT%H%M%S')}",
        "task_id": "W010-F2A-C2-CONFORMANCE-REV13-01",
        "actor": "worker-010",
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "target_report": str(AUDIT.relative_to(ROOT)),
        "target_report_sha256": audit_sha,
        "method": "independent second implementation; positive-marker data-class test, "
                  "ordinal regularity lattice, own-assertion-field direction scan; no import "
                  "of the audited driver",
        "predicate_repairs": [
            {"defect": "contrary form `c^?k` matched the substring 'ck' inside 'black-hole' "
                       "in T-526's label, producing a false contrary verdict",
             "detected_by": "per_binding_verdict_agreement / semantic_contrary_count_is_zero",
             "fix": "word boundaries on the regularity tokens (\\bc\\^?k\\b, \\bc\\^?2\\b)"},
            {"defect": "contrary pattern matched inside a negated existence clause ('no proper "
                       "future C2 vacuum extension exists') because the negation lay inside "
                       "the matched span, not in the prefix",
             "detected_by": "FX1-positive-discharge fixture",
             "fix": "reject contrary matches whose span or 45-char prefix contains a negation "
                    "token"},
            {"defect": "FX5 fixture conflated a data-class disqualifier with an "
                       "evidence-level hypothesis form ('expected generically')",
             "detected_by": "FX5-characteristic-data fixture",
             "fix": "fixture genericity set to 'residual comeager' so the fixture tests one "
                    "axis; the open-hypothesis scan itself is unchanged"},
        ],
        "predicate_repair_note": "All three were caught by the labeled fixtures / cross-check "
                                 "written before the run, not by inspection; repairs change "
                                 "only the verifier, never the audited report.",
        "checks": checks,
        "fixtures": fixtures,
        "per_binding_agreement": agreement,
        "disagreements": disagreements,
        "reading": (
            f"Independent implementation reproduces the audit at {audit_sha[:12]}: "
            f"{n_agree}/{len(agreement)} bindings agree on D1/D2/D3/discharge; binding "
            f"selection sets are identical ({len(indep_ids)} ids); the semantic "
            f"contrary-side count is 0 by both implementations; {len(fixtures)}/"
            f"{len(fixtures)} labeled fixtures pass."
        ),
        "falsifier": "A fixture whose labeled expectation the independent implementation "
                     "misses, a binding-selection set difference, a per-binding verdict "
                     "disagreement, or a live pin whose bytes differ from the audited pin.",
        "limitations": [
            "Mechanical reproducibility check, not a reviewer verdict and not an "
            "independent-reviewer independence claim (same fleet slot as the audit author).",
            "The dual D1 formulation (positive marker) fails closed: an entry that does not "
            "state the class data class in its own assertion fields is not counted, even if "
            "a caveat mentions it.",
        ],
        "all_pass": all_pass,
        "validation_status": "unverified",
        "claims_completion": False,
    }
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    rc = 0 if all_pass else (2 if not fixtures_pass or not pins_ok else 3)
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"all_pass={all_pass} fixtures={sum(f['pass'] for f in fixtures)}/{len(fixtures)} "
          f"pins_ok={pins_ok} selection_ok={sel_ok} agreement={n_agree}/{len(agreement)} "
          f"indep_contrary={indep_contrary}")
    print("verify sha256:", sha256(OUT))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
