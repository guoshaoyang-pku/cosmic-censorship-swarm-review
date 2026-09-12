# W042-REVIEW-CORPUS-MUTATION-09 — review corpus is mutable under fixed filenames

**Class** AF-WCC-VAC-GEN (class_ids all four frozen classes) · **Node** A1 · **Gate** G-AUDIT
(related G-FORM, G-LIT) · **Actor** worker-042 · **No assignment card existed** in
`comms/inbox/worker-042.jsonl`, so this is a self-selected bounded task continuing
`W042-GATE-SCAN-GAP-02` (stream-vs-scan coverage). It does **not** adjudicate the F2b coverage
count; REC-39 assigns that to `astra-life05-verify-gform-r3`.

## Question

Between two byte-exact pins of `reviews/`, did review files change under fixed filenames, and
did any verdict change at the same reviewed-artifact hash? Does the F2b rev13 coverage set differ
between the pins? This is the mutability half of CF-31 ("review files are mutable under fixed
names") that a single-time-point binding table cannot recover.

## Pins

| pin | when | substrate | sha256 |
|---|---|---|---|
| T0 | 2026-09-12T00:26:27+08:00 | worker-042 `gate_scan_gap` snapshot, 72 files byte-copied with per-file hashes | manifest `4ee0145df14c` |
| T1 | 2026-09-12T01:19:28+08:00 | this task's freeze-first pin, 235 files byte-copied with per-file hashes | manifest `97d51342a2c0` |

T1 also pins map `a2585ffc2152`, events `b5fda1d88afb`, artifact-hashes `b692ad728c50`.
T0 self-check: 72/72 files re-hash to the T0 manifest; T1 self-check: 235/235 (control C10).

## Headline

- **5 of 72** T0-pinned review files were rewritten in place before T1; 4 carry verdict/binding
  fields.
- **One same-pin verdict flip:** `F2b-review-07.json` accept(4.0) → revise(3.0) at the *same*
  reviewed artifact hash `1bb78ce9b357`, with a `correction_note`; T0 `created_at` 00:24, T1 00:32.
- **One rebind verdict change:** `L0-review-worker-006.json` revise(2.5)@`ce42d205e761` →
  accept(4.0)@`3e3d35531421` — legitimate re-review of a moved object, not a same-pin flip.
- **F2b rev13 coverage drift:** 0 files bound to `b2ab6acb2bbe` at T0; 15 at T1 (3 accept, 12
  non-accept). Of CF-31's four named files (worker-052/071/072/090), three are accept and
  `F2b-review-worker-072-rev29.json` is **revise** at the same pin. A polarity-blind count of
  hash-bound full-schema verdicts reads 4; a `verdict==accept` count reads 3. Both numbers are
  reproducible from the same pinned corpus; REC-39 decides which is correct.
- **Namespace growth:** 72 → 235 files (158 new, 142 verdict-bearing) in 53 minutes; 4 further
  review files appeared in the ~3 minutes after the T1 pin.
- **Name reuse:** 4 mutated filenames changed document identity (target/node/created_at/event_id),
  e.g. `L1-spotcheck-10.json` was a different document (old batch spotcheck) at T0.

## Findings (each carries its own falsifier in `report.json`)

| id | kind | one-line |
|---|---|---|
| W042-RCM-01 | defect-governance | 5/72 fixed-name files rewritten; field deltas enumerated |
| W042-RCM-02 | defect-high | same-pin accept→revise flip at `F2b-review-07.json` |
| W042-RCM-03 | reconciliation input | F2b rev13 polarity split (3 accept / 4 polarity-blind) measured at both pins |
| W042-RCM-04 | defect-governance | fixed filenames reused across review rounds (identity tuples differ) |
| W042-RCM-05 | coverage-scope | corpus grew 72→235; filename-keyed scans compare different corpora |
| W042-RCM-06 | observation | 1 review file + 3 registry/stream files moved inside the run window |

## Interpretation limits

- Measurements rest on the **snapshot copies**, not live files; later traffic cannot change them.
- `hash_stale`-style reasoning does not apply: a mutation here is a byte change at a fixed path,
  not a claim that the earlier verdict was false when written.
- The report states counts and polarity; it does **not** rule which coverage count is correct,
  does not set `done`/`passed`, and issues no gate verdict.
- `F2b-review-rev13-052.json` lacks `counts_as_full_schema_verdict` and `created_at`; rows with a
  missing flag are counted as full (flag is not `False`). `F2b-review-worker-072-rev29.json` is
  named "rev29" but its `reviewed_sha256` is the rev13 pin `b2ab6acb2bbe`.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-042/review_corpus_mutation/pin_snapshot.py
python3 artifacts/worker-042/review_corpus_mutation/audit_review_mutation.py   # 10/10 controls, exit 0
```

Deterministic payload `0ebb401de987…` is byte-stable across runs; only the live-drift observation
(W042-RCM-06) and `generated_at` differ. Checker `0be787e5db5e`, pin tool `50d523437077`, report
`dcae75271f7b`, T1 manifest `97d51342a2c0`.
