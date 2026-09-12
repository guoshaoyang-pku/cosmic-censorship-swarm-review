# worker-045 — C8 gate-binding verification (2026-09-12T00:27:57+08:00)

Task `W045-C8-BINDING-VERIFY` · class `AF-WCC-SCALAR-SPH` · node `N0` · gate `G-NUM`.

**Verdict: BINDING-DEFECT-CONFIRMED.** The G-NUM reason "binds unbound (stale)" is a pin-field mismatch, not a missing verdict:
`reviews/G-NUM-protocol-review.json` (accept 4.5, `counts_as_full_schema_verdict=true`) pins the
current protocol hash via `reviewed_sha256` (`1e6cdf04d7a2`), while
`research_map/astra_lifecycle.py:259` reads only `artifact_sha256` from that file. The
controller's own `_explicit_pins()` convention binds the verdict, and 2
independent accept(s) at the current hash exist on disk.

- Full measurement: `c8_binding_verification.json` (sha256 `72b17556490392a3ba1c49a78cb48855126fd324f5e47bfa2faa6ca45c9516c0`)
- Reproduce: `python3 artifacts/worker-045/run_c8_binding_verify.py`
- Falsifier: see `falsifier` in the JSON.
- Scope: read-only; no gate verdict, no node completion, no physics claim.
