#!/usr/bin/env python3
"""Emit W16-F2B-REV29-CONTAINMENT-ADJUDICATION-01 events, idempotently.

Writes (append-only, idempotent by event_id):
  artifacts/worker-016/f2b_rev29_containment_adjudication/manifest.json
  runtime/state/w016_checkpoint_f2b_rev29_adjudication.json
  runtime/state/w016_checkpoints.jsonl
  comms/outbox/worker-16.jsonl

Read-only on every canonical artifact. No map/ledger/schema/detector write.
"""
import datetime
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
BASE = "artifacts/worker-016/f2b_rev29_containment_adjudication"
TASK_ID = "W16-F2B-REV29-CONTAINMENT-ADJUDICATION-01"
CLASS_ID = "AF-SCC-C0-VAC-GEN"
NODE_ID = "F2b"
GATE = "G-FORM"
ACTOR = "worker-16"
SLOT = "worker-016"
PREFIX = "w16-f2b-rev29-adj-20260912T0115"
OUTBOX = os.path.join(ROOT, "comms", "outbox", "worker-16.jsonl")
STATE = os.path.join(ROOT, "runtime", "state")
CKPT = os.path.join(STATE, "w016_checkpoint_f2b_rev29_adjudication.json")
CKPT_LOG = os.path.join(STATE, "w016_checkpoints.jsonl")

F2B = "schemas/af_scc_c0_vacuum.yaml"
F2A = "schemas/af_scc_c2_vacuum.yaml"
FROZEN = "artifacts/formulation/FROZEN.json"
F0 = "research_map/formulation_taxonomy.yaml"
VOCAB = "artifacts/formulation/VOCAB_ALIASES.json"


def sha(rel):
    with open(os.path.join(ROOT, rel), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def ref(rel, full=False):
    h = sha(rel)
    return "%s#sha256:%s" % (rel, h if full else h[:12])


def now_ts():
    n = datetime.datetime.now().astimezone()
    ts = n.strftime("%Y-%m-%dT%H:%M:%S%z")
    return ts[:-2] + ":" + ts[-2:]


def build_manifest():
    files = ["adjudicate_f2b_containment.py", "results.json", "cluster_table.json",
             "REPORT.md", "controls/null_copy_frozen.yaml", "emit_events.py"]
    man = {
        "task_id": TASK_ID,
        "actor": SLOT,
        "self_reference": ("this manifest cannot contain its own post-write sha256; its hash is "
                           "recorded in the artifact event that publishes it"),
        "files": {f: sha(BASE + "/" + f) for f in files},
    }
    with open(os.path.join(HERE, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(man, fh, indent=1)
        fh.write("\n")
    return man


def main():
    r = json.load(open(os.path.join(HERE, "results.json"), encoding="utf-8"))
    c = json.load(open(os.path.join(HERE, "cluster_table.json"), encoding="utf-8"))
    man = build_manifest()
    h = {f: sha(BASE + "/" + f) for f in
         ["adjudicate_f2b_containment.py", "results.json", "cluster_table.json",
          "REPORT.md", "manifest.json"]}
    R = {k: "%s/%s#sha256:%s" % (BASE, k, v) for k, v in h.items()}
    pins = ("%s#sha256:%s" % (F2B, sha(F2B)[:12]), "%s#sha256:%s" % (F2A, sha(F2A)[:12]),
            "%s#sha256:%s" % (FROZEN, sha(FROZEN)[:12]), "%s#sha256:%s" % (F0, sha(F0)[:12]),
            "%s#sha256:%s" % (VOCAB, sha(VOCAB)[:12]))

    ts = now_ts()
    findings = {f["id"]: f["status"] for f in r["findings"]}
    rep = r["repair_adequacy"]
    landable = r["adjudication"]["landable_candidates"]
    not_landable = r["adjudication"]["not_landable_candidates"]

    # worker checkpoint (written before events so its hash can be referenced)
    ckpt = {
        "task_id": TASK_ID,
        "actor": SLOT,
        "created_at": r["generated_at"],
        "class_id": CLASS_ID,
        "sibling_control_class_id": r["sibling_control_class_id"],
        "node_id": NODE_ID,
        "gate": GATE,
        "pins": {k: v["measured"] for k, v in r["pins_measured"].items()},
        "pins_all_match": r["pins_all_match"],
        "findings": findings,
        "repair_adequacy": {k: {kk: vv for kk, vv in v.items() if kk != "changed_paths"}
                            for k, v in rep.items()},
        "landable_candidates": landable,
        "not_landable_candidates": not_landable,
        "controls_hold": r["pre_registered_predicates_hold"],
        "checker_exit_code": r["exit_code"],
        "cluster_census": {"n_adverse_verdicts": c["n_adverse_verdicts"],
                           "carrier_counts": c["carrier_counts"]},
        "artifact_hashes": h,
        "authority": r["authority"],
        "not_claimed": r["not_claimed"],
    }
    with open(CKPT, "w", encoding="utf-8") as fh:
        json.dump(ckpt, fh, indent=1)
        fh.write("\n")
    log_row = {"task_id": TASK_ID, "actor": SLOT, "created_at": ckpt["created_at"],
               "checkpoint": os.path.relpath(CKPT, ROOT),
               "checkpoint_sha256": sha(os.path.relpath(CKPT, ROOT)),
               "findings": findings, "landable": landable}
    log_line = json.dumps(log_row)
    prior_log = ""
    if os.path.exists(CKPT_LOG):
        with open(CKPT_LOG, "r", encoding="utf-8") as fh:
            prior_log = fh.read()
    if log_line not in prior_log.splitlines():
        with open(CKPT_LOG, "a", encoding="utf-8") as fh:
            fh.write(log_line + "\n")
    ck_ref = "runtime/state/w016_checkpoint_f2b_rev29_adjudication.json#sha256:" + \
             sha("runtime/state/w016_checkpoint_f2b_rev29_adjudication.json")[:12]

    # stale refs from the first publish, for an explicit erratum (no measurement changed)
    stale = {}
    if os.path.exists(OUTBOX):
        with open(OUTBOX, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                except Exception:
                    continue
                if e.get("event_id") == PREFIX + "-artifact-manifest":
                    stale["manifest_sha256"] = e.get("sha256")
    stale_manifest = stale.get("manifest_sha256", "<not previously published>")

    events = [
        {
            "event_id": PREFIX + "-task-claim", "event_type": "status", "created_at": ts,
            "actor": ACTOR, "agent_slot": SLOT, "task_id": TASK_ID, "node_id": NODE_ID,
            "gate": GATE, "class_id": CLASS_ID, "status": "active", "hours": 0.6,
            "summary": ("No open worker-016 inbox card (FORM-HELDOUT-08 closed 00:15, superseded "
                        "by FORM-HELDOUT-09). Took ONE bounded class-bound task "
                        "W16-F2B-REV29-CONTAINMENT-ADJUDICATION-01: independent adjudication of "
                        "the late adverse F2b verdicts at the frozen rev29 pin b2ab6acb2bbe and "
                        "a repair-adequacy test of the four circulating candidates."),
            "evidence_refs": [pins[0], pins[2], pins[3]],
            "next_falsifier": ("any pinned input moves mid-run, or a re-run of the checker under "
                               "the same pins produces a different finding set (exit 3/2 voids)"),
        },
        {
            "event_id": PREFIX + "-artifact-checker", "event_type": "artifact", "created_at": ts,
            "actor": ACTOR, "agent_slot": SLOT, "node_id": NODE_ID, "gate": GATE,
            "class_id": CLASS_ID, "artifact_type": "adjudication_checker",
            "path": BASE + "/adjudicate_f2b_containment.py", "sha256": h["adjudicate_f2b_containment.py"],
            "validation_status": "unverified",
            "description": ("Deterministic read-only checker: H1 premise inversion, H2 normative "
                            "denial, H3 repair entailment direction, V1 token divergence; 9 "
                            "pre-registered evaluations incl. synthetic discrimination controls"),
            "evidence_refs": [R["adjudicate_f2b_containment.py"], pins[0]],
        },
        {
            "event_id": PREFIX + "-artifact-results", "event_type": "artifact", "created_at": ts,
            "actor": ACTOR, "agent_slot": SLOT, "node_id": NODE_ID, "gate": GATE,
            "class_id": CLASS_ID, "artifact_type": "adjudication_results",
            "path": BASE + "/results.json", "sha256": h["results.json"],
            "validation_status": "unverified",
            "description": ("Pins all match; frozen H1/H2 reproduced; circulating repairs "
                            "84b5d3fa/98f9ec83 introduce H3; corrected 51c253c4 and nesting "
                            "4951cc96 finding-free; controls 9/9 as pre-registered, exit 0"),
            "evidence_refs": [R["results.json"], pins[0], pins[1], pins[2], pins[3], pins[4]],
        },
        {
            "event_id": PREFIX + "-artifact-cluster", "event_type": "artifact", "created_at": ts,
            "actor": ACTOR, "agent_slot": SLOT, "node_id": NODE_ID, "gate": GATE,
            "class_id": CLASS_ID, "artifact_type": "adverse_verdict_census",
            "path": BASE + "/cluster_table.json", "sha256": h["cluster_table.json"],
            "validation_status": "unverified",
            "description": ("18 adverse verdicts bound to b2ab6acb2bbe since 00:50; keyword carrier "
                            "counts H1 6, V1 4, H3 3, H2 1 (lower bound; ids-only entries unmapped)"),
            "evidence_refs": [R["cluster_table.json"], pins[0]],
        },
        {
            "event_id": PREFIX + "-artifact-report", "event_type": "artifact", "created_at": ts,
            "actor": ACTOR, "agent_slot": SLOT, "node_id": NODE_ID, "gate": GATE,
            "class_id": CLASS_ID, "artifact_type": "report",
            "path": BASE + "/REPORT.md", "sha256": h["REPORT.md"], "validation_status": "unverified",
            "description": "Human-readable adjudication: findings, repair table, controls, disposition",
            "evidence_refs": [R["REPORT.md"], pins[0]],
        },
        {
            "event_id": PREFIX + "-artifact-manifest", "event_type": "artifact", "created_at": ts,
            "actor": ACTOR, "agent_slot": SLOT, "node_id": NODE_ID, "gate": GATE,
            "class_id": CLASS_ID, "artifact_type": "manifest",
            "path": BASE + "/manifest.json", "sha256": h["manifest.json"],
            "validation_status": "unverified",
            "description": "sha256 of every deliverable except the manifest itself",
            "evidence_refs": [R["manifest.json"]],
        },
        {
            "event_id": PREFIX + "-review-f2b", "event_type": "review", "created_at": ts,
            "actor": ACTOR, "agent_slot": SLOT, "target_id": NODE_ID, "node_id": NODE_ID,
            "gate": GATE, "class_id": CLASS_ID, "reviewed_path": F2B,
            "reviewer": ACTOR,
            "reviewed_sha256": sha(F2B),
            "reviewed_frozen_path": FROZEN, "reviewed_frozen_sha256": sha(FROZEN),
            "counts_as_full_schema_verdict": False,
            "counts_reason": ("adjudication of third-party adverse verdicts plus candidate testing; "
                              "not a fresh independent full-schema verdict; counting is the "
                              "controller/audit-lead decision"),
            "authority_note": r["authority"],
            "verdict": "revise", "score": 3.0,
            "hard_failures": [
                {"id": "W16-F2B-REV29-H1",
                 "field": "implication_ledger.forbidden_transfers[0].reason",
                 "severity": "blocking-for-clean-accept",
                 "detail": r["findings"][0]["basis"],
                 "falsifier": r["findings"][0]["falsifier"]},
                {"id": "W16-F2B-REV29-H2",
                 "field": "regularity.must_not_conflate[0]",
                 "severity": "blocking-for-clean-accept",
                 "detail": r["findings"][1]["basis"],
                 "falsifier": r["findings"][1]["falsifier"]},
            ],
            "findings": [
                {"id": "W16-F2B-REV29-H3",
                 "severity": "blocking-for-landing-circulating-repairs",
                 "detail": r["findings"][2]["basis"],
                 "independently_reproduces": "worker-029 W029-R7-H2",
                 "falsifier": r["findings"][2]["falsifier"]},
                {"id": "W16-F2B-REV29-V1",
                 "severity": "non-blocking",
                 "detail": r["findings"][3]["basis"] + "; separate single-sourcing ruling pending "
                           "under w017-20260912-vocab-source-blocker",
                 "falsifier": r["findings"][3]["falsifier"]},
            ],
            "falsifier": ("re-run the checker at the same pins and obtain a different carrier set; "
                          "or exhibit a frozen adjudication that the pinned carriers are correct"),
            "evidence_refs": [pins[0], pins[2], pins[1], pins[4], R["results.json"],
                              R["adjudicate_f2b_containment.py"], R["cluster_table.json"],
                              ck_ref],
        },
        {
            "event_id": PREFIX + "-claim-adjudication", "event_type": "claim", "created_at": ts,
            "actor": ACTOR, "agent_slot": SLOT, "node_id": NODE_ID, "gate": GATE,
            "class_id": CLASS_ID, "conclusion_type": "formal_model",
            "statement": ("Instrument-and-checker measurement, not a mathematics claim: at pins F2b "
                          "b2ab6acb2bbe / F2a e9a27996dfd3 / FROZEN rev29 815e08079aef / F0 "
                          "0abb9ed8a961, the frozen F2b carries two real adverse carriers (H1 "
                          "inverted 'larger' premise vs its own E-nesting, H2 normative containment "
                          "denial vs its own ledger and the corrected C2 sibling); the circulating "
                          "repairs 84b5d3fa and 98f9ec83 close H1/H2 but introduce a reversed "
                          "H2_loc entailment (H3, class-relative: true in C2, false in C0), while "
                          "worker-029 candidates 51c253c4 and 4951cc96 are finding-free under the "
                          "same checker; no candidate re-stamps the V1 alias token."),
            "assumptions": [
                "the file's own extension_class_containment, forbidden_weakenings and "
                "one_way_entailments rows are the binding direction reference at this pin",
                "the corrected C2 sibling is the cross-artifact direction control",
                "keyword/lexical adjudication is sufficient for the named prose carriers; the "
                "underlying PDE statements are not re-proved",
            ],
            "falsifier": ("any pinned input moves; a landed repair whose H2_loc sentence keeps the "
                          "C0 => H2_loc direction makes H3 fire again; a fresh frozen adjudication "
                          "reversing the E-nesting voids H1/H2"),
            "artifact_refs": [BASE + "/results.json", BASE + "/REPORT.md",
                              BASE + "/cluster_table.json", BASE + "/manifest.json"],
            "evidence_refs": [R["results.json"], R["REPORT.md"], R["cluster_table.json"],
                              pins[0], pins[1], pins[2], ck_ref],
        },
        {
            "event_id": PREFIX + "-blocker-f2b-landing", "event_type": "blocker", "created_at": ts,
            "actor": ACTOR, "agent_slot": SLOT, "node_id": NODE_ID, "gate": GATE,
            "class_id": CLASS_ID,
            "description": ("F2b cannot be cleanly accepted at b2ab6acb2bbe: H1 and H2 are "
                            "reproduced at the pin, and the two circulating repairs "
                            "(84b5d3fa, 98f9ec83) are not landable because their H2_loc "
                            "replacement asserts the reversed entailment (H3). The two "
                            "worker-029 candidates close H1/H2/H3 but leave the V1 alias token."),
            "needed_to_unblock": ("lead adopts corrected_51c253c4 or nesting_4951cc96 (or flips the "
                                  "entailment clause), re-freezes FROZEN with per-file pins and "
                                  "re-runs the gate; separately rule the F0/VOCAB single-sourcing "
                                  "token conflict (w017-20260912-vocab-source-blocker) or record an "
                                  "explicit waiver"),
            "evidence_refs": [R["results.json"], pins[0], pins[2], pins[3], ck_ref],
        },
        {
            "event_id": PREFIX + "-erratum-checkpoint-ref", "event_type": "status",
            "created_at": ts, "actor": ACTOR, "agent_slot": SLOT, "task_id": TASK_ID,
            "node_id": NODE_ID, "gate": GATE, "class_id": CLASS_ID, "status": "active",
            "hours": 0.05,
            "summary": ("ERRATUM (no measurement changed): (1) the first emitter run wrote the "
                        "worker checkpoint with a wall-clock created_at; an idempotency re-run "
                        "rewrote it (5285b1985fb8 -> 18d88bf03763) while the already-accepted "
                        "review-f2b, claim-adjudication, blocker-f2b-landing and status-complete "
                        "events cite 5285b1985fb8. The checkpoint is now deterministic "
                        "(created_at = results.generated_at) and stable at %s. (2) emit_events.py "
                        "was edited to make that checkpoint deterministic and to add this erratum, "
                        "so manifest.json was rebuilt: its published hash is now %s, superseding "
                        "the artifact-manifest event hash %s. Both new hashes are the binding "
                        "refs; interim checkpoint log lines remain in "
                        "runtime/state/w016_checkpoints.jsonl as provenance."
                        % (ck_ref.split(":")[-1], h["manifest.json"][:12], stale_manifest[:12])),
            "evidence_refs": [ck_ref, R["manifest.json"],
                              "runtime/state/w016_checkpoints.jsonl", R["results.json"]],
            "next_falsifier": ("re-run emit_events.py and confirm the checkpoint hash is unchanged "
                               "and 0 events are appended"),
        },
        {
            "event_id": PREFIX + "-status-complete", "event_type": "status", "created_at": ts,
            "actor": ACTOR, "agent_slot": SLOT, "task_id": TASK_ID, "node_id": NODE_ID,
            "gate": GATE, "class_id": CLASS_ID, "status": "active", "hours": 0.6,
            "summary": ("CHECKPOINT + EXIT. Bounded class-bound task complete at worker level. "
                        "Findings: H1 CONFIRMED, H2 CONFIRMED, H3 CONFIRMED-IN-CANDIDATES, V1 "
                        "CONFIRMED-DIVERGENCE (non-blocking). Landable candidates: corrected_51c253c4, "
                        "nesting_4951cc96. 9/9 pre-registered controls hold, checker exit 0, pins "
                        "stable. Worker checkpoint written; no node completion, no gate verdict, no "
                        "canonical write."),
            "evidence_refs": [R["results.json"], R["REPORT.md"], ck_ref, pins[0], pins[2]],
            "next_falsifier": ("re-run the checker after any F2b/F0/VOCAB write; a new pin with the "
                               "carriers repaired and a correct entailment direction voids this "
                               "finding set"),
        },
    ]

    # append-only, idempotent by event_id
    existing = set()
    if os.path.exists(OUTBOX):
        with open(OUTBOX, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    existing.add(json.loads(line).get("event_id"))
                except Exception:
                    continue
    appended = 0
    with open(OUTBOX, "a", encoding="utf-8") as fh:
        for e in events:
            if e["event_id"] in existing:
                continue
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
            appended += 1
    print("events:", len(events), "appended:", appended, "already present:", len(events) - appended)
    print("checkpoint:", os.path.relpath(CKPT, ROOT), sha(os.path.relpath(CKPT, ROOT))[:12])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
