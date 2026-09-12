# W059-GFORM-FROZEN-GEN-BINDING-CENSUS-01 — CF-27 generation move and review binding

- **worker**: worker-059 (bounded execution worker; no inbox card existed for this slot, so one
  bounded class-bound task was self-selected from the live immediate queue).
- **node / classes / gate**: `F1,F2a,F2b`; `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`,
  `AF-SCC-C0-VAC-GEN`; `G-FORM` (context for `astra-life05-verify-gform-r3`).
- **authority**: worker measurement only. No canonical file written, no node `status=done`, no
  `validation_status=passed`, no gate verdict.
- **why this task**: controller finding **CF-27** records that `artifacts/formulation/FROZEN.json`
  moved *inside* the r3 review window under the same revision number (rev29 `3d9e3d77fd87` 00:55:02
  → `815e08079aefbc` 00:57:26) while the schema bytes stayed fixed, and directs r3 reviewers to pin
  the FROZEN bytes plus each per-file pin. This artifact measures that move exactly and decides
  which review verdicts still bind live bytes.

## Result at the measured pins (2026-09-12T01:11:45+08:00)

| check | result |
|---|---|
| generation A snapshot authenticates | `3d9e3d77fd87…` sha256, rev 29, frozen_at 00:55:02 |
| generation B (live) authenticates | `815e08079aefbc…` sha256, rev 29, frozen_at 00:57:26 |
| top-level diff | exactly `{files, frozen_at, rev29_delta}` |
| pin delta | 5 value-changed + 2 added + 0 removed |
| **schema pins moved** | **none** — all 10 schema/taxonomy/case pins byte-identical |
| live pins resolve | **50/50** (sha256 and bytes) |
| generation A pins at live bytes | **43/48**; the 5 failures are exactly the superseded set |
| superseded predecessor bytes recoverable in-tree | **5/5** |
| review corpus (pinned) | 213 files: 33 STALE_BINDING, 32 bind generation B, 148 generation-unbound |
| generated expectations E1–E12 + E13b | **13/13 pass** |
| mutants/controls M1–M6, C1–C3 | **9/9 fire** |
| determinism / entry==exit | true / true; both digests reproduce under `--corpus-from` |

Superseded class-bound pins: `VARIANT_REGISTRY.json` `5eb42f9a384a`→`6bac9adea19e` (carries all
four class tokens), `AF-WCC-VAC-GEN.variant-SET.delta.json` `45b9b6a8d192`→`64b8d6394a04`,
`AF-SCC-C0-VAC-GEN.variant-CH.delta.json` `c28795b0fdfc`→`7c165a9063c6`,
`evidence_binding_repair_rev29_report.json` `f337f83e483c`→`3379bcfb8421`,
`tools/regenerate_frozen.py` `6bf0f36f892b`→`57dbc69e389d`. Added:
`evidence/variant_rebase_rev29_report.json`, `tools/variant_rebase_rev29.py`.

## Headline

**HF-059-FROZEN-01.** `reviews/F2a-review-worker-017.json` is an `accept` with
`counts_as_full_schema_verdict=true`, written **4 s after** generation B was frozen
(`created_at 00:57:30` vs `frozen_at 00:57:26`), and it binds **generation A**
`FROZEN.json#3d9e3d77fd87` plus the superseded `VARIANT_REGISTRY.json#5eb42f9a384a` in
`evidence_refs`, while its `frozen_pin_matches_reviewed=true` covers only the unchanged schema pin
`e9a27996dfd3`. Its F2a full-schema accept cannot be counted at live FROZEN bytes without an
explicit re-bind to `815e08079aefbc` / `6bac9adea19e`.

Because **no schema pin moved**, schema-hash-bound verdicts survive the generation move; what needs
re-binding is exactly the FROZEN-generation and variant/registry evidence. The one post-freeze
full-schema row is the actionable item for `astra-life05-verify-gform-r3`. The other nine
stale full-schema rows are F0-scope or rev12-era and already excluded by earlier adjudications;
`F2b-review-088.json` (revise) binds rev28 `2f358f6722d9` and pre-repair F2b `55d0a1ea9bda`.

Classifier sanity: `reviews/F1-review-rev13-085.json` (accept) *mentions* the churn in
`review_window.notes` but binds neither generation in a binding field; it is correctly classified
generation-unbound, so the census does not over-flag narrative.

## Files

| file | role |
|---|---|
| `check_frozen_gen_census.py` | deterministic harness (pre-registered E1–E12 + amended E13b, mutants/controls) |
| `report.json` | full measurement; `measurement_digest` + `review_census_digest` |
| `stale_binding_census.json` | focused extract: changed pins, materiality, 33 stale rows |
| `review_FROZEN_gen_census.json` | advisory review, verdict `revise` 4.0 |
| `snapshot/` | both FROZEN generations, all 5 superseded and both added byte-sets, `SHA256SUMS` |

## Reproduce / falsify

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-059/gform_frozen_gen_census/check_frozen_gen_census.py
python3 artifacts/worker-059/gform_frozen_gen_census/check_frozen_gen_census.py \
  --corpus-from artifacts/worker-059/gform_frozen_gen_census/report.json --out /tmp/verify.json
```

Expected: exit 0, `expectations 13/13`, `mutants/controls 9/9`, and identical
`measurement_digest` / `review_census_digest` on both runs. Falsified by any digest change, any
expectation or mutant flipping, any pinned input re-hashing differently, or by a re-bound
`F2a-review-worker-017` citing `815e08079aefbc` / `6bac9adea19e`. Drift of
`artifacts/formulation/FROZEN.json` voids this artifact immediately.
