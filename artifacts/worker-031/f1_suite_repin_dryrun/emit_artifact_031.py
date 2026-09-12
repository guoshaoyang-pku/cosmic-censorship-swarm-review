#!/usr/bin/env python3
"""Emit README.md, CHECKPOINT.json, SHA256SUMS for W031-F1-SUITE-REPIN-PROPOSAL-01.

Reads report.json (written by dryrun_repin_031.py) and pins the deliverable hashes.
Copies CHECKPOINT.json to runtime/state/ (worker checkpoint convention). Does not touch
any canonical path.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
from datetime import datetime, timedelta, timezone

TZ = timezone(timedelta(hours=8))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
OUTDIR = os.path.join(ROOT, "artifacts/worker-031/f1_suite_repin_dryrun")
TASK = "W031-F1-SUITE-REPIN-PROPOSAL-01"
INSTANCE = "worker-031-20260912T005730-968807"


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def main() -> int:
    rp = os.path.join(OUTDIR, "report.json")
    with open(rp, encoding="utf-8") as fh:
        rep = json.load(fh)
    b = rep["baseline_live_rev13"]
    a = rep["post_patch"]["tier_A"]
    bb = rep["post_patch"]["tier_B"]
    casc = rep["frozen_cascade"]
    ctl = rep["controls"]
    patch = rep["patch"]

    readme = f"""# {TASK} — dry-run re-pin of the F1 falsifier suite

**Agent** worker-031 · **class** `AF-WCC-VAC-GEN` (refs `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`) ·
**node** F1 · **gate** G-FORM · **verdict** `{rep['verdict']}` · worker measurement only.

The owner's blocker `L-FORM-04` (astra-lead-formulation, 2026-09-12T00:57:43+08:00) declares
`{rep['canonical_suite_sha256'][:12]}` NOT re-bound to F1 rev13 `d9cebb9404b2`. worker-029 and
worker-032 measured that defect; this task builds the **repair as an exact patch**, applies it to
artifact-local copies only, and measures that it closes every defect at the live pins.

## Question

What is the minimal patch to `schemas/f1_falsifier_tests.jsonl` that makes the suite self-consistent
at F1 rev13 / F0 rev5 / FROZEN rev29, and what does that patch cascade into?

## Pins (full sha256; drift-guarded before and after the run)

| path | sha256 | role |
|---|---|---|
| `schemas/f1_falsifier_tests.jsonl` | `{rep['canonical_suite_sha256']}` | suite under repair (read-only) |
| `schemas/af_wcc_vacuum.yaml` | `{rep['pinned_inputs']['schemas/af_wcc_vacuum.yaml']['sha256']}` | F1 rev13 |
| `research_map/formulation_taxonomy.yaml` | `{rep['pinned_inputs']['research_map/formulation_taxonomy.yaml']['sha256']}` | F0 rev5 |
| `artifacts/formulation/FROZEN.json` | `{rep['pinned_inputs']['artifacts/formulation/FROZEN.json']['sha256']}` | rev29 |
| `schemas/taxonomy_cases.jsonl` | `{rep['pinned_inputs']['schemas/taxonomy_cases.jsonl']['sha256']}` | corpus |
| `artifacts/formulation/evidence/taxonomy_consistency.json` | `{rep['pinned_inputs']['artifacts/formulation/evidence/taxonomy_consistency.json']['sha256']}` | consistency |
| `artifacts/worker-007/rev29_preflight/snapshot/af_wcc_vacuum.cce9c60146d6.yaml` | `{rep['pre_repair_f1_snapshot']['sha256']}` | pre-repair rev12 snapshot |

All 10 pinned inputs matched at start and finish (`inputs_stable_during_run: {rep['inputs_stable_during_run']}`).

## Result

| measurement | baseline (canonical) | tier A (operative only) | tier B (recommended) |
|---|---:|---:|---:|
| row bindings live | {b['binding_live']}/25 | {a['census']['binding_live']}/25 | {bb['census']['binding_live']}/25 |
| `binding_ref` vs `binding_sha256` consistent | {b['ref_sha_consistent']}/25 | {a['census']['ref_sha_consistent']}/25 | {bb['census']['ref_sha_consistent']}/25 |
| cross-artifact live | {b['cross_artifact_live']}/1 | {a['census']['cross_artifact_live']}/1 | {bb['census']['cross_artifact_live']}/1 |
| stored probes re-evaluating true | {b['probes_recomputed_pass']}/{b['probes_total']} | {a['census']['probes_recomputed_pass']}/84 | {bb['census']['probes_recomputed_pass']}/84 |
| vendor C1a/C1b/C2/C4–C10 | {sum(1 for v in rep['baseline_vendor'].values() if v['pass'])}/10 pass | {sum(1 for v in a['vendor'].values() if v['pass'])}/10 pass | {sum(1 for v in bb['vendor'].values() if v['pass'])}/10 pass |
| JSON-pointer changes | — | {a['distinct_pointers_declared']} | {bb['distinct_pointers_declared']} |
| patched sha256 | — | `{a['sha256']}` | `{bb['sha256']}` |
| patched bytes | {rep['canonical_suite_bytes']} | {a['bytes']} | {bb['bytes']} |

Baseline defect set (exactly as pre-registered): 25/25 row bindings stale (all carry pre-repair F1
`cce9c60146d6`), the single `F1-AMB-25` cross-artifact binding stale (F0 rev4 `276009f4`), and the two
`F1-AMB-25` stored probes false — probe 0 `f0_binding.declared_f0_sha256` (expects `276009f4`) and
probe 3 `f0_binding.binding_note` (expects `astra-classscope-02`). The same two probe mismatches
recompute at the hash-verified pre-repair rev12 snapshot, so the rev13 staging did not introduce them.

**Tier A** (53 pointers): 25× `binding_ref`+`binding_sha256` → rev13; `F1-AMB-25`
`cross_artifact[0].sha256` and probe 0 `expected` → live F0 `0abb9ed8`; probe 3 `expected` →
`{patch['binding_note_anchor_primary']}` anchor.
**Tier B** (84 pointers, recommended): tier A plus provenance/descriptive refresh —
`binding_frozen_revision` → 29 on all rows, `binding_frozen_revision_schema` → 13, `rebound_at`
(placeholder), `rebind_note`, both `observed_excerpt`s, and the F0 `evidence_refs` entry.

Minimality: the measured changed-pointer set equals the declared set exactly on both tiers
(0 unexpected, 0 declared-but-inert, row set unchanged). Semantics: the full question/deciding-field/
falsifier/class key set is identical on all 25 rows on both tiers.

## Cascade (not a worker action)

FROZEN rev29 pins `schemas/f1_falsifier_tests.jsonl` at `{rep['canonical_suite_sha256'][:12]}`;
any re-pin moves that one path, so `change_protocol` requires **FROZEN rev30** with the new
sha256/bytes, a re-emitted artifact event, a refreshed `runtime/state/artifact_hashes.json`, and a
vendor-verifier re-run. F1/F2a/F2b/F0 bytes and their FROZEN pins are untouched.

## Owner decisions

{chr(10).join('- ' + d for d in rep['owner_decisions'])}

## Controls ({sum(1 for v in ctl.values() if (v is True) or (isinstance(v, dict) and v.get('pass') is True))}/{len(ctl)} pass)

| control | value |
|---|---|
| K1 serializer round-trip byte-identical | `{ctl['K1_serializer_roundtrip_byte_identical']}` |
| K2 revision-responsive decoy (sandbox F1 rev14) | {ctl['K2_revision_responsive_decoy']['decoy_binding_stale']}/25 stale |
| K3 `binding_sha256` operative | {ctl['K3_binding_sha256_operative']['binding_stale']}/25 stale, {ctl['K3_binding_sha256_operative']['ref_sha_inconsistent']}/25 ref-inconsistent |
| K4a drop deciding `expected` | {ctl['K4a_drop_deciding_expected']['recomputed_pass']}/84 (mismatch {ctl['K4a_drop_deciding_expected']['mismatch_indices']}) |
| K4b drop `binding_note` `expected` | {ctl['K4b_drop_binding_note_expected']['recomputed_pass']}/84 (mismatch {ctl['K4b_drop_binding_note_expected']['mismatch_indices']}) |
| K5 cross-artifact operative | {ctl['K5_cross_artifact_operative']['cross_stale']} stale, probes {ctl['K5_cross_artifact_operative']['probes_recomputed_pass']}/84 |
| K6 anchor variants | V1={ctl['K6_binding_note_anchors']['variant_passes']['V1']}/84, V2={ctl['K6_binding_note_anchors']['variant_passes']['V2']}/84 |
| K7 input drift at finish | stable `{ctl['K7_input_drift_guard']['stable']}` |
| K8 patch determinism (fresh loads) | `{ctl['K8_patch_determinism']}` |
| K9 sandbox confinement | canonical paths written: {ctl['K9_sandbox_confinement']['canonical_paths_written']} |

## Deliverables

| path | sha256 (computed at emit) |
|---|---|
| `report.json` | TO_FILL_REPORT |
| `PROPOSED_PATCH.json` | TO_FILL_PATCH |
| `dryrun_repin_031.py` | TO_FILL_INSTRUMENT |
| `patched/f1_falsifier_tests.tierA.jsonl` | TO_FILL_TIERA |
| `patched/f1_falsifier_tests.tierB.jsonl` | TO_FILL_TIERB |
| `CHECKPOINT.json` | TO_FILL_CHECKPOINT |

**Falsifier.** {rep['falsifier']}

**Next falsifier.** {rep['next_falsifier']}

**Authority.** Worker measurement only. No canonical path was written: the patch exists solely as
`PROPOSED_PATCH.json` + the two artifact-local `patched/*.jsonl` files. No gate verdict, no node
status, no `validation_status`.

**Replay.** `{rep['replay']}`
"""
    with open(os.path.join(OUTDIR, "README.md"), "w", encoding="utf-8") as fh:
        fh.write(readme)

    checkpoint = {
        "task_id": TASK,
        "agent": "worker-031",
        "instance": INSTANCE,
        "created_at": rep["created_at"],
        "finished_at": rep["finished_at"],
        "class_id": rep["class_id"],
        "node_id": "F1",
        "gate": "G-FORM",
        "verdict": rep["verdict"],
        "pins": {k: v["sha256"] for k, v in rep["pinned_inputs"].items()},
        "pre_repair_snapshot": rep["pre_repair_f1_snapshot"],
        "key_measurements": {
            "baseline_bindings_stale": b["binding_stale"],
            "baseline_probes_recomputed_pass": b["probes_recomputed_pass"],
            "baseline_probe_mismatches": [(m["test_id"], m["probe_index"]) for m in b["probe_mismatches"]],
            "tier_A_sha256": a["sha256"], "tier_A_pointers": a["distinct_pointers_declared"],
            "tier_A_bindings_live": a["census"]["binding_live"],
            "tier_A_probes_recomputed_pass": a["census"]["probes_recomputed_pass"],
            "tier_B_sha256": bb["sha256"], "tier_B_pointers": bb["distinct_pointers_declared"],
            "tier_B_bindings_live": bb["census"]["binding_live"],
            "tier_B_probes_recomputed_pass": bb["census"]["probes_recomputed_pass"],
            "vendor_checks_tier_B": {k: v["pass"] for k, v in bb["vendor"].items()},
            "frozen_cascade_moved_paths": casc["moved_paths"],
            "controls_pass": ctl,
        },
        "deliverables": {},
        "canonical_paths_written": [],
        "falsifier": rep["falsifier"],
        "next_falsifier": rep["next_falsifier"],
        "authority": rep["authority"],
        "replay": rep["replay"],
    }
    ckpt_path = os.path.join(OUTDIR, "CHECKPOINT.json")

    def rel(path):
        return os.path.relpath(path, ROOT)

    deliverables = {
        rel(os.path.join(OUTDIR, "report.json")): sha256_file(os.path.join(OUTDIR, "report.json")),
        rel(os.path.join(OUTDIR, "PROPOSED_PATCH.json")): sha256_file(os.path.join(OUTDIR, "PROPOSED_PATCH.json")),
        rel(os.path.join(OUTDIR, "dryrun_repin_031.py")): sha256_file(os.path.join(OUTDIR, "dryrun_repin_031.py")),
        rel(os.path.join(OUTDIR, "patched/f1_falsifier_tests.tierA.jsonl")): sha256_file(os.path.join(OUTDIR, "patched/f1_falsifier_tests.tierA.jsonl")),
        rel(os.path.join(OUTDIR, "patched/f1_falsifier_tests.tierB.jsonl")): sha256_file(os.path.join(OUTDIR, "patched/f1_falsifier_tests.tierB.jsonl")),
    }
    checkpoint["deliverables"] = deliverables
    with open(ckpt_path, "w", encoding="utf-8") as fh:
        json.dump(checkpoint, fh, indent=1, sort_keys=True)
        fh.write("\n")
    checkpoint["deliverables"][rel(ckpt_path)] = sha256_file(ckpt_path)

    # fill README hashes now that all files exist
    readme = readme.replace("TO_FILL_REPORT", deliverables[rel(os.path.join(OUTDIR, "report.json"))])
    readme = readme.replace("TO_FILL_PATCH", deliverables[rel(os.path.join(OUTDIR, "PROPOSED_PATCH.json"))])
    readme = readme.replace("TO_FILL_INSTRUMENT", deliverables[rel(os.path.join(OUTDIR, "dryrun_repin_031.py"))])
    readme = readme.replace("TO_FILL_TIERA", deliverables[rel(os.path.join(OUTDIR, "patched/f1_falsifier_tests.tierA.jsonl"))])
    readme = readme.replace("TO_FILL_TIERB", deliverables[rel(os.path.join(OUTDIR, "patched/f1_falsifier_tests.tierB.jsonl"))])
    readme = readme.replace("TO_FILL_CHECKPOINT", checkpoint["deliverables"][rel(ckpt_path)])
    with open(os.path.join(OUTDIR, "README.md"), "w", encoding="utf-8") as fh:
        fh.write(readme)

    # SHA256SUMS (self excluded), then the runtime/state copy
    sums_path = os.path.join(OUTDIR, "SHA256SUMS")
    entries = dict(deliverables)
    entries[rel(os.path.join(OUTDIR, "README.md"))] = sha256_file(os.path.join(OUTDIR, "README.md"))
    entries[rel(os.path.join(OUTDIR, "patched/f1_falsifier_tests.tierA.jsonl.sha256"))] = sha256_file(os.path.join(OUTDIR, "patched/f1_falsifier_tests.tierA.jsonl.sha256"))
    entries[rel(os.path.join(OUTDIR, "patched/f1_falsifier_tests.tierB.jsonl.sha256"))] = sha256_file(os.path.join(OUTDIR, "patched/f1_falsifier_tests.tierB.jsonl.sha256"))
    with open(sums_path, "w", encoding="utf-8") as fh:
        for p, h in sorted(entries.items()):
            fh.write(f"{h}  {p}\n")

    state_copy = os.path.join(ROOT, "runtime/state/w031_f1_suite_repin_dryrun_checkpoint.json")
    shutil.copyfile(ckpt_path, state_copy)
    print(json.dumps({"readme": rel(os.path.join(OUTDIR, "README.md")),
                      "checkpoint": rel(ckpt_path), "state_copy": rel(state_copy),
                      "sha256sums": rel(sums_path),
                      "deliverables": {k: v[:12] for k, v in sorted(entries.items())}},
                     indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
