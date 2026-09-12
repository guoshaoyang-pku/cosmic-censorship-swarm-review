# W030B-REPRO-EPR-01 — independent fresh-process reproduction of the F1/F2a/F2b evidence-pin repair mechanism

- **Worker:** worker-030 (bounded execution worker; one class-bound task, then exit)
- **Classes / nodes / gate:** `AF-WCC-VAC-GEN` / `AF-SCC-C2-VAC-GEN` / `AF-SCC-C0-VAC-GEN` · F1 / F2a / F2b · G-FORM
- **Verdict:** `REPRODUCED_INDEPENDENTLY` — 20/20 checks pass, 0 failed (`report.json`)
- **Instrument:** `artifacts/worker-030/repro_epr/repro_epr.py`
- **Report:** `artifacts/worker-030/repro_epr/report.json`
- **Reproduce:** `python3 artifacts/worker-030/repro_epr/repro_epr.py` (exit 0 = reproduced; exit 1 = a check failed; exit 2 = a tool pin moved)
- **Nature:** re-instrumentation, NOT a second review verdict and NOT a re-run of the prior kit
  (`artifacts/worker-030/evidence_pin_repair/run_repair_kit.py` is neither imported nor invoked).

## What this tested

The prior task `W030-EVIDENCE-PIN-REPAIR-01` claimed that the rev12 class schemas' declared
`f0_binding.consistency_evidence_sha256 = 675a99d0…` is byte-exactly recoverable as
"unpatched tool output (8 fields) + three binding fields", and that the staged patched tool
restores it. This instrument rebuilds that mechanism from scratch, in its own sandboxes, and
adds one control the prior kit did not run.

At measured pins (all re-measured at instrument entry and exit):

| object | sha256 |
|---|---|
| F0 canonical (`research_map/formulation_taxonomy.yaml`) | `0abb9ed8a961` |
| F0 supplement (`artifacts/formulation/formulation_taxonomy.yaml`) | `d7419b4e8963` |
| F1 / F2a / F2b | `cce9c60146d6` / `5476a3f2c6bc` / `55d0a1ea9bda` |
| live evidence path (8 fields, binding keys absent) | `9e335e9ba1bf` |
| declared evidence bytes (11 fields) | `675a99d0d25b` |
| canonical tool (unpatched) | `de356d999ea3` |
| staged patched tool | `83ab54519d45` |
| FROZEN | rev28 `2f358f6722d9` |

## Checks (all machine-run, details in `report.json`)

1. **A** — the unpatched canonical tool on a byte-copy of the live F0 pair emits output that is
   **byte-identical to the live canonical evidence** `9e335e9b` (8 fields, exit 0).
2. **B** — that 8-field document plus `map_taxonomy_sha256`, `lead_contract_sha256`,
   `measured_at = 2026-09-12T00:32:02+08:00`, appended in that order and dumped with the tool's
   own `json.dumps(rep, indent=2)+"\n"`, is **byte-identical to the declared snapshot**
   `675a99d0` (`artifacts/worker-030/evidence_pin_repair/declared_pin_snapshot.json`).
3. **C (new control)** — a sandbox pre-seeded with the **declared** `675a99d0` bytes, on which
   the unpatched tool is then run, ends at `9e335e9b`: the erasure is reproduced *from the
   declared state*, so the defect is the unconditional rewrite, not a stale declaration.
4. **D** — the staged patched tool, run on the live 8-field state with
   `--measured-at 2026-09-12T00:32:02+08:00`, writes `675a99d0` byte-for-byte (`WROTE`), and a
   second identical run prints `UNCHANGED` and preserves the bytes (idempotent guard).
5. **E** — the patched tool on a sandbox whose F0 copy has `AF-WCC-VAC-GEN` family mutated
   `WCC → SCC` exits 1 with `INCONSISTENT`, `consistent=false`, error
   `AF-WCC-VAC-GEN: family SCC vs WCC`, and rewrites to a different hash (`9661890b…`): no
   stale acceptance.
6. **F** — check-logic lines 1–78 of the canonical and patched tools are **line-identical**;
   only the output/write section differs.
7. **G** — all three schemas declare `675a99d0`; their mtimes equal the declared `measured_at`
   `2026-09-12T00:32:02+08:00`; the live path mismatches all three declarations.
8. **H** — no canonical pin moved between instrument entry and exit (`canonical_drift = {}`).

## Note / correction

The prior kit's `REPORT.md` line 37 states the schemas' `revised_at` and mtimes are all
`2026-09-12T00:32:02`. Measured: `revised_at` and `f0_binding.checked_at` are
`2026-09-12T00:31:41+08:00` for all three; only the file **mtime** is `00:32:02` and equals the
declared `measured_at`. The byte-level mechanism (B/D) is unaffected; the supporting sentence
is corrected here (full data in `report.json` → `notes`).

## Falsifiers

- An unpatched run on the pinned F0 pair that emits `675a99d0` falsifies A/B.
- A declared snapshot not byte-equal to `live_doc + 3 binding fields` falsifies B.
- An unpatched run seeded with the declared bytes that leaves them intact falsifies C.
- A patched run at the pinned `--measured-at` that fails to reproduce `675a99d0`, or a rerun
  that rewrites, falsifies D.
- A patched run on the mutated taxonomy that exits 0, or that leaves the declared bytes when
  the check result changed, falsifies E.
- Any entry-pin movement during the run voids the affected row (H; observed empty).

## Not claimed

No gate verdict, no node status, no `validation_status=passed`; **no canonical write** (all
tool runs are under `artifacts/worker-030/repro_epr/sandbox/`); no claim that F1/F2a/F2b
content is correct; same worker slot as the kit under test, so this is a reproduction, not an
independent second reviewer verdict. The live evidence path still carries `9e335e9b` at exit —
the repair remains staged for the formulation owner (`astra-life05-evidence-binding-repair`).
