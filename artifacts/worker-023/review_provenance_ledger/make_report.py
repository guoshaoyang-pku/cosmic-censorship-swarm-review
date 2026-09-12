#!/usr/bin/env python3
"""Deterministic report assembler for W023-F2B-REVIEW-PROVENANCE-01.

Reads the frozen evidence files written by review_provenance_ledger.py runs plus the live
F2b verdict file and the accepted event stream, and writes `evidence/report.json` with no
wall-clock fields, so the report bytes are stable for a given input set.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(ROOT, "..", "..", ".."))

F2B_VERDICT = os.path.join(REPO, "reviews", "F2b-review-worker-072-rev29.json")
EVENTS = os.path.join(REPO, "research_map", "events.jsonl")
W036_MANIFEST = os.path.join(REPO, "artifacts", "worker-036", "gform_r3_binding_census",
                             "pinned", "MANIFEST.json")
W036_REPORT = os.path.join(REPO, "artifacts", "worker-036", "gform_r3_binding_census",
                           "report.json")
C0_SCHEMA = os.path.join(REPO, "schemas", "af_scc_c0_vacuum.yaml")
FROZEN = os.path.join(REPO, "artifacts", "formulation", "FROZEN.json")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    ev = ROOT + "/evidence"
    check = load(ev + "/check_seed.json")
    verify = load(ev + "/verify.json")
    selftest = load(ev + "/selftest.json")
    window = load(ev + "/w036_window_delta.json")

    f2b = load(F2B_VERDICT)
    f2b_sha = sha256_file(F2B_VERDICT)
    f2b_raw = open(F2B_VERDICT, "rb").read().decode("utf-8", "replace")

    # durable accepted-stream record of the pre-rewrite accept
    w072_event = None
    for line in open(EVENTS, "r", encoding="utf-8"):
        if "w072-2026-09-12T01:10:13+08:00-review-f2b" in line:
            w072_event = json.loads(line)
            break

    lost_prefix = None
    if w072_event:
        for ref in w072_event.get("evidence_refs", []):
            m = re.match(r"reviews/F2b-review-worker-072-rev29\.json#([0-9a-f]{12,64})$", ref)
            if m:
                lost_prefix = m.group(1)
    acked = bool(lost_prefix and lost_prefix in f2b_raw)

    report = {
        "schema": "w023-review-provenance-report/v1",
        "task_id": "W023-F2B-REVIEW-PROVENANCE-01",
        "actor": "worker-023",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-WCC-VAC-GEN"],
        "gate_of_record": "G-FORM",
        "authority": ("worker-level measurement only; no gate verdict, no node status, no "
                      "validation_status, no canonical write; reviews/ was read, never written"),
        "question": ("CF-31 root cause: reviews/*.json are mutable under fixed names. Can a "
                     "worker-side instrument preserve verdict bytes, distinguish acknowledged "
                     "supersession from silent evidence loss, and re-derive the disputed F2b "
                     "count record?"),
        "pins": {
            "schemas/af_scc_c0_vacuum.yaml": sha256_file(C0_SCHEMA),
            "artifacts/formulation/FROZEN.json": sha256_file(FROZEN),
            "artifacts/worker-036/gform_r3_binding_census/pinned/MANIFEST.json":
                sha256_file(W036_MANIFEST),
            "artifacts/worker-036/gform_r3_binding_census/report.json": sha256_file(W036_REPORT),
            "reviews/F2b-review-worker-072-rev29.json": f2b_sha,
        },
        "corpus_snapshot": {
            "n_review_files": check["summary"]["n_paths"],
            "snapshot_digest": check["snapshot_digest"],
            "ledger_records": verify["n_ledger_records"],
            "store_entries": verify["n_store_entries"],
            "store_verify_ok": verify["ok"],
            "post_seed_check": check["summary"]["counts"],
        },
        "instrument_controls": {
            "selftest_checks": selftest["n_checks"],
            "selftest_pass": selftest["n_pass"],
            "all_pass": selftest["all_pass"],
        },
        "window_delta_vs_worker036_snapshot": {
            "manifest_file_sha256": window["manifest_file_sha256"],
            "counts": window["counts"],
            "non_added": [r for r in window["changed"] if r["state"] != "ADDED"],
        },
        "f2b_072_case_study": {
            "current_file_sha256": f2b_sha,
            "current_verdict": f2b.get("verdict"),
            "current_score": f2b.get("score"),
            "current_hard_failures": [h.get("id") for h in f2b.get("hard_failures", [])],
            "supersedes_sha256": f2b.get("supersedes_sha256"),
            "supersedes_verdict": f2b.get("supersedes_verdict"),
            "superseded_at": f2b.get("superseded_at"),
            "revision_history": f2b.get("revision_history"),
            "accepted_stream_event_id": (w072_event or {}).get("event_id"),
            "accepted_stream_received_at": (w072_event or {}).get("_received_at"),
            "accepted_stream_verdict": (w072_event or {}).get("verdict"),
            "accepted_stream_score": (w072_event or {}).get("score"),
            "accepted_stream_blind": (w072_event or {}).get("blind"),
            "lost_accept_hash_prefix": lost_prefix,
            "replacement_acknowledges_lost_hash": acked,
            "disposition": ("NOT silent: the rev2 revise is a self-supersession that records "
                            "supersedes_sha256=7487f310d208.../supersedes_verdict=accept, and "
                            "the accepted stream holds the accept event at 01:10:14 (before "
                            "the 01:14:51 rewrite). The rev1 BYTES are gone (worker-036 is "
                            "right about bytes; only the record survives), which is exactly "
                            "the loss class this ledger now prevents going forward."),
        },
        "instrument_semantics": {
            "states": {
                "UNCHANGED": "bytes and mtime identical to the latest observation",
                "TOUCHED": "bytes identical, mtime moved (not a rewrite)",
                "SUPERSEDED": "bytes changed and the replacement contains the replaced sha256 "
                              "as a hex token (acknowledged, exit 0)",
                "REWRITTEN": "bytes changed with no hash-bearing pointer to the replaced bytes "
                             "(silent loss, fail closed, exit 2)",
                "RESTORED": "bytes equal an earlier observation of the same path (rollback; "
                            "recorded, exit 0)",
                "ADDED": "path first seen now",
                "REMOVED": "observed path gone (fail closed, exit 2)",
            },
            "fail_closed": "non-zero exit on REWRITTEN or REMOVED; SUPERSEDED/RESTORED are "
                           "recorded verdict changes, not evidence loss",
            "write_once_store": "store/<sha256>.json is created only if absent; every prior "
                                "verdict byte sequence that was ever seeded remains readable",
        },
        "worker_level_recommendation": [
            "run `check` immediately before and after every controller pass; REWRITTEN/REMOVED "
            "means a verdict byte sequence moved without a hash-bearing pointer and the pass "
            "should treat the affected coverage count as non-re-derivable",
            "require new verdict bytes at an occupied path to carry the replaced file's sha256 "
            "(supersedes_sha256 / revision_history), which is what makes the 072 flip auditable",
            "the ledger is a preservation record; it is not a review verdict and must not be "
            "counted toward coverage",
        ],
        "non_claims": [
            "not a gate verdict and not a coverage count",
            "not a claim that any verdict in the corpus is correct",
            "not a canonical instrument; reviews/ and research_map/ were not written",
            "the store preserves bytes from its seed time forward; it cannot recover the lost "
            "worker-072 rev1 bytes",
            "SUPERSEDED proves the replacement names the replaced hash, not that the "
            "replacement's content is sound",
        ],
        "falsifier": ("Falsified if: the detector fails to flag a synthetic silent accept->revise "
                      "rewrite at the same path (selftest control); it flags an unchanged or "
                      "merely touched file; verify finds a store entry whose bytes differ from "
                      "its recorded sha256; the w036 window delta is not reproducible from "
                      "artifacts/worker-036/gform_r3_binding_census/pinned/MANIFEST.json at hash "
                      "beab69e12028af0305989bbfcf7e0ad1f05b4b724d8e37416bc35e47da8d1766; or "
                      "reviews/F2b-review-worker-072-rev29.json stops containing the accepted-"
                      "stream's recorded prefix 7487f310d208. Re-run: selftest, seed, check, "
                      "verify, diff-manifest (commands in README.md)."),
    }
    out = json.dumps(report, indent=2, sort_keys=True) + "\n"
    with open(ev + "/report.json", "w", encoding="utf-8") as f:
        f.write(out)
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
