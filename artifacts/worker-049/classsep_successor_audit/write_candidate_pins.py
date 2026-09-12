#!/usr/bin/env python3
"""Write candidates_pinned.json for W049-CLASSSEP-SUCCESSOR-AUDIT-02.

Discovery is explicit: fixed panel paths plus a glob of worker-098's candidate
modules. Each candidate is recorded with its measured sha256 at pin time. The
audit runner reads this file, imports by path and verifies the hashes before and
after the run (drift -> verdicts VOID, results still written).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]

FIXED = [
    ("recovered_c266", "artifacts/worker-049/classsep_fn_audit/pinned/class_separation_c266_recovered.py",
     "pre-change canonical baseline (expected FAIL)"),
    ("live_canonical", "research_map/class_separation.py",
     "live detector at a8c04fc31e4a; already measured LIVE_GUARD_INTRODUCES_FN"),
    ("staged_prosefix_worker049", "artifacts/worker-049/classsep_prose_fix/class_separation_prosefix.py",
     "worker-049 staged calibration; author-conflicted control"),
    ("staged_cand_worker16", "proposed/class_separation.py",
     "worker-16 staged candidate (negated-split + PROSE_KEYS)"),
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    panel = []
    for cid, rel, role in FIXED:
        p = REPO / rel
        panel.append({"id": cid, "path": rel, "sha256": sha(p), "role": role,
                      "decl_parity_gated": cid in ("w098_v1", "w098_v2", "w098_v3")})
    w098 = sorted((REPO / "artifacts/worker-098/classsep_mention_scope").glob("candidate_class_separation*.py"))
    for p in w098:
        stem = p.stem
        suffix = stem.replace("candidate_class_separation", "").lstrip(".").lstrip("v")
        cid = f"w098_v{suffix}" if suffix else "w098_v1"
        panel.append({
            "id": cid,
            "path": p.relative_to(REPO).as_posix(),
            "sha256": sha(p),
            "role": f"worker-098 mention-scope candidate {stem}",
            "decl_parity_gated": True,
        })
    out = {
        "schema": "worker-049/classsep-successor-audit-candidates/v1",
        "task_id": "W049-CLASSSEP-SUCCESSOR-AUDIT-02",
        "actor": "worker-049",
        "panel": panel,
        "discovery": "fixed panel + glob artifacts/worker-098/classsep_mention_scope/candidate_class_separation*.py",
        "note": "hashes measured at pin time; the audit runner verifies each before import and re-verifies at end of run",
    }
    dst = HERE / "candidates_pinned.json"
    dst.write_text(json.dumps(out, indent=1) + "\n")
    print(f"wrote {dst.relative_to(REPO)} sha256={sha(dst)}")
    for c in panel:
        print(f"  {c['id']:28s} {c['sha256'][:12]} {c['path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
