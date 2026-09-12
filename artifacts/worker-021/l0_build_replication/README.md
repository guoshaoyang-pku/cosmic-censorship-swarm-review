# W021-L0-BUILD-REPL-01 — the L0 rev-3 canonical pair is byte-exactly reproducible

Bounded worker task taken from the live G-LIT critical path (no inbox card existed for
worker-021). The literature lead's own published falsifier for the rev-3 repair
(`lit-l5-20260912-019`) is:

> Re-run `build_literature.py`: it must exit 0 and the emitted ledger must still carry 0 rows
> with `status`/`supports_claim`/`validation_status`. Then re-run `artifacts/audit/audit_run.py`:
> if `ledger/theorems.jsonl` or any of the nine `theorems/batch-*.jsonl` files reappears in the
> HF-14 file list, the repair failed.

This bundle executes that falsifier independently: it runs the **pinned hardened builder**
(`artifacts/literature/tools/build_literature.py#a497a968638f`) in throwaway sandboxes over the
source-of-truth batches and compares emitted bytes to the canonical pins, then mutates sandbox
copies to prove the guards fail closed.

## Result (measured, not asserted)

Pinned snapshot: `ledger/theorems.jsonl#a1674f094979`, `ledger/citation_audit.csv#315c19145065`,
builder `#a497a968638f`, 63 pinned input/output paths, **zero drift during the run**.
20/20 checks PASS; worker-level verdict **ACCEPT** (reproduced).

| check | expected | observed |
|---|---|---|
| pristine sandbox A build (twice, independent copies) | rc 0 | rc 0 |
| emitted L0 ledger vs canonical `a1674f094979` | equal | **equal** |
| emitted L1 citation audit vs canonical `315c19145065` | equal | **equal** |
| build determinism (A vs B) | equal | **equal** |
| emitted rows / unique theorem_ids | 62 / 62 | 62 / 62 |
| emitted content tier census | 50 verified / 11 provisional / 1 rejected | **50 / 11 / 1** |
| rows carrying an HF-14 forbidden key (`status`, `validation_status`, `supports_claim`) | 0 | **0** |
| rows truthfully marking the review axis absent | 62 | **62** |
| HF-14 on emitted ledger (frozen A0 detector **and** independent re-implementation) | 0 / 0 | **0 / 0** |
| HF-14 on pre-rev3 archive `ce42d205` (positive control) | ≥1 | **60 / 60, identical ids** |
| forbidden-key mutation of a copied batch row | rc≠0, guard, no ledger written | **rc 1, guard, no ledger** |
| non-frozen `class_id` mutation | rc≠0, guard, no ledger written | **rc 1, guard, no ledger** |

**Conclusion.** At the pinned hashes, the canonical L0/L1 pair is exactly what the pinned
builder emits from the batch inputs: the "build product, not a hand-patch" claim survives
independent replication, and the HF-14 repair is durable (the guard fires before any output is
written). This closes the literature lead's stated build-replication falsifier at this snapshot.

## Secondary result — A0 HF-14 corpus recount (independent confirmation of lit-l5-021)

At T0, the frozen A0 corpus reader over `artifacts` + `comms/outbox` + `ledger`
(4403 files, 1935 ledger-shaped records) yields **586 HF-14-affected records across 12 files —
every one an archive, incoming, or worker snapshot of pre-rev3 bytes. Zero canonical or live
build-input files fire.** Eight of the twelve are exactly the files named in
`lit-l5-20260912-021`; four are newer snapshots written after that blocker
(`worker-029` ×2, `worker-036`, `worker-097/l0_rev4`). This confirms the blocker's diagnosis
(detector scope, not content) and shows the artefact class is still growing with every
pre-rev3 snapshot an agent retains.

## Two advisory defects found in the pinned builder (non-pinned outputs)

1. **`build_literature.py` is not self-contained on a clean tree** (control R5c): it writes
   `artifacts/literature/classes/<cid>.md` without creating that directory, so a checkout
   without `classes/` aborts *after* emitting L0/L1. Canonical bytes are unaffected; author-side
   `mkdir` or documentation fix.
2. **Class dossiers mis-count content status** (`build_literature.py:346` compares
   `content_status == 'accepted'`, a value the same builder rejects at `:200-201`), so every
   generated `classes/*.md` line reports "0 accepted" regardless of the real census. Non-pinned
   output, author-side fix.

## Method

1. Pin sha256 of 63 inputs/outputs (canonical L0/L1, builder, all 11 source batches, all 10
   theorem batches incl. the empty one, `FROZEN.json`, `audit_lib.py`, `audit_run.py`).
2. Build in two independent sandboxes that mirror the canonical tree layout; the canonical
   paths are never written.
3. Compare emitted `ledger/theorems.jsonl` and `ledger/citation_audit.csv` against the
   canonical pins and against each other.
4. Run the frozen A0 HF-14 detector (imported from `audit_lib.py#ae573db84631`) and an
   independent re-implementation of the rubric text on: a pre-registered 8-row synthetic
   battery, the pre-rev3 archive (positive control), and the emitted ledger.
5. Mutation controls: forbidden key, non-frozen class token, missing `classes/` directory.
6. Recount the A0 HF-14 corpus; then re-verify (R6c) that this task's own artifacts are
   corpus-neutral (no `theorem_id`-shaped fixtures, no retained ledger copies).
7. Re-pin all 63 paths after the run; any drift voids (exit 3) instead of falsifying.

## Files

| file | role |
|---|---|
| `replicate_l0_build.py` | fail-closed instrument (stdlib only; read-only on canonical paths) |
| `report.json` | pins, 20 checks, emitted census, HF-14 differential, corpus recount, findings |
| `controls.json` | synthetic HF-14 battery, mutation controls, archive positive control, drift |
| `raw/entry_hashes.json` | 63 T0/T1 pin hashes + emitted hash records |
| `raw/emitted_*_*.sha256` | emitted-bytes hashes only (no ledger copy: a retained copy would duplicate 62 canonical records into the A0 corpus) |
| `README.md` | this document |

Reproduce:

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-021/l0_build_replication/replicate_l0_build.py
```

## Scope and authority

Applies only to the build-replication property at the pinned hashes. It does not adjudicate the
ledger's content, class binding, HF-02 disjunctions, citation support, source scope, or any
physics claim; it does not edit any canonical artifact, claim, review, map, or detector; it sets
no gate verdict, node status, or validation promotion. Worker-level `ACCEPT` means "the
replication claim reproduced" — L0 review dispatch and any G-LIT disposition belong to the
literature lead and the controller.

## Falsifier

Re-run at the same pins. Falsified if (a) a pristine sandbox build does not reproduce
`a1674f094979` for `ledger/theorems.jsonl` or `315c19145065` for `ledger/citation_audit.csv`;
(b) two pristine builds disagree; (c) the forbidden-key or non-frozen-class mutation does not
make the builder exit non-zero with no ledger written; (d) the pre-rev3 archive positive control
does not fire; or (e) any pinned input/output drifts during the run (void, not falsified).
