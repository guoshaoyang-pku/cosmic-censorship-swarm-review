# W069-F2B-ACCEPTANCE-REBIND-COVERAGE-01

**Worker:** worker-069 · **Node:** F2b · **Class:** `AF-SCC-C0-VAC-GEN` · **Gate:** G-FORM
**Pins:** FROZEN rev29 `815e08079aefbc`, F1 `d9cebb9404b2`, F2a `e9a27996dfd3`, F2b/C0 `b2ab6acb2bbe`
**Verdict:** `PREFLIGHT_CLEARED_BY_REBIND__PASS_BLOCKED_ONLY_BY_REC41_STAGEB_R03`
**Pre-registered run verdict:** `REBIND_INSUFFICIENT_AT_MEASURED_BASE` (P4 required exit 0; 0 union escapes)
**Not a gate verdict, not a node transition, no canonical write.**

## Question

Controller pass-08 authorized one rev14 revision whose item (7) is the *acceptance-corpus rebind*
(CF-32, REC-36). Before it lands: does regenerating the rebased semantic-escape corpus with the
**pinned** generator at the live C0 base restore `ACCEPTANCE: PASS`, or does a content-level union
escape survive the rebind? (A byte move voids every current verdict, so a wrong rebind is expensive.)

## Result

| step | measurement |
|---|---|
| baseline sandbox, pinned fixture | `run_acceptance.py` exit **3**, `PREFLIGHT FAIL: rebased fixtures are stale`, corpus base `1bb78ce9b357` vs current base `b2ab6acb2bbe`; no report written |
| rebind (pinned `measure_semantic_escape.py` `c6e4f9cc`) | exit 0; fixture base **== live C0** `b2ab6acb2bbe`; 31 mutants, 1 unparsed, 0 control false positives, 33 files; **byte-identical across two independent sandboxes** (`sha256` match) |
| acceptance after rebind | preflight **cleared** (no longer exit 3); exit **1**, verdict FAIL; mutants **31/31**, `union_caught 31/31`, **0 union escapes**; controls 2/2 OK; canonical F2a/F2b OK |
| why FAIL remains | canonical **F1 `af_wcc_vacuum.yaml` fails stage-B with `failed_rules = ["R03"]`** on its untouched frozen bytes; all three canonical schemas pass the structural stage. This is the **REC-41** literal-substring binder defect (`astra-life08-stageb-r03`, worker-006), independent of the corpus |

So the authorized rebind **does** close the CF-32(i) preflight/regeneration defect and the reborn
corpus catches all 31 mutants by the two-stage union — but it is **not sufficient alone** for
`ACCEPTANCE: PASS` at these pins: the second CF-32/REC-41 blocker (stage-B R03 on F1) must land in
the same rev14 window, and then the pipeline must be re-run.

## Controls (all in sandboxes, live tree read-only)

- **CTL-1** baseline reproduces the live preflight failure text exactly.
- **CTL-2** one hex character flipped in the fixture's declared `base_sha256` still fails preflight and names the flipped hash → the field is read, not hard-coded.
- **CTL-3** regenerated sandbox passes preflight (precondition of the acceptance re-run).
- **CTL-4** regeneration reports exactly 1 unparsed mutation, matching the pinned fixture.
- **CTL-5** pin-guard helper self-test (correct hash accepted, wrong hash rejected).
- **CTL-6** deleting one mutant in a throwaway regenerated sandbox moves `mutants.total` 31 → 30, so the generated `rebased_fixtures/` directory is **load-bearing**; at these pins the run still FAILs on the independent F1/R03 blocker, so fail-closed behaviour could not be discriminated (see addendum A5).
- **CTL-7/CTL-8** fixture determinism across sandbox A/B; all 16 pinned live inputs and the live `rebased_fixtures/` listing unchanged before/after.

## Addendum — cause decomposition (`addendum_cause_decomposition.json`)

- stage-B on frozen bytes: F1 `reject R03`; F2a `accept`; F2b `accept`; structural stage F1/F2a/F2b `pass`.
- stage-B non-vacuity: accepts frozen F2a/F2b, rejects a pinned mutant it is recorded as catching (`struct01_composite_regularity.yaml`, `R06/R13`), rejects mangled canonical copies.
- **A6 conditional prediction (pre-registered here, before the fix lands):** adopted rebind + an adopted stage-B fix that makes the untouched frozen F1 pass stage-B (without degrading other rules) ⇒ sandbox `ACCEPTANCE: PASS` with canonical 3/3, controls 2/2, mutants 31/31, union 31/31. Falsifier: a post-fix sandbox run still exits non-zero or moves any row.

## Governance findings (measured, advisory)

1. `artifacts/formulation/evidence/rebased_fixtures/` (33 generated mutants, ~1 MiB) is read by `run_acceptance.py` at run time but **no hash in `FROZEN.files` covers its contents**. The rebind should re-pin the directory listing hash together with the fixture, or acceptance totals are not bound by any pin.
2. Stage-2 auditor `artifacts/worker-06/spec_conformance_audit.py` and its manifest are **not in `FROZEN.files`**; they are only *transitively* recorded inside the pinned fixture (`w06_sha256`, `corpus_manifest_sha256`), which does bind them today but makes the pin chain indirect.
3. `schemas/af_scc_c0_vacuum.yaml.sha256` is a stale, unbound sidecar (declares the rev11 `1bb78ce9b357`); no pipeline tool reads a `.sha256` sidecar (static scan), so it is hygiene, not a blocker.
4. `artifacts/formulation/FROZEN.json` is the pin root and is excluded from its own files map by design (`self_reference`); the census classification is annotated accordingly.
5. The pinned `acceptance_pipeline_report.json` (`9b7d6c82`, records PASS / union 31/31) predates the rev13 F1 byte move and cannot be regenerated from live bytes — consistent with CF-32; the report is not evidence at the current pins.

## Binding census at the pins

13 of 16 inputs are directly `FROZEN.files`-pinned; 2 (stage-B auditor, fixture manifest) are
transitively bound inside the pinned fixture; 1 is the pin root; the generated fixtures directory
is unpinned (finding 1).

## Falsifier

Re-run `check_rebind_coverage.py` on byte-identical pinned inputs. Falsified if (a) the baseline no
longer exits 3 or names different hashes; (b) the regenerated fixture does not bind live C0 or is not
byte-deterministic across the two sandboxes; (c) any recorded predicate flips on the same bytes;
(d) `ACCEPTANCE: PASS` is reached but a mutant recorded as caught is actually an escape; or (e) any
pinned input differs at re-measurement (drift voids the binding, not the checks).

## Reproduce

```bash
cd <repo>
python3 artifacts/worker-069/f2b_acceptance_rebind_coverage/check_rebind_coverage.py
python3 artifacts/worker-069/f2b_acceptance_rebind_coverage/addendum_cause_decomposition.py
```

Determinism: `report.json` `run_digest e31af21fc62a0910…` (re-run into a separate output directory
reproduces the whole report byte-for-byte). The addendum embeds tool `audited_at` fields and is not
claimed byte-deterministic.

## Artifacts

| path | role | sha256 |
|---|---|---|
| `PREREGISTRATION.json` | rules/predicates/controls fixed before the run | `7d581a2d4ae5…` |
| `check_rebind_coverage.py` | pre-registered instrument | `54fe8e6527d7…` |
| `report.json` | full machine verdict (`run_digest e31af21fc62a…`) | `98969c3660f2…` |
| `addendum_cause_decomposition.py` | causal decomposition instrument | `c8f75e0c6c56…` |
| `addendum_cause_decomposition.json` | decomposition + A6 prediction (`run_digest 5288539f6d69…`) | `a1bd41103f48…` |
| `sandbox_base/`, `sandbox_rebind_a/`, `sandbox_rebind_b/`, `sandbox_ctl2_fieldflip/`, `sandbox_ctl6_deleted_mutant/` | retained sandbox states (pinned copies + regenerated fixtures) | see `SHA256SUMS` |
| `raw/` | per-step outputs, pin snapshots, bodies | see `SHA256SUMS` |
| `CHECKPOINT.json` | bounded-lifecycle checkpoint | see `SHA256SUMS` |
| `SHA256SUMS` | hashes of every file in this directory | — |

## Non-claims

No mathematics claim; no physics claim; no gate verdict, node status or validation promotion; no
canonical file written, repaired or re-pinned. The REC-41 R03 attribution is reported as the
measured failing rule, not as an adjudication of worker-006's fix. Binds only the pins above.
