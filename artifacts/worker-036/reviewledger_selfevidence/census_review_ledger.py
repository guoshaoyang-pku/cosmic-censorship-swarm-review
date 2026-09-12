#!/usr/bin/env python3
"""W036-A1-REVIEWLEDGER-SELFEVIDENCE-01.

Deterministic, stdlib-only census of the review ledger in research_map/research_map.json:
is every accepted review record still backed by bytes on disk that carry the recorded
verdict / score / reviewer, and does the declared self-evidence digest resolve?

Read-only.  Issues no gate verdict, sets no node status and no validation_status.
Worker evidence only.

Usage:
    python3 census_review_ledger.py --stamp 2026-09-12T01:40:00+08:00 --out report.json
    python3 census_review_ledger.py --selftest
"""
import argparse
import hashlib
import json
import os
import re
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
MAP_REL = "research_map/research_map.json"
EVENTS_REL = "research_map/events.jsonl"
GATES = ("G-F0", "G-FORM", "G-LIT", "G-AUDIT", "G-NUM")
VERDICTS = ("accept", "revise", "reject", "inconclusive")
HEX_RE = re.compile(r"([0-9a-fA-F]{8,64})")


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(path):
    with open(path, "rb") as fh:
        return sha256_bytes(fh.read())


def split_ref(s):
    """Return (path, digest) for 'path#frag' refs; None for URLs / non-strings."""
    if not isinstance(s, str) or "://" in s:
        return None, None
    path, _, frag = s.partition("#")
    digest = None
    if frag:
        m = HEX_RE.search(frag)
        if m:
            digest = m.group(1).lower()
    return (path or None), digest


def norm_verdict(v):
    if not isinstance(v, str):
        return None
    low = v.strip().lower()
    for cand in VERDICTS:
        if cand in low:
            return cand
    return low


def as_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def pick(d, names):
    for n in names:
        if isinstance(d, dict) and d.get(n) is not None:
            return d[n]
    return None


def is_review_path(p):
    if not isinstance(p, str):
        return False
    base = os.path.basename(p).lower()
    return p.startswith("reviews/") or "review" in base


class Snapshot:
    """Read-once byte snapshot: every referenced file is read and hashed exactly once."""

    def __init__(self, root):
        self.root = root
        self.files = {}   # rel path -> bytes | None (None = missing/dir)
        self.hashes = {}  # rel path -> sha256 hex

    def get(self, rel):
        if rel in self.files:
            return self.files[rel]
        abs_path = os.path.join(self.root, rel)
        if os.path.isfile(abs_path):
            try:
                with open(abs_path, "rb") as fh:
                    data = fh.read()
            except OSError:
                data = None
        else:
            data = None
        self.files[rel] = data
        self.hashes[rel] = sha256_bytes(data) if data is not None else None
        return data

    def digest(self, rel):
        self.get(rel)
        return self.hashes.get(rel)

    def corpus_digest(self):
        items = sorted((p, h) for p, h in self.hashes.items() if h)
        blob = "\n".join(f"{h}  {p}" for p, h in items).encode()
        return sha256_bytes(blob), len(items)


def collect_self_candidates(rec):
    """(kind, path, digest, digest_origin) candidate self-evidence refs for one record."""
    out = []
    artifact = rec.get("artifact")
    if isinstance(artifact, str):
        apath, afrag = split_ref(artifact)
        if apath and is_review_path(apath):
            declared = rec.get("artifact_sha256")
            d = None
            if isinstance(declared, str):
                m = HEX_RE.search(declared)
                d = m.group(1).lower() if m else None
            if d is None and afrag:
                d = afrag
            out.append(("artifact", apath, d, "artifact_sha256" if d else None))
    for key in ("evidence_refs", "artifact_refs"):
        for ref in rec.get(key) or []:
            p, d = split_ref(ref)
            if p and is_review_path(p):
                out.append((key, p, d, key))
    target = rec.get("target_id")
    if isinstance(target, str) and target.startswith("reviews/"):
        p, d = split_ref(target)
        out.append(("target_id", p, d, "target_id"))
    # dedupe, artifact first
    seen, uniq = set(), []
    for kind, p, d, origin in out:
        if p in seen:
            continue
        seen.add(p)
        uniq.append((kind, p, d, origin))
    return uniq


def classify_record(rec, snap):
    """Return a deterministic classification dict for one map review record."""
    candidates = collect_self_candidates(rec)
    row = {
        "event_id": rec.get("event_id"),
        "reviewer": rec.get("reviewer"),
        "actor": rec.get("actor"),
        "verdict_record": rec.get("verdict"),
        "verdict_norm": norm_verdict(rec.get("verdict")),
        "score_record": as_float(rec.get("score")),
        "gate": rec.get("gate"),
        "node_id": rec.get("node_id"),
        "target_id": rec.get("target_id"),
        "class_id": rec.get("class_id"),
        "created_at": rec.get("created_at"),
        "self_path": None,
        "self_origin": None,
        "self_is_own_artifact": False,
        "has_any_path_ref": False,
        "self_digest_declared": None,
        "self_digest_measured": None,
        "self_digest_full": False,
        "file_verdict": None,
        "file_score": None,
        "file_reviewer": None,
        "file_target": None,
        "verdict_match": None,
        "score_match": None,
        "reviewer_match": None,
        "class": None,
        "refs_total": 0,
        "refs_match": 0,
        "refs_drift": 0,
        "refs_no_digest": 0,
        "refs_missing": 0,
    }
    if not candidates:
        row["class"] = "SE_NONE"
        row["has_any_path_ref"] = any(
            split_ref(s)[0]
            for key in ("evidence_refs", "artifact_refs")
            for s in (rec.get(key) or [])
        ) or bool(isinstance(rec.get("artifact"), str) and "/" in rec.get("artifact"))
        return row
    kind, path, declared, origin = candidates[0]
    row["self_path"] = path
    row["self_origin"] = f"{kind}:{origin}" if origin else kind
    row["self_is_own_artifact"] = kind == "artifact"
    row["has_any_path_ref"] = True
    data = snap.get(path)
    if data is None:
        row["class"] = "SE_MISSING"
        return row
    measured = snap.digest(path)
    row["self_digest_measured"] = measured
    row["self_digest_declared"] = declared
    if declared:
        row["self_digest_full"] = len(declared) == 64
        digest_ok = (measured == declared) if len(declared) == 64 else measured.startswith(declared)
    else:
        digest_ok = None
    # semantic layer
    try:
        doc = json.loads(data.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        doc = None
    if isinstance(doc, dict):
        fv = norm_verdict(pick(doc, ["verdict", "decision", "review_verdict", "recommendation"]))
        fs = as_float(pick(doc, ["score", "rating"]))
        fr = pick(doc, ["reviewer", "reviewer_id", "actor"])
        ft = pick(doc, ["target_id", "target", "reviewed_artifact"])
        row["file_verdict"], row["file_score"] = fv, fs
        row["file_reviewer"] = fr if isinstance(fr, str) else None
        row["file_target"] = ft if isinstance(ft, str) else None
        row["verdict_match"] = (fv == row["verdict_norm"]) if fv is not None else None
        row["score_match"] = (
            abs(fs - row["score_record"]) < 1e-9
            if (fs is not None and row["score_record"] is not None)
            else None
        )
        row["reviewer_match"] = (
            fr.strip() == str(row["reviewer"]).strip()
            if (isinstance(fr, str) and row["reviewer"] is not None)
            else None
        )
    # classify
    sem_known = row["verdict_match"] is not None or row["score_match"] is not None
    sem_ok = row["verdict_match"] is not False and row["score_match"] is not False
    if digest_ok is True:
        row["class"] = "SE_VERIFIED" if sem_ok else "SE_SEMANTIC_DRIFT"
    elif digest_ok is False:
        row["class"] = "SE_DIGEST_DRIFT_SEMANTICS_OK" if sem_ok else "SE_SEMANTIC_DRIFT"
    else:
        if sem_known and not sem_ok:
            row["class"] = "SE_SEMANTIC_DRIFT"
        elif sem_known:
            row["class"] = "SE_SEMANTIC_ONLY"
        else:
            row["class"] = "SE_NO_DIGEST"
    # all refs (addressability of the whole record)
    refs = []
    for key in ("evidence_refs", "artifact_refs"):
        for ref in rec.get(key) or []:
            p, d = split_ref(ref)
            if p:
                refs.append((p, d))
    if isinstance(rec.get("artifact"), str) and not is_review_path(rec.get("artifact")):
        p, d = split_ref(rec.get("artifact"))
        if p:
            refs.append((p, rec.get("artifact_sha256") if isinstance(rec.get("artifact_sha256"), str) else d))
    row["refs_total"] = len(refs)
    for p, d in refs:
        data = snap.get(p)
        if data is None:
            row["refs_missing"] += 1
            continue
        m = snap.digest(p)
        hh = d.lower() if isinstance(d, str) else None
        if hh and (m == hh if len(hh) == 64 else m.startswith(hh)):
            row["refs_match"] += 1
        elif hh:
            row["refs_drift"] += 1
        else:
            row["refs_no_digest"] += 1
    return row


def summarize(rows, events_review_ids=None):
    from collections import Counter, defaultdict

    classes = Counter(r["class"] for r in rows)
    accepts = [r for r in rows if r["verdict_norm"] == "accept"]
    gate_accepts = [r for r in accepts if r["gate"] in GATES]
    own_drift = [
        r for r in rows
        if r["self_is_own_artifact"] and r["class"] == "SE_SEMANTIC_DRIFT"
    ]
    own_missing = [
        r for r in rows
        if r["self_is_own_artifact"] and r["class"] == "SE_MISSING"
    ]
    # same cited review file, contradictory recorded verdicts/scores
    by_path = defaultdict(list)
    for r in rows:
        if r["self_path"]:
            by_path[r["self_path"]].append(r)
    collisions = []
    for path, group in sorted(by_path.items()):
        combos = {(g["verdict_norm"], g["score_record"]) for g in group}
        if len(group) > 1 and len(combos) > 1:
            collisions.append({
                "path": path,
                "records": len(group),
                "distinct_recorded_verdict_score": sorted(
                    [list(c) for c in combos], key=lambda x: (str(x[0]), str(x[1]))
                ),
                "file_verdict": group[0]["file_verdict"],
                "file_score": group[0]["file_score"],
                "event_ids": sorted(str(g["event_id"]) for g in group),
            })
    summary = {
        "records": len(rows),
        "class_counts": dict(sorted(classes.items())),
        "records_without_review_file_path": classes.get("SE_NONE", 0),
        "records_without_any_path_ref": sum(
            1 for r in rows if not r["has_any_path_ref"]
        ),
        "accepts": len(accepts),
        "gate_accepts": len(gate_accepts),
        "accepts_by_self_class": dict(sorted(Counter(r["class"] for r in accepts).items())),
        "gate_accepts_by_self_class": dict(sorted(Counter(r["class"] for r in gate_accepts).items())),
        "gate_accepts_verified": sum(1 for r in gate_accepts if r["class"] == "SE_VERIFIED"),
        "accepts_unverified": [
            {
                "event_id": r["event_id"],
                "reviewer": r["reviewer"],
                "gate": r["gate"],
                "target_id": r["target_id"],
                "self_path": r["self_path"],
                "self_is_own_artifact": r["self_is_own_artifact"],
                "class": r["class"],
                "created_at": r["created_at"],
            }
            for r in accepts
            if r["class"] not in ("SE_VERIFIED",)
        ],
        "semantic_drift": [
            {
                "event_id": r["event_id"],
                "reviewer": r["reviewer"],
                "gate": r["gate"],
                "self_path": r["self_path"],
                "self_is_own_artifact": r["self_is_own_artifact"],
                "verdict_record": r["verdict_record"],
                "verdict_file": r["file_verdict"],
                "score_record": r["score_record"],
                "score_file": r["file_score"],
                "class": r["class"],
                "created_at": r["created_at"],
            }
            for r in rows
            if r["class"] == "SE_SEMANTIC_DRIFT"
        ],
        "own_artifact_drift": [
            {
                "event_id": r["event_id"],
                "reviewer": r["reviewer"],
                "gate": r["gate"],
                "path": r["self_path"],
                "verdict_record": r["verdict_record"],
                "verdict_file": r["file_verdict"],
                "score_record": r["score_record"],
                "score_file": r["file_score"],
            }
            for r in own_drift
        ],
        "own_artifact_missing": [
            {"event_id": r["event_id"], "reviewer": r["reviewer"], "path": r["self_path"]}
            for r in own_missing
        ],
        "verdict_drift": [
            {
                "event_id": r["event_id"],
                "reviewer": r["reviewer"],
                "gate": r["gate"],
                "self_path": r["self_path"],
                "verdict_record": r["verdict_record"],
                "verdict_file": r["file_verdict"],
                "score_record": r["score_record"],
                "score_file": r["file_score"],
                "target_id": r["target_id"],
            }
            for r in rows
            if r["class"] == "SE_SEMANTIC_DRIFT" and r["verdict_match"] is False
        ],
        "score_drift": [
            {
                "event_id": r["event_id"],
                "reviewer": r["reviewer"],
                "gate": r["gate"],
                "self_path": r["self_path"],
                "verdict_record": r["verdict_record"],
                "verdict_file": r["file_verdict"],
                "score_record": r["score_record"],
                "score_file": r["file_score"],
                "target_id": r["target_id"],
            }
            for r in rows
            if r["class"] == "SE_SEMANTIC_DRIFT" and r["verdict_match"] is not False
        ],
        "shared_review_path_collisions": collisions,
        "short_digest_only": sum(
            1 for r in rows if r["self_digest_declared"] and not r["self_digest_full"]
        ),
    }
    if events_review_ids is not None:
        map_ids = {r["event_id"] for r in rows}
        summary["events_review_ids"] = len(events_review_ids)
        summary["events_review_ids_absent_from_map"] = sorted(events_review_ids - map_ids)
        summary["map_ids_absent_from_events"] = sorted(map_ids - events_review_ids)
    return summary


def run(root, stamp, out_path=None):
    map_abs = os.path.join(root, MAP_REL)
    with open(map_abs, "rb") as fh:
        map_bytes = fh.read()
    map_sha = sha256_bytes(map_bytes)
    doc = json.loads(map_bytes.decode("utf-8"))
    recs = doc.get("reviews") or []
    snap = Snapshot(root)
    rows = [classify_record(r, snap) for r in recs]
    rows.sort(key=lambda r: (str(r["event_id"]), str(r["self_path"])))
    # accepted-stream reconciliation
    events_review_ids = set()
    events_abs = os.path.join(root, EVENTS_REL)
    if os.path.isfile(events_abs):
        with open(events_abs, "rb") as fh:
            events_bytes = fh.read()
        events_sha = sha256_bytes(events_bytes)
        for line in events_bytes.decode("utf-8", "replace").splitlines():
            if '"review"' not in line:
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get("event_type") == "review":
                events_review_ids.add(d.get("event_id"))
    else:
        events_sha = None
    summary = summarize(rows, events_review_ids)
    corpus_digest, corpus_files = snap.corpus_digest()
    # fail-closed stability check: map bytes must not move within the run
    with open(map_abs, "rb") as fh:
        map_sha_after = sha256_bytes(fh.read())
    report = {
        "instrument": "W036-A1-REVIEWLEDGER-SELFEVIDENCE-01",
        "worker": "worker-036",
        "stamp": stamp,
        "root": os.path.abspath(root),
        "pins": {
            "map_path": MAP_REL,
            "map_sha256": map_sha,
            "map_sha256_after": map_sha_after,
            "events_path": EVENTS_REL,
            "events_sha256": events_sha,
            "corpus_digest": corpus_digest,
            "corpus_files": corpus_files,
        },
        "snapshot_stable": map_sha == map_sha_after,
        "summary": summary,
        "rows": rows,
    }
    if out_path:
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=1, sort_keys=True)
            fh.write("\n")
    return report


# --------------------------------------------------------------------------- selftest
def _selftest():
    checks = []

    def ck(name, cond):
        checks.append((name, bool(cond)))
        if not cond:
            print(f"SELFTEST FAIL: {name}")

    with tempfile.TemporaryDirectory() as td:
        os.makedirs(os.path.join(td, "reviews"))
        os.makedirs(os.path.join(td, "schemas"))
        good = json.dumps({"verdict": "accept", "score": 4.0, "reviewer": "w-test",
                           "target_id": "F1"}).encode()
        with open(os.path.join(td, "reviews", "good.json"), "wb") as fh:
            fh.write(good)
        with open(os.path.join(td, "reviews", "nomatch.json"), "wb") as fh:
            fh.write(json.dumps({"verdict": "revise", "score": 2.0}).encode())
        with open(os.path.join(td, "reviews", "nodigest.json"), "wb") as fh:
            fh.write(json.dumps({"verdict": "accept", "score": 4.0}).encode())
        with open(os.path.join(td, "schemas", "t.yaml"), "wb") as fh:
            fh.write(b"x: 1\n")
        good_sha = sha256_bytes(good)
        t_sha = sha256_file(os.path.join(td, "schemas", "t.yaml"))
        recs = [
            {"event_id": "e1", "verdict": "accept", "score": 4.0, "reviewer": "w-test",
             "target_id": "F1", "artifact": "reviews/good.json", "artifact_sha256": good_sha,
             "evidence_refs": [f"schemas/t.yaml#{t_sha[:12]}"]},
            {"event_id": "e2", "verdict": "accept", "score": 4.0, "reviewer": "w-test",
             "target_id": "F1", "artifact": "reviews/good.json",
             "artifact_sha256": "0" * 64, "evidence_refs": []},
            {"event_id": "e3", "verdict": "accept", "score": 4.0, "reviewer": "w-test",
             "target_id": "F1", "artifact": "reviews/nomatch.json",
             "artifact_sha256": None, "evidence_refs": []},
            {"event_id": "e4", "verdict": "accept", "score": 4.0, "reviewer": "w-test",
             "target_id": "F1", "artifact": "reviews/nodigest.json", "evidence_refs": []},
            {"event_id": "e5", "verdict": "accept", "score": 4.0, "reviewer": "w-test",
             "target_id": "F1", "artifact": "reviews/absent.json", "evidence_refs": []},
            {"event_id": "e6", "verdict": "accept", "score": 4.0, "reviewer": "w-test",
             "target_id": "F1", "evidence_refs": ["schemas/t.yaml"]},
            {"event_id": "e7", "verdict": "accept", "score": 3.0, "reviewer": "w-test",
             "target_id": "F1", "artifact": "reviews/good.json",
             "artifact_sha256": good_sha[:12], "evidence_refs": []},
        ]
        os.makedirs(os.path.join(td, "research_map"), exist_ok=True)
        with open(os.path.join(td, MAP_REL), "w") as fh:
            json.dump({"reviews": recs}, fh)
        report = run(td, "selftest")
        by_id = {r["event_id"]: r for r in report["rows"]}
        ck("e1 SE_VERIFIED", by_id["e1"]["class"] == "SE_VERIFIED")
        ck("e1 refs match counted", by_id["e1"]["refs_match"] == 1)
        ck("e2 digest drift same semantics", by_id["e2"]["class"] == "SE_DIGEST_DRIFT_SEMANTICS_OK")
        ck("e3 semantic drift", by_id["e3"]["class"] == "SE_SEMANTIC_DRIFT")
        ck("e4 semantic only", by_id["e4"]["class"] == "SE_SEMANTIC_ONLY")
        ck("e5 missing", by_id["e5"]["class"] == "SE_MISSING")
        ck("e6 no review path -> SE_NONE", by_id["e6"]["class"] == "SE_NONE")
        ck("e7 prefix digest verifies", by_id["e7"]["class"] == "SE_SEMANTIC_DRIFT")
        ck("short digest flagged", report["summary"]["short_digest_only"] == 1)
        ck("own artifact drift e3+e7", len(report["summary"]["own_artifact_drift"]) == 2)
        ck("own artifact missing e5", len(report["summary"]["own_artifact_missing"]) == 1)
        ck("verdict drift e3", len(report["summary"]["verdict_drift"]) == 1)
        ck("score drift e7", len(report["summary"]["score_drift"]) == 1)
        ck("snapshot stable", report["snapshot_stable"] is True)
        ck("accepts counted", report["summary"]["accepts"] == 7)
        ck("unverified accepts listed", len(report["summary"]["accepts_unverified"]) == 6)
    passed = sum(1 for _, ok in checks if ok)
    print(f"selftest: {passed}/{len(checks)} passed")
    return 0 if passed == len(checks) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--stamp", default=os.environ.get("W036_STAMP", "unspecified"))
    ap.add_argument("--out", default=None)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return _selftest()
    report = run(args.root, args.stamp, args.out)
    s = report["summary"]
    print(json.dumps({k: s[k] for k in ("records", "class_counts", "accepts", "gate_accepts",
                                        "gate_accepts_by_self_class", "short_digest_only")},
                     ensure_ascii=False, indent=1))
    print("map_sha256:", report["pins"]["map_sha256"])
    print("snapshot_stable:", report["snapshot_stable"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
