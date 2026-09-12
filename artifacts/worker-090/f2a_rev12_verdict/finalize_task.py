#!/usr/bin/env python3
"""Finalize W090-F2A-REV12-VERDICT-02: controls/evidence/review/checkpoint/outbox events.

Run after check_f2a_rev12.py. Appends (never overwrites) comms/outbox/worker-090.jsonl.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
REVIEWS = ROOT / "reviews"
STATE = ROOT / "runtime/state"
OUTBOX = ROOT / "comms/outbox/worker-090.jsonl"

PINS = {
    "F2a": ("schemas/af_scc_c2_vacuum.yaml",
            "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce"),
    "F0": ("research_map/formulation_taxonomy.yaml",
           "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"),
    "F0R": ("artifacts/formulation/formulation_taxonomy.yaml",
            "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1"),
    "F1": ("schemas/af_wcc_vacuum.yaml",
           "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3"),
    "F2b": ("schemas/af_scc_c0_vacuum.yaml",
            "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6"),
    "FROZEN": ("artifacts/formulation/FROZEN.json",
               "2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1"),
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def now() -> str:
    return _dt.datetime.now().astimezone().isoformat()


def main():
    results = json.loads((OUT / "results.json").read_text())
    controls = {
        "schema": "w090-f2a-rev12-controls/v1",
        "task_id": results["task_id"],
        "actor": "worker-090",
        "determinism_structural": results["controls"]["determinism_structural"],
        "mutants": results["controls"]["mutants"],
        "mutants_all_caught": results["controls"]["mutants_all_caught"],
        "pin_drift": results["controls"]["pin_drift"],
        "read_only_note": results["controls"]["read_only_note"],
    }
    (OUT / "controls.json").write_text(json.dumps(controls, indent=2) + "\n")

    deliverables = {}
    for name in ("check_f2a_rev12.py", "results.json", "controls.json", "README.md",
                 "raw_acceptance_stale.log", "raw_acceptance_rebased.log",
                 "raw_measure_rebased.log", "raw_f1_semantic_audit.json"):
        p = OUT / name
        if p.exists():
            deliverables[f"artifacts/worker-090/f2a_rev12_verdict/{name}"] = sha(p)

    ts = _dt.datetime.now().astimezone().strftime("%Y%m%dT%H%M%S")
    blocker_ids = results["summary"]["blocking_failures"]

    hard_failures = [
        {
            "id": "W090-F2A-01",
            "severity": "major (blocking for G-FORM; clearable by metadata refresh)",
            "axis": "f0_binding consistency-evidence hash binding",
            "finding": (
                "schemas/af_scc_c2_vacuum.yaml declares f0_binding.consistency_evidence_sha256="
                "675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48, but "
                "artifacts/formulation/evidence/taxonomy_consistency.json measures "
                "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b and embeds no sha256 "
                "of either compared tree. NEW in this task: a fresh run of the canonical checker on "
                "isolated copies of the frozen F0 pair reproduces the live evidence byte-for-byte "
                "(CONSISTENT, 4 classes, 0 divergences) and a supplement-contract mutation flips it to "
                "INCONSISTENT, so the substantive consistency claim is verified; the defect is the stale "
                "declaration plus the absence of embedded tree hashes. The declared 675a99d0 revision is "
                "not recoverable on disk or via git (evidence tree untracked)."
            ),
            "evidence_refs": [
                "schemas/af_scc_c2_vacuum.yaml#5476a3f2c6bc",
                "artifacts/formulation/evidence/taxonomy_consistency.json#9e335e9ba1bf",
                "artifacts/worker-090/f2a_rev12_verdict/results.json",
                "artifacts/formulation/tools/check_taxonomy_consistency.py",
            ],
            "falsifier": (
                "Embeds the measured sha256 of both compared trees in the evidence file and sets "
                "consistency_evidence_sha256 to the measured file hash; a re-run showing the declared "
                "675a99d0 equals the frozen-pair output would also close it."
            ),
        },
        {
            "id": "W090-F2A-02",
            "severity": "major (blocking for G-FORM; requires controller vocabulary single-sourcing)",
            "axis": "conclusion_type vocabulary authority",
            "finding": (
                "F2a's conclusion.conclusion_type is scc_c2_future_inextendibility. Canonical F0 "
                "field_vocabulary.conclusion_type.allowed lists only [weak_cosmic_censorship, "
                "strong_cosmic_censorship_C2, strong_cosmic_censorship_C0]; the equivalence to F2a's "
                "canonical token exists only in the authoring artifacts/formulation/VOCAB_ALIASES.json "
                "(46cd9f1eb534), whose policy says aliases must never appear in a new canonical artifact. "
                "Canonical F0's own axes.conclusion_type is the alias strong_cosmic_censorship_C2, so the "
                "registry and the taxonomy are not single-sourced. Alias-aware canonicalisation shows no "
                "C0/C2 merge (C2 stays scc_c2_future_inextendibility); a literal canonical-F0-only check "
                "rejects the schema. Matches the independent worker-045 blocker."
            ),
            "evidence_refs": [
                "schemas/af_scc_c2_vacuum.yaml#5476a3f2c6bc",
                "research_map/formulation_taxonomy.yaml#0abb9ed8a961",
                "artifacts/formulation/VOCAB_ALIASES.json#46cd9f1eb534",
                "artifacts/worker-090/f2a_rev12_verdict/results.json",
            ],
            "falsifier": (
                "A controller ruling designating one registry authoritative plus a revision of the other "
                "to match, or listing scc_c2_future_inextendibility in canonical F0's allowed set."
            ),
        },
        {
            "id": "W090-F2A-03",
            "severity": "major (blocking for the declared acceptance criterion; clearable by lead re-run)",
            "axis": "acceptance corpus preflight",
            "finding": (
                "artifacts/formulation/evidence/semantic_escape_rebased.json records base_sha256 "
                "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508 while the current "
                "authoring base artifacts/formulation/schemas/af_scc_c0_vacuum.yaml measures "
                "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6, so run_acceptance.py "
                "fails closed (exit 3, PREFLIGHT FAIL). Reproduced in a throwaway sandbox; re-running "
                "measure_semantic_escape.py rebases the corpus and F2a then passes both stages. After "
                "that sandbox rebase the family pipeline still returns FAIL because F1 (af_wcc_vacuum.yaml) "
                "is rejected by the worker-06 semantic auditor on R03 ('binder (q,t0) absent from formal "
                "sentence') - a rule-vs-text mismatch against the rev12 tail-predicate rewording, not an "
                "F2a defect. F2a's own row is structural=pass, semantic=pass; union catches 31/31 mutants, "
                "0 control false positives."
            ),
            "evidence_refs": [
                "artifacts/formulation/evidence/semantic_escape_rebased.json",
                "artifacts/formulation/tools/run_acceptance.py",
                "artifacts/worker-090/f2a_rev12_verdict/raw_acceptance_stale.log",
                "artifacts/worker-090/f2a_rev12_verdict/raw_acceptance_rebased.log",
                "artifacts/worker-090/f2a_rev12_verdict/raw_f1_semantic_audit.json",
                "schemas/af_scc_c0_vacuum.yaml#55d0a1ea9bda",
            ],
            "falsifier": (
                "Re-run measure_semantic_escape.py so the recorded base equals the current base and the "
                "preflight passes; separately, the F1 R03 rejection must be dispositioned (auditor rule "
                "update or F1 rewording) before the pipeline verdict can be PASS."
            ),
        },
    ]

    findings = [
        {"id": "W090-F2A-P1", "kind": "positive",
         "finding": "All five frozen inputs (F2a 5476a3f2, F0 0abb9ed8, supplement d7419b4e, FROZEN rev28 "
                    "2f358f67, evidence 9e335e9b) measure their pins at entry and exit (pin_drift empty); "
                    "FROZEN rev28 declares each of the three class paths.",
         "evidence_refs": ["artifacts/worker-090/f2a_rev12_verdict/results.json"]},
        {"id": "W090-F2A-P2", "kind": "positive",
         "finding": "F2a rev12 passes every class-semantics check independently implemented here: strict "
                    "YAML (0 duplicate keys), clock discipline, class identity, forall r in D0 binding with "
                    "no pair-typed binder, D0 tagged-union typing, domain resolution, SCC/WCC visibility "
                    "separation, canonical/supplement pointer resolution, and alias-aware C0/C2 non-merge.",
         "evidence_refs": ["schemas/af_scc_c2_vacuum.yaml#5476a3f2c6bc",
                           "artifacts/worker-090/f2a_rev12_verdict/results.json"]},
        {"id": "W090-F2A-P3", "kind": "positive",
         "finding": "30/33 checks pass; classes_semantics_failures is empty; 4/4 self-mutants are caught "
                    "(pointer corruption, future revised_at, duplicate key, C0 token swap); the structural "
                    "block is deterministic across a fresh re-read.",
         "evidence_refs": ["artifacts/worker-090/f2a_rev12_verdict/controls.json"]},
        {"id": "W090-F2A-N1", "kind": "new-measurement",
         "finding": "The consistency evidence is byte-reproducible from the frozen F0 pair and the "
                    "checker is mutation-sensitive, but the tool never reads the three class schemas "
                    "(coverage gap measured: output invariant to a garbage schema file; 0 'schemas/' "
                    "references in the tool). Evidence cannot itself certify schema-to-F0 consistency.",
         "evidence_refs": ["artifacts/worker-090/f2a_rev12_verdict/results.json",
                           "artifacts/formulation/tools/check_taxonomy_consistency.py"]},
    ]

    next_falsifier = (
        "Re-run artifacts/worker-090/f2a_rev12_verdict/check_f2a_rev12.py after the formulation lead's "
        "next freeze-metadata action: W090-F2A-01 closes only if f0_binding.consistency_evidence_sha256 "
        "equals the measured evidence file (and that file embeds both compared-tree hashes); W090-F2A-02 "
        "closes only on a controller vocabulary single-sourcing ruling; W090-F2A-03 closes only when "
        "measure_semantic_escape.py is re-run to the current base, and the separate F1 R03 semantic "
        "rejection must be dispositioned before run_acceptance.py can exit 0. Any of the 30 passing "
        "checks failing at the same pin, any self-mutant escaping, or any pin drift falsifies this verdict."
    )

    review = {
        "schema": "class-schema-review/v1",
        "review_id": "W090-F2A-REV12-VERDICT-02",
        "reviewer": "worker-090",
        "reviewer_role": "bounded execution worker (independent; did not author F2a, F0/F0R, F1, F2b or any prior F2a verdict)",
        "created_at": now(),
        "target_id": "F2a",
        "node_id": "F2a",
        "gate": "G-FORM",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "class_ids": ["AF-SCC-C2-VAC-GEN"],
        "artifact_path": "schemas/af_scc_c2_vacuum.yaml",
        "reviewed_sha256": PINS["F2a"][1],
        "artifact_sha256": PINS["F2a"][1],
        "counts_as_full_schema_verdict": True,
        "verdict": "revise",
        "score": 4.0,
        "hard_failures": hard_failures,
        "findings": findings,
        "positive_checks": results["summary"]["pass"],
        "checks_total": results["summary"]["checks_total"],
        "class_semantics_failures": results["summary"]["class_semantics_failures"],
        "artifact_refs": [
            "artifacts/worker-090/f2a_rev12_verdict/results.json",
            "artifacts/worker-090/f2a_rev12_verdict/controls.json",
            "artifacts/worker-090/f2a_rev12_verdict/evidence.json",
            "artifacts/worker-090/f2a_rev12_verdict/check_f2a_rev12.py",
            "artifacts/worker-090/f2a_rev12_verdict/README.md",
        ],
        "evidence_refs": [
            "schemas/af_scc_c2_vacuum.yaml#5476a3f2c6bc",
            "research_map/formulation_taxonomy.yaml#0abb9ed8a961",
            "artifacts/formulation/formulation_taxonomy.yaml#d7419b4e8963",
            "artifacts/formulation/FROZEN.json#2f358f6722d9",
            "artifacts/formulation/evidence/taxonomy_consistency.json#9e335e9ba1bf",
            "artifacts/formulation/VOCAB_ALIASES.json#46cd9f1eb534",
        ],
        "next_falsifier": next_falsifier,
        "authority_note": "advisory worker verdict; cannot set gate verdict or node status",
    }
    (REVIEWS / "F2a-rev12-verdict-090.json").write_text(json.dumps(review, indent=2) + "\n")

    evidence = {
        "schema": "w090-f2a-rev12-evidence/v1",
        "task_id": results["task_id"],
        "actor": "worker-090",
        "node_id": "F2a",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "gate": "G-FORM",
        "created_at": now(),
        "reviewed_sha256": PINS["F2a"][1],
        "pins": {k: {"path": v[0], "sha256": sha(ROOT / v[0]) if (ROOT / v[0]).exists() else None,
                     "expected": v[1]} for k, v in PINS.items()},
        "summary": results["summary"],
        "controls": controls,
        "deliverables": deliverables,
        "blocking_failure_ids": blocker_ids,
        "authority_note": "worker evidence only; no gate verdict, no node status, no canonical-file edit",
    }
    (OUT / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
    evidence_sha = sha(OUT / "evidence.json")
    review_sha = sha(REVIEWS / "F2a-rev12-verdict-090.json")

    def ev(suffix: str) -> str:
        return f"w090-f2a-{ts}-{suffix}"

    events = []
    for name, rel in deliverables.items():
        kind = "checker_code" if name.endswith(".py") else (
            "readme" if name.endswith(".md") else "raw_log" if name.endswith(".log") else "evidence")
        events.append({
            "actor": "worker-090", "event_type": "artifact", "event_id": ev(f"artifact-{name.split('/')[-1]}"),
            "created_at": now(), "node_id": "F2a", "class_id": "AF-SCC-C2-VAC-GEN", "gate": "G-FORM",
            "artifact_type": kind, "path": name, "sha256": rel,
            "evidence_refs": [f"schemas/af_scc_c2_vacuum.yaml#{PINS['F2a'][1][:12]}",
                              f"{name}#{rel[:12]}"],
            "validation_status": "unverified",
        })
    for rid, rel in (("review", "reviews/F2a-rev12-verdict-090.json"),
                     ("evidence", "artifacts/worker-090/f2a_rev12_verdict/evidence.json")):
        events.append({
            "actor": "worker-090", "event_type": "artifact", "event_id": ev(f"artifact-{rid}"),
            "created_at": now(), "node_id": "F2a", "class_id": "AF-SCC-C2-VAC-GEN", "gate": "G-FORM",
            "artifact_type": rid, "path": rel,
            "sha256": review_sha if rid == "review" else evidence_sha,
            "evidence_refs": [f"{rel}#{(review_sha if rid == 'review' else evidence_sha)[:12]}"],
            "validation_status": "unverified",
        })
    events.append({
        "actor": "worker-090", "event_type": "review", "event_id": ev("review"), "created_at": now(),
        "target_id": "F2a", "node_id": "F2a", "class_id": "AF-SCC-C2-VAC-GEN", "gate": "G-FORM",
        "reviewer": "worker-090", "verdict": "revise", "score": 4.0,
        "reviewed_sha256": PINS["F2a"][1], "counts_as_full_schema_verdict": True,
        "hard_failures": [h["id"] for h in hard_failures],
        "class_semantics_failures": [],
        "findings": [f["id"] for f in findings],
        "artifact_refs": ["reviews/F2a-rev12-verdict-090.json",
                          "artifacts/worker-090/f2a_rev12_verdict/evidence.json",
                          "artifacts/worker-090/f2a_rev12_verdict/results.json",
                          "artifacts/worker-090/f2a_rev12_verdict/controls.json"],
        "evidence_refs": [f"reviews/F2a-rev12-verdict-090.json#{review_sha[:12]}",
                          f"artifacts/worker-090/f2a_rev12_verdict/evidence.json#{evidence_sha[:12]}",
                          f"schemas/af_scc_c2_vacuum.yaml#{PINS['F2a'][1][:12]}",
                          f"research_map/formulation_taxonomy.yaml#{PINS['F0'][1][:12]}",
                          f"artifacts/formulation/evidence/taxonomy_consistency.json#9e335e9ba1bf",
                          f"artifacts/formulation/VOCAB_ALIASES.json#46cd9f1eb534"],
        "next_falsifier": next_falsifier,
        "authority_note": "advisory worker verdict; cannot set gate verdict or node status",
    })
    events.append({
        "actor": "worker-090", "event_type": "status", "event_id": ev("status"), "created_at": now(),
        "node_id": "F2a", "class_id": "AF-SCC-C2-VAC-GEN", "gate": "G-FORM", "status": "active",
        "hours": 0.4,
        "summary": ("W090-F2A-REV12-VERDICT-02 complete at worker level: independent full-schema "
                    "verification of F2a AF-SCC-C2-VAC-GEN at the frozen 5476a3f2. 33 checks "
                    "(30 pass, 3 blocking fail), 4/4 mutants caught, pins stable. Verdict revise 4.0 with "
                    "zero class-semantics failures: W090-F2A-01 stale consistency-evidence declaration "
                    "(substantive claim independently reproduced + mutation-sensitive), W090-F2A-02 "
                    "vocabulary authority split (needs controller single-sourcing), W090-F2A-03 stale "
                    "acceptance corpus (rebase is a lead re-run). New: family acceptance pipeline also "
                    "rejects F1 on semantic rule R03, not F2a."),
        "evidence_refs": [f"reviews/F2a-rev12-verdict-090.json#{review_sha[:12]}",
                          f"artifacts/worker-090/f2a_rev12_verdict/evidence.json#{evidence_sha[:12]}",
                          f"artifacts/worker-090/f2a_rev12_verdict/results.json",
                          f"schemas/af_scc_c2_vacuum.yaml#{PINS['F2a'][1][:12]}"],
        "next_falsifier": next_falsifier,
        "authority_note": "advisory worker status; no gate verdict, no node status promotion",
    })

    with OUTBOX.open("a") as fh:
        for e in events:
            fh.write(json.dumps(e) + "\n")

    checkpoint = {
        "checkpoint_id": f"w090-ckpt4-{ts}",
        "worker": "worker-090",
        "slot": "090",
        "at": now(),
        "task": "W090-F2A-REV12-VERDICT-02 independent full-schema verdict on F2a AF-SCC-C2-VAC-GEN at frozen rev12 5476a3f2",
        "node_id": "F2a",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "gate": "G-FORM",
        "status": "complete",
        "reviewed": {"path": "schemas/af_scc_c2_vacuum.yaml", "revision": 12,
                     "sha256": PINS["F2a"][1], "stable_pre_post": True},
        "verdict": "revise",
        "score": 4.0,
        "hard_failures": [h["id"] for h in hard_failures],
        "class_semantics_failures": [],
        "checks": {"total": results["summary"]["checks_total"], "pass": results["summary"]["pass"],
                   "blocking_fail": results["summary"]["blocking_failures"]},
        "artifacts": {k: v for k, v in deliverables.items()},
        "review": {"path": "reviews/F2a-rev12-verdict-090.json", "sha256": review_sha},
        "evidence": {"path": "artifacts/worker-090/f2a_rev12_verdict/evidence.json", "sha256": evidence_sha},
        "events_emitted": [e["event_id"] for e in events],
        "outbox": "comms/outbox/worker-090.jsonl",
        "pin_drift": results["controls"]["pin_drift"],
        "next_falsifier": next_falsifier,
        "authority_note": results["authority_note"],
    }
    (STATE / "w090_checkpoint_4.json").write_text(json.dumps(checkpoint, indent=2) + "\n")
    with (STATE / "w090_checkpoints.jsonl").open("a") as fh:
        fh.write(json.dumps({k: checkpoint[k] for k in
                             ("checkpoint_id", "worker", "slot", "at", "task", "node_id", "class_id",
                              "gate", "status", "verdict", "score", "hard_failures", "review",
                              "evidence", "outbox", "next_falsifier")}) + "\n")

    final_drift = []
    for k, (rel, want) in PINS.items():
        got = sha(ROOT / rel) if (ROOT / rel).exists() else None
        if got != want:
            final_drift.append({"pin": k, "measured": got, "expected": want})
    print(json.dumps({
        "events": [e["event_id"] for e in events],
        "review_sha256": review_sha,
        "evidence_sha256": evidence_sha,
        "checkpoint": "runtime/state/w090_checkpoint_4.json",
        "final_pin_drift": final_drift,
    }, indent=1))
    return 0 if not final_drift else 1


if __name__ == "__main__":
    raise SystemExit(main())
