# Checkpoint 04 — literature group (L0/L1)

- Time: 2026-09-11T23:39+08:00 (elapsed ~22 min wall clock)
- Counts: 90 sources (89 verified, 1 unresolved candidate), 60 entries (48 accepted, 11 provisional, 1 rejected-as-superseded)
- Reviews: adversarial A and B complete and adjudicated; citation-integrity C still running

## Late-breaking literature update (the headline of this checkpoint)

Three 2026 preprints change the SCC picture, and the ledger now carries them:

1. **Luk-Sbierski, arXiv:2604.04877 (Apr 2026), "The formation of a weak null singularity in the interior of generic rotating black holes"** — nonlinear vacuum, no symmetry, strictly rotating subextremal Kerr: a weak null singularity forms; the metric is C^0-extendible but **not Lipschitz-extendible** (T-526).
2. **Sbierski, arXiv:2409.18838, "Lipschitz inextendibility of weak null singularities from curvature blow-up"** — symmetry-free criterion; accepted for publication in **Inventiones Mathematicae** per the arXiv comment (T-527).
3. **Hintz, arXiv:2606.28253 (Jun/Aug 2026), "Nonlinear stability of subextremal Kerr black holes"** — claims global nonlinear stability in the **full subextremal range**, with companion preprints (T-528). This discharges the antecedent of the Dafermos-Luk conditional refutation of C^0 SCC at preprint level (T-301, T-515).

Consequences recorded in the class dossiers:
- `AF-SCC-C2-VAC-GEN`: from "no theorem located" (T-401 at checkpoint 03) to "covered at preprint level for generic rotating interiors; no peer-reviewed full-AF Cauchy theorem". Status entry T-401 remains provisional.
- `AF-SCC-C0-VAC-GEN`: the refuted corner now extends to the full subextremal range at preprint level; the data-class caveats remain.
- All three are preprints; peer review is a tracked unresolved item.

## Reviewer findings adjudicated (A and B)

Twelve findings were fixed, including: an inverted sentence in D-002 (C^0 extensions *do* exist), a wrong arXiv ID in SRC-043 (1207.3167→1207.3164), wrong JFA pages in SRC-066/SRC-089 (1948-1995), T-101 conclusion inflation (demoted to provisional, reworded), class-tag inflation on 10 matter/test-field entries (moved to `informs_classes`), and the metadata-only-anchor policy (now enforced by the builder and enumerated in the manifest). Full table: `reviews/lead-adjudication.md`.

## Structural improvements

- `class_ids` now means "the statement is about this class"; cross-class relevance is explicit in `informs_classes` and rendered as an "Informing evidence" section in every class dossier.
- Builder fails closed on: accepted entry with no abstract-level source; bad conclusion type; unknown class; missing falsifier; unresolved source on an accepted entry.
- `MANIFEST.json` enumerates accepted entries that carry metadata-only bibliographic anchors (9 currently) so the audit trail is explicit.

## Still open

1. Reviewer C (citation integrity) report and integration.
2. Post-change re-check: reviews A and B pinned earlier hashes; a final independent pass over the frozen ledger is queued.
3. Peer review of T-526/T-527/T-528; second Hintz companion (tame estimates) not located.
4. Chrusciel 1991 candidate (SRC-090) and the C² formulation origin text.
5. F0 artifact still missing; class binding remains provisional.

## Budget

~22 min wall clock. Work is retrieval- and adjudication-bound; no resource request.
