#!/usr/bin/env python3
"""Run the suite author's own verifier (vendored byte-identical at
artifacts/worker-032/run/verify_freeze_current.py, sha256 0527fac95b89...) against the
current pins, with its REPORT output redirected into this worker's artifact directory.

The tool is imported, not edited: only ``mod.REPORT`` (its output destination) is
rebound at runtime. Its checks C8 (stored probes re-evaluate to stored pass value) and
C9 (cross-artifact declared-F0 bindings match disk) are therefore the author's own
semantics, providing a cross-check on the worker-032 independent recomputation.
"""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
VENDOR = HERE.parent / "run" / "verify_freeze_current.py"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    spec = importlib.util.spec_from_file_location("vendor_verify_freeze_current", VENDOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # module has an __main__ guard; main() is not called here
    out = HERE / "vendor_report.json"
    mod.REPORT = out
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = mod.main()
    (HERE / "vendor_stdout.txt").write_text(buf.getvalue(), encoding="utf-8")
    summary = {"vendor_path": str(VENDOR), "vendor_sha256": sha256_file(VENDOR),
               "root_resolved": str(mod.ROOT), "returncode": rc,
               "report": str(out), "report_sha256": sha256_file(out) if out.exists() else None}
    print(json.dumps(summary, indent=1))
    return 0 if out.exists() else 2


if __name__ == "__main__":
    raise SystemExit(main())
