# W087-F0-FULL-REVIEW-03 — independent F0 / G-F0 verdict

**Verdict: `accept`** (score 4.0, advisory worker verdict) of the declared F0 taxonomy at the
pinned sha256

```
research_map/formulation_taxonomy.yaml
sha256 0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3   (rev5, draft_unverified)
```

Task taken from the F0 immediate queue, no card issued. Class-bound to all four frozen class ids
(`AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH`); node `F0`,
gate `G-F0`. This supplies **one** independent full-schema verdict; the gate criterion requires two.

## Why this task, and why it is not duplicative

G-F0 was `pending` at 00:37 with **0 distinct accept reviewers at the current canonical hash**:
the only verdict bound to `0abb9ed8a961` was the lead-audit `revise` (score 3.5, hard failures =
absence of accepts + the canonical/authoring divergence, both non-content items now adjudicated).
The predecessor worker-087 lifecycle delivered targeted closure evidence for B-16F0-1/2/3, not a
full-schema verdict. F1/F2a/F2b were being heavily reviewed by other workers; F0 at the current
hash was the open bottleneck.

## What was checked

`review_f0.py` runs 89 machine checks (84 criterion-level, 5 finding-level) plus 7 controls:

| group | content |
|---|---|
| identity | strict parse (duplicate keys rejected), node/gate, exactly the four frozen ids, unique, `classes` keys match, rubric + corpus-meta + schema `f0_binding` cross-consistency, no variant used as a class, no theorem-status claim |
| structure | per-class label/axes/hypotheses/conclusion/exclusions/test-cases/provenance, hypothesis ids, positive+negative cases |
| vocabulary | axis names, axis values against `field_vocabulary`, `conclusion.type == axes.conclusion_type` |
| guards | G2 regularity token exact; G3 merged-regularity scan of the **entire `classes:` subtree** (0 hits) plus a context-classified raw scan (3 hits, all in prohibition/example/revision text); T1–T3 transfer-rule soundness; G1–G7 present |
| conclusions | conclusion family consistency, comeager binder bound **before** the data quantifier in all four classes, canonical tail predicate in both WCC classes (explicit negation for the scalar class), no assertive set-based visibility predicate |
| disjointness | exactly the six unordered pairs; each pair's named decisive axes are valid and recomputed axis vectors genuinely differ |
| binding | corpus per-row `binding_status`, leak-catalog `taxonomy_ref`, scalar genericity deferral, open cases, schema supplement pin |

Result: **84/84 criterion checks pass, 0 hard failures, 7/7 controls pass** (duplicate-key,
merged-regularity fixture, collapsed-disjointness fixture, pre-rev5 set-based fixture, five-class
fixture, determinism, and a specificity control that the canonical *disowned* set-based mention is
not flagged). A wrong pin exits 2 and writes no report.

## Findings (all non-blocking; full text in `F0-review-087.json`)

| id | finding | owner |
|---|---|---|
| B3 | `AF-WCC-SCALAR-SPH`: `genericity_kind=unresolved` while the conclusion binds a comeager set — declared deferral (H4 unresolved, CG1, Q1, no F-node owns the class) | formulation lead / L1 |
| B4 | 9 corpus cases still `open=true` with no disposition field | formulation lead |
| B5 | no schema pins the class-contract supplement sha256 in `f0_binding` (CF-7 open repair) | formulation lead (`astra-life04-freeze-repair`) |

Two more hygiene findings were raised against the bytes present when the run started and were
**cleared by lead-side repins during the run**, then re-measured:

| id | was | cleared by |
|---|---|---|
| B1 | 36 corpus rows carried stale `binding_status: bound_taxonomy_sha_66bf917bd368` | `schemas/taxonomy_cases.jsonl` rewritten 00:42:36; all 36 rows now `bound_taxonomy_sha_0abb9ed8a961` (#ccf7041bd0ff) |
| B2 | `leak_rule_catalog.json` pinned rev3 `565a6e505188` | catalog rewritten; `taxonomy_ref` now rev5 `0abb9ed8a961` (#ccec815ea61d), declared checker re-run clean |

Recorded inputs (not imported by the instrument): the author-family validator passed
253/0 at the pin; the flash-02 corpus checker verdicts PASS with controls 11/11 after the repin.

## Re-run / falsifier

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-087/f0_full_review/review_f0.py \
  --expect-pin 0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3
# exit 0 accept / 3 revise / 2 drift (no report) / 4 control failure
```

Any critical check flipping to fail, any control failing, or the measured hash drifting voids the
verdict. A reader who exhibits a merged C0/C2 or WCC/SCC class binding, a disjointness pair sharing
all named decisive axis values, an assertive set-based visibility predicate in a WCC conclusion, or
a non-frozen class id used as a class refutes the corresponding PASS.

## Scope limits

Worker verdict only: it cannot set node status, `validation_status=passed`, or a gate verdict, and
G-F0 still needs two independent accepts. It binds only the declared taxonomy sha256 above; the
class-contract supplement is not reviewed, and no mathematical or citation correctness is
adjudicated.
