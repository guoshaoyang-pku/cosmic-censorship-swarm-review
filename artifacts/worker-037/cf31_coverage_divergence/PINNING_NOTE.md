# Pinning note — W037-CF31-COVERAGE-DIVERGENCE-01

`report.json` is the **pinned snapshot** of this measurement
(`created_at 2026-09-12T01:22:19+08:00`, corpus digest `7ee4b9335e52…`).

Re-running `check_cf31_coverage.py` rewrites its default `--json-out report.json` and changes
`created_at`, `runtime_seconds`, and the mtime-derived fields. To re-verify without disturbing
the pinned bytes, run:

```bash
python3 check_cf31_coverage.py --json-out /tmp/w037_cf31_rerun.json
```

The review corpus is live. A re-run is expected to reproduce the pinned counts only while the
recorded file sha256 values in `binding_table` are unchanged; `corpus_sha256_t0/t1` and
`pin_stable` decide that. The binding evidence is the per-file sha256, never the filename.
