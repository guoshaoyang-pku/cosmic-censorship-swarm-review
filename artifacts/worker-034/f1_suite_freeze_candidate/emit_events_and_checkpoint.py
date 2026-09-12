#!/usr/bin/env python3
"""W034-F1-FREEZE-CANDIDATE-DERIVATION-01 -- emit outbox events + checkpoints.

Writes (append is idempotent by event_id):
  artifacts/worker-034/f1_suite_freeze_candidate/SHA256SUMS
  artifacts/worker-034/f1_suite_freeze_candidate/checkpoint.json
  runtime/state/w034_f1_freeze_candidate_checkpoint.json
  comms/outbox/worker-034.jsonl   (artifact x8, claim, blocker, status)

No canonical write; events state a proposal, not an adoption or a gate verdict.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402
OUT = ROOT / "artifacts/worker-034/f1_suite_freeze_candidate"
REL = "artifacts/worker-034/f1_suite_freeze_candidate"
STATE = ROOT / "runtime/state/w034_f1_freeze_candidate_checkpoint.json"
OUTBOX = ROOT / "comms/outbox/worker-034.jsonl"
CST = timezone(timedelta(hours=8))

TASK_ID = "W034-F1-FREEZE-CANDIDATE-DERIVATION-01"
STAMP = "20260912T012230"  # fixed event stamp for this worker pass (at/before emission)
CREATED = "2026-09-12T01:22:30+08:00"
EV = "w034-fzc-%s" % STAMP

DELIVERABLES = [
    ("candidate", "candidate/f1_falsifier_tests.rev13.frozen29.derived.jsonl", "data"),
    ("report", "report.json", "report"),
    ("evidence", "evidence.json", "evidence"),
    ("ledger", "derivation_ledger.json", "evidence"),
    ("verification", "verification.json", "evidence"),
    ("instrument", "derive_f1_freeze_candidate.py", "code"),
    ("verifier", "verify_f1_freeze_candidate.py", "code"),
    ("emitter", "emit_events_and_checkpoint.py", "code"),
    ("readme", "README.md", "doc"),
]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ref(rel: str, sha: str) -> str:
    return "%s#sha256:%s" % (rel, sha)


def main() -> int:
    report = json.loads((OUT / "report.json").read_text())
    verification = json.loads((OUT / "verification.json").read_text())
    cand_sha = report["candidate_sha256"]
    assert cand_sha == verification["on_disk"]["sha256"], "candidate sha disagreement"
    assert report["freeze_ready"] and verification["on_disk"]["freeze_ready"]

    hashes = {}
    sizes = {}
    for key, rel, _kind in DELIVERABLES:
        p = OUT / rel
        hashes[key] = sha256_file(p)
        sizes[key] = p.stat().st_size

    artifact_refs = [
        ref("%s/%s" % (REL, rel), hashes[key]) for key, rel, _k in DELIVERABLES
    ]
    evidence_refs = list(artifact_refs) + [
        ref("schemas/f1_falsifier_tests.jsonl", report["pins"]["corpus_orig"]),
        ref("schemas/af_wcc_vacuum.yaml", report["pins"]["f1_live_rev13"]),
        ref("research_map/formulation_taxonomy.yaml", report["pins"]["f0_live_rev5"]),
        ref("artifacts/formulation/FROZEN.json", report["pins"]["frozen_rev29"]),
        ref("artifacts/worker-031/f1_suite_repin_dryrun/patched/f1_falsifier_tests.tierB.jsonl",
            report["pins"]["base_tierB"]),
        ref("artifacts/worker-077/f1_suite_rebind_dryrun/run/"
            "proposed_f1_falsifier_tests.rev13.mechanical.jsonl",
            report["pins"]["excerpt_source_w077_mechanical"]),
    ]

    # ---- events (built before the checkpoint so ids can be recorded) --------
    events = []
    for key, rel, kind in DELIVERABLES:
        events.append(
            {
                "event_id": "%s-artifact-%s" % (EV, key),
                "event_type": "artifact",
                "created_at": CREATED,
                "actor": "worker-034",
                "node_id": "F1",
                "class_id": "AF-WCC-VAC-GEN",
                "gate": "G-FORM",
                "task_id": TASK_ID,
                "artifact_type": kind,
                "path": "%s/%s" % (REL, rel),
                "sha256": hashes[key],
                "bytes": sizes[key],
                "validation_status": "unverified",
                "summary": {
                    "candidate": "derived union freeze candidate, 25 rows, 145121 bytes",
                    "report": "verdict FREEZE_READY_CANDIDATE_DERIVED, checks and controls",
                    "evidence": "full check detail, pins, changed pointers, derivation ledger",
                    "ledger": "76 per-pointer before/after/source entries",
                    "verification": "independent on-disk re-run + owner variants V1/V2",
                    "instrument": "derivation + C1-C8 + materiality + controls",
                    "verifier": "on-disk re-adjudication and variant checks",
                    "emitter": "outbox events + worker-local and runtime checkpoints",
                    "readme": "question, pins, write set, checks, non-claims, falsifier",
                }[key],
            }
        )

    events.append(
        {
            "event_id": "%s-claim" % EV,
            "event_type": "claim",
            "created_at": CREATED,
            "actor": "worker-034",
            "node_id": "F1",
            "class_id": "AF-WCC-VAC-GEN",
            "gate": "G-FORM",
            "task_id": TASK_ID,
            "conclusion_type": "numerical_evidence",
            "statement": (
                "Machine derivation and adjudication of the union F1 falsifier-corpus freeze "
                "candidate at the FROZEN rev29 pins (F1 rev13 d9cebb9404b2, F0 rev5 "
                "0abb9ed8a961, FROZEN 815e08079aef): base cand_w031_tierB 785e6a4e53d6 + the "
                "two residual W077 faithful observed_excerpt refreshes (F1-AMB-09 "
                "genericity.ambient_space, F1-AMB-21 f0_binding.declared_f0_sha256) + full "
                "rev13/FROZEN-rev29 row provenance on all 25 rows yields candidate "
                "adf0e2ef780f75d9 (145121 bytes). The derived bytes are freeze-ready: C1-C8 "
                "11/11 PASS, W029-equivalent B1/B2/X1/M2/C9 5/5 PASS, 8/8 mutant and 7/7 "
                "negative controls caught, two derivations byte-identical, all pins stable to "
                "end, 158 changed pointers all inside the declared D1/D2 write set with 0 "
                "semantic-forbidden changes. The four prior lineage candidates remain "
                "non-freeze-ready (tierA C6+C7, tierB C6+C7, W077 mechanical C3+C5a+C5b+C7+C8, "
                "W077 f0refresh C7+C8). No canonical path was written."
            ),
            "assumptions": [
                "the recorded probe pass flags are claims about the schema at the declared "
                "binding revision and the evaluator semantics are those of the L-FORM-04 "
                "instrument imported from the W034 adjudicator",
                "the binding targets for a rebind under FROZEN rev29 are F1 rev13 "
                "d9cebb9404b2 and F0 rev5 0abb9ed8a961 measured on disk at read time",
                "binding_frozen_revision_schema=13 identifies the schema revision the row "
                "binds (the live F1 artifact declares revision 13) and binding_frozen_revision"
                "=29 identifies the FROZEN revision at derivation",
                "the additive rebind_note and the fixed derivation stamp are publication "
                "metadata; owner variants V1 (no rebind_note) and V2 (frozen revision 30) "
                "are both re-adjudicated freeze-ready",
            ],
            "falsifier": (
                "any pinned input hash moving; any C1-C8 or materiality check flipping on a "
                "re-run over the pinned bytes; a changed pointer outside the D1/D2 write set; "
                "a non-deterministic derivation; or the applied corpus later differing from "
                "this candidate without a fresh adjudication"
            ),
            "artifact_refs": artifact_refs,
            "evidence_refs": evidence_refs,
        }
    )

    events.append(
        {
            "event_id": "%s-blocker" % EV,
            "event_type": "blocker",
            "created_at": CREATED,
            "actor": "worker-034",
            "node_id": "F1",
            "class_id": "AF-WCC-VAC-GEN",
            "gate": "G-FORM",
            "task_id": TASK_ID,
            "description": (
                "The F1 corpus repair is byte-complete as a proposal but not adopted: "
                "schemas/f1_falsifier_tests.jsonl still measures the stale rev29 bytes "
                "56bcb4b3234b with all 25 rows bound to F1 rev12 cce9c601 and two recorded "
                "excerpts/anchors stale, and FROZEN rev30 does not exist. The derived "
                "freeze-ready candidate adf0e2ef780f75d9 has not been reviewed by a "
                "non-author and has no owner adoption decision."
            ),
            "needed_to_unblock": (
                "F1 owner (or the rev14 fold) reviews and adopts the derived candidate or an "
                "owner re-stamped variant (V1 without rebind_note, V2 with "
                "binding_frozen_revision=30, both re-adjudicated freeze-ready), writes it to "
                "schemas/f1_falsifier_tests.jsonl, re-runs the W034 battery on the applied "
                "bytes, and publishes FROZEN rev30 with the per-file pin; independent "
                "non-author review of the applied bytes remains required before any G-FORM "
                "verdict"
            ),
            "next_falsifier": (
                "the applied corpus: re-run this battery on the bytes that land in "
                "schemas/f1_falsifier_tests.jsonl and on FROZEN rev30's per-file pin; the "
                "applied sha256 must equal this candidate (or a re-adjudicated variant)"
            ),
            "evidence_refs": evidence_refs,
        }
    )

    # ---- worker-local checkpoint -------------------------------------------
    checkpoint = {
        "schema": "worker-checkpoint/v1",
        "worker": "worker-034",
        "task_id": TASK_ID,
        "created_at": CREATED,
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-FORM",
        "status": "active",
        "verdict": report["verdict"],
        "authority": "worker evidence only; read-only on all canonical paths; no gate "
                     "verdict, no node status promotion, no canonical corpus write",
        "candidate": {
            "path": "%s/candidate/f1_falsifier_tests.rev13.frozen29.derived.jsonl" % REL,
            "sha256": cand_sha,
            "bytes": report["candidate_bytes"],
            "rows": 25,
            "freeze_ready": True,
            "owner_variants_freeze_ready": {
                v["variant"]: v["freeze_ready"] for v in verification["owner_variants"]
            },
        },
        "deliverables": {
            key: {"path": "%s/%s" % (REL, rel), "sha256": hashes[key], "bytes": sizes[key]}
            for key, rel, _k in DELIVERABLES
        },
        "pins": report["pins"],
        "pins_stable_to_end": report["pins_stable_to_end"],
        "applied_corpus_sha256_at_emission": verification["applied_corpus_sha256_at_verify"],
        "checks": {c["check_id"]: c["status"] for c in report["checks"]},
        "materiality_checks": {c["check_id"]: c["status"] for c in report["materiality_checks"]},
        "controls": {
            "mutants_all_caught": all(c["caught"] for c in report["mutant_controls"]),
            "negatives_all_caught": all(n["caught"] for n in report["negative_controls"]),
        },
        "changed_pointers_by_scope": report["changed_pointers_by_scope"],
        "out_of_write_set_changes": len(report["out_of_write_set_changes"]),
        "semantic_forbidden_changes": len(report["semantic_forbidden_changes"]),
        "events": [e["event_id"] for e in events] + ["%s-status" % EV],
        "outbox": "comms/outbox/worker-034.jsonl",
        "next_falsifier": (
            "the applied corpus: re-run this battery on the bytes that land in "
            "schemas/f1_falsifier_tests.jsonl and on FROZEN rev30's per-file pin"
        ),
        "falsifier": report["falsifier"],
    }
    OUT.joinpath("checkpoint.json").write_text(
        json.dumps(checkpoint, indent=2, ensure_ascii=False) + "\n"
    )
    chk_sha = sha256_file(OUT / "checkpoint.json")

    # ---- SHA256SUMS (includes checkpoint; excludes itself) ------------------
    sums_lines = []
    for key, rel, _k in DELIVERABLES:
        sums_lines.append("%s  %s" % (hashes[key], rel))
    sums_lines.append("%s  checkpoint.json" % chk_sha)
    sums_text = "\n".join(sums_lines) + "\n"
    (OUT / "SHA256SUMS").write_text(sums_text)
    sums_sha = sha256_file(OUT / "SHA256SUMS")

    # ---- runtime checkpoint (copy + stream binding) -------------------------
    runtime_ckpt = dict(checkpoint)
    runtime_ckpt["runtime"] = {
        "source_checkpoint": "%s/checkpoint.json#sha256:%s" % (REL, chk_sha),
        "sha256sums": "%s/SHA256SUMS#sha256:%s" % (REL, sums_sha),
        "checkpoint_written_at": CREATED,
    }
    STATE.write_text(json.dumps(runtime_ckpt, indent=2, ensure_ascii=False) + "\n")
    state_sha = sha256_file(STATE)

    # ---- status event last (references the runtime checkpoint) --------------
    events.append(
        {
            "event_id": "%s-status" % EV,
            "event_type": "status",
            "created_at": CREATED,
            "actor": "worker-034",
            "node_id": "F1",
            "class_id": "AF-WCC-VAC-GEN",
            "gate": "G-FORM",
            "task_id": TASK_ID,
            "status": "active",
            "hours": 0.5,
            "summary": (
                "W034-F1-FREEZE-CANDIDATE-DERIVATION-01 complete at worker level: verdict "
                "FREEZE_READY_CANDIDATE_DERIVED, candidate adf0e2ef780f75d9 (25 rows, 145121 "
                "bytes); C1-C8 11/11 and materiality 5/5 PASS; 8/8 mutant + 7/7 negative "
                "controls caught; deterministic and pin-stable; 0 changes outside the "
                "declared write set. No canonical write and no gate/node movement; adoption "
                "and FROZEN rev30 remain with the F1 owner."
            ),
            "next_falsifier": (
                "the applied corpus: re-run this battery on the bytes that land in "
                "schemas/f1_falsifier_tests.jsonl and on FROZEN rev30's per-file pin"
            ),
            "checkpoint": "runtime/state/w034_f1_freeze_candidate_checkpoint.json#sha256:%s"
            % state_sha,
            "evidence_refs": evidence_refs,
        }
    )

    # ---- append to outbox (idempotent by event_id) --------------------------
    for e in events:
        validate_event(e)  # fail closed before anything is written to the outbox
    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line).get("event_id"))
            except Exception:
                pass
    appended = []
    with OUTBOX.open("a", encoding="utf-8") as f:
        for e in events:
            if e["event_id"] in existing:
                continue
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
            appended.append(e["event_id"])

    print(
        "checkpoint=%s sums=%s runtime=%s appended=%d/%d"
        % (chk_sha[:16], sums_sha[:16], state_sha[:16], len(appended), len(events))
    )
    for eid in appended:
        print("  +", eid)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
