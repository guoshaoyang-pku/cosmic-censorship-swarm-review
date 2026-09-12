# W094C close-findings binding-chain verification (worker-094)

Bounded class-bound task taken from the standing G-F0/G-FORM requirement after the
astra-life03-close-findings / astra-life03-repin-claims publication settled (last canonical
write 00:35:08; stable through 00:37:30).

- `check_closefind.py` — deterministic, read-only checker (31 checks). Re-runnable:
  `python3 artifacts/worker-094/closefind_verify/check_closefind.py --pinned artifacts/worker-094/closefind_verify/PINNED.json --out artifacts/worker-094/closefind_verify/report.json`
- `PINNED.json` — sha256 of the nine measured artifacts; a byte change makes the run report
  VOID_MOVING_TARGET instead of a verdict.
- `report.json` — full check output, hard failures, findings, prior-finding closure table.
- `pinned/` — byte copies of the nine artifacts as measured.
- `CHECKPOINT.json` — checkpoint record.

Result at the pinned bytes: **revise** — F0 rev5 content closes HF-094-F0-1/2/3 and
B-16F0-1/2/3; two gate-evidence bindings are stale:
HF-094C-1 (36/36 case rows still pinned to rev2 66bf917b) and HF-094C-2
(three schemas declare consistency evidence sha 675a99d0 vs measured 9e335e9b).

Worker verdict is advisory only; worker events cannot set node status or a gate verdict.
