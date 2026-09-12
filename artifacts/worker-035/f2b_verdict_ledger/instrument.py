#!/usr/bin/env python3
"""W035-F2B-VERDICT-LEDGER-01 instrument (read-only, fail-closed).

Builds one hash-pinned ledger of F2b verdict records at the live pin and
reconciles the published F2b coverage counts (CF-31 / REC-39).

Key idea: review files are mutable under fixed names, so a count taken at one
instant is not reproducible later unless (a) each record's bytes are hashed,
and (b) in-place supersessions are reconstructed from the supersede events
(ghost records whose bytes no longer exist but whose hash+verdict are bound).

No canonical path is written. Exit: 0 ok, 2 pin drift, 3 input defect.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys

HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEXANY = re.compile(r"\b[0-9a-f]{64}\b")
ACCEPT = {"accept", "accepted", "pass"}
WITHDRAW_CUES = ("withdraw", "supersede", "void", "retract", "rescind")
FULL_CUES = ("counts_as_full_schema_verdict", "full_schema", "full-schema")


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(p):
    return sha256_bytes(open(p, "rb").read())


def walk(obj, path="$"):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield path, k, v
            yield from walk(v, path + "." + str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk(v, path + "[%d]" % i)


def declared_hashes(obj):
    found, seen = [], set()
    if not isinstance(obj, dict):
        return found
    for _, k, v in walk(obj):
        vals = []
        if isinstance(v, str):
            vals = HEXANY.findall(v)
        elif isinstance(v, dict):
            vals = [x for vv in v.values() if isinstance(vv, str) for x in HEXANY.findall(vv)]
        for h in vals:
            if h not in seen:
                seen.add(h)
                found.append({"key": k, "sha256": h})
    return found


def first_key(obj, keys):
    if not isinstance(obj, dict):
        return None
    for _, k, v in walk(obj):
        if str(k).lower() in keys and isinstance(v, (str, bool, int, float)):
            return v
    return None


def normalize_verdict(obj):
    raw = None
    for _, k, v in walk(obj):
        if str(k).lower() in ("verdict", "verdict_status", "review_verdict", "decision") and isinstance(v, str):
            raw = v.strip()
            break
    if raw is None:
        return None, None
    low = raw.lower()
    if low in ACCEPT:
        return "accept", raw
    if low.startswith("rev") or low in ("reject", "rejected", "fail", "fails", "major_revision"):
        return "revise", raw
    if low in ("inconclusive", "unknown", "pending", "undecided"):
        return "inconclusive", raw
    return "other", raw


def full_schema_flag(obj, blob_low):
    v = first_key(obj, {"counts_as_full_schema_verdict"})
    if isinstance(v, bool):
        return v, "counts_as_full_schema_verdict"
    rt = first_key(obj, {"review_type", "review_kind", "artifact_kind", "scope", "review_scope"})
    if isinstance(rt, str) and any(c in rt.lower() for c in FULL_CUES):
        return True, "review_type=" + rt
    if any(c in blob_low for c in FULL_CUES):
        return True, "text cue"
    return False, "undeclared"


def independence_declared(obj):
    v = first_key(obj, {"independent", "counts_as_independent", "reviewer_independence",
                        "counts_as_independent_second_verdict"})
    if isinstance(v, bool):
        return v, "declared"
    if isinstance(v, str):
        return v.lower() not in ("false", "no", "author", "self"), "declared=" + v
    a = first_key(obj, {"reviewer_is_author"})
    if isinstance(a, bool):
        return (not a), "reviewer_is_author"
    return None, "undeclared"


def own_lifecycle(obj):
    for _, k, v in walk(obj):
        kl = str(k).lower()
        if kl in ("superseded_by", "superseded_by_review", "void", "withdrawn", "self_superseded") and v:
            return "self-declared-superseded"
    return "live"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
    ap.add_argument("--out", required=True)
    ap.add_argument("--pin", default=None)
    args = ap.parse_args()
    root, out = os.path.abspath(args.root), os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)

    canon = os.path.join(root, "schemas", "af_scc_c0_vacuum.yaml")
    mirror = os.path.join(root, "artifacts", "formulation", "schemas", "af_scc_c0_vacuum.yaml")
    if not os.path.exists(canon):
        print("FATAL: canonical F2b missing", file=sys.stderr)
        return 3
    pin = args.pin or sha256_file(canon)
    pin_now = pin
    entry = {
        "measured_at": dt.datetime.now().astimezone().isoformat(),
        "canonical_sha256": pin_now,
        "mirror_sha256": sha256_file(mirror) if os.path.exists(mirror) else None,
        "map_sha256": sha256_file(os.path.join(root, "research_map", "research_map.json")),
        "frozen_sha256": sha256_file(os.path.join(root, "artifacts", "formulation", "FROZEN.json")),
    }

    # ---------- outbox events: supersession notices + withdrawal cues ----------
    events = []
    for f in sorted(os.listdir(os.path.join(root, "comms", "outbox"))):
        if not f.endswith(".jsonl"):
            continue
        slot = f[:-6]
        for line in open(os.path.join(root, "comms", "outbox", f), errors="replace"):
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            if not isinstance(d, dict):
                continue
            d["_slot"] = slot
            events.append(d)

    ghosts, notices, ghost_seen = [], [], set()
    for e in events:
        sp = e.get("supersedes_path")
        sh = e.get("supersedes_sha256")
        f2b_related = (isinstance(sp, str) and "f2b" in sp.lower()) or e.get("node_id") == "F2b" \
            or "AF-SCC-C0-VAC-GEN" in json.dumps(e.get("class_ids") or e.get("class_id") or "")
        if isinstance(sp, str) and isinstance(sh, str) and HEX64.match(sh) and f2b_related \
                and (sp, sh) not in ghost_seen:
            ghost_seen.add((sp, sh))
            disk = os.path.join(root, sp)
            disk_sha = sha256_file(disk) if os.path.exists(disk) else None
            ghosts.append({
                "path": sp,
                "sha256_gone": sh,
                "verdict_gone": e.get("supersedes_verdict") or e.get("prior_verdict"),
                "reviewer": e.get("reviewer") or e.get("actor"),
                "superseded_by_event": e.get("event_id"),
                "superseded_at": e.get("created_at"),
                "new_path": e.get("review_path"),
                "new_sha256": e.get("review_sha256"),
                "new_verdict": e.get("verdict"),
                "bytes_still_on_disk": disk_sha == sh if disk_sha else False,
                "note": "old bytes superseded in place" if disk_sha and disk_sha != sh else "old bytes still present",
            })
        txt = json.dumps(e).lower()
        if any(c in txt for c in WITHDRAW_CUES):
            notices.append({"event_id": e.get("event_id"), "actor": e.get("actor") or e.get("_slot"),
                            "event_type": e.get("event_type"), "created_at": e.get("created_at"),
                            "supersedes_path": sp, "supersedes_sha256": sh, "text": txt[:800]})

    # in-record supersessions (a live record may declare the prior bytes it replaced)
    for rec_path in [os.path.join(root, "reviews", n) for n in os.listdir(os.path.join(root, "reviews")) if n.endswith(".json")]:
        try:
            o = json.loads(open(rec_path, "rb").read().decode("utf-8", "replace"))
        except Exception:
            continue
        if not isinstance(o, dict):
            continue
        sp = o.get("supersedes_path") or ("reviews/" + os.path.basename(rec_path) if o.get("supersedes_sha256") else None)
        sh = o.get("supersedes_sha256")
        if isinstance(sp, str) and isinstance(sh, str) and HEX64.match(sh) and "f2b" in sp.lower() \
                and (sp, sh) not in ghost_seen and not any(gg["sha256_gone"] == sh for gg in ghosts):
            ghost_seen.add((sp, sh))
            cur = os.path.join(root, sp)
            cur_sha = sha256_file(cur) if os.path.exists(cur) else None
            ghosts.append({
                "path": sp, "sha256_gone": sh,
                "verdict_gone": o.get("supersedes_verdict") or o.get("prior_verdict"),
                "reviewer": o.get("reviewer") or o.get("actor"),
                "superseded_by_event": o.get("event_id") or o.get("review_id"),
                "superseded_at": o.get("created_at"),
                "new_path": sp, "new_sha256": cur_sha, "new_verdict": o.get("verdict"),
                "bytes_still_on_disk": cur_sha == sh if cur_sha else False,
                "note": "in-record supersession; prior bytes not preserved",
                "full_schema_inferred": o.get("counts_as_full_schema_verdict"),
            })

    # ---------- corpus ----------
    rev_dir = os.path.join(root, "reviews")
    records = []
    for name in sorted(os.listdir(rev_dir)):
        if not name.endswith(".json"):
            continue
        p = os.path.join(rev_dir, name)
        b = open(p, "rb").read()
        low = b.decode("utf-8", "replace").lower()
        if not ("f2b" in name.lower() or "f2b" in low or "af_scc_c0" in low):
            continue
        try:
            obj = json.loads(b.decode("utf-8", "replace"))
        except Exception:
            obj = None
        records.append({"file": "reviews/" + name, "bytes": b, "obj": obj,
                        "sha256": sha256_bytes(b),
                        "mtime": dt.datetime.fromtimestamp(os.path.getmtime(p)).astimezone().isoformat()})

    # author-lineage candidates: reviewer produced an F2b artifact (advisory only)
    def author_candidate(rev):
        d = os.path.join(root, "artifacts", str(rev))
        if not os.path.isdir(d):
            return False
        for dirpath, _dirs, files in os.walk(d):
            for fn in files:
                if "af_scc_c0" in fn.lower() or "f2b" in fn.lower():
                    return True
        return False

    ledger = []
    for rec in records:
        obj = rec["obj"] if isinstance(rec["obj"], dict) else {}
        blob_low = json.dumps(obj).lower()
        reviewer = first_key(obj, {"reviewer", "actor"})
        verdict, verdict_raw = normalize_verdict(obj)
        full, full_basis = full_schema_flag(obj, blob_low)
        indep, indep_basis = independence_declared(obj)
        dhs = declared_hashes(obj)
        binds = any(h["sha256"] == pin for h in dhs)
        nrefs = [n for n in notices
                 if n.get("supersedes_path") == rec["file"]
                 or (rec["file"] in n["text"] and n.get("actor") != reviewer and n.get("event_type") == "status")]
        ledger.append({
            "on_disk": True, "file": rec["file"], "sha256": rec["sha256"], "mtime": rec["mtime"],
            "reviewer": reviewer, "verdict": verdict, "verdict_raw": verdict_raw,
            "node_id": first_key(obj, {"node_id", "target_node"}), "class_id": first_key(obj, {"class_id", "class_ids"}),
            "created_at": first_key(obj, {"created_at", "reviewed_at", "measured_at"}),
            "binds_live_pin": binds, "declared_hashes": dhs,
            "offpin_hashes": sorted({h["sha256"] for h in dhs if h["sha256"] != pin}),
            "full_schema": full, "full_schema_basis": full_basis,
            "independent": indep, "independence_basis": indep_basis,
            "author_lineage_candidate": author_candidate(reviewer) if reviewer else False,
            "lifecycle": own_lifecycle(obj), "notice_refs": nrefs,
        })
    for g in ghosts:
        ledger.append({
            "on_disk": False, "file": g["path"], "sha256": g["sha256_gone"], "mtime": None,
            "reviewer": g["reviewer"], "verdict": (g["verdict_gone"] or "").lower() or None,
            "verdict_raw": g["verdict_gone"], "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN",
            "created_at": g["superseded_at"], "binds_live_pin": True, "declared_hashes": [],
            "offpin_hashes": [], "full_schema": None, "full_schema_basis": "bytes gone",
            "independent": None, "independence_basis": "bytes gone",
            "author_lineage_candidate": author_candidate(g["reviewer"]) if g["reviewer"] else False,
            "lifecycle": "superseded-by-event", "superseded_by_event": g["superseded_by_event"],
            "notice_refs": [], "ghost_detail": g,
        })

    on_disk = [r for r in ledger if r["on_disk"]]
    ondisk_bound_accepts = [r for r in on_disk if r["binds_live_pin"] and r["verdict"] == "accept"]
    ghost_bound_accepts = [r for r in ledger if not r["on_disk"] and r["verdict"] == "accept"]
    live_bound_accepts = [r for r in ondisk_bound_accepts if r["lifecycle"] == "live"]
    strict = [r for r in live_bound_accepts if r["full_schema"]]
    indep = [r for r in live_bound_accepts if r["independent"] is True]
    strict_indep = [r for r in strict if r["independent"] is True]

    nonlead_strict = [r for r in strict if not str(r["reviewer"]).startswith("astra")]
    def ghost_full(g):
        if g.get("full_schema_inferred") or g.get("full_schema"):
            return True
        cur = os.path.join(root, g["file"])
        if os.path.exists(cur):
            try:
                o = json.loads(open(cur, "rb").read().decode("utf-8", "replace"))
            except Exception:
                return False
            return o.get("supersedes_sha256") == g["sha256"] and bool(o.get("counts_as_full_schema_verdict"))
        return False

    ever_full = len(strict) + len([g for g in ghost_bound_accepts if ghost_full(g)])
    counts = {
        "R-A-on-disk-bound-accepts": len(ondisk_bound_accepts),
        "R-B-ghost-bound-accepts-reviews-dir": len([g for g in ghost_bound_accepts if g["file"].startswith("reviews/")]),
        "R-C-scan-instant-bound-accepts-A+B": len(ondisk_bound_accepts) + len([g for g in ghost_bound_accepts if g["file"].startswith("reviews/")]),
        "R-D-live-bound-accepts": len(live_bound_accepts),
        "R-E-live-bound-full-schema": len(strict),
        "R-F-live-bound-independent-declared": len(indep),
        "R-G-live-bound-full-schema-independent": len(strict_indep),
        "R-H-all-records-binding-pin": len([r for r in ledger if r["binds_live_pin"]]),
        "R-I-corpus-rows": len(ledger),
        "R-J-live-bound-full-schema-nonlead": len(nonlead_strict),
        "R-K-ever-bound-full-schema-accepts": ever_full,
    }
    members = {
        "live_bound_accepts": [r["file"] + "#" + r["sha256"][:12] + " verdict=" + str(r["verdict"]) for r in live_bound_accepts],
        "live_bound_full_schema": [r["file"] + " reviewer=" + str(r["reviewer"]) for r in strict],
        "nonlead_live_bound_full_schema": [r["file"] + " reviewer=" + str(r["reviewer"]) for r in nonlead_strict],
        "ghost_bound_accepts": [g["file"] + "#" + g["sha256"][:12] + " prior_verdict=" + str(g["verdict"]) for g in ghost_bound_accepts],
    }
    rule_table = [
        {"rule": "R-C: on-disk bound accepts + ghost bound accepts reconstructed from supersede events",
         "count": counts["R-C-scan-instant-bound-accepts-A+B"],
         "interpretation": "the '4 full accepts' instant scan before the worker-072 in-place supersession"},
        {"rule": "R-D: on-disk bound accepts whose own bytes are still live",
         "count": counts["R-D-live-bound-accepts"],
         "interpretation": "the post-supersession 'fresh 3' count"},
        {"rule": "R-E: R-D with in-record full-schema flag",
         "count": counts["R-E-live-bound-full-schema"],
         "interpretation": "strict full-schema accepts"},
        {"rule": "R-G: R-E with in-record independence declaration",
         "count": counts["R-G-live-bound-full-schema-independent"],
         "interpretation": "candidate count under the gate criterion (2 independent full-schema verdicts)"},
        {"rule": "R-H: every corpus row declaring the live pin (any verdict)",
         "count": counts["R-H-all-records-binding-pin"],
         "interpretation": "unfiltered binding population"},
        {"rule": "R-J: R-E restricted to reviewers that are not astra/lead agents",
         "count": counts["R-J-live-bound-full-schema-nonlead"],
         "interpretation": "the '2 independent full-schema accepts' claim (worker-071, worker-090)"},
        {"rule": "R-K: R-E plus ghost full-schema accepts reconstructed from supersede fields",
         "count": counts["R-K-ever-bound-full-schema-accepts"],
         "interpretation": "the controller scan '4 full accepts' at the pre-supersession instant"},
    ]

    controls = []

    def C(cid, ok, detail):
        controls.append({"id": cid, "pass": bool(ok), "detail": detail})

    w072_ghost = [g for g in ghost_bound_accepts if g["reviewer"] == "worker-072"]
    C("K1-worker-072-accept-reconstructed-as-ghost", len(w072_ghost) >= 1,
      "ghost accept rows for worker-072=%d, old_sha=%s" % (len(w072_ghost), [g["sha256"][:12] for g in w072_ghost]))
    C("K2-worker-090-live-bound-accept", any(r["reviewer"] == "worker-090" for r in ondisk_bound_accepts),
      "worker-090 bound accept rows=%d" % sum(1 for r in ondisk_bound_accepts if r["reviewer"] == "worker-090"))
    synth = {"reviewed_sha256": "0" * 64, "verdict": "accept"}
    C("K3-offpin-synthetic-not-bound", not any(h["sha256"] == pin for h in declared_hashes(synth)),
      "synthetic 0*64 binds pin=%s" % any(h["sha256"] == pin for h in declared_hashes(synth)))
    C("K4-bound-implies-pin-hash",
      all(any(h["sha256"] == pin for h in r["declared_hashes"]) for r in ondisk_bound_accepts),
      "checked=%d" % len(ondisk_bound_accepts))
    C("K5-ghost-bytes-absent",
      all(not g["ghost_detail"]["bytes_still_on_disk"] for g in w072_ghost) if w072_ghost else True,
      "worker-072 old bytes still on disk=%s" % [g["ghost_detail"]["bytes_still_on_disk"] for g in w072_ghost])
    exit_pin = sha256_file(canon)
    C("K6-pin-stable", exit_pin == pin_now, "entry=%s exit=%s" % (pin_now[:12], exit_pin[:12]))

    report = {
        "task_id": "W035-F2B-VERDICT-LEDGER-01", "actor": "worker-035",
        "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN", "class_ids": ["AF-SCC-C0-VAC-GEN"],
        "gate": "G-FORM",
        "question": ("Which F2b verdict records bind the live pin, what is each record's lifecycle state "
                     "and independence basis, and which counting rule reproduces each published F2b "
                     "coverage count (CF-31 / REC-39)?"),
        "entry": entry,
        "exit": {"measured_at": dt.datetime.now().astimezone().isoformat(), "canonical_sha256": exit_pin,
                 "map_sha256": sha256_file(os.path.join(root, "research_map", "research_map.json"))},
        "pin": pin, "counts": counts, "count_rule_table": rule_table, "members": members, "ledger": ledger,
        "controls": controls, "controls_failed": [c["id"] for c in controls if not c["pass"]],
        "falsifiers": [
            "an on-disk bound accept whose declared sha256 does not appear in its own current bytes",
            "a ghost record reconstructed from a supersede event whose old hash still exists on disk unchanged",
            "a live bound accept missing from this ledger that a same-pin re-scan finds",
            "a count-rule row not reproducible from ledger.json alone",
            "pin drift between entry and exit measurement",
        ],
        "non_claims": [
            "not a gate verdict; worker events cannot set G-FORM, node status or validation_status",
            "does not overturn any verdict; it reconciles records already on disk and reconstructs superseded ones",
            "no canonical path written; ledger binds bytes by sha256 only",
            "independence column is the in-record declaration; author_lineage_candidate is advisory, not a ruling",
            "the formulation lead's 0 accept / 7 revise census rule is not reproduced here; only rules derivable from bytes are tabled",
        ],
    }
    snap = os.path.join(out, "snapshot")
    os.makedirs(snap, exist_ok=True)
    sums = []
    for rec in records:
        obj = rec["obj"] if isinstance(rec["obj"], dict) else {}
        if any(h["sha256"] == pin for h in declared_hashes(obj)):
            dst = os.path.join(snap, rec["file"].replace("/", "__"))
            open(dst, "wb").write(rec["bytes"])
            sums.append("%s  %s" % (rec["sha256"], rec["file"]))
    json.dump(ledger, open(os.path.join(out, "ledger.json"), "w"), indent=1, sort_keys=True)
    json.dump(report, open(os.path.join(out, "report.json"), "w"), indent=1, sort_keys=True)
    for name in ("ledger.json", "report.json", "instrument.py"):
        sums.append("%s  %s" % (sha256_file(os.path.join(out, name)), name))
    open(os.path.join(out, "SHA256SUMS"), "w").write("\n".join(sorted(sums)) + "\n")
    print(json.dumps({"pin": pin, "counts": counts, "controls_failed": report["controls_failed"],
                      "ghosts": [g["path"] + "#" + g["sha256_gone"][:12] for g in ghosts]}, indent=1))
    return 0 if exit_pin == pin_now else 2


if __name__ == "__main__":
    sys.exit(main())
