# W023-F2B-DIR-GUARD-01 — proposed R31 containment/entailment-direction predicate

Worker: `worker-023` · node `F2b` · classes `AF-SCC-C0-VAC-GEN` (+ sibling `AF-SCC-C2-VAC-GEN`)
· gate `G-FORM` · worker-level, non-canonical, read-only on every canonical path.

## One-line result

The canonical gate's R06 certifies that `regularity.must_not_conflate` is present and non-empty
but not that its sentences agree with the same file's `implication_ledger`; a class-relative
direction predicate (`containment_direction_lint.py`, new rule **R31** as a *proposed* hook)
flags both circulating inverted repair candidates (`84b5d3fa29a6`, `48cadb72e507`), clears both
staged corrected candidates (`9ab32ee39d00`, `51c253c46306`) and the live rev13 bytes
(`b2ab6acb2bbe`, `e9a27996dfd3`), and is calibrated on five mutants. The canonical gate passes
**all twelve** fixtures, including the inverted ones — that gap is the deliverable's point.

## Why this exists

- `W023-F2B-DIR-REVIEW-01` (worker-023, 01:08) found that the standing H1/H2 containment repair
  asserts `H2_loc-inextendibility ENTAILS this class's conclusion` inside the **C0** file, the
  reverse of the file's own `one_way_entailments`, `forbidden_weakenings`, `subsumption_note`
  and `extension_class_containment`; hard failure `W023-F2B-DIR1`.
- `W080-F2B-REPAIR-H2E-01` (worker-080, 01:07) independently found the same inversion and
  staged two corrected candidates.
- Both packets recorded the same instrument gap: R06/R16 certify that a forbidden transfer is
  *marked* forbidden, not the entailment direction of the replacement sentence. This artifact is
  that missing predicate, delivered as a runnable lint + a minimal hook diff.

## Live pins at task entry and exit (unchanged, measured 2026-09-12T01:0x–01:1x +08:00)

| path | sha256 |
|---|---|
| `schemas/af_scc_c0_vacuum.yaml` (= `artifacts/formulation/schemas/...`) | `b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c` |
| `schemas/af_scc_c2_vacuum.yaml` | `e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe` |
| `schemas/af_wcc_vacuum.yaml` | `d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d` |
| `artifacts/formulation/FROZEN.json` (rev29) | `815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0` |
| `artifacts/formulation/tools/check_class_schema.py` (rev29 pin) | `000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff` |

No canonical path was written by this task. The patched checker exists only under
`sandbox/formulation/tools/`; `proposed_gate_hook_R31.diff` applies cleanly to the live checker
(`patch -p1 --dry-run` rc 0) but is **not** applied. Adopting it changes the frozen instrument
hash and voids the FROZEN rev29 pin until lead-formulation + controller re-freeze. That call is
not this worker's.

## What the predicate checks (document-internal, no physics)

- edges: `implication_ledger.one_way_entailments` rows with relation `entails`, transitively
  closed; an edge `X -> Y` means `E_Y ⊆ E_X`;
- nesting: `extension_class_containment` parsed into `(smaller, larger)` token pairs
  (`E_C0 contains E_H2loc ...`, `E_C2 subset of ...`), transitively closed;
- forms recognised: `<X>-inextendibility ENTAILS this class's conclusion` (requires `X -> own`),
  `this class's conclusion ... ENTAILS <X>-inextendibility` (requires `own -> X`),
  `<X>-inextendibility entails <Y>'s conclusion` (requires `X -> Y`), and containment-context
  arrow chains (`the implication runs C0 => C2`; regularity chains such as `C2 => C^{1,1} =>
  Riemann in L^inf` are excluded by a context gate);
- verdicts: `consistent` (edge or nesting supports it), `inverted` (reverse declared — hard),
  `unsupported` (neither direction declared — warning, not a block), `neutral` (explicit
  negation/mention guard), unparsed slot text is surfaced as `unclassified`, never certified.

## Calibration (pre-registered; `evidence/results.json`, 21/21 checks)

| fixture | sha256 | lint | patched gate |
|---|---|---|---|
| live C0 rev13 | `b2ab6acb2bbe` | 0 inverted | pass |
| live C2 rev13 | `e9a27996dfd3` | 0 inverted | pass |
| live WCC (not applicable) | `d9cebb9404b2` | n/a | pass |
| repair 066 / composed 044 | `84b5d3fa29a6` / `48cadb72e507` | **1 inverted each** | **fail R31** |
| corrected 023 (prior packet) | `9ab32ee39d00` | 0 inverted | pass |
| corrected 080 (staged) | `51c253c46306` | 0 inverted | pass |
| m07 nonsense / m08 negated | derived | 0 inverted (neutral/unclassified) | pass |
| m09 reversed / m10 arrow-inverted | derived | **1 inverted each** | **fail R31** |
| m11 unknown label | derived | 0 inverted, 1 unsupported | pass |
| canonical checker (blindness control) | rev29 pin | — | **rc 0 on all 12** |

`evidence/gate_hook.json`: 28/28 checks. Both suites exit non-zero on any pre-registered
expectation flipping.

## Reproduce

```bash
cd artifacts/worker-023/f2b_dir_guard
python3 make_fixtures.py             # re-pins fixtures, fails on hash drift
python3 run_suite.py                 # 21/21 direction-lint controls -> evidence/results.json
python3 gen_gate_patch.py            # rebuilds sandbox + diff, patch --dry-run must be rc 0
python3 run_gate_hook.py             # 28/28 canonical-vs-patched controls -> evidence/gate_hook.json
```

CLI for a single candidate (usable by reviewers today, no adoption needed):

```bash
python3 check_containment_direction.py --json <schema.yaml> [--expect-sha256 HEX]
# exit 0 no inversion / 1 inversion found / 2 unreadable or pin mismatch
```

## Deliverables (`SHA256SUMS` carries the full list)

| file | sha256 prefix |
|---|---|
| `containment_direction_lint.py` | `4bd4338be985` |
| `check_containment_direction.py` | `5067c9fb1689` |
| `proposed_gate_hook_R31.diff` | `cf57cc40910b` |
| `sandbox/formulation/tools/check_class_schema.py` (patched copy) | `da788a800083` |
| `fixtures/MANIFEST.json` (7 fixtures + 5 mutants) | `eb46753af122` |
| `evidence/results.json` | `ece38c5c3dde` |
| `evidence/gate_hook.json` | `1795341b60ed` |
| `make_fixtures.py` / `run_suite.py` / `gen_gate_patch.py` / `run_gate_hook.py` | see `SHA256SUMS` |

## Limits, non-claims, falsifier

- English lexical recognition only; a semantically inverted sentence in an unrecognised form
  lands in `unclassified`, not in a verdict. The lint cannot decide the mathematics, citation
  scope, or whether an unclassified sentence is a conflation.
- Not a gate verdict, not a node completion, not a canonical instrument change, not a claim
  that F2b's other defect families are closed, not a claim about C0/C2 physics beyond the
  documents' own declared entailment direction.
- Falsified if: any fixture hash moves; the lint flags live/corrected fixtures at the pins; it
  fails to flag `84b5d3fa`/`48cadb72`; the patched sandbox gate stops failing those two; or the
  diff stops applying to the FROZEN rev29 checker bytes. Re-run the four commands above.
