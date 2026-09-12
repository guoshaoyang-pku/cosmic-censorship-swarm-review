#!/usr/bin/env python3
"""Emit worker-073's L1 spot-check #4 events and checkpoint.

Reads the final artifact, re-verifies both the artifact hash and the pinned
ledger hash (fail-closed), then writes:
  * comms/outbox/worker-073.jsonl        (artifact + review + status events)
  * runtime/state/w073_checkpoint_1.json (bounded-worker checkpoint)
Never edits the ledger and never claims a gate verdict or node done-status.
"""
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone

ROOT = "/data3/guoshaoyang/workdir/ai4math-swarm"
ART = os.path.join(ROOT, "artifacts/worker-073/l1_spotcheck/spotcheck-l1-073.json")
SCRIPT = os.path.join(ROOT, "artifacts/worker-073/l1_spotcheck/run_spotcheck_073.py")
FETCHLOG = os.path.join(ROOT, "artifacts/worker-073/l1_spotcheck/fetch_log.jsonl")
LEDGER = os.path.join(ROOT, "ledger/citation_audit.csv")
OUTBOX = os.path.join(ROOT, "comms/outbox/worker-073.jsonl")
CHECKPOINT = os.path.join(ROOT, "runtime/state/w073_checkpoint_1.json")
PINNED = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
CLASSES = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
TZ = timezone(timedelta(hours=8))


def now():
    return datetime.now(TZ).isoformat(timespec="seconds")


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if not os.path.isfile(ART):
        print("artifact missing", file=sys.stderr)
        return 2
    art = json.load(open(ART, encoding="utf-8"))
    art_sha = sha256_file(ART)
    declared = open(ART + ".sha256", encoding="utf-8").read().split()[0]
    if declared != art_sha:
        print(f"artifact sha mismatch: file={art_sha} declared={declared}", file=sys.stderr)
        return 2
    ledger_sha = sha256_file(LEDGER)
    pinned_in_art = art["inputs"]["ledger/citation_audit.csv"]["sha256"]
    if ledger_sha != pinned_in_art or ledger_sha != PINNED:
        print(f"ledger drifted since the run: now={ledger_sha} art={pinned_in_art} pinned={PINNED}",
              file=sys.stderr)
        return 2

    s = art["summary"]
    findings = art["findings"]
    verdict = art["review_verdict"]
    hard = art["hard_failures"]
    rel_art = os.path.relpath(ART, ROOT)
    rel_script = os.path.relpath(SCRIPT, ROOT)
    art_ref = f"{rel_art}#sha256:{art_sha[:16]}"
    ledger_ref = f"ledger/citation_audit.csv#sha256:{ledger_sha[:16]}"
    script_ref = f"{rel_script}#sha256:{sha256_file(SCRIPT)[:16]}"
    stamp = datetime.now(TZ).strftime("%Y%m%dT%H%M%S")

    coverage = {}
    for r in art["results"]:
        cm = r.get("class_mapping") or "(evidence/tag only)"
        coverage.setdefault(cm, []).append(r["citation_id"])

    next_falsifier = ("Re-run artifacts/worker-073/l1_spotcheck/run_spotcheck_073.py at ledger sha256 "
                      "315c19145065a5f9: any row whose verdict changes, or a later re-fetch that "
                      "contradicts a recorded fetched sha256, falsifies the MATCH set and the review verdict.")

    events = [
        {
            "event_id": f"w073-status-L1-spotcheck4-{stamp}",
            "event_type": "status",
            "created_at": now(),
            "actor": "worker-073",
            "node_id": "L1",
            "class_id": ";".join(CLASSES),
            "status": "active",
            "hours": 0.4,
            "summary": (f"Independent L1 re-fetch spot check #4 for G-LIT on {rel_art.split('/')[-1]}: "
                        f"exhaustive over ledger data rows 1-40 (SRC-001..SRC-040) at pinned sha256 "
                        f"315c19145065a5f9, the frame with no prior check binding the current revision. "
                        f"Counts: {s['MATCH']} MATCH, {s['PARTIAL']} PARTIAL, {s['FAIL']} FAIL, "
                        f"{s['FETCH_FAILED']} FETCH_FAILED; {s['stored_locator_unresolvable']} rows carry a "
                        f"non-resolvable elided exact_locator; {s['arxiv_api_rate_limited_fallbacks']} arXiv "
                        f"search locators were HTTP-429-rate-limited and were confirmed via abs-page "
                        f"fallback. Read-only; no ledger edit; validation_status unverified."),
            "evidence_refs": [art_ref, ledger_ref, script_ref],
            "next_falsifier": next_falsifier,
            "class_coverage_checked": coverage,
        },
        {
            "event_id": f"w073-artifact-L1-spotcheck4-{stamp}",
            "event_type": "artifact",
            "created_at": now(),
            "actor": "worker-073",
            "node_id": "L1",
            "class_id": ";".join(CLASSES),
            "artifact_type": "l1_spotcheck",
            "path": rel_art,
            "sha256": art_sha,
            "validation_status": "unverified",
            "evidence_refs": [art_ref, ledger_ref, script_ref],
            "falsifier": art["falsifiers"][0],
            "summary": (f"Spot check #4 artifact: 40 rows (SRC-001..SRC-040), frame frozen before fetching, "
                        f"raw response sha256 per fetch, ledger sha256 re-measured after fetching "
                        f"(stable={s['ledger_sha256_stable_during_run']}). Review verdict: {verdict}."),
            "reproduce": art["reproduce"],
            "check_number": art["check_number"],
            "independent_of": art["independent_of"],
        },
        {
            "event_id": f"w073-review-L1-spotcheck4-{stamp}",
            "event_type": "review",
            "created_at": now(),
            "actor": "worker-073",
            "node_id": "L1",
            "class_id": ";".join(CLASSES),
            "target_id": "L1",
            "reviewer": "worker-073",
            "reviewed_sha256": ledger_sha,
            "reviewed_path": "ledger/citation_audit.csv",
            "verdict": verdict,
            "score": 3.0 if verdict == "revise" else 4.0,
            "hard_failures": hard,
            "findings": [{"id": f["id"], "severity": f["severity"], "finding": f["finding"]} for f in findings],
            "artifact_refs": [art_ref],
            "evidence_refs": [art_ref, ledger_ref] + art["independent_of"],
            "falsifier": art["falsifiers"][0],
            "scope_note": ("Independent re-fetch spot check of 40 ledger rows, offered as G-LIT evidence. It is "
                           "not a full-ledger review and promotes no theorem or gate verdict; only the "
                           "controller and group leads may move node/gate status."),
        },
        {
            "event_id": f"w073-status-L1-spotcheck4-final-{stamp}",
            "event_type": "status",
            "created_at": now(),
            "actor": "worker-073",
            "node_id": "L1",
            "class_id": ";".join(CLASSES),
            "status": "done",
            "hours": 0.5,
            "summary": (f"Bounded worker lifecycle complete: class-bound task (independent L1 spot check #4, "
                        f"rows 1-40 at sha 315c19145065a5f9) delivered. Artifact {rel_art} "
                        f"sha256:{art_sha[:16]}; review verdict {verdict} (score "
                        f"{3.0 if verdict == 'revise' else 4.0}); checkpoint runtime/state/w073_checkpoint_1.json. "
                        f"No node/gate status claimed; validation_status unverified. Worker exits now."),
            "evidence_refs": [art_ref, ledger_ref, "runtime/state/w073_checkpoint_1.json"],
            "next_falsifier": next_falsifier,
            "completion_scope": ("worker lifecycle only; this event is a completion claim, not a node done / "
                                 "gate verdict"),
        },
    ]

    # append-only, idempotent by event_id
    existing = set()
    if os.path.isfile(OUTBOX):
        for line in open(OUTBOX, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line).get("event_id"))
            except ValueError:
                continue
    written = []
    with open(OUTBOX, "a", encoding="utf-8") as f:
        for e in events:
            if e["event_id"] in existing:
                continue
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
            written.append(e["event_id"])

    checkpoint = {
        "worker": "worker-073",
        "checkpoint": 1,
        "at": now(),
        "run": "run-2026-09-12T00:00+08:00",
        "assignment_ref": "astra-life02-l1-spotcheck",
        "task": "Independent L1 re-fetch spot check #4 (G-LIT), ledger data rows 1-40 at sha256 315c19145065a5f9",
        "status": "complete",
        "verdict": verdict,
        "artifacts": {
            rel_art: art_sha,
            rel_script: sha256_file(SCRIPT),
            os.path.relpath(FETCHLOG, ROOT): sha256_file(FETCHLOG),
        },
        "ledger": {"ledger/citation_audit.csv": ledger_sha},
        "summary": s,
        "findings": findings,
        "review": {"verdict": verdict, "score": 3.0 if verdict == "revise" else 4.0,
                   "hard_failures": len(hard)},
        "events_emitted": written,
        "outbox": os.path.relpath(OUTBOX, ROOT),
        "hours_spent_estimate": 0.5,
        "next_falsifier": next_falsifier,
        "numerics_lock": "respected: no self-gravitating solver touched, no numerics/spherical_solver created",
        "read_only": "ledger and all other workers' artifacts unmodified; this worker wrote only its own artifact dir, outbox lines and this checkpoint",
        "class_coverage_checked": coverage,
        "non_claims": art["non_claims"],
    }
    os.makedirs(os.path.dirname(CHECKPOINT), exist_ok=True)
    with open(CHECKPOINT, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(json.dumps({"artifact_sha256": art_sha, "ledger_sha256": ledger_sha,
                      "events_written": written, "checkpoint": CHECKPOINT,
                      "verdict": verdict, "summary": s}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
