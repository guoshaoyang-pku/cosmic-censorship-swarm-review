#!/usr/bin/env python3
"""Emit the W058-REV30-FREEZE-REHEARSAL-01 event set to comms/outbox/worker-058.jsonl.

Append-only and idempotent: if the run's event ids are already present, nothing is written.
Validated against research_map/schemas.py before writing.  Worker authority only:
validation_status=unverified, status=active (workers cannot set done/passed/verdicts).
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "artifacts/worker-058/rev30_freeze_rehearsal"
OUTBOX = ROOT / "comms/outbox/worker-058.jsonl"
CST = timezone(timedelta(hours=8))
RUN_TAG = "w058-r30reh"
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402


def sha_file(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def ref(rel: str) -> str:
    h = sha_file(ROOT / rel)
    return f"{rel}#{h}"


def main() -> int:
    report = json.loads((OUT / "report.json").read_text())
    ckpt = json.loads((OUT / "checkpoint.json").read_text())
    now = datetime.now(CST).isoformat(timespec="seconds")
    tag = now.replace("-", "").replace(":", "").replace("+", "p")
    F2B = "F2b"
    NODES = "F1,F2a,F2b"
    classes = report["class_ids"]
    class_id = ";".join(classes)
    ev = report["verdict"]
    rep_ref = ref("artifacts/worker-058/rev30_freeze_rehearsal/report.json")
    ck_ref = ref("artifacts/worker-058/rev30_freeze_rehearsal/checkpoint.json")
    runbook_ref = ref("artifacts/worker-058/rev30_freeze_rehearsal/OWNER_RUNBOOK.md")
    instr_ref = ref("artifacts/worker-058/rev30_freeze_rehearsal/rehearse_rev30_freeze.py")
    guard_ref = ref("artifacts/worker-058/rev30_freeze_rehearsal/freeze_guard.py")
    cand_ref = ref("artifacts/worker08/rev29_candidate/af_scc_c0_vacuum.repair-candidate.yaml")
    frozen_ref = ref("artifacts/formulation/FROZEN.json")

    events = [
        {
            "event_id": f"{RUN_TAG}-{tag}-status-start",
            "event_type": "status",
            "created_at": now,
            "actor": "worker-058",
            "node_id": NODES,
            "gate": "G-FORM",
            "status": "active",
            "hours": 0.1,
            "summary": (
                "No assignment card exists in comms/inbox/worker-058.jsonl (relaunched slot). "
                "Took ONE bounded class-bound task, W058-REV30-FREEZE-REHEARSAL-01: sandbox-only "
                "rehearsal of the F2b two-leaf repair -> guarded re-freeze to rev30 -> "
                "verify_frozen -> FORM-SEP-04 acceptance chain, plus a freeze-identity collision "
                "audit of the rev29 incident."
            ),
            "evidence_refs": [frozen_ref, cand_ref],
            "next_falsifier": (
                "any canonical byte change during the run, or an input pin drift away from the "
                "declared rev29 hashes"
            ),
        },
        {
            "event_id": f"{RUN_TAG}-{tag}-artifact-instrument",
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-058",
            "node_id": NODES,
            "artifact_type": "instrument",
            "path": "artifacts/worker-058/rev30_freeze_rehearsal/rehearse_rev30_freeze.py",
            "sha256": instr_ref.split("#")[1],
            "validation_status": "unverified",
            "class_ids": classes,
            "gate": "G-FORM",
            "summary": (
                "Deterministic sandbox rehearsal driver: builds the rev30 tree from the 50 "
                "rev29 pins, applies the pre-validated C0 candidate to canonical+mirror, "
                "guarded re-freeze, verify_frozen, battery/dual on candidate vs rev29 control, "
                "pin-move table, idempotent second sandbox, controls M1-M6."
            ),
            "authority": "worker evidence only; canonical paths read-only",
            "next_falsifier": report["falsifier"],
        },
        {
            "event_id": f"{RUN_TAG}-{tag}-artifact-guard",
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-058",
            "node_id": NODES,
            "artifact_type": "verification_tool",
            "path": "artifacts/worker-058/rev30_freeze_rehearsal/freeze_guard.py",
            "sha256": guard_ref.split("#")[1],
            "validation_status": "unverified",
            "class_ids": classes,
            "gate": "G-FORM",
            "summary": (
                "Candidate freeze-identity guard: manifest digest over (revision, frozen_at, "
                "files), repeated-revision-distinct-identity detection (the CF-27 failure), "
                "pre-write revision monotonicity refusal, non-exiting tree byte check."
            ),
            "authority": "worker evidence only; not installed on any canonical tool",
            "next_falsifier": (
                "show two generations with the same revision label and different bytes that "
                "the guard does not flag, or a legitimate strictly-increasing re-freeze it "
                "refuses"
            ),
        },
        {
            "event_id": f"{RUN_TAG}-{tag}-artifact-report",
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-058",
            "node_id": NODES,
            "artifact_type": "verification_report",
            "path": "artifacts/worker-058/rev30_freeze_rehearsal/report.json",
            "sha256": rep_ref.split("#")[1],
            "validation_status": "unverified",
            "class_ids": classes,
            "gate": "G-FORM",
            "summary": (
                f"Full rehearsal certificate, verdict {ev}: sandbox rev30 manifest "
                f"{report['new_freeze']['manifest_sha256'][:12]} over "
                f"{report['new_freeze']['n_files']} pins (frozen_at {report['fixed_at']}), "
                f"verify_frozen rc=0, candidate battery/dual PASS/PASS vs rev29 control "
                f"FAIL/FAIL, pin moves exactly the two C0 paths, second sandbox byte-identical, "
                f"6/6 planted controls caught, canonical bytes unchanged."
            ),
            "authority": "worker evidence only; no gate verdict and no node completion",
            "next_falsifier": report["next_falsifier"],
        },
        {
            "event_id": f"{RUN_TAG}-{tag}-artifact-runbook",
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-058",
            "node_id": NODES,
            "artifact_type": "summary",
            "path": "artifacts/worker-058/rev30_freeze_rehearsal/OWNER_RUNBOOK.md",
            "sha256": runbook_ref.split("#")[1],
            "validation_status": "unverified",
            "class_ids": classes,
            "gate": "G-FORM",
            "summary": (
                "One-step owner publication procedure: apply the pre-validated two-leaf C0 "
                "repair to both copies, re-freeze at a strictly increasing revision with an "
                "explicit timestamp, verify rc=0, re-run the acceptance battery, then two "
                "blind full-schema F2b reviewers at the published hash."
            ),
            "authority": "worker evidence only; the owner owns any rev30 publication",
            "next_falsifier": report["next_falsifier"],
        },
        {
            "event_id": f"{RUN_TAG}-{tag}-artifact-checkpoint",
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-058",
            "node_id": NODES,
            "artifact_type": "checkpoint",
            "path": "artifacts/worker-058/rev30_freeze_rehearsal/checkpoint.json",
            "sha256": ck_ref.split("#")[1],
            "validation_status": "unverified",
            "class_ids": classes,
            "gate": "G-FORM",
            "summary": "Bounded-task checkpoint with pins, freeze identity, deliverable hashes.",
            "authority": "worker evidence only; no gate verdict and no node completion",
            "next_falsifier": report["next_falsifier"],
        },
        {
            "event_id": f"{RUN_TAG}-{tag}-claim",
            "event_type": "claim",
            "created_at": now,
            "actor": "worker-058",
            "node_id": NODES,
            "gate": "G-FORM",
            "class_id": class_id,
            "statement": (
                "Artifact-and-checker result (not a mathematics or physics claim), measured in "
                "an isolated sandbox at the rev29 pins (C0 b2ab6acb2bbe, C2 e9a27996dfd3, F1 "
                "d9cebb9404b2, FROZEN 815e08079aef): applying the pre-validated two-leaf C0 "
                "repair (worker-008 candidate 84b5d3fa29a6) to both C0 copies and re-freezing "
                "to revision 30 with an explicit timestamp yields a self-consistent manifest "
                f"({report['new_freeze']['manifest_sha256']}) that verifies clean (50/50), "
                "passes the FORM-SEP-04 battery and the fail-closed dual checker while the "
                "unrepaired rev29 control still fails both, moves exactly the two C0 pins and "
                "nothing else, reproduces byte-identically in a second sandbox, and is caught "
                "by none of the six planted controls. The recorded rev29 history contains two "
                "distinct generations under revision 29 (48-pin 3d9e3d77 at 00:55:02 and "
                "50-pin 815e08079aef at 00:57:26), so the bare label 'rev29' is ambiguous and "
                "any citation must carry the manifest hash and frozen_at."
            ),
            "conclusion_type": "formal_model",
            "assumptions": [
                "the rev29 pins are the ones measured at run time (frozen_live 815e08079aef, "
                "C0 b2ab6acb, C2 e9a27996, F1 d9cebb94, taxonomy 0abb9ed8a961)",
                "the worker-008 FORM-SEP-04 validation of the 84b5d3fa candidate is accepted "
                "as an input measurement, not re-derived here",
                "the FORM-SEP-04 battery and the fail-closed dual checker are unchanged "
                "instruments and are the recorded F2b acceptance pair",
                "revision 30 is used only as the rehearsal label; the owner may publish any "
                "strictly increasing revision",
            ],
            "falsifier": report["falsifier"],
            "evidence_refs": [
                rep_ref,
                ck_ref,
                runbook_ref,
                instr_ref,
                guard_ref,
                cand_ref,
                frozen_ref,
                ref("schemas/af_scc_c0_vacuum.yaml"),
                ref("schemas/af_scc_c2_vacuum.yaml"),
                ref("schemas/af_wcc_vacuum.yaml"),
                ref("research_map/formulation_taxonomy.yaml"),
                ref("artifacts/worker08/rev29_candidate_validation.json"),
                ref("artifacts/worker-040/rev29_frozen_drift_adjudication/pinned/"
                    "FROZEN.rev29.3d9e3d77fd87.json"),
            ],
            "authority": "worker evidence only; no gate verdict, node transition or validation promotion",
            "next_falsifier": report["next_falsifier"],
        },
        {
            "event_id": f"{RUN_TAG}-{tag}-blocker",
            "event_type": "blocker",
            "created_at": now,
            "actor": "worker-058",
            "node_id": F2B,
            "gate": "G-FORM",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "description": (
                "Owner action card (not a new defect): the F2b rev30 chain is now rehearsed and "
                "ready, but publication is blocked on the owner because writing the canonical "
                "C0 copies, bumping the freeze revision and commissioning the two blind F2b "
                "reviewers are owner/controller actions. The rehearsal shows the repair is "
                "mechanically complete and self-consistent; the remaining work is a "
                "publication decision, not another audit."
            ),
            "needed_to_unblock": (
                "Astra-lead-formulation publishes rev30: (1) cp "
                "artifacts/worker08/rev29_candidate/af_scc_c0_vacuum.repair-candidate.yaml "
                "(84b5d3fa29a6) over schemas/af_scc_c0_vacuum.yaml AND "
                "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml; (2) run "
                "regenerate_frozen.py --revision 30 --at <ISO8601>; (3) run verify_frozen.py "
                "expect rc=0 and record the new freeze identity without reusing revision 29 "
                "(CF-27); (4) re-run the FORM-SEP-04 battery at the new hash; then two blind "
                "full-schema F2b reviewers at the published manifest hash. L-FORM-03 taxonomy "
                "wording (G-F0-frozen) and the advisory strength bucket remain separate owner "
                "decisions and are not in the rehearsed repair surface."
            ),
            "evidence_refs": [
                rep_ref,
                runbook_ref,
                cand_ref,
                frozen_ref,
            ],
            "authority": "worker evidence only; owner action required, no canonical path written",
        },
        {
            "event_id": f"{RUN_TAG}-{tag}-status-final",
            "event_type": "status",
            "created_at": now,
            "actor": "worker-058",
            "node_id": NODES,
            "gate": "G-FORM",
            "status": "active",
            "hours": 0.8,
            "summary": (
                f"CHECKPOINT + EXIT. W058-REV30-FREEZE-REHEARSAL-01 complete at worker level "
                f"({ev}): one bounded class-bound task with eight deliverables on disk and "
                f"hash-pinned. The pre-validated two-leaf F2b repair (84b5d3fa) rehearses "
                f"end-to-end in an isolated tree: guarded re-freeze to revision 30 gives a "
                f"50-pin manifest {report['new_freeze']['manifest_sha256'][:12]} that verifies "
                f"clean, passes FORM-SEP-04 + dual containment (rev29 control still fails "
                f"both), moves exactly the two C0 pins, reproduces byte-identically, and the "
                f"freeze-identity guard confirms the two-generation rev29 collision. Six "
                f"planted controls (same-revision refusal, mirror divergence, pin tamper, "
                f"missing pin, third-generation collision, reverted repair) all fire. Canonical "
                f"bytes unchanged. Boundary: worker evidence only; no math truth, node "
                f"completion, validation_status or gate verdict claimed."
            ),
            "evidence_refs": [
                rep_ref,
                ck_ref,
                runbook_ref,
                instr_ref,
                guard_ref,
                cand_ref,
                frozen_ref,
            ],
            "next_falsifier": report["next_falsifier"],
        },
    ]

    for e in events:
        validate_event(e)

    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            if line.strip():
                try:
                    existing.add(json.loads(line).get("event_id"))
                except json.JSONDecodeError:
                    pass
    fresh = [e for e in events if e["event_id"] not in existing]
    if not fresh:
        print(json.dumps({"status": "already-emitted", "n_events": len(events)}))
        return 0
    with OUTBOX.open("a") as fh:
        for e in fresh:
            fh.write(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps({"status": "emitted", "n_events": len(fresh),
                      "outbox": str(OUTBOX.relative_to(ROOT))}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
