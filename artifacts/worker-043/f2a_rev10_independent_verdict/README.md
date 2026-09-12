# W043-F2A-INDEP-VERDICT-01 — independent verification of canonical F2a (AF-SCC-C2-VAC-GEN)

Worker 043, 2026-09-12. Read-only. Evidence only: this is **not** a gate verdict and it sets
no node status or `validation_status`.

## What was verified

| item | value |
|---|---|
| canonical artifact | `schemas/af_scc_c2_vacuum.yaml` |
| sha256 | `b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2` |
| schema revision field | 10 |
| FROZEN manifest | revision 25, sha256 `af24e9c39606…`, lists the same hash |
| stability | changed twice before 00:19:15 (+08:00), then stable through 00:22:36; verified bytes = frozen rev25 bytes |
| sibling hashes | F1 `9a8bd4c96800…`, F2b `1bb78ce9b357…`, taxonomy `276009f4f63d…` |

Main result: `report.json`. Raw instrument outputs: `raw/`. The exact bytes checked are in
`snapshot/` (so the analysis stays reproducible even if the canonical path moves).

## Findings at this hash

1. **HF-A1 resolved.** The dangling `extension_predicate` is gone: top-level block at line 91
   (`proper_future_extension_in_class`) with clauses (a)–(f) at lines 98–103; the D3
   `definition_ref` resolves. Probe `S7-C2` = pass.
2. **HF-A2 resolved.** `D0`–`D3` are all defined (lines 56–68). The formal, ordered, negation
   and negation-normal-form renderings are duals of each other; the earlier
   forall-vs-exists contradiction is gone.
3. **Probe `S5` is a false positive.** The only `'c0 or c2'` occurrences are entries in
   `anti_scope.phrases_that_are_not_this_class` (F2a line 280, F2b 283, F1 294). The probe's
   negation heuristic misses `not_this_class` because `_` is a word character.
4. **Probe `S6` still fires — open scope question.** The class sentence is uniform over `D0`
   (admissible `(s,delta)` pairs). It is now defined and internally consistent, and F1/F2b use
   the identical prefix and `D0` core, so this is a design decision ("one class vs a family
   over data regularity") for the lead/reviewer, not a dangling reference. The binding gate
   does not flag it.
5. **Shared data-class core confirmed.** F1/F2a/F2b share the same quantifier prefix, `D0` core
   and numeric `s`/`delta`. Only annotations differ (F1 adds "(weighted Sobolev)" and an
   L1-ownership clause). Conclusion clauses differ by design.
6. **Tooling green at this hash.** `check_class_schema.py` = pass (0 failed rules); the
   two-stage acceptance pipeline = PASS (3/3 canonical schemas pass both stages, union catches
   31/31 mutants, 2/2 controls, fixtures regenerated at base `1bb78ce9`). During this review the
   first acceptance invocation failed closed on stale rebased fixtures; the owner regenerated
   them mid-review and the re-run passes.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
SNAP=artifacts/worker-043/f2a_rev10_independent_verdict/snapshot
D=artifacts/worker-043/f2a_rev10_independent_verdict
python3 artifacts/formulation/tools/check_class_schema.py --json $SNAP/af_scc_c2_vacuum.yaml
python3 artifacts/formulation/tools/run_acceptance.py --json
python3 artifacts/worker18/f2_review/f2_class_probe.py --c2 $SNAP/af_scc_c2_vacuum.yaml --c0 $SNAP/af_scc_c0_vacuum.yaml --report /tmp/probe.json
python3 $D/check_f2a.py --f2a $SNAP/af_scc_c2_vacuum.yaml --c0 $SNAP/af_scc_c0_vacuum.yaml --f1 $SNAP/af_wcc_vacuum.yaml --out /tmp/check.json --expect-f2a-sha256 b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2
```

Falsifier and scope limits are in `report.json`. Nothing outside
`artifacts/worker-043/` was modified.
