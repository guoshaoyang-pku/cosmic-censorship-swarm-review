# W028-GFORM-DATACLASS-01 — T1 data-class guard audit at FROZEN rev29

- actor: worker-028 · created: 2026-09-12T01:06:26+08:00 · gate: G-FORM · nodes: F1,F2a,F2b
- classes: AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN
- artifact: `dataclass_audit_028.json` sha256 `b60ba13628885e0e4718f52b68bdf8cf7751fc371dbeb8eadb179d5b7b01f64f`
- checks: PASS (10/10) · controls: PASS (8/8)

## Pins

- F1: `d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d` (FROZEN rev29 `d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d`)
- F2a: `e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe` (FROZEN rev29 `e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe`)
- F2b: `b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c` (FROZEN rev29 `b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c`)
- FROZEN: rev 29 `815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0`
- F0: `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3` · EVID: `9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b`
- live map read: `5ab4bed181071461f107404fab6e22892fc162e5424907786633be9bd624634d`

## Claim under test

> no single frozen data class (s,delta,norm) is shared by F1/F2a/F2b, which disables the licensed C0=>C2 transfer

## Result

FALSIFIED at the FROZEN rev29 pins as stated. The factual premise 'no single frozen data class is shared' is false on the operative core, and the stated consequence 'disables the licensed C0=>C2 transfer' does not follow. Residual strict byte differences are annotation-level, as worker-060 already adjudicated at rev11 (verdict revise 3.5); they persist unchanged at rev13.

- T1 guard 1 (data_class): PASS on all 15 operative keys (strict), with 9 annotation-only paths recorded
- T1 guard 2 (genericity): PASS (kind and topology byte-equal on the licensed pair F2b->F2a)
- T1 guard 3: out of scope (source claim, not schema bytes)

## Checks

- PASS **K0-pins** all three schema pins: disk == FROZEN rev29 == controller-measured
- PASS **K1-parse** all three schemas parse as YAML mappings
- PASS **K2-domain-identity** D0 byte-identical three-way; D1/D2 byte-identical on the licensed pair; single r binder; refs resolve
- PASS **K3-t1-guard1-strict-core** T1 guard 1 strict: no DATA_SPACE_CORE key differs between F2a and F2b
- PASS **K4-t1-guard1-normalized-core** T1 guard 1 normalized: three-way DATA_SPACE_CORE equality under the two declared rules
- PASS **K5-dataclass-diff-enumeration** no operative data-space diff outside the two declared normalizable forms; all other diffs are annotation paths
- PASS **K6-t1-guard2-genericity** T1 guard 2: genericity_kind and genericity_topology byte-match on the licensed pair
- PASS **K7-transfer-composition** C0=>C2 entailment present in both siblings, converse not asserted, statement prefixes identical
- PASS **K8-rev11-to-rev13-stability** rev11 baseline verified by hash; no DATA_SPACE_CORE value moved rev11->rev13; D0 not identical at rev11 but byte-identical at rev13 (convergent repair)
- PASS **K9-manifest-mirrors** canonical == mirror bytes == FROZEN pins; F0 and consistency evidence pinned

## Controls

- PASS **C1** in-memory s-mutant must be caught by the core diff — expected 'regularity_class.sobolev_variant.s in diffs', observed ['regularity_class.sobolev_variant.s']
- PASS **C2** in-memory delta-mutant must be caught by the core diff — expected 'regularity_class.sobolev_variant.delta in diffs', observed ['regularity_class.sobolev_variant.delta']
- PASS **C3** dropped constraint row must be caught by the core diff — expected 'constraints.momentum in diffs', observed ['constraints.momentum']
- PASS **C4** null control: F2a vs itself must yield zero core diffs — expected [], observed []
- PASS **C5** planted extra key must land in annotation, never in DATA_SPACE_CORE — expected ['_audit_plant'], observed ['_audit_plant']
- PASS **C6** a wrong pin must fail the pin check — expected 'match=false', observed False
- PASS **C7** D0 mutant must break D0 identity — expected 'not identical', observed False
- PASS **C8** genericity-topology mutant must fail T1 guard 2 — expected 'match=false', observed False

## Falsifier

At the six pinned hashes (F1 d9cebb9404b2, F2a e9a27996dfd3, F2b b2ab6acb2bbe, FROZEN rev29 815e08079aef, F0 0abb9ed8a961, EVID 9e335e9ba1bf): falsified if (a) any of the 15 DATA_SPACE_CORE keys differs strictly between F2a and F2b, or (b) D0/D1/D2 definitions or the binder skeleton/statement prefix differ between the licensed pair, or (c) genericity.kind or genericity.topology_or_measure differ between F2a and F2b, or (d) any implication ledger forbids C0=>C2 or omits the entailment, or (e) any FROZEN rev29 pin stops matching disk, or (f) any control C1-C8 fails to reproduce its expected outcome. Any re-issue of a canonical path at new bytes voids this audit at that path and requires a fresh measurement.

## Limitations

- Scope is the data_class subtree, the quantifier domains D0-D2, the genericity guard axes, and the sibling implication ledgers; visibility, topology and conclusion prose are out of scope.
- T1 guard clause 3 (source claim must carry artifact_refs and a reviewer verdict) is a property of a claim, not of these schema bytes, and is not measured here.
- The tagged-union D0 question (one class vs a family of two statements) is a portfolio adjudication reserved to lead-audit; this audit measures cross-schema identity, which holds byte-for-byte either way.
- AF-WCC-SCALAR-SPH (N0) is out of scope; no transfer rule connects it to the vacuum classes.
- Checks and controls ran on pinned in-memory copies; the canonical paths were opened read-only.

## Non-claims

- no gate verdict, node status or validation_status=passed is set here
- no canonical artifact was modified; all checks ran read-only on pinned copies
- the lead-audit / controller own promotion and any T1 guard amendment
