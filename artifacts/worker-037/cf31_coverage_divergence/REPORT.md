# W037-CF31-COVERAGE-DIVERGENCE-01 — F2b coverage-count divergence (read-only)

| field | value |
|---|---|
| worker | worker-037 |
| class | `AF-SCC-C0-VAC-GEN` (F2b) |
| node / gate | F2b / G-FORM |
| finding | CF-31 → REC-39 (`astra-life05-verify-gform-r3` binding-table requirement) |
| snapshot time | 2026-09-12T01:22:19+08:00 |
| artifact | `artifacts/worker-037/cf31_coverage_divergence/report.json` |
| checker | `artifacts/worker-037/cf31_coverage_divergence/check_cf31_coverage.py` |
| canonical writes | **0** — report.json + temp dirs only |

## Answer

CF-31 is real but it is **not** a disagreement about the same measurement. The two counts
enumerate different file sets under different rules, and neither is a gate-coverage count:

| rule | files | full accept | full revise | scoped revise | inconclusive |
|---|---:|---:|---:|---:|---:|
| live controller scan (`astra_lifecycle.review_coverage`) | 7 | **3** (052, 071, 090) | 4 (017, 072, 075, 085) | 0 | 0 |
| formulation-lead census (7 tracked reviewers) | 7 | **0** | 4 (017, 018, 035, 075) | 3 (053, 066 ×2) | 0 |
| pin-bound universe (any F2b scope signal + explicit pin match) | 16 | **3** (052, 071, 090) | 7 (017, 018, 035, 041, 072, 075, 085) | 5 (017*, 029, 053, 066 ×2) | 1 (018) |

\* `reviews/CF31-F2b-binding-table-worker-017.json`, a parallel worker-017 contribution created
at 01:21:32, inside this run's window; recorded in the binding table by sha256, not consumed.

- CF-31's quoted **4 accepts** is the **01:12:38 pass-08-open** scan. It went stale 2m13s later:
  `reviews/F2b-review-worker-072-rev29.json` self-superseded **accept → revise** at
  **01:14:51** under an unchanged filename (its own `revision_history`: rev1 accept
  01:10:13, file sha `7487f310d208…`; rev2 revise 01:14:51). The pass-08-final scan at
  01:16:25 already reports **3**.
- The lead's **0 accept / 7 revise** is a count over the seven reviewers it tracked. It is not
  an enumeration of the pin: it omits the three pin-bound full accepts that exist on disk
  (worker-052, worker-071, worker-090).

## Root causes (each controlled)

1. **Rule scope.** The controller scan keys F2b membership on `_targets_in_review`, which
   normalizes only `target_id` / `target` / `target_subnode`. Nine pin-bound F2b verdict files
   express the target as `schemas/af_scc_c0_vacuum.yaml#<pin>`, `F2b@<pin> (…)`, a review-file
   fragment, or omit `target_id`; they match the pin but are silently dropped from the scan
   (control C3). They include six revises and one inconclusive.
2. **Reviewer scope.** The lead census covers its own seven tracked reviewers and therefore
   never examined the three accepts on disk.
3. **Mutability.** Review files are mutable under fixed names. worker-072's self-supersession
   is the second confirmed instance of the pattern the lead reported for worker-045/075; any
   count quoted from a scan is bound to the scan instant, not to the filename.
4. **Category error.** The scan answers "which verdict files exist and what do they say".
   The lead answered "do any accepts survive the live hard findings". REC-39 needs both
   columns, and it needs them keyed by **file sha256**, not filename.

## Materiality column (measured, not adjudicated)

At the pinned bytes, the three live full accepts declare **zero hard failures**
(worker-052, worker-071, worker-090 — `hard_failures: []`). The live full revises carry hard
failures against the *same* bytes:

| reviewer | hard failures | explicitly blocking |
|---|---:|---|
| worker-017 | 2 | yes (`B17-R13-01`, `B17-R13-02`) |
| worker-018 | 2 | yes (`W018-R13-F2B-B1/B2`) |
| worker-072 | 2 | yes (`W072-F2B-HF-01/02`) |
| worker-075 | 2 | unlabeled (`HF-075-F2b-*`) |
| worker-085 | 1 | unlabeled (`HF-085B-01`) |
| worker-035 | 1 | no |
| worker-041 | 0 | no |

So the enumerable truth is **3 full accepts / 7 full revises / 5 scoped revises / 1
inconclusive** (worker-017 appears in one full and one scoped file), and the material question —
whether the accepts' "non-blocking" classification or the revises' "blocking" classification
governs — is the gate owner's ruling, not this worker's. **A coverage number without the
materiality column is not a gate-coverage count**, which is why both prior counts were unsafe to
cite.

## Pins and instrument (measured at T0 = T1)

| pin | sha256 |
|---|---|
| `schemas/af_scc_c0_vacuum.yaml` + mirror | `b2ab6acb2bbe…` (unchanged) |
| `artifacts/formulation/FROZEN.json` (rev29) | `815e08079aef…` |
| `research_map/research_map.json` | `4cd5fc5ec248…` |
| `research_map/astra_lifecycle.py` (scan rule) | `b155313797c0…` |
| review-corpus digest (file+sha+verdict) | `7ee4b9335e52…`, stable T0→T1 |

Accept files, byte-bound:

| file | reviewer | file sha256 |
|---|---|---|
| `reviews/F2b-rev13-full-090.json` | worker-090 | `345f74bb73f4…` |
| `reviews/F2b-review-rev13-052.json` | worker-052 | `c3f720292e47…` |
| `reviews/F2b-review-rev13-worker-071.json` | worker-071 | `e5a313894f7c…` |

## Controls (8/8 PASS)

| # | control | observed |
|---|---|---|
| C1 | live scan reproduces pass-08-final | `[052, 071, 090]` |
| C2 | 072 reverted to its recorded rev1 accept reproduces pass-08-open | `[052, 071, 072, 090]` |
| C3 | target normalization is the drop cause | dropped file enters scan when `target_id` is normalized |
| C4 | lead's 7 files reproduce 0 accept / 7 revise | 0 / 7 |
| C5 | the absent-or-false full flag drives full-accept membership | 3 → 2 |
| C6 | wrong pin zeroes every rule (counts are pin-bound) | 0 rows |
| C7 | report path outside canonical write sets | true |
| C8 | **live controller instrument agrees with the re-implementation** | same 7 files, same 3 accepts, at instrument `b155313797c0` |

## Falsifier

Falsified if (a) F2b canonical/mirror bytes differ from
`b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c`; (b)
`reviews/F2b-review-worker-072-rev29.json` is not `revise` or its `revision_history` lacks the
01:10:13 accept (`7487f310d208…`) superseded at 01:14:51; (c) the live scan does not yield
`[worker-052, worker-071, worker-090]` or the reverted-072 control does not yield
`[worker-052, worker-071, worker-072, worker-090]`; (d) the lead's 7-file census does not
reproduce 0 accept / 7 revise; (e) the scan admits a
`target_id='schemas/af_scc_c0_vacuum.yaml#<pin>'` file.

## Does not claim

G-FORM pass/fail or any gate verdict; node completion or `validation_status=passed`; the REC-39
binding table (owned by `astra-life05-verify-gform-r3` / `astra-lead-audit`); which materiality
ruling on the named F2b findings is correct; bad faith by accepting reviewers (their own files
classify the named findings as non-blocking); any canonical artifact, review, schema, map or
ledger write.
