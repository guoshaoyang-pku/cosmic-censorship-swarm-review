# W028-F1F2A-INTERNAL-CONSISTENCY-01 — blast-radius bound on the F2b D1/D2 defect classes

Worker: `worker-028` (bounded execution worker; slot 028; no assignment card existed in
`comms/inbox/worker-028.jsonl`, self-selected from the live G-FORM blocker as
worker-014/027/064/096 did). Gate context: **G-FORM**, nodes **F1/F2a**, classes
**AF-WCC-VAC-GEN** and **AF-SCC-C2-VAC-GEN**. Read-only: no canonical file was written.

## Question

F2b at rev29 `b2ab6acb2bbe` carries two confirmed internal cross-field defects:

- **D1** — a bare containment denial at `regularity.must_not_conflate[0]` (line 152) while the
  same frozen file asserts the containment chain (line 239); and
- **D2** — an inverted size premise at `implication_ledger.forbidden_transfers[0].reason`
  (line 246: "C2 is a strictly larger extension class" against its own chain `E_C0 ⊃ E_H2loc ⊃
  E_{C^1,1} ⊃ E_C2`).

One known defect does not bound its blast radius. This run asks the sibling question at the
same frozen revision: **do F1 and F2a carry a D1–D5 cross-field contradiction at their exact
rev29 pins, under an independently written checker?**

## Method

`check_f1f2a_internal.py` (written for this task, no shared code with worker-072's F2b
instrument) loads the pinned YAML and adjudicates every normative cross-field statement against
the extension-set order the documents themselves declare
(`E_C2 ⊂ E_{C^1,1} ⊂ E_H2loc ⊂ E_C0`; larger extension set = stronger inexistence statement):

| id | check |
|---|---|
| W1–W6 | F1 WCC identity, I+/visibility conclusion roles, SCC content only in forbidden-strengthening/anti-scope positions, composite `C0 or C2` only in mention containers, no SCC conclusion token from an assertion path |
| S1–S9 | F2 SCC identity, visibility/I+ kept out of the conclusion, declared order field present, every `E_X subset-of/contains E_Y` pair matches the order, ledger entailment/forbidden directions licensed, no inverted larger/smaller or stronger/weaker premise, no bare containment denial, strength labels consistent, cross-family no-transfer row |
| X1–X3 | cross-document: distinct conclusion types, mutual anti-scope, no family leakage |

Mentions are handled explicitly: a containment denial that is quoted or adjacent to a
correction marker is recorded as a **mention**, not a finding (the F2a line 152 carry-over is
exactly this case; the F2b line 152 case is a bare assertion).

## Result

| run | role | checks | findings |
|---|---|---|---|
| F1 `d9cebb9404b2` | target | 6/6 pass | **0** (2 composite phrases, both in mention containers) |
| F2a `e9a27996dfd3` | target | 11/11 pass | **0** (1 quoted+corrected denial recorded as mention; 1 unranked `E_{C^0,1}` pair recorded, not adjudicated) |
| F2b `b2ab6acb2bbe` | real positive control | — | **D1 at :152 + D2 at :246 reproduced** |

The F2b run is the sensitivity witness: the same instrument that reports F1/F2a clean reports
the two known F2b defects at their exact carriers, so the F1/F2a negatives are not vacuous.

**Control battery: 12/12 declared outcomes.**

- 9 planted sensitivity mutants each fail exactly their declared check id (M1 W1, M2 W3,
  M3 W2, M4 W5, M5 S4b, M6 S7, M7 S5, M8 S6, M9 S4a, M10 S2);
- 2 null mutants (F1, F2a) add no finding;
- chain-field removal fires S4a.

Determinism: a second full run is byte-identical after stripping run timestamps
(`report.json` vs `report.run2.json`).

Canonical gate `check_class_schema.py --json` returns rc=0 on both F1 and F2a at the pinned
bytes — expected, and consistent with worker-072/worker-096: the structural gate is blind to
D1/D2 content defects.

## Scope and authority

This is a **scope-limited accept on defect classes D1–D5 only**
(`counts_as_full_schema_verdict: false`). It is not a full-schema verdict, not a gate verdict,
not a node status, not a review-coverage accept. Explicitly out of scope and untouched:

- the filed blocking F2a item **HF-028R-01** (extension category unpinned;
  `artifacts/worker-028/f2a_rev29_verdict/review_f2a_rev29_028.json`);
- the F2b repair adjudication and any rev14 landing;
- gate/node transitions, which remain with the audit lead and controller.

## Falsifier

Re-run `check_f1f2a_internal.py` at the same pins. Falsified if any pin moved; if F1 or F2a
yields a D1–D5 finding; if the F2b real control stops reporting the bare denial and the
inverted size premise; if any planted control does not fail its declared check id (or a null
control adds a finding); if canonical hashes or mtimes change across the run.

## Files

- `prereg.json` — checks, controls and verdict rule registered before the run
- `check_f1f2a_internal.py` — independent read-only instrument
- `report.json` / `report.run2.json` — run records (determinism check)
- `controls/` — 12 mutant YAMLs derived from the pinned bytes
- `snapshots/` — pinned F1/F2a/F2b bytes used
- `pins/SHA256SUMS` — canonical and snapshot hashes
- `checkpoint_028.json` — worker-local checkpoint
- `MANIFEST.json` — artifact hashes
