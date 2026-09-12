#!/usr/bin/env python3
"""W033-GFORM-R29-LEDGER-03 — supersession-aware two-channel G-FORM accept ledger.

Bounded, class-bound worker task by ``worker-033``.  Scope is **accept-set
bookkeeping only**: no gate verdict, no node completion, no theorem, no physics.

Question
--------
At the current epoch (schema hashes F1 ``d9cebb9404b2`` / F2a ``e9a27996dfd3`` /
F2b ``b2ab6acb2bbe``, FROZEN revision 29 ``815e08079aef``) the controller gate
audit at ``checked_at`` 2026-09-12T01:01:17 (astra-lifecycle-06-final, reason
sha256 ``3fc6c74453b0``) quotes:

    F1 [4 distinct accept reviewer(s) ['worker-045','worker-072','worker-075','worker-085']]
    F2a [3 distinct accept reviewer(s) ['worker-017','worker-072','worker-075']]
    F2b [0 distinct accept reviewer(s)]

Is that quote reproducible from the pinned two-channel corpus (``reviews/*.json``
+ the accepted ``research_map/events.jsonl`` stream) once each record must (a)
bind the epoch hash, (b) be full-schema, (c) come from a non-author, and (d)
still be operative under supersession?  Which classes meet the controller's own
two-distinct-accept criterion at the frozen bytes?  And which structural blind
spots remain in the controller scan (``research_map/astra_lifecycle.py``
``review_coverage()`` @032d4afcb061) at this epoch?

Rules (fixed before measurement; semantics inherited verbatim from
``artifacts/worker-033/gform_p05_ledger/ledger.py`` @4342806ad5fe)
----------------------------------------------------------------------------
Binding     : a record binds target T at epoch E iff a whitelisted hash-bearing
              field (artifact_sha256, reviewed_sha256, subject_sha256,
              target_sha256, ..., or the same keys inside ``evidence`` /
              ``pins`` / ``target_pins`` containers) contains the epoch hash with
              >= 12 hex prefix.  ``evidence_refs`` never bind; context pins
              (e.g. ``cross_artifact.F2a.sha256``) never bind.
Target      : identity tokens (target_id/node_id/artifact/target/class_id/
              class_ids) map to F1/F2a/F2b.
Full        : counts_as_full_schema_verdict is not False.
Independent : reviewer is not in the target author set
              {astra-lead-formulation, lead-formulation, deepseek-flash-01}.
Gate accept : counts_as_gate_accept is not False (reported side by side).
S1          : a record named by a later record's supersedes reference retires it.
S2          : within (target, epoch, reviewer) the latest created_at (ties by
              record id) retires every earlier differing verdict.
Duplicate   : same reviewer + target + epoch + verdict + time over two channels
              is one record with channel provenance, never a supersession.
As-of       : a record counts as-of an instant when created_at <= instant; a file
              record without created_at uses its true source mtime recorded at
              extraction, else unknown-time (included, flagged).

Controller reproduction
-----------------------
``controller_scan()`` reimplements ``astra_lifecycle.review_coverage()`` exactly:
file channel only, target map via ``_targets_in_review`` (exact ``target_id`` /
``target`` / ``target_subnode`` aliases only), pins via ``_explicit_pins`` (only
top-level artifact_sha256 / reviewed_sha256 / sha256 / cited_sha256), no
supersession, face value.  The delta between that scan and the two-channel
operative set measures the blind spots on pinned data.

Usage
-----
    python3 ledger.py --extract   # refresh pinned/ from the live corpus, hash sources
    python3 ledger.py             # verify pinned/, run controls, write report + controls

Exit status: 0 controls pass; 2 a control failed (fail-closed); 3 pinned manifest
drift.  Read-only on canonical paths.
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

TASK_ID = "W033-GFORM-R29-LEDGER-03"
PRIOR_TOOL = "artifacts/worker-033/gform_p05_ledger/ledger.py"
PRIOR_TOOL_SHA = "4342806ad5feb93ef49acc2f29debe89c847397c126f17cf65244c30f971d80b"
CONTROLLER_TOOL = "research_map/astra_lifecycle.py"
CONTROLLER_TOOL_SHA = "032d4afcb061d70f8f3ea1ba2231c04c12fa8a9f4745521a223ac16135ccc3ac"

EPOCH = {
    "F1": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "F2a": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "F2b": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
}
EPOCH_FROZEN_REV = 29
EPOCH_FROZEN_SHA = "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"
EPOCH_FROZEN_AT = (2026, 9, 12, 0, 57, 26)

# Frozen provenance of the quote under review (astra-lifecycle-06-final).
BASELINE_REPORT = "runtime/state/controller_verification/lifecycle_20260912-010117.json"
BASELINE_REPORT_SHA = "076d03a643213a6064b104c10b2a5aa7cb1688d6225ecbbe57561b97a19e33b4"
BASELINE_LABEL = "astra-lifecycle-06-final"
BASELINE_AT = (2026, 9, 12, 1, 1, 17)
BASELINE_MAP_AFTER = "f344ed2aaea58e4d21c46c1d919e2476b860da4b757b9fbc948d3649bac7c749"
BASELINE_GFORM_REASON = (
    "F1/F2a/F2b measured canonical hashes d9cebb9404b2, e9a27996dfd3, b2ab6acb2bbe; "
    "publication: af_wcc_vacuum.yaml=aligned, af_scc_c2_vacuum.yaml=aligned, "
    "af_scc_c0_vacuum.yaml=aligned. Review scan at these hashes: F1 [4 distinct accept "
    "reviewer(s) ['worker-045', 'worker-072', 'worker-075', 'worker-085']], F2a [3 distinct "
    "accept reviewer(s) ['worker-017', 'worker-072', 'worker-075']], F2b [0 distinct accept "
    "reviewer(s)]; verdicts bound to superseded hashes are advisory only."
)
BASELINE_GFORM_REASON_SHA = "3fc6c74453b049bfea20349c1a22b725ad689651526beecb933e52cd83ced44a"
EXPECTED_QUOTE = {
    "F1": ["worker-045", "worker-072", "worker-075", "worker-085"],
    "F2a": ["worker-017", "worker-072", "worker-075"],
    "F2b": [],
}

TARGET_TOKENS = {
    "F1": {"F1", "AF-WCC-VAC-GEN", "AF_WCC_VACUUM.YAML", "SCHEMAS/AF_WCC_VACUUM.YAML"},
    "F2a": {"F2A", "AF-SCC-C2-VAC-GEN", "AF_SCC_C2_VACUUM.YAML", "SCHEMAS/AF_SCC_C2_VACUUM.YAML"},
    "F2b": {"F2B", "AF-SCC-C0-VAC-GEN", "AF_SCC_C0_VACUUM.YAML", "SCHEMAS/AF_SCC_C0_VACUUM.YAML"},
}
# exact controller alias map (astra_lifecycle.TARGET_ALIASES @032d4afcb061)
CONTROLLER_ALIASES = {
    "F0": "F0", "F1": "F1", "F2A": "F2a", "F2B": "F2b", "F2": "F2b",
    "L0": "L0", "L1": "L1",
    "AF-WCC-VAC-GEN": "F1",
    "AF-SCC-C2-VAC-GEN": "F2a",
    "AF-SCC-C0-VAC-GEN": "F2b",
}
AUTHORS = {"astra-lead-formulation", "lead-formulation", "deepseek-flash-01"}
VERDICTS = {"accept", "revise", "reject", "inconclusive"}
HEX_RE = re.compile(r"\b[0-9a-f]{12,64}\b")
PIN_KEYS = {"artifact_sha256", "reviewed_sha256", "subject_sha256",
            "subject_snapshot_sha256", "target_sha256", "cited_sha256",
            "sha256", "declared_sha256", "reviewed_artifact_sha256",
            "target_evidence"}
NESTED_PIN_CONTAINERS = {"evidence", "pins", "target_pins"}
QUOTED_RE = re.compile(
    r"(F0|F1|F2a|F2b)\s*\[(\d+)\s+distinct accept reviewer\(s\)"
    r"(?:\s*\[(.*?)\])?\]")
SOURCE_PATHS = [
    "research_map/astra_lifecycle.py",
    "research_map/research_map.json",
    "research_map/events.jsonl",
    "artifacts/formulation/FROZEN.json",
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
    "artifacts/formulation/evidence/taxonomy_consistency.json",
    "research_map/formulation_taxonomy.yaml",
    BASELINE_REPORT,
]
RESOLUTION_MAP_PATHS = [
    "artifacts/formulation/FROZEN.json",
    "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/formulation_taxonomy.yaml",
    "artifacts/formulation/evidence/taxonomy_consistency.json",
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
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


def controller_targets(rec: dict) -> set:
    """Exact reimplementation of astra_lifecycle._targets_in_review."""
    out = set()
    for key in ("target_id", "target", "target_subnode"):
        v = rec.get(key)
        if isinstance(v, str):
            out.add(v)
        elif isinstance(v, dict):
            for k2 in ("target_id", "target_subnode", "subnode", "node_id"):
                if isinstance(v.get(k2), str):
                    out.add(v[k2])
    norm = set()
    for t in out:
        norm.add(CONTROLLER_ALIASES.get(t, CONTROLLER_ALIASES.get(t.upper(), t)))
    return norm


def controller_pins(rec: dict) -> list:
    """Exact reimplementation of astra_lifecycle._explicit_pins."""
    pins = []
    for key in ("artifact_sha256", "reviewed_sha256", "sha256", "cited_sha256"):
        v = rec.get(key)
        if isinstance(v, str):
            pins.append(v.lower())
    for key in ("target", "artifact"):
        v = rec.get(key)
        if isinstance(v, dict):
            for k2 in ("sha256", "artifact_sha256", "reviewed_sha256"):
                if isinstance(v.get(k2), str):
                    pins.append(v[k2].lower())
    return pins


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


def declared_ref_hashes(rec: dict) -> list:
    """Recursively collect declared/consistency sha256 values (resolution check only)."""
    out = set()

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                kl = k.lower()
                if isinstance(v, str) and "sha256" in kl and ("declared" in kl or "consistency" in kl):
                    out.update(h for h in HEX_RE.findall(v.lower()) if len(h) >= 12)
                walk(v)
        elif isinstance(o, (list, tuple)):
            for x in o:
                walk(x)

    walk(rec)
    return sorted(out)


def norm(rec: dict, channel: str, rid: str, mtime_ns=None) -> dict:
    reviewer = rec.get("reviewer") or rec.get("actor") or "?"
    t, tsrc = record_time(rec, mtime_ns)
    src_mtime = None
    if mtime_ns:
        dt = _dt.datetime.fromtimestamp(mtime_ns / 1e9, _dt.timezone.utc).astimezone(CST)
        src_mtime = tuple(dt.timetuple())[:6]
    declared = sorted({h for _k, v in hash_pin_values(rec)
                       for h in HEX_RE.findall(str(v).lower()) if len(h) >= 12})
    return {
        "rid": rid, "channel": channel, "reviewer": reviewer,
        "verdict": str(rec.get("verdict", "")).lower(),
        "targets": sorted(record_targets(rec) | binding_targets(rec)),
        "bound": sorted(binding_targets(rec)),
        "full": rec.get("counts_as_full_schema_verdict") is not False,
        "gate_accept_flag": rec.get("counts_as_gate_accept") is not False,
        "independent": reviewer not in AUTHORS,
        "time": t, "time_source": tsrc, "source_mtime": src_mtime,
        "created_at": str(rec.get("created_at") or rec.get("reviewed_at")
                          or rec.get("review_clock") or ""),
        "supersedes": supersedes_refs(rec),
        "declared_hashes": declared,
        "declared_ref_hashes": declared_ref_hashes(rec),
        "ctrl_targets": sorted(controller_targets(rec)),
        "ctrl_pins": controller_pins(rec),
        "ctrl_full": rec.get("counts_as_full_schema_verdict") is not False,
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


def controller_scan(records, asof=None):
    """Exact reimplementation of astra_lifecycle.review_coverage() on pinned data."""
    cov = {t: {"verdicts": [], "full_accepts": [], "distinct_accept_reviewers": [],
               "two_distinct_accepts": False} for t in EPOCH}
    for r in records:
        if r["channel"] != "reviews_file":
            continue
        if asof is not None and not (r["time"] is None or r["time"] <= asof):
            continue
        for t in set(r["ctrl_targets"]) & set(EPOCH):
            h = EPOCH[t]
            if not any(prefix_match(p, h) for p in r["ctrl_pins"]):
                continue
            entry = {"rid": r["rid"], "reviewer": r["reviewer"],
                     "verdict": r["verdict"], "full": r["ctrl_full"]}
            cov[t]["verdicts"].append(entry)
            if r["verdict"] == "accept" and r["ctrl_full"]:
                cov[t]["full_accepts"].append(entry)
    for c in cov.values():
        c["distinct_accept_reviewers"] = sorted({a["reviewer"] for a in c["full_accepts"]})
        c["two_distinct_accepts"] = len(c["distinct_accept_reviewers"]) >= 2
    return cov


def brief(r: dict) -> dict:
    return {k: r.get(k) for k in ("rid", "channel", "reviewer", "verdict", "full",
                                  "gate_accept_flag", "independent", "created_at",
                                  "time_source", "retired_by", "duplicate_channels")}


def parse_quote(reason: str):
    q = {}
    for mm in QUOTED_RE.finditer(reason or ""):
        rv = (mm.group(3) or "").replace("'", "")
        q[mm.group(1)] = {"reviewers": rv.split(", ") if rv.strip() else [],
                          "count": int(mm.group(2))}
    return q


def _review_record(d: dict) -> bool:
    return (isinstance(d, dict) and str(d.get("verdict", "")).lower() in VERDICTS
            and d.get("event_type", "review") in (None, "review"))


# ---------------------------------------------------------------- extraction
def extract() -> dict:
    if PIN.exists():
        shutil.rmtree(PIN)
    PIN.mkdir(parents=True)
    created_at = _dt.datetime.now(CST).isoformat(timespec="seconds")
    sources, man_files = {}, {}
    for rel in SOURCE_PATHS:
        p = ROOT / rel
        if not p.exists():
            continue
        st = p.stat()
        sources[rel] = {"sha256": sha256_file(p), "bytes": st.st_size,
                        "mtime_ns": st.st_mtime_ns}
        man_files[rel] = {"sha256": sources[rel]["sha256"], "bytes": st.st_size}

    records, file_sources = [], {}
    for p in sorted((ROOT / "reviews").glob("*.json")):
        raw = p.read_bytes()
        try:
            d = json.loads(raw)
        except Exception:
            continue
        if not _review_record(d):
            continue
        mt = p.stat().st_mtime_ns
        rec = norm(d, "reviews_file", f"file:{p.name}", mt)
        relevant = bool((set(rec["targets"]) & set(EPOCH))
                        or (set(rec["ctrl_targets"]) & set(EPOCH)))
        if not relevant:
            continue
        records.append(rec)
        file_sources[f"reviews/{p.name}"] = {"sha256": sha256_bytes(raw),
                                             "bytes": len(raw), "mtime_ns": mt}

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

    # baseline quote provenance from the controller report (asserted against constants)
    report = ROOT / BASELINE_REPORT
    prov_src = "frozen_constant"
    reason = BASELINE_GFORM_REASON
    report_sha = None
    map_after = None
    label = None
    if report.exists():
        rb = report.read_bytes()
        report_sha = sha256_bytes(rb)
        ctrl = json.loads(rb)
        label = ctrl.get("label")
        map_after = ctrl.get("map_sha256_after")
        if report_sha == BASELINE_REPORT_SHA:
            reason = (ctrl.get("controller_gate_audit", {}).get("G-FORM", {})
                      or {}).get("reason") or reason
            prov_src = BASELINE_REPORT
    frozen = {
        "provenance_source": prov_src,
        "controller_report": BASELINE_REPORT,
        "controller_report_sha256": BASELINE_REPORT_SHA,
        "controller_report_measured_sha256": report_sha,
        "controller_report_label": BASELINE_LABEL,
        "controller_report_label_measured": label,
        "map_sha256_after": BASELINE_MAP_AFTER,
        "map_sha256_after_measured": map_after,
        "checked_at": "2026-09-12T01:01:17+08:00",
        "gform_reason": reason,
        "gform_reason_sha256": sha256_bytes(reason.encode()),
        "gform_quoted": parse_quote(reason),
        "measured_hashes": dict(EPOCH),
        "hash_assertions": {
            "gform_reason_matches_constant":
                sha256_bytes(reason.encode()) == BASELINE_GFORM_REASON_SHA,
            "controller_report_matches_constant":
                (not report.exists()) or report_sha == BASELINE_REPORT_SHA,
            "parsed_quote_matches_expected": {
                k: parse_quote(reason).get(k, {}).get("reviewers", [])
                for k in EXPECTED_QUOTE} == EXPECTED_QUOTE,
        },
    }
    froz = json.loads((ROOT / "artifacts/formulation/FROZEN.json").read_text())
    frozen["frozen_manifest"] = {
        "path": "artifacts/formulation/FROZEN.json",
        "sha256": EPOCH_FROZEN_SHA,
        "measured_sha256": sha256_file(ROOT / "artifacts/formulation/FROZEN.json"),
        "revision": EPOCH_FROZEN_REV,
        "revision_measured": froz.get("revision"),
        "frozen_at": "2026-09-12T00:57:26+08:00",
        "frozen_at_measured": froz.get("frozen_at"),
        "pins_match_epoch": all(
            froz["files"].get({
                "F1": "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
                "F2a": "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
                "F2b": "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"}[t], {})
                .get("sha256") == h for t, h in EPOCH.items()),
    }
    live_map = json.loads((ROOT / "research_map/research_map.json").read_text())
    lga = live_map.get("controller_gate_audit", {}).get("G-FORM") or {}
    live_quote = {
        "source": "research_map/research_map.json",
        "map_updated_at": live_map.get("updated_at"),
        "checked_at": lga.get("checked_at"),
        "reason": lga.get("reason", ""),
        "reason_sha256": sha256_bytes((lga.get("reason", "")).encode()),
        "quoted": parse_quote(lga.get("reason", "")),
    }
    quoted_doc = {
        "task_id": TASK_ID,
        "baseline": frozen,
        "current_live": live_quote,
        "extraction_instant": created_at,
        "rules": "see ledger.py docstring; semantics inherited from " + PRIOR_TOOL,
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
        "controller_tool": CONTROLLER_TOOL, "controller_tool_sha256": CONTROLLER_TOOL_SHA,
        "files": {"records.json": {"sha256": h("records.json")},
                  "quoted.json": {"sha256": h("quoted.json")},
                  "sources.json": {"sha256": h("sources.json")}},
        "source_files": man_files,
        "quote_provenance": {
            "controller_report": BASELINE_REPORT,
            "controller_report_sha256": BASELINE_REPORT_SHA,
            "gform_reason_sha256": frozen["gform_reason_sha256"],
            "frozen_manifest_sha256": EPOCH_FROZEN_SHA,
            "assertions": frozen["hash_assertions"],
        },
    }
    (PIN / "MANIFEST.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    return {"records": len(records), "event_review_records": ev_records,
            "quoted": frozen["gform_quoted"], "assertions": frozen["hash_assertions"]}


# ---------------------------------------------------------------- controls
def control_suite(base, quoted_doc) -> dict:
    """Synthetic + material, fail-closed controls on the extracted rule implementation."""
    out = {}

    def mk(rid, reviewer, verdict, target, t, **kw):
        r = {"rid": rid, "channel": kw.pop("channel", "accepted_event"),
             "reviewer": reviewer, "verdict": verdict, "targets": [target],
             "bound": [target], "full": True, "gate_accept_flag": True,
             "independent": True, "time": t, "time_source": "created_at",
             "created_at": "", "supersedes": [], "raw_keys": [],
             "declared_hashes": [], "ctrl_targets": [], "ctrl_pins": [], "ctrl_full": True}
        r.update(kw)
        return r

    A = (2026, 9, 12, 1, 1, 0)
    B = (2026, 9, 12, 1, 2, 0)

    # C01 two-channel finds an event-only accept that a file-only scan misses
    recs = [mk("event:e1", "wA", "accept", "F2b", A)]
    two = operative(recs, "F2b", EPOCH["F2b"], asof=None)
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
    out["C03_S2_later_same_reviewer_retires_accept"] = (
        operative(recs, "F1", EPOCH["F1"], asof=None)["full_independent_accept_reviewers"] == [])

    # C04 S2 symmetric: later accept retires earlier revise
    recs = [mk("event:a", "wE", "revise", "F1", A),
            mk("event:b", "wE", "accept", "F1", B, supersedes=[])]
    out["C04_S2_later_accept_retires_revise"] = (
        operative(recs, "F1", EPOCH["F1"], asof=None)["full_independent_accept_reviewers"] == ["wE"])

    # C05 evidence_refs alone never bind
    d = mk("event:x", "wF", "accept", "F1", A)
    d["bound"] = []
    out["C05_evidence_refs_alone_do_not_bind"] = (
        operative([d], "F1", EPOCH["F1"], asof=None)["full_independent_accept_reviewers"] == [])

    # C06 context pin does not bind a sibling class
    ctx = {"artifact_sha256": EPOCH["F2a"], "cross_artifact": {"F2b": {"sha256": EPOCH["F2b"]}}}
    out["C06_context_pin_does_not_bind"] = binding_targets(ctx) == {"F2a"}

    # C07 as-of excludes post-quote records
    recs = [mk("event:p", "wG", "accept", "F1", B)]
    out["C07_asof_excludes_post_quote"] = (
        operative(recs, "F1", EPOCH["F1"], asof=BASELINE_AT)["full_independent_accept_reviewers"] == []
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
        two["full_independent_accept_reviewers"] == ["wJ"] and len(two["operative"]) == 1)

    # C12 target_sha256 is a binding pin (worker-080 pattern)
    recs = [mk("event:t", "wK", "accept", "F1", A, declared_hashes=[EPOCH["F1"]])]
    out["C12_target_sha256_binds"] = binding_targets({"target_sha256": EPOCH["F1"]}) == {"F1"}

    # C13 material F2b: worker-061's event-only accept is the only full accept
    f2b = operative(base, "F2b", EPOCH["F2b"], asof=None)["full_independent_accept_reviewers"]
    without = [r for r in base if not (r["verdict"] == "accept"
                                       and "F2b" in r["bound"]
                                       and r["reviewer"] == "worker-061")]
    n_wo = len(operative(without, "F2b", EPOCH["F2b"], asof=None)["full_independent_accept_reviewers"])
    out["C13_f2b_single_event_only_accept_material"] = (f2b == ["worker-061"] and n_wo == 0)

    # C14 material F1: criterion met, and restricting to one accept reviewer flips it
    f1 = operative(base, "F1", EPOCH["F1"], asof=None)["full_independent_accept_reviewers"]
    keep1 = sorted(f1)[0] if f1 else None
    restr = [r for r in base if not (r["verdict"] == "accept" and "F1" in r["bound"]
                                     and r["reviewer"] != keep1)]
    n1 = len(operative(restr, "F1", EPOCH["F1"], asof=None)["full_independent_accept_reviewers"])
    out["C14_f1_two_accept_criterion_material"] = (len(f1) >= 2 and n1 == 1)

    # C15 material F2a: criterion met, and restricting to one accept reviewer flips it
    f2a = operative(base, "F2a", EPOCH["F2a"], asof=None)["full_independent_accept_reviewers"]
    keep2 = sorted(f2a)[0] if f2a else None
    restr2 = [r for r in base if not (r["verdict"] == "accept" and "F2a" in r["bound"]
                                      and r["reviewer"] != keep2)]
    n2 = len(operative(restr2, "F2a", EPOCH["F2a"], asof=None)["full_independent_accept_reviewers"])
    out["C15_f2a_two_accept_criterion_material"] = (len(f2a) >= 2 and n2 == 1)

    # C16 controller scan vs two-channel on real pinned data: F2b gap + F1 event/target gaps
    cs = controller_scan(base)
    f1_missing = sorted(set(f1) - set(cs["F1"]["distinct_accept_reviewers"]))
    out["C16_controller_scan_channel_and_target_gaps"] = (
        cs["F2b"]["distinct_accept_reviewers"] == [] and f2b == ["worker-061"]
        and "worker-080" in f1_missing and "worker-089" in f1_missing)

    # C17 baseline provenance: reason hash + parsed quote match constants
    b = quoted_doc["baseline"]
    out["C17_baseline_quote_provenance"] = (
        b["gform_reason_sha256"] == BASELINE_GFORM_REASON_SHA
        and {k: b["gform_quoted"].get(k, {}).get("reviewers", [])
             for k in EXPECTED_QUOTE} == EXPECTED_QUOTE
        and all(b["hash_assertions"].values()))

    # C18 FROZEN rev29 predates the baseline quote and pins the epoch hashes
    fm = b["frozen_manifest"]
    out["C18_frozen_rev29_pins_epoch_before_quote"] = (
        fm["sha256"] == EPOCH_FROZEN_SHA and fm["measured_sha256"] == EPOCH_FROZEN_SHA
        and fm["revision_measured"] == EPOCH_FROZEN_REV and fm["pins_match_epoch"]
        and _ts(fm["frozen_at_measured"]) is not None
        and _ts(fm["frozen_at_measured"]) <= BASELINE_AT)

    # C19 manifest tamper is detected (self-hash check)
    man = json.loads((PIN / "MANIFEST.json").read_text())
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        for f in ("records.json", "quoted.json", "sources.json"):
            shutil.copy(PIN / f, td / f)
        (td / "records.json").write_text((td / "records.json").read_text() + " ")
        drift = [f for f, meta in man["files"].items()
                 if sha256_file(td / f) != meta["sha256"]]
    out["C19_manifest_tamper_detected"] = drift == ["records.json"]

    return {k: {"pass": bool(v), "detail": str(v)} for k, v in out.items()}


# ---------------------------------------------------------------- main
def manifest_drift(manifest) -> list:
    bad = []
    for f, meta in manifest["files"].items():
        if not (PIN / f).exists() or sha256_file(PIN / f) != meta["sha256"]:
            bad.append(f)
    return bad


def resolve_declared(records) -> dict:
    """Resolve every non-epoch hash cited by the operative freeze accepts."""
    known = {}
    for rel in RESOLUTION_MAP_PATHS:
        p = ROOT / rel
        if not p.exists():
            continue
        known[sha256_file(p)] = rel
    froz = json.loads((ROOT / "artifacts/formulation/FROZEN.json").read_text())
    for rel, meta in froz.get("files", {}).items():
        if meta.get("sha256"):
            known.setdefault(meta["sha256"], rel)
    unresolved, resolved = {}, {}
    for r in records:
        for h in set(r["declared_hashes"]) | set(r.get("declared_ref_hashes", [])):
            if h in EPOCH.values():
                continue
            if h in known:
                resolved.setdefault(h, set()).add(known[h])
            else:
                unresolved.setdefault(h, []).append(r["rid"])
    return {"resolved": {h: sorted(v) for h, v in sorted(resolved.items())},
            "unresolved": {h: sorted(set(v)) for h, v in sorted(unresolved.items())}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--extract", action="store_true")
    args = ap.parse_args()
    if args.extract:
        info = extract()
        print(json.dumps(info, indent=1, sort_keys=True))
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

    live_drift = []
    for rel, meta in manifest["source_files"].items():
        p = ROOT / rel
        if not p.exists() or sha256_file(p) != meta["sha256"]:
            live_drift.append({"path": rel, "pinned": meta["sha256"],
                               "live": sha256_file(p) if p.exists() else None})

    analysis, channels = {}, {}
    freeze_objs = {}
    cs_freeze = controller_scan(recs, asof=None)
    cs_base = controller_scan(recs, asof=BASELINE_AT)
    for t, h in EPOCH.items():
        freeze = operative(recs, t, h, asof=None)
        freeze_objs[t] = freeze
        at_base = operative(recs, t, h, asof=BASELINE_AT)
        post = operative([r for r in recs if (r["time"] or (0,) * 6) > EPOCH_FROZEN_AT],
                         t, h, asof=None)
        file_only = operative([r for r in recs if r["channel"] == "reviews_file"],
                              t, h, asof=None)
        q = (quoted_doc["baseline"]["gform_quoted"].get(t) or {})
        analysis[t] = {
            "epoch_sha256": h,
            "baseline_quote": {"reviewers": q.get("reviewers", []), "count": q.get("count")},
            "freeze": {
                "instant": quoted_doc["extraction_instant"],
                "full_independent_accept_reviewers": freeze["full_independent_accept_reviewers"],
                "gate_accept_reviewers": freeze["gate_accept_reviewers"],
                "two_distinct_full": len(freeze["full_independent_accept_reviewers"]) >= 2,
                "two_distinct_gate": len(freeze["gate_accept_reviewers"]) >= 2,
                "by_verdict": freeze["by_verdict"],
                "operative": [brief(r) for r in freeze["operative"]],
                "retired": [brief(r) for r in freeze["retired"]],
            },
            "controller_scan_at_freeze": {
                "distinct_accept_reviewers": cs_freeze[t]["distinct_accept_reviewers"],
                "two_distinct_accepts": cs_freeze[t]["two_distinct_accepts"],
                "accepts": cs_freeze[t]["full_accepts"],
            },
            "controller_scan_at_baseline": {
                "distinct_accept_reviewers": cs_base[t]["distinct_accept_reviewers"],
            },
            "two_channel_at_baseline": {
                "instant": "2026-09-12T01:01:17+08:00",
                "full_independent_accept_reviewers": at_base["full_independent_accept_reviewers"],
                "gate_accept_reviewers": at_base["gate_accept_reviewers"],
            },
            "two_channel_file_only_at_freeze": {
                "full_independent_accept_reviewers": file_only["full_independent_accept_reviewers"],
            },
            "post_frozen_publication": {
                "instant": "2026-09-12T00:57:26+08:00",
                "full_independent_accept_reviewers": post["full_independent_accept_reviewers"],
                "gate_accept_reviewers": post["gate_accept_reviewers"],
            },
            "delta_controller_vs_two_channel_freeze": {
                "missing_from_controller": sorted(
                    set(freeze["full_independent_accept_reviewers"])
                    - set(cs_freeze[t]["distinct_accept_reviewers"])),
                "extra_in_controller": sorted(
                    set(cs_freeze[t]["distinct_accept_reviewers"])
                    - set(freeze["full_independent_accept_reviewers"])),
            },
        }
        channels[t] = {
            "file_records_considered": file_only["records_considered"],
            "two_channel_records_considered": freeze["records_considered"],
            "event_only_full_accepts": sorted(
                set(freeze["full_independent_accept_reviewers"])
                - set(file_only["full_independent_accept_reviewers"])),
        }

    freeze_full = {t: analysis[t]["freeze"]["full_independent_accept_reviewers"] for t in EPOCH}
    freeze_gate = {t: analysis[t]["freeze"]["gate_accept_reviewers"] for t in EPOCH}
    criterion = {
        "reading": ("distinct non-author reviewers with a full-schema accept "
                    "(counts_as_full_schema_verdict is not False) bound to the measured "
                    "hash and operative under S1/S2; the counting rule published in the "
                    "G-F0 pass reason"),
        "two_distinct_met_full_view": {t: len(freeze_full[t]) >= 2 for t in EPOCH},
        "two_distinct_met_gate_view": {t: len(freeze_gate[t]) >= 2 for t in EPOCH},
        "quoted_counts": {t: analysis[t]["baseline_quote"]["count"] for t in EPOCH},
        "note": ("worker measurement only; whether counts_as_gate_accept=false records "
                 "count, and any gate verdict, remain controller/lead-audit decisions"),
    }

    # in-place amendment audit: file records whose created_at and source mtime disagree
    def _epoch_seconds(t):
        return _dt.datetime(*t[:6]).timestamp() if t else None

    amend = []
    operative_at_freeze = {r["rid"]: r for t in EPOCH for r in freeze_objs[t]["operative"]}
    for r in operative_at_freeze.values():
        if r["channel"] != "reviews_file" or not r.get("source_mtime"):
            continue
        t_c = _ts(r["created_at"])
        if t_c and abs(_epoch_seconds(t_c) - _epoch_seconds(r["source_mtime"])) > 60:
            amend.append({"rid": r["rid"], "reviewer": r["reviewer"],
                          "verdict": r["verdict"], "created_at": r["created_at"],
                          "source_mtime": list(r["source_mtime"])})
    operative_accepts = []
    for t in EPOCH:
        for r in freeze_objs[t]["operative"]:
            if r["verdict"] == "accept" and r["full"] and r["independent"]:
                operative_accepts.append(r)
    resolution = resolve_declared(operative_accepts)

    # quoted reviewers whose accept content is absent from the pinned corpus
    quoted_without_pinned_accept = {}
    for t in EPOCH:
        quoted = analysis[t]["baseline_quote"]["reviewers"]
        pinned_accepts = {r["reviewer"] for r in recs
                          if t in r["targets"] and t in r["bound"]
                          and r["verdict"] == "accept" and r["full"] and r["independent"]}
        quoted_without_pinned_accept[t] = sorted(set(quoted) - pinned_accepts)

    missing_map = {t: analysis[t]["delta_controller_vs_two_channel_freeze"]["missing_from_controller"]
                   for t in EPOCH}
    extra_map = {t: analysis[t]["delta_controller_vs_two_channel_freeze"]["extra_in_controller"]
                 for t in EPOCH}
    event_only = {t: channels[t]["event_only_full_accepts"] for t in EPOCH}

    findings = [
        {"id": "W033-R29-HF-01", "severity": "hard",
         "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
         "finding": (
             "Controller scan vs two-channel operative set at the freeze instant is not "
             f"equal for any class. missing_from_controller={missing_map}; "
             f"event-only full accepts={event_only}. The scan is file-channel only "
             "(astra_lifecycle.review_coverage() lines 185-207), so every accept that "
             "exists only in the accepted event stream is invisible; the target map "
             "(_targets_in_review lines 144-157) also drops path#hash target_id forms."),
         "evidence_refs": ["research_map/astra_lifecycle.py#032d4afcb061",
                           "artifacts/worker-033/gform_r29_ledger/pinned/records.json",
                           "artifacts/worker-033/gform_r29_ledger/report.json"]},
        {"id": "W033-R29-HF-02", "severity": "hard", "class_ids": ["AF-SCC-C0-VAC-GEN"],
         "finding": (
             "F2b at the frozen bytes has exactly one full-schema independent accept, "
             "worker-061 (event-only, 00:54:27, reviewed_sha256=artifact_sha256="
             "b2ab6acb2bbe), which the controller scan reports as 0. F2b therefore still "
             "fails the two-distinct-accept criterion under both the full and the gate "
             "view, but the published quote hides the only accept it has."),
         "evidence_refs": ["research_map/events.jsonl#w061-varstrength-20260912T0055-review-f2b",
                           "artifacts/worker-033/gform_r29_ledger/report.json"]},
        {"id": "W033-R29-HF-03", "severity": "hard",
         "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
         "finding": (
             "Two accepts quoted at 01:01:17 have no accept content in the pinned corpus: "
             f"quoted_without_pinned_accept={quoted_without_pinned_accept} (worker-045 F1 "
             "and worker-075 F2a). The pinned bytes for those paths are revise records "
             "created after the quote (01:01:45 / 01:01:37), so the quoted accept states "
             "were either amended in place with no separate path or the quote was wrong; "
             "from the frozen corpus alone the quoted set is not reproducible. The quote "
             "also omits worker-089 (F1 accept, target_id "
             "'schemas/af_wcc_vacuum.yaml#d9cebb9404b2' unmapped by _targets_in_review) "
             "and worker-038/worker-080 (F1 event-only accepts)."),
         "evidence_refs": ["runtime/state/controller_verification/lifecycle_20260912-010117.json",
                           "reviews/F1-review-worker-045.json",
                           "reviews/F2a-review-rev29-075.json",
                           "reviews/F1-review-worker-089.json",
                           "research_map/astra_lifecycle.py#032d4afcb061"]},
        {"id": "W033-R29-POS-04", "severity": "info",
         "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
         "finding": (
             "At the frozen bytes the two-distinct-accept criterion is met in the full "
             f"view for F1 ({freeze_full['F1']}) and F2a ({freeze_full['F2a']}) and is "
             f"not met for F2b ({freeze_full['F2b']}). This is a worker bookkeeping "
             "measurement, not a gate verdict; the gate-accept view is reported "
             f"separately (F1={freeze_gate['F1']}, F2a={freeze_gate['F2a']}, "
             f"F2b={freeze_gate['F2b']})."),
         "evidence_refs": ["artifacts/worker-033/gform_r29_ledger/report.json"]},
        {"id": "W033-R29-INFO-05", "severity": "info",
         "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
         "finding": (
             "In-place amendment is a reproducibility hazard independent of the channel "
             "gap: file records whose created_at and true source mtime disagree by >60 s "
             f"are listed in the report ({len(amend)} at freeze, e.g. worker-002 F1 and "
             "worker-073 F1). Because a review file is rewritten at the same path, a "
             "post-hoc snapshot cannot reconstruct the file corpus as of an earlier "
             "controller quote; the accepted event stream is the durable record."),
         "evidence_refs": ["artifacts/worker-033/gform_r29_ledger/report.json",
                           "runtime/state/controller_verification/lifecycle_20260912-010117.json"]},
        {"id": "W033-R29-INFO-06", "severity": "info",
         "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
         "finding": (
             "Binding-integrity cross-check on the operative freeze accepts only: declared "
             f"non-epoch hashes resolve on disk ({sorted(resolution['resolved'])}) with "
             f"{len(resolution['unresolved'])} unresolved. The rev13/rev29 declared F0 "
             "binding 0abb9ed8a961 (canonical taxonomy) and consistency evidence "
             "9e335e9ba1bf both resolve, i.e. the HF-086-R1 declared-hash gap is repaired "
             "at these bytes."),
         "evidence_refs": ["artifacts/formulation/FROZEN.json#815e08079aef",
                           "research_map/formulation_taxonomy.yaml#0abb9ed8a961",
                           "artifacts/formulation/evidence/taxonomy_consistency.json"]},
    ]

    controls = control_suite(recs, quoted_doc)
    n_fail = sum(1 for c in controls.values() if not c["pass"])
    report = {
        "task_id": TASK_ID, "worker": "worker-033",
        "scope": "accept-set bookkeeping only; worker-level measurement, not a gate verdict",
        "rules_source": {"derived_from": PRIOR_TOOL, "sha256": PRIOR_TOOL_SHA,
                         "controller_tool": CONTROLLER_TOOL,
                         "controller_tool_sha256": CONTROLLER_TOOL_SHA},
        "epoch": EPOCH,
        "frozen_manifest": quoted_doc["baseline"]["frozen_manifest"],
        "baseline_quote": quoted_doc["baseline"],
        "current_live_quote": quoted_doc["current_live"],
        "extraction_instant": quoted_doc["extraction_instant"],
        "analysis": analysis,
        "channels": channels,
        "criterion": criterion,
        "quoted_without_pinned_accept": quoted_without_pinned_accept,
        "in_place_amendment_candidates": amend,
        "declared_hash_resolution": resolution,
        "findings": findings,
        "controls": {"total": len(controls), "failed": n_fail, "all_passed": n_fail == 0},
        "pinned": {"manifest_sha256": sha256_file(PIN / "MANIFEST.json"),
                   "records_sha256": sha256_file(PIN / "records.json"),
                   "quoted_sha256": sha256_file(PIN / "quoted.json"),
                   "sources_sha256": sha256_file(PIN / "sources.json"),
                   "source_file_count": len(manifest["source_files"])},
        "live_source_drift": live_drift,
        "falsifier": (
            "Re-run ledger.py on the pinned snapshot; controls fail-closed. The report is "
            "falsified if any of: the two-channel operative set at freeze equals the "
            "controller-scan set for all three classes (no channel/target gap exists on "
            "the pinned corpus); worker-061's F2b accept at b2ab6acb2bbe is withdrawn, "
            "superseded by a later binding verdict from worker-061, or shown not to bind "
            "that hash; a second independent full-schema F2b accept lands inside the "
            "pinned snapshot; F1 or F2a falls below two operative full accepts; the live "
            "schemas move off d9cebb9404b2/e9a27996dfd3/b2ab6acb2bbe; worker-088/089/080 "
            "records are shown absent from the pinned corpus; or the pinned FROZEN "
            "rev29/baseline-report/reason hashes differ from their constants."),
        "not_claimed": [
            "no gate verdict, no node status=done, no validation_status=passed",
            "no theorem, no physics, no adjudication of substantive F1/F2a/F2b findings",
            "no review of schema semantics; the gate-flag dispute is left to lead-audit",
        ],
        "generated_at": _dt.datetime.now(CST).isoformat(timespec="seconds"),
    }
    (TASK / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    (TASK / "controls.json").write_text(json.dumps(
        {"task_id": TASK_ID, "total": len(controls), "failed": n_fail,
         "all_passed": n_fail == 0, "controls": controls},
        indent=1, sort_keys=True) + "\n")
    (TASK / "run.log").write_text(
        f"{report['generated_at']} {TASK_ID} controls={len(controls)} failed={n_fail}\n"
        f"  freeze_full={json.dumps(freeze_full)}\n"
        f"  freeze_gate={json.dumps(freeze_gate)}\n"
        f"  controller_at_freeze={json.dumps({t: analysis[t]['controller_scan_at_freeze']['distinct_accept_reviewers'] for t in EPOCH})}\n"
        f"  missing_from_controller={json.dumps(missing_map)}\n"
        f"  live_source_drift={json.dumps(live_drift)}\n")
    print(json.dumps({"task_id": TASK_ID, "controls_failed": n_fail,
                      "freeze_full_accepts": freeze_full,
                      "freeze_gate_accepts": freeze_gate,
                      "controller_at_freeze": {t: analysis[t]["controller_scan_at_freeze"]["distinct_accept_reviewers"] for t in EPOCH},
                      "missing_from_controller": missing_map,
                      "two_distinct_met_full": criterion["two_distinct_met_full_view"],
                      "live_source_drift": len(live_drift)}, indent=1))
    return 2 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
