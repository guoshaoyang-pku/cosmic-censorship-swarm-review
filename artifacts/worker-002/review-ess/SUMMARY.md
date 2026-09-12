# W002-REVIEW-ESS-01 -- review-independence (Kish ESS) census

- actor: `worker-002`  |  class binding: AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN, AF-WCC-SCALAR-SPH
- map snapshot: `research_map/research_map.json#4fd40d4d1e4f`  |  captured: 2026-09-12T00:27:05+08:00
- corpus: 199 review records (21 pending ingest)  |  reviewer-vs-actor identity mismatches: 25
- binding_valid=True  drift_targets=none  determinism_ok=True  controls=7/7
- similarity threshold Jaccard>=0.5 over 4-gram shingles; ESS=(sum n_c)^2/sum n_c^2

## Recorded verdicts bound to the LIVE canonical hash

| target | live sha256 | reviews | accept raw/rev/ESS | revise raw/rev/ESS | inconcl. raw/rev/ESS | 2 independent accepts |
|---|---|---:|---|---|---|---|
| A0 | `d748a9e3574e` | 7 | 1/1/1.0 | 4/4/4.0 | 0/0/0.0 | no |
| F0 | `276009f4f63d` | 14 | 1/1/1.0 | 3/3/3.0 | 2/2/2.0 | no |
| F1 | `9a8bd4c96800` | 23 | 0/0/0.0 | 12/8/8.0 | 2/2/2.0 | no |
| F2a | `b6123750b37d` | 28 | 3/3/3.0 | 7/7/7.0 | 2/2/2.0 | YES |
| F2b | `1bb78ce9b357` | 21 | 5/5/5.0 | 4/4/4.0 | 1/1/1.0 | YES |
| L0 | `ce42d205e761` | 9 | 1/1/1.0 | 5/5/5.0 | 0/0/0.0 | no |
| L1 | `315c19145065` | 6 | 2/2/2.0 | 0/0/0.0 | 0/0/0.0 | YES |

Columns are raw events / distinct reviewer identities / ESS after reviewer-dedup then text clustering.

## Limits (read before using)

- Measurement only. This sets no gate verdict, node status or validation_status; the controller/leads adjudicate independence and acceptance.
- Hash binding is permissive: a review counts as bound to the live hash if any cited 8..64-hex token is a prefix of it. A review that merely mentions the live hash in a superseded context is still counted; inspect `accepts_bound_live`.
- Reviewer identity uses the `reviewer` field when present else `actor`. Exposure between reviewers is not observable here.
- Text normalization collapses hex and numeric literals, so reviews differing only in numbers cluster together by design; see controls C3/C4.

## Falsifier

REJECT the headline if: (a) a review file outside `research_map.json#reviews` and `comms/outbox/*.jsonl` changes a target's effective accept count; (b) any cited hash counted as live is not a prefix of the measured canonical sha256; or (c) two accepts in one text cluster are shown to be genuinely independent reviews.

Reproduce: `python3 artifacts/worker-002/review-ess/census_review_ess.py` (exit 0 = stable, exit 2 = target drift during scan).

