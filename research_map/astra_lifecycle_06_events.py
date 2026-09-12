"""Controller event emission for the astra-lifecycle-06 pass (idempotent).

Emits hash-bound gate records and the bounded detector-adjudication assignment at the
hashes measured on disk at run time. Re-running is safe: duplicate event_ids are
skipped by the accepted stream and already-sent inbox cards are not re-sent.

Measured at emission (fail-closed if a pinned path is absent):
  F0 declared taxonomy 0abb9ed8a961 + class-contract supplement d7419b4e8963 (REC-3);
  F1/F2a/F2b rev13 d9cebb9404b2 / e9a27996dfd3 / b2ab6acb2bbe (FROZEN rev29, mirrors aligned);
  case corpus ccf7041bd0ff; consistency evidence 9e335e9ba1bf;
  L0 a1674f094979 (rev3-final); L1 315c19145065; A0 rubric d748a9e3574e;
  A0 detector-scope adjudication a26be4b85706; protocol 1e6cdf04d7a2; gates.py fcd1d70991b6;
  N0 stop-rule deliverable da7c36071995; detector a8c04fc31e4a (drifted from pinned c266dbecaa87).

Rulings in this batch: G-F0 stays PASS at unchanged bytes; G-FORM/G-LIT/G-NUM/G-AUDIT stay
  pending with refreshed hash-bound reasons. The unrecorded detector write is NOT adopted and
  the frozen pin is NOT refreshed: astra-life06-classsep-detector-adjudication supersedes
  astra-life05-classsep-calibration. numerics_lock stays LOCKED; no N1 work and no solver
  anywhere in this pass.

  python3 research_map/astra_lifecycle_06_events.py
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
CONSIST = measure("artifacts/formulation/evidence/taxonomy_consistency.json")
L0 = measure("ledger/theorems.jsonl")
L1 = measure("ledger/citation_audit.csv")
A0 = measure("evaluation_rubric.yaml")
A0SCOPE = measure("evaluation/A0_detector_scope_adjudication.json")
DET = measure("research_map/class_separation.py")
REG = measure("runtime/bin/classsep_regression.py")
PROTO = measure("numerics/CONVERGENCE_PROTOCOL.md")
NGATES = measure("numerics/gates.py")
N0REV3 = measure("numerics/results/flat_wave_convergence_rev3.json")

DET_OLD = "c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920"
DET_STAGED = "e2d24b927ee81c45"  # proposed/class_separation.py (CF-16 staged candidate)
DRIFT = "artifacts/worker-098/classsep_prose_shadow/drift_recheck.json#ffabb753313f"
FNAUDIT = "artifacts/worker-049/classsep_fn_audit/results.json#9e1bf2043934"
RECOVERED = ("artifacts/worker-049/classsep_fn_audit/pinned/"
             "class_separation_c266_recovered.py#" + DET_OLD[:12])

DECISIONS = "runtime/state/controller_verification/astra-lifecycle-06-decisions.json"

# ---------------------------------------------------------------- gate records
GATES = [
    {
        "event_id": "astra-life06-gate-gf0", "event_type": "gate", "actor": "astra",
        "created_at": NOW, "gate_id": "G-F0", "scope": "F0", "verdict": "pass",
        "criteria": (
            "Declared F0 taxonomy exists at the canonical path; exactly the four frozen class ids; "
            "disjointness tests; >=2 independent reviewer verdicts at one measured hash. RE-ASSERTED "
            "MET at unchanged bytes: declared taxonomy " + F0[:12] + " (rev5) with companion "
            "supplement " + F0_SUP[:12] + " (REC-3: distinct artifacts, byte-identity not required); "
            "7 distinct independent accept reviewers at the measured hash per the pass-06 gate audit "
            "(worker-025, worker-038, worker-041, worker-052, worker-078, deepseek-flash-18, "
            "deepseek-flash-19); 6/6 disjointness pairs; bytes stable since 00:31:41. Residuals "
            "recorded, NOT gate criteria: CF-20 evidence binding was repaired downstream of F0 and "
            "does not touch F0 bytes; CF-21 axes.genericity_kind remains stale metadata against the "
            "explicit comeager conclusion. DIRECTIVE: canonical F0 bytes " + F0[:12] + " are frozen; "
            "any write to that path voids this verdict and requires fresh accepts at the new hash."
        ),
        "evidence_refs": [
            "research_map/formulation_taxonomy.yaml#" + F0[:12],
            "artifacts/formulation/formulation_taxonomy.yaml#" + F0_SUP[:12],
            "research_map/research_map.json#controller_gate_audit",
            DECISIONS,
        ],
    },
    {
        "event_id": "astra-life06-gate-gform", "event_type": "gate", "actor": "astra",
        "created_at": NOW, "gate_id": "G-FORM", "scope": "F1,F2a,F2b", "verdict": "pending",
        "criteria": (
            "F1/F2a/F2b exist with exact quantifiers/topology/regularity/genericity/I+/visibility/"
            "conclusion_type, no C0/C2 merge, and 2 independent accepts per class at one measured "
            "hash. The pass-05 evidence-binding repair LANDED (CF-20): schemas/taxonomy_cases.jsonl "
            + CASES[:12] + " is rebound and the schemas are rev13 " + F1[:12] + " / " + F2A[:12] +
            " / " + F2B[:12] + " under FROZEN rev29, all three mirror pairs aligned. Coverage at "
            "these hashes is 0 accepts per class: rev12 verdicts are void with their pins, and the "
            "FROZEN meta document moved again under the same revision number inside this window "
            "(3d9e3d77fd87 -> " + FROZEN[:12] + " at 00:57:27, CF-27) while the schema bytes stayed "
            "fixed. WITHHELD pending astra-life05-verify-gform-r3 (two independent non-author "
            "reviewers per class, measured sha256 cited, moving-target stop rule applies)."
        ),
        "evidence_refs": [
            "schemas/af_wcc_vacuum.yaml#" + F1[:12],
            "schemas/af_scc_c2_vacuum.yaml#" + F2A[:12],
            "schemas/af_scc_c0_vacuum.yaml#" + F2B[:12],
            "schemas/taxonomy_cases.jsonl#" + CASES[:12],
            "artifacts/formulation/evidence/taxonomy_consistency.json#" + CONSIST[:12],
            "artifacts/formulation/FROZEN.json#" + FROZEN[:12],
            DECISIONS,
            "research_map/research_map.json#controller_gate_audit",
        ],
    },
    {
        "event_id": "astra-life06-gate-glit", "event_type": "gate", "actor": "astra",
        "created_at": NOW, "gate_id": "G-LIT", "scope": "L0,L1", "verdict": "pending",
        "criteria": (
            "Ledger rows have resolvable locators and honest verification_status; >=3 independent "
            "re-fetch spot checks; unresolved marked unresolved; 2 independent accepts at one L0 "
            "hash. L0 measured " + L0[:12] + " (owner-announced rev3-final build product): 1 "
            "distinct accept (worker-075) against worker-025/worker-011/worker-093/deepseek-flash-18/"
            "worker-005 revise and worker-063 inconclusive at the same hash. L1 " + L1[:12] +
            " unchanged with 23 independent spot checks (>=3 met). WITHHELD pending "
            "astra-life05-verify-l0-final: two blind accepts at " + L0[:12] + "; any ledger write "
            "voids both."
        ),
        "evidence_refs": [
            "ledger/theorems.jsonl#" + L0[:12],
            "ledger/citation_audit.csv#" + L1[:12],
            "reviews/L0-review-075.json#" + L0[:12],
            DECISIONS,
            "research_map/research_map.json#controller_gate_audit",
        ],
    },
    {
        "event_id": "astra-life06-gate-gnum", "event_type": "gate", "actor": "astra",
        "created_at": NOW, "gate_id": "G-NUM", "scope": "N0", "verdict": "pending",
        "criteria": (
            "Flat-space convergence order measured AND independently replicated within tolerance; "
            "protocol reviewed; lock guard passes. Lock: LOCKED, solver absent, guard present, N1 "
            "hash absent - no numerics work was authorized or performed this pass. C8: protocol "
            + PROTO[:12] + " carries the standing accept 4.5 and two revise verdicts on the evidence "
            "basis; the operative verdict is routed to astra-life05-gnum-protocol-adjudication (no "
            "controller self-adjudication). N0 stop-rule deliverable numerics/results/"
            "flat_wave_convergence_rev3.json " + N0REV3[:12] + " exists with four-rung fixed-dt "
            "certification and replicated replication verdicts, but the N0 node verdict on disk is "
            "still revise 3.5: G-NUM passes only on an N0 accept at one hash (astra-life04-n0-verify, "
            "deadline 03:00). N1 remains locked regardless: release additionally requires G-FORM + "
            "G-AUDIT."
        ),
        "evidence_refs": [
            "numerics/CONVERGENCE_PROTOCOL.md#" + PROTO[:12],
            "numerics/gates.py#" + NGATES[:12],
            "numerics/results/flat_wave_convergence_rev3.json#" + N0REV3[:12],
            "research_map/research_map.json#numerics_lock",
            DECISIONS,
            "research_map/research_map.json#controller_gate_audit",
        ],
    },
    {
        "event_id": "astra-life06-gate-gaudit", "event_type": "gate", "actor": "astra",
        "created_at": NOW, "gate_id": "G-AUDIT", "scope": "A0,A1", "verdict": "pending",
        "criteria": (
            "A0 rubric exists without a universal scalar score and has an independent verdict; A1 "
            "has 2 independent accepts per formulation/literature target at a cited sha256. A0 "
            "rubric " + A0[:12] + " has 0 accepts (3 revise); the detector-scope adjudication "
            "landed at evaluation/A0_detector_scope_adjudication.json " + A0SCOPE[:12] + " but is "
            "unverified (CF-23) - astra-life04-verify-a0 must bind rubric + scope artifact. A1 "
            "coverage at measured hashes: F0 7 accepts at the F0 hash (criterion met), F1/F2a/F2b 0 "
            "at rev13, L0 1 (need >=2 each). Evidence audit: 17 hard CLASSSEP findings of the CF-16 "
            "metalinguistic-mention pattern plus the CF-26 instrument-drift hard finding; the "
            "27-fixture regression still scores PASS 17TP/10TN/0FP/0FN at the moved detector "
            + DET[:12] + ". The detector change is contested and is NOT adopted: "
            "astra-life06-classsep-detector-adjudication supersedes astra-life05-classsep-calibration; "
            "the frozen pin stays at " + DET_OLD[:12] + ". WITHHELD."
        ),
        "evidence_refs": [
            "evaluation_rubric.yaml#" + A0[:12],
            "evaluation/A0_detector_scope_adjudication.json#" + A0SCOPE[:12],
            DRIFT,
            FNAUDIT,
            "research_map/class_separation.py#" + DET[:12],
            "runtime/bin/classsep_regression.py#" + REG[:12],
            DECISIONS,
            "research_map/research_map.json#controller_gate_audit",
        ],
    },
    {
        "event_id": "astra-life06-gate-gform-refresh", "event_type": "gate", "actor": "astra",
        "created_at": NOW, "gate_id": "G-FORM", "scope": "F1,F2a,F2b", "verdict": "pending",
        "criteria": (
            "Coverage refresh measured in the pass-06 close gate audit (01:00:44) at the rev13 pins "
            + F1[:12] + " / " + F2A[:12] + " / " + F2B[:12] + ": F1 has 3 distinct accept reviewers "
            "(worker-045, worker-075, worker-085), F2a has 3 (worker-017, worker-072, worker-075), "
            "F2b has 0. The >=2 count is met numerically for F1/F2a but binding still requires "
            "astra-life05-verify-gform-r3 to adjudicate non-author independence at the measured "
            "hashes, and F2b must reach >=2 accepts at one stable hash; no gate moves on a reviewer "
            "count alone. The FROZEN meta move inside this window (CF-27) and the moving-target stop "
            "rule still apply. WITHHELD."
        ),
        "evidence_refs": [
            "schemas/af_wcc_vacuum.yaml#" + F1[:12],
            "schemas/af_scc_c2_vacuum.yaml#" + F2A[:12],
            "schemas/af_scc_c0_vacuum.yaml#" + F2B[:12],
            "artifacts/formulation/FROZEN.json#" + FROZEN[:12],
            "research_map/research_map.json#controller_gate_audit",
            DECISIONS,
        ],
    },
]

# ---------------------------------------------------------------- assignment
CARD = dict(event_type="assignment", actor="astra", created_at=NOW, supersedes=
            "astra-life05-classsep-calibration (same artifact path and owner; its acceptance "
            "bound only the staged candidate proposed/class_separation.py e2d24b92, which is now "
            "one of three candidates and the worse one on cue-carrying genuine assertions)")
ASSIGNMENTS = [
    {
        **CARD, "event_id": "astra-life06-classsep-detector-adjudication",
        "node_id": "A1", "assignee": "astra-lead-audit",
        "artifact": "reviews/CLASSSEP-calibration-adjudication.json", "gate": "G-AUDIT",
        "class_id": "GLOBAL",
        "evidence_refs": [
            "research_map/class_separation.py#" + DET[:12],
            RECOVERED,
            "proposed/class_separation.py#" + DET_STAGED[:12],
            DRIFT,
            FNAUDIT,
            "artifacts/worker-085/candidate_diff/report.json",
            "runtime/bin/classsep_regression.py#" + REG[:12],
            DECISIONS,
        ],
        "deadline": "2026-09-12T02:30:00+08:00", "budget_agent_hours": 1.5,
        "acceptance": (
            "SUPERSEDES astra-life05-classsep-calibration (same artifact path). One operative "
            "adjudication at cited hashes across the three detectors: applied canonical "
            + DET[:12] + ", recovered pre-change canonical " + DET_OLD[:12] + " (byte-verified "
            "copy), staged candidate " + DET_STAGED[:12] + ". Bind: worker-098 drift recheck "
            "(corpus PASS, 3/4 declared FP probes firing, growth 3, no over-suppression), worker-049 "
            "pre-registered adversarial FN audit (10/10 cue-carrying genuine assertions suppressed, "
            "9 HIGH; 13 declaration diffs), worker-035 control battery, and the 27-fixture "
            "regression at each candidate. Deliver a per-fixture TP/FP/FN census and EXACTLY ONE "
            "decision: (a) adopt " + DET[:12] + " with the exact bytes frozen and a controller "
            "pin-refresh request; (b) roll back to " + DET_OLD[:12] + " reproduced from the "
            "recovered copy; or (c) record assertion-vs-mention as not lexically separable at this "
            "window and state the residual hard count honestly. Include the claims-retirement policy "
            "for historical metalinguistic claims and require one independent review at the chosen "
            "hash. DETECTOR WRITES FREEZE until the decision lands; no schema, ledger or claim "
            "edits; no gate self-pass."
        ),
        "expected_information_gain": (
            "Settles whether G-AUDIT's CLASSSEP hard count is a detector artifact or a real class "
            "leak with measured error rates on three candidates, and closes the CF-26 instrument "
            "drift with a hash-bound adoption/rollback decision."),
        "falsifier": (
            "An adopted detector that suppresses a genuine 'C0 or C2' assertion on the labeled "
            "corpus; a decision without cited hashes; a census not reproducible from the artifact; "
            "any write to research_map/class_separation.py while the round is open."),
        "stop_rule": (
            "Stop if the live detector moves again or the recovered c266dbec copy fails hash "
            "verification; record the contest as unresolved rather than shipping a patch. No gate "
            "verdict, no claim promotion, no N1 work."),
    },
]

# ------------------------------------------------------------------- notices
NOTICES = [
    {
        "event_id": "astra-life06-notice-detector-drift", "event_type": "status", "actor": "astra",
        "created_at": NOW, "node_id": "A1", "status": "active", "hours": 0.1,
        "summary": (
            "Controller ruling (REC-22, CF-26): research_map/class_separation.py changed "
            + DET_OLD[:12] + " -> " + DET[:12] + " at 00:52:00 with no recorded authorizing event. "
            "The change is NOT adopted and the frozen pin is NOT refreshed; c266dbec-bound verdicts "
            "are void at the new bytes. Detector writes freeze. "
            "astra-life06-classsep-detector-adjudication (audit lead, 02:30) supersedes "
            "astra-life05-classsep-calibration and must decide adopt / rollback / "
            "not-lexically-separable at cited hashes with an independent review."
        ),
        "evidence_refs": ["research_map/class_separation.py#" + DET[:12], RECOVERED, DRIFT,
                          FNAUDIT, DECISIONS],
        "next_falsifier": "Any detector write while the adjudication round is open, or a decision "
                          "without a cited hash.",
    },
    {
        "event_id": "astra-life06-notice-gform-rev13", "event_type": "status", "actor": "astra",
        "created_at": NOW, "node_id": "F1", "status": "active", "hours": 0.1,
        "summary": (
            "Controller ruling (REC-23, CF-20/CF-27): the evidence-binding repair landed - case "
            "corpus " + CASES[:12] + " rebound, schemas rev13 " + F1[:12] + " / " + F2A[:12] + " / "
            + F2B[:12] + ", all mirror pairs aligned - so the rev12 pins are void and the rev12 "
            "verdicts are advisory only. FROZEN rev29 moved under the same revision number at "
            "00:57:27 (" + FROZEN[:12] + ") while the schema bytes stayed fixed: reviewers must pin "
            "the FROZEN bytes too. G-FORM stays pending on astra-life05-verify-gform-r3 (two "
            "independent non-author reviewers per class at the rev29 pins); no gate moves on a "
            "landed repair alone."
        ),
        "evidence_refs": ["schemas/af_wcc_vacuum.yaml#" + F1[:12],
                          "schemas/af_scc_c2_vacuum.yaml#" + F2A[:12],
                          "schemas/af_scc_c0_vacuum.yaml#" + F2B[:12],
                          "schemas/taxonomy_cases.jsonl#" + CASES[:12],
                          "artifacts/formulation/FROZEN.json#" + FROZEN[:12], DECISIONS],
        "next_falsifier": "A per-class gate verdict bound to a superseded or mid-round-moving hash.",
    },
    {
        "event_id": "astra-life06-notice-lock-comms", "event_type": "status", "actor": "astra",
        "created_at": NOW, "node_id": "N0", "status": "active", "hours": 0.1,
        "summary": (
            "Controller ruling (REC-24/25/26): numerics_lock remains LOCKED with the solver absent "
            "and the N1 hash absent; no N1 allocation and no downstream numerics work this pass. "
            "Controller inbox integrity (CF-28): a malformed, future-dated line in "
            "comms/inbox/astra.jsonl duplicating the A0 detector-scope card was quarantined and "
            "recorded, not actioned; a genuine Human-PI directive must be re-sent well-formed "
            "through the protocol. Decisions record: " + DECISIONS + " (REC-22..REC-28)."
        ),
        "evidence_refs": ["research_map/research_map.json#numerics_lock",
                          "runtime/state/comms_quarantine/astra-inbox-line2-20260912T0100.jsonl",
                          "comms/PROTOCOL.md", DECISIONS],
        "next_falsifier": "Any solver/N1 artifact, or a second unattributable write to a pinned "
                          "instrument.",
    },
]


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
    for a in ASSIGNMENTS:
        if _already_sent(a["assignee"], a["event_id"]):
            print(f"INBOX    already-sent <- {a['event_id']}")
            continue
        msg = {k: v for k, v in a.items()}
        msg["to"] = a["assignee"]
        msg["event_type"] = "assignment"
        path = comms.send(a["assignee"], msg)
        print(f"INBOX    {path.relative_to(ROOT)} <- {a['event_id']}")
    print("pins:", json.dumps({"F0": F0[:12], "F1": F1[:12], "F2a": F2A[:12], "F2b": F2B[:12],
                               "FROZEN": FROZEN[:12], "L0": L0[:12], "L1": L1[:12],
                               "A0": A0[:12], "A0scope": A0SCOPE[:12], "proto": PROTO[:12],
                               "ngates": NGATES[:12], "N0rev3": N0REV3[:12],
                               "detector": DET[:12], "regression": REG[:12]}))


if __name__ == "__main__":
    main()
