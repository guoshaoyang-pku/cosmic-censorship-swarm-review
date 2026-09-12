# W047-LFORM01-C2-ORDER-VERIFY-01 — independent verification of L-FORM-01

Worker: `worker-047` (bounded execution slot; no inbound card existed for this slot, task
self-selected from the live queue after reading `HANDOFF.md`, `research_map/ASTRA_HANDOFF.md`,
`comms/PROTOCOL.md`, `comms/inbox` and the pass-04 state).
Class binding: `AF-SCC-C0-VAC-GEN` (primary), `AF-SCC-C2-VAC-GEN` (sibling propagation).
Gate relevance: `G-FORM` / `G-F0` binding hygiene. No gate verdict, node status or
`validation_status=passed` is claimed — worker events cannot set those.

## Question

`astra-lead-formulation` posted blocker `lead-form-20260912T004452-02` (L-FORM-01) at
2026-09-12T00:44:52+08:00: does `schemas/af_scc_c0_vacuum.yaml` at pin `55d0a1ea9bda`
really contain the self-contradiction that the row

- `implication_ledger.forbidden_transfers[0]`: {from: "no proper future C2 extension", to: "this class", reason: "C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker"}

asserts `E_C2` is larger than `E_C0` while the same file's
`implication_ledger.extension_class_containment` (line 238) declares
`E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2`?

## Method (self-contained, deterministic, read-only outside this directory)

Instrument: `check_lform01_c2_order.py` (stdlib only).
Reproduce: `python3 check_lform01_c2_order.py --controls`

1. **Pins.** Measure sha256 of the 8 canonical/mirror inputs. Any mismatch to the frozen pins
   -> exit 2 and no verdict (the run above happened when all pinned bytes were unchanged).
2. **Containment order.** Parse the three independent declarations of the extension-set order
   (C0 schema line 238, F2a schema line 236, F0 class-contract supplement line 145), normalise
   them to a largest-extension-set-first order `O`, and require all three to agree with the
   hand-derived order `["C0","H2loc","C1,1","C2"]`.
3. **Size claims.** Every `"X is a strictly larger|smaller extension class"` claim must agree
   with `O`: `X` is larger than this class iff `index(X) < index(this class)` in `O`.
4. **Strength claims.** Every `X-inextendibility is stronger|weaker than Y-inextendibility`,
   `X-inextendibility is the stronger statement` and `implication runs X => Y only` claim must
   agree with `O` under the rule "a larger extension set makes *no X extension* a stronger
   statement" (`S_X` stronger than `S_Y` iff `index(X) < index(Y)`).
5. **Analogue row present** in the C0 ledger.
6. **Mirror equality** for the three schemas (canonical vs `artifacts/formulation/schemas/`).
7. **Taxonomy relative-size** check on `meaning_C2` (`C^{1,1}` / `H^2_loc` may be called
   "strictly larger classes" only relative to C2).

## Result at the measured pins (all 8 pins matched)

`status=DEFECT`, `hard_defects=1`, 21 checks total (20 PASS / 1 FAIL), exit 0.

| check family | verdict |
|---|---|
| `CONTAINMENT_ORDER` x3 (C0 L238, F2a L236, supplement L145) | PASS — all parse to `[C0, H2loc, C1,1, C2]` |
| `SIZE_CLAIM` (C0 L245) | **FAIL** — claims `larger`, order requires `smaller` |
| `SIZE_CLAIM`/`STRENGTH_CLAIM`/`IMPLICATION_DIRECTION`/`STATEMENT_STRENGTH`/`ENTAILMENT_CHAIN` (C0 L188, L190, L238, L242, L271; F2a L238, L240, L243; supplement L145) | PASS (8 independent claims) |
| `ANALOGUE_ROW_PRESENT` (C0) | PASS |
| `MIRROR_EQUAL` x3 | PASS — mirrors byte-identical |
| `TAXONOMY_RELATIVE_SIZE` (taxonomy L140) | PASS — "strictly larger classes" = C^{1,1}/H^2_loc relative to C2 |

**Verified defect (single, hard).** `schemas/af_scc_c0_vacuum.yaml` line 245:

```
- {from: "no proper future C2 extension", to: "this class", reason: "C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker"}
```

`E_C2` is the **smallest** extension set (`E_C0 ⊇ E_H2loc ⊇ E_{C^1,1} ⊇ E_C2`), so C2 is the
strictly **smaller** extension class relative to C0. The transfer *direction* is correctly
forbidden and the *conclusion* ("C2-inextendibility is strictly weaker") is true; the stated
*reason* is inverted and contradicts the file's own containment (line 238), its own notes
(lines 188: "a C2 result is weaker", line 190: "C0-inextendibility is the stronger statement"),
line 242 and line 271 ("C0 containment runs C0 => C2 only"). The sibling F2a states the analogue
row without this reason (F2a L243: "the converse containment is false; C2-inextendibility is
weaker than H2_loc-inextendibility"), and the F0 supplement L145 and taxonomy L140 both use the
canonical order. Severity: **major — machine-readable ledger self-contradiction / false
justification** (the lead's B/N triage is the owner's call; this report supplies the evidence).
Because `55d0a1ea9bda` is FROZEN rev27/rev28, a repair requires a new revision and re-review of
the F2b slot; this report does not itself void any verdict.

## Controls (8/8 PASS, all in private mutated roots; no canonical path written)

| control | mutation | expected | observed |
|---|---|---|---|
| C1_baseline | none (canonical root, pin check on) | exit 0, exactly 1 `SIZE_CLAIM` FAIL in C0 | exit 0, 1 |
| C2_size_repair | L245 `larger` -> `smaller` (both trees) | exit 4, 0 fails | exit 4, 0 |
| C3_order_reversed | all three containment chains reversed + expected order overridden | C0 L245 becomes consistent; >=1 other C0 claim flips to FAIL | 0 size fails, 4 other fails |
| C4_row_removed | analogue row deleted (both trees) | `ANALOGUE_ROW_PRESENT` FAIL | 1 fail |
| C5_f2a_inversion | same inverted wording injected into F2a (both trees) | F2a claim FAIL | 1 fail |
| C6_drift | one byte appended, pins unchanged | exit 2, no verdict | exit 2 |
| C7_repaired | repair only | exit 4 clean | exit 4, 0 |
| C8_paraphrase_ok | correct paraphrase that avoids the flagged phrase | exit 4 clean (no false positive) | exit 4, 0 |

C3 shows the check is order-sensitive rather than keyword-sensitive; C8 shows it does not flag
a correct rephrasing that drops the disputed phrase.

## Falsifiers / what would overturn this

1. Re-measure: any of the 8 pins differs from `snapshot/SHA256SUMS` -> the run is void (moving
   target), re-pin and re-run.
2. If the C0 containment declaration at line 238 or the supplement L145 is shown to mean the
   reverse order (C2's extension set larger than C0's), the finding is falsified. It is not:
   both parse to `[C0, H2loc, C1,1, C2]` and agree with the taxonomy.
3. If `forbidden_transfers[0].reason` is shown to be a non-semantic editorial label, the hard
   severity is falsified (the self-contradiction remains).
4. If the instrument, re-run on the same bytes, yields a different verdict, or any of the eight
   controls fails, the instrument is invalid.

## Limits / non-claims

- This is a focused single-row verification, **not** a full-schema F2b verdict and not an
  independent G-FORM acceptance; `counts_as_full_schema_verdict=false` and it must not be
  counted toward the two-accept coverage.
- Findings are limited to the extension-set ordering axis; no claim about the physics, the
  C0/C2 separation, or any other field of the schemas.
- No canonical artifact was edited. The FROZEN revision is the owner's to repair.
- Worker events cannot set `status=done`, `validation_status=passed`, or a gate verdict.

## Files

- `check_lform01_c2_order.py` — instrument (re-runnable; exit 0 defect verified / 4 clean /
  2 drift / 3 control failure / 5 unparsed).
- `report.json`, `raw/run_stdout.txt` — full machine-readable result, all checks and controls.
- `snapshot/` — frozen copies of the 8 pinned inputs + `SHA256SUMS`.
- `controls/` — private control roots with `control_results.json`.
- `MANIFEST.json`, `checkpoint.json` — hashes and checkpoint record.
