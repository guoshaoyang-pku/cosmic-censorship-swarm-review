# W023-L0-HF02-INTEG-01 — end-to-end integration of the HF-02 ledger-disjunction branch

`worker-023`, bounded lifecycle, read-only on canonical artifacts.
**Worker-level completion claim only: no node status, no gate verdict, no `validation_status=passed`.**

## Question

worker-093 proposed `check_ledger_class_disjunction()` as a patch to
`artifacts/audit/audit_lib.py` and verified the function *in isolation*.
worker-023 (previous instance) verified *composition* of the two open HF-02
proposals against an extracted copy of the checker. Neither verified the branch
**inside the canonical runner**. This task closes that gap:

> At the pinned bytes, does the 093 diff apply cleanly, and does **one wiring
> line** in `audit_run.py` make the real runner flag exactly the 8 dual-class
> ledger rows — adding nothing else and removing nothing — deterministically?

## Pinned inputs (fail closed; `run_integration_023.py` exits 2 if any moved)

| input | sha256 |
|---|---|
| `ledger/theorems.jsonl` | `a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28` |
| `artifacts/audit/audit_lib.py` | `ae573db84631b970caeea46e8821aee8af66166f6a5f16251e4a6c819a377c8c` |
| `artifacts/audit/audit_run.py` | `3b27dd3fef7f41488158099f888e3685dc8d9cca9f0507ad46c4d01f9bd2c411` |
| `artifacts/audit/evaluation_rubric.yaml` | `d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885` |
| `artifacts/worker-093/l0_rev3_review/proposed_hf02_disjunction_patch.diff` | `0247a5c93acc0e015d09cf4dcec8c643696d4328b748c871857fb82cc9b4669a` |
| `artifacts/worker-093/l0_rev3_review/patched_audit_lib.py` (declared post-patch bytes) | `9c8def1b50379e7cb5b6414cdf73c31e891276b2cf1bf8635a25aad7b4b1de8e` |

The live map is a moving target; its snapshot hash is recorded per run in
`report.json` (`pins["research_map/research_map.json@snapshot"]`). Only
within-run deltas are interpreted.

## Method

Two frozen sandboxes under `tmp/w023_hf02_integration/` mirror only what the
runner reads (audit tooling, rubric, ledger, map, `started_at`). The patched
sandbox:

1. applies the 093 diff with GNU `patch -p1` — dry run then real apply — and
   checks the result hashes to the declared `patched_audit_lib.py`;
2. inserts the missing call site in the copied `audit_run.py`:

   ```python
   claimv += A.check_ledger_class_disjunction(corpus["records"], classes)
   ```

   (see `runner_wiring.diff`; one insertion, anchored before the HF-13 block).

Six runner executions: baseline and patched, each against a trimmed map
(`groups=[]`, isolates claim-side detections) and the full frozen map snapshot
(a partial mirror — deltas only), plus a rerun pair for determinism. All runs use `--scan <sandbox>/ledger
--quiet --kind findings --fail-on-critical`, so the delta is attributable to
the ledger branch alone. 15 controls exercise the patched function on synthetic
records and on the frozen corpus.

## Results (machine output: `report.json`; independent re-derivation: `verification.json`)

| scenario | violations | HF-02 disjunction rows | derived G-AUDIT | exit |
|---|---:|---|---:|---:|
| baseline, trimmed map | 0 | none | pending | 0 |
| baseline, full map | 2 partial-mirror HF-05/06 | none | fail* | 2 |
| patched, trimmed map | 8 | the 8 expected ids | fail | 2 |
| patched, full map | baseline + 8 | the 8 expected ids | fail | 2 |

\* the sandbox mirrors only the files the ledger scan reads, so done-node
artifact-existence checks in the full-map variant are **not faithful** and its
absolute verdicts are not interpretable. The patch-attributable delta is
identical in both variants: **8 added HF-02, 0 removed, 0 other changes**.
Patched exit 2 is `--fail-on-critical` firing on criticals, not a crash.
Reruns are digest-identical.

Controls: **15/15**. Fifteen checks in the report: **14/14** (plus the
independent verifier: **28/28**, including re-execution of the frozen trimmed
scenarios). The eight rows: `D-004 D-005 T-303 T-305 T-402 T-515 T-526 T-528`.

## Findings

- **F1 (integration verified).** The 093 diff is byte-faithful and sufficient
  once wired; the wired runner flags exactly the 8 dual-class rows.
- **F2 (major, instrument).** The diff ships **no call site**, so P-CODE alone
  is inert. A landing change must include `runner_wiring.diff`.
- **F3 (minor, instrument).** `audit_run.py:142-143` derives `G-FORM` from
  `any(c.get("class_id") for c in [])`, a constant-False expression: G-FORM can
  never leave `pending` from this runner. Observed in all six runs.
- **F4 (consequence).** Landing P-CODE at this ledger flips the derived
  `G-AUDIT` verdict `pending -> fail`. The code repair and the ledger repair
  (P-DATA shape) or a rubric amendment must land together, else the repair
  itself blocks the gate.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-023/l0_hf02_integration/run_integration_023.py --keep-sandboxes
python3 artifacts/worker-023/l0_hf02_integration/verify_report_023.py
```

The driver exits 0 on pass, 2 if a pinned input moved (verdict void), 3 on a
failed check/control. The verifier re-derives every assertion from `raw/` and
re-executes the frozen scenarios.

## Falsifier

Re-run at the same pins. Falsified if: any pinned hash differs (void, not
wrong); the patched runner reports other than exactly the 8 expected rows; the
canonical runner reports any of them; an added violation is not HF-02
ledger-disjunction; the patched `audit_lib.py` does not hash to `9c8def1b5037`;
or any control fails to reproduce its expected value.

## Scope limits and overlap

- Sandboxed frozen inputs; the live workspace and map may move after the run.
- No literature re-reading, no L1 re-fetch: this is a tooling integration test.
- Overlap: worker-093 verified the function in isolation and the validator gap;
  the previous worker-023 verified P-CODE + P-DATA composition against an
  extracted checker (`composition-023.json`). This artifact adds the missing
  end-to-end runner wiring, the two-file landing requirement, and the gate
  consequence. Membership of the 8-row set agrees with both.
