# W001-F2B-REV13-CONTAINMENT-CLOSURE-01

One bounded class-bound task, worker-001 (slot recycled; no inbox card exists). Node F2b /
class `AF-SCC-C0-VAC-GEN` / gate `G-FORM`. **Worker measurement only** - no node status, no
`validation_status=passed`, no gate verdict, no canonical write.

## Question

At the live rev13 bytes (F2b `b2ab6acb2bbe`, F2a `e9a27996fd d3`), is the open
containment-direction finding (`L-FORM-01` / `W097-F2B-HF3` / worker-008 `CD-01`) real, is the
forbidden-transfer row itself correct, and what is the minimal lexical repair?

## Verdict

| id | result |
|---|---|
| `CD01_CONFIRMED` | line 246: `C2 is a strictly larger extension class` contradicts the document's own `E_C0 contains E_H2loc contains E_C^{1,1} contains E_C2` (line 239) and `E_C2 subset of E_H2loc` (line 242). The row's transfer direction is **correct**; only the size gloss is inverted. |
| `CD02_PRESENT` | line 152: literal denial `No containment with C2 or C0 is asserted here` coexists with the declared chain; the F2a sibling marks exactly this denial as wrong. Scoped reading available -> major ambiguity, clarification recommended. |
| `REPAIR_CANDIDATE_VERIFIED` | non-canonical candidate = base + 2 pre-registered lexical edits; 0 inversions, canonical `check_class_schema.py` pass, diff confined to lines 152/246, controls 8/8. |

Report sha256 `d6d57e9bbda7`, candidate sha256 `90ede5c9516b`, pins in `PINNED.json`.
Adoption impact: 2 FROZEN rev29 entries reference the F2b path; adoption needs an
authorized revision + downstream re-base and voids rev13-bound F2b verdicts as advisory only.

## Files

- `adjudicate_containment_repair.py` - fail-closed harness (exit 3 pin drift / 4 control failure / 5 precondition)
- `REPAIR_CANDIDATE.yaml` - NON-CANONICAL candidate (base + edit A + edit B)
- `REPAIR_CANDIDATE.diff` - exact two-line diff
- `report.json` - full decision record, checks C1-C7, controls K1-K8, falsifiers
- `PINNED.json` - measured pins and guard policy
- `CHECKPOINT.json` - worker checkpoint (byte-identical runtime copy)

## Falsifiers

See `report.json#falsifier`. In short: any pin move exits 3; F-01 needs a documented alternative
reading of "extension class" consistent with lines 239/242 (none is declared); F-02 needs
evidence the literal denial is contract-required; the candidate fails on a canonical-checker
failure, an out-of-region diff, or any control not detected.
