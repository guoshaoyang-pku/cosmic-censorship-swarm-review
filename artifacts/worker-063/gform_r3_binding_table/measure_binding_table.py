#!/usr/bin/env python3
"""worker-063 / G-FORM r3 per-file binding table (REC-39 support, read-only).

Purpose
-------
REC-39 requires `astra-life05-verify-gform-r3` to publish, for every verdict at the
measured FROZEN rev29 pins: filename / reviewer / verdict / reviewed_sha256 /
verdict mtime / full-schema flag / independence basis, and to state which of the
disputed coverage counts is correct and why the other is wrong (CF-31).

This script independently measures that table from disk. It writes nothing to any
canonical artifact and makes no gate verdict. All counts are criterion-dependent
and reported as such.

Falsifiers tested (declared in reviews/G-FORM-final-verify-r3.json):
  F1  a cited sha256 in r3 that does not equal the measured canonical sha256
  F2  a counted accept whose reviewer authored the artifact
  F3  a counted accept silent on a named carrier (recorded dispositions + probe)
  F4  any schema write during the round that moves a pin
"""
import glob
import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
TZ = timezone(timedelta(hours=8))
HEX64 = re.compile(r"\b[0-9a-f]{64}\b")
HEXPFX = re.compile(r"\b[0-9a-f]{12,63}\b")

SCHEMAS = {
    "F1": ("AF-WCC-VAC-GEN", "schemas/af_wcc_vacuum.yaml"),
    "F2a": ("AF-SCC-C2-VAC-GEN", "schemas/af_scc_c2_vacuum.yaml"),
    "F2b": ("AF-SCC-C0-VAC-GEN", "schemas/af_scc_c0_vacuum.yaml"),
}
CARRIER_KEYWORDS = {
    "F2b": ["must_not_conflate", "strictly larger", "containment", "implication_ledger", "E_C2"],
    "F2a": ["extension_predicate", "extension_topology", "iota_regularity", "manifold"],
    "F1": ["class_identity_variants", "relation", "falsifier_tests", "provenance"],
}
# recorded third-party artifacts that classify counted accepts as silent
RECORDED_DISPOSITIONS = [
    "artifacts/worker-066/f2b_accept_disposition/report.json",
    "artifacts/worker-066/f2b_accept_disposition/addendum_report.json",
    "artifacts/worker-097/f2b_accept_sufficiency/report.json",
]
# verbatim pinned copies made by worker-066 (mutation check for F2b accepts)
PINNED_F2B_COPIES = {
    "reviews/F2b-rev13-full-090.json": "artifacts/worker-066/f2b_accept_disposition/pinned/reviews__F2b-rev13-full-090.json",
    "reviews/F2b-review-rev13-worker-071.json": "artifacts/worker-066/f2b_accept_disposition/pinned/reviews__F2b-review-rev13-worker-071.json",
    "reviews/F2b-review-rev13-052.json": "artifacts/worker-066/f2b_accept_disposition/pinned/reviews__F2b-review-rev13-052.json",
}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def iso(ts):
    return datetime.fromtimestamp(ts, TZ).isoformat()


def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def first_sha(d, *keys):
    for k in keys:
        v = d.get(k)
        if isinstance(v, str) and HEX64.fullmatch(v):
            return v
    for k in ("frozen_manifest", "target", "pin"):
        v = d.get(k)
        if isinstance(v, dict):
            for kk in ("sha256", "declared_sha256", "measured_sha256", "reviewed_sha256"):
                if isinstance(v.get(kk), str) and HEX64.fullmatch(v[kk]):
                    return v[kk]
    return None


def main():
    out = {
        "schema": "worker-063/gform-r3-binding-table/v2",
        "actor": "worker-063",
        "authority": "advisory read-only measurement; no gate verdict, no canonical write, no status transition",
        "measured_at": datetime.now(TZ).isoformat(),
        "task": "REC-39 support: per-file binding table + criterion-dependent counts + CF-31 adjudication input",
    }

    # ---- pins: FROZEN rev29 declared vs live measured -------------------------
    frozen_path = os.path.join(ROOT, "artifacts/formulation/FROZEN.json")
    frozen = load_json(frozen_path) or {}
    out["frozen"] = {"path": "artifacts/formulation/FROZEN.json",
                     "revision": frozen.get("revision"),
                     "static_sha256": sha256_file(frozen_path)}
    pins = {}
    for cls, (klass, path) in SCHEMAS.items():
        live = sha256_file(os.path.join(ROOT, path))
        declared = ((frozen.get("files") or {}).get(path) or {}).get("sha256")
        pins[cls] = {"class_id": klass, "path": path, "pin": live,
                     "frozen_declared": declared, "pin_matches_frozen": declared == live}
    out["pins"] = pins

    # ---- pin authors: only artifact events that emit the canonical schema -----
    authors = {c: set() for c in SCHEMAS}
    stream_reviews = {}  # event_id -> {actor, created_at, reviewed sha if present}
    events_path = os.path.join(ROOT, "research_map/events.jsonl")
    n_events = 0
    if os.path.exists(events_path):
        with open(events_path, "r", encoding="utf-8") as fh:
            for line in fh:
                n_events += 1
                try:
                    ev = json.loads(line)
                except Exception:
                    continue
                etype = ev.get("event_type")
                if etype == "artifact":
                    # authorship = the event's OWN declared artifact path is the schema
                    # (canonical or mirror); pin mention alone is not authorship.
                    ap = ev.get("artifact") or ev.get("path") or ev.get("artifact_path") or []
                    paths = ap if isinstance(ap, list) else [ap]
                    norm = {os.path.normpath(str(x)).lstrip("./") for x in paths if x}
                    for cls, p in pins.items():
                        if p["path"] in norm or any(n.endswith("/" + p["path"]) for n in norm):
                            authors[cls].add(ev.get("actor"))
                elif etype == "review" and ev.get("event_id"):
                    stream_reviews[ev["event_id"]] = {
                        "actor": ev.get("actor"), "created_at": ev.get("created_at"),
                    }
    out["pin_author_actors"] = {c: sorted(a) for c, a in authors.items()}
    out["stream_events_scanned"] = n_events

    # ---- corpus: every reviews/*.json verdict file ---------------------------
    corpus = []
    for f in sorted(glob.glob(os.path.join(ROOT, "reviews/*.json"))):
        rel = os.path.relpath(f, ROOT)
        corpus.append((rel, sha256_file(f), os.path.getmtime(f)))
    corpus_digest = hashlib.sha256("".join(f"{r}:{h}\n" for r, h, _ in corpus).encode()).hexdigest()
    out["corpus"] = {"scope": "reviews/*.json", "n_files": len(corpus),
                     "digest": corpus_digest}

    rows_by_class = {c: [] for c in SCHEMAS}
    for rel, fsha, mtime in corpus:
        d = load_json(os.path.join(ROOT, rel))
        if not isinstance(d, dict):
            continue
        verdict = d.get("verdict")
        if not isinstance(verdict, str):
            continue
        reviewed = first_sha(d, "reviewed_sha256", "target_sha256", "artifact_sha256",
                             "reviewed_target_sha256", "spec_sha256")
        if not reviewed:
            continue
        for cls, p in pins.items():
            if reviewed != p["pin"]:
                continue
            hf = d.get("hard_failures")
            reviewer = d.get("reviewer") or d.get("actor")
            flag = d.get("counts_as_full_schema_verdict")
            flag_state = "true" if flag is True else ("false" if flag is False else "ABSENT")
            row = {
                "file": rel, "file_sha256": fsha,
                "file_bytes": os.path.getsize(os.path.join(ROOT, rel)),
                "mtime": iso(mtime),
                "reviewer": reviewer, "verdict": verdict, "score": d.get("score"),
                "reviewed_sha256": reviewed,
                "full_schema_flag": flag_state,
                "independent_flag": d.get("counts_as_independent"),
                "n_hard_failures": len(hf) if isinstance(hf, list) else None,
                "created_at": d.get("created_at"),
                "file_event_id": d.get("event_id"),
                "independence_basis": ("non-author" if reviewer not in authors[cls] else "AUTHOR"),
            }
            rows_by_class[cls].append(row)
    for cls in rows_by_class:
        rows_by_class[cls].sort(key=lambda r: (r["created_at"] or r["mtime"], r["file"]))
    out["rows_by_class"] = rows_by_class

    # ---- criterion-dependent counts ------------------------------------------
    def crit_strict(r):   # declared full-schema accept, non-author, no hard failures
        return (r["verdict"] == "accept" and r["full_schema_flag"] == "true"
                and r["independence_basis"] == "non-author" and r["n_hard_failures"] in (0, None))

    def crit_loose(r):    # any accept at the pin, non-author, no hard failures
        return (r["verdict"] == "accept" and r["independence_basis"] == "non-author"
                and r["n_hard_failures"] in (0, None))

    counts = {}
    for cls, rows in rows_by_class.items():
        counts[cls] = {
            "rows_at_pin": len(rows),
            "strict_declared_full_accept": sorted(r["reviewer"] for r in rows if crit_strict(r)),
            "loose_accept_at_pin": sorted(r["reviewer"] for r in rows if crit_loose(r)),
            "accept_flag_absent": [{"file": r["file"], "reviewer": r["reviewer"],
                                    "n_hard": r["n_hard_failures"]}
                                   for r in rows if r["verdict"] == "accept" and r["full_schema_flag"] == "ABSENT"],
            "accept_flag_false": [{"file": r["file"], "reviewer": r["reviewer"]}
                                  for r in rows if r["verdict"] == "accept" and r["full_schema_flag"] == "false"],
            "revise_at_pin": sum(1 for r in rows if r["verdict"] == "revise"),
        }
    out["criterion_counts"] = counts

    # ---- r3 comparison --------------------------------------------------------
    r3_path = os.path.join(ROOT, "reviews/G-FORM-final-verify-r3.json")
    r3_text = open(r3_path, encoding="utf-8").read()
    r3_sha = sha256_file(r3_path)
    r3 = json.loads(r3_text)
    r3_rows, resolution = {}, []
    for entry in r3.get("coverage_table", []):
        cls = entry.get("class")
        if cls not in SCHEMAS:
            continue
        listed = []
        for a in entry.get("non_author_accepts_full", []):
            eid = a.get("event_id")
            disk = [r for r in rows_by_class[cls] if r["reviewer"] == a.get("reviewer")]
            # exact match on the file's own declared id, or on its review_id
            exact = [r for r in disk if r["file_event_id"] == eid]
            if not exact:
                exact = [r for r in disk
                         if (load_json(os.path.join(ROOT, r["file"])) or {}).get("review_id") == eid]
            chosen = (exact or disk or [None])[0]
            if exact:
                resolves = "exact_file_id"
            elif chosen is not None:
                resolves = "stream_id_only" if eid in stream_reviews else "reviewer_only"
            else:
                resolves = "none"
            rec = {
                "reviewer": a.get("reviewer"), "r3_event_id": eid,
                "r3_created_at": a.get("created_at"), "r3_full_schema": a.get("full_schema"),
                "disk_file": chosen and chosen["file"],
                "disk_file_event_id": chosen and chosen["file_event_id"],
                "disk_reviewed_sha256": chosen and chosen["reviewed_sha256"],
                "disk_full_schema_flag": chosen and chosen["full_schema_flag"],
                "disk_verdict": chosen and chosen["verdict"],
                "disk_file_sha256": chosen and chosen["file_sha256"],
                "disk_mtime": chosen and chosen["mtime"],
                "resolves": resolves,
                "in_stream": eid in stream_reviews,
                "r3_fields_present": {
                    "filename": bool(a.get("file") or a.get("filename")),
                    "reviewed_sha256": bool(a.get("reviewed_sha256")),
                    "independence_basis": bool(a.get("independence_basis")),
                    "verdict_mtime": bool(a.get("created_at")),
                },
            }
            listed.append(rec)
            resolution.append({"class": cls, **{k: rec[k] for k in
                             ("reviewer", "r3_event_id", "disk_file", "resolves", "in_stream")}})
        r3_rows[cls] = {"n_listed": len(listed), "adjudicated_verdict": entry.get("adjudicated_verdict"),
                        "r3_claim_of_full_accepts": len(entry.get("non_author_accepts_full", [])),
                        "rows": listed}
    # omissions / overcounts versus strict and loose criteria
    r3_claim = {cls: {r["reviewer"] for r in info["rows"]} for cls, info in r3_rows.items()}
    r3_vs_disk = {}
    for cls, rows in rows_by_class.items():
        strict = {r["reviewer"] for r in rows if crit_strict(r)}
        loose = {r["reviewer"] for r in rows if crit_loose(r)}
        claim = r3_claim.get(cls, set())
        r3_vs_disk[cls] = {
            "r3_claimed": sorted(claim),
            "disk_strict": sorted(strict),
            "disk_loose": sorted(loose),
            "claimed_but_not_strict": sorted(claim - strict),
            "claimed_but_not_loose": sorted(claim - loose),
            "disk_strict_not_claimed": sorted(strict - claim),
            "disk_loose_not_claimed": sorted(loose - claim),
        }
    out["r3"] = {
        "path": "reviews/G-FORM-final-verify-r3.json", "sha256": r3_sha,
        "measured_at_field": r3.get("measured_at"),
        "coverage_table": r3_rows,
        "row_resolution": resolution,
        "r3_vs_disk": r3_vs_disk,
    }

    # ---- falsifier F1: cited full hashes resolve? -----------------------------
    live_hashes = {p["pin"]: f"{cls}:{p['path']}" for cls, p in pins.items()}
    live_hashes[out["frozen"]["static_sha256"]] = "artifacts/formulation/FROZEN.json"
    for path, meta in (frozen.get("files") or {}).items():
        live_hashes[meta.get("sha256")] = path
    f1 = []
    for c in sorted(set(HEX64.findall(r3_text))):
        f1.append({"sha256": c, "resolves_to": live_hashes.get(c, "UNRESOLVED")})
    out["falsifier_F1_cited_hashes"] = f1

    # ---- falsifier F2: counted accepts authored by the pin author -------------
    f2 = []
    for cls, info in r3_rows.items():
        for rec in info["rows"]:
            if rec["reviewer"] in authors[cls]:
                f2.append({"class": cls, "reviewer": rec["reviewer"],
                           "problem": "reviewer_is_pin_author"})
    out["falsifier_F2_author_accepts"] = f2

    # ---- falsifier F3: silence on named carriers ------------------------------
    f3 = {"recorded_dispositions": [], "carrier_mention_probe": []}
    for rel in RECORDED_DISPOSITIONS:
        p = os.path.join(ROOT, rel)
        if os.path.exists(p):
            d = load_json(p) or {}
            f3["recorded_dispositions"].append({
                "path": rel, "sha256": sha256_file(p),
                "verdict": d.get("verdict") or (d.get("sufficiency") and "INSUFFICIENT"),
                "silent_accepts": {k: v.get("accepts_disposing") for k, v in (d.get("sufficiency") or {}).items()}
                or d.get("verdict"),
            })
        else:
            f3["recorded_dispositions"].append({"path": rel, "missing": True})
    for cls, rows in rows_by_class.items():
        kws = CARRIER_KEYWORDS[cls]
        for r in rows:
            if not (crit_strict(r) or crit_loose(r)):
                continue
            text = open(os.path.join(ROOT, r["file"]), encoding="utf-8", errors="replace").read().lower()
            hits = [k for k in kws if k.lower() in text]
            f3["carrier_mention_probe"].append({
                "class": cls, "file": r["file"], "reviewer": r["reviewer"],
                "criterion": "strict" if crit_strict(r) else "loose",
                "keyword_hits": hits, "n_hits": len(hits),
                "informational_only": True})
    out["falsifier_F3_carrier_silence"] = f3

    # ---- falsifier F4: pin movement + mutation check on F2b accepts -----------
    now_pins = {c: sha256_file(os.path.join(ROOT, p["path"])) for c, p in pins.items()}
    out["falsifier_F4_pin_movement"] = [
        {"class": c, "pin_at_measure": pins[c]["pin"], "pin_now": now_pins[c],
         "moved": pins[c]["pin"] != now_pins[c]} for c in SCHEMAS]
    mut = []
    for live, pinned in PINNED_F2B_COPIES.items():
        lp, pp = os.path.join(ROOT, live), os.path.join(ROOT, pinned)
        if os.path.exists(lp) and os.path.exists(pp):
            lh, ph = sha256_file(lp), sha256_file(pp)
            mut.append({"live": live, "live_sha256": lh, "pinned_copy": pinned,
                        "pinned_sha256": ph, "unchanged_since_pin": lh == ph})
    out["f2b_mutation_check_vs_w066_pins"] = mut

    out["summary"] = {
        "f1_unresolved_cited_hashes": sum(1 for x in f1 if x["resolves_to"] == "UNRESOLVED"),
        "f2_violations": len(f2),
        "f3_missing_recorded_dispositions": sum(1 for x in f3["recorded_dispositions"] if x.get("missing")),
        "f3_strict_accepts_with_zero_probe_hits": sum(
            1 for x in f3["carrier_mention_probe"] if x["criterion"] == "strict" and x["n_hits"] == 0),
        "f4_violations": sum(1 for x in out["falsifier_F4_pin_movement"] if x["moved"]),
        "r3_rows_not_resolvable_to_a_file": sum(1 for r in resolution if r["resolves"] != "file_event_id"),
        "r3_rows_missing_reviewed_sha256": sum(
            1 for info in r3_rows.values() for rec in info["rows"] if not rec["r3_fields_present"]["reviewed_sha256"]),
        "r3_rows_missing_filename": sum(
            1 for info in r3_rows.values() for rec in info["rows"] if not rec["r3_fields_present"]["filename"]),
        "r3_rows_missing_independence_basis": sum(
            1 for info in r3_rows.values() for rec in info["rows"] if not rec["r3_fields_present"]["independence_basis"]),
        "r3_claimed_but_not_strict": {c: v["claimed_but_not_strict"] for c, v in r3_vs_disk.items()},
        "r3_claimed_but_not_loose": {c: v["claimed_but_not_loose"] for c, v in r3_vs_disk.items()},
        "disk_loose_not_claimed": {c: v["disk_loose_not_claimed"] for c, v in r3_vs_disk.items()},
    }
    return out


if __name__ == "__main__":
    report = main()
    dest = os.path.join(os.path.dirname(os.path.abspath(__file__)), "report.json")
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(json.dumps(report["summary"], indent=1, sort_keys=True))
    print("report:", dest)
    print("report_sha256:", sha256_file(dest))
