# worker-046 / F2a live-pin transfer (rev13)

Bounded task executed 2026-09-12 ~01:19 +08:00. It is the `next_falsifier` pre-registered in
`reviews/F2a-review-rev27-a.json`, run against the live byte-state.

Class-bound: node `F2a`, class `AF-SCC-C2-VAC-GEN`, gate `G-FORM`.
Parent assignments: `audit-r2-F2a-a`, `audit-r2-F2a-bindchain-worker-046`.

## Measured byte-state

| path | sha256 |
|---|---|
| schemas/af_scc_c2_vacuum.yaml (rev13) | e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe |
| schemas/af_scc_c0_vacuum.yaml (rev13) | b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c |
| schemas/af_scc_regularities.yaml (rev7) | 27255e5b34f36b252accf1217dc01b63a5f5ec09f33af03938565c8fb99b20ed |
| artifacts/formulation/FROZEN.json (rev29) | 815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0 |
| artifacts/formulation/KEY_MANIFEST.json | 014e2d3019781632cdb78ace266cf08cc11f9cf8b8ef0a049beb74eb9c6b6b9a |

`evidence/pre_hashes.txt` and `evidence/post_hashes.txt` are identical (no input mutation).

## Commands (reproduce)

```bash
python3 artifacts/formulation/tools/check_class_schema.py --json schemas/af_scc_c2_vacuum.yaml
python3 artifacts/formulation/tools/check_class_schema.py --json schemas/af_scc_c0_vacuum.yaml
python3 artifacts/formulation/tools/check_taxonomy_consistency.py
python3 artifacts/worker18/f2_review/check_aggregator_pins.py
python3 artifacts/worker-046/f2a_live_repin_rev13/d0_instantiation_check_live.py
# rev27-manifest rerun (historical skew record):
python3 artifacts/worker-046/f2a_live_repin_rev13/toolchain/formulation/tools/check_class_schema.py \
        --json schemas/af_scc_c2_vacuum.yaml
```

## Result

Verdict `revise`, score 3.0, `counts_as_gate_verdict=false`.
`HF-046-F2a-01` and `HF-046-F2a-02` dissolved at the live pin; `F-046-F2a-01/02/03/04/05` survive
(`F-046b-01/02/04/05/06`); `F-046-F2a-06` resolved, replaced by the freeze-coverage residual
`F-046b-03`. Outputs:

- review: `reviews/F2a-review-live-rev13-worker-046.json`
- event: `comms/outbox/worker-046.jsonl` (`w046-f2a-live-rev13-repin-review-20260912T011942`)
- checkpoint: `runtime/state/worker-046_F2a_live_repin_checkpoint.json`
