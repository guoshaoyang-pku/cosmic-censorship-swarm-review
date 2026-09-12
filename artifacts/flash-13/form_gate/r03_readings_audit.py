#!/usr/bin/env python3
"""R03 semantic-vs-literal readings audit at the frozen rev29 / rev13 bytes (gate rev1.3).

Decides nothing by itself.  It measures, at pinned hashes, the two disclosed readings of R03 and
the controls that separate them, and writes one JSON record (`r03_readings_rev29.json`) with every
input hash, every reading, and the assertions that must hold for the gate revision to be sound.

Assertions (all must hold; exit 0 iff they do)
  A1  FROZEN.json is rev29 at 815e08079aefbc and the three canonical schema bytes match its pins.
  A2  Under the semantic reading S, all three canonical schemas PASS R03 (and the full gate).
  A3  Under the literal reading L, canonical WCC FAILS R03 on exactly the tuple binder "(q,t0)"
      and canonical C2/C0 pass -- i.e. the two readings differ on exactly the disputed case.
  A4  All 10 fixtures_r03 controls match their expected (L, S) matrix.
  A5  The repaired m25 (fixtures_v13) still fails R03, now on the missing declared variable t0
      with a matching kind sequence; the legacy m25 also fails (kind mismatch + literal).
  A6  No canonical byte changes during the audit (re-measured at exit).
Output: r03_readings_rev29.json (audit record) and canonical_recheck_rev29_v13.json (per-schema).
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
GATE = HERE / "check_class_schema.py"
FROZEN = REPO / "artifacts/formulation/FROZEN.json"
RULE_SPEC = REPO / "artifacts/formulation/rule_spec.json"
CANON = {
    "AF-WCC-VAC-GEN": REPO / "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
    "AF-SCC-C2-VAC-GEN": REPO / "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
    "AF-SCC-C0-VAC-GEN": REPO / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
}
FROZEN_REV = 29
FROZEN_SHA16 = "815e08079aefbc16"
CONTROL_MANIFEST = HERE / "fixtures_r03/manifest.json"
V13_MANIFEST = HERE / "fixtures_v13/manifest.json"
LEGACY_MANIFEST = HERE / "fixtures/manifest.json"
LEGACY_SUITE = HERE / "legacy_v12/fixture_suite_report.v12_r03.json"
LEGACY_RECHECK = HERE / "legacy_v12/canonical_recheck_rev29.v12_r03.json"


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_gate():
    spec = importlib.util.spec_from_file_location("ccs", GATE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def reading(res):
    return {"semantic_pass": res["r03_readings"]["semantic"]["pass"],
            "literal_pass": res["r03_readings"]["literal"]["pass"],
            "literal_unused": [u["binder"] for u in res["r03_readings"]["literal"]["unused"]],
            "kind_sequence_declared": res["r03_readings"]["semantic"]["kind_sequence_declared"],
            "kind_sequence_found": res["r03_readings"]["semantic"]["kind_sequence_found"],
            "missing_variables": res["r03_readings"]["semantic"]["missing_variables"],
            "unbound_variables": res["r03_readings"]["semantic"]["unbound_variables"]}


def main() -> int:
    ccs = load_gate()
    rec = {
        "actor": "deepseek-flash-13",
        "gate": ccs.GATE_ID, "gate_version": ccs.GATE_VERSION, "spec": f"{ccs.SPEC_ID} v{ccs.SPEC_VERSION}",
        "gate_sha256": sha256_file(GATE),
        "rule_spec_sha256": sha256_file(RULE_SPEC),
        "frozen_rev_expected": FROZEN_REV, "frozen_sha256_expected": FROZEN_SHA16,
        "question": ("R03: 'quantifiers.formal is a single sentence using those binders'. Does a "
                     "declared tuple binder rendered variable-wise in the sentence satisfy it?"),
        "readings": {
            "L_literal": "every declared binder string occurs verbatim (rev1.2 criterion)",
            "S_semantic": ("formal keyword sequence equals declared kind sequence; every declared "
                           "binder variable occurs at or after its own quantifier keyword (rev1.3 "
                           "pass criterion)"),
        },
        "canonical": {}, "controls": {}, "m25": {}, "legacy_corpus_under_v13": {},
        "assertions": {}, "problems": [],
    }
    frozen = json.loads(FROZEN.read_text())
    files = frozen.get("files", {})
    rec["frozen_rev_measured"] = frozen.get("revision")
    rec["frozen_sha256_measured"] = sha256_file(FROZEN)

    a1 = frozen.get("revision") == FROZEN_REV and sha256_file(FROZEN)[:16] == FROZEN_SHA16
    for cid, p in CANON.items():
        pin = files.get(str(p.relative_to(REPO)), {}).get("sha256")
        meas = sha256_file(p)
        res_s = ccs.evaluate(p, cid, r03_mode="semantic")
        res_l = ccs.evaluate(p, cid, r03_mode="literal")
        rec["canonical"][cid] = {
            "path": str(p.relative_to(REPO)), "sha256": meas, "pin_sha256": pin,
            "frozen_match": meas == pin,
            "semantic_verdict": res_s["verdict"], "semantic_failed": res_s["failed_rules"],
            "literal_verdict": res_l["verdict"], "literal_failed": res_l["failed_rules"],
            "readings": reading(res_s),
        }
        a1 = a1 and meas == pin
    a2 = all(v["semantic_verdict"] == "pass" for v in rec["canonical"].values())
    wcc = rec["canonical"]["AF-WCC-VAC-GEN"]
    a3 = (wcc["literal_verdict"] == "fail" and wcc["literal_failed"] == ["R03"]
          and wcc["readings"]["literal_unused"] == ["(q,t0)"]
          and all(rec["canonical"][c]["literal_verdict"] == "pass"
                  for c in ("AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN")))

    cman = json.loads(CONTROL_MANIFEST.read_text())
    a4 = True
    for name, meta in cman["controls"].items():
        p = Path(meta["path"])
        res_s = ccs.evaluate(p, meta["class_id"], r03_mode="semantic")
        res_l = ccs.evaluate(p, meta["class_id"], r03_mode="literal")
        got = {"L": "pass" if res_l["r03_readings"]["literal"]["pass"] else "fail",
               "S": "pass" if res_s["r03_readings"]["semantic"]["pass"] else "fail"}
        ok = got == {"L": meta["expected"]["L"], "S": meta["expected"]["S"]}
        a4 = a4 and ok
        rec["controls"][name] = {"class_id": meta["class_id"], "sha256": sha256_file(p),
                                 "expected": meta["expected"], "measured": got,
                                 "literal_verdict": res_l["verdict"],
                                 "semantic_verdict": res_s["verdict"], "match": ok}
    a4 = a4 and len(cman["controls"]) == 10
    rec["controls_that_L_accepts_and_S_rejects"] = sorted(
        n for n, v in rec["controls"].items()
        if v["measured"] == {"L": "pass", "S": "fail"})

    v13man = json.loads(V13_MANIFEST.read_text())
    legman = json.loads(LEGACY_MANIFEST.read_text())
    a5 = True
    for label, man, key in (("legacy", legman, "legacy"), ("repaired_v13", v13man, "v13")):
        meta = man["mutants"]["m25_wcc_binder_unused"]
        p = Path(meta["path"])
        res = ccs.evaluate(p, meta["class_id"])
        rd = reading(res)
        rec["m25"][label] = {"path": str(p.relative_to(REPO)), "sha256": sha256_file(p),
                             "verdict": res["verdict"], "failed_rules": res["failed_rules"],
                             "readings": rd}
        a5 = a5 and res["verdict"] == "fail" and "R03" in res["failed_rules"]
    a5 = (a5
          and rec["m25"]["repaired_v13"]["readings"]["semantic_pass"] is False
          and rec["m25"]["repaired_v13"]["readings"]["kind_sequence_found"]
          == rec["m25"]["repaired_v13"]["readings"]["kind_sequence_declared"]
          and [m["variable"] for m in rec["m25"]["repaired_v13"]["readings"]["missing_variables"]] == ["t0"])

    # legacy corpus under v1.3: record the measured delta (positives fail on the kind defect)
    legacy_delta = {}
    for name, meta in legman["positives"].items():
        res = ccs.evaluate(Path(meta["path"]), meta["class_id"])
        legacy_delta[name] = {"verdict": res["verdict"], "failed_rules": res["failed_rules"]}
    rec["legacy_corpus_under_v13"]["positives"] = legacy_delta
    rec["legacy_corpus_under_v13"]["note"] = (
        "legacy positives fail v1.3 R03 because ordered[2].kind='exists' contradicts their own "
        "formal sentence 'not exists p'; this is the corpus defect repaired into fixtures_v13")
    rec["legacy_v12_suite_report_sha256"] = sha256_file(LEGACY_SUITE) if LEGACY_SUITE.exists() else None
    rec["legacy_v12_canonical_recheck_sha256"] = sha256_file(LEGACY_RECHECK) if LEGACY_RECHECK.exists() else None

    # A6: canonical bytes must not move during the audit
    a6 = all(sha256_file(p) == rec["canonical"][cid]["sha256"] for cid, p in CANON.items())
    a6 = a6 and sha256_file(FROZEN)[:16] == FROZEN_SHA16

    rec["assertions"] = {
        "A1_frozen_rev29_and_pins": a1,
        "A2_semantic_passes_all_three_canonicals": a2,
        "A3_literal_differs_only_on_wcc_tuple": a3,
        "A4_controls_match_matrix": a4,
        "A5_m25_still_fails_R03": a5,
        "A6_no_canonical_byte_drift": a6,
    }
    for k, v in rec["assertions"].items():
        if not v:
            rec["problems"].append(k)
    rec["verdict"] = "pass" if not rec["problems"] else "fail"

    (HERE / "r03_readings_rev29.json").write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")

    # per-schema canonical recheck record under v1.3
    recheck = {"actor": "deepseek-flash-13", "gate_version": ccs.GATE_VERSION,
               "mode": "canonical", "frozen_rev": frozen.get("revision"),
               "frozen_sha256": sha256_file(FROZEN), "gate_sha256": sha256_file(GATE),
               "results": [rec["canonical"][cid] for cid in ("AF-WCC-VAC-GEN",
                                                             "AF-SCC-C2-VAC-GEN",
                                                             "AF-SCC-C0-VAC-GEN")],
               "readings_record": "artifacts/flash-13/form_gate/r03_readings_rev29.json"}
    (HERE / "canonical_recheck_rev29_v13.json").write_text(json.dumps(recheck, indent=2, sort_keys=True) + "\n")

    print(json.dumps(rec["assertions"], indent=1))
    print("verdict:", rec["verdict"], "| S-rejects/L-accepts controls:",
          rec["controls_that_L_accepts_and_S_rejects"])
    print("wrote r03_readings_rev29.json and canonical_recheck_rev29_v13.json")
    return 0 if rec["verdict"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
