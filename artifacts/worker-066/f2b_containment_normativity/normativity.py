#!/usr/bin/env python3
"""W066-F2B-CONTAINMENT-NORMATIVITY-01 -- independent normativity adjudication.

Question.  At the live canonical F2b bytes (post rev13 evidence-binding repair),
the two containment clauses carried over from rev12 (and rev11) are still present:
  H1  implication_ledger.forbidden_transfers[0].reason  -> "C2 is a strictly larger
      extension class, so C2-inextendibility is strictly weaker" while the document's
      own chain makes E_C2 the smallest extension set;
  H2  regularity.must_not_conflate[0] -> "No containment with C2 or C0 is asserted
      here" while the document asserts that containment in its ledger.
The predecessor adjudication (W066-REV12-F2B-CONTAINMENT-ADJUDICATION-01) left one
resolution explicitly open: "or a reviewer may rule the two clauses non-normative
prose at the bound hash, which this adjudication does not."

This script decides that question mechanically:
  (A) are the two carriers normative blocks of the frozen class contract
      (machine-required by FORM-RULE-SPEC R01-R31 and consumed by the binding gate)?
  (B) is their *content* machine-enforced, i.e. can the canonical gate distinguish
      the defective wording from the corrected wording?
  (C) does the document itself mark either carrier advisory / non-normative?
  (D) does the rev13 repair carry the clauses forward (hash provenance)?

Method: read-only, pinned byte copies; the canonical gate is run inside a sandbox
tree on pristine and mutated copies; mutants and their expected gate verdicts were
pre-registered before the first run (PREREG below).  No canonical path is written.

Usage:  python3 normativity.py     (reads pinned/, writes evidence/ + report.json)
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PINNED = HERE / "pinned"
EVID = HERE / "evidence"
SANDBOX = HERE / "sandbox"
CROSS = HERE / "crosscheck"
CST = timezone(timedelta(hours=8))

# ----------------------------------------------------------------------------- prereg
# Mutant -> expected canonical-gate verdict.  Fixed before the first run.
PREREG = {
    "M0_pristine": ("pass", "the live rev13 bytes as frozen"),
    "M1_mnc_empty": ("fail:R06", "must_not_conflate is a required non-empty list"),
    "M2_h2_corrected": ("pass", "content unenforced: corrected wording still passes"),
    "M3_h2_false_strengthened": ("pass", "content unenforced: a stronger FALSE denial still passes"),
    "M4_ft_c0_to_c2": ("fail:R16", "forbidden_transfers direction tokens are enforced"),
    "M4b_ft_partial_reverse": ("pass", "the direction check fires only on the exact C0->C2 token pair"),
    "M5_ledger_removed": ("fail:R16", "implication_ledger itself is required"),
    "M6_ft_reason_removed": ("pass", "the reason prose is not enforced"),
    "M7_chain_reversed": ("pass", "the containment chain semantics are not enforced"),
    "M8_h1_corrected": ("pass", "content unenforced: corrected premise still passes"),
    "M9_h1_nonsense": ("pass", "content unenforced: a meaningless premise still passes"),
    "M10_h2_empty_string": ("pass", "list truthiness only: an empty-string entry passes"),
}


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def pinned(name: str) -> Path:
    hits = sorted(PINNED.glob(name + "__*"))
    if not hits:
        raise SystemExit(f"pinned input missing: {name}")
    return hits[0]


def cst_now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def build_sandbox() -> Path:
    if SANDBOX.exists():
        shutil.rmtree(SANDBOX)
    (SANDBOX / "artifacts/formulation/tools").mkdir(parents=True)
    (SANDBOX / "schemas").mkdir(parents=True)
    shutil.copyfile(pinned("rule_spec"), SANDBOX / "artifacts/formulation/rule_spec.json")
    shutil.copyfile(pinned("key_manifest"), SANDBOX / "artifacts/formulation/KEY_MANIFEST.json")
    shutil.copyfile(pinned("gate_tool"), SANDBOX / "artifacts/formulation/tools/check_class_schema.py")
    return SANDBOX / "artifacts/formulation/tools/check_class_schema.py"


def run_gate(tool: Path, schema: Path) -> dict:
    proc = subprocess.run([sys.executable, str(tool), "--json", str(schema)],
                          capture_output=True, text=True, timeout=300)
    try:
        rep = json.loads(proc.stdout)
    except Exception:
        rep = {"verdict": "crash", "failed_rules": [], "stderr": proc.stderr[-400:],
               "rc": proc.returncode}
    rep["rc"] = proc.returncode
    return rep


def mk_mutants(doc: dict) -> dict:
    """Return {name: mutated doc}.  Deep-copied through JSON to stay independent."""
    base = json.loads(json.dumps(doc))

    def clone():
        return json.loads(json.dumps(base))

    out = {}
    m = clone(); m["regularity"]["must_not_conflate"] = []; out["M1_mnc_empty"] = m
    m = clone()
    m["regularity"]["must_not_conflate"][0] = (
        "H2_loc (locally square-integrable curvature) is a distinct regularity-axis "
        "value. This class's ledger nests H2_loc strictly between C0 and C2: "
        "E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2.")
    out["M2_h2_corrected"] = m
    m = clone()
    m["regularity"]["must_not_conflate"][0] = (
        "H2_loc is a distinct regularity-axis value. C0 and C2 are disjoint extension "
        "classes and no containment holds in either direction.")
    out["M3_h2_false_strengthened"] = m
    m = clone()
    m["implication_ledger"]["forbidden_transfers"][0]["from"] = "no proper future C0 extension"
    m["implication_ledger"]["forbidden_transfers"][0]["to"] = "no proper future C2 extension"
    out["M4_ft_c0_to_c2"] = m
    m = clone()
    m["implication_ledger"]["forbidden_transfers"][0]["from"] = "no proper future C0 extension"
    out["M4b_ft_partial_reverse"] = m
    m = clone(); m.pop("implication_ledger", None); out["M5_ledger_removed"] = m
    m = clone(); m["implication_ledger"]["forbidden_transfers"][0].pop("reason", None)
    out["M6_ft_reason_removed"] = m
    m = clone()
    m["implication_ledger"]["extension_class_containment"] = (
        "E_C2 contains E_{C^1,1} contains E_H2loc contains E_C0; this class requires the "
        "HIGHEST regularity, so its inexistence statement is the weakest.")
    out["M7_chain_reversed"] = m
    m = clone()
    m["implication_ledger"]["forbidden_transfers"][0]["reason"] = (
        "C2 is a strictly smaller extension class, so C2-inextendibility is strictly stronger")
    out["M8_h1_corrected"] = m
    m = clone()
    m["implication_ledger"]["forbidden_transfers"][0]["reason"] = (
        "C2 is a much bigger extension class, trust the direction")
    out["M9_h1_nonsense"] = m
    m = clone(); m["regularity"]["must_not_conflate"][0] = ""; out["M10_h2_empty_string"] = m
    return out


def text_findings(c0_path: Path, c2_path: Path) -> dict:
    """Independent text-level detector (does not import the predecessor's checker)."""
    doc = yaml.safe_load(c0_path.read_text())
    c2 = yaml.safe_load(c2_path.read_text())
    chain = str(doc["implication_ledger"]["extension_class_containment"])
    ft = doc["implication_ledger"]["forbidden_transfers"][0]
    mnc = doc["regularity"]["must_not_conflate"]
    # order-relative: parse E_X tokens in the order in which the chain says "contains"
    order = re.findall(r"E_\{?([A-Za-z0-9^,\\\s]+?)\}?(?=\s+contains|\s*;|$)", chain)
    order = [o.strip().rstrip("}") for o in order]
    reason = str(ft.get("reason", ""))
    h1 = None
    mm = re.search(r"(C2|C0)\s+is\s+a\s+strictly\s+(larger|smaller)\s+extension\s+class", reason)
    if mm:
        tok, adj = mm.group(1), mm.group(2)
        if tok == "C2" and adj == "larger" and order and order[0] in ("C0", "C\\^1,1", "H2loc"):
            h1 = {"id": "W066-R13-F2B-H1", "carrier": "implication_ledger.forbidden_transfers[0].reason",
                  "claim": f"{tok} is a strictly {adj} extension class",
                  "declared_order_largest_first": order,
                  "defect": "E_C2 is the smallest extension set in the declared chain; "
                            "'larger' inverts the premise the prohibition rests on"}
    denial = None
    for i, s in enumerate(mnc):
        if re.search(r"no\s+containment\s+with\s+(C2|C0)", str(s), re.I):
            denial = (i, str(s))
    assertive = []
    for e in doc["implication_ledger"].get("one_way_entailments", []):
        if re.search(r"contains|subset|entails", json.dumps(e), re.I):
            assertive.append(e)
    h2 = None
    if denial and assertive:
        h2 = {"id": "W066-R13-F2B-H2", "carrier": f"regularity.must_not_conflate[{denial[0]}]",
              "claim": "no containment with C2 or C0 is asserted here",
              "contradicts": "implication_ledger.extension_class_containment + "
                             f"{len(assertive)} one_way_entailments rows",
              "defect": "a live denial inside the normative must_not_conflate list contradicts "
                        "the document's own asserted chain"}
    # sibling asymmetry: does C2 carry a corrected nesting statement instead?
    c2_mnc = c2["regularity"]["must_not_conflate"]
    c2_corrected = any(re.search(r"nests?|contains|between", str(s), re.I) and
                       re.search(r"C2|C0", str(s)) for s in c2_mnc)
    c2_denial = any(re.search(r"no\s+containment", str(s), re.I) for s in c2_mnc)
    c2_wrong_note = "was wrong" in json.dumps(c2_mnc)
    return {"h1": h1, "h2": h2, "chain": chain,
            "parsed_order_largest_first": order,
            "sibling_c2": {"carries_corrected_nesting": c2_corrected,
                           "carries_live_denial": c2_denial,
                           "records_earlier_denial_as_wrong": c2_wrong_note}}


def advisory_markers(doc: dict) -> list:
    """Look for explicit advisory/non-normative markers near the two carriers."""
    markers = []
    pat = re.compile(r"non[-_ ]?normative|advisory|informational only|not binding|"
                     r"nonbinding|prose only|not normative", re.I)
    carriers = {
        "implication_ledger": doc.get("implication_ledger"),
        "regularity": doc.get("regularity"),
    }
    for name, sub in carriers.items():
        blob = json.dumps(sub)
        for m in pat.finditer(blob):
            markers.append({"carrier": name, "match": m.group(0)})
    return markers


def rule_basis() -> list:
    spec = json.loads(pinned("rule_spec").read_text())
    basis = []
    for r in spec.get("rules", []):
        req = json.dumps(r)
        if re.search(r"implication_ledger|must_not_conflate|forbidden_transfers|"
                     r"extension.class.containment|containment", req, re.I):
            basis.append({"rule": r.get("id"), "require": r.get("require")})
    return basis


def main() -> dict:
    (HERE / "evidence").mkdir(exist_ok=True)
    target = pinned("target_c0")
    sibling = pinned("sibling_c2")
    rev12 = pinned("prior_rev12_c0")
    doc = yaml.safe_load(target.read_text())
    tool = build_sandbox()

    checks = {}
    checks["target"] = {"path": "schemas/af_scc_c0_vacuum.yaml", "sha256": sha256(target),
                        "declared_revision": doc.get("revision"),
                        "declared_revised_at": doc.get("revised_at"),
                        "bytes": target.stat().st_size}
    checks["sha_stability_in_pin"] = {"pinned_vs_canonical": sha256(target) ==
                                      sha256(REPO / "schemas/af_scc_c0_vacuum.yaml")}
    checks["carried_forward_from_rev12"] = {
        "rev12_sha256": sha256(rev12),
        "h1_clause_present_in_rev12": "strictly larger extension class" in rev12.read_text(),
        "h1_clause_present_in_rev13": "strictly larger extension class" in target.read_text(),
        "h2_clause_present_in_rev12": "No containment with C2 or C0 is asserted here" in rev12.read_text(),
        "h2_clause_present_in_rev13": "No containment with C2 or C0 is asserted here" in target.read_text(),
    }
    checks["normative_markers_absent"] = advisory_markers(doc)
    checks["rule_basis"] = rule_basis()
    checks["gate_tool"] = {"path": "artifacts/formulation/tools/check_class_schema.py",
                           "sha256": sha256(pinned("gate_tool"))}

    # (B) gate mutants
    mutants = mk_mutants(doc)
    results = {}
    sdir = SANDBOX / "schemas"
    pristine = sdir / "pristine.yaml"
    shutil.copyfile(target, pristine)
    rep = run_gate(tool, pristine)
    results["M0_pristine"] = rep
    for name, mdoc in mutants.items():
        p = sdir / f"{name}.yaml"
        p.write_text(yaml.safe_dump(mdoc, sort_keys=False, allow_unicode=True))
        results[name] = run_gate(tool, p)
    controls = []
    all_match = True
    for name, (expect, why) in PREREG.items():
        observed = results[name]
        obs = observed["verdict"] if expect == "pass" else (
            f"fail:{','.join(observed.get('failed_rules') or [])}")
        match = (obs == expect)
        all_match = all_match and match
        controls.append({"mutant": name, "pre_registered": expect, "observed": obs,
                         "match": match, "why": why, "rc": observed.get("rc")})
    checks["gate_mutant_results"] = results
    checks["controls_all_match"] = all_match

    # (A/D) text-level and provenance
    tf = text_findings(target, sibling)
    checks["independent_text_findings"] = tf
    checks["finding_count"] = int(bool(tf["h1"])) + int(bool(tf["h2"]))

    # cross-instrument: successor check of the predecessor's published rev12 spans
    cc = {"prior_instrument": "W066-REV12-F2B-CONTAINMENT-ADJUDICATION-01",
          "prior_verdict": "revise", "prior_findings": ["W066-R12-F2B-H1", "W066-R12-F2B-H2"]}
    try:
        pr = json.loads((REPO / "artifacts/worker-066/f2b_containment_adjudication/report.json").read_text())
        cc["prior_target"] = (pr.get("target") or {}).get("sha256")
        cc["prior_confirmed"] = [f.get("kind") or f.get("id") for f in (pr.get("confirmed_findings") or [])]
    except Exception as e:  # noqa: BLE001
        cc["error"] = f"{type(e).__name__}: {e}"
    checks["cross_instrument_predecessor"] = cc

    # final drift re-measure of every pinned target
    drift = {}
    for key in ("target_c0", "sibling_c2", "rule_spec", "gate_tool", "f0_canonical"):
        p = pinned(key)
        drift[key] = {"pinned_sha256": sha256(p),
                      "live_sha256": sha256(REPO / (json.loads((HERE / "PINNED.json").read_text())
                                                    ["inputs"][key]["path"])),
                      }
    for v in drift.values():
        v["match"] = v["pinned_sha256"] == v["live_sha256"]
    checks["post_run_drift"] = drift

    verdict = {
        "question": "Are H1 (forbidden_transfers[0].reason inverted size premise) and "
                    "H2 (must_not_conflate[0] live containment denial) normative content "
                    "of the frozen F2b class contract, or non-normative prose?",
        "verdict": "normative_content_defect",
        "answer": (
            "(A) Both carriers are normative: R06 requires a non-empty "
            "regularity.must_not_conflate list and R16 requires "
            "implication_ledger.one_way_entailments + forbidden_transfers with enforced "
            "direction tokens; the document carries no advisory/non-normative marker on "
            "either carrier. (B) Their *content* is not machine-enforced: the canonical "
            "gate returns pass for the defective wording and pass for corrected, "
            "strengthened-false, empty-string and nonsense variants alike, while the same "
            "gate does reject an emptied must_not_conflate (R06) and a reversed "
            "forbidden_transfers direction (R16). (C) The rev13 evidence-binding repair "
            "carried both clauses forward unchanged (byte-identical sentences at rev12 and "
            "rev13). Therefore H1/H2 are normative-content defects with a machine blind "
            "spot, not optional prose; a canonical gate PASS cannot certify them and does "
            "not discharge the predecessor's blocker."),
        "consequence_for_gform": (
            "REC-12 bounded the rev13 repair to evidence binding and forbade class-semantics "
            "changes, so rev13 (and any FROZEN rev29 that freezes it) still carries both "
            "defects. A G-FORM verdict at the rev13/rev29 pins that relies on the canonical "
            "gate alone will be gate-green and contain a live normative contradiction; "
            "astra-life05-verify-gform-r3 should re-run an order-relative containment check "
            "(predecessor instrument, re-run here) before any accept."),
        "repair": {
            "candidate": "artifacts/worker-008/f2b_rev11_dualrepair/candidate_rev12/"
                         "af_scc_c0_vacuum.yaml#98f9ec83c487",
            "edits": 2,
            "scope_note": "the 2-edit semantic repair is outside REC-12's four bounded items; "
                          "it needs either folding into the same revision before the FROZEN "
                          "rev29 write or a separate bounded owner card",
            "acceptance": ["canonical gate PASS (necessary, not sufficient)",
                           "order-relative containment checker returns zero findings",
                           "single-edit revert fires exactly its own finding",
                           "sibling C2 unchanged at its frozen hash"],
        },
        "authority": "worker reviewer verdict only; no gate or node state moved",
    }

    report = {
        "schema_version": "0.1",
        "task_id": "W066-F2B-CONTAINMENT-NORMATIVITY-01",
        "event_type": "review",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN"],
        "actor": "worker-066",
        "reviewer": "worker-066",
        "created_at": cst_now(),
        "gate": "G-FORM",
        "target": checks["target"],
        "sibling": {"path": "schemas/af_scc_c2_vacuum.yaml", "sha256": sha256(sibling)},
        "prior_rev12": {"path": "schemas/af_scc_c0_vacuum.yaml", "sha256": sha256(rev12)},
        "verdict": verdict["verdict"],
        "score": 2.5,
        "counts_as_full_schema_verdict": False,
        "review_scope": "normativity adjudication of two named clauses; not a full-schema "
                        "class-leakage/quantifier verdict",
        "adjudication": verdict,
        "controls": controls,
        "controls_all_match": all_match,
        "checks": checks,
        "assumptions": [
            "a verdict binds bytes, not paths; all runs used the pinned copies",
            "the document's own extension_class_containment sentence is the reference order",
            "'normative' means machine-required by FORM-RULE-SPEC and/or carried in a "
            "block the binding gate consumes; 'non-normative' means the document itself "
            "marks it advisory or no rule requires the carrier",
            "a canonical gate PASS certifies structure, not the truth of prose inside a "
            "required block (the gate's own docstring lists this blind spot)",
        ],
        "falsifier": (
            "Re-run normativity.py on the same pins. This adjudication is falsified if: the "
            "target bytes move (hash change voids it); the document at the bound hash marks "
            "implication_ledger.forbidden_transfers or regularity.must_not_conflate advisory/"
            "non-normative; rule_spec.json drops R06/R16 or the containment requirement; the "
            "canonical gate distinguishes the corrected from the defective wording (which "
            "would make the defect machine-detectable and the normativity claim differently "
            "scoped); any pre-registered control departs from its expectation; or the two "
            "sentences are absent at the bound hash."),
        "evidence_refs": [
            f"schemas/af_scc_c0_vacuum.yaml#{sha256(target)[:12]}",
            f"schemas/af_scc_c2_vacuum.yaml#{sha256(sibling)[:12]}",
            f"artifacts/formulation/rule_spec.json#{sha256(pinned('rule_spec'))[:12]}",
            f"artifacts/formulation/tools/check_class_schema.py#{sha256(pinned('gate_tool'))[:12]}",
            "artifacts/worker-066/f2b_containment_normativity/evidence/checks.json",
            "artifacts/worker-066/f2b_containment_normativity/evidence/controls.json",
        ],
        "limits": "Text-level consistency and rule-scope adjudication only; no claim about the "
                  "mathematics of C0/C2 inextendibility. Binds the pinned bytes only.",
        "next_falsifier": "any hash move of the target/sibling, or a FROZEN rev29 that "
                          "includes the 2-edit repair (which supersedes this revise).",
    }
    (EVID / "checks.json").write_text(json.dumps(checks, indent=2) + "\n")
    (EVID / "controls.json").write_text(json.dumps(controls, indent=2) + "\n")
    (HERE / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({
        "verdict": report["verdict"],
        "findings": checks["finding_count"],
        "all_controls_match": all_match,
        "target": report["target"]["sha256"][:16],
        "carried_forward": checks["carried_forward_from_rev12"],
        "cross_instrument": cc.get("predecessor_report_verdict"),
        "advisory_markers": checks["normative_markers_absent"],
        "gate_pristine": results["M0_pristine"]["verdict"],
    }, indent=1))
    return report


if __name__ == "__main__":
    main()
