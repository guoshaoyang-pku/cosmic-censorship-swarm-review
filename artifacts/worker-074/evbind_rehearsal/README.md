# W074-F2A-EVBIND-REHEARSAL-01 — sandboxed rehearsal of the consistency-evidence pin repair

**Worker:** worker-074 (bounded execution worker)
**Class binding:** `AF-SCC-C2-VAC-GEN` (F2a), node `F2a`, gate `G-FORM`
**Scope note:** F1 (`AF-WCC-VAC-GEN`) and F2b (`AF-SCC-C0-VAC-GEN`) declare the *same*
`f0_binding.consistency_evidence_sha256` and were measured for scope only; no verdict is
claimed for them. No mathematical-semantics claim is made.
**Authority:** measurement and rehearsal only. **No canonical repo file was written**
(enforced by check `S9-canonical-untouched`); every write is under
`artifacts/worker-074/evbind_rehearsal/`. No node status, `validation_status`, review
verdict, or gate verdict is set.

## The question

All three G-FORM schemas declare:

```
f0_binding.consistency_evidence          = artifacts/formulation/evidence/taxonomy_consistency.json
f0_binding.consistency_evidence_sha256   = 675a99d0d25b2b37…   (728 bytes)
```

but that path carries `9e335e9ba1bfcf77…` (495 bytes), the 8-field form produced by the
canonical checker's unconditional rewrite (`artifacts/formulation/tools/check_taxonomy_consistency.py:80`).
Reviewers filed this as a blocking hard failure (HF-022-R1, HF-W063-01, B-17R12-02,
W-034-F2B-R1). worker-030 staged a repair kit claiming the declared bytes are byte-exactly
reproducible and restorable. This audit does not take that claim on trust.

## What was measured (all 18 checks PASS)

| id | check | result |
|---|---|---|
| S0 | evidence at canonical path is the 495-byte live form | `9e335e9b…`, FROZEN rev28 pins it at 495 bytes |
| S0 | all three schemas declare the same 728-byte pin | `675a99d0…`, declared ≠ measured |
| S0 | FROZEN rev28 baseline | 44 pins, 0 mismatches |
| S1 | bytes-728 carriers of `675a99d0` | 14 carriers found (15 687 files searched); **none at the canonical path** |
| C1a | surgical append of the three binding fields to the live bytes | `675a99d0…` **byte-identical** to a preserved carrier |
| C1b | tool-style re-serialisation (`json.dumps(..., indent=2)` + appended fields) | `675a99d0…` |
| C1c | 5 negative controls (indent=1, `consistent:false`, wrong F0 pin, missing pin, `measured_at` +1 s) | none reaches `675a99d0` |
| R1 | canonical checker run **in sandbox** | rewrites the path to `9e335e9b…` — the eraser is reproduced |
| R2 | restore declared bytes + patched checker (`--measured-at 2026-09-12T00:32:02+08:00`) | prints `UNCHANGED`, preserves `675a99d0…` |
| R2b | second patched-checker run | idempotent, `675a99d0…` preserved |
| R2c | declared pin would resolve at the path after the restore | yes |
| R3 | **FROZEN rev28 cascade after the restore** | exactly **1 new pin mismatch**: the evidence path (`9e335e9b…` pinned vs `675a99d0…` measured) |
| R4 | patched checker on live bytes **without** `--measured-at` | writes a *new* hash (`283c2249…`) — the restore must pin the historical `measured_at` |
| R5 | counterfactual: re-pin the schemas to `9e335e9b` instead of restoring bytes | F2a schema leaves `5476a3f2…` → FROZEN schema-pin mismatch; every review bind at the frozen hash is voided |

## Finding `W074-EVBIND-F1`

The declared pin is real, content-current and byte-exactly restorable; worker-030's
mechanism claim **replicates independently**. But the repair is **not a one-file action**:
restoring the declared bytes at the canonical path converts the schema-side binding
failure into a FROZEN rev28 pin mismatch, because rev28 froze the *overwritten* 495-byte
form of that same path. The minimal correct owner sequence is:

1. restore the 728-byte document `675a99d0…` at
   `artifacts/formulation/evidence/taxonomy_consistency.json` (or run the patched checker
   with `--out <that path> --measured-at 2026-09-12T00:32:02+08:00` over the live core);
2. bump `artifacts/formulation/FROZEN.json` to a new revision that re-pins that path at
   `675a99d0…`;
3. emit the artifact event carrying the new FROZEN hash.

Then F1/F2a/F2b declared binds resolve simultaneously, with zero semantic change
(`consistent: true`, same four classes, 0 errors, 0 contract divergences).

**Do not** re-pin the schemas to the live form instead (R5): it moves the frozen G-FORM
artifacts off `cce9c601…/5476a3f2…/55d0a1ea…` and voids every review verdict bound to them.

## Reproduce / falsify

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-074/evbind_rehearsal/audit_evbind_rehearsal.py   # exit 0 iff all 18 checks pass
```

**Falsifier** (also in `report.json`): the finding is void if (a) the 728-byte carrier no
longer hashes to `675a99d0…`; (b) the canonical path already carries `675a99d0…` or FROZEN
already pins it; (c) FROZEN revision ≠ 28 or its pin for the evidence path is not
`9e335e9b…`; (d) the patched checker on the restored bytes with the historical
`--measured-at` does not print `UNCHANGED` or does not preserve the bytes; (e) a re-run on
the same pinned inputs yields any check FAIL or a different carrier set; or (f) any schema
already declares a pin other than `675a99d0…`.

## Files

- `audit_evbind_rehearsal.py` — the independent instrument (stdlib + PyYAML only)
- `report.json` — measured snapshot, declared bindings, all checks, falsifier
- `raw/run_log.txt`, `raw/sandbox_evidence_restored.json`,
  `raw/reconstruction_negative_controls.json` — raw outputs
- `sandbox/` — disposable sandbox replica (mirrors the pinned inputs; canonical repo untouched)
