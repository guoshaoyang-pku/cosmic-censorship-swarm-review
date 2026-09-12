# W100-F2B-REV30-DIRECTION-CROSSVERIFY-01

Bounded class-bound task taken by **worker-100** at 2026-09-12T01:12+08:00. Node **F2b**,
class **AF-SCC-C0-VAC-GEN**, gate **G-FORM**. No inbox card existed for worker-100; the task was
self-selected from the open rev30 repair thread.

## Question

Three independent corrected-remedy candidates exist for the F2b `regularity.must_not_conflate[0]`
defect, plus the staged rev30 base. Which one is direction-consistent with the document's own
declared containment chain and implication ledger, structurally gate-passing, internally
consistent, and minimal, so the owner can publish it as the F2b part of rev30?

## Why it matters

worker-058's freeze rehearsal (`artifacts/worker-058/rev30_freeze_rehearsal/report.json`,
sha256 `1e31bbe5e933`) is staged on candidate `84b5d3fa29a6` and its runbook applies that
candidate. worker-080 measured a hard entailment-direction inversion in it. Publishing
`84b5d3fa` verbatim lands the inversion; picking among the corrected variants without a
hash-bound comparison is unreviewed. This task supplies that comparison.

## Pins (all re-verified live at run time; any shared drift voids the run)

| object | sha256 |
|---|---|
| `schemas/af_scc_c0_vacuum.yaml` (live canonical, rev13) | `b2ab6acb2bbe` |
| `artifacts/formulation/schemas/af_scc_c0_vacuum.yaml` (mirror) | `b2ab6acb2bbe` |
| `schemas/af_scc_c2_vacuum.yaml` (F2a sibling) | `e9a27996dfd3` |
| `artifacts/formulation/FROZEN.json` (rev29) | `815e08079aef` |
| `artifacts/formulation/tools/check_class_schema.py` | `000e09e46b2f` |
| staged base `.../staged/candidate_84b5d3fa.yaml` | `84b5d3fa29a6` |
| corrected `.../staged/candidate_corrected.yaml` (w080) | `51c253c46306` |
| corrected `.../staged/candidate_nesting_only.yaml` (w080) | `4951cc969803` |
| corrected `artifacts/worker-023/f2b_dir_review/proposed_af_scc_c0_vacuum_v2_corrected.yaml` | `9ab32ee39d00` |

## Method

`crossverify_direction.py` (deterministic, stdlib + PyYAML) reads the pinned snapshots and
adjudicates, per target, checks S1-S10 declared in `preregistration.json`:

- S1 identity; S2 required subset chain `E_C2 ⊂ E_{C^1,1} ⊂ E_H2loc ⊂ E_C0` in the bullet;
- S3 no unquoted denial (correction notes and quoted spans are stripped with an
  apostrophe-aware scanner, so possessives are not mistaken for quote pairs);
- S4 no assertion use of the prohibited phrase; S5 no claim `X-inextendibility ⇒ this class`
  for X ≠ this class (a claim is only exempt when immediately preceded by `not`);
- S6 direction coverage: explicit licensed claim or explicit delegation to `implication_ledger`;
- S7 internal consistency: `forbidden_transfers` rows must be unlicensed edges,
  `one_way_entailments` rows must be licensed by the declared chain, the
  `forbidden_weakenings` row must say `not this class`, `subsumption_note` must say
  `never the reverse`, `extension_class_containment` must say STRONGEST / entails-the-others;
- S8 live canonical structural gate (`check_class_schema.py --json`, hash-pinned) exit 0, pass,
  zero failed rules; S9 one-leaf delta vs the staged base; S10 two-leaf delta vs canonical.

Controls M1-M10 include a re-inverted bullet, a dropped direction sentence, a `larger`-premise
regression, a dropped `forbidden_weakenings` row, an inverted chain, an unquoted denial, an
identity positive control, a removed nesting pointer, and the canonical + staged-base negative
controls. All ten must match their declared expectation.

## Result — `CROSSVERIFY_COMPLETE`

- **Recommended: `cand023_v2`** (`artifacts/worker-023/f2b_dir_review/proposed_af_scc_c0_vacuum_v2_corrected.yaml`,
  sha256 `9ab32ee39d00`). Clean on S1-S10: states the licensed direction
  (`this class's conclusion ENTAILS H2_loc-inextendibility and C2-inextendibility, never the
  reverse`), records both the R2 denial correction and the R3 direction correction, passes the
  canonical structural gate, changes exactly one leaf versus the staged base
  (`regularity.must_not_conflate[0]`) and exactly the two repair leaves versus canonical.
- Also clean: `cand080_corrected` (`51c253c46306`, explicit both directions, compact) and
  `cand080_nesting` (`4951cc969803`, direction delegated to the ledger; smallest exposure but
  least explicit). Ranking rule in `preregistration.json`.
- **Not publishable as-is: staged base `84b5d3fa`** — hard finding **HF-W100-R3-01**:
  `regularity.must_not_conflate[0]` asserts `H2_loc-inextendibility ENTAILS this class's
  conclusion` inside the C0 file. The file's own chain (`E_H2loc ⊂ E_C0`) and its
  `forbidden_weakenings` row (`H2_loc-inextendibility is weaker and entails the C2 sibling, not
  this class`) make that an unlicensed reverse transfer. Its structural gate still passes: the
  mechanical gate is blind to this class of defect.
- Residual, untouched by all candidates: `HF-075-F2b-VOCAB` (`conclusion.conclusion_type =
  scc_c0_future_inextendibility`).

Reports: `report.json` sha256 `3ad70453c7ec`; instrument `crossverify_direction.py` sha256
`172144531c3d`; pre-registration `preregistration.json` sha256 `694938112218`; pins
`pinned.sha256` sha256 `842f25b0f139`.

Reviews written (both scoped, `counts_as_full_schema_verdict=false`):
`reviews/F2b-direction-crossverify-worker-100.json` (revise, hard HF-W100-R3-01, staged base) and
`reviews/F2b-remedy-crossverify-worker-100.json` (accept, remedy text only, recommended candidate).

## Falsifier

Re-run `python3 crossverify_direction.py` at the same pins. This cross-verification is falsified
if any shared pin differs, if any target's live bytes differ from its declared hash, if a re-run
yields different per-check results, if a control departs from its declared expectation, or if any
clean candidate is shown to contain a direction claim the document's own containment chain does
not license.

## Authority limits

Worker measurement only. No canonical path was written; no node status, no
`validation_status=passed`, no gate verdict is claimed. The owner (lead-formulation) owns any
rev30 publication; publishing a corrected candidate changes the F2b canonical hash and voids
`b2ab6acb`-bound verdicts, as worker-035 recorded.
