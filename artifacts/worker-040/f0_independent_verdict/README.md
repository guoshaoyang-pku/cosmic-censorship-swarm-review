# W040-F0-INDEP-VERDICT-01 — independent F0 verification (worker-040)

**Task.** One bounded class-bound task, no assignment card existed for worker-040 in
`comms/inbox/`. Independent, hash-bound verification of the declared F0 taxonomy
`research_map/formulation_taxonomy.yaml` for the four frozen class ids, in response to the
formulation lead's corrected resource request (independent reviewer at the final hashes).

**Target (bound).** `research_map/formulation_taxonomy.yaml`
sha256 `276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc` (revision 4).
Verdict **accept, score 4.0**, no hard failures, three soft/process findings. One independent
verdict only — G-F0 still needs a second accept at the same hash.

**What was run (all exits 0; captured in `instrument_runs.json`).**

| instrument | result |
|---|---|
| `research_map/validate_map.py` | VALID |
| `artifacts/worker-01/validate_taxonomy.py` | 253/253 checks, 37 cases, pass |
| `artifacts/formulation/tools/check_taxonomy_consistency.py` | CONSISTENT, 0 contract-text divergences |
| `artifacts/formulation/tools/check_variant_registry.py` | VALID, 4 parents / 7 variants |
| `artifacts/formulation/tools/verify_frozen.py` | FROZEN rev 25, 40 files, 0 problems |
| `class_separation.regression()` | PASS, tp 17 / tn 10 / fp 0 / fn 0 |
| `audit_evidence.audit()` (read-only) | 1 hard (claims[36], controller adjudicated CF-16 false positive) + 1 soft (dual-tree divergence) |

**Independent checks (`independent_checks.json`, written from scratch, no canonical checker
imported).** C1 class set = exactly the frozen four; C2 no unregistered class-id-shaped token;
C3 variant registry covers parents/schema; C4 canonical↔authoring mirror; C5 each schema's
`f0_binding` matches the live F0 hash; C6 `class_contract_pointer` resolves; C7 all six
disjointness pairs documented; C8 no duplicate YAML keys; C9 G-F0 gate evidence refs resolve;
C10 clock discipline.

**Findings.**

1. *soft, process* — canonical and authoring F0 trees are not byte-identical
   (`276009f4…` vs `c8e979a1…`) and use different key schemas; the class contracts agree on
   family/regularity/conclusion/exclusions. Under the canonical-path policy this blocks
   verdict **binding**, not the content.
2. *soft, hygiene* — G-F0's evidence list names `reviews/F0-review-17.json` and
   `reviews/F0-review-19.json`, absent on disk.
3. *soft, interface* — all three canonical schemas point `class_contract_pointer` at the
   authoring mirror, not the declared canonical F0 path (keys resolve, nodes agree).
4. *positive* — the earlier F0 class-token soft flags (`AF-WCC-VAC-GEN-SET`,
   `AF-SCC-C0-CH-VAC-GEN`) are gone at this hash.
5. *known* — the one live hard CLASSSEP finding is claims[36], already adjudicated CF-16.

**Drift guard.** `entry_hashes.json` / `exit_hashes.json`; no tracked file changed during the
run. The verdict is void if the canonical F0 hash differs from `276009f4…` at gate-verdict
time. Re-run `run_checks.py` after any new publication.

**Falsifier.** A fifth class-id-shaped token in `class_ids`, a class contradicting the frozen
contract axes, an unregistered class-id-shaped token, a canonical hash other than `276009f4…`
at verdict time, or the appearance of the two missing gate review files.

No node completion, no gate verdict, no shared file modified.
