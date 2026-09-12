"""Controller event emission for the astra-indep-2 / pass-09 lifecycle (idempotent).

One independent controller lifecycle. Emits hash-bound gate records, ONE new bounded
assignment for the genuinely new blocking work (CF-33 injection containment), and the
pass-09 rulings. Re-running is safe: duplicate event_ids are skipped by the accepted
stream and already-sent inbox cards are not re-sent.

Measured at emission (fail-closed on the G-F0 taxonomy pin and the restored detector):
  F0 0abb9ed8a961 + companion d7419b4e8963; F1/F2a/F2b d9cebb9404b2 / e9a27996dfd3 /
  b2ab6acb2bbe under FROZEN rev29 815e08079aef; detector a8c04fc31e4a (restored;
  pin c266dbecaa87; void e36b0d644ca preserved byte-verbatim).

Rulings (REC-43):
  G-F0 stays PASS at unchanged bytes (any taxonomy write voids it).
  G-FORM/G-LIT/G-NUM/G-AUDIT stay pending with refreshed hash-bound `unmet` lists.
  REC-43 CF-33: the injected 'astra-classsep-stabilize-0118' card (byte-identical in
    comms/inbox/astra.jsonl:4 and comms/inbox/astra-lead-audit.jsonl:31) has no
    accepted-stream emission, no lifecycle emission and a dangling artifact ref; it is
    not authority, not actioned, quarantined byte-verbatim, and the CF-29 detector
    freeze and REC-38 review satisfaction stand. One read-only containment scan is
    assigned to worker-093.
  numerics_lock stays LOCKED; N1 forbidden; G-NUM would certify N0 only.

  python3 research_map/astra_lifecycle_09_events.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research_map"))
import comms  # noqa: E402

CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")


def measure(rel: str) -> str:
    p = ROOT / rel
    if not p.is_file():
        raise SystemExit(f"FAIL-CLOSED: pinned path absent: {rel}")
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


F0 = measure("research_map/formulation_taxonomy.yaml")
F0_SUP = measure("artifacts/formulation/formulation_taxonomy.yaml")
F1 = measure("schemas/af_wcc_vacuum.yaml")
F2A = measure("schemas/af_scc_c2_vacuum.yaml")
F2B = measure("schemas/af_scc_c0_vacuum.yaml")
FROZEN = measure("artifacts/formulation/FROZEN.json")
SUITE = measure("schemas/f1_falsifier_tests.jsonl")
L0 = measure("ledger/theorems.jsonl")
L1 = measure("ledger/citation_audit.csv")
A0 = measure("evaluation_rubric.yaml")
PROTO = measure("numerics/CONVERGENCE_PROTOCOL.md")
N0REV3 = measure("numerics/results/flat_wave_convergence_rev3.json")
DET = measure("research_map/class_separation.py")

F0_PASS = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
DET_PIN = "c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920"
DET_RESTORED = "a8c04fc31e4afa1b691cd6bfb6bf8b4f953a0adc925939a8351bab9cf453c5bd"
DET_VOID = "e36b0d644ca75b1efc291b44a3188facb7839d81790073341431f3bb77b86eed"
Q_ASTRA = "runtime/state/comms_quarantine/astra-inbox-line4-20260912T0120.jsonl"
Q_AUDIT = "runtime/state/comms_quarantine/astra-lead-audit-inbox-line31-20260912T0117.jsonl"
CF33 = "runtime/state/controller_verification/cf33-injection-provenance.json"
DEC08 = "runtime/state/controller_verification/astra-lifecycle-08-decisions.json"

if F0 != F0_PASS:
    raise SystemExit(f"FAIL-CLOSED: G-F0 taxonomy pin moved: {F0[:12]} != {F0_PASS[:12]}")
if DET != DET_RESTORED:
    raise SystemExit(f"FAIL-CLOSED: detector is not the restored adjudicated bytes: {DET[:12]}")
if not (ROOT / "runtime/state/controller_verification/class_separation.e36b0d644ca.evidence.py").is_file():
    raise SystemExit("FAIL-CLOSED: void-revision evidence copy absent")
if hashlib.sha256((ROOT / "runtime/state/controller_verification/class_separation.e36b0d644ca.evidence.py").read_bytes()).hexdigest() != DET_VOID:
    raise SystemExit("FAIL-CLOSED: void-revision evidence copy hash mismatch")
for q in (Q_ASTRA, Q_AUDIT):
    if not (ROOT / q).is_file():
        raise SystemExit(f"FAIL-CLOSED: CF-33 quarantine copy absent: {q}")
    if hashlib.sha256((ROOT / q).read_bytes()).hexdigest() != "3167994548db83fa05ac9cd2da758d24346a34df548e724e50095b3c26563f0d":
        raise SystemExit(f"FAIL-CLOSED: CF-33 quarantine copy hash mismatch: {q}")

# ---------------------------------------------------------------- gate records
GATES = [
    {
        "event_id": "astra-indep2-gate-gf0", "event_type": "gate", "actor": "astra",
        "created_at": NOW, "gate_id": "G-F0", "scope": "F0", "verdict": "pass",
        "owner": "lead-formulation", "eta": "0.0d",
        "criteria": (
            "F0 canonical taxonomy and companion supplement are hash-pinned; at least two "
            "independent review accepts bind the canonical bytes; no byte moves."),
        "unmet": [],
        "controller_note": (
            "Unchanged at pass 09: canonical " + F0[:12] + ", companion " + F0_SUP[:12] +
            "; seven distinct independent accepts bind " + F0[:12] + ". ANY write to "
            "research_map/formulation_taxonomy.yaml voids this pass (CF-21 residual stays recorded)."),
        "evidence_refs": ["research_map/formulation_taxonomy.yaml#" + F0[:12],
                          "artifacts/formulation/formulation_taxonomy.yaml#" + F0_SUP[:12],
                          "reviews/F0-review-rev27-b.json#152cae0efbe4",
                          "research_map/research_map.json#controller_gate_audit"],
    },
    {
        "event_id": "astra-indep2-gate-gform", "event_type": "gate", "actor": "astra",
        "created_at": NOW, "gate_id": "G-FORM", "scope": "F1,F2a,F2b", "verdict": "pending",
        "owner": "lead-formulation", "eta": "1.0d",
        "criteria": (
            "F1/F2a/F2b frozen and mirror-aligned; >=2 independent full-schema accepts per class "
            "at the measured hashes; F2b content defects discharged; acceptance/held-out evidence "
            "reproducible; token crosswalk pinned."),
        "unmet": [
            "F2b D1/D2 content defects and F2a extension-category pin are folded only by the "
            "authorized rev14 / FROZEN rev30 (astra-life08-formulation-rev14, due 02:15).",
            "CF-31 F2b coverage divergence: scan reports 4 full accepts at " + F2B[:12] +
            " (worker-052/071/072/090) while the formulation lead census reports 0 accept / 7 "
            "revise; astra-life05-verify-gform-r3 must publish a per-file binding table first.",
            "CF-32: run_acceptance.py exits 3 at rev29 and stage-B R03 rejects the untouched F1 " +
            F1[:12] + ", so acceptance and held-out numbers are not gate evidence until re-run "
            "(astra-life08-stageb-r03).",
            "Bytes move at rev14: every current verdict is void and r3 re-runs at the new pins.",
        ],
        "controller_note": "Pass-09 refresh; CF-31/CF-32 remain the binding blockers.",
        "evidence_refs": ["schemas/af_wcc_vacuum.yaml#" + F1[:12],
                          "schemas/af_scc_c2_vacuum.yaml#" + F2A[:12],
                          "schemas/af_scc_c0_vacuum.yaml#" + F2B[:12],
                          "artifacts/formulation/FROZEN.json#" + FROZEN[:12],
                          "schemas/f1_falsifier_tests.jsonl#" + SUITE[:12],
                          "research_map/research_map.json#controller_findings", DEC08],
    },
    {
        "event_id": "astra-indep2-gate-glit", "event_type": "gate", "actor": "astra",
        "created_at": NOW, "gate_id": "G-LIT", "scope": "L0,L1", "verdict": "pending",
        "owner": "lead-literature", "eta": "1.0d",
        "criteria": (
            "L0 theorem ledger adjudicated at a frozen hash with >=2 independent accepts and no "
            "unresolved hard failure; L1 citation audit >=3 independent re-fetch spot checks per "
            "the frozen protocol and locator policy dispositioned."),
        "unmet": [
            "L0 " + L0[:12] + ": 2 accepts vs 5 revise + 1 inconclusive and two rubric-scope "
            "objections; astra-life05-verify-l0-final (lead-audit, 02:30) must adjudicate.",
            "L1 " + L1[:12] + ": 24 binding re-fetch spot checks >=3 required, but the locator "
            "finding (71/97 search-query locators, replicated) has no disposition.",
            "The gate-unmet '201 citations' figure is not a measured universe "
            "(census: 151 sources / 77 theorems / 228 union / 388 class rows).",
        ],
        "controller_note": "Pass-09 refresh; no literature byte is frozen by this gate record.",
        "evidence_refs": ["ledger/theorems.jsonl#" + L0[:12],
                          "ledger/citation_audit.csv#" + L1[:12],
                          "reviews/INDEX.md", DEC08],
    },
    {
        "event_id": "astra-indep2-gate-gnum", "event_type": "gate", "actor": "astra",
        "created_at": NOW, "gate_id": "G-NUM", "scope": "N0,N1", "verdict": "pending",
        "owner": "lead-numerics", "eta": "1.0d",
        "criteria": (
            "N0 flat-space convergence order measured and independently replicated at a frozen "
            "hash; convergence protocol reviewed with C1-C8 discharged; N1 remains locked until "
            "G-FORM and G-AUDIT pass and this gate certifies N0 only."),
        "unmet": [
            "N0 node verdict on disk is still revise 3.5 (" + N0REV3[:12] + ").",
            "Stop-rule items open: astra-life04-n0-stoprule (lead-numerics, 02:30) and "
            "astra-life04-n0-verify (lead-audit, 03:00).",
            "numerics_lock stays LOCKED (solver_absent=True, guard_present=True); N1 is forbidden "
            "regardless of this gate.",
        ],
        "controller_note": "Pass-09 refresh; protocol " + PROTO[:12] + " C8 MET (standing accept 4.5).",
        "evidence_refs": ["numerics/CONVERGENCE_PROTOCOL.md#" + PROTO[:12],
                          "numerics/results/flat_wave_convergence_rev3.json#" + N0REV3[:12],
                          "research_map/research_map.json#numerics_lock", DEC08],
    },
    {
        "event_id": "astra-indep2-gate-gaudit", "event_type": "gate", "actor": "astra",
        "created_at": NOW, "gate_id": "G-AUDIT", "scope": "A0,A1", "verdict": "pending",
        "owner": "lead-audit", "eta": "1.0d",
        "criteria": (
            "A0 rubric verified at a frozen hash with one independent verdict resolving each "
            "prior finding and a bounded detector scope; A1 independent node review at the frozen "
            "instrument hashes; CF-31 coverage adjudicated; detector write freeze respected."),
        "unmet": [
            "A0 " + A0[:12] + ": 6 revise verdicts on disk, no accept; scope artifact unverified "
            "(astra-life04-verify-a0 + astra-life05-a0-detector-scope, lead-audit, 02:00).",
            "A1: no full accept at the measured hashes; CF-31 blocks any A1 coverage claim.",
            "CF-33: the injected 'astra-classsep-stabilize-0118' card is not authority and is not "
            "actioned; no detector write is authorized by it (REC-43).",
            "CF-29 detector freeze continues: live " + DET[:12] + " (pin " + DET_PIN[:12] +
            "); any further write voids the round.",
        ],
        "controller_note": "Pass-09 refresh; REC-38 review satisfaction stands.",
        "evidence_refs": ["evaluation_rubric.yaml#" + A0[:12],
                          "research_map/class_separation.py#" + DET[:12],
                          "runtime/state/controller_verification/cf29-detector-write-forensics.json",
                          CF33, DEC08],
    },
]

# ---------------------------------------------------------------- assignments
CARD = dict(event_type="assignment", actor="astra", created_at=NOW)
ASSIGNMENTS = [
    {
        **CARD, "event_id": "astra-indep2-cf33-containment",
        "node_id": "A1", "assignee": "worker-093", "gate": "G-AUDIT",
        "class_id": "GLOBAL",
        "artifact": "artifacts/worker-093/cf33_containment/report.json",
        "deadline": "2026-09-12T01:55:00+08:00", "budget_agent_hours": 0.5,
        "evidence_refs": [CF33, Q_ASTRA + "#3167994548db", Q_AUDIT + "#3167994548db",
                          "comms/inbox/astra.jsonl:4", "comms/inbox/astra-lead-audit.jsonl:31",
                          "research_map/class_separation.py#" + DET[:12],
                          "research_map/formulation_taxonomy.yaml#" + F0[:12]],
        "acceptance": (
            "Read-only containment scan for the CF-33 payload (verbatim sha256 3167994548db, line "
            "sha256 9ff2edc1e684, event_id astra-classsep-stabilize-0118) over the repo outside "
            ".git/runtime caches. Classify every hit: the two quarantine copies plus the two inbox "
            "lines are known; worker provenance/census mentions are observations, not authority. "
            "Deliver a hit census and exactly one verdict (accept|revise|reject|inconclusive) plus "
            "the pre/post sha256 of research_map/class_separation.py and "
            "research_map/formulation_taxonomy.yaml proving neither moved during the scan. NO "
            "detector, taxonomy, inbox, FROZEN or claim write; no gate verdict."),
        "expected_information_gain": (
            "Closes the CF-33 blast radius: proves the injected directive was not copied into any "
            "canonical artifact or acted on anywhere outside the two inbox lines."),
        "falsifier": (
            "A hit outside the four known locations that cites the card as authority or acts on "
            "it, or any byte move in the frozen detector/taxonomy during the scan window."),
        "stop_rule": (
            "Stop and report inconclusive on any frozen-pin move or if the scan would require "
            "editing a canonical artifact; do not restore or repair anything."),
    },
]

# ------------------------------------------------------------------- notices
NOTICES = [
    {
        "event_id": "astra-indep2-notice-cf33", "event_type": "status",
        "actor": "astra", "created_at": NOW, "node_id": "A1", "status": "active", "hours": 0.1,
        "summary": (
            "Controller ruling (REC-43): the assignment card 'astra-classsep-stabilize-0118' "
            "(byte-identical sha256 3167994548db in comms/inbox/astra-lead-audit.jsonl:31 and "
            "comms/inbox/astra.jsonl:4) is NOT authority and must not be actioned. It has no "
            "accepted-stream self-emission, no astra outbox record, no lifecycle emission, a "
            "future-dated created_at (01:18:00 vs inbox mtimes 01:12:31/01:16:23) and a dangling "
            "artifact ref reviews/CLASSSEP-stabilization-0118.json; it directs a detector write "
            "against CF-29/REC-29 and re-opens a review REC-38 already satisfied. Both copies are "
            "quarantined byte-verbatim; the measured provenance is at " + CF33 + ". The CF-29 "
            "detector freeze (live " + DET[:12] + ", pin " + DET_PIN[:12] + ", void " + DET_VOID[:12] +
            " preserved) and the standing audit assignments govern unchanged. worker-093 has the "
            "bounded read-only containment scan astra-indep2-cf33-containment."),
        "evidence_refs": [CF33, Q_ASTRA + "#3167994548db", Q_AUDIT + "#3167994548db",
                          "research_map/class_separation.py#" + DET[:12], DEC08],
        "next_falsifier": (
            "Any write to research_map/class_separation.py or research_map/formulation_taxonomy.yaml, "
            "or any artifact/claim that cites the forged card as authority."),
    },
    {
        "event_id": "astra-indep2-notice-lock", "event_type": "status",
        "actor": "astra", "created_at": NOW, "node_id": "N1", "status": "blocked", "hours": 0.1,
        "summary": (
            "numerics_lock stays LOCKED at pass 09: solver_absent=True, guard_present=True, N1 "
            "forbidden. N0 flat-space work may continue and is the only numerics path; G-NUM, if it "
            "passes, certifies N0 only. Stop-rule items due 02:30/03:00 remain the open requirement; "
            "no self-gravitating code or run."),
        "evidence_refs": ["research_map/research_map.json#numerics_lock",
                          "numerics/CONVERGENCE_PROTOCOL.md#" + PROTO[:12], DEC08],
        "next_falsifier": (
            "Any N1 artifact, solver file or self-gravitating run appearing while the lock is "
            "engaged, or a gate verdict citing N1."),
    },
]

NOTIFY = {
    "astra-indep2-cf33-containment": ["worker-093"],
    "astra-indep2-notice-cf33": ["astra-lead-audit", "astra-lead-formulation"],
    "astra-indep2-notice-lock": ["astra-lead-numerics"],
}


def _already_sent(agent: str, event_id: str) -> bool:
    p = ROOT / "comms" / "inbox" / f"{agent}.jsonl"
    if not p.exists():
        return False
    for line in p.read_text().splitlines():
        try:
            if json.loads(line).get("event_id") == event_id:
                return True
        except ValueError:
            continue
    return False


def main():
    for ev in GATES + ASSIGNMENTS + NOTICES:
        res = comms.append_event(ev)
        print(("APPENDED " if res.get("accepted") else "SKIPPED  ") + ev["event_id"] + " " + ev["event_type"])
    by_id = {e["event_id"]: e for e in ASSIGNMENTS + NOTICES}
    for eid, agents in NOTIFY.items():
        for agent in agents:
            if _already_sent(agent, eid):
                print(f"INBOX    already-sent <- {eid} [{agent}]")
                continue
            msg = dict(by_id[eid])
            msg["to"] = agent
            path = comms.send(agent, msg)
            print(f"INBOX    {path.relative_to(ROOT)} <- {eid} [{agent}]")
    print("pins:", json.dumps({"F0": F0[:12], "F0sup": F0_SUP[:12], "F1": F1[:12], "F2a": F2A[:12],
                               "F2b": F2B[:12], "FROZEN": FROZEN[:12], "suite": SUITE[:12],
                               "L0": L0[:12], "L1": L1[:12], "A0": A0[:12], "proto": PROTO[:12],
                               "N0rev3": N0REV3[:12], "detector": DET[:12], "pin": DET_PIN[:12],
                               "void": DET_VOID[:12]}))


if __name__ == "__main__":
    main()
