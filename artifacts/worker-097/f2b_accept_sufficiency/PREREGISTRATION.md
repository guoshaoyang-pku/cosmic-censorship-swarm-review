# W097-F2B-ACCEPT-SUFFICIENCY-01 — pre-registration

- **worker**: worker-097 (instance 20260912T010800)
- **node**: F2b · **class**: AF-SCC-C0-VAC-GEN · **gate**: G-FORM
- **question**: at the frozen F2b revision `schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe`
  (FROZEN rev29 `815e08079aefbc`), do the accept verdicts recorded at that same hash
  constitute *sufficient review evidence* to discharge the two live self-contradictions
  that revise verdicts at the same hash flag?
- **not the question**: whether F2b should be accepted or revised. This audit renders **no
  class verdict** and claims no gate or node state.

## Disclosure

Task selection followed reading the live review record at `b2ab6acb2bbe` (3 accepts vs ≥2
revises citing two carriers). The audit is therefore **not blind to the conflict**. The
mechanical checks and controls below were fixed before the instrument was run, and every
classification is computed from primary bytes by the pinned instrument, not by hand.

## Carrier definitions (fixed before the run)

| id | primary field | line | contested content |
|---|---|---|---|
| HF-152 | `regularity.must_not_conflate[0]` | 152 | the live denial "No containment with C2 or C0 is asserted here" |
| HF-246 | `implication_ledger.forbidden_transfers[0].reason` | 246 | "C2 is a strictly larger extension class" |

Reference wording (independent of the contested file): F2a `schemas/af_scc_c2_vacuum.yaml`
line 237 and the F0 companion supplement `artifacts/formulation/formulation_taxonomy.yaml`
line 145 both declare the nested extension sets `E_C2 ⊂ E_{C^1,1} ⊂ E_H2loc ⊂ E_C0`.

## Pre-registered checks

1. **Pins.** Every input hash is measured before and after; the run is void if any moved.
2. **HF-246 derivation.** Parse the artifact's own `extension_class_containment` chain (line
   239); take the innermost set. The line-246 reason is `CONSISTENT` iff its comparatives
   agree with the chain (E_C2 innermost ⇒ C2 extension class strictly *smaller*), else
   `INCONSISTENT`.
3. **HF-152 derivation.** `CONSISTENT` iff the line-152 denial sentence is absent or is
   consistent with the containment asserted at lines 239/242; else `INCONSISTENT`.
4. **Accept coverage.** For each accept verdict at the hash, scan (a) every string in the
   verdict JSON and (b) every line of each instrument/evidence file it cites, and classify
   per carrier: `DISPOSED` (explicit line citation, verbatim contested content, or
   field+judgment in one statement) · `EXCLUDED-FROM-CHECK` (carrier explicitly excluded
   from the check's scope) · `MENTION-ONLY` · `NONE`.
   A verdict counts as covering a carrier only at `DISPOSED`.
5. **Revise-side context.** Same classifier applied to the revise verdicts at the hash, to
   show the classifier can recognise a real disposition.

## Pre-registered controls

| id | control | expected |
|---|---|---|
| C1 | synthetic verdict disposing of both carriers | both `DISPOSED` |
| C2 | worker-097 revise `REVIEW.json` (known disposition) | both `DISPOSED` |
| C3 | synthetic verdict with no carrier tokens | both `NONE` |
| C4 | sandbox mutation `strictly larger` → `strictly smaller` | HF-246 flips to `CONSISTENT` |
| C5 | sandbox deletion of the line-152 denial sentence | HF-152 flips to `CONSISTENT` |
| C6 | hash stability of all inputs before/after | no drift |

If any control fails, the run is reported as failed and no sufficiency conclusion is drawn.

## Decision rule

- If the two clauses are `INCONSISTENT` from primary bytes **and** no accept at the hash
  `DISPOSED` of a carrier, the accept set is reported `insufficient` for that carrier as a
  matter of record, and the report says what a sufficient disposition would have to
  contain. Otherwise the report says which accept discharges which carrier.
