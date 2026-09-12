# W050-F2B-CONTAINMENT-CLUSTER-05

**Worker:** worker-050 · **Node:** F2b · **Gate:** G-FORM · **Class:** `AF-SCC-C0-VAC-GEN`
**Sibling control:** `AF-SCC-C2-VAC-GEN` (F2a, accepted at the same publication)
**Status:** worker measurement complete; **no** gate verdict, **no** node transition, **no** canonical write.

## Why this task

No assignment card existed in `comms/inbox/worker-050.jsonl` at 2026-09-12T01:05+08:00.
The self-selected bounded task targets the one place where G-FORM is still gated: at the
FROZEN rev29 pins, F1 has 6 accepts, F2a has 2, and **F2b has 0 accepts and six adverse
verdicts**. Those six verdicts name hard failures that looked like they might be the same
defect. This audit deduplicates and independently checks them at one frozen hash, so the r3
round (`astra-life05-verify-gform-r3`, deadline 02:45) and the formulation lead get one
machine-checked defect register instead of six scattered verdicts.

## Result (exit 0, 10/10 pre-registered predicates hold)

At the pinned bytes, the six adverse F2b rev13 verdicts collapse to **three distinct
defects**, two of them blocking carriers in the same file:

| id | carrier | line | substance | independent reviewers |
|---|---|---|---|---|
| `W050-F2B-D1` | `regularity.must_not_conflate[0]` | 152 | live denial "No containment with C2 or C0 is asserted here" is false of the same document, whose `implication_ledger` asserts `E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2` (line 238) and derives four one-way entailments from it (241–244) | worker-017, worker-018, worker-066 |
| `W050-F2B-D2` | `implication_ledger.forbidden_transfers[0].reason` | 246 | premise "C2 is a strictly larger extension class" is inverted against the same chain, in which `E_C2` is the innermost/smallest set; the row's conclusion ("C2-inextendibility is strictly weaker") and the prohibition itself are correct | worker-017, worker-018, worker-053, worker-066, worker-075 |
| `W050-F2B-D3` | `conclusion.conclusion_type` | — | `scc_c0_future_inextendibility` (VOCAB_ALIASES canonical) is absent from the F0 declared `field_vocabulary.conclusion_type.allowed`, whose corresponding value is the alias `strong_cosmic_censorship_C0`: two frozen artifacts disagree on the canonical token | worker-075 |

Supporting measurements:

- **Sibling asymmetry (C4).** The accepted F2a (`e9a27996dfd3`) `must_not_conflate[1]` at
  line 152 carries the exact correction note that the F2b denial was wrong
  (`[R2 major: the earlier 'no containment with C2 is asserted' was wrong]`). F2b carries no
  such note at the same publication. The repair landed in one frozen sibling only.
- **Entailment rows are consistent (C5).** All four `one_way_entailments` rows follow the
  chain orientation (E_to ⊆ E_from), so D1/D2 are the only self-inconsistent carriers.
- **Binding census (C7).** 7 adverse verdicts are bound to the current pin `b2ab6acb2bbe`
  (worker-035's is adverse but carries no comparable carrier text); **0 accepts** are bound
  to it. worker-001's accept cites `177a5f0019b1` and is superseded, not binding.
- **Carry-over (C9).** Both carriers are present in the third-party rev12 snapshot
  `55d0a1ea9bda` (lines 151 and 245), so the rev13 evidence-binding repair neither
  introduced nor removed them. Provenance of that snapshot is indirect (see limits).

## Pins (re-measured at start and exit; any movement voids the run, exit 3)

| input | sha256 |
|---|---|
| `schemas/af_scc_c0_vacuum.yaml` (F2b, rev13) | `b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c` |
| `schemas/af_scc_c2_vacuum.yaml` (F2a control) | `e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe` |
| `artifacts/formulation/FROZEN.json` (rev29) | `815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0` |
| `research_map/formulation_taxonomy.yaml` (declared F0) | `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3` |
| `artifacts/formulation/formulation_taxonomy.yaml` (supplement) | `d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1` |
| `artifacts/formulation/VOCAB_ALIASES.json` | `46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba` |
| rev12 snapshot (third-party, worker-060) | `55d0a1ea9bda…` (measured; cited by the rev12 verdicts) |

FROZEN rev29 declares both canonical pins and `revision: 29` (C1).

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-050/f2b_containment_cluster/audit_f2b_containment.py
# exit 0 = all predicates hold; 2 = a finding is refuted; 3 = input drift (void)
```

Outputs: `report.json` (full check-by-check measurement), `review_binding_table.json`
(per-verdict binding census with review-file hashes).

## Falsifiers

- **F1 (D1):** at the pinned bytes, `must_not_conflate[0]` does not contain the denial, or
  `implication_ledger.extension_class_containment` does not assert the chain → D1 refuted.
- **F2 (D2):** a reading in which `E_C2` is the largest extension set, or a pinned revision
  whose `forbidden_transfers[0].reason` states the ordering consistently with the chain → D2 refuted.
- **F3 (D3):** a pinned F0 revision whose allowed list contains `scc_c0_future_inextendibility`,
  or a VOCAB_ALIASES revision making `strong_cosmic_censorship_C0` canonical → D3 refuted.
- **F4 (whole run):** any pinned input moves (exit 3) → measurement void; re-run at the new bytes.
- **F5 (carry-over):** a canonical rev12 copy whose bytes differ from the worker-060 snapshot
  → the C9 carry-over reading is void.

## Limits

- This is a **worker measurement**, not a gate verdict, node completion, or
  `validation_status`. The map/gate owner must adjudicate.
- The mathematics of containment is **not** re-derived. C2/C3/C5 rest on the file's own
  asserted chain, on reader-level consistency of two carriers, and on the two independent
  reader checks already recorded by other workers; the underlying set-theoretic claim is the
  formulation lead's to certify.
- D3 is a frozen-vocabulary divergence; whether F0 or VOCAB_ALIASES should move is not decided here.
- The rev12 carry-over uses a third-party snapshot (`artifacts/worker-060/…`), not a
  canonical ledger artifact.
- Review-file bytes are snapshotted by hash in `review_binding_table.json`; a later edit to a
  review file does not change this measurement's binding anchor (the F2b hash) but would
  change the census row.
- No canonical artifact, schema, ledger, map, review or detector was written.
