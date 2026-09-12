#!/usr/bin/env python3
"""W037-REV14-F2B-REPAIR-ORACLE-01 -- pre-registered, read-only acceptance oracle for the
authorized rev14/rev30 repair of F2b items (1) and (2).

Why this exists
---------------
The ONE authorized rev14 write (card `astra-life08-formulation-rev14`) instructs:
  (1) F2b `regularity.must_not_conflate[0]` containment denial -> "the F2a corrected wording";
  (2) F2b `implication_ledger.forbidden_transfers[0].reason` "C2 is a strictly larger extension
      class" -> direction-correct wording.
F2a is the C2 class; F2b is the C0 class.  The two classes sit at opposite ends of the
extension-set chain (E_C2 subset E_{C^1,1} subset E_H2loc subset E_C0), so the *direction of the
entailment* flips between them.  A verbatim copy of F2a's corrected closing clause into F2b
("... so H2_loc-inextendibility ENTAILS this class's conclusion") is therefore INVERTED for C0.
That is exactly the carrier worker-053 independently flagged as W053-H2-01.
R-CT(The prior worker-037 rule) detects *denials* and the *forbidden-transfer premise*, not the
H2 closing-clause direction; a denial-absence predicate returns REPAIR_OK on inverted carriers
(ablation control below, corroborating W053-H2-04).  This oracle closes that hole ahead of the
write and pre-registers the acceptance rule so the repair cannot be graded post hoc.

Read-only: the only path written is the --json-out argument.  No canonical artifact is touched.
Worker events cannot set gate verdicts, node status, or validation_status.

Usage
-----
  python3 oracle.py --json-out report.json --label live_rev29
  python3 oracle.py --c0 <candidate.yaml> --json-out cand.json --label cand
  python3 oracle.py --self-test --json-out selftest.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]

# ---------------------------------------------------------------- frozen pins (measured, not asserted)
F0_TAXONOMY_PIN = "0abb9ed8a961"
CF29_DETECTOR_PIN = "a8c04fc31e4a"
REV29_C0_PIN = "b2ab6acb2bbe"
REV29_C2_PIN = "e9a27996dfd3"
REV29_F1_PIN = "d9cebb9404b2"
REV29_FROZEN_PIN = "815e08079aef"
SCHEMA_NAMES = ["af_wcc_vacuum.yaml", "af_scc_c2_vacuum.yaml", "af_scc_c0_vacuum.yaml"]
TAXONOMY = REPO / "research_map" / "formulation_taxonomy.yaml"
DETECTOR = REPO / "research_map" / "class_separation.py"
FROZEN = REPO / "artifacts" / "formulation" / "FROZEN.json"
MIRROR_DIR = REPO / "artifacts" / "formulation" / "schemas"

# worker-053 provenance for the shared calibration carriers (expected classifications only).
W053_REPORT = REPO / "artifacts" / "worker-053" / "f2b_rev30_h2_direction" / "report.json"
CALIBRATION_CARRIERS = [
    ("live_c0_rev29", "schemas/af_scc_c0_vacuum.yaml", "LIVE_DENIAL", REV29_C0_PIN),
    ("c2_sibling_live", "schemas/af_scc_c2_vacuum.yaml", "CORRECT_ENTAILMENT", REV29_C2_PIN),
    ("rehearsed_058_84b5d3fa", "artifacts/worker08/rev29_candidate/af_scc_c0_vacuum.repair-candidate.yaml", "INVERTED_ENTAILMENT", "84b5d3fa29a6"),
    ("composite_076_940e54ad", "artifacts/worker-076/f2b_repair_landing_audit/candidate/af_scc_c0_vacuum.repair-minimal.yaml", "INVERTED_ENTAILMENT", "940e54ad226c"),
    ("rev13_integration_044_48cadb", "artifacts/worker-044/f2b_rev13_integration/sandbox/schemas/af_scc_c0_vacuum.yaml", "INVERTED_ENTAILMENT", "48cadb72e507"),
    ("corrected_080_51c253c4", "artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_corrected.yaml", "CORRECT_ENTAILMENT", "51c253c46306"),
    ("nesting_only_080_4951cc96", "artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_nesting_only.yaml", "AGNOSTIC_NESTING_ONLY", "4951cc969803"),
    ("cd_repair_022_a110f8", "artifacts/worker-022/f2b_cd_repair/candidate/af_scc_c0_vacuum.repair-candidate.yaml", "NO_H2_CLAUSE", "a110f8e875af"),
]


def sha256f(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s)).strip()


def load_yaml(p: Path):
    import yaml
    return yaml.safe_load(p.read_bytes())


def run(cmd, timeout=120):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout or "")[-400:], (r.stderr or "")[-400:]
    except Exception as e:  # noqa: BLE001
        return 99, "", f"{type(e).__name__}: {e}"


# ------------------------------------------------------------------ classifiers
def classify_mnc0_c0(text: str) -> dict:
    """Classify must_not_conflate[0] WITH THE C0 CLASS AS SUBJECT (ground truth order
    C0 -> H2loc -> C11 -> C2: C0-inextendibility is the strongest)."""
    t = norm(text)
    lo = t.lower()
    denial = bool(re.search(r"no containment with (c2 or c0|c2|c0)", lo)) or bool(
        re.search(r"no containment[^.]{0,40}asserted", lo))
    ban_retained = bool(re.search(
        r"strictly between[^.]{0,120}(must not be cited|not a class definition|is not used)", lo))
    sents = re.split(r"(?<=[.;])\s+", t)
    ban_sents = [s for s in sents if re.search(r"must not be cited|not a class definition|is not used", s, re.I)]
    other = " ".join(s for s in sents if s not in ban_sents)
    positive_use = "strictly between" in other.lower()
    nesting = ("E_C2" in t and "E_H2loc" in t and "E_C0" in t) and bool(
        re.search(r"E_C2\s+subset", t) or re.search(r"E_C0\s+contains\s+E_H2loc", t))
    inverted = bool(re.search(r"H2_?loc-inextendibility\s+ENTAILS\s+this class", t, re.I)) or bool(
        re.search(r"H2_?loc-inextendibility\s+entails\s+this class", t, re.I))
    correct = bool(re.search(r"this class's conclusion[^.]{0,90}ENTAILS\s+H2_?loc-inextendibility", t, re.I)) or bool(
        re.search(r"C0-inextendibility[^.]{0,90}ENTAILS[^.]{0,60}H2_?loc", t, re.I))

    if denial:
        cls, why = "LIVE_DENIAL", "clause denies containing relation(s) its own ledger declares"
    elif inverted:
        cls, why = "INVERTED_ENTAILMENT", "clause makes H2_loc-inextendibility entail this C0 class"
    elif correct and nesting:
        cls, why = "CORRECT_ENTAILMENT", "nesting declared and direction is C0 => H2_loc"
    elif nesting:
        cls, why = "AGNOSTIC_NESTING_ONLY", "nesting declared, entailment direction deferred to ledger"
    else:
        cls, why = "NO_H2_CLAUSE", "no H2 containment/entailment clause found"
    if cls == "CORRECT_ENTAILMENT" and not ban_retained:
        cls, why = "BAN_MISSING", "direction correct but the 'strictly between' ban is not retained"
    if cls in ("CORRECT_ENTAILMENT", "AGNOSTIC_NESTING_ONLY") and positive_use:
        cls, why = "BAN_SELF_CONTRADICTION", "'strictly between' asserted positively while also banned"
    return {
        "class": cls, "why": why, "denial": denial, "nesting": nesting,
        "inverted_h2_clause": inverted, "correct_h2_clause": correct,
        "ban_retained": ban_retained, "ban_positive_use": positive_use,
    }


def classify_ft0_c0(row: dict) -> dict:
    """Classify implication_ledger.forbidden_transfers[0] with C0 as subject."""
    r = norm(row.get("reason", ""))
    lo = r.lower()
    inverted = "strictly larger extension class" in lo
    correct = ("strictly smaller extension class" in lo) or (
        "strictly stronger regularity requirement" in lo and "E_C2 subset of E_C0" in r)
    operative = "C2-inextendibility is strictly weaker" in r
    if inverted:
        cls, why = "FAIL_INVERTED_PREMISE", "calls C2 a strictly larger extension class (C2 is innermost)"
    elif correct:
        cls, why = "PASS" if operative else "PASS_NO_OPERATIVE", "premise direction correct"
    else:
        cls, why = "OWNER_ADJUDICATION", "premise neither the known inverted nor a recognised correct form"
    return {"class": cls, "why": why, "inverted_premise": inverted, "correct_premise": correct,
            "operative_conclusion_retained": operative, "reason": r}


def r_ct(c0: dict, raw: str) -> list:
    """Prior worker-037 containment rule, re-implemented: (a) a must_not_conflate clause denying a
    containment pair the file's own implication_ledger declares; (b) a forbidden_transfers reason
    asserting the reverse size ordering."""
    out = []
    ledger = c0.get("implication_ledger") or {}
    chain = norm(ledger.get("extension_class_containment", ""))
    declared = re.findall(r"E_(\S+?) contains E_(\S+?)(?= contains|;|$)", chain)
    declared_pairs = [(a, b) for a, b in declared]
    for idx, item in enumerate((c0.get("regularity") or {}).get("must_not_conflate") or []):
        s = norm(item)
        if re.search(r"no containment with", s, re.I):
            out.append({"rule": "R-CT(a)", "carrier": f"regularity.must_not_conflate[{idx}]",
                        "finding": "denies containment while ledger declares " + str(declared_pairs),
                        "line": line_of(raw, s[:60])})
    for idx, row in enumerate(ledger.get("forbidden_transfers") or []):
        r = norm(row.get("reason", ""))
        if re.search(r"strictly larger extension class", r, re.I):
            out.append({"rule": "R-CT(b)", "carrier": f"implication_ledger.forbidden_transfers[{idx}].reason",
                        "finding": "calls the innermost extension class strictly larger",
                        "line": line_of(raw, r[:60])})
    return out


def denial_only_predicate(mnc: dict) -> str:
    """Ablation: the worker-007-family predicate shape -- denial absence + ban, no direction."""
    if mnc["denial"]:
        return "FAIL"
    if not mnc["ban_retained"]:
        return "FAIL"
    return "REPAIR_OK"


def line_of(raw: str, needle: str):
    for i, ln in enumerate(raw.splitlines(), 1):
        if needle and needle[:40] in ln:
            return i
    return None


def item1_verdict(mnc: dict) -> dict:
    ok_strict = mnc["class"] == "CORRECT_ENTAILMENT"
    ok_weak = mnc["class"] == "AGNOSTIC_NESTING_ONLY"
    rejected = mnc["class"] in ("LIVE_DENIAL", "INVERTED_ENTAILMENT", "BAN_MISSING",
                                "BAN_SELF_CONTRADICTION")
    return {
        "rev14_item1_ok": bool(ok_strict or ok_weak),
        "grade": "ACCEPT_STRICT" if ok_strict else ("ACCEPT_WEAK" if ok_weak else
                 ("OWNER_ADJUDICATION" if mnc["class"] == "NO_H2_CLAUSE" else "REJECT")),
        "rejected": rejected,
        "note": ("rev14 wording 'the F2a corrected wording' is direction-ambiguous: F2a is the C2 end of the "
                 "chain. ACCEPT_STRICT requires the C0-direction closing clause; AGNOSTIC_NESTING_ONLY is "
                 "accepted only because it declares no inversion."),
    }


def item2_verdict(ft: dict) -> dict:
    return {"rev14_item2_ok": ft["class"] in ("PASS", "PASS_NO_OPERATIVE"),
            "grade": ft["class"]}


# ------------------------------------------------------------------ mutations (in memory, no writes)
def mutate_text(raw: str, c0: dict, c2: dict, fix152: str | None = None,
                fix246: str | None = None, inject_leak: bool = False) -> str:
    out = raw
    if fix152 is not None:
        old = str(c0["regularity"]["must_not_conflate"][0])
        assert old in out, "mnc0 not found verbatim"
        out = out.replace(old, fix152, 1)
    if fix246 is not None:
        oldr = str(c0["implication_ledger"]["forbidden_transfers"][0]["reason"])
        assert oldr in out, "ft0 reason not found verbatim"
        out = out.replace(oldr, fix246, 1)
    if inject_leak:
        anchor = '  must_not_conflate:\n'
        out = out.replace(anchor, anchor + '    - "C0 or C2 is a single class and may be declared as one here"\n', 1)
    return out


def build_selftest(c0: dict, c2: dict, raw_c0: str) -> list:
    f2a_clause = str(c2["regularity"]["must_not_conflate"][1])  # the literal "F2a corrected wording"
    correct_c0_clause = ("H2_loc (locally square-integrable curvature) is a distinct regularity-axis value "
                         "phrased in terms of CURVATURE, not metric differentiability. The extension sets are "
                         "nonetheless nested: E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0 (see "
                         "implication_ledger); this class's conclusion (C0-inextendibility) therefore ENTAILS "
                         "H2_loc-inextendibility, and H2_loc-inextendibility entails the C2 sibling's conclusion, "
                         "not this class. The informal phrase 'strictly between' is not a class definition and "
                         "must not be cited (worker-16 F2b-16-02 accepted).")
    correct_ft = ("C2 is a strictly stronger regularity requirement (E_C2 subset of E_C0), so "
                  "C2-inextendibility is strictly weaker")
    cases = [
        ("S0_live", {}, "LIVE_DENIAL", "FAIL", "FAIL"),
        ("S1_fix152_correct_c0_direction", {"fix152": correct_c0_clause}, "CORRECT_ENTAILMENT", "PASS", "FAIL"),
        ("S2_fix152_verbatim_f2a_copy", {"fix152": f2a_clause}, "INVERTED_ENTAILMENT", "FAIL", "FAIL"),
        ("S3_fix246_correct", {"fix246": correct_ft}, "LIVE_DENIAL", "FAIL", "PASS"),
        ("S4_fix_both_correct", {"fix152": correct_c0_clause, "fix246": correct_ft}, "CORRECT_ENTAILMENT", "PASS", "PASS"),
        ("S5_leak_injected", {"inject_leak": True}, "LIVE_DENIAL", "FAIL", "FAIL"),
    ]
    rows = []
    import yaml  # noqa: F401
    for cid, kw, exp_cls, exp_i1, exp_i2 in cases:
        txt = mutate_text(raw_c0, c0, c2, **kw)
        d = yaml.safe_load(txt)
        mnc = classify_mnc0_c0(d["regularity"]["must_not_conflate"][0])
        ft = classify_ft0_c0(d["implication_ledger"]["forbidden_transfers"][0])
        r = r_ct(d, txt)
        v1, v2 = item1_verdict(mnc), item2_verdict(ft)
        exp_rct = 2 if cid in ("S0_live", "S5_leak_injected") else (
            1 if cid in ("S1_fix152_correct_c0_direction", "S2_fix152_verbatim_f2a_copy", "S3_fix246_correct") else 0)
        if cid == "S5_leak_injected":
            exp_rct = 2
        obs = {
            "id": cid, "mnc_class": mnc["class"], "item1_grade": v1["grade"], "item2_grade": v2["grade"],
            "r_ct_n": len(r), "expect": {"mnc_class": exp_cls, "item1": exp_i1, "item2": exp_i2, "r_ct_n": exp_rct},
            "pass": bool(mnc["class"] == exp_cls and v1["grade"] == exp_i1 and v2["grade"] == exp_i2
                         and len(r) == exp_rct),
        }
        rows.append(obs)
    return rows


# ------------------------------------------------------------------ main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--c0", default=str(REPO / "schemas" / "af_scc_c0_vacuum.yaml"))
    ap.add_argument("--c2", default=str(REPO / "schemas" / "af_scc_c2_vacuum.yaml"))
    ap.add_argument("--json-out", required=True)
    ap.add_argument("--label", default="live")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--skip-scope", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    c0p, c2p = Path(a.c0), Path(a.c2)
    if not c0p.is_absolute():
        c0p = REPO / c0p
    if not c2p.is_absolute():
        c2p = REPO / c2p
    rep: dict = {
        "task_id": "W037-REV14-F2B-REPAIR-ORACLE-01", "label": a.label,
        "actor": "worker-037", "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
        "node_id": "F2b", "gate": "G-FORM", "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "ground_truth_order": {"entailment_order": ["C0", "H2LOC", "C11", "C2"],
                               "set_order_largest_first": ["C0", "H2LOC", "C11", "C2"]},
    }
    pin0 = {}
    for name, p in (("c0", c0p), ("c2", c2p)):
        pin0[name] = {"path": str(p.relative_to(REPO)) if str(p).startswith(str(REPO)) else str(p),
                      "sha256": sha256f(p), "bytes": p.stat().st_size}
    raw_c0 = c0p.read_text()
    c0 = load_yaml(c0p)
    c2 = load_yaml(c2p)
    mnc = classify_mnc0_c0(c0["regularity"]["must_not_conflate"][0])
    ft = classify_ft0_c0(c0["implication_ledger"]["forbidden_transfers"][0])
    v1, v2 = item1_verdict(mnc), item2_verdict(ft)
    findings_rct = r_ct(c0, raw_c0)
    ablation = denial_only_predicate(mnc)

    rep["pins_t0"] = pin0
    rep["input_mnc0"] = norm(c0["regularity"]["must_not_conflate"][0])
    rep["input_ft0"] = norm(c0["implication_ledger"]["forbidden_transfers"][0].get("reason", ""))
    rep["mnc0_classification"] = mnc
    rep["ft0_classification"] = ft
    rep["item1"] = v1
    rep["item2"] = v2
    rep["r_ct_findings"] = findings_rct
    rep["rev14_f2b_repair_ok"] = bool(v1["rev14_item1_ok"] and v2["rev14_item2_ok"] and not findings_rct)

    # blindness ablation: denial-absence predicate on the same bytes
    rep["ablation_denial_only"] = {
        "predicate": "no denial + ban retained (no direction assertion)",
        "verdict_on_these_bytes": ablation,
        "blind_to_inversion": ablation == "REPAIR_OK" and mnc["class"] == "INVERTED_ENTAILMENT",
    }

    if a.self_test:
        rep["selftest"] = build_selftest(c0, c2, raw_c0)
        rep["selftest_all_pass"] = all(r["pass"] for r in rep["selftest"])

    # calibration on the shared carrier corpus (read-only, measured hashes)
    cal = []
    for cid, rel, exp, exppfx in CALIBRATION_CARRIERS:
        p = REPO / rel
        try:
            raw = p.read_text()
            d = load_yaml(p)
            m = classify_mnc0_c0(d["regularity"]["must_not_conflate"][0])
            f = classify_ft0_c0(d["implication_ledger"]["forbidden_transfers"][0])
            cal.append({"id": cid, "path": rel, "sha256": sha256f(p), "prefix_expected": exppfx,
                        "hash_match": sha256f(p).startswith(exppfx),
                        "w053_expected": exp, "w037_observed": m["class"], "agree": m["class"] == exp,
                        "ft0_class": f["class"]})
        except Exception as e:  # noqa: BLE001
            cal.append({"id": cid, "path": rel, "error": f"{type(e).__name__}: {e}"})
    rep["calibration"] = cal
    rep["calibration_agreement"] = {
        "n": len(cal), "agree": sum(1 for c in cal if c.get("agree")),
        "divergences": [c["id"] for c in cal if c.get("agree") is False],
        "w053_report_sha256": sha256f(W053_REPORT) if W053_REPORT.exists() else None,
    }

    # scope-integrity: F0 / detector / mirrors / FROZEN pin chain
    scope = {"f0_taxonomy_pin_expected": F0_TAXONOMY_PIN, "cf29_detector_pin_expected": CF29_DETECTOR_PIN}
    if not a.skip_scope:
        scope["f0_taxonomy_sha256"] = sha256f(TAXONOMY)
        scope["f0_taxonomy_unmoved"] = sha256f(TAXONOMY).startswith(F0_TAXONOMY_PIN)
        scope["cf29_detector_sha256"] = sha256f(DETECTOR)
        scope["cf29_detector_unmoved"] = sha256f(DETECTOR).startswith(CF29_DETECTOR_PIN)
        pairs = {}
        for n in SCHEMA_NAMES:
            cp, mp = REPO / "schemas" / n, MIRROR_DIR / n
            if cp.exists() and mp.exists():
                pairs[n] = {"canonical": sha256f(cp), "mirror": sha256f(mp),
                            "byte_identical": sha256f(cp) == sha256f(mp)}
            else:
                pairs[n] = {"error": "missing"}
        scope["mirror_pairs"] = pairs
        scope["mirror_pairs_all_byte_identical"] = all(v.get("byte_identical") for v in pairs.values())
        if FROZEN.exists():
            fz = json.loads(FROZEN.read_text())
            decl = fz.get("files") or {}
            resolved, mismatch, missing = [], [], []
            for path, meta in decl.items():
                fp = REPO / path
                if not fp.exists():
                    missing.append(path)
                    continue
                got = sha256f(fp)
                (resolved if got == meta.get("sha256") else mismatch).append(
                    {"path": path, "declared": str(meta.get("sha256"))[:16], "measured": got[:16]})
            schema_decl = {n: decl.get(f"schemas/{n}", {}).get("sha256") for n in SCHEMA_NAMES}
            scope["frozen"] = {"revision": fz.get("revision"), "sha256": sha256f(FROZEN),
                               "declared_files": len(decl), "resolved": len(resolved),
                               "mismatch": mismatch, "missing": missing,
                               "declared_schema_pins": {k: (v[:16] if v else None) for k, v in schema_decl.items()},
                               "measured_schema_pins": {n: sha256f(REPO / "schemas" / n)[:16] for n in SCHEMA_NAMES}}
    rep["scope"] = scope

    # stability
    time.sleep(0.05)
    pin1 = {"c0_sha256": sha256f(c0p), "c2_sha256": sha256f(c2p)}
    rep["pins_t1"] = pin1
    rep["pins_stable"] = (pin0["c0"]["sha256"] == pin1["c0_sha256"] and pin0["c2"]["sha256"] == pin1["c2_sha256"])
    rep["runtime_seconds"] = round(time.time() - t0, 3)

    # pre-registered acceptance rule for the rev14/rev30 landing
    rep["prereg"] = {
        "task_id": "W037-REV14-F2B-REPAIR-ORACLE-01",
        "target": "the ONE authorized rev14/rev30 write of schemas/af_scc_c0_vacuum.yaml (F2b), "
                  "items (1) and (2) of card astra-life08-formulation-rev14",
        "acceptance_rule": [
            "item1: must_not_conflate[0] is CORRECT_ENTAILMENT (nesting declared AND closing clause in the "
            "C0 direction) or at minimum AGNOSTIC_NESTING_ONLY; LIVE_DENIAL / INVERTED_ENTAILMENT / "
            "BAN_MISSING / BAN_SELF_CONTRADICTION are rejection grades",
            "item2: forbidden_transfers[0].reason is direction-correct (not 'strictly larger extension "
            "class') and retains 'C2-inextendibility is strictly weaker'",
            "R-CT findings == 0 on the new bytes",
            "scope: F0 taxonomy 0abb9ed8a961 and CF-29 detector a8c04fc31e4a unmoved; all three mirror "
            "pairs byte-identical; FROZEN rev30 declares the new schema sha256 values",
        ],
        "reject_modes_pre_registered": {
            "verbatim_f2a_copy": "copying F2a's closing clause 'so H2_loc-inextendibility ENTAILS this "
                                 "class's conclusion' into F2b is INVERTED for C0 (see S2 control)",
            "denial_absence_only": "a predicate that checks denial absence + ban without the H2 direction "
                                   "returns REPAIR_OK on inverted carriers (ablation; corroborates W053-H2-04)",
        },
        "run_command": "python3 artifacts/worker-037/rev14_f2b_repair_oracle/oracle.py "
                       "--json-out <new>.json --label rev30_landing",
        "falsifier": "Falsified if (a) the live F2b pin is not b2ab6acb2bbe at T0; (b) live "
                     "must_not_conflate[0] does not carry the 'No containment with C2 or C0' denial; "
                     "(c) any of the three inverted staged carriers (84b5d3fa / 940e54ad / 48cadb72) is not "
                     "classified INVERTED_ENTAILMENT; (d) corrected_080 51c253c4 is not CORRECT_ENTAILMENT or "
                     "nesting_only_080 4951cc96 is not AGNOSTIC_NESTING_ONLY; (e) the self-test mutants do not "
                     "reproduce their pre-registered classes; (f) the denial-only ablation is not REPAIR_OK on "
                     "an inverted carrier; (g) pins_stable is false; (h) scope reports F0/detector moved or a "
                     "mirror pair divergent.",
        "does_not_claim": ["G-FORM pass/fail or any gate verdict", "node completion",
                           "validation_status promotion", "authority to edit canonical artifacts",
                           "that the rev30 write has landed (it has not at T0)",
                           "that nesting_only_080 or cd_repair_022 is the instructed wording",
                           "adoption of worker-053's recommendation or instrument",
                           "review verdict on any artifact"],
    }

    out = Path(a.json_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: rep[k] for k in ("label", "mnc0_classification", "item1", "item2",
                                          "r_ct_findings", "rev14_f2b_repair_ok", "ablation_denial_only",
                                          "calibration_agreement", "pins_stable") if k in rep}, indent=1))
    print("wrote", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
