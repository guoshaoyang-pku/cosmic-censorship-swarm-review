# worker-060 checkpoints — W060-F2B-VERDICT-01

| # | at | node/class | reviewed sha256 | verdict | evidence |
|---|---|---|---|---|---|
| 1 | 2026-09-12T00:22:20+08:00 | F2b / AF-SCC-C0-VAC-GEN | `1bb78ce9b357…355508` | PASS (0 failed checks) | `evidence.json` sha256 `524c0f59a8bb3efa…366549`; snapshot `snapshots/af_scc_c0_vacuum.1bb78ce9b357.yaml` |

Checkpoint files: `runtime/state/w060_checkpoint_1.json`, `runtime/state/w060_checkpoints.jsonl`.

Hash-stability note: the canonical F2b file was republished during the window
(`a2aef5ac` map-measured 00:17:46 → `962f33c6` 00:19:05 → `1bb78ce9` from 00:19:47, stable through
00:22:14). All verdicts are pinned to `1bb78ce9`; they do not transfer to any other hash.

Authority note: worker evidence only. No gate verdict, no node completion, no `validation_status`
promotion. Not one of the two named independent reviewer accepts required by G-FORM.
