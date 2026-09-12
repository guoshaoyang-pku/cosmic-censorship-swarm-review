#!/usr/bin/env python3
"""Addendum emitter for worker-057 lifecycle 2 (GFORM-SYMDEF-057, rev-12 re-measure).

Emits the checker erratum, the rev-12 report artifact and a closing status, then
writes checkpoint seq 3.  Refuses to re-emit an existing event_id.
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
rev11 = json.load(open(OUT / 'report.json'))
rev12 = json.load(open(OUT / 'report.rev12-cce9c601.json'))


def sh(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()


H = {'rev11': sh(OUT / 'report.json'), 'rev12': sh(OUT / 'report.rev12-cce9c601.json'),
     'checker': sh(OUT / 'check_normative_symbols.py'), 'md12': sh(OUT / 'REPORT.rev12.md')}
in12 = [f"{p}#{v['sha256'][:12]}" for p, v in rev12['measured_inputs'].items()] + \
       [f"{rev12['taxonomy']['path']}#{rev12['taxonomy']['sha256'][:12]}"]
ev = []


def add(e):
    validate_event(e)
    ev.append(e)


add({"event_id": f"w57-symdef-{stamp}-artifact-checker-v2-erratum", "event_type": "artifact", "created_at": ts,
     "actor": "worker-057", "node_id": "F1,F2a,F2b", "artifact_type": "reproducible_checker_corrected",
     "path": "artifacts/worker-057/symdef_check/check_normative_symbols.py", "sha256": H['checker'],
     "validation_status": "unverified", "class_ids": rev12['class_ids'],
     "supersedes": "w57-symdef-20260912T003243-artifact-checker",
     "erratum": ("The superseded checker (sha256 d53d0055b561…) mis-read the rev-12 superscript space notation "
                 "X^r_vac(AF) as a predicate call r_vac(AF), a false positive. The lookbehind now excludes '^'. "
                 "The rev-11 report is unaffected: the triggering byte sequence exists only in rev 12."),
     "evidence_refs": [f"artifacts/worker-057/symdef_check/check_normative_symbols.py#{H['checker'][:12]}",
                       f"schemas/af_wcc_vacuum.yaml:89#cce9c60146d6"],
     "falsifier": "Re-run the checker on rev 12: if r_vac is reported again as a call, or if any control/mutant fails, the correction is falsified."})
add({"event_id": f"w57-symdef-{stamp}-artifact-report-rev12", "event_type": "artifact", "created_at": ts,
     "actor": "worker-057", "node_id": "F1,F2a,F2b", "artifact_type": "symbol_definition_consistency_report_rev12",
     "path": "artifacts/worker-057/symdef_check/report.rev12-cce9c601.json", "sha256": H['rev12'],
     "validation_status": "unverified", "class_ids": rev12['class_ids'],
     "evidence_refs": in12 + [f"artifacts/worker-057/symdef_check/report.rev12-cce9c601.json#{H['rev12'][:12]}"],
     "falsifier": rev12['falsifier']})
add({"event_id": f"w57-symdef-{stamp}-artifact-report-rev12-md", "event_type": "artifact", "created_at": ts,
     "actor": "worker-057", "node_id": "F1,F2a,F2b", "artifact_type": "human_summary_rev12",
     "path": "artifacts/worker-057/symdef_check/REPORT.rev12.md", "sha256": H['md12'],
     "validation_status": "unverified", "class_ids": rev12['class_ids'],
     "evidence_refs": [f"artifacts/worker-057/symdef_check/REPORT.rev12.md#{H['md12'][:12]}"]})

summary = (
    "GFORM-SYMDEF-057 addendum: the canonical schemas moved to rev 12 (F1 cce9c601, F2a 5476a3f2, F2b 55d0a1ea; taxonomy 0abb9ed8) "
    "at 00:31:41, detected as drift during the rev-11 emission. Re-running the fixed checker at rev 12 reproduces every rev-11 finding: "
    "F1 AF_{I+} and P_WCC still have no definition site; F2a/F2b MGHD is still taxonomy-acronym-prose-only; the class-defining predicate "
    "is still defined on the extension tuple and applied to MGHD(D) in both SCC classes. Controls C1/C2 true; mutants 5/5. Checker erratum: "
    "the first rev-12 run produced a false positive on the superscript space notation X^r_vac(AF) (read as r_vac(AF)); the lookbehind now "
    "excludes '^' and the false positive is gone. Worker-local task complete; no gate/node promotion claimed.")
add({"event_id": f"w57-symdef-{stamp}-status-addendum", "event_type": "status", "created_at": ts,
     "actor": "worker-057", "node_id": "F1,F2a,F2b", "status": "active", "hours": 0.1,
     "summary": summary,
     "evidence_refs": [f"artifacts/worker-057/symdef_check/report.rev12-cce9c601.json#{H['rev12'][:12]}",
                       f"artifacts/worker-057/symdef_check/check_normative_symbols.py#{H['checker'][:12]}"] + in12,
     "next_falsifier": rev12['falsifier']})

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

cp = json.load(open('runtime/state/w57_checkpoint_2.json'))
cp3 = {
    "checkpoint_id": f"w57-ckpt-{stamp}", "checkpoint_seq": 3, "actor": "worker-057",
    "instance": cp["instance"], "role": cp["role"],
    "task": dict(cp["task"], revision_followup="re-measured at rev 12 after drift was detected during rev-11 emission"),
    "created_at": ts, "created_at_basis": "wall clock at write time (CF-14 clock discipline)", "hours": 0.4,
    "measured_inputs": rev12['measured_inputs'],
    "taxonomy_sha256": rev12['taxonomy']['sha256'],
    "superseded_inputs_rev11": rev11['measured_inputs'],
    "drift_check": {"rev11_report_bound": {k: v['sha256'][:12] for k, v in rev11['measured_inputs'].items()},
                    "rev12_remeasure_bound": {k: v['sha256'][:12] for k, v in rev12['measured_inputs'].items()},
                    "rev11_drift_recorded_in": "w57-symdef-20260912T003243-artifact-report"},
    "artifacts": [
        {"path": "artifacts/worker-057/symdef_check/report.json", "sha256": H['rev11'],
         "validation_status": "unverified", "binds": "rev 11"},
        {"path": "artifacts/worker-057/symdef_check/report.rev12-cce9c601.json", "sha256": H['rev12'],
         "validation_status": "unverified", "binds": "rev 12", "primary": True},
        {"path": "artifacts/worker-057/symdef_check/check_normative_symbols.py", "sha256": H['checker'],
         "role": "reproducible checker (corrected)", "supersedes_sha256": "d53d0055b561d752fc3e8cf2105b68e7b88b49ab150e252e196a426f12752962"},
        {"path": "artifacts/worker-057/symdef_check/REPORT.md", "sha256": sh(OUT / 'REPORT.md'), "role": "human summary (rev 11)"},
        {"path": "artifacts/worker-057/symdef_check/REPORT.rev12.md", "sha256": H['md12'], "role": "human summary (rev 12)"}],
    "measurements_sha256": {"rev11": rev11['measurements_sha256'], "rev12": rev12['measurements_sha256']},
    "findings_summary": {
        "persist_at_rev12": ["F1 AF_{I+} no definition site", "F1 P_WCC no definition site at rev12",
                             "F2a/F2b MGHD taxonomy-acronym-prose-only", "F2a/F2b predicate argument role"],
        "rev11_only": [], "new_at_rev12": [],
        "false_positive_corrected": "r_vac (superscript space notation X^r_vac(AF) mis-read as a call in the first rev-12 run)"},
    "events_emitted": {"path": "comms/outbox/worker-057.jsonl", "rev11_event_ids": cp["events_emitted"]["event_ids"],
                       "addendum_event_ids": [e['event_id'] for e in ev],
                       "authority_note": "worker events cannot set status=done, validation_status=passed, or a gate verdict"},
    "falsifier": rev12['falsifier'],
    "next_step": cp["next_step"],
    "blockers_open": cp["blockers_open"],
    "kill_or_recycle": "task complete at two revisions; worker slot can be recycled. No further resource requested."}
(Path('runtime/state') / 'w57_checkpoint_3.json').write_text(json.dumps(cp3, indent=1) + "\n")
with open('runtime/state/w57_checkpoints.jsonl', 'a') as f:
    f.write(json.dumps({k: cp3[k] for k in ('checkpoint_id', 'checkpoint_seq', 'actor', 'created_at', 'hours', 'task',
                                            'findings_summary', 'blockers_open')}) + "\n")
print("emitted addendum events:", [e['event_id'] for e in ev])
print("rev12 report", H['rev12'], "| checker", H['checker'])
print("checkpoint runtime/state/w57_checkpoint_3.json")
