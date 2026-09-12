#!/usr/bin/env python3
"""Independent G-FORM rev29 pin census (worker-099, bounded execution task).

Why this exists
---------------
The G-FORM r3 reviewers (`astra-life05-verify-gform-r3`) are required to pin the FROZEN
bytes *plus each per-file pin*, and CF-27 recorded a same-revision move of
`artifacts/formulation/FROZEN.json` inside the r3 window.  This script is an independent,
stdlib-only re-measurement of every pin declared by FROZEN rev29 at two instants separated
by a short quiescent gap, plus a class-id -> schema binding census over the frozen
formulation artifacts.  It separates two questions that are easy to conflate:

  1. pin fidelity   -- does each on-disk file match the sha256/bytes declared in FROZEN?
  2. quiescence     -- are the canonical bytes (and mtimes) untouched across the gap?

It deliberately does NOT import or invoke the formulation author's `verify_frozen.py`;
all hashing is redone from bytes here.  It writes nothing outside its own artifact dir and
never touches `research_map/class_separation.py` or any formulation artifact.

Output: pin_census.json in the same directory as this script.

Reproduce:  python3 artifacts/worker-099/frozen_r3_pin_census/run_pin_census.py
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

FROZEN_REL = "artifacts/formulation/FROZEN.json"
# FROZEN self-hash cited by the controller in ASTRA_HANDOFF pass-06 / CF-27 for rev29.
FROZEN_EXTERNAL_REFERENCE = "815e08079aefbc"
TAXONOMY_EXPECTED = {
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a961",
    "artifacts/formulation/formulation_taxonomy.yaml": "d7419b4e8963",
}
CLASS_IDS = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]
SCHEMA_FILES = [
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
    "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
]
DUAL_MIRROR_PAIRS = [
    ("schemas/af_wcc_vacuum.yaml", "artifacts/formulation/schemas/af_wcc_vacuum.yaml"),
    ("schemas/af_scc_c2_vacuum.yaml", "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"),
    ("schemas/af_scc_c0_vacuum.yaml", "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"),
]
QUIESCENT_GAP_S = 15
OBSERVED_INSTRUMENTS = [
    "research_map/class_separation.py",
    "proposed/class_separation.py",
    "artifacts/worker-049/classsep_fn_audit/pinned/class_separation_c266_recovered.py",
]


def sha256_bytes(path: str) -> tuple[str | None, int | None]:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
    except OSError:
        return None, None
    return h.hexdigest(), os.path.getsize(path)


def stat_ns(path: str) -> int | None:
    try:
        return os.stat(path).st_mtime_ns
    except OSError:
        return None


def iso_ns(ns: int | None) -> str | None:
    if ns is None:
        return None
    return _dt.datetime.fromtimestamp(ns / 1e9).astimezone().isoformat(timespec="milliseconds")


def measure(paths: list[str]) -> dict:
    out = {}
    for rel in paths:
        p = os.path.join(ROOT, rel)
        digest, nbytes = sha256_bytes(p)
        out[rel] = {
            "sha256": digest,
            "bytes": nbytes,
            "mtime_ns": stat_ns(p),
            "exists": digest is not None,
        }
    return out


def now() -> str:
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


def class_binding() -> dict:
    binding = {}
    for cid in CLASS_IDS:
        hits = {}
        for rel in SCHEMA_FILES + [
            "artifacts/formulation/formulation_taxonomy.yaml",
            "research_map/formulation_taxonomy.yaml",
            "artifacts/formulation/KEY_MANIFEST.json",
            "artifacts/formulation/VARIANT_REGISTRY.json",
        ]:
            p = os.path.join(ROOT, rel)
            try:
                text = open(p, encoding="utf-8", errors="replace").read()
            except OSError:
                hits[rel] = None
                continue
            n = text.count(cid)
            if n:
                hits[rel] = n
        binding[cid] = hits
    # schema-local C0/C2 co-mention check (ASTRA_HANDOFF hard rule: never "C0 or C2")
    co_mention = {}
    for rel in SCHEMA_FILES:
        p = os.path.join(ROOT, rel)
        try:
            text = open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            co_mention[rel] = None
            continue
        literal_lines = []
        for lineno, line in enumerate(text.splitlines(), 1):
            if re.search(r"C0\s+or\s+C2|C2\s+or\s+C0", line):
                literal_lines.append({"line": lineno, "text": line.strip()[:300]})
        co_mention[rel] = {
            "mentions_C0_class_id": text.count("AF-SCC-C0-VAC-GEN"),
            "mentions_C2_class_id": text.count("AF-SCC-C2-VAC-GEN"),
            "literal_C0_or_C2": len(literal_lines),
            "literal_C0_or_C2_lines": literal_lines,
        }
    return {"by_class": binding, "schema_co_mention": co_mention}


def main() -> int:
    frozen_path = os.path.join(ROOT, FROZEN_REL)
    frozen_sha, frozen_bytes = sha256_bytes(frozen_path)
    frozen = json.load(open(frozen_path, encoding="utf-8"))
    declared = frozen.get("files", {})
    listed = sorted(declared)

    t0 = now()
    first = measure(listed)
    time.sleep(QUIESCENT_GAP_S)
    t1 = now()
    second = measure(listed)
    frozen_sha_2, frozen_bytes_2 = sha256_bytes(frozen_path)

    rows = []
    pin_drift, byte_drift, mtime_moved = [], [], []
    for rel in listed:
        a, b = first[rel], second[rel]
        d = declared[rel]
        row = {
            "path": rel,
            "declared_sha256": d.get("sha256"),
            "declared_bytes": d.get("bytes"),
            "measured_sha256_first": a["sha256"],
            "measured_sha256_second": b["sha256"],
            "measured_bytes": a["bytes"],
            "sha_match_declared": a["sha256"] == d.get("sha256"),
            "bytes_match_declared": a["bytes"] == d.get("bytes"),
            "bytes_stable_across_gap": a["sha256"] == b["sha256"],
            "mtime_stable_across_gap": a["mtime_ns"] == b["mtime_ns"],
            "mtime_first": iso_ns(a["mtime_ns"]),
            "mtime_second": iso_ns(b["mtime_ns"]),
        }
        rows.append(row)
        if not (row["sha_match_declared"] and row["bytes_match_declared"]):
            pin_drift.append(rel)
        if not row["bytes_stable_across_gap"]:
            byte_drift.append(rel)
        if not row["mtime_stable_across_gap"]:
            mtime_moved.append(rel)

    dual = {}
    for left, right in DUAL_MIRROR_PAIRS:
        dual[f"{left} == {right}"] = (
            first[left]["sha256"] is not None and first[left]["sha256"] == first[right]["sha256"]
        )

    taxonomy = {}
    for rel, expect in TAXONOMY_EXPECTED.items():
        digest, nbytes = sha256_bytes(os.path.join(ROOT, rel))
        taxonomy[rel] = {
            "measured_sha256": digest,
            "measured_bytes": nbytes,
            "expected_prefix": expect,
            "matches_expected_prefix": bool(digest and digest.startswith(expect)),
        }

    instruments = {}
    for rel in OBSERVED_INSTRUMENTS:
        digest, nbytes = sha256_bytes(os.path.join(ROOT, rel))
        instruments[rel] = {"sha256": digest, "bytes": nbytes, "mtime": iso_ns(stat_ns(os.path.join(ROOT, rel)))}

    binding = class_binding()

    pin_verdict = "PASS" if (
        not pin_drift
        and not byte_drift
        and all(dual.values())
        and all(v["matches_expected_prefix"] for v in taxonomy.values())
        and frozen_sha == frozen_sha_2
        and frozen_sha is not None
        and frozen_sha.startswith(FROZEN_EXTERNAL_REFERENCE)
    ) else "DRIFT"
    quiescence_verdict = "QUIESCENT" if not mtime_moved else "WRITER_ACTIVE"

    artifact = {
        "artifact": "G-FORM rev29 independent pin census",
        "artifact_id": "worker-099/frozen_r3_pin_census",
        "worker": "worker-099",
        "created_at": t1,
        "node_id": "F1/F2",
        "gate": "G-FORM",
        "class_ids": CLASS_IDS,
        "scope": (
            "hash/pin fidelity and byte/mtime quiescence census only; no schema-content "
            "judgement, no gate verdict"
        ),
        "frozen_manifest": {
            "path": FROZEN_REL,
            "declared_revision": frozen.get("revision"),
            "declared_frozen_at": frozen.get("frozen_at"),
            "measured_sha256_first": frozen_sha,
            "measured_sha256_second": frozen_sha_2,
            "measured_bytes": frozen_bytes,
            "external_reference_prefix": FROZEN_EXTERNAL_REFERENCE,
        },
        "instants": {
            "first": t0,
            "second": t1,
            "quiescent_gap_seconds": QUIESCENT_GAP_S,
        },
        "per_file": rows,
        "summary": {
            "n_files": len(rows),
            "n_sha_match_declared": sum(1 for r in rows if r["sha_match_declared"]),
            "n_bytes_match_declared": sum(1 for r in rows if r["bytes_match_declared"]),
            "n_bytes_stable_across_gap": sum(1 for r in rows if r["bytes_stable_across_gap"]),
            "n_mtime_stable_across_gap": sum(1 for r in rows if r["mtime_stable_across_gap"]),
            "pin_drift_list": pin_drift,
            "byte_drift_list": byte_drift,
            "mtime_moved_list": mtime_moved,
        },
        "dual_mirrors": dual,
        "taxonomy": taxonomy,
        "class_binding": binding,
        "detector_hashes_observed_secondary": instruments,
        "pin_verdict": pin_verdict,
        "quiescence_verdict": quiescence_verdict,
        "interpretation": (
            "pin_verdict=PASS means every one of the 50 files listed in FROZEN rev29 matched its "
            "declared sha256 and byte count at both instants, the FROZEN self-hash matched the "
            "controller-cited 815e08079aefbc prefix, both schema mirrors were byte-equal, and both "
            "taxonomy hashes matched their declared prefixes. quiescence_verdict=WRITER_ACTIVE means "
            "at least one pinned file's mtime advanced inside the gap even though its bytes stayed "
            "identical; that is writer activity inside the r3 window, not a pin violation, and it is "
            "why reviewers must bind sha256 rather than path or mtime."
        ),
        "falsifier": (
            "Re-running run_pin_census.py against the same FROZEN rev29 declarations returns a "
            "measured sha256 or byte count that differs from a declaration, a FROZEN self-hash that "
            "no longer starts with 815e08079aefbc, a broken dual mirror, a taxonomy hash that no "
            "longer starts with its declared prefix, or a pinned file whose bytes change across the "
            "gap; any of those voids this census."
        ),
        "reproduce": "python3 artifacts/worker-099/frozen_r3_pin_census/run_pin_census.py",
    }

    out_path = os.path.join(HERE, "pin_census.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(artifact, fh, indent=1, sort_keys=True)
    digest, nbytes = sha256_bytes(out_path)
    with open(out_path + ".sha256", "w", encoding="utf-8") as fh:
        fh.write(f"{digest}  pin_census.json\n")
    print(json.dumps({
        "pin_verdict": pin_verdict,
        "quiescence_verdict": quiescence_verdict,
        "n_files": len(rows),
        "pin_drift_list": pin_drift,
        "byte_drift_list": byte_drift,
        "mtime_moved_list": mtime_moved,
        "frozen_sha256": frozen_sha,
        "taxonomy_ok": all(v["matches_expected_prefix"] for v in taxonomy.values()),
        "dual_mirrors_ok": all(dual.values()),
        "artifact_sha256": digest,
        "artifact_bytes": nbytes,
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
