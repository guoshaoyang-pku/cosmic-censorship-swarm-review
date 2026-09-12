#!/usr/bin/env python3
"""Assemble W029-F1-REV13-REOBSERVE-01 deliverables (pins, evidence, checkpoint, sums, events)."""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
TZ = timezone(timedelta(hours=8))
NOW = lambda: datetime.now(TZ).isoformat(timespec="seconds")

TASK_ID = "W029-F1-REV13-REOBSERVE-01"
PIN_SOURCES = {
    "rev13_live__schemas__af_wcc_vacuum.yaml": ROOT / "schemas/af_wcc_vacuum.yaml",
    "rev13_copy__worker-007__af_wcc_vacuum.d9cebb9404b2.yaml":
        ROOT / "artifacts/worker-007/rev29_preflight/snapshot/af_wcc_vacuum.d9cebb9404b2.yaml",
    "rev12_copy__worker-007__af_wcc_vacuum.cce9c60146d6.yaml":
        ROOT / "artifacts/worker-007/rev29_preflight/snapshot/af_wcc_vacuum.cce9c60146d6.yaml",
    "live__schemas__f1_falsifier_tests.jsonl": ROOT / "schemas/f1_falsifier_tests.jsonl",
    "live__research_map__formulation_taxonomy.yaml": ROOT / "research_map/formulation_taxonomy.yaml",
    "live__artifacts__formulation__FROZEN.json": ROOT / "artifacts/formulation/FROZEN.json",
}


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    report = json.loads((HERE / "report.json").read_text(encoding="utf-8"))
    digest = report["measurement_digest"]

    # 1. pinned inputs
    pinned = HERE / "pinned"
    pinned.mkdir(exist_ok=True)
    lines = []
    for name, src in PIN_SOURCES.items():
        dst = pinned / name
        shutil.copyfile(src, dst)
        h = sha256_file(dst)
        lines.append(f"{h}  pinned/{name}")
    (HERE / "pinned.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # 2. pre-registration (expectations are hard-coded in the adjudicated checker)
    pre = {
        "task_id": TASK_ID,
        "actor": "worker-029",
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-FORM",
        "registered_at": NOW(),
        "status": "declared_before_final_adjudicated_run",
        "index_of_expectations": "check_f1_rev13_reobserve.py (sha256 in SHA256SUMS); E1-E15 are "
                                 "hard-coded in that file, so the expectation set is pinned by "
                                 "the script hash and cannot be edited after the run unnoticed",
        "honesty_note": "The checker was developed in this session; exploratory executions preceded "
                        "the final adjudicated run. The expectations were written into the script "
                        "before the final run, and the recorded report.json is that run's output.",
        "expectation_ids": [e["id"] for e in report["expectations"]],
        "falsifier": report["falsifier"],
    }
    (HERE / "PREREGISTRATION.json").write_text(json.dumps(pre, indent=1) + "\n", encoding="utf-8")

    # 3. evidence
    ev = {
        "task_id": TASK_ID,
        "actor": "worker-029",
        "created_at": NOW(),
        "verdict": report["verdict"],
        "measurement_digest": digest,
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-FORM",
        "class_bound": True,
        "read_only": True,
        "no_canonical_write": True,
        "no_gate_verdict": True,
        "evidence_refs": [
            "schemas/af_wcc_vacuum.yaml#d9cebb9404b2",
            "schemas/f1_falsifier_tests.jsonl#56bcb4b3234b",
            "research_map/formulation_taxonomy.yaml#0abb9ed8a961",
            "artifacts/formulation/FROZEN.json#815e08079aef",
            "artifacts/worker-029/f1_rev13_reobserve/report.json",
            "artifacts/worker-029/f1_rev13_reobserve/PREREGISTRATION.json",
            "artifacts/worker-029/f1_rev13_reobserve/CHECKPOINT.json",
        ],
        "pins": report["pins"],
        "pin_drift": report["pin_drift"],
        "controls": report["controls"],
        "failed_expectations": [e["id"] for e in report["expectations"] if not e["ok"]],
        "findings": [f["id"] for f in report["findings"]],
        "falsifier": report["falsifier"],
        "next_falsifier": report["next_falsifier"],
    }
    (HERE / "evidence.json").write_text(json.dumps(ev, indent=1) + "\n", encoding="utf-8")

    # 4. README
    c = report["census"]
    n = report["named_rows"]
    readme = f"""# {TASK_ID} — F1 suite re-observation against live rev13

**One class-bound task.** Node `F1`, class `AF-WCC-VAC-GEN`, gate `G-FORM`.
Read-only worker measurement; no canonical byte written, no gate verdict, no node status.

## Question

REC-36 item (6) folds into the rev14 / FROZEN rev30 revision a rebind of all 25 rows of
`schemas/f1_falsifier_tests.jsonl` (`56bcb4b3234b`) to the live F1 pin plus re-observation of
`F1-AMB-11` / `F1-AMB-17` / `F1-AMB-23` against the rev13 text. Rev13 (`d9cebb9404b2`) moved the
visibility-strictness directions. Does any row's stored probe actually read the moved content, and
would a sha256-only rebind leave a row green while the substance it relies on changed?

## Result (verdict: `{report['verdict']}`)

| measurement | value |
|---|---|
| rows / probes | {c['rows']} / {c['probes']} |
| rows bound to superseded rev12 `cce9c60146d6` | **{c['rows_bound_to_rev12_cce9c60146d6']} / 25** |
| rows citing live rev13 `d9cebb9404b2` | **{c['rows_bound_to_live_rev13_d9cebb9404b2']} / 25** |
| changed leaves rev12 -> rev13 | {c['changed_leaf_count']} (substantive, not bookkeeping) |
| rows whose probes read changed content | {c['rows_reading_changed_content']} — exactly `F1-AMB-11, 17, 23, 25` |
| rows with a recomputed probe mismatch | {c['rows_with_recomputed_mismatch']} — `F1-AMB-25` only (pre-existing) |
| probes asserting the corrected direction (STRONGER/WEAKER) | **0 / 84** |
| probes reading any `relation` leaf | **0** |
| measurement digest | `{digest}` |

**No named row flips mechanically against rev13** — every stored `pass` still recomputes. The
finding is narrower and sharper than a defect: the rows are *substantively* stale while being
*mechanically* green, so a hash-only rebind would pass every binding check and re-observe nothing.

## Per-row re-observation

| row | deciding field | changed leaf | mechanical | substance |
|---|---|---|---|---|
| `F1-AMB-11` | `visibility.definition` | `visibility.definition` (EXACT) | unchanged_pass | changed |
| `F1-AMB-17` | `visibility.definition` | `visibility.definition` (EXACT) | unchanged_pass | changed |
| `F1-AMB-23` | `class_identity_variants` | `[0].relation` STRONGER->WEAKER | unchanged_pass | changed |

Rev14 must, per row:
- **F1-AMB-11** — refresh the stored excerpt of `visibility.definition`; it quotes only the
  unchanged prefix and does not carry the rev13 equivalence statement. `resolved_geodesic` stands.
- **F1-AMB-17** — keep `NOT equivalent` on the *unchanged* leaf `visibility.negation_conclusion`
  (single-point vs open-set). Do **not** retarget it at `visibility.definition`, which now asserts
  the *tail vs whole-curve* EQUIVALENT on the same block. Whole-block equivalence greps conflate
  the two claims. Re-observe probe[0] and record that the field moved for an unrelated correction.
- **F1-AMB-23** — the direction its container now carries is covered by **no probe**; either add a
  direction probe on `class_identity_variants[0].relation` or record explicitly that
  `is_this_class=false` is direction-independent. The row also has `schema_snapshot: null` and
  `schema_under_test: null`, so it declares no schema revision under test.

Findings `W029-R13-01 … -06` are machine-readable in `report.json`.

## Method and independence

- `check_f1_rev13_reobserve.py` re-implements the probe semantics independently
  (`contains` / `equals` / `path_exists` / `nonnull` / `is_none` / `is_true`, `json.dumps`
  flattening) and recomputes all 84 probes against the live rev13 bytes.
- The rev12 snapshot is taken from **three** independent on-disk copies (workers 007/060/088),
  byte-identical (`K6`); the rev13 bytes are corroborated by **four** further independent copies
  (workers 040/060/082 and 007), all equal to the live pin (`K7`).
- Controls: `K1` unknown kind fail-closed, `K2` determinism, `K4` probe sensitivity (token
  deletion flips `F1-AMB-11` probe[1]; the mutation is asserted to remove the substring so the
  control cannot pass vacuously), `K5` the known `F1-AMB-25` mismatch reproduces, `K6`/`K7`
  corpus integrity. All pass. `E1`–`E15` all hold; zero pin drift T0->T1.
- The `K4` control initially returned **false** because the first mutation (`TAIL` -> `TAILX`)
  left the searched substring intact. The mutation was corrected to delete the token; that
  false-pass is retained here as a process note rather than silently fixed.

## Falsifier

{report['falsifier']}

## Deliverables

- `check_f1_rev13_reobserve.py` — checker, exit 0 complete / 2 failed expectation / 3 pin drift
- `report.json` — full machine-readable report, digest `{digest}`
- `PREREGISTRATION.json`, `evidence.json`, `CHECKPOINT.json`, `pinned/`, `SHA256SUMS`
"""
    (HERE / "README.md").write_text(readme, encoding="utf-8")

    # 5. checkpoint (artifact_hashes excludes CHECKPOINT.json itself)
    comps = ["report.json", "evidence.json", "README.md", "PREREGISTRATION.json",
             "check_f1_rev13_reobserve.py", "pinned.sha256"]
    artifact_hashes = {f: sha256_file(HERE / f) for f in comps}
    artifact_hashes.update(
        {f"pinned/{p.name}": sha256_file(p) for p in sorted((HERE / "pinned").iterdir())})
    ckpt = {
        "task_id": TASK_ID,
        "actor": "worker-029",
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-FORM",
        "created_at": NOW(),
        "status": "complete",
        "verdict": report["verdict"],
        "measurement_digest": digest,
        "pins": report["pins"],
        "pin_drift": report["pin_drift"],
        "controls": report["controls"],
        "expectations_ok": [e["id"] for e in report["expectations"] if e["ok"]],
        "expectations_failed": [e["id"] for e in report["expectations"] if not e["ok"]],
        "findings": [f["id"] for f in report["findings"]],
        "falsifier": report["falsifier"],
        "falsifier_outcome": "NOT FALSIFIED",
        "next_falsifier": report["next_falsifier"],
        "no_canonical_write": True,
        "no_gate_verdict": True,
        "self_hash_excluded": True,
        "artifact_hashes": artifact_hashes,
    }
    (HERE / "CHECKPOINT.json").write_text(json.dumps(ckpt, indent=1) + "\n", encoding="utf-8")

    # 6. SHA256SUMS over the artifact tree (events.jsonl excluded by design)
    sums = []
    for p in sorted(HERE.rglob("*")):
        if p.is_file() and p.name not in ("SHA256SUMS", "events.jsonl"):
            sums.append(f"{sha256_file(p)}  {p.relative_to(HERE)}")
    (HERE / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")
    sums_hash = sha256_file(HERE / "SHA256SUMS")

    # 7. outbox events
    ts = datetime.now(TZ).strftime("%Y%m%dT%H%M%S")
    base = f"w029r13-{ts}"
    rel = "artifacts/worker-029/f1_rev13_reobserve"
    events = [
        {
            "event_id": f"{base}-01-artifact-report",
            "event_type": "artifact",
            "created_at": NOW(),
            "actor": "worker-029",
            "node_id": "F1",
            "class_id": "AF-WCC-VAC-GEN",
            "gate": "G-FORM",
            "artifact_type": "reobservation_report",
            "path": f"{rel}/report.json",
            "sha256": artifact_hashes["report.json"],
            "validation_status": "worker_measured_unverified",
            "summary": "Independent re-observation of the 25-row F1 falsifier suite against live "
                       "rev13 d9cebb9404b2: 25/25 rows still bound to rev12 cce9c60146d6, 0/25 to "
                       "rev13; 12-leaf substantive delta; 4 rows read changed content "
                       "(AMB-11/17/23/25); no mechanical flip; 0/84 probes assert the corrected "
                       "STRONGER->WEAKER direction; E1-E15 hold, controls K1/K2/K4/K5/K6/K7 pass.",
            "evidence_refs": [f"{rel}/report.json#{digest}", f"{rel}/SHA256SUMS#{sums_hash[:12]}"],
            "falsifier": report["falsifier"],
        },
        {
            "event_id": f"{base}-02-artifact-evidence",
            "event_type": "artifact",
            "created_at": NOW(),
            "actor": "worker-029",
            "node_id": "F1",
            "class_id": "AF-WCC-VAC-GEN",
            "gate": "G-FORM",
            "artifact_type": "evidence_manifest",
            "path": f"{rel}/evidence.json",
            "sha256": artifact_hashes["evidence.json"],
            "validation_status": "worker_measured_unverified",
            "summary": "Evidence/pin manifest for the F1 rev13 re-observation; read-only, no "
                       "canonical write, no gate verdict.",
            "evidence_refs": [f"{rel}/evidence.json"],
            "falsifier": report["falsifier"],
        },
        {
            "event_id": f"{base}-03-review-suite",
            "event_type": "review",
            "created_at": NOW(),
            "actor": "worker-029",
            "node_id": "F1",
            "class_id": "AF-WCC-VAC-GEN",
            "gate": "G-FORM",
            "target_id": "schemas/f1_falsifier_tests.jsonl#56bcb4b3234b",
            "reviewer": "worker-029",
            "verdict": "revise",
            "score": 3.0,
            "hard_failures": [
                "stale binding: 25/25 rows cite superseded F1 rev12 cce9c60146d6, 0/25 cite live "
                "rev13 d9cebb9404b2",
                "direction coverage gap: 0/84 probes assert STRONGER/WEAKER or read any `relation` "
                "leaf, so the rev13 correction to class_identity_variants[0].relation is unpinned",
            ],
            "findings": [
                "F1-AMB-11/17/23 read content changed by rev13 while every stored pass still "
                "recomputes: a sha256-only rebind would be green and vacuous",
                "F1-AMB-17 scope-collision hazard: keep `NOT equivalent` on "
                "visibility.negation_conclusion, do not retarget at visibility.definition",
                "F1-AMB-23 declares schema_snapshot=null and schema_under_test=null",
                "rev13-relevant row set is closed and equals REC-36 item (6)'s set",
            ],
            "evidence_refs": [f"{rel}/report.json#{digest}", f"{rel}/SHA256SUMS#{sums_hash[:12]}"],
            "falsifier": report["falsifier"],
        },
        {
            "event_id": f"{base}-04-status",
            "event_type": "status",
            "created_at": NOW(),
            "actor": "worker-029",
            "node_id": "F1",
            "class_id": "AF-WCC-VAC-GEN",
            "gate": "G-FORM",
            "status": "active",
            "summary": "W029-F1-REV13-REOBSERVE-01 complete at worker level: one bounded class-bound "
                       "task, read-only, verdict "
                       "reobserve_required__no_mechanical_flip__direction_unpinned; E1-E15 hold; "
                       "zero pin drift; no canonical edit; no gate or node status claimed.",
            "evidence_refs": [
                f"{rel}/report.json#{digest}",
                f"{rel}/evidence.json#{artifact_hashes['evidence.json'][:12]}",
                f"{rel}/CHECKPOINT.json#{artifact_hashes.get('CHECKPOINT.json', sha256_file(HERE / 'CHECKPOINT.json'))[:12]}",
                f"{rel}/README.md#{artifact_hashes['README.md'][:12]}",
                f"{rel}/SHA256SUMS#{sums_hash[:12]}",
            ],
            "next_falsifier": report["next_falsifier"],
        },
    ]
    (HERE / "events.jsonl").write_text(
        "\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")

    # 8. append to my outbox (protocol upward channel)
    outbox = ROOT / "comms/outbox/worker-029.jsonl"
    with outbox.open("a", encoding="utf-8") as fh:
        for e in events:
            fh.write(json.dumps(e) + "\n")
    # verify the appended lines parse back
    tail = outbox.read_text(encoding="utf-8").splitlines()[-len(events):]
    assert all(json.loads(l)["event_id"].startswith(base) for l in tail), "outbox append verify failed"
    print(json.dumps({"ok": True, "event_ids": [e["event_id"] for e in events],
                      "sums_hash": sums_hash, "measurement_digest": digest,
                      "checkpoint_hash": sha256_file(HERE / "CHECKPOINT.json")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
