# W054-F1-REPAIR-VERIFY-01 — independent verification of the flash-15 F1 repair candidate

**Worker:** `worker-054` · **Node:** `F1` · **Class:** `AF-WCC-VAC-GEN` · **Gate:** `G-FORM`

**Verified pair (frozen snapshots):**

| role | original path | sha256 |
|---|---|---|
| pinned F1 rev11 | `schemas/af_wcc_vacuum.yaml` | `9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503` |
| candidate repair | `artifacts/flash-15/f1_wcc_visibility/repaired_proposal.af_wcc_vacuum.yaml` | `303705c46834ff4df23671b1cc965684e8cecdac2dc1e6daf999a0c1b0d055ac` |

**Report:** `report.json` sha256 `e07cc32ce087305ac5723470291a0aa84e3a3970b6c340c648674f2f4ea6275a`
**Tool:** `verify_repair.py` sha256 `8044a71105eb5655a974a6f3df73e9b75b5fba472909851c256d04c2093bd167`

## Verdict — `accept_scope_limited` (score 4.0)

The candidate is exactly the pinned rev11 bytes plus the three declared edits, and the repaired
`quantifiers.formal` is the exact negation of the class's canonical single-q **tail** visibility
predicate.

| Check | Result |
|---|---|
| V1 diff exactness | **pass** — 3 changed lines in 3 hunks, all declared; no collateral edits |
| V2 formal + D5 tail form | **pass** |
| V3 ordered binder chain | **pass** — only the final `not_exists` binder changed, to `(q,t0)`/D5 |
| V4 predicate references | **pass** — `conclusion.statement_formal` → `visible_singularity_from_I_plus` → D5 |
| V5 finite-model check | **pass** — 5580 models: old whole-curve reading mismatches 3906; tail reading 0 |
| V6 negation duality | **pass** |
| V7 residual containment scan | **warn** — `witness_protocol` step (4) keeps whole-curve wording (minor) |
| V8 binding hygiene | **warn** — candidate does not repair pre-existing duplicate `revised_at` keys or the authoring-tree `class_contract_pointer` |
| V9 gate | **warn** — `check_class_schema.py` recorded PASS at candidate time (`probe_report.json#e94e578d61ea`); re-running now fails R22 on the legacy key `revised_at_unused` because the checker's unpinned `KEY_MANIFEST` was tightened mid-session (tooling drift, not a defect of the repair) |
| V10 drift | **pass** — frozen snapshots stable across the run |

## Why this is still useful after rev12

The live canonical F1 moved to `b474fbc4…`/`cce9c601…` while this verification ran; the lead's
rev12 landed the same tail repair (independently checked in
`../f1_rev12_verify/report.json`, where the landed formal clause is byte-identical to this
candidate's). This report is the hash-bound check of the candidate that informed that repair,
reproducible from the snapshots at any later time.

## Falsifier

Re-run this tool in an unchanged tree. Falsified if (a) a pinned snapshot hash differs before vs
after, (b) the proposal differs in anything other than the three declared edits, (c) a reading is
exhibited under which the repaired `quantifiers.formal` is not equivalent to the negation of the
canonical tail predicate, (d) the repaired copy fails the canonical checker for a reason other
than the `KEY_MANIFEST` R22 drift, or (e) any residual R-1…R-4 stops reproducing at the pinned
bytes.

## Scope limit

Verifies one candidate repair for HF-06 at pinned rev11. Not a full schema accept, not a gate
verdict, not evidence about weak cosmic censorship. `counts_as_full_schema_verdict=false`;
`clears_binding_blockers=false`.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-054/f1_repair_verify/verify_repair.py    # exit 0
python3 artifacts/worker-054/f1_rev12_verify/verify_rev12.py      # exit 1 (R8 revise finding)
```
