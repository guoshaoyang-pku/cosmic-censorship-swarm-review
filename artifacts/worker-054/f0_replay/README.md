# W054-F0-REPLAY-01 — out-of-binding replay of the frozen F0/G-F0 class-leakage corpus

- **Actor:** worker-054 (bounded execution worker)
- **Node / gate / class ids:** F0 / G-F0 / `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH`
- **Status:** worker report only. No theorem, no gate verdict, no node transition, no
  `validation_status: passed`. Evidence for the formulation and audit leads.
- **Created:** 2026-09-12 (run window ~00:20 local; machine-pinned hashes below)

## Question

The frozen 36-case corpus (`schemas/taxonomy_cases.jsonl`) declares
`binding_status: bound_taxonomy_sha_66bf917bd368` (rev 3). The canonical taxonomy has since
been republished. The corpus's own next-falsifier #1 is: *re-run `check_taxonomy_cases.py`
against the next taxonomy hash; any case whose axis vector no longer resolves uniquely
falsifies the binding.* This task performs exactly that replay and cross-checks the
checker's self-claims with an independent recomputation.

## Method

1. Measure sha256 of four live inputs; copy byte-identical snapshots into `inputs/`.
2. Run the corpus's own checker (`artifacts/flash-02/check_taxonomy_cases.py`) against the
   snapshot bytes → `checker_report.json` + `logs/`.
3. Re-measure the live inputs after the run; report any mid-run move (drift).
4. Independently recompute — with local code only — the report's self-claims: corpus
   counts, per-class coverage, open-case set, pairwise class disjointness, the four frozen
   class ids, and the corpus meta binding vs the current canonical hash.
5. `report.json` records every check with its pass/fail and detail.

## Result

| item | value |
|---|---|
| checker exit / verdict | `0` / **PASS**, `errors: []` |
| mutation controls | **10/10 detected** |
| independent consistency checks | **12/12 pass** (`report.json.checks`) |
| corpus | 16 positive / 20 negative cases (unchanged) |
| open cases | 9, unchanged (`N01 N02 N04 N09 N10 N11 N14 N15 N16`) |
| pairwise disjointness | 6/6 class pairs, differing-axis sets match recomputation |
| input drift during run | none (`C11`) |
| binding | **out-of-binding replay**: corpus bound to `565a6e505188` (rev 3), replayed at `276009f4f63d` (rev 4, `draft_unverified`) |
| corpus resolves at current bytes | **yes** — no case's axis vector stopped resolving |

**Reading:** the rev-3 → rev-4 republication did not disturb the class-axis resolution of
the frozen corpus, so the corpus's own falsifier #1 did *not* fire at the pinned bytes.
This does **not** make the corpus in-binding: the corpus meta record still declares
`bound_taxonomy_sha_66bf917bd368`, and only the formulation lead may re-pin it.

### Hash pins (machine-measured, this run)

| artifact | sha256 |
|---|---|
| `research_map/formulation_taxonomy.yaml` (snapshot, rev 4) | `276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc` |
| `schemas/taxonomy_cases.jsonl` | `b9699119bbabf01489f851b6dfa0c05a56f457c031e4e69992b8f57c30c489a2` |
| `artifacts/flash-02/leak_rule_catalog.json` | `215f6e228250827a3f80a6155fd9a71c0ed0548e347e1d7ec3332275f1fb6f17` |
| `artifacts/flash-02/check_taxonomy_cases.py` | `c1519a972e01539d4bb9e7f79103660944c8d09cc451550b74116cf03bc88040` |
| `report.json` | `ea543e87b14bcf75a296f62c779c068a7f7ccaca8969567f7a26bf80e5042ef4` |
| `checker_report.json` | `6557f2ffe0181c032580833dfc357fe30123fad1c959ccad280f9791360c459c` |
| `replay.py` | `e08c5bb71b69fb8bea4d6551ad004bef5e5addfc400322fcc2e9f77213057875` |

The canonical file is being actively republished (this worker measured revision-3
`0fcc6a1928fd` ≈00:18 and revision-4 `276009f4f63d` at run start). Only the snapshot hash
is pinned by this report.

## What this does not claim

- No theorem, counterexample, numerical result, or physics claim.
- Passing fixtures is shape/separation evidence, not mathematical correctness, non-vacuity,
  or truth.
- The checker is the corpus author's tool; this replay re-runs it byte-identically and
  cross-checks its self-claims, but does not re-implement its leak rules.
- The 9 open cases (new class / split required) are the formulation lead's adjudication.
- No gate verdict, node status, or artifact `validation_status` is moved by this artifact.

## Falsifier

Re-run `python3 artifacts/worker-054/f0_replay/replay.py` in an unchanged tree. The report
is falsified if (a) the checker exits non-zero or returns a non-PASS verdict at the same
re-measured taxonomy sha256, (b) any live input hash differs from the pins above, (c) the
independent recount of counts/coverage/open-set/disjointness disagrees with the checker
report, or (d) the corpus-wide resolution result changes while every pinned hash is
unchanged.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-054/f0_replay/replay.py     # exit 0 iff checker PASS + 12/12 checks + no drift
```
