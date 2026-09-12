# W084-POSTREV-COVERAGE-01 — review note

Worker: `worker-084` · node targets: F0, F1, F2a, F2b · classes: `AF-WCC-VAC-GEN`,
`AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN` (+ declared taxonomy binding all frozen classes)
Gate routing: G-F0 / G-FORM / G-AUDIT (coverage criterion) · authority: measurement only.

## What was asked

One bounded, class-bound question: **after the `astra-life03-close-findings` revision, how many
independent ACCEPT verdicts survive at the measured canonical hashes, in (A) the controller's
`reviews/*.json` scan and (B) the accepted event stream?**

## What happened while measuring

The first instrument run was aborted before emit: it snapshotted the pre-revision corpus
(00:30:25) and then read the controller's `measured_hashes`, which already returned the
post-revision bytes — the revision landed at 00:31:41–00:33:03 inside the snapshot window.
Rather than emit a straddling report, the instrument was re-pinned to the post-revision
state and the pre-revision run was discarded. The measured migration is now the report's
`measured_migration` field.

## Findings

1. **All four class-binding targets were revised** (close-findings):

   | target | class | superseded | measured now |
   |---|---|---|---|
   | F0 | (taxonomy) | `276009f4f63d` | `0abb9ed8a961` |
   | F1 | AF-WCC-VAC-GEN | `9a8bd4c96800` | `cce9c60146d6` |
   | F2a | AF-SCC-C2-VAC-GEN | `b6123750b37d` | `5476a3f2c6bc` |
   | F2b | AF-SCC-C0-VAC-GEN | `1bb78ce9b357` | `55d0a1ea9bda` |

2. **FROZEN is coherent at the new bytes, across two regenerations.** Rev 27
   (`frozen_at = 00:32:59`) pinned all four measured hashes with a non-future stamp; while this
   report was being written the manifest was regenerated again to rev 28 (`frozen_at = 00:35:08`,
   `sha256 2f358f6722d9`), which **still** pins all four measured canonical hashes and is still
   non-future-dated. The report pins rev 28. The round-3 defect D1 (future-dated freeze stamp,
   which recurred across rev24→rev25) is fixed at both revisions. This is the one clean positive,
   and it survived a regeneration — the failure mode in round 3 was that regeneration
   *re-introduced* the defect.

3. **Coverage at the measured hashes is 0/4 in both channels — 11 prior verdicts were
   invalidated by the revision.** Every hash-bound accept for these targets cites a superseded
   hash, so under the controller's own rule ("verdicts bound to superseded hashes are advisory
   only") G-F0/G-FORM/G-AUDIT have no countable accept at any of the four current hashes:
   F0 lost 2, F1 lost 1, F2a lost 3, F2b lost 5. **This is a re-verification debt of 11 verdicts
   across all four targets, not a content finding.** The 02:00 `astra-life03-verify-gform` /
   `verify-gf0` passes should not be read as content failures until this debt is re-run.

4. **Instrument undercount, and why the obvious fix is wrong.** In the superseded corpus,
   7 hash-bound ACCEPT events are invisible to the `reviews/*.json` scan. Only **1** of them is
   evidence-anchored: worker-040's F0 accept (review_path exists, `review_sha256` matches). The
   other **6** (`worker-026` F1, `worker-050`/`worker-098` F2a, `deepseek-flash-07`/`worker-060`/
   `worker-096` F2b) carry **no `review_path` and no hash** — they are not countable evidence
   under protocol rule 2. So "just count the event stream" would promote unanchored events;
   the correct remediation is events-binding **plus** an evidence-anchor requirement, or
   requiring materialization of `reviews/<name>.json`. Both options are costed in
   `report.remediation`.

5. **Invisibility mechanisms are three distinct code paths**, not one: `R7_channel_only`
   (no review file at all), `R2_target_encoding_unmapped` (target recorded as `path#hash` or an
   unknown token, so the scanner's alias table drops it), and `R1_file_exists_but_scan_yields_no_accept`
   (`deepseek-flash-07` rewrote its F2b file from accept to revise at 00:26:33, after the
   00:24:40 audit had already counted it — corpus churn, not a scanner bug).

6. **The map's declared node hashes are stale on all four targets** (`declared != measured`,
   controller-recorded at 00:33:16). Expected immediately after a revision; flagged so it is
   repaired by the next lifecycle pass rather than mistaken for drift.

## Checks

10 machine checks, 9 pass. The single FAIL is `C1.7b_all_invisible_accepts_are_evidence_anchored`
(6 unanchored accept events) and it is a genuine finding, not instrument error. `C1.7a` confirms
the one anchored invisible accept is valid. No drift during the check: the four class targets were
byte-stable across the whole window (00:32:02 → 00:35:19+); only `FROZEN.json` was regenerated
(rev27 → rev28), and it remained coherent at both revisions.

## Limitations / what this does not say

- This makes **no claim about cosmic censorship** and no claim about the *content* of the
  revised schemas. It does not accept or reject any revision; it counts and classifies verdict
  coverage.
- It does not adjudicate which channel is binding for the gate criterion — that is the
  controller/audit-lead's call, and the report states the measured consequence of each option.
- `R` classifications are heuristics over the review corpus; each is backed by named candidate
  files in `report.reconciliation[target].invisible_accepts_at_superseded`.
- The `dir_accepts`/`accepts_at` counts inherit the controller's own alias and pin rules by
  import (`astra_lifecycle`), so a bug in those rules is a bug in both channels equally.

## Falsifier (short form)

Re-run `verify_coverage_recon.py` at the same hashes. Falsified if any pass re-runs false; if
coverage at the measured hashes reaches ≥2 distinct accepts (debt no longer outstanding); if a
`reviews/*.json` record is materialized for an "invisible" reviewer+target (invisibility retired
by evidence); or if FROZEN `frozen_at` becomes future-dated again. Hash drift voids the per-target
counts, it does not falsify the instrument claim.
