# worker-029 review — W029-LIVE-HF2902-04

**One bounded class-bound task, then exit.** Classes `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`,
`AF-SCC-C0-VAC-GEN`; node `F1,F2a,F2b`; gate `G-FORM`. Read-only: no canonical schema, ledger,
taxonomy, gate or map record was edited.

## Verdict

**`revise` (2.0/5) — 5/6 checks PASS, exactly one hard FAIL: `C2-HF-29-02-live-ledger`.**

HF-29-02 survives the CF-19 ledger rewrite. At the live bytes, **11 of 15 `l1_ledger_refs` rows**
assert `citation_status: verified_by_L1` while every row of the live `ledger/theorems.jsonl`
records `verification_status: abstract-read` and `review_status: not_independently_reviewed`
(61 abstract-read + 1 unverified, **0 independently reviewed**). The token `verified_by_L1` appears
nowhere in any of the three ledger generations.

## Pinned inputs (measured at snapshot, re-measured matching at emission)

| input | sha256 (first 12) | vs rev12 pin |
|---|---|---|
| `schemas/af_wcc_vacuum.yaml` (F1) | `cce9c60146d6` | unchanged |
| `schemas/af_scc_c2_vacuum.yaml` (F2a) | `5476a3f2c6bc` | unchanged |
| `schemas/af_scc_c0_vacuum.yaml` (F2b) | `55d0a1ea9bda` | unchanged |
| `research_map/formulation_taxonomy.yaml` (F0 canonical) | `0abb9ed8a961` | unchanged |
| `ledger/theorems.jsonl` (live, CF-19 write 00:35:19) | `a1674f094979` | **moved** (rev12 pin `3e3d35531421`) |
| `artifacts/literature/archive/theorems.rev3-handpatch-20260912T003026.jsonl` | `3e3d35531421` | = rev12 ledger pin |
| `artifacts/literature/archive/theorems.pre-rev3-20260912T003026.jsonl` | `ce42d205e761` | pre-rev3 generation |

The rev12 closure snapshot
(`artifacts/worker-029/rev12_closure_verify/ledger_theorems_snapshot.jsonl`) hashes to
`3e3d35531421…` and is byte-equal to the rev3 archive copy — verified, not assumed
(`snapshot_manifest.json.rev12_ledger_snapshot_crosscheck`).

Because all four formulation inputs are byte-identical to the rev12 pins, the only canonical input
that moved is the ledger, and only check `C2` of `W029-REV12-CLOSURE-03` consumed the ledger. This
task therefore re-runs the C2 honesty logic (unchanged rule) on the live ledger instead of
re-deriving the closed findings HF-29-01 / HF-29-03.

## Checks

| check | severity | result |
|---|---|---|
| `C0-snapshot-integrity-live-drift` | hard | PASS — all six snapshots match declared hashes; all seven canonical paths re-hash matching at run time |
| `C1-pin-binding` | info | PASS — three class schemas + taxonomy unchanged from rev12 pins; no duplicate YAML mapping keys; ledger moved |
| `C2-HF-29-02-live-ledger` | hard | **FAIL** — 11 over-claims against the live ledger (list below) |
| `C3-citation-evidence-invariance` | hard | PASS — the 11 rows are `abstract-read` in all three generations; no generation records independent review |
| `C4-ledger-vocabulary` | info | PASS — vocabulary recorded; `verified_by_L1` is not a ledger value |
| `C5-comparator-controls` | hard | PASS — 5/5 controls (exact match, conservative downgrade, over-claim mutation, missing row, no claim) |

### The 11 over-claimed rows

| class | ids |
|---|---|
| F1 | `T-204`, `T-208` |
| F2a | `T-401`, `T-402`, `T-514`, `T-520` |
| F2b | `D-002`, `T-301`, `T-302`, `T-515`, `T-528` |

The 4 remaining refs are honest: F1 `D-001` asserts no status; F1 `T-209`, F2a `T-305`, F2b `T-305`
assert `unresolved`, a conservative downgrade on an abstract-read row.

## What the ledger generations show

| generation | rows | verification_status | review_status | independently reviewed |
|---|---:|---|---|---:|
| `pre_rev3` `ce42d205e761` | 62 | 61 abstract-read, 1 unverified | field absent | 0 |
| `rev3` `3e3d35531421` | 62 | 61 abstract-read, 1 unverified | 62 not_independently_reviewed | 0 |
| `live` `a1674f094979` | 62 | 61 abstract-read, 1 unverified | 62 not_independently_reviewed | 0 |

The CF-19 rewrite neither repaired nor altered the citation-evidence level of any cited row. The
pre-rev3 generation simply lacks the `review_status` field; the rev3 → live move preserved all 62
row statuses relevant here, so the contradiction is a property of every generation, not an artifact
of the latest unannounced write.

## Fix (owner: astra-lead-formulation / astra-lead-literature)

Either (i) set the 11 `citation_status` values to the ledger vocabulary (`abstract-read`), consistent
with the same schemas' own `citation_status: unverified` footer; or (ii) record genuine independent
L1 verification in `ledger/theorems.jsonl` and re-pin the ledger hash. `ledger/citation_audit.csv`
verifies citation **metadata** (resolver/primary-page fetch), which cannot license
`verified_by_L1`. No schema text change is needed for the data-class criterion.

## Reproduction

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-029/live_hf2902/snapshot_live_hf2902.py   # optional: re-snapshot (moves the pin)
python3 artifacts/worker-029/live_hf2902/check_live_hf2902.py     # reads snapshots only
# report_core.json is byte-stable across reruns (verified twice:
# 1668f14b3ea5398942a96283dbc446c16f82c9be0f0b21d7a29651170ac70167)
```

Artifact hashes: checker `90f5b94adf3a`, snapshot script `5b845bc78da2`, manifest `a23c8a22d346`,
report.json `266af59aaa5e`, evidence.json `9c02a00b6184`, report_core.json `1668f14b3ea5`.

## Falsifier

Re-run the checker on the same snapshot bytes: the HF-29-02 re-binding is falsified if `C2` reports
PASS (all 11 cited rows resolve to a live ledger row recording independent verification, or the
`citation_status` values were revised to the ledger vocabulary), or if `C5` fails. If a canonical
path no longer matches its snapshot hash, the check is superseded, not falsified.

## Authority note

Worker evidence only. This review cannot set a gate verdict, a node status, or a
`validation_status`; it is not a theorem and makes no claim about the correctness of the underlying
censorship mathematics. Checkpoint: `runtime/state/w029_live_hf2902_checkpoint.json`.
