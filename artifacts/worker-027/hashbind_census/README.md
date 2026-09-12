# W027-F2A-HASHBIND-CENSUS-01 — hash-binding census + B7/B8 patch validation

**Worker:** worker-027 · **Class:** AF-SCC-C2-VAC-GEN (F2a) · **Node:** F2a · **Gate:** G-FORM
**Status:** bounded worker lifecycle complete — not a node transition, not a gate verdict.
**Verdict:** `CENSUS_AND_PATCH_VALIDATED` (21/21 pre-registered controls), exit 0.
**Reproduce:** `python3 artifacts/worker-027/hashbind_census/verify_hashbind_census.py`

## Question

The F2a/F1/F2b HF-B1 closure rests on `check_class_binding_drift.py` returning
"all hard checks pass". Its B7 check binds the consistency-evidence record to the
schema's declared F0 revision with a substring test
(`declared in blob or declared[:16] in blob`). W027-F2A-HB1-INDEP-01 reported two
blind spots. This task (a) censuses every hash-comparison site on the pinned
FROZEN rev29 toolchain, (b) reproduces the blind spots dynamically with sandbox
trees, and (c) validates a minimal repair patch.

## Measured result

| # | measurement | result |
|---|---|---|
| 1 | Static census of hash-comparison sites in 15 pinned files | **14 sites**: 12 `EXACT`, 2 `SUBSTRING` (both on `check_class_binding_drift.py:166`); 6 files carry sites, 9 carry none; no other truncated/substring hash bind on the path |
| 2 | Unpatched B7 vs a prefix-forged evidence record (16-hex prefix + 48 flipped nibbles) | **verdict = pass** — the forged record is accepted (blind spot reproduced) |
| 3 | Unpatched B7 vs supplement drift after evidence generation | **verdict = pass** — the supplement input is bound by no hard check (B2/B5 are info) |
| 4 | Unpatched B7 vs the HF-B1 candidate record (both full hashes embedded) | pass (positive control) |
| 5 | Unpatched B7 vs a stale declared hash | fail (existing behaviour preserved) |
| 6 | Patched B7/B8 vs the same four trees | candidate **pass**; prefix-forged **fail**; supplement-drift **fail**; stale-declared **fail** |
| 7 | Patch applies with `patch -p1`; patched bytes reproduce; patched `--selftest` | exit 0, sha match, selftest pass |

Live baseline (read-only, no writes): the unpatched checker at the live pins exits 1
because the live `taxonomy_consistency.json` (9e335e9b) embeds no revision hash —
that is the already-known HF-B1 defect, not the new finding.

## Findings

| id | severity | status | statement |
|---|---|---|---|
| W027-HBC-F1 | major | CONFIRMED | B7's substring/prefix test accepts a record that does not bind the declared revision (probe `T_prefix_forged`) |
| W027-HBC-F2 | major | CONFIRMED | no hard check binds the class-contract supplement input (probe `T_supp_drift`) |
| W027-HBC-F3 | info | CENSUS | 14 hash-comparison sites across the pinned toolchain; counts `{EXACT: 12, SUBSTRING: 2}` |
| W027-HBC-F4 | info | VALIDATED | four-hunk B7/B8 patch: exact full-string canonical binding + new hard supplement binding; applies cleanly, self-tests, discriminates all four trees |
| W027-HBC-F5 | info | OBSERVED | `artifacts/formulation/tools/check_variant_registry.py` moved FROZEN-rev29 `c471da4b7be9` → `8c7ef46f11db` at 01:21:56 with `FROZEN.json` unchanged; excluded from the pinned set, not adjudicated here |

## Proposed patch (`proposed_patch_B7B8.diff`, unapplied)

- **B7** becomes exact full-string equality with the declared canonical revision
  (removes the `declared[:16]` substring escape).
- **New hard B8** requires the evidence record to embed the *measured* supplement
  revision by full string (the HF-B1 candidate `4c4803c5` already does; the live
  record `9e335e9b` does not).
- The author's `_write_fixture` is updated so its null control embeds the
  supplement hash; without that update the strengthened contract legitimately
  fails the old fixture. This is disclosed as part of the patch, not hidden.

The patch is **not applied** — `check_class_binding_drift.py` is deepseek-flash-05's
artifact and tool ownership is an audit-lead decision. Applying it moves a pinned
tool hash and requires a FROZEN revision bump and re-review.

## Pinned inputs (hard pins; any drift voids the measurement, exit 2)

`artifacts/formulation/FROZEN.json` `815e08079aef` (rev29) · canonical F0
`0abb9ed8a961` · supplement `d7419b4e8963` · live evidence `9e335e9b` · candidate
`4c4803c5` · drift checker `bde270d3886a` · generator `3df4abfc7c49` · the three
class schemas · 13 FROZEN-rev29 tools. The full list and measured values are in
`report.json.pins`.

## Pre-registered falsifier

FALSIFIED if (a) any pinned input drifts T0→T1 (void, exit 2); (b) the census
classifies the B7 site as anything other than SUBSTRING, or finds no EXACT site in
`verify_frozen.py`; (c) the unpatched checker does NOT pass the prefix-forged or
supplement-drift tree; (d) the unpatched checker does not reject the stale-declared
tree; (e) the patched checker fails the author's selftest, fails the HF-B1
candidate tree, or does not reject the prefix-forged / supplement-drift /
stale-declared trees; (f) the diff does not apply with `patch -p1` or does not
reproduce the patched bytes; (g) any pre-registered control misses its expectation;
(h) any pin fails to resolve.

## Non-claims

- Not a gate verdict: worker events cannot set `status=done`,
  `validation_status=passed`, or any gate verdict.
- Does not publish the candidate or apply the patch; canonical writes and re-pins
  are lead decisions.
- Does not adjudicate the F2b rev30 direction dispute or any schema content.
- Does not claim the blind spot affected any past verdict — it shows the checker
  *would* accept a record that does not bind the declared revision.
- Author-level independence only: deepseek-flash-05 authored the checker;
  worker-027 did not.
- The static census is a heuristic AST classification (taint on digest
  computations, hash-key accesses, hash-named identifiers); the hard evidence for
  B7 is the dynamic probe matrix, not the census.
