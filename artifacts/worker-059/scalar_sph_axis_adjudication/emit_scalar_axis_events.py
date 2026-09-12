#!/usr/bin/env python3
"""Append the W059-SCALARSPH-AXIS-ADJ-01 upward events to comms/outbox/worker-059.jsonl.

Self-checks before every write (PROTOCOL rule 5): artifact exists on disk, its
sha256 matches the emitted value, event validates against research_map.schemas,
event_id is unique against the existing outbox.
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
sys.path.insert(0, str(ROOT))
from research_map.schemas import validate_event  # noqa: E402

D = ROOT / "artifacts/worker-059/scalar_sph_axis_adjudication"
OUT = ROOT / "comms/outbox/worker-059.jsonl"
TS = "2026-09-12T00:56:00+08:00"
P = "w059-scalarspaxis-20260912T0056"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rel(p):
    return str(Path(p).relative_to(ROOT))


ART = {
    "evidence": rel(D / "independent_evidence.json"),
    "matrix": rel(D / "axis_legality_matrix.json"),
    "claims": rel(D / "claims_binding_audit.json"),
    "instrument": rel(D / "check_scalar_sph_axis.py"),
    "review": rel(D / "review_F0scalar_0abb9ed8.json"),
    "checkpoint": rel(D / "checkpoint_w059_scalar_axis.json"),
    "annex": rel(D / "postrun_annex.json"),
    "finalize": rel(D / "finalize_annex.py"),
}
H = {k: sha(ROOT / v) for k, v in ART.items()}
REVIEW = json.loads((ROOT / ART["review"]).read_text())
EVID = json.loads((ROOT / ART["evidence"]).read_text())
MATRIX = json.loads((ROOT / ART["matrix"]).read_text())

ev_refs = [
    f"{ART['evidence']}#{H['evidence']}",
    f"{ART['matrix']}#{H['matrix']}",
    f"{ART['claims']}#{H['claims']}",
    f"{ART['instrument']}#{H['instrument']}",
    "artifacts/worker-059/scalar_sph_axis_adjudication/snapshot/formulation_taxonomy.canonical.0abb9ed8a961.yaml#0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/worker-059/scalar_sph_axis_adjudication/snapshot/formulation_taxonomy.supplement.d7419b4e8963.yaml#d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    f"{ART['annex']}#{H['annex']}",
]
FALSIFIER = REVIEW["next_falsifier"]

events = [
    {
        "event_id": f"{P}-artifact-evidence",
        "event_type": "artifact", "node_id": "F0", "group_id": "formulation",
        "class_id": "AF-WCC-SCALAR-SPH", "gate": "G-F0",
        "artifact_type": "independent_verification",
        "path": ART["evidence"], "sha256": H["evidence"], "validation_status": "unverified",
        "evidence_refs": ev_refs, "falsifier": FALSIFIER,
        "created_at": TS, "actor": "worker-059",
    },
    {
        "event_id": f"{P}-artifact-matrix",
        "event_type": "artifact", "node_id": "F0", "group_id": "formulation",
        "class_id": "AF-WCC-SCALAR-SPH", "gate": "G-F0",
        "artifact_type": "registry_legality_matrix",
        "path": ART["matrix"], "sha256": H["matrix"], "validation_status": "unverified",
        "evidence_refs": ev_refs, "falsifier": FALSIFIER,
        "created_at": TS, "actor": "worker-059",
    },
    {
        "event_id": f"{P}-artifact-claims",
        "event_type": "artifact", "node_id": "F0", "group_id": "formulation",
        "class_id": "AF-WCC-SCALAR-SPH", "gate": "G-F0",
        "artifact_type": "claims_binding_audit",
        "path": ART["claims"], "sha256": H["claims"], "validation_status": "unverified",
        "evidence_refs": ev_refs, "falsifier": FALSIFIER,
        "created_at": TS, "actor": "worker-059",
    },
    {
        "event_id": f"{P}-artifact-instrument",
        "event_type": "artifact", "node_id": "F0", "group_id": "formulation",
        "class_id": "AF-WCC-SCALAR-SPH", "gate": "G-F0",
        "artifact_type": "instrument",
        "path": ART["instrument"], "sha256": H["instrument"], "validation_status": "unverified",
        "evidence_refs": ev_refs, "falsifier": FALSIFIER,
        "created_at": TS, "actor": "worker-059",
    },
    {
        "event_id": f"{P}-artifact-checkpoint",
        "event_type": "artifact", "node_id": "F0", "group_id": "formulation",
        "class_id": "AF-WCC-SCALAR-SPH", "gate": "G-F0",
        "artifact_type": "checkpoint",
        "path": ART["checkpoint"], "sha256": H["checkpoint"], "validation_status": "unverified",
        "evidence_refs": ev_refs, "falsifier": FALSIFIER,
        "created_at": TS, "actor": "worker-059",
    },
    {
        "event_id": f"{P}-artifact-annex",
        "event_type": "artifact", "node_id": "F0", "group_id": "formulation",
        "class_id": "AF-WCC-SCALAR-SPH", "gate": "G-F0",
        "artifact_type": "drift_annex",
        "path": ART["annex"], "sha256": H["annex"], "validation_status": "unverified",
        "evidence_refs": ev_refs, "falsifier": FALSIFIER,
        "created_at": TS, "actor": "worker-059",
    },
    {
        "event_id": f"{P}-artifact-finalize",
        "event_type": "artifact", "node_id": "F0", "group_id": "formulation",
        "class_id": "AF-WCC-SCALAR-SPH", "gate": "G-F0",
        "artifact_type": "instrument",
        "path": ART["finalize"], "sha256": H["finalize"], "validation_status": "unverified",
        "evidence_refs": ev_refs, "falsifier": FALSIFIER,
        "created_at": TS, "actor": "worker-059",
    },
    {
        "event_id": f"{P}-claim-d3-registry",
        "event_type": "claim", "node_id": "F0", "group_id": "formulation",
        "class_id": "AF-WCC-SCALAR-SPH", "gate": "G-F0",
        "conclusion_type": "formal_model",
        "statement": (
            "Measured at FROZEN rev28 pair A=research_map/formulation_taxonomy.yaml#0abb9ed8a961 and "
            "B=artifacts/formulation/formulation_taxonomy.yaml#d7419b4e8963 (class AF-WCC-SCALAR-SPH): "
            "(1) the stored D3 discharge records contradict each other on class scope - A says 'confirmed "
            "discharged for ALL FOUR classes, including AF-WCC-SCALAR-SPH', B says 'all three vacuum classes' - "
            "while the canonical consistency tool re-run in sandbox prints CONSISTENT (4 classes, 0 contract-text "
            "divergences); (2) scalar axes.genericity_kind='unresolved' is admitted by F0 field_vocabulary but is "
            "absent from rule_spec.vocabularies.genericity_kind and is neither a canonical key nor a declared alias "
            "in VOCAB_ALIASES; (3) genericity_topology is instantiated in 0/4 class axes although declared with a "
            "mandatory rule; (4) 95 claims bind to the class and 0 assert its WCC conclusion. Independent "
            "instrument, 29 checks, 10/10 single-defect mutants detected."),
        "assumptions": [
            "the two files are the FROZEN rev28 logical artifacts named in FROZEN.json logical_artifacts",
            "the stored D3 records are intended to be consistency-checked by the canonical tool",
            "worker-level measurement; no node status or gate verdict is claimed",
        ],
        "falsifier": FALSIFIER,
        "evidence_refs": ev_refs,
        "created_at": TS, "actor": "worker-059",
    },
    {
        "event_id": f"{P}-review",
        "event_type": "review", "node_id": "F0", "group_id": "formulation",
        "class_id": "AF-WCC-SCALAR-SPH", "gate": "G-F0",
        "target_id": "F0/AF-WCC-SCALAR-SPH",
        "target_path": "research_map/formulation_taxonomy.yaml",
        "reviewer": "worker-059",
        "reviewed_revision": 5, "reviewed_sha256": REVIEW["reviewed_sha256"],
        "companion_sha256": REVIEW["companion_sha256"],
        "artifact": ART["review"], "sha256": H["review"],
        "verdict": "revise", "score": 3.5,
        "counts_as_independent_verdict": True,
        "counts_as_full_schema_verdict": False,
        "counts_as_independent_second_verdict": False,
        "hard_failures": [h["id"] + ": " + h["name"] for h in REVIEW["hard_failures"]],
        "findings": [f["id"] + ": " + f["text"][:240] for f in REVIEW["findings"]],
        "evidence_refs": ev_refs,
        "next_falsifier": FALSIFIER,
        "validation_status": "unverified",
        "created_at": TS, "actor": "worker-059",
    },
    {
        "event_id": f"{P}-blocker",
        "event_type": "blocker", "node_id": "F0", "group_id": "formulation",
        "class_id": "AF-WCC-SCALAR-SPH", "gate": "G-F0",
        "description": (
            "HF-059-SPH-01: the two FROZEN-pinned F0 artifacts store contradictory D3 discharge scopes for "
            "AF-WCC-SCALAR-SPH while the canonical consistency certificate is green (record cannot be cited). "
            "HF-059-SPH-02: no registry-clean scalar genericity_kind token exists (unresolved unregistered in "
            "VOCAB_ALIASES and rule_spec; provisional_baire_residual an alias forbidden in new canonical artifacts; "
            "only residual_comeager clean but contradicts the declared unresolved state) and genericity_topology "
            "is instantiated in 0/4 class axes."),
        "needed_to_unblock": (
            "A controller ruling that (a) designates the governing genericity registry for the scalar class, "
            "(b) fixes the D3 record scope in canonical F0 to match the supplement (or the reverse), and "
            "(c) schedules the two-slot instantiation as a fresh F0 revision with a re-run of the F0 acceptance "
            "round - not inside astra-life05-evidence-binding-repair, whose REC-12 bounds forbid axis-semantics "
            "changes. Until then AF-WCC-SCALAR-SPH remains closed to WCC-conclusion claims (H4)."),
        "evidence_refs": ev_refs,
        "created_at": TS, "actor": "worker-059",
    },
    {
        "event_id": f"{P}-status",
        "event_type": "status", "node_id": "F0", "group_id": "formulation",
        "class_id": "AF-WCC-SCALAR-SPH", "gate": "G-F0",
        "status": "active", "hours": 0.4,
        "checkpoint_id": "w059-ckpt-scalarspaxis-20260912T0053",
        "summary": (
            "W059-SCALARSPH-AXIS-ADJ-01 complete at worker level: cross-artifact adjudication of the "
            "AF-WCC-SCALAR-SPH genericity/record binding at FROZEN rev28 (A 0abb9ed8, B d7419b4e, VOCAB 46cd9f1e, "
            "rule_spec 40f9bb9e). Verdict revise 3.5: content surface green (single-q TAIL predicate, no assertive "
            "SET wording, field consistency, D1 resolved, FROZEN pins match); 9 measured defects all in the "
            "genericity/record layer, two raised to hard failures (D3 scope contradiction; no registry-clean token "
            "plus missing two-slot). 29 checks / 20 pass; 10/10 single-defect mutants detected; canonical tool "
            "sandboxed. Materiality: 95 bound claims, 0 theorem-level, 0 asserting the class conclusion. "
            "FROZEN.json was republished to rev29 at 00:55:02 during the run; A 0abb9ed8 / B d7419b4e / VOCAB "
            "46cd9f1e / rule_spec 40f9bb9e are unchanged and rev29 re-pins A and B at the reviewed hashes, so the "
            "verdict survives (postrun_annex.json). No global state mutated, no node completion or gate verdict "
            "claimed."),
        "evidence_refs": ev_refs,
        "next_falsifier": FALSIFIER,
        "created_at": TS, "actor": "worker-059",
    },
]

# ------------------- pre-write self-checks -------------------
existing = OUT.read_text().splitlines() if OUT.exists() else []
existing_ids = {json.loads(l).get("event_id") for l in existing if l.strip()}
problems = []
for e in events:
    try:
        validate_event(e)
    except Exception as exc:
        problems.append(f"schema {e['event_id']}: {exc}")
    if e["event_id"] in existing_ids:
        problems.append(f"duplicate event_id {e['event_id']}")
    for r in e.get("evidence_refs", []):
        path = r.split("#")[0]
        p = ROOT / path
        if not p.exists():
            problems.append(f"{e['event_id']}: missing evidence {path}")
        elif "#" in r and len(r.split("#")[1]) == 64:
            if sha(p) != r.split("#")[1]:
                problems.append(f"{e['event_id']}: hash mismatch {path}")
for k, v in ART.items():
    if not (ROOT / v).exists():
        problems.append(f"missing artifact {v}")
if problems:
    print("REJECTED:"); [print(" -", p) for p in problems]; sys.exit(1)

with OUT.open("a") as f:
    for e in events:
        f.write(json.dumps(e) + "\n")
(D / "emitted_hashes.json").write_text(json.dumps({
    "task_id": "W059-SCALARSPH-AXIS-ADJ-01",
    "outbox": str(OUT.relative_to(ROOT)),
    "lines_before": len(existing), "lines_after": len(existing) + len(events),
    "event_ids": [e["event_id"] for e in events],
    "artifact_sha256": H,
    "schema_validation": "all pass (research_map.schemas.validate_event)",
    "evidence_refs_verified_on_disk": True,
}, indent=1) + "\n")
print(json.dumps({"ok": True, "appended": len(events), "lines_after": len(existing) + len(events),
                  "event_ids": [e["event_id"] for e in events]}, indent=1))
