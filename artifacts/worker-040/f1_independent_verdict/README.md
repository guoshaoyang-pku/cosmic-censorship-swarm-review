# worker-040 / W040-F1-INDEP-VERDICT-02

Independent, class-bound verification of the canonical F1 schema
`schemas/af_wcc_vacuum.yaml` (class **AF-WCC-VAC-GEN**, node F1, gate G-FORM) at
sha256 `9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503`
(revision 11, mtime 2026-09-12T00:19:14+08:00).

**Verdict: revise — score 3.0** (not a gate verdict; one independent verdict).

## Why this task

No assignment card exists in `comms/inbox/worker-040.jsonl`. The 00:24:40 lifecycle
scan records G-FORM F1 at `9a8bd4c96800` with exactly one distinct accept and every
other F1 verdict revise/inconclusive, and the F1 publication pair is aligned, so the
target is stable and binding. The contested flash-19 HF-06 "critical" defect had no
independent adjudication; this review supplies one (and refutes it).

## Result

| check | result |
|---|---|
| C1 structure (required blocks, class components) | pass |
| C2 class binding (WCC conclusion, no SCC leakage, exclusions) | pass |
| C3 canonical instruments (check_class_schema, taxonomy consistency, variant registry, verify_frozen, classsep regression, map validator) | pass |
| C4 contract pointer resolves in canonical F0 tree | **fail** (HF-040-01) |
| C5 duplicate revision keys / non-future effective timestamp | **fail** (HF-040-02) |
| C6 normative symbol `AF_{I+}` defined | **fail** (HF-040-03) |
| C7 HF-06 adjudication (whole-curve vs tail single-q) | pass — HF-06 **refuted** |
| C8 reader divergence from the textual split | soft (no semantic divergence) |
| C9 f0_binding declared == measured canonical F0 | pass |
| C10 entry/exit drift guard over 8 tracked files | 0 drift |

The C7 machine check enumerates all 241 strict partial orders on 2–4 elements, every
chain and every q: **0** whole-vs-tail divergences. The teeth control (arbitrary,
non-past-closed J) finds **26** divergences, and past-closed J finds **0** — the
harness can see a genuine difference, and past-closure is exactly what makes the
schema's two phrasings equivalent. The true SET-vs-single-q distinction needs the open
end of the geodesic and is checked symbolically (SET: witness `j=i`; single-q: refuted
by `i=j+1`; tail: refuted by `i=max(j,k)+1`).

## Files

| file | sha256 |
|---|---|
| `verdict.json` (main artifact) | `908572cde86087962d5f2c8ca5d6e4b6bc84d4b96690e6dd96b3a650c3532e60` |
| `checks.json` (machine results) | `974ce00648d80b7b04e4c837bfdddcdc86a69cb810ff632b3b35cb2a42518b8d` |
| `instrument_runs.json` (canonical tool runs) | `74ca408b9678b45dbe9caeea92b51a52d6ceabc2579a6f5a4641813830863b48` |
| `run_checks.py` (reproducer) | `1fbdd1909ab73e033162414a83fddc231b0b73b4c71e101d8addbd11eccc45a3` |
| `entry_hashes.json` / `exit_hashes.json` | `87a6ab0d695e…` / see file |
| `../../reviews/F1-review-040.json` (review record) | `86e447fa09be1fda7ddb6afdd1f5c6ea9d26bd9197414eb802aa4d9302e3cbde` |

Reproduce:

```bash
cd <repo root>
python3 artifacts/worker-040/f1_independent_verdict/run_checks.py
```

## Falsifier

The verdict is falsified by (a) bytes at the same hash in which the pointer resolves
against the canonical F0 tree, `revised_at` occurs once with a non-future value, and
`AF_{I+}` has a definitional leaf; (b) a causal geodesic γ, q ∈ I+, t0 with
γ([t0,T)) ⊆ J⁻(q) ∩ M but γ ⊄ J⁻(q) ∩ M (reinstating HF-06); or (c) a canonical F1
hash other than `9a8bd4c96800` at gate-verdict time (voids, not refutes).

## Authority

Worker event only. No shared file was modified. This cannot set a node done, a
validation status passed, or a gate verdict; the controller and group leads decide
with artifact + review evidence.
