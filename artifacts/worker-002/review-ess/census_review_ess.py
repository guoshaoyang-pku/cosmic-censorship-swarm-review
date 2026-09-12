#!/usr/bin/env python3
"""W002-REVIEW-ESS-01 -- independent review-independence (Kish ESS) census.

Task (bounded, class-bound, read-only on every canonical path):
  The map/protocol require "two independent reviewer verdicts" per target (G-F0,
  G-FORM, G-AUDIT) and comms/PROTOCOL.md + reviews/INDEX.md require that a set of
  reviews sharing a text or a template be collapsed by Kish effective sample size
  (ESS). No instrument measured that collapse on the live review corpus. This one does.

What it measures (measurement only; it sets no gate verdict and no node status):
  1. The review corpus = map.reviews (accepted review events) + review events present
     in comms/outbox/*.jsonl but not yet ingested into the map snapshot (pending_ingest).
  2. Per target (F0/F1/F2a/F2b/L0/L1/A0 + class-id aliases): verdict counts, raw
     distinct reviewer identities, verdicts bound to the LIVE canonical sha256, and
     near-duplicate clusters of review text (normalized 4-gram shingles, Jaccard).
  3. Kish ESS = (sum n_c)^2 / sum n_c^2 over the text clusters, for all verdicts and
     for accepts bound to the live hash. This is the effective number of independent
     verdicts after removing template/duplicate dependence.
  4. Drift guard: every target hash is measured before and after the scan; if any
     changed, binding_valid=false and exit 2 (fail closed).

Reviewer identity is taken from the `reviewer` field when present (the map sometimes
re-emits a reviewer's verdict under a different `actor`, e.g. lead-authored review
events that carry reviewer="deepseek-flash-16 (...)"), else from `actor`. Both raw and
canonical counts are reported; the canonical identity is what dedup uses.

Determinism: stdlib only, no network, no clock dependence inside the measurement.
Controls: C1..C7 synthetic corpora with known ESS + threshold sweep + in-process
re-run digest.

Usage:
  python3 census_review_ess.py [--map research_map/research_map.json] \
      [--out artifacts/worker-002/review-ess] [--threshold 0.5] [--quiet]
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

SCHEMA_VERSION = "0.1"
TASK_ID = "W002-REVIEW-ESS-01"
ACTOR = "worker-002"
CLASS_IDS = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]

# canonical target files, live-hash pinned at scan time
TARGET_FILES = {
    "F0": "research_map/formulation_taxonomy.yaml",
    "F1": "schemas/af_wcc_vacuum.yaml",
    "F2a": "schemas/af_scc_c2_vacuum.yaml",
    "F2b": "schemas/af_scc_c0_vacuum.yaml",
    "L0": "ledger/theorems.jsonl",
    "L1": "ledger/citation_audit.csv",
    "A0": "evaluation_rubric.yaml",
}
CLASS_ALIAS = {
    "AF-WCC-VAC-GEN": "F1",
    "AF-SCC-C2-VAC-GEN": "F2a",
    "AF-SCC-C0-VAC-GEN": "F2b",
    "AF-WCC-SCALAR-SPH": "N0",
}
AXES = ["family", "matter_model", "symmetry", "asymptotics", "regularity_token",
        "genericity_kind", "conclusion_type"]

# text fields that carry a review's substance (metadata excluded on purpose)
TEXT_KEYS = [
    "statement", "summary", "note", "notes", "delta_vs_draft", "reason", "rationale",
    "findings", "hard_failures", "does_not_claim", "next_falsifier", "falsifier",
    "observations", "detail", "details", "comment", "comments", "description",
]
# fields scanned for cited hashes
HASH_FIELDS = [
    "evidence_refs", "artifact", "artifacts", "artifact_refs", "artifact_path",
    "artifact_sha256", "sha256", "target_path", "reviewed_sha256", "path", "paths",
    "target_id", "supersedes", "reviewed", "measured_hashes", "binding",
]
HEX_RE = re.compile(r"\b[0-9a-fA-F]{8,64}\b")
WORD_RE = re.compile(r"[a-z0-9<>]+")


# --------------------------------------------------------------------------- utils
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def measure_targets(root: Path) -> dict:
    out = {}
    for tgt, rel in TARGET_FILES.items():
        p = root / rel
        if p.exists():
            b = p.read_bytes()
            st = p.stat()
            out[tgt] = {
                "path": rel,
                "sha256": sha256_bytes(b),
                "bytes": len(b),
                "mtime_epoch": int(st.st_mtime),
            }
        else:
            out[tgt] = {"path": rel, "sha256": None, "missing": True}
    return out


def iter_text(value):
    """Yield every string in an arbitrarily nested JSON value."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from iter_text(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            yield from iter_text(v)


def extract_text(rec: dict) -> str:
    parts = []
    for k in TEXT_KEYS:
        if k in rec:
            parts.extend(iter_text(rec[k]))
    return " ".join(parts)


def normalize(text: str) -> list:
    """Lowercase; collapse hex/digit/identifier noise so templates collide."""
    t = text.lower()
    t = HEX_RE.sub(" <hex> ", t)
    t = re.sub(r"\b\d+(\.\d+)?([eE][-+]?\d+)?\b", " <n> ", t)
    t = re.sub(r"[^a-z0-9<>\s]", " ", t)
    toks = WORD_RE.findall(t)
    return toks


def shingles(tokens: list, n: int = 4) -> frozenset:
    if len(tokens) < n:
        return frozenset(tokens)
    return frozenset(tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1))


def jaccard(a: frozenset, b: frozenset) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    return inter / (len(a) + len(b) - inter)


def cluster(items: list, sim, threshold: float) -> list:
    """Single-linkage union-find clustering; deterministic by index order."""
    parent = list(range(len(items)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if sim(i, j) >= threshold:
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[max(ri, rj)] = min(ri, rj)
    groups = {}
    for i in range(len(items)):
        groups.setdefault(find(i), []).append(i)
    return [sorted(v) for _, v in sorted(groups.items())]


def kish_ess(sizes: list) -> float:
    if not sizes:
        return 0.0
    s = sum(sizes)
    return (s * s) / sum(n * n for n in sizes)


def canonical_reviewer(rec: dict) -> str:
    raw = rec.get("reviewer") or rec.get("actor") or "unknown"
    raw = str(raw)
    raw = re.sub(r"\(.*?\)", "", raw).strip().lower()
    raw = raw.replace(" ", "-")
    return raw or "unknown"


def extract_hashes(rec: dict) -> list:
    found = set()
    for k in HASH_FIELDS:
        if k in rec:
            for s in iter_text(rec[k]):
                for m in HEX_RE.findall(s):
                    found.add(m.lower())
    return sorted(found)


def hash_binds_live(hashes: list, live: str) -> bool:
    if not live:
        return False
    for h in hashes:
        if len(h) >= 8 and live.startswith(h):
            return True
    return False


def target_of(rec: dict) -> str:
    tid = str(rec.get("target_id") or rec.get("node_id") or "OTHER")
    for part in re.split(r"[,;|/]+", tid):
        part = part.strip()
        if part in TARGET_FILES:
            return part
        if part in CLASS_ALIAS:
            return CLASS_ALIAS[part]
    if tid.startswith("F2"):
        return "F2"
    return "OTHER"


# ------------------------------------------------------------------- corpus load
def load_map(root: Path, map_path: Path):
    b = map_path.read_bytes()
    m = json.loads(b)
    return m, sha256_bytes(b)


def load_outbox_reviews(root: Path, known_ids: set):
    """Review events written to comms/outbox but not present in the map snapshot."""
    pending, files = [], {}
    for f in sorted(glob.glob(str(root / "comms" / "outbox" / "*.jsonl"))):
        p = Path(f)
        try:
            raw = p.read_bytes()
        except OSError:
            continue
        files[str(p.relative_to(root))] = sha256_bytes(raw)
        for line in raw.decode("utf-8", "replace").splitlines():
            line = line.strip()
            if not line or not line.startswith("{"):
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            if e.get("event_type") != "review":
                continue
            eid = e.get("event_id")
            if eid and eid in known_ids:
                continue
            e["_source_file"] = str(p.relative_to(root))
            e["_pending_ingest"] = True
            e["_outbox_line_sha256"] = sha256_bytes(line.encode())
            pending.append(e)
    return pending, files


# ------------------------------------------------------------------ census core
def build_records(map_recs: list, pending: list):
    recs = []
    for r in list(map_recs) + list(pending):
        r = dict(r)
        r["_target"] = target_of(r)
        r["_reviewer"] = canonical_reviewer(r)
        r["_actor"] = str(r.get("actor") or "unknown").lower()
        r["_hashes"] = extract_hashes(r)
        r["_text_tokens"] = normalize(extract_text(r))
        r["_shingles"] = shingles(r["_text_tokens"])
        r["_pending"] = bool(r.get("_pending_ingest"))
        recs.append(r)
    # deterministic order: created_at, event_id
    recs.sort(key=lambda x: (str(x.get("created_at") or ""), str(x.get("event_id") or "")))
    return recs


def threshold_sweep(recs: list, thresholds: list) -> dict:
    out = {}
    for t in thresholds:
        cl = cluster(recs, lambda i, j: jaccard(recs[i]["_shingles"], recs[j]["_shingles"]), t)
        out[str(t)] = {
            "clusters": len(cl),
            "sizes": sorted((len(c) for c in cl), reverse=True),
            "ess": round(kish_ess([len(c) for c in cl]), 4),
        }
    return out


def census(recs: list, live: dict, threshold: float) -> dict:
    targets = {}
    # groups: one per mapped target plus OTHER
    groups = {}
    for r in recs:
        groups.setdefault(r["_target"], []).append(r)
    for tgt in sorted(groups):
        rs = groups[tgt]
        live_sha = (live.get(tgt) or {}).get("sha256")
        cl = cluster(rs, lambda i, j: jaccard(rs[i]["_shingles"], rs[j]["_shingles"]), threshold)
        cluster_of = {}
        clusters = []
        for cid, members in enumerate(cl):
            for i in members:
                cluster_of[i] = cid
            clusters.append({
                "cluster_id": cid,
                "size": len(members),
                "event_ids": [rs[i].get("event_id") for i in members],
                "reviewers": sorted({rs[i]["_reviewer"] for i in members}),
                "verdicts": sorted({str(rs[i].get("verdict")) for i in members}),
            })

        def verdict_counts(sel):
            d = {}
            for r in sel:
                d[str(r.get("verdict"))] = d.get(str(r.get("verdict")), 0) + 1
            return dict(sorted(d.items()))

        accepts = [r for r in rs if str(r.get("verdict")) == "accept"]
        accepts_live = [r for r in accepts if hash_binds_live(r["_hashes"], live_sha)]
        # index -> record for cluster lookup
        idx = {id(r): i for i, r in enumerate(rs)}

        def ess_for(sel):
            sizes = {}
            for r in sel:
                c = cluster_of[idx[id(r)]]
                sizes[c] = sizes.get(c, 0) + 1
            return round(kish_ess(list(sizes.values())), 4), sorted(sizes.values(), reverse=True)

        raw_reviewers = sorted({r["_reviewer"] for r in rs})
        raw_actors = sorted({r["_actor"] for r in rs})
        acc_raw = sorted({r["_reviewer"] for r in accepts_live})
        ess_all, all_cluster_sizes = ess_for(rs)
        blocks = [r for r in rs if str(r.get("verdict")) in ("revise", "reject", "inconclusive")
                  and hash_binds_live(r["_hashes"], live_sha)]
        # effective count per verdict: dedup by reviewer identity, then cluster text
        per_verdict_bound = {}
        for verdict in ("accept", "revise", "reject", "inconclusive"):
            sel = [r for r in rs if str(r.get("verdict")) == verdict
                   and hash_binds_live(r["_hashes"], live_sha)]
            dedup, order = {}, []
            for r in sel:
                if r["_reviewer"] not in dedup:
                    dedup[r["_reviewer"]] = r
                    order.append(r)
            ess, sizes = ess_for(order)
            per_verdict_bound[verdict] = {
                "raw_events": len(sel),
                "distinct_reviewers": sorted(dedup),
                "reviewer_deduped_events": len(order),
                "ess_after_reviewer_dedup": ess,
                "cluster_sizes_after_reviewer_dedup": sizes,
            }
        ess_acc = per_verdict_bound["accept"]["ess_after_reviewer_dedup"]
        acc_cluster_sizes = per_verdict_bound["accept"]["cluster_sizes_after_reviewer_dedup"]
        targets[tgt] = {
            "canonical_path": (live.get(tgt) or {}).get("path"),
            "live_sha256": live_sha,
            "reviews_total": len(rs),
            "by_verdict": verdict_counts(rs),
            "pending_ingest_reviews": sum(1 for r in rs if r["_pending"]),
            "distinct_reviewers_raw": raw_reviewers,
            "distinct_actors_raw": raw_actors,
            "reviews_with_any_cited_hash": sum(1 for r in rs if r["_hashes"]),
            "verdicts_bound_live": verdict_counts([r for r in rs if hash_binds_live(r["_hashes"], live_sha)]),
            "accepts_bound_live": [
                {
                    "event_id": r.get("event_id"),
                    "actor": r.get("actor"),
                    "reviewer": r.get("reviewer") or r.get("actor"),
                    "cited_hashes": r["_hashes"],
                    "cluster_id": cluster_of[idx[id(r)]],
                    "pending_ingest": r["_pending"],
                    "source": r.get("_source_file") or "research_map.json#reviews",
                }
                for r in accepts_live
            ],
            "distinct_accept_reviewers_bound_live": acc_raw,
            "raw_accept_reviewer_count_bound_live": len(acc_raw),
            "accept_ess_bound_live": ess_acc,
            "accept_cluster_sizes_bound_live": acc_cluster_sizes,
            "verdict_ess_all": ess_all,
            "verdict_cluster_sizes_all": all_cluster_sizes,
            "bound_live_blocking_verdicts": len(blocks),
            "effective_verdicts_bound_live": per_verdict_bound,
            "two_independent_accepts_bound_live": ess_acc >= 2.0,
        }
    return {
        "threshold": threshold,
        "n_reviews_total": len(recs),
        "n_reviews_pending_ingest": sum(1 for r in recs if r["_pending"]),
        "reviewer_actor_mismatch_reviews": sum(
            1 for r in recs if r["_reviewer"] != r["_actor"]),
        "targets": targets,
        "review_clusters_all": [
            {
                "cluster_id": cid,
                "size": len(members),
                "event_ids": [recs[i].get("event_id") for i in members],
                "reviewers": sorted({recs[i]["_reviewer"] for i in members}),
                "targets": sorted({recs[i]["_target"] for i in members}),
            }
            for cid, members in enumerate(cluster(recs, lambda i, j: jaccard(
                recs[i]["_shingles"], recs[j]["_shingles"]), threshold))
            if len(members) > 1
        ],
    }


# ---------------------------------------------------------------------- controls
def _mk(text, reviewer, verdict="accept", target="F1", hashes=None):
    return {
        "event_id": "ctl-" + sha256_bytes(f"{text}|{reviewer}|{verdict}|{target}".encode())[:12],
        "event_type": "review", "actor": reviewer, "reviewer": reviewer,
        "verdict": verdict, "target_id": target,
        "statement": text,
        "evidence_refs": [f"schemas/af_wcc_vacuum.yaml#{h}" for h in (hashes or [])],
    }


def run_controls(threshold: float) -> dict:
    base = ("The class contract holds: quantifiers, topology, regularity token and "
            "conclusion direction all match the frozen taxonomy; structural gate pass; "
            "no class leakage between C0 and C2; witnesses exist for the residual claims. ")
    controls = []
    # C1 identical text, 4 distinct reviewers -> ESS 1
    recs = [_mk(base, f"rev-{i}", target="F1") for i in range(4)]
    controls.append(_ctl("C1_identical_text_ess1", recs, threshold, expect_ess=1.0))
    # C2 disjoint text, 4 reviewers -> ESS 4 (varied LETTER tokens: digit variants
    # collide by design under normalization, which C3 tests; repeated tokens would
    # collapse under 4-gram shingling, so the unique part must have varied n-grams)
    recs = [_mk(base + " ".join(
                f"uniq{chr(97 + i)}w{chr(97 + (j % 26))}{chr(97 + (j // 26))}"
                for j in range(60)) + f" tail{chr(97 + i)}", f"rev-{i}", target="F1")
            for i in range(4)]
    controls.append(_ctl("C2_disjoint_text_ess4", recs, threshold, expect_ess=4.0))
    # C3 same template, one number differs -> normalized collision, ESS 1
    recs = [_mk(base + f" observed value {i} 0.000{i}", f"rev-{i}", target="F1") for i in range(4)]
    controls.append(_ctl("C3_number_only_diff_ess1", recs, threshold, expect_ess=1.0))
    # C4 same template, only target hash differs -> ESS 1
    recs = [_mk(base, f"rev-{i}", target="F1",
                hashes=["a" * 12 + f"{i:04d}" if False else ("%012x" % i)]) for i in range(4)]
    controls.append(_ctl("C4_hash_only_diff_ess1", recs, threshold, expect_ess=1.0))
    # C5 same text under four different actors but one reviewer field -> reviewer dedup
    recs = []
    for i in range(4):
        r = _mk(base, "rev-same", target="F1")
        r["actor"] = f"worker-{i:03d}"
        recs.append(r)
    controls.append(_ctl("C5_actor_alias_ess1", recs, threshold, expect_ess=1.0))
    # C6 two exactly duplicated texts -> ESS 2
    alt = ("Separate line of argument from a different instrument: the invariant "
           "functional is scheme-appropriate and the drift criterion is resolution aware. ")
    recs = [_mk(base, "rev-a", target="F1"), _mk(base, "rev-b", target="F1"),
            _mk(alt, "rev-c", target="F1"), _mk(alt, "rev-d", target="F1")]
    controls.append(_ctl("C6_mixed_ess2", recs, threshold, expect_ess=2.0))
    # C7 empty text, distinct reviewers -> shingle-less; documented degenerate case
    recs = [_mk("", f"rev-{i}", target="F1") for i in range(4)]
    controls.append(_ctl("C7_empty_text_degenerate", recs, threshold, expect_ess=1.0))

    passed = sum(1 for c in controls if c["pass"])
    return {
        "threshold": threshold,
        "controls": controls,
        "passed": passed,
        "total": len(controls),
        "note": "Controls are synthetic; C7 documents the degenerate empty-text case "
                "(all-empty shingle sets are Jaccard-identical by construction).",
    }


def _ctl(name, recs, threshold, expect_ess):
    for i, r in enumerate(recs):
        r["_shingles"] = shingles(normalize(extract_text(r)))
    cl = cluster(recs, lambda i, j: jaccard(recs[i]["_shingles"], recs[j]["_shingles"]), threshold)
    ess = round(kish_ess([len(c) for c in cl]), 4)
    return {
        "control": name,
        "n_reviews": len(recs),
        "clusters": len(cl),
        "ess": ess,
        "expected_ess": expect_ess,
        "pass": ess == expect_ess,
    }


# -------------------------------------------------------------------------- main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", default="research_map/research_map.json")
    ap.add_argument("--out", default="artifacts/worker-002/review-ess")
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    root = Path.cwd()
    outdir = root / args.out
    outdir.mkdir(parents=True, exist_ok=True)

    live_before = measure_targets(root)
    m, map_sha = load_map(root, root / args.map)
    map_recs = m.get("reviews", [])
    known = {r.get("event_id") for r in map_recs if isinstance(r, dict)}
    pending, outbox_hashes = load_outbox_reviews(root, known)
    recs = build_records(map_recs, pending)
    live_after = measure_targets(root)
    stable = live_before == live_after
    drifted = sorted(t for t in TARGET_FILES if live_before.get(t) != live_after.get(t))

    result = census(recs, live_after, args.threshold)
    sweep = threshold_sweep(recs, [0.3, 0.4, 0.5, 0.6, 0.7])
    # determinism: rebuild and re-census in-process
    recs2 = build_records(map_recs, pending)
    det_digest = sha256_bytes(json.dumps(
        census(recs2, live_after, args.threshold), sort_keys=True).encode())
    det_digest2 = sha256_bytes(json.dumps(result, sort_keys=True).encode())
    det_ok = det_digest == det_digest2
    controls = run_controls(args.threshold)

    def public_rec(r):
        return {k: v for k, v in r.items() if k not in ("_shingles", "_text_tokens")}

    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "actor": ACTOR,
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime()),
        "map_path": args.map,
        "map_sha256": map_sha,
        "map_reviews_recorded": len(map_recs),
        "live_targets_before": live_before,
        "live_targets_after": live_after,
        "outbox_file_sha256": outbox_hashes,
        "reviews": [public_rec(r) for r in recs],
    }
    (outdir / "review_corpus_snapshot.json").write_text(
        json.dumps(snapshot, indent=1, sort_keys=True) + "\n")

    report = {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "actor": ACTOR,
        "class_ids": CLASS_IDS,
        "authority_note": "measurement only; worker events cannot set node status, "
                          "validation_status, or a gate verdict",
        "method": {
            "corpus": "research_map.json#reviews + comms/outbox review events not yet ingested",
            "reviewer_identity": "reviewer field (parenthetical stripped) else actor",
            "text": "statement/summary/note/findings/hard_failures/does_not_claim/"
                    "next_falsifier/delta_vs_draft, hex and numeric literals normalized",
            "similarity": "Jaccard over 4-gram word shingles; single-linkage clustering",
            "threshold": args.threshold,
            "ess": "Kish ESS = (sum n_c)^2 / sum n_c^2 over text clusters",
        },
        "binding_valid": stable,
        "drift_targets": drifted,
        "determinism_digest": det_digest,
        "determinism_ok": det_ok,
        "controls_summary": {"passed": controls["passed"], "total": controls["total"]},
        "sweep": sweep,
        "census": result,
        "headline": {
            "two_independent_accepts_bound_live": {
                t: v["two_independent_accepts_bound_live"]
                for t, v in result["targets"].items()
            },
            "raw_vs_effective_accepts_bound_live": {
                t: {
                    "raw": v["raw_accept_reviewer_count_bound_live"],
                    "effective_ess": v["accept_ess_bound_live"],
                }
                for t, v in result["targets"].items()
            },
            "bound_live_opposition_effective": {
                t: {
                    k: {
                        "raw_events": v["effective_verdicts_bound_live"][k]["raw_events"],
                        "distinct_reviewers": len(v["effective_verdicts_bound_live"][k]["distinct_reviewers"]),
                        "effective_ess": v["effective_verdicts_bound_live"][k]["ess_after_reviewer_dedup"],
                    }
                    for k in ("revise", "reject", "inconclusive")
                    if v["effective_verdicts_bound_live"][k]["raw_events"] > 0
                }
                for t, v in result["targets"].items()
            },
        },
    }
    (outdir / "ess_report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    (outdir / "controls.json").write_text(json.dumps(
        {"schema_version": SCHEMA_VERSION, "task_id": TASK_ID,
         "synthetic_controls": controls, "real_corpus_sweep": sweep,
         "determinism_ok": det_ok, "determinism_digest": det_digest},
        indent=1, sort_keys=True) + "\n")

    # human-readable summary, generated from the same report object (no hand numbers)
    lines = [
        f"# {TASK_ID} -- review-independence (Kish ESS) census",
        "",
        f"- actor: `{ACTOR}`  |  class binding: {', '.join(CLASS_IDS)}",
        f"- map snapshot: `{args.map}#{map_sha[:12]}`  |  captured: {snapshot['captured_at']}",
        f"- corpus: {result['n_reviews_total']} review records "
        f"({result['n_reviews_pending_ingest']} pending ingest)  |  "
        f"reviewer-vs-actor identity mismatches: {result['reviewer_actor_mismatch_reviews']}",
        f"- binding_valid={stable}  drift_targets={drifted or 'none'}  "
        f"determinism_ok={det_ok}  controls={controls['passed']}/{controls['total']}",
        f"- similarity threshold Jaccard>={args.threshold} over 4-gram shingles; "
        f"ESS=(sum n_c)^2/sum n_c^2",
        "",
        "## Recorded verdicts bound to the LIVE canonical hash",
        "",
        "| target | live sha256 | reviews | accept raw/rev/ESS | revise raw/rev/ESS | "
        "inconcl. raw/rev/ESS | 2 independent accepts |",
        "|---|---|---:|---|---|---|---|",
    ]
    for t, v in result["targets"].items():
        if t in ("OTHER", "F2") or v["live_sha256"] is None:
            continue
        ev = v["effective_verdicts_bound_live"]

        def cell(k):
            d = ev[k]
            return f"{d['raw_events']}/{len(d['distinct_reviewers'])}/{d['ess_after_reviewer_dedup']:.1f}"

        lines.append(
            f"| {t} | `{str(v['live_sha256'])[:12]}` | {v['reviews_total']} | "
            f"{cell('accept')} | {cell('revise')} | {cell('inconclusive')} | "
            f"{'YES' if v['two_independent_accepts_bound_live'] else 'no'} |")
    lines += [
        "",
        "Columns are raw events / distinct reviewer identities / ESS after reviewer-dedup "
        "then text clustering.",
        "",
        "## Limits (read before using)",
        "",
        "- Measurement only. This sets no gate verdict, node status or validation_status; "
        "the controller/leads adjudicate independence and acceptance.",
        "- Hash binding is permissive: a review counts as bound to the live hash if any "
        "cited 8..64-hex token is a prefix of it. A review that merely mentions the live "
        "hash in a superseded context is still counted; inspect `accepts_bound_live`.",
        "- Reviewer identity uses the `reviewer` field when present else `actor`. "
        "Exposure between reviewers is not observable here.",
        "- Text normalization collapses hex and numeric literals, so reviews differing "
        "only in numbers cluster together by design; see controls C3/C4.",
        "",
        "## Falsifier",
        "",
        "REJECT the headline if: (a) a review file outside `research_map.json#reviews` and "
        "`comms/outbox/*.jsonl` changes a target's effective accept count; (b) any cited "
        "hash counted as live is not a prefix of the measured canonical sha256; or "
        "(c) two accepts in one text cluster are shown to be genuinely independent reviews.",
        "",
        "Reproduce: `python3 artifacts/worker-002/review-ess/census_review_ess.py` "
        "(exit 0 = stable, exit 2 = target drift during scan).",
        "",
    ]
    (outdir / "SUMMARY.md").write_text("\n".join(lines) + "\n")

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "actor": ACTOR,
        "outputs": {
            p.name: {"path": str(p.relative_to(root)), "sha256": sha256_file(p),
                     "bytes": p.stat().st_size}
            for p in sorted(outdir.glob("*")) if p.is_file() and p.name != "manifest.json"
        },
        "inputs": {
            args.map: map_sha,
            **{t: live_after[t]["sha256"] for t in TARGET_FILES if live_after[t].get("sha256")},
        },
        "note": "manifest.json does not hash itself",
    }
    (outdir / "manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")

    if not args.quiet:
        print(json.dumps(report["headline"], indent=1))
        print("controls:", controls["passed"], "/", controls["total"],
              "determinism_ok:", det_ok, "binding_valid:", stable)
    return 0 if (stable and det_ok) else 2


if __name__ == "__main__":
    sys.exit(main())
