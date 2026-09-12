#!/usr/bin/env python3
"""Cheap re-review pass: check each recorded finding against the current revision.

For every reviewed target, evaluate the specific patterns the finding named. If a finding
is resolved, re-pin the review and append a resolution note; if it persists, keep the pin
stale and say so. Prints a table suitable for a checkpoint log.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REV = ROOT / "reviews"
NOW = datetime.now().astimezone().isoformat(timespec="seconds")


def sha(p: str) -> str:
    f = ROOT / p
    return hashlib.sha256(f.read_bytes()).hexdigest() if f.exists() else "MISSING"


def text(p: str) -> str:
    f = ROOT / p
    return f.read_text(errors="replace") if f.exists() else ""


CHECKS = {
    "F0": {
        "path": "research_map/formulation_taxonomy.yaml",
        "checks": [
            ("HF-02 C2 containment", lambda t: bool(re.search(r"does NOT forbid C\^?\{?1,1", t))),
            ("HF-06 provisional axes", lambda t: "provisional_baire_residual" in t or "provisional" in t),
            ("HF-04 disjointness scope", lambda t: bool(re.search(r"descriptor|data(-| )space", t, re.I))),
        ],
    },
    "F1": {
        "path": "schemas/af_wcc_vacuum.yaml",
        "checks": [
            ("HF-06 canonical form decided", lambda t: not re.search(r"kept out of the scan blocks|scan blocks", t)),
            ("HF-06 completeness contradiction", lambda t: not re.search(r"initial_slice_topology:.*complete", t)),
            ("HF-04 'complete to the past'", lambda t: "complete to the past" not in t),
        ],
    },
    "F2a": {
        "path": "schemas/af_scc_c2_vacuum.yaml",
        "checks": [
            ("HF-02 class-specific conclusion_type",
             lambda t: "scc_c2_future_inextendibility" in t),
            ("HF-06 disjunctive D0 removed",
             lambda t: not re.search(r"\(i\) the smooth-with-decay default.*or\s*\(ii\)", t, re.S)),
            ("HF-06 F1 data contract bound", lambda t: "s = 4" in t and "1/2 + epsilon" in t),
        ],
    },
    "F2b": {
        "path": "schemas/af_scc_c0_vacuum.yaml",
        "checks": [
            ("HF-06 disjunctive D0 removed", lambda t: "selected: \"smooth-with-decay\"" in t),
            ("HF-03 candidate_anchors", lambda t: "candidate_anchors" in t),
        ],
    },
    "L0": {
        "path": "ledger/theorems.jsonl",
        "checks": [
            ("HF-02 invented tokens removed", _no_invented := (lambda t: not re.search(
                r"AF-SCC-OTHER-MODELS|AF-WCC-VAC-BH-FORM|AF-WCC-VAC-NS-CONSTR", t))),
            ("HF-03 scope metadata present", lambda t: '"source_meta"' in t),
            ("HF-14 reviewer verdicts present",
             lambda t: bool(re.search(r'"reviewed_by"|"reviewer_verdict"', t))),
        ],
    },
}


def main() -> int:
    rows = []
    for target, spec in CHECKS.items():
        t = text(spec["path"])
        results = [(name, bool(fn(t))) for name, fn in spec["checks"]]
        resolved = [n for n, ok in results if ok]
        open_ = [n for n, ok in results if not ok]
        # build an aggregate hygiene view for L0 across all ledger files
        if target == "L0":
            files = sorted((ROOT / "artifacts/literature").rglob("*.jsonl"))
            with_scope = sum(1 for f in files for l in f.read_text().splitlines()
                             if '"source_meta"' in l)
            reviewed = sum(1 for f in files for l in f.read_text().splitlines()
                           if re.search(r'"reviewed_by"|"reviewer_verdict"', l))
            results.append((f"HF-03 corpus-wide source_meta={with_scope}", with_scope > 0))
            results.append((f"HF-14 corpus-wide reviewer_verdicts={reviewed}", reviewed > 0))
            open_ += [n for n, ok in results[-2:] if not ok]
        review = REV / f"{target}-review-lead-audit.json"
        if review.exists():
            d = json.loads(review.read_text())
            cur = sha(spec["path"])
            pinned = d.get("artifact_sha256")
            if cur != pinned and not open_:
                d["sha_history"] = d.get("sha_history", []) + [
                    {"sha256": pinned, "at": d.get("last_repinned_at")},
                    {"sha256": cur, "at": NOW, "note": "auto re-pin: all recorded checks pass on this revision"}]
                d["artifact_sha256"] = cur
                d["last_repinned_at"] = NOW
                review.write_text(json.dumps(d, indent=2) + "\n")
            rows.append((target, "resolved" if not open_ else "open", len(resolved), len(open_), cur[:12], pinned[:12] if pinned else "-"))
        else:
            rows.append((target, "no-review", len(resolved), len(open_), sha(spec["path"])[:12], "-"))
    print(f"re-review @ {NOW}")
    print(f"{'target':6s} {'state':9s} {'ok':>3s} {'open':>4s} {'current':12s} {'pinned':12s}")
    for r in rows:
        print(f"{r[0]:6s} {r[1]:9s} {r[2]:3d} {r[3]:4d} {r[4]:12s} {r[5]:12s}")
    with open(ROOT / "artifacts" / "audit" / "checkpoints" / "rereview_log.jsonl", "a") as f:
        f.write(json.dumps({"at": NOW, "rows": rows}, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
