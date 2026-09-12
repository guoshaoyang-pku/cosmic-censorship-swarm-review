# W037-REV13-COVERAGE-REBIND-01 — L1 class-coverage evidence rebinding census

- **Actor**: worker-037 (bounded execution worker; no inbox card existed for worker-037, task
  self-selected from the live post-rev13 critical path)
- **Node / gate**: L1 / G-LIT
- **Class binding**: `AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN` (the L1 node's declared
  class set; the coverage matrix additionally carries `AF-WCC-SCALAR-SPH`, reported here as an
  out-of-scope observation, not as a bound class)
- **Live pins this census binds to** (measured at start and end of the run; `inputs_stable: true`):
  F1 `d9cebb9404b2`, F2a `e9a27996dfd3`, F2b `b2ab6acb2bbe`, FROZEN rev29 `815e08079aef`,
  ledger `a1674f094979`, matrix `abbaee54a5a3`, citation audit `315c19145065`
- **Authority**: worker-level measurement evidence only. No gate verdict, no node status, no
  `validation_status` promotion, no canonical-path write, no class re-adjudication.
- **Reproduce**: `python3 artifacts/worker-037/rev13_coverage_rebind/rebind_census.py`
  (re-runs the three flash-10 instruments read-only with redirected output; writes only under
  this directory and `runtime/state/`).

## Findings

### F1 — 15 gate-input pins in the L1 coverage family are superseded (17/48 declared pins overall)

The census walks every `*.json` in `artifacts/flash-10/l1_class_coverage/` and classifies each
declared `path -> sha256` against the live bytes. 48 declared pins: **31 ALIGNED, 17 SUPERSEDED,
0 MISSING**. The superseded set includes 15 pins on gate-bearing inputs:

| declared input | declared | live | declaring artifacts |
|---|---|---|---|
| `schemas/af_wcc_vacuum.yaml` | `16128b62fe08` / `9a8bd4c96800` / `cce9c60146d6` | `d9cebb9404b2` | wcc audit rev9/rev11/rev12 + rev12 reaudit |
| `schemas/af_scc_c2_vacuum.yaml` | `8dae50da1ab5` / `5476a3f2c6bc` | `e9a27996dfd3` | c2 audit rev3 + rev12 reaudit/checkpoint |
| `ledger/theorems.jsonl` | `ce42d205e761` / `3e3d35531421` | `a1674f094979` | coverage_summary + wcc/c2 audit outputs |

No C0 (`AF-SCC-C0-VAC-GEN`) class-conformance instrument exists in the family, so that class has
no coverage-conformance evidence to rebind at any hash — a per-class gap, not a drift.

### F2 — The conformance *readings* survive rev13; only the binding is stale

Re-running the unmodified instruments at the live rev13 bytes gives the same readings as their
rev12 baselines:

| instrument | rev13 reading | rev12 baseline | substantive field differences |
|---|---|---|---|
| `wcc_class_conformance_audit.py` (`9ea59332553b`) | 11 bound, 0 discharging, `open_problem` | 11 / 0 / `open_problem` | **none** (only `sha256`, `revision`, tree-observation) |
| `c2_class_conformance_audit.py` (`cebbf53a05d2`) | 10 bound, 0 discharging, `open_problem` | 10 / 0 / `open_problem` | **none** (only `sha256`, pin-observation) |

So the correct repair for F1 is a **re-pin, not re-adjudication**: the evidence content is
unchanged across rev12→rev13, but every existing output declares a superseded hash and may not be
cited at the live bytes.

### F3 — The published coverage matrix does **not** reproduce at the live ledger

Re-running the unmodified coverage builder (`901ffa6bbc39`) on the live inputs produces a matrix
whose sha256 differs from the published one (`855a2852bb73` vs live `abbaee54a5a3`) and whose
per-class counts collapse on exactly the `covered` cells:

| class | published `covered/partial/none` | rebuilt at live ledger |
|---|---|---|
| AF-WCC-VAC-GEN | **7** / 15 / 70 | **0** / 22 / 70 |
| AF-SCC-C2-VAC-GEN | **3** / 17 / 72 | **0** / 20 / 72 |
| AF-SCC-C0-VAC-GEN | **3** / 25 / 64 | **0** / 28 / 64 |
| AF-WCC-SCALAR-SPH | **8** / 6 / 78 | **0** / 14 / 78 |

21 of 388 rows change, in columns `coverage`, `evidence_basis`, `notes` (21 each), and for 2 rows
also the displayed strongest-binding text (`exact_theorem`, `theorem_locator`, `genericity`,
`regularity`, `assumptions`, `scope_flags`).

### F4 — Cause, isolated by control: the live ledger has no `status` key

The builder's coverage predicate is
`t["status"] == "accepted" and t["entry_kind"] in {theorem, counterexample_candidate} and
t["conclusion_type"] in {theorem, counterexample}`.
The live ledger (`a1674f094979`) carries **0/62 rows with a `status` key**: its vocabulary is
`content_status` / `verification_status` / `review_status` / `author_asserts_supports`. The first
conjunct is therefore false for every row, and `covered` is unreachable at the live bytes. The
declared summary was built against ledger `ce42d205e761`, which is not the live ledger.

Controls (all four in `controls.json`):

| id | control | result |
|---|---|---|
| C1 | add **only** `status: accepted` to a *copy* of the live ledger on rows with `content_status=verified` + `author_asserts_supports=true` (62 rows touched) | published counts reproduced **exactly**: 7/3/3/8 = 21 |
| C2 | second unmodified rebuild, byte-identical to the first | identical (`true`) |
| C3 | *counterfactual*: re-key the predicate to the nearest live token (`content_status=verified and author_asserts_supports`) | 21 covered — same cell set |
| C4 | mutation: C3 key with `content_status` removed from a ledger copy | 0 covered |

C1 is the causal isolation: the published 21 `covered` cells are exactly the cells the frozen
predicate produces once the retired `status` vocabulary is restored. C4 shows the counterfactual
instrument is sensitive to the field rather than to file identity.

### F5 — What the 21 published cells mean at the live bytes (two readings, one caveat)

- **Under the frozen builder key**: the live ledger cannot license any `covered` cell; all 21
  rows on disk are marked `evidence_basis: ledger_theorem_covered`, a token the live ledger no
  longer supports. This is an evidence-binding defect on the published matrix and summary.
- **Under the pending A0/BL-9 vocabulary ruling**: if `content_status: verified and
  author_asserts_supports: true` is ruled to carry acceptance force, the same 21 cells return
  (C3) — but all 62 rows also carry `review_status: not_independently_reviewed`, so any citation
  of a `covered` cell must carry that caveat. This report does **not** make that ruling.

Either way the artifact of record must move: rebuild + re-publish the matrix and summary at the
live ledger, or obtain the vocabulary ruling and re-key the builder, then emit fresh artifact
events. The worker cannot write canonical paths.

### F6 — Exposure

The stale family is not peripheral: `research_map.json` mentions `class_coverage.csv` 26×,
`coverage_summary.json` 20×, `l1_class_coverage` 41×; `events.jsonl` 57× / 50× / 159×. The L1
node's own declared artifact (`ledger/citation_audit.csv`) **is** aligned
(`315c19145065`, `declared_hash_matches_measured: true`), so this is a supporting-evidence defect,
not a node-artifact defect.

## Rebind manifest (owner: lead-literature; A0/BL-9 for the vocabulary branch)

1. Re-pin the WCC and C2 conformance outputs to `d9cebb9404b2` / `e9a27996dfd3` + ledger
   `a1674f094979` and re-emit artifact events (content readings unchanged — F2).
2. Rebuild `ledger/class_coverage.csv` + `coverage_summary.json` at the live ledger and re-emit
   artifact events; do not cite the current 7/3/3/8 counts meanwhile.
3. Obtain the A0/BL-9 ruling on `content_status`/`author_asserts_supports` acceptance force
   before re-keying the builder; record the ruling in the same revision.
4. If a C0 conformance instrument is wanted, it does not exist yet (F1) — a gap, not a rebind.

## Falsifier

This census is falsified by any of: (a) a declared pin listed as SUPERSEDED whose live file
actually hashes to the declared value; (b) a rebuild of the coverage matrix at the live ledger
inputs that equals the published `abbaee54a5a3` or yields a non-zero `covered` count under the
unmodified builder; (c) demonstration that the live ledger does contain a `status` key on one or
more rows; (d) controls C1/C4 failing to move the counts in the recorded directions; (e) any
canonical input changing during the run window (`inputs_stable` would read false).

## Reproducibility

`report.json` carries `determinism.stable_core_sha256`, a hash over parts 1–4 (pins, conformance
field diff, coverage rebuild, controls) which is a pure function of the pinned inputs and was
verified byte-stable across two runs (`f69f7632300c`). The report additionally embeds live-map
observation fields (the rerun JSONs' own `created_at`/`out_sha256`, the class-definition `map_*`
observation values, and the part-5 mention counts) which move with the map and the 15-minute
auto-cycle; those are listed in `determinism.volatile_fields`. The emitted artifact events pin the
snapshot bytes, as required.

## Non-claims

Not a gate verdict; not a node status or `validation_status` change; not a class re-adjudication;
not a claim that the 21 cells are mathematically unsupported — only that the live ledger does not
license the token used to publish them; not an A0/BL-9 vocabulary ruling; not a review verdict on
any artifact; not authority to edit canonical or third-party artifacts.
