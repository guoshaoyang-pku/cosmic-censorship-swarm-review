# W053-F1-REV12-INDEP-VERIFY-01

Bounded execution-slot task by `worker-053` (class `AF-WCC-VAC-GEN`, node `F1`,
gate `G-FORM`). Answers one question: **does `schemas/af_wcc_vacuum.yaml` at its
measured hash resolve the rev11 hard findings, and are its declared F0 /
consistency-evidence bindings and the FROZEN manifest fresh at the same bytes?**

## Verdict (see `report.json` for the machine record)

| field | value |
|---|---|
| verdict | `revise` |
| score | 3.75 / 5 |
| F1 measured sha256 | `cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3` (rev12, 36014 B) |
| canonical F0 measured | `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3` |
| consistency evidence measured | `9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b` |
| FROZEN | revision 28, 44/44 listed files byte-exact |
| drift | stable (no input changed across the run) |
| controls | 8/8 planted defects detected |

### Hard failure (blocks an accept at this hash)

**C8 / HF053-1 (major) — stale consistency-evidence pin.** `f0_binding` declares
`consistency_evidence_sha256 = 675a99d0d25b2b37…`, but the file
`artifacts/formulation/evidence/taxonomy_consistency.json` measures
`9e335e9ba1bfcf77…` (495 B) and was last written at `00:36:36`, after the
declared `checked_at` `00:31:41`. FROZEN revision 28 pins the *new* hash, so the
schema's own declaration is one revision behind the evidence it cites, and the
binding's own rule ("must be refreshed … before any gate verdict") is not met.
The declared F0 taxonomy hash itself is fresh. **Fix:** refresh
`f0_binding.consistency_evidence_sha256` to `9e335e9b…` and re-freeze; that is a
one-line owner change, not a content change.

### Minor finding

**C11 (minor, process) — byte-identical post-freeze touch.**
`artifacts/formulation/evidence/taxonomy_consistency.json` was rewritten at
`00:36:36`, 88 s after FROZEN rev28's `frozen_at` (`00:35:08`). Its bytes equal
the frozen pin (C9 passes 44/44), so this is an idempotent-rewrite hygiene
signal, not a content defect.

### Rev11 hard findings: all six verified resolved at this hash

| rev11 finding | check | result |
|---|---|---|
| duplicate `revised_at` keys | C2 raw-node duplicate scan | no duplicates |
| future-dated timestamp | C3 wall-clock scan | none |
| `class_contract_pointer` to the authoring tree | C4 | points to canonical `#classes.AF-WCC-VAC-GEN`, segment reference + separate supplement pointer |
| undefined `AF_{I+}` | C5 | defined in `i_plus.predicate_abbreviation`, used by `statement_formal` |
| whole-curve vs canonical tail predicate (HF-025-1) | C6 | `quantifiers.formal` uses the single-q tail; negation matches; discriminating model shows the readings differ |
| D0 pair-binder ill-typedness (HF-025-2) | C7 | D0 is a tagged union `smooth \| (sobolev,s,delta)`; formal binds `r` over D0 |

## Method

`check_f1_rev12.py` is a standalone stdlib + PyYAML checker. Every input is read
**once** into memory; all hashes, parses and checks use those same bytes (no
TOCTOU re-read). A drift guard re-reads the bind set after the checks and the
run aborts into `inconclusive` if anything moved. Every check carries its own
falsifier, and eight planted-defect controls exercise the same predicate
functions (K1 duplicate key, K2 future date, K3 pointer redirect, K4 stale
evidence pin, K5 missing symbol definition, K6 whole-curve rewrite, K7
undeclared quantifier domain, K8 inflated conclusion type).

Re-run:

```bash
python3 artifacts/worker-053/f1_rev12_verify/check_f1_rev12.py
```

Exit 0 = checks ran drift-stable; exit 1 = drift (inconclusive). Outputs are
`report.json`, `controls.json`, `run.log`; hashes of all five artifacts are in
`hashes.txt`.

## Authority and non-claims

Evidence only. This task sets no gate verdict, no node status and writes nothing
under `research_map/`, `schemas/`, `ledger/` or `artifacts/formulation/`. It does
not adjudicate whether weak cosmic censorship is true, and it does not refresh
the stale pin it reports — that is the artifact owner's fix. A worker review is
not a gate verdict (`comms/PROTOCOL.md`, authority rule).
