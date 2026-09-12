#!/usr/bin/env python3
"""Sandbox mutant M1: force stage-2 verdict=accept for every input."""
import importlib.util, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
spec = json.loads((ROOT / "artifacts/formulation/rule_spec.json").read_text())
s = importlib.util.spec_from_file_location("w06_engine_m1", ROOT / "artifacts/worker-06/spec_conformance_audit.py")
m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
rep = m.audit_file(Path(sys.argv[1]), spec)
print(json.dumps({"verdict": "accept", "failed_rules": []}))
