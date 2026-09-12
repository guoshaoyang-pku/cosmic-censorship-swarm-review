#!/usr/bin/env python3
"""W085-CLAIM-RETIRE-04 — independent, read-only verification of claim-supersession
handling in the canonical controller ingest path and its effect on the evidence-audit
class-separation hard count.

Question (from the formulation lead's blocker leadform-blocker-20260912T003626, and
from a direct read of the frozen sources): when a `claim` event carries a
`supersedes_claim_event_id`, does `research_map/apply_events.py` retire or mark the
target claim, or does it append-only?  If append-only, how many live target claims
remain active merely because of that, and how many class-separation hard findings do
they contribute to the count the controller's evidence audit reports?

Method (freeze-first, following the worker-085 approval-binding probe):
  * all inputs are the immutable copies under ./snapshot/, whose hashes are checked
    against snapshot/manifest.json before and after every measurement;
  * `class_separation.py` and the claim branch / ingest dedup guard of
    `apply_events.py` are executed FROM THE FROZEN BYTES (no import of canonical
    modules, bytecode writes disabled);
  * every probe map is synthetic or an in-memory copy; no canonical file is written,
    and no patch is applied anywhere outside the probe process.

Exit codes: 0 all checks pass; 2 snapshot drift before starting; 3 one or more checks
failed.  This is instrument/tooling calibration evidence: it is not a mathematics or
physics claim, not a node completion, and not a gate verdict.
"""
from __future__ import annotations

import ast
import copy
import datetime
import hashlib
import importlib.util
import json
import sys
import textwrap
from pathlib import Path

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
SNAP = HERE / "snapshot"
ROOT = HERE.parents[2]  # <repo>/artifacts/worker-085/claim_retire -> <repo>
REPORT = HERE / "report.json"

CANONICAL = {
    "research_map/research_map.json": "map",
    "research_map/apply_events.py": "apply_events",
    "research_map/class_separation.py": "class_separation",
    "research_map/events.jsonl": "events",
}

CHECKS: list[dict] = []


def check(cid: str, desc: str, ok: bool, detail=None) -> bool:
    CHECKS.append({"id": cid, "desc": desc, "ok": bool(ok), "detail": detail})
    return bool(ok)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now_cst() -> str:
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def source_block(src: str, node) -> str:
    lines = src.splitlines()
    return textwrap.dedent("\n".join(lines[node.lineno - 1:node.end_lineno]))


def find_claim_branch(tree: ast.AST, src: str):
    """Verbatim body statements of `elif t == "claim":` inside apply_one()."""
    for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "apply_one"]:
        for node in ast.walk(fn):
            if not isinstance(node, ast.If):
                continue
            t = node.test
            if (isinstance(t, ast.Compare) and isinstance(t.left, ast.Name) and t.left.id == "t"
                    and len(t.ops) == 1 and isinstance(t.ops[0], ast.Eq)
                    and isinstance(t.comparators[0], ast.Constant) and t.comparators[0].value == "claim"):
                stmt = node.body[0]
                return source_block(src, stmt), stmt.lineno, stmt.end_lineno
    raise RuntimeError("claim branch not found")


def find_dedup_guard(tree: ast.AST, src: str):
    """Verbatim `if ev["event_id"] in applied_ids: ... continue` guard inside main()."""
    for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "main"]:
        for node in ast.walk(fn):
            if not isinstance(node, ast.If):
                continue
            s = ast.dump(node.test)
            if "applied_ids" in s and "event_id" in s:
                return source_block(src, node), node.lineno, node.end_lineno
    raise RuntimeError("dedup guard not found")


def supersede_target_id(claim: dict):
    for k in ("supersedes_claim_event_id", "supersedes"):
        v = claim.get(k)
        if isinstance(v, str) and v:
            return k, v
    return None, None


def per_claim_findings(cs, claim: dict, idx: int):
    return list(cs.findings(claim, f"claims[{idx}]", mode="prose"))


def hard_of(findings):
    return [f for f in findings if not str(f).startswith("CLASSSEP-SOFT:")]


def make_mock_env(branch_src: str):
    """Exec the verbatim branch body with only m/ev/now supplied."""
    ns = {"m": {"claims": []}, "ev": {}, "now": lambda: "2026-09-12T00:47:00+08:00"}
    exec(compile(branch_src, "<verbatim apply_events.py claim branch>", "exec"), ns)
    return ns


def make_replica(guard_src: str, branch_src: str):
    """Mini-replica of the ingest loop using the two verbatim blocks."""
    body = textwrap.indent(guard_src, " " * 8) + "\n" + textwrap.indent(branch_src, " " * 8)
    src = (
        "def _replica(events, m, now, applied_ids=None):\n"
        "    applied_ids = set(applied_ids or [])\n"
        "    skipped, applied = [], []\n"
        "    for ev in events:\n"
        f"{body}\n"
        "        applied_ids.add(ev['event_id'])\n"
        "        applied.append(ev['event_id'])\n"
        "    return applied_ids, applied, skipped\n"
    )
    ns = {}
    exec(compile(src, "<verbatim replay: guard + claim branch>", "exec"), ns)
    return ns["_replica"]


def retire_aware(target_id: str):
    """PROPOSAL ONLY (not applied): the minimal retirement marker this probe measures."""

    def _apply(m, ev, now):
        for c in m.get("claims", []):
            if c.get("event_id") == target_id and not c.get("retired"):
                c["retired"] = True
                c["superseded_by"] = ev.get("event_id")
                c["superseded_at"] = now()
        m.setdefault("claims", []).append({**ev, "promotion_status": "unpromoted", "received_at": now()})

    return _apply


PROPOSAL_PATCH_TEXT = (
    "--- a/research_map/apply_events.py\n"
    "+++ b/research_map/apply_events.py\n"
    "@@ elif t == \"claim\":\n"
    " elif t == \"claim\":\n"
    "+    _sup = ev.get(\"supersedes_claim_event_id\") or ev.get(\"supersedes\")\n"
    "+    if _sup:\n"
    "+        for _c in m.get(\"claims\", []):\n"
    "+            if _c.get(\"event_id\") == _sup and not _c.get(\"retired\"):\n"
    "+                _c[\"retired\"] = True\n"
    "+                _c[\"superseded_by\"] = ev[\"event_id\"]\n"
    "+                _c[\"superseded_at\"] = now()\n"
    "     m[\"claims\"].append({**ev, \"promotion_status\": \"unpromoted\",\n"
    "                         \"received_at\": now()})\n"
)


def main() -> int:
    generated_at = now_cst()
    result: dict = {
        "task_id": "W085-CLAIM-RETIRE-04",
        "actor": "worker-085",
        "generated_at": generated_at,
        "gate": "G-AUDIT",
        "node_id": "F0",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-VAC-GEN"],
        "verdict": "PENDING",
        "checks": CHECKS,
        "snapshot_dir": str(SNAP.relative_to(ROOT)),
        "proposal": {"applied": False, "patch_text": PROPOSAL_PATCH_TEXT},
        "falsifiers": [
            "F1: the verbatim claim branch mutates the target named by supersedes_claim_event_id "
            "(retired / superseded_by / status change), or any canonical revision already does so.",
            "F2: no claim in the frozen map carries a supersede field whose target is live and un-retired.",
            "F3: no live un-retired target contributes a class-separation hard finding; i.e. the "
            "counterfactual hard-count delta is zero.",
            "F4: the verbatim guard fails to skip a replayed event_id (ingest-level idempotence broken).",
            "F5: any snapshot byte changes during the run, or the manifest hashes do not match "
            "(measurement window void).",
            "F6: the reference retirement marker changes claim records other than its named target, "
            "or is not idempotent on replay.",
        ],
        "non_claims": [
            "No mathematics, physics or class-semantics claim is made; every statement is about tooling bytes.",
            "No node completion, validation_status or gate verdict is claimed; canonical files are unmodified.",
            "The retirement marker is a proposal for the tooling owner (CF-4); it is executed only on "
            "synthetic in-process maps.",
        ],
    }

    # ---------------- A. pins ----------------
    man_path = SNAP / "manifest.json"
    if not man_path.exists():
        print("FATAL: snapshot/manifest.json missing", file=sys.stderr)
        return 2
    manifest = json.loads(man_path.read_text())
    snap_ok, snap_bad = [], []
    for name, rec in sorted(manifest["snapshot"].items()):
        p = SNAP / name
        ok = p.is_file() and sha256(p) == rec["sha256"] and p.stat().st_size == rec["bytes"]
        (snap_ok if ok else snap_bad).append(name)
    if not check("A1", "snapshot bytes match snapshot/manifest.json at start", not snap_bad, {"ok": snap_ok, "bad": snap_bad}):
        result["verdict"] = "SNAPSHOT_DRIFT_AT_START"
        REPORT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        return 2

    live_now = {}
    drift = {}
    for rel, key in CANONICAL.items():
        live_now[key] = {"sha256": sha256(ROOT / rel), "bytes": (ROOT / rel).stat().st_size}
        drift[key] = live_now[key]["sha256"] != manifest["canonical_at_freeze"][rel]["sha256"]
    check("A2", "canonical paths hashed at start; drift vs freeze recorded (informational)",
          True, {"drift": drift, "live_now": live_now})
    result["live_now"] = live_now
    result["canonical_drift_vs_freeze"] = drift

    frozen_map = json.loads((SNAP / "research_map.json").read_text())
    cs = load_module(SNAP / "class_separation.py", "cs_085_snapshot")
    check("A3", "frozen class_separation loads; KNOWN_CLASSES is the four frozen ids",
          set(cs.KNOWN_CLASSES) == {"AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"},
          sorted(cs.KNOWN_CLASSES))

    ae_src = (SNAP / "apply_events.py").read_text()
    tree = ast.parse(ae_src)
    branch_src, b_lo, b_hi = find_claim_branch(tree, ae_src)
    guard_src, g_lo, g_hi = find_dedup_guard(tree, ae_src)
    check("A4", "verbatim claim branch extracted and contains no supersede/retire handling",
          "m[\"claims\"].append(" in branch_src and not any(t in branch_src for t in ("supersede", "retire", "retired")),
          {"lines": f"{b_lo}-{b_hi}", "text": branch_src, "sha256": hashlib.sha256(branch_src.encode()).hexdigest()})
    check("A5", "verbatim ingest dedup guard extracted (applied_ids / continue)",
          "applied_ids" in guard_src and "continue" in guard_src,
          {"lines": f"{g_lo}-{g_hi}", "text": guard_src, "sha256": hashlib.sha256(guard_src.encode()).hexdigest()})
    result["verbatim_blocks"] = {
        "claim_branch": {"lines": f"{b_lo}-{b_hi}", "sha256": hashlib.sha256(branch_src.encode()).hexdigest(), "text": branch_src},
        "dedup_guard": {"lines": f"{g_lo}-{g_hi}", "sha256": hashlib.sha256(guard_src.encode()).hexdigest(), "text": guard_src},
    }

    # ---------------- B. live census at the frozen revision ----------------
    claims = frozen_map.get("claims", [])
    superseders = []
    for i, c in enumerate(claims):
        field, tid = supersede_target_id(c)
        if field:
            superseders.append({"index": i, "successor": c.get("event_id"), "field": field, "target": tid,
                                "successor_created_at": c.get("created_at")})
    by_id = {c.get("event_id"): (i, c) for i, c in enumerate(claims)}
    for s in superseders:
        hit = by_id.get(s["target"])
        s["target_live"] = bool(hit)
        s["target_index"] = hit[0] if hit else None
        s["target_retired"] = bool(hit and (hit[1].get("retired") or hit[1].get("superseded_by")
                                            or str(hit[1].get("status", "")).lower() in {"superseded", "retired"}))
        s["successor_after_target"] = bool(hit and s["index"] > hit[0])
        if hit:
            fs = per_claim_findings(cs, hit[1], hit[0])
            s["target_hard_findings"] = hard_of(fs)
            s["target_all_findings"] = fs
        else:
            s["target_hard_findings"] = []
            s["target_all_findings"] = []
    live_unretired = [s for s in superseders if s["target_live"] and not s["target_retired"]]
    check("B1", "supersede-carrying claims exist in the frozen map and are enumerated",
          len(superseders) > 0, {"n_claims": len(claims), "n_superseders": len(superseders)})
    check("B2", "at least one supersede target is present in the map and NOT retired",
          len(live_unretired) > 0,
          [{"successor": s["successor"], "target": s["target"], "retired": s["target_retired"],
            "successor_after_target": s["successor_after_target"]} for s in superseders])
    hard_targets = [s for s in live_unretired if s["target_hard_findings"]]
    check("B3", "at least one live un-retired supersede target contributes a CLASSSEP hard finding",
          len(hard_targets) > 0,
          [{"target": s["target"], "successor": s["successor"], "n_hard": len(s["target_hard_findings"]),
            "findings": s["target_hard_findings"]} for s in hard_targets])

    all_findings = list(cs.findings_for_map(frozen_map))
    hard_all = hard_of(all_findings)
    soft_all = [f for f in all_findings if str(f).startswith("CLASSSEP-SOFT:")]
    check("B4", "frozen map class-separation count recorded (verbatim detector)",
          True, {"hard": len(hard_all), "soft": len(soft_all)})

    retired_target_ids = {s["target"] for s in hard_targets}
    stripped = copy.deepcopy(frozen_map)
    stripped["claims"] = [c for c in stripped["claims"] if c.get("event_id") not in retired_target_ids]
    stripped_findings = list(cs.findings_for_map(stripped))
    stripped_hard = hard_of(stripped_findings)
    delta = len(hard_all) - len(stripped_hard)
    check("B5", "removing the declared-superseded target claims lowers the map hard count by their finding count",
          delta == sum(len(s["target_hard_findings"]) for s in hard_targets) and delta > 0,
          {"hard_with_targets": len(hard_all), "hard_without": len(stripped_hard), "delta": delta,
           "removed_targets": sorted(retired_target_ids)})
    result["live_census"] = {
        "map_updated_at": frozen_map.get("updated_at"),
        "n_claims": len(claims),
        "n_superseders": len(superseders),
        "n_live_unretired_targets": len(live_unretired),
        "n_dangling_targets": sum(1 for s in superseders if not s["target_live"]),
        "n_live_unretired_targets_with_hard_findings": len(hard_targets),
        "hard_attributable_to_superseded_targets": sum(len(s["target_hard_findings"]) for s in hard_targets),
        "map_hard_total": len(hard_all),
        "map_soft_total": len(soft_all),
        "counterfactual_hard_after_removal": len(stripped_hard),
        "counterfactual_delta": delta,
        "superseders": superseders,
    }

    claim_events = [json.loads(l) for l in (SNAP / "claim_events.jsonl").read_text().splitlines() if l.strip()]
    ev_sup = [e for e in claim_events if supersede_target_id(e)[0]]
    applied = set(frozen_map.get("applied_event_ids", []))
    ev_sup_applied = [e for e in ev_sup if e.get("event_id") in applied]
    lead_cited = [e for e in claim_events if "supersede-20260912T003626" in str(e.get("event_id", ""))]
    check("B6", "frozen claim-event stream census: supersede events exist and at least one is applied",
          len(ev_sup) > 0 and len(ev_sup_applied) >= 1,
          {"n_claim_events": len(claim_events), "n_supersede_events": len(ev_sup),
           "n_applied": len(ev_sup_applied),
           "lead_cited_T003626_in_stream": len(lead_cited),
           "sample": [{"event_id": e.get("event_id"), "supersedes": supersede_target_id(e)[1]} for e in ev_sup[:8]]})
    result["event_stream_census"] = {
        "n_claim_events": len(claim_events),
        "n_supersede_claim_events": len(ev_sup),
        "n_supersede_claim_events_applied": len(ev_sup_applied),
        "lead_blocker_cited_event_present_in_stream": len(lead_cited) > 0,
    }

    # ---------------- C. verbatim branch controls ----------------
    m1 = {"claims": []}
    ev1 = {"event_id": "x-1", "event_type": "claim", "statement": "plain claim", "created_at": "t"}
    ns = {"m": m1, "ev": ev1, "now": lambda: "t-now"}
    exec(compile(branch_src, "<branch>", "exec"), ns)
    check("C1", "control: a supersede-free claim event appends exactly once and preserves fields",
          len(m1["claims"]) == 1 and m1["claims"][0]["statement"] == "plain claim"
          and m1["claims"][0]["promotion_status"] == "unpromoted",
          m1["claims"])

    target = {"event_id": "t-old", "statement": "old composite C0/C2 merged", "class_ids": ["AF-SCC-C0-VAC-GEN"]}
    m2 = {"claims": [copy.deepcopy(target)]}
    before = json.dumps(m2["claims"][0], sort_keys=True)
    ev2 = {"event_id": "t-new", "event_type": "claim", "statement": "rephrased successor",
           "supersedes_claim_event_id": "t-old", "created_at": "t"}
    ns2 = {"m": m2, "ev": ev2, "now": lambda: "t2-now"}
    exec(compile(branch_src, "<branch>", "exec"), ns2)
    after = json.dumps(m2["claims"][0], sort_keys=True)
    check("C2", "DEFECT REPRODUCED: supersede event appends the successor and leaves the named target unmutated",
          len(m2["claims"]) == 2 and before == after and m2["claims"][1]["supersedes_claim_event_id"] == "t-old",
          {"target_unchanged": before == after, "n_claims_after": len(m2["claims"]),
           "successor_fields": {k: m2["claims"][1].get(k) for k in ("event_id", "supersedes_claim_event_id", "promotion_status")}})

    m3 = {"claims": [copy.deepcopy(target)]}
    before3 = json.dumps(m3, sort_keys=True)
    ev3 = {"event_id": "t-dangling", "event_type": "claim", "statement": "dangling", "supersedes_claim_event_id": "nope"}
    ns3 = {"m": m3, "ev": ev3, "now": lambda: "t3-now"}
    exec(compile(branch_src, "<branch>", "exec"), ns3)
    check("C3", "control: dangling supersede target does not crash and does not mutate other claims",
          len(m3["claims"]) == 2 and json.dumps(m3["claims"][0], sort_keys=True) == json.dumps(target, sort_keys=True),
          {"n_claims_after": len(m3["claims"])})

    replica = make_replica(guard_src, branch_src)
    mr = {"claims": []}
    evs = [ev2, ev2]
    applied_ids, applied_list, skipped = replica(evs, mr, lambda: "t-now")
    check("C4", "control: verbatim dedup guard + claim branch is idempotent on a replayed event_id",
          len(applied_list) == 1 and len(skipped) == 1 and len(mr["claims"]) == 1,
          {"applied": applied_list, "skipped": skipped, "n_claims": len(mr["claims"])})

    m5 = {"claims": []}
    ns5 = {"m": m5, "ev": ev2, "now": lambda: "t5-now"}
    exec(compile(branch_src, "<branch>", "exec"), ns5)
    exec(compile(branch_src, "<branch>", "exec"), ns5)
    check("C5", "scope note: the branch alone has no dedup (guard is the sole idempotence mechanism)",
          len(m5["claims"]) == 2,
          {"n_claims_after_double_branch": len(m5["claims"])})

    # ---------------- D. reference retirement behavior (synthetic only) ----------------
    m6 = {"claims": [copy.deepcopy(target), {"event_id": "other", "statement": "untouched", "class_ids": ["AF-WCC-VAC-GEN"]}]}
    other_before = json.dumps(m6["claims"][1], sort_keys=True)
    ra = retire_aware("t-old")
    ra(m6, ev2, lambda: "t6-now")
    tgt = m6["claims"][0]
    check("D1", "proposal: retirement marker flags exactly the named target and its successor, nothing else",
          tgt.get("retired") is True and tgt.get("superseded_by") == "t-new" and tgt.get("superseded_at") == "t6-now"
          and json.dumps(m6["claims"][1], sort_keys=True) == other_before and len(m6["claims"]) == 3,
          {"target": tgt, "n_claims": len(m6["claims"])})
    ra(m6, ev2, lambda: "t6b-now")
    check("D2", "proposal is idempotent on the marker: replay does not rewrite superseded_at/superseded_by "
                "(successor dedup remains the ingest guard's job)",
          len(m6["claims"]) == 4 and tgt.get("superseded_at") == "t6-now" and tgt.get("superseded_by") == "t-new",
          {"n_claims": len(m6["claims"]), "target_superseded_at": tgt.get("superseded_at")})

    synth = {"claims": [copy.deepcopy(target), {"event_id": "other", "statement": "clean WCC claim",
                                                "class_ids": ["AF-WCC-VAC-GEN"]}], "groups": [], "portfolio_events": []}
    synth_hard_before = len(hard_of(cs.findings_for_map(synth)))
    for c in synth["claims"]:
        if c.get("event_id") == "t-old":
            c["retired"] = True
    kept = copy.deepcopy(synth)
    kept["claims"] = [c for c in kept["claims"] if not c.get("retired")]
    synth_hard_after = len(hard_of(cs.findings_for_map(kept)))
    check("D3", "proposal consumer counterfactual: excluding the retired claim lowers hard count by exactly 1",
          synth_hard_before - synth_hard_after == 1,
          {"hard_before": synth_hard_before, "hard_after": synth_hard_after})

    m8 = {"claims": [copy.deepcopy(target)]}
    before8 = json.dumps(m8, sort_keys=True)
    ev8 = {"event_id": "plain-2", "event_type": "claim", "statement": "plain"}
    retire_aware("unused")(m8, ev8, lambda: "t8-now")
    check("D4", "proposal negative control: supersede-free event retires nothing",
          json.dumps([m8["claims"][0]], sort_keys=True) == json.dumps([target], sort_keys=True) and len(m8["claims"]) == 2,
          {"first_claim_unchanged": json.dumps(m8["claims"][0], sort_keys=True) == json.dumps(target, sort_keys=True)})

    check("D5", "canonical apply_events.py is unmodified by this probe (proposal only)",
          sha256(ROOT / "research_map/apply_events.py") == manifest["canonical_at_freeze"]["research_map/apply_events.py"]["sha256"],
          {"live_apply_events_sha256": sha256(ROOT / "research_map/apply_events.py")})

    # ---------------- E. exit / drift ----------------
    snap_ok2, snap_bad2 = [], []
    for name, rec in sorted(manifest["snapshot"].items()):
        p = SNAP / name
        ok = p.is_file() and sha256(p) == rec["sha256"]
        (snap_ok2 if ok else snap_bad2).append(name)
    check("E1", "snapshot bytes unchanged at end (measurement window stable)", not snap_bad2,
          {"bad": snap_bad2})
    drift_end = {k: sha256(ROOT / rel) != manifest["canonical_at_freeze"][rel]["sha256"]
                 for rel, k in CANONICAL.items()}
    check("E2", "canonical live hashes re-measured at end; drift reported as observation only", True,
          {"drift": drift_end})
    result["canonical_drift_at_end"] = drift_end

    live_claim = {}
    with (ROOT / "research_map/events.jsonl").open("rb") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            try:
                d = json.loads(s)
            except Exception:
                continue
            if d.get("event_type") == "claim":
                live_claim[d.get("event_id")] = json.dumps(d, sort_keys=True, ensure_ascii=False)
    frozen_claim = {e.get("event_id"): json.dumps(e, sort_keys=True, ensure_ascii=False) for e in claim_events}
    missing = sorted(set(frozen_claim) - set(live_claim))
    changed = sorted(k for k in frozen_claim if k in live_claim and live_claim[k] != frozen_claim[k])
    check("E3", "frozen claim-event snapshot is a stable subset of the live stream (no claim-event rewrite)",
          not missing and not changed,
          {"frozen_claim_events": len(frozen_claim), "live_claim_events": len(live_claim),
           "missing": missing[:5], "changed": changed[:5]})

    n_pass = sum(1 for c in CHECKS if c["ok"])
    result["n_checks"] = len(CHECKS)
    result["n_pass"] = n_pass
    result["verdict"] = "CLAIM_RETIREMENT_GAP_REPRODUCED" if all(c["ok"] for c in CHECKS) else "CHECK_FAILURE"
    REPORT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(f"{result['verdict']}: {n_pass}/{len(CHECKS)} checks pass")
    for c in CHECKS:
        print(f"  [{'PASS' if c['ok'] else 'FAIL'}] {c['id']} {c['desc']}")
    return 0 if all(c["ok"] for c in CHECKS) else 3


if __name__ == "__main__":
    sys.exit(main())
