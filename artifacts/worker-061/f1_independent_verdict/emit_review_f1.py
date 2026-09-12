#!/usr/bin/env python3
"""Emit W061-F1-INDEP-REV-02 review artifacts, checkpoint, and comms events.

Reads the probe outputs already produced by probe_f1.py (binding run at the pin-time clock
reference plus a live recheck), writes REVIEW.json / REVIEW.md / PINNED.json / CHECKPOINT.json
/ SHA256SUMS, appends the upward events to comms/outbox/worker-061.jsonl, and appends a local
checkpoint line to runtime/state/w061_checkpoints.jsonl.

Append-only: it never edits or deletes existing comms traffic, and never writes
research_map/research_map.json or any formulation/literature artifact (worker authority rule).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
HERE = ROOT / "artifacts/worker-061/f1_independent_verdict"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")
STAMP = datetime.now(CST).strftime("%Y%m%dT%H%M%S")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


probe = json.loads((HERE / "probe_f1_output.json").read_text())
recheck = json.loads((HERE / "probe_f1_recheck.json").read_text())
control_files = sorted((HERE / "control").glob("gate_*.json"))

H = {
    "schema": sha(HERE / "pinned/af_wcc_vacuum.yaml"),
    "f2a": sha(HERE / "pinned/af_scc_c2_vacuum.yaml"),
    "f2b": sha(HERE / "pinned/af_scc_c0_vacuum.yaml"),
    "tax_canon": sha(HERE / "pinned/formulation_taxonomy.canonical.yaml"),
    "tax_author": sha(HERE / "pinned/formulation_taxonomy.authoring.yaml"),
    "frozen": sha(HERE / "pinned/FROZEN.json"),
    "gate_tool": sha(HERE / "pinned/check_class_schema.py"),
    "gate_spec": sha(HERE / "pinned/rule_spec.json"),
    "classsep": sha(HERE / "pinned/class_separation.py"),
    "probe_py": sha(HERE / "probe_f1.py"),
    "probe_out": sha(HERE / "probe_f1_output.json"),
    "probe_recheck": sha(HERE / "probe_f1_recheck.json"),
    "emit_py": sha(HERE / "emit_review_f1.py"),
}
for cf in control_files:
    H[f"control/{cf.name}"] = sha(cf)
for mf in sorted((HERE / "mutant").glob("*.yaml")):
    H[f"mutant/{mf.name}"] = sha(mf)

P = {p["id"]: p for p in probe["probes"]}
hard = probe["hard_failures"]
verdict = probe["verdict"]
score = probe["score"]

FINDINGS = [
    "F-01 HARD (P3; HF-06 class, independently reproduced at the pinned hash): the exact quantifier prefix and "
    "the conclusion block expand DIFFERENT visibility predicates. quantifiers.formal (schemas/af_wcc_vacuum.yaml:54-55) "
    "closes with 'not exists q in I+ with gamma subset J^-(q) intersect M' and quantifiers.domains.D5 (:79-81) defines q by "
    "'gamma([0,T)) is contained in the causal past J^-(q)' - both are WHOLE-CURVE single-q containment. The class's one canonical "
    "predicate, visibility.definition (:219-220), is the single-q TAIL predicate ('exists q in I+ AND t0 in [0,T) such that the "
    "TAIL gamma([t0,T)) is contained in J^-(q)'), and conclusion.statement_formal (:251) binds that predicate by name. "
    "Direction: whole-curve non-containment A is IMPLIED by tail non-containment B (a tail is a subset of the curve), so A is "
    "strictly weaker than the conclusion's negation; a development with a visible tail but no visible whole curve satisfies the "
    "formal expansion and violates the conclusion. The schema itself states the whole-curve reading 'would misclassify a geodesic "
    "that starts in the exterior and ends inside the black-hole region' (:220) and that single-q non-containment must not be "
    "replaced by B-containment (:227); class_identity_variants (:231-244) declares exactly ONE canonical predicate. "
    "quantifiers.negation (:85-88) negates the TAIL predicate, so quantifiers.formal and quantifiers.negation are not exact "
    "negations of each other. Probe P3 fail. Falsifier: state the tail form (with explicit t0) in quantifiers.formal and D5, which "
    "also restores formal/negation exactness.",
    "F-02 HARD (P4): D0, the domain of the first quantifier, is a disjunction ('Sobolev variant s > 5/2 and delta in (1/2,1), or "
    "the smooth-with-decay default', :65) while the binder is the pair (s,delta) and the quantified objects are pair-indexed "
    "(G_{s,delta}, X^{s,delta}_vac in quantifiers.formal; X^{s,delta}_vac in genericity.ambient_space). The smooth-with-decay branch "
    "has a Frechet ambient space and no (s,delta) values, so the binder is not well-typed over that branch; and the same leaf says "
    "the class 'is fixed at these values', which conflicts with quantifying over all of D0. evaluation_rubric.yaml:126 / G-FORM "
    "requires an exact quantifier prefix with no 'or'. Consequence: two competent readers can instantiate the class differently "
    "(all admissible regularity pairs vs one fixed regime), which is the artifact's own falsifier schema_falsifiers[0] (:282) firing "
    "on its own domain. Probe P4 fail. Falsifier: make D0 a single well-typed domain for (s,delta) (e.g. fix one regularity regime, "
    "or split the smooth case into its own class with its own binder).",
    "F-03 HARD (P5): the class-contract binding does not resolve inside the authoritative artifact. class_contract_pointer (:38) "
    "targets 'artifacts/formulation/formulation_taxonomy.yaml#class_contracts.AF-WCC-VAC-GEN'. The canonical "
    "research_map/formulation_taxonomy.yaml has no top-level class_contracts key (its structure is 'classes'); the authoring mirror "
    "artifacts/formulation/formulation_taxonomy.yaml does have class_contracts, and the two trees are divergent "
    f"(canonical {H['tax_canon'][:12]} vs authoring {H['tax_author'][:12]}). f0_binding.class_contract_supplement (:311) also points "
    "at the authoring copy. This independently reproduces worker-090 HF090-01 and worker-059 HF-3 at the pinned hash. Probe P5 fail. "
    "Falsifier: repoint the pointer and supplement at research_map/formulation_taxonomy.yaml#classes.AF-WCC-VAC-GEN (or publish the "
    "two trees byte-identically).",
    "F-04 HARD (P6): the canonical bytes carry 7 duplicate top-level YAML mapping keys: revised_at x7 (:8,:10,:12,:14,:16,:20,:23) "
    "and revised_at_unused x2 (:26,:28). yaml.safe_load silently keeps the last value (revision: 11 survives, six of seven revision "
    "timestamps do not); a strict loader raises ConstructorError at line 10. Consequence: the revision history of a 'frozen' artifact "
    "is not machine-readable, and a conforming strict parser rejects the document. Probe P6 fail. Falsifier: replace the duplicate "
    "keys with a single 'revised_at' plus a 'revision_log' list.",
    "F-05 SOFT / PROCESS (P7; CF-14 class): at the pin-time clock reference 2026-09-12T00:27:29+08:00 the declared "
    "revised_at (:23) was 2026-09-12T00:30:00+08:00, i.e. 151 s ahead of the review clock. The defect is self-expiring: the live "
    "recheck after 00:30 finds no future-dated timestamp. Recorded as a process finding, not a blocking hard failure. Falsifier: no "
    "declared timestamp ahead of the clock at measurement time.",
    "F-06 FINDING / ACTIONABLE (P9; causal control, this review's main new signal): the binding canonical structural gate "
    "(artifacts/formulation/tools/check_class_schema.py, pinned sha256 000e09e4..., rule spec pinned sha256 "
    f"{H['gate_spec'][:12]}) has ZERO discriminating power on the visibility-predicate axis. It returns pass/exit 0 with "
    "failed_rules=[] on (i) the pinned canonical bytes, which carry the F-01 contradiction; (ii) mutant M0, which applies the "
    "substitution visibility.must_not_conflate explicitly forbids (single-q non-containment -> B-containment, B = M minus J^-(I+)); "
    "(iii) mutant M1, which substitutes the registered variant SET reading for the one canonical single-q tail predicate "
    "(class_identity_variants says the two 'must never be interchanged'); and (iv) the tail-consistent repair M2. Three of those four "
    "documents differ only in the semantics the gate is supposed to police, so the gate cannot detect a documented class-identity or "
    "must_not_conflate violation. This is consistent with the gate's own docstring ('no check that the mathematics in a definition is "
    "correct, only that it is present, non-vague and class-consistent'). Needed to unblock: a rule that resolves the predicate named "
    "in conclusion.statement_formal (visible_singularity_from_I_plus), extracts its definition, and requires quantifiers.formal, "
    "quantifiers.negation and the D5 definition to agree on the tail-vs-whole form; M0 and M1 are ready-made NEG fixtures. "
    "Probe P9 fail (soft flag: it is a finding about the gate, not a defect of the schema text).",
    "F-07 POSITIVE (P1): exactly one top-level class_id AF-WCC-VAC-GEN; class_components AF/WCC/VAC/GEN with no regularity token; "
    "conclusion_type=weak_cosmic_censorship, family WCC; no SCC / C0 / C2 / inextendibility token anywhere on the assertive "
    "conclusion surface. Probe P1 pass.",
    "F-08 POSITIVE (P2): every G-FORM-required block is present - quantifiers.formal/ordered/negation/negation_normal_form, domains "
    "D0-D5, order_matters, topology (4D, one-ended AF slice, I+ = R x S^2), data_class, regularity, genericity "
    "(residual_comeager, is_part_of_class true), i_plus.role=conclusion, visibility.role=conclusion, conclusion, two-tier falsifier, "
    "anti_scope. Probe P2 pass.",
    "F-09 POSITIVE (P8): the canonical gate returns pass on the pinned bytes (exit 0, failed_rules []). Recorded as the contrast "
    "that makes F-06 causal: same gate, same bytes, semantic contradiction present. Probe P8 pass.",
    "F-10 POSITIVE (P10): research_map/class_separation.py finds nothing on the pinned F1 text and runtime/bin/classsep_regression.py "
    "still scores leaks 17/17, controls 10/10. The F-01/F-02 defects are semantic, not token-level leaks, so the class-separation "
    "layer is not the right control for them. Probe P10 pass.",
    "F-11 POSITIVE, WITH CAVEAT (P11): F1/F2a/F2b agree on all 12 restricting data-class paths at the pinned triple (matter, Lambda, "
    "equations, both constraints, default regularity, s, delta, both decay rates, symmetry, ADM sign); the two remaining differences "
    "are gloss-only (weighted-Sobolev label, parity-clause prose). Caveat preserved rather than collapsed: D0 is disjunctive in all "
    "three classes, so the strong reading of 'one frozen data class' (s,delta,norm) is still unmet (W037-F5); path-equality does not "
    "discharge the transfer precondition by itself. Probe P11 pass.",
    "F-12 POSITIVE (P12): f0_binding.declared_f0_sha256 equals the measured canonical taxonomy hash "
    f"{H['tax_canon'][:12]} at pin time, and the FROZEN.json rev25 entry for schemas/af_wcc_vacuum.yaml equals the pinned F1 hash "
    f"{H['schema'][:12]}. Drift window: F1, F2a, F2b and the canonical taxonomy were byte-stable from pin (00:25:50) through the "
    "recheck; F1 was NOT churning during this review window (unlike the 00:18-00:19 window reported by worker-037/worker-059). "
    "Probe P12 pass; see drift_window in the probe output.",
]

REVIEW = {
    "task_id": "W061-F1-INDEP-REV-02",
    "created_at": NOW,
    "reviewer": "worker-061",
    "target": {"node_id": "F1", "class_id": "AF-WCC-VAC-GEN", "gate": "G-FORM",
               "artifact": "schemas/af_wcc_vacuum.yaml", "sha256": H["schema"],
               "revision_field": 11, "bytes": (HERE / "pinned/af_wcc_vacuum.yaml").stat().st_size},
    "measurement": probe["measurement"],
    "independence": {
        "author_of_target": "astra-lead-formulation",
        "reviewer_authored_target": False,
        "shares_text_with_other_verdicts": False,
        "note": "own probe implementation; no canonical-gate code imported into the semantic checks "
                "(the gate is invoked as a black box for the P8/P9 contrast only)",
    },
    "pinned": probe["pinned"],
    "drift_window": probe["drift_window"],
    "probes": probe["probes"],
    "hard_failures": hard,
    "verdict": verdict,
    "score": score,
    "findings": FINDINGS,
    "next_falsifier": probe["next_falsifier"],
    "authority_note": probe["authority_note"],
    "artifacts": {
        "review_json": "artifacts/worker-061/f1_independent_verdict/REVIEW.json",
        "probe_output_binding": "artifacts/worker-061/f1_independent_verdict/probe_f1_output.json",
        "probe_output_live_recheck": "artifacts/worker-061/f1_independent_verdict/probe_f1_recheck.json",
        "probe_script": "artifacts/worker-061/f1_independent_verdict/probe_f1.py",
        "pinned_schema": "artifacts/worker-061/f1_independent_verdict/pinned/af_wcc_vacuum.yaml",
        "gate_blindness_controls": [f"artifacts/worker-061/f1_independent_verdict/control/{p.name}"
                                    for p in control_files],
        "mutants": [f"artifacts/worker-061/f1_independent_verdict/mutant/{p.name}"
                    for p in sorted((HERE / "mutant").glob("*.yaml"))],
    },
}
(HERE / "REVIEW.json").write_text(json.dumps(REVIEW, indent=2, default=str) + "\n")

md = [
    "# W061-F1-INDEP-REV-02 — independent consistency review of F1 (`AF-WCC-VAC-GEN`)",
    "",
    f"- **Target**: `schemas/af_wcc_vacuum.yaml` @ `{H['schema']}` (rev field 11, "
    f"{(HERE / 'pinned/af_wcc_vacuum.yaml').stat().st_size} bytes), node **F1**, gate **G-FORM**",
    f"- **Verdict**: **{verdict}**, score **{score}**, hard failures **{len(hard)}**",
    f"- **Measurement**: pin 2026-09-12T00:25:50+08:00; probes referenced to "
    f"{probe['measurement']['t_start_reference']}; live recheck {recheck['measurement']['t_run']}",
    f"- **Drift window stable**: {probe['drift_window']['stable']} (F1/F2a/F2b/canonical taxonomy unchanged)",
    "",
    "## Hard failures",
    "",
]
for fid in hard:
    md.append(f"- **{fid}** — {P[fid]['title']}")
md += ["", "## Probes", "", "| probe | status | hard | meaning |", "|---|---|---|---|"]
for p in probe["probes"]:
    md.append(f"| {p['id']} | {p['status']} | {'yes' if p['hard'] else 'no'} | {p['title'][:110]} |")
md += ["", "## Findings", ""]
for f in FINDINGS:
    md.append(f"- {f}")
md += ["", "## Next falsifier", "", probe["next_falsifier"], "",
       "## Authority", "", probe["authority_note"], ""]
(HERE / "REVIEW.md").write_text("\n".join(md))

PINNED = {
    "task_id": "W061-F1-INDEP-REV-02",
    "at": NOW,
    "pin_time": "2026-09-12T00:25:50+08:00",
    "files": {k: {"path": v["path"], "sha256": v["sha256"]} for k, v in probe["pinned"].items()},
    "control_and_mutant_hashes": {k: v for k, v in H.items()
                                  if k.startswith("control/") or k.startswith("mutant/")},
    "probe_hashes": {"probe_f1.py": H["probe_py"],
                     "probe_f1_output.json": H["probe_out"],
                     "probe_f1_recheck.json": H["probe_recheck"]},
}
(HERE / "PINNED.json").write_text(json.dumps(PINNED, indent=2, default=str) + "\n")

CHECKPOINT = {
    "checkpoint_id": f"w061-cp2-{STAMP}",
    "task_id": "W061-F1-INDEP-REV-02",
    "at": NOW,
    "node_id": "F1",
    "class_id": "AF-WCC-VAC-GEN",
    "gate": "G-FORM",
    "status": "task_complete_pending_adjudication",
    "hours": 0.5,
    "artifact_hashes": {
        "REVIEW.json": sha(HERE / "REVIEW.json"),
        "probe_f1_output.json": H["probe_out"],
        "probe_f1_recheck.json": H["probe_recheck"],
        "pinned/af_wcc_vacuum.yaml": H["schema"],
        "gate/gate_pinned.json": sha(HERE / "gate/gate_pinned.json"),
        "control/gate_M0-B-CONTAINMENT.json": H.get("control/gate_M0-B-CONTAINMENT.json"),
        "control/gate_M1-VARIANT-SET-READING.json": H.get("control/gate_M1-VARIANT-SET-READING.json"),
        "control/gate_M2-TAIL-CONSISTENT-REPAIR.json": H.get("control/gate_M2-TAIL-CONSISTENT-REPAIR.json"),
    },
    "verdict": verdict,
    "score": score,
    "hard_failures": hard,
    "claimed_node_status": None,
    "claimed_gate_verdict": None,
    "evidence_refs": [
        f"artifacts/worker-061/f1_independent_verdict/pinned/af_wcc_vacuum.yaml#sha256:{H['schema'][:12]}",
        f"artifacts/worker-061/f1_independent_verdict/probe_f1_output.json#sha256:{H['probe_out'][:12]}",
        f"artifacts/worker-061/f1_independent_verdict/control/gate_M0-B-CONTAINMENT.json#sha256:"
        f"{H.get('control/gate_M0-B-CONTAINMENT.json', '')[:12]}",
        f"artifacts/worker-061/f1_independent_verdict/mutant/M0_B_containment.yaml#sha256:"
        f"{H.get('mutant/M0_B_containment.yaml', '')[:12]}",
        f"artifacts/worker-061/f1_independent_verdict/pinned/formulation_taxonomy.canonical.yaml#sha256:{H['tax_canon'][:12]}",
        f"artifacts/worker-061/f1_independent_verdict/pinned/formulation_taxonomy.authoring.yaml#sha256:{H['tax_author'][:12]}",
    ],
    "next_falsifier": probe["next_falsifier"],
}
(HERE / "CHECKPOINT.json").write_text(json.dumps(CHECKPOINT, indent=2, default=str) + "\n")

# ---- SHA256SUMS -------------------------------------------------------------
lines = []
for p in sorted(HERE.rglob("*")):
    if p.is_file() and p.name != "SHA256SUMS":
        lines.append(f"{sha(p)}  {p.relative_to(HERE)}")
(HERE / "SHA256SUMS").write_text("\n".join(lines) + "\n")

# ---- upward events ----------------------------------------------------------
OUTBOX = ROOT / "comms/outbox/worker-061.jsonl"


def ev(eid, etype, **kw):
    return {"event_id": eid, "event_type": etype, "created_at": NOW, "actor": "worker-061", **kw}


EVID = [
    f"artifacts/worker-061/f1_independent_verdict/pinned/af_wcc_vacuum.yaml#sha256:{H['schema'][:12]}",
    f"artifacts/worker-061/f1_independent_verdict/probe_f1_output.json#sha256:{H['probe_out'][:12]}",
    f"artifacts/worker-061/f1_independent_verdict/gate/gate_pinned.json#sha256:{sha(HERE / 'gate/gate_pinned.json')[:12]}",
    f"artifacts/worker-061/f1_independent_verdict/control/gate_M0-B-CONTAINMENT.json#sha256:"
    f"{H.get('control/gate_M0-B-CONTAINMENT.json','')[:12]}",
    f"artifacts/worker-061/f1_independent_verdict/control/gate_M1-VARIANT-SET-READING.json#sha256:"
    f"{H.get('control/gate_M1-VARIANT-SET-READING.json','')[:12]}",
    f"artifacts/worker-061/f1_independent_verdict/pinned/formulation_taxonomy.canonical.yaml#sha256:{H['tax_canon'][:12]}",
    f"artifacts/worker-061/f1_independent_verdict/pinned/formulation_taxonomy.authoring.yaml#sha256:{H['tax_author'][:12]}",
    f"artifacts/worker-061/f1_independent_verdict/probe_f1.py#sha256:{H['probe_py'][:12]}",
]

events = [
    ev(f"w061-f1-{STAMP}-claim", "status", node_id="F1", class_id="AF-WCC-VAC-GEN", gate="G-FORM",
       task_id="W061-F1-INDEP-REV-02", status="active", hours=0.5,
       summary=("No assignment card exists in comms/inbox for worker-061. Took one bounded class-bound task: independent "
                "machine-checked consistency review of F1 (AF-WCC-VAC-GEN) at the pinned canonical bytes "
                f"{H['schema'][:12]}, against the pinned canonical F0 taxonomy and F2a/F2b siblings, plus a causal "
                "gate-blindness control. Result: verdict revise, score 2.5, 4 hard failures (visibility-predicate "
                "inconsistency in quantifiers.formal/D5 vs the canonical tail predicate; disjunctive (s,delta) D0 under the "
                "A0 exact-prefix rule; class_contract_pointer resolving only in the divergent authoring tree; 7 duplicate "
                "top-level YAML keys)."),
       evidence_refs=EVID, next_falsifier=probe["next_falsifier"]),
    ev(f"w061-f1-{STAMP}-artifact-review", "artifact", node_id="F1", class_id="AF-WCC-VAC-GEN",
       artifact_type="independent_review_json",
       path="artifacts/worker-061/f1_independent_verdict/REVIEW.json",
       sha256=sha(HERE / "REVIEW.json"), validation_status="unverified",
       note="Worker evidence, not a gate verdict and not a node completion claim; controller/lead adjudication required."),
    ev(f"w061-f1-{STAMP}-artifact-probe", "artifact", node_id="F1", class_id="AF-WCC-VAC-GEN",
       artifact_type="machine_probe_output",
       path="artifacts/worker-061/f1_independent_verdict/probe_f1_output.json",
       sha256=H["probe_out"], validation_status="unverified",
       note=("12 probes P1-P12 over the pinned bytes, binding run referenced to the pin-time clock; rerunnable via "
             "probe_f1.py. Live recheck without the clock reference: "
             "artifacts/worker-061/f1_independent_verdict/probe_f1_recheck.json "
             f"sha256:{H['probe_recheck'][:12]}.")),
    ev(f"w061-f1-{STAMP}-artifact-control", "artifact", node_id="F1", class_id="AF-WCC-VAC-GEN",
       artifact_type="gate_blindness_control_set",
       path="artifacts/worker-061/f1_independent_verdict/mutant/M0_B_containment.yaml",
       sha256=H.get("mutant/M0_B_containment.yaml", ""), validation_status="unverified",
       note=("M0/M1/M2 mutants + their canonical-gate reports under control/. The gate passes all three and the pinned "
             "bytes, so it has no rule on the visibility-predicate axis; M0/M1 are ready-made NEG fixtures.")),
    ev(f"w061-f1-{STAMP}-review", "review", reviewer="worker-061", target_id="F1", node_id="F1",
       class_id="AF-WCC-VAC-GEN", gate="G-FORM", artifact="schemas/af_wcc_vacuum.yaml",
       artifact_sha256=H["schema"], verdict=verdict, score=score,
       hard_failures=[f"{fid}: {P[fid]['title']}" for fid in hard],
       findings=FINDINGS,
       next_falsifier=probe["next_falsifier"],
       authority_note=probe["authority_note"]),
    ev(f"w061-f1-{STAMP}-final", "status", node_id="F1", class_id="AF-WCC-VAC-GEN", gate="G-FORM",
       task_id="W061-F1-INDEP-REV-02", status="active", hours=0.5,
       summary=("Bounded task complete: REVIEW.json/REVIEW.md + PINNED.json + CHECKPOINT.json + rerunnable probe + "
                "gate-blindness controls written and hashed; review event emitted. No node status, validation_status or "
                "gate verdict claimed (worker authority rule). The revise binds only to the pinned hash "
                f"{H['schema'][:12]}; the drift window was stable."),
       evidence_refs=EVID, next_falsifier=probe["next_falsifier"]),
]
with OUTBOX.open("a") as fh:
    for e in events:
        fh.write(json.dumps(e, default=str) + "\n")

with (ROOT / "runtime/state/w061_checkpoints.jsonl").open("a") as fh:
    fh.write(json.dumps(CHECKPOINT, default=str) + "\n")

print(json.dumps({
    "task_id": REVIEW["task_id"], "verdict": verdict, "score": score, "hard_failures": hard,
    "review_sha256": sha(HERE / "REVIEW.json"),
    "events_appended": len(events),
    "review_json": str(HERE / "REVIEW.json"),
}, indent=2))
