# W067-N0-FIXEDVERDICT-REV2-INDEP-01 — independent verification of the N0 fixed-replication verdict rebind

**Worker** worker-067 · **class** `AF-WCC-SCALAR-SPH` · **node** `N0` · **gate** `G-NUM`
**Actor authority** bounded breadth worker. Advisory verification only: no gate verdict, no node
transition, no `validation_status=passed`, no `numerics_lock` change. Read-only on every canonical
path; wrote only under `artifacts/worker-067/` and `runtime/state/worker-067_checkpoint_9.json`.

## Why this task

The live numerics lead lifecycle (00:55:21) closed the stale-F0-pin defect of
`numerics/protocol/fixed_replication_verdict.json#dcad962324e3be15` by publishing a successor,
`numerics/protocol/fixed_replication_verdict_rev2.json#7954d2d355451e3d`, and claimed it re-runs
the identical R1/R2/R4/R5 arithmetic (79 numeric leaves, max difference 0.0) with the corrected
taxonomy measurement. That claim was self-verified by its author. It is the proposed discharge of
the third live C8 protocol dissent (`w067-provledger`), so it needs an independent check — and the
answer decides whether the dissent is dischargeable now or only after an owner binding action.

## Verdict

`REV2_METADATA_ONLY_AND_PINS_RESOLVE__SUPERSESSION_NOT_YET_BOUND`

| check | result | measured basis |
|---|---|---|
| A1 hard pins + no-write canary | **PASS** | 6 pinned prefixes measured before and after; all 10 anchors byte-identical across the run |
| A2 declared-hash chain | **ALL_RESOLVE** | 9/9 resolvable claims resolve on disk (chained evidence + provenance + source verifier); the frozen-run rev2 taxonomy pin is correctly marked historical and absent |
| A3 metadata-only claim | **REPRODUCED** | independent leaf walk: **79 numeric leaves equal, 0 differ** (matches the declared `numeric_leaves_compared=79`, `max_abs_difference=0.0`, `differing_leaves={}`); 24 expected change leaves, **0 unexpected differences** |
| A4 frozen-run flag | **CONSISTENT** | generator semantics recomputed: frozen run pin `66bf917bd368` ≠ live taxonomy `0abb9ed8a961` → flag `false` is correct; see ambiguity finding F1 |
| A5 supersession operativity | **NOT YET BOUND** | 3 live consumers still cite the superseded artifact without the successor; see finding F2 |
| C1–C5 controls | **5/5 PASS** | no-write canary, chain mutation, numeric mutation, flag flip, citation-count override |

## Findings

**F1 — field-name ambiguity (non-blocking, residual risk).** The successor carries the rebound pin
`provenance.taxonomy_sha256 = 0abb9ed8a961` (resolves on disk) *and*
`provenance.fixed_taxonomy_sha256_matches_on_disk = false`. Under the generating script's
definition (`numerics/protocol/verify_fixed_scheme_independence.py#a0daf1271bfb`, expression
`fixed["provenance"]["f0_taxonomy_sha256"] == taxonomy_sha`) the flag means "the **frozen run's**
original pin equals live taxonomy" — `false` is correct there, and the `taxonomy_rebind` block
documents it. Under the field *name* it reads "this record's taxonomy pin does not match disk",
which contradicts the rebound pin. A fail-closed consumer keying on the bare boolean would misread
the successor as unbound. No measured number depends on it.

**F2 — the supersession is dischargeable-by-binding but not yet bound (adjudication input).** Live
consumers that cite the superseded artifact and do **not** cite the successor:

| consumer | cites superseded | cites successor |
|---|---:|---:|
| `numerics/tests/n0_gate_proposal.json#b4192221ff7d` | 4 | 0 |
| `numerics/protocol/n0_c4_registration_manifest.json#49e8316fde60` | 8 | 0 |
| `numerics/protocol/format_conditions_disposition.json#e7c05ff33fe2` | 5 | 0 |
| `numerics/protocol/n0_gate_proposal_leadverify.json#ea4cf6c9bd3c` | 5 | 3 |

The lead-verification artifact names the successor; the proposal, the C4 registration manifest and
the disposition artifact do not. Until the audit adjudication
(`astra-life05-gnum-protocol-adjudication`, due 02:15) or the controller binds
`fixed_replication_verdict_rev2.json#7954d2d355451e3d` as the replication evidence of record, the
C8 `w067-provledger` dissent remains live. This task does not adjudicate C8 and proposes no gate
verdict.

**F3 — arithmetic independence confirmed.** The 79/0.0 claim is reproduced by a leaf walk written
independently of the lead's rebind script, comparing every numeric leaf present in both artifacts
with exact equality (no tolerance): scheme own/harness drifts, Q1/Q2 orders, p/delta/agreement
values and R2/R5 bounds are all bit-equal. The only non-numeric differences are the three declared
rebind fields, the two refresh stamps, `runtime_seconds` (volatile), and the four new documentation
blocks (`supersedes`, `taxonomy_rebind`, `numeric_delta_vs_superseded`, `source_verifier`).

## Method

`check_fixedverdict_rev2.py` (stdlib only) measures its anchor hashes **before** the checks and
again **after** them and exits 2 on any drift or failed control, 1 on an unexpected difference,
0 otherwise. The comparison, chain resolution, generator-semantics recomputation and citation
counts are deterministic; all mutation controls operate on in-memory deep copies, never on disk.

Controls (5/5, in `report.json`):
- **C1** no-write canary — all 10 anchors byte-identical before/after.
- **C2** rebind the successor's chained taxonomy pin back to `66bf917b` in memory → chain reports unresolved.
- **C3** perturb one shared numeric leaf in memory → comparator reports an unexpected numeric difference.
- **C4** flip the frozen-run flag to `true` in memory → generator-semantics recomputation flags it.
- **C5** append the successor hash to a copy of the proposal text → that consumer leaves the unbound set.

## Reproduction

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-067/n0_fixedverdict_rev2_indep/check_fixedverdict_rev2.py \
  --out artifacts/worker-067/n0_fixedverdict_rev2_indep/report.json
```

## Falsifiers

Withdrawn if any of: (a) either verdict artifact, the canonical taxonomy, the frozen run, or
`verify_fixed_scheme_independence.py` no longer hashes to its pinned prefix at re-measurement
(moving target); (b) a re-run finds any differing numeric leaf or any successor difference outside
the declared rebind metadata (then the metadata-only claim is false); (c) the successor's declared
chain has an unresolved entry; (d) a live consumer that cites `dcad9623` without the successor is
re-pinned to the successor by an authoritative event (then F2 only is discharged); (e) the
rebind/naming ambiguity is removed by renaming or documenting the flag in the successor (then F1
only is withdrawn).

## Not claimed

No G-NUM verdict, no node completion, no gate self-pass, no `numerics_lock` change (N1 remains
locked, no solver artifact touched), no physics/censorship claim, no repair of either artifact
(CF-12: one canonical path, one owner).
