#!/usr/bin/env python3
"""W038-F0-FREEZE-INTEGRITY-02 — do FROZEN.json's pins actually match the bytes on disk?

Why this exists
  `check_f0_independent.py` IND-06 binds only the two `logical_artifacts` entries
  (canonical F0 + supplement). FROZEN.json also carries a 43-entry `files` map that
  no check in the repo verifies end-to-end. Prior worker-038 traffic
  (w038-f0-conformance-moving-target-blocker-20260912T003250) recorded F0 moving
  under review; this check answers, at a single measured instant, whether the
  manifest the reviewers are asked to bind to is internally consistent with disk.

Scope
  Node F0, gate G-F0, classes AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;
  AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH. Reads only files under --root. No network,
  no clock-dependent verdict (mtimes are reported as provenance, not as a criterion).

Falsifier
  Any pinned file whose measured sha256 differs from the pin, any missing pinned
  file, or a mid-run move of FROZEN.json itself refutes the corresponding PASS;
  a substantiated mismatch flips the verdict to `revise`.

Exit 0 = all pins match and FROZEN.json was stable; 1 = at least one mismatch;
2 = FROZEN.json moved mid-run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

FROZEN = "artifacts/formulation/FROZEN.json"
F0 = "research_map/formulation_taxonomy.yaml"
SUPPLEMENT = "artifacts/formulation/formulation_taxonomy.yaml"
SCHEMAS = [
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
]
F0_CRITICAL = [F0, SUPPLEMENT] + SCHEMAS


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_ts(s):
    try:
        return datetime.fromisoformat(str(s))
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--json-out", required=True)
    ap.add_argument("--snapshot-dir", default=None,
                    help="if set, copy FROZEN.json bytes here so the verdict stays bound")
    args = ap.parse_args()
    root = Path(args.root).resolve()

    fp = root / FROZEN
    frozen_bytes_before = fp.read_bytes()
    frozen_sha_before = hashlib.sha256(frozen_bytes_before).hexdigest()
    frozen = json.loads(frozen_bytes_before.decode("utf-8"))
    frozen_at = parse_ts(frozen.get("frozen_at"))

    if args.snapshot_dir:
        sd = Path(args.snapshot_dir)
        sd.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(fp, sd / "FROZEN.snapshot.json")
        (sd / "FROZEN.snapshot.sha256").write_text(frozen_sha_before + "  " + FROZEN + "\n")
        for p in F0_CRITICAL:
            src = root / p
            if src.exists():
                dst = sd / p.replace("/", "__")
                shutil.copyfile(src, dst)

    def check_map(label, entries, path_key=None):
        # `files` is path -> meta; `logical_artifacts` is logical_id -> {path, sha256, ...}.
        rows, mism, missing, post = [], [], [], []
        for key, meta in entries.items():
            if path_key:
                path = (meta or {}).get(path_key)
                if not path:
                    missing.append({"key": key, "pinned": meta, "why": f"no {path_key!r} field"})
                    continue
            else:
                path = key
            want = meta.get("sha256") if isinstance(meta, dict) else meta
            p = root / path
            if not p.exists():
                missing.append({"path": path, "pinned": want})
                rows.append({"path": path, "status": "MISSING", "pinned": want, "measured": None})
                continue
            got = sha256_file(p)
            mtime = datetime.fromtimestamp(p.stat().st_mtime).astimezone()
            after = bool(frozen_at and mtime > frozen_at)
            row = {"path": path, "status": "MATCH" if got == want else "MISMATCH",
                   "pinned": want, "measured": got, "mtime": mtime.isoformat(),
                   "mtime_after_frozen_at": after}
            rows.append(row)
            if got != want:
                mism.append(row)
            if after:
                post.append(path)
        return {"label": label, "n": len(entries), "rows": rows,
                "mismatches": mism, "missing": missing, "modified_after_freeze": post}

    files_res = check_map("files", frozen.get("files") or {})
    logical_res = check_map("logical_artifacts", frozen.get("logical_artifacts") or {},
                            path_key="path")

    # F0-critical pins, measured directly (independent of the manifest's own claim).
    crit = []
    fmap = frozen.get("files") or {}
    lamap = frozen.get("logical_artifacts") or {}
    for p in F0_CRITICAL:
        measured = sha256_file(root / p)
        pinned = (fmap.get(p) or {}).get("sha256")
        crit.append({"path": p, "measured": measured, "pinned_in_files": pinned,
                     "match": pinned == measured})
    la_canon = (lamap.get("F0-declared-taxonomy") or {}).get("sha256")
    la_supp = (lamap.get("F0-class-contract-supplement") or {}).get("sha256")
    la_ok = (la_canon == sha256_file(root / F0)
             and la_supp == sha256_file(root / SUPPLEMENT)
             and (lamap.get("F0-declared-taxonomy") or {}).get("path") == F0
             and (lamap.get("F0-class-contract-supplement") or {}).get("path") == SUPPLEMENT)

    frozen_bytes_after = fp.read_bytes()
    frozen_sha_after = hashlib.sha256(frozen_bytes_after).hexdigest()
    stable = frozen_sha_before == frozen_sha_after

    all_ok = (not files_res["mismatches"] and not files_res["missing"]
              and not logical_res["mismatches"] and not logical_res["missing"]
              and all(c["match"] for c in crit) and la_ok)
    verdict = "accept" if (all_ok and stable) else "revise"

    report = {
        "artifact": "artifacts/worker-038/f0_conformance/freeze_integrity_check.py",
        "task": "W038-F0-FREEZE-INTEGRITY-02",
        "node_id": "F0",
        "gate": "G-F0",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN",
                      "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "measured_at": datetime.now().astimezone().isoformat(),
        "frozen_manifest": {
            "path": FROZEN,
            "sha256_before": frozen_sha_before,
            "sha256_after": frozen_sha_after,
            "stable_across_run": stable,
            "revision": frozen.get("revision"),
            "frozen_at": frozen.get("frozen_at"),
        },
        "files_map": files_res,
        "logical_artifacts_map": logical_res,
        "f0_critical_pins": crit,
        "logical_artifacts_pin_ok": la_ok,
        "summary": {
            "files_total": files_res["n"],
            "files_mismatch": len(files_res["mismatches"]),
            "files_missing": len(files_res["missing"]),
            "logical_total": logical_res["n"],
            "logical_mismatch": len(logical_res["mismatches"]),
            "f0_critical_match": sum(1 for c in crit if c["match"]),
            "f0_critical_total": len(crit),
            "pinned_files_modified_after_frozen_at": len(files_res["modified_after_freeze"]),
        },
        "verdict": verdict,
        "verdict_scope": ("freeze-integrity of the manifest pins at the measured FROZEN.json "
                          "revision; not a gate verdict, not a physics judgement, not a "
                          "node-completion claim"),
        "falsifier": ("any pinned file whose measured sha256 differs from the pin, any missing "
                      "pinned file, or a mid-run move of FROZEN.json refutes the corresponding "
                      "PASS; any substantiated mismatch flips this verdict to revise"),
    }
    Path(args.json_out).write_text(json.dumps(report, indent=2, sort_keys=False) + "\n")
    print(json.dumps(report["summary"], indent=1))
    print("verdict:", verdict, "| FROZEN", frozen_sha_before[:12], "->", frozen_sha_after[:12])
    if not stable:
        return 2
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
