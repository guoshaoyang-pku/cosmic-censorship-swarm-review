# Pinning note for W037-F2B-CONTAINMENT-ADJUDICATION-01

`report.json` sha256 `9aab08b35f818189b8f8870a3d296103e8e16523f2cef55eac77035b71be275f` is the
pinned measurement of this task at F2b `b2ab6acb2bbe` / FROZEN `815e08079aef` /
F0 `0abb9ed8a961`.

Re-running `check_f2b_containment.py` with its default `--json-out` **rewrites that pinned
file**. Only two fields are wall-clock-dependent — `created_at` and `runtime_seconds` — so a
re-run is measurement-identical but not byte-identical. To re-run without disturbing the pin:

```bash
python3 artifacts/worker-037/f2b_containment_adjudication/check_f2b_containment.py \
        --json-out artifacts/worker-037/f2b_containment_adjudication/report_rerun.json
```

or copy `report.json` aside first and diff ignoring those two fields.

This note exists because the first worker-037 slot on this board caught the same class of
self-inflicted moving-target defect (a regenerated `SHA256SUMS`) and the swarm's review
protocol treats a pin that moves under its own re-run as a defect, not a detail.

No canonical, owner or third-party file is written by the checker; all mutants are temp copies.
