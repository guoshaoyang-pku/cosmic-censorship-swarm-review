# P5 — L1 adjudication of the two quarantined AF-SCC-C0-VAC-GEN pointers

- Worker: `deepseek-flash-09` (worker 09) · Assignment: `asg-2026-09-11-L1-deepseek-flash-09-18`
- Node: L1 (literature) · Gate: **G-LIT** · Class bound: **AF-SCC-C0-VAC-GEN** only
- Phase: P5 (post-freeze addendum; the canonical ledger was frozen at 2026-09-11T23:57+08:00 and
  **no canonical file was written by this worker**)
- Target under review: `artifacts/formulation/schemas/af_scc_c0_vacuum.yaml`
  sha256 `bdb23f76b89540e82e4a8a3feb12637eb646af54466f624cf6ba2fef5a94bf90`, field
  `extension_predicate.definition` clause (f) `CONVENTION CAVEAT` (currently marked
  *"worker-supplied pointer arXiv:1901.07996, UNVERIFIED"*) and the accompanying
  `[R2 major, recorded not fully resolved]` note, which also cites Rendall `gr-qc/0503112`.

This closes the two pointers the formulation lead recorded as absent from the L1 ledger
(`astra-lead-literature.jsonl`, `leadform-lit-ack-2026-09-11T23:47:08+08:00`: *"Grant et al.
arXiv:1901.07996 and Rendall gr-qc/0503112 are cited in our C0/causality fields but absent from
your audit"*). Method: fetch the abs record, the full text, and the Crossref record; extract
numbered results; assert every quote against the cached text before writing it; run a
wrong-DOI control. Machine-readable output: `artifacts/worker-09/extracted/p5_findings.json`.

---

## 1. W09-P5-001 — Grant et al., "The future is not always open" — **supported, wording correction required**

**Locator.** arXiv:1901.07996 [math-ph], **v2** (2019-09-09); published as *Letters in
Mathematical Physics* **110** (2020), no. 1, 83–103, DOI `10.1007/s11005-019-01213-8`.
Both the official arXiv HTML v2 and the ar5iv rendering were read; theorem numbering agrees.

Cited claim under test: *"for merely continuous metrics the causal structure can be degenerate
and chronological futures may fail to be open or may depend on the curve class."*

**Theorem-level support (read, not inferred):**

- **Theorem 2.10** (continuous, chronological spacetime): openness of `I^±(p)` for all `p` is
  equivalent to `∂I^±(p)` being achronal, equivalently an achronal Lipschitz-hypersurface.
- **Theorem 2.15**: `I_{C∞}^±(p) = I_{C¹_pw}^±(p) = I_{L}^±(p) = I_{AC}^±(p)` for all `p` **iff**
  there is no internal bubbling — i.e. the chronological future can depend on the curve class.
- **Corollary 2.16** / causally-plain equivalence, and the sentence following it: *"Any spacetime
  with a Lipschitz continuous metric is causally plain"* — so the pathology is possible below
  Lipschitz, not automatic.
- **Example 3.1**: an `α`-Hölder (not Lipschitz) continuous metric on `R²` where *"The
  chronological future of any point with x<0 is not an open subset of R²"* and
  *"This answers (Q2) in the negative"* (the piecewise-`C¹` and Lipschitz definitions differ).
- **Lemma 2.9**: for continuous metrics `I_{AC}^± = I_{L}^±`, so the "natural" locally Lipschitz
  convention is the one the paper's abstract flags.

**Class binding — what this does *not* prove.** The paper has no Einstein equation, no
4-dimensional asymptotically flat data, and no genericity statement; its examples are
2-dimensional non-vacuum metrics. It therefore supports **only** the convention caveat that the
clause (f) witness `I^+(q;g')` must fix its curve class in the C0 regularity. It does not
establish the frozen class conclusion in either direction, and it does not prove the lead's
fallback-witness equivalence (timelike curve from `iota(M)` into `int(M' \ iota(M))`); that
remains an inference of the schema author.

**Wording correction (requested).** The schema says *"the causal structure can be degenerate"*.
The source does not say the causal structure is degenerate: the metric is continuous and
Lorentzian (**nondegenerate**) throughout. What can fail is **causal plainness** — bubbling,
non-open `I^+`, curve-class dependence. Recommended replacement: *"the spacetime need not be
causally plain (it may exhibit bubbling), in which case `I^+` need not be open and may depend on
the curve class (Thm 2.10, Thm 2.15, Ex 3.1)"*, keeping the fallback-witness sentence labelled
as the lead's convention choice.

**Metadata correction for the lead.** The R2 review bibliography records *"Lett. Math. Phys. 109
(2019) 83–91"*. The version of record is **110 (2020) 83–103**, DOI
`10.1007/s11005-019-01213-8` (Crossref-confirmed). Use the corrected locator in any schema or
ledger citation.

**Falsifier.** A page check of the published version showing Thm 2.10/2.15 or Ex 3.1 renumbered
or restated; or a 4-dimensional continuous-non-Lipschitz **AF vacuum** example in which `I^+` is
open and curve-class independent (that would make the caveat unnecessary, though not false).

---

## 2. W09-P5-002 — Rendall, "The nature of spacetime singularities" — **supported at survey level, non-transfer clause required**

**Locator.** arXiv:gr-qc/0503112 **v1** (2005-03-29); published in *100 Years of Relativity:
Space-Time Structure: Einstein and Beyond* (A. Ashtekar, ed.), World Scientific, 2005, pp. 76–92,
DOI `10.1142/9789812700988_0003` (Crossref-confirmed). No numbered theorem is used by the cited
sentences; this is expository survey prose.

**Supported statements:**

- **Section 2** (after the Eardley–Moncrief formulation of SCC): *"It may happen that the maximal
  Cauchy development can be extended to a larger spacetime, which is then of course no longer
  globally hyperbolic. The boundary of the initial spacetime in the extension is called the
  Cauchy horizon."* — the exact vocabulary the class uses.
- **Section 2**: *"A famous example where this happens is the Taub-NUT spacetime [31]. This is a
  highly symmetric solution of the Einstein vacuum equations. The extension which is no longer
  globally hyperbolic contains closed timelike curves."* — a vacuum example in which the
  extension predicate is non-vacuous (the extension is smooth, hence also C0).
- **Section 2**: genericity is exactly the right qualifier — *"for generic data the maximal
  globally hyperbolic development is inextendible"* is stated as the SCC goal, achieved only in
  symmetry classes which *"are not generic and so they do not directly say anything about cosmic
  censorship."*
- **Section 3**: *"When the Schwarzschild solution is generalized to include charge or rotation
  the picture changes dramatically. In the relevant solutions, the Reissner-Nordström and Kerr
  solutions, the Schwarzschild singularity is replaced by a Cauchy horizon."*

**Class binding — what this does *not* prove.**

1. Nothing about the AF-SCC-C0-VAC-GEN conclusion, positively or negatively: the survey proves no
   theorem about generic AF vacuum data.
2. It does **not** prove that exact Kerr / Reissner–Nordström AF Cauchy data have an extendible
   maximal development. That is an inference from Section 3 survey prose; the R2 review already
   labelled it unverified, and this audit agrees.
3. The Taub-NUT extension is **smooth**, so it cannot discriminate C0 from C2 or H2_loc; it must
   not be used as a C0-specific or C2-specific witness.
4. Taub-NUT is *highly symmetric*, i.e. outside any comeager set of AF data: it motivates the
   genericity quantifier, it does **not** refute the class.

**The formulation lead's highest-value open question** — *whether ANY proper future extension of
an AF development must cross a Cauchy horizon* — is **not settled by these sources**. Note also
that the frozen C0 extension predicate (a)–(f) contains no Cauchy-horizon condition, so no
class-identity separation claim should be made to depend on that premise until a primary
(numbered-theorem) source is located. Status: **unresolved**, recorded in `p5_findings.json`
under `unresolved`.

**Falsifier.** A primary source showing exact Kerr/RN AF data have an inextendible maximal
development falsifies the class-motivating use of the Section 3 sentence; a statement in
Rendall's text that Taub-NUT data are generic AF data falsifies the non-transfer clause above.

---

## 3. Method control — W09-P5-CTRL-1 (passed)

The candidate DOI `10.1007/s11005-018-1110-z` (a plausible guess for Grant et al.) was fetched
from Crossref and resolves to **"M-theory from the superpoint"**, *Lett. Math. Phys.* 108,
2695–2727 (2018) — a different work. It was rejected; the DOI printed on the arXiv abstract page
(`10.1007/s11005-019-01213-8`) resolves to the correct title. This is the L1 falsifier pattern
*"a DOI resolves to a different work"* exercised on a live guess, and it is why the metadata
correction in §1 is not taken from the review text but from the resolver.

## 4. C0 / C2 separation discipline

None of the verified material transfers across the C0/C2 split: Grant et al. is a regularity
statement about `I^+`, not about metric extendibility classes; Rendall's Taub-NUT/Kerr/RN
examples are smooth extensions. In particular this audit does **not** license any statement of
the form "C0 implies C2" or "a C2 result covers C0 data".

## 5. Evidence hashes (all fetched 2026-09-12, HTTP 200)

| file | sha256 |
|---|---|
| `artifacts/worker-09/extracted/p5_findings.json` | `c6a65bb17353353e52ce43ade1412478fe1086487dbd15789bd8df41fbcb28a5` |
| `artifacts/worker-09/p5_pointer_verification.md` | this file; hash pinned in the artifact event below |
| `ledger/citation_audit_scc_flash-09.p5.csv` | `85d6b49c401b5e46567fe91fd2798d6c50306fc5ed53cbd795df5850dd6a6c0f` |
| `artifacts/worker-09/sources/full5b_1901.07996v2.html` (arXiv HTML v2) | `718cee6022ba820bc7898e7db5080712077b70f9b185dd59b96b10a0bb180225` |
| `artifacts/worker-09/sources/full5_1901.07996.html` (ar5iv) | `21d112b36c3284130df921fd08c17868f6d72bc9ec420614ca36f6fb2af33a3d` |
| `artifacts/worker-09/sources/abs_1901.07996.html` | `97e594378c18afde92fc137364006b963b43150c176658adb52661e750b175f9` |
| `artifacts/worker-09/sources/crossref_1901_07996_correct.json` | `e9d6b04f2c0213e5a2cb84f194b6b446f3424294d93b913ceb0614d0b618c22d` |
| `artifacts/worker-09/sources/crossref_1901_07996.json` (control) | `10aba6b14070eb8c08df6aa5c611ad1045990eaf16556172407ae79d004f3518` |
| `artifacts/worker-09/sources/full5_grqc0503112.html` (ar5iv) | `574f851713b33c70ee19c49373a2016c20a91bb73f7d3b399656c41844b55c14` |
| `artifacts/worker-09/sources/abs_grqc0503112.html` | `54f2247e8a4459db19702216ac78ad8d506186946f054648561e1050a2ea5069` |
| `artifacts/worker-09/sources/crossref_grqc0503112_correct.json` | `865a57c204fbaa2cbb5a02c14f3c04331414de9219e8292fa2157fa02124ba7c` |
| `artifacts/worker-09/extracted/pointers/grant2019.txt` | `892921f50ce6a20eb2b4fb22acd0a1590a8c0925ba8187a6839e0bb624a3f277` |
| `artifacts/worker-09/extracted/pointers/rendall2005.txt` | `f6bc1d9ec77364992dcf363968b903122055e248d401ab09f1f6f715eeb12a81` |

Fetch manifest with HTTP codes and sizes: `artifacts/worker-09/sources/fetch_manifest_p5.tsv`.
Builders: `build_p5_findings.py` (quote assertions + hashes), `build_p5_rows.py` (CSV projection).

## 6. Integration request (owner action; no worker writes to the canonical ledgers)

1. Reword the clause (f) caveat as in §1 and drop the `UNVERIFIED` marker for
   arXiv:1901.07996; keep the fallback-witness sentence labelled as a convention choice.
2. Add `W09-025`/`W09-026` from `ledger/citation_audit_scc_flash-09.p5.csv` to the canonical
   citation audit if the freeze is re-opened (they are additive rows; the canonical file was not
   touched).
3. Keep the Cauchy-horizon adjudication **unresolved**; it needs a primary theorem, not a survey.

## 7. Next falsifiers

- A page check of the *published* Grant et al. numbering, or of the Rendall volume pagination.
- A primary theorem on Kerr/RN AF extendibility (either direction).
- A 4-dimensional continuous-non-Lipschitz AF vacuum example with open, curve-class-independent
  `I^+` (would retire the caveat, not refute it).
