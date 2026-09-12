# W084-R03V2-SCOPE-INDEP-01 — independent adjudication of W006-R03-SCOPE-01

**Verdict: accept.** One bounded class-bound task, executed read-only against the
published W006-R03-SCOPE-01 bytes. No canonical artifact, fixture, tool or
published report was written.

## What was verified

Subject: `artifacts/worker-06/r03scope/` (report `e81f7818d026`, raw
`33ab1e03e690`, manifest `40a457905eee`, preregistration `f376d7124cfb`).

- **Pins**: 14 pinned files (4 candidate tools, 3 live canonicals, 5 published
  artifacts + 2 more) hashed before and after the run — 14/14 stable.
- **Reproduction**: 88 cells (4 candidates × 19 fixtures + 3 canonicals)
  re-executed from preserved bytes with an independent subprocess driver that
  imports no worker-006 code. 88/88 agree with the published raw verdicts on
  returncode, verdict, failed rules and document hash.
- **Determinism**: all 88 cells re-executed a second time — 0 field differences.
- **Labels**: all 19 fixture labels re-derived from the frozen binder semantics
  before running (6 pos / 8 neg / 4 edge / 1 byte-identical control); 19/19 agree
  with the manifest.
- **Frozen oracle**: "accept iff the literal `(q,t0)` occurs in
  `quantifiers.formal`" predicts the measured frozen verdict on 19/19 fixtures,
  confirming the frozen rule's FP/FN pattern is literal matching.
- **Mutation target**: every mutant differs from its declared base only at
  `quantifiers.formal`; the control has zero diff.
- **Canonical control**: frozen rejects WCC on exactly R03 and accepts C2/C0;
  all three repair candidates accept all three live canonicals with no failed rule.
- **Declared matrix**: 76/76 declared expectations reproduce, 0 deviations.

## Confirmed headline

| candidate | FP | FN | scope-safe |
|---|---|---|---|
| frozen `c79d8ab8440a` | 4 | 2 | no |
| `cand_r03v2` `e41a4b23a840` | 0 | 0 | yes |
| `cand_004` `645eb16a0060` | 0 | 7 | no |
| `cand_E3` `3f69bc1eb27a` | 0 | 8 | no |

## Findings

- **F-01 (info)** — exact reproduction, twice; no non-R03 failed rule.
- **F-02 (info)** — labels independently confirmed; frozen FP/FN mechanics are
  literal-match mechanics.
- **F-03 (minor)** — `cand_r03v2` rejects **4/4** edge probes (comma-coordinated,
  long span, split/nested quantifiers, brace group), not the two named in the
  claim. All four were manifest-declared `v2:reject`, so the matrix has zero
  deviations, but the summary sentence understates the edge residue.
- **F-04 (info)** — scope limit: one class, one slot, one rule family, 14 scored
  cells. The author's later-held-out-corpus falsifier stays open.
- **F-05 (info)** — stage-B is unpinned in FROZEN rev29; adoption must pin tool
  `e41a4b23a840` and rule module `c572a033c054` in the same revision.

## Falsifier outcome

None of the pre-registered falsifiers triggered.

## Limits

Same durable worker id built FORM-HELDOUT-10 (no held-out byte is read here);
rules are executed, not re-implemented; this sets no gate verdict, completes no
node, and recommends no adoption.

## Evidence

`PREREGISTRATION.json#a9a4061e24e2`, `reproduction.json#bf779d809eaf`,
`determinism.json#b07ef7bedc4f`, `raw/`, `raw_pass2/`.
