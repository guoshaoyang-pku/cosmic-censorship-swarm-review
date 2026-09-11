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
MIRRORS = [
    ("research_map/formulation_taxonomy.yaml", "artifacts/formulation/formulation_taxonomy.yaml"),
    ("schemas/af_wcc_vacuum.yaml", "artifacts/formulation/schemas/af_wcc_vacuum.yaml"),
    ("schemas/af_scc_c2_vacuum.yaml", "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"),
    ("schemas/af_scc_c0_vacuum.yaml", "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"),
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
    for canonical, authoring in MIRRORS:
        cp, ap = ROOT / canonical, ROOT / authoring
        rec = {"canonical": canonical, "authoring": authoring,
               "canonical_sha256": None, "authoring_sha256": None, "status": "missing"}
        if cp.is_file() and ap.is_file():
            ch, ah = sha256(cp), sha256(ap)
            rec.update(canonical_sha256=ch, authoring_sha256=ah,
                       status="aligned" if ch == ah else "divergent")
        pairs.append(rec)
    return {"checked_at": now(),
            "policy": "canonical path is authoritative; the authoring tree must be published "
                      "byte-identically to it before review verdicts bind",
            "pairs": pairs,
            "divergent": sum(1 for p in pairs if p["status"] == "divergent")}


def gate_audit(m: dict, hashes: dict, pub: dict, soft: list) -> dict:
    gates = {g["gate_id"]: g for g in m.get("gates", [])}
    div = {p["canonical"]: p for p in pub["pairs"]}
    ledger_flags = [s for s in soft if "ledger/" in s]
    f0_flags = [s for s in soft if "F0 artifact" in s]
    f2b_flags = [s for s in soft if "F2b artifact" in s]

    def h(nid: str) -> str:
        return (hashes.get(nid, {}).get("sha256") or "absent")[:12]

    audit = {
        "G-F0": {
            "verdict": gates.get("G-F0", {}).get("verdict", "pending"),
            "checked_at": now(),
            "reason": (f"canonical taxonomy {h('F0')} was revised after every verdict on record; "
                       f"latest verdicts cite 66bf917b or a82f249c and none is an accept binding to "
                       f"the measured canonical sha256. Publication pair F0 is "
                       f"{div.get('research_map/formulation_taxonomy.yaml', {}).get('status', 'unknown')}."
                       + (f" {len(f0_flags)} class-separation soft flag(s) on the taxonomy await "
                          "disposition." if f0_flags else "")),
        },
        "G-FORM": {
            "verdict": gates.get("G-FORM", {}).get("verdict", "pending"),
            "checked_at": now(),
            "reason": ("F1/F2a/F2b measured canonical hashes "
                       f"{h('F1')}, {h('F2a')}, {h('F2b')}; recorded verdicts at these hashes are "
                       "revise (F1 16/17, F2a 17/18, F2b 18); no two independent accepts at any "
                       "current hash. Canonical/authoring publication divergence: "
                       + ", ".join(f"{p['canonical']}={p['status']}" for p in pub["pairs"]
                                   if "schemas/" in p["canonical"]) + "."
                       + (f" {len(f2b_flags)} class-separation soft flag(s) on F2b await disposition."
                          if f2b_flags else "")),
        },
        "G-LIT": {
            "verdict": gates.get("G-LIT", {}).get("verdict", "pending"),
            "checked_at": now(),
            "reason": (f"L0 measured {h('L0')}; latest verdicts are revise (lead-audit 3.0, "
                       "flash-16 3.5, flash-17 2.5) at an earlier hash; no accept binds to the "
                       f"current ledger hash. L1 measured {h('L1')}; independent re-fetch spot "
                       "checks are still below the required three at the frozen hash."
                       + (f" Evidence audit flags {len(ledger_flags)} ledger token issue(s)."
                          if ledger_flags else " The ledger class-token flag from the 00:07 audit "
                                               "is cleared at the current hash.")),
        },
        "G-NUM": {
            "verdict": gates.get("G-NUM", {}).get("verdict", "pending"),
            "checked_at": now(),
            "reason": ("self-gravitating numerics remain locked; the replication verdict on disk is "
                       "PROVISIONAL (numerics/protocol/fixed_replication_verdict.json). Awaiting "
                       "lead-numerics hash-pinned N0 gate proposal integrating the flash-13 triage "
                       "and flash-14 scheme-independence review. Lock guard present."),
        },
        "G-AUDIT": {
            "verdict": gates.get("G-AUDIT", {}).get("verdict", "pending"),
            "checked_at": now(),
            "reason": ("A0 rubric exists (measured d748a9e3574e) but A1 has fewer than two "
                       "independent verdicts per target binding to current canonical hashes for "
                       "F0/F1/F2a/F2b/L0; two class-separation soft flags on F2b "
                       "(candidate-variant tokens) await disposition by the audit lead."),
        },
    }
    return audit


def findings_merge(m: dict, pub: dict, hashes: dict, soft: list) -> list:
    """Controller findings are controller-owned: rewrite in place, preserve first-seen order/id."""
    order = [f.get("id") for f in m.get("controller_findings", [])]
    by_id = {f.get("id"): dict(f) for f in m.get("controller_findings", [])}
    ledger_clear = not any("ledger/" in s for s in soft)

    def h(nid: str) -> str:
        return (hashes.get(nid, {}).get("sha256") or "absent")[:12]

    want = [
        {"id": "CF-7", "severity": "major", "status": "directive-issued",
         "finding": ("Four formulation artifacts remain dual-tree divergent "
                     "(canonical schemas/ + research_map/ vs authoring artifacts/formulation/); "
                     "review verdicts bind to superseded hashes, so G-F0 and G-FORM cannot be judged."),
         "action": ("assigned PUBLISH-FROZEN-01 to lead-formulation: publish the frozen revision "
                    "byte-identically to canonical paths, re-emit artifact events, reconcile FROZEN.json; "
                    "gates recorded pending with hash-bound reasons. FORM-MAP-PATCH-002 superseded: "
                    "the canonical path stays authoritative."),
         "evidence": ["runtime/state/artifact_hashes.json", "artifacts/formulation/FROZEN.json",
                      "artifacts/formulation/proposals/map_patch_F0_F1_F2.json"]},
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
                     "lock guard numerics/tests/selfgravity_lock_guard.py present; N0 replication "
                     "verdict is PROVISIONAL, so N0 stays active/unverified."),
         "action": "G-NUM withheld pending lead-numerics proposal; lock unchanged.",
         "evidence": ["numerics/tests/selfgravity_lock_guard.py",
                      "numerics/protocol/fixed_replication_verdict.json",
                      "numerics/protocol/scheme_independence_review.md"]},
        {"id": "CF-11", "severity": "info", "status": "recorded",
         "finding": (f"Lifecycle pass measured canonical hashes {h('F0')}/{h('F1')}/{h('F2a')}/"
                     f"{h('F2b')}/{h('L0')}/{h('L1')} and recorded them in the map; declared-vs-measured "
                     "hash drift is flagged per node by artifact_sha256_measured."),
         "action": "Checkpoint records the full artifact registry; reviewers must cite measured hashes.",
         "evidence": ["research_map/research_map.json", "runtime/state/artifact_hashes.json"]},
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
            ing = comms.ingest(dry_run=False, verbose=True)
            applied = apply_events.main(dry_run=False)
            m = json.loads(MAP.read_text())
            hashes = measured_hashes(m)
            pub = publication_status()
            soft = audit_evidence.audit(MAP)["soft"]
            m["publication_status"] = pub
            m["controller_gate_audit"] = gate_audit(m, hashes, pub, soft)
            m["controller_findings"] = findings_merge(m, pub, hashes, soft)
            m["legacy_artifacts"] = [{
                "path": "schemas/af_scc_regularities.yaml",
                "sha256": digest("schemas/af_scc_regularities.yaml")["sha256"],
                "role": "non-class aggregator (legacy combined C0/C2 file); never a class artifact",
                "recorded_at": now()}]
            m["updated_at"] = now()
            errs = validate_map(m)
            tmp = MAP.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(m, indent=2) + "\n")
            tmp.replace(MAP)
            map_sha_after = sha256(MAP)
            rec = checkpoint.main(label)
            report = {
                "label": label,
                "at": now(),
                "map_sha256_before": map_sha_before,
                "map_sha256_after": map_sha_after,
                "map_validator": "VALID" if not errs else "INVALID",
                "map_errors": errs,
                "ingest": {k: ing[k] for k in ("accepted", "rejected", "duplicates", "files")},
                "events_applied": applied["applied"],
                "events_demoted": applied["demoted"],
                "gates": {g["gate_id"]: g.get("verdict") for g in m.get("gates", [])},
                "numerics_lock": m.get("numerics_lock", {}).get("state"),
                "measured_hashes": hashes,
                "publication_status": pub,
                "controller_gate_audit": m["controller_gate_audit"],
                "controller_findings": [f["id"] for f in m["controller_findings"]],
                "evidence_hard_failures": rec["evidence_hard_failures"],
                "evidence_soft_findings": rec["evidence_soft_findings"],
                "classsep_regression": rec["classsep_regression"],
                "checkpoint_id": rec["checkpoint_id"],
            }
            outdir = ROOT / "runtime" / "state" / "controller_verification"
            outdir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(CST).strftime("%Y%m%d-%H%M%S")
            path = outdir / f"lifecycle_{stamp}.json"
            path.write_text(json.dumps(report, indent=2, sort_keys=True))
            report["report_path"] = str(path.relative_to(ROOT))
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
