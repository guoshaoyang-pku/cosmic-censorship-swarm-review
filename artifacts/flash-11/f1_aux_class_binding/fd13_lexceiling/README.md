# FD13-LEXCEIL-01 — lexical ceiling of the proposed FD-13 R12 fix

**Status:** unverified worker measurement. No completion claim, no gate verdict, no canonical
bytes touched. The schema owner (astra-lead-formulation) binds interpretation.

**Task:** proposed new bounded card under node **F1**, gate **G-CLASSBIND**, classes
**AF-WCC-VAC-GEN / AF-SCC-C2-VAC-GEN / AF-SCC-C0-VAC-GEN**. FORM-DIFF-02
(`assign-FORM-DIFF-02-20260911T2331`) is stopped at its 3.0 h budget; this is the
"next falsifier" recorded in `flash11-FORMDIFF02-rev29-status-20260912T0108`.

## Question

FD-13 is the field-global scope of the canonical R12 geodesic exemption: the check is
`INEXTENDIB.search(field) and not GEODESIC.search(field)` (`INEXTENDIB = /inextendib/i`,
`GEODESIC = /geodesic/i`), so **one geodesic word anywhere in `non_vacuity.condition`
exempts every non-geodesic (SCC-style) inextendibility assertion in that field**. The
proposal (`fd13/tools/patched_check_class_schema.py`, sha `5eaab3f8f031`) keeps the same two
regexes and only changes the granularity: it splits the field on `(?<=[.;])\s+` and tests each
clause. This experiment asks what that patch can and cannot close.

## Design

Byte-minimal fixtures: frozen WCC schema
(`artifacts/formulation/schemas/af_wcc_vacuum.yaml`, sha `d9cebb9404b2`, FROZEN rev29) plus
exactly one appended sentence inside `non_vacuity.condition`, inserted before the closing
quote after the anchor `(worker-16 F1-16-03 accepted).` — no YAML round-trip. The field
already contains a legitimate geodesic phrase ("MGHD is future geodesically incomplete"),
which is what the field-global exemption keys on.

| family | content | prediction |
|---|---|---|
| A (3 probes) | `inextendib` token in its own `.`/`;` clause, no geodesic word in that clause | patch catches at R12 |
| B (3 probes) | `inextendib` token comma/`and`/`while`-joined to a geodesic word in the **same** clause | patch escapes (punctuation granularity) |
| C (4 probes) | non-geodesic inextendibility asserted **without** the `inextendib` token (no extension as a C^{1,1} manifold; no isometric embedding; no causal continuation; no larger supermanifold) | both gates escape (token ceiling) |
| K (6 controls) | legitimate geodesic statements (existing control, comma-joined, clause-split) + the three unmodified canonical schemas | must stay accepted |

Three gates per fixture: canonical base (`000e09e4`), canonical patched proposal (`5eaab3f8`,
run from a self-contained env pinned to rule_spec `40f9bb9e` / KEY_MANIFEST `014e2d30`), and
the independent flash-11 gate (`a89b221c`). All pins are hard-asserted before measuring; the
script aborts on any move.

## Measured (2026-09-12T01:13+08:00)

`lexceiling_results.json` (`4669a326893c`), 16 fixtures × 3 gates, 0 crashes, 0 YAML parse
errors, 0 control false positives (18/18 control checks accepted).

| probe | base | patched | flash-11 | rules (patched) |
|---|---|---|---|---|
| A1 `C^2-inextendible` own sentence (= rev29 leak) | accept | **reject** | reject | R12 |
| A2 future-inextendible Lorentzian manifold | accept | **reject** | reject | R12 |
| A3 semicolon-separated `inextendible` | accept | **reject** | reject | R12 |
| B1 `geodesically complete, and the maximal development is C^2-inextendible` | accept | accept | accept | — |
| B2 geodesic witness `, but ... also inextendible as a manifold` | accept | accept | accept | — |
| B3 `geodesically incomplete, while ... inextendible` | accept | accept | reject | — (flash-11 R12) |
| C1 no extension as a C^{1,1} Lorentzian manifold | accept | accept | accept | — |
| C2 no isometric embedding into a larger manifold | accept | accept | accept | — |
| C3 cannot be continued past the boundary by any causal curve | accept | accept | accept | — |
| C4 no larger manifold contains it as a proper open subset | accept | accept | accept | — |
| K1–K3 geodesic controls, K4 three canonical schemas | accept | accept | accept | — |

Counts: A base-escape 3/3 → patch catch 3/3; B base-escape 3/3 → patch catch **0/3**
(all escape); C base-escape 4/4 → patch catch **0/4** (all escape); controls 0 false
positives; independent flash-11 catches 4/10 non-control probes (A1–A3, B3).

## Falsifier

Pre-registered: FIRED IF (a) any family-C token-free paraphrase is rejected by
canonical_patched at R12, or (b) any family-B punctuation-joined probe is rejected by
canonical_patched at R12, or (c) any control/canonical schema is rejected by any gate, or
(d) an asserted pin moves (binding abort).

**Not fired.** Confounds: none (no non-R12 rejections). The pre-registered prediction is
confirmed on all 10 non-control probes.

## Interpretation (worker-level, non-binding)

1. The clause-local patch is a **strict improvement** over the field-global guard: it closes
   the exact FD-13 channel when the SCC assertion is its own sentence (3/3), with no false
   positive on any control.
2. It does **not** close the channel in general. A non-geodesic claim joined by a comma /
   `and` / `while` to a geodesic word stays in one clause and is exempt (3/3 escape), and any
   paraphrase that avoids the `inextendib` token escapes unconditionally (4/4 escape). Both
   detectors are token detectors; the patch moved the token test, it did not make the check
   semantic or punctuation-insensitive.
3. Consequence for the owner: do **not** score FD-13 closed on the patch alone. Closing the
   class-crossing channel needs a semantic predicate (or an explicit class-content check on
   assertive paths), not another token/clause variant. The independent flash-11 gate's
   disagreement on B3 (catches it, canonical patched does not) shows the two independent
   implementations still differ on the punctuation boundary — a second differential finding,
   not a resolution.
4. Caveat carried from FORM-DIFF-02: the probes are single-sentence, surface-level fixtures
   on one field (`non_vacuity.condition`). They bound the *detector*, not the physics, and
   the 3/3 A-family catch is measured on wording derived from the known FD-13 leak, so it is
   not an out-of-sample semantic estimate.

## Reproduce

```bash
cd artifacts/flash-11/f1_aux_class_binding/fd13_lexceiling
python3 lexceiling_probe.py        # writes lexceiling_results.json, probe_*.yaml
```

Read-only w.r.t. every shared tree; all writes stay in this directory.
