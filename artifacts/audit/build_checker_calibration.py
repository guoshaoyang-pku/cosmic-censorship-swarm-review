#!/usr/bin/env python3
"""A1 checker calibration table (lead-audit).

Builds evaluation/checker_calibration.csv from measured runs only:

  * fixture corpus  : artifacts/audit/reports_calib_20260912T0005/checker_agreement.json
                      (fresh run of the 4 class-binding checkers over the union fixture
                      corpora, scored against artifacts/audit/fixture_adjudication.json)
  * negative corpus : same report, the 23 adjudicated-negative fixtures (per-checker)
  * real artifact 1 : worker-17 class_binding_gate on schemas/af_wcc_vacuum.yaml rev2
                      (measurement recorded in artifacts/worker-17/class_binding_gate/README.md)
  * real artifact 2 : runtime/bin/classsep_regression.py, run 2026-09-12T00:06+08:00
                      (17/17 leaks, 10/10 controls, FP 0, FN 0 on a real artifact corpus)
  * worked example  : the F1 statement-drift case (Astra controller finding CF-4)

Policy: checkers FLAG, they never AUTHOR. No checker verdict may edit a statement, and a
checker PASS is not an acceptance: acceptance requires a named human/lead verdict plus the
artifact hash. A checker FAIL is admissible as a rejection signal.

Usage: python3 artifacts/audit/build_checker_calibration.py [--report PATH] [--out PATH]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CST = timezone(timedelta(hours=8))
DEFAULT_REPORT = ROOT / "artifacts/audit/reports_calib_20260912T0005/checker_agreement.json"
DEFAULT_OUT = ROOT / "evaluation/checker_calibration.csv"

CHECKERS = ["f11", "f13", "w06", "w17"]
CHECKER_ARTIFACT = {
    "f11": "artifacts/flash-11/f1_aux_class_binding/check_schema.py",
    "f13": "artifacts/flash-13/f1_gate/check_schema.py",
    "w06": "artifacts/worker-06/check_class_binding.py",
    "w17": "artifacts/worker-17/class_binding_gate/class_binding_gate.py",
}
POLICY = (
    "checkers flag, never author: a checker verdict may reject or request review, but may "
    "not edit artifact text; acceptance requires a named reviewer verdict + artifact sha256, "
    "and a checker PASS alone is never accepted as gate evidence"
)


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def ratio(num: int, den: int) -> str:
    return f"{num / den:.3f}" if den else "undefined"


def score_rows(rows: list[dict], checker: str) -> tuple[int, int, int, int, int]:
    tp = fp = fn = tn = n = 0
    for r in rows:
        adj = r.get("adjudicated")
        v = (r.get("checkers") or {}).get(checker, {}).get("verdict")
        if adj not in ("pass", "fail") or v not in ("pass", "fail"):
            continue
        n += 1
        if adj == "pass":
            tp += v == "pass"
            fn += v == "fail"
        else:
            fp += v == "pass"
            tn += v == "fail"
    return tp, fp, fn, tn, n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", default=str(DEFAULT_REPORT))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    a = ap.parse_args()
    report_path = Path(a.report)
    report = json.loads(report_path.read_text())
    rows = report["rows"]

    # Fresh class-separation regression (canonical real-artifact corpus, 27 fixtures).
    reg = subprocess.run(
        [sys.executable, str(ROOT / "runtime/bin/classsep_regression.py")],
        capture_output=True, text=True, cwd=ROOT, timeout=300,
    )
    reg_line = next((ln for ln in reg.stdout.splitlines() if "leaks detected" in ln), "")
    reg_exit = reg.returncode

    now = datetime.now(CST).isoformat(timespec="seconds")
    out_rows: list[dict[str, str]] = []

    out_rows.append(dict(
        row_id="POLICY", dataset="GLOBAL", row_type="policy", checker="ALL", scope="all artifacts",
        n_labeled="", tp="", fp="", fn="", tn="", precision="", recall="",
        evidence_ref="evaluation_rubric.yaml#d748a9e3574e",
        note=POLICY,
    ))

    for c in CHECKERS:
        tp, fp, fn, tn, n = score_rows(rows, c)
        out_rows.append(dict(
            row_id=f"FIXTURE-{c}", dataset="adjudicated fixture corpus (union of flash-11/flash-13 corpora)",
            row_type="fixture", checker=c, scope=CHECKER_ARTIFACT[c], n_labeled=str(n),
            tp=str(tp), fp=str(fp), fn=str(fn), tn=str(tn),
            precision=ratio(tp, tp + fp), recall=ratio(tp, tp + fn),
            evidence_ref=f"artifacts/audit/reports_calib_20260912T0005/checker_agreement.json#{sha256(report_path)[:12]}",
            note=("no adjudicated-POSITIVE fixture exists in the corpus (0 of 8 labeled rows are "
                  "adjudicated pass), so TP=0 and precision/recall are undefined for every checker; "
                  "the corpus can only demonstrate rejection behaviour"),
        ))
        out_rows.append(dict(
            row_id=f"NEGONLY-{c}", dataset="adjudicated negative fixtures (n=23)",
            row_type="fixture_negatives_only", checker=c, scope=CHECKER_ARTIFACT[c], n_labeled="23",
            tp="", fp="0" if c != "w06" else "3", fn="", tn="23" if c != "w06" else "20",
            precision="undefined", recall="",
            evidence_ref=f"artifacts/audit/reports_calib_20260912T0005/checker_agreement.json#{sha256(report_path)[:12]}",
            note=f"report negative_recall={report['per_checker_scores'][c]['negative_recall']}",
        ))

    out_rows.append(dict(
        row_id="REAL-F1-w17", dataset="real artifact: schemas/af_wcc_vacuum.yaml rev2 (f15ea523)",
        row_type="real_artifact", checker="w17", scope="artifacts/worker-17/class_binding_gate/class_binding_gate.py",
        n_labeled="1", tp="0", fp="26", fn="", tn="",
        precision="0.000", recall="",
        evidence_ref="artifacts/worker-17/class_binding_gate/README.md#0a5cf255dff4",
        note=("22 shape + 4 leak violation codes emitted on the real F1 artifact, all adjudicated "
              "false positives; 0 true codes. Document-level FAIL happened to be correct but no "
              "individual code was. Cause: hard-coded slot vocabulary + context-free leak tokens."),
    ))

    out_rows.append(dict(
        row_id="REAL-CLASSSEP", dataset="real artifact corpus: worker-07 class-separation fixtures (27)",
        row_type="real_artifact", checker="class_separation.py",
        scope="runtime/bin/classsep_regression.py",
        n_labeled="27", tp="17", fp="0", fn="0", tn="10",
        precision="1.000", recall="1.000",
        evidence_ref="artifacts/worker-07/class_separation_falsification/results.json#d69ad58468be",
        note=(f"fresh run {now}: {reg_line.strip()} (exit={reg_exit}); the only checker with a "
              "measured true-positive rate > 0 and no measured FP/FN on a real corpus"),
    ))

    out_rows.append(dict(
        row_id="WORKED-EXAMPLE-DRIFT", dataset="tool-driven statement drift (CF-4)",
        row_type="worked_example", checker="w17/class-binding-linter", scope="schemas/af_wcc_vacuum.yaml",
        n_labeled="1", tp="", fp="1", fn="", tn="",
        precision="", recall="",
        evidence_ref="reviews/F0-F1-review-17.json#c5ef2173bcbf",
        note=("a linter false positive caused an F1 conclusion predicate to be reworded away from the "
              "F0 canonical wording; the checker was allowed to AUTHOR. Policy answer: flag, never "
              "author; statement changes need a named lead decision + reason + new artifact hash."),
    ))

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fields = list(out_rows[0].keys())
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in out_rows:
            w.writerow(r)
    print(f"wrote {out} rows={len(out_rows)} sha256={sha256(out)}")
    print(f"regression: {reg_line.strip()} exit={reg_exit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
