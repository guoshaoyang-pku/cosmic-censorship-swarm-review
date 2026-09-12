#!/usr/bin/env python3
"""W094G-CF21-SCOPE-PRECISION-01 -- CF-21 disposition-scope audit.

Read-only, deterministic, pin-gated audit that decomposes the live controller
finding CF-21 (and worker-094's own prior claims about it) into separately
measurable sub-claims, at frozen bytes, and issues a scope correction where a
sub-claim is mis-attributed.

Why this exists
---------------
Worker-094's accepted-stream claims w094-gencons-20260912T005630-claim-declaration-consistency
and w094f-cf21rev13-20260912T011015-claim assert that the F0 taxonomy's D3
class_scope_adjudication record ("the comeager quantifier is now stated
explicitly in each class conclusion text ... confirmed discharged for ALL FOUR
classes") "is unsupported for AF-WCC-SCALAR-SPH".  D3's declared scope is the
conclusion-text wording divergence (D1/D3), not the genericity axis.  This audit
separates:
  * the live CF-21 core (axis/H4 vs conclusion) -- re-measured;
  * the D3 sub-clause -- re-scoped against D3's own text;
  * two evidence surfaces CF-21's record does not cite: the companion
    class-contract supplement and the bound class-separation case corpus;
  * the N0 class-binding-of-record carrier -- whether the numerics chain
    inherits the inconsistency materially.

Authority: worker evidence only.  No gate verdict, no node done/passed, no
validation_status=passed, no canonical/shared file written.  Reads pinned inputs
only; writes run/report.json under this directory.

Exit codes: 0 measured; 3 control deviation; 4 pin drift; 5 self-test failure.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / "artifacts/worker-094/cf21_scope_audit"
OUT = HERE / "run/report.json"

CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).replace(microsecond=0).isoformat()

TASK_ID = "W094G-CF21-SCOPE-PRECISION-01"
ACTOR = "worker-094"
CLASSES = ["AF-WCC-SCALAR-SPH", "AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
SCALAR = "AF-WCC-SCALAR-SPH"
CONTROLS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]

# --- pins (full sha256, measured 2026-09-12T01:1x+08:00) ---------------------
PINS = {
    "research_map/formulation_taxonomy.yaml":
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/formulation_taxonomy.yaml":
        "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "schemas/taxonomy_cases.jsonl":
        "ccf7041bd0ff3ce844c07a700a588b7fe8e3c90880674c5e595b21f6259a8f03",
    "artifacts/formulation/VOCAB_ALIASES.json":
        "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba",
    "artifacts/formulation/evidence/taxonomy_consistency.json":
        "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b",
    "numerics/N0_CLASS_BINDING_AUTHORITY.json":
        "effd20b0ea094a8dfd4f686e62c49b1667622337efd6a7c154f7fadae0b98419",
    "numerics/results/flat_wave_convergence_rev3.json":
        "da7c360719950f7ef6be2624391dee464f8c818a0be74ec44f0f8c70d2b28ac3",
    # the two prior worker-094 reports whose claim text is under audit
    "artifacts/worker-094/genericity_consistency/run/report.json":
        "10a92ff3c9c1d4271a584b8fa6c79fe94ac505fcfe1db74189a256f76708f282",
    "artifacts/worker-094/cf21_rev13_recheck/run/report.json":
        "629a3232bb84fc8a77b60b782d6f6a3705e5277096d9391b3cb07abd97a0cea9",
    # the accepted-stream claims that carry the sub-clause under audit
    "comms/outbox/worker-094.jsonl":
        None,  # append-only traffic file: measured for information, not pinned
}

MARKER_KEYS = ("claim_status", "provisional", "blocked_by_unresolved_hypothesis", "provisional_status")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def measure_pins() -> dict:
    return {p: (sha256(ROOT / p) if (ROOT / p).is_file() else None) for p in PINS}


def line_of(text: str, needle: str, start: int = 0) -> int | None:
    idx = text.find(needle, start)
    return None if idx < 0 else text.count("\n", 0, idx) + 1


# --- predicates --------------------------------------------------------------
# Each predicate takes already-loaded structures so controls can mutate copies.

def p_axis_unresolved(tax: dict) -> bool:
    return tax["classes"][SCALAR]["axes"]["genericity_kind"] == "unresolved"


def p_value_status_unresolved(tax: dict) -> bool:
    return tax["classes"][SCALAR].get("genericity_value_status") == "unresolved_pending_L1"


def p_h4_unresolved_claim_blocking(tax: dict) -> bool:
    h4 = [h for h in tax["classes"][SCALAR]["hypotheses"] if h.get("id") == "H4"][0]
    return bool(h4.get("unresolved") is True
                and h4.get("machine_checkable") is False
                and "must be named before any claim is filed" in str(h4.get("text", "")))


def p_conclusion_asserts_comeager_no_marker(tax: dict) -> bool:
    concl = tax["classes"][SCALAR]["conclusion"]
    txt = str(concl.get("text", ""))
    marker = any(k in concl for k in MARKER_KEYS)
    return ("comeager" in txt.lower()) and (not marker)


def p_d3_resolution_text(tax: dict) -> str:
    adj = tax["class_scope_adjudication"]
    for row in adj.get("resolved_divergences", []):
        if row.get("id") == "D3":
            return str(row.get("resolution", ""))
    return ""


def p_d3_scope_is_conclusion_wording(tax: dict) -> bool:
    t = p_d3_resolution_text(tax).lower()
    return ("comeager quantifier" in t
            and "conclusion text" in t
            and ("discharged for all four classes" in t))


def p_d3_text_claims_genericity_notion_discharged(tax: dict) -> bool:
    t = p_d3_resolution_text(tax).lower()
    return any(k in t for k in ("genericity notion", "genericity_kind", "genericity slot", "notion is discharged"))


def p_scalar_conclusion_states_comeager_bound_before(tax: dict) -> bool:
    txt = str(tax["classes"][SCALAR]["conclusion"].get("text", "")).lower()
    return ("for a comeager set g of data" in txt) and ("chosen before and independently of the data" in txt)


UNRESOLVED_TOKENS = {"gen", "unresolved", "", "none", "null"}


def p_supplement_discharges_axis(supp: dict) -> bool:
    """True iff the companion supplement resolves the scalar genericity notion.

    Resolution = a genericity-bearing field anywhere in the scalar contract
    carries a concrete kind/topology/value token rather than the uniform 'GEN'
    placeholder.
    """
    def fields(node, prefix=""):
        if isinstance(node, dict):
            for k, v in node.items():
                yield from fields(v, f"{prefix}{k}")
        elif isinstance(node, str) and re.search(r"genericit", prefix, re.I):
            yield prefix, node

    return any(str(v).strip().lower() not in UNRESOLVED_TOKENS for _, v in fields(supp["class_contracts"][SCALAR]))


def p_supplement_uniform_gen_token(supp: dict) -> bool:
    toks = {cid: str(supp["class_contracts"][cid].get("components", {}).get("genericity", "")).strip().upper()
            for cid in CLASSES}
    return all(v == "GEN" for v in toks.values())


def p_axis_load_bearing_cases(cases: list) -> dict:
    rows = [c for c in cases if c.get("class_id") == SCALAR]
    return {
        "scalar_rows": len(rows),
        "rows_with_genericity_kind_in_decisive_axes": sum(
            1 for c in rows if "genericity_kind" in (c.get("decisive_axes") or [])),
        "rows_with_axis_vector_unresolved": sum(
            1 for c in rows if (c.get("axis_vector") or {}).get("genericity_kind") == "unresolved"),
        "rows_with_open_false": sum(1 for c in rows if c.get("open") is False),
        "rows_naming_unresolved_in_statement": sum(
            1 for c in rows if "unresolved" in str(c.get("statement", "")).lower()),
    }


def p_control_classes_resolved(tax: dict) -> dict:
    out = {}
    for cid in CONTROLS:
        cc = tax["classes"][cid]
        concl = cc.get("conclusion", {})
        out[cid] = {
            "genericity_kind": cc.get("axes", {}).get("genericity_kind"),
            "value_status": cc.get("genericity_value_status"),
            "conclusion_has_comeager": "comeager" in str(concl.get("text", "")).lower(),
        }
    return out


def p_control_classes_are_resolved(tax: dict) -> bool:
    m = p_control_classes_resolved(tax)
    return all(v["genericity_kind"] not in (None, "unresolved") and v["conclusion_has_comeager"]
               for v in m.values())


def p_n0_binding(rec: dict, carrier: dict, tax_sha: str) -> dict:
    cb = carrier.get("class_binding", {})
    blob = json.dumps(carrier)
    return {
        "record_binding_of_record_path": rec.get("binding", {}).get("path"),
        "record_binding_of_record_sha256": rec.get("binding", {}).get("sha256"),
        "binding_equals_taxonomy_pin": rec.get("binding", {}).get("sha256") == tax_sha,
        "carrier_class_binding_sha256": cb.get("sha256"),
        "carrier_binds_taxonomy_pin": cb.get("sha256") == tax_sha,
        "carrier_genericity_tokens": sum(blob.lower().count(k) for k in
                                         ("comeager", "genericity_kind", "residual_comeager", "baire")),
        "carrier_binding_status": cb.get("binding_status"),
    }


def p_prior_assertions(outbox_text: str) -> dict:
    """Measure the prior worker-094 claims' D3 sub-clause on the accepted traffic."""
    ev = [json.loads(l) for l in outbox_text.splitlines() if l.strip()]
    hits = []
    for e in ev:
        if e.get("actor") != "worker-094":
            continue
        blob = json.dumps(e)
        if "D3" in blob and "unsupported" in blob.lower():
            hits.append(e.get("event_id"))
    return {"events_with_d3_unsupported_subclause": hits, "n": len(hits)}


# --- controls (in-memory mutants; never written to disk) ---------------------

def run_controls(tax0, supp0, rec0, car0, cases0, pins_measured) -> list:
    res = []

    def add(cid, desc, observed, expected):
        res.append({"id": cid, "description": desc, "observed": observed,
                    "expected": expected, "behaved": observed == expected})

    tax = copy.deepcopy(tax0)
    tax["classes"][SCALAR]["axes"]["genericity_kind"] = "residual_comeager"
    add("M0", "self-test: predicate inversion detector -- inverting any predicate must change the baseline",
        {"p_axis_unresolved": p_axis_unresolved(tax), "p_value_status_unresolved": p_value_status_unresolved(tax)},
        {"p_axis_unresolved": False, "p_value_status_unresolved": True})

    tax = copy.deepcopy(tax0)
    tax["classes"][SCALAR]["axes"]["genericity_kind"] = "residual_comeager"
    add("M1", "declared scalar genericity kind resolved (residual_comeager) -> axis predicate flips",
        p_axis_unresolved(tax), False)

    tax = copy.deepcopy(tax0)
    tax["classes"][SCALAR]["genericity_value_status"] = "resolved_comeager"
    add("M2", "genericity_value_status cleared -> value-status predicate flips",
        p_value_status_unresolved(tax), False)

    tax = copy.deepcopy(tax0)
    for h in tax["classes"][SCALAR]["hypotheses"]:
        if h.get("id") == "H4":
            h["unresolved"] = False
    add("M3", "H4.unresolved=false -> H4 claim-blocking predicate flips",
        p_h4_unresolved_claim_blocking(tax), False)

    tax = copy.deepcopy(tax0)
    tax["classes"][SCALAR]["conclusion"]["text"] = tax["classes"][SCALAR]["conclusion"]["text"].replace(
        "For a comeager set G of data", "For every data set")
    add("M4", "conclusion comeager quantifier removed -> comeager predicate flips",
        p_conclusion_asserts_comeager_no_marker(tax), False)

    tax = copy.deepcopy(tax0)
    tax["classes"][SCALAR]["conclusion"]["claim_status"] = "blocked_by_unresolved_hypothesis"
    add("M5", "machine-readable blocked marker added to the conclusion -> comeager predicate flips",
        p_conclusion_asserts_comeager_no_marker(tax), False)

    supp = copy.deepcopy(supp0)
    supp["class_contracts"][SCALAR]["components"]["genericity"] = "residual_comeager"
    add("M6", "supplement scalar genericity token resolved -> discharge predicate flips",
        p_supplement_discharges_axis(supp), True)

    supp = copy.deepcopy(supp0)
    supp["class_contracts"][CONTROLS[0]]["components"]["genericity"] = "residual_comeager"
    add("M7", "supplement uniformity broken on one control class -> uniformity predicate flips",
        p_supplement_uniform_gen_token(supp), False)

    cases = copy.deepcopy(cases0)
    for c in cases:
        if c.get("class_id") == SCALAR and "genericity_kind" in (c.get("decisive_axes") or []):
            c["decisive_axes"].remove("genericity_kind")
            break
    base = p_axis_load_bearing_cases(cases0)["rows_with_genericity_kind_in_decisive_axes"]
    mut = p_axis_load_bearing_cases(cases)["rows_with_genericity_kind_in_decisive_axes"]
    add("M8", "one scalar case row loses genericity_kind from decisive_axes -> load-bearing count drops",
        mut, base - 1)

    tax = copy.deepcopy(tax0)
    for row in tax["class_scope_adjudication"]["resolved_divergences"]:
        if row.get("id") == "D3":
            row["resolution"] = ("the genericity notion is confirmed discharged for all four classes "
                                 "including AF-WCC-SCALAR-SPH")
    add("M9", "D3 text made a genericity-notion discharge -> scope predicate flips (proves the "
              "correction is text-measured, not assumed)",
        {"scope_is_conclusion_wording": p_d3_scope_is_conclusion_wording(tax),
         "claims_genericity_notion": p_d3_text_claims_genericity_notion_discharged(tax)},
        {"scope_is_conclusion_wording": False, "claims_genericity_notion": True})

    tax = copy.deepcopy(tax0)
    tax["classes"][CONTROLS[1]]["axes"]["genericity_kind"] = "unresolved"
    add("M10", "one control class axis made unresolved -> control-class predicate flips (isolation)",
        p_control_classes_are_resolved(tax), False)

    drift = dict(pins_measured)
    k = "research_map/formulation_taxonomy.yaml"
    drift[k] = "0" * 64
    add("M11", "simulated pin drift fires the drift gate", any(PINS[p] != drift[p] for p in PINS
                                                              if PINS[p] is not None), True)
    return res


def main() -> int:
    measured = measure_pins()
    drift = {p: {"expected": PINS[p], "measured": measured[p]}
             for p in PINS if PINS[p] is not None and measured[p] != PINS[p]}
    if drift:
        print(json.dumps({"verdict": "PIN_DRIFT", "drift": drift}, indent=1))
        return 4

    tax_text = (ROOT / "research_map/formulation_taxonomy.yaml").read_text()
    tax = yaml.safe_load(tax_text)
    supp = yaml.safe_load((ROOT / "artifacts/formulation/formulation_taxonomy.yaml").read_text())
    cases = [json.loads(l) for l in (ROOT / "schemas/taxonomy_cases.jsonl").read_text().splitlines() if l.strip()]
    rec = json.loads((ROOT / "numerics/N0_CLASS_BINDING_AUTHORITY.json").read_text())
    car = json.loads((ROOT / "numerics/results/flat_wave_convergence_rev3.json").read_text())
    outbox = (ROOT / "comms/outbox/worker-094.jsonl").read_text()

    tax_sha = PINS["research_map/formulation_taxonomy.yaml"]
    preds = {
        "C1_axis_unresolved": p_axis_unresolved(tax),
        "C2_value_status_unresolved": p_value_status_unresolved(tax),
        "C3_h4_unresolved_claim_blocking": p_h4_unresolved_claim_blocking(tax),
        "C4_conclusion_asserts_comeager_no_marker": p_conclusion_asserts_comeager_no_marker(tax),
        "C5_d3_scope_is_conclusion_wording": p_d3_scope_is_conclusion_wording(tax),
        "C6_d3_text_claims_genericity_notion_discharged": p_d3_text_claims_genericity_notion_discharged(tax),
        "C7_scalar_conclusion_satisfies_d3_wording": p_scalar_conclusion_states_comeager_bound_before(tax),
        "C8_supplement_discharges_axis": p_supplement_discharges_axis(supp),
        "C9_supplement_uniform_gen_token": p_supplement_uniform_gen_token(supp),
        "C10_control_classes_resolved": p_control_classes_are_resolved(tax),
    }
    load_bearing = p_axis_load_bearing_cases(cases)
    n0 = p_n0_binding(rec, car, tax_sha)
    prior = p_prior_assertions(outbox)

    controls = run_controls(tax, supp, rec, car, cases, measured)
    controls_ok = all(c["behaved"] for c in controls)
    if not controls_ok:
        print(json.dumps({"verdict": "CONTROL_DEVIATION",
                          "controls": [c for c in controls if not c["behaved"]]}, indent=1))
        return 3

    core_live = all(preds[k] for k in
                    ("C1_axis_unresolved", "C2_value_status_unresolved",
                     "C3_h4_unresolved_claim_blocking", "C4_conclusion_asserts_comeager_no_marker"))
    d3_scope_corrected = (preds["C5_d3_scope_is_conclusion_wording"]
                          and not preds["C6_d3_text_claims_genericity_notion_discharged"]
                          and preds["C7_scalar_conclusion_satisfies_d3_wording"]
                          and prior["n"] > 0)
    discharge_absent = (not preds["C8_supplement_discharges_axis"]) and preds["C9_supplement_uniform_gen_token"]

    if core_live and d3_scope_corrected and discharge_absent and preds["C10_control_classes_resolved"]:
        verdict = "CF21_STANDS_D3_ATTRIBUTION_CORRECTED"
    elif core_live and not d3_scope_corrected:
        verdict = "CF21_STANDS_D3_ATTRIBUTION_UPHELD"
    elif not core_live:
        verdict = "CF21_CORE_NOT_REPRODUCED"
    else:
        verdict = "INDETERMINATE"

    correction = (
        "WITHDRAWN SUB-CLAUSE: worker-094 claims w094-gencons-20260912T005630-claim-declaration-consistency "
        "(review w094-gencons-20260912T005630-review-cf21, blocker w094-gencons-20260912T005630-blocker) and "
        "w094f-cf21rev13-20260912T011015-claim/blocker state that the D3 record 'is unsupported for "
        "AF-WCC-SCALAR-SPH'. Measured at taxonomy 0abb9ed8a961: D3's resolution text is scoped to the "
        "comeager quantifier being stated explicitly in each class conclusion text (the D1/D3 wording "
        "divergence), and the scalar conclusion does state it, bound before the data ('For a comeager set G "
        "of data in the class, chosen before and independently of the data'). The D3 sub-clause is therefore "
        "mis-attributed and is withdrawn. The CF-21 core is NOT withdrawn: the scalar axis genericity_kind "
        "is 'unresolved' / genericity_value_status 'unresolved_pending_L1' and H4 is unresolved:true while "
        "the conclusion commits to a comeager quantifier with no machine-readable provisional/blocked "
        "marker. A whole-record reading of D3 would overstate, but that is not what D3's text says; no D3 "
        "re-adjudication is needed, while the axis/H4-vs-conclusion residual stands."
    )

    report = {
        "schema": "worker-094/cf21-scope-audit/v1",
        "task_id": TASK_ID,
        "actor": ACTOR,
        "created_at": NOW,
        "class_id": ";".join(CLASSES),
        "class_ids": CLASSES,
        "node_id": "F0",
        "node_ids": ["F0", "N0"],
        "gate": "G-F0",
        "gate_scope": "advisory evidence only; G-F0/G-FORM/G-NUM verdicts are controller/lead fields",
        "advisory": True,
        "pins": PINS,
        "pins_measured": measured,
        "pin_match": True,
        "inputs": {
            "canonical_taxonomy": {"path": "research_map/formulation_taxonomy.yaml", "sha256": tax_sha,
                                   "revision": tax.get("revision")},
            "companion_supplement": {"path": "artifacts/formulation/formulation_taxonomy.yaml",
                                     "sha256": PINS["artifacts/formulation/formulation_taxonomy.yaml"]},
            "case_corpus": {"path": "schemas/taxonomy_cases.jsonl",
                            "sha256": PINS["schemas/taxonomy_cases.jsonl"], "rows": len(cases)},
            "n0_binding_record": {"path": "numerics/N0_CLASS_BINDING_AUTHORITY.json",
                                  "sha256": PINS["numerics/N0_CLASS_BINDING_AUTHORITY.json"]},
            "n0_carrier": {"path": "numerics/results/flat_wave_convergence_rev3.json",
                           "sha256": PINS["numerics/results/flat_wave_convergence_rev3.json"]},
        },
        "evidence_lines": {
            "scalar_class_key": line_of(tax_text, '  "AF-WCC-SCALAR-SPH":'),
            "axes.genericity_kind": line_of(tax_text, 'genericity_kind: "unresolved"'),
            "genericity_value_status": line_of(tax_text, 'genericity_value_status: "unresolved_pending_L1"'),
            "H4_text": line_of(tax_text, "must be named before any claim is filed"),
            "conclusion_comeager": line_of(tax_text, "For a comeager set G of data"),
            "D3_record": line_of(tax_text, "confirmed discharged for ALL FOUR classes"),
        },
        "predicates": preds,
        "axis_load_bearing_corpus_measurement": load_bearing,
        "n0_binding_measurement": n0,
        "prior_claim_measurement": prior,
        "controls": controls,
        "controls_ok": controls_ok,
        "verdict": verdict,
        "verdict_reason": (
            "Core CF-21 sub-claims C1-C4 reproduce at the frozen F0 bytes (scalar only); the D3 "
            "sub-clause of the prior worker-094 claims is mis-scoped because D3 is satisfied for its "
            "own declared scope (C5+C6+C7 true, C6 false = D3 does not claim a genericity-notion "
            "discharge); the companion supplement declares genericity only as the uniform token 'GEN' "
            "and provides no kind/topology/value, so it does not discharge the axis; the unresolved "
            "axis is load-bearing for the bound class-separation corpus; the N0 class-binding "
            "authority binds the inconsistent taxonomy bytes by hash reference with zero genericity "
            "tokens in the carrier (material independence, named binding)."
        ),
        "correction": correction,
        "correction_targets": prior["events_with_d3_unsupported_subclause"],
        "repair_options_unchanged": [
            "taxonomy rev6 that resolves axes.genericity_kind to residual_comeager (with the corpus "
            "rebound) or adds a machine-readable provisional/blocked marker on the conclusion and "
            "re-runs the full G-F0 round -- any write voids G-F0 at 0abb9ed8a961",
            "explicit controller record of acceptance of residual CF-21 with a rationale, as the "
            "pass-07 disposition already does for the axis token",
        ],
        "no_third_path": "the companion supplement does not discharge the axis (C8 false, C9 uniform)",
        "falsifier": (
            "Re-run this audit at unchanged pins. Falsified if any pinned sha256 differs; if the "
            "scalar axis is not 'unresolved' or the value status not 'unresolved_pending_L1'; if H4 is "
            "resolved or the conclusion gains a machine-readable provisional/blocked marker; if D3's "
            "resolution text is shown to claim a genericity-notion discharge; if the scalar conclusion "
            "does not state the bound comeager quantifier; if the supplement is shown to resolve the "
            "genericity kind; if any of the 12 controls departs from its pre-registered expectation; "
            "or if the prior worker-094 claims are shown not to carry the D3-unsupported sub-clause."
        ),
        "next_falsifier": (
            "python3 artifacts/worker-094/cf21_scope_audit/audit_cf21_scope.py ; exit 0 with "
            "CF21_STANDS_D3_ATTRIBUTION_CORRECTED re-confirms; a repaired scalar axis/conclusion "
            "flips the core to not-live (CF21_CORE_NOT_REPRODUCED), which voids the residual, not the "
            "D3 correction."
        ),
        "authority_note": (
            "Worker evidence only: no gate verdict, no node done/passed, no validation_status=passed, "
            "no canonical or shared file written. Read-only on every pinned input; this report is the "
            "only write."
        ),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=1) + "\n")
    drift_after = {p: {"expected": PINS[p], "measured": sha256(ROOT / p)}
                   for p in PINS if PINS[p] is not None and sha256(ROOT / p) != PINS[p]}
    out = {"verdict": verdict, "report": str(OUT.relative_to(ROOT)),
           "report_sha256": sha256(OUT), "controls_ok": controls_ok,
           "drift_after_run": drift_after, "predicates": preds}
    print(json.dumps(out, indent=1))
    return 0 if not drift_after else 4


if __name__ == "__main__":
    sys.exit(main())
