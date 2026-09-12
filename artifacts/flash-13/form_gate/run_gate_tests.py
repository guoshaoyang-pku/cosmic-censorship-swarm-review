#!/usr/bin/env python3
"""FORM-GATE-01 acceptance runner.

Checks, in order:
  A. the 3 conforming fixtures pass all 16 rules (R16 skipped only for WCC);
  B. each of the 18 mutants is rejected and the expected rule id fires;
     cross-talk (extra rules firing) is recorded; exact-keying is required for the suite
     to count as clean;
  C. the 6 rephrased mutants are reported as CAUGHT (with rule) or BLIND SPOT (documented,
     never counted as a pass);
  D. the gate runs on the three canonical schemas when present, and exits 3 when they are
     absent (not a pass).

Writes gate_report.json next to this file. Exit 0 iff A and B pass.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
GATE = HERE / "check_class_schema.py"
FIX = HERE / "fixtures"  # overridable with --fixtures (e.g. fixtures_v13)
OUTDIR = HERE           # overridable with --outdir


def _cli():
    import argparse
    ap = argparse.ArgumentParser(description="FORM-GATE-01 acceptance runner")
    ap.add_argument("--fixtures", default=str(FIX),
                    help="fixture corpus dir containing manifest.json (default fixtures/)")
    ap.add_argument("--outdir", default=str(OUTDIR), help="where the two reports are written")
    return ap.parse_args()

spec = importlib.util.spec_from_file_location("check_class_schema", GATE)
ccs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ccs)


def run_target(path: Path, class_id=None):
    return ccs.evaluate(path, class_id)


def main() -> int:
    global FIX, OUTDIR
    args = _cli()
    FIX = Path(args.fixtures)
    OUTDIR = Path(args.outdir)
    OUTDIR.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((FIX / "manifest.json").read_text())
    report = {"gate": ccs.GATE_ID, "gate_version": ccs.GATE_VERSION,
              "spec": f"{ccs.SPEC_ID} v{ccs.SPEC_VERSION}",
              "gate_sha256": ccs.sha256_file(GATE),
              "positives": {}, "mutants": {}, "rephrased": {}, "canonical": {}, "exit_codes": {}}

    a_ok = True
    for name, meta in manifest["positives"].items():
        res = run_target(Path(meta["path"]), meta["class_id"])
        ok = res["verdict"] == "pass"
        a_ok = a_ok and ok
        report["positives"][name] = {"verdict": res["verdict"], "failed_rules": res["failed_rules"],
                                     "skipped": res["rules_skipped"], "sha256": res["sha256"],
                                     "pass": ok}
        print(f"{'PASS' if ok else 'FAIL'}  positive {name}: verdict={res['verdict']} "
              f"failed={res['failed_rules']}")

    b_ok = True
    exact = 0
    for name, meta in manifest["mutants"].items():
        res = run_target(Path(meta["path"]), meta["class_id"])
        expected = meta["expected_rule"]
        fired = set(res["failed_rules"])
        keyed = fired == {expected}
        rejected = res["verdict"] == "fail"
        ok = rejected and expected in fired
        b_ok = b_ok and ok
        exact += int(keyed)
        report["mutants"][name] = {"expected_rule": expected, "fired_rules": sorted(fired),
                                   "rejected": rejected, "single_rule_keyed": keyed,
                                   "cross_talk": sorted(fired - {expected}), "pass": ok}
        flag = "PASS" if ok else "FAIL"
        extra = f" cross-talk={sorted(fired - {expected})}" if not keyed else ""
        print(f"{flag}  mutant {name}: expected={expected} fired={sorted(fired)}{extra}")

    c_ok = True
    for name, meta in manifest["rephrased"].items():
        res = run_target(Path(meta["path"]), meta["class_id"])
        caught = res["verdict"] == "fail"
        report["rephrased"][name] = {
            "note": meta["note"], "status": "CAUGHT" if caught else "BLIND_SPOT",
            "fired_rules": res["failed_rules"], "verdict": res["verdict"],
        }
        if caught:
            print(f"INFO  rephrased {name}: CAUGHT by {res['failed_rules']}")
        else:
            print(f"INFO  rephrased {name}: document BLIND SPOT (no rule fired)")

    canonical_ok = True
    canonical_results = []
    try:
        frozen_files = json.loads((REPO / ccs.FROZEN_MANIFEST).read_text()).get("files", {})
    except Exception:
        frozen_files = {}
    for cid, rel in ccs.CANONICAL.items():
        p = REPO / rel
        used = rel
        if not p.exists() and (REPO / ccs.CANONICAL_FALLBACK[cid]).exists():
            used = ccs.CANONICAL_FALLBACK[cid]
            p = REPO / used
        if p.exists():
            res = run_target(p, cid)
            fmeta = frozen_files.get(used, {})
            entry = {"class_id": cid, "verdict": res["verdict"],
                     "failed_rules": res["failed_rules"],
                     "possible_synonyms": res.get("possible_synonyms", {}),
                     "conformance_note": res.get("conformance_note", ""),
                     "sha256": res["sha256"], "source": used,
                     "frozen_sha256": fmeta.get("sha256"),
                     "frozen_prefix": (fmeta.get("sha256") or "")[:12] or None,
                     "frozen_match": (res["sha256"] == fmeta["sha256"]) if fmeta else None,
                     "per_rule": res["per_rule"]}
            report["canonical"][used] = entry
            canonical_results.append({k: entry[k] for k in
                                      ("class_id", "sha256", "per_rule", "verdict", "source",
                                       "failed_rules", "frozen_sha256", "frozen_prefix",
                                       "frozen_match", "possible_synonyms")})
            print(f"INFO  canonical {used}: verdict={res['verdict']} "
                  f"failed={res['failed_rules']} frozen_match={entry['frozen_match']} "
                  f"sha12={(res['sha256'] or '')[:12]}")
        else:
            canonical_ok = False
            report["canonical"][rel] = {"class_id": cid, "verdict": "absent"}

    with tempfile.TemporaryDirectory() as td:
        proc = subprocess.run(
            [sys.executable, str(GATE), "--canonical", "--canonical-dir", td],
            capture_output=True, text=True)
        report["exit_codes"]["canonical_absent"] = proc.returncode
        absent_ok = proc.returncode == 3
        print(f"{'PASS' if absent_ok else 'FAIL'}  exit-3 on absent canonical dir: "
              f"exit={proc.returncode}")

    proc = subprocess.run([sys.executable, str(GATE), str(FIX / "conforming_wcc.yaml")],
                          capture_output=True, text=True)
    report["exit_codes"]["conforming_single"] = proc.returncode
    single_ok = proc.returncode == 0
    print(f"{'PASS' if single_ok else 'FAIL'}  exit-0 on conforming single target: "
          f"exit={proc.returncode}")

    summary = {
        "positives_pass": a_ok,
        "mutants_all_rejected_with_expected_rule": b_ok,
        "mutants_single_rule_keyed": exact,
        "mutants_total": len(manifest["mutants"]),
        "rephrased_caught": sum(1 for v in report["rephrased"].values() if v["status"] == "CAUGHT"),
        "rephrased_blind_spots": sum(1 for v in report["rephrased"].values()
                                     if v["status"] == "BLIND_SPOT"),
        "canonical_schemas_present": canonical_ok,
        "exit_3_on_absent_canonical": report["exit_codes"]["canonical_absent"] == 3,
        "exit_0_on_conforming_single": report["exit_codes"]["conforming_single"] == 0,
    }
    report["summary"] = summary
    (OUTDIR / "fixture_suite_report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    # G3 deliverable shape: {class_id, sha256, per_rule, verdict} per canonical schema
    gate_report = {
        "gate": ccs.GATE_ID, "gate_version": ccs.GATE_VERSION,
        "spec": f"{ccs.SPEC_ID} v{ccs.SPEC_VERSION}", "mode": "canonical",
        "gate_sha256": ccs.sha256_file(GATE),
        "verdict": "pass" if canonical_results and all(r["verdict"] == "pass"
                                                       for r in canonical_results) else "fail",
        "results": canonical_results,
        "fixture_suite": summary,
        "report_sha256_note": "hashes of the gate and of each target are recorded per result",
    }
    (OUTDIR / "gate_report.json").write_text(json.dumps(gate_report, indent=2, sort_keys=True) + "\n")
    print("\nFORM-GATE-01 fixture suite summary:")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if (a_ok and b_ok and absent_ok and single_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
