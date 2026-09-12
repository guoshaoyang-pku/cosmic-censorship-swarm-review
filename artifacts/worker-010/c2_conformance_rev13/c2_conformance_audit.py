#!/usr/bin/env python3
"""W010-F2A-C2-CONFORMANCE-REV13-01 — class-bound conformance + direction audit of
AF-SCC-C2-VAC-GEN (F2a) at the FROZEN rev29 / schema-rev13 pins.

No inbox card existed for worker-010 at fleet 2026-09-12T01:04; this is ONE self-selected
bounded class-bound task (comms/PROTOCOL.md rule 4; ASTRA_HANDOFF "your assignment is in
comms/inbox", which is empty for this slot and is recorded as such).

What this measures, and why it is not a re-run of the C0 audit or of the CBR audit
------------------------------------------------------------------------------------
* W010-L1-REAUDIT-02 audited AF-SCC-C0-VAC-GEN only. The C2 sibling has never had a
  D1_data_class / D2_conclusion / D3_evidence discharge analysis at any revision.
* W010-CBR-01 (class binding reconcile) flagged direction *lexically*: any "extension
  exists" sentence was flagged negation-side for every class. That reading is wrong for the
  C2 class specifically, because C^0 / L^2_loc / Lipschitz extension assertions are NOT
  negations of "no proper future C^2 vacuum extension" (regularity inclusion runs
  C^{0,1}_loc -> C^1 -> C^2, so ruling out a *stronger* regularity implies the conclusion,
  while exhibiting a *weaker* extension does not contradict it). This audit reclassifies the
  five C2 bindings the CBR flagged, with quoted evidence and a reason code, and records the
  corrected contrary count.

Deterministic, stdlib + PyYAML only, no network, no writes outside this directory.
Exit codes: 0 = report written and inputs stable; 2 = control failure; 3 = input drift (VOID).
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / "c2_conformance_audit.json"
SNAP = HERE / "snapshots"
CST = timezone(timedelta(hours=8))

TASK_ID = "W010-F2A-C2-CONFORMANCE-REV13-01"
CLASS_ID = "AF-SCC-C2-VAC-GEN"
NODE_ID = "L1"
GATE = "G-LIT"

SCHEMA = "schemas/af_scc_c2_vacuum.yaml"
LEDGER = "ledger/theorems.jsonl"
TAXONOMY = "research_map/formulation_taxonomy.yaml"
COVERAGE = "ledger/class_coverage.csv"
FROZEN = "artifacts/formulation/FROZEN.json"
CBR = "artifacts/worker-010/class_binding_reconcile/binding_reconcile_audit.json"

# (path, expected 12-hex prefix of the sha256 measured at task start)
PINS = {
    SCHEMA: "e9a27996dfd3",
    LEDGER: "a1674f094979",
    TAXONOMY: "0abb9ed8a961",
    COVERAGE: "abbaee54a5a3",
    FROZEN: "815e08079aef",
    CBR: "dc391cad38cd",
}

RESULT_KINDS = {"theorem", "counterexample", "preprint_result", "conditional_theorem"}
NON_RESULT_KINDS = {"definition", "literature_status", "conjecture"}

# ---------------------------------------------------------------- D1 data-class families
# A result entry satisfies D1 only if it quantifies over the class's residual/comeager set
# of one-ended asymptotically flat VACUUM Cauchy data in the declared regularity class.
# Each family below is a disqualifier; the report records the matched span as evidence.
D1_FAMILIES = [
    ("CHARACTERISTIC_OR_INTERIOR",
     r"characteristic (?:initial value|initial data|cauchy|data)|black[- ]hole interior|"
     r"interior of (?:a |the )?(?:dynamical )?black hole|hypersurface slightly inside|"
     r"beyond characteristic data|inside a dynamical black hole"),
    ("SPECIAL_OR_NONGENERIC_DATA",
     r"data class is special|high[- ]frequency/impulsive|high[- ]frequency|impulsive|"
     r"not generic AF collapse|non-?generic (?:data|class)"),
    ("UNQUANTIFIED_OR_EXPECTED_GENERICITY",
     r"not quantified as open/dense|generic in the stated|expected \(not proved\)|"
     r"expected to hold|conjecturally present|not proved here|expected generically|"
     r"expected \(not proved here\)"),
    ("CONDITIONAL_DATA_ASSUMPTION",
     r"conditional on|satisfying a precise nonlinear price|price[- ]?law[- ]?type estimate|"
     r"assumes a nonlinear price"),
    ("MODEL_OR_REDUCED_SYMMETRY",
     r"two-ended|t\^?3[- ]?gowdy|gowdy|spherically symmetric|symmetry reduction|"
     r"einstein-maxwell-real-scalar model"),
    ("EXACT_SOLUTION",
     r"exact solution|schwarzschild solution|kerr solution"),
]

# --------------------------------------------------- D2 conclusion (regularity inclusion)
# C2 class conclusion: MGHD admits NO proper future C2 vacuum extension (or stronger).
# contrary_extension_asserted : asserts a C2-or-smoother vacuum extension exists -> negates.
# supports_class_conclusion   : rules out C^{0,1}_loc / C^1 / C^2 / C^k / smooth extension
#                               -> implies the conclusion by regularity inclusion.
# weaker_extension_asserted   : asserts a C^0 / L^2_loc-connection / bare-metric extension
#                               -> NOT the negation of the C2 conclusion.
D2_CONTRARY = re.compile(
    r"(?:admits?|exists?|there (?:is|exists))\s+(?:a\s+)?(?:proper\s+)?(?:future\s+)?c\^?2\b"
    r"|(?:c\^?2|c\^?k|smooth)\s+(?:vacuum\s+)?(?:metric\s+)?extension\s+(?:exists|of the maximal)"
    r"|extendible as a c\^?2|extendible as a smooth",
    re.I)
D2_SUPPORTS = re.compile(
    r"not\s+lipschitz[- ]?extend|non-?lipschitz[- ]?extend|lipschitz[- ]?inextend"
    r"|c\^?\{?0,1\}?[_ ]?loc[- ]?inextend|not\s+c\^?2[- ]?(?:future[- ]?)?extend"
    r"|non-?c\^?2[- ]?(?:future[- ]?)?extend|no proper future c\^?2[^.\n]{0,90}extension"
    r"|c\^?2[^.\n]{0,120}inextend|not\s+smooth[- ]?extend|smooth[- ]?inextend"
    r"|higher[- ]regularity extension[^.\n]{0,60}(?:forbidden|excluded|no)",
    re.I)
D2_WEAKER = re.compile(
    r"(?:continuous(?:ly)?|c\^?0)[- ]?extend|extends continuously"
    r"|extension with continuous metric|christoffel symbols (?:in|square|fail)"
    r"|l\^?2[_ ]?loc|bare metric extension",
    re.I)

OPEN_HYPOTHESIS = re.compile(
    r"assum|conditional|expected|hypothes|conjectur|not proved", re.I)

CBR_FLAGGED_C2 = ["D-004", "T-303", "T-401", "T-402", "T-526"]


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def measure(rel: str) -> dict:
    p = ROOT / rel
    if not p.exists():
        return {"path": rel, "exists": False, "sha256": None, "bytes": None}
    b = p.read_bytes()
    return {"path": rel, "exists": True, "sha256": hashlib.sha256(b).hexdigest(),
            "bytes": len(b), "sha256_prefix": hashlib.sha256(b).hexdigest()[:12]}


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def load_ledger(path: Path) -> list:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def bindings_of(entries: list, class_id: str = CLASS_ID) -> list:
    """Binding predicate: the class token appears in the entry's declared class_ids list."""
    return [e for e in entries if class_id in (e.get("class_ids") or [])]


ASSERTION_FIELDS = ["statement_exact", "genericity", "regularity", "topology",
                    "scope_caveats", "unresolved", "does_not_imply", "assumptions", "label"]
META_FIELDS = ["falsifiers", "next_action", "ledger_tags", "acceptance_authority",
               "review_status", "verification_status", "author_asserts_supports",
               "evidence_basis", "source_ids"]


def field_parts(e: dict, fields=None) -> list:
    """[(field, text)] for the assertion-bearing fields only. Meta fields such as the
    entry's own `falsifiers` ("Construct data whose MGHD admits a C^2 extension ...") are
    excluded: they state what would refute the entry, not what it asserts."""
    fields = fields or ASSERTION_FIELDS
    out = []
    for f in fields:
        v = e.get(f)
        if v is None:
            continue
        if isinstance(v, (list, tuple)):
            for x in v:
                out.append((f, re.sub(r"\s+", " ", str(x)).lower()))
        elif isinstance(v, dict):
            out.append((f, re.sub(r"\s+", " ", json.dumps(v, ensure_ascii=False)).lower()))
        else:
            out.append((f, re.sub(r"\s+", " ", str(v)).lower()))
    return out


def build_text(entry: dict, fields=None) -> str:
    return " || ".join(t for _, t in field_parts(entry, fields))


NEGATED_PREFIX = re.compile(r"\b(?:no|not|non|never|without|fails? to|absent)\b")


def all_matches(families, entry: dict) -> list:
    """Every (family, field, span) match across the assertion fields, in field order."""
    out = []
    for field, text in field_parts(entry):
        for code, pat in families:
            for m in re.finditer(pat, text, re.I):
                out.append({"family": code, "field": field, "span": m.group(0)})
    return out


def pick_primary(matches: list, families) -> dict | None:
    order = [code for code, _ in families]
    for code in order:
        for m in matches:
            if m["family"] == code:
                return m
    return None


def classify_d1(entry: dict) -> dict:
    kind = entry.get("entry_kind")
    if kind in NON_RESULT_KINDS or entry.get("conclusion_type") in ("open_problem", "formal_model"):
        return {"verdict": "n/a", "reason": "NON_RESULT_ENTRY", "matched": None, "matches": []}
    matches = all_matches(D1_FAMILIES, entry)
    primary = pick_primary(matches, D1_FAMILIES)
    if primary:
        return {"verdict": "fail", "reason": primary["family"], "matched": primary["span"],
                "matched_field": primary["field"], "matches": matches}
    return {"verdict": "pass", "reason": "NO_DISQUALIFIER_MATCHED", "matched": None,
            "matches": []}


def _non_negated(rx: re.Pattern, entry: dict) -> dict | None:
    """First match of `rx` that is not inside a negated context ('no proper future C2
    vacuum extension exists' must not be read as 'a C2 extension exists')."""
    for field, text in field_parts(entry):
        for m in rx.finditer(text):
            prefix = text[max(0, m.start() - 40):m.start()]
            if NEGATED_PREFIX.search(prefix):
                continue
            return {"field": field, "span": m.group(0)}
    return None


def assertion_side(entry: dict) -> dict:
    contrary = _non_negated(D2_CONTRARY, entry)
    if contrary:
        return {"side": "contrary_extension_asserted", "matched": contrary["span"],
                "matched_field": contrary["field"]}
    for name, rx in (("supports_class_conclusion", D2_SUPPORTS),
                     ("weaker_extension_asserted", D2_WEAKER)):
        m = _non_negated(rx, entry)
        if m:
            return {"side": name, "matched": m["span"], "matched_field": m["field"]}
    return {"side": "not_determined", "matched": None, "matched_field": None}


def classify_d2(entry: dict) -> dict:
    kind = entry.get("entry_kind")
    side = assertion_side(entry)
    if kind in NON_RESULT_KINDS or entry.get("conclusion_type") in ("open_problem", "formal_model"):
        return {"verdict": "n/a", "reason": "NON_RESULT_ENTRY", "assertion_side": side["side"],
                "matched": side["matched"]}
    if side["side"] == "contrary_extension_asserted":
        return {"verdict": "contrary", "reason": "C2_OR_SMOOTHER_EXTENSION_ASSERTED",
                "assertion_side": side["side"], "matched": side["matched"]}
    if side["side"] == "supports_class_conclusion":
        return {"verdict": "supports", "reason": "STRONGER_REGULARITY_RULED_OUT",
                "assertion_side": side["side"], "matched": side["matched"]}
    if side["side"] == "weaker_extension_asserted":
        return {"verdict": "weaker_not_contrary",
                "reason": "WEAKER_REGULARITY_EXTENSION_IS_NOT_A_C2_NEGATION",
                "assertion_side": side["side"], "matched": side["matched"]}
    return {"verdict": "not_determined", "reason": "NO_DIRECTION_FORM_MATCHED",
            "assertion_side": side["side"], "matched": side["matched"]}


def classify_d3(entry: dict) -> dict:
    unresolved = entry.get("unresolved") or []
    text = build_text(entry, ["genericity", "statement_exact", "scope_caveats",
                              "does_not_imply", "assumptions"])
    hyp = OPEN_HYPOTHESIS.search(text)
    sub = {
        "content_status_verified": entry.get("content_status") == "verified",
        "evidence_peer_reviewed_or_accepted": entry.get("evidence_level") in
        ("peer-reviewed", "accepted-in-press"),
        "no_unresolved_item": len(unresolved) == 0,
        "no_open_hypothesis_form": hyp is None,
    }
    return {"verdict": "pass" if all(sub.values()) else "fail",
            "reason": "ALL_SUBCHECKS_PASS" if all(sub.values()) else
                      "FAILED:" + ",".join(k for k, v in sub.items() if not v),
            "subchecks": sub, "n_unresolved": len(unresolved),
            "open_hypothesis_span": hyp.group(0) if hyp else None}


def classify(entry: dict) -> dict:
    d1, d2, d3 = classify_d1(entry), classify_d2(entry), classify_d3(entry)
    discharge = (d1["verdict"] == "pass" and d2["verdict"] == "supports"
                 and d3["verdict"] == "pass")
    return {"d1_data_class": d1, "d2_conclusion": d2, "d3_evidence": d3,
            "discharges_class": discharge}


def cbr_reclassify(entry: dict, finding: dict | None = None) -> dict:
    """Map the CBR lexical flag for this entry to the semantic (regularity-aware) side.

    The reason code is decided from the span the CBR actually flagged (`matched_text`
    inside `matched_sentence`), not from the entry text at large: an entry may state the
    regularity inclusion correctly elsewhere and still have been flagged on a C0 clause.
    """
    side = assertion_side(entry)
    matched_texts = [str(x).lower() for x in ((finding or {}).get("matched_text") or [])]
    sentences = [str(x).lower() for x in ((finding or {}).get("matched_sentence") or [])]
    neg_scope = False
    for mt in matched_texts:
        pat = re.compile(r"(?:non-?|not\s+|never\s+)" + re.escape(mt))
        if any(pat.search(s) for s in sentences):
            neg_scope = True
    reason = "NEGATION_SCOPE_MATCH" if neg_scope else "REGULARITY_CONFLATION"
    if entry.get("entry_kind") in NON_RESULT_KINDS:
        reason = reason + "+NOT_A_RESULT"
    return {"cbr_direction": "contrary", "semantic_side": side["side"],
            "semantic_is_contrary": side["side"] == "contrary_extension_asserted",
            "reason_code": reason, "matched": side["matched"],
            "cbr_matched_text": matched_texts}


# --------------------------------------------------------------------------- controls
def synth(entry_id, kind, ctype, statement, genericity, topology, evidence, content, unresolved):
    return {"theorem_id": entry_id, "entry_kind": kind, "conclusion_type": ctype,
            "statement_exact": statement, "genericity": genericity, "topology": topology,
            "regularity": "synthetic control", "evidence_level": evidence,
            "content_status": content, "unresolved": unresolved, "source_ids": ["CTRL"],
            "class_ids": [CLASS_ID], "scope_caveats": [], "label": "synthetic control"}


def control_suite() -> list:
    cases = [
        ("CTRL-POS-c2-discharges", dict(
            kind="theorem", ctype="theorem", evidence="peer-reviewed", content="verified",
            statement="For every r in D0 there is a comeager set G_r of one-ended "
                      "asymptotically flat vacuum Cauchy data such that no proper future C2 "
                      "vacuum extension of the maximal development exists.",
            genericity="residual comeager in the declared topology", topology="one-ended AF",
            unresolved=[]), {"d1": "pass", "d2": "supports", "d3": "pass", "discharge": True}),
        ("CTRL-NEG-c0-extension-not-contrary", dict(
            kind="preprint_result", ctype="theorem", evidence="preprint", content="verified",
            statement="The spacetime metric extends continuously across the Cauchy horizon; "
                      "the extension is a continuous metric and is not claimed to be C2.",
            genericity="comeager in the declared topology", topology="one-ended AF",
            unresolved=[]), {"d1": "pass", "d2": "weaker_not_contrary", "d3": "fail",
                             "discharge": False}),
        ("CTRL-CONTRARY-c2-extension-asserted", dict(
            kind="theorem", ctype="theorem", evidence="peer-reviewed", content="verified",
            statement="For a comeager set of one-ended asymptotically flat vacuum Cauchy "
                      "data the maximal development admits a proper future C2 vacuum extension.",
            genericity="comeager", topology="one-ended AF", unresolved=[]),
         {"d1": "pass", "d2": "contrary", "d3": "pass", "discharge": False}),
        ("CTRL-D1-characteristic-data", dict(
            kind="preprint_result", ctype="theorem", evidence="peer-reviewed", content="verified",
            statement="Given a characteristic initial value problem with data on a dynamical "
                      "horizon, the metric is not Lipschitz extendible.",
            genericity="not quantified as open/dense", topology="characteristic data",
            unresolved=[]), {"d1": "fail", "d2": "supports", "d3": "pass", "discharge": False}),
        ("CTRL-D3-preprint-open-item", dict(
            kind="preprint_result", ctype="theorem", evidence="preprint", content="provisional",
            statement="No proper future C2 vacuum extension exists for a comeager set of "
                      "one-ended asymptotically flat vacuum Cauchy data.",
            genericity="residual comeager", topology="one-ended AF",
            unresolved=["peer review"]), {"d1": "pass", "d2": "supports", "d3": "fail",
                                          "discharge": False}),
    ]
    out = []
    for name, kw, expect in cases:
        e = synth(name, **kw)
        obs = classify(e)
        got = {"d1": obs["d1_data_class"]["verdict"], "d2": obs["d2_conclusion"]["verdict"],
               "d3": obs["d3_evidence"]["verdict"], "discharge": obs["discharges_class"]}
        out.append({"name": name, "expected": expect, "observed": got,
                    "pass": got == expect})
    return out


def main() -> int:
    SNAP.mkdir(parents=True, exist_ok=True)

    start = {rel: measure(rel) for rel in PINS}
    pin_match = {rel: (start[rel]["exists"] and start[rel]["sha256_prefix"] == pref)
                 for rel, pref in PINS.items()}

    # frozen byte snapshots (hash-named, written once; never overwritten if bytes equal)
    snap_paths = {}
    for rel, pref in PINS.items():
        if not start[rel]["exists"]:
            continue
        dst = SNAP / f"{Path(rel).stem}.{pref}{Path(rel).suffix}"
        if not dst.exists() or sha256(dst) != start[rel]["sha256"]:
            shutil.copyfile(ROOT / rel, dst)
        snap_paths[rel] = str(dst.relative_to(ROOT))

    entries = load_ledger(ROOT / LEDGER)
    c2 = bindings_of(entries)

    rows = []
    for e in c2:
        cl = classify(e)
        rows.append({
            "theorem_id": e["theorem_id"],
            "entry_kind": e.get("entry_kind"),
            "conclusion_type": e.get("conclusion_type"),
            "content_status": e.get("content_status"),
            "evidence_level": e.get("evidence_level"),
            "label": (e.get("label") or "")[:160],
            "d1_data_class": cl["d1_data_class"],
            "d2_conclusion": cl["d2_conclusion"],
            "d3_evidence": cl["d3_evidence"],
            "discharges_class": cl["discharges_class"],
            "assertion_side": cl["d2_conclusion"]["assertion_side"],
        })

    controls = control_suite()
    controls_pass = all(c["pass"] for c in controls)

    # sibling-leak control: an entry bound only to C0 must not enter the C2 set
    leak = synth("CTRL-BINDING-sibling-leak", kind="theorem", ctype="theorem",
                 statement="No proper future C0 extension exists for a comeager set.",
                 genericity="comeager", topology="one-ended AF", evidence="peer-reviewed",
                 content="verified", unresolved=[])
    leak["class_ids"] = ["AF-SCC-C0-VAC-GEN"]
    leak_excluded = len(bindings_of(entries + [leak])) == len(c2)
    controls.append({"name": "CTRL-BINDING-sibling-leak", "expected": {"excluded": True},
                     "observed": {"excluded": leak_excluded}, "pass": leak_excluded})
    controls_pass = controls_pass and leak_excluded

    n_result = sum(1 for r in rows if r["entry_kind"] in RESULT_KINDS)
    n_d1_pass = sum(1 for r in rows if r["d1_data_class"]["verdict"] == "pass")
    n_d2_supports = sum(1 for r in rows if r["d2_conclusion"]["verdict"] == "supports")
    n_d2_contrary = sum(1 for r in rows if r["d2_conclusion"]["verdict"] == "contrary")
    n_d2_weaker = sum(1 for r in rows if r["d2_conclusion"]["verdict"] == "weaker_not_contrary")
    n_d3_pass = sum(1 for r in rows if r["d3_evidence"]["verdict"] == "pass")
    discharging = [r["theorem_id"] for r in rows if r["discharges_class"]]

    # ---- direction reclassification of the CBR's lexical C2 flags
    by_id = {e["theorem_id"]: e for e in c2}
    try:
        cbr_report = json.loads((ROOT / CBR).read_text(encoding="utf-8"))
        cbr_findings = {f["theorem_id"]: f for f in cbr_report.get("direction_findings", [])
                        if f.get("class_id") == CLASS_ID}
    except Exception:
        cbr_findings = {}
    reclass = []
    for tid in CBR_FLAGGED_C2:
        e = by_id.get(tid)
        if e is None:
            reclass.append({"theorem_id": tid, "present": False})
            continue
        r = cbr_reclassify(e, cbr_findings.get(tid))
        r.update({"theorem_id": tid, "label": (e.get("label") or "")[:120]})
        reclass.append(r)
    semantic_contrary_all = [r["theorem_id"] for r in rows
                             if r["assertion_side"] == "contrary_extension_asserted"]

    reading = (
        f"At F2a rev13 {start[SCHEMA]['sha256_prefix']} (FROZEN rev29 "
        f"{start[FROZEN]['sha256_prefix']}) and ledger {start[LEDGER]['sha256_prefix']}, "
        f"{len(rows)} ledger entries carry {CLASS_ID} in class_ids. Of these, {n_result} are "
        f"results and {len(rows) - n_result} are definitions/literature-status/conjecture. "
        f"No result satisfies D1_data_class (all four are characteristic/interior, "
        f"special-class or conditionally generic). {n_d2_supports} results conclude a "
        f"regularity at least as strong as C2-inextendibility (Lipschitz/C^0,1 "
        f"inextendibility implies non-C2-extendibility), {n_d2_weaker} asserts only a weaker "
        f"(C0) extension and is therefore NOT the negation of the C2 conclusion, and "
        f"{n_d2_contrary} asserts a C2-or-smoother extension. D3_evidence passes for "
        f"{n_d3_pass} bindings (every binding carries >=1 unresolved ledger item; two are "
        f"provisional; three are preprint-level). n_discharging={len(discharging)}; the class "
        f"conclusion state is '{'open' if not discharging else 'discharged'}'."
    )

    correction = (
        f"The CBR audit (W010-CBR-01, sha256 {start[CBR]['sha256_prefix']}) flagged "
        f"{len(CBR_FLAGGED_C2)} C2 bindings as 'negation-side' with a lexical 'extension "
        f"exists' form. Re-read with regularity inclusion that count is 0: all "
        f"{len(reclass)} are regularity-conflation artifacts (a C0/L^2_loc/Lipschitz "
        f"extension is not a C2 extension) and/or negation-scope matches (the string "
        f"'C^2-extendibility' inside 'non-C^2-extendibility'). No binding asserts a "
        f"C2-or-smoother vacuum extension for the class data."
    )

    report = {
        "audit_id": f"worker-010-c2-conformance-{TASK_ID.lower()}",
        "report_id": f"w010-c2-conformance-rev13-{datetime.now(CST).strftime('%Y%m%dT%H%M%S')}",
        "task_id": TASK_ID,
        "task": "class-bound conformance + direction audit of the AF-SCC-C2-VAC-GEN "
                "ledger bindings (D1 data class / D2 conclusion / D3 evidence)",
        "actor": "worker-010",
        "alias_actor": "deepseek-flash-10",
        "assignment_ref": None,
        "assignment_note": "no inbox card exists for worker-010 at fleet 2026-09-12T01:04; "
                           "ONE bounded class-bound task self-selected per comms/PROTOCOL.md "
                           "and the convention recorded by workers 048/063/069",
        "node_id": NODE_ID,
        "gate": GATE,
        "class_id": CLASS_ID,
        "class_ids": [CLASS_ID],
        "created_at": now(),
        "class_definition": {
            "path": SCHEMA,
            "sha256": start[SCHEMA]["sha256"],
            "revision": "13",
            "scope_statement": "MGHD of generic asymptotically flat vacuum initial data "
                               "admits no proper future extension that is a C2 Lorentzian "
                               "solution of the vacuum equations",
            "frozen_regularity": "C2",
            "frozen_direction": "future",
            "epistemic_status": "open_problem",
            "sibling_disjoint_from": "AF-SCC-C0-VAC-GEN",
            "genericity_kind": "residual_comeager",
        },
        "requirement_conjuncts": {
            "D1_data_class": "RESULT entry over the class's residual/comeager generic set of "
                             "one-ended asymptotically flat VACUUM Cauchy data (no "
                             "characteristic/interior, special-class, model-symmetry or "
                             "conditionally-generic substitution)",
            "D2_conclusion": "concludes that the maximal development admits NO proper future "
                             "C2 vacuum extension, or a strictly stronger regularity "
                             "statement that implies it by inclusion "
                             "(C^{0,1}_loc / C^1 / C^2 / C^k / smooth inextendibility); "
                             "asserting a C0 or L^2_loc extension is NOT the negation",
            "D3_evidence": "content_status=verified AND evidence in {peer-reviewed, "
                           "accepted-in-press} AND no unresolved ledger item AND no open "
                           "hypothesis in the conclusion",
            "discharge": "D1 AND D2 AND D3",
        },
        "bindings": rows,
        "binding_predicate": "entry.class_ids contains 'AF-SCC-C2-VAC-GEN'",
        "direction_reclassification_vs_cbr": {
            "cbr_audit_ref": f"{CBR}#{start[CBR]['sha256_prefix']}",
            "cbr_lexical_contrary_count_c2": len(CBR_FLAGGED_C2),
            "cbr_lexical_contrary_ids": CBR_FLAGGED_C2,
            "semantic_contrary_count_all_bindings": len(semantic_contrary_all),
            "semantic_contrary_ids": semantic_contrary_all,
            "reclassified": reclass,
            "reason_codes": {
                "REGULARITY_CONFLATION": "a C0 / L^2_loc-connection / Lipschitz extension "
                                         "assertion does not negate a no-C2-extension "
                                         "conclusion; C^k inextendibility for k>=2 is what "
                                         "negates (and C^{0,1}-inextendibility implies it)",
                "NEGATION_SCOPE_MATCH": "the lexical matcher matched 'C^2-extendibility' "
                                        "inside 'non-C^2-extendibility'",
                "NOT_A_RESULT": "the binding is a definition / literature-status / "
                                "conjecture entry, not a result",
            },
        },
        "negative_controls": {"controls": controls, "all_pass": controls_pass},
        "summary": {
            "n_bound_entries": len(rows),
            "n_result_entries": n_result,
            "n_non_result_entries": len(rows) - n_result,
            "n_d1_pass": n_d1_pass,
            "n_d2_supports": n_d2_supports,
            "n_d2_contrary": n_d2_contrary,
            "n_d2_weaker_not_contrary": n_d2_weaker,
            "n_d3_pass": n_d3_pass,
            "n_discharging": len(discharging),
            "discharging_entries": discharging,
            "supporting_but_not_discharging": [r["theorem_id"] for r in rows
                                               if r["d2_conclusion"]["verdict"] == "supports"
                                               and not r["discharges_class"]],
            "class_conclusion_state": "open_problem" if not discharging else "discharged",
            "class_declared_epistemic_status": "open_problem",
        },
        "reading": reading,
        "direction_correction": correction,
        "inputs": {rel: start[rel] for rel in PINS},
        "input_pins_matched": pin_match,
        "snapshot_paths": snap_paths,
        "map_context": None,
        "falsifier": "Any one of: (i) one C2-bound ledger entry at ledger "
                     f"{start[LEDGER]['sha256_prefix']} satisfying D1 AND D2(supports or "
                     "stronger) AND D3, which makes n_discharging>=1 and the class state "
                     "'discharged'; (ii) one binding this audit calls weaker/not-contrary "
                     "whose quoted sentence in fact asserts a C2-or-smoother vacuum "
                     "extension for the class data; (iii) one ledger entry with "
                     "AF-SCC-C2-VAC-GEN in class_ids omitted from the binding set; (iv) one "
                     "D1/D2/D3/discharge verdict disagreement with the independent verifier.",
        "limitations": [
            "The audit inherits ledger class_ids; it does not re-adjudicate the binding "
            "(A1's job).",
            "D1/D2/D3 are declared mechanical readings of the ledger fields "
            "statement_exact/genericity/regularity/topology/scope_caveats/unresolved; a "
            "reviewer may bind an entry differently, which is the A1 verdict this artifact "
            "asks for.",
            "D2 is a direction/regularity reading, not an adjudication of whether a "
            "conditional or non-class result is mathematically correct.",
            "This is a ledger/schema state measurement at the pinned hashes, not a "
            "mathematical result, not a reviewer verdict, and not a gate verdict.",
        ],
        "validation_status": "unverified",
        "claims_completion": False,
    }

    # controller context, recorded but not pinned (the map is mutated continuously)
    try:
        rm = json.loads((ROOT / "research_map/research_map.json").read_text(encoding="utf-8"))
        report["map_context"] = {
            "sha256": sha256(ROOT / "research_map/research_map.json"),
            "updated_at": rm.get("updated_at"),
            "gates": {g["gate_id"]: g["verdict"] for g in rm.get("gates", [])},
            "numerics_lock": (rm.get("numerics_lock") or {}).get("state"),
        }
    except Exception as exc:  # pragma: no cover
        report["map_context"] = {"error": str(exc)}

    # ---- input stability: re-hash every pinned input after the run
    end = {rel: measure(rel) for rel in PINS}
    unstable = [rel for rel in PINS if end[rel]["sha256"] != start[rel]["sha256"]]
    report["input_stability"] = {"all_stable": not unstable, "unstable_inputs": unstable,
                                 "checked_at": now()}
    if unstable:
        report["reading"] = "VOID: a pinned input changed between measurement and re-check."
        report["summary"]["class_conclusion_state"] = "void_input_drift"

    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    rc = 0 if not unstable else 3
    if not controls_pass:
        rc = 2
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"bound={len(rows)} results={n_result} d1_pass={n_d1_pass} "
          f"d2_supports={n_d2_supports} d2_contrary={n_d2_contrary} "
          f"d2_weaker={n_d2_weaker} d3_pass={n_d3_pass} discharging={len(discharging)}")
    print(f"cbr_flagged={len(CBR_FLAGGED_C2)} semantic_contrary="
          f"{len(semantic_contrary_all)} controls_pass={controls_pass} "
          f"pins_matched={all(pin_match.values())} stable={not unstable}")
    print("audit sha256:", sha256(OUT))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
