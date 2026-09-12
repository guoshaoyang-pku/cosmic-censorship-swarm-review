#!/usr/bin/env python3
"""Emit the W003 worker lifecycle to comms/outbox/worker-003.jsonl and write the checkpoint.

Order: status(open) -> 5x artifact -> claim -> review -> blocker -> status(complete)
-> checkpoint json + jsonl -> status(checkpoint). Every event carries event_id, event_type,
created_at, actor, class/node/gate/task, hash-prefixed evidence refs and a falsifier.
Read-only on canonical paths; writes only the outbox append, the checkpoint files and SHA256SUMS.
"""
import datetime
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
OUTBOX = REPO / "comms/outbox/worker-003.jsonl"
STATE = REPO / "runtime/state"
DELIVERABLES = [
    "report.json",
    "probe_stdout.txt",
    "verify_f2b_rev14_candidate.py",
    "README.md",
    "emit_events.py",
    "pinned/sandbox_pristine_manifest.txt",
]
TASK = "W003-F2B-REV14-CANDIDATE-INDEPENDENT-CLOSURE-01"
CLASS = "AF-SCC-C0-VAC-GEN"
NODE = "F2b"
GATE = "G-FORM"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def ref(p, full=False):
    h = sha(REPO / p if not str(p).startswith("/") else p)
    return f"{p}#{h if full else h[:12]}"


def now():
    return datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()


def event(seq, etype, **kw):
    eid = f"w003-{STAMP}-{seq:02d}-{etype}"
    e = {"event_id": eid, "event_type": etype, "created_at": now(), "actor": "worker-003",
         "class_id": CLASS, "class_ids": [CLASS], "node_id": NODE, "gate": GATE, "task_id": TASK}
    e.update(kw)
    return e


STAMP = datetime.datetime.now().astimezone().strftime("%Y%m%dT%H%M%S")
report = json.loads((ROOT / "report.json").read_text())
hashes = {d: sha(ROOT / d) for d in DELIVERABLES}
events = []

cand = "artifacts/worker-044/f2b_live_closure_01/closure_summary.json"
cand_ref = ref(cand, full=True)
rep_ref = ref("artifacts/worker-003/f2b_rev14_candidate_closure/report.json")
probe_ref = ref("artifacts/worker-003/f2b_rev14_candidate_closure/probe_stdout.txt")
script_ref = ref("artifacts/worker-003/f2b_rev14_candidate_closure/verify_f2b_rev14_candidate.py")
readme_ref = ref("artifacts/worker-003/f2b_rev14_candidate_closure/README.md")
manifest_ref = ref("artifacts/worker-003/f2b_rev14_candidate_closure/pinned/sandbox_pristine_manifest.txt")
c0_ref = "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe"
frozen_ref = "artifacts/formulation/FROZEN.json#815e08079aef"
f0_ref = "research_map/formulation_taxonomy.yaml#0abb9ed8a961"

events.append(event(1, "status", status="active", hours=0.5,
    summary=("No card exists for worker-003; took ONE bounded class-bound task: independent non-author "
             "closure verification of the worker-044 composed F2b rev14 candidate (C0 48cadb72, evidence "
             "675a99d0, FROZEN a57492cc, aggregator 601355e7) against the five recorded blocking families "
             "H1/H2/A2/A6/SEP-6 at the live rev13 / FROZEN rev29 base."),
    evidence_refs=[cand_ref, c0_ref, frozen_ref, f0_ref],
    next_falsifier=("Re-run verify_f2b_rev14_candidate.py after any owner revision: B1/B2 must stay closed, "
                    "the declared evidence hash must become a writer fixpoint, check_variant_deltas must "
                    "return VALID, and the FROZEN revision label must be unique.")))

artifacts = [
    ("report.json", "closure_verification_report", rep_ref),
    ("probe_stdout.txt", "probe_output", probe_ref),
    ("verify_f2b_rev14_candidate.py", "independent_verifier", script_ref),
    ("README.md", "task_summary", readme_ref),
    ("pinned/sandbox_pristine_manifest.txt", "pinned_candidate_tree_manifest", manifest_ref),
]
for i, (name, atype, r) in enumerate(artifacts, start=2):
    events.append(event(i, "artifact", artifact_type=atype,
        path=f"artifacts/worker-003/f2b_rev14_candidate_closure/{name}",
        sha256=hashes[name], validation_status="unverified", evidence_refs=[r]))

events.append(event(7, "claim", conclusion_type="formal_model",
    statement=("At the candidate bytes (C0 48cadb72 canonical==authoring, C2 d94d490d, F1 88871f8f, evidence "
               "675a99d0, FROZEN a57492cc rev29, KEY_MANIFEST 61b9d8c1, aggregator 601355e7) measured "
               "2026-09-12T01:12+08:00 against the live base (C0 b2ab6acb, FROZEN 815e0807 rev29, F0 "
               "0abb9ed8), the five families measure H1 pass, H2 pass, A6 pass, SEP-6 pass, A2 content pass / "
               "durability FAIL. Two candidate-level hard failures: (H1) the declared self-verifying evidence "
               "doc is not a fixpoint of the candidate's own pinned writer cde1a165, whose write path emits "
               "9e335e9b without map_taxonomy_sha256/lead_contract_sha256/measured_at; (H2) moving F1/C0 to "
               "rev14 without re-basing the variant deltas leaves check_variant_deltas INVALID (CH b2ab6acb -> "
               "48cadb72, SET d9cebb94 -> 88871f8f) and the FROZEN-pinned variant_delta_check.json fc6ee058 "
               "is not reproducible (candidate emits aa183716). 12/16 checks pass, 7/7 planted controls "
               "discriminate, 50/50 candidate FROZEN pins resolve, all three check_class_schema runs rc 0, "
               "verify_frozen rc 0. This is an artifact-and-checker measurement, not a mathematics claim."),
    assumptions=["candidate sandbox bytes are as declared by the author closure summary 7bd2b25cd6fa",
                 "the project's pinned checkers are the acceptance instruments",
                 "live drift after the snapshot voids live applicability, not the snapshot measurement"],
    falsifier=report["falsifier"],
    evidence_refs=[rep_ref, probe_ref, script_ref, cand_ref, c0_ref, frozen_ref],
    artifact_refs=[rep_ref, probe_ref, script_ref, readme_ref, manifest_ref]))

events.append(event(8, "review", target_id=(cand + "#7bd2b25cd6fa (composed F2b rev14 candidate, "
                                             "C0 48cadb72e507)"),
    reviewer="worker-003", verdict="revise", score=3.5,
    hard_failures=["W003-F2B14-H1", "W003-F2B14-H2"],
    findings=[f"{f['id']} ({f['severity']}): {f['detail'][:220]}" for f in report["findings"]] +
             [f"{k}: {v}" for k, v in report["family_notes"].items()],
    evidence_refs=[rep_ref, probe_ref, script_ref, cand_ref, c0_ref, frozen_ref],
    falsifier=report["falsifier"]))

events.append(event(9, "blocker",
    description=("The worker-044 composed F2b rev14 candidate is NOT acceptance-ready as one atomic revision. "
                 "(H1) A2 durability: the declared evidence doc 675a99d0 is not reproducible by any pinned "
                 "deterministic writer (guarded writer computes 9e335e9b; close_findings_rev27.py stamps "
                 "measured_at=now). (H2) The two variant deltas are not re-based to the candidate schemas "
                 "(check_variant_deltas INVALID; FROZEN-pinned variant_delta_check.json fc6ee058 not "
                 "reproducible). Publication notes N1-N4 also stand."),
    needed_to_unblock=("Formulation lead (owner): in ONE atomic revision (i) make a pinned writer emit the "
                       "enriched evidence doc deterministically and re-pin it; (ii) re-base both variant deltas "
                       "and re-run check_variant_deltas/check_variant_registry; (iii) publish FROZEN under the "
                       "next free revision; (iv) reconcile the aggregator re-pin against the live "
                       "af_scc_regularities.yaml, which moved to 27255e5b at 01:11:13. No write to canonical "
                       "bytes was made by this worker."),
    evidence_refs=[rep_ref, probe_ref, c0_ref, frozen_ref, cand_ref],
    falsifier=("A re-run at the same pins with a deterministic enriched writer and re-based deltas, or an owner "
               "ruling that the lean evidence doc is the intended declaration, clears the corresponding "
               "blocker.")))

events.append(event(10, "status", status="active", hours=0.5,
    summary=("W003-F2B-REV14-CANDIDATE-INDEPENDENT-CLOSURE-01 complete at worker level: 6 artifacts on disk and "
             "hash-pinned, independent verifier exit 2 with 12/16 checks pass, 7/7 planted controls "
             "discriminate, 50/50 candidate FROZEN pins resolve, zero canonical writes. Verdict "
             "CANDIDATE_NOT_ACCEPTANCE_READY (hard failures W003-F2B14-H1/H2). Completion claim only: workers "
             "cannot set done/passed or a gate verdict. Checkpoint follows."),
    evidence_refs=[rep_ref, readme_ref, probe_ref, script_ref],
    next_falsifier=report["next_falsifier"]))

OUTBOX.parent.mkdir(parents=True, exist_ok=True)
with OUTBOX.open("a") as fh:
    for e in events:
        fh.write(json.dumps(e, sort_keys=False) + "\n")

# ---------------------------------------------------------------- checkpoint
ckpt_dt = datetime.datetime.now().astimezone().replace(microsecond=0)
ckpt_id = "w003-ckpt-" + ckpt_dt.strftime("%Y%m%dT%H%M%S")
ckpt_path = STATE / f"w003_checkpoint_{ckpt_dt.strftime('%Y%m%dT%H%M%S')}.json"
cpdir = STATE / "checkpoints"
global_ckpt = None
if cpdir.exists():
    cands = sorted(cpdir.glob("ckpt-*.json"))
    global_ckpt = str(cands[-1].relative_to(REPO)) if cands else None

checkpoint = {
    "worker": "worker-003",
    "task_id": TASK,
    "checkpoint_id": ckpt_id,
    "created_at": ckpt_dt.isoformat(),
    "node_id": NODE,
    "class_ids": [CLASS],
    "gate": GATE,
    "verdict": report["verdict"],
    "hard_failures": [h["id"] for h in report["hard_failures"]],
    "family_status": report["family_status"],
    "checks": "12/16 pass; 7/7 planted controls discriminate; 50/50 candidate FROZEN pins resolve; 0 canonical writes",
    "probe_exit_code": 2,
    "artifacts": {f"artifacts/worker-003/f2b_rev14_candidate_closure/{d}": hashes[d] for d in DELIVERABLES},
    "pins": {"candidate_c0": "48cadb72e507cfcbc469f6519fcc0294bb83f083cc1733521610ff63e5f3c38a",
             "candidate_frozen": "a57492ccae88d540dce9a4206a072b6110aef8be403078a421902b57e68041fa",
             "live_c0": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
             "live_frozen": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
             "live_f0": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
             "live_aggregator_at_run": "27255e5b34f36b252accf1217dc01b63a5f5ec09f33af03938565c8fb99b20ed"},
    "live_base_drift": report["live_base_drift"],
    "events": [e["event_id"] for e in events],
    "next_falsifier": report["next_falsifier"],
    "result": report["verdict"] + ": candidate closes H1/H2 (containment) and A6/SEP-6, but A2 durability and "
              "variant-delta re-base are hard failures; non-blocking publication notes N1-N6 recorded.",
}
ckpt_path.write_text(json.dumps(checkpoint, indent=1, sort_keys=True) + "\n")
with (STATE / "w003_checkpoints.jsonl").open("a") as fh:
    fh.write(json.dumps(checkpoint, sort_keys=True) + "\n")

# checkpoint event references the checkpoint files
ckpt_ref = f"runtime/state/{ckpt_path.name}#" + sha(ckpt_path)[:12]
log_ref = "runtime/state/w003_checkpoints.jsonl#" + sha(STATE / "w003_checkpoints.jsonl")[:12]
ev = event(11, "status", status="active", hours=0.5,
    summary=(f"Checkpoint complete: {ckpt_ref} and runtime/state/w003_checkpoints.jsonl, pinning 6 artifacts "
             f"and {len(events)} task events. Live drift recorded: schemas/af_scc_regularities.yaml 94562101 -> "
             f"27255e5b during the run; not in FROZEN.files, so not a freeze breach. Bounded task ends here; no "
             f"gate verdict or node transition claimed."),
    evidence_refs=[ckpt_ref, log_ref, rep_ref],
    next_falsifier=report["next_falsifier"])
with OUTBOX.open("a") as fh:
    fh.write(json.dumps(ev, sort_keys=False) + "\n")

# SHA256SUMS for the deliverable dir (excluding itself)
sums = ROOT / "SHA256SUMS"
lines = [f"{hashes[d]}  {d}" for d in DELIVERABLES]
sums.write_text("\n".join(lines) + "\n")

print("events emitted:", [e["event_id"] for e in events] + [ev["event_id"]])
print("checkpoint:", ckpt_ref)
print("deliverable hashes:")
for d in DELIVERABLES:
    print(" ", hashes[d][:16], d)
