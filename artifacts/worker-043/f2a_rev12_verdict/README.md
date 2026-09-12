# W043C-F2A-REV12-VERDICT-01 — independent F2a verdict at FROZEN rev28

Bounded class-bound task, worker slot 043. No inbox card existed for `worker-043`; the task was
taken from the live critical path.

## Why this task

`reviews/G-FORM-final-verify.json` (astra-lead-audit, measured 2026-09-12T00:33:38+08:00) records
blocking item **B-GFORM-1**: no class reaches two independent full-schema verdicts at the rev27/rev28
frozen hash. F2a had **zero**. This is one independent full-schema verdict for F2a
(`AF-SCC-C2-VAC-GEN`), the class this slot verified at the superseded rev10 hash in W043.

## Reviewed bytes (frozen)

| artifact | sha256 | bytes |
|---|---|---|
| `schemas/af_scc_c2_vacuum.yaml` (F2a, rev12) | `5476a3f2c6bc7196…` | 29976 |
| `artifacts/formulation/FROZEN.json` (rev **28**, frozen_at 00:35:08) | `2f358f6722d92062…` | 21973 |
| `artifacts/formulation/evidence/taxonomy_consistency.json` | `9e335e9ba1bfcf77…` | 495 |

Canonical == authoring mirror == FROZEN rev28 pin for F2a. A byte snapshot with mtimes is in
`snapshot/` (`SNAPSHOT_MANIFEST.json`).

## Verdict: **revise**, score 3.0 (advisory)

- **14/14 content checks PASS**: identity/binding, strict YAML hygiene (0 duplicate keys), freeze pin
  and mirror, clock discipline (no future-dated `revised_at`), quantifier chain
  (`forall r in D0` / comeager `G_r` / `forall` data / `not_exists` extension) with all four domains
  typed and resolving, SCC conclusion with visibility excluded and the WCC falsifier forbidden,
  C2 classical-Ric extension predicate with clauses (a)–(f), regularity/composite-token ban, ledger
  direction (`C0 ⇒ C2` licensed, converse forbidden, no inverted size premise), decidable two-tier
  falsifier, no conclusion inflation, pointers resolve, declared `check_class_schema.py` PASS.
- **HF-043-1 (blocking, binding)**: `f0_binding.consistency_evidence_sha256` is
  `675a99d0d25b2b37…`, but the named evidence file measures `9e335e9ba1bfcf77…` and is pinned at
  that hash by FROZEN rev28. No file on disk hashes to `675a99d0` (0 hits). The same stale value is
  embedded in F1 and F2b.
- **HF-043-2 (major, evidence regression)**: the frozen consistency evidence is hashless (no
  `map_taxonomy_sha256` / `lead_contract_sha256`), regressing the rev27 closure item (e)
  (`F1-review-090 F090-05` / `F1-review-19 F-4`) that `close_findings_rev27.py:379-380` had
  discharged.
- **O-GFORM-1 adjudicated non-blocking**: F2a/F2b `data_class` key-identity is intended encoding —
  the token selects the extension class, not the data; five separation carriers track the C2 token.
- **O-043-1 cross-reference**: the F2 index `schemas/af_scc_regularities.yaml` (`94562101a816`)
  pins superseded components and keeps duplicate `revised_at` keys — owned by the F2 index, already
  blocked by worker-005 (00:34:22); not counted against F2a.

### Ordering constraint (P-043-1)

The embedded hash can only be corrected **after** the evidence file is regenerated, because the
correct value is the hash of the *repaired* evidence (`0058692bf244…` in the counterfactual), not
the current `9e335e9b…`. Then re-freeze.

## Pre-registered acceptance test

`raw/counterfactual_repair.py` applies the two declared repairs plus the required re-freeze to a
scratch copy (read-only on the shared tree) and re-runs the checker:

```json
{"verdict": "accept", "score": 4.0, "n_fail": 0, "R15": "PASS", "R16": "PASS", "acceptance": "PASS"}
```

## Reproduce

```bash
python3 artifacts/worker-043/f2a_rev12_verdict/check_f2a_rev12.py --root . --selftest \
  --json artifacts/worker-043/f2a_rev12_verdict/raw/check_selftest.json
python3 artifacts/worker-043/f2a_rev12_verdict/raw/counterfactual_repair.py .
```

Exit codes: 0 accept, 2 revise, 3 input drift (report VOID), 4 control battery failed.
Controls: 7 mutants (wrong conclusion family, C0 regularity, containment inversion,
duplicate+future `revised_at`, unresolvable pointer, hashless evidence, stale embedded hash) all
detected; the pristine review produces exactly the two declared FAILs (no false positives).

## Authority and falsifier

Worker verdict is evidence only: it cannot set `status=done`, `validation_status=passed`, or any
gate verdict (`comms/PROTOCOL.md` rule 2). `counts_as_full_schema_verdict=true` asserts only that
this is a full-schema independent verdict for coverage counting.

**Falsifier**: any byte change of the reviewed files after the snapshot voids the review.
HF-043-1 is falsified by a file at the named path hashing to `675a99d0…`; HF-043-2 by
`map_taxonomy_sha256`/`lead_contract_sha256` being present and correct in the frozen evidence.
An accept for F2a at this hash requires both repairs plus a re-freeze.
