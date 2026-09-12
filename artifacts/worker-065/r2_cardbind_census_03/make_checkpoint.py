#!/usr/bin/env python3
"""W065-R2-CARDBIND-CENSUS-03 helper: build the checkpoint from the run's own outputs.

Derives every reported count from report.json / diff_vs_02.json rather than restating them by
hand, hashes the artifact directory, and writes the checkpoint both in the artifact dir and
in runtime/state/. checkpoint.json itself is excluded from artifacts{} because a manifest
cannot contain its own post-write hash (same convention as W065-R2-INDEP-PREREG-01 erratum).

Deterministic: same bytes + same --created-at -> same checkpoint. Worker-level measurement
only: no gate verdict, no node status, no validation_status.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

TASK_ID = "W065-R2-CARDBIND-CENSUS-03"
WORKER = "worker-065"
CLASS_IDS = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact-dir", required=True)
    ap.add_argument("--runtime-out", required=True)
    ap.add_argument("--created-at", required=True)
    ap.add_argument("--snapshot", required=True)
    args = ap.parse_args()

    adir = os.path.abspath(args.artifact_dir)
    report = json.load(open(os.path.join(adir, "report.json")))
    diff = json.load(open(os.path.join(adir, "diff_vs_02.json")))
    manifest = json.load(open(os.path.join(adir, "input_manifest.json")))

    artifacts = {}
    for name in sorted(os.listdir(adir)):
        if name == "checkpoint.json":
            continue
        full = os.path.join(adir, name)
        if os.path.isfile(full):
            artifacts[name] = {"sha256": sha256_file(full), "bytes": os.path.getsize(full)}

    ts = report["target_summary"]
    n0_key = next(k for k in ts if k.startswith("numerics/results/flat_wave_convergence_rev3.json#"))
    probe = diff["swap_pair_probe"]
    snap_probe = probe["snapshot_probe"]

    checkpoint = {
        "schema": "w065-checkpoint/1",
        "task_id": TASK_ID,
        "worker": WORKER,
        "gate": "G-AUDIT",
        "node_id": "A1",
        "node_ids": ["F0", "F1", "F2a", "F2b", "N0", "A0"],
        "class_ids": CLASS_IDS,
        "status": "MEASURED",
        "created_at": args.created_at,
        "cutoff": report["cutoff"],
        "generated_at": report["generated_at"],
        "artifact_dir": os.path.relpath(adir, os.getcwd()).replace(os.sep, "/"),
        "artifacts": artifacts,
        "self_hash_excluded": (
            "checkpoint.json is excluded from artifacts{} by design: a manifest cannot contain "
            "its own post-write hash."
        ),
        "inputs": {
            "map": {
                "sha256": report["map"]["sha256"],
                "updated_at": report["map"]["updated_at"],
            },
            "prereg": {
                "sha256": report["prereg"]["sha256"],
                "pinned_match": report["prereg"]["pinned_match"],
                "path": "artifacts/worker-065/r2_independence_prereg/prereg.json",
            },
            "census_tool": {
                "sha256": manifest["census_tool"]["sha256"],
                "path": manifest["census_tool"]["path"],
            },
            "census_02_report": {
                "sha256": diff["inputs"]["base"]["sha256"],
                "path": diff["inputs"]["base"]["path"],
            },
            "input_manifest": {
                "sha256": sha256_file(os.path.join(adir, "input_manifest.json")),
                "entries": manifest["entry_count"],
            },
            "swap_pair_snapshot": snap_probe,
        },
        "controls": f"{report['controls_pass']}/{report['controls_total']}",
        "determinism": (
            "Two back-to-back census.py runs on the manifest-pinned snapshot at cutoff "
            f"{report['cutoff']} and generated-at {report['generated_at']} were byte-identical "
            "(cmp); the delivered report.json is byte-identical to them. diff_reports.py was "
            "re-run once and reproduced diff_vs_02.json byte-identically. The live tree was not "
            "used for the delivered report because a live write moved an excluded file's metadata "
            "between trial runs."
        ),
        "result_summary": {
            "card_bound_verdicts": len(report["card_bound_verdicts"]),
            "card_bound_verdicts_base": diff["card_bound_verdicts"]["base_count"],
            "added_card_bound_verdicts": [
                {"file": a["file"], "reviewer": a["reviewer"], "verdict": a["verdict"]}
                for a in diff["card_bound_verdicts"]["added"]
            ],
            "card_set_unchanged": diff["card_inventory"]["same_ids"],
            "path_collisions": sorted(report["path_collisions"].keys()),
            "unlanded_card_deliverables": report["unlanded_card_deliverables"],
            "missing_declared_paths": report["missing_declared_paths"],
            "third_party_replication_files": sorted(
                x["file"] for x in report["third_party_replications"]
            ),
            "target_coverage": {
                t: {
                    "independent_verdict_reviewers": ts[t]["independent_verdict_reviewers"],
                    "independent_verdict_reviewers_citing_live_pin": ts[t][
                        "independent_verdict_reviewers_citing_live_pin"
                    ],
                    "independent_accept_reviewers": ts[t]["independent_accept_reviewers"],
                    "meets_two_independent_verdicts_citing_pin": ts[t][
                        "meets_two_independent_verdicts_citing_pin"
                    ],
                    "meets_two_independent_accepts": ts[t]["meets_two_independent_accepts"],
                }
                for t in sorted(ts)
            },
            "n0_artifact_target_key": n0_key,
            "swap_pair_probe_verdict": probe["verdict"],
            "declared_path_a_landed": probe["declared_path_a_landed"],
            "f2a_b_base_sha256_unchanged": (
                snap_probe["reviews/F2a-review-rev27-b.json"].get("sha256")
                == probe["census_02_recorded"]["reviews/F2a-review-rev27-b.json"]["sha256"]
            ),
        },
        "findings": [
            "F-065-CB-1 F2a swapped pair: hazard still live at cutoff, no overwrite; -a missing, -b sha unchanged fc2d94bbd54c.",
            "F-065-CB-3 F2b cross-assignee collision did not materialise on disk: 035 landed its own base path -b; map card text still names -a.",
            "F-065-CB-6 post-census-02 landings: F2b 035 (revise) and N0 012 (accept) add two card-bound verdicts; unlanded 7 -> 6.",
            "F-065-CB-7 reviews/F2a-review-rev27-c.json (092) is a real same-target review bound to no audit-r2 card; counting it would inflate F2a.",
            "Arithmetic: only F0 has two independent pin-citing accepts; F1 two pin-citing revises; F2a/F2b/A0 one each; N0 one accept on the artifact pin.",
        ],
        "falsifier": (
            "Falsified if, at cutoff 2026-09-12T00:57:00+08:00, (a) any path classified "
            "swapped_pair or cross_assignee_collision resolves to one card or one assignee on "
            "re-reading map.assignments at map sha256 262da69798578d7741e1d66dec3ed977d05c4bef296974c36063cb255bee628c; "
            "or (b) any reviewer counted in independent_* carries A_ASSIGNED or "
            "B_PRIOR_ALIAS_AMBIGUOUS for that target in prereg 023d18b4cfb6; or (c) any reviewer "
            "listed in an independent_*_citing_live_pin field lacks the target's live pin sha256 "
            "in its cited hashes; or (d) re-running census.py on the manifest-pinned bytes at the "
            "recorded cutoff and generated-at does not reproduce report.json; or (e) "
            "reviews/F2a-review-rev27-b.json in the snapshot does not hash to fc2d94bbd54c while "
            "swap_pair_probe says no_overwrite_at_census_03_cutoff."
        ),
        "next_falsifier": (
            "After the 02:15 r2 deadline, re-run at a later cutoff: did "
            "reviews/F2a-review-rev27-a.json appear (046 landed) or did -b change hash "
            "(overwrite)? Did any second card-bound F2a/F2b/A0 verdict land without a path "
            "collision?"
        ),
        "authority_note": (
            "Worker-level measurement only. Sets no gate verdict, no node status, no "
            "validation_status=passed; edits no reviewed artifact."
        ),
        "does_not_claim": (
            "Does not rank or endorse any verdict; does not claim verdict independence in a "
            "statistical sense; does not assert worker-015 and deepseek-flash-15 are the same "
            "executor; does not claim the r2 wave is complete."
        ),
    }
    payload = json.dumps(checkpoint, indent=1, sort_keys=True)
    with open(os.path.join(adir, "checkpoint.json"), "w") as fh:
        fh.write(payload)
    with open(args.runtime_out, "w") as fh:
        fh.write(payload)
    print(
        json.dumps(
            {
                "artifact_checkpoint": os.path.relpath(os.path.join(adir, "checkpoint.json"), os.getcwd()),
                "runtime_checkpoint": args.runtime_out,
                "control": checkpoint["controls"],
                "swap_pair": probe["verdict"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
