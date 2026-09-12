# W095-HOLD-BIND-INTEGRITY-04 (pass-05 re-probe)

Class-bound task: node `F2b`, class `AF-SCC-C0-VAC-GEN`, gate `G-FORM`.
Re-tests the falsifier of W095-HOLD-BIND-INTEGRITY-03 at map `11311ab36005` (updated 2026-09-12T00:43:08+08:00).

Verdict: **revise** (score 3/5). `counts_as_full_schema_verdict=false`.

- R1 pin match: PASS (all five held paths at FROZEN rev28 pins)
- R2 manifest self: PASS (FROZEN.json measured 2f358f6722d9)
- R3 event shadow: FAIL (shadowed: schemas/af_wcc_vacuum.yaml, schemas/af_scc_c2_vacuum.yaml, schemas/af_scc_c0_vacuum.yaml, research_map/formulation_taxonomy.yaml)
- R4 declared evidence resolution: FAIL (declared 675a99d0d25b vs measured 9e335e9ba1bf)
- R5 gate coverage: info (see evidence/raw/map_gate_slice_r2.json)
- R6 no probe drift: PASS

Raw evidence: `evidence/raw/`. Reproduce: `python3 run_probe_r2.py` (append `--emit`
to re-emit outbox events/checkpoint; event_ids are idempotent).
