#!/usr/bin/env python3
"""Write CHECKPOINT.json for W036-CLASSSEP-COMPOSE-01 (artifact dir + runtime/state copy).

Hash-pins every deliverable and input with full 64-hex digests.  Does not write any
canonical registry (runtime/state/artifact_hashes.json is controller-owned).
"""
from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
INSTANCE = "worker-036-compose-20260912T010500"


def h(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


def main() -> int:
    report = json.loads((HERE / "report.json").read_text())
    artifacts = {}
    for name in [
        "build_composition.py",
        "make_checkpoint.py",
        "emit_events.py",
        "emit_correction.py",
        "probe_compose.py",
        "candidate_build.json",
        "report.json",
        "README.md",
        "fixtures/compose_fixtures.jsonl",
    ]:
        p = HERE / name
        artifacts[rel(p)] = h(p)
    for p in sorted((HERE / "snapshots").glob("*.py")):
        artifacts[rel(p)] = h(p)
    for p in sorted((HERE / "snapshots").glob("*.json")):
        artifacts[rel(p)] = h(p)
    for p in sorted((HERE / "snapshots").glob("*.jsonl")):
        artifacts[rel(p)] = h(p)

    inputs = {
        "research_map/class_separation.py": h(ROOT / "research_map/class_separation.py"),
        "proposed/class_separation.py": h(ROOT / "proposed/class_separation.py"),
        "artifacts/worker-036/classsep_disj_rule/candidate_class_separation.py": h(
            ROOT / "artifacts/worker-036/classsep_disj_rule/candidate_class_separation.py"),
        "research_map/research_map.json": h(ROOT / "research_map/research_map.json"),
        "ledger/theorems.jsonl": h(ROOT / "ledger/theorems.jsonl"),
        "artifacts/worker-07/class_separation_falsification/results.json": h(
            ROOT / "artifacts/worker-07/class_separation_falsification/results.json"),
        "artifacts/worker-027/classsep_token_binding/ood_corpus/results.json": h(
            ROOT / "artifacts/worker-027/classsep_token_binding/ood_corpus/results.json"),
        "artifacts/worker-085/candidate_diff/report.json": h(
            ROOT / "artifacts/worker-085/candidate_diff/report.json"),
    }
    checks = report["checks"]
    r = report
    ck = {
        "checkpoint_id": "w036-classsep-compose-ckpt-20260912T010500",
        "task_id": r["task_id"],
        "actor": "worker-036",
        "instance": INSTANCE,
        "created_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "node_id": "A1",
        "gate": "G-AUDIT/G-CLASSBIND",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "scope_classes": r["scope_classes"],
        "authority_note": "Worker checkpoint only. No gate verdict, no node status, no canonical artifact or registry modified, no canonical patch applied. A message is not a result until the controller applies it and records the artifact hash.",
        "deliverable": "Two-window composition audit of the staged class-separation candidates (prose-precision e2d24b927ee8 + container-recall 1bc87c9542ed): mechanical 3-way composition, pre-registered compose battery, additivity census, live-surface counterfactuals, rebase hazard measurement, null/overfire controls.",
        "artifacts": artifacts,
        "inputs_pinned_full_sha256": inputs,
        "result": {
            "overall": r["overall"],
            "checks_passed": sum(1 for c in checks if c["ok"]),
            "checks_total": len(checks),
            "probe_exit_expected": 0,
            "composed_c0_sha256": r["revisions"]["PR0"]["sha256"],
            "composed_c1_sha256": r["revisions"]["PR1"]["sha256"],
            "canonical_c0_sha256": r["revisions"]["C0"]["sha256"],
            "canonical_c1_sha256": r["revisions"]["C1"]["sha256"],
            "prose_patch_sha256": r["revisions"]["P"]["sha256"],
            "container_patch_sha256": r["revisions"]["R"]["sha256"],
            "hunk_counts": {"base_c0": r["composition"]["base_c0"]["hunk_counts"],
                            "base_c1": r["composition"]["base_c1"]["hunk_counts"]},
            "rebase_conflicts": {"base_c0": {k: len(v["rebase_conflicts"]) for k, v in r["composition"]["base_c0"]["patches"].items()},
                                 "base_c1": {k: len(v["rebase_conflicts"]) for k, v in r["composition"]["base_c1"]["patches"].items()}},
            "additivity": {w: {"items": r["additivity"][w]["items"],
                               "interaction_count": r["additivity"][w]["interaction_count"],
                               "aggregate_counts": r["additivity"][w]["aggregate_counts"]}
                           for w in ("base_c0", "base_c1")},
            "live_map_totals": {"C0_window": r["map_measurements"]["live_C0_window"]["totals"],
                                "C1_window": r["map_measurements"]["live_C1_window"]["totals"]},
            "live_map_snapshot_sha256": r["map_measurements"]["live_C0_window"]["map_sha256"],
            "live_base_delta_C0_to_C1": [c["measured"] for c in checks if c["id"] == "K6f"][0],
            "naive_reapply_reverted_lines": {k: v["reverts_new_base_lines"]
                                             for k, v in r["composition"]["naive_reapply_hazard"]["measured"].items()},
            "ledger_container_rows": r["ledger_container_rows"],
            "worker_07_regression": r["corpus_regression"]["worker_07"],
            "worker_027_ood_unchanged": (r["corpus_regression"]["worker_027_ood"] or {}).get("per_fixture_identical"),
            "external_controls": {
                "worker085_canonical_match": [c["ok"] for c in checks if c["id"] == "K2a"][0],
                "worker085_prose_match": [c["ok"] for c in checks if c["id"] == "K2b"][0],
                "prior_canonical_match": [c["ok"] for c in checks if c["id"] == "K3a"][0],
                "prior_container_match": [c["ok"] for c in checks if c["id"] == "K3b"][0],
            },
            "controls": r["controls"],
        },
        "limitations": r["limitations"],
        "next_falsifier": "Re-run build_composition.py then probe_compose.py at the pinned snapshots: falsified if any of the 48 checks fails — a window where the composition is not C+P+R (conflict, reverse-apply, delta-union), any item where Counter(PR) != Counter(P)+Counter(R)-Counter(C), any external-control mismatch against worker-085 or the prior packet, any worker-07/OOD classification change, any live added finding not attributable to the patch's own surface, a null control changing a finding, an overfire control failing to break >=5 negatives, a naive 2-way reapply that does NOT revert C1's own edit, or any pinned input drifting mid-run. Rebase window void if research_map/class_separation.py moves off a8c04fc31e4a.",
    }
    out = json.dumps(ck, indent=1) + "\n"
    (HERE / "CHECKPOINT.json").write_text(out)
    state = ROOT / "runtime/state" / "w036_classsep_compose_checkpoint_20260912T010500.json"
    state.write_text(out)
    print(json.dumps({"checkpoint": rel(HERE / "CHECKPOINT.json"), "state_copy": rel(state),
                      "artifacts": len(artifacts), "overall": ck["result"]["overall"],
                      "checks": f"{ck['result']['checks_passed']}/{ck['result']['checks_total']}"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
