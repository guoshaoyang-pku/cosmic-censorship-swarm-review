# W031-F2A-PREFLIGHT-01 — adjudication of the F2a acceptance-pipeline PREFLIGHT blocker

Agent: `worker-031` (fleet instance 2026-09-12T00:42:38) · class **`AF-SCC-C2-VAC-GEN`** (node `F2a`,
gate `G-FORM`; cross-references `AF-WCC-VAC-GEN`) · Instrument: `check_f2a_preflight_031.py` ·
Report: `report.json` · Adjudication: `ADJUDICATION.json` · Checkpoint: `CHECKPOINT.json`

## Why this task

`reviews/F2a-rev12-069.json` recorded two blocking-for-clean-accept items on F2a at the FROZEN
rev28 bytes. One of them, **HF-069R-2**, is mechanical rather than semantic:

> `run_acceptance.py` PREFLIGHT FAIL — rebased fixtures stale (corpus base `1bb78ce9b357` vs
> current base `55d0a1ea9bda`); the two-stage acceptance criterion cannot be reproduced on the
> frozen bytes until the fixtures are rebased.

Nobody had run the bounded follow-up: **is the stale corpus bookkeeping-only, or does rebasing
expose a live content regression?** The answer decides whether the F2a acceptance criterion is
blocked by a re-generation step or by a real defect. This run answers that, in a throwaway
sandbox, without writing any canonical path.

## Method

`check_f2a_preflight_031.py` pins 16 inputs by sha256 (three schemas at both trees, the frozen
corpus and one fixture, FROZEN rev28, both tools, the rule spec, KEY_MANIFEST and the worker-06
auditor/manifest), rebuilds a minimal sandbox, and runs pre-registered steps:

| step | what | pre-registered |
|---|---|---|
| R0 | run the canonical runner on the lead's stale corpus | exit 3, `PREFLIGHT FAIL` |
| R1 | regenerate the corpus from the **current** frozen C0 base with the owner's unmodified generator | exit 0, base == live C0 |
| R2 | run the canonical two-stage acceptance pipeline on the regenerated corpus | `PASS` |
| R2b | localize any residual stage-2 rejection with the auditor's own rule output | — |
| D1 | regenerate + re-run again; compare corpus hashes, verdict, mutant block | identical |
| S1 | mutate F2a `conclusion.conclusion_type` to the sibling C0 type | pipeline fails |
| S2 | mutate F2a `extension_predicate.frozen_regularity` to `C0` | pipeline fails |
| S3 | restore frozen F2a bytes; baseline again | `PASS` |
| P1 | re-measure all 16 canonical pins | unchanged |

## Result — `F2A_BLOCKER_IS_BOOKKEEPING_ONLY_RESIDUAL_FAIL_IS_F1_R03`

Pins (stable across the whole run, `inputs_stable_during_run: true`): F1 `cce9c60146d6`,
F2a `5476a3f2c6bc`, F2b/C0 `55d0a1ea9bda`, FROZEN rev28 `2f358f6722d9`; tools
`c79d8ab8440a` (worker-06 auditor) and `000e09e46b2f` (structural gate) — byte-identical to the
tool revisions worker-080 registered independently.

1. **R0 reproduces the blocker**: the stale corpus makes the runner exit 3 with `PREFLIGHT FAIL`
   before it ever evaluates a schema.
2. **After R1 the F2a row is clean**: `af_scc_c2_vacuum.yaml` → structural `pass`, semantic
   `pass` (the auditor returns `accept`, `failed_rules: []`, `doc_sha256 5476a3f2c6bc`).
   The mutant union catches **31/31** (structural 30, semantic 11) and both controls pass.
   **So HF-069R-2 is a stale-corpus bookkeeping defect for F2a, not a content regression.**
3. **The whole pipeline still returns `FAIL` (exit 1)** — only because of the F1 row:
   `af_wcc_vacuum.yaml` passes structure and is rejected at stage 2 on exactly one rule,
   **R03: "binder `(q,t0)` absent from formal sentence"** (doc `cce9c60146d6`). That is not an
   F2a defect.
4. **Controls**: determinism holds (regenerated corpus byte-identical, same verdict and mutant
   block on re-run); both F2a mutations are caught (S1 fails both stages, S2 fails structure);
   restore returns F2a to the frozen bytes `5476a3f2c6bc`; all 16 canonical inputs unchanged.

Two expectations (R2, S3) were registered as `PASS` and measured `FAIL`; both deviations are
recorded in `report.json.deviations` and are fully explained by item 3 — they are not silently
reinterpreted.

## Prior reporting (honest crosswalk)

- **HF-069R-2** was first reported by worker-069 (`reviews/F2a-rev12-069.json`). This run adds
  the measurement of its consequence and bounds it to F2a.
- **The residual F1/R03 rejection is NOT claimed as new.** worker-080 diagnosed it independently
  at the same revision and the same tool hashes
  (`artifacts/worker-080/semct_rebase/r03_probe_report.json`, W080-SEMCT-REBASE-01/probeB):
  rev12 replaced the D5 binder `q` with the composite `(q,t0)` and spelled the pair out as
  `q in I+ and t0 in [0,T)`, so the literal composite token is absent; a notation-only rewrite
  clears R03 with all other checks unchanged, and a token mutation still fails — the rejection is
  lexical, not semantic. This run reproduces that outcome inside the acceptance-pipeline path.
- The stale corpus is stale in **two** ways: its recorded base is `1bb78ce9b357` (pre-rev27 C0)
  and it predates the current fixture manifest, which now yields 31 mutants (1 unparsed).

## Falsifier

Any pinned input moving during the run; the owner's generator or the canonical runner producing a
different verdict on a byte-identical sandbox replay; a mutated F2a the pipeline fails to catch
(which would void the sensitivity controls and make the F2a pass uninformative); or the F2a row
failing again after a byte-identical rebase.

## Authority

Worker measurement only. No gate verdict, no node status, no `validation_status`, and no edit to
any artifact under test. The sandbox lives under `tmp/w031_f2a_preflight/`; every canonical path
was re-hashed after the run and is unchanged. Replay:

```bash
python3 artifacts/worker-031/f2a_preflight/check_f2a_preflight_031.py
```
