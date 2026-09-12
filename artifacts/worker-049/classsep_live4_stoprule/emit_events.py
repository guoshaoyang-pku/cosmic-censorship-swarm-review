#!/usr/bin/env python3
"""Emit W049-CLASSSEP-LIVE4-STOPRULE-03 checkpoint + outbox events (idempotent ids)."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
A = ROOT / "artifacts/worker-049/classsep_live4_stoprule"
OUTBOX = ROOT / "comms/outbox/worker-049.jsonl"
CP = ROOT / "runtime/state/w049_live4_stoprule_checkpoint.json"
CPL = ROOT / "runtime/state/w049_checkpoints.jsonl"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


results = A / "results.json"
runner = A / "run_live4_audit_049.py"
prereg = A / "pre_registration.json"
readme = A / "README.md"
res = json.loads(results.read_text())
hashes = {"results": {"path": results.relative_to(ROOT).as_posix(), "sha256": sha(results)},
          "runner": {"path": runner.relative_to(ROOT).as_posix(), "sha256": sha(runner)},
          "prereg": {"path": prereg.relative_to(ROOT).as_posix(), "sha256": sha(prereg)},
          "readme": {"path": readme.relative_to(ROOT).as_posix(), "sha256": sha(readme)}}
stop = res["stop_rule_determination"]
summary = res["summary"]

checkpoint = {
    "schema": "worker-049/task-checkpoint/v1",
    "task_id": "W049-CLASSSEP-LIVE4-STOPRULE-03",
    "actor": "worker-049",
    "instance": "worker-049-20260912T010537-968807",
    "created_at": "2026-09-12T01:11:00+08:00",
    "node_id": "A1",
    "gate": "G-AUDIT",
    "class_id": "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
    "status": "complete_at_worker_level",
    "validation_status": "unverified",
    "one_line": "Live class-separation detector oscillated inside the open adjudication window "
                "(a8c04fc3 -> e36b0d644ca7 ~01:06 -> a8c04fc3 at 01:08:14); stop-rule condition 1 "
                "is satisfied and recorded as unresolved; the drift revision e36b0d644ca7 is "
                "behaviourally identical to a8c04fc31e4a on all 34 pre-registered adversarial "
                "fixtures (10/34 cue-carrying genuine assertions cleared, all HIGH) and is neither "
                "a fix nor a regression on this set.",
    "artifacts": hashes,
    "stop_rule_determination": stop["determination"],
    "live_at_measure_start": stop["live_at_measure_start"],
    "live_at_measure_end": stop["live_at_measure_end"],
    "condition_1_live_moved": stop["condition_1_live_moved"],
    "condition_2_recovery_failed": stop["condition_2_recovery_failed"],
    "cue_fn_totals_across_three_corpora": {k: v["cue_fn_total_all_corpora"] for k, v in summary.items()},
    "worker07": {k: v["worker07"] + " " + v["worker07_verdict"] for k, v in summary.items()},
    "authority": "worker event; no gate verdict, no node status, no validation_status; every input read-only",
    "next_falsifier": res["pins"] and "re-run run_live4_audit_049.py at the pre_registration pins; any per-fixture flag or cue-FN drift, any pin mismatch, or a non-reproducible stop-rule determination falsifies",
}
CP.write_text(json.dumps(checkpoint, indent=1) + "\n")
if "W049-CLASSSEP-LIVE4-STOPRULE-03" not in CPL.read_text():
    with CPL.open("a") as f:
        f.write(json.dumps({"checkpoint": 4, "at": checkpoint["created_at"], "worker": "worker-049",
                        "instance": checkpoint["instance"], "assignment": checkpoint["task_id"],
                        "node_id": "A1", "gate": "G-AUDIT",
                        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
                        "hours_spent_estimate": 0.4,
                        "status": {"delivered": True, "validation_status": "unverified",
                                   "stop_rule": stop["determination"]},
                        "checkpoint_file": CP.relative_to(ROOT).as_posix(),
                        "checkpoint_sha256": sha(CP)}) + "\n")

def ref(name: str) -> str:
    return hashes[name]["path"] + "#" + hashes[name]["sha256"][:12]


ev = []
base = {"actor": "worker-049", "node_id": "A1", "gate": "G-AUDIT",
        "class_id": "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN", "group_id": "audit",
        "task_id": "W049-CLASSSEP-LIVE4-STOPRULE-03",
        "authority_note": "worker evidence; cannot set status=done, validation_status=passed or a gate verdict"}

ev.append({**base, "event_id": "w049-live4-20260912T0111-art-results", "event_type": "artifact",
           "artifact_type": "stoprule_census", "path": hashes["results"]["path"],
           "sha256": hashes["results"]["sha256"], "validation_status": "unverified",
           "created_at": "2026-09-12T01:11:00+08:00",
           "evidence_refs": [ref("results"), ref("runner"), ref("prereg")]})
ev.append({**base, "event_id": "w049-live4-20260912T0111-art-harness", "event_type": "artifact",
           "artifact_type": "runner_and_preregistration",
           "path": hashes["runner"]["path"], "sha256": hashes["runner"]["sha256"],
           "validation_status": "unverified", "created_at": "2026-09-12T01:11:05+08:00",
           "supporting": [hashes["prereg"], hashes["readme"]],
           "harness_provenance": res["harness"]})
ev.append({**base, "event_id": "w049-live4-20260912T0111-claim", "event_type": "claim",
           "created_at": "2026-09-12T01:11:10+08:00", "conclusion_type": "empirical_observation",
           "statement": "The class-separation detector live path moved after the 01:00:35 adjudication "
                        "card was issued: it held e36b0d644ca7 (not one of the card's three hashes) at "
                        "01:07 and was restored to a8c04fc31e4a at mtime 01:08:14. Stop-rule condition 1 "
                        "is therefore satisfied; condition 2 is not (the recovered c266dbec copy "
                        "re-verifies). Measured from an independent hash-verified pinned copy, "
                        "e36b0d644ca7 is behaviourally identical to a8c04fc31e4a on all 34 "
                        "pre-registered adversarial fixtures: 10/34 cue-carrying genuine assertions "
                        "cleared (all HIGH), 0/12 v3 discriminators, 6 v1 mention FPs, declaration "
                        "diffs 1/13/1, worker-07 17/0/10/0 PASS. It is neither a fix nor a regression "
                        "on this set.",
           "assumptions": ["the three pre-registered corpora are frozen at the hashes in pre_registration.json",
                           "the pinned copies hash-verified in results.json.pins are byte-exact",
                           "cue-induced FN = adversarial fixture clears while its cue-stripped twin flags on the same detector"],
           "falsifier": "re-run run_live4_audit_049.py at the pins: any per-fixture flag or cue-FN count differing from results.json, any pin mismatch, a non-deterministic double run, or evidence the live path never held e36b0d644ca7 after 01:00:35 falsifies",
           "evidence_refs": [ref("results"),
                             "research_map/class_separation.py#a8c04fc31e4a",
                             "artifacts/worker-045/classsep_e36_arm/pinned/class_separation_e36b0d644ca.py#e36b0d644ca7",
                             "artifacts/worker-049/classsep_fn_audit/pinned/class_separation_c266_recovered.py#c266dbceca87",
                             "artifacts/worker-049/classsep_fn_audit/corpus.json#9eb2ea9e2743",
                             "artifacts/worker-049/classsep_fn_audit/corpus_guard_probe.json#db6dff9f4eda",
                             "artifacts/worker-049/classsep_successor_audit/corpus_v3.json#6764c04978c9",
                             "comms/inbox/astra-lead-audit.jsonl#astra-life06-classsep-detector-adjudication",
                             "comms/inbox/astra.jsonl#astra-detector-patch-result-0112"]})
ev.append({**base, "event_id": "w049-live4-20260912T0111-blocker-stoprule", "event_type": "blocker",
           "created_at": "2026-09-12T01:11:15+08:00",
           "description": "The adjudication card astra-life06-classsep-detector-adjudication binds three "
                          "hashes but its instrument moved inside the window and then reverted: "
                          "a8c04fc31e4a (card) -> e36b0d644ca7 (~01:06, controller records the patch as "
                          "not accepted) -> a8c04fc31e4a (01:08:14). The card's own stop rule says to "
                          "record the contest as unresolved rather than shipping a patch; a fourth-hash "
                          "census exists only for this drift revision and shows it is identical to the "
                          "applied revision on the pre-registered FN set.",
           "needed_to_unblock": "astra-lead-audit: state explicitly whether the 01:00:35 card is read at "
                                "(a) the currently live a8c04fc31e4a endpoint, with the 01:06-01:08 "
                                "e36b0d644ca7 excursion recorded as an instrument-integrity finding, or "
                                "(b) unresolved per the stop rule. Either way the standing over-suppression "
                                "blocker is unchanged: no revision yet measured clears 0 cue-induced FN on "
                                "v1/v2/v3.",
           "evidence_refs": [ref("results"),
                             "comms/inbox/astra.jsonl#astra-detector-patch-result-0112",
                             "comms/inbox/astra-lead-audit.jsonl#astra-life06-classsep-detector-adjudication",
                             "research_map/class_separation.py#a8c04fc31e4a"],
           "next_falsifier": "A controller/lead record that binds the detector decision at a hash that is "
                             "stable across the decision window, or a revision that clears 0 cue-induced FN "
                             "on v1/v2/v3 at unchanged corpus hashes."})
ev.append({**base, "event_id": "w049-live4-20260912T0111-status-final", "event_type": "status",
           "created_at": "2026-09-12T01:11:20+08:00", "status": "active", "hours": 0.4,
           "summary": "W049-CLASSSEP-LIVE4-STOPRULE-03 complete at worker level: live-detector drift "
                      "endpoint measured, stop-rule condition 1 satisfied (moved and reverted), "
                      "condition 2 clear, drift revision e36b0d644ca7 behaviourally identical to "
                      "a8c04fc31e4a on all 34 pre-registered adversarial fixtures. Checkpoint "
                      "runtime/state/w049_live4_stoprule_checkpoint.json. No gate verdict, node status or "
                      "validation_status claimed; every canonical input read-only.",
           "evidence_refs": [ref("results"), "runtime/state/w049_live4_stoprule_checkpoint.json#" + sha(CP)[:12]],
           "next_falsifier": "Re-run the runner at the pins; any census or stop-rule drift falsifies."})

with OUTBOX.open("a") as f:
    for e in ev:
        f.write(json.dumps(e) + "\n")

# validation pass on the whole outbox
bad = 0
for i, line in enumerate(OUTBOX.read_text().splitlines(), 1):
    if not line.strip():
        continue
    try:
        json.loads(line)
    except Exception as ex:
        bad += 1
        print(f"BAD line {i}: {ex}")
print("checkpoint_sha256", sha(CP))
print("results_sha256", hashes["results"]["sha256"])
print("events_appended", len(ev), "outbox_bad_lines", bad)
