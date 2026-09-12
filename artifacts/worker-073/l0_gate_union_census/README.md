# W073-L0-GLIT-UNION-CENSUS-01 — L0/G-LIT verdict binding census at ledger a1674f094979

**Actor** worker-073 (recycled slot; no inbox card exists for this agent id)
**Node / gate** L0 / G-LIT
**Class scope** AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN, AF-WCC-SCALAR-SPH
**Decision** `L0_UNION_CONFIRMED` — 10/10 controls fired, all criteria pass, double-run byte-identical
**Authority** worker measurement only: no gate verdict, no node status, no `validation_status`,
and **not** a substitute for `astra-life05-verify-l0-final`. No canonical path is written.

## Question

G-LIT `unmet[0]` requires `astra-life05-verify-l0-final` to state "whether the accepts bind the
primary-source ledger or a card subset". Independently: at `ledger/theorems.jsonl`
sha256 `a1674f094979`, which L0 verdicts actually bind those bytes, and does the union of

- **A** `reviews/*.json` review objects,
- **B** `research_map/research_map.json['reviews']` (authoritative accepted stream), and
- **C** `research_map/events.jsonl` review events

reproduce the 4-row `coverage_table` of `reviews/L0-review-final-verify.json` (astra-lead-audit, 01:18)?

Why this is not a duplicate: `artifacts/worker-036/gform_r3_binding_census` explicitly scopes to
F1/F2a/F2b G-FORM targets and excludes L0; the lead's artifact is an adjudication with an accept
table, not a per-record binding census; `W048-GFORM-COVERAGE-RECOUNT-01` audits the controller
coverage instrument, not L0 record binding.

## Method

Own stdlib-only, read-only instrument `run_check_073_l0union.py`. Strict pin gate (exit 3 on
ledger drift, before and after). Union corpus deduped by `event_id` → `review_id` → identity;
non-verdict artifacts excluded and listed. Hash binding classified from **both** carrying sites:
`reviewed_sha256` (`EXACT_FIELD`) and a `path#sha256` reference embedded in `target_id`/`reviewed_path`
(`EXACT_TARGET_REF`), plus `OTHER_HASH`, `PATH_ONLY`, `MALFORMED`, `UNBOUND`. Inputs snapshotted
byte-for-byte into `snapshot/`. Pre-registration `prereg.json` was written before run 1; three
disclosed amendments fix instrument defects only (no data criterion relaxed), with runs 1–3 preserved.

## Result

Pins stable: ledger `a1674f094979` (62 rows, 151521 bytes) before and after; lead artifact
`8f3ddc732983`; map `45acd9d93d1e`; events `9f82f36d93ce`.

| corpus | accept | revise | inconclusive | accept reviewers |
|---|---:|---:|---:|---|
| union (files + map + events), distinct reviewer-verdict units | 4 | 3 | 1 | 050, 072, 075, 079 |
| union, physical records (2 cross-source duplicates) | 6 | 3 | 1 | same 4 |
| `reviews/*.json` only, hash-bound | 2 | 1 | 1 | 075, 079 |

Hash-bound revises: **worker-029, worker-093, worker-097**. Inconclusive: worker-063.

Binding of the four accepts — **all four bind the primary-source ledger, none binds a card,
digest, subset or snapshot**:

| reviewer | verdict | score | full flag (raw) | full by controller rule | binding |
|---|---|---|---|---|---|
| worker-075 | accept | 4.0 | True | full | `EXACT_FIELD` (file + stream) |
| worker-079 | accept | 4.0 | True | full | `EXACT_FIELD` (file + stream) |
| worker-050 | accept | 4.0 | **null** | **full** | `EXACT_FIELD` (stream only) |
| worker-072 | accept | 4.5 | **null** | **full** | `EXACT_TARGET_REF` (`ledger/theorems.jsonl#a1674f…`, stream only) |

So the gate basis named by the lead — two explicit full-schema non-author accepts (075, 079) —
is independently reproduced, and the `>= 2 distinct accepts` requirement holds. The labelled
count does not: see L0U-01.

## Findings

- **L0U-01 (major).** The lead's `coverage_table` states `counts_as_full_schema_verdict=False`
  for worker-072 and worker-050, but those records carry **no such value at all** (null), and the
  controller's own rule (`research_map/astra_lifecycle.py:195`,
  `full = d.get("counts_as_full_schema_verdict") is not False`) makes absence default to **full**.
  Under that rule the hash-bound full-accept set is `{050, 072, 075, 079}`, not the 2 named in
  `verdict_basis`.
- **L0U-02 (info).** worker-072's binding lives only in `target_id` as `ledger/theorems.jsonl#<sha>`.
  The controller scan's `_explicit_pins` (`astra_lifecycle.py:160-173`) reads only
  `artifact_sha256/reviewed_sha256/sha256/cited_sha256`, and the scan reads `reviews/*.json` only,
  so this accepted-stream-only record is invisible to it. File-scan and union views must disagree
  here by construction.
- **L0U-03 (info).** The accepts bind the primary-source ledger, resolving G-LIT `unmet[0]`'s
  "primary-source ledger or a card subset" question in favour of the ledger.
- **L0U-04 (major, post-hoc derived).** The unmet text's "5 revise (025, 011, 093, 18, 005)"
  mixes bound and unbound verdicts: only worker-093 has a hash-bound revise record; 025, 011 and
  18 carry no pin (`UNBOUND`) and 005 carries a dict (`MALFORMED`). Meanwhile the two hash-bound
  revises **worker-029 and worker-097** are absent from the named list. The figure reproduces
  under neither hash-bound mechanism (union 3, files-only 1) and under-reports binding opposition.
- **L0U-05 (minor).** worker-005's `reviewed_sha256` is a dict, not a string — a signature-schema
  violation no exact-hash consumer can bind.
- **L0U-06 (info).** worker-075 and worker-079 each appear twice (file + accepted stream); the
  distinct-reviewer aggregate is the coverage unit.

## Controls

10/10 fired: hash mutant → `OTHER_HASH`; dict hash → `MALFORMED`; path-only → `PATH_ONLY`;
three-source dedup; lead-reviewer independence proxy; HF-14 positive injection fires;
row-count mutant fails; pin-drift abort; cross-source identity merge (D2 regression);
non-verdict exclusion (D3 regression).

HF-14 triple at the pinned bytes: `status=0`, `validation_status=0`, `supports_claim=0`
(`author_asserts_supports` is present on 60/62 rows and is **not** an HF-14 predicate; run 1
wrongly used it — see amendment-1 D1).

## Reproduction

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-073/l0_gate_union_census/run_check_073_l0union.py \
  --out artifacts/worker-073/l0_gate_union_census/report.json \
  --snapshot-dir artifacts/worker-073/l0_gate_union_census/snapshot
```

Deterministic: two consecutive runs are byte-identical apart from `started_at`/`finished_at`.

## Limits

- Independence is a proxy (`reviewer != 'astra-lead-literature'`, the ledger owner-of-record);
  no per-row authorship is available in the ledger to test independence more strongly.
- The census measures verdict records and hash binding only. It makes no mathematical claim,
  no coverage claim beyond the measured corpus, and does not adjudicate finding merit.
- Post-hoc L0U-04 is derived from the frozen snapshot, not re-measured.

## Falsifier

Re-run the instrument at the same pins: any per-record `binding_class`, coverage group or verdict
differing from `report.json`, any control not firing, any lead `coverage_table` row not
reproducing, or `ledger/theorems.jsonl` moving off `a1674f094979` voids the corresponding row or
the whole verdict.

## Artifacts

| file | sha256 (prefix) |
|---|---|
| `prereg.json` | `7db790ca3989` |
| `amendment-1.json` | `a3631dea0473` |
| `amendment-2.json` | `313442c7b59f` |
| `amendment-3.json` | `a78a434f92ff` |
| `run_check_073_l0union.py` | `bf99eb64e756` |
| `report.json` | `9972cb085f3c` |
| `run_stdout.txt` | `f97e63ecdafb` |
| `snapshot/union_records.json` | `61c5cc49278c` |
| `snapshot/MANIFEST.json` | `2805e0130e2f` |
| preserved runs | `report.run1-pre-amendment.json` `d401e68e4865`, `report.run2-pre-amendment2.json` `d40567e1dfbf`, `report.run3-pre-amendment3.json` (see `run_stdout.run3-pre-amendment3.txt`) |
