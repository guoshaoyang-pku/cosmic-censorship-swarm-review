#!/usr/bin/env python3
"""
Build BLOCKER.json for W071-F1-REV27-BLIND-REVIEW-01 from measurement.json.

The assignment card's acceptance clause (1) is binding:
  pin measured != pin assigned  ->  STOP and emit a `blocker` (moving target), NOT a verdict.
This builder folds the bind-chain addendum card (audit-r2-F1-bindchain-worker-071) into the
single blocker artifact, because the addendum's stop rule says "fold into the single verdict
file already assigned" and no verdict may be written.

Writes exactly one file: BLOCKER.json. Prints its sha256 for event/checkpoint chaining.
"""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TZ = timezone(timedelta(hours=8))


def now_iso():
    return datetime.now(TZ).isoformat(timespec="milliseconds")


def sha_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    m = json.loads((HERE / "measurement.json").read_text())
    meas_sha = sha_file(HERE / "measurement.json")
    instr_sha = sha_file(HERE / "measure.py")

    pin = m["assigned_pin"]
    cur = m["schemas"][0]
    occ = m["target_verdict_path_occupancy"]
    chain = m["declared_hash_chain"]
    decl_by_key = {d["declared_field"]: d["declared_sha256"] for d in chain["declarations"]}
    witness = m["rev12_witness"]["now_matches"][0] if m["rev12_witness"]["now_matches"] else {}
    rev_tail = m["f1_revision_history_tail"]

    blocker = {
        "artifact_type": "review_blocker",
        "blocker_id": m["task_id"] + "/BLOCKER",
        "task_id": m["task_id"],
        "worker": m["worker"],
        "actor": m["worker"],
        "role": "independent_verifier",
        "created_at": now_iso(),
        "gate": m["gate"],
        "node_id": m["node_id"],
        "class_id": m["class_id"],
        "assignment_event_ids": m["assignment_event_ids"],
        "assignment_created_at": m["assignment_created_at"],
        "assignment_deadline": m["assignment_deadline"],
        "blocker_type": "moving_target_pin_mismatch+target_path_occupied+assignment_overtaken",
        "code": "MOVING_TARGET",
        "headline": (
            "F1 (schemas/af_wcc_vacuum.yaml) no longer hashes to the assigned rev27 pin; no blind "
            "verdict was written, and the assigned verdict path was already occupied before this "
            "worker started."
        ),
        "assigned_pin": pin,
        "measured_f1": {
            "path": cur["path"],
            "sha256": cur["sha256_before_read"],
            "bytes": cur["bytes"],
            "mtime": cur["mtime"],
            "revision_from_file": m["f1_revision_from_file"],
            "stable_during_read": cur["stable_during_read"],
        },
        "pin_check": m["pin_check"],
        "revision_identification": {
            "assigned_pin_revision": 12,
            "assigned_pin_evidence": {
                "kind": "accepted-stream witness that cce9c60146d6 was the live F1 hash at "
                        "2026-09-12T00:32:43 (rev12 publication)",
                "source": "research_map/events.jsonl",
                "line": witness.get("line"),
                "event_id": witness.get("event_id"),
                "created_at": witness.get("created_at"),
                "received_at": witness.get("_received_at"),
                "matches_prefix": pin["sha256"][:12],
            },
            "current_revision": m["f1_revision_from_file"],
            "current_revision_evidence": rev_tail,
            "conclusion": (
                "the file advanced rev12 -> rev13 (visibility strictness repair + "
                "f0_binding.consistency_evidence_sha256 refresh) at 2026-09-12T00:53:20+08:00, "
                "after the assignment cards were authored (00:44:18 / 00:47:58) and before this "
                "worker's measurement window"
            ),
        },
        "target_verdict_path_occupancy": occ,
        "bind_chain_addendum": {
            "addendum_event_id": "audit-r2-F1-bindchain-worker-071",
            "measured_at": m["finished_at"],
            "measured_at_bytes": "current rev13 bytes (NOT the stale rev12 pin)",
            "declarations": chain["declarations"],
            "pointers": chain["pointers"],
            "refresh_rule": chain["refresh_rule"],
            "all_declared_hashes_resolved": chain["all_declared_hashes_resolved"],
            "binding_hashes_resolved": chain["binding_hashes_resolved"],
            "any_mismatch": chain["any_mismatch"],
            "hard_failures": [],
            "positive_statement": (
                "Every sha256 declared in the F1 schema resolves at the measured rev13 bytes: "
                "declared_f0_sha256 -> research_map/formulation_taxonomy.yaml (0abb9ed8a961), "
                "consistency_evidence_sha256 -> artifacts/formulation/evidence/taxonomy_consistency.json "
                "(9e335e9ba1bf), provenance worker_sha256 -> "
                "artifacts/flash-04/f1_ambiguity/schema_snapshots/af_wcc_vacuum.7a3e1f93.yaml "
                "(7a3e1f93f77c). The schema's refresh rule is satisfied at current bytes "
                "(declared F0 hash == live F0 hash; consistency evidence hash == live file; "
                "taxonomy_consistency.json consistent=true, errors=[]). Both pointer fragments "
                "(classes.AF-WCC-VAC-GEN, class_contracts.AF-WCC-VAC-GEN) resolve."
            ),
        },
        "controls": m["controls"],
        "controls_passed": m["controls_passed"],
        "measurement_valid": m["measurement_valid"],
        "hard_failures": [
            (
                "HASH-BOUND: assigned pin schemas/af_wcc_vacuum.yaml#"
                + pin["sha256"]
                + " does not equal the measured file sha256 "
                + str(cur["sha256_before_read"])
                + " (rev12 -> rev13). Acceptance clause (1) forbids a verdict at this pin."
            ),
            (
                "PATH-BOUND: the assigned target reviews/F1-review-rev27-a.json already exists "
                "(sha256 " + str(occ.get("sha256")) + ", bytes " + str(occ.get("bytes"))
                + ", mtime " + str(occ.get("mtime")) + "), so writing the assigned verdict file "
                "would overwrite a peer artifact; it was not written."
            ),
        ],
        "findings": [
            "The two inbox cards (audit-r2-F1-a, audit-r2-F1-bindchain-worker-071) pin the F1 "
            "schema at its rev12 hash cce9c60146d6, but rev13 d9cebb94 was already live and "
            "FROZEN (manifest revision 29, frozen_at 2026-09-12T00:57:26+08:00) before this "
            "worker started. Both canonical and authoring F1 mirrors now carry rev13.",
            "The assigned verdict path reviews/F1-review-rev27-a.json was written at "
            "2026-09-12T00:53:52+08:00, i.e. before this worker's start and 30s after rev13 "
            "landed; per CF-12 (one canonical path, one owner) it was left untouched.",
            "Because no verdict is written, the bind-chain addendum is reported here instead of "
            "in a verdict file. It is a positive mechanical result at current bytes, but it does "
            "not unblock the stale assignment.",
            "No review verdict, no gate verdict and no node status is emitted or implied; worker "
            "events cannot move those.",
        ],
        "evidence_refs": [
            "schemas/af_wcc_vacuum.yaml#" + str(cur["sha256_before_read"])[:12],
            "schemas/af_wcc_vacuum.yaml#revision_history.index[11]",
            "reviews/F1-review-rev27-a.json#" + str(occ.get("sha256"))[:12],
            "research_map/events.jsonl:" + str(witness.get("line")),
            "artifacts/formulation/FROZEN.json#" + str(m["frozen_manifest"]["sha256"])[:12],
            "research_map/formulation_taxonomy.yaml#" + str(decl_by_key.get("declared_f0_sha256"))[:12],
            "artifacts/formulation/formulation_taxonomy.yaml#d7419b4e8963",
            "artifacts/formulation/evidence/taxonomy_consistency.json#9e335e9ba1bf",
            "artifacts/flash-04/f1_ambiguity/schema_snapshots/af_wcc_vacuum.7a3e1f93.yaml#7a3e1f93f77c",
            "artifacts/worker-071/f1_rev27_blind_review/measurement.json#" + meas_sha[:12],
            "comms/inbox/worker-071.jsonl",
            "comms/PROTOCOL.md:52-53",
            "research_map/ASTRA_HANDOFF.md:36-48",
        ],
        "measurement": {
            "path": "artifacts/worker-071/f1_rev27_blind_review/measurement.json",
            "sha256": meas_sha,
            "instrument": {
                "path": "artifacts/worker-071/f1_rev27_blind_review/measure.py",
                "sha256": instr_sha,
            },
        },
        "needed_to_unblock": (
            "The gate owner (astra-lead-audit with the controller) must issue a fresh assignment "
            "whose pin is the live F1 sha256 (measured d9cebb94 at 2026-09-12T01:15+08:00; "
            "re-measure at issuance), to a reviewer who is not an author of F1, for a NEW "
            "unoccupied verdict path (or explicitly authorize a distinct reviewer slot at the "
            "rev27 path after adjudicating the existing occupant). If instead the intent is to "
            "review rev12, the rev12 bytes cce9c601 must be restored and re-frozen first, which "
            "is a formulation-lead action, not a worker action."
        ),
        "falsifier": m["falsifier"],
        "void_condition": m["void_condition"],
        "no_verdict_emitted_reason": (
            "Acceptance clause (1): pre-read sha256 differs from the assigned pin -> emit a "
            "blocker (moving target) instead of a verdict. The assigned verdict path is also "
            "already occupied by a peer artifact, so writing it would overwrite work this worker "
            "did not author (CF-4 / CF-12)."
        ),
        "authority_note": (
            "Worker evidence only. Does not set status=done, validation_status=passed, or any "
            "gate verdict. Only the controller and group leads may move those, with artifact + "
            "review evidence."
        ),
    }

    out = HERE / "BLOCKER.json"
    out.write_text(json.dumps(blocker, indent=2, sort_keys=False) + "\n")
    print("wrote", out.relative_to(ROOT))
    print("sha256", sha_file(out))
    print("measurement.json sha256", meas_sha)
    print("measure.py sha256", instr_sha)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
