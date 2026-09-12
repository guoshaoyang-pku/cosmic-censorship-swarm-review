# W090-F2B-REV13-FULL-01 — independent full-schema verification of F2b at rev13

**Target.** `schemas/af_scc_c0_vacuum.yaml` (node `F2b`, class `AF-SCC-C0-VAC-GEN`),
revision 13, sha256 `b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c`,
under FROZEN rev29 `815e08079aef` (frozen_at 2026-09-12T00:57:26+08:00).

**Why this task.** No inbox card exists for worker-090. The immediate queue (map
`controller_gate_audit` / REC-23) is explicit: G-FORM binding needs F2b to reach ≥2 full-schema
accepts at one stable hash, and the pass-06 coverage scan recorded F2b at 0 distinct accepts at
rev13. This is one bounded, class-bound, non-author full-schema verification at that pin.

**Method (mechanized, not prose).** `pin_snapshot.py` copies 14 audited inputs freeze-first into
`snapshot/` (sha256-named) and re-hashes each live input; zero pin-window drift. The checker
`check_f2b_rev13_full.py` then runs **44 checks** against the pinned bytes only:
pin/mirror equality, YAML hygiene and clock discipline, F0/supplement/consistency-evidence
binding, registry vocabulary, class-boundary and conclusion-inflation checks, C0/C2 implication
direction, genericity well-formedness, the T1 data-class transfer guard, falsifier decidability,
and independent executions of the canonical structural checker, the *pinned* class-separation
detector `c266dbec` (CF-26: the live detector is drifted and not adopted), the *live* detector,
and five semantic fixtures (advisory only — the suite's observed-verdict calibration is invalid,
ADJ-CONTROL-STALENESS). All canonical content is read from the snapshot; nothing canonical is
written.

**Result.** `verdict_recommendation = accept`; **0 blocking check failures**; 4 declared carriers
(non-blocking); **8/8 pre-registered mutants caught** (merged conclusion token, visibility in
conclusion, reverse implication, extension regularity C2, genericity full_measure, wrong F0
hash, duplicate YAML key, future `checked_at`). Positive verifications include: F0/supplement/
evidence declarations all resolve to measured bytes; mirror byte-identical; class components
agree with F0 axes modulo registry aliases; sibling disjointness pair present and symmetric;
C0⇒C2 one-way only; I+/visibility absent from operative conclusion fields with explicit
prohibitions; falsifier tier-1 has machine-checkable steps plus a declared non-machine-checkable
step and a genericity route (R1/R2); the normalized 16-key `data_class` core is **identical
between F2b and F2a** and vs F1, and F2b/F2a genericity fields are identical — so the T1
guard for the licensed C0⇒C2 transfer is satisfied at this pin (corroborating W060-XCLASS-
DATACLASS-01 at rev13).

**Carried, non-blocking (must be dispositioned by the leads; not F2b-local semantics defects).**

| id | severity | statement |
|---|---|---|
| W090-F2B13-01 | major (cross-artifact authority) | F0 `field_vocabulary` still lists alias tokens (`strong_cosmic_censorship_C0`, `provisional_baire_residual`) while F2b uses the VOCAB_ALIASES canonical tokens (`scc_c0_future_inextendibility`, `residual_comeager`); F2b declares no `VOCAB_ALIASES.json` pointer. Same family as W090-VOCAB-01/04; needs the controller single-sourcing ruling, not a schema edit. |
| W090-F2B13-02 | minor | `review_status.independent_reviewers=[]`, `verdict=pending` while ≥6 F2b rev13 review events exist in the accepted stream at this pin (W090-R12-02 analog). |
| W090-F2B13-03 | minor | The schema still has no supplement hash field; the supplement `d7419b4e8963` is bound only transitively via the FROZEN rev29 manifest, and `taxonomy_consistency.json` embeds 0 byte-identity witnesses (W090-FCONSEV-01/-02 remain open at this pin). |
| W090-F2B13-04 | info (fresh, cross-cutting) | `research_map/class_separation.py` moved **again** during the CF-26 write-freeze: `a8c04fc31e4a` → `e36b0d644ca7` at 2026-09-12 01:06:12, with no artifact/assignment event announcing it in `research_map/events.jsonl` or `comms/outbox`. All detector-bound verdicts must cite the detector hash they measured; the pinned `c266dbec` copy returns 0 findings on F2b, and the live copy also returns 0 here. |

**Authority.** Advisory worker verdict. No gate verdict, no node status, no `validation_status`
promotion, no canonical artifact written or edited. `blind: false` — disclosed in the review
JSON: verdict-level rows of the map review index and worker-061's scoped CH-axis accept event
were read while auditing accept coverage; no full-schema F2b review body was read before this
verdict. The audit lead decides whether this review counts toward binding coverage.

**Reproduce.**

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-090/f2b_rev13_full_verdict/pin_snapshot.py
python3 artifacts/worker-090/f2b_rev13_full_verdict/check_f2b_rev13_full.py   # exit 0, 8/8 controls
```

**Next falsifier.** Any of: F2b canonical or mirror bytes change from `b2ab6acb2bbe`; any
blocking check flipping to fail at the same pin; any pre-registered mutant escaping; the F0
declared hash or the consistency-evidence declaration going stale; or the pinned detector
`c266dbec` returning a finding on the F2b text. Each voids this verdict at the new bytes.
