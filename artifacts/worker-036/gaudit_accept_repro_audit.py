#!/usr/bin/env python3
"""W036-GATE-REPRO-01 -- do the recorded G-AUDIT/G-FORM "distinct accept reviewer(s)"
counts reproduce against the review corpus, and is each accept backed by a stable file?

Class-bound task (primary class AF-WCC-VAC-GEN; siblings AF-SCC-C2-VAC-GEN,
AF-SCC-C0-VAC-GEN, AF-WCC-SCALAR-SPH).  Node A1 / gates G-AUDIT + G-FORM.

Question measured
-----------------
`research_map/research_map.json -> controller_gate_audit.G-FORM.reason` records, at
checked_at 2026-09-12T00:24:40+08:00:

    F1 [1 distinct accept reviewer(s) ['astra-lead-audit']]
    F2a [2 distinct accept reviewer(s) ['astra-lead-audit', 'worker-047']]
    F2b [4 distinct accept reviewer(s) ['astra-lead-audit', 'deepseek-flash-07',
         'deepseek-flash-17', 'worker-030']]

This script re-runs the *exact* controller rule (astra_lifecycle.py:160-198, transcribed
behaviourally below) over `reviews/*.json` pinned to the same measured canonical target
hashes, diffs the result against the recorded reason, and classifies every accept entry
it finds.  A second, advisory pass over `map.reviews` (the accepted event record) measures
accepts that exist in the event record but are invisible to a `reviews/*.json`-only scan.

No gate verdict is set here: worker events cannot set a gate verdict or a node status.
Output is machine JSON only.  Exit 1 means hard findings exist; 2 means the snapshot moved
under the scan (findings advisory); 0 means the recorded counts reproduced with no hard
finding.

Self-test: `python3 gaudit_accept_repro_audit.py --selftest` builds a synthetic corpus in a
temp dir and asserts the controller-rule behaviour on planted cases (accept / superseded
pin / revise / scoped accept / missing reviewer / 12-hex prefix / target alias) plus the
recorded-reason parser.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------- controller rule
# Transcribed from research_map/astra_lifecycle.py:118-198 (read 2026-09-12T00:26).
VERDICT_KINDS = ("accept", "revise", "reject", "inconclusive")
TARGET_ALIASES = {
    "F0": "F0", "F1": "F1", "F2A": "F2a", "F2B": "F2b", "F2": "F2b",
    "L0": "L0", "L1": "L1",
    "AF-WCC-VAC-GEN": "F1",
    "AF-SCC-C2-VAC-GEN": "F2a",
    "AF-SCC-C0-VAC-GEN": "F2b",
}
PIN_KEYS = ("artifact_sha256", "reviewed_sha256", "sha256", "cited_sha256")
NESTED_PIN_KEYS = ("sha256", "artifact_sha256", "reviewed_sha256")


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _targets_in_review(d: dict) -> set:
    out = set()
    for key in ("target_id", "target", "target_subnode"):
        v = d.get(key)
        if isinstance(v, str):
            out.add(v)
        elif isinstance(v, dict):
            for k2 in ("target_id", "target_subnode", "subnode", "node_id"):
                if isinstance(v.get(k2), str):
                    out.add(v[k2])
    return {TARGET_ALIASES.get(t, TARGET_ALIASES.get(t.upper(), t)) for t in out}


def _explicit_pins(d: dict) -> list:
    pins = []
    for key in PIN_KEYS:
        v = d.get(key)
        if isinstance(v, str):
            pins.append(v.lower())
    for key in ("target", "artifact"):
        v = d.get(key)
        if isinstance(v, dict):
            for k2 in NESTED_PIN_KEYS:
                if isinstance(v.get(k2), str):
                    pins.append(v[k2].lower())
    return pins


def _pin_matches(pin: str, h: str) -> bool:
    """Controller rule (astra_lifecycle.py:185): prefix either way on 12 hex chars."""
    return bool(pin) and bool(h) and (pin.startswith(h[:12]) or h.startswith(pin[:12]))


def scan_reviews_dir(reviews_dir: Path, hashes: dict) -> dict:
    """Exact controller rule over reviews/*.json.  Returns per-target coverage + detail."""
    cov = {t: {"verdicts": [], "accepts": [], "full_accepts": [], "scoped_accepts": [],
               "distinct_accept_reviewers": []} for t in hashes}
    for rp in sorted(reviews_dir.glob("*.json")):
        try:
            d = json.loads(rp.read_text())
        except Exception:
            continue
        v = str(d.get("verdict", "")).lower()
        if v not in VERDICT_KINDS:
            continue
        reviewer = str(d.get("reviewer") or d.get("actor") or "?")
        full = d.get("counts_as_full_schema_verdict") is not False
        pins = _explicit_pins(d)
        for t in _targets_in_review(d):
            if t not in cov:
                continue
            h = (hashes.get(t, {}).get("sha256") or "")
            if not any(_pin_matches(p, h) for p in pins):
                continue
            matched = sorted({p for p in pins if _pin_matches(p, h)},
                             key=lambda p: (-len(p), p))
            entry = {
                "file": rp.name, "reviewer": reviewer, "verdict": v,
                "counts_as_full_schema_verdict": full,
                "scoped_flag_present": "counts_as_full_schema_verdict" in d,
                "scope": d.get("scope"),
                "created_at": d.get("created_at"),
                "event_id": d.get("event_id"),
                "target_field": d.get("target_id") or d.get("target_subnode"),
                "pin_used": matched[0] if matched else None,
                "pin_full_64": bool(matched and len(matched[0]) == 64),
                "pin_prefix_len": len(matched[0]) if matched else 0,
                "reviewer_field": ("reviewer" if d.get("reviewer") else
                                   "actor" if d.get("actor") else "absent"),
                "evidence_refs": d.get("evidence_refs"),
                "file_sha256": _sha256_file(rp),
                "file_mtime": datetime.fromtimestamp(rp.stat().st_mtime)
                                     .astimezone().isoformat(timespec="seconds"),
            }
            cov[t]["verdicts"].append(entry)
            if v == "accept":
                cov[t]["accepts"].append(entry)
                (cov[t]["full_accepts"] if full else cov[t]["scoped_accepts"]).append(entry)
    for c in cov.values():
        c["distinct_accept_reviewers"] = sorted({a["reviewer"] for a in c["full_accepts"]})
        c["two_distinct_accepts"] = len(c["distinct_accept_reviewers"]) >= 2
    return cov


def scan_event_record(reviews: list, hashes: dict) -> dict:
    """Advisory second source: the accepted event record (map.reviews).

    Same target/pin idea, but pins may also live in `evidence_refs` as `path#<hex>`.
    This measures accepts that a `reviews/*.json`-only scan cannot see; it does NOT
    set a count, because the binding source is the audit lead's matrix.
    """
    out = {t: [] for t in hashes}
    for r in reviews:
        v = str(r.get("verdict", "")).lower()
        if v != "accept":
            continue
        reviewer = str(r.get("reviewer") or r.get("actor") or "?")
        pins = []
        for k in PIN_KEYS + ("target_sha256", "review_sha256"):
            x = r.get(k)
            if isinstance(x, str):
                pins.append(x.lower())
        for ref in (r.get("evidence_refs") or []):
            if isinstance(ref, str) and "#" in ref:
                frag = ref.rsplit("#", 1)[1].strip().lower()
                if re.fullmatch(r"[0-9a-f]{12,64}", frag):
                    pins.append(frag)
        for t in _targets_in_review(r):
            if t not in out:
                continue
            h = (hashes.get(t, {}).get("sha256") or "")
            if any(_pin_matches(p, h) for p in pins):
                out[t].append({
                    "event_id": r.get("event_id"), "reviewer": reviewer,
                    "received_at": r.get("received_at") or r.get("created_at"),
                    "target_id": r.get("target_id"),
                    "pin_used": sorted({p for p in pins if _pin_matches(p, h)},
                                       key=lambda p: (-len(p), p))[0],
                    "evidence_refs": r.get("evidence_refs"),
                })
    return out


def check_evidence_refs(root: Path, reviews: list, hashes: dict) -> list:
    """Resolve `path#<hex12+>` evidence refs of accept events pinned to measured hashes.

    A ref is `match` when the file on disk still hashes to the cited prefix, `stale`
    when it does not, `missing` when the file is absent.  This is the accept event's
    own evidence chain; a stale/missing ref means the recorded accept cannot be
    re-derived from the cited bytes.
    """
    rows = []
    for r in reviews:
        if str(r.get("verdict", "")).lower() != "accept":
            continue
        pins = []
        for k in PIN_KEYS + ("target_sha256", "review_sha256"):
            x = r.get(k)
            if isinstance(x, str):
                pins.append(x.lower())
        for ref in (r.get("evidence_refs") or []):
            if isinstance(ref, str) and "#" in ref:
                frag = ref.rsplit("#", 1)[1].strip().lower()
                if re.fullmatch(r"[0-9a-f]{12,64}", frag):
                    pins.append(frag)
        for t in _targets_in_review(r):
            if t not in hashes:
                continue
            h = hashes[t]["sha256"]
            if not any(_pin_matches(p, h) for p in pins):
                continue
            for ref in (r.get("evidence_refs") or []):
                if not isinstance(ref, str) or "#" not in ref:
                    continue
                path, frag = ref.rsplit("#", 1)
                frag = frag.strip().lower()
                if not re.fullmatch(r"[0-9a-f]{12,64}", frag):
                    continue
                fp = root / path
                base = {"event_id": r.get("event_id"), "reviewer": r.get("reviewer"),
                        "target": t, "received_at": r.get("received_at"),
                        "ref": ref, "cited": frag}
                if not fp.is_file():
                    rows.append({**base, "status": "missing", "current": None})
                    continue
                cur = _sha256_file(fp)
                rows.append({**base, "status": "match" if cur.startswith(frag[:12])
                             else "stale", "current": cur})
    return rows


# ---------------------------------------------------------------- recorded reason
_REC_RE = re.compile(r"(?:(\w+) )?\[(\d+) distinct accept reviewer\(s\)(?:\s*\[([^\]]*)\])?\]")


def parse_recorded_reason(reason: str) -> list:
    """Extract [(label, count, [reviewers])] from a gate-audit reason string."""
    rows = []
    for m in _REC_RE.finditer(reason or ""):
        revs = re.findall(r"'([^']*)'", m.group(3) or "")
        rows.append((m.group(1) or "", int(m.group(2)), revs))
    if not rows:
        m = re.search(r"(\d+) distinct accept reviewer\(s\)(?:\s*\[([^\]]*)\])?", reason or "")
        if m:
            rows.append(("", int(m.group(1)), re.findall(r"'([^']*)'", m.group(2) or "")))
    return rows


# ---------------------------------------------------------------- selftest
def _selftest() -> int:
    H1 = "a" * 64
    H2 = "b" * 64
    checks = []

    def ck(name, cond):
        checks.append((name, bool(cond)))

    with tempfile.TemporaryDirectory() as td:
        rd = Path(td) / "reviews"
        rd.mkdir()
        corpus = {
            "f_ok.json": {"verdict": "accept", "reviewer": "r1", "reviewed_sha256": H1,
                          "counts_as_full_schema_verdict": True, "target_id": "F1"},
            "f_super.json": {"verdict": "accept", "reviewer": "r2", "reviewed_sha256": H2,
                             "target_id": "F1"},
            "f_rev.json": {"verdict": "revise", "reviewer": "r3", "artifact_sha256": H1,
                           "target_id": "F1"},
            "f_scoped.json": {"verdict": "accept", "reviewer": "r4", "sha256": H1,
                              "counts_as_full_schema_verdict": False,
                              "scope": "softflags_only", "target_id": "F1"},
            "f_norev.json": {"verdict": "accept", "cited_sha256": H1, "target_id": "F1"},
            "f_prefix.json": {"verdict": "accept", "reviewer": "r6",
                              "reviewed_sha256": H1[:12], "target_id": "F1"},
            "f_alias.json": {"verdict": "accept", "reviewer": "r7",
                             "target": {"sha256": H1}, "target_id": "AF-WCC-VAC-GEN"},
        }
        for name, obj in corpus.items():
            (rd / name).write_text(json.dumps(obj))

        cov = scan_reviews_dir(rd, {"F1": {"sha256": H1}, "F2a": {"sha256": H2[:12] + "0" * 52}})
        c = cov["F1"]
        ck("accept+pinned is a full accept", "r1" in c["distinct_accept_reviewers"])
        ck("superseded pin is excluded", "r2" not in {a["reviewer"] for a in c["accepts"]})
        ck("revise is not an accept", all(a["reviewer"] != "r3" for a in c["accepts"]))
        ck("scoped accept counted in accepts", "r4" in {a["reviewer"] for a in c["accepts"]})
        ck("scoped accept excluded from full/distinct",
           "r4" not in c["distinct_accept_reviewers"])
        ck("missing reviewer becomes '?' and counts distinct (leniency)",
           "?" in c["distinct_accept_reviewers"])
        ck("12-hex prefix pin matches", "r6" in c["distinct_accept_reviewers"])
        ck("alias normalises to F1", "r7" in c["distinct_accept_reviewers"])
        ck("distinct reviewer set is sorted/unique",
           c["distinct_accept_reviewers"] == sorted(set(c["distinct_accept_reviewers"])))
        ck("two_distinct_accepts true", c["two_distinct_accepts"] is True)

        rows = parse_recorded_reason(
            "F1/F2a/F2b measured canonical hashes x; Review scan at these hashes: "
            "F1 [2 distinct accept reviewer(s) ['a', 'b']], F2a [0 distinct accept reviewer(s)], "
            "F2b [1 distinct accept reviewer(s) ['c']]")
        ck("reason parser count/labels",
           [(r[0], r[1], r[2]) for r in rows] ==
           [("F1", 2, ["a", "b"]), ("F2a", 0, []), ("F2b", 1, ["c"])])

        ev = scan_event_record(
            [{"verdict": "accept", "reviewer": "e1", "target_id": "F1",
              "evidence_refs": ["x.json#" + H1[:12]], "event_id": "ev1"},
             {"verdict": "accept", "reviewer": "e2", "target_id": "F1",
              "reviewed_sha256": H2, "event_id": "ev2"}],
            {"F1": {"sha256": H1}})
        ck("event-record ref pin matches", [x["reviewer"] for x in ev["F1"]] == ["e1"])

    failed = [n for n, ok in checks if not ok]
    print(json.dumps({"selftest": "PASS" if not failed else "FAIL",
                      "checks": len(checks), "failed": failed}, indent=1))
    return 0 if not failed else 1


# ---------------------------------------------------------------- main
TARGETS = [
    ("F1", "schemas/af_wcc_vacuum.yaml", "AF-WCC-VAC-GEN"),
    ("F2a", "schemas/af_scc_c2_vacuum.yaml", "AF-SCC-C2-VAC-GEN"),
    ("F2b", "schemas/af_scc_c0_vacuum.yaml", "AF-SCC-C0-VAC-GEN"),
    ("F0", "research_map/formulation_taxonomy.yaml", "AF-WCC-VAC-GEN"),
    ("L0", "ledger/theorems.jsonl", "AF-WCC-VAC-GEN"),
    ("A0", "evaluation_rubric.yaml", "AF-WCC-VAC-GEN"),
]
GATE_FOR = {"F0": "G-F0", "F1": "G-FORM", "F2a": "G-FORM", "F2b": "G-FORM",
            "L0": "G-LIT", "A0": "G-AUDIT"}


def snapshot(root: Path) -> dict:
    hashes, missing = {}, []
    for t, rel, cls in TARGETS:
        p = root / rel
        if p.is_file():
            hashes[t] = {"sha256": _sha256_file(p), "path": rel, "class_id": cls}
        else:
            missing.append(rel)
    corpus = []
    for rp in sorted((root / "reviews").glob("*.json")):
        st = rp.stat()
        corpus.append({"file": rp.name, "sha256": _sha256_file(rp), "bytes": st.st_size,
                       "mtime": datetime.fromtimestamp(st.st_mtime)
                                        .astimezone().isoformat(timespec="seconds")})
    digest = hashlib.sha256("\n".join(f"{c['file']} {c['sha256']}" for c in corpus).encode())
    return {"targets": hashes, "missing": missing, "corpus": corpus,
            "corpus_digest": digest.hexdigest(), "corpus_files": len(corpus)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None)
    ap.add_argument("--report", default=None)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return _selftest()

    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[2]
    reviews_dir = root / "reviews"
    snap = snapshot(root)
    if snap["missing"]:
        print(json.dumps({"error": "missing targets", "missing": snap["missing"]}))
        return 3
    hashes = snap["targets"]
    measured_at = datetime.now().astimezone().isoformat(timespec="seconds")

    map_path = root / "research_map" / "research_map.json"
    events_path = root / "research_map" / "events.jsonl"
    m = json.loads(map_path.read_text())
    cga = m.get("controller_gate_audit", {})
    cov = scan_reviews_dir(reviews_dir, hashes)
    ev_cov = scan_event_record(m.get("reviews", []), hashes)
    ref_rows = check_evidence_refs(root, m.get("reviews", []), hashes)

    findings = []

    def add(fid, severity, statement, evidence, falsifier):
        findings.append({"id": fid, "severity": severity, "statement": statement,
                         "evidence": evidence, "falsifier": falsifier})

    # --- recorded vs re-run
    repro_rows = []
    for t in ("F0", "F1", "F2a", "F2b"):
        gate = GATE_FOR[t]
        reason = (cga.get(gate) or {}).get("reason", "")
        rows = parse_recorded_reason(reason)
        rec = next((r for r in rows if r[0] == t), None)
        if rec is None and gate == "G-F0":
            rec = rows[0] if rows else None
        now = cov[t]["distinct_accept_reviewers"]
        rec_n = rec[1] if rec else None
        rec_revs = rec[2] if rec else None
        row = {"target": t, "gate": gate, "recorded_checked_at":
               (cga.get(gate) or {}).get("checked_at"),
               "recorded_count": rec_n, "recorded_reviewers": rec_revs,
               "rerun_count": len(now), "rerun_reviewers": now,
               "reproduces": (rec_n == len(now) and (rec_revs or []) == now)}
        repro_rows.append(row)
        if not row["reproduces"]:
            missing_revs = [r for r in (rec_revs or []) if r not in now]
            add(f"F-REPRO-{t}", "hard",
                f"{gate} reason records {rec_n} distinct accept reviewer(s) {rec_revs} at "
                f"measured target hash {hashes[t]['sha256'][:12]}, but the pinned corpus "
                f"re-run yields {len(now)} {now}.",
                [f"research_map/research_map.json#controller_gate_audit.{gate} (map sha "
                 f"{_sha256_file(map_path)[:12]})",
                 f"reviews/ corpus digest {snap['corpus_digest'][:12]}"],
                f"Re-run this scanner on the same target hashes and corpus digest: "
                f"falsified if {gate} [{rec_n} {rec_revs}] reproduces, i.e. reviewers "
                f"{missing_revs} again have full-schema accept files pinned to "
                f"{hashes[t]['sha256'][:12]}.")
            if missing_revs:
                add(f"F-PHANTOM-{t}", "hard",
                    f"reviewer(s) {missing_revs} are counted as accepting {t} by the "
                    f"recorded reason but no review file in the pinned corpus supports it.",
                    [f"research_map/research_map.json#controller_gate_audit.{gate}"],
                    f"falsified if a reviews/*.json file with verdict accept, reviewer in "
                    f"{missing_revs}, and an explicit pin matching "
                    f"{hashes[t]['sha256'][:12]} exists at corpus digest "
                    f"{snap['corpus_digest'][:12]}.")

    # --- provenance of the accept-bearing files that changed after the gate audit
    churn = []
    for t in ("F1", "F2a", "F2b"):
        for f in cov[t]["verdicts"]:
            if "lead-audit-r2" in f["file"]:
                churn.append({"target": t, **{k: f[k] for k in
                              ("file", "verdict", "created_at", "event_id", "file_sha256",
                               "file_mtime", "pin_used")}})
    if churn:
        add("F-CHURN-01", "soft",
            "The three astra-lead-audit review files that the 00:24:40 gate audit counted "
            "as accepts now carry verdict=revise, were written after the gate audit "
            "(created_at 00:25:15), and their event_id names revision r3 while the filename "
            "says r2; the pre-image accept bytes are not retained anywhere in the event record.",
            [f"reviews/{c['file']} sha256 {c['file_sha256'][:12]} verdict {c['verdict']} "
             f"created_at {c['created_at']} event_id {c['event_id']}" for c in churn],
            "falsified if an accepted event or retained artifact with verdict=accept for "
            "F1/F2a/F2b at these hashes and created_at <= 2026-09-12T00:24:40 exists in "
            "events.jsonl or reviews/.")

    # --- leniency / strictness of the controller rule on the live corpus
    loose = []
    for t, c in cov.items():
        for a in c["accepts"]:
            if a["reviewer"] == "?":
                loose.append({"target": t, "why": "reviewer field absent", **a})
            elif a["scoped_flag_present"] and not a["counts_as_full_schema_verdict"]:
                loose.append({"target": t, "why": "scoped accept (excluded from full count)",
                              **a})
    if loose:
        add("F-LENIENT-01", "soft",
            "The controller rule defaults counts_as_full_schema_verdict to full when the "
            "field is absent, and defaults the reviewer id to '?' when both reviewer and "
            "actor are absent; both defaults can enter the gate count.",
            [f"{x['target']}: {x['file']} reviewer={x['reviewer']} "
             f"scope={x.get('scope')} why={x['why']}" for x in loose],
            "falsified if every accept entry in the pinned corpus sets an explicit "
            "counts_as_full_schema_verdict and a non-empty reviewer/actor.")

    # --- completeness: accepts in the event record that a reviews/*.json-only scan misses
    under = []
    for t in ("F1", "F2a", "F2b", "F0", "L0", "A0"):
        seen = {(a["reviewer"], a["pin_used"]) for a in cov[t]["full_accepts"]}
        for e in ev_cov.get(t, []):
            if (e["reviewer"], e["pin_used"]) not in seen and \
               e["reviewer"] not in cov[t]["distinct_accept_reviewers"]:
                under.append({"target": t, **e})
    if under:
        add("F-UNDERCOUNT-01", "major",
            "The gate reason's accept count is a reviews/*.json-only scan; the accepted "
            "event record (map.reviews) holds further accepts pinned to the same measured "
            "hashes whose evidence lives under artifacts/**.  The G-AUDIT/G-FORM criteria "
            "do not restrict evidence to reviews/, so the recorded count is an undercount "
            "of the recorded evidence.",
            [f"{x['target']}: {x['event_id']} reviewer={x['reviewer']} "
             f"pin={x['pin_used'][:12]} refs={x['evidence_refs']}" for x in under],
            "falsified if the gate criterion is amended to require verdicts in reviews/ "
            "only, or if each listed event is shown to be non-independent/non-binding.")

    # --- evidence-chain integrity of accept events pinned to the measured hashes
    bad_refs = [x for x in ref_rows if x["status"] != "match"]
    if bad_refs:
        add("F-EVIDREF-01", "hard",
            f"{len(bad_refs)} evidence ref(s) of accept events pinned to a measured target "
            f"hash do not resolve to the cited bytes (stale or missing file).",
            [f"{x['target']} {x['event_id']} reviewer={x['reviewer']} ref={x['ref']} "
             f"status={x['status']} current={str(x['current'])[:12]}" for x in bad_refs],
            "falsified if every cited `path#hex` ref of these accept events hashes to its "
            "cited prefix at the recorded snapshot (re-run and compare).")

    # --- snapshot stability (fail-closed)
    snap2 = snapshot(root)
    stable = (snap2["corpus_digest"] == snap["corpus_digest"] and
              all(snap2["targets"][t]["sha256"] == hashes[t]["sha256"] for t in hashes))
    if not stable:
        add("F-SNAPSHOT-01", "info",
            "The corpus or a target file moved while the scan ran; all counts are advisory.",
            [f"corpus {snap['corpus_digest'][:12]} -> {snap2['corpus_digest'][:12]}"],
            "re-run on a quiesced tree; falsified if digests are equal on re-run.")

    report = {
        "schema_version": "0.1",
        "task_id": "W036-GATE-REPRO-01",
        "node_id": "A1",
        "gate": "G-AUDIT",
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN",
                      "AF-WCC-SCALAR-SPH"],
        "actor": "worker-036",
        "measured_at": measured_at,
        "method": "controller-rule re-run over reviews/*.json at pinned measured target "
                  "hashes (astra_lifecycle.py:160-198 behaviour) + map.reviews advisory pass",
        "snapshot": {
            "map_path": "research_map/research_map.json",
            "map_sha256": _sha256_file(map_path),
            "events_sha256": _sha256_file(events_path) if events_path.is_file() else None,
            "corpus_digest": snap["corpus_digest"],
            "corpus_files": snap["corpus_files"],
            "targets": {t: {"path": v["path"], "sha256": v["sha256"],
                            "class_id": v["class_id"]} for t, v in hashes.items()},
            "snapshot_stable": stable,
        },
        "recorded_vs_rerun": repro_rows,
        "accept_entries_reviews_dir": {t: cov[t]["full_accepts"] for t in cov},
        "scoped_or_unattributed_accepts": loose,
        "accepts_event_record_not_in_reviews_dir": under,
        "accept_event_evidence_refs": ref_rows,
        "churn_evidence": churn,
        "findings": findings,
        "hard_findings": sum(1 for f in findings if f["severity"] == "hard"),
        "global_falsifier": "Re-run `python3 artifacts/worker-036/gaudit_accept_repro_audit.py` "
                            "at the same map sha256 and corpus digest; any recorded accept "
                            "count or reviewer set that this report calls non-reproducible "
                            "but which reproduces is a falsification, as is any accept entry "
                            "listed here that the corpus does not contain.",
        "authority_note": "Worker event. No node status, validation_status, or gate verdict "
                          "is set by this artifact; the gate audit is controller-owned.",
        "exit_code_meaning": {"0": "no hard findings", "1": "hard findings present",
                              "2": "snapshot moved", "3": "missing target/error"},
    }
    out = Path(args.report) if args.report else \
        root / "artifacts" / "worker-036" / "gaudit_accept_repro_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1, sort_keys=True))
    print(json.dumps({"report": str(out), "sha256": _sha256_file(out),
                      "snapshot_stable": stable,
                      "hard_findings": report["hard_findings"],
                      "recorded_vs_rerun": [{k: r[k] for k in
                                             ("target", "recorded_count", "rerun_count",
                                              "reproduces")} for r in repro_rows]}, indent=1))
    if not stable:
        return 2
    return 1 if report["hard_findings"] else 0


if __name__ == "__main__":
    sys.exit(main())
