# W072-F1-REVIEW-REV13-01 — independent F1 conformance review (worker-072)

Bounded, non-author review of `schemas/af_wcc_vacuum.yaml` (F1, class `AF-WCC-VAC-GEN`, gate G-FORM)
at rev13 `d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d`.

## Verdict
accept 4.5, 24 PASS / 0 FAIL, 12/12 mutation controls caught, 0 escaped. Worker evidence only:
this does not set node status, `validation_status`, or a gate verdict.

## Method
`check_f1.py` (mine, from scratch for F1; harness helpers re-used from my own F2a instrument) parses the
canonical schema with a duplicate-key-tracking YAML loader and applies 24 checks derived from the frozen
G-FORM criteria plus the schema's own declared contract. Mention sites (`anti_scope`, `forbidden_*`,
`must_not_conflate`, `revision_history`) are checked for the required mention; assertion slots
(`class_id`, `scope_statement`, quantifiers, conclusion statement, visibility/I+ conclusion fields) are
scanned for leakage. Negative controls mutate one field/path each on a sandboxed copy and must trip the
target check (K1 class-id swap, K2 SCC conclusion type, K3 I+ removed from conclusion, K4 quantifier order
reversed, K5 set-based visibility reading, K6 strength direction flipped, K7 F0 hash zeroed, K8 falsifier
removed, K9 SCC leak injected into `statement_formal`, K10 excluded-set status marked resolved,
K11 duplicate key, K12 clean-redump determinism).

## Reproduction
    python3 artifacts/worker-072/f1_review/check_f1.py --root . \
        --json artifacts/worker-072/f1_review/report.json --controls

## Pins measured at review
{
 "schemas/af_wcc_vacuum.yaml": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
 "artifacts/formulation/schemas/af_wcc_vacuum.yaml": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
 "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
 "artifacts/formulation/formulation_taxonomy.yaml": "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
 "artifacts/formulation/evidence/taxonomy_consistency.json": "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b",
 "artifacts/formulation/FROZEN.json": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
 "artifacts/worker-072/f1_review/pins/af_wcc_vacuum.rev12.yaml": "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
 "artifacts/worker-072/f1_review/pins/af_wcc_vacuum.rev13.yaml": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d"
}

## Findings
- W072F1-01 all 24 checks PASS at rev13.
- W072F1-02 rev12->rev13 delta is exactly the 9 carded paths (strictness-direction repair + evidence refresh).
- W072F1-03 FROZEN rev29 pins all 50 files, 0 mismatches; F1 verdict binding-eligible at the measured hash.
- W072F1-04 non-blocking: `revision=13` but last `revision_history` index is 11.
- W072F1-05 scope: structural/declarative and hash-bound only; no mathematics/citation verdict.

## Falsifier
Any schema hash other than `d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d`, a FAIL on a clean run, a delta path outside the
nine named paths, a control escape, or a FROZEN rev29 pin that no longer equals the live bytes.

## Authority
Worker evidence only; the audit lead adjudicates G-FORM coverage and Astra records the gate.
