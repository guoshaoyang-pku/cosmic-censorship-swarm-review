# W060-XCLASS-DATACLASS-01 — is the licensed C0⇒C2 transfer disabled by a data-class divergence?

- **Worker:** worker-060 (bounded execution worker; one class-bound task, then exit)
- **Nodes / classes / gate:** F1/F2a/F2b · `AF-WCC-VAC-GEN` / `AF-SCC-C2-VAC-GEN` / `AF-SCC-C0-VAC-GEN` · G-FORM
- **Pins (all five measured equal at run time; snapshots under `snapshots/`):**

  | tag | path | sha256 (prefix) |
  |---|---|---|
  | F1 | `schemas/af_wcc_vacuum.yaml` | `9a8bd4c9680042a408…` |
  | F2a | `schemas/af_scc_c2_vacuum.yaml` | `b6123750b37d8bee1e92…` |
  | F2b | `schemas/af_scc_c0_vacuum.yaml` | `1bb78ce9b3572cdac229…` |
  | F0 canonical | `research_map/formulation_taxonomy.yaml` | `276009f4f63dbf838f32…` |
  | F0 authoring | `artifacts/formulation/formulation_taxonomy.yaml` | `c8e979a1eb48969be3b1…` |

- **Verdict:** **revise** (advisory, score 3.5) — the literal T1 guard fails, but the failure is
  annotation-level, not a data-space mismatch. 10/10 checks pass; 5/5 negative controls behaved.
- **Evidence:** `artifacts/worker-060/xclass_dataclass_adjudication/evidence.json`
  (`sha256 29f9a88c42a6a5d950f1c43e563bfe0784defc0579a7921475e7349b3eb08c4f`).
- **Reproduce:**
  `python3 artifacts/worker-060/xclass_dataclass_adjudication/verify_xclass_dataclass.py --snapshots`
  (exit 0 = adjudication; exit 2 = a pin drifted, no verdict reported).

No assignment card existed in `comms/inbox/worker-060.jsonl`. This is a self-proposed, bounded,
class-bound adjudication. It claims no node completion, no gate verdict, and no physics result.

## Why this task

The map's G-FORM unmet list contains: *"no single frozen data class (s,delta,norm) is shared by
F1/F2a/F2b, which disables the licensed C0⇒C2 transfer"*. The canonical taxonomy licenses exactly
one transfer, T1 (C0⇒C2), guarded by *"data_class fields must match exactly (including s, delta
once F2 fixes them)"*. Worker-071 measured that the three `data_class` blocks are not equal and
explicitly left undecided *which reading the guard should use*. This task decides that, with its
own extractor (no other worker's checker and no canonical gate module is imported).

## Measurements at the pinned hashes

`data_class` has **23 leaf paths** across the three schemas. Nine differ under canonical-JSON
(strict) comparison:

| # | path | F1 | F2a | F2b | class |
|---|---|---|---|---|---|
| 1 | `adm_mass.hypotheses_reconciliation` | — | — | present | annotation |
| 2 | `adm_mass.locator` | — | "to be supplied by L1" | "to be supplied by L1 (Schoen-Yau / Witten)…" | annotation |
| 3 | `adm_mass.rigidity` | present | — | — | annotation |
| 4 | `asymptotic_decay.parity_conditions` | "not imposed; imposing … different class" | "not imposed" | "not imposed" | data-space field, leading directive identical |
| 5 | `diffeo_quotient` | long form | short form | short form | annotation |
| 6 | `excluded_data` | present | — | — | annotation |
| 7 | `gauge` | long form | short form | short form | annotation |
| 8 | `regularity_class.sobolev_variant.spaces` | "…K in H^{s-1}_{delta+1} (weighted Sobolev)" | "…K in H^{s-1}_{delta+1}" | same as F2a | data-space field, trailing parenthetical only |
| 9 | `regularity_class.sobolev_variant.status` | long form | short form | short form | annotation |

**The 15 data-space-core keys** (`matter`, `cosmological_constant`, `equations`,
`constraints.hamiltonian`, `constraints.momentum`, `regularity_class.default`,
`regularity_class.sobolev_variant.{s,delta,spaces}`, `asymptotic_decay.{metric,
second_fundamental_form,parity_conditions}`, `symmetry`, `adm_mass.{exists,sign}`) — the fields
that fix the admissible data space — give:

| comparison | strict | normalized (2 declared rules, below) |
|---|---|---|
| three-way F1/F2a/F2b | 2 diff paths (#4, #8) | **0 diff paths (15/15 equal)** |
| licensed pair F2a vs F2b | **0 diff paths (15/15 equal)** | 0 diff paths |

Declared normalization rules (additive annotations only, both auditable in `evidence.json`):
`sobolev_variant.spaces` → strip a single trailing parenthesized note; `parity_conditions` → take
the leading directive before the first `;`.

## Adjudication

1. **The literal T1 guard fails** at the pinned hashes: between the licensed pair F2a (C2) and
   F2b (C0) exactly two paths differ, `adm_mass.locator` and
   `adm_mass.hypotheses_reconciliation`; both are provenance/annotation fields.
2. **Materiality: the C0⇒C2 transfer is *not* disabled by a data-space divergence.** All 15
   data-space-core keys — including the `(s, delta)` pair the guard singles out, and `spaces` —
   are strictly equal between F2a and F2b. The gate-audit wording "no single frozen data class is
   shared … disables the licensed transfer" is therefore **overstated for T1** and should be
   restated as an annotation-level divergence.
3. **Three-way reading:** F1 differs from F2a/F2b only in annotation fields, plus the two
   normalizable annotation forms (#4, #8). F1 is WCC and has no licensed transfer with either SCC
   class (taxonomy X4), so these differences do not touch a licensed inference.
4. **The authoring claim** `class_contracts.AF-SCC-C0-VAC-GEN.data_class_freeze` ("…identical
   across F1/F2a/F2b…") is **refuted at T0/T1** (bytes and canonical JSON differ) and **confirmed
   at T3** for the 15 data-space keys. The claim is true in intent, false as written.
5. **Recommended dispositions (lead-formulation owns the text; advisory only):**
   - **D1 (preferred):** amend T1's guard to name an explicit data-space-core key set (the 15
     paths above) and declare annotation/provenance fields out of the exact-match guard. T1 then
     passes at these hashes with no schema edit.
   - **D2 (not recommended):** align the annotation fields byte-for-byte across the schemas; this
     deletes review-response provenance (worker-16 / worker-18 acknowledgements) silently.
   - Either way, restate the G-FORM unmet item: the blocker is annotation-level, not a difference
     in `(s, delta, norm)` or any data-space-defining field.

## Checker self-test (negative controls)

| id | mutation | expected | observed |
|---|---|---|---|
| C1 | F2b `delta` → `delta in (1/2, 1]` | data-space mismatch | caught (`…sobolev_variant.delta`) |
| C2 | F2a `constraints.momentum` → `0 = 0` | data-space mismatch | caught |
| C3 | F2a `spaces` → drop the `K` term | data-space mismatch | caught (`…sobolev_variant.spaces`) |
| C4 | F2a `parity_conditions` → `imposed` | data-space mismatch | caught |
| C5 | F2a `adm_mass.locator` → different text | annotation only, **not** data-space | strict flagged, data-space clean |

Pin-drift control: mutating F2b's `delta` in a scratch root makes the script exit 2 with
`PIN_DRIFT` before reporting any verdict. Two consecutive runs produce identical evidence
payloads apart from `created_at`.

## Falsifier (this adjudication dies if)

At the five pinned hashes: **if any of the 15 data-space-core keys differs strictly between
`schemas/af_scc_c2_vacuum.yaml` (F2a) and `schemas/af_scc_c0_vacuum.yaml` (F2b), the materiality
conclusion is refuted** and C0⇒C2 is disabled by a data-space mismatch. If a future T1 guard names
a different key set or an explicit annotation-exclusion clause, this verdict binds only to the
guard text quoted above. Any pin drift voids the adjudication at the drifted path.

## Non-claims and scope limits

- No theorem, counterexample, convergence result, or gate verdict is claimed. Worker events cannot
  set `status=done`, `validation_status=passed`, or a gate verdict.
- Scope is the `data_class` subtree only. Quantifiers, genericity, conclusion, visibility, the
  F0 canonical-vs-authoring divergence, and the F1 contract-pointer/duplicate-key findings are out
  of scope.
- `AF-WCC-SCALAR-SPH` (N0) is out of scope.
- The two normalization rules are declared and additive; they cannot merge two different data
  spaces (controls C1–C4 exercise the strict detector).
