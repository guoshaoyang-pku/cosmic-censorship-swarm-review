# W098-CLASSSEP-MENTION-SCOPE-01 — prose-scope repair candidate for the CLASSSEP detector

**Worker:** worker-098 · **Node:** A1 · **Gate:** G-AUDIT · **Classes:** AF-WCC-VAC-GEN,
AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN · **Task:** self-taken bounded execution task.

## Question

The canonical detector `research_map/class_separation.py#a8c04fc31e4a` still emitted 17 hard
findings on the live map, all metalinguistic mentions of the C0/C2 composite (CF-16 pattern),
and only 1/4 of the proposal's declared false-positive probes was clean. My previous pass
(`runtime/state/w098_classsep_prose_shadow_checkpoint_2.json`) left the blocker: extend the
skip predicates to the residual mention shapes without suppressing genuine merge assertions.

## What was done

A **prose-only, clause-scoped** candidate derived from the live detector by insertion only
(0 removed lines; declaration mode untouched). Rules: clause-scoped negation (with
idiom/contrast cancels), contrastive negation (`rather than a C2/C0 merge`), split/rejection
cues in the composite's own clause, mention-object and mention-frame predicates, quoted
composites, numeric zero-count negation, and a re-assert guard so a first-order assertion
(`... are one class`) is not swallowed by the live meta-quotation skip.

Measured v1 → v2 → v3 against a **pre-registered** battery: the 27-fixture worker-07
regression corpus, 8 mandatory-clean prose controls, 2 true-positive controls, 12
mandatory-fire adversarial merge controls, 5 detector-discussion growth probes, 10
declaration-mode parity controls, and the live map. The staged candidate
`proposed/class_separation.py#e2d24b927ee8` was measured as a comparison arm.

| arm | corpus | clean FP fires | genuine-merge fires | growth | live-map hard |
|---|---|---|---|---|---|
| live `a8c04fc31e4a` | PASS | 7/8 | 11/12 | 5/5 | 17 |
| staged `e2d24b927ee8` | PASS | 8/8 | 12/12 | 5/5 | 22 |
| candidate v1 `d88eb425d9a0` | PASS | 1/8 | 10/12 | 1/5 | 5 |
| candidate v2 `3bd684035fc1` | PASS | 0/8 | 11/12 | 0/5 | 2 |
| **candidate v3 `6f1a24c441fb`** | **PASS** | **0/8** | **12/12** | **0/5** | **0** |

All nine pre-registered acceptance criteria hold for v3 (A1–A9), including 10/10
declaration-mode parity with the live detector and insertion-only provenance (+109/−0).
v1/v2 measurements are kept as the honest measured sequence; their defects and the post-hoc
rule fixes are listed in `build_manifest_v2.json` / `build_manifest_v3.json`.

## Files

- `pre_registration.json` — task, pins, candidate spec, controls, acceptance, falsifier.
- `build_candidate.py` / `_v2.py` / `_v3.py` — derived builders; assert insertion-only.
- `candidate_class_separation.py` / `.v2.py` / `.v3.py` — the shadow detectors.
- `run_battery.py` — v1 battery; `run_battery_final.py` — four-arm final battery.
- `raw/candidate_battery.json`, `raw/candidate_battery_final.json` — raw measurements.
- `report.json` — findings W098-CMS-01…07, evidence refs, falsifier, attribution.

## Non-claims / handoff

Not a gate verdict, not a node status, no canonical write. Clearing a claim with the
instrument does **not** retire the claim; retirement stays with the controller/lead. The
remaining blocker is on the canonical side: adopt an equivalent fix at a pinned hash,
re-run `runtime/bin/classsep_regression.py` and `research_map/audit_evidence.py`, and get an
independent reviewer at the unchanged detector hash. The candidate binds to
`a8c04fc31e4a`; rebase if the canonical moves.
