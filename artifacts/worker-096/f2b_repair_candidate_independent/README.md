# W096-F2B-REPAIR-CANDIDATE-INDEPENDENT-VERIFY-01

Worker `worker-096` · Node `F2b` · Class `AF-SCC-C0-VAC-GEN` · Gate `G-FORM` · Read-only on every
canonical path.

## One-line result

At the live F2b rev13 bytes (`schemas/af_scc_c0_vacuum.yaml` sha256 `b2ab6acb2bbe…`, FROZEN rev29
`815e08079aef…`), an independently written, fail-closed harness verifies that **both staged
worker-080 corrected repair candidates — `candidate_corrected` `51c253c46306…` and
`candidate_nesting_only` `4951cc969803…` — clear both live defects, change exactly the two declared
carrier leaves, introduce no defect under the document's own containment order, and pass the
canonical structural gate**. The circulating candidate `84b5d3fa29a6…` is independently confirmed
**defective**: its line-152 replacement asserts `H2_loc-inextendibility ENTAILS this class's
conclusion` inside the C0 file, which inverts the file's own chain (repair-introduced
`direction_inverted`). The canonical gate returns `pass` for live, for the defective candidate and
for the corrected candidates — it is blind to all of these defects (re-measured).

## Pins measured before and after (0 drift)

| artifact | sha256 |
|---|---|
| `schemas/af_scc_c0_vacuum.yaml` (live F2b rev13) | `b2ab6acb2bbe7f86…` |
| `artifacts/formulation/schemas/af_scc_c0_vacuum.yaml` (mirror) | byte-identical |
| `schemas/af_scc_c2_vacuum.yaml` (C2 sibling) | `e9a27996dfd308bd…` |
| `artifacts/formulation/FROZEN.json` (rev29, declares the live F2b pin) | `815e08079aefbc16…` |
| `artifacts/formulation/rule_spec.json` | `40f9bb9e657b2c6b…` |
| `research_map/formulation_taxonomy.yaml` (F0 rev5) | `0abb9ed8a96135c9…` |
| `artifacts/formulation/formulation_taxonomy.yaml` (supplement) | `d7419b4e8963cb71…` |
| `artifacts/formulation/VOCAB_ALIASES.json` | `46cd9f1eb534df73…` |

## Method (own harness; worker-080's/022's/100's code not imported or executed)

1. Strict duplicate-key-aware YAML parse of every input; sha256 pins measured before and after
   (drift fatal, exit 2).
2. The document's **own** `implication_ledger.extension_class_containment` chain is parsed into an
   extension-set order (`E_C0 ⊇ E_H2loc ⊇ E_{C^1,1} ⊇ E_C2`); every normative size premise,
   containment assertion/denial and entailment direction is adjudicated against that order,
   class-relatively (`"this class"` resolves through `class_components.regularity_token`).
3. Candidate-vs-live leaf-path delta must be a subset of the two declared carriers
   (`regularity.must_not_conflate[0]`, `implication_ledger.forbidden_transfers[0].reason`), and the
   line diff must be exactly lines 152 and 246.
4. Canonical structural gate (`artifacts/formulation/tools/check_class_schema.py`) run as
   corroboration on snapshot copies only.
5. Planted controls must fire; a control that does not fire is a harness failure.

## Results

| document | hard defects under its own chain | changed lines | canonical gate |
|---|---|---|---|
| live `b2ab6acb` | `containment_denial` (`:152`), `size_premise_inverted` (`:246`) | — | pass (blind) |
| C2 sibling `e9a27996` | none | — | pass |
| `candidate_corrected` `51c253c4` | **none** | 152, 246 | pass |
| `candidate_nesting_only` `4951cc96` | **none** | 152, 246 | pass |
| `candidate_84b5d3fa` (circulating) | **`direction_inverted`** (`:152`) | 152, 246 | pass (blind) |
| `candidate_worker022` `a110f8e8` | none on this predicate | 152, 246 | pass |

Both corrected candidates share the line-246 fix (`strictly larger` → `strictly smaller` (E_C2 ⊂
E_C0)); they differ only in the line-152 replacement: `candidate_corrected` states the correct
direction explicitly (`this class's conclusion ⇒ H2loc-inext; H2loc-inext ⇒ C2 sibling`),
`candidate_nesting_only` states the nesting and points at the ledger without an entailment claim.
Both were checked against the sibling, the ledger's `one_way_entailments` rows, `forbidden_weakenings`
and `subsumed`/`cross_family` prose. Controls: **11/11** (live fires both defects; 84b5d3fa fires the
inversion; flipped-direction, inverted-chain, non-carrier-change, duplicate-key and pin-drift
mutations are all caught; the C2 sibling's identical sentence is correctly *not* flagged).

## Advisory findings (for the gate owner; not gate verdicts)

- **F1 — verdict census vs controller coverage.** Ten review files on disk at run time bind
  `b2ab6acb2bbe`, including **three `accept` verdicts** (worker-052 4.0, worker-071 4.0
  `counts_as_full_schema_verdict=true`, worker-072 4.0) and seven `revise`. The pass-06 controller
  state reads F2b coverage `0`. This receipt does not adjudicate the controller's
  independence/at-hash filter; it records the measured discrepancy (the accept files are recent —
  mtimes 01:10–01:11 — and the tree is live).
- **F2 — fixture drift.** The two old strings remain in 115 files (`C2 is a strictly larger extension
  class`) and 75 files (`No containment with C2 or C0 is asserted here`), including FROZEN-pinned
  canonical/mirror/review artifacts. The proposed new strings appear in 0 non-sibling files; the
  sibling's true instance of `H2_loc-inextendibility ENTAILS this class's conclusion` is in its own
  2 pinned files and is correct there. Landing should note the stale fixtures rather than silently
  regenerate pinned evidence.
- **F3 — landing consequence.** Any landing must bump revision/`revised_at`, so the landed bytes will
  **not** equal the candidate hash; every verdict bound to `b2ab6acb` is void on the move, and the
  landed revision needs its own freeze and fresh independent verdicts.
- **F4 — detector context.** Naive lexical detectors false-positive on quoted meta-audit prose
  (`[R2 major: the earlier 'no containment …' was wrong]`); this harness's detectors are
  quote/bracket-context aware, and that context rule is itself covered by controls (relevant to
  CF-26).

## Non-claims

No mathematics or physics claim; no canonical write; no node status; no `validation_status=passed`;
no gate verdict; no landing authorization. Verdicts bind staged, non-canonical files only.
`candidate_worker022` is measured but **not adjudicated** here (worker-100's REP-CD-02 wording
finding is outside this predicate's scope).

## Falsifier

Re-run `verify_candidates.py` on the same pins. Falsified if any declared pin moves, a control stops
firing, either worker-080 candidate yields a hard defect under the document's own chain, a corrected
candidate differs from live outside the two declared carriers, or the canonical gate fails on a
candidate.

## Files

| file | role |
|---|---|
| `verify_candidates.py` | deterministic read-only harness (`f1e06d3bf2cd…`) |
| `report.json` | full machine report (`bdef57934706…`) |
| `runlog.txt` | verbatim stdout of the final run, exit 0 (`5593faa86d45…`) |
| `snapshots/` | byte snapshots of live, C2 sibling and all four candidates, hash-pinned |
| `../../runtime/state/w096_checkpoint_9.json` | worker-local resumable checkpoint |
