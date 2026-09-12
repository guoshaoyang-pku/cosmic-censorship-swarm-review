# W066-F2AGG-VERDICT-01 — independent verdict on the F2 aggregator

Bounded, class-bound worker task taken without an inbox card (worker-066 instance
`worker-066-20260912T002907-968807`).

| field | value |
|---|---|
| target | `schemas/af_scc_regularities.yaml#94562101a81645349e1ff17b9184dd956887d8fc6b54a3d7ed7cd786ed8b4ce4` |
| class ids | `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN` |
| node / gate | F2 / G-FORM |
| pinned components | C2 `b6123750b37d…`, C0 `1bb78ce9b357…` (snapshot 00:31) |
| verdict | **revise** (reviewer-level only; workers cannot move gates) |
| score | 2.5 |
| hard failures | `W066-F2AGG-H1` … `W066-F2AGG-H5` |

## Why this task

`schemas/af_scc_regularities.yaml` is the F2 index that pins the two strong-censorship
components. The only recorded pin check under this path
(`artifacts/worker18/f2_review/aggregator_pin_check.json`) targets the **retired** merged
aggregator `c6bfda2b` and returned `fail`; the file's own review notes require a re-run
after the astra-classscope-02 re-pin, and no verdict existed at the live hash `94562101`.
The task was therefore an independent, hash-bound verification of the live bytes.

## What was measured (all on pinned copies; no canonical writes)

**Machine-green at the pinned byte set**

- `PIN-DRIFT` pass: live aggregator bytes == pinned bytes (`94562101a816`) throughout.
- `SEP-1` … `SEP-7` pass under an independent re-implementation (not the author's lint):
  exactly two components, one class id each; no class-id join or disjunction; no composite
  regularity token in any selector field; no conclusion object; exactly one selector per
  component (`C2` / `C0`); pins equal the pinned component bytes; no restated cross-class
  relation.
- `CONTRACT-BOOLS` pass: all seven `aggregator_contract` booleans match their declared intent.
- `CONTROL-SUITE` pass: **8/8** — one pristine control passes, and all seven hand-built byte
  mutants (pin mismatch, merged class string, conclusion injection, duplicate component,
  missing component, composite token, restated implication) are rejected by the
  pre-registered rule and only that rule.
- `SEP3-RAW-MENTIONS` pass: the only raw-text composite-token mentions are inside
  anti-scope/prohibition lists (`"any 'C0 or C2' composite regularity"`) or a containment
  disclaimer — mentions, not uses.

**Findings (blocking at the pinned bytes)**

| id | finding | falsifier |
|---|---|---|
| `W066-F2AGG-H1` | duplicate root mapping key `revised_at` ×4 (lines 11-14) while `revision: 6`: a conforming parser keeps only the last value, so the declared revision history is unreadable (same defect class as W066-B1) | `yaml.compose` returns no duplicate at `$.revised_at`, or a conforming parser recovers four distinct values |
| `W066-F2AGG-H2` | declared bindings are stale: "rule_spec v1.1" vs frozen v1.2 (`40f9bb9e`); the named gate (`000e09e4`) enforces R01–R25 + R27–R31 while the spec declares R01–R16 (14 enforced ids undeclared); `revision_note` pins F0 at `0fcc6a19`, matching neither live F0 tree (`276009f4` canonical / `c8e979a1` authoring) | spec declares v1.1 or contains R17–R25/R27–R31; or a live F0 tree starts `0fcc6a19` |
| `W066-F2AGG-H3` | the recorded review-owner pin check targets the retired `c6bfda2b` with verdict `fail`; no verdict exists at `94562101`, and the file itself demands the re-run | a review artifact at `94562101` with a non-fail verdict |
| `W066-F2AGG-H4` | not freeze-bound: absent from FROZEN rev26 (40 files); the map's `legacy_artifacts` record for this path describes the live bytes as the "legacy combined C0/C2 file" although the live file declares `merge_forbidden: true`, `defines_conclusion: false`; the retired merged artifact is a different byte string (`c6bfda2b`) | FROZEN rev26 lists the path, or `94562101 == c6bfda2b`, or the map labels it a non-class index |
| `W066-F2AGG-H5` | **live drift measured in-task**: both components rewritten at 00:32:02 — C2 `b6123750b37d` → `5476a3f2c6bc`, C0 `1bb78ce9b357` → `55d0a1ea9bda` — so `SEP-6` fails at verdict time and the aggregator is invalid until re-pinned (its own revision note says exactly this) | the live components hash back to `b6123750b37d`/`1bb78ce9b357`, or the aggregator is re-pinned and re-emitted |

The author's lint, run only as a cross-check, agrees on the drift:
`aggregator=fail components=fail fixtures=pass`, failing A3/C6 on exactly the two component
pins (`evidence/author_lint_report.json`). It does not detect the duplicate-key defect
(it loads with a last-wins parser), which is why the independent `yaml.compose` probe in
`evidence/checks.json#YAML-DUP-KEYS` carries H1.

## Files

| path | what |
|---|---|
| `PINNED.json` | sha256/bytes/mtime for the ten pinned inputs |
| `pinned/` | byte copies of the pinned inputs |
| `verify_aggregator.py` | independent checker + control builder (re-runnable) |
| `snapshot.py` | pin/snapshot step |
| `controls/` | the seven mutants + pristine control that were run |
| `live_recheck/` | durable copies of the live component bytes the drift was measured against |
| `evidence/checks.json` | every check with pass/fail and raw observations |
| `evidence/controls.json` | per-control pre-registered rule vs fired rule |
| `evidence/staleness.json` | declared-binding vs frozen-object probes |
| `evidence/live_drift.json` | live component hashes, pin comparison, raw composite mentions |
| `evidence/author_lint_report.json` | author lint output (cross-check only) |
| `report.json` | full verdict, findings, falsifiers, evidence refs |
| `CHECKPOINT.json` | checkpoint result after the events were emitted |

## Reproduce

```bash
cd artifacts/worker-066/f2_aggregator_verdict
python3 snapshot.py            # re-pin (hashes will differ after the 00:32 component revision)
python3 verify_aggregator.py   # checks + controls -> evidence/, report.json
python3 emit_events.py         # schema-validated events -> comms/outbox/worker-066.jsonl
```

## Limits

The verdict is a reviewer verdict, not a gate transition. It binds the pinned bytes only.
The separation invariants are structural: they cannot show that either component's
mathematics is true, non-vacuous, or properly scoped. The mutant corpus is hand-built and
synthetic (eight controls), so it establishes falsifiability of the checker, not coverage
of all possible leaks. The live drift is time-sensitive: any later component revision makes
H5's hashes historical and the remedy (re-pin + re-freeze) unchanged.
