# W044-F2B-REV13-INTEGRATION-01 — composed rev13/14 F2b repair + pin closure

**Worker:** worker-044 · **Node:** F2b · **Class:** `AF-SCC-C0-VAC-GEN` · **Gate:** G-FORM
**Snapshot:** 2026-09-12T00:56:02+08:00 (all results bound to `pinned/` hashes)
**Verdict:** `COMPOSED_F2B_REV14_CANDIDATE_ACCEPTANCE_READY_IN_SANDBOX` (worker measurement only)

## Why this task exists

Two repair families were proposed independently for F2b:

- **containment** — worker-066's two-edit patch (from worker-008's finding): the false containment
  denial in `regularity.must_not_conflate[0]` and the inverted size premise in
  `implication_ledger.forbidden_transfers[0].reason`;
- **binding** — worker-044's acceptance oracle (with worker-086's evidence-collision root cause and
  worker-005's alias-registry finding): restore the enriched self-verifying evidence document, bind
  `VOCAB_ALIASES.json` by path+sha256, make the evidence writer non-writing.

Nobody had checked whether the **union** is sufficient and consistent as one atomic revision, nor
what else must move with it. That is this task.

The target also moved mid-flight: at 00:53:20+08:00 a separate lifecycle
(`astra-life05-evidence-binding-repair`) rewrote all three class schemas plus
`gate_test_report.json` without refreshing FROZEN (measured 7 drift problems at 00:53:41), and at
00:55:02 FROZEN rev29 was regenerated to absorb that drift. The measurement below is therefore
snapshot-bound; live drift after the snapshot is reported, not hidden.

## Snapshot state (what the owner starts from)

| check | result |
|---|---|
| containment defects (H1 inverted premise, H2 false denial) | **2 live defects** |
| A1 declared evidence hash resolves | pass (the 00:53 edit moved the declaration to the lean `9e335e9b`) |
| A2 evidence self-verifying (carries input pins) | **fail** |
| A6 alias registry bound | **fail** |
| canonical structural gate (C0/C2/F1) | 0 / 0 / 0 |
| FROZEN rev29 | 0 problems (freeze breach already absorbed at 00:55:02) |
| F2 aggregator SEP-6 component pins | **stale** (pinned rev11 `1bb78ce9` / `b6123750`) |

## Composed candidate (sandbox only)

| edit | content |
|---|---|
| R1/R2 | worker-066's two containment edits, applied byte-exactly to canonical **and** authoring mirrors |
| R3a | restore the enriched self-verifying evidence doc (`675a99d0d25b`) at the declared canonical path |
| R3b | **all three** schemas (C0/C2/F1 × canonical+authoring) re-declare `675a99d0d25b`; schema revision 13→14 |
| R4 | `extensions.vocabulary_binding` in C0/C0A: alias registry path + sha256 |
| R6 | worker-086's non-writing writer guard replaces `check_taxonomy_consistency.py` |
| R7 | regenerate `KEY_MANIFEST.json` from the authoring schemas |
| R8 | `regenerate_frozen.py --revision 29`: refresh every pin (`verify_frozen` 0 problems) |
| R9 | re-pin the F2 aggregator C0 component to the composed hash and C2 to the snapshot hash, revision 6→7 |

Composed hashes: C0 `48cadb72e507` (canonical == authoring), evidence `675a99d0d25b`,
FROZEN `2538ab0e3c86`, KEY_MANIFEST `61b9d8c187c0`, aggregator `601355e7ccab`.

## Result

| check | snapshot | composed |
|---|---|---|
| H1H2 containment | fail | **pass** |
| A1 evidence hash resolves | pass | pass |
| A2 evidence self-verifying | fail | **pass** |
| A3 FROZEN evidence pin | pass | pass |
| A4b/A5b class-axis equivalence | pass | pass |
| A6 alias registry bound | fail | **pass** |
| A7 structural gate | pass | pass |
| A8 class separation | pass | pass |
| structural gates C0/C2/F1 | 0/0/0 | 0/0/0 |
| `verify_frozen` | 0 problems | 0 problems |
| aggregator SEP-6 | stale | **ok** |
| mirrors byte-equal | yes | yes |

**8/8 controls discriminate**: K1/K2 revert each containment edit, K3 stale declaration → A1 fails,
K4 unbind registry → A6 fails, K5 skip freeze refresh → `verify_frozen` nonzero, K6 revert
aggregator re-pin → SEP-6 fails, K7 unguarded writer moves the evidence, K8 class-separation
positive control fires. The guarded writer left the evidence at `675a99d0` over two runs and
`verify_frozen` stayed at 0 problems. The structured closure scan reports **no machine-binding
stale references**; remaining `9e335e9b` mentions are historical prose in `binding_note` /
`revision_history` only.

## What this does and does not establish

It establishes that the union of the two repair proposals, plus the pin closure they omit, is
internally consistent and acceptance-ready **in the sandbox**. It does not publish anything: the
canonical tree is untouched, no gate verdict, node status, or `validation_status=passed` is set,
and there is no mathematics or physics claim. The next revision numbers (schema rev14, FROZEN
rev30 or the next free one) are the owner's choice, and R3b needs the owner's sign-off because it
supersedes the 00:53 declaration in F1/F2a as well as F2b.

**Falsifier.** The report is falsified if (a) any check reported pass measures fail (or vice versa)
on the pinned bytes; (b) any of K1–K8 fails to flip its target check; (c) the containment pair does
not match worker-066's `proposed_patch.diff`; (d) `verify_frozen` or any structural gate is nonzero
after regeneration; (e) SEP-6 leaves a stale component pin; (f) either guarded-writer run moves the
evidence hash; (g) a live machine-binding file still references an old moved hash; (h) `pinned/`
does not reproduce the snapshot hashes; (i) a pinned input drifts after the snapshot, which voids
live applicability but not the snapshot measurement. All checks are re-runnable from `report.json`.

**Credit.** Containment patch worker-066 (finding worker-008); evidence collision/restore and writer
guard worker-086; alias-registry finding worker-005; this task composes them and adds the
change-impact closure (KEY_MANIFEST, FROZEN drift, schema mirrors, aggregator SEP-6) and the
durability test.
