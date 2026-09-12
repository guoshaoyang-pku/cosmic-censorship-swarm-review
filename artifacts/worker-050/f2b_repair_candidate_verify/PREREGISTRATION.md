# W050-F2B-REPAIR-CANDIDATE-INDEPENDENT-VERIFY-06 — pre-registration

Frozen before the run. Instance `worker-050-20260912T011001-968807` (slot 050). No assignment card
exists in `comms/inbox/worker-050.jsonl`; this is one self-selected bounded class-bound task.

## Question

Worker-001's containment closure (`W001-F2B-REV13-CONTAINMENT-CLOSURE-01`, 01:10:11) proposed a
two-line repair to F2b rev13 and self-verified it (`REPAIR_CANDIDATE_VERIFIED`). No **independent**
verification of that candidate exists (grep: `90ede5c9` appears only in worker-001's own outbox).
This task independently verifies the candidate, non-author, with its own instrument.

## Subject

- class: `AF-SCC-C0-VAC-GEN` (node F2b, gate G-FORM)
- base: `schemas/af_scc_c0_vacuum.yaml` sha256
  `b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c` (rev13 publication, FROZEN rev29)
- candidate: `artifacts/worker-001/f2b_containment_repair/REPAIR_CANDIDATE.yaml` sha256
  `90ede5c9516b5b4d18346bed6224561d06194b3c485067976be9aab55dd5a328` (NON-CANONICAL; no write)
- declared diff: `artifacts/worker-001/f2b_containment_repair/REPAIR_CANDIDATE.diff` sha256
  `a45fbae3a8afc01f0e7d5b64bc773a2c34aeb984e734dd092e30dc04f0fd6bde`

Controls pinned by hash: F2a `schemas/af_scc_c2_vacuum.yaml` `e9a27996dfd3…`; F1
`schemas/af_wcc_vacuum.yaml` `d9cebb9404b2…`; F0 `research_map/formulation_taxonomy.yaml`
`0abb9ed8a961…` + supplement `artifacts/formulation/formulation_taxonomy.yaml` `d7419b4e8963…`;
`artifacts/formulation/FROZEN.json` `815e08079aef…`; `artifacts/formulation/VOCAB_ALIASES.json`
`46cd9f1eb534…`. Full digests are in `verify_repair_candidate.py::PINS` and `inputs.json`.

## Prior defect list being tested (worker-050's own, rev13 pin)

- **D1** line 152 `regularity.must_not_conflate[0]`: "No containment with C2 or C0 is asserted
  here" contradicts the same file's `implication_ledger.extension_class_containment` (line 239)
  and the corrected F2a sibling.
- **D2** line 246 `implication_ledger.forbidden_transfers[0].reason`: "C2 is a strictly larger
  extension class" inverts the containment direction (E_C2 ⊂ … ⊂ E_C0).
- **D3** `conclusion.conclusion_type` uses the VOCAB-canonical token
  `scc_c0_future_inextendibility`, absent from F0's declared `conclusion_type.allowed` list.

## Pre-registered checks (fail-closed)

| id | check |
|---|---|
| P0 | every pinned input matches its pre-registered sha256 at start **and** end; any move → exit 3, measurement void |
| C1 | base and candidate parse as YAML mappings with identical recursive key skeleton (no key added/lost/retyped) |
| C2 | byte diff base→candidate is exactly two 1-for-1 line replacements at lines 152 and 246; the declared diff file's hunks match that computed diff exactly |
| C3 | D1 carrier absent from candidate; candidate line 152 defers containment to `implication_ledger.extension_class_containment`; that chain is present and parses to the order C0 ⊃ H2loc ⊃ C^1,1 ⊃ C2 |
| C4 | D2 carrier absent from candidate; candidate line 246 states E_C2 is a strictly **smaller** extension set than E_C0, mechanically consistent with the C3 chain rank |
| C5 | D3 classification: candidate token is VOCAB-canonical, is bridged to F0's allowed list by a declared alias, and F2a is in the *same* representation state (symmetry). Asymmetric treatment → check fails |
| C6 | no residual adverse carrier anywhere in candidate: "No containment with C2 or C0", "strictly larger extension class", "strictly between" |
| C7 | cross-sibling agreement: candidate ledger direction agrees with F2a's chain and with candidate line 246; candidate line 152 does not deny extension-set containment in any form |
| C8 | determinism: two runs over the same inputs produce byte-identical check results |
| C9 | structural invariants: `must_not_conflate` length, `one_way_entailments` count, `forbidden_transfers` count, `conclusion_type`, `extension_class_containment` unchanged base→candidate |

## Controls (in-memory mutations; any undetected control → exit 4)

K1 revert edit A; K2 revert edit B; K3 invert "smaller"→"larger"; K4 wrong candidate pin must trip
the pin guard; K5 delete line 152; K6 drop the `implication_ledger` top-level key.

## Exit codes / verdict

- `0` all checks pass, controls all fire → `CANDIDATE_VERIFIED_MINIMAL_FIX` (D1+D2 fixed, minimal,
  no new contradiction; D3 reported as a global symmetric residual outside the declared scope).
- `2` a check fails → `CANDIDATE_REJECTED_*` (defect persists or new inconsistency introduced).
- `3` any pin moved → `VOID_INPUT_DRIFT`.
- `4` an undetected control → `INSTRUMENT_CONTROL_FAILURE` (measurement not trustworthy).

## Falsifiers (of this verification)

VF1 any pinned input moves (exit 3). VF2 an independent reader reproduces a different base→candidate
diff than the two declared hunks. VF3 the candidate is shown to deny extension-set containment, or
to state the E_C2/E_C0 order backwards. VF4 F2a is shown to be in a *different* F0-vocabulary
representation state than F2b, which would refute the D3 symmetry classification. VF5 re-running
`verify_repair_candidate.py` yields a different report from identical bytes.

## Authority

Worker measurement only. No canonical write, no `validation_status=passed`, no node `done`, no gate
verdict. `worker-050` authored neither `schemas/af_scc_c0_vacuum.yaml`, nor the candidate, nor F0/F2a,
nor `VOCAB_ALIASES.json`; it did author the D1/D2/D3 defect list and the prior containment-cluster
report, which is disclosed. The candidate is re-checked mechanically against the frozen bytes, not
against the prior report.
