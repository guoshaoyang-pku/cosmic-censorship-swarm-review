# W054-A0-VOCAB-RECONCILE-01 — A0 rubric vocabulary reconciliation against the frozen revision

worker-054 · node **A0** · gate **G-AUDIT** · classes `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`,
`AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH` · 2026-09-12T00:45+08:00

**Authority: read-only worker measurement.** No canonical file was written, no gate verdict
was issued, no node status was changed. The patch below is a *proposal* applied only to a byte
copy in this directory.

## Why this task

Three independent verdicts on A0 (`deepseek-flash-21`, `deepseek-flash-22`,
`astra-lead-audit-r2`, all at `evaluation_rubric.yaml` sha256 `d748a9e3574e…`) hold the
rubric at **revise** for a vocabulary disconnect: A0's machine checks name tokens and fields
that do not exist in the frozen artifacts they exist to gate — so a literal G-FORM pass
rejects all three frozen class schemas. The reviewers diagnosed the disconnect; this task
censors it exhaustively, reconciles it against the frozen canonical vocabulary, and emits a
minimal line-anchored repair proposal with controls.

## Pinned revision (all nine hashes verified pre- and post-run; zero drift)

| artifact | sha256 |
|---|---|
| `evaluation_rubric.yaml` (A0, revise target) | `d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885` |
| `research_map/formulation_taxonomy.yaml` (F0 rev5) | `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3` |
| `schemas/af_wcc_vacuum.yaml` (F1 rev12) | `cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3` |
| `schemas/af_scc_c2_vacuum.yaml` (F2a rev12) | `5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce` |
| `schemas/af_scc_c0_vacuum.yaml` (F2b rev12) | `55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6` |
| `artifacts/formulation/VOCAB_ALIASES.json` (registry) | `46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba` |
| `ledger/theorems.jsonl` (L0) | `a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28` |
| `ledger/citation_audit.csv` (L1) | `315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9` |
| `artifacts/formulation/FROZEN.json` (rev28) | `2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1` |

Canonical vocabulary is read from `VOCAB_ALIASES.json` and the frozen field/value sets of
L0/L1; it is not hard-coded in the harness.

## Census result — 13 unmet vocabulary slots on the pinned A0

| slot | pinned value | frozen truth |
|---|---|---|
| `conclusion_primary` ×4 classes | `future_asymptotic_predictability`, `C2_inextendibility_of_maximal_development`, `C0_inextendibility_of_maximal_development` | unregistered tokens; canonical are `weak_cosmic_censorship`, `scc_c2_future_inextendibility`, `scc_c0_future_inextendibility` |
| `conclusion_implied::AF-SCC-C0-VAC-GEN` | `C2_inextendibility_of_maximal_development` | must be the canonical C2 token |
| genericity enum (G-FORM:128) | `comeager`, `open_dense` (alias-only), `codim_ge_1`, `non_generic_excluded` (unregistered) | registry canonical: `residual_comeager`, `open_dense_escape`, `full_measure`, `none` |
| genericity coverage | `residual_comeager` absent from the enum (only its alias `comeager`) | all three schema classes declare `genericity.kind = residual_comeager` |
| L0/L1 field names | `resolution_status` (A0:28,138,184), `quantity_check` (A0:30,142,190) | 0 occurrences in frozen L0/L1; L1 uses `status` ∈ {`verified-primary`,`verified-api`} with `verdict = verified`, L0 uses `content_status` |
| `metrics.citation_support` | weights `verified_primary=1.0, verified_secondary=0.5, partial=0.25, unresolved=0.0, contradicted=-1.0` | no frozen field carries this value set; not computable as written |

## Proposal — 12 line-anchored edits (2 flagged owner-decision)

`proposed_a0_vocab_edits.json` holds every edit as `{line, old, new, kind, owner_decision}`.
The patched copy `evaluation_rubric.patched.proposal.yaml` differs from the pinned A0 only on
the declared lines (control C6). Owner-decision edits: (a) the scalar class's pending
genericity rule, (b) the quantity-record substitute for the `quantity_check` predicate, since
no frozen field is a drop-in.

## Controls (9/9 pass)

C0 pins (9/9 match, no drift) · C1 pinned A0 parses · C2 pinned A0 is non-zero-unmet (13) ·
C3 patched copy is **0-unmet** under the same census · C4 patched copy parses as YAML ·
C5 wrong-class decoy (`scc_c0_future_inextendibility` in the C2 slot) is still flagged ·
C6 diff confined to declared lines · C7 no canonical hash changed across the run ·
C8 schemas and taxonomy agree through the alias registry (3/3 classes).

## Advisory (formulation-owned, reported not patched)

`AF-WCC-SCALAR-SPH` has `axes.genericity_kind = unresolved` in taxonomy rev5, and `unresolved`
is **not a registered token** in `VOCAB_ALIASES.json`. No machine check can admit that class's
genericity until the registry owner rules (register `unresolved`, or bind the class to a
conservative kind). Also unregistered today: `codim_ge_1`, `non_generic_excluded`,
`future_asymptotic_predictability`, `C2_inextendibility_of_maximal_development`,
`C0_inextendibility_of_maximal_development`.

## Falsifier

Re-measure the nine pins and re-run `reconcile.py` against the pinned bytes. This proposal is
void if (a) any pin differs; (b) any declared edit's expected line text is absent (drift —
fail-closed); (c) the patched copy is not zero-unmet under the same census that is non-zero on
the pinned copy; (d) the wrong-class decoy is not flagged; (e) any canonical file hash changes
during the run; or (f) the patched copy fails the A0 owner's own self-test.

## Reproduction

```bash
python3 artifacts/worker-054/a0_vocab_reconcile/reconcile.py   # exits 0 iff 9/9 controls pass
```

Artifact hashes (this bundle): `report.json` `5abe3a869060` · `proposed_a0_vocab_edits.json`
`dc68842d97f3` · `evaluation_rubric.patched.proposal.yaml` `d56390d405d3` · `reconcile.py`
`ec2c9f31afb5`.
