#!/usr/bin/env python3
"""Astra independent controller lifecycle (one pass, then exit).

Runs under the same exclusive flock as run_cycle.py so a manual controller pass and
the 15-minute loop can never interleave a read-modify-write on research_map.json.

Duties discharged in this pass:
  1. consume comms + artifacts  (ingest -> apply_events)
  2. maintain the DAG           (split F2 -> F2a/F2b; retire the merged class artifact)
  3. maintain the gates         (criteria/verdict/unmet/owner/ETA, repoint dangling refs)
  4. keep numerics gated        (numerics_lock stays locked; N1 must stay queued)
  5. record hashes/validation   (measured sha256; honest validation_status)
  6. issue bounded assignments  (5 cards -> comms/inbox + map.assignments)
  7. checkpoint

Idempotent: guarded by controller_findings CF-7..CF-9 and assignment event_ids.

  python3 runtime/bin/astra_lifecycle_independent.py --dry-run
  python3 runtime/bin/astra_lifecycle_independent.py --apply --label astra-indep-1
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "research_map"))
import comms  # noqa: E402
import apply_events  # noqa: E402
import promote  # noqa: E402
import accounting  # noqa: E402
import checkpoint  # noqa: E402

CST = timezone(timedelta(hours=8))
LOCK = ROOT / "runtime" / "state" / "map.lock"
MAP = ROOT / "research_map" / "research_map.json"

RUN = "run-2026-09-12T00:00+08:00"
DEADLINE = "2026-09-12T03:15+08:00"
LOCK_NOTE = ("numerics_lock is LOCKED: no self-gravitating solver, no N1 work, "
             "do not create numerics/spherical_solver/. N0 flat-space calibration only.")


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def node_index(m):
    return {n["id"]: (g, n) for g in m["groups"] for n in g["nodes"]}


# --------------------------------------------------------------------------- edits
def split_f2(m, measured):
    """F2 currently declares the merged artifact schemas/af_scc_regularities.yaml.
    Replace it with two class-bound nodes at the canonical paths that already carry
    independent reviewer verdicts. Idempotent."""
    g = next(g for g in m["groups"] if g["id"] == "formulation")
    idx = {n["id"]: i for i, n in enumerate(g["nodes"])}
    if "F2a" in idx and "F2b" in idx:
        return False, "F2a/F2b already present"
    f2 = g["nodes"][idx["F2"]]

    f2a = dict(f2)
    f2a.update({
        "id": "F2a",
        "label": "AF-SCC C2 vacuum schema",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "artifact": "schemas/af_scc_c2_vacuum.yaml",
        "artifact_sha256": measured.get("schemas/af_scc_c2_vacuum.yaml"),
        "artifact_exists": measured.get("schemas/af_scc_c2_vacuum.yaml") is not None,
        "gate": "G-FORM",
        "eta_days": 1,
        "split_from": "F2",
        "split_at": now(),
        "split_reason": ("F2 declared the merged artifact schemas/af_scc_regularities.yaml, which the group "
                         "direction explicitly rejects; C2 and C0 are separate classes (ASTRA_HANDOFF hard "
                         "decision 1) and now have separate class-bound files."),
        "last_status": {
            "at": now(),
            "by": "astra",
            "summary": ("Node created by controller DAG repair (F2 -> F2a/F2b). Declared artifact is the "
                        "class-bound C2 schema; current on-disk revision is under revise verdicts "
                        "(reviews/F2a-review-18.json, reviews/F2a-review-17.json). Not a completion."),
            "evidence_refs": ["reviews/F2a-review-18.json", "reviews/F2a-review-17.json",
                              "schemas/af_scc_c2_vacuum.yaml"],
            "next_falsifier": ("A revision that keeps a dangling extension_predicate reference, or that leaves "
                               "the forall-quantifier mismatch, is rejected on re-review."),
        },
    })

    f2b = dict(f2)
    f2b.update({
        "id": "F2b",
        "label": "AF-SCC C0 vacuum schema",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "artifact": "schemas/af_scc_c0_vacuum.yaml",
        "artifact_sha256": measured.get("schemas/af_scc_c0_vacuum.yaml"),
        "artifact_exists": measured.get("schemas/af_scc_c0_vacuum.yaml") is not None,
        "gate": "G-FORM",
        "eta_days": 1,
        "split_from": "F2",
        "split_at": now(),
        "split_reason": "see F2a; C0 must never be merged with C2 nor inherit C2's conclusion type",
        "last_status": {
            "at": now(),
            "by": "astra",
            "summary": ("Node created by controller DAG repair (F2 -> F2a/F2b). Declared artifact is the "
                        "class-bound C0 schema at revision 6; two accept verdicts exist on earlier revisions "
                        "(rev3/rev4) and a revise verdict on the current hash (reviews/F2b-review-18.json). "
                        "Accept verdicts do not transfer across hashes. Not a completion."),
            "evidence_refs": ["reviews/F2b-review-16-r3.json", "reviews/F2b-review-lead-audit.json",
                              "reviews/F2b-review-18.json", "schemas/af_scc_c0_vacuum.yaml"],
            "next_falsifier": ("Re-review of the rev5/rev6 delta at the frozen hash; any reintroduction of a "
                               "composite 'C0 or C2' string or a node_id mismatch rejects the revision."),
        },
    })

    g["nodes"][idx["F2"]] = f2a
    g["nodes"].append(f2b)

    # retire the merged artifact from service as a class artifact
    fa = m.setdefault("frozen_artifacts", [])
    if not any(f.get("path") == "schemas/af_scc_regularities.yaml" for f in fa):
        fa.append({
            "path": "schemas/af_scc_regularities.yaml",
            "node_id": "F2",
            "sha256": measured.get("schemas/af_scc_regularities.yaml"),
            "frozen_at": now(),
            "reason": ("RETIRED: single merged C0/C2 artifact; rejected by the formulation group direction and "
                       "by ASTRA_HANDOFF hard decision 1. Must not be used as a class artifact or a gate input."),
            "active": False,
            "superseded_at": now(),
            "superseded_note": "replaced by schemas/af_scc_c2_vacuum.yaml (F2a) and schemas/af_scc_c0_vacuum.yaml (F2b)",
        })
    return True, "F2 split into F2a/F2b; merged artifact retired"


def refresh_gates(m, measured):
    today = now()
    gates = {g["gate_id"]: g for g in m["gates"]}

    gates["G-F0"].update({
        "verdict": "pending",
        "owner": "lead-formulation",
        "updated_at": today,
        "eta": "0.5d",
        "evidence_refs": ["research_map/formulation_taxonomy.yaml",
                          "reviews/F0-F1-review-17.json",
                          "reviews/F0-review-lead-audit.json",
                          "schemas/taxonomy_cases.jsonl",
                          "reviews/INDEX.md"],
        "unmet": [
            "no accept verdict exists at the current hash 66bf917bd368: recorded verdicts are revise x4 and inconclusive x1",
            "reviews/INDEX.md records G-F0 fail against intermediate hash 347c924b; the map verdict must be reconciled with the index",
            "the taxonomy is still labelled draft_unverified by its author and its genericity slots are owned by F1/F2",
            "9 taxonomy cases remain open (new class vs split) and were never dispositioned by the lead",
        ],
        "controller_note": ("verdict held at pending because a re-review round is in flight against rev3; "
                            "the gate cannot pass without two independent accept verdicts at one hash."),
    })
    gates["G-FORM"].update({
        "verdict": "pending",
        "owner": "lead-formulation",
        "updated_at": today,
        "eta": "1.5d",
        "evidence_refs": ["schemas/af_wcc_vacuum.yaml",
                          "schemas/af_scc_c2_vacuum.yaml",
                          "schemas/af_scc_c0_vacuum.yaml",
                          "reviews/F1-review-16-r2.json",
                          "reviews/F1-review-lead-audit.json",
                          "reviews/F2a-review-18.json",
                          "reviews/F2b-review-18.json",
                          "reviews/INDEX.md"],
        "unmet": [
            "F1 at 7a3e1f93 has revise verdicts (flash-16 r2, lead-audit); no accept at the current hash",
            "F2a at 23fec0e9 has revise verdicts with hard failures HF-A1 (dangling extension_predicate) and HF-A2 (forall mismatch)",
            "F2b at e6b1af2b has a revise verdict (HF-B1 composite-regularity exemption, HF-B2 node_id mismatch)",
            "no single frozen data class (s,delta,norm) is shared by F1/F2a/F2b, which disables the licensed C0=>C2 transfer",
            "the map previously bound F2 to the retired merged artifact; that path is now removed",
        ],
        "controller_note": ("verdict held at pending; reviews/INDEX.md records fail. The gate needs two accept "
                            "verdicts per class at one frozen hash, not a path-level pass."),
    })
    gates["G-LIT"].update({
        "verdict": "pending",
        "owner": "lead-literature",
        "updated_at": today,
        "eta": "1.0d",
        "evidence_refs": ["ledger/theorems.jsonl",
                          "ledger/citation_audit.csv",
                          "reviews/L0-review-17.json",
                          "reviews/L0-review-lead-audit.json",
                          "artifacts/literature/reviews/citation-integrity-C.md",
                          "reviews/INDEX.md"],
        "unmet": [
            "L0 carries three revise verdicts (flash-16, flash-17 HF-01, lead-audit HF) and no accept",
            "the citation-integrity review records four hard failures (wrong DOI/year/pages, non-reproducible verification pages, unannotated duplicate clusters)",
            "ledger rows use class tokens outside the frozen four (AF-WCC-VAC-BH-FORM, AF-WCC-VAC-NS-CONSTR, AF-SCC-OTHER-MODELS)",
            "201 citations have no source_meta scope fields; 100+ accepted records are self-certified",
            "fewer than 3 independent re-fetch spot checks are recorded as passed",
        ],
        "controller_note": "verdict pending; INDEX.md records fail. Not adjudicable on the current evidence.",
    })
    gates["G-NUM"].update({
        "verdict": "pending",
        "owner": "lead-numerics",
        "updated_at": today,
        "eta": "0.5d",
        "locked": True,
        "lock_note": LOCK_NOTE,
        "evidence_refs": ["numerics/tests/flat_wave.py#8b52014dac47",
                          "numerics/tests/flat_wave_replication.py#8ade1cdc163e",
                          "artifacts/numerics/n0/lead_calibration_report.json",
                          "runtime/state/controller_verification/N0_adjudication.md",
                          "runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json#sha256:6542db93eebc",
                          "numerics/gates.py"],
        "unmet": [
            "independent numerical-protocol review is not recorded (nobody may self-review)",
            "cnfem triage from the N0 adjudication is not closed: fix with root cause, or exclude with evidence",
            "the replication harness invariant functional is leapfrog-specific; a scheme-agnostic check or relabelling is required",
            "the audit lead asks for a 4th resolution before the order claim is accepted",
            "cnfd own-energy drift 6.6e-8 has no principled threshold justification",
        ],
        "controller_note": ("N0 flat-space work only. N1 stays queued and numerics_lock stays LOCKED; release "
                            "requires G-FORM and G-AUDIT pass plus measured, independently replicated N0 convergence."),
    })
    gates["G-AUDIT"].update({
        "verdict": "pending",
        "owner": "lead-audit",
        "updated_at": today,
        "eta": "1.0d",
        "evidence_refs": ["evaluation_rubric.yaml",
                          "reviews/",
                          "runtime/bin/classsep_regression.py",
                          "artifacts/worker-06/blindspot_report.json",
                          "artifacts/worker-07/class_separation_falsification/results.json"],
        "unmet": [
            "A1 needs two independent verdicts per formulation/literature target at a cited sha256; the current F1/F2a/F2b verdicts are revise",
            "A0 has no recorded reviewer verdict even though the rubric file exists",
            "four of five class-binding gates are uncalibrated on audited-positive fixtures",
            "the evaluation rubric must contain no universal scalar score",
        ],
        "controller_note": "verdict pending; checker calibration passed, target reviews did not.",
    })
    return gates


def normalize_validation(m, measured):
    """validation_status must not lead the gate. L0/L1 were reported passed while their
    gate is pending and reviewer verdicts on disk are revise with hard failures."""
    changes = []
    idx = node_index(m)
    for nid, new, reason in [
        ("L0", "unverified", "3 revise verdicts on disk (flash-16, flash-17 HF-01, lead-audit HF); no accept; G-LIT pending"),
        ("L1", "unverified", "citation-integrity review records 4 hard failures; G-LIT pending"),
    ]:
        g, n = idx[nid]
        if n.get("validation_status") == new:
            continue
        old = n.get("validation_status")
        n["validation_status"] = new
        n.setdefault("validation_history", []).append({
            "at": now(), "by": "astra", "from": old, "to": new,
            "reason": reason,
            "evidence_refs": ["reviews/L0-review-17.json", "reviews/L0-review-lead-audit.json",
                              "artifacts/literature/reviews/citation-integrity-C.md"],
        })
        changes.append(f"{nid}: validation_status {old} -> {new}")
    return changes


def refresh_eta(m):
    eta = {
        "formulation": (0.5, 1.5, "F1/F2a/F2b revise verdicts must be closed at one frozen hash per class"),
        "literature": (1.0, 3.0, "ledger hygiene + source_meta scope + 3 independent re-fetch spot checks"),
        "numerics": (0.5, 1.5, "N0 closure only; N1 stays queued behind the lock"),
        "audit": (0.5, 1.5, "A1 re-review at frozen hashes + A0 verdict"),
    }
    for g in m["groups"]:
        if g["id"] in eta:
            lo, hi, why = eta[g["id"]]
            g["eta_days_low"], g["eta_days_high"] = lo, hi
            g["eta_basis"] = why
            g["eta_updated_at"] = now()
    return eta


def add_findings(m, measured):
    cf = m.setdefault("controller_findings", [])
    have = {f["id"] for f in cf}
    if "CF-7" not in have:
        cf.append({
            "id": "CF-7", "at": now(), "severity": "major", "status": "fixed",
            "finding": ("Node F2 declared schemas/af_scc_regularities.yaml, a single merged C0/C2 artifact. "
                        "That path is the exact artifact the group direction rejects, and G-FORM is scoped to "
                        "F1,F2a,F2b, so the DAG had no node for either SCC class."),
            "action": ("split F2 -> F2a (schemas/af_scc_c2_vacuum.yaml) and F2b (schemas/af_scc_c0_vacuum.yaml) "
                       "at the paths that already carry reviewer verdicts; retired the merged artifact "
                       "(active=false) so it can never be a gate input"),
            "evidence": ["schemas/af_scc_c2_vacuum.yaml", "schemas/af_scc_c0_vacuum.yaml",
                         "schemas/af_scc_regularities.yaml", "reviews/F2a-review-18.json",
                         "reviews/F2b-review-18.json"],
        })
    if "CF-8" not in have:
        cf.append({
            "id": "CF-8", "at": now(), "severity": "major", "status": "recorded",
            "finding": ("Gate-ledger divergence: reviews/INDEX.md records G-F0, G-FORM and G-LIT as fail, while "
                        "research_map.json holds all gates at pending with updated_at 23:27 (before the latest "
                        "revisions). Separately L0 and L1 carried validation_status=passed although their gate is "
                        "pending and their on-disk verdicts are revise with hard failures."),
            "action": ("kept gate verdicts pending (review rounds are in flight) but recorded explicit unmet "
                       "criteria per gate; demoted L0/L1 to unverified with reasons; require the gate owners to "
                       "reconcile the index with the map at the next adjudication"),
            "evidence": ["reviews/INDEX.md", "reviews/L0-review-17.json", "reviews/L0-review-lead-audit.json",
                         "artifacts/literature/reviews/citation-integrity-C.md", "research_map/research_map.json#gates"],
        })
    if "CF-9" not in have:
        cf.append({
            "id": "CF-9", "at": now(), "severity": "minor", "status": "fixed",
            "finding": ("G-F0 evidence_refs pointed at reviews/F0-review-17.json and reviews/F0-review-19.json, "
                        "neither of which exists on disk, so the gate was not adjudicable on its declared refs."),
            "action": ("repointed G-F0 to the real verdict files reviews/F0-F1-review-17.json and "
                       "reviews/F0-review-lead-audit.json plus the taxonomy-case corpus"),
            "evidence": ["reviews/F0-F1-review-17.json", "reviews/F0-review-lead-audit.json",
                         "schemas/taxonomy_cases.jsonl"],
        })
    return cf


# --------------------------------------------------------------------------- cards
def cards(measured):
    common = {
        "created_at": now(),
        "actor": "astra",
        "run_id": RUN,
        "deadline": DEADLINE,
        "issued_by": "astra",
        "issued_at": now(),
        "evidence_rule": "artifact + sha256 + reviewer verdict; fluent text is never a theorem",
        "numerics_lock": LOCK_NOTE,
    }
    C = []
    C.append(dict(common, event_id="astra-indep-1-F1-F2-formulation", event_type="assignment",
                  assignee="astra-lead-formulation", node_id="F1,F2a,F2b", gate="G-FORM",
                  artifact=["schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml",
                            "schemas/af_scc_c0_vacuum.yaml"],
                  class_id="AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
                  evidence_refs=["reviews/F1-review-16-r2.json", "reviews/F2a-review-18.json",
                                 "reviews/F2b-review-18.json", "reviews/F0-review-lead-audit.json"],
                  falsifier=("A revision that still contains a dangling class-core reference, a composite "
                             "'C0 or C2' string, or a per-class quantifier that disagrees with its own "
                             "statement_formal is rejected on re-review."),
                  acceptance=("One frozen revision per class at the node's declared canonical path; each carries a "
                              "sha256-carrying artifact event; the three schemas share one declared data class "
                              "(s,delta,norm) or record the divergence explicitly; two independent accept verdicts "
                              "per class at that hash; no new class ids."),
                  budget_agent_hours=8,
                  eig="G-FORM is the critical-path gate for the whole vacuum portfolio and for the numerics unlock.",
                  stop_rule=("Stop at one hash per class with two accept verdicts, or report the exact unmet "
                             "criterion. Any write after freeze invalidates the verdicts and opens a new round."),
                  task=("Close the revise verdicts on F1/F2a/F2b at the canonical paths. Publish from your "
                        "authoring tree into the canonical path rather than repointing the map; the map's declared "
                        "paths are where the review verdicts live. Do not adopt new class ids for the WCC "
                        "visibility variants: record them under the parent class with a variant_id and keep the "
                        "four frozen class ids.")))
    C.append(dict(common, event_id="astra-indep-1-A1-audit", event_type="assignment",
                  assignee="astra-lead-audit", node_id="A1", gate="G-AUDIT",
                  artifact="reviews/", class_id="AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
                  evidence_refs=["evaluation_rubric.yaml", "reviews/INDEX.md", "runtime/bin/classsep_regression.py"],
                  falsifier=("An accept verdict recorded against a hash that is not the node's declared artifact "
                             "hash, or a promotion justified by a lexical gate pass, invalidates the review."),
                  acceptance=("Two independent verdicts per formulation target at a cited sha256; an explicit "
                              "verdict on A0; the five competing class-binding gates reduced to one derived from "
                              "artifacts/formulation/rule_spec.json; G-AUDIT criteria adjudicated against the map."),
                  budget_agent_hours=5,
                  eig="Unblocks G-AUDIT, which with G-FORM is a precondition of the numerics unlock.",
                  stop_rule="Stop when each target has two verdicts at one hash, or record which target cannot reach two.",
                  task=("Re-run the A1 queue against the frozen F1/F2a/F2b hashes; state plainly which verdicts are "
                        "stale. Reconcile reviews/INDEX.md with the map gate verdicts, and record the A0 verdict.")))
    C.append(dict(common, event_id="astra-indep-1-L0-L1-literature", event_type="assignment",
                  assignee="astra-lead-literature", node_id="L0,L1", gate="G-LIT",
                  artifact=["ledger/theorems.jsonl", "ledger/citation_audit.csv"],
                  class_id="AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH",
                  evidence_refs=["reviews/L0-review-17.json", "reviews/L0-review-lead-audit.json",
                                 "artifacts/literature/reviews/citation-integrity-C.md", "ledger/class_coverage.csv"],
                  falsifier=("A locator that does not resolve to the cited primary source, or a row whose "
                             "verification_status claims more than its recorded verification page supports, "
                             "fails the ledger."),
                  acceptance=("Every row has a resolvable locator and an honest verification_status; the four "
                              "hard failures from the citation-integrity review are fixed or explicitly marked "
                              "unresolved; non-frozen class tokens are relabelled as ledger tags; de-duplicated "
                              "ledger files; >=3 independent re-fetch spot checks recorded."),
                  budget_agent_hours=6,
                  eig="G-LIT is the only gate with no accept evidence at all and it bounds every literature claim.",
                  stop_rule="Stop when the hard failures are closed or marked unresolved with a reason; no silent acceptance.",
                  task=("Fix ledger hygiene in descending value: source_meta scope fields, replace self-certified "
                        "accepted records with reviewer verdicts, relabel invented class tokens, merge and dedupe "
                        "the ledger files. Record the C2 no-primary-theorem blocker as a map-level state-of-field "
                        "finding rather than a retrieval failure.")))
    C.append(dict(common, event_id="astra-indep-1-N0-numerics", event_type="assignment",
                  assignee="astra-lead-numerics", node_id="N0", gate="G-NUM",
                  artifact="numerics/tests/flat_wave.py", class_id="AF-WCC-SCALAR-SPH",
                  evidence_refs=["runtime/state/controller_verification/N0_adjudication.md",
                                 "numerics/CONVERGENCE_PROTOCOL.md",
                                 "artifacts/numerics/n0/lead_calibration_report.json"],
                  falsifier=("A scheme that passes only because the invariant functional was retuned to it, or a "
                             "cnfem exclusion without a shown root cause, falsifies the convergence claim."),
                  acceptance=("cnfem triaged to a root cause (fixed, or excluded with evidence); scheme-agnostic "
                              "invariant check or honest relabelling; a 4th resolution; the cnfd drift threshold "
                              "justified; an independent reviewer verdict on numerics/CONVERGENCE_PROTOCOL.md."),
                  budget_agent_hours=3,
                  eig="N0 is one criterion away from G-NUM and is the only numerics work the lock permits.",
                  stop_rule=("Stop when G-NUM can be proposed with hashes, or record the exact unmet criterion. "
                             "N1 stays queued; do not create numerics/spherical_solver/."),
                  task=("Close the N0 adjudication follow-ups. " + LOCK_NOTE)))
    C.append(dict(common, event_id="astra-indep-1-CF5-ledger-verify", event_type="assignment",
                  assignee="deepseek-flash-19", node_id="L0", gate="G-LIT",
                  artifact="artifacts/flash-19/class_token_census.json",
                  class_id="AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH",
                  evidence_refs=["ledger/theorems.jsonl", "research_map/class_separation.py",
                                 "research_map/audit_evidence.py"],
                  falsifier=("A class token in the ledger that is not one of the four frozen ids and not "
                             "explicitly tagged as a ledger-local tag falsifies the census."),
                  acceptance=("Machine census of every class token in ledger/theorems.jsonl and "
                              "ledger/citation_audit.csv with counts, each classified frozen / ledger-tag / "
                              "violation, plus a one-line remedy per violation."),
                  budget_agent_hours=1.5,
                  eig="Closes open controller finding CF-5 with measured evidence instead of a prose assertion.",
                  stop_rule="Stop at the census artifact; do not edit the ledger (the literature lead owns it).",
                  task=("Independent verification only: census class tokens, do not modify ledger files.")))
    return C


def apply_edits(m, measured, dry):
    log = []
    ok, msg = split_f2(m, measured)
    log.append(("DAG " + ("applied" if ok else "skipped")) + ": " + msg)
    refresh_gates(m, measured)
    log.append("GATES refreshed: G-F0, G-FORM, G-LIT, G-NUM, G-AUDIT (all pending with explicit unmet criteria)")
    for c in normalize_validation(m, measured):
        log.append("VALIDATION " + c)
    refresh_eta(m)
    log.append("ETA refreshed on 4 groups")
    add_findings(m, measured)
    log.append("FINDINGS ensured: CF-7, CF-8, CF-9")

    cards_ = cards(measured)
    existing = {a.get("event_id") for a in m.get("assignments", [])}
    new_cards = [c for c in cards_ if c["event_id"] not in existing]
    return log, cards_, new_cards


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--label", default="astra-indep-1")
    a = ap.parse_args()
    dry = not a.apply

    LOCK.parent.mkdir(parents=True, exist_ok=True)
    with LOCK.open("w") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            if not dry:
                ing = comms.ingest(dry_run=False, verbose=True)
                applied = apply_events.main(dry_run=False)
                print("INGEST", json.dumps({k: ing[k] for k in ("accepted", "rejected", "duplicates")}))
                print("APPLY", json.dumps({k: v for k, v in applied.items() if k != "details"})[:300])
            else:
                ing, applied = None, None

            m = json.loads(MAP.read_text())
            measured = {}
            for rel in ["schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml",
                        "schemas/af_scc_c0_vacuum.yaml", "schemas/af_scc_regularities.yaml",
                        "research_map/formulation_taxonomy.yaml", "numerics/tests/flat_wave.py",
                        "ledger/theorems.jsonl", "ledger/citation_audit.csv", "evaluation_rubric.yaml"]:
                measured[rel] = sha256(ROOT / rel)

            # keep measured hashes fresh on the nodes
            idx = node_index(m)
            for nid, rel in [("F0", "research_map/formulation_taxonomy.yaml"),
                             ("F1", "schemas/af_wcc_vacuum.yaml"),
                             ("N0", "numerics/tests/flat_wave.py"),
                             ("L0", "ledger/theorems.jsonl"),
                             ("L1", "ledger/citation_audit.csv"),
                             ("A0", "evaluation_rubric.yaml")]:
                if nid in idx:
                    _, n = idx[nid]
                    if measured.get(rel):
                        n["artifact_sha256"] = measured[rel]
                        n["artifact_exists"] = True
                        n["artifact_sha256_measured_at"] = now()

            log, cards_, new_cards = apply_edits(m, measured, dry)

            print("\n== planned controller edits ==")
            for line in log:
                print("  *", line)
            print(f"  * assignment cards: {len(cards_)} total, {len(new_cards)} new")

            if not dry:
                for c in new_cards:
                    m.setdefault("assignments", []).append(c)
                    comms.send(c["assignee"], c)
                    comms.append_event(c)
                prom = promote.evaluate(m)
                acct = accounting.refresh(m)
                m["updated_at"] = now()
                tmp = MAP.with_suffix(".json.tmp")
                tmp.write_text(json.dumps(m, indent=2) + "\n")
                tmp.replace(MAP)
                print("WROTE map; promotion:", json.dumps(prom)[:200])
                rec = checkpoint.main(a.label)
                print("CHECKPOINT", rec["checkpoint_id"], "hard:", rec["evidence_hard_failures"])
            else:
                print("\n(dry run: nothing written)")
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


if __name__ == "__main__":
    main()
