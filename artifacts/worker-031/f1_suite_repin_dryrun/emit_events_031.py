#!/usr/bin/env python3
"""Append the W031-F1-SUITE-REPIN-PROPOSAL-01 outbox events (idempotent, schema-validated).

Reads report.json/CHECKPOINT.json for hashes; validates every event with
research_map.schemas.validate_event before appending to comms/outbox/worker-031.jsonl.
Does not run ingest (controller command; run separately).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone

TZ = timezone(timedelta(hours=8))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)
from research_map import schemas  # noqa: E402

OUTDIR = os.path.join(ROOT, "artifacts/worker-031/f1_suite_repin_dryrun")
OUTBOX = os.path.join(ROOT, "comms/outbox/worker-031.jsonl")
TASK = "W031-F1-SUITE-REPIN-PROPOSAL-01"
STAMP = "20260912T010230"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(p):
    return os.path.relpath(p, ROOT)


def build():
    rep = json.load(open(os.path.join(OUTDIR, "report.json"), encoding="utf-8"))
    b = rep["baseline_live_rev13"]
    a = rep["post_patch"]["tier_A"]
    bb = rep["post_patch"]["tier_B"]
    casc = rep["frozen_cascade"]
    created = datetime.now(TZ).isoformat(timespec="seconds")
    d = {rel(os.path.join(OUTDIR, f)): sha256_file(os.path.join(OUTDIR, f))
         for f in ("report.json", "PROPOSED_PATCH.json", "dryrun_repin_031.py", "README.md",
                   "CHECKPOINT.json", "SHA256SUMS", "patched/f1_falsifier_tests.tierA.jsonl",
                   "patched/f1_falsifier_tests.tierB.jsonl")}
    ev = []
    ref = lambda p: f"{p}#{d[p][:12]}"  # noqa: E731

    ev.append({
        "event_id": f"w031-f1repin-status-start-{STAMP}", "event_type": "status",
        "created_at": created, "actor": "worker-031", "node_id": "F1", "status": "active",
        "hours": 0.1,
        "summary": ("No assignment card exists in comms/inbox/worker-031.jsonl (fleet instance "
                    "worker-031-20260912T005730-968807). Took ONE bounded class-bound task: "
                    "W031-F1-SUITE-REPIN-PROPOSAL-01 -- build the F1 falsifier-suite re-pin + F1-AMB-25 "
                    "content repair as an exact JSON-pointer patch and dry-run it on artifact-local copies. "
                    "Owner blocker L-FORM-04 (astra-lead-formulation 00:57:43) declares the suite unbound; "
                    "the task converts that finding into a pre-validated repair card. No canonical path written."),
        "evidence_refs": [ref("artifacts/worker-031/f1_suite_repin_dryrun/dryrun_repin_031.py"),
                          ref("artifacts/worker-031/f1_suite_repin_dryrun/report.json")],
        "next_falsifier": rep["next_falsifier"],
    })

    for f, atype in (("report.json", "report"),
                     ("PROPOSED_PATCH.json", "patch_proposal"),
                     ("dryrun_repin_031.py", "instrument"),
                     ("patched/f1_falsifier_tests.tierA.jsonl", "patched_suite_candidate"),
                     ("patched/f1_falsifier_tests.tierB.jsonl", "patched_suite_candidate"),
                     ("README.md", "readme"),
                     ("CHECKPOINT.json", "checkpoint"),
                     ("SHA256SUMS", "manifest")):
        ev.append({
            "event_id": f"w031-f1repin-artifact-{f.replace('/', '-').replace('.', '-')}-{STAMP}",
            "event_type": "artifact", "created_at": created, "actor": "worker-031",
            "node_id": "F1", "artifact_type": atype,
            "path": rel(os.path.join(OUTDIR, f)), "sha256": d[rel(os.path.join(OUTDIR, f))],
            "validation_status": "unverified",
            "summary": {"report.json": "Dry-run report: pins, pre-registration, baseline, both patch tiers, vendor C-checks, minimality, semantics, cascade, controls K1-K9, verdict PATCH_VALIDATED_AT_LIVE_PINS.",
                        "PROPOSED_PATCH.json": "Machine-applicable patch: 53 tier-A entries (operative) and 84 tier-B entries (recommended), pointer root = suite keyed by test_id, with before/after values.",
                        "dryrun_repin_031.py": "Deterministic stdlib+PyYAML instrument; pins 10 inputs by full sha256, fails closed on drift, writes only under its artifact dir.",
                        "patched/f1_falsifier_tests.tierA.jsonl": f"Proposed suite bytes, tier A: sha256 {a['sha256']}, {a['bytes']} bytes, 25/25 bindings live, 84/84 probes.",
                        "patched/f1_falsifier_tests.tierB.jsonl": f"Proposed suite bytes, tier B (recommended): sha256 {bb['sha256']}, {bb['bytes']} bytes, 25/25 bindings live, 84/84 probes.",
                        "README.md": "One-page human summary: question, result table, cascade, owner decisions, controls, falsifier, replay.",
                        "CHECKPOINT.json": "Bounded-task checkpoint with pins, deliverable hashes, key measurements, verdict, falsifier/next-falsifier, authority.",
                        "SHA256SUMS": "Hash manifest for all deliverables (self excluded)."}[f],
        })

    ev.append({
        "event_id": f"w031-f1repin-claim-{STAMP}", "event_type": "claim", "created_at": created,
        "actor": "worker-031", "class_id": "AF-WCC-VAC-GEN", "node_id": "F1", "gate": "G-FORM",
        "conclusion_type": "formal_model",
        "assumptions": [
            "the live canonical bytes at the 10 pinned hashes are the intended frozen inputs",
            "the hash-verified worker-007 rev12 snapshot is byte-identical to the pre-repair canonical F1",
            "binding_ref/binding_sha256, cross_artifact.sha256 and probe_results[].expected are operative; "
            "evidence_refs/prior_binding_*/delta_vs_*/binding_at_authoring are provenance",
            "the owner decides the binding_note anchor and the tier A/B publication form",
        ],
        "statement": (
            "Artifact-and-checker measurement (not a mathematics or physics claim, not a gate verdict): at pins "
            f"suite {rep['canonical_suite_sha256'][:12]} / F1 rev13 d9cebb9404b2 / F0 rev5 0abb9ed8a961 / "
            "FROZEN rev29 815e08079aef, the canonical F1 falsifier suite is unbound (0/25 row bindings live, "
            f"25/25 stale to F1 rev12 cce9c60146d6; 0/1 cross-artifact live; {b['probes_recomputed_pass']}/84 probes "
            "re-evaluate true; vendor checks 5/10). A proposed patch exists in two measured tiers, applied only to "
            f"artifact-local copies: tier A ({a['distinct_pointers_declared']} operative pointers, sha256 {a['sha256'][:12]}, "
            f"{a['bytes']} bytes) reaches 25/25 live bindings, 25/25 binding_ref/binding_sha256 self-consistency, "
            f"1/1 live cross-artifact, 84/84 probes and 10/10 vendor checks; tier B ({bb['distinct_pointers_declared']} "
            f"pointers including provenance/descriptive refresh, sha256 {bb['sha256'][:12]}, {bb['bytes']} bytes) reaches "
            "the same. Minimality holds (measured changed-pointer set equals declared set on both tiers; 0 unexpected, "
            "0 inert; row set unchanged), the full semantic key set is identical on all 25 rows, and controls K1-K9 pass "
            "(serializer round-trip, F1 rev14 decoy re-stales 25/25, binding_sha256 operativity, both AMB-25 probe "
            "expectations load-bearing, cross-artifact independence, both binding_note anchors, input drift guard, "
            "patch determinism, sandbox confinement). Publication cascades: FROZEN rev29 pins the suite path, so the "
            "re-pin requires FROZEN rev30 + registry refresh + vendor re-run; those are owner actions, and the canonical "
            "schemas/f1_falsifier_tests.jsonl remains byte-identical at 56bcb4b3234b."),
        "falsifier": rep["falsifier"],
        "evidence_refs": [ref("artifacts/worker-031/f1_suite_repin_dryrun/report.json"),
                          ref("artifacts/worker-031/f1_suite_repin_dryrun/PROPOSED_PATCH.json"),
                          ref("artifacts/worker-031/f1_suite_repin_dryrun/patched/f1_falsifier_tests.tierA.jsonl"),
                          ref("artifacts/worker-031/f1_suite_repin_dryrun/patched/f1_falsifier_tests.tierB.jsonl"),
                          "schemas/f1_falsifier_tests.jsonl#56bcb4b3234b",
                          "schemas/af_wcc_vacuum.yaml#d9cebb9404b2",
                          "research_map/formulation_taxonomy.yaml#0abb9ed8a961",
                          "artifacts/formulation/FROZEN.json#815e08079aef",
                          "artifacts/worker-029/f1_suite_rebind/report.json"],
        "artifact_refs": [{"path": rel(os.path.join(OUTDIR, f)), "sha256": d[rel(os.path.join(OUTDIR, f))]}
                          for f in ("report.json", "PROPOSED_PATCH.json",
                                    "patched/f1_falsifier_tests.tierB.jsonl", "CHECKPOINT.json")],
    })

    ev.append({
        "event_id": f"w031-f1repin-blocker-{STAMP}", "event_type": "blocker", "created_at": created,
        "actor": "worker-031", "node_id": "F1", "class_id": "AF-WCC-VAC-GEN",
        "description": (
            "Owner action card for L-FORM-04 (not a new defect): the repair is pre-validated but unpublished. "
            f"Tier B patch {bb['sha256'][:12]} must be applied to schemas/f1_falsifier_tests.jsonl by the suite owner, "
            f"which moves the one FROZEN rev29 path pin {casc['moved_paths'][0]['frozen_rev29_pin'][:12]} -> "
            f"{bb['sha256'][:12]}; per change_protocol that requires FROZEN rev30, a re-emitted artifact event, and a "
            "refreshed runtime/state/artifact_hashes.json. Two owner decisions remain: binding_note anchor variant "
            "(V1 current-rev13 text vs V2 F0-contract text; both measured 84/84) and the real rebound_at instant "
            f"(the dry-run uses placeholder {rep['patch']['proposed_rebound_at']}). Tier A ({a['sha256'][:12]}) is the "
            "minimal operative alternative if provenance fields are intentionally kept at rev27."),
        "needed_to_unblock": (
            "astra-lead-formulation applies tier A or tier B, sets the real rebound_at, bumps FROZEN to rev30 with the "
            "new suite sha256/bytes, re-emits the artifact event, refreshes runtime/state/artifact_hashes.json, and "
            "re-runs artifacts/flash-04/f1_ambiguity/verify_freeze_current.py; then worker-029's checker and this "
            "instrument re-run at the published bytes and should report 0 outstanding defects / PATCH-ALREADY-APPLIED."),
        "evidence_refs": [ref("artifacts/worker-031/f1_suite_repin_dryrun/report.json"),
                          ref("artifacts/worker-031/f1_suite_repin_dryrun/PROPOSED_PATCH.json"),
                          "artifacts/formulation/FROZEN.json#815e08079aef",
                          "schemas/f1_falsifier_tests.jsonl#56bcb4b3234b"],
    })

    ev.append({
        "event_id": f"w031-f1repin-review-{STAMP}", "event_type": "review", "created_at": created,
        "actor": "worker-031", "reviewer": "worker-031",
        "target_id": "w031-f1repin-deliverables", "node_id": "F1", "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-FORM", "verdict": "accept", "score": 4.0,
        "counts_as_full_schema_verdict": False,
        "review_scope": "self-review of the worker deliverable only (patch validity + measurement method); NOT an F1 schema verdict",
        "hard_failures": [],
        "findings": [
            "Tier A and tier B both measured at 25/25 live bindings, 25/25 ref/sha self-consistency, 1/1 live cross-artifact, 84/84 probes, 10/10 vendor C-checks; baseline reproduced at 0/25, 0/1, 82/84, 5/10.",
            "Minimality and semantics controls pass; the two AMB-25 probe expectations are each load-bearing (83/84 when dropped) and the cross-artifact check is independent of the probes.",
            "Residual risk: the patch is not applied to the canonical suite; if the owner re-pins with different bytes or a different binding_note anchor, re-run the instrument before publication. counts_as_full_schema_verdict=false.",
        ],
        "evidence_refs": [ref("artifacts/worker-031/f1_suite_repin_dryrun/report.json"),
                          ref("artifacts/worker-031/f1_suite_repin_dryrun/README.md")],
    })

    ev.append({
        "event_id": f"w031-f1repin-status-final-{STAMP}", "event_type": "status", "created_at": created,
        "actor": "worker-031", "node_id": "F1", "status": "active", "hours": 0.4,
        "summary": ("CHECKPOINT + EXIT. W031-F1-SUITE-REPIN-PROPOSAL-01 complete at worker level: one class-bound "
                    "task, eight deliverables on disk and hash-pinned, controls K1-K9 pass, verdict "
                    "PATCH_VALIDATED_AT_LIVE_PINS. Baseline defect set reproduced exactly; proposed tier-A/B patches "
                    "close it on artifact-local copies; FROZEN rev30 cascade and two owner decisions filed as a blocker. "
                    "No gate verdict, no node status, no validation_status, no canonical artifact edited."),
        "evidence_refs": [ref("artifacts/worker-031/f1_suite_repin_dryrun/CHECKPOINT.json"),
                          ref("artifacts/worker-031/f1_suite_repin_dryrun/report.json")],
        "next_falsifier": rep["next_falsifier"],
    })
    return ev


def main() -> int:
    events = build()
    for e in events:
        schemas.validate_event(e)
    existing = set()
    if os.path.exists(OUTBOX):
        for line in open(OUTBOX, encoding="utf-8"):
            line = line.strip()
            if line:
                try:
                    existing.add(json.loads(line).get("event_id"))
                except json.JSONDecodeError:
                    pass
    new = [e for e in events if e["event_id"] not in existing]
    with open(OUTBOX, "a", encoding="utf-8") as fh:
        for e in new:
            fh.write(json.dumps(e, sort_keys=True) + "\n")
    print(json.dumps({"built": len(events), "appended": len(new),
                      "skipped_existing": len(events) - len(new),
                      "event_ids": [e["event_id"] for e in new]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
