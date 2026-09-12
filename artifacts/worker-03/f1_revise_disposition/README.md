# F1 revise-finding disposition at the frozen revision

- **task**: `F1-REVISE-DISPOSITION-01` | **actor**: `worker-03` (agent id `deepseek-flash-03`)
- **node / class / gate**: `F1` / `AF-WCC-VAC-GEN` / `G-FORM`
- **target**: `schemas/af_wcc_vacuum.yaml` sha256 `9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503` (schema rev 11, FROZEN rev 25, pin `9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503`)
- **authority**: author-side textual audit. NOT a review verdict, NOT an acceptance, no node/gate authority.
  The agent id that drafted F1 performed it; independent confirmation is required before any gate use.

## Question

The recorded F1 revise verdicts (`reviews/F1-review-16.json`, `F1-review-16-r2.json`,
`F1-review-lead-audit.json`) bind F1 rev2/rev3 (`f55722a7` / `7a3e1f93`). The frozen target is
rev 11 (`9a8bd4c96800`). For every concrete finding in those verdicts, is the cited
defect still present in the frozen bytes?

## Result: 13 resolved / 2 partial / 0 present

Every disposition is derived from a named re-runnable probe over the frozen bytes
(`artifacts/worker-03/f1_revise_disposition/scan_f1_disposition.py`). Residual items a re-review must adjudicate:

| id | verdict | residual (line anchors at the frozen revision) |
|---|---|---|
| F1-16-05 | partially resolved | `future-inextendibility` is still listed BOTH as machine-checkable (l.274) and as a proof obligation (l.275) |
| F1-16-07 | partially resolved, schema provenance stale | the external ambiguity suite IS rebound to the frozen pin (`binding_sha256=9a8bd4c96800`), but `adjudication_queue.provenance` still cites the rev3 worker draft `7a3e1f93` / 16 probes (l.184), and `open_rows` lists 3 rows while the note says "1 open" (l.188-190) |

Resolved highlights: the unverified equivalence is out of the statement and tagged
`claimed equivalence, UNVERIFIED`; the black-hole-region requirement is explicitly excluded from
`non_vacuity` and named a forbidden strengthening; `tier_1`/`tier_2` separate non-meagerness from
the single-datum strengthening; `machine_checkable_steps` and `proof_obligations` are split; the
`acceptance_map`/"pinned" wording, dangling `unresolved_refs`, the slice-completeness
contradiction, and the linter-shaped wording are all gone; `f0_binding` is fresh (declared ==
measured F0 `276009f4f63d`).

## Freeze churn observed while this task ran (evidence, not a blocker)

F1 was republished in place three times in ~3 minutes; two earlier scanner runs are preserved in
drift mode, hash-pinned:

| preserved report | sha256 | pin at scan | measured |
|---|---|---|---|
| `report.rev9-b65fcc0f.void.json` | `071ffc980ae3` | `b65fcc0f` (rev9) | `b65fcc0f` |
| `report.rev10-16128b62.void.json` | `bd53a3cec3bf` | `68392dd8` (rev10) | `16128b62` |

Timeline measured here: `68392dd8` (00:16:22, pinned by FROZEN rev24) -> `16128b62` (00:18:37) ->
`9a8bd4c9` (00:19:14, rev11, pinned by FROZEN rev25). During the window FROZEN rev24 still pinned
`68392dd8`, so a reviewer binding the then-declared "final" hash would have bound a superseded
revision. `leadform-status-0014` documents the three refreeze cycles; FROZEN rev25 now pins the
measured bytes, and this report's `drift_ledger` records the transition.

The dominant remaining G-FORM blocker is process-level: **no independent verdict of record binds
`9a8bd4c96800`** (`review_status.verdict: pending`).

## Falsifiers

- Whole report: re-run the scanner against pin `9a8bd4c96800`. Falsified if any recorded check
  does not reproduce, if the canonical sha256 differs from the pin while a disposition claims
  resolved, or if a `resolved_at_frozen` finding's cited defect is shown present at the frozen bytes.
- F1-16-05: show future-inextendibility listed under only one of the two lists.
- F1-16-07: show the suite's `binding_sha256` differs from the pin, or the schema provenance already
  cites the frozen suite.

## Re-run

```bash
python3 artifacts/worker-03/f1_revise_disposition/scan_f1_disposition.py
```

Tool sha256 `af3ab9e97bcb2d4875088f59572e1435e9411e578f9931e3dba8750f51f5bffe`. Report sha256 `fe350faaa33cf7b67c8b408b2e9ea887fac79bc5e7633097231580a510021ed3`.
