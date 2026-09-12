# W022-EVBIND-GUARD-01 — writer/publish guard for the consistency-evidence binding regression

Worker: `worker-022` (bounded execution worker). Mode: **measurement + instrument** — no canonical
file written, no gate verdict, no node status, no schema edit. The guard is read-only on every
canonical path; it writes only under `artifacts/worker-022/evbind_guard/`.

Gate: `G-FORM`. Classes: `AF-WCC-VAC-GEN` (F1), `AF-SCC-C2-VAC-GEN` (F2a), `AF-SCC-C0-VAC-GEN`
(F2b), plus the F0 taxonomy and the `AF-WCC-SCALAR-SPH` class it carries.

## Why this task

`worker-092` (W092-EVBIND-01) determined that the live 495-byte
`artifacts/formulation/evidence/taxonomy_consistency.json` is a **regression** produced as a side
effect of the FROZEN-pinned checker, and recommended **R2 + a writer guard**: restore/adopt the
bound revision and stop the checker from silently reverting the canonical gate-bound path. The
guard itself was the missing durable piece. This task builds and self-tests it.

## What was measured (pinned at run time; see `report.json:pins`)

| input | sha256 (prefix) |
|---|---|
| `schemas/af_wcc_vacuum.yaml` | `cce9c60146d6` |
| `schemas/af_scc_c2_vacuum.yaml` | `5476a3f2c6bc` |
| `schemas/af_scc_c0_vacuum.yaml` | `55d0a1ea9bda` |
| `research_map/formulation_taxonomy.yaml` (F0) | `0abb9ed8a961` |
| `artifacts/formulation/formulation_taxonomy.yaml` (supplement) | `d7419b4e8963` |
| `artifacts/formulation/evidence/taxonomy_consistency.json` (live) | `9e335e9ba1bf` (495 B) |
| declared `consistency_evidence_sha256` in all three schemas | `675a99d0d25b` (728 B archived) |
| `artifacts/formulation/tools/check_taxonomy_consistency.py` | `de356d999ea3` |
| `artifacts/formulation/FROZEN.json` | `2f358f6722d9` (rev28) |

## Finding — `REGRESSION_UNBOUND`, not a phantom and not a stale declaration

All three schemas declare the same evidence hash `675a99d0`. It resolves to an archived 728-byte
revision whose embedded tree bindings **still equal today's trees**:

```
map_taxonomy_sha256  = 0abb9ed8a961…  == live research_map/formulation_taxonomy.yaml
lead_contract_sha256 = d7419b4e8963…  == live artifacts/formulation/formulation_taxonomy.yaml
measured_at          = 2026-09-12T00:32:02+08:00
```

The live document at the canonical path (`9e335e9b`, 495 B) has lost both fields. FROZEN rev28 pins
the unbound revision. So the declaration is not pointing at nothing (worker-043's HF-043-1,
"the `675a99d0` bytes exist nowhere on disk", is **falsified** — a repo-wide scan finds 12
byte-identical copies, and the guard resolves the declared revision from *third-party* archives,
not from its own pin), and it is not stale (its bindings match the live trees). The canonical path
holds a document that is *weaker than the one the schemas cite*.

Two consequences the guard makes explicit:

1. **`publish_gate = BLOCK`.** Any publish step that would write the canonical evidence path from
   the lean checker output must be refused while the document lacks the two tree bindings.
2. **The repair direction matters.** Re-stamping the three schemas to `9e335e9b` (option R1) would
   bind the verdicts to the *unbound* revision. Adopting a bound revision (R2) or making the
   checker emit the digests (R3) keeps the chain.

## Independent semantic recomputation (not importing the project's checker)

A second implementation compares the two F0 trees class-by-class — family, regularity token,
alias-canonicalised conclusion type, non-empty exclusions, test-case presence, SCC
`known_obstruction`, canonicalised genericity kind — plus the D1/D2/D3 contract-text checks and the
C0⇒C2 one-way / C2⇏C0 forbidden entailment pair. Result: **4/4 classes consistent, 0 errors, 0
divergences**, agreeing with the live payload. A naive text scan would have flagged
`AF-WCC-SCALAR-SPH` for containing `J-(I+)`; that token occurs **only inside a bracketed rev5
historical note saying the set-based wording is superseded and is not this class's predicate** —
the metalinguistic-mention pattern of CF-16, handled by stripping bracket notes before scanning.

Soft finding (H7): the schema bindings' `checked_at` is `00:31:41`, but the declared evidence's
own `measured_at` is `00:32:02` — the binding was stamped 21 s before the revision it names
existed. Minor, but it is a real ordering defect in the same family as the earlier future-dating
findings.

## Instrument and controls (all 8 behaved as required; `instrument_ok = true`)

| id | control | observed |
|---|---|---|
| C1 | replay the FROZEN-pinned checker in a sandbox copy | reproduces the live `9e335e9b` byte-for-byte, exit 0 |
| C2 | mutate `AF-SCC-C0-VAC-GEN` family SCC→WCC in the sandbox | exit 1, `consistent=false` (C1's PASS is meaningful) |
| C3 | restore the sandbox | reproduces `9e335e9b` again |
| C4 | bound-candidate round-trip | guard accepts, 0 problems |
| C5 | drop `map_taxonomy_sha256` from the candidate | guard refuses |
| C6 | mutate `lead_contract_sha256` | guard refuses |
| C7 | future-dated `measured_at` | guard refuses |
| C8 | unknown declared hash | classified `PHANTOM`, not `REGRESSION` |

The destructive-writer mechanism is proved **without touching the canonical path**: the sandbox
checker's `ROOT` is its own copy, so its write lands in `sandbox/artifacts/...`.

## Deliverables

- `verify_evbind_guard_022.py` — re-runnable, fail-closed guard + self-test (exit 0 iff the
  instrument is sound and no pinned input drifted mid-run).
- `report.json` — full machine record: pins, declaration census, 9 checks, 8 controls, drift.
- `candidate/taxonomy_consistency.bound.json` — a **non-canonical** bound candidate for the owner
  to adopt: live semantic payload + both live tree hashes + `measured_at = FROZEN.frozen_at`
  (deterministic, non-future). Owner adoption and re-pinning remain the lead's call.
- `pinned/` — byte copies of every input, with `manifest.json`.
- `sandbox/` — isolated replay tree.

## Falsifier

Repair the ordering — keep or restore a consistency-evidence revision carrying
`map_taxonomy_sha256` and `lead_contract_sha256` equal to the live trees at the canonical path (or
re-declare all three schemas to such a revision) — then re-run the guard: classification becomes
`BOUND_OK` and the publish gate `ALLOW`, falsifying the finding. Instrument self-falsifiers: any of
C1–C8 not behaving as required, or any pinned input moving mid-run, voids this report rather than
falsifying it.

## Authority

Worker measurement only. `validation_status` stays `unverified`; no node completion, gate verdict,
or canonical write is claimed. `astra-lead-formulation` owns the evidence path; `astra-lead-audit`
adjudicates.
