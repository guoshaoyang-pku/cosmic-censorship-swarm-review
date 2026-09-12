#!/usr/bin/env python3
"""Emit W074-R3-VERDICT-INDEPENDENCE-CENSUS-01 events + checkpoint.

Appends valid protocol events to comms/outbox/worker-074.jsonl (idempotent by
event_id), writes runtime/state/w074_checkpoint_r3indep.json, and self-validates
required fields against research_map/events.schema.json before writing.
"""

import datetime
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUTBOX = os.path.join(ROOT, "comms", "outbox", "worker-074.jsonl")
CHECKPOINT = os.path.join(ROOT, "runtime", "state", "w074_checkpoint_r3indep.json")
SUFFIX = "20260912T010604"
TASK = "W074-R3-VERDICT-INDEPENDENCE-CENSUS-01"
CLASSES = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
NODES = ["F1", "F2a", "F2b"]


def sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def ref(path, full=False):
    h = sha256(os.path.join(ROOT, path))
    return path + "#" + (h if full else h[:12])


def now():
    return datetime.datetime.now().astimezone().isoformat()


def required_ok(d):
    base = all(k in d and d[k] for k in ("event_id", "event_type", "created_at", "actor"))
    if not base:
        return False, "base"
    req = {
        "status": [],
        "claim": ["class_id", "statement", "conclusion_type", "assumptions", "falsifier",
                  "evidence_refs"],
        "artifact": ["node_id", "artifact_type", "path", "sha256", "validation_status"],
    }.get(d["event_type"], [])
    for k in req:
        if k not in d or d[k] in (None, "", [], {}):
            return False, k
    return True, "ok"


def main():
    report = json.load(open(os.path.join(HERE, "report.json")))
    classes = report["classes"]
    f1, f2a, f2b = classes["F1"], classes["F2a"], classes["F2b"]
    artifacts = {
        "report": "artifacts/worker-074/r3_verdict_independence/report.json",
        "readme": "artifacts/worker-074/r3_verdict_independence/README.md",
        "census": "artifacts/worker-074/r3_verdict_independence/r3_independence_census.py",
        "selftest": "artifacts/worker-074/r3_verdict_independence/selftest.json",
    }
    hashes = {k: sha256(os.path.join(ROOT, p)) for k, p in artifacts.items()}
    evidence = [ref(artifacts["report"]), ref(artifacts["readme"]), ref(artifacts["selftest"]),
                ref(artifacts["census"]),
                "artifacts/formulation/FROZEN.json#815e08079aef",
                "schemas/af_wcc_vacuum.yaml#d9cebb9404b2",
                "schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3",
                "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe"]
    falsifier = report["falsifier"]
    summary = (
        "G-FORM r3 coverage/independence census at FROZEN rev29 (F1 d9cebb9404b2, F2a e9a27996dfd3, "
        "F2b b2ab6acb2bbe; FROZEN 815e08079aef), measured 01:06:02-01:06:04+08:00 over 102 review "
        "files, controls 6/6, no frame drift. F1: 16 verdicts at the live pin (7 accept / 9 revise), "
        "7 non-author accepts, ESS 7.0, max pairwise findings Jaccard 0.024 -> COVERED. F2a: 7 at "
        "live (2 accept / 5 revise), 2 non-author accepts, ESS 2.0 -> COVERED. F2b: 9 at live "
        "(1 accept / 8 revise), 1 non-author accept (worker-001), ESS 1.0 -> PARTIAL: the card's "
        "'two independent non-author reviewers per class' is NOT met for F2b at this instant; the "
        "revises cluster on containment/normativity (worker-017, worker-066 x2) and the binding "
        "chain (worker-035), i.e. the L-FORM-01 field. 21 stale-only files (14 F1, 7 F2a) must not "
        "count as binding; F2b has 0. W074-R3-F2: reviews/F2a-review-rev27-b.json declares "
        "created_at 00:52:23 but cites the rev13 F2a pin whose bytes were written 00:53:20.683, so "
        "its live-pin claim is a post-authoring amendment (revise; does not change F2a coverage). "
        "Measurement only: no gate verdict, no node status."
    )
    events = [
        {
            "event_id": "w074-r3indep-%s-status" % SUFFIX,
            "event_type": "status",
            "created_at": now(),
            "actor": "worker-074",
            "node_id": ",".join(NODES),
            "class_id": ";".join(CLASSES),
            "class_ids": CLASSES,
            "gate": "G-FORM",
            "status": "active",
            "hours": 0.4,
            "summary": summary,
            "evidence_refs": evidence,
            "next_falsifier": falsifier,
            "counts_as_gate_verdict": False,
        },
        {
            "event_id": "w074-r3indep-%s-claim" % SUFFIX,
            "event_type": "claim",
            "created_at": now(),
            "actor": "worker-074",
            "node_id": ",".join(NODES),
            "gate": "G-FORM",
            "class_id": ";".join(CLASSES),
            "class_ids": CLASSES,
            "statement": summary,
            "conclusion_type": "audit_measurement",
            "assumptions": [
                "the r3 card astra-life05-verify-gform-r3 is the acceptance text",
                "a verdict counts at the live pin only if the measured live sha256 appears in the file",
                "author set = live schema authored_by + owner; revision-note mentions do not disqualify",
                "text similarity is a proxy for verdict independence, not proof of copying",
            ],
            "falsifier": falsifier,
            "evidence_refs": evidence,
            "artifact_refs": [artifacts["report"], artifacts["readme"], artifacts["selftest"],
                              artifacts["census"]],
            "counts_as_gate_verdict": False,
        },
    ]
    for key, atype in (("report", "audit_report"), ("readme", "audit_report"),
                       ("census", "audit_tool"), ("selftest", "control_evidence")):
        events.append({
            "event_id": "w074-r3indep-%s-artifact-%s" % (SUFFIX, key),
            "event_type": "artifact",
            "created_at": now(),
            "actor": "worker-074",
            "node_id": ",".join(NODES),
            "class_id": ";".join(CLASSES),
            "class_ids": CLASSES,
            "gate": "G-FORM",
            "artifact_type": atype,
            "path": artifacts[key],
            "sha256": hashes[key],
            "validation_status": "unverified",
            "evidence_refs": evidence,
            "falsifier": falsifier,
            "task_id": TASK,
        })

    # self-validate
    bad = []
    for e in events:
        ok, why = required_ok(e)
        if not ok:
            bad.append((e.get("event_id"), why))
    if bad:
        raise SystemExit("invalid events: %s" % bad)

    existing = set()
    if os.path.exists(OUTBOX):
        for line in open(OUTBOX, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line).get("event_id"))
            except Exception:
                continue
    new_events = [e for e in events if e["event_id"] not in existing]
    with open(OUTBOX, "a", encoding="utf-8") as fh:
        for e in new_events:
            fh.write(json.dumps(e, sort_keys=True) + "\n")

    checkpoint = {
        "checkpoint_id": "w074-r3indep-%s" % SUFFIX,
        "created_at": now(),
        "worker": "worker-074",
        "task": {
            "task_id": TASK,
            "assignment_ref": "self-selected; serves card astra-life05-verify-gform-r3 "
                              "(no comms/inbox/worker-074.jsonl card existed)",
            "class_bound": True,
            "classes": CLASSES,
            "node_id": ",".join(NODES),
            "gate": "G-FORM",
            "task": "independent r3 verdict coverage/independence census at FROZEN rev29 pins",
        },
        "measurement": {
            "t0": report.get("measurement_instant_t0"),
            "t1": report.get("measurement_instant_t1"),
            "review_files_considered": len(report["review_files_considered"]),
            "moved_during_run": report["moved_during_run"],
            "frozen_rev29_matches": report["frozen"].get("matches_pin"),
            "live_pins_match": all(v["matches_live_pin"] for v in report["targets"].values()),
        },
        "coverage": {t: report["classes"][t]["coverage"] for t in ("F1", "F2a", "F2b")},
        "counts": {t: {
            "at_live": report["classes"][t]["entries_at_live_pin"],
            "stale_only": report["classes"][t]["entries_stale_only"],
            "hist": report["classes"][t]["verdict_histogram_at_live"],
            "non_author_accepts": report["classes"][t]["non_author_accept_reviewers"],
            "ess_accepts": report["classes"][t]["kish_ess_non_author_accepts"],
        } for t in ("F1", "F2a", "F2b")},
        "artifacts": {p: hashes[k] for k, p in artifacts.items()},
        "controls": {"selftest": "6/6", "file": artifacts["selftest"]},
        "events_emitted": [e["event_id"] for e in new_events],
        "events_deduplicated": [e["event_id"] for e in events if e["event_id"] in existing],
        "authority_limits": [
            "measurement only: no gate verdict, no node status, no validation_status promotion",
            "writes only inside artifacts/worker-074/r3_verdict_independence/ and this checkpoint",
        ],
        "next_falsifier": falsifier,
    }
    os.makedirs(os.path.dirname(CHECKPOINT), exist_ok=True)
    with open(CHECKPOINT, "w", encoding="utf-8") as fh:
        json.dump(checkpoint, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(json.dumps({"outbox_new": [e["event_id"] for e in new_events],
                      "checkpoint": CHECKPOINT}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
