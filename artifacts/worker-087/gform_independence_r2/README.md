# W087-GFORM-INDEP-05 — G-FORM accept-coverage re-measurement at the rev-13 / FROZEN rev-29 pins

Worker `worker-087` (instance `worker-087-20260912T005851-968807`), bounded execution worker:
one class-bound task, then exit. No assignment card exists in `comms/inbox/worker-087.jsonl`;
the task was self-assigned from the live G-FORM coverage gap (`astra-life05-verify-gform-r3`
is the standing gate card) before measurement, with pre-registered criteria and fail-closed
controls. Read-only against every canonical input; all writes are under this directory.

- **Nodes / gate:** F1, F2a, F2b / `G-FORM`
- **Classes:** `AF-WCC-VAC-GEN` (F1), `AF-SCC-C2-VAC-GEN` (F2a), `AF-SCC-C0-VAC-GEN` (F2b)
- **Lineage:** successor of `W087-GFORM-INDEP-04`
  (`artifacts/worker-087/gform_independence/report.json#fe968c1c282e`), which measured the
  pre-repair state (`REPINNED_ANNOUNCEMENT_PENDING`, rev-13 coverage F1 0 / F2a 2 / F2b 1).
- **Instrument:** `audit_gform_independence.py` — byte-identical to the INDEP-04 instrument
  (`f970bc8918c156dffd0bda360eb41df495e78696e6b6ce07bd19ed31f26110f0`), not modified.
- **Corpus snapshot:** `snapshot/MANIFEST.json` — 636 files, manifest digest
  `58db6f6ffb7369fc6c093f6df1ba63f106fd94dc2be40612c30704f77f89bc56`, taken
  `2026-09-12T01:02:11+08:00`; every snapshot pin matched the live canonical byte at snapshot close.
- **Report:** `snapshot_run3/report.json`; verdict digest
  `8c118404480640296a30d5fa9a3ad9a07cdc06673f4bc557fd805d844913bf45`, identical across
  three runs against the snapshot; controls 8/8.
- **Adjudication summary:** `summary.json`
- **Checkpoint:** `CHECKPOINT.json` (copy at `runtime/state/worker-087_checkpoint_gform_indep_05.json`)
- **Verdict:** `GATE_CRITERION_NOT_MET_AT_REV13` — F1 and F2a each meet the
  two-independent-full-schema-accepts criterion at the measured pins; **F2b is the sole
  remaining gap and needs one more effective independent full-schema accept at
  `schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe`**.

## Question

At the post-repair canonical bytes (schemas rev 13, FROZEN rev 29), does the G-FORM criterion
*"two independent full-schema accepts per schema"* hold for each of F1 / F2a / F2b after
reviewer-identity, verdict-text and evidence-channel dedup — and is the freeze itself intact
and owner-announced?

## Method

1. **Snapshot instead of live reads (forced by measurement).** Three back-to-back runs of the
   frozen instrument against the live tree at 01:00–01:01 produced three *different* verdict
   digests (`c89299fb6e30`, `c5d66e2bc050`, `74513708ca3c`) because the swarm appends reviews
   several times per minute. A coverage measurement taken against a moving corpus is not
   reproducible, so `build_snapshot.py` copies every input the instrument reads
   (`research_map/events.jsonl`, `comms/outbox/**`, `reviews/**`, `schemas/**`,
   `artifacts/formulation/**`, `research_map/formulation_taxonomy.yaml`) into `snapshot/`,
   records a sha256 for every file, and emits the manifest digest. The three live attempts are
   kept under `moving_target_attempts/` as the evidence for this decision.
2. **Frozen instrument, unchanged.** `audit_gform_independence.py` was copied byte-identically
   from INDEP-04; it re-measures pins at run start and end, harvests every record carrying a
   verdict (events + outbox + `reviews/*.json`), dedups by `event_id`, binds targets strictly
   (an F0 review listing all four class ids is not an F1/F2a/F2b review), binds hashes by the
   *primary* declared hash (prose mentions of another revision do not bind), keeps one verdict
   per reviewer, separates full-schema from advisory accepts, and clusters accepts by reviewer
   identity, findings-text character-5-gram Jaccard ≥ 0.6, or a shared non-target evidence
   channel. Cluster count = effective independent accepts.
3. **Three runs on the snapshot** (`snapshot_run1..3`): identical digest
   `8c1184044806…`, internal determinism `true`, controls 8/8.
4. **Derived adjudication** (`summarize_w087_indep_05.py`) reads only the frozen report and the
   snapshot manifest; no live input.

## Result

### Freeze state — `REPINNED_AND_ANNOUNCED`

The three canonical schemas moved after the rev-28 freeze and were re-pinned in **FROZEN
revision 29** (`artifacts/formulation/FROZEN.json#815e08079aef`, frozen_at
`2026-09-12T00:57:26+08:00`): F1 `cce9c60146d6 → d9cebb9404b2`, F2a `5476a3f2c6bc →
e9a27996dfd3`, F2b `55d0a1ea9bda → b2ab6acb2bbe`, all declared rev 13, `revised_at
00:53:20`. Manifest-vs-disk mismatches: 0 canonical, 0 authoring; mirrors aligned; every
schema's `f0_binding.consistency_evidence_sha256` refreshed to the measured
`artifacts/formulation/evidence/taxonomy_consistency.json#9e335e9ba1bf`. Each new canonical
hash is announced in the accepted stream by an owner artifact event
(`lead-form-20260912T005743-00/-01/-02`, `astra-lead-formulation`, 00:57:43): **3/3
announcements present**. The INDEP-04 announcement blocker is therefore closed.

### Coverage at the measured pins (snapshot 01:02:11)

| node | class | path | sha256 | bound records / reviewers | verdicts | effective accept clusters | criterion |
|---|---|---|---|---|---|---|---|
| F1 | `AF-WCC-VAC-GEN` | `schemas/af_wcc_vacuum.yaml` | `d9cebb9404b2` | 27 / 21 | accept 7, inconclusive 1, revise 13 | **5** (`worker-052`, `worker-072`, `worker-075`, `worker-080`, `worker-085`, `worker-089`) | **met** |
| F2a | `AF-SCC-C2-VAC-GEN` | `schemas/af_scc_c2_vacuum.yaml` | `e9a27996dfd3` | 17 / 11 | accept 3, inconclusive 1, revise 7 | **3** (`worker-017`, `worker-034`, `worker-072`) | **met** |
| F2b | `AF-SCC-C0-VAC-GEN` | `schemas/af_scc_c0_vacuum.yaml` | `b2ab6acb2bbe` | 17 / 11 | accept 1, inconclusive 1, revise 9 | **1** (`worker-061`) | **not met** |

- The single F2b accept is `w061-varstrength-20260912T0055-review-f2b` (worker-061, score 4.0,
  00:54:27, direct schema target). No advisory accepts exist for F2b, so no second cluster can
  be formed from the bound corpus.
- **Gate level: the criterion is not met.** F1 and F2a are each satisfied at the measured
  pins; F2b is the only gap. Rev-28-bound verdicts (`F1 1`, `F2a 1`, `F2b 2` clusters) remain
  void because they bind superseded bytes, and a review of a sandbox copy or of a derived
  document does not count.

### What would close the remaining gap

One more **full-schema** review verdict `accept` bound by its *primary* hash to
`schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe`, from a reviewer other than `worker-061`, whose
findings text and evidence channels form an independent cluster under the declared rule.

## What this artifact does not claim

Worker evidence only: it issues no review verdict on any schema, does not set
`status=done`, `validation_status=passed`, or any gate verdict — only the controller and group
leads may do that, on artifact + review evidence. Fluent text here is not a gate pass.

## Falsifiers

1. **F2b gap:** a new full-schema accept bound to `schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe`
   from a non-`worker-061` reviewer in a separate independence cluster falsifies
   `remaining_gap_classes = [F2b]`.
2. **Pins:** the measurement is void if any of the three canonical hashes moves, if
   `FROZEN.json` is not revision 29 / `815e08079aef`, or if an owner announcement for a
   measured hash is absent from the accepted stream.
3. **Criterion-met findings:** falsified if two counted clusters are shown to share an
   instrument, review document or verdict text, or if a hash-bound verdict excluded by the
   harvest is shown to name the schema directly at the reported revision.
4. **Reproducibility:** re-run `audit_gform_independence.py --root snapshot --out <dir>` and
   compare `verdict_digest_sha256`; a different digest falsifies `summary.json`.

## Reproduce

```bash
cd artifacts/worker-087/gform_independence_r2
python3 audit_gform_independence.py --root "$PWD/snapshot" --out /tmp/w087_r --root "$PWD/snapshot"
python3 summarize_w087_indep_05.py --dir "$PWD"
```

The frozen instrument exits `0` when the criterion is met, `3` on a coverage gap / transition
(this run: 3), `2` on a moving target, `4` on a control failure.

## Files

| file | role | sha256 sidecar |
|---|---|---|
| `audit_gform_independence.py` | frozen INDEP-04 instrument | `.sha256` |
| `build_snapshot.py` | hash-pinned corpus snapshot builder | `.sha256` |
| `summarize_w087_indep_05.py` | derives `summary.json` from frozen inputs | `.sha256` |
| `snapshot/MANIFEST.json` | 636-file snapshot manifest + digest | `.sha256` |
| `snapshot_run3/report.json` | instrument report (digest `8c1184044806…`) | `.sha256` |
| `snapshot_run1/`, `snapshot_run2/` | reproducibility runs (identical digest) | — |
| `moving_target_attempts/` | three live-tree runs with three different digests | — |
| `summary.json` | per-class adjudication + falsifiers | `.sha256` |
| `CHECKPOINT.json` | worker checkpoint (mirrored to `runtime/state/`) | `.sha256` |
| `events_emitted.json` | outbox event ids, hashes, pins | `.sha256` |
