# W023-L0-HF02-LEDGER-01 — byte-exact HF-02 repaired-ledger candidate + runner measurement

`worker-023`, bounded lifecycle, **read-only on canonical artifacts**.
Worker-level product: `applied=false`, no node status, no gate verdict, no
`validation_status=passed`.

## Question

The HF-02 blocker at L0 now has three verified pieces: the 8-row adjudication
(`l0_hf02/`), the P-CODE + P-DATA composition matrix (`hf02_compose/`), and the
end-to-end runner-wiring integration (`l0_hf02_integration/`). What was still
missing was the **candidate bytes themselves**: a ledger a lead could apply.
This task closes that gap:

> At the pinned ledger, does applying the adjudicated ops produce a ledger that
> is byte-identical to the original outside the affected rows, keeps a binding
> channel on every patched row, drives the rubric-literal HF-02 count 8 → 1 → 0
> (V7 → V8), and drives the **093-patched, wired runner** to exactly the same
> counts while the **canonical runner stays blind**?

## Two variants (one op is conditional)

The prior adjudication conditions the `T-526` rebinding on an F1 membership
ruling. The candidate is therefore built in two shapes:

| variant | ops | rows changed | HF-02 after | sha256 |
|---|---|---:|---:|---|
| `proposed_ledger_v7.jsonl` | 7 unqualified ops; `T-526` untouched | 7 | 1 | `d66d06f8b20c` |
| `proposed_ledger_v8.jsonl` | all 8 ops incl. `T-526` | 8 | 0 | `33f6f8817239` |

V7 requires no new ruling; V8 requires the F1 ruling for `T-526`.

## Pinned inputs (fail closed; builder exits 2 if any moved)

| input | sha256 |
|---|---|
| `ledger/theorems.jsonl` | `a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28` |
| `evaluation_rubric.yaml` | `d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885` |
| `artifacts/audit/audit_lib.py` | `ae573db84631b970caeea46e8821aee8af66166f6a5f16251e4a6c819a377c8c` |
| `artifacts/audit/audit_run.py` | `3b27dd3fef7f41488158099f888e3685dc8d9cca9f0507ad46c4d01f9bd2c411` |
| `artifacts/worker-093/.../proposed_hf02_disjunction_patch.diff` | `0247a5c93acc0e015d09cf4dcec8c643696d4328b748c871857fb82cc9b4669a` |
| `artifacts/worker-093/.../patched_audit_lib.py` (declared post-patch) | `9c8def1b50379e7cb5b6414cdf73c31e891276b2cf1bf8635a25aad7b4b1de8e` |

## Method

`build_repair_023.py` rebuilds only the affected JSON-lines with the ledger's
own writer convention (`json.dumps(..., ensure_ascii=False, sort_keys=True)`,
roundtrip-verified byte-exact on **all 62 rows** before any edit), then builds
six frozen sandboxes under `tmp/w023_hf02_ledger_repair/` (canonical and
093-patched tooling × original / V7 / V8) from a trimmed map (`groups=[]`) and
runs the real runner in each with `--scan ledger --quiet --kind findings
--fail-on-critical`. The patched sandboxes apply the 093 diff (dry run + real,
result hash must equal the declared patched bytes) and insert the one missing
wiring line from `l0_hf02_integration/runner_wiring.diff`.

`verify_repair_023.py` re-derives everything independently: its own parser,
its own HF-02 predicate written from the rubric sentence, its own row/field
diff, re-execution of all six scenarios, and two mutation controls (reintroduce
a dual-class row into V8; patched runner must fire exactly once, canonical
runner must stay blind).

## Results

| scenario | exit | violations | HF-02 disjunction rows | derived G-AUDIT |
|---|---:|---:|---|---|
| canonical × original | 0 | 0 | none | pending |
| canonical × V7 | 0 | 0 | none | pending |
| canonical × V8 | 0 | 0 | none | pending |
| patched × original | 2 | 8 | all 8 expected ids | fail |
| patched × V7 | 2 | 1 | `T-526` | fail |
| patched × V8 | 0 | 0 | none | pending |

*The sandbox map is trimmed, so absolute gate verdicts are not interpretable;
the variant-to-variant delta is.* Reruns are digest-identical; the
patch-attributable delta is 8 added / 0 removed (original), 7 removed / 0 added
(V7), 8 removed / 0 added (V8), and every removed violation is an HF-02
disjunction entry. No non-HF-02 violation changes in any variant.

Checks **39/39**, controls **9/9** (build); independent verification **38/38**.

## Findings

- **F1 (candidate bytes ready).** Both shapes are byte-exact: unchanged rows are
  byte-identical, diffs are confined to `class_ids` / `informs_classes` /
  `ledger_tags`, ids and row order are preserved, and every patched row keeps a
  binding channel (`class_ids` or `informs_classes` non-empty).
- **F2 (`T-526` conditional).** V7 clears 7 of 8 and is unqualified; V8 clears
  all 8 but lands the `T-526` op that the adjudication packet defers to the F1
  membership ruling.
- **F3 (landing still needs authority).** P-CODE (`audit_lib.py`) is still at
  `ae573db84631` and unlanded; landing V8 without P-CODE + wiring leaves the
  canonical audit blind to the repair, and landing P-CODE without a ledger
  repair flips derived `G-AUDIT` to fail. The repair bytes and the code change
  must land as one change; that decision is the controller/leads'.
- **F4 (scope dependency).** If the A0 detector-scope ruling is that HF-02 is
  claim-scoped (worker-077 reading), the ledger repair is not required and this
  artifact is a reference proposal, not a fix.
- **F5 (canonical blindness reproduced).** The canonical runner reports 0
  disjunctions on original, V7 and V8 with an identical violation digest.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-023/hf02_ledger_repair/build_repair_023.py
python3 artifacts/worker-023/hf02_ledger_repair/verify_repair_023.py
```

Exit 0 pass; 2 a pinned input moved (verdict void); 3 a check failed.

## Falsifier

Re-run at the same pins. Falsified if any pinned hash differs (void); V7/V8 do
not differ from the original on exactly the expected rows/fields; any unchanged
line is not byte-identical; any patched row loses both binding channels; the
rubric-literal HF-02 count is not 8/1/0; the patched runner does not report
exactly 8/1/0 disjunction rows or the canonical runner reports any; a non-HF-02
violation changes; or any check/control fails.

## Scope and overlap

- No canonical file written; the workspaces `ledger/`, `artifacts/audit/` and
  `evaluation_rubric.yaml` are hash-checked before and after.
- Overlap: worker-093 (patch + isolation test), worker-036/077/080 (detector
  scope/coverage), previous worker-023 packets (adjudication, composition,
  integration). This artifact adds the candidate bytes and their end-to-end
  runner measurement; it does not re-adjudicate any row.
