# W072-A — class-bound conformance & falsifier audit: `AF-WCC-SCALAR-SPH`

Bounded worker task (`worker=072`), taken from the frozen F0 taxonomy's own gap list:
**CG1** ("`AF-WCC-SCALAR-SPH` has no schema node (F-node) in `research_map.json`") and
**Q4** ("which literature statements … are actually theorems, with primary-source scope quotes
and hashes?"). No assignment card existed for `worker-072`; the task is taken, not issued.

## Deliverable

| file | what it is |
|---|---|
| `audit_scalar_sph.py` | deterministic, stdlib-only runner; fails closed on input-hash drift |
| `spotcheck_report.json` | machine-readable result: pins, per-entry classification, controls, locator audit, findings |
| `README.md` | this file |

Reproduce: `python3 artifacts/worker-072/scalar_sph_class_audit/audit_scalar_sph.py`

## Method

1. **Pins.** The run aborts unless sha256 of `research_map/formulation_taxonomy.yaml`,
   `ledger/theorems.jsonl` and `ledger/citation_audit.csv` match the revisions measured at
   task start. It did abort once (rc=2): the taxonomy was rewritten mid-task
   (`0fcc6a1928fd` → `276009f4f63d`). On re-measurement H1–H4 and the class
   `conclusion_type` were unchanged, so the run was re-pinned and repeated. The drift is
   recorded in `spotcheck_report.json.input_drift_observed_during_task` (finding W072-F4).
2. **Class definition** (F0, rev 4) is read from the taxonomy block: H1 massless scalar /
   Λ=0 / Einstein-scalar; H2 spherical symmetry; H3 asymptotically flat with one end and an
   MGHD; H4 an explicit genericity notion (taxonomy marks it *unresolved*, owned by L0/L1).
   The class conclusion predicate is `conclusion.type == weak_cosmic_censorship`.
3. **Bound population.** Every `ledger/theorems.jsonl` entry whose `class_ids` contains the
   class (10 entries) and every `citation_audit.csv` row whose `class_mapping` contains it
   (14 rows).
4. **Classification.** H1–H3 by token evidence in the entry's own text (label, exact
   statement, assumptions, regularity, topology, caveats); H4 by an explicit genericity
   notion token (dense-open / comeager / residual / full-measure / positive-probability)
   *not negated within 90 characters*; conclusion discharge by `conclusion_type`.
5. **Controls (the load-bearing part).** A detector that can only answer "no" is vacuous:
   - `CTRL-VACUUM` (T-101 mutated to vacuum, no scalar field) **must** fall out of H1 → observed `False`.
   - `CTRL-FULL-WCC` (T-101 mutated to `conclusion_type=weak_cosmic_censorship` + a comeager
     genericity clause) **must** discharge the conclusion → observed `True`.
   - `discriminating_power_ok = true`.
6. **L1 locator audit.** Each bound citation row is checked for a syntactically resolvable
   `doi` / `arxiv_id` / `url` locator.

## Result (at the pinned revisions)

```
entries bound                                 10
mechanically conform H1-H3                     5
genericity notion named (H4)                   0
discharge the class WCC conclusion             0
in-class evidence without the conclusion       5
citation rows bound / unresolvable locator    14 / 0
controls discriminating_power_ok              true
```

**Findings**

- **W072-F1** — The class is evidence-rich and conclusion-poor: 0/10 bound entries state the
  class's WCC conclusion; 5/10 are mechanically in-class (H1–H3) but carry an
  instability/obstruction or numerical result instead.
- **W072-F2** — H4 (genericity) is named in 0/10 bound entries, matching the taxonomy's
  `unresolved_pending_L1` status. With CG1 (no F-node owns the class) this makes any WCC
  conclusion for the class not yet stateable, independent of entry count.
- **W072-F3** — 14/14 class-bound citation rows carry a machine-resolvable locator; no
  locator gap in this class's slice of L1.
- **W072-F4** — F0 was rewritten on a minutes timescale during the task; verdicts must bind a
  measured sha256.

## Scope limits (explicit)

- Token evidence is *mechanical*, not a semantic reading of the papers. H1–H3 passes mean
  the entry's own metadata carries the hypothesis, not that the paper proves it.
- Only entries whose `class_ids` already include the class were classified; a mis-filed entry
  elsewhere in the ledger would be invisible to this audit (that is the W072-F1 falsifier's
  second clause).
- No gate verdict, no node completion, no theorem, no physics result is claimed
  (`validation_status: unverified`; workers cannot set `done`/`passed`).
- Nothing was written to `runtime/state/artifact_hashes.json` (controller-owned).

## Falsifier

Re-run at the pinned hashes: a different per-entry classification falsifies the table. More
sharply — produce one class-bound entry that (a) passes H1–H3, (b) names a genericity notion
with a stated data-space topology and primary-source scope, and (c) carries
`conclusion_type: weak_cosmic_censorship`; that entry falsifies the "conclusion-poor" finding
and would move the class from evidence-audit to schema-authoring.
