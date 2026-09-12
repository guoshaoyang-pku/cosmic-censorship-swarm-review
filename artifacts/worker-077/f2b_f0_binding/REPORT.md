# W077-F2B-F0BIND-CONSISTENCY-01 — F0-declared vs F2b consistency audit (worker-077)

- **Class**: `AF-SCC-C0-VAC-GEN` · **Nodes**: F2b, F0 · **Gate**: G-FORM (+ G-F0)
- **Verdict**: `revise` (2.5/5) · hard failures: C2-F0-F2B-INDEX-CONSISTENCY, C3-F2B-F0-BINDING, C4-CITATION-BINDING-REPLICATION · superseded: False
- **Created**: 2026-09-12T00:40:50+08:00 · worker evidence only; no gate verdict.

## Pinned inputs

| path | sha256 |
|---|---|
| `schemas/af_scc_c0_vacuum.yaml` | `55d0a1ea9bda96b8` |
| `artifacts/formulation/schemas/af_scc_c0_vacuum.yaml` | `55d0a1ea9bda96b8` |
| `research_map/formulation_taxonomy.yaml` | `0abb9ed8a96135c9` |
| `ledger/theorems.jsonl` | `a1674f09497975cf` |

## Checks

| id | severity | result | detail |
|---|---|---|---|
| C0-PIN-STABILITY | hard | **PASS** | all four pinned inputs matched their declared sha256 before the checks |
| C1-DUP-KEY-GUARD | hard | **PASS** | no duplicate YAML mapping keys in the two parsed targets |
| C2-F0-F2B-INDEX-CONSISTENCY | hard | **FAIL** | primary finding: F0 declared C0 quantifier domain vs F2b D0 -> DIVERGENT_F0_OMITS_SMOOTH_BRANCH |
| C2b-F0-QUANTIFIER-EXPLICITNESS | info | **PASS** | the declared F0 C0 text does carry an explicit comeager quantifier bound before the data, so the G-F0 'explicit comeager quantifier' wording criterion is nominally met; the defect is the index domain, not quantifier abse |
| C3-F2B-F0-BINDING | hard | **FAIL** | declared F0 hash matches the live declared artifact; consistency evidence declared 675a99d0d25b but live file measures 9e335e9ba1bf |
| C4-CITATION-BINDING-REPLICATION | hard | **FAIL** | 5 F2b l1_ledger_refs rows claim citation_status='verified_by_L1' while the pinned ledger records review_status='not_independently_reviewed' (token 'verified_by_L1' occurs 0x in the ledger; schema provenance.citation_stat |
| C5-CLASSIFIER-SELFTEST | hard | **PASS** | index classifier controls 5/5 pass (equal, omit-smooth, omit-sobolev, both-named, absent) |
| C6-FROZEN-CONTEXT | info | **PASS** | FROZEN.json measured for context only (not a hard check; the freeze is owned by the formulation lead) |
| C7-POST-CHECK-DRIFT | hard | **PASS** | no pinned input moved during the audit window |

## Primary finding (W077-HF-01)

The declared F0 taxonomy C0 conclusion (lines [346]) reads:

> For every admissible (s,delta) there is a comeager set G_{s,delta} of data such that for every data set in G_{s,delta}, the MGHD is future-inextendible as a C0 (continuous-metric) Lorentzian manifold: it admits no isometric embedding into a larger spacetime whose metric extends continuously. The com

F2b rev12 defines the same class over a wider index (line 52):

> admissible regularity indices, a tagged disjoint union: r = smooth (the smooth-with-decay default) or r = (sobolev,s,delta) with s > 5/2 and delta in (1/2,1). X^r_vac(AF) is the corresponding one-ended AF vacuum constraint manifold (Frechet for r = smooth; weighted Sobolev product H^s_delta x H^{s-1

Classifier result: `DIVERGENT_F0_OMITS_SMOOTH_BRANCH`. The F2b `f0_binding` is hash-current to this taxonomy revision, so the two pinned artifacts state the class over different index domains; the taxonomy's H3 defers the data space to F2, so the gate owner should either refresh the F0 text or record the deferral explicitly.

## Findings

### W077-HF-01 (major)

Declared-F0 vs F2b quantifier-domain divergence: the canonical taxonomy's C0 conclusion quantifies over admissible (s,delta) pairs (G_{s,delta}) and never mentions the smooth-with-decay branch, while F2b rev12 defines D0 as the tagged disjoint union r = smooth OR r = (sobolev,s,delta) and quantifies 'forall r in D0'. The F2b f0_binding is hash-current to the same taxonomy revision, so one class id currently has two pinned statements with different index domains. The taxonomy's H3 defers the data space to F2, which makes this a dispositionable deferral rather than a mathematical contradiction, but no explicit deferral note is recorded at the conclusion and the lead's taxonomy_consistency check does not compare the class-statement index domain.

- **needed_to_unblock**: gate owner disposition: either refresh the F0 C0 conclusion text to the r-index (matching F2b/F2a) at a new taxonomy revision, or record the deferral explicitly in the F0 class text and re-review at the new hash
- **falsifier**: At the same pinned hashes, the finding is refuted if the F0 taxonomy C0 conclusion quantifies over the smooth-with-decay branch as well as the Sobolev branch, or if it carries an explicit index-deferral clause that supersedes its '(s,delta)' wording.

### W077-HF-02 (major)

F2b f0_binding.consistency_evidence_sha256 is stale: it declares 675a99d0d25b2b37 while the file it names measures 9e335e9ba1bfcf77. The declared F0 artifact hash itself does match the live taxonomy. Independently reproduced from worker-095's F-EVID-1 at the same hashes.

- **needed_to_unblock**: refresh f0_binding.consistency_evidence_sha256 to the canonical-path bytes and re-freeze, or restore the enriched evidence bytes and re-pin
- **falsifier**: declared consistency-evidence sha256 == measured canonical-path sha256 at the reviewed revision

### W077-HF-03 (major)

F2b l1_ledger_refs over-claim replicated at ledger a1674f09497975cf: ['D-002', 'T-301', 'T-515', 'T-528', 'T-302'] claim citation_status='verified_by_L1' while the ledger records verification_status='abstract-read' and review_status='not_independently_reviewed'; the token 'verified_by_L1' occurs 0 times in the ledger.

- **needed_to_unblock**: set those five citation_status values to the ledger's own vocabulary (abstract-read) or produce ledger rows whose verification_status/review_status record independent L1 verification, then re-pin
- **falsifier**: a ledger row for any of the five ids with verification_status='verified' and a review_status other than 'not_independently_reviewed' at the pinned ledger hash

## Falsifier

Re-run this harness on the same pinned bytes: any hard check that reports PASS here must still report PASS; a pinned input that changes supersedes the verdict instead of falsifying it. W077-HF-01 is falsified by an F0 C0 conclusion that quantifies the smooth-with-decay branch too.

## Non-claims

- not a gate verdict
- does not set any node done
- does not upgrade validation_status
- not a full-schema acceptance verdict
- F2b rev12 content is not re-adjudicated here

## Reproduce

```bash
python3 artifacts/worker-077/f2b_f0_binding/check_f2b_f0_binding.py
```
