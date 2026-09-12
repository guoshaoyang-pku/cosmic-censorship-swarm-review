# W006-R03-SCOPE-01 — submission (worker-006)

**One bounded class-bound task.** Node `A1`, gate `G-CLASSBIND` (folds into `G-AUDIT`),
classes `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`.
**Question:** on a fresh pre-registered corpus at the live FROZEN rev29 bytes, does any
published R03 repair separate *correct* composite-binder renderings from
*scope-erroneous* ones — where the negated quantifier does not bind every declared
variable — and what are each candidate's false positives / false negatives?
**Status:** measurement `VALID`. No gate verdict, no node completion, no theorem, no
adoption recommendation. Adoption is the schema owner's decision.

## Why this task

Formulation lead, lifecycle-08 (`lead-form-20260912T011516-122/124/125`, 01:15): the
variable-wise R03 patch **cand_E3** accepts a negation-scope-error rendering
(`not exists q in I+ with <body>, and t0 in [0,T).`) identically to the correct grouped
rendering, so it is not scope-safe; the recommended **option A-prime** is variable-wise
matching **plus** a scope-aware grouping requirement, with the scope-error variant as a
permanent negative control. The A-prime question was open: does any candidate already
implement that scope check, and how do the published repairs compare on scope families
beyond the lead's single probe variant?

## Method (pre-registered, fail-closed)

`preregistration.json` (`f376d7124cfb`) fixed pins, candidates, declared per-candidate
semantics, hypotheses, decision rule and falsifier **before any fixture was scored**. The
corpus manifest is `fixture_manifest.json` (`40a457905eee`), hashed in the pre-registration.

* **Corpus:** 19 fresh fixtures — 1 canonical control, 6 scored positives, 8 scored
  negatives, 4 interpretation-dependent edge probes (`edge_*`, reported, not scored).
  No fixture is reused from W006-R03-CAND-HEADTOHEAD-01, the R03-v2 calibration set, the
  worker-004 set or the heldout corpora. Every mutant is single-target raw-text surgery on
  `quantifiers.formal` of the live canonical WCC and is asserted by parsed deep diff to
  change exactly that one leaf.
* **Candidates (each pinned by sha256 in the pre-registration; no canonical path written):**

  | candidate | sha256 | rule |
  |---|---|---|
  | frozen | `c79d8ab8440a` | literal `(q,t0)` substring of `quantifiers.formal` |
  | **cand_r03v2** | `e41a4b23a840` | binder-head co-binding: one quantifier clause head contains the identifiers in order, each within span=80 |
  | cand_004 | `645eb16a0060` | every alphanumeric component a whole word anywhere in `formal` |
  | cand_E3 | `3f69bc1eb27a` | literal, else all comma-components as substrings anywhere |

* **Identical command per candidate x file**, raw auditor JSON kept in `raw/`; a second
  pass re-runs every cell and requires semantic reproduction (G6).
* **Validity gates (all passed, `measurement=VALID`):** G1 zero byte drift (10 pins + 19
  fixtures, pre and post); G2 frozen canonical control (C0/C2 accept, WCC reject `R03`
  only); G3 every repair accepts all three live canonicals; G4 no non-R03 failure on any
  fixture and non-R03 parity across candidates; G5 corpus informative, no candidate error;
  G6 semantic reproduction 19/19 x 4.

## Result (out-of-sample, live rev29)

Primary counts are scored fixtures only (6 pos must accept / 8 neg must reject):

| candidate | primary FP | primary FN | canonical controls | scope-safe? |
|---|---:|---:|---:|---|
| frozen `c79d8ab8440a` | 4 | 2 | 2/3 (WCC rejected) | **no, both directions** |
| **cand_r03v2 `e41a4b23a840`** | **0** | **0** | **3/3** | **yes, on this corpus** |
| cand_004 `645eb16a0060` | 0 | 7 | 3/3 | no (accepts 7/8 scope errors) |
| cand_E3 `3f69bc1eb27a` | 0 | 8 | 3/3 | no (accepts 8/8 scope errors) |

* **frozen FPs** (correct renderings rejected): grouped tuple with a space `(q, t0)`,
  doubled-space coordination, filler adverb `and also t0`, whitespace-expanded binder.
  **frozen FNs** (scope errors accepted): `neg_literal_tuple_elsewhere` — the literal
  `(q,t0)` appears in a trailing clause after the body while the negation still binds only
  q; `neg_ids_in_body_letting` — the tuple is introduced by `letting` inside the body.
  *The frozen literal test is not a scope check at all; it passes whenever the token
  appears anywhere.*
* **cand_004 / cand_E3** accept every scope-error family except the substring-only
  negative (cand_004 also rejects that one). Position-blind and scope-blind, as the lead
  measured on one variant; this corpus shows the failure generalises over 6 additional
  scope families (after-body conjunction, after-body parenthetical, non-binding literal
  token, reversed order, implication consequent, earlier-quantifier binding, body
  `letting`).
* **cand_r03v2** is the only candidate that accepts all 6 correct renderings and rejects
  all 8 scope/binding errors. Its rejection of the scope errors is its documented
  binder-head locality: a variable bound after the clause's body marker (`with` /
  `such that`) or in another clause is not in the binder head. On this evidence the
  **scope-aware half of option A-prime is already implemented by R03-v2**; no separate
  grouping requirement is needed to pass this corpus. (cand_r03v2's two pre-declared
  over-rejects — comma-coordinated binder, ~140-char span — remain; both are `edge_*`
  probes, unscored, and unchanged from the head-to-head.)

Per-fixture matrix, raw auditor output and per-candidate class-contract misses with
minimal repro are in `report.json`, `raw_verdicts.json` and `blindspot_report.json`.

## Falsifier outcome

| pre-registered falsifier | outcome |
|---|---|
| any pinned input byte or fixture byte drifts | **not triggered** (10 pins + 19 fixtures, pre == post) |
| any fixture fails a non-R03 rule under any candidate | **not triggered** (non-R03 sets empty and identical on all 19) |
| frozen canonical control not reproduced | **not triggered** (C0/C2 accept, WCC reject `R03`) |
| raw JSON not reproducible from recorded commands | **not triggered** (19/19 x 4 semantic reproduction) |
| any deviation from a declared per-candidate expectation | **none** (0 deviations across 19 x 4 = 76 declared cells) |

Standing falsifier for a candidate row: a later held-out scope corpus on which that
candidate accepts a genuine scope error or rejects a genuine correct rendering.

## Honest limits

1. The corpus is 18 mutants on one leaf (`quantifiers.formal`) of one class; it is a
   binder/scope corpus, not a random sample of real schema prose.
2. Legitimacy calls for the four `edge_*` probes (comma-coordinated binder, ~140-char
   span, split quantifiers, brace group) are the worker's interpretation of R03's text
   "a single sentence using those binders"; they are declared, unscored, and do not enter
   FP/FN. A different reading reclassifies them.
3. This measures R03 stage B only. R03 does not catch semantic class leaks; the lead's
   substantive blocker (`lead-form-...-124`: informative C2+C0 arms union escape 1.0 on
   heldout-09/10) is untouched by this task.
4. The declared expectations matched the observations in all 76 cells, so this corpus is
   confirmatory, not a blind test of the rules; its out-of-sample value is against the
   candidates, not against my model of them.
5. Runner repair, disclosed: run 1 (`report.run1_runnerbug_invalid.json`,
   `raw_verdicts.run1.json`) was voided by a runner-side gate that required per-candidate
   verdict variance; it flagged the run because cand_E3 accepts all scored fixtures — which
   is the measured finding, not corpus invalidity. G5 was redefined to corpus
   informativeness. Corpus bytes, pre-registration, declared expectations, pins and all
   recorded verdicts are unchanged by the repair.
6. Instrument governance: the stage-2 rule engine is **not pinned** in
   `artifacts/formulation/FROZEN.json` (lead blocker `lead-form-20260912T011516-123`).
   This task pins every candidate by its own sha256 in its own pre-registration and wrote
   no canonical path; it does not fix the governance gap.

## Files

| file | role |
|---|---|
| `preregistration.json` / `preregister.py` | pins, candidates, semantics, hypotheses, corpus hash, decision rule, falsifier — hashed before scoring |
| `make_fixtures.py` / `fixtures/` / `fixture_manifest.json` | deterministic 19-fixture corpus, per-fixture hashes, declared expectations, rationales |
| `run_scope.py` | fail-closed runner, validity gates G1–G6, scoring, blindspot report |
| `report.json` / `raw_verdicts.json` / `raw/` | aggregates and raw auditor output per candidate x file |
| `blindspot_report.json` | declared-expectation deviations, class-contract misses, declared residues |
| `report.run1_runnerbug_invalid.json` / `raw_verdicts.run1.json` | preserved run 1 (post-hoc disclosure) |

**Not claimed:** gate verdict, node completion, theorem, physics result, adoption of any
candidate, or that R03-v2 is correct beyond this corpus.
