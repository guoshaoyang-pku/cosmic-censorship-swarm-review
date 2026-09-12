# W099-FORM-DIRECTION-CENSUS-01 — class/variant direction-inversion census

Bounded worker `worker-099` · 2026-09-12 · node F0/F1/F2a/F2b · gate G-FORM · read-only

## Why this task

The formulation lead's pass-05 lifecycle left two open, class-bound blockers naming
*specific* surviving instances of an inverted containment/strength direction:

- **L-FORM-01** — `schemas/af_scc_c0_vacuum.yaml` `forbidden_transfers[0].reason` says
  "C2 is a strictly larger extension class".
- **L-FORM-03 (reduced)** — the inverted SET/union direction survives in the two F0
  artifacts (`research_map/formulation_taxonomy.yaml:200`,
  `artifacts/formulation/formulation_taxonomy.yaml:176`).

No complete cross-artifact enumeration of the **pattern family** existed, so neither the
r3 reviewer nor a repairer could know whether the named rows were the whole set. This
instrument enumerates every candidate direction assertion in the frozen corpus and in the
wider formulation/schema text tree, classifies it, and preserves a quote per row for human
adjudication.

## Pins (sha256, measured at run time, 0 drift during the run)

| artifact | sha256 (prefix) |
|---|---|
| `research_map/formulation_taxonomy.yaml` | `0abb9ed8a961` |
| `artifacts/formulation/formulation_taxonomy.yaml` | `d7419b4e8963` |
| `schemas/af_wcc_vacuum.yaml` | `d9cebb9404b2` |
| `schemas/af_scc_c2_vacuum.yaml` | `e9a27996dfd3` |
| `schemas/af_scc_c0_vacuum.yaml` | `b2ab6acb2bbe` |
| `artifacts/formulation/VARIANT_REGISTRY.json` | `6bac9adea19e` |
| `schemas/f1_falsifier_tests.jsonl` | `56bcb4b3234b` |
| `artifacts/formulation/FROZEN.json` | `815e08079aef` |

True direction asserted by the pins themselves: `E_C2 ⊂ E_{C^1,1} ⊂ E_H2loc ⊂ E_C0`
(C2 is the **innermost / smallest** extension class; C2-inextendibility is the **weakest**
conclusion), and the single-q TAIL predicate **entails** the union/SET reading (SET strictly
**weaker**, rev13).

## Method

- Deterministic stdlib-only scan, 3-line sliding window (YAML-wrapped sentences seen whole),
  3 candidate families: extension-class size, statement strength, WCC visibility readings.
- Subject-bound rules; retraction/correction language only excuses a hit when the marker sits
  within ±80 chars of the direction token (a neighbouring line's "converse containment is
  false" must not excuse the c0 inversion — this was caught and fixed in self-audit).
- Controls: 9 synthetic fixtures with declared labels + 8 corpus anchors (3 must be INVERTED,
  5 must not). Exit 3 on pin drift or any control failure.
- Extended sweep: every `.json/.jsonl/.yaml/.yml/.md/.txt` under `artifacts/formulation/`
  and `schemas/` (201 files not already pinned), hits labelled `fixture_or_mutant`,
  `pinned_snapshot`, `report_or_review`, or `live_tree`.

## Result — 8 pinned artifacts (69 candidate rows)

| verdict | count |
|---|---:|
| INVERTED | **3** |
| CORRECT | 25 |
| META_RETRACTED | 7 |
| MANUAL_REVIEW (candidates, no bound rule) | 34 |

**Exactly three live inverted assertions, and they are the three already named by the lead:**

1. `schemas/af_scc_c0_vacuum.yaml:246` — "C2 is a strictly larger extension class" (`P1-C2-LARGER`)
2. `research_map/formulation_taxonomy.yaml:200` — SET/union reading "strictly stronger" (`P2-SET-STRONGER`)
3. `artifacts/formulation/formulation_taxonomy.yaml:176` — D1 "F0 was stronger; (b) implies (c) but not conversely" (`P2-F0-STRONGER`)

All 34 MANUAL_REVIEW rows were read: every one is correctly directed (CH/CH-variant weaker,
two-sided stronger, C0 conclusion stronger, distributional-variant qualifier, spatial "subset",
or binding-history JSON). No hidden inversion. The 7 META rows are genuine retractions.

## Net-new observations (beyond the lead's named rows)

- **Repair-scope trap — a second copy.** `artifacts/formulation/schemas/af_scc_c0_vacuum.yaml:246`
  (pinned snapshot directory) carries the *same* inverted line as the canonical F2b schema.
  L-FORM-01 names only `schemas/af_scc_c0_vacuum.yaml`; a one-file repair leaves the snapshot
  copy inverted.
- **Repair-scope trap — fixture corpora.** The extended sweep finds 150 inverted-direction rows
  outside the pinned set: 141 in deliberate fixture/mutant corpora
  (`fixtures/`, `semantic_contract_tests/`, `rebased_fixtures/`, `heldout_rebased/`,
  `novel_mutants/`), 8 in reports/reviews quoting the defect, 1 in the pinned snapshot above,
  and **0 in live_tree files**. Any text-level repair must therefore be path-scoped or it
  corrupts the test corpora.
- **Escape mechanism corroborated.** `artifacts/formulation/reviews/R3_evidence_reproduction.json:132`
  records that R16 only tests that `one_way_entailments`/`forbidden_transfers` are non-empty, so
  a ledger with the inverted transfer wording passes — consistent with this defect surviving
  R1/R2/R3 text review.
- **L-FORM-04 corroboration (cross-check only, not this task's claim):** 25/25 rows of
  `schemas/f1_falsifier_tests.jsonl` bind to F1 rev12 `cce9c60146d6`; 0/25 to rev13
  `d9cebb9404b2`.

## Falsifier

Re-run `run_direction_census.py` at the pins: the completeness claim is falsified by (a) any
byte change in a pinned file, (b) any *live* direction inversion not in the three rows above —
e.g. a sentence positively asserting `C2` is the larger extension class, the SET reading is
stronger, or `C0` is weaker, in a non-retraction context, or (c) a self-test/anchor flip.
The extended-sweep observations are falsified by a live_tree row with an inverted direction at
the recorded file hashes.

## Non-claims

Not a gate verdict; cannot move G-FORM or any gate; does not set node status or
`validation_status`; no canonical file edited; the three rows are **not repaired** — the
repair is the lead's/controller's, and G-F0 bytes remain untouchable. `MANUAL_REVIEW` rows are
candidates, not findings. Lexical classification over prose; the quotes are the adjudication
surface.

## Rerun

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-099/form_direction_census/run_direction_census.py   # exit 0 = pins+controls pass
```

Outputs: `census.json` (primary + by-context sweep), `extended_hits.jsonl` (one row per
extended hit with quote and context class).
