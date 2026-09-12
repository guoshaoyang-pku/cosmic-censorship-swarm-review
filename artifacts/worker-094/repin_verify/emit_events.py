#!/usr/bin/env python3
"""Emit the W094D-REPIN-VERIFY-01 outbox events (append-only).

Every event is validated against research_map/schemas.py before it is written,
so a schema-invalid event cannot leave this process (the failure mode that
rejected CLM-W094C-CLOSEFIND-BINDING-01 as 'invalid conclusion_type').

Run from the swarm root:  python3 artifacts/worker-094/repin_verify/emit_events.py
"""
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import SchemaError, validate_event  # noqa: E402

CN = timezone(timedelta(hours=8))
NOW = datetime.now(CN).isoformat(timespec="seconds")
P = "artifacts/worker-094/repin_verify/"


def sha(rel: str) -> str:
    h = hashlib.sha256()
    h.update((ROOT / rel).read_bytes())
    return h.hexdigest()


H_CHECKER = sha(P + "check_repin.py")
H_REPORT = sha(P + "report.json")
H_PIN = sha(P + "PINNED.json")
H_SRC = sha(P + "sources/lead_claims.json")
H_CKPT = sha(P + "CHECKPOINT.json")
H_REV = sha("reviews/repin-verify-094.json")
H_TAX = sha("research_map/formulation_taxonomy.yaml")

CLASS = "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH"
CIDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
BASE = dict(actor="worker-094", created_at=NOW, node_id="F0", gate="G-F0",
            class_id=CLASS, class_ids=CIDS)

EVENTS = [
    {**BASE, "event_id": "ART-W094D-REPIN-CHECKER-01", "event_type": "artifact",
     "artifact_type": "verification_checker", "path": P + "check_repin.py", "sha256": H_CHECKER,
     "validation_status": "passed",
     "note": "Re-runnable checker with --self-test negative control; exit 3 = hard failure, "
             "4 = void_moving_target."},
    {**BASE, "event_id": "ART-W094D-REPIN-REPORT-01", "event_type": "artifact",
     "artifact_type": "verification_report", "path": P + "report.json", "sha256": H_REPORT,
     "validation_status": "unverified", "target_sha256": H_TAX,
     "note": "19/27 checks pass; 6 hard check failures; verdict revise; binds snapshot " + NOW + "."},
    {**BASE, "event_id": "ART-W094D-REPIN-PINNED-01", "event_type": "artifact",
     "artifact_type": "hash_pin_set", "path": P + "PINNED.json", "sha256": H_PIN,
     "validation_status": "unverified",
     "note": "Byte pins incl. mtimes for 9 canonical files; any later change voids the verdict."},
    {**BASE, "event_id": "ART-W094D-REPIN-SOURCES-01", "event_type": "artifact",
     "artifact_type": "provenance_snapshot", "path": P + "sources/lead_claims.json",
     "sha256": H_SRC, "validation_status": "unverified",
     "note": "Pinned copies of the three lead events under test plus the taxonomy_cases meta "
             "record and row-token census."},
    {**BASE, "event_id": "ART-W094D-REPIN-CHECKPOINT-01", "event_type": "artifact",
     "artifact_type": "checkpoint", "path": P + "CHECKPOINT.json", "sha256": H_CKPT,
     "validation_status": "unverified",
     "note": "Finalize re-measure: 0 pinned drift between report and checkpoint."},
    {**BASE, "event_id": "ART-W094D-REPIN-REVIEW-01", "event_type": "artifact",
     "artifact_type": "review_report", "path": "reviews/repin-verify-094.json", "sha256": H_REV,
     "validation_status": "unverified"},
    {**BASE, "event_id": "REV-W094D-REPIN-01-EV", "event_type": "review", "target_id": "F0",
     "reviewer": "worker-094", "verdict": "revise", "score": 3.0,
     "hard_failures": ["HF-094D-1", "HF-094D-2"],
     "findings": ["F-094D-1", "F-094D-2", "F-094D-3", "F-094D-4"],
     "artifact": "reviews/repin-verify-094.json", "artifact_sha256": H_REV,
     "result_summary": "19/27 checks pass; 2 substantive hard failures (consistency_evidence sha "
                       "stale in 3 schemas; corpora absent from FROZEN rev28); freeze-hold "
                       "verified; 00:37:22 repin-DONE claim premature with superseded hash",
     "summary": "Independent re-verification of astra-life03-repin-claims + astra-life04-freeze-hold "
                "at the bytes of " + NOW + ": FROZEN rev28 matches all six canonical pins "
                "(freeze-hold verified). HF-094C-1 is CLOSED (36/36 case rows rebind "
                "0abb9ed8a961) but that rewrite happened at 00:42:36, 5m14s AFTER the 00:37:22 "
                "'re-pins DONE' claim and 3m38s after lifecycle close, so the claim was premature "
                "and cites superseded f0c20b96f76d. HF-094C-2 persists unchanged: all three "
                "schemas declare consistency_evidence_sha256 675a99d0 vs measured 9e335e9b. New "
                "structural finding: neither gate-evidence corpus is in FROZEN rev28, so the "
                "corpus move produced no revision bump. Worker verdict is advisory only.",
     "evidence_refs": [P + "report.json#" + H_REPORT[:12], P + "PINNED.json#" + H_PIN[:12],
                       P + "sources/lead_claims.json#" + H_SRC[:12],
                       "artifacts/formulation/FROZEN.json#2f358f6722d9",
                       "schemas/taxonomy_cases.jsonl#ccf7041bd0ff",
                       "schemas/f1_falsifier_tests.jsonl#56bcb4b3234b",
                       "schemas/af_wcc_vacuum.yaml#cce9c60146d6",
                       "schemas/af_scc_c2_vacuum.yaml#5476a3f2c6bc",
                       "schemas/af_scc_c0_vacuum.yaml#55d0a1ea9bda",
                       "artifacts/formulation/evidence/taxonomy_consistency.json#9e335e9ba1bf",
                       "research_map/formulation_taxonomy.yaml#0abb9ed8a961"],
     "artifact_refs": ["reviews/repin-verify-094.json", P + "check_repin.py#" + H_CHECKER[:12],
                       P + "report.json#" + H_REPORT[:12], P + "PINNED.json#" + H_PIN[:12],
                       P + "sources/lead_claims.json#" + H_SRC[:12],
                       P + "CHECKPOINT.json#" + H_CKPT[:12]],
     "next_falsifier": "Repin consistency_evidence_sha256 to 9e335e9ba1bf in all three schemas "
                       "(both trees), list both corpora in FROZEN, and re-emit an artifact event "
                       "carrying ccf7041bd0ff; then re-run check_repin.py --prior on this run's "
                       "PINNED.json. If all hard checks pass and the declared-F0 sha "
                       "0abb9ed8a961 is unchanged, this revise is superseded by an accept. Any "
                       "change to the declared-F0 sha voids this verification."},
    {**BASE, "event_id": "CLM-W094D-REPIN-BINDING-01", "event_type": "claim",
     "conclusion_type": "formal_model",
     "statement": "FORMAL-MODEL-LEVEL binding finding (not a mathematical theorem, not a numerical "
                  "result) at snapshot " + NOW + " for classes AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN, "
                  "AF-SCC-C0-VAC-GEN, AF-WCC-SCALAR-SPH (node F0, gate G-F0): the "
                  "astra-life04-freeze-hold is verified (FROZEN rev28 2f358f6722d9 matches all six "
                  "measured canonical pins), but the astra-life03-repin-claims completion claim is "
                  "not: its cited schemas/taxonomy_cases.jsonl hash f0c20b96f76d was rewritten at "
                  "00:42:36 to ccf7041bd0ff (36/36 rows now bind 0abb9ed8a961), i.e. 5m14s after "
                  "the 00:37:22 claim and 3m38s after the 00:38:58 lifecycle close; and all three "
                  "class schemas still declare consistency_evidence_sha256=675a99d0d25b2b37 "
                  "against the measured artifacts/formulation/evidence/taxonomy_consistency.json="
                  "9e335e9ba1bfcf77 (the hash FROZEN rev28 itself lists). Neither corpus is listed "
                  "in FROZEN rev28, so the 00:42:36 move produced no revision bump. The binding "
                  "chain is therefore not frozen at a single hash set.",
     "assumptions": ["the measured sha256 values in report.json are the bytes at snapshot " + NOW,
                     "the ingested event text for lead-form-20260912T003722-01 is the lead's "
                     "emitted claim (pinned copy in sources/lead_claims.json)",
                     "an mtime later than a claim's created_at proves the bytes the claim cites "
                     "had already been replaced when the claim was emitted"],
     "falsifier": "Re-measure schemas/taxonomy_cases.jsonl with all 36 rows asserting the "
                  "declared-F0 sha, all three schemas declaring "
                  "consistency_evidence_sha256=9e335e9ba1bf, both corpora listed in FROZEN, and an "
                  "artifact event carrying ccf7041bd0ff or later; then this claim is void. A later "
                  "file write alone is not a falsifier: the claim binds only the snapshot above.",
     "evidence_refs": [P + "report.json#" + H_REPORT[:12], P + "sources/lead_claims.json#" + H_SRC[:12],
                       "schemas/taxonomy_cases.jsonl#ccf7041bd0ff",
                       "schemas/af_wcc_vacuum.yaml#cce9c60146d6",
                       "schemas/af_scc_c0_vacuum.yaml#55d0a1ea9bda",
                       "artifacts/formulation/FROZEN.json#2f358f6722d9",
                       "artifacts/formulation/evidence/taxonomy_consistency.json#9e335e9ba1bf"],
     "artifact_refs": ["reviews/repin-verify-094.json", P + "report.json#" + H_REPORT[:12],
                       P + "sources/lead_claims.json#" + H_SRC[:12]]},
    {**BASE, "event_id": "ST-W094D-REPIN-01", "event_type": "status", "status": "done", "hours": 0.2,
     "summary": "W094D-REPIN-VERIFY-01 complete at worker level (not a node done and not a gate "
                "verdict): one class-bound task, independent 27-check verification of "
                "astra-life03-repin-claims + astra-life04-freeze-hold at the measured bytes; "
                "verdict revise with 2 substantive hard failures, 4 findings, freeze-hold verified, "
                "and a 00:42:36 mid-window corpus repin detected and pinned. Artifacts hash-pinned, "
                "checker re-runnable, checkpoint written.",
     "evidence_refs": [P + "CHECKPOINT.json#" + H_CKPT[:12], P + "report.json#" + H_REPORT[:12],
                       "reviews/repin-verify-094.json#" + H_REV[:12]],
     "next_falsifier": "Re-run check_repin.py --prior on this run's PINNED.json after the author "
                       "repins the three consistency_evidence_sha256 fields, lists both corpora in "
                       "FROZEN, and re-emits an artifact event carrying ccf7041bd0ff; if all hard "
                       "checks pass at an unchanged declared-F0 sha 0abb9ed8a961 this verdict is "
                       "superseded by an accept."},
]


def main() -> int:
    lines = []
    for ev in EVENTS:
        try:
            validate_event(dict(ev))
        except SchemaError as e:
            raise SystemExit(f"refusing to emit {ev.get('event_id')}: {e}")
        lines.append(json.dumps(ev, sort_keys=True))
        print(f"VALID  {ev['event_type']:8} {ev['event_id']}")
    with (ROOT / "comms/outbox/worker-094.jsonl").open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"appended {len(lines)} events")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
