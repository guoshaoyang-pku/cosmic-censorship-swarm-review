# W082-A1-F0-INDEP-REV5-01 — F0 rev5 review-independence census

- Pinned artifact: `research_map/formulation_taxonomy.yaml` sha256 `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3`
- FROZEN: `2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1`; window 2026-09-12T00:48:17+08:00 .. 2026-09-12T00:48:20+08:00 (+08:00); hash drift: **False**
- Worker verdict (audit only, not a gate): **accept** score 4.0; R2 met: True

## Accept corpus at the pinned hash (one row per reviewer)

| reviewer | score | full-schema flag | copies | text tokens | hard failures | representative source |
|---|---:|---|---:|---:|---:|---|
| deepseek-flash-18 | 4.0 | None | 9 | 910 | 0 | `reviews/F0-review-18.json` |
| deepseek-flash-19 | 4.0 | None | 8 | 558 | 0 | `reviews/F0-review-19.json` |
| worker-025 | 4.0 | True | 8 | 608 | 0 | `comms/outbox/worker-025.jsonl` |
| worker-038 | 3.5 | True | 18 | 420 | 0 | `reviews/F0-conformance-038-rev28.json` |
| worker-078 | 4.0 | True | 3 | 430 | 0 | `reviews/F0-criteria-audit-078.json` |
| worker-087 | 4.0 | True | 6 | 218 | 0 | `comms/outbox/worker-087.jsonl` |

## Non-accept verdicts at the pinned hash

| reviewer | verdict | score | copies | findings |
|---|---|---:|---:|---:|
| astra-lead-audit | revise | 3.5 | 7 | 2 |
| worker-047 | revise | 2.5 | 5 | 6 |
| worker-048 | revise | 3.0 | 2 | 2 |
| worker-073 | revise | 3.5 | 3 | 3 |
| worker-094 | revise | 3.5 | 2 | 3 |

## Independence measurement

- Distinct accept reviewers: **6** (deepseek-flash-18, deepseek-flash-19, worker-025, worker-038, worker-078, worker-087)
- Mean / max pairwise 5-gram Jaccard: **0.0038 / 0.0122**
- Kish-style ESS (n/(1+(n-1)r̄)): **5.889**
- Components at tau=0.30 (independence) / 0.50 (protocol dedup): **6 / 6**
- Accepts declaring `counts_as_full_schema_verdict=true`: **4**
- Accepts with a live-store or ingested copy: **6**
- Author reviewers in the accept set: **[]** (excluded author set: astra-lead-formulation, deepseek-flash-01)

## Pairwise accept similarity

```json
[
 {
  "reviewer_a": "deepseek-flash-18",
  "reviewer_b": "deepseek-flash-19",
  "jaccard_5gram": 0.0021
 },
 {
  "reviewer_a": "deepseek-flash-18",
  "reviewer_b": "worker-025",
  "jaccard_5gram": 0.0101
 },
 {
  "reviewer_a": "deepseek-flash-18",
  "reviewer_b": "worker-038",
  "jaccard_5gram": 0.0046
 },
 {
  "reviewer_a": "deepseek-flash-18",
  "reviewer_b": "worker-078",
  "jaccard_5gram": 0.0122
 },
 {
  "reviewer_a": "deepseek-flash-18",
  "reviewer_b": "worker-087",
  "jaccard_5gram": 0.0
 },
 {
  "reviewer_a": "deepseek-flash-19",
  "reviewer_b": "worker-025",
  "jaccard_5gram": 0.0079
 },
 {
  "reviewer_a": "deepseek-flash-19",
  "reviewer_b": "worker-038",
  "jaccard_5gram": 0.0041
 },
 {
  "reviewer_a": "deepseek-flash-19",
  "reviewer_b": "worker-078",
  "jaccard_5gram": 0.0
 },
 {
  "reviewer_a": "deepseek-flash-19",
  "reviewer_b": "worker-087",
  "jaccard_5gram": 0.0026
 },
 {
  "reviewer_a": "worker-025",
  "reviewer_b": "worker-038",
  "jaccard_5gram": 0.002
 },
 {
  "reviewer_a": "worker-025",
  "reviewer_b": "worker-078",
  "jaccard_5gram": 0.002
 },
 {
  "reviewer_a": "worker-025",
  "reviewer_b": "worker-087",
  "jaccard_5gram": 0.0025
 },
 {
  "reviewer_a": "worker-038",
  "reviewer_b": "worker-078",
  "jaccard_5gram": 0.0
 },
 {
  "reviewer_a": "worker-038",
  "reviewer_b": "worker-087",
  "jaccard_5gram": 0.0064
 },
 {
  "reviewer_a": "worker-078",
  "reviewer_b": "worker-087",
  "jaccard_5gram": 0.0
 }
]
```

## Controls

```json
{
 "C1_exact_clone_self_similarity": 1.0,
 "C1_exact_clone_pair_similarity": 0.9956,
 "C2_null_bag_mean_jaccard": 0.0,
 "C2_null_bag_max_jaccard": 0.0,
 "C2_permutation_of_own_tokens_jaccard": 0.0,
 "C3_accept_vs_nonaccept_mean_jaccard": 0.0023,
 "C3_accept_vs_nonaccept_max_jaccard": 0.0177
}
```

## Findings

- **W082-F0I-01** (non_blocking): 6 distinct reviewer accept verdicts bind the pinned F0 rev5 hash 0abb9ed8a961 after collapsing 52 channel copies to 6 reviewers: deepseek-flash-18, deepseek-flash-19, worker-025, worker-038, worker-078, worker-087. Reviewer-text independence (5-gram Jaccard): mean 0.0038, max 0.0122, Kish-style ESS 5.889, accept components at tau=0.30: 6. No pair reaches the protocol same-text dedup threshold 0.50.
- **W082-F0I-02** (non_blocking): Strict full-schema counting: 4 of 6 accepts declare counts_as_full_schema_verdict=true (worker-025, worker-038, worker-087); deepseek-flash-18/19 carry no such declaration. 6 accepts have a live-store or ingested copy; the review store copy of worker-087's accept (artifacts/worker-087/f0_full_review/F0-review-087.json) carries no primary hash field - only its ingested event does. The criterion still clears two independent full-schema verdicts at the pinned bytes.
- **W082-F0I-03** (non_blocking): Channel-copy hygiene: several accepts appear as 2-4 re-emitted copies (worker-038 x4, worker-025 x2, deepseek-flash-18 x2, deepseek-flash-19 x2) with non-identical extracted text in some copies (worker-038 findings 0 vs 2; worker-087 findings 4 vs 3). The audit lead should bind coverage to reviewer ids, not event ids, and to one declared copy per reviewer.
- **W082-F0I-04** (non_blocking): Self-declared exposure exists inside the accept set: reviews/F0-review-18.json discloses reading the headline verdict labels of worker-025's accept and the lead-audit revise before writing; worker-087's file and worker-025/038 all report non-authorship. This measurement establishes text/authorship independence under the protocol rule, NOT statistical error independence - per HANDOFF.md no audited intervention has been shown to restore that.
- **W082-F0I-05** (non_blocking): Convergent issue coverage, not duplication: the unresolved scalar-class genericity (genericity_kind='unresolved' vs an explicit comeager conclusion) is independently reported by worker-025 (W025-F0-O1), worker-038 (W038-02-F1), worker-087 (B3) and deepseek-flash-18 (N1/N2). Four independent reads of one open content item - the audit lead should treat it as one item.
- **W082-F0I-06** (non_blocking): Instrument controls separate duplicates from independent text across the full range: exact clone 0.9956, seeded null mean 0.0 / max 0.0, accept-vs-non-accept mean 0.0023, double-run determinism True.

## Falsifier

Re-run `harvest_f0_independence.py` at the pinned F0 bytes. This record is void if a primary-hash-bound
accept reviewer is missed, if any two accept reviewers reach Jaccard >= 0.50, or if an accepting reviewer
is an author of the taxonomy.

Authority: worker evidence only. No gate verdict, no node status, no validation_status.

