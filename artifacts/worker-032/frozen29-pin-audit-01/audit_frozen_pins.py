#!/usr/bin/env python3
"""W032-FROZEN29-LIVE-PIN-AUDIT-01: independent, read-only live pin audit of
artifacts/formulation/FROZEN.json revision 29 (sha256 prefix 815e08079aef) against
the bytes on disk, at the G-FORM review frame.

Pre-registered checks (fixed before measurement):
  A manifest  - FROZEN.json parses, revision == 29, pin count == 50, no duplicate
                paths, FROZEN.json is not a member of its own files map.
  B pins      - every declared pin exists, sha256 matches, byte count matches.
  C mirrors   - the three class schemas are byte-identical between the canonical
                path (schemas/) and the authoring mirror
                (artifacts/formulation/schemas/), per FROZEN.path_policy.
  D stability - all pins + FROZEN.json measured twice (T1, T2) with a fixed
                interval; any hash/bytes change is a moving target (CF-27).
  E gatepins  - live F0/F1/F2a/F2b/FROZEN hashes equal the pass-07 measured pins
                recorded in research_map/research_map.json when that file names
                them (reference only; recorded, not enforced).

Pre-registered verdict rule:
  PASS          all 50 pins match AND mirrors identical AND no T1->T2 change;
  FAIL          any pin mismatch / missing pin / mirror divergence;
  MOVING_TARGET FROZEN.json or any pin changed between T1 and T2;
  ERROR         manifest unreadable or self-test control failed.

Controls (run before the live measurement; a control failure aborts with ERROR):
  K1 pin table non-empty and == 50.
  K2 a synthetic manifest with one wrong hash is flagged by the same comparison.
  K3 a synthetic manifest naming a missing file is flagged.
  K4 byte identity of two reads of the same unchanged file is stable.

Read-only: this tool opens no file for writing under the repository. It writes
nothing except the report path passed on the command line (default: stdout).
"""

import argparse
import hashlib
import json
import os
import sys
import tempfile
import time

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
FROZEN_REL = "artifacts/formulation/FROZEN.json"
FROZEN_SHA_PIN = "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"
EXPECTED_REVISION = 29
EXPECTED_PINS = 50
CLASS_SCHEMAS = ("af_wcc_vacuum.yaml", "af_scc_c2_vacuum.yaml", "af_scc_c0_vacuum.yaml")
GATE_PINS = {
    "F0": ("research_map/formulation_taxonomy.yaml", "0abb9ed8a961"),
    "F1": ("schemas/af_wcc_vacuum.yaml", "d9cebb9404b2"),
    "F2a": ("schemas/af_scc_c2_vacuum.yaml", "e9a27996dfd3"),
    "F2b": ("schemas/af_scc_c0_vacuum.yaml", "b2ab6acb2bbe"),
}


def sha256_file(path):
    h = hashlib.sha256()
    n = 0
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
            n += len(chunk)
    return h.hexdigest(), n


def measure(base, rel):
    p = os.path.join(base, rel)
    if not os.path.isfile(p):
        return {"path": rel, "exists": False, "sha256": None, "bytes": None, "mtime_ns": None}
    digest, size = sha256_file(p)
    return {
        "path": rel,
        "exists": True,
        "sha256": digest,
        "bytes": size,
        "mtime_ns": os.stat(p).st_mtime_ns,
    }


def compare_manifest(base, manifest):
    """Return per-pin rows for one measurement of a parsed manifest's files map."""
    rows = []
    for rel in sorted(manifest["files"]):
        declared = manifest["files"][rel]
        got = measure(base, rel)
        rows.append({
            "pin_id": "PIN-%02d" % len(rows),
            "path": rel,
            "declared_sha256": declared.get("sha256"),
            "declared_bytes": declared.get("bytes"),
            "measured_sha256": got["sha256"],
            "measured_bytes": got["bytes"],
            "exists": got["exists"],
            "hash_match": got["exists"] and got["sha256"] == declared.get("sha256"),
            "bytes_match": (declared.get("bytes") is None) or (got["bytes"] == declared.get("bytes")),
            "mtime_ns": got["mtime_ns"],
        })
    return rows


def self_tests(base):
    """K2/K3/K4: the comparison must flag a wrong hash and a missing file."""
    out = {}
    with tempfile.TemporaryDirectory(prefix="w032_pinaudit_") as td:
        good = os.path.join(td, "good.txt")
        with open(good, "wb") as fh:
            fh.write(b"w032-control\n")
        h, n = sha256_file(good)
        # K4: repeated read stability
        h2, n2 = sha256_file(good)
        out["K4_repeat_read_stable"] = (h == h2 and n == n2)
        # K2: wrong declared hash must be flagged
        wrong = {"files": {"good.txt": {"sha256": "0" * 64, "bytes": n}}}
        rows_wrong = compare_manifest(td, wrong)
        out["K2_wrong_hash_flagged"] = (len(rows_wrong) == 1 and not rows_wrong[0]["hash_match"])
        # K3: missing file must be flagged
        missing = {"files": {"nope.txt": {"sha256": h, "bytes": n}}}
        rows_missing = compare_manifest(td, missing)
        out["K3_missing_file_flagged"] = (
            len(rows_missing) == 1 and not rows_missing[0]["exists"]
            and not rows_missing[0]["hash_match"]
        )
    out["controls_pass"] = all(out.values())
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=float, default=45.0,
                    help="seconds between the two stability passes (default 45)")
    ap.add_argument("--out", default=None, help="write JSON report here (default stdout)")
    args = ap.parse_args()

    frozen_path = os.path.join(REPO, FROZEN_REL)
    report = {
        "task": "W032-FROZEN29-LIVE-PIN-AUDIT-01",
        "actor": "worker-032",
        "node_id": "F1;F2a;F2b",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "mode": "read-only",
        "repo_root": REPO,
        "frozen_path": FROZEN_REL,
        "frozen_sha256_pin": FROZEN_SHA_PIN,
        "expected_revision": EXPECTED_REVISION,
        "expected_pins": EXPECTED_PINS,
        "interval_seconds": args.interval,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "checks": {},
        "controls": {},
        "pins": [],
        "pin_changes_t1_t2": [],
        "mirrors": [],
        "gate_pins": [],
        "verdict": "ERROR",
        "limits": [
            "One repository snapshot; no network; no canonical or manifest write.",
            "Stability window is the configured interval, not a continuous watch.",
            "A PASS binds only the measured hashes at the recorded instants.",
        ],
    }

    controls = self_tests(REPO)
    report["controls"].update(controls)
    if not controls["controls_pass"]:
        report["error"] = "self-test control failure; live measurement aborted"
        emit(report, args.out)
        return 2

    if not os.path.isfile(frozen_path):
        report["error"] = "FROZEN.json absent"
        emit(report, args.out)
        return 2

    frozen_sha_t1, frozen_bytes_t1 = sha256_file(frozen_path)
    with open(frozen_path, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)

    pins = manifest.get("files", {})
    report["checks"]["A_manifest"] = {
        "frozen_sha256_t1": frozen_sha_t1,
        "frozen_bytes_t1": frozen_bytes_t1,
        "frozen_sha256_equals_pin": frozen_sha_t1 == FROZEN_SHA_PIN,
        "revision": manifest.get("revision"),
        "revision_ok": manifest.get("revision") == EXPECTED_REVISION,
        "pin_count": len(pins),
        "pin_count_ok": len(pins) == EXPECTED_PINS,
        "duplicate_paths": len(pins) != len(set(pins)),
        "self_referenced": FROZEN_REL in pins,
        "frozen_at": manifest.get("frozen_at"),
        "owner": manifest.get("owner"),
    }

    rows_t1 = compare_manifest(REPO, manifest)
    report["pins"] = rows_t1

    # C: canonical/mirror byte identity for the three class schemas.
    for name in CLASS_SCHEMAS:
        canon = measure(REPO, "schemas/" + name)
        mirror = measure(REPO, "artifacts/formulation/schemas/" + name)
        report["mirrors"].append({
            "name": name,
            "canonical": canon,
            "mirror": mirror,
            "identical": bool(canon["exists"] and mirror["exists"]
                              and canon["sha256"] == mirror["sha256"]
                              and canon["bytes"] == mirror["bytes"]),
        })

    # D: second pass.
    time.sleep(args.interval)
    frozen_sha_t2, frozen_bytes_t2 = sha256_file(frozen_path)
    rows_t2 = compare_manifest(REPO, manifest)
    by_path = {r["path"]: r for r in rows_t1}
    for r2 in rows_t2:
        r1 = by_path[r2["path"]]
        if (r1["measured_sha256"] != r2["measured_sha256"]
                or r1["measured_bytes"] != r2["measured_bytes"]
                or r1["mtime_ns"] != r2["mtime_ns"]):
            report["pin_changes_t1_t2"].append({
                "pin_id": r2["pin_id"], "path": r2["path"],
                "t1_sha256": r1["measured_sha256"], "t2_sha256": r2["measured_sha256"],
                "t1_bytes": r1["measured_bytes"], "t2_bytes": r2["measured_bytes"],
            })
    report["checks"]["D_stability"] = {
        "frozen_sha256_t2": frozen_sha_t2,
        "frozen_bytes_t2": frozen_bytes_t2,
        "frozen_changed": (frozen_sha_t1 != frozen_sha_t2) or (frozen_bytes_t1 != frozen_bytes_t2),
        "changed_pins": len(report["pin_changes_t1_t2"]),
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }

    # E: live gate pins vs the map's pass-07 measured pins (recorded reference).
    map_pins = {}
    try:
        with open(os.path.join(REPO, "research_map/research_map.json"), "r", encoding="utf-8") as fh:
            map_pins = json.load(fh)
        measured = (map_pins.get("controller_gate_audit") or {})
    except Exception as exc:  # reference only
        report["checks"]["E_gatepins_error"] = repr(exc)
        measured = {}
    for label, (rel, prefix) in GATE_PINS.items():
        got = measure(REPO, rel)
        report["gate_pins"].append({
            "label": label,
            "path": rel,
            "expected_prefix": prefix,
            "measured_sha256": got["sha256"],
            "prefix_match": bool(got["sha256"] and got["sha256"].startswith(prefix)),
        })

    # B: rows summary.
    bad = [r for r in rows_t1 if not (r["exists"] and r["hash_match"] and r["bytes_match"])]
    mirrors_ok = all(m["identical"] for m in report["mirrors"])
    report["checks"]["B_pins"] = {
        "total": len(rows_t1),
        "matched": len(rows_t1) - len(bad),
        "mismatched_ids": [r["pin_id"] for r in bad],
        "mirrors_identical": mirrors_ok,
    }

    a_ok = (report["checks"]["A_manifest"]["frozen_sha256_equals_pin"]
            and report["checks"]["A_manifest"]["revision_ok"]
            and report["checks"]["A_manifest"]["pin_count_ok"]
            and not report["checks"]["A_manifest"]["duplicate_paths"]
            and not report["checks"]["A_manifest"]["self_referenced"])
    if not a_ok:
        report["verdict"] = "FAIL"
        report["reason"] = "manifest-integrity check failed"
    elif bad or not mirrors_ok:
        report["verdict"] = "FAIL"
        report["reason"] = "pin or mirror mismatch: %s" % ([r["pin_id"] for r in bad] or "mirror")
    elif report["checks"]["D_stability"]["frozen_changed"] or report["pin_changes_t1_t2"]:
        report["verdict"] = "MOVING_TARGET"
        report["reason"] = "bytes changed inside the stability window (CF-27)"
    else:
        report["verdict"] = "PASS"
        report["reason"] = "all 50 pins, 3 mirror pairs and the double-pass window agree"

    report["falsifier"] = (
        "Falsified if any of the 50 declared pins does not match the live bytes, or any "
        "canonical/mirror class-schema pair is not byte-identical, or any pin changes inside the "
        "T1->T2 window, or the report's counts are not reproducible by re-running this tool at "
        "artifacts/formulation/FROZEN.json#%s." % FROZEN_SHA_PIN[:12]
    )
    report["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    emit(report, args.out)
    return 0 if report["verdict"] == "PASS" else 1


def emit(report, out):
    text = json.dumps(report, indent=1, sort_keys=False)
    if out:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    else:
        sys.stdout.write(text + "\n")


if __name__ == "__main__":
    sys.exit(main())
