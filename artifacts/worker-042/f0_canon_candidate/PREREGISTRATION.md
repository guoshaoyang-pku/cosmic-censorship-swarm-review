# W042-F0-CANON-CANDIDATE-08 — pre-registration (written before the checker was run)

Actor: worker-042. No assignment card exists in `comms/inbox/worker-042.jsonl` at claim time.
One bounded class-bound task, taken as the continuation of `W042-XART-TOKEN-CENSUS-07`:
produce an **offline, hash-pinned repair candidate** for the F0 declared conclusion-type
vocabulary and measure exactly what adopting it would change. **No canonical path is written.**

## Frozen inputs (pin-first; all read-only)

| path | role |
|---|---|
| `research_map/formulation_taxonomy.yaml` | F0 declared taxonomy, G-F0 pass pin `0abb9ed8a961` |
| `artifacts/formulation/formulation_taxonomy.yaml` | F0 companion supplement `d7419b4e8963` |
| `artifacts/formulation/VOCAB_ALIASES.json` | alias policy `46cd9f1eb534` (rule 1: aliases never in a new canonical artifact) |
| `artifacts/formulation/FROZEN.json` | rev29 manifest `815e08079aef` |
| `artifacts/formulation/rule_spec.json` | gate vocabulary source `40f9bb9e657b` (`class_conclusion_type`) |
| `schemas/af_{wcc,scc_c2,scc_c0}_vacuum.yaml` + `artifacts/formulation/schemas/...` | rev13 schemas (mirrors) |
| `artifacts/formulation/evidence/taxonomy_consistency.json` | consistency evidence `9e335e9ba1bf` |
| `artifacts/formulation/tools/check_taxonomy_consistency.py` | canonical cross-check tool `de356d999ea3` |
| `artifacts/worker-019/f2a_review/results.json` | literal-membership consumer rule B1 |
| `artifacts/worker-097/f2b_rev13_review/check_f2b_rev13.py` | alias-registry consumer rule `alias_allowed` |
| `research_map/events.jsonl` | pinned arrival-order stream for the blast-radius count |

## Candidate construction (byte-minimal, fail-closed)

Two variants of `research_map/formulation_taxonomy.yaml`, built only from the snapshot copy:

- **A (value sites only):** replace the 6 quoted alias tokens with the VOCAB_ALIASES canonical
  tokens — 2 entries in `field_vocabulary.conclusion_type.allowed`, and
  `classes[AF-SCC-C2-VAC-GEN].axes.conclusion_type` / `.conclusion.type`,
  `classes[AF-SCC-C0-VAC-GEN].axes.conclusion_type` / `.conclusion.type`.
  The rule prose at line 153 keeps the alias spellings (mention residue = 2 substrings).
- **B (value sites + rule prose):** A plus the line-153 rewrite
  `strong_cosmic_censorship_C2 and _C0` -> `scc_c2_future_inextendibility and scc_c0_future_inextendibility`
  (total alias-string residue = 0).

## Pre-registered expectations (fail = finding, not silent)

- **E1 PIN:** every snapshot copy re-hashes to the live file; no pin drift during the run.
- **E2 FROZEN-NON-VACUOUS:** the frozen F0 **fails** canonicality: allowed-list 2 alias entries,
  4 class-axis alias values, 2 prose alias mentions (8 alias substrings, 6 quoted).
- **E3 CAND-A:** allowed-list and all 4 class-axis slots canonical; quoted residue 0;
  total alias-substring residue 2 (prose) -> status `PASS_WITH_MENTION_RESIDUE`.
- **E4 CAND-B:** total alias-substring residue 0 -> status `PASS_FULL`.
- **E5 MINIMAL-DIFF:** parsed-tree diff candidate-vs-frozen is confined to the expected paths;
  no key added/removed; list lengths unchanged; `class_ids` unchanged; 4 classes.
- **E6 SEMANTICS:** alias-resolved conclusion token per class identical frozen/A/B;
  C0 and C2 remain distinct; the merge guard still names both types (B names canonical forms).
- **E7 CONSUMER REPLAY:** literal membership (worker-019 B1 rule) frozen FAIL -> A PASS -> B PASS;
  alias-registry rule (worker-097) PASS on all three; cross-tree `canon()` equality
  (`check_taxonomy_consistency.py` logic) PASS on all three; `rule_spec` gate vocabulary
  (`class_conclusion_type`) canonical and unaffected by the F0 edit. Coverage note: the pinned
  consistency tool contains no reference to `field_vocabulary.conclusion_type.allowed`
  (the only `allowed` hit is `transfer_rules.allowed`), so it cannot detect E2.
- **E8 CONTROLS (each mutation must be detected by its designated check):**
  CTL-1 alias re-introduced -> E3 fails; CTL-2 C0/C2 merged -> E6 fails;
  CTL-3 unrelated key changed -> E5 fails; CTL-4 allowed entry dropped -> E5 fails;
  CTL-5 candidate == frozen -> E3 fails; CTL-6 duplicate YAML key -> strict parse fails;
  CTL-7 A vs B residue separation (2 vs 0) confirmed.
- **E9 BLAST RADIUS:** count pinned events referencing `0abb9ed8a961`, by event type and actor.
  Adoption is expected to require one revision bump of one file (F0) plus re-review of every
  accepted F0-bound record counted there; this is a cost measurement, not a gate action.

## Stop rule

Any pin move during the run voids the affected candidate and the run exits `PIN_DRIFT` with no
completion claim. A control that does not fire voids the corresponding check, not the whole run.

## ERRATUM r2 (written after the first full run; original expectations above left verbatim)

Three of the pre-registered constants were miscounted; the measurements are unchanged and the
checker constants are corrected here, not the observations:

1. **E2/E3/E4 alias-substring count.** The line-153 prose is
   `strong_cosmic_censorship_C2 and _C0 are distinct values ...`: it carries **one full alias
   token** plus an **abbreviated `_C0`**, not two full tokens. The full-token scanner therefore
   measures **7** alias substrings on frozen F0 (6 quoted + 1 prose), not 8, and candidate A
   leaves **1** full alias substring (the prose `_C2`), not 2. Candidate B still leaves 0.
   Consequence: variant A is a smaller "mention residue" than pre-registered, and a naive
   literal scanner would not even see the abbreviated `_C0`.
2. **CTL-3 mutation string.** The unrelated key is `schema_version: "0.1"` (quoted), not
   `schema_version: 0.1`; the first-run control mutated nothing and correctly reported "not
   detected". The control is fixed to mutate the real line.
3. **CTL-5/CTL-7 constants** follow from (1): non-vacuity expects residue 7; the A/B residue
   separation expects 1 vs 0.

These corrections make the controls stricter, not weaker: CTL-3 now actually mutates a byte and
must be caught by E5.

