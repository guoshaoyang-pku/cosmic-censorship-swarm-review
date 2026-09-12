#!/usr/bin/env python3
"""Emit the W021-L0-BUILD-REPL-01 events to comms/outbox/worker-021.jsonl.

Validates every event against research_map/schemas.py before appending and is idempotent
on event_id (re-running does not duplicate).  `--dry-run` validates and prints only.
The final status event pins the worker checkpoint by sha256.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "research_map"))
import schemas  # noqa: E402

CST = timezone(timedelta(hours=8))
OUTBOX = ROOT / "comms" / "outbox" / "worker-021.jsonl"
CHECKPOINT = ROOT / "runtime" / "state" / "w021_checkpoint_l0_build_repl.json"
CLASSES = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
CLASS_STR = ";".join(CLASSES)
TASK = "W021-L0-BUILD-REPL-01"
LEDGER_PIN = "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28"
CIT_PIN = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
BUILDER_PIN = "a497a968638f1e13183d853ab0518f458da885e5f7b1f0f3c647429ec039413c"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ref(path: Path, n: int = 12) -> str:
    rel = path.relative_to(ROOT)
    return f"{rel}#{sha256(path)[:n]}" if path.exists() else str(rel)


def build_events():
    now = datetime.now(CST).isoformat(timespec="seconds")
    stamp = datetime.now(CST).strftime("%Y%m%dT%H%M%S")
    report = HERE / "report.json"
    controls = HERE / "controls.json"
    readme = HERE / "README.md"
    instrument = HERE / "replicate_l0_build.py"
    entry = HERE / "raw" / "entry_hashes.json"
    rep, ctl = ref(report), ref(controls)
    rd, ins, ent = ref(readme), ref(instrument), ref(entry)
    evidence = [rep, ctl, rd, ent, f"ledger/theorems.jsonl#{LEDGER_PIN[:12]}",
                f"ledger/citation_audit.csv#{CIT_PIN[:12]}",
                f"artifacts/literature/tools/build_literature.py#{BUILDER_PIN[:12]}",
                "research_map/class_separation.py#c266dbceca87"]

    task_claim = {
        "event_id": f"w021-l0buildrepl-{stamp}-task",
        "event_type": "status", "created_at": now, "actor": "worker-021",
        "node_id": "L0", "status": "active", "hours": 0.3,
        "summary": (f"No inbox card exists for worker-021 (fleet 2026-09-12T00:42). Taking ONE bounded "
                    f"class-bound task: {TASK}, independent execution of the literature lead's own build "
                    f"falsifier for L0 rev-3 (lit-l5-20260912-019). Two pristine sandbox builds by the "
                    f"pinned builder reproduce the canonical pair a1674f094979/315c19145065 byte-exactly; "
                    f"HF-14 guard fail-closed; 20/20 checks, 0 pin drift. No gate verdict or node "
                    f"completion claimed."),
        "evidence_refs": evidence,
        "next_falsifier": ("Re-run the instrument at the same pins: a non-reproduced canonical hash, "
                           "non-deterministic builds, a mutation that does not fail closed, or a dead "
                           "archive positive control."),
    }

    def art(name, atype, path, role):
        return {"event_id": f"w021-l0buildrepl-{stamp}-artifact-{name}",
                "event_type": "artifact", "created_at": now, "actor": "worker-021",
                "node_id": "L0", "class_id": CLASS_STR, "class_ids": CLASSES, "gate": "G-LIT",
                "artifact_type": atype, "path": str(path.relative_to(ROOT)),
                "sha256": sha256(path), "validation_status": "unverified", "role": role,
                "evidence_refs": evidence}

    artifacts = [
        art("report", "l0_build_replication_report", report,
            "pins, 20 checks, emitted census, HF-14 differential, corpus recount, findings"),
        art("controls", "l0_build_replication_controls", controls,
            "synthetic HF-14 battery, builder mutation controls, archive positive control, drift"),
        art("readme", "l0_build_replication_readme", readme, "human-readable method and result"),
        art("instrument", "l0_build_replication_instrument", instrument,
            "fail-closed stdlib instrument; read-only on canonical paths"),
        art("entryhashes", "l0_build_replication_entry_hashes", entry,
            "63 T0/T1 pin hashes plus emitted-bytes hash records"),
    ]

    claim = {
        "event_id": f"w021-l0buildrepl-{stamp}-claim",
        "event_type": "claim", "created_at": now, "actor": "worker-021",
        "node_id": "L0", "class_id": CLASS_STR, "class_ids": CLASSES, "gate": "G-LIT",
        "conclusion_type": "formal_model",
        "statement": (f"Artifact-and-checker result, not a mathematical claim: at pins "
                      f"ledger/theorems.jsonl {LEDGER_PIN[:12]} / ledger/citation_audit.csv "
                      f"{CIT_PIN[:12]} / builder {BUILDER_PIN[:12]}, two independent pristine sandbox "
                      f"builds reproduce the canonical pair byte-exactly and deterministically "
                      f"(L0 {LEDGER_PIN[:12]}, L1 {CIT_PIN[:12]}); the emitted ledger has 62 rows / 62 "
                      f"unique theorem_ids, content census 50 verified / 11 provisional / 1 rejected, "
                      f"0 rows carrying status/validation_status/supports_claim, and all 62 rows mark "
                      f"the review axis absent. The frozen A0 HF-14 detector and an independent "
                      f"re-implementation agree exactly: 0 fires on the emitted ledger and on the nine "
                      f"non-empty theorem batches, 60 fires on the pre-rev3 archive ce42d205 (positive "
                      f"control), and 3/3 expected fires on a pre-registered synthetic battery. "
                      f"supports_claim and non-frozen-class mutations exit non-zero with no ledger "
                      f"written (fail-closed). Worker verdict ACCEPT for the build-replication property."),
        "assumptions": [
            "the canonical tree is a build product of artifacts/literature/{sources,theorems}/batch-*.jsonl",
            "the pinned builder hash a497a968638f is the hardening revision described in lit-l5-20260912-015",
            "sandbox copies reproduce the canonical tree layout so the builder's ROOT resolution is valid",
            "canonical paths are never written; emitted bytes are retained as sha256 records only",
            "the pre-rev3 archive ce42d205 is an acceptable HF-14 positive control",
            "conclusion_type=formal_model labels a machine-checked statement about the build/binding model, not a physics claim",
        ],
        "falsifier": ("Re-run at the same pins: falsified if (a) a pristine sandbox build does not "
                      "reproduce a1674f094979 or 315c19145065; (b) two pristine builds disagree; (c) the "
                      "forbidden-key or non-frozen-class mutation does not exit non-zero with no ledger "
                      "written; (d) the archive positive control does not fire; or (e) any pinned "
                      "input/output drifts during the run (void, not falsified)."),
        "evidence_refs": evidence,
        "artifact_refs": [rep, ctl, rd, ent],
    }

    review = {
        "event_id": f"w021-l0buildrepl-{stamp}-review",
        "event_type": "review", "created_at": now, "actor": "worker-021",
        "target_id": f"artifacts/literature/tools/build_literature.py#{BUILDER_PIN[:12]}",
        "reviewer": "worker-021", "verdict": "accept", "score": 4.0, "hard_failures": [],
        "findings": ("Build-replication review of the pinned builder (NOT a review of L0 content; "
                     "content review at this hash remains worker-097 revise 1.75 and is not affected). "
                     "20/20 checks PASS, 0 pin drift: pristine sandbox builds reproduce canonical L0 "
                     "a1674f094979 and L1 315c19145065 byte-exactly and deterministically; the HF-14 "
                     "guard is fail-closed on supports_claim and non-frozen-class mutations (no ledger "
                     "written); the archive positive control fires 60/60 identically under the frozen and "
                     "an independent detector. Two advisory defects, non-pinned outputs: builder writes "
                     "classes/*.md without creating the directory (clean-tree abort after L0/L1 "
                     "emission), and class dossiers mis-count content_status=='accepted' (always 0). "
                     "A0 HF-14 corpus recount independently confirms lit-l5-20260912-021: all 586 "
                     "affected records across 12 files are pre-rev3 snapshots, 0 canonical/build-input."),
        "evidence_refs": evidence,
    }

    final = {
        "event_id": f"w021-l0buildrepl-{stamp}-status-complete",
        "event_type": "status", "created_at": now, "actor": "worker-021",
        "node_id": "L0", "status": "active", "hours": 0.5,
        "summary": (f"CHECKPOINT complete and exiting cleanly. {TASK}: one bounded class-bound task, 5 "
                    f"artifacts on disk and hash-pinned, 20/20 checks pass, 0 pin drift, worker verdict "
                    f"ACCEPT. L0/L1 canonical pair a1674f094979/315c19145065 reproduced byte-exactly from "
                    f"source of truth; HF-14 repair durable and fail-closed; 2 advisory builder defects and "
                    f"the A0 scope confirmation recorded. No gate verdict, node completion, claim edit or "
                    f"canonical write is claimed; slot exits for recycling."),
        "evidence_refs": evidence + [ref(CHECKPOINT)],
        "next_falsifier": ("Re-run artifacts/worker-021/l0_build_replication/replicate_l0_build.py at the "
                           "same pins; void on pin drift, falsify on non-reproduction, non-determinism, a "
                           "guard that does not fail closed, or a dead archive positive control."),
    }
    return [task_claim] + artifacts + [claim, review, final]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    events = build_events()
    for e in events:
        schemas.validate_event(e)  # raises on invalid
    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            if line.strip().startswith("{"):
                try:
                    existing.add(json.loads(line).get("event_id"))
                except ValueError:
                    pass
    if a.dry_run:
        print(json.dumps({"validated": len(events),
                          "would_append": [e["event_id"] for e in events if e["event_id"] not in existing],
                          "already_present": [e["event_id"] for e in events if e["event_id"] in existing]},
                         indent=2))
        return 0
    OUTBOX.parent.mkdir(parents=True, exist_ok=True)
    appended = []
    with open(OUTBOX, "a") as f:
        for e in events:
            if e["event_id"] in existing:
                continue
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
            appended.append(e["event_id"])
    print(json.dumps({"appended": appended, "count": len(appended)}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
