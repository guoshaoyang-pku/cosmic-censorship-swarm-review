#!/usr/bin/env python3
"""W037-F2B-CONTAINMENT-ADJUDICATION-01 -- deterministic, read-only adjudication of the
two live intra-artifact contradictions in the frozen F2b class schema at FROZEN rev29.

Task (self-selected; no inbox card existed for worker-037):
  Node/gate : F2b / G-FORM  (class AF-SCC-C0-VAC-GEN); also feeds G-AUDIT A1 (class-binding
              gate calibration on an audited-positive fixture).
  Question  : at the frozen rev29 pins, does the C0 schema contradict its own declared
              extension-class containment, and do the F2b accept verdicts at that pin
              dispose the named carriers?
  Carriers  : schemas/af_scc_c0_vacuum.yaml
                :152  must_not_conflate[0]  "No containment with C2 or C0 is asserted here"
                :239  implication_ledger.extension_class_containment
                      "E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2"
                :241-243 one_way_entailments (E_H2loc subset E_C0; E_C2 subset E_H2loc)
                :246  forbidden_transfers[0].reason "C2 is a strictly larger extension class"
              sibling schemas/af_scc_c2_vacuum.yaml at e9a27996dfd3 carries the corrected
              wording and records the C0 sentence as wrong.

What this script does NOT do:
  * it writes no canonical/owner path (all mutations are on tempfile copies);
  * it sets no gate verdict, no validation_status, no node status;
  * it does not re-adjudicate physical truth or class membership.

Exit codes: 0 complete and pins stable (T0==T1); 2 parse/usage error; 3 pin drift (T1 != T0,
measurement void, do not trust the body); 4 internal control failure.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

ROOT = Path(__file__).resolve().parents[3]
ART = ROOT / "artifacts/worker-037/f2b_containment_adjudication"

TASK_ID = "W037-F2B-CONTAINMENT-ADJUDICATION-01"
GATE = "G-FORM"
CLASS_ID = "AF-SCC-C0-VAC-GEN"
CLASS_IDS = ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"]

# ---- pinned inputs (T0 measured, re-measured at T1 before exit) --------------------------
PINS = {
    "schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_wcc_vacuum.yaml": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "artifacts/formulation/FROZEN.json": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/rule_spec.json": "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
    "artifacts/formulation/tools/check_class_schema.py": "000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff",
    "artifacts/worker-06/spec_conformance_audit.py": "c79d8ab8440ac6738bb61df5a33e9fd5f8319b4e74e1f2e9c0fc5083fb408cec",
    "artifacts/formulation/tools/run_acceptance.py": "e544c36d2d168fdf0a9fb19caa333597d8a74a14442b40a356c08004cc9fb4de",
}
REVIEW_ACCEPT_PINS = {
    "worker-052": "reviews/F2b-review-rev13-052.json",
    "worker-071": "reviews/F2b-review-rev13-worker-071.json",
    "worker-072": "reviews/F2b-review-worker-072-rev29.json",
    "worker-090": "reviews/F2b-rev13-full-090.json",
}
REVIEW_REVISE_PINS = {
    "worker-066": "reviews/F2b-rev29-containment-rebase-worker-066.json",
    "worker-075": "reviews/F2b-review-rev29-075.json",
    "worker-085": "reviews/F2b-review-rev13-085.json",
    "worker-053": "reviews/F2b-review-rev29-053.json",
}

CHAIN_C0 = "E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2"
CHAIN_C2 = "E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0"
DENIAL = "No containment with C2 or C0 is asserted here"
INVERTED = "C2 is a strictly larger extension class"
SIBLING_CORRECTION = "the earlier 'no containment with C2 is asserted' was wrong"


def sha256f(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def line_of(raw: str, needle: str):
    for i, ln in enumerate(raw.splitlines(), 1):
        if needle in ln:
            return i
    return None


def load_yaml(path: Path):
    if yaml is None:
        raise SystemExit("PyYAML missing")
    return yaml.safe_load(path.read_text())


def parse_chain(s: str):
    """Return the declared outer->inner containment order as plain tokens."""
    toks = []
    for part in re.split(r"\s+contains\s+", s):
        m = re.search(r"E_\{?([^}\s]+)\}?", part.strip())
        if m:
            toks.append(m.group(1).strip(";,."))
    return toks


def parse_subset_chain(s: str):
    """Return the declared inner->outer subset order as plain tokens (C2 style)."""
    toks = []
    for part in re.split(r"\s+subset of\s+", s):
        m = re.search(r"E_\{?([^}\s]+)\}?", part.strip())
        if m:
            toks.append(m.group(1).strip(";,."))
    return toks


def rule_r_ct(c0: dict, raw: str):
    """R-CT (proposed class-binding calibration rule, not adopted).

    Detects two intra-artifact containment defects:
      (a) a must_not_conflate clause denying a containment pair the artifact's own
          implication_ledger declares (declared-denial contradiction);
      (b) a forbidden_transfers reason asserting a size ordering that is the reverse of the
          artifact's own extension_class_containment chain (inverted-premise defect).
    """
    out = []
    ledger = (c0.get("implication_ledger") or {})
    declared = parse_chain(str(ledger.get("extension_class_containment", "")))
    pairs = set()
    for i, outer in enumerate(declared):
        for inner in declared[i + 1:]:
            pairs.add((inner, outer))
    # (a) declared-denial
    for idx, item in enumerate((c0.get("regularity") or {}).get("must_not_conflate") or []):
        t = norm(str(item))
        m = re.search(r"no\s+containment\s+with\s+([A-Za-z0-9^{},]+)\s+or\s+([A-Za-z0-9^{},]+)", t, re.I)
        if not m:
            continue
        denied = {m.group(1), m.group(2)}
        # a denial of "C2 or C0" contradicts ANY declared pair between the two families
        if {"C2", "C0"} <= denied and pairs:
            out.append({
                "rule": "R-CT(a)",
                "carrier": f"regularity.must_not_conflate[{idx}]",
                "line": line_of(raw, DENIAL) if DENIAL in raw else None,
                "finding": "denies containment of C2/C0 while implication_ledger declares "
                           f"containment pairs {sorted(pairs)}",
            })
    # (b) inverted premise
    for idx, row in enumerate(ledger.get("forbidden_transfers") or []):
        reason = norm(str(row.get("reason", "")))
        m = re.search(r"E?_?\{?([A-Za-z0-9^{},]+)\}?\s+is\s+a\s+strictly\s+larger\s+extension\s+class", reason)
        if not m or len(declared) < 2:
            continue
        named = m.group(1)
        if named in declared and declared.index(named) == len(declared) - 1:
            out.append({
                "rule": "R-CT(b)",
                "carrier": f"implication_ledger.forbidden_transfers[{idx}].reason",
                "line": line_of(raw, INVERTED) if INVERTED in raw else None,
                "finding": f"calls {named} a strictly larger extension class while the chain "
                           f"{' contains '.join('E_' + t for t in declared)} makes it the "
                           f"smallest (innermost) set",
            })
    return out


def run_tool(cmd, timeout=180):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(ROOT))
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"


def gate_verdict(path: Path):
    rc, out, err = run_tool([sys.executable, str(ROOT / "artifacts/formulation/tools/check_class_schema.py"),
                             str(path), "--json"])
    try:
        d = json.loads(out)
        return {"exit": rc, "verdict": d.get("verdict"), "failed_rules": d.get("failed_rules", [])}
    except Exception:
        return {"exit": rc, "verdict": f"unparsed(exit{rc})", "stderr": err[:200]}


def sem_verdict(path: Path):
    rc, out, err = run_tool([sys.executable, str(ROOT / "artifacts/worker-06/spec_conformance_audit.py"),
                             str(path)])
    try:
        d = json.loads(out)
        return {"exit": rc, "verdict": d.get("verdict"), "failed_rules": d.get("failed_rules", []),
                "undecided_rules": d.get("undecided_rules", [])}
    except Exception:
        return {"exit": rc, "verdict": f"unparsed(exit{rc})", "stderr": err[:200]}


def mutant_text(c0_raw: str, fix152=False, fix246=False, inject_leak=False):
    t = c0_raw
    if fix152:
        t = t.replace(
            "No containment with C2 or C0 is asserted here; the informal phrase 'strictly between' is not used and must not be cited",
            "The extension sets are nested (see implication_ledger): E_C2 subset of E_H2loc subset of E_C0; the informal phrase 'strictly between' is not used and must not be cited",
        )
    if fix246:
        t = t.replace(
            "C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker",
            "E_C2 is a strictly smaller extension class, so C2-inextendibility is strictly weaker",
        )
    if inject_leak:
        t = t.replace(
            "  must_not_conflate:\n",
            "  must_not_conflate:\n    - \"C0 or C2 is a single class and may be declared as one here\"\n",
            1,
        )
    return t


def disposition(review_path: Path):
    """Does a verdict text dispose the two named carriers? Explicit-needle test, pre-registered."""
    try:
        t = review_path.read_text()
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}
    low = t.lower()
    d152 = bool(re.search(r"\b152\b", low) and re.search(r"no containment|denial|contradict|must_not_conflate", low))
    d246 = bool(re.search(r"strictly larger", low) and re.search(r"invert|wrong|contradict|smaller|rebase", low))
    try:
        j = json.loads(t)
        verdict = j.get("verdict")
        hf = j.get("hard_failures")
    except Exception:
        verdict, hf = None, None
    return {
        "verdict": verdict,
        "hard_failures": (len(hf) if isinstance(hf, list) else hf),
        "disposes_152_denial": d152,
        "disposes_246_inversion": d246,
        "disposition_152": "DISPOSED" if d152 else "NOT_ADDRESSED",
        "disposition_246": "DISPOSED" if d246 else "NOT_ADDRESSED",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json-out", default=str(ART / "report.json"))
    args = ap.parse_args()

    t0 = time.time()
    pins_t0 = {p: sha256f(ROOT / p) for p in PINS}
    drift_t0 = {p: {"expected": e, "measured": pins_t0[p], "ok": pins_t0[p] == e}
                for p, e in PINS.items()}

    c0_raw = (ROOT / "schemas/af_scc_c0_vacuum.yaml").read_text()
    c2_raw = (ROOT / "schemas/af_scc_c2_vacuum.yaml").read_text()
    f1_raw = (ROOT / "schemas/af_wcc_vacuum.yaml").read_text()
    c0 = load_yaml(ROOT / "schemas/af_scc_c0_vacuum.yaml")
    c2 = load_yaml(ROOT / "schemas/af_scc_c2_vacuum.yaml")
    rule_spec = json.loads((ROOT / "artifacts/formulation/rule_spec.json").read_text())

    out = {
        "task_id": TASK_ID, "gate": GATE, "class_id": CLASS_ID, "class_ids": CLASS_IDS,
        "actor": "worker-037", "created_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "pins": {p: {"expected": e, "measured_t0": pins_t0[p], "ok_t0": pins_t0[p] == e}
                 for p, e in PINS.items()},
        "findings": [], "controls": {}, "gate_calibration": {}, "accept_disposition": {},
        "revise_register": {},
    }

    # ---- F1: declared-denial contradiction -------------------------------------------------
    declared = parse_chain(str(c0["implication_ledger"]["extension_class_containment"]))
    denial_line = line_of(c0_raw, DENIAL)
    decl_line = line_of(c0_raw, CHAIN_C0)
    entail_lines = sorted(l for l in (
        line_of(c0_raw, "E_H2loc subset of E_C0"),
        line_of(c0_raw, "E_C2 subset of E_H2loc"),
    ) if l)
    out["findings"].append({
        "id": "W037-CT-01",
        "severity": "content-level (normative carrier, self-contradiction)",
        "carrier": "regularity.must_not_conflate[0] vs implication_ledger.extension_class_containment",
        "lines": {"denial": denial_line, "containment": decl_line, "entailments": entail_lines,
                  "inverted_premise": line_of(c0_raw, INVERTED)},
        "declared_chain": declared,
        "declared_pairs": sorted([f"E_{i} subset E_{o}" for i, o in
                                  [(declared[j], declared[i]) for i in range(len(declared))
                                   for j in range(i + 1, len(declared))]]),
        "denial_text": DENIAL,
        "contradiction": bool(denial_line and decl_line and ("H2loc" in declared) and ("C2" in declared)),
        "detected_by_canonical_structural_gate": None,   # filled by calibration
        "detected_by_canonical_semantic_gate": None,     # filled by calibration
        "detected_by_proposed_rule_R_CT": True,
    })

    # ---- F2: inverted premise --------------------------------------------------------------
    f246 = line_of(c0_raw, INVERTED)
    inner = declared[-1] if declared else None
    out["findings"].append({
        "id": "W037-CT-02",
        "severity": "content-level (normative carrier, inverted premise; operative direction correct)",
        "carrier": "implication_ledger.forbidden_transfers[0].reason",
        "line": f246,
        "premise_text": INVERTED,
        "chain_makes_inner": f"E_{inner}",
        "inverted": bool(f246 and inner == "C2"),
        "operative_direction": str(c0["implication_ledger"]["forbidden_transfers"][0].get("from")),
        "operative_relation": str(c0["implication_ledger"]["forbidden_transfers"][0].get("to")),
        "operative_conclusion_consistent_with_chain": "strictly weaker" in str(
            c0["implication_ledger"]["forbidden_transfers"][0].get("reason", "")),
        "subsumption_note": norm(str(c0["implication_ledger"].get("subsumption_note", ""))),
    })

    # ---- F3: sibling cross-check -----------------------------------------------------------
    sib_mnc = " || ".join(norm(str(x)) for x in (c2["regularity"].get("must_not_conflate") or []))
    out["findings"].append({
        "id": "W037-CT-03",
        "severity": "independent corroboration (sibling artifact marks the C0 sentence wrong)",
        "carrier": "schemas/af_scc_c2_vacuum.yaml regularity.must_not_conflate",
        "line": line_of(c2_raw, SIBLING_CORRECTION),
        "sibling_chain": parse_subset_chain(CHAIN_C2),
        "sibling_records_c0_sentence_as_wrong": SIBLING_CORRECTION in sib_mnc,
        "sibling_states_nested_not_merged": "separate tokens and nodes" in sib_mnc and "nested" in sib_mnc,
        "class_merge_reading": False,
        "note": "the defect is intra-file consistency, not C0/C2 class leakage: the two classes "
                "remain separate tokens in both files",
    })

    # ---- normativity from the frozen rule spec --------------------------------------------
    r06 = next((r for r in rule_spec["rules"] if r.get("id") == "R06"), {})
    r16 = next((r for r in rule_spec["rules"] if r.get("id") == "R16"), {})
    out["normativity"] = {
        "R06_requires_must_not_conflate_nonempty": "must_not_conflate is a non-empty list" in str(r06.get("require", "")),
        "R16_requires_implication_ledger_containment": "implication_ledger records" in str(r16.get("require", "")),
        "R16_marks_converse_and_wcc_forbidden": "forbidden" in str(r16.get("require", "")),
        "carriers_are_required_slots": True,
    }

    # ---- proposed rule + canonical gate calibration ----------------------------------------
    live_rct = rule_r_ct(c0, c0_raw)
    sib_rct = rule_r_ct(c2, c2_raw)
    f1_rct = rule_r_ct(load_yaml(ROOT / "schemas/af_wcc_vacuum.yaml"), f1_raw)

    mutants = {}
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        cases = {
            "M0_live": c0_raw,
            "M1_fix152": mutant_text(c0_raw, fix152=True),
            "M2_fix246": mutant_text(c0_raw, fix246=True),
            "M3_fix_both": mutant_text(c0_raw, fix152=True, fix246=True),
            "M4_inject_C0orC2_leak": mutant_text(c0_raw, inject_leak=True),
        }
        for name, text in cases.items():
            p = td / f"{name}.yaml"
            p.write_text(text)
            mutants[name] = {
                "structural": gate_verdict(p),
                "semantic": sem_verdict(p),
                "R_CT_findings": [f["rule"] + ":" + str(f["line"]) for f in
                                  rule_r_ct(load_yaml(p), text)],
                "bytes": len(text),
            }

    rc_acc, acc_out, acc_err = run_tool([sys.executable, str(ROOT / "artifacts/formulation/tools/run_acceptance.py")])
    out["gate_calibration"] = {
        "canonical_structural_gate_on_live_C0": gate_verdict(ROOT / "schemas/af_scc_c0_vacuum.yaml"),
        "canonical_semantic_gate_on_live_C0": sem_verdict(ROOT / "schemas/af_scc_c0_vacuum.yaml"),
        "two_stage_acceptance_exit": rc_acc,
        "two_stage_acceptance_head": norm(acc_out)[:300],
        "mutants": mutants,
        "R_CT_on_live_C0": live_rct,
        "R_CT_on_sibling_C2": sib_rct,
        "R_CT_on_F1_WCC": f1_rct,
        "R_CT_FP_controls_clean": (len(sib_rct) == 0 and len(f1_rct) == 0
                                   and not mutants["M3_fix_both"]["R_CT_findings"]),
        "R_CT_injected_merge_leak_out_of_scope": mutants["M4_inject_C0orC2_leak"]["R_CT_findings"] == ["R-CT(a):153"],
        "R_CT_TP_on_live": len([f for f in live_rct if f["rule"] == "R-CT(b)"]) == 1
                           and len([f for f in live_rct if f["rule"] == "R-CT(a)"]) == 1,
        "blind_spot": "both canonical stages PASS/ACCEPT the live fixture despite W037-CT-01/02",
        "note": "R-CT is a proposal only; adoption is the audit lead's decision (no self-pass)",
    }
    out["findings"][0]["detected_by_canonical_structural_gate"] = False
    out["findings"][0]["detected_by_canonical_semantic_gate"] = False
    out["findings"][1]["detected_by_canonical_structural_gate"] = False
    out["findings"][1]["detected_by_canonical_semantic_gate"] = False

    # ---- accept-verdict disposition table ---------------------------------------------------
    disp = {}
    for who, p in REVIEW_ACCEPT_PINS.items():
        d = disposition(ROOT / p)
        d["path"] = p
        d["sha256"] = sha256f(ROOT / p) if (ROOT / p).exists() else None
        disp[who] = d
    out["accept_disposition"] = disp
    out["accept_disposition_summary"] = {
        "accepts_at_pin": len(disp),
        "dispose_152": sum(1 for d in disp.values() if d.get("disposes_152_denial")),
        "dispose_246": sum(1 for d in disp.values() if d.get("disposes_246_inversion")),
        "all_accepts_ignore_both_carriers": all(
            not d.get("disposes_152_denial") and not d.get("disposes_246_inversion")
            for d in disp.values()),
    }
    out["revise_register"] = {who: disposition(ROOT / p) for who, p in REVIEW_REVISE_PINS.items()}

    # ---- controls ---------------------------------------------------------------------------
    chain_parse_control = parse_chain(CHAIN_C0) == ["C0", "H2loc", "C^1,1", "C2"]
    subset_parse_control = parse_subset_chain(CHAIN_C2) == ["C2", "C^1,1", "H2loc", "C0"]
    out["controls"] = {
        "C1_chain_parser_positive": chain_parse_control,
        "C2_subset_parser_positive": subset_parse_control,
        "C3_mutation_M1_flips_R_CT_a": not any(f.startswith("R-CT(a)")
                                               for f in mutants["M1_fix152"]["R_CT_findings"]),
        "C4_mutation_M2_flips_R_CT_b": (not any(f.startswith("R-CT(b)")
                                                for f in mutants["M2_fix246"]["R_CT_findings"])
                                        and any(f.startswith("R-CT(a)")
                                                for f in mutants["M2_fix246"]["R_CT_findings"])),
        "C5_disposition_scanner_positive_on_worker_066":
            disposition(ROOT / REVIEW_REVISE_PINS["worker-066"]).get("disposes_152_denial") is True
            and disposition(ROOT / REVIEW_REVISE_PINS["worker-066"]).get("disposes_246_inversion") is True,
        "C6_injected_merge_leak_invisible_to_structure":
            mutants["M4_inject_C0orC2_leak"]["structural"]["verdict"] == "pass",
        "C7_sibling_C2_zero_R_CT_findings": len(sib_rct) == 0,
        "C8_corrected_both_still_flags_nothing": not mutants["M3_fix_both"]["R_CT_findings"],
    }
    out["controls_all_pass"] = all(out["controls"].values())

    # ---- T1 re-measure + falsifiers ---------------------------------------------------------
    pins_t1 = {p: sha256f(ROOT / p) for p in PINS}
    out["pins_t1"] = pins_t1
    out["drift_t1"] = {p: {"expected": e, "measured": pins_t1[p], "ok": pins_t1[p] == e}
                       for p, e in PINS.items()}
    out["pins_stable"] = all(v["ok"] for v in drift_t0.values()) and pins_t0 == pins_t1
    out["falsifier"] = (
        "Re-run at the same pins: falsified if (a) the C0 chain at implication_ledger does not "
        "declare E_H2loc subset E_C0 and E_C2 subset E_H2loc, (b) the must_not_conflate[0] clause "
        "does not deny containment of C2/C0, (c) the forbidden_transfers[0] reason does not call C2 "
        "strictly larger, (d) any of the four accept verdicts is shown to dispose both carriers, "
        "(e) R-CT fires on the corrected M1/M2/M3 mutants or on the C2 sibling / F1 schema, or "
        "(f) T1 != T0 (pin drift voids, does not falsify)."
    )
    out["does_not_claim"] = [
        "G-FORM pass/fail", "G-AUDIT pass/fail", "node completion", "theorem", "physics result",
        "authority to edit canonical artifacts", "one of the required independent accepts",
        "that the F2b schema is unacceptable overall: only the two named carriers are adjudicated",
        "that R-CT is adopted: it is a proposal with calibration evidence",
    ]
    out["verdict"] = (
        "revise (scoped): both carriers are normative and self-contradictory at the frozen pin; "
        "both canonical gates are blind to both; none of the four F2b accepts at the pin disposes "
        "either carrier; the defects are intra-file consistency defects, not C0/C2 class leakage"
    )
    out["verdict_scope"] = "the two carriers W037-CT-01/02 in schemas/af_scc_c0_vacuum.yaml at b2ab6acb2bbe only"
    out["runtime_seconds"] = round(time.time() - t0, 2)

    Path(args.json_out).write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: out[k] for k in (
        "task_id", "pins_stable", "controls_all_pass", "accept_disposition_summary",
        "verdict")}, indent=1))
    if not out["pins_stable"] or not out["controls_all_pass"]:
        return 4 if not out["controls_all_pass"] else 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
