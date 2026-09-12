# proposed/ — worker-16 candidate detector copies (NOT live)

Runnable copies of `research_map/audit_evidence.py` and `research_map/class_separation.py` with the
three staged fixes described in `../CANDIDATE-PATCH.md`. They exist so the calibration harness can
prove the fixes green without editing shared files:

```bash
python3 ../run_calibration.py --detector-dir . --out ../calibration_report.proposed.json
```

Apply `../detector_fixes.patch` to `research_map/` only through the detector owner.
