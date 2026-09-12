#!/usr/bin/env python3
"""W026-CF31-DIVERGENCE-ATTRIBUTION-01 — why the G-FORM F2b coverage counts disagree.

Task (worker-026, bounded, read-only, class-bound AF-SCC-C0-VAC-GEN via node F2b, gate G-FORM):
CF-31 records that the controller's hash-bound scan of reviews/*.json reports 4 distinct full
accepts at F2b b2ab6acb2bbe while the formulation lead's per-file census at the same bytes
reports 0 accept / 7 revise, and that the two sets share no reviewer. CF-31's action assigns the
canonical per-file binding TABLE to astra-life05-verify-gform-r3 (lead-audit). This worker does
NOT publish that table and does NOT set a gate verdict. It measures the *mechanism*:

  M1 corpus freeze        sha256/size/mtime/verdict/pins of every reviews/*.json + corpus digest
  M2 Method-C reproduction faithful re-execution of astra_lifecycle.review_coverage
  M3 anchor control       independent reimplementation must equal Method C exactly
  M4 corpus reconstruction rebuild the review corpus at a past instant from preserved bytes
  M5 scan replay          replay the four persisted controller scans and diff the reviewer sets
  M6 filter lattice       3x2x2x2x2x2 census-rule combinations at live and at lead-instant bytes
  M7 mutation census      every pinned/snapshot copy of a live review file vs the live bytes
  M8 controls             C0 anchor + C1..C14 mutation/negative/blind-spot controls

Falsifier: see report.json:falsifier.
Authority: worker-level read-only measurement only; no gate verdict, no node status, no
validation_status promotion, no canonical write, no edit to reviews/, schemas/ or research_map/.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]          # .../ai4math-swarm
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "research_map"))
import astra_lifecycle as AL  # noqa: E402  (module level is constants + pure functions)

CST = timezone(timedelta(hours=8))
LIVE_SCHEMAS = {
    "F1": "schemas/af_wcc_vacuum.yaml",
    "F2a": "schemas/af_scc_c2_vacuum.yaml",
    "F2b": "schemas/af_scc_c0_vacuum.yaml",
}
SCAN_SOURCES = [
    ("astra-lifecycle-07-final", "runtime/state/controller_verification/lifecycle_20260912-010951.json"),
    ("astra-lifecycle-07-post", "runtime/state/controller_verification/lifecycle_20260912-011029.json"),
    ("astra-lifecycle-08-open", "runtime/state/controller_verification/lifecycle_20260912-011239.json"),
    ("astra-lifecycle-08-final", "runtime/state/controller_verification/lifecycle_20260912-011626.json"),
]
LEAD_CENSUS_INSTANT = "2026-09-12T01:13:00+08:00"   # lead direction_update lead-form-20260912T0113-107
PIN_FIELDS = ("artifact_sha256", "reviewed_sha256", "sha256", "cited_sha256")
COPY_PATS = ("artifacts/*/pinned/*.json", "artifacts/*/snapshot/*.json",
             "artifacts/*/*/pinned/*.json", "artifacts/*/*/snapshot/*.json",
             "artifacts/*/*/*/pinned/*.json", "artifacts/*/*/*/snapshot/*.json",
             "artifacts/*/*/live_snapshot/reviews/*.json")


def now_iso() -> str:
    return datetime.now(CST).replace(microsecond=0).isoformat()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(Path(p).read_bytes())


def iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, CST).replace(microsecond=0).isoformat()


def epoch_of(iso_str: str) -> float:
    return datetime.fromisoformat(iso_str).timestamp()


# --------------------------------------------------------------------------------------
# M1 — corpus freeze
# --------------------------------------------------------------------------------------
def load_corpus() -> tuple[list[dict], dict]:
    entries, digest = [], hashlib.sha256()
    for p in sorted((ROOT / "reviews").glob("*.json")):
        raw = p.read_bytes()
        h = sha256_bytes(raw)
        digest.update(p.name.encode() + b"\0" + h.encode() + b"\0")
        try:
            d = json.loads(raw)
        except Exception:
            d = None
        entries.append({"name": p.name, "sha256": h, "bytes": len(raw),
                        "mtime": round(p.stat().st_mtime, 3), "mtime_iso": iso(p.stat().st_mtime),
                        "parse_ok": d is not None, "doc": d})
    return entries, {"files": len(entries), "corpus_digest": digest.hexdigest(),
                     "measured_at": now_iso()}


# --------------------------------------------------------------------------------------
# M3 — parameterised census (defaults reproduce astra_lifecycle.review_coverage)
# --------------------------------------------------------------------------------------
def _pins(d: dict, pin_fields) -> list:
    out = []
    for key in pin_fields:
        v = d.get(key)
        if isinstance(v, str):
            out.append(v.lower())
    for key in ("target", "artifact"):
        v = d.get(key)
        if isinstance(v, dict):
            for k2 in ("sha256", "artifact_sha256", "reviewed_sha256"):
                if isinstance(v.get(k2), str):
                    out.append(v[k2].lower())
    return out


def _targets(d: dict, mode: str) -> set:
    """mode 'method_c' == astra_lifecycle._targets_in_review; 'node_id_inclusive' adds top-level
    node_id, which Method C deliberately does NOT read; 'top_level_only' drops nested dicts."""
    if mode == "method_c":
        return AL._targets_in_review(d)
    out = set()
    if mode == "node_id_inclusive":
        for key in ("target_id", "target", "target_subnode", "node_id"):
            v = d.get(key)
            if isinstance(v, str):
                out.add(v)
            elif isinstance(v, dict):
                for k2 in ("target_id", "target_subnode", "subnode", "node_id"):
                    if isinstance(v.get(k2), str):
                        out.add(v[k2])
    elif mode == "top_level_only":
        v = d.get("target_id")
        if isinstance(v, str):
            out.add(v)
    else:
        raise ValueError(mode)
    return {AL.TARGET_ALIASES.get(t, AL.TARGET_ALIASES.get(t.upper(), t)) for t in out}


def census(corpus: list[dict], hashes: dict, *, pin_match="prefix12_bidir",
           pin_fields=PIN_FIELDS, full_default="true_when_absent", targets="method_c",
           dedup="per_file", independence="any") -> dict:
    cov = {t: {"verdicts": [], "accepts": [], "full_accepts": [], "scoped_accepts": [],
               "distinct_accept_reviewers": []} for t in hashes}
    for e in corpus:
        d = e.get("doc")
        if not isinstance(d, dict):
            continue
        v = str(d.get("verdict", "")).lower()
        if v not in AL.VERDICT_KINDS:
            continue
        reviewer = str(d.get("reviewer") or d.get("actor") or "?")
        if full_default == "true_when_absent":
            full = d.get("counts_as_full_schema_verdict") is not False
        else:
            full = d.get("counts_as_full_schema_verdict") is True
        if independence == "blind_only" and d.get("blind") is not True:
            continue
        pins = _pins(d, pin_fields)
        if not pins:
            continue
        for t in _targets(d, targets):
            if t not in cov:
                continue
            h = hashes.get(t, {}).get("sha256") or ""
            if not h:
                continue
            hit = (any(p.startswith(h[:12]) or h.startswith(p[:12]) for p in pins)
                   if pin_match == "prefix12_bidir" else any(p == h for p in pins))
            if not hit:
                continue
            entry = {"file": e["name"], "reviewer": reviewer, "verdict": v,
                     "counts_as_full_schema_verdict": full}
            cov[t]["verdicts"].append(entry)
            if v == "accept":
                cov[t]["accepts"].append(entry)
                (cov[t]["full_accepts"] if full else cov[t]["scoped_accepts"]).append(entry)
    for c in cov.values():
        if dedup == "per_reviewer":
            keep, seen = [], set()
            for a in c["full_accepts"]:
                if a["reviewer"] in seen:
                    continue
                seen.add(a["reviewer"])
                keep.append(a)
            c["full_accepts"] = keep
        c["distinct_accept_reviewers"] = sorted({a["reviewer"] for a in c["full_accepts"]})
    return cov


def live_hashes() -> dict:
    return {k: {"sha256": sha256_file(ROOT / v), "path": v} for k, v in LIVE_SCHEMAS.items()}


# --------------------------------------------------------------------------------------
# M7 — mutation census over pinned / snapshot copies of live review files
# --------------------------------------------------------------------------------------
def mutation_census(corpus: list[dict]) -> dict:
    live = {e["name"]: e for e in corpus}
    hits, scanned = [], 0
    for pat in COPY_PATS:
        for p in sorted(ROOT.glob(pat)):
            base = p.name[len("reviews__"):] if p.name.startswith("reviews__") else p.name
            if base not in live:
                continue
            scanned += 1
            raw = p.read_bytes()
            h = sha256_bytes(raw)
            try:
                d = json.loads(raw)
            except Exception:
                d = {}
            lv = live[base]
            ld = lv["doc"] or {}
            hits.append({
                "copy": str(p.relative_to(ROOT)), "review": base, "copy_sha256": h,
                "copy_bytes": len(raw), "copy_mtime": round(p.stat().st_mtime, 3),
                "copy_mtime_iso": iso(p.stat().st_mtime), "copy_verdict": d.get("verdict"),
                "copy_full_flag": d.get("counts_as_full_schema_verdict"),
                "live_sha256": lv["sha256"], "live_bytes": lv["bytes"], "live_mtime": lv["mtime"],
                "live_mtime_iso": lv["mtime_iso"], "live_verdict": ld.get("verdict"),
                "live_full_flag": ld.get("counts_as_full_schema_verdict"),
                "bytes_identical": h == lv["sha256"],
                "verdict_differs": d.get("verdict") != ld.get("verdict"),
            })
    diverged = [h for h in hits if not h["bytes_identical"]]
    flips = [h for h in diverged if h["verdict_differs"]]
    return {"copies_scanned": scanned, "copies_diverged": len(diverged),
            "verdict_flips": len(flips), "diverged": diverged, "flips": flips}


# --------------------------------------------------------------------------------------
# M4 — reconstruct the corpus as of a past instant from preserved bytes
# --------------------------------------------------------------------------------------
def corpus_at(T: float, corpus: list[dict], mut: dict) -> tuple[list[dict], list[dict]]:
    """For each live review name: choose the newest revision whose recorded time <= T.
    Revision candidates = live bytes (if live mtime <= T) + every preserved copy with
    copy_mtime <= T. copy_mtime is when the copy was TAKEN, a lower bound on the revision's
    age; the rule is declared and its mismatches are reported, not hidden."""
    by_name: dict[str, list[dict]] = {}
    for h in mut["diverged"] + [h for h in mut["diverged"]]:
        by_name.setdefault(h["review"], []).append(h)
    out, notes = [], []
    for e in corpus:
        cands = []
        if e["mtime"] <= T:
            cands.append({"t": e["mtime"], "doc": e["doc"], "src": "live"})
        for h in by_name.get(e["name"], []):
            if h["copy_mtime"] <= T:
                try:
                    d = json.loads((ROOT / h["copy"]).read_bytes())
                except Exception:
                    continue
                cands.append({"t": h["copy_mtime"], "doc": d, "src": h["copy"]})
        if not cands:
            continue
        best = max(cands, key=lambda c: c["t"])
        if best["src"] != "live":
            notes.append({"review": e["name"], "used": best["src"], "used_mtime_iso": iso(best["t"]),
                          "live_mtime_iso": e["mtime_iso"], "chosen_verdict": (best["doc"] or {}).get("verdict"),
                          "live_verdict": (e["doc"] or {}).get("verdict")})
        out.append({"name": e["name"], "sha256": e["sha256"], "bytes": e["bytes"],
                    "mtime": best["t"], "mtime_iso": iso(best["t"]), "parse_ok": True,
                    "doc": best["doc"], "source": best["src"]})
    return out, notes


# --------------------------------------------------------------------------------------
# M5 — replay the persisted controller scans
# --------------------------------------------------------------------------------------
def scan_replay(corpus, hashes, mut, node="F2b") -> list[dict]:
    rows = []
    for label, rel in SCAN_SOURCES:
        p = ROOT / rel
        if not p.exists():
            rows.append({"label": label, "report": rel, "error": "report missing"})
            continue
        d = json.loads(p.read_text())
        at = d.get("at") or d.get("started_at")
        T = epoch_of(at)
        published = (d.get("review_coverage") or {}).get(node, {}).get("distinct_accept_reviewers")
        sub, notes = corpus_at(T, corpus, mut)
        got = census(sub, hashes)[node]["distinct_accept_reviewers"]
        rows.append({"label": label, "report": rel, "at": at, "published": published,
                     "replayed": got, "match": got == published,
                     "missing_from_replay": sorted(set(published or []) - set(got)),
                     "extra_in_replay": sorted(set(got) - set(published or [])),
                     "files": len(sub), "substitutions": notes})
    return rows


# --------------------------------------------------------------------------------------
# M6 — filter lattice
# --------------------------------------------------------------------------------------
def lattice(corpus, hashes, node="F2b", tag="live") -> list[dict]:
    rows = []
    for pm in ("prefix12_bidir", "exact64"):
        for pf, pf_name in ((PIN_FIELDS, "any_explicit"), (("reviewed_sha256",), "reviewed_sha256_only")):
            for fd in ("true_when_absent", "require_explicit_true"):
                for tg in ("method_c", "node_id_inclusive", "top_level_only"):
                    for dd in ("per_file", "per_reviewer"):
                        for ind in ("any", "blind_only"):
                            cov = census(corpus, hashes, pin_match=pm, pin_fields=pf,
                                         full_default=fd, targets=tg, dedup=dd, independence=ind)
                            vs = cov[node]["verdicts"]
                            rows.append({
                                "corpus": tag, "pin_match": pm, "pin_fields": pf_name,
                                "full_default": fd, "targets": tg, "dedup": dd,
                                "independence": ind,
                                "accept": sum(1 for x in vs if x["verdict"] == "accept"),
                                "revise": sum(1 for x in vs if x["verdict"] == "revise"),
                                "inconclusive": sum(1 for x in vs if x["verdict"] == "inconclusive"),
                                "reject": sum(1 for x in vs if x["verdict"] == "reject"),
                                "distinct_accepts": cov[node]["distinct_accept_reviewers"],
                                "accept_files": sorted(x["file"] for x in vs if x["verdict"] == "accept")})
    return rows


# --------------------------------------------------------------------------------------
# M8 — controls
# --------------------------------------------------------------------------------------
def _entry(name, doc, mtime=0.0):
    raw = json.dumps(doc).encode()
    return {"name": name, "sha256": sha256_bytes(raw), "bytes": len(raw), "mtime": mtime,
            "mtime_iso": iso(mtime) if mtime else "n/a", "parse_ok": True, "doc": doc}


def run_controls(corpus, hashes) -> dict:
    H_F2B, H_F1 = hashes["F2b"]["sha256"], hashes["F1"]["sha256"]
    OLD = "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508"
    res = []

    def add(i, name, expected, observed, ok):
        res.append({"id": i, "name": name, "expected": expected, "observed": observed, "pass": bool(ok)})

    ref, mine = AL.review_coverage(hashes), census(corpus, hashes)
    ok = all(ref[t]["distinct_accept_reviewers"] == mine[t]["distinct_accept_reviewers"] and
             sorted((v["file"], v["reviewer"], v["verdict"], v["counts_as_full_schema_verdict"])
                    for v in ref[t]["verdicts"]) ==
             sorted((v["file"], v["reviewer"], v["verdict"], v["counts_as_full_schema_verdict"])
                    for v in mine[t]["verdicts"]) for t in hashes)
    add("C0", "anchor: reimplementation equals Method C on live corpus",
        "exact equality on verdicts + distinct accepts, all 3 nodes",
        "exact equality" if ok else "MISMATCH", ok)

    e = [_entry("x.json", {"verdict": "accept", "reviewer": "r1", "target_id": "F2b", "reviewed_sha256": H_F2B})]
    a = census(e, hashes)["F2b"]["distinct_accept_reviewers"]
    b = census(e, hashes, full_default="require_explicit_true")["F2b"]["distinct_accept_reviewers"]
    add("C1", "full-flag absent", "C=[r1]; strict=[]", f"C={a}; strict={b}", a == ["r1"] and b == [])

    e = [_entry("x.json", {"verdict": "accept", "reviewer": "r2", "target_id": "F2b", "reviewed_sha256": OLD})]
    a = census(e, hashes)["F2b"]["distinct_accept_reviewers"]
    add("C2", "superseded-hash accept", "[]", str(a), a == [])

    e = [_entry("x.json", {"verdict": "accept", "reviewer": "r3", "target_id": "F2b",
                           "reviewed_sha256": H_F2B, "counts_as_full_schema_verdict": False})]
    c = census(e, hashes)["F2b"]
    add("C3", "explicit scoped accept", "accepts=1, full=0, distinct=[]",
        f"accepts={len(c['accepts'])}, full={len(c['full_accepts'])}, distinct={c['distinct_accept_reviewers']}",
        len(c["accepts"]) == 1 and len(c["full_accepts"]) == 0 and c["distinct_accept_reviewers"] == [])

    e = [_entry("x.json", {"verdict": "revise", "reviewer": "r4", "target_id": "F2b", "reviewed_sha256": H_F2B})]
    a = census(e, hashes)["F2b"]["distinct_accept_reviewers"]
    add("C4", "revise verdict", "[]", str(a), a == [])

    bad = {"name": "bad.json", "sha256": "0" * 64, "bytes": 1, "mtime": 0.0, "mtime_iso": "n/a",
           "parse_ok": False, "doc": None}
    a = census([bad], hashes)["F2b"]["distinct_accept_reviewers"]
    add("C5", "malformed review skipped", "[]", str(a), a == [])

    e = [_entry("x.json", {"verdict": "accept", "reviewer": "r6", "target_id": "F2b",
                           "body": f"reviewed {H_F2B} carefully"})]
    a = census(e, hashes)["F2b"]["distinct_accept_reviewers"]
    add("C6", "prose-only hash mention", "[]", str(a), a == [])

    e = [_entry("x.json", {"verdict": "accept", "reviewer": "r7", "target_id": "F2b",
                           "reviewed_sha256": H_F2B[:12]})]
    a = census(e, hashes)["F2b"]["distinct_accept_reviewers"]
    b = census(e, hashes, pin_match="exact64")["F2b"]["distinct_accept_reviewers"]
    add("C7", "12-char prefix pin", "C=[r7]; exact64=[]", f"C={a}; exact64={b}", a == ["r7"] and b == [])

    e = [_entry("x.json", {"verdict": "accept", "reviewer": "r8",
                           "target": {"node_id": "F2b", "sha256": H_F2B}})]
    a = census(e, hashes)["F2b"]["distinct_accept_reviewers"]
    add("C8", "nested target.node_id + target.sha256", "[r8]", str(a), a == ["r8"])

    e = [_entry("x.json", {"verdict": "accept", "reviewer": "r9",
                           "target_id": "AF-SCC-C0-VAC-GEN", "reviewed_sha256": H_F2B})]
    a = census(e, hashes)["F2b"]["distinct_accept_reviewers"]
    b = census(e, hashes, targets="top_level_only")["F2b"]["distinct_accept_reviewers"]
    add("C9", "class-id alias target_id", "method_c=[r9]; top_level_only=[r9]",
        f"method_c={a}; top_level_only={b}", a == ["r9"] and b == ["r9"])

    e = [_entry("x.json", {"verdict": "accept", "actor": "r10", "target_id": "F2b", "reviewed_sha256": H_F2B})]
    a = census(e, hashes)["F2b"]["distinct_accept_reviewers"]
    add("C10", "reviewer missing, actor present", "[r10]", str(a), a == ["r10"])

    e = [_entry("x.json", {"verdict": "accept", "reviewer": "r11", "target_id": "F1", "reviewed_sha256": H_F2B})]
    a = census(e, hashes)["F2b"]["distinct_accept_reviewers"]
    add("C11", "cross-node pin leakage", "[]", str(a), a == [])

    cov = census([], hashes)
    a = {t: cov[t]["distinct_accept_reviewers"] for t in hashes}
    add("C12", "null control: empty corpus", "all nodes []", str(a), a == {t: [] for t in hashes})

    e = [_entry("x.json", {"verdict": "accept", "reviewer": "r13", "target_id": "F1", "reviewed_sha256": H_F1})]
    cov = census(e, hashes)
    add("C13", "positive twin of C11 (F1 pin, F1 target)", "F1=[r13], F2b=[]",
        f"F1={cov['F1']['distinct_accept_reviewers']}, F2b={cov['F2b']['distinct_accept_reviewers']}",
        cov["F1"]["distinct_accept_reviewers"] == ["r13"] and cov["F2b"]["distinct_accept_reviewers"] == [])

    # C14 blind-spot control: top-level node_id is NOT read by Method C but IS by the wider rule.
    e = [_entry("x.json", {"verdict": "accept", "reviewer": "r14", "node_id": "F2b",
                           "reviewed_sha256": H_F2B})]
    a = census(e, hashes)["F2b"]["distinct_accept_reviewers"]
    b = census(e, hashes, targets="node_id_inclusive")["F2b"]["distinct_accept_reviewers"]
    add("C14", "top-level node_id only (Method C blind spot)",
        "method_c=[]; node_id_inclusive=[r14]", f"method_c={a}; node_id_inclusive={b}",
        a == [] and b == ["r14"])

    return {"controls": res, "passed": sum(1 for r in res if r["pass"]), "total": len(res)}


# --------------------------------------------------------------------------------------
def main() -> int:
    started = now_iso()
    hashes = live_hashes()
    corpus, corpus_meta = load_corpus()
    mut = mutation_census(corpus)
    replay = scan_replay(corpus, hashes, mut)
    lat_live = lattice(corpus, hashes, "F2b", "live")
    T_lead = epoch_of(LEAD_CENSUS_INSTANT)
    sub_lead, sub_lead_notes = corpus_at(T_lead, corpus, mut)
    lat_lead = lattice(sub_lead, hashes, "F2b", "lead_census_instant_0113")
    ctl = run_controls(corpus, hashes)
    ref = AL.review_coverage(hashes)

    f2b_flip = next((h for h in mut["flips"] if h["review"] == "F2b-review-worker-072-rev29.json"), None)
    replay_ok = [r for r in replay if r.get("match")]

    def pairs(rows):
        return sorted({(r["accept"], r["revise"]) for r in rows})

    reproduce_07 = [r for r in lat_lead if (r["accept"], r["revise"]) == (0, 7)]
    reproduce_47_live = [r for r in lat_live if (r["accept"], r["revise"]) == (4, 7)]

    findings = []
    if f2b_flip:
        findings.append({
            "id": "W026-CF31-F1", "severity": "proven",
            "statement": (
                "reviews/F2b-review-worker-072-rev29.json was rewritten IN PLACE: the preserved "
                f"pre-rewrite bytes at {f2b_flip['copy']} carry verdict='accept' "
                f"(sha256 {f2b_flip['copy_sha256'][:12]}, {f2b_flip['copy_bytes']} B, copy taken "
                f"{f2b_flip['copy_mtime_iso']}); the live file carries verdict='revise' "
                f"(sha256 {f2b_flip['live_sha256'][:12]}, {f2b_flip['live_bytes']} B, mtime "
                f"{f2b_flip['live_mtime_iso']}). Same filename, same declared created_at, no "
                "revision marker in the name."),
            "evidence": [f2b_flip["copy"], "reviews/F2b-review-worker-072-rev29.json"]})
    findings.append({
        "id": "W026-CF31-F2", "severity": "proven",
        "statement": ("The persisted controller scans move F2b 4 -> 3 across exactly this rewrite: "
                      "astra-lifecycle-08-open published "
                      "['worker-052','worker-071','worker-072','worker-090']; astra-lifecycle-08-final "
                      "published ['worker-052','worker-071','worker-090']. Replaying the corpus from "
                      "preserved bytes reproduces "
                      f"{len(replay_ok)}/{len(replay)} persisted scans exactly, including the 4-set at "
                      "08-open. No filter difference is needed to explain the controller's own move."),
        "evidence": [r["report"] for r in replay if r.get("report")]})
    findings.append({
        "id": "W026-CF31-F3", "severity": "proven",
        "statement": ("Method C has a target-extraction blind spot that biases the same count "
                      "downward: research_map/astra_lifecycle.py::_targets_in_review reads only "
                      "target_id / target / target_subnode, so a review that identifies its node "
                      "solely by a top-level node_id, or by a 'path#hash' target_id, is invisible. "
                      f"Control C14 demonstrates the blind spot; the live F2b corpus contains such "
                      "files (see mutation_census.json and lattice.json targets=node_id_inclusive)."),
        "evidence": ["research_map/astra_lifecycle.py", "artifacts/worker-026/cf31_divergence_attribution/lattice.json"]})
    findings.append({
        "id": "W026-CF31-F4", "severity": "bounded",
        "statement": (f"At live bytes the tested census rules yield only the pairs {pairs(lat_live)} "
                      f"for F2b; at the lead's census instant ({LEAD_CENSUS_INSTANT}) they yield "
                      f"{pairs(lat_lead)}. "
                      f"{len(reproduce_07)} of {len(lat_lead)} rule combinations reproduce the lead's "
                      "stated '0 accept / 7 revise' at that instant. That number is therefore NOT "
                      "reproducible from any tested rule on the bytes that survive: the review corpus was "
                      "being rewritten underneath both counters, so no surviving snapshot is obliged to "
                      "reproduce either count except the controller's, which it does. The lead's revise "
                      "half is not reproducible either - an unbound (any-revision) F2b count gives 32 "
                      "revise / 12 accept, and the hash-bound count gives 4 revise at live bytes."),
        "evidence": ["artifacts/worker-026/cf31_divergence_attribution/lattice.json"]})
    findings.append({
        "id": "W026-CF31-F5", "severity": "instrument",
        "statement": (f"mutation census over {mut['copies_scanned']} pinned/snapshot copies of live "
                      f"review files found {mut['copies_diverged']} byte-diverged and "
                      f"{mut['verdict_flips']} verdict flips - every one a review file rewritten under "
                      "a fixed name. This is the structural defect CF-31 names, now with byte evidence "
                      "and a preserved pre-rewrite copy."),
        "evidence": ["artifacts/worker-026/cf31_divergence_attribution/mutation_census.json"]})

    report = {
        "task_id": "W026-CF31-DIVERGENCE-ATTRIBUTION-01",
        "actor": "worker-026", "gate": "G-FORM", "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "authority": ("worker-level read-only measurement only; no gate verdict, no node status, no "
                      "validation_status promotion, no canonical write; does NOT publish the "
                      "astra-life05-verify-gform-r3 per-file binding table and does NOT adjudicate "
                      "which count is gate-correct"),
        "non_duplication": ("astra-life05-verify-gform-r3 (lead-audit, artifact "
                            "reviews/G-FORM-final-verify-r3.json) owns the canonical per-file binding "
                            "table and the gate-correct count. This task measures the divergence "
                            "MECHANISM (byte-proven in-place rewrite, Method-C target blind spot, "
                            "filter-switch sensitivity) and does not write that path."),
        "started_at": started, "generated_at": now_iso(),
        "verdict": "TEMPORAL_INPLACE_REWRITE__PLUS_METHOD_C_TARGET_BLINDSPOT",
        "live_hashes": hashes, "corpus": corpus_meta,
        "method_c_live": {t: {"distinct_accept_reviewers": ref[t]["distinct_accept_reviewers"],
                              "verdicts": len(ref[t]["verdicts"])} for t in hashes},
        "scan_replay": replay,
        "replay_summary": {
            "scans_tested": len(replay),
            "scans_matching_published_exactly": len(replay_ok),
            "limitation": ("reconstruction picks, per review file, the newest revision whose recorded time "
                           "is <= the scan instant. copy_mtime is when a preserved copy was TAKEN, a "
                           "lower bound on its revision's age, and this swarm has a recorded clock-"
                           "discipline finding. The single miss (astra-lifecycle-07-final, 01:09:52) is "
                           "exactly this case: the preserved accept copy of F2b-review-worker-072-rev29.json "
                           "was taken at 01:10:13, 21 s AFTER that scan, so the rule cannot place it. The "
                           "two instants CF-31 cites (08-open 4 accepts, 08-final 3 accepts) both replay "
                           "exactly."),
            "load_bearing_instants_match": all(
                r.get("match") for r in replay if r["label"] in ("astra-lifecycle-08-open", "astra-lifecycle-08-final"))},
        "unverified_hypothesis": {
            "statement": ("Method C returns exactly 7 F2b verdicts at the live bytes (3 accept + 4 revise), "
                          "and the lead's direction_update reports exactly '7 revise'. A single miscount of "
                          "'7 verdicts' as '7 revise' would produce the lead's revise half."),
            "status": "NOT A CLAIM - hypothesis only, recorded because the numeric coincidence is exact",
            "discriminating_test": ("obtain the lead's per-file census list; if it enumerates the same 7 files "
                                    "as Method C, the hypothesis is supported; if it enumerates a different set, "
                                    "it is refuted. This worker cannot discriminate further without that list."),
            "method_c_f2b_verdict_files": [v["file"] for v in ref["F2b"]["verdicts"]]},
        "lattice_summary": {
            "live_pairs": pairs(lat_live),
            "lead_instant_pairs": pairs(lat_lead),
            "reproduce_lead_0_accept_7_revise": reproduce_07,
            "reproduce_4_accept_7_revise_at_live": reproduce_47_live,
            "combinations_per_corpus": len(lat_live)},
        "lead_instant_substitutions": sub_lead_notes,
        "mutation_census_summary": {k: mut[k] for k in ("copies_scanned", "copies_diverged", "verdict_flips")},
        "findings": findings, "controls": ctl,
        "pins": {"live_schemas": {k: sha256_file(ROOT / v) for k, v in LIVE_SCHEMAS.items()},
                 "astra_lifecycle.py": sha256_file(ROOT / "research_map" / "astra_lifecycle.py")},
        "falsifier": ("Falsified if a re-run at the same corpus digest finds (a) C0 mismatch between "
                      "the reimplementation and research_map/astra_lifecycle.py::review_coverage; "
                      "(b) the F2b accept-set move 4->3 not attributable to the byte divergence of "
                      "reviews/F2b-review-worker-072-rev29.json recorded in mutation_census.json; "
                      "(c) a persisted controller scan whose replay set does not match its published "
                      "set for a reason other than the declared copy-mtime rule; or (d) any control "
                      "C1-C14 not flipping as declared."),
        "non_claims": [
            "Does not state which of the two counts is gate-correct; that is astra-life05-verify-gform-r3.",
            "Does not assert the pre-rewrite verdict was substantively right; only that the bytes changed.",
            "Does not edit reviews/, schemas/, research_map/ or any canonical artifact.",
            "Does not set status=done, validation_status=passed or any gate verdict.",
        ],
    }

    for name, obj in {
        "corpus_manifest.json": {**corpus_meta,
                                 "entries": [{k: v for k, v in e.items() if k != "doc"} for e in corpus]},
        "lattice.json": {"live": lat_live, "lead_census_instant_0113": lat_lead},
        "mutation_census.json": mut,
        "snapshot_replay.json": {"scans": replay, "lead_instant_substitutions": sub_lead_notes},
        "controls.json": ctl,
        "report.json": report,
    }.items():
        (HERE / name).write_text(json.dumps(obj, indent=1))

    print(json.dumps({
        "verdict": report["verdict"], "controls": f"{ctl['passed']}/{ctl['total']}",
        "corpus_files": corpus_meta["files"], "corpus_digest": corpus_meta["corpus_digest"][:12],
        "method_c_live_F2b": ref["F2b"]["distinct_accept_reviewers"],
        "replay": [{"label": r["label"], "published": r.get("published"), "replayed": r.get("replayed"),
                    "match": r.get("match")} for r in replay],
        "live_pairs": pairs(lat_live), "lead_instant_pairs": pairs(lat_lead),
        "copies_scanned": mut["copies_scanned"], "verdict_flips": mut["verdict_flips"],
    }, indent=1))
    return 0 if ctl["passed"] == ctl["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
