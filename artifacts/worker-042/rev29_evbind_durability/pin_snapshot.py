#!/usr/bin/env python3
"""W042-REV29-EVBIND-DURABILITY-06 -- freeze-first input pinner.

Copies the inputs this task's checker audits into snapshot/ under
sha256-named copies plus a manifest. The checker reads only snapshot/ bytes, so
every classification is replayable from the pin. Writes only under this
worker's own artifacts directory. No canonical path is opened for writing.

Usage: python3 pin_snapshot.py
"""
import hashlib
import json
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SNAP = HERE / "snapshot"
TZ = timezone(timedelta(hours=8))

# relpath -> stable snapshot filename (all inside snapshot/)
FILES = {
    "research_map/formulation_taxonomy.yaml": "A_map_taxonomy.yaml",
    "artifacts/formulation/formulation_taxonomy.yaml": "B_lead_contract.yaml",
    "artifacts/formulation/VOCAB_ALIASES.json": "AL_vocab_aliases.json",
    "artifacts/formulation/evidence/taxonomy_consistency.json": "E_consistency_evidence.json",
    "artifacts/formulation/tools/check_taxonomy_consistency.py": "W_check_taxonomy_consistency.py",
    "artifacts/formulation/tools/verify_frozen.py": "verify_frozen.py",
    "artifacts/formulation/FROZEN.json": "FROZEN.json",
    "schemas/af_wcc_vacuum.yaml": "F1_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml": "F2a_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml": "F2b_scc_c0_vacuum.yaml",
    "research_map/events.jsonl": "events.jsonl",
}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    SNAP.mkdir(parents=True, exist_ok=True)
    records = {}
    for rel, name in FILES.items():
        src = REPO / rel
        if not src.exists():
            print(f"MISSING {rel}", file=sys.stderr)
            return 2
        dst = SNAP / name
        shutil.copyfile(src, dst)
        records[rel] = {
            "snapshot_file": name,
            "sha256": sha256_file(dst),
            "bytes": dst.stat().st_size,
        }
    # second live measurement: flag any input that moved during the pin
    for rel, rec in records.items():
        rec["live_stable_during_pin"] = sha256_file(REPO / rel) == rec["sha256"]
    manifest = {
        "task_id": "W042-REV29-EVBIND-DURABILITY-06",
        "actor": "worker-042",
        "pinned_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "repo": str(REPO),
        "files": records,
        "note": "checker reads these snapshot copies only; live files are re-measured for stability, never modified",
    }
    (SNAP / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    bad = [r for r, v in records.items() if not v["live_stable_during_pin"]]
    print(f"pinned {len(records)} files; unstable during pin: {len(bad)}")
    for b in bad:
        print("  MOVED " + b)
    print("manifest", sha256_file(SNAP / "manifest.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
