#!/usr/bin/env python3
"""W058-CONTAIN-01 sensitivity self-test.

A containment audit that cannot fail is worthless.  This harness runs the
independent checker (check_containment_premise.py) over canonical inputs and
over five deliberately altered copies, and asserts a *pre-registered* expected
verdict for each.  The canonical tree is never written to: every mutant is
built in a scratch root under the system temp dir.

Pre-registered expectations
    M0  canonical revision            -> FAIL, exactly 1 hard failure,
                                         code class_size_premise_inverted
    M1  C0 'strictly larger' -> 'smaller' (the repair worker08 proposed)
                                      -> PASS, 0 hard failures
    M2  C2 entailment row from/to swapped (weaker -> stronger, claimed entails)
                                      -> FAIL with entailment_runs_weaker_to_stronger
    M3  C2 chain declaration reordered so C2 and C0 disagree
                                      -> FAIL with a chain-concordance problem
    M4  C0 subsumption_note gains an inverted size claim
                                      -> FAIL with class_size_premise_inverted
    M5  byte-identical copy           -> identical verdict to M0 (stability)

Exit 0 iff every expectation holds.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CST = timezone(timedelta(hours=8))

spec = importlib.util.spec_from_file_location("ccp", HERE / "check_containment_premise.py")
ccp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ccp)

SCHEMAS = {
    "schemas/af_scc_c2_vacuum.yaml": None,
    "schemas/af_scc_c0_vacuum.yaml": None,
    "schemas/af_wcc_vacuum.yaml": None,
}
FROZEN_REL = "artifacts/formulation/FROZEN.json"

M1_OLD = '"C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker"'
M1_NEW = '"C2 is a strictly smaller extension class, so C2-inextendibility is strictly weaker"'
M2_OLD = '{from: "no proper future C0 extension", to: "no proper future C2 extension", relation: entails'
M2_NEW = '{from: "no proper future C2 extension", to: "no proper future C0 extension", relation: entails'
M3_OLD = "E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0 (nested extension sets)"
M3_NEW = "E_C2 subset of E_{C^1,1} subset of E_C0 subset of E_H2loc (nested extension sets)"
M4_OLD = 'This direction runs C0 => H2loc => C2, never the reverse."'
M4_NEW = 'This direction runs C0 => H2loc => C2, never the reverse. C2 is a strictly larger extension class."'


def build_root(mutate=None) -> tuple[Path, dict]:
    """Copy the canonical inputs into a scratch root, apply mutate(texts)."""
    tmp = Path(tempfile.mkdtemp(prefix="w058-selftest-"))
    for rel in list(SCHEMAS) + [FROZEN_REL]:
        src = ROOT / rel
        dst = tmp / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    texts = {rel: (tmp / rel).read_text(encoding="utf-8") for rel in SCHEMAS}
    if mutate:
        texts = mutate(texts)
    for rel, t in texts.items():
        (tmp / rel).write_text(t, encoding="utf-8")
    return tmp, texts


def run_case(name: str, mutate=None) -> dict:
    tmp, _ = build_root(mutate)
    try:
        res = ccp.audit(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    codes = sorted({f["code"] for f in res.get("hard_failures", [])})
    return {
        "case": name,
        "verdict": res.get("verdict"),
        "hard_failure_count": res.get("hard_failure_count"),
        "failure_codes": codes,
        "chain_problems": res.get("chain_problems"),
        "checked_statement_count": res.get("checked_statement_count"),
        "binding_mode": res.get("binding_status", {}).get("mode"),
    }


def m1(t):
    assert M1_OLD in t["schemas/af_scc_c0_vacuum.yaml"], "M1 anchor missing"
    t["schemas/af_scc_c0_vacuum.yaml"] = t["schemas/af_scc_c0_vacuum.yaml"].replace(M1_OLD, M1_NEW)
    return t


def m2(t):
    assert M2_OLD in t["schemas/af_scc_c2_vacuum.yaml"], "M2 anchor missing"
    t["schemas/af_scc_c2_vacuum.yaml"] = t["schemas/af_scc_c2_vacuum.yaml"].replace(M2_OLD, M2_NEW)
    return t


def m3(t):
    assert M3_OLD in t["schemas/af_scc_c2_vacuum.yaml"], "M3 anchor missing"
    t["schemas/af_scc_c2_vacuum.yaml"] = t["schemas/af_scc_c2_vacuum.yaml"].replace(M3_OLD, M3_NEW)
    return t


def m4(t):
    assert M4_OLD in t["schemas/af_scc_c0_vacuum.yaml"], "M4 anchor missing"
    t["schemas/af_scc_c0_vacuum.yaml"] = t["schemas/af_scc_c0_vacuum.yaml"].replace(M4_OLD, M4_NEW)
    return t


def main() -> int:
    cases = []
    m0 = run_case("M0_canonical", None)
    m0["expected"] = "FAIL with exactly 1 class_size_premise_inverted, >=20 statements checked"
    m0["ok"] = (
        m0["verdict"] == "FAIL"
        and m0["hard_failure_count"] == 1
        and m0["failure_codes"] == ["class_size_premise_inverted"]
        and (m0["checked_statement_count"] or 0) >= 20
        and m0["binding_mode"] in {"FROZEN", "LIVE_ONLY_FROZEN_STALE"}
    )
    cases.append(m0)

    m1r = run_case("M1_repaired_reason", m1)
    m1r["expected"] = "PASS with 0 hard failures (proves the flag is caused by that token)"
    m1r["ok"] = m1r["verdict"] == "PASS" and m1r["hard_failure_count"] == 0
    cases.append(m1r)

    m2r = run_case("M2_swapped_entailment", m2)
    m2r["expected"] = "FAIL containing entailment_runs_weaker_to_stronger"
    m2r["ok"] = m2r["verdict"] == "FAIL" and "entailment_runs_weaker_to_stronger" in m2r["failure_codes"]
    cases.append(m2r)

    m3r = run_case("M3_reordered_chain", m3)
    m3r["expected"] = "FAIL with a chain-concordance or declaration-edge problem"
    m3r["ok"] = m3r["verdict"] == "FAIL" and (
        bool(m3r["chain_problems"]) or "declaration_edge_contradicts_reference" in m3r["failure_codes"]
    )
    cases.append(m3r)

    m4r = run_case("M4_planted_size_inversion", m4)
    m4r["expected"] = "FAIL containing class_size_premise_inverted"
    m4r["ok"] = m4r["verdict"] == "FAIL" and "class_size_premise_inverted" in m4r["failure_codes"]
    cases.append(m4r)

    m5r = run_case("M5_byte_identical_copy", None)
    m5r["expected"] = "verdict and failure count identical to M0"
    m5r["ok"] = (
        m5r["verdict"] == m0["verdict"]
        and m5r["hard_failure_count"] == m0["hard_failure_count"]
        and m5r["failure_codes"] == m0["failure_codes"]
    )
    cases.append(m5r)

    payload = {
        "artifact": "W058-CONTAIN-01 sensitivity self-test",
        "worker": "worker-058",
        "actor": "deepseek-flash-058",
        "task_id": "W058-CONTAIN-01",
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "checker": "artifacts/worker-058/containment_premise/check_containment_premise.py",
        "checker_sha256": hashlib.sha256(
            (HERE / "check_containment_premise.py").read_bytes()
        ).hexdigest(),
        "canonical_root": str(ROOT),
        "bound_schema_hashes": {
            rel: hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() for rel in SCHEMAS
        },
        "case_count": len(cases),
        "cases": cases,
        "all_expectations_met": all(c["ok"] for c in cases),
        "interpretation": (
            "If all_expectations_met is false this audit's verdict must be treated as "
            "invalid, because the checker either fails to detect a planted defect or "
            "flags a repaired/byte-identical input."
        ),
    }
    out = json.dumps(payload, indent=2)
    (HERE / "sensitivity_selftest.json").write_text(out + "\n", encoding="utf-8")
    print(out)
    return 0 if payload["all_expectations_met"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
