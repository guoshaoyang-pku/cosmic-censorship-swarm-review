#!/usr/bin/env python3
"""Audit lifecycle-09 census: hash-bound verdict coverage for the audit gate targets.

Read-only. Measures the canonical bytes, then binds every review record in
research_map/research_map.json to a target pin by SHA256 (full or 12-hex prefix).
A verdict counts for a class only if the pin hash appears in target_id, or the
canonical path appears in target_id AND the pin hash appears in evidence_refs.

Output: artifacts/audit/l09/audit_l09_census.json
"""
import hashlib, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(ROOT)

def sha(p):
    with open(p, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()

def measure(path):
    try:
        h = sha(path)
        return {"path": path, "sha256": h, "bytes": os.path.getsize(path), "exists": True}
    except FileNotFoundError:
        return {"path": path, "sha256": None, "bytes": None, "exists": False}

m = json.load(open('research_map/research_map.json'))
frozen = json.load(open('artifacts/formulation/FROZEN.json'))

TARGETS = {
    "F1":  {"path": "schemas/af_wcc_vacuum.yaml",              "pin": frozen['files']['schemas/af_wcc_vacuum.yaml']['sha256'],      "author": "astra-lead-formulation", "gate": "G-FORM"},
    "F2a": {"path": "schemas/af_scc_c2_vacuum.yaml",           "pin": frozen['files']['schemas/af_scc_c2_vacuum.yaml']['sha256'],   "author": "astra-lead-formulation", "gate": "G-FORM"},
    "F2b": {"path": "schemas/af_scc_c0_vacuum.yaml",           "pin": frozen['files']['schemas/af_scc_c0_vacuum.yaml']['sha256'],   "author": "astra-lead-formulation", "gate": "G-FORM"},
    "F0":  {"path": "research_map/formulation_taxonomy.yaml",   "pin": frozen['files']['research_map/formulation_taxonomy.yaml']['sha256'], "author": "astra-lead-formulation", "gate": "G-F0"},
    "L0":  {"path": "ledger/theorems.jsonl",                   "pin": "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28", "author": "astra-lead-literature", "gate": "G-LIT"},
    "A0":  {"path": "evaluation_rubric.yaml",                  "pin": "d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885", "author": "astra-lead-audit", "gate": "G-AUDIT"},
}

measured = {}
for name, t in TARGETS.items():
    mm = measure(t['path'])
    measured[name] = mm
    t['measured_sha256'] = mm['sha256']
    t['pin_matches_measured'] = (mm['sha256'] == t['pin'])

FROZEN_m = measure('artifacts/formulation/FROZEN.json')
SCHEMAS_OTHER = {p: measure(p) for p in (
    'research_map/class_separation.py', 'runtime/bin/classsep_regression.py',
    'schemas/f1_falsifier_tests.jsonl', 'artifacts/formulation/evidence/taxonomy_consistency.json',
    'schemas/af_scc_regularities.yaml', 'schemas/af_scc_c0_vacuum.yaml.sha256', 'entry_hashes.json')}

def binds(rev, name, path, pin):
    """True iff this review record binds THIS target pin (defensible strict rule)."""
    t = str(rev.get('target_id') or '')
    refs = json.dumps(rev.get('evidence_refs') or [])
    if pin in t or pin[:12] in t:
        return True
    if path in t and (pin in refs or pin[:12] in refs):
        return True
    # generic class-name target: only that class name, and the pin must be in refs
    if t.strip() == name and (pin in refs or pin[:12] in refs):
        return True
    return False

census = {}
for name, t in TARGETS.items():
    rows = []
    for r in m['reviews']:
        if not binds(r, name, t['path'], t['pin']):
            continue
        reviewer = r.get('reviewer') or r.get('actor')
        hf = r.get('hard_failures')
        rows.append({
            "created_at": r.get('created_at'),
            "event_id": r.get('event_id'),
            "reviewer": reviewer,
            "verdict": r.get('verdict'),
            "score": r.get('score'),
            "full_schema": r.get('counts_as_full_schema_verdict'),
            "non_author": reviewer != t['author'],
            "hard_failures": hf,
            "n_hard": (len(hf) if isinstance(hf, list) else (1 if hf else 0)),
            "findings_head": (json.dumps(r.get('findings'))[:400] if r.get('findings') else None),
        })
    rows.sort(key=lambda x: x['created_at'] or '')
    accepts = [x for x in rows if x['verdict'] == 'accept' and x['non_author']]
    revises = [x for x in rows if x['verdict'] == 'revise']
    census[name] = {
        "path": t['path'], "pin": t['pin'], "measured_sha256": t['measured_sha256'],
        "pin_matches_measured": t['pin_matches_measured'], "author": t['author'], "gate": t['gate'],
        "n_bound": len(rows),
        "accepts_non_author": accepts,
        "accepts_non_author_full": [x for x in accepts if x['full_schema']],
        "revises": revises,
        "inconclusive": [x for x in rows if x['verdict'] == 'inconclusive'],
        "verdict_rows": rows,
    }

out = {
    "schema": "audit-l09-census/1",
    "created_at": __import__('datetime').datetime.now().astimezone().isoformat(timespec='seconds'),
    "lifecycle": "lead-audit-lifecycle-09",
    "targets": census,
    "measured_hashes": {k: v['sha256'] for k, v in measured.items()},
    "frozen_manifest": FROZEN_m,
    "frozen_revision": frozen.get('revision'),
    "aux_hashes": {k: v['sha256'] for k, v in SCHEMAS_OTHER.items()},
    "frozen_pin_vs_live": {p: {"pin": v['sha256'], "live": SCHEMAS_OTHER[p]['sha256'], "match": v['sha256'] == SCHEMAS_OTHER[p]['sha256']}
                           for p, v in frozen['files'].items() if p in SCHEMAS_OTHER},
}
os.makedirs('artifacts/audit/l09', exist_ok=True)
json.dump(out, open('artifacts/audit/l09/audit_l09_census.json', 'w'), indent=1)

for name, t in census.items():
    print(f"{name:4s} pin={t['pin'][:12]} live={str(t['measured_sha256'])[:12]} match={t['pin_matches_measured']} "
          f"bound={t['n_bound']} accepts(non-author)={len(t['accepts_non_author'])} full={len(t['accepts_non_author_full'])} revises={len(t['revises'])}")
    for a in t['accepts_non_author_full']:
        print(f"     ACCEPT-full {a['created_at']} {a['reviewer']}")
    late = [r for r in t['revises'] if (r['created_at'] or '') >= '2026-09-12T01:00']
    for r in late:
        print(f"     REVISE-late {r['created_at']} {r['reviewer']} score={r['score']} n_hard={r['n_hard']}")
print("\naux pins:")
for p, v in out['frozen_pin_vs_live'].items():
    print(f"  frozen_pin_matches_live={v['match']}  {p}")
print("live aux:", json.dumps(out['aux_hashes'], indent=1))
