#!/usr/bin/env python3
"""W16-CONV-04 emitter: append convergence-16 events to the worker-16 outbox and checkpoint.

Idempotent: if an event_id is already present in the outbox, it is not appended again.
Aborts on any target-hash drift relative to the reviewed FROZEN rev29 pins.
"""
import hashlib
import json
import os
import datetime

ROOT = "/data3/guoshaoyang/workdir/ai4math-swarm"
os.chdir(ROOT)

PINS = {
    "artifacts/formulation/FROZEN.json": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "schemas/af_wcc_vacuum.yaml": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "ledger/theorems.jsonl": "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28",
}
REVIEW = "reviews/convergence-16.json"
REPORT = "artifacts/worker-16/convergence/REPORT.md"
OUTBOX = "comms/outbox/worker-16.jsonl"
CHECKPOINT = "runtime/state/w016_checkpoint_convergence.json"
CHECKPOINT_LOG = "runtime/state/w016_checkpoints.jsonl"


def h(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


drift = {p: (PINS[p], h(p)) for p in PINS if h(p) != PINS[p]}
if drift:
    raise SystemExit("DRIFT DETECTED, not emitting: %s" % json.dumps(drift))

review_sha = h(REVIEW)
report_sha = h(REPORT)
run_log_sha = h("artifacts/worker-16/convergence/out/run_log.json")
ts = "20260912T0112"
base = "w16-conv04-%s" % ts
review_obj = json.load(open(REVIEW))
by_target = {}
for _t in review_obj["targets"]:
    by_target[_t["target_id"]] = _t
    if _t.get("target_subnode"):
        by_target[_t["target_subnode"]] = _t

def ev(eid, etype, **kw):
    d = {"event_id": eid, "event_type": etype, "created_at": now(), "actor": "worker-16",
         "assignment_event_id": "astra-conv-04", "node_id": "A1", "gate": "G-AUDIT"}
    d.update(kw)
    return d

events = [ev(base + "-artifact-convergence", "artifact",
             artifact_type="review", path=REVIEW, sha256=review_sha,
             bytes=os.path.getsize(REVIEW), validation_status="unverified",
             class_ids=["AF-WCC-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
             summary="W16-CONV-04 P2 B/N convergence triage at FROZEN rev29 815e08079aef: F0 accept, F1 accept, F2b accept, L0 revise (2 B). Same-reviewer triage, not an independent second verdict.",
             evidence_refs=[REVIEW + "#" + review_sha[:12],
                            "artifacts/formulation/FROZEN.json#815e08079aef",
                            "artifacts/worker-16/convergence/out/run_log.json#" + run_log_sha[:12],
                            REPORT + "#" + report_sha[:12]])]

rev_meta = {
    "F0": ("AF-WCC-VAC-GEN", "research_map/formulation_taxonomy.yaml#" + PINS["research_map/formulation_taxonomy.yaml"][:12]),
    "F1": ("AF-WCC-VAC-GEN", "schemas/af_wcc_vacuum.yaml#" + PINS["schemas/af_wcc_vacuum.yaml"][:12]),
    "F2b": ("AF-SCC-C0-VAC-GEN", "schemas/af_scc_c0_vacuum.yaml#" + PINS["schemas/af_scc_c0_vacuum.yaml"][:12]),
    "L0": ("AF-SCC-C0-VAC-GEN", "research_map/research_map.json#claim-lit-20260911-012-1abbb2fa6746"),
}
for tid in ["F0", "F1", "F2b", "L0"]:
    t = by_target[tid]
    cls, target_ref = rev_meta[tid]
    findings = [{"label": f["label"], "status": f.get("status", ""),
                 "severity": "blocking" if f["label"].startswith("B-") else "non_blocking",
                 "statement": f.get("statement", "")[:300]} for f in t["findings"]]
    events.append(ev("%s-review-%s" % (base, tid.lower()), "review",
                     target_id=tid, reviewer="worker-16",
                     class_id=cls, class_ids=review_obj["class_ids"],
                     reviewed_artifact=t["path"], reviewed_sha256=t.get("sha256") or t.get("claim_canonical_sha256"),
                     verdict=t["verdict"], score=t["score"], hard_failures=t.get("hard_failures", []),
                     findings=findings,
                     counts_as_independent_second_verdict=False,
                     b_n_policy=review_obj["b_n_policy"],
                     next_falsifier=t["next_falsifier"],
                     evidence_refs=[REVIEW + "#" + review_sha[:12], target_ref,
                                    "artifacts/formulation/FROZEN.json#815e08079aef"]))

events.append(ev(base + "-status", "status",
                 status="active", hours=1.0,
                 class_ids=review_obj["class_ids"],
                 summary=("W16-CONV-04 complete (worker evidence, not a gate verdict): reviews/convergence-16.json "
                          "sha256 %s triages all four worker-16 review targets at FROZEN rev29 815e08079aef. "
                          "F0 0abb9ed8 accept; F1 d9cebb94 accept (all 4 prior blocking findings resolved; R03 stage-2 "
                          "reject is a lexical tool false positive per W16-R03-ADJ-01, carried as a gate blocker); "
                          "F2b b2ab6acb accept (prior blocking findings resolved, symmetry slot present; r3 accept at "
                          "6f121a82 does not transfer); L0 claim lit-20260911-012 revise with 2 B findings (class "
                          "binding lacks the interior-data transfer label; statement drops the 'appropriate' "
                          "qualifier). Same-reviewer triage: does not satisfy G-AUDIT's independent-second-verdict "
                          "requirement. No frozen byte modified." % review_sha[:12]),
                 evidence_refs=[REVIEW + "#" + review_sha[:12],
                                "artifacts/worker-16/convergence/out/run_log.json#" + run_log_sha[:12],
                                "artifacts/formulation/FROZEN.json#815e08079aef"],
                 next_falsifier=("A run_acceptance.py exit 0 at the frozen bytes with unpatched tools; or an R03 "
                                 "stage-2 accept at F1 d9cebb94; or a claim lit-20260911-012 revision carrying the "
                                 "qualifier + transfer label (flips L0 to accept); or any target-hash drift."),
                 open_gate_blockers=[b["id"] for b in review_obj["open_gate_blockers"]],
                 review_artifact=REVIEW + "#" + review_sha[:12]))

existing = set()
if os.path.exists(OUTBOX):
    for line in open(OUTBOX):
        line = line.strip()
        if not line:
            continue
        try:
            existing.add(json.loads(line).get("event_id"))
        except Exception:
            pass
appended = [e for e in events if e["event_id"] not in existing]
with open(OUTBOX, "a") as f:
    for e in appended:
        f.write(json.dumps(e, sort_keys=True) + "\n")

post_drift = {p: h(p) for p in PINS}
ckpt = {
    "actor": "worker-16",
    "worker": "worker-16",
    "worker_slot": "worker-016",
    "checkpoint_id": "w16-ckpt-conv04-01",
    "checkpoint_at": now(),
    "task": {"id": "W16-CONV-04", "assignment_event_id": "astra-conv-04", "node_id": "A1",
             "gate": "G-AUDIT", "class_ids": review_obj["class_ids"],
             "budget_agent_hours": 1.5, "hours_this_pass": 1.0, "source": "open astra-conv-04 card in comms/inbox/deepseek-flash-16.jsonl"},
    "frozen_binding": {"manifest": "artifacts/formulation/FROZEN.json", "revision": 29,
                       "manifest_sha256": PINS["artifacts/formulation/FROZEN.json"],
                       "verify_frozen": "rc=0, 50 files, 0 problems"},
    "deliverables": {REVIEW: {"sha256": review_sha, "bytes": os.path.getsize(REVIEW)},
                     REPORT: {"sha256": report_sha, "bytes": os.path.getsize(REPORT)},
                     "artifacts/worker-16/convergence/out/run_log.json": {"sha256": run_log_sha}},
    "verdicts": {t["target_id"]: {"sha256": t.get("sha256") or t.get("claim_canonical_sha256"),
                                  "verdict": t["verdict"], "score": t["score"],
                                  "b_open": sum(1 for f in t["findings"] if f["label"].startswith("B-")),
                                  "n_open": sum(1 for f in t["findings"] if f["label"].startswith("N-"))}
                 for t in review_obj["targets"]},
    "emitted_events": [e["event_id"] for e in events],
    "events_appended_this_pass": [e["event_id"] for e in appended],
    "post_write_drift_check": {p: ("match" if post_drift[p] == PINS[p] else "DRIFT") for p in PINS},
    "open_and_not_addressed": [b["id"] + ": " + b["scope"] for b in review_obj["open_gate_blockers"]],
    "read_only": "no shared/frozen artifact modified; writes are reviews/convergence-16.json, artifacts/worker-16/convergence/, the worker-16 outbox, and this checkpoint",
    "authority_note": "worker event cannot set validation_status=passed, node status=done, or a gate verdict; this convergence triage is not an independent second verdict.",
}
open(CHECKPOINT, "w").write(json.dumps(ckpt, indent=1, sort_keys=True) + "\n")
with open(CHECKPOINT_LOG, "a") as f:
    f.write(json.dumps({"checkpoint_id": ckpt["checkpoint_id"], "at": ckpt["checkpoint_at"],
                        "path": os.path.basename(CHECKPOINT),
                        "verdict": "F0 accept / F1 accept / F2b accept / L0 revise(2B) at FROZEN rev29",
                        "events": len(appended)}) + "\n")

print("drift: none")
print("review sha256:", review_sha)
print("events appended:", len(appended), "of", len(events))
for e in events:
    print(" ", e["event_type"], e["event_id"])
print("checkpoint:", CHECKPOINT)
