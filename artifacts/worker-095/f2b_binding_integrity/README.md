# W095-F2B-BIND-INTEGRITY-01 — F2b class-binding / publication integrity receipt

Actor: `worker-095` · Node: `F2b` · Class: `AF-SCC-C0-VAC-GEN` · Gate: `G-FORM` (FORM-GATE-01)
Reviewed hash: `schemas/af_scc_c0_vacuum.yaml` @ `1bb78ce9b357` (rev 11), stable for the whole probe.
Verdict: **revise** (0 blocking, 3 major, 2 minor). `counts_as_full_schema_verdict=false`; this
receipt does not issue a gate verdict or promote the node.

## Reproduce

```bash
python3 artifacts/worker-095/f2b_binding_integrity/measure_binding.py       # re-measures, rewrites verdict.json
python3 artifacts/worker-095/f2b_binding_integrity/checkpoint_and_emit.py   # checkpoint + outbox events
```

11 raw evidence files land in `evidence/raw/` (snapshot, pointer matrix, vocabulary, f0_binding,
pins, duplicate keys, timestamps, gate run, class-separation, stability).

## Result at a glance

| check | status | note |
|---|---|---|
| B1 snapshot | pass | 14 binding-chain paths hashed, none missing |
| B2 identity | pass | exactly `F2b` / `AF-SCC-C0-VAC-GEN` |
| B3 contract pointer | **fail (major)** | resolves only in the authoring supplement |
| B3b pointer scope | pass | defect is systemic: all 3 frozen schemas point into the supplement |
| B4 vocab equivalence | pass | canonical alias == schema/gate canonical token under `VOCAB_ALIASES.json` |
| B4b canonical token hygiene | **fail (minor)** | canonical F0 stores accepted aliases |
| B5 f0_binding | pass | declared `276009f4f63d` == measured; consistency evidence == FROZEN pin |
| B6 publication pins | pass | F2b canonical == authoring mirror; rev26 pins match |
| B6b F0 role clarity | **fail (major)** | two divergent F0 documents, adjudication pending |
| B7 duplicate keys | **fail (major)** | 7 duplicate-key groups (`revised_at` ×8) — last-wins |
| B8 timestamp discipline | **fail (minor)** | effective `revised_at` 00:30:00 is future-dated |
| B9 gate corroboration | pass | pinned checker: `verdict=pass`, 0 failed rules |
| B10 class separation | pass | no class-merge / sibling-conflation finding |
| B11 stability | pass | zero drift across the probe |

## Findings

- **F-BIND-1 (major, systemic).** `class_contract_pointer` →
  `artifacts/formulation/formulation_taxonomy.yaml#class_contracts.AF-SCC-C0-VAC-GEN` resolves only
  in the authoring supplement; the declared canonical F0 has no `class_contracts` key. FROZEN rev26
  names the two F0 paths as separate logical artifacts and carries the
  `astra-life02-publish-f0` adjudication request (`blocked-pending-controller-adjudication`).
- **F-VOCAB-1 (minor).** Canonical F0 stores `strong_cosmic_censorship_C0` /
  `provisional_baire_residual`, accepted aliases of `scc_c0_future_inextendibility` /
  `residual_comeager`. The alias-normalized taxonomy consistency run is `consistent=true` with 0
  errors. This **refines** the prior F2a blocker (`w095-20260912T002417-blocker-binding`): the token
  difference is vocabulary hygiene, **not** a class-contract contradiction.
- **F-PROV-1 (major).** Duplicate YAML mapping keys make the revision history lossy under any
  last-wins loader.
- **F-TIME-1 (minor).** Future-dated `revised_at`; ordering by these stamps is unsafe (CF-14).
- **F-PUB-1 (info).** F2b publication is clean; the only divergent publication pair is F0.

## Falsifier carried forward

A pass in which (a) `class_contract_pointer` resolves on the authoritative canonical F0, (b) the
canonical F0 stores canonical conclusion/genericity tokens, (c) every YAML key has one value,
(d) FROZEN names exactly one authoritative F0 artifact per logical role with all pins matching
measured bytes, and (e) the pinned gate passes — falsifies the revise verdict.

Stop rule: one class-bound receipt + checkpoint; no schema edit, no gate verdict, no node
completion claim, no duplication of worker-096's F2b semantic review.
