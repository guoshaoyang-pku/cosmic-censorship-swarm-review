# W074-N0-CKPT-COVERAGE-PATCH-01 — independent verification of the numerics checkpoint-coverage patch

Bounded class-bound worker task · `worker-074` · 2026-09-12 · node **N0** · class
**AF-WCC-SCALAR-SPH** · gate **G-NUM** · read-only on every canonical path.

## Why this task

The numerics group lead filed blocker `lnum-blocker-4d80a7a99a8399844881` (01:07:41+0800):
`numerics/checkpoint.py` (sha256 `35955c3873fc…`, registered instrument, owner
`astra-lead-numerics`) tracks 19 paths, but four N0/G-NUM closure artifacts are invisible to
its churn detector, so the N0 closure landing was never reported as `changed`. The lead
proposed — and explicitly did **not** apply — extending `TRACKED` by those four paths,
pending controller authorization. No worker had independently verified that the proposal
does what it claims. This task does that, and measures the operational consequence of a
mid-run patch.

Closure paths the lead measured (`tracked_omits`):

1. `numerics/results/flat_wave_convergence_rev3.json`
2. `numerics/protocol/n0_fixed_dt_certification.json`
3. `numerics/protocol/n0_registration_drift_audit.json`
4. `numerics/N0_CLASS_BINDING_AUTHORITY.json`

## Method

Instrument: `verify_n0_ckpt_coverage.py` (stdlib only, deterministic, fail-closed exit 3).

1. **Pins** — 16 inputs (instrument, four-or-more checkpoint records, the coverage audit,
   the gap witness, the four closure artifacts, `numerics/gates.py`) re-hashed before and
   after; any drift aborts with no report.
2. **Historical gap reproduction** — parse the checkpoint records around each landing;
   require that each closure path's mtime falls in a window whose record's
   `changed_since_last_checkpoint` omits it and whose `artifact_hashes` lacks it.
3. **Sandbox replay** — copy `numerics/`, `artifacts/numerics/`, `research_map/` into
   `tmp/w074_n0_ckpt_coverage/sandbox/`, install three variants (`unpatched` = byte copy of
   the pinned module, `patched` = the four-entry extension, `wrong` = four `.bak` names) and
   call the module's **unmodified** `make_record(index, previous_hashes)` six times.
   `load_gate_state` is replaced at runtime by a fixed stub so hash-change detection is
   isolated from volatile gate/map traffic; the hashing code path (`TRACKED`, `sha256`,
   changed computation) is untouched. This substitution is disclosed in the report and in
   `selftest.json`.
4. **Descriptive residual census** — how many further `numerics/` paths cited in the
   accepted event stream stay untracked after the extension. Recorded as an observation
   with a non-claim, because the tracker is a curated churn detector, not a registry.

## Result (all 16 checks pass)

**Gap confirmed.** Four `(path, landing-window)` rows, one per closure path, e.g.
`flat_wave_convergence_rev3.json` landed 00:44:23 but `num-ckpt-20260912-004552` reported
`changed=['numerics/blockers.md']`; `n0_registration_drift_audit.json` (01:00:37) and
`N0_CLASS_BINDING_AUTHORITY.json` (01:00:07) both landed into the `-010105` window that
reported `changed=[]`.

**Proposal verified in sandbox.** The patched variant

- reports exactly the four paths after they mutate; unpatched reports none of them;
- keeps reporting an originally-tracked file change as the same singleton;
- stays silent on the untracked control `numerics/N0_REPORT.md`;
- is a strict, prefix-preserving superset (19 → 23 entries, nothing removed, no duplicates);
- the wrong-path `.bak` control does **not** detect the real mutations (path-specific).

**Operational consequence (F3).** Applying the patch mid-run makes the next checkpoint emit
a **one-time appearance delta** listing all four paths, because the previous checkpoint maps
lack those keys; the delta disappears on the following checkpoint. It does not retroactively
repair the historical blind window.

**Moving-target note (F4).** The blocker cites audit pin `a87c027135cf` (01:07:23); the
artifact was regenerated at 01:09:52 to `009f0375062a`, so that evidence ref no longer
resolves on disk. The substantive payload (`tracked_omits`, `tracked_count=19`,
`checkpoint_script_sha256`, `applied=false`) is identical across the regeneration. The
instrument's own pin guard caught this on first measurement and exited 3 — row preserved in
`raw/pin_failure_before_repin.json`.

## Files

| file | sha256 |
|---|---|
| `report.json` | see `SHA256SUMS` |
| `selftest.json` | see `SHA256SUMS` |
| `verify_n0_ckpt_coverage.py` | see `SHA256SUMS` |
| `raw/gap_reproduction.json` | record-level gap evidence |
| `raw/patch_replay.json` | six replay scenarios + minimality |
| `raw/residual_untracked_census.json` | descriptive observation (volatile event stream pinned at scan) |
| `raw/pin_failure_before_repin.json` | fail-closed event on the drifted audit pin |
| `raw/run_log.txt` | full run log |

`SHA256SUMS` covers every file above.

## Falsifier

Falsified if any of: (a) any pinned input no longer hashes to its pin; (b) the four paths are
shown tracked/visible in any named record's hash map or changed list; (c) the audit's
`tracked_omits` differs from the four paths; (d) the sandbox patched variant fails to report
exactly the four paths after their mutation, or reports any untracked path; (e) the patched
variant changes the report for any of the 19 originally tracked paths; (f) the previous
record maps already contain the four keys, so no appearance delta occurs; or (g) a re-run on
the same pinned inputs yields any check FAIL or a different extension/residual set.

## Non-claims

Not a gate verdict (G-NUM stays pending). Not a node status. Not `validation_status=passed`.
Not a numerics-lock release; N1 stays queued and no solver code was written or run. Does not
adjudicate the C8 protocol contest or the N0 order numbers. **The canonical instrument was
not edited** — the patch exists only as sandbox bytes and the textual diff in `report.json`;
authorization to apply it belongs to Astra (owner `astra-lead-numerics`). Worker events
cannot set gate verdicts or node status.

## Rerun

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-074/n0_ckpt_coverage_patch/verify_n0_ckpt_coverage.py   # exit 0 = all checks pass
```

Exit 3 means a pin moved or a control failed; re-pin live bytes before citing this report.
