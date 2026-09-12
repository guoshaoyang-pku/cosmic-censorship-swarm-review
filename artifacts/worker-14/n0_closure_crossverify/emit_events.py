#!/usr/bin/env python3
"""Deterministic outbox emitter for W014-GNUM-N0-CLOSURE-CROSSVERIFY-01.

Writes the runtime checkpoint, then appends the task's events to
comms/outbox/worker-014.jsonl. Idempotent: an event_id already present is skipped.
Hashes are measured from disk at emission time.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "artifacts/worker-14/n0_closure_crossverify"
OUTBOX = ROOT / "comms/outbox/worker-014.jsonl"
CKPT = ROOT / "runtime/state/w014_n0_closure_crossverify_checkpoint.json"
NOW = datetime.now().astimezone().isoformat(timespec="seconds")
STAMP = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S")
ACTOR = "worker-014"
CID, NODE, GATE = "AF-WCC-SCALAR-SPH", "N0", "G-NUM"

FALSIFIER = (
    "Re-run artifacts/worker-14/n0_closure_crossverify/verify_n0_closure_x.py at the pinned inputs. "
    "Falsified if any recomputed fit leaves |p-2|>0.3, a ladder is non-monotone, cross-scheme spread "
    "exceeds 0.25, recomputation disagrees with cert/rev3 beyond 1e-12, a cited verdict artifact "
    "drifts off its declared hash or loses its token, live taxonomy != 0abb9ed8a961 or lacks "
    "AF-WCC-SCALAR-SPH, numerics_lock != locked or numerics/spherical_solver appears, T1 moves off "
    "88ec0bf298cb or T2 off 87b311e72032, any control fails to fire, or any pinned input drifts "
    "pre/post. A later write to any pinned path voids the verdict for the new bytes."
)
NOT_CLAIM = [
    "not a G-NUM gate verdict; gate authority stays Astra / lead-audit",
    "not an N0 node completion or status transition",
    "no numerics_lock release; N1 stays queued",
    "no adjudication of the B-N0-R2-2 protocol-review contest",
    "no canonical-path write; read-only over every pinned input",
    "no physics / self-gravity / WCC / SCC claim",
]
TARGETS = {
    "numerics/protocol/lifecycle08_stoprule_closure_verify.json":
        "88ec0bf298cbc4de6ae2a6d3038961d404f1c43a64cbaa92f29b6ad6cce77f75",
    "reviews/N0-stoprule-closure-review-worker-017.json":
        "87b311e72032b38a6ad9137be9e373d00fb641691b75e066ad0a3271523454dc",
}


def sha(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def main() -> int:
    report_html = json.loads((TASK / "report.json").read_text())
    deliverables = {
        "artifacts/worker-14/n0_closure_crossverify/report.json": sha("artifacts/worker-14/n0_closure_crossverify/report.json"),
        "artifacts/worker-14/n0_closure_crossverify/verify_n0_closure_x.py": sha("artifacts/worker-14/n0_closure_crossverify/verify_n0_closure_x.py"),
        "artifacts/worker-14/n0_closure_crossverify/PRE_REGISTRATION.md": sha("artifacts/worker-14/n0_closure_crossverify/PRE_REGISTRATION.md"),
        "artifacts/worker-14/n0_closure_crossverify/README.md": sha("artifacts/worker-14/n0_closure_crossverify/README.md"),
    }
    task = "W014-GNUM-N0-CLOSURE-CROSSVERIFY-01"
    checkpoint = {
        "actor": ACTOR,
        "task_id": task,
        "class_id": CID,
        "node_id": NODE,
        "gate": GATE,
        "emitted_at": NOW,
        "verdict": report_html["verdict"],
        "verdict_scope": report_html["verdict_scope"],
        "counts": {"checks": len(report_html["checks"]),
                   "flags": sum(1 for c in report_html["checks"] if c["status"] == "flag"),
                   "controls_fired": report_html["controls"]["fired"],
                   "controls_total": report_html["controls"]["n"]},
        "targets": TARGETS,
        "pins_measured": report_html["pins_measured"],
        "deliverables": deliverables,
        "event_ids": [
            f"w014-n0x-{STAMP}-artifact-report",
            f"w014-n0x-{STAMP}-artifact-instrument",
            f"w014-n0x-{STAMP}-artifact-prereg",
            f"w014-n0x-{STAMP}-artifact-readme",
            f"w014-n0x-{STAMP}-artifact-checkpoint",
            f"w014-n0x-{STAMP}-review-closure",
            f"w014-n0x-{STAMP}-review-first-review",
            f"w014-n0x-{STAMP}-claim",
            f"w014-n0x-{STAMP}-status",
        ],
        "next_falsifier": FALSIFIER,
        "does_not_claim": NOT_CLAIM,
    }
    CKPT.parent.mkdir(parents=True, exist_ok=True)
    CKPT.write_text(json.dumps(checkpoint, indent=1, sort_keys=True) + "\n")
    ckpt_rel = "runtime/state/w014_n0_closure_crossverify_checkpoint.json"
    deliverables[ckpt_rel] = sha(ckpt_rel)

    base = {
        "actor": ACTOR, "created_at": NOW, "class_id": CID, "node_id": NODE, "gate": GATE,
        "task_id": task, "falsifier": FALSIFIER, "does_not_claim": NOT_CLAIM,
    }

    def art(name: str, rel: str, artifact_type: str, summary: str, extra: dict | None = None) -> dict:
        e = dict(base, event_id=f"w014-n0x-{STAMP}-artifact-{name}", event_type="artifact",
                 artifact_type=artifact_type, path=rel, sha256=deliverables[rel], summary=summary,
                 validation_status="unverified",
                 evidence_refs=[f"{rel}#{deliverables[rel][:12]}",
                                "numerics/protocol/lifecycle08_stoprule_closure_verify.json#88ec0bf298cb"])
        if extra:
            e.update(extra)
        return e

    events = [
        art("report", "artifacts/worker-14/n0_closure_crossverify/report.json",
            "n0_closure_crossverify_report",
            "W014-GNUM-N0-CLOSURE-CROSSVERIFY-01: second independent read-only verdict on T1 "
            "(lifecycle08 stop-rule closure 88ec0bf298cb) and T2 (worker-017 review 87b311e72032). "
            "Verdict N0_CLOSURE_AND_FIRST_REVIEW_CROSSVERIFIED_ACCEPT: 20/20 checks, 0 flags, "
            "12/12 controls, 21/21 pins pre/post stable, deterministic re-run.",
            {"controls_passed": True, "controls_total": 12}),
        art("instrument", "artifacts/worker-14/n0_closure_crossverify/verify_n0_closure_x.py",
            "instrument",
            "Independent re-implementation (own log-log LSQ and registration classifier; does not "
            "import worker-017's instrument or any numerics generator). Read-only; fail-closed pin "
            "gate, 10 sections, 12 in-memory controls, pre/post drift guard."),
        art("prereg", "artifacts/worker-14/n0_closure_crossverify/PRE_REGISTRATION.md",
            "pre_registration",
            "Predictions P1-P10 and the falsifier declared before the instrument was implemented or "
            "run; every prediction held. No prediction was re-labelled."),
        art("readme", "artifacts/worker-14/n0_closure_crossverify/README.md",
            "readme",
            "Task record: why, result table, advisories, exact reproduction, scope limits."),
    ]

    findings = [
        "X2: own LSQ over the raw cert rows reproduces cert, rev3 and the closure exactly (worst abs "
        "diff 0.0e+00 over 3 schemes x 8 quantities); |p-2| <= 1.36e-4 << 0.3; ladders strictly "
        "monotone; cross-scheme spread 7.958116929374093e-05 <= 0.25.",
        "X4: live taxonomy 0abb9ed8a961 rev5 contains AF-WCC-SCALAR-SPH; authority record "
        "effd20b0ea09 binding sha/revision and carrier da7c36071995 agree.",
        "X5: frozen module 8ade1cdc163e cert+disk; w046 SUPPORTED / w057 REPRODUCED / w081 accept "
        "all hash-match; flash-13 accept 4.0 binds rev3 da7c36071995 and discloses F-06.",
        "X6: numerics_lock=locked, no spherical_solver, gates.evaluate production_allowed=false.",
        "X7 (advisory, non-blocking): closure labels research_map/formulation_taxonomy.yaml "
        "'unregistered' but it is top-level-match in runtime/state/artifact_hashes.json#hashes at the "
        "same sha; the three reviewer-verdict artifacts are genuinely unregistered; stale pin "
        "reviews/G-NUM-protocol-review.json#1e6cdf04d7a2 (disk 8137f18f1a3b) confirmed.",
        "X8: T2's bytes match its declared hash 87b311e72032, its 4 sub-refs resolve, its pinned copy "
        "is byte-identical to live T1, and all seven findings are consistent with my independent "
        "measurements.",
        "Gate-blocker outside scope (reproduced from T2/F05): a clean N0 accept still awaits B-N0-R2-2 "
        "(contested protocol review) and the registration gap; G-NUM stays pending.",
    ]
    events.append(dict(base, event_id=f"w014-n0x-{STAMP}-review-closure", event_type="review",
                       target_id="numerics/protocol/lifecycle08_stoprule_closure_verify.json",
                       reviewer="worker-014 (independent of the author astra-lead-numerics)",
                       verdict="accept", score=4.0, hard_failures=[], findings=findings,
                       counts_as_gate_verdict=False, counts_as_node_verdict=False,
                       evidence_refs=[f"numerics/protocol/lifecycle08_stoprule_closure_verify.json#88ec0bf298cb",
                                      f"artifacts/worker-14/n0_closure_crossverify/report.json#{deliverables['artifacts/worker-14/n0_closure_crossverify/report.json'][:12]}",
                                      "numerics/protocol/n0_fixed_dt_certification.json#1677822ceb9c",
                                      "numerics/results/flat_wave_convergence_rev3.json#da7c36071995"]))
    events.append(dict(base, event_id=f"w014-n0x-{STAMP}-review-first-review", event_type="review",
                       target_id="reviews/N0-stoprule-closure-review-worker-017.json",
                       reviewer="worker-014 (independent of worker-017; instrument written without reading theirs)",
                       verdict="accept", score=4.0, hard_failures=[],
                       counts_as_gate_verdict=False, counts_as_node_verdict=False,
                       findings=["T2 integrity verified at 87b311e72032: 4/4 evidence refs resolve "
                                 "(report d3d7c450ebc5, crosscheck 749090f9a2ba, instrument ba56eade7561, "
                                 "pinned copy 88ec0bf298cb); pinned copy byte-identical to live T1; "
                                 "F01-F07 consistent with my independent recomputation; counts_as_gate_verdict "
                                 "and counts_as_node_verdict correctly false."],
                       evidence_refs=["reviews/N0-stoprule-closure-review-worker-017.json#87b311e72032",
                                      "artifacts/worker-017/n0_stoprule_closure_verify/report.json#d3d7c450ebc5",
                                      "artifacts/worker-017/n0_stoprule_closure_verify/registration_crosscheck.json#749090f9a2ba"]))
    events.append(dict(base, event_id=f"w014-n0x-{STAMP}-claim", event_type="claim",
                       conclusion_type="numerical_evidence_and_process_audit",
                       assumptions=["the bounded pinned input set is the verification surface",
                                    "the reviewed revision is the bytes at the declared hashes; later "
                                    "writes void the verdict for the new bytes"],
                       statement="At the pinned hashes T1 numerics/protocol/lifecycle08_stoprule_closure_verify.json"
                                 "#88ec0bf298cb and T2 reviews/N0-stoprule-closure-review-worker-017.json#87b311e72032 "
                                 "survive a second independent read-only cross-verification: the four-rung fixed-dt "
                                 "order claim is reproduced exactly from raw rows by a separate LSQ implementation "
                                 "(3 schemes, |p-2|<=1.36e-4, spread 7.958116929374093e-05<=0.25), the F0 rev5 rebind "
                                 "and the three hash-pinned replication verdicts resolve as declared, the numeric lock "
                                 "guard holds, T2's evidence chain is intact and consistent with the recomputation, "
                                 "12/12 controls fire and all 21 pinned inputs are byte-stable across the run.",
                       evidence_refs=[f"artifacts/worker-14/n0_closure_crossverify/report.json#{deliverables['artifacts/worker-14/n0_closure_crossverify/report.json'][:12]}",
                                      "numerics/protocol/lifecycle08_stoprule_closure_verify.json#88ec0bf298cb",
                                      "reviews/N0-stoprule-closure-review-worker-017.json#87b311e72032",
                                      "numerics/protocol/n0_fixed_dt_certification.json#1677822ceb9c",
                                      "numerics/results/flat_wave_convergence_rev3.json#da7c36071995"]))
    events.append(dict(base, event_id=f"w014-n0x-{STAMP}-status", event_type="status",
                       status="active", hours=0.6,
                       summary="CHECKPOINT + EXIT / worker-014. One bounded class-bound task taken (no inbox "
                               "card for this slot): W014-GNUM-N0-CLOSURE-CROSSVERIFY-01, a second independent "
                               "worker-level verdict on the N0 stop-rule closure package now feeding "
                               "astra-life04-n0-verify. Verdict N0_CLOSURE_AND_FIRST_REVIEW_CROSSVERIFIED_ACCEPT: "
                               "20/20 checks, 0 flags, 12/12 controls, 21/21 pins stable, deterministic re-run. "
                               "Advisories: taxonomy top-level-match vs T1's 'unregistered' label; 3 verdict "
                               "artifacts remain unregistered; stale pin 8137f18f confirmed. G-NUM stays pending "
                               "(B-N0-R2-2 outside scope). Worker-level only: no gate verdict, no node completion, "
                               "no canonical write.",
                       next_falsifier=FALSIFIER,
                       evidence_refs=[f"runtime/state/w014_n0_closure_crossverify_checkpoint.json#{deliverables[ckpt_rel][:12]}",
                                      f"artifacts/worker-14/n0_closure_crossverify/report.json#{deliverables['artifacts/worker-14/n0_closure_crossverify/report.json'][:12]}",
                                      "numerics/protocol/lifecycle08_stoprule_closure_verify.json#88ec0bf298cb",
                                      "reviews/N0-stoprule-closure-review-worker-017.json#87b311e72032"]))

    # checkpoint artifact event, emitted last so its hash is the written file's
    events.insert(4, art("checkpoint", ckpt_rel, "checkpoint",
                         "Runtime checkpoint: verdict, targets, measured pins, deliverable hashes, event ids, "
                         "next falsifier."))

    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            if line.strip():
                try:
                    existing.add(json.loads(line).get("event_id"))
                except json.JSONDecodeError:
                    pass
    OUTBOX.parent.mkdir(parents=True, exist_ok=True)
    added = 0
    with OUTBOX.open("a") as fh:
        for e in events:
            if e["event_id"] in existing:
                continue
            fh.write(json.dumps(e, sort_keys=True) + "\n")
            added += 1
    print(f"emitted {added}/{len(events)} events -> {OUTBOX}")
    print(f"checkpoint {ckpt_rel}#{deliverables[ckpt_rel][:12]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
