# W087-F0-CLOSURE-CHECK-02 — independent closure verification of the three blocking F0 findings

worker-087 · node **F0** · gate **G-F0** · classes `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`,
`AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH` · 2026-09-12T00:34+08:00

## Verdict

**`BLOCKING_FINDINGS_CLOSED_AT_0abb9ed8a961`** — at the frozen canonical F0 revision
`research_map/formulation_taxonomy.yaml` sha256 `0abb9ed8a961…` (rev5, `FROZEN.json` revision 27),
the three blocking findings raised against rev4 are mechanically discharged by an independent
instrument, and the instrument's negative control shows it still detects the defect when the
pre-rev5 wording is re-introduced.

| finding | raised by | decided by | status at rev5 |
|---|---|---|---|
| **B-16F0-1 / W082-F-01** — demoted set-based visibility wording, bare generic quantifier, unsourced "equivalently" clause in `AF-WCC-SCALAR-SPH` | worker-16, worker-082, astra-lead-audit | CL1, CL2, CL3 | **CLOSED** |
| **B-16F0-2** — `resolved_divergences[D3]` claims the comeager quantifier for each class, not discharged for `AF-WCC-SCALAR-SPH` | worker-16, worker-082 | CL4 | **CLOSED** |
| **B-16F0-3** — C2/C0 `provenance.schema_owner` targets legacy `schemas/af_scc_regularities.yaml` and superseded node `F2` | worker-16 | CL5 | **CLOSED** |

This is targeted closure evidence, **not** a full-schema review, **not** a gate verdict, and
**not** a node-status change. Two independent full-schema accepts at the frozen hash are still
required for G-F0.

## What was blocking at rev4 (`276009f4f63d`)

Measured with this instrument at the rev4 pin: exit `3`, `CL1`–`CL5` all `OPEN`, invariants
`INV1`–`INV4` passing. The rev4 `AF-WCC-SCALAR-SPH` conclusion read:

> For generic data in the class, the MGHD admits I+ and every future-inextendible causal geodesic
> contained in J-(I+) is complete; equivalently, the singularities that form are hidden behind an
> event horizon and no singularity is visible from I+.

That is the set-based `J-(I+)` reading that D1 demoted to variant `SET` of `AF-WCC-VAC-GEN`, a
bare generic quantifier while the class's `genericity_kind` is `unresolved`, and an unsourced
equivalence. The sibling WCC class (`AF-WCC-VAC-GEN`) had already been repaired, so the repair was
incomplete across classes. Separately, D3 asserted the comeager quantifier "in each class
conclusion text" and the two SCC `schema_owner` pointers named a legacy non-class aggregator and
the superseded node name `F2`.

## What rev5 changed (`0abb9ed8a961`, written 00:31:41; FROZEN rev27 at 00:32:59)

The formulation lead's own revision note states the claim; this bundle verifies it:

> rev5 closes the content-bearing F0-review-lead-audit-r2 blocking findings: (f) the
> AF-WCC-SCALAR-SPH conclusion no longer carries the demoted set-based visibility reading; it now
> states the single-q tail predicate with the comeager set bound before the data (worker-16
> B-16F0-1 / worker-082 W082-F-01); (g) the D3 resolution is confirmed discharged for the scalar
> class (B-16F0-2 / W082-F-02); (h) C2/C0 provenance.schema_owner pointers now name the canonical
> class schemas and the F2a/F2b node ids instead of the legacy `schemas/af_scc_regularities.yaml`
> and the superseded node name F2 (B-16F0-3). No class id added; class_ids unchanged.

The new conclusion states a comeager set chosen before and independently of the data, defines
non-visibility by the single-q tail predicate (`tail gamma([t0,T))` not contained in `J^-(q)∩M`),
and records that the superseded set-based wording is variant `SET`, not this class's predicate.

## How closure is decided (instrument, not prose)

`accept_f0_closure.py` is a standalone verifier (stdlib + PyYAML only; it does not import
worker-16's `check_f0.py`, worker-082's tooling, flash-02 tooling, `class_separation.py` or
`audit_evidence.py`). It parses the target, applies sentence-level detectors, and emits a machine
report. Exit codes: `0` closed, `3` open, `1` controls failed (result invalid), `2` drift
(fail-closed, no JSON written).

| check | decides | mechanism at rev5 |
|---|---|---|
| CL1 | B-16F0-1a D1 residue | No class conclusion assertively carries the set-based `J-(I+)`/union-of-`J^-(q)` reading; both WCC classes carry the single-q tail predicate; SCC classes carry none. The hyphenated `contained-in-J-(I+)` mention in rev5's superseding note is classified as a disowning sentence, not an assertion. |
| CL2 | W082-F-01(b) unsourced equivalence | No sentence asserts `equivalently`/`equivalence` without a disclaimer. `AF-WCC-VAC-GEN`'s "not an asserted equivalence" is a disclaimer and is correctly not flagged. |
| CL3 | W082-F-01(a) bare generic | A class with `genericity_kind: unresolved` must bind the deferral explicitly; rev5's scalar conclusion names the unresolved genericity datum instead of bare "for generic data". |
| CL4 | B-16F0-2 D3 discharge | Every class conclusion either states a comeager binder or is covered by a named deferral in D3's scope note. Rev5 states the binder for all four. (The named-deferral branch is exercised by the historical rev4 repair candidate below.) |
| CL5 | B-16F0-3 ownership | Each `schema_owner` must name the schema that itself declares that `class_id`/`node_id` and must not be in the map's `legacy_artifacts`. Rev5 resolves to `F1`/`schemas/af_wcc_vacuum.yaml`, `F2a`/`schemas/af_scc_c2_vacuum.yaml`, `F2b`/`schemas/af_scc_c0_vacuum.yaml`; the scalar class declares its coverage gap. |
| INV1–INV4 | regression | exactly the four frozen class ids; axis values vocabulary-legal with 6/6 disjointness pairs differing on a decisive axis; no duplicate YAML mapping keys; no merged C0/C2 spelling in a conclusion. |

**Controls (5/5 PASS, fail-closed).** Known-good tail conclusion not flagged; known-bad set-based
conclusion flagged on all three detectors; proposed fixed text clean; schema-owner parser
distinguishes the legacy pointer from the canonical one; duplicate-key detector catches a
duplicate and clears a clean document.

**Negative control (end-to-end).** `make_regression.py` restores the pre-rev5 scalar conclusion
into the current bytes (`regression_check.yaml`); the verifier then exits `3` with `CL1`–`CL4`
open. This is what makes the `CLOSED` verdict on rev5 meaningful: the same instrument still sees
the defect when it is present.

**Drift control.** Wrong `--pin` exits `2` and writes no JSON (fail-closed).

## Pin / publication state captured at bundle time (00:34:43)

- canonical `0abb9ed8a961…` **equals** the `FROZEN.json` rev27 pin; `frozen_at` 00:32:59 is later
  than the file's `written_at` 00:31:41.
- map `publication_status` classifies the canonical taxonomy and the authoring class-contract
  supplement as **`companion-pinned`** (astra-life04 adjudication REC-3: distinct artifacts, each
  hash-pinned and consistency-checked; byte-identity is not the requirement). CL6 therefore passes
  as an adjudicated companion pair.
- map gate audit at 00:33:16 still records G-F0 `pending` with **0 accepts** at `0abb9ed8`; the
  taxonomy's own `status` field is still `draft_unverified`.

## Historical: the worker repair candidate (superseded, kept as provenance)

Before rev5 landed, this worker built a minimal repair candidate from rev4
(`formulation_taxonomy.candidate.yaml`, sha256 `6207dfc0…`) with four anchored, reversible edits
(E1 conclusion, E2 D3 scope note, E3/E4 schema owners; semantic diff exactly five leaf paths) and
verified it closes `CL1`–`CL5` with all invariants and controls passing (`make_candidate.py`,
`candidate.diff`, `candidate_edits.json`). The lead's rev5 wording supersedes it — the lead owns
class semantics — but it is retained as the provenance of the intended minimal repair and as the
fixture that exercises the CL4 named-deferral branch.

## Lead-side remainder (reported, not decided here)

1. **CL7 — corpus binding status.** The `schemas/taxonomy_cases.jsonl` meta pin is now
   `0abb9ed8`, but all 36 case records still carry
   `binding_status: bound_taxonomy_sha_66bf917bd368` (a superseded F0 hash). Owner
   `astra-life03-repin-claims`.
2. **G-F0 accepts.** Two independent full-schema accept verdicts at the frozen `0abb9ed8` hash are
   still required; this bundle is not a review verdict.
3. **Bookkeeping reconciliation.** FROZEN rev27 still carries
   `f0_mirror_adjudication_request.status = "disposition-recorded-pending-controller-adjudication"`
   while the map records the REC-3 companion ruling; the two records should be reconciled by the
   owner. The instrument follows the map as the sole global state.
4. **Author status.** The taxonomy still labels itself `draft_unverified`; changing that is an
   author/controller decision.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-087/f0_closure_check/run_all.py \
  --expect-pin 0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3
# single-target verification (any revision):
python3 artifacts/worker-087/f0_closure_check/accept_f0_closure.py \
  --target research_map/formulation_taxonomy.yaml --pin <sha256>
```

## Falsifier

Re-run `run_all.py` at the same `--expect-pin`: any expectation not `PASS`, any control failure,
or canonical drift voids the verdict. Independently, a reviewer showing that the rev5
`AF-WCC-SCALAR-SPH` conclusion asserts a visibility predicate not fixed by the class's hypotheses,
or that the comeager binder is not bound before the data, falsifies the B-16F0-1/B-16F0-2 closure
even though the mechanical checks pass. A controller reversal of REC-3 reverts CL6 to
`PENDING`/`FAIL`.
