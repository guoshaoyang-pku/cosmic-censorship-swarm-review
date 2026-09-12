# Independent checker agreement, adjudicated (2026-09-11T23:22:12+08:00)

- fixtures: 34 (5 accept-intended, 23 negatives, 5 escape probes)
- nominal checkers: 4 | **Kish ESS: 4.0**
- No checker's own corpus is a valid gold standard: every flash-11 'good' fixture is adjudicated reject (HF-01 conclusion inflation + HF-06 genericity/quantifier mismatch). Scores are reported against the adjudicated labels, and cross-acceptance measures whether a shared artifact schema exists at all.

## Score against adjudicated labels

| checker | adjudicated rows | accuracy | false accepts | accepts contaminated 'good' fixtures | negative recall |
|---|---:|---:|---:|---|---:|
| w06 | 8 | 7 | 1 | 1 | 20/23 |
| f11 | 8 | 2 | 6 | 4 | 23/23 |
| f13 | 8 | 6 | 2 | 1 | 23/23 |
| w17 | 8 | 8 | 0 | 0 | 23/23 |

## Cross-acceptance of declared-accept documents

| fixture | origin | adjudicated | w06 | f11 | f13 | w17 |
|---|---|---|---|---|---|---|
| `good_af_scc_c0_vac_gen.yaml` | flash-11 | fail | fail | pass | fail | fail |
| `good_af_scc_c2_vac_gen.yaml` | flash-11 | fail | fail | pass | fail | fail |
| `good_af_wcc_scalar_sph.yaml` | flash-11 | fail | fail | pass | fail | fail |
| `good_af_wcc_vac_gen.yaml` | flash-11 | fail | fail | pass | fail | fail |
| `valid_af_wcc_vac_gen.yaml` | flash-13 | fail | pass | fail | pass | fail |

## Pairwise agreement

| pair | n | agreement | kappa |
|---|---:|---:|---:|
| w06|f11 | 34 | 0.6471 | -0.186 |
| w06|f13 | 34 | 0.8824 | 0.2766 |
| w06|w17 | 34 | 0.8824 | 0.0 |
| f11|f13 | 34 | 0.7059 | -0.1039 |
| f11|w17 | 34 | 0.7647 | 0.0 |
| f13|w17 | 34 | 0.9412 | 0.0 |

## Verdict-vector clusters (4)

- cluster 0: w06
- cluster 1: f11
- cluster 2: f13
- cluster 3: w17
