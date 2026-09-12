# W077-F1-ANCHORBIND-01 — F1 anchor-binding census (AF-WCC-VAC-GEN)

Worker: `worker-077` (lifecycle `worker-077-20260912T005105-968807`).
Node `F1`, gate `G-FORM`, class `AF-WCC-VAC-GEN`. Read-only; no canonical path written.
Deliverable is worker-level, `validation_status=unverified`, and is **not** a gate verdict.

## Why this task

Live critical-path blocker `lit-l7-20260912-007` (BL-11) records that the F1 schema's
weighted-Sobolev threshold (`s > 5/2`, `delta in (1/2,1)`), positive-mass and
future-asymptotic-predictability items have no primary-source anchors, and asks:
*"state which schema field each anchor binds, so the anchor is falsifiable per field."*
No worker had produced a per-field anchor census at the rev29 bytes. This run does that and
independently reproduces the blocker's zero-hit measurements.

## Pins (measured before and after the run; no drift inside the run)

| input | sha256 |
|---|---|
| `schemas/af_wcc_vacuum.yaml` (rev29/rev13) | `d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d` |
| `artifacts/formulation/FROZEN.json` (rev29, frozen_at 00:57:26) | `815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0` |
| `ledger/theorems.jsonl` | `a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28` |
| `ledger/citation_audit.csv` | `315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9` |
| `schemas/f1_falsifier_tests.jsonl` | `56bcb4b3234bc86c324bec6e38f142c5ef39517f20d823b6a333f578b7d0851e` |
| `research_map/formulation_taxonomy.yaml` | `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3` |

The FROZEN manifest is a moving input (re-frozen during the observation window,
`3d9e3d77` → `815e0807`, both revision 29). The F1 **content** pin `d9cebb9404b2` was stable.
Bind verdicts to the content hash + FROZEN revision, not to manifest bytes.

## Result

**Verdict: `revise`, score 2.5, `counts_as_full_schema_verdict=false`.**
Checks 8 PASS / 2 FAIL; controls 7/7 PASS; zero drift; content-deterministic across two runs.

| # | check | result |
|---|---|---|
| C1 | live F1 == FROZEN rev29 pin | PASS |
| C1b | single frozen class id | PASS (`AF-WCC-VAC-GEN`) |
| C2 | provenance anchor rows declared | PASS — 5/5 `identifier=null`, 5/5 unresolved |
| C3 | `needed_for` field bindings resolve | PASS — 6 literal + 1 unique recovery (`quantifiers D2` → `quantifiers.domains.D2`) |
| C4 | anchor concepts locatable in F1 text | PASS |
| C5 | BL-11 zero-hit reproduction + positive control | PASS |
| C6 | SRC-096/097 registered but unbound | PASS |
| C7 | candidate anchor source exists per concept | **FAIL** — `A-WSOBOLEV` 0, `A-POSMASS` 0 |
| C8 | falsifier suite binds the live F1 hash | **FAIL** — 0/25 (all bind `cce9c60146d6`) |
| C10 | no input drift | PASS |

### Findings

- **W077-AB-01 (major, hard) — unanchored schema obligation.** F1 declares 5 provenance
  anchor concepts; all 5 carry `identifier: null` and `status: unresolved` while their
  `needed_for` fields are load-bearing (`data_class`, `regularity`, `data_class.adm_mass`,
  `conclusion.equivalent_standard_formulation`, `quantifiers.domains.D2`).
  Reproduces BL-11 from the rev29 bytes.
  *Falsifier:* any anchor row at the live hash with a non-null, resolved identifier.
- **W077-AB-02 (major, hard) — no registered L1 anchor for the four BL-11 items.**
  At ledger `a1674f09` / citation audit `315c1914`, `s>5/2`, `delta in (1/2,1)`,
  `positive mass`, `predictability` each have **0** hits, while positive control
  `cauchy horizon` has 61/58 hits (scanner live). `A-WSOBOLEV` and `A-POSMASS` also have
  **0** candidate sources in the pinned citation audit, so these anchors cannot be satisfied
  from the frozen corpus without new sources or withdrawal of the dependent fields.
  *Falsifier:* any lexical variant of a BL-11 item in the pinned ledger/citation audit.
- **W077-AB-03 (minor) — stale falsifier-suite binding.** `schemas/f1_falsifier_tests.jsonl`
  (25 rows) binds `cce9c60146d6…` (rev28) on 25/25 rows; 0 rows bind the live rev29 hash.
  Not citable as current-revision falsifier-exercise evidence until re-bound by its owner.
  *Falsifier:* a suite row binding the live F1 hash.
- **W077-AB-04 (minor) — imprecise field-binding token.** `needed_for: "regularity, quantifiers D2"`
  is not itself a resolvable YAML path; unique recovery is `quantifiers.domains.D2`
  ("one-ended asymptotically flat vacuum initial data satisfying both constraint equations in
  the declared regularity class"). The obligation is well-defined after a one-token path repair.

### Per-field anchor table (the BL-11 deliverable)

| anchor concept | declared `needed_for` | resolved field path | L1 ledger hits | L1 citation hits | registered candidates |
|---|---|---|---|---|---|
| weighted Sobolev classes | `data_class, regularity` | `data_class.regularity_class.sobolev_variant.{s,delta,spaces}`, `regularity.data_regularity` | 0 | 0 | none |
| MGHD existence/uniqueness | `regularity, quantifiers D2` | `quantifiers.domains.D2` (recovered) | 28 | 8 | SRC-026, 047, 050, 057, 069, 071 |
| positive mass theorem | `data_class.adm_mass` | `data_class.adm_mass.sign` | 0 | 0 | none |
| future asymptotic predictability | `conclusion.equivalent_standard_formulation` | `conclusion.equivalent_standard_formulation.predicate` | 0 | 3 | SRC-096, SRC-097 (both unbound, no L0 entry) |
| WCC known status | prose sentinel ("no status claim made") | — | 2 | 2 | SRC-001 |

The `Cauchy horizon` universal named by the literature lead is **recorded as open, not
adjudicated** here (61 ledger / 58 citation hits, no row adjudicating the universal; this is a
formulation-scope question).

## Controls

K1 token injection (positive), K2 token absence (negative), K3 field resolution (positive),
K4 fabricated field path (fail-closed), K5 duplicate YAML key rejected, K5b canonical bytes
parse strictly, K6 pin-mutation sensitivity. All 7 pass.

## Determinism

Two runs at fixed content pins produce identical reports apart from `created_at` and the
`mtime_ns` of `artifacts/formulation/evidence/taxonomy_consistency.json`, which is
unconditionally rewritten with identical bytes by its producer (sha256 stable at `9e335e9b`).
Content digest excluding the moving FROZEN manifest is equal across runs
(`04cd88e8d741d7d8…`). See `determinism.json`.

## Re-run

```bash
python3 artifacts/worker-077/f1_anchor_bind/check_f1_anchor_bind.py --out report.json
# exit 0 = instrument ok + pins stable; 2 = control failure; 3 = pin/drift failure
```

## Non-claims

Not a gate verdict; sets no node status and no `validation_status=passed`; edits no canonical
artifact; asserts no mathematics or physics; candidate source lists are lexical matches, not
endorsed anchors; the census binds only the pins above and is void on any drift of them.
