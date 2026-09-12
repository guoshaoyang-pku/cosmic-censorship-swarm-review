# W097-F1-FALSIFIER-EXEC-01 — executing the F1 falsifier/ambiguity suite

Worker: `worker-097` (bounded execution worker) · Node **F1** · Class **AF-WCC-VAC-GEN** · Gate **G-FORM**

Authority: **worker measurement only.** No gate verdict, no node completion, no
`validation_status` promotion, and no claim about cosmic censorship itself. This is an
artifact audit submitted for lead/controller adjudication.

## Question

`schemas/f1_falsifier_tests.jsonl` (25 rows, author deepseek-flash-04) records, for each
ambiguity probe, a *deciding field* and one or more *probe results*. Until now the suite had
only been hash-checked, never **executed**: does the canonical F1 schema
(`schemas/af_wcc_vacuum.yaml`) actually decide each row from the field the row names?

## Method

`run_f1_falsifier_exec.py` (this directory) does, at pinned bytes:

1. Measures sha256 of the schema and the suite, snapshots both, and re-measures at the end
   (any drift voids the run rather than changing the verdict).
2. Resolves every `deciding_field`, `deciding_field_contract` and alternate as a dotted path
   (with `[*]` list mapping and `A plus B` composites) in the parsed schema.
3. Classifies each row:
   - `RESOLVED_DETERMINATE` — primary deciding field resolves, status is determinate;
   - `RESOLVED_OPEN_OBLIGATION` — resolves, but the row's own status/unresolved keywords
     declare an open obligation;
   - `ALTERNATE_ONLY` / `UNRESOLVED_PATH` — the named field does not resolve.
4. Independently re-executes all 84 probe entries: resolves the probe's own `path` and checks
   `contains` / `equals` / `is_true` / `is_none` / `nonnull` / `path_exists` against the
   resolved value, including a normalized prefix check that the recorded (usually truncated)
   `observed_excerpt` really was cut from that value. Author `pass` flags are compared with the
   executed result.
5. Runs six negative/positive controls (missing subtree, bogus field, probe
   present/absent discrimination, probe path binding, stale binding hash, unmodified
   baseline). The run **fails closed** (exit 2, no findings published) if any control fails.

## Pinned inputs (measured at run time)

| input | sha256 |
|---|---|
| `schemas/af_wcc_vacuum.yaml` | `9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503` |
| `schemas/f1_falsifier_tests.jsonl` | `c4c477adcb7ab88995c417e8c8c9ef4b9b0415e569babefb61894df3b8425ec2` |

Both hashes were stable before and after execution (`report.json → drift`). Snapshots are in
`snapshots/`.

## Result at these hashes

- **25/25 rows bind to the measured schema hash** — the suite is current, not stale.
- **21/25 rows are `RESOLVED_DETERMINATE`; 4/25 are `RESOLVED_OPEN_OBLIGATION`.**
- **0/25 rows are undecidable for want of a field** — every named primary deciding field
  resolves in the schema.
- **84/84 probes reproduce under independent execution**, and **0 probes disagree with the
  author's `pass` flag**.
- **6/6 controls pass.**

Findings recorded in `report.json`:

- **F-3 (minor, naming drift):** two `deciding_field_contract` expressions do not resolve
  verbatim in the schema — `class_components.symmetry` (the schema keeps symmetry at
  `data_class.symmetry`) and `conclusion.equivalence_claim` (the schema key is
  `conclusion.equivalent_standard_formulation`). The rows themselves still resolve through
  their primary fields; this is pointer/vocabulary drift between suite and schema, not a
  missing decision.
- **F-6 (info, declared obligations):** rows `F1-AMB-01`, `F1-AMB-02`, `F1-AMB-03`,
  `F1-AMB-15` resolve to fields whose own status declares an open obligation
  (`non_vacuity.condition`, `genericity.excluded_set`, `conclusion.equivalent_standard_formulation`).
  The schema decides the *shape* of these obligations but not the obligations themselves;
  that is disclosed by the schema and by the rows.

There is **no F-1/F-2/F-4/F-5/F-7** at this hash: no unresolvable deciding field, no stale
binding, no unreproducible probe, no probe contradicting its author.

## Interpretation limits

This instrument measures **executability and internal consistency of the suite against the
frozen schema**. It does **not** decide whether F1 should pass G-FORM, whether the schema's
formulation is physically correct, or whether any ambiguity is mathematically resolved. A
revision of either input changes the hashes above and voids this report rather than
falsifying it.

## Falsifier

Re-run this instrument at the same pinned hashes and exhibit a row whose reported
`decisability_class` differs from `report.json`, or a row classified `UNRESOLVED_PATH` whose
deciding field is present under the schema's own key spelling. Alternatively, show a control
that passes when it should fail (the instrument is then not fail-closed).

## Next falsifier

Run the same execution against the next F1 revision and the next suite binding. A row moving
between `UNRESOLVED_PATH`/`ALTERNATE_ONLY` and `RESOLVED_DETERMINATE`, or a change in the
four declared obligations, is the next measurement.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-097/f1_falsifier_exec/run_f1_falsifier_exec.py   # exit 0 = controls passed
```

Writes `report.json` and `raw_sha256.txt` next to the script. No input file is modified.
