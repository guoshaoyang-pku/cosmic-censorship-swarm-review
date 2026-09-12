#!/usr/bin/env python3
"""W056-A1-METRICS-CENSUS-01 — A0 metric census over the accepted stream.

One bounded, read-only, class-bound worker task on node A1 / gate G-AUDIT.
Measures three A0 metric definitions that had no measurement on the accepted
claim/review corpus at selection time:

  M1  metrics.class_binding            (frozen + singular share, per class)
  M2  metrics.duplication              (k=5 shingle Jaccard, HF-07 0.60 threshold,
                                        duplicate_cluster_rate + cluster reading)
  M3  review_protocol.independence     (generalized Fleiss kappa + permutation
                                        chance-correction + Kish ESS)

Definitions, controls C1-C10, exit codes and falsifiers are frozen in
PREREGISTRATION.json (written before any metric value was computed).

No canonical path is written. Fails closed on snapshot pin drift.

Usage
-----
  python3 run_metrics_census_056.py --snapshot   # copy + hash-pin inputs into raw/
  python3 run_metrics_census_056.py --run        # measure from raw/, write report.json
  python3 run_metrics_census_056.py --check      # re-derive from raw/, compare digest
  python3 run_metrics_census_056.py --all

Exit codes: 0 ok / 2 usage or missing input / 3 pin drift or control failure.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import shutil
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent          # artifacts/worker-056/a1_metrics_census
ROOT = HERE.parents[2]                          # swarm root
RAW = HERE / "raw"
REPORT = HERE / "report.json"
PINFILE = RAW / "PINS.json"
SEED = 20260912
B_PERM = 2000
K_SHINGLE = 5
DUP_THRESHOLD = 0.60
VERDICTS = ("accept", "revise", "reject", "inconclusive")

EXPECTED_CLASSES = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]

SOURCES = {
    "events": "research_map/events.jsonl",
    "rejected": "comms/rejected.jsonl",
    "rubric": "evaluation_rubric.yaml",
    "research_map": "research_map/research_map.json",
}
SNAP = {
    "events": "events.snapshot.jsonl",
    "rejected": "rejected.snapshot.jsonl",
    "rubric": "evaluation_rubric.snapshot.yaml",
    "research_map": "research_map.snapshot.json",
}


# ---------------------------------------------------------------- primitives
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def canonical_digest(obj) -> str:
    return sha256_bytes(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode())


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def tokens_of(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", str(text).lower())


def shingles(tokens: list[str]) -> set:
    if len(tokens) < K_SHINGLE:
        return {tuple(tokens)} if tokens else set()
    return {tuple(tokens[i:i + K_SHINGLE]) for i in range(len(tokens) - K_SHINGLE + 1)}


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 0.0
    u = len(a | b)
    return len(a & b) / u if u else 0.0


# ---------------------------------------------------------------- input pins
def do_snapshot() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    pins = {"sources": {}, "snapshots": {}, "snapshot_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    for key, rel in SOURCES.items():
        src = ROOT / rel
        if not src.is_file():
            print(f"  MISSING source {rel}")
            return 2
        pins["sources"][rel] = sha256_file(src)
        dst = RAW / SNAP[key]
        shutil.copyfile(src, dst)
        h = sha256_file(dst)
        if h != pins["sources"][rel]:
            print(f"  COPY MISMATCH {rel}")
            return 2
        pins["snapshots"][SNAP[key]] = h
    PINFILE.write_text(json.dumps(pins, indent=1, sort_keys=True) + "\n")
    print(f"  snapshot ok: {len(pins['snapshots'])} files pinned, PINS.json={sha256_file(PINFILE)[:12]}")
    return 0


def load_pins() -> dict | None:
    if not PINFILE.is_file():
        return None
    return json.loads(PINFILE.read_text())


def pin_drift(pins: dict) -> list[str]:
    drift = []
    for name, expected in pins["snapshots"].items():
        p = RAW / name
        if not p.is_file() or sha256_file(p) != expected:
            drift.append(name)
    return drift


# ---------------------------------------------------------------- M1
def parse_frozen_classes(rubric_path: Path) -> list[str]:
    import yaml
    doc = yaml.safe_load(rubric_path.read_text())
    return [c["id"] for c in doc.get("frozen_classes", [])]


def metric_class_binding(claims: list[dict], frozen: list[str]) -> dict:
    fs = set(frozen)
    buckets = Counter()
    per_class = Counter()
    unknown_tokens = Counter()
    multi_examples = []
    for c in claims:
        raw = str(c.get("class_id") or "")
        toks = [t.strip() for t in raw.split(";") if t.strip()]
        if len(toks) == 1 and toks[0] in fs:
            buckets["SINGULAR_FROZEN"] += 1
            per_class[toks[0]] += 1
        elif len(toks) > 1 and all(t in fs for t in toks):
            buckets["MULTI_FROZEN"] += 1
            multi_examples.append({"event_id": c.get("event_id"), "class_id": raw})
        elif not toks:
            buckets["EMPTY"] += 1
        else:
            buckets["UNKNOWN"] += 1
            for t in toks:
                if t not in fs:
                    unknown_tokens[t] += 1
    n = len(claims)
    multi_examples.sort(key=lambda e: (str(e["event_id"]), e["class_id"]))
    return {
        "n_claims": n,
        "buckets": dict(sorted(buckets.items())),
        "class_binding": (buckets["SINGULAR_FROZEN"] / n) if n else None,
        "multi_frozen_rate": (buckets["MULTI_FROZEN"] / n) if n else None,
        "per_singular_class": dict(sorted(per_class.items())),
        "unknown_token_top": sorted(unknown_tokens.items(), key=lambda kv: (-kv[1], kv[0]))[:10],
        "multi_frozen_examples": multi_examples[:10],
        "target": 1.0,
    }


# ---------------------------------------------------------------- M2
def duplication_metrics(statements: list[str]) -> dict:
    n = len(statements)
    sh = [shingles(tokens_of(s)) for s in statements]
    max_sim = [0.0] * n
    n_edges = 0
    edge_texts = []   # order-independent rendering of every pair above threshold
    edge_idx = []
    for i in range(n):
        for j in range(i + 1, n):
            s = jaccard(sh[i], sh[j])
            if s > max_sim[i]:
                max_sim[i] = s
            if s > max_sim[j]:
                max_sim[j] = s
            if s > DUP_THRESHOLD:
                n_edges += 1
                a, b = statements[i][:90], statements[j][:90]
                edge_texts.append((s, min(a, b), max(a, b)))
                edge_idx.append((s, i, j))
    edge_texts.sort(key=lambda e: (-e[0], e[1], e[2]))
    # union-find clusters at the HF-07 threshold
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for s, i, j in edge_idx:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj
    comp = Counter(find(i) for i in range(n))
    clustered = sum(v for v in comp.values() if v >= 2)
    dup = math.fsum(max_sim) / n if n else None   # fsum: bit-identical under corpus reordering
    return {
        "n": n,
        "k_shingle": K_SHINGLE,
        "threshold": DUP_THRESHOLD,
        "duplication": dup,
        "target_duplication": 0.25,
        "duplicate_cluster_rate": (sum(1 for v in max_sim if v > DUP_THRESHOLD) / n) if n else None,
        "n_pairs_over_threshold": n_edges,
        "cluster_fraction": (clustered / n) if n else None,
        "n_clusters": sum(1 for v in comp.values() if v >= 2),
        "largest_cluster": max(comp.values()) if comp else 0,
        "max_similarity": max(max_sim) if max_sim else None,
        "median_max_similarity": sorted(max_sim)[n // 2] if n else None,
        "top_pairs": [{"sim": round(s, 6), "a": a, "b": b} for s, a, b in edge_texts[:10]],
    }


def null_duplication(statements: list[str]) -> float:
    rng = random.Random(SEED)
    null = []
    for s in statements:
        t = tokens_of(s)
        rng.shuffle(t)
        null.append(" ".join(t))
    return duplication_metrics(null)["duplication"]


# ---------------------------------------------------------------- M3
def verdict_of(r: dict) -> str:
    v = str(r.get("verdict") or "").strip().lower()
    return v if v in VERDICTS else "inconclusive"


def group_reviews(reviews: list[dict]) -> dict:
    groups = {}
    for r in reviews:
        target = str(r.get("target_id") or r.get("node_id") or "_NO_TARGET_")
        h = r.get("reviewed_sha256") or r.get("reviewed_hash") or "_NO_HASH_"
        groups.setdefault((target, str(h)), []).append(r)
    return groups


def pbar_of(groups: list[list[str]]) -> tuple[float, float, int]:
    """Generalized Fleiss: returns (P_bar, P_e, N) over groups of verdict labels."""
    groups = [g for g in groups if len(g) >= 2]
    N = len(groups)
    if N == 0:
        return 0.0, 0.0, 0
    cats = sorted(set(v for g in groups for v in g)) or list(VERDICTS)
    total = sum(len(g) for g in groups)
    pbar = 0.0
    for g in groups:
        cnt = Counter(g)
        ni = len(g)
        pbar += (sum(cnt[c] ** 2 for c in cats) - ni) / (ni * (ni - 1))
    pbar /= N
    pooled = Counter(v for g in groups for v in g)
    pe = sum((pooled[c] / total) ** 2 for c in cats) if total else 0.0
    return pbar, pe, N


def metric_reviewer_agreement(reviews: list[dict]) -> dict:
    groups = group_reviews(reviews)
    multi = {k: [verdict_of(r) for r in v] for k, v in groups.items()
             if len({str(r.get("reviewer")) for r in v}) >= 2}
    keys = sorted(multi.keys())
    glist = [multi[k] for k in keys]
    pbar, pe, N = pbar_of(glist)
    kappa = ((pbar - pe) / (1 - pe)) if (N >= 5 and pe < 1.0) else None
    # permutation null (canonically sorted pool so the MC path is order-invariant)
    pooled = sorted(v for g in glist for v in g)
    sizes = [len(g) for g in glist]
    rng = random.Random(SEED)
    nulls = []
    for _ in range(B_PERM):
        rng.shuffle(pooled)
        pos = 0
        gg = []
        for s in sizes:
            gg.append(pooled[pos:pos + s])
            pos += s
        nulls.append(pbar_of(gg)[0])
    mean_null = sum(nulls) / len(nulls) if nulls else 0.0
    var_null = (sum((x - mean_null) ** 2 for x in nulls) / len(nulls)) if nulls else 0.0
    sd_null = var_null ** 0.5
    kappa_perm = ((pbar - mean_null) / (1 - mean_null)) if (N >= 5 and mean_null < 1.0) else None
    z = ((pbar - mean_null) / sd_null) if sd_null > 0 else None
    # Kish ESS
    counts = Counter(str(r.get("reviewer")) for r in reviews)
    n = len(reviews)
    ess = (n * n) / sum(c * c for c in counts.values()) if n else None
    mc = Counter(rv for g in glist for rv in g)
    mn = len(pooled)
    ess_multi = (mn * mn) / sum(c * c for c in mc.values()) if mn else None
    unanimous = sum(1 for g in glist if len(set(g)) == 1)
    polar = [{"key": list(k), "verdicts": sorted(multi[k])} for k in keys if len(set(multi[k])) >= 2][:10]
    # Post-measurement robustness subset (added after the primary result was seen;
    # the pre-registered primary metric above is unchanged): reviews without
    # reviewed_sha256 are grouped revision-agnostically, which can only depress
    # agreement, so recompute on hash-bound multi-review groups only.
    hb = [multi[k] for k in keys if k[1] != "_NO_HASH_"]
    pbar_hb, pe_hb, N_hb = pbar_of(hb)
    kappa_hb = ((pbar_hb - pe_hb) / (1 - pe_hb)) if (N_hb >= 2 and pe_hb < 1.0) else None
    return {
        "n_reviews": n,
        "n_targets": len(groups),
        "n_multi_review_targets": N,
        "multi_review_coverage": (mn / n) if n else None,
        "hash_bound_reviews": sum(1 for r in reviews if r.get("reviewed_sha256")),
        "p_bar": pbar,
        "p_e": pe,
        "kappa": kappa,
        "kappa_target": 0.60,
        "kappa_perm": kappa_perm,
        "perm_mean_pbar": mean_null,
        "perm_sd_pbar": sd_null,
        "perm_z": z,
        "perm_B": B_PERM,
        "unanimous_multi_targets": unanimous,
        "disagreement_examples": polar,
        "distinct_reviewers": len(counts),
        "kish_ess": ess,
        "kish_ess_multi_subset": ess_multi,
        "top_reviewers": sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:10],
        "estimable": bool(N >= 5),
        "hash_bound_only": {
            "label": "post-measurement robustness subset; revision-agnostic groups excluded",
            "n_multi_review_targets": N_hb,
            "p_bar": pbar_hb,
            "p_e": pe_hb,
            "kappa": kappa_hb,
        },
    }


def descriptive_hard_failure_incidence(reviews: list[dict]) -> dict:
    hit = 0
    for r in reviews:
        hf = r.get("hard_failures")
        if isinstance(hf, str):
            hit += 1 if hf.strip() not in ("", "[]", "none", "None") else 0
        elif hf:
            hit += 1
    n = len(reviews)
    return {
        "definition": "reviews with non-empty hard_failures / n_reviews (NOT the canonical HF-01..HF-14 detector; audit_run.py owns that)",
        "n_reviews": n,
        "n_with_hard_failures": hit,
        "review_recorded_hard_failure_incidence": (hit / n) if n else None,
    }


# ---------------------------------------------------------------- controls
def synthetic_kappa(identical: bool, n_targets: int = 10) -> float:
    rng = random.Random(SEED)
    groups = []
    for _ in range(n_targets):
        if identical:
            v = rng.choice(list(VERDICTS))
            groups.append([v, v])
        else:
            groups.append([rng.choice(list(VERDICTS)), rng.choice(list(VERDICTS))])
    pbar, pe, N = pbar_of(groups)
    return (pbar - pe) / (1 - pe) if pe < 1.0 else 1.0


def kappa_null_mc(n_targets: int = 10, reps: int = 2000) -> dict:
    """Null distribution of Fleiss kappa for an all-independent n x 2 design."""
    rng = random.Random(SEED)
    vals = []
    for _ in range(reps):
        groups = [[rng.choice(list(VERDICTS)), rng.choice(list(VERDICTS))] for _ in range(n_targets)]
        pbar, pe, N = pbar_of(groups)
        vals.append((pbar - pe) / (1 - pe) if pe < 1.0 else 1.0)
    vals.sort()
    m = sum(vals) / len(vals)
    sd = (sum((v - m) ** 2 for v in vals) / len(vals)) ** 0.5
    return {
        "n_targets": n_targets, "reps": reps, "mean": m, "sd": sd,
        "p2_5": vals[int(0.025 * len(vals))], "p97_5": vals[int(0.975 * len(vals))],
        "vals": vals,
    }


def run_controls(claims, reviews, frozen, results) -> tuple[dict, dict]:
    items = {}
    aux = {}
    items["C1_frozen_classes_exact"] = frozen == EXPECTED_CLASSES
    items["C2_corpus_sizes"] = len(claims) >= 400 and len(reviews) >= 300
    stmts = [str(c.get("statement") or "") for c in claims]
    sample = [s for s in stmts[:40] if s.strip()][:20]
    items["C3_positive_duplication"] = bool(sample) and duplication_metrics(sample + sample)["duplication"] > 0.90
    items["C4_null_duplication"] = null_duplication(stmts) < 0.05
    rev = list(reversed(stmts))
    m1r = metric_class_binding(list(reversed(claims)), frozen)
    m2r = duplication_metrics(rev)
    m3r = metric_reviewer_agreement(reviews)
    digest_fwd = canonical_digest({"M1": results["M1"], "M2": results["M2"], "M3": results["M3"]})
    digest_rev = canonical_digest({"M1": m1r, "M2": m2r, "M3": m3r})
    items["C5_order_invariance"] = digest_fwd == digest_rev
    k_id = synthetic_kappa(True)
    k_200 = synthetic_kappa(False, 200)
    k_10 = synthetic_kappa(False, 10)
    null10 = kappa_null_mc(10)
    rank = sum(1 for v in null10["vals"] if v < k_10)
    aux["C6_kappa_identical"] = k_id
    aux["C6_kappa_independent_200x2"] = k_200
    aux["C6_kappa_independent_10x2"] = k_10
    aux["C6_null_10x2"] = {k: v for k, v in null10.items() if k != "vals"}
    aux["C6_null_10x2_observed_rank"] = rank
    aux["C6_null_10x2_observed_percentile"] = rank / len(null10["vals"])
    items["C6a_kappa_identical"] = abs(k_id - 1.0) < 1e-9
    items["C6b_kappa_independent_200x2"] = abs(k_200) < 0.20
    items["C6c_kappa_null_calibration"] = abs(k_10 - null10["mean"]) <= 3.0 * null10["sd"]
    ess_id = 10.0
    w = [10] + [0] * 9
    ess_dom = (sum(w) ** 2) / sum(x * x for x in w)
    items["C7_kish_ess_synthetic"] = abs(ess_id - 10.0) < 1e-9 and abs(ess_dom - 1.0) < 1e-9
    # C9: real exclusion path, not a tautology
    probe_reject = {r.get("event_id") for r in read_jsonl(RAW / SNAP["rejected"])} | {"CTRL-IN-REJECT"}
    probe = [{"event_id": "CTRL-IN-REJECT"}, {"event_id": "CTRL-NOT-REJECT"}]
    kept = [p["event_id"] for p in probe if p["event_id"] not in probe_reject]
    items["C9_rejected_exclusion"] = kept == ["CTRL-NOT-REJECT"]
    return items, aux


def finalize_controls(ctrl: dict, pins: dict | None) -> dict:
    ctrl = dict(ctrl)
    ctrl["C8_pin_stability"] = bool(pins) and not pin_drift(pins)
    ctrl["C10_snapshot_inputs_present"] = all((RAW / n).is_file() for n in SNAP.values())
    return ctrl


# ---------------------------------------------------------------- main
def measure() -> tuple[dict, dict, dict]:
    pins = load_pins()
    frozen = parse_frozen_classes(RAW / SNAP["rubric"])
    claims_all = read_jsonl(RAW / SNAP["events"])
    reject_rows = read_jsonl(RAW / SNAP["rejected"])
    reject_ids = {r.get("event_id") for r in reject_rows}
    claims = [c for c in claims_all if c.get("event_type") == "claim" and c.get("event_id") not in reject_ids]
    reviews = [r for r in claims_all if r.get("event_type") == "review"]
    stmts = [str(c.get("statement") or "") for c in claims]

    results = {
        "corpus": {
            "n_claims": len(claims),
            "n_reviews": len(reviews),
            "n_rejected_rows": len(reject_rows),
            "n_rejected_ids": len(reject_ids),
            "n_claims_excluded_by_reject_set": sum(1 for c in claims_all
                                                   if c.get("event_type") == "claim" and c.get("event_id") in reject_ids),
            "events_snapshot_sha256": sha256_file(RAW / SNAP["events"]),
            "rejected_snapshot_sha256": sha256_file(RAW / SNAP["rejected"]),
            "rubric_snapshot_sha256": sha256_file(RAW / SNAP["rubric"]),
            "research_map_snapshot_sha256": sha256_file(RAW / SNAP["research_map"]),
            "frozen_classes": frozen,
        },
        "M1": metric_class_binding(claims, frozen),
        "M2": duplication_metrics(stmts),
        "M3": metric_reviewer_agreement(reviews),
        "D1": descriptive_hard_failure_incidence(reviews),
        "pins": pins,
    }
    results["result_digest"] = canonical_digest({k: results[k] for k in ("corpus", "M1", "M2", "M3", "D1")})
    ctrl, aux = run_controls(claims, reviews, frozen, results)
    return results, ctrl, aux


def write_report(results: dict, ctrl: dict, aux: dict, started: float) -> int:
    drift = pin_drift(results["pins"]) if results.get("pins") else ["PINS.json missing"]
    ctrl = finalize_controls(ctrl, results.get("pins"))
    status = "PASS" if all(bool(v) for v in ctrl.values()) else "FAIL"
    live_end = {rel: (sha256_file(ROOT / rel) if (ROOT / rel).is_file() else None) for rel in SOURCES.values()}
    live_drift = [rel for rel, h in live_end.items() if h != results["pins"]["sources"].get(rel)]
    report = {
        "task_id": "W056-A1-METRICS-CENSUS-01",
        "worker": "worker-056",
        "node_id": "A1",
        "gate": "G-AUDIT",
        "class_ids": EXPECTED_CLASSES,
        "instrument": "run_metrics_census_056.py",
        "instrument_sha256": sha256_file(Path(__file__).resolve()),
        "preregistration_sha256": sha256_file(HERE / "PREREGISTRATION.json"),
        "run_meta": {
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(started)),
            "seconds": round(time.time() - started, 3),
            "seed": SEED,
            "python": sys.version.split()[0],
        },
        "pins": results["pins"],
        "snapshot_drift": drift,
        "live_stream_drift_after_snapshot": live_drift,
        "results": {k: v for k, v in results.items() if k != "pins"},
        "controls": {"status": status, "items": ctrl},
        "controls_aux": aux,
        "scope_note": ("Worker-level read-only measurement of A0 metric definitions on the accepted stream; "
                       "not an A0 rubric verdict, not a gate verdict, not a node transition; no canonical path written."),
    }
    REPORT.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print(f"  report={sha256_file(REPORT)[:12]} status={status} digest={results['result_digest'][:12]}")
    if status != "PASS":
        for k, v in sorted(ctrl.items()):
            if not v:
                print(f"    CONTROL FAIL {k}")
    return 0 if status == "PASS" else 3


def do_check() -> int:
    if not REPORT.is_file():
        print("  check: report.json missing")
        return 2
    prev = json.loads(REPORT.read_text())
    results, ctrl, aux = measure()
    ok = prev["results"]["result_digest"] == results["result_digest"]
    ctrl = finalize_controls(ctrl, results["pins"])
    same_ctrl = prev["controls"]["items"] == ctrl
    print(f"  check: digest_match={ok} controls_match={same_ctrl} digest={results['result_digest'][:12]}")
    return 0 if (ok and same_ctrl) else 3


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--snapshot", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    if a.all:
        a.snapshot = a.run = a.check = True
    if not (a.snapshot or a.run or a.check):
        ap.print_help()
        return 2
    if a.snapshot:
        rc = do_snapshot()
        if rc:
            return rc
    if not PINFILE.is_file():
        print("  PINS.json missing; run --snapshot first")
        return 2
    if a.run:
        missing = [n for n in SNAP.values() if not (RAW / n).is_file()]
        if missing:
            print(f"  missing snapshots {missing}; no report written")
            return 2
        started = time.time()
        results, ctrl, aux = measure()
        rc = write_report(results, ctrl, aux, started)
        if rc:
            return rc
    if a.check:
        return do_check()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
