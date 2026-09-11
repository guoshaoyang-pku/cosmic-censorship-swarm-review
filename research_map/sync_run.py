"""Project a framework/run.py run directory into research_map.json."""
from __future__ import annotations
import argparse, hashlib, json, time
from pathlib import Path

def sha256(p):
    h=hashlib.sha256(); h.update(Path(p).read_bytes()); return h.hexdigest()

def sync(map_path, run_dir, node_id, events_path=None):
    mp=Path(map_path); data=json.loads(mp.read_text()); rd=Path(run_dir); metrics={}
    if (rd/"metrics.json").exists(): metrics=json.loads((rd/"metrics.json").read_text())
    target=None
    for g in data["groups"]:
        for n in g.get("nodes",[]):
            if n["id"]==node_id: target=n
    if target is None: raise SystemExit(f"unknown map node {node_id}")
    target["status"] = "done" if (rd/"SOLVED.json").exists() else "active"
    target["run_dir"] = str(rd)
    target["calls"] = metrics.get("calls", 0)
    target["verified"] = metrics.get("verified", 0)
    target["admitted"] = metrics.get("admitted", 0)
    target["solved"] = metrics.get("solved", 0)
    target["last_metrics"] = metrics
    arts=[]
    for p in rd.rglob('*'):
        if p.is_file() and p.name not in {"metrics.json"}: arts.append({"path":str(p),"sha256":sha256(p),"bytes":p.stat().st_size})
    target["artifacts"] = arts
    data["updated_at"] = time.strftime('%Y-%m-%dT%H:%M:%S%z')
    mp.write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n")
    if events_path:
        ev={"event_id":f"sync-{node_id}-{int(time.time())}","event_type":"artifact","created_at":time.time(),"actor":"framework.sync_run","node_id":node_id,"artifact_type":"run_directory","path":str(rd),"sha256":sha256(rd/"metrics.json") if (rd/"metrics.json").exists() else "","validation_status":"passed" if metrics else "unverified"}
        with open(events_path,'a') as f:f.write(json.dumps(ev)+"\n")

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("run_dir"); ap.add_argument("--node",required=True); ap.add_argument("--map",default="research_map.json"); ap.add_argument("--events"); a=ap.parse_args(); sync(a.map,a.run_dir,a.node,a.events)
