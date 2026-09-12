# W085-F1-CARD-CLOSE-05 — r2 F1 card closure + stability reconciliation (worker-085)

Read-only, bounded, class-bound (`AF-WCC-VAC-GEN`, node F1, gate G-FORM). No verdict, gate
verdict, node status or `validation_status` is set. Artifacts:
`probe_card_reconcile.py`, `report.json` (machine), this file.

## Headline

| item | result |
|---|---|
| Card `audit-r2-F1-b` declared pin | `cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3` |
| Current `schemas/af_wcc_vacuum.yaml` | `d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d` (rev13) |
| Pin state | **superseded / moving target**; card executed at the declared pin *before* the move |
| Verdict `reviews/F1-review-rev27-b.json` | present, sha256 `cae70876…`, equals the sha recorded in its own checkpoint; bound to `cce9c601…` |
| Review event | ingested **exactly once**; 0 worker-085 lines in `comms/rejected.jsonl` |
| Addendum | folded into `rev27-b` (`f0_binding_chain`, `refresh_rule_assessment`, `HF-085-BIND-01`) |
| New verdict emitted | **none** — the card's moving-target stop rule bars it at the new bytes, and rev13 `d9cebb94…` already carries a worker-085 accept |
| Declared `f0_binding` hashes at current bytes | **6/6 resolved, 0 mismatches** |
| Schemas' refresh rule | **satisfied** (declared F0 `0abb9ed8…` unchanged; consistency evidence `9e335e9b…` matches) |
| FROZEN rev29 (`815e0807…`) pins | **6/6 match** the measured files |
| Measurement window | clean (all input hashes identical before/after) |

## What was checked

1. **Closure** — both inbox cards, their declared pin, the verdict file, the two checkpoints,
   the accepted stream and the reject stream. `HF-085-BIND-01` (declared `675a99d0…` vs
   measured `9e335e9b…` under the card pin) is **RESOLVED at `d9cebb94…`**: all three schemas
   now declare `9e335e9b…`, which is what the named referent measures.
2. **Bind chain (addendum, current bytes)** — for F1/F2a/F2b: `declared_f0_sha256` →
   `research_map/formulation_taxonomy.yaml` resolved; `consistency_evidence_sha256` → the
   consistency JSON resolved; both pointers (`class_contract_pointer`,
   `class_contract_supplement_pointer`) resolve in their YAML targets. The supplement pointer
   still declares no hash at point of use (live bytes `d7419b4e…` = FROZEN rev29 logical pin).
3. **Refresh rule** — not triggered: the declared F0 bytes are unchanged since `checked_at`,
   and the consistency evidence matches its declared hash. Verified independently, not trusted
   from the schema text.
4. **Stability since the verdicts** — F1/F2a/F2b hashes equal both the rev13 review pin and the
   rev13 checkpoint record; FROZEN rev29 pins match current bytes.
5. **Cross-artifact shared fields** — `data_class` core values (`matter`, `equations`,
   `cosmological_constant`, `constraints`, `symmetry`) are equal across F1/F2a/F2b; all
   differing keys are presentational/elaborative (`gauge`/`diffeo_quotient` wording, F1-only
   `excluded_data`, F2b-only `hypotheses_reconciliation`). `regularity` differences are wording
   (`and`/comma, citation-status detail) plus the class-defining `extension_regularity`
   (`null`/C2/C0). `extension_predicate` is absent in F1 by design (WCC asserts no extension
   claim) and present in both siblings.

## Findings (worker evidence only)

- **F-085C-01** *(informational)* — card closure: executed at pin, superseded, no re-verdict.
- **F-085C-02** *(low, comms)* — both bind-chain addendum cards (worker-085 and worker-071)
  name `reviews/F1-review-rev27-a.json`; the stop rule ("fold into the single verdict file
  already assigned") makes worker-085 fold into its own `rev27-b`. Dispatch field is
  cross-wired; artifact record is correct.
- **F-085C-03** *(low, cross-artifact)* — F2b (`b2ab6acb…`) still contains both
  "No containment with C2 or C0 is asserted here" (must_not_conflate) and
  "E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2" (implication_ledger), while F2a
  asserts the chain. Persists unchanged at the current pin; F1 class statement unaffected.
- **F-085C-04** *(low, carried)* — `f0_binding.class_contract_supplement_pointer` declares no
  sha256 at point of use (carried from `F-085R-05`).

## Falsifiers

- `reviews/F1-review-rev27-b.json` no longer hashes to `cae708765818fcc268eed05c124b2fd23867d9de520257608978ba0c8e480049`,
  or its review event is absent/duplicated in `research_map/events.jsonl`.
- Any declared `f0_binding` hash fails to resolve against its named referent at the measured bytes.
- The probe's before/after input hashes differ (drift inside the window).
- A duplicate worker-085 F1 verdict at the card pin exists without its own pin.

**Next falsifier:** re-run `probe_card_reconcile.py`; a future F0 amendment that changes
`research_map/formulation_taxonomy.yaml` triggers the schemas' refresh rule and voids this
binding confirmation (not the closure record).

## Authority

Worker evidence only. No canonical artifact, taxonomy, manifest, map or review file was
modified; no gate verdict, node status or `validation_status` claimed.
