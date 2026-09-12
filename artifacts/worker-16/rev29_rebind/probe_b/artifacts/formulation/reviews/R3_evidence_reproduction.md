# R3 — Independent evidence reproduction / refutation

Reviewer: **R3** (independent verification agent)
Workspace: `/data3/guoshaoyang/workdir/ai4math-swarm`
Window: **2026-09-11 23:26:26 – 23:30 CST** (live swarm; artifacts were being written by other
agents *during* this review — see "Moving target" below).
Tools under test (sha256, measured at 23:29:27):

| file | sha256 |
|---|---|
| `artifacts/formulation/tools/check_class_schema.py` | `84f1aa2f058a8c297b8cc38bc7e037194e30b46915fb923d9bfbd23e1e500a24` (unchanged all review) |
| `artifacts/formulation/tools/run_gate_tests.py` | `73fadd0a127edc4f…` at start → **revised by another agent 23:28:52** → `b6dd43333cbdb7a28e86f1bd9c130981386ebe7e3138e7fd38daa649beca08fa` |
| `artifacts/formulation/evidence/gate_test_report.json` (final) | `703ddd76ad0fed2b1f54e3c48b711adef1aaebc62d34c0e46c11c8994dbea6a7` |

No file outside `artifacts/formulation/reviews/` was edited by R3. Running the requested harness
does rewrite its own fixtures/evidence (documented side effect, see C2). Auxiliary raw log:
`artifacts/formulation/reviews/R3_command_log.txt`.

---

## C1 — "The research map's declared node artifacts mostly do not exist"

**Verdict: REFUTED** (at all three revisions observed; the claim matches only the *superseded*
revision audited in `evidence/map_artifact_audit.txt`).

Command (run three times, `cwd` = repo root):

```bash
python3 - <<'EOF'
import json, hashlib
from pathlib import Path
p = Path('research_map/research_map.json')
print('map sha256:', hashlib.sha256(p.read_bytes()).hexdigest())
m = json.loads(p.read_text())
rows=[]
for g in m['groups']:
    for n in g.get('nodes') or []:
        art=n.get('artifact'); ex=bool(art) and Path(art).exists()
        rows.append((g['id'], n['id'], n.get('status'), art, ex))
print('TOTAL', len(rows), 'existing', sum(r[4] for r in rows), 'missing', sum(not r[4] for r in rows))
print('missing:', [(r[0],r[1],r[3]) for r in rows if not r[4]])
EOF
```

| snapshot (CST) | map `updated_at` | map sha256 | declared node artifacts | exist | missing |
|---|---|---|---|---|---|
| 23:26:26 | 2026-09-11T23:26:04 | `83e2d8b318334b4ffe25ba1fefe8f549082cabaa46597cb68cf4d632c7560fc2` | 11 | **7** | 4 |
| 23:28:40 | 2026-09-11T23:28:19 | `b69d2ff998a9084c79a2161bc2b675177fd1e0d3975ec1eeeb47250cf1386e36` | 11 | **9** | 2 |
| 23:29:40 | 2026-09-11T23:29:35 | `bcd61e3f3a4b89c00efe9784cc9b769ab96bfa517e32e1cd9295b01ba28a0166` | 11 | **9** | 2 |

Snapshot 1 raw rows (7 exist / 4 missing):

```
formulation F0 active True   research_map/formulation_taxonomy.yaml
formulation F1 active True   schemas/af_wcc_vacuum.yaml
formulation F2 active False  schemas/af_scc_regularities.yaml
literature  L0 active True   ledger/theorems.jsonl
literature  L1 active True   ledger/citation_audit.csv
numerics    N0 active True   numerics/tests/flat_wave.py
numerics    N1 queued False  numerics/spherical_solver/
numerics    N1-BLOCK queued False numerics/blockers.md
audit       A0 active True   evaluation_rubric.yaml
audit       A1 active True   reviews/
audit       A2 active False  evaluation/ablation.csv
```

Between 23:26 and 23:28, two declared artifacts appeared on disk (`evaluation/ablation.csv`,
mtime 23:27:43; `schemas/af_scc_regularities.yaml`, mtime 23:28:07), so snapshot 1's missing count
shrank from 4 to 2. The only artifacts still missing at the end are **N1** (`numerics/spherical_solver/`)
and **N1-BLOCK** (`numerics/blockers.md`), both inside the `numerics_lock.state == "locked"` branch;
their node-level `artifact_exists: false` flags agree with disk.

The prior audit `artifacts/formulation/evidence/map_artifact_audit.txt` reports
`ARTIFACT_EXISTENCE: 0/10 exist; 10 missing` against map sha `82b96a7d8085d82c95c93a7f82d9ffafa085e20287df536215cb7e0550139d71`.
That revision no longer exists on disk, so the claim "mostly do not exist" is true only of a
superseded map revision.

**Could not test:** the map is a moving target. I have no revision of it earlier than the 23:26:04
file, so I cannot independently confirm the 0/10 stale audit; I only confirm that every revision I
could observe has a majority of declared artifacts present.

---

## C2 — "The structural gate passes its own acceptance harness"

**Verdict: CONFIRMED** (tested on both harness revisions).

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/formulation/tools/run_gate_tests.py ; echo "EXIT=$?"
sha256sum artifacts/formulation/evidence/gate_test_report.json artifacts/formulation/evidence/gate_test_report.txt
```

Run 1 (harness rev `73fadd0a`), **exit 0**, stdout:

```
GATE TEST REPORT: PASS
canonical pass : 3/3
null controls  : 5/5
mutants caught : 22/22
rephrased leak probes caught (blind spots = misses): 0/5
  probe p01_scc_schema_wcc_meaning (WCC): MISSED -> documented blind spot
  probe p02_wcc_schema_scc_meaning (SCC): MISSED -> documented blind spot
  probe p03_c2_schema_c0_meaning (C0-regularity): MISSED -> documented blind spot
  probe p04_wcc_genericity_weakened (genericity-transfer): MISSED -> documented blind spot
  probe p05_scc_i_plus_completeness_rephrased (I+-completeness-in-SCC): MISSED -> documented blind spot
```

Run 2, **exit 0**, stdout byte-identical; report sha256 before run 2 = after run 2 =
`a0ce68af9414d076636e712de04038403bfce5ba6ae2a77ddc11bef020d8cd83`; `diff` of run1/run2 JSON = identical.

Report-vs-print consistency: `report["counts"] == {canonical_pass: 3, null_controls_pass: 5,
mutants_caught: 22, mutants_total: 22, rephrased_caught: 0, rephrased_total: 5}`, verdict `PASS`;
the `printed counts` equal those numbers, and `gate_test_report.txt` equals run stdout.
The report's `canonical_sha256` was also re-hashed against disk — all three match.

The harness writes 32 fixture files on every run. Those files were byte-identical before/after
(32/32 same sha256), so regeneration is deterministic too.

**Target moved mid-review:** at 23:28:52 another agent replaced `run_gate_tests.py` with a revision
(`b6dd4333…`) that adds a `self_application` parse/composite-label check. I re-ran the *current*
harness twice:

```
=== CURRENT-REV RUN A ===  EXIT=0
GATE TEST REPORT: PASS
canonical pass : 3/3
null controls  : 5/5
mutants caught : 22/22
rephrased leak probes caught (blind spots = misses): 0/5
self-application (parse + composite labels): clean
report sha after A: 703ddd76ad0fed2b1f54e3c48b711adef1aaebc62d34c0e46c11c8994dbea6a7
=== CURRENT-REV RUN B ===  EXIT=0
report sha after B: 703ddd76ad0fed2b1f54e3c48b711adef1aaebc62d34c0e46c11c8994dbea6a7
STDOUT A==B ; REPORT JSON A==B
```

`703ddd76…` also equals the report the concurrent agent had written at 23:28:55, i.e. the harness
is reproducible across writers on the current revision as well.

**Untested:** the harness's *assertions* are self-declared (the 22 expected rule ids come from the
harness itself); C3 therefore re-runs the gate directly rather than trusting the harness.

---

## C3 — "The gate catches 22/22 targeted mutants"

**Verdict: CONFIRMED** — direct gate invocation, not via the harness.

```bash
python3 - <<'EOF'
import json, subprocess, sys
from pathlib import Path
rep = json.loads(Path('artifacts/formulation/evidence/gate_test_report.json').read_text())
exp = {m['name']: m for m in rep['mutants']}
for n in sorted(exp):
    p = Path('artifacts/formulation/fixtures/negative')/f'{n}.yaml'
    r = subprocess.run([sys.executable,'artifacts/formulation/tools/check_class_schema.py','--json',str(p)],
                       capture_output=True,text=True)
    out = json.loads(r.stdout)
    print(n, r.returncode, out['failed_rules'], exp[n]['expected_rule'],
          exp[n]['expected_rule'] in out['failed_rules'])
EOF
```

Result: **22/22 mutants exit 1 and contain their expected rule id**; zero disagreements with the
report (`direct-run mutants with expected rule present: 22 / 22`, `disagreements: []`). Four mutants
fail additional rules (m09 `R10,R12`; m10 `R11,R12`; m12 `R06,R13`; m19 `R12,R14`) — expected rule
still present in every case.

The six requested files, raw gate output (exit 1 in all six):

```
m01_drop_quantifiers          failed_rules=['R03']  | R03: quantifiers.ordered missing/empty
m08_scc_i_plus_conclusion     failed_rules=['R09']  | R09: SCC i_plus.role must be assumption with in_conclusion=false
m12_composite_regularity      failed_rules=['R06','R13'] | R06: SCC extension_regularity 'C0 or C2' != class token 'C2'
                                                        | R13: composite regularity wording at $.regularity.extension_regularity
m13_foreign_conclusion_in_wcc failed_rules=['R12']  | R12: SCC-style inextendibility in conclusion.statement_formal
m16_verified_without_sources  failed_rules=['R15']  | R15: citation_status=verified requires identified sources
m21_no_visibility_wcc         failed_rules=['R10']  | R10: visibility.role None invalid / WCC visibility.{predicate_name,definition,negation_conclusion} missing
```

**Untested:** whether each mutant is *minimal* (exactly one semantic defect). The spec says "each
keyed to exactly one expected rule id"; m09/m10/m12/m19 trip 2 rules, so they are not single-rule
mutants, though their expected rule is caught.

---

## C4 — "100% escape rate on the 5 rephrased semantic probes"

**Verdict: CONFIRMED for the 5 corpus probes; novel probes escape at 5/8.**

```bash
for f in artifacts/formulation/fixtures/rephrased/*.yaml; do
  python3 artifacts/formulation/tools/check_class_schema.py "$f"; echo "exit=$?"
done
```

All five `exit=0 verdict=pass failed_rules=[]` (p01…p05), matching the report's
`rephrased_caught: 0/5`. The blind spot is exactly the 5/5 the claim states.

### Novel mutants (R3-authored; only under `reviews/novel_mutants/`)

Generator: `artifacts/formulation/reviews/novel_mutants/_make_novel_mutants.py`
(raw sources: `artifacts/formulation/schemas/*.yaml`). Gate run per file:
`python3 artifacts/formulation/tools/check_class_schema.py --json <file>`.

| file | category | exit | result | rules | why it escaped |
|---|---|---|---|---|---|
| `n01_scc_c2_relabelled_as_c0.yaml` | (a) swap class_id SCC↔SCC | 1 | CAUGHT | R02,R06,R11 | — |
| `n02_scc_c0_relabelled_as_c2.yaml` | (a) swap class_id SCC↔SCC | 1 | CAUGHT | R02,R06,R11 | — |
| `n03_wcc_empty_forbidden_strengthenings.yaml` | (b) empty `conclusion.forbidden_strengthenings` | 1 | CAUGHT | R11 | — |
| `n04_wcc_composite_only_in_comment.yaml` | (c) "C0 or C2" only in a YAML comment | 0 | **MISSED** | — | `yaml.safe_load` discards comments; all rules scan the parsed document, never raw text |
| `n05_scc_wcc_meaning_in_nonvacuity_condition.yaml` | (d) WCC meaning in `non_vacuity.condition` of an SCC schema | 0 | **MISSED** | — | `non_vacuity.condition` is not in `ASSERTIVE_PATHS`; R13 composite scan only looks for `C0/C2 or|and|/` patterns |
| `n06_scc_ledger_converse_entailment.yaml` | extra (e) R16 ledger records the **converse** entailment | 0 | **MISSED** | — | R16 only checks `one_way_entailments` and `forbidden_transfers` are *non-empty*; direction/content never inspected |
| `n07_scc_completeness_in_unscanned_i_plus_key.yaml` | extra (f) SCC `i_plus.completeness_definition` asserts completeness | 0 | **MISSED** | — | R09 SCC completeness scan covers only `i_plus.definition` and `i_plus.required_properties` (substring "complete"); `completeness_definition` is unscanned |
| `n08_wcc_provenance_establishes_conclusion.yaml` | extra (g) verified source "establishes the class conclusion" | 0 | **MISSED** | — | R15 has no implementation of its clause "no source is presented as establishing the class conclusion" |

Raw output excerpt:

```
exit=1 CAUGHT n01_scc_c2_relabelled_as_c0.yaml ['R02', 'R06', 'R11']
exit=1 CAUGHT n02_scc_c0_relabelled_as_c2.yaml ['R02', 'R06', 'R11']
exit=1 CAUGHT n03_wcc_empty_forbidden_strengthenings.yaml ['R11']
exit=0 MISSED n04_wcc_composite_only_in_comment.yaml []
exit=0 MISSED n05_scc_wcc_meaning_in_nonvacuity_condition.yaml []
exit=0 MISSED n06_scc_ledger_converse_entailment.yaml []
exit=0 MISSED n07_scc_completeness_in_unscanned_i_plus_key.yaml []
exit=0 MISSED n08_wcc_provenance_establishes_conclusion.yaml []
```

For (c) I verified the mutation is comment-only: the parsed doc of n04 is **equal** to the parsed
canonical WCC doc, while the raw text contains `C0 or C2`.

**Escape rate on novel mutants: 5/8 files** (2/4 requested categories: (a),(b) caught; (c),(d) escaped).
Note n05's target field is literally named in the gate's own docstring as a known blind spot
("lexical leakage scan covers ASSERTIVE_PATHS only"); n06/n07/n08 are **not** acknowledged blind
spots — they are rules whose implementation is weaker than `rule_spec.json` (§C5).

**Could not test:** no rephrased probe for the C0/C2 axis beyond p03, and no probe exercising
`falsifier` prose fields; I did not exhaustively enumerate unscanned string fields.

---

## C5 — "The canonical schemas satisfy the rule spec"

**Verdict: CONFIRMED for the three canonical schemas, with documented implementation gaps.**

```bash
for f in artifacts/formulation/schemas/af_wcc_vacuum.yaml \
         artifacts/formulation/schemas/af_scc_c2_vacuum.yaml \
         artifacts/formulation/schemas/af_scc_c0_vacuum.yaml; do
  python3 artifacts/formulation/tools/check_class_schema.py "$f"; echo "exit=$?"
done
```

```
PASS artifacts/formulation/schemas/af_wcc_vacuum.yaml     class=AF-WCC-VAC-GEN     failed_rules=[]  exit=0
PASS artifacts/formulation/schemas/af_scc_c2_vacuum.yaml  class=AF-SCC-C2-VAC-GEN  failed_rules=[]  exit=0
PASS artifacts/formulation/schemas/af_scc_c0_vacuum.yaml  class=AF-SCC-C0-VAC-GEN  failed_rules=[]  exit=0
```

### Manual intent check (primary: R16 implication ledger)

Read from the YAML text, not the string check:

* `af_scc_c2_vacuum.yaml` → `one_way_entailments: [{from: "no proper future C0 extension",
  to: "no proper future C2 extension", relation: entails, reason: "every C2 extension is a C0
  extension (extension-class containment); so C0-inextendibility is the stronger statement"}]`.
  Since C2 extensions ⊂ C0 extensions, "no C0 extension" ⇒ "no C2 extension". **Direction is
  logically correct.** `forbidden_transfers` lists the converse (`no C2 extension → no C0
  extension`, reason "the converse containment is false"), `H2_loc → this class`, and
  `AF-WCC-VAC-GEN → this class`. **R16 intent is genuinely met.**
* `af_scc_c0_vacuum.yaml` → correct too: C0-metric-inextendibility ⇒ C2-inextendibility, and
  C0-metric-inextendibility ⇒ no distributional-vacuum C0 extension (distributional Ric=0
  extensions ⊂ continuous metric extensions); the weaker converse is forbidden with the reason
  that C2 is a strictly larger extension class.

Spot checks of R09 and R12 on the canonical files also match intent: SCC `i_plus` is
`role: assumption`, `in_conclusion: false`, `completeness_in_conclusion: false`, with an explicit
`forbidden` list barring I+ completeness; the WCC assertive blocks carry no SCC-family token.

### Rule implementations weaker than their stated intent (evidence-backed)

1. **R16 (strongest).** Spec: "records the one-way statements (C2 ⊂ C0; therefore
   C0-inextendibility entails C2-inextendibility) and marks the converse … as forbidden_or_unresolved".
   Implementation (lines 333–336) is `if not il.get("one_way_entailments") or not
   il.get("forbidden_transfers"): fail` — a pure non-emptiness test. **Proof: `n06` records the
   converse entailment and passes.**
2. **R09.** Spec: SCC has "no completeness assertion inside i_plus". Implementation scans only
   `i_plus.definition` and `i_plus.required_properties` for the substring `complete`. **Proof:
   `n07` hides completeness in `i_plus.completeness_definition` and passes.** The check is also
   lexical in the other direction: a control with `definition: "I+ is NOT assumed complete …"`
   fails R09 (`exit=1`, "SCC i_plus asserts completeness outside a forbidden list") — a false
   positive. Control run in `/tmp/r3_neg_complete.yaml` (scratch, not a deliverable).
3. **R12.** Spec scans the `leakage_scan_blocks` `[conclusion, visibility, i_plus, falsifier]`;
   implementation hardcodes 18 `ASSERTIVE_PATHS`, so prose fields inside those blocks or elsewhere
   are unscanned. **Proof: `n05` puts unambiguous WCC meaning in the SCC schema's
   `non_vacuity.condition` and passes.** Also, the spec's clause "occurrences inside
   anti_scope/variants are exempt but **must be tagged**" has no implementation —
   `grep -n "tag" check_class_schema.py` → no match.
4. **R15.** Spec: "no source is presented as establishing the class conclusion". Implementation
   checks only vocabulary membership, source identifiers when `verified`, and presence of
   `unresolved_citations`. **Proof: `n08` marks a source "establishes: the class conclusion" and
   passes.**

---

## Moving-target / concurrency caveat

The workspace was being edited by other agents throughout. Files observed changing **not** by R3:
`run_gate_tests.py` (23:28:52, new revision), `research_map.json` (23:26:04 → 23:28:19 → 23:29:35),
`evaluation/ablation.csv` (created 23:27:43), `schemas/af_scc_regularities.yaml` (created 23:28:07),
plus `artifacts/formulation/proposals/map_patch_F0_F1_F2.json` and `tools/apply_map_proposal.py`
(23:27:04–07, changed while C2 run 1/2 were executing). Every number above is a timestamped
snapshot; re-running later may differ. `check_class_schema.py` itself never changed during the
review (`84f1aa2f…`), so C3/C4/C5 gate verdicts are stable across the whole window.
