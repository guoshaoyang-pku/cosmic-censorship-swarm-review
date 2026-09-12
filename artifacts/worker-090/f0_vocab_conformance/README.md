# W090-F0-VOCAB-CONFORMANCE-01 — F0-relative vocabulary conformance of F1/F2a/F2b

**Worker:** worker-090  **Node:** F2a (primary, class `AF-SCC-C2-VAC-GEN`)  **Gate:** G-FORM
**Verdict:** scoped `revise` (NOT a full-schema verdict)  **Pins:** F2a `5476a3f2c6bc`,
F1 `cce9c60146d6`, F2b `55d0a1ea9bda`, F0 `0abb9ed8a961`, registry `46cd9f1eb534`,
FROZEN rev28 `2f358f6722d9`. Pin stable across the whole run (`pin_stable=true`).

## What was measured

Every vocabulary-valued field of the three frozen rev12 class schemas was extracted structurally
and classified against the canonical F0 rev5 `field_vocabulary.*.allowed` lists, using the
declared `artifacts/formulation/VOCAB_ALIASES.json` registry. Classification per token:

| class | axis | declared | F0 allowed contains | class |
|---|---|---|---|---|
| F1 | genericity_kind | `residual_comeager` | `baire_residual`, `provisional_baire_residual` (…its aliases) | **inverted** |
| F2a | conclusion_type | `scc_c2_future_inextendibility` | `strong_cosmic_censorship_C2` (its alias) | **inverted** |
| F2a | genericity_kind | `residual_comeager` | `baire_residual`, `provisional_baire_residual` | **inverted** |
| F2b | conclusion_type | `scc_c0_future_inextendibility` | `strong_cosmic_censorship_C0` | **inverted** |
| F2b | genericity_kind | `residual_comeager` | `baire_residual`, `provisional_baire_residual` | **inverted** |
| F1/F2a/F2b | regularity_token, family | C2 / C0 / null, SCC/WCC | exact | exact (6) |

Counts: **exact 6, inverted 5, alias_resolvable 0, unregistered 0, null_token 1.**

## Findings

- **W090-VOCAB-01 (major, blocking until adjudicated).** Authority inversion: on all five
  non-exact slots the schema uses the *canonical* key of `VOCAB_ALIASES.json`, while the F0
  allowed list contains only that canonical's *aliases*. Exact F0 membership and registry
  canonicity therefore disagree on the same meaning. An F0-exact conformance check rejects F2a
  on 2 of its 4 vocabulary axes; an alias-aware check accepts them only if alias-equivalence is
  authoritative — the controller ruling that is still open (W090-F2A-02 / HF-W061-F2AB-01).
- **W090-VOCAB-04 (major, F2a + F2b).** F2a and F2b each depend on the alias registry for one or
  more non-exact tokens but declare **no** registry pointer. F1 does (`genericity.vocabulary_aliases_ref`,
  line 149). The dependency is implicit for F2a/F2b.
- **W090-VOCAB-06 (major).** The canonical taxonomy's *own* class descriptors carry registry-alias
  tokens: `strong_cosmic_censorship_C2/_C0` and `provisional_baire_residual` (5 instances). Under
  the registry policy — "accepted aliases … must never appear in a new canonical artifact" — the
  F0 authority itself is the largest canonicalisation target, not the schemas alone.
- **W090-VOCAB-05 (info).** F0 is internally self-consistent: 26/26 non-null `classes[*].axes`
  tokens are members of F0's own allowed lists (0 violations); the disagreement is strictly
  cross-artifact.
- **W090-VOCAB-03 (info, empty).** No token is accepted merely as a registry alias whose registry
  canonical is F0-allowed; the mismatch is entirely the inversion direction above.
- **Sanity:** 0 duplicate top-level YAML keys in all four compared files (rev12 fixed the earlier
  duplicate-key defect).

## Non-claims

Not a full-schema verdict; quantifiers, topology, physics and class semantics are out of scope.
No canonical artifact was written. This audit does **not** decide which authority wins (F0 allowed
list vs registry canonical); it measures that they disagree and names every instance.

## Falsifier

Falsified at these pins if (a) any token classified `inverted`/`unregistered` is a member of its
F0 allowed list, (b) any token classified `exact` is absent from both allowed list and registry
alias table, (c) a schema classified registry-pointer-absent contains a `VOCAB_ALIASES.json`
reference, or (d) any control fails to reproduce its pre-committed classification.

## Reproduce

```bash
cd artifacts/worker-090/f0_vocab_conformance
python3 check_vocab_conformance.py     # exit 0 iff pin_stable and all 8 controls pass
```

Controls: C0 baseline reproduction, C1 bogus token → unregistered, C2 F0-listed token → exact,
C3 add registry canonical to F0 allowed → exact, C4 registry key removal → unregistered, C5 F0
allowed removal → unregistered, C6 byte append → pin digest changes, C7 duplicate key → detected.
**8/8 pass.** Controls run on copies under `sandbox/`; canonical tree untouched.
