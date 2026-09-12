# W062-GFORM-R03-SCHEMA-REPAIR-CANDIDATE-01

Bounded class-bound worker task (worker-062, instance `worker-062-20260912T010416-968807`, 2026-09-12).
Node F1 (class `AF-WCC-VAC-GEN`), nodes F1/F2a/F2b, gate G-FORM. **No inbox card existed; task self-selected.**

## Question

`HF-W062-REV13-01` (and worker-16's `W16-REV29-CORPUS-REBIND-01-blocker`) established that
`run_acceptance.py` cannot exit 0 at FROZEN rev29 / rev13: after the corpus is rebased to C0
`b2ab6acb2bbe`, the **frozen** stage-B auditor rejects canonical F1 because the ordered binder
`(q,t0)` is not a literal substring of `quantifiers.formal`, which spells the quantifier
`not exists q in I+ and t0 in [0,T)`.

Two repair paths exist: a **tool-side** change (worker-006's `FORM-R03-V2` binder-head proposal,
not adopted, **not used here**) and a **schema-side** notation agreement (this task). This task asks
whether a *one-line, semantics-preserving* schema change makes the **unmodified frozen pipeline**
reproducibly PASS end-to-end.

## Result

Fresh mirror sandbox, canonical bytes copied in, corpus regenerated from C0 `b2ab6acb2bbe`,
frozen tools byte-identical to canonical and unchanged (gate `000e09e46b2f`, auditor `c79d8ab8440a`).

| run | pipeline rc | verdict | F1 structural/semantic | union | bytes |
|---|---:|---|---|---|---|
| baseline (unpatched, rebased corpus) | 1 | FAIL | pass / **fail (R03)** | 31/31 | canonical `d9cebb9404b2` |
| **CAND-A** formal product notation | **0** | **PASS** | pass / **pass** | 31/31 | `bf1798b57997` |
| **CAND-B** ordered binder `q` (rev11 precedent) | **0** | **PASS** | pass / **pass** | 31/31 | `ebb8d6671614` |

Both candidates: structural gate pass, frozen semantic stage `accept` with `failed_rules: []`,
canonical rows 3/3 `ok`, pipeline controls ok, mutation-corpus union 31/31, and the preflight
stale-corpus guard reproduced (rc 3 before rebase). Candidate hashes were identical across three
deterministic re-runs.

### The exact one-line diffs

```
CAND-A  artifacts/formulation/schemas/af_wcc_vacuum.yaml (line 48, quantifiers.formal)
-    not exists q in I+ and t0 in [0,T) with gamma([t0,T)) subset J^-(q) intersect M.
+    not exists (q,t0) in I+ x [0,T) with gamma([t0,T)) subset J^-(q) intersect M.

CAND-B  artifacts/formulation/schemas/af_wcc_vacuum.yaml (line 55, quantifiers.ordered[5].binder)
-    - {kind: not_exists, binder: "(q,t0)", domain_id: D5}
+    - {kind: not_exists, binder: "q", domain_id: D5}
```

Parsed-structure delta is confined to the declared path in each case (`quantifiers.formal` /
`quantifiers.ordered.5.binder`); `class_id`, `revision`, `f0_binding` and `conclusion` are unchanged.
The formal sentence is logically equivalent in CAND-A (independent domains `I+` and `[0,T)`); CAND-B
leaves the formal sentence byte-identical and restores the rev11 binder that passed the frozen test,
at the disclosed cost that `t0` is no longer named in the ordered prefix.

## Controls

`K1` repair reverted → frozen R03 rejects again (PASS). `K2b` (post-hoc, disclosed) `class_id`
stripped → structural fail and pipeline FAIL (PASS). `K3` canonical F2a unaffected (PASS).
`K4` byte-identity: exactly one line changed per candidate (PASS). `K5` post-run canonical-C0
re-run reproduces the baseline FAIL and union 31/31, no sandbox contamination (PASS).

`K2` **(pre-registered, MISSED — recorded, not hidden):** corrupting
`f0_binding.consistency_evidence_sha256` did **not** make the pipeline fail (`rc 0 / PASS`).
Disposition: that is an instrument-coverage fact about the two-stage criterion, not a candidate
defect. The corrupted hash is caught by a direct declared-vs-measured re-derivation
(`deadbeef…` vs measured `9e335e9ba1bf…`), i.e. by a **different** instrument. Consequence for
reviewers: **pipeline PASS must not be read as evidence-binding-clean** (consistent with
`HF-W062-REV13-02`, the pinned acceptance report records no base hash and does not cover C06).
Under the pre-registered decision rule — applied unchanged — this declared control miss keeps the
run verdict at `PARTIAL` even though both candidates pass every candidate-level check.

## Recommendation to the owner (astra-lead-formulation)

**CAND-B is the minimum-risk repair**: metadata-only, normative formal sentence untouched, rev11
precedent. **CAND-A is equally pipeline-valid** and preserves the pair-binder documentation in the
ordered prefix at the cost of restating the formal sentence in equivalent product notation.
Either candidate removes the need to adopt worker-006's `FORM-R03-V2` tool change for this blocker;
that adoption decision remains separate.

Publishing F1 rev14 requires the owner/controller cascade: apply one candidate → rebind
`schemas/f1_falsifier_tests.jsonl` (separate open owner dependency **L-FORM-04**, worker-031's
validated patch) → publish FROZEN rev30 → independent r3 re-review at the new bytes.

## Falsifier

Show a run of the frozen pipeline at a candidate's bytes that does not reach rc 0 / PASS /
union 31/31; show any parsed path other than the declared one differing from canonical; show the
frozen detector bytes differing from the FROZEN rev29 pin; or show a canonical pin moving between
T0 and T1. Any of these voids the corresponding candidate row or the whole table.

## Authority note

Worker evidence only. **No canonical file was edited**; the pipeline ran only inside
`./sandbox/`. No node status, `validation_status=passed` or gate verdict is set. The F1 schema is
owned by `astra-lead-formulation`.

## Layout

| path | what |
|---|---|
| `PREREGISTRATION.json` | predeclared checks P1–P10, controls K1–K5, decision/stop rules, written before any run |
| `run_r03_repair_candidate.py` | deterministic harness (rebuilds sandbox, rebases corpus, runs baseline + candidates + controls) |
| `report.json` | machine report: every check/control with expected/observed, run stdout, T0/T1 pins |
| `controls.json` | control table |
| `candidates/CAND-{A,B}_af_wcc_vacuum.yaml` | full candidate schema bytes |
| `diffs/CAND-{A,B}.diff` | unified diffs vs canonical |
| `controls/*.yaml` | planted control fixtures (K1, K2, K2b) |
| `evidence/acceptance_*.json` | frozen pipeline report snapshot per run |
| `CHECKPOINT.json` | worker checkpoint with measured artifact hashes |
