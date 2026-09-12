# W025-L0-HF02-STAGED-REPAIR-01 — staged, verified candidate for the L0 class_ids disjunction

Worker: `worker-025` (bounded execution worker). Node `L0`, gate `G-LIT`.
Classes touched: `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`, `AF-WCC-VAC-GEN`.

## Why this exists

At the measured ledger revision `ledger/theorems.jsonl#a1674f094979` (62 rows),
`worker-023` produced an un-applied HF-02 proposal
(`artifacts/worker-023/l0_hf02/hf02-disjunction-adjudication-023.json#0f86158c5bb7`):
eight rows carry more than one frozen class token in `class_ids`, and the packet
recommends per-row dispositions (variant-informs / relation-informs / WCC-only).
No staged revision with an acceptance test existed. This packet supplies one —
as a **candidate only**: the live ledger was read, never written.

## What was done

1. **Fail-closed pins.** Five inputs are hash-pinned; the build aborts on any drift
   (`ledger a1674f094979`, adjudication `0f86158c5bb7`, `VARIANT_REGISTRY 5eb42f9a384a`,
   `evaluation_rubric d748a9e3574e`, `formulation_taxonomy 0abb9ed8a961`).
2. **Independent detector.** Re-implemented the rubric-literal HF-02
   "disjunction of class_ids" test (a row with >1 frozen class token). It returns
   exactly the eight rows `D-004 D-005 T-303 T-305 T-402 T-515 T-526 T-528`,
   matching worker-023's set — independent agreement, not copied.
3. **Mechanical application** of the eight `set` ops to a worker-owned staged copy
   (`staged/theorems.hf02-staged.jsonl`, sha256
   `b3ab6a1a635720a97e51fd332bcf1d9f9e6fdc45ad64d886106f1cd298d61cea`, 62 rows).
4. **Acceptance + controls** (`report.json`, 14/14): row set and order unchanged;
   HF-02 disjunctions 8 → 0; every non-target field byte-identical; all class tokens
   frozen; `class_ids ∩ informs_classes = ∅`; idempotent; four negative controls
   (re-introduced disjunction, row loss, statement tamper, unknown row) all flip as
   declared, plus the live ledger as the disjunctive baseline.

## What is *not* claimed

- No gate verdict, node status, `validation_status=passed`, or claim re-adjudication.
- The **dispositions are worker-023's**, not re-derived here; this packet verifies
  only that applying them is mechanical, scoped, and regression-free.
- Adoption is **conditional on the audit lead's HF-02 scope ruling**: the same
  detector text also matches multi-class routing arrays in accepted claim *events*
  (worker-023 counted 76); that surface is untouched here.
- Adopting the staged bytes changes the ledger hash, so it requires an announced
  artifact event and a lead/controller re-pin (CF-19 discipline). This worker did
  **not** move the live path; it remains `a1674f094979`.

## Reproduction

```bash
python3 artifacts/worker-025/l0_hf02_staged/build_and_verify.py
# -> verdict=STAGED_REPAIR_VALIDATED_CONDITIONAL_ON_HF02_SCOPE_RULING acceptance=14/14
```

## Files

| path | sha256 (prefix) |
|---|---|
| `build_and_verify.py` | `79a393c98b3ad140` |
| `report.json` | `46d98ec27dea7fb5` |
| `staged/theorems.hf02-staged.jsonl` | `b3ab6a1a635720a9` |
| `staged/diff.json` | `241b493611c04372` |

Next falsifier: apply the staged bytes at the pinned anchor and find any remaining
HF-02 disjunction, any change outside `{class_ids, informs_classes, ledger_tags}`,
any dropped/reordered row, or a live-ledger hash other than `a1674f094979`.
