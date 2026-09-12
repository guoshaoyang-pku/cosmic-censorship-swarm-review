#!/usr/bin/env python3
"""Emit worker-06 FORM-EXEMPT-09 checkpoint + outbox events (validated, reproducible)."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

CORPUS = Path(__file__).resolve().parent
ROOT = CORPUS.parents[2]  # CORPUS is already the package directory
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

NOW = datetime.now(ZoneInfo("Asia/Shanghai")).replace(microsecond=0).isoformat()


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


A = {
    "manifest": CORPUS / "manifest.json",
    "report": CORPUS / "report.json",
    "relocation_report": CORPUS / "relocation_report.json",
    "classification": CORPUS / "classification.json",
    "findings": CORPUS / "FINDINGS.md",
    "submission": CORPUS / "SUBMISSION.md",
}
H = {k: sha(v) for k, v in A.items()}
for k, v in H.items():
    assert len(v) == 64, (k, v)

report = json.loads(A["report"].read_text())
rel = json.loads(A["relocation_report"].read_text())
assert report["corpus_validity"]["verdict"] == "VALID"
assert report["aggregates"]["union_escape_rate"] == 1.0

rel_paths = {k: str(v.relative_to(ROOT)) for k, v in A.items()}
checkpoint = {
    "checkpoint": 5,
    "at": NOW.replace("+08:00", "+0800"),
    "worker": "worker-06",
    "hours_spent_estimate": 1.2,
    "assignment": ("FORM-EXEMPT-09 (successor to FORM-HELDOUT-07): exempt-field held-out corpus, "
                   "node A1, gate G-CLASSBIND, classes AF-SCC-C0/C2-VAC-GEN + AF-WCC-VAC-GEN"),
    "status": {
        "corpus": "VALID (10/10 controls accepted by both stages)",
        "union_escape_rate": report["aggregates"]["union_escape_rate"],
        "structural_escape_rate": report["aggregates"]["structural_escape_rate"],
        "semantic_escape_rate": report["aggregates"]["semantic_escape_rate"],
        "relocation_criterion": f"{rel['criterion_confirmed']}/{rel['n_cases']} confirmed, "
                                f"gate gaps {rel['gate_gaps']}",
        "classification": json.loads(A["classification"].read_text())["counts"],
        "stage_hashes": {"structural": report["stage_1_structural"]["sha256"],
                         "semantic": report["stage_2_semantic"]["sha256"]},
        "no_completion_claim": "worker cannot set done/passed; no theorem, no physics result",
    },
    "artifacts": {rel_paths[k]: {"sha256": v} for k, v in H.items()},
    "falsifier": ("any mutant shown not to violate a frozen class invariant, or any control rejected "
                  "by either stage; a repair must be re-measured on a fresh corpus"),
}
cp_path = ROOT / "runtime" / "state" / "w06_checkpoint_5.json"
cp_path.write_text(json.dumps(checkpoint, indent=2, ensure_ascii=False) + "\n")
with (ROOT / "runtime" / "state" / "w06_checkpoints.jsonl").open("a") as f:
    f.write(json.dumps(checkpoint, ensure_ascii=False) + "\n")

ev = [
    {"event_id": "w06-20260912T0045-exempt09-artifact-manifest", "event_type": "artifact",
     "created_at": NOW, "actor": "worker-06", "node_id": "A1", "artifact_type": "corpus_manifest",
     "path": rel_paths["manifest"], "sha256": H["manifest"], "validation_status": "unverified",
     "class_ids": report["class_ids"], "manifest_sha256_self": H["manifest"]},
    {"event_id": "w06-20260912T0045-exempt09-artifact-report", "event_type": "artifact",
     "created_at": NOW, "actor": "worker-06", "node_id": "A1", "artifact_type": "validation_evidence",
     "path": rel_paths["report"], "sha256": H["report"], "validation_status": "unverified",
     "class_ids": report["class_ids"]},
    {"event_id": "w06-20260912T0045-exempt09-artifact-relocation", "event_type": "artifact",
     "created_at": NOW, "actor": "worker-06", "node_id": "A1", "artifact_type": "control_evidence",
     "path": rel_paths["relocation_report"], "sha256": H["relocation_report"],
     "validation_status": "unverified"},
    {"event_id": "w06-20260912T0045-exempt09-artifact-classification", "event_type": "artifact",
     "created_at": NOW, "actor": "worker-06", "node_id": "A1", "artifact_type": "derived_analysis",
     "path": rel_paths["classification"], "sha256": H["classification"],
     "validation_status": "unverified"},
    {"event_id": "w06-20260912T0045-exempt09-artifact-findings", "event_type": "artifact",
     "created_at": NOW, "actor": "worker-06", "node_id": "A1", "artifact_type": "report",
     "path": rel_paths["findings"], "sha256": H["findings"], "validation_status": "unverified"},
    {"event_id": "w06-20260912T0045-exempt09-artifact-submission", "event_type": "artifact",
     "created_at": NOW, "actor": "worker-06", "node_id": "A1", "artifact_type": "report",
     "path": rel_paths["submission"], "sha256": H["submission"], "validation_status": "unverified"},
    {"event_id": "w06-20260912T0045-exempt09-status", "event_type": "status",
     "created_at": NOW, "actor": "worker-06", "node_id": "A1", "status": "active", "hours": 1.2,
     "summary": (
         "FORM-EXEMPT-09 complete and VALID: 18 pre-registered mutants hiding frozen-invariant leaks in "
         "exempt/unscanned explanatory fields escape BOTH stages (union escape 1.0000; structural 1.0000, "
         "semantic 1.0000); 10/10 controls accepted so the corpus is not format-dominated. Relocation "
         "control: 11/14 sentences are caught with the expected rule in a scanned field (genuine "
         "field-exemption escapes); 3 are not caught anywhere (all-field gate gaps: matter token absent "
         "from R12, transfer truth-table prose unchecked by R28, R15 regex narrower than spec). "
         "Artifacts under artifacts/worker-06/exempt_field_corpus/. No completion, no theorem claimed."),
     "evidence_refs": [f"{rel_paths['report']}#{H['report'][:12]}",
                       f"{rel_paths['manifest']}#{H['manifest'][:12]}",
                       f"{rel_paths['relocation_report']}#{H['relocation_report'][:12]}",
                       f"{rel_paths['classification']}#{H['classification'][:12]}"],
     "next_falsifier": ("any mutant shown not to violate a frozen invariant, or any control rejected by "
                        "either stage; a repaired gate must be re-measured on a fresh corpus, never this one")},
    {"event_id": "w06-20260912T0045-exempt09-claim", "event_type": "claim",
     "created_at": NOW, "actor": "worker-06", "class_id": "AF-SCC-C0-VAC-GEN",
     "class_ids": report["class_ids"], "node_id": "A1",
     "conclusion_type": "formal_model",
     "statement": (
         "Held-out measurement (manifest sha256 "
         f"{H['manifest'][:16]}) on the frozen canonical schemas (FROZEN rev18: C0 bdb23f76b895, "
         "C2 e9fcefe6e595, WCC f962c117ba11): 18 mutants that state a frozen-invariant violation inside "
         "a key-exempt or unscanned explanatory field are all accepted by BOTH acceptance stages "
         "(union escape 1.0000; structural stage check_class_schema.py sha256 "
         f"{report['stage_1_structural']['sha256'][:16]}, semantic stage spec_conformance_audit.py "
         f"sha256 {report['stage_2_semantic']['sha256'][:16]}), with all 10 controls accepted. A post-hoc "
         "relocation control confirms 11/14 of the injected sentences are caught by the expected rule in "
         "a scanned field, so the escapes are field exemptions rather than over-claimed leaks; the "
         "remaining 3 families are all-field gate gaps (matter-in-VAC, transfer-truth-table prose, "
         "source-overclaim regex). No repair was attempted; no theorem or physics result is claimed."),
     "assumptions": [
         "corpus was authored and its manifest hashed before any stage ran; fixture hashes verified at run time",
         "escapes are structural findings, not proof that any mutant is a legitimate formulation",
         "the relocation control is post-hoc and hash-bound to the main reports; it does not alter them",
         "class interpretation remains with the schema owner (astra-lead-formulation)"],
     "falsifier": ("a mutant shown not to violate a frozen invariant, or a control rejected by either "
                   "stage, invalidates the corresponding family; a repaired gate rejecting all 18 while "
                   "accepting all controls falsifies the blind-spot claim in the direction of improvement "
                   "and must be re-measured on a fresh corpus"),
     "evidence_refs": [f"{rel_paths['report']}#{H['report'][:12]}",
                       f"{rel_paths['manifest']}#{H['manifest'][:12]}",
                       f"{rel_paths['relocation_report']}#{H['relocation_report'][:12]}",
                       f"{rel_paths['classification']}#{H['classification'][:12]}"],
     "artifact_refs": [f"{rel_paths['report']}#{H['report'][:12]}",
                       f"{rel_paths['manifest']}#{H['manifest'][:12]}",
                       f"{rel_paths['findings']}#{H['findings'][:12]}"]},
]
for e in ev:
    validate_event(e)

out = ROOT / "comms" / "outbox" / "worker-06.jsonl"
with out.open("a") as f:
    for e in ev:
        f.write(json.dumps(e, ensure_ascii=False, separators=(",", ":")) + "\n")
print(json.dumps({"checkpoint": str(cp_path), "events_appended": len(ev),
                  "outbox": str(out), "hashes": {k: v[:12] for k, v in H.items()},
                  "at": NOW}, indent=2))
