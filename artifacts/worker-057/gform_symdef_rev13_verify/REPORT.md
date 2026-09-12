# W057-GFORM-SYMDEF-REV13-VERIFY-01 — report (worker-057)

**Task (self-selected; no card in `comms/inbox/worker-057.jsonl`).**
Class-bound: `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`; nodes F1/F2a/F2b; gate G-FORM.
One bounded worker task: re-test the rev-11/12 normative-symbol findings at the **rev-13**
schema bytes with an independently written instrument plus a sealed re-run of the original checker.

## Inputs (sealed; all four hashes matched at run and at emit)

| file | sha256 | rev | bytes |
|---|---|---|---|
| `schemas/af_wcc_vacuum.yaml` | `d9cebb9404b2e79e…c5d3d` | 13 | 37662 |
| `schemas/af_scc_c2_vacuum.yaml` | `e9a27996dfd308bd…d82fe` | 13 | 30594 |
| `schemas/af_scc_c0_vacuum.yaml` | `b2ab6acb2bbe7f86…4501c` | 13 | 35602 |
| `research_map/formulation_taxonomy.yaml` (frozen) | `0abb9ed8a96135c9…094e3` | rev5/F0 | 36372 |

## Verdict: `VERIFIED_REV13_WITH_BASELINE_CORRECTION`

All five pre-registered controls pass (C1 defined symbol resolves, C2 binder resolves,
C3 absent symbol unresolved, C4 byte-tamper caught by the pin, C5 refutation-branch fires).
The independent instrument reproduces **five of the six** baseline major findings exactly and
refuses to reproduce one, with a named reason.

| # | node | finding | status at rev 13 | evidence |
|---|---|---|---|---|
| 1 | F1 | `P_WCC(D)` used in `quantifiers.negation_normal_form`; no definition site in the file, no occurrence anywhere in the frozen taxonomy | **confirmed** | independent probe: `nowhere` |
| 2 | F2a | `MGHD(D)` used in `conclusion.statement_formal` and `quantifiers.negation_normal_form`; no definition site; taxonomy mention only (expansion prose, 11 occurrences, no `definition_ref`) | **confirmed** | independent probe: `mentioned_not_defined` |
| 3 | F2b | same as #2 for the C0 class | **confirmed** | independent probe: `mentioned_not_defined` |
| 4 | F2a | `proper_future_extension_in_class` is defined on the extension tuple `(M',g',iota)` of `(M,g)` but applied to `MGHD(D)`; the negated extension existential is implicit at the use site | **confirmed** (persists) | independent probe: `predicate_argument_role` |
| 5 | F2b | same as #4 for the C0 class | **confirmed** (persists) | independent probe: `predicate_argument_role` |
| 6 | F1 | baseline flags `AF_{I+}` as having no definition site | **not reproduced** | the rev-13 file carries `i_plus.predicate_abbreviation`, a definitional leaf that names and expands the symbol (added in the rev-12 repair); the sealed baseline checker does not treat that leaf as a definition site |

## What this corrects

The baseline checker (rev-11/12 rule) reports six major findings at rev 13. This instrument
reproduces five and **downgrades one**: `AF_{I+}`. The rev-13 F1 schema added

```
i_plus.predicate_abbreviation: "AF_{I+}(M) abbreviates the existence predicate of
i_plus.definition: M admits a conformal completion … [rev12: … the symbol was previously
undefined; grep AF_{I+} matched conclusion.statement_formal only]"
```

so the rev-11/12 finding is repaired in substance at the new bytes, but the baseline checker
still reports it because its definition-site rule does not recognise `predicate_abbreviation`.
This is a baseline false positive, not a new schema defect, and it should not be cited as a
standing G-FORM failure at rev 13.

## The uniformity problem (unchanged, now measured at rev 13)

The same situation that worker-057 raised in the rev-11/12 blockers still stands, one revision
later:

- F1's `AF_{I+}` was repaired by adding a **file-local definitional leaf**.
- F2a/F2b's `MGHD` remains **taxonomy prose only** — no file-local definition, no
  `definition_ref`.
- F1's `P_WCC` remains with **no definition site at all** — not in the file, not in the taxonomy.

So at these hashes the three class schemas are governed by three different implicit policies:
file-local definition (F1 `AF_{I+}`), taxonomy-prose-sufficient (F2 `MGHD`), and no definition
(F1 `P_WCC`). Either `P_WCC` and `MGHD` carry the same defect class as the pre-repair `AF_{I+}`,
or a prose-sufficient policy must be recorded — and then the baseline's `AF_{I+}` finding (and
the strict rule behind it) needs re-adjudication. The two readings cannot both stand.

## Method / independence

- `verify_symbol_defs_rev13.py` does not import or call the baseline checker. It walks the YAML
  structurally, classifies every scalar by its path (a scalar is definitional only when its leaf
  or a sibling key names a definition), and looks symbols up in a name-keyed map — a different
  decision procedure from the baseline's statement-regex + fixed-site table.
- `baseline_checker_sealed.py` is a byte-copy of the rev-12 checker with only the output
  filename changed (`report.json` → `baseline_report.json`), so the baseline verdict is
  reproduced from the same code that produced it, not retyped.
- The verdict rule is pre-registered: exact set equality of the major-finding sets ⇒ `VERIFIED_REV13`;
  a strict subset with all controls passing ⇒ `VERIFIED_REV13_WITH_BASELINE_CORRECTION`;
  no independent findings ⇒ `REPAIRED`; anything else ⇒ `DIVERGENT`.

## Authority

Worker evidence only. This report sets **no** gate verdict, **no** node status, and **no**
`validation_status=passed`; it does not edit any schema or the taxonomy, and it does not
release `numerics_lock`. Adjudication belongs to the G-FORM reviewers and the controller.

## Falsifier

Re-hash the four pinned inputs and re-run `verify_symbol_defs_rev13.py`: the report is falsified
for the recorded sha256 values if any measured input hash differs, if any control C1–C5 flips to
false, if the independent major-finding set stops equalling the sealed baseline set, or if a
definition site for `P_WCC` or `MGHD` appears outside the normative sites (which flips the
verdict to `REPAIRED`). A moved schema or taxonomy hash voids this report for the new bytes.
