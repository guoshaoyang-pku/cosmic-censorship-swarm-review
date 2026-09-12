# W083-REF01-REV29-DISPOSITION-01 — disposition of W083-REF-01 at FROZEN rev29

| field | value |
|---|---|
| task | W083-REF01-REV29-DISPOSITION-01 (self-selected; no inbox card existed for slot 083) |
| actor | worker-083 |
| class_ids | AF-WCC-VAC-GEN; AF-SCC-C2-VAC-GEN; AF-SCC-C0-VAC-GEN |
| node_id | F0,F1,F2a,F2b |
| gate | G-FORM (measurement only — no gate verdict, no node status) |
| bound generation | FROZEN rev29 `artifacts/formulation/FROZEN.json#815e08079aef` (revision 29, frozen_at 2026-09-12T00:57:26+08:00) |
| instrument | `check_ref01_rev29_disposition.py#93e66673af35` (stdlib-only, read-only, deterministic) |
| result | **PASS_REF01_DISPOSITION** — 8/8 hard checks, 7/7 controls, 0 pin drift |
| canonical digest | `5da99ec3678c5347c6d5c44b9cf8bfd241f323c37fc3db9df7d03a36c2871ccc` |
| prior record | `artifacts/worker-083/rev12_evidence_fixpoint/REPORT.md` (00:44, task W083-REV12-CLOSURE-EVIDENCE-FIXPOINT-01) |

## 1. Result

The defect first reported as W083-REF-01 is **still live at FROZEN rev29 and is neither
repaired nor superseded** by the rev29 evidence-binding repair. Re-measured at the live pins:

| # | declared entry (path in the report) | declared | FROZEN rev29 pin | live bytes | class |
|---|---|---|---|---|---|
| 1 | `research_map/formulation_taxonomy.yaml` | `0abb9ed8a961` | `0abb9ed8a961` | `0abb9ed8a961` | **CURRENT** |
| 2 | `artifacts/formulation/evidence/taxonomy_consistency.json` | `f3c119a8825d` | `9e335e9ba1bf` | `9e335e9ba1bf` | **STALE_DECLARED** |
| 3 | `schemas/af_wcc_vacuum.yaml` | `b474fbc49cdd` | `d9cebb9404b2` | `d9cebb9404b2` | **STALE_DECLARED** |
| 4 | `artifacts/formulation/schemas/af_wcc_vacuum.yaml` | `b474fbc49cdd` | `d9cebb9404b2` | `d9cebb9404b2` | **STALE_DECLARED** |
| 5 | `schemas/af_scc_c2_vacuum.yaml` | `a7ccae4d5dec` | `e9a27996dfd3` | `e9a27996dfd3` | **STALE_DECLARED** |
| 6 | `artifacts/formulation/schemas/af_scc_c2_vacuum.yaml` | `a7ccae4d5dec` | `e9a27996dfd3` | `e9a27996dfd3` | **STALE_DECLARED** |
| 7 | `schemas/af_scc_c0_vacuum.yaml` | `b71ec02c601d` | `b2ab6acb2bbe` | `b2ab6acb2bbe` | **STALE_DECLARED** |
| 8 | `artifacts/formulation/schemas/af_scc_c0_vacuum.yaml` | `b71ec02c601d` | `b2ab6acb2bbe` | `b2ab6acb2bbe` | **STALE_DECLARED** |

Rule applied: `CURRENT` = declared equals live bytes and the FROZEN rev29 pin;
`STALE_DECLARED` = declared matches neither live bytes nor the pin and no byte copy exists in the
scan set. The single `CURRENT` entry is the declared F0 taxonomy, which the rev27 closure apply did
not rewrite; it is current by coincidence of lineage, not by repair (the report's own `phase: apply`
block claims it `changed: true`, revision 5 — and that part happens to hold).

Separately, **freeze integrity is intact**: for all 8 declared paths the live bytes equal the
FROZEN rev29 pin, the report bytes equal their pin (`dab1d49b9985`), both the manifest and the
report strict-parse with no duplicate keys, and no bound input moved during the run (drift = []).
The defect is in the report's *declared-hash block*, not in the current freeze.

## 2. Reproducibility probe on the pinned closure procedure

`python3 artifacts/formulation/tools/close_findings_rev27.py --dry-run` (tool pinned at
`0234cd3cbda4`, unchanged since 00:31:31):

```
exit 1
ASSERT FAIL [F0 scalar-sph conclusion]: expected 1 occurrence(s), found 0
```

All 12 guarded paths (the 8 declared entries + report + tool + FROZEN + gate_test_report) were
content-hashed before and after: **0 changed** (control C5). The closure record is therefore not
reproducible from its own pinned (report, tool, bytes) triple at rev29; the pinned procedure fails
closed on a pattern that no longer exists in the live supplement.

## 3. Recoverability of the four intermediate generations

Content-hash scan of the repository (root minus `.git`/`tmp`/`node_modules`/`__pycache__`/`.cache`/
`.dsh`; 42 files >4 MB skipped):

- **31,028 files / 763,212,311 bytes scanned; 0 copies** of `b474fbc4`, `a7ccae4d`,
  `b71ec02c`, `f3c119a8` (hard check E7).
- `runtime/state/artifact_hashes.json` contains none of the four values (obs: `registry_hits` = []).

The four values survive **only as citations**, not as bytes:

| intermediate | citing files (excluding the report itself and this task's own output) |
|---|---|
| `b474fbc4` | `reviews/F1-rev12-closure-090.json`, `reviews/F2a-review-034.json`, `reviews/F2a-review-034-repin.json`, `reviews/G-FORM-final-verify.json`, + 7 `runtime/state` checkpoint files |
| `b71ec02c` | `reviews/F2a-review-034.json`, `reviews/F2a-review-034-repin.json`, `reviews/G-FORM-final-verify.json`, + 6 `runtime/state` checkpoint files |
| `a7ccae4d` | `reviews/F2a-review-034.json`, `reviews/G-FORM-final-verify.json`, + 4 `runtime/state` checkpoint files |
| `f3c119a8` | `reviews/F1-review-rev27-a.json`, + 2 `runtime/state` checkpoint files |

None of those citing files is named in the live map's gate `evidence_refs`
(`citing_files_in_live_map_gate_refs` = []), so the dangling citations are not load-bearing for the
gate record itself.

## 4. Which binding is operative, and what the gate record actually cites

At the same snapshot the G-FORM gate record names:

- `artifacts/formulation/evidence/close_findings_rev27_report.json` — **path only, unhashed**; content
  is the stale block above;
- `reviews/closefind-verify-094.json#0abb9ed8a961` — hash-bound to the *F0 taxonomy*, not to the
  report or to the schemas.

The artifact that actually carries the live byte binding is
`artifacts/formulation/evidence/gate_test_report.json#26540a6b43cc` (bytes equal the FROZEN rev29
pin): its `canonical_sha256` map declares all three rev13 schema hashes
`d9cebb9404b2` / `e9a27996dfd3` / `b2ab6acb2bbe` (hard check E6). At the measured snapshot that
file was **not** named in the live gate `evidence_refs` (observation
`gate_test_report_named_in_live_gate_refs` = false; the map is a moving target and this reads a
timestamped snapshot, `map_sha256 = a2585ffc2152`).

## 5. Consequence (no verdict claimed)

A G-FORM r3 reviewer may not cite the rev27 closure table's schema or consistency hashes as evidence
of the rev13/rev29 bytes: 7 of its 8 declared values resolve to nothing, and the procedure that
wrote it fails closed at the same bytes. The rev13/rev29 byte state is instead carried by
`gate_test_report.json#26540a6b` (three live schema hashes) and by the rev29 repair evidence
(`evidence_binding_repair_rev29_report.json`, `lead_independent_verify_rev29.json`). This report
sets no gate verdict, node status or `validation_status`.

## 6. Measures-only remedy options (deliberately NOT applied)

- **R1 (preferred, owner):** emit a rev30 closure receipt at the live bytes that re-declares the
  eight paths against the current pins, leaving the rev27 report in place as historical provenance;
  FROZEN then needs a revision bump that pins the new receipt. Owner/controller authority required.
- **R2 (controller):** record a finding that the rev27 report's declared-hash block is
  historical/void for rev13+ and pin `gate_test_report.json#26540a6b` into the G-FORM
  `evidence_refs` as the operative byte binding. No canonical byte moves.
- **R3 (rejected here):** editing the pinned report in place — it is a FROZEN artifact and a worker
  may not write canonical bytes.

## 7. Controls, falsifier, limits

Controls (7/7): C1 live-value mutation flips one entry to `CURRENT`; C2 one-hex-digit perturbation
stays `STALE_DECLARED` with no false `CURRENT`; C3 missing path → `MISSING_PATH`; C4 in-memory pin
mutation trips the drift guard; C5 tool dry-run writes nothing; C6 all-live synthetic report reaches
8/8 `CURRENT`; C7 static canonical digest reproduces across two runs.

Falsifier (void this measurement): exhibit (i) bytes matching one of
`b474fbc4`/`a7ccae4d`/`b71ec02c`/`f3c119a8` in a canonical or archived artifact; or (ii) a FROZEN
generation whose pinned rev27 closure record declares the rev29 schema/consistency pins; or (iii) a
dry-run of the pinned tool that exits 0 with `changed:false` on every audited path; or (iv) a
post-measurement write to the report path that supersedes the declared block. Any byte change among
the bound inputs voids the measurement — re-run the instrument and compare
`canonical_digest_sha256 = 5da99ec3678c5347c6d5c44b9cf8bfd241f323c37fc3db9df7d03a36c2871ccc`.

Limits: artifact/evidence measurement only; not a mathematics, physics or schema-content claim; no
gate verdict, node status, `validation_status`, canonical edit or repair; the consumer/map
observations are timestamped moving-target reads and are excluded from the canonical digest.
