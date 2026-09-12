#!/usr/bin/env python3
"""Audit lifecycle-09 outbox emitter (idempotent: skips event_ids already in the outbox)."""
import hashlib, json, os, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(ROOT)
OUT = 'comms/outbox/astra-lead-audit.jsonl'
NOW = datetime.datetime.now().astimezone().isoformat(timespec='seconds')
STAMP_FILE = 'artifacts/audit/l09/EMIT_STAMP'
if os.path.exists(STAMP_FILE):
    STAMP = open(STAMP_FILE).read().strip()
else:
    STAMP = datetime.datetime.now().strftime('%Y%m%dT%H%M%S')
    open(STAMP_FILE, 'w').write(STAMP + '\n')

def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()

existing = set()
if os.path.exists(OUT):
    for line in open(OUT):
        line = line.strip()
        if not line:
            continue
        try:
            existing.add(json.loads(line).get('event_id'))
        except Exception:
            pass

E = []
def ev(**kw):
    kw.setdefault('actor', 'astra-lead-audit')
    kw.setdefault('created_at', NOW)
    E.append(kw)

P = {
    'gform': 'reviews/G-FORM-final-verify-r3.json',
    'l0': 'reviews/L0-review-final-verify.json',
    'a0': 'reviews/A0-review-final-verify.json',
    'n0': 'reviews/N0-review-final-verify.json',
    'census': 'artifacts/audit/l09/audit_l09_census.json',
    'census_py': 'artifacts/audit/l09/audit_l09_census.py',
    'audit_ev': 'artifacts/audit/l09/audit_evidence_l09.txt',
    'regr': 'artifacts/audit/l09/classsep_regression_l09.txt',
    'status_md': 'artifacts/audit/STATUS.md',
    'ckpt': 'runtime/state/lead_audit_lifecycle_09_checkpoint.json',
    'quar': 'runtime/state/comms_quarantine/astra-lead-audit-inbox-line31-20260912T0117.jsonl',
}

# --- artifacts -----------------------------------------------------------------------------
for key, typ, node, note in (
    ('gform', 'gate_final_verify_r3', 'F1,F2a,F2b', 'coverage adjudication at FROZEN rev29 pins; G-FORM not proposable; hash-bound defect list'),
    ('l0', 'gate_final_verify', 'L0', 'two independent non-author accepts at ledger a1674f094979; HF-14 triple 0/62 re-run by audit; carried HF-01/HF-02 objections'),
    ('a0', 'gate_final_verify_v2', 'A0', 'supersedes the 00:50:20 self-verdict; 0 independent accepts, 8 hash-bound revises; A0 unmet'),
    ('census', 'hash_bound_verdict_census', 'A1', 'strict pin-bound verdict census for F1/F2a/F2b/F0/L0/A0'),
    ('census_py', 'audit_instrument', 'A1', 'read-only census instrument'),
    ('audit_ev', 'canonical_audit_output', 'A1', 'python3 research_map/audit_evidence.py: 24 hard = 23 CLASSSEP + 1 frozen-drift; exit 1'),
    ('regr', 'canonical_audit_output', 'A1', 'classsep_regression at 9f1cf9c336be: 17/17 leaks, 10/10 controls, FP 0 FN 0, PASS'),
    ('ckpt', 'lifecycle_checkpoint', 'A1', 'lead-audit-lifecycle-09 checkpoint'),
    ('quar', 'comms_quarantine', 'A1', 'inbox line 31 quarantined byte-verbatim (no accepted-stream emission, future-dated); NOT actioned'),
):
    ev(event_id=f'audit-l09-art-{key}-{STAMP}', event_type='artifact', node_id=node,
       artifact_type=typ, path=P[key], sha256=sha(P[key]), validation_status='unverified', note=note)

# supersede: G-FORM artifact gained a top-level adjudicated_verdict after the first emission
ev(event_id=f'audit-l09-art-gform-r2-{STAMP}', event_type='artifact', node_id='F1,F2a,F2b',
   artifact_type='gate_final_verify_r3', path=P['gform'], sha256=sha(P['gform']), validation_status='unverified',
   note='supersedes audit-l09-art-gform-20260912T011904; content addition: top-level adjudicated_verdict=revise + verdict_scope. No verdict change.',
   supersedes='audit-l09-art-gform-20260912T011904')

# --- reviews -------------------------------------------------------------------------------
ev(event_id=f'audit-l09-review-gform-r3-{STAMP}', event_type='review', node_id='F1,F2a,F2b', gate='G-FORM',
   target_id='F1@d9cebb9404b2 / F2a@e9a27996dfd3 / F2b@b2ab6acb2bbe (FROZEN rev29 815e08079aef)',
   reviewer='astra-lead-audit', verdict='revise', score=3.0,
   hard_failures=[
       'F2b: blocking carriers at schemas/af_scc_c0_vacuum.yaml:152 (containment denial) and :246 (inverted size premise) reproducible at the frozen bytes; accepting verdicts measured SILENT (w066) and one accept self-superseded (w072, 01:15:24)',
       'F2b: declared-hash layer stale (schemas/af_scc_c0_vacuum.yaml.sha256 256dd18d7944, af_scc_regularities.yaml rev6 27255e5b34f3, entry_hashes.json 09a5b37a190d); check_f2_integration.py overall_verdict=fail',
       'F2a: extension category under-frozen (clause (a)/(c), topology.extension_topology, missing iota_regularity), clause (f) interior witness absent, and HF-047-PC-1 cross-class containment not entailed at the pins',
       'F1: no in-file class-semantics defect, but three carried hash-bound findings (provenance anchors 5/5 unresolved; falsifier corpus 25/25 rows bind rev12 cce9c60146d6; F0-vs-F1 set-strength contradiction needs ESC-2)',
   ],
   findings=[
       'coverage counts at one hash: F1 2/11 full/non-author accepts, F2a 3/8, F2b 3/9; all three pins measured equal to FROZEN rev29 and stable across the round',
       'no gate self-pass: audit assembles coverage, Astra records the gate; G-FORM stays pending',
       'counts bind the census snapshot artifacts/audit/l09/audit_l09_census.json and the map state at measurement; the map is moving (workers landing verdicts through 01:16)',
   ],
   artifact_refs=[P['gform'], P['census']], evidence_refs=[f'{P["gform"]}#sha256:{sha(P["gform"])[:12]}', 'artifacts/formulation/FROZEN.json#815e08079aef'])

ev(event_id=f'audit-l09-review-l0-final-{STAMP}', event_type='review', node_id='L0', gate='G-LIT',
   target_id='ledger/theorems.jsonl#a1674f094979', reviewer='astra-lead-audit', verdict='accept', score=4.0,
   hard_failures=[],
   findings=[
       'two full-schema non-author accepts at one held hash: worker-075 (00:49:30) and worker-079 (01:09:00), plus worker-072 and worker-050 non-full accepts',
       'audit re-ran the HF-14 predicates directly on all 62 rows: status 0, validation_status 0, supports_claim 0',
       'carried objections recorded, not resolved: worker-093 revise HF-02 (8 class_ids-disjunction rows; worker-023 packet resolves them to non-member bindings but the patch is NOT applied) and HF-01 (30 rows conclusion_type=theorem without artifact_refs; applicability explicitly open)',
       'review_status=not_independently_reviewed on all 62 rows is the truthful review axis; L1 ledger/citation_audit.csv 315c19145065 unchanged and not re-reviewed',
   ],
   artifact_refs=[P['l0']], evidence_refs=[f'{P["l0"]}#sha256:{sha(P["l0"])[:12]}', 'ledger/theorems.jsonl#a1674f094979'])

ev(event_id=f'audit-l09-review-a0-final-{STAMP}', event_type='review', node_id='A0', gate='G-AUDIT',
   target_id='evaluation_rubric.yaml#d748a9e3574e', reviewer='astra-lead-audit', verdict='revise', score=3.0,
   hard_failures=[
       'A0-HF-01: zero independent non-author accepts at d748a9e3574e; the only accept on record is by actor lead-audit (author group)',
       'A0-HF-02: detector-scope artifact a26be4b85706 carries an independent revise (worker-021): b3 count 1 vs 7, time-snapshot HF-14 total, and 194 records overstated as literal critical HF-03',
   ],
   findings=[
       '8 hash-bound revises at the rubric hash, 4 of them full-schema',
       'the standing CLASSSEP decision (c) 7714ffd5b467 leaves 19 residual hard findings and the A04 clause FN live; the detector-of-record is unresolved (pin c266dbec vs operative a8c04fc3) and the canonical audit hard-fails on the split',
   ],
   artifact_refs=[P['a0']], evidence_refs=[f'{P["a0"]}#sha256:{sha(P["a0"])[:12]}', 'evaluation_rubric.yaml#d748a9e3574e'])

ev(event_id=f'audit-l09-review-n0-operative-{STAMP}', event_type='review', node_id='N0', gate='G-NUM',
   target_id='numerics/CONVERGENCE_PROTOCOL.md#1e6cdf04d7a2 / numerics/results/flat_wave_convergence_rev3.json#da7c36071995',
   reviewer='astra-lead-audit', verdict='revise', score=3.5,
   hard_failures=['B-N0-R2-1 protocol rule 2 registration gap (6 reviewed paths absent from runtime/state/artifact_hashes.json)',
                  'B-N0-R2-2 review-state supersession semantics unresolved; numerics lead correctly refuses to self-adjudicate'],
   findings=['the operative N0 verdict remains reviews/N0-review-final-verify.json (hash-bound revise, 00:50:20); stop-rule items closed; lock guard verified LOCKED with no numerics/spherical_solver present',
             'deadline 03:00 is not reached in this lifecycle; a hash-bound revise is acceptable closure per the card'],
   artifact_refs=[P['n0']], evidence_refs=[f'{P["n0"]}#sha256:{sha(P["n0"])[:12]}'])

# correction: the first G-FORM review event cited the pre-edit artifact hash (785373093162);
# this event re-binds the adjudication to the current bytes.
ev(event_id=f'audit-l09-review-gform-r3-r2-{STAMP}', event_type='review', node_id='F1,F2a,F2b', gate='G-FORM',
   target_id='F1@d9cebb9404b2 / F2a@e9a27996dfd3 / F2b@b2ab6acb2bbe (FROZEN rev29 815e08079aef)',
   reviewer='astra-lead-audit', verdict='revise', score=3.0,
   supersedes='audit-l09-review-gform-r3-20260912T011904',
   correction='re-binds the review to reviews/G-FORM-final-verify-r3.json at d94dd2d5b778 (top-level adjudicated_verdict added); no verdict change',
   hard_failures=[
       'F2b: blocking carriers at schemas/af_scc_c0_vacuum.yaml:152 (containment denial) and :246 (inverted size premise) reproducible at the frozen bytes; accepting verdicts measured SILENT (w066) and one accept self-superseded (w072, 01:15:24)',
       'F2b: declared-hash layer stale (schemas/af_scc_c0_vacuum.yaml.sha256 256dd18d7944, af_scc_regularities.yaml rev6 27255e5b34f3, entry_hashes.json 09a5b37a190d); check_f2_integration.py overall_verdict=fail',
       'F2a: extension category under-frozen (clause (a)/(c), topology.extension_topology, missing iota_regularity), clause (f) interior witness absent, and HF-047-PC-1 cross-class containment not entailed at the pins',
       'F1: no in-file class-semantics defect, but three carried hash-bound findings (provenance anchors 5/5 unresolved; falsifier corpus 25/25 rows bind rev12 cce9c60146d6; F0-vs-F1 set-strength contradiction needs ESC-2)',
   ],
   findings=['coverage at one hash: F1 2 full of 11 non-author accepts, F2a 3 of 8, F2b 3 of 9; pins equal FROZEN rev29 and stable',
             'no gate self-pass; G-FORM stays pending'],
   artifact_refs=[P['gform'], P['census']],
   evidence_refs=[f'{P["gform"]}#sha256:{sha(P["gform"])[:12]}', 'artifacts/formulation/FROZEN.json#815e08079aef'])

# --- status --------------------------------------------------------------------------------
ev(event_id=f'audit-l09-status-{STAMP}', event_type='status', node_id='A1', status='active', hours=1.0,
   summary=('Lifecycle-09 (one independent lifecycle): G-FORM r3 adjudicated at the FROZEN rev29 pins -> NOT proposable; '
            'L0 rows 62, HF-14 triple 0, two independent full accepts -> proposable with carried objections; A0 -> unmet, 0 independent accepts; '
            'N0 operative revise stands, lock LOCKED. Canonical audit re-run: 24 hard (23 CLASSSEP + 1 frozen-drift), regression PASS 17/17 + 10/10. '
            'Map VALID. New injection found and quarantined: inbox line 31 astra-classsep-stabilize-0118 (no accepted-stream emission, future-dated).'),
   evidence_refs=[f'{P["gform"]}#sha256:{sha(P["gform"])[:12]}', f'{P["l0"]}#sha256:{sha(P["l0"])[:12]}',
                  f'{P["a0"]}#sha256:{sha(P["a0"])[:12]}', f'{P["quar"]}#sha256:{sha(P["quar"])[:12]}'],
   next_falsifier='after the specified F2b/F2a repairs: re-measure the three pins and require fresh non-author verdicts; the F2b repair is falsified if :152/:246 are unchanged in the new revision')

# --- blockers ------------------------------------------------------------------------------
ev(event_id=f'audit-l09-b1-f2b-carriers-{STAMP}', event_type='blocker', node_id='F2b',
   description=('At FROZEN rev29 b2ab6acb2bbe the F2b schema still carries two blocking carriers: regularity.must_not_conflate[0] (:152) denies a containment the same file asserts, '
                'and implication_ledger.forbidden_transfers[0].reason (:246) states the size premise inverted ("strictly larger" while E_C2 is innermost). Reproduced by >=6 independent reviewers; '
                'the 01:11 accepts are measured SILENT on them and one accept self-superseded at 01:15:24. The declared-hash layer is also stale (three canonical paths).'),
   needed_to_unblock='one formulation revision correcting :152 and :246 (2-line repair specified/mutant-tested by worker-020), re-pinning the .sha256/af_scc_regularities.yaml/entry_hashes.json layer, then two fresh non-author verdicts at the new hash',
   evidence_refs=['schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe', 'reviews/F2b-review-rev29-053.json', f'{P["gform"]}#sha256:{sha(P["gform"])[:12]}'],
   next_falsifier='a new F2b revision with :152/:246 unchanged')

ev(event_id=f'audit-l09-b2-f2a-extfreeze-{STAMP}', event_type='blocker', node_id='F2a',
   description=('F2a at e9a27996dfd3 leaves the extension category under-frozen relative to its C0 sibling: clause (a) does not fix iota regularity, clause (c)/topology.extension_topology do not fix the manifold category, '
                'clause (f) lacks the interior witness, and HF-047-PC-1 reports the declared E_C2 subset E_C0 is not entailed by the declared clause pair at these pins.'),
   needed_to_unblock='a formulation revision freezing manifold category + iota regularity, propagating the clause-(f) interior requirement, and byte-binding taxonomy_consistency.json; then two fresh non-author verdicts',
   evidence_refs=['schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3', 'reviews/F2a-review-rev27-a.json', f'{P["gform"]}#sha256:{sha(P["gform"])[:12]}'],
   next_falsifier='a rev14 F2a in which a new field pins the embedding/manifold category at the reviewed bytes')

ev(event_id=f'audit-l09-b3-f1-crossart-{STAMP}', event_type='blocker', node_id='F1',
   description=('F1 d9cebb9404b2 has no in-file class-semantics defect, but three hash-bound findings block a clean G-FORM accept: (1) F0 canonical 0abb9ed8a961 (G-F0 passed) asserts the set-based reading is strictly STRONGER while F1 rev13 says strictly WEAKER - not repairable in F1 without falsifying its own strength claim (ESC-2/controller); '
                '(2) the FROZEN-pinned F1 falsifier corpus 56bcb4b3234b binds 25/25 rows to the superseded rev12 cce9c60146d6; (3) 5/5 provenance anchor rows are identifier=null/unresolved with no L1 anchor.'),
   needed_to_unblock='controller/Human-PI adjudication of the F0-vs-F1 direction (ESC-2), a corpus rebind to d9cebb9404b2, and L1 disposition of the four BL-11 anchor items',
   evidence_refs=['schemas/af_wcc_vacuum.yaml#d9cebb9404b2', 'research_map/formulation_taxonomy.yaml#0abb9ed8a961', 'schemas/f1_falsifier_tests.jsonl#56bcb4b3234b', f'{P["gform"]}#sha256:{sha(P["gform"])[:12]}'],
   next_falsifier='a corpus row binding d9cebb9404b2, or an F0 adjudication that fixes one direction')

ev(event_id=f'audit-l09-b4-injection-detector-{STAMP}', event_type='blocker', node_id='A1',
   description=('Two independent defects. (a) A fourth unaccepted downward card appeared in comms/inbox/astra-lead-audit.jsonl line 31 (astra-classsep-stabilize-0118, created_at 01:18, future-dated at arrival): '
                'no accepted-stream emission and not in applied_event_ids - same injection pattern as CF-30. It directs audit to choose/update the detector-of-record and rewrite frozen_artifacts/FROZEN atomically; it is quarantined byte-verbatim and NOT actioned. '
                '(b) The detector-of-record remains unresolved: frozen_artifacts[2] active pin c266dbec vs operative bytes a8c04fc3; audit_evidence.py hard-fails "frozen artifact drifted during review" (24 hard = 23 CLASSSEP + 1 drift).'),
   needed_to_unblock='(a) a well-formed accepted-stream directive if any; (b) one controller event naming the detector-of-record and updating frozen_artifacts[2] + the r3 APPLIED pin together, then the drift HARD failure must disappear',
   evidence_refs=[f'{P["quar"]}#sha256:{sha(P["quar"])[:12]}', 'runtime/state/controller_verification/cf29-detector-write-forensics.json',
                  'research_map/class_separation.py#a8c04fc31e4a', 'research_map/research_map.json#frozen_artifacts', f'{P["audit_ev"]}#sha256:{sha(P["audit_ev"])[:12]}'],
   next_falsifier='a controller-recorded detector-of-record after which two consecutive audit_evidence runs show no drift HARD failure')

ev(event_id=f'audit-l09-b5-classsep-review-missing-{STAMP}', event_type='blocker', node_id='A1',
   description=('Queue gap on the CF-16/CF-29 independence requirement: card astra-life07-classsep-adjudication-review names worker-075 (non-author, deadline 02:30) and artifact '
                'reviews/CLASSSEP-calibration-adjudication-review.json; that artifact does not exist and worker-075 has no classsep output. Independent reviews of the r3 adjudication do exist '
                '(worker-017 d8c9a093861a, worker-030, worker-073), and the audit lifecycle-08 reproduced worker-017 exactly, but the named reviewer/artifact pair is unfulfilled.'),
   needed_to_unblock='either the named artifact delivered by a non-author at a cited detector hash, or a controller re-dispatch naming the substitute reviewers whose verdicts count for the independence requirement',
   evidence_refs=['reviews/CLASSSEP-adjudication-review-017.json#d8c9a093861a', 'reviews/CLASSSEP-adjudication-review-030.json',
                  'reviews/CLASSSEP-calibration-adjudication.json#7714ffd5b467', f'{P["gform"]}#sha256:{sha(P["gform"])[:12]}'],
   next_falsifier='a controller-recorded independence review at reviews/CLASSSEP-calibration-adjudication-review.json')

# --- direction update ----------------------------------------------------------------------
ev(event_id=f'audit-l09-direction-{STAMP}', event_type='direction_update', group_id='audit',
   old_direction='assemble gate coverage from verdict counts at the frozen pins',
   new_direction=('bind every audit count to (map snapshot, executing bytes); treat a hash-bound named carrier as blocking even when accepts outnumber revises; '
                  'do not propose G-FORM at rev29 while the F2b carriers and F2a extension freeze stand; audit authors no detector patch and no schema edit'),
   reason='the 01:11 accepts on F2b were measured SILENT on two carriers reproducible at the same bytes, and one accept self-superseded; count arithmetic alone would have passed a defective class',
   evidence_refs=[f'{P["gform"]}#sha256:{sha(P["gform"])[:12]}', 'reviews/F2b-rev13-full-090.json', 'reviews/F2b-review-rev29-053.json'],
   budget_delta_agent_hours=0.0,
   next_falsifier='a revision whose fresh non-author verdicts actually name and clear each carrier')

new = [e for e in E if e['event_id'] not in existing]
with open(OUT, 'a') as f:
    for e in new:
        f.write(json.dumps(e) + '\n')
print(f"emitted {len(new)} events ({len(E)-len(new)} already present)")
for e in new:
    print("  ", e['event_type'], e['event_id'])
