# W034 — F1 freeze-candidate derivation (AF-WCC-VAC-GEN / F1 / G-FORM)

Task: take the two independently produced F1 falsifier-corpus repair lineages, derive the
single union candidate that closes every adjudicated residual, and adjudicate the derived
bytes with the same battery that produced `W034-F1-REPAIR-CANDIDATE-ADJUDICATION-01`.

**Verdict: `FREEZE_READY_CANDIDATE_DERIVED`** — proposal bytes on disk, no canonical write.

| | |
|---|---|
| candidate | `candidate/f1_falsifier_tests.rev13.frozen29.derived.jsonl` |
| sha256 | `adf0e2ef780f75d98fc7f78f08d256ea556493994e78585c9083da4143c271f8` |
| bytes / rows | 145121 / 25 |
| object under test | `schemas/f1_falsifier_tests.jsonl` (still the pinned rev29 bytes `56bcb4b3234b`, unchanged by this task) |
| pins (all re-measured, stable to end) | F1 rev13 `d9cebb9404b2`, F0 rev5 `0abb9ed8a961`, FROZEN rev29 `815e08079aef` |
| base lineage | `artifacts/worker-031/f1_suite_repin_dryrun/patched/f1_falsifier_tests.tierB.jsonl` `785e6a4e53d6` |
| excerpt source | `artifacts/worker-077/f1_suite_rebind_dryrun/run/proposed_f1_falsifier_tests.rev13.mechanical.jsonl` `306480f5f45a` |

## Derived write set (76 ledger entries; 158 changed JSON pointers)

- **D1 record fidelity (2 fixes).** Probes whose recorded `observed_excerpt` did not resolve
  to the live rev13 value: `F1-AMB-09` `genericity.ambient_space` and `F1-AMB-21`
  `f0_binding.declared_f0_sha256`. Both faithful values come from the W077 mechanical
  lineage (verified against rev13 before use).
- **D2 row provenance (74 fixes).** Every row: `binding_frozen_revision_schema=13`,
  `binding_frozen_revision=29`, `rebound_at=2026-09-12T01:20:30+08:00` (fixed derivation
  stamp, no future-dating), plus an additive `rebind_note`. Historical fields
  (`binding_at_authoring`, `prior_binding_*`) are never rewritten.

Changed pointers by scope vs the rev29 corpus: `row_binding_or_provenance` 150,
`observation` 4, `cross_artifact_binding` 1, `citation` 1, `probe_expectation` 2.
0 semantic-forbidden changes, 0 out-of-write-set changes.

## Adjudication of the derived bytes

C1–C8 battery imported verbatim from
`artifacts/worker-034/f1_repair_candidate_adjudication/adjudicate_f1_repair_candidates.py`:

| check | status | measured |
|---|---|---|
| C1 load/order 25 rows | PASS | order identical |
| C1b class binding | PASS | all `AF-WCC-VAC-GEN` / `F1` |
| C2 row binding to F1 rev13 | PASS | 25/25 |
| C3 84 probes at rev13 | PASS | 84, 0 fail |
| C6 excerpt fidelity at rev13 | PASS | 0 mismatches |
| C4 probe identity | PASS | 0 path/kind/role changes |
| C4b expectation-change scope | PASS | only the two declared F1-AMB-25 probes |
| C5a P1 anchor = live F0 | PASS | `0abb9ed8a961…` |
| C5b P4 revision-specific anchor | PASS | present in rev13 note, absent at authoring |
| C7 provenance complete | PASS | 0 gaps |
| C8 history preserved | PASS | 0 rewrites |

W029-equivalent materiality checks (the W029 instrument is hard-bound to the canonical path):

| check | status | measured |
|---|---|---|
| B1 all 25 rows rebound to live rev13 | PASS | `binding_frozen_revision_schema=[13]`, one binding, one fresh `rebound_at` |
| B2 suite binding = canonical F1 sha | PASS | `d9cebb9404b2` on both sides |
| X1 cross-artifact declarations resolve to live F0 | PASS | 1/1 |
| M2 84 probes recompute true at rev13 | PASS | 84/84, no pre-existing false rows |
| C9 schema F0 binding = live F0 | PASS | `0abb9ed8a961…` |

Controls: the 8 mutant controls are all caught; 7 negative controls are all caught
(original corpus, base tierB, w077_f0refresh, plus reverted-excerpt, reverted-provenance,
rewritten-history and dropped-row mutants of the derived bytes). The lineage re-adjudication
reproduces the prior verdicts exactly: tierA `C6+C7`, tierB `C6+C7`, w077 mechanical
`C3,C5a,C5b,C7,C8`, w077 f0refresh `C7,C8`. Derivation is byte-deterministic (two
derivations, one digest).

## Owner variants (independent verification, `verification.json`)

- **V1** `rebind_note` omitted on every row → still freeze-ready (minimal-byte publication).
- **V2** `binding_frozen_revision=30` (candidate is part of the FROZEN rev30 issue) → still
  freeze-ready. The owner may also re-stamp `rebound_at` at publication; C7 only requires a
  fresh ISO-parseable value and `binding_frozen_revision >= 29`.

## Non-claims

Worker evidence only: no gate verdict, no node status, no `validation_status`, no canonical
write, no claim retirement. `schemas/f1_falsifier_tests.jsonl` measured `56bcb4b3234b`
before and after this task. This candidate is a proposal for the F1 owner / rev14 fold.

## Falsifier

Any check in `report.json` whose status flips on a re-run over the pinned bytes; any changed
pointer outside the D1/D2 write set; any declared pin whose sha256 differs at use time; or a
derived candidate not byte-identical across two derivations.

## Next falsifier

When the owner applies a corpus to `schemas/f1_falsifier_tests.jsonl`, re-run this battery on
the applied bytes and on FROZEN rev30's per-file pin: the applied sha256 must equal this
candidate (freeze-ready) or be re-adjudicated as a new candidate.

## Reproduction

```bash
python3 artifacts/worker-034/f1_suite_freeze_candidate/derive_f1_freeze_candidate.py   # exit 0 = freeze-ready
python3 artifacts/worker-034/f1_suite_freeze_candidate/verify_f1_freeze_candidate.py   # on-disk + variants
```

`report.json` (machine verdict), `evidence.json` (full check detail, pins, ledger),
`derivation_ledger.json` (per-pointer before/after/source), `checkpoint.json` (worker-local).
