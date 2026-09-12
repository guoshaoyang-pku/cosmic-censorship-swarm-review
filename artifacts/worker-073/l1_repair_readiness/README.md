# W073-L1-REPAIR-READINESS-01 — independent verification of the staged L1 locator repair recipe

**Worker:** worker-073 (recycled slot; no inbox card exists, task self-selected from the REC-35 G-LIT
hold and worker-025's F5 staged-repair claim).
**Node / gate:** L1 / G-LIT. **Class scope:** the four frozen classes carried by the L1 rows
(AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN, AF-WCC-SCALAR-SPH); disjunctive and
`(evidence/tag only)` rows are bucketed, never assigned.
**Boundary:** read-only, offline. No canonical path written. No theorem, node status, gate verdict
or validation_status. No repair applied.

## Question

worker-025's locator adjudication (`artifacts/worker-025/l1_locator_adj/report.json#26f0071c558e`)
claims F5: *97/97 ledger rows have a record-identifier replacement drawn from the row's own
`evidence_url`/`url`/`doi`/`arxiv_id`*. That claim is decision input for
`astra-life05-verify-l0-final` (audit lead, 02:30), and had not been independently verified
end-to-end (worker-099 verified only the 10-row scalar class; my own spot check #4 covered rows
1–40). This task tests the recipe for all 97 rows with its own implementation.

## Frame (fail-closed, measured before and after)

| path | sha256 |
|---|---|
| `ledger/citation_audit.csv` | `315c19145065…` |
| `artifacts/worker-025/l1_locator_adj/report.json` | `26f0071c558e…` |
| `artifacts/worker-025/l1_locator_adj/run_l1_locator_025.py` | `1a2f6588be5c…` |
| `artifacts/literature/L0_L1_ACCEPTANCE.md` | `fde5600b45a5…` |
| `evaluation_rubric.yaml` | `d748a9e3574e…` |

The instrument exits 3 without writing a report if any pin does not match or moves mid-run.

## Result — `REPAIR_READY_WITH_RESIDUAL` (review verdict `accept`, 4.0)

| criterion | result |
|---|---|
| C1 coverage | 97/97 rows carry a proposal |
| C2 provenance (no invention) | 97/97 derivable from the row's own fields; **0 invented values** |
| C3 record identity | 97/97 single-record identifiers; 0 discovery queries / ellipses / bare values |
| C4 malformed-subclass closure | 27/27 `...` cells closed by a valid, distinct replacement |
| C5 class coverage | AF-WCC-VAC-GEN 12/12, AF-SCC-C2 4/4, AF-SCC-C0 4/4, AF-WCC-SCALAR-SPH 10/10 repair-ready; 26 disjunctive + 41 evidence/tag rows bucketed |
| C6 census reproduction | defective partition (27 TRUNCATED + 40 DISCOVERY) agrees per row, 67/67; 3 boundary disagreements reported (L1R-03) |
| C7 determinism | two runs byte-identical |
| controls | 9/9 fired (K1–K9), including the K6 positive control |

**So the recipe is mechanically complete and provenance-safe: the owner can apply it without
inventing any value, and every malformed cell gets a resolvable single-record identifier.**

## Findings for the audit lead

- **L1R-02 (material).** 37/97 replacements are single-record **metadata-API endpoints**, not primary
  pages: `inspirehep.net/api/literature/<id>` ×27, `api.crossref.org/works/<doi>` ×7,
  `api.openalex.org/works/doi:<doi>` ×3. Only 60/97 proposals are primary pages. Applying the recipe
  removes the "not a record locator" defect but does **not** restore the acceptance note's
  "primary page/record URL" property for those 37 rows. This does not by itself unblock L1 acceptance.
- **L1R-03 (finding).** worker-025's DIRECT/OTHER boundary is not independently reproducible on 3 rows
  (SRC-087, SRC-089, SRC-092): identical API-endpoint shapes are split inconsistently by the source
  classifier (crossref 5× DIRECT vs 2× OTHER; openalex 2× DIRECT vs 1× OTHER). The headline
  "26 record locators / 71 not" is boundary-dependent; the load-bearing defective partition is stable.
- **L1R-04 (info).** SRC-090's `exact_locator` has page annotation text appended to the URL; its
  replacement drops it and is a direct PDF.
- **L1R-05 (disclosure).** Run 1 under the v1 taxonomy returned `REPAIR_NOT_READY` because of two
  **instrument** defects (single-record API endpoints/PDF classified `FAIL_OTHER`; the K6 bare-identifier
  clause unimplemented). Run 1 is preserved at `report.run1-taxonomy-v1.json#5d00b75d7e70`; `amendment-1.json`
  records the change. No criterion about the data was relaxed.

## Reproduce

```bash
python3 artifacts/worker-073/l1_repair_readiness/run_check_073_l1repair.py
```

Exit 0 on READY decisions, 2 on NOT_READY, 3 fail-closed. Report sha256
`c12be6afaf25844ddcb3349b70d0a56fa98bd7a4812f07ffe7007d559cc0ce5e`.

## Falsifier

Any proposed locator not derivable from its own row fields; any discovery query, `...`, or non-record
proposal; any unclosed malformed cell; any per-row disagreement with worker-025 on a TRUNCATED or
DISCOVERY row; any unfired control; any frame move. A write to the ledger voids the binding for the
new bytes and requires a fresh round (CF-19 discipline).

## Limits

Offline structural validation only — no live HTTP resolution of proposed targets (worker-025/099
scope). Class binding (HF-02/A0) and ledger content correctness are not re-adjudicated.
