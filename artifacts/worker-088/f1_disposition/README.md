# W088-F1-LIVE-DISPOSITION-01 — F1 verdict-corpus disposition at the live pin

Worker: `worker-088` (no inbox card existed; one self-selected bounded class-bound task).
Node `F1`, class `AF-WCC-VAC-GEN`, gate `G-FORM`. Read-only on canonical paths.
Window: 2026-09-12T01:18–01:23+08:00.

## Question

The published G-FORM reason counts **accepts** per class pin. F1's live FROZEN rev29 pin
`d9cebb9404b2` also carries revise verdicts with hash-anchored hard failures. Does the accept
count discharge them, or is an accept-only scan hiding live blocking findings? This is the
evidence the owner of `astra-life05-verify-gform-r3` needs when weighing revise verdicts.

## Answer (measurement, not a gate verdict)

**The accept count does not discharge the live revise corpus.** Seven findings reproduce at the
pinned bytes, including a 25/25 stale suite binding, stale stored probes, acceptance evidence that
is not input-hash-bound, and a declared stage-2 rejection of the frozen bytes. Faithful replication
of the controller's own `review_coverage` reproduces the published **4** full accepts exactly, and a
permissive live-pin scan finds **9** revise verdicts plus one full accept (`worker-089`) the scan
drops on target format alone. F1 is not clean at `d9cebb9404b2` on this measurement.

## Method and pins (all re-hashed at exit; nothing moved)

| path | sha256 (12) |
|---|---|
| `schemas/af_wcc_vacuum.yaml` | `d9cebb9404b2` |
| `schemas/f1_falsifier_tests.jsonl` | `56bcb4b3234b` |
| `artifacts/formulation/FROZEN.json` (rev29) | `815e08079aef` |
| `artifacts/formulation/evidence/acceptance_pipeline_report.json` | `9b7d6c8208d3` |
| `research_map/formulation_taxonomy.yaml` (F0 rev5) | `0abb9ed8a961` |
| `artifacts/heldout/heldout-09/bases/af_wcc_vacuum.yaml` (rev12 control) | `cce9c60146d6` |

The controller scan is not paraphrased: `VERDICT_KINDS`, `TARGET_ALIASES`, `_targets_in_review`
and `_explicit_pins` are lifted by AST from the pinned `research_map/astra_lifecycle.py` and
executed against the 43-file frozen F1 review corpus. The declared stage-2 auditor is executed on
**sandbox copies** under `sandbox/` with `PYTHONDONTWRITEBYTECODE=1`; no canonical byte is written.
All 43 review files and the four pinned tools are hashed before and after (hash guard clean).

## Findings

| id | axis | status | one-line measurement |
|---|---|---|---|
| W088-D1 | accept-only scan vs live revise corpus | REPRODUCED_AT_LIVE | 4 full accepts reproduced (matches published); 9 live-bound revise verdicts permissive / 5 visible to the real rule; counts are accept-only |
| W088-D2 | suite rows bind superseded rev12 | REPRODUCED_AT_LIVE | `f1_falsifier_tests.jsonl`: 25/25 rows `binding_sha256=cce9c601` (rev12, frozen rev27), **0/25** bind live `d9cebb`; the suite file itself is FROZEN rev29-pinned |
| W088-D3 | F1-AMB-25 probes stale | REPRODUCED_AT_LIVE | deciding probe expects F0 rev4 `276009f4` at `f0_binding.declared_f0_sha256` (live `0abb9ed8`); `binding_note` expects `astra-classscope-02` (absent from the live leaf); `cross_artifact` stores `276009f4` |
| W088-D4 | acceptance evidence unbound/stale | REPRODUCED_AT_LIVE | `acceptance_pipeline_report.json` contains **0** sha256 tokens for any measured schema, mtime 00:27:40 predates F1 rev13 00:53:40, and its stage-2 path is a worker artifact; a rev11-era PASS is indistinguishable from a PASS at `d9cebb` |
| W088-D5 | stage-2 auditor on live bytes | REPRODUCED_AT_LIVE | sandbox run of `artifacts/worker-06/spec_conformance_audit.py`: exit=1, `verdict=reject`, `failed_rules=['R03']`; same on the rev12 control |
| W088-D6 | C5-style symbol binding | INSTRUMENT_LOCAL | textual premise holds (`symbol_definitions: null`, bindings only via `i_plus.predicate_abbreviation` and prose `completeness_definition`); the criterion itself is local to worker-048's frozen helper, not a canonical gate rule |
| W088-D7 | controller scan undercounts | REPRODUCED_AT_LIVE | the real rule drops 5 live-pin verdicts: object-valued verdict (`F1-review-rev27-b`), path#hash target (`worker-089` full accept), unrecognised target (`worker-071`), dict-valued pins (`worker-004`, `worker-018`) |
| W088-D8 | F0/F1 strength contradiction invisible | REPRODUCED_AT_LIVE | pinned checker has **0** executable conditionals comparing strength directions; live F0 says "stronger" at 4 loci (incl. line 200), live VARIANT_REGISTRY says "strictly weaker"; workers 002/004/018/045 all name it |

## Live-bound revise disposition

| review | reviewer | named failures | maps to |
|---|---|---|---|
| `F1-suite-rebind-worker-029` | worker-029 | HF-W029-F1-01, F-W029-F1-02, F-W029-F1-03 | D2, D3 |
| `F1-review-worker-073-rev29` | worker-073 | F1-073-01 (blocking) | D2 |
| `F1-review-rev29-worker-071` | worker-071 | HF-071R3-01, HF-071R3-02 | D5, D2, D3, D4 |
| `F1-review-worker-048-rev13-closure` | worker-048 | W48-F1R13-HF-1 (blocking) | D6 |
| `F1-review-worker-045` | worker-045 | HF-045-1 | D8 |
| `F1-review-worker-018` | worker-018 | HF-W018-F1-1 (blocking) — **invisible to scan** | D8 |
| `F1-review-worker-002-rev13` | worker-002 | checker-coverage-gap | D8 |
| `F1-rev13-strictness-direction-worker-004` | worker-004 | W004-DIR-01-HF — **invisible to scan** | D8 |
| `F1-review-rev27-b` | worker-085 | HF-085-BIND-01 — stale pin (rev12), advisory | — |

## Controls (8/8 pass)

CTL-1 live accept counted · CTL-2 stale pin excluded · CTL-3 12-hex prefix accepted ·
CTL-4 malformed JSON skipped · CTL-5 dict pin invisible to the real rule · CTL-6 dict verdict
invisible · CTL-7 census digest deterministic · CTL-8 zero live-bound suite rows (parser
positive control). Run twice; `measurement_digest` and findings identical
(`9e6bd0b009a998f43c5d4a6b7233306f736ab215905c62ed5b8341aee76b84a0`); corpus stable during the run.

## Falsifier

Re-run `python3 dispose_f1.py` at the same pins: falsified if any REPRODUCED_AT_LIVE measurement
differs, if any control departs, or if a pinned input hash moved without the report recording it.
Each finding row carries its own narrower falsifier in `report.json`.

## Authority limits (non-claims)

Worker measurement only: no gate verdict, node status, `validation_status=passed`, or canonical
byte is set. No mathematics is judged and no reviewer is accused of error. A move of any pinned
hash voids this disposition for the moved bytes.
