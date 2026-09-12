#!/usr/bin/env python3
"""Emit W056-SET-DIRECTION-SENSE-01 events to comms/outbox/worker-056.jsonl and write
runtime/state/w056_checkpoint_4.json (+ w056_checkpoints.jsonl).

Idempotent: event_ids already present in the outbox are skipped. Reads its own artifact
hashes from SHA256SUMS so the events always carry the measured hashes; no shared state
other than the outbox and the checkpoint files is written.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CST = timezone(timedelta(hours=8))
OUTBOX = ROOT / "comms/outbox/worker-056.jsonl"
STATE = ROOT / "runtime/state"
TASK = "W056-SET-DIRECTION-SENSE-01"
CLASS = "AF-WCC-VAC-GEN"
NODES = ["F1", "F0"]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def h12(p: str) -> str:
    return f"{p}#{sha(ROOT / p)[:12]}"


report = json.loads((HERE / "report.json").read_text())
sums = (HERE / "SHA256SUMS").read_text().strip().splitlines()
arts = {}
for line in sums:
    h, name = line.split()
    arts[name] = h
sums_hash = sha(HERE / "SHA256SUMS")

EVID = [
    h12("artifacts/worker-056/set_direction_sense/report.json"),
    h12("artifacts/worker-056/set_direction_sense/run_sense_audit_056.py"),
    h12("artifacts/worker-056/set_direction_sense/README.md"),
    h12("artifacts/worker-056/set_direction_sense/emit_events.py"),
    h12("artifacts/worker-056/set_direction_sense/SHA256SUMS"),
    h12("artifacts/worker-056/set_direction_sense/hygiene/removed_events.jsonl"),
    h12("artifacts/worker-056/set_direction_sense/hygiene/NOTE.json"),
    "research_map/formulation_taxonomy.yaml#0abb9ed8a961",
    "artifacts/formulation/formulation_taxonomy.yaml#d7419b4e8963",
    "artifacts/formulation/VARIANT_REGISTRY.json#6bac9adea19e",
    "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json#64b8d6394a04",
    "schemas/af_wcc_vacuum.yaml#d9cebb9404b2",
    "reviews/G-FORM-visdir-residual-086.json#3d5afeb086c9",
    "artifacts/worker-086/visdir_repair_loc/report.json#9dc536368aea",
]
FALSIFIER = report["falsifier"]

now = datetime.now(CST).isoformat(timespec="seconds")
stamp = datetime.now(CST).strftime("%Y%m%dT%H%M%S")
ts = now


def ev(event_id, event_type, **kw):
    return {"event_id": event_id, "event_type": event_type, "created_at": ts,
            "actor": "worker-056", "class_id": CLASS, "class_ids": [CLASS],
            "node_id": "F1", "node_ids": NODES, "gate": "G-FORM", **kw}


events = []

events.append(ev(
    f"w056-{stamp}-sds-take", "status",
    status="active", hours=0.1,
    summary=("No inbox card exists for worker-056 (fleet relaunched 2026-09-12T00:58). Took ONE bounded "
             "class-bound task: W056-SET-DIRECTION-SENSE-01, node F1 / class AF-WCC-VAC-GEN / gate G-FORM. "
             "Type the SET 'strictly stronger/weaker' claims by sense (visibility predicate vs censorship "
             "conclusion) at the five L-FORM-03 locations, with a machine-checked order-theoretic model, a "
             "clause-typed census and controls. Read-only: no canonical, ledger, numerics or frozen file "
             "written by this task."),
    evidence_refs=EVID, next_falsifier=FALSIFIER))

for name, atype in [("report.json", "analysis_report"),
                    ("run_sense_audit_056.py", "runner"),
                    ("README.md", "readme"),
                    ("emit_events.py", "event_emitter"),
                    ("SHA256SUMS", "manifest"),
                    ("hygiene/removed_events.jsonl", "emission_hygiene_evidence"),
                    ("hygiene/NOTE.json", "emission_hygiene_note")]:
    p = f"artifacts/worker-056/set_direction_sense/{name}"
    events.append(ev(
        f"w056-{stamp}-sds-art-{name.replace('.', '-')}", "artifact",
        node_id="F1", artifact_type=atype, path=p, sha256=sha(ROOT / p),
        validation_status="unverified",
        summary=f"{TASK} artifact {name}",
        evidence_refs=[f"{p}#{sha(ROOT / p)[:12]}", "runtime/state/w056_checkpoint_4.json"],
        next_falsifier=FALSIFIER))

events.append(ev(
    f"w056-{stamp}-sds-claim", "claim",
    statement=("At pinned F1 rev13 (schemas/af_wcc_vacuum.yaml d9cebb9404b2e79e) and the rev29 formulation "
               "artifacts, every live SET-direction claim is sense-dependent and both directions are TRUE of "
               "different objects: as a VISIBILITY PREDICATE Vis_set is strictly WEAKER (Vis_tail => Vis_set, "
               "0 violations in 29,736 finite predicate cases over preorders on <=4 points; the omega-chain "
               "model has Vis_set and not Vis_tail); as a CENSORSHIP CONCLUSION 'no Vis_set-singularity' is "
               "strictly STRONGER (it entails the parent's 'no Vis_tail-singularity' by contraposition, and the "
               "omega world with the chain as its only curve has C_parent true / C_set false). A clause-typed "
               "census of the five L-FORM-03 locations (plus one live downstream carrier) finds ZERO direction "
               "tokens that are false in the sense their own clause types: F0 canonical :200 is untyped/"
               "ambiguous and TRUE conclusion-level; supplement :176 attaches the token to the negated "
               "outside-the-union statement (TRUE) but mislabels the row 'visibility ='; VARIANT_REGISTRY.json:57 "
               "and the SET delta :11 are predicate-typed TRUE but variant-level incomplete; the SET delta :22 is "
               "correctly predicate-typed. Residual is a sense-typing/annotation defect, not a surviving "
               "inversion."),
    conclusion_type="formal_model",
    assumptions=[
        "causal structure modelled as a reflexive-transitive preorder with J^-(q) past-closed",
        "causal geodesic images modelled as chains of length >= 2",
        "the omega model is the direct limit of the machine-checked finite prefixes N in {8,24,64} plus the "
        "stated unboundedness lemma (no machine enumeration of the infinite object)",
        "sense classification is rule-based on the clause that carries the direction token; rule set, local "
        "clauses and five controls are in report.json",
    ],
    falsifier=FALSIFIER,
    artifact_refs=[f"artifacts/worker-056/set_direction_sense/{n}#{h[:12]}" for n, h in arts.items()],
    evidence_refs=EVID, scope="direction-sense typing only; no gate verdict, no node completion",
    next_falsifier=FALSIFIER))

events.append(ev(
    f"w056-{stamp}-sds-review-lform03", "review",
    target_id="L-FORM-03", reviewer="worker-056", verdict="revise", score=3.0,
    hard_failures=[],
    findings=[
        {"id": "W056-SDS-R1", "kind": "scope_correction", "severity": "major",
         "statement": ("L-FORM-03's five residual locations are re-measured: none carries a direction token that "
                       "is false in the sense its own clause types. Re-scope the blocker from 'inverted SET "
                       "direction survives' to 'sense-typing/annotation defect'. The F0 canonical :200 sentence "
                       "is TRUE under the conclusion-level reading (SET conclusion entails the parent "
                       "conclusion) and false only under the predicate-level reading; because the parenthetical "
                       "defines the predicate while the noun 'reading' is untyped, 'AMBIGUOUS' is the honest "
                       "classification. Do NOT edit :200 on this evidence: a write voids G-F0/REC-11 for an "
                       "ambiguity."),
         "evidence": ["artifacts/worker-056/set_direction_sense/report.json#8f9b54d117a3"]},
        {"id": "W056-SDS-R2", "kind": "transfer_hazard", "severity": "major",
         "statement": ("Because C_set => C_parent, a theorem proved for variant SET transfers TO "
                       "AF-WCC-VAC-GEN, while a parent-class theorem does NOT transfer to the variant. The "
                       "variant-level `strength` fields (VARIANT_REGISTRY.json:57, SET delta :11) say only "
                       "'strictly weaker', which inverts the transfer direction if read conclusion-level. "
                       "Repair = add the dual sentence, no class id / hypothesis / predicate change. The same "
                       "untyped phrasing already appears in reviews/G-FORM-visdir-residual-086.json:33 "
                       "(SET-DIR-09), so the gap is live, not hypothetical."),
         "evidence": ["artifacts/worker-056/set_direction_sense/report.json#8f9b54d117a3",
                      "artifacts/formulation/VARIANT_REGISTRY.json#6bac9adea19e",
                      "reviews/G-FORM-visdir-residual-086.json#3d5afeb086c9"]},
        {"id": "W056-SDS-R3", "kind": "corroboration_extension", "severity": "minor",
         "statement": ("Corroborates worker-086 F-086-V5 on the D1 supplement row and extends it: the token at "
                       ":176 attaches to 'lies outside J^-(I+) as a SET', i.e. the negation, and is TRUE even at "
                       "negation level; the defect is the 'visibility =' label, not the direction. Relabel, do "
                       "not flip. Independently reproduces worker-086 F-086-V1's order-theoretic result "
                       "(T1 equivalence 0/29,736 here; T2/T4 separation)."),
         "evidence": ["artifacts/worker-056/set_direction_sense/report.json#8f9b54d117a3",
                      "reviews/G-FORM-visdir-residual-086.json#3d5afeb086c9",
                      "artifacts/worker-086/visdir_repair_loc/report.json#9dc536368aea"]},
    ],
    evidence_refs=EVID,
    counts_as_full_schema_verdict=False, counts_as_independent=True,
    scope="adjudication input on the L-FORM-03 residual characterization only; not a gate verdict",
    next_falsifier=FALSIFIER))

events.append(ev(
    f"w056-{stamp}-sds-review-registry", "review",
    target_id="artifacts/formulation/VARIANT_REGISTRY.json#6bac9adea19e",
    reviewer="worker-056", verdict="revise", score=3.0, hard_failures=[],
    findings=[
        {"id": "W056-SDS-R4", "kind": "sense_incomplete", "severity": "major",
         "statement": ("Variant SET's `strength` field is correctly predicate-typed ('the parent's single-q tail "
                       "predicate entails the union reading') but is the only variant-level strength summary and "
                       "is silent on the conclusion direction, which is strictly STRONGER. Recommended repair: "
                       "'strictly weaker as a visibility predicate; strictly stronger as a censorship conclusion "
                       "(SET entails AF-WCC-VAC-GEN)'. Same change in "
                       "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json:11. No class id, "
                       "hypothesis, predicate or frozen byte needs to change for this repair."),
         "evidence": ["artifacts/worker-056/set_direction_sense/report.json#8f9b54d117a3",
                      "artifacts/formulation/VARIANT_REGISTRY.json#6bac9adea19e",
                      "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json#64b8d6394a04"]},
    ],
    evidence_refs=EVID,
    counts_as_full_schema_verdict=False, counts_as_independent=True,
    scope="variant-level strength field only; order-theoretic result independently reproduced",
    next_falsifier=FALSIFIER))

existing = set()
if OUTBOX.exists():
    for line in OUTBOX.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            existing.add(json.loads(line)["event_id"])
        except Exception:
            pass


def logical(eid: str) -> str:
    """Task-local id without the emission timestamp, so a re-run that only changes the
    clock cannot duplicate an already-emitted event."""
    return eid.split("-sds-", 1)[1] if "-sds-" in eid else eid


existing_logical = {logical(eid) for eid in existing}
new = [e for e in events if logical(e["event_id"]) not in existing_logical]
with OUTBOX.open("a", encoding="utf-8") as fh:
    for e in new:
        fh.write(json.dumps(e, sort_keys=True) + "\n")

# ------------------------------------------------------------- checkpoint ----
STATE.mkdir(parents=True, exist_ok=True)
ckpt = {
    "worker": "worker-056", "checkpoint": 4, "at": ts, "task_id": TASK,
    "node": "F1", "class": CLASS, "gate": "G-FORM", "hours_spent_estimate": 0.4,
    "verdict": report["verdict"],
    "artifacts": {f"artifacts/worker-056/set_direction_sense/{n}": h for n, h in arts.items()},
    "model": {
        "predicate_cases": report["model"]["finite_census"]["predicate_cases"],
        "worlds": report["model"]["finite_census"]["worlds"],
        "T1_violations": report["model"]["T1_fixed_q_whole_iff_tail"]["violations"],
        "T2_violations": report["model"]["T2_tail_implies_set"]["violations"],
        "T3_violations": report["model"]["T3_finite_Iplus_no_separation"]["violations"],
        "Cset_not_Cparent": report["model"]["finite_census"]["Cset_not_Cparent"],
        "controls_all_pass": report["controls"]["all_pass"],
        "inputs_stable": not report["drift"],
    },
    "census_verdicts": {r["row_id"]: r["verdict"] for r in report["census_rows"]},
    "events_emitted": sorted(eid for eid in (existing | {e["event_id"] for e in new}) if "-sds-" in eid),
    "authority": ("worker evidence only; cannot set status=done, validation_status=passed or any gate "
                  "verdict; no canonical, ledger, numerics or frozen file written"),
}
ck_path = STATE / "w056_checkpoint_4.json"
ck_path.write_text(json.dumps(ckpt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
with (STATE / "w056_checkpoints.jsonl").open("a", encoding="utf-8") as fh:
    fh.write(json.dumps({**ckpt, "artifacts": {k: v for k, v in ckpt["artifacts"].items()}},
                        sort_keys=True) + "\n")
ck_hash = sha(ck_path)

final = ev(
    f"w056-{stamp}-sds-complete", "status",
    status="active", hours=0.4,
    summary=(f"{TASK} complete at worker level: 7 artifacts/evidence files on disk and hash-pinned "
             f"(report {arts['report.json'][:12]}, runner {arts['run_sense_audit_056.py'][:12]}, "
             f"README {arts['README.md'][:12]}, emitter {arts['emit_events.py'][:12]}, "
             f"SHA256SUMS {sums_hash[:12]}); checkpoint runtime/state/w056_checkpoint_4.json"
             f"#{ck_hash[:12]}. Verdict MODEL_OK / CONTROLS_PASS / INPUTS_STABLE. Result: SET is strictly "
             "weaker as a visibility predicate and strictly stronger as a censorship conclusion; zero of the "
             "five L-FORM-03 locations carries a token false in its own clause-typed sense, so L-FORM-03 "
             "should be re-scoped to a sense-typing defect and F0 canonical :200 must not be edited. Worker "
             "exits now; no gate verdict, no node status, no canonical artifact modified."),
    evidence_refs=[f"runtime/state/w056_checkpoint_4.json#{ck_hash[:12]}"] + EVID,
    next_falsifier=FALSIFIER)
if logical(final["event_id"]) not in (existing_logical | {logical(e["event_id"]) for e in new}):
    with OUTBOX.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(final, sort_keys=True) + "\n")
    new.append(final)

print(f"appended {len(new)} events")
for e in new:
    print(" ", e["event_id"], e["event_type"])
print("checkpoint", ck_path, ck_hash[:12])
