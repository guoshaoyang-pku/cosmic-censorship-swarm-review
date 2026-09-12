#!/usr/bin/env python3
"""
W48-GATE-COVERAGE-INTEGRITY-01 — independent, hash-pinned audit of the controller
gate-audit "distinct accept reviewer" counts (G-F0 / G-FORM / G-LIT).

WHY THIS EXISTS
  `research_map/astra_lifecycle.py::review_coverage()` scans only `reviews/*.json`.
  It has no supersession filter (a reviewer's later hash-bound revise does not remove
  their earlier accept) and no artifacts-side scan (review records written under
  `artifacts/<agent>/.../REVIEW.json` are invisible).  This instrument replicates the
  controller rule exactly, then measures what an extended rule (artifacts-side +
  canonical-path targets + supersession) returns on the same pinned bytes.

WHAT THIS IS NOT
  No gate verdict, no node status, no validation promotion, no schema-content review.
  It audits the *coverage arithmetic* of one map snapshot, nothing else.

READ-ONLY wrt the shared corpus. Writes only under --out-dir (default = this dir).

Exit codes: 0 clean; 2 a control failed; 3 a pinned input drifted during the run.
"""
import argparse
import ast
import hashlib
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime

CST = datetime.now().astimezone().tzinfo
INSTRUMENT_ID = "W48-GATE-COVERAGE-INTEGRITY-01"

# canonical artifact path -> node id (declared extension over the controller alias map)
PATH_TARGETS = {
    "research_map/formulation_taxonomy.yaml": "F0",
    "artifacts/formulation/formulation_taxonomy.yaml": "F0",
    "schemas/af_wcc_vacuum.yaml": "F1",
    "schemas/af_scc_c2_vacuum.yaml": "F2a",
    "schemas/af_scc_c0_vacuum.yaml": "F2b",
    "ledger/theorems.jsonl": "L0",
    "ledger/citation_audit.csv": "L1",
    "evaluation_rubric.yaml": "A0",
    "numerics/CONVERGENCE_PROTOCOL.md": "N0",
}
# node -> owner identities that must never be counted as independent reviewers
AUTHORS = {
    "F0": {"astra-lead-formulation", "lead-formulation", "deepseek-flash-01"},
    "F1": {"astra-lead-formulation", "lead-formulation"},
    "F2a": {"astra-lead-formulation", "lead-formulation"},
    "F2b": {"astra-lead-formulation", "lead-formulation"},
    "L0": {"astra-lead-literature", "lead-literature"},
    "A0": {"astra-lead-audit", "lead-audit"},
    "N0": {"astra-lead-numerics", "lead-numerics"},
}
EXCLUDE_DIR_PARTS = {"tmp", "mirror", "pinned", "snapshot", "snapshots", "__pycache__", ".git", "events"}
MAX_FILE_BYTES = 3_000_000
GATE_NODES = {"G-F0": ["F0"], "G-FORM": ["F1", "F2a", "F2b"], "G-LIT": ["L0"]}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def load_controller_rule(lifecycle_path):
    """Read VERDICT_KINDS / TARGET_ALIASES out of the controller source (provenance: its sha256)."""
    src = open(lifecycle_path, encoding="utf-8").read()
    tree = ast.parse(src)
    found = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            tgt = node.targets[0]
            if isinstance(tgt, ast.Name) and tgt.id in ("VERDICT_KINDS", "TARGET_ALIASES"):
                found[tgt.id] = ast.literal_eval(node.value)
    if "VERDICT_KINDS" not in found or "TARGET_ALIASES" not in found:
        raise SystemExit("could not extract VERDICT_KINDS/TARGET_ALIASES from " + lifecycle_path)
    return found["VERDICT_KINDS"], found["TARGET_ALIASES"]


def explicit_pins(d):
    """Verbatim semantics of astra_lifecycle._explicit_pins."""
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


def targets_in_review(d, aliases, extended=False):
    """Verbatim semantics of astra_lifecycle._targets_in_review, plus optional path mapping.

    extended=True additionally reads node_id / class_id, which the controller rule ignores.
    """
    out = set()
    keys = ("target_id", "target", "target_subnode") + (("node_id", "class_id") if extended else ())
    for key in keys:
        v = d.get(key)
        if isinstance(v, str):
            out.add(v)
        elif isinstance(v, dict):
            for k2 in ("target_id", "target_subnode", "subnode", "node_id"):
                if isinstance(v.get(k2), str):
                    out.add(v[k2])
    norm = set()
    for t in out:
        norm.add(aliases.get(t, aliases.get(t.upper(), t)))
    return norm, out


def path_targets(raw_targets):
    hits = set()
    for t in raw_targets:
        base = t.split("#", 1)[0].strip()
        if base in PATH_TARGETS:
            hits.add(PATH_TARGETS[base])
    return hits


def matches(pin, anchor):
    """Prefix match against the 12-hex anchor the map recorded at the audited snapshot."""
    p, a = pin.lower().strip(), (anchor or "").lower().strip()
    return bool(a) and (p.startswith(a[:12]) or a.startswith(p[:12]))


def walk_candidates(root, out_dir_abs):
    """reviews/*.json (canonical) + artifacts/**/*.json (extended), excluding snapshot copies."""
    files = []
    rev_dir = os.path.join(root, "reviews")
    if os.path.isdir(rev_dir):
        for n in sorted(os.listdir(rev_dir)):
            if n.endswith(".json"):
                files.append(os.path.join(rev_dir, n))
    art_dir = os.path.join(root, "artifacts")
    for dirpath, dirnames, filenames in os.walk(art_dir):
        dirnames[:] = [d for d in dirnames
                       if d not in EXCLUDE_DIR_PARTS
                       and "sandbox" not in d.lower()
                       and not d.lower().startswith("controls")]
        if os.path.abspath(dirpath).startswith(out_dir_abs):
            dirnames[:] = []
            continue
        for n in filenames:
            if n.endswith(".json"):
                files.append(os.path.join(dirpath, n))
    return files


def collect(root, out_dir_abs):
    recs = []
    for p in walk_candidates(root, out_dir_abs):
        try:
            if os.path.getsize(p) > MAX_FILE_BYTES:
                continue
            d = json.load(open(p, encoding="utf-8", errors="replace"))
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        recs.append({"path": os.path.relpath(p, root), "abs": p, "d": d,
                     "sha256": sha256_file(p),
                     "mtime": datetime.fromtimestamp(os.path.getmtime(p), CST).isoformat()})
    return recs


def verdict_of(d, kinds):
    v = str(d.get("verdict", "")).lower()
    return v if v in kinds else None


def reviewer_of(d, extended=False):
    keys = ("reviewer", "actor") + (("worker", "worker_id", "agent", "author_id") if extended else ())
    for k in keys:
        v = d.get(k)
        if isinstance(v, str) and v:
            return v
    return "?"


def created_of(rec):
    d = rec.get("d")
    c = d.get("created_at") if isinstance(d, dict) else rec.get("created_at")
    if isinstance(c, str) and c:
        return c
    return None


def effective_time(rec):
    """created_at when present, else mtime; returns sortable string."""
    return created_of(rec) or rec["mtime"]


def scan(recs, anchors, aliases, kinds, use_artifacts, use_path_map, use_hash_only,
         extended_keys=None):
    """Return {node: {file: entry}} for hash-bound verdicts under a declared rule variant.

    Variant A  : canonical reviews/*.json, alias targets only (the controller's rule)
    Variant B  : + artifacts-side first-party review records
    Variant C  : B + canonical-path targets (schemas/..., ledger/..., ...)
    Variant D  : C + hash-only attribution for a record that names no target but pins
                 exactly one node's recorded anchor (most inclusive; used for the census)
    """
    out = defaultdict(dict)
    for rec in recs:
        d = rec["d"]
        v = verdict_of(d, kinds)
        if not v:
            continue
        p = rec["path"]
        if not use_artifacts and p.startswith("artifacts/"):
            continue
        if use_artifacts and p.startswith("artifacts/") and "review" not in p.lower():
            continue
        if extended_keys is None:
            extended_keys = bool(use_artifacts)
        tg, raw = targets_in_review(d, aliases, extended=extended_keys)
        if use_path_map:
            tg = set(tg) | path_targets(raw)
        pins = explicit_pins(d)
        if use_hash_only and not tg:
            hit = [n for n, a in anchors.items() if any(matches(x, a) for x in pins)]
            if len(hit) == 1:
                tg = {hit[0]}
        for t in tg:
            a = anchors.get(t)
            if not a:
                continue
            if any(matches(x, a) for x in pins):
                out[t][rec["path"]] = {
                    "file": rec["path"], "reviewer": reviewer_of(d, extended=extended_keys), "verdict": v,
                    "counts_as_full_schema_verdict": d.get("counts_as_full_schema_verdict"),
                    "full": d.get("counts_as_full_schema_verdict") is not False,
                    "created_at": created_of(rec), "mtime": rec["mtime"],
                    "sha256": rec["sha256"],
                }
    return out


def full_accept_reviewers(node_map):
    """Distinct identified reviewers among full accepts; '?' (no reviewer/actor) is not a person."""
    return sorted({e["reviewer"] for e in node_map.values()
                   if e["verdict"] == "accept" and e["full"] and e["reviewer"] != "?"})


def unidentified_accepts(node_map):
    return sorted({e["file"] for e in node_map.values()
                   if e["verdict"] == "accept" and e["full"] and e["reviewer"] == "?"})


def supersession(node_map):
    """A reviewer's later hash-bound revise/reject retracts their earlier accept."""
    retracted, latest = [], {}
    by_reviewer = defaultdict(list)
    for e in node_map.values():
        by_reviewer[e["reviewer"]].append(e)
    for rev, entries in by_reviewer.items():
        entries.sort(key=lambda e: (effective_time(e), e["file"]))
        latest[rev] = entries[-1]["verdict"]
        if entries[-1]["verdict"] in ("revise", "reject"):
            for e in entries[:-1]:
                if e["verdict"] == "accept":
                    retracted.append({"reviewer": rev, "accept_file": e["file"],
                                      "accept_created_at": e["created_at"],
                                      "retracted_by": entries[-1]["file"],
                                      "retracting_verdict": entries[-1]["verdict"],
                                      "retracted_at": entries[-1]["created_at"]})
    return retracted, latest


def recorded_counts(map_doc):
    cga = map_doc.get("controller_gate_audit", {})
    out = {}
    for gate, nodes in GATE_NODES.items():
        reason = str(cga.get(gate, {}).get("reason", ""))
        if gate == "G-F0":
            m = re.search(r"(\d+)\s+distinct accept reviewer\(s\)(?:\s*\[([^\]]*)\])?", reason)
            out["F0"] = {"gate": gate, "count": int(m.group(1)) if m else None,
                         "reviewers": (m.group(2) if m and m.group(2) else "").strip(),
                         "checked_at": cga.get(gate, {}).get("checked_at")}
        else:
            for node in nodes:
                m = re.search(re.escape(node) + r"\s*\[(\d+)\s+distinct accept reviewer\(s\)(?:\s*\[([^\]]*)\])?\]", reason)
                out[node] = {"gate": gate, "count": int(m.group(1)) if m else None,
                             "reviewers": (m.group(2) if m and m.group(2) else "").strip(),
                             "checked_at": cga.get(gate, {}).get("checked_at")}
    return out


# ---------------------------------------------------------------- controls
def build_controls(ctrl_root, hashes, aliases, kinds):
    """Synthetic corpus exercising each declared classification rule."""
    def put(rel, obj):
        p = os.path.join(ctrl_root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        json.dump(obj, open(p, "w"), indent=1)

    h1 = hashes["F1"]
    base = {"target_id": "F1", "artifact": "schemas/af_wcc_vacuum.yaml",
            "counts_as_full_schema_verdict": True}
    put("reviews/c1-clean-a.json", dict(base, reviewer="ctrl-a", verdict="accept",
                                        reviewed_sha256=h1, created_at="2026-09-12T00:01:00+08:00"))
    put("reviews/c1-clean-b.json", dict(base, reviewer="ctrl-b", verdict="accept",
                                        reviewed_sha256=h1, created_at="2026-09-12T00:02:00+08:00"))
    put("reviews/c2-retract-a.json", dict(base, reviewer="ctrl-c", verdict="accept",
                                          reviewed_sha256=h1, created_at="2026-09-12T00:03:00+08:00"))
    put("reviews/c2-retract-b.json", dict(base, reviewer="ctrl-c", verdict="revise",
                                          reviewed_sha256=h1, created_at="2026-09-12T00:04:00+08:00"))
    put("reviews/c3-unbound.json", dict(base, reviewer="ctrl-d", verdict="accept",
                                        created_at="2026-09-12T00:05:00+08:00"))
    put("reviews/c4-scoped.json", dict(base, reviewer="ctrl-e", verdict="accept",
                                       counts_as_full_schema_verdict=False,
                                       reviewed_sha256=h1, created_at="2026-09-12T00:06:00+08:00"))
    put("artifacts/worker-ctrl/art_only/REVIEW.json", dict(base, reviewer="ctrl-f", verdict="accept",
                                                           reviewed_sha256=h1, created_at="2026-09-12T00:07:00+08:00"))
    put("artifacts/worker-ctrl/tmp/mirror/reviews/copy.json", dict(base, reviewer="ctrl-g", verdict="accept",
                                                                   reviewed_sha256=h1, created_at="2026-09-12T00:08:00+08:00"))
    put("reviews/c8-path-target.json", dict(base, reviewer="ctrl-h", verdict="accept",
                                            target_id="schemas/af_wcc_vacuum.yaml",
                                            reviewed_sha256=h1,
                                            counts_as_full_schema_verdict=True,
                                            created_at="2026-09-12T00:09:00+08:00"))
    put("reviews/c9-hash-only.json", {"reviewer": "ctrl-i", "verdict": "accept",
                                      "reviewed_sha256": h1,
                                      "counts_as_full_schema_verdict": True,
                                      "created_at": "2026-09-12T00:11:00+08:00"})
    put("artifacts/worker-ctrl/author_accept/REVIEW.json", dict(base, reviewer="astra-lead-formulation",
                                                                verdict="accept", reviewed_sha256=h1,
                                                                created_at="2026-09-12T00:10:00+08:00"))
    recs = collect(ctrl_root, "/nonexistent")
    anchors = dict(hashes)
    variants = {
        "ctrl_reviews_only": scan(recs, anchors, aliases, kinds, False, False, False),
        "ctrl_extended": scan(recs, anchors, aliases, kinds, True, False, False),
        "ctrl_extended_pathmap": scan(recs, anchors, aliases, kinds, True, True, False),
        "ctrl_extended_pathmap_hashonly": scan(recs, anchors, aliases, kinds, True, True, True),
    }
    checks = []

    def chk(cid, cond, detail):
        checks.append({"control": cid, "pass": bool(cond), "detail": detail})

    a = variants["ctrl_reviews_only"].get("F1", {})
    b = variants["ctrl_extended"].get("F1", {})
    c = variants["ctrl_extended_pathmap"].get("F1", {})
    ret1, _ = supersession(a)
    adj_a = [r for r in full_accept_reviewers(a) if r not in {x["reviewer"] for x in ret1}]
    chk("C1-clean-pair", adj_a == ["ctrl-a", "ctrl-b"],
        "reviews-only adjusted accepts=%s" % adj_a)
    ret, _ = supersession(a)
    chk("C2-retraction", [r["reviewer"] for r in ret] == ["ctrl-c"],
        "retracted=%s" % [r["reviewer"] for r in ret])
    chk("C3-unbound-not-counted", "ctrl-d" not in full_accept_reviewers(a),
        "accepts=%s" % full_accept_reviewers(a))
    chk("C4-scoped-not-counted", "ctrl-e" not in full_accept_reviewers(a),
        "accepts=%s" % full_accept_reviewers(a))
    chk("C5-artifacts-only-hidden-from-reviews-scan", "ctrl-f" not in full_accept_reviewers(a)
        and "ctrl-f" in full_accept_reviewers(b),
        "reviews-only=%s extended=%s" % (full_accept_reviewers(a), full_accept_reviewers(b)))
    chk("C6-snapshot-copy-excluded", "ctrl-g" not in full_accept_reviewers(b),
        "extended accepts=%s" % full_accept_reviewers(b))
    chk("C7-path-target-hidden-from-alias-scan", "ctrl-h" not in full_accept_reviewers(b)
        and "ctrl-h" in full_accept_reviewers(c),
        "extended=%s pathmap=%s" % (full_accept_reviewers(b), full_accept_reviewers(c)))
    chk("C8-author-identity-visible", "astra-lead-formulation" in full_accept_reviewers(b),
        "author accept is measured, flagged separately")
    d = variants["ctrl_extended_pathmap_hashonly"].get("F1", {})
    chk("C9-hash-only-attribution", "ctrl-i" in full_accept_reviewers(d),
        "hash-only accepts=%s" % full_accept_reviewers(d))
    return checks, variants


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out-dir", default=os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--snapshot", default=None,
                    help="pinned lifecycle JSON whose controller_gate_audit is under audit")
    args = ap.parse_args()
    root = os.path.abspath(args.root)
    out_dir = os.path.abspath(args.out_dir)
    out_dir_abs = out_dir.rstrip(os.sep) + os.sep

    lifecycle = os.path.join(root, "research_map", "astra_lifecycle.py")
    map_path = os.path.join(root, "research_map", "research_map.json")
    kinds, aliases = load_controller_rule(lifecycle)
    map_doc = json.load(open(map_path, encoding="utf-8"))
    snap, snap_sha, snap_cov = None, None, {}
    if args.snapshot:
        snap = json.load(open(args.snapshot, encoding="utf-8"))
        snap_sha = sha256_file(args.snapshot)
        snap_cov = snap.get("review_coverage", {}) or {}
    hashes = {}
    for node in ("F0", "F1", "F2a", "F2b", "L0"):
        gate = {"F0": "G-F0", "F1": "G-FORM", "F2a": "G-FORM", "F2b": "G-FORM", "L0": "G-LIT"}[node]
        reason = str(map_doc.get("controller_gate_audit", {}).get(gate, {}).get("reason", ""))
        pats = {"F0": r"canonical taxonomy ([0-9a-f]{12})",
                "F1": r"(cce9c60146d6)",
                "F2a": r"(5476a3f2c6bc)",
                "F2b": r"(55d0a1ea9bda)",
                "L0": r"L0 measured ([0-9a-f]{12})"}
        m = re.search(pats[node], reason)
        hashes[node] = m.group(1) if m else ""
    # full hashes for matching: resolve 12-prefix against the artifact files
    full_hashes = {}
    for node, path in (("F0", "research_map/formulation_taxonomy.yaml"),
                       ("F1", "schemas/af_wcc_vacuum.yaml"),
                       ("F2a", "schemas/af_scc_c2_vacuum.yaml"),
                       ("F2b", "schemas/af_scc_c0_vacuum.yaml"),
                       ("L0", "ledger/theorems.jsonl")):
        p = os.path.join(root, path)
        if os.path.isfile(p):
            h = sha256_file(p)
            if not hashes.get(node) or h.startswith(hashes[node][:12]):
                full_hashes[node] = h
            else:
                full_hashes[node] = h  # record both; drift surfaced below
    pins = {"research_map/astra_lifecycle.py": sha256_file(lifecycle),
            "research_map/research_map.json": sha256_file(map_path)}
    for node, path in (("F0", "research_map/formulation_taxonomy.yaml"),
                       ("F1", "schemas/af_wcc_vacuum.yaml"),
                       ("F2a", "schemas/af_scc_c2_vacuum.yaml"),
                       ("F2b", "schemas/af_scc_c0_vacuum.yaml"),
                       ("L0", "ledger/theorems.jsonl")):
        p = os.path.join(root, path)
        pins[path] = sha256_file(p) if os.path.isfile(p) else "absent"

    recs = collect(root, out_dir_abs)
    corpus_pins = {r["path"]: r["sha256"] for r in recs}

    anchors = dict(hashes)  # the 12-hex prefixes the audited snapshot recorded
    if snap and snap.get("measured_hashes"):
        for n in ("F0", "F1", "F2a", "F2b", "L0"):
            h = (snap["measured_hashes"].get(n) or {}).get("sha256")
            if isinstance(h, str) and h:
                anchors[n] = h
    variants = {
        "A_reviews_only_controller_rule": scan(recs, anchors, aliases, kinds, False, False, False),
        "B_extended_artifacts": scan(recs, anchors, aliases, kinds, True, False, False),
        "C_extended_pathmap": scan(recs, anchors, aliases, kinds, True, True, False),
        "D_extended_pathmap_hashonly": scan(recs, anchors, aliases, kinds, True, True, True),
    }
    recorded = recorded_counts(snap if snap else map_doc)
    nodes = ["F0", "F1", "F2a", "F2b", "L0"]
    table = {}
    for node in nodes:
        node_report = {"recorded_in_map": recorded.get(node), "variants": {}}
        for vname, vmap in variants.items():
            nm = vmap.get(node, {})
            ret, latest = supersession(nm)
            accs = full_accept_reviewers(nm)
            retracted_reviewers = {r["reviewer"] for r in ret}
            node_report["variants"][vname] = {
                "bound_verdicts": sorted(({"file": e["file"], "reviewer": e["reviewer"],
                                           "verdict": e["verdict"], "full": e["full"],
                                           "created_at": e["created_at"]} for e in nm.values()),
                                         key=lambda x: (x["reviewer"], x["file"])),
                "full_accept_reviewers": accs,
                "full_accept_count": len(accs),
                "author_reviewers_present": sorted(set(accs) & AUTHORS.get(node, set())),
                "unidentified_reviewer_accepts": unidentified_accepts(nm),
                "retracted_accepts": ret,
                "adjusted_full_accept_reviewers": [r for r in accs if r not in retracted_reviewers],
                "adjusted_full_accept_count": len([r for r in accs if r not in retracted_reviewers]),
            }
        table[node] = node_report

    # controls
    ctrl_root = os.path.join(out_dir, "controls_corpus")
    if os.path.isdir(ctrl_root):
        import shutil
        shutil.rmtree(ctrl_root)
    controls, ctrl_variants = build_controls(ctrl_root, full_hashes, aliases, kinds)
    controls_pass = all(c["pass"] for c in controls)

    # reproduce guard: census-relevant drift fails closed; ambient writes are reported only
    census_files = set()
    for vmap in variants.values():
        for nm in vmap.values():
            census_files.update(nm.keys())
    drift, ambient = [], []
    for rel, h in pins.items():
        if rel == args.snapshot or (args.snapshot and os.path.abspath(rel) == os.path.abspath(args.snapshot)):
            continue
        p = os.path.join(root, rel)
        now = sha256_file(p) if os.path.isfile(p) else "absent"
        if now != h:
            drift.append({"path": rel, "at_snapshot": h, "at_end": now})
    for r in recs:
        if os.path.isfile(r["abs"]):
            now = sha256_file(r["abs"])
            if now != r["sha256"]:
                (drift if r["path"] in census_files else ambient).append(
                    {"path": r["path"], "at_snapshot": r["sha256"], "at_end": now})

    # controller self-replication: variant A raw accept set vs the snapshot's own review_coverage
    replication = {}
    for node in nodes:
        raw_a = sorted({e["reviewer"] for e in variants["A_reviews_only_controller_rule"].get(node, {}).values()
                        if e["verdict"] == "accept" and e["full"] and e["reviewer"] != "?"})
        ctl = sorted((snap_cov.get(node) or {}).get("distinct_accept_reviewers", []))
        replication[node] = {"variant_A_raw_accept_reviewers": raw_a,
                             "snapshot_review_coverage_accept_reviewers": ctl,
                             "agree": raw_a == ctl}
    findings = []
    c_census = {n: table[n]["variants"]["D_extended_pathmap_hashonly"]["adjusted_full_accept_reviewers"] for n in nodes}
    for node in nodes:
        rec = table[node]["recorded_in_map"] or {}
        c = table[node]["variants"]["D_extended_pathmap_hashonly"]
        a = table[node]["variants"]["A_reviews_only_controller_rule"]
        recorded_set = set(re.findall(r"[A-Za-z0-9_.\-]+", rec.get("reviewers") or ""))
        identity_changed = recorded_set != set(c["adjusted_full_accept_reviewers"])
        if rec.get("count") is not None and (rec["count"] != c["adjusted_full_accept_count"]
                                             or identity_changed):
            findings.append({
                "id": "W48-GCI-%s" % node,
                "node": node,
                "recorded_count": rec["count"],
                "recorded_reviewers": rec.get("reviewers"),
                "identity_changed": identity_changed,
                "corrected_count": c["adjusted_full_accept_count"],
                "corrected_reviewers": c["adjusted_full_accept_reviewers"],
                "reviews_only_count": a["adjusted_full_accept_count"],
                "retracted": c["retracted_accepts"],
                "invisible_to_reviews_only_scan": sorted(
                    {e["file"] for e in c["bound_verdicts"] if e["verdict"] == "accept" and e["full"]}
                    - {e["file"] for e in a["bound_verdicts"] if e["verdict"] == "accept" and e["full"]}),
                "gate_effect": ("criterion met (>=2)" if c["adjusted_full_accept_count"] >= 2
                                else "criterion NOT met (%d/2)" % c["adjusted_full_accept_count"]),
            })

    report = {
        "instrument": INSTRUMENT_ID,
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "snapshot": {"root": root, "gate_audit_snapshot": args.snapshot,
                     "gate_audit_snapshot_sha256": snap_sha,
                     "map_sha256": pins["research_map/research_map.json"],
                     "lifecycle_sha256": pins["research_map/astra_lifecycle.py"],
                     "measured_canonical_hashes": pins,
                     "recorded_anchor_prefixes": anchors,
                     "live_vs_recorded_canonical": {
                         n: {"recorded_prefix": anchors.get(n),
                             "live_sha256": full_hashes.get(n),
                             "match": bool(anchors.get(n)) and str(full_hashes.get(n, "")).startswith(anchors[n][:12])}
                         for n in nodes},
                     "controller_gate_audit_checked_at": {n: (recorded.get(n) or {}).get("checked_at")
                                                          for n in nodes},
                     "review_records_scanned": len(recs)},
        "rule_under_audit": {
            "source": "research_map/astra_lifecycle.py::review_coverage",
            "scanned_glob": "reviews/*.json",
            "dedup_key": "distinct reviewer label among accepts with counts_as_full_schema_verdict != False",
            "no_supersession_filter": True,
            "no_artifacts_side_scan": True,
            "target_aliases": aliases,
        },
        "corrected_census": {n: {"count": len(c_census[n]), "reviewers": c_census[n]} for n in nodes},
        "per_node": table,
        "findings": findings,
        "controller_self_replication": replication,
        "controls": controls,
        "controls_all_pass": controls_pass,
        "reproduce_guard": {"drift": drift, "stable": not drift,
                            "ambient_writes_not_fatal": ambient,
                            "records_pinned": len(corpus_pins)},
        "falsifier": (
            "At the sha256 pins recorded in snapshot.measured_canonical_hashes and the per-record "
            "sha256 in snapshot.records: (a) any verdict I mark retracted for which no later hash-bound "
            "revise/reject by the same reviewer exists; (b) any corrected count that a re-run of this "
            "instrument, or an independent implementation of the published rule, does not reproduce; "
            "(c) any file I count that is a snapshot/mirror copy rather than a first-party verdict; "
            "(d) any control that does not classify as declared. A later write to the live corpus is a "
            "new revision to re-run against, not a falsifier of the snapshot."),
        "not_claimed": ["no gate verdict", "no node status", "no validation_status promotion",
                        "no schema-content review", "no claim that any schema or ledger is correct"],
    }
    os.makedirs(out_dir, exist_ok=True)
    json.dump(report, open(os.path.join(out_dir, "report.json"), "w"), indent=1)
    json.dump({"instrument": INSTRUMENT_ID,
               "created_at": report["created_at"],
               "pins": pins,
               "corpus_record_sha256": corpus_pins},
              open(os.path.join(out_dir, "snapshot_manifest.json"), "w"), indent=1)
    print(json.dumps({"findings": findings, "controls_all_pass": controls_pass,
                      "drift": drift, "records": len(recs)}, indent=1))
    if not controls_pass:
        return 2
    if drift:
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
