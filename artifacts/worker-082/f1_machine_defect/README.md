# worker-082 / f1_machine_defect

**Task:** `W082-F1-MACHINE-DEFECT-VERIFY-01` — independent machine data-integrity and binding verification
of F1 (`schemas/af_wcc_vacuum.yaml`, class `AF-WCC-VAC-GEN`), node F1, gate G-FORM.

**Verdict:** `revise` (data integrity / binding) at sha256
`9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503`.
`counts_as_full_schema_verdict: false` — this is **not** a G-FORM accept and cannot move the gate.

## Contents

| file | role |
|---|---|
| `run_checks.py` | reproducible checker; exit 1 iff a blocking machine defect is confirmed |
| `evidence.json` | machine-readable results, 9 checks with exact line numbers and measured hashes |
| `frozen_f1_9a8bd4c96800.yaml` | byte-identical frozen copy of the reviewed revision (binding bytes) |
| `VERIFY-F1-082.json` | verification record (reviewer, hashes, findings, falsifier, stop rule) |
| `FIX-PROPOSAL-082.md` | advisory mechanical fix for the owner (lead-formulation); not applied |
| `emit_w082_events.py` | schema-validating, idempotent outbox emitter |

## Reproduce

```bash
cd <repo>
python3 artifacts/worker-082/f1_machine_defect/run_checks.py --out /tmp/rc.json; echo "exit=$?"
```

Exit 0 means no blocking machine defect (i.e. the artifact was revised). Exit 1 at the frozen hash is
expected. Checks `W082M-01..06, 08, 09` are deterministic functions of the bytes; `W082M-07` is a
timestamped snapshot of the live `reviews/` corpus and may grow between runs.

## Confirmed blocking defects at the reviewed hash

- `revised_at` duplicated 7x (lines 8,10,12,14,16,20,23); PyYAML last-wins keeps only `00:30:00`, silently
  discarding six revision stamps, so `revision: 11` is unverifiable.
- `revised_at_unused` duplicated 2x (lines 26,28) and dead.
- effective `revised_at` and `f0_binding.checked_at` are 119 s ahead of the wall clock at check time.
- `class_contract_pointer` / `class_contract_supplement` resolve to the authoring tree
  (`artifacts/formulation/formulation_taxonomy.yaml`, measured `c8e979a1eb48`) instead of the declared
  canonical `research_map/formulation_taxonomy.yaml` (`276009f4f63d`).
- `review_status.independent_reviewers: []` while 9 hash-bound verdicts exist (0 accepts).

The D0 disjunction is recorded as **syntax only**; the "family of two class statements" reading is inherited
from worker-088 / lead-audit r2 and was not independently adjudicated here.
