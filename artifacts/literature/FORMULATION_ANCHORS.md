# Formulation ↔ literature anchors (response to F1)

- **From:** astra-lead-literature (L0/L1 owner) · **At:** 2026-09-12T00:09+08:00
- **Re:** `comms/inbox/astra-lead-literature.jsonl` lines 6–7 (lead-formulation evidence packet
  `2026-09-11T23:43:51` and ack `2026-09-11T23:47:08`)
- **Canonical audit:** `ledger/citation_audit.csv` (`315c1914…`) · **Adjudication:** `reviews/L2-shard-adjudication.md`

## Request 1 — unanchored F1/F2 items

| item used by F1/F2 | ledger status after this pass | what would close it |
|---|---|---|
| weighted-Sobolev thresholds `s > 5/2` | **absent** — no source row, no theorem row | a bibliographic pointer from F1 (author/year/venue or DOI/arXiv). The ledger anchors only what it can locate and quote; it will not invent a citation. |
| `δ ∈ (1/2, 1)` | **absent** | same |
| positive mass theorem | **absent** (not among the 97 sources) | a specific statement + primary locator; the ledger needs to know which form (ADM/PMT rigidity) F1 uses |
| future-asymptotic-predictability equivalence | **absent as a source**; the vocabulary exists only in prose | a primary definition text; the ledger has no theorem entry for it |
| containment chain `E_C2 ⊂ E_{C^1,1} ⊂ E_H2loc ⊂ E_C0` | **not anchored** as such | primary sources for each inclusion. Note SRC-090 now shows the SCCC statement is parameterised by an unspecified `C^k`, which weakens any claim that a single source fixes the chain. |

These four items are carried as a blocker event (`lit-l2-20260912-010`) so they cannot silently
disappear. No row was added without a working locator.

## Request 2 — Grant et al. and Rendall (absent from the audit)

**Resolved this session.** Both are now canonical sources, with locators re-fetched by the lead:

| new source | locator | evidence level (canonical) | assessment |
|---|---|---|---|
| **SRC-096** Grant–Kunzinger–Sämann–Steinbauer, *The future is not always open*, Lett. Math. Phys. 110(1) 83–103 (2020) | `10.1007/s11005-019-01213-8`, arXiv:1901.07996 | abstract-read (peer-reviewed) | **caveat pointer only.** Low-regularity causality theory: chronological futures need not be open; causal bubbling. No Einstein equation, no 4D AF data, no genericity statement → it cannot support a claim that the AF-SCC-C0 class is degenerate. |
| **SRC-097** Rendall, *The nature of spacetime singularities*, in *100 Years of Relativity* (2005) 76–92 | `10.1142/9789812700988_0003`, arXiv:gr-qc/0503112 | abstract-read (survey) | **survey-level only.** Confirms the Cauchy-horizon vocabulary and the Taub-NUT non-vacuity example; proves no theorem about Kerr/AF extendibility. |

**Clause (f) wording finding (from worker-09 P5, abstract-level supported by the lead).** The
correct caveat is *"not causally plain (may exhibit bubbling)"*, **not** *"causal structure can be
degenerate"*. Worker-09 P5 extracted Theorem 2.10 / 2.15, Corollary 2.16 and Example 3.1 from
arXiv:1901.07996v2; the lead verified the abstract and paper structure but did not re-extract the
theorem bodies. F1 owns the decision to adopt this wording change.

## Request 3 — Cauchy-horizon adjudication ("must ANY future extension of an AF development cross a CH?")

**Literature-side answer: the ledger does not settle this, and cannot with its current sources.**

- The closest evidence is **SRC-004 Dafermos–Luk 2025** (Ann. Math.): a `C^0` extension across a
  *non-trivial* Cauchy-horizon piece, with the antecedent (Kerr exterior stability) claimed only in
  the 2026 Hintz preprint (SRC-078). Both are labelled `preprint`/`preprint-antecedent` in the ledger.
- **SRC-024 / SRC-081 / SRC-080** give the C^2 / Lipschitz side (inextendibility), not a general
  "every extension crosses a CH" statement.
- **SRC-090** shows the classical SCCC statement ("every maximal Hausdorff development … is globally
  hyperbolic") is stated for an unspecified `C^k`, i.e. it defines failure as a *differentiability*
  breakdown, not as "crossing a CH".
- Therefore the question is a **formulation scope decision** (what counts as an extension and in
  which regularity), not a literature gap that can be closed by another fetch. It is escalated back
  to F1 with the two admissible readings recorded:
  1. *strong reading* — any extension of the development must cross a Cauchy horizon: not supported
     by any ledger source;
  2. *weak reading* — for the MGHD to be extendible there must exist a Cauchy horizon separating
     the development from the extension: supported at definition level (SRC-097 vocabulary;
     SRC-090's global-hyperbolicity failure), but with no genericity content.

Until F1 rules, L1 will not bind any class-identity separation to a CH-crossing predicate.
