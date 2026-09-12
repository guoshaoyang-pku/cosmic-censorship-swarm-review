#!/usr/bin/env python3
"""W033-INBOX-BACKING-CENSUS-01
Downward-channel authority-backing census over comms/inbox/*.jsonl, with a
blast-radius analysis scoped to the open G-FORM r3 round
(AF-WCC-VAC-GEN; AF-SCC-C2-VAC-GEN; AF-SCC-C0-VAC-GEN).

Question
--------
CF-28/CF-30 record forged downward cards attributed to actor 'astra' in
comms/inbox/astra.jsonl and comms/inbox/astra-lead-audit.jsonl. The controller
quarantined the four lines it found. Was that the whole batch, and did any
unbacked downward card reach the G-FORM r3 authority, its reviewers, or the
three class artifacts?

Method (read-only; writes only inside this directory)
-----------------------------------------------------
1. Freeze the corpus: every comms/inbox/*.jsonl byte-for-byte into pinned/,
   plus the accepted stream, the controller-verification corpus, the
   quarantine corpus, and derived indexes (outbox event ids, G-FORM reviewer
   pool). All measurements are computed from the pinned copies.
2. For every inbox line: raw bytes, sha256, parse status, and a backing
   classification against four record channels:
     ACCEPTED          event_id present in research_map/events.jsonl
     CONTROLLER        event_id present in runtime/state/controller_verification/**
     QUARANTINE        event_id/raw line present in runtime/state/comms_quarantine/**
     OUTBOX            event_id present in some comms/outbox/*.jsonl
     UNBACKED          none of the above
3. Content integrity for ACCEPTED cards: compare every non-wrapper key of the
   card with the accepted event object; any disagreement is a mismatch.
4. Anomaly rules:
     MALFORMED_LINE          JSON parse failure
     CONTROLLER_CARD_UNBACKED actor == 'astra' and not ACCEPTED
     CONTENT_MISMATCH         ACCEPTED with non-empty mismatched keys
     NON_PROTOCOL_CARD        no event_id and no event_type
   Direct-write lead cards (actor astra-lead-*/lead-* and UNBACKED) are
   classified as an expected unbacked channel, not an anomaly.
5. Fingerprints on anomalies: future-dated (created_at > containing file mtime),
   detector-family event_id, token overlap with the quarantined payloads,
   recipient in the G-FORM r3 authority/reviewer pool, and mentions of the
   three class ids, the three schema paths/hashes, FROZEN rev29, or the
   class-separation instrument.
6. Controls (fail-closed): known injections, known-good controller cards,
   synthetic clone/mutation/missing-id/lead-card/malformed/future-dated
   fixtures, determinism, manifest-tamper, blast-radius keyword detector.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

TASK_ID = "W033-INBOX-BACKING-CENSUS-01"
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
PIN = OUT / "pinned"
TZ = _dt.timezone(_dt.timedelta(hours=8))

CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
SCHEMA_PATHS = [
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
]
SCHEMA_HASHES = ["d9cebb9404b2", "e9a27996dfd3", "b2ab6acb2bbe"]
FROZEN_HASH = "815e08079aef"
R3_ASSIGNMENT_ID = "astra-life05-verify-gform-r3"
DETECTOR_KEYWORDS = ["class_separation", "class-separation", "detector"]
WRAPPER_KEYS = {"_received_at", "_source_file", "_normalized", "_ingest_seq", "_applied_at"}
# Routing/annotation keys legitimately added on one side only (comms.py send adds
# `to`; the accepted-stream normalizer adds `class_id`). Presence differences on
# these are recorded as info, never as a content mismatch.
ROUTING_KEYS = {"to", "class_id", "class_ids", "counts_as_full_schema_verdict",
                "counts_as_gate_accept", "coverage_counting_note", "unsolicited_note",
                "assignment_event_ids", "assignment_event_id"}

# Known injected lines recorded by CF-28/CF-30 (pinned from the controller
# quarantine records). Used only as control expectations, never as ground
# truth for the classifier: the classifier must fire on them by rule.
KNOWN_INJECTED = {
    ("astra-lead-audit.jsonl", 24): "human-pi-detector-fix-20260912T0100",
    ("astra-lead-audit.jsonl", 25): "astra-detector-fix-0105",
    ("astra-lead-audit.jsonl", 27): "astra-detector-patch-result-0112",
    ("astra.jsonl", 3): "astra-detector-patch-result-0112",
}
KNOWN_MALFORMED = {("astra.jsonl", 2)}
KNOWN_GOOD_ACCEPTED = [
    ("astra-lead-audit.jsonl", 19),   # astra-life05-verify-gform-r3
    ("astra-lead-audit.jsonl", 28),   # astra-life07-notice-classsep-r3
    ("astra-lead-audit.jsonl", 1),    # asg-...-07
]


def now_iso() -> str:
    return _dt.datetime.now(TZ).isoformat(timespec="seconds")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def ts_gt(a: str | None, b: str) -> bool:
    """True if ISO8601 a is strictly after b (best effort, tz-aware)."""
    if not a:
        return False
    try:
        pa = _dt.datetime.fromisoformat(a.replace("Z", "+00:00"))
    except Exception:
        return False
    try:
        pb = _dt.datetime.fromisoformat(b.replace("Z", "+00:00"))
    except Exception:
        return False
    if pa.tzinfo is None:
        pa = pa.replace(tzinfo=TZ)
    if pb.tzinfo is None:
        pb = pb.replace(tzinfo=TZ)
    return pa > pb


def tokens(text: str) -> set:
    return set(re.findall(r"[a-z0-9_\-]{3,}", (text or "").lower()))


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / max(1, len(a | b))


# --------------------------------------------------------------------------
# input freeze
# --------------------------------------------------------------------------
def freeze_inputs() -> dict:
    if PIN.exists():
        shutil.rmtree(PIN)
    (PIN / "inbox").mkdir(parents=True)
    (PIN / "sources").mkdir(parents=True)
    (PIN / "quarantine").mkdir(parents=True)

    manifest = {"inbox": {}, "sources": {}, "quarantine": {}, "derived": {}}

    for p in sorted((ROOT / "comms" / "inbox").glob("*.jsonl")):
        raw = p.read_bytes()
        (PIN / "inbox" / p.name).write_bytes(raw)
        manifest["inbox"][f"comms/inbox/{p.name}"] = {
            "sha256": sha256_bytes(raw), "bytes": len(raw),
            "mtime": _dt.datetime.fromtimestamp(p.stat().st_mtime, TZ).isoformat(timespec="microseconds"),
        }

    srcs = [
        "research_map/events.jsonl",
        "runtime/state/controller_verification/cf29-detector-write-forensics.json",
    ]
    # newest lifecycle reports at freeze (names are ISO timestamps, so lexical
    # order is chronological); pinning them makes "no controller record" a claim
    # about the latest controller state, not an older one
    lifecycles = sorted((ROOT / "runtime/state/controller_verification").glob("lifecycle_*.json"))
    for p in lifecycles[-3:]:
        srcs.append(str(p.relative_to(ROOT)))
    for p in sorted((ROOT / "runtime/state/controller_verification").glob("astra-lifecycle-*decisions.json")):
        srcs.append(str(p.relative_to(ROOT)))
    for rel in srcs:
        p = ROOT / rel
        if not p.exists():
            continue
        raw = p.read_bytes()
        name = rel.replace("/", "__")
        (PIN / "sources" / name).write_bytes(raw)
        manifest["sources"][rel] = {"sha256": sha256_bytes(raw), "bytes": len(raw)}

    for p in sorted((ROOT / "runtime/state/comms_quarantine").glob("*.jsonl")):
        raw = p.read_bytes()
        (PIN / "quarantine" / p.name).write_bytes(raw)
        manifest["quarantine"][f"runtime/state/comms_quarantine/{p.name}"] = {
            "sha256": sha256_bytes(raw), "bytes": len(raw),
        }

    # derived: outbox event ids (the upward channel)
    outbox_ids = {}
    for p in sorted((ROOT / "comms" / "outbox").glob("*.jsonl")):
        ids = []
        for line in p.read_bytes().split(b"\n"):
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            if isinstance(e, dict) and e.get("event_id"):
                ids.append(e["event_id"])
        if ids:
            outbox_ids[f"comms/outbox/{p.name}"] = sorted(set(ids))
    (PIN / "sources" / "outbox_event_ids.json").write_text(canon(outbox_ids), encoding="utf-8")
    manifest["derived"]["outbox_event_ids.json"] = {
        "sha256": sha256_bytes((PIN / "sources" / "outbox_event_ids.json").read_bytes()),
    }

    # derived: G-FORM reviewer pool from reviews/*.json (class-bound only)
    pool = {}
    for p in sorted((ROOT / "reviews").glob("*.json")):
        try:
            d = json.loads(p.read_bytes())
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        cid = d.get("class_id")
        cids = d.get("class_ids") or []
        tgt = d.get("target") or {}
        tpath = tgt.get("path") if isinstance(tgt, dict) else None
        binds = False
        if cid in CLASS_IDS or any(c in CLASS_IDS for c in cids if isinstance(c, str)):
            binds = True
        if isinstance(tpath, str) and any(tpath.endswith(s) or s in tpath for s in SCHEMA_PATHS):
            binds = True
        if binds:
            rv = d.get("reviewer")
            if rv:
                pool.setdefault(str(rv), []).append(f"reviews/{p.name}")
    for k in pool:
        pool[k] = sorted(set(pool[k]))
    (PIN / "sources" / "gform_reviewer_pool.json").write_text(canon(pool), encoding="utf-8")
    manifest["derived"]["gform_reviewer_pool.json"] = {
        "sha256": sha256_bytes((PIN / "sources" / "gform_reviewer_pool.json").read_bytes()),
    }

    (PIN / "MANIFEST.json").write_text(json.dumps(manifest, indent=1, sort_keys=True), encoding="utf-8")
    return manifest


# --------------------------------------------------------------------------
# indexes
# --------------------------------------------------------------------------
def build_indexes() -> dict:
    accepted = {}
    raw = (PIN / "sources" / "research_map__events.jsonl").read_bytes()
    for line in raw.split(b"\n"):
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except Exception:
            continue
        if isinstance(e, dict) and e.get("event_id"):
            accepted[e["event_id"]] = e

    controller_ids = set()
    for p in sorted((PIN / "sources").glob("runtime__state__controller_verification__*.json")):
        try:
            blob = json.loads(p.read_bytes())
        except Exception:
            continue
        stack = [blob]
        while stack:
            x = stack.pop()
            if isinstance(x, dict):
                for k, v in x.items():
                    if k in ("event_id", "assignment_event_id", "assignment_event_ids") or k.endswith("_event_id"):
                        if isinstance(v, str):
                            controller_ids.add(v)
                        elif isinstance(v, list):
                            controller_ids.update(s for s in v if isinstance(s, str))
                    stack.append(v)
            elif isinstance(x, list):
                stack.extend(x)

    quarantine_ids = set()
    quarantine_lines = []
    for p in sorted((PIN / "quarantine").glob("*.jsonl")):
        raw_q = p.read_bytes()
        for ln in raw_q.split(b"\n"):
            ln = ln.strip()
            if not ln:
                continue
            quarantine_lines.append({"file": p.name, "sha256": sha256_bytes(ln), "raw": ln.decode("utf-8", "replace")})
            try:
                e = json.loads(ln)
            except Exception:
                m = re.search(rb'"event_id"\s*:\s*"([^"]+)"', ln)
                if m:
                    quarantine_ids.add(m.group(1).decode())
                continue
            if isinstance(e, dict) and e.get("event_id"):
                quarantine_ids.add(e["event_id"])

    outbox_ids = set()
    try:
        ob = json.loads((PIN / "sources" / "outbox_event_ids.json").read_bytes())
        for ids in ob.values():
            outbox_ids.update(ids)
    except Exception:
        pass

    pool = json.loads((PIN / "sources" / "gform_reviewer_pool.json").read_bytes())
    return {
        "accepted": accepted,
        "controller_ids": controller_ids,
        "quarantine_ids": quarantine_ids,
        "quarantine_lines": quarantine_lines,
        "outbox_ids": outbox_ids,
        "reviewer_pool": pool,
    }


# --------------------------------------------------------------------------
# classification (pure rule; used for the census and for the controls)
# --------------------------------------------------------------------------
def classify_card(card: dict, raw_text: str, file_mtime: str, idx: dict) -> dict:
    eid = card.get("event_id")
    actor = card.get("actor")
    if not eid:
        cls = "NON_PROTOCOL_CARD" if not card.get("event_type") else "UNBACKED"
    elif eid in idx["accepted"]:
        cls = "ACCEPTED"
    elif eid in idx["controller_ids"]:
        cls = "CONTROLLER"
    elif eid in idx["quarantine_ids"]:
        cls = "QUARANTINE"
    elif eid in idx["outbox_ids"]:
        cls = "OUTBOX"
    else:
        cls = "UNBACKED"

    out = {
        "classification": cls,
        "in_accepted_stream": bool(eid and eid in idx["accepted"]),
        "in_controller_corpus": bool(eid and eid in idx["controller_ids"]),
        "in_quarantine": bool(eid and eid in idx["quarantine_ids"]),
        "in_outbox": bool(eid and eid in idx["outbox_ids"]),
        "anomaly": False,
        "anomaly_kinds": [],
        "content_mismatch_keys": [],
        "key_presence_notes": [],
        "future_dated": False,
        "detector_family": bool(eid and "detector" in str(eid)),
        "quarantine_token_overlap": 0.0,
        "blast_radius_hits": [],
        "recipient_in_r3_pool": False,
        "r3_authority_recipient": False,
    }
    if cls == "ACCEPTED":
        ev = idx["accepted"][eid]
        bad, notes = [], []
        for k in sorted((set(card) | set(ev)) - WRAPPER_KEYS - ROUTING_KEYS):
            if k in card and k in ev:
                if canon(card[k]) != canon(ev[k]):
                    bad.append(k)
            elif k not in card:
                notes.append(f"-{k}")
            else:
                notes.append(f"+{k}")
        out["content_mismatch_keys"] = bad
        out["key_presence_notes"] = notes
        if bad:
            out["anomaly"] = True
            out["anomaly_kinds"].append("CONTENT_MISMATCH")
    if actor == "astra" and cls in ("UNBACKED", "OUTBOX", "CONTROLLER", "QUARANTINE", "NON_PROTOCOL_CARD"):
        out["anomaly"] = True
        out["anomaly_kinds"].append("CONTROLLER_CARD_UNBACKED")
    if card.get("created_at") and ts_gt(str(card.get("created_at")), file_mtime):
        out["future_dated"] = True
        if out["anomaly"]:
            out["anomaly_kinds"].append("FUTURE_DATED")
    # token overlap with the quarantined payloads
    if out["anomaly"] and idx["quarantine_lines"]:
        t = tokens(raw_text)
        best = max((jaccard(t, tokens(q["raw"])) for q in idx["quarantine_lines"]), default=0.0)
        out["quarantine_token_overlap"] = round(best, 4)
    # suspected-forgery composite: unbacked controller card plus at least one
    # independent fingerprint (future-dated, detector-family id, or payload
    # overlap with a quarantined injection)
    if "CONTROLLER_CARD_UNBACKED" in out["anomaly_kinds"] and (
            out["future_dated"] or out["detector_family"] or out["quarantine_token_overlap"] >= 0.2):
        out["anomaly_kinds"].append("SUSPECTED_FORGED")
    # blast radius keywords
    low = raw_text.lower()
    hits = []
    for c in CLASS_IDS:
        if c.lower() in low:
            hits.append(f"class_id:{c}")
    for s in SCHEMA_PATHS:
        if s in raw_text:
            hits.append(f"schema_path:{s}")
    for h in SCHEMA_HASHES + [FROZEN_HASH]:
        if h in raw_text:
            hits.append(f"hash:{h}")
    for k in DETECTOR_KEYWORDS:
        if k in low:
            hits.append(f"detector:{k}")
    if "g-form" in low:
        hits.append("gate:G-FORM")
    if "g-audit" in low:
        hits.append("gate:G-AUDIT")
    if R3_ASSIGNMENT_ID in raw_text:
        hits.append(f"r3_assignment:{R3_ASSIGNMENT_ID}")
    out["blast_radius_hits"] = sorted(set(hits))
    rec = card.get("assignee") or card.get("recipient") or card.get("to")
    if rec and str(rec) in idx["reviewer_pool"]:
        out["recipient_in_r3_pool"] = True
    if str(rec or "") == "astra-lead-audit":
        out["r3_authority_recipient"] = True
    return out


def classify_raw_line(raw: bytes, file_mtime: str, idx: dict) -> dict:
    text = raw.decode("utf-8", "replace")
    try:
        card = json.loads(text)
        if not isinstance(card, dict):
            raise ValueError("not an object")
    except Exception as ex:
        eid = (re.search(r'"event_id"\s*:\s*"([^"]+)"', text) or [None, None])[1]
        asg = (re.search(r'"assignee"\s*:\s*"([^"]+)"', text) or [None, None])[1]
        return {
            "classification": "MALFORMED_LINE",
            "anomaly": True,
            "anomaly_kinds": ["MALFORMED_LINE"],
            "parse_error": str(ex)[:120],
            "event_id": eid,
            "actor": (re.search(r'"actor"\s*:\s*"([^"]+)"', text) or [None, None])[1],
            "assignee": asg,
            "created_at": (re.search(r'"created_at"\s*:\s*"([^"]+)"', text) or [None, None])[1],
            "content_mismatch_keys": [],
            "key_presence_notes": [],
            "in_accepted_stream": bool(eid and eid in idx["accepted"]),
            "in_controller_corpus": bool(eid and eid in idx["controller_ids"]),
            "in_quarantine": bool(eid and eid in idx["quarantine_ids"]),
            "in_outbox": bool(eid and eid in idx["outbox_ids"]),
            "future_dated": False,
            "detector_family": "detector" in text,
            "quarantine_token_overlap": 0.0,
            "blast_radius_hits": [],
            "recipient_in_r3_pool": False,
            "r3_authority_recipient": asg == "astra-lead-audit",
            "raw_prefix": text[:120],
        }
    rec = classify_card(card, text, file_mtime, idx)
    rec["event_id"] = card.get("event_id")
    rec["event_type"] = card.get("event_type")
    rec["actor"] = card.get("actor")
    rec["assignee"] = card.get("assignee")
    rec["created_at"] = card.get("created_at")
    return rec


# --------------------------------------------------------------------------
# census
# --------------------------------------------------------------------------
def scan(manifest: dict, idx: dict) -> dict:
    files = {}
    lines = []
    for name in sorted(manifest["inbox"]):
        rel = name
        meta = manifest["inbox"][rel]
        p = PIN / "inbox" / Path(rel).name
        raw = p.read_bytes()
        file_rec = {"path": rel, "sha256": sha256_bytes(raw), "bytes": len(raw),
                    "mtime": meta["mtime"], "lines": 0, "malformed": 0, "anomalies": 0}
        for i, ln in enumerate(raw.split(b"\n"), 1):
            s = ln.strip()
            if not s:
                continue
            rec = classify_raw_line(s, meta["mtime"], idx)
            rec.update({"file": rel, "line": i, "line_sha256": sha256_bytes(s), "bytes": len(s)})
            lines.append(rec)
            file_rec["lines"] += 1
            if rec["classification"] == "MALFORMED_LINE":
                file_rec["malformed"] += 1
            if rec.get("anomaly"):
                file_rec["anomalies"] += 1
        files[rel] = file_rec

    counts = {}
    for r in lines:
        counts[r["classification"]] = counts.get(r["classification"], 0) + 1

    anomalies = [r for r in lines if r.get("anomaly")]
    direct_write = [r for r in lines if r["classification"] == "UNBACKED"
                    and str(r.get("actor") or "").startswith(("astra-lead-", "lead-"))]
    anomaly_recipients = sorted({(r.get("assignee") or "(none)") for r in anomalies})
    anomaly_kinds = {}
    for r in anomalies:
        for k in r.get("anomaly_kinds", []):
            anomaly_kinds[k] = anomaly_kinds.get(k, 0) + 1
    blast = {}
    for r in anomalies:
        if r.get("blast_radius_hits"):
            blast[f"{r['file']}:{r['line']}"] = r["blast_radius_hits"]
    temporal = [{"file": r["file"], "line": r["line"], "event_id": r.get("event_id"),
                 "actor": r.get("actor"), "created_at": r.get("created_at"),
                 "file_mtime": files[r["file"]]["mtime"], "anomaly": r.get("anomaly", False)}
                for r in lines if r.get("future_dated")]

    astra = [r for r in lines if r.get("actor") == "astra"]
    invariant = {
        "actor_astra_cards": len(astra),
        "astra_accepted": sum(1 for r in astra if r["classification"] == "ACCEPTED"),
        "astra_unbacked_or_quarantined": sum(1 for r in astra if "CONTROLLER_CARD_UNBACKED" in r.get("anomaly_kinds", [])),
        "rule": ("every genuine controller (actor=astra) downward card carries an accepted-stream "
                 "event_id; cards failing this invariant are flagged CONTROLLER_CARD_UNBACKED"),
    }

    for r in lines:
        r.pop("raw_prefix", None)

    return {
        "files": files,
        "lines": lines,
        "classification_counts": counts,
        "anomalies": anomalies,
        "direct_write_lead_channel": direct_write,
        "anomaly_kinds": anomaly_kinds,
        "anomaly_recipients": anomaly_recipients,
        "blast_radius": blast,
        "temporal_inconsistencies": temporal,
        "astra_emission_invariant": invariant,
        "totals": {"files": len(files), "lines": len(lines)},
    }


def _quarantine_payload(raw: bytes) -> tuple[str, str | None]:
    """Return (payload_text, event_id) for a quarantine record line.

    Controller quarantine files carry either the byte-verbatim injected line or a
    wrapper record with the payload under raw_line/line/payload (the malformed
    CF-28 line is wrapped)."""
    text = raw.decode("utf-8", "replace")
    try:
        obj = json.loads(text)
    except Exception:
        m = re.search(r'"event_id"\s*:\s*"([^"]+)"', text)
        return text, (m.group(1) if m else None)
    if isinstance(obj, dict):
        for k in ("raw_line", "raw_line_utf8", "line", "payload", "raw", "content", "quarantined_line"):
            if isinstance(obj.get(k), str):
                inner = obj[k]
                m = re.search(r'"event_id"\s*:\s*"([^"]+)"', inner)
                return inner.strip(), (m.group(1) if m else None)
        eid = obj.get("event_id")
        if isinstance(eid, str):
            return text, eid
    m = re.search(r'"event_id"\s*:\s*"([^"]+)"', text)
    return text, (m.group(1) if m else None)


def quarantine_crosscheck(census: dict, idx: dict) -> dict:
    by_sha = {r["line_sha256"]: f"{r['file']}:{r['line']}" for r in census["lines"]}
    by_eid = {r.get("event_id"): f"{r['file']}:{r['line']}" for r in census["lines"] if r.get("event_id")}
    matched, unmatched = {}, []
    for q in idx["quarantine_lines"]:
        payload, eid = _quarantine_payload(q["raw"].encode())
        key = by_sha.get(sha256_bytes(payload.encode()))
        if not key and eid:
            key = by_eid.get(eid)
        if key:
            matched[q["sha256"][:16]] = {"quarantine_file": q["file"], "inbox_location": key,
                                         "event_id": eid, "match": "bytes" if by_sha.get(sha256_bytes(payload.encode())) else "event_id"}
        else:
            unmatched.append({"quarantine_file": q["file"], "sha256": q["sha256"], "event_id": eid})
    return {"matched": matched, "unmatched": unmatched}


# --------------------------------------------------------------------------
# controls
# --------------------------------------------------------------------------
def run_controls(manifest: dict, idx: dict, census: dict) -> dict:
    c = {}

    def add(cid, name, ok, detail):
        c[cid] = {"name": name, "pass": bool(ok), "detail": str(detail)[:600]}

    by_loc = {f"{r['file']}:{r['line']}": r for r in census["lines"]}

    # C01 known injected lines -> controller-card-unbacked anomaly by rule
    det = {}
    for (f, ln), eid in KNOWN_INJECTED.items():
        r = by_loc.get(f"comms/inbox/{f}:{ln}")
        det[f"{f}:{ln}"] = bool(r and r.get("anomaly") and "CONTROLLER_CARD_UNBACKED" in r["anomaly_kinds"] and r.get("event_id") == eid)
    add("C01", "known injected lines flagged CONTROLLER_CARD_UNBACKED", all(det.values()), det)

    # C02 known malformed line flagged
    r = by_loc.get("comms/inbox/astra.jsonl:2")
    add("C02", "known malformed injected line flagged MALFORMED_LINE",
        bool(r and r["classification"] == "MALFORMED_LINE"), r and r["classification"])

    # C03 known-good controller cards backed, no mismatch
    good = {}
    for f, ln in KNOWN_GOOD_ACCEPTED:
        r = by_loc.get(f"comms/inbox/{f}:{ln}")
        good[f"{f}:{ln}"] = bool(r and r["classification"] == "ACCEPTED" and not r["content_mismatch_keys"] and not r["anomaly"])
    add("C03", "known-good controller cards ACCEPTED and content-intact", all(good.values()), good)

    # C04 synthetic clone with new event_id -> anomaly
    mtime = manifest["inbox"]["comms/inbox/astra.jsonl"]["mtime"]
    clone = {"event_id": "astra-detector-clone-ctl", "event_type": "assignment", "created_at": "2026-09-12T01:00:00+08:00",
             "actor": "astra", "node_id": "A1", "assignee": "astra-lead-audit"}
    r = classify_card(clone, canon(clone), mtime, idx)
    add("C04", "synthetic actor=astra unbacked clone flagged", "CONTROLLER_CARD_UNBACKED" in r["anomaly_kinds"], r)

    # C05 backed card with one field mutated -> content mismatch
    src = by_loc["comms/inbox/astra-lead-audit.jsonl:19"]
    base = json.loads((PIN / "inbox" / "astra-lead-audit.jsonl").read_bytes().split(b"\n")[18])
    mut = dict(base)
    mut["acceptance"] = str(mut.get("acceptance", "")) + " TAMPERED"
    r = classify_card(mut, canon(mut), mtime, idx)
    add("C05", "mutated backed card -> CONTENT_MISMATCH",
        "CONTENT_MISMATCH" in r["anomaly_kinds"] and r["content_mismatch_keys"] == ["acceptance"],
        {"mismatch": r["content_mismatch_keys"], "presence_notes": r["key_presence_notes"]})

    # C06 missing event_id actor=astra -> unbacked anomaly
    r = classify_card({"event_type": "assignment", "actor": "astra", "node_id": "A1"}, "{}", mtime, idx)
    add("C06", "actor=astra card without event_id flagged", "CONTROLLER_CARD_UNBACKED" in r["anomaly_kinds"], r["classification"])

    # C07 lead direct-write unbacked card is channel-expected, not anomaly
    lead = {"event_id": "leadform-ctl", "event_type": "status", "actor": "astra-lead-formulation", "created_at": "2026-09-12T01:00:00+08:00"}
    r = classify_card(lead, canon(lead), mtime, idx)
    add("C07", "lead direct-write unbacked card not flagged as controller anomaly",
        r["classification"] == "UNBACKED" and not r["anomaly"], r["classification"])

    # C08 malformed detection on synthetic bytes
    r = classify_raw_line(b'event_id:human-pi-x{"event_id":"human-pi-y"}', mtime, idx)
    add("C08", "synthetic malformed bytes flagged MALFORMED_LINE", r["classification"] == "MALFORMED_LINE", r["classification"])

    # C09 future-dating rule both directions
    fut = {"event_id": "astra-fut-ctl", "event_type": "assignment", "actor": "astra", "created_at": "2099-01-01T00:00:00+08:00"}
    past = {"event_id": "astra-past-ctl", "event_type": "assignment", "actor": "astra", "created_at": "2000-01-01T00:00:00+08:00"}
    rf = classify_card(fut, canon(fut), mtime, idx)
    rp = classify_card(past, canon(past), mtime, idx)
    add("C09", "future-dating rule fires forward and not backward", rf["future_dated"] and not rp["future_dated"], {"future": rf["future_dated"], "past": rp["future_dated"]})

    # C10 blast-radius keyword detector
    hit = classify_card({"event_id": "astra-br-ctl", "event_type": "assignment", "actor": "astra"},
                        "research_map/class_separation.py " + CLASS_IDS[1] + " " + SCHEMA_HASHES[2], mtime, idx)
    miss = classify_card({"event_id": "astra-br-ctl2", "event_type": "assignment", "actor": "astra"},
                         "unrelated text about weather", mtime, idx)
    add("C10", "blast-radius detector fires on class/detector text and not on benign text",
        bool(hit["blast_radius_hits"]) and not miss["blast_radius_hits"], {"hit": hit["blast_radius_hits"], "miss": miss["blast_radius_hits"]})

    # C11 quarantine cross-check resolves the controller-quarantined lines
    xc = quarantine_crosscheck(census, idx)
    add("C11", "quarantine cross-check matches controller-quarantined bytes", len(xc["matched"]) >= 4 and not xc["unmatched"], xc)

    # C12 determinism: rescan pinned corpus, payload digests equal
    census2 = scan(manifest, idx)
    add("C12", "determinism: second scan of pinned corpus is identical",
        canon(census) == canon(census2), {"digest1": sha256_bytes(canon(census).encode())[:16],
                                          "digest2": sha256_bytes(canon(census2).encode())[:16]})

    # C13 manifest tamper -> verify fails
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "pinned"
        shutil.copytree(PIN, tmp)
        f = tmp / "inbox" / "astra.jsonl"
        f.write_bytes(f.read_bytes() + b'{"event_id":"tamper"}\n')
        tampered_ok = sha256_bytes(f.read_bytes()) != manifest["inbox"]["comms/inbox/astra.jsonl"]["sha256"]
    add("C13", "manifest tamper is detectable", tampered_ok, "inbox/astra.jsonl byte change vs MANIFEST.json")

    # C14 batch-continuation fingerprint -> SUSPECTED_FORGED
    cont = {"event_id": "astra-classsep-stabilize-ctl", "event_type": "assignment", "actor": "astra",
            "created_at": "2099-01-01T01:18:00+08:00", "node_id": "A1", "assignee": "astra-lead-audit",
            "artifact": "research_map/class_separation.py"}
    r = classify_card(cont, canon(cont), mtime, idx)
    add("C14", "batch-continuation fingerprint -> SUSPECTED_FORGED",
        "SUSPECTED_FORGED" in r["anomaly_kinds"] and r["future_dated"] and r["r3_authority_recipient"], r)

    # C15 routing-key presence difference alone is not a content mismatch
    withto = dict(base)
    withto["to"] = "astra-lead-audit"
    r = classify_card(withto, canon(withto), mtime, idx)
    add("C15", "routing-key presence difference is not a content mismatch",
        not r["content_mismatch_keys"], {"mismatch": r["content_mismatch_keys"], "notes": r["key_presence_notes"]})

    passed = sum(1 for v in c.values() if v["pass"])
    return {"task_id": TASK_ID, "controls": c, "passed": passed, "total": len(c), "all_passed": passed == len(c)}


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main(argv: list) -> int:
    verify = "--verify" in argv
    freeze_at = now_iso()
    if verify:
        manifest = json.loads((PIN / "MANIFEST.json").read_bytes())
        for rel, meta in manifest["inbox"].items():
            p = PIN / "inbox" / Path(rel).name
            if sha256_bytes(p.read_bytes()) != meta["sha256"]:
                print(f"VERIFY FAIL: pinned inbox drift {rel}")
                return 2
        for rel, meta in manifest["sources"].items():
            p = PIN / "sources" / rel.replace("/", "__")
            if sha256_bytes(p.read_bytes()) != meta["sha256"]:
                print(f"VERIFY FAIL: pinned source drift {rel}")
                return 2
        for rel, meta in manifest["quarantine"].items():
            p = PIN / "quarantine" / Path(rel).name
            if sha256_bytes(p.read_bytes()) != meta["sha256"]:
                print(f"VERIFY FAIL: pinned quarantine drift {rel}")
                return 2
        idx = build_indexes()
        census = scan(manifest, idx)
        controls = run_controls(manifest, idx, census)
        xc = quarantine_crosscheck(census, idx)
        payload = {"census": census, "quarantine_crosscheck": xc}
        digest = sha256_bytes(canon(payload).encode())
        recorded = json.loads((OUT / "report.json").read_bytes()).get("payload_digest")
        match = digest == recorded
        print(f"verify payload digest: {digest}")
        print(f"recorded payload digest: {recorded}")
        print(f"match: {match}; controls {controls['passed']}/{controls['total']}")
        return 0 if (match and controls["all_passed"]) else 3
    else:
        manifest = freeze_inputs()
        idx = build_indexes()
        census = scan(manifest, idx)
        controls = run_controls(manifest, idx, census)
        xc = quarantine_crosscheck(census, idx)

    payload = {"census": census, "quarantine_crosscheck": xc}
    payload_digest = sha256_bytes(canon(payload).encode())

    report = {
        "task_id": TASK_ID,
        "class_ids": CLASS_IDS,
        "gate": "G-FORM;G-AUDIT",
        "node_id": "A1",
        "authority": "worker evidence only; no gate verdict, no node status, no validation_status",
        "freeze_at": freeze_at,
        "scope": ("Downward-channel authority backing across all comms/inbox/*.jsonl, plus blast radius "
                  "scoped to the open G-FORM r3 round (AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN). "
                  "Read-only; every measurement is recomputed from pinned/ bytes."),
        "totals": census["totals"],
        "classification_counts": census["classification_counts"],
        "anomaly_kinds": census["anomaly_kinds"],
        "anomaly_recipients": census["anomaly_recipients"],
        "astra_emission_invariant": census["astra_emission_invariant"],
        "controller_sources_scanned": sorted(manifest["sources"]),
        "blast_radius": census["blast_radius"],
        "temporal_inconsistencies": census["temporal_inconsistencies"],
        "quarantine_crosscheck": xc,
        "direct_write_lead_channel_count": len(census["direct_write_lead_channel"]),
        "direct_write_lead_channel_files": sorted({r["file"] for r in census["direct_write_lead_channel"]}),
        "payload_digest": payload_digest,
        "files": census["files"],
        "anomalies": census["anomalies"],
        "observation_lines": sorted(
            [r for r in census["lines"] if r["classification"] in ("NON_PROTOCOL_CARD",)],
            key=lambda r: (r["file"], r["line"]),
        ),
    }
    (OUT / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True), encoding="utf-8")
    (OUT / "controls.json").write_text(json.dumps(controls, indent=1, sort_keys=True), encoding="utf-8")

    log = [
        f"task={TASK_ID}",
        f"freeze_at={freeze_at}",
        f"inbox_files={census['totals']['files']} lines={census['totals']['lines']}",
        f"classification_counts={json.dumps(census['classification_counts'], sort_keys=True)}",
        f"anomalies={len(census['anomalies'])} kinds={json.dumps(census['anomaly_kinds'], sort_keys=True)}",
        f"quarantine_matched={len(xc['matched'])} unmatched={len(xc['unmatched'])}",
        f"controls={controls['passed']}/{controls['total']} all_passed={controls['all_passed']}",
        f"payload_digest={payload_digest}",
        f"report_sha256={sha256_bytes((OUT / 'report.json').read_bytes())}",
        f"controls_sha256={sha256_bytes((OUT / 'controls.json').read_bytes())}",
    ]
    (OUT / "run.log").write_text("\n".join(log) + "\n", encoding="utf-8")
    print("\n".join(log))
    return 0 if controls["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
