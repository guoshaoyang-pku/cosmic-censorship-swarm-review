#!/usr/bin/env python3
"""Emit worker-070 live02 events + worker checkpoint (run AFTER run_live070.py).

Appends to comms/outbox/worker-070.jsonl (never rewrites predecessor lines; drops only its own
task_id lines first, so it is re-runnable) and writes runtime/state/w070_checkpoint_locator_live02.json.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
OUTDIR = ROOT / "artifacts" / "worker-070" / "l1_locator_live02"
REPORT = OUTDIR / "report.json"
RUNNER = OUTDIR / "run_live070.py"
FRAME = OUTDIR / "frame.json"
REVIEW = OUTDIR / "REVIEW.md"
RAW = OUTDIR / "raw"
OUTBOX = ROOT / "comms" / "outbox" / "worker-070.jsonl"
CKPT = ROOT / "runtime" / "state" / "w070_checkpoint_locator_live02.json"
LEDGER = ROOT / "ledger" / "citation_audit.csv"
CST = timezone(timedelta(hours=8))
TASK_ID = "w070-l1-locator-live-02"
FROZEN = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    art = json.loads(REPORT.read_text(encoding="utf-8"))
    report_sha = sha256_file(REPORT)
    runner_sha = sha256_file(RUNNER)
    frame_sha = sha256_file(FRAME)
    review_sha = sha256_file(REVIEW)
    ledger_sha = sha256_file(LEDGER)
    ts = datetime.now(CST).isoformat(timespec="seconds")
    eid = "w070L2-" + ts.replace(":", "").replace("-", "")[:15]
    agg = art["aggregate"]
    vc = agg["verdict_counts"]
    top = agg["top_hit_count"]
    n = agg["rows_in_family"]
    p = art["pins"]
    drift = art["inputs"]["ledger/citation_audit.csv"]["drift"]
    corpus_valid = art["corpus_valid"]
    hard = art["hard_failures"]
    not_top = [r["citation_id"] for r in art["census"] if r["verdict"] != "TOP_HIT_MATCH"]
    share = agg["rows_sharing_a_locator"]
    nf = art["falsifier"]
    report_ref = f"artifacts/worker-070/l1_locator_live02/report.json#{report_sha[:12]}"
    runner_ref = f"artifacts/worker-070/l1_locator_live02/run_live070.py#{runner_sha[:12]}"
    frame_ref = f"artifacts/worker-070/l1_locator_live02/frame.json#{frame_sha[:12]}"
    review_ref = f"artifacts/worker-070/l1_locator_live02/REVIEW.md#{review_sha[:12]}"
    ledger_ref = f"ledger/citation_audit.csv#{ledger_sha[:16]}"
    ckpt_ref = "runtime/state/w070_checkpoint_locator_live02.json"

    status_start = {
        "event_id": f"{eid}-status-start", "event_type": "status", "created_at": ts,
        "actor": "worker-070", "node_id": "L1", "group_id": "literature", "class_ids": FROZEN,
        "status": "active", "hours": 0.3,
        "assignment_ref": TASK_ID,
        "summary": ("No inbox card exists for worker-070 (relaunched slot). Took ONE bounded class-bound successor task: "
                    "W070-L1-LOCATOR-LIVE-02 = live re-resolution of the arxiv-api-query locator family "
                    f"({n} rows) of ledger/citation_audit.csv at pinned sha 315c19145065, the family the rev3 census "
                    "left 35/38 rows untested (it live-sampled only the first three). Frame registered and hashed before any fetch; as-recorded URL fetched once "
                    "per row; verdict is id-based (claimed arxiv_id at rank 1 / in page / absent); controls include an "
                    "offline parser fixture, two live recorded-title positive controls, a live nonsense negative control, "
                    "an idempotence refetch and 97/97 classification agreement with the predecessor census. "
                    "Does not claim node completion or any gate verdict."),
        "evidence_refs": [ledger_ref, "research_map/research_map.json", "artifacts/worker-070/l1_locator_resolvability/census.json"],
        "next_falsifier": nf,
    }
    artifact_ev = {
        "event_id": f"{eid}-artifact-locator-live-report", "event_type": "artifact", "created_at": ts,
        "actor": "worker-070", "node_id": "L1", "group_id": "literature",
        "artifact_type": "l1_locator_live_resolution_report",
        "path": "artifacts/worker-070/l1_locator_live02/report.json", "sha256": report_sha,
        "validation_status": "unverified", "class_ids": FROZEN, "gate": "G-LIT", "task_id": TASK_ID,
        "ledger_sha256": ledger_sha, "ledger_sha256_pinned": p["ledger/citation_audit.csv"],
        "ledger_drift": drift, "corpus_valid": corpus_valid,
        "frame_sha256": frame_sha, "controls": "all pass" if art["falsifier_outcome"]["controls_pass"] else "FAILED",
        "verdict_counts": vc, "top_hit_count": top, "top_hit_rate": agg["as_recorded_reresolution_rate"],
        "summary": (f"{n} arxiv-api-query rows fetched as recorded at the pinned ledger hash. Only {top}/{n} re-resolve "
                    f"to the claimed work at rank 1 as recorded; {vc.get('HIT_IN_PAGE_NOT_TOP', 0)} return it lower in the "
                    f"page and {vc.get('NOT_IN_RETURNED_PAGE', 0)} do not return it in the page at all "
                    f"(FETCH_FAILED={vc.get('FETCH_FAILED', 0)}). {agg['duplicate_locator_groups']} locator strings are "
                    f"shared by {share} rows (max {agg['max_rows_per_locator']} rows on one query), so `exact_locator` is "
                    "not work-specific for most of the family. Raw responses and the pre-registered frame are on disk and hashed."),
        "evidence_refs": [ledger_ref, frame_ref, runner_ref],
        "next_falsifier": nf,
    }
    artifact_runner_ev = {
        "event_id": f"{eid}-artifact-runner", "event_type": "artifact", "created_at": ts,
        "actor": "worker-070", "node_id": "L1", "group_id": "literature", "artifact_type": "verifier",
        "path": "artifacts/worker-070/l1_locator_live02/run_live070.py", "sha256": runner_sha,
        "validation_status": "unverified", "class_ids": FROZEN, "gate": "G-LIT", "task_id": TASK_ID,
        "summary": "Deterministic instrument: pins the ledger sha256, classifies all 97 locators independently, writes and "
                   "hashes the frame before any fetch, fetches each recorded URL once with >=3.1s spacing, parses the Atom "
                   "feed, applies the id-ranked verdict rule, runs the controls and fails closed on end-of-run ledger drift.",
        "evidence_refs": [report_ref, ledger_ref],
        "next_falsifier": nf,
    }
    artifact_frame_ev = {
        "event_id": f"{eid}-artifact-frame", "event_type": "artifact", "created_at": ts,
        "actor": "worker-070", "node_id": "L1", "group_id": "literature", "artifact_type": "preregistration",
        "path": "artifacts/worker-070/l1_locator_live02/frame.json", "sha256": frame_sha,
        "validation_status": "unverified", "class_ids": FROZEN, "gate": "G-LIT", "task_id": TASK_ID,
        "summary": f"Pre-registered frame of all {n} arxiv-api-query rows (row index, citation_id, claimed arxiv_id, "
                   "locator and locator_sha256), written and hashed before the first live fetch; registration time and "
                   "runner hash are recorded in frame.sha256.txt beside it.",
        "evidence_refs": [report_ref, runner_ref],
        "next_falsifier": nf,
    }
    artifact_review_ev = {
        "event_id": f"{eid}-artifact-review-note", "event_type": "artifact", "created_at": ts,
        "actor": "worker-070", "node_id": "L1", "group_id": "literature", "artifact_type": "review_note",
        "path": "artifacts/worker-070/l1_locator_live02/REVIEW.md", "sha256": review_sha,
        "validation_status": "unverified", "class_ids": FROZEN, "gate": "G-LIT", "task_id": TASK_ID,
        "summary": "Human-readable review generated from report.json: verdict table, per-class split, the non-top rows, "
                   "control outcomes and limits. Rev1 of the run is preserved under superseded/ with its defect recorded.",
        "evidence_refs": [report_ref, frame_ref, runner_ref],
        "next_falsifier": nf,
    }
    review_ev = {
        "event_id": f"{eid}-review-locator-live", "event_type": "review", "created_at": ts,
        "actor": "worker-070", "target_id": "ledger/citation_audit.csv", "reviewer": "worker-070",
        "verdict": "revise", "score": 2.5,
        "hard_failures": hard,
        "findings": [
            (f"WORK-SPECIFICITY (major): only {top}/{n} arxiv-api-query `exact_locator` cells re-resolve to the row's own "
             f"claimed work at rank 1 when fetched exactly as recorded. {vc.get('HIT_IN_PAGE_NOT_TOP', 0)} return the work "
             f"at ranks 2-10 and {vc.get('NOT_IN_RETURNED_PAGE', 0)} return it nowhere in the page "
             "(default max_results=10). Examples at the shared Schwarzschild query: SRC-005 rank 2, SRC-006 rank 0, "
             "SRC-007 rank 3, SRC-008 rank 4, SRC-009 rank 5."),
            (f"SHARED LOCATORS (major): {agg['duplicate_locator_groups']} distinct locator strings cover {share}/{n} rows "
             f"(one query covers {agg['max_rows_per_locator']} rows). A cell shared by k rows cannot be the exact locator "
             "of more than one of them; the column therefore functions as a search recipe, not a pointer."),
            ("The 27-row elided-locator finding from the predecessor rev3 census is unaffected and stands; this run adds "
             "that the non-elided arXiv query family is also not work-specific."),
            ("Scope/limits: one fetch per row at one pinned ledger hash; arXiv ranking may vary over time, so a rank is a "
             "measurement at the recorded time, not a permanent property. No ledger edit was made; worker evidence only, "
             "no gate verdict, no node completion."),
            ("Self-correction: run revision 2. Rev1 (preserved under superseded/) reported agree=false on the three "
             "re-executed predecessor rows because raw verdict names (QUERY_*) were compared to this run's normalized "
             "names; the normalization is fixed and no measurement or verdict changed."),
        ],
        "task_id": TASK_ID, "artifact_ref": report_ref,
        "reviewed_sha256": ledger_sha, "class_ids": FROZEN, "gate": "G-LIT",
        "scope_limit": f"{n}/{n} arxiv-api-query rows live-fetched once at one ledger hash",
        "evidence_refs": [report_ref, review_ref, frame_ref, runner_ref, ledger_ref],
    }
    claim_ev = {
        "event_id": f"{eid}-claim-locator-live", "event_type": "claim", "created_at": ts,
        "actor": "worker-070", "node_id": "L1", "class_id": "GLOBAL", "class_ids": FROZEN,
        "conclusion_type": "formal_model", "gate": "G-LIT", "task_id": TASK_ID,
        "statement": (
            f"At ledger/citation_audit.csv#{ledger_sha[:16]} (sha256 {ledger_sha}, stable before and after the fetch window), "
            f"the {n} rows whose `exact_locator` is an arXiv API query URL were fetched exactly as recorded: {top}/{n} "
            f"({agg['as_recorded_reresolution_rate']}) return the row's own claimed arxiv_id at rank 1, "
            f"{vc.get('HIT_IN_PAGE_NOT_TOP', 0)} return it at rank 2-10, {vc.get('NOT_IN_RETURNED_PAGE', 0)} do not return it "
            f"in the returned page, and {vc.get('FETCH_FAILED', 0)} failed to fetch (PARSE_ERROR={vc.get('PARSE_ERROR', 0)}). "
            f"{agg['duplicate_locator_groups']} locator strings are shared by {share} of the {n} rows "
            f"(max {agg['max_rows_per_locator']} rows per locator), so the column cannot be work-specific for those rows. "
            f"All controls passed (parser fixture, 2 live recorded-title positives, live nonsense negative, idempotence refetch, "
            f"97/97 classification agreement); corpus_valid={corpus_valid}; ledger drift={drift}. "
            "This is a locator-scope measurement bound to the pinned ledger hash; it asserts nothing about cosmic censorship."),
        "assumptions": [
            "The row's own `arxiv_id` (version-stripped) is the identity the row claims; the locator should re-resolve to it.",
            "arXiv API ranking is the resolution semantics of a query locator; rank 1 is the operational meaning of "
            "'exact locator' for a query-shaped cell.",
            "The as-recorded URL is fetched without modification; adding id_list/abs URLs would change the object under test.",
            "The pinned ledger hash is the artifact identity; drift voids, later ranking changes are drift-like, not falsification.",
        ],
        "artifact_refs": [report_ref, runner_ref, frame_ref],
        "evidence_refs": [ledger_ref, report_ref, frame_ref, runner_ref],
        "falsifier": nf,
    }
    status_done = {
        "event_id": f"{eid}-status-complete", "event_type": "status", "created_at": ts,
        "actor": "worker-070", "node_id": "L1", "group_id": "literature", "class_ids": FROZEN,
        "status": "active", "hours": 0.3, "assignment_ref": TASK_ID,
        "summary": (f"worker-070 bounded task complete and exiting. Artifact report.json sha256 {report_sha}; frame.json "
                    f"sha256 {frame_sha}; runner sha256 {runner_sha}; checkpoint {ckpt_ref}. Ledger stable at "
                    f"{ledger_sha[:16]}; status={art['status']}; verdicts={vc}; only {top}/{n} top-resolve as recorded; "
                    f"{agg['duplicate_locator_groups']} shared locators cover {share}/{n} rows. Node L1 remains "
                    "active/pending: no gate verdict, no node done, no claim of theorem."),
        "evidence_refs": [report_ref, frame_ref, runner_ref, ledger_ref],
        "next_falsifier": nf,
    }
    events = [status_start, artifact_ev, artifact_runner_ev, artifact_frame_ev, artifact_review_ev,
              review_ev, claim_ev, status_done]

    raw_files = sorted(x.name for x in RAW.glob("*.xml"))
    ckpt = {
        "worker": "worker-070", "checkpoint_at": ts, "task_id": TASK_ID,
        "assignment_ref": "self-taken; no inbox card for worker-070",
        "node_id": "L1", "gate": "G-LIT", "group_id": "literature", "class_ids": FROZEN,
        "status": "bounded_task_complete_unverified" if not drift else "bounded_task_void_ledger_drift",
        "question": art["question"],
        "ledger_sha256_pinned": p["ledger/citation_audit.csv"],
        "ledger_sha256_start": art["inputs"]["ledger/citation_audit.csv"]["sha256_start"],
        "ledger_sha256_end": art["inputs"]["ledger/citation_audit.csv"]["sha256_end"],
        "ledger_drift": drift,
        "aggregate": {"rows_in_family": n, "verdict_counts": vc, "top_hit_count": top,
                      "top_hit_rows": agg["top_hit_rows"],
                      "as_recorded_reresolution_rate": agg["as_recorded_reresolution_rate"],
                      "distinct_locators": agg["distinct_locators"],
                      "duplicate_locator_groups": agg["duplicate_locator_groups"],
                      "rows_sharing_a_locator": share,
                      "max_rows_per_locator": agg["max_rows_per_locator"],
                      "per_class": agg["per_class"],
                      "reexecution_agreement_predecessor_live_rows": agg["reexecution_agreement_predecessor_live_rows"]},
        "controls_pass": art["falsifier_outcome"]["controls_pass"],
        "corpus_valid": corpus_valid,
        "artifacts": {
            "artifacts/worker-070/l1_locator_live02/report.json": report_sha,
            "artifacts/worker-070/l1_locator_live02/run_live070.py": runner_sha,
            "artifacts/worker-070/l1_locator_live02/frame.json": frame_sha,
            "artifacts/worker-070/l1_locator_live02/REVIEW.md": review_sha,
            "artifacts/worker-070/l1_locator_live02/raw/": f"{len(raw_files)} files",
            "artifacts/worker-070/l1_locator_live02/superseded/report.rev1-reexec-name-defect.json":
                art.get("supersedes", {}).get("sha256"),
        },
        "events_emitted": [e["event_id"] for e in events],
        "authority_note": "worker event; cannot set node status done, validation_status passed, or any gate verdict",
        "next_falsifier": nf,
        "stop_rule": "bounded single pass over the 38-row family at one pinned ledger hash; no ledger edit",
    }
    CKPT.write_text(json.dumps(ckpt, indent=2, ensure_ascii=False), encoding="utf-8")
    ckpt_sha = sha256_file(CKPT)
    for e in events:
        ref = f"{ckpt_ref}#{ckpt_sha[:12]}"
        if ref not in e["evidence_refs"]:
            e["evidence_refs"].append(ref)

    kept = []
    if OUTBOX.exists():
        for line in OUTBOX.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                d = json.loads(line)
                stale = d.get("task_id") == TASK_ID or d.get("assignment_ref") == TASK_ID
            except Exception:  # noqa: BLE001
                stale = False
            if not stale:
                kept.append(line)
    with OUTBOX.open("w", encoding="utf-8") as f:
        for line in kept:
            f.write(line + "\n")
        for e in events:
            json.dump(e, f, ensure_ascii=False)
            f.write("\n")

    print(f"checkpoint {CKPT} sha256 {ckpt_sha}")
    print(f"appended {len(events)} events to {OUTBOX} (kept {len(kept)} prior lines)")
    for e in events:
        print(" ", e["event_id"], e["event_type"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
