# W16-R03-ADJ-01 — adjudication of the stage-2 R03 rejection of frozen F1

**Worker:** worker-16 (slot 016) · **At:** 2026-09-12T00:47+08:00
**Node:** F1 · **Class:** `AF-WCC-VAC-GEN` · **Gate:** G-FORM
**Target:** `artifacts/formulation/schemas/af_wcc_vacuum.yaml` (canonical mirror `schemas/af_wcc_vacuum.yaml`)
**Target sha256:** `cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3` (FROZEN rev28)
**Disposition of:** W16R28-F2 (blocker `w16-REV28-VERIFY-01-blocker`), corroborated by worker-004
`w004-semct-blocker-f1-r03-20260912T0040`.

**Authority note.** This is worker evidence, not a gate verdict. No frozen byte was modified; no node
status or validation status is claimed. Option choice below belongs to the formulation owner / controller.

---

## 1. Question

Stage 2 of the adopted acceptance pipeline (`artifacts/worker-06/spec_conformance_audit.py`,
sha256 `c79d8ab8440ac6738bb61df5a33e9fd5f8319b4e74e1f2e9c0fc5083fb408cec`) rejects frozen F1 while
accepting F2a and F2b. The only failed rule is R03:

```
R03  fail  binder '(q,t0)' absent from formal sentence
```

Is that

* **(a) a real schema defect** — an unbound/missing quantifier, a class leak, conclusion inflation,
  or a C2 assumption smuggled into the C0/WCC class; or
* **(b) a literal-match false positive of the R03 *implementation*** — the frozen formal sentence
  renders the composite binder variable-wise (`not exists q in I+ and t0 in [0,T) with ...`) and the
  checker tests `binder_string not in formal` literally (lines 210–212)?

## 2. Sources (sha256 measured before and after; unchanged)

| source | sha256 |
|---|---|
| `artifacts/formulation/schemas/af_wcc_vacuum.yaml` | `cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3` |
| `artifacts/formulation/schemas/af_scc_c2_vacuum.yaml` | `5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce` |
| `artifacts/formulation/schemas/af_scc_c0_vacuum.yaml` | `55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6` |
| `artifacts/worker-06/spec_conformance_audit.py` | `c79d8ab8440ac6738bb61df5a33e9fd5f8319b4e74e1f2e9c0fc5083fb408cec` |
| `artifacts/formulation/tools/check_class_schema.py` | `000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff` |
| `artifacts/formulation/rule_spec.json` | `40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e` |
| `artifacts/formulation/FROZEN.json` (rev28) | `2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1` |
| `artifacts/formulation/KEY_MANIFEST.json` | `014e2d3019781632cdb78ace266cf08cc11f9cf8b8ef0a049beb74eb9c6b6b9a` |

All runs executed in a staged copy under `artifacts/worker-16/r03_adjudication/{stage,tools}/`.
`immutability.unchanged = true` for every source above.

## 3. What the R03 implementation actually tests

`spec_conformance_audit.py:210–212`:

```python
for b in binders:
    if b not in formal:
        bad.append(f"binder {b!r} absent from formal sentence")
```

F1 declares six ordered binders; the probe (`lexical_probe` in `out/adjudication.json`) shows five
occur literally in `quantifiers.formal` and the sixth does not:

| kind | binder | domain | literal in formal | variable-wise in formal |
|---|---|---|---|---|
| forall | `r` | D0 | yes | — |
| exists | `G_r` | D1 | yes | — |
| forall | `(Sigma,h,K)` | D2 | yes | Sigma/h/K all yes |
| exists | `(Mtilde,gtilde,Omega)` | D3 | yes | all yes |
| forall | `gamma` | D4 | yes | — |
| not_exists | `(q,t0)` | D5 | **no** | q yes, t0 yes |

The frozen formal sentence says:

```
for all future-inextendible causal geodesics gamma ... :
not exists q in I+ and t0 in [0,T) with gamma([t0,T)) subset J^-(q) intersect M.
```

and D5 defines exactly `pairs (q,t0) with q a point of I+ and t0 in [0,T) ...`. So the quantifier does
bind both variables; only the literal token `(q,t0)` is not printed.

## 4. Tests and results (declared before running; `out/raw_verdicts.json`)

| run | stage 1 (R01–R16) | stage 2 baseline | stage 2 hardened | expected |
|---|---|---|---|---|
| F1 frozen (twice, deterministic) | pass | **reject** (R03 only) | reject (R03 only) | reject |
| F2a frozen | pass | accept | — | accept |
| F2b frozen | pass | accept | — | accept |
| **V1** F1 copy, clause re-rendered `not exists (q,t0) in D5 with ...` | pass | **accept** | accept | accept |
| **V2** F1 copy, `(q,t0)` added only in a YAML comment | — | reject (R03) | — | reject |
| **V4** F1 copy, not_exists clause binds neither q nor t0 | pass | reject (R03) | — | reject |
| **P** patched stage-2 tool on frozen F1 | — | **accept**, `doc_sha256 = cce9c60146d6…` | — | accept |
| P on V4 (unbound negative control) | — | reject (R03) | — | reject |
| P on V1 / V2 | — | accept / accept | — | accept |

The V1 edit is one clause; D5 already carries the removed wording, so semantics are preserved
(and stage 1 passes it unchanged). V2 shows the predicate reads the parsed `quantifiers.formal`
field, not raw file text. V4 shows R03 still catches a genuinely unbound quantifier under both the
baseline and the patched implementation — the patch is not a rubber stamp. V4 also passes stage 1,
which is why R03 exists as a separate stage-2 rule.

## 5. Adjudication

**W16R28-F2 is a literal-match false positive of the R03 *implementation*, with one real residual
defect: a cross-schema binder-rendering convention inconsistency.**

* F1's `not_exists` quantifier genuinely binds `q` and `t0`; D5 resolves and defines the pair domain.
* The failure is produced solely by the lexical predicate `b not in formal`. The rule text
  (`rule_spec.json#40f9bb9e657b`, R03: *"quantifiers.formal is a single sentence using those
  binders"*) does not require literal tuple printing.
* A variable-wise implementation of the same requirement accepts the frozen bytes unchanged
  (`doc_sha256` re-reported as `cce9c60146d6…`), so no semantic content changes are needed.
* Not a class leak, not conclusion inflation, no C2 assumption imported, quantifier ordering and
  domain resolution are correct.
* Residual defect: F2a/F2b print composite binders literally, F1 does not; the frozen corpus is not
  uniformly self-presenting under the adopted lexical checker.

### Resolution options (owner/controller decision)

| | option A — amend R03 to variable-wise binder use | option B — one-clause rendering change in F1 |
|---|---|---|
| touches frozen class bytes | no | yes (F1 hash changes) |
| measured effect | frozen F1 accepted; V4 still rejected; F2a/F2b unaffected | both stages accept; semantics preserved |
| consequence | tool revision versioned + hash re-pinned; G-FORM evidence re-run at the new tool hash | HOLD must be lifted; FROZEN re-frozen; all F1 reviews/evidence voided, re-run at new hash |

Option A has the smaller blast radius and is the route the measured tests support; Option B is a
legitimate one-clause fix if the corpus convention (literal composite binders) is to be kept.

## 6. Falsifiers

* **Adjudication (b) is refuted** by showing that frozen F1's `not_exists` clause fails to bind `q` or
  `t0` (e.g. `t0` free), or that D5 does not resolve, or that V1/V4 behave differently from the table
  at the pinned tool hashes.
* **The patch is refuted** by a schema that P accepts while failing to bind a declared composite
  binder's variables, or by P rejecting a schema the literal rule accepts.
* **Immutability is refuted** by any byte change in the seven pinned sources after this run.
* **Option A's consequence** is refuted by a run of `run_acceptance.py` at the frozen bytes that
  already exits 0 without amending either the tool or F1 — in which case W16R28-F1's stale-corpus
  diagnosis is itself incomplete and must be re-examined.
* **Scope:** W16R28-F1 (stale semantic corpus base `1bb78ce9` vs C0 `55d0a1ea`, `run_acceptance.py`
  exit 3) and W16R28-F3/F4 are **not** addressed here; W16R28-F1 remains open and independent.

## 7. Deliverables

| path | sha256 |
|---|---|
| `artifacts/worker-16/r03_adjudication/adjudicate_r03.py` | see `artifact_manifest.json` |
| `artifacts/worker-16/r03_adjudication/out/adjudication.json` | see `artifact_manifest.json` |
| `artifacts/worker-16/r03_adjudication/out/raw_verdicts.json` | see `artifact_manifest.json` |
| `artifacts/worker-16/r03_adjudication/tools/spec_conformance_audit_r03patch.py` | see `artifact_manifest.json` |
| `artifacts/worker-16/r03_adjudication/REPORT.md` | this file |
| `artifacts/worker-16/r03_adjudication/artifact_manifest.json` | hashes of the above |
