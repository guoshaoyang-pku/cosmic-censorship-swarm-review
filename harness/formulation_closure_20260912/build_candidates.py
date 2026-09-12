from pathlib import Path
import hashlib, json, yaml, importlib.util, subprocess, sys, difflib
from datetime import datetime, timezone, timedelta
ROOT=Path('/data3/guoshaoyang/workdir/ai4math-swarm')
DEST=ROOT/'artifacts/formulation/candidates/closure-20260912-0555'
DEST.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
protected=[ROOT/x for x in ['schemas/af_wcc_vacuum.yaml','schemas/af_scc_c2_vacuum.yaml','schemas/af_scc_c0_vacuum.yaml','artifacts/formulation/FROZEN.json','research_map/formulation_taxonomy.yaml','artifacts/formulation/formulation_taxonomy.yaml','research_map/class_separation.py','artifacts/worker-06/spec_conformance_audit.py']]
pre={str(p.relative_to(ROOT)):sha(p) for p in protected}
def diffs(a,b,p='$'):
 if type(a)!=type(b):return [p]
 if isinstance(a,dict):return [x for k in a.keys()|b.keys() for x in ([p+'.'+k] if k not in a or k not in b else diffs(a[k],b[k],p+'.'+k))]
 if isinstance(a,list):return [p] if len(a)!=len(b) else [x for i in range(len(a)) for x in diffs(a[i],b[i],p+'['+str(i)+']')]
 return [] if a==b else [p]
def replace_once(s,a,b):
 assert s.count(a)==1, (a,s.count(a))
 return s.replace(a,b,1)
def record(src,name,text,expected):
 p=DEST/name
 if p.exists():assert p.read_text()==text, 'immutable candidate path already exists'
 else:p.write_text(text)
 a=yaml.safe_load(src.read_text()); b=yaml.safe_load(text)
 ds=sorted(diffs(a,b));assert ds==sorted(expected),(ds,expected)
 run=subprocess.run([sys.executable,str(ROOT/'artifacts/formulation/tools/check_class_schema.py'),'--json',str(p)],text=True,capture_output=True)
 try:report=json.loads(run.stdout)
 except Exception:report={'error':run.stderr,'stdout':run.stdout}
 patch=''.join(difflib.unified_diff(src.read_text().splitlines(True),text.splitlines(True),fromfile=str(src.relative_to(ROOT)),tofile=str(p.relative_to(ROOT))))
 (DEST/(name+'.diff')).write_text(patch)
 return {'path':str(p.relative_to(ROOT)),'sha256':sha(p),'source_path':str(src.relative_to(ROOT)),'source_sha256':sha(src),'changed_paths':ds,'structural':report,'returncode':run.returncode}
src=ROOT/'schemas/af_scc_c0_vacuum.yaml'
text=Path('/tmp/af_scc_c0_vacuum_rev14_isolated.yaml').read_text()
f2b=record(src,'af_scc_c0_vacuum.yaml',text,['$.revision_history[11].notes[0]'])
f2b['record_index_field']=12
src=ROOT/'schemas/af_wcc_vacuum.yaml'; raw=src.read_text(); doc=yaml.safe_load(raw)
raw=replace_once(raw,'not exists q in I+ and t0 in [0,T) with gamma([t0,T)) subset J^-(q) intersect M.','not exists (q,t0) in D5 with gamma([t0,T)) subset J^-(q) intersect M.')
old=doc['i_plus']['completeness_definition']
new='Every null geodesic generator lying in I+ is future-complete in the affine parameter of the specified conformal metric gtilde. This concerns generators within I+, not physical null geodesics in M approaching I+. No equivalence of these two completeness conditions is asserted.'
raw=replace_once(raw,json.dumps(old,ensure_ascii=False),json.dumps(new,ensure_ascii=False))
old=doc['i_plus']['completeness_definition_status']
new='Candidate convention only: conformal gauge and allowed rescalings remain unresolved and require formulation-lead adjudication before freeze. No theorem equating boundary-generator completeness with physical null-geodesic completeness is asserted. Structural validation does not discharge this obligation.'
raw=replace_once(raw,json.dumps(old,ensure_ascii=False),json.dumps(new,ensure_ascii=False))
f1=record(src,'af_wcc_vacuum.yaml',raw,['$.quantifiers.formal','$.i_plus.completeness_definition','$.i_plus.completeness_definition_status'])
post={str(p.relative_to(ROOT)):sha(p) for p in protected};assert pre==post
report={'created_at':datetime.now(timezone(timedelta(hours=8))).isoformat(),'status':'isolated_candidates_not_published','candidates':[f2b,f1],'protected_pre':pre,'protected_post':post,'invariants_unchanged':pre==post,'gate_effect':'none; G-FORM and G-AUDIT remain pending, N1 locked','blind_reviews':0,'heldout_reviews':0,'open_obligations':['F1 conformal gauge normalization and completeness definition require adjudication','Scope-aware R03 tool candidate and pinned instrument required','Final authorized publication and fresh independent blind reviews required','Previously exposed fixture families cannot serve as held-out']}
(DEST/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'dest':str(DEST),'report_sha256':sha(DEST/'validation.json'),'candidates':report['candidates'],'protected_unchanged':pre==post}))

