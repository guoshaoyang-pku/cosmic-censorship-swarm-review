# Checkpoints — W060-CONTAINMENT-SEMANTICS-SWEEP-01

| # | at (+08:00) | state |
|---|---|---|
| 1 | 2026-09-12T00:41 | Recon complete: read HANDOFF.md, ASTRA_HANDOFF.md, PROTOCOL.md, map assignments/gates, worker-060 prior artifacts; confirmed FROZEN rev28 pins (F2b `55d0a1ea`, F2a `5476a3f2`, F0 `0abb9ed8`, supplement `d7419b4e`, FROZEN `2f358f67`). Task chosen: cross-artifact containment-semantics sweep + gate-sensitivity control. No assignment card in `comms/inbox/worker-060.jsonl`. |
| 2 | 2026-09-12T00:43 | `verify_containment_semantics.py` written; first run failed closed on a mis-pinned prose substring (correct behaviour); verifier corrected. |
| 3 | 2026-09-12T00:45 | Logic fixes after first full run: overlapping chain parse, entailment direction `E_target ⊆ E_source`, strength polarity, comparator resolution, dedupe. Run: 39 checks, 1 failed (the real defect), gate controls measured. |
| 4 | 2026-09-12T00:46 | Coverage recall probe folded in: 1495 strings scanned, 1 hit, 0 new, 0 unresolved. Final run: 40 checks, 1 failed; `evidence.json` sha256 `8f177b1e2fad0506…`. |
| 5 | 2026-09-12T00:47 | `REPORT.md`, this checkpoint file, `SHA256SUMS`, and `runtime/state/w060_containment_sweep_checkpoint_1.json` written; outbox events emitted; worker exits for recycling. |

No reviewed file was modified. Canonical hashes re-measured after every gate run; unchanged.
