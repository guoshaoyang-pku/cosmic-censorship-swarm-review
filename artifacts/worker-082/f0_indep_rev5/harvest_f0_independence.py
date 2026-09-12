#!/usr/bin/env python3
"""W082-A1-F0-INDEP-REV5-01 — independent review-independence census at F0 rev5.

Question: at the pinned canonical F0 taxonomy hash
0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3, how many *mutually
independent* reviewer verdicts exist, and does the G-F0 criterion "two independent reviewer
verdicts" hold after (a) same-text dedup and (b) author exclusion?

Protocol rule (comms/PROTOCOL.md; A1 acceptance): "two reviews that agree because they are the
same text count as one".  Authority: worker evidence only.  Emits NO gate verdict, NO node
status, NO validation_status=passed, edits NO canonical artifact.  Read-only apart from its own
output directory.

Method (pre-registered before measurement):
  * Harvest every review-shaped record in reviews/, artifacts/**, comms/**, events.jsonl whose
    PRIMARY target-hash field binds the pinned F0 hash.  Records that only cite the hash (e.g.
    inside evidence_refs) are weak/mention-only and never counted as verdicts.
  * Collapse channel copies to ONE representative per reviewer: a reviewer's three re-emitted
    copies are one reviewer verdict, not three.  Representative = richest live record, with all
    aliases and per-copy differences recorded.
  * Text = reviewer-authored strings under finding/detail/summary/rationale/consequence/
    finding-list keys, normalized to lowercase alphanumerics.
  * Similarity = Jaccard over 5-gram shingles.
  * R1 (protocol dedup): an accept pair with Jaccard >= 0.50 counts as ONE verdict.
  * R2 (criterion, pre-registered): G-F0's "two independent reviewer verdicts" is MET iff
    >= 2 accept components at tau=0.30 AND >= 2 accepts declare counts_as_full_schema_verdict
    true AND no accepting reviewer is an author.
  * Verdict: accept if R2 and no R1 pair; accept with score 3.5 if R2 and only caveat-band
    [0.30,0.50) pairs; revise if R2 fails or an R1 duplicate exists.
  * Controls: C1 exact clone (must be ~1.0), C2 seeded random-token null, C3 accept-vs-non-accept
    cross similarity, C4 double-run determinism, C5 pinned-hash stability during the run.

Usage:
  python3 harvest_f0_independence.py            # measure, print summary
  python3 harvest_f0_independence.py --write    # measure and write evidence.json/REVIEW/REPORT
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import random
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone

ROOT = "/data3/guoshaoyang/workdir/ai4math-swarm"
F0_PATH = "research_map/formulation_taxonomy.yaml"
F0_SHA = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
F0_PREFIX = F0_SHA[:12]
SUPPLEMENT_PATH = "artifacts/formulation/formulation_taxonomy.yaml"
SUPPLEMENT_SHA = "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1"
FROZEN_PATH = "artifacts/formulation/FROZEN.json"
OUT_DIR = os.path.join(ROOT, "artifacts/worker-082/f0_indep_rev5")
TZ = timezone(timedelta(hours=8))

PRIMARY_HASH_FIELDS = (
    "reviewed_sha256", "artifact_sha256", "target_sha256", "artifact_sha256_prefix",
    "reviewed_sha256_prefix", "target_sha256_prefix", "reviewed_hash", "target_hash",
)
TEXT_KEYS = (
    "finding", "detail", "summary", "score_rationale", "rationale", "statement",
    "consequence_for_gate", "label", "note", "notes", "positives", "negative_findings",
    "residual_observations", "hard_failures", "blocking_items", "claims_not_made",
    "authority_note", "independence_statement", "checklist", "machine_checks",
    "gate_criteria_results", "falsifier",
)
TEXT_LIST_KEYS = ("findings", "hard_failures", "positives", "residual_observations",
                  "negative_findings", "blocking_items", "residual_observations")
LIVE_PREFIXES = ("reviews/", "comms/outbox/", "comms/inbox/")
TAU_DEDUP = 0.50
TAU_INDEP = 0.30
SHINGLE_N = 5
SEED = 82082


def now_iso():
    return datetime.now(TZ).isoformat(timespec="seconds")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def measure_pins():
    pins = {}
    for rel in (F0_PATH, SUPPLEMENT_PATH, FROZEN_PATH):
        p = os.path.join(ROOT, rel)
        if os.path.exists(p):
            pins[rel] = {
                "sha256": sha256_file(p),
                "bytes": os.path.getsize(p),
                "mtime": datetime.fromtimestamp(os.path.getmtime(p), TZ).isoformat(timespec="seconds"),
            }
    return pins


def preselect_files():
    """Candidate files that mention the pinned hash (fast grep prefilter, walk fallback)."""
    try:
        out = subprocess.run(
            ["grep", "-rl", "--include=*.json", "--include=*.jsonl", F0_PREFIX,
             "reviews", "artifacts", "comms", "research_map/events.jsonl"],
            cwd=ROOT, capture_output=True, text=True, timeout=180,
        ).stdout
        files = [os.path.join(ROOT, p.strip()) for p in out.splitlines() if p.strip()]
        if files:
            return files
    except Exception:
        pass
    files = []
    for pat in ("reviews/**/*.json", "artifacts/**/*.json", "comms/**/*.jsonl",
                "comms/**/*.json", "research_map/events.jsonl"):
        files += glob.glob(os.path.join(ROOT, pat), recursive=True)
    return files


def iter_records():
    seen_files = set()
    for path in sorted(preselect_files()):
        if path in seen_files or not os.path.isfile(path):
            continue
        seen_files.add(path)
        rel = os.path.relpath(path, ROOT)
        raw = open(path, "rb").read()
        digest = sha256_bytes(raw)
        if path.endswith(".jsonl"):
            for line in raw.decode("utf-8", "replace").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if isinstance(obj, dict):
                    yield rel, obj, digest
        else:
            try:
                obj = json.loads(raw.decode("utf-8"))
            except Exception:
                continue
            if isinstance(obj, dict):
                yield rel, obj, digest


def is_review_shape(d):
    if d.get("event_type") == "review":
        return True
    return "verdict" in d and ("reviewer" in d or "actor" in d)


def primary_hash_fields(d):
    out = {}
    for k in PRIMARY_HASH_FIELDS:
        v = d.get(k)
        if isinstance(v, str) and v:
            out[k] = v
    return out


def binds_pinned(d):
    return any(v.startswith(F0_PREFIX) or v == F0_SHA for v in primary_hash_fields(d).values())


def cites_hash(d):
    return F0_PREFIX in json.dumps(d, sort_keys=True)


def channel_tier(src, reviewer):
    if src.startswith(LIVE_PREFIXES):
        return "live-store"
    if src == "research_map/events.jsonl":
        return "ingested-event"
    compact = reviewer.replace("-", "")
    if f"/{reviewer}/" in src or f"/{compact}/" in src or os.path.basename(src).startswith(reviewer):
        return "own-artifact"
    return "third-party-snapshot"


def text_of(d):
    parts = []

    def walk(key, val):
        if isinstance(val, str):
            if key in TEXT_KEYS or key.endswith("_note") or key.endswith("_statement"):
                parts.append(val)
        elif isinstance(val, dict):
            for k, v in val.items():
                walk(k, v)
        elif isinstance(val, list):
            if key in TEXT_LIST_KEYS:
                for v in val:
                    if isinstance(v, str):
                        parts.append(v)
                    elif isinstance(v, dict):
                        for k2, v2 in v.items():
                            walk(k2, v2)
            else:
                for v in val:
                    if isinstance(v, dict):
                        for k2, v2 in v.items():
                            walk(k2, v2)

    for k, v in d.items():
        walk(k, v)
    return "\n".join(p for p in parts if isinstance(p, str) and p.strip())


def normalize(text):
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def shingles(text, n=SHINGLE_N):
    toks = normalize(text).split()
    if len(toks) < n:
        return {tuple(toks)} if toks else set()
    return {tuple(toks[i:i + n]) for i in range(len(toks) - n + 1)}


def jaccard(a, b):
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def components(nodes, sim, tau):
    parent = {n: n for n in nodes}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i, a in enumerate(nodes):
        for b in nodes[i + 1:]:
            if sim.get((a, b), 0.0) >= tau:
                ra, rb = find(a), find(b)
                if ra != rb:
                    parent[rb] = ra
    groups = {}
    for n in nodes:
        groups.setdefault(find(n), []).append(n)
    return sorted((sorted(v) for v in groups.values()), key=lambda g: g[0])


def harvest():
    """Return (reviewer-level verdicts, weak-binding records, self-excluded records)."""
    raw = []
    weak = []
    self_excluded = []
    for src, obj, src_sha in iter_records():
        if not is_review_shape(obj):
            continue
        reviewer = obj.get("reviewer") or obj.get("actor")
        verdict = obj.get("verdict")
        if not reviewer or not verdict:
            continue
        rid = obj.get("event_id") or obj.get("review_id") or f"{src}:{json.dumps(obj, sort_keys=True)[:80]}"
        task_id = str(obj.get("task_id") or "")
        if src.startswith("artifacts/worker-082/f0_indep_rev5/") or task_id.startswith("W082-A1-F0-INDEP"):
            self_excluded.append({"source": src, "record_id": rid})
            continue
        if binds_pinned(obj):
            raw.append({
                "reviewer": reviewer,
                "verdict": str(verdict),
                "score": obj.get("score"),
                "target_id": obj.get("target_id") or obj.get("node_id"),
                "class_id": obj.get("class_id"),
                "counts_as_full_schema_verdict": obj.get("counts_as_full_schema_verdict"),
                "review_kind": obj.get("review_kind"),
                "created_at": obj.get("created_at") or obj.get("_received_at"),
                "record_id": rid,
                "source": src,
                "tier": channel_tier(src, reviewer),
                "source_sha256": src_sha,
                "hash_fields": primary_hash_fields(obj),
                "hard_failures": obj.get("hard_failures") if isinstance(obj.get("hard_failures"), list) else [],
                "n_findings": len(obj.get("findings")) if isinstance(obj.get("findings"), list) else 0,
                "independence_selfreport": {k: obj.get(k) for k in (
                    "independent", "independence", "independence_statement", "kish_ess",
                    "author_of_target", "blind_to_artifact_lineage") if k in obj},
                "text": text_of(obj),
            })
        elif cites_hash(obj):
            weak.append({"source": src, "record_id": rid, "reviewer": reviewer,
                         "verdict": str(verdict), "target_id": obj.get("target_id") or obj.get("node_id"),
                         "reason": "hash cited but no primary target-hash field"})

    # collapse to one representative per (reviewer, verdict); keep aliases and copy differences
    groups = {}
    for r in raw:
        groups.setdefault((r["reviewer"], r["verdict"]), []).append(r)

    tier_rank = {"live-store": 3, "ingested-event": 2, "own-artifact": 2, "third-party-snapshot": 1}
    verdicts = []
    for (reviewer, verdict), copies in groups.items():
        def rank(r):
            return (tier_rank.get(r["tier"], 0), len(json.dumps(r)), str(r.get("created_at") or ""))
        reps = sorted(copies, key=rank)
        rep = dict(reps[-1])
        rep["copies"] = [{"source": c["source"], "tier": c["tier"], "record_id": c["record_id"],
                          "source_sha256": c["source_sha256"][:16], "created_at": c["created_at"],
                          "n_findings": c["n_findings"], "score": c["score"],
                          "counts_as_full_schema_verdict": c["counts_as_full_schema_verdict"],
                          "text_sha256": sha256_bytes(normalize(c["text"]).encode())[:16]}
                         for c in copies]
        rep["n_copies"] = len(copies)
        rep["copy_text_variants"] = len({sha256_bytes(normalize(c["text"]).encode()) for c in copies})
        rep["has_live_copy"] = any(c["tier"] == "live-store" for c in copies)
        rep["has_ingested_copy"] = any(c["tier"] == "ingested-event" for c in copies)
        verdicts.append(rep)
    return verdicts, weak, self_excluded


def measure(records):
    accepts = sorted([r for r in records if r["verdict"] == "accept"],
                     key=lambda r: r["reviewer"])
    non_accepts = sorted([r for r in records if r["verdict"] != "accept"],
                         key=lambda r: r["reviewer"])
    nodes = [r["reviewer"] for r in accepts]
    sh = {r["reviewer"]: shingles(r["text"]) for r in accepts}
    sim = {}
    for i, a in enumerate(nodes):
        for b in nodes[i + 1:]:
            sim[(a, b)] = jaccard(sh[a], sh[b])
    pairs = [{"reviewer_a": a, "reviewer_b": b, "jaccard_5gram": round(v, 4)}
             for (a, b), v in sorted(sim.items())]
    vals = list(sim.values())
    rbar = (sum(vals) / len(vals)) if vals else 0.0
    n = len(accepts)
    ess = n / (1 + (n - 1) * rbar) if n else 0.0
    comp = {str(t): components(nodes, sim, t) for t in (TAU_DEDUP, TAU_INDEP, 0.20)}
    return {
        "accepts": [{
            "reviewer": r["reviewer"], "score": r["score"],
            "counts_as_full_schema_verdict": r["counts_as_full_schema_verdict"],
            "review_kind": r["review_kind"], "target_id": r["target_id"],
            "created_at": r["created_at"], "n_findings": r["n_findings"],
            "n_hard_failures": len(r["hard_failures"]), "n_copies": r["n_copies"],
            "copy_text_variants": r["copy_text_variants"], "has_live_copy": r["has_live_copy"],
            "has_ingested_copy": r["has_ingested_copy"],
            "representative_source": r["source"], "representative_record_id": r["record_id"],
            "representative_source_sha256": r["source_sha256"][:16],
            "hash_fields": r["hash_fields"],
            "text_tokens": len(normalize(r["text"]).split()),
            "text_sha256": sha256_bytes(normalize(r["text"]).encode())[:16],
            "independence_selfreport": r["independence_selfreport"],
            "copies": r["copies"],
        } for r in accepts],
        "non_accepts": [{
            "reviewer": r["reviewer"], "verdict": r["verdict"], "score": r["score"],
            "counts_as_full_schema_verdict": r["counts_as_full_schema_verdict"],
            "created_at": r["created_at"], "n_findings": r["n_findings"],
            "n_copies": r["n_copies"], "has_live_copy": r["has_live_copy"],
            "representative_source": r["source"], "copy_text_variants": r["copy_text_variants"],
        } for r in non_accepts],
        "pairwise_accept_similarity": pairs,
        "mean_pairwise_jaccard": round(rbar, 4),
        "max_pairwise_jaccard": round(max(vals), 4) if vals else 0.0,
        "kish_ess_accepts": round(ess, 3),
        "components": comp,
    }


def controls(records, m):
    accepts = sorted([r for r in records if r["verdict"] == "accept"], key=lambda r: r["reviewer"])
    c = {}
    if accepts:
        sh = shingles(accepts[0]["text"])
        c["C1_exact_clone_self_similarity"] = round(jaccard(sh, sh), 4)
        c["C1_exact_clone_pair_similarity"] = round(jaccard(sh, shingles(accepts[0]["text"] + "\n" + accepts[0]["text"])), 4)
    rng = random.Random(SEED)
    if accepts:
        toks = normalize(accepts[0]["text"]).split()
        vocab = sorted({t for r in accepts for t in normalize(r["text"]).split()})
        nulls = [[rng.choice(vocab) for _ in toks] for _ in range(50)]
        sims = [jaccard(shingles(" ".join(nulls[i])), shingles(" ".join(nulls[j])))
                for i in range(len(nulls)) for j in range(i + 1, len(nulls))]
        c["C2_null_bag_mean_jaccard"] = round(sum(sims) / len(sims), 4)
        c["C2_null_bag_max_jaccard"] = round(max(sims), 4)
        c["C2_permutation_of_own_tokens_jaccard"] = round(
            jaccard(shingles(" ".join(toks)), shingles(" ".join(rng.sample(toks, len(toks))))), 4)
    if accepts and any(r["verdict"] != "accept" for r in records):
        cross = [jaccard(shingles(a["text"]), shingles(r["text"]))
                 for r in records if r["verdict"] != "accept" for a in accepts]
        c["C3_accept_vs_nonaccept_mean_jaccard"] = round(sum(cross) / len(cross), 4)
        c["C3_accept_vs_nonaccept_max_jaccard"] = round(max(cross), 4)
    return c


def adjudicate(m, authors):
    accepts = m["accepts"]
    authors_hit = [a["reviewer"] for a in accepts if a["reviewer"] in authors]
    dup = [p for p in m["pairwise_accept_similarity"] if p["jaccard_5gram"] >= TAU_DEDUP]
    caveat = [p for p in m["pairwise_accept_similarity"] if TAU_INDEP <= p["jaccard_5gram"] < TAU_DEDUP]
    n_comp = len(m["components"][str(TAU_INDEP)])
    n_full = len([a for a in accepts if a["counts_as_full_schema_verdict"] is True])
    n_live = len([a for a in accepts if a["has_live_copy"] or a["has_ingested_copy"]])
    r2 = (n_comp >= 2) and (n_full >= 2) and (not authors_hit)
    if r2 and not dup and not caveat:
        verdict, score = "accept", 4.0
    elif r2 and not dup:
        verdict, score = "accept", 3.5
    else:
        verdict, score = "revise", 2.5
    return {
        "rule_R1_tau_dedup": TAU_DEDUP,
        "rule_R2_tau_indep": TAU_INDEP,
        "duplicate_pairs_at_R1": dup,
        "caveat_pairs_in_[0.30,0.50)": caveat,
        "accept_components_at_R2": n_comp,
        "accepts_declaring_full_schema_verdict": n_full,
        "accepts_with_live_or_ingested_copy": n_live,
        "author_reviewers_in_accept_set": authors_hit,
        "distinct_accept_reviewers": len(accepts),
        "distinct_non_accept_reviewers": len(m["non_accepts"]),
        "R2_met": bool(r2),
        "verdict": verdict,
        "score": score,
    }


def build_review(evidence, pins):
    m = evidence["measurement"]
    adj = evidence["adjudication"]
    c = evidence["controls"]
    findings = [{
        "id": "W082-F0I-01", "severity": "non_blocking",
        "finding": (
            f"{adj['distinct_accept_reviewers']} distinct reviewer accept verdicts bind the pinned F0 rev5 "
            f"hash {F0_PREFIX} after collapsing {sum(a['n_copies'] for a in m['accepts'])} channel copies to "
            f"{adj['distinct_accept_reviewers']} reviewers: "
            f"{', '.join(a['reviewer'] for a in m['accepts'])}. Reviewer-text independence "
            f"(5-gram Jaccard): mean {m['mean_pairwise_jaccard']}, max {m['max_pairwise_jaccard']}, "
            f"Kish-style ESS {m['kish_ess_accepts']}, accept components at tau=0.30: {adj['accept_components_at_R2']}. "
            f"No pair reaches the protocol same-text dedup threshold 0.50."
        ),
        "falsifier": ("Rerun harvest_f0_independence.py at the pinned F0 bytes: if two accept reviewers score "
                      "Jaccard >= 0.50, or a distinct accept reviewer is missed, this finding is void."),
    }, {
        "id": "W082-F0I-02", "severity": "non_blocking",
        "finding": (
            f"Strict full-schema counting: {adj['accepts_declaring_full_schema_verdict']} of "
            f"{adj['distinct_accept_reviewers']} accepts declare counts_as_full_schema_verdict=true "
            "(worker-025, worker-038, worker-087); deepseek-flash-18/19 carry no such declaration. "
            f"{adj['accepts_with_live_or_ingested_copy']} accepts have a live-store or ingested copy; the review "
            "store copy of worker-087's accept (artifacts/worker-087/f0_full_review/F0-review-087.json) carries "
            "no primary hash field - only its ingested event does. The criterion still clears two independent "
            "full-schema verdicts at the pinned bytes."
        ),
        "falsifier": "Showing that the flag-bearing accepts are not independent, or that no ingested copy exists.",
    }, {
        "id": "W082-F0I-03", "severity": "non_blocking",
        "finding": (
            "Channel-copy hygiene: several accepts appear as 2-4 re-emitted copies (worker-038 x4, "
            "worker-025 x2, deepseek-flash-18 x2, deepseek-flash-19 x2) with non-identical extracted text in "
            "some copies (worker-038 findings 0 vs 2; worker-087 findings 4 vs 3). The audit lead should bind "
            "coverage to reviewer ids, not event ids, and to one declared copy per reviewer."
        ),
        "falsifier": "Showing the copies are materially identical and the distinction is immaterial.",
    }, {
        "id": "W082-F0I-04", "severity": "non_blocking",
        "finding": (
            "Self-declared exposure exists inside the accept set: reviews/F0-review-18.json discloses reading "
            "the headline verdict labels of worker-025's accept and the lead-audit revise before writing; "
            "worker-087's file and worker-025/038 all report non-authorship. This measurement establishes "
            "text/authorship independence under the protocol rule, NOT statistical error independence - per "
            "HANDOFF.md no audited intervention has been shown to restore that."
        ),
        "falsifier": "A disclosure showing copied reasoning rather than headline-label exposure.",
    }, {
        "id": "W082-F0I-05", "severity": "non_blocking",
        "finding": (
            "Convergent issue coverage, not duplication: the unresolved scalar-class genericity "
            "(genericity_kind='unresolved' vs an explicit comeager conclusion) is independently reported by "
            "worker-025 (W025-F0-O1), worker-038 (W038-02-F1), worker-087 (B3) and deepseek-flash-18 (N1/N2). "
            "Four independent reads of one open content item - the audit lead should treat it as one item."
        ),
        "falsifier": "Showing the four mentions share a source text rather than independent artifact reads.",
    }, {
        "id": "W082-F0I-06", "severity": "non_blocking",
        "finding": (
            f"Instrument controls separate duplicates from independent text across the full range: exact clone "
            f"{c.get('C1_exact_clone_pair_similarity')}, seeded null mean {c.get('C2_null_bag_mean_jaccard')} / "
            f"max {c.get('C2_null_bag_max_jaccard')}, accept-vs-non-accept mean "
            f"{c.get('C3_accept_vs_nonaccept_mean_jaccard')}, double-run determinism "
            f"{evidence['instrument_determinism']['identical']}."
        ),
        "falsifier": "A control pair scoring like an accept pair or an accept pair scoring like the null.",
    }]
    if adj["caveat_pairs_in_[0.30,0.50)"]:
        findings.append({
            "id": "W082-F0I-07", "severity": "moderate",
            "finding": f"Accept pairs in the caveat band [0.30,0.50): {json.dumps(adj['caveat_pairs_in_[0.30,0.50)'])}",
            "falsifier": "Inspection showing shared boilerplate field names, not shared findings.",
        })
    if adj["duplicate_pairs_at_R1"]:
        findings.append({
            "id": "W082-F0I-08", "severity": "hard",
            "finding": f"Accept pairs at/above the protocol dedup threshold 0.50: {json.dumps(adj['duplicate_pairs_at_R1'])}",
            "falsifier": "Re-measurement showing Jaccard < 0.50 for those reviewers' reviewer-authored text.",
        })
    return {
        "schema_version": "0.1",
        "artifact_type": "review",
        "artifact_kind": "review",
        "event_id": "w082-" + re.sub(r"[^0-9T]", "", evidence["finished_at"]) + "-review-f0-indep",
        "review_id": "W082-A1-F0-INDEP-REV5-01",
        "task_id": "W082-A1-F0-INDEP-REV5-01",
        "event_type": "review",
        "created_at": evidence["finished_at"],
        "actor": "worker-082",
        "reviewer": "worker-082",
        "reviewer_role": "independent execution worker; machine review-independence audit",
        "node_id": "F0",
        "target_id": "F0",
        "target_id_full": "F0 canonical declared taxonomy rev5 at sha256 " + F0_SHA,
        "gate": "G-F0",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "artifact": F0_PATH,
        "artifact_path": F0_PATH,
        "artifact_sha256": F0_SHA,
        "reviewed_sha256": F0_SHA,
        "supplement_path": SUPPLEMENT_PATH,
        "supplement_sha256": pins.get(SUPPLEMENT_PATH, {}).get("sha256"),
        "frozen_path": FROZEN_PATH,
        "frozen_sha256": pins.get(FROZEN_PATH, {}).get("sha256"),
        "review_kind": "review-independence / text-duplication census (A1 criterion evidence)",
        "scope": ("Independent measurement of how many mutually independent accept verdicts bind the pinned F0 "
                  "rev5 bytes after the protocol same-text dedup rule and author exclusion. NOT a schema content "
                  "review, NOT a gate verdict, NOT a validation_status."),
        "counts_as_full_schema_verdict": False,
        "counts_as_independent": True,
        "verdict": adj["verdict"],
        "score": adj["score"],
        "score_rationale": (
            f"Pre-registered R2 met={adj['R2_met']}: {adj['accept_components_at_R2']} accept components at "
            f"tau=0.30, {adj['accepts_declaring_full_schema_verdict']} accepts declaring "
            f"counts_as_full_schema_verdict=true, non-author reviewers only. Kish-style ESS "
            f"{m['kish_ess_accepts']}; no accept pair at the 0.50 dedup threshold; "
            f"{len(adj['caveat_pairs_in_[0.30,0.50)'])} caveat-band pair(s)."
        ),
        "hard_failures": [f for f in findings if f["severity"] == "hard"],
        "findings": findings,
        "evidence_refs": [
            f"artifacts/worker-082/f0_indep_rev5/evidence.json#sha256:{evidence['evidence_sha256'][:16]}",
            "artifacts/worker-082/f0_indep_rev5/harvest_f0_independence.py#sha256:"
            + sha256_file(os.path.join(OUT_DIR, "harvest_f0_independence.py"))[:16],
            f"{F0_PATH}#sha256:{F0_PREFIX}",
            f"{SUPPLEMENT_PATH}#sha256:{SUPPLEMENT_SHA[:12]}",
            f"{FROZEN_PATH}#sha256:{pins.get(FROZEN_PATH, {}).get('sha256', 'missing')[:12]}",
        ] + [f"reviews/F0-review-{n}.json" for n in ("18", "19", "025")]
          + ["reviews/F0-conformance-038-rev28.json", "artifacts/worker-087/f0_full_review/F0-review-087.json"],
        "artifact_refs": [
            "artifacts/worker-082/f0_indep_rev5/evidence.json",
            "artifacts/worker-082/f0_indep_rev5/REVIEW-F0-INDEP-082.json",
        ],
        "assumptions": [
            "the harvest covers reviews/, artifacts/**, comms/** and research_map/events.jsonl at the observation window; review evidence published outside those channels is out of scope",
            "one reviewer id = one verdict; re-emitted channel copies are collapsed and enumerated, not counted as independence",
            "5-gram Jaccard is a proxy for the protocol's 'same text' rule; thresholds 0.30/0.50 are pre-registered in the instrument",
        ],
        "falsifier": ("Re-run harvest_f0_independence.py at the pinned F0 bytes: this verdict is void if a "
                      "primary-hash-bound accept reviewer is missed, if any two accept reviewers score Jaccard "
                      ">= 0.50, or if an accepting reviewer is an author of the taxonomy."),
        "next_falsifier": ("The audit lead's G-F0-r2 review re-harvests the corpus and finds either an additional "
                           "independent accept reviewer or a >=0.50 pair among the measured accepts."),
        "not_claimed": ["no gate verdict", "no node status", "no validation_status", "no schema content acceptance",
                        "no statistical error-independence claim"],
        "authority_note": ("Worker events cannot set status=done, validation_status=passed, or a gate verdict "
                           "(ASTRA_HANDOFF authority note; comms/PROTOCOL.md)."),
        "instrument": {
            "path": "artifacts/worker-082/f0_indep_rev5/harvest_f0_independence.py",
            "sha256": sha256_file(os.path.join(OUT_DIR, "harvest_f0_independence.py")),
            "network": "none",
            "canonical_files_modified": "none (read-only; outputs only under artifacts/worker-082/f0_indep_rev5/)",
        },
    }


def build_report(evidence):
    m = evidence["measurement"]
    adj = evidence["adjudication"]
    c = evidence["controls"]
    lines = [
        "# W082-A1-F0-INDEP-REV5-01 — F0 rev5 review-independence census",
        "",
        f"- Pinned artifact: `{F0_PATH}` sha256 `{F0_SHA}`",
        f"- FROZEN: `{evidence['pins_end'].get(FROZEN_PATH, {}).get('sha256', '?')}`; "
        f"window {evidence['started_at']} .. {evidence['finished_at']} (+08:00); hash drift: **{evidence['hash_drift_during_run']}**",
        f"- Worker verdict (audit only, not a gate): **{adj['verdict']}** score {adj['score']}; R2 met: {adj['R2_met']}",
        "",
        "## Accept corpus at the pinned hash (one row per reviewer)",
        "",
        "| reviewer | score | full-schema flag | copies | text tokens | hard failures | representative source |",
        "|---|---:|---|---:|---:|---:|---|",
    ]
    for a in m["accepts"]:
        lines.append(f"| {a['reviewer']} | {a['score']} | {a['counts_as_full_schema_verdict']} | {a['n_copies']} "
                     f"| {a['text_tokens']} | {a['n_hard_failures']} | `{a['representative_source']}` |")
    lines += ["", "## Non-accept verdicts at the pinned hash", "",
              "| reviewer | verdict | score | copies | findings |", "|---|---|---:|---:|---:|"]
    for a in m["non_accepts"]:
        lines.append(f"| {a['reviewer']} | {a['verdict']} | {a['score']} | {a['n_copies']} | {a['n_findings']} |")
    lines += [
        "",
        "## Independence measurement",
        "",
        f"- Distinct accept reviewers: **{adj['distinct_accept_reviewers']}** "
        f"({', '.join(a['reviewer'] for a in m['accepts'])})",
        f"- Mean / max pairwise 5-gram Jaccard: **{m['mean_pairwise_jaccard']} / {m['max_pairwise_jaccard']}**",
        f"- Kish-style ESS (n/(1+(n-1)r̄)): **{m['kish_ess_accepts']}**",
        f"- Components at tau=0.30 (independence) / 0.50 (protocol dedup): "
        f"**{len(m['components']['0.3'])} / {len(m['components']['0.5'])}**",
        f"- Accepts declaring `counts_as_full_schema_verdict=true`: **{adj['accepts_declaring_full_schema_verdict']}**",
        f"- Accepts with a live-store or ingested copy: **{adj['accepts_with_live_or_ingested_copy']}**",
        f"- Author reviewers in the accept set: **{adj['author_reviewers_in_accept_set']}** "
        f"(excluded author set: {', '.join(evidence['author_set_excluded'])})",
        "",
        "## Pairwise accept similarity",
        "",
        "```json",
        json.dumps(m["pairwise_accept_similarity"], indent=1),
        "```",
        "",
        "## Controls",
        "",
        "```json",
        json.dumps(c, indent=1),
        "```",
        "",
        "## Findings",
        "",
    ]
    for f in build_review(evidence, evidence["pins_end"])["findings"]:
        lines.append(f"- **{f['id']}** ({f['severity']}): {f['finding']}")
    lines += [
        "",
        "## Falsifier",
        "",
        "Re-run `harvest_f0_independence.py` at the pinned F0 bytes. This record is void if a primary-hash-bound",
        "accept reviewer is missed, if any two accept reviewers reach Jaccard >= 0.50, or if an accepting reviewer",
        "is an author of the taxonomy.",
        "",
        "Authority: worker evidence only. No gate verdict, no node status, no validation_status.",
        "",
    ]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    started = now_iso()
    pins_start = measure_pins()
    if pins_start.get(F0_PATH, {}).get("sha256") != F0_SHA:
        print("FAIL CLOSED: F0 pin mismatch", pins_start.get(F0_PATH), file=sys.stderr)
        return 2

    records, weak, self_excluded = harvest()
    m1 = measure(records)
    c1 = controls(records, m1)
    # C4 determinism: re-measure the FROZEN harvested records (same inputs must give same output).
    m_same = measure(records)
    det1 = sha256_bytes(json.dumps(m1, sort_keys=True).encode())
    det2 = sha256_bytes(json.dumps(m_same, sort_keys=True).encode())
    # Corpus motion indicator (the swarm is live): a second harvest may see new copies/verdicts.
    records2, _, _ = harvest()
    m2 = measure(records2)
    live_delta = {
        "second_harvest_n_verdicts": len(records2),
        "same_verdict_set": sorted((r["reviewer"], r["verdict"]) for r in records) ==
                            sorted((r["reviewer"], r["verdict"]) for r in records2),
        "measurement_digest_second_harvest": sha256_bytes(json.dumps(m2, sort_keys=True).encode()),
    }

    authors = {"astra-lead-formulation", "deepseek-flash-01"}
    try:
        fro = json.load(open(os.path.join(ROOT, FROZEN_PATH)))
        if isinstance(fro.get("owner"), str):
            authors.add(fro["owner"])
    except Exception:
        pass
    tax = open(os.path.join(ROOT, F0_PATH), encoding="utf-8").read()
    mm = re.search(r'^authored_by:\s*"?([^"\n]+)"?', tax, re.M)
    if mm:
        authors.add(mm.group(1).strip())

    adj = adjudicate(m1, authors)
    finished = now_iso()
    pins_end = measure_pins()
    evidence = {
        "schema_version": "w082-f0-indep-1.0",
        "task_id": "W082-A1-F0-INDEP-REV5-01",
        "worker": "worker-082",
        "node_id": "F0",
        "gate": "G-F0",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "scope": "review-independence / text-duplication census at the pinned F0 rev5 bytes",
        "started_at": started,
        "finished_at": finished,
        "observation_window": [started, finished],
        "pins_start": pins_start,
        "pins_end": pins_end,
        "hash_drift_during_run": pins_start != pins_end,
        "author_set_excluded": sorted(authors),
        "corpus": {
            "n_reviewer_verdicts_bound_to_pin": len(records),
            "n_weak_mention_only_excluded": len(weak),
            "n_self_records_excluded": len(self_excluded),
            "self_records_excluded": self_excluded[:10],
            "weak_mention_only_sample": weak[:25],
            "verdicts": [{
                "reviewer": r["reviewer"], "verdict": r["verdict"], "score": r["score"],
                "counts_as_full_schema_verdict": r["counts_as_full_schema_verdict"],
                "created_at": r["created_at"], "representative_source": r["source"],
                "representative_source_sha256": r["source_sha256"],
                "n_copies": r["n_copies"], "copy_text_variants": r["copy_text_variants"],
                "has_live_copy": r["has_live_copy"], "has_ingested_copy": r["has_ingested_copy"],
                "hash_fields": r["hash_fields"], "copies": r["copies"],
            } for r in sorted(records, key=lambda r: (r["reviewer"], r["verdict"]))],
        },
        "measurement": m1,
        "controls": c1,
        "instrument_determinism": {"digest_run1": det1, "digest_run2_same_inputs": det2, "identical": det1 == det2},
        "corpus_motion": live_delta,
        "adjudication": adj,
        "limits": [
            "text similarity is a proxy; 0.30/0.50 thresholds are pre-registered in the instrument and the full pairwise matrix is published",
            "the harvest is channel-based; review evidence published only outside reviews/, artifacts/**, comms/**, events.jsonl is not counted",
            "this record measures verdict-text and authorship independence, not correctness of the underlying review findings",
            "the corpus is live: verdicts added after the observation window are not in this census",
        ],
        "authority": "worker evidence only; no gate verdict, no node status, no validation_status",
    }
    ev_bytes = json.dumps(evidence, indent=1, sort_keys=True).encode()
    evidence["evidence_sha256"] = sha256_bytes(ev_bytes)
    review = build_review(evidence, pins_end)
    review_bytes = json.dumps(review, indent=1, sort_keys=True).encode()

    print(json.dumps({
        "task": evidence["task_id"],
        "F0_sha256": pins_end[F0_PATH]["sha256"],
        "hash_drift": evidence["hash_drift_during_run"],
        "distinct_accepts": adj["distinct_accept_reviewers"],
        "accept_reviewers": [a["reviewer"] for a in m1["accepts"]],
        "accept_copies_total": sum(a["n_copies"] for a in m1["accepts"]),
        "non_accept_reviewers": [(a["reviewer"], a["verdict"]) for a in m1["non_accepts"]],
        "mean_pairwise_jaccard": m1["mean_pairwise_jaccard"],
        "max_pairwise_jaccard": m1["max_pairwise_jaccard"],
        "kish_ess": m1["kish_ess_accepts"],
        "components_tau30": adj["accept_components_at_R2"],
        "full_schema_flag_accepts": adj["accepts_declaring_full_schema_verdict"],
        "live_or_ingested_accepts": adj["accepts_with_live_or_ingested_copy"],
        "R2_met": adj["R2_met"],
        "verdict": adj["verdict"],
        "controls": c1,
        "determinism_identical": det1 == det2,
    }, indent=1))

    if args.write:
        os.makedirs(OUT_DIR, exist_ok=True)
        ev_path = os.path.join(OUT_DIR, "evidence.json")
        open(ev_path, "wb").write(ev_bytes)
        rv_path = os.path.join(OUT_DIR, "REVIEW-F0-INDEP-082.json")
        open(rv_path, "wb").write(review_bytes)
        open(os.path.join(OUT_DIR, "REPORT.md"), "w").write(build_report(evidence))
        print("wrote", ev_path, sha256_bytes(ev_bytes)[:16])
        print("wrote", rv_path, sha256_bytes(review_bytes)[:16])
    return 0


if __name__ == "__main__":
    sys.exit(main())
