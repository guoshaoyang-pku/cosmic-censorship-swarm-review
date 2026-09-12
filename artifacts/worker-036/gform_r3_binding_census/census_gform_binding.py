#!/usr/bin/env python3
"""W036-GFORM-R3-BIND-01 -- per-class G-FORM rev29 accept-coverage census.

Question taken (worker-036, bounded round; no inbox card existed):

    At the live FROZEN rev29 pins, does the controller's recorded G-FORM coverage
    (controller_gate_audit: F1 / F2a / F2b distinct-accept-reviewer counts) reproduce
    against the review corpus, and if not, which review files bind what -- and is each
    binding accept's own evidence chain (FROZEN pin, path#sha256 refs) still on disk?

This is a *binding census*, not a schema review.  It re-implements the controller's exact
review-coverage rule (research_map/astra_lifecycle.py:176-214, read 2026-09-12T01:1x) and
cross-checks it against the earlier independent worker-036 implementation
(artifacts/worker-036/gaudit_accept_repro_audit.py).  All corpus analysis runs on ONE
in-memory snapshot of reviews/*.json (read once), which is byte-pinned under pinned/ so the
report can be re-derived after the live corpus moves.  Canonical/FROZEN pins are measured at
entry and exit; drift inside the run makes the snapshot void (exit 2).

Writes ONLY under this artifact directory.  Never writes a canonical path, the map, or
runtime/state/artifact_hashes.json.

Exit codes: 0 = census valid (findings may still exist); 2 = canonical/FROZEN pin drift inside
the run (report still written, claim void); 1 = internal validity check failed.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import shutil
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CST = timezone(timedelta(hours=8))
REVIEWS = ROOT / "reviews"
MAP = ROOT / "research_map" / "research_map.json"
EVENTS = ROOT / "research_map" / "events.jsonl"
FROZEN = ROOT / "artifacts" / "formulation" / "FROZEN.json"
SCANNER = ROOT / "artifacts" / "worker-036" / "gaudit_accept_repro_audit.py"
REV12_ARCHIVE = (ROOT / "artifacts" / "worker-066" / "f2b_rev29_containment_binding" /
                 "pinned" / "c0_rev12_archive__c0_live__af_scc_c0_vacuum.yaml")
FROZEN_REV29 = "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"

# ---------------------------------------------------------------- controller rule (transcribed)
# research_map/astra_lifecycle.py:130-214 -- VERDICT_KINDS, TARGET_ALIASES, _explicit_pins,
# prefix-either-way matching on 12 hex, counts_as_full_schema_verdict is not False.
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

TARGETS = {
    "F1": {"class_id": "AF-WCC-VAC-GEN", "canonical": "schemas/af_wcc_vacuum.yaml",
           "mirror": "artifacts/formulation/schemas/af_wcc_vacuum.yaml"},
    "F2a": {"class_id": "AF-SCC-C2-VAC-GEN", "canonical": "schemas/af_scc_c2_vacuum.yaml",
            "mirror": "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"},
    "F2b": {"class_id": "AF-SCC-C0-VAC-GEN", "canonical": "schemas/af_scc_c0_vacuum.yaml",
            "mirror": "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"},
}
TOKENS = {
    "F1": ("AF-WCC-VAC-GEN", "af_wcc_vacuum.yaml", '"F1"'),
    "F2a": ("AF-SCC-C2-VAC-GEN", "af_scc_c2_vacuum.yaml", '"F2a"', "F2A"),
    "F2b": ("AF-SCC-C0-VAC-GEN", "af_scc_c0_vacuum.yaml", '"F2b"', "F2B"),
}
HEX12 = re.compile(r"^[0-9a-f]{12,64}$")
ANYHEX = re.compile(r"\b[0-9a-f]{12,64}\b")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts).astimezone(CST).isoformat(timespec="seconds")


# ---------------------------------------------------------------- corpus snapshot (one read)
def read_corpus() -> dict:
    """reviews/*.json read exactly once into memory; the census binds to these bytes."""
    snap = {}
    for rp in sorted(REVIEWS.glob("*.json")):
        try:
            raw = rp.read_bytes()
        except OSError:
            continue
        snap[rp.name] = {"bytes": raw, "sha256": sha256_bytes(raw),
                         "mtime": iso(rp.stat().st_mtime), "path": rp}
    return snap


def corpus_digest(snap: dict) -> str:
    return sha256_bytes("".join(f"{n}\0{s['sha256']}\n" for n, s in sorted(snap.items())).encode())


def disk_state(names: list) -> dict:
    out = {}
    for n in names:
        p = REVIEWS / n
        if p.is_file():
            out[n] = sha256_file(p)
    return out


# ---------------------------------------------------------------- controller rule
def targets_in_review(d: dict) -> set:
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


def explicit_pins(d: dict) -> list:
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


def pin_matches(pin: str, h: str) -> bool:
    return bool(pin) and bool(h) and (pin.startswith(h[:12]) or h.startswith(pin[:12]))


def controller_scan(snap: dict, hashes: dict) -> dict:
    """Independent re-implementation of astra_lifecycle.review_coverage at snapshot bytes."""
    cov = {t: {"verdicts": [], "accepts": [], "full_accepts": [], "scoped_accepts": [],
               "distinct_accept_reviewers": []} for t in hashes}
    for name, s in sorted(snap.items()):
        try:
            d = json.loads(s["bytes"].decode())
        except Exception:
            continue
        v = str(d.get("verdict", "")).lower()
        if v not in VERDICT_KINDS:
            continue
        reviewer = str(d.get("reviewer") or d.get("actor") or "?")
        full = d.get("counts_as_full_schema_verdict") is not False
        pins = explicit_pins(d)
        for t in targets_in_review(d):
            if t not in cov:
                continue
            matched = sorted({p for p in pins if pin_matches(p, hashes[t]["sha256"])},
                             key=lambda p: (-len(p), p))
            if not matched:
                continue
            entry = {"file": name, "reviewer": reviewer, "verdict": v,
                     "counts_as_full_schema_verdict": full, "pin_used": matched[0],
                     "sha256": s["sha256"]}
            cov[t]["verdicts"].append(entry)
            if v == "accept":
                cov[t]["accepts"].append(entry)
                (cov[t]["full_accepts"] if full else cov[t]["scoped_accepts"]).append(entry)
    for c in cov.values():
        c["distinct_accept_reviewers"] = sorted({a["reviewer"] for a in c["full_accepts"]})
        c["two_distinct_accepts"] = len(c["distinct_accept_reviewers"]) >= 2
    return cov


def load_scanner():
    if not SCANNER.is_file():
        return None
    spec = importlib.util.spec_from_file_location("w036_gaudit_scanner", SCANNER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def historical_hashes() -> dict:
    """Hashes that were pinned to a canonical/mirror path in the accepted event stream.

    Deliberately precise: only (a) artifact events whose `path` is the canonical or mirror
    path, (b) evidence/artifact refs of the exact form `<canonical-or-mirror-path>#<hex>`,
    and (c) explicit pin fields on events whose target resolves to the class.  Prose mentions
    of a filename must not enter this registry (an earlier draft scanned whole lines and swept
    in every unrelated hash in the stream).
    """
    hist = {t: set() for t in TARGETS}
    paths = {t: (TARGETS[t]["canonical"], TARGETS[t]["mirror"]) for t in TARGETS}
    ref_re = {t: re.compile(r"^(?:" + "|".join(re.escape(p) for p in paths[t]) +
                            r")#([0-9a-f]{12,64})$") for t in TARGETS}
    if EVENTS.is_file():
        with EVENTS.open(errors="replace") as fh:
            for line in fh:
                try:
                    ev = json.loads(line)
                except Exception:
                    continue
                for t in TARGETS:
                    p, h = ev.get("path"), ev.get("sha256")
                    if isinstance(p, str) and isinstance(h, str) and p in paths[t]:
                        hist[t].add(h.lower())
                    for key in ("evidence_refs", "artifact_refs"):
                        for ref in ev.get(key) or []:
                            if isinstance(ref, str):
                                m = ref_re[t].match(ref)
                                if m:
                                    hist[t].add(m.group(1))
                            elif isinstance(ref, dict):
                                rp, rh = ref.get("path"), ref.get("sha256")
                                if isinstance(rp, str) and isinstance(rh, str) and rp in paths[t]:
                                    hist[t].add(rh.lower())
                    tid = ev.get("target_id")
                    if isinstance(tid, str):
                        norm = TARGET_ALIASES.get(tid, TARGET_ALIASES.get(tid.upper(), tid))
                        if norm == t:
                            for key in PIN_KEYS:
                                hv = ev.get(key)
                                if isinstance(hv, str):
                                    hist[t].add(hv.lower())
    if REV12_ARCHIVE.is_file():
        hist["F2b"].add(sha256_file(REV12_ARCHIVE))
    return {t: {h for h in hs if len(h) >= 12} for t, hs in hist.items()}


def classify_pin(pin: str, current: str, hist: set) -> str:
    if pin_matches(pin, current):
        return "canonical"
    for frag in hist:
        if pin.startswith(frag[:12]) or frag.startswith(pin[:12]):
            return f"historical:{frag[:12]}"
    return "unknown"


def inclusive_census(snap: dict, hashes: dict, hist: dict) -> list:
    """Every review file mentioning a G-FORM token, with binding classification."""
    rows = []
    for name, s in sorted(snap.items()):
        text = s["bytes"].decode(errors="replace")
        mentioned = sorted({t for t, toks in TOKENS.items() if any(tok in text for tok in toks)})
        if not mentioned:
            continue
        base = {"file": name, "sha256": s["sha256"], "mtime": s["mtime"], "mentioned": mentioned}
        try:
            d = json.loads(text)
        except Exception:
            rows.append({**base, "status": "unparseable_json"})
            continue
        v = str(d.get("verdict", "")).lower()
        tgts = sorted(targets_in_review(d) & set(hashes))
        pins = explicit_pins(d)
        row = {**base, "targets": tgts, "verdict": v or None,
               "reviewer": str(d.get("reviewer") or d.get("actor") or "?"),
               "created_at": d.get("created_at"), "pins_declared": sorted(pins),
               "counts_as_full_schema_verdict": d.get("counts_as_full_schema_verdict"),
               "blind": d.get("blind")}
        if v not in VERDICT_KINDS:
            row["status"] = "no_standard_verdict"
        elif not tgts:
            row["status"] = "target_not_alias_resolved"
        else:
            binding = [t for t in tgts if any(pin_matches(p, hashes[t]["sha256"]) for p in pins)]
            if binding:
                row["binding_targets"] = binding
                row["status"] = ("binding_full_accept" if v == "accept" and
                                 d.get("counts_as_full_schema_verdict") is not False
                                 else "binding_scoped_accept" if v == "accept"
                                 else "binding_non_accept")
            else:
                cls = {p: classify_pin(p, hashes[tgts[0]]["sha256"], hist.get(tgts[0], set()))
                       for p in pins}
                row["pin_class"] = cls
                if v == "accept" and any(c.startswith("historical") for c in cls.values()):
                    row["status"] = "accept_pin_superseded"
                elif v == "accept":
                    row["status"] = "accept_pin_not_canonical"
                else:
                    row["status"] = "verdict_pin_not_canonical"
        rows.append(row)
    return rows


def refs_of(d: dict) -> list:
    refs = []
    for key in ("evidence_refs", "artifact_refs"):
        for ref in d.get(key) or []:
            if isinstance(ref, str):
                refs.append(ref)
            elif isinstance(ref, dict):
                p = ref.get("path") or ref.get("ref")
                if isinstance(p, str):
                    refs.append(p + (f"#{str(ref.get('sha256'))[:12]}" if ref.get("sha256") else ""))
    return refs


def resolve_refs(d: dict) -> list:
    out = []
    for ref in refs_of(d):
        if "#" not in ref:
            continue
        path, frag = ref.rsplit("#", 1)
        frag = frag.strip().lower()
        if not HEX12.match(frag):
            continue
        fp = ROOT / path
        rec = {"ref": ref, "cited": frag}
        if not fp.is_file():
            rec["status"] = "missing"
        else:
            cur = sha256_file(fp)
            rec["status"] = "match" if cur.startswith(frag[:12]) else "stale"
            rec["current"] = None if rec["status"] == "match" else cur
        out.append(rec)
    return out


def binding_details(snap: dict, census: list, hashes: dict) -> list:
    out = []
    for row in census:
        if row.get("status") != "binding_full_accept":
            continue
        s = snap[row["file"]]
        text = s["bytes"].decode(errors="replace")
        d = json.loads(text)
        pins = explicit_pins(d)
        hexes = {m.group(0)[:12] for m in ANYHEX.finditer(text)}
        out.append({
            "file": row["file"], "sha256": row["sha256"], "reviewer": row["reviewer"],
            "targets": row["binding_targets"], "created_at": row.get("created_at"),
            "mtime": row.get("mtime"), "blind": row.get("blind"), "score": d.get("score"),
            "counts_as_full_schema_verdict": row.get("counts_as_full_schema_verdict"),
            "hard_failures": (d.get("hard_failures") if isinstance(d.get("hard_failures"), list)
                              else len(d.get("hard_failures") or []) if d.get("hard_failures") else 0),
            "cites_frozen_rev29": FROZEN_REV29[:12] in hexes,
            "frozen_pins_in_file": sorted(h for h in hexes if h.startswith("815e0807") or
                                          h.startswith("3d9e3d77")),
            "hash_stable_before_after": d.get("hash_stable_before_after"),
            "pin_used": sorted({p for p in pins if any(
                pin_matches(p, hashes[t]["sha256"]) for t in row["binding_targets"])},
                key=lambda p: (-len(p), p)),
            "evidence": resolve_refs(d),
        })
    return out


# ---------------------------------------------------------------- selftest
def selftest() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="w036bind_selftest_", dir=str(HERE)))
    try:
        cur, old = "a" * 64, "b" * 64

        def fake(name, obj):
            raw = json.dumps(obj).encode()
            return (name, {"bytes": raw, "sha256": sha256_bytes(raw), "mtime": "t",
                           "path": tmp / name})

        snap = dict([
            fake("accept-current.json", {"verdict": "accept", "target_id": "F2b",
                                         "reviewed_sha256": cur, "reviewer": "r1"}),
            fake("accept-prefix.json", {"verdict": "accept", "target_id": "AF-SCC-C0-VAC-GEN",
                                        "artifact_sha256": cur[:12], "actor": "r2"}),
            fake("accept-superseded.json", {"verdict": "accept", "target_id": "F2b",
                                            "reviewed_sha256": old, "reviewer": "r3"}),
            fake("revise-current.json", {"verdict": "revise", "target_id": "F2b",
                                         "reviewed_sha256": cur, "reviewer": "r4"}),
            fake("scoped-accept.json", {"verdict": "accept", "target_id": "F2b",
                                        "reviewed_sha256": cur, "reviewer": "r5",
                                        "counts_as_full_schema_verdict": False}),
            fake("accept-unpinned.json", {"verdict": "accept", "target_id": "F2b", "reviewer": "r6"}),
            fake("merged-alias.json", {"verdict": "accept",
                                       "target": {"target_subnode": "F2b", "sha256": cur},
                                       "reviewer": "r7"}),
            fake("other-target.json", {"verdict": "accept", "target_id": "L0",
                                       "reviewed_sha256": cur, "reviewer": "r8"}),
        ])
        hashes = {"F2b": {"sha256": cur}}
        cov = controller_scan(snap, hashes)
        ck = []
        ck.append(("current_accepts_counted",
                   {"r1", "r2"} <= set(cov["F2b"]["distinct_accept_reviewers"])))
        ck.append(("superseded_accept_excluded", "r3" not in cov["F2b"]["distinct_accept_reviewers"]))
        ck.append(("revise_excluded", "r4" not in cov["F2b"]["distinct_accept_reviewers"]))
        ck.append(("scoped_accept_not_full",
                   "r5" not in cov["F2b"]["distinct_accept_reviewers"] and
                   any(a["file"] == "scoped-accept.json" for a in cov["F2b"]["scoped_accepts"])))
        ck.append(("unpinned_excluded", "r6" not in cov["F2b"]["distinct_accept_reviewers"]))
        ck.append(("nested_pin_counted", "r7" in cov["F2b"]["distinct_accept_reviewers"]))
        ck.append(("other_target_isolated",
                   all(a["file"] != "other-target.json" for a in cov["F2b"]["accepts"])))
        ck.append(("classify_pin", classify_pin(old, cur, {old}) == f"historical:{old[:12]}"
                   and classify_pin(cur, cur, set()) == "canonical"
                   and classify_pin("c" * 64, cur, set()) == "unknown"))
        rows = inclusive_census(snap, hashes, {"F2b": {old}})
        by = {r["file"]: r for r in rows}
        ck.append(("census_current_bound", by["accept-current.json"]["status"] == "binding_full_accept"))
        ck.append(("census_superseded_classified",
                   by["accept-superseded.json"]["status"] == "accept_pin_superseded"))
        ck.append(("census_scoped_classified",
                   by["scoped-accept.json"]["status"] == "binding_scoped_accept"))
        return 0 if all(ok for _, ok in ck) else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------- report
def build(stamp: str) -> dict:
    frozen_sha = sha256_file(FROZEN)
    manifest = json.loads(FROZEN.read_text())
    canonical = {}
    for t, spec in TARGETS.items():
        cpath, mpath = ROOT / spec["canonical"], ROOT / spec["mirror"]
        csha, msha = sha256_file(cpath), sha256_file(mpath)
        canonical[t] = {
            "class_id": spec["class_id"], "canonical": spec["canonical"],
            "canonical_sha256": csha, "mirror": spec["mirror"], "mirror_sha256": msha,
            "mirror_bytes_identical": csha == msha,
            "manifest_declared_canonical": manifest.get("files", {}).get(spec["canonical"], {}).get("sha256"),
            "manifest_declared_mirror": manifest.get("files", {}).get(spec["mirror"], {}).get("sha256"),
        }
    hashes = {t: {"sha256": canonical[t]["canonical_sha256"]} for t in TARGETS}

    snap = read_corpus()
    snap_digest = corpus_digest(snap)
    map_bytes = MAP.read_bytes()
    map_sha = sha256_bytes(map_bytes)
    m = json.loads(map_bytes)
    gate_doc = (m.get("controller_gate_audit") or {}).get("G-FORM") or {}
    reason, checked_at = gate_doc.get("reason", ""), gate_doc.get("checked_at")

    cov = controller_scan(snap, hashes)
    scanner = load_scanner()
    xcheck = None
    if scanner is not None:
        # cross-check the two implementations on byte-pinned copies, so it cannot read
        # different bytes than the snapshot
        pintmp = Path(tempfile.mkdtemp(prefix="xcheck_", dir=str(HERE)))
        try:
            for name, s in snap.items():
                (pintmp / name).write_bytes(s["bytes"])
            xcov = scanner.scan_reviews_dir(pintmp, hashes)
            xcheck = {"agree": all(cov[t]["distinct_accept_reviewers"] ==
                                   xcov[t]["distinct_accept_reviewers"] for t in TARGETS),
                      "scanner_accepts": {t: xcov[t]["distinct_accept_reviewers"] for t in TARGETS}}
        finally:
            shutil.rmtree(pintmp, ignore_errors=True)

    hist = historical_hashes()
    census = inclusive_census(snap, hashes, hist)
    binding = binding_details(snap, census, hashes)
    relevant = sorted(r["file"] for r in census)

    # byte-pin the relevant files so the report survives corpus movement
    pin_dir = HERE / "pinned"
    if pin_dir.exists():
        shutil.rmtree(pin_dir)
    pin_dir.mkdir(parents=True)
    for name in relevant:
        (pin_dir / name).write_bytes(snap[name]["bytes"])
    pin_manifest = {name: snap[name]["sha256"] for name in relevant}
    (pin_dir / "MANIFEST.json").write_text(json.dumps(pin_manifest, indent=1, sort_keys=True) + "\n")

    end_disk = disk_state(sorted(snap))
    grew = sorted(set(end_disk) - set(snap))
    changed = sorted(n for n in set(end_disk) & set(snap) if end_disk[n] != snap[n]["sha256"])
    relevant_changed = [n for n in changed if n in relevant]
    end_pins = {t: sha256_file(ROOT / TARGETS[t]["canonical"]) for t in TARGETS}
    pin_drift = sorted([t for t in TARGETS if end_pins[t] != hashes[t]["sha256"]] +
                       (["frozen"] if sha256_file(FROZEN) != frozen_sha else []))

    rec = {}
    for t in TARGETS:
        mm = re.search(rf"{re.escape(t)} \[(\d+) distinct accept reviewer\(s\)"
                       rf"(?:\s*\[([^\]]*)\])?", reason)
        rec[t] = {"count": int(mm.group(1)) if mm else None,
                  "reviewers": re.findall(r"'([^']*)'", mm.group(2) or "") if mm else []}
    if scanner is not None:
        xrec = scanner.parse_recorded_reason(reason)
        xmap = {label: (n, revs) for label, n, revs in xrec}
        for t in TARGETS:
            got = xmap.get(t)
            if got and (got[0] != rec[t]["count"] or sorted(got[1]) != sorted(rec[t]["reviewers"])):
                rec[t]["crosscheck_mismatch"] = {"scanner": got}

    validity = []

    def ck(name, cond, detail=""):
        validity.append({"name": name, "pass": bool(cond), "detail": detail})
        return bool(cond)

    ck("frozen_manifest_measured", frozen_sha == FROZEN_REV29,
       f"revision={manifest.get('revision')} sha={frozen_sha[:12]}")
    ck("three_mirror_pairs_byte_identical", all(canonical[t]["mirror_bytes_identical"] for t in TARGETS))
    ck("manifest_declares_all_six_pins",
       all(canonical[t]["manifest_declared_canonical"] == canonical[t]["canonical_sha256"] and
           canonical[t]["manifest_declared_mirror"] == canonical[t]["mirror_sha256"] for t in TARGETS))
    ck("two_implementations_agree", xcheck is None or xcheck["agree"],
       json.dumps(xcheck["scanner_accepts"]) if xcheck else "scanner unavailable")
    ck("selftest", selftest() == 0)
    ck("pins_stable_within_run", not pin_drift, str(pin_drift))
    ck("recorded_reason_parse_crosscheck",
       all("crosscheck_mismatch" not in rec[t] for t in TARGETS))

    findings = []

    def fnd(fid, severity, statement, evidence):
        findings.append({"id": fid, "severity": severity, "statement": statement,
                         "evidence": evidence})

    for t in TARGETS:
        fresh = cov[t]["distinct_accept_reviewers"]
        if rec[t]["count"] != len(fresh) or sorted(rec[t]["reviewers"]) != fresh:
            lost = sorted(set(rec[t]["reviewers"]) - set(fresh))
            added = sorted(set(fresh) - set(rec[t]["reviewers"]))
            fnd(f"W036-BIND-{t}", "major",
                f"Recorded G-FORM coverage for {t} is stale at map checked_at {checked_at}: "
                f"recorded {rec[t]['count']} {rec[t]['reviewers']} vs fresh {len(fresh)} {fresh} "
                f"at {hashes[t]['sha256'][:12]}."
                + (f" No longer binding: {lost}." if lost else "")
                + (f" Newly binding: {added}." if added else ""),
                [f"research_map/research_map.json#{map_sha[:12]}"] +
                [f"reviews/{a['file']}#{a['sha256'][:12]}" for a in cov[t]["full_accepts"]])
            for rev in lost:
                rows = [r for r in census if r.get("reviewer") == rev and t in (r.get("targets") or [])]
                for r in rows:
                    fnd(f"W036-BIND-CHURN-{rev}-{t}", "major",
                        f"{t}: reviewer {rev} is listed in the recorded gate reason but no longer "
                        f"holds a binding full accept in the snapshot: "
                        f"reviews/{r['file']} now reads verdict={r.get('verdict')} "
                        f"status={r.get('status')} at sha256 {r['sha256'][:12]}, "
                        f"mtime {r.get('mtime')}; the accept-bearing bytes are not preserved at "
                        f"the path, so the recorded count is not re-derivable from the path alone.",
                        [f"reviews/{r['file']}#{r['sha256'][:12]}",
                         f"research_map/research_map.json#{map_sha[:12]}"])
    for b in binding:
        if not b["cites_frozen_rev29"]:
            fnd(f"W036-BIND-FROZEN-{b['reviewer']}", "minor",
                f"{b['file']} ({b['reviewer']}) binds {b['targets']} at the canonical hash but "
                f"does not cite FROZEN rev29 {FROZEN_REV29[:12]} (CF-27 requires reviewers to pin "
                f"the FROZEN bytes plus each per-file pin).",
                [f"reviews/{b['file']}#{b['sha256'][:12]}"])
        if b["blind"] is False:
            fnd(f"W036-BIND-BLIND-{b['reviewer']}", "minor",
                f"{b['file']} ({b['reviewer']}) is a full accept but declares blind=false; "
                f"eligibility is the audit lead's call, recorded here not adjudicated.",
                [f"reviews/{b['file']}#{b['sha256'][:12]}"])
        stale = [e for e in b["evidence"] if e["status"] != "match"]
        if stale:
            fnd(f"W036-BIND-EVID-{b['reviewer']}", "minor",
                f"{b['file']} ({b['reviewer']}) is a binding full accept with "
                f"{len(stale)} stale/missing evidence ref(s): "
                + "; ".join(f"{e['ref']} -> {e['status']}" for e in stale),
                [f"reviews/{b['file']}#{b['sha256'][:12]}"])

    n_fail = sum(1 for c in validity if not c["pass"])
    report = {
        "task_id": "W036-GFORM-R3-BIND-01",
        "actor": "worker-036",
        "created_at": stamp,
        "node_id": "F1,F2a,F2b",
        "gate": "G-FORM",
        "class_ids": sorted({TARGETS[t]["class_id"] for t in TARGETS}),
        "authority_note": ("worker measurement only; issues no gate verdict, sets no node status or "
                           "validation_status, and writes no canonical path. Binding-count eligibility "
                           "(blindness, non-author status, verdict merit) is the audit lead's call."),
        "pins": {"frozen": {"path": "artifacts/formulation/FROZEN.json", "sha256": frozen_sha,
                            "revision": manifest.get("revision"),
                            "frozen_at": manifest.get("frozen_at")},
                 "targets": canonical,
                 "map": {"path": "research_map/research_map.json", "sha256": map_sha,
                         "gate_checked_at": checked_at}},
        "recorded_gate_audit": rec,
        "fresh_coverage": {t: {"distinct_accept_reviewers": cov[t]["distinct_accept_reviewers"],
                               "full_accepts": [a["file"] for a in cov[t]["full_accepts"]],
                               "scoped_accepts": [a["file"] for a in cov[t]["scoped_accepts"]],
                               "all_bound_verdicts": [a["file"] for a in cov[t]["verdicts"]]}
                           for t in TARGETS},
        "cross_check_scanner": xcheck,
        "binding_accepts": binding,
        "inclusive_census": census,
        "historical_canonical_hashes": {t: sorted(hist[t]) for t in TARGETS},
        "corpus": {"snapshot_digest": snap_digest, "files_in_snapshot": len(snap),
                   "relevant_files": len(relevant), "pinned_files": len(pin_manifest),
                   "grew_after_snapshot": grew, "changed_after_snapshot": changed,
                   "relevant_changed_after_snapshot": relevant_changed},
        "pin_drift": pin_drift,
        "validity_checks": {"passed": sum(1 for c in validity if c["pass"]), "total": len(validity),
                            "failed": [c["name"] for c in validity if not c["pass"]],
                            "list": validity},
        "findings": findings,
        "next_falsifier": ("Re-run this script at the pinned hashes. FALSIFIED if (a) any file listed "
                           "as a binding full accept no longer passes the controller rule (verdict != "
                           "accept, target alias unresolved, counts_as_full_schema_verdict false, or "
                           "pin not matching the canonical 12-hex prefix), (b) any full accept bound to "
                           "a G-FORM canonical hash in the snapshot is absent from "
                           "fresh_coverage.full_accepts, (c) any pinned file sha256 differs from "
                           "pinned/MANIFEST.json, or (d) FROZEN/canonical pins move (void, not "
                           "falsified)."),
        "snapshot_stable": n_fail == 0 and not pin_drift,
    }
    rc = 2 if pin_drift else (1 if n_fail else 0)
    return report, rc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stamp", default=None)
    ap.add_argument("--json-out", default=str(HERE / "report.json"))
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        rc = selftest()
        print("SELFTEST", "PASS" if rc == 0 else "FAIL")
        return rc
    stamp = args.stamp or datetime.now(CST).isoformat(timespec="seconds")
    report, rc = build(stamp)
    Path(args.json_out).write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print(f"CENSUS task={report['task_id']} validity={report['validity_checks']['passed']}/"
          f"{report['validity_checks']['total']} findings={len(report['findings'])} rc={rc}")
    print("recorded:", json.dumps(report["recorded_gate_audit"]))
    print("fresh   :", json.dumps({t: report["fresh_coverage"][t]["distinct_accept_reviewers"]
                                   for t in TARGETS}))
    print("binding :", json.dumps([(b["file"], b["reviewer"], b["targets"])
                                   for b in report["binding_accepts"]]))
    if report["validity_checks"]["failed"]:
        print("failed  :", report["validity_checks"]["failed"])
    for f in report["findings"]:
        print("finding :", f["id"], "-", f["statement"][:160])
    return rc


if __name__ == "__main__":
    sys.exit(main())
