# W018-REQDROP-STRENGTH-ADJ-01 — requirement-drop strength-label adjudication

Bounded class-bound task taken by `worker-018` at 2026-09-12T01:25+08:00. No inbox card
existed for this slot; the task was self-selected from the live G-FORM critical path.

## Question

At the FROZEN rev29 pins, does the requirement-drop construction ("the extension is not
required to solve Ric = 0") carry a correct strength label in the canonical schemas?
worker-096 (`artifacts/worker-096/reqdrop_strength_label_sweep/report.json#1ac3d17138be`)
raised B1 (F2a:265 "weaker statement"), B2 (F1:260 "weaker visibility notion") and
B3 (cross-file opposition F2a vs F2b/C0), all `candidate_defect_unadjudicated_by_author`.

## Answer (worker-level; not a gate verdict)

- **B1 CONFIRMED.** `schemas/af_scc_c2_vacuum.yaml:265` says the Ric-drop is a "weaker
  statement". The same file's rule at line 237 says the opposite: lower required
  regularity → larger admissible extension set → **stronger** inexistence statement.
  The C0 sibling agrees at lines 80, 95–98, 101 and the F2a anti-scope block itself at
  line 269 calls C0 a "different (stronger) extension class". The class-binding half of
  the entry is right; the strength word is inverted. One-word repair, no formal field.
- **B3 CONFIRMED** as the same defect seen cross-file. The defect carrier is F2a only;
  C0/F2b's "strongest form of the statement" is the consistent labelling.
- **B2 N-LEVEL (ambiguous / likely inverted).** `af_wcc_vacuum.yaml:260` lists "using a
  weaker visibility notion" as a weakening, while line 235 defines the union/SET
  predicate as strictly weaker (it admits more geodesics) and a weaker predicate makes
  the "no visible singularity" conclusion stronger. Kept non-blocking because the same
  list already contains a non-weakening at line 259.
- **N1 (new, non-blocking).** The same Ric-drop also sits under `forbidden_weakenings`
  at F2a:231; under line 237 it is a class substitution to a stronger sibling, not a
  weakening. Placement/annotation issue; the list is known-mixed (line 232).

Timing matters: REC-36 authorizes exactly ONE rev14/FROZEN rev30 fold, and a byte move
voids every current verdict. If the fold lands without the F2a:265 word fix, the r3
binding table has to carry an unclosed F2a content defect or spend the authorized
revision. Folding the one-word fix is the cheap path.

## Method and controls

`adjudicate.py` (stdlib only, read-only) hash-pins F2a `e9a27996dfd3`, C0
`b2ab6acb2bbe`, F1 `d9cebb9404b2` and FROZEN rev29 `815e08079aef`, refuses to run on
pin drift, extracts ten exact line anchors, applies rules R1–R6 and runs six in-memory
mutation controls:

| control | expectation | result |
|---|---|---|
| K1 fix the word at F2a:265 | B1 disappears | pass |
| K2 remove the C0 "strongest" anchor | B3 disappears, B1 stays | pass |
| K3 invert F2a:237's convention | R1 fails | pass |
| K4 re-extract same bytes | identical | pass |
| K5 append a decoy "weaker statement" | no new B1 hit | pass |
| K6 wrong pin | rejected | pass |

Pre-registered live expectation: R1 PASS, R2 FAIL, R3 N, R4 FAIL, R5 N, R6 PASS.
Observed exactly that; `core_digest 71a2d3a9ccc0…`, exit 0, byte-identical on re-run.

## Deliverables

- `adjudicate.py` — deterministic fail-closed checker.
- `report.json` — full pin table, anchors, rules, findings, controls, `core_digest`.
- `checkpoint.json` — pins entry/exit, deliverable hashes, scope.
- `SHA256SUMS.txt` — task-relative manifest.
- Review record: `reviews/REQDROP-strength-adjudication-018.json` (verdict `revise`,
  score 3.5, 0 hard failures, B1/B3 blocking-for-fold, N1/N2 backlog).

## Non-claims

Not a schema verdict beyond the named carriers, not a gate verdict, not a node
transition, no canonical write. Worker events cannot set `status=done`,
`validation_status=passed` or a gate verdict. The repair decision belongs to
`astra-lead-formulation` and the G-FORM gate owner.

## Reproduce

```bash
cd <repo>
python3 artifacts/worker-018/strength_label_adjudication/adjudicate.py   # exit 0
```

Any byte move to the pinned files voids this verdict; re-run at the new pins.
