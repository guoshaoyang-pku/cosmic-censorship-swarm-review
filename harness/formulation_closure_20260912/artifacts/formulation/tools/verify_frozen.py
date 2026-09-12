#!/usr/bin/env python3
"""Verify FROZEN.json against disk; exit 1 on any drift (reviewers should run this first)."""
import hashlib, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
man = json.loads((ROOT/"artifacts/formulation/FROZEN.json").read_text())
bad = []
for p, rec in man["files"].items():
    f = ROOT/p
    if not f.exists():
        bad.append(f"MISSING {p}"); continue
    h = hashlib.sha256(f.read_bytes()).hexdigest()
    if h != rec["sha256"]:
        bad.append(f"DRIFT {p}: manifest {rec['sha256'][:12]} disk {h[:12]}")
print(f"FROZEN revision {man['revision']} frozen_at {man['frozen_at']}: {len(man['files'])} files, {len(bad)} problems")
for b in bad: print("  " + b)
sys.exit(1 if bad else 0)
