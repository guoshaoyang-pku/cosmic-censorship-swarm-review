# W055-A0-RUBRIC-01 — independent A0 conformance verdict (class-bound, G-AUDIT)

Worker `worker-055` (bounded instance, 2026-09-12). Node **A0**; gate **G-AUDIT**;
classes `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH`.

**Authority: advisory worker verdict only.** No gate verdict, node status, or
`validation_status` is set here. Per `ASTRA_HANDOFF.md`, only the controller and group
leads move gates.

## Why this task

`reviews/A1-rebind-coverage.json` records for A0:

- `a0_conformance.universal_scalar_score_token_present: true` — a structural spot check
  with the note *"the binding A0 question is the missing independent verdict"*;
- `blockers` for F0/F1/F2a/F2b, and `A0` is one of the two G-AUDIT targets
  ("evaluation_rubric.yaml exists without a universal scalar score").

The spot check flags the token `universal_scalar_score`; the open question is whether it
is a **use** (rubric violation) or a **mention** (declared prohibition). This bundle
answers that with a machine-checkable adjudicator plus five staged mutation controls, and
then gives an independent full verdict on `evaluation_rubric.yaml`.

## Pins (measured; drift voids the verdict)

| artifact | sha256 |
|---|---|
| `evaluation_rubric.yaml` (canonical, live, snapshot, controller registry) | `d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885` |
| `research_map/formulation_taxonomy.yaml` (F0 rev5) | `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3` |
| `schemas/af_wcc_vacuum.yaml` (F1 rev12) | `cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3` |
| `schemas/af_scc_c2_vacuum.yaml` (F2a rev12) | `5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce` |
| `schemas/af_scc_c0_vacuum.yaml` (F2b rev12) | `55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6` |

## Result

**Verdict: `revise`, score 3.0.** One blocking hard failure, two minor advisory findings.

### Resolved: the universal-scalar-score question (G-AUDIT criterion)

`PASS`. Zero aggregate-score **uses** were found. The only occurrences of the flagged
token are prohibition **mentions** at `evaluation_rubric.yaml:10-13`
(`no_universal_scalar_score: "… no single number … never averaged into one score"`) and the
promotion rule (`:289`, "only G-* verdicts promote … consensus is not evidence"). The
audit lead's `universal_scalar_score_token_present: true` is therefore a metalinguistic
false positive of the structural token scan — the same pattern as CF-16.

Mutation controls prove the adjudicator discriminates:

| mutant | injected | expected caught | observed |
|---|---|---|---|
| M0 | none (byte copy) | — | clean (0 violations) |
| M1 | `universal_score` + numeric promotion rule | scalar, promotion | caught |
| M2 | `metrics.overall_score` = mean across task types | scalar | caught |
| M3 | `review_protocol` deleted | promotion | caught |
| M4 | class id merged to `AF-SCC-C2-C0-VAC-GEN` | classes | caught |
| M5 | `forbidden_evidence` emptied | classes | caught |

### Blocking: vocabulary disconnect (HF-055-A0-1)

Independently reproduced from primary bytes: A0's G-FORM vocabulary does not cover the
frozen schemas it exists to gate.

| schema | `genericity.kind` | in A0 enum `{comeager, full_measure, open_dense, codim_ge_1, non_generic_excluded}`? | `conclusion_type` | in that class' A0 `conclusion_primary`/`conclusion_implied`? |
|---|---|---|---|---|
| F1 | `residual_comeager` | **no** | `weak_cosmic_censorship` | **no** |
| F2a | `residual_comeager` | **no** | `scc_c2_future_inextendibility` | **no** |
| F2b | `residual_comeager` | **no** | `scc_c0_future_inextendibility` | **no** |

A literal G-FORM / HF-02 reading therefore rejects all three frozen schemas. This
reproduces the independent flash-22 finding with a separate instrument and adds the
per-class machine table.

### Advisory (non-blocking)

- `ADV-055-A0-1`: `gates[G-AUDIT]` names reviewer-agreement `kappa >= 0.60`, but no kappa
  metric is defined; `metrics` / `review_protocol` use Kish ESS instead (internal
  coherence gap).
- `ADV-055-A0-2`: the mission's progress list includes accepted-claim rate and cost per
  accepted claim; neither appears in `metrics` (`hard_failure_rate` and `information_gain`
  are present).

## Falsifiers

1. **Hash drift** — any change to `evaluation_rubric.yaml` voids this verdict; re-run at
   the new hash.
2. **Scalar clause** — a file at the canonical path promoting/ranking with a single
   aggregate numeric score refutes the scalar PASS.
3. **Vocabulary clause** — a declared alias/mapping at the pinned hash that maps
   `residual_comeager` and the `scc_*` conclusion types into A0's allowed sets refutes
   HF-055-A0-1.
4. **Instrument clause** — any staged mutant escaping its registered expected failing
   check refutes the instrument's discriminating power.

## Reproduce

```bash
python3 artifacts/worker-055/a0_rubric_verdict/check_a0_rubric.py   # exit 0 iff all expectations hold
python3 artifacts/worker-055/a0_rubric_verdict/finalize.py          # manifest + checkpoint + outbox events
```

Read-only on every canonical path; all writes are confined to this bundle's `stage/`,
`snapshot/`, and the state/outbox files named in the checkpoint.
