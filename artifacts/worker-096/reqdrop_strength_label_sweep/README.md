# W096-F2A-REQDROP-STRENGTH-LABEL-SWEEP-01

Worker: `worker-096` · one bounded class-bound task, self-selected (no card in
`comms/inbox/worker-096.jsonl`). Gate context: **G-FORM** · nodes **F1, F2a, F2b** ·
classes **AF-SCC-C2-VAC-GEN**, **AF-SCC-C0-VAC-GEN**, **AF-WCC-VAC-GEN**.

## Question

The F2b repair round fixed a defect family that is *not* a containment-chain error but a
**requirement-drop strength label**: F2b:246 said "C2 is a strictly larger extension
class, so C2-inextendibility is strictly weaker" while the file's own chain makes E_C2 the
smallest set. worker-096's earlier containment-premise sweep covered the
`E_X contains/smaller/larger` family and found no sibling. This sweep covers the disjoint
family: **premises whose strength label depends on adding or dropping a requirement on the
extension** (an equation, a regularity, a causality condition).

> Do the three live schemas label *requirement drops* consistently with their own stated
> rule — larger forbidden extension set ⇒ stronger inexistence statement?

## Method (independent, machine-checked, read-only)

`sweep.py` composes each YAML with line marks, extracts **every** scalar containing a
direction/strength token (128 entries across the three files, full census in
`report.json`), and applies six deterministic checks. No review text, no earlier worker
report and no diff is an input; the checks are functions of the pinned bytes.

Convention anchors are read from the pinned bytes themselves:
`F2b:95-97` ("NO equation is required of g' … this is the strongest form of the
statement"), `F2b:239`, `F2a:237` ("the lower the required regularity, the larger the set
of admissible extensions, hence the stronger the inexistence statement"),
`F1:235` (union/SET reading is "strictly WEAKER … entails the union reading").

| check | kind | expected on | result |
|---|---|---|---|
| A1 containment denial | control | live F2b:152 | fires (known hard defect reproduced) |
| A2 inverted size premise | control | live F2b:246 | fires (known hard defect reproduced) |
| A3 class-relative entailment inversion | control | `candidate_84b5d3fa` only | fires; live F2b, corrected & nesting candidates, F2a do not |
| B1 Ric-drop strength label | finding | F2a:265 | fires |
| B2 weaker-visibility weakening conflict | finding | F1:260 | fires |
| B3 cross-file Ric-construction label conflict | finding | F2a vs F2b | fires |

Controls: 4/4 matched, 0 pin drift (all 11 input hashes resolve), 0 duplicate mapping keys
in the five schemas checked. `check_class_schema.py` (`000e09e4`) returns rc=0 on live
F1/F2a/F2b, on both corrected candidates **and** on the known-defective `84b5d3fa` — the
canonical structural gate is blind to all of these prose defects, as worker-029/066/096
measured separately.

## Findings

**W096-REQDROP-B1 (major, F2a:265).** `falsifier.schema_falsifiers[3]` reads
"the extension is not required to solve Ric = 0: weaker statement bound to the wrong
class". Dropping Ric(g')=0 from the extension predicate (`F2a:85` requires it) *enlarges*
the forbidden extension set, so by the file's own rule at `F2a:237` the statement is
**stronger**, not weaker. The C0 sibling labels the identical construction "the strongest
form of the statement". The string is not discussed anywhere in `events.jsonl` or in any
review report; heldout-10 uses this slot only as fixture text for a META-erasure mutant,
so the label itself has never been adjudicated. F2a is an accepted artifact on the G-FORM
critical path, and a landing of `candidate_corrected` repairs only F2b's two carriers —
the family would remain asymmetric.

**W096-REQDROP-B2 (minor, F1:260).** `conclusion.forbidden_weakenings[3]` lists "using a
weaker visibility notion" as a weakening, while `F1:235` defines the weaker visibility
predicate as the one admitting *more* geodesics. Under that convention a weaker visibility
predicate strengthens the class conclusion. Kept at minor because "weaker visibility
notion" can also be read as "a notion classifying fewer geodesics as visible"; that reading
is consistent but uses "weaker" in the opposite sense from `F1:235`.

**W096-REQDROP-B3 (major, cross-file).** B1's sentence names exactly the C0 class
construction, and the pinned C0 file calls that construction the strongest form. The two
pinned artifacts assign opposite strength labels to the same requirement drop.

None of these is claimed as a hard gate-blocker: all three are prose labels, the canonical
gate is measured blind, and the author has not been asked. B1/B3 are class-bound and
gate-relevant because they sit in F2a/F1, both accepted on G-FORM.

## Falsifiers

- Harness: any pin mismatch; a control not firing; the F2a sibling's true entailment
  sentence firing A3; duplicate keys; anchors missing.
- B1/B3: an authority clause defining statement strength inversely to forbidden-set size,
  or an author edit of `F2a:265`.
- B2: a definition elsewhere in F1/F0 of "weaker visibility notion" as the notion
  classifying fewer geodesics as visible, or an author edit disambiguating `F1:260`.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-096/reqdrop_strength_label_sweep/sweep.py   # exit 0, writes report.json + runlog.txt
```

## Non-claims

No gate verdict, no node status, no `validation_status=passed`, no canonical file written.
Findings are worker measurements against the schemas' own stated convention.
