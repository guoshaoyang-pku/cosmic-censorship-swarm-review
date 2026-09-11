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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import class_separation  # noqa: E402

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

    # 3. class separation (module: class_separation.py, regression-tested against
    # worker-07's 27-fixture falsification corpus at runtime/bin/classsep_regression.py)
    def _route(items):
        for it in items:
            (soft if str(it).startswith("CLASSSEP-SOFT:") else hard).append(it)

    _route(class_separation.findings_for_map(m))
    for g in m.get("groups", []):
        for n in g.get("nodes", []):
            art = n.get("artifact")
            if art and (ROOT / art).is_file() and (ROOT / art).stat().st_size < 2_000_000:
                try:
                    _route(class_separation.findings_for_text(
                        (ROOT / art).read_text(errors="replace"), f"{n['id']} artifact {art}"))
                except OSError:
                    pass

    # 3a. dual-tree check. mode="mirror": two trees of one artifact and must be byte-identical
    # at publish time. mode="companion": two DISTINCT artifacts (the declared F0 taxonomy and
    # its class-contract supplement); byte-identity is not required, not even possible without
    # destroying a frozen input (astra-life04 adjudication REC-3), so the pair is recorded via
    # publication_status and CF-7 instead of flagged here.
    MIRRORS = [
        ("research_map/formulation_taxonomy.yaml", "artifacts/formulation/formulation_taxonomy.yaml", "companion"),
        ("schemas/af_wcc_vacuum.yaml", "artifacts/formulation/schemas/af_wcc_vacuum.yaml", "mirror"),
        ("schemas/af_scc_c2_vacuum.yaml", "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml", "mirror"),
        ("schemas/af_scc_c0_vacuum.yaml", "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml", "mirror"),
    ]
    frozen_paths = {f["path"] for f in m.get("frozen_artifacts", []) if f.get("active", True)}
    for canon, author, mode in MIRRORS:
        cp, ap = ROOT / canon, ROOT / author
        if not (cp.is_file() and ap.is_file()):
            if mode == "companion":
                soft.append(f"companion pair incomplete: {canon} / {author}")
            continue
        if mode == "mirror" and sha256(cp) != sha256(ap):
            msg = (f"dual-tree divergence: {canon} ({sha256(cp)[:12]}) != {author} ({sha256(ap)[:12]}); "
                   f"publish the frozen revision to the canonical path")
            (hard if canon in frozen_paths else soft).append(msg)

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

    # registry: hash every artifact in the key deliverable directories (measured, not claimed).
    # runtime/state/controller_verification is included so controller-generated evidence (e.g.
    # the N0 replication run 6542db93eebc) is registered for PROTOCOL rule 2 (numerics C4).
    # pass-05 repair (worker-14 registration_coverage blocker + lead-numerics C4 blocker): the
    # scan roots now cover all of numerics/ (protocol, results, top-level docs and tools),
    # artifacts/numerics/ and the repo-root evaluation_rubric.yaml, so the C8 protocol accept
    # (1e6cdf04d7a2), the N0 stop-rule evidence (numerics/results/*) and the A0 rubric are
    # registered. __pycache__/.pyc are build debris, never evidence.
    registry = {}

    def _register(f: Path) -> None:
        registry[str(f.relative_to(ROOT))] = {"sha256": sha256(f), "bytes": f.stat().st_size}

    for d in ("schemas", "ledger", "numerics", "reviews", "evaluation",
              "artifacts/numerics", "runtime/state/controller_verification"):
        dp = ROOT / d
        if dp.is_dir():
            for f in sorted(x for x in dp.rglob("*")
                            if x.is_file() and not x.name.startswith("._")
                            and "__pycache__" not in x.parts and x.suffix != ".pyc"):
                _register(f)
    rubric = ROOT / "evaluation_rubric.yaml"
    if rubric.is_file():
        _register(rubric)

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
