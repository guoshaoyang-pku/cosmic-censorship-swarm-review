# W071-T1-GUARD-EVAL-01 -- machine evaluation of transfer rule T1's three guards

Generated 2026-09-12T00:29:03+08:00 by `eval_t1_guards.py`. Measurement only: no gate verdict, no node status, no validation_status=passed.

Classes `AF-SCC-C0-VAC-GEN` (source, F2b) -> `AF-SCC-C2-VAC-GEN` (target, F2a); gate `G-FORM`.

## Verdict

- measurement_valid: **True** (window STABLE, controls all_pass True)
- G1 literal: **FAIL**
- G2 literal: **UNEVALUABLE_AS_WRITTEN**
- G3 literal: **PASS**
- T1_licensed_at_pins: **False**

At the pinned hashes T1 is NOT licensed: guard(s) G1, G2 do not evaluate PASS under the pre-registered literal readings. G1 fails on 2 exact-match witness path(s) (['data_class.adm_mass.hypotheses_reconciliation', 'data_class.adm_mass.locator']), 0 of them inside the pre-registered core tuple (core tuple strictly equal); G2 is UNEVALUABLE_AS_WRITTEN because the literal field names genericity_kind / genericity_topology resolve nowhere in the frozen schemas; G3 passes literally on 1 bound C0-class claim(s), but the bound claim(s) do not assert C0 future-inextendibility and carry revise verdicts; 2 C0-class claim(s) mention C0 inextendibility and none is bound (post-run strengthened-reading diagnostic: 0 qualifying). The G-FORM unmet item stands at exactly the strength of these guard-level findings; note that G3's literal text is satisfied by a claim that is not the C0 conclusion, so the unmet item is carried by G1 and G2. Context (not part of T1): the F1 data_class differs from F2b at 2 core-key path(s) (['data_class.asymptotic_decay.parity_conditions', 'data_class.regularity_class.sobolev_variant.spaces']), so the gate's joint F1/F2a/F2b wording is driven by F1, not by the F2b->F2a pair.

## G1 witnesses (exact-match failures)

| path | F2a (target) | F2b (source) | F2a line | F2b line |
|---|---|---|---|---|
| `data_class.adm_mass.hypotheses_reconciliation` | <missing> | pointwise rates are the smooth-with-decay default; the Sobolev variant uses the same rates distributionally, and i_plus k >= 3 is assumed independently of both (worker-16 F2b-16-04 acknowledged, recorded not resolved) | None | 145 |
| `data_class.adm_mass.locator` | to be supplied by L1 | to be supplied by L1 (Schoen-Yau / Witten); the sign is used only to exclude negative-mass data from the ambient space | 144 | 145 |

## G2

Literal verdict: **UNEVALUABLE_AS_WRITTEN** -- the literal field name(s) genericity_kind, genericity_topology do not resolve in both frozen schemas; a missing field cannot satisfy 'must match exactly'.
Mapped (non-binding) reading: **PASS**.
- `genericity_kind` -> `genericity.kind`: equal_exact_text=True
- `genericity_topology` -> `genericity.topology_or_measure`: equal_exact_text=True

## G3

Literal verdict: **PASS** -- 1 C0-class claim(s) carry both artifact_refs and a reviewer verdict with target_id == claim event_id.
- C0-class claims found: 39 (of which mention C0 inextendibility: 2)
- bound (artifact_refs + claim-targeted reviewer verdict): 1
  - `flash02-opencase-claim-0010b-20260912T0015`: conclusion_type=stability_result, asserts C0 inextendibility=False, verdicts=['revise', 'revise']
- post-run strengthened-reading diagnostic (not pre-registered, never binding): 0 qualifying claim(s) (asserts C0 inextendibility + artifact_refs + accept verdict)

## Context: where the gate's F1/F2a/F2b wording diverges (not part of T1)

T1 runs F2b -> F2a. The gate unmet item is worded over F1/F2a/F2b jointly, so the F1 data_class is compared to F2b here for context only. Strict witnesses: 9, of which 2 are core-key paths (['data_class.asymptotic_decay.parity_conditions', 'data_class.regularity_class.sobolev_variant.spaces']).


## Pinned hashes

- F0_canonical (`research_map/formulation_taxonomy.yaml`): `276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc`
- F2a_target (`schemas/af_scc_c2_vacuum.yaml`): `b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2`
- F2b_source (`schemas/af_scc_c0_vacuum.yaml`): `1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508`
- map (`research_map/research_map.json`): `4fd40d4d1e4fc3602192eb8533e9a9f5075aa63ac644bd5c2dab30357f68db6b`
- F1_context (`schemas/af_wcc_vacuum.yaml`): `9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503`
## Instrument history

- v1 of `eval_t1_guards.py` matched a review to a claim through any file the claim cited, which let literature claims inherit reviews of `ledger/theorems.jsonl`. The pre-registered rule (review.target_id == claim.event_id) was not implemented literally. The v1 output is kept as `guard_eval.v1-instrument-bug.json` (superseded intermediate sha256 `ba844b352deff8461a4ef1ddd8865bf3c8d3b196890a5da48eef96685bf33740`) and is not the binding result; v2 implements the pre-registered rule and is the result above.


## Falsifier

Re-run artifacts/worker-071/t1_guard_eval/eval_t1_guards.py at the same pinned sha256 values. Falsified per guard if G1_literal evaluates PASS, or G2_literal evaluates PASS, or G3_literal evaluates PASS, contrary to the recorded per-guard verdicts; if all three evaluate PASS then T1 is licensed at the pins, the G-FORM unmet item is refuted at the whole strength of the transfer rule, and this report's overall verdict is falsified. Any input sha256 change across the pre/post window voids the result at the changed path and requires a re-run.

## Limitations

- G1 compares F2b (source) with F2a (target) only; F1 (AF-WCC-VAC-GEN) is a different transfer family and is not part of T1.
- The G2 mapped reading uses a mapping (genericity_kind -> genericity.kind, genericity_topology -> genericity.topology_or_measure) inferred by this artifact; F0 does not declare it.
- G3 binds claims recorded in research_map/research_map.json only; un-ingested outbox traffic is out of scope by construction.
- Line numbers are value-node start lines from the YAML composer.
- No gate verdict, no node status, no validation_status=passed is asserted.
