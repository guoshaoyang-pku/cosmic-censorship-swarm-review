#!/usr/bin/env python3
"""Control: run the canonical regression runner (runtime/bin/classsep_regression.py)
against the worker-081 candidate module, without touching the canonical detector.
The runner is unmodified; only sys.modules['class_separation'] is preloaded."""
import importlib.util
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CAND = ROOT / "artifacts/worker-081/classsep_clause_candidate/class_separation_clause.py"

spec = importlib.util.spec_from_file_location("class_separation", CAND)
mod = importlib.util.module_from_spec(spec)
sys.modules["class_separation"] = mod
spec.loader.exec_module(mod)

sys.argv = ["classsep_regression.py", "--verbose"]
runpy.run_path(str(ROOT / "runtime/bin/classsep_regression.py"), run_name="__main__")
