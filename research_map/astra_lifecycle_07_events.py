"""Controller event emission for the astra-lifecycle-07 pass (idempotent).

Emits hash-bound gate records, ONE bounded independent-review assignment for the landed
CLASSSEP r3 adjudication, and the pass-07 rulings (detector third write, downward-channel
injection, G-FORM coverage, lock hold). Re-running is safe: duplicate event_ids are skipped
by the accepted stream and already-sent inbox cards are not re-sent.

Measured at emission (fail-closed if a pinned path is absent; detector MUST be the restored
adjudicated bytes a8c04fc31e4a):
  F0 0abb9ed8a961 + companion d7419b4e8963; F1/F2a/F2b rev13 d9cebb9404b2 / e9a27996dfd3 /
  b2ab6acb2bbe under FROZEN rev29 815e08079aef; case corpus ccf7041bd0ff;
  L0 a1674f094979; L1 315c19145065; A0 rubric d748a9e3574e;
  adjudication 7714ffd5b467; census tool fc92f4eac503; map snapshot f344ed2aaea5;
  detector a8c04fc31e4a (restored); unauthorized bytes e36b0d644ca preserved as evidence.

Rulings: G-F0 stays PASS at unchanged bytes. G-FORM/G-LIT/G-NUM/G-AUDIT stay pending with
  refreshed hash-bound reasons (F2b still 0 accepts; L0 2 accepts vs 5 revise; G-NUM C8 met
  but N0 revise 3.5; G-AUDIT decision (c) review-pending). Detector writes stay frozen; the
  active frozen pin stays c266dbecaa87; e36b0d644ca is void and was mechanically restored.
  numerics_lock stays LOCKED; no N1 work and no solver anywhere in this pass.

  python3 research_map/astra_lifecycle_07_events.py
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
CASES = measure("schemas/taxonomy_cases.jsonl")
L0 = measure("ledger/theorems.jsonl")
L1 = measure("ledger/citation_audit.csv")
A0 = measure("evaluation_rubric.yaml")
A0SCOPE = measure("evaluation/A0_detector_scope_adjudication.json")
PROTO = measure("numerics/CONVERGENCE_PROTOCOL.md")
NGATES = measure("numerics/gates.py")
N0REV3 = measure("numerics/results/flat_wave_convergence_rev3.json")
ADJ = measure("reviews/CLASSSEP-calibration-adjudication.json")
CENSUS = measure("artifacts/audit/classsep_r3_adjudication.py")
SNAP = measure("artifacts/audit/classsep_r3_map_snapshot_20260912T010324.json")
DET = measure("research_map/class_separation.py")
REG = measure("runtime/bin/classsep_regression.py")

DET_PIN = "c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920"
DET_RESTORED = "a8c04fc31e4afa1b691cd6bfb6bf8b4f953a0adc925939a8351bab9cf453c5bd"
DET_VOID = "e36b0d644ca75b1efc291b44a3188facb7839d81790073341431f3bb77b86eed"
if DET != DET_RESTORED:
    raise SystemExit(f"FAIL-CLOSED: detector is not the restored adjudicated bytes: {DET[:12]}")
if not (ROOT / "runtime/state/controller_verification/class_separation.e36b0d644ca.evidence.py").is_file():
    raise SystemExit("FAIL-CLOSED: void-revision evidence copy absent")
if hashlib.sha256((ROOT / "runtime/state/controller_verification/class_separation.e36b0d644ca.evidence.py").read_bytes()).hexdigest() != DET_VOID:
    raise SystemExit("FAIL-CLOSED: void-revision evidence copy hash mismatch")

DEC06 = "runtime/state/controller_verification/astra-lifecycle-06-decisions.json"
DEC07 = "runtime/state/controller_verification/astra-lifecycle-07-decisions.json"
FORENSICS = "runtime/state/controller_verification/cf29-detector-write-forensics.json"
Q_ASTRA = "runtime/state/comms_quarantine/astra-inbox-line3-20260912T0112.jsonl"
Q_AUDIT = "runtime/state/comms_quarantine/astra-lead-audit-inbox-lines24-25-27-20260912T0112.jsonl"

# ---------------------------------------------------------------- gate records
GATES = [
    {
        "event_id": "astra-life07-gate-gf0", "event_type": "gate", "actor": "astra",
        "created_at": NOW, "gate_id": "G-F0", "scope": "F0", "verdict": "pass",
        "criteria": (
            "Re-asserted MET at unchanged bytes: declared taxonomy " + F0[:12] + " (rev5) + "
            "companion class-contract supplement " + F0_SUP[:12] + " (REC-3: distinct artifacts, "
            "byte-identity not required); pass-07 gate audit counts 7 distinct independent accept "
            "reviewers at the measured hash (deepseek-flash-18, deepseek-flash-19, worker-025, "
            "worker-038, worker-041, worker-052, worker-078) with worker-094 revise noted; 6/6 "
            "disjointness pairs; bytes stable. Any write to research_map/formulation_taxonomy.yaml "
            "voids this verdict and requires fresh accepts at the new hash."),
        "evidence_refs": ["research_map/formulation_taxonomy.yaml#" + F0[:12],
                          "artifacts/formulation/formulation_taxonomy.yaml#" + F0_SUP[:12],
                          "research_map/research_map.json#controller_gate_audit", DEC07],
    },
    {
        "event_id": "astra-life07-gate-gform", "event_type": "gate", "actor": "astra",
        "created_at": NOW, "gate_id": "G-FORM", "scope": "F1,F2a,F2b", "verdict": "pending",
        "criteria": (
            "Measured pins unchanged: F1 " + F1[:12] + ", F2a " + F2A[:12] + ", F2b " + F2B[:12]
            + " under FROZEN rev29 " + FROZEN[:12] + ", case corpus " + CASES[:12] + "; all three "
            "mirror pairs aligned. Coverage at the rev29 pins: F1 4 distinct accepts (worker-052, "
            "worker-072, worker-075, worker-085), F2a 2 (worker-017, worker-072), F2b 0 (worker-017 "
            "and worker-075 revise; F2b additionally needs >=2 accepts at one stable hash). "
            "astra-life05-verify-gform-r3 must adjudicate non-author independence at the measured "
            "hashes and cite the FROZEN bytes plus each per-file pin (CF-27 moving-target rule); "
            "superseded-hash verdicts are advisory only. No gate moves on counts alone."),
        "evidence_refs": ["schemas/af_wcc_vacuum.yaml#" + F1[:12],
                          "schemas/af_scc_c2_vacuum.yaml#" + F2A[:12],
                          "schemas/af_scc_c0_vacuum.yaml#" + F2B[:12],
                          "artifacts/formulation/FROZEN.json#" + FROZEN[:12],
                          "schemas/taxonomy_cases.jsonl#" + CASES[:12],
                          "research_map/research_map.json#controller_gate_audit", DEC07],
    },
    {
        "event_id": "astra-life07-gate-glit", "event_type": "gate", "actor": "astra",
        "created_at": NOW, "gate_id": "G-LIT", "scope": "L0,L1", "verdict": "pending",
        "criteria": (
            "L0 measured " + L0[:12] + " (rev3-final): 2 distinct full accepts (worker-075, "
            "worker-079) against 5 revise (worker-025, worker-011, worker-093, deepseek-flash-18, "
            "worker-005) and 1 inconclusive (worker-063) - astra-life05-verify-l0-final must "
            "adjudicate whether the accepts bind the primary-source ledger or only a card subset. "
            "L1 measured " + L1[:12] + " with 23 independent re-fetch spot checks binding this "
            "hash; the L1 locator adjudication (worker-025: 71/97 exact_locator values are not "
            "record locators) is a live revise and must be dispositioned. No gate moves on spot "
            "checks alone."),
        "evidence_refs": ["ledger/theorems.jsonl#" + L0[:12],
                          "ledger/citation_audit.csv#" + L1[:12],
                          "reviews/L0-review-worker-079.json",
                          "reviews/L1-locator-adjudication-025.json",
                          "research_map/research_map.json#controller_gate_audit", DEC07],
    },
    {
        "event_id": "astra-life07-gate-gnum", "event_type": "gate", "actor": "astra",
        "created_at": NOW, "gate_id": "G-NUM", "scope": "N0", "verdict": "pending",
        "criteria": (
            "self-gravitating numerics remain LOCKED (solver_absent=True, guard_present=True); "
            "protocol " + PROTO[:12] + " criterion C8 is MET (standing accept 4.5 binds this hash); "
            "N0 node verdict on disk is revise 3.5 and the stop-rule deliverable " + N0REV3[:12] +
            " still needs an N0 accept at one measured hash (astra-life04-n0-verify) with the "
            "convergence order independently replicated and the protocol review of record. Guard "
            "and gates code: " + NGATES[:12] + ". N1 remains forbidden regardless: it additionally "
            "requires G-FORM and G-AUDIT (numerics_lock required_gates)."),
        "evidence_refs": ["numerics/CONVERGENCE_PROTOCOL.md#" + PROTO[:12],
                          "numerics/results/flat_wave_convergence_rev3.json#" + N0REV3[:12],
                          "numerics/gates.py#" + NGATES[:12],
                          "research_map/research_map.json#numerics_lock",
                          "research_map/research_map.json#controller_gate_audit", DEC07],
    },
    {
        "event_id": "astra-life07-gate-gaudit", "event_type": "gate", "actor": "astra",
        "created_at": NOW, "gate_id": "G-AUDIT", "scope": "A0,A1", "verdict": "pending",
        "criteria": (
            "A0 rubric " + A0[:12] + " exists; A0 detector-scope artifact " + A0SCOPE[:12] +
            " landed unverified (astra-life04-verify-a0). A1 coverage at measured hashes: F0 7, F1 "
            "4, F2a 2, F2b 0, L0 2 distinct accepts (>=2 each required; superseded-hash verdicts do "
            "not count). The CLASSSEP r3 adjudication " + ADJ[:12] + " landed with decision (c) - "
            "assertion-vs-mention is not lexically separable, no adoption, no retirement, raw hard "
            "count stands - and is review-pending (astra-life07-classsep-adjudication-review). "
            "G-AUDIT stays pending; no gate self-pass."),
        "evidence_refs": ["evaluation_rubric.yaml#" + A0[:12],
                          "evaluation/A0_detector_scope_adjudication.json#" + A0SCOPE[:12],
                          "reviews/CLASSSEP-calibration-adjudication.json#" + ADJ[:12],
                          "research_map/research_map.json#controller_gate_audit", DEC07],
    },
]

# ---------------------------------------------------------------- assignments
CARD = dict(event_type="assignment", actor="astra", created_at=NOW)
ASSIGNMENTS = [
    {
        **CARD, "event_id": "astra-life07-classsep-adjudication-review",
        "node_id": "A1", "assignee": "worker-075", "gate": "G-AUDIT", "class_id": "GLOBAL",
        "artifact": "reviews/CLASSSEP-calibration-adjudication-review.json",
        "deadline": "2026-09-12T02:30:00+08:00", "budget_agent_hours": 1.5,
        "evidence_refs": [
            "reviews/CLASSSEP-calibration-adjudication.json#" + ADJ[:12],
            "artifacts/audit/classsep_r3_adjudication.py#" + CENSUS[:12],
            "artifacts/audit/classsep_r3_map_snapshot_20260912T010324.json#" + SNAP[:12],
            "artifacts/worker-049/classsep_fn_audit/pinned/class_separation_c266_recovered.py#" + DET_PIN[:12],
            "research_map/class_separation.py#" + DET_RESTORED[:12],
            FORENSICS,
            DEC07,
        ],
        "acceptance": (
            "Exactly one INDEPENDENT non-author review of the landed r3 CLASSSEP adjudication at "
            "the frozen hashes. Reproduce, read-only: (i) the 27-fixture regression 17TP/0FP/10TN/"
            "0FN at each cited arm; (ii) the APPLIED live census hard=19 = 17 labeled metalinguistic "
            "FP + 2 unlabeled DETECTOR_SELF meta-claims at snapshot " + SNAP[:12] + "; (iii) the "
            "per-arm sensitivity/specificity table (APPLIED 4/6-3/10, PRE 4/6-1/10, STAGED 5/6-1/10, "
            "PROSEFIX 4/6-10/10 with 10 HIGH cue-FN) and confirm no arm meets "
            "sens>=5/6 AND spec>=9/10 AND 27-fixture PASS AND 0 HIGH cue-induced FN; (iv) the "
            "attribution correction - the 10/10 cue-carrying suppression belongs to "
            "dc8aa0de3869 (prosefix), NOT e2d24b92 (staged), whose rejection rests on the FP axis; "
            "(v) detector bytes research_map/class_separation.py are the restored "
            + DET_RESTORED[:12] + " before and after the review, and the void revision "
            + DET_VOID[:12] + " stays out. Deliver a per-fixture TP/FP/FN census plus exactly one "
            "verdict (accept|revise|reject|inconclusive). Freeze: no detector write, no schema/"
            "ledger/claim edit, no gate self-pass. If any cited hash fails to reproduce, STOP and "
            "report inconclusive rather than repairing it."),
        "expected_information_gain": (
            "Closes the REC-22 round with an independent reproduction of decision (c) and its "
            "residual hard count, so the controller can decide whether to open a bounded successor "
            "detector round or record assertion-vs-mention as a documented instrument limit."),
        "falsifier": (
            "Any arm meeting the adoption bar at unchanged hashes; a genuine first-order C0/C2 "
            "merge assertion among the claims labeled metalinguistic FP; non-reproducible counts in "
            "artifacts/audit/classsep_r3_adjudication.py; or a detector write during the review."),
        "stop_rule": (
            "Stop on detector move, hash mismatch, or an unreproducible census; report the contest "
            "as unresolved with the failing pin. No gate verdict, no adoption, no N1 work."),
    },
]

# ------------------------------------------------------------------- notices
NOTICES = [
    {
        "event_id": "astra-life07-notice-classsep-r3", "event_type": "status", "actor": "astra",
        "created_at": NOW, "node_id": "A1", "status": "active", "hours": 0.1,
        "summary": (
            "Controller ruling (REC-29/30, CF-16/CF-26/CF-29): the r3 adjudication " + ADJ[:12] +
            " landed with exactly one decision (c) - assertion-vs-mention is NOT lexically "
            "separable at this window; no adoption, no rollback-by-audit, no claim retirement; "
            "residual hard count 19 (17 labeled FP + 2 meta) and the A04 clause FN stay live. "
            "G-AUDIT stays pending. astra-life07-classsep-adjudication-review (worker-075, "
            "non-author, deadline 02:30) must now independently reproduce the census and the "
            "attribution correction. The instrument moved a THIRD time during the freeze "
            "(a8c04fc31e4a -> e36b0d644ca at 01:06:12, no authorizing event): e36b0d644ca is void "
            "and preserved as evidence, the active pin stays " + DET_PIN[:12] + ", and the live "
            "bytes were mechanically restored to the adjudicated " + DET_RESTORED[:12] +
            " before the review. Any further detector write voids the round."),
        "evidence_refs": ["reviews/CLASSSEP-calibration-adjudication.json#" + ADJ[:12],
                          "research_map/class_separation.py#" + DET_RESTORED[:12], FORENSICS,
                          "runtime/state/controller_verification/class_separation.e36b0d644ca.evidence.py",
                          DEC07],
        "next_falsifier": "A detector write while the review is open, or a review that cannot "
                          "reproduce a cited count at a named hash.",
    },
    {
        "event_id": "astra-life07-notice-injection", "event_type": "status", "actor": "astra",
        "created_at": NOW, "node_id": "A1", "status": "active", "hours": 0.1,
        "summary": (
            "Controller ruling (REC-31, CF-30): cards attributed to actor 'astra' appeared in "
            "comms/inbox/astra.jsonl line 3 and comms/inbox/astra-lead-audit.jsonl lines 24, 25, "
            "27 (human-pi-detector-fix-20260912T0100 / astra-detector-fix-0105 / "
            "astra-detector-patch-result-0112) with no accepted-stream emission and no controller "
            "lifecycle record; one is future-dated and written early, one reports the 01:06:12 "
            "detector state. They are NOT authority, are quarantined byte-verbatim, and are not "
            "actioned. The audit lead's refusal to author the detector it measures "
            "(audit-l07-b4) is upheld: the detector edit is not reassigned to audit. Their state "
            "claim is independently corroborated (CF-29) and recorded as evidence only. A genuine "
            "Human-PI directive must be re-sent as a well-formed accepted event; writers must not "
            "hand-edit inbox JSONL."),
        "evidence_refs": [Q_ASTRA, Q_AUDIT, FORENSICS, "comms/PROTOCOL.md", DEC07],
        "next_falsifier": "A card in any inbox whose event_id never appears in the accepted "
                          "stream, or a second write to an instrument under freeze.",
    },
    {
        "event_id": "astra-life07-notice-attribution-correction", "event_type": "status",
        "actor": "astra", "created_at": NOW, "node_id": "A1", "status": "active", "hours": 0.1,
        "summary": (
            "Controller record correction (REC-32, audit-l07-b6): the pass-06 card "
            "astra-life06-classsep-detector-adjudication attributed '10/10 cue-carrying genuine "
            "assertions suppressed, 9 HIGH' to proposed/class_separation.py e2d24b927ee8. Measured "
            "by the r3 census: that suppression belongs to "
            "artifacts/worker-049/classsep_prose_fix/class_separation_prosefix.py dc8aa0de3869; "
            "e2d24b92 clears 0 cue-carrying assertions. The staged candidate's rejection stands, "
            "but on the FP axis (specificity 1/10), not on the FN evidence. No event is edited: "
            "this correction is the operative record."),
        "evidence_refs": ["reviews/CLASSSEP-calibration-adjudication.json#" + ADJ[:12],
                          "artifacts/worker-049/classsep_fn_audit/results.json#9e1bf2043934",
                          DEC07],
        "next_falsifier": "A later event that re-conflates the two staged artifacts.",
    },
    {
        "event_id": "astra-life07-notice-gform-coverage", "event_type": "status", "actor": "astra",
        "created_at": NOW, "node_id": "F1", "status": "active", "hours": 0.1,
        "summary": (
            "Controller coverage notice (REC-33, CF-20/CF-27): at the unchanged rev29 pins F1 "
            + F1[:12] + " has 4 distinct accepts (worker-052/072/075/085), F2a " + F2A[:12] +
            " has 2 (worker-017/072), and F2b " + F2B[:12] + " still has 0 accepts while its recent "
            "verdicts are revise (worker-017, worker-075). The standing astra-life05-verify-gform-r3 "
            "(audit lead, 02:45) must adjudicate non-author independence at the measured hashes; "
            "reviewers must pin FROZEN " + FROZEN[:12] + " plus each per-file pin. No gate movement "
            "on coverage counts alone; F2b needs >=2 independent accepts at one stable hash."),
        "evidence_refs": ["schemas/af_wcc_vacuum.yaml#" + F1[:12],
                          "schemas/af_scc_c2_vacuum.yaml#" + F2A[:12],
                          "schemas/af_scc_c0_vacuum.yaml#" + F2B[:12],
                          "artifacts/formulation/FROZEN.json#" + FROZEN[:12], DEC07],
        "next_falsifier": "A gate verdict bound to a superseded or mid-round-moving hash.",
    },
    {
        "event_id": "astra-life07-notice-gform-coverage-update", "event_type": "status",
        "actor": "astra", "created_at": NOW, "node_id": "F1", "status": "active", "hours": 0.1,
        "summary": (
            "Controller coverage update (REC-33 correction): the pass-07 final gate audit at "
            "01:09:51 measured the rev29 pins with F1 " + F1[:12] + " 4 distinct accepts, F2a "
            + F2A[:12] + " 2, and F2b " + F2B[:12] + " now 2 distinct full accepts (worker-072, "
            "worker-090) - superseding the F2b=0 snapshot in astra-life07-notice-gform-coverage "
            "and in the astra-life07-gate-gform record text. F2b also carries revise verdicts "
            "landed after the accepts (worker-002, worker-023, worker-050, worker-066). G-FORM "
            "stays pending: astra-life05-verify-gform-r3 must still adjudicate non-author "
            "independence at the measured hashes, weigh the late revise verdicts, and bind FROZEN "
            + FROZEN[:12] + " plus each per-file pin. No verdict changes on coverage."),
        "evidence_refs": ["schemas/af_scc_c0_vacuum.yaml#" + F2B[:12],
                          "artifacts/formulation/FROZEN.json#" + FROZEN[:12],
                          "research_map/research_map.json#controller_gate_audit", DEC07],
        "next_falsifier": "A G-FORM verdict that ignores the late F2b revise verdicts or binds a "
                          "superseded hash.",
    },
    {
        "event_id": "astra-life07-notice-lock", "event_type": "status", "actor": "astra",
        "created_at": NOW, "node_id": "N0", "status": "active", "hours": 0.1,
        "summary": (
            "Controller ruling (REC-34, CF-10/CF-22): numerics_lock remains LOCKED; guard present, "
            "solver absent, N1 hash absent; no N1 allocation and no self-gravitating work in this "
            "pass. G-NUM stays pending: criterion C8 is MET at protocol " + PROTO[:12] + " but the "
            "N0 node verdict on disk is still revise 3.5 and astra-life04-n0-verify must land an N0 "
            "accept at one hash with the convergence order independently replicated. G-NUM passing "
            "would certify N0 only; N1 additionally requires G-FORM + G-AUDIT."),
        "evidence_refs": ["numerics/gates.py#" + NGATES[:12],
                          "numerics/CONVERGENCE_PROTOCOL.md#" + PROTO[:12],
                          "research_map/research_map.json#numerics_lock", DEC07],
        "next_falsifier": "Any solver/N1 artifact or an N1 hash appearing while locked.",
    },
]

# inbox delivery: the assignment goes to its assignee; the two integrity/lock rulings go to
# the running audit lead as well (no canonical path duplication, CF-12).
NOTIFY = {
    "astra-life07-classsep-adjudication-review": ["worker-075"],
    "astra-life07-notice-classsep-r3": ["astra-lead-audit"],
    "astra-life07-notice-injection": ["astra-lead-audit"],
    "astra-life07-notice-gform-coverage-update": ["astra-lead-audit"],
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
                               "F2b": F2B[:12], "FROZEN": FROZEN[:12], "cases": CASES[:12],
                               "L0": L0[:12], "L1": L1[:12], "A0": A0[:12], "A0scope": A0SCOPE[:12],
                               "proto": PROTO[:12], "ngates": NGATES[:12], "N0rev3": N0REV3[:12],
                               "adjudication": ADJ[:12], "census": CENSUS[:12], "snapshot": SNAP[:12],
                               "detector": DET[:12], "regression": REG[:12],
                               "detector_pin": DET_PIN[:12], "detector_void": DET_VOID[:12]}))


if __name__ == "__main__":
    main()
