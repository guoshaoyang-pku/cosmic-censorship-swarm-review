#!/usr/bin/env python3
"""Finalize W053-F1-REV12-INDEP-VERIFY-01: hashes, review record, checkpoint, outbox.

Reads report.json (written by check_f1_rev12.py) and emits:
  - hashes.txt                       sha256 of all five task artifacts
  - reviews/F1-review-053.json       hash-bound independent review (controller scan format)
  - runtime/state/w053_f1_rev12_checkpoint.json + w053_checkpoints.jsonl
  - appended JSONL events in comms/outbox/worker-053.jsonl
Nothing under research_map/, schemas/, ledger/ or artifacts/formulation/ is written.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
CST = _dt.timezone(_dt.timedelta(hours=8))
NOW = _dt.datetime.now(CST)
STAMP = NOW.strftime("%Y%m%dT%H%M%S")
NOW_ISO = NOW.isoformat(timespec="seconds")

ARTIFACTS = [
    ("checker", "artifacts/worker-053/f1_rev12_verify/check_f1_rev12.py"),
    ("report", "artifacts/worker-053/f1_rev12_verify/report.json"),
    ("controls", "artifacts/worker-053/f1_rev12_verify/controls.json"),
    ("summary", "artifacts/worker-053/f1_rev12_verify/README.md"),
    ("run_log", "artifacts/worker-053/f1_rev12_verify/run.log"),
]
F1 = "schemas/af_wcc_vacuum.yaml"
CANON = "research_map/formulation_taxonomy.yaml"
CONS = "artifacts/formulation/evidence/taxonomy_consistency.json"


def sha(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def main() -> int:
    rep = json.loads((OUT / "report.json").read_text())
    pins = rep["pins_before"]
    f1_sha = pins[F1]["sha256"]
    h = {name: {"path": rel, "sha256": sha(rel)} for name, rel in ARTIFACTS}

    (OUT / "hashes.txt").write_text(
        "".join(f"{v['sha256']}  {v['path']}\n" for v in h.values()))
    h["hashes"] = {"path": "artifacts/worker-053/f1_rev12_verify/hashes.txt",
                   "sha256": sha("artifacts/worker-053/f1_rev12_verify/hashes.txt")}

    # ---------------- review record ----------------
    c8 = rep["checks"]["C8"]["measured"]
    c11 = rep["checks"]["C11"]["measured"]
    hard = [{
        "id": "HF053-1",
        "name": "stale_consistency_evidence_pin",
        "severity": "major",
        "class_id": "AF-WCC-VAC-GEN",
        "detail": (
            f"{F1}#{f1_sha[:12]} declares f0_binding.consistency_evidence_sha256="
            f"{c8['declared_consistency_evidence_sha256'][:16]}..., but the measured "
            f"{CONS} is {c8['measured_consistency_evidence_sha256'][:16]}... "
            f"(mtime {c8['evidence_file_mtime']} > declared checked_at {c8['checked_at']}; "
            f"FROZEN revision {rep['checks']['C9']['measured']['revision']} pins the measured "
            "hash). The declared F0 taxonomy hash itself is fresh "
            f"({c8['declared_f0_matches_measured']}), and the evidence file still reports "
            "consistent=true over the four classes; the defect is the false evidence-hash "
            "declaration, whose own rule requires a refresh before any gate verdict."),
        "fix": ("refresh f0_binding.consistency_evidence_sha256 to the measured hash of "
                "artifacts/formulation/evidence/taxonomy_consistency.json, bump revised_at and "
                "re-freeze; no class-semantics change"),
        "gate_effect": ("G-FORM cannot accept F1 at this hash: an accept would certify a "
                        "declared evidence hash that is false at the measured bytes."),
        "evidence_refs": [
            f"{F1}#{f1_sha[:12]}",
            f"{CONS}#{c8['measured_consistency_evidence_sha256'][:12]}",
            f"artifacts/worker-053/f1_rev12_verify/report.json#{h['report']['sha256'][:12]}",
            f"artifacts/worker-053/f1_rev12_verify/controls.json#{h['controls']['sha256'][:12]}",
        ],
    }]
    findings = [
        {"id": "P053-1", "severity": "positive", "kind": "rev11 HF closed",
         "finding": "duplicate revised_at keys: no duplicate mapping key anywhere in the F1 document (C2)."},
        {"id": "P053-2", "severity": "positive", "kind": "rev11 HF closed",
         "finding": "future-dated timestamps: no ISO-8601 string in the parsed document is ahead of the run clock (C3)."},
        {"id": "P053-3", "severity": "positive", "kind": "rev11 HF closed",
         "finding": "class_contract_pointer resolves at research_map/formulation_taxonomy.yaml#classes.AF-WCC-VAC-GEN; the supplement pointer is a separate field and resolves in the supplement (C4)."},
        {"id": "P053-4", "severity": "positive", "kind": "rev11 HF closed",
         "finding": "AF_{I+} is defined by i_plus.predicate_abbreviation and is used by conclusion.statement_formal (C5)."},
        {"id": "P053-5", "severity": "positive", "kind": "rev11 HF-025-1 closed",
         "finding": "quantifiers.formal uses the canonical single-q TAIL predicate, D5 labels whole-curve as strictly stronger and not the predicate, and the discriminating model separates the two readings (C6)."},
        {"id": "P053-6", "severity": "positive", "kind": "rev11 HF-025-2 closed",
         "finding": "D0 is a tagged disjoint union (smooth | (sobolev,s,delta)) and the formal quantifier binds r over D0; no pair binder remains (C7)."},
        {"id": "P053-7", "severity": "positive", "kind": "freeze integrity",
         "finding": f"FROZEN revision {rep['checks']['C9']['measured']['revision']} pins all "
                    f"{rep['checks']['C9']['measured']['files_listed']} listed files byte-exactly, including F1, the canonical taxonomy and the supplement (C9)."},
        {"id": "F053-11", "severity": "minor", "kind": "freeze hygiene",
         "finding": ((f"{CONS} was rewritten at {c11['post_freeze_writes'][0]['mtime']}, after "
                      "frozen_at; bytes are identical to the frozen pin, so this is an idempotent-rewrite "
                      "signal (C11), not a content defect.") if c11.get("post_freeze_writes")
                     else "no FROZEN-listed file was touched after frozen_at (C11 pass).")},
    ]
    review = {
        "review_id": "F1-review-053",
        "task_id": rep["task_id"],
        "created_at": NOW_ISO,
        "reviewed_at": rep["created_at"],
        "reviewer": "worker-053",
        "reviewer_independence": (
            "not an author of schemas/af_wcc_vacuum.yaml, research_map/formulation_taxonomy.yaml, "
            "artifacts/formulation/** or of any prior F1 review; read the canonical bytes once into "
            "memory and checked them with an independently written checker "
            "(artifacts/worker-053/f1_rev12_verify/check_f1_rev12.py) whose 8 planted-defect "
            "controls all fire."),
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-FORM",
        "target_id": "F1",
        "target": {"target_id": "F1", "path": F1, "sha256": f1_sha, "artifact_sha256": f1_sha},
        "reviewed_path": F1,
        "reviewed_sha256": f1_sha,
        "reviewed_mtime": pins[F1]["mtime"],
        "hash_stable_during_review": rep["stable"],
        "counts_as_full_schema_verdict": True,
        "verdict": rep["verdict"],
        "score": rep["score"],
        "hard_failures": hard,
        "findings": findings,
        "check_matrix": rep["measured_bottom_line"]["check_matrix"],
        "controls": {"total": len(rep["controls"]), "detected": sum(1 for c in rep["controls"] if c["detected"])},
        "evidence_refs": [
            f"{F1}#{f1_sha[:12]}",
            f"{CANON}#{pins[CANON]['sha256'][:12]}",
            f"{CONS}#{pins[CONS]['sha256'][:12]}",
            f"artifacts/worker-053/f1_rev12_verify/report.json#{h['report']['sha256'][:12]}",
            f"artifacts/worker-053/f1_rev12_verify/controls.json#{h['controls']['sha256'][:12]}",
            f"artifacts/worker-053/f1_rev12_verify/check_f1_rev12.py#{h['checker']['sha256'][:12]}",
        ],
        "falsifier": (
            "Re-run check_f1_rev12.py at the same pins. Falsified if any of C1-C11 flips, if any of the "
            "8 controls stops firing, if any pinned input drifts during the run, or if the measured "
            "consistency-evidence hash equals the declared 675a99d0... (i.e. the C8 hard failure is "
            "repaired by a refresh)."),
    }
    (ROOT / "reviews" / "F1-review-053.json").write_text(
        json.dumps(review, indent=2, sort_keys=True) + "\n")
    h["review"] = {"path": "reviews/F1-review-053.json",
                   "sha256": sha("reviews/F1-review-053.json")}

    # ---------------- checkpoint ----------------
    events = [f"w053-f1rev12-{STAMP}-task"] + \
             [f"w053-f1rev12-{STAMP}-artifact-{n}" for n, _ in ARTIFACTS] + \
             [f"w053-f1rev12-{STAMP}-claim", f"w053-f1rev12-{STAMP}-review",
              f"w053-f1rev12-{STAMP}-complete"]
    ckpt = {
        "checkpoint_id": f"w053-f1rev12-ckpt-{STAMP}",
        "worker": "worker-053",
        "task_id": rep["task_id"],
        "created_at": NOW_ISO,
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-FORM",
        "result": (f"verdict {rep['verdict']} score {rep['score']}; rev11 hard findings verified "
                   "resolved at the measured hash; 1 major residual (stale consistency-evidence pin "
                   "C8) + 1 minor (byte-identical post-freeze touch C11); drift stable; controls 8/8"),
        "checks": "10/12 PASS (C8 major FAIL, C11 minor FAIL)",
        "f1_sha256_measured": f1_sha,
        "canonical_f0_sha256_measured": pins[CANON]["sha256"],
        "consistency_evidence_sha256_measured": pins[CONS]["sha256"],
        "frozen_revision": rep["checks"]["C9"]["measured"]["revision"],
        "frozen_files_match": rep["checks"]["C9"]["measured"]["files_match"],
        "drift_stable": rep["stable"],
        "controls_detected": review["controls"],
        "artifacts": {v["path"]: v["sha256"] for v in h.values()},
        "events": events,
        "review": "reviews/F1-review-053.json",
        "outbox": "comms/outbox/worker-053.jsonl",
        "next_falsifier": review["falsifier"],
        "map_sha256_measured": sha("research_map/research_map.json"),
    }
    (ROOT / "runtime" / "state" / f"w053_f1rev12_checkpoint_{STAMP}.json").write_text(
        json.dumps(ckpt, indent=2, sort_keys=True) + "\n")
    with open(ROOT / "runtime" / "state" / "w053_checkpoints.jsonl", "a") as f:
        f.write(json.dumps(ckpt, sort_keys=True) + "\n")

    # ---------------- outbox ----------------
    ev = []

    def art_event(name: str, info: dict, atype: str, summary: str):
        ev.append({
            "event_id": f"w053-f1rev12-{STAMP}-artifact-{name}",
            "event_type": "artifact",
            "created_at": NOW_ISO,
            "actor": "worker-053",
            "node_id": "F1",
            "class_id": "AF-WCC-VAC-GEN",
            "gate": "G-FORM",
            "artifact_type": atype,
            "path": info["path"],
            "sha256": info["sha256"],
            "validation_status": "unverified",
            "summary": summary,
            "evidence_refs": [f"{info['path']}#{info['sha256'][:12]}"],
        })

    ev.append({
        "event_id": f"w053-f1rev12-{STAMP}-task",
        "event_type": "status",
        "created_at": NOW_ISO,
        "actor": "worker-053",
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-FORM",
        "status": "active",
        "hours": 0.15,
        "summary": ("No assignment card exists in comms/inbox for worker-053 (relaunched slot); took ONE "
                    "bounded class-bound task, W053-F1-REV12-INDEP-VERIFY-01: independent machine "
                    f"verification of {F1} at its measured hash against the rev11 hard findings, the "
                    "declared F0/consistency bindings and the FROZEN manifest."),
        "evidence_refs": ["research_map/ASTRA_HANDOFF.md", "comms/PROTOCOL.md"],
        "next_falsifier": review["falsifier"],
    })
    art_event("checker", h["checker"], "verification_tool",
              "Standalone read-only F1 rev12 checker: one-read pinning, 11 checks with falsifiers, drift guard, 8 planted-defect controls.")
    art_event("report", h["report"], "verification_report",
              f"Full machine record: verdict {rep['verdict']} score {rep['score']}, per-check measurements, pins before/after, drift and control results.")
    art_event("controls", h["controls"], "control_results",
              "8/8 planted defects detected by the same predicate functions used in the checks.")
    art_event("summary", h["summary"], "summary",
              "Human-readable adjudication, rev11 finding-by-finding table, rerun command and authority note.")
    art_event("runlog", h["run_log"], "run_log",
              "Captured stdout of the drift-stable verification run.")
    ev.append({
        "event_id": f"w053-f1rev12-{STAMP}-claim",
        "event_type": "claim",
        "created_at": NOW_ISO,
        "actor": "worker-053",
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-FORM",
        "conclusion_type": "formal_model",
        "statement": (
            f"At the pinned snapshot (F1 {f1_sha[:12]}, canonical F0 {pins[CANON]['sha256'][:12]}, "
            f"consistency evidence {pins[CONS]['sha256'][:12]}, FROZEN rev "
            f"{rep['checks']['C9']['measured']['revision']}, drift stable, controls 8/8), F1 rev12 "
            "resolves all six rev11 hard findings (no duplicate keys, no future timestamps, pointer at "
            "canonical #classes with a separate supplement pointer, AF_{I+} defined, single-q tail "
            "predicate with matching negation, D0 tagged-union binder r), and FROZEN pins all listed "
            "files byte-exactly; but the artifact's own f0_binding declares consistency_evidence_sha256 "
            "675a99d0... while the measured evidence file is 9e335e9b..., so at this hash an independent "
            "review verdict is revise (one major), score 3.75, with a minor byte-identical post-freeze "
            "touch on the same evidence file. This is a formal-model/artifact-level finding; it sets no "
            "gate verdict and no node status."),
        "assumptions": [
            "the two F0 paths remain the different-artifacts exception recorded in FROZEN rev27 path_policy",
            "the controller's target alias F1 == schemas/af_wcc_vacuum.yaml and hash prefix matching at 12 hex",
            "the declared consistency-evidence pin is normative because f0_binding.rule says it must be refreshed before any gate verdict",
        ],
        "falsifier": review["falsifier"],
        "evidence_refs": [
            f"{F1}#{f1_sha[:12]}",
            f"{CONS}#{pins[CONS]['sha256'][:12]}",
            f"reviews/F1-review-053.json#{h['review']['sha256'][:12]}",
            f"artifacts/worker-053/f1_rev12_verify/report.json#{h['report']['sha256'][:12]}",
        ],
        "artifact_refs": [f"{v['path']}#{v['sha256'][:12]}" for v in h.values()],
    })
    ev.append({
        "event_id": f"w053-f1rev12-{STAMP}-review",
        "event_type": "review",
        "created_at": NOW_ISO,
        "actor": "worker-053",
        "target_id": "F1",
        "reviewer": "worker-053",
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-FORM",
        "verdict": rep["verdict"],
        "score": rep["score"],
        "reviewed_sha256": f1_sha,
        "counts_as_full_schema_verdict": True,
        "hard_failures": hard,
        "findings": findings,
        "evidence_refs": review["evidence_refs"],
    })
    ev.append({
        "event_id": f"w053-f1rev12-{STAMP}-complete",
        "event_type": "status",
        "created_at": NOW_ISO,
        "actor": "worker-053",
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-FORM",
        "status": "active",
        "hours": 0.15,
        "summary": (f"W053-F1-REV12-INDEP-VERIFY-01 complete: 6 artifacts on disk and hash-pinned; "
                    f"verdict {rep['verdict']} score {rep['score']} (C8 major stale consistency-evidence "
                    "pin; C11 minor post-freeze touch); drift stable; controls 8/8; task-completion status, "
                    "not a node transition (workers cannot set done/passed or a gate verdict)."),
        "evidence_refs": [f"{v['path']}#{v['sha256'][:12]}" for v in h.values()],
        "next_falsifier": review["falsifier"],
    })

    out = ROOT / "comms" / "outbox" / "worker-053.jsonl"
    text = out.read_text()
    if text and not text.endswith("\n"):
        text += "\n"
    with open(out, "w") as f:
        f.write(text + "".join(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n" for e in ev))

    print(f"review    reviews/F1-review-053.json {h['review']['sha256'][:12]} verdict={rep['verdict']} score={rep['score']}")
    print(f"checkpoint runtime/state/w053_f1rev12_checkpoint_{STAMP}.json")
    print(f"outbox    {len(ev)} events appended to comms/outbox/worker-053.jsonl")
    for e in ev:
        print(f"  {e['event_id']} [{e['event_type']}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
