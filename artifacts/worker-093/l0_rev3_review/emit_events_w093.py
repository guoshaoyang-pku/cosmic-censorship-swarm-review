#!/usr/bin/env python3
"""Emit worker-093's events for W093-L0-REV3-VERDICT-01 and write the worker checkpoint.

Deterministic, append-only, wall-clock timestamps (CF-14). Re-measures the reviewed ledger
at emit time: if it differs from the hash the review binds, the verdict events are emitted
as void/moving-target instead of binding.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))
ROOT = Path.cwd()
ART = ROOT / "artifacts/worker-093/l0_rev3_review"
REVIEW = ROOT / "reviews/L0-review-093.json"
OUTBOX = ROOT / "comms/outbox/worker-093.jsonl"
STATE = ROOT / "runtime/state"
LEDGER = ROOT / "ledger/theorems.jsonl"
BOUND_LEDGER = "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28"


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main() -> int:
    ts = datetime.now(CST).strftime("%Y%m%dT%H%M%S")
    outputs = {}
    for p in sorted(ART.iterdir()):
        if p.is_file() and p.name != "manifest.json":
            outputs[str(p.relative_to(ROOT))] = {"sha256": sha(p), "bytes": p.stat().st_size}
    outputs[str(REVIEW.relative_to(ROOT))] = {"sha256": sha(REVIEW), "bytes": REVIEW.stat().st_size}
    emitter = Path(__file__).resolve()
    outputs[str(emitter.relative_to(ROOT))] = {"sha256": sha(emitter), "bytes": emitter.stat().st_size}
    manifest = {"task_id": "W093-L0-REV3-VERDICT-01", "actor": "worker-093", "written_at": now(),
                "bound_ledger_sha256": BOUND_LEDGER, "outputs": outputs}
    (ART / "manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True))
    outputs["artifacts/worker-093/l0_rev3_review/manifest.json"] = {
        "sha256": sha(ART / "manifest.json"), "bytes": (ART / "manifest.json").stat().st_size}

    ledger_now = sha(LEDGER)
    binding = ledger_now == BOUND_LEDGER
    report = json.loads((ART / "report.json").read_text())
    review = json.loads(REVIEW.read_text())
    disj = [d["theorem_id"] for d in report["findings"]["hf02_disjunction"]["rows"]]

    def ref(rel: str, n: int = 12) -> str:
        return f"{rel}#{sha(ROOT / rel)[:n]}"

    ev_common = {
        "actor": "worker-093",
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": report["corpus"]["frozen_classes"],
        "gate": "G-LIT",
        "node_id": "L0",
        "created_at": now(),
    }
    events = []

    events.append({**ev_common,
                   "event_id": f"w093-l0rev-{ts}-task-claim",
                   "event_type": "status",
                   "status": "active",
                   "hours": 0.4,
                   "summary": (
                       "No inbox assignment for worker-093. Took one bounded class-bound task, "
                       "W093-L0-REV3-VERDICT-01: blind independent L0 review at the ledger revision measured at "
                       f"review time ({ledger_now[:12]}), re-running the map-requested HF-14 triple predicate and "
                       "testing whether the L0 accept/revise split is a rubric-vs-validator gap. Read-only; no gate "
                       "verdict and no node completion claimed."),
                   "evidence_refs": [ref("ledger/theorems.jsonl"), ref("evaluation_rubric.yaml"),
                                     ref("artifacts/audit/audit_lib.py")],
                   "next_falsifier": report["falsifier"]})

    for name, typ, note in (
            ("review_l0_rev3.py", "review_instrument",
             "Deterministic stdlib-only instrument: re-implements the HF-14 predicate from audit_lib.py:459-473, "
             "the rubric-literal HF-02 class_ids disjunction detector, HF-01 literal, class-binding metric, "
             "citation linkage, duplication; reproduces the canonical validator's record/claim routing; 5 planted "
             "controls + determinism digest; exit 0 iff scan/controls/determinism pass."),
            ("report.json", "audit_report",
             "Machine output at the pinned snapshot: HF-14 0 rows; 8 rubric-literal HF-02 disjunction rows "
             "(D-004,D-005,T-303,T-305,T-402,T-515,T-526,T-528) and the canonical validator does not implement "
             "that branch; 30 literal HF-01 rows; class-binding metric 26/34=0.7647; 0 HF-07 pairs; citation "
             "linkage 92/92 with 0 mismatches; controls 5/5; determinism ok."),
            ("proposed_hf02_disjunction_patch.diff", "proposed_patch",
             "Additive patch to artifacts/audit/audit_lib.py adding check_ledger_class_disjunction(); verified by "
             "loading the patched copy: flags exactly the 8 corpus rows, planted 2-class control fires. Proposal "
             "only; canonical file not edited."),
            ("patched_audit_lib.py", "patch_candidate",
             "Post-patch bytes of artifacts/audit/audit_lib.py used for the patch verification."),
            ("README.md", "summary",
             "One-page summary: revision churn (3e3d3553 -> a1674f09), pinned hashes, results, verdict, patch "
             "options, overlap with worker-023, reproduce command, falsifier, scope limits."),
            ("manifest.json", "manifest", "sha256 of every output + input pin.")):
        events.append({**ev_common,
                       "event_id": f"w093-l0rev-{ts}-artifact-{name.split('.')[0]}",
                       "event_type": "artifact",
                       "artifact_type": typ,
                       "path": f"artifacts/worker-093/l0_rev3_review/{name}",
                       "sha256": outputs[f"artifacts/worker-093/l0_rev3_review/{name}"]["sha256"],
                       "validation_status": "unverified",
                       "task_id": "W093-L0-REV3-VERDICT-01",
                       "evidence_refs": [ref("artifacts/worker-093/l0_rev3_review/report.json")],
                       "note": note})

    events.append({**ev_common,
                   "event_id": f"w093-l0rev-{ts}-review",
                   "event_type": "review",
                   "target_id": "L0",
                   "reviewer": "worker-093",
                   "verdict": review["verdict"] if binding else "inconclusive",
                   "score": review["score"] if binding else None,
                   "hard_failures": review["hard_failures"] if binding else [],
                   "artifact_refs": [ref("reviews/L0-review-093.json"),
                                     ref("artifacts/worker-093/l0_rev3_review/report.json")],
                   "evidence_refs": [f"ledger/theorems.jsonl#{ledger_now[:12]}",
                                     ref("evaluation_rubric.yaml"),
                                     ref("artifacts/audit/audit_lib.py")],
                   "findings": [
                       {"hf": "HF-02", "branch": "rubric-literal disjunction of class_ids",
                        "rows": disj, "count": len(disj),
                        "canonical_validator_implements_branch": False},
                       {"hf": "HF-01", "branch": "literal record reading: conclusion_type=theorem, no artifact_refs",
                        "count": 30, "applicability": "open; author reads detector as claim-scoped"}],
                   "note": ("Binding verdict at the measured bytes." if binding else
                            "VERDICT VOID: ledger moved after the scan; emitted as moving-target, not binding."),
                   "falsifier": report["falsifier"]})

    events.append({**ev_common,
                   "event_id": f"w093-l0rev-{ts}-claim",
                   "event_type": "claim",
                   "conclusion_type": "formal_model",
                   "statement": (
                       f"At ledger/theorems.jsonl#{ledger_now[:12]} (62 rows): (1) the HF-14 triple predicate returns "
                       "0 rows, so the map's requested first check passes at this revision; (2) the A0 rubric's "
                       "literal HF-02 detector 'disjunction of class_ids' fires on 8 rows while the canonical "
                       "validator (audit_run.py routes ledger rows to corpus['records']; check_class_binding reads "
                       "singular claim.get('class_id')) implements no disjunction branch, so the validator and its "
                       "own rubric disagree; (3) literal HF-01 fires on 30 theorem rows with no artifact_refs and the "
                       "record-vs-claim scope is unadjudicated; (4) singular-class binding is 26/34. Verdict: revise "
                       "3.5 at the measured bytes."),
                   "assumptions": report["assumptions"],
                   "evidence_refs": [f"ledger/theorems.jsonl#{ledger_now[:12]}", ref("evaluation_rubric.yaml"),
                                     ref("artifacts/audit/audit_lib.py"), ref("artifacts/audit/audit_run.py"),
                                     ref("reviews/L0-review-093.json"),
                                     ref("artifacts/worker-093/l0_rev3_review/report.json"),
                                     "artifacts/worker-023/l0_hf02/hf02-disjunction-adjudication-023.json#0f86158c5bb7"],
                   "artifact_refs": [ref("reviews/L0-review-093.json"),
                                     ref("artifacts/worker-093/l0_rev3_review/proposed_hf02_disjunction_patch.diff")],
                   "falsifier": report["falsifier"]})

    events.append({**ev_common,
                   "event_id": f"w093-l0rev-{ts}-complete",
                   "event_type": "status",
                   "status": "active",
                   "hours": 0.4,
                   "summary": (
                       "W093-L0-REV3-VERDICT-01 complete at worker level: instrument, report, patch diff, patched "
                       "candidate, README, review and manifest written and hashed; controls 5/5, determinism ok, "
                       f"binding={binding}. No canonical artifact edited; no node completion or gate verdict claimed "
                       "(controller/lead authority)."),
                   "evidence_refs": [ref("artifacts/worker-093/l0_rev3_review/report.json"),
                                     ref("reviews/L0-review-093.json"),
                                     ref("artifacts/worker-093/l0_rev3_review/manifest.json")],
                   "next_falsifier": report["falsifier"]})

    with OUTBOX.open("a") as f:
        for e in events:
            f.write(json.dumps(e, sort_keys=True) + "\n")

    ckpt = {"actor": "worker-093", "task_id": "W093-L0-REV3-VERDICT-01", "checkpoint_at": now(),
            "bound_ledger_sha256": BOUND_LEDGER, "ledger_sha256_at_emit": ledger_now,
            "binding_valid": binding, "verdict": review["verdict"] if binding else "inconclusive",
            "hard_failures": review["hard_failures"] if binding else [],
            "controls_pass": report["controls"]["all_pass"], "determinism_ok": report["determinism_ok"],
            "moving_target_during_scan": report["moving_target"],
            "event_ids": [e["event_id"] for e in events],
            "outputs": {k: v["sha256"] for k, v in outputs.items()},
            "authority_note": "worker event; cannot set node status=done, validation_status=passed, or a gate verdict"}
    (STATE / f"w093_checkpoint_{ts}.json").write_text(json.dumps(ckpt, indent=1, sort_keys=True))
    with (STATE / "w093_checkpoints.jsonl").open("a") as f:
        f.write(json.dumps(ckpt, sort_keys=True) + "\n")

    print(json.dumps({"ledger_now": ledger_now, "binding": binding, "events": len(events),
                      "verdict": ckpt["verdict"], "outputs": outputs,
                      "checkpoint": f"runtime/state/w093_checkpoint_{ts}.json"}, indent=1))
    return 0 if binding else 2


if __name__ == "__main__":
    raise SystemExit(main())
