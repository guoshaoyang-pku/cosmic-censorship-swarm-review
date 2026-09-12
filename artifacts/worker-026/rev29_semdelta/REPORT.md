# W026-GFORM-REV29-SEMDELTA-01 — rev12 -> rev13 semantic-delta guard

**Worker:** worker-026 (bounded execution worker, no inbox card; task self-selected from the
immediate queue) · **Classes:** `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`
· **Nodes:** F1, F2a, F2b · **Gate:** G-FORM
**Verdict:** `ZERO_UNDECLARED_SEMANTIC_DELTA` at FROZEN rev29 · **Controls:** 12/12
**Authority:** worker-level measurement only — not a node done, not a gate verdict, not a
`validation_status` promotion; no canonical artifact was written.

## Why this task

`astra-life05-evidence-binding-repair` (Astra, 00:48:41) authorises exactly four bounded
byte-moving repairs to the three class schemas + `schemas/taxonomy_cases.jsonl`, and its own
falsifier is: *"Any change to a class definition, hypothesis, conclusion predicate or axis
semantics"*. Nothing measured that falsifier at the new bytes. This instrument does:

1. pins the **rev12** bytes (F1 `cce9c60146d6`, F2a `5476a3f2c6bc`, F2b `55d0a1ea9bda`,
   FROZEN rev28 `2f358f6722d9`) — the rev12 schema copies are re-verified byte-exact from
   `artifacts/worker-026/gform_rev12_reverify/pinned/`;
2. projects every leaf of the three schemas, `taxonomy_cases.jsonl` and
   `f1_falsifier_tests.jsonl` into a flat path->value map (4 166 leaves);
3. diffs the live rev13 bytes against that map and classifies each changed leaf as
   `ITEM_1`/`ITEM_2`/`ITEM_3` (the declared repairs), `METADATA` (revision bookkeeping),
   or **`UNDECLARED`** (the repair's falsifier);
4. adds three auxiliary checks at the same pins: mirror alignment, FROZEN
   declared-vs-measured, and stale `binding_sha256` values in the falsifier rows;
5. carries 12 mutation/strictness controls, including duplicate-key rejection in both the
   YAML and JSONL loaders.

## Measured result (rev12 -> rev13)

Pins at check: F1 `d9cebb9404b2`, F2a `e9a27996dfd3`, F2b `b2ab6acb2bbe`, F0
`0abb9ed8a961`, FROZEN rev29 `3d9e3d77fd87`; entry == exit, zero drift.

| bucket | count | what moved |
|---|---:|---|
| ITEM_1 | 0 | `taxonomy_cases.jsonl` was already bound to F0 rev5 `0abb9ed8a961` at rev12; unchanged |
| ITEM_2 | 9 | `f0_binding.consistency_evidence_sha256` `675a99d0` -> `9e335e9b` + `checked_at` + `binding_note`, all three schemas |
| ITEM_3 | 3 | F1 `class_identity_variants[0].relation` direction corrected; `visibility.definition` and `quantifiers.domains.D5.definition` explanatory sentences corrected |
| METADATA | 18 | `revision` 12 -> 13, `revised_at`, `revision_history[10]` in all three schemas |
| **UNDECLARED** | **0** | — |

**Predicate clauses preserved.** For the two ITEM_3 paths that carry the class predicate
(`visibility.definition`, `quantifiers.domains.D5.definition`) the first-sentence extractor
returns byte-identical old/new strings: only the explanatory strictness sentence changed.
The one direction correction is `relation`: "strictly STRONGER ... non-containment in the
union implies no single q sees a tail" -> "strictly WEAKER ... the single-q tail predicate
entails the union reading, and non-containment in the union implies no single q sees a tail".
That is the assertion direction the repair was authorised to fix; the mathematical
adjudication is worker-076 `W076-GFORM-STRICTNESS-RECONCILE-06` / worker-040
`W040-F1-STRICTNESS-ADJ-04`, not this instrument.

**Auxiliary checks.**
- Mirror alignment: all three `artifacts/formulation/schemas/*` mirrors byte-equal to the
  canonical rev13 paths.
- FROZEN rev29 (`3d9e3d77fd87`) declares matching measured hashes for all five probed paths.
- **Open finding — stale falsifier bindings.** `schemas/f1_falsifier_tests.jsonl`
  (`56bcb4b3b323`, frozen in rev29) carries **25/25 rows with
  `binding_sha256 = cce9c60146d6`** (the rev12 F1 pin) and **0/25** binding the frozen rev13
  F1 pin `d9cebb9404b2`. The r3 acceptance card requires each row's `binding_sha256 == the
  pin`; this instrument reports the exact counts and does not edit the file.

## Controls (12/12, `report_selftest.json`)

C1 projection determinism · C2 live-vs-baseline zero undeclared · C3 key reorder is not a
semantic delta · C4 `conclusion_type` mutation -> UNDECLARED · C5 `scope_statement` mutation
-> UNDECLARED · C6 declared item-2 refresh -> ITEM_2 only · C7 declared item-3 strictness
edit -> ITEM_3 only · C8 declared item-1 rebind -> ITEM_1 only · C9 `taxonomy_cases`
statement mutation -> UNDECLARED · C10 `class_components.regularity_token` mutation ->
UNDECLARED · C11 duplicate YAML key rejected · C12 duplicate JSONL key rejected.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-026/rev29_semdelta/semantic_delta_guard.py --selftest \
    --out artifacts/worker-026/rev29_semdelta/report_selftest.json
python3 artifacts/worker-026/rev29_semdelta/semantic_delta_guard.py \
    --baseline artifacts/worker-026/rev29_semdelta/baseline_rev12.json \
    --declared artifacts/worker-026/rev29_semdelta/rev29_pins.json \
    --out artifacts/worker-026/rev29_semdelta/report_rev12_to_rev13.json
# exit 0 = zero undeclared, 1 = undeclared found, 2 = pin moved / parse failure
```

## Falsifier

This report is falsified if any of: (a) a leaf outside the declared ITEM_1/2/3 and METADATA
path sets moved between the pinned rev12 copies and the rev13 bytes (re-run returns
`UNDECLARED_SEMANTIC_DELTA_FOUND`); (b) the `visibility.definition` or
`quantifiers.domains.D5.definition` predicate clause differs between the two revisions (the
`item3_predicate_sentences_preserved` flag turns false); (c) any rev12 pinned copy in
`artifacts/worker-026/gform_rev12_reverify/pinned/` fails its sha256; (d) any of the 12
controls stops discriminating; or (e) the stale-binding count on
`schemas/f1_falsifier_tests.jsonl` changes without a new artifact event.

## Non-claims

Not a gate verdict; does not edit, re-freeze or promote any canonical artifact; does not
adjudicate whether the corrected strictness direction is mathematically right (worker-076 /
worker-040 own that); does not decide whether the stale falsifier bindings are a defect or a
documented exemption (the audit lead owns that disposition); `ITEM_1 = 0` is a measurement
that the taxonomy_cases binding was already current, not a repair claim.
