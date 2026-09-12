# FD14-PROBE10-XMEAS — independent cross-measurement on worker-06 FORM-PROBE-10

Bounded class-bound worker task (parent assignment `assign-FORM-DIFF-02-20260911T2331`).
It closes the two still-open FORM-DIFF-02 acceptance tests:

- **D3** — per-fixture disagreements between independent implementations, with minimal repro.
- **D4** — my own escape rate on the worker-06 semantic corpus once published, stated as a
  number with the corpus hash.

| field | value |
|---|---|
| task_id | `FD14-PROBE10-XMEAS` |
| actor | `deepseek-flash-11` |
| node / gate | `F1` / `G-CLASSBIND` |
| class_ids | `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN` |
| corpus | worker-06 `FORM-PROBE-10`, manifest `9afd257312b5`, frozen rev 28, bases rev28 |
| authority | advisory worker evidence only — no gate verdict, no node status, no `validation_status=passed`, no canonical write, no theorem, no physics result |

## Pins (measured before the run; fail-closed)

| object | path | sha256 |
|---|---|---|
| corpus manifest | `artifacts/worker-06/probe10/manifest.json` | `9afd257312b5019d19adf94fb6488696ef902a57bcaf898183085860adb2882d` |
| worker-06 published verdicts | `artifacts/worker-06/probe10/raw_verdicts.json` | `88e52d144602b41108d1534a0866ba39698f226131f7ed26714040f7ace2d6bd` |
| my independent gate | `artifacts/flash-11/f1_aux_class_binding/check_schema.py` | `a89b221c1c68e34f87776e5648a8e890d2a0f9f0b919280d3e176422b2d689f0` |
| canonical gate | `artifacts/formulation/tools/check_class_schema.py` | `000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff` |
| runner | `.../probe10_cross/run_probe10_cross.py` | `56e4ca360be79f9f9d8e78653b1bb56b79877cf75a2da82b7a72e339c574f43c` |
| results | `.../probe10_cross/cross_results.json` | `8995fee5736b8ac1df97ffd4bb3c5d78bb10aa0aa7123f9bad6f3247ac93f814` |
| determinism check | `.../probe10_cross/determinism_check.json` | `1dbec9b040efbe92bd827b6d007a826ebe365df4fb4ca965a10366071d07034b` |

The live canonical schemas are at rev29 (`d9cebb9404b2` / `e9a27996dfd3` / `b2ab6acb2bbe`).
`FORM-PROBE-10` fixtures are built on the rev28 base bytes; the measurement is bound to the
fixture bytes and the two gate hashes above, not to the live schema revision.

## Method

```bash
python3 artifacts/flash-11/f1_aux_class_binding/probe10_cross/run_probe10_cross.py
```

Every manifest-listed fixture is sha256-verified against the manifest before either gate runs.
Both gates are invoked as `<gate> <fixture> --json` and normalised to `accept` / `reject`;
`crash`/`error`/timeout are recorded separately. The run aborts (`valid=false`, exit 3) if the
manifest, a fixture, the worker-06 verdict reference, or either gate hash has moved.
19 manifest fixtures (12 mutants, 5 pass controls, 2 sensitivity controls) plus the 2 post-hoc
probes outside the manifest (`h01`, `h02`) were measured.

## Result — D4: escape rate on FORM-PROBE-10 @ `9afd257312b5`

| instrument | accepted mutants | escape rate |
|---|---:|---:|
| flash-11 independent gate `a89b221c` | 11 / 12 | **0.9167** |
| canonical gate `000e09e4` | 11 / 12 | 0.9167 |
| worker-06 published stage A (`raw_verdicts.json`) | 11 / 12 | 0.9167 |

The single catch for all three is `m03_rephrased_completeness_in_c0_iplus_definition`
(family `iplus-completeness-in-scc`), failed at **R09** by both live gates; the published
worker-06 stage-A catch therefore reproduces at these pins.

Per-family (flash-11 / canonical / worker-06-published escaped, out of n):

| family | n | flash11 | canonical | w06 |
|---|---:|---:|---:|---:|
| converse-entailment | 1 | 1 | 1 | 1 |
| curvature-hypothesis-in-c0 | 1 | 1 | 1 | 1 |
| foreign-regularity-in-c2 | 1 | 1 | 1 | 1 |
| genericity-transfer-truth-table | 1 | 1 | 1 | 1 |
| iplus-completeness-in-scc | 2 | 1 | 1 | 1 |
| multi-end-slice | 1 | 1 | 1 | 1 |
| scc-content-in-wcc | 1 | 1 | 1 | 1 |
| wcc-content-in-scc | 4 | 4 | 4 | 4 |

Controls:

| control class | n | flash-11 | canonical |
|---|---:|---|---|
| pass controls (must accept) | 5 | 5/5 accept | 5/5 accept |
| sensitivity controls (must reject) | 2 | **0/2 rejected** | 2/2 rejected |
| post-hoc probes (outside manifest) | 2 | 2/2 accept | 2/2 accept |

`valid=true`: no pin moved, no fixture drifted, no pass control was rejected. But the
sensitivity check **fails for my instrument**, so
`interpretation.like_for_like_with_canonical = false`: 11/12 is an upper bound from a less
sensitive instrument, not a like-for-like detection comparison.

## Findings (D3 — disagreements are the deliverable)

### FD14-01 — flash-11 R12 misses an assertive WCC token the canonical R12 catches

`d01_literal_visible_token_c0` (sensitivity control, sha `3668441376fb`) appends to the C0
conclusion (`make_probes.py:215-218`, `fixtures/d01_literal_visible_token_c0.yaml`):

> A visible incomplete geodesic decides this class.

| gate | verdict | rule |
|---|---|---|
| flash-11 `a89b221c` | `accept` (exit 0) | — |
| canonical `000e09e4` | `reject` (exit 1) | `R12` |
| worker-06 stage A (published) | `fail` | `R12` |

Minimal repro:

```bash
python3 artifacts/flash-11/f1_aux_class_binding/check_schema.py \
  artifacts/worker-06/probe10/fixtures/d01_literal_visible_token_c0.yaml --json   # ACCEPT
python3 artifacts/formulation/tools/check_class_schema.py \
  artifacts/worker-06/probe10/fixtures/d01_literal_visible_token_c0.yaml --json   # fail R12
```

Mechanism: flash-11 R12 (`check_schema.py:648-654`; token list `WCC_LEAK_PATTERNS`
at `check_schema.py:348-353`) scans the assertive paths for `visible (from|to) i+`,
`no naked singularity`, `visible_singularity_from_i_plus`, `not visible from` — but not the
`visible … geodesic` shape. The canonical tool's `FOREIGN[fam]` set at `000e09e4` is wider
(`check_class_schema.py:308-317`).
**Targeted rule proposal:** widen the flash-11 R12 WCC token set to the canonical assertive
family (or import the canonical token list verbatim), then re-run this fixture set; the
probe is a must-catch.

### FD14-02 — flash-11 has no R31 foreign-regularity scan

`d02_literal_twice_diff_c0` (sensitivity control, sha `def473c89b39`) appends to the C0
conclusion (`make_probes.py:220-223`):

> The extension is assumed twice differentiable.

| gate | verdict | rule |
|---|---|---|
| flash-11 `a89b221c` | `accept` (exit 0) | — |
| canonical `000e09e4` | `reject` (exit 1) | `R31` |
| worker-06 stage A (published) | `fail` | `R31` |

Minimal repro:

```bash
python3 artifacts/flash-11/f1_aux_class_binding/check_schema.py \
  artifacts/worker-06/probe10/fixtures/d02_literal_twice_diff_c0.yaml --json   # ACCEPT
python3 artifacts/formulation/tools/check_class_schema.py \
  artifacts/worker-06/probe10/fixtures/d02_literal_twice_diff_c0.yaml --json   # fail R31
```

Mechanism: flash-11's rule horizon is R01–R16; there is no R31. "twice" is only inspected
inside `implication_ledger` token direction (R16, `check_schema.py:719`), so a C0 schema that
asserts a C2 regularity class in `conclusion.statement_natural_language` is accepted. The
canonical R31 (`check_class_schema.py:510-535`) scans the assertive paths and the
`extension_predicate` subtree with a foreign-regularity regex for the class.
**Targeted rule proposal:** port canonical R31 into the flash-11 gate as a new code over the
same assertive-path list, keeping the existing R13 composite-wording scan distinct.

### FD14-03 — matched escape rate ≠ matched detection power

On the 12 mutants all three instruments agree 12/12 on the normalised verdict
(flash-11 vs canonical: `flash11_vs_canonical_agreements = 12`), and both live gates escape
11/12. That agreement is **corpus-limited**: the two disagreements appear only on the
sensitivity controls, where canonical catches both literal probes and flash-11 catches
neither. A gate comparison that reports only mutant escape rate (or only mutant agreement)
would have declared the two implementations equivalent at these pins. The disagreements are
the deliverable, per the FORM-DIFF-02 falsifier.

Post-hoc `h01`/`h02` (synonym paraphrases, outside the manifest) are accepted by both gates
(2/2 escape each), consistent with the published worker-06 post-hoc note; they are reported
separately and are not part of the escape-rate denominator.

## Falsifier

Pre-registered before the run:

> FIRED IF (a) the manifest, a manifest-listed fixture, worker-06 `raw_verdicts.json`, or
> either gate hash differs from its pin at run start (abort, no number); (b) flash-11 or
> canonical rejects any of the 5 pass controls (instrument false positive, no number);
> (c) a re-run at the same pins returns a different per-fixture verdict for any fixture
> (nondeterministic instrument); (d) the published worker-06 stage-A catch m03 is not
> reproduced as a reject by either gate at the pins (corpus/pin mismatch).

Status: **not fired** on 2026-09-12.

- (a) all four pins matched exactly (`pins_measured` in `cross_results.json`);
- (b) 5/5 pass controls accepted by both gates;
- (c) re-run determinism check: 21/21 fixtures identical verdict vectors
  (`determinism_check.json#1dbec9b040ef`, vector sha `97665ad885efecd7` both runs);
- (d) m03 caught by both gates at R09, matching the published stage-A record.

Re-fire conditions: any write to either gate (hashes above), a new `FORM-PROBE-10`
manifest revision, or a new `raw_verdicts.json`. The escape number is bound to the pinned
bytes only.

## Non-claims

- No gate verdict, no node status, no `validation_status=passed`, no canonical write.
- No theorem, counterexample, or physics result. "Escape" here means only that a gate
  accepted bytes into which worker-06 inserted wrong-class content; it is a statement about
  the gate, not about the class definitions being wrong.
- The sensitivity failure invalidates a like-for-like comparison; the 0.9167 number is
  reported with that caveat and is not evidence that the classes are unguarded.
- Advisory worker evidence; the schema owner (`astra-lead-formulation`) and the audit lead
  bind interpretation, and `astra-life05-verify-gform-r3` owns the G-FORM adjudication.
