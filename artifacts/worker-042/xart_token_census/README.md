# W042-XART-TOKEN-CENSUS-07 — cross-artifact conclusion-token binding census

**Worker:** worker-042 (instance launched 2026-09-12T01:02:35+08:00)
**Node/class scope:** F0 vocabulary surface, all four frozen classes
(`AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH`)
**Gate relevance:** G-FORM (rev13 review round) / G-F0 declared vocabulary — measurement input only.
**Authority:** worker artifact. No node status, no gate verdict, no `validation_status=passed`.

## Headline

At frozen revision **FROZEN rev29 `815e08079aef`** and the rev13 schema hashes, the
cross-artifact conclusion-token binding is **internally consistent per class** (E1–E4, E6),
but the **F0 declared allowed-list carries alias forms where every other canonical artifact
carries the canonical forms** (E5 FAIL), and the same F0 field is consumed by two
reviewer-side rules that return **opposite** results on the same frozen bytes (F-2).

Exactly one check fails; it is the one this task was written to test.

## Pinned inputs (all measured stable before and after the run)

| path | sha256 (prefix) |
|---|---|
| `research_map/formulation_taxonomy.yaml` | `0abb9ed8a961` |
| `artifacts/formulation/formulation_taxonomy.yaml` | `d7419b4e8963` |
| `artifacts/formulation/FROZEN.json` | `815e08079aef` (rev29) |
| `artifacts/formulation/VOCAB_ALIASES.json` | `46cd9f1eb534` |
| `artifacts/formulation/VARIANT_REGISTRY.json` | `6bac9adea19e` |
| `artifacts/formulation/evidence/taxonomy_consistency.json` | `9e335e9ba1bf` |
| `schemas/af_wcc_vacuum.yaml` | `d9cebb9404b2` (rev13) |
| `schemas/af_scc_c2_vacuum.yaml` | `e9a27996dfd3` (rev13) |
| `schemas/af_scc_c0_vacuum.yaml` | `b2ab6acb2bbe` (rev13) |

Snapshot manifest `7b0c1fc5b412`; report `26e47b70477a`; tool `935779656a1d`.

## Census table

| class | surface | token | class under policy |
|---|---|---|---|
| WCC-VAC | F0 `axes.conclusion_type` | `weak_cosmic_censorship` | CANONICAL |
| WCC-VAC | F0 `conclusion.type` | `weak_cosmic_censorship` | CANONICAL |
| WCC-VAC | supplement `class_contracts[...]` | `weak_cosmic_censorship` | CANONICAL |
| WCC-VAC | `schemas/af_wcc_vacuum.yaml` | `weak_cosmic_censorship` | CANONICAL |
| SCC-C2 | F0 `axes.conclusion_type` | `strong_cosmic_censorship_C2` | **ALIAS** |
| SCC-C2 | F0 `conclusion.type` | `strong_cosmic_censorship_C2` | **ALIAS** |
| SCC-C2 | supplement `class_contracts[...]` | `scc_c2_future_inextendibility` | CANONICAL |
| SCC-C2 | `schemas/af_scc_c2_vacuum.yaml` | `scc_c2_future_inextendibility` | CANONICAL |
| SCC-C0 | F0 `axes.conclusion_type` | `strong_cosmic_censorship_C0` | **ALIAS** |
| SCC-C0 | F0 `conclusion.type` | `strong_cosmic_censorship_C0` | **ALIAS** |
| SCC-C0 | supplement `class_contracts[...]` | `scc_c0_future_inextendibility` | CANONICAL |
| SCC-C0 | `schemas/af_scc_c0_vacuum.yaml` | `scc_c0_future_inextendibility` | CANONICAL |
| WCC-SCALAR | F0 `axes.conclusion_type` | `weak_cosmic_censorship` | CANONICAL |
| WCC-SCALAR | F0 `conclusion.type` | `weak_cosmic_censorship` | CANONICAL |
| WCC-SCALAR | supplement `class_contracts[...]` | `weak_cosmic_censorship` | CANONICAL |

Declared allowed-list `field_vocabulary.conclusion_type.allowed` =
`[weak_cosmic_censorship, strong_cosmic_censorship_C2, strong_cosmic_censorship_C0]` — items
1 and 2 are aliases of `scc_c2_future_inextendibility` / `scc_c0_future_inextendibility`.

Per-class policy evaluation is consistent: every surface of a class maps to exactly one
canonical group; C0 and C2 are distinct; no rejected/ambiguous token (`scc`,
`strong_cosmic_censorship`) appears. The two WCC classes intentionally share
`weak_cosmic_censorship`; they are separated by matter model and symmetry, not by conclusion
type. (A first draft of E4 wrongly treated that as a merge; corrected before the reported run
and recorded here.)

## Findings

### F-1 (hard) — F0 allowed-list is non-canonical

`research_map/formulation_taxonomy.yaml#field_vocabulary.conclusion_type.allowed[1..2]` carry
the alias forms. `VOCAB_ALIASES.json` states: *"canonical token first; accepted aliases are
equivalent for consistency checks only and must never appear in a new canonical artifact"*,
and F0 is a frozen canonical artifact (`status: draft_unverified`). Every other canonical
surface — including F0's own per-class `axes.conclusion_type` — uses the canonical tokens.

**Falsifier:** re-run at these pins; falsified if every allowed-list token is its own canonical
group token, or if `VOCAB_ALIASES.json` no longer declares the `scc_*_future_inextendibility`
tokens canonical.

### F-2 (hard, severity evidence) — the same F0 field is read by two opposite rules

| node | schema token | literal membership in F0 `allowed` | alias-registry rule | rules agree |
|---|---|---|---|---|
| F1 | `weak_cosmic_censorship` | true | true | yes |
| F2a | `scc_c2_future_inextendibility` | **false** | true | **no** |
| F2b | `scc_c0_future_inextendibility` | **false** | true | **no** |

On the same frozen bytes, `artifacts/worker-019/f2a_review/check_f2a_independent.py` check
`B1` (declared `"hard": true`) evaluates `ct in f0_allowed` and **fails**, while
`artifacts/worker-097/f2b_rev13_review/check_f2b_rev13.py::alias_allowed` walks the alias
registry and **passes** (`via=alias-registry`). Both were re-executed here mechanically from
the frozen bytes, not inferred from prose. Worker-019's recorded `results.json` shows
`{"id": "B1", "hard": true, "pass": false}`.

**Falsifier:** falsified if no audited schema token has
`literal_membership_in_F0_allowed != alias_registry_rule_accepts` at these pins, or if the two
consumer rules are shown to be the same rule.

## Relation to existing work (non-duplication)

- worker-100 `rev13_binding_integrity` check `C8` graded the F0-axis token gap **R-2 minor**,
  and worker-075 (`F2b-review-rev29-075.json`) raised the same axis as a **revise 3.5**
  blocking item requiring gate-owner adjudication. This census is the exhaustive four-class
  surface-by-surface accounting that neither performed (`C8` covers F0 axes only), and it adds
  the measured two-rule divergence (F-2) that explains why the grade diverged.
- worker-099 `form_direction_census` covers direction/logic inversion, a different axis.
- No open assignment card claims this axis (`comms/inbox/worker-042.jsonl` does not exist;
  the live cards target detector adjudication, G-FORM r3 verification, L0 final verification,
  G-NUM adjudication, A0 scope verification and N0 verify).

## Direction (adjudication input, not a decision)

The single re-stamp direction that makes every canonical surface, the policy, and both
consumer rules agree is: canonicalise F0 surfaces `field_vocabulary.conclusion_type.allowed`
and `classes[*].conclusion.type` to `scc_c2_future_inextendibility` /
`scc_c0_future_inextendibility` (WCC rows already canonical). That is a **new F0 revision**:
the current G-F0 pass is bound to `0abb9ed8a961` and any write to
`research_map/formulation_taxonomy.yaml` voids it, so the re-stamp must be adjudicated and
re-reviewed by the gate owner. The opposite direction (stamp the schemas back to the alias
forms) would violate policy rule 1. Worker-042 does not adjudicate.

## Instrument and controls

`run_xart_token_census.py` reads only the snapshot, re-hashes the live files, and is
deterministic: two runs produced identical `deterministic_payload_sha256`
`80211a8652e03da04b631727e78bf078cdecae082d56f50930a7ee782002fa81` (only `generated_at`
differs). Five self-contained controls, all behaving as pre-registered:

| control | expected check | detected |
|---|---|---|
| M1 schema set to alias token | E3_SCHEMA_CANONICAL | yes |
| M2 schema set to bogus token | E1_TOKENS_PRESENT | yes |
| M3 schema set to rejected merge token | E1_TOKENS_PRESENT | yes |
| M4 C2 schema cross-wired to C0 token | E2_WITHIN_CLASS_AGREE | yes |
| M5 baseline unchanged | E2_WITHIN_CLASS_AGREE | no (must not fire) |

Checks: E1 present (PASS), E2 within-class agreement (PASS), E3 schema canonical (PASS),
E4 no merge (PASS), E5 vocabulary canonical (**FAIL**), E6 class identity (PASS),
E7 FROZEN pins (PASS). Exit 1.

## Reproduce

```bash
cd artifacts/worker-042/xart_token_census
python3 pin_inputs.py                      # freeze-first; writes snapshot/manifest.json
python3 run_xart_token_census.py           # writes report.json; exit 1 on E5
```

## Scope limits

This is a token-binding census, not a semantic review: it does not judge whether the
conclusions are true, whether the class contracts are mathematically adequate, or whether
alias-equivalence should be acceptable at the gate. It measures what tokens are on which
frozen surface and what the frozen policy says about them. E7 covers only the nine audited
inputs; the full 50-file FROZEN manifest is checked by worker-100's C1.
