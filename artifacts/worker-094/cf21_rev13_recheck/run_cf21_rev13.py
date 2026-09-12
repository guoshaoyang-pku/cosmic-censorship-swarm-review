#!/usr/bin/env python3
"""W094F-CF21-REV13-RECHECK-01 - execute the declared CF-21 next-falsifier at the
live FROZEN rev29 pins.

WHY THIS EXISTS
---------------
Worker-094's W094-GENERICITY-CONSISTENCY-01 (report 10a92ff3c9c1d4, 00:52:15)
declared the instrument for controller finding CF-21: AF-WCC-SCALAR-SPH carries
`axes.genericity_kind: unresolved` / `genericity_value_status:
unresolved_pending_L1` while its conclusion quantifies over "a comeager set G of
data" (baseline FAIL: G2+G5).  That run bound the *rev12* schema bytes
(cce9c60146d6 / 5476a3f2c6bc / 55d0a1ea9bda) with the taxonomy at its unchanged
0abb9ed8a961.  Its declared next_falsifier was: re-run the checker after the
formulation owner repins or repairs the taxonomy.

Between 00:52:15 and 00:57:26 the three class schemas moved rev12 -> rev13 under
FROZEN revision 29 (evidence-binding repair, CF-20).  The taxonomy did NOT move:
0abb9ed8a961 is both the G-F0-pass pin and the live bytes.  This task executes
the declared re-run at the live gate-relevant pins, WITHOUT editing or
re-pinning the original instrument: it imports the byte-identical declared
checker (pinned 4adcfcbe9884) and applies its own declared rules and controls
to the live bytes, then diffs the per-class verdicts against the rev12-pinned
report.

DELIVERABLE
-----------
report.json: measured input hashes before/after, pin match table, baseline
findings, 7/7 in-memory controls, drift, and a structural comparison against the
rev12-pinned report.  The verdict is one of
  CF21_LIVE_AT_REV13_INVARIANT   baseline FAIL, controls PASS, findings identical
  CF21_VOID_AT_REV13             baseline PASS at the live bytes
  CF21_CHANGED_AT_REV13          baseline findings differ from the rev12 report
  INSTRUMENT_* / INPUT_DRIFT / PIN_MISMATCH   fail-closed conditions

Exit codes: 0 measured (any baseline verdict), 2 control deviation, 3 input
drift during the run, 4 expected-pin mismatch, 5 instrument hash mismatch.

AUTHORITY
---------
Worker evidence only: no gate verdict, no node status, no validation_status=
passed, and no frozen/canonical byte is written.  Read-only on all pinned
inputs.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))
TASK_ID = "W094F-CF21-REV13-RECHECK-01"
ACTOR = "worker-094"
CLASS_ID = "AF-WCC-SCALAR-SPH"
NODE_ID = "F0"

DECLARED_CHECKER = "artifacts/worker-094/genericity_consistency/check_genericity_consistency.py"
DECLARED_CHECKER_SHA = "4adcfcbe98842c20d5ccaf236377e3bae3caccbdd1024c66956bf88ac887789c"
PRIOR_REPORT = "artifacts/worker-094/genericity_consistency/run/report.json"
PRIOR_REPORT_SHA = "10a92ff3c9c1d4271a584b8fa6c79fe94ac505fcfe1db74189a256f76708f282"

# Live gate-relevant pins at FROZEN rev29 (815e0807), measured independently
# before this task and re-measured at run time.
EXPECTED_INPUTS = {
    "research_map/formulation_taxonomy.yaml":
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "schemas/af_wcc_vacuum.yaml":
        "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "schemas/af_scc_c2_vacuum.yaml":
        "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_scc_c0_vacuum.yaml":
        "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "artifacts/formulation/VOCAB_ALIASES.json":
        "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba",
    "artifacts/formulation/FROZEN.json":
        "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now_iso() -> str:
    return datetime.now(CST).replace(microsecond=0).isoformat()


def load_declared_checker(root: Path):
    spec = importlib.util.spec_from_file_location(
        "declared_cf21_checker", root / DECLARED_CHECKER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def measure(root: Path, paths) -> dict:
    out = {}
    for p in paths:
        f = root / p
        out[p] = {"sha256": sha256_file(f), "bytes": f.stat().st_size}
    return out


def build_manifest(root: Path, report: dict) -> dict:
    here = root / "artifacts/worker-094/cf21_rev13_recheck"
    deliverables = {
        "driver": "run_cf21_rev13.py",
        "report": "run/report.json",
        "readme": "README.md",
    }
    d = {}
    for k, rel in deliverables.items():
        f = here / rel
        if f.exists():
            d[k] = {"path": f"artifacts/worker-094/cf21_rev13_recheck/{rel}",
                    "sha256": sha256_file(f), "bytes": f.stat().st_size}
    manifest = {
        "task_id": TASK_ID,
        "actor": ACTOR,
        "created_at": report["created_at"],
        "class_id": CLASS_ID,
        "node_id": NODE_ID,
        "gate_scope": "G-F0 / G-FORM (advisory evidence only)",
        "advisory": "worker evidence only; no gate verdict, no node status, no frozen byte written",
        "deliverables": d,
        "instrument": {"path": DECLARED_CHECKER, "sha256": DECLARED_CHECKER_SHA,
                       "note": "byte-identical declared CF-21 checker, imported not copied"},
        "pinned_inputs": EXPECTED_INPUTS,
        "verdict": report["verdict"],
        "baseline": report["baseline"]["verdict"],
        "controls": report["controls"]["verdict"],
        "drift_after_run": report["drift_after_run"],
        "falsifier": report["falsifier"],
        "next_falsifier": report["next_falsifier"],
    }
    out = here / "run/manifest.json"
    out.write_text(json.dumps(manifest, indent=1) + "\n")
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--manifest-only", action="store_true",
                    help="re-emit run/manifest.json from the existing report")
    args = ap.parse_args()

    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[3]
    here = root / "artifacts/worker-094/cf21_rev13_recheck"
    out_path = Path(args.out) if args.out else (here / "run/report.json")

    if args.manifest_only:
        report = json.loads(out_path.read_text())
        m = build_manifest(root, report)
        print(json.dumps({"manifest": str(here / "run/manifest.json"),
                          "sha256": sha256_file(here / "run/manifest.json"),
                          "verdict": m["verdict"]}, indent=1))
        return 0

    # instrument hash gate (fail closed before executing anything)
    instrument_sha = sha256_file(root / DECLARED_CHECKER)
    if instrument_sha != DECLARED_CHECKER_SHA:
        print(json.dumps({"error": "instrument hash mismatch",
                          "declared": DECLARED_CHECKER_SHA,
                          "measured": instrument_sha}, indent=1))
        return 5

    inputs = list(EXPECTED_INPUTS) + [DECLARED_CHECKER, PRIOR_REPORT]
    before = measure(root, inputs)
    pin_status = {
        p: {"expected": e, "measured": before[p]["sha256"],
            "match": before[p]["sha256"] == e}
        for p, e in EXPECTED_INPUTS.items()
    }
    pin_match = all(v["match"] for v in pin_status.values())
    prior_sha_ok = before[PRIOR_REPORT]["sha256"] == PRIOR_REPORT_SHA

    chk = load_declared_checker(root)
    yaml = chk.yaml  # module-level import of the declared instrument

    tax = yaml.safe_load((root / chk.TAXONOMY).read_text())
    raw = (root / chk.TAXONOMY).read_text()
    alias2canon = chk.load_alias_table(root)
    schema_docs = {p: yaml.safe_load((root / p).read_text()) for p in chk.SCHEMAS}
    tax_sha = before[chk.TAXONOMY]["sha256"]
    schema_shas = {p: before[p]["sha256"] for p in chk.SCHEMAS}

    findings = chk.check_taxonomy(tax, alias2canon, raw, tax_sha, schema_docs, schema_shas)
    baseline = chk.verdict_of(findings)
    per_class = chk.per_class(findings)
    ctl = chk.controls(tax, schema_docs, alias2canon, raw, tax_sha, schema_shas)
    ctl_ok = all(c["status"] == "PASS" for c in ctl)

    after = measure(root, inputs)
    drift = {p: {"before": before[p]["sha256"], "after": after[p]["sha256"]}
             for p in inputs if before[p]["sha256"] != after[p]["sha256"]}

    prior = json.loads((root / PRIOR_REPORT).read_text())
    prior_pc = prior["baseline"]["per_class"]
    prior_hard = sorted((r, cid) for cid, v in prior_pc.items() for r in v["hard"])
    now_hard = sorted((f["rule"], f["class_id"]) for f in findings if f["severity"] == "hard")
    findings_identical = (per_class == prior_pc)
    taxonomy_unchanged = (before[chk.TAXONOMY]["sha256"] ==
                          prior["inputs"][chk.TAXONOMY]["sha256"])
    moved = sorted(p for p in chk.SCHEMAS
                   if before[p]["sha256"] != prior["inputs"][p]["sha256"])

    if not ctl_ok:
        verdict = "INSTRUMENT_CONTROL_DEVIATION"
        reason = "at least one declared control did not behave as pre-registered"
    elif drift:
        verdict = "INPUT_DRIFT"
        reason = "a pinned input changed during the run; the measurement is void"
    elif not pin_match:
        verdict = "PIN_MISMATCH"
        reason = "live bytes differ from the expected FROZEN rev29 pins; re-pin and re-run"
    elif not prior_sha_ok:
        verdict = "INSTRUMENT_PRIOR_REPORT_MISMATCH"
        reason = "the rev12 reference report hash differs from the declared pin"
    elif baseline == "PASS":
        verdict = "CF21_VOID_AT_REV13"
        reason = "the declared checker passes at the live rev13/FROZEN rev29 bytes"
    elif findings_identical:
        verdict = "CF21_LIVE_AT_REV13_INVARIANT"
        reason = ("baseline FAIL with the same per-class findings as the rev12-pinned run: "
                  "the rev13 evidence-binding repair did not change the CF-21 verdict")
    else:
        verdict = "CF21_CHANGED_AT_REV13"
        reason = "baseline FAIL but the per-class findings differ from the rev12-pinned run"

    report = {
        "task_id": TASK_ID,
        "actor": ACTOR,
        "created_at": now_iso(),
        "class_id": CLASS_ID,
        "node_id": NODE_ID,
        "advisory": "worker evidence only; no gate verdict, no node status, no frozen byte written",
        "instrument": {
            "path": DECLARED_CHECKER,
            "sha256": instrument_sha,
            "expected_sha256": DECLARED_CHECKER_SHA,
            "imported": True,
            "note": "the declared CF-21 checker is imported byte-identical, not copied or edited",
        },
        "inputs": before,
        "pin_status": pin_status,
        "pin_match": pin_match,
        "prior_report": {"path": PRIOR_REPORT, "sha256": before[PRIOR_REPORT]["sha256"],
                         "expected_sha256": PRIOR_REPORT_SHA, "match": prior_sha_ok},
        "baseline": {
            "verdict": baseline,
            "hard_failure_count": sum(1 for f in findings if f["severity"] == "hard"),
            "soft_finding_count": sum(1 for f in findings if f["severity"] == "soft"),
            "per_class": per_class,
            "findings": findings,
            "hard_rules": now_hard,
        },
        "controls": {"verdict": "PASS" if ctl_ok else "FAIL", "count": len(ctl), "results": ctl},
        "drift_after_run": drift,
        "rev12_reference": {
            "created_at": prior["created_at"],
            "baseline": prior["baseline"]["verdict"],
            "per_class": prior_pc,
            "hard_rules": prior_hard,
            "input_hashes": {k: v["sha256"] for k, v in prior["inputs"].items()},
        },
        "delta": {
            "taxonomy_unchanged": taxonomy_unchanged,
            "schemas_moved_rev12_to_rev13": moved,
            "findings_identical_to_rev12_run": findings_identical,
            "hard_rule_set_identical": prior_hard == now_hard,
        },
        "verdict": verdict,
        "verdict_reason": reason,
        "falsifier": (
            "Void on any pinned byte change (re-measure), on a control deviation, or on a live "
            "AF-WCC-SCALAR-SPH repair: declare a concrete/provisional genericity_kind with a "
            "binding schema (or an explicit provisional/blocked marker on the conclusion), clear "
            "or machine-readably block H4, and the declared checker must return baseline PASS "
            "with 7/7 controls. A file rewrite alone is not a falsifier; the finding binds the "
            "sha256 values in `inputs` and must be re-run at any new bytes."
        ),
        "next_falsifier": (
            "python3 artifacts/worker-094/cf21_rev13_recheck/run_cf21_rev13.py "
            "--out artifacts/worker-094/cf21_rev13_recheck/run/report.json"
        ),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=1) + "\n")

    summary = {
        "task_id": TASK_ID,
        "verdict": verdict,
        "baseline": baseline,
        "hard_failures": [{"rule": r, "class_id": c} for r, c in now_hard],
        "per_class": per_class,
        "controls": report["controls"]["verdict"],
        "drift": drift,
        "pin_match": pin_match,
        "findings_identical_to_rev12": findings_identical,
        "report": str(out_path),
        "report_sha256": sha256_file(out_path),
    }
    print(json.dumps(summary, indent=1))

    if drift:
        return 3
    if not ctl_ok:
        return 2
    if not pin_match or not prior_sha_ok:
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
