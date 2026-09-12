# worker-039 — C0 CONVENTION CAVEAT citation verification

Class-bound task: `AF-SCC-C0-VAC-GEN` (frozen C0 SCC schema). Node `L0` / gate `G-LIT`.
Task id: `L1-C0-CAVEAT-1901.07996`. Status at handoff: **unclaimed**.

## Why this task

`schemas/af_scc_c0_vacuum.yaml` (canonical sha256 `1bb78ce9b357…`, line 99,
`extension_predicate.definition`) carries the only explicitly `UNVERIFIED` citation in the
frozen schemas:

> CONVENTION CAVEAT: for merely continuous metrics the causal structure can be degenerate and
> chronological futures may fail to be open or may depend on the curve class (Grant et al.,
> worker-supplied pointer arXiv:1901.07996, UNVERIFIED); if the causal relation is degenerate,
> the witness must instead be a timelike curve from iota(M) to a point of int(M' minus iota(M)).

No ledger row, review, or event referenced `1901.07996` before this run. This artifact closes
the pointer check; it does **not** claim the C0 class, its conclusion, or clause (f).

## Result

**verdict = PARTIAL** (see `verification.json`).

| caveat sub-claim | grade | decisive evidence |
|---|---|---|
| causal structure degenerate / chronology pathological below Lipschitz | SUPPORTED | abstract; `Future_nopen.tex:87-93` |
| chronological futures may be non-open | SUPPORTED | `Future_nopen.tex:720` (Example 3.1: "not an open subset of R^2"; "answers (Q1) in the negative") |
| futures may depend on the curve class | SUPPORTED | abstract; `Future_nopen.tex:190-191`; Lemma 2.2 at `:340-352` |
| remedy: "the witness must instead be a timelike curve" | **NOT_SUPPORTED_BY_SOURCE** | Lemma 2.2 is the only openness result and holds for the l.u.t./piecewise-C^1 class; `Future_nopen.tex:819` shows the pathologies persist even allowing C^1 curves with finitely many null-tangent points |

Finding for the lead: clause (f)'s degenerate-case witness class is not pinned down. Either
restate it as a **l.u.t. / piecewise-C^1 timelike curve with a named degeneracy criterion**, or
mark clause (f) an **open proof obligation**. Do not silently promote the pointer to VERIFIED.

## Source

- Grant, Kunzinger, Sämann, Steinbauer, *The future is not always open*,
  Lett. Math. Phys. (2019), DOI `10.1007/s11005-019-01213-8`, arXiv:1901.07996v2
  (submitted 2019-01-23, revised 2019-09-09).
- Fetched evidence (hashed into `verification.json`):
  - `raw/arxiv_1901.07996.abs.html` sha256 `97e594378c18…` (HTTP 200 from arxiv.org)
  - `raw/src.tar.gz` sha256 `bf93d7981ba0…` (`https://arxiv.org/e-print/1901.07996`)
  - `raw/src/Future_nopen.tex` sha256 `1e2fd7a7665e…` (LaTeX source, 1130 lines)

## Reproduce

```bash
python3 artifacts/worker-039/c0_continuous_metric_citation/verify_c0_caveat_citation.py
```

Fail-closed: exit `2` on schema-hash drift, missing/tampered raw evidence, or a required
verbatim quote not found; exit `0` with `verification.json` rewritten on success.

## Measurement caveat (important)

The canonical C0 schema was republished during this session (`68392dd82050…` → `1bb78ce9b357…`
at 2026-09-12T00:19:14+08:00). Every quote, grade, and check here binds **only** to
`1bb78ce9b357…`; the checker refuses to run against any other hash. A later schema revision
must be re-checked, not assumed.

## Boundaries

- Read-only w.r.t. `research_map/*`, `schemas/*`, `ledger/*`: nothing was mutated.
- `validation_status: unverified`; no gate verdict, no `done` status, no completion claim.
- One source inspected; the two-dimensional α-Hölder examples lie inside C0, but the schema's
  "merely continuous" scope is broader than the examples.
