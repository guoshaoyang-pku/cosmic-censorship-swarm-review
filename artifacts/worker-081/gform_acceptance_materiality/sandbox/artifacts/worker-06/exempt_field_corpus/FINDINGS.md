# FORM-EXEMPT-09 — prose leaks in the exempt explanatory fields (worker-06)

Node: `A1` (gate `G-CLASSBIND`) · classes: `AF-SCC-C0-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-WCC-VAC-GEN`
Successor to `FORM-HELDOUT-07`; takes the lead's stated next step
(`comms/inbox/worker-06.jsonl:7`: "the highest-value next corpus would be prose leaks in the
exempt explanatory fields, which neither stage scans by design").
No node completion, no theorem, no physics result is claimed.

## Question

On the frozen canonical schemas (FROZEN rev18, `verify_frozen.py` 33 files / 0 problems), how much
class-contract leakage can be hidden in fields that are key-exempt (`EXEMPT_KEY`, e.g.
`visibility.reason`, `genericity.class_change_warning`, `provenance.no_status_claim`) or outside every
scanned path, and do the two acceptance stages catch it?

## Method (pre-registered)

- 18 mutants, each = one frozen canonical base (rev18 sha prefixes `bdb23f76b895` C0,
  `e9fcefe6e595` C2, `f962c117ba11` WCC) with exactly one string replaced in an exempt/unscanned field.
- 14 leak families, each tied to a frozen invariant (R04, R05, R09, R12, R13, R15, R18, R20, R21,
  R26, R27, R28, R29, R31) with the rule that catches the same text in a scanned field.
- 7 controls: 3 canonical round-trips (format control), 2 conforming in-class edits in the same
  fields, 2 explicitly negated composite/foreign phrases. Plus the 3 canonical schemas as-is.
- `manifest.json` (sha256 `0627216b6b276f80…`) was written and hashed **before** any gate ran; fixture
  hashes are verified before measurement; no fix was attempted after seeing results.

Stages (hashes recorded in `report.json`):

1. structural: `artifacts/formulation/tools/check_class_schema.py` sha256 `000e09e46b2fb4ab…`
2. semantic: `artifacts/worker-06/spec_conformance_audit.py` sha256 `c79d8ab8440ac673…`
   (baseline W06 auditor, kept as a second opinion; layout caveat recorded).

## Result — corpus VALID, union escape 18/18

All 10 controls accepted by both stages ⇒ the measurement is not format-dominated.

| stage | caught | escape rate |
|---|---:|---:|
| structural | 0/18 | **1.0000** |
| semantic | 0/18 | **1.0000** |
| union | 0/18 | **1.0000** |

Escaped families (all 18 are escapes): X1 WCC content in SCC prose (2), X2 merged C0/C2 regularity (2),
X3 sibling-regularity substitution (2), X13 genericity-kind substitution (2), and one each of
X4 C0 curvature hypothesis, X5 theorem promotion, X6 quantifier-order substitution,
X7 I+ completeness in SCC, X8 matter in VAC, X9 multi-end slice, X10 foreign content in `extensions`,
X11 transfer truth-table inversion, X12 SCC content in WCC, X14 source-conclusion overclaim.
Per-family examples and one-sentence reasons: `report.json` → `aggregates.escape_families`.

For comparison, the same pipeline on the general held-out corpus (`FORM-HELDOUT-07`) escaped at
0.3462 union, falling to 0.0385 after R26–R31 hardening. This corpus raises the escape rate back to
1.0 by moving every leak into the fields the hardening deliberately excluded.

## Leak-criterion control (post-hoc, hash-bound)

`relocation_controls.py` re-locates each injected sentence into a *scanned* field:
11/14 cases are caught there with exactly the expected rule (R04, R09, R12 ×3, R13, R20, R21, R23/R29,
R31 ×2) ⇒ those escapes are genuine field-exemption escapes, not over-claimed leaks.
3/14 are not caught even in a scanned field ⇒ all-field gate gaps:

- **X8 matter in VAC** — spec R12 mentions a "foreign matter/asymptotic token", but no such token is
  implemented in `FOREIGN`; "a small amount of scalar-field matter is permitted" passes anywhere.
- **X11 transfer truth-table inversion** — R28 only inspects `genericity.transfer_failures` /
  `transfer_holds` rows; the same claim in prose passes anywhere.
- **X14 source-conclusion overclaim** — R15's regex is narrower than the spec ("settles the censorship
  question" is not matched); the sentence passes even inside `provenance.sources`.

Derived, hash-bound classification (`classification.json`): 14 field-exemption escapes,
3 all-field gate gaps, 1 prose-only gap (X6: the invariant is enforced only on the structured
quantifier block, so no prose relocation can be caught).

## Interpretation

The acceptance surface is structural, not semantic: a class leak survives if it is written in
explanatory prose. This is not a regression of R26–R31 — those rules closed the specific fields the
previous corpus exposed — it is the documented residue, now measured at 18/18 with controls.

## Falsifiers

- Any mutant shown not to violate a frozen class invariant (leak criterion invalid for that family).
- Any control rejected by either stage (corpus format-dominated ⇒ measurement invalid).
- Re-running under different canonical/gate hashes without re-pinning (hashes in `report.json`).
- A repaired gate that rejects all 18 mutants while still accepting all 10 controls would falsify the
  blind-spot claim in the direction of improvement; that repair must then be re-measured on a **fresh**
  corpus, never this one.

## Limits

Corpus authored by one agent; 18 mutants; the relocation control is post-hoc (declared as such);
the semantic stage targets the earlier worker-draft layout; no repair implemented; no claim beyond the
two stage hashes and the frozen base hashes recorded here.

## Artifacts (sha256)

| artifact | sha256 |
|---|---|
| `manifest.json` | `0627216b6b276f80132c75ebe5257f074175f56a311c83db3df838fd6bb055fb` |
| `report.json` | `8af6bb5a3ba15864c54db67a3c4ed3b604b477165edf582f452c0e755e988452` |
| `relocation_manifest.json` | `4461a18a03a1bf4b3a5cc75d39269cb0c54ac3caa94981a24bb7390d0e5558fe` |
| `relocation_report.json` | `60a57bdbd447b6c36509187de0506617ef74578256997a02eb265b61d8f86079` |
| `classification.json` | `c5236a877374cc2433619bf7af1d2c754d58c6dcbbe06b67a1373966e0fa7d1e` |
| `make_corpus.py` | `58cb69fe2a93a85f29a573d2a59eb33f152dae807e0c03bb1b061d275e7f6cb8` |
| `run_corpus.py` | `aebb4b8aab0ea1c9c6c8946bbbd70945d8c0ce72c759f883e91e25ee72940617` |
| `relocation_controls.py` | `d5b917f71ba054ab369364116324fbcab45f34fa1ee563b5fc2b2b634d11fe28` |
| stage 1 `check_class_schema.py` | `000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff` |
| stage 2 `spec_conformance_audit.py` | `c79d8ab8440ac6738bb61df5a33e9fd5f8319b4e74e1f2e9c0fc5083fb408cec` |

Fixture-level hashes are in `manifest.json` (each entry carries `sha256`), bound to the manifest hash
above; the runner verifies them before measuring.
