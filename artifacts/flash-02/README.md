# FLASH-02 / F0-G-F0 — adversarial class-leakage test corpus

Assignment: `asg-2026-09-11-F0-deepseek-flash-02-11` (from Astra, `comms/inbox/deepseek-flash-02.jsonl`)
Node: `F0`  Gate: `G-F0`  Deadline: `2026-09-12T03:15+08:00`

Task as assigned: adversarial test cases for class leakage; artifact `schemas/taxonomy_cases.jsonl`;
>= 8 positive and >= 8 negative cases covering the 4 classes; each case names the class and the
decisive hypothesis. Acceptance: submit with sha256; flag ambiguous cases as open.
Falsifier: a case cannot be classified under exactly one class.

## Deliverable

`schemas/taxonomy_cases.jsonl` — 37 records: 1 `meta` + **16 positive** + **20 negative** cases.

| class | positive | negative |
|---|---:|---:|
| AF-WCC-VAC-GEN | 4 | 4 |
| AF-SCC-C2-VAC-GEN | 4 | 6 |
| AF-SCC-C0-VAC-GEN | 4 | 4 |
| AF-WCC-SCALAR-SPH | 4 | 3 |
| cross-class / composite (no single class) | 0 | 3 |

Every case carries: `statement`, `decisive_hypothesis`, `decisive_axes`, `axis_vector`,
`expected_verdict`, `expected_classification`, `expected_leak_rule`, `leak_kind`,
`expected_resolution`, `open`, `falsifier`, `evidence_refs`, `binding_status`.

`expected_resolution` gives each case exactly one intended gate action, so the corpus is an
oracle rather than a collection of opinions:

- `unique_class:<class_id>` — positive; accept and classify to exactly this class.
- `reject_misfiled:target=<class_id>` — negative; evidence supports the target class instead.
- `reject_new_class_required` — negative; no class in the taxonomy accepts the record (CG2).
- `reject_split_required` — negative; the record must be split into >= 2 class records.
- `reject_leak:<rule_id>` — negative; reject with the named textual/semantic leak rule.

`open: true` (9 cases) marks decidable gate inputs that expose an open taxonomy gap or require a
split. They are **flagged for the formulation lead**, not resolved by this worker.

## Binding and provenance

- Taxonomy: `research_map/formulation_taxonomy.yaml`, revision 3, status `draft_unverified`.
  The file is **live-edited by the swarm**: during this run its sha256 moved
  `a82f249c` (rev1) -> `347c924b` (rev2) -> `dac2853c` (rev2) -> `14bc6a1b` (rev2) -> `66bf917b` (rev3).
  The rev3 migration was detected by the checkpoint daemon and the corpus was re-pinned and re-verified:
  axes unchanged, checker still PASS with 10/10 controls. **Revision numbers are not a binding
  identity; the sha256 is.** Every case carries `binding_status: bound_taxonomy_sha_<12 hex>` and
  the checker fails if the axes no longer resolve. `artifacts/flash-02/pin_taxonomy.py` re-pins
  idempotently when the hash moves.
- Leak-rule catalog: `artifacts/flash-02/leak_rule_catalog.json` — maps every negative to
  taxonomy guards G1-G7, forbidden transfers X1-X5, coverage gaps CG1/CG2, or open questions Q1/Q2.
- Positive case `TC-F0-P15` is anchored to a fetched primary source:
  Christodoulou 1999, *Ann. of Math.* **149**, 183-217,
  PDF sha256 `9ac456d0795916782a58fc474aa2c8e235395f9a869355733e62228ec345adfd`,
  extracted text sha256 `b391e2e430a717d733aec68a3bf251bc7d4a04e47a7a00ea7ef217805a3d5f3a`
  (`artifacts/flash-02/sources/`). Crossref records for that paper, its 1994 companion and
  Choptuik 1993 are in the same directory. No theorem status is claimed.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/flash-02/check_taxonomy_cases.py         # corpus checker + 10 mutation controls
python3 artifacts/flash-02/escape_matrix.py                # independent tiered-gate simulation
python3 artifacts/flash-02/pin_taxonomy.py                 # re-pin to current taxonomy sha
python3 artifacts/flash-02/annotate_expected_resolution.py # regenerate expected_resolution/open
```

Checker result on taxonomy sha `66bf917b` (rev3): **PASS**, 10/10 negative controls detected.
It enforces: structure, vocabulary, unique-class resolution for positives, non-resolution for
axis negatives, lexical-pattern presence, semantic witnesses, paraphrase-token absence, coverage,
one-resolution-per-case, and pairwise class disjointness.

## Measurements (independent implementation, `escape_matrix.json`)

Taxonomy rev2 G3 semantics (normalize `^ { } _` and whitespace, then match the merged token):

| gate tier | positives accepted | negatives rejected | escape rate |
|---|---:|---:|---:|
| T1 axis + vocabulary | 16/16 | 12/20 | 40.0% |
| T2 T1 + rev2 lexical G3/G7 | **15/16** | 14/20 | 30.0% |
| T3 T2 + semantic adjudication (upper bound) | 16/16 | 20/20 | 0% |

T1 escapes: `N05` (bare `Theorem:`), `N06` (comeager->measure-one), `N07` (C2 filed as C0),
`N08` (visibility premise for inextendibility), `N12` (bare `generic` + theorem), `N17` (vacuous
generic set), `N19`/`N20` (extension-class smuggle). T2 additionally catches `N05` but still
escapes `N06, N07, N08, N12, N17, N19`.

## Findings for the formulation and audit leads

1. **G3 is negation-blind, also in rev2.** Minimal repro: positive `TC-F0-P04` says *"...no
   statement is made about C0 or C2 inextendibility"*; the rev2 normalized match still fires, so a
   naive lexical gate rejects a conforming record (T2 `wrongly_rejected_positives`). Fix: apply G3
   to conclusion/regularity content only, or exclude explicit disclaimer contexts, with
   `TC-F0-P04` + `TC-F0-N13/N14` as regression tests. The pattern to copy is
   `artifacts/worker-01/validate_taxonomy.py`'s `semantic_subset` approach.
2. **The C2 vocabulary's containment claim is false as written.** Taxonomy rev2 says the C2
   conclusion forbids "C2 (hence also C^{1,1}, H^2_loc, C^k for k>=2)". But
   `C^k(k>=2) subset C^2 subset C^{1,1} subset C^0`, and the sharp Sobolev embedding gives
   `H^s(R^4) subset C^0` only for `s > 2`, so `H^2_loc` is **not** contained in C^2. Forbidding
   C2 extensions does not forbid C^{1,1} or H^2_loc extensions by containment. Cases
   `TC-F0-N19`/`N20` encode this leak; the fix needs a containment/converse ledger, not a
   parenthetical (open question Q2).
3. **Five-plus negatives are semantic-only.** No regex over the statement reliably catches
   `N06, N07, N08, N12, N17, N19`; they need a semantic gate plus independent reviewer. Treating
   T1/T2 as sufficient leaves a measured 30% negative escape rate on this corpus.
4. **Same revision, different content.** The taxonomy's sha256 changed twice while `revision`
   stayed `2`. Any pipeline that pins a revision number instead of a hash can silently bind to
   different prose. Recommend `artifact#sha256` pinning for every downstream gate.
5. **Nine cases are open.** `N01, N10, N16` require new classes (non-spherical scalar/CG2,
   de Sitter); `N13, N14, N15` require splitting; `N04` electrovacuum; `N09` SCC scalar; `N18`
   T1 guard record. Routed to the formulation lead.

## What this does not claim

- No theorem, counterexample, numerical result, or physics claim.
- No verification that any real research statement belongs to a class; the cases are fixtures.
- No completion of F0/G-F0. The artifact is `validation_status: unverified`; F0 requires two
  independent reviewer verdicts and, per `comms/PROTOCOL.md` rule 2, a sha256 registered in
  `runtime/state/artifact_hashes.json`.
- The anchor material in `sources/` verifies source scope only (bibliographic metadata and
  verbatim text presence); it does not promote Christodoulou 1999 to a claim of this swarm.

## Next falsifiers

1. Re-run `check_taxonomy_cases.py` against the next taxonomy hash; any case whose axis vector no
   longer resolves uniquely falsifies the binding (this already happened once, rev1 -> rev2).
2. Implement a negation-aware G3 and show `TC-F0-P04` accepted while `TC-F0-N13/N14` rejected.
3. Implement a semantic gate for the six T2-escaping cases and re-measure the escape rate; a
   claimed 0% with no per-case witness is not accepted.
4. Produce an explicit `H^2_loc \ C^2` witness (or a containment lemma) to settle finding 2.
