# W094E-F0-SETDIR-01 — AF-WCC-VAC-GEN variant SET direction audit at FROZEN rev29

Bounded, class-bound worker task taken by `worker-094` (no inbox card for this slot).
Class **AF-WCC-VAC-GEN**, variant **SET**, node **F0**, gate context **G-FORM / L-FORM-03**.
Read-only: no canonical or shared file was written; no gate verdict, node status, or
`validation_status` is claimed.

## Why this task

The FROZEN rev29 re-base at **2026-09-12T00:57:26+08:00** moved three decision-relevant files
(`VARIANT_REGISTRY.json`, the SET delta, `FROZEN.json`). The last variant-strength recheck
(`worker-061`, 00:56:01) binds the *previous* registry hash and is therefore void for the live
bytes. The rev29 addendum says the residual L-FORM-03 is "confined to the two F0 artifacts
(canonical :200, supplement :176)" and that `check_variant_registry` is VALID. No worker had
measured (a) whether the re-based registry/delta labels are consistent with their own
justification clauses, (b) the F0 sites at the level they grammatically denote, or (c) whether
the owner's checker's VALID verdict is substantive.

## The two levels (pre-registered)

| level | statement | derived order |
|---|---|---|
| predicate | `P(q)` = some tail of `gamma` lies in `J^-(q)` for one `q`; `S` = `gamma` lies in `∪_q J^-(q)` (variant SET predicate) | `P ⇒ S`, not conversely ⇒ **S is strictly WEAKER than P** |
| statement/class | parent asserts `¬P`; variant SET asserts `¬S` | `¬S ⇒ ¬P`, not conversely ⇒ **the SET variant is strictly STRONGER than its parent class** |

A direction phrase is adjudicated **at the level of its grammatical subject**. Derivation is
machine-checked here, not cited: all preorders on 2 and 3 points with all causal sequences
(6,354 predicate cases, `P⇒S` 0 violations; finite-model `S∧¬P` 0 violations), the whole-curve
single-q form ≡ tail form (T1 replication, 0 violations), and an unbounded omega-chain witness
(`x_i ≤ q_j ⇔ i ≤ j`) where `S` holds and no `q_j` sees a tail. Scope: model-theoretic in the
declared causal-preorder semantics; physical realizability of the omega-chain is carried by the
class's own T4 note, not re-proved.

## Live claims at the pinned bytes

| # | site | level | asserted | expected | verdict |
|---|---|---|---|---|---|
| 1 | F0 canonical `variants[SET].definition` (:94) | class | stronger | stronger | consistent |
| 2 | F0 canonical `class_identity_variants` (:199) | predicate | stronger | weaker | **inverted (F0V-SETDIR-01)** |
| 3 | F0 supplement `contract_divergences D1.f0_reading` (:176) | predicate | stronger | weaker | **inverted (F0V-SETDIR-02)** |
| 4 | F1 rev13 `class_identity_variants[SET].relation` (:235) | predicate | weaker | weaker | consistent |
| 5 | `VARIANT_REGISTRY variants[SET].strength` label | class | weaker | stronger | **inverted (F0V-SETDIR-03)** |
| 6 | SET-delta `strength` label (:11) | class | weaker | stronger | **inverted (F0V-SETDIR-04)** |
| 7 | SET-delta `changes[visibility.definition].to` (:22) | predicate | weaker | weaker | consistent |
| 8 | SET-delta `changes[visibility.negation_conclusion].to` (:27) | statement | stronger | stronger | consistent |

Findings 1/2 and 3: the F0-frozen file uses the same phrase "strictly stronger" for the SET
variant in two blocks at **opposite levels** — correct at class level (:94), inverted at
predicate level (:199); the supplement repeats the predicate-level inversion (:176). This
*splits* the rev29 residual: the F0 sites are as reported, but they are predicate-level wording
inversions, not a wrong class order.

Findings 3/4 are **new at the 00:57:26 bytes**: the re-base changed the registry and delta
labels from the class-level-correct "strictly STRONGER than AF-WCC-VAC-GEN" to "strictly weaker
than AF-WCC-VAC-GEN" while keeping the statement-level justification (`¬S ⇒ ¬P, but not
conversely`) that entails the opposite label. The repair corrected the predicate-level clause
(:22) but moved the class-level label in the wrong direction, so residual L-FORM-03 is **not**
confined to the two F0 artifacts.

Leakage consequence (why wording is load-bearing): a set-visible singularity refutes only the
SET variant, not AF-WCC-VAC-GEN; a single-q-visible one refutes both. A class-level "SET is
weaker" label licenses binding a set-based refutation to the frozen class — exactly the
direction the variant registry calls class leakage.

## Checker false-VALID (F0V-SETDIR-CHECKER)

`artifacts/formulation/tools/check_variant_registry.py#c471da4b7be9` requires
`"STRONGER" in SET.strength` ("variant SET must be marked stronger than its parent"). On the
live registry the requirement is satisfied **only** by the bracket note `[rev13 direction
corrected from 'strictly STRONGER']`, while the operative label is "strictly weaker". Proof by
sandbox execution (control C6, copies of the checker + inputs under `sandbox/`):

| run | exit | verdict |
|---|---|---|
| live registry | 0 | VALID |
| bracket correction notes stripped | 1 | INVALID — "variant SET must be marked stronger than its parent" |
| class-level label restored | 0 | VALID |

So the owner's VALID verdict on SET strength is a mention-match, not an assertion check.

## Controls (7/7 behaved as pre-registered)

| id | control | observed |
|---|---|---|
| C1 | all preorders n=2,3: `P⇒S` | 0 violations / 6,354 cases |
| C2 | finite I+/gamma: `S⇒∃` single-q tail | 0 violations |
| C3 | omega-chain: `S` true, no `q_j` sees a tail | holds, N=8/24/64 |
| C4 | drop transitivity: `P` true while `S` false (harness is live) | holds, witness `a≤q` missing |
| C5 | whole-curve single-q ≡ tail (T1 replication) | 0 violations |
| C6 | owner checker note-sensitivity (false-VALID mechanism) | 0 / 1 / 0 |
| C7 | revision-note stripper keeps `gamma([0,T))`, drops the corrected-from mention | holds |

Instrument verdict: **MEASURED_INSTRUMENT_VALID**, zero input drift pre/post.

## Pins

F0 canonical `research_map/formulation_taxonomy.yaml#0abb9ed8a961`;
supplement `artifacts/formulation/formulation_taxonomy.yaml#d7419b4e8963`;
F1 `schemas/af_wcc_vacuum.yaml#d9cebb9404b2`;
registry `artifacts/formulation/VARIANT_REGISTRY.json#6bac9adea19e`;
SET delta `...AF-WCC-VAC-GEN.variant-SET.delta.json#64b8d6394a04`;
checker `.../check_variant_registry.py#c471da4b7be9`;
FROZEN `artifacts/formulation/FROZEN.json#815e08079aef` (rev29). Advisory only (actively
revised peer artifact, not load-bearing): `artifacts/worker-076/gform_strictness_reconcile/
probe_result.json#3707d6e1e96c`.

## Falsifier

FALSE if any pinned input hash differs at re-measure; if the F0 canonical sentence's grammatical
subject is class-level rather than predicate-level; if a claim read as class-level is in fact
governed by a declared predicate-level convention in the artifact; or if control C6 does not
reproduce (live checker exit ≠ 0).

## Reproduce

```bash
python3 artifacts/worker-094/f0_setdir_audit/audit_f0_setdir.py   # exit 0, 5 findings, 7/7 controls
```

## Files

- `audit_f0_setdir.py#9854875a6e79` — deterministic, stdlib-only, read-only auditor.
- `run/report.json#849febe9a59c` — claim table, findings, checker sandbox, controls, pins.
- `run/manifest.json#16ec2c674666` — deliverable hashes.
- `sandbox/` — copies used for the owner-checker control (no canonical path).

## Authority / non-claims

Worker evidence only. This is a wording/level audit of declaration fields; it asserts no
theorem about cosmic censorship, sets no node status, and does not re-open G-F0 or promote
G-FORM. Findings 3/4 concern bytes published at 00:57:26; the next authorized revision of the
registry/delta is the natural repair point, and any byte change voids this snapshot.
