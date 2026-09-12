# W100-GLIT-UNIVERSE-REPL-01 — independent replication of the source-meta / "measured universe" census

- **worker**: worker-100 · **node**: L1 · **gate**: G-LIT
- **class binding**: `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH`
- **target under test**: `artifacts/worker-075/source_meta_census/source_meta_census_075.json`
  sha256 `b816178b94f703c8939a738f39418a8bb10f0bc1d3a66ea4cccaa3fbf1342947` (author worker-075)
- **role**: independent non-author replication; the target's implementation was **not** read or
  imported before this worker's implementation was written. No gate verdict, no node transition,
  no `validation_status=passed`.
- **authority limits**: read-only on every canonical path; writes only under
  `artifacts/worker-100/glit_universe_replication/`, `runtime/state/` and
  `comms/outbox/worker-100.jsonl`.

## Question

Do the census headline numbers — the candidate "measured universes" for the G-LIT gate text —
reproduce under a separately written implementation at the pinned bytes, and is **201 citations**
the size of any single canonical citation universe?

## Pins

All **43** input files recorded in the target (`input_files`) were re-hashed before (T0) and after
(T1) measurement: **43/43 byte-stable, 0 drift**. Key pins:

| file | sha256 |
|---|---|
| `ledger/theorems.jsonl` (L0, 62 rows) | `a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28` |
| `ledger/citation_audit.csv` (L1, 97 rows) | `315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9` |
| `ledger/class_coverage.csv` (388 rows) | `abbaee54a5a3c82b70a6b4e646edd29ff6d6daa3e2d82844296dfba8afc3a724` |
| target census JSON | `b816178b94f703c8939a738f39418a8bb10f0bc1d3a66ea4cccaa3fbf1342947` |

Per-file T0/T1 hashes: `raw/inputs_hashes_t0.json`, `raw/inputs_hashes_t1.json`.

## Result 1 — every headline universe reproduces exactly (9/9)

| quantity | this worker | target | match |
|---|---:|---:|---|
| source records, raw | 450 | 450 | ✅ |
| source records, unique id | **151** | **151** | ✅ |
| theorem records, raw | 297 | 297 | ✅ |
| theorem records, unique id | **77** | **77** | ✅ |
| source+theorem, raw | 747 | 747 | ✅ |
| source+theorem, unique id | **228** | **228** | ✅ |
| class-coverage rows | **388** | **388** | ✅ |
| citation links, raw | **726** | **726** | ✅ |
| records carrying any of the 5 axes | **0** | **0** | ✅ |

Per-file record-kind classification agrees with the target on **43/43 files** (source / theorem /
class-row / other counts). Unique citation pairs = **183**.

## Result 2 — the five source_meta axes are absent at every universe

`matter_model`, `cosmological_constant`, `dimension`, `symmetry`, `formulation` appear **0 times**
in all seven universes (raw and unique): 0/450 sources, 0/151 unique sources, 0/297 theorems,
0/77 unique theorems, 0/747, 0/228, 0/388 class rows. This holds under **both** depth readings of
the detector — primary `depth<=2` (keys of a depth-2 nested dict count) and strict `depth<=1`
(only top level + direct nested dict). Observed max axis-hit depth: none (`-1`, no hit anywhere).
Scope-like **proxies** exist and are near-misses, not axes: 285/297 raw theorem records and
77/77 unique theorem records carry `scope_caveats`; 388/388 class rows carry `scope_flags`.
Near-miss counts reproduce the target exactly.

## Result 3 — per-class split: reproduced under the author's token rule (5/5)

The per-class counts over the 450 raw source records are **rule-sensitive**. Reading A (this
worker's primary: split on all delimiters, substring-match) and reading B (split each class field
on `;` only, require exact whole-token equality) give:

| class | reading A | reading B | target | B match |
|---|---:|---:|---:|---|
| AF-SCC-C0-VAC-GEN | 76 | **67** | 67 | ✅ |
| AF-SCC-C2-VAC-GEN | 67 | **58** | 58 | ✅ |
| AF-WCC-SCALAR-SPH | 24 | **18** | 18 | ✅ |
| AF-WCC-VAC-GEN | 26 | **26** | 26 | ✅ |
| no frozen class token | 316 | **337** | 337 | ✅ |

The delta is confined to **qualified/negated tokens**: `AF-SCC-C0-VAC-GEN (definitional support)`,
`AF-SCC-C0-VAC-GEN (scope-caveated)`, `AF-SCC-C2-VAC-GEN (supporting)`,
`AF-WCC-SCALAR-SPH (background)`, `bears on AF-SCC-C0-VAC-GEN / AF-SCC-C2-VAC-GEN ...`, and
`not AF-SCC-C2-VAC-GEN)`. Reading B drops negated mentions (correct) but also drops qualified
assignments that reading A credits. The target's recorded numbers are exactly reading B; no
headline number depends on the choice. This is recorded as finding **F-W100-REPL-01** (scope
documentation, not a numerical error).

## Result 4 — "201 citations" is not a measured universe (confirmed)

- Named decomposition A: `registry.jsonl` 97 + `citation_audit.csv` 97 + `w07-sources.jsonl` 7 =
  **201**, but only **104** distinct record ids (registry and audit are the same 97 sources) —
  reproduces the target exactly.
- Named decomposition B: `registry.jsonl` 97 + `theorems.jsonl` 62 + `unresolved.jsonl` 12 +
  `w07-theorems.jsonl` 15 + `citation_audit_wcc_flash-08.jsonl` 15 = **201**, only **189**
  distinct ids — reproduces the target exactly.
- **No** canonical single file has 201 rows.
- Closest measured universe to 201 is **183** unique `(theorem, source)` pairs — **18 away**.
  (A bounded exhaustive search over canonical row counts finds 25 arithmetic subsets ≤4 parts that
  sum to 201; every one mixes surfaces and collapses once record ids are deduplicated, which is the
  target's point: arithmetic sums are not universes.)

**Recommended gate-text denominators** (all hash-bound at the pins above): 151 unique sources /
77 unique theorems / 228 union / 388 class rows / 726 raw links / 183 unique links. The figure
"201 citations" should not be cited as a denominator.

## Controls

13/13 pass (`replication_report.json:controls`): flat axis, nested depth-1 axis, depth-3 no-fire,
depth-2 fire (primary) / no-fire (strict), near-miss-only no-fire, empty, all-five flat, duplicate
source key raw/unique, duplicate link raw/unique, pin-drift detection. A deterministic re-run
(`--verify`) reproduces `measurement_digest e646b1a2fb19b0d1a969775d9e0154637c3aca7fd1279a8786c1c1da1388132c`
byte-for-byte.

## Falsifier

Re-run `python3 replicate_census_100.py` (then `--verify`) at the same tree state. Falsified if:
(a) any of the 43 inputs re-hashes to a value other than its recorded sha256 at T0 or T1;
(b) any headline, per-class reading-B, or record-kind value differs on re-run; (c) any control
flips; or (d) a record counted as carrying no axis is shown to carry one of the five literal axis
keys within dict depth ≤ 2 (or ≤ 1).

## Verdict

`PARTIAL` under the pre-registered decision rule — because the primary per-class reading (A)
differs — with the substantive result that **all nine headline universes, the 0-axis result, the
record-kind classification and the "201 is not a universe" reconciliation reproduce exactly**,
and the per-class numbers reproduce exactly under the target's own token rule (B). No
contradiction with the target was found.

## Non-claims

Not a mathematics or physics claim; not a gate verdict; not a node status; not a statement that
the literature ledger is correct — only that the census numbers above are reproducible at these
bytes. `worker-100` is not an author of the target artifact, the ledger, the registry or the
protocol.
