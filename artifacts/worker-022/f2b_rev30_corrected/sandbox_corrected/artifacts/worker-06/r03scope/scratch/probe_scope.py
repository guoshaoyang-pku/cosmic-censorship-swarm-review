#!/usr/bin/env python3
"""Quick scope-safety probe: run the lead's three F1 tails through every published R03 tool."""
import hashlib, json, subprocess, sys
from pathlib import Path
import yaml

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
OUT = ROOT / "artifacts/worker-06/r03scope/scratch"
CANON = ROOT / "schemas/af_wcc_vacuum.yaml"
SPEC = ROOT / "artifacts/formulation/rule_spec.json"
TOOLS = {
 "frozen_c79d8ab8440a": "artifacts/worker-06/spec_conformance_audit.py",
 "r03v2_e41a4b23a840": "artifacts/worker-06/r03v2/audit_r03v2.py",
 "cand_004_645eb16a0060": "artifacts/worker-004/f1_r03_repair/patched/spec_conformance_audit.py",
 "cand_E3_3f69bc1eb27a": "artifacts/worker-064/r03_cause/work/cand_E3/artifacts/worker-06/spec_conformance_audit.py",
}
ANCHOR = "with finite affine length: "
TAILS = {
 "frozen_variable_wise": "not exists q in I+ and t0 in [0,T) with gamma([t0,T)) subset J^-(q) intersect M.",
 "grouped_tuple": "not exists (q,t0) in D5 with gamma([t0,T)) subset J^-(q) intersect M.",
 "scope_error_binds_q_only": "not exists q in I+ with gamma([t0,T)) subset J^-(q) intersect M, and t0 in [0,T).",
}
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def make(name, tail):
    doc = yaml.safe_load(CANON.read_text())
    f = doc["quantifiers"]["formal"]; i = f.index(ANCHOR)+len(ANCHOR)
    assert f[i:].strip() == TAILS["frozen_variable_wise"], f[i:]
    doc["quantifiers"]["formal"] = f[:i] + tail
    p = OUT / f"variant_{name}.yaml"; p.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)); return p
def run(tool, target):
    js = OUT / "res.json"
    if js.exists(): js.unlink()
    r = subprocess.run([sys.executable, str(ROOT/tool), str(target), "--spec", str(SPEC), "--json", str(js)],
                       capture_output=True, text=True, timeout=120)
    v, rules = "?", []
    print("DEBUG", " ".join([sys.executable, str(ROOT/tool), str(target), "--spec", str(SPEC), "--json", str(js)])); print("ERR", r.stderr[-300:])
    if js.exists():
        j = json.loads(js.read_text()); v = j.get("verdict"); rules = j.get("failed_rules", [])
    return v, rules
res = {}
print("pins pre:"); pins = {t: sha(ROOT/p) for t,p in TOOLS.items()}; pins["canon"] = sha(CANON)
for k,v in pins.items(): print(" ", k, v[:12])
for name, tail in TAILS.items():
    p = make(name, tail)
    res[name] = {t: run(TOOLS[t], p) for t in TOOLS}
    # also canonical itself
res["canonical_F1"] = {t: run(TOOLS[t], CANON) for t in TOOLS}
pins_post = {t: sha(ROOT/p) for t,p in TOOLS.items()}; pins_post["canon"] = sha(CANON)
print(json.dumps({"pins_pre": pins, "pins_post": pins_post,
                  "drift": [k for k in pins if pins[k]!=pins_post[k]],
                  "matrix": {n:{t:list(v) for t,v in d.items()} for n,d in res.items()}}, indent=1))
