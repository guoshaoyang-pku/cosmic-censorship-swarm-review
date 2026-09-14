# Swarm effectiveness evaluation — first audited cycle

## What was evaluated

The first five-role DeepSeek Flash cycle produced formulation (F1), literature (L1), numerics (N1), adversarial audit (A1), and synthesis (S1) drafts. Four independent review roles then examined the formulation draft and the taxonomy: mathematical referee (R1), literature verifier (R2), numerical-relativity referee (R3), and swarm-evaluation designer (R4).

## Measured execution metrics

- API completion: 5/5 first-cycle roles after endpoint and reasoning-mode repair.
- Structural audit: 5/5 outputs had valid outer JSON and nonempty scope/caveat fields.
- Independent review completion: 4/4 after one network retry.
- Scientific acceptance of F1: 0/1 under the proposed ACR gate.
- Hard-failure rate for F1: 1/1, because it merges WCC/SCC and C0/C2 variants and phrases conjectural statements as universal claims.
- Citation verification for F1: not applicable as a positive rate; F1 supplied no citations, so it fails the citation gate rather than receiving credit.

These numbers show why HTTP success and output length are inadequate swarm metrics: the first fluent formulation draft was rejected by all relevant gates.

## Independent-review consensus

R1 identified 15 issues and rated the draft's overall mathematical correctness about 2.4/5. The most serious issues were undefined genericity, conflation of incompleteness/Cauchy horizons/visibility, treating C0 and C2 inextendibility as interchangeable, and using DOC definitions as if they were conclusions.

R2 marked the theorem-ledger claims for primary-source verification rather than accepting them as citations. It specifically requires checking genericity, null-infinity regularity, DOC causal properties, Cauchy-horizon claims, and any statement that upgrades model-specific work to a general theorem.

R3 rejected F1 as a numerical-relativity formulation because it was mislabeled: the proposed spherical scalar pilot must use `AF-WCC-SCALAR-SPH` or `AF-SCC-SCALAR-SPH`, while F1 claimed vacuum WCC/SCC. It also required a correct reduced ansatz, separate horizon definitions, a causal-boundary visibility formulation, and explicit convergence/constraint tests.

R4 supplied the useful evaluation design: compare one strong model, self-consistency sampling, independent cheap agents, and cheap agents plus coordinator at equal token and wall-clock budgets. Suggested pass thresholds are ACR≥0.60, citation-support fraction≥0.75, fabricated-citation rate≤0.03, hard-failure rate≤0.10, duplication≤0.35, reviewer kappa≥0.60, information gain≥0.15 versus the strong-model baseline, and at least 8 of 12 priority classes covered.

## Current verdict

The swarm is **useful as a proposal generator and adversarial checklist generator**, but it is **not yet reliable as a mathematical research oracle**. Its value appears only after class binding, independent review, citation verification, and explicit rejection of overstrong statements. The first cycle is a successful harness test precisely because it caught a fluent but invalid formulation.

## Required next gate

Do not launch the numerical pilot from F1. First produce a corrected class-bound formulation for `AF-WCC-SCALAR-SPH`, separately produce a conjecture-only schema for `AF-WCC-VAC-GEN` and `AF-SCC-C2/C0-VAC-GEN`, then rerun R1–R3. A formulation may enter the canonical ledger only if two reviewers agree within one score point and no hard failure remains.
