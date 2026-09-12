# W035-F2A-REV12-INDEP-VERDICT-01 — independent full-schema verdict on F2a (AF-SCC-C2-VAC-GEN)

Bounded execution worker `worker-035`, no inbox card existed for this slot. One class-bound task,
self-selected from the live controller state: the pass-05 gate audit
(`runtime/state/controller_verification/lifecycle_20260912-004308.json`) records
`G-FORM ... F2a [0 distinct accept reviewer(s)]` at the FROZEN rev28 pin, and the pass-04 card
`astra-life04-verify-gform-r2` requires two independent blind full-schema verdicts per class at
one frozen hash. This is one such verdict for F2a, from a reviewer distinct from workers
034/043/048/069/088/090/096.

**Verdict: `revise`, score 3.5 — class semantics pass at the pinned bytes; three hash-bound
blocking failures remain, all on evidence/provenance binding, not on class semantics.**

## Pinned inputs (read-only)

| path | sha256 (prefix) | bytes |
|---|---|---|
| `schemas/af_scc_c2_vacuum.yaml` (reviewed) | `5476a3f2c6bc7196` | 29976 |
| `artifacts/formulation/schemas/af_scc_c2_vacuum.yaml` (mirror) | `5476a3f2c6bc7196` | 29976 |
| `research_map/formulation_taxonomy.yaml` (declared F0) | `0abb9ed8a96135c9` | 36372 |
| `artifacts/formulation/formulation_taxonomy.yaml` (supplement) | `d7419b4e8963cb71` | 21699 |
| `artifacts/formulation/FROZEN.json` | `2f358f6722d92062` | — |
| `artifacts/formulation/evidence/taxonomy_consistency.json` | `9e335e9ba1bfcf77` | 495 |
| `schemas/af_scc_c0_vacuum.yaml` (sibling) | `55d0a1ea9bda96b8` | 34984 |
| `ledger/theorems.jsonl` | `a1674f09497975cf` | 151521 |
| `research_map/class_separation.py` (shared detector) | `c266dbceca87fb99` | — |

Snapshot manifest: `snapshot/SNAPSHOT.sha256`. Canonical F2a hash re-measured after all checks:
unchanged (`moving_target_check.drift=false`).

## Method

`check_f2a_rev12.py` is an own implementation (no other worker's checker imported) with 14 check
groups / 58 subchecks, each pre-registered, plus 10 synthetic mutants + a null control. It is
read-only with respect to canonical paths; all writes are inside this directory. The only
canonical module used is `research_map/class_separation.py` (hash-pinned in C13.3).

## Result

| group | checks | result |
|---|---|---|
| C01 identity / freeze pin / mirror | canonical == mirror == FROZEN rev28 pin, class id, revision 12 | PASS |
| C02 strict YAML hygiene + clock discipline | duplicate-key-rejecting load, stamps not future-dated | PASS |
| C03 class-token discipline | all class-shaped tokens inside the frozen four; C2 token semantics; no composite assertion | PASS |
| C04 quantifier chain | `forall r / exists G_r comeager / forall D / not_exists extension`; D0 tagged union `{smooth} ∪ {(sobolev,s>5/2,δ∈(1/2,1))}` | PASS |
| C05 conclusion typing | `scc_c2_future_inextendibility`, WCC content excluded from the conclusion, I+/visibility roles | PASS |
| C06 containment direction | `E_C2 ⊂ E_{C^1,1} ⊂ E_H2loc ⊂ E_C0`; entailments lower→C2; forbidden transfers C2→lower; agrees with the C0 schema (reverse wording, same relation) | PASS |
| C07 disjointness from C0 | distinct conclusion types; no C0 token in assertion blocks; H2LOC/TWOSIDED registered as variants | PASS |
| C08 F0 binding chain | declared F0 resolves; pointers resolve; **evidence pointer stale (C08.4)**; **evidence not hash-bound (C08.5)** | **FAIL** |
| C09 falsifier decidability | tier 1/2, machine steps, schema falsifiers, vacuity falsifier | PASS |
| C10 genericity typing | `residual_comeager`, alias-equal to the taxonomy, transfer directions typed | PASS |
| C11 cross-artifact | conclusion/regularity alias-equal taxonomy ↔ schema ↔ supplement | PASS |
| C12 L1 ledger refs | ids resolve; **4/5 claim `citation_status=verified_by_L1` unsupported by the pinned ledger (C12.3)** | **FAIL** |
| C13 machine class separation | detector 0 findings on the snapshot; 27-fixture regression 17/17 leaks, 10/10 controls, FP 0 / FN 0, exit 0; detector hash pinned | PASS |
| C14 drift | all 10 pinned inputs unchanged at finalize | PASS |

Controls: **11/11** — each of M1–M10 flips its named subcheck (or keeps a known-fail subcheck
failing); M0 null control reproduces the clean subcheck vector
(`controls.json`).

## Hard failures (all blocking, hash-bound)

1. **HF-035-F2A-1 — stale consistency-evidence pointer.** `f0_binding.consistency_evidence_sha256`
   declares `675a99d0d25b2b37…`, but the file at the declared path measures
   `9e335e9ba1bfcf77…` and is FROZEN rev28-pinned at that value; the `675a99d0` bytes exist
   nowhere under the pinned tree (C08.4, C08.6). The binding's own rule requires the consistency
   check to be re-run and the binding refreshed **before any gate verdict**. (Corroborates the
   family-wide finding recorded by workers 034/040/043/063/077/086/090/094; independently
   reproduced here for F2a.)
2. **HF-035-F2A-2 — evidence is not hash-bound.** The pinned evidence document carries only
   `consistent: true` over four class ids; it carries no `map_taxonomy_sha256`, no
   `lead_contract_sha256`, no `measured_at` (keys listed in C08.5). Re-stamping the schema pointer
   to `9e335e9b` would make the pointer resolve but would still not bind the consistency verdict
   to the declared F0 revision `0abb9ed8` / supplement `d7419b4e`.
3. **HF-035-F2A-3 — L1 provenance claims unsupported by the pinned ledger.** 4 of 5
   `l1_ledger_refs` (T-401, T-402, T-514, T-520) declare `citation_status: verified_by_L1`, but
   `ledger/theorems.jsonl` at `a1674f094979` has no `citation_status` field on any row and records
   `verification_status: abstract-read` and `review_status: not_independently_reviewed` for all
   five referenced rows, with `acceptance_authority` explicitly "author self-assessment, not a
   reviewer verdict" (C12.3).

Projected repair path (not applied here; lead owns the canonical paths): regenerate the
consistency evidence so that it embeds the compared-tree hashes and the check result, re-pin
`consistency_evidence_sha256` in the three schemas to the regenerated hash, align
`l1_ledger_refs` with the ledger vocabulary (`content_status` / `review_status`), re-freeze to
rev13, then re-run this harness at the new hash. Under that counterfactual the three blocking
subchecks clear; no class-semantics change is required by this review.

## Cross-class observation (not a finding against F2a)

The C0 sibling schema (`55d0a1ea9bda`) line 245 contains the inverted phrase "C2 is a strictly
larger extension class" inside `forbidden_transfers[0].reason`, contradicting its own line 238
chain; F2a's text is clean (C06.5). Recorded for the C0/F2b owners only.

## Reproduction

```bash
sha256sum schemas/af_scc_c2_vacuum.yaml   # 5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce
python3 artifacts/worker-035/f2a_rev12_verdict/check_f2a_rev12.py
python3 runtime/bin/classsep_regression.py
```

## Falsifier

Any blocking subcheck passing on a re-run at the pinned hashes; a file at the declared evidence
path hashing to `675a99d0…`; a ledger row for T-401/T-402/T-514/T-520 carrying
`citation_status=verified_by_L1` or `review_status=independently_reviewed`; a pinned evidence
document carrying the compared-tree hashes; any pinned input moving during the run (then this
verdict is void, not wrong); a re-freeze of F2a (this verdict binds to `5476a3f2c6bc` only).

## Non-claims

Not a gate verdict; cannot pass G-FORM or move F2a/node status. No canonical artifact was edited.
The review verifies schema form, binding and class separation — it does not prove or refute the
physics statement.
