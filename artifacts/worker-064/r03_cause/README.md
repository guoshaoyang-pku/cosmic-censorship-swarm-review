# W064-R03-CAUSE-01 — root cause, regression provenance and sole-blocker test for the canonical WCC R03 rejection

Bounded class-bound worker task taken by `worker-064` **without an inbox card** (none exists for
this slot). Node **A1** (calibration evidence routing), gate **G-AUDIT**. Classes
`AF-WCC-VAC-GEN` (primary), `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`.

The task is an **independent replication and extension**, not a first report. Two workers had
already identified the R03 blocker minutes earlier:

- `w080-sr-20260912T004243-blocker-f1r03` (worker-080): after the control rebase, SCT-K03
  (canonical F1) still fails R03; Probe B calls it lexical and shows an equivalent D5-relative
  rewrite clears R03.
- `w16-R03-ADJ-01` (worker-16): independent adjudication; one-clause literal rendering (V1)
  accepted; a variable-wise R03 tool patch accepts the frozen bytes and still rejects an unbound
  control; Options A (amend the tool) / B (edit F1, new hash + re-review).
- `W064-SEMCT-REBASE-01` and `W004-SEMCT-CONTROL-REBASE-01`: the control-rebase and pin-refresh
  basis this audit re-derives independently.

What this audit adds: (i) the rev11→rev12 **regression provenance** with pinned rev11 bytes that
pass R03 in both semantic stages; (ii) three schema-side one-clause candidates plus a binder-list
alternative and a tool-relaxation variant, all measured; (iii) an **end-to-end discriminating
suite run** showing R03 is the sole residual blocker once `ADJ-CONTROL-STALENESS` is mechanically
repaired — by either route (schema edit or tool amendment); (iv) a measured record of the
**frozen-bytes churn** that occurred while the task was built.

**No canonical artifact was modified.** Every mutation happens in mirrors under `work/`, and the
harness takes a one-time snapshot (`work/_frozen`) at run start so the run is atomic with respect
to further canonical churn. The canonical suite runner is never executed in place.

## Snapshot (FROZEN rev29; full hashes in `report.json#snapshot`)

| artifact | sha256 (12) |
|---|---|
| `schemas/af_wcc_vacuum.yaml` (F1 rev13) | `d9cebb9404b2` |
| `schemas/af_scc_c2_vacuum.yaml` (F2a rev13) | `e9a27996dfd3` |
| `schemas/af_scc_c0_vacuum.yaml` (F2b rev13) | `b2ab6acb2bbe` |
| `schemas/semantic_contract_tests/manifest.json` | `b2e8bd17892b` |
| `artifacts/formulation/tools/check_class_schema.py` | `000e09e46b2f` |
| `artifacts/worker-06/spec_conformance_audit.py` | `c79d8ab8440a` |
| `artifacts/formulation/rule_spec.json` | `40f9bb9e657b` |
| `artifacts/formulation/KEY_MANIFEST.json` | `014e2d301978` |
| historical rev11 WCC `artifacts/worker-061/f1_independent_verdict/pinned/af_wcc_vacuum.yaml` | `9a8bd4c96800` |

No staged input drifted during the run (`report.json#canonical_drift_at_end` carries only the
informational `FROZEN.json` marker, which moved `3d9e3d77fd87` → `815e08079aef`, still rev29).

## Baseline at the pinned bytes

| schema | structural | semantic baseline | semantic hardened |
|---|---|---|---|
| WCC `d9cebb9404b2` | pass | **reject — R03 only** | **reject — R03 only** |
| C2 `e9a27996dfd3` | pass | accept | accept |
| C0 `b2ab6acb2bbe` | pass | accept | accept |

Exact auditor detail: `binder '(q,t0)' absent from formal sentence`. All other 15 rules pass;
SEM-1/2/3 are the auditor's declared undecidables.

## Root cause

`quantifiers.ordered[5] = {kind: not_exists, binder: "(q,t0)", domain_id: D5}` while
`quantifiers.formal` renders the same quantifier variable-wise:

```
not exists q in I+ and t0 in [0,T) with gamma([t0,T)) subset J^-(q) intersect M.
```

R03 is implemented as a literal substring test (`spec_conformance_audit.py:210-212`): every
declared `binder` string must occur in `formal`. The token `(q,t0)` does not. The **whole**
per-binder table is in `report.json#root_cause.binder_table`: WCC binders 0–4 all match; binder 5
is the only miss. C0/C2 print their tuple binder `(M',g',iota)` literally, so they pass — i.e.
**the frozen corpus is not uniformly self-presenting**, and the readability of R03 depends on that
convention.

`rule_spec.json#R03` says `quantifiers.formal` is "a single sentence using those binders" without
stating whether a composite binder must be printed literally or may be used variable-wise.
Therefore:

- under a **variable-wise** reading the sentence conforms (both `q` and `t0` are bound in the
  clause, D5 resolves and defines the pair domain) → the rejection is a tool-side literal-match
  false positive (the reading taken by worker-080 and worker-16);
- under a **literal** reading the schema is non-conforming to R03 as implemented.

This audit does not re-adjudicate that choice. It measures the inconsistency that makes the choice
load-bearing, and verifies both resolution routes end-to-end.

## Regression provenance (rev11 → rev12 → rev13)

Pinned rev11 WCC `9a8bd4c96800` (same auditor hash) is **accepted by both semantic stages, R03
pass**; its binder was `q` and the formal sentence used `q`. The rev11→rev12 quantifier diff
touches `{formal, ordered, domains, negation, negation_normal_form}`: binder `q` → `(q,t0)`,
whole-curve → tail predicate, D5 redefined as pairs. The rev12 mathematics is the intended repair
(F1-review-19 HF-06); only its formal-sentence rendering stopped printing the declared binder, and
the rev13 re-pin (`d9cebb9404b2`, FROZEN rev29) kept that rendering. So R03 is a **rev12
regression that survives rev13**, not a long-standing condition.

## Repair candidates (all in `patch_candidates/`, worker-local)

| candidate | change | structural | semantic baseline | semantic hardened | notes |
|---|---|---|---|---|---|
| **E1a** | formal tail → `not exists (q,t0) in D5 with gamma([t0,T)) subset J^-(q) intersect M.` | pass | accept | accept | only `quantifiers.formal` differs; variant sha `2f51ace6ef74` |
| **E1b** | formal tail → `not exists (q,t0) in I+ x [0,T) with …` | pass | accept | accept | explicit product domain; variant sha `bf1798b57997` |
| **E1c** | formal tail → `not exists (q,t0) with q in I+ and t0 in [0,T) and …` | pass | accept | accept | keeps split clauses and adds the tuple; variant sha `56b324469b2d` |
| **E2** | `ordered[5].binder "(q,t0)" → "q"` | pass | accept | accept | passes, but **drops `t0` from the machine-readable binding**; weaker than E1a/E1b; variant sha `ebb8d6671614` |
| **E3** | worker-local auditor: accept a composite binder if all its comma-separated components occur in `formal` | — | accept | accept | tool change, requires spec-owner adjudication; mutant catch count **unchanged (11/32 baseline, same 11 fixtures)** |

Every E1\* edit is a single-clause replacement; the parsed-YAML check confirms **no key other than
`quantifiers.formal` changes**.

## End-to-end discriminating experiment (full suite, mirrors only)

Controls rebased with the two previously reported mechanical edits (A: `revised_at_unused` nested
under `extensions:`; B: delete the 8-line misplaced `finite_codimension_complement →
residual_comeager` `direction: transfers` row) — the rebased control hashes reproduce the
previously published values exactly (`ce8b15e22722`, `253c28e03c53`, `2399f5752af1`).

| run | basis | exit | valid_for_calibration | controls | conforming canonicals | mutants (struct/base/hard) |
|---|---|---|---|---|---|---|
| S0 | unmodified manifest | 2 | false | 0/3 | 3/3 | 32/11/32 |
| S1 | rebased controls + refreshed pins + **canonical WCC** | 3 | **false** | 3/3 | **2/3 — only `SCT-K03`, R03** | 32/11/32 |
| S2 | S1 + **E1a** WCC | **0** | **true** | 3/3 | 3/3 | 32/11/32 |
| S3 | E1a WCC + rebased control bytes with **stale control pins** | 2 | false | 0/3 | 3/3 | 32/11/32 |
| S4 | rebased controls + refreshed pins + **canonical WCC** + E3 amended auditor | **0** | **true** | 3/3 | 3/3 | 32/11/32 |

Readings:

1. **S1 vs S2**: after the control rebase and pin refresh, R03 on WCC is the *sole* residual
   blocker; a one-clause notation repair turns exit 3/false into exit 0/true with mutant counts
   unchanged.
2. **S4**: the same validity is reachable without touching canonical bytes, via the variable-wise
   R03 implementation (worker-16 Option A); the canonical WCC hash in the results stays
   `d9cebb9404b2`.
3. **S3**: the integrity check still catches stale control pins, so nothing above is achieved by
   weakening pin verification.
4. **S1** also reproduces the routing defect: a rejected conforming canonical leaves
   `validity.blocking_adjudication = []` while `valid_for_calibration=false` (already reported by
   worker-080 and `W064-SEMCT-REBASE-01`).

## Frozen-bytes churn observed (secondary finding)

The live canonical WCC path was observed at three distinct hashes inside ~3 minutes while this
task was being built: `cce9c60146d6` (FROZEN rev28, frozen_at 00:35:08) → `bf0c28fa673e` →
`d9cebb9404b2` (FROZEN rev29, frozen_at 00:55:02; C0/C2 re-pinned to `b2ab6acb2bbe` /
`e9a27996dfd3`). `FROZEN.json` was then rewritten again at 00:57:26 (still rev29, marker hash
`815e0807`). **Any review verdict bound to the rev28 hashes is void.** The harness now snapshots
once and reports `canonical_drift_at_end`. Note: `2f51ace6ef74` is *not* a live hash — it is the
deterministic E1a repair applied to rev13 bytes (candidate E1a).

## Decision-relevant consequence (not a gate verdict)

- **Option B (schema edit, e.g. E1a)**: one clause; suite becomes valid at the new WCC hash; the
  frozen WCC hash changes, so current F1 review verdicts bound to `d9cebb9404b2` are voided and
  re-reviews are required.
- **Option A (amend R03 to variable-wise use)**: canonical bytes untouched; suite becomes valid
  at the frozen hash (S4); no mutant catch is lost; requires rule-spec adjudication.

Both are recorded here as measured routes; the choice belongs to the rule-spec owner / lead.

## Falsifiers (each measured clause)

- WCC accepted by both semantic stages at `d9cebb9404b2`, an additional failing rule, `(q,t0)`
  printed in `formal`, `q`/`t0` not both bound, or D5 unresolved → falsifies the root cause.
- Rev11 WCC `9a8bd4c96800` failing R03 / rejected, or a rev11→rev12 diff not touching
  `formal`/`ordered` → falsifies the regression provenance.
- Any E1\* candidate changing a YAML key other than `quantifiers.formal`, or rejected by a stage;
  E2 failing; E3 losing a mutant catch → falsifies the repair table.
- S0 ≠ exit 2; S1 ≠ exit 3 or a conforming rejection other than `SCT-K03`; S2/S4 ≠ exit 0/valid
  true; S3 ≠ exit 2; mutant counts ≠ 32/11/32 → falsifies the sole-blocker reading.

## Reproduce

```bash
cd <repo>
python3 artifacts/worker-064/r03_cause/w064_r03_cause_audit.py   # exit 0 = all expectations reproduced
python3 artifacts/worker-064/r03_cause/emit_w064_r03.py         # appends events + checkpoint (idempotent)
```

The harness rebuilds every mirror from the one-time pinned snapshot, writes `report.json`, raw
stage outputs under `raw/`, and exits 1 on snapshot drift or 2 if any expectation is falsified.

## Not claimed

No gate verdict, no node completion, no canonical modification, no mathematical verdict beyond
the measured rule text, and no claim of first discovery (see cross-reference above).
