# W095-HOLD-BIND-INTEGRITY-06 -- freeze-hold / class-binding integrity re-probe (r4)

Class-bound task: node **F2b**, class **AF-SCC-C0-VAC-GEN**, gate **G-FORM**.
Successor to `freeze_hold_binding_integrity_r3/` (W095-HOLD-BIND-INTEGRITY-05), re-testing its
declared next falsifier at the live FROZEN revision after the 00:57:48 ingest of the
lead-formulation rev29 pin announcements.

- Probe time: **2026-09-12T01:02:08+08:00**; FROZEN **rev29**
  (`815e08079aef`), F2b rev13 (`b2ab6acb2bbe`).
- Reproduce: `python3 artifacts/worker-095/freeze_hold_binding_integrity_r4/run_probe_r4.py`
- Verdict: **revise** (3/5), hard failures `HF-06-01`, `HF-06-02`.
  Worker review only: `counts_as_full_schema_verdict=false`, no node status or gate verdict set.

## Check table

| check | result | what it measures |
|---|---|---|
| R1 PIN-MATCH | PASS | all FROZEN rev29 pins vs disk bytes |
| R2 MANIFEST-SELF | PASS | FROZEN.json measured vs its announcement |
| R3 ANNOUNCE | PASS | pin announcement per held path (HF-05-01 re-test) |
| R4 ORDER-RESOLUTION | FAIL | created_at-max / file-order-last / _received_at-max vs pin |
| R5 DECLARED-EVIDENCE | PASS | f0_binding declared == measured, two consecutive reads |
| R6 NO-PROBE-DRIFT | PASS | pinned artifacts stable across the probe window |
| R7 CLASS-BINDING | PASS | F2b class_id + class_contract_pointer resolves in canonical F0 |
| R9 STREAM-HYGIENE | INFO | non-ingested / future-dated event cohort |

## Result in one paragraph

The byte-level freeze hold is intact (R1/R2/R6 PASS, 50/50 pins match) and the rev29
change_protocol gap reported by r3 as **HF-05-01 is repaired**: every held path and
FROZEN.json now has an artifact event in the accepted stream carrying the pin
(`lead-form-20260912T005743-00..06`, ingested 00:57:48). What remains is the ordering defect
(**HF-06-01**): resolution by agent-declared `created_at` still binds stale bytes for 2/5 held
paths -- F2b `schemas/af_scc_c0_vacuum.yaml` -> `e6b1af2bd692` (`w06-20260912T0115-f2b-rev6`)
and `research_map/formulation_taxonomy.yaml` -> `276009f4f63d`
(`leadform-artifact-0095-r4f0`) -- while file order and `_received_at` order both resolve to
the pin. The F2b shadow is also the new **HF-06-02**: it is future-dated (created_at
01:15:00, +13 min) and was never ingested (`_received_at` absent), so the r3-recommended
`_received_at` fallback has no defined value for it; the accepted stream carries 914 such
non-ingested events. F2b class binding (R7) and declared-evidence resolution (R5) pass.

Do not read this as a gate verdict or a node completion.
