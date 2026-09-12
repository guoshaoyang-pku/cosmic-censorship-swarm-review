#!/usr/bin/env python3
"""Disclosed post-hoc amendment to W062-GFORM-R03-SCOPE-SAFE-RULE-CANDIDATE-01.

Two things, both written AFTER the pre-registered run and both labelled post-hoc:

 A1. E11's pre-registered *property* is "the E4 patch applies to exactly one block
     in the baseline bytes and the resulting file differs from baseline in one hunk".
     The harness measured "differs in one hunk" with a positional line-by-line zip,
     which reports 446 because the +22 inserted lines shift every later line.
     Correct instrument: difflib unified diff -> hunk count. This amendment recomputes
     it and records BOTH readings. The pre-registered verdict stays PARTIAL.

 A2. Direct run on the published canonical F1 bytes (`schemas/af_wcc_vacuum.yaml`,
     d9cebb9404b2) rather than on the harness's YAML round-trip variant V0, for all
     three tools. Corroboration only; not part of the pre-registered matrix.
"""
from __future__ import annotations

import difflib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CST = timezone(timedelta(hours=8))
SB = HERE / "sandbox"

BASE = ROOT / "artifacts/worker-06/spec_conformance_audit.py"
E4 = SB / "tools/E4/spec_conformance_audit.py"
SPEC = ROOT / "artifacts/formulation/rule_spec.json"
F1 = ROOT / "schemas/af_wcc_vacuum.yaml"


def sha(p):
    import hashlib
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def now():
    return datetime.now(CST).isoformat(timespec="seconds")


def hunk_count(a: str, b: str):
    diff = list(difflib.unified_diff(a.splitlines(keepends=True), b.splitlines(keepends=True),
                                     fromfile="baseline", tofile="E4", n=3))
    hunks = [i for i, line in enumerate(diff) if line.startswith("@@")]
    changed = sum(1 for line in diff if line[:1] in "+-" and not line.startswith(("+++", "---")))
    return {"unified_diff_hunks": len(hunks), "unified_diff_changed_lines": changed,
            "unified_diff": "".join(diff)}


def run(tool, schema, out):
    r = subprocess.run([sys.executable, str(tool), str(schema), "--spec", str(SPEC), "--json", str(out)],
                       capture_output=True, text=True, timeout=180)
    rep = json.loads(out.read_text()) if out.exists() else {}
    if out.exists():
        out.unlink()
    return {"exit": r.returncode, "verdict": rep.get("verdict", "?"),
            "failed_rules": rep.get("failed_rules", []), "doc_sha256": rep.get("doc_sha256")}


def main():
    base_text = BASE.read_text()
    e4_text = E4.read_text()
    hc = hunk_count(base_text, e4_text)

    tools = {
        "baseline_literal": SB / "tools/base/spec_conformance_audit.py",
        "E3_variable_wise": SB / "tools/E3/spec_conformance_audit.py",
        "E4_scope_aware": E4,
    }
    direct = {}
    for name, tool in tools.items():
        direct[name] = run(tool, F1, SB / "out" / f"amend_{name}.json")

    pins = {
        "schemas/af_wcc_vacuum.yaml": sha(F1),
        "artifacts/worker-06/spec_conformance_audit.py": sha(BASE),
        "sandbox/tools/E4/spec_conformance_audit.py": sha(E4),
    }
    out = {
        "amendment_id": "W062-GFORM-R03-SCOPE-SAFE-RULE-CANDIDATE-01-A1",
        "actor": "worker-062",
        "created_at": now(),
        "post_hoc": True,
        "disclosure": "Written after the pre-registered run. No expectation, candidate byte or verdict is changed; the pre-registered verdict remains PARTIAL because E11 failed as implemented.",
        "A1_E11_instrument_correction": {
            "pre_registered_property": "patch applies to exactly one block (C6 PASS: base block occurs once) and the resulting file differs from baseline in one hunk",
            "as_measured_by_harness": {"method": "positional line zip", "changed_lines": 446, "result": "FAIL"},
            "corrected_measurement": hc,
            "reading": "one contiguous replacement; the harness's 446 is an artifact of positional comparison across a +22-line insertion, not a multi-hunk patch",
        },
        "A2_direct_canonical_bytes_corroboration": {
            "schema": "schemas/af_wcc_vacuum.yaml",
            "schema_sha256": sha(F1),
            "note": "V0 in the pre-registered matrix is a YAML round-trip of the canonical document; this runs the published bytes directly",
            "results": direct,
            "expected": {"baseline_literal": "reject/R03", "E3_variable_wise": "accept", "E4_scope_aware": "accept"},
        },
        "pins_at_amendment": pins,
    }
    (HERE / "AMENDMENT_01.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({k: out[k] for k in ("A1_E11_instrument_correction", "A2_direct_canonical_bytes_corroboration")}, indent=1)[:3000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
