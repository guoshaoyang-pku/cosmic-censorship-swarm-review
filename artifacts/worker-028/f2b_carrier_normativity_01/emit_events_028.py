#!/usr/bin/env python3
"""Emit W028-F2B-CARRIER-NORMATIVITY-01 events to comms/outbox/worker-028.jsonl.

Validates every event with research_map.schemas.validate_event before appending.
Append-only; does not ingest (ingest is the controller's action).
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")
OUT = ROOT / "comms/outbox/worker-028.jsonl"

ART = "artifacts/worker-028/f2b_carrier_normativity_01/carrier_normativity_028.json"
RUN = "artifacts/worker-028/f2b_carrier_normativity_01/run_carrier_normativity_028.py"
REP = "artifacts/worker-028/f2b_carrier_normativity_01/REPORT.md"
CKP = "artifacts/worker-028/f2b_carrier_normativity_01/checkpoint_028.json"
H_ART = "a5e815c31b47db1727321fc8b6bac75e47e5f4d11bae12baae3affa289f3cc13"
H_RUN = "6f57624b3d4220a851970ad92c916dae5f0442207f55d307f84ab498a0dca22d"
H_REP = "0b9ce8bf5fe1d28f2b450058aec4bc03a3b3c6d5abb704ece271994efef19e51"
P_F2B = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"
P_F2A = "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe"
P_FZ = "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"
P_SPEC = "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e"
P_GATE = "000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff"
P_F0 = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
P_EVID = "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b"

EVIDENCE = [
    f"{ART}#{H_ART[:12]}", f"{RUN}#{H_RUN[:12]}", f"{REP}#{H_REP[:12]}", f"{CKP}#74d1a3f8883a",
    "artifacts/worker-028/f2b_carrier_normativity_01/pins/SHA256SUMS",
    f"schemas/af_scc_c0_vacuum.yaml#{P_F2B[:12]}",
    f"schemas/af_scc_c2_vacuum.yaml#{P_F2A[:12]}",
    f"artifacts/formulation/FROZEN.json#{P_FZ[:12]}",
    f"artifacts/formulation/rule_spec.json#{P_SPEC[:12]}",
    f"artifacts/formulation/tools/check_class_schema.py#{P_GATE[:12]}",
    f"research_map/formulation_taxonomy.yaml#{P_F0[:12]}",
    f"artifacts/formulation/evidence/taxonomy_consistency.json#{P_EVID[:12]}",
    "reviews/F2b-containment-normativity-worker-066.json",
    "reviews/F2b-rev13-containment-worker-017.json",
]

events = [
    {
        "event_id": "w028-f2b-carrier-20260912T011330-art",
        "event_type": "artifact", "created_at": NOW, "actor": "worker-028",
        "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"], "gate": "G-FORM",
        "artifact_type": "measurement", "path": ART, "sha256": H_ART,
        "validation_status": "unverified",
        "summary": "W028-F2B-CARRIER-NORMATIVITY-01 measurement artifact: 27/27 checks, 6/6 controls; H1/H2 are real text defects but neither rule-spec-normative nor contract-normative at the pin.",
        "evidence_refs": EVIDENCE,
    },
    {
        "event_id": "w028-f2b-carrier-20260912T011330-run",
        "event_type": "artifact", "created_at": NOW, "actor": "worker-028",
        "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"], "gate": "G-FORM",
        "artifact_type": "runner", "path": RUN, "sha256": H_RUN,
        "validation_status": "unverified",
        "summary": "Independent runner: order-relative carrier detector, canonical/pinned gate runs, four gate-sensitivity mutants, two-edit repair impact diff.",
        "evidence_refs": EVIDENCE,
    },
    {
        "event_id": "w028-f2b-carrier-20260912T011330-rep",
        "event_type": "artifact", "created_at": NOW, "actor": "worker-028",
        "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"], "gate": "G-FORM",
        "artifact_type": "report", "path": REP, "sha256": H_REP,
        "validation_status": "unverified",
        "summary": "REPORT.md for W028-F2B-CARRIER-NORMATIVITY-01 with pins, operational definitions, rule trace, gate-sensitivity matrix and consequences for the G-FORM r3 review.",
        "evidence_refs": EVIDENCE,
    },
    {
        "event_id": "w028-f2b-carrier-20260912T011330-claim",
        "event_type": "claim", "created_at": NOW, "actor": "worker-028",
        "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"], "gate": "G-FORM",
        "statement": "At F2b sha256 b2ab6acb2bbe / FROZEN rev29 815e0807, the two contested carrier clauses (H1 implication_ledger.forbidden_transfers[0].reason :246; H2 regularity.must_not_conflate[0] :152) are real live text defects but are NOT normative under the binding rule spec R01-R16 or the canonical class-schema gate: R06 binds only the existence of a non-empty must_not_conflate list and R16 only the ledger's recorded chain/entailments and forbidden marking, neither binds entry/reason truth; the canonical gate returns pass on pristine and is verdict-invariant under repaired, nonsense, strengthened-false and empty carrier content, while it does reject a composite token moved to an assertive path (R13), a forbidden required C0=>C2 transfer (R16), a converse C2=>C0 entailment (R16) and an emptied must_not_conflate (R06); and a two-edit wording repair changes exactly the two carrier paths and no other rule-bound contract field. H1 states an inverted size premise that, read literally, licenses the very transfer its row forbids; H2 falsely denies a containment the same document asserts at :239 and :241-244. Therefore W066's content-normativity claim is rejected at these bytes and the correct disposition is an editorial revise (two minimal wording repairs), not a class-binding failure; the licensed C0=>C2 entailment row is untouched.",
        "conclusion_type": "formal_model",
        "assumptions": [
            "operational definition: rule-spec-normative = gate-verdict-changing or named by a rule require/fail on content; contract-normative = changes a rule-bound contract field other than the clause",
            "measurement binds the nine pinned sha256 bytes, not paths or revisions",
            "the canonical gate at 000e09e46b2f and rule_spec R01-R16 as written are the binding structural rules for G-FORM",
            "the two-edit repair used is this task's own minimal wording repair, not worker-066's candidate",
            "this is worker evidence; it sets no gate verdict, node status or validation_status=passed",
        ],
        "falsifier": "Falsified if any of the nine pinned hashes moves; if the canonical gate at the pin fails or distinguishes repaired/nonsense/empty carrier text from pristine; if repairing the two clauses changes any parsed contract path outside the two carriers; if R06/R16 require/fail text at the pin names entry/reason truth; if a sibling carries either defect kind; or if any check K0-K7 or control C1-C6 departs from its recorded expectation. Any hash move voids the claim and requires a fresh run.",
        "evidence_refs": EVIDENCE,
        "artifact_refs": [f"{ART}#{H_ART[:12]}", f"{RUN}#{H_RUN[:12]}", f"{REP}#{H_REP[:12]}", f"{CKP}#74d1a3f8883a"],
        "non_claims": [
            "no gate verdict; G-FORM stays pending for astra-lead-audit r3",
            "no node status; F2b remains active",
            "editorial does not mean optional: two false sentences in a frozen schema still require revision",
            "no mathematics, F0 taxonomy or L1 ledger adjudication",
            "not one of the independent verdicts required by astra-life05-verify-gform-r3",
        ],
    },
    {
        "event_id": "w028-f2b-carrier-20260912T011330-review",
        "event_type": "review", "created_at": NOW, "actor": "worker-028", "reviewer": "worker-028",
        "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"], "gate": "G-FORM",
        "target_id": f"schemas/af_scc_c0_vacuum.yaml#{P_F2B}",
        "artifact": "schemas/af_scc_c0_vacuum.yaml",
        "artifact_sha256": P_F2B,
        "reviewed_sha256": P_F2B,
        "frozen_sha256": P_FZ,
        "verdict": "revise", "score": 3.5,
        "counts_as_full_schema_verdict": False,
        "counts_as_independent": True,
        "verdict_scope": "normativity adjudication of the two carried carrier clauses at b2ab6acb and their gate/rule-spec status; not a full-surface schema review, not a gate verdict, not a node status",
        "hard_failures": [
            {"id": "W028-F2B-H1", "severity": "editorial", "blocking_for_clean_accept": True,
             "carrier": "implication_ledger.forbidden_transfers[0].reason", "line": 246,
             "finding": "size premise inverted against the document's own chain at :239; read literally it would license the transfer the row forbids. Not an R06/R16 fail and not gate-distinguishable."},
            {"id": "W028-F2B-H2", "severity": "editorial", "blocking_for_clean_accept": True,
             "carrier": "regularity.must_not_conflate[0]", "line": 152,
             "finding": "false containment denial contradicting the same document at :239 and :241-244 and the corrected C2 sibling at e9a27996. Not an R06/R16 fail and not gate-distinguishable."},
        ],
        "findings": [
            "Both clauses are byte-identical to the rev12 55d0a1ea bytes (carried forward), so rev12 accept-class verdicts predate the detection, not the defect.",
            "Canonical gate at the pin: PASS, zero failures, on pristine; PASS on repaired/nonsense/strengthened-false/empty carriers; FAIL R13/R16/R16/R06 on four positive mutants — the gate binds structure, not carrier truth.",
            "R06 binds must_not_conflate existence only; R16 binds the recorded chain, one-way entailments and forbidden marking only; neither require/fail names entry or reason truth.",
            "Two-edit repair of H1+H2 parses, passes the gate, is detector-clean and changes exactly the two carrier paths; no rule-bound contract field moves, so a wording repair needs no class-semantics re-derivation.",
            "Consequence: the pending G-FORM r3 review may treat these as editorial blockers to a clean accept (repair then re-freeze, or explicitly record them and fold the repair as follow-up); they are not class-binding failures.",
        ],
        "evidence_refs": EVIDENCE,
        "falsifier": "Falsified if the target or FROZEN bytes move; if the canonical gate at the pin distinguishes the repaired from the defective carrier text; if R06/R16 require/fail names entry/reason truth at the pin; if the two-edit repair changes any contract path outside the two carriers; or if any check/control in the bound measurement departs from its expectation.",
        "authority": "worker reviewer verdict only; no gate verdict and no node state moved",
    },
    {
        "event_id": "w028-f2b-carrier-20260912T011330-status",
        "event_type": "status", "created_at": NOW, "actor": "worker-028",
        "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"], "gate": "G-FORM",
        "status": "active", "hours": 0.3,
        "summary": "W028-F2B-CARRIER-NORMATIVITY-01 complete at worker level: 27/27 checks, 6/6 controls at F2b b2ab6acb2bbe / FROZEN rev29 815e0807. H1+H2 are real carried text defects; neither triggers any R01-R16 require/fail, neither is gate-distinguishable, and a two-edit repair changes only the two carrier paths. W066 content-normativity claim rejected; disposition = editorial revise (two minimal wording repairs), not a class-binding or gate failure; the licensed C0=>C2 entailment row is untouched. Worker-local checkpoint recorded. No gate verdict, node status or validation_status=passed claimed.",
        "next_falsifier": "Re-run run_carrier_normativity_028.py at the live pins after any F2b/rule-spec/checker move: expect 27/27 + 6/6; a pin move, a gate failure on repaired text, a gate that distinguishes carrier content, a repair path diff beyond the two carriers, or an R06/R16 content binding voids the claim and requires a fresh adjudication.",
        "evidence_refs": EVIDENCE,
    },
]

for ev in events:
    validate_event(ev)

with OUT.open("a", encoding="utf-8") as f:
    for ev in events:
        f.write(json.dumps(ev, ensure_ascii=False) + "\n")
print(f"appended {len(events)} validated events -> {OUT}")
