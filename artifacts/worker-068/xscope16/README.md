# W068-CLASSBIND-XSCOPE-16 — cross-artifact axis-level disjointness census

Bounded class-bound task taken by worker-068 (no inbox card existed for this slot). Node A1;
gate G-CLASSBIND (folded into G-AUDIT as calibration evidence). Read-only on every canonical
path; the only writes are this task's own artifacts.

## Question

For the four frozen formulation classes, does the axis-level separation declared in the canonical
F0 `disjointness` table agree with (a) the class axis values actually recorded in the same file,
and (b) the supplement `disjointness_matrix` basis prose and `axis_registry` freezes? Every
verdict is bound to measured bytes.

## Pins (measured, fail-closed preflight; exit 2 on any drift)

| path | sha256 (prefix) | bytes |
|---|---|---|
| research_map/formulation_taxonomy.yaml (F0 canonical) | `0abb9ed8a961` | 36372 |
| artifacts/formulation/formulation_taxonomy.yaml (F0 supplement) | `d7419b4e8963` | 21699 |
| artifacts/formulation/FROZEN.json (rev29) | `815e08079aef` | 24805 |
| schemas/taxonomy_cases.jsonl | `ccf7041bd0ff` | 58791 |
| schemas/af_wcc_vacuum.yaml (F1) | `d9cebb9404b2` | 37662 |
| schemas/af_scc_c2_vacuum.yaml (F2a) | `e9a27996dfd3` | 30594 |
| schemas/af_scc_c0_vacuum.yaml (F2b) | `b2ab6acb2bbe` | 35602 |
| artifacts/formulation/VARIANT_REGISTRY.json | `6bac9adea19e` | 10811 |

Full hashes are in `PREREGISTRATION.json` and `raw_census.json::measured_pins`.

## Rules (fixed in PREREGISTRATION.json before the first run)

- **R1** canonical pair set == supplement pair set.
- **R2** every axis named in a canonical row's `decisive_axes` must have differing values in
  `classes[*].axes` (else EQUAL / MISSING_AXIS, a finding).
- **R3** any *undeclared* axis whose two values differ is recorded as UNDECLARED_SEPARATOR (info).
- **R4** the supplement basis prose, token-mapped by the pre-registered phrase table, is compared
  with the canonical decisive-axis set (SUBSET/SUPERSET/CROSS/DISJOINT_NONEMPTY/EMPTY).
- **R5** supplement `axis_registry[*].frozen` values are compared with canonical axis tokens for
  the mapped axes (`regularity_axis`→`regularity_token`, `genericity_axis`→`genericity_kind`).
- **R6** canonical `genericity_value_status` recorded as context, no verdict derived.

## Result (6 pairs × declared axes = 18 cells)

| check | result |
|---|---|
| R1 pair sets | **EQUAL** — 6 unordered pairs in both artifacts |
| R2 declared decisive axes | **18/18 DIFFERS** (0 EQUAL, 0 MISSING_AXIS) |
| R3 undeclared separators | **5** (info) |
| R4 supplement basis vs canonical decisive set | **6/6 SUBSET** (no over-claim) |
| R5 registry-vs-canonical tokens | `regularity_axis` 2/2 MATCH; `genericity_axis` **1 MATCH, 3 TOKEN_DIFFERS** |
| predictions P1–P6 | **6/6 matched** |
| planted controls K1–K6 | **6/6 pass** (`--selftest`, exit 0) |

So at F0 rev5 the canonical disjointness table is axis-level sound: every axis it calls decisive
really does separate the two class descriptors, and the supplement's prose basis never claims more
than the canonical list. Two measured observations remain.

### Finding W068-X16-R5 (token divergence, cross-artifact)

For the three vacuum classes the supplement `axis_registry.genericity_axis.frozen` reads
`residual_comeager`, while canonical `classes[*].axes.genericity_kind` reads
`provisional_baire_residual` and `genericity_value_status` reads
`provisional_owned_by_F1` / `provisional_owned_by_F2`. AF-WCC-SCALAR-SPH matches
(`unresolved`/`unresolved`). This is a *token-level* divergence: any consumer matching exact axis
tokens sees two spellings for one axis on the same classes, and the supplement's word "frozen" is
ahead of the canonical status field ("provisional"). The supplement's own `scalar_note` already
says canonical "records genericity as provisional", so the divergence was known in prose but is not
reconciled in tokens. Related to controller finding CF-21 (genericity axis recorded-open); this
census adds the cross-artifact dimension and adjudicates nothing.

### Finding W068-X16-R3 (undeclared separators, info)

The three AF-WCC-SCALAR-SPH pairs separate additionally on `genericity_kind`
(`provisional_baire_residual` vs `unresolved`), and the two SCC↔SPH pairs additionally on
`regularity_token` (`C2`/`C0` vs `null`). F0 does not list these axes as decisive for those pairs.
Not a defect — the declared axes already separate the descriptors — but a consumer that reads
"decisive_axes" as "all separating axes" would under-count.

## Limitations

- Structural, declaration-level measurement only. The canonical `disjointness_scope` says the table
  separates **class descriptors, not data spaces**; this census does not test data-space overlap
  and does not adjudicate whether a declared decisive axis is physically decisive.
- The supplement basis mapping is token-based via a pre-registered phrase table; phrases not in the
  table are ignored (recorded as EMPTY only if nothing maps).
- Independent but not author-independent of the *instruments*: this is one worker's own extractor,
  with 6 planted controls; no second executor has re-run it.

## Falsifier

Any byte move in a pinned input voids the binding. A reviewer exhibiting a canonical
decisive-axis cell or supplement frozen value that the extractor misreads (false negative), or a
verdict reported for a cell whose anchor text is not on disk (false positive), falsifies that cell.
Pin drift between registration and measurement voids the whole census.

## Non-claims

Not a gate verdict, not a node transition, no `validation_status=passed`, no canonical write.
A1/G-CLASSBIND/G-FORM/G-F0 remain owned by the controller and leads. No claim about the truth of
any class or of cosmic censorship.

## Reproduce

```bash
cd artifacts/worker-068/xscope16
python3 run_xscope16.py --selftest   # planted controls, exit 0
python3 run_xscope16.py              # preflight (fail-closed) -> raw_census.json, controls.json, report.json
```
