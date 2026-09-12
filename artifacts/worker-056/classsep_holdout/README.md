# W056-CLASSSEP-HOLDOUT-01 — independent holdout on the applied classsep fix

- worker: `worker-056` | node `A1` | gate `G-AUDIT` | class ids: four frozen classes
- pinned detector snapshot `a8c04fc31e4a` (`research_map/class_separation.py`), map snapshot `56478e3f1d19`
- pre-registration: `prereg_holdout_fixtures.json` sha256 `353096323b12` (written and hashed before the first detector invocation)
- drift: detector_moved=False, map_moved=False

## Method

29 pre-registered fixtures: 10 prose merge assertions (7 adversarial over-suppression probes where a
skip-list phrase lies inside the detector's +-60-char window), 10 explicit meta-audit/quotation
surfaces that must stay clean, 4 benign context controls, 5 declaration-mode R1/R3/R4 surfaces.
The canonical `runtime/bin/classsep_regression.py` was also run (worker-07 corpus) as the directive requires.

## Result

- genuine merge surfaces detected **7/14**, missed 7 (A03, A04, A05, A06, A07, A09, A10)
- meta-audit surfaces still flagged **4/10** (B01, B02, B03, B10)
- benign context controls flagged 0/4; declaration positives 4/4
- canonical regression runner exit 0 (output in `raw/`)
- live map findings on the pinned snapshot: 17 claim-statement hard findings; buckets {"candidate-genuine-assertion": 3, "candidate-residual-fp": 11, "skip-phrase-in-window-recheck": 3}
- worker verdict: **revise** (calibration evidence, not a gate verdict)

## Findings

**W056-CH-01 (major, over-suppression / missed genuine merges)** — 7/14 pre-registered genuine merge surfaces are missed by the applied fix: A03, A04, A05, A06, A07, A09, A10. Every miss has a skip-list phrase (false-positive / non-merge / detector finding / quoted detector / no-genuine-merge / not-a-merge) inside the detector's +-60-char context window while the sentence still asserts the merge, so the context-wide skip suppresses genuine assertions, not only meta-audit quotations.

**W056-CH-02 (major, residual meta-audit false positives)** — 4/10 explicit meta-audit / quotation fixtures are still flagged: B01, B02, B03, B10; these include the three residual probes worker-098 reported at this hash.

**W056-CH-03 (major, live residual findings)** — On the pinned map 56478e3f1d19 the detector emits 17 claim-statement hard findings; 11 contain meta/quotation markers in a +-160-char window and are candidates for the CF-16 metalinguistic-mention class, 0 have a skip phrase only outside the +-60 window, 3 fire although a skip phrase lies inside the +-60 window on at least one composite occurrence (claims with several composites; manual recheck), and 3 carry no meta marker (candidate genuine declarations). Rows with raw context are in the report.

## Falsifiers

- W056-CH-01: A re-run at the same detector hash in which any listed fixture emits a CLASSSEP finding, or a demonstration that the listed fixture is not a genuine merge assertion.
- W056-CH-02: A re-run at the same detector hash in which any listed fixture emits no CLASSSEP finding.
- W056-CH-03: Per-row adjudication showing a row's bucket label contradicts its quoted context.

## Non-claims

- Worker calibration evidence only: no gate verdict, no node status, no validation_status=passed, no promotion.
- No canonical artifact was edited; the detector and map were read and snapshotted only.
- Expectations are normative (the detector's own documented contract + the human-PI acceptance clause); a missed fixture is evidence of over-suppression, not a proof about any research claim.
- The evidence binds to the snapshot hashes above and is time-bounded; if the live detector moved (drift.detector_moved) it is void for the live file.
- The residual-live buckets are mechanical marker classifications for reviewer triage, not semantic adjudications.

## Rerun

```bash
python3 artifacts/worker-056/classsep_holdout/run_holdout_056.py
```
