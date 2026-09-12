#!/usr/bin/env python3
"""Emit W032-CF16-DELTA-02 events to comms/outbox/worker-032.jsonl.

Self-rejection pass first (PROTOCOL rule 5): every artifact must exist with the
declared sha256, the report hash must be the pinned one, the class ids must
match, and every event must pass research_map.schemas.validate_event before a
single line is appended.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CST = timezone(timedelta(hours=8))
OUT = ROOT / "comms" / "outbox" / "worker-032.jsonl"
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

TASK = "W032-CF16-DELTA-02"
D = "artifacts/worker-032/cf16-delta-02"
CLASS_ID = "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN"
REPORT_SHA = "1b6f2222c950b3e275396c3365590105161f85ad0cad3469abbfc4c52650d4ce"
PASS1_SHA = "e9a185ba9fdfeeb266c23e1368b0de94806ea9fae5a56275089da11ec28347f1"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    now = datetime.now(CST).isoformat(timespec="seconds")
    stamp = datetime.now(CST).strftime("%Y%m%dT%H%M")
    report = json.loads((ROOT / D / "report.json").read_text())
    assert report["task_id"] == TASK
    assert report["class_id"] == CLASS_ID

    artifacts = {
        "verification_report": f"{D}/report.json",
        "verification_tool": f"{D}/adjudicate_delta.py",
        "classification_builder": f"{D}/build_classification.py",
        "classification": f"{D}/classification.json",
        "readme": f"{D}/README.md",
        "checkpoint": f"{D}/CHECKPOINT.json",
        "event_emitter": f"{D}/emit_events.py",
        "pinned_map_snapshot": f"{D}/pinned/research_map.ed28b714464e.json",
        "pinned_detector_pre": f"{D}/pinned/class_separation.c266dbceca87.pre.py",
        "pinned_detector_post": f"{D}/pinned/class_separation.a8c04fc31e4a.post.py",
        "detector_diff": f"{D}/detector_diff.txt",
        "drift_observation": f"{D}/drift_observation.json",
    }
    measured = {}
    for kind, rel in artifacts.items():
        p = ROOT / rel
        if not p.is_file():
            print(f"SELF-REJECT: missing artifact {rel}", file=sys.stderr)
            return 1
        measured[kind] = (rel, sha256(p))
    if measured["verification_report"][1] != REPORT_SHA:
        print("SELF-REJECT: report.json changed since the adjudication; re-run required", file=sys.stderr)
        return 1
    if sha256(ROOT / "artifacts/worker-032/cf16-delta/report.json") != PASS1_SHA:
        print("SELF-REJECT: pass-1 report hash mismatch; carried labels not trustworthy", file=sys.stderr)
        return 1
    ckpt_sha = measured["checkpoint"][1]

    ev = []
    ev.append({
        "event_id": f"w032-cf16delta2-{stamp}-status-start",
        "event_type": "status",
        "created_at": now,
        "actor": "worker-032",
        "node_id": "A1",
        "class_id": CLASS_ID,
        "status": "active",
        "hours": 0.15,
        "summary": (
            "W032-CF16-DELTA-02 started (no inbox card for slot 032; self-selected bounded class-bound "
            "task). Scope: adjudicate the CLASSSEP hard set at pinned map ed28b714 (292 claims) under the "
            "controller-applied checker patch a8c04fc31e4a vs the pre-patch c266dbceca87, carry pass-1 "
            "labels forward, run the independent corpus-wide converse false-negative scan, and measure the "
            "patch's false-negative behaviour with positive controls and adversarial scope probes. "
            "Read-only on canonical paths."
        ),
        "evidence_refs": [f"{D}/pinned/research_map.ed28b714464e.json#ed28b714464e"],
        "next_falsifier": "Any survivor or cleared finding is a genuine composite assertion, or a first-order positive control fails under the patched detector.",
    })
    ev.append({
        "event_id": f"w032-cf16delta2-{stamp}-claim",
        "event_type": "claim",
        "created_at": now,
        "actor": "worker-032",
        "node_id": "A1",
        "class_id": CLASS_ID,
        "conclusion_type": "formal_model",
        "statement": (
            "Instrument/checker-calibration measurement, not a mathematics or physics claim. At pinned map "
            "ed28b714 (292 claims, updated_at 00:51:24) the controller-applied 3-line prose exemption "
            "c266dbceca87 -> a8c04fc31e4a reduces the hard CLASSSEP claim-prose set from 20 to 16 (4 "
            "cleared, 0 added); all 4 cleared findings carry pass-1 non-assertion labels "
            "(DETECTOR_SELF_DESCRIPTION, QUOTED_MENTION, NEGATED_MENTION x2). The 16 survivors are all "
            "mention-level (NEGATED 5, QUOTED 5, CASE_LABEL 4, DETECTOR_SELF 1, DESCRIPTIVE 1; 0 GENUINE), "
            "no flagged claim declares a composite class token, and 13/13 findings shared with pass 1 "
            "replicate label and statement hash exactly. An independent converse scan over all 292 claims "
            "finds 51 composite mentions, 26 assertion-cued, 11 unflagged, 0 genuine. Controls pass: 4/4 "
            "first-order positives fire under both revisions, 13/13 negative mentions stay non-genuine, "
            "worker-07 regression 17/0/10/0 PASS for both. Two measured limits of the applied patch: (1) "
            "the exemption regex is evaluated over the whole +/-60 char window, so 4/4 adversarial "
            "concessive-clause probes (O1 'no genuine C0/C2 merge, but ... one class'; O2 'non-merge "
            "bookkeeping step'; O3 'quoted detector output is a false positive'; O4 '... is not a merge') "
            "fire pre-patch and are suppressed post-patch; (2) the stock _MERGE_ASSERT vocabulary misses "
            "'constitutes/forms/is a single + one/single + family|regularity' (4/5 blind-spot probes "
            "missed by both revisions; 'are one family' is caught only via bare 'are one'). The patch does "
            "not close the metagrowth loop: at observation time live map 56478e3f1d19 (320 claims, 17 hard) "
            "had gained exactly one finding since the pin, this worker's own pass-1 claim, which quotes "
            "label counts and '0 genuine assertions that C0 and C2 are one class' - phrasings outside the "
            "trigger list. This task declines to adjudicate its own claim and flags it for an independent "
            "labeler. Concurrent independent replication: worker-098 blocker w098-cps-20260912T0054-blocker-drift "
            "reported the same 20->16 effect and 'safe but insufficient'; worker-049 staged a larger "
            "prose-precision proposal; worker-080 staged a class-id-disjunction candidate; worker-093 named "
            "the growth mechanism. No priority claimed."
        ),
        "assumptions": [
            "The frozen four class ids are the only valid class tokens (ASTRA_HANDOFF hard decision 1).",
            "Carried labels are trustworthy only while the pass-1 report hash e9a185ba9fdfeeb2 matches.",
            "claim event_id + context hash is a stable finding key across the patch; occurrence indices are not.",
            "O1-O4 and B1-B5 are synthetic probes of checker behaviour, not claims found in the corpus.",
        ],
        "falsifier": report["falsifier"],
        "evidence_refs": [
            f"{D}/report.json#{REPORT_SHA[:16]}",
            f"{D}/classification.json#932ad26959cb3471",
            f"{D}/pinned/research_map.ed28b714464e.json#ed28b714464e",
            f"{D}/pinned/class_separation.a8c04fc31e4a.post.py#a8c04fc31e4a",
            f"{D}/detector_diff.txt#2175a335de5821af",
            "artifacts/worker-032/cf16-delta/report.json#e9a185ba9fdfeeb2",
        ],
        "artifact_refs": [f"{D}/report.json#{REPORT_SHA[:16]}"],
    })
    for kind, (rel, digest) in measured.items():
        ev.append({
            "event_id": f"w032-cf16delta2-{stamp}-artifact-{kind}",
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-032",
            "node_id": "A1",
            "class_id": CLASS_ID,
            "artifact_type": kind,
            "path": rel,
            "sha256": digest,
            "validation_status": "unverified",
            "note": "W032-CF16-DELTA-02 artifact; measurement evidence only, not a gate verdict.",
            "evidence_refs": [f"{rel}#{digest[:16]}"],
        })
    ev.append({
        "event_id": f"w032-cf16delta2-{stamp}-review-w098",
        "event_type": "review",
        "created_at": now,
        "actor": "worker-032",
        "target_id": "w098-cps-20260912T0054-blocker-drift",
        "reviewer": "worker-032",
        "verdict": "accept",
        "score": 4.5,
        "hard_failures": [],
        "findings": (
            "Advisory independent replication of the pass-2 drift recheck. Same pins (map ed28b714, "
            "detector a8c04fc31e4a), independently written harness: pre 20 -> post 16, 4 cleared / 0 added, "
            "corpus 17/0/10/0 PASS for both revisions, 0 genuine among survivors, 0 unflagged genuine in the "
            "converse scan. The blocker's 'safe but insufficient' verdict is supported and extended with two "
            "reproducible limits: (1) 4/4 concessive-clause probes show the exemption is window-scoped, so a "
            "trigger phrase can suppress a genuine assertion elsewhere in the +/-60 char window; (2) the "
            "stock _MERGE_ASSERT vocabulary misses 'constitutes/forms/is a single family|regularity' (4/5 "
            "probes), a pre-existing false-negative channel. Deduction only: the patch should not be treated "
            "as closing the CF-16 class until those two channels are addressed or explicitly accepted."
        ),
        "evidence_refs": [
            f"{D}/report.json#{REPORT_SHA[:16]}",
            "artifacts/worker-098/classsep_prose_shadow/drift_recheck.json",
        ],
    })
    ev.append({
        "event_id": f"w032-cf16delta2-{stamp}-blocker-patch-limits",
        "event_type": "blocker",
        "created_at": now,
        "actor": "worker-032",
        "node_id": "A1",
        "class_id": CLASS_ID,
        "description": (
            "Applied checker patch a8c04fc31e4a is safe at pin ed28b714 (20->16 hard, 0 genuine, regression "
            "PASS) but has two measured false-negative channels and does not close the CF-16 metagrowth "
            "class. (1) Window-scoped exemption: the trigger regex is matched over the whole +/-60 char "
            "window, so 4/4 concessive-clause probes with a genuine composite assertion are suppressed "
            "(O1-O4 in report.json#controls.over_suppression_probes). (2) Assertion-vocabulary gap, "
            "pre-existing in both revisions: _MERGE_ASSERT misses 'constitutes/forms/is a single + "
            "one/single + family|regularity' (B1/B3/B4/B5 missed, B2 caught only via bare 'are one'). "
            "(3) Metagrowth: one minute after the pin the live map 56478e3f1d19 (320 claims) had gained "
            "exactly one hard finding - worker-032's own pass-1 claim, using phrasings outside the trigger "
            "list - so the hard count re-mints on the next verification claim."
        ),
        "needed_to_unblock": (
            "Scope the exemption to the assertion's local clause (or require the trigger and the assertion "
            "cue to bind the same C0/C2 mention), extend the assertion vocabulary or document the gap, and "
            "route verification-claim prose through a metalinguistic/quotation channel; re-run the "
            "worker-07 corpus plus the O1-O4/B1-B5 probes at the new pin."
        ),
        "evidence_refs": [
            f"{D}/report.json#{REPORT_SHA[:16]}",
            f"{D}/detector_diff.txt#2175a335de5821af",
            f"{D}/drift_observation.json#c5e5ae69dd06ab88",
            "artifacts/worker-098/classsep_prose_shadow/drift_recheck.json",
            "artifacts/worker-093/classsep_metagrowth/report.json#9d8574474639",
        ],
    })
    ev.append({
        "event_id": f"w032-cf16delta2-{stamp}-status-complete",
        "event_type": "status",
        "created_at": now,
        "actor": "worker-032",
        "node_id": "A1",
        "class_id": CLASS_ID,
        "status": "active",
        "hours": 0.4,
        "summary": (
            "W032-CF16-DELTA-02 complete from the worker side (node completion NOT claimed). CHECKPOINT + "
            f"EXIT. checkpoint {D}/CHECKPOINT.json#{ckpt_sha[:16]} (state copy "
            f"runtime/state/w032_cf16_delta_checkpoint_2.json, same sha256). Result: patch effect 20->16 "
            "(4 cleared, 0 added), 16/16 survivors mention-level with 13/13 carried-label replication, 0 "
            "genuine, converse scan 0 unflagged genuine, controls pass, regression PASS both revisions, "
            "4/4 over-suppression probes fired, 4/5 vocabulary blind-spot probes missed. No gate verdict, "
            "no validation_status=passed, no canonical file or claim text edited."
        ),
        "evidence_refs": [
            f"{D}/CHECKPOINT.json#{ckpt_sha[:16]}",
            f"runtime/state/w032_cf16_delta_checkpoint_2.json#{ckpt_sha[:16]}",
            f"{D}/report.json#{REPORT_SHA[:16]}",
        ],
        "next_falsifier": (
            "Re-run adjudicate_delta.py against a fresh pin: any GENUINE_ASSERTION among survivors or "
            "cleared findings, any first-order positive control failing under the patched detector, any "
            "unflagged first-order merge in the converse scan, or either regression leaving 17/10/0/0 "
            "falsifies this measurement."
        ),
    })

    for e in ev:
        try:
            validate_event(e)
        except Exception as exc:  # noqa: BLE001
            print(f"SELF-REJECT: event {e.get('event_id')} invalid: {exc}", file=sys.stderr)
            return 1
    with OUT.open("a") as f:
        for e in ev:
            f.write(json.dumps(e) + "\n")
    print(f"appended {len(ev)} events to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
