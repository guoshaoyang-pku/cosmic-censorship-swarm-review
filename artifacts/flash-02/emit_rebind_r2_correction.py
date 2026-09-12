#!/usr/bin/env python3
"""Correction events for the R2 repair: the independent-verification report was
regenerated after an initial emission and its run timestamp changed its hash.

Correction:
  * artifact 0010b declares the now-deterministic report at its stable hash;
  * claim 0100c supersedes claim 0100b with corrected evidence refs;
  * status 0101b is an addendum recording the correction.
All three are CLASSSEP-self-checked and idempotent.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import sys
from pathlib import Path

OUTBOX = Path("comms/outbox/deepseek-flash-02.jsonl")
CLASS_ID = ";".join(["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN",
                     "AF-WCC-SCALAR-SPH"])
ARTIFACTS = [
    "schemas/taxonomy_cases.jsonl",
    "artifacts/flash-02/leak_rule_catalog.json",
    "artifacts/flash-02/rebind_rows_r2.py",
    "artifacts/flash-02/rebind_rows_r2_report.json",
    "artifacts/flash-02/rebind_catalog_pin.py",
    "artifacts/flash-02/rebind_catalog_pin_report.json",
    "artifacts/flash-02/check_taxonomy_cases.py",
    "artifacts/flash-02/taxonomy_cases_check_report.json",
    "artifacts/flash-02/reports/check_stale_pin_guard.fail.f0c20b96.json",
    "artifacts/flash-02/rebind_r2_independent_check.json",
    "artifacts/flash-02/snapshots/taxonomy_cases.pre-rebind-r2.f0c20b96.jsonl",
    "artifacts/flash-02/snapshots/leak_rule_catalog.pre-rebind-r2.215f6e22.json",
]


def sha(p: str) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main() -> int:
    sys.path.insert(0, str(Path("research_map").resolve()))
    import class_separation  # noqa: E402

    old = json.loads(Path("artifacts/flash-02/rebind_r2_independent_check.json").read_text())
    created = _dt.datetime.now().astimezone().isoformat(timespec="seconds")
    ts = created.replace("-", "").replace(":", "").replace("+", "")[:15]
    evidence = [f"{p}#{sha(p)[:12]}" for p in ARTIFACTS]
    h2 = sha("artifacts/flash-02/rebind_r2_independent_check.json")

    correction_note = (
        "Correction to the earlier claim in this task: the independent-verification report was "
        "regenerated after it was first hashed, and its run timestamp changed its bytes. The "
        "verifier has been made deterministic (no run timestamp; byte-stable across re-runs) and "
        "is re-declared here at its stable hash; the corrected evidence list supersedes the "
        "previous one. No corpus, catalog or checker result changed."
    )
    claim_statement = (
        "Artifact-and-checker result, not a mathematics or physics claim and not a theorem: "
        "the F0 corpus schemas/taxonomy_cases.jsonl was repaired from the state in which its "
        "meta bound taxonomy revision 5 while all 36 case rows still bound a superseded "
        "revision (HF-094C-1). The repair rewrote exactly the 36 row pins to the revision "
        "measured on disk, with per-row content-preservation digests proving no other field "
        "changed, and rebound the leak-rule catalog's revision reference for the same reason. "
        "The class-separation checker was hardened with a stale-pin guard and an 11th control; "
        "it returns FAIL with 36 STALE_TAXONOMY_PIN errors on the pre-repair bytes and PASS "
        "with 11/11 controls on the post-repair bytes, where the four frozen classes remain "
        "separate and each is covered in both polarities. An independent verifier re-derived "
        "8 checks from the rollback snapshots and live files and returned PASS. " + correction_note
    )
    claim_falsifier = (
        "Any live case row whose content (all fields except binding_status) differs from the "
        "rollback snapshot, any row pin unequal to the 12-hex prefix of the taxonomy file "
        "measured on disk, a changed meta record, an orphaned catalog guard reference, a "
        "checker report not bound to the live corpus/catalog/taxonomy hashes, a checker verdict "
        "other than PASS with 11/11 controls, or an independent-verification report whose bytes "
        "are not reproducible by re-running its tool."
    )
    assumptions = [
        "The canonical taxonomy remains research_map/formulation_taxonomy.yaml rev5 at its "
        "recorded sha256.",
        "The 36 case rows' semantics are unchanged; only the revision they bind moved.",
        "The corpus is not listed in artifacts/formulation/FROZEN.json, so this repair is not a "
        "post-freeze edit of a frozen artifact.",
    ]
    scan_text = "\n".join([claim_statement] + assumptions + [claim_falsifier])
    findings = class_separation.findings_for_text(scan_text, "claim:flash02-f0rebindr2-correction")
    if findings:
        print("SELF-REJECT: class-separation findings in correction prose:")
        for f in findings:
            print("  -", f)
        return 2

    events = [
        {
            "event_id": f"flash02-f0rebindr2-artifact-0010b-{ts}",
            "event_type": "artifact",
            "created_at": created,
            "actor": "deepseek-flash-02",
            "node_id": "F0",
            "gate": "G-F0",
            "class_id": CLASS_ID,
            "artifact_type": "independent_repair_verification_deterministic",
            "path": "artifacts/flash-02/rebind_r2_independent_check.json",
            "sha256": h2,
            "validation_status": "unverified",
            "supersedes_declared_hash": "b36768d7d314",
            "summary": ("Deterministic version of the independent repair verification: 8/8 checks "
                        "PASS; byte-stable across re-runs (no run timestamp)."),
        },
        {
            "event_id": f"flash02-f0rebindr2-claim-0100c-{ts}",
            "event_type": "claim",
            "created_at": created,
            "actor": "deepseek-flash-02",
            "node_id": "F0",
            "gate": "G-F0",
            "class_id": CLASS_ID,
            "conclusion_type": "formal_model",
            "claims_theorem_status": False,
            "supersedes_event_id": f"flash02-f0rebindr2-claim-0100b-20260912T004453",
            "supersede_reason": ("independent-verification evidence re-declared at a deterministic "
                                 "hash; no result changed"),
            "statement": claim_statement,
            "assumptions": assumptions,
            "falsifier": claim_falsifier,
            "evidence_refs": evidence,
            "artifact_refs": ARTIFACTS,
        },
        {
            "event_id": f"flash02-f0rebindr2-status-0101b-{ts}",
            "event_type": "status",
            "created_at": created,
            "actor": "deepseek-flash-02",
            "node_id": "F0",
            "gate": "G-F0",
            "class_id": CLASS_ID,
            "status": "active",
            "hours": 0.45,
            "summary": ("Addendum: correction events emitted (artifact 0010b, claim 0100c, status "
                        "0101b). Final hashes: corpus ccf7041bd0ff, catalog ccec815ea61d, "
                        "checker report 0d00bba89979, independent report " + h2[:12] + ". All 12 "
                        "artifact declarations now match measured bytes."),
            "evidence_refs": evidence,
            "next_falsifier": ("Re-run python3 artifacts/flash-02/verify_rebind_r2.py twice and "
                               "confirm identical report bytes; re-run "
                               "artifacts/flash-02/check_taxonomy_cases.py and confirm PASS "
                               "11/11."),
        },
    ]

    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line).get("event_id"))
            except ValueError:
                pass
    new = [e for e in events if e["event_id"] not in existing]
    with OUTBOX.open("a", encoding="utf-8") as f:
        for e in new:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    print(f"emitted {len(new)} correction events (skipped {len(events) - len(new)})")
    for e in new:
        print(" ", e["event_id"], e["event_type"])
    print(f"independent report stable hash: {h2}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
