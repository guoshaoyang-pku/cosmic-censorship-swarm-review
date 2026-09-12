# artifacts/worker-054/t1_guard_rev13

Read-only, hash-pinned adjudication of the licensed **T1** transfer guard
(`AF-SCC-C0-VAC-GEN → AF-SCC-C2-VAC-GEN`, `research_map/formulation_taxonomy.yaml
#transfer_rules.allowed[0]`) at the rev13 / FROZEN rev29 pins, 2026-09-12 ~01:04 +08:00.

- `checker.py` — deterministic checker. Pins every input by sha256 and aborts fail-closed on pin
  mismatch, unparsable YAML, or a `class_id` mismatch. Compares the `data_class` subtree and the
  `genericity` guard fields under a pre-registered key split (17 mathematical content keys vs 6
  citation/provenance annotations), runs 7 mutation/cross-pair controls on in-memory copies, and
  re-hashes every input at the end for drift.
- `report.json` — full measurement: every compared key with both values, all controls, drift.
  Produced with `--created-at 2026-09-12T01:04:53+08:00`; re-running at the same bytes and the
  same `--created-at` is byte-identical (verified twice).
- `input_hashes.json` — sha256 of each input and of its `frozen_inputs/` byte copy, FROZEN rev29
  declared schema pins, and the report hash.
- `frozen_inputs/` — byte copies of F1/F2a/F2b schemas, the taxonomy, and FROZEN.json.
- `summary.md` — result, adjudication, controls, limits, falsifier.

Pins: F1 `schemas/af_wcc_vacuum.yaml#d9cebb9404b2`,
F2a `schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3`,
F2b `schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe`,
taxonomy `research_map/formulation_taxonomy.yaml#0abb9ed8a961`;
all four match FROZEN revision 29 (`815e08079aef`, frozen_at 00:57:26).

Verdict in one line: T1 guard-2 holds exactly; T1 guard-1 fails only on two annotation keys under
a literal whole-subtree reading and holds on all 17 mathematical content keys, so the map's
"data-class divergence disables the C0=>C2 transfer" item is not supported at these bytes.

Authority: worker measurement only. No gate verdict, no node status, no canonical write.
Falsifier and re-run command are in `summary.md`.
