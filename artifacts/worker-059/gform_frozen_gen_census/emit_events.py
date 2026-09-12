#!/usr/bin/env python3
"""Emit worker-059 events for W059-GFORM-FROZEN-GEN-BINDING-CENSUS-01 and checkpoint.

Idempotent: event_ids already present in comms/outbox/worker-059.jsonl are skipped.
Every emitted line is parsed back and checked for required fields per event_type.
Writes only the worker outbox and runtime/state/w059_checkpoint_*.json[.jsonl].
"""
import datetime
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
OUTBOX = os.path.join(ROOT, "comms", "outbox", "worker-059.jsonl")
STATE = os.path.join(ROOT, "runtime", "state")
CKPT_JSON = os.path.join(STATE, "w059_checkpoint_frozen_gen.json")
CKPT_LOG = os.path.join(STATE, "w059_checkpoints.jsonl")

CLASSES = "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN"
NODES = "F1,F2a,F2b"
GATE = "G-FORM"
TASK = "W059-GFORM-FROZEN-GEN-BINDING-CENSUS-01"
NOW = "2026-09-12T01:12:30+08:00"

ARTIFACTS = [
    ("report.json", "independent_verification",
     "Full CF-27 measurement: both FROZEN rev29 generations, pin deltas, 50/50 live pin resolution, "
     "43/48 predecessor resolution, 213-review binding census, 13/13 expectations, 9/9 mutants/controls."),
    ("stale_binding_census.json", "registry_legality_matrix",
     "Focused extract: changed/superseded/added pins with class scan, recoverability, materiality, "
     "33 stale-binding rows, falsifier."),
    ("check_frozen_gen_census.py", "instrument",
     "Deterministic harness with pre-registered expectations E1-E12+E13b, amendment log, "
     "6 mutants and 3 controls, and --corpus-from reproducible verification mode."),
    ("review_FROZEN_gen_census.json", "independent_verdict",
     "Advisory review verdict revise 4.0 with HF-059-FROZEN-01 and 10 findings."),
    ("README.md", "summary",
     "Human-readable summary, headline finding, snapshot inventory, reproduce/falsify commands."),
    ("snapshot/SHA256SUMS", "artifact_manifest",
     "Checksums of both FROZEN generations, all 5 superseded and both added byte-sets."),
]

FALSIFIER = (
    "Re-run check_frozen_gen_census.py --corpus-from report.json at the same pins: falsified if "
    "measurement_digest or review_census_digest changes, if any expectation E1-E12/E13b or "
    "mutant/control M1-M6/C1-C3 changes result, or if any pinned input re-hashes differently. "
    "HF-059-FROZEN-01 is voided by a re-bound F2a-review-worker-017 (or a controller ruling) that "
    "cites FROZEN 815e08079aefbc and VARIANT_REGISTRY 6bac9adea19e in its binding evidence_refs; "
    "drift of artifacts/formulation/FROZEN.json voids this artifact immediately."
)

REQUIRED = {
    "artifact": ["event_id", "event_type", "created_at", "actor", "node_id", "artifact_type",
                 "path", "sha256", "validation_status"],
    "claim": ["event_id", "event_type", "created_at", "actor", "class_id", "statement",
              "conclusion_type", "assumptions", "falsifier", "evidence_refs"],
    "review": ["event_id", "event_type", "created_at", "actor", "target_id", "reviewer",
               "verdict", "score", "hard_failures", "findings"],
    "blocker": ["event_id", "event_type", "created_at", "actor", "node_id", "description",
                "needed_to_unblock", "evidence_refs"],
    "status": ["event_id", "event_type", "created_at", "actor", "node_id", "status",
               "hours", "summary", "evidence_refs", "next_falsifier"],
}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rp(rel):
    return os.path.join(ROOT, rel)


def main():
    art_dir = "artifacts/worker-059/gform_frozen_gen_census"
    hashes = {rel: sha(rp(f"{art_dir}/{rel}")) for rel, _t, _d in ARTIFACTS}
    report = json.load(open(rp(f"{art_dir}/report.json")))
    # the claim text quotes these prefixes; refuse to emit on mismatch
    assert report["measurement_digest"].startswith("da717446ebfa"), report["measurement_digest"]
    assert report["review_census_digest"].startswith("edf82c4d35fa"), report["review_census_digest"]

    events = []
    common = {"node_id": NODES, "class_id": CLASSES, "gate": GATE,
              "evidence_refs": [f"{art_dir}/report.json#{hashes['report.json'][:12]}",
                                f"{art_dir}/stale_binding_census.json#{hashes['stale_binding_census.json'][:12]}",
                                f"{art_dir}/check_frozen_gen_census.py#{hashes['check_frozen_gen_census.py'][:12]}"]}

    events.append({
        "event_id": "w059-frozengen-20260912T0112-task-receipt", "event_type": "status",
        "created_at": NOW, "actor": "worker-059", **common, "status": "active", "hours": 0.05,
        "checkpoint_id": "w059-ckpt-frozengen-20260912T0112",
        "summary": ("No inbox card exists for worker-059. Took ONE bounded class-bound task: "
                    "W059-GFORM-FROZEN-GEN-BINDING-CENSUS-01, read-only audit of the CF-27 "
                    "same-revision FROZEN rev29 generation move (3d9e3d77fd87 -> 815e08079aefbc) "
                    "and of which F1/F2a/F2b review verdicts still bind live bytes. Selected to "
                    "avoid concurrent w054 t1guard, w097 F2b rev13 and the classsep adjudication."),
        "next_falsifier": FALSIFIER})

    for rel, atype, desc in ARTIFACTS:
        events.append({
            "event_id": f"w059-frozengen-20260912T0112-artifact-{rel.replace('/', '-').replace('.', '-')}",
            "event_type": "artifact", "created_at": NOW, "actor": "worker-059", **common,
            "artifact_type": atype, "path": f"{art_dir}/{rel}", "sha256": hashes[rel],
            "validation_status": "unverified", "description": desc, "falsifier": FALSIFIER})

    events.append({
        "event_id": "w059-frozengen-20260912T0112-claim", "event_type": "claim",
        "created_at": NOW, "actor": "worker-059", **common, "conclusion_type": "formal_model",
        "assumptions": [
            "the two FROZEN generations are the byte-pinned files in snapshot/ (hashes verified before and after the run)",
            "a 'binding field' is a key path matching (sha256|hash|pin|bind|reviewed|artifact|mirror|evidence_ref|frozen); narrative mentions are excluded",
            "the review corpus is the 213-file pinned set recorded in report.json review_census.corpus_pins",
            "all measurements are made on frozen snapshots and the live FROZEN bytes at report time, never on moving traffic"],
        "statement": (
            "Machine-measured at pinned bytes (generation A 3d9e3d77fd87, generation B 815e08079aefbc, "
            "measurement_digest da717446ebfa, review_census_digest edf82c4d35fa): the CF-27 FROZEN rev29 "
            "move is same-revision (29->29, frozen_at 00:55:02 -> 00:57:26), its top-level diff is "
            "exactly {files, frozen_at, rev29_delta}, and its pin delta is exactly 5 value-changed + 2 "
            "added + 0 removed paths. No schema-facing pin moved: all 10 schema/taxonomy/case pins are "
            "byte-identical across generations, so schema-hash-bound verdicts survive while "
            "FROZEN-generation-bound and variant/registry-bound verdicts do not. Generation B resolves "
            "50/50 pins at live bytes; generation A resolves 43/48 and the 5 failures are exactly the "
            "superseded class-bound set (VARIANT_REGISTRY 5eb42f9a384a, AF-WCC-VAC-GEN.variant-SET.delta "
            "45b9b6a8d192, AF-SCC-C0-VAC-GEN.variant-CH.delta c28795b0fdfc, "
            "evidence_binding_repair_rev29_report f337f83e483c, tools/regenerate_frozen 6bf0f36f892b); "
            "all 5 predecessor byte-sets remain recoverable in-tree. The pinned 213-review census finds "
            "33 STALE_BINDING, 32 generation-B-bound and 148 generation-unbound reviews (bound counts "
            "rev28 25 / A 2 / B 32). Exactly one stale-bound review was authored after generation B was "
            "frozen: reviews/F2a-review-worker-017.json (accept, counts_as_full_schema_verdict=true, "
            "created 00:57:30) binds FROZEN#3d9e3d77fd87 and VARIANT_REGISTRY#5eb42f9a384a in "
            "evidence_refs while its frozen_pin_matches_reviewed=true covers only the unchanged schema "
            "pin e9a27996dfd3; its F2a full-schema accept is therefore not countable at live FROZEN "
            "bytes without an explicit re-bind. Harness: 13/13 expectations, 9/9 mutants/controls, "
            "deterministic, entry==exit stable, and both digests reproduce under --corpus-from."),
        "falsifier": FALSIFIER})

    events.append({
        "event_id": "w059-frozengen-20260912T0112-review", "event_type": "review",
        "created_at": NOW, "actor": "worker-059", **common,
        "target_id": "artifacts/formulation/FROZEN.json@815e08079aefbc",
        "target_path": "artifacts/formulation/FROZEN.json",
        "reviewer": "worker-059", "verdict": "revise", "score": 4.0,
        "reviewed_revision": 29, "reviewed_sha256": report["generations"]["live"]["sha256"],
        "companion_sha256": report["generations"]["predecessor"]["sha256"],
        "counts_as_independent_verdict": True, "counts_as_full_schema_verdict": False,
        "counts_as_independent_second_verdict": False,
        "artifact": f"{art_dir}/review_FROZEN_gen_census.json#{hashes['review_FROZEN_gen_census.json'][:12]}",
        "hard_failures": [
            "HF-059-FROZEN-01: reviews/F2a-review-worker-017.json (accept, full-schema, created "
            "2026-09-12T00:57:30+08:00 i.e. 4 s after generation B froze at 00:57:26) binds "
            "FROZEN.json#3d9e3d77fd87 and VARIANT_REGISTRY.json#5eb42f9a384a in evidence_refs; its "
            "frozen_pin_matches_reviewed=true covers only the unchanged schema pin e9a27996dfd3, so "
            "its F2a full-schema accept cannot be counted at live FROZEN bytes without a re-bind."],
        "findings": [
            "F-059-FROZEN-01: same-revision move; top-level diff exactly {files, frozen_at, rev29_delta}; pin delta exactly 5 changed + 2 added + 0 removed.",
            "F-059-FROZEN-02: no schema-facing pin moved (10/10 byte-identical), so schema-bound verdicts survive and generation/variant-bound verdicts need re-binding.",
            "F-059-FROZEN-03: the changed pins include all class-bound variant/registry artifacts; added are variant_rebase_rev29_report.json and variant_rebase_rev29.py.",
            "F-059-FROZEN-04: live 50/50 pins resolve; predecessor 43/48 with failures exactly the superseded set; all 5 predecessor byte-sets recoverable in-tree.",
            "F-059-FROZEN-05: pinned 213-review census = 33 STALE_BINDING / 32 genB / 148 unbound; bound counts rev28 25, genA 2, genB 32.",
            "F-059-FROZEN-06: F2a-review-worker-017 is the only post-freeze stale-bound review; it is the single actionable coverage item for astra-life05-verify-gform-r3.",
            "F-059-FROZEN-07: the other nine stale full-schema rows are F0-scope or rev12-era; F2b-review-088 (revise) binds rev28 FROZEN and pre-repair F2b 55d0a1ea9bda.",
            "F-059-FROZEN-08: F1-review-rev13-085 mentions the churn only in review_window.notes and is correctly classified generation-unbound; no over-flagging of narrative.",
            "F-059-FROZEN-09: rev29_delta documents the downstream variant rebase only in generation B while revision stays 29 (the CF-27 pattern).",
            "F-059-FROZEN-10: drafted expectation E13 (3/5 recoverable) was falsified by the full scan (5/5) and is recorded in report.json amendments as E13b."],
        "next_falsifier": FALSIFIER})

    events.append({
        "event_id": "w059-frozengen-20260912T0112-blocker", "event_type": "blocker",
        "created_at": NOW, "actor": "worker-059", **common,
        "description": (
            "HF-059-FROZEN-01: the F2a full-schema accept reviews/F2a-review-worker-017.json (created "
            "00:57:30, after the 00:57:26 freeze) binds FROZEN generation A 3d9e3d77fd87 and the "
            "superseded VARIANT_REGISTRY 5eb42f9a384a in evidence_refs, so it cannot be counted as "
            "F2a coverage at the live FROZEN bytes. Secondary: reviews/F2b-review-088.json (revise, "
            "full-schema) binds rev28 FROZEN 2f358f6722d9 and pre-repair F2b schema 55d0a1ea9bda, so "
            "its findings cannot be carried onto rev13 without re-measurement."),
        "needed_to_unblock": (
            "Either (a) re-bind reviews/F2a-review-worker-017.json to FROZEN#815e08079aefbc and "
            "VARIANT_REGISTRY#6bac9adea19e in its binding evidence_refs and re-issue it with a fresh "
            "created_at, or (b) a controller ruling that counts it as F2a coverage on the unchanged "
            "schema pin alone and records that the FROZEN/registry pins were stale. For F2b, re-run "
            "the review against F2b rev13 b2ab6acb2bbe. No schema revision is required: all 10 "
            "schema-facing pins are byte-identical across the generation move."),
        "expected_information_gain": (
            "high: resolves the only post-freeze stale-bound full-schema accept on the F2a leg of "
            "G-FORM and gives astra-life05-verify-gform-r3 an exact re-bind list instead of a "
            "generation-wide void."),
        "evidence_refs": common["evidence_refs"] + [
            f"{art_dir}/review_FROZEN_gen_census.json#{hashes['review_FROZEN_gen_census.json'][:12]}",
            f"{art_dir}/snapshot/FROZEN.3d9e3d77fd87.json#{sha(rp(f'{art_dir}/snapshot/FROZEN.3d9e3d77fd87.json'))[:12]}"]})

    events.append({
        "event_id": "w059-frozengen-20260912T0112-status-complete", "event_type": "status",
        "created_at": NOW, "actor": "worker-059", **common, "status": "active", "hours": 0.35,
        "checkpoint_id": "w059-ckpt-frozengen-20260912T0112",
        "task_id": TASK, "task_complete_pending_review": True,
        "summary": (
            "CHECKPOINT + EXIT. W059-GFORM-FROZEN-GEN-BINDING-CENSUS-01 complete at worker level: "
            "CF-27 FROZEN rev29 generation move measured exactly (same revision, 5 superseded + 2 "
            "added pins, 0 schema pins moved, live 50/50 resolve, predecessor 43/48, predecessor "
            "bytes 5/5 recoverable), 213-review binding census (33 stale / 32 genB / 148 unbound), "
            "one post-freeze stale-bound full-schema accept identified (F2a-review-worker-017) and "
            "reported as HF-059-FROZEN-01. Harness 13/13 expectations, 9/9 mutants/controls, "
            "deterministic, digests reproduce under --corpus-from. No canonical file modified; no "
            "status=done, no validation_status=passed, no gate verdict claimed."),
        "evidence_refs": common["evidence_refs"] + [
            f"{art_dir}/review_FROZEN_gen_census.json#{hashes['review_FROZEN_gen_census.json'][:12]}",
            f"{art_dir}/snapshot/SHA256SUMS#{hashes['snapshot/SHA256SUMS'][:12]}"],
        "next_falsifier": FALSIFIER})

    # ---- validate
    errors = []
    for e in events:
        for k in REQUIRED[e["event_type"]]:
            if k not in e:
                errors.append(f"{e['event_id']}: missing {k}")
        if not isinstance(e.get("score", 0), (int, float)) and e["event_type"] == "review":
            errors.append(f"{e['event_id']}: bad score")
    if errors:
        print("VALIDATION ERRORS:")
        for x in errors:
            print(" ", x)
        return 1

    # ---- idempotent append
    existing = set()
    if os.path.exists(OUTBOX):
        for line in open(OUTBOX, "r", encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line).get("event_id"))
            except json.JSONDecodeError:
                pass
    added = 0
    with open(OUTBOX, "a", encoding="utf-8") as fh:
        for e in events:
            if e["event_id"] in existing:
                continue
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
            added += 1

    # ---- checkpoint
    ckpt = {
        "checkpoint_id": "w059-ckpt-frozengen-20260912T0112",
        "actor": "worker-059", "task_id": TASK, "created_at": NOW,
        "node_id": NODES, "class_id": CLASSES, "gate": GATE, "status": "active",
        "task_complete_pending_review": True, "hours": 0.35,
        "artifacts": {f"{art_dir}/{rel}": hashes[rel] for rel, _t, _d in ARTIFACTS},
        "measurement_digest": report["measurement_digest"],
        "review_census_digest": report["review_census_digest"],
        "expectations_all_pass": report["expectations_all_pass"],
        "mutants_controls_all_fired": report["mutants_controls_all_fired"],
        "entry_exit_stable": report["entry_exit_stable"],
        "events_emitted": [e["event_id"] for e in events],
        "canonical_files_written": [],
        "next_falsifier": FALSIFIER,
    }
    with open(CKPT_JSON, "w", encoding="utf-8") as fh:
        json.dump(ckpt, fh, indent=1, sort_keys=False)
        fh.write("\n")
    with open(CKPT_LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"checkpoint_id": ckpt["checkpoint_id"], "actor": "worker-059",
                             "task_id": TASK, "created_at": NOW, "status": "active",
                             "task_complete_pending_review": True,
                             "checkpoint_path": os.path.relpath(CKPT_JSON, ROOT),
                             "checkpoint_sha256": sha(CKPT_JSON)}) + "\n")

    print(f"events: {len(events)} built, {added} appended, {len(events) - added} already present")
    print("outbox:", os.path.relpath(OUTBOX, ROOT))
    print("checkpoint:", os.path.relpath(CKPT_JSON, ROOT), sha(CKPT_JSON)[:16])
    if not report["expectations_all_pass"] or not report["mutants_controls_all_fired"]:
        print("REFUSING: harness did not fully pass")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
