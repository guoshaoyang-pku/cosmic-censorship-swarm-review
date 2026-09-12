#!/usr/bin/env python3
"""Emit worker-001's bounded-lifecycle outputs from the frozen review.json.

Writes (all paths relative to the swarm root):
  reviews/F2b-review-worker-001.json                       binding verdict record
  artifacts/worker-001/f2b_review/PIN_MANIFEST.json        measurement chain
  artifacts/worker-001/f2b_review/README.md                reproduce instructions
  comms/outbox/worker-001.jsonl                            artifact/review/claim/status events
  runtime/state/worker-001_checkpoint_1.json               worker checkpoint

Validation: every emitted line is re-parsed, and every hash written into an event is
re-measured from disk before the file is written. Exits non-zero on any mismatch.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))
ROOT = "/data3/guoshaoyang/workdir/ai4math-swarm"
ART = "artifacts/worker-001/f2b_review"
REVIEW = f"{ART}/review.json"
HARNESS = f"{ART}/run_review.py"
OUTBOX = "comms/outbox/worker-001.jsonl"
CHECKPOINT = "runtime/state/worker-001_checkpoint_1.json"
VERDICT_COPY = "reviews/F2b-review-worker-001.json"
PIN_MANIFEST = f"{ART}/PIN_MANIFEST.json"


def sha(p):
    with open(os.path.join(ROOT, p), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def now():
    return datetime.now(CST).isoformat(timespec="seconds")


def main():
    review = json.load(open(os.path.join(ROOT, REVIEW)))
    assert review["verdict"] == "accept", review["verdict"]
    measured_at = now()
    stamp = measured_at.replace(":", "").replace("-", "")
    reviewed_sha = review["reviewed_sha256"]
    harness_sha = sha(HARNESS)
    review_sha = sha(REVIEW)

    # A verdict on superseded bytes must not be emitted as if it were current.
    live_sha = sha("schemas/af_scc_c0_vacuum.yaml")
    live_f0 = sha("research_map/formulation_taxonomy.yaml")
    if live_sha != reviewed_sha:
        raise SystemExit(
            f"refusing to emit: live F2b {live_sha[:16]} != reviewed {reviewed_sha[:16]}"
        )

    findings_compact = [
        {
            "id": f["id"],
            "severity": f["severity"],
            "kind": f["kind"],
            "finding": f["finding"],
            "deciding_field": f.get("deciding_field"),
            "falsifier": f.get("falsifier"),
        }
        for f in review["findings"]
    ]

    events = [
        {
            "event_id": f"w001-artifact-f2b-harness-{stamp}",
            "event_type": "artifact",
            "created_at": measured_at,
            "actor": "worker-001",
            "node_id": "F2b",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "gate": "G-FORM",
            "artifact_type": "review_harness",
            "path": HARNESS,
            "sha256": harness_sha,
            "validation_status": "unverified",
            "evidence_refs": [f"{HARNESS}#sha256:{harness_sha[:16]}"],
            "summary": (
                "Independent fail-closed structural review harness for F2b (checks H1-H12 from the "
                "assignment acceptance + A0 verifiers.schema_formulation). Exits 3 without a verdict "
                "if the live canonical hash differs from --expect."
            ),
            "falsifier": "A run of the harness at a different --expect that still emits a verdict, or an independent reimplementation that disagrees on any H-check.",
        },
        {
            "event_id": f"w001-artifact-f2b-review-{stamp}",
            "event_type": "artifact",
            "created_at": measured_at,
            "actor": "worker-001",
            "node_id": "F2b",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "gate": "G-FORM",
            "artifact_type": "independent_review",
            "path": REVIEW,
            "sha256": review_sha,
            "validation_status": "unverified",
            "evidence_refs": [
                f"{REVIEW}#sha256:{review_sha[:16]}",
                f"schemas/af_scc_c0_vacuum.yaml#sha256:{reviewed_sha}",
                f"research_map/formulation_taxonomy.yaml#sha256:{live_f0}",
            ],
            "summary": (
                f"Full-schema hash-pinned review of F2b at {reviewed_sha[:16]}: verdict "
                f"{review['verdict']} score {review['score']}, 0 hard failures, 12/12 checks pass, "
                f"conditions {review['conditions']}, findings {[f['id'] for f in review['findings']]}."
            ),
            "falsifier": review["falsifier"],
        },
        {
            "event_id": f"w001-review-f2b-{stamp}",
            "event_type": "review",
            "created_at": measured_at,
            "actor": "worker-001",
            "node_id": "F2b",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "gate": "G-FORM",
            "target_id": f"schemas/af_scc_c0_vacuum.yaml#{reviewed_sha}",
            "reviewed_path": "schemas/af_scc_c0_vacuum.yaml",
            "reviewed_sha256": reviewed_sha,
            "reviewer": "worker-001",
            "independent": True,
            "verdict": review["verdict"],
            "score": review["score"],
            "hard_failures": review["hard_failures"],
            "findings": findings_compact,
            "artifact_refs": [
                f"{REVIEW}#sha256:{review_sha[:16]}",
                f"{HARNESS}#sha256:{harness_sha[:16]}",
            ],
            "evidence_refs": [
                f"schemas/af_scc_c0_vacuum.yaml#sha256:{reviewed_sha}",
                f"research_map/formulation_taxonomy.yaml#sha256:{live_f0}",
                "artifacts/formulation/VARIANT_REGISTRY.json",
                "evaluation_rubric.yaml#verifiers.schema_formulation",
            ],
            "scope_note": review["scope_note"],
            "falsifier": review["falsifier"],
            "reproduce": review["reproduce"],
        },
        {
            "event_id": f"w001-claim-f2b-variantregistry-{stamp}",
            "event_type": "claim",
            "created_at": measured_at,
            "actor": "worker-001",
            "node_id": "F2b",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "gate": "G-FORM",
            "conclusion_type": "observation",
            "statement": (
                f"At F2b sha256 {reviewed_sha[:16]} the canonical F0 taxonomy registers 2 variants "
                "inline (AF-WCC-VAC-GEN SET, AF-SCC-C0-VAC-GEN CH) while "
                "artifacts/formulation/VARIANT_REGISTRY.json v2.0 registers 7; the schema's anti_scope "
                "cites variant_id H2LOC and DISTRIBUTIONAL, which are absent from the canonical inline "
                "registry. The declared consistency evidence (495-byte verdict object) does not compare "
                "variant registries."
            ),
            "assumptions": [
                "canonical path policy: research_map/formulation_taxonomy.yaml is authoritative",
                "VARIANT_REGISTRY.json is the registry the schema names, not a canonical artifact",
                "the observation is about registry consistency, not about the truth of any variant",
            ],
            "artifact_refs": [f"{REVIEW}#sha256:{review_sha[:16]}"],
            "evidence_refs": [
                f"research_map/formulation_taxonomy.yaml#sha256:{live_f0}",
                "artifacts/formulation/VARIANT_REGISTRY.json#version:2.0",
                f"schemas/af_scc_c0_vacuum.yaml#sha256:{reviewed_sha}",
            ],
            "falsifier": (
                "Canonical F0 is shown to contain H2LOC and DISTRIBUTIONAL for AF-SCC-C0-VAC-GEN, or "
                "an independent per-field consistency run reproduces the 7-variant registry from "
                "canonical F0 alone."
            ),
        },
        {
            "event_id": f"w001-status-f2b-review-{stamp}",
            "event_type": "status",
            "created_at": measured_at,
            "actor": "worker-001",
            "node_id": "F2b",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "gate": "G-FORM",
            "status": "done",
            "hours": 0.7,
            "summary": (
                f"One bounded class-bound task complete: independent full-schema review of F2b at "
                f"{reviewed_sha[:16]} (accept 4.0, 0 hard failures, conditions W001-F1/F2/F3). "
                f"Artifacts {REVIEW} sha256:{review_sha[:16]} and {HARNESS} sha256:{harness_sha[:16]}; "
                "checkpoint runtime/state/worker-001_checkpoint_1.json. No node done, gate verdict or "
                "theorem is claimed."
            ),
            "evidence_refs": [
                f"{REVIEW}#sha256:{review_sha[:16]}",
                f"schemas/af_scc_c0_vacuum.yaml#sha256:{reviewed_sha}",
                f"{CHECKPOINT}",
            ],
            "next_falsifier": review["falsifier"],
            "completion_scope": (
                "worker lifecycle only; this is a completion claim for one review task, not a node "
                "done and not a gate verdict (per PROTOCOL rule 2 and the worker authority limit)."
            ),
        },
    ]

    # ---- validate every reference before writing --------------------------------
    for ev in events:
        assert ev["event_id"] and ev["event_type"] and ev["created_at"] and ev["actor"]
        json.dumps(ev)  # must be serializable
    for p, expected in ((HARNESS, harness_sha), (REVIEW, review_sha),
                        ("schemas/af_scc_c0_vacuum.yaml", reviewed_sha)):
        assert sha(p) == expected, p

    os.makedirs(os.path.join(ROOT, os.path.dirname(OUTBOX)), exist_ok=True)
    with open(os.path.join(ROOT, OUTBOX), "w") as fh:
        for ev in events:
            fh.write(json.dumps(ev) + "\n")

    with open(os.path.join(ROOT, VERDICT_COPY), "w") as fh:
        json.dump(review, fh, indent=1)
        fh.write("\n")

    manifest = {
        "manifest_id": f"w001-pin-manifest-{stamp}",
        "at": measured_at,
        "actor": "worker-001",
        "reviewed_artifact": {
            "path": "schemas/af_scc_c0_vacuum.yaml",
            "sha256": reviewed_sha,
            "bytes": os.path.getsize(os.path.join(ROOT, "schemas/af_scc_c0_vacuum.yaml")),
        },
        "pinned_copies": {
            p: sha(p)
            for p in (
                f"{ART}/pinned/schemas_af_scc_c0_vacuum.yaml",
                f"{ART}/pinned/schemas_af_scc_c2_vacuum.yaml",
                f"{ART}/pinned/schemas_af_wcc_vacuum.yaml",
                f"{ART}/pinned/research_map_formulation_taxonomy.yaml",
                f"{ART}/pinned/artifacts_formulation_formulation_taxonomy.yaml",
                f"{ART}/pinned/history/schemas_af_scc_c0_vacuum.a2aef5ac.yaml",
            )
            if os.path.exists(os.path.join(ROOT, p))
        },
        "observed_chain": {
            "F2b_class_schema": [
                "a8d899d2941fa5b6 (read 00:13-00:15; superseded)",
                "a2aef5ac7fe377a8 (pinned 00:16:22; superseded)",
                "962f33c6d0473572 (measured 00:18; superseded, H11 drift observed)",
                "1bb78ce9b3572cda (reviewed; H1-H12 all pass)",
            ],
            "F0_taxonomy": [
                "565a6e505188d6c2 (map measurement 00:11; superseded)",
                "0fcc6a1928fd40b0 (pinned 00:15:42; superseded)",
                "276009f4f63dbf83 (current at verdict; equals f0_binding declaration)",
            ],
        },
        "note": (
            "Two artifacts were rewritten while this review was in flight; the harness aborts without "
            "a verdict on hash drift, and the emitted verdict is bound to the reviewed sha. A later "
            "revision makes the verdict advisory, not wrong: re-run the harness."
        ),
    }
    with open(os.path.join(ROOT, PIN_MANIFEST), "w") as fh:
        json.dump(manifest, fh, indent=1)
        fh.write("\n")

    readme = (
        "# worker-001 F2b review\n\n"
        f"Target: `schemas/af_scc_c0_vacuum.yaml` (AF-SCC-C0-VAC-GEN, node F2b, gate G-FORM)\n"
        f"Verdict: **{review['verdict']}** score {review['score']} at sha256 `{reviewed_sha}`\n\n"
        "Reproduce (fail-closed: exits 3 without a verdict if the canonical bytes changed):\n\n"
        f"    python3 {HARNESS} --root . --expect {reviewed_sha} --out {REVIEW}\n\n"
        f"- Full verdict: `{REVIEW}` (copy: `{VERDICT_COPY}`)\n"
        f"- Measurement chain and pinned inputs: `{PIN_MANIFEST}`\n"
        "- Conditions: W001-F1 variant registry, W001-F2 conclusion-type vocabulary, W001-F3\n"
        "  non-reproducible consistency evidence. Minor: W001-F4 duplicate YAML keys, W001-F5\n"
        "  revised_at ahead of mtime. Info: W001-F6 disjunctive D0, W001-F7 binding current.\n"
    )
    with open(os.path.join(ROOT, f"{ART}/README.md"), "w") as fh:
        fh.write(readme)

    checkpoint = {
        "checkpoint_id": f"w001-ckpt-{stamp}",
        "at": measured_at,
        "actor": "worker-001",
        "role": "worker",
        "slot": "001",
        "lifecycle": "one bounded class-bound task, then exit",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "task": f"independent hash-pinned structural review of F2b at {reviewed_sha}",
        "artifacts": [
            {"path": HARNESS, "sha256": harness_sha},
            {"path": REVIEW, "sha256": review_sha},
            {"path": PIN_MANIFEST, "sha256": sha(PIN_MANIFEST)},
            {"path": VERDICT_COPY, "sha256": sha(VERDICT_COPY)},
            {"path": "schemas/af_scc_c0_vacuum.yaml", "sha256": reviewed_sha},
            {"path": "research_map/formulation_taxonomy.yaml", "sha256": live_f0},
        ],
        "events_emitted": [ev["event_id"] for ev in events],
        "verdict": review["verdict"],
        "score": review["score"],
        "hard_failures": review["hard_failures"],
        "conditions": review["conditions"],
        "findings": [f["id"] for f in review["findings"]],
        "cross_checks": review["cross_checks"],
        "not_claimed": [
            "node F2b done",
            "any gate verdict (G-FORM/G-AUDIT)",
            "any theorem or physical result",
            "physical fidelity of the formulation",
        ],
        "next_falsifier": review["falsifier"],
        "authority_note": (
            "Worker events cannot set status=done on a node, validation_status=passed, or a gate "
            "verdict; the status event's done refers to this worker lifecycle only."
        ),
    }
    with open(os.path.join(ROOT, CHECKPOINT), "w") as fh:
        json.dump(checkpoint, fh, indent=1)
        fh.write("\n")

    # final validation pass
    for line in open(os.path.join(ROOT, OUTBOX)):
        json.loads(line)
    json.load(open(os.path.join(ROOT, CHECKPOINT)))
    json.load(open(os.path.join(ROOT, PIN_MANIFEST)))
    print(json.dumps({
        "status": "emitted",
        "outbox": OUTBOX,
        "events": [ev["event_id"] for ev in events],
        "checkpoint": CHECKPOINT,
        "verdict_copy": VERDICT_COPY,
        "pin_manifest": PIN_MANIFEST,
        "reviewed_sha256": reviewed_sha,
        "harness_sha256": harness_sha,
        "review_sha256": review_sha,
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
