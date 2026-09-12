# W053-INDEX-RECON-01 — INDEX.md ↔ map reconciliation

Worker-053, one bounded class-bound task. `reviews/INDEX.md` (A1 review queue, generated
`2026-09-11T23:27:56+08:00`) was reconciled against `research_map/research_map.json` and the on-disk
canonical artifacts at one pinned snapshot. Read-only evidence: **no gate verdict, no node transition, no
judgement of any verdict's merit** — only whether the INDEX row and the map agree on hash and status.

## Command

```bash
python3 artifacts/worker-053/index_recon/check_index_recon.py   # writes reconciliation.json, stdlib only
```

## Pins (sha256, read once; re-hashed at end, `drift.detected = false`)

| input | sha256 |
|---|---|
| `ledger/theorems.jsonl` | `ce42d205e7617e3a032c109b24a00b57c7c6b104f37dad5125745af15deebd72` |
| `research_map/formulation_taxonomy.yaml` | `276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc` |
| `research_map/research_map.json` | `a8a73f983baa28d16052abc4cecdf93df9181be29af32d461ca542e4deba5448` |
| `reviews/INDEX.md` | `73b7b92a9babe627cfa00bfe24e362fee4f03669a441bee28d680d089abbaf78` |
| `schemas/af_scc_c0_vacuum.yaml` | `1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508` |
| `schemas/af_scc_c2_vacuum.yaml` | `b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2` |
| `schemas/af_wcc_vacuum.yaml` | `9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503` |

## Per-row reconciliation

| row | INDEX sha256(12) | INDEX verdict | live canonical sha256(12) | hash status | map gate | map accepts bound-to-live | map accepts unbound |
|---|---|---|---|---|---|---:|---:|
| A1 | `?` | ? | `—` | no_target_path | G-AUDIT pending | 0 | 0 |
| F0 | `347c924b4273` | revise | `276009f4f63d` | hash_superseded | G-F0 pending | 0 | 2 |
| F1 | `a7ef0398dfb7` | revise | `9a8bd4c96800` | hash_superseded | G-FORM pending | 0 | 1 |
| F2a | `21df6f7fc4a6` | revise | `b6123750b37d` | hash_superseded | G-FORM pending | 0 | 4 |
| F2b | `0150bfdf671b` | revise | `1bb78ce9b357` | hash_superseded | G-FORM pending | 1 | 5 |
| G-FORM | `4b2297eb850b` | reject | `—` | unresolvable_target | G-FORM pending | 0 | 0 |
| L0 | `e42923726186` | revise | `ce42d205e761` | hash_superseded | G-LIT pending | 0 | 6 |

`G-FORM` is a brace-glob/prose target (class-binding gate collection), so it has no single file to hash —
recorded as `unresolvable_target`, which is a limitation of the INDEX row, not a result about the gate.

## Gate-table reconciliation

| gate | INDEX says | map says | mismatch |
|---|---|---|---|
| G-F0 | fail | pending | YES |
| G-FORM | fail | pending | YES |
| G-LIT | fail | pending | YES |
| G-AUDIT | pending | pending | no |
| G-NUM | pending | pending | no |

## Findings (each carries its own falsifier in `reconciliation.json`)

### IR-01 (major)

Every class-bound INDEX row whose target is a single canonical file is hash-superseded: F0, F1, F2a, F2b, L0. The INDEX sha256(12) values are not the live bytes at the pinned snapshot, so no INDEX verdict can be read as a verdict on the current revision.

**Falsifier:** Re-run the checker at the same pins: the finding is falsified if any of these rows is classified hash_current, i.e. the first 12 hex of the live canonical sha256 equals the INDEX sha256(12).

### IR-02 (major)

The map stores accept verdicts for F0, F1, F2a, F2b, L0 that declare no artifact hash binding (artifact_sha256/reviewed_sha256 null and no #sha suffix on target_id), so they cannot certify any revision; counts: {"F0": 2, "F1": 1, "F2a": 4, "F2b": 5, "L0": 6}. At this snapshot the only class-bound target with an accept bound to the live canonical bytes is F2b (w001-review-f2b-20260912T002004+0800).

**Falsifier:** Re-run the checker at the same pins: falsified if an accept for one of these targets is found carrying a declared hash that prefixes the live canonical sha256.

### IR-05 (minor)

Hash-bound accepts at the live canonical bytes exist only for: F2b (w001-review-f2b-20260912T002004+0800). For every other class-bound target the map's accepts are unbound, so the G-F0/G-FORM unmet reason 'no accept at the current hash' is reproduced for them and not for this one.

**Falsifier:** Re-run the checker at the same pins: falsified if another target gains an accept whose declared hash prefixes its live canonical sha256, or if the bound accept's hash no longer prefixes the live canonical bytes.

### IR-03 (minor)

INDEX rows G-FORM name brace-glob/prose targets, not a single file, so their hash column cannot be reconciled mechanically by this checker.

**Falsifier:** Falsified if the pinned INDEX.md resolves those targets to a single concrete file path on re-read.

### IR-04 (major)

The INDEX gate table disagrees with the map gate verdicts for: G-F0, G-FORM, G-LIT. The INDEX records the 23:27:56 review-round verdicts; the map records later hash-bound pending verdicts (see map_unmet per gate).

**Falsifier:** Re-run the checker at the same pins: falsified for a gate if index_verdict equals map_verdict.

## Limits

- A map review is matched to a row by target_id/node/gate/path; review records with unrelated targets are ignored.
- binding is counted only through declared hash fields or a #sha target suffix, never by filename or prose (same policy as W03-VERDICT-BIND-01).
- the checker does not judge the merit of any verdict, only whether the INDEX row and the map agree on hash and status.
- content timestamps in the event stream are known unreliable (controller finding CF-6); ordering uses map list order.

## Falsifier for the whole report

Re-run artifacts/worker-053/index_recon/check_index_recon.py against the same pinned reviews/INDEX.md and research_map/research_map.json bytes. The report is falsified if (a) any row classified hash_superseded matches the live artifact prefix; (b) any row classified hash_current differs from the live sha256; (c) index_rows_parsed != the data-row count of the pinned INDEX table; or (d) drift.detected is false but a re-hash shows an input changed.

Inputs drift fast in this run (the formulation lead published new revisions during the window); the
report is valid only at the pins above. `check_index_recon.py` re-hashes every input at the end and sets
`drift.detected` if anything moved.
