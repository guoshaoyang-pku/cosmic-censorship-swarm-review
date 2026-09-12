#!/usr/bin/env python3
"""Emit W061-F2A-INDEP-REV-01 review artifacts, checkpoint, and comms events.

Reads the probe outputs already produced by probe_f2a.py (pinned + drift), writes
REVIEW.json / REVIEW.md / PINNED.json / CHECKPOINT.json / SHA256SUMS, appends the
upward events to comms/outbox/worker-061.jsonl and a local checkpoint line to
runtime/state/w061_checkpoints.jsonl.

This script is idempotent in the sense that it appends only; it never edits or deletes
existing comms traffic, and never writes research_map/research_map.json or any
formulation/literature artifact (worker authority rule).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
HERE = ROOT / "artifacts/worker-061/f2a_independent_verdict"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")
STAMP = datetime.now(CST).strftime("%Y%m%dT%H%M%S")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


pinned = json.loads((HERE / "probe_f2a_output.json").read_text())
drift = json.loads((HERE / "drift/probe_f2a_drift_output.json").read_text())

H = {
    "schema": sha(HERE / "pinned/af_scc_c2_vacuum.yaml"),
    "f1": sha(HERE / "pinned/af_wcc_vacuum.yaml"),
    "f2b": sha(HERE / "pinned/af_scc_c0_vacuum.yaml"),
    "taxonomy": sha(HERE / "pinned/formulation_taxonomy.canonical.yaml"),
    "gate_tool": sha(HERE / "pinned/check_class_schema.py"),
    "classsep_tool": sha(HERE / "pinned/class_separation.py"),
    "probe": sha(HERE / "probe_f2a.py"),
    "probe_out": sha(HERE / "probe_f2a_output.json"),
    "gate_out": sha(HERE / "gate/check_class_schema_pinned.json"),
    "drift_schema": sha(HERE / "drift/af_scc_c2_vacuum.yaml"),
    "drift_f1": sha(HERE / "drift/af_wcc_vacuum.yaml"),
    "drift_f2b": sha(HERE / "drift/af_scc_c0_vacuum.yaml"),
    "drift_probe_out": sha(HERE / "drift/probe_f2a_drift_output.json"),
}

FINDINGS = [
    "F-01 POSITIVE (HF-A1 resolved at this hash): extension_predicate block 'proper_future_extension_in_class' exists with "
    "frozen_direction=future, frozen_regularity=C2, frozen_equation_concept=classical_ricci and clauses (a)-(f) in its definition; "
    "quantifiers.domains.D3.definition_ref resolves to it and conclusion.statement_formal calls the same predicate. Probe P2 pass.",
    "F-02 POSITIVE (HF-A2 disposition, hash-bound): the D0/(s,delta) binder used by quantifiers.formal, quantifiers.negation, "
    "quantifiers.negation_normal_form and conclusion.statement_formal is now (i) defined in quantifiers.domains.D0 with a "
    "definition_ref, and (ii) the same quantifier form as the pinned canonical F0 class statement ('For every admissible (s,delta) "
    "...'). The rev3-vintage internal contradiction (an order_note claiming exactly one frozen data class / no regularity-pair binder "
    "while the statement carried the binder) is absent from this revision. The prior HF-A2 hard failure is therefore falsified "
    "against these bytes; it would return if the canonical F0 text dropped the admissible-(s,delta) quantifier while F2a kept it. Probe P3 pass.",
    "F-03 POSITIVE: canonical check_class_schema.py returns pass (exit 0, failed_rules []) on the pinned bytes. Probe P4 pass.",
    "F-04 POSITIVE: f0_binding.declared_f0_sha256 equals the measured pinned canonical taxonomy hash "
    f"{H['taxonomy'][:12]} (research_map/formulation_taxonomy.yaml). Probe P5 pass.",
    "F-05 POSITIVE: research_map/class_separation.py finds nothing on the pinned F2a text; the frozen regression corpus still scores "
    "leaks 17/17, controls 10/10, FP 0, FN 0 (VERDICT: PASS). Probe P6 pass.",
    "F-06 POSITIVE: F1/F2a/F2b agree on all 12 restricting data-class paths at the pinned triple (matter, Lambda, equations, both "
    "constraints, default regularity, s, delta, both decay rates, symmetry, ADM sign). The two residual textual differences are "
    "gloss-only: F1 appends ' (weighted Sobolev)' to the Sobolev spaces phrase, and F1 appends an explanatory clause after "
    "'not imposed' for parity. Consequence: the map's G-FORM unmet item 'no single frozen data class (s,delta,norm) is shared by "
    "F1/F2a/F2b' is NOT reproduced at the pinned triple; it should be re-measured before it is used to hold G-FORM. Probe P7 pass.",
    "F-07 POSITIVE: no conclusion inflation. conclusion_type is the C2 token scc_c2_future_inextendibility (family SCC); the assertive "
    "conclusion surfaces carry no WCC/visibility content and no C0 conclusion token; the C0/C1/H2_loc and two-sided readings live in "
    "forbidden_* / variant slots. Probe P8 pass.",
    "F-08 SOFT (not a hard failure): binder naming. conclusion.statement_formal quantifies 'forall D in G_{s,delta}' while "
    "quantifiers.ordered names the same D2 binder '(Sigma,h,K)'. Same domain, cosmetic divergence; recommend aligning the names in the "
    "next revision.",
    "F-09 SOFT: unresolved_items (diffeomorphism-quotient construction, meagreness of the excluded families, non-vacuity witness "
    "membership, nonlinear extension regularity) remain declared unresolved. This review does not resolve them and the accept does not "
    "extend to them.",
    "F-10 PROCESS / drift: between the pin (00:19+08:00) and this emission the canonical F2a moved 4f97273e -> 4b3dfd76 -> "
    f"{H['drift_schema'][:12]} (rev11), F1 -> {H['drift_f1'][:12]}, F2b -> {H['drift_f2b'][:12]}. A non-binding drift control reran the "
    "same eight probes on the newest canonical copies: all pass, and the semantic delta between 4b3dfd76 and rev11 is the revision "
    "number only. The accept binds to the pinned hash; later canonical bytes are not covered by it.",
]

REVIEW = {
    "task_id": "W061-F2A-INDEP-REV-01",
    "created_at": NOW,
    "reviewer": "worker-061",
    "reviewer_role": "bounded execution worker; not an author of F2a and no formulation artifact was edited",
    "target_id": "F2a",
    "node_id": "F2a",
    "class_id": "AF-SCC-C2-VAC-GEN",
    "gate": "G-FORM",
    "verdict": "accept",
    "score": 4.0,
    "hard_failures": [],
    "findings": FINDINGS,
    "reviewed_sha256": H["schema"],
    "reviewed_hashes": {
        "schemas/af_scc_c2_vacuum.yaml": H["schema"],
        "research_map/formulation_taxonomy.yaml": H["taxonomy"],
        "schemas/af_wcc_vacuum.yaml": H["f1"],
        "schemas/af_scc_c0_vacuum.yaml": H["f2b"],
        "artifacts/formulation/tools/check_class_schema.py": H["gate_tool"],
        "research_map/class_separation.py": H["classsep_tool"],
    },
    "pinned_artifact": "artifacts/worker-061/f2a_independent_verdict/pinned/af_scc_c2_vacuum.yaml",
    "drift_control": {
        "measured_at": NOW,
        "hash": H["drift_schema"],
        "probe_verdict": drift["verdict"],
        "hard_failures": drift["hard_failures"],
        "semantic_delta_vs_pinned": "revision number only (semantic YAML diff)",
        "binding": False,
    },
    "evidence_refs": [
        f"artifacts/worker-061/f2a_independent_verdict/pinned/af_scc_c2_vacuum.yaml#sha256:{H['schema'][:12]}",
        f"artifacts/worker-061/f2a_independent_verdict/probe_f2a_output.json#sha256:{H['probe_out'][:12]}",
        f"artifacts/worker-061/f2a_independent_verdict/gate/check_class_schema_pinned.json#sha256:{H['gate_out'][:12]}",
        f"artifacts/worker-061/f2a_independent_verdict/pinned/formulation_taxonomy.canonical.yaml#sha256:{H['taxonomy'][:12]}",
        f"artifacts/worker-061/f2a_independent_verdict/pinned/af_wcc_vacuum.yaml#sha256:{H['f1'][:12]}",
        f"artifacts/worker-061/f2a_independent_verdict/pinned/af_scc_c0_vacuum.yaml#sha256:{H['f2b'][:12]}",
        f"artifacts/worker-061/f2a_independent_verdict/probe_f2a.py#sha256:{H['probe'][:12]}",
    ],
    "artifact_refs": [
        f"artifacts/worker-061/f2a_independent_verdict/REVIEW.json",
        f"artifacts/worker-061/f2a_independent_verdict/probe_f2a_output.json#sha256:{H['probe_out'][:12]}",
    ],
    "independence": {
        "author_of_target": "astra-lead-formulation",
        "reviewer_is_author": False,
        "correlated_exposure": "Prior F2a reviews (17, 18, 19, lead-audit) and reviews/convergence-*.json were read to select the "
        "probe set; HF-A1 and HF-A2 are the same defects those reviewers raised, so finding-selection is correlated with them. The "
        "pass/fail computation itself is a fresh machine run on bytes none of them reviewed, but this is not an independent discovery "
        "of a new defect.",
        "conflicts": "none declared; no shared text with the reviewed artifact or with the prior reviews",
    },
    "scope_limits": [
        "Structure, class binding and scope only: no physical truth claim, no citation verification, no proof check.",
        "The unresolved_items in the artifact are not resolved or accepted by this review.",
        "Per the map authority rule this is worker evidence, not a gate verdict; G-FORM remains pending until the controller/lead records it.",
        "An accept here is per-class F2a in isolation; G-FORM additionally needs F1/F2b accepts at one frozen hash.",
    ],
    "next_falsifier": pinned["next_falsifier"],
}

REVIEW_MD = f"""# W061-F2A-INDEP-REV-01 — independent review of F2a (AF-SCC-C2-VAC-GEN)

- Reviewer: worker-061 (not an author; no formulation artifact edited)
- Emitted: {NOW}
- Verdict: **accept**, score 4.0, hard failures: none
- Reviewed artifact: `schemas/af_scc_c2_vacuum.yaml` at sha256 `{H['schema']}`
  (pinned copy `pinned/af_scc_c2_vacuum.yaml`, revision 10)
- Canonical F0 taxonomy checked against: sha256 `{H['taxonomy']}` (binding fresh)
- Siblings compared: F1 `{H['f1'][:12]}`, F2b `{H['f2b'][:12]}`

## What was checked (machine evidence)

| probe | result |
|---|---|
| P1 identity/axes | pass |
| P2 extension_predicate, clauses (a)-(f), frozen axes (HF-A1) | pass — fixed at this revision |
| P3 D0/(s,delta) quantifier coherence vs canonical F0 (HF-A2) | pass at this revision |
| P4 canonical `check_class_schema.py` | pass, exit 0, no failed rules |
| P5 F0 declared-vs-measured hash binding | pass |
| P6 class-separation detector + 27-fixture regression | pass (17/17 leaks, 10/10 controls) |
| P7 F1/F2a/F2b restricting data-class concordance | pass (2 gloss-only diffs) |
| P8 conclusion direction / inflation guard | pass |

Full machine report: `probe_f2a_output.json`; gate stdout: `gate/check_class_schema_pinned.json`.

## Findings

""" + "\n".join(f"- {f}" for f in FINDINGS) + f"""

## Drift control (non-binding)

The canonical file changed while this review ran. The same probe set was rerun on the newest
canonical copies (F2a `{H['drift_schema'][:12]}` = rev11, F1 `{H['drift_f1'][:12]}`,
F2b `{H['drift_f2b'][:12]}`) and returned **accept** with no hard failures; the semantic
delta between the pinned rev10 and rev11 is the revision number only. This control does not
extend the binding verdict.

## Scope and authority

Structure/class-binding only. Unresolved mathematical items stay unresolved. This is worker
evidence: it does not set a node status, a `validation_status`, or a gate verdict.
"""

PINNED = {
    "task_id": "W061-F2A-INDEP-REV-01",
    "pinned_at": NOW,
    "note": "byte copies; canonical hashes measured at pin time",
    "paths": {
        "schemas/af_scc_c2_vacuum.yaml": {"pinned": "pinned/af_scc_c2_vacuum.yaml", "sha256": H["schema"]},
        "schemas/af_wcc_vacuum.yaml": {"pinned": "pinned/af_wcc_vacuum.yaml", "sha256": H["f1"]},
        "schemas/af_scc_c0_vacuum.yaml": {"pinned": "pinned/af_scc_c0_vacuum.yaml", "sha256": H["f2b"]},
        "research_map/formulation_taxonomy.yaml": {"pinned": "pinned/formulation_taxonomy.canonical.yaml", "sha256": H["taxonomy"]},
        "artifacts/formulation/tools/check_class_schema.py": {"pinned": "pinned/check_class_schema.py", "sha256": H["gate_tool"]},
        "research_map/class_separation.py": {"pinned": "pinned/class_separation.py", "sha256": H["classsep_tool"]},
    },
    "drift_at_emission": {
        "schemas/af_scc_c2_vacuum.yaml": H["drift_schema"],
        "schemas/af_wcc_vacuum.yaml": H["drift_f1"],
        "schemas/af_scc_c0_vacuum.yaml": H["drift_f2b"],
        "research_map/formulation_taxonomy.yaml": H["taxonomy"],
    },
}

CHECKPOINT = {
    "checkpoint_id": f"w061-cp1-{STAMP}",
    "task_id": "W061-F2A-INDEP-REV-01",
    "at": NOW,
    "node_id": "F2a",
    "class_id": "AF-SCC-C2-VAC-GEN",
    "status": "task_complete_pending_adjudication",
    "hours": 0.4,
    "artifact_hashes": {
        "REVIEW.json": None,  # filled below
        "probe_f2a_output.json": H["probe_out"],
        "pinned/af_scc_c2_vacuum.yaml": H["schema"],
        "gate/check_class_schema_pinned.json": H["gate_out"],
    },
    "verdict": "accept",
    "score": 4.0,
    "hard_failures": [],
    "claimed_node_status": None,
    "claimed_gate_verdict": None,
    "evidence_refs": REVIEW["evidence_refs"],
    "next_falsifier": REVIEW["next_falsifier"],
}

(HERE / "REVIEW.json").write_text(json.dumps(REVIEW, indent=2) + "\n")
(HERE / "REVIEW.md").write_text(REVIEW_MD)
(HERE / "PINNED.json").write_text(json.dumps(PINNED, indent=2) + "\n")

review_hash = sha(HERE / "REVIEW.json")
CHECKPOINT["artifact_hashes"]["REVIEW.json"] = review_hash
(HERE / "CHECKPOINT.json").write_text(json.dumps(CHECKPOINT, indent=2) + "\n")
checkpoint_hash = sha(HERE / "CHECKPOINT.json")

# ---- SHA256SUMS over the artifact tree (excluding caches and the manifest itself) ----
lines = []
for p in sorted(HERE.rglob("*")):
    if p.is_file() and "__pycache__" not in p.parts and p.name != "SHA256SUMS":
        lines.append(f"{sha(p)}  {p.relative_to(HERE)}")
(HERE / "SHA256SUMS").write_text("\n".join(lines) + "\n")

# ---- comms outbox events ---------------------------------------------------------
out = ROOT / "comms/outbox/worker-061.jsonl"
out.parent.mkdir(parents=True, exist_ok=True)
ev = [
    {
        "event_id": f"w061-{STAMP}-claim",
        "event_type": "status",
        "created_at": NOW,
        "actor": "worker-061",
        "node_id": "F2a",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "gate": "G-FORM",
        "task_id": "W061-F2A-INDEP-REV-01",
        "status": "active",
        "hours": 0.4,
        "summary": "Took one bounded class-bound task with no inbox assignment: independent machine-checked review of F2a "
                   "(AF-SCC-C2-VAC-GEN) at the pinned canonical bytes, probing HF-A1 (extension_predicate), HF-A2 "
                   "(D0/(s,delta) quantifier), the canonical structural gate, the F0 hash binding, class separation, and "
                   "F1/F2a/F2b restricting data-class concordance. Result: 8/8 probes pass; verdict accept at the pinned hash.",
        "evidence_refs": REVIEW["evidence_refs"],
        "next_falsifier": REVIEW["next_falsifier"],
        "reviewed_sha256": H["schema"],
    },
    {
        "event_id": f"w061-{STAMP}-artifact-review",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-061",
        "node_id": "F2a",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "artifact_type": "independent_review_json",
        "path": "artifacts/worker-061/f2a_independent_verdict/REVIEW.json",
        "sha256": review_hash,
        "validation_status": "unverified",
        "note": "Worker evidence, not a gate verdict and not a node completion claim; controller/lead adjudication required.",
    },
    {
        "event_id": f"w061-{STAMP}-artifact-probe",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-061",
        "node_id": "F2a",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "artifact_type": "machine_probe_output",
        "path": "artifacts/worker-061/f2a_independent_verdict/probe_f2a_output.json",
        "sha256": H["probe_out"],
        "validation_status": "unverified",
        "note": "Eight probes P1-P8 over the pinned bytes; rerunnable via probe_f2a.py.",
    },
    {
        "event_id": f"w061-{STAMP}-review",
        "event_type": "review",
        "created_at": NOW,
        "actor": "worker-061",
        "reviewer": "worker-061",
        "target_id": "F2a",
        "node_id": "F2a",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "gate": "G-FORM",
        "verdict": "accept",
        "score": 4.0,
        "hard_failures": [],
        "findings": FINDINGS,
        "reviewed_sha256": H["schema"],
        "evidence_refs": REVIEW["evidence_refs"],
        "independence": REVIEW["independence"],
        "scope_limits": REVIEW["scope_limits"],
        "drift_control": REVIEW["drift_control"],
        "next_falsifier": REVIEW["next_falsifier"],
    },
    {
        "event_id": f"w061-{STAMP}-final",
        "event_type": "status",
        "created_at": NOW,
        "actor": "worker-061",
        "node_id": "F2a",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "gate": "G-FORM",
        "task_id": "W061-F2A-INDEP-REV-01",
        "status": "active",
        "hours": 0.4,
        "summary": "Bounded task complete: REVIEW.json + probe evidence + CHECKPOINT.json written; review event emitted. "
                   "No node status, validation_status or gate verdict is claimed (worker authority rule). Canonical drift after "
                   "the pin is recorded and the accept binds only to the pinned hash.",
        "evidence_refs": [
            f"artifacts/worker-061/f2a_independent_verdict/REVIEW.json#sha256:{review_hash[:12]}",
            f"artifacts/worker-061/f2a_independent_verdict/CHECKPOINT.json#sha256:{checkpoint_hash[:12]}",
            f"comms/outbox/worker-061.jsonl#w061-{STAMP}-review",
        ],
        "next_falsifier": REVIEW["next_falsifier"],
    },
]
with out.open("a") as fh:
    for e in ev:
        fh.write(json.dumps(e, ensure_ascii=False) + "\n")

state = ROOT / "runtime/state"
state.mkdir(parents=True, exist_ok=True)
with (state / "w061_checkpoints.jsonl").open("a") as fh:
    fh.write(json.dumps(CHECKPOINT, ensure_ascii=False) + "\n")

print(json.dumps({
    "review_json_sha256": review_hash,
    "checkpoint_sha256": checkpoint_hash,
    "probe_schema_sha256": H["schema"],
    "events_appended": len(ev),
    "outbox": str(out),
}, indent=2))
