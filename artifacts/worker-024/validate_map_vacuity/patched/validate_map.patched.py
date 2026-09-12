"""Validate research_map.json and event streams before Astra accepts state."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from schemas import validate_event, SchemaError

ROOT = Path(__file__).parent
TAXONOMY = ROOT / "formulation_taxonomy.yaml"

def load(path): return json.loads(Path(path).read_text())

def _real_entries(p):
    return [c for c in p.iterdir() if c.name != ".DS_Store" and not c.name.startswith("._")]


def validate_map(m, base=None):
    # W024-VALIDATE-MAP-VACUITY-01 proposed patch (owner decision to apply):
    #  (1) non-vacuity block -- a structurally stripped map must not validate;
    #  (2) map artifact paths are repo-root-relative (apply_events.py:19,393),
    #      so the default base is the repo root, not the research_map/ dir.
    base = Path(base) if base else ROOT.parent
    errors=[]
    groups_raw=m.get("groups")
    if not isinstance(groups_raw,list) or not groups_raw:
        errors.append("vacuity guard: map has no groups")
    if not any(isinstance(g,dict) and g.get("nodes") for g in (groups_raw or [])):
        errors.append("vacuity guard: map has no nodes")
    for _key in ("gates","claims","reviews","assignments","numerics_lock"):
        if _key not in m:
            errors.append(f"vacuity guard: missing required section {_key}")
    if isinstance(m.get("gates"),list) and not m["gates"]:
        errors.append("vacuity guard: gates list is empty")
    _lock=m.get("numerics_lock") or {}
    if isinstance(_lock,dict) and _lock.get("state")=="locked":
        _locked=set(_lock.get("locked_nodes") or [])
        for _g in groups_raw or []:
            if not isinstance(_g,dict): continue
            for _n in _g.get("nodes",[]) or []:
                if isinstance(_n,dict) and _n.get("id") in _locked and _n.get("status") in {"active","done"}:
                    errors.append(f"locked node {_n['id']} status {_n['status']} while numerics_lock=locked (hard decision 2)")
    groups={g["id"]:g for g in (groups_raw or [])}; nodes={}
    for g in groups.values():
        for n in g.get("nodes",[]):
            if n["id"] in nodes: errors.append(f"duplicate node {n['id']}")
            nodes[n["id"]]=(g["id"],n)
    edges=[]
    for gid,(group,n) in nodes.items():
        for dep in n.get("depends_on",[]):
            if dep not in nodes: errors.append(f"{gid}: unknown dependency {dep}")
            else: edges.append((dep,gid))
        if n.get("status") == "done" and not n.get("artifact"):
            errors.append(f"{gid}: done node has no artifact")
        if n.get("status") == "done" and not n.get("validation_status", n.get("validated", False)):
            errors.append(f"{gid}: done node lacks validation_status/validated=true")
        if n.get("status") == "done":
            art = n.get("artifact")
            if art:
                p = base / art
                if not p.exists():
                    errors.append(f"{gid}: declared artifact missing on disk: {art}")
                elif p.is_dir() and not _real_entries(p):
                    errors.append(f"{gid}: declared artifact directory is empty: {art}")
            if not n.get("evidence_refs"):
                errors.append(f"{gid}: done node has no evidence_refs")
    for e in m.get("cross_group_edges",[]):
        if e.get("from") not in nodes or e.get("to") not in nodes: errors.append(f"unknown cross edge {e}")
        else: edges.append((e["from"],e["to"]))
    adj={k:[] for k in nodes}
    for a,b in edges: adj.setdefault(a,[]).append(b)
    visiting=set(); visited=set()
    def dfs(x):
        if x in visiting: errors.append(f"cycle detected at {x}"); return
        if x in visited:return
        visiting.add(x)
        for y in adj.get(x,[]): dfs(y)
        visiting.remove(x); visited.add(x)
    for x in nodes: dfs(x)
    return errors

def validate_events(paths):
    errors=[]
    for p in paths:
        for i,line in enumerate(Path(p).read_text().splitlines(),1):
            if not line.strip(): continue
            try: validate_event(json.loads(line))
            except (ValueError, SchemaError) as e: errors.append(f"{p}:{i}: {e}")
    return errors

if __name__ == "__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--map",default=str(ROOT/"research_map.json")); ap.add_argument("--base",default=None); ap.add_argument("events",nargs="*"); a=ap.parse_args()
    errs=validate_map(load(a.map), base=a.base)+validate_events(a.events)
    if errs:
        print('INVALID'); print('\n'.join('- '+e for e in errs)); sys.exit(1)
    print('VALID')
