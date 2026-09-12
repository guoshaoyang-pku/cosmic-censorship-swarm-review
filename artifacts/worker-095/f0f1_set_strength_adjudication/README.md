# worker-095 — F0/F1 SET-strength adjudication (ESC-2)

One bounded, class-bound, read-only task taken from live state because `comms/inbox/worker-095.jsonl`
does not exist (fleet 2026-09-12T01:20+08:00). Node **F1**, class **AF-WCC-VAC-GEN**, gate
**G-FORM**.

Subject: the open blocker `audit-l09-b3-f1-crossart-20260912T011904` (item 1), escalated as
**ESC-2** — F0 canonical rev5 and F1 rev13 appear to give opposite strength directions for the
set-based (SET) visibility reading.

Result: **no substantive conflict.** The two labels are true of the objects they name — F0's
"strictly stronger" is class/conclusion-level, F1's "strictly WEAKER" is predicate-level — and the
variant's own delta artifact already states both levels. Minimal remedy is a level tag in the
REC-36-authorized F1 rev14; no F0 write, no G-F0 reopening, no strength claim falsified.
Details, exact quotes and the machine-checked lemmas: `ADJUDICATION.md`.

| file | what |
|---|---|
| `strength_probe.py` | deterministic stdlib instrument (pins, extracts, exhaustive/random preorder checks, ω-chain, level adjudication, controls) |
| `report.json` | full machine-readable run output + core digest |
| `ADJUDICATION.md` | dossier: claims, lemmas, ESC-2 decision table, ruling, falsifier |
| `verdict.json` | worker verdict on F1 at the pinned hash (not a content accept) |
| `evidence/raw/` | raw evidence: pins, extracts, finite_exhaustive, random_models, omega_chain, level_adjudication, controls |
| `MANIFEST.json` | sha256 of every file in this directory |

Reproduce (exit 0 = PASS): `python3 strength_probe.py`

Boundaries: read-only on every canonical path; writes only under
`artifacts/worker-095/f0f1_set_strength_adjudication/` and `runtime/state/`; does not set node
status, `validation_status=passed`, or a gate verdict.
