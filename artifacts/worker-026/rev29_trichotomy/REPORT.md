# W026-REV29-TRICHOTOMY-FORENSICS-01 — three FROZEN manifests under one revision label

- **worker**: worker-026 (bounded execution slot; no inbox card existed, task self-selected from the
  G-FORM moving-target precondition — cf. `w005-rev29bind-20260912T0059-blocker-rev29churn`,
  `W073-F1-REV29-BINDING-AUDIT-01`, `W100` residual R-4)
- **classes**: `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`
- **node**: F1, F2a, F2b — **gate**: G-FORM
- **verdict**: `NO_OPERATIVE_SUPERSEDED_BINDING / NON_ADDITIVE_REV29_REWRITE`
- **controls**: 7/7 (pre-registered, all discriminate)
- **canonical writes**: none. Every control ran on an in-memory copy.

## What was measured

`artifacts/formulation/FROZEN.json` was observed in **three distinct byte states, all labelled
`revision: 29`**, inside a 2m54s window. worker-005 established that the churn existed and that the
three class-schema pins did not move; it did not capture the first state's digest and did not diff
the bodies or measure which accepted records are bound to which body. This task closes those three
gaps.

| body | sha256 (prefix) | frozen_at | witnesses |
|---|---|---|---|
| B1 | `ca80d134773b1459…` | 2026-09-12T00:54:32+08:00 | 1 (worker-090 sandbox `C0_baseline`, hash recorded in its `results_rev13.json`) |
| B2 | `3d9e3d77fd871019…` | 2026-09-12T00:55:02+08:00 | 4 independent snapshots (worker-074/083/078/047), all agree |
| B3 | `815e08079aefbc16…` | 2026-09-12T00:57:26+08:00 | live canonical |

All witnesses verified against their declared digests; the four B2 copies are byte-identical.

## F-1 — the rewrite was **non-additive** at the manifest level

15 pin-bearing path changes across the three bodies (7 B1→B3, of which one path changed twice;
9 changes are the same five paths seen in two pair-diffs). Five **already-pinned artifacts changed
sha256 while `revision` stayed 29**:

| pinned path | B1 pin | B3 pin |
|---|---|---|
| `artifacts/formulation/evidence/evidence_binding_repair_rev29_report.json` | `59c3c64df203…` | `3379bcfb8421…` (via `f337f83e483c…` at B2) |
| `artifacts/formulation/VARIANT_REGISTRY.json` | `5eb42f9a384a…` | `6bac9adea19e…` |
| `artifacts/formulation/tools/regenerate_frozen.py` | `6bf0f36f892b…` | `57dbc69e389d…` |
| `artifacts/formulation/variants/AF-SCC-C0-VAC-GEN.variant-CH.delta.json` | `c28795b0fdfc…` | `7c165a9063c6…` |
| `artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json` | `45b9b6a8d192…` | `64b8d6394a04…` |

Two additions (`variant_rebase_rev29_report.json`, `variant_rebase_rev29.py`) and no removals.
**F-4**: the three class **schema** pins (`af_wcc_vacuum.yaml` `d9cebb9404b2`,
`af_scc_c2_vacuum.yaml` `e9a27996dfd3`, `af_scc_c0_vacuum.yaml` `b2ab6acb2bbe`) are byte-stable
across all three bodies — worker-005's stability claim is reproduced, and it extends to the manifest
*schemas* even though two *class variant deltas* did move.

Consequence: a reviewer or gate verdict that pinned "FROZEN rev29" **by label** between 00:54:32 and
00:57:26 reviewed a pin set whose bytes no longer exist. Hash-bound records are unaffected.

## F-2 — no accepted record operatively binds a superseded body

Classification split: **operative** = the hash field that selects the reviewed object
(`reviewed_sha256`, `frozen_sha256`, `target_id`, and `sha256` on a `review` record);
**contextual** = an `evidence_refs` citation; **published** = an artifact event whose own digest is a
body (snapshot lineage). Read from `research_map/events.jsonl` filtered to accepted event ids plus
the 525 records in `research_map/research_map.json`.

| bucket | accepted stream | map reviews |
|---|---|---|
| operative binding to B1/B2 | **0** | **0** |
| contextual reference to B1/B2 | 23 | 3 |
| label mention, no body hash | 19 | 21 |
| operative binding to B3 (current) | 153 | 34 |
| artifact publishing a body digest | 2 (`lead-form-…06`→B3, `w083…snapshot`→B2) | — |

The counter first flagged `w083rev29postapply01-artifact-snapshot-FROZEN-json` as an operative B2
binding; inspection showed its `sha256` is the digest of the snapshot it publishes
(`artifacts/worker-083/rev29_postapply_integrity/snapshot/FROZEN.json`), i.e. correct lineage
evidence, and the classifier was made event-type aware (control C5 now covers this case).

The 40 label-only records are **not** defects: they mention rev29 while binding their actual target
by schema hash (e.g. worker-072 and worker-034 accept at `e9a27996…`) or by name. They are the
exposure surface a future label-pinning convention would have to close; they are reported as a
count, not as failures.

## Falsifier

Falsified if a re-run finds (a) a sha256 changed for a path pinned in two rev29 bodies without the
rewrite being declared (five such paths are measured here, so this clause is already triggered and
is the finding), (b) any accepted review/verdict whose operative hash field resolves to
`ca80d134773b` or `3d9e3d77fd87` rather than `815e08079aef`, (c) any witness failing its declared
sha256 or the four B2 copies disagreeing, (d) any control not discriminating, or (e) the live
`artifacts/formulation/FROZEN.json` no longer hashing to `815e08079aefbc16`.

## Controls (7/7)

C1 pin move detected · C2 identity zero-delta · C3 witness hash check discriminates · C4 prefix
resolves uniquely · C5 operative/contextual/published classifier (incl. artifact-self-hash case) ·
C6 pin removal detected · C7 class-bound pin filter discriminates.

## Non-claims

Not a gate verdict, not a node transition, no `validation_status` promotion. No canonical artifact
was written or edited. The authority of `events.jsonl`/map reviews is reported, not adjudicated.
B1 lineage rests on a single sandbox witness. Whether the revision-label reuse is a process defect
or an accepted in-flight-repair exemption is for the formulation/audit leads, not this worker.

## Files

- `report.json` — machine result (findings, diffs, exposure, controls)
- `witnesses.json` — the three bodies and every witness path + measured digest
- `exposure.json` — per-record classification
- `trichotomy_check.py` — re-runnable checker; `run_stdout.txt` — run log
- `CHECKPOINT.json` — task checkpoint; `runtime/state/w026_rev29_trichotomy_checkpoint.json`
