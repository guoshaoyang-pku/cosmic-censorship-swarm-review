#!/usr/bin/env python3
"""Re-measure the FORM-HELDOUT-07 corpus with the current two-stage pipeline.

CAVEAT (must travel with the numbers): the gate rules R26-R30 were written after reading the
held-out report's FAMILY LIST, so the 'after' number is not out-of-sample for those families.
The 'before' numbers are worker-06's, measured with gate sha ea3deb8c42b5 before hardening.
"""
import json, subprocess, sys, hashlib
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
C = ROOT/"artifacts/worker-06/heldout_corpus"
GATE = ROOT/"artifacts/formulation/tools/check_class_schema.py"
SEM = ROOT/"artifacts/worker-06/spec_conformance_audit.py"
def run(tool, p, jf):
    args=[sys.executable,str(tool)]+(["--json",str(p)] if jf else [str(p)])
    r=subprocess.run(args,capture_output=True,text=True)
    if jf:
        try: d=json.loads(r.stdout); return d.get("verdict","?")
        except Exception: return f"crash{r.returncode}"
    try:
        d=json.loads(r.stdout); v=d.get("verdict"); return "pass" if str(v).lower() in ("accept","pass","ok") else "fail"
    except Exception: return "pass" if r.returncode==0 else "fail"
muts=sorted(C.glob("h*.yaml")); ctrls=sorted(C.glob("c*.yaml"))
rep={"corpus":str(C.relative_to(ROOT)),"gate_sha256":hashlib.sha256(GATE.read_bytes()).hexdigest(),
     "before":{"by":"worker-06","structural_escape":0.3846,"semantic_escape":0.7692,"union_escape":0.3462,
               "note":"measured with gate sha ea3deb8c42b5 before R26-R30"},
     "caveat":"R26-R30 were informed by the held-out family list; this recheck is NOT out-of-sample for those families.",
     "mutants":[],"controls":[]}
esc=[]
for p in muts:
    g=run(GATE,p,True); s=run(SEM,p,False); caught = (g=="fail") or (s=="fail")
    fam=p.stem.split("_",1)[1]
    rep["mutants"].append({"fixture":p.name,"structural":g,"semantic":s,"union_caught":caught,"family":fam})
    if not caught: esc.append(p.name)
for p in ctrls:
    g=run(GATE,p,True); s=run(SEM,p,False)
    rep["controls"].append({"control":p.name,"structural":g,"semantic":s,"ok":g=="pass" and s=="pass"})
n=len(muts)
rep["after"]={"structural_caught":sum(1 for m in rep["mutants"] if m["structural"]=="fail"),
              "semantic_caught":sum(1 for m in rep["mutants"] if m["semantic"]=="fail"),
              "union_caught":sum(1 for m in rep["mutants"] if m["union_caught"]),
              "union_escape":round(len(esc)/n,4),"union_escapes":esc,
              "controls_ok":all(c["ok"] for c in rep["controls"])}
out=ROOT/"artifacts/formulation/evidence/heldout_recheck.json"
out.write_text(json.dumps(rep,indent=2)+"\n")
print(json.dumps({"before":rep["before"],"after":rep["after"]},indent=1))
