#!/usr/bin/env python3
"""W093-L0-REVREG-01 -- independent L0 verdict-registration census.

One bounded class-bound task: at the measured bytes of ledger/theorems.jsonl
(node L0, classes AF-WCC-VAC-GEN / AF-SCC-C2-VAC-GEN / AF-SCC-C0-VAC-GEN /
AF-WCC-SCALAR-SPH), enumerate the verdict-bearing records that bind those bytes,
across five registration channels, and report exactly which of them the
controller's advisory scan (astra_lifecycle.review_coverage) does not see and why.

Read-only on every canonical path. This is a measurement: it issues no review
verdict, sets no gate verdict, no node status, no validation_status, and edits
no canonical file. It is not an L0 review and must not be consumed as one.

Binding policy (stated, so the register is auditable):
  strong bind  -- the record pins the ledger hash in an explicit pin field
                  (artifact_sha256 / reviewed_sha256 / sha256 / ...) or inside a
                  target identifier (target_id/target/node_id, e.g.
                  "L0:ledger/theorems.jsonl#a1674f094979").
  weak mention -- the hash occurs only in prose/findings text.  Weak mentions
                  are reported separately and never counted in the register;
                  they may be incidental references.

Registration policy: one record per distinct verdict; identical copies are
merged (a snapshot/archive/pinned copy is not a second verdict), and the primary
source is the first of reviews-doc, artifact-doc, accepted-stream event,
outbox event, map row.

Deterministic, stdlib-only. Exit 0 iff controls pass, the classifier is
byte-reproducible, the ledger hash is stable across the run, and every
registered row carries a verified matching token.

Falsifier (also emitted as the claim falsifier):
  Re-run at the same pinned ledger sha256. The census is FALSIFIED if (a) an
  on-disk verdict-bearing document that names L0 and strongly binds the
  measured ledger hash is absent from `register_live`; or (b) a row in
  `register_live` has a bind token that does not match the measured ledger hash
  under the controller prefix rule; or (c) a `controller_missed_live` row's
  miss-mode is not reproducible from the predicate in
  research_map/astra_lifecycle.py; or (d) the classifier digest differs between
  two passes over identical file bytes; or (e) the imported controller
  function's L0 set differs from `controller_reproduction`; or (f) the ledger
  sha256 at run end differs from the pin at run start.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LEDGER = ROOT / "ledger" / "theorems.jsonl"
MAP = ROOT / "research_map" / "research_map.json"
LIFECYCLE_DIR = ROOT / "runtime" / "state" / "controller_verification"
OUT = ROOT / "artifacts" / "worker-093" / "l0_revreg"
CST = timezone(timedelta(hours=8))

SUPERSEDED_LEDGER = {
    "ce42d2057617e3a032c109b24a00b57c7c6b104f37dad5125745af15deebd72": "pre-rebuild ce42d205",
    "3e3d35531421388a17ca7bad7f6c7093dd1cc21a3a808ca8ff65ce6c2b79c6a6": "pre-rebuild 3e3d3553",
    "5fb8bf3a3d145671c013d9478e0fb70a10781372ebd232bef74d6dc5f3d55fe3": "pre-rebuild 5fb8bf3a",
    "effe0f4908bcaada38ec95bdab0dceae641e5d53e1304fcfb0af4f8d104db8c0": "intermediate effe0f49",
}
L1_CITATION = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
VERDICTS = {"accept", "revise", "reject", "inconclusive"}
VERDICT_KEYS = ("verdict", "verdict_recommendation", "review_verdict", "disposition")
PIN_KEYS = ("artifact_sha256", "reviewed_sha256", "sha256", "cited_sha256",
            "target_sha256", "ledger_sha256", "source_sha256", "declared_sha256",
            "declared_f0_sha256", "consistency_evidence_sha256")
COPY_COMPONENTS = {"snapshot", "snapshots", "pinned", "archive", "archives",
                   "incoming", "raw", "controls"}
HEX = re.compile(r"[0-9a-fA-F]{8,64}")


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def mtime_of(p: Path) -> str:
    return datetime.fromtimestamp(p.stat().st_mtime, CST).isoformat(timespec="seconds")


def load_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None


def normalize_verdict(v):
    if not isinstance(v, str):
        return None
    s = v.strip().lower().replace("-", "_").replace(" ", "_")
    s = {"accepted": "accept", "accepts": "accept", "revision": "revise",
         "revise_required": "revise", "rejected": "reject",
         "inconclusive_": "inconclusive"}.get(s, s)
    return s if s in VERDICTS else None


def pick_verdict(d: dict):
    for k in VERDICT_KEYS:
        n = normalize_verdict(d.get(k))
        if n:
            return n, k, "top"
    rec = d.get("recommendation")
    if isinstance(rec, dict):
        for k in VERDICT_KEYS + ("ruling",):
            n = normalize_verdict(rec.get(k))
            if n:
                return n, "recommendation." + k, "nested"
    if isinstance(rec, str):
        n = normalize_verdict(rec)
        if n:
            return n, "recommendation", "top"
    return None, None, None


def _walk_strings(obj, sink: list):
    if isinstance(obj, str):
        sink.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            _walk_strings(v, sink)
    elif isinstance(obj, list):
        for v in obj:
            _walk_strings(v, sink)


def collect_targets(d: dict) -> list:
    out = []
    for k in ("target_id", "target", "node_id", "target_subnode", "subnode", "artifact"):
        if k in d:
            _walk_strings(d[k], out)
    return sorted({s.strip() for s in out if s.strip()})


def collect_pins(d: dict):
    explicit, via_target = set(), set()
    for k in PIN_KEYS:
        if k in d:
            strs = []
            _walk_strings(d[k], strs)
            for s in strs:
                explicit.update(m.lower() for m in HEX.findall(s))
    for k in ("target", "artifact", "target_id", "node_id", "target_subnode", "subnode"):
        if k in d:
            strs = []
            _walk_strings(d[k], strs)
            for s in strs:
                via_target.update(m.lower() for m in HEX.findall(s))
    return sorted(explicit), sorted(via_target)


def token_matches(tok: str, live: str) -> bool:
    """Controller prefix rule: p.startswith(h[:12]) or h.startswith(p[:12])."""
    return tok.startswith(live[:12]) or live.startswith(tok)


def match_kind(tokens, live):
    for t in tokens:
        if token_matches(t, live):
            return t
    return None


def scope_of(targets, path, pins) -> str:
    blob = (" ".join(targets) + " " + str(path)).lower()
    has_cit = "citation" in blob
    has_ledger = ("theorem" in blob) or re.search(r"\bl0\b", blob) is not None or "ledger" in blob
    known = tuple(SUPERSEDED_LEDGER) + (L1_CITATION,)
    pin_known = any(token_matches(t, k) for t in pins for k in known)
    if has_cit and not has_ledger and not pin_known:
        return "L1-citation"
    if has_ledger or pin_known:
        return "L0-ledger"
    return "other"


def make_record(obj: dict, path: str, origin: str, channel: str, doc_sha: str,
                line, mtime: str, live: str):
    v, vkey, vpos = pick_verdict(obj)
    if not v:
        return None
    reviewer = str(obj.get("reviewer") or obj.get("actor") or obj.get("owner") or "?").strip().lower()
    targets = collect_targets(obj)
    explicit, via_target = collect_pins(obj)
    text_pins = sorted({m.lower() for m in HEX.findall(json.dumps(obj, sort_keys=True, default=str))})
    live_ex = match_kind(explicit, live)
    live_tg = match_kind(via_target, live)
    live_pr = match_kind(text_pins, live)
    if live_ex:
        bind_src, bind_tok = "explicit", live_ex
    elif live_tg:
        bind_src, bind_tok = "target", live_tg
    elif live_pr:
        bind_src, bind_tok = "prose", live_pr
    else:
        bind_src, bind_tok = None, None
    sup = sorted({tok for tok in (set(explicit) | set(via_target) | set(text_pins))
                  if any(token_matches(tok, s) for s in SUPERSEDED_LEDGER)})
    return {
        "path": path, "line": line, "origin": origin, "channel": channel,
        "doc_sha256": doc_sha, "mtime": mtime, "reviewer": reviewer, "verdict": v,
        "verdict_key": vkey, "verdict_position": vpos,
        "counts_as_full_schema_verdict": obj.get("counts_as_full_schema_verdict") is not False,
        "full_flag_raw": ("true" if obj.get("counts_as_full_schema_verdict") is True
                          else "false" if obj.get("counts_as_full_schema_verdict") is False else "absent"),
        "score": obj.get("score"), "created_at": obj.get("created_at"),
        "targets": targets, "scope": scope_of(targets, path, explicit + via_target),
        "pins_explicit": explicit, "pins_target": via_target, "pins_prose": text_pins,
        "bind_source": bind_src, "bind_token": bind_tok, "binds_superseded": sup,
        "strong_live": bind_src in ("explicit", "target"),
        "weak_live": bind_src == "prose",
    }


def excluded_path(rel: str) -> bool:
    parts = rel.replace("\\", "/").split("/")
    return any(p in COPY_COMPONENTS for p in parts[2:])  # keep artifacts/<worker>/... root


def iter_artifact_docs():
    for p in sorted((ROOT / "artifacts").rglob("*")):
        if not p.is_file() or p.suffix not in (".json", ".jsonl"):
            continue
        if p.stat().st_size > 2_000_000:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if '"verdict"' not in text and "verdict_recommendation" not in text:
            continue
        low = text.lower()
        if "l0" not in low and "theorem" not in low and "ledger" not in low:
            continue
        yield p, text


def collect(live: str):
    rows, file_hashes = [], {}

    def add(obj, rel, origin, channel, doc_sha, line):
        r = make_record(obj, rel, origin, channel, doc_sha, line, mtime_of(ROOT / rel), live)
        if r:
            rows.append(r)

    for p in sorted((ROOT / "reviews").glob("*.json")):
        rel = str(p.relative_to(ROOT))
        doc_sha = sha256_file(p)
        file_hashes[rel] = doc_sha
        d = load_json(p)
        if isinstance(d, dict):
            add(d, rel, "document", "reviews", doc_sha, None)

    for p, text in iter_artifact_docs():
        rel = str(p.relative_to(ROOT))
        if excluded_path(rel):
            continue
        doc_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        file_hashes[rel] = doc_sha
        if p.suffix == ".jsonl":
            for i, line in enumerate(text.splitlines(), 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                add(d, rel, "document", "artifact", doc_sha, i)
        else:
            try:
                d = json.loads(text)
            except Exception:
                d = None
            if isinstance(d, dict):
                add(d, rel, "document", "artifact", doc_sha, None)

    for p in sorted((ROOT / "comms" / "outbox").rglob("*.jsonl")):
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        rel = str(p.relative_to(ROOT))
        doc_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        file_hashes[rel] = doc_sha
        for i, line in enumerate(text.splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            if d.get("event_type") == "review":
                add(d, rel, "event", "outbox", doc_sha, i)

    ev = ROOT / "research_map" / "events.jsonl"
    if ev.exists():
        rel = str(ev.relative_to(ROOT))
        doc_sha = sha256_file(ev)
        file_hashes[rel] = doc_sha
        with open(ev, encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                if d.get("event_type") == "review":
                    add(d, rel, "event", "events", doc_sha, i)

    m = load_json(MAP)
    if isinstance(m, dict) and isinstance(m.get("reviews"), list):
        rel = "research_map/research_map.json"
        doc_sha = sha256_file(MAP)
        file_hashes[rel] = doc_sha
        for i, d in enumerate(m["reviews"], 1):
            if isinstance(d, dict):
                add(d, rel, "event", "map", doc_sha, i)

    return rows, file_hashes


ORIGIN_RANK = {"document": 0, "event": 1}
CHANNEL_RANK = {"reviews": 0, "artifact": 1, "events": 2, "outbox": 3, "map": 4}


def dedup(rows):
    """Merge the same verdict recorded on several channels/copies into one row."""
    # 1. drop non-review copies whose verdict document is byte-identical to a reviews/*.json doc
    review_shas = {r["doc_sha256"] for r in rows if r["channel"] == "reviews"}
    kept = []
    for r in rows:
        if r["channel"] != "reviews" and r["doc_sha256"] in review_shas:
            continue
        kept.append(r)
    # 2. drop identical artifact docs beyond the first (same bytes = same verdict doc)
    seen_artifact, out = set(), []
    for r in sorted(kept, key=lambda x: (CHANNEL_RANK[x["channel"]], x["path"], x["line"] or 0)):
        if r["channel"] == "artifact":
            if r["doc_sha256"] in seen_artifact:
                continue
            seen_artifact.add(r["doc_sha256"])
        out.append(r)
    # 3. merge rows with the same verdict identity
    merged = {}
    for r in out:
        if r["bind_token"]:
            key = (r["reviewer"], r["verdict"], r["bind_token"], r["bind_source"])
        else:
            key = (r["reviewer"], r["verdict"], tuple(r["targets"]), r["created_at"] or r["mtime"])
        if key not in merged:
            r = dict(r)
            r["created_at_all"] = [r["created_at"]] if r["created_at"] else []
            r["sources"] = [{"path": r["path"], "line": r["line"], "channel": r["channel"],
                             "doc_sha256": r["doc_sha256"]}]
            merged[key] = r
        else:
            m = merged[key]
            m["sources"].append({"path": r["path"], "line": r["line"],
                                 "channel": r["channel"], "doc_sha256": r["doc_sha256"]})
            raws = {m["full_flag_raw"], r["full_flag_raw"]}
            m["full_flag_raw"] = ("false" if "false" in raws else
                                  "true" if "true" in raws else "absent")
            m["counts_as_full_schema_verdict"] = m["full_flag_raw"] != "false"
            if r["created_at"]:
                m["created_at_all"].append(r["created_at"])
            if (ORIGIN_RANK[r["origin"]], CHANNEL_RANK[r["channel"]]) < \
               (ORIGIN_RANK[m["origin"]], CHANNEL_RANK[m["channel"]]):
                m.update({k: r[k] for k in ("path", "line", "origin", "channel", "doc_sha256", "mtime")})
    rows = sorted(merged.values(), key=lambda r: (r["path"], r["line"] or 0, r["reviewer"], r["verdict"]))
    for r in rows:
        r["channels"] = sorted({s["channel"] for s in r["sources"]}, key=lambda c: CHANNEL_RANK[c])
        r["created_at"] = min([c for c in r["created_at_all"] if c], default=r["created_at"])
    return rows


def controller_reproduction(live: str):
    """Call the canonical controller scan and re-derive it under the pinned hash."""
    sys.path.insert(0, str(ROOT / "research_map"))
    import astra_lifecycle as al  # noqa: E402
    cov = al.review_coverage({"L0": {"sha256": live}})
    block = cov.get("L0", {})
    seen = sorted({v["file"] for v in block.get("verdicts", [])})
    mine = []
    for p in sorted((ROOT / "reviews").glob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            continue
        v = str(d.get("verdict", "")).lower()
        if v not in VERDICTS:
            continue
        pins = al._explicit_pins(d)
        if any(t == "L0" for t in al._targets_in_review(d)) and \
           any(tok.startswith(live[:12]) or live.startswith(tok[:12]) for tok in pins):
            mine.append(p.name)
    return {"controller_function_seen": seen, "reimplementation_seen": sorted(set(mine)),
            "agree": seen == sorted(set(mine)),
            "l0_block": {"verdicts": block.get("verdicts", []),
                         "distinct_accept_reviewers": block.get("distinct_accept_reviewers", []),
                         "full_accepts": block.get("full_accepts", [])},
            "note": block.get("note")}


def pinned_lifecycle_scan():
    reps = sorted(LIFECYCLE_DIR.glob("lifecycle_*.json"))
    if not reps:
        return None
    p = max(reps, key=lambda q: q.stat().st_mtime)
    d = load_json(p) or {}
    cov = d.get("review_coverage", {}).get("L0", {})
    return {"path": str(p.relative_to(ROOT)), "sha256": sha256_file(p),
            "verdicts": cov.get("verdicts", []),
            "distinct_accept_reviewers": cov.get("distinct_accept_reviewers", []),
            "measured_hashes_L0": (d.get("measured_hashes", {}) or {}).get("L0")}


def muts(rows, live, controller_files):
    """Miss modes for strong live-binding rows the controller scan does not see."""
    out = []
    for r in rows:
        if not r["strong_live"] or r["scope"] != "L0-ledger":
            continue
        seen = "reviews" in r["channels"] and r["path"] in [f"reviews/{x}" for x in controller_files]
        modes = []
        if not seen:
            extra = [c for c in r["channels"] if c != "reviews"]
            if extra:
                modes.append("M1-channel:" + ",".join(extra))
            if r["verdict_key"] != "verdict" or r["verdict_position"] != "top":
                modes.append("M2-verdict-key:" + str(r["verdict_key"]))
            if r["bind_source"] != "explicit":
                modes.append("M3-pin-source:" + str(r["bind_source"]))
            if not any(("l0" in t.lower()) or ("theorem" in t.lower()) for t in r["targets"]):
                modes.append("M4-target-alias")
            if not modes:
                modes.append("M5-unexplained")
        out.append({"path": r["path"], "line": r["line"], "reviewer": r["reviewer"],
                    "verdict": r["verdict"], "channels": r["channels"],
                    "controller_seen": seen, "miss_modes": modes})
    return out


def build_controls(live: str):
    """Classify planted fixtures; every expectation is asserted."""
    live12 = live[:12]
    fixtures = [
        ("ctl1_seen_accept", {"reviewer": "ctl-a", "verdict": "accept", "target_id": "L0",
                              "reviewed_sha256": live, "score": 4.0}, "reviews", "explicit", True, True, []),
        ("ctl2_artifact_channel", {"reviewer": "ctl-b", "verdict": "accept", "target_id": "L0",
                                   "artifact_sha256": live, "score": 4.0}, "artifact", "explicit", True, False,
         ["M1-channel:artifact"]),
        ("ctl3_renamed_key", {"reviewer": "ctl-c", "verdict_recommendation": "revise",
                              "target_id": "L0", "reviewed_sha256": live, "score": 3.0},
         "reviews", "explicit", True, False, ["M2-verdict-key:verdict_recommendation"]),
        ("ctl4_target_embedded_hash", {"reviewer": "ctl-d", "verdict": "accept",
                                       "target_id": "L0:ledger/theorems.jsonl#" + live12,
                                       "score": 4.0}, "reviews", "target", True, False,
         ["M3-pin-source:target"]),
        ("ctl5_superseded_only", {"reviewer": "ctl-e", "verdict": "accept", "target_id": "L0",
                                  "reviewed_sha256": list(SUPERSEDED_LEDGER)[0], "score": 4.0},
         "reviews", None, False, False, []),
        ("ctl6_not_a_verdict", {"reviewer": "ctl-f", "note": "analysis only", "target_id": "L0",
                                "reviewed_sha256": live}, "reviews", None, False, False, []),
        ("ctl7_nested_recommendation", {"reviewer": "ctl-g", "target_id": "L0",
                                        "recommendation": {"verdict": "inconclusive"},
                                        "reviewed_sha256": live}, "reviews", "explicit", True, False,
         ["M2-verdict-key:recommendation.verdict"]),
        ("ctl8_scoped_full_flag", {"reviewer": "ctl-h", "verdict": "accept", "target_id": "L0",
                                   "reviewed_sha256": live,
                                   "counts_as_full_schema_verdict": False}, "reviews", "explicit", True,
         True, []),
        ("ctl9_prose_only", {"reviewer": "ctl-i", "verdict": "accept", "target_id": "L0",
                             "findings": "the ledger hash " + live + " was inspected"},
         "reviews", "prose", True, False, []),
    ]
    results = []
    for name, doc, channel, want_src, want_live, want_seen, want_modes in fixtures:
        r = make_record(doc, "controls/" + name, "document", channel, "0" * 64, None, "fixture", live)
        if r is None:
            results.append({"fixture": name, "record": None, "pass": want_src is None and not want_modes,
                            "want_bind_source": want_src})
            continue
        seen = (channel == "reviews" and r["verdict_key"] == "verdict" and r["verdict_position"] == "top"
                and r["bind_source"] == "explicit"
                and any(("l0" in t.lower()) or ("theorem" in t.lower()) for t in r["targets"]))
        had = r["strong_live"]
        if had:
            cc = [] if seen else [m["miss_modes"] for m in muts([dict(r, channels=[channel])], live, [])][0]
        else:
            cc = []
        ok = (r["bind_source"] == want_src and sorted(cc) == sorted(want_modes) and seen == want_seen)
        if name == "ctl8_scoped_full_flag":
            ok = ok and r["counts_as_full_schema_verdict"] is False
        if name == "ctl9_prose_only":
            ok = ok and r["weak_live"] and not r["strong_live"]
        results.append({"fixture": name, "record_verdict": r["verdict"], "strong_live": had,
                        "bind_source": r["bind_source"], "controller_seen": seen, "miss_modes": cc,
                        "want_binds_live": want_live, "want_bind_source": want_src,
                        "want_controller_seen": want_seen, "want_modes": want_modes, "pass": ok})
    return results


def markdown_out_of_scope(live: str):
    """Prose documents that mention L0 + a verdict word + the live hash.

    Listed for completeness; NOT counted as verdicts: the comms protocol carries a
    verdict as a review event/JSON record referencing a hash, and a prose sentence
    is not machine-registrable.
    """
    pat = re.compile(r"(?i)\b(accept|revise|reject|inconclusive)\b")
    hits = []
    for p in sorted((ROOT / "reviews").glob("*.md")) + sorted((ROOT / "artifacts").rglob("*.md")):
        if p.stat().st_size > 2_000_000:
            continue
        rel = str(p.relative_to(ROOT))
        if "l0" not in rel.lower() and "theorem" not in rel.lower() and "review" not in rel.lower():
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if live[:12] not in text and live not in text:
            continue
        m = pat.search(text)
        hits.append({"path": rel, "sha256": sha256_file(p),
                     "first_verdict_word": m.group(1).lower() if m else None,
                     "counted": False,
                     "reason": "prose document; not a schema review event/JSON verdict record"})
    return hits


def ledger_class_profile():
    rows = [json.loads(l) for l in LEDGER.read_text().splitlines() if l.strip()]
    prof, unbound = {}, 0
    for r in rows:
        ids = r.get("class_ids") or []
        if not ids:
            unbound += 1
        for c in ids:
            prof[c] = prof.get(c, 0) + 1
    return {"rows": len(rows), "rows_without_class_ids": unbound, "per_class": dict(sorted(prof.items()))}


def digest(rows):
    h = hashlib.sha256()
    for r in sorted(rows, key=lambda x: (x["path"], x["line"] or 0, x["reviewer"], x["verdict"])):
        h.update(json.dumps(r, sort_keys=True, default=str).encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT / "census.json"))
    args = ap.parse_args()

    started = now()
    live = sha256_file(LEDGER)
    live_size = LEDGER.stat().st_size
    raw_a, files_a = collect(live)
    raw_b, files_b = collect(live)
    rows = dedup(raw_a)
    ctrl = controller_reproduction(live)
    pin_report = pinned_lifecycle_scan()
    live2 = sha256_file(LEDGER)

    register_live = [r for r in rows if r["strong_live"] and r["scope"] == "L0-ledger"]
    prose_only = [r for r in rows if r["weak_live"] and r["scope"] == "L0-ledger"]
    superseded = [r for r in rows if (not r["strong_live"]) and (not r["weak_live"])
                  and r["binds_superseded"] and r["scope"] == "L0-ledger"]
    other_scope = [r for r in rows if r["strong_live"] and r["scope"] != "L0-ledger"]
    miss = muts(rows, live, ctrl["controller_function_seen"])
    missed_live = [m for m in miss if not m["controller_seen"]]
    reviewers_live = sorted({r["reviewer"] for r in register_live})
    accepts_live = sorted({r["reviewer"] for r in register_live
                           if r["verdict"] == "accept" and r["counts_as_full_schema_verdict"]})
    scoped_accepts_live = sorted({r["reviewer"] for r in register_live
                                  if r["verdict"] == "accept" and not r["counts_as_full_schema_verdict"]})

    controls = build_controls(live)
    md_hits = markdown_out_of_scope(live)
    drift = sorted(set(files_a) ^ set(files_b)) + \
        sorted(k for k in set(files_a) & set(files_b) if files_a[k] != files_b[k])
    stable_rows_a = {r["doc_sha256"]: r for r in raw_a}
    stable_rows_b = {r["doc_sha256"]: r for r in raw_b}
    common = sorted(set(stable_rows_a) & set(stable_rows_b))
    det_ok = digest([stable_rows_a[k] for k in common]) == digest([stable_rows_b[k] for k in common])
    consistency = all(r["bind_token"] and (r["bind_token"].startswith(live[:12]) or live.startswith(r["bind_token"]))
                      for r in register_live)
    controls_ok = all(c["pass"] for c in controls)
    ok = controls_ok and det_ok and (live == live2) and consistency and ctrl["agree"]

    out = {
        "schema": "w093-l0-revreg-census/v1",
        "task_id": "W093-L0-REVREG-01",
        "actor": "worker-093",
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "node_id": "L0",
        "gate": "G-LIT",
        "started_at": started,
        "finished_at": now(),
        "ledger": {"path": "ledger/theorems.jsonl", "sha256_start": live, "sha256_end": live2,
                   "bytes": live_size, "stable_across_run": live == live2, "mtime": mtime_of(LEDGER)},
        "ledger_class_profile": ledger_class_profile(),
        "binding_policy": {"strong": ["explicit pin field", "hash inside target_id/target/node_id"],
                           "weak": "prose/findings mention only; reported separately, never counted"},
        "channels": {"reviews/*.json": sum(1 for r in raw_a if r["channel"] == "reviews"),
                     "artifacts/** (primary docs)": sum(1 for r in raw_a if r["channel"] == "artifact"),
                     "comms/outbox/*.jsonl": sum(1 for r in raw_a if r["channel"] == "outbox"),
                     "research_map/events.jsonl": sum(1 for r in raw_a if r["channel"] == "events"),
                     "research_map.json#reviews": sum(1 for r in raw_a if r["channel"] == "map")},
        "controller_scan_at_pin": pin_report,
        "controller_reproduction": ctrl,
        "registration_surfaces": {
            "note": "the same bytes, three registration surfaces; the gate-facing count depends on which one is used",
            "pinned_lifecycle_scan": {
                "source": (pin_report or {}).get("path"),
                "verdict_records": len((pin_report or {}).get("verdicts", [])),
                "distinct_accept_reviewers": (pin_report or {}).get("distinct_accept_reviewers", []),
            },
            "live_controller_function": {
                "verdict_records": len(ctrl["controller_function_seen"]),
                "distinct_accept_reviewers": ctrl["l0_block"].get("distinct_accept_reviewers", []),
            },
            "all_channel_register": {
                "verdict_records": len(register_live),
                "distinct_reviewers": len(reviewers_live),
                "accept_records_full_schema": [r["reviewer"] + ":" + r["verdict"] for r in register_live
                                               if r["verdict"] == "accept" and r["counts_as_full_schema_verdict"]],
            },
        },
        "counts": {
            "verdict_records_before_dedup": len(raw_a),
            "verdict_records_after_dedup": len(rows),
            "register_live_records": len(register_live),
            "register_live_distinct_reviewers": len(reviewers_live),
            "register_live_accepts_full_schema": accepts_live,
            "register_live_accepts_scoped": scoped_accepts_live,
            "prose_only_live_mentions": len(prose_only),
            "superseded_only_records": len(superseded),
            "live_records_other_scope": len(other_scope),
            "controller_missed_live_records": len(missed_live),
        },
        "reviewer_eligibility": {
            "note": "reviewers already on record at the measured hash; a fresh blind round must draw from outside this set (REC-13)",
            "on_record_reviewers": reviewers_live,
            "on_record_verdicts": [{"reviewer": r["reviewer"], "verdict": r["verdict"],
                                    "channels": r["channels"], "path": r["path"], "line": r["line"],
                                    "created_at": r["created_at"]} for r in register_live],
        },
        "register_live": register_live,
        "register_prose_only": prose_only,
        "register_superseded_only": superseded,
        "register_live_other_scope": other_scope,
        "markdown_out_of_scope": md_hits,
        "controller_missed_live": missed_live,
        "controls": controls,
        "digest": {"classifier": digest([stable_rows_a[k] for k in common]),
                   "classifier_pass2": digest([stable_rows_b[k] for k in common]),
                   "determinism_ok": det_ok, "register_consistency_ok": consistency,
                   "files_read": len(files_a), "input_drift": drift},
        "verdict": "PASS" if ok else "FAIL",
        "non_claims": [
            "not a review verdict and not a gate verdict; the controller/leads adjudicate",
            "does not adjudicate blind-ness, freshness, text reuse or independence of any verdict",
            "does not count a verdict as binding for a gate; it registers what is on disk at the pinned bytes",
        ],
    }
    Path(args.out).write_text(json.dumps(out, indent=1, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": out["verdict"], "ledger": live[:12],
                      "register_live_records": len(register_live),
                      "on_record_reviewers": reviewers_live,
                      "accepts_full": accepts_live,
                      "missed_by_controller": len(missed_live),
                      "controls_ok": controls_ok, "determinism_ok": det_ok,
                      "controller_agree": ctrl["agree"], "input_drift": drift[:5]}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
