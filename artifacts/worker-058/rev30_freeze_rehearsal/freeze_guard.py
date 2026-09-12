#!/usr/bin/env python3
"""freeze_guard.py -- freeze-identity and revision-monotonicity guard (candidate, read-only).

W058-REV30-FREEZE-REHEARSAL-01, worker-058.  Class binding AF-SCC-C0-VAC-GEN (F2b), gate
context G-FORM.  This module exists because FROZEN revision 29 was published at least twice
with different bytes under the same revision label (recorded by worker-005 / worker-040 /
worker-058; CF-27), which made every citation of the bare label "rev29" ambiguous and voided
predecessor-pin verdicts.  The canonical pipeline (`regenerate_frozen.py`, `verify_frozen.py`)
checks bytes-vs-manifest but never checks *identity across generations* or revision monotonicity.

A freeze identity is the tuple (revision, frozen_at, manifest_digest) where manifest_digest is
the sha256 of the canonical JSON encoding of {"revision", "frozen_at", "files"}.  Two
byte-distinct generations sharing a revision label are a hard identity collision.

Worker evidence only: no canonical path is read-write here; no gate verdict, node status or
validation_status is claimed.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

IDENTITY_KEYS = ("revision", "frozen_at", "files")


def manifest_digest(man: dict) -> str:
    """Digest over the identity-bearing fields only (paths, sha256, bytes, revision, stamp)."""
    payload = {k: man[k] for k in IDENTITY_KEYS if k in man}
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def identity(man: dict) -> dict:
    return {
        "revision": man.get("revision"),
        "frozen_at": man.get("frozen_at"),
        "n_files": len(man.get("files", {})),
        "manifest_digest": manifest_digest(man),
    }


def load_identity(path: Path) -> dict:
    return identity(json.loads(Path(path).read_text()))


def audit_history(records: list[dict]) -> dict:
    """Records are identity dicts.  Returns collisions and the observed revision multiset."""
    by_rev: dict = {}
    for r in records:
        by_rev.setdefault(str(r.get("revision")), set()).add(r.get("manifest_digest"))
    collisions = []
    for rev, digests in sorted(by_rev.items(), key=lambda kv: (len(kv[0]), kv[0])):
        if len(digests) > 1:
            collisions.append(
                {
                    "revision": rev,
                    "distinct_identities": sorted(digests),
                    "n_generations": len(digests),
                }
            )
    return {
        "records": records,
        "n_records": len(records),
        "revisions": {rev: len(d) for rev, d in sorted(by_rev.items())},
        "repeated_revision_distinct_identity": collisions,
        "history_unique": not collisions,
    }


def guard_new_revision(records: list[dict], new: dict) -> dict:
    """Refuse a re-freeze that repeats a revision label or moves backwards.

    Returns {"accept": bool, "violations": [...]}.  Callers must not write the manifest when
    accept is false.
    """
    violations = []
    existing_revs = []
    for r in records:
        try:
            existing_revs.append(int(r.get("revision")))
        except (TypeError, ValueError):
            continue
    if existing_revs:
        top = max(existing_revs)
        if new.get("revision") is not None and int(new["revision"]) <= top:
            violations.append(
                {
                    "guard": "G1_revision_not_increasing",
                    "detail": f"new revision {new.get('revision')} <= current max {top}",
                }
            )
    same = [r for r in records if str(r.get("revision")) == str(new.get("revision"))]
    for r in same:
        if r.get("manifest_digest") != new.get("manifest_digest"):
            violations.append(
                {
                    "guard": "G2_repeated_revision_distinct_identity",
                    "detail": (
                        f"revision {new.get('revision')} already recorded with a different "
                        f"manifest digest"
                    ),
                    "existing_manifest_digest": r.get("manifest_digest"),
                    "new_manifest_digest": new.get("manifest_digest"),
                }
            )
    return {"accept": not violations, "violations": violations, "new_identity": new}


def verify_tree(man: dict, root: Path) -> dict:
    """Byte check of a manifest against a tree (mirrors verify_frozen.py, non-exiting)."""
    problems = []
    for rel, rec in sorted(man.get("files", {}).items()):
        f = Path(root) / rel
        if not f.is_file():
            problems.append({"path": rel, "problem": "MISSING"})
            continue
        h = hashlib.sha256(f.read_bytes()).hexdigest()
        if h != rec.get("sha256"):
            problems.append(
                {
                    "path": rel,
                    "problem": "DRIFT",
                    "manifest": rec.get("sha256"),
                    "disk": h,
                }
            )
    return {"n_files": len(man.get("files", {})), "problems": problems, "clean": not problems}
