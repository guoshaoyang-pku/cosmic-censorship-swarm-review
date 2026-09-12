#!/usr/bin/env python3
"""Re-base the FORM-HELDOUT-07 mutations onto the CURRENT frozen canonical C0 schema and
re-measure the two-stage union escape rate. This removes the staleness confound in
measure_heldout.py (whose controls were older-revision copies).

CAVEAT: gate rules R26-R30 were written after reading the held-out FAMILY LIST, so the
'after' rate is not out-of-sample for those families. 'before' is worker-06's out-of-sample
measurement with the pre-hardening gate.
"""
from __future__ import annotations
import ast, copy, hashlib, json, re, shutil, subprocess, sys
from pathlib import Path
import yaml
ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT/"artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
MAN = ROOT/"artifacts/worker-06/heldout_corpus/manifest.json"
TMP = ROOT/"artifacts/formulation/evidence/heldout_rebased"
GATE = ROOT/"artifacts/formulation/tools/check_class_schema.py"
SEM = ROOT/"artifacts/worker-06/spec_conformance_audit.py"

def parse(text):
    text=text.strip()
    m=re.match(r"^delete\s+([\w.\[\]]+)\s*=\s*None$",text)
    if m: return ("delete",m.group(1),None)
    m=re.match(r"^([\w.\[\]]+)\s*=\s*(.*)$",text,re.S)
    if not m: return None
    path,raw=m.group(1),m.group(2).strip()
    try: val=ast.literal_eval(raw)
    except Exception: val=raw.strip("'\"")
    return ("set",path,val)

def apply_op(doc,op):
    kind,path,val=op; cur=doc
    parts=re.split(r"\.(?![^\[]*\])",path)
    for p in parts[:-1]:
        key=re.sub(r"\[\d+\]$","",p)
        idx=re.search(r"\[(\d+)\]$",p)
        if idx is not None:
            cur=cur.setdefault(key,[]); 
            while len(cur)<=int(idx.group(1)): cur.append({})
            cur=cur[int(idx.group(1))]
        else:
            cur=cur.setdefault(p,{})
    last=parts[-1]; key=re.sub(r"\[\d+\]$","",last); idx=re.search(r"\[(\d+)\]$",last)
    if kind=="delete":
        if idx is not None: cur[key].pop(int(idx.group(1)))
        else: cur.pop(key,None)
    else:
        if idx is not None: cur[key][int(idx.group(1))]=val
        else: cur[key]=val

def run(tool,p,jf):
    args=[sys.executable,str(tool)]+(["--json",str(p)] if jf else [str(p)])
    r=subprocess.run(args,capture_output=True,text=True)
    if jf:
        try: d=json.loads(r.stdout); return d.get("verdict","?")
        except Exception: return f"crash{r.returncode}"
    try:
        d=json.loads(r.stdout); return "pass" if str(d.get("verdict")).lower() in ("accept","pass","ok") else "fail"
    except Exception: return "pass" if r.returncode==0 else "fail"

def main():
    man=json.loads(MAN.read_text()); base=yaml.safe_load(BASE.read_text())
    if TMP.exists(): shutil.rmtree(TMP)
    TMP.mkdir(parents=True)
    rep={"corpus":"FORM-HELDOUT-07","base":str(BASE.relative_to(ROOT)),"base_sha256":hashlib.sha256(BASE.read_bytes()).hexdigest(),
         "gate_sha256":hashlib.sha256(GATE.read_bytes()).hexdigest(),
         "before_by_worker06":{"gate_sha256_prefix":"ea3deb8c42b5","structural_escape":0.3846,"semantic_escape":0.7692,"union_escape":0.3462,
                               "controls_note":"all 7 controls accepted by both stages in that run"},
         "caveat":"R26-R30 were informed by the held-out family list; the after rate is not out-of-sample for those families.",
         "mutants":[],"controls":[]}
    def special(name, d):
        if name.startswith("h08_"):
            d["genericity"]["transfer_failures"].append({"pair":["full_measure","residual_comeager"],"direction":"entails",
                "witness":"a full-measure set is comeager","status":"elementary"})
        elif name.startswith("h15_"):
            d["quantifiers"]["ordered"]=[e for e in d["quantifiers"]["ordered"] if not str(e.get("binder","")).startswith("G_")]
            d["quantifiers"]["formal"]="forall D in X_vac(AF): not exists proper_future_C0_metric_extension(MGHD(D))"
        elif name.startswith("h18_"):
            d["implication_ledger"]["one_way_entailments"].append({"from":"no proper future C2 extension",
                "to":"no proper future C0 extension","relation":"entails","reason":"converse","status":"elementary"})
        elif name.startswith("h23_"):
            d["class_contract_pointer"]="artifacts/formulation/formulation_taxonomy.yaml#class_contracts.AF-SCC-C2-VAC-GEN"
        elif name.startswith("h24_"):
            d["scope_statement"]=str(d.get("scope_statement",""))+" and no extension with a twice-differentiable metric exists"
        elif name.startswith("h25_"):
            d["data_class"].pop("asymptotic_decay",None)
        elif name.startswith("h26_"):
            o=d["quantifiers"]["ordered"]; last=o.pop(); o.insert(1,last)  # extension quantifier before the data quantifier
        return d
    for fx in man["mutants"]:
        d=copy.deepcopy(base)
        if fx["fixture"].startswith(("h08_","h15_","h18_","h23_","h24_","h25_","h26_")):
            d=special(fx["fixture"],d)
        else:
            op=parse(fx["mutation"])
            if op is None:
                rep["mutants"].append({"fixture":fx["fixture"],"error":"unparsed","mutation":fx["mutation"]}); continue
            apply_op(d,op)
        p=TMP/fx["fixture"]; p.write_text(yaml.safe_dump(d,sort_keys=False,width=120))
        g=run(GATE,p,True); s=run(SEM,p,False); caught=(g=="fail") or (s=="fail")
        rep["mutants"].append({"fixture":fx["fixture"],"family":fx["family"],"rephrased":fx["rephrased"],
                               "structural":g,"semantic":s,"union_caught":caught})
    # fresh controls on the current canonical layout
    ctrls=[("ctrl_canonical_base",lambda x:None),
           ("ctrl_quoted_phrase",lambda x:x["anti_scope"]["phrases_that_are_not_this_class"].append(
               "the forbidden composite wording 'C0 or C2' is quoted only to ban it"))]
    for name,mut in ctrls:
        d=copy.deepcopy(base); mut(d); p=TMP/f"{name}.yaml"; p.write_text(yaml.safe_dump(d,sort_keys=False,width=120))
        g=run(GATE,p,True); s=run(SEM,p,False)
        rep["controls"].append({"control":name,"structural":g,"semantic":s,"ok":g=="pass" and s=="pass"})
    muts=[m for m in rep["mutants"] if "error" not in m]
    esc=[m["fixture"] for m in muts if not m["union_caught"]]
    rep["after"]={"mutants":len(muts),"structural_caught":sum(1 for m in muts if m["structural"]=="fail"),
                  "semantic_caught":sum(1 for m in muts if m["semantic"]=="fail"),
                  "union_caught":len(muts)-len(esc),"union_escape":round(len(esc)/len(muts),4),
                  "union_escapes":esc,"controls_ok":all(c["ok"] for c in rep["controls"])}
    out=ROOT/"artifacts/formulation/evidence/heldout_rebased.json"; out.write_text(json.dumps(rep,indent=2)+"\n")
    print(json.dumps({"before":rep["before_by_worker06"],"after":rep["after"]},indent=1))
main()
