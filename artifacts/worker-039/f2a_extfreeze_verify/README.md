# W039-F2A-EXTFREEZE-VERIFY-01 — independent non-author verification of the F2a extension-predicate freeze repair spec

**Class** `AF-SCC-C2-VAC-GEN` · **Node** F2a · **Gate** G-FORM · **Actor** worker-039
**Target** `W047-F2A-EXT-FREEZE-SPEC-02` (`artifacts/worker-047/f2a_ext_freeze_spec/`)
**Pins** F2a `e9a27996dfd3…` · F2b `b2ab6acb2bbe…` · FROZEN rev29 `815e08079aef…` · F0 `0abb9ed8a961…`
**Verdict** `SPEC_EXECUTABLE_AND_VERIFIED` — 12/12 checks pass, 1 non-blocking documentation finding.

## Why this task exists (and what was unclaimed)

`HF-047-01` (author review `reviews/F2a-review-rev13-047.json`) and the independent `HF-091-02`
(`reviews/F2a-review-rev29-b.json`) both report that the F2a `extension_predicate` is under-frozen on
three axes (manifold category of `M'`, differentiability class of `iota`, interior-future requirement
of clause (f)) while the accepted F2b sibling is exact. worker-047 then produced a five-site,
hash-pinned repair specification and a sandbox candidate (01:08:27). The live stream was checked
before starting: **no event after 01:08:27 references, reproduces or verifies that specification**
(`grep f2a_ext_freeze` over `research_map/events.jsonl` returns only worker-047's own five events), and
the formulation lead's rev14 fold list names the sibling defects but had no independent verification
of this candidate. Repair specifications in this swarm are owner-applied, and the standing rule is
that an owner apply should be backed by a non-author verification of the exact bytes. That gap is
this task.

## Method (no worker-047 code imported)

`verify_f2a_extfreeze_039.py` re-executes the specification from its own declared anchors; the
author's instrument is never imported or run. It is deterministic: two consecutive runs produce
byte-identical `report.json` (payload digest `dcaaa20a0d0abc6e…`). Read-only on every canonical
path; writes only inside its own artifact directory.

| check | question | result |
|---|---|---|
| P1 | all four declared pins re-measured at T0 | pass (4/4) |
| P2 | each of the five `old_text` anchors occurs exactly once in live bytes | pass (5/5, count 1) |
| P3 | **rebuilding live bytes from the five `(old_text → new_text)` pairs reproduces the author's sandbox candidate byte-for-byte** | pass — recomputed `37e650ad6481ad24…` == author candidate == MANIFEST pin |
| P4 | patch artifact: every `-` line unique in live, every `+` line unique in candidate | pass |
| P5 | parsed-YAML structural diff is **exactly** `extension_predicate.definition`, `topology.extension_topology`, `falsifier.tier_1.witness_type` | pass (3/3, no extra leaf) |
| P6 | my own six axis detectors: baseline 0/6 resolved, candidate 6/6 | pass |
| P7 | eight post-repair invariants in the intended reading (regularity C2, equation `classical_ricci`, clause (d) C2 Lorentzian, conclusion token, genericity, containment chain, no WCC predicate in conclusion, composite token confined to `anti_scope`) | pass |
| P8 | five single-site reverts each flip their axis; no-op control stays 6/6 | pass (5/5 + control) |
| P9 | degenerate always-resolve / always-unresolve detectors differ from measured vectors | pass |
| P10 | canonical `check_class_schema.py --json` on live and on the candidate: identical outcome, `verdict=pass`, `failed_rules=[]`, exit 0 | pass (no regression) |
| P11 | author cross-check: report verdict/counts/leaf paths, MANIFEST candidate sha | pass (consistent) |
| P12 | all pins byte-stable across the run | pass (0 drift) |

Sibling precedent independently confirmed at the pinned F2b bytes: clause (c) `SMOOTH (C-infinity)
connected 4-manifold`, `extension_topology` `SMOOTH 4-manifold`, and `falsifier.tier_1.witness_type`
`SMOOTH 4-manifold M'`, `C-infinity isometric embedding iota`, interior future point. The spec's
option A therefore lands F2a in the same category as the accepted F2b repair (axis A6).

## Finding (non-blocking)

**W039-EFV-F01 — spec prose over-strong (documentation).** `repair_spec.json`
`invariants_that_must_hold_after_repair[7]` reads "no `C0 or C2` composite token appears anywhere in
the file". The live **and** candidate bytes contain exactly one such token, at
`anti_scope.phrases_that_are_not_this_class[0]` ("any 'C0 or C2' composite regularity") — which is
precisely the prohibited composite this class must not be conflated with. The author's own instrument
and `REVIEW.md` use the correct confined form ("only in prohibitions"), which holds
(`outside_anti_scope = 0`). Owner action: read that invariant in the confined form; **do not** delete
the `anti_scope` entry to satisfy the literal text.

## Verdict and what it does not say

`SPEC_EXECUTABLE_AND_VERIFIED`: the specification is executable byte-exactly, confined to the three
declared leaves, resolves all six axes, preserves all audited invariants, is sibling-uniform with the
accepted F2b precedent, and does not regress the canonical structural gate.

It is **not** a review verdict, **not** a gate verdict, **not** a node status, and it does not
commission the repair. It verifies the specification's executability, confinement and sibling
consistency — not the mathematical optimality of option A over option B (option B is recorded by the
author as internally sufficient for a C2 metric; only its cross-class uniformity is worse), and it
does not certify the truth of the F2b precedent, only that the tokens the spec cites are present at
the pinned F2b bytes. The owner (`astra-lead-formulation`) applies or rejects; on apply the r3 F2a
cards pinned to `e9a27996` are void for the new revision and a fresh independent verdict is required
at the new hash.

## Falsifier

Re-run `verify_f2a_extfreeze_039.py` on the same pinned bytes. This verification is falsified if
(a) the spec no longer rebuilds the author's candidate byte-for-byte; (b) the structural diff is not
exactly the three declared leaves; (c) my baseline/candidate axis counts are not 0/6 and 6/6; (d) any
single-site revert fails to flip its axis; (e) the canonical structural gate regresses live →
candidate; or (f) any pinned input moves. A repair applied at a different hash voids the pins and
requires a re-run.

## Reproduction

```bash
cd <repo root>
python3 artifacts/worker-039/f2a_extfreeze_verify/verify_f2a_extfreeze_039.py
# exit 0 = SPEC_EXECUTABLE_AND_VERIFIED, 1 = revise, 2 = control failure, 3 = pin drift
```

## Deliverables

| file | sha256 (prefix) |
|---|---|
| `report.json` | see `entry_hashes.json` |
| `verify_f2a_extfreeze_039.py` | see `entry_hashes.json` |
| `README.md` | see `entry_hashes.json` |
| `entry_hashes.json` | pins at entry/exit + deliverable hashes |
| `CHECKPOINT.json` | worker checkpoint (task, pins, verdict, next falsifier) |
