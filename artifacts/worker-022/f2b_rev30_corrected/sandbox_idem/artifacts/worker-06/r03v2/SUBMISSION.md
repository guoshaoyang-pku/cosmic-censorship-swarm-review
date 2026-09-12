# R03-v2 — stage-B binder-check repair proposal (one class-bound task)

**Owner** worker-006 · **Node** A1 · **Gate** G-CLASSBIND (folds into G-AUDIT) ·
**Classes** AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN
**Basis** `astra-lead-formulation` blocker `lead-form-20260912T005843-94` (node A1), whose
falsifier is a stage-B rule change under which the `'(q,t0)'` binder no longer fails.
**Status** measurement + proposal only. No gate verdict, no node completion, no theorem.

## What was wrong

Frozen stage B (`artifacts/worker-06/spec_conformance_audit.py` @ `c79d8ab8440a`, R03)
fails a quantifier entry when its `binder` string is not a **literal substring** of
`quantifiers.formal`. Canonical AF-WCC-VAC-GEN declares binder `"(q,t0)"` and writes the same
binding as `not exists q in I+ and t0 in [0,T)`, so the canonical schema — a pass control — is
rejected. Every probe-10/11 measurement therefore had to run stage B′ with this check removed,
which is why the lead's H5 "controls pass both stages" condition could not be met.

Minimal repro:

```
python3 artifacts/worker-06/spec_conformance_audit.py schemas/af_wcc_vacuum.yaml
# verdict reject, R03: binder '(q,t0)' absent from formal sentence   <-- false positive
python3 artifacts/worker-06/r03v2/audit_r03v2.py schemas/af_wcc_vacuum.yaml
# verdict accept, R03: 6 ordered quantifiers, all domains resolved
```

## The proposed rule (R03-v2)

Replace the literal-substring test with a **binder-head co-binding** test. For each ordered
entry, its identifiers must appear, in order, inside one quantifier clause's *binder head* —
the clause prefix before the first top-level `:` `;` `,` `with` / `such that` / `where` /
`of` / `letting` (parenthesised groups are never split) — with each identifier within
`span` characters of the previous one. Default `span = 80`.

Delivered as `audit_r03v2.py`, generated deterministically from the frozen source by
`make_r03v2.py` with exactly **two textual deltas**: D1 path rebase (copy lives one directory
deeper) and D2 the R03 block. D2 is the only semantic change. The frozen tool is untouched.

## Pre-registered calibration (corpus hashed before any run)

`preregistration.json` fixed the rule, span, corpus and decision rule before the run;
`fixture_manifest.json` was hashed in the pre-registration and every fixture byte was verified
before and after. Pins: frozen source `c79d8ab8440a`, WCC `d9cebb9404b2`, C2 `e9a27996dfd3`,
C0 `b2ab6acb2bbe`, FROZEN.json `815e08079aef`, rule_spec `40f9bb9e657b`. **No pin drift.**

| set | n | frozen R03 | R03-v2 |
|---|---|---|---|
| positive controls (3 canonicals + 3 conforming + 2 negated-phrase) | 8 | 6 accept (2 FP) | **8 accept (FP = 0)** |
| `neg_abs` — binder identifier removed from formal | 3 | 3 caught | **3 caught** |
| `neg_nonbind` — declared binder unbound, spelling survives in a trailing remark | 3 | 0 caught | **3 caught** |
| canonical gate negatives (`artifacts/formulation/fixtures/negative/`, 31 files) | 31 | — | **0 unexplained lost catches** |

Gate-negative classification: 11 disagreements are the declared literal-tuple FP family
(every failed binder's identifiers are co-bound under R03-v2), 3 are substantive R03 violations
rejected by both (`m01`/`m02`/`m03`), 17 have no R03 disagreement, **0 lost catches**.

Span ablation (`calibration_table.json`): `pos_fp = 0` for every pre-registered span (13…∞);
`neg_abs` 3/3 and `neg_nonbind` 3/3 at every span. The window only matters for a coordinated
binder kept inside one head. Pre-registered unscored probes show the over-reject edge:
a tuple padded with 30 filler chars is accepted at span ≥ 40, with 100 chars at span ≥ 120,
with 300 chars only at an unbounded span.

## Falsifier outcome

| pre-registered falsifier | outcome |
|---|---|
| any positive control rejected by R03-v2 | **not triggered** (8/8 accepted) |
| any `neg_abs` accepted by R03-v2 (lost catch) | **not triggered** (3/3 caught) |
| any gate negative whose frozen R03 rejection is not reproduced, outside the declared FP family | **not triggered** (0) |
| pinned input drift during the run | **not triggered** |

Standing falsifier for adoption: run R03-v2 against a *new* canonical revision; a positive
control rejected at `span` or a genuinely unbound binder accepted falsifies the rule there.

## Honest limits (documented, not hidden)

1. R03-v2 is a deterministic heuristic over surface text, not a parser. A declared binder whose
   identifiers happen to sit in a head that does not actually introduce them is still accepted.
2. It over-rejects a legitimate coordinated binder whose variables are more than `span`
   characters apart in one head (span probes s02/s03); `span=80` is the pre-registered default,
   `span=∞` keeps every measured catch and admits the probes.
3. The corpus is a derived, non-exemptible regression set, not held-out prose. The held-out
   escape measurement for the A1 queue still has to be re-dispatched at rev29 on top of this fix.
4. The pre-registration text says 30 gate negatives from the earlier listing; 31 were present at
   run time and all 31 were included (superset, no selection).

## Files

| file | role |
|---|---|
| `preregistration.json` | rule, span, corpus, expectations, decision rule, falsifier (written before run) |
| `fixture_manifest.json` | hashed corpus definition |
| `r03v2_rule.py` | standalone proposed predicate + frozen predicate |
| `make_r03v2.py` | deterministic generator (pins asserted, single semantic delta) |
| `audit_r03v2.py` | proposal copy of stage B (D1+D2) |
| `run_calibration.py` | runner |
| `report.json`, `calibration_table.json`, `blindspot_report.json`, `raw_verdicts.json` | results |
| `fixtures/` | 17-fixture corpus (8 pos / 3 neg_abs / 3 neg_nonbind / 3 span probes) |

**Not claimed:** gate verdict, node completion, theorem, physics result. Adoption of the rule is
the schema owner's decision; editing the frozen tool is the controller/lead's action.
