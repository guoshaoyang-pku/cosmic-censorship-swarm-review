# W097-CF32-ACCEPTANCE-REPRO-01 — pre-registration

- **worker:** worker-097 (bounded execution slot)
- **written:** 2026-09-12T01:2x+08:00, BEFORE any fixture is rebased or any gate is run
  for this task (the only prior action was a single read-only reconnaissance invocation of
  `run_acceptance.py` at ~01:21 whose stdout was already quoted in the controller's CF-32).
- **node:** F2b / F2a (acceptance corpus is the C0 schema-derived corpus; C2 arms enter via
  the held-out/stage-B suite) — **gate:** G-FORM
- **class_id:** `AF-SCC-C0-VAC-GEN` (primary, corpus base); `AF-SCC-C2-VAC-GEN` (secondary)
- **authority:** worker evidence only. No gate verdict, no node status, no
  `validation_status=passed`. No canonical write.

## Question

CF-32(i) asserts the G-FORM evidence pipeline is not reproducible at the rev29/rev13 pins:
`artifacts/formulation/tools/run_acceptance.py` exits 3 at preflight because
`artifacts/formulation/evidence/semantic_escape_rebased.json` binds
`base_sha256 = 1bb78ce9b357…` (rev11 C0) while the live canonical C0 measures
`b2ab6acb2bbe…`; yet `evidence/acceptance_pipeline_report.json` still records canonical
3/3 pass and `union_caught 31/31`.

Two questions, both measurable read-only:

1. **Reproduction** — is CF-32(i) exact at T0 (exit code, both hashes, stale report bytes)?
2. **Materiality** — if the corpus is re-based onto the live canonical C0 (same recorded
   `path=value` operations, same manifest), do the recorded stage verdicts and the
   `union_caught 31/31` claim survive? A stale *hash binding* and a stale *measurement* are
   different defects; only the second would invalidate the recorded numbers themselves.

## Method (fixed before measurement)

1. Pin every input by sha256 at T0; snapshot the small ones under `pins/`.
2. Reproduce `python3 artifacts/formulation/tools/run_acceptance.py`: record exit code and stdout.
3. **Sandbox rebase (no canonical writes).** Re-implement `measure_semantic_escape.py`'s
   recorded operation (`path = value` / `delete path = None`) independently in
   `run_repro.py`; apply each op to a deep copy of the **live** canonical C0
   (`artifacts/formulation/schemas/af_scc_c0_vacuum.yaml`); write fixtures only under
   `sandbox_fixtures/`. Run both stages (`check_class_schema.py --json`,
   `spec_conformance_audit.py`) on each fixture.
4. **Control C6 (parser equivalence):** cross-check my parser against
   `measure_semantic_escape.py::parse_mutation` on all manifest fixtures; count mismatches.
   A mismatch voids the corresponding row.
5. **Delta table:** compare each live-rebased verdict against the verdict stored in the
   stale corpus (`semantic_escape_rebased.json`). Report every change; do not explain away
   any change.
6. **Controls:** C1 preflight failure reproduced; C2 stale-base predicate true
   (stored != live); C3 a fixture the stored corpus recorded as a structural catch still
   fails the union; C4 the two manifest controls pass both stages; C5 canonical inputs
   re-hash unchanged after the run (read-only proof).
7. **Rebind readiness map:** census of every file under `artifacts/formulation/evidence/`
   and `artifacts/worker-06/semantic_fixtures/` carrying the stale digest, plus FROZEN
   rev29 pin-set membership for the three pipeline components and the corpus manifest.

## Pre-registered predictions (to be checked, not assumed)

- **P1** preflight exits 3; stdout names `1bb78ce9b357…` vs `b2ab6acb2bbe…`.
- **P2** `acceptance_pipeline_report.json` is byte-stale (`9b7d6c8208d3…`) and its PASS
  cannot be regenerated at live bytes while the corpus binds the rev11 base.
- **P3** under the live rebase the union still catches every mutant, but I record the exact
  per-stage totals even if they differ from the stored 30/11/31; any difference is a
  finding, not noise.
- **P4** `spec_conformance_audit.py` (and the corpus manifest) are absent from
  `artifacts/formulation/FROZEN.json`, so the pipeline's stage-2 dependency and its corpus
  are unpinned even after a hash rebind.

## Falsifiers

- `run_acceptance.py` exits 0 at T0 → CF-32(i) does not reproduce.
- The stored corpus already binds the live C0 → staleness is void.
- Any canonical path's sha256 differs before vs after the run → the run is not read-only and
  every result is void.
- Parser-equivalence mismatches > 0 in a row → that row is excluded and reported.
- Live-rebased union catch < mutants_rebased → the recorded 31/31 does not transfer to live
  bytes; that is a hard finding for rev14 item (7), not a reason to soften the report.

## Stop rule

Stop at the first of: (a) 25 minutes of active work, (b) two consecutive tool failures that
cannot be bounded, (c) any need to write outside `artifacts/worker-097/cf32_acceptance_repro/`,
`comms/outbox/worker-097.jsonl`, or `runtime/state/w097_*`. On stop, emit a blocker instead of
a partial claim.
