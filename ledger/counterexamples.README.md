# L1 counterexamples ledger — `ledger/counterexamples.jsonl`

Assignment: `asg-2026-09-11-L1-deepseek-flash-11-20` (Astra, node **L1**, class **GLOBAL**,
gate **G-LIT**, deadline 2026-09-12T03:15+08:00).
Worker: `deepseek-flash-11`. Status: **draft, unreviewed, gate not claimed.**
Artifact sha256: `581b9cdf41b1d1d6d617aaa1ef0b3891f059f53b2e1b13424031165963cb2d82`
(`ledger/counterexamples.jsonl.sha256`). Metadata: `ledger/counterexamples.meta.json`.
Builder (deterministic): `artifacts/flash-11/L1_counterexamples/build_counterexamples.py`.

## What this is

12 records of known solutions/spacetimes/results that probe **hypothesis necessity** for the
frozen cosmic-censorship formulation classes. Each record carries: the class it bounds, the
hypothesis it violates, why that hypothesis is inside the class statement (so the entry is a
legitimate probe and not the failure mode named in the assignment's falsifier), the
conclusion failure, the primary source, and the exact verification method used.

Acceptance asked for **>=6**; 12 are supplied. 9/12 have a verbatim abstract retrieved;
3/12 are metadata-level only and say so. No entry is marked verified or reviewed.

## Verification levels (do not flatten these)

| level | meaning | entries |
|---|---|---|
| `arxiv_abstract_page` / `inspire_api_abstract` / `osti_abstract_page` | DOI/arXiv metadata resolved and a verbatim abstract obtained | ce-01, ce-03, ce-05, ce-06, ce-07, ce-08, ce-09, ce-10, ce-11 |
| `crossref_api` / `crossref_search` | bibliographic metadata resolved; no abstract obtained | ce-02, ce-12 |
| title-level (inside the above) | the content claim is title-level | ce-04 (no abstract in INSPIRE) |

One correction is recorded rather than hidden: an early search-result guess of
`10.1007/BF01212252` for Christodoulou 1984 was wrong; INSPIRE resolves the paper to
`10.1007/BF01223743`, which is what the ledger uses (ce-06).

## Coverage: hypothesis x class

| hypothesis probed | class bound | entries | binding confidence |
|---|---|---|---|
| positive ADM mass / energy condition | AF-WCC-VAC-GEN | ce-01 | provisional (schema unfrozen) |
| vacuum matter (Q=0), sub-extremality | electrovacuum extension (**GLOBAL**) | ce-02 | out of frozen scope |
| genericity (threshold/codimension-one) | AF-WCC-SCALAR-SPH | ce-03, ce-04, ce-05 | mixed (ce-04 title-level) |
| spacetime dimension = 4 | AF-WCC-VAC-GEN | ce-07 | confounded with ALF |
| regularity / maximal-development | AF-WCC-VAC-GEN | ce-08 | probe only, not a refutation |
| vacuum matter model (dust analogue) | **GLOBAL** | ce-06 | out of frozen scope |
| asymptotic flatness / I+ structure | **GLOBAL** | ce-11 | nakedness assumed, not proved |
| **C0-inextendibility conclusion** | AF-SCC-C0-VAC-GEN | ce-09 (against), ce-10 (control) | conditional on Kerr stability |
| C2 extension regularity | AF-SCC-C2-VAC-GEN | ce-12 | charged analogue only |

## Empty cells (the informative part)

* **4D vacuum, genericity.** No counterexample exists in this ledger. Every known
  naked-singularity example found is either non-vacuum (dust, scalar, charged), or
  non-dynamical (static exact solutions), or in dimension > 4. For AF-WCC-VAC-GEN this is
  consistent with the conjecture being open; it means the genericity hypothesis for *vacuum*
  cannot currently be shown necessary by example.
* **AF-SCC-C2-VAC-GEN, hypothesis necessity.** No vacuum entry. ce-09 is about C0 and
  ce-12 is charged; the C2 class's necessity is supported only by contrast, not by a direct
  vacuum counterexample.
* **Non-generic vacuum data.** Same as the first cell: no example found.
* **Energy conditions other than positive mass** (ANEC, DEC as separate hypotheses):
  not covered.

## How to re-fetch (audit path for flash-19 / lead-literature)

Each record stores `source.resolver_api` — the exact INSPIRE/Crossref/OSTI/arXiv URL used.
Procedure: re-fetch that URL, compare title/authors/venue/DOI, then compare
`source_verification.abstract_quote` character-for-character. A mismatch is a hard finding.

## Next falsifier (assignment-aligned)

1. Freeze F1/F2, then run the class-binding gate against the frozen schemas and re-bind every
   entry. Any entry whose violated hypothesis is **not imposed** by the frozen schema is
   dropped or re-labelled as a scope note — this is the assignment's stated falsifier.
2. Re-fetch every `resolver_api` URL and diff quotes; report any drift verbatim.
3. For ce-09: re-check whether the C0 class defines inextendibility among *vacuum solutions*
   or among continuous Lorentzian manifolds. If the former, ce-09 does not refute the class
   and loses its role.
4. For ce-04 (title-level): obtain the 1994 Annals paper text (JSTOR) and replace the
   inferred genericity binding with a quoted one, or mark unresolved.

## Corrections (self-audit)

- **2026-09-11T23:45 — ce-10 page range withdrawn.** The first revision said
  "J. Differential Geom. 108, 285-316". That value came from memory. Crossref for
  `10.4310/jdg/1518490820` carries **no page range**, and a secondary reference list
  (Van de Moortel, CMP 382:1263-1341) cites 319-378. The field is now `null` and the
  uncertainty is recorded in the record. The JSONL sha256 therefore changed from
  `78e2dcf7…` to `{new}`; the first artifact event is superseded.

## Provenance note

The builder writes fixed bytes (no generation timestamp inside the JSONL), so the sha256 is
reproducible. `counterexamples.meta.json` carries the counts and known gaps.
