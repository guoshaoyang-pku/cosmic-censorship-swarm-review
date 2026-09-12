#!/usr/bin/env python3
"""One-shot emitter for worker-057 lifecycle 2 (GFORM-SYMDEF-057).

Writes validated JSONL events to comms/outbox/worker-057.jsonl and the
checkpoint to runtime/state/w57_checkpoint_2.json + w57_checkpoints.jsonl.
Idempotence guard: refuses to re-emit if any event_id already exists.
"""
import json, hashlib, sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, 'research_map')
from schemas import validate_event

CST = timezone(timedelta(hours=8))
now = datetime.now(CST)
ts = now.isoformat()
stamp = now.strftime('%Y%m%dT%H%M%S')
OUT = Path('artifacts/worker-057/symdef_check')
rep = json.load(open(OUT / 'report.json'))


def sh(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()


drift = {}
for p, v in rep['measured_inputs'].items():
    cur = sh(p)
    if cur != v['sha256']:
        drift[p] = {'report': v['sha256'][:12], 'now': cur[:12]}
tax = rep['taxonomy']['path']
if sh(tax) != rep['taxonomy']['sha256']:
    drift[tax] = {'report': rep['taxonomy']['sha256'][:12], 'now': sh(tax)[:12]}

H = {'report': sh(OUT / 'report.json'), 'checker': sh(OUT / 'check_normative_symbols.py'),
     'md': sh(OUT / 'REPORT.md')}
inputs_ref = [f"{p}#{v['sha256'][:12]}" for p, v in rep['measured_inputs'].items()]
ev = []


def add(e):
    validate_event(e)
    ev.append(e)


add({"event_id": f"w57-symdef-{stamp}-artifact-report", "event_type": "artifact", "created_at": ts,
     "actor": "worker-057", "node_id": "F1,F2a,F2b",
     "artifact_type": "symbol_definition_consistency_report",
     "path": "artifacts/worker-057/symdef_check/report.json", "sha256": H['report'],
     "validation_status": "unverified", "class_ids": rep['class_ids'],
     "evidence_refs": inputs_ref + [f"artifacts/worker-057/symdef_check/report.json#{H['report'][:12]}"],
     "drift_check": {"measured_at": ts, "drift": drift or "clean"},
     "falsifier": rep['falsifier']})
add({"event_id": f"w57-symdef-{stamp}-artifact-checker", "event_type": "artifact", "created_at": ts,
     "actor": "worker-057", "node_id": "F1,F2a,F2b", "artifact_type": "reproducible_checker",
     "path": "artifacts/worker-057/symdef_check/check_normative_symbols.py", "sha256": H['checker'],
     "validation_status": "unverified", "class_ids": rep['class_ids'],
     "evidence_refs": [f"artifacts/worker-057/symdef_check/check_normative_symbols.py#{H['checker'][:12]}"],
     "falsifier": "Re-run on the pinned hashes: any change in the per-symbol classification or binder sets, or a control/mutant failure, falsifies the checker."})
add({"event_id": f"w57-symdef-{stamp}-artifact-reportmd", "event_type": "artifact", "created_at": ts,
     "actor": "worker-057", "node_id": "F1,F2a,F2b", "artifact_type": "human_summary",
     "path": "artifacts/worker-057/symdef_check/REPORT.md", "sha256": H['md'],
     "validation_status": "unverified", "class_ids": rep['class_ids'],
     "evidence_refs": [f"artifacts/worker-057/symdef_check/REPORT.md#{H['md'][:12]}"],
     "falsifier": "Falsified together with report.json; the markdown is a rendering of the measured report."})

summary = (
    "GFORM-SYMDEF-057 applied the same definition-site rule that produced F1's dangling-symbol hard failure "
    "(AF_{I+}) across F1/F2a/F2b at rev-11 hashes (F1 9a8bd4c96800, F2a b6123750b37d, F2b 1bb78ce9b357; "
    f"taxonomy 276009f4f63d; drift={drift or 'clean'}). Uniformity: F1 local {{visible_singularity_from_I_plus}}, "
    "file-prose {complete}, no-definition-site {AF_{I+}, P_WCC}; F2a/F2b local {proper_future_extension_in_class}, "
    "taxonomy-acronym-prose-only {MGHD}, no-definition-site {}. NEW relative to the review corpus: P_WCC is used by "
    "F1 quantifiers.negation_normal_form and defined nowhere in file or taxonomy; MGHD is used by both SCC normative "
    "sites with only a prose acronym expansion in the canonical taxonomy; the class-defining predicate is defined on "
    "the extension tuple (M',g',iota) but applied to MGHD(D) in both SCC classes. Controls C1/C2 true, mutants 5/5. "
    "Worker-local task complete; no gate/node promotion claimed.")
add({"event_id": f"w57-symdef-{stamp}-status-checkpoint", "event_type": "status", "created_at": ts,
     "actor": "worker-057", "node_id": "F1,F2a,F2b", "status": "active", "hours": 0.25,
     "summary": summary,
     "evidence_refs": [f"artifacts/worker-057/symdef_check/report.json#{H['report'][:12]}"] + inputs_ref,
     "next_falsifier": rep['falsifier']})

claim_stmt = (
    "At canonical rev-11 hashes schemas/af_wcc_vacuum.yaml#9a8bd4c96800, schemas/af_scc_c2_vacuum.yaml#b6123750b37d, "
    "schemas/af_scc_c0_vacuum.yaml#1bb78ce9b357 and canonical taxonomy research_map/formulation_taxonomy.yaml#276009f4f63d, "
    "one definition-site rule classifies the symbols used in the normative sites as follows: F1 conclusion.statement_formal "
    "uses visible_singularity_from_I_plus (local definition), AF_{I+} (no definition site in file or taxonomy) and complete "
    "(file-prose definition at i_plus.completeness_definition); F1 quantifiers.negation_normal_form uses P_WCC (no definition "
    "site anywhere); F2a and F2b conclusion.statement_formal and quantifiers.negation_normal_form use MGHD (taxonomy acronym/prose "
    "only, no definition_ref) and proper_future_extension_in_class (local definition on the extension tuple (M',g',iota) of (M,g), "
    "applied to MGHD(D) with no extension-tuple argument). Binder realization: all three statements realize D, which is not one of "
    "the quantifiers.ordered binder names. This is a statement about schema well-formedness at pinned hashes, not a mathematical "
    "claim about cosmic censorship.")
add({"event_id": f"w57-symdef-{stamp}-claim-uniformity", "event_type": "claim", "created_at": ts,
     "actor": "worker-057", "node_id": "F1,F2a,F2b",
     "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
     "statement": claim_stmt, "conclusion_type": "formal_model",
     "assumptions": ["the three canonical files and the canonical taxonomy are the measured hashes recorded in evidence_refs",
                     "a symbol is 'defined' when it has a name/predicate_name+definition leaf, a definition-style file key naming it, or a bound binder; taxonomy prose mention alone is recorded as a weaker class",
                     "no semantic correctness of the class statements is assumed or decided"],
     "falsifier": rep['falsifier'],
     "evidence_refs": [f"artifacts/worker-057/symdef_check/report.json#{H['report'][:12]}"] + inputs_ref + [f"{tax}#{rep['taxonomy']['sha256'][:12]}"],
     "artifact_refs": [f"artifacts/worker-057/symdef_check/report.json#{H['report'][:12]}"]})

add({"event_id": f"w57-symdef-{stamp}-blocker-symbols", "event_type": "blocker", "created_at": ts,
     "actor": "worker-057", "node_id": "F1,F2a,F2b",
     "description": (
         "Normative statements use symbols with no definition site under the rule already applied to F1 (HF-06): F1 "
         "quantifiers.negation_normal_form uses P_WCC(D) (nowhere in the file or the canonical taxonomy); F2a/F2b use MGHD(D) "
         "in conclusion.statement_formal and quantifiers.negation_normal_form (taxonomy line 171 expands the acronym in prose "
         "only, no definition_ref). Either the F2a/F2b statements carry the same defect as F1's AF_{I+}, or the dangling-symbol "
         "policy must be recorded as taxonomy-prose-definition-sufficient and F1's hard failure re-adjudicated; the two cannot "
         "both stand at these hashes."),
     "needed_to_unblock": (
         "lead-formulation publishes a symbols/definitions block or definition_ref for P_WCC and MGHD (or records the uniform "
         "policy that taxonomy prose expansion counts as a definition site); then re-run "
         "artifacts/worker-057/symdef_check/check_normative_symbols.py at the new hash and confirm no_definition_site is empty "
         "(or that the recorded policy names each accepted prose-only symbol)."),
     "evidence_refs": ["schemas/af_wcc_vacuum.yaml:89#9a8bd4c96800", "schemas/af_scc_c2_vacuum.yaml:218#b6123750b37d",
                       "schemas/af_scc_c0_vacuum.yaml:220#1bb78ce9b357", "research_map/formulation_taxonomy.yaml:171#276009f4f63d",
                       f"artifacts/worker-057/symdef_check/report.json#{H['report'][:12]}"]})

add({"event_id": f"w57-symdef-{stamp}-blocker-predicate-role", "event_type": "blocker", "created_at": ts,
     "actor": "worker-057", "node_id": "F2a,F2b",
     "description": (
         "The class-defining predicate proper_future_extension_in_class is defined in both SCC schemas as a relation on the "
         "extension tuple (M',g',iota) of (M,g) (definition clauses (a)-(f), extension_predicate.name/definition), but "
         "conclusion.statement_formal applies it to the single argument MGHD(D), the development of the data; neither the "
         "extension tuple nor the D3 not_exists binder (M',g',iota) appears as an argument, so the negated extension existential "
         "is implicit at the use site. Under the G-FORM 'exact quantifiers' criterion this is the same abbreviation class as the "
         "F1 statement_formal abbreviation already recorded by worker-057 lifecycle 1 (HF-A2)."),
     "needed_to_unblock": (
         "lead-formulation or the G-FORM reviewer records an abbreviation rule (the predicate absorbs the negated D3 extension "
         "existential) at a named revision, or expands statement_formal so the extension tuple appears explicitly; then re-run "
         "the checker and expect the predicate_argument_role finding to clear."),
     "evidence_refs": ["schemas/af_scc_c2_vacuum.yaml:218#b6123750b37d", "schemas/af_scc_c0_vacuum.yaml:220#1bb78ce9b357",
                       f"artifacts/worker-057/symdef_check/report.json#{H['report'][:12]}"]})

add({"event_id": f"w57-symdef-{stamp}-status-complete", "event_type": "status", "created_at": ts,
     "actor": "worker-057", "node_id": "F1,F2a,F2b", "status": "active", "hours": 0.3,
     "summary": "One class-bound task complete (worker-local): GFORM-SYMDEF-057 artifact, claim and two blockers emitted; "
                "6 major + 3 info findings at rev-11 hashes; drift check clean. No gate verdict, no validation_status=passed, "
                "no node status=done claimed; controller/lead adjudication required. Worker slot can be recycled.",
     "evidence_refs": [f"artifacts/worker-057/symdef_check/report.json#{H['report'][:12]}"],
     "next_falsifier": rep['falsifier']})

existing = set(json.load(open('runtime/state/ingested_ids.json')))
for p in Path('comms/outbox').glob('*.jsonl'):
    for line in open(p):
        line = line.strip()
        if not line:
            continue
        try:
            existing.add(json.loads(line).get('event_id'))
        except Exception:
            pass
coll = [e['event_id'] for e in ev if e['event_id'] in existing]
assert not coll, f"collision {coll}"

with open('comms/outbox/worker-057.jsonl', 'a') as f:
    for e in ev:
        f.write(json.dumps(e) + "\n")

cp = {
    "checkpoint_id": f"w57-ckpt-{stamp}", "checkpoint_seq": 2, "actor": "worker-057",
    "instance": "session worker-57 (supervisor instance dir not found under runtime/instances)",
    "role": "bounded execution worker",
    "task": {"task_id": "GFORM-SYMDEF-057",
             "title": "Normative-symbol definition consistency across F1/F2a/F2b at rev-11 canonical hashes",
             "gate": "G-FORM", "node_ids": ["F1", "F2a", "F2b"],
             "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
             "bound": "one task, one artifact set; no gate verdict, no write outside artifacts/worker-057/, comms/outbox/worker-057.jsonl and runtime/state/w57_*"},
    "created_at": ts, "created_at_basis": "wall clock at write time (CF-14 clock discipline)", "hours": 0.3,
    "measured_inputs": rep['measured_inputs'], "taxonomy_sha256": rep['taxonomy']['sha256'],
    "drift_check": drift or "clean",
    "artifacts": [
        {"path": "artifacts/worker-057/symdef_check/report.json", "sha256": H['report'],
         "bytes": (OUT / 'report.json').stat().st_size, "validation_status": "unverified", "primary": True},
        {"path": "artifacts/worker-057/symdef_check/check_normative_symbols.py", "sha256": H['checker'], "role": "reproducible checker"},
        {"path": "artifacts/worker-057/symdef_check/REPORT.md", "sha256": H['md'], "role": "human summary"}],
    "measurements_sha256": rep['measurements_sha256'],
    "findings_summary": {"major": rep['major_finding_count'], "info": len(rep['findings']) - rep['major_finding_count'],
                         "new_candidates": ["F1 P_WCC undefined in quantifiers.negation_normal_form",
                                            "F2a/F2b MGHD acronym-prose-only in both normative sites",
                                            "F2a/F2b extension predicate argument role (defined on extension tuple, applied to MGHD(D))"],
                         "known_overlap": ["F1 AF_{I+} (HF-06 / HF090-03)",
                                           "F1 complete prose-only at i_plus.completeness_definition"]},
    "events_emitted": {"path": "comms/outbox/worker-057.jsonl", "event_ids": [e['event_id'] for e in ev],
                       "authority_note": "worker events cannot set status=done, validation_status=passed, or a gate verdict"},
    "falsifier": rep['falsifier'],
    "next_step": "lead-formulation/reviewer: adjudicate the dangling-symbol policy uniformly (P_WCC, MGHD) and the predicate argument-role abbreviation; re-run the checker at the next revision.",
    "blockers_open": [f"w57-symdef-{stamp}-blocker-symbols", f"w57-symdef-{stamp}-blocker-predicate-role"],
    "kill_or_recycle": "task complete; worker slot can be recycled. No further resource requested."}
(Path('runtime/state') / 'w57_checkpoint_2.json').write_text(json.dumps(cp, indent=1) + "\n")
with open('runtime/state/w57_checkpoints.jsonl', 'a') as f:
    f.write(json.dumps({k: cp[k] for k in ('checkpoint_id', 'checkpoint_seq', 'actor', 'created_at', 'hours', 'task',
                                           'findings_summary', 'blockers_open')}) + "\n")

print("emitted", len(ev), "events")
for e in ev:
    print(' ', e['event_type'], e['event_id'])
print("report", H['report'])
print("checkpoint runtime/state/w57_checkpoint_2.json")
