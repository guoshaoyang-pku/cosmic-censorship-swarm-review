# worker-001 F2b review

Target: `schemas/af_scc_c0_vacuum.yaml` (AF-SCC-C0-VAC-GEN, node F2b, gate G-FORM)
Verdict: **accept** score 4.0 at sha256 `1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508`

Reproduce (fail-closed: exits 3 without a verdict if the canonical bytes changed):

    python3 artifacts/worker-001/f2b_review/run_review.py --root . --expect 1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508 --out artifacts/worker-001/f2b_review/review.json

- Full verdict: `artifacts/worker-001/f2b_review/review.json` (copy: `reviews/F2b-review-worker-001.json`)
- Measurement chain and pinned inputs: `artifacts/worker-001/f2b_review/PIN_MANIFEST.json`
- Conditions: W001-F1 variant registry, W001-F2 conclusion-type vocabulary, W001-F3
  non-reproducible consistency evidence. Minor: W001-F4 duplicate YAML keys, W001-F5
  revised_at ahead of mtime. Info: W001-F6 disjunctive D0, W001-F7 binding current.
