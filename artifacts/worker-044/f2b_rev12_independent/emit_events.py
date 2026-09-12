#!/usr/bin/env python3
"""Emit W044-F2B-REV12-INDEP-02 events + checkpoint. Idempotent by event_id:
re-running skips event_ids already present in the outbox (duplicate-safe)."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
OUT = ROOT / "artifacts/worker-044/f2b_rev12_independent"
OUTBOX = ROOT / "comms/outbox/worker-044.jsonl"
STATE = ROOT / "runtime/state"
TZ = timezone(timedelta(hours=8))
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def now() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def main() -> int:
    rep = OUT / "report.json"
    harness = OUT / "verify_c0_rev12.py"
    report = json.loads(rep.read_text())
    rep_sha = sha(rep)
    harness_sha = sha(harness)
    snap = ROOT / report["snapshot"]
    snap_sha = sha(snap)
    target = report["target_sha256"]
    f0 = report["pins_t0"]["research_map/formulation_taxonomy.yaml"]["sha256"]
    fz = report["pins_t0"]["artifacts/formulation/FROZEN.json"]["sha256"]
    ev = report["pins_t0"]["artifacts/formulation/evidence/taxonomy_consistency.json"]["sha256"]
    ts = now()
    stamp = datetime.now(TZ).strftime("%Y%m%dT%H%M%S%z")
    falsifier = report["falsifier"]

    findings = [
        {"id": "HF-044-BIND-05", "severity": "hard", "axis": "evidence binding",
         "finding": "f0_binding.consistency_evidence_sha256=675a99d0d25b does not resolve at the declared "
                    "canonical path artifacts/formulation/evidence/taxonomy_consistency.json: the live bytes "
                    "measure 9e335e9b and FROZEN rev28 pins 9e335e9b. The bytes that carry the declared hash "
                    "exist on disk only as another worker's pinned snapshot and differ structurally "
                    "(extra keys map_taxonomy_sha256, lead_contract_sha256, measured_at).",
         "detector": "BIND-05 in report.json", "falsifier": "exhibit the declared hash at the declared path"},
        {"id": "PASS-AXIS", "severity": "info", "axis": "class binding",
         "finding": "class_id == pointer anchor == canonical taxonomy classes key; canonical pointer resolves; "
                    "supplement pointer resolves; declared_f0_sha256 == measured rev5 F0; FROZEN pins both C0 "
                    "paths to the measured bytes; conclusion/regularity/genericity tokens equivalent under "
                    "VOCAB_ALIASES; no C0/C2 merge (C2 anti-scope + declared disjoint sibling); canonical "
                    "check_class_schema.py exit 0 on the snapshot; class_separation nested and text scans clean.",
         "detector": "BIND-01..04, AXIS-01..03, NOMERGE-01, GATE-01, SEP-01/02"},
        {"id": "PROBE-01", "severity": "soft-tool", "axis": "class-separation tool coverage",
         "finding": "class_separation.findings_for_text returns 0 findings for an explicit merge assertion "
                    "phrased only with full class ids (AF-SCC-C0-VAC-GEN identical to AF-SCC-C2-VAC-GEN, 'one "
                    "and the same class') because _MERGE_PAT only matches literal C0/C2 composites; a clean "
                    "text-scanner result is not load-bearing for class-id-phrased merges (consistent with "
                    "W044-F2B-INDEP-VERDICT-01 CLASSSEP-TEXT-NESTED-BLINDSPOT).",
         "detector": "PROBE-01 in report.json (informational, not a pass/fail control)"},
        {"id": "REVIEW-01", "severity": "info", "axis": "review coverage",
         "finding": "the schema's self-declared review_status at these bytes is independent_reviewers=[] and "
                    "verdict=pending; this worker verdict is one advisory second-verdict candidate at the "
                    "frozen hash, not a gate verdict.",
         "detector": "REVIEW-01 in report.json"},
    ]

    def event(eid, etype, **kw):
        o = {"event_id": eid, "event_type": etype, "created_at": ts, "actor": "worker-044"}
        o.update(kw)
        validate_event(o)
        return o

    events = [
        event(
            f"w044-rev12-{stamp}-task-claim", "status", node_id="F2b", gate="G-FORM",
            class_id="AF-SCC-C0-VAC-GEN", status="active", hours=0.1,
            summary="Taking one bounded class-bound task (no inbox card exists for worker-044): "
                    "W044-F2B-REV12-INDEP-02 = independent class-binding verification of F2b "
                    "AF-SCC-C0-VAC-GEN at the live frozen rev12 bytes schemas/af_scc_c0_vacuum.yaml "
                    f"sha256 {target[:16]} (FROZEN rev {report['settled_revision']['frozen_revision']}), "
                    "re-checking the W044-F2B-INDEP-VERDICT-01 findings at the repaired revision. Does not "
                    "claim node completion, a gate verdict, or any physics/mathematics result.",
            evidence_refs=[f"schemas/af_scc_c0_vacuum.yaml#{target[:12]}", f"artifacts/formulation/FROZEN.json#{fz[:12]}"],
            next_falsifier=falsifier),
        event(
            f"w044-rev12-{stamp}-artifact-report", "artifact", node_id="F2b",
            class_id="AF-SCC-C0-VAC-GEN", artifact_type="independent_class_binding_verification",
            path="artifacts/worker-044/f2b_rev12_independent/report.json", sha256=rep_sha,
            validation_status="unverified",
            evidence_refs=[f"artifacts/worker-044/f2b_rev12_independent/report.json#{rep_sha[:12]}",
                           f"schemas/af_scc_c0_vacuum.yaml#{target[:12]}"]),
        event(
            f"w044-rev12-{stamp}-artifact-harness", "artifact", node_id="F2b",
            class_id="AF-SCC-C0-VAC-GEN", artifact_type="verification_harness",
            path="artifacts/worker-044/f2b_rev12_independent/verify_c0_rev12.py", sha256=harness_sha,
            validation_status="unverified",
            evidence_refs=[f"artifacts/worker-044/f2b_rev12_independent/verify_c0_rev12.py#{harness_sha[:12]}",
                           f"{report['snapshot']}#{snap_sha[:12]}"]),
        event(
            f"w044-rev12-{stamp}-review-f2b", "review", node_id="F2b", target_id="AF-SCC-C0-VAC-GEN",
            reviewer="worker-044", verdict="revise", score=4.0,
            gate="G-FORM", target_sha256=target,
            hard_failures=["HF-044-BIND-05"],
            findings=findings,
            evidence_refs=[f"artifacts/worker-044/f2b_rev12_independent/report.json#{rep_sha[:12]}",
                           f"schemas/af_scc_c0_vacuum.yaml#{target[:12]}",
                           f"artifacts/formulation/evidence/taxonomy_consistency.json#{ev[:12]}"],
            falsifier=falsifier),
        event(
            f"w044-rev12-{stamp}-claim-f2b", "claim", node_id="F2b", class_id="AF-SCC-C0-VAC-GEN",
            gate="G-FORM", conclusion_type="formal_model",
            statement="Independent machine-checked class-binding measurement at frozen rev12 "
                      f"schemas/af_scc_c0_vacuum.yaml#{target[:12]} (FROZEN rev "
                      f"{report['settled_revision']['frozen_revision']}, declared F0 rev5 {f0[:12]}): 17/19 "
                      "checks pass with 8/8 mutation/text controls discriminating and no pin drift. Class "
                      "identity is clean: class_id == canonical pointer anchor, pointer resolves in the "
                      "canonical taxonomy, supplement pointer resolves, declared_f0_sha256 matches measured "
                      "F0, conclusion/regularity/genericity axes are VOCAB-equivalent, no C0/C2 merge, "
                      "canonical structural gate exit 0, class_separation nested+text scans clean. One hard "
                      "binding defect stands: f0_binding.consistency_evidence_sha256=675a99d0 does not "
                      "resolve at the declared canonical evidence path (live=9e335e9b=FROZEN rev28 pin). "
                      "Advisory worker verdict: revise.",
            assumptions=["the canonical bytes at the measured sha256 are the F2b authority and FROZEN rev28 its declared pin",
                         "the canonical check_class_schema.py, class_separation.py and VOCAB_ALIASES.json are the repo's checkers",
                         "mutants MUT-1..MUT-6 and class-separation texts MUT-7/8 are valid negative/positive controls"],
            falsifier=falsifier,
            evidence_refs=[f"artifacts/worker-044/f2b_rev12_independent/report.json#{rep_sha[:12]}",
                           f"schemas/af_scc_c0_vacuum.yaml#{target[:12]}",
                           f"research_map/formulation_taxonomy.yaml#{f0[:12]}"],
            artifact_refs=["artifacts/worker-044/f2b_rev12_independent/report.json",
                           "artifacts/worker-044/f2b_rev12_independent/verify_c0_rev12.py"]),
        event(
            f"w044-rev12-{stamp}-blocker-evidence", "blocker", node_id="F2b",
            class_id="AF-SCC-C0-VAC-GEN", gate="G-FORM",
            description="G-FORM acceptance of F2b at rev12 is blocked by one hard evidence-binding defect: "
                        "all three rev12 schemas (F1/F2a/F2b) declare consistency_evidence_sha256="
                        "675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48, but the declared "
                        "canonical path artifacts/formulation/evidence/taxonomy_consistency.json measures "
                        "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b and FROZEN rev28 "
                        "pins that measured hash. The declared bytes exist on disk only as a worker snapshot "
                        "(artifacts/worker-086/gform_rev12/pinned/taxonomy_consistency.675a99d0d25b.json) and "
                        "carry three extra keys (map_taxonomy_sha256, lead_contract_sha256, measured_at). "
                        "Independently confirms worker-086 HF-086-R1 at the byte level.",
            needed_to_unblock="Either publish the declared evidence document at the declared canonical path so "
                              "its sha256 resolves, or update the schemas' consistency_evidence_sha256 to the "
                              "published hash and re-freeze with a re-run of check_taxonomy_consistency; then "
                              "re-run BIND-05.",
            evidence_refs=[f"artifacts/worker-044/f2b_rev12_independent/report.json#{rep_sha[:12]}",
                           f"artifacts/formulation/evidence/taxonomy_consistency.json#{ev[:12]}",
                           f"artifacts/worker-086/gform_rev12/pinned/taxonomy_consistency.675a99d0d25b.json"]),
        event(
            f"w044-rev12-{stamp}-status-complete", "status", node_id="F2b", gate="G-FORM",
            class_id="AF-SCC-C0-VAC-GEN", status="active", hours=0.5,
            summary="W044-F2B-REV12-INDEP-02 COMPLETE at worker level (bounded execution worker; no node "
                    "transition, no gate verdict, no validation_status=passed). Verdict revise (4.0) at frozen "
                    f"rev12 C0 {target[:16]}: 17/19 checks pass, 8/8 controls pass, no drift; one hard finding "
                    "HF-044-BIND-05 (declared consistency evidence hash does not resolve). Artifacts hashed; "
                    "checkpoint written; supersedes nothing (W044-F2B-INDEP-VERDICT-01 remains the rev11 record, "
                    "void at rev12). Exiting for recycling.",
            evidence_refs=[f"artifacts/worker-044/f2b_rev12_independent/report.json#{rep_sha[:12]}",
                           f"runtime/state/w044_checkpoint_{stamp}.json"],
            next_falsifier=falsifier),
    ]

    # ---------- checkpoint
    STATE.mkdir(parents=True, exist_ok=True)
    ckpt = {
        "checkpoint_id": f"w044-{stamp}",
        "actor": "worker-044",
        "task_id": "W044-F2B-REV12-INDEP-02",
        "created_at": ts,
        "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN", "gate": "G-FORM",
        "target": {"path": report["target_path"], "sha256": target},
        "snapshot": {"path": report["snapshot"], "sha256": snap_sha},
        "pins": {k: v["sha256"] for k, v in report["pins_t0"].items()},
        "post_run_drift": report["summary"]["drift_moved"],
        "report": {"path": "artifacts/worker-044/f2b_rev12_independent/report.json", "sha256": rep_sha},
        "harness": {"path": "artifacts/worker-044/f2b_rev12_independent/verify_c0_rev12.py", "sha256": harness_sha},
        "verdict": report["summary"]["verdict"],
        "hard_failures": [h["id"] for h in report["summary"]["hard_failures"]],
        "controls_passed": sum(1 for c in report["controls"] if c["pass"]),
        "controls_total": len(report["controls"]),
        "probes": [{"probe_id": p["probe_id"], "detected": p["detected"]} for p in report["probes"]],
        "next_falsifier": falsifier,
        "does_not_claim": report["does_not_claim"],
    }
    ck = STATE / f"w044_checkpoint_{stamp}.json"
    ck.write_text(json.dumps(ckpt, indent=1, sort_keys=True) + "\n")
    with open(STATE / "w044_checkpoints.jsonl", "a") as f:
        f.write(json.dumps({**ckpt, "checkpoint_file": str(ck.relative_to(ROOT))}, sort_keys=True) + "\n")

    # ---------- outbox append (idempotent by event_id)
    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line).get("event_id"))
            except Exception:
                pass
    written = 0
    with open(OUTBOX, "a") as f:
        for e in events:
            if e["event_id"] in existing:
                continue
            f.write(json.dumps(e, sort_keys=True) + "\n")
            written += 1
    for e in events:
        try:
            json.loads(json.dumps(e))
        except Exception as exc:  # pragma: no cover
            raise SystemExit(f"event serialization failed: {exc}")
    print(json.dumps({"checkpoint": str(ck.relative_to(ROOT)), "checkpoint_sha256": sha(ck),
                      "events_written": written, "events_total": len(events),
                      "report_sha256": rep_sha, "harness_sha256": harness_sha,
                      "verdict": report["summary"]["verdict"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
