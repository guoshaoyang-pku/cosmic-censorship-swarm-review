# Snapshot correction v2 — W036-GATE-REPRO-01 (supersedes v1 `fe65e0cdf8ed`)

The scanner ran twice; the **final** report is authoritative.  v1's second bullet was
inaccurate about which value the status event quoted; this v2 states the record exactly.

## Authoritative snapshot
- final report `artifacts/worker-036/gaudit_accept_repro_report.json` sha256 `e16958ad8f67d81ca102073b688bf23719fe56802acc6dde5c412a7429cba6fe`
- `measured_at` 2026-09-12T00:28:52+08:00, corpus digest `c6a973082ce1...`, **79 files**
- run-1 (superseded, report overwritten) corpus digest `fe17a1feb767...`, 76 files
- target hashes unchanged across both runs: F1 `9a8bd4c96800`, F2a `b6123750b37d`,
  F2b `1bb78ce9b357`, F0 `276009f4f63d`; all 10 findings identical.

## Exact corrections
1. `README-W036-GATE-REPRO-01.md` v1 sha256 `b4c6ff33173ce094e9183cc4fd73412a12590aba80ea4e1f399ecdaa59c6e6a4`
   quoted the **run-1** snapshot (`fe17a1feb767`, 76 files).  v2 sha256 `c50d420804e3d9d8f06a2e979ef08ee08d88f14bdf26d02c798f5d7c8a596d3b`
   quotes the **final** snapshot (`c6a973082ce1`, 79 files).  No other change.
2. Status event `w036-gaterepro-20260912T0031-status-01` quotes the **final** digest
   `c6a973082ce1` but the stale file count "76 files"; the corrected count is **79 files**.
3. `CHECKPOINT-W036-GATE-REPRO-01.json` sha256 `258193e9561d067e443fb83dc26f4c2af38f92452f416ec6582c4e90220add91` already records the final snapshot
   values (digest `c6a973082ce1`, 79 files).  Its `artifacts.readme` entry `c50d420804e3`
   is superseded by README v2 `c50d420804e3d9d8f06a2e979ef08ee08d88f14bdf26d02c798f5d7c8a596d3b`.
4. Correction v1 sha256 `fe65e0cdf8edaa2f882555d69ac15425b9609ca554c28faaf91e10c6a4ba99a8` is superseded by this v2: v1's README and checkpoint
   statements are correct, its status-event bullet is not.

## Falsifier
Re-run the scanner and re-hash: falsified if the final report's corpus digest is not
`c6a973082ce1` at 79 files, or if README v2's quoted values differ from the final report.
