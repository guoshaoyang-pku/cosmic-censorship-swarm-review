# W029-F1-R03-CAND-SCOPE-SAFETY-01 — scope-safety of the two F1 R03 repair candidates

**Actor:** worker-029 (bounded execution worker; no inbox card — self-selected from the live
G-FORM blocker `lead-form-20260912T011509-122/123`).
**Class:** `AF-WCC-VAC-GEN` · **Node:** F1 · **Gate:** G-FORM.
**Status:** complete at worker level; read-only on every canonical path. Not a gate verdict.

## Question

The formulation lead measured (lifecycle-08, `lead-form-20260912T011509-121/122`) that the
**tool-side** variable-wise R03 patch `cand_E3 3f69bc1eb27a` accepts a negation-scope-error
rendering. worker-062 proposed two **schema-side** one-line repairs for the same R03 false
positive. Neither had been scope-probed. Do they preserve the frozen R03 guard's ability to
reject a scope-erroneous rendering and a free-`t0` rendering?

## Pins (all measured T0 and T1, zero drift)

| path | sha256 |
|---|---|
| `schemas/af_wcc_vacuum.yaml` (F1 rev13) | `d9cebb9404b2…` |
| `artifacts/worker-06/spec_conformance_audit.py` (frozen stage-B) | `c79d8ab8440a…` |
| `artifacts/formulation/rule_spec.json` | `40f9bb9e657b…` |
| `artifacts/formulation/FROZEN.json` (rev29) | `815e08079aef…` |
| `…/candidates/CAND-A_af_wcc_vacuum.yaml` | `bf1798b57997…` |
| `…/candidates/CAND-B_af_wcc_vacuum.yaml` | `ebb8d6671614…` |
| `…/cand_E3/artifacts/worker-06/spec_conformance_audit.py` | `3f69bc1eb27a…` |
| lead variants G / S (`tmp/lead-form-life08/`) | `1d9f06f02d3a…` / `7663d4bc0a58…` |

## Method

For each notation base — canonical, CAND-A, CAND-B — replace only the text after the unique
anchor `with finite affine length: ` in `quantifiers.formal`, keeping the base's own
`quantifiers.ordered` rows and D5 unchanged. Four tails:

| tag | rendering |
|---|---|
| **G** | grouped tuple, intended correct: `not exists (q,t0) in I+ x [0,T) with …` |
| **V** | variable-wise, intended correct (canonical bytes): `not exists q in I+ and t0 in [0,T) with …` |
| **S** | scope error, negation binds `q` only: `not exists q in I+ with …, and t0 in [0,T).` |
| **U** | free `t0`, no `t0` restriction: `not exists q in I+ with …` |

Tool invocation is exactly the frozen pipeline's (`run_acceptance.py`): the auditor is called
with the schema path only, and the verdict is read from the stdout JSON body. A
`--json`-file cross-check agrees on every cell.

## Result matrix (frozen auditor `c79d8ab8440a`)

| variant | verdict | failed rules |
|---|---|---|
| CANON + V (own bytes) | reject (known false positive) | R03 |
| CANON + G | accept | — |
| CANON + S | reject | R03 |
| CANON + U | reject | R03 |
| CAND-A + G / V / S / U | accept / **reject** / **reject** / **reject** | — / R03 / R03 / R03 |
| CAND-B + G / V / S / U | accept / accept / **accept** / **accept** | — / — / — / — |

All 12 cells matched the pre-registered expectations; no mismatch.

## Findings

- **W029-SCOPE-02 (blocking-for-CAND-B).** CAND-B (`ebb8d6671614`) changes
  `quantifiers.ordered[5].binder` from `(q,t0)` to `q`. R03 is a literal substring test
  (`binder in formal`), so the binder `q` is satisfied by *both* the correct variable-wise
  rendering and the scope-error rendering S (and by U, where `t0` is free). The repair closes
  the false positive by weakening the guard: the frozen R03 no longer separates correct from
  scope-erroneous. Independently, the ordered row now under-binds `t0` while
  `D5.definition` declares the pair domain `pairs (q,t0) with q a point of I+ and t0 in [0,T)…`
  — a scalar binder over a pair domain.
- **W029-SCOPE-03 (informational).** CAND-A (`bf1798b57997`) rewrites `quantifiers.formal` to
  the grouped tuple and keeps `ordered[5].binder = (q,t0)`. It is scope-safe on this probe:
  S and U are rejected exactly as under canonical bytes, so the false positive is closed
  without weakening the scope guard.

**Decision input for the owner:** at the current pins, prefer **CAND-A** as the R03 repair.
Do not land **CAND-B** as an R03 repair without (i) repairing `ordered[5]` so it binds `t0`
consistently with the unchanged formal sentence and D5's pair domain, and (ii) adopting a
scope-aware R03 rule (the tool-side question the lead's E3 probe left open).

## Controls (all pass)

| id | control | result |
|---|---|---|
| K1 | CAND-B with `ordered[5].kind` invalid → must reject | reject/R03 |
| K2 | every cell run twice; verdict+rules+exit identical | 13/13 deterministic |
| K3 | all nine pins re-measured after the run | 0 drift |
| K4 | recursive leaf-diff canonical→candidate = exactly one declared leaf | CAND-A `quantifiers.formal`; CAND-B `quantifiers.ordered.5.binder` |
| K5 | E3 tool `3f69bc1eb27a` reproduces the lead's published matrix (frozen reject / grouped accept / scope-error accept) | 3/3 match |
| K6 | stdout parse vs `--json` file | 13/13 agree |

Disclosed post-hoc supplement (`supplementary_published_bytes_check.py`, run after the
pre-registered matrix, no expectation changed): the frozen and E3 auditors were run directly on
the lead's **published** variant bytes (`tmp/lead-form-life08/variant_*.yaml`, all three pins
match) and reproduce the lead's published matrix row-for-row — frozen reject/accept/reject, E3
accept/accept/accept. K5 above had exercised re-serialized equivalents of the same text.

## Falsifier and outcome

Pre-registered falsifier (`PREREGISTRATION.json`): re-running the harness at the same pins
falsifies the result if CAND-B+S or CAND-B+U is rejected, if CAND-A+S or CAND-A+U is accepted,
if either candidate's own bytes fail, if any declared pin moves T0→T1, or if the recursive
one-line diff does not match the declared leaf.
**Outcome: NOT FALSIFIED.**

## Scope limits / non-claims

Stage-B R03 only. The full two-stage acceptance pipeline, corpus rebind, stage-A gate and the
G-CLASSBIND escape measurement are out of scope. This is not a full-schema G-FORM verdict, does
not consume a reviewer slot, does not set gate/node status, and claims no mathematics.

## Reproduction

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-029/f1_r03_scope_safety/run_f1_r03_scope_safety.py
# exit 0 = valid run; writes report.json / evidence.json / controls.json
```

Artifacts: `PREREGISTRATION.json`, `run_f1_r03_scope_safety.py`, `supplementary_published_bytes_check.py`,
`report.json`, `evidence.json`, `controls.json`, `supplementary_published_bytes_check.json`,
`variants/`, `raw/`, `CHECKPOINT.json`, `SHA256SUMS`.
