#!/usr/bin/env python3
import json, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "tools" / "gate.py"
DATA = ROOT / "data" / "pinned.json"
OUT = ROOT / "out" / "report.json"
def main():
    r = subprocess.run([sys.executable, str(GATE), str(DATA)], capture_output=True, text=True)
    OUT.write_text(r.stdout)
if __name__ == "__main__":
    main()
