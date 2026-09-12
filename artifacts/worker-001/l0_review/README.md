# worker-001 / W001-L0-REVIEW-CE42D205

One bounded class-bound task for gate **G-LIT**, node **L0**, classes
`AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH`.

**Verdict: revise, score 3.5, 1 hard failure (HF-L0-01).** The reviewed ledger
meets the locator half of its stop rule (92/92 source_ids resolve, every
registry row carries a doi/arxiv/url, 0 accepted+unverified contradictions) but
fails the class-column half: 28/62 rows have `class_ids: []` (24 accepted), and
21 of those have no `informs_classes` fallback.

Reproduce (read-only on all reviewed paths; exit 3 = hash drift, no verdict):

```bash
python3 artifacts/worker-001/l0_review/run_l0_review.py \
  --expect-ledger ce42d205e7617e3a032c109b24a00b57c7c6b104f37dad5125745af15deebd72
```

Contents:
- `run_l0_review.py` — pinned checks C1–C13 + 6 negative controls
- `review.json` — the verdict (copy at `reviews/L0-review-worker-001.json`)
- `EVIDENCE.json` — measured hashes, check results, control results
- `raw/arxiv_*.xml` — 4 arXiv Atom payloads fetched at review time (T-302,
  T-505, T-526, T-401), hashed in `EVIDENCE.json`

Not claimed: no gate verdict, no node status, no ledger edit, no claim that any
citation is unsupported (4/4 spot checks SUPPORTED).
