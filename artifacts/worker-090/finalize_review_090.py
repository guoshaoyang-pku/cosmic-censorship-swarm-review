#!/usr/bin/env python3
"""Emit worker-090's independent F1 review bundle from the measured evidence record.

Inputs (all measured by artifacts/worker-090/review_f1_independent.py):
    artifacts/worker-090/evidence.json

Outputs:
    reviews/F1-review-090.json                 review verdict artifact (primary)
    comms/outbox/worker-090.jsonl              upward events (artifact x2, review, status)
    runtime/state/w090_checkpoint_1.json       worker checkpoint

Refuses to write if F1's measured sha256 no longer matches the reviewed hash
(freeze rule: a verdict binds only to frozen bytes).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "schemas/af_wcc_vacuum.yaml"
EVIDENCE = ROOT / "artifacts/worker-090/evidence.json"
REVIEW = ROOT / "reviews/F1-review-090.json"
SCRIPT = ROOT / "artifacts/worker-090/review_f1_independent.py"
OUTBOX = ROOT / "comms/outbox/worker-090.jsonl"
CHECKPOINT = ROOT / "runtime/state/w090_checkpoint_1.json"
CST = timezone(timedelta(hours=8))


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def ref(p: Path) -> str:
    return f"{p.relative_to(ROOT)}#{sha256(p)[:12]}"


def main() -> int:
    ev = json.loads(EVIDENCE.read_text())
    reviewed = ev["target"]["sha256"]
    measured_pre = sha256(TARGET)
    if measured_pre != reviewed:
        print(json.dumps({"error": "target moved since review checks",
                          "reviewed": reviewed, "measured": measured_pre}))
        return 3

    ts = datetime.now(CST).strftime("%Y%m%dT%H%M%S")
    f0_measured = sha256(ROOT / "research_map/formulation_taxonomy.yaml")

    hard_failures = [
        {
            "id": "HF090-01",
            "name": "contract_pointer_not_canonical",
            "severity": "major",
            "closest_taxonomy": "none (evidence/binding hygiene; recommend HF-15 evidence_binding_drift)",
            "detail": ("class_contract_pointer = artifacts/formulation/formulation_taxonomy.yaml"
                       "#class_contracts.AF-WCC-VAC-GEN targets the authoring tree; the fragment "
                       "does not resolve in the canonical taxonomy (top-level key is 'classes', not "
                       "'class_contracts'), while f0_binding.declared_f0_artifact names the canonical "
                       "path. Two inconsistent contract references in one artifact; under the "
                       "controller canonical-path policy (ASTRA_HANDOFF 2026-09-12) the pointer is "
                       "unresolved against the authoritative tree."),
            "measured": {"pointer_resolves_in_canonical": "unresolved",
                         "pointer_resolves_in_authoring": "resolved"},
        },
        {
            "id": "HF090-02",
            "name": "parser_dependent_future_dated_timestamp",
            "severity": "major",
            "closest_taxonomy": "none (provenance/clock discipline, CF-6 family)",
            "detail": ("Duplicate top-level YAML keys: revised_at x7 and revised_at_unused x2. "
                       "PyYAML last-wins makes the effective revised_at '2026-09-12T00:30:00+08:00', "
                       f"which is future-dated relative to the file mtime {ev['target']['mtime']} and "
                       "to review wall clock; revised_at_unused is meaningless in a canonical "
                       "artifact. The rev10 "
                       "comment also cites F0 hash 565a6e50 while the field carries 276009f4 "
                       "(comment/field drift). During this worker slot the bytes also moved "
                       "16128b62 -> 9a8bd4c9 while the revision field stayed 11, so a "
                       "revision-number-keyed verdict cannot distinguish those byte states."),
            "measured": {"duplicate_revised_at": 7, "duplicate_revised_at_unused": 2,
                         "effective_last_wins": "2026-09-12T00:30:00+08:00",
                         "target_mtime": ev["target"]["mtime"]},
        },
        {
            "id": "HF090-03",
            "name": "undefined_normative_symbol",
            "severity": "major",
            "closest_taxonomy": "schema_falsifiers[0] (imprecision: two competent readers diverge)",
            "detail": ("conclusion.statement_formal uses the predicate AF_{I+}(M_D); no definition of "
                       "AF_{I+} exists in the schema, in the canonical F0 taxonomy, or in the "
                       "authoring F0 taxonomy. quantifiers.formal spells out the intended condition, "
                       "so the reading is recoverable, but the normative formal statement is not "
                       "self-contained."),
            "measured": {"occurrences_in_target": 1, "explicit_definitions": 0},
        },
    ]
    findings = [
        {"id": "F090-01", "kind": "positive", "text":
            "All required sections present (quantifiers, topology, data_class, regularity, genericity, "
            "i_plus, visibility, conclusion, falsifier, anti_scope, class_components); conclusion_type "
            "= weak_cosmic_censorship; class_components = AF/WCC/VAC/GEN, regularity_token none."},
        {"id": "F090-02", "kind": "positive", "text":
            f"f0_binding.declared_f0_sha256 == measured canonical F0 hash at review time "
            f"({f0_measured[:12]}); rev11 fixed the earlier stale 66bf917b binding. The declared F0 "
            "artifact is itself churning (0fcc6a19 -> 276009f4 -> current within minutes), so this "
            "match is instant-bound, not freeze-stable."},
        {"id": "F090-03", "kind": "positive", "text":
            "Class separation is clean at this revision: class_separation.findings_for_text returns "
            "0 findings (the earlier CLASSSEP-SOFT unknown token AF-WCC-VAC-GEN-SET was cleared in "
            "rev11 by normalizing the variant delta filename). SET reading remains a registered "
            "variant pointer (is_this_class false), not a class and not a merge."},
        {"id": "F090-04", "kind": "defect", "text":
            "schemas/f1_falsifier_tests.jsonl (24 rows, 17 with citation_status unresolved) is bound "
            "to binding_sha256 b65fcc0f0118 (previous revision), not to the reviewed revision; it "
            "cannot be cited as falsifier-exercise evidence for these bytes until re-bound."},
        {"id": "F090-05", "kind": "defect", "text":
            "artifacts/formulation/evidence/taxonomy_consistency.json reports consistent=true but "
            "contains no sha256 of either compared tree, so the consistency evidence cited by "
            "f0_binding cannot be pinned to the declared/measured F0 revision pair."},
        {"id": "F090-06", "kind": "context", "text":
            "schemas/semantic_contract_tests/observed_verdicts.json validity.valid_for_calibration=false "
            "with blocking adjudication ADJ-CONTROL-STALENESS; the semantic-contract stage is not yet "
            "usable as gate calibration evidence (not an F1-specific defect). Re-checked at review "
            "time; controller to re-verify before use."},
    ]
    next_falsifier = (
        "Re-measure schemas/af_wcc_vacuum.yaml and research_map/formulation_taxonomy.yaml after the "
        "author's fixes: (1) repoint class_contract_pointer to "
        "research_map/formulation_taxonomy.yaml#classes.AF-WCC-VAC-GEN and re-run the consistency "
        "check with measured sha256s of both trees; (2) collapse duplicate revised_at/revised_at_unused "
        "keys to a single non-future timestamp and align the rev comment with the binding field; "
        "(3) define AF_{I+} in the schema or inline the predicate in statement_formal. If any of the "
        "three survives at the next frozen hash, the revision must not be accepted for G-FORM."
    )

    review = {
        "review_id": "RV-090-F1-001",
        "reviewer": "worker-090",
        "reviewer_role": "bounded execution worker (independent; not an author of F1)",
        "target_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "artifact_path": "schemas/af_wcc_vacuum.yaml",
        "reviewed_sha256": reviewed,
        "reviewed_revision": 11,
        "target_mtime": ev["target"]["mtime"],
        "verdict": "revise",
        "score": 3.5,
        "hard_failures": hard_failures,
        "findings": findings,
        "evidence_refs": [
            f"schemas/af_wcc_vacuum.yaml#{reviewed[:12]}",
            f"research_map/formulation_taxonomy.yaml#{f0_measured[:12]}",
            ref(EVIDENCE),
        ],
        "artifact_refs": ["reviews/F1-review-090.json", "artifacts/worker-090/evidence.json"],
        "method": ("Mechanical, reproducible inspection of the frozen bytes by an independent worker: "
                   "section/scalar presence, f0 binding declared-vs-measured hash comparison, pointer "
                   "fragment resolution in both F0 trees, top-level YAML duplicate-key scan with "
                   "last-wins semantics, effective-timestamp vs mtime/wall-clock check, symbol "
                   "definition scan, class_separation.findings_for_text, and falsifier-suite binding "
                   "check. No network, no seeds, no state mutation."),
        "reproduction": (
            "python3 artifacts/worker-090/review_f1_independent.py "
            f"--expect {reviewed} --out artifacts/worker-090/evidence.json"
        ),
        "next_falsifier": next_falsifier,
        "hash_stability": {
            "measured_at_review": reviewed,
            "f0_canonical_measured_at_review": f0_measured,
            "re_measured_at_write": None,
            "stable": None,
            "note": "F1 moved three times during this worker slot (68392dd8 -> 16128b62 -> 9a8bd4c9, "
                    "the last without a revision-number bump); the freeze rule requires the hash to "
                    "be unchanged when the next verdict lands, so the controller must re-measure "
                    "before treating this verdict as binding.",
        },
        "authority_note": ("Worker verdict is advisory evidence only. Per ASTRA_HANDOFF, worker events "
                           "cannot set status=done, validation_status=passed, or a gate verdict; the "
                           "controller/leads decide with artifact + review evidence."),
        "created_at": now(),
    }
    measured_post = sha256(TARGET)
    review["hash_stability"]["re_measured_at_write"] = measured_post
    review["hash_stability"]["stable"] = measured_post == reviewed
    if measured_post != reviewed:
        review["verdict"] = "inconclusive"
        review["score"] = 0.0
        review["hash_stability"]["action"] = ("target moved between review and write; verdict "
                                              "downgraded to inconclusive; re-review required")
    REVIEW.parent.mkdir(parents=True, exist_ok=True)
    REVIEW.write_text(json.dumps(review, indent=2, sort_keys=True) + "\n")

    review_sha = sha256(REVIEW)
    evidence_sha = sha256(EVIDENCE)
    script_sha = sha256(SCRIPT)

    def event(event_id, **kw):
        base = {"event_id": event_id, "created_at": now(), "actor": "worker-090"}
        base.update(kw)
        return base

    events = [
        event(f"w090-{ts}-artifact-review", event_type="artifact", node_id="F1", class_id="AF-WCC-VAC-GEN",
              artifact_type="review", path="reviews/F1-review-090.json", sha256=review_sha,
              validation_status="unverified",
              evidence_refs=[f"schemas/af_wcc_vacuum.yaml#{reviewed[:12]}", ref(EVIDENCE)]),
        event(f"w090-{ts}-artifact-evidence", event_type="artifact", node_id="F1", class_id="AF-WCC-VAC-GEN",
              artifact_type="evidence", path="artifacts/worker-090/evidence.json",
              sha256=evidence_sha, validation_status="unverified",
              evidence_refs=[f"schemas/af_wcc_vacuum.yaml#{reviewed[:12]}",
                             f"artifacts/worker-090/review_f1_independent.py#{script_sha[:12]}"]),
        event(f"w090-{ts}-review", event_type="review", target_id="F1", class_id="AF-WCC-VAC-GEN",
              reviewer="worker-090", verdict=review["verdict"], score=review["score"],
              hard_failures=[h["id"] + ":" + h["name"] for h in hard_failures],
              findings=[f["text"] for f in findings],
              reviewed_sha256=reviewed, reviewed_revision=11,
              artifact_refs=["reviews/F1-review-090.json", "artifacts/worker-090/evidence.json"],
              evidence_refs=[f"schemas/af_wcc_vacuum.yaml#{reviewed[:12]}",
                             f"research_map/formulation_taxonomy.yaml#{f0_measured[:12]}",
                             ref(EVIDENCE)],
              next_falsifier=next_falsifier,
              authority_note="advisory worker verdict; cannot set gate verdict or node status"),
        event(f"w090-{ts}-status", event_type="status", node_id="F1", class_id="AF-WCC-VAC-GEN",
              status="active", hours=0.4,
              summary=(f"Independent full-schema review of F1 AF-WCC-VAC-GEN at revision 11: verdict "
                       f"{review['verdict']} ({review['score']}). Three major binding/provenance/"
                       "precision defects (HF090-01..03), three further findings; zero "
                       "class-separation findings; falsifier suite and F0 consistency evidence need "
                       "re-binding. No gate or status promotion claimed."),
              evidence_refs=[f"schemas/af_wcc_vacuum.yaml#{reviewed[:12]}", ref(EVIDENCE),
                             ref(REVIEW)],
              next_falsifier=next_falsifier),
    ]
    with OUTBOX.open("w") as f:
        for e in events:
            f.write(json.dumps(e, sort_keys=True) + "\n")

    checkpoint = {
        "checkpoint_id": f"w090-cp1-{ts}",
        "worker": "worker-090",
        "slot": "090",
        "created_at": now(),
        "task": ("one class-bound task: independent full-schema review of F1 AF-WCC-VAC-GEN "
                 "(schemas/af_wcc_vacuum.yaml) at its frozen measured hash"),
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "verdict": review["verdict"],
        "score": review["score"],
        "artifacts": {
            "reviews/F1-review-090.json": sha256(REVIEW),
            "artifacts/worker-090/evidence.json": evidence_sha,
            "artifacts/worker-090/review_f1_independent.py": script_sha,
        },
        "hash_start": reviewed,
        "hash_end": measured_post,
        "hash_stable": measured_post == reviewed,
        "f0_canonical_sha256": f0_measured,
        "events_emitted": [e["event_id"] for e in events],
        "outbox": "comms/outbox/worker-090.jsonl",
        "evidence_refs": [f"schemas/af_wcc_vacuum.yaml#{reviewed[:12]}",
                          f"research_map/formulation_taxonomy.yaml#{f0_measured[:12]}",
                          ref(REVIEW), ref(EVIDENCE)],
        "next_falsifier": next_falsifier,
        "authority": ("worker checkpoint; no status=done, no validation_status=passed, no gate "
                      "verdict; controller ingests outbox and decides"),
        "session_note": ("prior worker-090 instance (00:12:31) was killed before writing artifacts; "
                         "this instance completed the task at 00:1x with fresh measurements. F1 moved "
                         "68392dd8 -> 16128b62 during the slot."),
    }
    CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT.write_text(json.dumps(checkpoint, indent=2, sort_keys=True) + "\n")

    print(json.dumps({
        "review": str(REVIEW.relative_to(ROOT)), "review_sha256": sha256(REVIEW),
        "outbox": str(OUTBOX.relative_to(ROOT)), "events": len(events),
        "checkpoint": str(CHECKPOINT.relative_to(ROOT)),
        "reviewed_sha256": reviewed, "hash_end": measured_post,
        "stable": measured_post == reviewed, "verdict": review["verdict"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
