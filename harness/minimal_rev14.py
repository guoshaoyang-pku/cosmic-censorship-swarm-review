from pathlib import Path
import shutil, hashlib, json, subprocess

base = Path('/data3/guoshaoyang/workdir/ai4math-swarm')
out = Path('/tmp/minimal_rev14_candidates')
out.mkdir(exist_ok=True)
f1 = out / 'af_wcc_vacuum.yaml'
f2 = out / 'af_scc_c0_vacuum.yaml'
shutil.copy2(base / 'schemas/af_wcc_vacuum.yaml', f1)
shutil.copy2(base / 'schemas/af_scc_c0_vacuum.yaml', f2)
old = 'not exists q in I+ and t0 in [0,T) with gamma([t0,T)) subset J^-(q) intersect M.'
new = 'not exists (q,t0) with q in I+ and t0 in [0,T) such that gamma([t0,T)) subset J^-(q) intersect M.'
s = f1.read_text()
assert old in s
f1.write_text(s.replace(old, new, 1))
lines = f2.read_text().splitlines()
i = next(i for i, x in enumerate(lines) if 'rev14 delta (astra-life08-formulation-rev14' in x)
lines[i] = '  - {index: 12, at: "2026-09-12T01:35:00+08:00", unused: false, notes: ["rev14 bounded wording repair: extension-set containment direction and implication ledger recorded; no class-semantics change."] }'
f2.write_text('\n'.join(lines) + '\n')
result = {'schema': 'minimal-rev14-candidate-validation/v1', 'candidates': []}
for cls, p in [('F1', f1), ('F2b', f2)]:
    r = subprocess.run(['python3', 'artifacts/formulation/tools/check_class_schema.py', '--json', str(p)], cwd=base, capture_output=True, text=True)
    st = json.loads(r.stdout)
    r = subprocess.run(['python3', 'artifacts/worker-06/spec_conformance_audit.py', '--json', '/tmp/minsem.json', str(p)], cwd=base, capture_output=True, text=True)
    se = json.loads(Path('/tmp/minsem.json').read_text())
    result['candidates'].append({'class': cls, 'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'bytes': p.stat().st_size, 'structural': st.get('verdict'), 'structural_failed_rules': st.get('failed_rules', []), 'semantic': se.get('verdict'), 'semantic_failed_rules': se.get('failed_rules', se.get('fails', []))})
(base / 'artifacts/formulation/evidence/minimal_rev14_candidate_validation.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
