#!/usr/bin/env python3
"""W056-FREEZE-QUIESCENCE-01 -- hash-stability witness for the frozen research inputs.

Why this exists
---------------
The audit lead's live directive (direction_update
`audit-direction-freeze-quiescence-20260912T0036`, 2026-09-12T00:35:58+08:00) requires:
writers stop on the frozen paths, FROZEN publishes the pins before reviewers are dispatched,
and "gate verdicts are invalid if any pinned input changes between the two verdicts".

That rule needs a measurement.  This runner samples the sha256 of the canonical content
targets AND of every path pinned by `artifacts/formulation/FROZEN.json`, every `--interval`
seconds for `--window` seconds, and reports whether a single hash per path held for the whole
window.  It never writes outside its own artifact directory, never edits a canonical
artifact, and emits no gate verdict.

Rule (frozen before the run)
----------------------------
Verdict-bearing paths = the 8 canonical content targets
+ every readable path pinned in FROZEN.json `files` / `logical_artifacts`
+ the two freeze indices (FROZEN.json, KEY_MANIFEST.json), when present at T0.

  QUIESCENT  every verdict-bearing path had one single sha256 across all samples
  DRIFT      at least one verdict-bearing path showed >=2 distinct sha256 values

`research_map/research_map.json` is *reported* but excluded from the verdict: it is the live
bookkeeping channel and is expected to move as events are applied.

Exit codes
----------
0  QUIESCENT   (all verdict-bearing paths stable for the whole window)
3  DRIFT       (a verdict-bearing path changed; drift_targets names it and the instant)
2  setup error (a required content target is missing / unreadable)

Usage
-----
  python3 run_quiescence_056.py --window 600 --interval 20 --out quiescence-056.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime

# Swarm root = <root>/artifacts/worker-056/freeze_quiescence/run_quiescence_056.py
ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

# --- frozen task constants (declared before any sampling) --------------------------------

TASK_ID = "W056-FREEZE-QUIESCENCE-01"
ACTOR = "worker-056"
CLASS_IDS = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]
NODE_IDS = ["F0", "F1", "F2a", "F2b", "L0", "L1", "A0"]
GATE = "G-F0;G-FORM;G-LIT;G-AUDIT"
FROZEN_PATH = "artifacts/formulation/FROZEN.json"
KEY_MANIFEST_PATH = "artifacts/formulation/KEY_MANIFEST.json"
MAP_PATH = "research_map/research_map.json"

CONTENT_TARGETS = [
    ("F0-canonical-taxonomy", "research_map/formulation_taxonomy.yaml"),
    ("F0-authoring-supplement", "artifacts/formulation/formulation_taxonomy.yaml"),
    ("F1-af-wcc-vacuum", "schemas/af_wcc_vacuum.yaml"),
    ("F2a-af-scc-c2-vacuum", "schemas/af_scc_c2_vacuum.yaml"),
    ("F2b-af-scc-c0-vacuum", "schemas/af_scc_c0_vacuum.yaml"),
    ("L0-theorem-ledger", "ledger/theorems.jsonl"),
    ("L1-citation-ledger", "ledger/citation_audit.csv"),
    ("A0-evaluation-rubric", "evaluation_rubric.yaml"),
]

# Reported but excluded from the quiescence verdict (live bookkeeping channel only).
NON_VERDICT_TARGETS = [("global-map", MAP_PATH)]

VERDICT_RULE = (
    "QUIESCENT iff every verdict-bearing path (the 8 content targets + every readable "
    "FROZEN.json pin + the FROZEN.json / KEY_MANIFEST.json indices when present at T0) "
    "presents exactly one distinct sha256 across all samples in the declared window; "
    "DRIFT otherwise. research_map/research_map.json is reported but not verdict-bearing. "
    "The rule was fixed before the first sample."
)

NON_CLAIMS = [
    "This is worker evidence, not a gate verdict, node status, or validation_status=passed.",
    "QUIESCENT at this window does not certify content correctness, only byte-stability; "
    "reviewers must still bind their verdicts to the hashes recorded here.",
    "QUIESCENT is time-bounded: it says nothing about writes after the last sample instant.",
    "The runner read canonical artifacts read-only; it edited nothing outside "
    "artifacts/worker-056/freeze_quiescence/.",
    "No claim is made about ledger contents; only their hashes were measured.",
    "The pin set is the one FROZEN.json carried at T0; a pin added after T0 is outside this "
    "witness even if the added path later changes.",
]


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 16), b""):
            h.update(block)
    return h.hexdigest()


def stat_target(rel_path: str) -> dict:
    try:
        st = os.stat(rel_path)
        return {
            "path": rel_path,
            "sha256": sha256_file(rel_path),
            "bytes": st.st_size,
            "mtime": datetime.fromtimestamp(st.st_mtime).astimezone().isoformat(
                timespec="seconds"
            ),
            "mtime_ns": st.st_mtime_ns,
            "readable": True,
        }
    except OSError as exc:
        return {"path": rel_path, "readable": False, "error": str(exc)}


def read_json(path: str):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def collect_verdict_paths() -> tuple:
    """Content targets + FROZEN pins + freeze indices, deduplicated, labelled by group."""
    content = {rel: name for name, rel in CONTENT_TARGETS}
    pin_meta = {}
    frozen = read_json(FROZEN_PATH)
    if isinstance(frozen, dict):
        files = frozen.get("files") if isinstance(frozen.get("files"), dict) else {}
        for rel, pin in files.items():
            if isinstance(pin, dict) and "sha256" in pin:
                pin_meta.setdefault(rel, {"group": "FROZEN.files", "pinned": pin["sha256"]})
        logical = frozen.get("logical_artifacts")
        if isinstance(logical, dict):
            for name, e in logical.items():
                if isinstance(e, dict) and e.get("path") and e.get("sha256"):
                    pin_meta.setdefault(e["path"], {
                        "group": "FROZEN.logical_artifacts",
                        "pinned": e["sha256"], "name": name})
    indices = {}
    for rel in (FROZEN_PATH, KEY_MANIFEST_PATH):
        if stat_target(rel)["readable"]:
            indices[rel] = os.path.basename(rel)
    aux = {rel: name for name, rel in NON_VERDICT_TARGETS}

    verdict_paths = {}
    for rel, name in content.items():
        verdict_paths[rel] = {"group": "content", "name": name}
    for rel, meta in pin_meta.items():
        if rel not in verdict_paths:
            verdict_paths[rel] = {"group": meta["group"], "pinned": meta["pinned"],
                                  "name": meta.get("name", os.path.basename(rel))}
    for rel, name in indices.items():
        if rel not in verdict_paths:
            verdict_paths[rel] = {"group": "freeze-index", "name": name}
    return verdict_paths, aux, frozen


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", type=int, default=600,
                    help="total observation window in seconds (default 600)")
    ap.add_argument("--interval", type=int, default=20,
                    help="seconds between samples (default 20)")
    ap.add_argument("--out", default="quiescence-056.json",
                    help="output JSON path (default: alongside this script)")
    args = ap.parse_args()

    if args.window < 0 or args.interval <= 0:
        print("setup error: window must be >=0 and interval > 0", file=sys.stderr)
        return 2

    # All target paths are swarm-root-relative; the runner is location-independent.
    os.chdir(ROOT)

    missing = [rel for _, rel in CONTENT_TARGETS if not stat_target(rel)["readable"]]
    if missing:
        print(f"setup error: required content targets missing: {missing}", file=sys.stderr)
        return 2

    verdict_paths, aux_paths, frozen = collect_verdict_paths()
    all_paths = list(verdict_paths) + list(aux_paths)

    t_start = time.time()
    samples = []
    first = {rel: stat_target(rel) for rel in all_paths}
    map_t0 = read_json(MAP_PATH) or {}
    samples.append({"at": now_iso(), "t_offset_seconds": 0,
                    "sha256": {rel: first[rel].get("sha256") for rel in all_paths}})

    elapsed = 0.0
    while elapsed < args.window:
        time.sleep(min(args.interval, args.window - elapsed))
        elapsed = round(time.time() - t_start, 3)
        snap = {rel: stat_target(rel) for rel in all_paths}
        samples.append({"at": now_iso(), "t_offset_seconds": elapsed,
                        "sha256": {rel: snap[rel].get("sha256") for rel in all_paths}})

    # closing read is always the authoritative t1 sample
    last = {rel: stat_target(rel) for rel in all_paths}
    map_t1 = read_json(MAP_PATH) or {}
    samples.append({"at": now_iso(), "t_offset_seconds": round(time.time() - t_start, 3),
                    "sha256": {rel: last[rel].get("sha256") for rel in all_paths}})

    def distinct(rel: str) -> list:
        seen = []
        for s in samples:
            v = s["sha256"].get(rel)
            if v not in seen:
                seen.append(v)
        return seen

    def timeline(rel: str) -> list:
        changes, prev = [], None
        for s in samples:
            cur = s["sha256"].get(rel)
            if prev is not None and cur != prev:
                changes.append({"at": s["at"], "t_offset_seconds": s["t_offset_seconds"],
                                "from": prev, "to": cur})
            prev = cur
        return changes

    def entry(rel: str, meta: dict) -> dict:
        values = distinct(rel)
        return {
            "name": meta.get("name", os.path.basename(rel)),
            "group": meta.get("group", "aux"),
            "pinned_sha256": meta.get("pinned"),
            "sha256_t0": first[rel].get("sha256"),
            "sha256_t1": last[rel].get("sha256"),
            "distinct_sha256_in_window": values,
            "bytes": last[rel].get("bytes"),
            "mtime_t0": first[rel].get("mtime"),
            "mtime_t1": last[rel].get("mtime"),
            "changed_in_window": len([v for v in values if v is not None]) > 1,
            "changes": timeline(rel),
        }

    verdict_report, drift_targets = {}, []
    for rel, meta in verdict_paths.items():
        e = entry(rel, meta)
        verdict_report[rel] = e
        if e["changed_in_window"]:
            drift_targets.append(rel)

    aux_report = {rel: entry(rel, {"group": "aux", "name": meta})
                  for rel, meta in aux_paths.items()}

    # T0 pin coherence: FROZEN pins vs the T0 bytes already sampled here.
    pin_mismatches, pins_checked, pins_missing = [], 0, []
    for rel, meta in verdict_paths.items():
        pinned = meta.get("pinned")
        if not pinned:
            continue
        pins_checked += 1
        measured = first[rel].get("sha256")
        if measured is None:
            pins_missing.append(rel)
            pin_mismatches.append({"path": rel, "pinned": pinned, "measured": None,
                                   "note": "pinned path missing/unreadable at T0"})
        elif measured != pinned:
            pin_mismatches.append({"path": rel, "pinned": pinned, "measured": measured,
                                   "note": "on-disk bytes differ from FROZEN pin at T0"})

    verdict = "DRIFT" if drift_targets else "QUIESCENT"
    report = {
        "schema_version": "0.1",
        "artifact_type": "freeze_quiescence_witness",
        "task_id": TASK_ID,
        "actor": ACTOR,
        "reviewer": ACTOR,
        "node_ids": NODE_IDS,
        "class_ids": CLASS_IDS,
        "gate": GATE,
        "created_at": now_iso(),
        "authority": (
            "Worker evidence only: no gate verdict, no node status, no validation_status="
            "passed, no edit to any canonical artifact. Controller/leads own all gate moves."
        ),
        "question": (
            "Over the declared wall-clock window, did every canonical content target and "
            "every FROZEN-pinned input hold a single sha256, so that a reviewer verdict bound "
            "now would still bind at the second verdict (directive "
            "audit-direction-freeze-quiescence-20260912T0036)?"
        ),
        "verdict_rule": VERDICT_RULE,
        "window": {
            "window_seconds": args.window,
            "sample_interval_seconds": args.interval,
            "samples": len(samples),
            "t0": samples[0]["at"],
            "t1": samples[-1]["at"],
            "verdict_bearing_paths": len(verdict_paths),
            "aux_paths": len(aux_paths),
        },
        "verdict": verdict,
        "drift_targets": drift_targets,
        "verdict_bearing_targets": verdict_report,
        "aux_targets": aux_report,
        "frozen_pin_check_at_t0": {
            "frozen_path": FROZEN_PATH,
            "frozen_revision": frozen.get("revision") if isinstance(frozen, dict) else None,
            "frozen_at": frozen.get("frozen_at") if isinstance(frozen, dict) else None,
            "files_pins_checked": pins_checked,
            "files_pins_missing": pins_missing,
            "files_pin_mismatches": pin_mismatches,
            "coherent": not pin_mismatches,
        },
        "map_state_at_t0": {
            "path": MAP_PATH,
            "sha256": first[MAP_PATH].get("sha256"),
            "updated_at": map_t0.get("updated_at"),
            "gates": {g.get("gate_id"): g.get("verdict") for g in map_t0.get("gates", [])},
            "numerics_lock": (map_t0.get("numerics_lock") or {}).get("state"),
        },
        "map_state_at_t1": {
            "sha256": last[MAP_PATH].get("sha256"),
            "updated_at": map_t1.get("updated_at") if isinstance(map_t1, dict) else None,
        },
        "interpretation": (
            "QUIESCENT: every verdict-bearing path held one sha256 for the whole window; a "
            "verdict recorded against these hashes was not invalidated by a write inside the "
            "window. DRIFT: at least one path moved; see verdict_bearing_targets[*].changes "
            "for the sample instant, and void any verdict bound to the pre-change hash."
        ),
        "falsifier": (
            "A third party re-running this measurement over an overlapping window who observes "
            "a verdict-bearing sha256 change that this report's samples missed (sampling "
            "granularity) falsifies the QUIESCENT verdict; so does evidence that a listed "
            "path was written between the final sample and this report's recorded hash. A "
            "changed_in_window=true path with no change record falsifies the DRIFT timeline. "
            "Any sha256 in this report that does not reproduce by direct `sha256sum` at the "
            "recorded mtime falsifies the measurement."
        ),
        "non_claims": NON_CLAIMS,
        "exit_code": 0 if verdict == "QUIESCENT" else 3,
    }

    out_path = args.out
    if not out_path.startswith("/"):
        out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), out_path)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, sort_keys=True)
        fh.write("\n")

    summary = {
        "task_id": TASK_ID,
        "verdict": verdict,
        "drift_targets": drift_targets,
        "samples": len(samples),
        "window_seconds": args.window,
        "verdict_bearing_paths": len(verdict_paths),
        "frozen_revision": report["frozen_pin_check_at_t0"]["frozen_revision"],
        "frozen_pin_coherent": report["frozen_pin_check_at_t0"]["coherent"],
        "pin_mismatches": len(pin_mismatches),
        "out": out_path,
    }
    print(json.dumps(summary, indent=1))
    return 0 if verdict == "QUIESCENT" else 3


if __name__ == "__main__":
    sys.exit(main())
