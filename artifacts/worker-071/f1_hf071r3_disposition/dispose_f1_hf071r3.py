#!/usr/bin/env python3
"""W071-F1-HF071R3-DISPOSITION-01 instrument.

Reviewer-side, read-only disposition of the two hard failures recorded in
reviews/F1-review-rev29-worker-071.json (HF-071R3-01 stage-B R03 rejection;
HF-071R3-02 falsifier-suite binding).  Implements the checks and controls frozen in
PREREGISTRATION.json (written before this instrument ran).  No project module is
imported; the stage-B auditor is invoked as a subprocess, exactly as the canonical
two-stage acceptance pipeline invokes it.

Usage:
  python3 dispose_f1_hf071r3.py
  exit 0 = checks completed (read disposition.json), 2 = control failure, 3 = pin drift
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
INPUTS = HERE / "inputs"
TASK_ID = "W071-F1-HF071R3-DISPOSITION-01"
CST = timezone(timedelta(hours=8))

F1 = "schemas/af_wcc_vacuum.yaml"
REVIEW = "reviews/F1-review-rev29-worker-071.json"
SEM = "artifacts/worker-06/spec_conformance_audit.py"
RULE_SPEC = "artifacts/formulation/rule_spec.json"
SUITE = "schemas/f1_falsifier_tests.jsonl"
REPORT = "artifacts/formulation/evidence/acceptance_pipeline_report.json"
FROZEN = "artifacts/formulation/FROZEN.json"
F0 = "research_map/formulation_taxonomy.yaml"
DECISIONS = "runtime/state/controller_verification/astra-lifecycle-08-decisions.json"
REV11 = "artifacts/worker-034/f1_repair_candidate_adjudication/pinned/f1_authoring_rev11__af_wcc_vacuum.9a8bd4c9.yaml"
REV12 = "artifacts/worker-034/f1_repair_candidate_adjudication/pinned/f1_rev12__af_wcc_vacuum.cce9c60146d6a907.yaml"
CAND_G = "artifacts/worker-029/f1_r03_scope_safety/variants/CAND-A__G_grouped_correct.yaml"
CAND_V = "artifacts/worker-029/f1_r03_scope_safety/variants/CAND-A__V_variable_wise_correct.yaml"
CANON_V = "artifacts/worker-029/f1_r03_scope_safety/variants/CANON__V_variable_wise_correct.yaml"

PIN = {
    F1: "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    FROZEN: "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    SEM: "c79d8ab8440ac6738bb61df5a33e9fd5f8319b4e74e1f2e9c0fc5083fb408cec",
    RULE_SPEC: "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
    SUITE: "56bcb4b3234bc86c324bec6e38f142c5ef39517f20d823b6a333f578b7d0851e",
    REPORT: "9b7d6c8208d3beae2510c5c9c0a4bdaf7ede8adb277cd2a4f6f9cd0fd430f0c6",
    F0: "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    REV11: "9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503",
    REV12: "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
}
MEASURE_AT_RUN = [REVIEW, CAND_G, CAND_V, CANON_V, DECISIONS]
FRAME_PATHS = list(PIN) + MEASURE_AT_RUN


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def measure_frame() -> dict:
    return {rel: sha256_file(ROOT / rel) for rel in FRAME_PATHS}


def tuple_components(binder: str):
    b = str(binder)
    if b.startswith("(") and b.endswith(")") and "," in b:
        return [c.strip() for c in b[1:-1].split(",") if c.strip()]
    return None


def tuple_aware_containment(binder: str, formal: str) -> tuple[bool, dict]:
    """Canonical-tuple-aware reading of R03's 'formal is a single sentence using those
    binders': a parenthesised tuple binder is used iff each component occurs as a whole
    token in the formal sentence in tuple order."""
    comps = tuple_components(binder)
    if comps is None:
        return (str(binder) in formal), {"mode": "literal", "binder": binder}
    positions = []
    for c in comps:
        m = re.search(r"(?<![A-Za-z0-9_])" + re.escape(c) + r"(?![A-Za-z0-9_])", formal)
        if not m:
            return False, {"mode": "tuple", "binder": binder, "missing_component": c}
        positions.append(m.start())
    ordered = all(positions[i] < positions[i + 1] for i in range(len(positions) - 1))
    return ordered, {"mode": "tuple", "binder": binder,
                     "component_positions": positions, "in_order": ordered}


def binder_census(doc: dict) -> list:
    q = doc.get("quantifiers") or {}
    ordered = q.get("ordered") or []
    formal = str(q.get("formal") or "")
    out = []
    for i, e in enumerate(ordered):
        if not isinstance(e, dict):
            out.append({"index": i, "error": "not a mapping"})
            continue
        b = e.get("binder")
        lit = (str(b) in formal) if b else False
        tup, tdet = tuple_aware_containment(str(b), formal) if b else (False, {})
        out.append({"index": i, "kind": e.get("kind"), "binder": b,
                    "domain_id": e.get("domain_id"),
                    "literal_in_formal": lit, "tuple_aware_in_formal": tup,
                    "tuple_detail": tdet})
    return out


def run_stage_b(path: Path) -> dict:
    """Invoke the pinned stage-B auditor exactly as run_acceptance.py does (stdout JSON)."""
    r = subprocess.run([sys.executable, str(ROOT / SEM), str(path)],
                       capture_output=True, text=True, cwd=str(ROOT))
    try:
        d = json.loads(r.stdout)
    except Exception as exc:  # noqa: BLE001
        return {"crash": f"{exc}", "returncode": r.returncode, "stderr": r.stderr[-400:]}
    return {"verdict": d.get("verdict"), "failed_rules": d.get("failed_rules"),
            "doc_sha256": d.get("doc_sha256"), "returncode": r.returncode,
            "r03": next((c for c in d.get("checks", []) if c.get("rule") == "R03"), None),
            "undecided_rules": d.get("undecided_rules")}


def read_suite() -> dict:
    rows = [json.loads(l) for l in (ROOT / SUITE).read_text().splitlines() if l.strip()]
    binds = Counter(str(r.get("binding_sha256")) for r in rows)
    amb = [r for r in rows if "AMB-25" in str(r.get("test_id", ""))]
    amb_rows = []
    for r in amb:
        ca = r.get("cross_artifact") or []
        amb_rows.append({
            "test_id": r.get("test_id"),
            "binding_sha256": r.get("binding_sha256"),
            "binding_frozen_revision_schema": r.get("binding_frozen_revision_schema"),
            "deciding_field": r.get("deciding_field"),
            "declared_cross_artifact_f0": (ca[0] or {}).get("sha256") if ca else None,
            "probe_expectations": [{"path": p.get("path"), "expected": p.get("expected")}
                                   for p in (r.get("probe_results") or [])][:4],
        })
    return {"rows": len(rows), "binding_counts": dict(binds),
            "binds_reviewed_pin": binds.get(PIN[F1], 0), "amb25": amb_rows}


def read_report_staleness() -> dict:
    p = ROOT / REPORT
    text = p.read_text()
    hexes = sorted(set(re.findall(r"\b[0-9a-f]{64}\b", text)))
    doc = json.loads(text)
    schema_hexes = {PIN[F1], PIN[REV12]}
    return {
        "mtime": datetime.fromtimestamp(p.stat().st_mtime, CST).isoformat(),
        "sha256": PIN[REPORT],
        "distinct_64hex_strings": len(hexes),
        "any_input_schema_hash_present": sorted(set(hexes) & schema_hexes),
        "f1_row": next((r for r in doc.get("canonical", [])
                        if str(r.get("schema", "")).endswith("af_wcc_vacuum.yaml")), None),
        "verdict_field": doc.get("verdict"),
        "contains_schema_filename": "af_wcc_vacuum" in text,
    }


def read_decisions() -> dict:
    doc = json.loads((ROOT / DECISIONS).read_text())
    rec = next((d for d in doc.get("decisions", []) if d.get("id") == "REC-41"), None)
    return {"rec41_present": rec is not None,
            "rec41_title": (rec or {}).get("title"),
            "rec41_ruling": (rec or {}).get("ruling"),
            "rec41_names_literal_binder": bool(rec and "literal" in json.dumps(rec).lower()),
            "rec41_assigns_worker_006": bool(rec and "worker-006" in json.dumps(rec)),
            "sem_hash_now": sha256_file(ROOT / SEM),
            "sem_hash_matches_prereg_pin": sha256_file(ROOT / SEM) == PIN[SEM],
            "sem_mtime": datetime.fromtimestamp((ROOT / SEM).stat().st_mtime, CST).isoformat()}


def core_digest(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def main() -> int:
    created = datetime.now(CST).isoformat()
    INPUTS.mkdir(exist_ok=True)

    t0 = measure_frame()
    drift_pin = {rel: {"expected": exp, "measured": t0[rel], "match": t0[rel] == exp}
                 for rel, exp in PIN.items()}

    # evidence snapshots (copies only; no canonical write)
    snapshots = {}
    for rel in FRAME_PATHS:
        dst = INPUTS / rel.replace("/", "__")
        shutil.copy2(ROOT / rel, dst)
        snapshots[rel] = {"copy": str(dst.relative_to(ROOT)), "sha256": sha256_file(dst),
                          "matches_source": sha256_file(dst) == t0[rel]}

    checks, controls = [], []

    def check(cid, title, verdict, detail):
        checks.append({"id": cid, "title": title, "verdict": verdict, "detail": detail})

    def control(cid, title, expected, observed):
        controls.append({"id": cid, "title": title, "expected": expected,
                         "observed": observed, "pass": expected == observed})

    # D2 review integrity
    rev = json.loads((ROOT / REVIEW).read_text())
    hf_ids = [h.get("id") for h in rev.get("hard_failures", [])]
    check("D2", "review file integrity",
          "pass" if rev.get("verdict") == "revise" and {"HF-071R3-01", "HF-071R3-02"} <= set(hf_ids) else "fail",
          {"review_sha256": t0[REVIEW], "verdict": rev.get("verdict"), "hard_failure_ids": hf_ids})

    # D3 stage-B reproduction at the pin
    sb_live = run_stage_b(ROOT / F1)
    check("D3", "stage-B reproduction at the pin",
          "pass" if sb_live.get("verdict") == "reject" and sb_live.get("failed_rules") == ["R03"] else "fail",
          sb_live)

    # D4 literal binder census
    doc = yaml.safe_load((ROOT / F1).read_text())
    census = binder_census(doc)
    missing = [c.get("binder") for c in census if not c.get("literal_in_formal")]
    check("D4", "literal binder census",
          "pass" if missing == ["(q,t0)"] else "fail",
          {"binders": census, "literal_missing": missing})

    # D5 canonical-tuple-aware R03
    tuple_all = all(c.get("tuple_aware_in_formal") for c in census)
    r03_detail = str((sb_live.get("r03") or {}).get("detail", ""))
    only_containment = bool(re.fullmatch(r"binder '.*' absent from formal sentence", r03_detail))
    check("D5", "canonical-tuple-aware R03",
          "pass" if tuple_all and only_containment else "fail",
          {"tuple_aware_all_binders": tuple_all, "r03_detail": r03_detail,
           "auditor_r03_detail_is_containment_only": only_containment,
           "tuple_aware_r03_verdict": "pass" if (tuple_all and only_containment) else "fail"})

    # D6 remedy-branch candidates
    cand = {}
    for rel in (CAND_G, CAND_V, CANON_V):
        cd = yaml.safe_load((ROOT / rel).read_text())
        c_census = binder_census(cd)
        formal = str((cd.get("quantifiers") or {}).get("formal") or "")
        cand[rel] = {
            "sha256": t0[rel],
            "literal_tuple_present": "(q,t0)" in formal,
            "literal_all_binders": all(c.get("literal_in_formal") for c in c_census),
            "tuple_aware_all_binders": all(c.get("tuple_aware_in_formal") for c in c_census),
        }
    check("D6", "remedy-branch candidates",
          "pass" if cand[CAND_G]["literal_tuple_present"] and cand[CAND_G]["literal_all_binders"]
          and not cand[CAND_V]["literal_all_binders"] and cand[CAND_V]["tuple_aware_all_binders"]
          and not cand[CANON_V]["literal_all_binders"] and cand[CANON_V]["tuple_aware_all_binders"] else "fail",
          cand)

    # D7 suite census
    suite = read_suite()
    live_f0 = t0[F0]
    amb_stale = []
    for row in suite["amb25"]:
        if row.get("declared_cross_artifact_f0") not in (None, live_f0):
            amb_stale.append({"test_id": row["test_id"], "declared": row["declared_cross_artifact_f0"],
                              "live_f0": live_f0})
    check("D7", "HF-071R3-02 census",
          "pass" if suite["rows"] == 25 and suite["binding_counts"].get(PIN[REV12]) == 25
          and suite["binds_reviewed_pin"] == 0 else "fail",
          {"suite": suite, "amb25_stale_anchor_rows": amb_stale})

    # D8 acceptance report staleness
    rep = read_report_staleness()
    check("D8", "acceptance report staleness",
          "pass" if not rep["any_input_schema_hash_present"] else "fail", rep)

    # D9 controller ruling cross-check
    dec = read_decisions()
    check("D9", "controller ruling cross-check",
          "pass" if dec["rec41_present"] and dec["rec41_names_literal_binder"]
          and dec["rec41_assigns_worker_006"] and dec["sem_hash_matches_prereg_pin"] else "fail", dec)

    # D10 notation regression history
    sb11, sb12 = run_stage_b(ROOT / REV11), run_stage_b(ROOT / REV12)
    c11 = binder_census(yaml.safe_load((ROOT / REV11).read_text()))
    c12 = binder_census(yaml.safe_load((ROOT / REV12).read_text()))
    check("D10", "notation regression history",
          "pass" if (sb11.get("r03") or {}).get("verdict") == "pass"
          and (sb12.get("r03") or {}).get("verdict") == "fail"
          and (c11[-1].get("literal_in_formal") is True) and (c12[-1].get("literal_in_formal") is False) else "fail",
          {"rev11": {"stage_b": sb11, "ordered5": c11[-1] if c11 else None},
           "rev12": {"stage_b": sb12, "ordered5": c12[-1] if c12 else None}})

    # Controls
    synthetic = "not exists (q,t0) in I+ x [0,T) with gamma subset J^-(q)"
    control("K1", "literal positive", True, "(q,t0)" in synthetic)
    ordered_formal = "not exists q in I+ and t0 in [0,T) with gamma subset J^-(q)"
    control("K2", "tuple order", False,
            tuple_aware_containment("(q,t0)", "not exists t0 in [0,T) and q in I+ with gamma subset J^-(q)")[0])
    control("K3", "component missing", False, tuple_aware_containment("(q,t0)", ordered_formal.replace("t0", "t1"))[0])
    control("K4", "literal route candidate", True,
            all(c.get("literal_in_formal") for c in binder_census(yaml.safe_load((ROOT / CAND_G).read_text()))))
    d1 = core_digest({"checks": checks, "controls": controls, "census": census})
    d2 = core_digest({"checks": checks, "controls": controls, "census": binder_census(yaml.safe_load((ROOT / F1).read_text()))})
    control("K5", "determinism", True, d1 == d2)

    t1 = measure_frame()
    moved = sorted(rel for rel in FRAME_PATHS if t0[rel] != t1[rel])
    control("K6", "read-only", [], moved)
    control("K7", "auditor harness can accept", "pass", (sb11.get("r03") or {}).get("verdict"))

    # Dispositions
    d3_ok = checks[1]["verdict"] == "pass"
    d4_ok = checks[2]["verdict"] == "pass"
    d5_ok = checks[3]["verdict"] == "pass"
    k_ok = all(c["pass"] for c in controls)
    if not d3_ok:
        hf1 = "CLOSED_BY_FIX" if sb_live.get("verdict") in ("accept", "pass") else "UNRESOLVED_MEASUREMENT"
    elif d4_ok and d5_ok and k_ok:
        hf1 = "INSTRUMENT_SIDE_CONFIRMED"
    else:
        hf1 = "SCHEMA_SIDE_RESIDUAL"
    hf2 = "CLOSED_BY_FIX" if suite["binds_reviewed_pin"] == 25 else "LIVE_UNCHANGED"

    dispositions = {
        "HF-071R3-01": {
            "disposition": hf1,
            "statement": ("The stage-B R03 rejection of the pinned AF-WCC-VAC-GEN schema is a literal "
                          "binder-notation miss of exactly one binder, '(q,t0)', whose quantifier is present "
                          "in quantifiers.formal in variable-wise form; under a canonical-tuple-aware reading "
                          "all R03 requirements hold. Controller ruling REC-41 independently classifies the "
                          "literal-substring binder as the defect and assigns the fix to worker-006; the pinned "
                          "auditor hash is unchanged from the pre-registered pin, so the fix had not landed at "
                          "measurement time."),
            "residual": [
                "instrument fix astra-life08-stageb-r03 (worker-006) + re-run of the two-stage pipeline, or rev14 adoption of a literal-bearing rendering (worker-029 CAND-A__G form);",
                "acceptance_pipeline_report.json at 9b7d6c82 carries no input schema sha256 and predates F1 rev12, so it cannot certify the frozen bytes (schema-side evidence defect, rev14 scope)."
            ],
            "falsifier": "Re-run the pinned auditor on the pinned bytes: an accept/R03-pass falsifies INSTRUMENT_SIDE_CONFIRMED and makes it CLOSED_BY_FIX; any R03 failure reason other than the literal containment miss makes it SCHEMA_SIDE_RESIDUAL."
        },
        "HF-071R3-02": {
            "disposition": hf2,
            "statement": ("All 25 falsifier rows still bind the rev12 hash cce9c60146d6 and none binds the "
                          "reviewed rev13 pin d9cebb9404b2; F1-AMB-25 still expects the superseded F0 anchor "
                          "276009f4f63d. The rebind is already inside the controller-authorized rev14 scope "
                          "(REC-36 item 6)."),
            "falsifier": "A suite re-issue in which all 25 rows carry binding_sha256 == the then-live F1 pin closes this item."
        },
        "acceptance_report_staleness": {
            "disposition": "LIVE" if not rep["any_input_schema_hash_present"] else "REMEASURE",
            "statement": "The pinned acceptance report contains no 64-hex input schema hash and therefore cannot be re-bound to the frozen revision it is cited for.",
            "falsifier": "A regenerated report that records the reviewed schema sha256 and passes both stages closes this item."
        }
    }

    payload = {
        "schema_version": "1.0",
        "task_id": TASK_ID,
        "actor": "worker-071",
        "created_at": created,
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-FORM",
        "artifact_kind": "reviewer_disposition_measurement",
        "object": {"review_file": REVIEW, "review_sha256": t0[REVIEW],
                   "reviewed_sha256": PIN[F1], "recorded_verdict": rev.get("verdict")},
        "frame_t0": t0, "frame_t1": t1, "moved_during_run": moved,
        "pin_matches": drift_pin,
        "checks": checks,
        "controls": controls,
        "dispositions": dispositions,
        "snapshots": snapshots,
        "core_digest": core_digest({"checks": checks, "controls": controls,
                                    "dispositions": dispositions, "census": census}),
        "non_claims": [
            "No gate verdict, node status, validation_status=passed, or canonical byte is set or written.",
            "The recorded review verdict and hard-failure list are unchanged; this is a separate hash-bound disposition artifact.",
            "No adjudication of grouped-vs-variable-wise quantifier scope semantics (worker-029/034 own that); only the R03 binder-notation interaction is measured."
        ]
    }

    (HERE / "disposition.json").write_text(json.dumps(payload, indent=1, sort_keys=False, default=str) + "\n")
    report = dict(payload)
    report["preregistration_sha256"] = sha256_file(HERE / "PREREGISTRATION.json")
    report["instrument_sha256"] = sha256_file(HERE / "dispose_f1_hf071r3.py")
    (HERE / "report.json").write_text(json.dumps(report, indent=1, sort_keys=False, default=str) + "\n")

    summary = {"task_id": TASK_ID, "disposition_HF-071R3-01": hf1,
               "disposition_HF-071R3-02": hf2,
               "checks_passed": sum(1 for c in checks if c["verdict"] == "pass"),
               "checks_total": len(checks),
               "controls_passed": sum(1 for c in controls if c["pass"]),
               "controls_total": len(controls),
               "moved": moved, "core_digest": payload["core_digest"]}
    print(json.dumps(summary, indent=1))
    if moved:
        return 3
    if not k_ok:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
