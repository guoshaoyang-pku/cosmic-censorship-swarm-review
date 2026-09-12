# W068-FORM-POLARITY-12 — class-general conclusion-content freeze: escape measurement and candidate-rule evaluation

**Worker:** worker-068 (bounded task, no inbox card). **Node:** A1. **Gate:** G-CLASSBIND
(folded into G-AUDIT as calibration evidence). **Classes:** AF-WCC-VAC-GEN,
AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN. **Status:** measurement complete; proposal, not
adopted; no gate verdict and no node transition claimed.

## Question

FORM-HELDOUT-09 and FORM-POLARITY-10/11 measured that neither class-binding stage compares
`conclusion.statement_formal` / `conclusion.statement_natural_language` against the frozen
class conclusion: conclusion-polarity inversions escape both stages for all three classes.
This task asks the next two questions:

1. Do conclusion **content substitutions that contain no negation marker** also escape, on
   all three classes, at a fully pinned pipeline?
2. Can a class-general, vocabulary-free **conclusion-freeze** candidate rule catch the whole
   conclusion-statement escape family without flagging any conforming control?

## Method (all bytes pinned; no live input read by the measurement)

A fresh corpus (33 fixtures) was built against the archived **revision-11** class bases and
run through a **three-class pinned shadow** of the two stages:

| input | sha256 (12) |
|---|---|
| stage A `check_class_schema.py` | `000e09e46b2f` |
| stage B `spec_conformance_audit.py` | `c79d8ab8440a` |
| rule spec `rule_spec.json` | `40f9bb9e657b` |
| KEY_MANIFEST rev27 | `fce91948ba3a` |
| W / C2 / C0 rev11 bases | `9a8bd4c96800` / `b6123750b37d` / `1bb78ce9b357` |

Corpus: 3 identity controls, 15 carried-over polarity probes (p1–p7), **12 new
content-substitution probes** (s1 argument, s2 quantifier strength, s3 quantifier domain,
s4 object/regularity — each keeps every class token and every negation-marker count), and 3
known-rejected liveness controls. `manifest.json` was hashed before any stage run; all
fixture and shadow hashes were re-verified after the run (`valid=true`, no drift).

The candidate rule is implemented in `conclusion_freeze_check.py` with three variants:
`freeze_statements` (statement content only), `freeze_full` (plus class tokens), and
`negation_only` (declared 15-token negation-marker count; a narrow baseline).

The same rule was re-evaluated read-only over the union of the three earlier pinned corpora
(FORM-HELDOUT-09, FORM-POLARITY-10, FORM-POLARITY-11).

## Results

### 1. The content blind spot is class-general, and not only about negation

Arm calibration: identity accepted by both stages for all three classes (3/3) — every arm
informative. Known-rejected liveness controls rejected 3/3.

**24 of 27 content probes escape both stages** (W 9, C2 7, C0 8):

- **12/12 substitution probes escape** — every s1–s4 probe on every class is accepted by
  both stages. None of them contains a negation marker absent from the base.
- 12/15 polarity probes escape; the 3 p4 `conclusion_type` token flips are caught by R11.

### 2. Candidate rule R-CAND-F (conclusion statement freeze)

| corpus | conclusion-statement escapes | R-CAND-F catch | conforming controls | R-CAND-F false positives |
|---|---|---|---|---|
| new 3-class corpus | 24 | **24/24** | 3 (identity) | **0/3** |
| union (heldout3 + polarity10 + polarity11) | 14 (13 fresh + 1 reference copy) | **14/14** | 12 | **0/12** |

On the union corpora R-CAND-F also flags 6/40 already-caught content-changing probes (the
rule is additive; those fixtures are rejected by stage A anyway) and 6/12 known-rejected
liveness controls (again already rejected).

### 3. A negation-only rule is not sufficient

`negation_only` catches the polarity family (12/15 new probes, 14/14 union statement-axis
escapes) and **0/12 substitution probes**. A polarity/content check built on negation
vocabulary — including the independent C0-only four-criterion check of worker-003
(`artifacts/worker-003/c0_polarity_adjudication`, 1/49 on heldout3) — does not generalise to
substitutions that use in-class vocabulary.

### 4. The escape instances split into two content axes (F4)

| axis | n | R-CAND-F |
|---|---|---|
| conclusion statement content (13 fresh escapes + c0_03 reference) | 14 | 14/14 |
| non-statement content: `i_plus.completeness_definition`, `class_identity_variants`, `anti_scope` entries (FORM-HELDOUT-08 reference escapes m04/m16/m25/m29) | 4 | 0/4 |

The four FORM-HELDOUT-08 escape families survive with **identical conclusion statements**;
their changed leaves lie elsewhere. A conclusion-statement freeze cannot catch them — a
definition-site freeze (R-CAND-D) is the open successor, declared as gap `W068-P12-G1`.

## Findings (each with an executable falsifier in `report.json`)

- **W068-P12-F1** — non-negation conclusion content substitutions are accepted by both
  stages in all three classes (pinned three-class shadow, identity-calibrated).
- **W068-P12-F2** — R-CAND-F flags every conclusion-statement probe on the new corpus and
  every conclusion-statement escape in the union corpora, with zero false positives on 12
  conforming controls; it does not catch non-statement-axis escapes.
- **W068-P12-F3** — `negation_only` misses all 12 substitution probes.
- **W068-P12-F4** — the union escape set decomposes into a statement axis (14) and a
  non-statement/definitional axis (4).

## Artifacts

`manifest.json` (pins before run) · `conclusion_freeze_check.py` (candidate rule) ·
`build_corpus12.py` · `run_polarity12.py` · `raw_verdicts.json` · `report.json` ·
`checkpoint.json` · `candidate_rule.json` (proposal, owner lead-formulation/lead-audit) ·
`corpus_index.json` · `fixtures/` · `known_leaks/` · `shadow/`.

## Reproduction

```bash
cd <repo>
python3 artifacts/worker-068/polarity12/build_corpus12.py
python3 artifacts/worker-068/polarity12/run_polarity12.py
python3 artifacts/worker-068/polarity12/conclusion_freeze_check.py \
    --fixture artifacts/worker-068/polarity12/fixtures/w_s2_quantifier_strength_substitution.yaml \
    --base    artifacts/worker-068/polarity12/shadow/schemas/af_wcc_vacuum.yaml \
    --variant freeze_statements --json
```

## Non-claims and limitations

- Author-built corpus: the probe labels are worker-068's; an independent reviewer must
  adjudicate each probe as a genuine class-contract violation before the escape counts are
  cited. No gate verdict, node completion, or `validation_status=passed` is claimed.
- The union evaluation re-uses worker-068-built corpora; it is a re-analysis at pinned
  bytes, not an independent corpus.
- The rule decides statement invariance, not mathematics: legitimate post-freeze revisions
  require re-freezing the class contract.
- `negation_only` uses a declared 15-token vocabulary; a richer lexical classifier may catch
  some substitutions it misses. The point measured here is that lexical polarity checks are
  not a completeness argument for the content axis.

## Falsifier

Any identity control rejected by either stage (arm non-informative); any pinned shadow or
fixture byte drift between build and run; any substitution probe rejected by both stages
(reported as a catch, not an escape); any conforming control flagged by R-CAND-F; or a
leaf-level re-diff contradicting the escape-axis decomposition.
