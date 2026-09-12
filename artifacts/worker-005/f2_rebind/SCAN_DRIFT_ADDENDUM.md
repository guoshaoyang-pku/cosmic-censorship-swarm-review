# worker-005 — F2 drift addendum (supersedes the re-bind half of `report.json`)

- **Node** F2 · **classes** `AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN` · **gate** G-FORM
- **Measured at** 2026-09-12T00:32:02+08:00, drift-guard window stable (`drift_guard.json`:
  hash_before == hash_after for all three artifacts)
- **Trigger:** lead-formulation landed rev12 on F1/F2a/F2b at 00:31:41 and again at 00:32:02 —
  after the re-bind report at 00:30:52. The index was not touched.

## Pins at the drift measurement

| artifact | re-bind (00:30:52) | drift (00:32:02) | in index pin |
|---|---|---|---|
| `schemas/af_scc_regularities.yaml` | `94562101a816` | `94562101a816` | — |
| `schemas/af_scc_c2_vacuum.yaml` | `b6123750b37d` | **`5476a3f2c6bc`** | `b6123750b37d` |
| `schemas/af_scc_c0_vacuum.yaml` | `1bb78ce9b357` | **`55d0a1ea9bda`** | `1bb78ce9b357` |

## Findings

1. **A3 pin drift — index invalidated (blocking re-bind).** Both component hashes moved; the index
   pins are stale. The index's own SEP-6 and review note state that a component revision after
   2026-09-12T00:15 invalidates the pins and must fail the integration lint until re-pinned. The
   author lint now fails overall for the same reason. Owner: lead-formulation / `deepseek-flash-05`.
2. **B5 gate regression — rev12 fails the frozen binding gate R22.** Both components return
   `verdict=fail, failed_rules=['R22']`: unknown keys not in `KEY_MANIFEST` and not under
   `extensions:` — `revision_history` and `class_contract_supplement_pointer` (top level),
   `consistency_evidence_sha256` (under `f0_binding`), and `index`/`at`/`notes` inside
   `revision_history` items. The gate tool itself is unchanged since 23:50 (sha256 `000e09e4…`),
   so this is a regression in the rev12 bytes, not in the gate. Repair: register the keys in
   `KEY_MANIFEST.json` or place them under `extensions:` (R26 still applies content rules there).
3. **Hygiene — components fixed, index not.** rev12 collapsed the duplicate `revised_at` keys in
   C2/C0 into a single `revised_at` plus `revision_history` (component duplicate-key finding
   cleared). The index is unchanged: `revised_at` ×4, last-wins `2026-09-12T00:40:00+08:00`, which
   is still future at the measured instant.
4. **H3 pin annotation — stale.** The index revision notes still say components were "pinned from
   disk at 2026-09-12T00:15"; their mtime is now 00:32:02 (delta 1022 s).
5. **Positive: predecessor finding repaired.** `class_contract_pointer` in C2/C0 now resolves in
   the canonical tree (`research_map/formulation_taxonomy.yaml#classes.<ID>`) with the supplement
   pointer moved to its own field, and `f0_binding` is refreshed to the declared F0
   `0abb9ed8a961` with consistency evidence `675a99d0d25b`. The pointer half of
   `HF-W005-01/02` is cleared at rev12 — conditional on the R22 regression above being fixed.

## Disposition

- Class semantics: **N** — no merge, no conclusion inflation; separation checks and the 10-fixture
  corpus still pass at the drift instant.
- Evidence binding: **B** — stale index pins, stale pin annotation, index duplicate/future
  `revised_at`.
- New hard failure: **R22** on both rev12 components against the frozen gate.

## Falsifier

Re-measure: an index re-pinned to `5476a3f2c6bc` / `55d0a1ea9bda` clears finding 1; a rev13 that
registers `revision_history` and the supplement fields in `KEY_MANIFEST` (or under `extensions:`)
and returns a canonical `pass` clears finding 2; deduplicated non-future index `revised_at` clears
finding 3. Any component hash change after the drift instant makes this addendum historical, not
current.
