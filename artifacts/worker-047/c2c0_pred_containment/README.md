# W047-C2C0-PRED-CONTAINMENT-01 — does the declared C2/C0 extension predicate pair entail `E_C2 ⊆ E_C0`?

**Actor:** worker-047 · **When:** 2026-09-12 ~01:14 +08:00 · **Status:** worker task complete; `DEFECT`; focused verification (**not** a full-schema verdict, **not** countable toward G-FORM two-accept coverage).
**Nodes:** F2a, F2b, F0, A1 · **Classes:** `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN` (cross-class).

## Why this task

No assignment card existed in `comms/inbox/worker-047.jsonl` at launch (fleet 2026-09-12T01:08). After reading
`HANDOFF.md`, `research_map/ASTRA_HANDOFF.md`, `research_map.json` and all comms, one bounded class-bound gap was
selected that no in-flight worker covered at selection time: the **containment premise** shared by four loci —
F2a's `class_boundary.one_way_implication`, F2a's `implication_ledger`, the F0 supplement, and taxonomy transfer
rule T1. The F2a predicate **under-freezing** itself is already reported (worker-047 HF-047-01 at rev13,
worker-091 HF-091-02 at rev29); the F2b line-246 inverted-reason carrier is already reported (worker-017/018/075).
The increment here is the **justification-soundness consequence**: whether the containment those loci rely on is
entailed by the *declared clause pair* at the current pins, plus the **T1 guard gap** that would let a claim
transfer pass every declared guard across two non-aligned predicates.

## Question

At the pinned rev13 canonical bytes, does `E_C2 ⊆ E_C0` — "every C2 extension is a C0 extension", the stated
reason for the C0⇒C2 transfer — follow from the declared `extension_predicate` clauses of the two siblings?

## Pins (measured; instrument exits 2 on any drift)

| input | sha256 (12) | bytes |
|---|---|---|
| `schemas/af_scc_c2_vacuum.yaml` (F2a) | `e9a27996dfd3` | 30594 |
| `schemas/af_scc_c0_vacuum.yaml` (F2b) | `b2ab6acb2bbe` | 35602 |
| `schemas/af_wcc_vacuum.yaml` (F1) | `d9cebb9404b2` | 37662 |
| `research_map/formulation_taxonomy.yaml` (F0) | `0abb9ed8a961` | 36372 |
| `artifacts/formulation/formulation_taxonomy.yaml` (F0 supplement) | `d7419b4e8963` | 21699 |
| `artifacts/formulation/FROZEN.json` (rev29) | `815e08079aef` | 24805 |
| three `artifacts/formulation/schemas/*` mirrors | byte-identical to canonical | — |

Byte copies: `snapshot/` + `snapshot/PINS.json` + `snapshot/SHA256SUMS`.

## Method

`check_c2c0_pred_containment_047.py` (stdlib only, no network, read-only outside this directory): parses clauses
(c), (d), (f) of both `extension_predicate` definitions from the pinned text; locates the four containment-premise
loci; tests containment soundness and T1 guard coverage; then runs **9 synthetic mutants as controls**. Checks were
pre-registered in the instrument before the reported runs. Exit semantics: `0` defect verified, `4` clean,
`2` input drift, `3` control mis-calibration, `5` unparsed, and `--strict` → `1` while any contract check FAILs
(so the instrument doubles as the repair-acceptance test). Three runs are byte-identical modulo `created_at` and the
controls path; `--strict` returns 1.

## Decisive table

| # | check | result | evidence |
|---|---|---|---|
| C01 | F2a clause (c) declares a manifold category | **FAIL** | `af_scc_c2_vacuum.yaml#e9a27996dfd3:95` — "M' is connected and time-orientable" |
| C02 | F2a clause (f) requires an interior witness | **FAIL** | `:98` — witness only `p in M' minus iota(M)` |
| C03 | F2b clause (c) declares SMOOTH | PASS | `af_scc_c0_vacuum.yaml#b2ab6acb2bbe:91` |
| C04 | F2b clause (f) requires interior witness | PASS | `:94` — `int(M' minus iota(M))` non-empty + witness in it |
| C05 | F2b clause (f) strictly stronger than F2a's | PASS | asymmetry confirmed; F2b's own note blocks "boundary/dense-open" additions |
| C06 | F2a predicate well-posed (C2 metric needs a smooth structure) | **FAIL** | clause (d) `:96` requires a C2 metric; no smooth structure declared at `:95`/`:117` |
| C07 | F2a ledger asserts the containment premise | PASS | `:239` reason "E_C2 subset of E_C0" |
| C08 | F0 supplement asserts the containment premise | PASS | `formulation_taxonomy.yaml#d7419b4e8963:191` |
| C09 | taxonomy T1 guards cover the predicate-convention axis | **FAIL** | `formulation_taxonomy.yaml#0abb9ed8a961:500-503` — guards cover data_class, genericity, artifacts only |
| C10 | explicit cross-class predicate-alignment declaration exists | **FAIL** | no hit in any pinned artifact |
| C11 | containment licensed by the declared bytes | **FAIL** | C01/C02/C06 FAIL and C10 FAIL — the premise needs an unstated convention |
| C12–C15 | INFO: H2_loc middle term is registry-level; sibling data_class/genericity differ only in prose (`adm_mass` locator, `excluded_set`); a fourth premise locus at F2a `:78` | INFO | — |

**Controls 9/9:** K1 add SMOOTH to F2a (c) → C01/C06 flip; K2 add interior to F2a (f) → C02 flips, C05 flips;
K3 both → C11 flips to PASS; K4 strip SMOOTH from F2b → C03 flips; K5 strip interior from F2b → C04/C05 flip;
K6 add the predicate guard to T1 → C09 flips; K7 add an alignment declaration → C10/C11 flip; K8 reverse the
ledger containment → C07 flips; K9 truncate F2a → parse fail-closed detected.

## Findings

- **F-PC-1 (critical, cross-class justification gap).** At these pins the declared clause pair does **not** entail
  `E_C2 ⊆ E_C0`: F2a clause (c) is category-silent and clause (f) admits a boundary witness, while F2b clause (c)
  requires a SMOOTH `M'` and clause (f) requires the witness in `int(M' minus iota(M))` (its own note: this
  "blocks an extension that only adds boundary/dense-open points"). Four loci rely on the premise anyway: F2a
  `class_boundary.one_way_implication` (`:78`), F2a `implication_ledger` (`:239`), F0 supplement (`:191`), taxonomy
  T1 (`:495-503`). The premise is therefore **conditional on an undeclared cross-class convention**, not derivable
  from the pinned definitions.
- **F-PC-2 (major, transfer-rule guard gap).** T1's guards check `data_class` and `genericity` equality but not the
  extension-predicate convention axis, so a claim can pass every declared guard while source and target predicates
  disagree on manifold category / interior witness.
- **F-PC-3 (major).** No pinned artifact declares that the two siblings share those conventions.
- **F-PC-4 (info).** Four independent premise loci inventoried above.
- **F-PC-5 (info, scope).** Corroborates HF-047-01 / HF-091-02 (under-freezing) and the line-246 carrier findings;
  the new content is the containment-consequence and the T1 guard gap, not the under-freezing observation.

## Minimal repairs

- **R1 (preferred, already specced):** apply the option-A repair in
  `artifacts/worker-047/f2a_ext_freeze_spec/` to F2a — align clauses (c)/(f) with the accepted F2b F2b-16-03
  smooth-category and interior-witness repair; then re-run this instrument; expectation C01/C02/C06/C10/C11 → PASS.
- **R2 (alternative):** keep F2a as is and add to T1 the guard "the extension-predicate conventions must match
  exactly (manifold category and clause (f) interior witness)", plus an explicit alignment declaration in F2a;
  then re-run; expectation C09/C10 → PASS (C11 licensed by declaration).
- **R3 (honest weakening):** mark the four premise loci as conditional on the alignment convention until R1/R2 lands.
- A new F2a revision is needed for R1/R2; this artifact directory is the only thing this worker wrote.

## Falsifier

Falsified if, at the pins in `report.json`: (a) F2a clause (c) is shown to entail a smooth manifold category (via a
definition, taxonomy binding, or canonical convention note in the pinned artifacts); (b) F2a clause (f) is shown to
entail the interior-witness condition; (c) T1's guard set is shown to include the extension-predicate convention
axis; or (d) an explicit cross-class predicate-alignment declaration is shown to exist in a pinned artifact. **A
later file write at a new hash is not a falsifier** — the new bytes must be measured and this instrument re-run.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-047/c2c0_pred_containment/check_c2c0_pred_containment_047.py \
  --json-out artifacts/worker-047/c2c0_pred_containment/report.json \
  --controls-out artifacts/worker-047/c2c0_pred_containment/controls/control_results.json
# exit 0 = defect verified; add --strict for exit 1 while any contract check FAILs
```

## Limits / non-claims

This is **not** a claim that the containment or the C0⇒C2 transfer is mathematically false, and **not** a claim that
a boundary-only extension exists. It is a justification-soundness finding about the pinned bytes. It is a focused
axis verification (`counts_as_full_schema_verdict=false`), sets no node status, no `validation_status=passed`, and
no gate verdict. All authority stays with the controller / formulation and audit leads.
