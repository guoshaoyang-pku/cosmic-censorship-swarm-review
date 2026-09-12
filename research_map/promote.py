"""Claim promotion engine.

A claim is never promoted by fluency, by an agent's summary, or by HTTP success.
This module computes, per claim, whether the declared evidence satisfies the bar for
its conclusion_type, and records promotion_status + blocking reasons in the map.

Bars (conservative; a gate pass is always required for the class scope):
  open_problem        : artifact exists
  formal_model        : artifact exists + 1 review verdict
  numerical_evidence  : artifact exists + 1 review verdict + replication evidence path
  conditional_theorem : artifact exists + >=2 accept verdicts + gate pass
  theorem             : artifact exists + >=2 accept verdicts + gate pass + declared proof artifact
  counterexample      : artifact exists + >=2 accept verdicts (or controller adjudication)

Promotion is idempotent and never downgrades a controller-set status.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BARS = {
    "open_problem": {"reviews": 0, "gate": False, "replication": False},
    "formal_model": {"reviews": 1, "gate": False, "replication": False},
    "numerical_evidence": {"reviews": 1, "gate": False, "replication": True},
    "conditional_theorem": {"reviews": 2, "gate": True, "replication": False},
    "theorem": {"reviews": 2, "gate": True, "replication": False},
    "counterexample": {"reviews": 2, "gate": False, "replication": False},
    "stability_result": {"reviews": 2, "gate": True, "replication": False},
}
GATE_FOR_CLASS = {
    "AF-WCC-VAC-GEN": "G-FORM",
    "AF-SCC-C2-VAC-GEN": "G-FORM",
    "AF-SCC-C0-VAC-GEN": "G-FORM",
    "AF-WCC-SCALAR-SPH": "G-NUM",
}


def _accepts_for(reviews, artifact_refs, class_id, node_id=None, claim_id=None):
    n = 0
    for r in reviews:
        if r.get("verdict") != "accept":
            continue
        tid = str(r.get("target_id", ""))
        if claim_id and tid == claim_id:
            n += 1
            continue
        if any(tid and tid in str(a) for a in artifact_refs) or (node_id and tid == node_id) \
           or any(str(a).startswith(tid) for a in artifact_refs):
            n += 1
    return n


def _controller_adjudicated(reviews, claim_id):
    return any(r.get("verdict") == "accept" and str(r.get("reviewer")) == "astra"
               and str(r.get("target_id")) == str(claim_id) for r in reviews)


def evaluate(m: dict) -> dict:
    gates = {g["gate_id"]: g.get("verdict") for g in m.get("gates", [])}
    reviews = m.get("reviews", [])
    counts = {"promoted": 0, "blocked": 0, "recorded": 0}
    for c in m.get("claims", []):
        ct = c.get("conclusion_type", "open_problem")
        bar = BARS.get(ct, BARS["open_problem"])
        artifact_refs = [str(a) for a in (c.get("artifact_refs") or [])]
        art_refs = artifact_refs + [str(x) for x in (c.get("evidence_refs") or [])]
        existing, stale = [], []
        import hashlib as _hl

        def _digest(fp):
            h = _hl.sha256()
            with fp.open("rb") as f:
                for ch in iter(lambda: f.read(1 << 20), b""):
                    h.update(ch)
            return h.hexdigest()

        for a in artifact_refs:
            path_part, _, frag = str(a).partition("#")
            frag = frag.replace("sha256:", "").strip()
            p = ROOT / path_part if path_part else None
            if p and p.exists():
                if frag and not _digest(p).startswith(frag):
                    stale.append(f"{path_part} referenced revision {frag[:12]} is superseded (disk {_digest(p)[:12]})")
                else:
                    existing.append(path_part)
        reasons = []
        if not artifact_refs:
            reasons.append("claim has no artifact_refs (evidence_refs are not artifacts)")
        elif not existing:
            reasons.append("no artifact_refs resolving to a current file on disk")
        reasons += stale
        if _controller_adjudicated(reviews, c.get("event_id")):
            c["promotion_status"] = "controller_adjudicated"
            c["promotion_note"] = "controller review accepted; see reviews with reviewer=astra"
            counts["promoted"] += 1
            continue
        n_acc = _accepts_for(reviews, art_refs, c.get("class_id"), c.get("node_id"), c.get("event_id"))
        if n_acc < bar["reviews"]:
            reasons.append(f"{n_acc}/{bar['reviews']} independent accept verdicts")
        if bar["gate"]:
            gid = GATE_FOR_CLASS.get(str(c.get("class_id", "")).upper())
            if ct == "conditional_theorem" and not gid:
                gid = "G-LIT"
            v = gates.get(gid) if gid else None
            if gid and v != "pass":
                reasons.append(f"gate {gid} is {v or 'absent'}")
            elif not gid:
                reasons.append("no gate maps to this class")
        if bar["replication"]:
            rep = [p for p in existing if "replic" in p.lower() or "verif" in p.lower()]
            if not rep:
                reasons.append("no replication/verification artifact referenced")
        if ct == "theorem" and not any("proof" in p.lower() or "lean" in p.lower() for p in existing):
            reasons.append("no proof artifact referenced")
        if c.get("promotion_status") == "controller_adjudicated":
            continue
        if reasons:
            c["promotion_status"] = "promotion_blocked"
            c["promotion_blockers"] = reasons
            counts["blocked"] += 1
        elif bar["reviews"] == 0 and ct in {"open_problem", "formal_model"}:
            c["promotion_status"] = "recorded"
            c["promotion_note"] = "low-bar claim recorded with artifact; not a theorem"
            counts["recorded"] += 1
        else:
            c["promotion_status"] = "promoted"
            c["promotion_note"] = "bar satisfied for conclusion_type " + ct
            counts["promoted"] += 1
    return counts
