#!/usr/bin/env python3
"""Independent audit of artifacts/formulation/FROZEN.json (worker-025, bounded task).

Why this exists
---------------
`artifacts/formulation/tools/verify_frozen.py` checks each manifest entry against
its own file on disk. It cannot detect the failure mode that mattered for CF-7:
a *declared pair* (canonical path vs authoring mirror) that is each internally
consistent but not byte-identical to each other. FROZEN.json's `path_policy`
asserts exactly that cross-tree byte-identity. This auditor tests the assertion,
not just the hashes.

Checks
------
  M  manifest-vs-disk: sha256 + byte length for every declared file.
  P  declared-pair byte identity: for every declared path under
     `artifacts/formulation/` that has a declared canonical counterpart
     (`schemas/<name>` or `research_map/<name>`), compare the bytes.
  S  stability: any M or P failure is re-measured after --settle-seconds so an
     in-flight writer is labelled IN_FLIGHT, not reported as a stable finding.

Exit codes
----------
  0  no failure
  1  stable manifest drift or missing declared file
  2  stable cross-tree divergence (policy violation) but manifest internally OK
  3  manifest unreadable / structurally invalid

Read-only: this script never writes outside its --out paths. It makes no gate
verdict and no node status. Findings are point-in-time and carry a falsifier.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

CST = timezone(timedelta(hours=8))
MANIFEST_DEFAULT = "artifacts/formulation/FROZEN.json"
AUTHORING_PREFIX = "artifacts/formulation/"
# canonical counterpart rule, tied to the manifest's own path_policy
CANONICAL_RULES = (
    ("schemas/", "schemas/"),          # artifacts/formulation/schemas/X -> schemas/X
    ("research_map/", "research_map/"),  # artifacts/formulation/X      -> research_map/X
)
POLICY_KEY = "path_policy"
POLICY_CLAIM = "byte-identical at publish time"


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def measure(root: str, rel: str) -> dict:
    p = os.path.join(root, rel)
    if not os.path.isfile(p):
        return {"path": rel, "exists": False, "sha256": None, "bytes": None}
    b = open(p, "rb").read()
    return {
        "path": rel,
        "exists": True,
        "sha256": hashlib.sha256(b).hexdigest(),
        "bytes": len(b),
        "mtime": datetime.fromtimestamp(os.path.getmtime(p), CST).isoformat(timespec="seconds"),
    }


def canonical_counterpart(rel: str, declared: set) -> str | None:
    """Return the declared canonical path for an authoring path, or None."""
    if not rel.startswith(AUTHORING_PREFIX):
        return None
    tail = rel[len(AUTHORING_PREFIX):]
    candidates = []
    for prefix, canon_prefix in CANONICAL_RULES:
        if tail.startswith(prefix):
            candidates.append(canon_prefix + tail[len(prefix):])
    # flat authoring file (e.g. formulation_taxonomy.yaml) -> research_map/<name>
    candidates.append("research_map/" + tail)
    for c in candidates:
        if c in declared:
            return c
    return None


def paired_paths(files: dict) -> list[tuple[str, str]]:
    declared = set(files)
    pairs = []
    for rel in sorted(declared):
        c = canonical_counterpart(rel, declared)
        if c and c != rel:
            pairs.append((c, rel))
    return pairs


def parse_policy(manifest: dict) -> dict:
    pol = manifest.get(POLICY_KEY)
    return {
        "present": bool(pol),
        "text": pol,
        "asserts_blanket_byte_identity": bool(pol) and POLICY_CLAIM in str(pol),
        # the policy sentence scopes mirroring to "the artifacts/formulation/ entries"
        "scoped_to_all_authoring_entries": bool(pol) and "artifacts/formulation/" in str(pol),
    }


def authoring_role(root: str, rel: str) -> str | None:
    """Best-effort read of an `artifact_role:` line (no YAML dependency)."""
    p = os.path.join(root, rel)
    if not os.path.isfile(p):
        return None
    try:
        for line in open(p, encoding="utf-8", errors="replace"):
            s = line.strip()
            if s.startswith("artifact_role:"):
                return s.split(":", 1)[1].strip().strip('"').strip("'")
    except OSError:
        return None
    return None


def snapshot(root: str, manifest: dict) -> dict:
    files = manifest["files"]
    rows = {}
    for rel, rec in files.items():
        m = measure(root, rel)
        m["declared_sha256"] = rec.get("sha256")
        m["declared_bytes"] = rec.get("bytes")
        m["hash_match"] = m["exists"] and m["sha256"] == rec.get("sha256")
        m["bytes_match"] = m["exists"] and m["bytes"] == rec.get("bytes")
        rows[rel] = m
    pair_rows = []
    for canon, author in paired_paths(files):
        a, b = rows[author], rows[canon]
        identical = bool(a["exists"] and b["exists"] and a["sha256"] == b["sha256"])
        pair_rows.append({
            "canonical": canon,
            "authoring": author,
            "identical": identical,
            "canonical_sha256": b["sha256"],
            "authoring_sha256": a["sha256"],
            "canonical_bytes": b["bytes"],
            "authoring_bytes": a["bytes"],
        })
    return {"measured_at": now(), "files": rows, "pairs": pair_rows}


def diff_snapshots(s1: dict, s2: dict, two_snapshot: bool) -> dict:
    """Classify each failing row/pair as STABLE, IN_FLIGHT or SINGLE_SNAPSHOT.

    A failure that is present on both measurements is STABLE; one that is clean
    on the second measurement was an in-flight write (IN_FLIGHT). With
    two_snapshot=False nothing is re-measured, so no failure is called stable.
    """
    out = {"drift": [], "missing": [], "divergent": [], "in_flight": []}

    def kind_of(still_bad: bool) -> str:
        if not two_snapshot:
            return "SINGLE_SNAPSHOT"
        return "STABLE" if still_bad else "IN_FLIGHT"

    for rel, r in s1["files"].items():
        if r["hash_match"] and r["bytes_match"]:
            continue
        r2 = s2["files"][rel]
        still_bad = (not r2["hash_match"]) or (not r2["bytes_match"])
        rec = {
            "path": rel, "kind": kind_of(still_bad),
            "declared_sha256": r["declared_sha256"], "declared_bytes": r["declared_bytes"],
            "first_sha256": r["sha256"], "second_sha256": r2["sha256"],
            "second_exists": r2["exists"],
        }
        if rec["kind"] == "IN_FLIGHT":
            out["in_flight"].append(rec)
        else:
            (out["missing"] if not r["exists"] else out["drift"]).append(rec)
    for p in s1["pairs"]:
        if p["identical"]:
            continue
        p2 = next(q for q in s2["pairs"]
                  if q["canonical"] == p["canonical"] and q["authoring"] == p["authoring"])
        rec = {
            "canonical": p["canonical"], "authoring": p["authoring"],
            "kind": kind_of(not p2["identical"]),
            "canonical_sha256": p["canonical_sha256"], "authoring_sha256": p["authoring_sha256"],
            "canonical_bytes": p["canonical_bytes"], "authoring_bytes": p["authoring_bytes"],
            "second_canonical_sha256": p2["canonical_sha256"],
            "second_authoring_sha256": p2["authoring_sha256"],
        }
        if rec["kind"] == "IN_FLIGHT":
            out["in_flight"].append(rec)
        else:
            out["divergent"].append(rec)
    # pairs/files that were clean first and are still clean are not listed; a
    # pair that *became* divergent on the second measurement is not a finding
    # here (the snapshot pair timing differs) and is reported as UNSTABLE_TARGET.
    for p in s2["pairs"]:
        if p["identical"]:
            continue
        if not any(q["canonical"] == p["canonical"] and q["authoring"] == p["authoring"]
                   for q in s1["pairs"] if not q["identical"]):
            out["in_flight"].append({
                "canonical": p["canonical"], "authoring": p["authoring"],
                "kind": "UNSTABLE_TARGET",
                "note": "clean at snapshot 1, divergent at snapshot 2; target is being written",
            })
    return out


def build_findings(manifest: dict, root: str, d: dict, two_snapshot: bool) -> list[dict]:
    findings = []
    stab = "STABLE" if two_snapshot else "SINGLE_SNAPSHOT"
    for i, m in enumerate(sorted(d["missing"], key=lambda x: x["path"]), 1):
        findings.append({
            "id": f"W025-M{i:02d}",
            "severity": "blocker",
            "check": "M",
            "stability": stab,
            "claim": f"FROZEN.json rev{manifest.get('revision')} declares a file that does not exist: {m['path']}",
            "measured": m,
            "falsifier": f"Create {m['path']} with sha256 {m['declared_sha256']}; the finding is falsified.",
        })
    for i, m in enumerate(sorted(d["drift"], key=lambda x: x["path"]), 1):
        findings.append({
            "id": f"W025-D{i:02d}",
            "severity": "blocker",
            "check": "M",
            "stability": stab,
            "claim": (f"FROZEN.json rev{manifest.get('revision')} pins {m['path']} at "
                      f"{str(m['declared_sha256'])[:16]} but the on-disk bytes hash "
                      f"{str(m['second_sha256'])[:16]} on this measurement."),
            "measured": m,
            "falsifier": (f"Re-measure {m['path']} at >=30s intervals and obtain "
                          f"{str(m['declared_sha256'])[:16]}, or re-freeze the manifest on the "
                          f"measured hash; the finding is falsified."),
        })
    for i, p in enumerate(sorted(d["divergent"], key=lambda x: x["canonical"]), 1):
        role = authoring_role(root, p["authoring"])
        policy = parse_policy(manifest)
        findings.append({
            "id": f"W025-P{i:02d}",
            "severity": "major",
            "check": "P",
            "stability": stab,
            "claim": (f"FROZEN.json rev{manifest.get('revision')} path_policy asserts that "
                      f"artifacts/formulation/ entries are byte-identical at publish time, but the "
                      f"measured pair ({p['canonical']} vs {p['authoring']}) is divergent "
                      f"({p['canonical_bytes']} vs {p['authoring_bytes']} bytes)."),
            "measured": p,
            "policy_asserts_blanket_byte_identity": policy["asserts_blanket_byte_identity"],
            "authoring_artifact_role": role,
            "authoring_role_conflicts_with_mirror_claim": bool(
                role and ("SUPPLEMENT" in role.upper() or "not be read as a competing" in role)),
            "falsifier": (f"Measure {p['canonical']} and {p['authoring']} at >=30s intervals and "
                          f"obtain equal sha256, or amend path_policy so the assertion is scoped to "
                          f"the pairs that are actually mirrors; the finding is falsified."),
            "remedy_options": [
                "amend path_policy to name the exact mirror pairs (schemas/*.yaml) and class the "
                "authoring taxonomy as a supplement with its own declared hash",
                "or publish the authoring taxonomy byte-identically to the canonical path",
            ],
        })
    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=os.environ.get("SWARM_ROOT", "."), help="swarm root")
    ap.add_argument("--manifest", default=MANIFEST_DEFAULT)
    ap.add_argument("--settle-seconds", type=float, default=30.0,
                    help="wait this long and re-measure before classifying failures "
                         "(default 30; use 0 for a single snapshot, which cannot certify stability)")
    ap.add_argument("--out", default=None, help="write JSON report here")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    root = os.path.abspath(args.root)
    manifest_path = os.path.join(root, args.manifest)
    try:
        raw = open(manifest_path, "rb").read()
        manifest = json.loads(raw)
        if not isinstance(manifest.get("files"), dict) or not manifest["files"]:
            raise ValueError("missing non-empty 'files' map")
    except (OSError, ValueError) as e:
        print(f"FATAL manifest unreadable/invalid: {manifest_path}: {e}", file=sys.stderr)
        return 3

    s1 = snapshot(root, manifest)
    s2 = s1
    if args.settle_seconds > 0 and (
            any(not r["hash_match"] or not r["bytes_match"] for r in s1["files"].values())
            or any(not p["identical"] for p in s1["pairs"])):
        time.sleep(args.settle_seconds)
        s2 = snapshot(root, manifest)

    d = diff_snapshots(s1, s2)
    findings = build_findings(manifest, root, d)
    stable_blocking = [f for f in findings if f["check"] == "M"]
    stable_policy = [f for f in findings if f["check"] == "P"]

    report = {
        "artifact": "FROZEN-AUDIT",
        "generated_by": "worker-025",
        "generated_at": now(),
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "node_ids": ["F0", "F1", "F2a", "F2b"],
        "gate": "G-FORM",
        "tool": {"path": "artifacts/worker-025/frozen_audit/audit_frozen.py",
                 "sha256": sha256_file(os.path.abspath(__file__))},
        "manifest": {
            "path": args.manifest,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
            "revision": manifest.get("revision"),
            "frozen_at": manifest.get("frozen_at"),
            "declared_files": len(manifest["files"]),
            "path_policy": parse_policy(manifest),
        },
        "settle_seconds": args.settle_seconds,
        "snapshot_1_at": s1["measured_at"],
        "snapshot_2_at": s2["measured_at"],
        "declared_pairs_checked": len(s1["pairs"]),
        "pairs": s2["pairs"],
        "manifest_vs_disk": {k: {kk: v[kk] for kk in
                                 ("exists", "sha256", "declared_sha256", "bytes",
                                  "declared_bytes", "hash_match", "bytes_match", "mtime")}
                             for k, v in s2["files"].items()},
        "findings": findings,
        "summary": {
            "manifest_drift_or_missing_stable": len(stable_blocking),
            "cross_tree_divergent_stable": len(stable_policy),
            "in_flight_resolved_on_second_measurement": (
                sum(1 for x in d["drift"] + d["missing"] if x["kind"] == "RESOLVED")
                + sum(1 for x in d["divergent"] if x["kind"] == "RESOLVED")),
            "verdict": ("clean" if not findings else
                        ("stable_policy_divergence" if not stable_blocking else "stable_manifest_drift")),
        },
        "not_claimed": [
            "no gate verdict (G-FORM stays with Astra); this is supporting evidence only",
            "no node status change; F0/F1/F2a/F2b stay as recorded by the controller",
            "no claim that the canonical revision is semantically correct; only byte/JSON facts",
            "point-in-time measurement: a later write invalidates this snapshot, re-run the tool",
        ],
    }

    if args.out:
        out = args.out if os.path.isabs(args.out) else os.path.join(root, args.out)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w") as f:
            json.dump(report, f, indent=2, sort_keys=True)
            f.write("\n")

    if not args.quiet:
        print(json.dumps(report["summary"], indent=2))
        for f in findings:
            print(f"  {f['severity'].upper():<8} {f['id']} [{f['check']}] {f['claim']}")
        if args.out:
            print(f"report: {args.out}")

    if stable_blocking:
        return 1
    if stable_policy:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
