# W065-GFORM-PINBIND-RECHECK-05 — per-class declared-pin binding recheck (F1 / F2a / F2b, G-FORM)

Bounded class-bound worker task. No inbox card existed for `worker-065` at launch
(checked `comms/inbox/`, 2026-09-12T01:18+08:00); the task was self-selected from the
G-FORM unmet row "FROZEN/per-file pin binding" and continues worker-065's
`W065-CANON-SIDEPIN-CENSUS-04` line at a later window.

Classes: `AF-WCC-VAC-GEN` (F1), `AF-SCC-C2-VAC-GEN` (F2a), `AF-SCC-C0-VAC-GEN` (F2b);
gate `G-FORM`. **Worker evidence only: this sets no node status, no
`validation_status=passed`, and no gate verdict; it edits no canonical path.**

## Question

Every declared hash side-pin on a canonical path is where a re-binding reviewer or
tool can be sent to superseded bytes. Census-04 measured 96 such pins and found 8
gate-relevant stale ones. This recheck asks, at the current G-FORM r3 verification
window:

1. Does every declared pin that resolves to a G-FORM class schema equal the live bytes?
2. Did the 8 gate-relevant defects repair after census-04?
3. Which landed reviews declare a currently-stale advertised hash instead of the live
   class bytes?

## Method (declared, fail-closed)

* **Instrument is not re-implemented.** `pinned/check_sidepins.pinned.py` is a
  byte-identical copy of the census-04 checker, sha256
  `88b19be6d9a7761b281f34dc3b8b162efe42ab6951f790e62ff962788eb47d43`; the driver
  re-verifies that hash, plus the census-04 report/shadow/control pins, before
  measuring and fails closed otherwise.
* **Window.** 12 canonical paths (`3 class schemas`, F2b sidecar, aggregator,
  `entry_hashes.json`, `FROZEN.json`, and the census-04 instrument/checkpoint files)
  are hashed before and after all work. Any move ⇒ `UNSTABLE`, measurement void.
* **Live run** is executed twice; the two JSON outputs must be byte-identical.
* **Per-class rollup** collects every declared pin whose resolved target is that class
  schema, plus the FROZEN rev29 pin and (for SCC) the aggregator component pin, and
  emits one verdict per class: `PIN_BOUND` or `PIN_HAZARD`.
* **Controls** (fresh, under `controls/`): C1 census-04 repair shadow (hash-verified
  copy) ⇒ rc 0; C2 F1 entry pin reverted to stale `9a8bd4c9` ⇒ STALE detected; C3 F2b
  sidecar reverted to stale `1bb78ce9` ⇒ STALE detected; C4 shadow reserialised with
  identical pin values (byte change only) ⇒ rc 0, no format false positive; C5
  aggregator C0 component pin reverted ⇒ STALE detected.
* **Citation census** scans string values of every top-level `reviews/*.json`, binds
  the snapshot by a digest over sorted `(path, sha256)`, and buckets each record per
  class: live-only / stale-advertised-only / both / other-hashes-only / no 64-hex.
  It is a declared-hash census, not a verdict on reviewer independence or merit.

## Result — `PIN_HAZARD` for all three classes, window `STABLE`, controls 5/5

Live checker: **rc 2**, 96 pins, counts `OK_FROZEN_AND_LIVE 56 / OK_LIVE 26 /
MOVING_TARGET_EXEMPT 1 / STALE 13`, **8 gate-relevant defects**. The defect set is
**identical to census-04** (by source/target/advertised/live identity): no pin was
repaired between the two windows, and none is new.

| class | live schema sha256 | FROZEN rev29 pin | aggregator pin | declared pins | stale declared | verdict |
|---|---|---|---|---|---|---|
| `AF-WCC-VAC-GEN` (F1) | `d9cebb9404b2…` | match | — | 3 | 1 (`entry_hashes.json`: `9a8bd4c9…`) | `PIN_HAZARD` |
| `AF-SCC-C2-VAC-GEN` (F2a) | `e9a27996dfd3…` | match | match | 4 | 1 (`entry_hashes.json`: `b6123750…`) | `PIN_HAZARD` |
| `AF-SCC-C0-VAC-GEN` (F2b) | `b2ab6acb2bbe…` | match | match | 5 | 2 (`entry_hashes.json` and the F2b sidecar: `1bb78ce9…`) | `PIN_HAZARD` |

The split matters: **the frozen-manifest and aggregator layers bind live bytes for all
three classes; the failure is in the registry layer** (`entry_hashes.json` for all
three, plus `schemas/af_scc_c0_vacuum.yaml.sha256` for F2b). The other four
gate-relevant stale pins are the F0/mirror taxonomy entry, the `FROZEN.json` entry, and
two `artifacts/flash-04/f1_ambiguity/BUNDLE.sha256` pins; five further stale pins are
advisory (including the recorded `DRIFT_CONTESTED` detector pin).

### Citation exposure at the review snapshot (229 records, digest `42eeb6c0f3a3…`)

| class | stale-advertised-only | live-only | both | other hashes | no 64-hex |
|---|---:|---:|---:|---:|---:|
| `AF-WCC-VAC-GEN` | 22 | 22 | 0 | 176 | 8 |
| `AF-SCC-C2-VAC-GEN` | 10 | 17 | 1 | 192 | 8 |
| `AF-SCC-C0-VAC-GEN` | 16 | 22 | 4 | 179 | 8 |

Read as exposure, not error: a review in the stale-advertised-only bucket declares a
hash that a currently-stale registry pin advertises (e.g. F1 `9a8bd4c9…`), so a
re-binding reader following that registry reaches superseded bytes. The census does not
claim those reviews are wrong or that their authors followed the sidecar; a review may
also cite a historical revision for legitimate comparison (that lands in
"other hashes"). The review set moved by one file during the task; the digest pins the
exact 229-record snapshot.

## Findings

* **F-065-PB-1** The 8 gate-relevant stale declared pins persist unchanged since
  census-04 at the r3 window; no repair landed by 01:19.
* **F-065-PB-2** All three G-FORM classes are `PIN_HAZARD` on declared registry pins
  while their FROZEN rev29 and aggregator pins match live bytes — the per-file pin
  binding gap is registry-local, not manifest-local.
* **F-065-PB-3** The F2b sidecar trap recorded at
  `W087-GFORM-INDEP-05` is still live and still advertises the superseded `1bb78ce9…`.
* **F-065-PB-4** Citation exposure to the stale advertised hashes is non-zero and
  class-specific at the snapshot digest above (table).

## Falsifier

Falsified if (a) any pin this recheck calls STALE is shown to resolve correctly under a
declared resolution rule (FROZEN `path_policy` redirect or a documented alias); or
(b) any of the 12 window-pinned paths moved between the pre and post readings (window
`UNSTABLE`, measurement void at the newer revision); or (c) a declared pin called STALE
is shown byte-equal to its target under any declared resolution rule; or (d) re-running
the pinned checker at the recorded window does not reproduce the reported defect set.

## Reproduce

```bash
python3 artifacts/worker-065/gform_pinbind_recheck/recheck.py --stamp 2026-09-12T01:19:16+08:00
```

Deterministic: the instrument is pinned by hash, the live run is executed twice with
byte-identical JSON, and the report records every window pin. Canonical writes: none
(reads only; control shadows are copies under `controls/`).

## Non-claims

* Not a gate verdict, node status, or `validation_status`; not a review of any class
  schema's mathematical content.
* Not a reviewer-independence or verdict-merit judgement; not a claim that any named
  reviewer made an error.
* The repair shadow in `shadow/base` is an artifact-local candidate refresh (inherited
  from census-04); it is **not applied** to any canonical registry.
