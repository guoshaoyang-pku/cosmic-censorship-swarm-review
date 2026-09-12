#!/usr/bin/env python3
"""Emit the W092-F2A-REV13-FULL-01 artifacts, events and checkpoint.

Writes:
  - manifest.json / SHA256SUMS.txt            (artifact hashes)
  - comms/outbox/worker-092.jsonl             (append-only; idempotent per event_id)
  - runtime/state/worker-092_F2A_rev13_checkpoint.json

No canonical path is written.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUTBOX = ROOT / "comms/outbox/worker-092.jsonl"
CKPT = ROOT / "runtime/state/worker-092_F2A_rev13_checkpoint.json"

ARTIFACTS = {
    "report": HERE / "report.json",
    "instrument": HERE / "verify_f2a_rev13.py",
    "readme": HERE / "README.md",
    "review_json": HERE / "review.json",
    "claim_json": HERE / "claim.json",
}
NODE, CLASS, GATE = "F2a", "AF-SCC-C2-VAC-GEN", "G-FORM"
F2A_SHA = "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe"
FROZEN_SHA = "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stamp", required=True, help="ISO8601 created_at for this batch")
    a = ap.parse_args()
    stamp = a.stamp
    batch = "w092-r13-" + stamp.replace(":", "").replace("-", "")[:15]

    manifest = {k: {"path": str(p.relative_to(ROOT)), "sha256": sha(p), "bytes": p.stat().st_size}
                for k, p in ARTIFACTS.items()}
    (HERE / "manifest.json").write_text(json.dumps(
        {"task_id": "W092-F2A-REV13-FULL-01", "created_at": stamp,
         "pins": {"schemas/af_scc_c2_vacuum.yaml": F2A_SHA,
                  "artifacts/formulation/FROZEN.json": FROZEN_SHA},
         "artifacts": manifest}, indent=1, sort_keys=True) + "\n")
    manifest["manifest"] = {"path": "artifacts/worker-092/f2a_rev13_review/manifest.json",
                            "sha256": sha(HERE / "manifest.json"), "bytes": (HERE / "manifest.json").stat().st_size}
    sums = "\n".join(f"{v['sha256']}  {v['path']}" for v in manifest.values()) + "\n"
    (HERE / "SHA256SUMS.txt").write_text(sums)

    def ev(eid, etype, **kw):
        base = {"actor": "worker-092", "event_id": eid, "event_type": etype, "created_at": stamp}
        base.update(kw)
        return base

    # prior artifact events for the same path with a different hash are superseded by this batch
    prior = []
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            try:
                prior.append(json.loads(line))
            except Exception:
                pass

    def superseded_by(path, new_hash):
        return sorted({e["event_id"] for e in prior
                       if e.get("event_type") == "artifact" and e.get("path") == path
                       and e.get("sha256") != new_hash})

    events = []
    for key, meta in manifest.items():
        body = dict(node_id=NODE, class_id=CLASS, gate=GATE,
                    artifact_type=key, path=meta["path"], sha256=meta["sha256"],
                    validation_status="unverified",
                    summary=f"W092-F2A-REV13-FULL-01 {key} artifact (sha256 {meta['sha256'][:12]}).",
                    falsifier="A file whose bytes differ from the recorded sha256 voids the affected citation.")
        sup = superseded_by(meta["path"], meta["sha256"])
        if sup:
            body["supersedes"] = sup
        events.append(ev(f"{batch}-artifact-{key}", "artifact", **body))
    review = json.loads((HERE / "review.json").read_text())
    review.update({"actor": "worker-092", "event_id": f"{batch}-review-f2a", "event_type": "review",
                   "created_at": stamp})
    events.append(review)
    claim = json.loads((HERE / "claim.json").read_text())
    claim.update({"actor": "worker-092", "event_id": f"{batch}-claim", "event_type": "claim",
                  "created_at": stamp})
    events.append(claim)
    events.append(ev(
        f"{batch}-blocker-evidence-binding", "blocker", node_id=NODE, class_id=CLASS, gate=GATE,
        description="F2a at rev13 e9a27996 cannot receive a clean accept: the declared consistency-evidence hash resolves (I2a closed) but the 495-byte evidence embeds no sha256 of either compared tree, so the standing HF-043-2 / HF-035-F2A-2 / HF-19-F2A-3 closures remain unsatisfied; additionally the canonical evidence path was rewritten at 00:59:25 after the schema checked_at 00:53:20 (bytes unchanged) because the frozen-pinned checker rewrites it unconditionally.",
        needed_to_unblock="Owner lands a bound consistency-evidence revision that embeds map_taxonomy_sha256=0abb9ed8a961 and lead_contract_sha256=d7419b4e8963, plus a non-writing guard (or a sandbox-only checker policy), then re-freezes and re-stamps. Controller rules W090-VOCAB-01 registry authority. Owner freezes M' manifold category and iota regularity in extension_predicate. Owner rebases the semantic-escape corpus to the live authoring C0 and re-runs run_acceptance.py.",
        evidence_refs=["artifacts/worker-092/f2a_rev13_review/report.json#" + manifest["report"]["sha256"][:12],
                       "reviews/F2a-review-rev27-c.json", "reviews/F2a-review-043.json",
                       "artifacts/worker-086/evbind_repair_demo/report.json",
                       "artifacts/worker-022/evbind_guard/report.json"]))
    events.append(ev(
        f"{batch}-status-complete", "status", node_id=NODE, class_id=CLASS, gate=GATE,
        status="active", hours=1.0,
        summary="CHECKPOINT W092-F2A-REV13-FULL-01 complete (worker level): independent full-schema F2a verification at FROZEN rev29 815e0807 / F2a e9a27996 delivered as revise 3.5; class content clean, 25 checks, 12/12 controls, 13/13 pins entry==exit; four card items closed except the evidence hash-boundness half (I2b); 5 hash-bound hard failures with individual falsifiers. Node status deliberately unchanged (worker events carry no authority).",
        evidence_refs=["artifacts/worker-092/f2a_rev13_review/manifest.json#" + manifest["manifest"]["sha256"][:12],
                       "artifacts/worker-092/f2a_rev13_review/report.json#" + manifest["report"]["sha256"][:12],
                       "runtime/state/worker-092_F2A_rev13_checkpoint.json"],
        next_falsifier="Re-run verify_f2a_rev13.py after the evidence-tree binding and non-writing guard land; any pre-registered pin move voids this verdict for the moved bytes."))

    seen = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            try:
                seen.add(json.loads(line).get("event_id"))
            except Exception:
                pass
    appended = 0
    with OUTBOX.open("a") as fh:
        for e in events:
            if e["event_id"] in seen:
                continue
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
            appended += 1

    ck = {"task_id": "W092-F2A-REV13-FULL-01", "actor": "worker-092", "created_at": stamp,
          "node_id": NODE, "class_id": CLASS, "gate": GATE, "verdict": "revise", "score": 3.5,
          "pins": {"schemas/af_scc_c2_vacuum.yaml": F2A_SHA,
                   "artifacts/formulation/FROZEN.json": FROZEN_SHA,
                   "artifacts/formulation/evidence/taxonomy_consistency.json":
                       "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b"},
          "artifacts": {k: v["sha256"] for k, v in manifest.items()},
          "events_emitted": [e["event_id"] for e in events if e["event_id"] not in seen],
          "events_skipped_duplicate": sorted(e["event_id"] for e in events if e["event_id"] in seen),
          "hard_failures": [h["id"] for h in review["hard_failures"]],
          "next_falsifier": review.get("next_falsifier"),
          "authority": "worker measurement only; no node status, validation_status or gate verdict"}
    CKPT.write_text(json.dumps(ck, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({"appended": appended, "checkpoint": str(CKPT.relative_to(ROOT)),
                      "manifest_sha256": manifest["manifest"]["sha256"][:12]}, indent=1))


if __name__ == "__main__":
    main()
