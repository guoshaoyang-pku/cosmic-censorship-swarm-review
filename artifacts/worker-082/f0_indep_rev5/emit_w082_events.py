#!/usr/bin/env python3
"""Emit W082-A1-F0-INDEP-REV5-01 events to comms/outbox/worker-082.jsonl (content-idempotent).

Idempotency incident + fix (2026-09-12T00:50+08:00): the first version keyed idempotency on the
exact `event_id`, which embedded a wall-clock stamp.  A second run produced a new stamp and
re-emitted the delivery under new ids, so events 004927 and 005005 are byte-equivalent in content
but distinct in the stream.  This version keys idempotency on event *content* (artifact path /
review_id / status suffix) so re-runs cannot re-emit, and emits one stable-id correction note
(`w082-f0-indep-dedup-note`) telling downstream consumers to count the delivery once.

Worker authority: status stays `active`; no gate verdict, no node status=done, no
validation_status=passed.  Each event is validated against research_map/schemas.py before append.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

ROOT = "/data3/guoshaoyang/workdir/ai4math-swarm"
OUT_DIR = os.path.join(ROOT, "artifacts/worker-082/f0_indep_rev5")
OUTBOX = os.path.join(ROOT, "comms/outbox/worker-082.jsonl")
TZ = timezone(timedelta(hours=8))
TASK = "W082-A1-F0-INDEP-REV5-01"
F0 = "research_map/formulation_taxonomy.yaml"
F0_SHA = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
STAMP_RE = re.compile(r"^w082-\d{8}T\d{6}[+-]\d{4}-(.+)$")

sys.path.insert(0, os.path.join(ROOT, "research_map"))
from schemas import validate_event  # noqa: E402


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def dedup_key(event):
    suffix = None
    m = STAMP_RE.match(str(event.get("event_id", "")))
    if m:
        suffix = m.group(1)
    if event.get("event_type") == "artifact":
        return "artifact:" + str(event.get("path"))
    if event.get("event_type") == "review":
        return "review:" + str(event.get("review_id") or event.get("target_id"))
    return "status:" + str(suffix or event.get("event_id"))


def load_existing():
    keys = set()
    if os.path.exists(OUTBOX):
        for line in open(OUTBOX):
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            if isinstance(e, dict):
                keys.add(dedup_key(e))
    return keys


def main():
    stamp = datetime.now(TZ).strftime("%Y%m%dT%H%M%S%z")
    ev = json.load(open(os.path.join(OUT_DIR, "evidence.json")))
    rv = json.load(open(os.path.join(OUT_DIR, "REVIEW-F0-INDEP-082.json")))
    art = {
        "evidence.json": (os.path.join(OUT_DIR, "evidence.json"), "evidence_bundle"),
        "REVIEW-F0-INDEP-082.json": (os.path.join(OUT_DIR, "REVIEW-F0-INDEP-082.json"), "review"),
        "harvest_f0_independence.py": (os.path.join(OUT_DIR, "harvest_f0_independence.py"), "instrument"),
        "REPORT.md": (os.path.join(OUT_DIR, "REPORT.md"), "report"),
    }
    hashes = {k: sha256_file(p) for k, (p, _) in art.items()}
    reviews_copy = os.path.join(ROOT, "reviews/F0-indep-082-rev5.json")
    if os.path.exists(reviews_copy):
        hashes["reviews/F0-indep-082-rev5.json"] = sha256_file(reviews_copy)
    adj = ev["adjudication"]
    m = ev["measurement"]
    now = datetime.now(TZ).isoformat(timespec="seconds")

    events = [{
        "event_id": f"w082-{stamp}-status-f0-indep-open",
        "event_type": "status",
        "created_at": now,
        "actor": "worker-082",
        "node_id": "F0",
        "class_id": rv["class_id"],
        "status": "active",
        "hours": 0.3,
        "summary": (f"{TASK} opened: independent review-independence census at the pinned F0 rev5 "
                    f"{F0_SHA[:12]} (observer window {ev['observation_window'][0]}..{ev['observation_window'][1]}). "
                    "Measures how many mutually independent accept verdicts exist after channel-copy collapse, "
                    "the protocol same-text dedup rule and author exclusion. No gate verdict."),
        "evidence_refs": [f"{F0}#sha256:{F0_SHA[:12]}", "artifacts/worker-082/f0_indep_rev5/evidence.json"],
        "next_falsifier": rv["falsifier"],
    }]

    for name, (path, atype) in art.items():
        events.append({
            "event_id": f"w082-{stamp}-artifact-f0-indep-{name.replace('.', '-')}",
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-082",
            "node_id": "F0",
            "class_id": rv["class_id"],
            "artifact_type": atype,
            "path": f"artifacts/worker-082/f0_indep_rev5/{name}",
            "sha256": hashes[name],
            "validation_status": "unverified",
            "summary": f"{TASK} artifact ({atype})",
            "evidence_refs": [f"{F0}#sha256:{F0_SHA[:12]}"],
            "next_falsifier": rv["falsifier"],
        })

    review_event = dict(rv)
    review_event["event_id"] = f"w082-{stamp}-review-f0-indep"
    review_event["created_at"] = now
    events.append(review_event)

    if "reviews/F0-indep-082-rev5.json" in hashes:
        events.append({
            "event_id": f"w082-{stamp}-artifact-f0-indep-review-store-copy",
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-082",
            "node_id": "F0",
            "class_id": rv["class_id"],
            "artifact_type": "review",
            "path": "reviews/F0-indep-082-rev5.json",
            "sha256": hashes["reviews/F0-indep-082-rev5.json"],
            "validation_status": "unverified",
            "summary": f"{TASK} canonical review-store copy (scoped; counts_as_full_schema_verdict=false)",
            "evidence_refs": [f"{F0}#sha256:{F0_SHA[:12]}"],
            "next_falsifier": rv["falsifier"],
        })

    events.append({
        "event_id": "w082-f0-indep-dedup-note",
        "event_type": "status",
        "created_at": now,
        "actor": "worker-082",
        "node_id": "F0",
        "class_id": rv["class_id"],
        "status": "active",
        "hours": 0.05,
        "summary": (
            f"{TASK} idempotency correction: the delivery was emitted twice under wall-clock event-id "
            "stamps 004927 and 005005 because the first emitter keyed idempotency on the exact event_id. "
            "The two sets are content-identical (same artifact paths and sha256, same review_id "
            "W082-A1-F0-INDEP-REV5-01, same scoped verdict). Downstream consumers: count the delivery ONCE, "
            "keyed by review_id W082-A1-F0-INDEP-REV5-01 / artifact path; do not count it as two F0 accepts. "
            "The emitter is fixed to content-keyed idempotency in "
            "artifacts/worker-082/f0_indep_rev5/emit_w082_events.py."
        ),
        "evidence_refs": [
            f"artifacts/worker-082/f0_indep_rev5/REVIEW-F0-INDEP-082.json#sha256:{hashes['REVIEW-F0-INDEP-082.json'][:16]}",
            f"artifacts/worker-082/f0_indep_rev5/evidence.json#sha256:{hashes['evidence.json'][:16]}",
            f"{F0}#sha256:{F0_SHA[:12]}",
        ],
        "next_falsifier": ("If any downstream count reports two independent F0 accepts from worker-082 for this "
                           "task, or if the two stamped sets differ in any artifact sha256, this correction is void."),
    })

    existing = load_existing()
    appended, skipped = 0, 0
    with open(OUTBOX, "a") as fh:
        for e in events:
            clean = {k: v for k, v in e.items() if not k.startswith("_")}
            validate_event(json.loads(json.dumps(clean)))
            if dedup_key(clean) in existing:
                skipped += 1
                continue
            fh.write(json.dumps(clean, sort_keys=True) + "\n")
            existing.add(dedup_key(clean))
            appended += 1
    print(f"appended={appended} skipped={skipped} -> {os.path.relpath(OUTBOX, ROOT)}")
    for e in events:
        print(" ", dedup_key(e), "|", e["event_id"])

    # worker checkpoint (own file; the controller's checkpoint.py owns current_checkpoint.json)
    ckpt = {
        "checkpoint_id": f"w082-f0indep-ckpt-{datetime.now(TZ).strftime('%Y%m%dT%H%M%S')}",
        "task_id": TASK,
        "worker": "worker-082",
        "node_id": "F0",
        "gate": "G-F0",
        "class_ids": rv["class_ids"],
        "created_at": now,
        "status": "delivered-active (worker cannot set done/gate verdict)",
        "result": (f"{adj['distinct_accept_reviewers']} distinct accept reviewers at F0 rev5 {F0_SHA[:12]}; "
                   f"ESS {m['kish_ess_accepts']}; max pairwise Jaccard {m['max_pairwise_jaccard']}; "
                   f"{len(adj['duplicate_pairs_at_R1'])} pair(s) >=0.50; worker review verdict accept; "
                   "audit evidence only, counts_as_full_schema_verdict=false"),
        "checks": ("reviewer-level channel-copy collapse; author exclusion; text-dedup R1=0.50; independence "
                   "R2=0.30; controls clone 0.9956 / null 0.0 / cross 0.0023; determinism True"),
        "observation_window": ev["observation_window"],
        "artifacts": dict(
            {f"artifacts/worker-082/f0_indep_rev5/{k}": v for k, v in hashes.items()
             if not k.startswith("reviews/")},
            **{k: v for k, v in hashes.items() if k.startswith("reviews/")},
            **({"artifacts/worker-082/f0_indep_rev5/README.md":
                sha256_file(os.path.join(OUT_DIR, "README.md"))}
               if os.path.exists(os.path.join(OUT_DIR, "README.md")) else {}),
            **{"artifacts/worker-082/f0_indep_rev5/emit_w082_events.py":
               sha256_file(os.path.join(OUT_DIR, "emit_w082_events.py"))},
        ),
        "pinned_targets": {
            F0: ev["pins_end"][F0]["sha256"],
            "artifacts/formulation/formulation_taxonomy.yaml": ev["pins_end"]["artifacts/formulation/formulation_taxonomy.yaml"]["sha256"],
            "artifacts/formulation/FROZEN.json": ev["pins_end"]["artifacts/formulation/FROZEN.json"]["sha256"],
        },
        "canonical_review_id": rv["review_id"],
        "event_duplication": {
            "status": "self-reported; content-identical duplicate set",
            "first_set_stamp": "20260912T004927+0800",
            "duplicate_set_stamp": "20260912T005005+0800",
            "dedup_instruction": "count once by review_id W082-A1-F0-INDEP-REV5-01 / artifact path",
            "correction_event_id": "w082-f0-indep-dedup-note",
        },
        "outbox_canonical_set": [
            "w082-20260912T004927+0800-status-f0-indep-open",
            "w082-20260912T004927+0800-artifact-f0-indep-evidence-json",
            "w082-20260912T004927+0800-artifact-f0-indep-REVIEW-F0-INDEP-082-json",
            "w082-20260912T004927+0800-artifact-f0-indep-harvest_f0_independence-py",
            "w082-20260912T004927+0800-artifact-f0-indep-REPORT-md",
            "w082-20260912T004927+0800-review-f0-indep",
            "w082-20260912T004927+0800-artifact-f0-indep-review-store-copy",
            "w082-20260912T004927+0800-status-f0-indep-delivered",
            "w082-f0-indep-dedup-note",
        ],
        "next_falsifier": rv["next_falsifier"],
        "known_minor_defects": [
            "W082-F0I-02 prose parenthetical in the frozen REVIEW/REPORT enumerates three of the four "
            "full-schema accept reviewers (omits worker-078). The authoritative structured data is "
            "evidence.json measurement.accepts[*].counts_as_full_schema_verdict and the REPORT accept table: "
            "worker-025, worker-038, worker-078, worker-087 are true."
        ],
        "authority": "worker evidence only; no gate verdict, no node status=done, no validation_status=passed",
    }
    ckpt_path = os.path.join(ROOT, "runtime/state/w082_f0_indep_rev5_checkpoint.json")
    with open(ckpt_path, "w") as fh:
        json.dump(ckpt, fh, indent=1, sort_keys=True)
    with open(os.path.join(ROOT, "runtime/state/w082_f0_indep_checkpoints.jsonl"), "a") as fh:
        fh.write(json.dumps(ckpt, sort_keys=True) + "\n")
    print("checkpoint ->", os.path.relpath(ckpt_path, ROOT))


if __name__ == "__main__":
    main()
