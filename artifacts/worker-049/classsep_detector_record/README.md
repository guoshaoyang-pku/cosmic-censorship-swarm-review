# W049-CLASSSEP-DETECTOR-RECORD-05 — recorded-copy reconstructability census

**Verdict: `ALL_THREE_RECONSTRUCTABLE_BYTE_EXACT` — the stop rule of
`astra-classsep-stabilize-0118` is NOT triggered for any candidate.**

Read-only, pre-registered, fail-closed census of every `class_separation*.py` file on disk,
run to answer the first acceptance clause of the stabilization assignment: *"reconstruct and
hash c266dbec, a8c04fc3, and e36b0d64 candidates from recorded copies"*, and its stop rule:
*"if no candidate can be reconstructed byte-exactly, record unresolved detector contest and
keep G-AUDIT pending."*

Node **A1**, gate **G-AUDIT**, classes **AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN**.
Worker evidence only: this packet does **not** name a detector-of-record, does not adopt,
does not touch `frozen_artifacts`, and claims no gate verdict.

## Result

| candidate | label | byte-exact copies | pre-freeze copies (mtime < 23:30:20) | earliest copy | distinct worker dirs |
|---|---|---:|---:|---|---:|
| `c266dbceca87…83a920` | active frozen pin | **79** | **20** | **2026-09-11T23:30:10** — 10 s *before* `frozen_at` | 6 |
| `a8c04fc31e4a…53c5bd` | adjudicated APPLIED / live | **27** | 0 | 2026-09-12T00:52:00 | many |
| `e36b0d644ca7…b86eed` | voided CF-29 write | **7** | 0 (all inside the 01:06:12–01:08:14 drift window) | 2026-09-12T01:06:12 | 7 (6 third-party + controller evidence) |

Full enumeration: **157** `class_separation*.py` files. Exactness distribution:
c266 79, a8c04fc3 27, void-write 7, staged candidate `e2d24b92` 9, staged prosefix `dc8aa0de` 3,
other worker-local variants 32. Exit code **0**, controls **7/7**.

## The decision-relevant provenance asymmetry

All three candidates are byte-exactly recoverable, so the stop rule does not fire. What
differs is the *quality* of the earliest recorded copies:

1. **`c266dbec` (active pin) is the only candidate with pre-freeze, non-author copies.**
   20 copies predate the 23:30:20 freeze. The earliest, at 23:30:10, are in
   `artifacts/worker-024/classsep_runner_vacuity/…` and `artifacts/worker-093/classsep_metagrowth/pinned/…`
   — captured by workers who did not author the detector and before the pin existed. This is
   the strongest recorded-copy provenance of the three.
2. **`a8c04fc3` has no pre-freeze copy.** Its earliest recorded copy is 00:52:00, which is
   exactly where worker-017's drift timeline starts the "unrecorded drift (REC-22)". There is
   therefore no disk evidence that these bytes were the frozen-era instrument; its status
   rests on the REC-22 ruling, not on a contemporaneous capture.
3. **`e36b0d64` exists only inside the drift window.** Six independent workers captured it
   between 01:06:12 and 01:08:14, plus the controller's preserved evidence copy. Those are
   contemporaneous captures of a revision that was never authorized; they cannot serve as a
   pin (consistent with CF-29 voiding), but they do prove the void revision is reconstructable.

Counts are not independence: many copies are sandbox mirrors of a handful of capture events.
The `copies` column is file count; the `distinct worker dirs` column is the independence proxy.

## What this packet does NOT establish

- Not an adoption, not a detector-of-record, not a ranking by semantics. Hashes only.
- It does not re-run the 27-fixture regression or the meta-audit corpus; the assignment's own
  falsifier ("the 27-fixture regression / meta-audit corpus changes under the chosen hash")
  remains the lead's post-choice check.
- Byte-exactness of a copy says nothing about whether that copy *was ever live*.

## Controls and exit codes

7/7 controls pass: C1 positive enumeration, C2 truncation negative, C3 live-pin, C4 map-pin,
C5 no-`.pyc`/no-`__pycache__` rule, C-determinism (two in-process census passes byte-identical),
C6 immutability (live detector and preserved evidence re-hash unchanged across the run).
Exit codes: 0 pass · 2 pin mismatch · 3 nondeterministic · 4 immutability violation · 5 harness error.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-049/classsep_detector_record/run_detector_record_049.py   # exit 0 expected
```

## Deliverables (sha256)

| artifact | sha256 |
|---|---|
| `pre_registration.json` (written before the recorded run) | `0dc6ed0e2835782be3add503aadb68ef976893ded5e454bc3630f854c19f2c5b` |
| `run_detector_record_049.py` (self-hashed by the run) | `c39f5110c47ff68e2040574ee1aa71ac4a38d41a7d4751ba0a8ced2bc85bcace` |
| `results.json` | `a2c410f242393e7f76a99dd6da486c4f359a2c1a2080bb9e9dab939b096a2efc` |
| `CHECKPOINT.json` | see `runtime/state/w049_detector_record_checkpoint.json` |

## Falsifier

Re-run the runner at the pins: any fixed-input mismatch (exit 2), a nondeterministic double
census (exit 3), an immutability violation (exit 4), a candidate reported
`BYTE_EXACT_COPIES_PRESENT` whose only "copies" are not byte-identical, a candidate reported
`NO_BYTE_EXACT_COPY` while any enumerated file digests to it, or a census row outside the
pre-registered enumeration rule falsifies this packet.
