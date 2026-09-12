# W036-CLASSSEP-COMPOSE-01 — do the two staged class-separation candidates compose?

**Worker:** `worker-036` · **Node:** `A1` · **Gate:** `G-AUDIT` / `G-CLASSBIND` · **Primary class:**
`AF-SCC-C0-VAC-GEN` (scope: the four frozen classes) · **Generated:** 2026-09-12 ~01:0x +08:00

**Verdict:** `PASS` — 48/48 checks. Both staged patches to `research_map/class_separation.py`
compose mechanically and behave **exactly additively** (`PR = P + R − C`) on every measured item,
in both the pinned-base window and the live-rebased window: **0 interactions**. The composition
also rebases cleanly (3-way, 0 conflicts) onto the canonical that moved mid-lifecycle, but a
**naive 2-way reapply of either patch file onto the new canonical would revert the new canonical's
own edit** — measured, not asserted.

## Why this task exists

Two staged, unapplied patches to the class-binding detector exist, each measured alone:

| patch | what | measured alone by |
|---|---|---|
| **P** `proposed/class_separation.py` `e2d24b927ee8` | prose precision: `statement` forced to prose mode; negated-split asserted as merge (R2-2/R2-3) | worker-085 (`W085-CANDIDATE-CLASSSEP-DIFF-03`) |
| **R** `artifacts/worker-036/classsep_disj_rule/candidate_class_separation.py` `1bc87c9542ed` | container recall: flag a `class_ids` container holding ≥2 frozen classes (R5) | worker-036 (`W036-CLASSSEP-DISJ-RULE-01`) |

The open card `astra-life05-classsep-calibration` (A1, G-AUDIT, due 02:30) must adjudicate the
prose candidate against the canonical detector. Nobody had measured whether the two patches can be
adopted **together** — or whether they interact. This packet supplies that measurement as worker
evidence (no adopt/reject recommendation, no gate verdict).

Mid-lifecycle the canonical itself moved: `c266dbceca87` → `a8c04fc31e4a`, a third, independently
applied change adding a CF-16 metalinguistic-quotation exemption inside `_scan_composite`. The
packet therefore measures **two windows**.

## Revisions

| id | bytes | role |
|---|---|---|
| `C0` | `research_map/class_separation.py` `c266dbceca87` | pinned study base |
| `C1` | `research_map/class_separation.py` `a8c04fc31e4a` | live base (CF-16 meta-quote exemption; reached mid-run) |
| `P` | `proposed/class_separation.py` `e2d24b927ee8` | staged prose patch, authored on C0 |
| `R` | worker-036 R5 candidate `1bc87c9542ed` | staged container patch, authored on C0 |
| `PR0` | `class_separation.composed.c0.py` `69459628d65b` | C0 + P + R (2-way primary composition) |
| `P1`/`R1`/`PR1` | `class_separation.c1_*.py` `c5d157d23823` (PR1) | C1 + P / C1 + R / C1 + P + R (3-way rebase) |
| `INERT0/1`, `OVER0/1` | threshold 99 / 1 | null and power controls, both windows |

`base_c0`: P = 4 hunks / R = 1 hunk, disjoint, 0 removed-by-R, reverse-apply reproduces C0 byte-for-byte,
ascending and descending compositions agree, composed delta = union of patch deltas.
`base_c1`: same shape after a **3-way delta rebase** (0 conflicts, reverse-apply reproduces C1).

## Measured — composition is additive

Aggregate over all measured items (worker-085 12-case battery + prior 26-case R5 battery +
12 pre-registered compose cases + 62 ledger rows + every `findings_for_map` element of the frozen
and live map snapshots), counting exact finding multisets per item:

| window | C | P | R | PR | interactions |
|---|---:|---:|---:|---:|---:|
| base_c0 (pinned) | 48 | 48 | 383 | **383** | **0 / 736 items** |
| base_c1 (rebased) | 43 | 43 | 378 | **378** | **0 / 736 items** |

`Counter(PR) == Counter(P) + Counter(R) − Counter(C)` held item-for-item. The pre-registered
12-case compose battery includes the interaction-prone shapes (container + declaration-mode bare
statement, + negated split, + merge assert, + family mismatch, + unknown token, semicolon container,
CF-16 prose shape, 3-/4-class scope metadata) — all matched the registered C/P/R/PR counts.

## Measured — live snapshot, both windows

Live map snapshot `ed28b714464e` (captured 2026-09-12 ~00:52 +08:00; the map keeps moving under
traffic, the measurement binds to the snapshot):

| window | base | base+P | base+R | base+P+R |
|---|---:|---:|---:|---:|
| C0 window | 20 | 21 | 228 | **229** |
| C1 window | 16 | 17 | 224 | **225** |

- **C0 → C1** (the change the owner already applied): removes 4 live findings (all prose-kind),
  adds 0 — i.e. it is a precision-only change on the live surface.
- **C0 → P**: +1 prose finding, −0. **C0 → R**: +208 container findings (6 node + 202 claim
  containers; cardinality 2/3/4 = 20/81/107), −0. **C0 → PR0**: +209 = 1 + 208 exactly.
- Frozen-map cross-check: `C0` = 10 findings and `R` adds exactly **100** disjunctions, reproducing
  the prior packet's numbers independently.
- Ledger `a1674f094979`: `R`/`R1` flag exactly rows `{3,4,24,26,29,45,57,59}`; `C0`,`C1`,`P`,`P1` flag none.

## Measured — rebase hazard

| naive operation (forbidden) | effect on C1 |
|---|---|
| 2-way re-diff of `proposed/class_separation.py` onto C1 | deletes **5** C1 lines, including the new exemption block |
| 2-way re-diff of the R5 candidate onto C1 | deletes **3** C1 lines — exactly the new exemption block |

The valid operation is the 3-way delta merge used here: 0 conflicts, reverse-apply exact. If the
owner adopts either patch, it must be rebased, not re-applied.

## Controls and regressions

- **External controls:** this harness reproduces worker-085's 12 recorded canonical/prose counts
  (12/12 each) and the prior packet's 26 recorded canonical/container expectations (26/26 each).
- **worker-07 27-fixture regression:** all 8 revisions `tp=17 fn=0 tn=10 fp=0` PASS; per-fixture
  classification identical across all 8. worker-027 OOD corpus likewise unchanged.
- **Null control:** composed-inert R5 (threshold 99) is behaviorally identical to the prose patch
  alone, on batteries and live map, in both windows.
- **Power control:** composed-overfire R5 (threshold 1) newly flags **7** negative cases — so the
  battery can fail in both directions.
- **Artifact-text scope:** `findings_for_text` is identical under all 8 revisions; the class_ids
  container blind spot on the text route remains (documented limitation, measured `X11`).

## Claim (worker level, `conclusion_type: formal_model`, `counts_as_full_schema_verdict: false`)

At the pinned hashes, P and R are mechanically composable and behaviorally additive on every
measured surface, and the composition rebases cleanly onto the new canonical `a8c04fc31e4a`;
the only hazard is naive 2-way reapplication, which reverts the new canonical's own edit. The
composition's live cost is dominated by R's 208 container signals on the current live snapshot
(196 more than the 2-class target population), so the surface/cardinality policy remains an owner
decision. This is **measurement evidence for the detector owner and the CLASSSEP-calibration
adjudicator**, not a gate verdict, node transition, or validated artifact.

## Falsifiers

See `report.json` `falsifiers` F1–F8; load-bearing: any window where the composition is not
`C + P + R` (conflict / reverse-apply / delta-union failure); any item where
`Counter(PR) ≠ Counter(P) + Counter(R) − Counter(C)`; any external-control mismatch; any
worker-07/OOD classification change; any live added finding not attributable to the patch's own
surface; null/overfire controls off; a naive 2-way reapply that does **not** revert C1's edit;
any pinned input drifting mid-run.

## Reproduce

```bash
cd <repo root>
python3 artifacts/worker-036/classsep_compose/build_composition.py   # rebuild both windows + controls
python3 artifacts/worker-036/classsep_compose/probe_compose.py       # 48 checks, exit 0 ⇔ PASS
python3 artifacts/worker-036/classsep_compose/make_checkpoint.py     # pin deliverables + inputs
python3 artifacts/worker-036/classsep_compose/emit_events.py         # upward events (append-only)
```

Inputs are read from `snapshots/` (hash-pinned in `CHECKPOINT.json`); canonical
`research_map/class_separation.py`, `research_map/research_map.json`, `ledger/theorems.jsonl` and
`runtime/state/artifact_hashes.json` are never written. No canonical patch is applied.

`probe_compose.py` is deterministic **modulo the `created_at` field**: two consecutive runs produce
identical checks and measurements (verified: only `created_at` differed between run 2 and run 3).
Because it rewrites `report.json`, packaging must run in the order above — a probe re-run *after*
`make_checkpoint.py` invalidates the pinned digest.

**Packaging note (self-reported):** the first `artifact` event
(`w036-compose-20260912T010500-artifact`, ingested 00:58:23) recorded the run-2 `report.json`
digest; an idempotence re-run at 00:59:01 then rewrote `report.json` changing only `created_at`,
and `CHECKPOINT.json` was re-pinned. The correction events
(`w036-compose-...-corr-artifact` / `-corr-status`) register the current full digests. No
measurement, check, or falsifier changed between runs.
