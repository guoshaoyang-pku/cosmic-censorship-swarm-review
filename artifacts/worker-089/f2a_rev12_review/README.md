# W089-F2A-REV12-REVIEW-03 — independent review of F2a (AF-SCC-C2-VAC-GEN) rev12

**Verdict: accept (4.0) for class content at the FROZEN rev28 pin.**
This is worker-level evidence, **not** a gate verdict and not a node completion.

## Why this task

The audit lead's closing verification (`reviews/G-FORM-final-verify.json`, 00:35:21) found
`B-GFORM-1`: no class has two independent verdicts at the rev27/28 frozen hashes — F1 had one
(revise), **F2a and F2b had zero**. worker-034's F2a machine verification binds the superseded
rev11 hash `b6123750`, so it is void for the freeze. This task supplies the missing independent
F2a verdict at the frozen hash.

## Target

| | |
|---|---|
| class | `AF-SCC-C2-VAC-GEN` (node F2a, gate G-FORM) |
| canonical | `schemas/af_scc_c2_vacuum.yaml` |
| sha256 | `5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce` (revision 12) |
| authoring twin | `artifacts/formulation/schemas/af_scc_c2_vacuum.yaml` — byte-identical |
| frozen pin | `artifacts/formulation/FROZEN.json` rev28, `2f358f6722d9…`, frozen_at 00:35:08 (not future) |
| stability | 90 s window, 7 samples: **no drift** in the target, FROZEN, both taxonomies, F1 or F2b |

## Result — 15/15 checks pass, 10/10 planted defects caught

| check | what it establishes | result |
|---|---|---|
| C01 | no duplicate top-level YAML keys | pass |
| C02 | `revised_at` is wall-clock (≤ now, consistent with mtime) | pass |
| C03 | revision bumped to 12, history consistent | pass |
| C04 | `class_contract_pointer` → canonical taxonomy `classes.AF-SCC-C2-VAC-GEN`, resolves | pass |
| C05 | supplement pointer is a separate field resolving in the authoring tree | pass |
| C06 | declared F0 hash == measured canonical taxonomy hash | pass |
| C07 | FROZEN pins this sha on both paths, mirror equal | pass |
| C08 | identity exactly AF/SCC/VAC/GEN + C2, no stray class token | pass |
| C09 | D0 well-typed; byte-identical across F1/F2a/F2b (**closes HF-034-F2A-1**) | pass |
| C10 | extension predicate frozen: C2 / classical_ricci / future, clauses (a)–(f) | pass |
| C11 | no C0/C2 merge; conclusion typed `scc_c2_future_inextendibility` | pass |
| C12 | no WCC/I+ content leaks into the SCC conclusion | pass |
| C13 | genericity block: comeager, constraint-manifold topology, variants not classes | pass |
| C14 | falsifier block bound to this class | pass |
| C15 | licensed C0⇒C2 transfer precondition holds at the shared frozen data class (**closes HF-034-F2A-2 context**) | pass |

Controls M1–M10 each plant one defect (duplicate key, future timestamp, authoring pointer, dangling
fragment, corrupted F0 hash, merge-shaped class id, ill-typed D0, WCC conclusion, widened
conclusion type, deleted C0⇒C2 entailment) and **all ten are caught**; the unmutated baseline
passes every check (no false positive).

## Recorded observation (excluded from the accept's scope)

`OBS-089-1`: the schema's inline `f0_binding.consistency_evidence_sha256` (`675a99d0…`) no longer
resolves — the live evidence file measures `9e335e9b…`, the value FROZEN rev28 pins. The class
bytes are unaffected and the declared F0 taxonomy hash still matches, but the inline pointer is
stale. This is independently recorded as **HF-086-R1** (`reviews/G-FORM-rev12-binding-086.json`);
it is not re-litigated or waived here.

## Re-run

```bash
cd artifacts/worker-089/f2a_rev12_review
python3 check_f2a_rev12.py --window 90 --interval 15
# writes f2a_review_report.json (+ pinned snapshots, controls/)
```

## Falsifier

Any of C01–C15 fails at a newer canonical hash, or the FROZEN pin/mirror equality breaks, or a
planted control stops being caught → this accept is void for the newer revision. The 90 s
stability window showed no drift, so the verdict binds `5476a3f2c6bc…` only.
