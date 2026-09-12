# W079-GFORM-REV29-BINDCHAIN-CENSUS-01 (worker-079)

Independent, read-only resolution of the `f0_binding` chain declared inside the three vacuum
class schemas at the FROZEN rev29 pins, plus cross-schema uniformity and the schemas' own
refresh rule. Scope is disjoint from `artifacts/worker-099/frozen_r3_pin_census/` (worker-099
census-tests the 50 FROZEN-declared files and both mirrors; this artifact resolves the binding
chain *inside* F1/F2a/F2b and its pointers).

## Question

ASTRA_HANDOFF pass-07 withholds G-FORM pending `astra-life05-verify-gform-r3`:
non-author independence **plus FROZEN/per-file pin binding**. The audit-r2
`*-bindchain-*` addenda asked for exactly this chain check, but they were dispatched at the
rev27 pins; the schemas moved to rev13 bytes (FROZEN rev29) afterwards, and no dedicated
per-class `f0_binding` chain census at the rev29 pins existed in `reviews/`.

## Method

`run_bindchain_079.py` reads its pin table from `PREREGISTRATION.json` (`ca59593f8601`) and
measures every pinned input twice. It then, per class:

1. `SCHEMA-PIN-CANONICAL` / `SCHEMA-PIN-MIRROR`: canonical schema and `artifacts/formulation`
   mirror both match the FROZEN rev29 declaration.
2. `MIRROR-BYTE-EQUAL`: the two copies are byte-identical.
3. `F0-DECLARED-RESOLVES`: `f0_binding.declared_f0_artifact` measures `declared_f0_sha256`.
4. `EVIDENCE-DECLARED-RESOLVES`: `consistency_evidence` measures `consistency_evidence_sha256`.
5. `SUPPLEMENT-DECLARED-RESOLVES`: the class-contract supplement measures the FROZEN declared hash.
6. `POINTER-CANONICAL-CLASS`: `#classes.<class_id>` resolves in the canonical taxonomy.
7. `POINTER-SUPPLEMENT-CONTRACT`: the top-level and `f0_binding` supplement pointers are
   identical, their path equals `f0_binding.class_contract_supplement`, the
   `class_contract_pointer` path equals `declared_f0_artifact`, and `#class_contracts.<class_id>`
   resolves in the supplement.
8. `REFRESH-RULE-SATISFIED`: the schema's own rule ("if the declared F0 artifact changes hash,
   this binding must be refreshed and the consistency check re-run before any gate verdict") is
   satisfied at the scan instant.
9. `SCHEMA-CLASS-ID-MATCH`, `EVIDENCE-LISTS-CLASS`.

Globals: `CROSS-SCHEMA-UNIFORMITY`, `FROZEN-DECLARES-BINDING-FILES`, and two NOTE-level
annotations (evidence freshness, taxonomy disjointness recorded verbatim).

Fail-closed: any pin drift exits 2 and writes no report; any control failure exits 3 and writes
no report; a missing pinned input is `MISSING`, never a silent pass. Five pre-registered controls
(positive match, comparator mismatch detection, bogus-fragment NOT_FOUND, missing-file
fail-closed, byte-flip detection) all behave as declared.

`report.json` is **content-deterministic**: it contains no wall-clock timestamps and no file
mtimes, so re-running at the same pins reproduces it byte-for-byte. Volatile scan metadata
(per-pin mtimes, scan instant, quiescence flag) goes to `run_log.json`, which is explicitly not
part of the reproducible claim.

## Result (measured 2026-09-12 01:13-01:15 +08:00)

- **verdict = PASS**, 0 hard failures: 11 rows × 3 classes all PASS (36 PASS checks, 2 NOTE).
- FROZEN rev29 self-hash `815e08079aefbc168f...` (matches the controller-cited prefix);
  all 9 binding-relevant files declared by FROZEN and matching live bytes.
- All three schemas declare one identical tuple: canonical F0
  `research_map/formulation_taxonomy.yaml` `0abb9ed8a961`, evidence
  `artifacts/formulation/evidence/taxonomy_consistency.json` `9e335e9ba1bf`, supplement
  `artifacts/formulation/formulation_taxonomy.yaml` `d7419b4e8963`.
- `REFRESH-RULE-SATISFIED`: declared hashes equal the live hashes at scan time, so the rev13
  refresh (astra-life05-evidence-binding-repair) is current at rev29.

## Soft notes (not failures)

- **N1 — post-freeze byte-identical rewrite of the evidence file.** `taxonomy_consistency.json`
  has mtime 01:15:44, newer than every `f0_binding.checked_at` (00:53:20 / 00:53:41) and newer
  than `FROZEN.frozen_at` (00:57:26), while its bytes still measure the declared `9e335e9b`
  (volatile epoch in `run_log.json`; quiescence verdict `WRITER_ACTIVE_BYTE_IDENTICAL`).
  The pin contract is sha256-based (FROZEN `change_protocol`), so this is writer activity, not a
  pin violation. Because the evidence file carries no timestamp and no input-hash field, the
  "check re-run" claim is only verifiable by hash equality — a stale byte-identical rewrite is
  indistinguishable from a fresh run. Same observation as worker-099's `quiescence_verdict=
  WRITER_ACTIVE`, recorded independently here.
- **N2 — naming asymmetry.** The top level of each schema carries
  `class_contract_supplement_pointer` but no bare `class_contract_supplement` path field, while
  `f0_binding` carries both. All compared fields agree today, so no consumer can misbind the
  supplement; a strict symmetry linter would flag it.

## Instrument honesty

The first harness run produced 3 spurious hard failures because the agreement condition
incorrectly required a top-level `class_contract_supplement` field that does not exist at top
level. The instrument was corrected against the pre-registered rule text (pointers agree on
path+fragment) **before** any event was emitted; no report from the buggy revision was published.

A second instrument defect was caught after the first outbox block was written: the report
embedded per-pin mtimes, so a byte-identical post-freeze rewrite of the evidence file changed
the report hash without changing any measured hash. The report was made content-deterministic
(mtimes moved to `run_log.json`) and the **pre-ingest** outbox block was replaced; no measurement
value, verdict or control changed. The superseded hash `472fd1871490` appears nowhere in the
final accepted stream.

## Files

| path | sha256 (first 12) |
|---|---|
| `PREREGISTRATION.json` | see `SHA256SUMS` |
| `run_bindchain_079.py` | see `SHA256SUMS` |
| `report.json` | see `SHA256SUMS` |
| `run_log.json` | see `SHA256SUMS` (volatile) |
| `emit_events_079.py` | see `SHA256SUMS` |
| `runtime/state/w079_checkpoint_5.json` | see `SHA256SUMS` |

Not claimed: gate verdict, node completion, schema-content review, F0 correctness, ledger
correctness, any `validation_status` beyond `unverified`.
