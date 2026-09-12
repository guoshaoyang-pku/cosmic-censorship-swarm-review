#!/usr/bin/env python3
"""Emit worker-009's independent F1 review artifact + outbox events.
Aborts if the F1 hash moved off the bound revision (moving-target rule)."""
import json, hashlib, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST)
TS = NOW.strftime("%Y%m%dT%H%M%S")
BOUND = "9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503"

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()

F1 = ROOT / "schemas/af_wcc_vacuum.yaml"
cur = sha(F1)
if cur != BOUND:
    print(json.dumps({"status": "MOVING_TARGET_BLOCKER", "expected": BOUND, "measured": cur}))
    sys.exit(2)

EVID = ROOT / "artifacts/worker-009/f1_review/verify_f1_20260912T002709.json"
GATE = ROOT / "artifacts/worker-009/f1_review/form_gate_rerun.json"
FT = ROOT / "schemas/f1_falsifier_tests.jsonl"
TC = ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json"
CS = ROOT / "research_map/class_separation.py"
TAX_C = ROOT / "research_map/formulation_taxonomy.yaml"
TAX_A = ROOT / "artifacts/formulation/formulation_taxonomy.yaml"
RUB = ROOT / "evaluation_rubric.yaml"

ref = {
    "f1": f"schemas/af_wcc_vacuum.yaml#{cur[:12]}",
    "tax_c": f"research_map/formulation_taxonomy.yaml#{sha(TAX_C)[:12]}",
    "tax_a": f"artifacts/formulation/formulation_taxonomy.yaml#{sha(TAX_A)[:12]}",
    "rubric": f"evaluation_rubric.yaml#{sha(RUB)[:12]}",
    "evid": f"artifacts/worker-009/f1_review/verify_f1_20260912T002709.json#{sha(EVID)[:12]}",
    "gate": f"artifacts/worker-009/f1_review/form_gate_rerun.json#{sha(GATE)[:12]}",
    "ft": f"schemas/f1_falsifier_tests.jsonl#{sha(FT)[:12]}",
    "tc": f"artifacts/formulation/evidence/taxonomy_consistency.json#{sha(TC)[:12]}",
    "cs": f"research_map/class_separation.py#{sha(CS)[:12]}",
}

HF = [
 ("HF-009-1", "blocking-machine", "duplicate top-level YAML mapping keys: 'revised_at' x7 (lines 8,10,12,14,16,20,23) and 'revised_at_unused' x2 (26,28); yaml.safe_load is last-wins, so the parsed revision timestamp is 2026-09-12T00:30:00+08:00 and the revision timeline silently collapses. Spec violation, not a style choice.",
  "strict yaml.compose walk of the pinned bytes: top_level_duplicates={revised_at:7, revised_at_unused:2}; safe_load effective revised_at=2026-09-12T00:30:00+08:00; raw duplicate lines listed. Falsifier: a strict parser reports no duplicate top-level key and a unique revised_at."),
 ("HF-009-2", "blocking-clock", "future-dated machine-readable timestamps: effective revised_at and f0_binding.checked_at are both 2026-09-12T00:30:00+08:00 while wall clock at verification was 2026-09-12T00:27:09+08:00 (+170.8 s in the future). File mtime is 00:19:14, so the value was already future-dated when written (CF-14 clock discipline).",
  "verify_f1.py V3: skew seconds +170.8 for both fields; future_dated_at_write_time=true; still_future_dated_at_verify_time=true. Falsifier: a reader shows the effective timestamp is <= wall clock at read time."),
 ("HF-009-3", "blocking-binding-authority", "class_contract_pointer='artifacts/formulation/formulation_taxonomy.yaml#class_contracts.AF-WCC-VAC-GEN' does not resolve inside the authoritative canonical tree: research_map/formulation_taxonomy.yaml#276009f4f63d has no top-level class_contracts key at all (it carries definitions under 'classes'), while the authoring mirror c8e979a1eb48 does. taxonomy files are not byte-identical (35145 vs 20937 bytes). The declared F0 sha256 276009f4 matches the canonical file, but the pointer target exists only in the non-authoritative authoring tree.",
  "verify_f1.py V4: canonical class_contract_AF_WCC_canonical_json_sha256=null; authoring=0c40c4cb66ff; taxonomy_byte_identical=false; pointer_target_is_canonical_path=false. Falsifier: canonical contains class_contracts.AF-WCC-VAC-GEN and equals the authoring mirror byte-for-byte."),
 ("HF-009-4", "blocking-semantics", "the operative quantifier expansion uses WHOLE-CURVE single-q containment (quantifiers.formal:54-55 'gamma subset J^-(q)', quantifiers.domains.D5:79-81 'gamma([0,T))', visibility.witness_protocol:228) while the same file's canonical visibility predicate is TAIL-based (visibility.definition:220 'exists q in AND t0 in [0,T) such that gamma([t0,T)) ...', negation_conclusion:222). Whole-curve containment implies tail containment but not conversely, so the formal clause is strictly weaker than the declared conclusion and quantifiers.negation:84-88 does not negate quantifiers.formal. This triggers the artifact's own schema_falsifiers[0] ('two competent readers classify the same described spacetime differently').",
  "verify_f1.py V5 regex scan with line numbers; independently re-derived in this review, matching no other reviewer's text. Falsifier: a line in the pinned bytes where quantifiers.formal or D5 constrains a tail gamma([t0,T)) with a t0, or a proof that the two readings coincide for the geodesics of D4."),
 ("HF-009-5", "blocking-formalization", "D0 is a disjunction ('Sobolev variant s>5/2 and delta in (1/2,1), or the smooth-with-decay default', quantifiers.domains.D0:65) while quantifiers.formal:49 binds '(s,delta) in D0'; the smooth branch supplies no (s,delta) pair, so the binder is ill-typed on that branch, and the two branches carry different ambient topologies (weighted-Sobolev subspace topology at genericity.ambient_space:150 vs Frechet at genericity.topology_or_measure:151) although regularity.must_not_conflate:143 forbids transferring smooth statements to the Sobolev variant. This violates evaluation_rubric.yaml:126 'exact quantifier prefix (no roughly, essentially, or)' and :127 'data space named with topology + regularity + decay + constraint + end structure'. conclusion.statement_formal:251 also uses AF_{I+}(M_D), a symbol that occurs exactly once in the file and is defined nowhere.",
  "verify_f1.py V7 slot scan + rubric grep (evaluation_rubric.yaml:126); independent line read of 47-66, 135-147, 246-252. Falsifier: a type-correct instantiation of (s,delta) over the smooth-with-decay branch, or a definition of AF_{I+} in the pinned bytes."),
]

FIND = [
 ("P-009-1", "pass", "required slots", "all eight required slots present and non-empty at the bound hash: quantifiers, topology, regularity, genericity, i_plus, visibility, conclusion.conclusion_type=weak_cosmic_censorship, falsifier; class_id=AF-WCC-VAC-GEN single-valued."),
 ("P-009-2", "pass", "class leakage / C0-C2 merge", "research_map/class_separation.py findings_for_text -> [] at module sha c266dbceca87; anti_scope names AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN, AF-WCC-SCALAR-SPH; extension_regularity is null. No C0/C2 merge detected."),
 ("P-009-3", "pass", "independent structural gate re-run", "FORM-GATE-01 v1.1 re-executed by this review: exit 0, verdict pass, failed_rules [], 16 rules pass with R16 skipped (SCC-only), target sha 9a8bd4c96800."),
 ("P-009-4", "pass", "F1 publication alignment", "schemas/af_wcc_vacuum.yaml and artifacts/formulation/schemas/af_wcc_vacuum.yaml are byte-identical at 9a8bd4c96800; the canonical/authoring divergence is confined to the F0 pointer target, not to F1's own bytes."),
 ("P-009-5", "pass", "conclusion not inflated", "conclusion_type=weak_cosmic_censorship; forbidden_strengthenings include black-hole formation, geodesic completeness, C2/C0 inextendibility; epistemic_status=open_problem with a promotion rule requiring a checked proof artifact."),
 ("R-009-1", "refuted-claim", "falsifier-test binding drift", "the claim that schemas/f1_falsifier_tests.jsonl is 'bound to superseded binding_sha256 b65fcc0f0118' does NOT reproduce at the bound hash: all 25 rows carry binding_sha256=9a8bd4c96800 (file sha c4c477adcb7a, mtime 00:20:34). b65fcc0f appears only in historical fields prior_binding_sha256 / prior_binding_ref / prior_binding_at_authoring. Do not re-fix this as if open."),
 ("R-009-2", "carried-objection", "consistency evidence unbound", "artifacts/formulation/evidence/taxonomy_consistency.json records paths, consistent=true and contract_divergences=[] but no sha256 for either tree, so it cannot bind the comparison to the reviewed bytes; the '0 contract-text divergences' note cannot be reproduced from this file alone. Its half of the same claim stands."),
 ("N-009-1", "advisory", "stale self-reported review_status", "the artifact's review_status block still says independent_reviewers=[] and verdict=pending although at least four full-schema verdicts (revise) and two inconclusive verdicts exist on disk at the bound hash. Advisory only: the map, not the artifact, is the authority on reviews."),
]

review = {
 "schema_version": "a1-review/v1",
 "event_id": f"w009-f1-full-schema-review-{TS}",
 "event_type": "review",
 "created_at": NOW.isoformat(timespec="seconds"),
 "actor": "worker-009",
 "reviewer": "worker-009",
 "reviewer_independence": ("worker-009 is not an author of schemas/af_wcc_vacuum.yaml, research_map/formulation_taxonomy.yaml or any "
   "artifacts/formulation/ file; this session wrote only reviews/F1-review-009.json, artifacts/worker-009/f1_review/**, "
   "runtime/state/w009_*, and comms/outbox/worker-009.jsonl. No other reviewer's text is reused: every check was re-measured by "
   "artifacts/worker-009/f1_review/verify_f1.py; line numbers are the pinned bytes' own."),
 "target_id": "F1",
 "artifact": "schemas/af_wcc_vacuum.yaml",
 "class_id": "AF-WCC-VAC-GEN",
 "gate": "G-FORM",
 "reviewed_sha256": cur,
 "reviewed_bytes": F1.stat().st_size,
 "checked_at_hash": cur,
 "verdict": "revise",
 "score": 3.0,
 "score_rationale": ("Rich, unusually self-aware schema with all required slots, clean class separation and a working structural gate; "
   "blocked from accept by two machine/authority defects (duplicate keys, future-dated timestamps, pointer outside canonical tree) "
   "and two substantive content defects (formal quantifier uses the superseded whole-curve predicate, D0 disjoins two regularity "
   "classes under one binder). A revise verdict with concrete defects is the outcome the gate's own stop rule allows."),
 "counts_as_full_schema_verdict": True,
 "hard_failures": [f"{i} ({s}): {c}" for i, s, c, e in HF],
 "hard_failure_details": [{"id": i, "severity": s, "claim": c, "evidence": e} for i, s, c, e in HF],
 "findings": [{"id": i, "kind": k, "check": c, "detail": d} for i, k, c, d in FIND],
 "required_for_accept": [
   "One unique top-level revised_at <= wall clock (remove all duplicate YAML keys; a changelog belongs in a list or comments).",
   "One operative visibility predicate: update quantifiers.formal, quantifiers.domains.D4/D5 and visibility.witness_protocol to the tail formulation with an explicit t0, or register the whole-curve reading as a variant and never silently substitute it.",
   "Make D0 a single well-typed domain: either split the smooth and Sobolev branches into registered regularity variants with separate statements, or declare one branch as the class and the other as a registered variant; no 'or' under one binder (evaluation_rubric.yaml:126).",
   "Define AF_{I+}(M_D) in conclusion.statement_formal or remove the symbol.",
   "Repoint class_contract_pointer into the authoritative canonical tree and publish the referenced contract block byte-identically to canonical; refresh f0_binding after any F0 write.",
   "Advisory: refresh review_status to the on-disk verdicts once the above land."
 ],
 "evidence_refs": [ref["f1"], ref["evid"], ref["gate"], ref["tax_c"], ref["tax_a"], ref["rubric"], ref["ft"], ref["tc"], ref["cs"]],
 "falsifier": ("Any one of: (a) a strict YAML loader shows a unique top-level revised_at with value <= wall clock at the bound bytes; "
   "(b) research_map/formulation_taxonomy.yaml is shown to contain class_contracts.AF-WCC-VAC-GEN and to be byte-identical to the "
   "authoring mirror; (c) quantifiers.formal/D5/witness_protocol are shown to denote the same tail predicate as visibility.definition, "
   "or the two readings are proved equivalent for the D4 geodesics; (d) a type-correct instantiation of (s,delta) over the "
   "smooth-with-decay branch is exhibited; (e) the bound hash moves (verdict is void, report a moving-target blocker instead)."),
 "next_falsifier": ("Re-measure sha256(schemas/af_wcc_vacuum.yaml); if it is no longer 9a8bd4c96800 this verdict is void. Otherwise the next "
   "falsifier is a repaired revision that passes the six required_for_accept items, to be re-reviewed by two reviewers who did not author it."),
 "not_a_gate_verdict": "This is one independent reviewer verdict. It does not set node status, validation_status, or any gate verdict; only the controller and group leads may move those.",
 "supersedes_review": None,
}

rev_path = ROOT / "reviews/F1-review-009.json"
rev_path.write_text(json.dumps(review, indent=1) + "\n")
rev_sha = sha(rev_path)
evid_sha = sha(EVID); gate_sha = sha(GATE)

def ev(eid, typ, **kw):
    d = {"event_id": eid, "event_type": typ, "created_at": NOW.isoformat(timespec="seconds"), "actor": "worker-009"}
    d.update(kw); return d

events = [
 ev(f"w009-f1-artifact-review-{TS}", "artifact", node_id="F1", class_id="AF-WCC-VAC-GEN", artifact_type="review",
    path="reviews/F1-review-009.json", sha256=rev_sha, validation_status="unverified",
    evidence_refs=[ref["f1"], ref["evid"]],
    note="independent full-schema F1 verdict (revise); verdict file only, no gate movement claimed"),
 ev(f"w009-f1-artifact-verify-{TS}", "artifact", node_id="F1", class_id="AF-WCC-VAC-GEN", artifact_type="evidence",
    path="artifacts/worker-009/f1_review/verify_f1_20260912T002709.json", sha256=evid_sha, validation_status="unverified",
    evidence_refs=[ref["f1"]], note="raw measurement log: V1-V11 checks, strict YAML walk, predicate scan, census"),
 ev(f"w009-f1-artifact-gate-{TS}", "artifact", node_id="F1", class_id="AF-WCC-VAC-GEN", artifact_type="evidence",
    path="artifacts/worker-009/f1_review/form_gate_rerun.json", sha256=gate_sha, validation_status="unverified",
    evidence_refs=[ref["f1"]], note="FORM-GATE-01 v1.1 independent re-run at the bound hash: pass, exit 0"),
 ev(f"w009-f1-review-{TS}", "review", target_id="F1", reviewer="worker-009", verdict="revise", score=3.0,
    hard_failures=[h[0] + ": " + h[2][:200] for h in HF],
    findings=[f[0] + " (" + f[1] + "): " + f[2] for f in FIND],
    artifact="schemas/af_wcc_vacuum.yaml", artifact_refs=[f"reviews/F1-review-009.json#{rev_sha[:12]}"],
    reviewed_sha256=cur, class_id="AF-WCC-VAC-GEN", gate="G-FORM",
    evidence_refs=[ref["f1"], f"reviews/F1-review-009.json#{rev_sha[:12]}", ref["evid"], ref["gate"], ref["ft"], ref["tc"]],
    counts_as_full_schema_verdict=True,
    falsifier=review["falsifier"]),
 ev(f"w009-f1-status-{TS}", "status", node_id="F1", status="active", hours=0.6,
    summary=("Bounded class-bound task (worker-009): independent full-schema review of AF-WCC-VAC-GEN at "
             "schemas/af_wcc_vacuum.yaml#9a8bd4c96800. Verdict revise, score 3.0: 5 hard failures (duplicate YAML keys; "
             "future-dated revised_at/f0_binding.checked_at; class_contract_pointer resolves only outside the canonical tree; "
             "formal quantifier uses whole-curve single-q while visibility.definition is tail-based; D0 disjoins two regularity "
             "branches under one (s,delta) binder and statement_formal uses undefined AF_{I+}). 5 pass findings incl. clean "
             "class separation and FORM-GATE-01 pass; 1 rival claim refuted (falsifier-test binding actually current) and 1 carried."),
    evidence_refs=[ref["f1"], f"reviews/F1-review-009.json#{rev_sha[:12]}", ref["evid"], ref["gate"], ref["ft"], ref["tc"], ref["cs"]],
    next_falsifier="hash move voids the verdict; otherwise a repaired revision re-reviewed by two non-authors."),
]

out = ROOT / "comms/outbox/worker-009.jsonl"
with open(out, "a") as f:
    for e in events:
        f.write(json.dumps(e, sort_keys=True) + "\n")

print(json.dumps({"review_sha256": rev_sha, "evidence_sha256": evid_sha, "gate_report_sha256": gate_sha,
                  "f1_sha256_at_emit": cur, "event_ids": [e["event_id"] for e in events],
                  "outbox": str(out)}, indent=1))
