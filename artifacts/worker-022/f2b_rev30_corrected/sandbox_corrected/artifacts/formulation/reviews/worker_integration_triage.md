# Worker integration triage — formulation F0/F1/F2 (lead record)

Lead: `astra-lead-formulation`. Time: 2026-09-11T23:42–23:58 (+08:00). This file adjudicates the
formulation artifacts produced **by other agents** against the lead-owned canonical set. It is a
disposition record, not a claim: nothing here promotes a node or asserts physics.

## Canonical set (lead-owned, frozen by `FROZEN.json`)

| node | class | canonical artifact |
|---|---|---|
| F0 | all four classes | `artifacts/formulation/formulation_taxonomy.yaml` |
| F1 | AF-WCC-VAC-GEN | `artifacts/formulation/schemas/af_wcc_vacuum.yaml` |
| F2a | AF-SCC-C2-VAC-GEN | `artifacts/formulation/schemas/af_scc_c2_vacuum.yaml` |
| F2b | AF-SCC-C0-VAC-GEN | `artifacts/formulation/schemas/af_scc_c0_vacuum.yaml` |
| — | binding rule spec | `artifacts/formulation/rule_spec.json` (v1.1) |

## Worker artifacts and disposition

| artifact | author | disposition | harvested | rejected / reason |
|---|---|---|---|---|
| `schemas/af_wcc_vacuum.yaml` (r3, 35 KB) | deepseek-flash-03 (+ flash-04 ambiguity suite) | **input**, superseded as declared artifact | `adjudication_queue` open rows (F1-AMB-01/02/15) folded into canonical F1 with provenance+hash; `unresolved` field list used as a cross-check | nothing substantive rejected; it was never the lead-owned file and its hash moved 4× in 12 min (worker-16 F1-16-02) |
| `schemas/af_scc_c2_vacuum.yaml` | deepseek-flash-05 | **input**, superseded | `class_boundary` (merge_forbidden, one-way implication, import_rule) and `conventions` folded in with the one-way implication restated to match the canonical ledger | `conclusion_type: strong_cosmic_censorship` (ambiguous token; canonical requires `scc_c2_future_inextendibility`); genericity phrased as "open and dense … equivalently residual", which conflates two notions and is the same error flash-15 found in the lead file |
| `schemas/af_scc_c0_vacuum.yaml` | deepseek-flash-05 (derived from the lead file, `supersedes_sha256`) | **input**, superseded | `c0_specifics.what_fails_at_c0`; the `composite_regularity_lint` idea | the sentence "the two classes inherit nothing from each other in either direction" — the C0⇒C2 one-way entailment is real; the `arXiv:1507.00601` identifier is carried as **unverified**, L1 owns it |
| `schemas/af_scc_regularities.yaml` | worker draft | **rejected as a class artifact** | nothing | one artifact covering two classes invites the forbidden merged regularity; the canonical split is F2a/F2b; it may survive only as a registry that binds the two files by hash and asserts no merged conclusion |
| `schemas/taxonomy_cases.jsonl`, `schemas/f1_falsifier_tests.jsonl` | workers 03/04/05 | **evidence inputs** | referenced by the adjudication queue | not gate-checked by the lead; their own authors own correctness |

## Review findings accepted into the canonical revision 2

1. **flash-15 (real mathematical error, lead artifact).** The C0/C2/F1 schemas claimed
   `open_dense_escape -> residual_comeager` was a *failed* transfer with the witness "open dense
   does not imply comeager". False: a dense open set is comeager (it is the countable intersection
   of the constant family). Correct relations now recorded in all three schemas and in
   `rule_spec.json`: `open_dense_escape ⇒ residual_comeager`; `residual_comeager ⇏ open_dense_escape`
   (the irrationals are comeager with empty interior); the variant's strength is `strictly_stronger`,
   not `strictly_weaker`.
2. **worker-16 F1-16-03.** Non-vacuity must not require a non-empty black-hole region; that belongs
   to the separate black-hole-formation statement. Canonical F1 now gates non-vacuity on a
   future-**incomplete** development.
3. **worker-16 F1-16-04.** A universal-over-G statement is refuted by one member of G; the
   non-meagerness requirement is only one of two refutation routes. Both routes are now stated.
4. **worker-16 F1-16-05.** Machine-checkable steps vs proof obligations are now separate keys.
5. **R3 novel mutants.** R16 did not check ledger direction, R09 scanned only two keys, R15's
   overclaim clause was unimplemented, R12's path set was narrow. Gate strengthened; mutants
   m23–m26 added to the asserted corpus; a negation control added for the new R09 scan. R3's
   `n04` (composite wording inside a YAML comment) remains a documented blind spot: a parser-based
   gate cannot see comments, and no gate should be trusted for it.

## Note on the map-artifact claim

The lead's phase-0 audit ("0/10 declared artifacts exist") was true for map revision
`sha256:82b96a7d…` at 23:17 and is **stale** as of 23:29, when workers had populated the declared
paths (9/11 existing; only `N1` and `N1-BLOCK` missing, both under `numerics_lock`). R3 is right to
refute the claim as a present-tense statement; the corrected, timestamped form is recorded in the
event stream.
