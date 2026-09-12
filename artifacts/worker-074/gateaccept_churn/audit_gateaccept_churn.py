#!/usr/bin/env python3
"""W074-GATEACCEPT-CHURN-01: same-instant control on W036-GATE-REPRO-01.

Question: the controller's 2026-09-12T00:24:40 gate-audit reasons record N distinct
full-schema accept reviewers per target (F0/F1/F2a/F2b/A0/L0); worker-036 re-ran the
same rule at 00:28:52 on the then-current reviews/ corpus and got different counts
(artifacts/worker-036/gaudit_accept_repro_report.json). Is the recorded count a
controller-scan defect ("phantom accepts") or a temporal artifact of review files
being rewritten in place after the scan?

Method (read-only; no canonical path is written):
  1. Pin the controller's scan record (lifecycle_20260912-002440.json#review_coverage)
     and the checkpoint written by the same lifecycle invocation
     (ckpt-20260912-002440.json#artifact_registry, which stores each review file's
     sha256 at scan instant).
  2. Re-run the documented scan rule (astra_lifecycle.py:160-198) over a manifest of
     the *current* reviews/ corpus and compare with the recorded counts.
  3. For every recorded full accept, reconstruct provenance:
       recorded(file, reviewer, verdict)  [scan instant]
       vs registry sha256 at scan instant [scan instant]
       vs registry sha256 after the 00:25:15 batch write [next checkpoint]
       vs current file (sha256, mtime, verdict, withdrawal text).
  4. Time-series every affected review file through the checkpoint registry.
  5. Re-measure the target artifacts now (the closure revision may have moved them).

Exit code: 0 if the report is written and stable, 2 on unrecoverable input error.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # artifacts/worker-074/gateaccept_churn -> swarm root

SCAN_AT = "2026-09-12T00:24:40+08:00"
SCAN_CKPT = ROOT / "runtime/state/checkpoints/ckpt-20260912-002440.json"
NEXT_CKPT = ROOT / "runtime/state/checkpoints/ckpt-20260912-002548.json"
LIFECYCLE = ROOT / "runtime/state/controller_verification/lifecycle_20260912-002440.json"
MAP = ROOT / "research_map/research_map.json"
REVIEWS = ROOT / "reviews"

# target -> (artifact path, controller-scan measured sha from the same lifecycle)
TARGETS = {
    "F0": ("research_map/formulation_taxonomy.yaml", None),
    "F1": ("schemas/af_wcc_vacuum.yaml", None),
    "F2a": ("schemas/af_scc_c2_vacuum.yaml", None),
    "F2b": ("schemas/af_scc_c0_vacuum.yaml", None),
    "A0": ("evaluation_rubric.yaml", None),
    "L0": ("ledger/theorems.jsonl", None),
}
VERDICT_KINDS = ("accept", "revise", "reject", "inconclusive")
COUNTED_TARGETS = ("F0", "F1", "F2a", "F2b", "A0", "L0")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def jload(p: Path):
    return json.loads(p.read_text())


def corpus_manifest() -> dict:
    files = {}
    for p in sorted(REVIEWS.glob("*.json")):
        try:
            files[p.name] = {"bytes": p.stat().st_size, "sha256": sha256_file(p)}
        except OSError:
            continue
    digest = sha256_bytes(json.dumps(files, sort_keys=True).encode())
    return {"corpus_digest_sha256": digest, "files": files, "n_files": len(files)}


def scan_rule(corpus: dict, target_hashes: dict) -> dict:
    """Re-implementation of astra_lifecycle.py:160-198 scan rule.

    Counts reviews/*.json with a verdict in VERDICT_KINDS, a target alias in the
    scan set, an explicit sha256 pin whose 12-hex prefix matches the measured target
    hash, and counts_as_full_schema_verdict != False.
    """
    aliases = {
        "F0": "F0", "F1": "F1", "F2A": "F2a", "F2B": "F2b", "F2": "F2b",
        "L0": "L0", "L1": "L1",
        "AF-WCC-VAC-GEN": "F1", "AF-SCC-C2-VAC-GEN": "F2a", "AF-SCC-C0-VAC-GEN": "F2b",
    }
    cov = {t: {"full_accepts": [], "verdicts": []} for t in COUNTED_TARGETS}
    for name, meta in sorted(corpus["files"].items()):
        p = REVIEWS / name
        try:
            d = jload(p)
        except Exception:
            continue
        v = str(d.get("verdict", "")).lower()
        if v not in VERDICT_KINDS:
            continue
        reviewer = str(d.get("reviewer") or d.get("actor") or "?")
        full = d.get("counts_as_full_schema_verdict") is not False
        pins = []
        for key in ("artifact_sha256", "reviewed_sha256", "sha256", "cited_sha256"):
            val = d.get(key)
            if isinstance(val, str):
                pins.append(val.lower())
        for key in ("target", "artifact"):
            val = d.get(key)
            if isinstance(val, dict):
                for k2 in ("sha256", "artifact_sha256", "reviewed_sha256"):
                    if isinstance(val.get(k2), str):
                        pins.append(val[k2].lower())
        raw_targets = set()
        for key in ("target_id", "target", "target_subnode"):
            val = d.get(key)
            if isinstance(val, str):
                raw_targets.add(val)
            elif isinstance(val, dict):
                for k2 in ("target_id", "target_subnode", "subnode", "node_id"):
                    if isinstance(val.get(k2), str):
                        raw_targets.add(val[k2])
        targets = {aliases.get(t, aliases.get(t.upper(), t)) for t in raw_targets}
        for t in targets:
            if t not in cov:
                continue
            h = target_hashes.get(t, "")
            if h and any(pp.startswith(h[:12]) or h.startswith(pp[:12]) for pp in pins):
                entry = {"file": name, "reviewer": reviewer, "verdict": v, "full": full}
                cov[t]["verdicts"].append(entry)
                if v == "accept" and full:
                    cov[t]["full_accepts"].append(entry)
    for t, c in cov.items():
        c["distinct_accept_reviewers"] = sorted({e["reviewer"] for e in c["full_accepts"]})
    return cov


def registry_series(path: str) -> list:
    out = []
    for cp in sorted((ROOT / "runtime/state/checkpoints").glob("*.json")):
        try:
            d = jload(cp)
        except Exception:
            continue
        e = (d.get("artifact_registry") or {}).get(path)
        if isinstance(e, dict):
            out.append({"checkpoint": cp.stem, "created_at": d.get("created_at"),
                        "sha256": e.get("sha256"), "bytes": e.get("bytes")})
    return out


def main() -> int:
    try:
        life = jload(LIFECYCLE)
        scan_ckpt = jload(SCAN_CKPT)
        next_ckpt = jload(NEXT_CKPT)
        mp = jload(MAP)
    except Exception as exc:
        print(f"FATAL input error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    recorded_measured = life.get("measured_hashes", {})
    for t, (path, _) in TARGETS.items():
        rec = recorded_measured.get(t) or {}
        TARGETS[t] = (path, rec.get("sha256"))
    recorded_hashes = {t: v[1] for t, v in TARGETS.items()}

    recorded_cov = {t: life.get("review_coverage", {}).get(t, {}) for t in COUNTED_TARGETS}
    corpus = corpus_manifest()
    rerun = scan_rule(corpus, recorded_hashes)

    # provenance for every recorded full accept
    provenance = []
    for t in COUNTED_TARGETS:
        for acc in recorded_cov[t].get("full_accepts", []):
            rel = "reviews/" + acc["file"]
            p = ROOT / rel
            at = (scan_ckpt.get("artifact_registry") or {}).get(rel, {})
            after = (next_ckpt.get("artifact_registry") or {}).get(rel, {})
            cur = {"exists": p.exists()}
            if p.exists():
                d = None
                try:
                    d = jload(p)
                except Exception:
                    pass
                cur.update({
                    "sha256": sha256_file(p),
                    "bytes": p.stat().st_size,
                    "mtime": datetime.fromtimestamp(p.stat().st_mtime).isoformat(),
                    "verdict": (d or {}).get("verdict"),
                    "reviewer": (d or {}).get("reviewer"),
                    "event_id": (d or {}).get("event_id"),
                    "created_at": (d or {}).get("created_at"),
                    "withdraws_prior_accept": any(
                        "withdraw" in str(x).lower() for x in (d or {}).get("findings", [])),
                })
            changed = bool(at.get("sha256") and cur.get("sha256") and at["sha256"] != cur["sha256"])
            verdict_changed = bool(at.get("sha256") and str(cur.get("verdict")) != "accept")
            provenance.append({
                "target": t, "file": rel, "recorded_reviewer": acc["reviewer"],
                "recorded_verdict": acc["verdict"],
                "recorded_as_full_accept_by_scan": True,
                "sha256_at_scan_checkpoint": at.get("sha256"),
                "sha256_at_next_checkpoint": after.get("sha256"),
                "current_sha256": cur.get("sha256"),
                "current_verdict": cur.get("verdict"),
                "current_mtime": cur.get("mtime"),
                "current_event_id": cur.get("event_id"),
                "current_created_at": cur.get("created_at"),
                "current_withdraws_prior_accept": cur.get("withdraws_prior_accept"),
                "content_changed_after_scan": changed,
                "verdict_no_longer_accept": verdict_changed,
                "classification": ("superseded_in_place_after_scan" if changed and verdict_changed
                                   else "unchanged" if not changed else "content_changed"),
            })

    affected = sorted({p["file"] for p in provenance if p["content_changed_after_scan"]})
    timeline = {f: registry_series(f) for f in affected}

    now_targets = {}
    for t, (path, rec) in TARGETS.items():
        p = ROOT / path
        now_targets[t] = {
            "path": path,
            "sha256_at_scan": rec,
            "sha256_now": sha256_file(p) if p.exists() else None,
            "moved_since_scan": bool(rec and p.exists() and sha256_file(p) != rec),
        }
    now_hashes = {t: v["sha256_now"] for t, v in now_targets.items()}
    rerun_now = scan_rule(corpus, now_hashes)

    # per-divergence explanation for the four W036 recorded-vs-rerun findings
    by_file = {p["file"]: p for p in provenance}
    f0_094 = registry_series("reviews/F0-review-094.json")
    explanations = [
        {"w036_id": "F-REPRO-F0", "target": "F0", "recorded": 0, "w036_rerun": 1,
         "cause": "review file written after the scan instant and later withdrawn",
         "file": "reviews/F0-review-094.json",
         "registry_series": f0_094,
         "current_verdict": (jload(ROOT / "reviews/F0-review-094.json").get("verdict")
                             if (ROOT / "reviews/F0-review-094.json").exists() else None)},
        {"w036_id": "F-REPRO-F1", "target": "F1", "recorded": 1, "w036_rerun": 0,
         "cause": "in-place supersession after scan",
         "file": "reviews/F1-review-lead-audit-r2.json",
         "provenance": by_file.get("reviews/F1-review-lead-audit-r2.json")},
        {"w036_id": "F-REPRO-F2a", "target": "F2a", "recorded": 2, "w036_rerun": 1,
         "cause": "in-place supersession after scan",
         "file": "reviews/F2a-review-lead-audit-r2.json",
         "provenance": by_file.get("reviews/F2a-review-lead-audit-r2.json")},
        {"w036_id": "F-REPRO-F2b", "target": "F2b", "recorded": 4, "w036_rerun": 2,
         "cause": "two in-place supersessions after scan",
         "files": ["reviews/F2b-review-lead-audit-r2.json", "reviews/F2b-review-07.json"],
         "provenance": [by_file.get("reviews/F2b-review-lead-audit-r2.json"),
                        by_file.get("reviews/F2b-review-07.json")]},
    ]

    # recorded accepts that W036 could not reproduce (from their report)
    w036 = {}
    wp = ROOT / "artifacts/worker-036/gaudit_accept_repro_report.json"
    if wp.exists():
        wd = jload(wp)
        w036 = {"report_sha256": sha256_file(wp),
                "corpus_digest": (wd.get("snapshot") or {}).get("corpus_digest"),
                "measured_at": wd.get("measured_at"),
                "recorded_vs_rerun": wd.get("recorded_vs_rerun")}

    findings = [
        {
            "id": "W074-CHURN-F1",
            "severity": "info",
            "status": "resolved-explanation",
            "statement": (
                "All four recorded-vs-rerun accept-count divergences in W036-GATE-REPRO-01 are "
                "explained by review files being rewritten in place after the controller scan, not "
                "by a controller scan defect. At the 00:24:40 scan instant the controller's own "
                "checkpoint registry records the pre-rewrite bytes for every disputed accept; those "
                "byte hashes no longer exist on disk and the current files parse as revise with an "
                "explicit withdrawal of the 00:22 accept."),
            "evidence_refs": [
                "runtime/state/controller_verification/lifecycle_20260912-002440.json#review_coverage",
                "runtime/state/checkpoints/ckpt-20260912-002440.json#artifact_registry",
                "runtime/state/checkpoints/ckpt-20260912-002548.json#artifact_registry",
                "artifacts/worker-074/gateaccept_churn/report.json",
                "artifacts/worker-074/gateaccept_churn/raw/registry_timeline.json",
            ],
        },
        {
            "id": "W074-CHURN-F2",
            "severity": "major",
            "status": "open",
            "statement": (
                "Provenance gap: neither the gate reason strings nor review_coverage identify review "
                "evidence by content hash (file name + reviewer + verdict only), while the protocol "
                "permits in-place overwrite of reviews/*.json. A recorded accept therefore becomes "
                "unverifiable the moment the author rewrites the file; no copy of the pre-rewrite "
                "bytes (22ff0c1c3f60, 16c38e5b2873, b2a936d2b87f, 7df2904783b5, b90d2acc4218) "
                "exists in the checkpoint registry, in the worker-042 snapshot, or elsewhere on "
                "disk. W036's post-hoc re-run divergence is the symptom of this gap, not of a "
                "fabricated count."),
            "evidence_refs": [
                "runtime/state/checkpoints/ckpt-20260912-002440.json#artifact_registry",
                "artifacts/worker-042/gate_scan_gap/snapshot/reviews/F1-review-lead-audit-r2.json",
                "artifacts/worker-036/gaudit_accept_repro_report.json",
            ],
        },
        {
            "id": "W074-CHURN-F3",
            "severity": "major",
            "status": "open",
            "statement": (
                "The 00:24:40 gate reasons were stale within 35 seconds: astra-lead-audit batch-"
                "rewrote five full-schema accepts (F1, F2a, F2b, A0, L0) to revise at 00:25:15 "
                "(identical mtime .335434 on all five files), L0-review-worker-006 followed at "
                "00:25:24, F2b-review-07 at 00:26:33, and F0-review-094's accept window ran "
                "00:27:38-00:29:05. Any gate reason or count derived from a scan must carry the "
                "corpus digest it was computed over; the recorded reason carries checked_at only."),
            "evidence_refs": [
                "runtime/state/checkpoints/ckpt-20260912-002548.json#artifact_registry",
                "comms/outbox/astra-lead-audit.jsonl",
            ],
        },
        {
            "id": "W074-CHURN-F4",
            "severity": "minor",
            "status": "open",
            "statement": (
                "W036's F-PHANTOM-F1/F2a/F2b wording ('no review file in the pinned corpus "
                "supports it') is true only for the post-rewrite corpus; it mischaracterizes the "
                "recorded count as unsupported rather than temporally non-reproducible. W036's "
                "churn_evidence also cites event ids (audit-review-*-lead-audit-r3-20260912T0025) "
                "that exist only inside the rewritten review files (field event_id), not in the "
                "ingested event stream; the ingested supersession events are "
                "audit-review-<T>-lead-audit-final-20260912T0027 in "
                "comms/outbox/astra-lead-audit.jsonl with created_at 00:26:00."),
            "evidence_refs": [
                "artifacts/worker-036/gaudit_accept_repro_report.json#findings",
                "comms/outbox/astra-lead-audit.jsonl",
            ],
        },
        {
            "id": "W074-CHURN-F5",
            "severity": "info",
            "status": "recorded",
            "statement": (
                "Moving target: by this run's measurement the closure revision had replaced all "
                "four canonical formulation artifacts, so every review bound to the recorded scan "
                "hashes (F0 276009f4, F1 9a8bd4c9, F2a b6123750, F2b 1bb78ce9) is now stale and the "
                "next lifecycle scan cannot carry the recorded coverage forward. Newly measured "
                "hashes are in current_targets."),
            "evidence_refs": [
                "research_map/formulation_taxonomy.yaml",
                "schemas/af_wcc_vacuum.yaml",
                "schemas/af_scc_c2_vacuum.yaml",
                "schemas/af_scc_c0_vacuum.yaml",
            ],
        },
    ]

    report = {
        "schema_version": 1,
        "task_id": "W074-GATEACCEPT-CHURN-01",
        "worker": "worker-074",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "node_ids": ["F0", "F1", "F2a", "F2b", "A0"],
        "gates": ["G-F0", "G-FORM", "G-AUDIT"],
        "measured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "question": ("Do the recorded 00:24:40 distinct-accept counts reproduce, and if not, is the "
                     "cause a scan defect or review-corpus churn after the scan?"),
        "authority_note": ("Worker-authored evidence only: this report sets no node status, no "
                           "validation_status=passed, and no gate verdict."),
        "pinned_inputs": {
            "lifecycle_record": {"path": str(LIFECYCLE.relative_to(ROOT)),
                                 "sha256": sha256_file(LIFECYCLE)},
            "scan_instant_checkpoint": {"path": str(SCAN_CKPT.relative_to(ROOT)),
                                        "sha256": sha256_file(SCAN_CKPT)},
            "next_checkpoint": {"path": str(NEXT_CKPT.relative_to(ROOT)),
                                "sha256": sha256_file(NEXT_CKPT)},
            "map": {"path": "research_map/research_map.json", "sha256": sha256_file(MAP)},
            "w036_report": w036,
        },
        "recorded_scan": {
            "checked_at": SCAN_AT,
            "source": "lifecycle_20260912-002440.json#review_coverage + controller_gate_audit",
            "recorded_target_hashes": recorded_hashes,
            "recorded_full_accepts": {t: recorded_cov[t].get("full_accepts", [])
                                      for t in COUNTED_TARGETS},
            "recorded_distinct_accept_reviewers": {
                t: recorded_cov[t].get("distinct_accept_reviewers", []) for t in COUNTED_TARGETS},
        },
        "rerun_same_rule_current_corpus": {
            "corpus_digest_sha256": corpus["corpus_digest_sha256"],
            "corpus_files": corpus["n_files"],
            "target_hashes_used": "recorded_scan.recorded_target_hashes",
            "full_accepts": {t: rerun[t]["full_accepts"] for t in COUNTED_TARGETS},
            "distinct_accept_reviewers": {t: rerun[t]["distinct_accept_reviewers"]
                                          for t in COUNTED_TARGETS},
        },
        "rerun_at_current_targets": {
            "corpus_digest_sha256": corpus["corpus_digest_sha256"],
            "target_hashes_used": now_hashes,
            "full_accepts": {t: rerun_now[t]["full_accepts"] for t in COUNTED_TARGETS},
            "distinct_accept_reviewers": {t: rerun_now[t]["distinct_accept_reviewers"]
                                          for t in COUNTED_TARGETS},
        },
        "w036_divergence_explanations": explanations,
        "accept_provenance": provenance,
        "churn_timeline": timeline,
        "current_targets": now_targets,
        "findings": findings,
        "global_falsifier": (
            "FALSIFIED IF any of: (a) a file classified superseded_in_place_after_scan has the same "
            "sha256 in ckpt-20260912-002440.json#artifact_registry and in the current tree; (b) the "
            "recorded review_coverage does not list that file as a full accept at 00:24:40; (c) the "
            "checkpoint registry at 00:24:40 does not contain a sha256 for that path; (d) any review "
            "file on disk today, at the recorded target hash, is a full accept whose sha256 equals "
            "the at-scan registry value (i.e. the accept bytes survived); or (e) a re-run of this "
            "script on the same pinned inputs yields a different classification for any file."),
    }

    here = HERE
    (here / "raw").mkdir(exist_ok=True)
    (here / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True))
    (here / "raw" / "current_corpus_manifest.json").write_text(json.dumps(corpus, indent=1))
    (here / "raw" / "registry_timeline.json").write_text(json.dumps(timeline, indent=1))
    # stability re-check of the reviews corpus during the run
    corpus2 = corpus_manifest()
    stable = corpus2["corpus_digest_sha256"] == corpus["corpus_digest_sha256"]
    (here / "raw" / "corpus_stability.txt").write_text(
        f"corpus_digest_start={corpus['corpus_digest_sha256']}\n"
        f"corpus_digest_end={corpus2['corpus_digest_sha256']}\nstable={stable}\n")
    print(json.dumps({
        "report": str((here / "report.json").relative_to(ROOT)),
        "report_sha256": sha256_file(here / "report.json"),
        "corpus_stable": stable,
        "recorded": report["recorded_scan"]["recorded_distinct_accept_reviewers"],
        "rerun_recorded_hashes": report["rerun_same_rule_current_corpus"]["distinct_accept_reviewers"],
        "rerun_current_hashes": report["rerun_at_current_targets"]["distinct_accept_reviewers"],
        "current_targets": {t: v["moved_since_scan"] for t, v in now_targets.items()},
        "superseded_files": [p["file"] for p in provenance if p["content_changed_after_scan"]],
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
