#!/usr/bin/env python3
"""W065-R2-CARDBIND-CENSUS-02 -- card-bound deliverable binding and per-target
independent-verdict census for the audit-r2 review wave (gate G-AUDIT, node A1).

Worker-level measurement only. This tool sets no gate verdict, no node status and
no validation_status. It is the post-verdict half of W065-R2-INDEP-PREREG-01
(artifacts/worker-065/r2_independence_prereg/): the prereg froze the pre-card
independence classification of the 17 audit-r2 cards; this census binds the
landed verdict files back to those cards, detects declared-deliverable path
collisions, and counts per-target verdicts with the reviewer dedup that the
prereg's next_falsifier demanded.

Deterministic: same --cutoff + same on-disk bytes -> same report.json.

Usage:
  python3 census.py --repo <swarm-root> --cutoff 2026-09-12T01:05:00+08:00 --out report.json
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
import sys
from datetime import datetime

CARD_RE = re.compile(r"audit-r2-[A-Za-z0-9-]+")
HARD_FLAGS = ("A_ASSIGNED", "B_PRIOR_ALIAS_AMBIGUOUS")
TARGETS = ["F0", "F1", "F2a", "F2b", "N0", "A0", "L0"]
REF_KEYS = (
    "assignment_event_id",
    "assignment_ids",
    "assignment_ref",
    "assignment",
    "card_id",
    "assignment_id",
)
SHA_KEYS = ("reviewed_sha256", "artifact_sha256", "reviewed_hashes")
REVIEWER_KEYS = ("reviewer", "actor")
TARGET_KEYS = ("target_id", "node_id")
VERDICT_KEYS = ("verdict", "review_verdict", "decision")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def iso_epoch(ts: str) -> float:
    return datetime.fromisoformat(ts).timestamp()


def parse_iso(value):
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def first(obj: dict, keys):
    for k in keys:
        if k in obj:
            return obj[k]
    return None


def verdict_of(obj: dict):
    v = first(obj, VERDICT_KEYS)
    if isinstance(v, dict):
        nested = v.get("verdict")
        return nested if isinstance(nested, str) else None
    return v if isinstance(v, str) else None


def refs_of(obj: dict):
    out = []
    for k in REF_KEYS:
        v = obj.get(k)
        if isinstance(v, str):
            out.append(v)
        elif isinstance(v, list):
            out.extend(x for x in v if isinstance(x, str))
    return out


def cited_sha(obj: dict):
    """Return (sha256_or_None, basis). Accepts a str or a dict of paths->sha."""
    v = first(obj, SHA_KEYS)
    if isinstance(v, str) and re.fullmatch(r"[0-9a-f]{64}", v):
        return v, "sha256_field"
    if isinstance(v, dict):
        for val in v.values():
            if isinstance(val, str) and re.fullmatch(r"[0-9a-f]{64}", val):
                return val, "sha256_map"
    return None, None


def collect_sha256s(obj, depth=4):
    """All 64-hex strings anywhere in the verdict (bounded depth).

    Needed because verdict files place their pin in different fields
    (`reviewed_sha256`, `artifact_sha256`, `pin.expected`, `reviewed_hashes`,
    bind-chain maps). Pin matching must not depend on one vendor's key choice.
    """
    hits = set()

    def walk(x, d):
        if d > depth:
            return
        if isinstance(x, str):
            hits.update(re.findall(r"(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])", x))
        elif isinstance(x, dict):
            for v in x.values():
                walk(v, d + 1)
        elif isinstance(x, list):
            for v in x:
                walk(v, d + 1)

    walk(obj, 0)
    return hits


def row_sha_set(row):
    if row.get("cited_sha256_all"):
        return set(row["cited_sha256_all"])
    return {row["cited_sha256"]} if row.get("cited_sha256") else set()


# ---------------------------------------------------------------- card loading
def load_cards(map_obj: dict):
    cards = []
    for a in map_obj.get("assignments", []):
        eid = str(a.get("event_id", ""))
        if not eid.startswith("audit-r2"):
            continue
        acceptance = str(a.get("acceptance", "") or "")
        kind = "base"
        if "bindchain" in eid:
            kind = "addendum"
        elif acceptance.upper().startswith("SUPERSEDES"):
            kind = "supersede"
        cards.append(
            {
                "event_id": eid,
                "assignee": a.get("assignee"),
                "node_id": a.get("node_id"),
                "gate": a.get("gate"),
                "class_id": a.get("class_id"),
                "deadline": a.get("deadline"),
                "declared_path": a.get("artifact"),
                "kind": kind,
            }
        )
    return cards


def collision_classes(cards):
    """Group declared deliverables by path and classify each path.

    swapped_pair: exactly two paths between the same two assignees, each holding
    one base card and one addendum, with the addendum assignees exchanged. That
    is the F2a pattern: 046's addendum points at 091's base path and vice versa.
    """
    by_path: dict[str, list] = {}
    for c in cards:
        by_path.setdefault(c["declared_path"], []).append(c)
    out = {}
    for path, group in by_path.items():
        assignees = sorted({c["assignee"] for c in group})
        kinds = sorted({c["kind"] for c in group})
        if len(group) == 1:
            cls = "single_card"
        elif len(assignees) == 1:
            cls = "same_assignee_sequential"  # base + own addendum, or supersede
        else:
            cls = "cross_assignee_collision"
        out[path] = {
            "classification": cls,
            "cards": [
                {"event_id": c["event_id"], "assignee": c["assignee"], "kind": c["kind"]}
                for c in group
            ],
            "assignees": assignees,
            "kinds": kinds,
        }

    def swap_roles(group):
        base = [c for c in group["cards"] if c["kind"] == "base"]
        add = [c for c in group["cards"] if c["kind"] == "addendum"]
        return base, add

    paths = sorted(out)
    for i, p1 in enumerate(paths):
        for p2 in paths[i + 1:]:
            g1, g2 = out[p1], out[p2]
            if g1["classification"] != "cross_assignee_collision":
                continue
            if g2["classification"] != "cross_assignee_collision":
                continue
            if set(g1["assignees"]) != set(g2["assignees"]) or len(g1["assignees"]) != 2:
                continue
            b1, a1 = swap_roles(g1)
            b2, a2 = swap_roles(g2)
            if len(b1) == 1 and len(a1) == 1 and len(b2) == 1 and len(a2) == 1:
                if (b1[0]["assignee"] == a2[0]["assignee"]
                        and b2[0]["assignee"] == a1[0]["assignee"]
                        and b1[0]["assignee"] != a1[0]["assignee"]):
                    out[p1]["classification"] = "swapped_pair"
                    out[p2]["classification"] = "swapped_pair"
    return out


# ------------------------------------------------------------------ binding
def bind_verdict_files(repo: str, cards, cutoff_epoch: float, cutoff_dt):
    """Return (bound_rows, third_party_rows, excluded_rows, scanned_rows).

    A verdict is card-bound only when (a) it explicitly names a card id AND its
    reviewer is that card's assignee, or (b) it sits at a card's declared path
    and its reviewer is that card's assignee. A file that self-claims a card but
    was written by someone else is recorded as a third-party replication and
    counts toward no card's coverage (F2b-088 pattern).
    """
    by_id = {c["event_id"]: c for c in cards}
    by_path: dict[str, list] = {}
    for c in cards:
        by_path.setdefault(c["declared_path"], []).append(c)

    bound, third_party, excluded, scanned = [], [], [], []
    for path in sorted(glob.glob(os.path.join(repo, "reviews", "*.json"))):
        st = os.stat(path)
        rel = os.path.relpath(path, repo)
        rec = {
            "file": rel,
            "mtime": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
            "mtime_epoch": st.st_mtime,
            "sha256": sha256_file(path),
        }
        if st.st_mtime > cutoff_epoch:
            rec["exclusion"] = "mtime_after_cutoff"
            excluded.append(rec)
            continue
        try:
            obj = json.load(open(path))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            rec["exclusion"] = f"unparseable_json:{type(exc).__name__}"
            excluded.append(rec)
            continue
        if not isinstance(obj, dict):
            rec["exclusion"] = "not_a_json_object"
            excluded.append(rec)
            continue
        rec["created_at"] = obj.get("created_at")
        created = parse_iso(obj.get("created_at"))
        if created is not None and created.timestamp() > cutoff_epoch + 1:
            rec["exclusion"] = "created_at_after_cutoff"
            rec["clock_skew_seconds"] = round(created.timestamp() - cutoff_epoch, 1)
            excluded.append(rec)
            continue

        reviewer = first(obj, REVIEWER_KEYS)
        target = first(obj, TARGET_KEYS)
        cited, cited_basis = cited_sha(obj)
        raw_refs = refs_of(obj)
        tokens = []
        for r in raw_refs:
            tokens.extend(CARD_RE.findall(r))
        matched_ids = sorted({t for t in tokens if t in by_id})
        path_cards = by_path.get(rel, [])
        path_assignee_match = [c for c in path_cards if c["assignee"] == reviewer]
        own = own_card_ids(matched_ids, cards, reviewer)

        binding, basis = None, None
        if own:
            binding = by_id[max(own, key=len)]
            basis = "explicit_assignment_ref"
        elif len(path_assignee_match) == 1:
            binding = path_assignee_match[0]
            basis = "declared_path+reviewer==assignee"
        rec.update(
            {
                "reviewer": reviewer,
                "target_id": target or (binding["node_id"] if binding else None),
                "verdict": verdict_of(obj),
                "cited_sha256": cited,
                "cited_sha256_all": sorted(collect_sha256s(obj)),
                "cited_basis": cited_basis,
                "matched_card_ids": matched_ids,
                "declared_path_cards": [c["event_id"] for c in path_cards],
                "binding_card": binding["event_id"] if binding else None,
                "binding_basis": basis,
            }
        )
        if binding is not None:
            rec["card"] = binding
            rec["declared_path_honored"] = rel == binding["declared_path"]
            bound.append(rec)
        elif matched_ids or path_cards:
            rec["exclusion"] = "self_claimed_card_but_reviewer_is_not_a_card_assignee"
            rec["claimed_cards"] = matched_ids
            rec["claimed_by_other_assignees"] = sorted(
                {by_id[c]["assignee"] for c in matched_ids} | {c["assignee"] for c in path_cards}
            )
            third_party.append(rec)
        else:
            rec["exclusion"] = "not_bound_to_an_audit-r2_card"
            excluded.append(rec)
        scanned.append(rec)
    return bound, third_party, excluded, scanned


# ------------------------------------------------------------- independence
def count_independence(bound_rows, prereg_flags):
    """Dedup card-bound verdicts by (target, reviewer) and count accepts.

    hard-flagged reviewers are still counted in `dedup_accept_reviewers` (they
    reviewed) but excluded from `independent_accept_reviewers`.
    """
    groups: dict[tuple, dict] = {}
    for r in bound_rows:
        target = r["target_id"] or (r["card"]["node_id"] if r.get("card") else None)
        key = (target, r["reviewer"])
        g = groups.setdefault(
            key,
            {
                "target": target,
                "reviewer": r["reviewer"],
                "files": [],
                "verdicts": [],
                "cited_sha256": set(),
                "cards": set(),
                "basis": set(),
            },
        )
        g["files"].append(r["file"])
        if r["verdict"]:
            g["verdicts"].append(r["verdict"])
        if row_sha_set(r):
            g["cited_sha256"].update(row_sha_set(r))
        g["cards"].add(r["binding_card"])
        g["basis"].add(r["binding_basis"])

    rows = []
    for (target, reviewer), g in sorted(groups.items()):
        flags = prereg_flags.get((reviewer, target), "")
        hard = [f for f in HARD_FLAGS if f in flags]
        uniq = set(g["verdicts"])
        if not uniq:
            consolidated = None
        elif uniq == {"accept"}:
            consolidated = "accept"
        elif len(uniq) > 1:
            consolidated = "conflict:" + "+".join(sorted(uniq))
        else:
            consolidated = next(iter(uniq))
        rows.append(
            {
                "target": target,
                "reviewer": reviewer,
                "files": sorted(g["files"]),
                "raw_verdicts": g["verdicts"],
                "consolidated_verdict": consolidated,
                "duplicate_files_for_same_reviewer_target": len(g["files"]) - 1,
                "cited_sha256": sorted(g["cited_sha256"]),
                "cards": sorted(g["cards"]),
                "binding_basis": sorted(g["basis"]),
                "prereg_classification": flags or None,
                "hard_flags": hard,
                "counts_as_independent": not hard,
            }
        )
    return rows


def own_card_ids(matched_ids, cards, reviewer):
    """Card ids the reviewer is actually the assignee of (third-party filter)."""
    by_id = {c["event_id"]: c for c in cards}
    return [cid for cid in matched_ids if cid in by_id and by_id[cid]["assignee"] == reviewer]


def target_summary(indep_rows, cards, target_pins):
    cards_by_target: dict[str, list] = {}
    for c in cards:
        cards_by_target.setdefault(c["node_id"], []).append(c)
    out = {}
    for target in sorted(set(list(cards_by_target) + [r["target"] for r in indep_rows])):
        rs = [r for r in indep_rows if r["target"] == target]
        accepts = [r for r in rs if r["consolidated_verdict"] == "accept"]
        indep = [r for r in rs if r["counts_as_independent"]]
        indep_accepts = [r for r in accepts if r["counts_as_independent"]]
        pin = target_pins.get(target, {})
        pin_sha = pin.get("sha256")

        def cites_pin(r):
            return bool(pin_sha) and pin_sha in r["cited_sha256"]

        indep_citing = [r for r in indep if cites_pin(r)]
        indep_accepts_citing = [r for r in indep_accepts if cites_pin(r)]
        out[target] = {
            "live_pin_sha256": pin_sha,
            "cards_declared": [c["event_id"] for c in cards_by_target.get(target, [])],
            "reviewers_with_landed_verdicts": sorted({r["reviewer"] for r in rs}),
            "dedup_verdict_reviewers": len(rs),
            "dedup_accept_reviewers": len(accepts),
            "independent_verdict_reviewers": sorted({r["reviewer"] for r in indep}),
            "independent_accept_reviewers": sorted({r["reviewer"] for r in indep_accepts}),
            "independent_verdict_reviewers_citing_live_pin": sorted(
                {r["reviewer"] for r in indep_citing}
            ),
            "independent_accept_reviewers_citing_live_pin": sorted(
                {r["reviewer"] for r in indep_accepts_citing}
            ),
            "meets_two_independent_verdicts": len({r["reviewer"] for r in indep}) >= 2,
            "meets_two_independent_accepts": len({r["reviewer"] for r in indep_accepts}) >= 2,
            "meets_two_independent_verdicts_citing_pin": len(
                {r["reviewer"] for r in indep_citing}
            ) >= 2,
            "pin_cited_by": {r["reviewer"]: cites_pin(r) for r in rs},
            "cited_sha256_count_by_reviewer": {
                r["reviewer"]: len(r["cited_sha256"]) for r in rs
            },
        }
    return out


# ---------------------------------------------------------------- controls
def run_controls(cards, prereg_flags):
    """Five synthetic controls exercising the same functions as the main path."""
    ctl = []

    def rec(cid, expect, got, ok, note=""):
        ctl.append({"id": cid, "expect": expect, "got": got, "pass": bool(ok), "note": note})

    # C1: duplicate accept file, same reviewer+target -> one dedup accept, one raw extra file
    dup = [
        {"target_id": "F1", "reviewer": "worker-071", "file": "a.json", "verdict": "accept",
         "cited_sha256": "x", "binding_card": "audit-r2-F1-a", "binding_basis": "explicit"},
        {"target_id": "F1", "reviewer": "worker-071", "file": "b.json", "verdict": "accept",
         "cited_sha256": "x", "binding_card": "audit-r2-F1-bindchain-worker-071",
         "binding_basis": "explicit"},
    ]
    rows = count_independence(dup, prereg_flags)
    rec("C1_duplicate_accept_same_reviewer", "1 dedup accept, duplicates=1",
        f"{len(rows)} row, dup={rows[0]['duplicate_files_for_same_reviewer_target']}",
        len(rows) == 1 and rows[0]["duplicate_files_for_same_reviewer_target"] == 1)

    # C2: A_ASSIGNED reviewer accept -> dedup accept yes, independent accept no
    flags2 = dict(prereg_flags)
    flags2[("N0", "worker-012")] = "A_ASSIGNED"
    flagged = [{"target_id": "N0", "reviewer": "worker-012", "file": "c.json",
                "verdict": "accept", "cited_sha256": "y", "binding_card": "audit-r2-N0",
                "binding_basis": "explicit"}]
    rows2 = count_independence(flagged, flags2)
    rec("C2_flagged_reviewer_excluded_from_independent",
        "dedup accept=1, independent=0",
        f"dedup={rows2[0]['consolidated_verdict']}, indep={rows2[0]['counts_as_independent']}",
        rows2[0]["consolidated_verdict"] == "accept" and not rows2[0]["counts_as_independent"])

    # C3: accept + revise from one reviewer on one target -> conflict, not an accept
    conflict = [
        {"target_id": "F2a", "reviewer": "worker-091", "file": "d.json", "verdict": "accept",
         "cited_sha256": "z", "binding_card": "audit-r2-F2a-b", "binding_basis": "explicit"},
        {"target_id": "F2a", "reviewer": "worker-091", "file": "e.json", "verdict": "revise",
         "cited_sha256": "z", "binding_card": "audit-r2-F2a-bindchain-worker-091",
         "binding_basis": "explicit"},
    ]
    rows3 = count_independence(conflict, prereg_flags)
    rec("C3_conflicting_verdicts_same_reviewer", "conflict, not accept",
        rows3[0]["consolidated_verdict"],
        str(rows3[0]["consolidated_verdict"]).startswith("conflict"))

    # C4: cross-assignee path collision is classified (synthetic swapped pair)
    syn = [
        {"event_id": "audit-r2-X-a", "assignee": "wA", "node_id": "X", "kind": "base",
         "declared_path": "p_a"},
        {"event_id": "audit-r2-X-bindchain-wA", "assignee": "wA", "node_id": "X",
         "kind": "addendum", "declared_path": "p_b"},
        {"event_id": "audit-r2-X-b", "assignee": "wB", "node_id": "X", "kind": "base",
         "declared_path": "p_b"},
        {"event_id": "audit-r2-X-bindchain-wB", "assignee": "wB", "node_id": "X",
         "kind": "addendum", "declared_path": "p_a"},
    ]
    cls = collision_classes(syn)
    rec("C4_swapped_pair_detected", "swapped_pair on both paths",
        f"{cls['p_a']['classification']}/{cls['p_b']['classification']}",
        cls["p_a"]["classification"] == "swapped_pair"
        and cls["p_b"]["classification"] == "swapped_pair")

    # C5: same-assignee base+addendum must NOT be a collision
    syn2 = [
        {"event_id": "audit-r2-Y-a", "assignee": "wA", "node_id": "Y", "kind": "base",
         "declared_path": "q"},
        {"event_id": "audit-r2-Y-bindchain-wA", "assignee": "wA", "node_id": "Y",
         "kind": "addendum", "declared_path": "q"},
    ]
    cls2 = collision_classes(syn2)
    rec("C5_same_assignee_not_collision", "same_assignee_sequential",
        cls2["q"]["classification"],
        cls2["q"]["classification"] == "same_assignee_sequential")

    # C6: a self-claimed card written by a non-assignee is filtered out
    real = own_card_ids(
        ["audit-r2-F2b-a", "audit-r2-F2b-b", "not-a-card"], cards, "worker-088"
    )
    rec("C6_third_party_not_own_card", "[] for non-assignee",
        json.dumps(real), real == [])
    return ctl


# -------------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--cutoff", required=True, help="ISO-8601, e.g. 2026-09-12T01:05:00+08:00")
    ap.add_argument("--out", default="report.json")
    ap.add_argument("--generated-at", default=None,
                    help="override generated_at for byte-reproducibility checks")
    ap.add_argument("--prereg",
                    default="artifacts/worker-065/r2_independence_prereg/prereg.json")
    args = ap.parse_args(argv)

    repo = os.path.abspath(args.repo)
    cutoff_dt = datetime.fromisoformat(args.cutoff)
    cutoff_epoch = cutoff_dt.timestamp()

    prereg_path = os.path.join(repo, args.prereg)
    prereg = json.load(open(prereg_path))
    prereg_sha = sha256_file(prereg_path)

    map_path = os.path.join(repo, "research_map", "research_map.json")
    map_sha = sha256_file(map_path)
    map_obj = json.load(open(map_path))
    gates = {g.get("gate_id"): g for g in map_obj.get("gates", [])}

    cards = load_cards(map_obj)
    collisions = collision_classes(cards)

    prereg_flags = {}
    for row in prereg.get("rows", []):
        card = row.get("card", {})
        prereg_flags[(card.get("reviewer"), card.get("node_id"))] = row.get(
            "classification", ""
        )

    target_pins = {t: v for t, v in prereg.get("target_hashes", {}).items()
                   if isinstance(v, dict)}

    bound, third_party, excluded, scanned = bind_verdict_files(
        repo, cards, cutoff_epoch, cutoff_dt
    )
    indep_rows = count_independence(bound, prereg_flags)
    summary = target_summary(indep_rows, cards, target_pins)
    controls = run_controls(cards, prereg_flags)

    # card coverage: declared vs landed (a card lands if it is named by a verdict
    # whose reviewer is that card's assignee, whether or not it is the binding card)
    landed_cards = set()
    for r in bound:
        landed_cards.add(r["binding_card"])
        landed_cards.update(own_card_ids(r["matched_card_ids"], cards, r["reviewer"]))
    landed_cards = sorted(landed_cards)
    unlanded = [
        c["event_id"] for c in cards
        if c["event_id"] not in landed_cards and c["kind"] != "supersede"
    ]
    path_not_honored = [
        {"file": r["file"], "card": r["binding_card"],
         "declared_path": r["card"]["declared_path"]}
        for r in bound if not r.get("declared_path_honored", True)
    ]
    missing_paths = [
        p for p, info in sorted(collisions.items()) if not os.path.exists(os.path.join(repo, p))
    ]

    report = {
        "task_id": "W065-R2-CARDBIND-CENSUS-02",
        "worker": "worker-065",
        "gate": "G-AUDIT",
        "node_id": "A1",
        "class_ids": [
            "AF-WCC-VAC-GEN",
            "AF-SCC-C2-VAC-GEN",
            "AF-SCC-C0-VAC-GEN",
            "AF-WCC-SCALAR-SPH",
        ],
        "generated_at": args.generated_at or datetime.now().isoformat(timespec="seconds"),
        "cutoff": cutoff_dt.isoformat(),
        "predecessor_task": "W065-R2-INDEP-PREREG-01",
        "prereg": {"path": args.prereg.replace(os.sep, "/"), "sha256": prereg_sha,
                   "pinned_sha256": "023d18b4cfb6223af563555c1a070790b0bb32dc13fce066c0a4a4113f3e43af",
                   "pinned_match": prereg_sha
                   == "023d18b4cfb6223af563555c1a070790b0bb32dc13fce066c0a4a4113f3e43af"},
        "map": {"path": "research_map/research_map.json", "sha256": map_sha,
                "updated_at": map_obj.get("updated_at")},
        "gate_criteria_read": {
            gid: {"scope": g.get("scope"), "verdict": g.get("verdict"),
                  "criteria": g.get("criteria")}
            for gid, g in sorted(gates.items())
            if gid in ("G-F0", "G-FORM", "G-AUDIT")
        },
        "cards": cards,
        "declared_path_binding": collisions,
        "path_collisions": {
            p: v for p, v in sorted(collisions.items())
            if v["classification"] in ("cross_assignee_collision", "swapped_pair")
        },
        "missing_declared_paths": missing_paths,
        "unlanded_card_deliverables": unlanded,
        "declared_path_not_honored": path_not_honored,
        "scanned_review_files": scanned,
        "excluded_review_files": excluded,
        "third_party_replications": third_party,
        "card_bound_verdicts": bound,
        "independence_rows": indep_rows,
        "target_summary": summary,
        "controls": controls,
        "controls_pass": sum(1 for c in controls if c["pass"]),
        "controls_total": len(controls),
        "non_claims": [
            "Worker-level measurement only: sets no gate verdict, no node status, no "
            "validation_status=passed, and does not edit any reviewed artifact.",
            "`counts_as_independent` is a procedural pre-card involvement test inherited "
            "from the frozen prereg, not proof of bias and not a verdict on any review.",
            "Path-collision classes describe the map assignment text at the measured map "
            "hash; they are not claims about what any worker actually wrote.",
            "Verdicts after the cutoff are excluded by construction; re-run with a later "
            "--cutoff for an updated census.",
        ],
        "falsifier": (
            "Falsified if, at this cutoff, (a) any path classified swapped_pair or "
            "cross_assignee_collision resolves to one card or one assignee on re-reading "
            "map.assignments at the recorded map sha256; or (b) any reviewer counted in "
            "independent_* carries A_ASSIGNED or B_PRIOR_ALIAS_AMBIGUOUS for that target "
            "in the frozen prereg; or (c) any reviewer listed in an "
            "independent_*_citing_live_pin field lacks its target's live pin sha256 in its "
            "cited_sha256; or (d) "
            "re-running census.py --cutoff <recorded> --generated-at <recorded> on unchanged "
            "bytes does not reproduce report.json modulo the --out path."
        ),
        "run_controls_summary": {
            "pass": sum(1 for c in controls if c["pass"]),
            "total": len(controls),
        },
    }

    # honesty guard: the report must not claim success if controls fail
    if report["controls_pass"] != report["controls_total"]:
        report["status"] = "CONTROL_FAILURE"
    else:
        report["status"] = "MEASURED"

    with open(args.out, "w") as fh:
        json.dump(report, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(json.dumps({
        "status": report["status"],
        "controls": f"{report['controls_pass']}/{report['controls_total']}",
        "card_bound_verdicts": len(bound),
        "third_party_replications": len(third_party),
        "scanned": len(scanned),
        "excluded": len(excluded),
        "path_collisions": len(report["path_collisions"]),
        "missing_declared_paths": missing_paths,
        "unlanded_card_deliverables": unlanded,
        "declared_path_not_honored": path_not_honored,
        "target_summary": {
            t: {"indep": v["independent_verdict_reviewers"],
                "indep_citing_pin": v["independent_verdict_reviewers_citing_live_pin"],
                "indep_accepts": v["independent_accept_reviewers"],
                "two_accepts": v["meets_two_independent_accepts"],
                "two_citing_pin": v["meets_two_independent_verdicts_citing_pin"]}
            for t, v in summary.items()},
        "out": args.out,
    }, indent=1))
    return 0 if report["status"] == "MEASURED" else 1


if __name__ == "__main__":
    sys.exit(main())
