#!/usr/bin/env python3
"""Emit worker-035 outbox events + worker checkpoint for W035-F2A-REV12-INDEP-VERDICT-01.

Idempotent: events whose event_id already exists in comms/outbox/worker-035.jsonl are skipped.
Append-only; nothing canonical is written. Writes:
  runtime/state/w035_f2a_checkpoint_1.json
  comms/outbox/worker-035.jsonl  (append)
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
D = Path(__file__).resolve().parent
OUTBOX = ROOT / "comms/outbox/worker-035.jsonl"
CKPT = ROOT / "runtime/state/w035_f2a_checkpoint_1.json"
TZ = timezone(timedelta(hours=8))
STAMP = datetime.now(TZ).replace(microsecond=0)

TASK = "W035-F2A-REV12-INDEP-VERDICT-01"
NODE = "F2a"
CLASS = "AF-SCC-C2-VAC-GEN"
GATE = "G-FORM"
F2A_SHA = "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ref(p: Path) -> str:
    return f"{p.relative_to(ROOT)}#sha256:{sha(p)[:12]}"


report = D / "report.json"
controls = D / "controls.json"
checker = D / "check_f2a_rev12.py"
readme = D / "README.md"
snap = D / "snapshot/schemas__af_scc_c2_vacuum.yaml"
snapman = D / "snapshot/SNAPSHOT.sha256"
map_path = ROOT / "research_map/research_map.json"

artifacts = {
    "report": report,
    "controls": controls,
    "checker": checker,
    "readme": readme,
    "snapshot": snap,
    "snapshot_manifest": snapman,
}
hashes = {k: sha(v) for k, v in artifacts.items()}
map_sha = sha(map_path)
now = STAMP.isoformat()
if CKPT.exists():
    try:
        now = json.loads(CKPT.read_text())["created_at"]  # stable across re-runs
    except Exception:
        pass

checkpoint = {
    "checkpoint_id": "w035-f2a-ckpt-1",
    "worker": "worker-035",
    "task_id": TASK,
    "node_id": NODE,
    "class_id": CLASS,
    "class_ids": [CLASS],
    "gate": GATE,
    "created_at": now,
    "worker_level_status": "complete (bounded worker task); node status and gate verdicts unchanged",
    "authority": "worker evidence only; no gate verdict, no node status, no canonical-file edit; read-only except this artifact directory and runtime/state/w035_f2a_checkpoint_1.json",
    "verdict": "revise",
    "score": 3.5,
    "reviewed_artifact": "schemas/af_scc_c2_vacuum.yaml",
    "reviewed_sha256": F2A_SHA,
    "blocking_failed_subchecks": ["C08.4", "C08.5", "C12.3"],
    "hard_failures": ["HF-035-F2A-1", "HF-035-F2A-2", "HF-035-F2A-3"],
    "controls": {"pass": 11, "total": 11},
    "map_sha256_measured": map_sha,
    "artifacts": {k: {"path": str(v.relative_to(ROOT)), "sha256": hashes[k]} for k, v in artifacts.items()},
    "falsifier": [
        "any blocking subcheck that passes on a re-run at the pinned hashes",
        "a file at artifacts/formulation/evidence/taxonomy_consistency.json hashing to 675a99d0d25b2b37 at the reviewed revision",
        "a pinned ledger row for T-401/T-402/T-514/T-520 carrying citation_status=verified_by_L1 or review_status=independently_reviewed",
        "any pinned canonical input changing hash during the run",
    ],
    "non_claims": [
        "not a gate verdict; cannot pass G-FORM or move F2a/node status",
        "no canonical artifact edited",
        "verifies schema form, binding and class separation; not the physics statement",
    ],
}
CKPT.write_text(json.dumps(checkpoint, indent=2) + "\n")
ckpt_ref = f"runtime/state/w035_f2a_checkpoint_1.json#sha256:{sha(CKPT)[:12]}"

base = "w035-f2a-rev12"  # stable, task-derived: re-runs skip existing ids
ev = []


def add(kind, payload):
    e = {"event_id": f"{base}-{kind}", "event_type": payload.pop("event_type"),
         "created_at": now, "actor": "worker-035"}
    e.update(payload)
    ev.append(e)


common = {
    "node_id": NODE,
    "gate": GATE,
    "class_id": CLASS,
    "class_ids": [CLASS],
    "task_id": TASK,
}
non_claims = [
    "not a gate verdict; cannot pass G-FORM or move F2a/node status",
    "no canonical artifact edited; all writes under artifacts/worker-035/f2a_rev12_verdict/ and runtime/state/",
    "verifies schema form, binding and class separation; does not prove or refute the physics statement",
    "the verdict binds to F2a revision 12 / sha256 5476a3f2c6bc only",
]

add("status-open", {
    "event_type": "status", "status": "active", "hours": 0.5,
    "evidence_refs": [ref(map_path), f"runtime/state/controller_verification/lifecycle_20260912-004308.json#sha256:{sha(ROOT / 'runtime/state/controller_verification/lifecycle_20260912-004308.json')[:12]}"],
    "summary": ("No assignment card exists in comms/inbox/worker-035.jsonl for this slot. Took ONE class-bound "
                "task (W035-F2A-REV12-INDEP-VERDICT-01): independent full-schema review of F2a "
                "AF-SCC-C2-VAC-GEN at FROZEN rev28 pin 5476a3f2c6bc, where the pass-05 controller gate audit "
                "records 0 distinct accept reviewers and the pass-04 card astra-life04-verify-gform-r2 requires a "
                "second independent blind verdict. Own implementation; canonical artifacts read-only."),
    "next_falsifier": "Any blocking subcheck passing on a re-run at the pinned hashes; a canonical F2a re-freeze makes this verdict stale.",
    **common,
})

add("artifact-snapshot", {
    "event_type": "artifact", "validation_status": "unverified", "artifact_type": "f2a_rev12_snapshot",
    "path": str(snap.relative_to(ROOT)), "sha256": hashes["snapshot"],
    "evidence_refs": [ref(snap), ref(snapman)],
    "summary": f"Byte copy of the reviewed revision; canonical == mirror == FROZEN rev28 pin {F2A_SHA[:16]}.",
    **common,
})
add("artifact-checker", {
    "event_type": "artifact", "validation_status": "unverified", "artifact_type": "f2a_rev12_verifier_code",
    "path": str(checker.relative_to(ROOT)), "sha256": hashes["checker"],
    "evidence_refs": [ref(checker), ref(report)],
    "summary": "Own deterministic read-only harness: 14 check groups / 58 pre-registered subchecks + 10 mutants + null control; no other worker's checker imported.",
    **common,
})
add("artifact-report", {
    "event_type": "artifact", "validation_status": "unverified", "artifact_type": "f2a_rev12_verdict_report",
    "path": str(report.relative_to(ROOT)), "sha256": hashes["report"],
    "evidence_refs": [ref(report), ref(checker), ref(snap)],
    "summary": "Machine output: pins, per-subcheck status, 3 blocking hard failures (C08.4/C08.5/C12.3), 0 advisory, controls 11/11, drift false.",
    **common,
})
add("artifact-controls", {
    "event_type": "artifact", "validation_status": "unverified", "artifact_type": "f2a_rev12_controls",
    "path": str(controls.relative_to(ROOT)), "sha256": hashes["controls"],
    "evidence_refs": [ref(controls), ref(checker)],
    "summary": "Labeled mutant corpus M1-M10 each flipping its named subcheck plus null control M0; 11/11 pass.",
    **common,
})
add("artifact-readme", {
    "event_type": "artifact", "validation_status": "unverified", "artifact_type": "f2a_rev12_readme",
    "path": str(readme.relative_to(ROOT)), "sha256": hashes["readme"],
    "evidence_refs": [ref(readme), ref(report)],
    "summary": "Method, result table, hard failures, projected repair path, reproduction, falsifier, limitations and non-claims.",
    **common,
})
add("artifact-checkpoint", {
    "event_type": "artifact", "validation_status": "unverified", "artifact_type": "worker_checkpoint",
    "path": "runtime/state/w035_f2a_checkpoint_1.json", "sha256": sha(CKPT),
    "evidence_refs": [ckpt_ref, ref(report)],
    "summary": "Worker checkpoint for W035-F2A-REV12-INDEP-VERDICT-01: artifact hashes, pins, verdict, falsifiers.",
    **common,
})

add("review-f2a", {
    "event_type": "review", "reviewer": "worker-035",
    "target_id": f"schemas/af_scc_c2_vacuum.yaml#sha256:{F2A_SHA}",
    "target_path": "schemas/af_scc_c2_vacuum.yaml",
    "reviewed_revision": 12, "counts_as_full_schema_verdict": True,
    "verdict": "revise", "score": 3.5,
    "hard_failures": [
        "HF-035-F2A-1: f0_binding.consistency_evidence_sha256 declares 675a99d0d25b2b37 but the file at the declared path measures 9e335e9ba1bfcf77 and is FROZEN rev28-pinned there; the declared bytes exist nowhere under the pinned tree (C08.4, C08.6).",
        "HF-035-F2A-2: the pinned consistency evidence carries no hash of either compared tree (no map_taxonomy_sha256, no lead_contract_sha256, no measured_at), so consistent=true is not bound to the declared F0 0abb9ed8 / supplement d7419b4e (C08.5).",
        "HF-035-F2A-3: 4 of 5 l1_ledger_refs (T-401, T-402, T-514, T-520) claim citation_status=verified_by_L1 while the pinned ledger a1674f094979 has no citation_status field and records verification_status=abstract-read, review_status=not_independently_reviewed for all referenced rows (C12.3).",
    ],
    "findings": [
        "Class semantics pass at the pinned bytes: identity/freeze pin, strict YAML hygiene, token discipline, forall-exists(comeager)-forall-not-exists chain with tagged-union D0, C2 conclusion typing with WCC excluded, containment direction E_C2 subset E_{C^1,1} subset E_H2loc subset E_C0 agreeing with the C0 schema, disjointness from C0, falsifier tiers, genericity typing, and taxonomy/schema/supplement alias equality.",
        "Machine class separation is clean: canonical detector 0 findings on the snapshot; 27-fixture regression 17/17 leaks, 10/10 controls, FP 0 / FN 0, exit 0.",
        "All three blocking failures are evidence/provenance binding defects, not class-semantics or class-separation defects; a rev13 that regenerates hash-bound consistency evidence, re-pins the pointer and aligns l1_ledger_refs with the ledger vocabulary is projected to clear them without a semantic rewrite.",
        "Controls M1-M10 each flip their named subcheck; the failure set is not a harness artifact.",
        "Cross-class observation only (not an F2a finding): the C0 schema line 245 still contains the inverted phrase 'C2 is a strictly larger extension class'.",
    ],
    "evidence_refs": [ref(report), ref(controls), ref(checker), ref(snap), f"schemas/af_scc_c2_vacuum.yaml#sha256:{F2A_SHA[:12]}",
                      "artifacts/formulation/evidence/taxonomy_consistency.json#sha256:9e335e9ba1bf",
                      "ledger/theorems.jsonl#sha256:a1674f094979"],
    "falsifier": [
        "any blocking subcheck passing on a re-run at the pinned hashes",
        "a file at the declared evidence path hashing to 675a99d0d25b2b37",
        "a pinned ledger row for T-401/T-402/T-514/T-520 carrying citation_status=verified_by_L1 or review_status=independently_reviewed",
        "a canonical F2a re-freeze (this verdict binds to 5476a3f2c6bc)",
    ],
    "non_claims": non_claims + ["one reviewer's verdict, not the gate adjudication"],
    **common,
})

add("claim-f2a", {
    "event_type": "claim", "conclusion_type": "formal_model",
    "statement": (
        f"At FROZEN rev28 pin schemas/af_scc_c2_vacuum.yaml sha256 {F2A_SHA} (revision 12, class "
        "AF-SCC-C2-VAC-GEN, node F2a), an independent own-implementation verification passes 12 of 14 check "
        "groups (55/58 subchecks) including identity/mirror/freeze pin, strict YAML hygiene, class-token "
        "discipline, the exact quantifier chain, C2 conclusion typing without WCC inflation, containment "
        "direction, C0 disjointness, falsifier decidability, genericity typing, cross-artifact aliases and "
        "machine class separation (detector 0 findings; 27-fixture regression 17/0/10/0). Three blocking "
        "subchecks fail and are the reason for the revise verdict: (C08.4) f0_binding.consistency_evidence_sha256 "
        "declares 675a99d0d25b2b37 while the declared path measures 9e335e9ba1bfcf77 and is FROZEN-pinned there; "
        "(C08.5) that evidence document carries no compared-tree hashes, so its consistent=true is unbound to "
        "F0 0abb9ed8 / supplement d7419b4e; (C12.3) 4 of 5 l1_ledger_refs claim citation_status=verified_by_L1 "
        "with no supporting field or verdict in the pinned ledger a1674f094979. Controls M1-M10 flip their named "
        "subchecks and the null control reproduces the clean vector (11/11)."
    ),
    "assumptions": [
        "the FROZEN rev28 pin set is the revision under gate review",
        "the reviewed revision is the revision a lead would repair",
        "the pinned evidence document is the artifact the binding intends to cite",
    ],
    "falsifier": [
        "any blocking subcheck that passes on a re-run at the pinned hashes",
        "a file at artifacts/formulation/evidence/taxonomy_consistency.json hashing to 675a99d0d25b2b37 at the reviewed revision",
        "a pinned ledger row for T-401/T-402/T-514/T-520 carrying citation_status=verified_by_L1 or review_status=independently_reviewed",
        "a pinned consistency-evidence document carrying map_taxonomy_sha256 and lead_contract_sha256",
        "any pinned canonical input changing hash during the run; a canonical F2a re-freeze",
    ],
    "evidence_refs": [ref(report), ref(controls), ref(checker), ref(snap), f"schemas/af_scc_c2_vacuum.yaml#sha256:{F2A_SHA[:12]}"],
    "artifact_refs": [ref(report), ref(controls), ref(checker)],
    "non_claims": non_claims,
    **common,
})

add("status-complete", {
    "event_type": "status", "status": "active", "hours": 0.6,
    "evidence_refs": [ref(report), ref(controls), ref(readme), ckpt_ref, f"schemas/af_scc_c2_vacuum.yaml#sha256:{F2A_SHA[:12]}"],
    "summary": ("CHECKPOINT + EXIT. W035-F2A-REV12-INDEP-VERDICT-01 complete at worker level: one class-bound task, "
                "6 artifacts on disk and hash-pinned, controls 11/11, canonical F2a hash unchanged at finalize "
                "(5476a3f2c6bc, drift false), no canonical artifact edited. Verdict revise 3.5 with three hash-bound "
                "blocking hard failures (evidence binding x2, L1 provenance x1); projected rev13 repair path recorded "
                "in the README. Controller ingest/apply owns promotion; worker exits."),
    "next_falsifier": "Re-run check_f2a_rev12.py at the then-current F2a hash; a re-freeze voids this verdict and requires a fresh review at the new revision.",
    "completion_scope": "worker lifecycle only; this event is not a node done / gate verdict",
    "non_claims": non_claims,
    **common,
})

existing = set()
if OUTBOX.exists():
    for line in OUTBOX.read_text().splitlines():
        try:
            existing.add(json.loads(line)["event_id"])
        except Exception:
            pass

new = [e for e in ev if e["event_id"] not in existing]
with OUTBOX.open("a") as fh:
    for e in new:
        fh.write(json.dumps(e) + "\n")

print(f"checkpoint {CKPT.relative_to(ROOT)} sha256={sha(CKPT)}")
for e in ev:
    print(("APPEND " if e["event_id"] not in existing else "SKIP   ") + e["event_id"])
print(f"appended {len(new)}/{len(ev)} events to {OUTBOX.relative_to(ROOT)}")
