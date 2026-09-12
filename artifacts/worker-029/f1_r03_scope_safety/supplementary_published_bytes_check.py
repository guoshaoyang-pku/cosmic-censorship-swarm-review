#!/usr/bin/env python3
"""Disclosed post-hoc supplementary check for W029-F1-R03-CAND-SCOPE-SAFETY-01.

Runs the frozen auditor and the E3 auditor directly on the formulation lead's
*published* variant bytes (tmp/lead-form-life08/variant_*.yaml), not on the
re-derived variants used by the primary harness, and compares both tools to the
lead's published matrix in tmp/lead-form-life08/r03_scope_probe.json.

Post-hoc disclosure: this check was added after the pre-registered run, to remove
the objection that K5 exercised re-serialized rather than published bytes.  It
adds no new expectation and changes no pre-registered result.

Exit 0 valid, 3 pin mismatch.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
OUT = REPO / "artifacts/worker-029/f1_r03_scope_safety"
BASE_TOOL = REPO / "artifacts/worker-06/spec_conformance_audit.py"
E3_TOOL = REPO / "artifacts/worker-064/r03_cause/work/cand_E3/artifacts/worker-06/spec_conformance_audit.py"
LEAD = REPO / "tmp/lead-form-life08"
LEAD_PROBE = LEAD / "r03_scope_probe.json"
CST = timezone(timedelta(hours=8))

DECLARED = {
    "variant_frozen_variable_wise_intended_correct.yaml": "0f89efaec1bcaa0cdfe85b9e247255fcb3eb9379a9ce804cb483a4ca5f40e72e",
    "variant_grouped_tuple_intended_correct.yaml": "1d9f06f02d3af7fab4d0117bccf4dd9091ab71d3c74077d85e6d31b5401c3c0a",
    "variant_scope_error_negation_binds_q_only.yaml": "7663d4bc0a58e5c56c9dba4b6b49c3e7452f6f314a0e95ad0b97c025372e74d9",
}
KEYS = {
    "variant_frozen_variable_wise_intended_correct.yaml": "frozen_variable_wise_intended_correct",
    "variant_grouped_tuple_intended_correct.yaml": "grouped_tuple_intended_correct",
    "variant_scope_error_negation_binds_q_only.yaml": "scope_error_negation_binds_q_only",
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run(tool: Path, schema: Path) -> dict:
    r = subprocess.run([sys.executable, str(tool), str(schema)], capture_output=True, text=True, timeout=180)
    try:
        d = json.loads(r.stdout)
        v = str(d.get("verdict", d.get("status", "?"))).lower()
        failed = d.get("failed_rules", [])
    except Exception:
        v, failed = f"crash(exit{r.returncode})", []
    norm = "accept" if v in ("accept", "pass", "ok") else ("reject" if v in ("reject", "fail") else v)
    return {"exit": r.returncode, "verdict": norm, "failed_rules": failed}


def main() -> int:
    lead = json.loads(LEAD_PROBE.read_text())
    out = {"task_id": "W029-F1-R03-CAND-SCOPE-SAFETY-01", "check": "published-bytes E3 matrix reproduction",
           "created_at": datetime.now(CST).isoformat(timespec="seconds"),
           "disclosure": "post-hoc supplementary check (added after the pre-registered run; no expectation changed)",
           "tool_pins": {"frozen_auditor": sha(BASE_TOOL), "e3_auditor": sha(E3_TOOL)},
           "rows": {}}
    ok = True
    for fname, key in KEYS.items():
        p = LEAD / fname
        measured = sha(p)
        pin_ok = measured == DECLARED[fname]
        ok = ok and pin_ok
        base = run(BASE_TOOL, p)
        e3 = run(E3_TOOL, p)
        want_base = lead["results"][key]["baseline_literal"]["verdict"]
        want_e3 = lead["results"][key]["E3_variable_wise"]["verdict"]
        out["rows"][key] = {
            "published_path": str(p.relative_to(REPO)),
            "published_sha256": measured,
            "declared_sha256": DECLARED[fname],
            "pin_ok": pin_ok,
            "frozen_auditor": base,
            "frozen_auditor_lead": want_base,
            "frozen_match": base["verdict"] == want_base,
            "e3_auditor": e3,
            "e3_auditor_lead": want_e3,
            "e3_match": e3["verdict"] == want_e3,
        }
        ok = ok and base["verdict"] == want_base and e3["verdict"] == want_e3
    out["all_published_pins_ok"] = all(v["pin_ok"] for v in out["rows"].values())
    out["all_verdicts_match_lead_matrix"] = all(
        v["frozen_match"] and v["e3_match"] for v in out["rows"].values())
    out["pass"] = ok
    (OUT / "supplementary_published_bytes_check.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out["rows"], indent=1))
    print("pass:", out["pass"])
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
