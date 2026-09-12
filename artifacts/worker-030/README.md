# worker-030 — independent full-schema review of F2b (AF-SCC-C0-VAC-GEN)

Bounded class-bound task: an **independent, hash-bound, full-schema review of the canonical
strong-censorship C0 schema** `schemas/af_scc_c0_vacuum.yaml`, node `F2b`, class
`AF-SCC-C0-VAC-GEN`, gate scope `G-FORM` / `G-AUDIT`.

Why this task: `reviews/F2b-softflag-disposition-review.json` (astra-lead-audit, 00:14) disposed
the class-separation soft flags but states explicitly that *"A full-schema independent verdict on
F2b is still required for G-AUDIT; this is a scoped disposition, not that verdict."* The
controller gate audit at 00:17:27 records 0 distinct accept reviewers at the measured canonical
F2b hash. This review is offered as one such independent verdict.

## Files

| file | what |
|---|---|
| `f2b_review_check.py` | deterministic audit instrument (stdlib + PyYAML); exit 0 = no blocking check failed, 1 = blocking failure, 2 = target missing / hash drift vs pin |
| `f2b_binding_audit.json` | raw instrument output for the reviewed revision |
| `README.md` | this file |

Review artifact: `reviews/F2b-review-030.json`. Checkpoint: `runtime/state/w030_checkpoint_1.json`.
Events: `comms/outbox/worker-030.jsonl`.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-030/f2b_review_check.py          # rewrites the audit JSON
```

The instrument **fails closed**: it pins `sha256` of the reviewed revision and exits 2 if the file
has changed, rather than silently reviewing a different revision. It does not import
`research_map/class_separation.py` (that checker belongs to another worker); the class-token scan,
duplicate-key parse and cross-artifact checks are a separate implementation.

## What the instrument checks (36 checks)

- **identity** — measured sha256 + bytes vs pin and `.sha256` sidecar.
- **class binding** — frozen class id and component vector; unknown `AF-*` token scan; every
  `class_id` field inside the frozen four; sibling disjointness both directions vs F2a; WCC sibling
  carries the complementary I+/visibility role; composite `C0/C2` tokens only in forbidding contexts.
- **regularity** — `extension_regularity == C0` exactly, continuous metric, no solution concept,
  `must_not_conflate` covers H2_loc / distributional / C2.
- **quantifiers** — order `forall,exists(comeager),forall,not_exists`; D0–D3 defined; negation
  expressed as non-meagerness of the extendible set.
- **topology / genericity** — 4d, one AF end, `I+ = R x S^2`; extension manifold smooth vs metric
  continuous; comeager in the subspace topology, Baire argument, transfer table, class-change warning.
- **conclusion** — `scc_c0_future_inextendibility`, family SCC; no WCC content in the conclusion
  (asserted context); forbidden strengthenings/weakenings; open-problem status, no theorem inflation.
- **falsifier** — tier 1 refutes this class with an explicit witness and a non-meagerness
  requirement + machine-checkable steps; tier 2 labelled `refutes_strengthening_only`.
- **cross-artifact** — the 6 `l1_ledger_refs` cross-checked (status + class_ids) against
  `ledger/theorems.jsonl` at its measured hash; `f0_binding` declared hash vs measured canonical
  taxonomy, consistency evidence, and the taxonomy's `classes.AF-SCC-C0-VAC-GEN` axes.
- **hygiene** — strict duplicate-key parse, future-dated timestamps, stale hash literals in
  comments, `class_contract_pointer` policy.

## Reviewed revision and result

- reviewed: `schemas/af_scc_c0_vacuum.yaml` rev 11,
  `sha256 1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508`, 33276 bytes.
- 32 PASS, 0 blocking failures, 4 non-blocking findings → verdict recommendation **accept**.
- Cross-artifact pins at measurement: taxonomy `276009f4f63dbf83…`, ledger `ce42d205e7617e3a…`.
- Earlier revision `a2aef5ac7fe3…` was **not** reviewed: the instrument exited 2 on drift when the
  lead published rev 11 at 00:19:14; the review rebinds to rev 11.

## Limitations (non-claims)

- Structural and consistency audit only. It does **not** adjudicate the mathematics/physics of the
  formulation (rubric `human_adjudication_only`), does not verify citations or the ledger content
  beyond status/class-binding fields, and does not re-derive the Kerr obstruction.
- The ledger cross-check is comparison to the ledger's own recorded status, not an independent
  reading of the cited sources.
- One revision only; any further edit voids the verdict by construction.
- This is a worker review, not a gate verdict. No node/gate status is claimed; the controller and
  group leads own `G-FORM`/`G-AUDIT`.

## Falsifier

Any byte change to `schemas/af_scc_c0_vacuum.yaml` (sha256 leaves `1bb78ce9b3572cda`) voids this
review; a revision of `ledger/theorems.jsonl` that changes the status or `class_ids` of D-002,
T-301, T-302, T-305, T-515 or T-528 voids the ledger check; a canonical F0 taxonomy revision that
no longer carries `classes.AF-SCC-C0-VAC-GEN` with `regularity_token: C0` voids the binding check.
