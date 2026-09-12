# W067-N0-PROVENANCE-DRIFT-LEDGER-01

Class-bound task: `AF-WCC-SCALAR-SPH` / node `N0` / gate `G-NUM`. Bounded, read-only,
independent worker-067 measurement. Permitted under `numerics_lock` (N0 flat-space only;
no solver code, no self-gravitating run).

## Why

The live G-NUM reason (lifecycle `astra-lifecycle-05-close`, map `7f4f946d1f5b`, and the
controller gate audit at 00:48:44) says the only open item besides G-FORM/G-AUDIT is the
N0 node verdict (currently `revise 3.5`), with the three stop-rule items "4th resolution /
F0 re-bind / independent replication verdict" as the requirement. The audit lead's
`astra-life04-n0-verify` will read the N0 evidence chain. This task measures that chain's
declared `path -> sha256` bindings and its explicit `*_matches_on_disk` assertions against
the live bytes at one timestamp, so acceptance rests on measured bindings, not prose.

## Task (one bounded, class-bound)

Parse every declared `(path, expected-hash)` pair reachable from the current N0 acceptance
anchors, measure the live bytes, classify `MATCH / STALE / MISSING`, recompute the four
explicit provenance booleans in `fixed_replication_verdict.json`, and report which stale
pins are already recorded as drift and whether any assertion is contradicted by disk.

Anchors (all four stable before/after the sweep):

| anchor | sha256 (prefix) |
|---|---|
| `numerics/tests/n0_gate_proposal.json` | `b4192221ff7d` |
| `numerics/protocol/fixed_replication_verdict.json` | `dcad962324e3` |
| `numerics/protocol/n0_fixed_dt_certification.json` | `1677822ceb9c` |
| `numerics/CONVERGENCE_PROTOCOL.md` | `1e6cdf04d7a2` |

## Result (measured 2026-09-12T00:51+08:00)

`ledger.json` — verdict `LEDGER_COMPLETE_WITH_CONTRADICTED_ASSERTION`
(sha256 `0a0cef61c7c68c02de7160cce3bd3f8d87a16baae27acc291a75d2bf153f985c`):

- 39 bindings: **33 MATCH, 6 STALE, 0 MISSING**.
- 6 STALE = 5 recorded drift + 1 excluded by the source itself:
  - `numerics/protocol/fixed_replication_verdict.json` chained pin L7 and
    `provenance.taxonomy_sha256` L39 pin F0 rev2 `66bf917bd368…`; disk is rev5
    `0abb9ed8a961…` (the proposal's own `evidence_hashes` L325 correctly pins rev5 —
    control C1). Already recorded as drift in
    `numerics/results/flat_wave_convergence_rev3.json` L137/L140,
    `numerics/protocol/scheme_independence_review.md` L272 and `numerics/blockers.md` item 5.
  - `numerics/CONVERGENCE_PROTOCOL.md` L7 preamble inline ref `…taxonomy.yaml#66bf917bd368`
    (same rev2 pin; recorded drift, frozen so hash-bound reviews stay valid).
  - `numerics/gates.py` `907a88b1…` is the proposal's own `superseded_pins` entry (known).
  - `runtime/state/artifact_hashes.json` `d69b62dc…` is the proposal's own
    `excluded_mutable_snapshot` (controller-regenerated; deliberately not stable evidence).
  - `numerics/tests/n0_gate_proposal.json#58a175b5…` is the file's own `provenance.supersedes`
    record (historical).
- 4 explicit assertions in `fixed_replication_verdict.json` — 3 AGREE, **1 CONTRADICTS**:
  - L29 `fixed_json_sha256_matches_pinned` = true, measured MATCH → AGREES.
  - L26 `fixed_harness_sha256_matches_on_disk` = true, measured MATCH → AGREES.
  - L30 `fixed_script_sha256_matches_on_disk` = true, measured MATCH → AGREES.
  - **L31 `fixed_taxonomy_sha256_matches_on_disk` = true, measured STALE → CONTRADICTS.**
    The artifact asserts a binding check that is false as written at the live bytes.

Controls: 7/7 pass (C1 known-good rev5 binding MATCH; C2 known-stale rev2 binding STALE;
C3 corrupted-expectation flip MATCH→STALE; C4 missing-path detection; C5 assertion detector
true+mismatch→CONTRADICTS; C6 anchor stability; C7 every swept byte identical after the sweep
— read-only proof).

## Significance and scope

- The contradicted boolean is a **provenance/self-consistency defect, not a numerical one**:
  the verdict's q1/q2 scheme-independence numbers and the certified orders do not reference
  the taxonomy pin (its own `binding_status` is `PROVISIONAL`, and the proposal's
  `class_binding_note` says the F0 binding is not load-bearing for the order claim). No
  certified number changes.
- It **is** a false statement inside an artifact listed in the N0 acceptance chain
  (`n0_gate_proposal.evidence_hashes` L321) and one of the stop-rule evidence items, so a
  strict N0 acceptance should either have it repaired or carry an explicit proviso.
- Minimal repair (not applied; owner `astra-lead-numerics`, CF-12 one canonical path/one
  owner): update `chained_evidence_hashes["research_map/formulation_taxonomy.yaml"]` (L7) and
  `provenance.taxonomy_sha256` (L39) to the measured rev5 hash and re-evaluate L31; the three
  AGREE booleans are already correct. No other sweep row needs action.

## Reproduction

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-067/n0_provenance_ledger/check_provenance.py   # exit 0; exit 2 = fail-closed
```

The checker writes only `ledger.json` in this directory; canonical paths are measured,
never written (C6/C7).

## Falsifier

Re-run at the four anchor hashes above. The ledger is withdrawn if any control fails, if an
anchor drifts, or if a binding classified STALE re-hashes to its declared value (or vice
versa). The contradicted-assertion finding is withdrawn if `fixed_replication_verdict.json`
is repaired so L7/L39 equal the measured canonical taxonomy and L31 is re-evaluated, or if
the artifact is formally superseded by an ingested event.

## Not claimed

No gate verdict, no node status change, no `validation_status=passed`, no order/numerics
claim, no priority/ownership change, no canonical write, no N1/self-gravitating work. Worker
measurement and review only; acceptance remains with `astra-lead-audit` / the controller.
