#!/usr/bin/env python3
"""Emit the worker-086 deliverable for W086-GFORM-R2-DURABILITY-01 and checkpoint it.

Worker authority: emits artifacts/claim/status only.  It cannot set a gate verdict,
node status=done, or validation_status=passed.  All events are validated with
research_map/schemas.validate_event before they are appended, and every artifact
ref is re-hashed from disk at emit time.
"""
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ART = Path(__file__).resolve().parent
REPO = ART.parents[2]
OUTBOX = REPO / "comms/outbox/worker-086.jsonl"
STATE = REPO / "runtime/state"
CKPT = STATE / "w086_evbind_repair_demo_checkpoint.json"
CKPT_LOG = STATE / "worker-086_checkpoints.jsonl"

sys.path.insert(0, str(REPO))
from research_map.schemas import validate_event  # noqa: E402


def now() -> str:
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def sha(rel: str) -> str:
    return hashlib.sha256((REPO / rel).read_bytes()).hexdigest()


def ref(rel: str) -> str:
    return f"{rel}#{sha(rel)[:12]}"


def main() -> int:
    created = now()
    stamp = created.replace("-", "").replace(":", "").replace("+0800", "").replace("+08:00", "")
    report = json.loads((ART / "report.json").read_text())
    if report["checks_passed"] != report["checks_total"] or report["checks_total"] != 12:
        raise SystemExit(f"refusing to emit: report checks {report['checks_passed']}/{report['checks_total']}")
    if report["verdict"] != "R2_DURABLE_WITH_NOWRITE_GUARD__RESIDUAL_FROZEN_REPIN_AND_OWNER_APPLY_REQUIRED":
        raise SystemExit("refusing to emit: unexpected verdict")

    artifacts = {
        rel: sha(rel)
        for rel in (
            "artifacts/worker-086/evbind_repair_demo/probe_r2_durability.py",
            "artifacts/worker-086/evbind_repair_demo/guard_build.py",
            "artifacts/worker-086/evbind_repair_demo/guard.patch",
            "artifacts/worker-086/evbind_repair_demo/check_taxonomy_consistency.guarded.py",
            "artifacts/worker-086/evbind_repair_demo/report.json",
            "artifacts/worker-086/evbind_repair_demo/PINS.json",
            "artifacts/worker-086/evbind_repair_demo/README.md",
            "artifacts/worker-086/evbind_repair_demo/MANIFEST.sha256",
            "artifacts/worker-086/evbind_repair_demo/emit_events.py",
        )
    }
    verdict = report["verdict"]
    class_join = "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN"
    common = {
        "created_at": created,
        "actor": "worker-086",
        "node_id": "F1",
        "node_ids": ["F1", "F2a", "F2b"],
        "gate": "G-FORM",
        "class_id": class_join,
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
    }

    claim_statement = (
        "Artifact-and-checker measurement (not a mathematics or physics claim) at rev12 pins "
        "F1 cce9c60146d6 / F2a 5476a3f2c6bc / F2b 55d0a1ea9bda on declared F0 rev5 0abb9ed8a961 and "
        "declared consistency evidence 675a99d0: the worker-092 repair path R2 (stage the declared "
        "evidence bytes at artifacts/formulation/evidence/taxonomy_consistency.json) is durable if and "
        "only if the pinned standalone checker de356d99 is made non-writing. In a sandbox mirror of the "
        "checker inputs, the pinned unguarded checker run once rewrites the canonical-path copy to the "
        "lean document 9e335e9b (control; R2 alone fails the durability falsifier), while the "
        "two-replacement guard candidate cde1a165 keeps the restored bytes 675a99d0 byte-stable across "
        "repeated runs, keeps inconsistency detection live (rc 1, INCONSISTENT on a mutated taxonomy), "
        "and retains an explicit --write opt-in for owner regeneration; 12/12 checks pass, 10/10 live "
        "pins identical before and after (no canonical write by the corrected runs). Residual: FROZEN "
        "rev28 still pins the evidence path at 9e335e9b, so the owner must publish a FROZEN revision "
        "re-pinning the restored evidence hash 675a99d0 and the guarded tool hash before "
        "declared == disk == freeze holds at one instant. Disclosed incident: development run #1 "
        "executed the guarded candidate outside the sandbox mirror and performed a byte-identical "
        "rewrite (content sha 9e335e9b unchanged, mtime moved to 2026-09-12T00:47:25+08:00); see "
        "report.json incident_log."
    )
    claim_falsifier = (
        "The R2+guard repair fails if, after the owner stages the restore, applies guard.patch and "
        "re-pins FROZEN: (a) one guarded-checker run leaves the canonical evidence path at any hash "
        "other than 675a99d0; or (b) any of the three schema hashes or the F0 taxonomy hash changes; or "
        "(c) the unguarded pinned checker no longer rewrites a sandbox copy to 9e335e9b (control dead); "
        "or (d) FROZEN still pins 9e335e9b at the canonical evidence path. The probe itself is "
        "falsified if a rerun at the same live pins yields any check failure or a different report "
        "verdict."
    )

    events = [
        dict(common, event_id=f"w086-{stamp}-art-r2-probe", event_type="artifact",
             artifact_type="repair_durability_probe",
             path="artifacts/worker-086/evbind_repair_demo/probe_r2_durability.py",
             sha256=artifacts["artifacts/worker-086/evbind_repair_demo/probe_r2_durability.py"],
             validation_status="unverified",
             summary="Deterministic fail-closed R2 durability probe: 12 checks in a sandbox mirror, "
                     "live pins measured before/after, guard sentinel asserts the sandbox ROOT."),
        dict(common, event_id=f"w086-{stamp}-art-r2-report", event_type="artifact",
             artifact_type="repair_durability_result",
             path="artifacts/worker-086/evbind_repair_demo/report.json",
             sha256=artifacts["artifacts/worker-086/evbind_repair_demo/report.json"],
             validation_status="unverified",
             summary=f"Measured result: {verdict}; 12/12 checks; R2 alone not durable (control rewrites "
                     "to 9e335e9b), R2+guard durable, residual FROZEN re-pin required; incident_log "
                     "discloses the development-run byte-identical canonical touch."),
        dict(common, event_id=f"w086-{stamp}-art-r2-guard", event_type="artifact",
             artifact_type="writer_guard_candidate",
             path="artifacts/worker-086/evbind_repair_demo/check_taxonomy_consistency.guarded.py",
             sha256=artifacts["artifacts/worker-086/evbind_repair_demo/check_taxonomy_consistency.guarded.py"],
             validation_status="unverified",
             summary="Candidate only: pinned checker de356d99 with the canonical evidence write gated "
                     "behind an explicit --write; consistency logic and exit code unchanged.",
             target_sha256="de356d999ea3b6aeb9cfe7d35d6604328ccc4945ead3bc3ec566a929363f31cd"),
        dict(common, event_id=f"w086-{stamp}-art-r2-patch", event_type="artifact",
             artifact_type="patch",
             path="artifacts/worker-086/evbind_repair_demo/guard.patch",
             sha256=artifacts["artifacts/worker-086/evbind_repair_demo/guard.patch"],
             validation_status="unverified",
             summary="Two exact literal replacements for the owner to audit and apply to the canonical "
                     "checker; built by guard_build.py with the pinned input hash-checked."),
        dict(common, event_id=f"w086-{stamp}-art-r2-pins", event_type="artifact",
             artifact_type="pins",
             path="artifacts/worker-086/evbind_repair_demo/PINS.json",
             sha256=artifacts["artifacts/worker-086/evbind_repair_demo/PINS.json"],
             validation_status="unverified",
             summary="Live pins before/after (identical), declared evidence hash, guarded candidate and "
                     "patch hashes."),
        dict(common, event_id=f"w086-{stamp}-art-r2-readme", event_type="artifact",
             artifact_type="summary",
             path="artifacts/worker-086/evbind_repair_demo/README.md",
             sha256=artifacts["artifacts/worker-086/evbind_repair_demo/README.md"],
             validation_status="unverified",
             summary="One-page result, owner repair sequence, falsifier and incident disclosure."),
        dict(common, event_id=f"w086-{stamp}-art-r2-manifest", event_type="artifact",
             artifact_type="manifest",
             path="artifacts/worker-086/evbind_repair_demo/MANIFEST.sha256",
             sha256=artifacts["artifacts/worker-086/evbind_repair_demo/MANIFEST.sha256"],
             validation_status="unverified",
             summary="sha256 of every file in the deliverable directory."),
    ]

    ckpt_doc = {
        "checkpoint": 5,
        "worker": "worker-086",
        "role": "bounded execution worker",
        "slot": "086",
        "at": created,
        "hours_spent_estimate": 0.5,
        "task": {
            "task_id": "W086-GFORM-R2-DURABILITY-01",
            "node_ids": ["F1", "F2a", "F2b"],
            "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
            "gate": "G-FORM",
            "kind": "R2 restore durability probe + minimal non-writing guard candidate",
            "assignment_source": "self-issued from worker-086 next_falsifier "
                                 "(w086-20260912T004241-status-collision) and worker-092 R2+guard "
                                 "adjudication (w092-20260912T004304-evbind-claim); no inbox card existed "
                                 "for worker-086",
        },
        "target_pins": report["inputs"]["pins"],
        "verdict": verdict,
        "checks": f"{report['checks_passed']}/{report['checks_total']}",
        "guard_candidate": report["guard_candidate"],
        "artifacts": artifacts,
        "events_emitted": [e["event_id"] for e in events]
        + [f"w086-{stamp}-claim-r2-durability", f"w086-{stamp}-status-r2-durability"],
        "next_falsifier": "After the owner applies steps 1-3 of the repair recipe, re-run "
                          "artifacts/worker-086/evidence_collision/probe_collision.py and this probe at "
                          "the new pins; the repair clears only when declared hash, canonical bytes and "
                          "the FROZEN pin agree at one measured instant and no checker run moves the "
                          "canonical path hash.",
        "incident": report["incident_log"][0]["what"],
        "authority_note": "Worker evidence only; cannot set gate verdict, status=done, or "
                          "validation_status=passed.",
    }
    CKPT.write_text(json.dumps(ckpt_doc, indent=2) + "\n")

    ckpt_ref = ref("runtime/state/w086_evbind_repair_demo_checkpoint.json")
    evidence_refs = [ref(p) for p in artifacts]
    evidence_refs += [
        ckpt_ref,
        ref("artifacts/formulation/evidence/taxonomy_consistency.json"),
        ref("artifacts/formulation/FROZEN.json"),
        ref("artifacts/formulation/tools/check_taxonomy_consistency.py"),
        ref("schemas/af_wcc_vacuum.yaml"),
        ref("schemas/af_scc_c2_vacuum.yaml"),
        ref("schemas/af_scc_c0_vacuum.yaml"),
    ]
    claim = dict(
        common,
        event_id=f"w086-{stamp}-claim-r2-durability",
        event_type="claim",
        conclusion_type="stability_result",
        statement=claim_statement,
        assumptions=[
            "The three schema files, the two taxonomy files, VOCAB_ALIASES.json and FROZEN rev28 at the "
            "measured hashes are the intended rev12 publication state.",
            "The pinned standalone checker is the writer whose behaviour the R2 durability falsifier "
            "names; close_findings_rev27.py --apply is a second writer and is not exercised here.",
            "A sandbox copy of ROOT reproduces the canonical checker's behaviour because the checker "
            "reads only the four mirrored inputs and writes only the mirrored evidence path.",
        ],
        falsifier=claim_falsifier,
        evidence_refs=evidence_refs,
        artifact_refs=["artifacts/worker-086/evbind_repair_demo/report.json#"
                       + artifacts["artifacts/worker-086/evbind_repair_demo/report.json"][:12]],
        hours=0.5,
    )
    status = dict(
        common,
        event_id=f"w086-{stamp}-status-r2-durability",
        event_type="status",
        status="active",
        hours=0.5,
        summary=f"W086-GFORM-R2-DURABILITY-01 complete and checkpointed: {verdict}; 12/12 checks. "
                "R2 alone is not durable (pinned unguarded checker rewrites the sandbox canonical path to "
                "9e335e9b in one run); the guard candidate cde1a165 keeps the restored 675a99d0 bytes "
                "stable, preserves detection and keeps an explicit --write opt-in. Residual requirement: "
                "FROZEN rev29 re-pin of evidence 675a99d0 + guarded tool hash. Corrected probe runs wrote "
                "no canonical path (10/10 live pins identical); development-run byte-identical incident is "
                "disclosed in report.json. No node status, gate verdict or validation promotion claimed.",
        evidence_refs=evidence_refs,
        artifact_refs=[
            "artifacts/worker-086/evbind_repair_demo/report.json#"
            + artifacts["artifacts/worker-086/evbind_repair_demo/report.json"][:12],
            ckpt_ref,
        ],
        next_falsifier="Apply repair recipe steps 1-3, then re-run probe_collision.py and "
                       "probe_r2_durability.py at the new pins; any canonical-path move off 675a99d0, any "
                       "schema/F0 hash change, a dead unguarded control, or a FROZEN pin still at "
                       "9e335e9b falsifies the repair.",
    )

    out = [claim, status]
    for e in events + out:
        validate_event(e)

    existing = OUTBOX.read_text().splitlines() if OUTBOX.exists() else []
    seen = set()
    for line in existing:
        try:
            seen.add(json.loads(line)["event_id"])
        except Exception:
            pass
    new_ids = [e["event_id"] for e in events + out]
    dupes = [i for i in new_ids if i in seen]
    if dupes:
        raise SystemExit(f"duplicate event ids already in outbox: {dupes}")
    with OUTBOX.open("a") as fh:
        for e in events + out:
            fh.write(json.dumps(e, sort_keys=True) + "\n")

    with CKPT_LOG.open("a") as fh:
        fh.write(json.dumps({k: ckpt_doc[k] for k in
                             ("checkpoint", "at", "verdict", "checks", "artifacts", "events_emitted")},
                            sort_keys=True) + "\n")

    # post-write verification
    text = OUTBOX.read_text()
    parsed = [json.loads(l) for l in text.splitlines() if l.strip()]
    got = {o["event_id"] for o in parsed}
    missing = [i for i in new_ids if i not in got]
    if missing:
        raise SystemExit(f"post-write verification failed, missing {missing}")
    for e in events + out:
        validate_event(e)
    print(f"emitted {len(events) + len(out)} events to {OUTBOX.relative_to(REPO)} "
          f"({len(parsed)} lines total); checkpoint {CKPT.relative_to(REPO)}")
    print(f"checkpoint ref: {ckpt_ref}")
    for e in events + out:
        print("  ", e["event_id"], e["event_type"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
