# W098-GFORM-CORPUS-CAL-01 — independent calibration of the frozen G-FORM fixture corpus

Bounded task executed by `worker-098`. **Calibration evidence only**: no node completion,
no gate verdict, no theorem, no self-pass, and no rule or schema edits were made.

## Question

The frozen revision-28 formulation corpus landed at `artifacts/formulation/fixtures/`
(controls / negative / rephrased, written 2026-09-12T00:38:57–00:39:02+08:00) with **no
manifest and no recorded expected verdicts**. The G-FORM gate depends on that corpus
having been calibrated against the canonical structural gate. Does
`check_class_schema.py` (canonical, `000e09e46b2f`) actually sort those fixtures into the
classes the corpus design intends?

## Result

| group | n | intent | observed | outcome |
|---|---|---|---|---|
| canonical (F1, F2a, F2b) | 3 | pass | 3 pass | **PASS** |
| control | 6 | pass | 6 pass | **PASS** (0 falsely rejected) |
| negative | 31 | fail | 31 fail | **PASS** (0 uncaught; 20 distinct rule ids fired) |
| rephrased | 5 | fail | 2 fail, 3 pass | 2 legitimate exempt-field rewrites + **1 real escape** |

Run validity: `no_input_drift=true`, `all_live_canonical_pass=true`,
`all_controls_accepted=true`. All input hashes were taken **before** any stage ran and
re-verified byte-identical **after** the run.

### Finding CAL-01 — confirmed uncaught semantic escape (reported, not repaired)

`rephrased/p02_wcc_schema_scc_meaning` (AF-WCC-VAC-GEN, sha256
`f56bad14ed5a5b17656adb8b4468276fbd5bc45ef4f6e4e2a68d17b6c2041a1c`) changes **one leaf**:
`conclusion.statement_natural_language` is replaced by a bare SCC-style inextendibility
assertion ("…cannot be continued to a larger solution of the same equations") and drops
the WCC positive content entirely (complete future null infinity / no singularity visible
from I+).

- `conclusion.statement_natural_language` is **absent from `ASSERTIVE_PATHS`**, so the
  lexical leak scan never reads it.
- Detection in that field is therefore **negative-only** — it forbids SCC/FOREIGN tokens
  but never requires WCC's own conclusion family to be present. A conclusion asserting the
  wrong family in WCC-token-free prose is accepted.
- Falsifier: add `("conclusion","statement_natural_language")` to `ASSERTIVE_PATHS` **and**
  a WCC positive-content requirement; the fixture must then fail.

This belongs to the rule owner (formulation). It was not repaired here — the stop rule
forbids rule edits after seeing results.

### Finding CAL-02 — the two other uncaught rephrased fixtures are **not** escapes

`p01_scc_schema_wcc_meaning` and `p05_scc_i_plus_completeness_rephrased` change only
leaves under `anti_scope` / `class_boundary` / provenance / `authored_at`, which are
prescriptive-exempt namespaces by design (swapping sibling anti-scope rows across the
C0/C2 schemas is a legitimate rewrite). Accepting them is correct behaviour, not a
blind spot.

### Finding CAL-03 — misleading control name (hazard, no behavioural defect)

`control/null_scc_completeness_negated__AF-SCC-C2-VAC-GEN` is a **valid** document: it
negates completeness in `i_plus.definition` ("no completeness of I+ is asserted anywhere
in this class") and is correctly accepted. Its name reads as a reject-probe, and the
pre-registered intent in this run made exactly the error of assuming "negated ⇒ must
fail" — that mis-prediction is recorded in `report.json` (`controls.pre_registration_mispredictions`)
rather than silently corrected. Any downstream reader assuming the same will report a
false hard failure.

## Layout

| path | role |
|---|---|
| `manifest.json` | H1: every input hashed **before** any stage ran, plus the fixed intent rule |
| `run_calibration.py` | the runner (deterministic, no network, no repo mutation) |
| `tools/check_class_schema.py` | pinned byte-copy of the canonical gate (sha256 `000e09e46b2f`) |
| `rule_spec.json`, `KEY_MANIFEST.json` | pinned byte-copies of the gate's two data deps |
| `pinned/live/` | pinned byte-copies of the three frozen schemas under test |
| `pinned/corpus/` | byte-copy of the 42-fixture corpus at the review instant |
| `raw/` | H3: raw per-fixture stdout/stderr for all 45 runs |
| `raw_verdicts.jsonl` | one JSON line per run: exit code, verdict, failed rules, hashes |
| `report.json` | aggregates, findings, validity conditions |

## Reproduce

```bash
cd artifacts/worker-098/gform_corpus_calibration
python3 run_calibration.py          # rewrites manifest/report/raw; byte-identical inputs
```

The run is deterministic: it re-hashes its own inputs before and after and reports drift
if any input changed. If a pinned canonical file moves, re-run and re-pin — do not compare
a new run against these digests.
