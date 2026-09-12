#!/usr/bin/env python3
"""Emit the W008-FORMSEP04-CANDIDATE-VALIDATION-01 events (dry-run by default).

Appends upward events to comms/outbox/deepseek-flash-08.jsonl only with --emit.
Validates every event against research_map/schemas.validate_event and refuses to emit
an event_id already present in the outbox, inbox, accepted stream or rejects file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event, SchemaError  # noqa: E402

CST = timezone(timedelta(hours=8))
OUTBOX = ROOT / "comms/outbox/deepseek-flash-08.jsonl"
PROPOSED = ROOT / "artifacts/worker08/rev29_candidate/events_proposed.jsonl"
SEEN_FILES = [
    OUTBOX,
    ROOT / "comms/inbox/deepseek-flash-08.jsonl",
    ROOT / "research_map/events.jsonl",
    ROOT / "comms/rejected.jsonl",
]

TASK_ID = "W008-FORMSEP04-CANDIDATE-VALIDATION-01"
NODE = "F2"
GATE = "G-CLASSBIND"
CLASSES = "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN"
CAND = "artifacts/worker08/rev29_candidate/af_scc_c0_vacuum.repair-candidate.yaml"
BUNDLE = "artifacts/worker08/rev29_candidate_validation.json"
REPORT = "artifacts/worker08/rev29_candidate_validation.md"
HARNESS = "artifacts/worker08/rev29_candidate_validate.py"
CKPT = "runtime/state/worker-008_candidate_validation_checkpoint.json"
BATT = "artifacts/worker08/rev29_candidate/battery_candidate.json"
DUAL = "artifacts/worker08/rev29_candidate/dual_candidate.json"


def sha(p: str) -> str:
    h = hashlib.sha256()
    with open(ROOT / p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parent_sha(p: str) -> str:
    return sha(p + ".sha256") if (ROOT / (p + ".sha256")).is_file() else ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit", action="store_true")
    args = ap.parse_args()

    now = datetime.now(CST).isoformat(timespec="seconds")
    stamp = datetime.now(CST).strftime("%Y%m%dT%H%M%S%z")
    actor = "worker-008"
    h_cand, h_bundle, h_report = sha(CAND), sha(BUNDLE), sha(REPORT)
    h_harness, h_ckpt, h_batt, h_dual = sha(HARNESS), sha(CKPT), sha(BATT), sha(DUAL)
    bundle = json.loads((ROOT / BUNDLE).read_text())

    common = {
        "actor": actor,
        "agent_id": "deepseek-flash-08",
        "agent_slot": "worker-008",
        "node_id": NODE,
        "gate": GATE,
        "class_id": CLASSES,
        "class_ids": CLASSES.split(";"),
        "authority_note": (
            "Worker-level measurement only: no node status=done, no validation_status="
            "passed, no gate verdict, no theorem. Canonical paths read-only; interpretation "
            "owned by astra-lead-formulation. Pre-publication decision support for the "
            "pending F2b rev14 two-leaf repair."
        ),
        "created_at": now,
    }

    def ev(eid, etype, **kw):
        e = dict(common)
        e.update(event_id=f"w008-candval-{stamp}-{eid}", event_type=etype)
        e.update(kw)
        return e

    falsifier = bundle["falsifier"]
    evidence = [
        f"{CAND}#{h_cand[:12]}",
        f"{BUNDLE}#{h_bundle[:12]}",
        f"{HARNESS}#{h_harness[:12]}",
        f"{BATT}#{h_batt[:12]}",
        f"{DUAL}#{h_dual[:12]}",
        f"{CKPT}#{h_ckpt[:12]}",
        "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
        "schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3",
        "artifacts/formulation/FROZEN.json#815e08079aef",
    ]

    events = [
        ev("artifact-harness", "artifact", artifact_type="tool", path=HARNESS,
           sha256=h_harness, validation_status="unverified",
           summary="Revision-agnostic FORM-SEP-04 candidate-validation harness: reconstructs "
                   "the announced F2b two-edit candidate from live bytes, checks minimality, "
                   "runs the X1-X5 battery and the fail-closed dual checker with controls."),
        ev("artifact-candidate", "artifact", artifact_type="repair_candidate", path=CAND,
           sha256=h_cand, validation_status="unverified",
           summary="Non-canonical reconstructed F2b repair candidate: live rev13 C0 "
                   "b2ab6acb2bbe + exactly the two reference containment edits. Hash equals "
                   "worker-066's announced rebased candidate 84b5d3fa29a6. Owner publishes; "
                   "this path is not a canonical schema."),
        ev("artifact-validation", "artifact", artifact_type="evidence", path=BUNDLE,
           sha256=h_bundle, validation_status="unverified",
           summary="Validation bundle: pins, reconstruction proof (byte-exact announced-hash "
                   "reproduction, 2 changed lines / 2 changed leaf paths, no metadata moved), "
                   "battery and dual-checker results on candidate and canonical control, and "
                   "the wrong-expect fail-closed control."),
        ev("artifact-report", "artifact", artifact_type="report", path=REPORT,
           sha256=h_report, validation_status="unverified",
           summary="Human-readable candidate-validation report with results table, falsifier, "
                   "and limitations."),
        ev("claim-candidate", "claim", statement=(
            "At the live pins C0 schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe (rev13), C2 "
            "schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3 and FROZEN rev29 "
            "artifacts/formulation/FROZEN.json#815e08079aef (frozen_at 2026-09-12T00:57:26), "
            "the F2b containment repair candidate announced by worker-066 as sha256 "
            "84b5d3fa29a677ad157b924675bb5a9c08281395920be0221535465a5da44b40 is independently "
            "byte-reproducible from the live C0 bytes plus exactly the two reference edits "
            "(2 changed lines; changed leaf paths exactly "
            "regularity.must_not_conflate[0] and "
            "implication_ledger.forbidden_transfers[0].reason; revision/f0_binding/pointers "
            "unmoved). On the reconstructed candidate the full FORM-SEP-04 X1-X5 acceptance "
            "battery returns PASS with 0 expectation violations, 0 unjustified foreign-"
            "semantics hits, 0 converse assertions, 0 containment inversions, 0 composite-"
            "regularity violations, 0 hard failures, and both class schemas pass the "
            "structural gate; the fail-closed dual containment checker returns PASS with 0 "
            "findings. The unrepaired live C0 bytes measured at the same instant still FAIL "
            "both checkers with exactly the two owner-tracked defects (battery X3c=1 at "
            "forbidden_transfers[0].reason; dual 3 findings / 2 kinds including "
            "must_not_conflate[0]). A wrong-expectation run of the dual checker exits 3 with "
            "the FAIL-CLOSED sentinel and no checks, so the PASS cannot be manufactured by "
            "re-pointing the expectation. This is an artifact-and-checker measurement at "
            "worker level; it sets no gate verdict, node status or validation_status, and it "
            "does not re-adjudicate the normativity of the two carriers."
        ), conclusion_type="formal_model", assumptions=[
            "live canonical C0/C2/FROZEN bytes are the FROZEN rev29 pins measured at run time",
            "the two repair fragments are the rev12 reference wording (a different owner "
            "wording clears the same logical defects but hashes differently)",
            "the candidate is non-canonical and unpublished; the owner owns any rev14 wording "
            "and re-freeze",
            "X1-X5 battery and dual checker are the worker's own instruments, controls fired",
        ], falsifier=falsifier, evidence_refs=evidence,
           artifact_refs=[f"{CAND}#{h_cand[:12]}", f"{BUNDLE}#{h_bundle[:12]}"],
           gate=GATE),
        ev("status", "status", status="active", hours=0.4, evidence_refs=evidence,
           next_falsifier=falsifier,
           checkpoint_ref=f"{CKPT}#{h_ckpt[:12]}",
           summary=(
               "CHECKPOINT + EXIT. One bounded class-bound task taken and completed at worker "
               "level (no card issued; FORM-SEP-04 lane, F2/G-CLASSBIND). "
               "W008-FORMSEP04-CANDIDATE-VALIDATION-01: reconstructed worker-066's announced "
               "rebased F2b repair candidate 84b5d3fa29a6 byte-exactly from the live C0 "
               "b2ab6acb2bbe bytes plus the two reference edits (2 changed lines / 2 changed "
               "leaf paths, no metadata moved; announced hash reproduced); candidate PASSes "
               "the full FORM-SEP-04 X1-X5 battery (0 violations, 0 hard failures) and the "
               "fail-closed dual checker (0 findings), while the canonical control still "
               "FAILs both with the two owner-tracked L-FORM-01 defects at :152 and :246; "
               "wrong-expectation control fails closed (exit 3, FAIL-CLOSED). Verdict "
               "CANDIDATE_CLEARS_FORMSEP04. This pre-validates the pending rev14 repair "
               "surface for the owner. No gate verdict, node status, validation_status or "
               "theorem claimed. Read-only on canonical paths. Checkpoint "
               f"{CKPT}; worker exits."
           )),
    ]

    # ---- validate + uniqueness ------------------------------------------------
    problems = []
    for e in events:
        try:
            validate_event(e)
        except SchemaError as exc:
            problems.append(f"{e['event_id']}: {exc}")
    seen = set()
    for p in SEEN_FILES:
        if not p.is_file():
            continue
        with p.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if '"event_id"' not in line:
                    continue
                try:
                    seen.add(json.loads(line).get("event_id"))
                except Exception:  # noqa: BLE001
                    continue
    for e in events:
        if e["event_id"] in seen:
            problems.append(f"{e['event_id']}: duplicate event_id")
    if problems:
        print("VALIDATION FAILED:")
        for p in problems:
            print(" -", p)
        return 1

    body = "\n".join(json.dumps(e, sort_keys=True) for e in events) + "\n"
    PROPOSED.parent.mkdir(parents=True, exist_ok=True)
    PROPOSED.write_text(body)
    print(body)
    print(f"[ok] {len(events)} events valid; unique; proposed copy {PROPOSED.relative_to(ROOT)}")
    if args.emit:
        with OUTBOX.open("a", encoding="utf-8") as f:
            f.write(body)
        print(f"[emitted] appended {len(events)} events to {OUTBOX.relative_to(ROOT)}")
    else:
        print("[dry-run] no outbox write (re-run with --emit)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
