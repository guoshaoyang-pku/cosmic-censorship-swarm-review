"""Controller event emission for the astra-lifecycle-08 pass (idempotent).

Emits hash-bound gate records (with refreshed `unmet` text; apply_events REC-40 now accepts
criteria/unmet/controller_note from authority gate events), TWO bounded assignments for the
genuinely new blocking work, and the pass-08 rulings. Re-running is safe: duplicate event_ids
are skipped by the accepted stream and already-sent inbox cards are not re-sent.

Measured at emission (fail-closed on the G-F0 taxonomy pin and the restored detector):
  F0 0abb9ed8a961 + companion d7419b4e8963; F1/F2a/F2b rev13 d9cebb9404b2 / e9a27996dfd3 /
  b2ab6acb2bbe under FROZEN rev29 815e08079aef; f1 suite 56bcb4b3234b; case corpus ccf7041bd0ff;
  L0 a1674f094979; L1 315c19145065; A0 rubric d748a9e3574e; A0 scope artifact; adjudication
  7714ffd5b467; detector a8c04fc31e4a (restored; pin c266dbecaa87; void e36b0d644ca preserved).

Rulings (REC-36..REC-42):
  G-F0 stays PASS at unchanged bytes (any taxonomy write voids it).
  G-FORM/G-LIT/G-NUM/G-AUDIT stay pending with refreshed hash-bound `unmet` lists.
  REC-36 ONE authorized formulation revision (rev14 / FROZEN rev30) folds the F2b D1/D2 content
    repairs, the F2a extension-category resolution, the token crosswalk, the SET level label,
    the f1-suite rebind and the acceptance-corpus rebind; bytes move, so every current verdict
    is void and r3 re-runs at the new pins.
  REC-37 scc_* conclusion tokens are canonical for class schemas; F0's strong_* entries are
    alias forms per VOCAB_ALIASES policy; HF-075-F2a/F2b-VOCAB are alias-vs-canonical
    presentation conflicts to discharge by pinned crosswalk + re-review, NOT by an F0 write.
  REC-38 CLASSSEP adjudication review satisfied by two independent non-author accepts
    (worker-030 4.0, worker-045 4.5); detector writes stay frozen.
  REC-39 F2b coverage divergence (scan 4 accepts vs lead census 0/7) -> CF-31; r3 must publish
    a per-file binding table before any G-FORM movement.
  REC-40 gate-text refresh via apply_events optional fields; stale G-F0/G-FORM `unmet` replaced.
  REC-41 stage-B R03 literal-substring binder defect -> bounded owner fix; held-out numbers do
    not count as gate evidence until re-run.
  REC-42 numerics_lock stays LOCKED; no N1; G-NUM would certify N0 only.

  python3 research_map/astra_lifecycle_08_events.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research_map"))
import comms  # noqa: E402

CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")


def measure(rel: str) -> str:
    p = ROOT / rel
    if not p.is_file():
        raise SystemExit(f"FAIL-CLOSED: pinned path absent: {rel}")
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


F0 = measure("research_map/formulation_taxonomy.yaml")
F0_SUP = measure("artifacts/formulation/formulation_taxonomy.yaml")
F1 = measure("schemas/af_wcc_vacuum.yaml")
F2A = measure("schemas/af_scc_c2_vacuum.yaml")
F2B = measure("schemas/af_scc_c0_vacuum.yaml")
FROZEN = measure("artifacts/formulation/FROZEN.json")
SUITE = measure("schemas/f1_falsifier_tests.jsonl")
CASES = measure("schemas/taxonomy_cases.jsonl")
L0 = measure("ledger/theorems.jsonl")
L1 = measure("ledger/citation_audit.csv")
A0 = measure("evaluation_rubric.yaml")
A0SCOPE = measure("evaluation/A0_detector_scope_adjudication.json")
PROTO = measure("numerics/CONVERGENCE_PROTOCOL.md")
NGATES = measure("numerics/gates.py")
N0REV3 = measure("numerics/results/flat_wave_convergence_rev3.json")
ADJ = measure("reviews/CLASSSEP-calibration-adjudication.json")
W030 = measure("reviews/CLASSSEP-adjudication-review-030.json")
W045 = measure("artifacts/worker-045/classsep_r3_indep_review/report.json")
W075 = measure("artifacts/worker-075/f2b_defect_reconciliation/reconciliation.json")
W029 = measure("artifacts/worker-029/f1_suite_materiality/report.json")
DET = measure("research_map/class_separation.py")
REG = measure("runtime/bin/classsep_regression.py")

F0_PASS = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
DET_PIN = "c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920"
DET_RESTORED = "a8c04fc31e4afa1b691cd6bfb6bf8b4f953a0adc925939a8351bab9cf453c5bd"
DET_VOID = "e36b0d644ca75b1efc291b44a3188facb7839d81790073341431f3bb77b86eed"
if F0 != F0_PASS:
    raise SystemExit(f"FAIL-CLOSED: G-F0 taxonomy pin moved: {F0[:12]} != {F0_PASS[:12]}")
if DET != DET_RESTORED:
    raise SystemExit(f"FAIL-CLOSED: detector is not the restored adjudicated bytes: {DET[:12]}")
if not (ROOT / "runtime/state/controller_verification/class_separation.e36b0d644ca.evidence.py").is_file():
    raise SystemExit("FAIL-CLOSED: void-revision evidence copy absent")
if hashlib.sha256((ROOT / "runtime/state/controller_verification/class_separation.e36b0d644ca.evidence.py").read_bytes()).hexdigest() != DET_VOID:
    raise SystemExit("FAIL-CLOSED: void-revision evidence copy hash mismatch")

DEC07 = "runtime/state/controller_verification/astra-lifecycle-07-decisions.json"
DEC08 = "runtime/state/controller_verification/astra-lifecycle-08-decisions.json"
FORENSICS = "runtime/state/controller_verification/cf29-detector-write-forensics.json"
Q_ASTRA = "runtime/state/comms_quarantine/astra-inbox-line3-20260912T0112.jsonl"
Q_AUDIT = "runtime/state/comms_quarantine/astra-lead-audit-inbox-lines24-25-27-20260912T0112.jsonl"

# ---------------------------------------------------------------- gate records
GATES = [
    {
        "event_id": "astra-life08-gate-gf0", "event_type": "gate", "actor": "astra",
        "created_at": NOW, "gate_id": "G-F0", "scope": "F0", "verdict": "pass",
        "owner": "lead-formulation", "eta": "0.0d",
        "criteria": (
            "Re-asserted MET at unchanged bytes: declared taxonomy " + F0[:12] + " (rev5) + "
            "companion class-contract supplement " + F0_SUP[:12] + " (REC-3: distinct artifacts, "
            "byte-identity not required); pass-08 gate audit counts 7 distinct independent accept "
            "reviewers at the measured hash (deepseek-flash-18, deepseek-flash-19, worker-025, "
            "worker-038, worker-041, worker-052, worker-078) with worker-094 revise noted; 6/6 "
            "disjointness pairs; bytes stable across passes 04-08. Any write to "
            "research_map/formulation_taxonomy.yaml voids this verdict and requires fresh accepts "
            "at the new hash."),
        "unmet": [],
        "controller_note": (
            "Pass-08 refresh (REC-40): the stale pending-era unmet list and note (revision "
            "66bf917bd368) are discharged. G-F0 is PASS at " + F0[:12] + "; the taxonomy is a "
            "no-write artifact for the rev14 repair window."),
        "evidence_refs": ["research_map/formulation_taxonomy.yaml#" + F0[:12],
                          "artifacts/formulation/formulation_taxonomy.yaml#" + F0_SUP[:12],
                          "research_map/research_map.json#controller_gate_audit", DEC08],
    },
    {
        "event_id": "astra-life08-gate-gform", "event_type": "gate", "actor": "astra",
        "created_at": NOW, "gate_id": "G-FORM", "scope": "F1,F2a,F2b", "verdict": "pending",
        "owner": "lead-formulation", "eta": "1.5d",
        "criteria": (
            "Measured pins at emission: F1 " + F1[:12] + ", F2a " + F2A[:12] + ", F2b " + F2B[:12]
            + " under FROZEN rev29 " + FROZEN[:12] + ", f1 suite " + SUITE[:12] + ", case corpus "
            + CASES[:12] + "; all three mirror pairs aligned. REC-36 authorizes ONE revision "
            "(rev14 / FROZEN rev30) folding: F2b D1 must_not_conflate containment denial + D2 "
            "'C2 is strictly larger' inversion; F2a extension-manifold category pin or a pinned "
            "category-independence rebuttal; the scc_*/strong_* crosswalk per REC-37; the SET "
            "predicate-vs-class strength label in VARIANT_REGISTRY.json + SET delta + "
            "check_variant_registry.py; the f1-suite rebind (25 rows, F1-AMB-25 f0_sha, "
            "re-observation of F1-AMB-11/17/23) per worker-029 " + W029[:12] + "; and the "
            "acceptance-corpus rebind (CF-32). Any byte move voids every current verdict, "
            "including the 4 hash-bound F2b accepts; r3 re-runs at the new pins. No gate moves "
            "on counts alone."),
        "unmet": [
            "F2b b2ab6acb2bbe has confirmed internal content defects (D1 containment denial, D2 "
            "size-premise inversion) and a contested coverage count: the controller hash scan "
            "finds 4 full accepts while the formulation lead's per-file census finds 0 accept / 7 "
            "revise (CF-31). No G-FORM movement until the binding table resolves the count.",
            "F2a e9a27996dfd3 carries HF-075-F2a-EXTCAT (extension-manifold category unpinned, "
            "reproduced as HF-091-02): pin the category or land a pinned category-independence "
            "rebuttal in rev14.",
            "The conclusion_type token conflict (F0 strong_cosmic_censorship_C2/_C0 vs schema "
            "scc_c2/scc_c0_future_inextendibility) is adjudicated by REC-37: scc_* is canonical "
            "for class schemas, F0 entries are alias forms; discharge by a pinned crosswalk + "
            "assertion-correct consistency check, never by an F0 write.",
            "Acceptance pipeline non-reproducible at rev29 (run_acceptance.py exit 3, stale corpus "
            "base 1bb78ce9b357 vs live b2ab6acb2bbe) and FORM-HELDOUT-10 invalid by construction "
            "(stage-B R03 binder rejects untouched canonical F1): CF-32, REC-36/REC-41.",
            "Post-rev14: r3 must re-measure coverage from reviews/*.json at the new per-file pins "
            "and bind FROZEN rev30 plus each per-file pin (CF-27 moving-target rule).",
        ],
        "controller_note": (
            "Pass-08 refresh: the stale rev11-era unmet list is discharged and replaced. The "
            "gate stays pending by evidence, not by text."),
        "evidence_refs": ["schemas/af_wcc_vacuum.yaml#" + F1[:12],
                          "schemas/af_scc_c2_vacuum.yaml#" + F2A[:12],
                          "schemas/af_scc_c0_vacuum.yaml#" + F2B[:12],
                          "schemas/f1_falsifier_tests.jsonl#" + SUITE[:12],
                          "artifacts/formulation/FROZEN.json#" + FROZEN[:12],
                          "artifacts/worker-075/f2b_defect_reconciliation/reconciliation.json#" + W075[:12],
                          "artifacts/worker-029/f1_suite_materiality/report.json#" + W029[:12],
                          "research_map/research_map.json#controller_gate_audit", DEC08],
    },
    {
        "event_id": "astra-life08-gate-glit", "event_type": "gate", "actor": "astra",
        "created_at": NOW, "gate_id": "G-LIT", "scope": "L0,L1", "verdict": "pending",
        "owner": "lead-literature", "eta": "1.0d",
        "criteria": (
            "L0 measured " + L0[:12] + " (rev3-final): 2 distinct full accepts (worker-075 4.0, "
            "worker-079) against 5 revise (worker-025, worker-011, worker-093, deepseek-flash-18, "
            "worker-005) and 1 inconclusive (worker-063); worker-075's report also files two "
            "rubric-scope objections (HF-02 multi-class rows exist but are relation/variant "
            "mentions, not a union-class definition; HF-01 fires because ledger rows carry no "
            "artifact_refs field). astra-life05-verify-l0-final must adjudicate whether the "
            "accepts bind the primary-source ledger or a card subset. L1 measured " + L1[:12] +
            " with 24 independent re-fetch spot checks binding this hash (>=3 required); the L1 "
            "locator adjudication (worker-025: 71/97 exact_locator values are search queries, not "
            "record locators; worker-075/079 replicate on samples) is a live revise and must be "
            "dispositioned. No gate moves on spot checks alone."),
        "unmet": [
            "L0 verdict split 2 accept / 5 revise / 1 inconclusive at a1674f094979 is "
            "unadjudicated: verify-l0-final must state which findings are rubric-scope vs "
            "ledger defects and whether a second accept binds.",
            "L1 locator finding (worker-025 71/97, replicated by worker-079 67/97 and "
            "worker-075 on 3 sampled rows) needs an owner disposition: repair the ledger "
            "locators, or record the finding as scope-limited and re-review at the same hash.",
            "The G-LIT unmet figure '201 citations' is not a measured universe (worker-075 "
            "source-meta census: 151 unique sources / 77 theorems / 228 union / 388 class rows); "
            "gate text must cite one measured universe.",
        ],
        "controller_note": "Pass-08 refresh of the stale L0-era unmet list; L0/L1 bytes unchanged.",
        "evidence_refs": ["ledger/theorems.jsonl#" + L0[:12],
                          "ledger/citation_audit.csv#" + L1[:12],
                          "reviews/L0-review-075-rev3.json",
                          "reviews/L0-review-worker-079.json",
                          "artifacts/worker-075/source_meta_census/source_meta_census_075.json",
                          "research_map/research_map.json#controller_gate_audit", DEC08],
    },
    {
        "event_id": "astra-life08-gate-gnum", "event_type": "gate", "actor": "astra",
        "created_at": NOW, "gate_id": "G-NUM", "scope": "N0", "verdict": "pending",
        "owner": "lead-numerics", "eta": "1.0d",
        "criteria": (
            "self-gravitating numerics remain LOCKED (solver_absent=True, guard_present=True, "
            "live re-check at emission); protocol " + PROTO[:12] + " criterion C8 is MET (standing "
            "accept 4.5 binds this hash); N0 node verdict on disk is revise 3.5 and the stop-rule "
            "deliverable " + N0REV3[:12] + " still needs: (1) a fourth resolution rung or a scoped "
            "3-level order with tolerance justification; (2) class re-binding to declared F0 rev5 "
            + F0[:12] + "; (3) one independent replication verdict at the frozen run hash. Guard "
            "and gates code: " + NGATES[:12] + ". N1 remains forbidden regardless: it additionally "
            "requires G-FORM and G-AUDIT (numerics_lock required_gates)."),
        "unmet": [
            "N0 node verdict is revise 3.5 (N0-pin-split-adjudication-worker-081.json); no N0 "
            "accept at one measured hash exists.",
            "Stop-rule items 1-3 above are open (astra-life04-n0-stoprule, lead-numerics, 02:30; "
            "astra-life04-n0-verify, lead-audit, 03:00).",
            "G-NUM passing would certify N0 only; N1 stays locked behind G-FORM + G-AUDIT.",
        ],
        "controller_note": (
            "Pass-08 lock ruling (REC-42): no N1 allocation, no solver code, no self-gravitating "
            "run in this pass; N0 work is the only permitted numerics."),
        "evidence_refs": ["numerics/CONVERGENCE_PROTOCOL.md#" + PROTO[:12],
                          "numerics/results/flat_wave_convergence_rev3.json#" + N0REV3[:12],
                          "numerics/gates.py#" + NGATES[:12],
                          "research_map/research_map.json#numerics_lock",
                          "research_map/research_map.json#controller_gate_audit", DEC08],
    },
    {
        "event_id": "astra-life08-gate-gaudit", "event_type": "gate", "actor": "astra",
        "created_at": NOW, "gate_id": "G-AUDIT", "scope": "A0,A1", "verdict": "pending",
        "owner": "lead-audit", "eta": "1.0d",
        "criteria": (
            "A0 rubric " + A0[:12] + " exists; A0 detector-scope artifact " + A0SCOPE[:12] +
            " landed unverified and the on-disk A0 verdicts are 6 revise (astra-life04-verify-a0 "
            "must land one independent verdict stating each prior finding resolved/unresolved/out "
            "of scope; astra-life05-a0-detector-scope must bound the detector scan to canonical + "
            "live build inputs). A1 coverage at measured hashes: F0 7, F1 4, F2a 2, F2b 4 by scan "
            "vs 0 by census (CF-31), L0 2 distinct accepts; no A1 full accept exists. The CLASSSEP "
            "r3 adjudication " + ADJ[:12] + " decision (c) is now independently reviewed by two "
            "non-authors (worker-030 accept 4.0 at " + W030[:12] + "; worker-045 accept 4.5 at "
            + W045[:12] + "), discharging the pass-07 review assignment (REC-38); the A1 node "
            "verdict at the frozen detector is still not landed. G-AUDIT stays pending; no gate "
            "self-pass."),
        "unmet": [
            "A0: 6 revise verdicts on disk at d748a9e3574e; no accept. Detector scope artifact is "
            "unverified.",
            "A1: no full accept at the measured hashes; CF-31 coverage divergence must be "
            "adjudicated before any A1 coverage claim binds.",
            "CLASSSEP instrument write freeze continues (detector " + DET[:12] + "); the audit "
            "lead may not author the instrument it measures.",
        ],
        "controller_note": "Pass-08 refresh of the stale A0-era unmet list.",
        "evidence_refs": ["evaluation_rubric.yaml#" + A0[:12],
                          "evaluation/A0_detector_scope_adjudication.json#" + A0SCOPE[:12],
                          "reviews/CLASSSEP-calibration-adjudication.json#" + ADJ[:12],
                          "reviews/CLASSSEP-adjudication-review-030.json#" + W030[:12],
                          "artifacts/worker-045/classsep_r3_indep_review/report.json#" + W045[:12],
                          "research_map/research_map.json#controller_gate_audit", DEC08],
    },
]

# ---------------------------------------------------------------- assignments
CARD = dict(event_type="assignment", actor="astra", created_at=NOW)
ASSIGNMENTS = [
    {
        **CARD, "event_id": "astra-life08-formulation-rev14",
        "node_id": "F1,F2a,F2b", "assignee": "astra-lead-formulation", "gate": "G-FORM",
        "class_id": "AF-WCC-VAC-GEN,AF-SCC-C2-VAC-GEN,AF-SCC-C0-VAC-GEN",
        "artifact": "artifacts/formulation/FROZEN.json",
        "deadline": "2026-09-12T02:15:00+08:00", "budget_agent_hours": 2.0,
        "supersedes": "astra-life05-evidence-binding-repair (scope: FROZEN manifest + schema repair set)",
        "evidence_refs": [
            "artifacts/worker-075/f2b_defect_reconciliation/reconciliation.json#" + W075[:12],
            "artifacts/worker-075/f2b_defect_reconciliation/candidate/repair_spec_dryrun__af_scc_c0_vacuum.yaml#a6724e72bba3",
            "artifacts/worker-029/f1_suite_materiality/report.json#" + W029[:12],
            "artifacts/formulation/tools/run_acceptance.py:54-63",
            "schemas/f1_falsifier_tests.jsonl#" + SUITE[:12],
            "artifacts/formulation/VOCAB_ALIASES.json",
            "artifacts/formulation/rule_spec.json",
            "research_map/formulation_taxonomy.yaml#" + F0[:12],
            "artifacts/formulation/FROZEN.json#" + FROZEN[:12],
            DEC08,
        ],
        "acceptance": (
            "ONE authorized revision (rev14; FROZEN rev30) that folds exactly these repairs and "
            "nothing else: (1) F2b must_not_conflate[0] containment denial -> the F2a corrected "
            "wording (nested extension sets recorded in implication_ledger; keep the 'strictly "
            "between' ban); (2) F2b 'C2 is a strictly larger extension class' -> direction-correct "
            "'C2 is a strictly stronger regularity requirement (E_C2 subset of E_C0)'; mutation "
            "controls (worker-053 M5 family) must still pass; (3) F2a extension-manifold category "
            "pinned (smooth/C-infinity/C2-atlas token with stated reason) OR a pinned "
            "category-independence rebuttal that a reviewer can falsify; (4) per REC-37, keep "
            "class-schema conclusion_type = scc_c2/scc_c0_future_inextendibility (canonical) and "
            "add a pinned crosswalk artifact mapping F0's strong_cosmic_censorship_C2/_C0 alias "
            "entries + a consistency check that compares schema tokens to the VOCAB_ALIASES "
            "canonical mapping rather than to F0's raw alias list; (5) SET strength label: "
            "VARIANT_REGISTRY.json and the SET delta get a level-qualified wording "
            "(predicate-level label, class-level subject) plus an assertion-correct SET clause in "
            "check_variant_registry.py; (6) f1_falsifier_tests.jsonl: rebind all 25 rows to the "
            "live F1 pin, repair F1-AMB-25 f0_binding.declared_f0_sha256 -> " + F0[:12] + " and "
            "its binding_note, and re-observe F1-AMB-11/F1-AMB-17/F1-AMB-23 against the rev13 "
            "text (worker-029 spec); (7) acceptance-corpus rebind: re-run "
            "measure_semantic_escape.py at the new pins and run_acceptance.py to exit 0 and "
            "re-pin the report, or record the pinned acceptance report non-reproducible and "
            "exclude it from gate evidence (CF-32). Publish the three mirror pairs byte-identically, "
            "re-issue FROZEN with per-file pins, write the rollback copy, re-run every formulation "
            "checker with 0 pin drift, and report the pre/post hashes. NO write to "
            "research_map/formulation_taxonomy.yaml (voids G-F0), no detector write, no ledger or "
            "claim edit, no gate verdict. Current review verdicts are void once bytes move."),
        "expected_information_gain": (
            "Clears every evidence-backed G-FORM content blocker in one byte-stable revision so "
            "r3 can re-dispatch on a single reproducible manifest instead of a moving target."),
        "falsifier": (
            "A revision that moves bytes outside the seven-item scope; a taxonomy write; a mirror "
            "pair left divergent; a claimed acceptance run that still exits nonzero; or a FROZEN "
            "manifest whose per-file pins do not resolve to the published bytes."),
        "stop_rule": (
            "If any fold requires editing the F0 taxonomy, the detector, the ledger, or an "
            "artifact owned by another agent, STOP and report the item as out of scope rather "
            "than editing it. No gate self-pass; r3 is the gate path."),
    },
    {
        **CARD, "event_id": "astra-life08-stageb-r03",
        "node_id": "A1", "assignee": "worker-006", "gate": "G-FORM",
        "class_id": "AF-WCC-VAC-GEN,AF-SCC-C2-VAC-GEN,AF-SCC-C0-VAC-GEN",
        "artifact": "artifacts/worker-06/spec_conformance_audit.py",
        "deadline": "2026-09-12T02:30:00+08:00", "budget_agent_hours": 1.0,
        "evidence_refs": [
            "artifacts/worker-06/spec_conformance_audit.py",
            "schemas/af_wcc_vacuum.yaml#" + F1[:12],
            "artifacts/formulation/evidence/acceptance_pipeline_report.json",
            DEC08,
        ],
        "acceptance": (
            "Bounded stage-B binder fix: R03 currently rejects the UNTOUCHED frozen canonical F1 "
            + F1[:12] + " by literal-substring matching, so FORM-HELDOUT-10 is invalid by "
            "construction and every held-out escape number certifies nothing. Make the binder "
            "accept the canonical tuple form, or emit the exact literal the schema must declare "
            "and prove that no other stage-B rule degrades. Add a mutation control (a deliberately "
            "mangled F1 must still be rejected) and re-run FORM-HELDOUT-10 and FORM-HELDOUT-07 "
            "under the fixed binder, publishing manifest + report hashes. No canonical schema "
            "edit, no gate verdict, no N1 work."),
        "expected_information_gain": (
            "Restores the held-out corpus as a valid falsifier for G-FORM/G-AUDIT; without it "
            "the only out-of-sample signal is void."),
        "falsifier": (
            "The fixed binder accepts a mutated F1 that violates the bound rule, or a re-run "
            "held-out report whose input manifest does not hash to the pinned corpus."),
        "stop_rule": (
            "Stop if the fix requires a canonical schema byte change: report that the schema "
            "literal is the blocker and route it into rev14 instead."),
    },
]

# ------------------------------------------------------------------- notices
NOTICES = [
    {
        "event_id": "astra-life08-notice-classsep-review-satisfied", "event_type": "status",
        "actor": "astra", "created_at": NOW, "node_id": "A1", "status": "active", "hours": 0.1,
        "summary": (
            "Controller ruling (REC-38): the pass-07 open assignment "
            "astra-life07-classsep-adjudication-review (worker-075) is SATISFIED by two "
            "independent non-author accepts at the frozen adjudication " + ADJ[:12] + ": worker-030 "
            "accept 4.0 (51/51 checks, reviews/CLASSSEP-adjudication-review-030.json#" + W030[:12] +
            ") and worker-045 accept 4.5 (report " + W045[:12] + ", with an append-only "
            "attribution-correction addendum). Both reproduce decision (c) - assertion-vs-mention "
            "is not lexically separable, no adoption, no claim retirement, residual hard count 19 "
            "+ A04 clause FN - so a third review is redundant and is not required. Worker-075 "
            "self-selected the F2b defect reconciliation instead (recorded, not a fault). The "
            "detector freeze continues: live bytes " + DET[:12] + ", active pin " + DET_PIN[:12] +
            ", void revision " + DET_VOID[:12] + " preserved as evidence; any further write voids "
            "the round. The A1 node verdict at the frozen instrument remains the audit lead's "
            "work and G-AUDIT stays pending."),
        "evidence_refs": ["reviews/CLASSSEP-calibration-adjudication.json#" + ADJ[:12],
                          "reviews/CLASSSEP-adjudication-review-030.json#" + W030[:12],
                          "artifacts/worker-045/classsep_r3_indep_review/report.json#" + W045[:12],
                          "research_map/class_separation.py#" + DET[:12], FORENSICS, DEC08],
        "next_falsifier": "A detector write while the review window is open, or a review that "
                          "cannot reproduce a cited count at a named hash.",
    },
    {
        "event_id": "astra-life08-notice-cf31-binding", "event_type": "status", "actor": "astra",
        "created_at": NOW, "node_id": "F1,F2a,F2b", "status": "active", "hours": 0.1,
        "summary": (
            "Controller finding (CF-31, REC-39): at measured F2b " + F2B[:12] + " the hash-bound "
            "review scan reports 4 distinct full accepts (worker-052, worker-071, worker-072, "
            "worker-090) while the formulation lead's per-file census at the same bytes reports 0 "
            "accept / 7 revise (worker-066 x2, worker-035, worker-017, worker-075, worker-018, "
            "worker-053). The two reviewer sets are disjoint, so at least one method is wrong; "
            "review files are mutable under fixed names (worker-045 accept->revise 29s after a "
            "scan; worker-075 accept->revise 2m19s after it). astra-life05-verify-gform-r3 must "
            "publish a per-file binding table at the measured hash - filename, reviewer, verdict, "
            "reviewed_sha256, verdict mtime, full-schema flag, independence basis - and state "
            "which count is correct and why the other is wrong, BEFORE any G-FORM movement. "
            "Coverage is re-measured from disk at use time; the controller_gate_audit scan is an "
            "index, not evidence. Bytes move after rev14, so this table is a calibration exercise "
            "at the current pins and r3 re-runs afterwards at the new pins."),
        "evidence_refs": ["schemas/af_scc_c0_vacuum.yaml#" + F2B[:12],
                          "runtime/state/controller_verification/lifecycle_20260912-011239.json",
                          "comms/outbox/astra-lead-formulation.jsonl",
                          "research_map/research_map.json#controller_findings", DEC08],
        "next_falsifier": "A binding table that omits a hash-bound verdict file, or counts a "
                          "verdict whose reviewed_sha256 is not the measured pin.",
    },
    {
        "event_id": "astra-life08-notice-cf32-pipeline", "event_type": "status", "actor": "astra",
        "created_at": NOW, "node_id": "F1,F2a,F2b", "status": "active", "hours": 0.1,
        "summary": (
            "Controller finding (CF-32, REC-36/REC-41): the G-FORM evidence pipeline is not "
            "reproducible at rev29 and the held-out corpora are invalid by construction. (i) "
            "run_acceptance.py exits 3: the rebased semantic-escape corpus binds base "
            "1bb78ce9b357 (rev11 C0) while canonical C0 measures " + F2B[:12] + ", yet the pinned "
            "acceptance_pipeline_report.json still records 3/3 pass and union_caught 31/31 - it "
            "cannot be regenerated from live bytes. (ii) stage-B spec_conformance_audit.py rejects "
            "the untouched frozen F1 " + F1[:12] + " on R03 (literal-substring binder defect), so "
            "FORM-HELDOUT-10 and its escape numbers certify nothing (astra-life08-stageb-r03). "
            "Neither item is a gate evidence source until repaired and re-run; rev14 folds the "
            "corpus rebind and the binder fix lands in the stage-B tree."),
        "evidence_refs": ["artifacts/formulation/evidence/semantic_escape_rebased.json",
                          "artifacts/formulation/tools/run_acceptance.py:54-63",
                          "artifacts/worker-06/spec_conformance_audit.py",
                          "artifacts/formulation/evidence/acceptance_pipeline_report.json",
                          "comms/outbox/astra-lead-formulation.jsonl",
                          "research_map/research_map.json#controller_findings", DEC08],
        "next_falsifier": "A gate decision that cites the pinned acceptance report or a held-out "
                          "escape number without a post-fix re-run at pinned manifests.",
    },
    {
        "event_id": "astra-life08-notice-gate-text-refresh", "event_type": "status", "actor": "astra",
        "created_at": NOW, "node_id": "F0,F1,F2a,F2b", "status": "active", "hours": 0.1,
        "summary": (
            "Controller repair (REC-40): the formulation lead's gate-text staleness blocker is "
            "discharged. research_map/apply_events.py now lets an authority gate event refresh "
            "criteria/unmet/controller_note/eta/owner, and the pass-08 gate records replace the "
            "stale unmet lists: G-F0.unmet is cleared (verdict pass at " + F0[:12] + "), G-FORM "
            "cites the live pins " + F1[:12] + "/" + F2A[:12] + "/" + F2B[:12] + " and the seven "
            "rev14 items instead of superseded hashes, G-LIT/G-NUM/G-AUDIT likewise. The "
            "operative rule stands: coverage and hashes are re-measured from disk at use time; "
            "the map scan and gate text are indexes, not evidence (endorsing "
            "lead-form-20260912T0113-107). No schema byte was touched by this repair."),
        "evidence_refs": ["research_map/apply_events.py",
                          "research_map/research_map.json#gates",
                          "comms/outbox/astra-lead-formulation.jsonl#lead-form-20260912T0113-109",
                          DEC08],
        "next_falsifier": "A gate record whose unmet text names a hash that is not the measured "
                          "pin at the time it is used.",
    },
    {
        "event_id": "astra-life08-notice-lock", "event_type": "status", "actor": "astra",
        "created_at": NOW, "node_id": "N0", "status": "active", "hours": 0.1,
        "summary": (
            "Controller ruling (REC-42): numerics_lock remains LOCKED; guard present, solver "
            "absent, N1 hash absent at emission; no N1 allocation and no self-gravitating work in "
            "this pass. G-NUM stays pending on the N0 stop rule: fourth rung or scoped 3-level "
            "order, class re-bind to F0 " + F0[:12] + ", and one independent replication verdict "
            "at the frozen run hash; then astra-life04-n0-verify lands the N0 verdict at one "
            "measured hash. G-NUM passing would certify N0 only; N1 additionally requires G-FORM "
            "+ G-AUDIT."),
        "evidence_refs": ["numerics/gates.py#" + NGATES[:12],
                          "numerics/CONVERGENCE_PROTOCOL.md#" + PROTO[:12],
                          "research_map/research_map.json#numerics_lock", DEC08],
        "next_falsifier": "Any solver/N1 artifact or an N1 hash appearing while locked.",
    },
]

NOTIFY = {
    "astra-life08-formulation-rev14": ["astra-lead-formulation"],
    "astra-life08-stageb-r03": ["worker-006"],
    "astra-life08-notice-classsep-review-satisfied": ["astra-lead-audit"],
    "astra-life08-notice-cf31-binding": ["astra-lead-audit"],
    "astra-life08-notice-cf32-pipeline": ["astra-lead-formulation", "astra-lead-audit"],
    "astra-life08-notice-gate-text-refresh": ["astra-lead-formulation"],
    "astra-life08-notice-lock": ["astra-lead-numerics"],
}


def _already_sent(agent: str, event_id: str) -> bool:
    p = ROOT / "comms" / "inbox" / f"{agent}.jsonl"
    if not p.exists():
        return False
    for line in p.read_text().splitlines():
        try:
            if json.loads(line).get("event_id") == event_id:
                return True
        except ValueError:
            continue
    return False


def main():
    for ev in GATES + ASSIGNMENTS + NOTICES:
        res = comms.append_event(ev)
        print(("APPENDED " if res.get("accepted") else "SKIPPED  ") + ev["event_id"] + " " + ev["event_type"])
    by_id = {e["event_id"]: e for e in ASSIGNMENTS + NOTICES}
    for eid, agents in NOTIFY.items():
        for agent in agents:
            if _already_sent(agent, eid):
                print(f"INBOX    already-sent <- {eid} [{agent}]")
                continue
            msg = dict(by_id[eid])
            msg["to"] = agent
            path = comms.send(agent, msg)
            print(f"INBOX    {path.relative_to(ROOT)} <- {eid} [{agent}]")
    print("pins:", json.dumps({"F0": F0[:12], "F0sup": F0_SUP[:12], "F1": F1[:12], "F2a": F2A[:12],
                               "F2b": F2B[:12], "FROZEN": FROZEN[:12], "suite": SUITE[:12],
                               "cases": CASES[:12], "L0": L0[:12], "L1": L1[:12], "A0": A0[:12],
                               "proto": PROTO[:12], "ngates": NGATES[:12], "N0rev3": N0REV3[:12],
                               "adjudication": ADJ[:12], "w030": W030[:12], "w045": W045[:12],
                               "w075": W075[:12], "w029": W029[:12],
                               "detector": DET[:12], "regression": REG[:12],
                               "detector_pin": DET_PIN[:12], "detector_void": DET_VOID[:12]}))


if __name__ == "__main__":
    main()
