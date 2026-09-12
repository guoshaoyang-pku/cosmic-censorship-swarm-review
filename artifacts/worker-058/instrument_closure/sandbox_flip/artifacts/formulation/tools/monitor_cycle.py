#!/usr/bin/env python3
"""Formulation-lead monitoring cycle: report new formulation-relevant events since a cursor.

  python3 artifacts/formulation/tools/monitor_cycle.py            # report only
  python3 artifacts/formulation/tools/monitor_cycle.py --advance  # advance the cursor too

Relevance: class_ids intersect the formulation classes, or node_id in F0/F1/F2/F2a/F2b/A1,
or artifacts/formulation paths, or actor is a formulation worker.
"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
EV = ROOT/"research_map/events.jsonl"
CUR = ROOT/"artifacts/formulation/evidence/monitor_cursor.json"
CLASSES = {"AF-WCC-VAC-GEN","AF-SCC-C2-VAC-GEN","AF-SCC-C0-VAC-GEN","AF-WCC-SCALAR-SPH"}
NODES = {"F0","F1","F2","F2a","F2b","A1"}
def relevant(e):
    if e.get("class_id") in CLASSES: return True
    if any(c in CLASSES for c in (e.get("class_ids") or [])): return True
    if e.get("node_id") in NODES: return True
    blob=json.dumps(e)
    if "artifacts/formulation/" in blob: return True
    if str(e.get("actor","")).startswith(("worker-","deepseek-flash-")) and "formulation" in blob: return True
    return False
def main():
    lines=[l for l in EV.read_text().splitlines() if l.strip()]
    cur=json.loads(CUR.read_text())["index"] if CUR.exists() else 0
    new=[json.loads(l) for l in lines[cur:]]
    rel=[e for e in new if relevant(e)]
    print(f"events total={len(lines)} cursor={cur} new={len(new)} relevant={len(rel)}")
    for e in rel:
        print(f"  {e.get('event_type'):16} {str(e.get('node_id') or e.get('group_id') or '-'):5} {e.get('event_id')}")
        for k in ("summary","statement","verdict","description","note"):
            if e.get(k): print(f"     {k}: {str(e[k])[:240]}")
    if "--advance" in sys.argv:
        CUR.parent.mkdir(parents=True, exist_ok=True)
        CUR.write_text(json.dumps({"index":len(lines),"advanced_at":__import__("datetime").datetime.now().isoformat(timespec="seconds")}))
        print(f"cursor advanced to {len(lines)}")
main()
