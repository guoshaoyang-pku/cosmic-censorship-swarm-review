# W002-F2B-REV14-LANDING-PREDICATE-01

Pre-registered, deterministic, read-only predicate for the F2b portion of the authorized
REC-36 repair (node `F2b`, gate `G-FORM`, classes `AF-SCC-C0-VAC-GEN` and
`AF-SCC-C2-VAC-GEN`).

**Actor:** worker-002 (`deepseek-flash-02`) · **instrument:** `verify_rev14_landing.py` ·
**pre-registration:** `PREREGISTRATION.json` · **live report:** `report.json` ·
**controls:** `controls.json` (9/9) · **core digest:** `369acd0cfdd51c63…` (stable across
consecutive runs)

## Why this exists

REC-36 authorizes ONE rev14 / FROZEN rev30 revision folding the F2b `must_not_conflate`
containment denial (D1) and the "C2 is a strictly larger extension class" inversion (D2),
and requires `astra-life05-verify-gform-r3` to re-run at the new pins. This instrument
freezes the F2b acceptance predicate **before** any byte moves, so the landing can be
checked mechanically and fail-closed instead of by reading the revision note.

## Bindings (measured at entry and exit; 0 drift)

| artifact | sha256 | role |
|---|---|---|
| `schemas/af_scc_c0_vacuum.yaml` | `b2ab6acb2bbe…` (rev13) | subject F2b |
| `artifacts/formulation/schemas/af_scc_c0_vacuum.yaml` | `b2ab6acb2bbe…` | mirror (byte-identical) |
| `schemas/af_scc_c2_vacuum.yaml` | `e9a27996dfd3…` (rev13) | sibling F2a |
| `artifacts/formulation/FROZEN.json` | `815e08079aef…` (rev29) | freeze manifest |
| `research_map/formulation_taxonomy.yaml` | `0abb9ed8a961…` (rev5) | frozen taxonomy |
| `artifacts/formulation/rule_spec.json` | `40f9bb9e657b…` | R06/R16 |
| `artifacts/formulation/tools/check_class_schema.py` | `000e09e46b2f…` | canonical structural gate |
| `…/candidate/af_scc_c0_vacuum.repair2edit.yaml` | `84b5d3fa29a6…` | authorized 2-edit candidate |

## Live measurement (pre-landing, `FAIL_REC36_OPEN` — the pre-registered expected state)

- **D1 FAIL** — `regularity.must_not_conflate[0]` contains the live sentence
  *"No containment with C2 or C0 is asserted here"* while the same document asserts the
  nesting chain. The scanner distinguishes a live denial from a bracket-marked historical
  mention (control C04).
- **D1b PASS** — `implication_ledger.extension_class_containment` asserts all three
  adjacent pairs `E_C2 ⊂ E_{C^1,1} ⊂ E_H2loc ⊂ E_C0` in the correct direction.
- **D2 FAIL** — the C2→"this class" forbidden-transfer reason reads *"C2 is a strictly
  larger extension class"*, inverting the document's own poset; the conclusion polarity
  (*strictly weaker*) is present, so the fix is the premise.
- **M1 mirror identity PASS; M4 delta-confinement PASS (no change yet); M2/M3/M5 PENDING**
  (revision 13 < 14, FROZEN rev29 < 30, no rollback copy declared).
- **M7 (info)** — the canonical structural gate exits 0 on the live defective bytes: it
  cannot detect or certify this repair (control C08 shows it exits 1 only on a structural
  violation, an empty `must_not_conflate`).
- **M3 informational** — 1 of 50 FROZEN rev29 pins did not resolve at run time:
  `artifacts/formulation/tools/check_variant_registry.py` declared `c471da4b7be9`, measured
  `8c7ef46f11db`. Concurrent traffic continues; this is a measurement, not a defect ruling,
  and M3 is `pending` pre-landing regardless.

## Post-landing decision rule

`PASS_CANDIDATE_REV14` requires: revision ≥ 14 **and** D1/D1b/D2 clean **and** mirror
byte-identity **and** FROZEN revision ≥ 30 with 0 unresolved pins **and** F2b leaf delta
vs the pinned rev13 snapshot confined to `{revision*, written_at, created_at,
regularity.must_not_conflate[0], implication_ledger.forbidden_transfers[0].reason,
f0_binding.*}` **and** a declared rollback copy. Any canonical byte move with revision < 14
is `FAIL_UNSANCTIONED_BYTE_MOVE`. A `PASS_CANDIDATE_REV14` is an input to r3, never a gate
verdict.

## Controls (9/9 as pre-registered)

C01 live defect · C02 candidate clean + gate exit 0 · C03 denial paraphrase detected ·
C04 historical bracket mention not miscounted · C05 inversion paraphrase detected ·
C06 correct paraphrase accepted · C07 reversed chain detected · C08 empty
`must_not_conflate` rejected by the canonical gate · C09 unrelated carrier leaves the
verdict unchanged.

## Falsifier

Re-run `verify_rev14_landing.py --live --controls` on the same pins: any pin move, any
departure from `PREREGISTRATION.json` P1–P7, any control departing from its stated
expectation, or a differing `core_digest` across two consecutive runs falsifies this
measurement. After the authorized landing, only a reproduced `PASS_CANDIDATE_REV14` at the
new pins supports the F2b portion of REC-36.

## Honesty notes

1. `core_digest` excludes the M6 census of review files binding the rev13 hash, because
   that census tracks concurrent traffic and is not stationary; M6 remains in `report.json`
   as `info`.
2. The C06 control was constructed once on the repaired carrier, which made D1 pass; it was
   moved to the live carrier so that it matches the pre-registered expectation
   (`D1 fail, D2 pass`) and isolates the D2 paraphrase. No predicate logic changed.
3. Prior sight: the same two carriers were adjudicated independently in
   `artifacts/worker-002/f2b_containment_adjudication/`; this instrument is a landing-time
   re-implementation, not a blind replication.
4. No canonical file was written; no gate verdict, `validation_status=passed` or node
   `status=done` is claimed.
