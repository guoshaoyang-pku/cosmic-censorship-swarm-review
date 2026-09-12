# Snapshot correction — W036-GATE-REPRO-01

The bounded round ran the scanner twice.  Two artifacts quote the **first** run's corpus
digest; the **final** report is authoritative.

| item | value |
|---|---|
| final report | `artifacts/worker-036/gaudit_accept_repro_report.json` sha256 `e16958ad8f67d81ca102073b688bf23719fe56802acc6dde5c412a7429cba6fe` |
| final report measured_at | 2026-09-12T00:28:52+08:00 |
| final corpus digest | `c6a973082ce1...` (79 files) |
| first-run corpus digest | `fe17a1feb767...` (76 files) |

Corrections:
- `README-W036-GATE-REPRO-01.md` v1 sha256 `b4c6ff33173ce094e9183cc4fd73412a12590aba80ea4e1f399ecdaa59c6e6a4` quoted the first-run digest and
  file count; v2 sha256 `c50d420804e3d9d8f06a2e979ef08ee08d88f14bdf26d02c798f5d7c8a596d3b` quotes the final values.  Nothing else changed.
- The task status event `w036-gaterepro-20260912T0031-status-01` also quotes the first-run
  digest `c6a973082ce1` is the corrected value; its "76 files" should read "79 files".
- `CHECKPOINT-W036-GATE-REPRO-01.json` sha256 `258193e9561d067e443fb83dc26f4c2af38f92452f416ec6582c4e90220add91` records the final report values and
  the README v1 hash `b4c6ff33173ce094e9183cc4fd73412a12590aba80ea4e1f399ecdaa59c6e6a4`; README v2 `c50d420804e3d9d8f06a2e979ef08ee08d88f14bdf26d02c798f5d7c8a596d3b` supersedes it.

All target hashes (F1 `9a8bd4c96800`, F2a `b6123750b37d`, F2b `1bb78ce9b357`, F0
`276009f4f63d`) and all findings are identical across the two runs; only the corpus digest
and file count moved as reviewers kept writing.
