# W033-GFORM-R29-LEDGER-03 — two-channel G-FORM accept ledger (FROZEN rev29)

Bounded, class-bound worker task by `worker-033`. **Scope: accept-set bookkeeping
only.** No gate verdict, no node completion, no theorem, no physics, no
adjudication of substantive F1/F2a/F2b findings.

Classes: `AF-WCC-VAC-GEN` (F1), `AF-SCC-C2-VAC-GEN` (F2a), `AF-SCC-C0-VAC-GEN` (F2b).

## What was measured

Epoch: schema bytes `F1 d9cebb9404b2…`, `F2a e9a27996dfd3…`, `F2b b2ab6acb2bbe…`,
declared by FROZEN revision 29 (`artifacts/formulation/FROZEN.json` @`815e08079aef`,
frozen 2026-09-12T00:57:26+08:00).

Baseline quote under audit: controller G-FORM reason `checked_at`
**2026-09-12T01:01:17** (astra-lifecycle-06-final,
`runtime/state/controller_verification/lifecycle_20260912-010117.json`
@`076d03a64321`, reason @`3fc6c74453b0`):

| class | quoted accept reviewers |
|---|---|
| F1 | worker-045, worker-072, worker-075, worker-085 |
| F2a | worker-017, worker-072, worker-075 |
| F2b | — |

Recomputed from the pinned two-channel corpus (`reviews/*.json` + accepted
`research_map/events.jsonl`), with hash binding, full-schema filter, non-author
filter and explicit S1/S2 supersession, at the freeze instant
**2026-09-12T01:06:58+08:00**:

| class | operative full-schema accepts | operative gate accepts | controller scan at freeze | two distinct (full) |
|---|---|---|---|---|
| F1 | worker-038, worker-052, worker-072, worker-075, worker-080, worker-085, worker-089 | same minus worker-089 (`counts_as_gate_accept=false`) | worker-052, worker-072, worker-075, worker-085 | **yes** |
| F2a | worker-017, worker-034, worker-072 | worker-017, worker-034, worker-072 | worker-017, worker-072 | **yes** |
| F2b | worker-061 (event-only) | worker-061 | — | **no** |

Missing from the controller scan at freeze: F1 `worker-038`, `worker-080`
(event-only accepts), `worker-089` (`target_id`
`schemas/af_wcc_vacuum.yaml#d9cebb9404b2` is not mapped by
`astra_lifecycle._targets_in_review`); F2a `worker-034` (event-only); F2b
`worker-061` (event-only). No spurious controller entries were found.

## Findings

| id | class(es) | severity | summary |
|---|---|---|---|
| W033-R29-HF-01 | all three | hard | Controller scan ≠ two-channel operative set for every class: file-channel-only scan plus the exact-alias target map drops event-only accepts and path#hash target_ids. |
| W033-R29-HF-02 | AF-SCC-C0-VAC-GEN | hard | F2b has exactly one full accept (worker-061, event-only) but the quote reports 0; F2b still fails the two-distinct criterion under both views. |
| W033-R29-HF-03 | AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN | hard | Two quoted accepts (worker-045 F1, worker-075 F2a) have no accept content in the pinned corpus — current bytes at those paths are revise written after the quote (in-place amendment, no separate path). The quote is not reproducible from frozen bytes. |
| W033-R29-POS-04 | F1, F2a | info | At the frozen bytes F1 and F2a meet the two-distinct-accept criterion in the full view; F2b does not. Worker bookkeeping measurement, not a gate verdict. |
| W033-R29-INFO-05 | all three | info | In-place amendment of review files is a reproducibility hazard independent of the channel gap; the accepted event stream is the durable record. |
| W033-R29-INFO-06 | all three | info | Declared non-epoch hashes cited by the operative accepts resolve on disk (`0abb9ed8a961` → canonical taxonomy, `9e335e9ba1bf` → taxonomy_consistency.json), 0 unresolved; HF-086-R1 declared-hash gap is repaired at these bytes. |

## Rules (frozen before measurement)

Hash binding only through whitelisted pin fields (`artifact_sha256`,
`reviewed_sha256`, `target_sha256`, `cited_sha256`, `sha256`, … and the same keys
inside `evidence` / `pins` / `target_pins`); `evidence_refs` never bind; context
pins never bind. Full = `counts_as_full_schema_verdict is not False`; independent
= reviewer not in {astra-lead-formulation, lead-formulation, deepseek-flash-01};
S1 = named supersession retires; S2 = same reviewer's latest verdict at the same
target+epoch retires earlier differing verdicts; cross-channel duplicates with
identical reviewer/target/verdict/time are one record. Semantics inherited
verbatim from `artifacts/worker-033/gform_p05_ledger/ledger.py` @`4342806ad5fe`.

The controller scan is reproduced exactly (`controller_scan()`): file channel
only, `_targets_in_review` exact-alias target map, `_explicit_pins` top-level
whitelist, no supersession, face value — against
`research_map/astra_lifecycle.py` @`032d4afcb061`.

## Artifacts

| file | content |
|---|---|
| `ledger.py` | extraction + rule implementation + controller-scan reproduction + 19 fail-closed controls |
| `report.json` | full measurement, per-class analysis, findings, falsifier |
| `controls.json` | 19 controls (synthetic rule controls + material flips on pinned data) |
| `review.json` | worker review verdict on the 01:01:17 G-FORM ledger quote |
| `run.log` | one-line run summary |
| `pinned/` | frozen corpus: `records.json` (557 records), `quoted.json` (baseline + FROZEN + live quote provenance), `sources.json` (per-source hashes), `MANIFEST.json` |
| `SHA256SUMS` | hashes of all deliverable files |

## Reproduce

```bash
python3 artifacts/worker-033/gform_r29_ledger/ledger.py            # verify pinned + run
python3 artifacts/worker-033/gform_r29_ledger/ledger.py --extract  # re-pin (new snapshot)
```

Exit 0 = all controls pass; 2 = a control failed; 3 = pinned manifest drift.
Read-only on canonical paths.

## Falsifier

Re-run `ledger.py` on the pinned snapshot; controls fail-closed. The report is
falsified if any of: the two-channel operative set at freeze equals the
controller-scan set for all three classes (no channel/target gap exists on the
pinned corpus); worker-061's F2b accept at `b2ab6acb2bbe` is withdrawn,
superseded by a later binding verdict from worker-061, or shown not to bind that
hash; a second independent full-schema F2b accept lands inside the pinned
snapshot; F1 or F2a falls below two operative full accepts; the live schemas move
off `d9cebb9404b2` / `e9a27996dfd3` / `b2ab6acb2bbe`; or the pinned FROZEN
rev29 / baseline-report / reason hashes differ from their constants.

## Not claimed

No gate verdict, no `done` status, no promotion; no theorem or physics; no
adjudication of the substantive F1/F2a/F2b findings or of the
`counts_as_gate_accept` dispute.
