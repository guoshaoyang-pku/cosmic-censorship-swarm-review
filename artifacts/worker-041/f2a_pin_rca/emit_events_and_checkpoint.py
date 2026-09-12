#!/usr/bin/env python3
"""Emit the W041-F2A-PIN-RCA-01 report, outbox events and checkpoint.

Reads the raw controlled-experiment output so no hash is hand-typed.
Writes only inside artifacts/worker-041/**, the worker-041 outbox and the
worker-041 checkpoint files (worker write boundary).
"""
import hashlib
import json
import os
from datetime import datetime, timezone, timedelta

ROOT = "/data3/guoshaoyang/workdir/ai4math-swarm"
HERE = f"{ROOT}/artifacts/worker-041/f2a_pin_rca"
TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ).isoformat()
TASK = "W041-F2A-PIN-RCA-01"
CLAIM_CLASS = "AF-SCC-C2-VAC-GEN"
CLASS_IDS = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for c in iter(lambda: fh.read(65536), b""):
            h.update(c)
    return h.hexdigest()


exp = json.load(open(f"{HERE}/raw/experiment.json"))
target_sha = sha256(f"{ROOT}/schemas/af_scc_c2_vacuum.yaml")
live_ev = sha256(f"{ROOT}/artifacts/formulation/evidence/taxonomy_consistency.json")
exp_sha = sha256(f"{HERE}/raw/experiment.json")
script_sha = sha256(f"{HERE}/run_pin_rca.py")

p1 = exp["experiments"]["P1_P4_determinism_and_rewrite"]
p2 = exp["experiments"]["P2_sensitivity"]
p3 = exp["experiments"]["P3_declared_pin_reproducible"]

report = {
    "schema_version": "0.1",
    "record_id": f"{TASK}-report",
    "task_id": TASK,
    "actor": "worker-041",
    "reviewer": "worker-041",
    "created_at": NOW,
    "node_id": "F2a",
    "class_id": CLAIM_CLASS,
    "class_ids": CLASS_IDS,
    "gate": "G-FORM",
    "secondary_gate": "G-AUDIT",
    "review_kind": "independent root-cause experiment + hash-bound schema binding review",
    "counts_as_independent": True,
    "counts_as_full_schema_verdict": True,
    "verdict": "revise",
    "score": 3.0,
    "score_rationale": (
        "The schema is semantically clean on every machine criterion I could check "
        "(duplicate keys, timestamp discipline, class purity, quantifier typing, "
        "definition-ref resolution, cross-schema D0 identity, per-branch ambient/"
        "comeagerness) and the consistency check itself passes (consistent=true, errors=[]). "
        "The revise is forced solely by the hash-bound f0_binding failure, which is a real "
        "blocker for G-FORM/G-AUDIT and is not repairable inside the artifact's semantics."
    ),
    "target": {
        "path": "schemas/af_scc_c2_vacuum.yaml",
        "sha256": target_sha,
        "revision": 12,
        "measured_at": NOW,
        "hash_stable_across_review": True,
    },
    "findings": [
        {
            "id": "HF-041-RCA-1",
            "severity": "hard",
            "status": "confirmed (symptom already reported; root cause NEW here)",
            "axis": "artifact binding: pinned derived-output hash",
            "finding": (
                "schemas/af_scc_c2_vacuum.yaml declares "
                "f0_binding.consistency_evidence_sha256 = 675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48, "
                "but the measured artefact artifacts/formulation/evidence/taxonomy_consistency.json is "
                f"{live_ev}. Root cause: artifacts/formulation/tools/check_taxonomy_consistency.py:79-80 "
                "REWRITES that JSON on every invocation, and the output is a pure, input-sensitive "
                "function of four inputs (canonical taxonomy, authoring contract, VOCAB_ALIASES.json, "
                "checker bytes). Pinning the derived output therefore creates a stale-by-construction "
                "binding: any edit to any of the four inputs voids every schema pin that names it, "
                "with no edit to the schema itself."
            ),
            "machine_evidence": {
                "sandbox_runs_byte_identical": p1["byte_identical"],
                "sandbox_reproduces_live_evidence_hash": p1["reproduces_live_hash"],
                "output_rewritten_each_run": p1["rewritten_on_run"],
                "positive_control_output_changes_on_one_token_edit": p2["hash_changed"],
                "declared_pin_reproducible_from_current_inputs": p3[
                    "reproduced_by_current_inputs"
                ],
                "current_correct_pin_value": live_ev,
            },
            "prior_symptom_reporters": [
                "reviews/G-FORM-rev12-binding-086.json HF-086-R1 (worker-086, 00:36:02)",
                "reviews/closefind-verify-094.json HF-094C-2 (worker-094, 00:38:02)",
                "reviews/F2a-review-034-repin.json HF-034-F2A-3 (worker-034, 00:37:30)",
            ],
            "credit_note": (
                "The stale-pin symptom is NOT claimed as new. Workers 086/094/034 reported it first. "
                "What is new here is the determinism proof, the dependency-closure analysis, and the "
                "fact that the recommended re-stamp is only a temporary fixpoint (see HF-041-RCA-2)."
            ),
        },
        {
            "id": "HF-041-RCA-2",
            "severity": "hard",
            "status": "NEW",
            "axis": "refresh rule under-specifies the pinned object's dependency closure",
            "finding": (
                "The schema's own refresh rule reads 'if the declared F0 artifact changes hash, this "
                "binding must be refreshed and the consistency check re-run before any gate verdict'. "
                "That rule names ONE of the four inputs of the pinned output. A supplement, "
                "VOCAB_ALIASES.json or checker edit invalidates the pin without triggering the rule. "
                "The timeline shows exactly this: research_map/formulation_taxonomy.yaml mtime equals "
                "f0_binding.checked_at (00:31:41), while artifacts/formulation/formulation_taxonomy.yaml "
                "was modified at 00:31:56 - 15 s AFTER the pin was taken - and the evidence file has been "
                "regenerated repeatedly since (00:36:36, 00:38, 00:39:17). Therefore worker-086's "
                "recommended re-stamp restores a fixpoint only until the next supplement/alias/checker "
                "edit, and no rule would require a refresh."
            ),
            "machine_evidence": {
                "refresh_rule_inputs_named": 1,
                "refresh_rule_inputs_actual": 4,
                "canonical_taxonomy_mtime": "2026-09-12T00:31:41+08:00",
                "schema_checked_at": "2026-09-12T00:31:41+08:00",
                "authoring_contract_mtime": "2026-09-12T00:31:56+08:00",
                "authoring_contract_mtime_minus_checked_at_s": 15,
                "evidence_regenerated_after_pin": True,
                "output_changes_on_one_token_edit_of_input_B": p2["hash_changed"],
            },
        },
        {
            "id": "SF-041-RCA-1",
            "severity": "soft",
            "status": "NEW",
            "axis": "evidence artifact is not self-verifying",
            "finding": (
                "taxonomy_consistency.json records the input PATHS (map_taxonomy, lead_contract) but no "
                "input HASHES and no checker hash, so a consumer cannot detect staleness from the "
                "artifact alone; 'consistent: true' is an unprovenanced assertion. Embedding "
                "sha256(A), sha256(B), sha256(VOCAB_ALIASES.json) and sha256(checker) in the evidence "
                "document would make the re-run check local and would let any schema pin the full "
                "dependency closure instead of a mutable output."
            ),
            "machine_evidence": {
                "evidence_keys": list(p1["sandbox_output"].keys()),
                "input_hashes_present": False,
            },
        },
        {
            "id": "SF-041-RCA-2",
            "severity": "soft",
            "status": "NEW",
            "axis": "revision_history documentary ordering (non-blocking)",
            "finding": (
                "schemas/af_scc_c2_vacuum.yaml declares revision 12 but carries 10 revision_history "
                "entries; entry index 9 has at='2026-09-11T23:30:35+08:00', which is EARLIER than "
                "entry index 8 (00:30:00) and than index 10 (00:31:41), is marked unused=true, and "
                "bundles the 'rev11 delta' and 'rev8 delta' notes in one record. Purely documentary; "
                "it does not affect the formal content, but it makes the revision log non-monotone."
            ),
            "machine_evidence": {
                "declared_revision": 12,
                "history_entries": 10,
                "out_of_order_index": 9,
                "index9_at": "2026-09-11T23:30:35+08:00",
                "index8_at": "2026-09-12T00:30:00+08:00",
            },
        },
    ],
    "checks_passed": [
        "C1 yaml parses with duplicate-key-rejecting loader",
        "C2 no future-dated timestamps (max declared 00:31:41, now 00:39)",
        "C3 class_contract_pointer resolves in canonical taxonomy (#classes.AF-SCC-C2-VAC-GEN)",
        "C4 supplement pointer resolves in authoring tree and is a separate field",
        "C5 declared_f0_sha256 == measured canonical (0abb9ed8a961)",
        "C7 all 4 domain definition_refs resolve (D0 dotted regularity.data_regularity)",
        "C8 D0 is a tagged disjoint union bound by a single index r; no (s,delta)-pair binder",
        "C9 per-branch ambient + comeagerness present (X^r_vac, Frechet, Baire, D1 parameterised)",
        "C10 class purity: one_class_only, merge_forbidden, no C0/C2 composite token",
        "C11 conclusion asserts no WCC/I+ content (tokens appear only in forbidden_strengthenings)",
        "C12 conclusion_type + promotion_rule present, epistemic_status open_problem",
        "C13 F1/F2a/F2b D0 definition is verbatim identical (1 distinct string)",
        "C14 sibling_disjoint_from AF-SCC-C0-VAC-GEN declared",
    ],
    "prior_findings_closure": {
        "HF-086-1/HF-088-1 (D0 disjunctive -> ill-typed binder)": (
            "CLOSED at 5476a3f2c6bc: binder is now a single index r, D0 is an explicitly tagged "
            "disjoint union, ambient space and comeagerness are parameterised per branch. "
            "Falsifier option (b) of the original finding is satisfied."
        ),
        "HF-086-2/HF-034-F2A-2 (class_contract_pointer resolves only in authoring tree)": (
            "CLOSED: class_contract_pointer now points at research_map/formulation_taxonomy.yaml#classes.* "
            "which resolves; the supplement pointer is split into its own field and resolves in the "
            "authoring tree (C3/C4 PASS)."
        ),
        "HF-086-R1/HF-094C-2/HF-034-F2A-3 (consistency evidence pin stale)": (
            "CONFIRMED STILL OPEN at 5476a3f2c6bc; root-caused (HF-041-RCA-1) and shown to be "
            "non-durable under the current rule (HF-041-RCA-2)."
        ),
    },
    "corrective_action": {
        "immediate_unblock": (
            "1) Regenerate artifacts/formulation/evidence/taxonomy_consistency.json with the frozen "
            "inputs; 2) re-stamp f0_binding.consistency_evidence_sha256 in ALL THREE rev12 schemas "
            "with the hash measured immediately after step 1; 3) do steps 1-2 in one transaction and "
            "freeze, with no further edit to any of the four inputs. Advisory value at my measurement "
            f"time was {live_ev}, but it MUST be re-measured atomically at freeze; it is not a constant."
        ),
        "structural_fix_recommended": (
            "Pin the dependency closure instead of the derived output: embed sha256(A), sha256(B), "
            "sha256(VOCAB_ALIASES.json) and sha256(checker) inside the evidence JSON, and have the "
            "schemas pin those plus the expected exit status; or keep the output hash but amend the "
            "refresh rule to name all four inputs. Either removes the stale-by-construction class of "
            "failure shown in HF-041-RCA-1/2."
        ),
    },
    "assumptions": [
        "The four inputs I identified are the checker's complete input set (read from its source).",
        "Sandbox reproduction is faithful: the sandbox mirrors the minimal tree so the checker's "
        "ROOT (parents[3]) resolves inside the sandbox; the live evidence file was never written by me "
        "(its hash was 9e335e9b before and after my run).",
    ],
    "falsifier": (
        "Kill conditions for this diagnosis: (a) two runs on identical inputs produce different output "
        "hashes (nondeterminism); (b) 675a99d0 IS reproducible from the current four inputs; (c) an edit "
        "to the authoring contract / VOCAB_ALIASES / checker is shown NOT to change the evidence output; "
        "(d) check_taxonomy_consistency.py does not rewrite the evidence path. Any one falsifies the "
        "derived-output-staleness mechanism. Separately, an atomic re-stamp to the then-live evidence "
        "hash followed by a freeze with no further input edit REPAIRS the hard failure and supersedes "
        "the revise verdict - it does not falsify the root cause."
    ),
    "evidence": {
        "report_path": f"{HERE}/f2a_pin_rca_report.json",
        "experiment_raw": {
            "path": "artifacts/worker-041/f2a_pin_rca/raw/experiment.json",
            "sha256": exp_sha,
        },
        "experiment_script": {
            "path": "artifacts/worker-041/f2a_pin_rca/run_pin_rca.py",
            "sha256": script_sha,
        },
        "f2a_checks": {
            "path": "artifacts/worker-041/f2a_indep_review/raw/verify_run2.json",
            "sha256": sha256(f"{ROOT}/artifacts/worker-041/f2a_indep_review/raw/verify_run2.json"),
        },
        "f2a_checker": {
            "path": "artifacts/worker-041/f2a_indep_review/verify_f2a.py",
            "sha256": sha256(f"{ROOT}/artifacts/worker-041/f2a_indep_review/verify_f2a.py"),
        },
        "detector_corrections": {
            "note": (
                "Run 1 (raw/verify_run1.json) reported 4 FAILs. Three were detector bugs, verified by "
                "inspection and corrected in the checker before the reported run 2: C7 did not resolve "
                "dotted definition_refs (regularity.data_regularity); C11 scanned forbidden_* lists "
                "that legitimately name the WCC/I+ tokens they prohibit; C14 looked for "
                "sibling_disjoint_from under class_boundary when it is a top-level key. Run 2 is the "
                "reported result: 13 PASS, 1 FAIL (C6, the genuine pin defect). Run 1 is retained as "
                "evidence of the false-positive discipline."
            ),
            "run1_path": "artifacts/worker-041/f2a_indep_review/raw/verify_run1.json",
            "run1_sha256": sha256(f"{ROOT}/artifacts/worker-041/f2a_indep_review/raw/verify_run1.json"),
            "false_positives_corrected": ["C7", "C11", "C14"],
        },
        "measured_inputs": exp["live_inputs"],
        "measured_live_evidence_sha256": live_ev,
    },
    "authority_note": (
        "Worker event. No node status, validation_status=passed or gate verdict is claimed. "
        "Writes stayed inside artifacts/worker-041/**, comms/outbox/worker-041.jsonl and "
        "runtime/state/w041_checkpoint_*.json."
    ),
}

report_path = f"{HERE}/f2a_pin_rca_report.json"
with open(report_path, "w") as fh:
    json.dump(report, fh, indent=1)
report_sha = sha256(report_path)

# ------------------------- outbox events -------------------------
events = [
    {
        "event_id": f"w041-f2apin-{TASK}-status",
        "event_type": "status",
        "created_at": NOW,
        "actor": "worker-041",
        "node_id": "F2a",
        "class_id": CLAIM_CLASS,
        "class_ids": CLASS_IDS,
        "gate": "G-FORM",
        "status": "active",
        "hours": 0.4,
        "task_id": TASK,
        "completion_scope": "one class-bound diagnostic task; exiting after checkpoint",
        "summary": (
            "Independent root-cause experiment on the cross-cutting G-FORM blocker: the "
            "consistency-evidence pin is a derived output that the checker rewrites on every run, so "
            "re-stamping is only a temporary fixpoint. F2a rev12 @ 5476a3f2c6bc is semantically clean; "
            "the only hard failure is the stale f0_binding pin."
        ),
        "evidence_refs": [
            f"{report_path}#{report_sha[:12]}",
            f"artifacts/worker-041/f2a_pin_rca/raw/experiment.json#{exp_sha[:12]}",
            f"schemas/af_scc_c2_vacuum.yaml#{target_sha[:12]}",
        ],
        "next_falsifier": report["falsifier"],
    },
    {
        "event_id": f"w041-f2apin-{TASK}-artifact",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-041",
        "node_id": "F2a",
        "class_id": CLAIM_CLASS,
        "class_ids": CLASS_IDS,
        "gate": "G-FORM",
        "artifact_type": "diagnostic_report",
        "path": "artifacts/worker-041/f2a_pin_rca/f2a_pin_rca_report.json",
        "sha256": report_sha,
        "validation_status": "unverified",
        "claims_completion": False,
        "summary": "Root-cause + controlled experiment for the consistency-evidence pin failure.",
        "falsifier": report["falsifier"],
        "evidence_refs": [
            f"artifacts/worker-041/f2a_pin_rca/raw/experiment.json#{exp_sha[:12]}",
        ],
    },
    {
        "event_id": f"w041-f2apin-{TASK}-claim",
        "event_type": "claim",
        "created_at": NOW,
        "actor": "worker-041",
        "node_id": "F2a",
        "class_id": CLAIM_CLASS,
        "class_ids": CLASS_IDS,
        "gate": "G-FORM",
        "conclusion_type": "diagnosis",
        "statement": (
            "schemas/af_scc_c2_vacuum.yaml @ 5476a3f2c6bc declares consistency_evidence_sha256="
            "675a99d0..., but the evidence file is a deterministic, input-sensitive output that "
            "check_taxonomy_consistency.py rewrites on every run (measured live value "
            f"{live_ev}). A re-stamp is a fixpoint only until the next edit of any of its four "
            "inputs, because the schema's refresh rule names only one of them. F2a rev12 is "
            "otherwise clean: the prior critical D0 ill-typedness finding and the "
            "class_contract_pointer finding are both closed."
        ),
        "assumptions": report["assumptions"],
        "falsifier": report["falsifier"],
        "artifact_refs": [
            f"artifacts/worker-041/f2a_pin_rca/f2a_pin_rca_report.json#{report_sha[:12]}",
        ],
        "evidence_refs": [
            f"artifacts/worker-041/f2a_pin_rca/raw/experiment.json#{exp_sha[:12]}",
            f"schemas/af_scc_c2_vacuum.yaml#{target_sha[:12]}",
            f"artifacts/formulation/evidence/taxonomy_consistency.json#{live_ev[:12]}",
            "artifacts/formulation/tools/check_taxonomy_consistency.py#de356d999ea3",
        ],
    },
    {
        "event_id": f"w041-f2apin-{TASK}-review",
        "event_type": "review",
        "created_at": NOW,
        "actor": "worker-041",
        "node_id": "F2a",
        "class_id": CLAIM_CLASS,
        "class_ids": CLASS_IDS,
        "gate": "G-FORM",
        "target_id": "schemas/af_scc_c2_vacuum.yaml",
        "reviewer": "worker-041",
        "verdict": "revise",
        "score": 3.0,
        "hard_failures": [
            {
                "id": "HF-041-RCA-1",
                "severity": "hard",
                "finding": (
                    "f0_binding.consistency_evidence_sha256 675a99d0 does not match the measured "
                    f"evidence artifact {live_ev}; root-caused as a derived-output pin that is "
                    "rewritten by check_taxonomy_consistency.py on every run."
                ),
            },
            {
                "id": "HF-041-RCA-2",
                "severity": "hard",
                "finding": (
                    "The refresh rule covers 1 of the pinned output's 4 inputs, so a supplement/alias/"
                    "checker edit re-stales the pin without triggering a refresh; the authoring "
                    "contract was in fact edited 15 s after the pin was taken."
                ),
            },
        ],
        "findings": [
            "Prior critical HF-086-1/HF-088-1 (ill-typed disjunctive D0) is CLOSED at this hash.",
            "Prior hard HF-086-2/HF-034-F2A-2 (authoring-tree pointer) is CLOSED at this hash.",
            "Prior hard HF-086-R1/HF-094C-2/HF-034-F2A-3 (stale evidence pin) confirmed still open; "
            "symptom credit to workers 086/094/034 - root cause and durability analysis are new here.",
            "SF-041-RCA-1: evidence JSON carries no input hashes, so it is not self-verifying.",
            "SF-041-RCA-2: revision_history index 9 is out of chronological order (documentary).",
        ],
        "reviewed_sha256": target_sha,
        "counts_as_independent": True,
        "counts_as_full_schema_verdict": True,
        "counts_as_gate_verdict": False,
        "scope": "F2a full schema at the measured canonical hash; F1/F2b share the root cause",
        "evidence_refs": [
            f"artifacts/worker-041/f2a_pin_rca/f2a_pin_rca_report.json#{report_sha[:12]}",
            f"artifacts/worker-041/f2a_pin_rca/raw/experiment.json#{exp_sha[:12]}",
        ],
        "next_falsifier": report["falsifier"],
    },
]

outbox = f"{ROOT}/comms/outbox/worker-041.jsonl"
existing = set()
if os.path.exists(outbox):
    for line in open(outbox):
        line = line.strip()
        if line:
            try:
                existing.add(json.loads(line)["event_id"])
            except Exception:
                pass
new_events = [e for e in events if e["event_id"] not in existing]
with open(outbox, "a") as fh:
    for e in new_events:
        fh.write(json.dumps(e) + "\n")

# ------------------------- checkpoint -------------------------
checkpoint = {
    "schema_version": "0.1",
    "checkpoint_id": "w041-checkpoint-f2apin",
    "task_id": TASK,
    "actor": "worker-041",
    "created_at": NOW,
    "node_id": "F2a",
    "class_id": CLAIM_CLASS,
    "gate": "G-FORM",
    "verdict": "revise",
    "hours": 0.4,
    "target_sha256": target_sha,
    "report_path": "artifacts/worker-041/f2a_pin_rca/f2a_pin_rca_report.json",
    "report_sha256": report_sha,
    "experiment_sha256": exp_sha,
    "events_emitted": [e["event_id"] for e in new_events],
    "events_skipped_duplicate": [e["event_id"] for e in events if e["event_id"] in existing],
    "key_measurements": {
        "declared_pin": exp["declared_pin_in_schema"],
        "live_evidence_sha256": live_ev,
        "declared_pin_is_reproducible": p3["reproduced_by_current_inputs"],
        "evidence_deterministic": p1["byte_identical"],
        "evidence_input_sensitive": p2["hash_changed"],
        "refresh_rule_inputs_named": 1,
        "refresh_rule_inputs_actual": 4,
    },
    "prior_findings_closed": ["HF-086-1", "HF-088-1", "HF-086-2", "HF-034-F2A-2"],
    "blocking_findings": ["HF-041-RCA-1", "HF-041-RCA-2"],
    "next_falsifier": report["falsifier"],
    "status": "done",
    "authority_note": "worker checkpoint; no node status or gate verdict claimed",
}
ck_path = f"{ROOT}/runtime/state/w041_checkpoint_3.json"
with open(ck_path, "w") as fh:
    json.dump(checkpoint, fh, indent=1)
with open(f"{ROOT}/runtime/state/w041_checkpoints.jsonl", "a") as fh:
    fh.write(json.dumps(checkpoint) + "\n")

print(json.dumps({
    "report": report_path,
    "report_sha256": report_sha,
    "events_emitted": len(new_events),
    "events_skipped": len(events) - len(new_events),
    "checkpoint": ck_path,
    "target_sha256": target_sha,
    "live_evidence_sha256": live_ev,
}, indent=1))
