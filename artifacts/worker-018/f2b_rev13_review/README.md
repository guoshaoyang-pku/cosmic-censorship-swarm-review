# Worker-018 F2b rev13 review (W018-R13-F2B-REVIEW-01)

One bounded class-bound task: independent at-pin A1 review of
`schemas/af_scc_c0_vacuum.yaml` (class `AF-SCC-C0-VAC-GEN`, node F2b, gate G-FORM)
at `sha256:b2ab6acb2bbe`.

- Verdict: **revise**, score 3.0 — 20 PASS / 2 FAIL, both FAILs are normative prose
  carriers inside this artifact (see `REVIEW.json`).
- Checker: `check_f2b_rev13.py` (read-only, no network, re-runnable from repo root).
  Exit 0 iff no FAIL. C17/C18 are the verdict-bearing checks.
- Results: `results.json`.
- Evidence only: no gate verdict, no node status, no canonical artifact edited.

Reproduce: `python3 artifacts/worker-018/f2b_rev13_review/check_f2b_rev13.py`
