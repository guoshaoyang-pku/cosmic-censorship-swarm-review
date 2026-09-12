# W001-T1-TRANSFER-PRECONDITION-01 — one-page summary

**Worker:** worker-001 · **Task id:** W001-T1-TRANSFER-PRECONDITION-01 · **Node:** F2b (source class), F2a recorded
**Class binding:** AF-SCC-C0-VAC-GEN → AF-SCC-C2-VAC-GEN (AF-WCC-VAC-GEN recorded as family sibling only)
**Gate context:** G-FORM unmet item *"no single frozen data class (s,delta,norm) is shared by F1/F2a/F2b, which disables the licensed C0=>C2 transfer"*
**Nature:** artifact-and-binding measurement. No mathematical claim, no gate verdict, no node status, no canonical write.

## Question

At the rev13 pins, do F2a and F2b discharge the guards of canonical F0 transfer rule **T1**
(`research_map/formulation_taxonomy.yaml#transfer_rules.allowed[0]`)?

* G1 `data_class fields must match exactly (including s, delta once F2 fixes them)`
* G2 `genericity_kind and genericity_topology must match exactly`

## Verdict — `T1_PRECONDITION_UNMET` (transfer blocked)

Reason codes: `INDEX_NOT_FROZEN`, `NORM_NOT_DECLARED`, `DATA_CLASS_NOT_EXACT_MATCH`.

| Check | Result |
|---|---|
| C1 T1 rule present, C0→C2, guards recorded | PASS |
| C2 C0 vs C2 `data_class` exact match | **FAIL** — 2 leaf diffs, both provenance-only; **0 semantic, 0 index diffs** |
| C3 index frozen (`s`, `delta` single numeric) | **FAIL** — all three classes declare ranges: `s > 5/2`, `delta in (1/2, 1)` |
| C3 `norm` slot declared | **FAIL** — no `norm` leaf in any of F1/F2a/F2b `data_class` |
| C4 genericity kind / topology / ambient space C0 vs C2 | PASS (`residual_comeager`, subspace topology, identical ambient text) |
| C4 genericity strict equality | FAIL — `excluded_set` wording: C0 "admits" vs C2 "DOES admit"; not a T1 guard field |
| C5 triple-wise shared class | C0–C2: 2 provenance diffs, 0 semantic; WCC–SCC pairs: 6–9 semantic diffs (matter/symmetry) |
| C6 conclusions distinct, no merged C0/C2 token | PASS |

Controls CT1–CT8 (identical copy, seeded s/delta/kind/topology mutations, merged-token, frozen-detector,
norm-detector) **8/8 pass**; pin drift exits 3, control failure exits 4, both without a verdict.

## Independent correction to the gate wording

T1 is an **intra-SCC** rule. Its guards bind F2a and F2b only; F1 (`AF-WCC-VAC-GEN`) participates in no
T1 guard (`forbidden X4` explicitly forbids any WCC↔SCC transfer). The blocker is therefore the
**C0/C2 pair plus the unfrozen `s`, `delta` and the absent `norm`** — not the absence of a class shared
by all three. C0 and C2 already agree on every semantic `data_class` leaf (they differ only in two
`adm_mass` provenance strings), and their genericity kind/topology agree.

## Decisive falsifiers

* Any pinned sha256 moving voids the measurement (harness exits 3).
* At the pins, `T1_PRECONDITION_UNMET` is falsified if F2a and F2b declare byte-identical `data_class`
  subtrees **and** single numeric `s`, `delta` **and** a declared `norm` slot **and** identical
  genericity kind/topology — or if canonical F0 contains no allowed C0→C2 rule.
* A frozen-field definition is falsified by a downstream artifact that fixes `s`, `delta` and the norm
  at one value in a way this projection does not read.

## Artifacts (sha256)

* `audit_t1_transfer.py` — fail-closed harness
* `report.json` — full checks, controls, pins
* `PINNED.json` — measured pin manifest
* `CHECKPOINT.json` — worker checkpoint (runtime copy at `runtime/state/worker-001_checkpoint_t1.json`)
