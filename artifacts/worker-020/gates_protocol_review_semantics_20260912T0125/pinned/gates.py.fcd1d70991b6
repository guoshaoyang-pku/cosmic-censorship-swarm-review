"""Gate evaluation and the hard lock on self-gravitating production (N1).

Enforces ``research_map.json#numerics_lock`` (Astra hard decision #2): while the
lock is ``locked``, no self-gravitating solver may be written or run.  Release
requires *all* of:

1. every gate in ``numerics_lock.required_gates`` (G-FORM, G-AUDIT) has
   ``verdict == "pass"`` with non-empty ``evidence_refs``;
2. every requirement in ``numerics_lock.additional_requirements`` is backed by
   machine-checkable evidence:
     * N0 measured order reported by ``numerics/tests/flat_wave.py`` and
       independently replicated by ``numerics/tests/flat_wave_replication.py``,
       the two agreeing within tolerance;
     * the numerical protocol reviewed by audit (a ``review`` event targeting
       the protocol or N0 with verdict ``accept`` from a reviewer that is not
       the author);
3. the lock state is not ``locked``.

The function is fail-closed: any missing, unreadable or hash-mismatched
evidence blocks production.  This module is imported by the N1 lock-guard
self-test; nothing here writes solver code.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

PROTOCOL_ARTIFACTS = (
    "numerics/CONVERGENCE_PROTOCOL.md",
    "numerics/tests/flat_wave.py",
    "numerics/tests/flat_wave_replication.py",
)
RESULT_FILES = (
    "numerics/results/flat_wave_convergence.json",
    "numerics/results/flat_wave_replication.json",
    "artifacts/numerics/n0/lead_calibration_report.json",
)
PROTOCOL_PATH = PROTOCOL_ARTIFACTS[0]
ORDER_AGREEMENT_TOL = 0.35  # absolute difference in measured order accepted as agreement


class ProductionLocked(RuntimeError):
    """Raised when N1 (self-gravitating) work is attempted while locked."""


def sha256_file(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_map(root: Path = REPO_ROOT) -> dict:
    return json.loads((root / "research_map" / "research_map.json").read_text())


def load_event_stream(root: Path = REPO_ROOT) -> list[dict]:
    """All events visible to a lead: accepted stream plus every outbox/inbox file."""
    events: list[dict] = []
    sources = [root / "research_map" / "events.jsonl"]
    for folder in (root / "comms" / "outbox", root / "comms" / "inbox"):
        if folder.is_dir():
            sources.extend(sorted(folder.rglob("*.jsonl")))
    for p in sources:
        if not p.is_file():
            continue
        for line in p.read_text(errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                doc = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(doc, dict):
                events.append(doc)
    return events


def _gate_report(m: dict, events: list[dict]) -> dict:
    out = {}
    for g in m.get("gates", []):
        gid = g.get("gate_id")
        if not gid:
            continue
        passed_evidence = [
            e
            for e in events
            if e.get("event_type") == "gate"
            and e.get("gate_id") == gid
            and e.get("verdict") == "pass"
        ]
        out[gid] = {
            "scope": g.get("scope"),
            "verdict": g.get("verdict"),
            "criteria": g.get("criteria"),
            "map_evidence_refs": g.get("evidence_refs", []),
            "passing_gate_events": [e.get("event_id") for e in passed_evidence],
            "satisfied": g.get("verdict") == "pass" and bool(g.get("evidence_refs") or passed_evidence),
        }
    return out


def _primary_orders(doc: dict, rel: str) -> list[float]:
    """Extract the *order-2* measured orders that the agreement test compares.

    Mixing the order-2 and order-4 studies into one mean would compare apples to
    oranges (the implementation report contains both), so extraction is
    scheme-aware per report shape.
    """
    out: list[float] = []

    def add(v):
        if isinstance(v, (int, float)) and v == v:
            out.append(float(v))

    if not isinstance(doc, dict):
        return out
    if rel.endswith("flat_wave_convergence.json"):
        for s in doc.get("studies", []) or []:
            if isinstance(s, dict) and s.get("order_scheme") == 2:
                for v in s.get("order_l2", []) or []:
                    add(v)
    elif rel.endswith("flat_wave_replication.json"):
        res = doc.get("result") or {}
        ind = res.get("independent_orders") or {}
        for v in ind.values():
            add(v)
    elif rel.endswith("lead_calibration_report.json"):
        studies = doc.get("studies") or {}
        if isinstance(studies, dict):
            for s in studies.get("cartesian_mms", []) or []:
                if isinstance(s, dict) and s.get("order_scheme") == 2:
                    for v in s.get("orders", []) or []:
                        add(v)
            sph = studies.get("spherical_mms") or {}
            if isinstance(sph, dict):
                for v in sph.get("orders_psi", []) or []:
                    add(v)
    return out


def primary_order_summary(root: Path = REPO_ROOT) -> dict:
    """Mean primary (order-2) measured order per report, for checkpoints and gates."""
    summary = {}
    for rel in RESULT_FILES:
        p = root / rel
        doc = None
        if p.is_file():
            try:
                doc = json.loads(p.read_text())
            except (OSError, json.JSONDecodeError):
                doc = None
        vals = _primary_orders(doc, rel) if doc is not None else []
        summary[rel] = {
            "present": doc is not None,
            "mean_order": (sum(vals) / len(vals)) if vals else None,
            "samples": len(vals),
        }
    return summary


def _n0_evidence(root: Path, events: list[dict]) -> dict:
    art = root / "numerics" / "tests" / "flat_wave.py"
    rep = root / "numerics" / "tests" / "flat_wave_replication.py"
    art_events = [
        e
        for e in events
        if e.get("event_type") == "artifact"
        and str(e.get("path", "")).endswith(("flat_wave.py", "flat_wave_replication.py"))
    ]
    hashes = {}
    for p in (art, rep):
        rel = str(p.relative_to(root))
        rec = {"exists": p.is_file()}
        if rec["exists"]:
            rec["sha256"] = sha256_file(p)
            ev = [e for e in art_events if str(e.get("path", "")).endswith(p.name)]
            rec["artifact_event"] = bool(ev)
            rec["artifact_event_passed"] = any(
                e.get("validation_status") == "passed" for e in ev
            )
            rec["event_sha256_match"] = any(e.get("sha256") == rec["sha256"] for e in ev)
        else:
            rec.update({"sha256": None, "artifact_event": False, "artifact_event_passed": False,
                        "event_sha256_match": False})
        hashes[rel] = rec

    results = {}
    for rel in RESULT_FILES:
        p = root / rel
        if not p.is_file():
            continue
        try:
            doc = json.loads(p.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        vals = _primary_orders(doc, rel)
        if vals:
            results[rel] = vals

    return {"artifacts": hashes, "order_reports": results}


def _order_agreement(n0: dict) -> dict:
    """Compare measured orders across implementation/replication reports."""
    flat = {
        rel: (sum(vals) / len(vals))
        for rel, vals in n0["order_reports"].items()
        if vals
    }
    impl = flat.get("numerics/results/flat_wave_convergence.json")
    repl = flat.get("numerics/results/flat_wave_replication.json")
    agreed = None
    delta = None
    if impl is not None and repl is not None:
        delta = abs(impl - repl)
        agreed = delta <= ORDER_AGREEMENT_TOL
    return {"implemented_order": impl, "replicated_order": repl, "delta": delta,
            "tolerance": ORDER_AGREEMENT_TOL, "agreed": agreed,
            "all_reports": flat}


PROTOCOL_REVIEW_TARGETS = (
    "numerics/CONVERGENCE_PROTOCOL.md",
    "G-NUM-protocol",
    "N0",
)
PROTOCOL_REVIEW_SELF = "astra-lead-numerics"


def _review_cited_hashes(e: dict) -> list[str]:
    """Every protocol hash a review event cites: explicit fields plus evidence_refs pins.

    Both conventions are in use.  Some events set ``reviewed_sha256`` to the protocol hash;
    others (e.g. audit-review-gnum-protocol-final-20260912T0027) carry the *review file's* own
    hash in ``artifact_sha256`` and pin the protocol only through an evidence_ref of the form
    ``numerics/CONVERGENCE_PROTOCOL.md#<hash>``.  Taking the union avoids silently discarding a
    binding verdict; a review counts if ANY cited hash matches the protocol on disk.
    """
    out: list[str] = []
    for k in ("reviewed_sha256", "artifact_sha256", "reviewed_protocol_hash"):
        v = e.get(k)
        if isinstance(v, str) and len(v.strip()) >= 12:
            out.append(v.strip().lower())
    for ref in e.get("evidence_refs", []) or []:
        if not isinstance(ref, str):
            continue
        for sep in ("#sha256:", "#"):
            if ref.startswith(PROTOCOL_PATH + sep):
                h = ref.split(sep, 1)[1].strip().lower()
                if len(h) >= 12:
                    out.append(h)
    return out


def _targets_protocol(target: str) -> bool:
    t = target.strip()
    for cand in PROTOCOL_REVIEW_TARGETS:
        if t == cand or t.startswith(cand + "#") or t.startswith(cand + "@"):
            return True
    return False


def _protocol_review(events: list[dict], protocol_sha: str | None = None) -> dict:
    """Independent review state of the protocol of record.

    A review binds only if it (a) has event_type review, (b) names the protocol via
    ``PROTOCOL_REVIEW_TARGETS`` with or without a ``#``/``@`` pin, (c) cites a hash that
    prefix-matches the protocol currently on disk -- a verdict at a superseded revision is
    advisory only -- and (d) is not authored by the protocol owner (no self-review).

    Accepts and dissents are reported separately, deduplicated by event_id across the accepted
    stream and the outbox copies of the same event.  This is fail-closed: an uncited, stale, or
    self-authored verdict never turns the criterion green, and a live revise/reject at the
    current hash marks the protocol contested.
    """
    accepts: list[str] = []
    dissents: list[dict] = []
    advisory: list[dict] = []
    seen: set[str] = set()
    target = (protocol_sha or "").lower()
    for e in events:
        if e.get("event_type") != "review":
            continue
        verdict = e.get("verdict")
        if verdict not in ("accept", "revise", "reject"):
            continue
        if not _targets_protocol(str(e.get("target_id", ""))):
            continue
        if e.get("reviewer") == PROTOCOL_REVIEW_SELF:
            continue
        eid = str(e.get("event_id") or id(e))
        if eid in seen:
            continue
        seen.add(eid)
        cited = _review_cited_hashes(e)
        binds = bool(target) and any(
            target.startswith(c) or c.startswith(target) for c in cited
        )
        if not binds:
            advisory.append({"event_id": e.get("event_id"), "verdict": verdict,
                             "cited": cited, "reviewer": e.get("reviewer")})
            continue
        if verdict == "accept":
            accepts.append(e.get("event_id"))
        else:
            dissents.append({"event_id": e.get("event_id"), "verdict": verdict,
                             "reviewer": e.get("reviewer")})
    return {
        "reviewed": bool(accepts),
        "accepting_reviews": accepts,
        "dissenting_reviews": dissents,
        "contest": bool(dissents),
        "advisory_reviews_at_other_hashes": advisory,
        "protocol_sha256_measured": protocol_sha,
        "reviewed_protocol_sha256": protocol_sha if accepts else None,
    }


def evaluate(root: Path = REPO_ROOT) -> dict:
    m = load_map(root)
    events = load_event_stream(root)
    lock = m.get("numerics_lock", {}) or {}
    gates = _gate_report(m, events)
    required = list(lock.get("required_gates", []))
    gate_ok = {g: bool(gates.get(g, {}).get("satisfied")) for g in required}
    n0 = _n0_evidence(root, events)
    agreement = _order_agreement(n0)
    protocol_file = root / PROTOCOL_PATH
    protocol_sha = sha256_file(protocol_file) if protocol_file.is_file() else None
    protocol = _protocol_review(events, protocol_sha)

    reasons: list[str] = []
    if lock.get("state", "locked") == "locked":
        reasons.append("numerics_lock.state == 'locked' (release authority: astra)")
    for g, ok in gate_ok.items():
        if not ok:
            reasons.append(f"required gate {g} not satisfied")
    for rel, rec in n0["artifacts"].items():
        if not rec.get("exists"):
            reasons.append(f"N0 artifact missing: {rel}")
        elif not rec.get("artifact_event_passed"):
            reasons.append(f"N0 artifact has no passing artifact event: {rel}")
        elif not rec.get("event_sha256_match"):
            reasons.append(f"N0 artifact event hash does not match disk: {rel}")
    if not agreement["agreed"]:
        if agreement["implemented_order"] is None or agreement["replicated_order"] is None:
            reasons.append("N0 measured order missing implementation and/or replication report")
        else:
            reasons.append(
                f"N0 measured orders disagree beyond {ORDER_AGREEMENT_TOL}: "
                f"{agreement['implemented_order']:.3f} vs {agreement['replicated_order']:.3f}"
            )
    if not protocol["reviewed"]:
        reasons.append("numerical protocol has no independent accepting review at the current hash")
    if protocol["contest"]:
        reasons.append(
            "numerical protocol is contested at the current hash by: "
            + ", ".join(f"{d['event_id']}({d['verdict']}, {d['reviewer']})"
                        for d in protocol["dissenting_reviews"])
        )

    report = {
        "evaluated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "map_updated_at": m.get("updated_at"),
        "lock": {"state": lock.get("state"), "required_gates": required,
                 "additional_requirements": lock.get("additional_requirements", []),
                 "allowed_nodes": lock.get("allowed_nodes", []),
                 "locked_nodes": lock.get("locked_nodes", [])},
        "gates": gates,
        "gate_ok": gate_ok,
        "n0_evidence": n0,
        "order_agreement": agreement,
        "protocol_review": protocol,
        "production_allowed": not reasons,
        "blocking_reasons": reasons,
        "verdict": "N1_ALLOWED" if not reasons else "N1_BLOCKED",
    }
    return report


def ensure_n1_allowed(root: Path = REPO_ROOT) -> dict:
    """Fail-closed guard.  Raise :class:`ProductionLocked` unless N1 is released."""
    rep = evaluate(root)
    if not rep["production_allowed"]:
        raise ProductionLocked(
            "self-gravitating production (N1) is locked; blocking reasons: "
            + "; ".join(rep["blocking_reasons"])
        )
    return rep


def _emit_blockers(rep: dict, root: Path) -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from numerics.events import emit_blocker

    emit_blocker(
        node_id="N1",
        description=(
            "Self-gravitating production (N1) is locked: "
            + "; ".join(rep["blocking_reasons"])
        ),
        needed_to_unblock=(
            "Release checklist (research_map.json#numerics_lock): G-FORM pass, G-AUDIT pass, "
            "N0 order measured AND independently replicated within tolerance, numerical protocol "
            "reviewed by audit, lock state released by astra (escalation: human-pi). "
            "No self-gravitating solver code has been written by the numerics group."
        ),
        evidence_refs=[
            "research_map/research_map.json#numerics_lock",
            "numerics/blockers.md",
            "artifacts/numerics/gate_report.json",
        ],
        root=root,
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="N1 lock guard / gate check")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--pretty", action="store_true")
    ap.add_argument("--emit-blocker", action="store_true")
    ap.add_argument("--write-report", action="store_true")
    ap.add_argument("--root", default=str(REPO_ROOT))
    a = ap.parse_args()
    root = Path(a.root)
    rep = evaluate(root)
    if a.write_report:
        out = root / "artifacts" / "numerics" / "gate_report.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(rep, indent=2, sort_keys=True))
    if a.emit_blocker and not rep["production_allowed"]:
        _emit_blockers(rep, root)
    print(json.dumps(rep, indent=2 if a.pretty else None, sort_keys=True))
    sys.exit(0 if rep["production_allowed"] else 3)
