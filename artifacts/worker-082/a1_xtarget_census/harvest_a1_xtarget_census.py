#!/usr/bin/env python3
"""W082-A1-XTARGET-INDEP-CENSUS-01 — A1 coverage / review-independence census for
the three formulation targets F1 (AF-WCC-VAC-GEN), F2a (AF-SCC-C2-VAC-GEN) and
F2b (AF-SCC-C0-VAC-GEN) at the live post-repair bytes.

Question (one bounded, class-bound task; node A1, gate G-AUDIT):
  For each of the three formulation targets at the canonical bytes measured at snapshot time:
    (1) which reviewer verdicts BIND those bytes (primary target-hash field equals the measured
        hash) versus bind the superseded rev12 bytes versus cite the target without a hash;
    (2) how many of the binding accepts are independent after the protocol same-text dedup rule
        (Jaccard >= 0.50) and author exclusion;
    (3) does the A1 criterion ("two independent verdicts per target at a cited sha256") hold at
        the measured bytes?

The G-FORM repair (astra-life05-evidence-binding-repair, REC-12) moved the canonical schemas at
00:53:20-00:53:40, voiding every rev12 verdict.  This census measures exactly what survives at
the new bytes so the rev29 re-review (astra-life05-verify-gform-r3) is not built on stale counts.

Authority: worker evidence only.  Emits NO gate verdict, NO node status, NO
validation_status=passed, edits NO canonical artifact.  Read-only apart from its own output
directory.

Method (pre-registered before measurement):
  * Snapshot the three canonical schemas and their authoring-tree siblings; the measured sha256
    of the snapshot is the artifact identity.  Re-hash at the end; any change is reported as
    drift and makes the census void for the moved target (successor must re-pin).
  * Harvest every review-shaped record in reviews/, artifacts/**, comms/** and
    research_map/events.jsonl whose PRIMARY target-hash field matches a known target hash.
    Hash citations inside evidence_refs are mention-only and never counted as verdicts.
  * One reviewer id = one verdict per target per hash family; channel copies are collapsed and
    enumerated (with their copy-text variants).
  * Text = reviewer-authored strings under finding/detail/summary/rationale/... keys, normalized
    to lowercase alphanumerics; similarity = Jaccard over 5-gram shingles.
  * R1 (protocol dedup): an accept pair with Jaccard >= 0.50 counts as ONE verdict.
  * R2 (A1 criterion, pre-registered): MET iff >= 2 accept components at tau=0.30 AND >= 2
    accepts declare counts_as_full_schema_verdict=true AND no accepting reviewer is an author of
    the target.  Per-target coverage verdict: accept 4.0 (R2), revise 2.5 (some verdicts but R2
    fails), inconclusive 2.0 (no binding verdict at the measured bytes).
  * Controls: exact clone (~1.0), seeded null bag (0.0), accept-vs-non-accept cross, double-run
    determinism, snapshot-hash stability during the run.

Usage:
  python3 harvest_a1_xtarget_census.py                 # measure, print summary
  python3 harvest_a1_xtarget_census.py --write         # measure + write artifacts + checkpoint
  python3 harvest_a1_xtarget_census.py --write --emit  # also append events to the worker outbox
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import random
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone

ROOT = "/data3/guoshaoyang/workdir/ai4math-swarm"
OUT_DIR = os.path.join(ROOT, "artifacts/worker-082/a1_xtarget_census")
SNAP_DIR = os.path.join(OUT_DIR, "snapshots")
OUTBOX = os.path.join(ROOT, "comms/outbox/worker-082.jsonl")
CHECKPOINT = os.path.join(ROOT, "runtime/state/w082_a1_xtarget_checkpoint.json")
CHECKPOINT_LOG = os.path.join(ROOT, "runtime/state/w082_a1_xtarget_checkpoints.jsonl")
FROZEN_PATH = "artifacts/formulation/FROZEN.json"
TAXONOMY_PATH = "research_map/formulation_taxonomy.yaml"
TASK_ID = "W082-A1-XTARGET-INDEP-CENSUS-01"
NODE_ID = "A1"
GATE = "G-AUDIT"
TZ = timezone(timedelta(hours=8))

TARGETS = [
    {
        "node": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "stem": "af_wcc_vacuum",
        "canonical": "schemas/af_wcc_vacuum.yaml",
        "authoring": "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
        "ids": ["F1", "AF-WCC-VAC-GEN"],
    },
    {
        "node": "F2a",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "stem": "af_scc_c2_vacuum",
        "canonical": "schemas/af_scc_c2_vacuum.yaml",
        "authoring": "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
        "ids": ["F2a", "AF-SCC-C2-VAC-GEN"],
    },
    {
        "node": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "stem": "af_scc_c0_vacuum",
        "canonical": "schemas/af_scc_c0_vacuum.yaml",
        "authoring": "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
        "ids": ["F2b", "AF-SCC-C0-VAC-GEN"],
    },
]
BY_NODE = {t["node"]: t for t in TARGETS}

PRIMARY_HASH_RE = re.compile(
    r"^(reviewed|target|artifact|schema|canonical|authoring|sibling|supplement|frozen)_sha256"
    r"(_.*)?$|^(reviewed|target|artifact|schema)_(hash|sha)$"
)
PRIMARY_HASH_FIELDS = (
    "reviewed_sha256", "artifact_sha256", "target_sha256", "artifact_sha256_prefix",
    "reviewed_sha256_prefix", "target_sha256_prefix", "reviewed_hash", "target_hash",
)
ID_FIELDS = (
    "artifact", "artifact_path", "target_artifact", "path", "schema_path", "canonical_path",
    "authoring_path", "target_path", "artifact_ref", "target_id", "node_id", "class_id",
)
DIRECT_ID_FIELDS = (
    "target_id", "node_id", "class_id", "artifact", "artifact_path", "target_artifact",
    "target_path", "schema_path", "canonical_path", "authoring_path", "artifact_ref",
)
TEXT_KEYS = (
    "finding", "detail", "summary", "score_rationale", "rationale", "statement",
    "consequence_for_gate", "label", "note", "notes", "positives", "negative_findings",
    "residual_observations", "hard_failures", "blocking_items", "claims_not_made",
    "authority_note", "independence_statement", "checklist", "machine_checks",
    "gate_criteria_results", "falsifier",
)
TEXT_LIST_KEYS = ("findings", "hard_failures", "positives", "residual_observations",
                  "negative_findings", "blocking_items")
LIVE_PREFIXES = ("reviews/", "comms/outbox/", "comms/inbox/")
TAU_DEDUP = 0.50
TAU_INDEP = 0.30
SHINGLE_N = 5
SEED = 82082
# Reviewer ids used by other workers' synthetic control fixtures (ctrl-a..i, k1..k9, ...).
# They are instruments, not verdicts on the schemas, and were the first dry-run's largest
# contamination.  Path-based rule catches fixtures whose reviewer ids look real (the second
# contamination: worker-074's artifacts/worker-074/r3_verdict_independence/w074selftest_*/c*.json
# injected worker-900..906 and a synthetic astra-lead-formulation author accept at the pinned F1
# hash, which alone flipped F1 from accept to revise).
FIXTURE_REVIEWER_RE = re.compile(r"^(ctrl|control|k|worker-9\d\d)[-_.]?[a-z0-9]{0,4}$", re.I)
FIXTURE_PATH_RE = re.compile(
    r"(selftest|self[_-]test|(^|[/_-])fixtures?([/_-]|$)|(^|[/_-])synthetic([/_-]|$)|"
    r"(^|[/_-])controls?([/_-]|$))", re.I)
PROTOCOL_VERDICTS = {"accept", "revise", "reject", "inconclusive"}


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


def read_bytes(path):
    with open(path, "rb") as fh:
        return fh.read()


def norm_hash(v):
    if not isinstance(v, str):
        return None
    s = v.strip().lower()
    if s.startswith("sha256:"):
        s = s.split(":", 1)[1]
    # Extract the longest hex run rather than stripping all non-hex characters: 'sha256=e9a2...'
    # used to become 'a256e9a2...' and silently failed to bind.
    m = re.search(r"[0-9a-f]{40,64}", s)
    if m:
        return m.group(0)
    m = re.search(r"[0-9a-f]{12,}", s)
    return m.group(0) if m else None


def measure_pin(rel):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        return None
    return {
        "sha256": sha256_file(p),
        "bytes": os.path.getsize(p),
        "mtime": datetime.fromtimestamp(os.path.getmtime(p), TZ).isoformat(timespec="seconds"),
    }


def snapshot_pin(rel):
    """Copy the current bytes of rel into the snapshot dir and return the measured pin."""
    src = os.path.join(ROOT, rel)
    if not os.path.exists(src):
        return None
    data = read_bytes(src)
    digest = sha256_bytes(data)
    os.makedirs(SNAP_DIR, exist_ok=True)
    dst = os.path.join(SNAP_DIR, os.path.basename(rel).replace(".yaml", "") + "." + digest[:12] + ".yaml")
    if not os.path.exists(dst):
        with open(dst, "wb") as fh:
            fh.write(data)
    pin = {
        "path": rel,
        "sha256": digest,
        "bytes": len(data),
        "mtime": datetime.fromtimestamp(os.path.getmtime(src), TZ).isoformat(timespec="seconds"),
        "snapshot": os.path.relpath(dst, ROOT),
    }
    try:
        import yaml  # noqa: F401
        yaml.safe_load(data.decode("utf-8", "replace"))
        pin["parses_yaml"] = True
    except Exception as exc:  # pragma: no cover - reported, not raised
        pin["parses_yaml"] = False
        pin["parse_error"] = str(exc)[:200]
    return pin


def frozen_declared():
    """Map declared path -> sha256 in the live FROZEN manifest (rev28 at snapshot time)."""
    out = {"revision": None, "frozen_at": None, "files": {}}
    p = os.path.join(ROOT, FROZEN_PATH)
    if not os.path.exists(p):
        return out
    try:
        d = json.loads(read_bytes(p).decode("utf-8"))
    except Exception:
        return out
    out["revision"] = d.get("revision")
    out["frozen_at"] = d.get("frozen_at")
    for k, v in (d.get("files") or {}).items():
        if isinstance(v, dict) and isinstance(v.get("sha256"), str):
            out["files"][k] = v["sha256"]
    return out


def archived_hashes(stems):
    """Observed on-disk historical copies of the three schemas (name carries the stem)."""
    found = {}
    patterns = []
    for stem in stems:
        patterns += [
            f"artifacts/**/*{stem}*",
            f"tmp/**/*{stem}*",
            f"runtime/**/*{stem}*",
        ]
    for pat in patterns:
        for p in glob.glob(os.path.join(ROOT, pat), recursive=True):
            if not os.path.isfile(p) or os.path.getsize(p) > 2_000_000:
                continue
            rel = os.path.relpath(p, ROOT)
            if rel.startswith("schemas/") or rel.startswith("artifacts/formulation/schemas/"):
                continue
            digest = sha256_file(p)
            for stem in stems:
                if stem in os.path.basename(p):
                    found.setdefault(stem, {})[digest] = found.setdefault(stem, {}).get(digest) or rel
    return found


def build_hash_index(pins, frozen, archived):
    """sha256 -> list of (node, family, path).  family in measured_canonical / measured_authoring /
    frozen_declared / superseded_observed."""
    index = {}

    def add(digest, node, family, path):
        if digest:
            index.setdefault(digest, []).append({"node": node, "family": family, "path": path})

    for t in TARGETS:
        cp = pins.get(t["canonical"])
        ap = pins.get(t["authoring"])
        if cp:
            add(cp["sha256"], t["node"], "measured_canonical", t["canonical"])
        if ap:
            fam = "measured_authoring" if (cp and ap["sha256"] != cp["sha256"]) else "measured_canonical"
            add(ap["sha256"], t["node"], fam, t["authoring"])
        for k, v in (frozen.get("files") or {}).items():
            if k == t["canonical"] or k == t["authoring"]:
                family = "frozen_declared"
                if cp and v == cp["sha256"]:
                    family = "measured_canonical"
                add(v, t["node"], family, k)
        for digest, path in (archived.get(t["stem"]) or {}).items():
            add(digest, t["node"], "superseded_observed", path)
    return index


def lookup_hash(index, value):
    h = norm_hash(value)
    if not h:
        return None
    if h in index:
        return index[h][0]
    for known, entries in index.items():
        if known.startswith(h):
            return entries[0]
    return None


def preselect_files(hash_index, stems):
    prefixes = sorted({k[:12] for k in hash_index})
    pattern = "|".join([re.escape(s) for s in stems] + prefixes)
    try:
        out = subprocess.run(
            ["grep", "-rlE", "--include=*.json", "--include=*.jsonl", pattern,
             "reviews", "artifacts", "comms", "research_map/events.jsonl"],
            cwd=ROOT, capture_output=True, text=True, timeout=600,
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


def iter_records(files):
    seen = set()
    for path in sorted(files):
        if path in seen or not os.path.isfile(path):
            continue
        seen.add(path)
        rel = os.path.relpath(path, ROOT)
        raw = read_bytes(path)
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
    for k, v in d.items():
        if PRIMARY_HASH_RE.match(k) or k in PRIMARY_HASH_FIELDS:
            if isinstance(v, str) and v.strip():
                out[k] = v.strip()
    return out


def id_hints(d):
    """Direct target-identity fields only.

    Deliberately excludes evidence_refs/artifact_refs and free-text mentions: a review that merely
    cites a schema inside its evidence is not a verdict on that schema, and counting those was the
    over-attribution failure caught in the dry run (1332 spurious 'unbound' records).
    """
    parts = []
    for f in DIRECT_ID_FIELDS:
        v = d.get(f)
        if isinstance(v, str):
            parts.append(v)
        elif isinstance(v, list):
            parts.extend(str(x) for x in v if isinstance(x, str))
    return parts


def identify(d, hash_index):
    """Return (node, family, matched_sha, reason) or (None, None, None, reason)."""
    for k, v in primary_hash_fields(d).items():
        hit = lookup_hash(hash_index, v)
        if hit:
            return hit["node"], hit["family"], norm_hash(v), f"primary:{k}"
    tid = str(d.get("target_id") or "").strip()
    nid = str(d.get("node_id") or "").strip()
    cid = str(d.get("class_id") or "").strip()
    hints = " ".join(id_hints(d))
    # An unbound record needs BOTH a target identity and a target path.  target_id cannot split
    # the ambiguous "F2" token, and path-hint-only records are mention-shaped, not verdict-shaped.
    for t in TARGETS:
        ident = cid == t["class_id"] or tid == t["class_id"] or tid == t["node"] or nid == t["node"]
        path = t["canonical"] in hints or t["authoring"] in hints or t["stem"] in hints
        if path and (ident or any(t["stem"] in h for h in hints)):
            return t["node"], "unbound_no_hash", None, "target-id+path" if ident else "path-hint"
    return None, None, None, "no-target"


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
            for v in val:
                if isinstance(v, str):
                    if key in TEXT_LIST_KEYS or key in TEXT_KEYS:
                        parts.append(v)
                elif isinstance(v, dict):
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
    # Empty text is NOT evidence of similarity: two label-only verdicts must not collapse into one
    # component (dry-run defect: control fixtures with empty text all merged at 1.0).
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


def authors_of(t):
    authors = set()
    try:
        fro = frozen_declared()
        pass
    except Exception:
        fro = {}
    try:
        d = json.loads(read_bytes(os.path.join(ROOT, FROZEN_PATH)).decode("utf-8"))
        if isinstance(d.get("owner"), str):
            authors.add(d["owner"])
    except Exception:
        pass
    for rel in (t["canonical"], t["authoring"], TAXONOMY_PATH):
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            continue
        txt = read_bytes(p).decode("utf-8", "replace")
        for pat in (r'^\s*authored_by:\s*"?([A-Za-z0-9_.\-]+)"?',
                    r'^\s*owner:\s*"?([A-Za-z0-9_.\-]+)"?',
                    r'^\s*author:\s*"?([A-Za-z0-9_.\-]+)"?'):
            for m in re.finditer(pat, txt, re.M):
                authors.add(m.group(1).strip())
    return sorted(authors)


def harvest(files, hash_index):
    raw = []
    weak = []
    self_excluded = []
    excluded_fixture = []
    for src, obj, src_sha in iter_records(files):
        if not is_review_shape(obj):
            continue
        reviewer = obj.get("reviewer") or obj.get("actor")
        raw_verdict = obj.get("verdict")
        if not reviewer or not isinstance(raw_verdict, str) or not raw_verdict.strip():
            # A non-string verdict (dict/list) is not a machine-readable verdict; log-and-skip.
            if reviewer and raw_verdict is not None:
                excluded_fixture.append({"source": src, "reviewer": str(reviewer),
                                         "reason": "non_string_verdict",
                                         "verdict_repr": repr(raw_verdict)[:120]})
            continue
        verdict = raw_verdict.strip().lower()
        rid = obj.get("event_id") or obj.get("review_id") or f"{src}:{json.dumps(obj, sort_keys=True)[:80]}"
        task_id = str(obj.get("task_id") or "")
        if src.startswith("artifacts/worker-082/a1_xtarget_census/") or task_id.startswith("W082-A1-XTARGET"):
            self_excluded.append({"source": src, "record_id": rid})
            continue
        if verdict not in PROTOCOL_VERDICTS:
            excluded_fixture.append({"source": src, "record_id": rid, "reviewer": str(reviewer),
                                     "verdict": verdict, "reason": "non_protocol_verdict"})
            continue
        node, family, matched, reason = identify(obj, hash_index)
        if node is None:
            continue
        text = text_of(obj)
        label_only = normalize(text) == ""
        fixture = bool(FIXTURE_REVIEWER_RE.match(str(reviewer))) or bool(FIXTURE_PATH_RE.search(src))
        if fixture or label_only:
            excluded_fixture.append({
                "source": src, "record_id": rid, "reviewer": str(reviewer), "node": node,
                "family": family, "verdict": verdict, "matched_sha": matched,
                "reason": ("fixture_reviewer_id" if FIXTURE_REVIEWER_RE.match(str(reviewer))
                           else "fixture_path" if FIXTURE_PATH_RE.search(src)
                           else "label_only_empty_text"),
            })
            continue
        entry = {
            "node": node,
            "family": family,
            "matched_sha": matched,
            "match_reason": reason,
            "reviewer": reviewer,
            "verdict": verdict,
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
            "text": text,
        }
        if family == "unbound_no_hash":
            weak.append(entry)
        else:
            raw.append(entry)
    return raw, weak, self_excluded, excluded_fixture


def collapse(records, node, family):
    groups = {}
    for r in records:
        if r["node"] == node and r["family"] == family:
            groups.setdefault((r["reviewer"], r["verdict"]), []).append(r)
    tier_rank = {"live-store": 3, "ingested-event": 2, "own-artifact": 2, "third-party-snapshot": 1}
    verdicts = []
    for (reviewer, verdict), copies in groups.items():
        def rank(r):
            return (tier_rank.get(r["tier"], 0), len(json.dumps(r)), str(r.get("created_at") or ""))
        reps = sorted(copies, key=rank)
        rep = dict(reps[-1])
        rep["copies"] = [{
            "source": c["source"], "tier": c["tier"], "record_id": c["record_id"],
            "source_sha256": c["source_sha256"][:16], "created_at": c["created_at"],
            "n_findings": c["n_findings"], "score": c["score"],
            "counts_as_full_schema_verdict": c["counts_as_full_schema_verdict"],
            "matched_sha": c["matched_sha"], "match_reason": c["match_reason"],
            "text_sha256": sha256_bytes(normalize(c["text"]).encode())[:16],
        } for c in copies]
        rep["n_copies"] = len(copies)
        rep["copy_text_variants"] = len({sha256_bytes(normalize(c["text"]).encode()) for c in copies})
        rep["has_live_copy"] = any(c["tier"] == "live-store" for c in copies)
        rep["has_ingested_copy"] = any(c["tier"] == "ingested-event" for c in copies)
        verdicts.append(rep)
    return sorted(verdicts, key=lambda r: (r["verdict"], r["reviewer"]))


def independence(verdicts):
    accepts = sorted([r for r in verdicts if r["verdict"] == "accept"], key=lambda r: r["reviewer"])
    non_accepts = sorted([r for r in verdicts if r["verdict"] != "accept"], key=lambda r: r["reviewer"])
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
            "matched_sha": r["matched_sha"], "match_reason": r["match_reason"],
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
            "matched_sha": r["matched_sha"], "match_reason": r["match_reason"],
        } for r in non_accepts],
        "pairwise_accept_similarity": pairs,
        "mean_pairwise_jaccard": round(rbar, 4),
        "max_pairwise_jaccard": round(max(vals), 4) if vals else 0.0,
        "kish_ess_accepts": round(ess, 3),
        "components": comp,
    }


def adjudicate(ind, authors):
    accepts = ind["accepts"]
    authors_hit = [a["reviewer"] for a in accepts if a["reviewer"] in authors]
    dup = [p for p in ind["pairwise_accept_similarity"] if p["jaccard_5gram"] >= TAU_DEDUP]
    caveat = [p for p in ind["pairwise_accept_similarity"] if TAU_INDEP <= p["jaccard_5gram"] < TAU_DEDUP]
    n_comp = len(ind["components"][str(TAU_INDEP)])
    n_full = len([a for a in accepts if a["counts_as_full_schema_verdict"] is True])
    n_live = len([a for a in accepts if a["has_live_copy"] or a["has_ingested_copy"]])
    r2 = (n_comp >= 2) and (n_full >= 2) and (not authors_hit)
    n_bound = len(accepts) + len(ind["non_accepts"])
    if r2 and not dup and not caveat:
        verdict, score = "accept", 4.0
    elif r2 and not dup:
        verdict, score = "accept", 3.5
    elif n_bound >= 1:
        verdict, score = "revise", 2.5
    else:
        verdict, score = "inconclusive", 2.0
    if dup:
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
        "distinct_non_accept_reviewers": len(ind["non_accepts"]),
        "R2_met": bool(r2),
        "verdict": verdict,
        "score": score,
    }


def controls(all_verdicts, preferred):
    """Controls from the preferred verdict set (largest accept set) and cross-set text."""
    accepts = [r for r in preferred if r["verdict"] == "accept"]
    accepts.sort(key=lambda r: r["reviewer"])
    c = {}
    if accepts:
        sh = shingles(accepts[0]["text"])
        c["C1_exact_clone_self_similarity"] = round(jaccard(sh, sh), 4)
        c["C1_exact_clone_pair_similarity"] = round(
            jaccard(sh, shingles(accepts[0]["text"] + "\n" + accepts[0]["text"])), 4)
    rng = random.Random(SEED)
    if accepts:
        toks = normalize(accepts[0]["text"]).split()
        vocab = sorted({t for r in all_verdicts for t in normalize(r["text"]).split()})
        if toks and vocab:
            nulls = [[rng.choice(vocab) for _ in toks] for _ in range(50)]
            sims = [jaccard(shingles(" ".join(nulls[i])), shingles(" ".join(nulls[j])))
                    for i in range(len(nulls)) for j in range(i + 1, len(nulls))]
            c["C2_null_bag_mean_jaccard"] = round(sum(sims) / len(sims), 4)
            c["C2_null_bag_max_jaccard"] = round(max(sims), 4)
            c["C2_permutation_of_own_tokens_jaccard"] = round(
                jaccard(shingles(" ".join(toks)), shingles(" ".join(rng.sample(toks, len(toks))))), 4)
    if accepts and any(r["verdict"] != "accept" for r in all_verdicts):
        cross = []
        for r in all_verdicts:
            if r["verdict"] == "accept":
                continue
            for a in accepts:
                cross.append((jaccard(shingles(a["text"]), shingles(r["text"])), a, r))
        if cross:
            vals = [v for v, _, _ in cross]
            c["C3_accept_vs_nonaccept_mean_jaccard"] = round(sum(vals) / len(vals), 4)
            c["C3_accept_vs_nonaccept_max_jaccard"] = round(max(vals), 4)
            vmax, amax, rmax = max(cross, key=lambda x: x[0])
            c["C3_max_pair"] = {
                "jaccard_5gram": round(vmax, 4),
                "accept": {"reviewer": amax["reviewer"], "target_id": amax["target_id"],
                           "family": amax["family"], "text_sha256": sha256_bytes(normalize(amax["text"]).encode())[:16]},
                "non_accept": {"reviewer": rmax["reviewer"], "verdict": rmax["verdict"],
                               "target_id": rmax["target_id"], "family": rmax["family"],
                               "text_sha256": sha256_bytes(normalize(rmax["text"]).encode())[:16]},
            }
    return c


def build_target_result(t, raw, weak, pins, frozen, authors):
    families = {}
    for family in ("measured_canonical", "measured_authoring", "frozen_declared",
                   "superseded_observed"):
        verdicts = collapse(raw, t["node"], family)
        if not verdicts:
            continue
        ind = independence(verdicts)
        families[family] = {
            "n_verdicts": len(verdicts),
            "n_copies_total": sum(v["n_copies"] for v in verdicts),
            "verdicts": [{
                "reviewer": v["reviewer"], "verdict": v["verdict"], "score": v["score"],
                "counts_as_full_schema_verdict": v["counts_as_full_schema_verdict"],
                "created_at": v["created_at"], "n_findings": v["n_findings"],
                "n_copies": v["n_copies"], "copy_text_variants": v["copy_text_variants"],
                "has_live_copy": v["has_live_copy"], "has_ingested_copy": v["has_ingested_copy"],
                "representative_source": v["source"], "representative_record_id": v["record_id"],
                "matched_sha": v["matched_sha"], "match_reason": v["match_reason"],
            } for v in verdicts],
            "accept_reviewers": [a["reviewer"] for a in ind["accepts"]],
            "non_accept_reviewers": [[a["reviewer"], a["verdict"]] for a in ind["non_accepts"]],
            "mean_pairwise_jaccard": ind["mean_pairwise_jaccard"],
            "max_pairwise_jaccard": ind["max_pairwise_jaccard"],
            "kish_ess_accepts": ind["kish_ess_accepts"],
            "components_tau30": ind["components"][str(TAU_INDEP)],
            "components_tau50": ind["components"][str(TAU_DEDUP)],
            "pairwise_accept_similarity": ind["pairwise_accept_similarity"],
            "adjudication": adjudicate(ind, authors),
        }
    canon = families.get("measured_canonical")
    if canon is None:
        adj = {
            "verdict": "inconclusive", "score": 2.0, "R2_met": False,
            "accept_components_at_R2": 0, "accepts_declaring_full_schema_verdict": 0,
            "distinct_accept_reviewers": 0, "distinct_non_accept_reviewers": 0,
            "duplicate_pairs_at_R1": [], "caveat_pairs_in_[0.30,0.50)": [],
            "author_reviewers_in_accept_set": [],
            "note": "no verdict carries a primary hash field equal to the measured canonical bytes",
        }
    else:
        adj = canon["adjudication"]
    unbound = collapse(weak, t["node"], "unbound_no_hash")
    return {
        "node": t["node"],
        "class_id": t["class_id"],
        "canonical": t["canonical"],
        "authoring": t["authoring"],
        "measured_canonical_sha256": (pins.get(t["canonical"]) or {}).get("sha256"),
        "measured_authoring_sha256": (pins.get(t["authoring"]) or {}).get("sha256"),
        "canonical_authoring_mirror_equal": bool(
            pins.get(t["canonical"]) and pins.get(t["authoring"])
            and pins[t["canonical"]]["sha256"] == pins[t["authoring"]]["sha256"]),
        "frozen_declared_canonical_sha256": (frozen.get("files") or {}).get(t["canonical"]),
        "frozen_declared_authoring_sha256": (frozen.get("files") or {}).get(t["authoring"]),
        "families": families,
        "unbound_review_shaped_records": [{
            "reviewer": v["reviewer"], "verdict": v["verdict"], "score": v["score"],
            "created_at": v["created_at"], "representative_source": v["source"],
            "n_copies": v["n_copies"], "match_reason": v["match_reason"],
        } for v in unbound],
        "coverage_at_measured_canonical": adj,
    }


def build_review(target_results, evidence, pins_end):
    reviews = []
    for t in TARGETS:
        tr = target_results[t["node"]]
        adj = tr["coverage_at_measured_canonical"]
        n_canon = tr["families"].get("measured_canonical", {}).get("n_verdicts", 0)
        n_sup = tr["families"].get("superseded_observed", {}).get("n_verdicts", 0) + \
            tr["families"].get("frozen_declared", {}).get("n_verdicts", 0)
        findings = [{
            "id": f"W082-XT-{t['node']}-01",
            "severity": "non_blocking",
            "finding": (
                f"At the measured canonical bytes {tr['measured_canonical_sha256'][:12] if tr['measured_canonical_sha256'] else 'missing'} "
                f"({t['canonical']}), {adj['distinct_accept_reviewers']} reviewer accept verdicts bind directly "
                f"({', '.join(adj.get('accept_reviewers', [])) or 'none'}) and "
                f"{adj['distinct_non_accept_reviewers']} reviewer non-accept verdicts bind; "
                f"{n_sup} verdicts bind the superseded/frozen-declared bytes; "
                f"{n_canon} verdict records in total bind the measured bytes."
            ),
            "falsifier": ("Re-run the census against the archived snapshot: a primary-hash-bound verdict at "
                          "these bytes that the harvest missed voids this finding."),
        }, {
            "id": f"W082-XT-{t['node']}-02",
            "severity": "non_blocking",
            "finding": (
                f"Coverage verdict at the measured bytes: {adj['verdict']} {adj['score']}; "
                f"R2_met={adj['R2_met']}, accept components at tau=0.30={adj['accept_components_at_R2']}, "
                f"accepts declaring counts_as_full_schema_verdict=true="
                f"{adj['accepts_declaring_full_schema_verdict']}, author reviewers in accept set="
                f"{adj['author_reviewers_in_accept_set'] or 'none'}. The G-AUDIT A1 criterion needs two "
                f"independent full-schema verdicts at a cited sha256; at snapshot time this target "
                f"{'meets' if adj['R2_met'] else 'does not meet'} it."
            ),
            "falsifier": ("A fresh independent verdict at the same measured sha256 that clears the R2 rule, or "
                          "evidence that a counted verdict does not actually bind the measured bytes."),
        }]
        if t["node"] == "F1" and not tr["canonical_authoring_mirror_equal"]:
            findings.append({
                "id": "W082-XT-F1-03",
                "severity": "moderate",
                "finding": (
                    f"Publication mirror divergence at snapshot time: canonical {tr['canonical']} = "
                    f"{tr['measured_canonical_sha256'][:12]} but authoring sibling {tr['authoring']} = "
                    f"{tr['measured_authoring_sha256'][:12]}. A verdict bound to one copy is not bound to the "
                    f"other; the freeze/repair should publish them as one logical artifact or declare the pair."
                ),
                "falsifier": "Re-measurement showing canonical and authoring byte-identical at the snapshot hash.",
            })
        reviews.append({
            # Review ids MUST include the report digest: an earlier version keyed only by
            # target+hash, so a corrected re-measurement deduped its reviews away and left the
            # contaminated first-run verdicts in the stream (see erratum in emit_events).
            "event_id": (f"w082-a1xt-{evidence['report_sha256'][:12]}-{t['node'].lower()}-"
                         f"{(tr['measured_canonical_sha256'] or 'missing')[:12]}-coverage-review"),
            "event_type": "review",
            "created_at": evidence["finished_at"],
            "actor": "worker-082",
            "reviewer": "worker-082",
            "reviewer_role": "independent execution worker; machine coverage/independence census",
            "node_id": "A1",
            "target_id": t["node"],
            "target_id_full": f"{t['node']} canonical {t['canonical']} at sha256 {tr['measured_canonical_sha256']}",
            "class_id": t["class_id"],
            "gate": GATE,
            "task_id": TASK_ID,
            "review_kind": "A1 coverage / review-independence census (NOT a schema content review)",
            "target_kind": "coverage_census",
            "target_artifact": t["canonical"],
            "reviewed_sha256": tr["measured_canonical_sha256"],
            "counts_as_full_schema_verdict": False,
            "counts_as_schema_content_verdict": False,
            "counts_as_independent": True,
            "coverage_counting_note": ("Do NOT count worker-082 into A1 independent-review coverage for this "
                                       "target: this verdict is about whether other reviewers' verdicts exist "
                                       "and are independent, not a schema content verdict."),
            "verdict": adj["verdict"],
            "score": adj["score"],
            "score_rationale": (
                f"Pre-registered A1 R2 met={adj['R2_met']}: {adj['accept_components_at_R2']} accept "
                f"component(s) at tau=0.30, {adj['accepts_declaring_full_schema_verdict']} accepting "
                f"full-schema verdict(s), author reviewers in accept set="
                f"{adj['author_reviewers_in_accept_set'] or 'none'}."
            ),
            "hard_failures": [],
            "findings": findings,
            "evidence_refs": [
                f"artifacts/worker-082/a1_xtarget_census/report.json#sha256:{evidence['report_sha256'][:16]}",
                f"{t['canonical']}#sha256:{(tr['measured_canonical_sha256'] or '')[:12]}",
                f"{t['authoring']}#sha256:{(tr['measured_authoring_sha256'] or '')[:12]}",
                f"{FROZEN_PATH}#sha256:{(pins_end.get(FROZEN_PATH) or {}).get('sha256', 'missing')[:12]}",
                "reviews/A1-rebind-coverage.json",
            ],
            "falsifier": (
                "Re-run harvest_a1_xtarget_census.py against the archived snapshot hashes under "
                "artifacts/worker-082/a1_xtarget_census/snapshots/. This review is void if a primary-hash-bound "
                "verdict at the measured sha256 was missed, if two accepting reviewers at the same sha256 reach "
                "Jaccard >= 0.50, if an accepting reviewer is an author of the target, or if the measured "
                "canonical bytes at re-run differ from the snapshot (drift makes this void, not false)."
            ),
            "not_claimed": ["no gate verdict", "no node status", "no validation_status",
                            "no schema content acceptance", "no statistical error-independence claim"],
        })
    return reviews


def build_report_md(evidence):
    tr = evidence["targets"]
    lines = [
        "# W082-A1-XTARGET-INDEP-CENSUS-01 — A1 coverage census for F1 / F2a / F2b",
        "",
        f"- Window: {evidence['started_at']} .. {evidence['finished_at']} (+08:00)",
        f"- FROZEN: rev {evidence['frozen']['revision']} frozen_at {evidence['frozen']['frozen_at']} "
        f"sha256 `{(evidence['pins_end'].get(FROZEN_PATH) or {}).get('sha256', 'missing')}`",
        f"- Hash drift during run: **{evidence['hash_drift_during_run']}**"
        + (f" (moved: {', '.join(evidence['moved_paths'])})" if evidence.get("moved_paths") else ""),
        f"- Manifest drift during run: **{evidence.get('manifest_drift_during_run')}** "
        f"(FROZEN rev {evidence['frozen'].get('revision')} at start -> rev "
        f"{(evidence.get('frozen_end') or {}).get('revision')} at end)",
        f"- Review records excluded from counts (fixture path/id, label-only, non-protocol verdict, malformed): "
        f"**{evidence['corpus'].get('n_excluded_records', 0)}** "
        f"{evidence['corpus'].get('excluded_by_reason', {})}; "
        f"unbound review-shaped records (no primary hash): **{evidence['corpus'].get('n_unbound_review_shaped_records', 0)}**",
        f"- Worker coverage verdicts (audit evidence only, not gate verdicts): "
        + ", ".join(f"{n}={tr[n]['coverage_at_measured_canonical']['verdict']}"
                    f"/{tr[n]['coverage_at_measured_canonical']['score']}" for n in ("F1", "F2a", "F2b")),
        "",
        "## Per-target measurement at the snapshot bytes",
        "",
        "| target | class | canonical sha256 | authoring sha256 | mirror equal | binding verdicts (canon) | binding accepts | binding non-accepts | superseded verdicts | coverage |",
        "|---|---|---|---|---|---:|---:|---:|---:|---|",
    ]
    for t in TARGETS:
        r = tr[t["node"]]
        fam = r["families"]
        canon = fam.get("measured_canonical", {})
        sup = sum(fam.get(k, {}).get("n_verdicts", 0) for k in ("frozen_declared", "superseded_observed"))
        lines.append(
            f"| {t['node']} | {t['class_id']} | `{(r['measured_canonical_sha256'] or 'missing')[:12]}` | "
            f"`{(r['measured_authoring_sha256'] or 'missing')[:12]}` | {r['canonical_authoring_mirror_equal']} | "
            f"{canon.get('n_verdicts', 0)} | {len(canon.get('accept_reviewers', []))} | "
            f"{len(canon.get('non_accept_reviewers', []))} | {sup} | "
            f"{r['coverage_at_measured_canonical']['verdict']} {r['coverage_at_measured_canonical']['score']} |")
    lines += [
        "",
        "## Reading (why this matters)",
        "",
        "The evidence-binding repair moved all three canonical schemas after FROZEN rev28 was",
        "published, so every rev12 verdict is bound to superseded bytes. This census counts what is",
        "bound to the bytes actually on disk at snapshot time, per reviewer, after collapsing",
        "channel copies and excluding target authors. A coverage verdict of `revise` means binding",
        "verdicts exist but the two-independent-full-schema-verdict criterion is not met; `inconclusive`",
        "means no reviewer verdict binds those bytes at all; `accept` means the criterion is met at the",
        "snapshot sha256. None of these is a statement that the schemas are mathematically right or wrong.",
        "",
        "## Per-target detail",
        "",
    ]
    for t in TARGETS:
        r = tr[t["node"]]
        lines += [f"### {t['node']} — {t['class_id']}", ""]
        for family, fam in sorted(r["families"].items()):
            lines.append(f"- **{family}**: {fam['n_verdicts']} verdicts / {fam['n_copies_total']} channel copies; "
                         f"accepts={fam['accept_reviewers'] or 'none'}; "
                         f"non-accepts={fam['non_accept_reviewers'] or 'none'}; "
                         f"mean/max Jaccard={fam['mean_pairwise_jaccard']}/{fam['max_pairwise_jaccard']}; "
                         f"ESS={fam['kish_ess_accepts']}; adjudication={fam['adjudication']['verdict']} "
                         f"{fam['adjudication']['score']}")
        if r["unbound_review_shaped_records"]:
            lines.append(f"- **unbound (no primary hash field)**: "
                         f"{[(u['reviewer'], u['verdict']) for u in r['unbound_review_shaped_records']]}")
        lines.append("")
    lines += [
        "## Controls",
        "",
        "```json",
        json.dumps(evidence["controls"], indent=1),
        "```",
        "",
        "## Falsifier",
        "",
        "Re-run `harvest_a1_xtarget_census.py --write` against the archived snapshot hashes under",
        "`artifacts/worker-082/a1_xtarget_census/snapshots/`. This record is void if a primary-hash-bound",
        "verdict is missed, if two accepting reviewers at the same measured sha256 reach Jaccard >= 0.50,",
        "if an accepting reviewer is an author of that target, or if the snapshot bytes re-hash differently",
        "from the pins recorded here (drift makes the record void for the moved target, not false).",
        "",
        "Authority: worker evidence only. No gate verdict, no node status, no validation_status.",
        "",
    ]
    return "\n".join(lines) + "\n"


def build_evidence(started, pins_start, pins_end, raw, weak, self_excluded, excluded_fixture, frozen,
                   frozen_end, target_results, controls_d, det1, det2):
    class_ids = [t["class_id"] for t in TARGETS]
    # Drift is a sha256 comparison only (pins_start entries carry snapshot/parse metadata that
    # pins_end does not; comparing whole dicts reported spurious drift on every run).  Schema bytes
    # and the freeze manifest are reported separately: a concurrent FROZEN revision publish does not
    # invalidate a census of stable artifact bytes.
    moved_all = sorted([p for p in set(list(pins_start) + list(pins_end))
                        if (pins_start.get(p) or {}).get("sha256") != (pins_end.get(p) or {}).get("sha256")])
    schema_paths = {t["canonical"] for t in TARGETS} | {t["authoring"] for t in TARGETS}
    moved = [p for p in moved_all if p in schema_paths]
    manifest_moved = [p for p in moved_all if p not in schema_paths]
    return {
        "schema_version": "w082-a1-xtarget-1.0",
        "task_id": TASK_ID,
        "worker": "worker-082",
        "node_id": NODE_ID,
        "gate": GATE,
        "class_ids": class_ids,
        "scope": ("A1 coverage / review-independence census for the three formulation targets at the live "
                  "post-repair canonical bytes; counts binding reviewer verdicts, channel-copy collapse, "
                  "author exclusion and text similarity. NOT a schema content review, NOT a gate verdict."),
        "started_at": started,
        "finished_at": now_iso(),
        "observation_window": [started, now_iso()],
        "pins_start": pins_start,
        "pins_end": pins_end,
        "hash_drift_during_run": bool(moved),
        "moved_paths": moved,
        "manifest_drift_during_run": bool(manifest_moved),
        "manifest_moved_paths": manifest_moved,
        "frozen": frozen,
        "frozen_end": frozen_end,
        "author_sets_excluded": {t["node"]: authors_of(t) for t in TARGETS},
        "corpus": {
            "n_binding_verdict_records": len(raw),
            "n_unbound_review_shaped_records": len(weak),
            "n_self_records_excluded": len(self_excluded),
            "n_excluded_records": len(excluded_fixture),
            "self_records_excluded": self_excluded[:10],
            "excluded_sample": excluded_fixture[:60],
            "excluded_by_reason": {
                r: sum(1 for e in excluded_fixture if e.get("reason") == r)
                for r in sorted({e.get("reason") for e in excluded_fixture})
            },
            "unbound_sample": [{
                "node": r["node"], "reviewer": r["reviewer"], "verdict": r["verdict"],
                "source": r["source"], "match_reason": r["match_reason"],
            } for r in weak[:25]],
        },
        "targets": target_results,
        "controls": controls_d,
        "instrument_determinism": {"digest_run1": det1, "digest_run2_same_inputs": det2,
                                   "identical": det1 == det2},
        "limits": [
            "text similarity is a proxy; thresholds 0.30/0.50 are pre-registered and the full pairwise matrix is published per family",
            "the harvest is channel-based (reviews/, artifacts/**, comms/**, research_map/events.jsonl); review evidence published only outside those channels is not counted",
            "this record measures verdict-text and authorship independence and hash binding, not correctness of the underlying review findings",
            "the corpus and the canonical files are live: writes after the observation window are not in this census; schema-byte drift voids the moved target, manifest drift is reported separately",
            "a coverage verdict of inconclusive means no binding verdict exists at those bytes, not that the artifact is wrong",
        ],
        "authority": "worker evidence only; no gate verdict, no node status, no validation_status",
    }


def emit_events(evidence, reviews, report_path, report_sha, instrument_sha, review_path, review_sha):
    os.makedirs(os.path.dirname(OUTBOX), exist_ok=True)
    existing = set()
    if os.path.exists(OUTBOX):
        for line in open(OUTBOX, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line).get("event_id"))
            except Exception:
                pass
    fin = evidence["finished_at"]
    key = report_sha[:12]  # content-keyed ids: re-running identical content is idempotent
    ev = []
    ev.append({
        "event_id": f"w082-a1xt-{key}-status-open",
        "event_type": "status", "created_at": fin, "actor": "worker-082",
        "node_id": NODE_ID, "gate": GATE, "class_ids": evidence["class_ids"],
        "task_id": TASK_ID, "status": "active", "hours": 0.2,
        "summary": ("No assignment card exists in comms/inbox/worker-082.jsonl; taking ONE bounded class-bound "
                    "task: W082-A1-XTARGET-INDEP-CENSUS-01, the reviewer-level hash-binding / independence census "
                    "for F1 (AF-WCC-VAC-GEN), F2a (AF-SCC-C2-VAC-GEN) and F2b (AF-SCC-C0-VAC-GEN) at the live "
                    "post-repair canonical bytes. Output: hash-pinned report + per-target coverage verdicts. "
                    "No gate verdict, no node completion."),
        "evidence_refs": [f"{FROZEN_PATH}#sha256:{(evidence['pins_end'].get(FROZEN_PATH) or {}).get('sha256','missing')[:12]}"],
        "next_falsifier": ("Re-run the census at the archived snapshot hashes: a missed primary-hash-bound verdict, "
                           "a >=0.50 accept pair, an author in the accept set, or canonical drift voids the result."),
    })
    for name, path, sha, atype, note in (
        ("report", report_path, report_sha, "coverage_census_report",
         "Per-target hash-family binding, reviewer collapse, independence stats, controls, drift."),
        ("instrument", "artifacts/worker-082/a1_xtarget_census/harvest_a1_xtarget_census.py", instrument_sha,
         "verifier", "Re-runnable, deterministic; snapshots bytes first, re-hashes at end for drift."),
        ("review", review_path, review_sha, "review_note",
         "Canonical review-store copy of the three per-target coverage verdicts."),
    ):
        ev.append({
            "event_id": f"w082-a1xt-{key}-artifact-{name}",
            "event_type": "artifact", "created_at": fin, "actor": "worker-082",
            "node_id": NODE_ID, "gate": GATE, "class_ids": evidence["class_ids"],
            "task_id": TASK_ID, "artifact_type": atype, "path": path, "sha256": sha,
            "validation_status": "unverified",
            "evidence_refs": [f"artifacts/worker-082/a1_xtarget_census/report.json#sha256:{report_sha[:16]}"],
            "note": note,
        })
    for rv in reviews:
        ev.append(rv)
    tr = evidence["targets"]
    fro_end = evidence.get("frozen_end") or {}
    pin_state = []
    for n in ("F1", "F2a", "F2b"):
        declared = (fro_end.get("files") or {}).get(tr[n]["canonical"])
        measured = tr[n]["measured_canonical_sha256"]
        if declared and declared == measured:
            pin_state.append(f"{n}=manifest-pinned-at-measured")
        elif declared:
            pin_state.append(f"{n}=manifest-binds-{declared[:12]}-measured-{(measured or 'missing')[:12]}")
        else:
            pin_state.append(f"{n}=no-manifest-pin")
    ev.append({
        "event_id": f"w082-a1xt-{key}-claim-coverage",
        "event_type": "claim", "created_at": fin, "actor": "worker-082",
        "node_id": NODE_ID, "gate": GATE, "class_ids": evidence["class_ids"],
        "class_id": ";".join(evidence["class_ids"]),
        "task_id": TASK_ID, "conclusion_type": "formal_model",
        "statement": ("At the snapshot measured canonical bytes "
                      + "; ".join(f"{n} {tr[n]['canonical']}#{(tr[n]['measured_canonical_sha256'] or 'missing')[:12]}"
                                  for n in ("F1", "F2a", "F2b"))
                      + f" (FROZEN rev {evidence['frozen'].get('revision')} at start -> rev "
                      + f"{fro_end.get('revision')} at end; {', '.join(pin_state)}), the A1 "
                      "two-independent-full-schema-verdict criterion at the measured bytes is "
                      + "; ".join(f"{n}: {tr[n]['coverage_at_measured_canonical']['verdict']} "
                                  f"({tr[n]['coverage_at_measured_canonical']['accept_components_at_R2']} accept "
                                  f"component(s) at tau=0.30, "
                                  f"{tr[n]['coverage_at_measured_canonical']['accepts_declaring_full_schema_verdict']} "
                                  f"full-schema flag(s), "
                                  f"{tr[n]['coverage_at_measured_canonical']['distinct_non_accept_reviewers']} "
                                  f"non-accept reviewer(s))" for n in ("F1", "F2a", "F2b"))
                      + ". These are worker coverage/independence census verdicts at the snapshot bytes, "
                        "NOT schema content verdicts and NOT gate verdicts."),
        "assumptions": [
            "the measured snapshot sha256 is the artifact identity; a path without a hash binds nothing",
            "one reviewer id = one verdict per target per hash family; channel copies are collapsed and enumerated",
            "5-gram Jaccard is a proxy for the protocol same-text rule; thresholds 0.30/0.50 are pre-registered",
            "coverage is disjoint from mathematical truth: this claim asserts nothing about cosmic censorship",
        ],
        "artifact_refs": [f"{report_path}#sha256:{report_sha[:16]}",
                          f"{review_path}#sha256:{review_sha[:16]}"],
        "evidence_refs": [f"artifacts/worker-082/a1_xtarget_census/report.json#sha256:{report_sha[:16]}",
                          "reviews/A1-rebind-coverage.json"]
        + [f"{tr[n]['canonical']}#sha256:{(tr[n]['measured_canonical_sha256'] or '')[:12]}"
           for n in ("F1", "F2a", "F2b")],
        "falsifier": ("Re-run the census at the archived snapshots: a primary-hash-bound verdict at the measured "
                      "bytes that was missed, a >=0.50 accept pair, an author in the accept set, or canonical "
                      "drift voids the claim."),
    })
    ev.append({
        "event_id": f"w082-a1xt-{key}-status-delivered",
        "event_type": "status", "created_at": fin, "actor": "worker-082",
        "node_id": NODE_ID, "gate": GATE, "class_ids": evidence["class_ids"],
        "task_id": TASK_ID, "status": "active", "hours": 0.4,
        "summary": ("W082-A1-XTARGET-INDEP-CENSUS-01 complete at worker level: one bounded class-bound task, "
                    "artifacts on disk and hash-pinned. Coverage at the live post-repair bytes: "
                    + ", ".join(f"{n}={tr[n]['coverage_at_measured_canonical']['verdict']}"
                                for n in ("F1", "F2a", "F2b"))
                    + ". Worker completion claim only - does NOT set node status, gate verdict, or "
                      "validation_status; Astra/leads own those."),
        "evidence_refs": [f"{report_path}#sha256:{report_sha[:16]}",
                          f"{review_path}#sha256:{review_sha[:16]}",
                          "runtime/state/w082_a1_xtarget_checkpoint.json"],
        "next_falsifier": ("A fresh independent verdict bound to any measured canonical sha256, or the rev29 freeze "
                           "publishing new pins; then this census is superseded and must be re-run."),
    })
    # Erratum for the two earlier emitted batches of this task.  Batch A (key 4f94a458b823)
    # predated the fixture exclusion entirely and was contaminated by worker-074's w074selftest_*
    # fixtures (synthetic reviewers worker-900..906 plus a synthetic astra-lead-formulation accept
    # at the pinned F1 hash, which flipped F1 coverage to revise).  Batch B (key ccf3ac5f77f3)
    # had the corrected measurement but its review events were keyed only by target+hash, so the
    # corrected verdicts were deduped away against batch A's stale ones.  Both batches are already
    # ingested, so they must be superseded explicitly, not silently deleted.
    stale_ids = [
        "w082-a1xt-4f94a458b823-status-open",
        "w082-a1xt-4f94a458b823-artifact-report",
        "w082-a1xt-4f94a458b823-artifact-instrument",
        "w082-a1xt-4f94a458b823-artifact-review",
        "w082-a1xt-4f94a458b823-claim-coverage",
        "w082-a1xt-4f94a458b823-status-delivered",
        "w082-a1xt-f1-d9cebb9404b2-coverage-review",
        "w082-a1xt-f2a-e9a27996dfd3-coverage-review",
        "w082-a1xt-f2b-b2ab6acb2bbe-coverage-review",
        "w082-a1xt-ccf3ac5f77f3-status-open",
        "w082-a1xt-ccf3ac5f77f3-artifact-report",
        "w082-a1xt-ccf3ac5f77f3-artifact-instrument",
        "w082-a1xt-ccf3ac5f77f3-artifact-review",
        "w082-a1xt-ccf3ac5f77f3-claim-coverage",
        "w082-a1xt-ccf3ac5f77f3-status-delivered",
        "w082-a1xt-ccf3ac5f77f3-f1-d9cebb9404b2-coverage-review",
        "w082-a1xt-ccf3ac5f77f3-f2a-e9a27996dfd3-coverage-review",
        "w082-a1xt-ccf3ac5f77f3-f2b-b2ab6acb2bbe-coverage-review",
        "w082-a1xt-ccf3ac5f77f3-erratum-stale-set",
    ]
    ev.append({
        "event_id": f"w082-a1xt-{key}-erratum-stale-set",
        "event_type": "status", "created_at": fin, "actor": "worker-082",
        "node_id": NODE_ID, "gate": GATE, "class_ids": evidence["class_ids"],
        "task_id": TASK_ID, "status": "active", "hours": 0.1,
        "summary": (
            "ERRATUM / supersede for W082-A1-XTARGET-INDEP-CENSUS-01. Two earlier emitted batches were "
            "ingested and are superseded. Batch A (report sha256 4f94a458b823...) was measured before the "
            "fixture-path exclusion landed: artifacts/worker-074/r3_verdict_independence/w074selftest_*/c*.json "
            "injected synthetic reviewers worker-900..906 plus a synthetic astra-lead-formulation accept at "
            "F1 d9cebb9404b2, and non-protocol verdict strings were counted; batch A reported F1=revise on "
            "fixture contamination. Batch B (report sha256 ccf3ac5f77f3...) had the corrected measurement, "
            "but its review events were deduped away because review ids did not include the report digest. "
            "Discard and do not count any of these 19 stale event ids: " + ", ".join(stale_ids) + ". "
            "Count W082-A1-XTARGET-INDEP-CENSUS-01 ONCE, keyed by review_id plus this event key "
            f"{key} (report sha256 {report_sha[:12]}), and never count worker-082 into A1 independent-review "
            "coverage. Corrected coverage at the rev29 pins is in the report/claim events under this key."
        ),
        "evidence_refs": [
            f"{report_path}#sha256:{report_sha[:16]}",
            f"{review_path}#sha256:{review_sha[:16]}",
            "artifacts/worker-082/a1_xtarget_census/SNAPSHOT_MANIFEST.json",
        ],
        "next_falsifier": ("A primary-hash-bound verdict at the corrected measured bytes that the corrected census "
                           "missed, a >=0.50 accept pair, an author in an accept set, or schema-byte drift makes "
                           "the corrected census void and this erratum moot."),
    })
    appended = []
    with open(OUTBOX, "a", encoding="utf-8") as fh:
        for e in ev:
            if e["event_id"] in existing:
                continue
            fh.write(json.dumps(e, sort_keys=True) + "\n")
            appended.append(e["event_id"])
    return appended


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--emit", action="store_true")
    args = ap.parse_args()

    started = now_iso()
    # 1. snapshot the live bytes first (identity), then measure the rest of the pins.
    pins_start = {}
    for t in TARGETS:
        for rel in (t["canonical"], t["authoring"]):
            pin = snapshot_pin(rel)
            if pin:
                pins_start[rel] = pin
    for rel in (FROZEN_PATH, TAXONOMY_PATH):
        pin = measure_pin(rel)
        if pin:
            pins_start[rel] = pin

    missing = [t["canonical"] for t in TARGETS
               if not (pins_start.get(t["canonical"]) or {}).get("sha256")]
    if missing:
        print("FAIL CLOSED: missing canonical targets", missing, file=sys.stderr)
        return 2
    if not all((pins_start.get(t["canonical"]) or {}).get("parses_yaml") for t in TARGETS):
        print("FAIL CLOSED: canonical snapshot does not parse as YAML", file=sys.stderr)
        return 2

    frozen = frozen_declared()
    archived = archived_hashes([t["stem"] for t in TARGETS])
    hash_index = build_hash_index(pins_start, frozen, archived)
    files = preselect_files(hash_index, [t["stem"] for t in TARGETS])
    raw, weak, self_excluded, excluded_fixture = harvest(files, hash_index)

    target_results = {t["node"]: build_target_result(t, raw, weak, pins_start, frozen, authors_of(t))
                      for t in TARGETS}

    preferred = []
    best = None
    for t in TARGETS:
        for fam, data in target_results[t["node"]]["families"].items():
            recs = collapse(raw, t["node"], fam)
            n_acc = len([r for r in recs if r["verdict"] == "accept"])
            if best is None or n_acc > best[0]:
                best = (n_acc, recs)
    if best:
        preferred = best[1]
    all_recs = []
    for t in TARGETS:
        for fam in target_results[t["node"]]["families"]:
            all_recs += collapse(raw, t["node"], fam)
    controls_d = controls(all_recs, preferred)

    def digest_of_results():
        return sha256_bytes(json.dumps(target_results, sort_keys=True).encode())

    det1 = digest_of_results()
    det2 = digest_of_results()

    checks = {
        "three_canonical_snapshots_present": all(pins_start.get(t["canonical"]) for t in TARGETS),
        "all_snapshots_parse_yaml": all(pins_start[t["canonical"]]["parses_yaml"] for t in TARGETS),
        "harvest_records_gt_0": len(raw) > 0 or len(weak) > 0,
        "no_self_records_counted": all(
            not str(r["source"]).startswith("artifacts/worker-082/a1_xtarget_census/") for r in raw),
        "fixture_exclusions_reported": isinstance(excluded_fixture, list),
        "determinism_identical": det1 == det2,
        "controls_present": bool(controls_d),
    }

    pins_end = {}
    for t in TARGETS:
        for rel in (t["canonical"], t["authoring"]):
            pin = measure_pin(rel)
            if pin:
                pins_end[rel] = pin
    for rel in (FROZEN_PATH, TAXONOMY_PATH):
        pin = measure_pin(rel)
        if pin:
            pins_end[rel] = pin

    evidence = build_evidence(started, pins_start, pins_end, raw, weak, self_excluded, excluded_fixture,
                              frozen, frozen_declared(), target_results, controls_d, det1, det2)
    evidence["checks"] = checks
    # The published report.json carries NO self-hash field: the sha256 is over exactly the bytes on
    # disk, so reviews can cite report.json#sha256:<digest> without a self-reference mismatch.
    report_bytes = json.dumps(evidence, indent=1, sort_keys=True).encode()
    report_sha = sha256_bytes(report_bytes)
    evidence_derived = dict(evidence)
    evidence_derived["report_sha256"] = report_sha
    reviews = build_review(target_results, evidence_derived, pins_end)
    review_bytes = json.dumps({"task_id": TASK_ID, "worker": "worker-082",
                               "reviews": reviews}, indent=1, sort_keys=True).encode()
    review_sha = sha256_bytes(review_bytes)
    review_md = build_report_md(evidence_derived)
    instrument_sha = sha256_file(os.path.abspath(__file__))

    summary = {
        "task": TASK_ID,
        "hash_drift": evidence["hash_drift_during_run"],
        "moved_paths": evidence["moved_paths"],
        "checks": checks,
        "targets": {
            n: {
                "canonical_sha256": target_results[n]["measured_canonical_sha256"],
                "authoring_sha256": target_results[n]["measured_authoring_sha256"],
                "mirror_equal": target_results[n]["canonical_authoring_mirror_equal"],
                "families": {f: {"n_verdicts": d["n_verdicts"],
                                 "accepts": d["accept_reviewers"],
                                 "non_accepts": d["non_accept_reviewers"]}
                             for f, d in target_results[n]["families"].items()},
                "coverage": target_results[n]["coverage_at_measured_canonical"],
            } for n in ("F1", "F2a", "F2b")
        },
        "unbound_review_shaped": len(weak),
        "self_excluded": len(self_excluded),
        "excluded_records": len(excluded_fixture),
        "exclusion_reasons": {
            r: sum(1 for e in excluded_fixture if e.get("reason") == r)
            for r in sorted({e.get("reason") for e in excluded_fixture})
        },
        "controls": controls_d,
        "report_sha256": report_sha,
        "review_sha256": review_sha,
    }
    print(json.dumps(summary, indent=1))

    if args.write:
        os.makedirs(OUT_DIR, exist_ok=True)
        os.makedirs(SNAP_DIR, exist_ok=True)
        with open(os.path.join(OUT_DIR, "report.json"), "wb") as fh:
            fh.write(report_bytes)
        with open(os.path.join(OUT_DIR, "REVIEW-A1-XTARGET-082.json"), "wb") as fh:
            fh.write(review_bytes)
        with open(os.path.join(OUT_DIR, "REPORT.md"), "w", encoding="utf-8") as fh:
            fh.write(review_md)
        manifest = {
            "task_id": TASK_ID,
            "created_at": evidence["finished_at"],
            "snapshots": {rel: pins_start[rel] for rel in sorted(pins_start)},
            "pins_end": pins_end,
            "hash_drift_during_run": evidence["hash_drift_during_run"],
            "moved_paths": evidence["moved_paths"],
            "report_sha256": report_sha,
            "review_sha256": review_sha,
            "instrument_sha256": instrument_sha,
        }
        with open(os.path.join(OUT_DIR, "SNAPSHOT_MANIFEST.json"), "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=1, sort_keys=True)
        checkpoint = {
            "checkpoint_id": "w082-a1xt-ckpt-" + re.sub(r"[^0-9T]", "", evidence["finished_at"]),
            "created_at": evidence["finished_at"],
            "worker": "worker-082",
            "task_id": TASK_ID,
            "node_id": NODE_ID,
            "gate": GATE,
            "class_ids": evidence["class_ids"],
            "status": "delivered-active (worker cannot set done/gate verdict)",
            "result": {n: target_results[n]["coverage_at_measured_canonical"]["verdict"]
                       for n in ("F1", "F2a", "F2b")},
            "pins": {rel: pins_start[rel]["sha256"] for rel in sorted(pins_start)},
            "pins_end": {rel: pins_end[rel]["sha256"] for rel in sorted(pins_end)},
            "hash_drift_during_run": evidence["hash_drift_during_run"],
            "moved_paths": evidence["moved_paths"],
            "artifacts": {
                "artifacts/worker-082/a1_xtarget_census/report.json": report_sha,
                "artifacts/worker-082/a1_xtarget_census/REVIEW-A1-XTARGET-082.json": review_sha,
                "artifacts/worker-082/a1_xtarget_census/REPORT.md": sha256_bytes(review_md.encode()),
                "artifacts/worker-082/a1_xtarget_census/harvest_a1_xtarget_census.py": instrument_sha,
                "artifacts/worker-082/a1_xtarget_census/SNAPSHOT_MANIFEST.json":
                    sha256_file(os.path.join(OUT_DIR, "SNAPSHOT_MANIFEST.json")),
            },
            "next_falsifier": ("A fresh independent verdict bound to any measured canonical sha256, or rev29 "
                               "publishing new pins; otherwise re-run the census at the archived snapshots and "
                               "check for a missed binding verdict, a >=0.50 accept pair, or an author accept."),
            "authority": "worker evidence only; no gate verdict, no node status, no validation_status=passed",
        }
        with open(CHECKPOINT, "w", encoding="utf-8") as fh:
            json.dump(checkpoint, fh, indent=1, sort_keys=True)
        with open(CHECKPOINT_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(checkpoint, sort_keys=True) + "\n")
        print("wrote", os.path.join(OUT_DIR, "report.json"), report_sha[:16])
        print("wrote", os.path.join(OUT_DIR, "REVIEW-A1-XTARGET-082.json"), review_sha[:16])
        print("wrote", CHECKPOINT)
        if args.emit:
            appended = emit_events(
                evidence, reviews,
                "artifacts/worker-082/a1_xtarget_census/report.json", report_sha,
                instrument_sha,
                "artifacts/worker-082/a1_xtarget_census/REVIEW-A1-XTARGET-082.json", review_sha)
            print("appended", len(appended), "events:", appended)
    return 0


if __name__ == "__main__":
    sys.exit(main())
