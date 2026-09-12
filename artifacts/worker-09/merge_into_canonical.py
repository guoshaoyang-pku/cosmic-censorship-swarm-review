#!/usr/bin/env python3
"""Additively merge the worker-09 SCC citation-audit shard into ledger/citation_audit.csv.

Safety properties (the canonical file is owned by lead-literature and is written concurrently):
  1. additive only - existing rows are never modified or removed;
  2. idempotent - rows whose citation_id already exists are skipped;
  3. verify-before-replace - the canonical sha256 is re-read immediately before the atomic
     os.replace; if it changed since the merge was computed, the merge ABORTS and writes nothing;
  4. a timestamped backup of the pre-merge canonical is kept under
     artifacts/worker-09/merge_backups/.

Usage:
  python3 merge_into_canonical.py --dry-run   # report what would change
  python3 merge_into_canonical.py             # perform the merge
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import os
import shutil
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
W09 = ROOT / "artifacts" / "worker-09"
LEDGER = ROOT / "ledger"
CANON = LEDGER / "citation_audit.csv"
SHARD = LEDGER / "citation_audit_scc_flash-09.lead_schema.csv"
BACKUPS = W09 / "merge_backups"
CST = timezone(timedelta(hours=8))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_rows(path: Path):
    with path.open(newline="") as f:
        r = csv.DictReader(f)
        return list(r), r.fieldnames


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--update-existing", action="store_true",
                    help="also refresh rows already present whose reviewer is deepseek-flash-09")
    a = ap.parse_args()

    canon_rows, canon_fields = read_rows(CANON)
    shard_rows, shard_fields = read_rows(SHARD)
    missing = [c for c in canon_fields if c not in shard_fields]
    if missing:
        print(f"SCHEMA MISMATCH: shard lacks canonical columns {missing}\n"
              f"  canonical: {canon_fields}\n  shard    : {shard_fields}")
        return 2
    shard_rows = [{k: r.get(k, "") for k in canon_fields} for r in shard_rows]

    have = {r["citation_id"] for r in canon_rows}
    new = [r for r in shard_rows if r["citation_id"] not in have]
    dup = [r["citation_id"] for r in shard_rows if r["citation_id"] in have]
    shard_by_id = {r["citation_id"]: r for r in shard_rows}
    updated = []
    if a.update_existing:
        for i, r in enumerate(canon_rows):
            if r.get("reviewer") == "deepseek-flash-09" and r["citation_id"] in shard_by_id:
                if r != shard_by_id[r["citation_id"]]:
                    canon_rows[i] = shard_by_id[r["citation_id"]]
                    updated.append(r["citation_id"])
    print(f"canonical rows={len(canon_rows)} sha256={sha256(CANON)}")
    print(f"shard rows={len(shard_rows)} new={len(new)} already-present={len(dup)} updated={updated}")
    for r in new:
        print(f"  + {r['citation_id']:<8} {r['bibkey']:<28} {r['verdict']}")

    if a.dry_run:
        print("dry-run: nothing written")
        return 0
    if not new and not updated:
        print("nothing to merge")
        return 0

    pre_sha = sha256(CANON)
    BACKUPS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(CST).strftime("%Y%m%dT%H%M%S%z")
    backup = BACKUPS / f"citation_audit.{stamp}.csv"
    shutil.copy2(CANON, backup)

    tmp = CANON.with_suffix(".csv.w09tmp")
    with tmp.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=canon_fields)
        w.writeheader()
        for r in canon_rows + new:
            w.writerow(r)

    if sha256(CANON) != pre_sha:
        tmp.unlink(missing_ok=True)
        print("ABORT: canonical changed during merge; no write performed (shard preserved)")
        return 3
    os.replace(tmp, CANON)
    post_rows, _ = read_rows(CANON)
    print(f"merged: {len(canon_rows)} -> {len(post_rows)} rows; post sha256={sha256(CANON)}")
    print(f"backup: {backup}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
