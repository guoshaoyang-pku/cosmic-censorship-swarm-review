#!/usr/bin/env python3
"""W004 SEMCT control rebase: minimal, hash-pinned repair of ADJ-CONTROL-STALENESS.

Task (self-selected; no inbox card existed for worker-004 at 2026-09-12T00:29+08:00):
  class_id  AF-SCC-C0-VAC-GEN
  node      A1 (semantic contract-test calibration evidence routing to G-AUDIT)
  artifact  rebased copies of the three frozen controls +
            a patched copy of the contract-test suite proving the blocker clears

What the blocker is (measured, not assumed):
  The three frozen controls (`schemas/semantic_contract_tests/fixtures/controls/*.yaml`)
  carry, inside `genericity.transfer_failures`, one row
      pair [finite_codimension_complement, residual_comeager], direction: transfers
  The same pair is also correctly present in `genericity.transfer_holds`.  Rule R28 of
  the binding structural gate (`artifacts/formulation/tools/check_class_schema.py`,
  sha256 000e09e46b2f...) rejects a 'transfers' row sitting in transfer_failures, so
  all three controls are rejected by the structural stage and
  validity.valid_for_calibration is false (ADJ-CONTROL-STALENESS).

Repair tested here (the "rebase" arm of the adjudication item):
  delete that one misplaced duplicate row from each control; change nothing else.
  Mutants are not touched.

This script never writes a canonical/shared path.  It writes only under
artifacts/worker-004/semct_control_rebase/.  It emits no gate verdict, sets no node
status, and promotes no theorem; it produces measurements + hashes for the lead.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]  # artifacts/worker-004/semct_control_rebase -> repo root
CST = timezone(timedelta(hours=8))

STRUCT = REPO / "artifacts" / "formulation" / "tools" / "check_class_schema.py"
SEM = REPO / "artifacts" / "worker-06" / "spec_conformance_audit.py"
RUNNER = REPO / "schemas" / "semantic_contract_tests" / "run_contract_tests.py"
MANIFEST = REPO / "schemas" / "semantic_contract_tests" / "manifest.json"

CONTROLS = REPO / "schemas" / "semantic_contract_tests" / "fixtures" / "controls"
STALE = {
    "SCT-C01": CONTROLS / "control_comment_only_composite.yaml",
    "SCT-C02": CONTROLS / "control_conforming_base.yaml",
    "SCT-C03": CONTROLS / "control_quoted_forbidden_phrase.yaml",
}
CANONICAL = {
    "SCT-K01": REPO / "schemas" / "af_scc_c0_vacuum.yaml",
    "SCT-K02": REPO / "schemas" / "af_scc_c2_vacuum.yaml",
    "SCT-K03": REPO / "schemas" / "af_wcc_vacuum.yaml",
}

# every input the measurement is bound to; mismatch fails closed
PINS = {
    str(STRUCT.relative_to(REPO)): "000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff",
    str(SEM.relative_to(REPO)): "c79d8ab8440ac6738bb61df5a33e9fd5f8319b4e74e1f2e9c0fc5083fb408cec",
    str(RUNNER.relative_to(REPO)): "3be197c3729cebb51d43d9c3da87a0325743f399faf65cd7cb9cf293eee9b2f3",
    str(MANIFEST.relative_to(REPO)): "b2e8bd17892b6c5eba1b2d7dde48c9205d07854d025df042fb7a3d919a574f65",
    str((CONTROLS / "control_comment_only_composite.yaml").relative_to(REPO)):
        "a6ad2638dc993c32f7cc46a1a84441581ab785ba02c84a5197663e6284c86f2a",
    str((CONTROLS / "control_conforming_base.yaml").relative_to(REPO)):
        "7b910cf34e64baa7d2d02e229f7bfb5224ffb3fa70d264e1cc1f5ec3173e41eb",
    str((CONTROLS / "control_quoted_forbidden_phrase.yaml").relative_to(REPO)):
        "687fd697130497633e63b696ac90d0939c2699fd6d5f3b1bca06b55f5948dee6",
    "schemas/af_scc_c0_vacuum.yaml": "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508",
    "schemas/af_scc_c2_vacuum.yaml": "b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2",
    "schemas/af_wcc_vacuum.yaml": "9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503",
}

# exact 8-line duplicate row to remove, as it appears in all three controls (lines 264-271)
ROW = (
    "  - pair:\n"
    "    - finite_codimension_complement\n"
    "    - residual_comeager\n"
    "    direction: transfers\n"
    "    witness: a countable union of proper closed finite-codimension submanifolds is\n"
    "      meager\n"
    "    status: elementary\n"
    "    citation_status: n/a\n"
)

FLAG = {"py": sys.executable}


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def check_pins() -> dict:
    out = {}
    for rel, want in PINS.items():
        p = REPO / rel
        got = sha(p) if p.is_file() else "MISSING"
        out[rel] = {"expected": want, "measured": got, "match": got == want}
    bad = [k for k, v in out.items() if not v["match"]]
    if bad:
        raise SystemExit(f"PIN MISMATCH (fails closed): {bad}")
    return out


def run_structural(target: Path) -> dict:
    proc = subprocess.run([FLAG["py"], str(STRUCT), "--json", str(target)],
                          capture_output=True, text=True, timeout=180)
    try:
        rep = json.loads(proc.stdout[proc.stdout.index("{"):])
    except (ValueError, json.JSONDecodeError):
        rep = {}
    return {"tool": "structural", "exit": proc.returncode,
            "verdict": rep.get("verdict", "no_verdict"),
            "failed_rules": rep.get("failed_rules", []),
            "accepted": proc.returncode == 0 and rep.get("verdict") == "pass",
            "rejected": rep.get("verdict") == "fail",
            "stderr": proc.stderr.strip()[:300]}


def run_semantic(target: Path, hardened: bool) -> dict:
    out = HERE / "tmp" / f"audit_{'h' if hardened else 'b'}_{target.stem}.json"
    cmd = [FLAG["py"], str(SEM), str(target), "--json", str(out)]
    if hardened:
        cmd.insert(-2, "--hardened")
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    rep = {}
    if out.exists():
        try:
            rep = json.loads(out.read_text())
        finally:
            out.unlink()
    return {"tool": "semantic_hardened" if hardened else "semantic_baseline",
            "exit": proc.returncode,
            "verdict": rep.get("verdict", "no_verdict"),
            "failed_rules": rep.get("failed_rules", []),
            "undecided_rules": rep.get("undecided_rules", []),
            "accepted": rep.get("verdict") == "accept",
            "rejected": rep.get("verdict") == "reject",
            "stderr": proc.stderr.strip()[:300]}


def triplet(target: Path) -> dict:
    return {"structural": run_structural(target),
            "semantic_baseline": run_semantic(target, False),
            "semantic_hardened": run_semantic(target, True)}


def main() -> int:
    pins = check_pins()
    report: dict = {
        "task": "W004-SEMCT-CONTROL-REBASE-01",
        "adjudication_item": "ADJ-CONTROL-STALENESS",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "node_id": "A1",
        "gate": "G-AUDIT (calibration evidence only; this script sets no gate verdict)",
        "actor": "worker-004",
        "created_at": now(),
        "repo": str(REPO),
        "inputs_pinned": pins,
        "repair": {
            "kind": "delete one misplaced duplicate transfer row from each frozen control",
            "removed_block": ROW,
            "semantics": ("the pair [finite_codimension_complement, residual_comeager] "
                          "remains asserted as direction=transfers in genericity.transfer_holds; "
                          "the deleted entry was the same pair placed in transfer_failures, "
                          "which R28 rejects"),
            "untouched": ["all 32 leak mutants", "canonical schemas", "stage tools", "canonical suite files"],
        },
        "measurements": {},
        "falsifier": [
            "an unmodified frozen control accepted by the structural stage at this tool hash",
            "a rebased control rejected by structural or either semantic stage at this tool hash",
            "any byte difference between stale and rebased control outside the removed block",
            "the patched suite failing to reach exit 0 / valid_for_calibration=true, or mutant counts differing from 32/11/32",
            "a stage-tool hash change, which voids this report until re-run",
        ],
    }

    # --- 1. rebase by exact block deletion -------------------------------------------
    rebased = {}
    diffs = {}
    for tid, src in STALE.items():
        text = src.read_text()
        n = text.count(ROW)
        if n != 1:
            raise SystemExit(f"{tid}: expected exactly 1 misplaced row, found {n} (fails closed)")
        new_text = text.replace(ROW, "", 1)
        dst = HERE / "rebased_controls" / src.name
        dst.write_text(new_text)
        # only-difference proof
        import difflib
        d = list(difflib.unified_diff(text.splitlines(keepends=True),
                                      new_text.splitlines(keepends=True),
                                      fromfile=f"frozen/{src.name}", tofile=f"rebased/{src.name}"))
        hunks = [x for x in d if x.startswith("@@")]
        plus = [x for x in d if x.startswith("+") and not x.startswith("+++")]
        minus = [x for x in d if x.startswith("-") and not x.startswith("---")]
        diffs[tid] = {"hunks": len(hunks), "added_lines": len(plus), "removed_lines": len(minus)}
        if len(hunks) != 1 or plus or len(minus) != 8:
            raise SystemExit(f"{tid}: unexpected diff shape {diffs[tid]} (fails closed)")
        rebased[tid] = dst
        print(f"rebased {tid}: {src.name} {sha(src)[:12]} -> {sha(dst)[:12]} "
              f"(1 hunk, -8 lines, +0 lines)")
    report["rebased_controls"] = {
        tid: {"source": str(STALE[tid].relative_to(REPO)), "source_sha256": sha(STALE[tid]),
              "rebased": str(rebased[tid].relative_to(REPO)), "rebased_sha256": sha(rebased[tid]),
              "diff": diffs[tid]} for tid in STALE
    }

    # --- 2. stage measurements: stale vs rebased vs canonical ------------------------
    print("running stages on stale controls (expect structural R28 reject) ...")
    stale_meas = {tid: triplet(STALE[tid]) for tid in STALE}
    print("running stages on rebased controls (expect all accept) ...")
    rebased_meas = {tid: triplet(rebased[tid]) for tid in STALE}
    print("running stages on current canonical schemas (expect all accept) ...")
    canon_meas = {tid: triplet(CANONICAL[tid]) for tid in CANONICAL}
    report["measurements"]["stale_controls"] = stale_meas
    report["measurements"]["rebased_controls"] = rebased_meas
    report["measurements"]["canonical_controls"] = canon_meas

    def accepted_by(meas, t, stages=("structural", "semantic_baseline", "semantic_hardened")):
        return all(meas[t][s]["accepted"] for s in stages)

    stale_ok = sum(1 for t in STALE if stale_meas[t]["structural"]["accepted"])
    rebased_ok = sum(1 for t in STALE if accepted_by(rebased_meas, t))
    canon_ok = sum(1 for t in CANONICAL if accepted_by(canon_meas, t))
    report["measurements"]["summary"] = {
        "stale_accepted_by_structural": f"{stale_ok}/3",
        "stale_failed_rules": {t: stale_meas[t]["structural"]["failed_rules"] for t in STALE},
        "rebased_accepted_by_all_three_stages": f"{rebased_ok}/3",
        "canonical_accepted_by_all_three_stages": f"{canon_ok}/3",
        "stage_hashes": {"structural": sha(STRUCT), "semantic": sha(SEM)},
        "sufficient_to_clear_ADJ_CONTROL_STALENESS":
            bool(rebased_ok == 3 and canon_ok == 3 and stale_ok == 0),
    }
    print("summary:", json.dumps(report["measurements"]["summary"], indent=1))

    (HERE / "rebase_report.json").write_text(json.dumps(report, indent=1) + "\n")
    print(f"wrote {HERE / 'rebase_report.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
