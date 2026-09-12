# W090-F0-REV26 — independent audit of FROZEN.json revision 26

Node: F0 | Classes: AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN
Task: verify the rev26 adjudication-request claim and report binding/clock defects.
Reproduce: `python3 artifacts/worker-090/f0_rev26_adjudication/audit_f0_rev26.py`

## Reviewed bytes

| artifact | sha256 |
|---|---|
| artifacts/formulation/FROZEN.json (rev 26, frozen_at 00:24:49) | `2554e276a0db…` |
| research_map/formulation_taxonomy.yaml (declared F0) | `276009f4f63d…` |
| artifacts/formulation/formulation_taxonomy.yaml (class-contract supplement) | `c8e979a1eb48…` |
| schemas/af_wcc_vacuum.yaml | `9a8bd4c96800…` |
| schemas/af_scc_c2_vacuum.yaml | `b6123750b37d…` |
| schemas/af_scc_c0_vacuum.yaml | `1bb78ce9b357…` |
| schemas/taxonomy_cases.jsonl | `b9699119bbab…` |
| schemas/f1_falsifier_tests.jsonl | `c4c477adcb7a…` |

## Rev26 claim: SUPPORTED by the bytes

- C4a PASS — the two F0 artifacts have disjoint role keys: canonical carries
  `{class_ids, classes}`; the supplement carries `{class_contracts, frozen_classes,
  axis_registry, implication_ledger}`. Neither carries the other's role key.
- C4b PASS — identical four frozen class ids in both artifacts, and in
  `class_contracts`.
- C1 PASS — all 40 `FROZEN.files` sha256/byte pins match disk.
- C3 PASS — both `logical_artifacts` pins match disk.
- C6 PASS — all three schemas' `f0_binding` declares the measured canonical F0
  (`276009f4…`) and the measured supplement (`c8e979a1…`).
- C5 PASS — every schema `class_contract_pointer` resolves in the supplement and
  does **not** resolve in the canonical taxonomy (`failed_at: class_contracts`),
  exactly as rev26 states.
- C2 PASS — `frozen_at = 00:24:49` is behind wall clock (the rev25 future-dated
  manifest clock is corrected).

## Closure-blocking defects measured at rev26 (verdict: revise)

1. **C2b / C6b clock discipline (major).** The three canonical schemas keep
   effective `revised_at = 2026-09-12T00:30:00+08:00` (future vs a 00:27:23 wall
   clock) and `f0_binding.checked_at = 2026-09-12T00:30:00+08:00`. The timestamp
   prose says "corrected to mtime"; the machine-readable fields are still ahead of
   wall clock.
2. **C8 duplicate machine-readable keys (major).** `revised_at` occurs 7× in each
   schema (6 duplicates; last wins) with a stray `revised_at_unused`; the
   supplement `artifacts/formulation/formulation_taxonomy.yaml` itself carries
   `revised_at` 5×. Parser-dependent effective values; a revision-number-keyed
   verdict cannot distinguish the byte states.
3. **C7 stale downstream pin (minor, already owned).** `schemas/taxonomy_cases.jsonl`
   still pins F0 `565a6e50…`/`72d12c83…`, not the declared `276009f4…`.
   `schemas/f1_falsifier_tests.jsonl` is current at `9a8bd4c9…` (rebind landed).
4. **C4c dual conclusion-type vocabulary (warn).** The same conclusions are named
   with two vocabularies (`strong_cosmic_censorship_C0` vs
   `scc_c0_future_inextendibility`). Normalized comparison shows no contradiction
   (mapping declared in the script and falsifiable), but no shared machine-readable
   vocabulary exists across the two F0 artifacts — an interoperability gap a
   reader/checker can trip on.

## Policy note (controller decision, not decided here)

Rev26 withholds byte-identical publication because it claims the canonical
taxonomy and the authoring supplement are different artifacts (REC-1/REC-2 in
`artifacts/formulation/evidence/f0_mirror_conflict.json`). The measurements above
support the "different artifacts" reading. The canonical-path policy in
ASTRA_HANDOFF still requires byte-identical publication before verdicts bind, so
the controller must choose: pair-check exception (REC-1) or bounded re-freeze
with pointer refresh + re-review (REC-2). This audit does not decide that.

Authority: worker evidence only; cannot set gate verdict or node status.
