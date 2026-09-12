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


# --- R3 proposal: path/<node>@hash target aliases (W48-GFORM-COVERAGE-RULE-CHARACTERIZATION-01)
TARGET_PATH_ALIASES = {
    "research_map/formulation_taxonomy.yaml": "F0",
    "artifacts/formulation/formulation_taxonomy.yaml": "F0",
    "schemas/af_wcc_vacuum.yaml": "F1",
    "artifacts/formulation/schemas/af_wcc_vacuum.yaml": "F1",
    "schemas/af_scc_c2_vacuum.yaml": "F2a",
    "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml": "F2a",
    "schemas/af_scc_c0_vacuum.yaml": "F2b",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml": "F2b",
}


def _collect_hash_strings(v, out=None):
    """R3: recursively collect raw strings from str/dict/list values."""
    if out is None:
        out = []
    if isinstance(v, str):
        out.append(v.lower())
    elif isinstance(v, dict):
        for vv in v.values():
            _collect_hash_strings(vv, out)
    elif isinstance(v, list):
        for vv in v:
            _collect_hash_strings(vv, out)
    return out


def _norm_targets(t: str) -> set:
    """R3: normalise one target string (including comma/semicolon lists and
    path#hash / node@hash forms) to node ids."""
    out = set()
    for piece in re.split(r"[,;]", t):
        piece = piece.strip()
        if not piece:
            continue
        if piece in TARGET_ALIASES:
            out.add(TARGET_ALIASES[piece])
            continue
        if piece.upper() in TARGET_ALIASES:
            out.add(TARGET_ALIASES[piece.upper()])
            continue
        base = piece.split("#", 1)[0].split("@", 1)[0].strip()
        if base in TARGET_ALIASES:
            out.add(TARGET_ALIASES[base])
            continue
        if base.upper() in TARGET_ALIASES:
            out.add(TARGET_ALIASES[base.upper()])
            continue
        if base in TARGET_PATH_ALIASES:
            out.add(TARGET_PATH_ALIASES[base])
            continue
        name = base.rsplit("/", 1)[-1]
        if name in TARGET_PATH_ALIASES:
            out.add(TARGET_PATH_ALIASES[name])
    return out


def _targets_in_review(d: dict) -> set:
    out = set()
    for key in ("target_id", "target", "target_subnode", "class_id"):
        v = d.get(key)
        if isinstance(v, str):
            out.add(v)
        elif isinstance(v, dict):
            for k2 in ("target_id", "target_subnode", "subnode", "node_id", "class_id"):
                v2 = v.get(k2)
                if isinstance(v2, str):
                    out.add(v2)
                elif isinstance(v2, dict):
                    for k3 in ("target_id", "subnode", "node_id"):
                        if isinstance(v2.get(k3), str):
                            out.add(v2[k3])
    norm = set()
    for t in out:
        norm |= _norm_targets(t)
    return norm


def _explicit_pins(d: dict) -> list:
    """R3: hashes a review explicitly pins (not hashes merely mentioned in prose).
    Adds recursive flattening of dict/list-valued pins, the recognised target
    sha256 keys, and hex fragments carried by target strings (# and @ forms)."""
    pins = []
    for key in ("artifact_sha256", "reviewed_sha256", "sha256", "cited_sha256",
                "target_sha256"):
        for s in _collect_hash_strings(d.get(key)):
            if re.fullmatch(r"[0-9a-f]{8,64}", s):
                pins.append(s)
            else:
                pins.extend(m.group(0) for m in re.finditer(r"[0-9a-f]{8,64}", s))
    for key in ("target", "artifact"):
        v = d.get(key)
        if isinstance(v, dict):
            for k2 in ("sha256", "artifact_sha256", "reviewed_sha256"):
                for s in _collect_hash_strings(v.get(k2)):
                    pins.extend(m.group(0) for m in re.finditer(r"[0-9a-f]{8,64}", s))
    for key in ("target_id", "target", "target_subnode"):
        v = d.get(key)
        if isinstance(v, str):
            for part in re.split(r"[#,@\s]+", v):
                if re.fullmatch(r"[0-9a-f]{8,64}", part):
                    pins.append(part)
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
                     "lock guard numerics/tests/selfgravity_lock_guard.py present. C8: the rev3 "
                     "protocol review accept 4.5 binds protocol 1e6cdf04d7a2 but two revise verdicts "
                     "contest the evidence basis at the same hash; the basis has since been re-based, "
                     "so astra-life05-gnum-protocol-adjudication must settle the operative verdict. "
                     "The N0 node verdict on disk is still revise and N0 rev3 stop-rule evidence "
                     "exists; G-NUM stays pending until an N0 accept at one hash."),
         "action": ("G-NUM withheld; lock unchanged; N1 work remains forbidden. C4 registration "
                    "repaired this pass (registry scan roots now cover numerics/, "
                    "artifacts/numerics/ and evaluation_rubric.yaml)."),
         "evidence": ["numerics/tests/selfgravity_lock_guard.py",
                      "numerics/CONVERGENCE_PROTOCOL.md#1e6cdf04d7a2",
                      "reviews/G-NUM-protocol-review.json",
                      "numerics/results/flat_wave_convergence_rev3.json",
                      "runtime/state/artifact_hashes.json"]},
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
         "action": ("G-F0 passed at the measured hash on four distinct accepts; G-FORM/G-LIT/G-NUM/"
                    "G-AUDIT remain pending. Reviewers must cite measured canonical hashes; "
                    "superseded-hash verdicts are advisory only."),
         "evidence": ["research_map/research_map.json", "reviews/",
                      "runtime/state/artifact_hashes.json"]},
        {"id": "CF-16", "severity": "minor", "status": "adjudicated-decision-c-review-pending",
         "finding": ("audit_evidence.py reports hard CLASSSEP failures on claims whose statements "
                     "quote, negate, split or audit the merged-case token: the claims' class_ids are "
                     "the frozen four, so this is a metalinguistic mention, not a composite class "
                     "assertion, and traffic ABOUT the finding reproduces the token (per-author "
                     "rewording is an unbounded loop). The r3 adjudication landed 01:03-01:05 "
                     "(reviews/CLASSSEP-calibration-adjudication.json 7714ffd5b467, decision (c)): a "
                     "four-arm, five-corpus census at cited hashes finds NO adoptable arm - APPLIED "
                     "a8c04fc3 19 hard (17 labeled metalinguistic FP + 2 DETECTOR_SELF meta-claims), "
                     "sensitivity 4/6, specificity 3/10, battery 13/23, 1 HIGH cue-induced FN (A04 "
                     "clause boundary); PRE c266dbec 24 hard, spec 1/10; STAGED e2d24b92 25 hard, "
                     "sens 5/6, spec 1/10; PROSEFIX dc8aa0de spec 10/10 and battery 23/23 but 10 HIGH "
                     "cue-induced FN. Assertion-vs-mention is not lexically separable at this window; "
                     "no adoption, no rollback-by-audit, no claim retirement (raw count stands)."),
         "action": ("Ruled (REC-30): the decision is operative only after exactly one independent "
                    "non-author review at the frozen hashes (astra-life07-classsep-adjudication-review, "
                    "deadline 02:30) reproduces the census and the FN attribution correction "
                    "(dc8aa0de carries the 10/10 suppression, not e2d24b92). Detector writes stay "
                    "frozen; the active frozen pin stays c266dbecaa87 and e36b0d644ca-bound "
                    "measurements are void (CF-29). The controller does not edit another agent's "
                    "claim text (CF-4 policy); G-AUDIT stays pending."),
         "evidence": ["research_map/class_separation.py#a8c04fc31e4a",
                      "reviews/CLASSSEP-calibration-adjudication.json#7714ffd5b467",
                      "artifacts/worker-049/classsep_fn_audit/results.json#9e1bf2043934",
                      "artifacts/worker-098/classsep_prose_shadow/drift_recheck.json#ffabb753313f",
                      "proposed/class_separation.py#e2d24b927ee8",
                      "runtime/state/controller_verification/astra-lifecycle-06-decisions.json"]},
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
        {"id": "CF-19", "severity": "major", "status": "resolved-by-reconciliation",
         "finding": ("Freeze breach on L0: ledger/theorems.jsonl was rewritten at 2026-09-12T00:35:19 "
                     f"(measured {h('L0')}) after the literature lead's L4 lifecycle closed with an "
                     "exit hash of 3e3d35531421 and after FROZEN-equivalent review dispatch. No "
                     "artifact event in the accepted stream announced the new bytes at the time "
                     "(worker-073 observed the move mid-task and failed closed against the archived "
                     "rev-3 copy). Pass-05 measurement: the live bytes are now announced by the owner "
                     "as rev3 FINAL (build product regenerated from the repaired sources), so the "
                     "breach is reconciled at this hash."),
         "action": ("REC-13 (astra-lifecycle-05): CF-19/REC-10 closed by the owner's announced "
                    "source-of-truth rebuild at " + h('L0') + " with a per-file content-preservation "
                    "record; the earlier 3e3d3553 pin and all ce42d205 verdicts are void. Two blind "
                    "accepts at the announced hash are required before G-LIT is proposable "
                    "(astra-life05-verify-l0-final). Any further ledger write re-opens the finding."),
         "evidence": ["ledger/theorems.jsonl#" + h('L0'),
                      "artifacts/literature/tools/build_literature.py",
                      "artifacts/literature/reviews/rev3-axis-split.json",
                      "research_map/research_map.json#controller_gate_audit"]},
        {"id": "CF-20", "severity": "major", "status": "repair-landed-review-pending",
         "finding": ("Evidence-binding chain was stale at the frozen formulation bytes: "
                     "schemas/taxonomy_cases.jsonl had 36/36 rows bound to the superseded taxonomy "
                     "hash 66bf917bd368 while its meta pointed at rev5, and all three rev12 schemas "
                     "declared consistency_evidence_sha256 675a99d0 while the live "
                     "artifacts/formulation/evidence/taxonomy_consistency.json was 9e335e9ba1bf; the "
                     "schemas' own binding rule forbade a gate verdict until the evidence was "
                     "refreshed. The repair landed before this pass: the case corpus is rebound "
                     "(schemas/taxonomy_cases.jsonl ccf7041bd0ff) and the schemas are rev13 "
                     + h("F1") + " / " + h("F2a") + " / " + h("F2b") + " under FROZEN rev29, all "
                     "three mirror pairs aligned. Review coverage at the rev13 hashes is 0 accepts "
                     "per class: the rev12 verdicts are void with their pins, so G-FORM is withheld "
                     "on fresh review, not on a known defect."),
         "action": ("astra-life05-verify-gform-r3 (audit lead, deadline 02:45) is the only binding "
                    "path: two independent non-author reviewers per class at the rev29 pins, each "
                    "verdict measuring and citing the file sha256, no target write during the round. "
                    "The controller does not re-pin review verdicts and does not move G-FORM on a "
                    "landed repair alone; see CF-27 for the FROZEN meta move inside this window."),
         "evidence": ["schemas/taxonomy_cases.jsonl#ccf7041bd0ff",
                      "artifacts/formulation/evidence/taxonomy_consistency.json#9e335e9ba1bf",
                      "artifacts/formulation/FROZEN.json",
                      "schemas/af_wcc_vacuum.yaml#" + h("F1"),
                      "schemas/af_scc_c2_vacuum.yaml#" + h("F2a"),
                      "schemas/af_scc_c0_vacuum.yaml#" + h("F2b"),
                      "runtime/state/controller_verification/astra-lifecycle-06-decisions.json"]},
        {"id": "CF-21", "severity": "minor", "status": "recorded-open",
         "finding": ("AF-WCC-SCALAR-SPH axes.genericity_kind is 'unresolved' / "
                     "genericity_value_status 'unresolved_pending_L1' while its rev5 conclusion "
                     "explicitly quantifies over 'a comeager set G of data'. Four reviewers split: "
                     "three non-blocking (worker-025, worker-038, deepseek-flash-19 soft), one major "
                     "(worker-094 F-094C-1: 'the exact-genericity record cannot be both'). No "
                     "declared checker compares the field, so the suites pass either way."),
         "action": ("G-F0 passed on the content criteria with this finding recorded, NOT discharged. "
                    "The conclusion text is authoritative for the class predicate; the axis token is "
                    "stale metadata. F0 canonical bytes 0abb9ed8a961 are frozen by REC-11: any write "
                    "voids the gate and requires fresh accepts. If a future revision repairs the "
                    "axis, it must re-run the F0 review round."),
         "evidence": ["research_map/formulation_taxonomy.yaml#0abb9ed8a961:393,414",
                      "reviews/F0-conformance-038-rev28.json",
                      "reviews/closefind-verify-094.json",
                      "runtime/state/controller_verification/astra-lifecycle-05-decisions.json"]},
        {"id": "CF-22", "severity": "minor", "status": "repaired",
         "finding": ("Worker task-status leaked onto node status: worker-081's withdrawal of task "
                     "W081-N0-FDT-02 (status=rejected, last_status 00:42:19) set numerics node N0 to "
                     "rejected, even though the worker's own summary says the task was re-scoped and "
                     "the N0 stop-rule deliverable exists. Worker events describe tasks; node status "
                     "is a controller/lead field."),
         "action": ("Controller repair (idempotent, in astra_lifecycle.controller_repairs): N0 "
                    "restored to active; the repair is recorded in map.controller_repairs. Leads "
                    "must not let a worker status event stand as a node verdict; only controller/"
                    "lead status events move node state."),
         "evidence": ["comms/outbox/worker-081.jsonl",
                      "numerics/results/flat_wave_convergence_rev3.json",
                      "research_map/research_map.json#controller_repairs"]},
        {"id": "CF-23", "severity": "minor", "status": "artifact-landed-verification-pending",
         "finding": ("A0 detector scope defect (literature lead, 00:44): the HF-14/HF-03 detectors "
                     "reported corpus-level hits on archive/, incoming/ and worker snapshot paths "
                     "that are historical records, not live artifacts (8 files after the rev-3 "
                     "repair). A measurement ambiguity in A0, not a ledger defect. The scoped "
                     "adjudication landed this pass at "
                     "evaluation/A0_detector_scope_adjudication.json (a26be4b85706, 00:53:51): an "
                     "exclusion predicate classify(rel) in {historical, snapshot_copy}, explicit "
                     "class lists, and a measured before/after file census at pinned hashes. It "
                     "carries no independent verdict yet."),
         "action": ("astra-life04-verify-a0 (audit lead, deadline 02:00) must bind the rubric and "
                    "state, for each prior finding, whether the scope artifact resolves it, with a "
                    "cited sha256; no rubric edit, no gate self-pass. Verification must confirm no "
                    "live-artifact hit is hidden by the exclusion."),
         "evidence": ["evaluation/A0_detector_scope_adjudication.json#a26be4b85706",
                      "artifacts/audit/reports/audit-20260912T003820.json",
                      "evaluation_rubric.yaml:244-252"]},
        {"id": "CF-24", "severity": "info", "status": "recorded",
         "finding": ("G-F0 is the first gate to pass: declared F0 taxonomy 0abb9ed8a961 rev5 with "
                     "companion supplement d7419b4e8963 under FROZEN rev28 2f358f6722d9, four "
                     "distinct independent accepts at the measured hash, 6/6 disjointness pairs. "
                     "F0 promoted to done/passed by controller repair with PROTOCOL-rule-2 evidence. "
                     "No numerics consequence: G-NUM additionally requires G-FORM + G-AUDIT, which "
                     "remain pending; the lock is untouched."),
         "action": ("F0 canonical bytes are frozen; any write voids G-F0. G-FORM awaits the "
                    "evidence-binding repair and rev29 re-review; L0 awaits two accepts; N0 awaits "
                    "the protocol adjudication and node verdict; A0/A1 await calibration and "
                    "coverage."),
         "evidence": ["research_map/research_map.json#gates.G-F0",
                      "reviews/F0-review-025.json", "reviews/F0-conformance-038-rev28.json",
                      "runtime/state/controller_verification/astra-lifecycle-05-decisions.json"]},
        {"id": "CF-25", "severity": "minor", "status": "repaired",
         "finding": ("Done-node status volatility: the 15-minute auto-cycle "
                     "(research_map/run_cycle.py, which applies traffic between controller passes) "
                     "applied a worker status event on F0 at 00:50:08 that reverted the controller's "
                     "F0 done/passed promotion (applied 00:49:19) back to active. Worker status "
                     "events describe their task, not node state."),
         "action": ("Tool repair landed: apply_events.py ignores non-authority status events on a "
                    "done node (recorded in status_events_ignored), and "
                    "astra_lifecycle.controller_repairs re-asserts the F0 promotion every pass. No "
                    "artifact, hash or gate verdict changed."),
         "evidence": ["research_map/apply_events.py", "research_map/run_cycle.py",
                      "research_map/research_map.json#controller_repairs"]},
        {"id": "CF-26", "severity": "major", "status": "adjudicated-decision-c-instrument-moved-again",
         "finding": ("Class-separation instrument drifted mid-review with no recorded authority: "
                     "research_map/class_separation.py moved c266dbecaa87 -> a8c04fc31e4a at "
                     "00:52:00 (mtime), 36 s after the pass-05 lifecycle exit. No controller repair, "
                     "gate event, assignment card or author artifact declares the write; the pass-05 "
                     "summary lists only tool repairs. audit_evidence.py hard-fails 'frozen artifact "
                     "drifted during review' against the active frozen_artifacts pin (frozen 23:30:20, "
                     "reason: class-separation gate used for G-FORM/G-AUDIT). The applied guard was "
                     "contested (worker-098 revise 3.0 vs worker-049 pre-registered adversarial FN "
                     "audit). The r3 adjudication returned decision (c) at 01:03-01:05: not lexically "
                     "separable, no adoption, no rollback-by-audit, pin stays c266dbec. The instrument "
                     "then moved a THIRD time, a8c04fc31e4a -> e36b0d644ca at 01:06:12, during the "
                     "REC-22 freeze and with no authorizing event (see CF-29)."),
         "action": ("No adoption and no frozen-pin refresh: the c266dbec pin stays active as the "
                    "recorded baseline. The e36b0d644ca revision is void, preserved as evidence and "
                    "the live bytes were restored to the adjudicated r3 APPLIED bytes a8c04fc31e4a "
                    "from a hash-verified pin so the independent review runs at unchanged hashes "
                    "(REC-29/CF-29). Every verdict that used the detector must cite the hash it "
                    "measured; c266dbec-bound and e36b0d644ca-bound reviews are void at the restored "
                    "bytes. Any further detector write voids the round and is a new finding."),
         "evidence": ["research_map/class_separation.py#a8c04fc31e4a",
                      "runtime/state/controller_verification/cf29-detector-write-forensics.json",
                      "runtime/state/controller_verification/class_separation.e36b0d644ca.evidence.py",
                      "reviews/CLASSSEP-calibration-adjudication.json#7714ffd5b467",
                      "artifacts/worker-049/classsep_fn_audit/pinned/class_separation_c266_recovered.py#c266dbceca87",
                      "runtime/state/controller_verification/astra-lifecycle-06-decisions.json"]},
        {"id": "CF-27", "severity": "minor", "status": "recorded-for-review-round",
         "finding": ("Binding document moved inside the G-FORM r3 review window under the same "
                     "revision number: artifacts/formulation/FROZEN.json measured 3d9e3d77fd87 in "
                     "the pass-06 pre-flight (00:54) and 815e08079aefbc at 00:57:27, with the "
                     "declared revision still 29. The rev13 schema bytes themselves were stable "
                     "across the same window (d9cebb9404b2 / e9a27996dfd3 / b2ab6acb2bbe, all three "
                     "mirror pairs aligned), so this is meta-document drift, not a schema move."),
         "action": ("astra-life05-verify-gform-r3 reviewers must measure and cite the FROZEN bytes "
                    "(815e08079aefbc) plus each per-file pin before binding; the card's moving-target "
                    "stop rule applies. If any per-file pin changed inside the round, stop and "
                    "report rather than re-reviewing a moving target. No gate movement on the meta "
                    "move alone."),
         "evidence": ["artifacts/formulation/FROZEN.json#815e08079aefbc",
                      "schemas/af_wcc_vacuum.yaml#d9cebb9404b2",
                      "schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3",
                      "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe"]},
        {"id": "CF-28", "severity": "minor", "status": "recorded-quarantined-extended",
         "finding": ("Controller inbox integrity: comms/inbox/astra.jsonl line 2 is not valid JSON "
                     "- a stray prefix 'event_id:human-pi-overnight-20260912T0042n' is glued to an "
                     "assignment object (event_id human-pi-detector-fix-20260912T0100, actor "
                     "'astra', created_at 01:00, future-dated, assignee lead-audit) that duplicates "
                     "the standing A0 detector-scope card with a different, code-changing "
                     "acceptance and arrived after the detector had already been rewritten (00:52). "
                     "No human-pi event exists in the accepted stream; the line cannot be ingested "
                     "and is not authority for any action. EXTENDED at pass 07 (CF-30): the same "
                     "injection batch also planted well-formed cards in the audit-lead inbox and a "
                     "new line in this controller inbox."),
         "action": ("Quarantined byte-verbatim and recorded, not actioned: no card was issued from it "
                    "and no canonical path was duplicated (CF-12). The standing + amended detector "
                    "cards govern. Any genuine Human-PI directive must be re-sent as a well-formed "
                    "event through the protocol; writers must not hand-edit inbox JSONL."),
         "evidence": ["comms/inbox/astra.jsonl",
                      "runtime/state/comms_quarantine/astra-inbox-line2-20260912T0100.jsonl",
                      "runtime/state/comms_quarantine/astra-inbox-line3-20260912T0112.jsonl",
                      "comms/PROTOCOL.md",
                      "runtime/state/controller_verification/astra-lifecycle-06-decisions.json"]},
        {"id": "CF-29", "severity": "major", "status": "voided-restored-frozen",
         "finding": ("Unauthorized third write to the frozen class-separation instrument during the "
                     "REC-22/astra-life06 round: research_map/class_separation.py measured "
                     "a8c04fc31e4a (the r3 adjudication's APPLIED bytes) through 01:04 and was "
                     "rewritten to e36b0d644ca75b1e at 01:06:12 (mtime), after the adjudication "
                     "artifact landed. No accepted-stream event references e36b0d644ca, no "
                     "assignment card authorizes it, and the change is a one-line widening of the "
                     "mention guard ('0 genuine assertions' + optional 'or describes the' "
                     "suppression), i.e. the exact class of false-negative risk the adjudication "
                     "left open. The write raced the independent-review phase the decision requires."),
         "action": ("Ruled (REC-29): e36b0d644ca is not adopted and every e36b0d644ca-bound "
                    "measurement is void; the active frozen pin stays c266dbecaa87. The unauthorized "
                    "bytes are preserved byte-verbatim at "
                    "runtime/state/controller_verification/class_separation.e36b0d644ca.evidence.py "
                    "with a forensic manifest, and the live instrument was mechanically restored to "
                    "the hash-verified adjudicated bytes a8c04fc31e4a before the independent review. "
                    "This is a byte-identity restoration of a pinned artifact, not a code edit or an "
                    "adoption. Any further write to the detector voids the round and aborts the "
                    "review."),
         "evidence": ["runtime/state/controller_verification/cf29-detector-write-forensics.json",
                      "runtime/state/controller_verification/class_separation.e36b0d644ca.evidence.py",
                      "research_map/class_separation.py#a8c04fc31e4a",
                      "artifacts/worker-073/classsep_union_separability/pinned/class_separation.live.a8c04fc31e4a.py",
                      "runtime/state/controller_verification/astra-lifecycle-06-decisions.json#REC-22"]},
        {"id": "CF-30", "severity": "major", "status": "recorded-quarantined-not-authority",
         "finding": ("Downward-channel injection: cards attributed to actor 'astra' appeared in "
                     "comms/inbox/astra.jsonl line 3 and comms/inbox/astra-lead-audit.jsonl lines "
                     "24, 25, 27 with no corresponding accepted-stream event and no controller "
                     "lifecycle emission - 'human-pi-detector-fix-20260912T0100' (the well-formed "
                     "twin of the CF-28 malformed payload), 'astra-detector-fix-0105' (created_at "
                     "01:05:00 but written by 01:00:35) and 'astra-detector-patch-result-0112' "
                     "(created_at 01:12:00, written 01:06:56, reporting the e36b0d644ca state that "
                     "appeared at 01:06:12). Each directs a detector write or freeze action, "
                     "conflicting with REC-22 and the no-self-pass rule. The audit lead correctly "
                     "refused to author the fix it measures (blocker "
                     "audit-l07-b4-audit-author-conflict-20260912T010517)."),
         "action": ("Ruled (REC-31): the cards are quarantined byte-verbatim, are not authority, and "
                    "are not actioned; the audit lead's conflict refusal is upheld and the detector "
                    "edit is not reassigned to it. Their state claim is independently corroborated by "
                    "measurement (CF-29) and is recorded as evidence, not as instruction. A genuine "
                    "Human-PI directive must be re-sent as a well-formed accepted event through "
                    "comms/outbox; writers must not hand-edit inbox JSONL."),
         "evidence": ["runtime/state/comms_quarantine/astra-inbox-line3-20260912T0112.jsonl",
                      "runtime/state/comms_quarantine/astra-lead-audit-inbox-lines24-25-27-20260912T0112.jsonl",
                      "runtime/state/controller_verification/cf29-detector-write-forensics.json",
                      "comms/outbox/astra-lead-audit.jsonl",
                      "comms/PROTOCOL.md"]},
    ]
    for f in want:
        old = by_id.get(f["id"], {})
        f["at"] = old.get("at", now())
        f["updated_at"] = now()
        by_id[f["id"]] = f
        if f["id"] not in order:
            order.append(f["id"])
    return [by_id[i] for i in order if i in by_id]


AUTHORITY_ACTORS = {"astra", "lead-formulation", "lead-literature", "lead-numerics", "lead-audit",
                    "astra-lead-formulation", "astra-lead-literature", "astra-lead-numerics",
                    "astra-lead-audit"}


def controller_repairs(m: dict, hashes: dict, cov: dict, guard: dict) -> list:
    """Bounded, idempotent controller repairs, one record per (kind, target).

    Pass-05 scope: (1) promote F0 to done/passed once G-F0 has passed and the measured
    canonical hash carries >=2 distinct accepts (PROTOCOL rule 2); (2) restore a node
    status that a worker task-status leaked onto a node; (3) refresh the stale
    numerics/gates.py evidence pin on G-NUM; (4) record the audit_evidence.py registry
    scan-root repair. It never edits another agent's artifact or claim text.
    """
    reps = m.setdefault("controller_repairs", [])
    ts = now()
    added = []

    def rec(kind, target, detail, evidence):
        if any(r.get("kind") == kind and r.get("target") == target for r in reps):
            return
        entry = {"at": ts, "by": "astra", "kind": kind, "target": target,
                 "detail": detail, "evidence": evidence}
        reps.append(entry)
        added.append(entry)

    nodes = {n["id"]: n for g in m.get("groups", []) for n in g.get("nodes", [])}
    gates = {g["gate_id"]: g for g in m.get("gates", [])}

    # 1. F0 promotion: gate pass + >=2 distinct accepts at the measured canonical hash.
    # Enforced every pass (not only on first record): worker status events used to revert
    # a done node between controller passes (CF-25), so the promoted state is re-asserted.
    f0 = nodes.get("F0")
    f0h = hashes.get("F0", {}).get("sha256")
    accs = cov.get("F0", {}).get("distinct_accept_reviewers", [])
    if f0 and gates.get("G-F0", {}).get("verdict") == "pass" and f0h and len(accs) >= 2:
        f0["status"] = "done"
        f0["validation_status"] = "passed"
        f0["artifact_sha256"] = f0h
        f0["artifact_exists"] = True
        refs = list(f0.get("evidence_refs") or [])
        for r in ("reviews/F0-review-025.json", "reviews/F0-conformance-038-rev28.json",
                  "reviews/F0-review-18.json", "reviews/F0-review-19.json",
                  "artifacts/formulation/FROZEN.json",
                  "runtime/state/controller_verification/astra-lifecycle-05-decisions.json"):
            if r not in refs:
                refs.append(r)
        f0["evidence_refs"] = refs
        rec("node_promotion", "F0",
            ("G-F0 passed at " + f0h[:12] + " with " + str(len(accs)) + " distinct accepts ("
             + ", ".join(accs) + "); node promoted on artifact + review evidence (PROTOCOL rule 2). "
             "Any write to the canonical taxonomy voids the verdict and needs fresh accepts."),
            ["research_map/formulation_taxonomy.yaml#" + f0h[:12],
             "research_map/research_map.json#gates.G-F0"])

    # 2. Restore a node status that a worker task-status event leaked onto the node.
    for nid in ("N0",):
        n = nodes.get(nid)
        if not n:
            continue
        last_by = str((n.get("last_status") or {}).get("by", ""))
        if n.get("status") == "rejected" and last_by not in AUTHORITY_ACTORS:
            n["status"] = "active"
            rec("node_status_restore", nid,
                ("worker event by " + last_by + " set node status=rejected for a withdrawn TASK; "
                 "restored to active. The node is not rejected: lock-compatible flat-space work "
                 "continues and the stop-rule deliverable numerics/results/"
                 "flat_wave_convergence_rev3.json is on disk."),
                ["comms/outbox/" + last_by + ".jsonl",
                 "research_map/research_map.json#numerics_lock"])

    # 3. Re-pin the stale numerics/gates.py evidence ref on G-NUM.
    gnum = gates.get("G-NUM")
    gpath = ROOT / "numerics" / "gates.py"
    if gnum and gpath.is_file():
        new_ref = "numerics/gates.py#" + sha256(gpath)[:12]
        stale = {"numerics/gates.py#907a88b141bf4394"}
        refs = gnum.get("evidence_refs", [])
        if any(r in stale for r in refs):
            gnum["evidence_refs"] = sorted({r for r in refs if r not in stale} | {new_ref})
            rec("map_pin_refresh", "G-NUM",
                ("replaced the stale evidence ref numerics/gates.py#907a88b141bf4394 with "
                 + new_ref + " (lead-numerics 00:37 blocker: the guard was fixed to bind target_id "
                 "G-NUM-protocol; the old ref is historical)."),
                [new_ref, "comms/outbox/astra-lead-numerics.jsonl"])

    # 4. Tool repair record: registry scan roots (C4).
    rec("tool_repair", "research_map/audit_evidence.py",
        ("registry scan roots extended to numerics/, artifacts/numerics/ and the repo-root "
         "evaluation_rubric.yaml; __pycache__/.pyc excluded. Closes the C4 registration gap: "
         "protocol 1e6cdf04d7a2, artifacts/numerics/n0/* and the N0 rev3 stop-rule deliverable "
         "are registered for PROTOCOL rule 2."),
        ["runtime/state/artifact_hashes.json",
         "artifacts/worker-14/registration_audit/registration_coverage.json"])

    # 5. Tool repair record: validator base path (latent done-node check bug).
    rec("tool_repair", "research_map/validate_map.py",
        ("validate_map() default base corrected from this module's directory to the repo root, so "
         "declared repo-root-relative artifact paths resolve. The bug was latent until the first "
         "done-with-artifact node (F0) and produced a false 'declared artifact missing on disk'."),
        ["research_map/validate_map.py:16-22", "research_map/formulation_taxonomy.yaml"])

    # 6. Tool repair record: done-node status protection (CF-25).
    rec("tool_repair", "research_map/apply_events.py",
        ("a node already done (promoted on artifact + review evidence) is no longer demoted by a "
         "non-authority status event; the event is recorded in status_events_ignored. The "
         "15-minute auto-cycle (run_cycle.py) applies traffic between controller passes and "
         "silently reverted the F0 promotion at 00:50:08, one minute after it was applied."),
        ["research_map/apply_events.py", "research_map/run_cycle.py",
         "research_map/research_map.json#controller_repairs"])
    return added


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
            m["controller_repairs_log"] = controller_repairs(m, hashes, cov, guard)
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
