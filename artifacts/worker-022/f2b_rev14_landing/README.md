# W022-F2B-REV14-LANDING-PREFLIGHT-01 — atomic rev14 landing package for F2b

Worker-022, class `AF-SCC-C0-VAC-GEN`, node `F2b`, gate `G-FORM`. Read-only on every canonical
path; all outputs live under this directory plus the worker-022 outbox and checkpoint.

## Why this task exists

At the live rev13 pins every F2b review in the current r3 wave is `revise`, all on the same two
containment carriers, and all six reviewers are pinned to `b2ab6acb`:

| carrier | line | reviewers |
|---|---|---|
| `implication_ledger.forbidden_transfers[0].reason` says C2 is a *larger* extension class | 246 | 017, 018, 053, 066, 075 (= lead L-FORM-01) |
| `regularity.must_not_conflate[0]` still denies containment with C2/C0 | 152 | 017, 018, 035, 066 |

The owner must land a revision before a fresh r3 round can accept. Two independent workers have
already produced repair candidates (worker-022 `a110f8e8`, worker-066 `84b5d3fa`), and worker-100
is independently verifying candidate A's content. What was missing was the *landing* view: does a
repaired revision close exactly the recorded blocking carriers, what does the FROZEN rev30 manifest
look like, and what derived evidence must be regenerated. This preflight supplies that.

## Result

`REV14_LANDING_PREFLIGHT_COMPLETE`: **12/12 checks, 6/6 controls, 0 canonical writes.**

| item | value |
|---|---|
| candidate A (worker-022, removes the denial phrase) | `a110f8e8…` — `candidate_A/af_scc_c0_vacuum.rev14.yaml` |
| candidate B (worker-066, C2-sibling `[R2 major]` correction style) | `84b5d3fa…` — reconstructed byte-exactly from `artifacts/worker-066/f2b_repair_prereg/proposed_patch.diff` |
| FROZEN rev30 draft over A | `cb6f6001d4c3…` — `drafts/FROZEN.rev30.A.draft.json` |
| FROZEN rev30 draft over B | `1297f5cb78d3…` — `drafts/FROZEN.rev30.B.draft.json` |

Both candidates differ from live bytes on exactly lines 152 and 246; both pass the pinned
structural gate (`000e09e46b2f`, exit 0 / `pass`) and return 0 findings under both the frozen
`c266dbec` class-separation detector and the live `a8c04fc3` detector. The two candidates are
byte-identical on the line-246 repair and differ only in the line-152 wording.

## Decision-relevant measurements

1. **Closure.** Every blocking carrier named by workers 017/018/035/053/066/075 maps to detector
   D1 (order-relative size premise) or D2 (live denial) and is silent on both candidates. The
   non-content residual is the `conclusion_type` token binding (`HF-075-F2b-VOCAB`), independently
   adjudicated by worker-066 (`f2b_vocab_binding_adjudication/report.json`, 13/13 checks, 10/10
   controls) through `rule_spec.vocabularies.class_conclusion_type` + the frozen alias registry; it
   needs a gate-owner re-stamp, not a schema edit. This preflight measures the two sources: schema
   token `scc_c0_future_inextendibility` vs F0 `field_vocabulary.conclusion_type.allowed`
   (which contains `strong_cosmic_censorship_C0`), while the alias registry makes the schema token
   canonical.
2. **Reviewer-predicate matrix (measured, not assumed).** All seven documented blocking predicates
   fire on live bytes and are silent on **both** candidates:
   `017 CHK-09/10`, `018 B1/B2`, `053 C10`, `066 H1/H2`. B keeps the withdrawn denial only as a
   lowercase quotation inside the `[R2 major: …]` marker, so the case-sensitive substring checks of
   017/018 stay silent; only a case-insensitive normalized probe still sees it (A is silent even
   there). Style-vs-robustness: B mirrors the accepted C2 sibling bullet, A is maximally
   detector-robust. The owner decides.
3. **FROZEN rev30 draft.** Recomputing all entries with `regenerate_frozen.py`'s own
   `CANONICAL`/`PIN_EXTRAS`/`VOLATILE` key lists shows 0 missing entries and exactly the two C0
   entries (canonical `schemas/af_scc_c0_vacuum.yaml` + authoring mirror) moving. All other pins are
   unchanged. The draft carries a deterministic `frozen_at` placeholder, never a moving timestamp
   (the CF-27 hazard), and re-emits to the same hash.
4. **Derived evidence.** Landing moves the C0 base, so these must be re-run afterwards:
   `measure_semantic_escape.py` (it also regenerates `evidence/rebased_fixtures/` and unblocks the
   `run_acceptance.py` preflight, currently exit 3 on base `1bb78ce9`), `rebase_heldout.py`, and
   `run_gate_tests.py`. The frozen worker-06 semantic-contract corpus must **not** be edited
   (hash-verified provenance); its `ADJ-CONTROL-STALENESS` item is a lead control-rebase-or-pin
   decision that rev14 does not change.

## Controls

| id | mutation | expectation | result |
|---|---|---|---|
| M1 | pristine live bytes | D1 and D2 fire | pass |
| M2 | A with line-246 repair reverted | D1 fires, D2 silent | pass |
| M3 | A with line-152 repair reverted | D2 fires, D1 silent | pass |
| M4 | A with the containment chain reversed | D1 fires (chain-relative, not token grep) | pass |
| M5 | A with the required `conclusion` block deleted | structural gate rejects | pass |
| M6 | rev30 draft with the C0 entry set to rev12 `55d0a1ea` | draft staleness detector fires | pass |

Observation O1: appending a conflicting duplicate top-level `class_id` is rejected on
R02/R06/R09, not on a duplicate-key diagnostic (PyYAML last-wins). Pre-existing gate behaviour.

## Reproduction

```bash
python3 artifacts/worker-022/f2b_rev14_landing/preflight.py            # read-only, rewrites report/checkpoint
python3 artifacts/worker-022/f2b_rev14_landing/preflight.py --emit-events   # also appends outbox events
```

## Authority

Worker preflight only. No canonical write, no node status, no `validation_status`, no gate
verdict. The candidates and the FROZEN rev30 drafts are proposals for the F2b owner to land.

Falsifier: any declared pin moves without a new revision; a candidate fails to reproduce its
sha256; either candidate fails the pinned gate or produces a class-separation finding; D1/D2 do
not fire on live or are not silent on both candidates; the rev30 draft moves any entry other than
the two C0 entries or leaves a missing file; a blocking F2b carrier exists at `b2ab6acb` that is
not D1/D2; or any control departs from its pre-registered expectation.
