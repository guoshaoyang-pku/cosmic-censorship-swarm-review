#!/usr/bin/env python3
"""W14-GNUM-REGAUDIT-01: post-repair registry-coverage audit of the N0/G-NUM anchor set.

Class AF-WCC-SCALAR-SPH, node N0, gate G-NUM. Read-only measurement; no gate verdict.

Question: after pass 04's C4 repair (REC-7), which hash-cited N0/G-NUM anchors are
actually covered by runtime/state/artifact_hashes.json, which are not, and why?

Method (fully deterministic; no wall-clock in the payload):
  1. Read runtime/state/artifact_hashes.json once and record its sha256 (point-in-time pin).
  2. Read the current registry scan roots directly from research_map/audit_evidence.py
     (the `for d in (...)` tuple) and record that source's sha256. This makes the audit
     self-invalidating if the controller changes the scan scope.
  3. For every anchor in the N0/G-NUM anchor set, measure the on-disk sha256 and classify:
       registered_match | registered_mismatch | not_registered_inside_scan_roots |
       not_registered_outside_scan_roots | absent_on_disk
  4. Compare measured hashes against the prefixes cited by the reviewed records where a
     cited prefix exists (stale-citation check for the N0 review's unpinned evidence_refs).
  5. Emit one sorted JSON document.

Falsifier: re-running this script at the same pinned inputs yields a different
classification for any anchor, or any path classified outside_scan_roots is in fact
under an extracted scan root, or any classification disagrees with the recorded
registry_sha256 / audit_evidence.py sha256.

Usage: python3 artifacts/worker-14/registration_audit/registration_coverage.py
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CST = timezone(timedelta(hours=8))
OUT = ROOT / "artifacts" / "worker-14" / "registration_audit" / "registration_coverage.json"

# An anchor: path + role + where the citation comes from + the prefix cited by a reviewed
# record (None when the citing record carries no hash for that path).
ANCHORS = [
    # --- C4 registration requests from the worker C4 manifest (astra-numfix-03 residual) ---
    dict(path="numerics/CONVERGENCE_PROTOCOL.md",
         role="protocol-of-record rev3; C8 accept binds this hash",
         cited_prefix="1e6cdf04d7a24313",
         cited_source="reviews/G-NUM-protocol-review.json reviewed_sha256"),
    dict(path="runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json",
         role="controller FIXED replication run; R5/delta provenance anchor",
         cited_prefix="6542db93eebc5095",
         cited_source="reviews/G-NUM-protocol-review.json open_items / map G-NUM evidence_refs"),
    dict(path="artifacts/numerics/n0/lead_4rung_replication.json",
         role="lead 4-rung replication addendum; supplies R5 uncertainty",
         cited_prefix="a1f04d2a3cb4d66f",
         cited_source="comms/outbox/deepseek-flash-14.jsonl w14-art-2026-09-12T00:15:24+0800-fcdispo"),
    # --- evidence_refs of the (now superseded) N0 node review ---------------------------------
    dict(path="numerics/results/flat_wave_convergence.json",
         role="N0 review evidence_ref: primary convergence report",
         cited_prefix=None, cited_source="reviews/N0-review-lead-audit.json evidence_refs (no hash)"),
    dict(path="numerics/results/flat_wave_replication.json",
         role="N0 review evidence_ref: replication report",
         cited_prefix=None, cited_source="reviews/N0-review-lead-audit.json evidence_refs (no hash)"),
    dict(path="numerics/results/w04_acceptance_worker20.json",
         role="N0 review evidence_ref: independent acceptance run",
         cited_prefix=None, cited_source="reviews/N0-review-lead-audit.json evidence_refs (no hash)"),
    dict(path="evaluation_rubric.yaml",
         role="N0 review evidence_ref: verifiers.numerics criterion",
         cited_prefix=None, cited_source="reviews/N0-review-lead-audit.json evidence_refs (line ref)"),
    # --- declared N0 artifact and gate/verdict anchors ----------------------------------------
    dict(path="numerics/tests/flat_wave.py",
         role="N0 declared artifact (map node N0)",
         cited_prefix="8b52014dac47f996",
         cited_source="research_map.json measured_hashes.N0 / map node N0"),
    dict(path="reviews/G-NUM-protocol-review.json",
         role="C8 independent protocol review verdict (accept 4.5)",
         cited_prefix="8137f18f1a3b",
         cited_source="map gate audit C8 / controller_gate_audit.G-NUM"),
    dict(path="reviews/N0-review-lead-audit.json",
         role="N0 node review carrying the open stop_rule",
         cited_prefix="e3c314f886be",
         cited_source="runtime/state/artifact_hashes.json registry (self-consistent check)"),
    dict(path="numerics/tests/n0_order_4rung.json",
         role="4-rung raw order evidence (stop-rule item 1)",
         cited_prefix="c88146a1375c",
         cited_source="comms/outbox/deepseek-flash-14.jsonl w14-art-2026-09-12T00:15:24+0800-fcdispo"),
    dict(path="numerics/protocol/three_scheme_r1r5_summary.json",
         role="three-scheme R1-R5 4-rung summary (stop-rule item 1)",
         cited_prefix="6e1ded36be6f",
         cited_source="comms/outbox/deepseek-flash-14.jsonl w14-art-20260912T003420-normrobust"),
]

# Named by the live stop-rule assignments but not yet on disk at audit time.
PENDING = [
    dict(path="numerics/results/flat_wave_convergence_rev3.json",
         role="astra-life04-n0-stoprule deliverable (lead-numerics; stop-rule items 1+2)"),
    dict(path="reviews/N0-review-final-verify.json",
         role="astra-life04-n0-verify deliverable (lead-audit; independent verdict)"),
]

N0_REVIEW_CREATED_AT = "2026-09-11T23:32:31+08:00"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def mtime_iso(p: Path) -> str:
    return datetime.fromtimestamp(p.stat().st_mtime, CST).isoformat(timespec="seconds")


def scan_roots_from_source(src: str):
    m = re.search(r"for d in \((.*?)\):", src, re.S)
    if not m:
        return [], None
    roots = re.findall(r'"([^"]+)"', m.group(1))
    return roots, (m.group(1).strip() if roots else None)


def under_roots(rel: str, roots) -> str | None:
    for r in roots:
        if rel == r or rel.startswith(r.rstrip("/") + "/"):
            return r
    return None


def classify(rel: str, roots, registry: dict) -> tuple[str, dict | None, str | None]:
    entry = registry.get(rel)
    root = under_roots(rel, roots)
    if entry is None:
        if root is None:
            return "not_registered_outside_scan_roots", None, None
        return "not_registered_inside_scan_roots", None, root
    return "registered_match", entry, root  # mismatch decided by caller


def main() -> int:
    reg_path = ROOT / "runtime" / "state" / "artifact_hashes.json"
    reg_raw = reg_path.read_bytes()
    reg_sha = sha256_bytes(reg_raw)
    reg = json.loads(reg_raw)
    registry = reg.get("registry", {}) or {}

    audit_src_path = ROOT / "research_map" / "audit_evidence.py"
    audit_src = audit_src_path.read_text()
    audit_sha = sha256_bytes(audit_src.encode())
    roots, roots_literal = scan_roots_from_source(audit_src)

    n0_review_at = datetime.fromisoformat(N0_REVIEW_CREATED_AT)

    anchors = []
    for a in ANCHORS:
        rel = a["path"]
        p = ROOT / rel
        rec = {
            "path": rel,
            "role": a["role"],
            "cited_prefix": a["cited_prefix"],
            "cited_prefix_source": a["cited_source"],
            "exists_on_disk": p.is_file(),
            "measured_sha256": None,
            "measured_bytes": None,
            "measured_mtime": None,
            "cited_prefix_match": None,
            "registry_status": None,
            "registry_sha256": None,
            "registry_sha256_match": None,
            "covering_scan_root": None,
            "classification": None,
        }
        if p.is_file():
            rec["measured_sha256"] = sha256_file(p)
            rec["measured_bytes"] = p.stat().st_size
            rec["measured_mtime"] = mtime_iso(p)
            if a["cited_prefix"]:
                rec["cited_prefix_match"] = rec["measured_sha256"].startswith(a["cited_prefix"])
            entry = registry.get(rel)
            if entry is None:
                root = under_roots(rel, roots)
                rec["covering_scan_root"] = root
                rec["classification"] = ("not_registered_outside_scan_roots" if root is None
                                         else "not_registered_inside_scan_roots")
            else:
                rec["registry_sha256"] = entry.get("sha256")
                rec["registry_sha256_match"] = entry.get("sha256") == rec["measured_sha256"]
                rec["covering_scan_root"] = under_roots(rel, roots)
                rec["classification"] = ("registered_match" if rec["registry_sha256_match"]
                                         else "registered_mismatch")
        else:
            rec["classification"] = "absent_on_disk"
        anchors.append(rec)

    # stale-citation check for the N0 review's own evidence_refs (files only, unpinned)
    n0_refs = [a for a in anchors
               if a["cited_prefix_source"].startswith("reviews/N0-review-lead-audit.json")]
    modified_after_review = [
        {"path": a["path"], "measured_mtime": a["measured_mtime"],
         "n0_review_created_at": N0_REVIEW_CREATED_AT}
        for a in n0_refs
        if a["measured_mtime"] and datetime.fromisoformat(a["measured_mtime"]) > n0_review_at
    ]

    pending = []
    for a in PENDING:
        rel = a["path"]
        p = ROOT / rel
        pending.append({
            "path": rel,
            "role": a["role"],
            "exists_on_disk": p.is_file(),
            "covering_scan_root": under_roots(rel, roots),
            "registry_consequence_if_written_now": (
                "would be auto-registered by audit_evidence.py"
                if under_roots(rel, roots) else
                "would NOT be auto-registered (outside all scan roots)"),
        })

    counts: dict[str, int] = {}
    for a in anchors:
        counts[a["classification"]] = counts.get(a["classification"], 0) + 1

    gaps = [{"path": a["path"], "role": a["role"], "classification": a["classification"],
             "measured_sha256": a["measured_sha256"], "covering_scan_root": a["covering_scan_root"]}
            for a in anchors
            if a["classification"] != "registered_match"]

    out = {
        "schema": "w14-n0-gnum-registry-coverage-audit/v1",
        "task": "W14-GNUM-REGAUDIT-01",
        "actor": "deepseek-flash-14",
        "class_id": "AF-WCC-SCALAR-SPH",
        "class_ids": ["AF-WCC-SCALAR-SPH"],
        "node_id": "N0",
        "gate": "G-NUM",
        "assignment_ref": "no inbox card; bounded class-bound task from the open N0 stop-rule queue "
                           "(astra-life04-n0-stoprule / astra-life04-n0-verify are lead-owned)",
        "purpose": "Post-pass-04 measurement of which hash-cited N0/G-NUM anchors PROTOCOL rule 2 can "
                   "see in runtime/state/artifact_hashes.json, and which are invisible because the "
                   "registry scan roots do not cover their directories.",
        "pinned_inputs": {
            "runtime/state/artifact_hashes.json": reg_sha,
            "research_map/audit_evidence.py": audit_sha,
            "registry_checked_at_field": reg.get("checked_at"),
            "registry_entry_count": len(registry),
        },
        "scan_roots": roots,
        "scan_roots_literal": roots_literal,
        "classification_counts": dict(sorted(counts.items())),
        "anchors": anchors,
        "gaps": gaps,
        "pending_stoprule_paths": pending,
        "n0_review_evidence_refs_modified_after_review": modified_after_review,
        "worker_reading": (
            "Point-in-time measurement only. REGISTERED vs NOT-REGISTERED is decided against the "
            "registry sha pinned above; a later controller checkpoint rewrites that file and this "
            "audit must then be re-run. Absence of a path from the registry is a coverage fact, not "
            "a verdict about the path's scientific content. The two C4-requested anchors that remain "
            "unregistered (protocol-of-record 1e6cdf04, lead 4-rung replication a1f04d2a) and the "
            "N0 review's numerics/results evidence_refs all live outside the current scan roots, so "
            "the gap is structural (scan scope), not a one-off omission. The pending stop-rule "
            "artifact numerics/results/flat_wave_convergence_rev3.json is also outside the scan "
            "roots and will not be auto-registered when written."
        ),
        "falsifier": (
            "Falsified if a rerun at the pinned registry sha and audit_evidence.py sha yields a "
            "different classification for any anchor, or any path classified "
            "outside_scan_roots is in fact under an extracted scan root, or a registry entry "
            "reported here as matching does not match the on-disk measurement."
        ),
        "does_not_claim": [
            "no G-NUM verdict and no gate self-pass; G-NUM adjudication is Astra's",
            "no N0 completion; numerics_lock stays LOCKED, N1 not started, numerics/spherical_solver absent",
            "no independent review; this worker may not review its own artifacts",
            "no physics/censorship claim; provenance measurement only",
            "no claim that registry membership is required for every evidence_ref; that reading is the controller's",
            "no edit to any other agent's artifact; all inputs were read read-only",
            "no controller registration write; registering hashes is controller-owned",
        ],
        "note": "This audit artifact itself lives under artifacts/, which is outside the scan roots "
                "and is therefore not in the registry it audits.",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)} sha256={sha256_file(OUT)}")
    print("counts:", json.dumps(dict(sorted(counts.items()))))
    for g in gaps:
        print(f"  GAP {g['classification']:<38} {g['path']}")
    for p in pending:
        print(f"  PENDING {p['path']} -> {p['registry_consequence_if_written_now']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
