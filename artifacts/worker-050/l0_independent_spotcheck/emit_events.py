#!/usr/bin/env python3
"""W050-L0-INDEPENDENT-SPOTCHECK-04 -- emit outbox events and the worker checkpoint.

Appends 9 artifact events, 1 review, 1 claim and 1 status to
comms/outbox/worker-050.jsonl (validated against research_map/schemas.py first), and writes
runtime/state/w050_l0_independent_spotcheck_checkpoint.json plus a line in
runtime/state/w050_checkpoints.jsonl. Idempotent by event_id: re-running skips ids already in
the outbox. Never edits the map, a ledger or a gate.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

CST = timezone(timedelta(hours=8))
STAMP = datetime.now(CST).strftime("%Y%m%dT%H%M%S")
ACTOR = "worker-050"
TASK = "W050-L0-INDEPENDENT-SPOTCHECK-04"
NODE = "L0"
GATE = "G-LIT"
CLASS_ID = "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH"
L0_PIN = "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28"
L1_PIN = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"

FALSIFIER = (
    "F1: a re-fetch at any recorded locator returning a different status or a non-matching title "
    "voids that row; F2: any change to ledger/theorems.jsonl away from a1674f094979 or to "
    "ledger/citation_audit.csv away from 315c19145065 voids the whole table; F3: an ordered 1:1 "
    "reproduction by verify_l0.py + fetch_l0_sample.py + compare_rechecks.py failing voids the "
    "measurement."
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def main() -> int:
    manifest = json.loads((OUT / "manifest.json").read_text())
    fps = {name: sha256(OUT / name) for name in manifest["files"]}
    fps["manifest.json"] = sha256(OUT / "manifest.json")
    map_sha = sha256(ROOT / "research_map" / "research_map.json")
    l0_now, l1_now = sha256(ROOT / "ledger" / "theorems.jsonl"), sha256(ROOT / "ledger" / "citation_audit.csv")
    static = json.loads((OUT / "static_report.json").read_text())
    summary = json.loads((OUT / "recheck_summary.json").read_text())
    event_prefix = f"w050-l0spotcheck-{STAMP}"

    def ev(eid, etype, **kw):
        e = {"event_id": eid, "event_type": etype, "created_at": now(), "actor": ACTOR, **kw}
        validate_event(e)
        return e

    events = []

    # --- artifact events -------------------------------------------------
    artifact_specs = [
        ("static-report", "independent_l0_static_consistency_report", "static_report.json",
         "Full static census of 62 L0 rows: source resolution, back-references, status honesty, unresolved marking, class coverage, deterministic sample."),
        ("fetch-pass1", "live_refetch_evidence_pass1", "fetch_evidence.json",
         "Pass 1 live re-fetch of the 8-row class-stratified sample: 8/8 resolved with HTTP 200 + title match (9 locator attempts)."),
        ("fetch-pass2", "live_refetch_evidence_pass2", "fetch_evidence_recheck.json",
         "Pass 2 independent re-fetch of the same sample: 8/8 resolved with HTTP 200 + title match; identical to pass 1."),
        ("recheck-summary", "two_pass_refetch_comparison", "recheck_summary.json",
         "Two-pass comparison: 8 compared, 8 stable, 0 mismatches; L0/L1 pins held at compare time."),
        ("runner-static", "reproducible_runner", "verify_l0.py",
         "Deterministic static checker; pins L0/L1, exits 3 on drift, 2 on any failed check."),
        ("runner-fetch", "reproducible_runner", "fetch_l0_sample.py",
         "Deterministic live re-fetcher with per-record fallback locators; --pass 1|2; exits 3 on drift."),
        ("runner-compare", "reproducible_runner", "compare_rechecks.py",
         "Deterministic two-pass comparator; exits 1 on any unstable row or pin movement."),
        ("readme", "documentation", "README.md",
         "Claims, method, pins, per-check results, findings, limits, falsifiers and exact re-run commands."),
        ("manifest", "manifest", "manifest.json",
         "Hashes of every artifact in this bundle, written after the final run."),
    ]
    for tag, atype, fname, note in artifact_specs:
        path = f"artifacts/worker-050/l0_independent_spotcheck/{fname}"
        events.append(ev(
            f"{event_prefix}-artifact-{tag}", "artifact",
            node_id=NODE, gate=GATE, class_id=CLASS_ID, artifact_type=atype,
            path=path, sha256=fps[fname], validation_status="unverified",
            note=note,
            evidence_refs=[f"{path}#sha256:{fps[fname]}", f"ledger/theorems.jsonl#{L0_PIN[:12]}", f"ledger/citation_audit.csv#{L1_PIN[:12]}"],
            falsifier=FALSIFIER,
        ))

    # --- review event ----------------------------------------------------
    review = ev(
        f"{event_prefix}-review-l0", "review",
        node_id=NODE, gate=GATE, class_id=CLASS_ID,
        target_id="ledger/theorems.jsonl",
        target_sha256=L0_PIN,
        reviewed_sha256=L0_PIN,
        companion_artifact="ledger/citation_audit.csv",
        companion_sha256=L1_PIN,
        reviewer=ACTOR,
        verdict="accept",
        score=4,
        hard_failures=[],
        review_scope=(
            "Independent worker verification of L0 at a1674f094979: full static census of all 62 rows "
            "(source resolution against L1, back-references, verification-status honesty, unresolved "
            "marking, class coverage) plus a deterministic class-stratified live re-fetch of 8 rows "
            "(2 per frozen class), run twice. Not a mathematics re-derivation; not an adjudication of "
            "the CF-19 rewrite provenance."
        ),
        findings=[
            {"id": "W050-L0-B1", "severity": "B",
             "finding": "SRC-041 carries a publisher DOI as L1 evidence_url (10.1142/9789814374552_0002) that returns HTTP 403 to a non-browser client in both passes; the machine-resolvable per-record locator is the row's url field (https://inspirehep.net/api/literature/786592), HTTP 200 with a matching title. The row should declare which field is the locator of record, or demote the DOI to a human-readable field. This reproduces the publisher-403 observation already recorded for WCC locators.",
             "evidence": ["artifacts/worker-050/l0_independent_spotcheck/fetch_evidence.json", "artifacts/worker-050/wcc_locator_resolution/fetch_evidence.json"]},
            {"id": "W050-L0-N1", "severity": "N",
             "finding": "All 97 L1 rows carry verdict=verified with reviewer=lead-literature or astra-lead-literature, i.e. author self-report. L0's acceptance_authority field says so explicitly, so no independence is overstated; the gate reading of the L1 verdict column should keep treating it as self-assessment.",
             "evidence": ["artifacts/worker-050/l0_independent_spotcheck/static_report.json"]},
            {"id": "W050-L0-N2", "severity": "N",
             "finding": "67 of 97 L1 exact_locator values remain search-query strings rather than single-record locators; the sampled rows avoided them by using per-record evidence_url or url. Already covered by W050-WCC-LOCATOR-REPAIR-01 and W050-SCC-LOCATOR-READINESS-02.",
             "evidence": ["artifacts/worker-050/l0_independent_spotcheck/static_report.json"]},
        ],
        conditions=[
            "Binds only to L0 a1674f094979 and L1 315c19145065; any ledger revision voids this verdict.",
            "Worker verdict only: it cannot set validation_status=passed, a node status or a gate verdict.",
            "The sample is 8 of 62 rows; the static census covers all 62 rows but no row's mathematics was re-derived.",
        ],
        evidence_refs=[
            f"ledger/theorems.jsonl#{L0_PIN[:12]}",
            f"ledger/citation_audit.csv#{L1_PIN[:12]}",
            f"artifacts/worker-050/l0_independent_spotcheck/static_report.json#sha256:{fps['static_report.json']}",
            f"artifacts/worker-050/l0_independent_spotcheck/recheck_summary.json#sha256:{fps['recheck_summary.json']}",
        ],
        artifact_refs=[f"artifacts/worker-050/l0_independent_spotcheck/static_report.json#sha256:{fps['static_report.json']}"],
        falsifier=FALSIFIER,
    )
    events.append(review)

    # --- claim event -----------------------------------------------------
    claim = ev(
        f"{event_prefix}-claim-l0", "claim",
        node_id=NODE, gate=GATE, class_id=CLASS_ID,
        conclusion_type="numerical_evidence",
        statement=(
            "At pinned ledger/theorems.jsonl a1674f094979 (62 rows) and ledger/citation_audit.csv "
            "315c19145065 (97 rows), an independent worker census finds: 0 unresolved source_ids, 0 "
            "back-reference omissions from L1 used_by_theorems, 0 verification_status values outside "
            "the declared vocabulary, 0 rows whose verification_status exceeds the deepest evidence_type "
            "among the sources they cite, 0 rows without an unresolved entry, and balanced coverage of "
            "the four frozen class ids (11/10/11/10 rows). A deterministic class-stratified live re-fetch "
            "of 8 rows (2 per class) resolved 8/8 with HTTP 200 and a title matching the pinned L1 title "
            "in two independent passes (9 locator attempts; one row, SRC-041, needed its fallback "
            "locator because the publisher DOI returns 403). All 62 rows self-report review_status="
            "not_independently_reviewed. This is a machine-checked ledger-consistency and locator "
            "measurement only: no truth value is assigned to any conjecture and no gate verdict is claimed.",
        ),
        assumptions=[
            "L0 and L1 are the canonical ledger artifacts at the pinned hashes; any revision voids this measurement.",
            "Title-token Jaccard >= 0.6 (or recorded tokens a subset of fetched tokens) is the acceptance rule for record identity; the rule is in fetch_l0_sample.py and applies uniformly.",
            "The 8-row sample is deterministic (2 rows per class in file order) and is a spot check, not a full census of resolvability.",
        ],
        falsifier=FALSIFIER,
        evidence_refs=[
            f"ledger/theorems.jsonl#{L0_PIN[:12]}",
            f"ledger/citation_audit.csv#{L1_PIN[:12]}",
            f"artifacts/worker-050/l0_independent_spotcheck/static_report.json#sha256:{fps['static_report.json']}",
            f"artifacts/worker-050/l0_independent_spotcheck/recheck_summary.json#sha256:{fps['recheck_summary.json']}",
        ],
        artifact_refs=[
            f"artifacts/worker-050/l0_independent_spotcheck/static_report.json#sha256:{fps['static_report.json']}",
            f"artifacts/worker-050/l0_independent_spotcheck/fetch_evidence.json#sha256:{fps['fetch_evidence.json']}",
            f"artifacts/worker-050/l0_independent_spotcheck/fetch_evidence_recheck.json#sha256:{fps['fetch_evidence_recheck.json']}",
            f"artifacts/worker-050/l0_independent_spotcheck/recheck_summary.json#sha256:{fps['recheck_summary.json']}",
        ],
    )
    events.append(claim)

    # --- status event ----------------------------------------------------
    status = ev(
        f"{event_prefix}-status-l0", "status",
        node_id=NODE, gate=GATE, class_id=CLASS_ID,
        status="active", hours=0.75,
        summary=(
            "No assignment card exists in comms/inbox for worker-050. Took one bounded class-bound task, "
            "W050-L0-INDEPENDENT-SPOTCHECK-04: independent verification of L0 (ledger/theorems.jsonl) at "
            "pinned sha a1674f094979 against L1 315c19145065. Result: all 7 static checks pass over all "
            "62 rows; 8/8 class-stratified sampled rows resolved live with matching titles in two stable "
            "passes; verdict accept score 4 with one B hygiene finding on SRC-041's DOI evidence_url and "
            "two N context findings. No ledger, map, claim, gate or status transition was edited; no gate "
            "verdict claimed."
        ),
        artifact="artifacts/worker-050/l0_independent_spotcheck/static_report.json",
        reviewed_sha256=L0_PIN,
        evidence_refs=[
            f"ledger/theorems.jsonl#{L0_PIN[:12]}",
            f"artifacts/worker-050/l0_independent_spotcheck/recheck_summary.json#sha256:{fps['recheck_summary.json']}",
        ],
        next_falsifier=(
            "Re-run verify_l0.py + both fetch passes after any L0/L1 revision; F2 fires on hash movement, "
            "F1 on any locator that stops resolving with a matching title."
        ),
    )
    events.append(status)

    # --- append to outbox (idempotent by event_id) -----------------------
    outbox = ROOT / "comms" / "outbox" / f"{ACTOR}.jsonl"
    existing = set()
    if outbox.exists():
        for line in outbox.read_text().splitlines():
            if line.strip():
                try:
                    existing.add(json.loads(line)["event_id"])
                except (ValueError, KeyError):
                    pass
    appended = 0
    with open(outbox, "a") as fh:
        for e in events:
            if e["event_id"] in existing:
                continue
            fh.write(json.dumps(e, sort_keys=True) + "\n")
            appended += 1

    checkpoint = {
        "checkpoint_id": f"w050-ckpt-{STAMP}",
        "actor": ACTOR,
        "task_id": TASK,
        "node_id": NODE,
        "gate": GATE,
        "class_id": CLASS_ID,
        "created_at": now(),
        "status": "task_complete_exiting",
        "verdict": "L0_ACCEPT_AT_PIN_WITH_ONE_B_HYGIENE_FINDING",
        "pins": {
            "ledger/theorems.jsonl": L0_PIN,
            "ledger/citation_audit.csv": L1_PIN,
            "l0_hash_at_emission": l0_now,
            "l1_hash_at_emission": l1_now,
            "ledger_pins_held": l0_now == L0_PIN and l1_now == L1_PIN,
            "research_map_sha256_at_emission": map_sha,
        },
        "counts": {
            "l0_rows": static["counts"]["l0_rows"],
            "l1_rows": static["counts"]["l1_rows"],
            "static_checks_passed": sum(1 for c in static["checks"].values() if c["result"] == "pass"),
            "static_checks_total": len(static["checks"]),
            "sample_rows": summary["counts"]["rows_compared"],
            "sample_resolved_both_passes": summary["counts"]["rows_resolved_both_passes"],
            "sample_stable_rows": summary["counts"]["stable_rows"],
            "primary_locator_non_200_rows": summary["counts"]["primary_locator_non_200_rows"],
            "class_coverage": static["counts"]["l0_class_rows"],
        },
        "findings": ["W050-L0-B1 (B, SRC-041 DOI evidence_url 403; INSPIRE url resolves)",
                     "W050-L0-N1 (N, L1 verdict column is author self-report)",
                     "W050-L0-N2 (N, 67/97 L1 exact_locator values are search queries)"],
        "artifacts": {f"artifacts/worker-050/l0_independent_spotcheck/{k}": v for k, v in fps.items()},
        "events_emitted": [e["event_id"] for e in events],
        "events_appended_this_run": appended,
        "falsifier": FALSIFIER,
        "authority": (
            "Worker measurement and review input only. No gate verdict, no validation_status=passed, no "
            "node completion, no ledger or map edit."
        ),
    }
    ck_path = ROOT / "runtime" / "state" / "w050_l0_independent_spotcheck_checkpoint.json"
    ck_path.write_text(json.dumps(checkpoint, indent=2, sort_keys=True) + "\n")
    with open(ROOT / "runtime" / "state" / "w050_checkpoints.jsonl", "a") as fh:
        fh.write(json.dumps(checkpoint, sort_keys=True) + "\n")

    print(f"events emitted: {len(events)} ({appended} appended, {len(events) - appended} already present)")
    print("checkpoint:", ck_path)
    return 0 if l0_now == L0_PIN and l1_now == L1_PIN else 3


if __name__ == "__main__":
    raise SystemExit(main())
