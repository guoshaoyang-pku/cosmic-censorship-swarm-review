# W021-A0-HF03-REPL-01 — independent replication of the A0 HF-03 live finding

**Worker:** worker-021 (bounded execution slot) · **Node:** A0 · **Gate:** G-AUDIT
**Classes:** AF-WCC-VAC-GEN · AF-SCC-C2-VAC-GEN · AF-SCC-C0-VAC-GEN
**Verdict:** `REPLICATED_WITH_DISCREPANCIES` (23/23 controls PASS, 0 pin drift, not void)

Read-only on every canonical path. No gate verdict, no node transition, no claim/ledger write,
no detector or rubric edit. Dispositions remain with the controller, A0 and the literature lead.

## Object under test

| item | pinned at |
|---|---|
| adjudication artifact | `evaluation/A0_detector_scope_adjudication.json#a26be4b85706` (00:53:51) |
| rubric | `evaluation_rubric.yaml#d748a9e3574e` |
| blocker b2 (audit lead) | `comms/outbox/astra-lead-audit.jsonl#audit-l06-b2-hf03-live-20260912T005926` |
| blocker b3 (audit lead) | `comms/outbox/astra-lead-audit.jsonl#audit-l06-b3-staging-20260912T005926` |

All 27 file pins declared by the adjudication still resolved byte-exactly at run time
(`declared_pin_drift = 0`, `end_pin_drift = 0`).

## What was done

An independent, stdlib-only instrument (`replicate_a0_hf03.py`) re-implements from the documented
routing rule and the rubric text — importing no author code — (a) corpus enumeration over
`artifacts`, `comms/outbox`, `ledger`; (b) the citation/record routing predicate; (c) the
implemented HF-03 predicate; (d) the **literal rubric HF-03 branch** as a separate arm; (e) the
implemented HF-14 predicate; (f) the declared scope taxonomy. It is deterministic (K16) and
fail-closed on drift.

## Results — HF-03 (implemented predicate: citation lacks `source_meta` scope keys)

| scope | records | files |
|---|---:|---:|
| kept: 11 live sources batches | 97 | 11 |
| kept: live emitted `registry.jsonl` | 97 | 1 |
| **kept total** | **194** | **12** |
| excluded: `archive/batch-10.pre-L2-…` (10) + `incoming/w07-sources.jsonl` (7) | 17 | 2 |
| staging: `worker-07/…/batch-w07-sources.jsonl` | 7 | 1 |
| before-total | 218 | 15 |

The audit lead's **194/97/97 live count replicates exactly**, as do all per-file counts, the
excluded set and the staging count (`hf03_kept`, `hf03_excluded`, `hf03_staging`, `hf03_totals`
all agree).

## Results — rubric-scope arm (the part the 194 does not establish)

`evaluation_rubric.yaml` HF-03 (`unsupported_citation`, **critical**) is: *claim cites a citation
whose `resolution_status ∈ {unresolved, contradicted}` **or whose class metadata mismatches the
claim's class***. The implemented predicate is a different thing: *absence* of scope metadata
(no `matter_model`/`cosmological_constant`/`dimension`/`symmetry`, no `formulation`), emitted at
severity **`major`**.

| literal rubric branch | kept (live) | excluded | staging |
|---|---:|---:|---:|
| `resolution_status ∈ {unresolved, contradicted}` | **0** | 2 | 2 |
| class-metadata mismatch | 0 | 0 | 0 |
| absent metadata → non-evaluable as a mismatch | 194 | 15 | 5 |

**0 of the 194 kept-live rows satisfy the rubric's literal HF-03 predicate.** They are a
citation **metadata-completeness** deficit (real, and worth repairing) detected by a
`major`-severity implementation predicate that the rubric does not name as HF-03. The A0 gate
arithmetic keys on `critical` severity, so "194 HF-03 findings" is not supported as stated at
these bytes. The only two `unresolved/contradicted` citations in the corpus live in the excluded
`incoming/` copy and its staging twin.

## Results — staging claim b3 is misstated

Blocker b3 says the two worker-07 staging files carry "12 HF-14 records and **1 HF-03 record**".

* HF-14: **12 records** in `batch-w07-theorems.jsonl` — reproduced.
* HF-03: **7 records** in `batch-w07-sources.jsonl` — the adjudication artifact's own
  `hf03.staging_unresolved` says 7; b3 says 1. Measured and hash-pinned: **7**.

## Results — HF-14 after-scope total is not stable (new live finding)

The adjudication records `hf14.after_total_records = 0` and rules HF-14 a pure scope artifact.
Re-measurement finds a **new live-scope HF-14 surface** written after the 00:53:51 measurement:

| file | class | firing records | sha256 |
|---|---|---:|---|
| `artifacts/worker-037/rev13_coverage_rebind/rerun/theorems.augmented_status.jsonl` | `live_other` | **50** | `ce00cfa3f6bb` |

* 62 rows, 50 with `status: "accepted"` / 12 `withdrawn`; all 62 `review_status:
  not_independently_reviewed`; no reviewer-verdict field (`reviewer_verdicts`/`review_verdict`/
  `reviewed_by`); no artifact hash.
* It is **kept** by the adjudication's own predicate (K18) — the taxonomy has no class for a
  worker `rerun/` output, so it falls to `live_other`.
* Each firing row is a literal rubric HF-14 form: `status=accepted` with no independent reviewer
  verdict and no artifact hash (K19).
* **Most plausibly it is a control fixture, not a live acceptance record**: the author's
  `REPORT.md` documents control C1 as "add only `status: accepted` to a *copy* of the live ledger
  … (62 rows touched)", and the sibling files are named `*.c1_augmented` / `*.c4_mutated`. But the
  file is **not named** in the author's report or controls text (independent context probe,
  `author_declares_role=false`), is **not named in any other agent's outbox**
  (`named_in_other_agent_outbox=false`; it is hash-declared only inside the author's `SHA256SUMS`,
  K21), and was rewritten repeatedly (mtime 01:05:38 → 01:07:31) with stable bytes
  `ce00cfa3f6bb` (K20). A reviewer or detector cannot tell it apart from a live artifact under the
  declared taxonomy.

So the HF-14 "after scope = 0" result is a property of one instant, not of the predicate: it holds
only because this fixture did not exist at 00:53:51, and the taxonomy has no class for worker
counterfactual/mutation outputs. The canonical-ledger-clean part of the ruling still holds (mine
reproduces 0 fires on `ledger/theorems.jsonl`).

Measured corpus at run time: 8001 scanned `.json/.jsonl` files, 218 routed citations, 2617
routed records (vs 5067/218/2070 at the 00:53:51 instant — the tree grew under the measurement).

## Controls (23/23 PASS)

Positive/negative fixtures for both HF-03 arms (K1–K3, K14–K15), HF-14 (K4–K6), routing and
fixture exclusion (K7, K8, K8b), the full scope taxonomy (K9–K13), determinism (K16), declared-pin
drift (K17), the three new-live checks (K18–K20), and author-pin agreement (K21). Two controls
document field-name sensitivity: the HF-14 implementation recognizes `review_verdict`, **not** the
natural `reviewer_verdict` (K6b), so a row carrying `reviewer_verdict` still fires; the corpus
currently contains no `reviewer_verdict`/`review_verdict`/`reviewed_by`/`reviewer_verdicts` fields
at all (measured field census).

## Discrepancies recorded (not gate actions)

1. b3 staging HF-03 count: claims 1 record, measured 7 (artifact itself says 7).
2. HF-14 after-scope total: declared 0, measured 50 records in a post-measurement worker file
   classified `live_other` and kept by the declared predicate (control-fixture context above).
3. Declared `hf14` aggregate totals differ as a consequence (declared 586→0; measured 696→50).
4. Classification/severity gap: the 194 kept-live rows are rubric-scope `major`
   metadata-completeness hits under the implementation, not demonstrated rubric `critical` HF-03.

## Falsifier

Re-run at the same pins: **falsified** if the kept-live HF-03 count is not 194 (97 registry + 97
across the 11 batches), if the staging HF-03 record count is not 7, if the kept-live literal
rubric HF-03 count is not 0, or if any control fails. **Void** if any of the 27 declared file
pins, or the rubric / adjudication / audit-outbox inputs, move.

## Reproduce

```bash
cd <repo>
python3 artifacts/worker-021/a0_hf03_replication/replicate_a0_hf03.py
# exit 0 = complete; 2 = VOID (pin drift); 3 = control failure
# writes results.json, report.json, controls.json, raw/inputs_sha256.json under this directory
```

## Explicit non-claims

This is an instrument/checker-calibration measurement (`conclusion_type: formal_model`), not a
mathematics or physics claim and not a second A0 verdict. It does **not** rule that the missing
scope metadata should not be repaired, does **not** adopt or reject the scope predicate, does
**not** dispose of worker-037's file, and does **not** move G-AUDIT or any node status.
