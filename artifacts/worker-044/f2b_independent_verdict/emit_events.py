#!/usr/bin/env python3
"""Emit worker-044 W044-F2B-INDEP-VERDICT-01 events from report.json and write the worker
checkpoint. Validates every event against research_map/schemas.py before appending to
comms/outbox/worker-044.jsonl (the controller's ingest remains the only writer of
research_map/events.jsonl). Never sets a node status, validation_status=passed, or a gate verdict.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))
OUTBOX = ROOT / "comms" / "outbox" / "worker-044.jsonl"
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

CLASS = "AF-SCC-C0-VAC-GEN"
NODE = "F2b"
TASK = "W044-F2B-INDEP-VERDICT-01"
TARGET = "schemas/af_scc_c0_vacuum.yaml"


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main() -> int:
    rep_path = "artifacts/worker-044/f2b_independent_verdict/report.json"
    rep = json.loads((ROOT / rep_path).read_text())
    summ = rep["summary"]
    verdict = summ["verdict"]
    blocked = rep.get("moving_target") is not None
    pinned = rep.get("settled_revision") or {}
    pub_unsettled = rep.get("publication_unsettled")
    rep_sha = sha(ROOT / rep_path)
    stamp = datetime.now(CST).strftime("%Y%m%dT%H%M%S%z")

    fails = [c for c in rep.get("checks", []) if not c["ok"]]
    passes = [c for c in rep.get("checks", []) if c["ok"]]
    findings = "; ".join(f"{c['check_id']}={str(c['observed'])[:160]}" for c in fails[:8]) or "all checks passed"
    tool_note = ("; SCHEMA-AXIS: GATE-01/02/03/04, SEP-01..06, FIELD-01, SEM-01 all pass on the pinned snapshot. "
                 "TOOL-AXIS: class_separation.findings_for_text is blind to nested declaration fields and to WCC "
                 "conclusions (CS-03/04/05; positive controls CS-01/CS-02 pass) - a clean classsep result is not "
                 "load-bearing for nested-field class binding.")
    findings = findings + tool_note
    if pinned.get("canonical_sha256"):
        schema_axis = [c["check_id"] for c in rep.get("checks", [])
                       if c["check_id"].split("-")[0] in {"GATE", "SEP", "FIELD", "SEM"} and c["ok"]]
        summary_txt = (
            f"F2b independent class-binding verification at pinned schemas/af_scc_c0_vacuum.yaml "
            f"sha256 {pinned['canonical_sha256'][:16]} (FROZEN rev {pinned.get('frozen_revision')} declared pin at settle): "
            f"{len(passes)}/{summ['total']} checks pass, {len(schema_axis)} schema-axis checks pass "
            f"(structural gate + null/mutation controls, class separation, independent C0/C2 non-merge, quantifier/conclusion "
            f"assertions, semantic baseline). Verdict WITHHELD as inconclusive: publication binding "
            f"{'UNSETTLED (' + ','.join((pub_unsettled or {}).get('unsatisfied', [])) + ')' if pub_unsettled else 'settled'}, "
            f"and canonical bytes moved after the run (post-run target 55d0a1ea, snapshot 1bb78ce9). Independent findings: "
            f"(1) class_contract_pointer does not resolve in the AUTHORITATIVE canonical taxonomy (no class_contracts key; it "
            f"resolves only in the authoring tree), so the F2b contract binding is not machine-followable on the canonical path; "
            f"(2) the canonical class-separation TEXT scanner (findings_for_text) is blind to leaks in nested declaration fields "
            f"and to WCC conclusions (probes CS-03/04/05 miss; positive controls CS-01/CS-02 hit), so a clean classsep result is "
            f"not load-bearing evidence for nested-field class binding; (3) the pinned file carries 8 distinct duplicate top-level "
            f"revised_at keys (parser-dependent effective revision). Class-binding evidence only: no node transition, no gate "
            f"verdict, no validation_status=passed, no mathematics/physics claim."
        )
    else:
        summary_txt = (
            f"F2b independent class-binding verification did not reach a usable pin inside the bounded window "
            f"(FREEZE-UNSETTLED); blocker emitted. No verdict is bound to any transient revision."
        )

    events = []
    events.append({
        "event_id": f"w044-{stamp}-status-rescope", "event_type": "status", "created_at": now(),
        "actor": "worker-044", "node_id": NODE, "class_id": CLASS, "status": "active", "hours": 0.3,
        "task_id": TASK,
        "summary": ("Supersedes the reviewed_sha256 962f33c6... in w044-...-task-claim: that hash was a transient "
                    "mid-rewrite revision (canonical schemas were rewritten at 00:19:14). This run therefore gated on "
                    "freeze settlement before binding anything. " + summary_txt),
        "evidence_refs": [f"{rep_path}#{rep_sha[:16]}", "artifacts/formulation/FROZEN.json"],
        "next_falsifier": rep["falsifier"],
        "supersedes": "w044-2026-09-12T00:19:11+08:00-task-claim-f2b-indep",
    })
    events.append({
        "event_id": f"w044-{stamp}-artifact-report", "event_type": "artifact", "created_at": now(),
        "actor": "worker-044", "node_id": NODE, "class_id": CLASS,
        "artifact_type": "verification_report", "path": rep_path, "sha256": rep_sha,
        "validation_status": "unverified",
        "evidence_refs": [f"{rep_path}#{rep_sha[:16]}"],
        "falsifier": rep["falsifier"],
    })
    if pinned.get("canonical_sha256"):
        events.append({
            "event_id": f"w044-{stamp}-review-f2b", "event_type": "review", "created_at": now(),
            "actor": "worker-044", "reviewer": "worker-044", "node_id": NODE, "class_id": CLASS,
            "target_id": f"{TARGET}#{pinned['canonical_sha256'][:16]}",
            "verdict": verdict if verdict in {"accept", "revise", "reject", "inconclusive"} else "inconclusive",
            "score": summ["score"], "hard_failures": summ["hard_failures"], "findings": findings,
            "evidence_refs": [f"{rep_path}#{rep_sha[:16]}", f"{TARGET}#{pinned['canonical_sha256'][:16]}"],
            "scope": "class-binding/structural conformance at the pinned hash; not a theorem review, not a gate verdict",
        })
    events.append({
        "event_id": f"w044-{stamp}-claim-f2b", "event_type": "claim", "created_at": now(),
        "actor": "worker-044", "node_id": NODE, "class_id": CLASS, "conclusion_type": "formal_model",
        "statement": summary_txt,
        "assumptions": [
            "canonical path schemas/af_scc_c0_vacuum.yaml is the F2b authority and FROZEN.json its declared pin",
            "the pinned snapshot is byte-identical to the canonical bytes read once at settle time",
            "the canonical structural gate, class-separation checker and semantic baseline auditor are accepted as the repo's checkers",
            "mutation controls M1-M4 are valid negative controls for checker discriminating power",
        ],
        "falsifier": rep["falsifier"],
        "evidence_refs": [f"{rep_path}#{rep_sha[:16]}"]
        + ([f"{TARGET}#{pinned['canonical_sha256'][:16]}"] if pinned.get("canonical_sha256") else []),
        "artifact_refs": [f"{rep_path}#{rep_sha[:16]}"],
    })
    events.append({
        "event_id": f"w044-{stamp}-status-complete", "event_type": "status", "created_at": now(),
        "actor": "worker-044", "node_id": NODE, "class_id": CLASS,
        "status": "blocked" if blocked else "active", "hours": 0.6, "task_id": TASK,
        "summary": ("W044-F2B-INDEP-VERDICT-01 COMPLETE (bounded execution worker, exiting after checkpoint). "
                    + summary_txt + " Controller/audit lead still owns any gate use of this evidence."),
        "evidence_refs": [f"{rep_path}#{rep_sha[:16]}"],
        "next_falsifier": rep["falsifier"],
    })
    if blocked:
        events.append({
            "event_id": f"w044-{stamp}-blocker-freeze", "event_type": "blocker", "created_at": now(),
            "actor": "worker-044", "node_id": NODE, "class_id": CLASS,
            "description": ("FREEZE-UNSETTLED: F2b could not be bound to a stable published revision inside the bounded "
                            "window. " + json.dumps(rep["moving_target"]["observed"])[:600]),
            "needed_to_unblock": ("publish canonical == authoring == FROZEN pin for all four class artifacts (F0 taxonomy + "
                                  "F1/F2a/F2b schemas), then re-run verify_f2b.py at the settled revision"),
            "evidence_refs": [f"{rep_path}#{rep_sha[:16]}"],
        })

    for e in events:
        validate_event(e)
    OUTBOX.parent.mkdir(parents=True, exist_ok=True)
    with OUTBOX.open("a") as f:
        for e in events:
            f.write(json.dumps(e, sort_keys=True) + "\n")

    # ---- worker checkpoint (no global state mutation) ------------------------
    art = {}
    for rel in [rep_path, f"{TARGET}"]:
        p = ROOT / rel
        if p.is_file():
            art[rel] = {"sha256": sha(p)}
    for rel, h in [(pinned.get("snapshot_path"), pinned.get("snapshot_sha256")),
                   ("artifacts/worker-044/f2b_independent_verdict/verify_f2b.py", None)]:
        if rel and (ROOT / rel).is_file():
            art[rel] = {"sha256": h or sha(ROOT / rel)}
    ck = {
        "checkpoint": 1, "at": now(), "worker": "worker-044",
        "hours_spent_estimate": 0.6,
        "assignment": f"{TASK} (node {NODE}, class {CLASS}, gate G-FORM)",
        "status": {
            "freeze": "UNSETTLED" if blocked else ("PUBLICATION-BINDING-UNSETTLED" if pub_unsettled else "SETTLED"),
            "verdict": verdict, "score": summ["score"],
            "checks": f"{len(passes)}/{summ['total']} pass",
            "hard_failures": summ["hard_failures"],
            "pinned_sha256": pinned.get("canonical_sha256"),
            "frozen_revision": pinned.get("frozen_revision"),
            "no_completion_claim": "worker cannot set done/passed or a gate verdict; no theorem/physics result",
        },
        "artifacts": art,
        "falsifier": rep["falsifier"],
        "events_emitted": [e["event_id"] for e in events],
    }
    ckdir = ROOT / "runtime" / "state"
    ckdir.mkdir(parents=True, exist_ok=True)
    ckpath = ckdir / f"w044_checkpoint_{stamp}.json"
    ckpath.write_text(json.dumps(ck, indent=2, sort_keys=True))
    with (ckdir / "w044_checkpoints.jsonl").open("a") as f:
        f.write(json.dumps(ck, sort_keys=True) + "\n")
    print(json.dumps({"events": [e["event_id"] for e in events], "checkpoint": str(ckpath.relative_to(ROOT)),
                      "report_sha256": rep_sha, "verdict": verdict, "hard_failures": summ["hard_failures"]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
