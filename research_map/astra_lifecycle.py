"""One Astra control lifecycle (independent pass, then exit).

Order of operations, all under runtime/state/map.lock:
  1. ingest outbox traffic            (comms.py)
  2. apply validated events to map    (apply_events.py)
  3. controller repair: measured hashes, publication status, gate audit,
     controller findings              (this file)
  4. validate map + evidence audit    (validate_map.py, audit_evidence.py)
  5. checkpoint snapshot              (checkpoint.py; writes artifact_hashes.json)
  6. lifecycle report                 (runtime/state/controller_verification/)

It never claims a theorem, never sets a gate verdict (gate events from `astra`
carry verdicts through the normal event path), and never copies authoring-tree
files into canonical paths: publication is the author's bounded assignment, and
the controller only measures and records divergence.

  python3 research_map/astra_lifecycle.py --label astra-lifecycle-01
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research_map"))
import apply_events  # noqa: E402
import audit_evidence  # noqa: E402
import checkpoint  # noqa: E402
import comms  # noqa: E402
from validate_map import validate_map  # noqa: E402

LOCK = ROOT / "runtime" / "state" / "map.lock"
MAP = ROOT / "research_map" / "research_map.json"
CST = timezone(timedelta(hours=8))

# Canonical path <- authoring path. The canonical path is authoritative
# (assignments + audit_evidence.py); the authoring tree must be published
# byte-identically. Keep in sync with audit_evidence.MIRRORS.
# mode="mirror": two trees of one artifact, byte-identity required.
# mode="companion": two DISTINCT artifacts (declared taxonomy vs its class-contract
# supplement, astra-life04 adjudication REC-3); byte-identity is not required, but
# each path must be pinned and consistency-checked.
MIRRORS = [
    ("research_map/formulation_taxonomy.yaml", "artifacts/formulation/formulation_taxonomy.yaml", "companion"),
    ("schemas/af_wcc_vacuum.yaml", "artifacts/formulation/schemas/af_wcc_vacuum.yaml", "mirror"),
    ("schemas/af_scc_c2_vacuum.yaml", "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml", "mirror"),
    ("schemas/af_scc_c0_vacuum.yaml", "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml", "mirror"),
]


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def digest(art: str) -> dict:
    p = ROOT / art
    if p.is_file():
        return {"kind": "file", "sha256": sha256(p), "bytes": p.stat().st_size}
    if p.is_dir():
        h = hashlib.sha256()
        files = sorted(x for x in p.rglob("*") if x.is_file() and not x.name.startswith("._"))
        for x in files:
            h.update(f"{x.relative_to(p)}\0{sha256(x)}\n".encode())
        return {"kind": "directory", "sha256": h.hexdigest(), "files": len(files),
                "bytes": sum(x.stat().st_size for x in files)}
    return {"kind": "absent", "sha256": None}


def measured_hashes(m: dict) -> dict:
    """Record controller-measured hashes; flag declared-vs-measured drift."""
    out = {}
    for g in m.get("groups", []):
        for n in g.get("nodes", []):
            art = n.get("artifact")
            if not art:
                continue
            d = digest(art)
            out[n["id"]] = {"artifact": art, **d}
            n["artifact_exists"] = d["kind"] != "absent"
            if d["kind"] == "absent":
                continue
            n["artifact_sha256_measured"] = d["sha256"]
            n["artifact_bytes_measured"] = d["bytes"]
            n["artifact_measured_at"] = now()
            declared = n.get("artifact_sha256")
            if declared:
                n["declared_hash_matches_measured"] = (declared == d["sha256"])
    return out


def publication_status() -> dict:
    pairs = []
    for canonical, authoring, mode in MIRRORS:
        cp, ap = ROOT / canonical, ROOT / authoring
        rec = {"canonical": canonical, "authoring": authoring, "classification": mode,
               "canonical_sha256": None, "authoring_sha256": None, "status": "missing"}
        if cp.is_file() and ap.is_file():
            ch, ah = sha256(cp), sha256(ap)
            if mode == "mirror":
                status = "aligned" if ch == ah else "divergent"
            else:
                status = "companion-pinned"
            rec.update(canonical_sha256=ch, authoring_sha256=ah, status=status)
        if mode == "companion":
            rec["note"] = ("distinct artifacts per FROZEN.logical_artifacts: canonical is the "
                           "declared F0 taxonomy, authoring is the class-contract supplement "
                           "(F0-R). Byte-identity is not a publication requirement for this pair "
                           "(astra-life04 adjudication REC-3); each path must be hash-pinned and "
                           "consistency-checked.")
        pairs.append(rec)
    return {"checked_at": now(),
            "policy": ("mirror pairs (same artifact in two trees) must be published byte-identically "
                       "to the canonical path; companion pairs are distinct artifacts that must each "
                       "be hash-pinned (FROZEN.logical_artifacts) and consistency-checked, not "
                       "byte-identical. Review verdicts bind to the canonical hash."),
            "pairs": pairs,
            "divergent": sum(1 for p in pairs if p["status"] == "divergent"),
            "companion_pairs": sum(1 for p in pairs if p["classification"] == "companion")}


VERDICT_KINDS = ("accept", "revise", "reject", "inconclusive")
TARGET_ALIASES = {
    "F0": "F0", "F1": "F1", "F2A": "F2a", "F2B": "F2b", "F2": "F2b",
    "L0": "L0", "L1": "L1",
    "AF-WCC-VAC-GEN": "F1",
    "AF-SCC-C2-VAC-GEN": "F2a",
    "AF-SCC-C0-VAC-GEN": "F2b",
}


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
    norm = set()
    for t in out:
        norm.add(TARGET_ALIASES.get(t, TARGET_ALIASES.get(t.upper(), t)))
    return norm


def _explicit_pins(d: dict) -> list:
    """Hashes a review explicitly pins (not hashes merely mentioned in prose)."""
    pins = []
    for key in ("artifact_sha256", "reviewed_sha256", "sha256", "cited_sha256"):
        v = d.get(key)
        if isinstance(v, str):
            pins.append(v.lower())
    for key in ("target", "artifact"):
        v = d.get(key)
        if isinstance(v, dict):
            for k2 in ("sha256", "artifact_sha256", "reviewed_sha256"):
                if isinstance(v.get(k2), str):
                    pins.append(v[k2].lower())
    return pins


def review_coverage(hashes: dict) -> dict:
    """Advisory controller scan: verdicts in reviews/*.json that cite a measured hash.

    Binding coverage is adjudicated by the audit lead (reviews/A1-rebind-coverage.json);
    this scan exists so gate reasons cannot go stale against the review corpus.
    """
    cov = {t: {"verdicts": [], "accepts": [], "full_accepts": [], "scoped_accepts": [],
               "distinct_accept_reviewers": []}
           for t in hashes}
    for rp in sorted((ROOT / "reviews").glob("*.json")):
        try:
            text = rp.read_text()
            d = json.loads(text)
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
            if h and any(p.startswith(h[:12]) or h.startswith(p[:12]) for p in pins):
                entry = {"file": rp.name, "reviewer": reviewer, "verdict": v,
                         "counts_as_full_schema_verdict": full}
                cov[t]["verdicts"].append(entry)
                if v == "accept":
                    cov[t]["accepts"].append(entry)
                    (cov[t]["full_accepts"] if full else cov[t]["scoped_accepts"]).append(entry)
    for c in cov.values():
        c["distinct_accept_reviewers"] = sorted({a["reviewer"] for a in c["full_accepts"]})
        c["two_distinct_accepts"] = len(c["distinct_accept_reviewers"]) >= 2
        c["note"] = ("advisory controller scan; scoped verdicts "
                     "(counts_as_full_schema_verdict=false) are excluded; binding coverage "
                     "is adjudicated by the audit lead")
    return cov


def l1_spotchecks(prefix: str) -> list:
    hits = []
    patterns = ("reviews/L1-spotcheck-*.json", "artifacts/*/l1_spotcheck/spotcheck-l1-*.json")
    for pat in patterns:
        for p in sorted(ROOT.glob(pat)):
            try:
                if prefix and prefix in p.read_text():
                    hits.append(str(p.relative_to(ROOT)))
            except Exception:
                continue
    return hits


def clock_discipline() -> dict:
    events = comms.load_events()
    now_dt = datetime.now(CST)
    future = []
    for ev in events:
        try:
            t = datetime.fromisoformat(str(ev.get("created_at")))
        except Exception:
            continue
        if t.tzinfo is None:
            t = t.replace(tzinfo=CST)
        if t > now_dt:
            future.append({"event_id": ev.get("event_id"), "actor": ev.get("actor"),
                           "created_at": ev.get("created_at"),
                           "skew_seconds": int((t - now_dt).total_seconds())})
    return {"checked_at": now(), "events_total": len(events), "future_dated": len(future),
            "max_skew_seconds": max((f["skew_seconds"] for f in future), default=0),
            "max_future_created_at": max((f["created_at"] for f in future), default=None),
            "examples": sorted(future, key=lambda x: -x["skew_seconds"])[:3]}


def lock_guard(hashes: dict) -> dict:
    solver = ROOT / "numerics" / "spherical_solver"
    guard = ROOT / "numerics" / "tests" / "selfgravity_lock_guard.py"
    return {"solver_absent": not solver.exists(),
            "guard_present": guard.is_file(),
            "n1_hash": (hashes.get("N1", {}).get("sha256") or "absent")}


def gate_audit(m: dict, hashes: dict, pub: dict, soft: list, cov: dict,
               clock: dict, guard: dict) -> dict:
    gates = {g["gate_id"]: g for g in m.get("gates", [])}
    div = {p["canonical"]: p for p in pub["pairs"]}
    ledger_flags = [s for s in soft if "ledger/" in s]
    f0_flags = [s for s in soft if "F0 artifact" in s]
    f1_flags = [s for s in soft if "F1 artifact" in s]
    f2b_flags = [s for s in soft if "F2b artifact" in s]
    l1_prefix = (hashes.get("L1", {}).get("sha256") or "")[:12]
    spots = l1_spotchecks(l1_prefix)
    proto = ROOT / "numerics" / "CONVERGENCE_PROTOCOL.md"
    proto_h = sha256(proto)[:12] if proto.is_file() else "absent"
    proto_review = ROOT / "reviews" / "G-NUM-protocol-review.json"
    proto_verdict, proto_rev_h, proto_score = "absent", "absent", None
    if proto_review.is_file():
        try:
            prd = json.loads(proto_review.read_text())
            proto_verdict = str(prd.get("verdict") or "unknown")
            proto_score = prd.get("score")
            bound = prd.get("reviewed_sha256") or prd.get("artifact_sha256")
            proto_rev_h = str(bound)[:12] if bound else "unbound"
        except Exception:
            proto_verdict, proto_rev_h = "unreadable", "unreadable"
    c8_met = (proto_verdict == "accept" and proto_rev_h == proto_h)
    # N0 node-level verdict: newest reviews/*.json targeting N0 (protocol review excluded).
    n0_verdicts = []
    for rp in sorted((ROOT / "reviews").glob("*.json")):
        try:
            rd = json.loads(rp.read_text())
        except Exception:
            continue
        if str(rd.get("target_id")) != "N0" or "protocol" in rp.name.lower():
            continue
        n0_verdicts.append((str(rd.get("created_at") or ""), rp.name,
                            str(rd.get("verdict") or "?"), rd.get("score")))
    n0_verdicts.sort()
    n0_latest = n0_verdicts[-1] if n0_verdicts else None

    def h(nid: str) -> str:
        return (hashes.get(nid, {}).get("sha256") or "absent")[:12]

    def acc(t: str) -> list:
        return cov.get(t, {}).get("distinct_accept_reviewers", [])

    def accs(t: str) -> str:
        a = acc(t)
        return f"{len(a)} distinct accept reviewer(s)" + (f" {a}" if a else "")

    def verd(t: str) -> str:
        v = cov.get(t, {}).get("verdicts", [])
        return ", ".join(f"{x['reviewer']}:{x['verdict']}" for x in v) or "none"

    f0_pair = div.get("research_map/formulation_taxonomy.yaml", {})
    if f0_pair.get("classification") == "companion":
        f0_pub = ("the canonical declared-F0 taxonomy and the authoring class-contract supplement are "
                  "distinct pinned artifacts (REC-3; byte-identity is not required for this pair)")
    else:
        f0_pub = f"publication pair F0 is {f0_pair.get('status', 'unknown')}"

    audit = {
        "G-F0": {
            "verdict": gates.get("G-F0", {}).get("verdict", "pending"),
            "checked_at": now(),
            "reason": (f"canonical taxonomy {h('F0')}; review scan at this hash: {accs('F0')} "
                       f"[{verd('F0')}]; criterion needs two distinct independent accepts; "
                       f"{f0_pub}."
                       + (f" {len(f0_flags)} class-separation soft flag(s) on F0 await disposition "
                          "(checker cannot see candidate annotations)." if f0_flags else "")),
        },
        "G-FORM": {
            "verdict": gates.get("G-FORM", {}).get("verdict", "pending"),
            "checked_at": now(),
            "reason": ("F1/F2a/F2b measured canonical hashes "
                       f"{h('F1')}, {h('F2a')}, {h('F2b')}; publication: "
                       + ", ".join(f"{p['canonical'].split('/')[-1]}={p['status']}" for p in pub["pairs"]
                                   if "schemas/" in p["canonical"])
                       + f". Review scan at these hashes: F1 [{accs('F1')}], F2a [{accs('F2a')}], "
                         f"F2b [{accs('F2b')}]; verdicts bound to superseded hashes are advisory only."
                       + (f" {len(f1_flags)} class-separation soft flag(s) on F1 await disposition."
                          if f1_flags else "")
                       + (f" {len(f2b_flags)} class-separation soft flag(s) on F2b await disposition."
                          if f2b_flags else "")),
        },
        "G-LIT": {
            "verdict": gates.get("G-LIT", {}).get("verdict", "pending"),
            "checked_at": now(),
            "reason": (f"L0 measured {h('L0')}; review scan at this hash: {accs('L0')} [{verd('L0')}]. "
                       f"L1 measured {h('L1')}; {len(spots)} independent re-fetch spot check(s) bind "
                       f"to this hash ({', '.join(spots) if spots else 'none'}), required >=3."
                       + (f" Evidence audit flags {len(ledger_flags)} ledger token issue(s)."
                          if ledger_flags else " The ledger class-token flag is cleared at this hash.")),
        },
        "G-NUM": {
            "verdict": gates.get("G-NUM", {}).get("verdict", "pending"),
            "checked_at": now(),
            "reason": ("self-gravitating numerics remain locked "
                       f"(solver_absent={guard['solver_absent']}, guard_present={guard['guard_present']}); "
                       f"protocol measured {proto_h}; "
                       + (f"criterion C8 is MET (review verdict accept score {proto_score} binds "
                          f"{proto_rev_h}). " if c8_met else
                          f"criterion C8 is unmet: review verdict '{proto_verdict}' binds "
                          f"{proto_rev_h}. ")
                       + (f"N0 node verdict on disk: {n0_latest[2]} score {n0_latest[3]} "
                          f"({n0_latest[1]}); the stop-rule items (4th resolution / F0 re-bind / "
                          "independent replication verdict) are the open requirement. "
                          if n0_latest else "No N0 node verdict found in reviews/. ")
                       + "C4 registration is repaired at this pass (the controller checkpoint "
                         "registers runtime/state/controller_verification/). G-NUM stays pending "
                         "until the N0 node verdict is an accept at one hash; N1 remains locked "
                         "regardless (it additionally requires G-FORM and G-AUDIT)."),
        },
        "G-AUDIT": {
            "verdict": gates.get("G-AUDIT", {}).get("verdict", "pending"),
            "checked_at": now(),
            "reason": (f"A0 rubric exists (measured {h('A0')}); A1 coverage at measured hashes: "
                       + ", ".join(f"{t} {len(acc(t))}" for t in ("F0", "F1", "F2a", "F2b", "L0"))
                       + " distinct accepts (need >=2 each); review verdicts at superseded hashes do "
                         "not count."
                       + (f" {len(f0_flags) + len(f1_flags) + len(f2b_flags)} class-separation soft "
                          "flag(s) across F0/F1/F2b await disposition."
                          if (f0_flags or f1_flags or f2b_flags) else "")),
        },
    }
    return audit


def findings_merge(m: dict, pub: dict, hashes: dict, soft: list, cov: dict,
                   clock: dict, guard: dict) -> list:
    """Controller findings are controller-owned: rewrite in place, preserve first-seen order/id."""
    order = [f.get("id") for f in m.get("controller_findings", [])]
    by_id = {f.get("id"): dict(f) for f in m.get("controller_findings", [])}
    ledger_clear = not any("ledger/" in s for s in soft)

    def h(nid: str) -> str:
        return (hashes.get(nid, {}).get("sha256") or "absent")[:12]

    def acc(t: str) -> list:
        return cov.get(t, {}).get("distinct_accept_reviewers", [])

    aligned = [p["canonical"] for p in pub["pairs"] if p["status"] == "aligned"]
    divergent = [(p["canonical"], p.get("canonical_sha256") or "absent",
                  p.get("authoring_sha256") or "absent")
                 for p in pub["pairs"] if p["status"] == "divergent"]
    companions = [p for p in pub["pairs"] if p.get("classification") == "companion"]
    want = [
        {"id": "CF-7", "severity": "major", "status": "resolved-by-adjudication",
         "finding": ("Four formulation artifacts were dual-tree divergent (canonical schemas/ + "
                     "research_map/ vs authoring artifacts/formulation/). Adjudicated at pass 04: "
                     "F1/F2a/F2b are byte-identical mirror pairs (aligned); the F0 pair is NOT a "
                     "mirror pair but two distinct artifacts - the declared F0 taxonomy "
                     "(research_map/formulation_taxonomy.yaml) and its class-contract supplement "
                     "(artifacts/formulation/formulation_taxonomy.yaml, F0-R) - so byte-identity in "
                     "either direction would destroy a frozen input (REC-3)."),
         "action": ("F0 pair reclassified as a companion pair: canonical path remains the declared "
                    "F0 artifact; the supplement must be hash-pinned where referenced and "
                    "consistency-checked. Remaining repair: the three schemas' class_contract_pointer "
                    "values still lack an explicit supplement sha256 pin "
                    "(astra-life04-freeze-repair)."),
         "evidence": ["artifacts/formulation/evidence/f0_mirror_conflict.json#7e3a7bc89a75",
                      "artifacts/formulation/FROZEN.json#logical_artifacts",
                      "runtime/state/artifact_hashes.json",
                      "research_map/research_map.json#publication_status"]},
        {"id": "CF-8", "severity": "minor",
         "status": "resolved-by-revision" if ledger_clear else "directive-issued",
         "finding": ("At 00:04-00:07 the L0 status summary claimed '4-class compliant with 0 extension "
                     "tokens' while audit_evidence.py flagged AF-WCC-VAC-BH-FORM in ledger/theorems.jsonl: "
                     "fluent claim contradicted by tooling."
                     + (f" The ledger was revised to {h('L0')} and the flag is cleared."
                        if ledger_clear else "")),
         "action": ("Recorded as a process finding; L0 still needs a new revision accepted at the "
                    "current hash (assigned L0-REVISE-01)."),
         "evidence": ["ledger/theorems.jsonl", "research_map/audit_evidence.py"]},
        {"id": "CF-9", "severity": "minor", "status": "adjudicated",
         "finding": ("Class-separation soft flags on formulation artifacts are documented 'candidate' "
                     "variant tokens (F2b: AF-SCC-L2LOC-VAC-GEN, AF-SCC-C0-DISTRIBUTIONAL-VAC-GEN; "
                     "F0: AF-WCC-VAC-GEN-SET, AF-SCC-C0-CH-VAC), not asserted class leakage; the "
                     "checker cannot see the annotation."),
         "action": ("folded into A1-REBIND-01: audit must either calibrate the checker to the "
                    "candidate annotation or record a documented blind spot."),
         "evidence": ["schemas/af_scc_c0_vacuum.yaml", "research_map/formulation_taxonomy.yaml",
                      "runtime/bin/classsep_regression.py"]},
        {"id": "CF-10", "severity": "info", "status": "verified",
         "finding": ("numerics_lock verified locked; N1 queued and numerics/spherical_solver absent; "
                     "lock guard numerics/tests/selfgravity_lock_guard.py present. C8 is met by the "
                     "rev3 protocol review (accept 4.5) and the N0 node verdict on disk is revise "
                     "(reviews/N0-review-lead-audit.json, stop-rule items open), so N0 stays "
                     "active/unverified and G-NUM stays pending."),
         "action": "G-NUM withheld; lock unchanged; N1 work remains forbidden.",
         "evidence": ["numerics/tests/selfgravity_lock_guard.py",
                      "reviews/G-NUM-protocol-review.json",
                      "reviews/N0-review-lead-audit.json"]},
        {"id": "CF-11", "severity": "info", "status": "recorded",
         "finding": (f"Lifecycle pass measured canonical hashes {h('F0')}/{h('F1')}/{h('F2a')}/"
                     f"{h('F2b')}/{h('L0')}/{h('L1')} and recorded them in the map; declared-vs-measured "
                     "hash drift is flagged per node by artifact_sha256_measured."),
         "action": "Checkpoint records the full artifact registry; reviewers must cite measured hashes.",
         "evidence": ["research_map/research_map.json", "runtime/state/artifact_hashes.json"]},
        {"id": "CF-12", "severity": "major", "status": "adjudicated",
         "finding": ("Canonical path numerics/tests/n0_gate_proposal.json was assigned to two agents at "
                     "once (astra-numfix-02 -> deepseek-flash-13 and astra-adj2-05/astra-indep-1 -> "
                     "astra-lead-numerics); the worker submission overwrote the lead's at 00:08-00:09. "
                     "One canonical path must have exactly one owner."),
         "action": ("Collision adjudicated: the canonical path holds deepseek-flash-13's proposal "
                    "a1109b32cf16, which the numerics lead accepted as consistent; the lead's adjudication "
                    "is preserved at artifacts/numerics/n0/n0_gate_proposal_lead.json#bfce1460fafa. "
                    "Controller rule recorded: never issue two open assignments naming the same canonical "
                    "path; a successor assignment must narrow or supersede, not duplicate."),
         "evidence": ["numerics/tests/n0_gate_proposal.json",
                      "artifacts/numerics/n0/n0_gate_proposal_lead.json",
                      "comms/outbox/astra-lead-numerics.jsonl"]},
        {"id": "CF-13", "severity": "major", "status": "resolved-by-adjudication",
         "finding": ("Dual-tree publication measured at this pass: "
                     + (f"{len(aligned)} mirror pair(s) aligned "
                        f"({', '.join(aligned)}); " if aligned else "0 mirror pairs aligned; ")
                     + (("divergent: " + "; ".join(f"{c} canonical={ch[:12]} authoring={ah[:12]}"
                                                   for c, ch, ah in divergent) + ". ")
                        if divergent else "no divergent mirror pairs. ")
                     + (f"{len(companions)} companion pair(s) recorded as distinct artifacts "
                        f"({', '.join(c['canonical'] for c in companions)}). " if companions else "")
                     + "Mirror pairs require canonical == authoring == FROZEN pin; companion pairs "
                       "require each path pinned and consistency-checked, not byte-identical."),
         "action": ("REC-3 (astra-life04) closes astra-life02-publish-f0 as impossible-as-written: "
                    "the F0 pair is two distinct artifacts (declared taxonomy + class-contract "
                    "supplement), so no byte-identical publication exists that preserves both. "
                    "The remaining F0-side repair is the missing supplement sha256 pin inside the "
                    "three schemas (astra-life04-freeze-repair)."),
         "evidence": ["research_map/formulation_taxonomy.yaml",
                      "artifacts/formulation/formulation_taxonomy.yaml",
                      "artifacts/formulation/evidence/f0_mirror_conflict.json#7e3a7bc89a75",
                      "artifacts/formulation/FROZEN.json",
                      "runtime/state/artifact_hashes.json"]},
        {"id": "CF-14", "severity": "major", "status": "partially-repaired",
         "finding": (f"Clock discipline: controller measured {clock['future_dated']} accepted event(s) "
                     f"with created_at after the measurement instant (max "
                     f"{clock.get('max_future_created_at')}, skew up to {clock['max_skew_seconds']}s). "
                     "FROZEN.json rev20 declares frozen_at 2026-09-12T00:15:00+08:00 but was written at "
                     "00:11:04. Future-dated records make 'binding at measured_at' claims and event "
                     "ordering unreliable."),
         "action": ("Authors must stamp created_at with wall-clock at write time; controller treats "
                    "future-dated events as advisory for ordering and re-measures the audit lead's "
                    "clock_discipline matrix (reviews/A1-rebind-coverage.json) each pass. Tooling "
                    "repair at pass 04: apply_events.py's resource-request approval matcher no longer "
                    "stops at the first colon, so ids containing ':' bind by exact token."),
         "evidence": ["research_map/events.jsonl", "reviews/A1-rebind-coverage.json",
                      "research_map/apply_events.py:263-284",
                      "artifacts/formulation/FROZEN.json"]},
        {"id": "CF-15", "severity": "info", "status": "recorded",
         "finding": ("Gate audit reasons are derived from the measured review corpus and publication "
                     f"status at this pass: distinct accepts at measured hashes F0 {len(acc('F0'))}, "
                     f"F1 {len(acc('F1'))}, F2a {len(acc('F2a'))}, F2b {len(acc('F2b'))}, "
                     f"L0 {len(acc('L0'))}; L1 spot checks at the measured hash: "
                     f"{len(l1_spotchecks(h('L1')))}; solver_absent={guard['solver_absent']}, "
                     f"guard_present={guard['guard_present']}"),
         "action": ("All gates remain pending; numerics_lock remains locked. Reviewers must cite measured "
                    "canonical hashes; superseded-hash verdicts are advisory only."),
         "evidence": ["research_map/research_map.json", "reviews/",
                      "runtime/state/artifact_hashes.json"]},
        {"id": "CF-16", "severity": "minor", "status": "adjudicated-false-positive",
         "finding": ("audit_evidence.py reports hard CLASSSEP failures on claims whose statements "
                     "quote the merged-case probe labels 'TC-F0-N14 C0/C2 merge' and 'TC-F0-N15 "
                     "WCC/SCC merge' (claims[36] first; claims[94,96,97,101,112,127,144] as of pass " 
                     "04). The claims state those cases are merged-case probes that 'need no new "
                     "class' and their class_ids are the frozen four: a metalinguistic mention, not "
                     "a composite class assertion."),
         "action": ("Adjudicated false positive; the raw hard-failure count stays visible in the "
                    "checkpoint until the claim prose is rephrased by its author or the checker exempts "
                    "quoted case labels (audit-lead calibration under astra-life01-a1-rebind). "
                    "Controller does not edit another agent's claim text (CF-4 policy)."),
         "evidence": ["research_map/class_separation.py:73-94",
                      "artifacts/flash-02/open_case_disposition.json",
                      "research_map/research_map.json claims[36]"]},
        {"id": "CF-17", "severity": "major", "status": "adjudicated",
         "finding": ("F0 publication adjudication (REC-3). Assignment astra-life02-publish-f0 required "
                     "byte-identical publication of research_map/formulation_taxonomy.yaml and "
                     "artifacts/formulation/formulation_taxonomy.yaml. Measured: these are two DIFFERENT "
                     "artifacts (canonical 276009f4: class_ids/classes/disjointness, 35145 b; authoring "
                     "c8e979a1: class_contracts/axis_registry/implication_ledger, 20937 b; the three "
                     "frozen schemas' class_contract_pointer targets the supplement's #class_contracts "
                     "subtree). Byte-identical publication in either direction destroys a frozen input."),
         "action": ("Ruled: the F0 pair is a COMPANION pair, not a mirror pair. The canonical path "
                    "remains the declared F0 artifact for G-F0; the authoring path is the class-contract "
                    "supplement (F0-R) and must be hash-pinned where referenced plus consistency-checked. "
                    "astra-life02-publish-f0 is closed as impossible-as-written; astra-life04-freeze-repair "
                    "adds the missing supplement sha256 pin to the three schemas. Falsifier: any frozen "
                    "consumer that requires the two files to be byte-identical, or a canonical F0 change "
                    "that invalidates the four class ids / disjointness tests."),
         "evidence": ["artifacts/formulation/evidence/f0_mirror_conflict.json#7e3a7bc89a75",
                      "artifacts/formulation/FROZEN.json#logical_artifacts",
                      "research_map/formulation_taxonomy.yaml",
                      "artifacts/formulation/formulation_taxonomy.yaml"]},
        {"id": "CF-18", "severity": "info", "status": "recorded",
         "finding": ("Pass-04 controller rulings on open lead requests: (a) literature BL-2 - rev 3 is "
                     "deferred until two independent verdicts bind the frozen L0 hash ce42d205, then "
                     "authorized as one bounded metadata patch (source_meta, conclusion_type/"
                     "artifact_refs, locator annotations; no claim or class changes); (b) BL-3 - "
                     "abstract-level evidence is sufficient for G-LIT provided verification_status is "
                     "honest and T-101/T-102 stay provisional; no paywalled full text is required for "
                     "the gate; (c) lit-l4-006 - evidence_url is the locator column and exact_locator is "
                     "query-provenance, so no hash-moving metadata patch is authorized now; (d) numerics "
                     "C4 - the replication evidence is registered in artifact_hashes.json via the "
                     "controller registry; C8 is met at protocol 1e6cdf04 but G-NUM stays pending on the "
                     "N0 node verdict; (e) F2b map-field report - adjudicated stale: the declared "
                     "F2b.artifact_sha256 at this pass is the 64-hex measured canonical hash "
                     "1bb78ce9b357, so no zero-padded value remains to repair."),
         "action": ("Rulings recorded here; operational assignment astra-life04-l0-rev3 carries the "
                    "literature scope. No gate verdict is changed by this finding."),
         "evidence": ["comms/outbox/astra-lead-literature.jsonl",
                      "comms/outbox/astra-lead-audit.jsonl",
                      "reviews/G-NUM-protocol-review.json",
                      "research_map/research_map.json"]},
        {"id": "CF-19", "severity": "major", "status": "directive-issued",
         "finding": ("Freeze breach on L0: ledger/theorems.jsonl was rewritten at 2026-09-12T00:35:19 "
                     f"(measured {h('L0')}) after the literature lead's L4 lifecycle closed with an "
                     "exit hash of 3e3d35531421 and after FROZEN-equivalent review dispatch. No "
                     "artifact event in the accepted stream announces the new bytes (worker-073 "
                     "observed the move mid-task and failed closed against the archived rev-3 copy). "
                     "This is the same moving-target defect as audit-blocker-final-01, on a canonical "
                     "path owned by one agent."),
         "action": ("No controller edit to another agent's artifact. astra-life04-l0-freeze-reconcile "
                    "issued to the literature lead: reconcile the live bytes against the rev-3 archive "
                    "(content preservation + claim-lowering diff), emit the artifact event with a "
                    "wall-clock stamp, and hold; the two-reviewer verdict round binds the reconciled "
                    "hash only. IF the write is not the owner's, it must be reverted/published from "
                    "the archive and reported as an authority violation."),
         "evidence": ["ledger/theorems.jsonl",
                      "artifacts/literature/archive/theorems.rev3-handpatch-20260912T003026.jsonl",
                      "artifacts/worker-073/l0_hf14_postrepair/report.json",
                      "research_map/research_map.json#controller_gate_audit"]},
    ]
    for f in want:
        old = by_id.get(f["id"], {})
        f["at"] = old.get("at", now())
        f["updated_at"] = now()
        by_id[f["id"]] = f
        if f["id"] not in order:
            order.append(f["id"])
    return [by_id[i] for i in order if i in by_id]


def main(label: str) -> dict:
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    map_sha_before = sha256(MAP)
    with LOCK.open("w") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            started_at = now()
            ing = comms.ingest(dry_run=False, verbose=True)
            applied = apply_events.main(dry_run=False)
            m = json.loads(MAP.read_text())
            hashes = measured_hashes(m)
            pub = publication_status()
            soft = audit_evidence.audit(MAP)["soft"]
            cov = review_coverage(hashes)
            clock = clock_discipline()
            guard = lock_guard(hashes)
            m["publication_status"] = pub
            m["controller_gate_audit"] = gate_audit(m, hashes, pub, soft, cov, clock, guard)
            m["controller_findings"] = findings_merge(m, pub, hashes, soft, cov, clock, guard)
            m["legacy_artifacts"] = [{
                "path": "schemas/af_scc_regularities.yaml",
                "sha256": digest("schemas/af_scc_regularities.yaml")["sha256"],
                "role": "non-class aggregator (legacy combined C0/C2 file); never a class artifact",
                "recorded_at": now()}]
            m["updated_at"] = now()
            errs = validate_map(m)
            outdir = ROOT / "runtime" / "state" / "controller_verification"
            outdir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(CST).strftime("%Y%m%d-%H%M%S")
            report_rel = str((outdir / f"lifecycle_{stamp}.json").relative_to(ROOT))
            lif = m.setdefault("controller_lifecycles", [])
            if not any(l.get("lifecycle_id") == label for l in lif):
                lif.append({"lifecycle_id": label, "actor": "astra", "started_at": started_at,
                            "ended_at": now(), "report_json": report_rel,
                            "validate_map": "VALID" if not errs else "INVALID",
                            "numerics_lock": m.get("numerics_lock", {}).get("state")})
            tmp = MAP.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(m, indent=2) + "\n")
            tmp.replace(MAP)
            map_sha_after = sha256(MAP)
            rec = checkpoint.main(label)
            report = {
                "label": label,
                "at": now(),
                "started_at": started_at,
                "map_sha256_before": map_sha_before,
                "map_sha256_after": map_sha_after,
                "map_validator": "VALID" if not errs else "INVALID",
                "map_errors": errs,
                "ingest": {k: ing[k] for k in ("accepted", "rejected", "duplicates", "files")},
                "events_applied": applied["applied"],
                "events_demoted": applied["demoted"],
                "gates": {g["gate_id"]: g.get("verdict") for g in m.get("gates", [])},
                "numerics_lock": m.get("numerics_lock", {}).get("state"),
                "lock_guard": guard,
                "measured_hashes": hashes,
                "publication_status": pub,
                "review_coverage": cov,
                "clock_discipline": clock,
                "controller_gate_audit": m["controller_gate_audit"],
                "controller_findings": [f["id"] for f in m["controller_findings"]],
                "evidence_hard_failures": rec["evidence_hard_failures"],
                "evidence_soft_findings": rec["evidence_soft_findings"],
                "classsep_regression": rec["classsep_regression"],
                "checkpoint_id": rec["checkpoint_id"],
            }
            path = outdir / f"lifecycle_{stamp}.json"
            path.write_text(json.dumps(report, indent=2, sort_keys=True))
            report["report_path"] = report_rel
            print("LIFECYCLE " + json.dumps({k: report[k] for k in
                  ("label", "map_validator", "events_applied", "gates", "numerics_lock",
                   "publication_status", "evidence_hard_failures", "checkpoint_id", "report_path")},
                  default=str)[:1500])
            return report
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="astra-lifecycle")
    a = ap.parse_args()
    main(a.label)
