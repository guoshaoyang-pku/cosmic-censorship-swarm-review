#!/usr/bin/env python3
"""W008-F2B-DUALREPAIR-01 — control battery.

Runs the audit checker (same CLI a reviewer would use) over:
  ctl0_noop        canonical copy                       expect FAIL, both defects
  ctl1_revert251   candidate, D2 clause reverted        expect FAIL, only size_premise_inverted
  ctl2_revert157   candidate, D1 denial reverted        expect FAIL, only false_containment_denial
  candidate        the 2-edit repair                    expect PASS
  canonical        live frozen rev11                    expect FAIL, both defects
Each result is written to evidence/controls/<name>.json; the summary is
evidence/controls_summary.json.  Exit 0 only if every expectation holds.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
AUDIT = ROOT / "audit_dual_defect.py"
C2_LIVE = REPO / "schemas" / "af_scc_c2_vacuum.yaml"
C2_EXPECT = "b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2"
EXPECT_C0 = "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508"

sys.path.insert(0, str(ROOT))
from build_candidate import OLD_BULLET, OLD_REASON, NEW_BULLET, NEW_REASON, sha256_text  # noqa: E402

CTL = ROOT / "evidence" / "controls"
CTL.mkdir(parents=True, exist_ok=True)


def run_checker(c0: Path, expect: str, name: str) -> dict:
    out = CTL / f"{name}.raw.json"
    proc = subprocess.run(
        [sys.executable, str(AUDIT), "--c0", str(c0), "--c2", str(C2_LIVE),
         "--expect-c0", expect, "--expect-c2", C2_EXPECT,
         "--label", name, "--json", str(out)],
        capture_output=True, text=True)
    report = json.loads(out.read_text()) if out.exists() else {"verdict": "NO-OUTPUT",
                                                               "stderr": proc.stderr[-500:]}
    report["exit_code_observed"] = proc.returncode
    (CTL / f"{name}.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    out.unlink(missing_ok=True)
    return report


def kinds(report: dict):
    return sorted({f["kind"] for f in report.get("findings", [])})


def main() -> int:
    canonical_text = (REPO / "schemas" / "af_scc_c0_vacuum.yaml").read_text()
    candidate_text = (ROOT / "candidate" / "af_scc_c0_vacuum.yaml").read_text()
    if sha256_text(canonical_text) != EXPECT_C0:
        print("FAIL-CLOSED: canonical hash moved since snapshot")
        return 3

    cases = {}
    (CTL / "ctl0_noop_c0.yaml").write_text(canonical_text)
    (CTL / "ctl1_revert251_c0.yaml").write_text(candidate_text.replace(NEW_REASON, OLD_REASON, 1))
    (CTL / "ctl2_revert157_c0.yaml").write_text(candidate_text.replace(NEW_BULLET, OLD_BULLET, 1))
    specs = [
        ("canonical", REPO / "schemas" / "af_scc_c0_vacuum.yaml", EXPECT_C0,
         "FAIL", ["false_containment_denial", "size_premise_inverted"]),
        ("candidate", ROOT / "candidate" / "af_scc_c0_vacuum.yaml", None,
         "PASS", []),
        ("ctl0_noop", CTL / "ctl0_noop_c0.yaml", None,
         "FAIL", ["false_containment_denial", "size_premise_inverted"]),
        ("ctl1_revert251", CTL / "ctl1_revert251_c0.yaml", None,
         "FAIL", ["size_premise_inverted"]),
        ("ctl2_revert157", CTL / "ctl2_revert157_c0.yaml", None,
         "FAIL", ["false_containment_denial"]),
    ]
    ok = True
    for name, path, expect, want_verdict, want_kinds in specs:
        expect_hash = expect or sha256_text(path.read_text())
        rep = run_checker(path, expect_hash, name)
        got = {"path": str(path.relative_to(REPO)), "sha256": expect_hash,
               "verdict": rep.get("verdict"), "finding_kinds": kinds(rep),
               "n_findings": len(rep.get("findings", [])),
               "findings": rep.get("findings", []),
               "exit_code_observed": rep.get("exit_code_observed")}
        got["expectation_met"] = (got["verdict"] == want_verdict and got["finding_kinds"] == want_kinds)
        ok = ok and got["expectation_met"]
        cases[name] = got
    summary = {
        "task_id": "W008-F2B-DUALREPAIR-01",
        "checker": {"path": "audit_dual_defect.py", "sha256": hashlib.sha256(AUDIT.read_bytes()).hexdigest()},
        "c2_live": {"path": str(C2_LIVE.relative_to(REPO)), "sha256": C2_EXPECT},
        "cases": cases,
        "all_expectations_met": ok,
        "interpretation": {
            "canonical": "two text-level containment inconsistencies present at the frozen rev11 hash",
            "candidate": "both removed; declared chain unchanged; binding fields unchanged",
            "ctl1/ctl2": "each defect is independently necessary for the FAIL verdict",
        },
        "falsifier": "Any case whose observed verdict/finding set differs from its expectation, or a "
                     "candidate PASS without ctl1+ctl2 both FAILing, falsifies this control battery.",
    }
    (ROOT / "evidence" / "controls_summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: {"verdict": v["verdict"], "kinds": v["finding_kinds"],
                          "expectation_met": v["expectation_met"]} for k, v in cases.items()}, indent=1))
    print("ALL EXPECTATIONS MET:", ok)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
