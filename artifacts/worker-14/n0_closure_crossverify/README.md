# W014-GNUM-N0-CLOSURE-CROSSVERIFY-01 — README

**Verdict:** `N0_CLOSURE_AND_FIRST_REVIEW_CROSSVERIFIED_ACCEPT` (worker-level, read-only).
**Class:** AF-WCC-SCALAR-SPH · **Node:** N0 · **Gate:** G-NUM · **Worker:** worker-014.

## Why this task

No inbox card existed for this worker-014 instance (recycled slot). One bounded, class-bound task was
taken from the open N0 evidence need (`astra-life04-n0-verify`): a **second**, independently
implemented read-only verdict on the freshly landed N0 stop-rule closure package, which the
lead-audit must adjudicate.

- **T1** `numerics/protocol/lifecycle08_stoprule_closure_verify.json#88ec0bf298cb` (author:
  astra-lead-numerics, generated 01:13:11).
- **T2** `reviews/N0-stoprule-closure-review-worker-017.json#87b311e72032` (first independent
  review, worker-017, 01:15:50).

`artifacts/worker-017/…/verify_n0_closure_017.py` was hashed as an evidence pin but **not read**;
the instrument here is a separate re-implementation. No canonical or other-agent artifact was
written; every input was read-only and re-hashed before and after the run.

## Result

20/20 checks ok, 0 flags, 12/12 negative controls fired, 21/21 pinned inputs byte-stable pre/post,
byte-identical report on re-run.

| check | result |
|---|---|
| X1 closure metadata | schema `n0-stoprule-closure-verify/v1`, class/node/gate correct, `all_closure_items_closed=true` |
| X2 independent LSQ | own fit over raw cert rows reproduces cert, rev3 and closure to **0.0e+00** worst abs diff (3 schemes × 8 quantities) |
| X2 rungs | 3 schemes × 4 rungs, `dt=1e-4`, `dr=[0.2,0.1,0.05,0.025]` |
| X3 bands | `|p−2|` = 1.36e-4 / 8.37e-5 / 5.68e-5 ≤ 0.3; all ladders monotone; spread 7.958116929374093e-05 ≤ 0.25 and equals closure value to 1e-15 |
| X4 F0 rebind | live taxonomy `0abb9ed8a961` rev5 with `AF-WCC-SCALAR-SPH`; authority `effd20b0ea09` binding/carrier agree |
| X5 replication | module `8ade1cdc163e` cert+disk; w046 `SUPPORTED`, w057 `REPRODUCED`, w081 `accept`; flash-13 accept 4.0 binds rev3 `da7c36071995`, discloses F-06 |
| X6 lock | `numerics_lock.state=locked`, no `numerics/spherical_solver/`, `gates.evaluate` → `production_allowed=false` |
| X7 registration | closure `known_pins`: 6 registry-match, 1 top-level-match, 3 unregistered, 0 mismatch; stale pin disk `8137f18f1a3b` confirmed |
| X8 first review | T2 bytes match its declared hash; 4/4 sub-refs resolve; pinned copy byte-identical to live T1; all 7 findings consistent with my measurements |
| X9 controls | 12/12 (perturbed error, moved rung, reversed ladder, substituted F0 hash, planted solver, tightened R5, flipped token, empty class list, stale-pin mismatch, bogus registry path, pinned-copy change, moved review hash) |
| X10 drift | no input drift during the verification window |

**Advisories (non-blocking, reproduced/confirmed):**
1. T1 labels `research_map/formulation_taxonomy.yaml` as `unregistered`; it is in fact
   `top-level-match` in `runtime/state/artifact_hashes.json#hashes` (same sha). Documentary
   refinement of worker-017's crosscheck; no gate logic depends on it.
2. The three reviewer-verdict artifacts (w046/w057/w081) remain genuinely unregistered.
3. The carried stale pin `reviews/G-NUM-protocol-review.json#1e6cdf04d7a2` (disk `8137f18f1a3b`)
   is a mispin of the reviewed protocol hash; already recorded by T1.
4. A clean N0 accept is still blocked by the contested protocol review (B-N0-R2-2) and the
   registration gap; G-NUM stays pending regardless of this cross-verification.

## Reproduction

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-14/n0_closure_crossverify/verify_n0_closure_x.py \
        --out artifacts/worker-14/n0_closure_crossverify/report.json   # exit 0
sha256sum artifacts/worker-14/n0_closure_crossverify/report.json
```

Any deviation flips the verdict to `REVISE` (falsifier in `PRE_REGISTRATION.md` and in the report).
A later write to any pinned path voids this verdict for the new bytes.

## Does not claim

No G-NUM gate verdict, no N0 node transition, no lock release, no B-N0-R2-2 adjudication, no
canonical write, no physics / self-gravity / WCC / SCC claim. Worker-level evidence for the
lead-audit only.
