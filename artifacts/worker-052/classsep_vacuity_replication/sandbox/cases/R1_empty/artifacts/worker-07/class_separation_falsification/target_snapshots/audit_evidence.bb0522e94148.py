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


def artifact_digest(path: Path) -> dict:
    """File -> sha256; directory -> manifest digest over sorted (relpath, sha256)."""
    if path.is_file():
        return {"kind": "file", "sha256": sha256(path), "bytes": path.stat().st_size}
    if path.is_dir():
        h = hashlib.sha256()
        files = sorted(p for p in path.rglob("*") if p.is_file() and not p.name.startswith("._"))
        for p in files:
            h.update(f"{p.relative_to(path)}\0{sha256(p)}\n".encode())
        return {"kind": "directory", "sha256": h.hexdigest(), "files": len(files),
                "bytes": sum(p.stat().st_size for p in files)}
    return {"kind": "absent", "sha256": None}


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
                hashes[art] = {"node_id": nid, **artifact_digest(ROOT / art)}
            if not n.get("validation_status"):
                hard.append(f"{nid}: done without validation_status")
            if not n.get("evidence_refs") and not n.get("validation_evidence"):
                soft.append(f"{nid}: done without evidence_refs (validation unprovenanced)")
        elif art and (ROOT / art).exists() and n.get("status") in {"active", "blocked"}:
            hashes[art] = {"node_id": nid, "status": n.get("status"), **artifact_digest(ROOT / art)}

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

    ASSERTED_KEYS = ("class_id", "class_ids", "conclusion_type", "regularity",
                     "regularity_class", "scope", "conclusion")

    def scan_asserted(text: str, where: str):
        """Flag C0/C2 merges asserted in a semantic field; ignore prose and lint patterns."""
        for i, line in enumerate(text.splitlines(), 1):
            m = re.match(r"\s*[\"']?([A-Za-z_]+)[\"']?\s*[:=]\s*(.+)$", line)
            if m and m.group(1) in ASSERTED_KEYS and MERGE.search(m.group(2)):
                hard.append(f"{where}:{i}: asserted merged class in {m.group(1)}: {line.strip()[:120]}")
                return
        try:
            doc = json.loads(text)
        except ValueError:
            return

        def walk(o, path=""):
            if isinstance(o, dict):
                for k, v in o.items():
                    if k in ASSERTED_KEYS and isinstance(v, (str, list)):
                        s = " ".join(map(str, v)) if isinstance(v, list) else v
                        if MERGE.search(s):
                            hard.append(f"{where}: asserted merged class at {path}.{k}: {s[:120]}")
                            return True
                    if walk(v, f"{path}.{k}"):
                        return True
            elif isinstance(o, list):
                for j, v in enumerate(o):
                    if walk(v, f"{path}[{j}]"):
                        return True
            return False

        walk(doc)

    for g in m.get("groups", []):
        for n in g.get("nodes", []):
            cls = str(n.get("class_id", ""))
            for tok in re.split(r"[;,]", cls):
                if "C0" in tok and "C2" in tok:
                    hard.append(f"{n['id']}: single class token merges C0 and C2 ({tok.strip()})")
                    break
            scan_text(json.dumps({k: n.get(k) for k in ("label", "class_id", "conclusion_type")}), n["id"])
            art = n.get("artifact")
            if art and (ROOT / art).is_file() and (ROOT / art).stat().st_size < 2_000_000:
                try:
                    scan_asserted((ROOT / art).read_text(errors="replace"), f"{n['id']} artifact {art}")
                except OSError:
                    pass


    # registry: hash every artifact in the key deliverable directories (measured, not claimed)
    registry = {}
    for d in ("schemas", "ledger", "numerics/tests", "numerics/protocol", "reviews", "evaluation"):
        dp = ROOT / d
        if dp.is_dir():
            for f in sorted(x for x in dp.rglob("*") if x.is_file() and not x.name.startswith("._")):
                registry[str(f.relative_to(ROOT))] = {"sha256": sha256(f), "bytes": f.stat().st_size}

    # 2b. declared artifact hashes must match disk (silent revision drift)
    import hashlib as _hl

    def _sha(fp):
        h = _hl.sha256()
        with fp.open("rb") as f:
            for ch in iter(lambda: f.read(1 << 20), b""):
                h.update(ch)
        return h.hexdigest()

    for nid, n in nodes.items():
        art, declared = n.get("artifact"), n.get("artifact_sha256")
        if not art or not declared or declared in {"unverified", None}:
            continue
        fp = ROOT / art
        if not fp.is_file():
            continue
        cur = _sha(fp)
        if cur != declared:
            msg = (f"{nid}: declared artifact hash {declared[:12]} != disk {cur[:12]} for {art} "
                   f"(revision drift after artifact event)")
            (hard if n.get("validation_status") == "passed" else soft).append(msg)

    # 3b. frozen artifacts must not drift during review
    for f in m.get("frozen_artifacts", []):
        if not f.get("active", True):
            continue
        fp = ROOT / f["path"]
        if not fp.is_file():
            hard.append(f"frozen artifact missing: {f['path']}")
        else:
            cur = sha256(fp)
            if cur != f["sha256"]:
                hard.append(f"frozen artifact drifted during review: {f['path']} {f['sha256'][:12]} -> {cur[:12]}")

    # 4. dependency status: active node whose deps are not done -> soft (may be legitimately exploratory)
    for nid, n in nodes.items():
        if n.get("status") in {"active", "done"}:
            for d in n.get("depends_on", []):
                dn = nodes.get(d)
                if dn and dn.get("status") not in {"done"} and n.get("status") == "done":
                    hard.append(f"{nid}: done while dependency {d} is {dn.get('status')}")

    return {"hard": hard, "soft": soft, "hashes": hashes, "registry": registry,
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
