# W085-F2A-REV29-REVIEW-01 — independent non-author G-FORM review of F2a

Bounded class-bound worker task taken without an inbox card (both cards in
`comms/inbox/worker-085.jsonl` were already consumed at their declared pins; the slot
self-selected ONE task on the thinnest G-FORM node). Read-only: no canonical path was written,
no gate verdict, no node status, no `validation_status` is claimed.

- Class: `AF-SCC-C2-VAC-GEN` — node `F2a` — gate `G-FORM`
- Target: `schemas/af_scc_c2_vacuum.yaml` (canonical) / `artifacts/formulation/schemas/af_scc_c2_vacuum.yaml` (mirror)
- Reviewed sha256: `e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe` (rev13, 30594 bytes)
- FROZEN rev29: `815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0`
- Verdict: **accept, 4.0** — `reviews/F2a-review-rev29-085.json` (`b86ce67c4c0b`)
- Instrument: `probe_f2a.py` (`68b407fc0829`) → `probe.json` (`29a4413aa3f5`)

## Why this task

The controller's 01:12:39 gate audit records F1 4 accepts, F2b 4 accepts, **F2a 2** at
`e9a27996`. Worker-085 is a non-author of F2a with no prior F2a verdict, so an independent full
verdict is the cheapest way to add margin to the thinnest node before the audit lead's
`astra-life05-verify-gform-r3` adjudication (deadline 02:45).

## Measurement (all at the pin, t0 == t1, zero pin drift, mirror byte-identical)

| check | result |
|---|---|
| structural gate (`check_class_schema.py`) | pass, 0 failed rules |
| semantic baseline (`spec_conformance_audit.py`) | accept, 0 failed rules, SEM-1..3 undecided as declared |
| taxonomy consistency | CONSISTENT (4 classes, 0 divergences) — alias-tolerant, see F-085A-01 |
| variant registry | VALID (4 parents, 7 variants) |
| f0_binding | declared F0 `0abb9ed8a961` resolved; consistency evidence `9e335e9b` resolved; refresh rule satisfied |
| class-contract pointers | canonical + supplement both resolve |
| class leakage | 0 foreign tokens in asserted blocks; I+ in_conclusion=false; visibility role=not_in_conclusion |
| conclusion inflation | none; `epistemic_status: open_problem`; promotion rule present |
| containment chain | `E_C2 ⊂ E_{C^1,1} ⊂ E_H2loc ⊂ E_C0` present in order; forbidden transfers are the converses; **0 live denials**, 1 bracketed historical mention |
| falsifier | tier_1 decidable (4 machine steps + declared non-machine step); tier_2 `refutes_strengthening_only` |
| probe controls | 5/5 detection controls fire; 1/1 false-positive control (quoted mention) behaves |

## Findings

- **F-085A-01 (medium, cross-artifact, adjudication required).** Two frozen artifacts spell the
  F2a vocabulary differently while remaining alias-equivalent. `conclusion_type`: F0 class axis
  `strong_cosmic_censorship_C2` vs schema `scc_c2_future_inextendibility` (VOCAB_ALIASES
  canonical). `genericity_kind`: F0 axis `provisional_baire_residual` (F0 itself calls
  `provisional_*` an unfrozen placeholder) vs schema `residual_comeager`, which is **not** in
  F0's `field_vocabulary` allowed list. `check_taxonomy_consistency.py` is alias-tolerant and
  reports CONSISTENT, so the divergence is invisible to the canonical instrument. Alias
  equivalence means no class-statement change; one gate-level token re-stamp decides it. This is
  the F2a instance of worker-075's `HF-075-F2b-VOCAB`; F1 is unaffected.
- **F-085A-02 (low, shared with F1/F2b).** `asymptotic_decay` uses `s` in the `r = smooth`
  branch where `s` is not defined.
- **F-085A-03 (low, shared).** `genericity.ambient_space` justifies Baire-ness with "closed
  subset of a Banach space" while the smooth branch is Fréchet; Fréchet is Baire, so the
  conclusion survives.
- **F-085A-04/05 (informational).** Unused out-of-order `revision_history` index 9; empty
  self-declared `review_status.independent_reviewers` (gate coverage lives in the controller scan).
- **F-085A-06 (informational contrast).** F2b still carries a live "No containment with C2 or C0
  is asserted here" span against its own ledger; F2a has the corrected chain. F2b-side, not F2a.

## Cross-artifact / global records

- `D0` and `data_class` key sets byte-equal F2a/F2b; divergences (C2 vs C0 regularity, equation
  concept, `adm_mass.locator` detail) are the intended class-axis differences.
- Root `entry_hashes.json` (`09a5b37a190d`) is stale against 9/12 declared paths; the only
  `schemas/*.sha256` sidecar (`af_scc_c0_vacuum.yaml.sha256`) is stale for the C0 schema. Both are
  global remediation items outside this review (recorded, not actioned).

## Falsifiers

At the cited pins: any different measured hash; a live containment denial after mention-stripping;
a foreign token in an asserted block; an assertoric theorem/counterexample conclusion; any of the
four canonical tools failing; or an alias-equivalence failure on either vocabulary axis. A later
write to the schema is a new revision to re-review, not a falsifier of this verdict.

## Authority

Worker review event. No gate verdict, node status, `validation_status`, canonical write or freeze
change. This verdict binds only the bytes above.
