# W047-GFORM-D0-XCLASS-01 — cross-class D0 adjudication (F1 / F2a / F2b)

Actor: `worker-047`. Node scope: `F1`, `F2a`, `F2b`; gate `G-FORM`. Classes:
`AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`.
Authority: worker evidence only — no gate verdict, no node status, no canonical-file edit,
no amendment of any class artifact.

## Question

Every canonical G-FORM schema binds `forall (s,delta) in D0` and indexes `G_{s,delta}` and
`X^{s,delta}_vac(AF)` by that pair, while `D0.definition` is a two-member disjunction whose
second member is "the smooth-with-decay default". F2a reviewers 086 and 088 (and the audit
lead's r3) called this a blocking typing defect on **F2a**. The same text is present in
**F1** and **F2b**; F2b carries accept verdicts. This task measures the defect across all
three classes with one instrument and calibrates that instrument with controls.

## Method

`check_d0_cross_class_047.py` (sha256 `a065a9bcf590`) reads the three canonical schemas,
snapshots them, and runs 13 checks + 7 controls. No network. Fail-closed on unreadable input.
`--strict` exits 1 while any check FAILs, so the same script is the acceptance test for a
repair.

Pinned inputs (all byte-stable across the read):

| node | class | path | sha256 |
|---|---|---|---|
| F1 | AF-WCC-VAC-GEN | `schemas/af_wcc_vacuum.yaml` | `9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503` |
| F2a | AF-SCC-C2-VAC-GEN | `schemas/af_scc_c2_vacuum.yaml` | `b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2` |
| F2b | AF-SCC-C0-VAC-GEN | `schemas/af_scc_c0_vacuum.yaml` | `1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508` |

Frozen evidence: `report.json` (sha256 `f10c7b42a8b0`), byte copies under `snapshot/`,
`snapshot/MANIFEST.json`, `checkpoint.json`.

## Result

Checks FAIL: `C02` (duplicate top-level YAML keys), `C05` (D0 typing), `C06` (no ambient
object for the smooth branch), `C09` (pair-indexed objects over a non-pair D0 member),
`C10` (neither repair-acceptance shape present). Controls: **7/7 PASS**.

1. **F-047-XCLASS-3 (critical, all three classes).** `D0` is two disjuncts; the
   smooth-with-decay member supplies no `(s,delta)` instantiation; the binder, the
   quantifier block and `conclusion.statement_formal` are all pair-typed and
   pair-indexed. The artifact formalises a union of two class statements, not one
   well-typed class statement. This is not an F2a-local defect: F2a and F2b have
   byte-identical `D0` text (`C03`), and F1 differs only by a trailing
   "the class is fixed at these values…" clause.
2. **F-047-XCLASS-4 (major, all three classes).** The only structurally declared ambient
   object is the weighted Sobolev `X^{s,delta}_vac(AF)` (`genericity.ambient_space`); the
   smooth branch has only a Fréchet topology named. Comeagerness is therefore undefined on
   that branch (`C06`). A prose-proximity probe false-positived on F2b; it was replaced by a
   structural probe and the false positive is regression-pinned as control `K6`.
3. **F-047-XCLASS-2 (major, all three classes).** Duplicate top-level YAML mapping keys:
   `revised_at` ×7 (F1) / ×8 (F2a, F2b) plus `revised_at_unused` ×2 (F1). PyYAML last-wins,
   so the effective revision timestamp is parser-dependent. Already reported for F2a; it is
   cross-class.
4. **F-047-XCLASS-1 (major, review-corpus consistency).** F2a and F2b carry identical `D0`
   text, but at the pinned hashes the distinct accept reviewers are
   F2a `{worker-047, worker-050, worker-098}` vs F2b
   `{deepseek-flash-07, deepseek-flash-17, worker-001, worker-030, worker-060, worker-089, worker-096}`,
   and F1 has none. Either the D0 defect blocks all three (then the F2b accepts and my own
   earlier F2a accept are unsound) or it blocks none (then the F2a/F1 revise verdicts are
   over-strict). The gate owner must adjudicate; this report supplies the measurement, not
   the verdict.
5. **F1/F2a/F2b data class.** Key-level diff (`C07`): F1 alone carries
   `data_class.excluded_data`; values also differ on `adm_mass`, `asymptotic_decay`,
   `diffeo_quotient`, `gauge`, `regularity_class`; F2a==F2b textually on `regularity_class`.
   So the "single shared frozen data class" is exact only for F2a/F2b.

## Minimal repair options

`C10` shows neither shape is present. Two shapes satisfy the instrument
(`--strict` → exit 0):

* **R1 — collapse D0 to one parameterised regime** (`d0_disjuncts == 1`, pair supplied).
  Cheapest, but the smooth-with-decay default must then be stated as a separate class or a
  limit statement, not a D0 member.
* **R2 — typed union**: keep the smooth default, give it a structurally declared ambient
  object (e.g. a key under `genericity`), define comeagerness per branch, and state the class
  statement as the conjunction over members. Preserves the intended "default + Sobolev
  variant" reading and keeps one shared data class across the siblings.

## Falsifier

At the pinned hashes in `report.json.inputs`:

* (a) falsified if the smooth disjunct is shown to supply an `(s,delta)` instantiation or to
  have a declared ambient set plus comeagerness definition;
* (b) falsified if the three `D0` definitions are shown not to share the disjunctive member;
* (c) falsified if the duplicate-key scan is a false positive under strict YAML 1.2;
* (d) falsified if the recorded verdict profiles at those hashes are equal after reviewer
  dedup.

A later file write is not a falsifier: the verdict binds only to the pinned hashes.

## Not claimed

No truth claim about weak/strong cosmic censorship; no claim that the D0 defect changes any
mathematical content (it is a formalisation/typing defect); no gate verdict — G-FORM remains
pending; no new verdict on F1 or F2b. The accompanying outbox `review` event withdraws only
worker-047's own earlier F2a accept at `b6123750b37d`.

## Reproduce

```bash
python3 artifacts/worker-047/d0_cross_class/check_d0_cross_class_047.py \
  --out artifacts/worker-047/d0_cross_class/report.json \
  --snapshot-dir artifacts/worker-047/d0_cross_class/snapshot
```
