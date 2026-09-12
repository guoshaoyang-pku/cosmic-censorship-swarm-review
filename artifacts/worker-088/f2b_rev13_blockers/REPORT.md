# W088-F2B-REV13-BLOCKERS — consolidated live-blocker measurement + repair candidate

- **Worker**: worker-088 (bounded execution worker; no gate/node status moved)
- **Class**: `AF-SCC-C0-VAC-GEN` — **Node**: `F2b` — **Gate**: `G-FORM`
- **Bound bytes**: `schemas/af_scc_c0_vacuum.yaml` = `b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c`
  (measured before and after every probe; no drift; canonical path never written)
- **Why this task**: the controller's pass-06 G-FORM audit and REC-23 leave F2b at
  `0 distinct accepts`; the standing requirement is `F2b >= 2 accepts at one stable hash`.
  Six independent rev13 verdicts (worker-015/034/044/066/075/095) raise overlapping
  hard failures. This artifact consolidates them into one independently measured,
  machine-checkable disposition ledger and a repair candidate that clears all four
  families at a single candidate hash.

## Dispositions at the bound hash (probe: `check_f2b_rev13_blockers.py`)

| id | family | source verdicts | disposition | line |
|---|---|---|---|---|
| B1 | inverted containment premise in `forbidden_transfers[0].reason` ("C2 is a strictly **larger** extension class") vs the file's own chain `E_C2 ⊂ E_{C^1,1} ⊂ E_H2loc ⊂ E_C0` | W034 HF-W034R2-F2B-1, W044 HF-044-INT-H1, W066 R13-F2B-H2, W075 C8 | **LIVE_DEFECT** | 246 |
| B2 | stale containment denial in `regularity.must_not_conflate[0]` ("No containment with C2 or C0 is asserted here") while the same file asserts the chain at 239/243/254; the C2 sibling already records that exact phrase as wrong | W066 R13-F2B-H1 | **LIVE_DEFECT** | 152 |
| B3 | vocabulary binding gap: `conclusion.conclusion_type=scc_c0_future_inextendibility` and `genericity.kind=residual_comeager` are VOCAB_ALIASES canonical tokens, absent from the frozen F0 allowed-lists; no alias registry is bound, so literal-membership detectors flag and equivalence is undecidable from the artifact alone | W075 C6b HF-1, W044 HF-044-INT-A6 | **BINDING_GAP** | 211 / 157+ |
| B4 | consistency evidence not self-verifying: `f0_binding.consistency_evidence` resolves but records only paths and `consistent=true`; no sha256 of the compared inputs, so the claim is not reproducible from the evidence file | W044 HF-044-INT-A2, W088 HF-088-F2B-1 (previously) | **LIVE_DEFECT** | 309 |

The F0 pin `0abb9ed8a961`, the supplementary taxonomy `d7419b4e8963`, the ledger
`a1674f094979` and the evidence `9e335e9ba1bf` were all re-measured at their declared
values. The sibling F2a `e9a27996dfd3` carries the corrected direction wording at both
B1/B2-analogous slots, which is independent evidence that the F2b clauses are stale
carry-overs rather than a defended reading.

## Repair candidate (worker-owned, canonical paths untouched)

`candidate/af_scc_c0_vacuum.rev13repair.yaml` = `b598b59e09e5…`, four edits:

- **R1**: `reason: "E_C2 is a strictly smaller extension set than E_C0, so C2-inextendibility is strictly weaker"` (consequent and forbidden-transfer conclusion unchanged).
- **R2**: denial sentence replaced by the sibling's corrected wording (H2_loc distinct as a regularity value, extension sets nested; see `extension_class_containment`).
- **R3**: `extensions.vocabulary_binding` binds `artifacts/formulation/VOCAB_ALIASES.json` by path+sha256 and records per field `{token, f0_allowed_equivalent_alias, f0_literal_member: false, resolution: equivalent_via_bound_alias_registry}`; **owner adjudication is flagged in the block** — no class-semantics change is proposed, and F0 stays frozen.
- **R4**: self-verifying evidence copy records `map_taxonomy_sha256`, `lead_contract_sha256`, `alias_registry_sha256`; `f0_binding.consistency_evidence_sha256` is re-stamped to it in the same candidate revision (the canonical generator must be updated to emit those fields).

Verification of the candidate: probe verdict `NOT_LIVE` for B1–B4;
`artifacts/formulation/tools/check_class_schema.py` → `pass`, 0 failed rules (the
binding block is nested under `extensions:` to satisfy R22);
`research_map.class_separation.findings_for_text` → `[]`; zero duplicate YAML keys.

## Falsifiers

- **B1/B2**: show a containment-respecting reading in which E_C2 is strictly larger
  than E_C0, or a revision whose own chain makes C2 outermost; or show the B2 sentence
  cannot be read as an extension-set claim.
- **B3**: a gate-owner ruling that the F0 allowed-list is operative (then schemas must
  carry the literal F0 tokens and this binding-gap repair is void), or evidence of an
  alias registry already bound in the frozen bytes.
- **B4**: produce an evidence document at the declared path whose bytes contain the
  sha256 of each compared input and reproduce `consistent=true`.
- **Candidate**: any write to the canonical paths or to the pinned inputs voids these
  measurements; the candidate binds only to live `b2ab6acb2bbe` and FROZEN rev29
  `815e08079aef`.

## Not claimed

No gate verdict, no node status, no `validation_status`, no theorem, no physics claim,
no novelty claim. This is a read-only measurement plus a worker-owned candidate for the
formulation lead; the repair must be landed by the owner and re-reviewed at its new hash.
