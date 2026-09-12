# Astra directive compliance — literature group

- Actor: lead-literature · Time: 2026-09-11 ~23:56 (+08)
- Directive answered: `astra-w07adj-02` (inbox `comms/inbox/astra-lead-literature.jsonl`, line 4): class tokens outside the four frozen classes in `ledger/theorems.jsonl`.
- Assignments answered: `asg-2026-09-11-L0-astra-lead-literature-03`, `asg-2026-09-11-L1-astra-lead-literature-04`.

## 1. Four-class compliance (astra-w07adj-02)

- `class_ids` now contains only: `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH`.
- Extension/other tokens (`DEFINITIONS`, `OTHER-MODELS`, `BH-FORMATION`, `NS-CONSTRUCTION`, `SYNTHESIS`, `MGHD`, `REVIEW`, …) live in the new `ledger_tags` field and are indexed in `artifacts/literature/tag_index.md`.
- The builder **fails closed** if any `class_ids` token is outside the four; `MANIFEST.json:counts.entries_with_extension_class_tokens = 0`.
- Cross-class relevance of matter-model results is carried by `informs_classes` (also restricted to the four) and rendered as an "Informing evidence" section in each class dossier.

## 2. L0 acceptance fields

Every row of `ledger/theorems.jsonl` now carries `verification_status` in {`unverified`, `abstract-read`, `full-text`, `page-checked`} (Astra acceptance wording), derived conservatively: abstract-level evidence → `abstract-read`; metadata-only → `unverified`; no row claims `full-text` or `page-checked` yet. Current counts: 61 abstract-read, 1 unverified (the sole unverified row is D-009, a provisional background entry whose sources are metadata-only). Fixed 2026-09-12: nine legacy records were missing the evidence_type field, which had skewed the derivation.

Rows also carry: `source_ids` (locators in the registry), `statement_exact` (theorem as quoted), `assumptions`, `class_ids`, `does_not_imply` (what it does not prove), `falsifiers`, plus `status`, `evidence_level`, `scope_caveats`, `unresolved`.

## 3. L1 acceptance fields

`ledger/citation_audit.csv` is one row per source and now carries: locator (`doi`/`arxiv_id`/`url`), `resolver_result` (`resolved`/`unresolved`), `verification_method`, `exact_locator` (page/record URL), `class_mapping` (frozen-class mapping of the entries that cite it, or `(evidence/tag only)`), `verdict`, `reviewer`, and the verbatim `evidence_excerpt`. 95 sources, all locator-resolved; the only content-unread candidate is `SRC-090` (Chrusciel 1992, Contemp. Math. 132, 235-273), explicitly not citable as scope evidence.

## 4. Worker integration (assignment task "integrate workers 07-11")

- Worker-07 batch (quarantined earlier): 3 arXiv IDs independently re-fetched and merged as SRC-054/055/056; review verdict recorded in the outbox.
- Worker-08 L1 shard: integrated row-by-row; see `artifacts/literature/reviews/worker08-L1-integration.md`. Two new sources adopted from worker-08 (SRC-092 Christodoulou 1999 CQG; SRC-093 Dafermos-Rodnianski 2009 red-shift); one candidate rejected for the AF class (Ringstrom 2013, cosmological). Worker-09's SCC shard was integrated separately: SRC-094 (Gundlach-Martin-Garcia 2007) and SRC-095 (Van de Moortel 2018 EM-Klein-Gordon) adopted, with a passed negative-control DOI test recorded in reviews/worker09-L1-integration.md.
- Worker-09/10/11: no shard found on disk addressed to L0/L1 at this timestamp; if shards exist elsewhere the lead will record them as assignment drift rather than completion.

## 5. F0/F1/F2 binding

The four frozen schemas (`artifacts/formulation/schemas/*.yaml`, FROZEN.json rev 5) define class contracts and vocabulary (`regularity_token`, `genericity.kind`, `genericity.topology_or_measure`, `conclusion_type` = weak_cosmic_censorship / strong_cosmic_censorship_C2 / _C0). The ledger's class dossiers now use those four class ids verbatim. Mapping note for downstream readers: the ledger's genericity vocabulary (open+dense, comeager, first category, positive probability, high codimension, fine-tuned non-generic, unquantified) is descriptive and lives in scope caveats; for any map-level theorem claim it must be translated into the F1/F2 `genericity.kind` + `genericity.topology_or_measure` slots (full mapping: `artifacts/literature/GENERICITY_MAP.md`). D-007 records the only fully explicit quantifier in the primary literature (Luk-Oh Part II: open in weighted C^1, dense in weighted C^infinity).

**Binding statements used by the ledger (frozen hashes):**

| class | frozen schema sha256 (prefix) | binding statement |
|---|---|---|
| AF-WCC-VAC-GEN | `f512af5f4db3` | MGHD of generic AF vacuum data has complete I+, and no future-incomplete causal geodesic is visible from I+ (hiddenness, not absence). Genericity: `residual_comeager` in the weighted-Sobolev subspace topology on the constraint manifold. |
| AF-SCC-C2-VAC-GEN | `836746b39be4` | MGHD of generic AF vacuum data admits no proper future C² vacuum extension; `C^{1,1}`/`H^2_loc` are different classes; genericity `residual_comeager`. |
| AF-SCC-C0-VAC-GEN | `188e513130c6` | MGHD of generic AF vacuum data admits no proper future extension with merely continuous Lorentzian metric; genericity `residual_comeager`. |
| AF-WCC-SCALAR-SPH | (F0 taxonomy contract `64948570…`) | AF spherical massless-scalar collapse; WCC-side class (visibility/hiddenness), genericity slot owned by F1. |

**Class-dossier consequence recorded in `LITERATURE_STATUS.md`:** the strongest primary evidence currently available is `dense_open` (Luk-Oh) or `open_set`/special-family (all vacuum results); no verified primary theorem reaches the schemas' `residual_comeager` bar for the AF vacuum classes.

## 6. Residual items for Astra

1. F0/F1/F2 gate status is owned by formulation; the literature group binds to the frozen hashes in `artifacts/formulation/FROZEN.json` and will re-check if they change.
2. The 2026 vacuum SCC/Kerr-stability results are preprints (T-526/T-528) or accepted-in-press (T-527, Invent. Math. per arXiv comment); the ledger marks this with `evidence_level` and does not request validation promotion.
3. Evidence references in outbox events now include `path#sha256-prefix` where an artifact event is emitted.
