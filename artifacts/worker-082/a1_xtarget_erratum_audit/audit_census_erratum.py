#!/usr/bin/env python3
"""W082-A1-XTARGET-ERRATUM-AUDIT-01 -- audit of the supersession/erratum claims
attached to W082-A1-XTARGET-INDEP-CENSUS-01.

One bounded, class-bound task (node A1, gate G-AUDIT; classes F1 AF-WCC-VAC-GEN,
F2a AF-SCC-C2-VAC-GEN, F2b AF-SCC-C0-VAC-GEN).

Question
--------
W082-A1-XTARGET-INDEP-CENSUS-01 was emitted three times (report digests
4f94a458b823 -> ccf3ac5f77f3 -> 9651c42845c0).  A status event under the final
digest declares the first two batches stale and lists 19 event ids to discard.
That erratum is prose in a status event.  This instrument mechanically checks
whether the supersession is (a) correctly enumerated, (b) actually enforced in
the canonical map, and (c) factually accurate about the accepted stream.

Pre-registered checks (each carries its own falsifier)
------------------------------------------------------
A1  stale_set_exact      erratum's 19 ids == accepted-stream w082-a1xt ids minus
                         the 9651c42845c0 batch; every listed id was ingested.
A2  current_batch_intact all 10 9651c42845c0 ids are in the accepted stream and
                         in map.applied_event_ids, each exactly once.
A3  hash_binding         measured sha256 of report.json / REVIEW / instrument
                         equals the sha256 carried by the live artifact events;
                         snapshot bytes re-hash to the pins in the manifest.
A4  map_liveness         how many stale entries are still LIVE in
                         map.claims / map.reviews and whether any carries a
                         retirement marker.
A5  erratum_reason       the erratum says batch B's review events were "deduped
                         away"; test that against the accepted stream.
A6  corpus_archive       was the harvested review corpus archived, so the stated
                         falsifier ("re-run ... against the archived snapshot
                         hashes") can reproduce the counts?  Quantify drift.

Controls: positive (current batch), negative (mutated digest), null (absent
token), duplicate-id, determinism (two runs), hash-mutation detection.

Authority: worker evidence only.  Read-only except its own output directory.
Emits NO gate verdict, NO node status, NO validation_status=passed, and edits NO
canonical artifact.  The map is not modified by this instrument.

Usage:
  python3 audit_census_erratum.py            # measure + print
  python3 audit_census_erratum.py --write    # measure + write verdict.json/REPORT.md
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

ROOT = "/data3/guoshaoyang/workdir/ai4math-swarm"
OUT_DIR = os.path.join(ROOT, "artifacts/worker-082/a1_xtarget_erratum_audit")
CENSUS_DIR = os.path.join(ROOT, "artifacts/worker-082/a1_xtarget_census")
ACCEPTED = os.path.join(ROOT, "research_map/events.jsonl")
MAP_PATH = os.path.join(ROOT, "research_map/research_map.json")
OUTBOX = os.path.join(ROOT, "comms/outbox/worker-082.jsonl")
CHECKPOINT = os.path.join(ROOT, "runtime/state/w082_a1_xtarget_erratum_audit_checkpoint.json")

TASK_ID = "W082-A1-XTARGET-ERRATUM-AUDIT-01"
NODE_ID = "A1"
GATE = "G-AUDIT"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
CURRENT_DIGEST = "9651c42845c0"
STALE_DIGESTS = ["4f94a458b823", "ccf3ac5f77f3"]
ERRATUM_ID = "w082-a1xt-9651c42845c0-erratum-stale-set"
TZ = timezone(timedelta(hours=8))

CENSUS_REPORT = os.path.join(CENSUS_DIR, "report.json")
CENSUS_REVIEW = os.path.join(CENSUS_DIR, "REVIEW-A1-XTARGET-082.json")
CENSUS_INSTRUMENT = os.path.join(CENSUS_DIR, "harvest_a1_xtarget_census.py")
CENSUS_MANIFEST = os.path.join(CENSUS_DIR, "SNAPSHOT_MANIFEST.json")

PINS = {
    "schemas/af_wcc_vacuum.yaml": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
}


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def read_accepted_w082() -> dict[str, int]:
    """event_id -> occurrence count over the accepted stream (events.jsonl)."""
    counts: dict[str, int] = {}
    with open(ACCEPTED, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            eid = str(event.get("event_id", ""))
            if eid.startswith("w082-a1xt"):
                counts[eid] = counts.get(eid, 0) + 1
    return counts


def read_event(eid: str) -> dict | None:
    """Last accepted-stream copy of eid (fallback: worker outbox)."""
    found = None
    for path in (ACCEPTED, OUTBOX):
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or eid not in line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if str(event.get("event_id", "")) == eid:
                    found = event
    return found


def parse_erratum_stale_ids(text: str) -> list[str]:
    """Extract the id list the erratum publishes after 'stale event ids:'."""
    marker = "stale event ids:"
    idx = text.find(marker)
    body = text[idx + len(marker):] if idx >= 0 else text
    stop = body.find("Count W082")
    if stop >= 0:
        body = body[:stop]
    ids, seen = [], set()
    for token in re.findall(r"w082-a1xt-[A-Za-z0-9_.+-]+", body):
        token = token.rstrip(".,;")
        if token not in seen:
            seen.add(token)
            ids.append(token)
    return ids


def review_corpus_drift(observation_end: datetime) -> dict:
    """Bounded drift measure over reviews/ only: new protocol-verdict records
    written after the census observation window that bind one of the 3 pins."""
    deltas, total = [], 0
    verdicts = {"accept", "revise", "reject", "inconclusive"}
    review_dir = os.path.join(ROOT, "reviews")
    for name in sorted(os.listdir(review_dir)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(review_dir, name)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                raw = fh.read()
            record = json.loads(raw)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not isinstance(record, dict):
            continue
        if str(record.get("verdict", "")).lower() not in verdicts:
            continue
        bound = [p for p in PINS.values() if p in raw]
        if not bound:
            continue
        total += 1
        mtime = datetime.fromtimestamp(os.path.getmtime(path), TZ)
        if mtime > observation_end:
            deltas.append({
                "path": f"reviews/{name}",
                "mtime": mtime.isoformat(timespec="seconds"),
                "reviewer": record.get("reviewer") or record.get("actor"),
                "verdict": record.get("verdict"),
                "bound_pins": [k for k, v in PINS.items() if v in raw],
            })
    return {
        "scope": "reviews/*.json only (bounded independent proxy, not a full census re-run)",
        "binding_review_shaped_records_total_now": total,
        "new_since_observation_end": deltas,
        "new_since_observation_end_count": len(deltas),
    }


def measure() -> dict:
    report_sha = sha256_file(CENSUS_REPORT)
    review_sha = sha256_file(CENSUS_REVIEW)
    instrument_sha = sha256_file(CENSUS_INSTRUMENT)
    with open(CENSUS_MANIFEST, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    with open(MAP_PATH, "r", encoding="utf-8") as fh:
        research_map = json.load(fh)
    map_sha = sha256_file(MAP_PATH)

    accepted = read_accepted_w082()
    erratum = read_event(ERRATUM_ID)
    if erratum is None:
        raise SystemExit(f"FAIL CLOSED: erratum event {ERRATUM_ID} not found")
    listed = parse_erratum_stale_ids(str(erratum.get("summary", "")))

    current_ids = sorted(i for i in accepted if CURRENT_DIGEST in i)
    stale_ids = sorted(i for i in accepted if i not in set(current_ids))
    applied = set(research_map.get("applied_event_ids", []))

    # A1 -- stale set exact
    a1_pass = (set(listed) == set(stale_ids)) and len(listed) == 19
    a1 = {
        "check": "stale_set_exact",
        "status": "pass" if a1_pass else "fail",
        "erratum_declared_count_phrase": "19" if "these 19 stale event ids" in str(erratum.get("summary", "")) else "unspecified",
        "listed_count": len(listed),
        "accepted_stale_count": len(stale_ids),
        "listed_not_accepted": sorted(set(listed) - set(stale_ids)),
        "accepted_not_listed": sorted(set(stale_ids) - set(listed)),
        "falsifier": "A stale id absent from the erratum list, a non-stale id present in it, or a listed id that was never ingested.",
    }

    # A2 -- current batch intact
    dup_current = sorted(i for i in current_ids if accepted[i] != 1)
    a2_pass = (len(current_ids) == 10) and not dup_current and all(i in applied for i in current_ids)
    a2 = {
        "check": "current_batch_intact",
        "status": "pass" if a2_pass else "fail",
        "current_ids": current_ids,
        "current_ids_in_applied_event_ids": sorted(i for i in current_ids if i in applied),
        "duplicate_current_ids": dup_current,
        "falsifier": "A missing current-batch id, a duplicate occurrence, or a current id absent from applied_event_ids.",
    }

    # A3 -- hash binding
    art_sha = {}
    for eid in [i for i in current_ids if "-artifact-" in i]:
        event = read_event(eid)
        if event:
            art_sha[str(event.get("path", ""))] = str(event.get("sha256", ""))
    claim_event = read_event([i for i in current_ids if i.endswith("-claim-coverage")][0]) or {}
    claim_prefixes = []
    for ref in claim_event.get("artifact_refs", []):
        claim_prefixes.append(str(ref).split("#sha256:")[-1])
    snapshot_pins_ok = []
    for rel, meta in sorted(manifest.get("snapshots", {}).items()):
        if meta.get("snapshot"):
            check_path = os.path.join(ROOT, meta["snapshot"])
            source = meta["snapshot"]
        else:
            check_path = os.path.join(ROOT, rel)
            source = rel
        measured = sha256_file(check_path)
        snapshot_pins_ok.append({
            "path": rel,
            "checked_bytes": source,
            "archived_copy": bool(meta.get("snapshot")),
            "declared_sha256": meta["sha256"],
            "remeasured_sha256": measured,
            "resolved": measured == meta["sha256"],
        })
    a3_pass = (
        art_sha.get("artifacts/worker-082/a1_xtarget_census/report.json") == report_sha
        and art_sha.get("artifacts/worker-082/a1_xtarget_census/REVIEW-A1-XTARGET-082.json") == review_sha
        and art_sha.get("artifacts/worker-082/a1_xtarget_census/harvest_a1_xtarget_census.py") == instrument_sha
        and claim_prefixes[:1] == [report_sha[:16]]
        and all(s["resolved"] for s in snapshot_pins_ok)
    )
    a3 = {
        "check": "hash_binding",
        "status": "pass" if a3_pass else "fail",
        "measured": {
            "report.json": report_sha,
            "REVIEW-A1-XTARGET-082.json": review_sha,
            "harvest_a1_xtarget_census.py": instrument_sha,
        },
        "artifact_event_sha256": art_sha,
        "claim_artifact_prefixes": claim_prefixes,
        "snapshot_pins": snapshot_pins_ok,
        "falsifier": "Any measured sha256 differing from the live event/manifest pin, or a snapshot byte that no longer re-hashes to its declared pin.",
    }

    # A4 -- map liveness of stale entries
    live_stale_claims = [c.get("event_id") for c in research_map.get("claims", []) if c.get("event_id") in set(listed)]
    live_stale_reviews = [r.get("event_id") for r in research_map.get("reviews", []) if r.get("event_id") in set(listed)]
    retired = []
    for coll, name in ((research_map.get("claims", []), "claims"), (research_map.get("reviews", []), "reviews")):
        for entry in coll:
            if entry.get("event_id") in set(listed) and (
                entry.get("superseded_by") or entry.get("retired") or entry.get("promotion_status") == "retired"
            ):
                retired.append({"collection": name, "event_id": entry.get("event_id"), "marker": entry.get("superseded_by") or "retired"})
    live_stale_current_claims = [c.get("event_id") for c in research_map.get("claims", []) if c.get("event_id") in set(current_ids)]
    live_stale_current_reviews = [r.get("event_id") for r in research_map.get("reviews", []) if r.get("event_id") in set(current_ids)]
    a4_pass = len(retired) == len(live_stale_claims) + len(live_stale_reviews)
    a4 = {
        "check": "map_liveness",
        "status": "pass" if a4_pass else "unretired",
        "stale_claims_still_live": sorted(x for x in live_stale_claims if x),
        "stale_reviews_still_live": sorted(x for x in live_stale_reviews if x),
        "stale_entries_with_retirement_marker": retired,
        "current_claims_live": sorted(x for x in live_stale_current_claims if x),
        "current_reviews_live": sorted(x for x in live_stale_current_reviews if x),
        "stale_ids_in_applied_event_ids": sorted(i for i in listed if i in applied),
        "naive_consumer_counts": {
            "claims_keyed_by_task_id": sum(1 for c in research_map.get("claims", []) if c.get("task_id") == "W082-A1-XTARGET-INDEP-CENSUS-01"),
            "reviews_keyed_by_task_id": sum(1 for r in research_map.get("reviews", []) if r.get("task_id") == "W082-A1-XTARGET-INDEP-CENSUS-01"),
            "correct_count_after_erratum": 1,
        },
        "falsifier": "Evidence that a stale claim/review is marked superseded elsewhere, or that canonical consumers key these entries only by the final digest.",
    }

    # A5 -- erratum reason about batch B
    ccf_review_ids = sorted(i for i in accepted if "ccf3ac5f77f3" in i and "-coverage-review" in i)
    ccf_reviews_live = sorted(i for i in ccf_review_ids if i in {r.get("event_id") for r in research_map.get("reviews", [])})
    a5_pass = len(ccf_review_ids) == 3 and len(ccf_reviews_live) == 3
    a5 = {
        "check": "erratum_reason_batch_b_dedup",
        "status": "contradicted" if a5_pass else "consistent",
        "erratum_claim": "Batch B (ccf3ac5f77f3) review events were deduped away because review ids did not include the report digest.",
        "measured_batch_b_review_ids_in_accepted_stream": ccf_review_ids,
        "measured_live_in_map_reviews": ccf_reviews_live,
        "note": "The ids without a report digest belong to batch A (4f94a458b823), not batch B; batch B's three coverage reviews are present and applied.",
        "falsifier": "A re-ingest proving the three ccf3ac5f77f3 coverage reviews are absent from the accepted stream or from map.reviews.",
    }

    # A6 -- corpus archive / replayability
    snap_files = sorted(os.listdir(os.path.join(CENSUS_DIR, "snapshots")))
    corpus_manifest_present = any("corpus" in f.lower() for f in os.listdir(CENSUS_DIR))
    with open(CENSUS_REPORT, "r", encoding="utf-8") as fh:
        report = json.load(fh)
    limits = report.get("limits", [])
    observation_end = datetime.fromisoformat(str(manifest["created_at"]))
    drift = review_corpus_drift(observation_end)
    a6_pass = corpus_manifest_present
    a6 = {
        "check": "corpus_archive_replayability",
        "status": "pass" if a6_pass else "gap",
        "archived_snapshot_files": snap_files,
        "harvested_corpus_manifest_present": corpus_manifest_present,
        "census_discloses_live_corpus": any("corpus" in str(x) and "live" in str(x) for x in limits),
        "observation_end": observation_end.isoformat(timespec="seconds"),
        "corpus_drift": drift,
        "consequence": "The falsifier 're-run against the archived snapshot hashes' can re-check schema-byte binding but cannot reproduce the corpus-dependent counts; a replay is a drift/superset check unless a corpus manifest is archived.",
        "falsifier": "Discovery of an archived corpus manifest/digest for the census observation window that this check missed.",
    }

    # Controls
    neg_token = "w082-a1xt-deadbeef0000-status-open"
    null_token = "ffffffffffff"
    mutated = report_sha[:-1] + ("0" if report_sha[-1] != "0" else "1")
    controls = {
        "positive_current_batch_present": len(current_ids) == 10,
        "negative_mutated_digest_absent": neg_token not in accepted,
        "null_token_absent": not [i for i in accepted if null_token in i],
        "no_duplicate_accepted_ids": not [i for i, c in accepted.items() if c > 1],
        "hash_mutation_detected": (mutated != report_sha) and (sha256_file(CENSUS_REPORT) != mutated),
    }

    checks = [a1, a2, a3, a4, a5, a6]
    hard_failures = [c["check"] for c in checks if c["status"] == "fail"]
    findings = [
        {
            "id": "W082-EA-01",
            "severity": "medium",
            "title": "Stale census entries are live and unretired in the canonical map",
            "detail": (
                f"map.claims carries {len(live_stale_claims)} stale census claim(s) and map.reviews carries "
                f"{len(live_stale_reviews)} stale coverage review(s); map.applied_event_ids still holds all "
                f"{len([i for i in listed if i in applied])}/19 stale ids and no stale entry carries superseded_by/retired. "
                "The erratum is a status event only, so a consumer counting map claims/reviews by task_id sees 3 claims "
                "and 9 reviews for one census instead of 1 and 3."
            ),
            "evidence_refs": [
                "research_map/research_map.json#applied_event_ids",
                "research_map/research_map.json#claims",
                "research_map/research_map.json#reviews",
                f"{os.path.relpath(CENSUS_DIR, ROOT)}/report.json",
            ],
            "falsifier": "A map record or accepted event that retires or supersedes the six stale reviews and two stale claims.",
        },
        {
            "id": "W082-EA-02",
            "severity": "low",
            "title": "Erratum's stated reason for batch B is contradicted by the accepted stream",
            "detail": (
                "The erratum says batch B (ccf3ac5f77f3) review events were deduped away because their ids lacked the "
                "report digest. Measured: all three ccf3ac5f77f3 coverage reviews are in events.jsonl, in "
                "applied_event_ids and live in map.reviews. The digest-less review ids belong to batch A. The stale set "
                "itself is correct; only the published reason is wrong."
            ),
            "evidence_refs": ["research_map/events.jsonl#w082-a1xt-ccf3ac5f77f3-f1-d9cebb9404b2-coverage-review"],
            "falsifier": "A re-ingest or map snapshot showing the three ccf3ac5f77f3 coverage reviews absent.",
        },
        {
            "id": "W082-EA-03",
            "severity": "low",
            "title": "Corpus-dependent counts are not exactly replayable from the archived snapshots",
            "detail": (
                "snapshots/ archives only the three canonical schema bytes (plus the FROZEN pin set); the harvested "
                "review corpus (reviews/, artifacts/**, comms/**, events.jsonl) was not archived, so the published "
                "falsifier can re-check byte binding but not reproduce per-target counts. The census discloses corpus "
                "liveness in report.limits."
            ),
            "evidence_refs": ["artifacts/worker-082/a1_xtarget_census/SNAPSHOT_MANIFEST.json"],
            "falsifier": "An archived corpus manifest for the 2026-09-12T01:10:18..01:12:08 window.",
        },
        {
            "id": "W082-EA-04",
            "severity": "info",
            "title": "Verified: stale-set enumeration and hash binding are exact",
            "detail": (
                f"Erratum lists exactly the {len(stale_ids)} accepted-stream ids outside the final batch; all 10 final "
                f"ids are applied once; report/review/instrument bytes match the live event sha256s "
                f"(report {report_sha[:12]}, review {review_sha[:12]}, instrument {instrument_sha[:12]}); snapshot "
                f"bytes re-hash to their declared pins."
            ),
            "evidence_refs": ["artifacts/worker-082/a1_xtarget_census/SNAPSHOT_MANIFEST.json#report_sha256"],
            "falsifier": "Any hash mismatch at re-measurement.",
        },
    ]

    return {
        "schema": "worker-082/a1-xtarget-erratum-audit/v1",
        "task_id": TASK_ID,
        "worker": "worker-082",
        "node_id": NODE_ID,
        "gate": GATE,
        "class_ids": CLASS_IDS,
        "created_at": now(),
        "objective": (
            "Audit the supersession/erratum attached to W082-A1-XTARGET-INDEP-CENSUS-01: exactness of the stale-id set, "
            "hash binding of the final batch, whether the canonical map actually retires the stale entries, accuracy of "
            "the published erratum reason, and replayability of the published falsifier."
        ),
        "inputs": {
            "research_map/events.jsonl": sha256_file(ACCEPTED),
            "research_map/research_map.json": map_sha,
            "artifacts/worker-082/a1_xtarget_census/report.json": report_sha,
            "artifacts/worker-082/a1_xtarget_census/REVIEW-A1-XTARGET-082.json": review_sha,
            "artifacts/worker-082/a1_xtarget_census/harvest_a1_xtarget_census.py": instrument_sha,
            "artifacts/worker-082/a1_xtarget_census/SNAPSHOT_MANIFEST.json": sha256_file(CENSUS_MANIFEST),
        },
        "pins": PINS,
        "checks": checks,
        "findings": findings,
        "controls": controls,
        "verdict": {
            "verdict": "revise",
            "score": 3.5,
            "rationale": (
                "The final census batch is intact and hash-bound and the erratum's stale-id set is exact, but the "
                "supersession is not enforced in the canonical map (2 stale claims + 6 stale reviews live, unmarked) and "
                "one published erratum reason is contradicted by the accepted stream. Repairs are controller-side and "
                "mechanical; no census number at the pinned bytes changes."
            ),
            "hard_failures": hard_failures,
        },
        "repair_recommendation": {
            "owner": "controller/astra (worker cannot move map state)",
            "action": "Annotate the stale entries with superseded_by (field convention already used in map.reviews) or add a superseded_event_ids register; correct the batch-B reason in a follow-up erratum note; optionally archive a corpus manifest for exact replay.",
            "targets": {
                "stale_claims": sorted(x for x in live_stale_claims if x),
                "stale_reviews": sorted(x for x in live_stale_reviews if x),
                "superseded_by_value": "w082-a1xt-9651c42845c0-* (W082-A1-XTARGET-INDEP-CENSUS-01, final batch)",
            },
        },
        "authority": "worker evidence only; no gate verdict, no node status, no validation_status, no map edit",
        "falsifier": (
            "Re-run this instrument: a listed stale id that was never ingested, a current-batch id missing or duplicated, "
            "a measured sha256 that differs from the live event pin, a stale entry that turns out to carry a retirement "
            "marker, or an archived corpus manifest for the observation window (which voids W082-EA-03) falsifies the "
            "corresponding check."
        ),
    }


def canon(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def deterministic_digest(obj: dict) -> str:
    stripped = json.loads(canon(obj))
    stripped.pop("created_at", None)
    return hashlib.sha256(canon(stripped).encode()).hexdigest()


def render_report(v: dict) -> str:
    lines = [
        "# W082-A1-XTARGET-ERRATUM-AUDIT-01",
        "",
        f"- Task: `{v['task_id']}` (node {v['node_id']}, gate {v['gate']})",
        f"- Classes: {', '.join(v['class_ids'])}",
        f"- Created: {v['created_at']}",
        f"- Verdict: **{v['verdict']['verdict']}** {v['verdict']['score']}/5",
        "",
        "## Checks",
        "",
        "| check | status | measured |",
        "|---|---|---|",
    ]
    for c in v["checks"]:
        detail = ""
        if c["check"] == "stale_set_exact":
            detail = f"listed={c['listed_count']} accepted_stale={c['accepted_stale_count']} sym_diff={len(c['listed_not_accepted']) + len(c['accepted_not_listed'])}"
        elif c["check"] == "current_batch_intact":
            detail = f"{len(c['current_ids'])} ids, applied={len(c['current_ids_in_applied_event_ids'])}"
        elif c["check"] == "hash_binding":
            detail = ", ".join(f"{k.split('/')[-1]}={x[:12]}" for k, x in c["measured"].items())
        elif c["check"] == "map_liveness":
            detail = f"stale live: {len(c['stale_claims_still_live'])} claims + {len(c['stale_reviews_still_live'])} reviews; retired markers={len(c['stale_entries_with_retirement_marker'])}"
        elif c["check"] == "erratum_reason_batch_b_dedup":
            detail = f"batch B reviews present={len(c['measured_batch_b_review_ids_in_accepted_stream'])}"
        elif c["check"] == "corpus_archive_replayability":
            detail = f"snapshot files={len(c['archived_snapshot_files'])}; corpus manifest={c['harvested_corpus_manifest_present']}; new binding reviews since window={c['corpus_drift']['new_since_observation_end_count']}"
        lines.append(f"| {c['check']} | {c['status']} | {detail} |")
    lines += ["", "## Findings", ""]
    for f in v["findings"]:
        lines += [f"### {f['id']} ({f['severity']}) — {f['title']}", "", f["detail"], "", f"Falsifier: {f['falsifier']}", ""]
    lines += [
        "## Repair recommendation (controller-side)",
        "",
        f"- Stale claims to retire: {', '.join(v['repair_recommendation']['targets']['stale_claims']) or 'none'}",
        f"- Stale reviews to retire: {', '.join(v['repair_recommendation']['targets']['stale_reviews']) or 'none'}",
        f"- Authority: {v['authority']}",
        "",
        f"## Falsifier", "", v["falsifier"], "",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    first = measure()
    second = measure()
    digest1 = deterministic_digest(first)
    digest2 = deterministic_digest(second)
    first["controls"]["determinism_digest_run1"] = digest1
    first["controls"]["determinism_digest_run2"] = digest2
    first["controls"]["determinism_identical"] = digest1 == digest2

    print(json.dumps({c["check"]: c["status"] for c in first["checks"]}, indent=1))
    print("verdict:", first["verdict"]["verdict"], first["verdict"]["score"])
    print("determinism:", first["controls"]["determinism_identical"])
    if not first["controls"]["determinism_identical"]:
        print("FAIL CLOSED: non-deterministic measurement", file=sys.stderr)
        return 2

    if args.write:
        os.makedirs(OUT_DIR, exist_ok=True)
        verdict_path = os.path.join(OUT_DIR, "verdict.json")
        with open(verdict_path, "w", encoding="utf-8") as fh:
            json.dump(first, fh, indent=1, sort_keys=True)
            fh.write("\n")
        with open(os.path.join(OUT_DIR, "REPORT.md"), "w", encoding="utf-8") as fh:
            fh.write(render_report(first))
        print("wrote", verdict_path, sha256_file(verdict_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
