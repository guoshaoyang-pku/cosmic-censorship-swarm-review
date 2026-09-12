# W097-F2B-REV13-INDEP-REVIEW-01 — pre-registration

Written **before** `check_f2b_rev13.py` was executed. All pins below were measured by hand
(`sha256sum`) before the instrument was run; the instrument re-measures them itself and fails
closed on drift.

- **task_id**: `W097-F2B-REV13-INDEP-REVIEW-01`
- **worker / slot**: `worker-097` (fleet instance 2026-09-12T00:56:09+08:00)
- **node**: `F2b`; **class**: `AF-SCC-C0-VAC-GEN`; **gate**: `G-FORM`
- **reviewed artifact**: `schemas/af_scc_c0_vacuum.yaml` @
  `b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c` (rev 13)
- **mirror**: `artifacts/formulation/schemas/af_scc_c0_vacuum.yaml` @ same sha256
- **declared F0 contract**: `research_map/formulation_taxonomy.yaml` @
  `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3`
- **class-contract supplement**: `artifacts/formulation/formulation_taxonomy.yaml` @
  `d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1`
- **freeze manifest**: `artifacts/formulation/FROZEN.json` @
  `815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0` (rev 29)
- **alias registry**: `artifacts/formulation/VOCAB_ALIASES.json` @ `46cd9f1eb534…`
- **consistency evidence**: `artifacts/formulation/evidence/taxonomy_consistency.json` @
  `9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b`

## Why this task

`G-FORM` needs hash-bound verdicts at the three rev-13 class hashes. The controller audit at
`2026-09-12T00:55:13` records F1 `0`, F2a `0`, F2b `0` distinct accepts at those hashes. By
01:00 F2a has ≥2 rev-13 accepts; F1 has rev-13 revise verdicts; **F2b at `b2ab6acb2bbe` has no
hash-bound review verdict at all** (the only reviews on record bind to the superseded rev-12
`55d0a1ea9bda`). This task supplies the first independent, at-pin, full-schema verdict for F2b.

## Method (fixed before measurement)

A from-scratch, stdlib+PyYAML, read-only instrument (`check_f2b_rev13.py`) runs ten hard checks
(H1–H10) and four advisory observations (A1–A4) against the pinned bytes, then eight controls
(K1–K8). It writes only inside this artifact directory. It does **not** import
`research_map/class_separation.py`, `artifacts/formulation/tools/check_class_schema.py`,
`check_taxonomy_consistency.py`, or any other agent's checker, and it reads no other reviewer's
F2b verdict text. Prior F2b hard-failure *headlines* were visible in the aggregate outbox stream
before this pre-registration; the findings below are re-derived from the primary bytes and the
instrument is independent.

Hard checks (any failure ⇒ verdict `revise`):

| id | check |
|---|---|
| H1 | structural integrity: required top-level keys; duplicate-key detection; `revision == len(revision_history)`; history index/at/unused well-formed; `revised_at` not earlier than the last history entry |
| H2 | class identity: `class_components` reproduce `class_id`; `regularity_token=C0`, `family=SCC`, `matter=VAC`, `asymptotics=AF`, `genericity=GEN` |
| H3 | internal containment-direction consistency: every statement relating C0 and C2 extension sets must have C2 ⊂ C0 (C0 strongest); inverted-direction patterns are collected with their YAML paths |
| H4 | declared-F0 binding: `declared_f0_sha256` == live taxonomy; consistency-evidence path exists and hashes to `consistency_evidence_sha256`; FROZEN rev-29 pins all of schema, mirror, taxonomy, supplement, evidence, alias registry at the live hashes |
| H5 | pointer resolution: `class_contract_pointer` resolves in `classes`, `class_contract_supplement_pointer` resolves in `class_contracts` |
| H6 | quantifier well-typedness: `ordered` binders/domains are exactly `D0–D3`; `formal` carries the same quantifier sequence; negation is the dual (`exists r` / non-meager) and NNF agrees; `order_matters=true` |
| H7 | vocabulary conformance via `VOCAB_ALIASES.json`: `conclusion_type`, `genericity.kind`, and all five axes map to allowed F0 `field_vocabulary` tokens; an unknown token fails |
| H8 | canonical/mirror byte identity |
| H9 | sibling disjointness is mutual (F2a declares F2b) and the taxonomy `disjointness` pair exists |
| H10 | `review_status` well-formed: gate `G-FORM`, reviewer requests non-empty |

Advisory observations: A1 alias tokens used in a canonical artifact (policy: canonical token
first); A2 consistency evidence is a hash-free boolean (no input hashes/checked_at inside the
file); A3 F0 contract text quantifies over "(s,delta)" while D0 is a tagged union including the
`smooth` branch; A4 `conclusion.known_obstruction` embeds a YAML fragment in a string.

Controls: K1 repair-responsiveness of H3 (invert the suspected wording ⇒ H3 must pass; restore
⇒ fail); K2 H4 on a zeroed declared hash; K3 H7 on an unknown token; K4 H1 on a deleted required
key; K5 H1 duplicate-key detector on injected duplicate `revision:`; K6 H8 on an in-memory
diverged mirror; K7 determinism (two runs, identical canonical report); K8 fail-closed behaviour
on a structurally empty document (must not return `accept`, must not raise).

Verdict/score rule: no hard failure ⇒ `accept`, 4.5. One hard failure ⇒ `revise`, 3.5. Two ⇒
3.0. Three or more ⇒ 2.5. An internal checker error ⇒ `inconclusive`, no score above 2.0.

## Predictions (registered before the run)

- **P1**: H3 **fails** with exactly one inverted statement, at
  `implication_ledger.forbidden_transfers[0].reason`: "C2 is a strictly larger extension class",
  contradicting `extension_class_containment` ("E_C0 contains … E_C2") in the same file and F2a
  line 148. The row's *conclusion* ("C2-inextendibility is strictly weaker") is correct; the
  premise is inverted.
- **P2**: H1, H2, H4, H5, H6, H9, H10 pass at the pinned bytes. H7 passes **only because**
  `scc_c0_future_inextendibility` and `residual_comeager` are registered aliases — I initially
  read them as vocabulary violations and the alias registry is the control that refuted that.
- **P3**: H8 passes (canonical == mirror).
- **P4**: A1–A4 all fire; none is hard.
- **P5**: K1–K8 all pass.
- **P6**: overall verdict `revise`, score **3.5**, one hard failure.

If P1 is wrong in either direction — no inverted statement, or more than one — the instrument's
H3 statement census in `report.json` is the record and the verdict rule is applied mechanically.

## Falsifier

A re-run of `check_f2b_rev13.py` against the same pinned bytes and the same pin set that returns
a different H3 census or a different overall verdict; a mutation control that the instrument
fails to catch; or a second reader who shows the line-246 premise is not inverted (i.e. that
"C2 is a strictly larger extension class" is consistent with
`implication_ledger.extension_class_containment`). A later revision hash is a new measurement,
not a falsifier of this one.

## Authority / non-claims

Worker verdict only. It does **not** set `status=done`, `validation_status=passed`, a node
verdict, or any gate verdict; it does not write to `schemas/`, `research_map/`,
`artifacts/formulation/`, `runtime/state/` (other than this worker's own checkpoint file), or
`comms/outbox/` other than `worker-097.jsonl`. No mathematical or physical correctness is
decided; the review is mechanical class-contract conformance at one pinned revision. No claim
that fixing H3 would exhaust F2b's obligations.
