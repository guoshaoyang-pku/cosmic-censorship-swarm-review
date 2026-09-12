#!/usr/bin/env python3
"""Append worker-010's verification evidence to comms/outbox/worker-010.jsonl.

Bounded task W010B-C0-REV12-INDEP-VERIFY: independent third-implementation verification
of the AF-SCC-C0-VAC-GEN rev12 class-conformance re-audit.  Appends four events
(2 artifacts, 1 claim, 1 status); never rewrites existing lines.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUTBOX = ROOT / "comms/outbox/worker-010.jsonl"
CST = timezone(timedelta(hours=8))


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ev(path: str) -> str:
    h = sha256(ROOT / path)
    return f"{path}#{h[:12]}"


def main() -> int:
    now = datetime.now(CST).isoformat(timespec="seconds")
    stamp = datetime.now(CST).strftime("%Y%m%dT%H%M%S")
    run_id = "run-2026-09-11T23:15+08:00"

    report_path = "artifacts/worker-010/c0_conformance_rev12_verify/verify_c0_rev12_independent.json"
    script_path = "artifacts/worker-010/c0_conformance_rev12_verify/verify_c0_rev12_independent.py"
    report = json.loads((ROOT / report_path).read_text(encoding="utf-8"))
    summ = report["summary"]

    refs = [
        ev("artifacts/worker-010/c0_class_conformance/c0_class_conformance_audit.55d0a1ea9bda.json"),
        ev("schemas/af_scc_c0_vacuum.yaml"),
        ev("ledger/theorems.jsonl"),
        ev("research_map/formulation_taxonomy.yaml"),
        ev(report_path),
        ev(script_path),
        ev("artifacts/worker-010/c0_class_conformance/c0_class_conformance_audit.py"),
        ev("artifacts/worker-010/c0_class_conformance/c0_reaudit_rev12.py"),
        ev("artifacts/formulation/FROZEN.json"),
    ]

    summary_line = (
        f"Independent third-implementation verification of the AF-SCC-C0-VAC-GEN rev12 conformance "
        f"re-audit ({ev('artifacts/worker-010/c0_class_conformance/c0_class_conformance_audit.55d0a1ea9bda.json')}): "
        f"11 bound entries, 0 discharging, class state open_problem; discharge agreement "
        f"{summ['discharge_agreement']}, D2 agreement {summ['d2_agreement']}, all {len(report['checks'])} checks pass, "
        f"6/6 adversarial controls pass. Correction (V010-F1, medium): the audit's n_accepted_status=0 is a "
        f"ledger field-rename artifact (0/62 entries carry `status` at ledger a1674f094979; equivalent field "
        f"content_status, 9/11 bindings verified), but D3 still fails for all 11 under the corrected mapping "
        f"(each binding has >=1 unresolved item and/or preprint evidence), so the headline is robust. "
        f"D1 classifier sensitivity on T-528 (V010-F4, low, no discharge impact). Mechanical reproducibility "
        f"check only; same fleet slot as the target alias; not a reviewer verdict and no gate movement."
    )

    claim_statement = (
        "At the live pins schemas/af_scc_c0_vacuum.yaml#55d0a1ea9bda, ledger/theorems.jsonl#a1674f094979 and "
        "research_map/formulation_taxonomy.yaml#0abb9ed8a961, an independently written third implementation "
        "(no import of the audited driver) reproduces the AF-SCC-C0-VAC-GEN rev12 conformance reading: 11 ledger "
        "entries are bound to the class, 0 discharge D1_data_class AND D2_conclusion AND D3_evidence, and the "
        "class conclusion state is open_problem. Discharge verdicts agree 11/11 and D2 verdicts agree 11/11 with "
        "the target audit; D2 holds only for T-302. The target's n_accepted_status=0 is caused by the rev3 ledger "
        "dropping the `status` key (0/62 entries; equivalent content_status=verified for 9/11 bindings), not by an "
        "evidence downgrade; under the corrected mapping D3 still fails for all 11 bindings because every binding "
        "carries >=1 unresolved item and/or a preprint evidence level, so the 0-discharging headline is robust. "
        "This is a mechanical reproducibility measurement, not an independent reviewer verdict."
    )

    falsifier = (
        "Any of: a live pin no longer matching the audit at re-measurement; an independent binding selection "
        "differing from the 11 ids; an independent discharge verdict of true for any bound entry; an independent "
        "D2 verdict differing on any binding; a synthetic discharging control the independent predicate set "
        "cannot discharge; or a bound entry that passes D3 under the corrected content_status mapping."
    )

    events = [
        {
            "event_id": f"w010-{stamp}-c0rev12-verify-artifact-script",
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-010",
            "run_id": run_id,
            "node_id": "L1",
            "gate": "G-LIT",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "class_ids": ["AF-SCC-C0-VAC-GEN"],
            "artifact_type": "python",
            "path": script_path,
            "sha256": sha256(ROOT / script_path),
            "bytes": (ROOT / script_path).stat().st_size,
            "validation_status": "unverified",
            "claims_completion": False,
            "summary": (
                "Independent third implementation of the AF-SCC-C0-VAC-GEN conformance predicates "
                "(D1/D2/D3), written from the frozen class contract; does not import "
                "c0_class_conformance_audit.py. Emits the verification report and 6 adversarial controls."
            ),
            "evidence_refs": refs,
            "falsifier": (
                "A re-run whose stored report differs from a fresh run, or a check flipping to FAIL, or the "
                "adversarial controls failing to include a dischargeable positive."
            ),
        },
        {
            "event_id": f"w010-{stamp}-c0rev12-verify-artifact-report",
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-010",
            "run_id": run_id,
            "node_id": "L1",
            "gate": "G-LIT",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "class_ids": ["AF-SCC-C0-VAC-GEN"],
            "artifact_type": "verification_report",
            "path": report_path,
            "sha256": sha256(ROOT / report_path),
            "bytes": (ROOT / report_path).stat().st_size,
            "validation_status": "unverified",
            "claims_completion": False,
            "summary": summary_line,
            "findings": [f["id"] + ":" + f["severity"] for f in report["findings"]],
            "evidence_refs": refs,
            "falsifier": falsifier,
        },
        {
            "event_id": f"w010-{stamp}-c0rev12-verify-claim",
            "event_type": "claim",
            "created_at": now,
            "actor": "worker-010",
            "run_id": run_id,
            "node_id": "L1",
            "gate": "G-LIT",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "class_ids": ["AF-SCC-C0-VAC-GEN"],
            "conclusion_type": "open_problem",
            "statement": claim_statement,
            "assumptions": [
                "class_ids and status vocabulary are inherited from the L0/L1 ledger; this verifier does not re-adjudicate them (A1's job)",
                "D1/D2/D3 are mechanical readings of the ledger fields; the independent predicate set is documented in the report",
                "the corrected D3 mapping content_status verified->accepted is this verifier's reading of the rev3 ledger vocabulary, recorded as a finding for L0/A1 rather than applied to the ledger",
                "the verifier shares fleet slot 010 with the target alias; this is not an independence claim in the reviewer sense",
            ],
            "falsifier": falsifier,
            "evidence_refs": refs,
            "artifact_refs": [ev(report_path), ev(script_path)],
            "expected_information_gain": (
                "Supplies the missing independent implementation for the rev12 C0 conformance report, corrects "
                "the D3 mechanism claim while confirming its conclusion, and gives A1 a binding-by-binding "
                "agreement table instead of a same-driver re-run."
            ),
            "validation_status": "unverified",
        },
        {
            "event_id": f"w010-{stamp}-c0rev12-verify-status",
            "event_type": "status",
            "created_at": now,
            "actor": "worker-010",
            "run_id": run_id,
            "node_id": "L1",
            "gate": "G-LIT",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "class_ids": ["AF-SCC-C0-VAC-GEN"],
            "status": "active",
            "hours": 0.4,
            "summary": summary_line,
            "evidence_refs": [ev(report_path), ev(script_path), refs[1], refs[2], refs[0]],
            "next_falsifier": falsifier,
        },
    ]

    # validate JSON round-trip before appending
    lines = [json.dumps(e, ensure_ascii=False) for e in events]
    for line in lines:
        json.loads(line)

    with OUTBOX.open("a", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")

    print(f"appended {len(lines)} events to {OUTBOX.relative_to(ROOT)}")
    for e in events:
        print(" ", e["event_id"], "|", e["event_type"], "|", e.get("sha256", "")[:12])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
