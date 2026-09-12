# W054-F2B-REV29-UNION-LEDGER-01 — F2b rev29 defect union ledger

**Actor:** worker-054 · **Created:** 2026-09-12T01:13:00+08:00
**Class:** AF-SCC-C0-VAC-GEN (node F2b) · **Gate:** G-FORM (advisory input only)
**Target:** `schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe` (rev13) at FROZEN rev29
`artifacts/formulation/FROZEN.json#815e08079aef`

## What this is

One bounded, class-bound, read-only task: take the **union** of the F2b rev29 defect
claims that six independent reviewers reported between 00:35 and 01:10, and decide each
one from **primary bytes** with my own instrument. The output is a materiality-classified
ledger, not a verdict: it issues no gate verdict, sets no node status, and adopts no repair.

It exists because the F2b revises were scattered across reviewer-specific artifacts and
the G-FORM r3 census (`artifacts/worker-074/r3_verdict_independence/report.json#d5b8661f63da`)
counted them (1 non-author accept / 8 revise) without deciding which of them are operative.
The r3 verifier needs that decision to know whether a second accept is even possible at
these bytes.

## Result

| # | claim | carrier | status | materiality |
|---|---|---|---|---|
| 1 | H1 inverted containment premise | `implication_ledger.forbidden_transfers[0].reason` :246 | REPRODUCED | **OPERATIVE_BINDING_TEXT** |
| 2 | H2 containment denial | `regularity.must_not_conflate[0]` :152 | REPRODUCED | **OPERATIVE_BINDING_TEXT** |
| 3 | D3 conclusion-type vocabulary | `conclusion.conclusion_type` | REPRODUCED | RESOLVED_NONBLOCKING (alias registry + AMB-10) |
| 4 | revision-history non-monotone / names no live F0 hash | `revision_history` | REPRODUCED | HYGIENE |
| 5 | stale side pins (`1bb78ce9` vs live `b2ab6acb`) | `schemas/af_scc_c0_vacuum.yaml.sha256`, `entry_hashes.json` | REPRODUCED | HYGIENE |
| 6 | provenance worker hash has no on-disk referent; self-referential `harvested_from` | nested `provenance` block :75 | REPRODUCED | HYGIENE |
| 7 | `f0_binding` names the class-contract supplement without a hash pin | `f0_binding.class_contract_supplement_sha256` | REPRODUCED | HYGIENE |
| 8 | canonical gate cannot certify either operative carrier | `artifacts/formulation/tools/check_class_schema.py#000e09e46b2f` | REPRODUCED | **INSTRUMENT** |

**8/8 claims reproduced. 2 operative, 1 non-blocking, 4 hygiene, 1 instrument. 10/10 controls.**

### The two operative carriers (primary bytes)

- **:152** `regularity.must_not_conflate[0]` — "No containment with C2 or C0 is asserted
  here" — contradicted by the same document at `:239` `extension_class_containment`
  ("E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2") and the four one-way
  entailments derived from it. Required normative slot (rule_spec R06). The F2a sibling
  carries the corrected nesting wording and no denial. Byte-identical to rev12: the rev13
  delta is binding-only.
- **:246** `implication_ledger.forbidden_transfers[0].reason` — "C2 is a strictly larger
  extension class" — inverted against the file's own chain, which makes E_C2 the innermost
  (smallest) admissible-extension set. The row's `from`/`to` and its conclusion are correct;
  the stated premise is false. Required normative slot (rule_spec R16).

### Instrument blind spot (independent of the two carriers)

At `check_class_schema.py#000e09e46b2f`:

| input | gate |
|---|---|
| canonical defective bytes | **pass** |
| H1 fixed | pass |
| H2 fixed | pass |
| both fixed | pass |
| H1 reason replaced by `banana` | **pass** |
| containment chain fully reversed | **pass** |
| `must_not_conflate` emptied | **fail (R01)** |

So the canonical gate is alive on slot presence but cannot certify either carrier's
content. A gate PASS cannot ground an accept of these clauses.

### Candidate repairs (verified, not adopted)

Both available two-edit candidates close both carriers, keep the chain intact, and still
pass the canonical gate:

| candidate | sha256 | closes both | gate |
|---|---|---|---|
| `artifacts/worker-002/.../af_scc_c0_vacuum.repair2edit.yaml` | `84b5d3fa29a6` | yes | pass |
| `artifacts/worker-083/.../candidate/af_scc_c0_vacuum.yaml` | `1315427fbc92` | yes | pass |

Adoption is the formulation owner's call. **Any repair moves the hash and voids every
verdict bound to `b2ab6acb`** (worker-017 N17-R13-04), including this ledger.

## Verdict (worker level)

At `b2ab6acb2bbe` the F2b rev29 defect record resolves to **two operative binding-text
contradictions** plus hygiene debt. A second independent non-author accept at rev29 is
**not justified**; the minimal repair set is the two carrier edits, followed by re-freeze
and one re-review round.

## Reproduction

```bash
python3 artifacts/worker-054/f2b_rev29_union_ledger/checker.py \
        --created-at 2026-09-12T01:13:00+08:00
```

Pure function of the 12 pinned inputs in `PINNED.json` and `--created-at`; mutants are
regenerated under `scratch/`. No author code is imported; the only canonical tool
executed is the gate under test (subprocess, `--json`). Zero canonical writes.

## Falsifier / limits

FALSIFIED if, at the same pins: either operative carrier stops reproducing; the gate
fails the defective bytes or passes an emptied `must_not_conflate`; any of the 10 controls
changes observation; or any declared pin measures differently. VOID on any F2b hash move.

Not tested / not claimed: mathematics, F2a/F1 correctness (siblings are controls only),
rev12 byte comparison (canonical rev12 `55d0a1ea` bytes are absent from this tree, K10
records `not_testable`), and any gate or node transition.
