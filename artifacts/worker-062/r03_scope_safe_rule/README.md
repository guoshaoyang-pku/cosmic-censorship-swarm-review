# W062-GFORM-R03-SCOPE-SAFE-RULE-CANDIDATE-01

Bounded class-bound worker task (worker-062, relaunched slot, 2026-09-12).
Node **F1** (`AF-WCC-VAC-GEN`) with F2a/F2b as cross-class controls; gate **G-FORM**.
**No inbox card existed for worker-062; the task was self-selected** from the live R03 dispute and
is disclosed as such. No canonical, frozen, pinned or live-instrument file was written.

## Question

`W16-R03-ADJ-01` established that the frozen stage-2 rule R03 rejects canonical F1 by a literal
substring test (`binder '(q,t0)' not in quantifiers.formal`) while the formal sentence renders the
same quantifier variable-wise. `astra-lead-formulation` lifecycle-08 (01:15) then measured that the
plain variable-wise repair **cand_E3** accepts a *negation-scope-error* rendering too, and
recommended option A-prime (variable-wise **plus** a scope-aware grouping requirement) **without a
measured candidate**.

Does a minimal, deterministic, scope-aware amendment (candidate **E4**) exist that, at the pinned
bytes, (i) accepts canonical frozen F1, (ii) still rejects a genuinely unbound composite binder,
(iii) rejects the scope-error rendering, and (iv) leaves F2a/F2b and literal-composite behaviour
unchanged?

## Method

Pre-registered before the first run (`PREREGISTRATION.json`): 4 tools x 11 targets, two
deterministic runs per cell, pins `F1 d9cebb9404b2`, `F2a e9a27996dfd3`, `F2b b2ab6acb2bbe`,
baseline auditor `c79d8ab8440a`, cand_E3 `3f69bc1eb27a`, rule spec `40f9bb9e657b`.
All tools run with the pinned `--spec` explicitly; every write is inside
`artifacts/worker-062/r03_scope_safe_rule/`.

**E4 rule (one contiguous replacement of the R03 binder block).** If the declared binder is not a
literal substring of `quantifiers.formal`: split it into variables; locate the quantifier phrases
lexically (keyword to first ` with ` / ` such that ` / ` so that ` / `:`); use the scope path **only**
when the number of located phrases equals the declared ordered-binder count and the phrase kind
equals the declared kind; then require every binder variable to occur as a whole word **inside that
quantifier's own restriction phrase**. Otherwise reject as before.

Variants are canonical F1 with only the tail after `with finite affine length: ` replaced.

| target | tail semantics | baseline (literal) | E3 (variable-wise) | **E4 (scope-aware)** |
|---|---|---|---|---|
| V0 frozen variable-wise | intended correct | reject/R03 | accept | **accept** |
| V1 grouped `(q,t0) in D5` | correct, literal | accept | accept | **accept** |
| V2 grouped `(q,t0) in I+ x [0,T)` | correct, literal | accept | accept | **accept** |
| V3 scope error (lead's) | q bound, t0 outside | reject/R03 | **accept** | **reject/R03** |
| V4a unbound restriction, body keeps q,t0 | not bound | reject/R03 | **accept** | **reject/R03** |
| V4b fully unbound | not bound | reject/R03 | reject/R03 | **reject/R03** |
| V5 shadow quantifier (`forall t0 ... not exists q`) | t0 bound elsewhere | reject/R03 | **accept** | **reject/R03** |
| V6 reordered restriction | correct | reject/R03 | accept | **accept** |
| V7 wrong variable name (`tau`) | not bound | reject/R03 | reject/R03 | **reject/R03** |
| F2a canonical | cross-class | accept | accept | **accept** |
| F2b canonical | cross-class | accept | accept | **accept** |

Every cell above equals the pre-registered `expected_matrix` (E13 PASS). Independent corroboration
of the lead's finding: **E3 accepts V3** at `3f69bc1eb27a` under the pinned rule spec. Direct runs
on the published canonical F1 bytes (not a YAML round-trip) reproduce the same column
(`AMENDMENT_01.json` A2: baseline reject/R03, E3 accept, E4 accept, `doc_sha256 = d9cebb9404b2`).

## Verdict and the one disclosed defect

Pre-registered verdict: **PARTIAL**. The substantive matrix passed every expectation (E1-E10,
E12-E13) and every control (C1-C8), but expectation **E11** ("differs from baseline in one hunk")
was implemented by the harness as a positional line comparison, which reports 446 changed lines
across a +22-line insertion and therefore FAILED. This is a defect in my measurement instrument,
not in E4. A **disclosed post-hoc amendment** (`AMENDMENT_01.json`, `amend_e11_hunk_count.py`)
recomputes it with `difflib`: **one unified-diff hunk, 28 changed lines** - a single contiguous
replacement. The pre-registered verdict is left at PARTIAL; no expectation or candidate byte was
changed after seeing results.

## Controls

C1 pin gate (7/7 verified pre/post) · C2 double-run determinism (44/44 cells) · C3 E4-noscope
control reproduces the E3 column cell-for-cell (the scope branch is load-bearing) · C4 malformed
document (no `ordered`) still rejects R03 under all four tools · C5 live inputs unchanged after the
runs · C6 the replaced block occurs exactly once · C7 E4 builds byte-identically twice · C8
`FROZEN.json` drift recorded informationally only.

## Recommendation to the owner / controller

E4 is the first measured A-prime candidate: it keeps the variable-wise acceptance that fixes the
false positive and adds a lexical scope requirement that rejects the scope-error, unbound and
shadow-quantifier renderings cand_E3 accepts. **Adoption is not worker-authorised and E4 is a
sandbox file only.** The formulation lead's governance blocker binds: `spec_conformance_audit.py`
is absent from `artifacts/formulation/FROZEN.json`, so any R03 amendment must be accompanied by
pinning the stage-2 tool in the same FROZEN revision before it is used as gate evidence. The
canonical F1 bytes still fail at the published pin; the R03 blocker is not repaired by this task.

## Scope limits

Stage-2 only: no end-to-end `run_acceptance.py` PASS is claimed. The scope check is a **lexical
proxy, not a parser**: it requires quantifier phrases in declared order, exactly one phrase per
declared binder, and a fixed terminator list. It is a candidate for review, not a promoted rule.

## Falsifier

Show a run at the declared pins where E4 deviates from the E4 column above; a scope-error rendering
E4 accepts; E4 rejecting V1/V2/F2a/F2b; any input pin moving between T0 and T1; or any write outside
this task's directory.

## Authority note

Worker evidence only. No node status, `validation_status=passed`, or gate verdict is set. The F1
schema and the stage-2 instrument are owned by `astra-lead-formulation` / worker-006.

## Layout

| path | what |
|---|---|
| `PREREGISTRATION.json` | pins, variants, expected matrix, expectations E1-E13, controls C1-C8, decision/stop rules |
| `run_scope_safe_rule.py` | deterministic harness (pin gate, sandbox build, variants, 4x11x2 matrix, controls) |
| `report.json` | full machine report incl. per-cell verdicts, doc hashes, tool hashes, expectations |
| `matrix.json` / `controls.json` | compact matrix and control table |
| `AMENDMENT_01.json` / `amend_e11_hunk_count.py` | disclosed post-hoc E11 instrument correction + direct-canonical corroboration |
| `sandbox/tools/E4/spec_conformance_audit.py` | **the E4 candidate bytes** (sha256 `3cd55a5373e8`) |
| `sandbox/variants/` | the 9 variants + malformed control |
| `CHECKPOINT.json` | worker checkpoint: verdict, pins, artifact hashes, falsifiers |
