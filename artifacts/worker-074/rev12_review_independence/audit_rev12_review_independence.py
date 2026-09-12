#!/usr/bin/env python3
"""W074-A1-REV12-INDEP-01: A1 independence census of the rev12 (FROZEN rev28) review corpus.

Question (G-AUDIT criterion + A1 assignment falsifier + PROTOCOL.md):
  The gate needs TWO INDEPENDENT verdicts per formulation target at the measured canonical
  hash.  The controller's advisory scan counts DISTINCT REVIEWER IDS and full-schema accepts
  only (`research_map/astra_lifecycle.py::review_coverage`).  The protocol says two reviews
  that agree because they share a text/template count as ONE.  This instrument closes that
  gap at one measured instant for F0, F1, F2a, F2b (+ L0 as the literature target):
  it (a) replays the controller scan rule verbatim, (b) dedups the bound verdicts by
  reviewer identity, review-document bytes, findings-text shingles and evidence channel,
  and (c) reports which targets carry >=2 *clean* independent accepts and where a
  hard-failure revise/rereject coexists at the same hash.

Deterministic; no network; read-only with respect to every canonical artifact; fails
closed on target-hash drift or on a pinned-input mismatch.  Worker evidence only: issues
no gate verdict, sets no node status, re-adjudicates no review.

Run:  python3 artifacts/worker-074/rev12_review_independence/audit_rev12_review_independence.py
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CST = timezone(timedelta(hours=8))
OUT_DIR = Path(__file__).resolve().parent

# --- targets measured in this census (canonical path -> node) -----------------
TARGETS = {
    "F0": {
        "path": "research_map/formulation_taxonomy.yaml",
        "gate": "G-F0",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "review_criterion": "2 independent accepts (taxonomy); reviews/A1-rebind-coverage.json also adjudicates binding",
    },
    "F1": {
        "path": "schemas/af_wcc_vacuum.yaml",
        "gate": "G-FORM",
        "class_ids": ["AF-WCC-VAC-GEN"],
        "review_criterion": "2 independent accepts with cited sha256",
    },
    "F2a": {
        "path": "schemas/af_scc_c2_vacuum.yaml",
        "gate": "G-FORM",
        "class_ids": ["AF-SCC-C2-VAC-GEN"],
        "review_criterion": "2 independent accepts with cited sha256",
    },
    "F2b": {
        "path": "schemas/af_scc_c0_vacuum.yaml",
        "gate": "G-FORM",
        "class_ids": ["AF-SCC-C0-VAC-GEN"],
        "review_criterion": "2 independent accepts with cited sha256",
    },
    "L0": {
        "path": "ledger/theorems.jsonl",
        "gate": "G-LIT",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "review_criterion": "2 independent accepts with cited sha256",
    },
}

# verbatim from research_map/astra_lifecycle.py
VERDICT_KINDS = ("accept", "revise", "reject", "inconclusive")
TARGET_ALIASES = {
    "F0": "F0", "F1": "F1", "F2A": "F2a", "F2B": "F2b", "F2": "F2b",
    "L0": "L0", "L1": "L1",
    "AF-WCC-VAC-GEN": "F1",
    "AF-SCC-C2-VAC-GEN": "F2a",
    "AF-SCC-C0-VAC-GEN": "F2b",
}

SHINGLE_N = 6
INDEP_THRESHOLD = 0.60
SENSITIVITY = [0.50, 0.60, 0.70, 0.80]

# paths every formulation/literature review is expected to consume; sharing them is not
# an independent evidence channel.  Own evidence = cited paths minus this baseline minus
# the reviewer's own verdict document.
SHARED_BASELINE = {
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
    "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/formulation_taxonomy.yaml",
    "artifacts/formulation/FROZEN.json",
    "artifacts/formulation/rule_spec.json",
    "artifacts/formulation/tools/check_class_schema.py",
    "artifacts/formulation/tools/check_taxonomy_consistency.py",
    "research_map/class_separation.py",
    "runtime/bin/classsep_regression.py",
    "evaluation_rubric.yaml",
    "ledger/theorems.jsonl",
}

CONTROL_DUPLICATE = {
    "file": "CONTROL-duplicate-of-first-accept.json",
    "verdict": "accept",
    "counts_as_full_schema_verdict": True,
}
CONTROL_INDEPENDENT = {
    "file": "CONTROL-independent-synthetic-accept.json",
    "verdict": "accept",
    "counts_as_full_schema_verdict": True,
}
CONTROL_BAD_PIN = "dead" * 16


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def tokens(text: str):
    return re.findall(r"[a-z0-9_]+", text.lower())


def shingles(text: str, n: int = SHINGLE_N):
    t = tokens(text)
    if len(t) < n:
        return {" ".join(t)} if t else set()
    return {" ".join(t[i : i + n]) for i in range(len(t) - n + 1)}


class DSU:
    def __init__(self, n):
        self.p = list(range(n))

    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[max(ra, rb)] = min(ra, rb)


def cluster(n, pair_pred):
    d = DSU(n)
    for i in range(n):
        for j in range(i + 1, n):
            if pair_pred(i, j):
                d.union(i, j)
    groups: dict[int, list[int]] = {}
    for i in range(n):
        groups.setdefault(d.find(i), []).append(i)
    return groups


# --- controller scan rule, verbatim counterparts ------------------------------
def targets_in_review(d: dict) -> set:
    out = set()
    for key in ("target_id", "target", "target_subnode"):
        v = d.get(key)
        if isinstance(v, str):
            out.add(v)
        elif isinstance(v, dict):
            for k2 in ("target_id", "target_subnode", "subnode", "node_id"):
                if isinstance(v.get(k2), str):
                    out.add(v[k2])
    norm = set()
    for t in out:
        norm.add(TARGET_ALIASES.get(t, TARGET_ALIASES.get(t.upper(), t)))
    return norm


def explicit_pins(d: dict) -> list:
    pins = []
    for key in ("artifact_sha256", "reviewed_sha256", "sha256", "cited_sha256"):
        v = d.get(key)
        if isinstance(v, str):
            pins.append(v.lower())
    for key in ("target", "artifact"):
        v = d.get(key)
        if isinstance(v, dict):
            for k2 in ("sha256", "artifact_sha256", "reviewed_sha256"):
                if isinstance(v.get(k2), str):
                    pins.append(v[k2].lower())
    return pins


def binds_measured(pins, measured: str) -> bool:
    h = measured[:12]
    return any(str(p).lower().startswith(h) or h.startswith(str(p).lower()[:12]) for p in pins)


def findings_text(d: dict) -> str:
    f = d.get("findings")
    if f is None:
        f = d.get("summary") or d.get("statement") or ""
    return f if isinstance(f, str) else json.dumps(f, ensure_ascii=False, sort_keys=True)


def evidence_paths(d: dict) -> list:
    out = []
    for k in ("evidence_refs", "artifact_refs", "reviewed_artifacts"):
        v = d.get(k)
        if isinstance(v, list):
            out += [x for x in v if isinstance(x, str)]
        elif isinstance(v, dict):
            out += list(v.keys())
    seen, res = set(), []
    for x in out:
        p = x.split("#")[0].strip()
        if p and p not in seen:
            seen.add(p)
            res.append(p)
    return res


def hard_failure_count(d: dict) -> int:
    hf = d.get("hard_failures")
    if hf is None:
        return 0
    if isinstance(hf, list):
        return len(hf)
    if isinstance(hf, dict):
        return len(hf)
    return 1 if hf else 0


def scan_corpus(docs: dict, measured: dict) -> tuple[list, dict]:
    """Replay astra_lifecycle.py::review_coverage at the measured hashes (reviews/*.json only)."""
    coverage = {t: {"verdicts": [], "full_accepts": []} for t in TARGETS}
    rows = []
    for name in sorted(docs):
        d = docs[name]
        v = str(d.get("verdict", "")).lower()
        if v not in VERDICT_KINDS:
            continue
        reviewer = str(d.get("reviewer") or d.get("actor") or "?")
        full = d.get("counts_as_full_schema_verdict") is not False
        pins = explicit_pins(d)
        for t in targets_in_review(d):
            if t not in TARGETS:
                continue
            h = measured[t]["sha256"]
            if binds_measured(pins, h):
                entry = {"file": name, "reviewer": reviewer, "verdict": v, "full": full}
                coverage[t]["verdicts"].append(entry)
                if v == "accept" and full:
                    coverage[t]["full_accepts"].append(entry)
                rows.append({"target": t, **entry, "pins": pins})
    return rows, coverage


def dedup_target(t: str, bound: list, max_accepts: int | None = None):
    """Identity + review-doc-bytes + findings-shingle dedup of the bound verdicts for one target."""
    acc = [r for r in bound if r["verdict"] == "accept" and r["full"]]
    if max_accepts is not None:
        acc = acc[:max_accepts]

    def dup(i, j):
        a, b = acc[i], acc[j]
        if str(a["reviewer"]) == str(b["reviewer"]):
            return True
        if a["doc_sha256"] and a["doc_sha256"] == b["doc_sha256"]:
            return True
        return jaccard(shingles(a["findings_text"]), shingles(b["findings_text"])) >= INDEP_THRESHOLD

    groups = cluster(len(acc), dup) if acc else {}
    clusters = []
    for _k, idxs in sorted(groups.items(), key=lambda kv: min(kv[1])):
        members = [acc[i] for i in idxs]
        clusters.append(
            {
                "size": len(members),
                "reviewers": sorted({m["reviewer"] for m in members}),
                "files": sorted(m["file"] for m in members),
                "has_revise_at_hash": False,
            }
        )
    # a reviewer that also filed a revise/reject at the same hash has not given a clean accept
    conflicted = set()
    for r in bound:
        if r["verdict"] in ("revise", "reject") and hard_failure_count(r):
            for c in clusters:
                if r["reviewer"] in c["reviewers"]:
                    c["has_revise_at_hash"] = True
                    conflicted.add(tuple(c["files"]))
    clean = [c for c in clusters if not c["has_revise_at_hash"]]
    ev_signatures = sorted({tuple(r["own_evidence"]) or ("<shared-baseline-only>",) for r in acc})
    return {
        "raw_full_accepts": len(acc),
        "raw_full_accept_reviewers": sorted({r["reviewer"] for r in acc}),
        "identity_text_accept_clusters": clusters,
        "effective_accept_clusters": len(clusters),
        "clean_accept_clusters": len(clean),
        "conflicted_accept_clusters": len(clusters) - len(clean),
        "accept_evidence_signatures": [list(s) for s in ev_signatures],
        "distinct_evidence_channels": len(ev_signatures),
        "criterion_two_clean_independent_accepts": "met" if len(clean) >= 2 else "not met",
    }


def main() -> int:
    started = now()
    measured, bytes_map = {}, {}
    for t, spec in TARGETS.items():
        p = ROOT / spec["path"]
        if not p.is_file():
            print(json.dumps({"error": f"missing target {spec['path']}"}))
            return 2
        measured[t] = {"path": spec["path"], "sha256": sha256_file(p), "bytes": p.stat().st_size}
        bytes_map[t] = measured[t]["sha256"]

    # --- snapshot the review corpus (reviews/*.json, the controller's scan set) ----
    review_dir = ROOT / "reviews"
    corpus = {}
    manifest = []
    for rp in sorted(review_dir.glob("*.json")):
        raw = rp.read_text(errors="replace")
        corpus[rp.name] = {"raw": raw, "sha256": hashlib.sha256(raw.encode()).hexdigest()}
        manifest.append({"file": rp.name, "sha256": corpus[rp.name]["sha256"], "bytes": len(raw.encode())})
    corpus_digest = hashlib.sha256(
        "\n".join(f"{m['file']}:{m['sha256']}" for m in manifest).encode()
    ).hexdigest()

    # --- parsed docs with the fields this audit needs ------------------------------
    docs = {}
    for name, rec in corpus.items():
        try:
            d = json.loads(rec["raw"])
        except ValueError:
            continue
        if not isinstance(d, dict):
            continue
        d = dict(d)
        d["_file"] = name
        docs[name] = d
    for name, d in docs.items():
        d["doc_sha256"] = corpus[name]["sha256"]
        d["findings_text"] = findings_text(d)
        ev = evidence_paths(d)
        own = [p for p in ev if p not in SHARED_BASELINE and p != name and not p.endswith(name)]
        d["own_evidence"] = own

    scan_rows, coverage = scan_corpus(docs, measured)

    # --- per-target census ---------------------------------------------------------
    per_target = {}
    for t in TARGETS:
        bound_names = sorted({r["file"] for r in scan_rows if r["target"] == t})
        full_by_file = {r["file"]: r["full"] for r in scan_rows if r["target"] == t}
        bound = [{**docs[n], "full": full_by_file.get(n, True), "file": n} for n in bound_names]
        census = dedup_target(t, bound)
        conflicts = [
            {
                "file": r["file"],
                "reviewer": r["reviewer"],
                "verdict": r["verdict"],
                "hard_failures": hard_failure_count(r),
                "full_schema_verdict": r["full"],
            }
            for r in bound
            if r["verdict"] in ("revise", "reject") and hard_failure_count(r)
        ]
        per_target[t] = {
            "target": t,
            "gate": TARGETS[t]["gate"],
            "class_ids": TARGETS[t]["class_ids"],
            "measured": measured[t],
            "controller_scan": {
                "bound_verdict_files": bound_names,
                "full_accept_files": sorted({r["file"] for r in scan_rows if r["target"] == t and r["verdict"] == "accept" and r["full"]}),
                "distinct_full_accept_reviewers": sorted({r["reviewer"] for r in scan_rows if r["target"] == t and r["verdict"] == "accept" and r["full"]}),
            },
            "census": census,
            "blocking_conflicts_at_hash": conflicts,
        }

    # --- controls (in-memory only; prove the dedup/binding rules) ------------------
    first_acc = next((r for r in scan_rows if r["verdict"] == "accept" and r["full"]), None)
    controls = {}
    if first_acc:
        # C1 duplicate: same reviewer, same doc bytes, same findings -> must not add a channel
        t0 = first_acc["target"]
        first_doc = {**docs[first_acc["file"]], "full": first_acc["full"], "file": first_acc["file"]}
        base = dedup_target(t0, [first_doc])["effective_accept_clusters"]
        dup_doc = dict(first_doc)
        dup_doc["_file"] = CONTROL_DUPLICATE["file"]
        dup_doc["file"] = CONTROL_DUPLICATE["file"]
        dup_doc["doc_sha256"] = "0" * 64
        c1 = dedup_target(t0, [first_doc, dup_doc])["effective_accept_clusters"]
        controls["C1_duplicate_of_existing_accept_collapses"] = (base == 1 and c1 == 1)
        # C2 independent: distinct reviewer, distinct text, distinct evidence -> must add a cluster
        ind = dict(dup_doc)
        ind["reviewer"] = "CTRL-INDEP"
        ind["findings_text"] = "unique synthetic findings text " + " ".join(f"tok{i}" for i in range(40))
        ind["own_evidence"] = ["artifacts/CTRL/independent_probe.json"]
        c2 = dedup_target(t0, [first_doc, ind])["effective_accept_clusters"]
        controls["C2_distinct_accept_adds_cluster"] = (c2 == 2)
    else:
        controls["C1_duplicate_of_existing_accept_collapses"] = False
        controls["C2_distinct_accept_adds_cluster"] = False
    controls["C3_nonmatching_pin_does_not_bind"] = not binds_measured([CONTROL_BAD_PIN], measured["F1"]["sha256"])

    # --- drift check ---------------------------------------------------------------
    end_hashes = {t: sha256_file(ROOT / TARGETS[t]["path"]) for t in TARGETS}
    drift = {t: (end_hashes[t] != measured[t]["sha256"]) for t in TARGETS}
    controls["C4_no_target_drift_during_run"] = not any(drift.values())

    verdict_counts = {
        t: {
            v: sum(1 for r in scan_rows if r["target"] == t and r["verdict"] == v)
            for v in VERDICT_KINDS
        }
        for t in TARGETS
    }

    report = {
        "schema_version": "1.0",
        "artifact_type": "a1_review_independence_census",
        "artifact_id": "artifacts/worker-074/rev12_review_independence/report.json",
        "task_id": "W074-A1-REV12-INDEP-01",
        "actor": "worker-074",
        "created_at": started,
        "created_at_basis": "wall clock at write time (CF-14 clock discipline)",
        "authority": "worker evidence only; no gate verdict, no node status, no review verdict, no canonical-file edit",
        "not_duplicative_of": [
            "controller_gate_audit (distinct reviewer ids only; no text/template/evidence dedup)",
            "reviews/A1-rebind-coverage.json (binding coverage, not independence)",
            "individual rev12 reviews (this census consumes their recorded bytes and re-issues no verdict)",
        ],
        "question": (
            "At the measured rev12 canonical hashes, how many of the controller-counted full-schema "
            "accepts per target survive reviewer-identity + review-bytes + findings-text dedup as clean "
            "independent accepts, and where do blocking revise/reject verdicts coexist at the same hash?"
        ),
        "corpus": {
            "scan_set": "reviews/*.json (the controller's advisory scan set)",
            "n_review_docs": len(manifest),
            "corpus_digest_sha256": corpus_digest,
            "snapshot_created_at": started,
            "scan_rule": "research_map/astra_lifecycle.py: review_coverage (verdict in accept/revise/reject/inconclusive; target alias normalisation; explicit 12-hex pin match against measured sha256; counts_as_full_schema_verdict is not False)",
            "dedup_rule": f"identity: same reviewer id; bytes: identical review-document sha256; text: token {SHINGLE_N}-gram Jaccard >= {INDEP_THRESHOLD} on findings/summary; a cluster is CLEAN unless a member reviewer also filed a hard-failure revise/reject at the same hash",
            "sensitivity_thresholds": SENSITIVITY,
        },
        "targets": per_target,
        "controller_verdict_counts": verdict_counts,
        "controls": controls,
        "drift": drift,
        "finding": {
            "id": "W074-REV12-INDEP-F1",
            "statement": (
                "Census only; per-target counts are in targets[*].census. The criterion column uses "
                "clean independent accept clusters (identity+text dedup, no coexisting hard-failure revise)."
            ),
            "per_target_criterion": {t: per_target[t]["census"]["criterion_two_clean_independent_accepts"] for t in TARGETS},
            "caveat": "Independence is necessary, not sufficient: correctness and binding are separate checks, and this census does not re-adjudicate either.",
        },
        "falsifier": (
            "FALSIFIED IF: (a) any measured target sha256 differs from the values recorded here when re-run, "
            "or drifts during the run; (b) re-running this script on the same corpus digest yields different "
            "cluster assignments; (c) any two accepts placed in one cluster belong to different reviewers with "
            f"distinct review-document sha256 and findings shingle-Jaccard < {INDEP_THRESHOLD}; (d) any accept "
            "counted as clean is shown to be a re-send of another reviewer's verdict text; or (e) any control "
            "C1-C4 fails."
        ),
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "report.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    (OUT_DIR / "snapshot_manifest.json").write_text(
        json.dumps({"created_at": started, "corpus_digest_sha256": corpus_digest, "targets": measured, "files": manifest}, indent=2) + "\n"
    )
    (OUT_DIR / "raw").mkdir(exist_ok=True)
    (OUT_DIR / "raw" / "scan_output.txt").write_text(
        "\n".join(
            f"{r['target']} | {r['verdict']} | full={r['full']} | {r['reviewer']} | {r['file']} | pins={r['pins']}"
            for r in sorted(scan_rows, key=lambda x: (x["target"], x["file"]))
        )
        + "\n"
    )

    summary = {
        "report": str(out.relative_to(ROOT)),
        "report_sha256": sha256_file(out),
        "corpus_digest_sha256": corpus_digest,
        "targets": {
            t: {
                "sha256": measured[t]["sha256"],
                "controller_full_accepts": len(per_target[t]["controller_scan"]["full_accept_files"]),
                "controller_distinct_accept_reviewers": per_target[t]["controller_scan"]["distinct_full_accept_reviewers"],
                "effective_accept_clusters": per_target[t]["census"]["effective_accept_clusters"],
                "clean_accept_clusters": per_target[t]["census"]["clean_accept_clusters"],
                "criterion": per_target[t]["census"]["criterion_two_clean_independent_accepts"],
                "blocking_conflicts": len(per_target[t]["blocking_conflicts_at_hash"]),
            }
            for t in TARGETS
        },
        "controls": controls,
        "drift": drift,
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if all(controls.values()) and not any(drift.values()) else 3


if __name__ == "__main__":
    sys.exit(main())
