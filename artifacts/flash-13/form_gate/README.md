# FORM-GATE-01 — canonical executable class-schema gate

| field | value |
|---|---|
| assignment | `assign-FORM-GATE-01-20260911T2331` (lead-formulation) + `leadform-followup-…T2359` |
| node / gate | F1 / `G-CLASSBIND` (also intended for F2a, F2b) |
| spec | `artifacts/formulation/rule_spec.json` — FORM-RULE-SPEC, spec_version 1.2, rules R01–R16 |
| alias policy | `artifacts/formulation/VOCAB_ALIASES.json` (loaded, canonical token wins) |
| deliverable | `artifacts/flash-13/form_gate/check_class_schema.py` (primary implementation) |
| reports | `gate_report.json` (G3 shape, per-class `per_rule` with `json_path`), `fixture_suite_report.json` |
| fixtures | `fixtures/` — 3 conforming, 24 mutants, 6 rephrased; `fixtures/manifest.json` |
| status | **validation_status = unverified**; no node completion claimed |

## Independence (acceptance G5)

Written from FORM-RULE-SPEC and the frozen canonical field contract only. It does **not**
import, shell out to, or copy `artifacts/formulation/tools/check_class_schema.py` or any other
worker's gate/fixture. PyYAML is the only dependency. The lead's tool remains an independent
second implementation; a differential run of the two was not performed by this worker.

## Run

```bash
python3 artifacts/flash-13/form_gate/check_class_schema.py --canonical
python3 artifacts/flash-13/form_gate/check_class_schema.py FILE --class AF-SCC-C0-VAC-GEN
python3 artifacts/flash-13/form_gate/run_gate_tests.py     # fixture acceptance suite
```

Exit codes: `0` all rules pass · `1` ≥1 rule failure · `2` usage/parse error ·
`3` canonical schema absent (explicitly **not** a pass).

`--canonical` resolves `artifacts/formulation/schemas/*`, falls back to `schemas/*`, and binds
each result to `artifacts/formulation/FROZEN.json` (`frozen_sha256`, `frozen_prefix`,
`frozen_match`).

## Class parameterisation

Every rule is evaluated against `FROZEN_CLASSES[class_id]`; nothing is WCC-hardcoded:

| family | I+ (R09) | visibility (R10) | conclusion (R11) | extension regularity (R06) | ledger (R16) |
|---|---|---|---|---|---|
| WCC | role=`conclusion`, completeness definition required | role=`conclusion` + predicate/predicate_name + negation | `weak_cosmic_censorship` | null/none | skipped |
| SCC C2 | `in_conclusion=false`, completeness assertion forbidden | role=`not_in_conclusion` + WCC cross-reference | `scc_c2_future_inextendibility` | exactly `C2` | required |
| SCC C0 | as C2 | as C2 | `scc_c0_future_inextendibility` | exactly `C0` | required |

`ALLOWED_CONCLUSION_TYPES = {open_problem, formal_model, conditional_theorem}`; a `theorem`
label without `artifact_refs` fails R11. R13 bans composite `C0/C2` classes (including the
spelled-out `C-two / C-zero` form); R16 enforces the one-way implication ledger (C2 ⊂ C0) and
marks WCC↔SCC transfer forbidden/unresolved. Genericity kinds and conclusion types accept the
lead-published aliases, and every alias use is recorded in `alias_uses`.

## Measured results (2026-09-12T00:5x+08:00)

**Fixture suite (exit 0):**

* 3/3 conforming fixtures pass all applicable rules (R16 skipped for WCC only);
* **24/24 mutants rejected, each keyed to exactly one rule id**, with no cross-talk
  (2 mutants for each of R01–R16 as applicable, including the requested extended coverage for
  R09/R12/R15/R16: m19–m24);
* 6 rephrased mutants → 3 caught (R13 spelled-out regularity, R07 non-Baire "most data",
  R14 "continued" witness), 3 documented blind spots;
* `--canonical` on an empty directory returns 3; a conforming single target returns 0.

**Canonical schemas — FROZEN revision 4, `frozen_match=True` for all three:**

| canonical file | class | sha256 (prefix) | verdict |
|---|---|---|---|
| `artifacts/formulation/schemas/af_wcc_vacuum.yaml` | AF-WCC-VAC-GEN | `f512af5f4db3` | **pass** (R16 skipped) |
| `artifacts/formulation/schemas/af_scc_c2_vacuum.yaml` | AF-SCC-C2-VAC-GEN | `836746b39be4` | **pass** |
| `artifacts/formulation/schemas/af_scc_c0_vacuum.yaml` | AF-SCC-C0-VAC-GEN | `188e513130c6` | **pass** |

Per-rule verdicts and JSON paths are in `gate_report.json` under
`results[].per_rule[rule_id] = {status, json_path, detail}`.

## Findings

**F-GATE-1 (resolved): F2a pre-spec vocabulary.** At the earlier revision
`21df6f7f`/`9aaf12d5…` the C2 schema used six pre-spec synonyms and lacked the non-vacuity,
conclusion-type, provenance-status, falsifier-tier and implication-ledger blocks (14 rule
failures; a `possible_synonyms` diagnostic was emitted). The lead's `VOCAB_ALIASES.json` policy
and the frozen revision fixed this: the C2 schema now passes all 16 rules at `836746b39be4`.
The finding is retained here as the reason the gate emits the synonym diagnostic.

**F-GATE-2 (open, spec question): prohibition contexts vs R12.** R12 exempts foreign-family
tokens only inside `anti_scope`/`variants`, yet a correct SCC schema must name WCC content in
`forbidden_strengthenings` and `schema_falsifiers`, and a correct WCC schema says
"future-inextendible causal geodesic" in its visible-singularity definition. The gate treats
paths whose key contains `forbidden`/`must_not`/`not_conflate`/`schema_falsifier` as exemption
contexts, records the mentions in `exempted_mentions`, and scans otherwise. Requested decision:
ratify this reading, or require such entries to be tagged.

## Blind spots (3 rephrased mutants pass; documented, never counted as passes)

| fixture | evades | why it passes |
|---|---|---|
| `r01_extension_without_token` | SCC extendibility semantics in a WCC conclusion | "no continuous extension beyond the horizon" carries no SCC token |
| `r02_observed_without_visible` | WCC visibility semantics in an SCC conclusion | "cannot be observed from far away" avoids the token |
| `r06_observable_not_visible` | R12 cross-family conclusion import | "observable at future null infinity" avoids the tokens |

**Next falsifier for the gate:** a schema that passes R12 while importing the other family's
conclusion in synonyms — i.e. any of these three inserted as the *actual* conclusion rather than
a rephrased statement. Semantic leakage is not decidable lexically and remains A1 review work.

## Differential cross-check against the lead's frozen tool

`differential_vs_lead_tool.py` runs the lead's `artifacts/formulation/tools/check_class_schema.py`
as a **black box** (subprocess, JSON stdout only — never imported, source not consulted) on the
same 36 targets: 3 conforming fixtures, 24 mutants, 6 rephrased mutants, 3 canonical schemas.
`differential_report.json` records both sha256 values and every row.

The first run of this cross-check found a real divergence: my compact conforming fixtures used
the older token-list `class_components` shape, `predicate`, free-text `extension_solution_concept`
and `statements`/`forbidden_or_unresolved` ledger keys, which the lead's tool rejects. The
fixtures were then conformed to the **frozen canonical shape** (axes, `predicate_name`,
`extension_solution_concept` from the published vocabulary,
`one_way_entailments`/`forbidden_transfers`, `class_change_warning`,
`statement_natural_language`/`statement_formal`, `completeness_of_slice`, `I_plus_topology`).
Three mutants were also rewritten to mutate contract fields instead of extra fields this gate
invented, and this gate's R09 negation check was tightened to clause level (a negation earlier
in a string no longer masks an appended completeness assertion).

**Final differential (36 targets, both tools at the sha256 recorded in the report):**

| metric | value |
|---|---|
| verdict agreement | 30/36 (83%) |
| frozen canonical schemas | 3/3 pass under **both** gates (R01–R16 here; R01–R22 there) |
| mutants rejected | both tools 24/24 |
| disagreements | 6 — all are my *conforming/rephrased* fixtures failing the lead tool's R17/R18/R19/R22 |

**F-GATE-3 (superseded, kept for the record).** Against the lead tool at sha `eef3f43f932a`
the differential was 27/36 with 9 disagreements where this gate was stricter on spec text
(numeric decay R05; overclaim R15; cross-family tokens R12 ×4; spelled-out composite R13;
non-Baire generic_set R07; family witness R14); the lead tool rejected 18/24 mutants then.
Against the current tool (sha `1fcc3ad1df5d`) it rejects 24/24, so those coverage gaps appear
closed. The intermediate report file was overwritten by the final run; those numbers come from
this worker's run log for 2026-09-12T02:05+08:00.

**F-GATE-4 (governance, needs adjudication): unpublished rules in the canonical tool.**
The current `artifacts/formulation/tools/check_class_schema.py` (sha256 `1fcc3ad1df5d…`) rejects
all three of my conforming fixtures on rules **R17, R18, R19, R22**, but the published
`artifacts/formulation/rule_spec.json` (spec_version 1.2, revised 23:32:53) contains **only
R01–R16**. The frozen canonical schemas pass those extra rules, so a newer spec revision clearly
exists but is not published. Consequence: a gate cannot be validated against a rule set it
cannot read, and two conforming exemplars (my fixtures vs the frozen schemas) disagree only
because they were written to different unpublished revisions. Requested: publish the rule text
for R17–R22 (spec v1.3) and re-freeze, or pin the tool to v1.2; then this gate can be extended
rule by rule. I did not reverse-engineer the extra rules from the tool's behaviour, because that
would compromise the independence that makes the differential meaningful.

**Finding F-GATE-5 (manifest drift).** `FROZEN.json` revision 5 (frozen_at 23:35:45) records
schema hashes `f512af5f…`/`836746b3…`/`188e5131…`; the files on disk are now
`ef8441e4…`/`e67a6707…`/`7693c7c1…`. My gate passes **both** generations (the rev-5 run was
recorded with `frozen_match=true`); the manifest simply has not been bumped to the files that
are actually on disk. The change protocol in that same manifest requires a revision bump and an
artifact event on any change.

## Gate defects this suite caught in itself (controls, not reasoning)

1. Bare stem `inextendib` flagged `future-inextendible` (WCC I+ generators and WCC geodesic
   language). Tokens are now SCC-qualified ("… of the maximal development", "spacetime is …").
2. R13 flagged `must_not_conflate: "C2 and C0"` — a prohibition, not a composite class.
3. R09 flagged i_plus `forbidden: "asserting I+ completeness"` — a negation.
4. R14 let a wrong-family witness hide behind a correct `witness_type`.
5. R04 ignored `topology.I_plus_topology` when `conformal_boundary` is a list.
6. R03 required a redundant per-quantifier `domain` string although the spec's fail condition is
   an unresolved `domain_id`; the frozen schemas resolve domains through `quantifiers.domains`.
7. R07 accepted prose as a `generic_set`; the spec demands a set-builder or Baire formula.

## Non-claims

No node completion, no theorem, no physics, no citation adjudication. A gate pass is structural:
it does not say a schema is correct, non-vacuous, or faithful to the literature; that is A1's
review and the class owner's binding interpretation.

## Revision 1.1 — escape triage against the worker-06 semantic corpus (2026-09-12T00:2x+08:00)

Trigger: worker-06's frozen-base semantic corpus (`artifacts/worker-06/semantic_fixtures/`,
manifest `c102445df3971109`) measured the independent gate at `8130652042b47952` catching
**13/32** leaking mutants (escape 0.5938; worker-06 event `w06-20260912T0045-a1-gateruns`). This
revision closes every escape derivable from the published rule text, without importing or copying
the lead tool or worker-06's rules.

Additions, by rule id:
- **R02** `class_contract_pointer` may not name a foreign class (sem11).
- **R06** unknown `regularity` keys asserting a smoothness assumption are rejected (sem01); the
  class pins `extension_solution_concept` (sem08); `extension_predicate.frozen_equation_concept`
  is required, `frozen_regularity` must equal the class token and `frozen_direction` must be the
  one-sided future direction (struct10, sem09, sem10).
- **R07** `kind='none'` drops a class-identity slot (sem04); the frozen class kind is pinned
  (sem13 `full_measure`); `generic_set` must be a set-builder or Baire formula, not a prose
  gesture at "open dense" (sem03).
- **R08** the condition must be a substantive membership requirement (sem15, sem19);
  `witness_type` must name a witness, not a null placeholder (struct09); unknown `non_vacuity`
  keys asserting extra hypotheses are rejected (sem05).
- **R11** a conclusion may not be inherited from a sibling class (sem02); theorem promotion in
  the conclusion statements without `artifact_refs` fails (sem12).
- **R12** an SCC schema may not carry the sibling SCC class id inside a scanned block (sem02).
- **R14** the family witness check reads the witness text only; the class-id token in `refutes`
  no longer satisfies it (sem06).
- **R15** broader source-overclaim phrasing (sem18) and citation use embedded in the conclusion
  (sem14).
- **R16** an asserted converse row C2 => C0 in `one_way_entailments` fails (sem16).

Measured result (`escape_triage.json`, gate `ad7d120b8449`):
`caught_post_hardening 32/32`, `newly_caught 19`, `escapes 0`, corpus controls false positives
`[]`, all six canonical files (both trees) pass with `frozen_match=true` against FROZEN
revision 25. The structural fixture suite still passes 24/24 mutants with the expected rule and
3/3 positives; cross-talk R06 is recorded on six SCC mutants (single-rule-keyed 16/24).
Reproduce: `python3 artifacts/flash-13/form_gate/escape_triage.py`.

Measurement caveats: (1) the corpus manifest records base
`artifacts/formulation/schemas/af_scc_c0_vacuum.yaml` at `92406957234f`, the file on disk is
`1bb78ce9b357` (republished by the formulation lead), so the differential is valid over the
pinned fixtures but says nothing about the base revision; (2) gate revision 1.0
(`8130652042b47952`) is not archived (the repo git objects are unreadable), so the pre-hardening
column rests on the recorded measurement in
`artifacts/worker-06/canonical_gate_run.json#238eb129c81e` and this worker's outbox; future
revisions should archive the superseded file.

## Revision 1.2 — R03 declared-binder usage at the rev13 / FROZEN rev29 bytes (2026-09-12T01:0x+08:00)

Trigger: the standing FORM-GATE-01 card requires a frozen-hash run and deltas only. At the rev13
bytes (WCC `d9cebb9404b2`, C2 `e9a27996dfd3`, C0 `b2ab6acb2bbe`, FROZEN rev29 `815e08079aef`)
gate 1.1 passed all three. Re-reading R03 against the schema, canonical WCC `quantifiers.ordered[5]`
declares the tuple binder `(q,t0)` while its `quantifiers.formal` renders the same quantifier
variable-wise (`not exists q in I+ and t0 in [0,T) with ...`). R03's published require is that
`quantifiers.formal` is "a single sentence using those binders", but the 1.1 implementation only
required the formal sentence to contain *some* quantifier, so the defect escaped. This is the same
defect independently measured by the adopted semantic auditor (worker-064 `W064-R03-CAUSE-01`,
auditor `c79d8ab8440a`; reproduced from worker-080 Probe B and worker-16 W16-R03-ADJ-01).

Revision 1.2 adds a whitespace-normalised **literal-usage test** inside R03: every declared binder
must occur in `quantifiers.formal`. It is disclosed as literal — a semantically equivalent
alpha-renaming of a declared binder would be flagged — so the alpha-equivalence adjudication stays
with the rule owner; the test decides only the spec's literal wording. C0 and C2 are unaffected
(their tuple binders occur literally in their formal sentences).

**Measured bisect at byte-identical canonical files (see `canonical_recheck_rev29.json`):**

| gate | sha256 | AF-WCC-VAC-GEN | AF-SCC-C2 | AF-SCC-C0 |
|---|---|---|---|---|
| 1.1 | `ad7d120b8449` | pass | pass | pass |
| 1.2 | `5522541bde4e` | **fail R03** (`quantifiers.ordered[5].binder`) | pass | pass |

**Controls:** fixture suite exit 0 — 3/3 conforming pass; **25/25 mutants rejected with the
expected rule** (single-rule-keyed 17/25; the six SCC mutants still cross-talk R06); rephrased
corpus unchanged (5 caught, 1 documented blind spot); exit 3 on absent canonical. New single-rule
mutant `m25_wcc_binder_unused.yaml` (`72eab532a720`) differs from `conforming_wcc.yaml` only in
`quantifiers.ordered[2].binder: p -> (p,t0)`. Cross-check of worker-064's one-clause E1a repair
candidate (`2f51ace6ef74`) under gate 1.2: **pass R01–R16** (`e1a_crosscheck.json`), so the R03
failure is repairable by rendering the declared tuple binder and is not a blanket reject.

**Finding F-GATE-6 (gate under-detection, now closed in-gate).** Gate 1.1 gave a false pass on
R03 for canonical WCC at rev12 and rev13; the corrected gate reports the failure at rev13 bytes.
The finding is a formal-sentence rendering defect, not evidence against the rev12 mathematical
repair, and no canonical byte was touched by this worker. Standing falsifiers: (a) the rule owner
certifies the variable-wise rendering as satisfying R03 (then the literal test is too strict and
must be relaxed by rule adjudication, not silently), (b) an alpha-renamed schema certified as
conforming is rejected by the literal test, (c) any canonical byte changes (then re-run at the
new hash). F-GATE-4 (unpublished R17+ rules in the lead tool) still stands and still limits parity.

## Revision 1.3 — R03 realization test, both readings reported (2026-09-12T01:1x+08:00)

Revision 1.2's literal test resolved F-GATE-6 in the wrong direction: it rejects the frozen rev13
canonical WCC exemplar `d9cebb9404b2`, which the assignment names as conforming (G2), because
`ordered[5]` declares the pair binder `(q,t0)` while the sentence realises that single pair-choice
variable-wise (`not exists q in I+ and t0 in [0,T) ...`). Both declared variables occur, bound after
their quantifier; that is a rendering, not a scope error. At the same time the literal test cannot
see scope errors at all. Revision 1.3 therefore measures two readings of R03 in every result
(`r03_readings`) and uses the **semantic realization** reading as the pass criterion:

* **S (pass criterion)** — the quantifier-keyword sequence of `quantifiers.formal` equals the
  declared `kind` sequence of `quantifiers.ordered`, in order; and every variable named in every
  declared binder occurs whole-word at or after its own quantifier keyword.
* **L (reported, not the criterion)** — every declared binder string occurs verbatim (the 1.2
  criterion). `--r03-mode literal` reproduces 1.2's pass/fail exactly: **0 mismatches** against the
  archived 1.2 suite report over all 34 fixtures (`legacy_v12/fixture_suite_report.v12_r03.json`).

**This is not a relaxation.** Four controls are accepted by L and rejected by S
(`controls_that_L_accepts_and_S_rejects`): declared-kind reorder, a deleted quantifier clause whose
variables remain in the body, an extra body quantifier keyword, and a declared variable that occurs
only before its quantifier. `m25_wcc_binder_unused` still fails R03. The one case where S and L
disagree in the canonicals' favour is `c07_wcc_canonical_tuple_render` (L fail / S pass), i.e. the
false positive being corrected. A consistent alpha-rename (`c05`) is not punished; an
inconsistent one (`c06`) is.

**Corpus defect found by S and repaired in `fixtures_v13/`.** All 34 legacy fixtures declared
`quantifiers.ordered[2].kind: exists` while their own formal sentence says `not exists p in VIS with
Visible(p)` — a declared-kind/sentence contradiction 1.2 could not see. `make_fixtures_v13.py`
repairs the kind token only (one logical diff per file, recorded in `fixtures_v13/manifest.json`
with legacy and repaired sha256) and the repaired corpus reproduces the 1.2 suite metrics exactly:
3/3 positives pass, 25/25 mutants rejected with the expected rule, 17/25 single-rule-keyed (the
pre-existing R06 cross-talk is unchanged), 5/6 rephrased caught, 1 documented blind spot, exit 3 on
absent canonical, exit 0 on a conforming single target. Legacy corpus and 1.2 reports are archived
byte-identical under `legacy_v12/`.

**Evidence.** `r03_readings_rev29.json` (all assertions A1–A6 pass; gate hash in `gate_sha256`),
`canonical_recheck_rev29_v13.json` (three canonicals pass all 16 rules at `d9cebb9404b2` /
`e9a27996dfd3` / `b2ab6acb2bbe` under FROZEN rev29 `815e08079aefbc`), `fixtures_r03/manifest.json`
(10 controls), `fixtures_v13/manifest.json`, `fixture_suite_report.json` + `gate_report.json`
(acceptance run), `legacy_v12/` (superseded 1.2 outputs).

**Non-claims / process notes.** No gate verdict is set and no canonical byte was modified; the
rule-owner adjudication under `astra-life05-verify-gform-r3` stands. If the owner rules that R03
means literal occurrence, the worker-064 E1a/E1b one-clause repair satisfies S as well (E1a already
passed under 1.2's cross-check), so either ruling has a repair path. The gate source is superseded
in place: revision 1.2's bytes (`5522541bde4e`) are not archived byte-exactly, but its behaviour is
reproduced by `--r03-mode literal` and its outputs are archived. Standing falsifier: any canonical
byte change voids these readings; a certified-conforming schema that S rejects, or a schema S
accepts whose sentence does not realise its declared quantifier structure, refutes the revision.

