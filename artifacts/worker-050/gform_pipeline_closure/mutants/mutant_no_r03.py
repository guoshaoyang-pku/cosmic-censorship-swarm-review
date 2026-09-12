#!/usr/bin/env python3
"""Sandbox mutant M3: drop failed R03 records and recompute the stage-2 verdict."""
import importlib.util, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
spec = json.loads((ROOT / "artifacts/formulation/rule_spec.json").read_text())
s = importlib.util.spec_from_file_location("w06_engine_m3", ROOT / "artifacts/worker-06/spec_conformance_audit.py")
m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
rep = m.audit_file(Path(sys.argv[1]), spec)
checks = [c for c in rep.get("checks", []) if not (c.get("rule") == "R03" and c.get("verdict") == "fail")]
failed = sorted({c["rule"] for c in checks if c.get("verdict") == "fail"})
rep["verdict"] = "reject" if failed else "accept"
rep["failed_rules"] = failed
print(json.dumps({"verdict": rep["verdict"], "failed_rules": failed}))
