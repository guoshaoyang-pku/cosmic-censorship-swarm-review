# W054-F1-ADJUDICATE-01 — independent adjudication of contested F1 review findings

**Worker:** worker-054 (bounded execution worker) · **Class:** `AF-WCC-VAC-GEN` · **Node:** F1 ·
**Gate:** G-FORM · **Created:** 2026-09-12T00:26+08:00

## Why this task

The F1 review corpus is in **conflict at the same bytes** (`schemas/af_wcc_vacuum.yaml`
sha256 `9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503`, rev 11):

| side | reviewer | verdict | basis |
|---|---|---|---|
| accept | `astra-lead-audit` (`reviews/F1-review-lead-audit-r2.json`, 4.5) | accept | slots present, no inflation, clean class separation, mirror equality |
| revise | `worker-090` (HF090-01), `worker-094` (HF-094-2), `worker-059` (C12/C14/C15) | revise | contract pointer, duplicate YAML keys, future-dated timestamps |

Nobody had re-tested the two sides' *factual claims* side by side. This task does exactly that with
independent code, then classifies each defect as **semantic** vs **binding/hygiene** and maps it onto
the G-FORM criteria text read from the map at run time.

## Result — every contested claim reproduces; the camps differ on materiality, not facts

| check | question | result | materiality |
|---|---|---|---|
| A0 | inputs byte-pinned, no drift across the run | pass | binding |
| A1 | semantic slots / components / conclusion_type / quantifier order | pass | semantic |
| A2 | `class_contract_pointer` resolves in the **authoritative** tree | **fail** | binding |
| A3 | duplicate YAML mapping keys, parser-stable revision metadata | **fail** | binding |
| A4 | machine-readable timestamps sane vs wall clock | **fail** | binding |
| A5 | `f0_binding.declared_f0_sha256` == live canonical F0 | pass | semantic |
| A6 | no C0/C2 class token on the conclusion surface (own scan + map tooling) | pass | semantic |
| A7 | map node F1 + `FROZEN.json` pin the reviewed bytes | pass | binding |

**Verdict (worker-level, advisory): `revise`, score 4.0 — semantics pass, binding fails.**
Failed binding checks: A2, A3, A4.

### The three reproduced defects

1. **A2 — pointer dangles in the authoritative tree.** `class_contract_pointer =
   artifacts/formulation/formulation_taxonomy.yaml#class_contracts.AF-WCC-VAC-GEN` resolves only in the
   *authoring* tree. The canonical `research_map/formulation_taxonomy.yaml` carries the contract under
   top-level `classes` (no `class_contracts` key), and the two fragments are **structurally different**
   (`normalized_equal: false`). Under the canonical-path policy the pointer is unresolved.
2. **A3 — duplicate mapping keys make revision metadata parser-dependent.** `yaml.compose` finds
   `revised_at` ×7 and `revised_at_unused` ×2. A conforming first-wins reader gets
   `2026-09-11T23:34:10+08:00`; PyYAML last-wins gets `2026-09-12T00:30:00+08:00`. The duplicated key
   names are exactly `{revised_at, revised_at_unused}` — **disjoint from the semantic slot set**, so this
   is binding hygiene, not class semantics.
3. **A4 — future-dated timestamps.** Effective `revised_at` and `f0_binding.checked_at` are both
   `2026-09-12T00:30:00+08:00`, ahead of the run wall clock `2026-09-12T00:26:09+08:00` (>60 s tolerance).
   The in-document `revised_at` sequence is itself ordered; the defect is the clock offset, not the order.

### Adjudication of the conflict

The accept side is **not falsified on semantics** — A1/A5/A6 independently reproduce its substantive
findings. It is **incomplete on binding hygiene**: it lists no check of duplicate keys, timestamp
sanity, or canonical pointer resolution. The revise side's factual claims all reproduce, and their
correct classification is binding/hygiene rather than class-semantic. The two verdicts are therefore
compatible; the operative question is whether binding hygiene blocks a *freeze-stable* accept. It does:
a cited `sha256` whose revision metadata two conforming readers parse differently cannot anchor an
accept, and a class-contract pointer that resolves only in a non-authoritative tree cannot anchor the
class binding. Hence `revise`, with the minimal fix list below.

### Minimal fix (for the artifact owner, `lead-formulation`; not applied here)

1. collapse the 7 `revised_at` and 2 `revised_at_unused` keys into one ordered revision log
   (or key them `rev3…rev26`) so no conforming reader can disagree;
2. re-date `revised_at` / `f0_binding.checked_at` to wall-clock-consistent values;
3. either repoint `class_contract_pointer` at
   `research_map/formulation_taxonomy.yaml#classes.AF-WCC-VAC-GEN`, or publish the authoring taxonomy
   byte-identically so the pointer's target is authoritative.

## Artifacts and pins (measured at 2026-09-12T00:26:09+08:00, no drift after the run)

- `artifacts/worker-054/f1_adjudication/report.json` — full machine report (checks, pins, verdict, falsifier)
- `artifacts/worker-054/f1_adjudication/adjudicate_f1.py` — self-contained adjudicator
- `artifacts/worker-054/f1_adjudication/snapshot/af_wcc_vacuum.9a8bd4c96800.yaml` — exact reviewed bytes
- `schemas/af_wcc_vacuum.yaml` @ `9a8bd4c96800…` (rev 11) — reviewed artifact
- `artifacts/formulation/schemas/af_wcc_vacuum.yaml` @ `9a8bd4c96800…` — mirror, aligned
- `research_map/formulation_taxonomy.yaml` @ `276009f4f63d…` (canonical F0) vs
  `artifacts/formulation/formulation_taxonomy.yaml` @ `c8e979a1eb48…` — **divergent**
- `artifacts/formulation/FROZEN.json` @ `2554e276a0db…` (revision 26) — pins the reviewed F1 bytes
- map `research_map/research_map.json` @ `4fd40d4d1e4f…`

Reproduce: `python3 artifacts/worker-054/f1_adjudication/adjudicate_f1.py`

## Falsifier

Re-run the script in an unchanged tree. The adjudication is falsified if: (a) any pinned input hash
differs between the start and end re-measure; (b) `yaml.compose` reports no duplicate mapping keys in
`schemas/af_wcc_vacuum.yaml`; (c) `class_contract_pointer` resolves in
`research_map/formulation_taxonomy.yaml` at the pinned canonical hash; (d) the effective `revised_at`
and `f0_binding.checked_at` are not future-dated at re-run wall clock; (e) any A1 semantic check fails
(flipping semantics from pass to fail); or (f) the canonical and authoring taxonomy are byte-identical
(removing the pointer defect).

## Scope limits — what this is not

- **Not a gate verdict.** Worker events cannot set `status=done`, `validation_status=passed`, or a gate
  verdict (ASTRA_HANDOFF 2026-09-12); only the controller and group leads move those.
- **Not physics.** It tests the schema artifact contract/binding, not weak cosmic censorship.
- **No mutation.** No canonical artifact was modified; bytes were read and snapshotted only.
- **Independence.** The worker did not author the schema or any review under adjudication and imports no
  reviewer code; the only borrowed tool is `research_map/class_separation.py` as *corroboration* for A6,
  with an own token scan recorded alongside it.
