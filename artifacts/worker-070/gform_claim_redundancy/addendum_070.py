#!/usr/bin/env python3
"""W070-GFORM-CLAIM-REDUNDANCY-01 post-frame addendum (read-only; stdlib only).

The pre-registered primary signature (frame.json) is the full declared hash set of
each claim, which includes each worker's own artifact hashes; it is therefore close
to unique by construction (measured redundancy 1.0393). This addendum asks the
complementary question, declared AFTER the primary run and reported as secondary:

    how concentrated are the G-FORM claims on the SAME canonical target pins?

Rules declared here (post-frame, exploratory):
  * same snapshot as frame.json (hash re-verified);
  * universe identical to the primary run;
  * for every reference string under the frame's REF_KEYS, parse `path#hash` and
    `path#sha256:hash` pairs; keep a pair iff `path` starts with one of the declared
    canonical roots; normalise hash to 12 lower-case hex;
  * target key of a claim = sorted set of (path, hash12) pairs;
  * report distinct target keys, the per-pin claim counts and actor counts, and the
    claims-per-target-key distribution.

This is a citation-concentration measure only. Two claims citing the same pin are
not two independent measurements; conversely, different instrument hashes are not
shown to be method-independent. No gate verdict, no canonical write.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
FRAME = OUT / "frame.json"
SNAP = OUT / "report.json"
CST = timezone(timedelta(hours=8))

REF_KEYS = {
    "artifact_refs", "evidence_refs", "artifact_ref", "artifact_sha256",
    "reviewed_sha256", "ledger_sha256", "source_sha256", "sha256", "hash",
    "pins", "reviewed_pins", "frozen_manifest", "manifest_sha256",
    "frozen_rev29_pin", "entry_hashes", "exit_hashes", "reviewed_frozen_sha256",
    "reviewed_mirror_sha256", "supersedes_sha256", "base_sha256", "frozen_sha256",
}
CANON_ROOTS = (
    "schemas/",
    "research_map/",
    "ledger/",
    "artifacts/formulation/FROZEN.json",
    "artifacts/formulation/formulation_taxonomy.yaml",
    "artifacts/formulation/VARIANT_REGISTRY.json",
    "artifacts/formulation/VOCAB_ALIASES.json",
    "schemas/f1_falsifier_tests.jsonl",
    "schemas/taxonomy_cases.jsonl",
)
PAIR = re.compile(r"([A-Za-z0-9_./+-]+?)#(?:sha256:)?([0-9a-fA-F]{12,64})")
FALSIFIER = (
    "Re-run addendum_070.py against the same snapshot sha256 as frame.json. "
    "Falsified if any per-pin count or actor count differs, or if a claim is shown to "
    "cite a canonical path#hash pair not reported here. A snapshot mismatch voids the "
    "addendum. It asserts nothing about the content of the cited artifacts."
)


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_strings(value, out: list) -> None:
    if isinstance(value, str):
        out.append(value)
    elif isinstance(value, dict):
        for k, v in value.items():
            if isinstance(k, str) and re.fullmatch(r"[0-9a-fA-F]{12,64}", k):
                out.append(k)
            collect_strings(v, out)
    elif isinstance(value, list):
        for v in value:
            collect_strings(v, out)


def canonical_pairs(event: dict) -> set:
    strings: list = []
    for k in REF_KEYS:
        if k in event:
            collect_strings(event[k], strings)
    pairs = set()
    for s in strings:
        for path, h in PAIR.findall(s):
            if any(path.startswith(r) or path == r for r in CANON_ROOTS):
                pairs.add((path, h.lower()[:12]))
    return pairs


def class_binding(event: dict) -> set:
    b = set()
    if isinstance(event.get("class_id"), str):
        b.add(event["class_id"])
    if isinstance(event.get("class_ids"), list):
        b.update(c for c in event["class_ids"] if isinstance(c, str))
    return b


def main() -> int:
    frame = json.loads(FRAME.read_text())
    report = json.loads(SNAP.read_text())
    snap = ROOT / frame["snapshot"]["snapshot_path"]
    if sha256_file(snap) != frame["snapshot"]["snapshot_sha256"]:
        print("VOID: snapshot mismatch")
        return 2
    if report.get("snapshot_sha256") != frame["snapshot"]["snapshot_sha256"]:
        print("VOID: primary report is at a different snapshot")
        return 2

    gform = {"AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"}
    claims, seen = [], set()
    for line in snap.open():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        if not isinstance(d, dict) or d.get("event_type") != "claim":
            continue
        eid = d.get("event_id")
        if isinstance(eid, str):
            if eid in seen:
                continue
            seen.add(eid)
        if class_binding(d) & gform:
            claims.append(d)
    if len(claims) != report["claim_events_in_universe"]:
        print("VOID: universe recount differs from primary report")
        return 3

    keys = [tuple(sorted(canonical_pairs(d))) for d in claims]
    with_target = [k for k in keys if k]
    key_counts = Counter(keys)
    pin_claims = Counter()
    pin_actors = defaultdict(set)
    for d, k in zip(claims, keys):
        for p in k:
            pin_claims[p] += 1
            pin_actors[p].add(str(d.get("actor")))
    top_pins = [
        {
            "path": p,
            "hash12": h,
            "claims": n,
            "actors": len(pin_actors[(p, h)]),
            "actor_sample": sorted(pin_actors[(p, h)])[:8],
        }
        for (p, h), n in pin_claims.most_common(15)
    ]
    dist = Counter(len(k) for k in keys)
    multi = {f"{k}+": v for k, v in sorted(dist.items()) if k >= 2}
    out = {
        "schema": "worker-070/claim-redundancy-addendum/v1",
        "task_id": "W070-GFORM-CLAIM-REDUNDANCY-01",
        "actor": "worker-070",
        "created_at": now(),
        "status": "POST-FRAME SECONDARY (exploratory); primary pre-registered report is report.json",
        "snapshot_sha256": frame["snapshot"]["snapshot_sha256"],
        "universe_claims": len(claims),
        "canonical_roots": list(CANON_ROOTS),
        "rule": "claim target key = sorted set of (canonical path, hash12) pairs parsed from REF_KEYS refs",
        "claims_with_at_least_one_canonical_pin": len(with_target),
        "claims_with_no_canonical_pin": len(keys) - len(with_target),
        "distinct_target_keys": len(key_counts),
        "target_key_distribution": {str(k): v for k, v in sorted(dist.items())},
        "claims_sharing_a_target_key": sum(v for v in key_counts.values() if v > 1),
        "top_target_pins": top_pins,
        "falsifier": FALSIFIER,
        "non_claims": [
            "Citation concentration only; two claims citing one pin are not independent measurements.",
            "Different instrument hashes are not shown to be method-independent.",
            "Worker evidence only; no gate verdict, no node status, no canonical write.",
        ],
    }
    (OUT / "addendum.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: out[k] for k in (
        "claims_with_at_least_one_canonical_pin", "claims_with_no_canonical_pin",
        "distinct_target_keys", "claims_sharing_a_target_key")}, indent=1))
    print("top pins:")
    for p in top_pins[:10]:
        print(f"  {p['claims']:4d} claims / {p['actors']:3d} actors  {p['path']}#{p['hash12']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
