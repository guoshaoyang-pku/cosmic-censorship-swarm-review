from pathlib import Path
import importlib.util, json, hashlib, copy, sys, yaml
from datetime import datetime,timezone,timedelta
ROOT=Path('/data3/guoshaoyang/workdir/ai4math-swarm')
DEST=ROOT/'artifacts/formulation/candidates/r03-scope-20260912-0615'
DEST.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
base=ROOT/'artifacts/worker-06/spec_conformance_audit.py'
source=Path('/tmp/r03_scope_candidate.py').read_text()
code=base.read_text()
old='''                for b in binders:
                    if b not in formal:
                        bad.append(f"binder {b!r} absent from formal sentence")'''
assert code.count(old)==1
new='''                bad.extend(r03_rendering_problems(ordered, formal, family))'''
code=code.replace(old,new)
code=code.replace('class Audit:',source+'\n\nclass Audit:',1)
# No relative-import or default-spec ambiguity in the staged CLI.
oldroot='ROOT = HERE.parent.parent'
assert code.count(oldroot)==1
code=code.replace(oldroot,'ROOT = Path('+repr(str(ROOT))+')',1)
tool=DEST/'spec_conformance_audit_candidate.py'
if tool.exists(): assert tool.read_text()==code
else:tool.write_text(code)
compile(code,str(tool),'exec')
def module(path,name):
 spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
candidate=module(tool,'candidate');baseline=module(base,'baseline')
spec=json.loads((ROOT/'artifacts/formulation/rule_spec.json').read_text())
pins=[base,ROOT/'schemas/af_wcc_vacuum.yaml',ROOT/'schemas/af_scc_c2_vacuum.yaml',ROOT/'schemas/af_scc_c0_vacuum.yaml',ROOT/'artifacts/formulation/FROZEN.json',ROOT/'research_map/class_separation.py']
pre={str(p.relative_to(ROOT)):sha(p) for p in pins}
f1=yaml.safe_load((ROOT/'artifacts/formulation/candidates/closure-20260912-0555/af_wcc_vacuum.yaml').read_text())
formal=f1['quantifiers']['formal'];tail='not exists (q,t0) in D5 with gamma([t0,T)) subset J^-(q) intersect M.'
assert formal.count(tail)==1
cases=[('grouped_pair',formal,True),('grouped_formatting',formal.replace('not exists (q,t0)','not exists   (q,t0)'),True)]
for name,text in [
 ('loose_tail_binder','not exists q in I+ with gamma([t0,T)) subset J^-(q) intersect M, and t0 in [0,T).'),
 ('unbound_pair_mention','not exists q in I+ with gamma([t0,T)) subset J^-(q) intersect M. The tuple (q,t0) is mentioned.'),
 ('wrong_polarity','exists (q,t0) in D5 with gamma([t0,T)) subset J^-(q) intersect M.'),
 ('wrong_domain','not exists (q,t0) in D4 with gamma([t0,T)) subset J^-(q) intersect M.'),
 ('wrong_containment','not exists (q,t0) in D5 with gamma([t0,T)) not subset J^-(q) intersect M.'),
 ('escaped_postcondition',tail+' Or a visible singularity exists.'),
 ('swapped_binder','not exists (t0,q) in D5 with gamma([t0,T)) subset J^-(q) intersect M.'),
 ('extra_negation','not '+tail),
]:cases.append((name,formal.replace(tail,text),False))
cases.append(('unscoped_geodesic',formal.replace('forall future-inextendible causal geodesics','exists future-inextendible causal geodesics'),False))
rows=[]
for name,text,expected in cases:
 d=copy.deepcopy(f1);d['quantifiers']['formal']=text
 p=DEST/(name+'.yaml');p.write_text(yaml.safe_dump(d,sort_keys=False,allow_unicode=True))
 bs=baseline.Audit(spec).run(d);cs=candidate.Audit(spec).run(d)
 b=[x for x in bs if x['rule']=='R03'];c=[x for x in cs if x['rule']=='R03']
 ok=all(x['verdict']!='fail' for x in c)
 rows.append({'case':name,'fixture_sha256':sha(p),'expected_r03_pass':expected,'baseline_r03':b,'candidate_r03':c,'matches':ok==expected})
for f in ['af_scc_c2_vacuum.yaml','af_scc_c0_vacuum.yaml']:
 d=yaml.safe_load((ROOT/'schemas'/f).read_text());b=baseline.Audit(spec).run(d);c=candidate.Audit(spec).run(d)
 rows.append({'case':f,'non_wcc_all_checks_unchanged':b==c,'matches':b==c})
post={str(p.relative_to(ROOT)):sha(p) for p in pins};assert pre==post
report={'created_at':datetime.now(timezone(timedelta(hours=8))).isoformat(),'status':'isolated_development_regression_only','source_tool_sha256':sha(base),'candidate_tool_sha256':sha(tool),'rule_spec_sha256':sha(ROOT/'artifacts/formulation/rule_spec.json'),'protected_pre':pre,'protected_post':post,'cases':rows,'all_expected':all(x['matches'] for x in rows),'scope':'R03 terminal WCC quantifier serialization only; not a full semantic verifier, blind review, or held-out corpus','gate_effect':'none; final tool must be reviewed and pinned before gate use','limitations':['Rejects unsupported natural-language paraphrases rather than inferring scope','Does not establish conformal gauge completeness','Other semantic blind spots remain; F1/F2 final reviews are outstanding']}
(DEST/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'report':str(DEST/'report.json'),'sha256':sha(DEST/'report.json'),'all_expected':report['all_expected'],'cases':[(x['case'],x['matches']) for x in rows]}))
assert report['all_expected']

