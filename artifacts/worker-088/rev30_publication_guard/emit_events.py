#!/usr/bin/env python3
"""Emit worker-088's W088-REV30-PUBLICATION-GUARD-01 events + checkpoint.

Idempotent: existing event_ids already present in the outbox are skipped.
Writes only comms/outbox/worker-088.jsonl and
runtime/state/w088_checkpoint_rev30_publication_guard.json.
"""
from __future__ import annotations

import hashlib
import json
import os

ROOT = "/data3/guoshaoyang/workdir/ai4math-swarm"
TASK = "artifacts/worker-088/rev30_publication_guard"
OUTBOX = os.path.join(ROOT, "comms/outbox/worker-088.jsonl")
CKPT = os.path.join(ROOT, "runtime/state/w088_checkpoint_rev30_publication_guard.json")
CREATED = "2026-09-12T01:16:00+08:00"
HOURS = 0.4


def sha256_file(rel: str) -> str:
    h = hashlib.sha256()
    with open(os.path.join(ROOT, rel), "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def h12(rel: str) -> str:
    return sha256_file(rel)[:12]


def main() -> int:
    report = json.load(open(os.path.join(ROOT, TASK, "guard_report.json")))
    files = {
        "probe": f"{TASK}/guard_rev30.py",
        "report": f"{TASK}/guard_report.json",
        "report_md": f"{TASK}/REPORT.md",
        "sums": f"{TASK}/SHA256SUMS",
        "emitter": f"{TASK}/emit_events.py",
        "battery_rehearsed": f"{TASK}/_scratch/battery_rehearsed.json",
        "dual_rehearsed": f"{TASK}/_scratch/dual_rehearsed.json",
        "battery_corrected": f"{TASK}/_scratch/battery_corrected.json",
    }
    H = {k: sha256_file(v) for k, v in files.items()}
    H58 = sha256_file("artifacts/worker-058/rev30_freeze_rehearsal/report.json")

    live = report["live_c0"]
    reh = report["rehearsed_candidate"]
    cor = report["corrected_candidate"]
    nes = report["nesting_only_candidate"]
    link = report["publication_link"]

    ev = []
    ev.append({
        "event_id": "w088-rev30guard-00-status-start",
        "event_type": "status",
        "created_at": CREATED,
        "actor": "worker-088",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "status": "active",
        "hours": 0.0,
        "summary": "No inbox card exists for worker-088 (recycled slot). Took ONE bounded class-bound task "
                   "W088-REV30-PUBLICATION-GUARD-01: independent guard on the rehearsed F2b rev30 publication path.",
        "evidence_refs": [
            f"{'schemas/af_scc_c0_vacuum.yaml'}#{live['sha256'][:12]}",
            f"{'artifacts/worker08/rev29_candidate/af_scc_c0_vacuum.repair-candidate.yaml'}#{reh['sha256'][:12]}",
            f"{'artifacts/worker-058/rev30_freeze_rehearsal/OWNER_RUNBOOK.md'}#{link['runbook_sha256'][:12]}",
            f"{files['probe']}#{H['probe'][:12]}",
        ],
        "next_falsifier": "a pinned byte moving; the rehearsed candidate's H2 sentence shown direction-correct at "
                          "its cited line; or the corrected candidates shown to carry an inverted H2 direction.",
    })
    ev.append({
        "event_id": "w088-rev30guard-01-artifact-probe",
        "event_type": "artifact",
        "created_at": CREATED,
        "actor": "worker-088",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "artifact_type": "instrument",
        "path": files["probe"],
        "sha256": H["probe"],
        "validation_status": "unverified",
        "evidence_refs": [f"{files['probe']}#{H['probe'][:12]}"],
        "note": "Deterministic stdlib-only, cwd-independent, fail-closed publication guard: 15 declared pins, own "
                "YAML bullet extraction, class-relative direction classifiers, 7 in-memory controls, and both "
                "rehearsal acceptance tools re-run read-only. Exit 0 guard fired / 2 expectation failed / 3 pin drift.",
    })
    ev.append({
        "event_id": "w088-rev30guard-02-artifact-report",
        "event_type": "artifact",
        "created_at": CREATED,
        "actor": "worker-088",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "artifact_type": "report",
        "path": files["report"],
        "sha256": H["report"],
        "validation_status": "unverified",
        "evidence_refs": [f"{files['report']}#{H['report'][:12]}"],
        "note": "Machine evidence: verdict BLOCK_REHEARSED_REV30_CANDIDATE__SAFE_ALTERNATIVES_VERIFIED; all 13 "
                "expectations hold, 7/7 controls match, no pin drift during the run.",
    })
    ev.append({
        "event_id": "w088-rev30guard-03-artifact-reportmd",
        "event_type": "artifact",
        "created_at": CREATED,
        "actor": "worker-088",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "artifact_type": "report",
        "path": files["report_md"],
        "sha256": H["report_md"],
        "validation_status": "unverified",
        "evidence_refs": [f"{files['report_md']}#{H['report_md'][:12]}"],
        "note": "Human-readable guard: byte-state table, acceptance-suite blindness measurement, controls, "
                "recommendation, owner condition, falsifier, non-claims.",
    })
    ev.append({
        "event_id": "w088-rev30guard-04-artifact-checkpoint",
        "event_type": "artifact",
        "created_at": CREATED,
        "actor": "worker-088",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "artifact_type": "checkpoint",
        "path": "runtime/state/w088_checkpoint_rev30_publication_guard.json",
        "sha256": None,  # filled after checkpoint write, see re-emission below
        "validation_status": "unverified",
        "evidence_refs": [f"{files['report']}#{H['report'][:12]}"],
        "note": "Worker-088 checkpoint: pins, byte-state classifications, acceptance-suite blindness, artifact "
                "hashes, event ids, falsifier, non-claims.",
    })
    ev.append({
        "event_id": "w088-rev30guard-05-claim",
        "event_type": "claim",
        "created_at": CREATED,
        "actor": "worker-088",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "conclusion_type": "formal_model",
        "status": "unverified",
        "statement": "At the live pins (C0 b2ab6acb2bbe, C2 e9a27996dfd3, FROZEN rev29 815e08079aef, unchanged "
                     "during the run), the rev30 publication path rehearsed by worker-058 (OWNER_RUNBOOK step 1, "
                     "rehearsal report candidate and sandbox C0, all sha256 84b5d3fa29a677ad) would land a "
                     "direction-inverted H2 carrier: 84b5d3fa correctly repairs H1 (line 246 now 'strictly smaller "
                     "extension class (E_C2 subset of E_C0)') but its replacement regularity.must_not_conflate[0] "
                     "asserts 'H2_loc-inextendibility ENTAILS this class's conclusion' (H2loc-inext => C0-inext), "
                     "the false converse of the same file's implication_ledger one_way_entailments[0] "
                     "(C0-inext => H2loc-inext) and a direct contradiction of the retained line 232 ('entails the "
                     "C2 sibling, not this class'). The rehearsal's own acceptance tools are blind to this: battery "
                     "PASS/0 hard failures and dual PASS/0 findings at 84b5d3fa, while the corrected candidate "
                     "51c253c4 and the nesting-only candidate 4951cc96 independently measure H1_FIXED with "
                     "H2_CORRECT_DIRECTION and H2_AGNOSTIC_NESTING_ONLY respectively and both pass the rehearsal "
                     "battery. The same sentence under own=C2 measures H2_CORRECT_DIRECTION (class-relative control).",
        "assumptions": [
            "worker measurement only; read-only on canonical paths; no network",
            "the direction probe is class-relative: 'this class' is resolved to C0 for the C0 file and to C2 for "
            "the C2 control, and the set chain E_C2 subset E_{C^1,1} subset E_H2loc subset E_C0 is taken from the "
            "live file's own line 239 and one_way_entailments rows",
            "candidate-level safety only; no full-schema F2b verdict on 51c253c4/4951cc96",
        ],
        "falsifier": report["falsifier"],
        "evidence_refs": [
            f"{files['report']}#{H['report'][:12]}",
            f"{files['probe']}#{H['probe'][:12]}",
            f"{files['battery_rehearsed']}#{H['battery_rehearsed'][:12]}",
            f"{files['dual_rehearsed']}#{H['dual_rehearsed'][:12]}",
            f"{files['battery_corrected']}#{H['battery_corrected'][:12]}",
            f"{'schemas/af_scc_c0_vacuum.yaml'}#{live['sha256'][:12]}",
            f"{'artifacts/worker08/rev29_candidate/af_scc_c0_vacuum.repair-candidate.yaml'}#{reh['sha256'][:12]}",
            f"{'artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_corrected.yaml'}#{cor['sha256'][:12]}",
            f"{'artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_nesting_only.yaml'}#{nes['sha256'][:12]}",
        ],
        "artifact_refs": [files["report"], files["report_md"], files["probe"]],
    })
    ev.append({
        "event_id": "w088-rev30guard-06-review",
        "event_type": "review",
        "created_at": CREATED,
        "actor": "worker-088",
        "reviewer": "worker-088",
        "node_id": "F2b",
        "target_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "artifact": "artifacts/worker08/rev29_candidate/af_scc_c0_vacuum.repair-candidate.yaml",
        "artifact_sha256": reh["sha256"],
        "reviewed_sha256": reh["sha256"],
        "counts_as_full_schema_verdict": False,
        "verdict": "revise",
        "score": 3.0,
        "review_file": files["report"],
        "review_sha256": H["report"],
        "hard_failures": [
            "W088-R30G-01 inverted_entailment_direction: candidate 84b5d3fa regularity.must_not_conflate[0] "
            "asserts H2loc-inext => this class's conclusion (C0-inext); the live file's own chain/row 241 and "
            "retained line 232 assert the opposite direction (C0-inext => H2loc-inext => C2-inext)",
            "W088-R30G-02 normative_contradiction: the repaired H2 sentence contradicts the retained "
            "implication_ledger.forbidden_weakenings/line-232 statement 'entails the C2 sibling, not this class' "
            "inside the same file",
        ],
        "findings": [
            {"id": "W088-R30G-03", "severity": "major",
             "axis": "rehearsal false-certification",
             "finding": "REV30_FREEZE_REHEARSAL_READY + OWNER_RUNBOOK prescribe 84b5d3fa over both canonical C0 "
                        "copies, but the rehearsal's battery and dual acceptance tools both PASS that candidate "
                        "(0 hard failures, 0 findings) while its H2 carrier is inverted; the rehearsal certifies "
                        "H1 only.",
             "detector": "guard_rev30.py acceptance_tools + classify_bullet"},
            {"id": "W088-R30G-04", "severity": "positive",
             "axis": "safe alternatives independently verified at candidate level",
             "finding": "51c253c4 measures H1_FIXED + H2_CORRECT_DIRECTION with battery PASS; 4951cc96 measures "
                        "H1_FIXED + H2_AGNOSTIC_NESTING_ONLY. Both are freezable carriers for rev30 pending the "
                        "usual two blind full-schema reviews at the published hash.",
             "detector": "guard_rev30.py analyze_file + battery on corrected"},
        ],
        "independence": {
            "reviewer": "worker-088",
            "reviewer_is_author": False,
            "author": "astra-lead-formulation",
            "no_author_contact": True,
            "no_network": True,
            "prior_use": "worker-080 reported the same candidate-level entailment inversion in parallel; this "
                         "guard re-derives it from the candidate bytes with an independently written instrument "
                         "(own YAML-bullet extraction and class-relative regex classifiers, 7 controls) and adds "
                         "the publication-path link to worker-058's rehearsal plus the acceptance-suite blindness "
                         "measurement. No verdict text was inherited.",
        },
        "not_claimed": [
            "no gate verdict, node status, validation_status or theorem claim",
            "not a full-schema F2b review; candidate-carrier safety only",
            "no canonical path written",
        ],
        "next_falsifier": "Re-run guard_rev30.py at the owner's landed rev30 hash; the block lifts only if the "
                          "landed C0 H2 carrier measures H2_CORRECT_DIRECTION or H2_AGNOSTIC_NESTING_ONLY with H1 "
                          "fixed, the rehearsal battery passes at the landed hash, and the file's line 232/ledger "
                          "rows remain non-contradictory.",
    })
    ev.append({
        "event_id": "w088-rev30guard-07-blocker",
        "event_type": "blocker",
        "created_at": CREATED,
        "actor": "worker-088",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "description": "Publication guard on the rehearsed rev30 path: do NOT land candidate 84b5d3fa "
                       "(artifacts/worker08/rev29_candidate/af_scc_c0_vacuum.repair-candidate.yaml) as the F2b "
                       "rev30 repair even though the rehearsal verdict is REV30_FREEZE_REHEARSAL_READY and its "
                       "OWNER_RUNBOOK step 1 prescribes it. It fixes H1 but introduces a hard H2 entailment "
                       "inversion at regularity.must_not_conflate[0] that the rehearsal's own acceptance tools "
                       "pass (measured blindness at the same hashes).",
        "needed_to_unblock": "formulation lead, in one revision at one hash: keep the line-246 H1 fix, land one "
                             "direction-correct H2 wording at regularity.must_not_conflate[0] - either "
                             "51c253c463067e25 (explicit C0-inext => H2loc-inext; H2loc-inext => C2 sibling) or "
                             "4951cc9698032996 (nesting + ledger pointer only, no entailment claim) - then "
                             "re-freeze with a strictly increasing revision and an explicit timestamp, re-run the "
                             "battery, and re-run this guard at the landed hash before commissioning the two blind "
                             "full-schema F2b reviewers.",
        "falsifier": "a landed rev30 whose C0 must_not_conflate[0] carries the inverted direction without the "
                     "line-232 contradiction, or an explicit gate-owner ruling that the rehearsed H2 sentence is "
                     "correct at the cited bytes with the reading exhibited.",
        "evidence_refs": [
            f"{files['report']}#{H['report'][:12]}",
            f"{'artifacts/worker-058/rev30_freeze_rehearsal/report.json'}#{H58[:12]}",
            f"{'artifacts/worker-058/rev30_freeze_rehearsal/OWNER_RUNBOOK.md'}#{link['runbook_sha256'][:12]}",
            f"{'artifacts/worker08/rev29_candidate/af_scc_c0_vacuum.repair-candidate.yaml'}#{reh['sha256'][:12]}",
        ],
        "next_falsifier": "re-run guard_rev30.py at the next rev30 candidate/revision; the guard exits 0 only if "
                          "the landed carrier is direction-correct and the acceptance battery passes at the "
                          "landed hash.",
    })
    ev.append({
        "event_id": "w088-rev30guard-08-checkpoint-exit",
        "event_type": "status",
        "created_at": CREATED,
        "actor": "worker-088",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "status": "active",
        "hours": HOURS,
        "summary": "W088-REV30-PUBLICATION-GUARD-01 complete at worker level: independent guard on the rehearsed "
                   "F2b rev30 publication path. Verdict BLOCK_REHEARSED_REV30_CANDIDATE__SAFE_ALTERNATIVES_VERIFIED "
                   "- 13/13 expectations, 7/7 controls, 0 pin drift, deterministic across three runs. Read-only on "
                   "canonical paths; checkpoint runtime/state/w088_checkpoint_rev30_publication_guard.json; worker "
                   "exits. No gate verdict, node status, validation_status or theorem claimed.",
        "evidence_refs": [
            f"{files['report']}#{H['report'][:12]}",
            f"{files['report_md']}#{H['report_md'][:12]}",
            f"{files['probe']}#{H['probe'][:12]}",
            "runtime/state/w088_checkpoint_rev30_publication_guard.json",
        ],
        "next_falsifier": "re-run guard_rev30.py at the owner's landed rev30 hash; the block lifts only if the "
                          "landed C0 H2 carrier is direction-correct (or nesting-only) and the battery passes at "
                          "that hash.",
    })

    # ---- checkpoint --------------------------------------------------------
    checkpoint = {
        "schema": "worker-088/checkpoint/v1",
        "checkpoint_id": "w088-ckpt-rev30-publication-guard",
        "worker": "worker-088",
        "task_id": "W088-REV30-PUBLICATION-GUARD-01",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "created_at": CREATED,
        "verdict": report["verdict"],
        "pins": {k: v["measured"] for k, v in report["pins"].items()},
        "byte_states": {
            "live_c0": {"sha256": live["sha256"], "h1": live["h1"], "h2": live["classification"]},
            "rehearsed_candidate": {"sha256": reh["sha256"], "h1": reh["h1"], "h2": reh["classification"],
                                    "intra_file_contradiction": reh["intra_file_contradiction"]},
            "corrected_candidate": {"sha256": cor["sha256"], "h1": cor["h1"], "h2": cor["classification"]},
            "nesting_only_candidate": {"sha256": nes["sha256"], "h1": nes["h1"], "h2": nes["classification"]},
            "c2_live_own_C2_control": {"sha256": report["live_c2_class_relative_control"]["sha256"],
                                       "h2": report["live_c2_class_relative_control"]["classification"]},
        },
        "publication_link": link,
        "acceptance_suite_blind": report["expectations"]["acceptance_suite_blind_to_h2_defect"],
        "controls": report["controls"],
        "expectations": report["expectations"],
        "artifacts": {k: {"path": v, "sha256": H[k]} for k, v in files.items() if k != "emitter"},
        "event_ids": [e["event_id"] for e in ev],
        "falsifier": report["falsifier"],
        "non_claims": report["non_claims"],
        "authority": "worker measurement only; no canonical writes; no gate verdict, node status, "
                     "validation_status or theorem; owner (astra-lead-formulation) owns any rev30 publication.",
    }
    ckpt_text = json.dumps(checkpoint, indent=2, sort_keys=True) + "\n"
    with open(CKPT, "w", encoding="utf-8") as fh:
        fh.write(ckpt_text)
    ckpt_sha = sha256_file("runtime/state/w088_checkpoint_rev30_publication_guard.json")

    # fill the checkpoint artifact event now that the file exists
    for e in ev:
        if e["event_id"] == "w088-rev30guard-04-artifact-checkpoint":
            e["sha256"] = ckpt_sha
            e["evidence_refs"] = [f"runtime/state/w088_checkpoint_rev30_publication_guard.json#{ckpt_sha[:12]}"]

    existing = set()
    if os.path.exists(OUTBOX):
        for line in open(OUTBOX, "r", encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line).get("event_id"))
            except json.JSONDecodeError:
                continue
    added, skipped = 0, 0
    with open(OUTBOX, "a", encoding="utf-8") as fh:
        for e in ev:
            if e["event_id"] in existing:
                skipped += 1
                continue
            fh.write(json.dumps(e, sort_keys=True) + "\n")
            added += 1
    print(json.dumps({"checkpoint": CKPT, "checkpoint_sha256": ckpt_sha,
                      "events_added": added, "events_skipped": skipped,
                      "event_ids": [e["event_id"] for e in ev]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
