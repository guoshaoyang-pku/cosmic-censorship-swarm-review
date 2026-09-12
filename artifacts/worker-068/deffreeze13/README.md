# W068-FORM-DEFFREEZE-13 — definition-site freeze (R-CAND-D) and the mutation-isolation confound

**Worker:** worker-068 (bounded task, no inbox card). **Node:** A1. **Gate:** G-CLASSBIND
(folded into G-AUDIT as calibration evidence). **Classes:** AF-WCC-VAC-GEN,
AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN. **Status:** measurement complete; rule is a proposal,
not adopted; no gate verdict and no node transition claimed.

Successor to `W068-P12-G1` (FORM-POLARITY-12): the four FORM-HELDOUT-08 reference escapes
(`m04` adm-mass-erasure, `m16` containment-reversal, `m25` completeness-definition-swap,
`m29` data-domain-contradiction) escape both class-binding stages with conclusion statements
identical to the frozen base, so the conclusion-statement freeze R-CAND-F cannot see them.
This task measures a declared **definition-site freeze R-CAND-D** on those four families and
on the union corpora, and audits whether the reference-corpus catch is attributable to the
labelled mutation or to incidental rev8→rev11 drift.

## Method (all bytes pinned; the rule never reads the live tree)

| input | sha256 (12) |
|---|---|
| stage A `check_class_schema.py` | `000e09e46b2f` |
| stage B `spec_conformance_audit.py` | `c79d8ab8440a` |
| rule spec `rule_spec.json` | `40f9bb9e657b` |
| W / C2 / C0 rev11 bases | `9a8bd4c96800` / `b6123750b37d` / `1bb78ce9b357` |

1. **Reproduction.** Re-ran both pinned stages on the 4 reference fixtures; all four escape
   and every verdict matches the frozen `heldout3/raw_verdicts.json` (4/4 match).
2. **Mutation isolation.** `build_isolated.py` starts from the pinned rev11 base and applies
   ONLY the labelled leaf value taken from the reference fixture, then verifies by structural
   leaf diff that exactly one leaf changed. Result: `m04 → data_class.adm_mass.sign`,
   `m16 → implication_ledger.extension_class_containment`,
   `m25 → i_plus.completeness_definition`, `m29 → quantifiers.domains.D2.definition`.
3. **Stages on the isolated corpus.** Both pinned stages accept all four isolated fixtures —
   the escape is caused by the labelled mutation itself, with the rev8→rev11 drift removed.
4. **Freeze evaluation.** R-CAND-D variants applied to the 4 reference, the 4 isolated, the
   union corpora (`heldout3` + `polarity10` + `polarity11`, 18 escape instances, 12 conforming
   controls) and the FORM-POLARITY-12 corpus (27 content probes, 3 identity controls), plus
   19 conforming/formatting controls.
5. **Minimal-surface search.** Exhaustive over the declared site taxonomy for 4/4 catch with
   zero control false positives.

## Results

### 1. The four labelled mutations escape in isolation (confound removed)

| fixture | mutated leaf (verified single) | group | stage A | stage B | escape |
|---|---|---|---|---|---|
| `iso_m04` | `data_class.adm_mass.sign` | DATA | pass | accept | **yes** |
| `iso_m16` | `implication_ledger.extension_class_containment` | LEDGER | pass | accept | **yes** |
| `iso_m25` | `i_plus.completeness_definition` | IPLUS | pass | accept | **yes** |
| `iso_m29` | `quantifiers.domains.D2.definition` | QUANT | pass | accept | **yes** |

### 2. The reference-corpus catch is confounded

On the original reference fixtures a **metadata-only** freeze (revision counters, f0 binding
hashes/timestamps) flags 4/4 and an **identity-registry-only** freeze flags 4/4, while the
conclusion freeze flags 0/4. The minimal group family that catches the reference four is
`{META}` alone; on the isolated four it is exactly `{QUANT, DATA, IPLUS, LEDGER}`. The
reference corpus therefore cannot attribute a catch to the labelled mutation site.

### 3. R-CAND-D catch / false-positive matrix

| variant | isolated 4 | reference 4 | union escapes (18) | P12 content probes (27) | control FP (19) |
|---|---|---|---|---|---|
| `freeze_meta_only` | 0 | 4 | 5 | 0 | 0 |
| `freeze_conclusion` (R-CAND-F) | 0 | 0 | 14 | 27 | 0 |
| `freeze_defsites_min` | **4** | 4 | 5 | 0 | **0** |
| `freeze_contract_min` (defsites + CONC) | **4** | 4 | **18** | **27** | **0** |
| `freeze_defsites_core` | **4** | 4 | 5 | 0 | **0** |
| `freeze_contract_full` | **4** | 4 | **18** | **27** | **0** |
| `freeze_identity` | 0 | 4 | 4 | 0 | 2 |
| `freeze_all_minus_meta` | 4 | 4 | 18 | 27 | 2 |
| `freeze_all` | 4 | 4 | 18 | 27 | 2 |

The 2 control false positives of the identity-inclusive variants are the two **legitimate
registry-annotation controls** (`ctrl_c2_antiscope_note`, `ctrl_c0_variant_registered`) that
both stages accept: an identity-registry freeze must stay outside a contract freeze unless the
owner re-freezes registry annotations. All four formatting-only derivatives (comment
prepend/append, PyYAML re-serialisation, byte-identical copy under a new name) have zero
structural changes against their own source control and pass **every** variant.

### 4. Recommended surface (proposal)

`freeze_contract_min` = `{quantifiers, data_class, i_plus, implication_ledger,
extension_predicate, conclusion}`: catches 4/4 isolated definition-axis escapes, 27/27
statement-axis probes, 18/18 union escapes, with 0/19 control false positives.
`freeze_contract_full` adds `topology, regularity, genericity, scope_statement, c0_specifics`
at the same measured catch and FP. `EXT` carries no isolated mutation in this corpus but is
kept for union coverage; dropping it does not change any measured number.

## Findings (each with an executable falsifier in `report.json`)

- **W068-D13-F1** — the four labelled mutations escape both stages when isolated to exactly
  one leaf on the pinned base.
- **W068-D13-F2** — the reference-corpus catch is confounded: metadata-only and
  identity-only freezes each flag 4/4 while the conclusion freeze flags 0/4.
- **W068-D13-F3** — `freeze_defsites_min` / `freeze_contract_min` catch the four isolated
  escapes with zero control false positives; the minimal isolated family is
  `{QUANT, DATA, IPLUS, LEDGER}`.
- **W068-D13-F4** — formatting-only controls pass every variant; identity-inclusive variants
  flag the two legitimate registry-annotation controls.

## Artifacts

`definition_freeze_check.py` (R-CAND-D) · `build_isolated.py` ·
`isolated_manifest.json` · `isolated/iso_m{04,16,25,29}.yaml` · `run_deffreeze13.py` ·
`raw_verdicts.json` · `report.json` · `candidate_rule.json` · `checkpoint.json` /
`checkpoint_final.json`.

## Reproduction

```bash
cd <repo>
python3 artifacts/worker-068/deffreeze13/build_isolated.py
python3 artifacts/worker-068/deffreeze13/run_deffreeze13.py
python3 artifacts/worker-068/deffreeze13/definition_freeze_check.py \
    --fixture artifacts/worker-068/deffreeze13/isolated/iso_m25.yaml \
    --base    artifacts/worker-068/polarity12/shadow/schemas/af_wcc_vacuum.yaml \
    --variant freeze_contract_min --json
```

## Non-claims and limitations

- Author-built isolated corpus: the four mutation values are copied from worker-068's own
  heldout3 reference fixtures and the labels remain worker-068's. An independent reviewer must
  adjudicate each as a genuine class-contract violation; an independent executor (not
  worker-068) must reproduce the 4/4 isolated escape.
- The union and FORM-POLARITY-12 evaluations re-use worker-068-built corpora at pinned bytes;
  they are re-analyses, not an independent corpus.
- A freeze rule decides contract invariance, not mathematics: any legitimate post-freeze
  revision of a covered site requires an owner re-freeze of the class contract.
- The minimal-subset result is exact over the declared site taxonomy; a different taxonomy
  (e.g. splitting `data_class`) would yield a different minimal family.
- No gate verdict, node completion, or `validation_status=passed` is claimed.

## Falsifier

Any mutation-isolated fixture not flagged by `freeze_defsites_min`; any conforming control
flagged by `freeze_contract_min` / `freeze_contract_full`; any pinned-input drift between
build and run; or a stage verdict for an isolated fixture that contradicts the measured 4/4
escape.
