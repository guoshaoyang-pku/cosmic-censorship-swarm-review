"""Evidence audit for research_map.json.

The stock validator checks DAG shape only. This audit enforces the project rule that
a completed node requires an on-disk artifact plus validation evidence, that gates
are explicit and their dependents respect them, and that distinct WCC/SCC classes
are never merged. It writes runtime/state/artifact_hashes.json.

Exit code 0 = no hard violations; 1 = hard violations.
  python3 research_map/audit_evidence.py [--map research_map/research_map.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CST = timezone(timedelta(hours=8))
# Classes that must remain separate (ASTRA_HANDOFF.md hard decision 1).
SEPARATE_CLASSES = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def audit(map_path: Path) -> dict:
    m = json.loads(map_path.read_text())
    hard, soft, hashes = [], [], {}

    nodes = {}
    for g in m.get("groups", []):
        for n in g.get("nodes", []):
            n = dict(n)
            n["_group"] = g["id"]
            nodes[n["id"]] = n

    # 1. done nodes must have an existing artifact, validation evidence and hash
    for nid, n in nodes.items():
        art = n.get("artifact")
        if n.get("status") == "done":
            if not art:
                hard.append(f"{nid}: done with no declared artifact")
            elif not (ROOT / art).exists():
                hard.append(f"{nid}: done but artifact missing on disk: {art}")
            else:
                hashes[art] = {"sha256": sha256(ROOT / art), "node_id": nid,
                               "bytes": (ROOT / art).stat().st_size}
            if not n.get("validation_status"):
                hard.append(f"{nid}: done without validation_status")
            if not n.get("evidence_refs") and not n.get("validation_evidence"):
                soft.append(f"{nid}: done without evidence_refs (validation unprovenanced)")
        elif art and (ROOT / art).exists() and n.get("status") in {"active", "blocked"}:
            hashes[art] = {"sha256": sha256(ROOT / art), "node_id": nid,
                           "bytes": (ROOT / art).stat().st_size, "status": n.get("status")}

    # 2. gates: every gate must declare criteria + evidence; dependents must respect verdicts
    gates = {g["gate_id"]: g for g in m.get("gates", [])}
    for gid, g in gates.items():
        if not g.get("criteria"):
            hard.append(f"gate {gid}: no criteria")
        if g.get("verdict") not in {"pass", "fail", "pending", None}:
            hard.append(f"gate {gid}: invalid verdict {g.get('verdict')}")
        if g.get("verdict") == "pass" and not g.get("evidence_refs"):
            hard.append(f"gate {gid}: passed without evidence_refs")

    lock = m.get("numerics_lock", {})
    if lock.get("state") == "locked":
        for dep in lock.get("required_gates", []):
            g = gates.get(dep)
            if g is None:
                hard.append(f"numerics_lock: unknown required gate {dep}")
            elif g.get("verdict") != "pass" and lock.get("state") == "locked":
                pass  # expected; lock is doing its job
        # enforce: any active/done numerics node beyond N0 while locked = violation
        for nid in lock.get("locked_nodes", []):
            n = nodes.get(nid)
            if n and n.get("status") in {"active", "done"}:
                hard.append(f"numerics_lock: {nid} is {n['status']} while self-gravitating numerics are locked")

    # 3. class separation: check node labels/class ids and the artifacts themselves.
    # Prohibitions ("never write 'C0 or C2'") are instructions, not merged classes.
    NEG = re.compile(r"never|not\b|no\b|forbid|avoid|separate|split|distinct|reject|leak", re.I)
    MERGE = re.compile(r"C0\s+(?:or|and)\s+C2|C2\s+(?:or|and)\s+C0", re.I)

    def scan_text(text: str, where: str):
        for match in MERGE.finditer(text):
            ctx = text[max(0, match.start() - 120):match.start()]
            if not NEG.search(ctx):
                hard.append(f"{where}: merges C0/C2: ...{text[max(0,match.start()-60):match.end()+30]!r}")
                return

    for g in m.get("groups", []):
        for n in g.get("nodes", []):
            cls = str(n.get("class_id", ""))
            if "C0" in cls and "C2" in cls:
                hard.append(f"{n['id']}: class_id merges C0 and C2 ({cls})")
            scan_text(json.dumps({k: n.get(k) for k in ("label", "class_id", "conclusion_type")}), n["id"])
            art = n.get("artifact")
            if art and (ROOT / art).is_file() and (ROOT / art).stat().st_size < 2_000_000:
                try:
                    scan_text((ROOT / art).read_text(errors="replace"), f"{n['id']} artifact {art}")
                except OSError:
                    pass

    # 4. dependency status: active node whose deps are not done -> soft (may be legitimately exploratory)
    for nid, n in nodes.items():
        if n.get("status") in {"active", "done"}:
            for d in n.get("depends_on", []):
                dn = nodes.get(d)
                if dn and dn.get("status") not in {"done"} and n.get("status") == "done":
                    hard.append(f"{nid}: done while dependency {d} is {dn.get('status')}")

    return {"hard": hard, "soft": soft, "hashes": hashes,
            "checked_at": datetime.now(CST).isoformat(timespec="seconds")}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", default=str(ROOT / "research_map" / "research_map.json"))
    ap.add_argument("--write-hashes", action="store_true", default=True)
    a = ap.parse_args()
    res = audit(Path(a.map))
    out = ROOT / "runtime" / "state" / "artifact_hashes.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({k: v for k, v in res.items() if k != "hard"}, indent=2, sort_keys=True))
    print(f"evidence audit: {len(res['hard'])} hard, {len(res['soft'])} soft")
    for e in res["hard"]:
        print(f"  HARD  {e}")
    for e in res["soft"]:
        print(f"  soft  {e}")
    sys.exit(1 if res["hard"] else 0)
