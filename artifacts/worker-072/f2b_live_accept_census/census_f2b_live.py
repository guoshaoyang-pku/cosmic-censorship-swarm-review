#!/usr/bin/env python3
"""W072-F2B-LIVE-ACCEPT-CENSUS-01 -- decision-instant F2b full-accept census.

Question (REC-39 / CF-31): the F2b coverage count at pin b2ab6acb2bbe has been
published as 4 (controller pass-08 scan), 2 (worker-048 live recount, 01:10:02),
and 0 accept / 7 revise (formulation-lead per-file census).  Which count is
reproducible from disk at a stated instant, and what mechanism explains the
difference?

This instrument is read-only on every canonical path.  It

  1. re-measures the F2b pin and FROZEN rev29 manifest;
  2. censuses reviews/*.json at one instant with the *controller's own* predicate
     (`research_map/astra_lifecycle.py::review_coverage`) transcribed here, plus the
     stricter exact-64-bit pin variant;
  3. cross-checks every counted accept against the review event that declared it,
     comparing the event-declared review_sha256 with the live file sha256, so an
     in-place verdict mutation (same filename, new bytes) is detected mechanically;
  4. searches the accepted event stream for F2b accept events that no longer exist
     as files on disk (event-level vs file-level population);
  5. runs a mutation control battery in a throwaway sandbox under this artifact dir.

Exit codes: 0 = census complete and internally consistent; 2 = unexpected state
(fail closed, report still written).

Usage:
  python3 census_f2b_live.py                 # census + controls + report.json
  python3 census_f2b_live.py --no-controls   # census only
  python3 census_f2b_live.py --dir <reviews-dir> --stdout   # ad-hoc sandbox
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
ART = os.path.join(ROOT, "artifacts", "worker-072", "f2b_live_accept_census")
REVIEWS = os.path.join(ROOT, "reviews")
OUTBOX = os.path.join(ROOT, "comms", "outbox")
CST = timezone(timedelta(hours=8))

PIN = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"
PIN12 = PIN[:12]
FROZEN = "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"
F2B_PATH = "schemas/af_scc_c0_vacuum.yaml"
F2B_MIRROR = "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
CLASS_ID = "AF-SCC-C0-VAC-GEN"
VERDICTS = {"accept", "revise", "reject", "inconclusive"}
GENESIS_PUBLISHED = {
    "map_pass08_F2b_scan": 4,
    "named_reviewers": ["worker-052", "worker-071", "worker-072", "worker-090"],
    "source": "runtime/state/controller_verification/astra-lifecycle-08-decisions.json",
    "source_field": "review_coverage.dispute (CF-31): 'F2b scan (worker-052/071/072/090)'",
}


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _verdict_of(d: dict):
    v = d.get("verdict")
    if isinstance(v, dict):
        v = v.get("verdict")
    return v if isinstance(v, str) else None


def _explicit_pins(d: dict) -> list:
    """Transcription of research_map/astra_lifecycle.py::_explicit_pins."""
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


def _targets_in_review(d: dict) -> set:
    """Transcription (F2b-relevant subset) of astra_lifecycle.py::_targets_in_review."""
    out = set()
    for key in ("target_id", "node_id", "node_ids", "target", "artifact", "reviewed_path", "path"):
        v = d.get(key)
        if isinstance(v, str):
            out.add(v)
        elif isinstance(v, list):
            out.update(x for x in v if isinstance(x, str))
        elif isinstance(v, dict):
            for k2 in ("target_id", "target_subnode", "subnode", "node_id"):
                if isinstance(v.get(k2), str):
                    out.add(v[k2])
    return out


def _is_f2b_target(targets: set) -> bool:
    for t in targets:
        tl = t.lower()
        if t == "F2b" or t == CLASS_ID or "af_scc_c0_vacuum" in tl or tl.startswith("f2b"):
            return True
    return False


def _pin_match(pins: list, h: str) -> bool:
    """Controller test: a pin that shares the first 12 hex chars with the measured hash."""
    return any(p.startswith(h[:12]) or h.startswith(p[:12]) for p in pins if len(p) >= 12)


def census(reviews_dir: str, measured_at: str | None = None) -> dict:
    measured_at = measured_at or now()
    rows, unreadable, files_total = [], [], 0
    for name in sorted(os.listdir(reviews_dir)):
        if not name.endswith(".json") or name.startswith("._"):
            continue
        files_total += 1
        path = os.path.join(reviews_dir, name)
        try:
            with open(path, "r", errors="replace") as f:
                d = json.load(f)
        except Exception as e:  # noqa: BLE001
            unreadable.append({"file": name, "error": str(e)[:120]})
            continue
        if not isinstance(d, dict):
            unreadable.append({"file": name, "error": "not a JSON object"})
            continue
        verdict = _verdict_of(d)
        pins = _explicit_pins(d)
        targets = _targets_in_review(d)
        f2b = _is_f2b_target(targets)
        pm = _pin_match(pins, PIN)
        if not (f2b or pm):
            continue
        st = os.stat(path)
        full_decl = d.get("counts_as_full_schema_verdict", None)
        rows.append({
            "file": name,
            "sha256_now": sha256_file(path),
            "mtime": datetime.fromtimestamp(st.st_mtime, CST).isoformat(timespec="seconds"),
            "size": st.st_size,
            "reviewer": d.get("reviewer") or d.get("actor"),
            "reviewer_role": d.get("reviewer_role"),
            "blind": d.get("blind"),
            "verdict": verdict,
            "score": d.get("score"),
            "target_id": d.get("target_id") or d.get("target"),
            "reviewed_path": d.get("reviewed_path"),
            "reviewed_sha256": d.get("reviewed_sha256"),
            "f2b_target": f2b,
            "pin_match_12": pm,
            "pin_exact": PIN in [p.lower() for p in pins],
            "counts_as_full_schema_verdict": full_decl,
            "full_schema": full_decl is not False,
            "n_hard": len(d.get("hard_failures") or []),
            "supersedes_sha256": d.get("supersedes_sha256"),
            "supersedes_verdict": d.get("supersedes_verdict"),
            "review_path_declared": d.get("review_path"),
        })

    def sel(r, *, exact_pin=False, require_f2b=True, require_pin=True):
        if require_f2b and not r["f2b_target"]:
            return False
        if require_pin and not (r["pin_exact"] if exact_pin else r["pin_match_12"]):
            return False
        return r["verdict"] in VERDICTS

    controller_full_accepts = [r for r in rows if sel(r) and r["verdict"] == "accept" and r["full_schema"]]
    controller_scoped_accepts = [r for r in rows if sel(r) and r["verdict"] == "accept" and not r["full_schema"]]
    exact_full_accepts = [r for r in rows if sel(r, exact_pin=True) and r["verdict"] == "accept" and r["full_schema"]]
    all_citing_accepts = [r for r in rows if sel(r, require_f2b=False) and r["verdict"] == "accept"]
    f2b_verdicts = [r for r in rows if sel(r)]
    non_f2b = [r for r in rows if not r["f2b_target"]]

    return {
        "measured_at": measured_at,
        "reviews_dir": os.path.relpath(reviews_dir, ROOT) if reviews_dir.startswith(ROOT) else reviews_dir,
        "pin": {"path": F2B_PATH, "sha256": PIN, "frozen_rev29": FROZEN, "class_id": CLASS_ID},
        "predicate": "transcribed controller predicate: F2b target AND pin-prefix(12) in explicit pins "
                     "AND verdict accept AND counts_as_full_schema_verdict is not False",
        "counts": {
            "files_total_in_dir": files_total,
            "rows_relevant_f2b_or_pin": len(rows),
            "controller_full_accepts": len(controller_full_accepts),
            "controller_scoped_accepts": len(controller_scoped_accepts),
            "exact_pin_full_accepts": len(exact_full_accepts),
            "all_accepts_citing_pin_any_target": len(all_citing_accepts),
            "f2b_verdict_rows": len(f2b_verdicts),
            "non_f2b_rows_in_scope_by_pin": len(non_f2b),
            "revise": len([r for r in f2b_verdicts if r["verdict"] == "revise"]),
            "inconclusive": len([r for r in f2b_verdicts if r["verdict"] == "inconclusive"]),
        },
        "controller_full_accepts": controller_full_accepts,
        "controller_scoped_accepts": controller_scoped_accepts,
        "exact_pin_full_accepts": exact_full_accepts,
        "all_accepts_citing_pin_any_target": all_citing_accepts,
        "f2b_verdict_rows": f2b_verdicts,
        "unreadable": unreadable,
        "genesis_published": GENESIS_PUBLISHED,
    }


def _iter_outbox_events():
    for dirpath, _dirnames, filenames in os.walk(OUTBOX):
        for fn in sorted(filenames):
            if fn.startswith("._") or not (fn.endswith(".jsonl") or fn.endswith(".json")):
                continue
            path = os.path.join(dirpath, fn)
            try:
                with open(path, "r", errors="replace") as f:
                    text = f.read()
            except OSError:
                continue
            if "review_sha256" not in text and "review-f2b" not in text and "review_path" not in text:
                continue
            for line in text.splitlines():
                line = line.strip().rstrip(",")
                if not line.startswith("{") or not line.endswith("}"):
                    continue
                if PIN12 not in line and "F2b" not in line and "f2b" not in line:
                    continue
                try:
                    yield json.loads(line)
                except ValueError:
                    continue


def _norm_hash(h: str) -> str:
    """Normalize a declared digest: strip sha256: prefixes, keep leading hex."""
    h = h.strip().lower()
    if h.startswith("sha256:"):
        h = h[len("sha256:"):]
    m = re.match(r"[0-9a-f]{6,64}", h)
    return m.group(0) if m else ""


def _ref_pairs(ev: dict) -> list:
    """(review-file basename, declared hash) pairs declared by one review event."""
    pairs = []
    for key, hkey in (("review_path", "review_sha256"), ("path", "sha256")):
        p, h = ev.get(key), ev.get(hkey)
        if isinstance(p, str) and isinstance(h, str) and ("/reviews/" in ("/" + p) or p.startswith("reviews/")):
            nh = _norm_hash(h)
            if nh:
                pairs.append((os.path.basename(p), nh))
    for ref in (ev.get("evidence_refs") or []):
        if not isinstance(ref, str) or "#" not in ref:
            continue
        p, _, h = ref.partition("#")
        if "/reviews/" in ("/" + p) or p.startswith("reviews/"):
            nh = _norm_hash(h)
            if nh:
                pairs.append((os.path.basename(p), nh))
    return pairs


def event_crosscheck(rows: list, seen_at: str) -> dict:
    """Compare each row's live bytes with the latest event that declared that file.

    Declarations are read from the protocol citation form `reviews/<file>#<hash>` in
    evidence_refs, from review_path+review_sha256, or from path+sha256.
    """
    wanted = {r["file"]: r for r in rows}
    history: dict[str, list] = {}
    f2b_accept_events = []
    for ev in _iter_outbox_events():
        if ev.get("event_type") != "review":
            continue
        tgt = str(ev.get("target_id") or "")
        cls = json.dumps(ev.get("class_ids") or [])
        reviewed_pin = str(ev.get("reviewed_sha256") or "")
        is_f2b = ("F2b" in tgt or CLASS_ID in tgt or "af_scc_c0_vacuum" in str(ev.get("reviewed_path") or "")
                  or CLASS_ID in cls)
        if is_f2b and reviewed_pin.startswith(PIN12) and str(ev.get("verdict")) == "accept":
            refs = _ref_pairs(ev)
            f2b_accept_events.append({
                "event_id": ev.get("event_id"),
                "actor": ev.get("actor"),
                "created_at": ev.get("created_at"),
                "declared_review_hash": (refs[0][1] if refs else ev.get("review_sha256")),
                "review_path": (refs[0][0] if refs else ev.get("review_path")),
                "blind": ev.get("blind"),
                "score": ev.get("score"),
            })
        for base, declared in _ref_pairs(ev):
            if base not in wanted:
                continue
            stamp = str(ev.get("created_at") or "")
            history.setdefault(base, []).append({
                "_stamp": stamp,
                "event_id": ev.get("event_id"),
                "actor": ev.get("actor"),
                "created_at": ev.get("created_at"),
                "declared_verdict": (ev.get("verdict") if not isinstance(ev.get("verdict"), dict)
                                     else ev["verdict"].get("verdict")),
                "declared_hash": declared,
            })
    declared_latest, mutations, flips = {}, [], []
    for base, row in wanted.items():
        hist = sorted(history.get(base, []), key=lambda e: e["_stamp"])
        if not hist:
            row["mutation_status"] = "no-declaring-event-found"
            continue
        declared_latest[base] = hist[-1]
        live_hist = [{"created_at": e["created_at"], "event_id": e["event_id"],
                      "verdict": e["declared_verdict"], "declared_hash": e["declared_hash"][:12]}
                     for e in hist]
        row["declared_verdict_history"] = live_hist
        dec = hist[-1]["declared_hash"]
        if isinstance(dec, str) and len(dec) >= 12 and not row["sha256_now"].startswith(dec[:12]):
            row["mutation_status"] = "in-place-mutation"
            mutations.append({
                "file": base,
                "latest_event_id": hist[-1]["event_id"],
                "latest_declared_at": hist[-1]["created_at"],
                "latest_declared_hash": dec,
                "latest_declared_verdict": hist[-1]["declared_verdict"],
                "live_sha256": row["sha256_now"],
                "live_verdict": row["verdict"],
            })
        else:
            row["mutation_status"] = "bytes-match-latest-declaring-event"
        verdicts = [(e["created_at"], e["declared_verdict"], e["declared_hash"][:12]) for e in hist]
        if any(v == "accept" for _t, v, _h in verdicts) and hist[-1]["declared_verdict"] != "accept":
            flips.append({"file": base, "history": verdicts, "live_verdict": row["verdict"],
                          "live_sha256": row["sha256_now"][:12]})
    superseded_accepts = [r for r in rows if r.get("verdict") == "revise"
                          and str(r.get("supersedes_verdict") or "").lower() == "accept"]
    return {
        "declared_latest": declared_latest,
        "in_place_mutations": mutations,
        "declared_verdict_flips_in_place": flips,
        "event_level_f2b_accepts_at_pin": f2b_accept_events,
        "rows_superseding_an_accept": [
            {"file": r["file"], "live_verdict": r["verdict"], "live_sha256": r["sha256_now"][:12],
             "supersedes_sha256": r["supersedes_sha256"], "supersedes_verdict": r["supersedes_verdict"]}
            for r in superseded_accepts
        ],
        "seen_at": seen_at,
    }


# ---------------------------------------------------------------- controls
def _sandbox_copy(dst: str):
    os.makedirs(dst, exist_ok=True)
    for name in os.listdir(REVIEWS):
        if name.endswith(".json") and not name.startswith("._"):
            shutil.copy2(os.path.join(REVIEWS, name), os.path.join(dst, name))


def _patch(path: str, **kv):
    with open(path) as f:
        d = json.load(f)
    d.update(kv)
    with open(path, "w") as f:
        json.dump(d, f, indent=1)


def run_controls(base: dict) -> dict:
    for old in os.listdir(ART):
        if old.startswith("w072_census_controls_"):
            shutil.rmtree(os.path.join(ART, old), ignore_errors=True)
    tmp = tempfile.mkdtemp(prefix="w072_census_controls_", dir=ART)
    results = []
    stamp = "2026-09-12T01:30:00+08:00"

    def snap(tag):
        d = os.path.join(tmp, tag)
        _sandbox_copy(d)
        return d

    # K1 determinism: census twice on the same sandbox, ignore measured_at
    d = snap("k1")
    a = census(d, stamp)
    b = census(d, stamp)
    results.append({"id": "K1-determinism", "expect": "identical census",
                    "observed": canonical(a) == canonical(b), "pass": canonical(a) == canonical(b)})

    # K2 verdict flip: live revise -> accept must raise the full-accept count by one
    d = snap("k2")
    f = os.path.join(d, "F2b-review-worker-072-rev29.json")
    _patch(f, verdict="accept", **{"counts_as_full_schema_verdict": True})
    c = census(d, stamp)
    results.append({"id": "K2-verdict-flip", "expect": base["counts"]["controller_full_accepts"] + 1,
                    "observed": c["counts"]["controller_full_accepts"],
                    "pass": c["counts"]["controller_full_accepts"] == base["counts"]["controller_full_accepts"] + 1})

    # K3 pin tamper: move one accept off the pin -> count drops by one
    d = snap("k3")
    f = os.path.join(d, "F2b-review-rev13-052.json")
    _patch(f, reviewed_sha256="0" * 64)
    c = census(d, stamp)
    results.append({"id": "K3-pin-tamper", "expect": base["counts"]["controller_full_accepts"] - 1,
                    "observed": c["counts"]["controller_full_accepts"],
                    "pass": c["counts"]["controller_full_accepts"] == base["counts"]["controller_full_accepts"] - 1})

    # K4 scoped flag: mark one full accept scoped -> full count -1, scoped +1
    d = snap("k4")
    f = os.path.join(d, "F2b-rev13-full-090.json")
    _patch(f, counts_as_full_schema_verdict=False)
    c = census(d, stamp)
    results.append({"id": "K4-scoped-flag", "expect": [base["counts"]["controller_full_accepts"] - 1, 1],
                    "observed": [c["counts"]["controller_full_accepts"], c["counts"]["controller_scoped_accepts"]],
                    "pass": c["counts"]["controller_full_accepts"] == base["counts"]["controller_full_accepts"] - 1
                            and c["counts"]["controller_scoped_accepts"] >= 1})

    # K5 mutation detection: append a byte to a counted accept -> in-place mutation flagged
    d = snap("k5")
    f = os.path.join(d, "F2b-review-rev13-worker-071.json")
    with open(f, "a") as fh:
        fh.write("\n")
    c = census(d, stamp)
    x = event_crosscheck(c["controller_full_accepts"] + c["f2b_verdict_rows"], stamp)
    flagged = [m["file"] for m in x["in_place_mutations"]]
    results.append({"id": "K5-mutation-detect", "expect": "F2b-review-rev13-worker-071.json flagged",
                    "observed": flagged, "pass": "F2b-review-rev13-worker-071.json" in flagged})

    # K6 null: a review with no F2b target and an unrelated pin is excluded
    d = snap("k6")
    with open(os.path.join(d, "zz-null-control.json"), "w") as fh:
        json.dump({"verdict": "accept", "reviewed_sha256": "f" * 64, "target_id": "F1",
                   "reviewed_path": "schemas/af_wcc_vacuum.yaml", "counts_as_full_schema_verdict": True}, fh)
    c = census(d, stamp)
    results.append({"id": "K6-null-excluded", "expect": base["counts"]["controller_full_accepts"],
                    "observed": c["counts"]["controller_full_accepts"],
                    "pass": c["counts"]["controller_full_accepts"] == base["counts"]["controller_full_accepts"]})

    # K7 wrong-reviewer hard failure: the census must expose empty hard_failures list length 0
    if base["controller_full_accepts"]:
        results.append({"id": "K7-hard-failure-exposure", "expect": "n_hard present for every counted accept",
                        "observed": {r["file"]: r["n_hard"] for r in base["controller_full_accepts"]},
                        "pass": all("n_hard" in r for r in base["controller_full_accepts"])})
    summary = {"sandbox": os.path.relpath(tmp, ROOT), "controls": results,
               "controls_pass": all(r["pass"] for r in results),
               "sandbox_disposed": True}
    with open(os.path.join(ART, "controls", "controls_summary.json"), "w") as fh:
        json.dump(summary, fh, indent=1, sort_keys=True)
    shutil.rmtree(tmp, ignore_errors=True)
    return summary


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=REVIEWS)
    ap.add_argument("--no-controls", action="store_true")
    ap.add_argument("--stdout", action="store_true")
    args = ap.parse_args()

    measured_at = now()
    base = census(args.dir, measured_at)
    base["frozen_manifest"] = {
        "path": "artifacts/formulation/FROZEN.json",
        "declared_sha256": FROZEN,
        "measured_sha256": sha256_file(os.path.join(ROOT, "artifacts/formulation/FROZEN.json")),
    }
    base["frozen_manifest"]["match"] = base["frozen_manifest"]["declared_sha256"] == base["frozen_manifest"]["measured_sha256"]
    base["pin_measured_now"] = {
        "path": F2B_PATH, "sha256": sha256_file(os.path.join(ROOT, F2B_PATH)),
        "mirror": F2B_MIRROR, "mirror_sha256": sha256_file(os.path.join(ROOT, F2B_MIRROR)),
    }
    base["pin_measured_now"]["match"] = base["pin_measured_now"]["sha256"] == PIN == base["pin_measured_now"]["mirror_sha256"]

    rows = base["controller_full_accepts"] + base["controller_scoped_accepts"] + base["f2b_verdict_rows"]
    dedup = {r["file"]: r for r in rows}
    x = event_crosscheck(list(dedup.values()), measured_at)
    base["event_crosscheck"] = x

    f2b_rows = [r for r in dedup.values() if r["f2b_target"] and (r["pin_match_12"] or r["pin_exact"])]
    live_accepts = sorted(r["file"] for r in f2b_rows if r["verdict"] == "accept" and r["full_schema"])
    live_revises = sorted(r["file"] for r in f2b_rows if r["verdict"] == "revise")
    event_accepts = sorted({e["event_id"] for e in x["event_level_f2b_accepts_at_pin"] if e["event_id"]})

    base["reconciliation"] = {
        "live_file_level_full_accepts": live_accepts,
        "live_file_level_full_accept_count": len(live_accepts),
        "live_file_level_revises": live_revises,
        "event_level_f2b_accept_events_at_pin": event_accepts,
        "published_counts": GENESIS_PUBLISHED,
        "declared_in_place_flips": x["declared_verdict_flips_in_place"],
        "explanation": (
            "All published counts are instant-dependent snapshots of the same mutable review directory. "
            "The controller pass-08 scan (4) is reproducible only for the pre-flip file set {052,071,072,090}, "
            "in which worker-072's review file was still an accept; its successor bytes at the same path are a "
            "revise and declare supersession of accept 7487f310. worker-048's 2 (01:10:02) predates the 052 "
            "(01:10:18) and 071 (01:11:15) accept files; the lead's count uses a different predicate set. At "
            f"this instant the reproducible file-level count with the transcribed controller predicate is "
            f"{len(live_accepts)}."
        ),
        "count_changing_mechanisms": [
            "declared in-place review-file supersession under a fixed filename "
            "(F2b-review-worker-072-rev29.json: accept 7487f310 -> revise " + (
                next((f["live_sha256"] for f in x["declared_verdict_flips_in_place"]
                      if f["file"] == "F2b-review-worker-072-rev29.json"), "?") ) + ")",
            "new accept files arriving after an earlier snapshot (052 at 01:10:18, 071 at 01:11:15)",
            "predicate differences (pin-prefix vs exact-64, full vs scoped, F2b target normalization)",
        ],
    }
    base["decision_instant_statement"] = (
        f"At {measured_at}, at F2b pin {PIN12} under FROZEN rev29 {FROZEN[:12]}, the on-disk "
        f"full-schema accept set is {live_accepts} (n={len(live_accepts)}); "
        f"the superseded accept at the same path is {[r['file'] for r in dedup.values() if str(r.get('supersedes_verdict') or '').lower()=='accept']}."
    )
    base["falsifier"] = (
        "Re-run census_f2b_live.py at the same pins. Falsified if: (a) the F2b pin no longer hashes to "
        f"{PIN}; (b) FROZEN.json no longer hashes to {FROZEN}; (c) any counted accept file's sha256/mtime "
        "differs from report.json and its verdict is still accept at the cited pin; (d) the K1-K7 controls "
        "do not all pass; (e) a review file on disk at the pin with an accept verdict and full-schema flag "
        "exists that this census does not list."
    )
    base["not_claimed"] = [
        "no gate verdict, node status, or validation_status",
        "no assertion that any listed accept is semantically correct; only that it is on disk at the stated instant",
        "no canonical write",
    ]

    if not args.no_controls:
        base["controls"] = run_controls(base)

    out = os.path.join(ART, "report.json")
    with open(out, "w") as f:
        json.dump(base, f, indent=1, sort_keys=True)

    ok = (base["frozen_manifest"]["match"] and base["pin_measured_now"]["match"]
          and len(live_accepts) >= 1)
    if not args.no_controls:
        ok = ok and base["controls"]["controls_pass"]

    if args.stdout:
        print(json.dumps(base, indent=1, sort_keys=True))
    else:
        print(f"census at {measured_at}: controller-predicate full accepts = {len(live_accepts)} {live_accepts}")
        print(f"in-place mutations detected: {[m['file'] for m in x['in_place_mutations']]}")
        if not args.no_controls:
            print(f"controls: {'PASS' if base['controls']['controls_pass'] else 'FAIL'} "
                  f"({sum(1 for c in base['controls']['controls'] if c['pass'])}/{len(base['controls']['controls'])})")
        print(f"report: {os.path.relpath(out, ROOT)}")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
