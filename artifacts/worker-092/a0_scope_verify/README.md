# W092-A0-SCOPE-INDEP-01 — independent verification of the A0 detector-scope adjudication

- **Target**: `evaluation/A0_detector_scope_adjudication.json#a26be4b85706`
  (author `astra-lead-audit`, `astra-life05-a0-detector-scope`, gate `G-AUDIT`, node `A0`, class `GLOBAL`)
- **Rubric pin**: `evaluation_rubric.yaml#d748a9e3574e`
- **Worker**: `worker-092` (non-author; no inbox card existed, task self-selected from the live queue)
- **Verdict**: **accept (scope-limited)**, 0 hard failures, score 4.5
- **Instrument**: `verify_a0_scope.py` — own JSONL reader, own HF-14/HF-03 predicates, own scope
  classifier; imports no author code; pins all inputs and re-measures at exit; exit 0/1/2/3 = pass /
  hard failure / moving target / missing input.
- **Report**: `report.json#ec377515e823` (see `manifest.json` for the exact digest at emission)

## What was verified (card falsifier: "a scope change that hides a live-artifact hit; an
exclusion list that includes any canonical ledger or build input")

| check | result |
|---|---|
| C1 artifact + rubric pins | match (`a26be4b85706`, `d748a9e3574e`) |
| C2 all 27 declared `file_pins` re-measured | 27/27 resolve to the declared sha256 and re-classify to the declared class |
| C3 HF-14 per-file counts re-derived (12 files) | 586/586 exact, every file |
| C4 HF-03 per-file counts re-derived (15 files) | 218/218 exact, every file |
| C5 artifact assertions I1–I5 re-derived | I1/I2/I3/I4/I5 all reconcile; totals 586 = 0 kept + 574 excluded + 12 staging, 218 = 194 + 17 + 7 |
| C6 live-tree scope scan (`artifacts`, `comms/outbox`, `ledger`) | 1768 files classified excluded, **0 live-class paths excluded**, `ledger/**` never excluded, staging surfaced |
| C7 pre-registered controls | 9/9 as expected, incl. the live-under-`snapshot/` precedence hazard control |
| C8 excluded files are not live inputs | none is byte-identical to a canonical ledger file; none is referenced by `MANIFEST.json`, `registry.jsonl` or `literature/tools/*` |
| C9 canonical ledger cleanliness | `ledger/theorems.jsonl#a1674f094979`, 62 records, **0 HF-14 hits** independently |
| C10 detector corroboration | `a0_detector_scope.py#f13de2967ac7` defines `excluded` and evaluates live classes before historical/snapshot |
| C11 drift re-pin at exit | artifact, rubric and all 27 file pins unmoved |

Conclusion: the split ruling is reproduced. HF-14's 586 pre-scope hits are all in
historical/snapshot/staging paths; the canonical ledger is clean; HF-03's 194 post-scope hits are
on live build inputs and a live emitted product, so the scope change does **not** clear HF-03.
The scope predicate hides no live-artifact hit at the pinned bytes.

## Findings (no hard failure)

- **F-092-A0S-01 (info, wording)** — `recommendation.exact_predicate` states the exclusion test but
  not its precedence over `must_keep`. The author's classifier is live-first (corroborated) and no
  live path currently matches the literal exclusion, so nothing is hidden now; a naive adopter
  could drop a future `artifacts/literature/sources/**/snapshot/**` file. Minimal repair: append
  "evaluated after the must_keep classes (live classes win)". Falsifier: a live build input under an
  exclusion-matching segment that the adopted filter drops.
- **F-092-A0S-02 (info, detector breadth)** — the shared HF-14 predicate omits the rubric's literal
  "and no artifact hash" exemption: independently 586 hits under the shared reading (matches the
  artifact) vs 558 under the literal rubric reading, differing only in
  `artifacts/worker-007/l0_hf01_artifact_refs/proposed/theorems.with_artifact_refs.jsonl`
  (60 vs 32). Conservative for this artifact: that file is excluded under either reading and the
  live after-scope count stays 0. Falsifier: a non-excluded file where the two readings change the
  scope verdict.
- **F-092-A0S-03 (info)** — `ledger/citation_audit.csv` is taxonomy-canonical but the corpus scan
  reads only `.json`/`.jsonl`, so it can contribute no HF-03 hit; nominal, not a defect.
- **F-092-A0S-04 (process)** — the only prior verdict on this artifact is its author's own
  (`counts_as_independent_second_verdict=false`). This review is the missing non-author verdict; not
  a defect of the artifact.

## Authority and non-claims

Worker measurement + one independent review verdict. It sets no gate verdict, no node status and no
`validation_status`; it does not re-adjudicate the HF-03 live finding, the required repair, or the
whole-corpus snapshot counts (corpus growth is expected and is not drift; only the 27 declared file
pins are re-measured). G-AUDIT remains `pending`.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-092/a0_scope_verify/verify_a0_scope.py; echo $?
```
