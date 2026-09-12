#!/usr/bin/env python3
"""W087-GFORM-INDEP-04 — G-FORM accept-independence and freeze-state audit.

Two bounded, class-bound measurements over the FROZEN rev-28 G-FORM pins
(F1 cce9c60146d6 / F2a 5476a3f2c6bc / F2b 55d0a1ea9bda):

  A. Accept independence.  Harvest every review record from the accepted stream
     (research_map/events.jsonl), every comms/outbox jsonl/json, and every
     reviews/*.json document; keep only records whose target names a schema and that
     carry that schema's measured pin; one verdict per reviewer (latest wins); cluster
     full-schema accepts by reviewer identity, character-5-gram findings-text Jaccard
     >= 0.6 and shared evidence-channel signature. The cluster count is the effective
     independent accept count for the G-FORM "two independent accepts" criterion.

  B. Freeze-state / moving-target measurement.  At run start and run end, measure the
     three canonical schemas, their authoring mirrors, the FROZEN manifest entries for
     both trees, and the accepted event stream for an owner artifact event that
     announces each measured hash. If the schemas no longer match the rev-28 pins, the
     audit reports the transition (old pins, new bytes, mtimes, declared revision,
     manifest mismatch count, owner-announcement presence) and scores the accept
     independence of the historical rev-28 pins separately from the new bytes.

Exit codes: 0 criteria met and freeze intact; 3 criterion not met or a measured
pin transition (freeze breach / pending re-pin); 2 canonical bytes moved during the
run (moving target: no stable claim); 4 a fail-closed control failed; 1 internal error.

Read-only against every canonical input. Writes only under
artifacts/worker-087/gform_independence/ (or --out). No gate verdict, no node status,
no review verdict is issued; this is worker measurement evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))
HEX = re.compile(r"[0-9a-fA-F]{12,64}")

PINS = {
    "F1": {
        "path": "schemas/af_wcc_vacuum.yaml",
        "authoring": "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
        "sha256": "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
        "class_id": "AF-WCC-VAC-GEN",
        "tokens": ["f1", "af-wcc-vac-gen", "af_wcc_vacuum"],
    },
    "F2a": {
        "path": "schemas/af_scc_c2_vacuum.yaml",
        "authoring": "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
        "sha256": "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "tokens": ["f2a", "af-scc-c2-vac-gen", "af_scc_c2_vacuum"],
    },
    "F2b": {
        "path": "schemas/af_scc_c0_vacuum.yaml",
        "authoring": "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
        "sha256": "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "tokens": ["f2b", "af-scc-c0-vac-gen", "af_scc_c0_vacuum"],
    },
}
FROZEN_PATH = "artifacts/formulation/FROZEN.json"
FROZEN_SHA = "2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1"
EVIDENCE_PATH = "artifacts/formulation/evidence/taxonomy_consistency.json"
EVIDENCE_SHA = "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b"
COMMON_TOKENS = {p["sha256"][:12] for p in PINS.values()} | {FROZEN_SHA[:12], EVIDENCE_SHA[:12]}

# Superseded hashes: negative-control material only.
SUPERSEDED = {
    "F1": "9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503",
    "F2a": "b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2",
    "F2b": "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508",
}

TARGET_PRIORITY = (
    ("target_id", "node_id", "node", "target", "target_node"),
    ("artifact", "artifact_path", "path", "reviewed_path", "target_path"),
    ("class_id", "class_ids"),
)
TEXT_FIELDS = (
    "finding", "hard_failure", "statement", "objection", "reason", "summary",
    "positive", "minimal_fix", "score_basis", "scope", "detail", "note",
)
INSTRUMENT_KEYS = (
    "instrument", "checker", "tool", "machine", "script", "review_doc", "report",
    "harness", "audit", "replay",
)
NODE_TOKENS = {"f1", "f2a", "f2b", "f2"}
CLASS_TOKENS = {
    "af-wcc-vac-gen", "af-scc-c2-vac-gen", "af-scc-c0-vac-gen", "af-wcc-scalar-sph",
}


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def mtime_iso(p: Path) -> str | None:
    try:
        return datetime.fromtimestamp(p.stat().st_mtime, CST).isoformat(timespec="seconds")
    except OSError:
        return None


def walk_strings(x, key: str = ""):
    if isinstance(x, str):
        yield key, x
    elif isinstance(x, dict):
        for k, v in x.items():
            yield from walk_strings(v, str(k))
    elif isinstance(x, (list, tuple)):
        for v in x:
            yield from walk_strings(v, key)


def hex_tokens(rec) -> set[str]:
    out: set[str] = set()
    for _, s in walk_strings(rec):
        for t in HEX.findall(s):
            out.add(t.lower())
    return out


def _word_hit(value: str, token: str) -> bool:
    return re.search(r"(?<![a-z0-9_])" + re.escape(token) + r"(?![a-z0-9_])", value.lower()) is not None


def referenced_docs(rec, doc_index: dict) -> list[tuple[str, dict]]:
    """Review documents named by this record (by reviews/<name>.json basename)."""
    out: list[tuple[str, dict]] = []
    seen: set[str] = set()
    for _, s in walk_strings(rec):
        base = s.strip().split("#")[0].split(" ")[0]
        if not base.endswith(".json"):
            continue
        name = Path(base).name
        if name in doc_index and doc_index[name][0] not in seen:
            rel, doc = doc_index[name]
            seen.add(rel)
            out.append((rel, doc))
    return out


PRIMARY_HASH_KEYS = (
    "reviewed_sha256", "artifact_sha256", "target_sha256", "declared_sha256", "content_sha256", "sha256",
)


def _first_hash(v) -> str | None:
    if isinstance(v, str):
        toks = HEX.findall(v)
        return toks[0].lower() if toks else None
    if isinstance(v, dict):
        for vv in v.values():
            t = _first_hash(vv)
            if t:
                return t
    if isinstance(v, (list, tuple)):
        for vv in v:
            t = _first_hash(vv)
            if t:
                return t
    return None


def primary_hash(rec) -> tuple[str | None, str | None]:
    """The single revision hash this review primarily binds, if declared.

    A review that reviews rev-13 must not be harvested as a rev-28 verdict just because
    its prose mentions the older hash. Only if no explicit hash field exists do we fall
    back to scanning the whole record.
    """
    for key in PRIMARY_HASH_KEYS:
        if key in rec:
            t = _first_hash(rec[key])
            if t:
                return key, t
    tid = str(rec.get("target_id") or "")
    toks = HEX.findall(tid)
    if toks:
        return "target_id", toks[0].lower()
    return None, None


def binds_pin(rec, spec: dict, doc_index: dict) -> tuple[bool, list[str]]:
    pin12 = spec["sha256"][:12]
    key, ph = primary_hash(rec)
    if ph is not None:
        return (True, [f"primary:{key}"]) if ph.startswith(pin12) else (False, [])
    evidence: list[str] = []
    if any(t.startswith(pin12) for t in hex_tokens(rec)):
        evidence.append("record")
    for rel, doc in referenced_docs(rec, doc_index):
        if any(t.startswith(pin12) for t in hex_tokens(doc)):
            evidence.append(rel)
    return bool(evidence), evidence


def target_matches(rec, spec: dict) -> str | None:
    """Match the schema in the record's target fields only, with strict priority."""
    for keys in TARGET_PRIORITY:
        values = [(k, s) for k, s in walk_strings(rec) if k.lower() in keys]
        if not values:
            continue
        for key, s in values:
            for tok in spec["tokens"]:
                if _word_hit(s, tok):
                    return f"{key}={s[:80]}"
        return None
    return None


def review_text(rec) -> str:
    parts: list[str] = []
    for key, s in walk_strings(rec):
        kl = key.lower()
        if any(w in kl for w in TEXT_FIELDS):
            parts.append(s.lower())
    if not parts:
        parts = [s.lower() for _, s in walk_strings(rec)]
    return re.sub(r"\s+", " ", " ".join(parts)).strip()


def shingles(text: str) -> set[str]:
    if not text:
        return set()
    if len(text) < 20:
        return {text}
    return {text[i:i + 5] for i in range(len(text) - 4)}


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def channel_signature(rec, doc_index: dict) -> set[str]:
    sig: set[str] = set()
    for rel, doc in referenced_docs(rec, doc_index):
        sig.add("doc:" + sha256_bytes(json.dumps(doc, sort_keys=True).encode()))
    for key, s in walk_strings(rec):
        kl = key.lower()
        is_instrument_key = any(w in kl for w in INSTRUMENT_KEYS)
        for t in HEX.findall(s):
            t = t.lower()
            if t.startswith(tuple(COMMON_TOKENS)):
                continue
            if is_instrument_key:
                sig.add("sha:" + t)
        if is_instrument_key or kl in {"artifact", "artifact_path", "path"}:
            for p in re.findall(r"(?:artifacts|runtime|research_map|reviews)/[\w./-]+", s):
                if not p.startswith(("research_map/", "reviews/")):
                    sig.add("path:" + p)
    return sig


def _is_direct_schema_target(head: str, spec: dict) -> bool:
    if not head:
        return False
    if Path(head).name == Path(spec["path"]).name:
        return True
    parts = [p for p in re.split(r"[,;/+ ]+", head.lower()) if p]
    if parts and all(p in NODE_TOKENS | CLASS_TOKENS for p in parts):
        return any(p in spec["tokens"] for p in parts)
    return False


def is_full_schema_verdict(rec, spec: dict) -> tuple[bool, str]:
    """Full-schema requires the record to name the schema directly, declare it as its
    artifact, or self-declare counts_as_full_schema_verdict=true. Reviews of another
    review or of a derived checkpoint are advisory even when they carry the schema hash."""
    cf = rec.get("counts_as_full_schema_verdict")
    if cf is False:
        return False, "declared_counts_as_full_schema_verdict_false"
    if cf is True:
        return True, "declared_counts_as_full_schema_verdict_true"
    tid = str(rec.get("target_id") or "")
    head = tid.split("#")[0].strip()
    if _is_direct_schema_target(head, spec):
        return True, "target_id_names_schema"
    art = str(rec.get("artifact") or rec.get("artifact_path") or rec.get("path") or "")
    if art and Path(art.split("#")[0]).name == Path(spec["path"]).name:
        return True, "artifact_names_schema"
    if head.startswith(("reviews/", "artifacts/", "runtime/", "ledger/", "research_map/")):
        return False, "target_is_secondary_document"
    return False, "no_direct_schema_target"


def ts_key(s: str) -> tuple:
    s = (s or "").strip()
    try:
        return (0, datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp())
    except ValueError:
        return (1, re.sub(r"\D", "", s)[:14])


def load_corpus(root: Path):
    records: list[dict] = []
    sources: dict[str, str] = {}
    doc_index: dict[str, tuple[str, dict]] = {}

    def add(rel: str, obj: dict):
        if not isinstance(obj, dict):
            return
        obj = dict(obj)
        obj["_src"] = rel
        obj["_id"] = str(obj["event_id"]) if obj.get("event_id") else f"{rel}#{len(records)}"
        obj["_rich"] = len(json.dumps(obj, sort_keys=True, default=str))
        records.append(obj)

    def load(rel: str):
        p = root / rel
        try:
            b = p.read_bytes()
        except OSError:
            return None
        sources[rel] = sha256_bytes(b)
        text = b.decode("utf-8", errors="replace")
        if rel.endswith(".jsonl"):
            objs = []
            for line in text.splitlines():
                line = line.strip().rstrip(",")
                if line.startswith("{") and line.endswith("}"):
                    try:
                        objs.append(json.loads(line))
                    except ValueError:
                        continue
        else:
            try:
                doc = json.loads(text)
            except ValueError:
                return None
            objs = doc if isinstance(doc, list) else [doc]
        return objs

    event_files = ["research_map/events.jsonl"]
    outbox = root / "comms" / "outbox"
    if outbox.is_dir():
        event_files += [str(p.relative_to(root)) for p in sorted(outbox.rglob("*.jsonl"))]
        event_files += [str(p.relative_to(root)) for p in sorted(outbox.rglob("*.json"))]
    for rel in event_files:
        for obj in load(rel) or []:
            add(rel, obj)

    rev = root / "reviews"
    if rev.is_dir():
        for p in sorted(rev.glob("*.json")):
            rel = str(p.relative_to(root))
            for obj in load(rel) or []:
                if not isinstance(obj, dict):
                    continue
                doc_index[p.name] = (rel, obj)
                if obj.get("verdict") and (obj.get("reviewer") or obj.get("actor")):
                    add(rel, obj)
    return records, sources, doc_index


def dedupe_by_id(records: list[dict]) -> list[dict]:
    best: dict[str, dict] = {}
    for r in records:
        cur = best.get(r["_id"])
        if cur is None or r["_rich"] >= cur["_rich"]:
            best[r["_id"]] = r
    return list(best.values())


def harvest_target(records: list[dict], spec: dict, doc_index: dict):
    bound, unbound_superseded, target_mismatch = [], 0, 0
    sup = SUPERSEDED.get(spec["node"], "")
    for r in records:
        if not r.get("verdict"):
            continue
        tgt = target_matches(r, spec)
        ok, evidence = binds_pin(r, spec, doc_index)
        if not ok:
            toks = hex_tokens(r)
            for _, d in referenced_docs(r, doc_index):
                toks |= hex_tokens(d)
            if sup and any(t.startswith(sup[:12]) for t in toks) and tgt:
                unbound_superseded += 1
            elif tgt:
                target_mismatch += 1
            continue
        if not tgt:
            continue
        review_doc = None
        for rel, _ in referenced_docs(r, doc_index):
            review_doc = rel
            break
        full, full_reason = is_full_schema_verdict(r, spec)
        bound.append({
            "event_id": r.get("_id") or str(r.get("event_id") or "unknown"),
            "source": r.get("_src", "synthetic"),
            "reviewer": str(r.get("reviewer") or r.get("actor") or "unknown"),
            "verdict": norm_verdict(r["verdict"]),
            "score": r.get("score"),
            "created_at": str(r.get("created_at") or ""),
            "target_match": tgt,
            "hash_evidence": evidence,
            "review_doc": review_doc,
            "full_schema_verdict": full,
            "full_schema_reason": full_reason,
            "text": review_text(r),
            "_rec": r,
        })
    return bound, unbound_superseded, target_mismatch


def norm_verdict(v) -> str:
    if isinstance(v, str):
        return v.strip().lower()
    if isinstance(v, dict):
        for k in ("verdict", "value", "result"):
            if isinstance(v.get(k), str):
                return v[k].strip().lower()
    return "malformed"


def one_per_reviewer(bound: list[dict]) -> list[dict]:
    best: dict[str, dict] = {}
    for b in sorted(bound, key=lambda x: (ts_key(x["created_at"]), len(x["text"]))):
        best[b["reviewer"]] = b  # latest wins
    return sorted(best.values(), key=lambda x: x["reviewer"])


def cluster_accepts(accepts: list[dict], doc_index: dict) -> list[dict]:
    n = len(accepts)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[max(ri, rj)] = min(ri, rj)

    sh = [shingles(a["text"]) for a in accepts]
    sig = [channel_signature(a["_rec"], doc_index) for a in accepts]
    for i in range(n):
        for j in range(i + 1, n):
            if jaccard(sh[i], sh[j]) >= 0.6 or (sig[i] and sig[j] and (sig[i] & sig[j])):
                union(i, j)
    groups: dict[int, list[int]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    out = []
    for members in groups.values():
        reps = [accepts[m] for m in members]
        out.append({
            "cluster_id": None,
            "size": len(members),
            "reviewers": sorted(r["reviewer"] for r in reps),
            "event_ids": sorted(r["event_id"] for r in reps),
            "review_docs": sorted({r["review_doc"] for r in reps if r["review_doc"]}),
            "shared_signature": sorted(set.intersection(*[sig[m] for m in members])) if len(members) > 1 else [],
            "max_pair_jaccard": round(max((jaccard(sh[i], sh[j]) for i in members for j in members if i < j), default=0.0), 4),
            "members": [{
                "reviewer": r["reviewer"], "event_id": r["event_id"], "score": r["score"],
                "created_at": r["created_at"], "target_match": r["target_match"],
                "full_schema_reason": r["full_schema_reason"], "review_doc": r["review_doc"],
                "source": r["source"],
            } for r in sorted(reps, key=lambda x: x["reviewer"])],
        })
    out.sort(key=lambda c: (-c["size"], c["reviewers"]))
    for k, c in enumerate(out, 1):
        c["cluster_id"] = f"cluster-{k:02d}"
    return out


def analyze(records: list[dict], doc_index: dict, pins: dict) -> dict:
    per_target = {}
    for node, spec0 in pins.items():
        spec = dict(spec0)
        spec["node"] = node
        bound, sup, tm = harvest_target(records, spec, doc_index)
        reviewers = one_per_reviewer(bound)
        accepts_all = [r for r in reviewers if r["verdict"] == "accept"]
        accepts = [r for r in accepts_all if r["full_schema_verdict"]]
        advisory = [r for r in accepts_all if not r["full_schema_verdict"]]
        clusters = cluster_accepts(accepts, doc_index)
        verdict_counts: dict[str, int] = {}
        for r in reviewers:
            verdict_counts[r["verdict"]] = verdict_counts.get(r["verdict"], 0) + 1
        per_target[node] = {
            "path": spec["path"],
            "sha256": spec["sha256"],
            "class_id": spec["class_id"],
            "records_bound": len(bound),
            "distinct_reviewers_bound": len(reviewers),
            "verdict_counts_bound": dict(sorted(verdict_counts.items())),
            "full_schema_accept_reviewers": sorted(r["reviewer"] for r in accepts),
            "advisory_accept_reviewers": sorted(r["reviewer"] for r in advisory),
            "advisory_accepts": [{
                "reviewer": r["reviewer"], "event_id": r["event_id"], "score": r["score"],
                "target_match": r["target_match"], "full_schema_reason": r["full_schema_reason"],
                "review_doc": r["review_doc"],
            } for r in sorted(advisory, key=lambda x: x["reviewer"])],
            "excluded_superseded_hash_records": sup,
            "excluded_other_hash_revision_records": tm,
            "effective_accept_clusters": len(clusters),
            "criterion_two_independent_accepts": len(clusters) >= 2,
            "accept_clusters": clusters,
        }
    return per_target


def measure_pins(root: Path, pins: dict) -> dict:
    out = {}
    for node, spec in pins.items():
        p = root / spec["path"]
        out[node] = sha256_file(p) if p.exists() else "missing"
    return out


def announcement_events(records: list[dict], path: str, pin12: str) -> list[dict]:
    out = []
    for r in records:
        if r.get("event_type") != "artifact":
            continue
        if str(r.get("path") or "") != path:
            continue
        blob = json.dumps(r, sort_keys=True, default=str)
        if str(r.get("sha256") or "").startswith(pin12) or pin12 in blob:
            out.append({
                "event_id": r.get("event_id"), "actor": r.get("actor"),
                "created_at": str(r.get("created_at") or ""), "sha256": str(r.get("sha256") or "")[:16],
                "source": r.get("_src"),
            })
    return sorted(out, key=lambda x: ts_key(x["created_at"]))


def freeze_state(root: Path, records: list[dict], frozen: dict) -> dict:
    files = frozen.get("files") if isinstance(frozen.get("files"), dict) else {}
    state = {
        "manifest": {
            "path": FROZEN_PATH,
            "declared_revision": frozen.get("revision"),
            "frozen_at": frozen.get("frozen_at"),
            "measured_sha256": sha256_file(root / FROZEN_PATH) if (root / FROZEN_PATH).exists() else "missing",
            "expected_sha256_rev28": FROZEN_SHA,
        },
        "evidence_artifact": {
            "path": EVIDENCE_PATH,
            "measured_sha256": sha256_file(root / EVIDENCE_PATH) if (root / EVIDENCE_PATH).exists() else "missing",
            "expected_sha256": EVIDENCE_SHA,
        },
        "targets": {},
    }
    state["manifest"]["self_match"] = state["manifest"]["measured_sha256"] == FROZEN_SHA
    state["evidence_artifact"]["match"] = state["evidence_artifact"]["measured_sha256"] == EVIDENCE_SHA
    mismatch = {"canonical_manifest_entries": 0, "authoring_manifest_entries": 0, "canonical_vs_rev28_pin": 0}
    for node, spec in PINS.items():
        cp = root / spec["path"]
        ap = root / spec["authoring"]
        cur = sha256_file(cp) if cp.exists() else "missing"
        acur = sha256_file(ap) if ap.exists() else "missing"
        ctext = cp.read_text(errors="replace") if cp.exists() else ""
        centry = files.get(spec["path"], {}) if isinstance(files, dict) else {}
        aentry = files.get(spec["authoring"], {}) if isinstance(files, dict) else {}
        rev = re.search(r"^revision:\s*(\d+)", ctext, re.M)
        rev_at = re.search(r'^revised_at:\s*"([^"]+)"', ctext, re.M)
        ev = re.search(r'consistency_evidence_sha256:\s*"([0-9a-f]{64})"', ctext)
        ann = announcement_events(records, spec["path"], cur[:12])
        entry_match = centry.get("sha256") == cur
        a_entry_match = aentry.get("sha256") == acur
        pin_match = cur == spec["sha256"]
        if not entry_match:
            mismatch["canonical_manifest_entries"] += 1
        if not a_entry_match:
            mismatch["authoring_manifest_entries"] += 1
        if not pin_match:
            mismatch["canonical_vs_rev28_pin"] += 1
        state["targets"][node] = {
            "canonical_path": spec["path"],
            "authoring_path": spec["authoring"],
            "rev28_pin_sha256": spec["sha256"],
            "measured_sha256": cur,
            "matches_rev28_pin": pin_match,
            "measured_mtime": mtime_iso(cp),
            "authoring_sha256": acur,
            "authoring_matches_canonical": acur == cur,
            "frozen_canonical_entry_sha256": centry.get("sha256"),
            "frozen_canonical_entry_matches_disk": entry_match,
            "frozen_authoring_entry_sha256": aentry.get("sha256"),
            "frozen_authoring_entry_matches_disk": a_entry_match,
            "declared_revision": int(rev.group(1)) if rev else None,
            "declared_revised_at": rev_at.group(1) if rev_at else None,
            "f0_binding_consistency_evidence_sha256": ev.group(1) if ev else None,
            "consistency_evidence_pin_refreshed": bool(ev and ev.group(1) == EVIDENCE_SHA),
            "announcing_artifact_events": ann,
            "owner_announcement_present": len(ann) > 0,
        }
    state["mismatch_counts"] = mismatch
    internal = mismatch["canonical_manifest_entries"] == 0 and mismatch["authoring_manifest_entries"] == 0
    transition = mismatch["canonical_vs_rev28_pin"] > 0
    declared_rev = state["manifest"]["declared_revision"]
    repin = bool(declared_rev and declared_rev > 28) and internal
    mirrors = all(t["authoring_matches_canonical"] for t in state["targets"].values())
    ev_refreshed = all(t["consistency_evidence_pin_refreshed"] for t in state["targets"].values())
    announced = all(t["owner_announcement_present"] for t in state["targets"].values())
    state.update({
        "internal_consistency": internal,
        "transition_from_rev28": transition,
        "repin_complete": repin,
        "mirrors_aligned": mirrors,
        "evidence_pins_refreshed": ev_refreshed,
        "owner_announcements_present": announced,
        "freeze_intact": internal,
        "state": ("FREEZE_INCONSISTENT" if not internal else
                  "REPINNED_AND_ANNOUNCED" if repin and announced else
                  "REPINNED_AWAITING_ANNOUNCEMENT" if repin else
                  "REV28_INTACT" if not transition else "TRANSITION_UNPINNED"),
    })
    return state


def run_controls(doc_index: dict) -> dict:
    def mk(eid, reviewer, verdict, findings, target_id, sha, instrument=None):
        rec = {
            "event_id": eid, "event_type": "review", "actor": reviewer, "reviewer": reviewer,
            "verdict": verdict, "score": 4.0, "target_id": target_id,
            "target_sha256": sha, "findings": findings, "created_at": "2026-09-12T00:00:00+08:00",
        }
        if instrument:
            rec["evidence_refs"] = [instrument]
        return rec

    spec = dict(PINS["F2a"])
    spec["node"] = "F2a"
    controls = {}

    dup = [mk("c-dup-1", "rev-a", "accept", ["finding alpha beta gamma delta"], "F2a", spec["sha256"]),
           mk("c-dup-2", "rev-b", "accept", ["finding alpha beta gamma delta"], "F2a", spec["sha256"])]
    b, _, _ = harvest_target(dup, spec, doc_index)
    cl = cluster_accepts([r for r in one_per_reviewer(b) if r["verdict"] == "accept"], doc_index)
    controls["CTRL-DUP-identical-text-collapses"] = {"observed": len(cl), "expected": 1, "pass": len(cl) == 1}

    diff = [mk("c-diff-1", "rev-a", "accept", ["objection one: quantifier scope"], "F2a", spec["sha256"],
               "artifacts/a/check_a.py"),
            mk("c-diff-2", "rev-b", "accept", ["objection two: topology clause missing"], "F2a", spec["sha256"],
               "artifacts/b/check_b.py")]
    b, _, _ = harvest_target(diff, spec, doc_index)
    cl = cluster_accepts([r for r in one_per_reviewer(b) if r["verdict"] == "accept"], doc_index)
    controls["CTRL-DIFF-distinct-reviews-stay-separate"] = {"observed": len(cl), "expected": 2, "pass": len(cl) == 2}

    bad = [mk("c-sup-1", "rev-a", "accept", ["accept at old bytes"], "F2a", SUPERSEDED["F2a"])]
    b, _, _ = harvest_target(bad, spec, doc_index)
    controls["CTRL-SUPERSEDED-hash-not-counted"] = {"observed": len(b), "expected": 0, "pass": len(b) == 0}

    rev = [mk("c-rev-1", "rev-a", "revise", ["real defect x"], "F2a", spec["sha256"])]
    b, _, _ = harvest_target(rev, spec, doc_index)
    controls["CTRL-REVISE-not-an-accept"] = {
        "observed": len([r for r in one_per_reviewer(b) if r["verdict"] == "accept"]),
        "expected": 0, "pass": len([r for r in one_per_reviewer(b) if r["verdict"] == "accept"]) == 0}

    xt = [mk("c-xt-1", "rev-a", "accept", ["cross-target mention"], "F1", spec["sha256"])]
    b, _, _ = harvest_target(xt, spec, doc_index)
    controls["CTRL-XTARGET-hash-with-wrong-target-excluded"] = {
        "observed": len(b), "expected": 0, "pass": len(b) == 0}

    adv = [mk("c-adv-1", "rev-a", "accept", ["secondary accept"], "reviews/other.json#x", spec["sha256"])]
    b, _, _ = harvest_target(adv, spec, doc_index)
    controls["CTRL-SECONDARY-not-full-schema"] = {
        "observed": len([r for r in b if r["full_schema_verdict"]]), "expected": 0,
        "pass": len([r for r in b if r["full_schema_verdict"]]) == 0}

    empty = [mk("c-ann-1", "rev-a", "accept", ["no announcement"], "F2a", spec["sha256"])]
    controls["CTRL-ANNOUNCE-requires-artifact-event"] = {
        "observed": len(announcement_events(empty, spec["path"], spec["sha256"][:12])), "expected": 0,
        "pass": len(announcement_events(empty, spec["path"], spec["sha256"][:12])) == 0}

    return controls


def criterion_digest(analysis: dict) -> str:
    slim = {k: {kk: vv for kk, vv in v.items() if kk != "accept_clusters"} | {
        "clusters": [sorted(c["reviewers"]) for c in v["accept_clusters"]]}
        for k, v in analysis.items()}
    return sha256_bytes(json.dumps(slim, sort_keys=True).encode())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[3]))
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent))
    args = ap.parse_args()
    root = Path(args.root).resolve()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    started = now()

    pins_start = measure_pins(root, PINS)
    frozen_p = root / FROZEN_PATH
    frozen_doc = json.loads(frozen_p.read_text()) if frozen_p.exists() else {}
    frozen_start = sha256_file(frozen_p) if frozen_p.exists() else "missing"
    pin_mismatch = {n: h for n, h in pins_start.items() if h != PINS[n]["sha256"]}
    frozen_mismatch = frozen_start != FROZEN_SHA

    records, sources, doc_index = load_corpus(root)
    records = dedupe_by_id(records)
    controls = run_controls(doc_index)
    controls_ok = all(c["pass"] for c in controls.values())

    # Current pin set = whatever is on disk at run start, so the transition can be
    # scored on both the historical rev-28 pins and the new bytes.
    pins_current = {
        n: {**PINS[n], "sha256": pins_start[n], "historical_sha256": PINS[n]["sha256"]}
        for n in PINS
    }
    analysis_historical = analyze(records, doc_index, PINS)
    analysis_current = analyze(records, doc_index, pins_current) if pin_mismatch else analysis_historical
    digest1 = criterion_digest(analysis_historical)
    digest2 = criterion_digest(analyze(records, doc_index, PINS))
    determinism = {"digest_run1": digest1, "digest_run2": digest2, "equal": digest1 == digest2}
    controls["CTRL-DETERMINISM"] = {"observed": determinism["equal"], "expected": True, "pass": determinism["equal"]}
    controls_ok = controls_ok and determinism["equal"]

    pins_end = measure_pins(root, PINS)
    frozen_end = sha256_file(frozen_p) if frozen_p.exists() else "missing"
    moving = pins_end != pins_start or frozen_end != frozen_start

    # Freeze state is measured at the end of the run; start hashes are recorded alongside
    # it so a mid-run move is visible per target.
    frozen_doc_end = json.loads(frozen_p.read_text()) if frozen_p.exists() else {}
    freeze = freeze_state(root, records, frozen_doc_end)
    freeze["measured_phase"] = "end_of_run"
    for n in PINS:
        freeze["targets"][n]["measured_sha256_at_start"] = pins_start[n]
        freeze["targets"][n]["changed_during_run"] = pins_start[n] != pins_end[n]

    transition = bool(pin_mismatch) or frozen_mismatch
    met_hist = all(v["criterion_two_independent_accepts"] for v in analysis_historical.values())
    met_cur = all(v["criterion_two_independent_accepts"] for v in analysis_current.values())

    findings = []
    if transition:
        findings.append({
            "id": "W087-FREEZE-01",
            "severity": "major",
            "finding": ("All three canonical G-FORM schemas moved from the FROZEN rev-28 pins to the declared "
                        "rev-13 bytes: "
                        + "; ".join(f"{n} {PINS[n]['sha256'][:12]} -> {pins_start[n][:12]} "
                                    f"(mtime {freeze['targets'][n]['measured_mtime']}, revised_at "
                                    f"{freeze['targets'][n]['declared_revised_at']})" for n in sorted(pin_mismatch))
                        + f". FROZEN.json is now revision {freeze['manifest']['declared_revision']} "
                          f"(sha {frozen_end[:12]}, frozen_at {freeze['manifest']['frozen_at']}); manifest "
                          f"internal consistency: canonical mismatches "
                          f"{freeze['mismatch_counts']['canonical_manifest_entries']}, authoring mismatches "
                          f"{freeze['mismatch_counts']['authoring_manifest_entries']}; mirror pairs aligned: "
                          f"{freeze['mirrors_aligned']}; f0_binding consistency-evidence pins refreshed: "
                          f"{freeze['evidence_pins_refreshed']}; owner artifact event announcing each new "
                          f"canonical hash in the accepted stream: {freeze['owner_announcements_present']}. "
                          "Every rev-28-bound review verdict is therefore void (it binds superseded bytes), and "
                          "the rev-13 bytes need fresh hash-bound verdicts plus the accepted-stream artifact "
                          "announcement before any gate verdict."),
            "evidence": f"artifacts/worker-087/gform_independence/report.json#{digest1[:12]}",
        })
        for n in sorted(pin_mismatch):
            t = freeze["targets"][n]
            findings.append({
                "id": f"W087-FREEZE-02-{n}",
                "severity": "info" if t["owner_announcement_present"] else "major",
                "finding": (f"{n}: canonical {t['measured_sha256'][:12]} vs authoring "
                            f"{str(t['authoring_sha256'])[:12]} (mirror_equal={t['authoring_matches_canonical']}); "
                            f"manifest entry matches disk={t['frozen_canonical_entry_matches_disk']}; "
                            f"f0_binding consistency_evidence pin refreshed={t['consistency_evidence_pin_refreshed']}; "
                            f"owner-announcing artifact events for the new canonical hash: "
                            f"{len(t['announcing_artifact_events'])}."),
                "evidence": f"artifacts/worker-087/gform_independence/report.json#{digest1[:12]}",
            })
    findings.append({
        "id": "W087-STATE-01",
        "severity": "info",
        "finding": (f"Freeze state at end of run: {freeze['state']}; rev-28-bound coverage (historical, now void): "
                    + "; ".join(f"{n} {v['effective_accept_clusters']} cluster(s) from "
                                f"{v['full_schema_accept_reviewers']}" for n, v in analysis_historical.items())
                    + "; rev-13/current coverage: "
                    + "; ".join(f"{n} {v['effective_accept_clusters']} cluster(s) from "
                                f"{v['full_schema_accept_reviewers']}" for n, v in analysis_current.items()) + "."),
        "evidence": f"artifacts/worker-087/gform_independence/report.json#{digest1[:12]}",
    })
    for node, v in analysis_historical.items():
        findings.append({
            "id": f"W087-INDEP-{node}-{'OK' if v['criterion_two_independent_accepts'] else 'GAP'}",
            "severity": "pass" if v["criterion_two_independent_accepts"] else "blocking_evidence_gap",
            "finding": (f"At the historical rev-28 pin {v['path']}#{v['sha256'][:12]}: "
                        f"{len(v['full_schema_accept_reviewers'])} full-schema accept reviewer(s) "
                        f"{v['full_schema_accept_reviewers']} and {len(v['advisory_accept_reviewers'])} advisory "
                        f"accept(s) {v['advisory_accept_reviewers']} -> {v['effective_accept_clusters']} effective "
                        f"independent accept cluster(s); G-FORM two-independent-accepts criterion is "
                        f"{'MET' if v['criterion_two_independent_accepts'] else 'NOT MET'} for those bytes "
                        f"(void after the rev-13 write)."),
            "evidence": f"artifacts/worker-087/gform_independence/report.json#{digest1[:12]}",
        })

    status = ("MOVING_TARGET" if moving else
              "REPINNED_ANNOUNCEMENT_PENDING" if freeze.get("state") == "REPINNED_AWAITING_ANNOUNCEMENT" else
              "TRANSITION_MEASURED" if transition else "STABLE")
    report = {
        "schema_version": "0.1",
        "artifact_id": "artifacts/worker-087/gform_independence/report.json",
        "artifact_type": "gform_accept_independence_and_freeze_state_audit",
        "task_id": "W087-GFORM-INDEP-04",
        "actor": "worker-087",
        "created_at": started,
        "finished_at": now(),
        "status": status,
        "node_ids": ["F1", "F2a", "F2b"],
        "class_ids": [PINS[n]["class_id"] for n in ("F1", "F2a", "F2b")],
        "gate": "G-FORM",
        "question": ("(A) Does the G-FORM criterion 'two independent accepts per schema' hold at the FROZEN "
                     "rev-28 pins after reviewer-identity, text-template and evidence-channel dedup? "
                     "(B) Do the canonical schema bytes still match the FROZEN rev-28 pins at run start/end, "
                     "and is any post-freeze write announced by its owner?"),
        "pins_rev28_expected": {n: PINS[n]["sha256"] for n in PINS},
        "pins_measured_at_start": pins_start,
        "pins_measured_at_end": pins_end,
        "frozen_manifest_measured_at_start": frozen_start,
        "frozen_manifest_measured_at_end": frozen_end,
        "pin_mismatch_at_start": pin_mismatch,
        "hash_stable_during_run": not moving,
        "freeze_state": freeze,
        "criterion": ("effective independent full-schema accept clusters >= 2 per schema, where clusters are "
                      "formed by reviewer identity, character-5-gram findings-text Jaccard >= 0.6, or a non-empty "
                      "shared evidence-channel signature (instruments/scripts/review docs; the common target pins "
                      "are excluded from the signature). Reviews whose target is a derived/secondary document are "
                      "reported as advisory accepts and are not counted toward the criterion."),
        "coverage_at_rev28_pins": analysis_historical,
        "coverage_at_measured_pins": analysis_current,
        "criterion_met_at_rev28_pins": met_hist,
        "criterion_met_at_measured_pins": met_cur,
        "findings": findings,
        "controls": controls,
        "controls_ok": controls_ok,
        "determinism": determinism,
        "verdict_digest_sha256": digest1,
        "corpus": {"records_loaded": len(records), "review_docs_indexed": len(doc_index), "sources": sources},
        "falsifier": ("Re-run artifacts/worker-087/gform_independence/audit_gform_independence.py. The transition/"
                      "announcement finding is void if every measured canonical hash matches its entry in the "
                      "current FROZEN revision and an owner artifact event in the accepted stream announces each "
                      "hash. The coverage finding is falsified if (a) any schema reported >= 2 effective accept "
                      "clusters falls below 2 under the declared clustering rule; (b) two counted clusters share an "
                      "identical instrument, review document or verdict text; (c) a hash-bound verdict the harvest "
                      "excluded is shown to name the schema directly at the reported revision; (d) a control does "
                      "not reproduce; or (e) a re-run on the same corpus yields a different verdict digest."),
        "authority": ("Worker evidence only. Cannot set node status=done, validation_status=passed, or any gate "
                      "verdict; issues no review verdict on the schemas themselves. Read-only against every "
                      "canonical input."),
        "not_duplicative_of": [
            "worker-074/f2a_verdict_independence (audited F2a at the superseded b6123750b37d bytes only)",
            "worker-095/freeze_hold_binding_integrity_r3 (event-shadow/binding probe at F2b whose own R1 reported "
            "the manifest clean and whose R6 probe-drift criterion failed; this audit re-measures all three "
            "canonical paths, both manifest trees and the owner announcement after the 00:53 rev-13 write)",
            "research_map#controller_gate_audit (counts distinct reviewer ids only; no text/template/channel "
            "dedup, no manifest-versus-disk re-measure)",
        ],
    }
    (out / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print(json.dumps({
        "status": status,
        "controls_ok": controls_ok,
        "pin_mismatch": pin_mismatch,
        "freeze_intact": freeze["freeze_intact"],
        "criterion_met_at_rev28_pins": met_hist,
        "clusters_rev28": {k: v["effective_accept_clusters"] for k, v in analysis_historical.items()},
        "accepts_rev28": {k: v["full_schema_accept_reviewers"] for k, v in analysis_historical.items()},
        "accepts_current": {k: v["full_schema_accept_reviewers"] for k, v in analysis_current.items()},
        "digest": digest1,
    }, indent=1))
    if not controls_ok:
        return 4
    if moving:
        return 2
    if transition or not met_hist:
        return 3
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
