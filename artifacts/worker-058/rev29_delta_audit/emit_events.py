#!/usr/bin/env python3
"""Emit the validated W058-REV29-DELTA-05 event set and checkpoint 5, then exit.

Idempotent: existing event_ids in comms/outbox/worker-058.jsonl are skipped.
Every artifact path is re-hashed from disk at emit time; a mismatch aborts.
The controller owns ingest into research_map/events.jsonl.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent          # <repo>/artifacts/worker-058/rev29_delta_audit
ROOT = HERE.parents[2]                          # <repo>
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

OUTBOX = ROOT / "comms/outbox/worker-058.jsonl"
CHECKPOINT = ROOT / "runtime/state/w058_checkpoint_5.json"
CHECKPOINT_LOG = ROOT / "runtime/state/w058_checkpoints.jsonl"
REPORT = HERE / "rev29_delta_report.json"


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def now() -> str:
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def main() -> int:
    rep = json.loads(REPORT.read_text())
    ts = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    live = rep["D1_pins"]["measured_at_start"]
    v = rep["verdict"]
    c0 = live["schemas/af_scc_c0_vacuum.yaml"]
    f1 = live["schemas/af_wcc_vacuum.yaml"]
    c2 = live["schemas/af_scc_c2_vacuum.yaml"]
    frozen_sha = rep["D1_pins"]["frozen"]["manifest_sha256"]
    ev = rep["D1_pins"]["frozen"]
    L = {
        "c0": f"schemas/af_scc_c0_vacuum.yaml#{c0}",
        "f1": f"schemas/af_wcc_vacuum.yaml#{f1}",
        "c2": f"schemas/af_scc_c2_vacuum.yaml#{c2}",
        "frozen": f"artifacts/formulation/FROZEN.json#{frozen_sha}",
        "report": f"artifacts/worker-058/rev29_delta_audit/rev29_delta_report.json#{sha(REPORT)}",
        "selftest": f"artifacts/worker-058/rev29_delta_audit/sensitivity_selftest.json#"
                    f"{sha(HERE / 'sensitivity_selftest.json')}",
    }

    artifacts = [
        ("checker", HERE / "audit_rev29_delta.py", "checker",
         "Deterministic read-only rev29 delta checker: pins, FROZEN self-consistency, containment sweep, "
         "packet re-application, L-FORM-03 extraction, F1 delta census, verdict census, recurrence probe."),
        ("report", REPORT, "audit_certificate",
         "Full certificate for the rev29 freeze break: D1-D8 sub-checks, sensitivity, drift guard, verdict."),
        ("selftest", HERE / "sensitivity_selftest.json", "sensitivity_selftest",
         "7 mutants/controls; all expectations met (planted repair masks L-FORM-01, planted inversion fires, "
         "guard blocks silent write, no false positive on the corrected F1 relation)."),
        ("readme", HERE / "README.md", "readme",
         "Human-readable summary, formal relation used, hashes, falsifier, reproduce command."),
    ]

    events = []
    eid = lambda n: f"w058-rev29-{ts}-{n}"  # noqa: E731
    for n, (name, path, atype, summary) in enumerate(artifacts):
        events.append({
            "event_id": eid(f"artifact-{name}"), "event_type": "artifact", "created_at": now(),
            "actor": "worker-058", "node_id": "F1,F2a,F2b", "artifact_type": atype,
            "path": str(path.relative_to(ROOT)), "sha256": sha(path),
            "validation_status": "unverified",
            "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
            "gate": "G-FORM", "summary": summary,
            "authority": "worker evidence only; not a gate verdict or node status",
            "next_falsifier": v["next_falsifier"],
        })

    events.append({
        "event_id": eid("claim"), "event_type": "claim", "created_at": now(), "actor": "worker-058",
        "node_id": "F1,F2a,F2b", "gate": "G-FORM",
        "class_id": "AF-SCC-C0-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-WCC-VAC-GEN",
        "statement": (
            f"Artifact-and-checker result (not a mathematics or physics claim), measured at FROZEN rev29 "
            f"manifest {frozen_sha[:12]} (frozen_at {ev['frozen_at']}, {ev['files_total']} files, "
            f"verify_frozen rc=0): at F2b {c0[:12]} an independent containment sweep still returns the hard "
            f"class_size_predicate_inverted finding and the C0:152 containment denial is live; the F0 "
            f"taxonomy classes.AF-WCC-VAC-GEN.conclusion.text still carries the predicate-inverted SET "
            f"direction; W083's L-FORM-01 diff applies cleanly to the new bytes but its declared target "
            f"3cdcaa44 is stale (new result 2672d95c); f0_binding resolves in all three schemas via the "
            f"refresh direction; and moving one compared taxonomy input silently rewrites the frozen "
            f"consistency evidence and stales the declared hash because the O3 guard is not applied."),
        "conclusion_type": "formal_model",
        "assumptions": [
            "P_tail(gamma) => P_set(gamma) by past-closedness of J^-(q), so the SET predicate is strictly weaker",
            "the rev29 schema hashes are the ones pinned in D1 (c0 b2ab6acb, f1 d9cebb94, c2 e9a27996)",
            "the F2b sweep rules R1/R1b/R2/R3 are the W058 rounds 2-4 rule set, re-instantiated",
        ],
        "falsifier": v["falsifier"],
        "evidence_refs": [L["report"], L["frozen"], L["c0"], L["f1"], L["c2"], L["selftest"]],
        "artifact_refs": [L["report"], L["selftest"]],
    })

    events.append({
        "event_id": eid("review"), "event_type": "review", "created_at": now(), "actor": "worker-058",
        "reviewer": "worker-058", "target_id": f"FROZEN-rev29-delta/{c0[:12]}",
        "node_id": "F1,F2a,F2b", "class_id": "AF-SCC-C0-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-WCC-VAC-GEN",
        "gate": "G-FORM", "verdict": "revise", "score": 2.0,
        "hard_failures": v["hard_failures"],
        "findings": [
            "rev29 moved F1/F2a/F2b hashes while the F2b hard content defect (L-FORM-01, C0:245) remains "
            "live at b2ab6acb; the three predecessor-pin accepts per class are void by the hash move and "
            "F2b cannot supply two full-schema accepts at the live hash.",
            "F2b live-hash accept (worker-061, 00:54:27) is explicitly SCOPED to the variant-CH axis, not "
            "a full-schema verdict; it must not be counted toward G-FORM.",
            "FROZEN rev29 is not a unique object: three byte-distinct generations observed, the last two "
            f"both revision 29 (frozen_at 00:55:02/48 files and {ev['frozen_at']}/{ev['files_total']} files, "
            f"manifest {frozen_sha[:12]}); quote the manifest sha256 with any rev29 citation.",
            "L-FORM-02 closed in letter (declared 9e335e9b == measured) but recurrence is demonstrated "
            "when a compared input moves, because the unguarded checker (de356d99) silently rewrites the "
            "frozen evidence path; W083's O3 dry-run guard is the ready fix.",
            "L-FORM-03 partial: registry and SET delta strength/definition sites are now predicate-scoped "
            "weaker; the G-F0-frozen declared taxonomy conclusion.text still says the set-based reading is "
            "'strictly stronger' (inverted as a predicate statement; needs controller handling because "
            "repairing it voids G-F0).",
        ],
        "evidence_refs": [L["report"], L["selftest"], L["frozen"]],
        "authority": "worker measurement only; no gate verdict",
    })

    events.append({
        "event_id": eid("blocker"), "event_type": "blocker", "created_at": now(), "actor": "worker-058",
        "node_id": "F2b", "gate": "G-FORM",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "description": (
            f"F2b at rev29 {c0[:12]} still fails the recorded repair acceptance: L-FORM-01 "
            f"class_size_predicate_inverted (C0:245) and the C0:152 containment denial are live, and the "
            f"W083 L-FORM-01 patch's declared target hash is stale against the new bytes. The rev29 freeze "
            f"move additionally voided all predecessor-pin verdicts, so F2b has zero full-schema accepts "
            f"at the live hash while carrying a known hard defect."),
        "needed_to_unblock": (
            "One freeze break (rev30) that folds: the L-FORM-01 one-word repair in the canonical C0 and its "
            "mirror (re-pinned target 2672d95c or the then-current hash); the C0:152 containment-denial "
            "repair or an explicit adjudication that the steelman reading is binding; the strength-bucket "
            "mislabel; the F0-taxonomy SET-direction wording with controller sign-off on the G-F0 "
            "consequence; the O3 dry-run guard plus one declared-hash refresh; then re-freeze with a unique "
            "manifest and re-run two blind full-schema F2b reviewers at the new hash."),
        "evidence_refs": [L["report"], L["frozen"], L["c0"]],
        "authority": "worker evidence only; owner action required, no canonical path written",
    })

    events.append({
        "event_id": eid("status"), "event_type": "status", "created_at": now(), "actor": "worker-058",
        "node_id": "F1,F2a,F2b", "gate": "G-FORM", "status": "active", "hours": 1.1,
        "summary": (
            f"W058-REV29-DELTA-05 complete at worker level (one bounded class-bound task; no inbox card "
            f"existed for worker-058, so it took the successor its prior pass pre-registered). Result: "
            f"rev29 pins match and verify_frozen rc=0 at report time, f0_binding resolves in all three "
            f"schemas, F1 anchors 72/213/234 verified and the F1 delta is confined to 12 lines including "
            f"history; F2b L-FORM-01 is STILL LIVE at b2ab6acb with the C0:152 denial and the advisory "
            f"strength bucket; the F0-taxonomy SET direction remains predicate-inverted; L-FORM-02 "
            f"recurs silently on an input move without the O3 guard; sensitivity 7/7, drift guard clean. "
            f"Boundary: worker evidence only; no math truth, node completion or gate verdict claimed."),
        "evidence_refs": [L["report"], L["selftest"], L["frozen"], L["c0"], L["f1"], L["c2"]],
        "next_falsifier": v["next_falsifier"],
    })

    for e in events:
        validate_event(e)

    # hash re-verification for artifact events
    for e in events:
        if e["event_type"] == "artifact":
            p = ROOT / e["path"]
            if not p.exists() or sha(p) != e["sha256"]:
                raise SystemExit(f"artifact hash mismatch at emit time: {e['path']}")

    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            try:
                existing.add(json.loads(line).get("event_id"))
            except Exception:
                pass
    appended = 0
    with OUTBOX.open("a") as fh:
        for e in events:
            if e["event_id"] in existing:
                continue
            fh.write(json.dumps(e) + "\n")
            appended += 1

    cp = {
        "worker": "worker-058", "task_id": "W058-REV29-DELTA-05", "checkpoint_at": now(),
        "node_id": "F1,F2a,F2b", "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate": "G-FORM",
        "verdict": "FAIL",
        "counts": {"hard": len(v["hard_failures"]), "advisory": 1, "sensitivity_cases": 7,
                   "sensitivity_met": 7, "packet_targets_stale": 2},
        "bound_inputs": live,
        "frozen_revision": ev["revision"], "frozen_manifest_sha256": frozen_sha,
        "frozen_frozen_at": ev["frozen_at"], "frozen_self_consistent_at_report": ev["self_consistent"],
        "verify_frozen_rc": ev["verify_frozen_rc"],
        "hard_findings": v["hard_failures"],
        "lform01_live": rep["D3_content"]["lform01_still_live"],
        "lform02_recurrence_demonstrated": rep["D8_recurrence"]["mutated_input_run"]["silently_rewrote"],
        "lform03_hard_sites": [[s["file"], s["field"]] for s in rep["D5_lform03"]["hard_inversions"]],
        "artifact_hashes": {str(p.relative_to(ROOT)): sha(p) for p in
                            [HERE / "audit_rev29_delta.py", REPORT, HERE / "sensitivity_selftest.json",
                             HERE / "README.md"]},
        "events_appended": appended,
        "authority": "worker evidence only; no canonical path written; no gate verdict",
        "next_falsifier": v["next_falsifier"],
    }
    CHECKPOINT.write_text(json.dumps(cp, indent=2) + "\n")
    with CHECKPOINT_LOG.open("a") as fh:
        fh.write(json.dumps({k: cp[k] for k in ("worker", "task_id", "checkpoint_at", "verdict", "counts",
                                                "frozen_revision", "frozen_manifest_sha256")}) + "\n")
    print(json.dumps({"events_validated": len(events), "events_appended": appended,
                      "checkpoint": str(CHECKPOINT.relative_to(ROOT)), "verdict": cp["verdict"],
                      "hard": cp["counts"]["hard"]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
