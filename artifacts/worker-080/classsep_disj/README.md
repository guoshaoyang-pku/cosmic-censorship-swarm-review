# W080-CLASSSEP-DISJ-01 — candidate HF-02 "disjunction of class_ids" rule

Worker: `worker-080` (bounded instance, 2026-09-12 ~00:52). Classes: **AF-WCC-VAC-GEN,
AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN**. Node: A1. Gate: G-AUDIT (calibration evidence only).

**Status: worker-level candidate rule + measurements. No gate verdict, no node status, no
canonical file written. Adoption is the detector owner's decision.**

## Question

worker-036 (2026-09-12T00:38, map review `research_map/class_separation.py`, verdict revise 2.0)
measured that the standing class-separation detector is **silent on rubric HF-02 "disjunction of
class_ids"**: `_scan_class_ids` flags a *single* token that contains both C0 and C2 and unknown
AF- tokens, but nothing about a container binding >=2 *distinct frozen classes*. That is the live
L0 condition — `ledger/theorems.jsonl` at `a1674f094979` carries **8 rows with two frozen
`class_ids`** — and the literature lead's critical-path blocker is exactly those 8 rows. worker-036
proposed: *"add a list-disjunction rule (>=2 known class tokens in one class_ids container ->
finding) plus >=1 positive and >=1 negative fixture ... re-run `runtime/bin/classsep_regression.py`"*.

This task builds and measures that rule, and first **falsifies the proposal as literally written**.

## Method

`run_classsep_disj.py` loads the canonical detector and the candidate side by side, pins every
input by sha256 at entry and re-measures at exit, and pre-registers every expectation. It scores:

1. the worker-07 falsification corpus (27 fixtures) under both modules, with the repo root forced
   to the workspace root (the candidate lives outside `research_map/`, so its own `__file__`-relative
   root would be wrong);
2. synthetic structured positives/negatives and asserted artifact-line positives/negatives
   (written to `fixtures/`, hashed in `report.json`);
3. the live L0 ledger, the three frozen schemas, and the live map;
4. the audit-side implementation (`artifacts/audit/audit_lib.py check_class_binding`) on the two
   list-disjunction probes worker-036 used.

The candidate (`class_separation_disj_candidate.py`, canonical + delta, unified diff in
`patch.diff`) adds only:

- `_known_class_tokens` / `_scan_class_ids_disjunction`: >=2 **distinct known frozen** tokens in
  one asserted container -> `CLASSSEP: disjunction of class_ids in <where>: [...]`;
- `disjunction_findings(row, where)` and `findings_for_ledger(rows)`: structured-row scan;
- one delta in `findings_for_text`: an asserted `class_id:` / `class_ids:` line is also run through
  the disjunction rule (same scoping as the existing `_scan_composite` declaration mode).

**Scope decision (measured, not asserted).** The unscoped version of the proposal fires on **349**
`class_id`/`class_ids` key instances in the live map, nearly all of them node/claim/review *scope
and coverage* metadata rather than disjunctive assertions. The candidate therefore routes only
asserted containers (structured rows and asserted class-id lines) through the new rule; the map's
`findings_for_map` behavior is byte-for-byte unchanged (20 findings before and after, 0 of them
disjunctions). The 349 count is reported, not adjudicated: some map claims may be genuine HF-02
items for the audit lead to rule on separately.

## Results (all expectations met; exit 0)

| check | result |
|---|---|
| worker-07 regression, canonical | 17 tp / 0 fn / 10 tn / 0 fp, PASS |
| worker-07 regression, candidate | **17 / 0 / 10 / 0, PASS**; per-fixture detection identical to canonical |
| structured positives (2-class list, 3-class list, comma string, semicolon string, WCC+SCC list) | **5/5 flagged** |
| structured negatives (single, empty, same-class duplicate, unknown-only, singular string, null) | **6/6 clean** |
| asserted text positives (flow list, comma line) | **2/2 flagged** |
| asserted text negatives (single line, prose mention, exclusion flow-map) | **3/3 clean** |
| live L0 ledger `a1674f094979` (62 rows) | **exactly 8 flagged**: D-004, D-005, T-303, T-305, T-402, T-515, T-526, T-528 |
| frozen schemas F1/F2a/F2b | 0 disjunction findings |
| live map | naive counterfactual **349** vs scoped **0**; total findings 20 == 20 (no collateral) |
| audit_lib probe | P1 (singular+list) 0 violations; P2 (list-only) reports *"class_id None is not in the frozen class registry"*, **never** the rubric's "disjunction of class_ids" condition |
| determinism / input pins | measurement body identical on re-run; all 8 pinned hashes stable before/after |

Pins: detector `c266dbceca87fb99`, ledger `a1674f09497975cf`, rubric `d748a9e3574ebe0c`,
worker-07 corpus `d69ad58468be1665`, audit_lib `ae573db84631b970`, schemas
`cce9c60146d6` / `5476a3f2c6bc` / `55d0a1ea9bda`. Map measured at run entry/exit in
`report.json` (the map moves with swarm traffic; no drift inside the run).

**Advisory hash-hygiene observation (not gated):** the map review event by worker-036 that this
task builds on declares `target_sha256 = c266dbceca87b8b0f0f4b6ba4becc4bf57d2b1f4f0f6b0b9e5a5c1e0d5c9a6a1`
for `research_map/class_separation.py`, but the measured file is
`c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920` (8-char prefix matches, full
hash does not). The substance of worker-036's finding reproduces independently; only the recorded
target hash does not bind.

## What the owner can adopt

1. **Scoped rule**: apply `patch.diff` to `research_map/class_separation.py` (or copy the candidate
   module) and add one positive + one negative list-disjunction fixture to the worker-07 corpus;
   then re-run `runtime/bin/classsep_regression.py` at the new detector hash. The candidate already
   passes the standing corpus.
2. **Scope ruling**: decide separately whether map claim/review `class_ids` scope lists are in
   scope for HF-02. The candidate deliberately does not flag them; the 349-instance counterfactual
   is the measured cost of doing so.
3. **Audit-side naming**: `audit_lib.check_class_binding` still does not produce the rubric's
   "disjunction of class_ids" condition for a list-only row (it reports the singular-field
   registry error instead); if G-AUDIT needs that condition named, that is a second, independent
   patch.

## Falsifier

Re-run `python3 artifacts/worker-080/classsep_disj/run_classsep_disj.py` at the pinned hashes:
any change in the worker-07 regression score, any structured/text positive not flagged, any
negative flagged, a ledger finding set other than the 8 named rows, a disjunction finding on a
frozen schema or on the map under the scoped rule, a collateral change to the detector's other map
findings, or input-hash drift voids this report. A genuine HF-02 disjunction (a ledger/claim row
asserting one result under two frozen classes) the scoped rule does not flag — or a legitimate
single-class container it flags — falsifies the rule itself.

## Limits

- Worker-side candidate only: no canonical path was modified; the shared regression runner was not
  edited. Adoption is the detector owner's decision (CF-4: checkers flag, never author).
- The synthetic corpus is worker-authored; the worker-07 27-fixture corpus is the external control.
- `classsep` PASS is calibration evidence for class-binding shape, not a mathematical verdict, not
  a gate, and not coverage for the audit_lib implementation's HF-02 branches.
- The audit-side and map-scope questions above are left explicitly open; this task asserts nothing
  about them beyond the measurements in `report.json`.

## Files

| file | sha256 (16) | role |
|---|---|---|
| `class_separation_disj_candidate.py` | `d6f419e44b105ae7` | candidate detector (canonical + delta) |
| `run_classsep_disj.py` | `89df42a4fcd144e9` | pinned harness (exit 0 iff all expectations hold) |
| `report.json` | `3b512fe219babe19` | full measurements, pins, expectations, falsifier |
| `patch.diff` | `af5a7493fb96b143` | unified diff vs `research_map/class_separation.py` |
| `fixtures/*.json`, `fixtures/*.yaml` | see `report.json.fixtures` | 5 structured positives, 6 structured negatives, 2 text positives, 3 text negatives |

Reproduce: `python3 artifacts/worker-080/classsep_disj/run_classsep_disj.py` (exit 0).
