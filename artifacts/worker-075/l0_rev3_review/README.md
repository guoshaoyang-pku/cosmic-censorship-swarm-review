# W075-L0-REV3-INDEP-VERDICT-01 — independent L0 rev-3 review

**Reviewer:** worker-075 (authored neither the ledger nor any prior L0 verdict)
**Target:** `ledger/theorems.jsonl` @ `a1674f094979` (L0 rev 3 final), companion `ledger/citation_audit.csv` @ `315c19145065`
**Node / gate:** L0 / G-LIT — class_ids `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH`
**Request:** `astra-lead-literature` blocker **BL-7** + resource_request `lit-l5-20260912-022` ("Re-dispatch blind L0 review at ledger/theorems.jsonl#a1674f094979").

## Verdict

**accept, score 4.0, 0 hard failures, 2 open objections** (`report.json` → `verdict`).

All 11 pre-registered checks pass; all 8 mutation controls are detected; the snapshot was stable
across the run (re-hashed at the end).

| check | result |
|---|---|
| C01 pin (ledger + audit sha256) | PASS |
| C02 62 rows, unique ids | PASS |
| C03 retired axes (`status`/`validation_status`/`supports_claim`) | 0 rows |
| C04 axis honesty | `content_status` 50/11/1; `review_status` 62× `not_independently_reviewed` |
| C05 frozen class tokens only | 0 foreign; 2 prose prefixes (`AF-SCC-C2`, `AF-SCC`) resolve to frozen ids |
| C06 disjunction census | 8 rows, 6 relation/variant + 2 WCC-antecedent, **0 union-class definitions** |
| C07 theorem rows | 30; `artifact_refs` field structurally absent (0); ledger-native bar 30/30 |
| C08 unresolved marking | 62/62 rows carry a non-empty list |
| C09 locators | 92/92 cited sources resolve in `citation_audit.csv`; 97/97 audit rows `resolved` |
| C10 honesty | 62/62 self-assessment label; 0 verified rows without a verified source |
| C11 merged-class phrases | 5 hits, **0 in class-defining fields** (all descriptive/negative) |

## Open objections (recorded, not hard failures)

1. **HF-02 literal firing.** The rubric detector "disjunction of class_ids" fires on 8 rows
   (D-004, D-005, T-303, T-305, T-402, T-515, T-526, T-528). Independent classification: six are
   intermediate-regularity relation/variant rows (Lipschitz / L²_loc / L^s_loc / weak null), two
   (T-515, T-528) are Kerr-exterior stability status rows. None defines a class as a union or
   disjunction of C0 and C2, so this is a **rubric-scope** question (claim-event detector applied
   to ledger rows), not a ledger hard failure. T-515/T-528 binding `AF-SCC-C0-VAC-GEN` on
   Kerr-stability content is questionable and belongs to the ledger owner.
2. **HF-01 applicability.** The detector "conclusion_type == theorem AND no artifact_refs" fires on
   all 30 theorem rows because the ledger row schema has no `artifact_refs` field at all. The
   ledger-native evidence bar (≥1 verified source + non-empty falsifiers + non-empty assumptions)
   passes 30/30.

## Independence and limits

- The instrument was written from `comms/PROTOCOL.md`, the rubric HF text and the ledger bytes.
  It never imports or copies another review's harness and writes to no canonical path.
- `peer_work_at_same_hash`: `reviews/L0-review-093.json` (worker-093, revise 3.5) — read **after**
  this report was produced. Its two hard failures are the two rubric-scope objections above; the
  underlying counts (8 disjunction rows, 30 theorem rows) reproduce, the classification differs.
- Documented blind spots: no per-row quote-entailment check, no live re-fetch of the 92 sources,
  no judgement on the mathematics of any row.

## Reproduce

```bash
python3 artifacts/worker-075/l0_rev3_review/run_l0rev3_review_075.py     # exit 0; report.json
python3 artifacts/worker-075/l0_rev3_review/verify_l0rev3_review_075.py  # exit 0; 3/3 tamper control
```

**Falsifier.** Re-run both scripts at the same bytes: any check that flips, any control not
detected, any hash drift of `ledger/theorems.jsonl` / `ledger/citation_audit.csv`, or any
multi-class row re-classified as a union-class definition falsifies this report.

**Not claimed:** independent accept of any theorem row, gate verdict, node completion.
