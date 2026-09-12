# W072-B — independent canonical-hash review of F2a (AF-SCC-C2-VAC-GEN)

Worker: `worker-072` (breadth worker, no assignment card issued).
Task taken from the formulation lead's resource request of `2026-09-12T00:20:09+08:00`
(independent reviewer for the final rev11 schemas) and from the F2a schema's own
`review_status.independent_reviewers: []` at the canonical hash.

**Target:** `schemas/af_scc_c2_vacuum.yaml`
`#b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2`
**Recommendation:** `accept` (mechanical class binding and separation; 12/12 checks,
4/4 mutants caught, positive control clean). Worker verdict only — it cannot set
`validation_status=passed` or a gate verdict.

## What was checked

| id | check | result |
|---|---|---|
| A1 | canonical schema bytes == authoring bytes (F1, F2a, F2b) | pass |
| A2 | `f0_binding.declared_f0_sha256` == measured canonical taxonomy hash `276009f4f63d` | pass |
| A3 | `class_contract_pointer` target exists and carries the class contract | pass |
| B1 | class identity (`class_id`, `node_id`, `regularity_token=C2`, `one_class_only`, `conclusion_type=scc_c2_future_inextendibility`) | pass |
| C1 | mutual `sibling_disjoint_from` with `AF-SCC-C0-VAC-GEN`, distinct class ids | pass |
| C2 | distinct conclusion tokens; no composite "C0 or C2" and no sibling conclusion token in ASSERTIVE paths | pass |
| C3 | exempt composite mentions occur only in tagged `anti_scope` (`phrases_that_are_not_this_class`) | pass |
| D1 | canonical map taxonomy vs lead contract supplement consistent on shared fields (F2a+F2b), independent re-implementation | pass |
| F1 | owner structural gate `check_class_schema.py --json` on the canonical F2a file: `pass`, 0 failed rules | pass |
| F2 | owner two-stage pipeline `run_acceptance.py --json`: `PASS` (mutant union 31/31) | pass |
| G1 | mutants C1–C4 all caught by the *same* checks | pass |
| G2 | unmodified copy passes: no false positive | pass |

Owner-harness replay is labelled as a replay, not as an independent derivation of
R01–R16. The semantic auditor (`artifacts/worker-06/spec_conformance_audit.py`) run
directly on the canonical file returns `accept`, rc 0.

## Negative controls (discriminating power)

| mutant | expected | observed |
|---|---|---|
| C1 conclusion_type ← C0 token | caught | caught (shared token + sibling token asserted) |
| C2 `sibling_disjoint_from` removed | caught | caught |
| C3 `regularity_token` ← C0 | caught | caught |
| C4 "C0 or C2" injected into `scope_statement` | caught | caught |
| C5 unmodified copy | clean | clean |

## Findings (all non-blocking, recorded; none falsifies class binding)

- **N1** duplicate top-level YAML key `revised_at` ×8 in F2a (×8 in F2b): strict YAML
  parsers reject the file; PyYAML keeps the last value, so the effective timestamp is
  parser-dependent. Repair: keep one `revised_at` plus a changelog list.
- **N2** effective `revised_at = 2026-09-12T00:30:00+08:00` post-dates the file mtime
  (`00:19:14`) and wall clock at review time; `revision: 11` has no timestamp of its
  own (rev10's is last-wins). Consistent with the pre-existing future-dating note
  (CF-14); hash binding, not prose time, is authoritative.
- **N3** `review_status.independent_reviewers` was empty at this hash before this
  review (requested: `deepseek-flash-18`, `astra-lead-audit`).
- **N4** cross-tree taxonomy drift (`276009f4f63d` canonical vs `c8e979a1eb48`
  supplement) is pre-existing and not an F2a defect: A2 binds the canonical path and
  D1 re-checks shared fields.

## Scope limits

Mechanical class binding/separation only: no mathematical or physical correctness, no
citation-scope verification (L1 owns it), no semantic reading of prose beyond the
assertive/exempt partition. Owner tooling was replayed, not re-derived. Canonical path
only; the authoring tree is used solely for byte-equality and consistency checks.

## Falsifier

A C0 datum satisfying the C2 schema, a `conclusion_type` shared with C0, a composite
"C0 or C2" regularity in an ASSERTIVE path, any pin drift, or any of the mutants C1–C4
passing these checks falsifies this review. Re-run is deterministic apart from
timestamps; `result_digest` (below) is the stable comparison key.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-072/f2a_independent_verification/verify_f2a_c2.py
# rc 0 = accept, 1 = revise, 2 = pin drift (fail-closed, no verdict)
```

## Artifact hashes

| artifact | sha256 |
|---|---|
| `verify_f2a_c2.py` | `d3745e0013a7aced27aa8532372267d5143f3af3fbd1cc8a6c30d14b38579918` |
| `f2a_independent_report.json` | `08497afa0bbac5d9d6f4f200ec92eae85099cfe091595febae450a1d69f9337f` |
| `README.md` | see the artifact event |

`result_digest` (over checks, controls, measured pins): `6b9f7c24bc656f9e2326db71c57c42444c19b9ed26f5fb29e22df7af85471c6a`.
