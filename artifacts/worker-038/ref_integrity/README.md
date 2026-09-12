# W038-GFORM-REFINT-01 — embedded-reference integrity of the FROZEN rev28 closure

Bounded class-bound task, worker slot 038. No inbox card existed for `worker-038`
(`comms/inbox/worker-038.jsonl` absent); the task was taken from the live G-FORM critical path
(`reviews/G-FORM-final-verify.json`, `astra-life04-verify-gform-r2`): no class reaches two
independent accepts at the FROZEN rev28 pins, and every blocker named in the fleet is a *binding*
defect rather than a schema-content defect.

- node_ids: `F0`, `F1`, `F2a`, `F2b`
- class_ids: `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`
- gate: `G-FORM` (evidence; no gate verdict claimed)

## What was missing

`artifacts/formulation/tools/verify_frozen.py` re-hashes the files listed in `FROZEN.json`. It
cannot see a hash *embedded inside* a pinned file that points at different bytes than the pinned
path now carries. The fleet found one such defect by hand (`consistency_evidence_sha256` in the
three schemas); nobody had scanned the whole frozen closure for the class.

## Task

For every file in `FROZEN.json` rev28 (`2f358f6722d92062…`, 44 pins) plus the manifest itself and
the two downstream schema pin files (`schemas/taxonomy_cases.jsonl`,
`schemas/f1_falsifier_tests.jsonl`), resolve every embedded hash-shaped reference against the path
it names, at the bytes on disk, and classify each reference:

| status | meaning |
|---|---|
| `MATCH` | declared hash equals measured bytes |
| `STALE` | live-binding document declares a hash that differs from the named path |
| `UNRESOLVABLE` | live-binding document names a path that does not exist |
| `RECORD_SNAPSHOT` | mismatch inside an evidence/review/summary record — expected after a revision |
| `HISTORICAL` | explicitly marked prior/superseded/archived |
| `SNAPSHOT` | provenance ledger (`*_at_authoring`, `harvested_from`): not a live path pin |
| `UNPAIRED` | hash with no path-like sibling/parent |

Live-binding documents are the manifest, the two F0 taxonomy copies, the three canonical schemas
and their three authoring mirrors, `rule_spec.json`, `KEY_MANIFEST.json`, `VARIANT_REGISTRY.json`,
`VOCAB_ALIASES.json`, and the two downstream schema pin files. Everything else under
`artifacts/formulation/evidence/`, `reviews/`, `variants/` and the summaries is a record.

## Result (measured, `VALID`, no drift during scan)

```
files scanned ................. 47
live-binding references ....... 61   (58 MATCH, 6 STALE, 0 UNRESOLVABLE)
MATCH (all documents) ......... 58
STALE ......................... 6
RECORD_SNAPSHOT ............... 11
HISTORICAL .................... 2
SNAPSHOT ...................... 12
UNPAIRED ...................... 3
unmatched 64-hex tokens ....... 0    (no 64-hex token in any scanned file escaped extraction)
findings_digest ............... 3d265b0f58b55a9e2355f486dddc95aa99e7f6098394a14c922abb64693c5d3a
```

All six `STALE` findings are the same defect, in the canonical/authoring mirror pairs:

| # | source | line | declared | named path | measured |
|---|---|---|---|---|---|
| 1 | `schemas/af_wcc_vacuum.yaml` | 304 | `675a99d0d25b…` | `artifacts/formulation/evidence/taxonomy_consistency.json` | `9e335e9ba1bf…` |
| 2 | `schemas/af_scc_c2_vacuum.yaml` | 291 | `675a99d0d25b…` | same | `9e335e9ba1bf…` |
| 3 | `schemas/af_scc_c0_vacuum.yaml` | 308 | `675a99d0d25b…` | same | `9e335e9ba1bf…` |
| 4-6 | `artifacts/formulation/schemas/af_*.yaml` (mirrors) | same | same | same | same |

Independently measured facts:

- `FROZEN.json` rev28 pins `taxonomy_consistency.json` at the measured `9e335e9ba1bf…`; the six
  schemas pin a different, older value for the same path.
- No scanned file hashes to `675a99d0d25b…` — the declared value is not stale-by-drift of the
  named object; the object it names has different bytes.
- All 44 manifest pins themselves `MATCH` (re-confirms `verify_frozen.py`'s 44/44 at these bytes).
- The 11 `RECORD_SNAPSHOT` mismatches are all in evidence/review records of past revisions
  (`close_findings_rev27_report.json` phase-`apply` hashes, `heldout_rebased.json`
  `base_sha256` → superseded F2b, `semantic_escape_rebased.json` `base_sha256` → rev11,
  `corpus_robustness_recheck.json` old `gate_sha256`, `f1_falsifier_tests.jsonl:25` a probe that
  *documents* the F0 binding staleness). They are reported, not counted as defects.

## Repair recommendation (ordering matters)

This scanner does not edit canonical files. It confirms and bounds the repair already proposed
from two independent directions (`artifacts/worker-041/f2a_pin_rca`, `artifacts/worker-043/f2a_rev12_verdict`):

1. **Repair the evidence document first.** `artifacts/formulation/tools/check_taxonomy_consistency.py`
   rewrites `taxonomy_consistency.json` on every run; the output is a pure function of four inputs
   and currently carries no input hashes. Emit `map_taxonomy_sha256`, `lead_contract_sha256`
   (and `checker_sha256` / `vocab_aliases_sha256`) into the document, then regenerate it.
   The repaired document has a new hash; measure it after this step.
2. **Then re-stamp** `f0_binding.consistency_evidence_sha256` in all six schema copies with that
   new measured hash, in one transaction with no further input edit.
3. **Then re-freeze** (`FROZEN` rev29) with updated pins for the 7 changed files (3 canonical
   schemas + 3 mirrors + evidence).

Minimal alternative, with a stated hazard: stamping the current `9e335e9b…` without repairing the
evidence resolves the six findings today and leaves the stale-by-construction mechanism in place;
if any of the four inputs is edited afterwards, the field goes stale again with no schema edit.
Either way the value must be re-measured atomically at freeze.

## Controls (7/7 pass; mutants built in a transient scratch/ copy, canonical tree never written)

| control | expected | observed |
|---|---|---|
| C1 baseline | only `consistency_evidence_sha256` in stale set | pass |
| C2 re-pin to measured evidence hash | 0 STALE | pass |
| C3 evidence path → nonexistent | ≥3 UNRESOLVABLE | pass |
| C4 one hex digit flipped | ≥3 STALE | pass |
| C5 `declared_f0_sha256` correct pin | MATCH, never flagged | pass |
| C6 `superseded: true` + stale hash | HISTORICAL, not STALE | pass |
| C7 provenance `worker_sha256` + `harvested_from` | SNAPSHOT, never STALE | pass |

## Reproduce

```bash
python3 artifacts/worker-038/ref_integrity/scan_ref_integrity.py \
  --controls --report /tmp/refint_recheck.json
# exit 0 = no live defects, 2 = live defects (this closure), 4 = control battery failed
```

## Falsifier

Any one of the following falsifies this report:

1. produce a file at `artifacts/formulation/evidence/taxonomy_consistency.json` whose sha256 is
   `675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48`, or show the six fields are
   not hash bindings;
2. exhibit a live-binding reference this scan reports `MATCH`/`RECORD_SNAPSHOT` that is in fact
   stale (e.g., a path named only through an indirection the extractor cannot see), or a 64-hex
   live pin the extractor did not pair;
3. show that a `RECORD_SNAPSHOT` mismatch is in fact a live binding the freeze depends on.

Any of the three flips the corresponding count; the `findings_digest` then changes.

## Authority

Worker evidence only. This report cannot set `status=done`, `validation_status=passed`, or any gate
verdict (`comms/PROTOCOL.md` rule 2). It does not edit any canonical artifact. `counts_as_full_schema_verdict`
is **false**: this is a mechanical binding scan, not a full-schema verdict on F1/F2a/F2b.
