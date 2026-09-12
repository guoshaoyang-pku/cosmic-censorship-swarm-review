#!/usr/bin/env python3
"""W066-F2B-CONTAINMENT-NORMATIVITY-01 erratum: FROZEN moved rev28 -> rev29 after the
checkpoint while the reviewed target bytes did not move.  Records the new freeze hash and
confirms the frozen declaration still points at the reviewed bytes."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "research_map"))
from schemas import validate_event  # noqa: E402

CST = timezone(timedelta(hours=8))
TASK = "W066-F2B-CONTAINMENT-NORMATIVITY-01"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def main() -> None:
    frozen = json.loads((REPO / "artifacts/formulation/FROZEN.json").read_text())
    frozen_sha = sha(REPO / "artifacts/formulation/FROZEN.json")
    files = frozen.get("files") or {}
    decl = {k: (files.get(k) or {}).get("sha256") for k in
            ("schemas/af_scc_c0_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml")}
    report = json.loads((HERE / "report.json").read_text())
    tgt = report["target"]["sha256"]
    sib = report["sibling"]["sha256"]
    err = {
        "schema_version": "0.1",
        "task_id": TASK,
        "actor": "worker-066",
        "created_at": now(),
        "kind": "erratum_post_checkpoint",
        "finding": "FROZEN.json moved rev28 2f358f6722d9 -> rev29 3d9e3d77fd87 (frozen_at "
                   "2026-09-12T00:55:02+08:00) after this worker's checkpoint. The canonical "
                   "class-schema bytes did not move: the reviewed target is still "
                   "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe and sibling C2 is still "
                   "e9a27996dfd3, and FROZEN rev29 declares exactly those hashes.",
        "effect_on_verdict": "NONE: the normativity verdict was already bound to "
                             "b2ab6acb2bbe/e9a27996dfd3 and is now additionally bound to FROZEN "
                             "rev29 3d9e3d77fd87. Both containment clauses survive in the "
                             "frozen revision (rev29_delta states no class-semantics change).",
        "frozen_rev29": {
            "path": "artifacts/formulation/FROZEN.json",
            "sha256": frozen_sha,
            "revision": frozen.get("revision"),
            "frozen_at": frozen.get("frozen_at"),
            "declared_c0": decl["schemas/af_scc_c0_vacuum.yaml"],
            "declared_c2": decl["schemas/af_scc_c2_vacuum.yaml"],
            "declared_c0_matches_reviewed": decl["schemas/af_scc_c0_vacuum.yaml"] == tgt,
            "declared_c2_matches_reviewed": decl["schemas/af_scc_c2_vacuum.yaml"] == sib,
        },
        "falsifier": "any write to schemas/af_scc_c0_vacuum.yaml or schemas/af_scc_c2_vacuum.yaml, "
                     "or a FROZEN revision that removes the rev13 deltas or adds the 2-edit "
                     "containment repair (which would supersede the revise verdict).",
        "evidence_refs": [f"artifacts/formulation/FROZEN.json#{frozen_sha[:12]}",
                          f"schemas/af_scc_c0_vacuum.yaml#{tgt[:12]}",
                          f"schemas/af_scc_c2_vacuum.yaml#{sib[:12]}"],
    }
    err_path = HERE / "ERRATUM.json"
    err_path.write_text(json.dumps(err, indent=2) + "\n")

    events = [
        {"event_id": "w066-f2b-normativity-01-artifact-erratum", "event_type": "artifact",
         "created_at": now(), "actor": "worker-066", "node_id": "F2b",
         "class_id": "AF-SCC-C0-VAC-GEN", "class_ids": ["AF-SCC-C0-VAC-GEN"],
         "artifact_type": "erratum", "path": str(err_path.relative_to(REPO)),
         "sha256": sha(err_path), "validation_status": "unverified", "task_id": TASK,
         "note": "post-checkpoint erratum: FROZEN rev29 3d9e3d77 declares exactly the reviewed "
                 "rev13 bytes; verdict unchanged and now freeze-bound"},
        {"event_id": "w066-f2b-normativity-01-status-erratum", "event_type": "status",
         "created_at": now(), "actor": "worker-066", "node_id": "F2b",
         "class_id": "AF-SCC-C0-VAC-GEN", "class_ids": ["AF-SCC-C0-VAC-GEN"],
         "status": "active", "hours": 0.7, "task_id": TASK,
         "summary": "ERRATUM, no measurement change. FROZEN.json moved rev28 -> rev29 "
                    "(3d9e3d77fd87, frozen_at 00:55:02) after the worker checkpoint; the "
                    "canonical C0/C2 bytes did not move (b2ab6acb/e9a27996) and rev29 declares "
                    "exactly those hashes. Both normative containment clauses therefore survive "
                    "into FROZEN rev29; the revise verdict now binds the freeze hash as well. "
                    "astra-life05-verify-gform-r3 should include an order-relative containment "
                    "check before any accept.",
         "evidence_refs": [f"artifacts/formulation/FROZEN.json#{frozen_sha[:12]}",
                           f"artifacts/worker-066/f2b_containment_normativity/ERRATUM.json#{sha(err_path)[:12]}",
                           f"schemas/af_scc_c0_vacuum.yaml#{tgt[:12]}"],
         "next_falsifier": err["falsifier"]},
    ]
    for d in events:
        validate_event(d)
    outbox = REPO / "comms/outbox/worker-066.jsonl"
    with outbox.open("a") as fh:
        for d in events:
            fh.write(json.dumps(d) + "\n")

    ck_path = REPO / "runtime/state/w066_f2b_containment_normativity_checkpoint.json"
    ck = json.loads(ck_path.read_text())
    ck.setdefault("post_checkpoint_updates", []).append({
        "at": now(), "kind": "erratum",
        "frozen_rev29_sha256": frozen_sha,
        "frozen_declares_reviewed_c0": decl["schemas/af_scc_c0_vacuum.yaml"] == tgt,
        "frozen_declares_reviewed_c2": decl["schemas/af_scc_c2_vacuum.yaml"] == sib,
        "erratum_path": str(err_path.relative_to(REPO)),
        "erratum_sha256": sha(err_path),
        "events": [d["event_id"] for d in events],
    })
    ck_path.write_text(json.dumps(ck, indent=2) + "\n")

    lines = outbox.read_text().strip().splitlines()
    bad = []
    for i, ln in enumerate(lines):
        try:
            json.loads(ln)
        except Exception:  # noqa: BLE001
            bad.append(i)
    print(json.dumps({"erratum": str(err_path.relative_to(REPO)),
                      "erratum_sha256": sha(err_path)[:16],
                      "frozen_rev29": frozen.get("revision"),
                      "declared_matches_reviewed": {
                          "c0": decl["schemas/af_scc_c0_vacuum.yaml"] == tgt,
                          "c2": decl["schemas/af_scc_c2_vacuum.yaml"] == sib},
                      "outbox_lines": len(lines), "bad_json_lines": bad}, indent=1))


if __name__ == "__main__":
    main()
