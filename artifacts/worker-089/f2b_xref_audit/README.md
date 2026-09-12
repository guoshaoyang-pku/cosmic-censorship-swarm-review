# W089-F2B-XREF-01 — independent cross-artifact integrity audit of canonical F2b

**Worker:** `worker-089` (no assignment card existed for this id; task taken under the bounded-worker
prompt: *take one available class-bound task; if none, inspect the immediate queue and propose one
artifact-backed task*).

| field | value |
|---|---|
| class | `AF-SCC-C0-VAC-GEN` (node **F2b**, gate **G-FORM**) |
| target | `schemas/af_scc_c0_vacuum.yaml` @ `1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508` (rev 11, 33 276 B) |
| pinned snapshot | `pinned/af_scc_c0_vacuum.1bb78ce9….yaml` (byte-exact) |
| checker | `check_f2b_xref.py` (deterministic; stdlib + PyYAML; no network) |
| report | `xref_report.json` |
| verdict | **accept**, *mechanical scope only* — not a semantic review, not a gate verdict |
| controls | 7 planted defects all caught by their designated check; unmodified schema clean (0 hard findings) |
| stability | 120 s window / 13 samples: **0 drift** on F2b, F2a, F1, canonical taxonomy and FROZEN |

## What was checked (10 checks, all machine-checkable)

| id | check | result at `1bb78ce9` |
|---|---|---|
| X1 | input pin integrity (sha256/bytes for 8 inputs) | pass |
| X2 | `class_id` = components = `node_id` = regularity token `C0` | pass |
| X3 | sibling disjointness is **mutual** with F2a (`AF-SCC-C2-VAC-GEN`) | pass |
| X4 | `anti_scope` holds only frozen class ids; same-class entries are tagged variants (`kind`+`why`); sibling/WCC counter-classes present | pass |
| X5 | all 6 `l1_ledger_refs` resolve in `ledger/theorems.jsonl` | pass |
| X6 | every `l1_status` equals the ledger row status; provisional rows appear in `artifacts/literature/unresolved.jsonl` | pass |
| X7 | `f0_binding` names the canonical taxonomy and its declared hash equals the measured hash | pass |
| X8 | F2b and F2a induce the **same** nested order `E_C2 ⊂ E_{C^1,1} ⊂ E_H2loc ⊂ E_C0`; no inversion, no cycle | pass |
| X9 | exactly one regularity token (`C0`) in `conclusion_type`; no `C0`/`C2` merge in conclusion-bearing fields | pass |
| X10 | canonical == authoring tree == `FROZEN.json` (rev 25) for F2b | pass |

## Controls (why "pass" is not an assertion)

Seven defects are planted in-memory in the parsed schema, written to `controls/M*.json`, and each must
be caught by its designated check: `M1` status flip → X6; `M2` missing citation id → X5; `M3` broken
sibling → X3; `M4` corrupted F0 hash → X7; `M5` inverted containment → X8; `M6` `C0`/`C2` merge → X9;
`M7` untagged self-reference → X4. `N0` (unmodified) must stay clean. All 8 behave as required.

## Stability timeline (the part a future review inherits)

The canonical set had been republished roughly every 40 s before this run (F2b was observed at
`a2aef5ac` 00:18:37, `1bb78ce9` 00:19:14). During this audit the five pinned files were sampled
13× over 120 s: **one distinct hash each**, FROZEN `af24e9c3` (rev 25) unchanged. So this revision
was stable long enough for a verdict to bind, which is the precondition the gate needs.

## What this does NOT claim

- No gate verdict (worker events cannot set gates); G-FORM remains `pending`.
- No semantic sufficiency judgement of the C0 statement, hypotheses, or physics.
- Not an accept of F2a/F1 (X3/X8 read F2a only to test mutual consistency).
- Independence is limited to authorship: worker-089 authored no canonical artifact.

## Re-run

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-089/f2b_xref_audit/check_f2b_xref.py \
  --controls --window 120 --interval 10 \
  --expect-sha256 1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508 \
  --out artifacts/worker-089/f2b_xref_audit/xref_report.json
```

## Next falsifier

Re-run at a newer canonical hash: any X-check flipping from pass to fail, or any mutant that stops
being caught, falsifies this report for the newer revision. A verdict at a hash that changes during
the stability window is void for gate purposes. Concretely: a reviewer who exhibits a `C0`/`C2`
composite reading in `conclusion_type`/conclusion text, an untagged same-class `anti_scope` entry, a
ledger ref whose `l1_status` disagrees with `ledger/theorems.jsonl`, a containment inversion, or a
canonical/authoring/FROZEN hash split at the audited revision, reopens the corresponding check.
