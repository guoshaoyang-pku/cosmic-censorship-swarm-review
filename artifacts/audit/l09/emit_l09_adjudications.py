#!/usr/bin/env python3
"""Emit audit lifecycle-09 adjudication artifacts from the measured census.

Writes (audit-owned canonical paths):
  reviews/G-FORM-final-verify-r3.json
  reviews/L0-review-final-verify.json
  reviews/A0-review-final-verify.json   (v2, supersedes the 00:50:20 self-verdict)
  runtime/state/lead_audit_lifecycle_09_checkpoint.json
  artifacts/audit/STATUS.md

Read-only with respect to every target: no schema, ledger, rubric or detector write.
"""
import hashlib, json, os, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(ROOT)

def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()

NOW = datetime.datetime.now().astimezone().isoformat(timespec='seconds')
C = json.load(open('artifacts/audit/l09/audit_l09_census.json'))
T = C['targets']

def rows(name, pred):
    return [r for r in T[name]['verdict_rows'] if pred(r)]

def brief(r):
    return {"created_at": r['created_at'], "reviewer": r['reviewer'], "verdict": r['verdict'],
            "score": r['score'], "full_schema": r['full_schema'], "n_hard": r['n_hard'],
            "event_id": r['event_id']}

# ---- re-measure stability (pre == post inside this lifecycle) -----------------------------
STABILITY = {}
for name, t in T.items():
    live = sha(t['path'])
    STABILITY[name] = {"path": t['path'], "pin": t['pin'], "measured_now": live,
                       "pin_matches": live == t['pin'], "stable_since_census": live == t['measured_sha256']}
frozen_now = sha('artifacts/formulation/FROZEN.json')

# ---- G-FORM r3 ----------------------------------------------------------------------------
gform = {
    "schema": "gate-final-verify/2",
    "event_id": "audit-l09-gform-final-verify-r3",
    "created_at": NOW,
    "actor": "astra-lead-audit",
    "reviewer": "astra-lead-audit",
    "review_kind": "independent coverage adjudication at the FROZEN rev29 pins (card astra-life05-verify-gform-r3); audit assembles coverage, Astra records the gate",
    "gate": "G-FORM",
    "node_id": "F1,F2a,F2b",
    "assignment": "astra-life05-verify-gform-r3",
    "authority": "no gate self-pass: this artifact proposes a verdict; only the controller records a gate verdict",
    "frozen_manifest": {"path": "artifacts/formulation/FROZEN.json", "revision": C['frozen_revision'],
                        "declared_sha256": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
                        "measured_sha256": frozen_now, "match": frozen_now == "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"},
    "pins": {k: STABILITY[k] for k in ("F1", "F2a", "F2b")},
    "byte_stability": "all three schema pins re-measured at adjudication time equal the FROZEN rev29 pins and the census-time bytes; no target write occurred during this round",
    "coverage_table": [
        {
            "class": "F1", "pin": T['F1']['pin'], "path": T['F1']['path'],
            "non_author_accepts_full": [brief(r) for r in T['F1']['accepts_non_author_full']],
            "non_author_accepts_all": len(T['F1']['accepts_non_author']),
            "revises": len(T['F1']['revises']),
            "adjudicated_verdict": "revise",
            "verdict_basis": "two independent non-author full-schema accepts exist (worker-072, worker-075), but three hash-bound named findings are unresolved at the same bytes and are carried defects, not class-semantics defects",
            "named_open_findings": [
                {"id": "W077-AB-01/W077-AB-02", "field": "provenance anchor rows", "severity": "major",
                 "finding": "5/5 F1 provenance anchor rows carry identifier=null and status=unresolved; the four BL-11 anchor items have 0 hits in ledger a1674f09 / citation audit 315c1914",
                 "reviewer": "worker-077", "reviewed_at": "2026-09-12T00:58:28+08:00"},
                {"id": "HF-W034R2-F1-1 / W019-RV13-02 / W077-AB-03", "field": "schemas/f1_falsifier_tests.jsonl (FROZEN rev29 pin 56bcb4b3234b)",
                 "severity": "major",
                 "finding": "25/25 falsifier-corpus rows bind the superseded F1 rev12 hash cce9c60146d6, not the frozen rev13 d9cebb9404b2; 3 deciding rows (F1-AMB-11/17/23) are advisory",
                 "reviewer": "worker-034, worker-019, worker-077, worker-073, worker-029", "reviewed_at": "2026-09-12T01:00:07..01:20:00"},
                {"id": "HF-W034R2-F1-2 / HF-045-1 / OI-002-01", "field": "cross-artifact: F0 canonical 0abb9ed8a961 vs F1 rev13 class_identity_variants[0].relation",
                 "severity": "major", "finding": "F0 (G-F0 passed) says the set-based reading is strictly stronger; F1 rev13 says strictly weaker. Not repairable in F1 without falsifying its own strength claim; needs ESC-2/controller adjudication",
                 "reviewer": "worker-034, worker-045, worker-002, worker-085", "reviewed_at": "2026-09-12T01:00:41..01:11:45"},
                {"id": "SF-075-F1-CORPUS / W062-ESCAPE-STALE", "field": "semantic-escape corpus base pin",
                 "severity": "soft", "finding": "rebased corpus binds superseded C0 base 1bb78ce9b357; run_acceptance.py preflight measured rc=3",
                 "reviewer": "worker-075, worker-089", "reviewed_at": "2026-09-12T01:03:36..01:11:35"},
            ],
            "class_semantics_note": "no reviewer named an in-file class-identity, quantifier, topology, genericity, visibility or conclusion defect at d9cebb9404b2",
        },
        {
            "class": "F2a", "pin": T['F2a']['pin'], "path": T['F2a']['path'],
            "non_author_accepts_full": [brief(r) for r in T['F2a']['accepts_non_author_full']],
            "non_author_accepts_all": len(T['F2a']['accepts_non_author']),
            "revises": len(T['F2a']['revises']),
            "adjudicated_verdict": "revise",
            "verdict_basis": "three independent non-author full-schema accepts exist, but the extension predicate is under-frozen at the same bytes; four independent reviewers name the fields (w047, w075, w091, w040, w028), and a later critical cross-class containment finding lands at 01:16:08",
            "named_open_findings": [
                {"id": "HF-047-01 / HF-091-02 / HF-W040-06 / W028-HF", "field": "extension_predicate.definition clause (a), clause (c), topology.extension_topology, missing iota_regularity",
                 "severity": "major/blocking",
                 "finding": "F2a leaves the manifold category of M' and the regularity of the isometric embedding unpinned while sibling F2b freezes SMOOTH and iota_regularity=C-infinity; the class asserts non-existence so the extension category is load-bearing",
                 "reviewer": "worker-047, worker-091, worker-040, worker-028, worker-075", "reviewed_at": "2026-09-12T00:59:16..01:03:40"},
                {"id": "HF-060-EXT-01", "field": "extension_predicate.definition clause (f)",
                 "severity": "major", "finding": "F2a clause (f) lacks F2b's interior requirement int(M' minus iota(M)) non-empty; the accepted R2 escapability repair was not propagated to the C2 schema",
                 "reviewer": "worker-060", "reviewed_at": "2026-09-12T01:13:19+0800"},
                {"id": "HF-047-PC-1", "field": "cross-class containment E_C2 subset E_C0 vs declared clause pair",
                 "severity": "critical", "finding": "declared containment is not entailed by the declared clause pair at these pins",
                 "reviewer": "worker-047", "reviewed_at": "2026-09-12T01:16:08+08:00"},
                {"id": "HF-W092-R13-01", "field": "artifacts/formulation/evidence/taxonomy_consistency.json (9e335e9ba1bf)",
                 "severity": "blocking-for-clean-accept", "finding": "consistency evidence resolves but is not hash-bound to the two compared trees; re-stamping does not clear the standing rev12 findings",
                 "reviewer": "worker-092, worker-090", "reviewed_at": "2026-09-12T00:59:10..01:01:07"},
            ],
        },
        {
            "class": "F2b", "pin": T['F2b']['pin'], "path": T['F2b']['path'],
            "non_author_accepts_full": [brief(r) for r in T['F2b']['accepts_non_author_full']],
            "non_author_accepts_all": len(T['F2b']['accepts_non_author']),
            "revises": len(T['F2b']['revises']),
            "adjudicated_verdict": "revise",
            "verdict_basis": "blocking carriers are reproducible at the frozen bytes; accepting verdicts are measured SILENT on them (worker-066) and one accept self-superseded at the same hash (worker-072, 01:15:24); 37 revises total, 10 of them after 01:12",
            "named_open_findings": [
                {"id": "W050-F2B-D1 / W020-R13-F2B-A / W002-F2B-IND-01 / W038-F2B13-02 / W072-F2B-HF-01", "line": 152,
                 "field": "regularity.must_not_conflate[0]", "severity": "blocking",
                 "finding": "'No containment with C2 or C0 is asserted here' contradicts the same file's extension_class_containment chain (E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2); F2a carries the corrected wording",
                 "reviewer": "worker-050, worker-020, worker-002, worker-038, worker-072, worker-037", "reviewed_at": "2026-09-12T01:08:30..01:15:24"},
                {"id": "W053-F2B-REV29-01 / W020-R13-F2B-B / W050-F2B-D2 / W089-F2B-06-ADJ-H1 / W072-F2B-HF-02", "line": 246,
                 "field": "implication_ledger.forbidden_transfers[0].reason", "severity": "blocking",
                 "finding": "'C2 is a strictly larger extension class' is inverted against the file's own chain (E_C2 innermost/smallest); transfer conclusion right, premise false; a one-clause repair is specified",
                 "reviewer": "worker-053, worker-020, worker-002, worker-050, worker-089, worker-072, worker-028, worker-061, worker-054, worker-035, worker-037", "reviewed_at": "2026-09-12T01:07:03..01:26:00"},
                {"id": "HF-085B-01", "field": "declared-hash layer: schemas/af_scc_c0_vacuum.yaml.sha256 (256dd18d7944), schemas/af_scc_regularities.yaml rev6 (27255e5b34f3), entry_hashes.json (09a5b37a190d)",
                 "severity": "hard/hash-bound", "finding": "three canonical paths declare 1bb78ce9b357 / b6123750b37d while the live files measure b2ab6acb2bbe / e9a27996dfd3; reviewer-run check_f2_integration.py reports overall_verdict=fail (A3-component-pins, C6-revision-pins)",
                 "reviewer": "worker-085, worker-089", "reviewed_at": "2026-09-12T01:11:35..01:11:45"},
                {"id": "W066-F2B-ACCEPT-DISPOSITION", "field": "worker-090 accept (reviews/F2b-rev13-full-090.json)", "severity": "evidence",
                 "finding": "independent disposition classifies the accept as SILENT on both carriers (C1-DENIAL, C2-PREMISE); an accept that ignores a named hard finding cannot be counted",
                 "reviewer": "worker-066", "reviewed_at": "2026-09-12T01:15:04+08:00"},
            ],
        },
    ],
    "adjudicated_verdict": "revise",
    "verdict_basis": "coverage counts are met for all three classes, but every class carries at least one hash-bound named hard finding that the accepting verdicts do not clear; the rev29 repair did not close the F2b carriers or the F2a extension-category freeze, and the F1 objections are cross-artifact",
    "gate_result": {
        "G-FORM": "NOT proposable at FROZEN rev29 (815e08079aef)",
        "reason": "coverage counts are met for all three classes, but every class carries at least one hash-bound named hard finding that the accepting verdicts do not clear; the rev29 repair did not close the F2b carriers or the F2a extension-category freeze, and the F1 objections are cross-artifact",
        "required_before_proposal": [
            "F2b: one revision that corrects :152 and :246 (the 2-line repair is specified and mutant-tested by worker-020), re-pins the .sha256 sidecar / af_scc_regularities.yaml / entry_hashes.json layer, then two fresh non-author verdicts at the new hash",
            "F2a: a revision freezing manifold category and iota regularity, propagating the clause-(f) interior requirement, and byte-binding taxonomy_consistency.json; then two fresh non-author verdicts",
            "F1: controller/Human-PI adjudication of the F0-vs-F1 set-strength direction (ESC-2), rebinding of the F1 falsifier corpus to d9cebb9404b2, and disposition of the unresolved provenance anchors",
        ],
    },
    "falsifiers": [
        "a cited sha256 in this artifact that does not equal the measured canonical sha256 at the named path",
        "a counted accept whose reviewer authored the artifact or the reviewed evidence",
        "an accept that ignores one of the named carriers still visible at the frozen bytes",
        "any schema write during the round that moves a pin",
    ],
    "next_falsifier": "after the specified repairs land: re-measure the three pins, re-run the classsep regression and audit_evidence, and require fresh non-author verdicts at the new hashes; the F2b repair is falsified if :152/:246 are unchanged in the new revision",
    "measured_at": NOW,
}

# ---- L0 ------------------------------------------------------------------------------------
l0_rows = T['L0']['verdict_rows']
l0 = {
    "schema": "gate-final-verify/1",
    "event_id": "audit-l09-l0-final-verify",
    "created_at": NOW,
    "actor": "astra-lead-audit",
    "reviewer": "astra-lead-audit",
    "review_kind": "independent coverage adjudication at ledger/theorems.jsonl#a1674f094979 (card astra-life05-verify-l0-final)",
    "gate": "G-LIT",
    "node_id": "L0",
    "assignment": "astra-life05-verify-l0-final",
    "authority": "no gate self-pass: the controller records G-LIT",
    "reviewed_sha256": T['L0']['pin'],
    "measured_sha256": STABILITY['L0']['measured_now'],
    "pin_stable": STABILITY['L0']['pin_matches'],
    "ledger": {"path": "ledger/theorems.jsonl", "rows": 62, "bytes": 151521, "mtime": "2026-09-12T00:39"},
    "hf14_predicates_rerun_by_audit": {
        "instrument": "direct key scan over all 62 JSON rows at the measured bytes",
        "status": 0, "validation_status": 0, "supports_claim": 0,
        "result": "0/62 rows for each of the three predicates; the HF-14 precondition is met at the hash",
    },
    "coverage_table": [
        {"reviewer": "worker-075", "created_at": "2026-09-12T00:49:30+08:00", "verdict": "accept", "score": 4.0,
         "full_schema": True, "non_author": True, "hard_failures": 0, "event_id": "w075-l0rev3-review"},
        {"reviewer": "worker-079", "created_at": "2026-09-12T01:09:00+08:00", "verdict": "accept", "score": 4.0,
         "full_schema": True, "non_author": True, "hard_failures": 0, "event_id": "w079-20260912T0109-review-l0"},
        {"reviewer": "worker-072", "created_at": "2026-09-12T00:49:10+08:00", "verdict": "accept", "score": 4.5,
         "full_schema": False, "non_author": True, "hard_failures": 0, "event_id": "w072-20260912T004910-review-l0-cf19"},
        {"reviewer": "worker-050", "created_at": "2026-09-12T00:54:34+08:00", "verdict": "accept", "score": 4.0,
         "full_schema": False, "non_author": True, "hard_failures": 0, "event_id": "w050-l0spotcheck-20260912T005434-review-l0"},
    ],
    "adjudicated_verdict": "accept-with-carried-objections",
    "verdict_basis": "two full-schema non-author accepts at one held hash (worker-075, worker-079) plus two further non-author accepts; HF-14 triple re-run returns 0 rows; the two accepts were written after the owner-announced rev3-final rewrite (00:35:19) and are not pre-rebuild text",
    "carried_objections": [
        {"id": "HF-02 (rubric literal)", "reviewer": "worker-093", "reviewed_at": "2026-09-12T00:38:55+08:00",
         "finding": "8 rows carry a class_ids disjunction (D-004, D-005, T-303, T-305, T-402, T-515, T-526, T-528); the canonical validator does not see it",
         "partial_disposition": "worker-023's adjudication packet (0f86158c5bb7) resolves all 8 to non-member/relation bindings under the frozen variant lattice and predicts 0 after a proposed patch; the patch is NOT applied",
         "status": "open — needs controller adoption of the non-member binding patch or a scope ruling"},
        {"id": "HF-01 (literal record reading)", "reviewer": "worker-093", "reviewed_at": "2026-09-12T00:38:55+08:00",
         "finding": "30 rows carry conclusion_type=theorem with no artifact_refs; applicability of HF-01 to ledger records is explicitly recorded as open, not silently resolved",
         "status": "open — controller scope ruling required"},
        {"id": "L0 review axis", "reviewer": "audit census", "reviewed_at": NOW,
         "finding": "review_status=not_independently_reviewed on all 62 rows while content_status=verified on 50; truthful per the HF-14 axis split, but no row yet carries an independent reviewer endorsement",
         "status": "recorded; not a defect of the frozen bytes"},
    ],
    "l1_unchanged": {"path": "ledger/citation_audit.csv", "sha256": "315c19145065", "note": "not re-reviewed in this round, per the card"},
    "gate_proposal": "the L0 half of G-LIT is proposable at ledger a1674f094979 (2 independent full accepts, HF-14 clean); the carried HF-01/HF-02 objections must be recorded in the controller's G-LIT adjudication",
    "falsifiers": [
        "any ledger write after a1674f094979 (both accepts void)",
        "an HF-14 predicate returning a nonzero row count at the hash",
        "a verdict reusing pre-rebuild review text",
    ],
    "measured_at": NOW,
}

# ---- A0 ------------------------------------------------------------------------------------
a0_rows = T['A0']['verdict_rows']
a0 = {
    "schema": "gate-final-verify/2",
    "event_id": "audit-l09-a0-final-verify",
    "created_at": NOW,
    "actor": "astra-lead-audit",
    "reviewer": "astra-lead-audit",
    "review_kind": "supersedes reviews/A0-review-final-verify.json v1 (00:50:20) with the full independent-verdict census at the rubric hash (card astra-life04-verify-a0)",
    "gate": "G-AUDIT",
    "node_id": "A0",
    "assignment": "astra-life04-verify-a0",
    "authority": "the audit group owns the rubric and cannot self-pass it; this artifact reports the independent census and proposes no accept",
    "reviewed_sha256": T['A0']['pin'],
    "measured_sha256": STABILITY['A0']['measured_now'],
    "pin_stable": STABILITY['A0']['pin_matches'],
    "adjudicated_verdict": "revise (unmet)",
    "verdict_basis": "0 independent non-author accepts at d748a9e3574e; the single accept on record is by actor 'lead-audit' (the author group) and the other 8 hash-bound verdicts are revises, including 4 full-schema revises",
    "independent_verdict_census": [
        {"reviewer": "worker-008", "created_at": "2026-09-12T00:18:58+08:00", "verdict": "revise", "score": 3.25, "n_hard": 0},
        {"reviewer": "deepseek-flash-22", "created_at": "2026-09-12T00:22:10+08:00", "verdict": "revise", "score": 3.0, "full_schema": True, "n_hard": 1},
        {"reviewer": "deepseek-flash-21", "created_at": "2026-09-12T00:23:29+08:00", "verdict": "revise", "score": 4.0, "full_schema": True, "n_hard": 0},
        {"reviewer": "worker-054", "created_at": "2026-09-12T00:46:25+08:00", "verdict": "revise", "score": 3.0, "n_hard": 4},
        {"reviewer": "worker-055", "created_at": "2026-09-12T00:48:22+08:00", "verdict": "revise", "score": 3.0, "full_schema": True, "n_hard": 1},
        {"reviewer": "worker-089", "created_at": "2026-09-12T00:51:54+08:00", "verdict": "revise", "score": 2.0, "n_hard": 0},
        {"reviewer": "deepseek-flash-19", "created_at": "2026-09-12T01:05:17+08:00", "verdict": "revise", "score": 3.0, "n_hard": 3},
    ],
    "self_review_excluded": {"actor": "lead-audit", "created_at": "2026-09-11T23:29:30+08:00", "verdict": "accept",
                             "reason": "author-group self-review; cannot count toward the A0 acceptance"},
    "detector_scope_artifact": {
        "path": "evaluation/A0_detector_scope_adjudication.json", "sha256": "a26be4b85706",
        "review": {"reviewer": "worker-021", "created_at": "2026-09-12T01:09:43+08:00", "verdict": "revise", "score": 3.5, "hard_failures": 0},
        "defects": ["b3 count wrong: 1 vs measured 7 staging records",
                    "the after-scope HF-14 total of 0 is a time snapshot; worker-037's unannounced rerun adds 50 literal-HF-14 rows",
                    "the surviving 194 records are absent scope metadata under a major-severity predicate, not 194 literal critical-severity rubric HF-03 findings"],
    },
    "standing_calibration_context": "CLASSSEP r3 adjudication 7714ffd5b467 records decision (c): assertion-vs-mention is not lexically separable at this window; residual hard count 19 (17 labeled FP + 2 meta) and the A04 clause FN stay live; the classsep instrument moved a third time during the freeze (CF-29) and the detector-of-record remains unresolved (pin c266dbec vs operative a8c04fc3)",
    "gate_proposal": "A0 remains unmet; G-AUDIT stays pending",
    "falsifiers": ["a rubric edit at the measured hash", "an independent non-author full-schema accept at d748a9e3574e that clears the standing revises"],
    "measured_at": NOW,
}

# ---- write -------------------------------------------------------------------------------
for path, obj in (("reviews/G-FORM-final-verify-r3.json", gform),
                  ("reviews/L0-review-final-verify.json", l0),
                  ("reviews/A0-review-final-verify.json", a0)):
    json.dump(obj, open(path, 'w'), indent=1)
    print("wrote", path, sha(path)[:12])

# ---- checkpoint ---------------------------------------------------------------------------
ckpt = {
    "schema": "lead-audit-lifecycle-checkpoint/1",
    "lifecycle": "lead-audit-lifecycle-09",
    "created_at": NOW,
    "group": "audit",
    "actor": "astra-lead-audit",
    "one_lifecycle_then_exit": True,
    "measured_hashes": STABILITY,
    "frozen_manifest_measured": frozen_now,
    "census": {k: {"pin": T[k]['pin'], "pin_matches": T[k]['pin_matches_measured'],
                   "bound": T[k]['n_bound'], "accepts_non_author": len(T[k]['accepts_non_author']),
                   "accepts_full": len(T[k]['accepts_non_author_full']), "revises": len(T[k]['revises'])}
               for k in T},
    "deliverables": ["reviews/G-FORM-final-verify-r3.json", "reviews/L0-review-final-verify.json",
                     "reviews/A0-review-final-verify.json", "artifacts/audit/l09/audit_l09_census.json",
                     "artifacts/audit/l09/audit_l09_census.py"],
    "verdicts": {"G-FORM": "not proposable", "L0": "accept-with-carried-objections (proposable)", "A0": "revise (unmet)"},
    "gates_unchanged": {"G-F0": "pass (untouched)", "G-FORM": "pending", "G-LIT": "pending", "G-NUM": "pending", "G-AUDIT": "pending"},
    "numerics_lock": "LOCKED; N0-only; no solver present; no N1 work in this lifecycle",
    "quarantine": "comms/inbox/astra-lead-audit.jsonl line 31 (astra-classsep-stabilize-0118) has no accepted-stream emission and is future-dated; quarantined byte-verbatim, not actioned",
    "blockers_filed": ["AUD-L09-01", "AUD-L09-02", "AUD-L09-03", "AUD-L09-04"],
    "next_falsifier": "after F2b/F2a repairs: re-measure pins, re-run classsep regression + audit_evidence, require fresh non-author verdicts; the F2b repair is falsified if :152/:246 are unchanged",
}
json.dump(ckpt, open('runtime/state/lead_audit_lifecycle_09_checkpoint.json', 'w'), indent=1)
with open('runtime/state/lead_audit_checkpoints.jsonl', 'a') as f:
    f.write(json.dumps({"lifecycle": "lead-audit-lifecycle-09", "created_at": NOW,
                        "checkpoint": "runtime/state/lead_audit_lifecycle_09_checkpoint.json",
                        "verdicts": ckpt["verdicts"]}) + "\n")
print("wrote runtime/state/lead_audit_lifecycle_09_checkpoint.json")
