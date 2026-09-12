# W076-F0-TAXCASES-REV5-05 — F0 taxonomy-case corpus content validity + pin-repair verification

Worker: `worker-076` · Node: `F0` · Gate: `G-F0` · Classes: `AF-WCC-VAC-GEN`,
`AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH`
Status: worker completion claim only; artifact `validation_status = unverified`; no gate verdict.

## Question

`schemas/taxonomy_cases.jsonl` is the F0 adversarial class-leakage corpus and is cited in map
`G-F0` `evidence_refs`. It was stale-pinned (36/36 rows at rev2 `66bf917bd368`, blocking
`HF-094C-1` in `reviews/closefind-verify-094.json`) and was re-stamped to live rev5
`0abb9ed8a961` at 00:42:36 while this worker was measuring. This probe independently measures:

- **Q1** — is the corpus *content* valid at the live canonical rev5 taxonomy?
- **Q2** — did the pin repair change any verdict (pure restamp vs content edit)?
- **Q3** — does the replenished checker's new `STALE_TAXONOMY_PIN` guard (C11) actually catch
  the pre-repair defect class?
- **Q4** — is the corpus content-bound to the live axis values, i.e. does `F-094C-1`'s proposed
  `AF-WCC-SCALAR-SPH` genericity change break it?

## Result — `CONTENT_VALID_PIN_REPAIR_VERIFIED`

| check | measurement |
|---|---|
| checker at live pins (`artifacts/flash-02/check_taxonomy_cases.py` c68ae8bc) | **PASS**, 0 errors, 16 positive / 20 negative |
| built-in mutation controls | **11/11** fire |
| coverage | ≥2 both polarities for all four classes; disjointness OK |
| independent axis-vector resolver | 25/25 resolver-decidable declarations agree, 0 fail (11 non-decidable are leak-kind cases) |
| R1 identity rebind (36 rows at live pin) | payload identical to canonical → repair is a pure restamp |
| R2 stale rebind (36 rows at rev2 `66bf917bd368`) | C11 `STALE_TAXONOMY_PIN` fires on **36/36** rows → guard catches `HF-094C-1` |
| S1 scalar `genericity_kind` `unresolved → provisional_baire_residual` | **6 content errors** (P13–P16 `POSITIVE_NOT_SINGLE_CLASS`, N12 `SEMANTIC_AXES_NOT_CLEAN_OR_VIOLATION`, scalar positive coverage 0) |
| S2 C2/C0 `regularity_token` swap | **18 content errors** |
| canonical input drift during run | none (pre == post) |

Pre-repair state is preserved as a hash-bound observation: the checker report produced by this
worker at **00:42:09**, before the 00:42:30/00:42:36/00:43:17 repair, records corpus
`f0c20b96f76d` + catalog `215f6e22` against taxonomy `0abb9ed8a961`, verdict PASS, 10/10
controls. Those bytes were overwritten and are not re-runnable; the report embeds the input
hashes.

## Load-bearing consequence for F-094C-1

The corpus is **content-bound** to the live scalar axis. Setting
`AF-WCC-SCALAR-SPH.axes.genericity_kind` to `provisional_baire_residual` (one of the two repairs
`reviews/closefind-verify-094.json` F-094C-1 proposes) makes the checker fail on the four scalar
positive cases plus one semantic case and zeroes scalar positive coverage. Keeping
`unresolved` keeps the corpus PASSing. Any revision that changes the scalar axis must amend the
scalar case rows in the same revision, or the corpus must be re-derived from the amended
taxonomy.

Residual, not adjudicated here: the corpus meta says the taxonomy is `frozen_published` while
the catalog and the taxonomy file itself say `draft_unverified` (F-094C-2 territory), and the
map `G-F0` `unmet` text still cites `66bf917b` as "the current hash" at `map.updated_at`
00:43:08. Both are owner-side records, outside this probe's verdict.

## Files

| file | role |
|---|---|
| `probe_taxcases_rev5.py` | reproducible driver (read-only on canonical bytes) |
| `probe_result.json` | full result: pins, runs, per-case resolver table, controls, censuses, falsifier |
| `checker_report_canonical.json` | third-party checker report at live canonical pins |
| `checker_report_snapshot.json` | same on byte-identical snapshots (provenance control) |
| `checker_report_identity_rebind.json` / `checker_report_stale_rev2_rebind.json` | R1/R2 derived-pin controls |
| `checker_report_mutant_scalar_genericity.json` / `checker_report_mutant_c2c0_swap.json` | S1/S2 counterfactuals |
| `checker_report_canonical_prerepair_dryrun.json` | preserved 00:42:09 pre-repair observation |
| `inputs/` | byte-identical snapshots of taxonomy, corpus, catalog, checker |
| `derived/` | derived rebind copies and mutant taxonomies (canonical files never written) |
| `SHA256SUMS.txt` | hashes of all of the above |

## Reproduction

```bash
python3 artifacts/worker-076/f0_taxcases_rev5/probe_taxcases_rev5.py
```

## Falsifier

FALSE if (a) any canonical input sha256 differs between the pre and post pin (verdict must read
UNMEASURED); (b) the checker at rev5 returns non-PASS or any built-in control escapes; (c) the
independent resolver disagrees with any declared expected classification/resolution; (d) the
identity rebind changes the payload, or the rev2-restamped copy fails to raise
`STALE_TAXONOMY_PIN` on all 36 rows; (e) either axis counterfactual, rebased to its own mutant
pin, produces zero content errors.

## Non-claims

No gate verdict or node transition; no adjudication of F-094C-1; no assertion of taxonomy truth;
no disposition of the 9 open cases; no verification of repair authorship or event/review binding
at the new corpus hash; canonical files unmodified.
