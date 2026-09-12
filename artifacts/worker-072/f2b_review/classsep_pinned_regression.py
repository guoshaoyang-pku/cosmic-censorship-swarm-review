#!/usr/bin/env python3
"""Pinned-variant class-separation regression (worker-072 addendum evidence).

Replicates runtime/bin/classsep_regression.py's measurement loop but imports the detector
from an explicit directory, so the measured bytes are pinned by sha256 and cannot drift
under the run.

  python3 classsep_pinned_regression.py --module-dir DIR --label NAME [--expected-sha HEX] [--verbose]
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
CORPUS = ROOT / "artifacts/worker-07/class_separation_falsification"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--module-dir", required=True)
    ap.add_argument("--module", default="class_separation")
    ap.add_argument("--label", required=True)
    ap.add_argument("--expected-sha", default=None)
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()
    mdir = Path(a.module_dir).resolve()
    mod_path = mdir / f"{a.module}.py"
    got = sha256_file(mod_path)
    if a.expected_sha and got != a.expected_sha:
        print(json.dumps({"label": a.label, "error": "sha mismatch", "measured": got, "expected": a.expected_sha}))
        return 2
    sys.path.insert(0, str(mdir))
    spec = importlib.util.spec_from_file_location(a.module, mod_path)
    cs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cs)
    results = json.loads((CORPUS / "results.json").read_text())
    tp = fp = tn = fn = 0
    rows = []
    for fx in results["fixtures"]:
        p = ROOT / fx["fixture_path"]
        if not p.exists():
            rows.append({"id": fx["id"], "class": "MISSING"}); continue
        m = json.loads(p.read_text())
        detected = cs.findings_for_map(m)
        for g in m.get("groups", []):
            for n in g.get("nodes", []):
                art = n.get("artifact")
                if art and (ROOT / art).is_file():
                    detected += cs.findings_for_text((ROOT / art).read_text(errors="replace"), f"artifact {art}")
        g_ = bool(detected)
        t = bool(fx["is_class_merge"])
        cls = "TP" if (t and g_) else "FN-MISSED" if t else "FP-SPURIOUS" if g_ else "TN"
        tp += cls == "TP"; fn += cls == "FN-MISSED"; fp += cls == "FP-SPURIOUS"; tn += cls == "TN"
        rows.append({"id": fx["id"], "class": cls, "surface": fx.get("surface"),
                     "first": (detected[0][:110] if detected else "")})
    out = {"label": a.label, "module_path": str(mod_path.relative_to(ROOT)), "module_sha256": got,
           "corpus": str(CORPUS.relative_to(ROOT)), "tp": tp, "fn": fn, "tn": tn, "fp": fp,
           "leaks_detected": f"{tp}/{tp + fn}", "controls_clean": f"{tn}/{tn + fp}",
           "verdict": "PASS" if (fn == 0 and fp == 0) else "DEFECTIVE", "rows": rows}
    print(json.dumps(out, indent=2))
    return 0 if out["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
