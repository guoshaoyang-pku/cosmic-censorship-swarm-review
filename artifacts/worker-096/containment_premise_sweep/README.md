# W096-F2B-CONTAINMENT-PREMISE-SWEEP-01 — blast-radius bound on the L-FORM-01 inversion

Worker: `worker-096` · one bounded class-bound task, self-selected (no card in
`comms/inbox/worker-096.jsonl`). Gate context: **G-FORM / G-F0**, node **F2b**,
classes **AF-SCC-C0-VAC-GEN**, **AF-SCC-C2-VAC-GEN**, **AF-WCC-VAC-GEN**.

## Question

`astra-lead-formulation` reported at 2026-09-12T00:44:52+08:00 a class-bound defect
(L-FORM-01): `schemas/af_scc_c0_vacuum.yaml:245` justifies a forbidden transfer with
"C2 is a strictly larger extension class", while the same frozen file's declared chain at
line 238 is `E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2` — i.e. C2 is the
**smaller** extension class. One known defect does not bound the blast radius, so:

> Is the C0:245 inversion the **only** extension-class containment premise in the frozen
> set that contradicts the chain the artifacts themselves declare, or are there siblings?

## Method (independent, machine-checked)

`sweep.py` extracts every extension-class containment premise from the four frozen files
by direct string/YAML analysis — not from any review or earlier worker report — and
adjudicates each against the declared poset `C2 < C11 < H2LOC < C0` (strictly increasing
extension-set size; declared twice, `F2a:236` and `F2b:238`):

1. chain/pair premises `E_X contains|subset of E_Y`, scanned with an overlapping lookahead
   so `A contains B contains C` yields both links;
2. `<class> is a strictly larger|smaller extension class` with the document/ledger context
   as referent;
3. `those are strictly larger classes` in the taxonomy `meaning_C2` field (referent C2);
4. every `implication_ledger` row: an **entails** row is licensed iff
   `E_target ⊂ E_source`, a **forbidden** row is correct iff that entailment is *not*
   licensed. A wrongly-forbidden licensed transfer is a defect too.

Controls: 11 planted fixtures (4 correct/inverted larger-smaller pairs, 4 correct/inverted
containment pairs, 2 chain controls that fail if the middle link is dropped, 1 ledger
control that fails if a licensed transfer is wrongly forbidden). All 11 pass. Input hashes
are measured before and after; drift is a hard failure. FROZEN rev28 pin is re-measured.

## Result at the pinned snapshot (FROZEN rev28 `2f358f6722d9`)

| file | premises | ledger rows | consistent | inverted/defect |
|---|---:|---:|---:|---:|
| F2a `af_scc_c2_vacuum.yaml` (`5476a3f2c6bc`) | 12 | 6 | 17 | 0 |
| F2b `af_scc_c0_vacuum.yaml` (`55d0a1ea9bda`) | 6 | 7 | 10 | **1 (line 245)** |
| F0 `formulation_taxonomy.yaml` (`0abb9ed8a961`) | 1 | 0 | 1 | 0 |
| F1 `af_wcc_vacuum.yaml` (`cce9c60146d6`) | 0 (no `implication_ledger`, no E_* containment) | 0 | 0 | 0 |

- **The C0:245 inversion is reproduced** by an independent method.
- **0 new defect lines beyond F2b:245.** Every other containment premise and all 13 ledger
  rows are direction-consistent with the declared chain: the F2a chain and ledger, the F2b
  chain, both transitivity rows, the `E_C2 subset E_H2loc` premise, the taxonomy
  `meaning_C2` statement, and the two cross-family/variant rows are correctly out of scope.
- 3 rows are `out_of_scope` (cross-family WCC↔SCC, and the C0 distributional-vacuum
  variant); they are **not** adjudicated here.

## What this does and does not support

- Supports: the L-FORM-01 defect is **isolated on the containment-premise axis** at this
  hash; a one-token repair at line 245 is sufficient for this criterion (it still moves the
  F2b hash and voids verdicts at `55d0a1ea`).
- Does **not** support: a full-schema verdict, a gate verdict, a ruling that the defect is
  a G-FORM hard failure, or any judgment on the mathematics of the declared chain. Workers
  cannot move gates or `status=done`.
- The poset is taken from the two independent declarations inside the frozen artifacts
  themselves; this is an internal-consistency check, not a proof of the chain.

## Files

| file | role |
|---|---|
| `sweep.py` | deterministic extractor + adjudicator + 11 controls; `--selftest` runs controls only |
| `report.json` | full machine record: per-premise rows, ledger rows, controls, hashes, summary, falsifier |
| `runlog.txt` | verbatim stdout of the report-producing run (exit 0) |
| `README.md` | this file |

## Falsifier

Re-run `python3 sweep.py`. Falsified if it reports >0 new defect lines beyond `F2b:245`,
fails to reproduce the `F2b:245` inversion, any input hash differs from `report.json`
`inputs{}`, the FROZEN rev28 pin stops matching, or a control fails. A revision of the
declared chain itself (`F2a:236` / `F2b:238`) voids every verdict in the report.

## Reproduce

```bash
cd <repo root>
python3 artifacts/worker-096/containment_premise_sweep/sweep.py --selftest   # 11/11 controls
python3 artifacts/worker-096/containment_premise_sweep/sweep.py              # exit 0, writes report.json
```
