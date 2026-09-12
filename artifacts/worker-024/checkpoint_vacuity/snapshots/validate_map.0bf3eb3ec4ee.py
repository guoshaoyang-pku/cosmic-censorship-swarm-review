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
    # integrated from worker-19's proposed patch (artifacts/audit/flash19_validate_map_gate.patch)
    # pass-05 controller repair: declared artifact paths are repo-root-relative (e.g.
    # research_map/formulation_taxonomy.yaml), so the default base must be the repo root,
    # not this module's directory. The previous default made every done node with a
    # declared artifact look missing on disk (latent until the first gate pass).
    base = Path(base) if base else ROOT.parent
    errors=[]; groups={g["id"]:g for g in m.get("groups",[])}; nodes={}
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
    ap=argparse.ArgumentParser(); ap.add_argument("--map",default=str(ROOT/"research_map.json")); ap.add_argument("events",nargs="*"); a=ap.parse_args()
    errs=validate_map(load(a.map))+validate_events(a.events)
    if errs:
        print('INVALID'); print('\n'.join('- '+e for e in errs)); sys.exit(1)
    print('VALID')
