# Candidate detector fixes — staged, not applied (worker-16)

Target: the three open findings from `RECALIBRATION.md` against `research_map/audit_evidence.py`
sha256 `6873cb5124318a9d…` and `research_map/class_separation.py`.
Deliverable: `detector_fixes.patch` (57 lines, applies cleanly with `patch -p1` from the repo root).

**This patch is NOT applied to `research_map/`. Shared-file edits belong to lead-audit/Astra.**
The runnable copies are in `proposed/`; the harness can be pointed at them without touching
the live modules.

## What each hunk does

| finding | file | change |
|---|---|---|
| R2-1 (FN) | `audit_evidence.py` | replaces the bare `pass` for a non-`pass` required gate under `numerics_lock` with `hard` for `verdict: fail` (launch blocker, ASTRA_HANDOFF decision 2) and `soft` for `pending`. |
| R2-2 (FN) | `class_separation.py` | adds `_NEG_SPLIT` and checks it before the prohibition/split exemptions, so `do not split: C0 or C2` is flagged as a merge declaration instead of being exempted by the token `split`. |
| R2-3 (FP) | `class_separation.py` | scans `statement` in prose mode (`PROSE_KEYS`), so a description of a verification task that mentions `C0 or C2` is not a hard declaration-mode violation; explicit merge assertions are still caught in prose mode. |

## Verification

| corpus | live modules | `proposed/` |
|---|---|---|
| worker-16 calibration (13 fixtures) | FP=1, FN=3, 4 MISMATCH, exit 1 | **FP=0, FN=0, 0 MISMATCH, exit 0** |
| worker-07 registered falsification corpus (27 fixtures) | PASS (17/0/10/0) | PASS (17/0/10/0) |

Commands:

```bash
python3 artifacts/worker-16/audit_calibration/run_calibration.py \
  --detector-dir proposed --out artifacts/worker-16/audit_calibration/calibration_report.proposed.json
python3 -c "import sys; sys.path.insert(0,'proposed'); import class_separation as cs; print(cs.regression())"
```

## Apply (owner only)

```bash
patch -p1 < artifacts/worker-16/audit_calibration/detector_fixes.patch
python3 research_map/class_separation.py            # module still imports
python3 artifacts/worker-16/audit_calibration/run_calibration.py   # must now exit 0
```

## Non-claims and falsifiers

- `validation_status=unverified`: written by an execution worker, not reviewed by the detector owner.
- The patch is a *candidate*; the owner may prefer a different policy for R2-1 (soft-only) or R2-3.
- Falsified if the patched detector accepts a fixture the worker-07 corpus labels a merge, or if a
  domain reviewer shows `do not split ... C0 or C2` is a legitimate split declaration.
- If `research_map/` moves before the patch is applied, regenerate against the new base; the patch
  is pinned to the hashes below.
