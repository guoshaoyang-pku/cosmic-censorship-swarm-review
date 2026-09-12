# worker-018 F2a rev13/rev29 independent review harness (W018-R13-F2A-REVIEW-01)

Read-only, deterministic, no network, no model calls.

- Target: `artifacts/formulation/schemas/af_scc_c2_vacuum.yaml`
  sha256 `e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe` (bytes 30594),
  byte-identical to `schemas/af_scc_c2_vacuum.yaml`; FROZEN rev29 `815e08079aef` pins both.
- Sibling used for separation checks only: `artifacts/formulation/schemas/af_scc_c0_vacuum.yaml`
  sha256 `b2ab6acb2bbe`.
- Run: `python3 check_f2a_rev13.py --out results.json` → 24 PASS / 0 FAIL / 4 WARN, exit 0.

The harness never writes outside this directory and re-hashes every input at entry and exit
(zero drift, check C28). It implements the frozen `rule_spec.json#40f9bb9e657b` rules R01–R16
for F2a plus class-separation, sibling-symmetry, containment-licensing and registry-consistency
checks that are not part of the lead's own tooling.

The four WARNs are non-blocking traceability/bookkeeping items, recorded in
`reviews/F2a-review-18-rev13.json`; they are not class-semantics errors.
