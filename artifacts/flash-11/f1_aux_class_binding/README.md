# FORM-DIFF-02 — second gate + differential agreement matrix (flash-11)

**Status: unverified draft. No node completion, no theorem, no physics result is claimed.**
Task: `assign-FORM-DIFF-02-20260911T2331` (lead-formulation, node **F1**, gate **G-CLASSBIND**,
class_ids AF-WCC-VAC-GEN / AF-SCC-C2-VAC-GEN / AF-SCC-C0-VAC-GEN).
Base artifact: `check_schema.py` (this directory), extended here with an independent
canonical-layout mode implementing `artifacts/formulation/rule_spec.json` R01–R16.

Deliverables (this directory):

| file | sha256 |
|---|---|
| `check_schema.py` | `a89b221c1c68e34f…` (rev4-strengthened; full hash in outbox event) |
| `differential_matrix.json` | `12cec7fe95815044…` (57-fixture **rev5** run) |
| `README.md` | (this file; hash reported in the outbox event) |

Supporting: `build_corpus.py`, `differential_matrix.py`, `run_tests.py`, `adversarial.py`,
`probe_map_gates.py`, `corpus/` (snapshot), `fixtures/`, `evidence/`.

## How to reproduce

```bash
cd artifacts/flash-11/f1_aux_class_binding
python3 run_tests.py            # own-layout self-test: 17 pass / 0 fail / 4 documented escapes / null control 0/100
python3 build_corpus.py         # rebuild corpus snapshot (writes corpus/manifest.json + corpus sha256)
python3 differential_matrix.py  # run all 4 gates on all 52 fixtures -> differential_matrix.json
python3 check_schema.py --layout canonical <schema.yaml> --json      # independent R01-R16 on canonical layout
python3 check_schema.py <fixture.yaml> --json                       # own layout (auto-detected)
```

No implementation imports another; every matrix cell is a subprocess run (D1).

## Corpus snapshot (D2)

`corpus/` is a copy, not a mutation, of the shared corpora:
`w06/` 16 (worker-06), `f13/` 8 (flash-13), `canonical/` 3 (lead-formulation schemas),
`flash11/` 25 (this worker's controls). **Corpus sha256: `58c83083f41b6ae3a4645f2ccc081c173087e85b04eff26b0c9b5330e165d1d5`**
(see `corpus/manifest.json`; per-file origin + sha256 recorded). Source corpora are live; the
snapshot pins what the matrix below refers to.

## Headline matrix (52 fixtures x 4 gates)

| implementation | accept | reject | crash | notes |
|---|---:|---:|---:|---|
| flash11 (this dir) | 11 | 41 | 0 | 4/4 own positives, 3/3 canonical schemas, 4 documented escapes |
| flash13 (`WP13-F1-GATE`) | 2 | 50 | 0 | rejects all 3 canonical schemas |
| w06 (`w06-draft-1`) | 8 | 44 | 0 | accepts 3 known-bad f13 fixtures |
| canonical (`FORM-RULE-SPEC`) | 3 | 23 | **26** | crashes on every non-canonical layout |

**Canonical schema agreement:** flash11 3/3 accept, canonical tool 3/3 accept, flash13 0/3,
w06 0/3 — not unanimous. **Format-dominated rejections:** flash11 26/41 (63.4%), flash13
44/50 (88.0%), w06 9/44 (20.5%), canonical 23/23 structured rejections (100%, plus 26 crashes).
"Format-dominated" = first failed rule is an identity/layout rule (R01/R02 or w06
`single_class_id`), so the rejection does not establish semantic detection.

## Findings (D3 — disagreements are the deliverable; full list in `differential_matrix.json`)

32 findings; classification: `gate_robustness_crash` 25, `false_negative` 3,
`false_positive_or_version_skew` 12.

**A. The canonical gate crashes instead of rejecting (25 findings).**
`artifacts/formulation/tools/check_class_schema.py` raises `AttributeError: 'str' object has
no attribute 'get'` on all 16 worker-06 fixtures, all 8 flash-13 fixtures, and 2 of this
worker's fixtures. Repro:
`python3 artifacts/formulation/tools/check_class_schema.py corpus/w06/pos01_af_wcc_vac_gen.json --json`
It assumes `quantifiers` is a mapping (`.get("ordered")`); the other corpora use a string or a
different shape. A gate should return a structured `R01` reject for a non-conformant layout.
Targeted fix: type-guard each block and emit `R01 fail: quantifiers not a mapping`.

**B. Both other gates reject the lead's canonical schemas (3 findings, why they disagree with
each other is the point).**
- w06 fails `single_class_id` because it counts *every* occurrence of a class-id string: the
  canonical WCC schema mentions sibling classes in `anti_scope.not_this_class` and in
  forbidden-strengthening text, so w06 finds 5 ids. Repro:
  `python3 artifacts/worker-06/check_class_binding.py corpus/canonical/af_wcc_vacuum.yaml --json /tmp/o.json`
  Targeted fix: count class ids only in the identity block (`class_id`, `class_components`);
  require cross-references to be tagged in `anti_scope`.
- flash13 rejects them on key/vocabulary skew, e.g. `class_components.asymptotic_flatness`
  missing, `quantifier_order` must be a list, `topology.manifold` missing,
  `data_class.matter='none' is not vacuum`, genericity kind `residual_comeager` not in its
  vocabulary, `conclusion_type` looked up at top level instead of `conclusion.conclusion_type`.
  Repro: `python3 artifacts/flash-13/f1_gate/check_schema.py corpus/canonical/af_wcc_vacuum.yaml --json-out /tmp/o.json`.
  This is spec-version skew: both gates claim R01–R16 but disagree on required paths and
  vocabularies. One authoritative R-rule-to-path table is needed before any gate verdict is
  treated as gate evidence.

**C. worker-06 false negatives (3 findings).** w06 *accepts* three fixtures its own corpus
labels reject: `f13/leak_scalar_sph.yaml` (scalar matter in an AF-WCC-**VAC** class),
`f13/missing_falsifier.yaml`, `f13/vague_data_class.yaml`. flash-13 catches all three with
R05/R09/R10. Repro: `python3 artifacts/worker-06/check_class_binding.py corpus/f13/leak_scalar_sph.yaml --json /tmp/o.json`.

**D. R12/R09 lexical scans need context anchors (found during this task, fixed here).**
A bare `inextendib` token flags the canonical WCC schema, because WCC legitimately defines
singular geodesics as "future-inextendible causal geodesics". flash13's R09 makes the same
class of error on the same schema (token `inextendibility of the maximal development` taken
from forbidden-strengthening/anti-scope text). This worker now uses context-anchored patterns
(`inextendible` only when attached to spacetime/development/metric/manifold/extension) and
passes the canonical WCC schema. Targeted rule proposal: R12/R09 must specify
assertive-field + predicate-attachment semantics and must exclude `forbidden_*`, `anti_scope`,
`*_note`, and definitional uses of geodesic (in)extendibility.

**E. This worker's own gate limits (not hidden).** In own-layout mode, 26/41 rejections are
format-dominated; and 4 adversarial fixtures remain accepted by design: `adv_02` vacuous but
well-formed, `adv_03` content smuggled into an unrecognised field, `adv_04`/`adv_05`
out-of-lexicon paraphrases (see `evidence/results.json` and `evidence/adversarial*.json`).
Own-layout mutation sensitivity measured separately: 400/400 within the mutation vocabulary
(v1 393/400), explicitly an upper bound because the mutation vocabulary is the detector lexicon.

## D4 — this worker's escape rate on the worker-06 semantic corpus

**Number: 0/12 = 0.0** escape rate (no worker-06 negative fixture is accepted), measured on
corpus sha256 `58c83083f41b6ae3a4645f2ccc081c173087e85b04eff26b0c9b5330e165d1d5`.
**Caveat that must travel with the number:** all 12 rejections are format-dominated
(R01/R02 identity rules fail first on the flat layout), so this is a verdict-level 0, **not**
evidence of semantic discrimination. The complementary false-negative rate on the 4 worker-06
positives is **4/4 = 1.0** (all rejected; 3 of them by R01/R02 cascade). On the worker-06
corpus, this gate currently behaves as a layout check, not as a semantic gate.

## Falsifier (FORM-DIFF-02)

"If two independent implementations agree on a mutant that is in fact leaky (both
false-negative), differential testing is insufficient for that leak class."
**Result: not fired on this corpus.** No known-leaky fixture is accepted by two
implementations (`fixtures_with_2plus_accepting_impls` is empty). Single-implementation blind
spots found: w06 on `leak_scalar_sph`, `missing_falsifier`, `vague_data_class`; flash13 on
`probe_rephrased_leak` (its own documented blind spot); flash11 on its four documented
adversarial escapes. Two *different* implementations have *different* blind spots, which is
the good case for differential testing — but the corpus cannot currently convert that into a
clean separation because 63–100% of rejections are format-dominated. **What would fire it:**
a layout-conformant leaky mutant accepted by two gates; publishing the worker-06 corpus in the
canonical layout is the prerequisite, and is the recommended next step.

## Rev4 delta (lead follow-up 2026-09-11T23:33:37)

FROZEN.json advanced rev3 (23:33:20) → rev4 (23:34:46) while this task ran; all rev4 hashes
verify and the gate runs are bound to the actual on-disk hashes
(`af_wcc_vacuum.yaml f512af5f…`, `af_scc_c2_vacuum.yaml 836746b3…`,
`af_scc_c0_vacuum.yaml 188e5131…`, `rule_spec.json 40f9bb9e…`,
`check_class_schema.py dd8a374d…`). Deltas only:

1. **My gate was looser than rev4 on all four strengthened rules.** Before this follow-up it
   accepted all four targeted mutants below; it now implements R09 (sentence-local,
   negation-aware), R12 (widened assertive paths + sentence-local geodesic guard), R15
   (overclaim clause) and R16 (ledger direction), and still accepts all three frozen schemas.

| probe (leak) | flash11 before | flash11 after | canonical rev4 |
|---|---|---|---|
| `probe_r09_scc_asserts_completeness` | ACCEPT | **REJECT R09** | fail R09 |
| `probe_r12_leak_in_nonvacuity_path` | ACCEPT | **REJECT R12** | **pass (false negative)** |
| `probe_r15_overclaim_source` | ACCEPT | **REJECT R15** | fail R15 |
| `probe_r16_forbidden_converse` | ACCEPT | **REJECT R16** | fail R16 |
| `probe_r12_geodesic_control_accept` | ACCEPT | ACCEPT | pass |

2. **The FORM-DIFF-02 falsifier fired in the before-state.** Two independent gates (mine and
   the canonical rev4 tool) both accepted `probe_r12_leak_in_nonvacuity_path.yaml`, which is in
   fact leaky. Leak class: SCC-style spacetime inextendibility placed in an assertive field
   (`non_vacuity.condition`) whose *whole string* mentions a geodesic elsewhere — the canonical
   R12 guard is string-local (`INEXTENDIB and not GEODESIC` per string), so the unrelated
   geodesic mention exempts the leak. Minimal repro:
   `python3 artifacts/formulation/tools/check_class_schema.py .../probe_r12_leak_in_nonvacuity_path.yaml --json` → `pass`.
   **Targeted rule proposal:** evaluate the geodesic exemption sentence-locally (or
   clause-locally) and add `non_vacuity.condition`/`witness_type` to the calibration fixtures.
   After my fix the residual disagreement is canonical-only (`FD-13`).

3. **Matrix rerun (rev4, 57 fixtures incl. probes).** Corpus sha256
   `1b529be3f57b48fa…`. flash11 12 accept / 45 reject; flash13 2/55; w06 8/49; canonical
   5/52 with **0 crashes** (the rev4 tool now rejects non-canonical layouts structurally).
   Canonical schemas: flash11 3/3 accept, canonical 3/3 accept, flash13 0/3, w06 0/3.
   D4 numbers unchanged: my escape rate on worker-06 negatives 0/12 = 0.0, but still
   format-dominated; false-negative rate on its positives 4/4.
   Evidence: `evidence/rev4_delta_probes.json`.

## Rev5 addendum (lead follow-up 2026-09-11T23:35:45)

Deltas only, against frozen revision 5 (canonical tool `eef3f43f…`; schemas and rule_spec
unchanged from rev4):

* **0 verdict deltas** on all 57 fixtures x 4 gates between the rev4-tagged snapshot and the
  rev5 rerun. Stats identical: flash11 12 accept / 45 reject, flash13 2/55, w06 8/49,
  canonical 5/52.
* **Crash channel confirmed fixed.** The clean before/after is the first matrix run
  (tool `abb3003c`, rev2: **26/52 crashes**) vs the rev5 era (**0/57**, structured `R01`
  rejections on non-canonical layouts). The rev4-tagged snapshot was taken after rev5 was
  frozen, so it already contains the rev5-era tool — no clean rev4-only run exists.
* **Rule-id deltas: 3, all for worker-06 on the three canonical schemas.** Its verdict is
  unchanged (reject). FD-03 is re-diagnosed: w06 draft-2 no longer reports
  `single_class_id`; it now fails on `no_composite_regularity_string` (quoted forbidden
  phrases such as "C0 or C2" are not exempted), `regularity_selector` (a stray `C2` token),
  and `conclusion_family_match` (its conclusion-block extraction ingests booleans/strings).
  Repro: `python3 artifacts/worker-06/check_class_binding.py artifacts/formulation/schemas/af_wcc_vacuum.yaml --json /tmp/o.json`.
* **Format-dominated caveat unchanged and prominent:** canonical 49/52 rejections
  format-dominated (94.2%), flash13 49/55 (89.1%), flash11 26/45 (57.8%), w06 10/49 (20.4%).
  D4: my worker-06-negative escape rate is still **0/12 = 0.0 at verdict level only**; my
  false-negative rate on its positives is 4/4. This remains a layout check, not a semantic
  gate, on that corpus.
* Falsifier: still not fired in the current state; canonical-only R12 false negative on
  `rev4probes/probe_r12_leak_in_nonvacuity_path.yaml`, plus w06's three known misses.
* Manifest note: `FROZEN.json` carries its own previous-revision hash, which cannot match the
  current file; self-hash fields are stale by construction.

## Provenance / claims discipline

- Every verdict in `differential_matrix.json` is reproducible from the recorded command line;
  per-fixture sha256 and the corpus sha256 are recorded.
- No implementation is declared correct. The schema owner (`lead-formulation`) binds
  interpretation; this worker reports disagreements and does not resolve them.
- Gate runs recorded: 52 fixtures x 4 gates = 208 subprocess runs (one gate run against the
  canonical schemas included). Canonical schema hashes at run time:
  `af_wcc_vacuum.yaml 31ac6820…`, `af_scc_c2_vacuum.yaml 9aab12d5…`, `af_scc_c0_vacuum.yaml 684afaac…`
  (not yet present in `runtime/state/artifact_hashes.json` at the time of writing).

## Rev19 delta addendum (bounded worker run 2026-09-12T00:08+08:00)

Deltas only, against the FROZEN manifest revision 19 (`frozen_at 2026-09-12T00:04:48+08:00`;
canonical tool `000e09e4…`, schemas `f962c117…` / `e9fcefe6…` / `bdb23f76…`, rule_spec
`40f9bb9e…`). Baseline = the rev5-era matrix snapshot
`evidence/differential_matrix_rev5.json` (`12cec7fe…`). Corpus rebuilt: only the three
canonical schema copies changed (fixture sources byte-identical), corpus sha
`1b529be3…` → `35f9d812…`. Full report: `evidence/rev19_delta.json`.

* **2 verdict deltas, 25 rule-id deltas; all other verdicts identical.** Both verdict deltas
  are canonical on the rev4-era R12 probes: `accept → reject`. Stats: flash11 12/45,
  flash13 2/55, w06 8/49 unchanged; canonical 5/52 → 3/54.
* **Those two deltas are R28 true positives on stale fixtures, not the R12 fix.** The rev4
  probes were `deepcopy` of the rev4 canonical WCC schema and inherited its defect: a
  `[open_dense_escape, residual_comeager] direction: transfers` row sitting inside
  `transfer_failures`. Rev19's R28 truth table correctly rejects that. Rebuilt from the
  frozen rev19 base (`evidence/probes_rev19/`), the control is accepted by canonical and
  flash11 (**no false positive**), and **canonical still accepts the R12 leak probe with zero
  failed rules → FD-13 remains open**. Claiming FD-13 closed from the stale-probe deltas
  would be wrong.
* **Rebased probes isolate the four strengthenings** (`evidence/rev19_rebased_probes.json`):
  canonical catches R09/R15/R16 on the expected rule id; flash11 catches R09/R12/R15/R16;
  R12 leak: flash11 REJECT R12, canonical accept (single-implementation blind spot);
  R12 control: both accept. flash13/w06 reject all five on layout/identity rules.
* **Targeted rule proposal:** extend canonical R12's path list with `non_vacuity.condition`
  (and sibling assertive fields), then re-run both R12 probes. Falsifier re-fires if
  canonical then accepts the leak or rejects the control.
* **Falsifier (FORM-DIFF-02) not fired at matrix level:** 0 known-leaky fixtures with ≥2
  accepting implementations. The residual is canonical-only (FD-13).
* **Format-dominated caveat unchanged and prominent:** canonical 49/54 rejections
  format-dominated (90.7%), flash13 49/55 (89.1%), flash11 26/45 (57.8%), w06 10/49 (20.4%).
  D4 unchanged: my escape rate on worker-06 negatives 0/12 = 0.0 at **verdict level only**;
  false-negative rate on its positives 4/4. This is a layout check on that corpus, not a
  semantic gate.

## FD-13 follow-up (2026-09-12, `fd13/`)

**Correction to the rev19 note above.** The rev19 tool (`000e09e4…`) *already* scans
`non_vacuity.condition` (line 71); the "extend the path list" proposal above is superseded.
The real defect is the **scope of the geodesic exemption** at lines 312–314: `GEODESIC.search(s)`
runs over the whole field, so the legitimate words "future **geodesically** incomplete" in
`non_vacuity.condition` exempt the entire multi-sentence field and let a later sentence
*"The maximal development is C^2-inextendible."* (SCC content) pass uncaught.

* Byte-minimal repro (one appended sentence, no YAML round-trip) on both the frozen rev19 base
  (`f962c117…`) and the live authoring schema (`b65fcc0f…`): canonical **accepts both**.
* Proposed fix: clause-local exemption (`r12_proposal.diff`, patched tool `5eaab3f8…`).
* Measurement (`fd13/fd13_results.json`): 2/2 leaks caught by the fix and independently by
  flash11; 0 false positives on 5 controls × 3 gates; 57/57 corpus fixtures swept,
  **0 verdict changes** (1 additive `R12` on an already-`R28`-rejected stale probe);
  falsifier NOT fired.
* Still lexical, not semantic — a leak phrased without `inextendib`/`extension`/`horizon`
  tokens passes. See `fd13/README.md` for the caveats that must travel with this.

## Rev29 delta addendum (bounded worker run 2026-09-12T01:07+08:00)

Deltas only. FROZEN **rev29** (`815e08079aefbc…`, frozen_at 00:57:26); canonical tool
`000e09e4…` (unchanged), schemas rev13 `d9cebb9404b2…` / `e9a27996dfd3…` / `b2ab6acb2bbe…`,
rule_spec `40f9bb9e…`, KEY_MANIFEST `014e2d30…`. All pins verified byte-exact on disk before the
run. Baseline = the preserved rev19-rebased matrix
(`evidence/differential_matrix_rev19_rebased.json`, `e0c21b99…`, corpus `cead74aa…`); new matrix
`differential_matrix.json` = `evidence/differential_matrix_rev29.json` (`74f2decb…`, corpus
`b3086344…`); full report `evidence/rev29_delta.json` (`a708384a…`, hash recomputed after the
env-note correction below).

* **0 verdict deltas; 5 rule-id deltas** on 57 fixtures × 4 gates. Stats identical: flash11
  12/45, flash13 2/55, w06 8/49, canonical 3/54. Findings 16 → 16, none new, none resolved.
  Falsifier (FORM-DIFF-02) NOT fired: 0 known-leaky fixtures with ≥2 accepting implementations.
* **The 5 rule-id deltas are environment-driven, not schema-driven.** All five are canonical
  `R22 unknown keys: ['revised_at_unused']` additions on stale rev4-era probes, caused by the
  live KEY_MANIFEST moving between the two runs: `revised_at_unused` is present in the older
  manifest copies `fd13/KEY_MANIFEST.json` (`8ce752b5…`) and
  `fd13_rev26/rev27_env_km_fce91948/KEY_MANIFEST.json` (`fce91948…`) and absent from
  `014e2d30…` (rev28/rev29). R22 is additive on fixtures already rejected at
  R09/R15/R16/R28 → no verdict change, no semantic effect. Corpus diff: 57 rows, 0
  added/removed/byte-changed/expected-changed outside `corpus/canonical/*`; **only the three
  canonical schema copies changed (rev12 → rev13)**. This corrects the inherited
  `single_variable_note` in the delta report.
* **FD-13 rebased to rev29 and still OPEN** (`fd13_rev26/rev29_results.json`): the byte-minimal
  WCC leak `leak_rev29.yaml` (`90ae1b59…`) is accepted by canonical base with no rules;
  patched `5eaab3f8…` and independent flash11 `a89b221c…` both reject it at R12; control
  `control_rev29.yaml` (`052f61ae…`) and all three canonical schemas are accepted by all three
  gates. Targeted effect identical to rev28fix (1/1 escape, 1/1 catch by patch, 1/1 catch by
  independent gate, 0 false positives); rebase and proposal falsifiers NOT fired.
* **Format-dominated caveat unchanged and prominent:** canonical 49/54 rejections
  format-dominated (90.7%), flash13 49/55 (89.1%), flash11 26/45 (57.8%), w06 10/49 (20.4%).
  D4 on worker-06 corpus unchanged at verdict level only: escape rate on its negatives 0/12 =
  0.0, false-negative rate on its positives 1.0 (4/4 rejected) — a layout check, not a semantic
  gate.
* **No node completion, no validation_status=passed, no gate verdict, no canonical artifact
  modified by this worker.** Disagreements and the FD-13 leak remain the deliverables.
