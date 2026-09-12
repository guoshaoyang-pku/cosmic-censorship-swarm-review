#!/usr/bin/env python3
"""W080-CLASSSEP-DISJ-01 -- candidate rule for rubric HF-02 "disjunction of class_ids".

One bounded class-bound task (worker-080, 2026-09-12). Classes: AF-WCC-VAC-GEN,
AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN. Node A1; gate G-AUDIT (calibration evidence only).

Question: worker-036 (2026-09-12T00:38) measured that `research_map/class_separation.py`
is silent on a `class_ids` container binding >=2 distinct frozen classes -- the live L0
HF-02 condition (8 rows at ledger/theorems.jsonl a1674f094979) -- and proposed
"add a list-disjunction rule (>=2 known class tokens in one class_ids container ->
finding) plus >=1 positive and >=1 negative fixture ... re-run regression".
This harness (a) falsifies the *unscoped* version of that proposal by measuring its blast
radius on the live map, (b) implements and measures a scoped candidate that fires on
asserted containers only, and (c) verifies no collateral change to the detector's other
verdicts (worker-07 corpus, schemas, map).

Read-only on every canonical path. All runs happen in-process on bytes hashed at entry;
input hashes are re-measured at exit. No gate verdict, no node status, no canonical write.
"""
from __future__ import annotations

import difflib
import hashlib
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.dont_write_bytecode = True  # never create __pycache__ in canonical trees

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TZ = timezone(timedelta(hours=8))

CANON = ROOT / "research_map/class_separation.py"
CAND = HERE / "class_separation_disj_candidate.py"
LEDGER = ROOT / "ledger/theorems.jsonl"
RUBRIC = ROOT / "evaluation_rubric.yaml"
MAP = ROOT / "research_map/research_map.json"
CORPUS = ROOT / "artifacts/worker-07/class_separation_falsification/results.json"
AUDIT_LIB = ROOT / "artifacts/audit/audit_lib.py"
SCHEMAS = [ROOT / "schemas/af_wcc_vacuum.yaml",
           ROOT / "schemas/af_scc_c2_vacuum.yaml",
           ROOT / "schemas/af_scc_c0_vacuum.yaml"]

# Pins measured at 2026-09-12 ~00:52 (+08:00). Any drift voids the affected rows.
PINS = {
    "research_map/class_separation.py": "c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920",
    "ledger/theorems.jsonl": "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28",
    "evaluation_rubric.yaml": "d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885",
    "artifacts/worker-07/class_separation_falsification/results.json":
        "d69ad58468be16655921dcf0eab9570fa6e7ccaf828558a45d4b306cce3de452",
    "artifacts/audit/audit_lib.py": "ae573db84631b970caeea46e8821aee8af66166f6a5f16251e4a6c819a377c8c",
    "schemas/af_wcc_vacuum.yaml": "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
    "schemas/af_scc_c2_vacuum.yaml": "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
    "schemas/af_scc_c0_vacuum.yaml": "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
}

EXPECTED_LEDGER_IDS = ["D-004", "D-005", "T-303", "T-305", "T-402", "T-515", "T-526", "T-528"]
KNOWN = {"AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"}


def now() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod  # dataclasses in audit_lib need the module registered
    spec.loader.exec_module(mod)
    return mod


def repo_regression(module) -> dict:
    """Replicate research_map.class_separation.regression() with the repo root forced to
    ROOT (the candidate module lives outside research_map/, so its own __file__-relative
    root would be wrong). Ground truth is the corpus's independent is_class_merge field."""
    res = json.loads(CORPUS.read_text())
    tp = fn = tn = fp = 0
    per_fixture = {}
    for fx in res["fixtures"]:
        m = json.loads((ROOT / fx["fixture_path"]).read_text())
        det = module.findings_for_map(m)
        for g in m.get("groups", []):
            for n in g.get("nodes", []):
                art = n.get("artifact")
                if art and (ROOT / art).is_file():
                    det += module.findings_for_text(
                        (ROOT / art).read_text(errors="replace"), f"artifact {art}")
        got, truth = bool(det), bool(fx["is_class_merge"])
        per_fixture[fx["id"]] = got
        if truth and got:
            tp += 1
        elif truth and not got:
            fn += 1
        elif not truth and got:
            fp += 1
        else:
            tn += 1
    return {"tp": tp, "fn": fn, "tn": tn, "fp": fp,
            "verdict": "PASS" if fn == 0 and fp == 0 else "DEFECTIVE",
            "corpus_size": tp + fn + tn + fp, "per_fixture_detected": per_fixture}


STRUCT_POS = [
    ("P1_two_class_list",
     {"theorem_id": "FX-P1", "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"]}),
    ("P2_three_class_list",
     {"theorem_id": "FX-P2",
      "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-VAC-GEN"]}),
    ("P3_comma_string",
     {"theorem_id": "FX-P3", "class_ids": "AF-SCC-C0-VAC-GEN,AF-SCC-C2-VAC-GEN"}),
    ("P4_semicolon_string",
     {"theorem_id": "FX-P4", "class_ids": "AF-SCC-C0-VAC-GEN; AF-SCC-C2-VAC-GEN"}),
    ("P5_wcc_plus_scc_list",
     {"theorem_id": "FX-P5", "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C0-VAC-GEN"]}),
]
STRUCT_NEG = [
    ("N1_single_class_list", {"theorem_id": "FX-N1", "class_ids": ["AF-SCC-C0-VAC-GEN"]}),
    ("N2_empty_list", {"theorem_id": "FX-N2", "class_ids": []}),
    ("N3_duplicate_same_class",
     {"theorem_id": "FX-N3", "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C0-VAC-GEN"]}),
    ("N4_unknown_only", {"theorem_id": "FX-N4", "class_ids": ["AF-SCC-REG-VAC-GEN"]}),
    ("N5_singular_string", {"theorem_id": "FX-N5", "class_id": "AF-SCC-C0-VAC-GEN"}),
    ("N6_null_container", {"theorem_id": "FX-N6", "class_ids": None}),
]
TEXT_POS = [
    ("T1_flow_list_line", "class_ids: [AF-SCC-C0-VAC-GEN, AF-SCC-C2-VAC-GEN]\nstatement: x\n"),
    ("T2_comma_line", "class_ids: AF-WCC-VAC-GEN,AF-SCC-C0-VAC-GEN\nstatement: x\n"),
]
TEXT_NEG = [
    ("T3_single_line", "class_id: AF-SCC-C0-VAC-GEN\nstatement: x\n"),
    ("T4_prose_mention", "notes: compares AF-SCC-C0-VAC-GEN with AF-SCC-C2-VAC-GEN\n"),
    ("T5_exclusion_flowmap", '- {class_id: AF-SCC-C2-VAC-GEN, why: "different class"}\n'),
]


def naive_container_count(m: dict) -> int:
    """Unscoped counterfactual: every class_id/class_ids *key instance* whose value carries
    >=2 distinct frozen tokens, anywhere in the map (nodes, claims, reviews, events,
    assignments).  An object carrying both keys counts twice, as the naive rule would."""
    n = 0

    def walk(o):
        nonlocal n
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("class_id", "class_ids"):
                    if isinstance(v, str):
                        toks = [t.strip().strip("'\"").upper() for t in re.split(r"[;,]", v)]
                    elif isinstance(v, list):
                        toks = [str(x).strip().strip("'\"").upper() for x in v]
                    else:
                        toks = []
                    if len({t for t in toks if t in KNOWN}) >= 2:
                        n += 1
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(m)
    return n


def write_fixtures() -> list:
    fixtures = []
    for cid, payload in STRUCT_POS + STRUCT_NEG:
        p = HERE / "fixtures" / f"{cid}.json"
        p.write_text(json.dumps(payload, indent=1, sort_keys=True))
        fixtures.append({"id": cid, "path": str(p.relative_to(ROOT)), "sha256": sha256_file(p)})
    for cid, body in TEXT_POS + TEXT_NEG:
        p = HERE / "fixtures" / f"{cid}.yaml"
        p.write_text(body)
        fixtures.append({"id": cid, "path": str(p.relative_to(ROOT)), "sha256": sha256_file(p)})
    return fixtures


def measure(cand, canon, audit_lib, fixtures) -> dict:
    pins_entry = {rel: sha256_file(ROOT / rel) for rel in PINS}
    map_sha_entry = sha256_file(MAP)

    reg_canon = repo_regression(canon)
    reg_cand = repo_regression(cand)
    per_fixture_identical = reg_canon["per_fixture_detected"] == reg_cand["per_fixture_detected"]

    struct = []
    for cid, payload in STRUCT_POS:
        f = cand.disjunction_findings(payload, f"fixtures.{cid}")
        struct.append({"id": cid, "expect": "flag", "findings": f, "ok": len(f) == 1})
    for cid, payload in STRUCT_NEG:
        f = cand.disjunction_findings(payload, f"fixtures.{cid}")
        struct.append({"id": cid, "expect": "clean", "findings": f, "ok": len(f) == 0})

    text = []
    for cid, body in TEXT_POS:
        f = [x for x in cand.findings_for_text(body, f"fixtures.{cid}")
             if "disjunction of class_ids" in x]
        text.append({"id": cid, "expect": "flag", "findings": f, "ok": len(f) == 1})
    for cid, body in TEXT_NEG:
        f = [x for x in cand.findings_for_text(body, f"fixtures.{cid}")
             if "disjunction of class_ids" in x]
        text.append({"id": cid, "expect": "clean", "findings": f, "ok": len(f) == 0})

    rows = [json.loads(l) for l in LEDGER.read_text().splitlines() if l.strip()]
    ledger_findings = cand.findings_for_ledger(rows, "ledger")
    flagged = []
    for f in ledger_findings:
        m = re.search(r"ledger\[\d+\]:([A-Z]+-\d+)\.class_ids", f)
        flagged.append(m.group(1) if m else f)
    flagged_ids = sorted(set(flagged))
    ledger_ok = (len(ledger_findings) == len(EXPECTED_LEDGER_IDS)
                 and flagged_ids == sorted(EXPECTED_LEDGER_IDS))

    schema_rows = []
    for p in SCHEMAS:
        f = [x for x in cand.findings_for_text(p.read_text(), f"schema {p.name}")
             if "disjunction of class_ids" in x]
        schema_rows.append({"path": str(p.relative_to(ROOT)), "disjunction_findings": f,
                            "ok": len(f) == 0})

    m = json.loads(MAP.read_text())
    naive = naive_container_count(m)
    canon_total = canon.findings_for_map(m)
    cand_total = cand.findings_for_map(m)
    map_disj = [x for x in cand_total if "disjunction of class_ids" in x]

    classes = audit_lib.frozen_classes(audit_lib.load_rubric(RUBRIC))
    probes = []
    for pid, claim in (
        ("P1_singular_plus_list",
         {"claim_id": "W080-P1", "class_id": "AF-SCC-C2-VAC-GEN",
          "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
          "statement": "A regularity statement under the frozen C2 hypotheses.",
          "assumptions": ["x"], "falsifier": "f", "conclusion_type": "open_problem"}),
        ("P2_list_only",
         {"claim_id": "W080-P2", "class_id": None,
          "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
          "statement": "A statement whose row carries two class_ids entries.",
          "assumptions": ["x"], "falsifier": "f", "conclusion_type": "open_problem"}),
    ):
        vs = audit_lib.check_class_binding(claim, classes)
        probes.append({"id": pid,
                       "violations": [{"hf": v.hf, "detail": v.detail} for v in vs],
                       "names_disjunction_condition":
                           any("disjunction of class_ids" in (v.detail or "") for v in vs)})

    # advisory: hash hygiene on the review event this task is built on (not gated)
    measured_cs = pins_entry["research_map/class_separation.py"]
    hygiene = []
    for r in m.get("reviews", []):
        if r.get("reviewer") == "worker-036" and r.get("target_id") == "research_map/class_separation.py":
            declared = r.get("target_sha256")
            hygiene.append({"declared_target_sha256": declared, "measured": measured_cs,
                            "exact_match": declared == measured_cs,
                            "prefix8_match": bool(declared) and declared[:8] == measured_cs[:8]})

    pins_exit = {rel: sha256_file(ROOT / rel) for rel in PINS}
    map_sha_exit = sha256_file(MAP)

    expectations = {
        "E2_regression_candidate_PASS": reg_cand["verdict"] == "PASS",
        "E3_regression_identical_to_canonical":
            per_fixture_identical and reg_cand["tp"] == reg_canon["tp"]
            and reg_cand["tn"] == reg_canon["tn"],
        "E4_all_structured_positives_flag": all(r["ok"] for r in struct if r["expect"] == "flag"),
        "E5_all_structured_negatives_clean": all(r["ok"] for r in struct if r["expect"] == "clean"),
        "E6_all_text_positives_flag": all(r["ok"] for r in text if r["expect"] == "flag"),
        "E7_all_text_negatives_clean": all(r["ok"] for r in text if r["expect"] == "clean"),
        "E8_ledger_exactly_the_8_rows": ledger_ok,
        "E9_schemas_zero_disjunction": all(r["ok"] for r in schema_rows),
        "E10_map_no_collateral_change": canon_total == cand_total,
        "E11_map_no_disjunction_findings": len(map_disj) == 0,
        "E12_pins_stable": pins_entry == pins_exit,
        "E13_naive_rule_blast_radius_measured": naive >= 2,
        "E14_probe_documents_audit_side_gap": all(not p["names_disjunction_condition"]
                                                  for p in probes),
    }

    return {
        "task_id": "W080-CLASSSEP-DISJ-01",
        "created_at": now(),
        "worker": "worker-080",
        "node_id": "A1",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate": "G-AUDIT",
        "question": ("Is the detector blind to rubric HF-02 'disjunction of class_ids'; "
                     "can a scoped rule close the gap without colliding with scope lists?"),
        "pins_entry": pins_entry,
        "pins_exit": pins_exit,
        "map_sha256_entry": map_sha_entry,
        "map_sha256_exit": map_sha_exit,
        "map_drift_during_run": map_sha_entry != map_sha_exit,
        "candidate": {"path": str(CAND.relative_to(ROOT)), "sha256": sha256_file(CAND)},
        "fixtures": fixtures,
        "regression": {"canonical": reg_canon, "candidate": reg_cand,
                       "per_fixture_identical": per_fixture_identical},
        "structured_cases": struct,
        "text_cases": text,
        "ledger": {"path": "ledger/theorems.jsonl", "sha256": pins_entry["ledger/theorems.jsonl"],
                   "rows": len(rows), "findings": ledger_findings,
                   "flagged_ids": flagged_ids, "expected_ids": sorted(EXPECTED_LEDGER_IDS),
                   "ok": ledger_ok},
        "schemas": schema_rows,
        "map": {"path": "research_map/research_map.json",
                "naive_any_container_rule_count": naive,
                "naive_counterfactual_note": ("class_id/class_ids key instances with >=2 distinct "
                                              "frozen tokens, anywhere in the map; an object "
                                              "carrying both keys counts twice"),
                "candidate_disjunction_findings": map_disj,
                "canonical_total_findings": len(canon_total),
                "candidate_total_findings": len(cand_total)},
        "audit_lib_probe": probes,
        "hash_hygiene_observation": hygiene,
        "expectations": expectations,
        "expectations_met": all(expectations.values()),
        "verdict": ("CANDIDATE_RULE_MEASURED" if all(expectations.values())
                    else "EXPECTATION_FAILED"),
        "falsifier": (
            "Re-run this harness at the pinned input hashes: any change in the worker-07 "
            "regression score, any structured positive not flagged, any negative flagged, a "
            "ledger finding set other than the 8 named rows, a disjunction finding on a "
            "frozen schema or on the map under the scoped rule, a collateral change to the "
            "detector's other map findings, or input-hash drift voids this report. A "
            "genuine HF-02 disjunction (a ledger/claim row asserting one result under two "
            "frozen classes) that the scoped rule does not flag, or a legitimate single-class "
            "container the rule flags, falsifies the rule itself."),
        "limits": [
            "Worker-side candidate only: no canonical path was modified; adoption is the "
            "detector owner's decision.",
            "Scoped to asserted containers (structured rows / asserted class_id[:] lines); "
            "map scope/coverage lists are out of scope by design.",
            "The naive counterfactual count is the reason for the scope, not a claim that "
            "every naive hit is illegitimate -- some map claims may be genuine HF-02 items "
            "for the audit lead to adjudicate separately.",
            "The audit_lib probe only records that the implemented HF-02 does not name this "
            "condition; it asserts nothing about other HF-02 branches.",
        ],
    }


def main() -> int:
    canon = load_module("cs_canon", CANON)
    cand = load_module("cs_cand", CAND)
    audit_lib = load_module("audit_lib_w080", AUDIT_LIB)

    fixtures = write_fixtures()
    first = measure(cand, canon, audit_lib, fixtures)
    second = measure(cand, canon, audit_lib, fixtures)

    def body(r):
        return {k: v for k, v in r.items()
                if k not in ("created_at", "map_sha256_entry", "map_sha256_exit",
                             "map_drift_during_run")}

    deterministic = body(first) == body(second)

    final = first
    final["determinism"] = {"identical_measurement_body": deterministic}
    final["expectations"]["E15_deterministic"] = deterministic
    final["expectations_met"] = all(final["expectations"].values())
    final["verdict"] = ("CANDIDATE_RULE_MEASURED" if final["expectations_met"]
                        else "EXPECTATION_FAILED")

    diff = "".join(difflib.unified_diff(
        CANON.read_text().splitlines(keepends=True),
        CAND.read_text().splitlines(keepends=True),
        fromfile="research_map/class_separation.py", tofile=str(CAND.relative_to(ROOT))))
    (HERE / "patch.diff").write_text(diff)
    final["patch"] = {"path": "artifacts/worker-080/classsep_disj/patch.diff",
                      "sha256": sha256_file(HERE / "patch.diff")}

    (HERE / "report.json").write_text(json.dumps(final, indent=1, sort_keys=True))
    print(json.dumps({"verdict": final["verdict"],
                      "expectations_met": final["expectations_met"],
                      "expectations": final["expectations"],
                      "ledger_flagged_ids": final["ledger"]["flagged_ids"],
                      "naive_map_count": final["map"]["naive_any_container_rule_count"],
                      "regression_candidate": {k: v for k, v in final["regression"]["candidate"].items()
                                               if k != "per_fixture_detected"},
                      "report_sha256": sha256_file(HERE / "report.json")}, indent=2))
    return 0 if final["expectations_met"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
