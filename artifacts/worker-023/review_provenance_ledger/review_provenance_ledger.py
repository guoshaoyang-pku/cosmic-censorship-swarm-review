#!/usr/bin/env python3
"""W023-F2B-REVIEW-PROVENANCE-01 — content-addressed review-verdict provenance ledger.

Problem (CF-31, measured by worker-036): `reviews/*.json` are mutable under fixed names.
`reviews/F2b-review-worker-072-rev29.json` was rewritten in place at 2026-09-12T01:14:54+08:00
from verdict=accept (score 4.0) to verdict=revise (score 3.0), so the controller's recorded
F2b coverage (4 accepts at 01:12:39) is not re-derivable from the paths, and the accept-bearing
bytes are not preserved anywhere under reviews/.

This tool makes that class of evidence loss impossible going forward, without writing to
`reviews/`:

  seed   : scan a corpus glob, copy every file's bytes into a content-addressed store
           (`store/<sha256>.json`, write-once), append an observation record to `ledger.jsonl`.
  check  : re-scan, classify each path against the latest observation:
           UNCHANGED / TOUCHED (same bytes, new mtime) / REWRITTEN (bytes moved) /
           RESTORED (bytes equal an older observation of the same path) / ADDED / REMOVED.
           Exits 2 (fail closed) if any REWRITTEN or REMOVED is found, 0 otherwise.
  verify : re-hash the store and confirm every store entry equals its filename digest and
           every ledger record points at bytes that are present and hash-equal.
  diff-manifest : classify the live corpus against an external pinned {path: sha256} manifest
           (e.g. worker-036's snapshot) to recover mutations inside an earlier window.
  selftest : synthetic-corpus mutation controls (rewrite/add/remove/touch/restore/tamper).

Authority: worker-level measurement only. Reads `reviews/` and writes only under this task
directory. No gate verdict, no node status, no validation_status, no canonical write.

Determinism: `check`/`diff-manifest`/`selftest` output payloads contain no wall-clock fields;
`seeded_at`/`observed_at` live only in the append-only ledger. The identity of a measurement is
the sorted (path, sha256) digest it reports.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime

TASK_ID = "W023-F2B-REVIEW-PROVENANCE-01"
VERSION = "1.0.0"


def now_iso() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def snapshot_digest(pairs) -> str:
    """Deterministic identity over a corpus sample: sha256 of `path\tsha256` lines."""
    body = "\n".join(f"{p}\t{h}" for p, h in sorted(pairs)).encode("utf-8")
    return sha256_bytes(body)


def read_json(path: str):
    try:
        with open(path, "rb") as f:
            return json.loads(f.read().decode("utf-8", "replace"))
    except Exception:
        return None


def extract_verdict_fields(path: str, data) -> dict:
    """Best-effort extraction; absent fields stay absent (never guessed)."""
    out = {}
    if not isinstance(data, dict):
        return out
    for key in ("verdict", "score", "reviewer", "actor", "target_id", "node_id", "class_id",
                "counts_as_full_schema_verdict", "reviewed_sha256", "blind", "gate"):
        if key in data:
            out[key] = data[key]
    hf = data.get("hard_failures")
    out["hard_failures"] = len(hf) if isinstance(hf, list) else hf
    return out


def scan(corpus_glob: str) -> dict:
    """{relpath: {sha256,size,mtime_ns,review,refs}} for every file matching the glob.

    `refs` = hex tokens >=12 chars found in the raw bytes, used to decide whether a
    rewritten verdict file *acknowledges* the bytes it replaces (supersession pointer)
    or silently destroys them (CF-31's worker-072 accept -> revise flip).
    """
    import glob as _glob
    import re as _re
    hex_ref = _re.compile(rb"[0-9a-fA-F]{12,64}")
    files = {}
    for path in sorted(_glob.glob(corpus_glob, recursive=True)):
        if not os.path.isfile(path):
            continue
        raw = open(path, "rb").read()
        st = os.stat(path)
        refs = {m.group(0).decode("ascii").lower() for m in hex_ref.finditer(raw)}
        files[path] = {"sha256": sha256_bytes(raw), "size": st.st_size,
                       "mtime_ns": st.st_mtime_ns,
                       "review": extract_verdict_fields(path, read_json(path)),
                       "refs": sorted(refs)}
    return files


def load_ledger(ledger_path: str) -> list:
    if not os.path.exists(ledger_path):
        return []
    rows = []
    with open(ledger_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def latest_per_path(rows: list) -> dict:
    latest = {}
    for r in rows:
        p = r["path"]
        if p not in latest or r["seq"] > latest[p]["seq"]:
            latest[p] = r
    return latest


def history_per_path(rows: list) -> dict:
    hist = {}
    for r in rows:
        hist.setdefault(r["path"], []).append(r)
    return hist


def classify(live: dict, rows: list) -> list:
    latest = latest_per_path(rows)
    hist = history_per_path(rows)
    results = []
    for path in sorted(set(live) | set(latest)):
        cur_review = live.get(path, {}).get("review", {}) or {}
        if path in live and path not in latest:
            results.append({"path": path, "state": "ADDED", "sha256": live[path]["sha256"],
                            "verdict": cur_review.get("verdict")})
        elif path in latest and path not in live:
            results.append({"path": path, "state": "REMOVED", "sha256": None,
                            "old_sha256": latest[path]["sha256"],
                            "old_verdict": latest[path].get("verdict")})
        else:
            cur, old = live[path], latest[path]
            if cur["sha256"] == old["sha256"]:
                state = "UNCHANGED" if cur["mtime_ns"] == old.get("mtime_ns") else "TOUCHED"
                results.append({"path": path, "state": state, "sha256": cur["sha256"],
                                "verdict": cur_review.get("verdict")})
            else:
                earlier = {r["sha256"] for r in hist.get(path, [])}
                if cur["sha256"] in earlier:
                    state = "RESTORED"
                else:
                    refs = set(live[path].get("refs") or [])
                    acked = old["sha256"] in refs or any(
                        old["sha256"].startswith(r) for r in refs if len(r) < 64)
                    state = "SUPERSEDED" if acked else "REWRITTEN"
                results.append({"path": path, "state": state, "sha256": cur["sha256"],
                                "old_sha256": old["sha256"],
                                "verdict": cur_review.get("verdict"),
                                "old_verdict": old.get("verdict")})
    return results


def summarize(classification: list) -> dict:
    counts = {}
    for c in classification:
        counts[c["state"]] = counts.get(c["state"], 0) + 1
    verdict_flips = [c for c in classification
                     if c["state"] in ("REWRITTEN", "RESTORED", "SUPERSEDED")
                     and c.get("verdict") is not None and c.get("old_verdict") is not None
                     and c["verdict"] != c["old_verdict"]]
    evidence_loss = [c for c in classification
                     if c["state"] == "REMOVED" and c.get("old_verdict") is not None]
    total_flips = verdict_flips + evidence_loss
    return {"counts": dict(sorted(counts.items())), "n_paths": len(classification),
            "verdict_flips": total_flips,
            "acknowledged_supersessions": [c for c in classification
                                           if c["state"] == "SUPERSEDED"],
            "fail_closed": bool(counts.get("REWRITTEN") or counts.get("REMOVED"))}


# --------------------------------------------------------------------------- commands

def cmd_seed(args) -> int:
    live = scan(args.corpus)
    os.makedirs(args.store, exist_ok=True)
    rows = load_ledger(args.ledger)
    seq0 = max([r["seq"] for r in rows], default=0)
    seq = seq0
    store_added, store_present = [], []
    recs = []
    for path in sorted(live):
        digest = live[path]["sha256"]
        target = os.path.join(args.store, digest + ".json")
        if not os.path.exists(target):
            shutil.copyfile(path, target)
            store_added.append(digest)
        else:
            store_present.append(digest)
        seq += 1
        data = read_json(path)
        rec = {"seq": seq, "observed_at": now_iso(), "path": path, "sha256": digest,
               "size": live[path]["size"], "mtime_ns": live[path]["mtime_ns"],
               "store": os.path.relpath(target, args.root)}
        rec.update(extract_verdict_fields(path, data))
        recs.append(rec)
    with open(args.ledger, "a", encoding="utf-8") as f:
        for rec in recs:
            f.write(json.dumps(rec, sort_keys=True) + "\n")
    out = {"task_id": TASK_ID, "command": "seed", "corpus": args.corpus,
           "n_scanned": len(live), "n_store_added": len(store_added),
           "n_store_already_present": len(store_present),
           "snapshot_digest": snapshot_digest((p, live[p]["sha256"]) for p in live),
           "seeded_at": now_iso(), "ledger": args.ledger, "store": args.store}
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


def cmd_check(args) -> int:
    rows = load_ledger(args.ledger)
    if not rows and not args.allow_empty:
        print(json.dumps({"error": "empty ledger; run seed first"}, indent=2))
        return 3
    live = scan(args.corpus)
    classification = classify(live, rows)
    summary = summarize(classification)
    out = {"task_id": TASK_ID, "command": "check", "corpus": args.corpus,
           "snapshot_digest": snapshot_digest((p, live[p]["sha256"]) for p in live),
           "summary": summary,
           "changed": [c for c in classification if c["state"] not in ("UNCHANGED", "TOUCHED")],
           "touched": [c["path"] for c in classification if c["state"] == "TOUCHED"]}
    print(json.dumps(out, indent=2, sort_keys=True))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, sort_keys=True)
            f.write("\n")
    return 2 if (summary["fail_closed"] and args.strict) else 0


def cmd_verify(args) -> int:
    rows = load_ledger(args.ledger)
    bad = []
    for name in sorted(os.listdir(args.store)):
        p = os.path.join(args.store, name)
        if not os.path.isfile(p):
            continue
        want = name[:-5] if name.endswith(".json") else None
        got = sha256_file(p)
        if want != got:
            bad.append({"store_entry": name, "expected_from_name": want, "measured": got})
    dangling = []
    for r in rows:
        p = os.path.join(args.root, r["store"]) if not os.path.isabs(r["store"]) else r["store"]
        if not os.path.exists(p):
            dangling.append({"seq": r["seq"], "path": r["path"], "store": r["store"]})
        elif sha256_file(p) != r["sha256"]:
            dangling.append({"seq": r["seq"], "path": r["path"], "store": r["store"],
                             "reason": "store bytes != recorded sha256"})
    out = {"task_id": TASK_ID, "command": "verify", "n_ledger_records": len(rows),
           "n_store_entries": len([n for n in os.listdir(args.store)
                                   if os.path.isfile(os.path.join(args.store, n))]),
           "store_name_mismatches": bad, "dangling_records": dangling,
           "ok": not bad and not dangling}
    print(json.dumps(out, indent=2, sort_keys=True))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, sort_keys=True)
            f.write("\n")
    return 0 if out["ok"] else 2


def cmd_diff_manifest(args) -> int:
    with open(args.manifest, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    if not isinstance(manifest, dict):
        print(json.dumps({"error": "manifest must be {path: sha256}"}, indent=2))
        return 3
    if args.key_mode == "basename":
        manifest = {os.path.basename(k): v for k, v in manifest.items()}
    live = scan(args.corpus)
    if args.key_mode == "basename":
        live = {os.path.basename(k): v for k, v in live.items()}
    rows = []
    for path in sorted(set(live) | set(manifest)):
        cur = live.get(path, {}).get("sha256")
        old = manifest.get(path)
        if cur is None:
            state = "REMOVED"
        elif old is None:
            state = "ADDED"
        elif cur == old:
            state = "UNCHANGED"
        else:
            refs = set(live.get(path, {}).get("refs") or [])
            acked = old in refs or any(old.startswith(r) for r in refs if len(r) < 64)
            state = "SUPERSEDED" if acked else "REWRITTEN"
        rows.append({"path": path, "state": state, "manifest_sha256": old, "live_sha256": cur})
    counts = {}
    for r in rows:
        counts[r["state"]] = counts.get(r["state"], 0) + 1
    out = {"task_id": TASK_ID, "command": "diff-manifest", "manifest": args.manifest,
           "manifest_file_sha256": sha256_file(args.manifest), "key_mode": args.key_mode,
           "counts": dict(sorted(counts.items())),
           "changed": [r for r in rows if r["state"] != "UNCHANGED"],
           "note": "SUPERSEDED here means only that the live bytes contain the replaced "
                   "manifest sha as a hex token; this mode has no ledger history, so it "
                   "cannot detect RESTORED, and prose supersession without the hash stays "
                   "REWRITTEN."}
    print(json.dumps(out, indent=2, sort_keys=True))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, sort_keys=True)
            f.write("\n")
    return 0


# --------------------------------------------------------------------------- selftest

def _write(p: str, obj) -> None:
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, sort_keys=True)


def cmd_selftest(args) -> int:
    checks = []

    def check(name, cond, detail=""):
        checks.append({"check": name, "pass": bool(cond), "detail": detail})

    tmp = tempfile.mkdtemp(prefix="w023_rpl_selftest_")
    corpus = os.path.join(tmp, "reviews")
    os.makedirs(corpus)
    ledger = os.path.join(tmp, "ledger.jsonl")
    store = os.path.join(tmp, "store")
    glob = os.path.join(corpus, "*.json")
    a = os.path.join(corpus, "F2b-review-a.json")
    b = os.path.join(corpus, "F2b-review-b.json")
    _write(a, {"verdict": "accept", "score": 4.0, "reviewer": "worker-900",
               "target_id": "F2b", "hard_failures": []})
    _write(b, {"verdict": "revise", "score": 3.0, "reviewer": "worker-901",
               "target_id": "F2b", "hard_failures": ["x"]})

    def run_seed():
        return cmd_seed(argparse.Namespace(corpus=glob, ledger=ledger, store=store, root=tmp))

    def run_check(strict=True, out=None):
        return cmd_check(argparse.Namespace(corpus=glob, ledger=ledger, out=out,
                                            strict=strict, allow_empty=False))

    def run_verify():
        return cmd_verify(argparse.Namespace(ledger=ledger, store=store, root=tmp, out=None))

    import contextlib
    import io

    def quiet(fn):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = fn()
        return rc, json.loads(buf.getvalue())

    rc, _ = quiet(run_seed)
    check("seed rc=0", rc == 0, f"rc={rc}")
    rc, payload = quiet(run_check)
    check("clean re-check rc=0", rc == 0, f"rc={rc}")
    check("clean re-check all UNCHANGED",
          payload["summary"]["counts"] == {"UNCHANGED": 2}, json.dumps(payload["summary"]))
    rc, payload = quiet(run_verify)
    check("verify ok after seed", rc == 0 and payload["ok"], f"rc={rc}")

    # control 1: in-place verdict flip accept -> revise at the same path
    _write(a, {"verdict": "revise", "score": 3.0, "reviewer": "worker-900",
               "target_id": "F2b", "hard_failures": ["blocking"]})
    rc, payload = quiet(run_check)
    check("rewrite detected (exit 2)", rc == 2, f"rc={rc}")
    check("rewrite classified REWRITTEN",
          [c["state"] for c in payload["changed"]] == ["REWRITTEN"],
          json.dumps(payload["changed"]))
    check("rewrite reports accept -> revise flip",
          payload["summary"]["verdict_flips"] and
          payload["summary"]["verdict_flips"][0]["old_verdict"] == "accept" and
          payload["summary"]["verdict_flips"][0]["verdict"] == "revise",
          json.dumps(payload["summary"]["verdict_flips"]))
    check("accept-bearing bytes preserved in store",
          os.path.exists(os.path.join(store, payload["changed"][0]["old_sha256"] + ".json")),
          payload["changed"][0]["old_sha256"])

    # control 2: re-seed records the new bytes; old store entry still present (write-once)
    rc, _ = quiet(run_seed)
    rc, payload = quiet(run_check)
    check("after re-seed rc=0", rc == 0, f"rc={rc}")
    check("both historical bytes retained",
          len([n for n in os.listdir(store) if n.endswith(".json")]) >= 2,
          str(sorted(os.listdir(store))))

    # control 2b: an explicit supersession pointer is acknowledged, not failed
    prior = payload["changed"][0]["sha256"] if payload["changed"] else None
    prior = prior or sha256_file(a)
    _write(a, {"verdict": "reject", "score": 2.0, "reviewer": "worker-900",
               "target_id": "F2b", "hard_failures": ["x"],
               "provenance": {"supersedes_sha256": prior,
                              "note": "fresh re-review at the same path"}})
    rc, payload = quiet(run_check)
    check("acknowledged supersession classified SUPERSEDED, exit 0",
          rc == 0 and any(c["state"] == "SUPERSEDED" for c in payload["changed"]),
          json.dumps(payload["changed"]))
    check("acknowledged supersession is not fail_closed",
          not payload["summary"]["fail_closed"], json.dumps(payload["summary"]["counts"]))
    rc, _ = quiet(run_seed)

    # control 3: restore the original bytes -> RESTORED, evidence of a rollback
    _write(a, {"verdict": "accept", "score": 4.0, "reviewer": "worker-900",
               "target_id": "F2b", "hard_failures": []})
    rc, payload = quiet(run_check)
    check("restore classified RESTORED", any(c["state"] == "RESTORED" for c in payload["changed"]),
          json.dumps(payload["changed"]))

    # control 4: touch only (mtime moves, bytes identical) is not a rewrite
    future = os.stat(b).st_mtime + 100.0
    os.utime(b, (future, future))
    rc, payload = quiet(run_check)
    check("touch is TOUCHED not REWRITTEN",
          b in payload["touched"] and
          not any(c["path"] == b and c["state"] == "REWRITTEN" for c in payload["changed"]),
          json.dumps({"touched": payload["touched"],
                      "changed_states": sorted(c["state"] for c in payload["changed"])}))

    # control 5: add + remove
    c = os.path.join(corpus, "F2b-review-c.json")
    _write(c, {"verdict": "reject", "score": 1.0, "reviewer": "worker-902", "target_id": "F2b"})
    os.remove(b)
    rc, payload = quiet(run_check)
    states = sorted(s["state"] for s in payload["changed"])
    check("add detected", "ADDED" in states, json.dumps(states))
    check("remove detected (exit 2)", rc == 2 and "REMOVED" in states, json.dumps(states))

    # control 6: store tamper is caught by verify
    victim = sorted(n for n in os.listdir(store) if n.endswith(".json"))[0]
    with open(os.path.join(store, victim), "a", encoding="utf-8") as f:
        f.write(" ")
    rc, payload = quiet(run_verify)
    check("tampered store entry caught", rc == 2 and payload["store_name_mismatches"],
          json.dumps(payload["store_name_mismatches"])[:120])

    # control 7: manifest-diff catches an in-place rewrite against an external pin
    man = os.path.join(tmp, "manifest.json")
    _write(man, {a: sha256_file(a), c: "0" * 64})
    rc, payload = quiet(lambda: cmd_diff_manifest(
        argparse.Namespace(corpus=glob, manifest=man, out=None, key_mode="path")))
    check("manifest diff classifies anchor UNCHANGED and stale pin REWRITTEN",
          rc == 0 and {r["state"] for r in payload["changed"]} == {"REWRITTEN"},
          json.dumps(payload["changed"])[:160])

    shutil.rmtree(tmp, ignore_errors=True)
    n_pass = sum(1 for c in checks if c["pass"])
    out = {"task_id": TASK_ID, "command": "selftest", "n_checks": len(checks),
           "n_pass": n_pass, "all_pass": n_pass == len(checks), "checks": checks}
    print(json.dumps(out, indent=2, sort_keys=True))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, sort_keys=True)
            f.write("\n")
    return 0 if out["all_pass"] else 2


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=os.path.dirname(os.path.abspath(__file__)))
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("seed")
    p.add_argument("--corpus", default="reviews/*.json")
    p.add_argument("--ledger", default=None)
    p.add_argument("--store", default=None)
    p.set_defaults(fn=cmd_seed)

    p = sub.add_parser("check")
    p.add_argument("--corpus", default="reviews/*.json")
    p.add_argument("--ledger", default=None)
    p.add_argument("--out", default=None)
    p.add_argument("--strict", action="store_true", default=True)
    p.add_argument("--no-strict", dest="strict", action="store_false")
    p.add_argument("--allow-empty", action="store_true")
    p.set_defaults(fn=cmd_check)

    p = sub.add_parser("verify")
    p.add_argument("--ledger", default=None)
    p.add_argument("--store", default=None)
    p.add_argument("--out", default=None)
    p.set_defaults(fn=cmd_verify)

    p = sub.add_parser("diff-manifest")
    p.add_argument("--corpus", default="reviews/*.json")
    p.add_argument("--manifest", required=True)
    p.add_argument("--key-mode", choices=("path", "basename"), default="path")
    p.add_argument("--out", default=None)
    p.set_defaults(fn=cmd_diff_manifest)

    p = sub.add_parser("selftest")
    p.add_argument("--out", default=None)
    p.set_defaults(fn=cmd_selftest)

    args = ap.parse_args(argv)
    if getattr(args, "ledger", None) is None:
        args.ledger = os.path.join(args.root, "ledger.jsonl")
    if getattr(args, "store", None) is None:
        args.store = os.path.join(args.root, "store")
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
