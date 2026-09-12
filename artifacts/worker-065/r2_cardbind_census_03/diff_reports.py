#!/usr/bin/env python3
"""W065-R2-CARDBIND-CENSUS-03 helper: deterministic diff of census-03 against census-02.

Reads two census report.json files (same schema) and emits the delta that matters for the
recorded next falsifier: which card-bound verdicts landed between the two cutoffs, whether
the F2a swapped-pair hazard materialised (a path overwrite) or stayed a text hazard, and
which per-target independence fields moved.

Also probes the frozen snapshot for the F2a pair (existence, sha256, mtime) so the
overwrite question is answered from pinned bytes, not from live-tree timing.

Deterministic: same inputs + same --generated-at -> same output. Worker-level measurement
only: no gate verdict, no node status, no validation_status.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path: str):
    with open(path) as fh:
        return json.load(fh)


def index_card_bound(report):
    out = {}
    for b in report.get("card_bound_verdicts", []):
        key = (b.get("file"), b.get("reviewer"), b.get("target_id"), b.get("binding_card"))
        out[key] = b
    return out


def slim(b):
    keep = [
        "file",
        "reviewer",
        "target_id",
        "verdict",
        "binding_card",
        "binding_basis",
        "declared_path_honored",
        "sha256",
        "mtime",
        "created_at",
        "cited_sha256",
    ]
    return {k: b.get(k) for k in keep if k in b}


def target_view(report):
    view = {}
    for t, s in report.get("target_summary", {}).items():
        view[t] = {
            k: s.get(k)
            for k in [
                "live_pin_sha256",
                "reviewers_with_landed_verdicts",
                "independent_verdict_reviewers",
                "independent_verdict_reviewers_citing_live_pin",
                "independent_accept_reviewers",
                "independent_accept_reviewers_citing_live_pin",
                "meets_two_independent_verdicts",
                "meets_two_independent_verdicts_citing_pin",
                "meets_two_independent_accepts",
            ]
        }
    return view


def probe_swap_pair(snapshot: str, base_report, new_report):
    """F2a swapped pair: card audit-r2-F2a-bindchain-worker-046 declares -b (091's base),
    card audit-r2-F2a-bindchain-worker-091 declares -a (046's base). Overwrite = -b sha
    changes from the value recorded at census-02, or -a appears with 046 content."""
    paths = ["reviews/F2a-review-rev27-a.json", "reviews/F2a-review-rev27-b.json"]
    base_b = None
    for b in base_report.get("card_bound_verdicts", []):
        if b.get("file") == "reviews/F2a-review-rev27-b.json":
            base_b = b
            break
    probe = {
        "question": (
            "Between census-02 (cutoff 2026-09-12T00:55:00+08:00) and census-03 "
            "(cutoff 2026-09-12T00:57:00+08:00), did the swapped F2a addendum cards "
            "overwrite each other's declared base path?"
        ),
        "census_02_recorded": {
            "reviews/F2a-review-rev27-b.json": {
                "sha256": (base_b or {}).get("sha256"),
                "mtime": (base_b or {}).get("mtime"),
                "reviewer": (base_b or {}).get("reviewer"),
            },
            "reviews/F2a-review-rev27-a.json": "MISSING at census-02 (declared path not found)",
        },
        "snapshot_probe": {},
        "verdict": None,
    }
    for rel in paths:
        full = os.path.join(snapshot, rel)
        rec = {"exists": os.path.exists(full)}
        if rec["exists"]:
            st = os.stat(full)
            rec.update(
                {
                    "sha256": sha256_file(full),
                    "bytes": st.st_size,
                    "mtime_epoch": st.st_mtime,
                }
            )
        probe["snapshot_probe"][rel] = rec
    b_now = probe["snapshot_probe"]["reviews/F2a-review-rev27-b.json"]
    a_now = probe["snapshot_probe"]["reviews/F2a-review-rev27-a.json"]
    if b_now["exists"] and base_b and b_now.get("sha256") == base_b.get("sha256"):
        probe["verdict"] = "no_overwrite_at_census_03_cutoff"
    elif b_now["exists"] and base_b:
        probe["verdict"] = "OVERWRITE_DETECTED"
    elif not b_now["exists"]:
        probe["verdict"] = "BASE_FILE_MISSING"
    if a_now["exists"]:
        probe["declared_path_a_landed"] = True
    else:
        probe["declared_path_a_landed"] = False
    return probe


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="census-02 report.json")
    ap.add_argument("--new", required=True, help="census-03 report.json")
    ap.add_argument("--snapshot", required=True, help="frozen snapshot the new report ran on")
    ap.add_argument("--out", required=True)
    ap.add_argument("--generated-at", required=True)
    args = ap.parse_args()

    base = load(args.base)
    new = load(args.new)

    base_cards = {c["event_id"]: c for c in base.get("cards", [])}
    new_cards = {c["event_id"]: c for c in new.get("cards", [])}
    base_cb = index_card_bound(base)
    new_cb = index_card_bound(new)

    added = [slim(new_cb[k]) for k in sorted(new_cb, key=lambda x: [str(i) for i in x]) if k not in base_cb]
    removed = [slim(base_cb[k]) for k in sorted(base_cb, key=lambda x: [str(i) for i in x]) if k not in new_cb]
    changed = []
    for k in sorted(set(base_cb) & set(new_cb), key=lambda x: [str(i) for i in x]):
        b, n = base_cb[k], new_cb[k]
        if b.get("sha256") != n.get("sha256") or b.get("verdict") != n.get("verdict") or b.get("mtime") != n.get("mtime"):
            changed.append({"file": k[0], "reviewer": k[1], "target": k[2], "base": slim(b), "new": slim(n)})

    def lset(rep, key):
        return sorted(rep.get(key, []) if isinstance(rep.get(key), list) else sorted(rep.get(key, {}).keys()))

    diff = {
        "schema": "w065-census-diff/1",
        "task_id": "W065-R2-CARDBIND-CENSUS-03",
        "worker": "worker-065",
        "gate": "G-AUDIT",
        "node_id": "A1",
        "class_ids": new.get("class_ids"),
        "created_at": args.generated_at,
        "inputs": {
            "base": {
                "path": args.base,
                "sha256": sha256_file(args.base),
                "task_id": base.get("task_id"),
                "cutoff": base.get("cutoff"),
                "generated_at": base.get("generated_at"),
                "map_sha256": base.get("map", {}).get("sha256"),
            },
            "new": {
                "path": args.new,
                "sha256": sha256_file(args.new),
                "task_id": new.get("task_id"),
                "cutoff": new.get("cutoff"),
                "generated_at": new.get("generated_at"),
                "map_sha256": new.get("map", {}).get("sha256"),
            },
        },
        "card_inventory": {
            "base_cards": len(base_cards),
            "new_cards": len(new_cards),
            "same_ids": sorted(base_cards) == sorted(new_cards),
            "removed_card_ids": sorted(set(base_cards) - set(new_cards)),
            "added_card_ids": sorted(set(new_cards) - set(base_cards)),
            "definition_changes": [
                cid
                for cid in sorted(set(base_cards) & set(new_cards))
                if base_cards[cid] != new_cards[cid]
            ],
        },
        "card_bound_verdicts": {
            "base_count": len(base_cb),
            "new_count": len(new_cb),
            "added": added,
            "removed": removed,
            "changed_same_key": changed,
        },
        "path_binding_delta": {
            "path_collisions": {
                "base": sorted(base.get("path_collisions", {}).keys()),
                "new": sorted(new.get("path_collisions", {}).keys()),
            },
            "missing_declared_paths": {
                "base": base.get("missing_declared_paths"),
                "new": new.get("missing_declared_paths"),
            },
            "declared_path_not_honored": {
                "base": base.get("declared_path_not_honored"),
                "new": new.get("declared_path_not_honored"),
            },
            "unlanded_card_deliverables": {
                "base": base.get("unlanded_card_deliverables"),
                "new": new.get("unlanded_card_deliverables"),
                "resolved": sorted(
                    set(base.get("unlanded_card_deliverables", [])) - set(new.get("unlanded_card_deliverables", []))
                ),
                "newly_unlanded": sorted(
                    set(new.get("unlanded_card_deliverables", [])) - set(base.get("unlanded_card_deliverables", []))
                ),
            },
            "third_party_replications": {
                "base_files": sorted(x.get("file") for x in base.get("third_party_replications", [])),
                "new_files": sorted(x.get("file") for x in new.get("third_party_replications", [])),
            },
        },
        "target_coverage": {
            "base_keys": sorted(base.get("target_summary", {}).keys()),
            "new_keys": sorted(new.get("target_summary", {}).keys()),
            "base": target_view(base),
            "new": target_view(new),
        },
        "swap_pair_probe": probe_swap_pair(args.snapshot, base, new),
        "controls": {
            "base": {"pass": base.get("controls_pass"), "total": base.get("controls_total")},
            "new": {"pass": new.get("controls_pass"), "total": new.get("controls_total")},
        },
        "reading_notes": [
            "Card-bound coverage is a per-(target, reviewer) dedup of landed verdict files bound to a map assignment; it is not a count of independent scientific judgements and not a gate verdict.",
            "The census-03 target key for the N0 rev3 review is the review's pinned artifact id, so N0 coverage appears under 'numerics/results/...' rather than node id 'N0'; this is a key change, not a coverage regression.",
            "census-02's cutoff (00:55:00) predates the F2b-b (00:55:40) and N0-rev3 (00:55:26) landings, which is exactly why census-03 uses cutoff 00:57:00.",
            "All rows and counts are measurements at the recorded cutoff; verdicts landing after the cutoff are excluded by construction.",
        ],
        "non_claims": [
            "Worker-level measurement only: sets no gate verdict, no node status, no validation_status=passed.",
            "Does not rank or endorse any verdict; verdict strings are copied from the review files.",
            "'OVERWRITE_DETECTED' (if present) would be a file-integrity observation, not a bias finding about any reviewer.",
        ],
    }
    with open(args.out, "w") as fh:
        json.dump(diff, fh, indent=1, sort_keys=True)
    print(
        json.dumps(
            {
                "out": args.out,
                "added_card_bound": len(added),
                "removed_card_bound": len(removed),
                "changed_card_bound": len(changed),
                "swap_pair_verdict": diff["swap_pair_probe"]["verdict"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
