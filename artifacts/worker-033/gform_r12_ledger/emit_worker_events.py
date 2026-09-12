#!/usr/bin/env python3
"""Emit worker-033 deliverables for W033-GFORM-R12-LEDGER-01.

Fail-closed: every artifact referenced in an event must exist on disk and its
measured sha256 is embedded in the event.  Re-running skips event ids already
present in the outbox (idempotent).  Writes only:
  artifacts/worker-033/gform_r12_ledger/{review.json,run.log,SHA256SUMS}
  comms/outbox/worker-033.jsonl                      (append, dedup by id)
  runtime/state/w033_gform_r12_ledger_checkpoint_1.json
  runtime/state/w033_checkpoints.jsonl               (append)
No canonical artifact, map, or gate is modified.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

TASK = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[3]
OUTBOX = ROOT / "comms/outbox/worker-033.jsonl"
STATE = ROOT / "runtime/state"
CST = timezone(timedelta(hours=8))


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


def main() -> int:
    stamp = datetime.now(CST).strftime("%Y%m%dT%H%M%S")
    now = datetime.now(CST).replace(microsecond=0).isoformat()

    # 1. run the checker, keep its stdout as the run log
    proc = subprocess.run([sys.executable, str(TASK / "check_gform_r12_ledger.py")],
                          capture_output=True, text=True, cwd=ROOT)
    if proc.returncode != 0:
        print(proc.stdout, proc.stderr, file=sys.stderr)
        print(f"checker exit={proc.returncode}; refusing to emit", file=sys.stderr)
        return 2
    report = json.loads((TASK / "report.json").read_text())
    controls = json.loads((TASK / "controls.json").read_text())
    if not controls["controls_pass"]:
        print("controls failed; refusing to emit", file=sys.stderr)
        return 2
    (TASK / "run.log").write_text(
        f"# run {now}\n$ python3 {rel(TASK / 'check_gform_r12_ledger.py')}\n"
        + proc.stdout + f"exit=0\n")

    H = {n: sha(TASK / n) for n in
         ("check_gform_r12_ledger.py", "report.json", "controls.json", "README.md",
          "drift.json", "run.log")}
    ev = report["secondary_evidence_check"]
    analysis = report["analysis"]

    # 2. worker-level review verdict on the gate ledger (not on a class schema)
    review = {
        "schema_version": "0.1",
        "artifact_kind": "review",
        "event_id": f"w033-g12-{stamp}-review",
        "event_type": "review",
        "created_at": now,
        "actor": "worker-033",
        "reviewer": "worker-033",
        "task_id": "W033-GFORM-R12-LEDGER-01",
        "node_id": "G-FORM",
        "target_id": "G-FORM-ledger",
        "gate": "G-FORM",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "review_kind": "supersession_aware_accept_set_audit",
        "counts_as_full_schema_verdict": False,
        "counts_as_independent": True,
        "verdict": "revise",
        "score": 2.0,
        "score_rationale": (
            "The gate verdict G-FORM=pending is not contradicted (no class reaches two "
            "accepts under either reading), but the reason quoted at 00:43:08 is not "
            "reproducible: the F1 accept it cites was already withdrawn at that instant and "
            "the operative F1 accept is a different reviewer visible only in the event stream; "
            "F2a additionally carries a full-schema accept that the file-only scan cannot see."),
        "scope": (
            "Accept-set bookkeeping for the rev12 G-FORM epoch (F1 cce9c60146d6 / "
            "F2a 5476a3f2c6bc / F2b 55d0a1ea9bda) at the quote instant "
            "2026-09-12T00:43:08, from reviews/*.json + the accepted event stream, with "
            "explicit supersession. No schema semantics, no gate verdict, no node status."),
        "quoted_at_00_43_08": {
            "F1": analysis["F1"]["quoted"], "F2a": analysis["F2a"]["quoted"],
            "F2b": analysis["F2b"]["quoted"]},
        "operative_at_00_43_08_gate_view": {
            t: analysis[t]["asof_quote"]["gate_accept_reviewers"] for t in ("F1", "F2a", "F2b")},
        "operative_at_00_43_08_full_view": {
            t: analysis[t]["asof_quote"]["full_independent_accept_reviewers"]
            for t in ("F1", "F2a", "F2b")},
        "hard_failures": [
            {
                "id": "W033-R12-HF-01",
                "severity": "hard",
                "class_ids": ["AF-WCC-VAC-GEN"],
                "finding": (
                    "The gate reason quoted at 00:43:08 lists worker-088 as the F1 accept at "
                    "cce9c60146d6, but worker-088's own amended review at the same hash "
                    "(reviews/F1-review-088-rev12-amended.json, 00:38:49; event "
                    "w088-20260912T003902-review-f1-rev12-amended, 00:39:02) is revise and names "
                    "reviews/F1-review-088-rev12.json in supersedes. The quoted accept was "
                    "already retired at the quote instant under both S1 (named supersession) "
                    "and S2 (same reviewer, later verdict)."),
                "falsifier": (
                    "A worker-088 record at cce9c60146d6 after 00:39:02 that is an accept, or "
                    "bytes showing the amended review does not supersede the rev12 accept."),
            },
            {
                "id": "W033-R12-HF-02",
                "severity": "hard",
                "class_ids": ["AF-WCC-VAC-GEN"],
                "finding": (
                    "The operative F1 full independent accept at the quote instant is "
                    "worker-061 (event w061-rev12-20260912T0040-review, 00:37:58, "
                    "artifact_sha256=cce9c60146d6), which no reviews/*.json file carries; the "
                    "reviews-only scan therefore reports the wrong reviewer in both directions. "
                    "F1 operative set {worker-061} != quoted {worker-088}."),
                "falsifier": (
                    "A binding reviews/*.json accept by worker-061 at cce9c60146d6, or a "
                    "withdrawal/supersession of worker-061's accept before 00:43:08."),
            },
        ],
        "findings": [
            {
                "id": "W033-R12-03",
                "severity": "major",
                "class_ids": ["AF-SCC-C2-VAC-GEN"],
                "finding": (
                    "F2a: the quoted empty set is reproducible only under the gate-accept "
                    "reading. worker-089 (event w089-20260912T003959-review, 00:39:59) is a "
                    "full-schema, non-author accept binding 5476a3f2c6bc but sets "
                    "counts_as_gate_accept=false and its scope excludes the consistency-evidence "
                    "axis (OBS-089-1). Under the full-schema reading F2a's operative accept set "
                    "is {worker-089}, invisible to the file-only scan."),
            },
            {
                "id": "W033-R12-04",
                "severity": "positive",
                "class_ids": ["AF-SCC-C0-VAC-GEN"],
                "finding": (
                    "F2b: quoted {worker-098} is operative at 55d0a1ea9bda in both channels "
                    "(file F2b-repair-verify-worker-098.json + event "
                    "w098-f2brv-review-2026-09-12T00:37:56+08:00); this quote is reproducible."),
            },
            {
                "id": "W033-R12-05",
                "severity": "info",
                "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
                "finding": (
                    "Secondary hash-pinned cross-check (reproduces HF-086-R1, no new claim): "
                    "all three rev12 schemas declare f0_binding.consistency_evidence_sha256 = "
                    "675a99d0d25b..., which resolves nowhere: artifacts/formulation/evidence/"
                    "taxonomy_consistency.json measures 9e335e9ba1bf... and FROZEN rev28 pins "
                    "9e335e9ba1bf.... Each operative accept is silent on that axis (worker-061, "
                    "worker-098) or explicitly excludes it (worker-089 OBS-089-1)."),
            },
            {
                "id": "W033-R12-06",
                "severity": "major",
                "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
                "finding": (
                    "Mechanism (recurrence of W033-VL-01..06 at rev12): "
                    "astra_lifecycle.review_coverage() reads only reviews/*.json at face value, "
                    "so it emits a stale positive (withdrawn worker-088 accept) and misses "
                    "event-only accepts (worker-061; worker-089 on the full-schema reading). "
                    "A supersession-aware two-channel ledger is required before the next gate "
                    "reason is quoted."),
            },
        ],
        "criterion_effect": (
            "Under both readings the per-class maximum is one accept (F1 worker-061, F2a none "
            "or worker-089, F2b worker-098), below G-FORM's two independent accepts; this audit "
            "does not argue the pending verdict is wrong, only that its stated accept sets are."),
        "evidence_refs": [
            f"{rel(TASK / 'report.json')}#{H['report.json'][:12]}",
            f"{rel(TASK / 'check_gform_r12_ledger.py')}#{H['check_gform_r12_ledger.py'][:12]}",
            f"{rel(TASK / 'controls.json')}#{H['controls.json'][:12]}",
            "reviews/F1-review-088-rev12-amended.json",
            "reviews/F2b-repair-verify-worker-098.json",
            "research_map/events.jsonl",
            "pinned/research_map.json#controller_gate_audit.G-FORM",
        ],
        "falsifier": (
            "Re-run artifacts/worker-033/gform_r12_ledger/check_gform_r12_ledger.py on a pinned "
            "snapshot (13/13 controls, fail-closed). The verdict is falsified if: worker-061 "
            "re-issues a non-accept at cce9c60146d6 or is withdrawn; a binding reviews/*.json "
            "accept at cce9c60146d6 supersedes worker-061; worker-088 re-issues an operative "
            "accept at cce9c60146d6; worker-098's accept at 55d0a1ea9bda is superseded; "
            "worker-089's counts_as_gate_accept is corrected to true; any schema moves off the "
            "three epoch hashes; or the declared consistency-evidence hash is repaired so the "
            "cross-check resolves."),
        "non_claims": [
            "No gate verdict; G-FORM remains the controller's call.",
            "No node status, no validation_status=passed, no theorem, no physics.",
            "No adjudication of the substantive F1/F2a/F2b revise findings or schema semantics.",
        ],
    }
    (TASK / "review.json").write_text(json.dumps(review, indent=1, sort_keys=True) + "\n")
    H["review.json"] = sha(TASK / "review.json")

    # 3. SHA256SUMS over task deliverables + pinned manifest
    lines = []
    for n in ("check_gform_r12_ledger.py", "report.json", "controls.json", "review.json",
              "README.md", "drift.json", "run.log"):
        lines.append(f"{H[n]}  {n}")
    lines.append(f"{sha(TASK / 'pinned/MANIFEST.json')}  pinned/MANIFEST.json")
    (TASK / "SHA256SUMS").write_text("\n".join(lines) + "\n")
    H["SHA256SUMS"] = sha(TASK / "SHA256SUMS")

    R = lambda n: f"{rel(TASK / n)}#{H[n][:12]}"
    # outbox events carry flat string findings (channel schema); the structured
    # dicts stay in review.json / report.json
    hf_ev = [f"{h['id']} ({','.join(h.get('class_ids', []))}): {h['finding']}"
             for h in review["hard_failures"]]
    fd_ev = [f"{f['id']} [{f.get('severity')}] ({','.join(f.get('class_ids', []))}): "
             f"{f['finding']}" for f in review["findings"]]
    events = [
        {
            "event_id": f"w033-g12-{stamp}-claim", "event_type": "status", "created_at": now,
            "actor": "worker-033", "node_id": "G-FORM", "gate": "G-FORM",
            "class_ids": review["class_ids"], "status": "active", "hours": 0.2,
            "task_id": "W033-GFORM-R12-LEDGER-01",
            "summary": (
                "No assignment card existed in comms/inbox/worker-033.jsonl. Took one bounded "
                "class-bound task, W033-GFORM-R12-LEDGER-01: supersession-aware, hash-pinned "
                "audit of the G-FORM operative accept sets at the rev12 epoch (F1 cce9c60146d6 "
                "/ F2a 5476a3f2c6bc / F2b 55d0a1ea9bda) against the gate reason quoted at "
                "2026-09-12T00:43:08, from reviews/*.json + the accepted event stream. Output is "
                "a measurement, checker, controls and review; no gate verdict, no node "
                "completion, no theorem."),
            "evidence_refs": [R("report.json"), R("check_gform_r12_ledger.py"), R("controls.json"),
                              "pinned/research_map.json#controller_gate_audit.G-FORM"],
            "next_falsifier": review["falsifier"],
        },
        {
            "event_id": f"w033-g12-{stamp}-artifact-checker", "event_type": "artifact",
            "created_at": now, "actor": "worker-033", "node_id": "G-FORM", "gate": "G-FORM",
            "class_ids": review["class_ids"], "task_id": "W033-GFORM-R12-LEDGER-01",
            "artifact_type": "independent_checker_source", "path": rel(TASK / "check_gform_r12_ledger.py"),
            "sha256": H["check_gform_r12_ledger.py"], "validation_status": "unverified",
            "note": ("Deterministic, stdlib-only; reads pinned/ only; 13 synthetic controls; "
                     "exit 3 on pinned-manifest drift, 2 on control failure."),
            "evidence_refs": [R("controls.json")],
        },
        {
            "event_id": f"w033-g12-{stamp}-artifact-report", "event_type": "artifact",
            "created_at": now, "actor": "worker-033", "node_id": "G-FORM", "gate": "G-FORM",
            "class_ids": review["class_ids"], "task_id": "W033-GFORM-R12-LEDGER-01",
            "artifact_type": "accept_set_ledger_report", "path": rel(TASK / "report.json"),
            "sha256": H["report.json"], "validation_status": "unverified",
            "note": ("Quoted vs operative sets at 00:43:08: F1 quoted [worker-088] -> operative "
                     "{worker-061} (088 retired by own amendment); F2a [] reproduces only under "
                     "the gate-flag view (full view {worker-089}); F2b {worker-098} reproducible."),
            "evidence_refs": [R("check_gform_r12_ledger.py"), R("SHA256SUMS")],
        },
        {
            "event_id": f"w033-g12-{stamp}-artifact-controls", "event_type": "artifact",
            "created_at": now, "actor": "worker-033", "node_id": "G-FORM", "gate": "G-FORM",
            "class_ids": review["class_ids"], "task_id": "W033-GFORM-R12-LEDGER-01",
            "artifact_type": "falsifier_control_matrix", "path": rel(TASK / "controls.json"),
            "sha256": H["controls.json"], "validation_status": "unverified",
            "note": "13/13 controls PASS (S1/S2 retirement, binding whitelist, channel dedup, as-of, quoted parser).",
            "evidence_refs": [R("report.json")],
        },
        {
            "event_id": f"w033-g12-{stamp}-artifact-review", "event_type": "artifact",
            "created_at": now, "actor": "worker-033", "node_id": "G-FORM", "gate": "G-FORM",
            "class_ids": review["class_ids"], "task_id": "W033-GFORM-R12-LEDGER-01",
            "artifact_type": "independent_review_verdict", "path": rel(TASK / "review.json"),
            "sha256": H["review.json"], "validation_status": "unverified",
            "note": "Verdict revise (score 2.0) on the gate ledger; target G-FORM-ledger, not a class.",
            "evidence_refs": [R("report.json"), R("controls.json")],
        },
        {
            "event_id": f"w033-g12-{stamp}-artifact-readme", "event_type": "artifact",
            "created_at": now, "actor": "worker-033", "node_id": "G-FORM", "gate": "G-FORM",
            "class_ids": review["class_ids"], "task_id": "W033-GFORM-R12-LEDGER-01",
            "artifact_type": "task_readme", "path": rel(TASK / "README.md"),
            "sha256": H["README.md"], "validation_status": "unverified",
            "note": "Question, measured answer, rules, mechanism, falsifier, non-claims.",
            "evidence_refs": [R("report.json")],
        },
        {
            "event_id": f"w033-g12-{stamp}-artifact-drift", "event_type": "artifact",
            "created_at": now, "actor": "worker-033", "node_id": "G-FORM", "gate": "G-FORM",
            "class_ids": review["class_ids"], "task_id": "W033-GFORM-R12-LEDGER-01",
            "artifact_type": "live_drift_observation", "path": rel(TASK / "drift.json"),
            "sha256": H["drift.json"], "validation_status": "unverified",
            "note": ("Live re-hash at run time: F1/F2a/F2b all equal the pinned rev12 epoch "
                     "hashes; consistency-evidence file equal to pinned 9e335e9b."),
            "evidence_refs": [R("report.json")],
        },
        {
            "event_id": f"w033-g12-{stamp}-artifact-sums", "event_type": "artifact",
            "created_at": now, "actor": "worker-033", "node_id": "G-FORM", "gate": "G-FORM",
            "class_ids": review["class_ids"], "task_id": "W033-GFORM-R12-LEDGER-01",
            "artifact_type": "pinned_input_manifest", "path": rel(TASK / "SHA256SUMS"),
            "sha256": H["SHA256SUMS"], "validation_status": "unverified",
            "note": "Measured hashes of all deliverables and pinned/MANIFEST.json.",
            "evidence_refs": [R("report.json"), R("review.json")],
        },
        {
            "event_id": f"w033-g12-{stamp}-claim-formal", "event_type": "claim",
            "created_at": now, "actor": "worker-033", "node_id": "G-FORM", "gate": "G-FORM",
            "class_id": review["class_id"], "class_ids": review["class_ids"],
            "conclusion_type": "formal_model", "task_id": "W033-GFORM-R12-LEDGER-01",
            "artifact_refs": [R("report.json"), R("review.json"), R("controls.json"),
                              R("check_gform_r12_ledger.py")],
            "assumptions": [
                "Verdicts bind only through whitelisted target-pin hash fields; evidence_refs and context pins never bind.",
                "Operative = not named in a later record's supersedes (S1) and not outvoted by the same reviewer's latest verdict at the same target+epoch (S2).",
                "As-of 2026-09-12T00:43:08: created_at <= instant; missing file timestamps use recovered source mtime or are unknown-time and flagged.",
                "Scope is bookkeeping only; schema semantics are not re-derived.",
            ],
            "evidence_refs": [R("report.json"), R("check_gform_r12_ledger.py"), R("controls.json"),
                              R("review.json"), R("SHA256SUMS")],
            "statement": (
                "FORMAL-MODEL-LEVEL binding audit (not a mathematical theorem, not a numerical "
                "result) at pinned inputs. At the G-FORM rev12 epoch (F1 cce9c60146d6 / F2a "
                "5476a3f2c6bc / F2b 55d0a1ea9bda) the controller gate reason checked_at "
                "2026-09-12T00:43:08 quotes F1 [worker-088], F2a [], F2b [worker-098]. A "
                "supersession-aware two-channel reduction gives, at that instant: F1 "
                "{worker-061} (worker-088's accept was retired at 00:38:49/00:39:02 by its own "
                "amended revise at the same hash; worker-061's accept exists only in the event "
                "stream); F2b {worker-098} (reproducible); F2a {} under the gate-accept reading "
                "and {worker-089} under the full-schema reading (worker-089 is a binding, "
                "full-schema, non-author accept that sets counts_as_gate_accept=false). The "
                "file-only face-value scan astra_lifecycle.review_coverage() therefore emits "
                "both a stale positive and an event-only blind spot at this epoch. Independent "
                "cross-check reproducing HF-086-R1: all three schemas declare "
                "consistency_evidence_sha256 675a99d0d25b, which resolves nowhere (canonical "
                "path and FROZEN rev28 both 9e335e9ba1bf); none of the three operative accepts "
                "tested that axis. Under both readings no class reaches two accepts, so the "
                "pending gate verdict is not contradicted; the quoted sets are."),
            "falsifier": review["falsifier"],
        },
        {
            "event_id": f"w033-g12-{stamp}-review-formal", "event_type": "review",
            "created_at": now, "actor": "worker-033", "reviewer": "worker-033",
            "target_id": "G-FORM-ledger", "node_id": "G-FORM", "gate": "G-FORM",
            "class_ids": review["class_ids"], "task_id": "W033-GFORM-R12-LEDGER-01",
            "counts_as_full_schema_verdict": False, "counts_as_independent": True,
            "verdict": "revise", "score": 2.0,
            "reviewed_sha256": None,
            "hard_failures": hf_ev, "findings": fd_ev,
            "evidence_refs": review["evidence_refs"], "falsifier": review["falsifier"],
            "independence": ("worker-033 authored none of the reviewed verdicts and no canonical "
                             "artifact; the ledger is recomputed from pinned bytes by a tool "
                             "published with the report."),
        },
        {
            "event_id": f"w033-g12-{stamp}-blocker", "event_type": "blocker",
            "created_at": now, "actor": "worker-033", "node_id": "G-FORM", "gate": "G-FORM",
            "class_ids": review["class_ids"], "task_id": "W033-GFORM-R12-LEDGER-01",
            "description": (
                "The G-FORM gate reason checked_at 2026-09-12T00:43:08 is not reproducible from "
                "the pinned corpus: its F1 accept worker-088 was withdrawn by the same "
                "reviewer's amendment at the same hash 4m19s before the quote, and the operative "
                "F1 accept worker-061 is event-only; F2a additionally carries a full-schema "
                "accept (worker-089) invisible to the file-only scan. Any gate reason built by "
                "astra_lifecycle.review_coverage() keeps both defects (stale positive and "
                "event-only blind spot)."),
            "needed_to_unblock": (
                "Recompute review coverage with a supersession-aware, two-channel ledger (or "
                "patch astra_lifecycle.review_coverage accordingly), then re-quote the G-FORM "
                "accept sets; F1/F2a/F2b still need fresh hash-bound independent accepts at the "
                "published hashes to satisfy the two-accept criterion, and the declared "
                "consistency-evidence hash should be repaired or restamped so it resolves."),
            "evidence_refs": [R("report.json"), R("review.json"), R("controls.json")],
        },
        {
            "event_id": f"w033-g12-{stamp}-ckpt1", "event_type": "status", "created_at": now,
            "actor": "worker-033", "node_id": "G-FORM", "gate": "G-FORM",
            "class_ids": review["class_ids"], "status": "active", "hours": 0.5,
            "task_id": "W033-GFORM-R12-LEDGER-01",
            "summary": ("Checkpoint w033-g12-ckpt1: tool "
                        f"{H['check_gform_r12_ledger.py'][:12]}, report {H['report.json'][:12]}, "
                        f"controls 13/13 PASS, no target drift. Quoted@00:43:08 F1[worker-088] "
                        "F2a[] F2b[worker-098]; operative F1{worker-061} (full/gate), F2a{} gate / "
                        "{worker-089} full, F2b{worker-098}. Checkpoint file "
                        "runtime/state/w033_gform_r12_ledger_checkpoint_1.json."),
            "evidence_refs": [R("report.json"), R("controls.json"), R("SHA256SUMS")],
            "next_falsifier": review["falsifier"],
        },
        {
            "event_id": f"w033-g12-{stamp}-complete", "event_type": "status", "created_at": now,
            "actor": "worker-033", "node_id": "G-FORM", "gate": "G-FORM",
            "class_ids": review["class_ids"], "status": "active", "hours": 0.7,
            "task_id": "W033-GFORM-R12-LEDGER-01",
            "summary": ("W033-GFORM-R12-LEDGER-01 complete at worker level: artifacts exist on "
                        "disk with measured hashes, 13/13 controls pass, checker fail-closed on "
                        "manifest drift. Findings W033-R12-HF-01/02 and 03-06 each carry a "
                        "falsifier. Bounded worker lifecycle complete; exiting for re-queue. "
                        "Worker cannot set done/passed or a gate verdict."),
            "evidence_refs": [R("report.json"), R("check_gform_r12_ledger.py"), R("controls.json"),
                              R("review.json"), R("README.md"), R("drift.json"), R("SHA256SUMS")],
            "next_falsifier": review["falsifier"],
        },
    ]

    existing = set()
    existing_task = False
    if OUTBOX.is_file():
        for line in OUTBOX.read_text().splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    d = json.loads(line)
                    existing.add(d.get("event_id"))
                    if d.get("task_id") == "W033-GFORM-R12-LEDGER-01":
                        existing_task = True
                except Exception:
                    pass
    appended = []
    if existing_task:
        print("W033-GFORM-R12-LEDGER-01 events already present; emission skipped "
              "(idempotent per task)")
    else:
        with OUTBOX.open("a") as f:
            for e in events:
                if e["event_id"] in existing:
                    continue
                f.write(json.dumps(e, sort_keys=True) + "\n")
                appended.append(e["event_id"])

    # validate the appended lines round-trip
    seen = 0
    for line in OUTBOX.read_text().splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        json.loads(line)
        seen += 1

    ckpt = {
        "checkpoint": 1,
        "worker": "worker-033",
        "at": now,
        "task_id": "W033-GFORM-R12-LEDGER-01",
        "assignment": ("self-selected bounded class-bound task; no inbox card for worker-033 "
                       "(00:12:30/00:16:56 fleet launches)"),
        "node_id": "G-FORM",
        "gate": "G-FORM",
        "class_ids": review["class_ids"],
        "hours_spent_estimate": 0.7,
        "status": {
            "delivered": True,
            "validation_status": "unverified",
            "quoted_at_00_43_08": review["quoted_at_00_43_08"],
            "operative_gate_view": review["operative_at_00_43_08_gate_view"],
            "operative_full_view": review["operative_at_00_43_08_full_view"],
            "controls_pass": True,
            "controls_total": 13,
            "no_gate_verdict": True,
        },
        "final_hashes": {
            "F1_rev12": report["epochs"]["F1"]["epoch_rev12"],
            "F2a_rev12": report["epochs"]["F2a"]["epoch_rev12"],
            "F2b_rev12": report["epochs"]["F2b"]["epoch_rev12"],
            "consistency_evidence_measured": ev["measured_sha256"],
            "consistency_evidence_declared": ev["schemas"]["F1"]["declared_consistency_evidence_sha256"],
            "tool": H["check_gform_r12_ledger.py"],
            "report": H["report.json"],
            "controls": H["controls.json"],
            "review": H["review.json"],
        },
        "outbox_events": appended,
        "artifacts": {rel(TASK / n): H[n] for n in
                      ("check_gform_r12_ledger.py", "report.json", "controls.json",
                       "review.json", "README.md", "drift.json", "run.log", "SHA256SUMS")},
        "falsifier": review["falsifier"],
        "next_falsifier": review["falsifier"],
        "not_claimed": review["non_claims"],
        "numerics_lock": "respected: no N1 work, no numerics/spherical_solver/, no GPU work",
    }
    ck_path = STATE / "w033_gform_r12_ledger_checkpoint_1.json"
    ck_path.write_text(json.dumps(ckpt, indent=1, sort_keys=True) + "\n")
    with (STATE / "w033_checkpoints.jsonl").open("a") as f:
        f.write(json.dumps({
            "task_id": ckpt["task_id"], "created_at": now,
            "status": "complete-worker-level", "checkpoint_path": rel(ck_path),
            "checkpoint_sha256": sha(ck_path)}) + "\n")

    print(json.dumps({
        "appended_events": appended, "outbox_lines_total": seen,
        "report": H["report.json"], "review": H["review.json"],
        "controls": H["controls.json"], "tool": H["check_gform_r12_ledger.py"],
        "checkpoint": rel(ck_path), "checkpoint_sha256": sha(ck_path),
    }, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
