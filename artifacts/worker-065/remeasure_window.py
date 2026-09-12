#!/usr/bin/env python3
"""Worker-065: stability window around the data-class concordance measurement.

Why this exists
---------------
The measurement tool (data_class_concordance.py) records one sha256 per canonical
schema but only prints "drift aborts the run" in its docstring -- it never checks
drift.  The canonical schemas were republished at 2026-09-12T00:16:22, which voided
worker-065's earlier artifact under its own falsifier clause ("any of the three
measured canonical sha256 values changes without this artifact being re-measured").
This runner makes the drift check explicit and machine-checkable:

  1. hash the three canonical schemas BEFORE the measurement,
  2. run the measurement tool to a fresh --out path,
  3. hash the same three files AFTER the measurement,
  4. require pre == measurement-recorded == post for all three, and both built-in
     negative controls to pass; otherwise the window report is marked UNSTABLE and
     the exit code is non-zero.

Evidence only.  Sets no gate verdict and no node transition.

Reproduce:
    python3 artifacts/worker-065/remeasure_window.py --stamp 20260912T001900
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CST = timezone(timedelta(hours=8))
MEASURE = ROOT / "artifacts/worker-065/data_class_concordance.py"
SCHEMAS = {
    "F1": {"class_id": "AF-WCC-VAC-GEN", "path": "schemas/af_wcc_vacuum.yaml"},
    "F2a": {"class_id": "AF-SCC-C2-VAC-GEN", "path": "schemas/af_scc_c2_vacuum.yaml"},
    "F2b": {"class_id": "AF-SCC-C0-VAC-GEN", "path": "schemas/af_scc_c0_vacuum.yaml"},
}
FALSIFIER = (
    "Any of the three canonical schema sha256 values differs between the pre-window, "
    "measurement-recorded and post-window readings (window UNSTABLE), or either built-in "
    "negative control returns CONCORDANT_CORE. Substantively: a reviewer exhibits a "
    "data_class field that changes the admitted data set - different Sobolev index or "
    "decay rate, parity imposed, matter/Lambda changed, restricting predicate added or "
    "removed - that the declared restricting projection drops."
)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def measure(hashes: dict) -> dict:
    return {n: {"path": SCHEMAS[n]["path"], "sha256": hashes[n],
                "bytes": (ROOT / SCHEMAS[n]["path"]).stat().st_size}
            for n in SCHEMAS}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="artifacts/worker-065")
    ap.add_argument("--stamp", default=None)
    ap.add_argument("--measure-out", default=None,
                    help="path for the measurement artifact (default: out-dir/data_class_concordance_<stamp>.json)")
    args = ap.parse_args(argv)

    stamp = args.stamp or datetime.now(CST).strftime("%Y%m%dT%H%M%S")
    out_dir = (ROOT / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    meas_out = Path(args.measure_out) if args.measure_out else out_dir / f"data_class_concordance_{stamp}.json"
    if not meas_out.is_absolute():
        meas_out = (ROOT / meas_out).resolve()

    if not MEASURE.is_file():
        print(f"FATAL: missing measurement tool {MEASURE}", file=sys.stderr)
        return 2

    pre_hashes = {n: sha256_file(ROOT / SCHEMAS[n]["path"]) for n in SCHEMAS}
    proc = subprocess.run(
        [sys.executable, str(MEASURE), "--out", str(meas_out)],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    post_hashes = {n: sha256_file(ROOT / SCHEMAS[n]["path"]) for n in SCHEMAS}

    if not meas_out.is_file():
        print(f"FATAL: measurement produced no artifact; stdout={proc.stdout!r} stderr={proc.stderr!r}",
              file=sys.stderr)
        return 2
    meas = json.loads(meas_out.read_text())
    meas_hashes = {n: meas["canonical_paths"][n]["sha256"] for n in SCHEMAS}

    per_schema = {}
    stable = True
    for n in SCHEMAS:
        ok = pre_hashes[n] == meas_hashes[n] == post_hashes[n]
        stable = stable and ok
        per_schema[n] = {
            "class_id": SCHEMAS[n]["class_id"],
            "path": SCHEMAS[n]["path"],
            "pre_sha256": pre_hashes[n],
            "measurement_sha256": meas_hashes[n],
            "post_sha256": post_hashes[n],
            "stable": ok,
        }

    controls = meas.get("negative_controls", [])
    controls_ok = bool(meas.get("controls_ok")) and all(c.get("pass") for c in controls)
    verdict = meas.get("verdict")
    window_status = "STABLE" if (stable and controls_ok and proc.returncode == 0) else "UNSTABLE"

    report = {
        "actor": "worker-065",
        "task_id": "W065-DATACLASS-REMESA-02",
        "at": datetime.now(CST).isoformat(timespec="seconds"),
        "stamp": stamp,
        "class_ids": [SCHEMAS[n]["class_id"] for n in SCHEMAS],
        "node_id": "F2",
        "gate": "G-FORM",
        "window": {
            "pre": measure(pre_hashes),
            "measurement_recorded": measure(meas_hashes),
            "post": measure(post_hashes),
        },
        "per_schema": per_schema,
        "window_stable": stable,
        "measurement": {
            "path": str(meas_out.relative_to(ROOT)),
            "sha256": sha256_file(meas_out),
            "returncode": proc.returncode,
            "verdict": verdict,
            "controls_ok": controls_ok,
            "negative_controls": controls,
        },
        "runner_stdout": proc.stdout.strip(),
        "runner_stderr": proc.stderr.strip()[-2000:],
        "window_status": window_status,
        "falsifier": FALSIFIER,
        "limitations": [
            "A stable window is not a proof of stability at other times; it certifies the three readings around this one run.",
            "The measurement is the tool's declared projection; raw values for every path are in the measurement artifact so a reviewer can reject the projection without re-running.",
            "Evidence only: this report sets no gate verdict and no node transition.",
        ],
        "reproduce": (
            "python3 artifacts/worker-065/remeasure_window.py "
            f"--stamp {stamp} --measure-out {meas_out.relative_to(ROOT)}"
        ),
        "measurement_tool": {"path": "artifacts/worker-065/data_class_concordance.py",
                             "sha256": sha256_file(MEASURE)},
    }

    rep_out = out_dir / f"remeasure_window_{stamp}.json"
    rep_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "window_report": str(rep_out.relative_to(ROOT)),
        "window_report_sha256": sha256_file(rep_out),
        "measurement": report["measurement"],
        "window_stable": stable,
        "window_status": window_status,
        "verdict": verdict,
        "per_schema": {n: per_schema[n]["measurement_sha256"][:12] for n in SCHEMAS},
    }, indent=2))
    return 0 if window_status == "STABLE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
