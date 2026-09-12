# W054-T1-GUARD-REV13-01 — T1 transfer guard adjudicated at rev13 (read-only)

**Worker:** worker-054 (no inbox card; one bounded class-bound task self-selected)
**Date:** 2026-09-12 ~01:04 +08:00
**Nodes:** F1, F2a, F2b · **Classes:** AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN
**Rule under test:** `research_map/formulation_taxonomy.yaml#transfer_rules.allowed[0]` (T1),
`AF-SCC-C0-VAC-GEN → AF-SCC-C2-VAC-GEN`, guards: (1) `data_class` fields match exactly,
(2) `genericity_kind`/`genericity_topology` match exactly, (3) source claim evidence (not tested).
**Mode:** read-only. No canonical write, no gate verdict, no node status change.

## Pinned inputs (all three verified against FROZEN rev29 `815e08079aef`, frozen_at 00:57:26)

| node | path | sha256 (prefix) |
|---|---|---|
| F1 | `schemas/af_wcc_vacuum.yaml` | `d9cebb9404b2` |
| F2a | `schemas/af_scc_c2_vacuum.yaml` | `e9a27996dfd3` |
| F2b | `schemas/af_scc_c0_vacuum.yaml` | `b2ab6acb2bbe` |
| F0 | `research_map/formulation_taxonomy.yaml` | `0abb9ed8a961` |

## Result

| check | outcome |
|---|---|
| T1 guard-2 (`genericity.kind`, `genericity.topology_or_measure`) | **HOLDS exactly** (2/2 keys byte-identical) |
| T1 guard-1, literal whole-subtree reading | **FAILS**: exactly 2 of 23 keys differ — `adm_mass.locator`, `adm_mass.hypotheses_reconciliation` |
| T1 guard-1, pre-registered mathematical content (17 keys) | **HOLDS** (17/17 identical, including `s`, `delta`, the Sobolev-space token, decay rates, constraints, symmetry, gauge) |
| T1 guard-1, whole subtree minus declared annotation keys | **HOLDS** (0 mismatches) |
| Named `(s, delta, norm)` triple from the map's G-FORM unmet item | `s` and `delta` literal-equal across F1/F2a/F2b; `spaces`/norm literal-equal for F2a/F2b, F1 differs only by the parenthetical `(weighted Sobolev)` and is normalized-equal |
| Forbidden pair F1 → F2a, same content pass (control) | **FAILS** on 4 content keys — the checker is discriminating, not vacuous |

**Both failing keys of the licensed pair are annotation/provenance fields**, not data-space content:

- `data_class.adm_mass.locator`: F2b carries `to be supplied by L1 (Schoen-Yau / Witten); …`, F2a carries `to be supplied by L1`.
- `data_class.adm_mass.hypotheses_reconciliation`: present only in F2b; a note about the pointwise/Sobolev rate reconciliation and the independent `i_plus k >= 3` assumption.

## Adjudication

1. **The map's G-FORM unmet item — "no single frozen data class (s,delta,norm) is shared by
   F1/F2a/F2b, which disables the licensed C0=>C2 transfer" — is not supported at the rev13 bytes
   for the licensed pair.** F2a and F2b agree byte-for-byte on all 17 pre-registered mathematical
   data-space keys, on `s`, `delta`, and the Sobolev-space token. The only divergences are two
   citation/reconciliation annotations, so the transfer is *not* disabled by a data-space
   divergence. Whether guard-1 blocks the transfer depends entirely on how "exactly" is read.
2. **The prior worker disagreement is explained by that reading, not by the bytes:**
   worker-071's "T1 not canonically equal" is the literal reading; worker-060's "equal on all 15
   data-space-core keys" is the content reading; worker-029's `CONFIRMED_UNMET` was measured at
   rev11 and is superseded. At rev13 both readings are now stated separately with witnesses.
3. **Recommended repair (not performed):** either restate T1 guard-1 as "mathematical `data_class`
   fields match exactly; citation/provenance annotations excluded", or align the two annotation
   fields between F2b and F2a. Both are lead-formulation/lead-audit decisions; this report is
   evidence for the G-FORM r3 review only.
4. **Nothing here touches the gate:** T1 guard-3 (source claim carries `artifact_refs` and a
   reviewer verdict) is untested, and no reviewer verdict is claimed.

## Controls (all as declared, `controls_all_detected: true`)

| id | mutation (in-memory copy) | expected | observed |
|---|---|---|---|
| C1 | F2b `sobolev_variant.s` → `s > 3/2` | content pass detects | detected |
| C2 | F2b decay metric → `O(r^{-2})` | content pass detects | detected |
| C3 | F2b equations → Einstein–Maxwell | content pass detects | detected |
| C4 | F2b `adm_mass.locator` → `MUTANT` (annotation only) | content pass ignores, literal pass detects | ignored / detected |
| C5 | F2b `genericity.kind` → `full_measure` | genericity pass detects | detected |
| C6 | F2b `genericity.topology_or_measure` → `MUTANT` | genericity pass detects | detected |
| C7 | F1 vs F2a same content pass | non-vacuous (must fail) | detected (4 keys) |

## Limits / falsifier

- One run, one frozen revision; no second independent extractor was used (the report publishes
  every compared value, so a second extractor can be run against the same bytes).
- FROZEN revision 29 was rewritten several times; the report observes `815e08079aef` and does not
  pin it. The three schema pins and the taxonomy pin are the anchors.
- **Falsifier:** at the pinned bytes, re-run `checker.py --created-at 2026-09-12T01:04:53+08:00`;
  any changed verdict, mismatch-key list, control result or named-triple value falsifies this
  report. It is also falsified if any input drifts (`drift_detected`), if any input's
  `class_id`/revision differs from its pin, or if a control stops behaving as declared.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-054/t1_guard_rev13/checker.py --created-at 2026-09-12T01:04:53+08:00
# exit 0 = measurement complete with all 7 controls as declared; 10 = fail-closed
```

Artifacts: `report.json` (full per-key matrix, witness values, controls, drift),
`input_hashes.json` (+ `frozen_inputs/` byte copies), `checker.py`, `summary.md`, `README.md`.
