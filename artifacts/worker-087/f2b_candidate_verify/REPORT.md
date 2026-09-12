# W087-F2B-CANDIDATE-INDEP-VERIFY-01 — independent verification of the F2b rev13repair candidate

- **Worker**: worker-087 (bounded execution worker; no inbox card existed for this slot)
- **Class**: `AF-SCC-C0-VAC-GEN` — **Node**: F2b — **Gate**: G-FORM
- **Verifies**: `artifacts/worker-088/f2b_rev13_blockers/candidate/af_scc_c0_vacuum.rev13repair.yaml`
  = `b598b59e09e56ee4f9e61d1c80f54d702b0bbf14ec9ee646172bc4a87710557a` (packet with
  `candidate/artifacts/formulation/evidence/taxonomy_consistency.json` = `a03ba9c529e88e0d…`)
- **Against**: live canonical `schemas/af_scc_c0_vacuum.yaml` = `b2ab6acb2bbe7f86…`,
  FROZEN revision 29 = `815e08079aefbc16…`
- **Instrument**: `verify_candidate_087.py` (own duplicate-key-safe YAML loader, own leaf diff,
  own B1–B4 detectors, four mutation controls; read-only, all 8 pins re-measured before and
  after the run, drift-free: `true`)
- **Raw run**: `run1.json`; **verdict**: `accept` (packet-level, conditional), score 4.0.
  `counts_toward_gate_accept: false` — this is a candidate verification, not a full-schema
  verdict at a canonical pin.

## What was reproduced at the canonical bytes (defects)

| family | canonical evidence | status |
|---|---|---|
| B1 inverted containment premise | `implication_ledger.forbidden_transfers[0].reason` = "C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker" while the file's own chain makes `E_C2` the innermost set | reproduced |
| B2 stale containment denial | `regularity.must_not_conflate[0]` carries "No containment with C2 or C0 is asserted here" | reproduced |
| B3 unbound vocabulary | `conclusion_type=scc_c0_future_inextendibility`, `genericity.kind=residual_comeager` are not literal members of the frozen F0 allowed lists and no alias registry is bound | reproduced |
| B4 non-self-verifying evidence | canonical `artifacts/formulation/evidence/taxonomy_consistency.json` (`9e335e9b…`) records `consistent=true` but no sha256 of any compared input | reproduced |

## What the candidate clears

- **B1 closed**: reason reads "E_C2 is a strictly smaller extension set than E_C0, so
  C2-inextendibility is strictly weaker"; direction agrees with the file's declared chain and
  with `one_way_entailments`.
- **B2 closed**: the denial is gone, the nesting statement is present, and the banned phrase
  "strictly between" appears **only as a mention inside the ban**, not as a positive assertion.
  This avoids the wording defect worker-100 found in the competing worker-022 candidate
  (`HF-W100-02`, "sits strictly between" retained while banning the phrase).
- **B3 resolved by binding**: `extensions.vocabulary_binding` binds
  `artifacts/formulation/VOCAB_ALIASES.json` = `46cd9f1e…` (measured, matches); both declared
  aliases are members of their registry lists. The two tokens remain non-literal F0 members by
  design, and the candidate itself flags that **owner adjudication is required** — recorded here
  as an open dependency, not as a defect of the candidate.
- **B4 closed inside the packet**: the packet evidence copy records `map_taxonomy_sha256`,
  `lead_contract_sha256`, `alias_registry_sha256`, all three matching the live bytes.
- **No smuggled change**: 0 unexpected leaf-path diffs; `class_id`, `node_id`, `schema_version`,
  `scope_statement`, `quantifiers`, `topology`, both conclusion statements and `anti_scope` are
  byte-equal to canonical.
- **Controls 4/4 fire**; the canonical class-schema checker returns `pass` on the candidate
  (`rc=0`) — but it also passes on the canonical bytes, so the checker does **not** discriminate
  B1/B2 and cannot be the acceptance evidence for this repair.

## Landing condition (the one conditional finding)

The candidate schema declares `f0_binding.consistency_evidence_sha256 = a03ba9c5…` at the
canonical evidence path `artifacts/formulation/evidence/taxonomy_consistency.json`, whose live
bytes are `9e335e9b…`. The packet is self-consistent when rooted at the repo root (both files
landed together), but **a schema-only landing creates a declared-hash mismatch**. The owner must
either land schema + evidence atomically (and update `check_taxonomy_consistency.py` to emit the
three input hashes, as the candidate's own `generator` note requires), or re-stamp to a document
published at the declared path. Any landing moves FROZEN to a new revision and voids all rev13
verdicts.

## Falsifier

Re-run `verify_candidate_087.py` at the same eight pins: any pin move, any changed detector
verdict, a packet whose declared evidence hash fails to resolve inside the packet, or a
schema-only landing whose declared hash does not resolve at the declared path voids this
verification. A containment-respecting reading in which `E_C2` is strictly larger than `E_C0`,
or a reading in which the canonical `must_not_conflate[0]` sentence is not normative content,
voids the B1/B2 defect reproduction.

## Not claimed

No gate verdict, no node status, no `validation_status`, no theorem, no physics claim, no
adoption of the candidate. Worker events cannot move gates or status.
