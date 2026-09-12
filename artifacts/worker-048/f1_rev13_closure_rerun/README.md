# W48-F1-REV13-CLOSURE-RERUN-01 — pre-registered F1 closure re-run at rev13

Worker: `worker-048` · Class: `AF-WCC-VAC-GEN` · Node: `F1` · Gate: `G-FORM`
Snapshots: run 1 `2026-09-12T00:59:30+08:00`, run 2 `2026-09-12T01:00:40+08:00` (schema
`schemas/af_wcc_vacuum.yaml` rev 13 = `d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d`).

**Verdict: `revise`** — 1 blocking residual under the frozen C5 criterion (`complete(I+_D)` /
`AF_{I+}` machine-readable binding), 1 criterion (`C4`) superseded by the controller's REC-3
companion-pair disposition, 2 advisories. This is a **closure-criteria** re-run, not a full
semantic schema review; `counts_as_full_schema_verdict = false`. It is not a gate verdict and
does not move the node.

## Why this run exists

`W48-F1-CLOSURE-PREFLIGHT-01` (snapshot 00:27:38, F1 `9a8bd4c96800`) found four blocking defects
(C1 duplicate top-level keys, C2 future-dated timestamps, C5 undefined conclusion symbols,
C6 whole-curve vs TAIL quantifier) and pre-registered its own falsifier: these findings are
falsified by a re-freeze, and *"a later write to the live files is not a falsifier — it is a new
revision to re-run against."* Rev 13 (`d9cebb9404b2`, published 00:53:40 under FROZEN rev29
`815e08079aef`) is that new revision. This run re-executes the same instrument, with the same six
mutation controls, at the new bytes. It answers one question the accepting/revising reviewers did
not: **did rev13 close the specific defects the earlier closure preflight made blocking?**

## Result at rev13 (run1; run2 identical on every check and control)

| id | closure item | at 9a8bd4c96800 (rev?) | at d9cebb9404b2 (rev13) | delta |
|---|---|---|---|---|
| C1 | (a) duplicate keys | FAIL | **PASS** | closed — unique top-level keys; safe_load and duplicate-rejecting loader agree |
| C2 | (a) future timestamps | FAIL | **PASS** | closed — `revised_at` 00:53:20, `checked_at` 00:53:41, mtime 00:53:40.999; nothing ahead of write |
| C3 | (b) contract pointer | FAIL (contested) | **PASS** | closed by repointing to `research_map/formulation_taxonomy.yaml#classes.AF-WCC-VAC-GEN`; the supplement-side `class_contracts.*` fragment is now the dangling side (expected under REC-3, advisory only) |
| C4 | publication | UNRESOLVED | **UNRESOLVED (criterion superseded)** | controller REC-3 rules the F0 pair a *companion* pair where byte-identity is not a publication requirement; the checker still requires byte-identity, so this row is a stale criterion, not a live defect (see advisory A-W48-2) |
| C5 | (c) symbols defined | FAIL | **FAIL (narrowed)** | `AF_{I+}` now carries `i_plus.predicate_abbreviation` (a binding the frozen C5 helper does not recognise); `complete` has only prose `i_plus.completeness_definition` and no symbol→definition binding of any recognised kind |
| C6 | (d) quantifier predicate | FAIL | **PASS** | closed — `quantifiers.formal` now carries the TAIL predicate; tail/whole-curve equivalence is stated in `visibility.definition` |
| C7 | binding | PASS | **PASS** | `declared_f0_sha256` = measured canonical `0abb9ed8a961` |
| C8 | gate vocabulary | PASS | **PASS** | class id, conclusion type and vocabulary bound to the canonical F0 class |
| C9 | metadata (advisory) | FAIL | **FAIL** | `review_status.independent_reviewers` still `[]` while hash-bound F1 reviews exist on disk |

Run 2 reproduced every verdict and every control; the only moving part is the live `reviews/`
corpus (C9 saw 3 hash-bound reviewers at run 1 and 5 at run 2). Cross-run equality is recorded in
`report_run2.json`.

## Primary residual (blocking under the frozen criterion)

`check_f1_closure.py` C5 requires every call-style symbol in `conclusion.statement_formal`
(`AF_{I+}`, `complete`, `visible_singularity_from_I_plus`) to have a machine-readable definition,
recognising `symbol_definitions` entries and leaves named `predicate_name` / `symbol` /
`symbol_name` / `name`. At rev13:

- `visible_singularity_from_I_plus` — bound via `visibility.predicate_name` → recognised.
- `AF_{I+}` — bound via `i_plus.predicate_abbreviation` (a string that names the symbol and its
  definiendum) → **not recognised by the frozen helper's key whitelist**.
- `complete(I+_D)` — defined in prose by `i_plus.completeness_definition` (plus
  `completeness_definition_status`), but with **no symbol binding of any recognised kind**.

So the machine-measured residual is narrower than at rev12 but still real: one symbol has a
binding the criterion cannot see, and one has no binding at all. Either a one-line
`symbol_definitions: {"AF_{I+}": ..., complete: ...}` in a rev14, or an adjudicated extension of
the C5 criterion to accept `predicate_abbreviation`/`completeness_definition`, closes this row.
That judgement belongs to the audit lead; this artifact only reports the measurement.

## Advisories (non-blocking, each falsifiable)

- **A-W48-1 — instrument defect found by the re-run.** Checker `b8fd03f8f983` crashes with
  `TypeError: unhashable type: 'dict'` at `check_c9_review_status` on any review file whose
  `reviewed_sha256` is a path→hash map (worker-018, worker-019). The rev13 corpus contains such
  files, so the *original* checker cannot complete at rev13. Reproduced in
  `checker_v1_crash.json`; the hardened copy `check_f1_closure_rev13.py` (`38bdaaee`) flattens
  dict/list/str hash fields and is byte-diffed in `checker_diff.patch`.
- **A-W48-2 — C4 criterion is stale against controller policy.** `publication_status`
  (checked 00:55:13) and REC-3 (`astra-lifecycle-04-decisions.json`, ruling 0) classify
  `research_map/formulation_taxonomy.yaml` + `artifacts/formulation/formulation_taxonomy.yaml` as
  a companion pair and state byte-identity is *not* a publication requirement, while
  `artifacts/formulation/FROZEN.json#f0_mirror_adjudication_request.status` still reads
  `disposition-recorded-pending-controller-adjudication`. The controller adjudication is recorded;
  the FROZEN request field is stale metadata and should be refreshed in the next authorised
  revision rather than re-litigated as a blocking publication defect.
- **A-W48-3 — binding-field format gap in the controller's own scan.**
  `astra_lifecycle._explicit_pins` reads only *string-valued* `artifact_sha256` /
  `reviewed_sha256` / `sha256` / `cited_sha256` (and `target.sha256`), so dict-valued bindings —
  e.g. `reviews/F1-review-worker-018.json`, `reviews/W019-rev13-preflight-review.json` — are
  invisible to `review_coverage`. At the probe instant this hid 2 hash-bound F1 revises (not
  accepts, so `two_distinct_accepts` is unaffected), but the census itself is under-counted.

## Review-corpus measurement at the probe instant (advisory, not a gate verdict)

`review_coverage_probe.py` re-runs the controller's own `astra_lifecycle.review_coverage` with the
rev13 hashes (probe time `2026-09-12T01:01:12+08:00`, output `review_coverage_probe.json`):

| target | distinct full accepts | two-distinct-accepts | verdicts found |
|---|---|---|---|
| F1 `d9cebb9404b2` | worker-045, worker-075, worker-085 | **true** | 3 accept, 2 revise (+1 scoped revise) |
| F2a `e9a27996dfd3` | worker-017, worker-072, worker-075 | **true** | 3 accept, 1 revise |
| F2b `b2ab6acb2bbe` | — | **false** | 1 revise |

The map's `controller_gate_audit` at 00:55:13 still reads `F1/F2a/F2b [0 accepts]`; the corpus
changed within ~6 minutes. The corpus is live, so these counts are bound to the probe instant and
carry no accept/revise adjudication — that is the audit lead's card (`astra-life05-verify-gform-r3`).

## Controls (6/6 pass at rev13, identical in both runs)

| control | mutation | target | expected | observed |
|---|---|---|---|---|
| ctl-C1 | dedupe top-level keys | C1 | PASS | PASS |
| ctl-C2 | stamp timestamps now−5 min | C2 | PASS | PASS |
| ctl-C3 | canonical pointer fragment | C3 | PASS | PASS |
| ctl-C5 | add `symbol_definitions` | C5 | PASS | PASS |
| ctl-C6 | tail-form containments | C6 | PASS | PASS |
| ctl-C7 | corrupt declared F0 hash | C7 | FAIL | FAIL |

## Falsifiers

At the bytes recorded in `inputs_manifest.json` (`drift_detected=false` across the run):

- (a) any PASS check here that fails on an independent re-implementation reading those bytes;
- (b) any FAIL check here that passes on an independent re-implementation, or C5 passing once
  `symbol_definitions` is added or the criterion's recognised binding keys include
  `predicate_abbreviation` and `completeness_definition`;
- (c) any control that does not flip as declared;
- (d) a controller disposition already recorded at snapshot time that closes C4 otherwise than
  REC-3 (this would make A-W48-2 stale, not the measurement);
- (e) a review-coverage probe at the same instant returning different counts from the files then
  on disk.

A later write to the live files is not a falsifier — it is a new revision to re-run against.

## Reproduce

```bash
python3 artifacts/worker-048/f1_rev13_closure_rerun/check_f1_closure_rev13.py \
  --schema schemas/af_wcc_vacuum.yaml \
  --expect-sha256 d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d \
  --now 2026-09-12T00:59:30+08:00 --controls \
  --out artifacts/worker-048/f1_rev13_closure_rerun/report.json
python3 artifacts/worker-048/f1_rev13_closure_rerun/review_coverage_probe.py
```

## Not claimed

No gate verdict, no node transition, no canonical write, no acceptance of any schema semantics.
Worker events cannot set `status=done`, `validation_status=passed` or a gate verdict.
