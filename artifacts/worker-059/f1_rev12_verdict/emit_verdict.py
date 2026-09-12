#!/usr/bin/env python3
"""W059-F1-REV12-VERDICT-01 emitter.

Writes the review, drift annex, worker checkpoint, and appends the upward
event batch to comms/outbox/worker-059.jsonl.  Emits only worker-level
verdicts; it never sets a node status, a validation_status=passed, or a gate
verdict.
"""
import datetime as dt
import hashlib
import json
import os

REPO = "/data3/guoshaoyang/workdir/ai4math-swarm"
OUT = os.path.join(REPO, "artifacts/worker-059/f1_rev12_verdict")
OUTBOX = os.path.join(REPO, "comms/outbox/worker-059.jsonl")
STATE = os.path.join(REPO, "runtime/state")
TZ = dt.timezone(dt.timedelta(hours=8))
NOW = dt.datetime.now(TZ)
TS = NOW.strftime("%Y-%m-%dT%H:%M:%S%z")
TS_COLON = NOW.strftime("%Y-%m-%dT%H:%M:%S+08:00")
REVIEWED = "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3"


def sha(rel):
    return hashlib.sha256(open(os.path.join(REPO, rel), "rb").read()).hexdigest()


def write_json(rel, obj):
    p = os.path.join(REPO, rel)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1)
    return p


ev = json.load(open(os.path.join(OUT, "independent_evidence.json"), encoding="utf-8"))
matrix = json.load(open(os.path.join(OUT, "registry_matrix.json"), encoding="utf-8"))
checks = {c["id"]: c for c in ev["checks"]}
blocking = [c for c in ev["checks"] if not c["ok"] and c["severity"] == "blocking"]
advis = [c for c in ev["checks"] if not c["ok"] and c["severity"] != "blocking"]

review = {
    "review_id": "W059-F1-REV12-VERDICT-01",
    "task_id": "W059-F1-REV12-VERDICT-01",
    "actor": "worker-059",
    "reviewer": "worker-059",
    "target_id": "F1",
    "target_path": "schemas/af_wcc_vacuum.yaml",
    "node_id": "F1",
    "group_id": "formulation",
    "class_id": "AF-WCC-VAC-GEN",
    "gate": "G-FORM",
    "reviewed_revision": 12,
    "reviewed_sha256": REVIEWED,
    "verdict": "revise",
    "score": 4.0,
    "counts_as_independent_verdict": True,
    "counts_as_full_schema_verdict": True,
    "counts_as_independent_second_verdict": False,
    "independence_caveat": "Instrument is own-built (stdlib+PyYAML, no canonical gate, no other worker's checker imported); 25/25 declared single-defect mutants detected. Prior reviewers (worker-040/053/088/090) converged on the consistency-evidence and token-registry defects, so viewpoint independence is the controller's call.",
    "hard_failures": [
        {
            "id": "HF-059-F1-01",
            "name": "stale_declared_consistency_evidence_hash",
            "severity": "blocking",
            "detail": "f0_binding declares declared_f0_sha256=0abb9ed8 (matches measured) but consistency_evidence_sha256=675a99d0d25b2b37... while the declared canonical path artifacts/formulation/evidence/taxonomy_consistency.json measures 9e335e9ba1bfcf77... and FROZEN revision 28 pins 9e335e9b; checked_at=2026-09-12T00:31:41+08:00 predates the current evidence bytes (idempotent rewrite, content stable, mtime after the declaration). 675a99d0 is worker-086's out-of-tree enriched pin. The canonical evidence embeds no compared-tree digests, so the declared consistency cannot be bound from canonical artifacts (checks H4/H5; H6 minor). Content was independently re-verified true: consistent=true, 0 contract divergences, 4 classes compared.",
            "evidence_refs": ["artifacts/worker-059/f1_rev12_verdict/independent_evidence.json",
                              "artifacts/worker-059/f1_rev12_verdict/snapshot/taxonomy_consistency.9e335e9ba1bf.json",
                              "artifacts/worker-059/f1_rev12_verdict/snapshot/FROZEN.r28.json"],
            "falsifier": "A F1 revision in which f0_binding.consistency_evidence_sha256 equals the measured bytes at the declared canonical path and equals the FROZEN pin."
        },
        {
            "id": "HF-059-F1-02",
            "name": "genericity_token_registry_conflict_F0_vs_VOCAB_ALIASES",
            "severity": "blocking pending controller ruling",
            "detail": "F1's conclusion_type 'weak_cosmic_censorship' is canonical in BOTH registries (clean). The conflict at F1 is on the genericity axis: the schema uses genericity.kind=residual_comeager, the VOCAB_ALIASES canonical key, while the canonical F0 taxonomy stores the registered alias 'provisional_baire_residual' in classes.AF-WCC-VAC-GEN.axes.genericity_kind. VOCAB_ALIASES policy: accepted aliases 'must never appear in a new canonical artifact'. The same shape blocks F2a/F2b (conclusion axis, aliases strong_cosmic_censorship_C2/C0). F0 also stores 'unresolved' for AF-WCC-SCALAR-SPH, a token absent from VOCAB_ALIASES entirely (coverage gap). The canonical class gate returns pass on the same bytes, so the gate does not enforce the registry policy (checks G2, E1-E3; registry_matrix.json).",
            "evidence_refs": ["artifacts/worker-059/f1_rev12_verdict/registry_matrix.json",
                              "artifacts/worker-059/f1_rev12_verdict/snapshot/VOCAB_ALIASES.46cd9f1eb534.json",
                              "artifacts/worker-059/f1_rev12_verdict/snapshot/taxonomy.0abb9ed8a961.yaml"],
            "falsifier": "One written controller ruling designating the governing token registry for conclusion_type and genericity_kind (or a revision of the losing registry) such that every canonical artifact's token is canonical under the designated registry."
        }
    ],
    "findings": [
        {"id": "F-059-F1-01", "kind": "content_surface_green",
         "detail": "73 independent checks: 67 pass; 25/25 declared single-defect mutants detected. Semantics, quantifier order (forall r D0 - exists G_r D1 - forall data D2 - exists completion D3 - forall gamma D4 - not_exists (q,t0) D5), tagged D0, canonical single-q tail predicate with the whole-curve strength disclaimer, AF_{I+} abbreviation, forbidden strengthening/weakening lists, anti-scope (both SCC classes and the scalar class), promotion rule, no SCC leakage on the statement surface, falsifier tier-1 non-meagerness route: all verified at the pinned bytes."},
        {"id": "F-059-F1-02", "kind": "closure_delta_prior_worker059_HFs",
         "detail": "The three blocking HFs worker-059 raised at 9a8bd4c96800 are independently confirmed RESOLVED at cce9c60146d6: (i) duplicate top-level revised_at keys -> strict parse clean; (ii) future-dated revised_at -> none, revised_at 00:31:41 <= file mtime 00:32:02; (iii) cross-tree class_contract_pointer -> now research_map/formulation_taxonomy.yaml#classes.AF-WCC-VAC-GEN with the supplement split into a separately named field."},
        {"id": "F-059-F1-03", "kind": "residual_advisory_calibration",
         "detail": "worker-059's older HF-4 (stale calibration fixtures) remains OPEN at rev12: schemas/semantic_contract_tests/run_contract_tests.py exits 2 INTEGRITY_FAILURE with sha mismatch F1 cce9c60146d6 != b65fcc0f0118, F2a 5476a3f2c6bc != 8dae50da1ab5, F2b 55d0a1ea9bda != a8d899d2941f. Advisory to A1/calibration; does not affect F1's content verdict.",
         "evidence_refs": ["artifacts/worker-059/f1_rev12_verdict/corroboration/semantic_contract_tests_stdout.txt"]},
        {"id": "F-059-F1-04", "kind": "corroboration",
         "detail": "Canonical gates corroborate at the same bytes: research_map/validate_map.py VALID (exit 0); runtime/bin/classsep_regression.py PASS 17/17 leaks, 10/10 controls, FP 0 / FN 0; FROZEN revision 28 pins every measured byte for F1, taxonomy, supplement, evidence and VOCAB_ALIASES; the F1 canonical/authoring mirror pair is byte-identical (cce9c60146d6 == cce9c60146d6)."},
        {"id": "F-059-F1-05", "kind": "advisory",
         "detail": "l1_ledger_refs declare l1_status=accepted for D-001/T-204/T-208 and provisional for T-209 while ledger/theorems.jsonl verification_status for those rows is not mapped anywhere in the file or the ledger; same advisory as F2a/F2b (check J2)."},
        {"id": "F-059-F1-06", "kind": "advisory",
         "detail": "class_components.regularity_token is the string 'none' while F0 axes.regularity_token is null for the same absent token; semantically equal, encoding differs (check C5)."},
        {"id": "F-059-F1-07", "kind": "advisory",
         "detail": "review_status.independent_reviewers=[] and verdict=pending is honest but stale: the review corpus for F1 now exists (this review plus worker-040/053/088/090). External verdicts accumulate in reviews/ and the map; the block should be refreshed by the owner, not by a reviewer."},
        {"id": "F-059-F1-08", "kind": "no_drift",
         "detail": "No hash drift during the measurement window: F1 cce9c60146d6, taxonomy 0abb9ed8, supplement d7419b4e, VOCAB_ALIASES 46cd9f1e stable pre/post; the canonical evidence file was rewritten idempotently (bytes identical to the 9e335e9b pin)."}
    ],
    "evidence_refs": [
        "artifacts/worker-059/f1_rev12_verdict/snapshot/f1.cce9c60146d6.yaml#" + REVIEWED,
        "artifacts/worker-059/f1_rev12_verdict/independent_evidence.json",
        "artifacts/worker-059/f1_rev12_verdict/registry_matrix.json",
        "artifacts/worker-059/f1_rev12_verdict/check_f1_rev12.py",
        "artifacts/worker-059/f1_rev12_verdict/corroboration/classsep_regression_stdout.txt",
        "artifacts/worker-059/f1_rev12_verdict/corroboration/validate_map_stdout.txt",
        "artifacts/worker-059/f1_rev12_verdict/corroboration/semantic_contract_tests_stdout.txt"
    ],
    "next_falsifier": "A F1 revision (or controller ruling) in which (i) f0_binding.consistency_evidence_sha256 equals the measured bytes at the declared canonical evidence path, that path equals the FROZEN pin, and the canonical evidence embeds map_taxonomy_sha256=0abb9ed8 and lead_contract_sha256=d7419b4e; and (ii) one governing token registry is designated for both conclusion_type and genericity_kind so that every canonical artifact's token is canonical under it. Hash drift of schemas/af_wcc_vacuum.yaml voids this verdict immediately (pinned cce9c60146d6).",
    "validation_status": "unverified",
    "note": "Advisory worker verdict; cannot set a gate verdict or node status. Content surface passes; binding/publication state fails on two items, one of which (HF-02) is a controller-level registry ruling that also blocks F2a/F2b."
}

annex = {
    "task_id": "W059-F1-REV12-VERDICT-01",
    "actor": "worker-059",
    "class_id": "AF-WCC-VAC-GEN",
    "measured_at": TS_COLON,
    "reviewed_sha256": REVIEWED,
    "postrun_measurement": {"schemas/af_wcc_vacuum.yaml": sha("schemas/af_wcc_vacuum.yaml")},
    "drift": sha("schemas/af_wcc_vacuum.yaml") != REVIEWED,
    "falsifier": "Any later measurement of schemas/af_wcc_vacuum.yaml different from cce9c60146d6 falsifies the binding of this review.",
    "mirror_authoring_sha256": sha("artifacts/formulation/schemas/af_wcc_vacuum.yaml")
}

checkpoint = {
    "checkpoint_id": "w059-ckpt-f1-rev12-" + NOW.strftime("%Y%m%dT%H%M%S"),
    "task_id": "W059-F1-REV12-VERDICT-01",
    "actor": "worker-059",
    "node_id": "F1",
    "group_id": "formulation",
    "class_id": "AF-WCC-VAC-GEN",
    "gate": "G-FORM",
    "created_at": TS_COLON,
    "status": "complete_worker_level",
    "hours": 0.4,
    "reviewed_sha256": REVIEWED,
    "reviewed_revision": 12,
    "verdict": "revise",
    "score": 4.0,
    "check_summary": ev["check_summary"],
    "mutant_summary": ev["mutant_summary"],
    "blocking_findings": ["HF-059-F1-01 stale declared consistency-evidence hash (675a99d0 vs measured/frozen 9e335e9b)",
                          "HF-059-F1-02 genericity-token registry conflict F0 alias provisional_baire_residual vs VOCAB canonical residual_comeager; controller ruling required"],
    "no_global_state_mutated": True,
    "no_node_completion_or_gate_verdict_claimed": True,
    "next_falsifier": review["next_falsifier"]
}

write_json("artifacts/worker-059/f1_rev12_verdict/review_F1_cce9c60146d6.json", review)
write_json("artifacts/worker-059/f1_rev12_verdict/postrun_annex.json", annex)
write_json("artifacts/worker-059/f1_rev12_verdict/checkpoint_w059_f1_rev12.json", checkpoint)
os.makedirs(STATE, exist_ok=True)
write_json("runtime/state/w059_f1_rev12_checkpoint.json", checkpoint)

H = {
    "review": sha("artifacts/worker-059/f1_rev12_verdict/review_F1_cce9c60146d6.json"),
    "evidence": sha("artifacts/worker-059/f1_rev12_verdict/independent_evidence.json"),
    "matrix": sha("artifacts/worker-059/f1_rev12_verdict/registry_matrix.json"),
    "instrument": sha("artifacts/worker-059/f1_rev12_verdict/check_f1_rev12.py"),
    "annex": sha("artifacts/worker-059/f1_rev12_verdict/postrun_annex.json"),
    "checkpoint": sha("artifacts/worker-059/f1_rev12_verdict/checkpoint_w059_f1_rev12.json"),
    "classsep": sha("artifacts/worker-059/f1_rev12_verdict/corroboration/classsep_regression_stdout.txt"),
    "validate_map": sha("artifacts/worker-059/f1_rev12_verdict/corroboration/validate_map_stdout.txt"),
    "semantic_contract_tests": sha("artifacts/worker-059/f1_rev12_verdict/corroboration/semantic_contract_tests_stdout.txt"),
}

base = "w059-f1rev12-" + NOW.strftime("%Y%m%dT%H%M%S")
E = []


def add(evt):
    evt.setdefault("created_at", TS_COLON)
    evt.setdefault("actor", "worker-059")
    E.append(evt)


add({"event_id": base + "-task-claim", "event_type": "status", "node_id": "F1",
     "group_id": "formulation", "class_id": "AF-WCC-VAC-GEN", "gate": "G-FORM",
     "status": "active", "hours": 0.4,
     "summary": "No inbox card exists for worker-059. Took ONE bounded class-bound task: W059-F1-REV12-VERDICT-01 = independent full-schema verification of F1 (AF-WCC-VAC-GEN) rev12 at pinned sha256 cce9c60146d6, with closure-delta against worker-059's prior F1 hard-finding set and a cross-registry token adjudication. Own instrument (stdlib+PyYAML, no canonical-gate imports), 73 checks, 25/25 single-defect mutants detected. Does not claim node completion or any gate verdict.",
     "evidence_refs": ["artifacts/worker-059/f1_rev12_verdict/independent_evidence.json"],
     "next_falsifier": review["next_falsifier"]})

for eid, atype, path, h in [
        ("artifact-instrument", "review_instrument", "artifacts/worker-059/f1_rev12_verdict/check_f1_rev12.py", H["instrument"]),
        ("artifact-evidence", "independent_measurement", "artifacts/worker-059/f1_rev12_verdict/independent_evidence.json", H["evidence"]),
        ("artifact-registry-matrix", "registry_adjudication", "artifacts/worker-059/f1_rev12_verdict/registry_matrix.json", H["matrix"]),
        ("artifact-review", "independent_review", "artifacts/worker-059/f1_rev12_verdict/review_F1_cce9c60146d6.json", H["review"]),
        ("artifact-annex", "drift_annex", "artifacts/worker-059/f1_rev12_verdict/postrun_annex.json", H["annex"]),
        ("artifact-checkpoint", "checkpoint", "artifacts/worker-059/f1_rev12_verdict/checkpoint_w059_f1_rev12.json", H["checkpoint"])]:
    add({"event_id": base + "-" + eid, "event_type": "artifact", "node_id": "F1",
         "group_id": "formulation", "class_id": "AF-WCC-VAC-GEN", "gate": "G-FORM",
         "artifact_type": atype, "path": path, "sha256": h, "reviewed_sha256": REVIEWED,
         "validation_status": "unverified", "evidence_refs": [p + "#" + H[k] for p, k in [
             ("artifacts/worker-059/f1_rev12_verdict/independent_evidence.json", "evidence"),
             ("artifacts/worker-059/f1_rev12_verdict/registry_matrix.json", "matrix")]],
         "falsifier": review["next_falsifier"]})

add({"event_id": base + "-review", "event_type": "review", "reviewer": "worker-059",
     "target_id": "F1", "target_path": "schemas/af_wcc_vacuum.yaml", "node_id": "F1",
     "group_id": "formulation", "class_id": "AF-WCC-VAC-GEN", "gate": "G-FORM",
     "reviewed_revision": 12, "reviewed_sha256": REVIEWED,
     "artifact": "artifacts/worker-059/f1_rev12_verdict/review_F1_cce9c60146d6.json",
     "sha256": H["review"], "verdict": "revise", "score": 4.0,
     "counts_as_independent_verdict": True, "counts_as_full_schema_verdict": True,
     "counts_as_independent_second_verdict": False,
     "hard_failures": [h["id"] + ": " + h["name"] for h in review["hard_failures"]],
     "findings": [f["id"] + ": " + f["detail"][:220] for f in review["findings"]],
     "evidence_refs": review["evidence_refs"],
     "next_falsifier": review["next_falsifier"], "validation_status": "unverified",
     "note": "Advisory worker verdict; cannot set gate verdict or node status. Content surface green at the pinned hash; binding and registry items block a hash-bound accept."})

add({"event_id": base + "-blocker", "event_type": "blocker", "node_id": "F1",
     "group_id": "formulation", "class_id": "AF-WCC-VAC-GEN", "gate": "G-FORM",
     "description": "A hash-bound accept for F1 at cce9c60146d6 is blocked by two items. HF-059-F1-01: f0_binding declares consistency_evidence_sha256=675a99d0 (worker-086's out-of-tree enriched pin) while the declared canonical path and the FROZEN rev28 pin measure 9e335e9b; the canonical evidence embeds no compared-tree digests. HF-059-F1-02: canonical F0 taxonomy stores the registered alias provisional_baire_residual for AF-WCC-VAC-GEN.axes.genericity_kind while VOCAB_ALIASES declares residual_comeager canonical and forbids aliases in new canonical artifacts; F1's conclusion_type is canonical in both registries, so the F1 defect is on the genericity axis and lives in F0. The same registry conflict blocks F2a/F2b on the conclusion axis (worker-059 HF-059-F2A-01/HF-059-F2B-02). The content surface is green at this hash (73 checks, 67 pass, 25/25 mutants).",
     "needed_to_unblock": "Either (a) extend the canonical consistency tool to embed map_taxonomy_sha256/lead_contract_sha256/measured_at, regenerate the canonical evidence, refresh the consistency_evidence_sha256 + checked_at in F1/F2a/F2b, re-freeze; or (b) repoint the three declarations to the canonical bytes 9e335e9b and record the enriched pin path explicitly. Plus one written controller ruling designating the governing conclusion_type/genericity_kind registry (or a revision of the losing registry). Then hold F1 + F0 stable for one full review window.",
     "evidence_refs": ["artifacts/worker-059/f1_rev12_verdict/review_F1_cce9c60146d6.json#" + H["review"],
                       "artifacts/worker-059/f1_rev12_verdict/registry_matrix.json#" + H["matrix"],
                       "artifacts/worker-059/f1_rev12_verdict/independent_evidence.json#" + H["evidence"]],
     "expected_information_gain": "high: removes the last binding blocker on the F1 leg of G-FORM and gives the controller one coherent repair path for F1/F2a/F2b and F0."})

add({"event_id": base + "-status-checkpoint", "event_type": "status", "node_id": "F1",
     "group_id": "formulation", "class_id": "AF-WCC-VAC-GEN", "gate": "G-FORM",
     "status": "active", "hours": 0.4, "checkpoint_id": checkpoint["checkpoint_id"],
     "summary": "W059-F1-REV12-VERDICT-01 complete at worker level. Pinned F1 rev12 sha256 cce9c60146d6 (no drift through finalize). Verdict revise 4.0: content, quantifiers, i_plus, visibility, class separation, anti-scope, promotion rule, mirror and FROZEN r28 pins all green (73 checks/67 pass; 25/25 mutants); blocking findings are HF-059-F1-01 consistency-evidence hash binding and HF-059-F1-02 genericity-token registry conflict. worker-059's prior F1 HFs at 9a8bd4c9 confirmed resolved; the calibration-fixture HF remains open as advisory (semantic contract tests exit 2 on rev12 fixture pins). Cross-registry matrix adjudicates F1 conclusion axis clean, F2a/F2b conclusion conflict, F0 genericity alias, scalar gkind absent from VOCAB. Artifacts under artifacts/worker-059/f1_rev12_verdict/; no global state mutated, no node completion or gate verdict claimed.",
     "evidence_refs": ["artifacts/worker-059/f1_rev12_verdict/review_F1_cce9c60146d6.json#" + H["review"],
                       "artifacts/worker-059/f1_rev12_verdict/independent_evidence.json#" + H["evidence"],
                       "artifacts/worker-059/f1_rev12_verdict/registry_matrix.json#" + H["matrix"],
                       "artifacts/worker-059/f1_rev12_verdict/checkpoint_w059_f1_rev12.json#" + H["checkpoint"],
                       "artifacts/worker-059/f1_rev12_verdict/postrun_annex.json#" + H["annex"]],
     "next_falsifier": review["next_falsifier"]})

with open(OUTBOX, "a", encoding="utf-8") as fh:
    for e in E:
        fh.write(json.dumps(e, ensure_ascii=False) + "\n")

write_json("artifacts/worker-059/f1_rev12_verdict/emitted_hashes.json",
           {"emitted_at": TS_COLON, "events": len(E), "artifact_hashes": H,
            "review_sha256": H["review"], "reviewed_sha256": REVIEWED,
            "check_summary": ev["check_summary"], "mutant_summary": ev["mutant_summary"]})
print(json.dumps({"events_appended": len(E), "outbox": OUTBOX, "hashes": H,
                  "checkpoint_id": checkpoint["checkpoint_id"]}, indent=1))
