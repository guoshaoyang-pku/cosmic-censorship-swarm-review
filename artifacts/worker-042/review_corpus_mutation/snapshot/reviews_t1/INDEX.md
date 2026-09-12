# A1 review queue

Generated: 2026-09-11T23:27:56+08:00  |  reviewers assigned: lead-audit (this file set)

| target | artifact | sha256 (12) | verdict | score | hard failures |
|---|---|---|---:|---:|---|
| A1 | `?` | `?` | ? | ? |  |
| F0 | `research_map/formulation_taxonomy.yaml` | `347c924b4273` | revise | 3.0 | HF-02, HF-06, HF-04 |
| F1 | `schemas/af_wcc_vacuum.yaml` | `a7ef0398dfb7` | revise | 3.0 | HF-06, HF-04 |
| F2a | `schemas/af_scc_c2_vacuum.yaml` | `21df6f7fc4a6` | revise | 3.0 | HF-02, HF-06, HF-04 |
| F2b | `schemas/af_scc_c0_vacuum.yaml` | `0150bfdf671b` | revise | 4.0 | HF-06, HF-03 |
| G-FORM | `artifacts/{worker-06,flash-11,flash-13,worker-17,worker-05} class-binding gates + fixtures` | `4b2297eb850b` | reject | 2.0 | HF-12 |
| L0 | `ledger/theorems.jsonl + artifacts/literature/{registry,batch-01,batch-02,batch-w07,unresolved}.jsonl` | `e42923726186` | revise | 3.0 | HF-03 |

## Independence and review assignment

- lead-audit reviews above are semantic (class binding, conclusion direction, evidence scope).
- Reviewers 17/18/19 are assigned to reproduce them independently; assignments are in
  `comms/inbox/deepseek-flash-{17,18,19}.jsonl`. A worker's own artifact may not be
  reviewed by its author.
- Kish ESS is reported for any set of reviews that share a text or a template;
  two reviews that agree because they are the same text count as one.

## Ledger audit summary

- theorem entries: 43; registry entries: 119; unresolved: 0
- status distribution: {'verified-primary': 21, 'unresolved': 2, 'verified-api': 96}
- broken refs: 24; non-class tokens: 8; duplicate title pairs: 11; missing scope metadata: 119

## Gate status after this review

| gate | verdict | reason |
|---|---|---|
| G-F0 | fail | F0 revise (C2 containment reversal, provisional axes) |
| G-FORM | fail | F1/F2a/F2b revise; no frozen data class; tooling unreliable |
| G-LIT | fail | ledger scope metadata + dedup + broken refs |
| G-AUDIT | pending | A0 rubric materialized and self-tested; A1 queue open |
| G-NUM | pending | numerics lock respected; N0 calibration not yet reviewed |

