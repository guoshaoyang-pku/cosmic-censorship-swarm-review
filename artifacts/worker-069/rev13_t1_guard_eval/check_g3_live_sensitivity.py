#!/usr/bin/env python3
"""Addendum to W069-GFORM-T1-GUARD-REV13-01: G3 sensitivity to post-snapshot map drift.

The binding G3 population is the pinned map snapshot (sha256 262da69798578d77,
updated_at 2026-09-12T00:55:13+08:00). The controller's 15-minute cycle mutates the live
map, so this addendum re-runs the same pre-registered G3 literal reading against the live
map at a recorded instant and reports whether the verdict or population changed. It does
not modify the binding measurement or its hashes.
"""
import hashlib
import importlib.util
import json
import os
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
CST = timezone(timedelta(hours=8))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

spec = importlib.util.spec_from_file_location(
    "t1eval", os.path.join(HERE, "eval_t1_guards_rev13.py"))
t1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(t1)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    snap_path = os.path.join(HERE, "snapshot", "research_map_research_map.json")
    with open(snap_path) as f:
        snap = json.load(f)
    snap_g3 = t1.g3_literal(snap)

    live_path = os.path.join(ROOT, "research_map/research_map.json")
    live_sha = sha256_file(live_path)
    with open(live_path) as f:
        live = json.load(f)
    live_g3 = t1.g3_literal(live)

    changed = (live_g3["verdict"] != snap_g3["verdict"]
               or live_g3["bound_claim_count"] != snap_g3["bound_claim_count"]
               or live_g3["strengthened_qualifying_count"] != snap_g3["strengthened_qualifying_count"])

    out = {
        "task_id": "W069-GFORM-T1-GUARD-REV13-01-addendum-g3-live-sensitivity",
        "actor": "worker-069",
        "generated_at": datetime.now(CST).isoformat(),
        "binding_measurement": {
            "map_snapshot_sha256": "262da69798578d7741e1d66dec3ed977d05c4bef296974c36063cb255bee628c",
            "map_updated_at": snap.get("updated_at"),
            "g3": snap_g3,
        },
        "live_map": {
            "path": "research_map/research_map.json",
            "sha256": live_sha,
            "updated_at": live.get("updated_at"),
            "g3": live_g3,
        },
        "g3_population_changed": bool(changed),
        "verdict_changed": live_g3["verdict"] != snap_g3["verdict"],
        "interpretation": ("G3 literal verdict and population are unchanged under post-snapshot live-map drift"
                           if not changed else
                           "G3 literal verdict or population changed under live-map drift; the binding "
                           "measurement remains the pinned snapshot, and T1 licensing still turns on G1/G2"),
        "authority_note": "Worker measurement only; no gate verdict, node status or validation_status=passed.",
    }
    with open(os.path.join(HERE, "raw", "g3_live_sensitivity.json"), "w") as f:
        json.dump(out, f, indent=1, sort_keys=True)
        f.write("\n")
    print(json.dumps({
        "snapshot_g3": snap_g3["verdict"], "snapshot_bound": snap_g3["bound_claim_count"],
        "live_g3": live_g3["verdict"], "live_bound": live_g3["bound_claim_count"],
        "live_updated_at": live.get("updated_at"), "population_changed": bool(changed),
        "live_map_sha256": live_sha[:12],
    }, indent=1))


if __name__ == "__main__":
    main()
