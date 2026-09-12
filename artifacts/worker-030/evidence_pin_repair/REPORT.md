# W030-EVIDENCE-PIN-REPAIR-01 — the F1/F2a/F2b consistency-evidence pin is restorable, and the tool that erased it is identified

- **Worker:** worker-030 (bounded execution worker; one class-bound task, then exit)
- **Classes / nodes / gate:** `AF-WCC-VAC-GEN` / `AF-SCC-C2-VAC-GEN` / `AF-SCC-C0-VAC-GEN` · F1 / F2a / F2b · G-FORM
- **Verdict:** `REPAIR_KIT_VERIFIED` — 20/20 checks pass, 0 failed (machine checks in `report.json`)
- **Instrument:** `artifacts/worker-030/evidence_pin_repair/run_repair_kit.py`
- **Report:** `artifacts/worker-030/evidence_pin_repair/report.json`
- **Staged repair:** `artifacts/worker-030/evidence_pin_repair/patched_check_taxonomy_consistency.py`
- **Declared-byte snapshot:** `artifacts/worker-030/evidence_pin_repair/declared_pin_snapshot.json`
- **Reproduce:** `python3 artifacts/worker-030/evidence_pin_repair/run_repair_kit.py` (exit 0; exit 2 = a frozen content pin moved)

## The defect

All three rev12 class schemas declare

```
f0_binding.consistency_evidence_sha256 = 675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48
f0_binding.consistency_evidence        = artifacts/formulation/evidence/taxonomy_consistency.json
```

but at measurement time the canonical path carries the 8-field document
`9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b` (495 B), and `FROZEN` rev28
pins that 8-field value. The declared bytes exist only as worker snapshots. This is the
single binding defect that makes independent reviews of F1/F2a/F2b return `revise` at rev12.

## Mechanism (byte-exact, independently reproduced)

1. Running the **unmodified** `artifacts/formulation/tools/check_taxonomy_consistency.py` on the
   frozen F0 pair reproduces `9e335e9b…` exactly: the tool's `out.write_text(json.dumps(rep, …))`
   emits **8 fields** (`map_taxonomy`, `lead_contract`, `consistent`, `errors`,
   `contract_divergences`, `notes`, `classes_compared`, `alias_policy`) and runs unconditionally
   on every invocation.
2. Appending the three binding fields — `map_taxonomy_sha256` = the measured canonical F0 hash
   `0abb9ed8…`, `lead_contract_sha256` = the measured supplement hash `d7419b4e…`,
   `measured_at = 2026-09-12T00:32:02+08:00` — reproduces the declared document
   **byte-for-byte** (`675a99d0…`, 728 B).
3. The schemas' `revised_at` and the three schema mtimes are all `2026-09-12T00:32:02`, so the
   declared `measured_at` is the rebind/freeze instant, and the declared snapshot's recorded
   input hashes **equal the current canonical F0/F0-R hashes** — the declared bytes are
   content-current, not stale.
4. Therefore the overwrite is the defect, not the declaration: any re-run of the canonical tool
   (lead workflows, gate tests, checkpoint cycles) re-erases the three fields and re-breaks the
   binding chain for all three classes.

Measured collision timeline (all hashes re-measured; full list in `report.json`):

| when (+08:00) | observation |
|---|---|
| 00:32:02 | schemas rev12 written; declared evidence `675a99d0` is the current form |
| 00:32:58 | worker-086 pins the declared bytes from the canonical path (`675a99d0`, 728 B) |
| 00:33:16 | worker-043 snapshot measures the overwritten form (`9e335e9b`, 495 B) |
| 00:35:08 | FROZEN rev28 pins the overwritten form `9e335e9b` |
| 00:38:48 / 00:39:29 / 00:42:29 / 00:43:43 | canonical evidence mtime keeps advancing with the same 8-field content |

## Staged repair (owner action; this worker wrote nothing canonical)

1. Install the patched tool at `artifacts/formulation/tools/check_taxonomy_consistency.py`.
   Its check logic is **byte-identical** to the canonical tool (check `N5`); only the output
   section changed: it writes the three binding fields and refuses to rewrite when the inputs
   and the computed check result are unchanged (idempotence guard).
2. Run once:
   `python3 artifacts/formulation/tools/check_taxonomy_consistency.py --measured-at 2026-09-12T00:32:02+08:00`
   → writes `675a99d0…`, restoring the pin all three schemas declare (verified as `R5`: a tree
   seeded with the live 8-field bytes becomes the declared 11-field document in one command).
3. Re-run the same command → `UNCHANGED`, bytes preserved (`R4`).
4. If a future F0/F0-R revision changes the inputs, the guard rewrites with the new input hashes
   and a new `measured_at`; re-pin the schemas in the same revision.
5. Do **not** run the unpatched tool afterwards on the canonical path; it will re-erase the fields.

## Controls (all passed)

- `N1` semantic mutation of the supplement (`censorship: WCC → SCC`) → `INCONSISTENT`, exit 1,
  different hash; `N2` taxonomy mutation (`family: WCC → SCC`) → `INCONSISTENT`.
- `N3` a one-byte corruption of the snapshot no longer hashes to the declared value.
- `N4` with the declared bytes pre-seeded and a mutated input, the guard correctly **rewrites**
  with the new input hash (no stale acceptance).
- `N5` patched check logic byte-identical to canonical.
- `X1` no frozen content pin moved during the run (F0 `0abb9ed8`, F0-R `d7419b4e`, F1
  `cce9c601`, F2a `5476a3f2`, F2b `55d0a1ea`, FROZEN `2f358f67`, canonical tool `de356d99`).

## Falsifiers

- An unpatched run on the pinned F0 pair that produces `675a99d0` byte-for-byte falsifies the
  mechanism proof (`R1`/`R2`).
- A declared snapshot whose recorded F0/F0-R hashes differ from the measured canonical pair makes
  the restore stale and voids `R2`/`R5`.
- A patched run at `--measured-at 2026-09-12T00:32:02+08:00` that does not reproduce `675a99d0`
  falsifies `R3`; a second run that rewrites the file falsifies `R4`.
- A semantic mutation that the patched tool still certifies consistent falsifies `N1`/`N2`.
- Any frozen-content pin moving between instrument entry and exit voids every claim about that
  revision (reported as `canonical_drift`; observed empty).

## Not claimed

No gate verdict, no node status, no `validation_status=passed`; no canonical write (the repair is
staged for the formulation owner); no claim that the F1/F2a/F2b content is correct — this is the
binding chain only; no claim about the other co-rewritten evidence files.
