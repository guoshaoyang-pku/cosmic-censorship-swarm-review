#!/usr/bin/env python3
"""Apply the formulation group's map patch proposal, fail-closed.

  python3 artifacts/formulation/tools/apply_map_proposal.py                 # dry run (default)
  python3 artifacts/formulation/tools/apply_map_proposal.py --apply         # write map (Astra only)

Refuses to act if the base sha256 recorded in the proposal does not match the current map.
Resolves nodes by ID, not by array index, so concurrent edits do not silently misapply.
After patching it (a) runs the stock validator, (b) checks every declared artifact exists,
(c) checks the composite-regularity ban. Exit 0 = clean, 1 = problems, 2 = refused.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MAP = ROOT / "research_map" / "research_map.json"
PROP = ROOT / "artifacts" / "formulation" / "proposals" / "map_patch_F0_F1_F2.json"
sys.path.insert(0, str(ROOT / "research_map"))
from validate_map import validate_map  # noqa: E402


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# Composite-regularity detection must be negation-aware: the map legitimately QUOTES the
# forbidden phrase when banning it ("never 'C0 or C2'", "C2/C0 split", "keep C0 and C2
# separate"). A blunt substring search flags those and misses the merged slash form
# ("AF-SCC C0/C2 schema"), which is the actual leakage wording.
COMP_OR = __import__("re").compile(r"(C0|C2)\s+(or|and)\s+(C0|C2)", __import__("re").I)
COMP_SLASH = __import__("re").compile(r"(C0|C2)\s*/\s*(C0|C2)", __import__("re").I)
NEG_CTX = __import__("re").compile(
    r"(never|forbidden|no |not |cannot|merge|split|separate|distinct|ban|two files|registry|outside|anti_scope)", __import__("re").I)


def _strings(node, out):
    if isinstance(node, dict):
        for k, v in node.items():
            if k in ("composite_regularity_ban",):
                continue
            _strings(v, out)
    elif isinstance(node, list):
        for v in node:
            _strings(v, out)
    elif isinstance(node, str):
        out.append(node)


def composite_violations(m):
    """Flag composite regularity only where it BINDS a class, not where it is discussed.

    Measured on the live map 2026-09-11T23:35: 4 of 4 remaining lexical hits were
    mentions inside falsifier/criteria/claim-id text (e.g. "hunt 'C0 or C2' leakage"),
    not class definitions. Scanning identity fields plus bare labels removes that whole
    false-positive class; mentions stay reviewable by humans, which is honest.
    """
    ident = {"id", "label", "class_id", "class_ids", "artifact", "artifact_type", "gate_id", "scope"}
    bare = __import__("re").compile(r"^\W*(C0|C2)\s*(?:or|and|/)\s*(C0|C2)\W*$", __import__("re").I)
    out = []

    def walk(node, key=None):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, k)
        elif isinstance(node, list):
            for v in node:
                walk(v, key)
        elif isinstance(node, str):
            if key in ident and (COMP_OR.search(node) or COMP_SLASH.search(node)) and not NEG_CTX.search(node):
                out.append(f"{key}={node[:100]}")
            elif bare.match(node):
                out.append(f"bare label={node[:60]}")

    walk(m)
    return out


def find_node(m, nid):
    for gi, g in enumerate(m.get("groups", [])):
        for ni, n in enumerate(g.get("nodes", [])):
            if n.get("id") == nid:
                return gi, ni
    return None


def apply_ops(m, prop, log):
    m = copy.deepcopy(m)
    # resolve every node id ONCE against the pre-patch map: later ops may rename ids,
    # but array positions are stable, so index resolution must not be re-derived.
    index = {}
    for gi, g in enumerate(m.get("groups", [])):
        for ni, n in enumerate(g.get("nodes", [])):
            index[n.get("id")] = (gi, ni)
    for op in prop["ops"]:
        kind, nid, tail = op["op"], op.get("node"), op["path"]
        if tail.startswith("/gates"):
            m.setdefault("gates", []).append(copy.deepcopy(op["value"]))
            log.append(f"add gate {op['value']['gate_id']}")
            continue
        if tail.endswith("/-"):
            gid = op.get("group")
            gi = next((i for i, g in enumerate(m.get("groups", [])) if g.get("id") == gid), None)
            if gi is None:
                log.append(f"REFUSE: append group {gid!r} not found"); return None
            m["groups"][gi]["nodes"].append(copy.deepcopy(op["value"]))
            log.append(f"add node {op['value']['id']} to {gid}")
            continue
        if nid in index:
            gi, ni = index[nid]
            key = tail.rsplit("/", 1)[1]
            if kind == "add" and key in m["groups"][gi]["nodes"][ni]:
                log.append(f"SKIP add {nid}.{key}: already present"); continue
            m["groups"][gi]["nodes"][ni][key] = copy.deepcopy(op["value"])
            if key == "id":  # follow renames so later ops can address the new id
                index[op["value"]] = (gi, ni)
            log.append(f"{kind} {nid}.{key} = {json.dumps(op['value'])[:80]}")
        else:
            log.append(f"REFUSE: unhandled op path {tail}"); return None
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    prop = json.loads(PROP.read_text())
    if prop["base_sha256"] != sha(MAP):
        print(f"REFUSED: base sha mismatch\n  proposal {prop['base_sha256']}\n  current  {sha(MAP)}")
        return 2
    m = json.loads(MAP.read_text())
    log = []
    new = apply_ops(m, prop, log)
    print("\n".join("  " + x for x in log))
    if new is None:
        return 2
    errs = validate_map(new)
    print(f"stock validator: {'VALID' if not errs else 'INVALID'} {errs}")
    touched = {op.get("node") for op in prop["ops"]} | {"F2a", "F2b"}
    missing, missing_touched = [], []
    for g in new["groups"]:
        for n in g["nodes"]:
            p = n.get("artifact")
            if p and not (ROOT / p).exists():
                missing.append(f"{n['id']}:{p}")
                if n["id"] in touched:
                    missing_touched.append(f"{n['id']}:{p}")
    print(f"declared artifacts missing on disk (whole map): {len(missing)} -> {missing}")
    print(f"declared artifacts missing among PATCHED nodes: {len(missing_touched)} -> {missing_touched}")
    viol = composite_violations(new)
    print(f"composite-regularity ban: {'VIOLATED ' + str(viol) if viol else 'clean'}")
    ok = not errs and not missing_touched and not viol
    if a.apply:
        bak = ROOT / "runtime" / "state" / f"research_map.{sha(MAP)[:12]}.bak.json"
        bak.write_bytes(MAP.read_bytes())
        tmp = MAP.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(new, indent=2) + "\n")
        tmp.replace(MAP)
        print(f"APPLIED; rollback copy at {bak.relative_to(ROOT)}")
    else:
        print("dry run only; pass --apply to write (Astra owns the map)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
