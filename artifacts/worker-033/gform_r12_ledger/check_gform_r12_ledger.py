#!/usr/bin/env python3
"""W033-GFORM-R12-LEDGER-01 — operative G-FORM accept sets at the rev12 epoch.

Question
--------
At the rev12 G-FORM epoch (F1 cce9c60146d6 / F2a 5476a3f2c6bc / F2b 55d0a1ea9bda)
the controller gate audit quoted accept sets at ``checked_at`` = 2026-09-12T00:43:08.
Are those quotes reproducible from the pinned two-channel corpus (``reviews/*.json``
files + the accepted ``research_map/events.jsonl`` stream) once every record is
(a) hash-bound to the quoted epoch, (b) full-schema, (c) from a non-author, and
(d) still *operative* under explicit supersession?

Why this is not the controller's scan
-------------------------------------
``astra_lifecycle.review_coverage`` reads only ``reviews/*.json`` and takes every
file's verdict at face value.  It therefore cannot see:
  * a withdrawn accept whose file still says accept (false positive), or
  * an accept that exists only in the accepted event stream (false negative).
Both failure modes are measured here on one pinned snapshot.

Rules (fixed before measurement)
--------------------------------
Binding     : a record binds target T at epoch E iff a hash-bearing field outside
              the prose set (evidence_refs/artifact_refs/findings/scope/summary/
              falsifier/notes/...) contains the epoch hash with >=12 hex prefix.
              ``evidence_refs`` never bind.
Target      : identity tokens (target_id/node_id/artifact/target/class_id/
              class_ids) map to F1/F2a/F2b; a unique epoch hash also identifies
              its target implicitly (target_id may embed the hash).
Full        : counts_as_full_schema_verdict is not False.
Independent : reviewer is not in the target author set.
Gate accept : counts_as_gate_accept is not False.  The full-schema-accept view
              ignores this flag; both sets are reported side by side.
S1          : a record named by a later record's supersedes reference retires it.
S2          : within (target, epoch, reviewer), the latest created_at (ties by
              record id) retires every earlier verdict that differs.
Duplicate   : same reviewer + target + epoch + verdict over two channels is
              deduplicated, not treated as a supersession.
As-of       : a record is counted as-of the quote when its created_at <= quote
              instant; a file record without created_at uses its pinned mtime.
              Records after the instant are reported separately as deltas.

Exit status: 0 all controls pass; 2 a control failed (fail-closed); 3 pinned
manifest drift.  Read-only on canonical paths; worker-level measurement, not a
gate verdict and not a node completion.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

TASK = Path(__file__).resolve().parent
PIN = TASK / "pinned"
ROOT = Path(__file__).resolve().parents[3]

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


def walk_hash_fields(v, key="", out=None):
    """Yield (key_path, scalar) for hash-bearing, non-prose fields."""
    if out is None:
        out = []
    if key.split(".")[-1].lower() in PROSE_KEYS:
        return out
    if isinstance(v, dict):
        for k, x in v.items():
            walk_hash_fields(x, f"{key}.{k}" if key else k, out)
    elif isinstance(v, (list, tuple)):
        for x in v:
            walk_hash_fields(x, key, out)
    else:
        out.append((key, v))
    return out


def prefix_match(value: str, h: str) -> bool:
    if not isinstance(value, str):
        return False
    for tok in HEX_RE.findall(value.lower()):
        if len(tok) >= 12 and (h.startswith(tok) or tok.startswith(h[:len(tok)])):
            return True
    return False


def hash_pin_values(rec: dict):
    """Yield (path, value) for target-pin fields only.

    Context pins (e.g. cross_artifact.F2a.sha256 inside an F1 review) must not
    bind this record to a sibling class, so only whitelisted top-level pin keys
    and the same keys inside explicit container fields are read.
    """
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
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})", s or "")
    if not m:
        return None
    return tuple(int(x) for x in m.groups())


def record_time(rec: dict, mtime_ns=None):
    for k in ("created_at", "reviewed_at", "review_clock", "_received_at"):
        t = _ts(rec.get(k))
        if t:
            return t, k
    if mtime_ns:
        import datetime
        dt = datetime.datetime.fromtimestamp(mtime_ns / 1e9,
                                             datetime.timezone.utc).astimezone(
            datetime.timezone(datetime.timedelta(hours=8)))
        return tuple(dt.timetuple())[:6], "mtime"
    return None, None


def norm(rec: dict, channel: str, rid: str, mtime_ns=None) -> dict:
    verdict = str(rec.get("verdict", "")).lower()
    t, tsrc = record_time(rec, mtime_ns)
    return {
        "rid": rid, "channel": channel,
        "reviewer": rec.get("reviewer") or rec.get("actor") or "?",
        "verdict": verdict,
        "targets": sorted(record_targets(rec) | binding_targets(rec)),
        "bound": sorted(binding_targets(rec)),
        "full": rec.get("counts_as_full_schema_verdict") is not False,
        "gate_accept_flag": rec.get("counts_as_gate_accept") is not False,
        "independent": (rec.get("reviewer") or rec.get("actor")) not in AUTHORS,
        "time": t, "time_source": tsrc,
        "created_at": rec.get("created_at") or rec.get("reviewed_at")
                      or rec.get("review_clock") or "",
        "supersedes": supersedes_refs(rec),
        "raw_keys": sorted(rec.keys())[:24],
    }


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


def load_corpus(manifest: dict):
    records, prov = [], {"review_files": 0, "event_review_records": 0,
                         "event_lines": 0, "non_review_files": []}
    mfiles = manifest["files"]
    snapshot_ns = None
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})",
                 manifest.get("created_at", ""))
    if m:
        import datetime
        dt = datetime.datetime(*[int(x) for x in m.groups()],
                               tzinfo=datetime.timezone(
                                   datetime.timedelta(hours=8)))
        snapshot_ns = int(dt.timestamp() * 1e9)
    rdir = PIN / "reviews"
    for p in sorted(rdir.glob("*.json")) if rdir.is_dir() else []:
        rel = f"reviews/{p.name}"
        try:
            d = json.loads(p.read_text())
        except Exception:
            prov["non_review_files"].append(rel)
            continue
        if not isinstance(d, dict) or str(d.get("verdict", "")).lower() not in VERDICTS:
            prov["non_review_files"].append(rel)
            continue
        mt = mfiles.get(rel, {}).get("mtime_ns")
        if mt and snapshot_ns and mt >= snapshot_ns - 5_000_000_000:
            # copy time, not creation time: unknown, do not use as a clock
            mt = None
        records.append(norm(d, "reviews_file", f"file:{p.name}", mt))
        prov["review_files"] += 1
    ev = PIN / "events.jsonl"
    if ev.is_file():
        for i, line in enumerate(ev.read_text(errors="ignore").splitlines(), 1):
            line = line.strip()
            if not line.startswith("{"):
                continue
            prov["event_lines"] = i
            try:
                d = json.loads(line)
            except Exception:
                continue
            if d.get("event_type") != "review":
                continue
            if str(d.get("verdict", "")).lower() not in VERDICTS:
                continue
            records.append(norm(d, "accepted_event", f"event:{d.get('event_id') or i}"))
            prov["event_review_records"] += 1
    return records, prov


def retired_by(records):
    """Return rid -> retiring ref for S1 (named supersession)."""
    retired = {}
    for r in records:
        for ref in r["supersedes"]:
            for other in records:
                if other is r:
                    continue
                cand = {other["rid"], other["rid"].split(":", 1)[-1]}
                if ref in cand or (ref.endswith(".json") and
                                   other["rid"].endswith(ref.split("/")[-1])):
                    retired.setdefault(other["rid"], []).append(
                        {"by": r["rid"], "rule": "S1_named_supersedes"})
    return retired


def dedup(records):
    """Collapse only the same verdict re-published over two channels.

    The dedup key includes the record time so that a later verdict from the
    same reviewer at the same hash is never folded into an earlier one.
    """
    groups = {}
    for r in records:
        key = (r["reviewer"], tuple(r["targets"]), tuple(r["bound"]),
               r["verdict"], r["time"])
        groups.setdefault(key, []).append(r)
    out = []
    for _key, group in groups.items():
        group.sort(key=lambda x: (x["channel"] != "reviews_file", x["rid"]))
        primary = group[0]
        primary["duplicate_channels"] = sorted(g["channel"] for g in group[1:])
        out.append(primary)
    return sorted(out, key=lambda x: (x["time"] or (0,) * 6, x["rid"]))


def operative(records, target, epoch, asof=None):
    """Operative records for target+epoch; asof filters created <= instant."""
    rel = [dict(r) for r in records
           if target in r["targets"] and target in r["bound"]]
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
        if cur is None or (r["time"] or (0,) * 6, r["rid"]) > (cur["time"] or (0,) * 6, cur["rid"]):
            latest[k] = r
    for r in kept:
        k = (r["reviewer"], target, epoch)
        if latest[k] is not r:
            r["retired_by"] = [{"by": latest[k]["rid"], "rule": "S2_latest_by_reviewer"}]
            continue
    operative = [r for r in kept if "retired_by" not in r]
    accepts = [r for r in operative if r["verdict"] == "accept"]
    full_indep = [r for r in accepts if r["full"] and r["independent"]]
    gate = [r for r in full_indep if r["gate_accept_flag"]]
    return {
        "records_considered": len(rel),
        "asof": asof is not None,
        "operative": operative,
        "full_independent_accept_reviewers": sorted(r["reviewer"] for r in full_indep),
        "gate_accept_reviewers": sorted(r["reviewer"] for r in gate),
        "retired": [r for r in rel if "retired_by" in r],
        "by_verdict": {v: sorted(r["reviewer"] for r in rel if r["verdict"] == v)
                       for v in sorted({r["verdict"] for r in rel})},
    }


def control_suite():
    """Synthetic records pushed through the production functions."""
    C = {}
    base = dict(event_type="review", gate="G-FORM", counts_as_full_schema_verdict=True)
    h = EPOCH["F1"]
    recs = [
        dict(base, event_id="c1a", reviewer="r1", verdict="accept",
             created_at="2026-09-12T00:01:00+08:00", artifact_sha256=h, node_id="F1"),
        dict(base, event_id="c1b", reviewer="r1", verdict="revise",
             created_at="2026-09-12T00:02:00+08:00", artifact_sha256=h, node_id="F1"),
    ]
    op = operative([norm(r, "accepted_event", f"event:{r['event_id']}") for r in recs],
                   "F1", h)
    C["C1_latest_wins_retires_accept"] = (
        "PASS" if op["gate_accept_reviewers"] == [] and len(op["retired"]) == 1 else "FAIL")

    recs = [
        dict(base, event_id="c2a", reviewer="r2", verdict="accept",
             created_at="2026-09-12T00:01:00+08:00", artifact_sha256=h, node_id="F1"),
        dict(base, event_id="c2b", reviewer="r3", verdict="revise",
             created_at="2026-09-12T00:02:00+08:00", artifact_sha256=h, node_id="F1",
             supersedes={"event_id": "c2a"}),
    ]
    op = operative([norm(r, "accepted_event", f"event:{r['event_id']}") for r in recs],
                   "F1", h)
    C["C2_named_supersedes_retires_accept"] = (
        "PASS" if op["gate_accept_reviewers"] == [] else "FAIL")

    recs = [dict(base, event_id="c3", reviewer="r4", verdict="accept",
                 created_at="2026-09-12T00:01:00+08:00",
                 artifact_sha256=EPOCH["F2a"], node_id="F1")]
    op = operative([norm(r, "accepted_event", "event:c3") for r in recs], "F1", h)
    C["C3_other_hash_does_not_bind"] = "PASS" if op["gate_accept_reviewers"] == [] else "FAIL"

    recs = [dict(base, event_id="c4", reviewer="r5", verdict="accept",
                 created_at="2026-09-12T00:01:00+08:00", node_id="F1",
                 evidence_refs=[f"schemas/af_wcc_vacuum.yaml#{h[:12]}"])]
    op = operative([norm(r, "accepted_event", "event:c4") for r in recs], "F1", h)
    C["C4_evidence_refs_do_not_bind"] = "PASS" if op["gate_accept_reviewers"] == [] else "FAIL"

    recs = [dict(base, event_id="c5", reviewer="astra-lead-formulation", verdict="accept",
                 created_at="2026-09-12T00:01:00+08:00", artifact_sha256=h, node_id="F1")]
    op = operative([norm(r, "accepted_event", "event:c5") for r in recs], "F1", h)
    C["C5_author_excluded"] = "PASS" if op["gate_accept_reviewers"] == [] else "FAIL"

    recs = [dict(base, event_id="c6", reviewer="r6", verdict="accept",
                 created_at="2026-09-12T00:01:00+08:00", artifact_sha256=h, node_id="F1",
                 counts_as_full_schema_verdict=False)]
    op = operative([norm(r, "accepted_event", "event:c6") for r in recs], "F1", h)
    C["C6_scoped_excluded_from_full"] = "PASS" if op["gate_accept_reviewers"] == [] else "FAIL"

    recs = [
        dict(base, event_id="c7a", reviewer="r7", verdict="accept",
             created_at="2026-09-12T00:01:00+08:00", artifact_sha256=h, node_id="F1"),
        dict(base, event_id="c7b", reviewer="r7", verdict="revise",
             created_at="2026-09-12T00:02:00+08:00", artifact_sha256=EPOCH["F2a"],
             node_id="F1"),
    ]
    op = operative([norm(r, "accepted_event", f"event:{r['event_id']}") for r in recs],
                   "F1", h)
    C["C7_no_false_supersession_across_hashes"] = (
        "PASS" if op["gate_accept_reviewers"] == ["r7"] else "FAIL")

    recs = [
        dict(base, event_id="c8", reviewer="r8", verdict="accept",
             created_at="2026-09-12T00:01:00+08:00", artifact_sha256=h, node_id="F1"),
    ]
    n1 = norm(recs[0], "accepted_event", "event:c8")
    n2 = norm(recs[0], "reviews_file", "file:c8.json")
    op = operative([n1, n2], "F1", h)
    C["C8_duplicate_channels_dedup"] = (
        "PASS" if op["gate_accept_reviewers"] == ["r8"] and op["records_considered"] == 1
        else "FAIL")

    recs = [dict(base, event_id="c9", reviewer="r9", verdict="accept",
                 created_at="2026-09-12T00:01:00+08:00", artifact_sha256=h, node_id="F1")]
    n = norm(recs[0], "accepted_event", "event:c9")
    n_file = dict(n, channel="reviews_file", rid="file:c9.json", duplicate_channels=[])
    op = operative([n_file], "F1", h)
    C["C9_file_channel_counted"] = "PASS" if op["gate_accept_reviewers"] == ["r9"] else "FAIL"

    recs = [dict(base, event_id="c10", reviewer="r10", verdict="accept",
                 created_at="2026-09-12T00:01:00+08:00", artifact_sha256=h, node_id="F1",
                 counts_as_gate_accept=False)]
    op = operative([norm(r, "accepted_event", "event:c10") for r in recs], "F1", h)
    C["C10_gate_flag_view_separates"] = (
        "PASS" if op["gate_accept_reviewers"] == [] and
        op["full_independent_accept_reviewers"] == ["r10"] else "FAIL")

    reason = "Review scan at these hashes: F1 [1 distinct accept reviewer(s) ['a']], " \
             "F2a [0 distinct accept reviewer(s)], F2b [2 distinct accept reviewer(s) ['b', 'c']]"
    parsed = parse_quoted(reason)
    C["C11_quoted_parser_exact"] = (
        "PASS" if parsed == {"F1": ["a"], "F2a": [], "F2b": ["b", "c"]} else "FAIL")

    recs = [dict(base, event_id="c12", reviewer="r12", verdict="accept",
                 created_at="2026-09-12T00:59:00+08:00", artifact_sha256=h, node_id="F1")]
    op_q = operative([norm(r, "accepted_event", "event:c12") for r in recs],
                     "F1", h, asof=(2026, 9, 12, 0, 43, 8))
    op_n = operative([norm(r, "accepted_event", "event:c12") for r in recs], "F1", h)
    C["C12_asof_excludes_post_quote"] = (
        "PASS" if op_q["gate_accept_reviewers"] == [] and
        op_n["gate_accept_reviewers"] == ["r12"] else "FAIL")

    recs = [dict(base, event_id="c13", reviewer="r13", verdict="accept",
                 created_at="2026-09-12T00:01:00+08:00",
                 artifact_sha256="deadbeefdeadbeefdead", node_id="F1")]
    op = operative([norm(r, "accepted_event", "event:c13") for r in recs], "F1", h)
    C["C13_short_or_wrong_prefix_rejected"] = (
        "PASS" if op["gate_accept_reviewers"] == [] else "FAIL")
    return C


def parse_quoted(reason: str) -> dict:
    out = {}
    for t, _n, names in QUOTED_RE.findall(reason or ""):
        out[t] = sorted(x.strip().strip("'\"")
                        for x in (names or "").split(",") if x.strip())
    return out


def main() -> int:
    manifest_p = PIN / "MANIFEST.json"
    manifest = json.loads(manifest_p.read_text())
    drift = []
    for rel, meta in manifest["files"].items():
        p = PIN / rel
        if not p.is_file() or sha256_file(p) != meta["sha256"]:
            drift.append(rel)
    if drift:
        print("PINNED MANIFEST DRIFT:", drift, file=sys.stderr)
        return 3

    tool_sha = sha256_file(Path(__file__))
    map_doc = json.loads((PIN / "research_map.json").read_text())
    ga = map_doc["controller_gate_audit"]["G-FORM"]
    quote_at = _ts(ga["checked_at"])
    quoted = parse_quoted(ga.get("reason", ""))

    records, prov = load_corpus(manifest)

    epochs = {}
    for t, h in EPOCH.items():
        row = {"epoch_rev12": h}
        for fname, sub in (("af_wcc_vacuum.yaml", "F1"),
                           ("af_scc_c2_vacuum.yaml", "F2a"),
                           ("af_scc_c0_vacuum.yaml", "F2b")):
            if sub != t:
                continue
            pin = PIN / "canonical" / fname
            live = ROOT / "schemas" / fname
            if pin.is_file():
                row["pinned_canonical_sha256"] = sha256_file(pin)
                row["pinned_matches_epoch"] = row["pinned_canonical_sha256"] == h
            if live.is_file():
                row["live_sha256"] = sha256_file(live)
                row["live_matches_epoch"] = row["live_sha256"] == h
        epochs[t] = row

    analysis = {}
    for t, h in EPOCH.items():
        asof = operative(records, t, h, asof=quote_at)
        now = operative(records, t, h)
        q = quoted.get(t, [])
        q_status = {}
        for name in q:
            op_acc = [r for r in asof["operative"]
                      if r["reviewer"] == name and r["verdict"] == "accept"]
            ret_acc = [r for r in asof["retired"]
                       if r["reviewer"] == name and r["verdict"] == "accept"]
            if name in asof["gate_accept_reviewers"]:
                q_status[name] = "operative_gate_accept_at_quote_instant"
            elif name in asof["full_independent_accept_reviewers"]:
                q_status[name] = "operative_full_accept_not_gate_flagged"
            elif op_acc:
                q_status[name] = "operative_accept_but_not_full_or_independent"
            elif ret_acc:
                q_status[name] = "quoted_accept_retired_at_quote_instant"
            elif any(r["reviewer"] == name for r in now["operative"] + now["retired"]):
                q_status[name] = "quoted_reviewer_has_records_but_no_operative_accept"
            else:
                q_status[name] = "no_binding_accept_record_in_pinned_corpus"
        analysis[t] = {
            "quoted": q,
            "quoted_status": q_status,
            "asof_quote": {
                "checked_at": ga["checked_at"],
                "full_independent_accept_reviewers":
                    asof["full_independent_accept_reviewers"],
                "gate_accept_reviewers": asof["gate_accept_reviewers"],
                "operative_records": [
                    {"rid": r["rid"], "reviewer": r["reviewer"], "verdict": r["verdict"],
                     "channel": r["channel"], "full": r["full"],
                     "gate_accept": r["gate_accept_flag"],
                     "time_source": r["time_source"], "created_at": r["created_at"]}
                    for r in asof["operative"]],
                "retired_records": [
                    {"rid": r["rid"], "reviewer": r["reviewer"], "verdict": r["verdict"],
                     "channel": r["channel"], "retired_by": r["retired_by"]}
                    for r in asof["retired"]],
            },
            "now": {
                "full_independent_accept_reviewers":
                    now["full_independent_accept_reviewers"],
                "gate_accept_reviewers": now["gate_accept_reviewers"],
                "operative_accept_records": [
                    {"rid": r["rid"], "reviewer": r["reviewer"], "channel": r["channel"],
                     "full": r["full"], "gate_accept": r["gate_accept_flag"],
                     "created_at": r["created_at"]}
                    for r in now["operative"] if r["verdict"] == "accept"],
            },
        }

    # Secondary, hash-pinned cross-check: do the rev12 schemas' own declared
    # consistency-evidence hashes resolve at the canonical path / FROZEN pin?
    ev_path = ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json"
    ev_sha = sha256_file(ev_path) if ev_path.is_file() else None
    frozen = json.loads((PIN / "canonical/FROZEN.json").read_text())
    frozen_pin = frozen["files"].get(
        "artifacts/formulation/evidence/taxonomy_consistency.json", {}).get("sha256")
    ev_check = {"canonical_path": "artifacts/formulation/evidence/taxonomy_consistency.json",
                "measured_sha256": ev_sha,
                "frozen_rev28_pin": frozen_pin,
                "frozen_matches_measured": ev_sha == frozen_pin,
                "schemas": {}}
    for t, fname in (("F1", "af_wcc_vacuum.yaml"), ("F2a", "af_scc_c2_vacuum.yaml"),
                     ("F2b", "af_scc_c0_vacuum.yaml")):
        txt = (PIN / "canonical" / fname).read_text()
        m = re.search(r'consistency_evidence_sha256:\s*"?([0-9a-f]{64})"?', txt)
        declared = m.group(1) if m else None
        ev_check["schemas"][t] = {
            "declared_consistency_evidence_sha256": declared,
            "resolves_at_canonical_path": declared == ev_sha,
        }

    controls = control_suite()
    controls_pass = all(v == "PASS" for v in controls.values())

    report = {
        "schema": "w033-gform-r12-ledger-report/1",
        "task_id": "W033-GFORM-R12-LEDGER-01",
        "worker": "worker-033",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "tool_sha256": tool_sha,
        "pinned_manifest_sha256": sha256_file(manifest_p),
        "snapshot_at": manifest["created_at"],
        "epochs": epochs,
        "quote": {"source": "pinned/research_map.json#controller_gate_audit.G-FORM",
                  "checked_at": ga["checked_at"], "parsed_accept_sets": quoted,
                  "reason": ga.get("reason", "")},
        "corpus": prov,
        "analysis": analysis,
        "secondary_evidence_check": ev_check,
        "controls": controls,
        "controls_pass": controls_pass,
        "interpretations": {
            "gate_accept_view": "counts_as_gate_accept is not False (missing = counted)",
            "full_schema_view": ("counts_as_full_schema_verdict is not False; "
                                 "the counts_as_gate_accept flag is ignored"),
            "asof_time": "created_at <= quote instant; missing created_at uses pinned mtime",
        },
    }
    (TASK / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    (TASK / "controls.json").write_text(json.dumps(
        {"controls": controls, "controls_pass": controls_pass, "tool_sha256": tool_sha},
        indent=1, sort_keys=True) + "\n")

    live = {t: {"live_sha256": epochs[t].get("live_sha256"),
                "live_matches_epoch": epochs[t].get("live_matches_epoch")}
            for t in EPOCH}
    ev_live = sha256_file(ev_path) if ev_path.is_file() else None
    (TASK / "drift.json").write_text(json.dumps(
        {"measured_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone(__import__("datetime").timedelta(hours=8))
        ).replace(microsecond=0).isoformat(),
         "live_target_hashes": live,
         "live_consistency_evidence_sha256": ev_live,
         "live_consistency_evidence_matches_pinned": ev_live == ev_sha,
         "tool_sha256": tool_sha,
         "pinned_manifest_sha256": sha256_file(manifest_p)},
        indent=1, sort_keys=True) + "\n")

    print(json.dumps({
        "task_id": report["task_id"], "tool_sha256": tool_sha,
        "quote_checked_at": ga["checked_at"],
        "quoted": quoted,
        "asof_gate_accepts": {t: analysis[t]["asof_quote"]["gate_accept_reviewers"]
                              for t in EPOCH},
        "asof_full_accepts": {t: analysis[t]["asof_quote"]["full_independent_accept_reviewers"]
                              for t in EPOCH},
        "quoted_status": {t: analysis[t]["quoted_status"] for t in EPOCH},
        "controls_pass": controls_pass,
        "failed_controls": [k for k, v in controls.items() if v != "PASS"],
    }, indent=1, sort_keys=True))
    return 0 if controls_pass else 2


if __name__ == "__main__":
    sys.exit(main())
