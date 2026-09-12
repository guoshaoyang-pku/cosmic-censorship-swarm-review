# W056-FREEZE-QUIESCENCE-01 — hash-stability witness for the frozen research inputs

**Actor:** worker-056 (bounded execution worker; no inbox card existed for slot 056)
**Node bindings:** F0, F1, F2a, F2b, L0, L1, A0 · **Gates:** G-F0, G-FORM, G-LIT, G-AUDIT
**Classes:** AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN, AF-WCC-SCALAR-SPH
**Authority:** worker evidence only. No gate verdict, no node status, no `validation_status=passed`,
no edit to any canonical artifact. The controller and group leads own all gate moves.

## Why this task

The audit lead's live directive (`audit-direction-freeze-quiescence-20260912T0036`,
2026-09-12T00:35:58+08:00, pinned in `evidence/directive-20260912T0036.json`) requires writers to
stop on the frozen paths, FROZEN to publish the pins before reviewers are dispatched, and:

> "gate verdicts are invalid if any pinned input changes between the two verdicts"

and the audit lead's STATUS.md next-action 2 says a verdict counts "only if the hash is unchanged
when the second verdict lands". Neither rule is checkable without a measurement of hash stability
over a declared window on the canonical content **and** on every FROZEN-pinned input. No other
agent had produced that witness.

## Method (rule fixed before the run)

`run_quiescence_056.py` samples the sha256 of every verdict-bearing path every 20 s for 600 s:

- the 8 canonical content targets (F0 taxonomy + supplement, F1/F2a/F2b schemas, L0 theorem
  ledger, L1 citation ledger, A0 rubric);
- every path pinned in `FROZEN.json` `files` / `logical_artifacts`;
- the freeze indices `FROZEN.json` and `KEY_MANIFEST.json`.

48 verdict-bearing paths total. All 44 FROZEN pins are covered: 39 appear in the
`FROZEN.files` group and the other 5 are already canonical content targets (the four class
files plus the authoring taxonomy mirror). `research_map/research_map.json` is sampled and
reported but excluded from the verdict — it is the live bookkeeping channel.

**Verdict rule.** `QUIESCENT` iff every verdict-bearing path shows exactly one distinct sha256
across all samples in the window; `DRIFT` otherwise (naming the path and the sample instant).

A 6 s smoke run (`smoke_quiescence.json`) exercised the same rule before the main window.

## Result — QUIESCENT

| field | value |
|---|---|
| window | 2026-09-12T00:40:44+08:00 → 00:50:44+08:00 (600 s, 32 samples @ 20 s) |
| verdict | **QUIESCENT** — 0 drift targets |
| verdict-bearing paths | 48 (8 content + 39 FROZEN pins + 1 freeze index); 44/44 FROZEN pins covered |
| FROZEN index | revision 28, `frozen_at` 00:35:08, sha256 `2f358f6722d9…` — unchanged in window |
| FROZEN pin coherence at T0 | **coherent** — 0 mismatches, 0 missing |
| map (excluded) | moved normally: `3d45be5969ec` → `f06d40a8226a`, `updated_at` 00:37:18 → 00:50:08 |

Canonical hashes certified stable for the whole window (sha256 prefixes):

| target | sha256 (t0 = t1) | mtime |
|---|---|---|
| F0 `research_map/formulation_taxonomy.yaml` | `0abb9ed8a961` | 00:31:41 |
| F0 supplement `artifacts/formulation/formulation_taxonomy.yaml` | `d7419b4e8963` | 00:31:56 |
| F1 `schemas/af_wcc_vacuum.yaml` | `cce9c60146d6` | 00:32:02 |
| F2a `schemas/af_scc_c2_vacuum.yaml` | `5476a3f2c6bc` | 00:32:02 |
| F2b `schemas/af_scc_c0_vacuum.yaml` | `55d0a1ea9bda` | 00:32:02 |
| L0 `ledger/theorems.jsonl` | `a1674f094979` | 00:39:11 |
| L1 `ledger/citation_audit.csv` | `315c19145065` | 00:39:11 |
| A0 `evaluation_rubric.yaml` | `d748a9e3574e` | 2026-09-11T23:28:18 |

Note for L0 reviewers: the theorem ledger had already moved from the audit-lead STATUS pin
`3e3d35531421` to `a1674f094979` (62 rows, 151 521 bytes) before this window opened; the new
hash is the one this witness certifies and the one a binding verdict must cite.

## Artifacts

| path | sha256 | note |
|---|---|---|
| `quiescence-056.json` | `fd9ef2f2ca6d86375db442ca782eb4c5933823e56fdc5d1c6d6247391efb8c73` | full report, 32 samples, per-path timelines |
| `run_quiescence_056.py` | `4ee4d46de64faefbb0c88d0e8ce7447a5d464a3d5cf8f510ce6e6fe36d71981e` | stdlib-only runner, pinned rule |
| `smoke_quiescence.json` | `7661298a8948db4e52dc95dc8f351e3ebf8779f80d82563eab4f566d15c4c2a1` | 6 s pre-registration smoke run |
| `evidence/directive-20260912T0036.json` | `157be7f9ba976d146bcd5a39a0fef194467ff9365d6d14a3ac0cd76232fc1545` | the motivating audit directive |

Reproduce: `python3 artifacts/worker-056/freeze_quiescence/run_quiescence_056.py --window 600 --interval 20 --out quiescence-056.json`
(exit 0 = QUIESCENT, 3 = DRIFT, 2 = setup error). The runner resolves the swarm root from its own
path and writes only its `--out` file.

## Falsifier

A third party re-running this measurement over an overlapping window who observes a
verdict-bearing sha256 change that this report's samples missed (sampling granularity)
falsifies the QUIESCENT verdict; so does evidence that a listed path was written between the
final sample and the report's recorded hash. A `changed_in_window=true` path with no change
record falsifies the DRIFT timeline. Any sha256 here that does not reproduce by direct
`sha256sum` at the recorded mtime falsifies the measurement.

## Non-claims

- Worker evidence, not a gate verdict or node completion; `validation_status` stays unverified.
- `QUIESCENT` certifies byte-stability only, not content correctness — reviewers must still
  bind their verdicts to the hashes recorded here.
- The witness is time-bounded: it says nothing about writes after 00:50:44.
- The pin set is the one `FROZEN.json` rev28 carried at T0; pins added later are outside it.
- No ledger content was read as evidence and no canonical artifact was modified.

## Assumption ledger

- Identity of a path is its relative path under the swarm root; the runner `chdir`s to the root
  resolved from its own location, so it is invocation-directory independent.
- Clocks: sample instants are host wall-clock ISO strings; `mtime` values are filesystem times
  on the same host. Agents' self-reported `created_at` times are known to run ahead (CF-14) and
  are not used anywhere in this measurement.
