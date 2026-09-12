# W16-F0-MIRROR-VERIFY-01 — independent verification of F0-MIRROR-CONFLICT

**Worker:** worker-016 (bounded execution pass, 2026-09-12 ~00:30 +08:00)
**Target:** `artifacts/formulation/evidence/f0_mirror_conflict.json` (`7e3a7bc89a75…`, author `astra-lead-formulation`)
**Blocker under test:** `leadform-blocker-0007` (F0 publication blocked pending controller adjudication REC-1/REC-2)
**Node / classes:** F0 · `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH`
**Verdict: CONFIRMED** — every load-bearing claim of the evidence reproduces from bytes.

## What was verified (not re-derived from the lead's text)

| id | claim tested | result |
|---|---|---|
| V1 | canonical `research_map/formulation_taxonomy.yaml` = `276009f4f63d…`, 35145 b | PASS |
| V2 | authoring `artifacts/formulation/formulation_taxonomy.yaml` = `c8e979a1eb48…`, 20937 b | PASS |
| V3 | the two paths are not byte-identical | PASS |
| V4 | canonical carries `class_ids`/`classes`/`transfer_rules` and no `class_contracts`; authoring carries `class_contracts`/`axis_registry`/`implication_ledger` and no `class_ids` | PASS |
| V6 | all three schemas' `class_contract_pointer` target the authoring `#class_contracts.<CLASS>` fragment and resolve **only** there | PASS |
| V7 | all three `f0_binding` records name canonical `276009f4` as declared F0 and the authoring file as supplement | PASS |
| V8 | `check_taxonomy_consistency.py` requires `A["class_ids"]`, `A["classes"]` **and** `B["class_contracts"]`, `B.axis_registry.genericity_axis`, `B.implication_ledger` (lines 16–39, 71–73) | PASS |
| V9 | staged control: unsubstituted pair → `CONSISTENT (4 classes, 0 contract-text divergences)`, exit 0 | PASS |
| V10 | authoring ← canonical substitution → `KeyError: 'class_contracts'`, exit 1 | PASS |
| V11 | canonical ← authoring substitution → `KeyError: 'class_ids'`, exit 1 | PASS |
| V12 | one-byte mutation changes the pinned hash (byte binding is sensitive) | PASS |
| V13 | FROZEN rev26 (`2554e276a0db`, frozen_at 2026-09-12T00:24:49) pins both hashes, carries `logical_artifacts` + `f0_mirror_adjudication_request` | PASS |
| V14 | `audit_evidence.py` MIRRORS contains the F0 pair, so the soft dual-tree finding follows by construction | PASS |
| V15 | G-F0 audit coverage at `276009f4` | INFO (below) |

Controls: positive (V9) and negative (V12). The destructive substitutions ran only in the staged
tree `artifacts/worker-16/f0_mirror_check/stage/`; the repo checker writes its evidence file on
every run, so running it in place would have rewritten the pinned
`artifacts/formulation/evidence/taxonomy_consistency.json`. **No repo artifact was modified.**

## Two calibrated findings for the controller (not adjudications)

1. **V15 — accept coverage at the canonical hash.** F0-targeted review verdicts recorded in the
   map now include two accepts (`astra-lead-audit`, `worker-040`) alongside revises
   (worker-082, worker-16, deepseek-flash-17/19) and inconclusives (flash-21/22). The
   `controller_gate_audit` snapshot at 00:24:40 records **0 distinct accepts** because no F0 accept
   carries a top-level `artifact_sha256 == 276009f4…`; `w040-20260912T0023-review-f0` binds the hash
   through `evidence_refs`/`conditions` instead. Whether an evidence-refs-bound accept counts is
   controller authority — this verification does not move G-F0.
2. **Supersession lineage.** `565a6e505188` (the prior lead-audit accept) appears 13× in the map;
   all of it is superseded lineage per the lead's re-emission. No verdict in this report binds it.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-16/f0_mirror_check/verify_mirror_claim.py   # exit 0 = CONFIRMED
sha256sum artifacts/worker-16/f0_mirror_check/verification.json     # matches verification.sha256
```

## Falsifier

Any of V1–V13 turning FAIL on a re-run at these hashes, or either substitution run exiting 0
without an exception, refutes this confirmation. If a future revision makes the two paths
byte-identical while every frozen schema binding, the pinned consistency evidence, and the F0 gate
criteria still resolve, the "cannot be made identical without damage" claim is refuted.

**Next falsifier:** find any consumer of the authoring `#class_contracts` fragment beyond the three
schemas, the checker and the FROZEN-pinned consistency evidence; an easily repointable consumer
lowers REC-2's cost.

**Authority note:** worker-level verification only. No node completion, no gate verdict, no
REC-1/REC-2 adjudication is claimed here.
