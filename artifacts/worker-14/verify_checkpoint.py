#!/usr/bin/env python3
"""Hash-drift and state verification checkpoint for worker-14."""
import hashlib, json, subprocess, sys, time
from pathlib import Path
ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]
files = ["numerics/protocol/convergence_protocol.md","numerics/protocol/convergence_demo.py",
         "numerics/protocol/demo_output.json","numerics/protocol/demo_report_standard.json",
         "numerics/protocol/demo_report_wrong_order.json","numerics/protocol/audit_convergence_report.py",
         "numerics/protocol/scheme_independence_review.md","numerics/protocol/scheme_independence_check.py",
         "numerics/protocol/scheme_independence_evidence.json","numerics/protocol/build_gate_reports.py",
         "numerics/protocol/report_lffd.json","numerics/protocol/report_cnfd.json",
         "numerics/protocol/gate_reports_summary.json"]
rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "checkpoint": "verify",
       "hashes": {f: sha(f) for f in files},
       "replication_sha16": sha("numerics/tests/flat_wave_replication.py"),
       "candidate_sha16": sha("numerics/tests/flat_wave.py"),
       "gates_sha16": sha("numerics/gates.py"),
       "inbox_lines": sum(1 for _ in open(ROOT/"comms/inbox/deepseek-flash-14.jsonl")),
       "outbox_files": len(list((ROOT/"comms/outbox").iterdir()))}
sys.path.insert(0, str(ROOT))
try:
    from numerics.gates import evaluate
    r = evaluate(ROOT)
    rec["gates_evaluate"] = {"ok": True, "verdict": r.get("verdict"),
                             "blocking_reasons": r.get("blocking_reasons")}
except Exception as exc:
    rec["gates_evaluate"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
with open(ROOT/"artifacts/worker-14/checkpoints.jsonl","a") as f:
    f.write(json.dumps(rec, sort_keys=True)+"\n")
print(json.dumps(rec, indent=1, sort_keys=True))
