#!/usr/bin/env python3
"""Emit pass-2 (live-hash) artifacts, correction notice and checkpoint 2 for worker-098."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
HERE = ROOT / "artifacts/worker-098/f2a_independent_review"
STATE = ROOT / "runtime/state"
OUTBOX = ROOT / "comms/outbox/worker-098.jsonl"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    ev_p = HERE / "f2a_independent_evidence.v2.json"
    vd_p = HERE / "f2a_independent_verdict.v2.json"
    evidence = json.loads(ev_p.read_text())
    verdict = json.loads(vd_p.read_text())
    ts = evidence["generated_at"]
    target = evidence["reviewed_sha256"]
    short = target[:12]

    # live re-check: if F2a or F0 moved again, downgrade to a moving-target blocker
    live_f2a = sha(ROOT / "schemas/af_scc_c2_vacuum.yaml")
    live_f0 = sha(ROOT / "research_map/formulation_taxonomy.yaml")
    still_live = (live_f2a == target) and (live_f0 == evidence["support_hashes"][
        "canonical_formulation_taxonomy.yaml"])
    binding = "binding" if (still_live and verdict["verdict"] == "accept") else "advisory"

    artifacts = {
        str(ev_p.relative_to(ROOT)): sha(ev_p),
        str(vd_p.relative_to(ROOT)): sha(vd_p),
        str((HERE / "verify_f2a_pass2.py").relative_to(ROOT)): sha(HERE / "verify_f2a_pass2.py"),
        str((HERE / "af_scc_c2_vacuum.snapshot.v2.yaml").relative_to(ROOT)): sha(
            HERE / "af_scc_c2_vacuum.snapshot.v2.yaml"),
    }

    notice = {
        "event_id": f"w098-f2a-drift-notice-{ts}",
        "event_type": "status",
        "created_at": ts,
        "actor": "worker-098",
        "node_id": "F2a",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "status": "active",
        "summary": (
            "Moving-target correction: F2a was republished 4f97273ef440 -> b6123750b37d "
            "(revision 11: comment + revision bump + f0_binding declared hash refreshed; "
            "class semantics unchanged) after my pass-1 review and before its emission. Under "
            "the map's superseded-hash rule the pass-1 verdict (accept 4.5 at 4f97273ef440) is "
            "ADVISORY ONLY. Pass 2 was re-run at the live hash b6123750b37d: accept 4.5, "
            "canonical gate pass, 0 class-separation hard findings, 26/27 contract checks "
            "(the one miss is the known F0 canonical-vs-authoring publication divergence, a "
            "scope note on F0, not an F2a defect), 5/5 mutation controls detected, no drift "
            "during pass 2. F0 binding verified: declared_f0_sha256 == measured canonical "
            "research_map/formulation_taxonomy.yaml == 276009f4f63d."),
        "evidence_refs": [
            f"schemas/af_scc_c2_vacuum.yaml#{short}",
            "artifacts/worker-098/f2a_independent_review/f2a_independent_evidence.v2.json",
            f"research_map/formulation_taxonomy.yaml#{live_f0[:12]}",
        ],
        "next_falsifier": evidence["next_falsifier"],
    }
    art_ev = {
        "event_id": f"w098-f2a-v2-art-evidence-{ts}",
        "event_type": "artifact",
        "created_at": ts,
        "actor": "worker-098",
        "node_id": "F2a",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "artifact_type": "review_evidence",
        "path": str(ev_p.relative_to(ROOT)),
        "sha256": artifacts[str(ev_p.relative_to(ROOT))],
        "validation_status": "unverified",
        "evidence_refs": [f"schemas/af_scc_c2_vacuum.yaml#{short}"],
        "next_falsifier": evidence["next_falsifier"],
    }
    art_vd = {
        "event_id": f"w098-f2a-v2-art-verdict-{ts}",
        "event_type": "artifact",
        "created_at": ts,
        "actor": "worker-098",
        "node_id": "F2a",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "artifact_type": "review_record",
        "path": str(vd_p.relative_to(ROOT)),
        "sha256": artifacts[str(vd_p.relative_to(ROOT))],
        "validation_status": "unverified",
        "evidence_refs": [f"schemas/af_scc_c2_vacuum.yaml#{short}"],
        "next_falsifier": evidence["next_falsifier"],
    }
    rev = dict(verdict)
    rev["binding_status"] = binding
    rev["live_recheck_at_emit"] = {"f2a": live_f2a, "f0": live_f0, "still_live": still_live}
    done = {
        "event_id": f"w098-f2a-v2-done-{ts}",
        "event_type": "status",
        "created_at": ts,
        "actor": "worker-098",
        "node_id": "F2a",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "status": "active",
        "completion_claim": True,
        "binding_status": binding,
        "hours": 0.5,
        "summary": (
            f"W098-F2A-INDEP-VERDICT-01 bound at live hash {short}: verdict "
            f"{verdict['verdict']} score {verdict['score']}, binding_status={binding}. "
            "Bounded task complete; no node completion, no gate verdict, no theorem claimed. "
            "Controller/lead-formulation must ingest and decide."),
        "evidence_refs": [
            f"artifacts/worker-098/f2a_independent_review/f2a_independent_evidence.v2.json#{artifacts[str(ev_p.relative_to(ROOT))][:12]}",
            f"schemas/af_scc_c2_vacuum.yaml#{short}",
        ],
        "next_falsifier": evidence["next_falsifier"],
    }
    events = [notice, art_ev, art_vd, rev, done] if still_live else [
        {**notice, "event_type": "blocker", "status": "blocked",
         "description": "F2a/F0 moved again during pass-2 emission; no binding verdict issued.",
         "needed_to_unblock": "a quiescent revision window long enough to re-measure and review",
         "evidence_refs": notice["evidence_refs"]},
        art_ev, art_vd,
    ]

    checkpoint = {
        "worker": "worker-098",
        "checkpoint": 2,
        "checkpoint_at": ts,
        "task_id": "W098-F2A-INDEP-VERDICT-01",
        "assignment_source": "self-taken (no inbox card for worker-098; fleet launched 00:16:57)",
        "node_id": "F2a",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "verdict": verdict["verdict"],
        "score": verdict["score"],
        "binding_status": binding,
        "hard_failures": verdict["hard_failures"],
        "reviewed_sha256": target,
        "supersedes": {
            "checkpoint": 1,
            "reviewed_sha256": "4f97273ef4404126ef5c8a083ccd5ed4d4ef9fd1aeaf6884c8c5aee0542e12f8",
            "reason": "F2a republished to b6123750b37d before emission; pass-1 advisory only",
        },
        "canonical_f2a_hash_at_end": evidence["canonical_hash_at_end"],
        "declared_f0_sha256": evidence["stage_5_drift"]["f0_start"],
        "drift_during_review": evidence["drift_during_review"],
        "stage_results": {
            "canonical_gate": evidence["stage_1_canonical_gate"]["verdict"],
            "classsep_hard_findings": len(evidence["stage_2_class_separation"]["hard_findings"]),
            "contract_checks_ok": (
                f"{sum(1 for x in evidence['stage_3_contract_checks'] if x['ok'])}"
                f"/{len(evidence['stage_3_contract_checks'])}"),
            "scope_notes": evidence["stage_3_scope_notes"],
            "mutation_controls_detected": (
                f"{sum(1 for x in evidence['stage_4_controls'] if x['detected'])}"
                f"/{len(evidence['stage_4_controls'])}"),
        },
        "artifacts": artifacts,
        "events_emitted": [e["event_id"] for e in events],
        "authority": ("no gate verdict, no node completion, no self-pass; F2a/G-FORM and the "
                      "F0 publication divergence remain with controller + lead-formulation"),
        "numerics_lock": "respected: no N1 work, no numerics/spherical_solver/",
        "scope_limit": evidence["scope_limit"],
        "next_falsifier": evidence["next_falsifier"],
        "hours_spent_estimate": 0.8,
    }

    STATE.mkdir(parents=True, exist_ok=True)
    (STATE / "w098_checkpoint_2.json").write_text(json.dumps(checkpoint, indent=1) + "\n")
    (STATE / "w098_latest_checkpoint.json").write_text(json.dumps(checkpoint, indent=1) + "\n")
    with (STATE / "w098_checkpoints.jsonl").open("a") as fh:
        fh.write(json.dumps(checkpoint) + "\n")
    with OUTBOX.open("a") as fh:
        for e in events:
            fh.write(json.dumps(e) + "\n")

    ok = True
    for line in OUTBOX.read_text().splitlines():
        try:
            o = json.loads(line)
        except Exception as ex:
            print("PARSE FAIL", ex)
            ok = False
            continue
        for req in ("event_id", "event_type", "created_at", "actor"):
            if not o.get(req):
                print("SCHEMA FAIL", o.get("event_id"), "missing", req)
                ok = False
    print(json.dumps({
        "outbox": str(OUTBOX.relative_to(ROOT)),
        "events_appended": len(events),
        "checkpoint": str((STATE / "w098_checkpoint_2.json").relative_to(ROOT)),
        "binding_status": binding,
        "live_f2a": live_f2a, "live_f0": live_f0,
        "self_validation": "PASS" if ok else "FAIL",
    }, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
