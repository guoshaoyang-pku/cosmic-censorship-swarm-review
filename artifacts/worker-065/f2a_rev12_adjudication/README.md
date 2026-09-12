# W065 F2a rev12 adjudication (AF-SCC-C2-VAC-GEN)

Task `W065-F2A-REV12-ADJUDICATION-01` | node F2a | gate G-FORM | class `AF-SCC-C2-VAC-GEN` | reviewer `worker-065` (not an author)

Target: `schemas/af_scc_c2_vacuum.yaml#5476a3f2c6bc` (rev12, FROZEN rev28).

Window: **STABLE** across the run.

## Verdict: revise (advisory, score 3.5)

Two live defects, two stale blockers cleared.

| id | finding | status | severity |
|---|---|---|---|
| W065-H1 | declared `consistency_evidence_sha256` 675a99d0 does not resolve at the declared path (live 9e335e9b; FROZEN rev28 pins 9e335e9b) | CONFIRMED_REAL | blocking_for_gate_criterion |
| W065-H2 | `citation_status: verified_by_L1` is undefined in both frozen ledger artifacts; ledger records abstract-read for those ids | CONFIRMED_REAL | major_vocabulary_scope |
| W065-H3 | `class_contract_pointer` fails to resolve in canonical F0 | NOT_REPRODUCED_STALE | none |
| W065-H4 | R22 unknown keys (worker-005) | NOT_REPRODUCED_TOOL_SCOPED | none |
| W065-H5 | F0 canonical/supplement byte divergence | NOT_A_DEFECT_BY_RULING (REC-3) | none |
| W065-H6 | stale index pin b6123750b37d | OUT_OF_CLASS_SCOPE (lives in `schemas/af_scc_regularities.yaml`) | none |

## Key measurements

- canonical gate (sha `000e09e46b2f`) + FROZEN-pinned manifest
  (sha `014e2d301978`) on F2a rev12: **verdict=pass,
  failed_rules=[]**; positive control on an injected unknown key fires R22
  (`['R22']`), so the pass is not vacuous.
- rev27 replay manifest (264 keys) reproduces exactly the six keys named by HF-W005-F2D-01:
  `['at', 'class_contract_supplement_pointer', 'consistency_evidence_sha256', 'index', 'notes', 'revision_history', 'unused']` — the finding is a replay-scope artifact.
- consistency evidence: declared `675a99d0d25b` -> live path `9e335e9ba1bf`;
  the declared hash is carried by 5 files found in a
  6637-file repo scan (none of them the declared path).
- `verified_by_L1`: 0 occurrences in the ledger,
  0 in the citation audit; 4 F2a rows claim it.
- pointer resolution: canonical `True`, supplement `True`,
  corrupted-fragment control resolves `False` (must be false).

## Controls

['C1a-class_contract_pointer: ok=True', 'C1b-class_contract_supplement_pointer: ok=True', 'C1n-negative-control-corrupted-fragment: ok=False', 'C2-declared_f0_sha256: ok=True']

R22 live control: fired=True.

## Falsifiers

Each finding carries its own falsifier in `report.json`. Global falsifiers for this adjudication:
a window hash differing between `window_pre` and `window_post`; a canonical-gate run at the
FROZEN-pinned tool/manifest shas that disagrees with the recorded verdict; a corrupted-pointer
control that resolves; or an R22 positive control that fails to fire.
