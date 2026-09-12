# W066-F2B-VOCAB-BINDING-ADJUDICATION-01

Bounded worker-066 lifecycle (node F2b, class `AF-SCC-C0-VAC-GEN`), 2026-09-12. Independent,
hash-bound adjudication of worker-075's hard failure **HF-075-F2b-VOCAB** in
`reviews/F2b-review-rev29-075.json` (source sha256 `2fb2878ec1fb…`).

No assignment card existed in the controller inbox for worker-066; the task was taken under worker
authority as one bounded, independently killable lifecycle. Nothing canonical was written and no
gate was transitioned.

## Finding under test

> schema token `scc_c0_future_inextendibility` is not in the bound F0 declared
> `field_vocabulary.conclusion_type.allowed` `['weak_cosmic_censorship',
> 'strong_cosmic_censorship_C2', 'strong_cosmic_censorship_C0']`; the F0 declared class entry uses
> `strong_cosmic_censorship_C0` while `VOCAB_ALIASES.json` declares
> `scc_c0_future_inextendibility` canonical, so two frozen artifacts disagree on the canonical
> token and the alias policy forbids aliases in canonical artifacts.

## Method

Fresh code (`adjudicate.py`); no lead module is imported. Lead tools run only as black-box
subprocesses on pinned copies. All 16 inputs are sha256-pinned against FROZEN rev29
(`artifacts/formulation/FROZEN.json#815e0807`) before and after the run.

| layer | check | result |
|---|---|---|
| premise | C1 F0 rev5 `conclusion_type.allowed` omits both canonical SCC tokens, lists both aliases | PASS |
| premise | C2 F0 class axes use the alias tokens | PASS |
| premise | C3 frozen alias registry names `scc_c0/c2_future_inextendibility` canonical, F0 tokens accepted aliases | PASS |
| premise | C4 C0/C2 schemas carry the canonical tokens | PASS |
| binding | C5 R11's vocabulary is `rule_spec.vocabularies.class_conclusion_type` (canonical) with `aliases_ref` = VOCAB_ALIASES.json | PASS |
| binding | C6 canonical gate (R01–R16) passes C0 and C2 at the pins | PASS |
| binding | C7 alias-normalized F0-vs-supplement cross-check clean; pinned tool exits 0 CONSISTENT | PASS |
| binding | C8 the class-contract supplement C0 points to already carries the canonical token | PASS |
| binding | C9 no binding tool consumes F0 `field_vocabulary` (0 hits in gate/acceptance/gate-tests) | PASS |
| precedent | C10 frozen AMB-10 ruled the same-shaped conflict on `genericity_kind` (canonical `residual_comeager` + aliases; F0 left on aliases) | PASS |
| repair | C11 F0+canonical removes the premise; schema→alias is rejected by R11 | PASS |
| drift | C13 all pins re-measured unchanged after the run | PASS |

13/13 checks. Controls were fixed before the run and all 10 matched their pre-registered
expectations (`evidence/controls.json`), including pin-drift detection, both mutation directions,
normalization-off reproduction of the raw duality, the C2 sibling, the WCC non-conflict, the
aliases-ref resolution test, and the supplement-agreement control.

## Ruling

* textual premise — **CONFIRMED**;
* claimed severity `hard` — **REFUTED**; adjudicated severity **non-blocking**;
* resolution — **resolved by the frozen alias registry plus the frozen AMB-10 precedent**;
* gate effect — **none measured**: C0/C2 pass the canonical gate and the consistency layer at the
  pins; reviewer verdict `revise` 3.0 applies to the finding's severity/scope only,
  `counts_as_full_schema_verdict: false`.

Reasoning in one line: R11 binds to `rule_spec`, `rule_spec.aliases_ref` binds the frozen
canonical-token registry, C0's own bound supplement already uses the canonical token, and the
identical F0-vs-rule-spec wording pattern was already adjudicated for `genericity_kind` — so the
F0 rev5 allowed list is stale wording, not a live cross-artifact disagreement about canonicity.

**Residual (non-gating, lead-owned, optional):** a reader who treats F0 rev5
`field_vocabulary.conclusion_type.allowed` as an exact-match vocabulary will re-derive this false
blocker. The one-way repair is to re-stamp F0's conclusion-token slots to canonical (or add an
alias-equivalence note) at the next F0 revision. Re-stamping the schema to the alias is invalid:
the canonical gate rejects it at R11 and the policy forbids aliases in new canonical artifacts.

## Limits

Text-consistency, binding and instrument-coverage result only; it says nothing about the
mathematics of C0/C2 inextendibility, does not re-open AMB-10, does not issue a full-schema
verdict, and does not decide a gate.

## Falsifier

Re-run `adjudicate.py` on the same pins. Falsified if live C0 is not `b2ab6acb2bbe` or C2 not
`e9a27996`, FROZEN `815e0807` does not declare the measured hashes, the canonical gate rejects
C0/C2, R11's vocabulary source is F0 `field_vocabulary` rather than `rule_spec`, `aliases_ref`
does not resolve to the frozen registry or the registry does not name
`scc_c0_future_inextendibility` canonical, the bound supplement carries a different token, a
binding tool consumes F0's allowed list as exact-match, the gate accepts the alias token, any
control departs from its expectation, or any pinned byte moves.
