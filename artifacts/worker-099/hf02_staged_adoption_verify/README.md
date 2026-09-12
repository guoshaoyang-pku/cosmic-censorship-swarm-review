# W099-HF02-STAGED-ADOPTION-VERIFY-01 — non-author verification of the staged HF-02 repair

Worker `worker-099`, node `L0`, gate `G-LIT`, classes `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`,
`AF-WCC-VAC-GEN`. Read-only on every canonical path. Worker evidence only: no ledger edit, no
gate verdict, no `validation_status=passed`, no node status.

## Why

BL-7 (`comms/outbox/astra-lead-literature.jsonl` `lit-l10-20260912-006`) is the single
gate-blocking decision on G-LIT: does rubric-literal HF-02 ("disjunction of class_ids", critical)
apply to ledger rows? Its option (b) is "adopt a tested, content-preserving staged repair"
(worker-025, `staged/theorems.hf02-staged.jsonl#b3ab6a1a6357`). Worker-025 verified only that
applying worker-023's dispositions was mechanical and explicitly did **not** re-derive them;
worker-023's packet owns the dispositions but is unapplied and itself carries one pending F1
ruling. No non-author verification of the staged bytes existed. This packet supplies it before
the ruling is made.

## Pins (all measured; fail-closed)

| path | sha256 |
|---|---|
| `ledger/theorems.jsonl` | `a1674f094979…` |
| `artifacts/worker-025/l0_hf02_staged/staged/theorems.hf02-staged.jsonl` | `b3ab6a1a6357…` |
| `artifacts/worker-025/l0_hf02_staged/staged/diff.json` | `241b493611c0…` |
| `artifacts/worker-023/l0_hf02/hf02-disjunction-adjudication-023.json` | `0f86158c5bb7…` |
| `research_map/formulation_taxonomy.yaml` | `0abb9ed8a961…` |
| `evaluation_rubric.yaml` | `d748a9e3574e…` |
| `artifacts/formulation/VARIANT_REGISTRY.json` (live) | `6bac9adea19e…` |
| `…/VARIANT_REGISTRY.5eb42f9a384a.json` (packet revision) | `5eb42f9a384a…` |
| `artifacts/worker-099/bl7_hf02_binding/binding_analysis.json` (prior census) | `ffe9119cb5f2…` |

Zero pin drift; every input re-measured unchanged after the run.

## Result (core digest `ca5479f39559ac25`, identical across two runs)

Mechanically the staged repair is faithful and effective:

* **8/8** of worker-023's recommended dispositions applied exactly (class_ids + informs_classes);
  `ledger_tags_add` appended in order on all 6 rows that carry one.
* 62 rows, order preserved; only `class_ids`, `informs_classes`, `ledger_tags` differ, only on the
  8 named rows; every other field byte-identical.
* rubric-literal HF-02 disjunctions **8 → 0**; unknown frozen-token hits 0; variant ids in
  `class_ids` 0 (`class_ids ∩ informs_classes = ∅` on all rows).
* population rows whose own `does_not_imply` disclaims a token in their `class_ids`
  **8/8 → 0/8** (the repair removes every self-contradicted class binding).

But it is **not license-complete**, and it does not by itself discharge G-LIT:

| per-row | live class_ids | staged class_ids | staged informs | worker-023 | subject-reading crosswalk |
|---|---|---|---|---|---|
| D-004 | C2, C0 | — | C0 | VARIANT_INFORMS | aligned (intermediate, no frozen class) |
| D-005 | C0, C2 | — | C0 | VARIANT_INFORMS | aligned (intermediate, no frozen class) |
| T-303 | C2, C0 | — | C0 | VARIANT_INFORMS | **not aligned** (prior subject C0 demoted) |
| T-305 | C0, C2 | — | C0 | VARIANT_INFORMS | aligned (intermediate, no frozen class) |
| T-402 | C2, C0 | — | C0, C2 | RELATION_INFORMS | **not aligned** (prior genuine dual demoted) |
| T-515 | WCC, C0 | WCC | — | WCC_ONLY | aligned (subject preserved) |
| T-526 | C2, C0 | — | C2 | NEEDS_F1_RULING | **not aligned** (prior subject C0 dropped, C2 inference kept) |
| T-528 | WCC, C0 | WCC | — | WCC_ONLY | aligned (subject preserved) |

1. **T-526 is LICENSE_PENDING.** Its packet row carries `needs_f1_ruling` (does a characteristic
   interior-data result discharge `AF-SCC-C2-VAC-GEN`?), and the staged bytes apply the packet's
   `if_no` default. No accepted lead/controller ruling on that question exists after the packet
   time (`research_map/events.jsonl`, 0 hits). Adopting the staged bytes adopts a default branch
   of an explicitly open ruling.
2. **Empty class bindings grow 28/62 → 34/62**, and rows with `conclusion_type ∈ {theorem,
   conditional_theorem}` and no class binding grow 21 → 24 (newly T-303, T-305, T-526). The G-LIT
   criterion `statement scope matched to class_id` (`evaluation_rubric.yaml:140`) cannot be
   satisfied for a row with `class_ids == []`, so option (b) still needs an explicit ruling that
   empty class bindings are acceptable — or a repair that binds the disputed subjects.
3. **The interpretive fork is live on 3/8 rows.** Under the prior worker-099 subject-matter census
   (`ffe9119cb5f2`; 16/16 cell quotes re-grounded in the pinned bytes, fabrication control clean),
   T-303, T-402 and T-526 change meaning: the subject class is demoted to `informs_classes` (or,
   for T-526, replaced by the C2 inference relation). The BL-7 ruling must select the semantics of
   `class_ids` (conclusion-instance vs subject-matter) before the staged bytes can be called
   content-preserving for those rows.
4. Registry pin drift is immaterial: the packet pins `5eb42f9a384a`, live is `6bac9adea19e`; only
   the `SET` variant changed, while `L2CONN`, `LIP`, `H2LOC` are byte-identical across revisions.
   Pin hygiene note only.

## Checks and controls

C1 rows/allowed-fields PASS · C2 detector PASS · C3 binding shape PASS · C4 adoption fidelity PASS ·
C5 conditional license LICENSE_PENDING · C6 self-declared scope INFO · C7 gate scope-match census
INFO · C8 subject crosswalk INFO · C9 registry drift INFO · C10 informs text mention INFO.
Controls: CTL-1a/1b/2/3/4/5 all PASS (detector, unknown-token, scope-rule, row-integrity,
fidelity and quote-grounding mutation controls all flip as declared).

## Reproduce

```bash
python3 artifacts/worker-099/hf02_staged_adoption_verify/run_adoption_verify.py
# -> verdict=VERIFIED core_digest=ca5479f39559ac25
```

## Falsifiers

Re-run at the same pins and get a different `core_digest`; any pinned hash moves; an accepted
lead/controller ruling on T-526's characteristic-interior question (flips C5 to PASS); a G-LIT
gate pass or an explicit HF-02 scope ruling after 2026-09-12T00:36:38+08:00 (closes BL-7 and
changes the consequence above).

## Files

| path | role |
|---|---|
| `PREREGISTRATION.json` | frozen rules, hypotheses, controls, falsifiers (written before the run) |
| `run_adoption_verify.py` | deterministic stdlib-only instrument (fail-closed on pins) |
| `RESULTS.json` | machine record: pins, checks, controls, per-row table, aggregates, digest |
