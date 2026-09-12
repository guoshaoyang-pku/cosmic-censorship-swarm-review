# W090-F1-REV12-CLOSURE — independent closure check of F1 rev12

Worker: `worker-090` (slot 090) · Node `F1` · Class `AF-WCC-VAC-GEN` · Gate `G-FORM`
Checked snapshot: `schemas/af_wcc_vacuum.yaml` revision 12,
sha256 `cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3`
(canonical and authoring mirrors byte-identical; both unchanged across the run).

## Question

At revision 11 this slot filed three hash-bound findings (`HF090-01/02/03`).
Revision 12's own revision note claims all three are closed, plus D0 retyping and
the tail-visibility repair. This artifact tests that claim mechanically, on frozen
bytes, with mutants that re-open each finding.

## Result

**All three prior hard findings are closed at this snapshot. No blocking defect
found by the 19-check suite. Two residual major/hygiene defects remain.**

| prior finding | rev11 defect | rev12 status | check | mutant |
|---|---|---|---|---|
| HF090-01 | `class_contract_pointer` pointed at the authoring tree | **closed** — pointer is `research_map/formulation_taxonomy.yaml#classes.AF-WCC-VAC-GEN` and the fragment resolves in the canonical taxonomy; supplement split into its own field | H04, H05 | M2 caught |
| HF090-02 | 7 duplicate top-level `revised_at` keys, future-dated | **closed** — 0 duplicate mapping keys anywhere; single `revised_at`; wall-clock skew −214 s; history rows non-future | H01, H02, H03, H13 | M1, M6 caught |
| HF090-03 | `AF_{I+}` used but never defined | **closed** — defined in `i_plus.predicate_abbreviation`; 3 symbol lines = 2 operative (definition + `statement_formal`) + 1 prose | H08 | M3 caught |
| rev12 claim | D0 was a mixed-type disjunction | **verified** — D0 is a tagged disjoint index set; first quantifier binds `r in D0` | H10 | — |
| rev12 claim | whole-curve vs tail visibility | **verified** — `quantifiers.formal`, D5, `visibility.definition`, `visibility.negation_conclusion` all single-q tail; whole-curve only in prohibition prose | H11, H12 | M4 caught |

Residual (non-blocking) findings at the snapshot:

- **W090-R12-01 (major, binding):** `f0_binding.consistency_evidence_sha256`
  declares `675a99d0…` but the live evidence file measures `9e335e9b…`; and the
  evidence file itself embeds **zero** 64-hex digests, so even a matching pointer
  would not bind `consistent=true` to the declared/measured F0 revision pair.
  Re-stamping alone does not close this — the generator must embed both tree hashes.
- **W090-R12-02 (advisory, hygiene):** `review_status.independent_reviewers` is
  still `[]` with `verdict: pending` while the review corpus exists.

## Files

| path | role | sha256 |
|---|---|---|
| `check_f1_rev12_closure.py` | checker + 6 mutants | see `evidence.json` |
| `results.json` | machine-readable 19 checks, mutant results, hash guard | see `evidence.json` |
| `snapshot/` | frozen inputs + `SHA256SUMS.txt` | — |

## Reproduction

```bash
cd <repo>
python3 artifacts/worker-090/f1_rev12_closure/check_f1_rev12_closure.py \
  --out artifacts/worker-090/f1_rev12_closure/results.json
```

Exit 0 iff no blocking check fails; every mutant must read `"status": "caught"`.

## Falsifier

Re-run the checker after the next revision. The closure verdict is falsified if
any of H01/H02/H03/H04/H08/H10/H11/H12 flips to `fail` at a newer stable hash, if
any mutant escapes, or if the frozen snapshot `cce9c601…` is not byte-identical to
the reviewed canonical file.
