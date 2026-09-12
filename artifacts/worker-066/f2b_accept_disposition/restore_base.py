#!/usr/bin/env python3
"""Restore the pin-instant (01:15:04) base artifacts so the base event set's evidence refs resolve.

A determinism re-run of audit.py at 01:16 overwrote report.json / evidence/*.json with the
later-instant census, and three further reviews landed after the pin.  The pin instant is
reconstructible: the pinned review copies plus the review corpus minus the three post-pin files.
This script mirrors a sandbox, runs the UNCHANGED audit.py inside it, and verifies that the
regenerated evidence reproduces the hashes the base events already cite.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REAL = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SB = Path("/tmp/w066_restore_base")
POST_PIN = {  # reviews that appeared after the pin instant -- absent from the pin corpus
    "F2b-direction-crossverify-worker-100.json",
    "F2b-remedy-crossverify-worker-100.json",
    "F2b-rev30-h2-direction-053.json",
}
EXPECT = {  # hashes the base event set cites
    "report.json": "a82623db025e8b14b266ed9c171ddfa83c63cbc66525c02894f7eaa23a175696",
    "evidence/accepts.json": "63e18044807d61c6466b356ff68df5e700e14abc25583fd81fdef2d3803faafc",
    "evidence/carriers.json": "a6a9352f533f9960063d2380e81415ecee78ea528c0110b970314f4072c6a1d8",
    "evidence/checks.json": "7a18e9059b3a638ba9c5a5c1dcced1d0e50d8cc2b6dc56f756508bd763badb87",
    "evidence/controls.json": "70d6ff0ed2ec8021a099b5bf702ab9b9f02f41c8633bc6ded1ca8cf6102a1c45",
}


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


# 0. preserve the later-instant artifacts before anything is overwritten
later = OUT / "evidence" / "instant-011604"
later.mkdir(parents=True, exist_ok=True)
for rel in ("report.json", "evidence/accepts.json", "evidence/carriers.json",
            "evidence/checks.json", "evidence/controls.json", "evidence/pins.json"):
    src = OUT / rel
    if src.is_file():
        shutil.copy2(src, later / Path(rel).name)
(later / "README.txt").write_text(
    "Later-instant (01:16) copies of the base artifacts, preserved when the pin-instant evidence "
    "was restored from the pinned corpus. The addendum claim cites report.json#03e5c2de; that "
    "content is this directory's report.json.\n")

# 1. build the sandbox
if SB.exists():
    shutil.rmtree(SB)
SB.mkdir(parents=True)
TASKREL = "artifacts/worker-066/f2b_accept_disposition"
for d in ("schemas", "research_map"):
    os.symlink(REAL / d, SB / d)
(SB / "artifacts").mkdir()
for d in ("formulation", "worker-080"):
    os.symlink(REAL / "artifacts" / d, SB / "artifacts" / d)
(SB / TASKREL).mkdir(parents=True)
(SB / "reviews").mkdir()
pinned = json.loads((OUT / "evidence" / "pinned_inputs.json").read_text())
pin_map = {rel: rec for rel, rec in pinned.items() if rec and rel.startswith("reviews/")}
for f in sorted((REAL / "reviews").glob("F2b-*.json")):
    if f.name in POST_PIN:
        continue
    rel = f"reviews/{f.name}"
    dst = SB / rel
    if rel in pin_map:  # pinned bytes win (worker-072 moved after the pin)
        shutil.copy2(REAL / pin_map[rel]["pinned_copy"], dst)
    else:
        shutil.copy2(f, dst)
shutil.copy2(OUT / "audit.py", SB / TASKREL / "audit.py")

# 2. run the unchanged instrument inside the sandbox
r = subprocess.run([sys.executable, str(SB / TASKREL / "audit.py")],
                   capture_output=True, text=True)
print("sandbox run rc=", r.returncode, r.stdout.strip()[:200], r.stderr.strip()[:200])

# 3. verify reproduction, then restore
ok = True
for rel, want in EXPECT.items():
    got = sha(SB / TASKREL / rel)
    match = got == want
    ok = ok and match
    print(f"  {rel}: {'MATCH' if match else 'DIFF '} {got[:12]} want {want[:12]}")

if ok:
    for rel in EXPECT:
        shutil.copy2(SB / TASKREL / rel, OUT / rel)
    print("RESTORED: pin-instant base artifacts reproduced byte-exactly")
    sys.exit(0)
print("NOT RESTORED: reproduction failed; base refs remain superseded")
sys.exit(1)
