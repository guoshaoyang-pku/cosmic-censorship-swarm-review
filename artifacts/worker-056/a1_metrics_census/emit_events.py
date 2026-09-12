#!/usr/bin/env python3
"""W056-A1-METRICS-CENSUS-01 — fail-closed outbox emitter.

- Validates every event with the real `research_map/comms.normalize_event` +
  `research_map/schemas.validate_event` before writing (a rejected event id is
  terminal, so pre-flight is the only cheap gate).
- Re-hashes every `path#prefix` evidence/artifact ref from disk and refuses to
  emit if a file is missing or a prefix mismatches.
- Idempotent: skips event_ids already present in the outbox.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "research_map"))
from comms import normalize_event  # noqa: E402
from schemas import validate_event, SchemaError  # noqa: E402

OUTBOX = ROOT / "comms" / "outbox" / "worker-056.jsonl"
TASK = "W056-A1-METRICS-CENSUS-01"
TS = "2026-09-12T01:35:00+08:00"
P = "w056-a1metrics-20260912T0135"

FILES = [
    ("prereg", "artifacts/worker-056/a1_metrics_census/PREREGISTRATION.json", "task_preregistration"),
    ("amend1", "artifacts/worker-056/a1_metrics_census/AMENDMENT-01.json", "control_calibration_amendment"),
    ("amend2", "artifacts/worker-056/a1_metrics_census/AMENDMENT-02.json", "control_calibration_amendment"),
    ("runner", "artifacts/worker-056/a1_metrics_census/run_metrics_census_056.py", "measurement_instrument"),
    ("report", "artifacts/worker-056/a1_metrics_census/report.json", "measurement_report"),
    ("readme", "artifacts/worker-056/a1_metrics_census/README.md", "task_record"),
    ("sums", "artifacts/worker-056/a1_metrics_census/SHA256SUMS", "artifact_manifest"),
    ("pins", "artifacts/worker-056/a1_metrics_census/raw/PINS.json", "input_pins"),
    ("fail1", "artifacts/worker-056/a1_metrics_census/evidence/bringup_controls_FAIL_report.json", "bringup_evidence"),
    ("fail2", "artifacts/worker-056/a1_metrics_census/evidence/bringup2_controls_FAIL_report.json", "bringup_evidence"),
    ("emit", "artifacts/worker-056/a1_metrics_census/emit_events.py", "event_emitter"),
    ("ckpt", "runtime/state/w056_checkpoint_6.json", "worker_checkpoint"),
]


def sha(rel: str) -> str:
    h = hashlib.sha256()
    with (ROOT / rel).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ref(rel: str) -> str:
    return f"{rel}#{sha(rel)[:16]}"


def verify_refs(event: dict) -> None:
    for key in ("evidence_refs", "artifact_refs"):
        for r in event.get(key, []) or []:
            if "#" in r:
                path, prefix = r.rsplit("#", 1)
                if not (ROOT / path).is_file():
                    raise SystemExit(f"  FAIL missing ref file {path}")
                if not sha(path).startswith(prefix):
                    raise SystemExit(f"  FAIL ref hash mismatch {r}")


def build_events() -> list[dict]:
    report = json.loads((HERE / "report.json").read_text())
    res = report["results"]
    m1, m2, m3, d1 = res["M1"], res["M2"], res["M3"], res["D1"]
    ck = "runtime/state/w056_checkpoint_6.json"
    ev = res["corpus"]["events_snapshot_sha256"][:12]
    evidence = [
        ref("artifacts/worker-056/a1_metrics_census/report.json"),
        ref("artifacts/worker-056/a1_metrics_census/PREREGISTRATION.json"),
        ref("artifacts/worker-056/a1_metrics_census/README.md"),
        ref("artifacts/worker-056/a1_metrics_census/raw/PINS.json"),
        ref("artifacts/worker-056/a1_metrics_census/SHA256SUMS"),
        ref(ck),
    ]
    falsifier = (
        "F1 FALSE if `python3 run_metrics_census_056.py --check` against the pinned raw/ snapshots "
        "returns a different result_digest than 78275fb47a88, or two check runs disagree. "
        "F2 FALSE if any raw/ pin moves without a drift entry. F3 FALSE if any control C1-C10 does not "
        "behave as pre-registered. F4 FALSE if an independent re-derivation under the frozen definitions "
        "produces materially different M1/M2/M3. F5 FALSE if a claim counted SINGULAR_FROZEN has a "
        "class_id token list length != 1, or a counted >0.60 duplicate pair measures <=0.60. "
        "F6 FALSE if D1 (0.5628) is quoted as the canonical A0 hard_failure_rate rather than "
        "review-recorded incidence."
    )
    events = [{
        "event_id": f"{P}-take",
        "event_type": "status",
        "created_at": TS,
        "actor": "worker-056",
        "node_id": "A1",
        "node_ids": ["A1", "F0", "F1", "F2a", "F2b", "L0", "L1"],
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "gate": "G-AUDIT",
        "status": "active",
        "hours": 0.5,
        "summary": (
            "No inbox card exists for worker-056 (comms/inbox has no worker-056.jsonl); took ONE bounded "
            "class-bound task: A0 metric census over the accepted stream at one hash-pinned snapshot. Gap: "
            "metrics.class_binding, metrics.duplication/duplicate_cluster_rate and review_protocol kappa/Kish "
            "ESS had zero measurements on the accepted claim/review corpus (0 'duplicate_cluster' occurrences). "
            "Read-only; no canonical, ledger, numerics, review or frozen path written."
        ),
        "evidence_refs": evidence,
        "next_falsifier": falsifier,
    }]
    for slug, path, atype in FILES:
        if not (ROOT / path).is_file():
            continue
        events.append({
            "event_id": f"{P}-art-{slug}",
            "event_type": "artifact",
            "created_at": TS,
            "actor": "worker-056",
            "node_id": "A1",
            "node_ids": ["A1"],
            "class_id": "AF-WCC-VAC-GEN",
            "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
            "gate": "G-AUDIT",
            "artifact_type": atype,
            "path": path,
            "sha256": sha(path),
            "validation_status": "unverified",
            "summary": f"{TASK} artifact {Path(path).name}",
            "evidence_refs": [ref(path), ref(ck)],
            "next_falsifier": falsifier,
        })
    events.append({
        "event_id": f"{P}-claim",
        "event_type": "claim",
        "created_at": TS,
        "actor": "worker-056",
        "node_id": "A1",
        "node_ids": ["A1"],
        "gate": "G-AUDIT",
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "conclusion_type": "numerical_evidence",
        "statement": (
            f"Artifact-and-checker measurement at one hash-pinned accepted-stream snapshot "
            f"(events.snapshot.jsonl sha256 {ev}; {res['corpus']['n_claims']} claim events / "
            f"{res['corpus']['n_reviews']} review events; 0 claim ids excluded by the rejected set; "
            f"12/12 controls PASS; --check reproduces result_digest 78275fb47a88 twice): "
            f"(M1) A0 metrics.class_binding = {m1['class_binding']:.4f} "
            f"(400/584 claims carry exactly one frozen class_id; 167/584 declare multiple frozen classes; "
            f"17/584 declare GLOBAL) against target 1.0. "
            f"(M2) duplication = {m2['duplication']:.4f} and duplicate_cluster_rate = "
            f"{m2['duplicate_cluster_rate']:.4f} (40/584; 28 pairs above 0.60, 17 clusters, largest 3, max "
            f"similarity 1.0), both inside the A0 targets (<=0.25). "
            f"(M3) generalized Fleiss kappa over the 60 multi-review targets = {m3['kappa']:.4f} "
            f"(hash-bound-only robustness subset, 26 targets: {m3['hash_bound_only']['kappa']:.4f}) against the "
            f"A0/G-AUDIT target 0.60, permutation z = {m3['perm_z']:.2f}, and Kish ESS inside the contested "
            f"subset = {m3['kish_ess_multi_subset']:.2f} versus 147 nominal reviewers. "
            f"(D1) review-recorded hard-failure incidence = {d1['review_recorded_hard_failure_incidence']:.4f} "
            f"(408/725), which is NOT the canonical A0 hard_failure_rate. Interpretation boundary: multi-class "
            f"class_id values are often deliberate cross-class scope declarations; whether they count against "
            f"class_binding is the open ledger-scope ruling (BL-7-style), not adjudicated here. No gate verdict, "
            f"no node transition, no canonical write."
        ),
        "assumptions": [
            "corpus = accepted events.jsonl rows of type claim/review minus events named in the rejected set at the same snapshot",
            "metric definitions and thresholds are exactly those operationalized in PREREGISTRATION.json (k=5 shingles, 0.60 HF-07 threshold, literal frozen+singular class_binding)",
            "M3 groups by (target_id, reviewed_sha256-if-present); 425/725 reviews lack a hash, so those groups are revision-agnostic",
            "the snapshot is one instant of a growing append-only stream; live files moved during the run (recorded as live_stream_drift) while the raw/ snapshot did not",
            "D1 counts non-empty review.hard_failures fields and is not the canonical HF-01..HF-14 detector owned by audit_run.py",
        ],
        "falsifier": falsifier,
        "evidence_refs": evidence + [
            ref("artifacts/worker-056/a1_metrics_census/AMENDMENT-01.json"),
            ref("artifacts/worker-056/a1_metrics_census/AMENDMENT-02.json"),
            ref("artifacts/worker-056/a1_metrics_census/evidence/bringup_controls_FAIL_report.json"),
            ref("artifacts/worker-056/a1_metrics_census/evidence/bringup2_controls_FAIL_report.json"),
        ],
        "artifact_refs": [
            ref("artifacts/worker-056/a1_metrics_census/report.json"),
            ref("artifacts/worker-056/a1_metrics_census/run_metrics_census_056.py"),
        ],
        "next_falsifier": falsifier,
    })
    events.append({
        "event_id": f"{P}-blocker-kappa",
        "event_type": "blocker",
        "created_at": TS,
        "actor": "worker-056",
        "node_id": "A1",
        "node_ids": ["A1"],
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "gate": "G-AUDIT",
        "description": (
            "G-AUDIT's reviewer-agreement criterion (kappa >= 0.60) is not met by the live review design at "
            "the pinned snapshot: generalized Fleiss kappa 0.2055 on the 60 multi-review targets (0.1362 on "
            "the 26 hash-bound-only targets), permutation z 2.25, contested-subset Kish ESS 1.74 against 147 "
            "nominal reviewers. The rubric's fallback ('or the review is re-run with a third reviewer') is not "
            "automatically satisfied by adding raters: the measured defect is correlated verdicts / low "
            "effective independence, not a missing rater."
        ),
        "needed_to_unblock": (
            "An audit-lead/controller disposition: either re-run the A0/A1 review under an explicit "
            "independence design and re-measure M3 with this instrument at the new snapshot, or record a "
            "reasoned deviation from the 0.60 kappa criterion at the gate. Worker does not adjudicate which."
        ),
        "evidence_refs": evidence,
        "next_falsifier": falsifier,
    })
    events.append({
        "event_id": f"{P}-final",
        "event_type": "status",
        "created_at": TS,
        "actor": "worker-056",
        "node_id": "A1",
        "node_ids": ["A1", "F1", "F2b", "L0"],
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "gate": "G-AUDIT",
        "status": "active",
        "hours": 0.5,
        "summary": (
            "W056-A1-METRICS-CENSUS-01 delivered at worker level and exiting: measured class_binding 0.6849, "
            "duplication 0.1022 / duplicate_cluster_rate 0.0685 (both inside target), kappa 0.2055 (0.1362 "
            "hash-bound; target 0.60 NOT met), contested-subset Kish ESS 1.74 vs 147 nominal, D1 review-recorded "
            "hard-failure incidence 0.5628 (not the canonical metric). 12/12 controls pass, two determinism "
            "fixes and two control-calibration amendments preserved, bring-up failures archived. No node "
            "completion, no gate verdict, no canonical write; routed to astra-lead-audit for A1/G-AUDIT use."
        ),
        "evidence_refs": evidence,
        "next_falsifier": falsifier,
    })
    return events


def main() -> int:
    events = build_events()
    existing = set()
    if OUTBOX.is_file():
        for line in OUTBOX.read_text(errors="replace").splitlines():
            line = line.strip()
            if line:
                try:
                    existing.add(json.loads(line).get("event_id"))
                except json.JSONDecodeError:
                    pass
    out, skipped = [], 0
    for e in events:
        if e["event_id"] in existing:
            skipped += 1
            continue
        verify_refs(e)
        d = normalize_event(dict(e), "comms/outbox/worker-056.jsonl")
        try:
            validate_event(d)
        except SchemaError as ex:
            print(f"  PREFLIGHT REJECT {e['event_id']}: {ex}")
            return 1
        out.append(e)
    if not out:
        print(f"  nothing to emit (skipped={skipped})")
        return 0
    with OUTBOX.open("a") as f:
        for e in out:
            f.write(json.dumps(e, sort_keys=True) + "\n")
    print(f"  emitted {len(out)} events (skipped={skipped}) -> {OUTBOX.relative_to(ROOT)}")
    for e in out:
        print(f"    {e['event_type']:<9} {e['event_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
