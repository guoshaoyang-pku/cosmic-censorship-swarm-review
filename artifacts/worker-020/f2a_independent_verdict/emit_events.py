#!/usr/bin/env python3
"""Emit worker-020's hash-bound outbox events for W020-F2A-INDEP-VERDICT-01.

Messages are appended to comms/outbox/worker-020.jsonl (the writer is this agent).
Every artifact event carries path + sha256 + validation_status; every evidence_ref is
`path#sha256-prefix`. Worker events do not set gate verdicts or node status=done.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUTBOX = ROOT / "comms/outbox/worker-020.jsonl"
CST = _dt.timezone(_dt.timedelta(hours=8))
TASK = "W020-F2A-INDEP-VERDICT-01"
CLASS = "AF-SCC-C2-VAC-GEN"
NODE = "F2a"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def h12(s: str) -> str:
    return s[:12]


def stamp(offset: int) -> str:
    return (_dt.datetime.now(CST) + _dt.timedelta(seconds=offset)).isoformat(timespec="seconds")


TARGET = ROOT / "schemas/af_scc_c2_vacuum.yaml"
F0 = ROOT / "research_map/formulation_taxonomy.yaml"
F0_AUT = ROOT / "artifacts/formulation/formulation_taxonomy.yaml"
EV = HERE / "f2a_independent_verdict.json"
MD = HERE / "f2a_independent_verdict.md"
SCRIPT = HERE / "verify_f2a_independent.py"
GATE_F = HERE / "gate_f2a_snapshot.json"
CS_F = HERE / "classsep_f2a_snapshot.json"
TL_F = HERE / "drift_timeline.json"
SNAP_T = HERE / "snapshots/f2a_b6123750b37d.yaml"
SNAP_F0 = HERE / "snapshots/f0_taxonomy_276009f4f63d.yaml"

live_target = sha(TARGET)
live_f0 = sha(F0)
ev = json.loads(EV.read_text())
target_sha = ev["t0_target_sha256"]
f0_sha = ev["drift"]["t0_f0_sha256"]
binding_current = live_target == target_sha
assert sha(SNAP_T) == target_sha, "snapshot drift"
assert sha(SNAP_F0) == f0_sha, "F0 snapshot drift"

rows: list[dict] = []


def add(kind: str, offset: int, slug: str | None = None, **kw):
    row = {"event_id": f"w020-{_dt.datetime.now(CST).strftime('%Y%m%dT%H%M')}-f2a-{slug or kind}",
           "event_type": kind, "created_at": stamp(offset), "actor": "worker-020",
           "assignment": TASK, "node_id": NODE, "class_id": CLASS}
    row.update(kw)
    rows.append(row)


# 1. task claim / status
add("status", 0, slug="status-claim", status="active", hours=0.4,
    summary=(f"Worker-020 took bounded class-bound task {TASK}: independent verification of the canonical "
             f"F2a schema {TARGET.name} at frozen sha256 {h12(target_sha)} (bytes preserved at "
             f"{SNAP_T.relative_to(ROOT)}), with the declared F0 artifact {F0.name} frozen at {h12(f0_sha)}. "
             f"Ran the canonical structural gate and the class-separation detector on the frozen bytes, plus 17 "
             f"independent checks. Verdict: revise (score 2) on hard failure C15 (class_contract_pointer does not "
             f"resolve in the declared canonical F0). Target was unchanged across a 7-sample, ~30s settle window."),
    evidence_refs=[f"schemas/af_scc_c2_vacuum.yaml#{h12(target_sha)}",
                   f"research_map/formulation_taxonomy.yaml#{h12(f0_sha)}",
                   f"{EV.relative_to(ROOT)}#{h12(sha(EV))}"],
    next_falsifier=("a re-measurement of schemas/af_scc_c2_vacuum.yaml showing a hash different from "
                    f"{h12(target_sha)} (verdict void), or a run of the same checks at a later revision that "
                    "returns accept, superseding this revise"))

# 2-9 artifacts
artifacts = [
    (SCRIPT, "art-script", "verification_script", "unverified",
     "frozen verification script; re-runnable, no model calls, writes only under artifacts/worker-020/"),
    (SNAP_T, "art-snapshot", "frozen_snapshot", "unverified",
     "byte-identical copy of the reviewed canonical F2a at the frozen sha256"),
    (SNAP_F0, "art-snapshot-f0", "frozen_snapshot", "unverified",
     "byte-identical copy of the declared canonical F0 taxonomy at the frozen sha256"),
    (EV, "art-evidence", "review_evidence", "unverified",
     "machine evidence record: gate run, class-separation run, checks C01-C17, drift window"),
    (MD, "art-report", "review_evidence", "unverified", "human-readable verdict summary"),
    (GATE_F, "art-gate", "gate_run_output", "unverified",
     "canonical gate report on the frozen snapshot (exit 0, verdict pass)"),
    (CS_F, "art-classsep", "detector_run_output", "unverified",
     "class-separation findings on the frozen snapshot (0 hard, 0 soft; detector regression PASS)"),
    (TL_F, "art-timeline", "drift_sample", "unverified",
     "hash samples for target, siblings and F0 taken before/after the settle window"),
]
for i, (p, slug, atype, vstatus, note) in enumerate(artifacts, start=3):
    add("artifact", i, slug=slug, artifact_type=atype, path=str(p.relative_to(ROOT)), sha256=sha(p),
        validation_status=vstatus, bytes=p.stat().st_size, note=note,
        evidence_refs=[f"{p.relative_to(ROOT)}#{h12(sha(p))}"])

# 10. review verdict
hard = ev["hard_failures"]
findings = [
    {"id": "C15", "severity": "hard",
     "statement": ("class_contract_pointer 'artifacts/formulation/formulation_taxonomy.yaml"
                   "#class_contracts.AF-SCC-C2-VAC-GEN' does not resolve against the declared canonical F0 "
                   f"artifact research_map/formulation_taxonomy.yaml#{h12(f0_sha)} (no 'class_contracts' key; "
                   "canonical carries classes.AF-SCC-C2-VAC-GEN). It resolves only in the authoring tree "
                   f"artifacts/formulation/formulation_taxonomy.yaml#{h12(sha(F0_AUT))}, which is byte-divergent "
                   "from canonical and is not authoritative under the controller canonical-path policy."),
     "evidence_refs": [f"schemas/af_scc_c2_vacuum.yaml#{h12(target_sha)}:36",
                       f"research_map/formulation_taxonomy.yaml#{h12(f0_sha)}",
                       f"{EV.relative_to(ROOT)}#{h12(sha(EV))}"]},
    {"id": "C13", "severity": "soft",
     "statement": "pointer target path is the authoring tree, not the canonical path (policy violation if it stays)",
     "evidence_refs": [f"{EV.relative_to(ROOT)}#{h12(sha(EV))}"]},
    {"id": "C14", "severity": "soft",
     "statement": ("7 duplicate YAML mapping keys 'revised_at' (lines 10,12,14,16,18,21,23): strict YAML 1.2 "
                   "parsers reject the file; PyYAML silently keeps the last value"),
     "evidence_refs": [f"{SNAP_T.relative_to(ROOT)}#{h12(target_sha)}"]},
    {"id": "C16", "severity": "soft",
     "statement": ("consistency_evidence artifacts/formulation/evidence/taxonomy_consistency.json records no input "
                   "sha256, so the 'CONSISTENT' claim cannot be bound to the declared F0 hash"),
     "evidence_refs": ["artifacts/formulation/evidence/taxonomy_consistency.json"]},
    {"id": "C17", "severity": "soft",
     "statement": (f"F0 canonical {h12(f0_sha)} and authoring {h12(sha(F0_AUT))} are byte-divergent, so the "
                   "publication pair cannot yet anchor a review verdict"),
     "evidence_refs": [f"research_map/formulation_taxonomy.yaml#{h12(f0_sha)}",
                       f"artifacts/formulation/formulation_taxonomy.yaml#{h12(sha(F0_AUT))}"]},
    {"id": "P01", "severity": "positive",
     "statement": ("canonical gate sha 000e09e46b2f exits 0 (verdict pass, failed_rules []) and class-separation "
                   "sha c266dbceca87 reports 0 hard / 0 soft findings on the frozen snapshot; checks C01-C12 pass"),
     "evidence_refs": [f"{GATE_F.relative_to(ROOT)}#{h12(sha(GATE_F))}",
                       f"{CS_F.relative_to(ROOT)}#{h12(sha(CS_F))}"]},
]
add("review", 11, target_id="F2a", reviewer="worker-020", verdict="revise", score=2,
    hard_failures=hard, findings=findings,
    reviewed_sha256=target_sha, class_id=CLASS, gate="G-FORM",
    binding_current_at_emit=binding_current, live_target_sha256_at_emit=live_target,
    falsifier=("a canonical F2a revision whose class_contract_pointer resolves at "
               f"research_map/formulation_taxonomy.yaml#classes.{CLASS} (or a byte-identical publication making "
               "the authoring contract canonical), reviewed at its own measured hash"),
    evidence_refs=[f"schemas/af_scc_c2_vacuum.yaml#{h12(target_sha)}",
                   f"{EV.relative_to(ROOT)}#{h12(sha(EV))}",
                   f"{MD.relative_to(ROOT)}#{h12(sha(MD))}"],
    does_not_claim=["gate verdict", "node completion", "schema truth"])

# 11. blocker
add("blocker", 12,
    description=("F2a class-binding evidence chain is unresolvable against the declared canonical F0: "
                 f"schemas/af_scc_c2_vacuum.yaml#{h12(target_sha)} line 36 points at "
                 "artifacts/formulation/formulation_taxonomy.yaml#class_contracts.AF-SCC-C2-VAC-GEN, but the "
                 f"declared canonical research_map/formulation_taxonomy.yaml#{h12(f0_sha)} has no class_contracts "
                 f"key (it uses classes.{CLASS}), and the authoring tree is byte-divergent "
                 f"({h12(sha(F0_AUT))}) and non-authoritative. The canonical gate passes because it does not "
                 "check pointer resolvability; two independent accepts at this hash would therefore bind to a "
                 "contract that a reviewer cannot reach from the canonical artifact."),
    needed_to_unblock=("lead-formulation either (a) repoints class_contract_pointer to "
                       f"research_map/formulation_taxonomy.yaml#classes.{CLASS} and re-emits the artifact with a "
                       "new sha256, or (b) publishes the authoring contract tree byte-identically to canonical "
                       "(same sha256) so the pointer resolves; then re-run the consistency check with recorded "
                       "input hashes and re-review at the new hash."),
    evidence_refs=[f"schemas/af_scc_c2_vacuum.yaml#{h12(target_sha)}",
                   f"research_map/formulation_taxonomy.yaml#{h12(f0_sha)}",
                   f"artifacts/formulation/formulation_taxonomy.yaml#{h12(sha(F0_AUT))}",
                   f"{EV.relative_to(ROOT)}#{h12(sha(EV))}"],
    falsifier=("a canonical F0 revision that contains class_contracts.AF-SCC-C2-VAC-GEN, or a repointed F2a whose "
               "pointer resolves at the canonical path; either makes this blocker stale and re-reviewable"),
    does_not_claim=["gate verdict", "node completion"])

# 12. checkpoint / completion claim
add("status", 13, slug="status-checkpoint", status="active", hours=0.6,
    summary=(f"COMPLETION CLAIM (worker may not set done). {TASK} finished at worker level: verdict revise/2 with "
             f"hard failure C15 + 4 soft findings + 1 positive control, all hash-bound. Reviewed hash "
             f"{h12(target_sha)}; live hash at emit {h12(live_target)} (binding_current={binding_current}). "
             f"Evidence {EV.relative_to(ROOT)}#{h12(sha(EV))}. A checkpoint snapshot is taken next by "
             "research_map/checkpoint.py. No gate verdict, no node completion, no theorem."),
    evidence_refs=[f"{EV.relative_to(ROOT)}#{h12(sha(EV))}",
                   f"{MD.relative_to(ROOT)}#{h12(sha(MD))}",
                   f"{TL_F.relative_to(ROOT)}#{h12(sha(TL_F))}"],
    next_falsifier=("controller re-measure of schemas/af_scc_c2_vacuum.yaml differs from "
                    f"{h12(target_sha)}; or a new F2a revision fixes C15 and a re-run of "
                    f"{SCRIPT.name} returns accept at the new hash; or the checkpoint's classsep_regression "
                    "verdict is not PASS."),
    does_not_claim=["gate verdict", "node completion", "schema truth"])

OUTBOX.parent.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

seen_ids = set()
for r in rows:
    validate_event(r)
    assert r["event_id"] not in seen_ids, f"duplicate event_id {r['event_id']}"
    seen_ids.add(r["event_id"])

with OUTBOX.open("a") as f:
    for r in rows:
        f.write(json.dumps(r, sort_keys=True) + "\n")

print(json.dumps({"outbox": str(OUTBOX.relative_to(ROOT)), "events": len(rows),
                  "outbox_sha256": sha(OUTBOX),
                  "review_verdict": "revise", "reviewed_sha256": target_sha,
                  "binding_current": binding_current}, indent=2))
