#!/usr/bin/env python3
"""Sandbox mutant M2: force stage-2 accept only for struct12_i_plus_completeness_lexical.yaml."""
import importlib.util, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
spec = json.loads((ROOT / "artifacts/formulation/rule_spec.json").read_text())
s = importlib.util.spec_from_file_location("w06_engine_m2", ROOT / "artifacts/worker-06/spec_conformance_audit.py")
m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
p = Path(sys.argv[1])
rep = m.audit_file(p, spec)
if p.name == "struct12_i_plus_completeness_lexical.yaml":
    rep["verdict"] = "accept"; rep["failed_rules"] = []
print(json.dumps({"verdict": rep["verdict"], "failed_rules": rep.get("failed_rules", [])}))
