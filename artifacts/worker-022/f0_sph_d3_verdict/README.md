# W022-F0-SPH-D3-INDEP-VERDICT-01 — independent verification of HF-059-SPH-01

**Verdict: CORROBORATED (14/14 checks, 6/6 controls, no pin drift).** Score 4.0.
Class `AF-WCC-SCALAR-SPH`, node F0, gate G-F0. Worker evidence only.

## What was verified

Worker-059's blocking finding HF-059-SPH-01 claims that at the FROZEN-pinned F0 pair the stored
D3 discharge-scope records disagree about the spherical-scalar class while the canonical
taxonomy-consistency certificate is green. This run reproduces that independently at

- A = `research_map/formulation_taxonomy.yaml` **0abb9ed8a961** (declared taxonomy, rev5)
- B = `artifacts/formulation/formulation_taxonomy.yaml` **d7419b4e8963** (class-contract supplement)
- FROZEN rev29 **815e08079aef** pins both hashes; certificate
  `artifacts/formulation/evidence/taxonomy_consistency.json` **9e335e9ba1bf**

## Measured facts

1. **A (stored D3, `class_scope_adjudication.resolved_divergences`)**: `status: resolved`,
   resolution "...confirmed discharged for **ALL FOUR classes, including AF-WCC-SCALAR-SPH**,
   whose conclusion text carried the demoted set-based wording until rev5".
2. **A (two independent secondary locations)**: `revision_note_rev5` clause (g) repeats the
   scalar-class D3 discharge; the scalar class conclusion carries "[rev5: D1/D3 discharge for
   this class".
3. **B (stored D3, `contract_divergences.items`)**: `class: all three vacuum classes`,
   `status: resolved`, resolution text names neither the scalar class nor a four-class scope.
   A whole-document scan found no other B-side scalar D3/discharge record (0 hits).
4. **Certificate green**: `consistent: true`, `errors: []`, `contract_divergences: []`,
   `classes_compared` lists four classes including `AF-WCC-SCALAR-SPH`.
5. **Why the certificate is silent (static + dynamic)**: the checker never reads the stored
   records; it recomputes D1-D3 from class conclusion texts. Reproduced in a throwaway sandbox
   (exit 0, `CONSISTENT (4 classes, 0 contract-text divergences)`), and the silence control
   mutating only the stored records leaves the certificate green and unchanged.
6. **Materiality**: on the live map, 146 claims bind `AF-WCC-SCALAR-SPH`; **0** are
   `theorem`/`conditional_theorem`. The defect is record-integrity, not class semantics, and no
   promoted WCC result depends on it.

## Controls (single-defect mutants, all fire)

| id | mutation | required | observed |
|---|---|---|---|
| M1 | A D3 scope four-class -> three-class | C8 flips to AGREE | PASS |
| M2 | B D3 scope three-class -> four-class | C8 flips to AGREE | PASS |
| M3 | A's two secondary scalar-D3 statements removed | C4 false, C8 still CONTRADICTION | PASS |
| M4 | unrelated A test-case description edited | D3 verdict unchanged | PASS |
| M5 | B D1 class scope edited | D3 verdict unchanged | PASS |
| M6 | A truncated mid-document (unclosed flow sequence) | parse fails closed | PASS |

## What this does and does not say

- **Does**: the stored D3 records at the pinned bytes are not scope-consistent, and the green
  certificate cannot be cited as evidence that the scalar class is discharged; worker-059's
  finding is reproduced by an independent instrument.
- **Does not**: change class semantics, assert any physics, edit A/B/FROZEN/the certificate or any
  canonical path, set node status, `validation_status`, or a gate verdict. Adjudicating whether
  the stored records are binding prose is a controller/owner decision.

## Falsifier

A single-scope D3 record in both A and B at pinned bytes; or a B-side scalar D3 discharge
resolution anywhere in B; or a canonical certificate that is not green — any one voids this
corroboration. Pin drift start-to-end voids the instrument.

## Reproduce

```bash
python3 artifacts/worker-022/f0_sph_d3_verdict/verify_f0_sph_d3_022.py   # exit 0 = CORROBORATED
```

Read-only on canonical paths; the checker reproduction and all mutants run under
`artifacts/worker-022/f0_sph_d3_verdict/sandbox/`.

## Files

- `preregistration.json` — pins, C1-C14, M1-M6, verdict rule, falsifier (frozen before measurement)
- `verify_f0_sph_d3_022.py` — independent stdlib+PyYAML verifier (no canonical/worker imports)
- `report.json` — full check/control table, sandbox transcripts, pin drift
- `sandbox/` — checker run on pinned bytes and on the stored-record mutant
