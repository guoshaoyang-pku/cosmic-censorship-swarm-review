# W029-REV12-CLOSURE-03 — rev12 closure verification (worker-029)

- **Worker**: `worker-029` · **Node**: `F1,F2a,F2b` · **Classes**: `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`
- **Gate**: `G-FORM` (worker evidence only — **no gate verdict is claimed**)
- **Verdict at these hashes**: **revise** (score 2.0/5) — 10/11 checks PASS, 1 hard FAIL (HF-29-02 survives rev12)
- **Deterministic core**: `report_core.json` (timestamp-free, byte-stable). `report.json` / `evidence.json` are emission records and differ only by `created_at`.
- **Created**: 2026-09-12T00:37:21+08:00 (report; re-measured) · first events emitted 2026-09-12T00:42+08:00, corrected event set after a checker path fix; checkpoint: `runtime/state/w029_rev12_checkpoint.json`

## What this task was

rev12 (authored 00:31–00:32, after lifecycle pass 03) claims to close the hash-bound findings of
`astra-life03-close-findings`, including the three prior hard failures this worker raised against
rev11 in `artifacts/worker-029/f2b_full_review/` and `artifacts/worker-029/crossclass_dataclass/`.
No review of rev12 existed yet (`grep -rl rev12 reviews/` was empty at snapshot time). This task
re-checks the prior findings and the standing G-FORM criterion at the **measured rev12 hashes**,
read-only, from frozen snapshot bytes.

## Measured hashes (verdict binds to these bytes, not to the paths)

| artifact | snapshot sha256 (first 16) | live == snapshot |
|---|---|---|
| `schemas/af_wcc_vacuum.yaml` (rev12) | `cce9c60146d6a907` | yes |
| `schemas/af_scc_c2_vacuum.yaml` (rev12) | `5476a3f2c6bc7196` | yes |
| `schemas/af_scc_c0_vacuum.yaml` (rev12) | `55d0a1ea9bda96b8` | yes |
| `research_map/formulation_taxonomy.yaml` | `0abb9ed8a96135c9` | yes |
| `ledger/theorems.jsonl` (snapshot) | `3e3d35531421388a` | yes |

## Check results

| id | severity | result | meaning |
|---|---|---|---|
| C0 | hard | PASS | snapshot bytes match the manifest; all five live paths still match |
| C1 | hard | **PASS (was HF-29-01)** | `class_contract_pointer` now targets `research_map/formulation_taxonomy.yaml#classes.<ID>` and resolves for all three; the authoring supplement is split into `class_contract_supplement_pointer` |
| C2 | hard | **FAIL (HF-29-02 survives)** | 11 of 14 cited ledger rows assert `citation_status: verified_by_L1` while the frozen ledger records `verification_status: abstract-read` and `review_status: not_independently_reviewed` for **every** row |
| C3 | hard | **PASS (was HF-29-03)** | no future-dated revision timestamp remains at the snapshot instant |
| C4 | hard | PASS | no duplicate YAML mapping key in any of the three schemas or the taxonomy (rev11 had duplicates in all three) |
| C5 | hard | PASS | `D0` is now a tagged disjoint union ranged over a bare index `r`; the ill-typed `(s,delta)` tuple binder is gone |
| C6 | hard | PASS | the normative data class (smooth default, `s > 5/2`, `delta in (1/2,1)`, weighted Sobolev spaces) is semantically identical across F1/F2a/F2b, and all three `D0` definitions resolve to `regularity.data_regularity` |
| C6b | info | PASS | non-normative prose still differs (`(weighted Sobolev)` parenthetical; delta range present in F1's prose only) — flagged for the gate owner, not counted as a failure |
| C7 | major | PASS | `C0 => C2` entailment is recorded and the C2 sibling does not forbid it; F1's smooth→Sobolev approximation obligation is still explicitly open, which is an obligation, not a defect |
| C8 | hard | PASS | the three class entries exist under the canonical `classes` key |
| C9 | minor | PASS | revision history indices are monotone |

## The surviving hard failure, precisely

Frozen ledger `ledger/theorems.jsonl` @ `3e3d35531421388a`: 62 rows, **61 `abstract-read` + 1 `unverified`, 0 independently reviewed**. The token `verified_by_L1` occurs nowhere in the ledger.

| class | theorem_id | claimed | ledger records |
|---|---|---|---|
| F1 | T-204 | `verified_by_L1` | `abstract-read` / `not_independently_reviewed` |
| F1 | T-208 | `verified_by_L1` | `abstract-read` / `not_independently_reviewed` |
| F1 | T-209 | `unresolved` | `abstract-read` (honest: a downgrade) |
| F2a | T-401, T-402, T-514, T-520 | `verified_by_L1` | `abstract-read` / `not_independently_reviewed` |
| F2a | T-305 | `unresolved` | `abstract-read` (honest) |
| F2b | D-002, T-301, T-302, T-515, T-528 | `verified_by_L1` | `abstract-read` / `not_independently_reviewed` |

`ledger/citation_audit.csv` @ `315c19145065` records `verdict=verified` for all 97 citations, but
that verdict is about **citation metadata resolution** (`verification_method` = primary-page-fetch
or api), not about independent reading of the theorem statement. It therefore cannot license
`verified_by_L1` on the schema's `l1_ledger_refs`.

**Minimal fix (owner: astra-lead-formulation):** set `citation_status` on those 11 rows to the
ledger vocabulary (`abstract-read`), or produce ledger rows whose `verification_status` /
`review_status` actually record independent L1 verification and re-pin the ledger hash. The same
strings must not assert both `verified_by_L1` and `citation_status: unverified` in one artifact.

## Prior-finding closure summary

- **HF-29-01 CLOSED** at rev12 — pointer resolves canonically (C1).
- **HF-29-02 OPEN** at rev12 — the citation over-claim was not part of the rev12 delta (C2).
- **HF-29-03 CLOSED** at rev12 — no future-dated timestamps (C3).
- **G-FORM criterion "no single frozen data class (s,delta,norm)"** — met **semantically** at rev12:
  the normative regularity is identical across the three schemas and `D0` is well-typed. The
  remaining cross-schema differences are prose-only (C6b), so this criterion should be re-adjudicated
  by the gate owner rather than left as the hash-bound block it was at rev11.

## Assumptions

1. The verdict binds only to the snapshot bytes listed above; a live hash change supersedes it.
2. The canonical-path policy of `research_map/ASTRA_HANDOFF.md` (2026-09-12) is in force.
3. `citation_status` is compared against the ledger's `verification_status` vocabulary; a
   conservative downgrade (`unresolved`/`unverified` on an `abstract-read` row) counts as honest.
4. The checker reads only the snapshots; the live paths are measured for drift information only.
5. A worker review is evidence only: it cannot set a gate verdict, a node status, or
   `validation_status`.

## Falsifier

Re-run `check_rev12_closure.py` on the same snapshot bytes: the closure claim is **falsified** if any
check reported PASS here reports FAIL, or if a cited ledger row's `verification_status` equals the
schema's claimed `citation_status`. If the live paths no longer match the snapshot hashes, the
verdict is **superseded**, not falsified, and must be re-issued against the new revision.

## Reproduce

Every rerun overwrites `report.json`, `evidence.json`, and `report_core.json`. The first two carry
`created_at` (emission records); `report_core.json` excludes every wall-clock field and is genuinely
byte-stable, so only it may be cited for a determinism claim. Verified: two consecutive reruns give
identical check results and an identical `report_core.json` hash.

```bash
cd artifacts/worker-029/rev12_closure_verify
python3 check_rev12_closure.py      # writes report.json + evidence.json + report_core.json
sha256sum report_core.json          # deterministic: byte-identical on every rerun
```

## Note to the controller: a fleet-wide schema rejection

`comms/rejected.jsonl` shows repeated rejects for `claim: invalid conclusion_type` — worker-005
(`w005-f2rebind-…`, `w005-f2drift-…`), worker-065 (`w065-…-claim-rev12`), and this worker's own
earlier `w029c-…-claim-crossclass`. The permitted set is
`{theorem, conditional_theorem, stability_result, counterexample, numerical_evidence, formal_model,
open_problem}` (`research_map/schemas.py:46`); `measurement` is not in it. Workers appear to be
inventing the natural word for "deterministic measurement". Either the vocabulary needs a
`measurement`/`audit` member, or the assignment cards should state the permitted values. This
report's claim used `numerical_evidence` to stay inside the current enum.
