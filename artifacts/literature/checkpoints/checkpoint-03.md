# Checkpoint 03 — literature group (L0/L1)

- Time: 2026-09-11T23:34+08:00 (elapsed ~17 min wall clock; the "hours" field in the corresponding outbox status events was also corrected to true wall-clock values)
- Counts: 77 sources, 57 entries (46 accepted, 10 provisional, 1 rejected-as-superseded)
- Independent reviewers: 3 subagents still running (scalar/vacuum WCC audit; SCC audit; citation-integrity spot-check)

## Closed since checkpoint 02

| gap | resolution | source |
|---|---|---|
| MGHD existence/uniqueness (needed to define every class) | closed; new definition entry D-008 | Choquet-Bruhat-Geroch 1969, CMP 14, 329-335 (SRC-073) |
| Dafermos 2003 exact scope | closed via OpenAlex abstract reconstruction: open set of characteristic data, curvature blows up, metric extends continuously | SRC-072 |
| Ringstrom 2009 Gowdy statement | closed enough to accept: C^2-inextendibility, open in C^1, dense in C^infinity; 2009 paper proves density | SRC-071; T-520; T-513 rejected as superseded |
| An 2025 DOI | closed: 10.4007/annals.2025.201.3.3 | SRC-067 |
| RSR 2023 journal ref | closed: Ann. Math. 198(1), 2023-07-01 | SRC-068 |
| Luk-Sbierski 2016 | verified at arXiv level (1512.08259); JFA volume still unconfirmed | SRC-066 |
| Rossetti 2025 (new) | charged massive KG on RN-dS: C^0 + L^2 Christoffel + H^1 extensions; second use of "Christodoulou-Chrusciel version" | SRC-070; T-519 |
| Scalar-field naked-singularity literature | added Liu-Li 2018 (robust instability), Li-Liu 2022 (non-symmetric perturbations, first-category exceptional set), Singh 2025 (fine-tuned NON-generic stable perturbations), Guo-Hadzic-Jang 2023 (Einstein-Euler isolated naked singularity) | SRC-074..077; T-522..525 |

## Structural result for the map

The AF-WCC-SCALAR-SPH dossier now has a clean picture:
- Christodoulou 1994 builds the naked-singularity family; 1999 proves instability in a rough framework; Liu-Li 2018 re-proves it robustly; Li-Liu 2022 extends instability to non-symmetric perturbations (exceptional set first category); An 2025 (Annals) censors the family with an anisotropic apparent horizon; Zheng 2026 finds stability only in a Holder topology; Singh 2025 finds stable perturbations only for fine-tuned non-generic data.
- Net: there is no verified primary result showing naked singularities are generic in any smooth/rough topology; every "stability" result is either topology-specific or non-generic by construction. This is now stated as a scope warning in the dossier.

## Citation-integrity finding (channel-level)

OpenAlex returns a **contaminated abstract** for DOI 10.1103/PhysRevLett.14.57 (Penrose 1965): the abstract_inverted_index reconstructs text about a 1960 cosmic-ray blast wave, not the singularity theorem. Metadata (title/authors/volume/pages/year) is correct. Consequence: OpenAlex abstracts are accepted only when cross-checked against a second channel; Penrose 1965 stays metadata-only and is not used for scope. Recorded for reviewer C.

## Reviews pending

Three background subagents are auditing (a) scalar/vacuum WCC entries, (b) SCC entries, (c) citation integrity. Their reports will land in `artifacts/literature/reviews/`. Any accepted entry they falsify will be demoted in the next build, and the failure recorded as progress.

## Next (checkpoint 04 target ~01:50)

1. Merge reviewer findings; demote/reword as required; add a `reviews/lead-adjudication.md`.
2. Write the human-facing `artifacts/literature/LITERATURE_STATUS.md` per-class status card with confidence and open items (for Astra/F1/N1).
3. Final unresolved sweep: Chrusciel defining text; Luk-Sbierski JFA volume; Ringstrom 2009 published-page confirmation; Penrose 1969 exact wording.
4. Final report + outbox event set; validate everything.
