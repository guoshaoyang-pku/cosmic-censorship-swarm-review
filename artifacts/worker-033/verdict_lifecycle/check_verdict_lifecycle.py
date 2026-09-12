#!/usr/bin/env python3
"""W033-VERDICT-LIFECYCLE-01 — operative accept sets for the G-FORM classes.

Question
--------
At the G-FORM canonical hashes, which reviewer verdicts (a) bind the measured
artifact hash, (b) are full-schema (not scoped), (c) come from a reviewer that
is not the artifact author, and (d) are still *operative* — i.e. not withdrawn
or superseded by a later verdict from the same reviewer, or by an explicit
supersession/correction record?

Why this is not the controller's scan
-------------------------------------
``astra_lifecycle.review_coverage`` reads only ``reviews/*.json`` and takes each
file's ``verdict`` at face value: it has no supersession model and cannot see
verdicts written only to the accepted event stream.  Two failure modes follow,
both measured here on a pinned snapshot:

* false positive / stale positive: a withdrawn accept still sitting in its
  review file is counted as an accept;
* false negative: an accept that exists only as an event (never written to a
  review file) is invisible to the scan.

Rules
-----
Binding   : a record binds target T at epoch E when one of its explicit target
            pin fields (artifact_sha256, reviewed_sha256, sha256, cited_sha256,
            target_evidence, target_id) contains the epoch hash prefix.
            ``evidence_refs`` never bind: they cite supporting material.
Duplicate : same reviewer, same target+epoch, same verdict via another channel
            (file vs event) — deduplicated, NOT counted as a supersession.
S1        : a record whose ``supersedes`` / ``supersedes_review`` names an
            earlier bound accept retires that accept.
S2        : within (target, epoch, reviewer), the latest verdict retires every
            earlier verdict that differs; ties break on rid.
S3        : supersession/withdrawal language in any bound record (verdict or
            correction carrier) is recorded as a declared withdrawal; it counts
            as retirement evidence when the withdrawn accept bytes are gone.

Independent : reviewer not in the target's author set.
Full        : ``counts_as_full_schema_verdict`` is not False.

Quoted-vs-measured reconciliation
---------------------------------
The report parses the accept sets quoted in the pinned 00:24:40 controller gate
reason and classifies every delta as withdrawn (with the retiring record),
created-after-quote, or scan blind spot (present at quote time, invisible to
``reviews/*.json``).

Exit status: 0 all controls pass; 2 controls failed (fail-closed).

Read-only on canonical paths.  Worker-level measurement, not a gate verdict.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]          # repo root
TASK = Path(__file__).resolve().parent              # artifacts/worker-033/verdict_lifecycle
PIN = TASK / "pinned"

TARGETS = {
    "F1": {"class_id": "AF-WCC-VAC-GEN", "path": "schemas/af_wcc_vacuum.yaml",
           "tokens": {"F1", "AF-WCC-VAC-GEN", "af_wcc_vacuum.yaml"}},
    "F2a": {"class_id": "AF-SCC-C2-VAC-GEN", "path": "schemas/af_scc_c2_vacuum.yaml",
            "tokens": {"F2A", "AF-SCC-C2-VAC-GEN", "af_scc_c2_vacuum.yaml"}},
    "F2b": {"class_id": "AF-SCC-C0-VAC-GEN", "path": "schemas/af_scc_c0_vacuum.yaml",
            "tokens": {"F2B", "AF-SCC-C0-VAC-GEN", "af_scc_c0_vacuum.yaml"}},
    "F0": {"class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH",
           "path": "research_map/formulation_taxonomy.yaml",
           "tokens": {"F0", "formulation_taxonomy.yaml"}},
}
TOKEN2TARGET = {}
for _t, _m in TARGETS.items():
    for _tok in _m["tokens"]:
        TOKEN2TARGET[_tok.upper()] = _t

# rev11 epoch (pre-republication): the hashes the 2026-09-12T00:24:40 controller
# gate reason was computed against.  Hard pins of the auditing question.
OLD_EPOCH = {
    "F1": "9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503",
    "F2a": "b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2",
    "F2b": "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508",
    "F0": "276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc",
}
AUTHORS = {
    "F1": {"astra-lead-formulation", "lead-formulation", "deepseek-flash-01"},
    "F2a": {"astra-lead-formulation", "lead-formulation", "deepseek-flash-01"},
    "F2b": {"astra-lead-formulation", "lead-formulation", "deepseek-flash-01"},
    "F0": {"astra-lead-formulation", "lead-formulation", "deepseek-flash-01"},
}
VERDICTS = {"accept", "revise", "reject", "inconclusive"}
WITHDRAW_RE = re.compile(r"withdraw|supersed|correct(?:ed|ion)|retract", re.I)
HEX_RE = re.compile(r"[0-9a-f]{12,64}")
STRONG_PIN_FIELDS = ("artifact_sha256", "reviewed_sha256", "sha256", "cited_sha256",
                     "target_evidence", "target_id")
IDENTITY_FIELDS = ("target_id", "target", "target_subnode", "artifact")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _flatten_strings(v):
    if isinstance(v, str):
        yield v
    elif isinstance(v, list):
        for x in v:
            yield from _flatten_strings(x)
    elif isinstance(v, dict):
        for x in v.values():
            yield from _flatten_strings(x)


def canon_targets(rec: dict, identity_only: bool = False) -> set:
    """Targets a verdict record speaks about.

    identity_only=True uses only target_id/target/target_subnode/artifact, i.e.
    the artifact the review claims to be about; the default additionally falls
    back to node_id/class tokens (used to attribute correction carriers).
    """
    out = set()
    keys = IDENTITY_FIELDS if identity_only else IDENTITY_FIELDS + (
        "node_id", "class_id", "class_ids", "class")
    for key in keys:
        for s in _flatten_strings(rec.get(key)):
            for piece in re.split(r"[;,/|()\[\]\s]+", s):
                t = TOKEN2TARGET.get(piece.upper())
                if t:
                    out.add(t)
    return out


def strong_pins(rec: dict) -> set:
    """Hashes in explicit target-pin fields (never evidence_refs)."""
    out = set()
    for key in STRONG_PIN_FIELDS:
        for s in _flatten_strings(rec.get(key)):
            if key == "target_id" and "#" not in s:
                continue
            for m in HEX_RE.findall(s.lower()):
                out.add(m)
    for key in ("target", "artifact"):
        v = rec.get(key)
        if isinstance(v, dict):
            for k2 in ("sha256", "artifact_sha256", "reviewed_sha256", "cited_sha256"):
                if isinstance(v.get(k2), str):
                    out.update(HEX_RE.findall(v[k2].lower()))
    return out


def ref_pins(rec: dict) -> set:
    out = set()
    for key in ("evidence_refs", "artifact_refs"):
        for s in _flatten_strings(rec.get(key)):
            out.update(HEX_RE.findall(s.lower()))
    return out


def binds(pins: set, h: str) -> bool:
    return any(p.startswith(h[:12]) or h.startswith(p[:12]) for p in pins)


def norm_record(rec: dict, source: str, rid: str, correction: bool = False) -> dict:
    reviewer = str(rec.get("reviewer") or rec.get("actor") or "?")
    verdict = str(rec.get("verdict", "")).lower()
    if verdict not in VERDICTS:
        verdict = ""
    full = rec.get("counts_as_full_schema_verdict") is not False
    created = str(rec.get("created_at") or "")
    sup_parts = []
    for key in ("supersedes", "supersedes_review"):
        for s in _flatten_strings(rec.get(key)):
            sup_parts.append(s)
    text = " | ".join(sup_parts)
    return {
        "rid": rid,
        "source": source,
        "reviewer": reviewer,
        "verdict": verdict,
        "full": full,
        "created_at": created,
        "supersedes_text": text,
        "targets": sorted(canon_targets(rec, identity_only=False)),
        "identity_targets": sorted(canon_targets(rec, identity_only=True)),
        "pins": sorted(strong_pins(rec)),
        "ref_pins": sorted(ref_pins(rec)),
        "correction": correction,
        "raw": rec,
    }


def load_corpus(pin_dir: Path):
    records = []
    prov = {"review_files": [], "review_files_loaded": 0, "event_lines": 0, "outbox_files": []}
    reviews_dir = pin_dir / "reviews"
    if reviews_dir.is_dir():
        for p in sorted(reviews_dir.glob("*.json")):
            prov["review_files"].append(p.name)
            try:
                d = json.loads(p.read_text())
            except Exception:
                continue
            if not isinstance(d, dict):
                continue
            if str(d.get("verdict", "")).lower() not in VERDICTS:
                continue
            records.append(norm_record(d, "review_file", f"file:{p.name}"))
            prov["review_files_loaded"] += 1
    ev = pin_dir / "events.jsonl"
    if ev.is_file():
        for i, line in enumerate(ev.read_text(errors="ignore").splitlines(), 1):
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            prov["event_lines"] = i
            if d.get("event_type") == "review" and str(d.get("verdict", "")).lower() in VERDICTS:
                records.append(norm_record(d, "event", f"event:{d.get('event_id') or i}"))
            elif d.get("event_type") in ("status", "artifact", "blocker"):
                blob = json.dumps(d).lower()
                if WITHDRAW_RE.search(blob):
                    records.append(norm_record(d, "correction_event",
                                               f"event:{d.get('event_id') or i}", correction=True))
    ob = pin_dir / "outbox"
    if ob.is_dir():
        for p in sorted(ob.rglob("*.json*")):
            prov["outbox_files"].append(str(p.relative_to(pin_dir)))
            for j, line in enumerate(p.read_text(errors="ignore").splitlines(), 1):
                line = line.strip()
                if not line.startswith("{"):
                    continue
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                if str(d.get("verdict", "")).lower() in VERDICTS:
                    records.append(norm_record(d, "outbox", f"outbox:{p.name}:{j}"))
                elif d.get("event_type") in ("status", "artifact", "blocker") \
                        and WITHDRAW_RE.search(json.dumps(d).lower()):
                    records.append(norm_record(d, "correction_outbox",
                                               f"outbox:{p.name}:{j}", correction=True))
    return records, prov


def _ts(s: str):
    """Sortable timestamp key tolerant of +0800 vs +08:00 and missing values."""
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})", s or "")
    if not m:
        return (0,) * 6 + (s or "",)
    return tuple(int(x) for x in m.groups()) + (s or "",)


def _refs(rec: dict) -> list:
    """Precise supersession references (event ids / review paths), never prose."""
    refs = []
    for key in ("supersedes", "supersedes_review"):
        v = rec.get(key)
        if isinstance(v, dict):
            for k2 in ("event_id", "review_id", "file", "path", "rid"):
                if isinstance(v.get(k2), str):
                    refs.append(v[k2].strip())
        elif isinstance(v, str):
            # tokens that look like an event id or a review file path
            for m in re.findall(r"[A-Za-z0-9][A-Za-z0-9._:+-]{5,}", v):
                if m.endswith(".json") or re.search(
                        r"review|artifact|status|claim|accept|checkpoint", m, re.I):
                    refs.append(m.strip())
    return refs


def _ref_matches(ref: str, rid: str) -> bool:
    """Exact reference match: full rid, rid suffix, or review-file basename."""
    suffix = rid.split(":", 1)[-1]
    if ref == rid or ref == suffix:
        return True
    if ref.endswith(".json") and suffix.endswith(".json"):
        return ref.split("/")[-1] == suffix.split("/")[-1]
    return False


def _verdict_related(text: str) -> bool:
    return bool(re.search(r"accept|verdict|review", text or "", re.I))


def analyze(records, epochs: dict, authors: dict, quoted_at: str | None = None) -> dict:
    out = {}
    for t, eps in epochs.items():
        out[t] = {}
        for ename, h in eps.items():
            bound = [r for r in records
                     if r["verdict"] and t in r["targets"] and binds(set(r["pins"]), h)
                     and (not r["identity_targets"] or t in r["identity_targets"]
                          or r["correction"])]
            bound_any = [r for r in records
                         if t in r["targets"] and binds(set(r["pins"]), h)]
            groups = {}
            for r in bound:
                groups.setdefault(r["reviewer"], []).append(r)
            superseded, duplicates = [], []
            # S1: explicit, exactly-named supersession of a bound accept
            by_rid = {r["rid"]: r for r in bound}
            s1_retired = {}
            for r in bound:
                for ref in _refs(r):
                    for rid, target_rec in by_rid.items():
                        if rid == r["rid"] or target_rec["verdict"] != "accept":
                            continue
                        if _ref_matches(ref, rid) and rid not in s1_retired:
                            s1_retired[rid] = {"rid": rid, "reviewer": target_rec["reviewer"],
                                               "verdict": "accept", "superseded_by": r["rid"],
                                               "rule": "S1",
                                               "reason": f"explicit reference {ref!r}"}
            # S2: latest verdict per reviewer retires earlier differing verdicts
            operative = {}
            for rev, rs in sorted(groups.items()):
                rs = sorted(rs, key=lambda r: (_ts(r["created_at"]), r["rid"]))
                op = rs[-1]
                operative[rev] = op
                for earlier in rs[:-1]:
                    item = {"rid": earlier["rid"], "reviewer": rev,
                            "verdict": earlier["verdict"],
                            "superseded_by": op["rid"], "rule": "S2",
                            "reason": "later verdict by same reviewer at same epoch"}
                    if earlier["verdict"] == op["verdict"]:
                        item["rule"] = "DUP"
                        item["reason"] = "same verdict via another channel"
                        duplicates.append(item)
                    else:
                        superseded.append(item)
            # apply S1 for real: a retired record cannot be the operative verdict
            for rid, meta in s1_retired.items():
                superseded.append(meta)
                rev = meta["reviewer"]
                if operative.get(rev, {}).get("rid") == rid:
                    rest = [r for r in groups[rev] if r["rid"] != rid]
                    if rest:
                        operative[rev] = sorted(rest, key=lambda r: (_ts(r["created_at"]), r["rid"]))[-1]
                    else:
                        operative.pop(rev, None)
            # S3: declared withdrawals (verdict-related only)
            declared = []
            for r in bound_any:
                text = r["supersedes_text"] or ""
                if not _verdict_related(text):
                    summary = str(r["raw"].get("summary", ""))
                    if not _verdict_related(summary):
                        continue
                    text = summary[:300]
                if r["correction"] or WITHDRAW_RE.search(r["supersedes_text"] or ""):
                    declared.append({
                        "rid": r["rid"], "reviewer": r["reviewer"],
                        "verdict": r["verdict"] or "(correction carrier)",
                        "evidence": text[:300], "rule": "S3",
                    })
            # reviewers whose accept is retired
            retired_accepts = {x["rid"] for x in superseded if x["verdict"] == "accept"}
            accepts_all, accepts_full, accepts_full_indep = [], [], []
            scan_b = []
            for rev, op in sorted(operative.items()):
                if op["verdict"] != "accept":
                    continue
                accepts_all.append(rev)
                if op["full"]:
                    accepts_full.append(rev)
                    if rev not in authors[t]:
                        accepts_full_indep.append(rev)
                    if op["source"] != "review_file":
                        scan_b.append(rev)
            # controller semantics, no supersession: any bound file accept
            scan_a_nominal = sorted({r["reviewer"] for r in bound
                                     if r["source"] == "review_file" and r["verdict"] == "accept"
                                     and r["full"]})
            # file-consistent scan: file accept whose reviewer's operative verdict is accept
            scan_a_consistent = sorted({r["reviewer"] for r in bound
                                        if r["source"] == "review_file" and r["verdict"] == "accept"
                                        and r["full"] and r["rid"] not in retired_accepts
                                        and operative.get(r["reviewer"], {}).get("verdict") == "accept"})
            quoted = sorted(quoted_sets.get(t, [])) if quoted_sets else []
            deltas = {}
            for rev in quoted:
                if rev in accepts_full_indep:
                    deltas[rev] = "operative"
                elif any(x["reviewer"] == rev for x in superseded):
                    deltas[rev] = "withdrawn_after_quote"
                elif any(x["reviewer"] == rev for x in declared):
                    deltas[rev] = "declared_withdrawal_no_surviving_bytes"
                else:
                    deltas[rev] = "not_reproducible_from_pinned_corpus"
            new_after = {}
            for rev in accepts_full_indep:
                if rev in quoted:
                    continue
                op = operative[rev]
                if quoted_at and _ts(op["created_at"]) > _ts(quoted_at):
                    new_after[rev] = "created_after_quote"
                else:
                    new_after[rev] = "scan_blind_spot_at_quote_time"
            out[t][ename] = {
                "measured_sha256": h,
                "bound_verdict_records": len(bound),
                "bound_records": [{"rid": r["rid"], "source": r["source"], "reviewer": r["reviewer"],
                                   "verdict": r["verdict"], "full": r["full"],
                                   "created_at": r["created_at"]} for r in sorted(
                                       bound, key=lambda r: (_ts(r["created_at"]), r["rid"]))],
                "superseded": sorted(superseded, key=lambda x: x["rid"]),
                "accept_retirements": sorted(
                    [x for x in superseded if x["verdict"] == "accept"], key=lambda x: x["rid"]),
                "duplicate_channel_records": sorted(duplicates, key=lambda x: x["rid"]),
                "declared_withdrawals": sorted(declared, key=lambda x: x["rid"]),
                "operative_accepts_all": sorted(accepts_all),
                "operative_accepts_full": sorted(accepts_full),
                "operative_accepts_full_independent": sorted(accepts_full_indep),
                "threshold_met_two_independent_full": len(accepts_full_indep) >= 2,
                "scan_A_file_only_nominal_controller_semantics": scan_a_nominal,
                "scan_A_file_only_consistent_with_operative": scan_a_consistent,
                "scan_B_event_only_operative": scan_b,
                "quoted_002440": quoted,
                "quoted_delta": deltas,
                "operative_not_quoted": new_after,
            }
    return out


def synthetic_controls() -> dict:
    res = {}
    E = {"T": {"e": "a" * 64}}
    AUTH = {"T": {"author-x"}}

    def mk(rid, reviewer, verdict, pin="a" * 64, created="2026-01-01T00:00:00+08:00",
           source="review_file", full=True, correction=False, **kw):
        d = {"event_id": rid, "reviewer": reviewer, "verdict": verdict,
             "artifact_sha256": pin, "created_at": created,
             "counts_as_full_schema_verdict": full, "target_id": "T"}
        d.update(kw)
        r = norm_record(d, source, rid, correction=correction)
        r["targets"] = ["T"]
        r["identity_targets"] = ["T"]
        return r

    def run(recs):
        return analyze(recs, E, AUTH, quoted_at=None)["T"]["e"]

    a = run([mk("f1", "u1", "accept"), mk("f2", "u1", "revise", created="2026-01-02T00:00:00+08:00")])
    res["C1_latest_wins_retires_accept"] = ("PASS" if a["operative_accepts_full"] == []
                                            and any(x["rule"] == "S2" for x in a["superseded"])
                                            else "FAIL")
    b = run([mk("r2", "u1", "revise", supersedes_review="the accept written at 00:22 is withdrawn")])
    res["C2_declared_withdrawal_recorded"] = ("PASS" if b["declared_withdrawals"] else "FAIL")
    c = run([mk("f3", "u1", "accept", pin="b" * 64)])
    res["C3_other_hash_not_bound"] = ("PASS" if c["bound_verdict_records"] == 0 else "FAIL")
    d4 = mk("f4", "u1", "accept"); d4["pins"] = []
    c4 = run([d4])
    res["C4_unpinned_not_bound"] = ("PASS" if c4["bound_verdict_records"] == 0 else "FAIL")
    c5 = run([mk("f5", "author-x", "accept")])
    res["C5_author_excluded"] = ("PASS" if c5["operative_accepts_full"] == ["author-x"]
                                 and c5["operative_accepts_full_independent"] == [] else "FAIL")
    c6 = run([mk("f6", "u2", "accept", full=False)])
    res["C6_scoped_excluded_from_full"] = ("PASS" if c6["operative_accepts_full"] == []
                                           and c6["operative_accepts_all"] == ["u2"] else "FAIL")
    c7 = run([mk("f7", "u3", "accept"),
              mk("ev9", "u3", "revise", source="event", supersedes="unrelated-event-id",
                 created="2026-01-03T00:00:00+08:00")])
    res["C7_no_false_supersession"] = ("PASS" if not any(x["rule"] == "S1" for x in c7["superseded"])
                                       else "FAIL")
    c8 = run([mk("ev1", "u4", "accept", source="event")])
    res["C8_event_only_accept_operative"] = (
        "PASS" if c8["scan_A_file_only_consistent_with_operative"] == []
        and c8["scan_B_event_only_operative"] == ["u4"]
        and c8["operative_accepts_full_independent"] == ["u4"] else "FAIL")
    # C9 duplicate channel record is deduplicated, not treated as a withdrawal
    c9 = run([mk("f9", "u5", "accept"), mk("ev9b", "u5", "accept", source="event",
                                           created="2026-01-02T00:00:00+08:00")])
    res["C9_duplicate_not_withdrawal"] = (
        "PASS" if c9["operative_accepts_full"] == ["u5"]
        and c9["duplicate_channel_records"]
        and not any(x["verdict"] == "accept" for x in c9["superseded"]) else "FAIL")
    # C10 evidence_refs alone do not bind
    d10 = mk("f10", "u6", "accept"); d10["pins"] = []
    d10["ref_pins"] = ["a" * 64]
    c10 = run([d10])
    res["C10_evidence_refs_do_not_bind"] = ("PASS" if c10["bound_verdict_records"] == 0 else "FAIL")
    return res


def controller_quotes() -> dict:
    out = {}
    for label, name in (("pass_002440", "controller_lifecycle_002440.json"),
                        ("pass_003316", "controller_lifecycle_003316.json")):
        p = PIN / name
        if not p.is_file():
            continue
        d = json.loads(p.read_text())
        ga = d.get("controller_gate_audit", {})
        out[label] = {"file": f"pinned/{name}", "sha256": sha256_file(p),
                      "G-FORM": ga.get("G-FORM", {}), "G-F0": ga.get("G-F0", {})}
    return out


QUOTED_RE = re.compile(r"(F0|F1|F2a|F2b)\s*\[(\d+)\s+distinct accept reviewer\(s\)\s*\[([^\]]*)\]\]")
quoted_sets: dict = {}


def parse_quoted(reason: str) -> dict:
    out = {}
    for t, _n, names in QUOTED_RE.findall(reason or ""):
        out[t] = sorted(x.strip().strip("'\"") for x in names.split(",") if x.strip())
    return out


def live_census(epochs: dict) -> dict:
    out = {}
    for t, eps in epochs.items():
        out[t] = {}
        for ename, h in eps.items():
            hits = []
            for p in sorted((ROOT / "reviews").glob("*.json")):
                try:
                    d = json.loads(p.read_text())
                except Exception:
                    continue
                if not isinstance(d, dict):
                    continue
                if str(d.get("verdict", "")).lower() in VERDICTS and t in canon_targets(d) \
                        and binds(strong_pins(d), h):
                    hits.append({"file": p.name, "reviewer": d.get("reviewer") or d.get("actor"),
                                 "verdict": str(d.get("verdict")).lower()})
            out[t][ename] = hits
    return out


def main() -> int:
    global quoted_sets
    epochs = {t: {"rev11": OLD_EPOCH[t]} for t in TARGETS}
    for t, m in TARGETS.items():
        p = PIN / "canonical" / Path(m["path"]).name
        if p.is_file():
            epochs[t]["current"] = sha256_file(p)

    records, prov = load_corpus(PIN)
    live_targets = {}
    for t, m in TARGETS.items():
        p = ROOT / m["path"]
        if p.is_file():
            live_targets[t] = sha256_file(p)
    drift = {t: (live_targets.get(t) == epochs[t].get("current")) for t in TARGETS}
    quotes = controller_quotes()
    q_reason = quotes.get("pass_002440", {}).get("G-FORM", {}).get("reason", "")
    quoted_at = quotes.get("pass_002440", {}).get("G-FORM", {}).get("checked_at")
    quoted_sets = parse_quoted(q_reason)
    result = analyze(records, epochs, AUTHORS, quoted_at=quoted_at)
    controls = synthetic_controls()
    controls_pass = all(v == "PASS" for v in controls.values())

    manifest = TASK / "SHA256SUMS"
    manifest_lines = manifest.read_text().splitlines() if manifest.is_file() else []
    live = live_census(epochs)
    tool_sha = sha256_file(Path(__file__))
    audit = json.loads((PIN / "controller_gate_audit.json").read_text())
    # Live (non-pinned) observations go to drift.json so report.json is a pure
    # function of the pinned inputs and re-running it is hash-stable.
    (TASK / "drift.json").write_text(json.dumps({
        "measured_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone(__import__("datetime").timedelta(hours=8))
        ).replace(microsecond=0).isoformat(),
        "live_census": live,
        "live_target_hashes": live_targets,
        "drift_live_vs_pinned": drift,
        "tool_sha256": tool_sha,
        "pinned_manifest_sha256": sha256_file(manifest) if manifest.is_file() else None,
    }, indent=1, sort_keys=True) + "\n")

    reconciliation = {}
    for t in ("F1", "F2a", "F2b"):
        blk = result[t]["rev11"]
        reconciliation[t] = {
            "quoted_002440": blk["quoted_002440"],
            "scan_A_nominal_now": blk["scan_A_file_only_nominal_controller_semantics"],
            "scan_A_consistent_now": blk["scan_A_file_only_consistent_with_operative"],
            "scan_B_event_only_now": blk["scan_B_event_only_operative"],
            "operative_now": blk["operative_accepts_full_independent"],
            "quoted_delta": blk["quoted_delta"],
            "operative_not_quoted": blk["operative_not_quoted"],
            "threshold_met_operative": blk["threshold_met_two_independent_full"],
            "quote_reproducible_from_pinned_corpus": (
                sorted(blk["quoted_002440"]) ==
                sorted(blk["scan_A_file_only_nominal_controller_semantics"])),
        }

    report = {
        "schema": "w033-verdict-lifecycle-report/1",
        "task_id": "W033-VERDICT-LIFECYCLE-01",
        "worker": "worker-033",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "tool_sha256": tool_sha,
        "pinned": {"review_files_listed": len(prov["review_files"]),
                   "review_files_with_verdict": prov["review_files_loaded"],
                   "event_lines": prov["event_lines"],
                   "outbox_files": prov["outbox_files"],
                   "manifest_lines": len(manifest_lines),
                   "map_updated_at": audit.get("updated_at"),
                   "controller_gate_audit_checked_at": {
                       k: v.get("checked_at") for k, v in audit["controller_gate_audit"].items()}},
        "controller_quotes": quotes,
        "controller_gate_audit_quote": {
            k: {"verdict": v.get("verdict"), "checked_at": v.get("checked_at"),
                "reason": v.get("reason")}
            for k, v in audit["controller_gate_audit"].items() if k in ("G-F0", "G-FORM")},
        "epochs": epochs,
        "reconciliation": reconciliation,
        "analysis": result,
        "controls": controls,
        "controls_pass": controls_pass,
        "notes": [
            "rev11 = pre-republication hashes, the epoch of the quoted 00:24:40 gate "
            "reason; current = hashes of the pinned canonical copies at pin time.",
            "scan_A reproduces astra_lifecycle.review_coverage semantics "
            "(reviews/*.json, verdict at face value, full-schema only).",
            "Binding uses explicit target-pin fields only; evidence_refs never bind.",
            "F0 is a secondary observation with the same instrument, outside the "
            "G-FORM claim.",
            "Worker-level measurement only: cannot set done/passed or a gate verdict.",
        ],
    }
    (TASK / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    (TASK / "controls.json").write_text(json.dumps(
        {"controls": controls, "controls_pass": controls_pass, "tool_sha256": tool_sha},
        indent=1, sort_keys=True) + "\n")

    print(f"tool_sha256 {tool_sha}")
    print(f"pinned: {prov['review_files_loaded']} verdict review files "
          f"(of {len(prov['review_files'])}), {prov['event_lines']} event lines, "
          f"manifest {len(manifest_lines)} lines")
    print(f"controls: {sum(1 for v in controls.values() if v == 'PASS')}/{len(controls)} pass")
    for t in ("F1", "F2a", "F2b", "F0"):
        for ename, blk in result[t].items():
            print(f"[{t}/{ename}] {blk['measured_sha256'][:12]} bound={blk['bound_verdict_records']} "
                  f"scanA={blk['scan_A_file_only_consistent_with_operative']} "
                  f"scanB={blk['scan_B_event_only_operative']} "
                  f"operative={blk['operative_accepts_full_independent']} "
                  f"two_indep={blk['threshold_met_two_independent_full']}")
            if blk["quoted_002440"]:
                print(f"    quoted_002440={blk['quoted_002440']} delta={blk['quoted_delta']}")
                print(f"    operative_not_quoted={blk['operative_not_quoted']}")
            for x in blk["superseded"]:
                print(f"    superseded {x['rid']} [{x['rule']}] by {x['superseded_by']}")
            for x in blk["declared_withdrawals"]:
                print(f"    declared_withdrawal {x['rid']} ({x['reviewer']})")
    return 0 if controls_pass else 2


if __name__ == "__main__":
    sys.exit(main())
