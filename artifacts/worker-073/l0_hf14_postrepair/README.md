# W073-L0-HF14-POSTREPAIR-01 — independent check of the L0 rev-3 HF-14 closure

- **Author:** `worker-073` (bounded execution worker, instance `worker-073-20260912T002948-968807`)
- **Node:** L0 (`ledger/theorems.jsonl`) · **Gate:** G-LIT · **Status:** worker evidence, `validation_status: unverified`
- **Class coverage:** per-class census over all 62 rows — `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`,
  `AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH`, plus 28 pre-existing unbound rows (BL-6)
- **Canonical files untouched.** This worker wrote only its own artifact directory, the outbox and
  the checkpoint. No node status, no gate verdict, no ledger edit.

## Why this task

The literature lead's rev-3 repair (`artifacts/literature/reviews/L0-rev3-hf14-repair.json`)
renamed the L0 acceptance vocabulary (`ce42d205e761` → `3e3d35531421`) and asserts HF-14
(`self_certified_acceptance`, critical) closed. Its own resource request
(`lit-l5-20260912-013`) names two missing items: *"the first independent read of the rev-3 delta
and the first check of whether the HF-14 predicates really return 0."* This artifact supplies
both, by an own implementation of the detector text.

## Method

Detector written from `evaluation_rubric.yaml:243-252` only — no import of
`artifacts/audit/audit_lib.py`, no use of the lead's repair tool. Acceptance markers:
`status == "accepted"`, `validation_status == "passed"`, `supports_claim is True`. Three readings:
R1 literal-weak (no verdict *field* and no hash *field*), R2 strict (no identity-bearing verdict
and no path-anchored sha256), R3 any-absence (harshest).

**Certified revision:** the archived rev-3 bytes
`artifacts/literature/archive/theorems.rev3-handpatch-20260912T003026.jsonl`, hash-verified
`3e3d35531421…` — identical to the `after_sha256` in the lead's repair record.

**Moving target observed:** the live `ledger/theorems.jsonl` matched `3e3d3553` when this task's
first run passed its pin check (~00:33) and had moved to `a1674f09…` by 00:35:19, when the second
run failed closed. The verdict is therefore bound to the archive; the live file is probed at start
and end and reported as `observed_not_certified` only.

## Result

| revision | rows | `status=accepted` | `supports_claim=true` | any marker | R1 | R2 | R3 |
|---|---:|---:|---:|---:|---:|---:|---:|
| pre-repair `ce42d205` | 62 | 50 | 60 | **60** | 60 | 60 | 60 |
| rev-3 `3e3d3553` (certified) | 62 | 0 | 0 | **0** | 0 | 0 | 0 |
| live `a1674f09` (observed only) | 62 | 0 | 0 | 0 | 0 | 0 | 0 |

- **Status: `CONFIRMED_CLOSED`** for HF-14 at certified rev-3 `3e3d3553`.
- Positive control on the data: pre-repair exposure reproduces the lead's disjunctive figure
  60/62 (the repair record's `hf14_rows_closed: 50` counts only the `status=accepted` arm;
  `supports_claim_withdrawn: 60` matches).
- Delta census: 62 rows changed, and **only** in acceptance-vocabulary fields
  (`acceptance_authority` ×62, `review_status` ×62, `status` ×50, `status_note` ×50,
  `supports_claim` ×60, `supports_claim_basis` ×60). **0 claim-bearing field changes**
  (`statement_exact`, `class_ids`, `source_ids`, assumptions, quantifiers, topology, … all
  byte-preserved); 0 unexpected new fields.
- Integrity: all `source_ids` still resolve in L1 (`315c1914`, 97/97 unique); `class_ids`
  unchanged on every row.
- Per-class pre-repair exposures (sum 60): WCC 9/18, C0 3/6, C2 4/8, C2;C0 4/8, C0;C2 2/4,
  WCC;C0 2/4, SCALAR-SPH 10/20, unbound 26/28.
- Controls: **8/8 pass**, including author-named verdict does not clear (R2), placeholder verdict
  without hash still fires, bare-hash-without-path does not clear strict, and deterministic re-run.

## Residual risk (decision-relevant, not the literal reading)

- **Counterfactual:** if a lead rules that the renamed statuses `included_unreviewed` (50) and
  `provisional` (11) still count as acceptance vocabulary, **61** rows would remain exposed. The
  detector's literal text does not name those statuses; this number is reported so the ruling can
  be made explicitly rather than by vocabulary drift.
- No row carries `validation_status` or `verification_status == passed`.
- Pre-existing and **not** introduced by rev 3: 28 unbound class rows and 8 rows with two frozen
  classes (open blocker BL-6); L1 locator resolvability (BL-4) is out of scope here.

## Reproduce / falsifier

```bash
python3 artifacts/worker-073/l0_hf14_postrepair/run_check_073.py   # exit 0 only on CONFIRMED_CLOSED
```

Fail-closed on any certified pin mismatch. **Falsifier:** a re-run at the pinned hashes that
fails any control, yields a nonzero rev-3 R1/R2/R3 count, finds a claim-bearing delta field, or
breaks an L0→L1 source reference. A different archive hash voids the binding rather than
contradicting the finding. This verdict is scoped to HF-14 closure + delta preservation at
`3e3d3553`; it is **not** a full L0 review, **not** a gate verdict, and **must not** be counted as
a G-LIT accept.
