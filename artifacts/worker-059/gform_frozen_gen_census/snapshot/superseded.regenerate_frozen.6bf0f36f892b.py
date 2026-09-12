#!/usr/bin/env python3
"""Regenerate FROZEN.json from disk after a published revision.

Keeps every existing entry (recomputing its sha256/bytes), and additionally pins the CANONICAL
published copy of each class artifact. Both trees are byte-identical at publish time, so the
authoring mirror and the canonical copy carry the same hash; reviewers and gates bind to the
canonical path.

Usage: python3 artifacts/formulation/tools/regenerate_frozen.py --revision 20 --delta "..." 
"""
import argparse, hashlib, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MAN = ROOT / "artifacts/formulation/FROZEN.json"
CANONICAL = [
    "research_map/formulation_taxonomy.yaml",
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
]
# Evidence/review artifacts that must be pinned on first publication but are not created by the
# tools above. Listed explicitly so a regeneration is reproducible.
PIN_EXTRAS = [
    "artifacts/formulation/reviews/BN_TRIAGE.md",
    "artifacts/formulation/evidence/bn_triage.json",
    "artifacts/formulation/evidence/variant_registry_check.json",
    "artifacts/formulation/evidence/variant_delta_check.json",
    "artifacts/formulation/tools/regenerate_frozen.py",
    # rev29 (astra-life05-evidence-binding-repair): pin the two re-pinned evidence corpora and the
    # repair report/tool, so the evidence-binding chain is inside the manifest and future stale-pin
    # drift is detectable (CF-20).
    "schemas/taxonomy_cases.jsonl",
    "schemas/f1_falsifier_tests.jsonl",
    "artifacts/formulation/evidence/evidence_binding_repair_rev29_report.json",
    "artifacts/formulation/tools/evidence_binding_repair_rev29.py",
]
# Re-runnable measurements that stamp a generation timestamp on every run. They are NOT pinned:
# pinning them guarantees drift the next time the check runs. Their verdicts are cited by hash in
# the emitting status event instead.
VOLATILE = [
    "artifacts/formulation/evidence/aggregator_pin_check_rev3.json",
]

def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--revision", type=int, required=True)
    ap.add_argument("--delta", required=True)
    ap.add_argument("--at", required=True)
    args = ap.parse_args()

    man = json.loads(MAN.read_text())
    files = dict(man.get("files", {}))
    dropped = [rel for rel in VOLATILE if rel in files]
    for rel in dropped:
        files.pop(rel, None)
    missing, added = [], []
    for rel in list(files) + CANONICAL + PIN_EXTRAS:
        p = ROOT / rel
        if not p.exists():
            missing.append(rel)
            continue
        h = sha(p)
        if rel not in files:
            added.append(rel)
        files[rel] = {"sha256": h, "bytes": p.stat().st_size}
    if missing:
        print("MISSING (refusing to write):", missing)
        return 1
    man["files"] = dict(sorted(files.items()))
    man["revision"] = args.revision
    man["frozen_at"] = args.at
    man[f"rev{args.revision}_delta"] = [args.delta]
    man["path_policy"] = (
        "the canonical published copy is research_map/formulation_taxonomy.yaml and schemas/*.yaml; "
        "the artifacts/formulation/ entries are the authoring mirror and are byte-identical at publish "
        "time. Reviewers, gates and the ledger bind to the canonical path + sha256."
    )
    MAN.write_text(json.dumps(man, indent=2) + "\n")
    print(f"FROZEN revision {args.revision}: {len(man['files'])} files pinned "
          f"({len(added)} canonical entr{'y' if len(added)==1 else 'ies'} added)")
    for a in added:
        print("  +", a)
    for d in dropped:
        print("  - (volatile, unpinned)", d)
    return 0

if __name__ == "__main__":
    sys.exit(main())
