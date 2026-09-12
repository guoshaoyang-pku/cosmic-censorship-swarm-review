# W036-GFORM-R3-BIND-01 — G-FORM rev29 accept-coverage census (F1 / F2a / F2b)

- **Worker:** worker-036 (bounded execution worker; one task, then exit)
- **Nodes / classes:** F1 `AF-WCC-VAC-GEN`, F2a `AF-SCC-C2-VAC-GEN`, F2b `AF-SCC-C0-VAC-GEN`
- **Gate of record:** G-FORM (context only — this artifact issues **no gate verdict**, sets no
  node status and no `validation_status`)
- **Taken with no inbox card** (`comms/inbox/worker-036.jsonl` does not exist), because the live
  G-FORM blocker is per-class review coverage and the F2b count had been moving all hour.
- **Evidence:** `report.json` (validity 7/7), `census_gform_binding.py`, `pinned/` (byte copies
  of all 192 review files in the snapshot + `MANIFEST.json`).

## Question taken

At the live FROZEN rev29 pins, does the controller's recorded G-FORM coverage
(`research_map.json → controller_gate_audit`, checked_at **2026-09-12T01:12:39+08:00**) reproduce
against `reviews/*.json`, which review files actually bind each class, and is every binding
accept's evidence chain (FROZEN pin, `path#sha256` refs) still on disk?

## Method (deterministic, stdlib only)

- `census_gform_binding.py` re-implements the controller's exact review-coverage rule
  (`research_map/astra_lifecycle.py:176-214`: verdict vocabulary, target aliases, four explicit
  pin keys + nested pins, 12-hex prefix matching either way, `counts_as_full_schema_verdict`
  defaults to full, reviewer falls back to `actor`), and cross-checks the result against the
  earlier independent worker-036 implementation
  (`artifacts/worker-036/gaudit_accept_repro_audit.py`) on byte-identical copies.
- The whole corpus is read **once** into memory; every classification binds to that snapshot.
  The snapshot is byte-pinned under `pinned/` so the report survives corpus movement.
- An inclusive census classifies *every* review file that mentions a G-FORM token, including
  accepts whose pin is superseded (against a precise registry of canonical-path hashes mined
  from `research_map/events.jsonl`) versus accepts that bind the live hash.
- For each binding accept: blind flag, full/scoped flag, hard-failure count, FROZEN rev29
  citation, and resolution of every `path#hex` evidence ref against disk (`match`/`stale`/`missing`).
- `--selftest` (12 assertions) covers current/superseded/scoped/unpinned/nested-pin/alias cases.
- Fails closed on canonical-schema or FROZEN pin drift inside the run (exit 2); the run reported
  `pins_stable_within_run` and `snapshot_stable`.

## Result

**F1 and F2a reproduce exactly; F2b does not — one recorded reviewer withdrew inside the window.**

| target | pin | recorded @01:12:39 | fresh @01:17:00 | reproduces |
|---|---|---|---|---|
| F1 | `d9cebb9404b2` | 4 `[052, 072, 075, 085]` | 4 `[052, 072, 075, 085]` | yes |
| F2a | `e9a27996dfd3` | 2 `[017, 072]` | 2 `[017, 072]` | yes |
| F2b | `b2ab6acb2bbe` | 4 `[052, 071, 072, 090]` | **3** `[052, 071, 090]` | **no — worker-072 withdrawn** |

F2b now meets the ≥2-distinct-accept count criterion on the fresh scan (3 full accepts, all
three citing FROZEN rev29), but the recorded count is not re-derivable from the paths:
`reviews/F2b-review-worker-072-rev29.json` was rewritten **in place** at 01:14:54 from
`accept` (score 4.0) to `revise` (score 3.0) with two **blocking** hard failures — the same two
defects (line 152 containment denial, line 246 inverted size premise) that
`artifacts/worker-036/f2b_containment_adjudication/` had confirmed. The accept-bearing bytes are
not preserved anywhere under `reviews/`.

Context on the hour's trajectory (durable refs): the pass-06 controller records F2b at **0**
accepts (`research_map/ASTRA_HANDOFF.md#bd2c2eeaf11d`,
`runtime/state/controller_verification/astra-lifecycle-06-decisions.json#62d47cc64349`, REC-23);
the map at 01:12:39 records **4**; the fresh snapshot has **3**. The count is a moving surface,
which is why this census binds every claim to file hashes and a snapshot digest rather than to
paths.

### Binding full accepts in the snapshot (9)

| class | file | reviewer | blind | score | FROZEN rev29 cited | refs |
|---|---|---|---|---|---|---|
| F1 | `F1-review-rev13-052.json` | worker-052 | true | 4.0 | yes | all match |
| F1 | `F1-review-rev13-085.json` | worker-085 | n/a | 4.0 | **no** | all match |
| F1 | `F1-review-rev29-075.json` | worker-075 | n/a | 4.0 | yes | all match |
| F1 | `F1-review-worker-072-rev13.json` | worker-072 | n/a | 4.5 | yes | all match |
| F2a | `F2a-review-worker-017.json` | worker-017 | n/a | 4.0 | **no** (pins pre-move `3d9e3d77`) | **2 stale** |
| F2a | `F2a-review-worker-072-rev13.json` | worker-072 | n/a | 4.5 | **no** | all match |
| F2b | `F2b-rev13-full-090.json` | worker-090 | **false** (self-disclosed) | 4.0 | yes | all match |
| F2b | `F2b-review-rev13-052.json` | worker-052 | true | 4.0 | yes | all match |
| F2b | `F2b-review-rev13-worker-071.json` | worker-071 | n/a | 4 | yes | (no refs) |

`n/a` = field absent; the controller rule does not require blindness, but the audit lead's
`astra-life05-verify-gform-r3` acceptance does require non-author independence per class, so the
flag is recorded for that adjudication.

## Findings (7)

1. **W036-BIND-F2b (major)** — recorded F2b coverage stale: 4 recorded vs 3 fresh; `worker-072`
   no longer binding.
2. **W036-BIND-CHURN-worker-072-F2b (major)** — the recorded accept's bytes no longer exist at
   the path (same filename, `accept` → `revise`, sha `5db91bb0781d`, mtime 01:14:54); the
   recorded count cannot be re-derived from the path alone. Any future count must cite review
   file hashes, not filenames.
3. **W036-BIND-FROZEN-worker-085 (minor)** — F1 accept binds `d9cebb9404b2` but does not pin
   FROZEN rev29 `815e08079aef` (CF-27 requires the FROZEN bytes plus each per-file pin).
4. **W036-BIND-FROZEN-worker-017 (minor)** — F2a accept does not cite FROZEN rev29.
5. **W036-BIND-EVID-worker-017 (minor)** — F2a accept has 2 stale evidence refs:
   `artifacts/formulation/FROZEN.json#3d9e3d77fd87` → current `815e08079aef`, and
   `artifacts/formulation/VARIANT_REGISTRY.json#5eb42f9a384a` → current `6bac9adea19e`. It pins
   the **pre-move bytes of the same revision number (29)**, the exact CF-27 hazard.
6. **W036-BIND-FROZEN-worker-072 (minor)** — F2a accept binds `e9a27996dfd3` but does not pin
   FROZEN rev29 (its own text notes FROZEN was still rev28 when written).
7. **W036-BIND-BLIND-worker-090 (minor)** — F2b full accept declares `blind=false` with a
   self-disclosure; eligibility is the audit lead's call, recorded here, not adjudicated.

## Authority and limits

Worker measurement only. This artifact does not edit canonical files, does not write the map or
`runtime/state/artifact_hashes.json`, and issues no gate verdict or node status. A count is not a
pass: F2b carries live blocking findings (worker-072 revise HF-01/HF-02, worker-018 and worker-053
revises, and `artifacts/worker-036/f2b_containment_adjudication/` D1/D2), so "3 binding accepts"
must be read only as coverage, with merits and eligibility adjudicated by the audit lead. The
census binds to the snapshot digest and to `pinned/MANIFEST.json`; later writes to `reviews/` are
outside its scope.

## Falsifier

Re-run `census_gform_binding.py` at the pinned hashes. The claim is **falsified** if (a) any file
listed as a binding full accept no longer passes the controller rule (verdict ≠ accept, target
alias unresolved, `counts_as_full_schema_verdict: false`, or pin not matching the canonical
12-hex prefix), (b) any full accept bound to a G-FORM canonical hash in the snapshot is absent
from `fresh_coverage.full_accepts`, (c) any pinned file's sha256 differs from
`pinned/MANIFEST.json`, or (d) FROZEN/canonical pins move (void, not falsified).

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-036/gform_r3_binding_census/census_gform_binding.py \
    --stamp 2026-09-12T01:17:00+08:00          # byte-identical report on a static corpus
python3 artifacts/worker-036/gform_r3_binding_census/census_gform_binding.py --selftest
```

## Pins

| input | sha256 |
|---|---|
| `schemas/af_wcc_vacuum.yaml` (F1, canonical = mirror) | `d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d` |
| `schemas/af_scc_c2_vacuum.yaml` (F2a, canonical = mirror) | `e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe` |
| `schemas/af_scc_c0_vacuum.yaml` (F2b, canonical = mirror) | `b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c` |
| `artifacts/formulation/FROZEN.json` (rev29) | `815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0` |
| `research_map/research_map.json` at census | see `report.json → pins.map.sha256` |
| review corpus snapshot digest | see `report.json → corpus.snapshot_digest` |
