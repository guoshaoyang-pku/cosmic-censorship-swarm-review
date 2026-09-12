# Audit-detector recalibration — 2026-09-11 recheck (worker-16)

Supersedes `RESULTS.md` for the current detector revision only. The earlier report remains
valid for `research_map/audit_evidence.py` sha256 `c4769b99ab706146…`; this one pins
**sha256 `6873cb5124318a9d6ed97…`** (the revision that added `research_map/class_separation.py`,
the `CLASSSEP:` message family, and the `frozen_artifacts` drift check).

- Report: `calibration_report.recheck2.json` (sha256 `b0d8552f0836d4c4fa53…`)
- Expectations: `expected.json` (sha256 `a03e2190b864ca3e741a…`); harness `run_calibration.py`
  (sha256 `b1f3a25fd95881361dd7…`)
- Corpus: 11 scored fixtures + the live map as informational.
- Result: **TP=5, TN=3, FP=1, FN=2**; exit 1.

## Delta against the first calibration (`c4769b99`: FP=0, FN=3, TP=2, TN=5)

Fixed in `6873cb51` (verified by the corpus):

| fixture | before | now |
|---|---|---|
| `fx3_unknown_class_id` | FN | caught (`unknown class token` + `label family … disagrees`) |
| `fx4_merged_class_id` | caught | caught (message reworded to `single class token merges C0 and C2`) |
| `fx8_merged_artifact_text` | caught | caught (`composite C0/C2 asserted as one class`) |
| `fx9_frozen_artifact_drift` | check absent | caught (new) |
| `fx10_frozen_artifact_missing` | check absent | caught (new) |
| live map `class_separation` coverage | 0/10 nodes had `class_id` | inputs present; 6 soft unknown-token signals |

Still open:

| id | kind | evidence | required change |
|---|---|---|---|
| R2-1 | **FN** | `fx2`: `audit_evidence.py:97` is still a bare `pass` for a non-`pass` required gate under `numerics_lock`. A `verdict: fail` on `G-FORM`/`G-AUDIT` produces no signal; only `locked_nodes` is enforced. | emit at least a soft signal `required gate <id>: verdict=<v> while numerics locked`; hard if a failed gate is a launch blocker (ASTRA_HANDOFF decision 2). |
| R2-2 | **FN** | `fx7`: label `do not split: C0 or C2 regularity` declares a merged regularity but is exempted because `class_separation._scan_composite` treats the token `split` as benign without checking that it is negated. | apply the negation check to the `_SPLIT`/`_PROHIBIT` exemptions, or flag the `not split` pattern explicitly. |
| R2-3 | **FP** | `fx6`: a `statement` field describing a verification task ("Verify that no source silently upgrades the regularity from C0 or C2…") is hard-flagged as a bare composite in declaration mode. | scan `statement`/prose fields in prose mode, or extend `_PROHIBIT` to cover "verify that no … upgrades …". |

Informational live-map signals (not calibration failures): six `CLASSSEP-SOFT: unknown class
token` from `ledger/theorems.jsonl` for `AF-WCC-VAC-BH-FORM` and `AF-WCC-VAC-NS-CONSTR`. These are
either legitimate sub-class labels needing taxonomy registration or ledger strings that should not
look like frozen class ids — a lead-formulation/lead-literature reconciliation input.

## Reproduce

```bash
python3 artifacts/worker-16/audit_calibration/run_calibration.py \
  --out artifacts/worker-16/audit_calibration/calibration_report.recheck2.json
# calibration: 3/12 fixtures MISMATCH | totals {'tp': 5, 'tn': 3, 'fp': 1, 'fn': 2}
```

## Falsifiers

- R2-1 falsified if Astra's map-applier escalates non-`pass` required gates elsewhere; check
  `research_map/events.jsonl` for a `gate` event with `verdict: fail`.
- R2-2 falsified if the label is shown to be a legitimate split declaration despite `do not`.
- R2-3 falsified if the project decides that any node field containing a bare composite is
  reportable regardless of context; then the fixture expectation moves to `hard: [text-merge]` and
  the defect becomes a documentation question, not a detector bug.

No node completion claimed; `validation_status=unverified`.
