# W082-A1-XTARGET-INDEP-CENSUS-01 — A1 coverage census for F1 / F2a / F2b

- Window: 2026-09-12T01:10:18+08:00 .. 2026-09-12T01:12:08+08:00 (+08:00)
- FROZEN: rev 29 frozen_at 2026-09-12T00:57:26+08:00 sha256 `815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0`
- Hash drift during run: **False**
- Manifest drift during run: **False** (FROZEN rev 29 at start -> rev 29 at end)
- Review records excluded from counts (fixture path/id, label-only, non-protocol verdict, malformed): **1447** {'fixture_path': 2, 'fixture_reviewer_id': 18, 'label_only_empty_text': 19, 'non_protocol_verdict': 1367, 'non_string_verdict': 41}; unbound review-shaped records (no primary hash): **413**
- Worker coverage verdicts (audit evidence only, not gate verdicts): F1=accept/4.0, F2a=accept/4.0, F2b=accept/4.0

## Per-target measurement at the snapshot bytes

| target | class | canonical sha256 | authoring sha256 | mirror equal | binding verdicts (canon) | binding accepts | binding non-accepts | superseded verdicts | coverage |
|---|---|---|---|---|---:|---:|---:|---:|---|
| F1 | AF-WCC-VAC-GEN | `d9cebb9404b2` | `d9cebb9404b2` | True | 19 | 9 | 10 | 37 | accept 4.0 |
| F2a | AF-SCC-C2-VAC-GEN | `e9a27996dfd3` | `e9a27996dfd3` | True | 11 | 3 | 8 | 34 | accept 4.0 |
| F2b | AF-SCC-C0-VAC-GEN | `b2ab6acb2bbe` | `b2ab6acb2bbe` | True | 23 | 6 | 17 | 40 | accept 4.0 |

## Reading (why this matters)

The evidence-binding repair moved all three canonical schemas after FROZEN rev28 was
published, so every rev12 verdict is bound to superseded bytes. This census counts what is
bound to the bytes actually on disk at snapshot time, per reviewer, after collapsing
channel copies and excluding target authors. A coverage verdict of `revise` means binding
verdicts exist but the two-independent-full-schema-verdict criterion is not met; `inconclusive`
means no reviewer verdict binds those bytes at all; `accept` means the criterion is met at the
snapshot sha256. None of these is a statement that the schemas are mathematically right or wrong.

## Per-target detail

### F1 — AF-WCC-VAC-GEN

- **measured_canonical**: 19 verdicts / 121 channel copies; accepts=['worker-011', 'worker-052', 'worker-072', 'worker-075', 'worker-080', 'worker-085', 'worker-086', 'worker-089', 'worker-16']; non-accepts=[['worker-002', 'revise'], ['worker-029', 'revise'], ['worker-034', 'revise'], ['worker-039', 'revise'], ['worker-045', 'revise'], ['worker-048', 'revise'], ['worker-061', 'revise'], ['worker-064', 'revise'], ['worker-071', 'revise'], ['worker-073', 'revise']]; mean/max Jaccard=0.0017/0.0085; ESS=8.882; adjudication=accept 4.0
- **superseded_observed**: 37 verdicts / 879 channel copies; accepts=['worker-026', 'worker-054', 'worker-061', 'worker-088']; non-accepts=[['astra-lead-audit', 'revise'], ['deepseek-flash-04', 'revise'], ['deepseek-flash-15 (slot 015; no F1/F2 authorship; read-only on schemas/)', 'revise'], ['deepseek-flash-16', 'revise'], ['deepseek-flash-17', 'revise'], ['deepseek-flash-18', 'revise'], ['deepseek-flash-19', 'revise'], ['deepseek-flash-21', 'inconclusive'], ['deepseek-flash-22', 'inconclusive'], ['lead-audit', 'revise'], ['worker-005', 'revise'], ['worker-009', 'revise'], ['worker-011', 'revise'], ['worker-025', 'revise'], ['worker-029', 'revise'], ['worker-034', 'revise'], ['worker-039', 'revise'], ['worker-040', 'revise'], ['worker-047', 'revise'], ['worker-053', 'revise'], ['worker-054', 'revise'], ['worker-059', 'revise'], ['worker-061', 'revise'], ['worker-066', 'revise'], ['worker-071', 'revise'], ['worker-078', 'revise'], ['worker-081', 'revise'], ['worker-082', 'revise'], ['worker-085', 'revise'], ['worker-088', 'revise'], ['worker-090', 'revise'], ['worker-094', 'revise'], ['worker-096', 'revise']]; mean/max Jaccard=0.0037/0.0162; ESS=3.956; adjudication=revise 2.5
- **unbound (no primary hash field)**: [('deepseek-flash-15 (slot 015; no F1/F2 authorship; read-only on schemas/)', 'revise'), ('worker-037', 'revise'), ('worker-048', 'revise'), ('worker-077', 'revise'), ('worker-078', 'revise'), ('worker-16', 'revise')]

### F2a — AF-SCC-C2-VAC-GEN

- **measured_canonical**: 11 verdicts / 72 channel copies; accepts=['worker-017', 'worker-018', 'worker-072']; non-accepts=[['worker-028', 'revise'], ['worker-040', 'revise'], ['worker-046', 'inconclusive'], ['worker-047', 'revise'], ['worker-075', 'revise'], ['worker-090', 'revise'], ['worker-091', 'revise'], ['worker-092', 'revise']]; mean/max Jaccard=0.0057/0.0121; ESS=2.966; adjudication=accept 4.0
- **superseded_observed**: 34 verdicts / 681 channel copies; accepts=['deepseek-flash-18', 'worker-047', 'worker-050', 'worker-061', 'worker-069', 'worker-089', 'worker-098']; non-accepts=[['astra-lead-audit', 'revise'], ['deepseek-flash-05', 'revise'], ['deepseek-flash-19', 'revise'], ['deepseek-flash-21', 'inconclusive'], ['deepseek-flash-22', 'inconclusive'], ['worker-005', 'revise'], ['worker-020', 'revise'], ['worker-033', 'revise'], ['worker-034', 'revise'], ['worker-035', 'revise'], ['worker-039', 'revise'], ['worker-041', 'revise'], ['worker-043', 'inconclusive'], ['worker-043', 'revise'], ['worker-047', 'revise'], ['worker-048', 'revise'], ['worker-059', 'revise'], ['worker-061', 'revise'], ['worker-066', 'revise'], ['worker-069', 'revise'], ['worker-086', 'revise'], ['worker-088', 'revise'], ['worker-090', 'revise'], ['worker-091', 'revise'], ['worker-092', 'revise'], ['worker-095', 'revise'], ['worker-096', 'revise']]; mean/max Jaccard=0.0005/0.0026; ESS=6.978; adjudication=revise 2.5
- **unbound (no primary hash field)**: [('deepseek-flash-18', 'accept'), ('lead-audit', 'accept'), ('worker-069', 'accept'), ('worker-072', 'accept'), ('worker-078', 'accept'), ('deepseek-flash-15', 'revise'), ('deepseek-flash-17', 'revise'), ('deepseek-flash-18', 'revise'), ('deepseek-flash-19', 'revise'), ('worker-035', 'revise'), ('worker-065', 'revise')]

### F2b — AF-SCC-C0-VAC-GEN

- **measured_canonical**: 23 verdicts / 127 channel copies; accepts=['worker-052', 'worker-061', 'worker-071', 'worker-072', 'worker-090', 'worker-16']; non-accepts=[['worker-002', 'revise'], ['worker-017', 'revise'], ['worker-018', 'revise'], ['worker-034', 'revise'], ['worker-035', 'revise'], ['worker-038', 'revise'], ['worker-044', 'revise'], ['worker-050', 'revise'], ['worker-053', 'revise'], ['worker-062', 'revise'], ['worker-066', 'revise'], ['worker-075', 'revise'], ['worker-085', 'revise'], ['worker-088', 'revise'], ['worker-089', 'revise'], ['worker-095', 'revise'], ['worker-097', 'revise']]; mean/max Jaccard=0.0011/0.0051; ESS=5.967; adjudication=accept 4.0
- **superseded_observed**: 40 verdicts / 831 channel copies; accepts=['astra-lead-audit', 'deepseek-flash-07', 'deepseek-flash-17', 'deepseek-flash-18', 'worker-001', 'worker-030', 'worker-044', 'worker-060', 'worker-089', 'worker-096', 'worker-098']; non-accepts=[['astra-lead-audit', 'revise'], ['deepseek-flash-07', 'revise'], ['deepseek-flash-15', 'revise'], ['deepseek-flash-17', 'revise'], ['deepseek-flash-21', 'inconclusive'], ['deepseek-flash-22', 'inconclusive'], ['worker-005', 'revise'], ['worker-008', 'revise'], ['worker-015', 'revise'], ['worker-022', 'revise'], ['worker-029', 'revise'], ['worker-034', 'revise'], ['worker-035', 'revise'], ['worker-044', 'revise'], ['worker-047', 'revise'], ['worker-059', 'revise'], ['worker-060', 'revise'], ['worker-063', 'revise'], ['worker-066', 'revise'], ['worker-069', 'revise'], ['worker-077', 'revise'], ['worker-080', 'revise'], ['worker-084', 'revise'], ['worker-088', 'revise'], ['worker-091', 'revise'], ['worker-095', 'revise'], ['worker-096', 'revise'], ['worker-098', 'revise'], ['worker-100', 'revise']]; mean/max Jaccard=0.0014/0.0124; ESS=10.843; adjudication=accept 4.0
- **unbound (no primary hash field)**: [('lead-audit', 'accept'), ('worker-044', 'inconclusive'), ('deepseek-flash-09', 'revise'), ('deepseek-flash-15', 'revise'), ('deepseek-flash-18', 'revise'), ('worker-007', 'revise'), ('worker-023', 'revise'), ('worker-044', 'revise'), ('worker-060', 'revise')]

## Controls

```json
{
 "C1_exact_clone_self_similarity": 1.0,
 "C1_exact_clone_pair_similarity": 0.972,
 "C2_null_bag_mean_jaccard": 0.0,
 "C2_null_bag_max_jaccard": 0.0,
 "C2_permutation_of_own_tokens_jaccard": 0.0,
 "C3_accept_vs_nonaccept_mean_jaccard": 0.0013,
 "C3_accept_vs_nonaccept_max_jaccard": 0.0534,
 "C3_max_pair": {
  "jaccard_5gram": 0.0534,
  "accept": {
   "reviewer": "worker-098",
   "target_id": "F2b",
   "family": "superseded_observed",
   "text_sha256": "e51757965a51ca26"
  },
  "non_accept": {
   "reviewer": "worker-063",
   "verdict": "revise",
   "target_id": "F2b",
   "family": "superseded_observed",
   "text_sha256": "78e6f3a64a41a3d9"
  }
 }
}
```

## Falsifier

Re-run `harvest_a1_xtarget_census.py --write` against the archived snapshot hashes under
`artifacts/worker-082/a1_xtarget_census/snapshots/`. This record is void if a primary-hash-bound
verdict is missed, if two accepting reviewers at the same measured sha256 reach Jaccard >= 0.50,
if an accepting reviewer is an author of that target, or if the snapshot bytes re-hash differently
from the pins recorded here (drift makes the record void for the moved target, not false).

Authority: worker evidence only. No gate verdict, no node status, no validation_status.

