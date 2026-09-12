# W038-F0-CONFORMANCE-02 — F0 recheck at FROZEN revision 28

Worker `worker-038`. Node **F0**, gate **G-F0**, classes
`AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH`.
Run at 2026-09-12T00:36–00:37 (+08:00).

## Why this run exists

`W038-F0-CONFORMANCE-01` accepted F0 at rev4 `276009f4` and then filed
`F0-FREEZE-DRIFT` (`w038-f0-conformance-moving-target-blocker-20260912T003250`):
the canonical taxonomy had moved to rev5 `0abb9ed8` while FROZEN rev26 still pinned
rev4, so no binding G-F0 verdict was possible. `astra-lead-audit` (`reviews/G-F0-final-verify.json`,
00:35:21) recorded the same as **B-GF0-1** (zero verdicts at the frozen hash) and
**B-GF0-2** (canonical != authoring unadjudicated) and proposed `pending`.

FROZEN.json revision 28 (`frozen_at` 00:35:08, sha `2f358f6722d9`) pins canonical
`0abb9ed8`, supplement `d7419b4e` and the three schemas. This run re-checks
conformance **at that frozen revision** and closes the freeze-integrity question.

## What was run (all four exit 0; pins identical before and after — `run_manifest_rev28.txt`)

| # | command | result |
|---|---|---|
| 1 | `validate_taxonomy.py --self-test` (declared checker) | exit 0 |
| 2 | `validate_taxonomy.py --json worker01_validation_rev28.json` | **253 pass / 0 fail**, verdict `pass` |
| 3 | `check_f0_independent.py --json-out independent_checks_rev28.json` | **11 PASS / 0 FAIL / 2 NOTE**, verdict `accept` |
| 4 | `freeze_integrity_check.py --json-out freeze_integrity_rev28.json` (new) | **44/44 files pins, 2/2 logical pins, 5/5 F0-critical pins match; 0 files modified after `frozen_at`; manifest stable**, verdict `accept` |

Inputs held at: canonical F0 `0abb9ed8a96135c9`, supplement `d7419b4e8963`, A0 rubric
`d748a9e3574e`, FROZEN `2f358f6722d9` (rev 28), declared checker `2cc8ee04023e`.

## Verdict

**`accept`, score 3.5**, bound to `research_map/formulation_taxonomy.yaml#0abb9ed8a961`
under FROZEN rev28. `reviews/F0-conformance-038-rev28.json#` carries the full review;
`artifacts/worker-038/f0_conformance/rev28_verdict.json#` is the machine summary.

Two non-blocking findings:

- **W038-02-F1** independently confirms `astra-lead-audit` **O-GF0-1**: for
  `AF-WCC-SCALAR-SPH`, `axes.genericity_kind == "unresolved"` and H4 says the
  genericity notion is unresolved and must be named before any claim is filed, yet the
  rev5 conclusion quantifies over *"a comeager set G of data"*. Field and conclusion
  disagree, and **no declared or independent checker compares `genericity_kind`**, so
  all three suites still pass. Repair in the next revision; claim filing on this class
  stays blocked by H4.
- **W038-02-F2** records the pre-rev28 freeze drift this new check was written to
  catch: at 00:35:06, rev27 (`5fa3b3bf95f2`) mismatched five listed files. Rev28
  matches all 44. The fix landed before this verdict, so the drift is historical.

## What this changes for the gate

- **B-GF0-1:** one non-author `accept` now exists at the frozen hash. It is **not
  blind** (worker-038 reviewed rev4 and probed rev5), so worker-038 counts as **one**
  distinct reviewer; the second required verdict must come from a different identity.
- **B-GF0-2:** unchanged and still controller-side (REC-1 pair-check exception vs
  REC-2 re-freeze). Supporting measurement only: rev28 keeps canonical and supplement
  as distinct logical artifacts, both pins match disk, and no pinned file changed
  after `frozen_at`.

## What this is not

Not a gate verdict, not a node-completion claim, not a physics judgement. A worker
event cannot set `status=done`, `validation_status=passed` or a gate verdict
(`comms/PROTOCOL.md`; `ASTRA_HANDOFF` authority note). F0 stays `draft_unverified`;
G-F0 stays `pending`.

## Falsifier

A reader who (a) shows any resolved id/symmetry/matter/conclusion axis is misread by
`check_f0_independent.py`, (b) exhibits a merged-regularity string the IND-08
normalization misses in a class block, (c) shows a taxonomy case naming a non-frozen
class or an unresolved hypothesis, (d) shows a canonical/supplement class-id mismatch,
or (e) shows a FROZEN rev28 pin whose bytes differ from the pin, refutes the
corresponding PASS; any substantiated FAIL flips the verdict to `revise`. The verdict
is void if FROZEN.json or the canonical taxonomy moves from the measured hashes.

Re-run: `bash artifacts/worker-038/f0_conformance/run_rev28.sh`.
