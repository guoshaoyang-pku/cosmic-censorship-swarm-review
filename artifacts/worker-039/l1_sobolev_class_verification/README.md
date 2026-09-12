# W039-L1-SOBOLEV-CLASS-01 — primary-source check of the frozen schemas' `sobolev_variant` citation

Worker-039, bounded execution worker. Class-bound task, node L1, gate G-LIT (G-FORM dependency
noted). Read-only with respect to canonical artifacts: this directory is the only write.

## What was checked

All three frozen class schemas carry the same declared-unverified data-class variant:

```
sobolev_variant: {s: "s > 5/2", delta: "delta in (1/2, 1)",
                  spaces: "h - delta_ij in H^s_delta, K in H^{s-1}_{delta+1}",
                  status: "standard_choice; UNVERIFIED citation"}
```

- `schemas/af_wcc_vacuum.yaml` — block form, lines 108-112, sha256 `cce9c60146d6a907...`
- `schemas/af_scc_c2_vacuum.yaml` — line 132, sha256 `5476a3f2c6bc7196...`
- `schemas/af_scc_c0_vacuum.yaml` — line 133, sha256 `55d0a1ea9bda96b8...`

The claim was decomposed before any verdict was computed (see `decision_rule` in
`verification.json`) and tested against four pinned open-access sources.

## Verdict: PARTIAL — the `UNVERIFIED citation` flag must stay

| sub-claim | status | evidence |
|---|---|---|
| SC1: `s > 5/2` classical local threshold for AF vacuum data | **SUPPORTED** | KR2001 `arXiv:math/0109173`, Theorem 1.1 (`for some s > 5/2`) and Remark 1.2 (`classical local existence result of [H-K-M] for asymptotically flat initial data sets ... with ∇g,k ∈ H^{s-1}(Σ) and s > 5/2`) |
| SC2: decay family `h-δ = O(r^-1)`, `K = O(r^-2)` | **PARTIALLY_SUPPORTED** | LR2005 `arXiv:math/0312479` = CMP 256:43-110 (2005), §1: `g_0ij = (1+2M/r)δ_ij + o(r^{-1-σ})`, `k_0 = o(r^{-2-σ})`, `σ > 0`; the source rates are strictly faster little-o and it does not enumerate the schema's derivative counts |
| SC3: weighted encoding `H^s_δ`, `H^{s-1}_{δ+1}` | **NOT_FOUND_IN_CHECKED_SET** | absent from all four checked sources; BI2004 `arXiv:gr-qc/0405092` §3 instead uses `(ḡ + H^2_{-1/2}) × H^1_{-3/2}` (negative decay indices), BIERI2009 uses interior/exterior weighted `L^p` norms |
| SC4: interval `δ ∈ (1/2, 1)` | **NOT_FOUND_IN_CHECKED_SET** | no checked source states a δ-range at all |

The threshold and the decay family are real and locatable; the *weighted encoding and the
interval are not*, and the checked literature uses different index-sign conventions. Clearing
the flag on the strength of the fetched sources would promote fluent text to a verified
citation, so the recommendation is to **retain `status: "standard_choice; UNVERIFIED citation"`**
and, if desired, add the KR2001/LR2005 locators as partial-support annotations. The schema
owner should supply a section/page locator in a named source (the schemas' `provenance` names
only "Choquet-Bruhat-Geroch maximal development" with `identifier: null`, which does not cover
this field), checking the index-sign convention before binding it.

## Files

| file | role |
|---|---|
| `verify_sobolev_class_claim.py` | fail-closed checker: source integrity, required quotes, absence checks, fabrication + mutation controls, verdict computation |
| `checks.json` | per-check raw evidence (matched text, offsets, contexts) |
| `verification.json` | structured result, sub-claims, decision rule, recommendation, falsifier |
| `SOURCE_MANIFEST.json` | fetched sources with sha256 and provenance |
| `run.log` | checker stdout at the final run |
| `raw/` | pinned fetched sources (ar5iv HTML renderings) + arXiv metadata XML |
| `entry_hashes.json` | hashes of every artifact in this bundle + the canonical inputs measured |

Reproduce:

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm/artifacts/worker-039/l1_sobolev_class_verification
python3 verify_sobolev_class_claim.py    # exit 0, prints overall_verdict
```

## Falsifier

A fetched primary source with an exact locator (section, theorem, page) stating the schema's
conjunction — `h - δ_ij ∈ H^s_δ` and `K ∈ H^{s-1}_{δ+1}` with `s > 5/2` and `δ ∈ (1/2, 1)` on
asymptotically flat vacuum data — flips SC3/SC4 and the overall verdict to SUPPORTED. A source
showing that `δ > 1/2` alone is the standard statement would instead make the `(1/2, 1)`
interval an unlicensed strengthening.

## Controls

- Fabricated-quote control: a synthetic claim sentence is absent from the pinned sources.
- Mutation control: changing one character of a real quote makes the matcher fail.
- Absence checks run over *all* four sources, not just the intended one.

## Authority and non-claims

Worker evidence only; no node status, no `validation_status=passed`, no gate verdict. This does
not assert the schema's normalization is wrong — only that it was not found in the four checked
open sources; absence there is not absence in the literature. The KR2001 identifier is a preprint
record, and the result it states is attributed by it to [H-K-M], which was not fetched.
