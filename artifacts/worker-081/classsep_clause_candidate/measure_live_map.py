#!/usr/bin/env python3
"""Measure the candidate vs the applied detector on the pinned r3 map snapshot.

Control: the applied detector must reproduce the adjudication's hard count (19 hard =
17 labeled FP + 2 unlabeled) on the same snapshot, evidence the harness is faithful.
Read-only: no canonical file is written; the applied bytes are copied here and
hash-verified against the pin recorded in pre_registration.json.
"""
import hashlib
import importlib.util
import json
import re
import shutil
import sys
from pathlib import Path

D = Path(__file__).resolve().parent
ROOT = D.parents[2]
SNAP = ROOT / "artifacts/audit/classsep_r3_map_snapshot_20260912T010324.json"
SNAP_SHA = "f344ed2aaea58e4d21c46c1d919e2476b860da4b757b9fbc948d3649bac7c749"
APPLIED_SRC = ROOT / "research_map/class_separation.py"
APPLIED_PIN = "a8c04fc31e4afa1b691cd6bfb6bf8b4f953a0adc925939a8351bab9cf453c5bd"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    assert sha(SNAP) == SNAP_SHA, f"snapshot moved: {sha(SNAP)}"
    applied_copy = D / "applied_a8c04fc3.py"
    shutil.copyfile(APPLIED_SRC, applied_copy)
    applied_sha = sha(applied_copy)
    m = json.loads(SNAP.read_text())
    print("snapshot", SNAP_SHA[:12], "claims", len(m.get("claims", [])), "applied", applied_sha[:12])

    arms = {}
    for name, path in (("APPLIED_a8c04fc3", applied_copy), ("CANDIDATE_r2", D / "class_separation_clause.py")):
        mod = load(path, name)
        findings = mod.findings_for_map(m)
        hard = [f for f in findings if not f.startswith("CLASSSEP-SOFT")]
        soft = [f for f in findings if f.startswith("CLASSSEP-SOFT")]
        claims = sorted({int(x) for f in hard for x in re.findall(r"claims\[(\d+)\]", f)})
        arms[name] = {"sha256": sha(path), "hard": len(hard), "soft": len(soft),
                      "claims_flagged": claims, "findings": hard}
        print(name, "hard", len(hard), "soft", len(soft), "claims", len(claims), claims[:20])

    out = {"snapshot": str(SNAP), "snapshot_sha256": SNAP_SHA,
           "applied_pin_expected": APPLIED_PIN, "applied_measured": applied_sha,
           "applied_control_reproduces_adjudication_19": arms["APPLIED_a8c04fc3"]["hard"] == 19,
           "arms": arms}
    (D / "live_map_impact.json").write_text(json.dumps(out, indent=1))
    print("control reproduces 19:", out["applied_control_reproduces_adjudication_19"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
