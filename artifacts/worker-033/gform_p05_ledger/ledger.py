#!/usr/bin/env python3
"""W033-GFORM-P05-LEDGER-02 — supersession-aware two-channel G-FORM accept ledger.

Bounded, class-bound worker task by ``worker-033``.  Scope is **accept-set
bookkeeping only**: no gate verdict, no node completion, no theorem, no physics.

Question
--------
The controller gate audit quotes G-FORM accept sets at ``checked_at``
2026-09-12T00:51:24 (astra-lifecycle pass 05, map sha ed28b714464e...):

    F1 [1 distinct accept reviewer(s) ['worker-088']], F2a [0 ...], F2b [1 ... ['worker-098']]

Are those quotes reproducible from the pinned two-channel corpus
(``reviews/*.json`` files + accepted ``research_map/events.jsonl`` stream) once
each record must (a) bind the quoted epoch hash, (b) be full-schema, (c) come
from a non-author, and (d) still be operative under supersession?  And, under
the controller's *own* counting rule (the rule that passed G-F0 at 00:48:43:
distinct full-schema accept reviewers bound to the measured hash), which of the
three classes already meet the two-distinct-accept criterion at the quote?

Rules (fixed before measurement; same semantics as
``artifacts/worker-033/gform_r12_ledger/check_gform_r12_ledger.py`` @4e8c7e16dc4e)
----------------------------------------------------------------------------------
Binding     : a record binds target T at epoch E iff a whitelisted hash-bearing
              field (artifact_sha256, reviewed_sha256, subject_sha256, ... or the
              same keys inside explicit pin containers) contains the epoch hash
              with >=12 hex prefix.  ``evidence_refs`` never bind; context pins
              (e.g. cross_artifact.F2a.sha256) never bind.
Target      : identity tokens (target_id/node_id/artifact/target/class_id/
              class_ids) map to F1/F2a/F2b.
Full        : counts_as_full_schema_verdict is not False.
Independent : reviewer is not in the target author set
              {astra-lead-formulation, lead-formulation, deepseek-flash-01}.
Gate accept : counts_as_gate_accept is not False (reported, not used by the
              controller's distinct-accept count).
S1          : a record named by a later record's supersedes reference retires it.
S2          : within (target, epoch, reviewer) the latest created_at (ties by
              record id) retires every earlier differing verdict.
Duplicate   : same reviewer + target + epoch + verdict + time over two channels
              is one record with channel provenance, never a supersession.
As-of       : a record counts as-of the quote when created_at <= instant; a file
              record without created_at uses its true source mtime recorded at
              extraction, else unknown-time (included, flagged).

Usage
-----
    python3 ledger.py --extract   # refresh pinned/ from the live corpus (hashes sources)
    python3 ledger.py             # verify pinned/ + controls, write report/controls

Exit status: 0 controls pass; 2 a control failed (fail-closed); 3 pinned manifest
drift/tamper.  Read-only on canonical paths.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

TASK = Path(__file__).resolve().parent
ROOT = TASK.parents[2]
PIN = TASK / "pinned"
CST = _dt.timezone(_dt.timedelta(hours=8))

TASK_ID = "W033-GFORM-P05-LEDGER-02"
PRIOR_TOOL = "artifacts/worker-033/gform_r12_ledger/check_gform_r12_ledger.py"
PRIOR_TOOL_SHA = "4e8c7e16dc4ea9eccbf9b3a255756409797fd6a0c8ef5c7d35b4d75e818abbb9"

EPOCH = {
    "F1": "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
    "F2a": "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
    "F2b": "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
}
TARGET_TOKENS = {
    "F1": {"F1", "AF-WCC-VAC-GEN", "AF_WCC_VACUUM.YAML", "SCHEMAS/AF_WCC_VACUUM.YAML"},
    "F2a": {"F2A", "AF-SCC-C2-VAC-GEN", "AF_SCC_C2_VACUUM.YAML", "SCHEMAS/AF_SCC_C2_VACUUM.YAML"},
    "F2b": {"F2B", "AF-SCC-C0-VAC-GEN", "AF_SCC_C0_VACUUM.YAML", "SCHEMAS/AF_SCC_C0_VACUUM.YAML"},
}
AUTHORS = {"astra-lead-formulation", "lead-formulation", "deepseek-flash-01"}
VERDICTS = {"accept", "revise", "reject", "inconclusive"}
PROSE_KEYS = {"evidence_refs", "artifact_refs", "findings", "scope", "summary",
              "falsifier", "next_falsifier", "notes", "note", "statement",
              "description", "verdict_scope", "review_scope", "independence",
              "hard_failures", "conditions", "non_claims", "needed_to_unblock",
              "score_rationale", "independence_note"}
HEX_RE = re.compile(r"\b[0-9a-f]{12,64}\b")
PIN_KEYS = {"artifact_sha256", "reviewed_sha256", "subject_sha256",
            "subject_snapshot_sha256", "target_sha256", "cited_sha256",
            "sha256", "declared_sha256", "reviewed_artifact_sha256",
            "target_evidence"}
NESTED_PIN_CONTAINERS = {"evidence", "pins", "target_pins"}
QUOTED_RE = re.compile(
    r"(F0|F1|F2a|F2b)\s*\[(\d+)\s+distinct accept reviewer\(s\)"
    r"(?:\s*\[(.*?)\])?\]")
QUOTE_AT = (2026, 9, 12, 0, 51, 24)      # pass-05 G-FORM reason checked_at
PASS04_AT = (2026, 9, 12, 0, 43, 8)      # pass-04 G-FORM reason checked_at
# Frozen provenance of the quote under review: the controller lifecycle-05 report
# (astra-lifecycle-05-final2) that produced the 00:51:24 gate audit.  The reason
# strings are read from that report at extraction and their hashes asserted
# against these constants; if the report is gone the constants are used and the
# provenance source is marked frozen_constant.
PASS05_REPORT = "runtime/state/controller_verification/lifecycle_20260912-005124.json"
PASS05_REPORT_SHA256 = "45b72957bc5227b679e6d0f3da29b56969fe4b9344761f94b5453ac30d12c00a"
PASS05_MAP_AFTER = "ed28b714464e01bda2124759c3237afbad8a47aabbc627b242833740da43faaa"
PASS05_GFORM_REASON = (
    "F1/F2a/F2b measured canonical hashes cce9c60146d6, 5476a3f2c6bc, 55d0a1ea9bda; "
    "publication: af_wcc_vacuum.yaml=aligned, af_scc_c2_vacuum.yaml=aligned, "
    "af_scc_c0_vacuum.yaml=aligned. Review scan at these hashes: F1 [1 distinct accept "
    "reviewer(s) ['worker-088']], F2a [0 distinct accept reviewer(s)], F2b [1 distinct "
    "accept reviewer(s) ['worker-098']]; verdicts bound to superseded hashes are advisory only.")
PASS05_GFORM_REASON_SHA256 = "1b0c7df205a74b310085b22ec58d4d23780fe396d2842603f34caf671531372f"
PASS05_GAUDIT_REASON = (
    "A0 rubric exists (measured d748a9e3574e); A1 coverage at measured hashes: F0 5, F1 1, "
    "F2a 0, F2b 1, L0 1 distinct accepts (need >=2 each); review verdicts bound to superseded "
    "hashes do not count.")
PASS05_GAUDIT_REASON_SHA256 = "a73662fbc1b0639c3aeae1bd38aef1a6cb57006d0ec6e66c5a6307d73761328e"
SOURCE_PATHS = [
    "research_map/research_map.json",
    "research_map/events.jsonl",
    "artifacts/formulation/FROZEN.json",
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
    "runtime/state/artifact_hashes.json",
]


# ---------------------------------------------------------------- primitives
def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def flat(v):
    if isinstance(v, str):
        yield v
    elif isinstance(v, (list, tuple)):
        for x in v:
            yield from flat(x)
    elif isinstance(v, dict):
        for x in v.values():
            yield from flat(x)


def prefix_match(value, h: str) -> bool:
    if not isinstance(value, str):
        return False
    for tok in HEX_RE.findall(value.lower()):
        if len(tok) >= 12 and (h.startswith(tok) or tok.startswith(h[:len(tok)])):
            return True
    return False


def hash_pin_values(rec: dict):
    for k, v in rec.items():
        kl = k.lower()
        if kl in PIN_KEYS:
            yield k, v
        elif kl in NESTED_PIN_CONTAINERS and isinstance(v, dict):
            for k2, v2 in v.items():
                if k2.lower() in PIN_KEYS:
                    yield f"{k}.{k2}", v2


def record_targets(rec: dict) -> set:
    out = set()
    for k in ("target_id", "node_id", "artifact", "target", "class_id", "class_ids",
              "target_id_full", "artifact_path"):
        v = rec.get(k)
        if v is None:
            continue
        for s in flat(v):
            u = str(s).upper()
            for t, toks in TARGET_TOKENS.items():
                for tok in toks:
                    if tok in u:
                        out.add(t)
    return out


def binding_targets(rec: dict) -> set:
    out = set()
    for _key, val in hash_pin_values(rec):
        for t, h in EPOCH.items():
            if prefix_match(val, h):
                out.add(t)
    return out


def _ts(s):
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})", str(s or ""))
    if not m:
        return None
    return tuple(int(x) for x in m.groups())


def record_time(rec: dict, mtime_ns=None):
    for k in ("created_at", "reviewed_at", "review_clock", "_received_at"):
        t = _ts(rec.get(k))
        if t:
            return t, k
    if mtime_ns:
        dt = _dt.datetime.fromtimestamp(mtime_ns / 1e9, _dt.timezone.utc).astimezone(CST)
        return tuple(dt.timetuple())[:6], "mtime"
    return None, None


def supersedes_refs(rec: dict) -> list:
    refs = []
    for key in ("supersedes", "supersedes_review"):
        v = rec.get(key)
        if isinstance(v, str):
            refs.extend(re.findall(r"[A-Za-z0-9][A-Za-z0-9._:/+-]{4,}\.json", v))
            refs.extend(re.findall(r"\bw\d{2,3}-[A-Za-z0-9T:+-]{6,}\b", v))
        elif isinstance(v, dict):
            for k2 in ("path", "file", "event_id", "review_id", "rid"):
                if isinstance(v.get(k2), str):
                    refs.append(v[k2].strip())
        elif isinstance(v, list):
            for x in v:
                if isinstance(x, str):
                    refs.append(x)
    return sorted(set(refs))


def norm(rec: dict, channel: str, rid: str, mtime_ns=None) -> dict:
    reviewer = rec.get("reviewer") or rec.get("actor") or "?"
    t, tsrc = record_time(rec, mtime_ns)
    return {
        "rid": rid, "channel": channel, "reviewer": reviewer,
        "verdict": str(rec.get("verdict", "")).lower(),
        "targets": sorted(record_targets(rec) | binding_targets(rec)),
        "bound": sorted(binding_targets(rec)),
        "full": rec.get("counts_as_full_schema_verdict") is not False,
        "gate_accept_flag": rec.get("counts_as_gate_accept") is not False,
        "independent": reviewer not in AUTHORS,
        "time": t, "time_source": tsrc,
        "created_at": str(rec.get("created_at") or rec.get("reviewed_at")
                          or rec.get("review_clock") or ""),
        "supersedes": supersedes_refs(rec),
        "raw_keys": sorted(rec.keys())[:24],
    }


def _tup(t):
    return tuple(t) if isinstance(t, (list, tuple)) and t else None


def load_records() -> list:
    recs = json.loads((PIN / "records.json").read_text())["records"]
    for r in recs:
        r["time"] = _tup(r.get("time"))
    return recs


def dedup(records):
    groups = {}
    for r in records:
        r["time"] = _tup(r.get("time"))
        key = (r["reviewer"], tuple(r["targets"]), tuple(r["bound"]),
               r["verdict"], r["time"])
        groups.setdefault(key, []).append(r)
    out = []
    for _key, group in groups.items():
        group.sort(key=lambda x: (x["channel"] != "reviews_file", x["rid"]))
        primary = dict(group[0])
        primary["duplicate_channels"] = sorted(g["channel"] for g in group[1:])
        out.append(primary)
    return sorted(out, key=lambda x: (x["time"] or (0,) * 6, x["rid"]))


def retired_by(records):
    retired = {}
    for r in records:
        for ref in r["supersedes"]:
            for other in records:
                if other is r:
                    continue
                cand = {other["rid"], other["rid"].split(":", 1)[-1]}
                if ref in cand or (ref.endswith(".json")
                                   and other["rid"].endswith(ref.split("/")[-1])):
                    retired.setdefault(other["rid"], []).append(
                        {"by": r["rid"], "rule": "S1_named_supersedes"})
    return retired


def operative(records, target, epoch, asof=None):
    rel = [dict(r) for r in records if target in r["targets"] and target in r["bound"]]
    for r in rel:
        r["time"] = _tup(r.get("time"))
    rel = dedup(rel)
    if asof is not None:
        rel = [r for r in rel if r["time"] is None or r["time"] <= asof]
    retired = retired_by(rel)
    kept = []
    for r in rel:
        if r["rid"] in retired:
            r["retired_by"] = retired[r["rid"]]
            continue
        kept.append(r)
    latest = {}
    for r in kept:
        k = (r["reviewer"], target, epoch)
        cur = latest.get(k)
        if cur is None or ((r["time"] or (0,) * 6, r["rid"])
                           > (cur["time"] or (0,) * 6, cur["rid"])):
            latest[k] = r
    for r in kept:
        if latest[(r["reviewer"], target, epoch)] is not r:
            r["retired_by"] = [{"by": latest[(r["reviewer"], target, epoch)]["rid"],
                                "rule": "S2_latest_by_reviewer"}]
    operative_recs = [r for r in kept if "retired_by" not in r]
    accepts = [r for r in operative_recs if r["verdict"] == "accept"]
    full_indep = [r for r in accepts if r["full"] and r["reviewer"] not in AUTHORS]
    gate = [r for r in full_indep if r["gate_accept_flag"]]
    return {
        "records_considered": len(rel),
        "asof": asof is not None,
        "operative": operative_recs,
        "full_independent_accept_reviewers": sorted(r["reviewer"] for r in full_indep),
        "gate_accept_reviewers": sorted(r["reviewer"] for r in gate),
        "retired": [r for r in rel if "retired_by" in r],
        "by_verdict": {v: sorted(r["reviewer"] for r in rel if r["verdict"] == v)
                       for v in sorted({r["verdict"] for r in rel})},
    }


def brief(r: dict) -> dict:
    return {k: r.get(k) for k in ("rid", "channel", "reviewer", "verdict", "full",
                                  "gate_accept_flag", "independent", "created_at",
                                  "time_source", "retired_by", "duplicate_channels")}


# ---------------------------------------------------------------- extraction
def _review_record(d: dict) -> bool:
    return (isinstance(d, dict) and str(d.get("verdict", "")).lower() in VERDICTS
            and d.get("event_type", "review") in (None, "review"))


def extract() -> dict:
    if PIN.exists():
        shutil.rmtree(PIN)
    PIN.mkdir(parents=True)
    created_at = _dt.datetime.now(CST).isoformat(timespec="seconds")
    sources, records = {}, []
    man_files = {}

    for rel in SOURCE_PATHS:
        p = ROOT / rel
        if not p.exists():
            continue
        st = p.stat()
        sources[rel] = {"sha256": sha256_file(p), "bytes": st.st_size,
                        "mtime_ns": st.st_mtime_ns}
        man_files[rel] = {"sha256": sources[rel]["sha256"], "bytes": st.st_size}

    # review files: relevant only if they carry a verdict
    rdir = ROOT / "reviews"
    file_sources = {}
    for p in sorted(rdir.glob("*.json")):
        raw = p.read_bytes()
        try:
            d = json.loads(raw)
        except Exception:
            continue
        if not _review_record(d):
            continue
        rel = f"reviews/{p.name}"
        mt = p.stat().st_mtime_ns
        rec = norm(d, "reviews_file", f"file:{p.name}", mt)
        if not (set(rec["targets"]) & set(EPOCH)):
            continue
        records.append(rec)
        file_sources[rel] = {"sha256": sha256_bytes(raw), "bytes": len(raw),
                             "mtime_ns": mt}
    # accepted event stream
    ev_records, ev_sha, ev_bytes, ev_lines = 0, None, 0, 0
    ev = ROOT / "research_map/events.jsonl"
    if ev.exists():
        raw = ev.read_bytes()
        ev_sha, ev_bytes = sha256_bytes(raw), len(raw)
        for i, line in enumerate(raw.decode("utf-8", "ignore").splitlines(), 1):
            line = line.strip()
            if not line.startswith("{"):
                continue
            ev_lines = i
            try:
                d = json.loads(line)
            except Exception:
                continue
            if not _review_record(d) or d.get("event_type") != "review":
                continue
            rec = norm(d, "accepted_event", f"event:{d.get('event_id') or i}")
            if not (set(rec["targets"]) & set(EPOCH)):
                continue
            records.append(rec)
            ev_records += 1
    if ev_sha:
        sources["research_map/events.jsonl"] = {"sha256": ev_sha, "bytes": ev_bytes,
                                                "mtime_ns": ev.stat().st_mtime_ns}
        man_files["research_map/events.jsonl"] = {"sha256": ev_sha, "bytes": ev_bytes}

    # quoted reasons: the pass-05 quote under review is frozen from its controller
    # report (provenance asserted), plus the live map's current quote as a delta.
    live = json.loads((ROOT / "research_map/research_map.json").read_text())
    lga = live.get("controller_gate_audit", {})

    def parse_quote(reason: str):
        q = {}
        for mm in QUOTED_RE.finditer(reason):
            rv = (mm.group(3) or "").replace("'", "")
            q[mm.group(1)] = {"reviewers": rv.split(", ") if rv.strip() else [],
                              "count": int(mm.group(2))}
        return q

    def a1_coverage(reason: str):
        out = {}
        for tt in ("F0", "F1", "F2a", "F2b", "L0"):
            mm = re.search(tt + r"\s+(\d+)(?:\s+distinct accept)?", reason)
            if mm:
                out[tt] = int(mm.group(1))
        return out

    prov_src, gform_reason, gaudit_reason = "frozen_constant", PASS05_GFORM_REASON, PASS05_GAUDIT_REASON
    ctrl_report = ROOT / PASS05_REPORT
    ctrl_file_only = {}
    if ctrl_report.exists():
        rb = ctrl_report.read_bytes()
        ctrl = json.loads(rb)
        if sha256_bytes(rb) == PASS05_REPORT_SHA256:
            cga = ctrl.get("controller_gate_audit", {})
            gform_reason = (cga.get("G-FORM") or {}).get("reason") or gform_reason
            gaudit_reason = (cga.get("G-AUDIT") or {}).get("reason") or gaudit_reason
            prov_src = PASS05_REPORT
            rc = ctrl.get("review_coverage", {})
            ctrl_file_only = {t: (rc.get(t) or {}).get("distinct_accept_reviewers", [])
                              for t in EPOCH}
    frozen = {
        "provenance_source": prov_src,
        "controller_report": PASS05_REPORT,
        "controller_report_sha256": PASS05_REPORT_SHA256,
        "controller_report_label": "astra-lifecycle-05-final2",
        "map_sha256_after": PASS05_MAP_AFTER,
        "gform_checked_at": "2026-09-12T00:51:24+08:00",
        "gform_reason": gform_reason,
        "gform_reason_sha256": sha256_bytes(gform_reason.encode()),
        "gform_quoted": parse_quote(gform_reason),
        "gaudit_checked_at": "2026-09-12T00:51:24+08:00",
        "gaudit_reason": gaudit_reason,
        "gaudit_reason_sha256": sha256_bytes(gaudit_reason.encode()),
        "gaudit_a1_coverage": a1_coverage(gaudit_reason),
        "measured_hashes": dict(EPOCH),
        "controller_file_only_accepts": ctrl_file_only,
        "hash_assertions": {
            "gform_reason_matches_constant":
                sha256_bytes(gform_reason.encode()) == PASS05_GFORM_REASON_SHA256,
            "gaudit_reason_matches_constant":
                sha256_bytes(gaudit_reason.encode()) == PASS05_GAUDIT_REASON_SHA256,
            "controller_report_matches_constant":
                (not ctrl_report.exists()) or sha256_file(ctrl_report) == PASS05_REPORT_SHA256,
        },
    }
    live_quote = {
        "source": "research_map/research_map.json",
        "checked_at": (lga.get("G-FORM") or {}).get("checked_at"),
        "reason": (lga.get("G-FORM") or {}).get("reason", ""),
        "reason_sha256": sha256_bytes(((lga.get("G-FORM") or {}).get("reason", "")).encode()),
        "quoted": parse_quote((lga.get("G-FORM") or {}).get("reason", "")),
        "gaudit_checked_at": (lga.get("G-AUDIT") or {}).get("checked_at"),
        "gaudit_a1_coverage": a1_coverage((lga.get("G-AUDIT") or {}).get("reason", "")),
    }
    quoted_doc = {
        "task_id": TASK_ID,
        "pass05": frozen,
        "current_live": live_quote,
    }
    (PIN / "records.json").write_text(json.dumps(
        {"created_at": created_at, "records": sorted(
            records, key=lambda r: (r["time"] or (0,) * 6, r["rid"]))},
        indent=1, sort_keys=True) + "\n")
    (PIN / "quoted.json").write_text(json.dumps(quoted_doc, indent=1, sort_keys=True) + "\n")
    (PIN / "sources.json").write_text(json.dumps(
        {"created_at": created_at, "sources": sources, "review_files": file_sources,
         "event_review_records": ev_records, "event_lines": ev_lines},
        indent=1, sort_keys=True) + "\n")

    def h(rel):
        return sha256_file(PIN / rel)

    manifest = {
        "task_id": TASK_ID, "created_at": created_at,
        "tool_sha256": sha256_file(Path(__file__)),
        "prior_tool": PRIOR_TOOL, "prior_tool_sha256": PRIOR_TOOL_SHA,
        "files": {"records.json": {"sha256": h("records.json")},
                  "quoted.json": {"sha256": h("quoted.json")},
                  "sources.json": {"sha256": h("sources.json")}},
        "source_files": man_files,
        "quote_provenance": {
            "controller_report": PASS05_REPORT,
            "controller_report_sha256": PASS05_REPORT_SHA256,
            "gform_reason_sha256": frozen["gform_reason_sha256"],
            "gaudit_reason_sha256": frozen["gaudit_reason_sha256"],
            "assertions": frozen["hash_assertions"],
        },
        "rules": "see ledger.py docstring; rules frozen from prior tool @"
                 + PRIOR_TOOL_SHA[:12],
    }
    (PIN / "MANIFEST.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    return {"sources": sources, "records": len(records),
            "event_review_records": ev_records,
            "quoted": frozen["gform_quoted"],
            "quote_assertions": frozen["hash_assertions"]}


# ---------------------------------------------------------------- controls
def control_suite(records, quoted_doc) -> dict:
    """Synthetic, fail-closed controls on the extracted rule implementation."""
    base = [dict(r) for r in records]
    out = {}

    def mk(rid, reviewer, verdict, target, t, **kw):
        r = {"rid": rid, "channel": kw.pop("channel", "accepted_event"),
             "reviewer": reviewer, "verdict": verdict, "targets": [target],
             "bound": [target], "full": True, "gate_accept_flag": True,
             "independent": True, "time": t, "time_source": "created_at",
             "created_at": "", "supersedes": [], "raw_keys": []}
        r.update(kw)
        return r

    A = (2026, 9, 12, 0, 51, 0)
    B = (2026, 9, 12, 0, 52, 0)

    # C01 two-channel finds an event-only accept that a file-only scan misses
    recs = [mk("event:e1", "wA", "accept", "F2b", A)]
    two = operative(recs, "F2b", EPOCH["F2b"], asof=QUOTE_AT)
    one = [r for r in recs if r["channel"] == "reviews_file"]
    out["C01_event_only_accept_visible_two_channel_only"] = (
        two["full_independent_accept_reviewers"] == ["wA"] and one == [])

    # C02 named supersession retires an accept
    recs = [mk("file:f1", "wB", "accept", "F1", A, channel="reviews_file"),
            mk("event:e2", "wC", "revise", "F1", B, supersedes=["file:f1"])]
    two = operative(recs, "F1", EPOCH["F1"], asof=None)
    out["C02_S1_named_supersedes_retires_accept"] = (
        two["full_independent_accept_reviewers"] == []
        and any(r["rid"] == "file:f1" and r.get("retired_by") for r in two["retired"]))

    # C03 S2: same reviewer later revise retires earlier accept
    recs = [mk("event:a", "wD", "accept", "F1", A),
            mk("event:b", "wD", "revise", "F1", B, supersedes=[])]
    two = operative(recs, "F1", EPOCH["F1"], asof=None)
    out["C03_S2_later_same_reviewer_retires_accept"] = (
        two["full_independent_accept_reviewers"] == [])

    # C04 S2 symmetric: later accept retires earlier revise
    recs = [mk("event:a", "wE", "revise", "F1", A),
            mk("event:b", "wE", "accept", "F1", B, supersedes=[])]
    two = operative(recs, "F1", EPOCH["F1"], asof=None)
    out["C04_S2_later_accept_retires_revise"] = (
        two["full_independent_accept_reviewers"] == ["wE"])

    # C05 evidence_refs alone never bind
    d = {"rid": "event:x", "channel": "accepted_event", "reviewer": "wF",
         "verdict": "accept", "targets": ["F1"], "bound": [], "full": True,
         "gate_accept_flag": True, "independent": True, "time": A,
         "time_source": "created_at", "created_at": "", "supersedes": [],
         "raw_keys": []}
    out["C05_evidence_refs_alone_do_not_bind"] = (
        operative([d], "F1", EPOCH["F1"], asof=None)["full_independent_accept_reviewers"] == [])

    # C06 context pin does not bind a sibling class
    ctx = {"artifact_sha256": EPOCH["F2a"], "cross_artifact": {"F2b": {"sha256": EPOCH["F2b"]}}}
    out["C06_context_pin_does_not_bind"] = binding_targets(ctx) == {"F2a"}

    # C07 as-of excludes post-quote records
    recs = [mk("event:p", "wG", "accept", "F1", B)]
    out["C07_asof_excludes_post_quote"] = (
        operative(recs, "F1", EPOCH["F1"], asof=QUOTE_AT)["full_independent_accept_reviewers"] == []
        and operative(recs, "F1", EPOCH["F1"], asof=None)["full_independent_accept_reviewers"] == ["wG"])

    # C08 author verdict not independent
    recs = [mk("event:au", "astra-lead-formulation", "accept", "F1", A)]
    out["C08_author_excluded_from_independent"] = (
        operative(recs, "F1", EPOCH["F1"], asof=None)["full_independent_accept_reviewers"] == [])

    # C09 gate flag false moves gate set but not full set
    recs = [mk("event:g", "wH", "accept", "F2a", A, gate_accept_flag=False)]
    two = operative(recs, "F2a", EPOCH["F2a"], asof=None)
    out["C09_gate_flag_splits_views"] = (
        two["full_independent_accept_reviewers"] == ["wH"]
        and two["gate_accept_reviewers"] == [])

    # C10 scoped verdict excluded from full accepts
    recs = [mk("event:s", "wI", "accept", "F2a", A, full=False)]
    out["C10_scoped_verdict_excluded"] = (
        operative(recs, "F2a", EPOCH["F2a"], asof=None)["full_independent_accept_reviewers"] == [])

    # C11 cross-channel duplicate is one record
    recs = [mk("file:d", "wJ", "accept", "F2b", A, channel="reviews_file"),
            mk("event:d", "wJ", "accept", "F2b", A)]
    two = operative(recs, "F2b", EPOCH["F2b"], asof=None)
    out["C11_cross_channel_duplicate_deduped"] = (
        two["full_independent_accept_reviewers"] == ["wJ"]
        and len(two["operative"]) == 1)

    # C12 embedded target_id hash binds the class
    recs = [mk("event:t", "wK", "accept", "F2a", A)]
    recs[0]["targets"] = ["F2a"]
    recs[0]["bound"] = ["F2a"]
    out["C12_embedded_target_hash_binds"] = (
        operative(recs, "F2a", EPOCH["F2a"], asof=None)["full_independent_accept_reviewers"] == ["wK"])

    # C13 the material F2b flip: remove worker-089's event -> one accept; keep -> two
    without = [r for r in base if not (r["reviewer"] == "worker-089"
                                       and r["channel"] == "accepted_event"
                                       and "F2b" in r["targets"])]
    with_ = [r for r in base
             if r["channel"] == "accepted_event" and r["reviewer"] == "worker-089"
             and r["verdict"] == "accept" and "F2b" in r["bound"]]
    n_wo = len(operative(without, "F2b", EPOCH["F2b"], asof=QUOTE_AT)["full_independent_accept_reviewers"])
    n_w = len(operative(base, "F2b", EPOCH["F2b"], asof=QUOTE_AT)["full_independent_accept_reviewers"])
    out["C13_f2b_two_accept_flip_on_w089_event"] = (
        n_wo == 1 and n_w >= 2 and len(with_) == 1)

    # C14 quoted-reason parse reproduces the pass-05 G-FORM string fields
    q = quoted_doc["pass05"]["gform_quoted"]
    out["C14_quoted_reason_parse_complete"] = (
        set(q) >= {"F1", "F2a", "F2b"} and q.get("F1", {}).get("reviewers") == ["worker-088"]
        and q.get("F2b", {}).get("reviewers") == ["worker-098"])

    # C16 frozen pass-05 quote provenance hashes match their constants
    out["C16_frozen_quote_provenance"] = (
        quoted_doc["pass05"]["gform_reason_sha256"] == PASS05_GFORM_REASON_SHA256
        and quoted_doc["pass05"]["gaudit_reason_sha256"] == PASS05_GAUDIT_REASON_SHA256
        and all(quoted_doc["pass05"]["hash_assertions"].values()))

    # C17 the live-map quote is present and distinct from the frozen pass-05 quote
    lv = quoted_doc.get("current_live", {})
    out["C17_live_quote_delta_present"] = (
        bool(lv.get("checked_at")) and lv.get("reason_sha256")
        != quoted_doc["pass05"]["gform_reason_sha256"])

    # C15 manifest tamper is detected (self-hash check)
    man = json.loads((PIN / "MANIFEST.json").read_text())
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        for f in ("records.json", "quoted.json", "sources.json"):
            shutil.copy(PIN / f, td / f)
        (td / "records.json").write_text((td / "records.json").read_text() + " ")
        drift = [f for f, meta in man["files"].items()
                 if sha256_file(td / f) != meta["sha256"]]
    out["C15_manifest_tamper_detected"] = drift == ["records.json"]

    return {k: {"pass": bool(v), "detail": str(v)} for k, v in out.items()}


# ---------------------------------------------------------------- main
def manifest_drift(manifest) -> list:
    bad = []
    for f, meta in manifest["files"].items():
        if not (PIN / f).exists() or sha256_file(PIN / f) != meta["sha256"]:
            bad.append(f)
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--extract", action="store_true")
    args = ap.parse_args()
    if args.extract:
        info = extract()
        print(json.dumps({"extracted": info["records"],
                          "event_review_records": info["event_review_records"],
                          "quoted": info["quoted"]}, indent=1, sort_keys=True))
        return 0

    manp = PIN / "MANIFEST.json"
    if not manp.exists():
        print("no pinned manifest; run --extract", file=sys.stderr)
        return 3
    manifest = json.loads(manp.read_text())
    drift = manifest_drift(manifest)
    if drift:
        print("PINNED MANIFEST DRIFT:", drift, file=sys.stderr)
        return 3

    recs = load_records()
    quoted_doc = json.loads((PIN / "quoted.json").read_text())
    sources = json.loads((PIN / "sources.json").read_text())

    # live-vs-pinned re-hash of the canonical sources used
    live_drift = []
    for rel, meta in manifest["source_files"].items():
        p = ROOT / rel
        if not p.exists() or sha256_file(p) != meta["sha256"]:
            live_drift.append({"path": rel,
                               "pinned": meta["sha256"],
                               "live": sha256_file(p) if p.exists() else None})

    analysis, channels = {}, {}
    for t, h in EPOCH.items():
        q = quoted_doc["pass05"]["gform_quoted"].get(t, {})
        asof = operative(recs, t, h, asof=QUOTE_AT)
        p04 = operative(recs, t, h, asof=PASS04_AT)
        latest = operative(recs, t, h, asof=None)
        file_only = sorted({r["reviewer"] for r in recs
                            if r["channel"] == "reviews_file" and r["verdict"] == "accept"
                            and r["full"] and r["independent"] and t in r["targets"]
                            and t in r["bound"]
                            and (r["time"] is None or r["time"] <= QUOTE_AT)})
        analysis[t] = {
            "epoch_sha256": h,
            "quoted_reviewers": q.get("reviewers", []),
            "quoted_count": q.get("count"),
            "file_only_accept_reviewers": file_only,
            "asof_quote": {
                "instant": "2026-09-12T00:51:24+08:00",
                "full_independent_accept_reviewers": asof["full_independent_accept_reviewers"],
                "gate_accept_reviewers": asof["gate_accept_reviewers"],
                "quoted_reproducible_full_view":
                    sorted(q.get("reviewers", [])) == asof["full_independent_accept_reviewers"],
                "quoted_reproducible_gate_view":
                    sorted(q.get("reviewers", [])) == asof["gate_accept_reviewers"],
                "operative": [brief(r) for r in asof["operative"]],
                "retired": [brief(r) for r in asof["retired"]],
            },
            "pass04_asof": {
                "instant": "2026-09-12T00:43:08+08:00",
                "full_independent_accept_reviewers": p04["full_independent_accept_reviewers"],
                "gate_accept_reviewers": p04["gate_accept_reviewers"],
            },
            "latest_operative": {
                "full_independent_accept_reviewers": latest["full_independent_accept_reviewers"],
                "gate_accept_reviewers": latest["gate_accept_reviewers"],
            },
            "delta_pass04_to_quote": sorted(
                set(asof["full_independent_accept_reviewers"])
                - set(p04["full_independent_accept_reviewers"])),
        }
    for t in EPOCH:
        channels[t] = {
            "file_only": analysis[t]["file_only_accept_reviewers"],
            "two_channel": analysis[t]["asof_quote"]["full_independent_accept_reviewers"],
        }

    counts = {t: len(analysis[t]["asof_quote"]["full_independent_accept_reviewers"]) for t in EPOCH}
    gate_counts = {t: len(analysis[t]["asof_quote"]["gate_accept_reviewers"]) for t in EPOCH}
    criterion = {
        "controller_reading": ("distinct reviewers with a full-schema accept "
                               "(counts_as_full_schema_verdict is not False) bound to "
                               "the measured hash at the quote instant; the same "
                               "counting rule published in the G-F0 pass reason at "
                               "2026-09-12T00:48:43 (5 distinct accept reviewers)"),
        "asof_full_accept_counts": counts,
        "asof_gate_accept_counts": gate_counts,
        "two_distinct_met": {t: counts[t] >= 2 for t in EPOCH},
        "gaudit_a1_quoted_coverage": quoted_doc["pass05"]["gaudit_a1_coverage"],
        "note": ("worker measurement only; whether counts_as_gate_accept=false records "
                 "count, and any gate verdict, remain controller/lead-audit decisions"),
    }

    # the epoch moved after the quoted instant; report the delta without claiming it
    live_hashes = {}
    mm = re.search(r"F1/F2a/F2b measured canonical hashes ([0-9a-f]+), ([0-9a-f]+), ([0-9a-f]+)",
                   quoted_doc["current_live"].get("reason", ""))
    if mm:
        live_hashes = {"F1": mm.group(1), "F2a": mm.group(2), "F2b": mm.group(3)}
    epoch_move = {
        "quoted_epoch": EPOCH,
        "live_epoch": live_hashes,
        "live_checked_at": quoted_doc["current_live"].get("checked_at"),
        "moved_since_quote": any(live_hashes.get(t, EPOCH[t])[:12] != EPOCH[t][:12]
                                 for t in EPOCH),
        "live_quoted_coverage": quoted_doc["current_live"].get("quoted"),
        "note": ("the rev12 ledger is advisory for the quoted epoch only; no claim is "
                 "made about rev13 coverage without a fresh binding pass"),
    }

    findings = [
        {"id": "W033-P05-HF-01", "severity": "hard", "class_ids": ["AF-WCC-VAC-GEN"],
         "finding": ("F1 quoted {worker-088} is not the operative set. worker-088's own "
                     "amended event at the same hash (00:39:02) is revise with S1 "
                     "supersedes on the accept file; operative F1 full/gate accept is "
                     "worker-061 (event-only, 00:37:58)."),
         "evidence_refs": ["reviews/F1-review-088-rev12-amended.json",
                           "research_map/events.jsonl#w088-20260912T003902-review-f1-rev12-amended",
                           "research_map/events.jsonl#w061-rev12-20260912T0040-review"]},
        {"id": "W033-P05-HF-02", "severity": "hard", "class_ids": ["AF-SCC-C0-VAC-GEN"],
         "finding": ("F2b quoted {worker-098} is reproducible only under the gate-accept "
                     "view. Under the controller's own criterion reading (the one that "
                     "passed G-F0 at 00:48:43) it is incomplete: worker-089's accepted "
                     "event at 00:48:09 is an independent full-schema accept bound to "
                     "55d0a1ea9bda, so the two-channel count is 2 distinct accepts "
                     "(worker-098 + worker-089) and F2b already meets the "
                     "two-distinct-accept criterion. The file-only scan reports 1. "
                     "worker-089 sets counts_as_gate_accept=false, so the gate-accept "
                     "view stays at 1; that flag is the lead-audit dispute."),
         "evidence_refs": ["research_map/events.jsonl#w089-20260912T004809-review",
                           "reviews/F2b-repair-verify-worker-098.json"]},
        {"id": "W033-P05-HF-03", "severity": "hard",
         "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
         "finding": ("Mechanism persists at pass 05: astra_lifecycle.review_coverage() "
                     "reads reviews/*.json only and at face value, so the pass-05 reason "
                     "(checked_at 00:51:24) still carries the withdrawn F1 accept and "
                     "still cannot see event-only accepts (worker-061 F1, worker-089 F2a "
                     "and F2b)."),
         "evidence_refs": ["research_map/astra_lifecycle.py:176",
                           "research_map/research_map.json#controller_gate_audit.G-FORM"]},
        {"id": "W033-P05-R12-03", "severity": "major", "class_ids": ["AF-SCC-C2-VAC-GEN"],
         "finding": ("F2a quoted {} is reproducible under the gate-accept view; under the "
                     "full-schema view it is {worker-089} (counts_as_gate_accept=false, "
                     "00:39:59), still event-only and still below two accepts."),
         "evidence_refs": ["research_map/events.jsonl#w089-20260912T003959-review"]},
        {"id": "W033-P05-INFO-04", "severity": "info",
         "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
         "finding": ("Secondary hash-pinned cross-check (reproduces HF-086-R1, no new "
                     "claim): the three rev12 schemas declare consistency_evidence_sha256 "
                     "675a99d0d25b which resolves nowhere; measured/FROZEN-pinned "
                     "taxonomy_consistency.json is 9e335e9ba1bf."),
         "evidence_refs": ["artifacts/formulation/evidence/taxonomy_consistency.json",
                           "artifacts/formulation/FROZEN.json"]},
        {"id": "W033-P05-DELTA-05", "severity": "info",
         "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
         "finding": (f"Epoch move after the quote: at "
                     f"{quoted_doc['current_live'].get('checked_at')} the measured canonical "
                     f"hashes are F1 {live_hashes.get('F1', '?')[:12]}, F2a "
                     f"{live_hashes.get('F2a', '?')[:12]}, F2b {live_hashes.get('F2b', '?')[:12]} "
                     "and the live scan reports 0 accepts for all three; the rev12 findings "
                     "above are historical for the 00:51:24 quote and are not a claim "
                     "about the new epoch."),
         "evidence_refs": ["research_map/research_map.json#controller_gate_audit.G-FORM"]},
    ]

    controls = control_suite(recs, quoted_doc)
    n_fail = sum(1 for c in controls.values() if not c["pass"])
    report = {
        "task_id": TASK_ID, "worker": "worker-033",
        "scope": "accept-set bookkeeping only; worker-level measurement, not a gate verdict",
        "rules_source": {"derived_from": PRIOR_TOOL, "sha256": PRIOR_TOOL_SHA},
        "epoch": EPOCH,
        "quote": quoted_doc["pass05"],
        "current_live_quote": quoted_doc["current_live"],
        "epoch_move": epoch_move,
        "analysis": analysis,
        "channels": channels,
        "criterion": criterion,
        "findings": findings,
        "controls": {"total": len(controls), "failed": n_fail,
                     "all_passed": n_fail == 0},
        "pinned": {"manifest_sha256": sha256_file(PIN / "MANIFEST.json"),
                   "records_sha256": sha256_file(PIN / "records.json"),
                   "quoted_sha256": sha256_file(PIN / "quoted.json"),
                   "sources_sha256": sha256_file(PIN / "sources.json"),
                   "source_file_count": len(manifest["source_files"])},
        "live_source_drift": live_drift,
        "falsifier": (
            "Re-run ledger.py on a pinned snapshot; controls fail-closed. The report is "
            "falsified if any of: worker-061's F1 accept is withdrawn or a binding "
            "reviews/*.json accept at cce9c60146d6 supersedes it; worker-088 re-issues an "
            "operative F1 accept at cce9c60146d6 after 00:39:02; worker-089's F2b accept "
            "at 55d0a1ea9bda is superseded/withdrawn, is shown not to bind that hash, or "
            "its counts_as_full_schema_verdict is corrected to false; worker-098's F2b "
            "accept is superseded; the quoted G-FORM reason at 00:51:24 is shown to "
            "list worker-061/worker-089 (i.e. a corrected controller scan); or any "
            "schema moves off the three epoch hashes."),
        "not_claimed": [
            "no gate verdict, no node status=done, no validation_status=passed",
            "no theorem, no physics, no adjudication of substantive F1/F2a/F2b findings",
            "no review of schema semantics; worker-089's gate-flag dispute is left to lead-audit",
        ],
        "generated_at": _dt.datetime.now(CST).isoformat(timespec="seconds"),
    }
    (TASK / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    (TASK / "controls.json").write_text(json.dumps(
        {"task_id": TASK_ID, "total": len(controls), "failed": n_fail,
         "all_passed": n_fail == 0, "controls": controls},
        indent=1, sort_keys=True) + "\n")
    print(json.dumps({"task_id": TASK_ID, "controls_failed": n_fail,
                      "asof_full_accepts": counts,
                      "criterion_met": criterion["two_distinct_met"],
                      "epoch_moved_since_quote": epoch_move["moved_since_quote"],
                      "live_source_drift": len(live_drift)}, indent=1))
    return 2 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
