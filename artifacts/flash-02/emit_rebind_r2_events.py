#!/usr/bin/env python3
"""Emit the R2 F0 binding-chain repair events to comms/outbox/deepseek-flash-02.jsonl.

One class-bound task: repair HF-094C-1 (36/36 case rows pinned the superseded
taxonomy revision) plus the companion stale catalog pin, harden the checker with
a stale-pin guard and control C11, and verify independently.

Rules honoured here:
  * every artifact event carries path + sha256 + validation_status (worker cannot
    set passed/done);
  * every evidence ref is path#sha256-prefix;
  * the claim text is run through research_map/class_separation.findings_for_text
    before writing, so this event cannot add a new CLASSSEP hard failure (CF-16);
  * re-running skips event_ids that already exist in the outbox (idempotent).
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import sys
from pathlib import Path

OUTBOX = Path("comms/outbox/deepseek-flash-02.jsonl")
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
CLASS_ID = ";".join(CLASS_IDS)

ARTIFACTS = [
    ("schemas/taxonomy_cases.jsonl", "f0_class_separation_corpus_repaired",
     "Repaired class-leakage corpus: all 36 case rows rebound from the superseded "
     "taxonomy pin to the canonical rev5 pin 0abb9ed8a961."),
    ("artifacts/flash-02/leak_rule_catalog.json", "leak_rule_catalog_repaired_pin",
     "Leak-rule catalog taxonomy_ref rebound rev3 565a6e50 -> rev5 0abb9ed8a961; "
     "all 18 rule bodies byte-identical, no orphaned guard refs."),
    ("artifacts/flash-02/rebind_rows_r2.py", "repair_tool_rows",
     "Guarded minimal row-pin rebind tool (6 guards, idempotent)."),
    ("artifacts/flash-02/rebind_rows_r2_report.json", "repair_report_rows",
     "Apply-mode report: 36/36 replacements, 0 variables other than binding_status, "
     "content-preservation digests per row."),
    ("artifacts/flash-02/rebind_catalog_pin.py", "repair_tool_catalog",
     "Guarded minimal catalog-pin rebind tool (6 guards, idempotent)."),
    ("artifacts/flash-02/rebind_catalog_pin_report.json", "repair_report_catalog",
     "Applied-state report: pin rev3 565a6e50 -> rev5 0abb9ed8a961, catalog body unchanged."),
    ("artifacts/flash-02/check_taxonomy_cases.py", "class_separation_checker_hardened",
     "Checker hardened with a stale-pin guard and control C11_stale_taxonomy_pin "
     "(11 controls total); now fails closed on any meta/row pin divergence."),
    ("artifacts/flash-02/taxonomy_cases_check_report.json", "class_separation_check_report",
     "PASS at the post-repair hashes: 16 positive / 20 negative cases, 4 classes covered "
     "in both polarities, 11/11 controls detected."),
    ("artifacts/flash-02/reports/check_stale_pin_guard.fail.f0c20b96.json",
     "stale_pin_guard_positive_control",
     "Pre-repair FAIL proof: the hardened checker returned FAIL with 36 STALE_TAXONOMY_PIN "
     "errors on corpus f0c20b96, i.e. the guard detects the real defect."),
    ("artifacts/flash-02/rebind_r2_independent_check.json", "independent_repair_verification",
     "Independent re-derivation (8 checks) from the snapshots and live files: content "
     "identity, pin equality, catalog validity, checker binding."),
    ("artifacts/flash-02/snapshots/taxonomy_cases.pre-rebind-r2.f0c20b96.jsonl",
     "rollback_snapshot_corpus",
     "Byte-exact rollback snapshot of the corpus before this repair."),
    ("artifacts/flash-02/snapshots/leak_rule_catalog.pre-rebind-r2.215f6e22.json",
     "rollback_snapshot_catalog",
     "Byte-exact rollback snapshot of the leak-rule catalog before this repair."),
]


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def now_iso() -> str:
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


def main() -> int:
    # Self-check the prose with the map's own class-separation scanner.
    sys.path.insert(0, str(Path("research_map").resolve()))
    import class_separation  # noqa: E402

    created = now_iso()
    ts = created.replace("-", "").replace(":", "").replace("+", "")[:15]

    claim_statement = (
        "Artifact-and-checker result, not a mathematics or physics claim and not a theorem: "
        "the F0 corpus schemas/taxonomy_cases.jsonl was internally self-contradictory "
        "(HF-094C-1: its meta bound taxonomy revision 5 while all 36 case rows still bound the "
        "superseded revision), so it could not serve as hash-bound gate evidence. The repair "
        "rebound exactly the 36 row pins to the taxonomy revision measured on disk, with a "
        "per-row content-preservation digest proving that no field other than binding_status "
        "changed, and rebound the leak-rule catalog's revision reference for the same reason. "
        "The class-separation checker was hardened with a stale-pin guard and an 11th control; "
        "it returns FAIL with 36 STALE_TAXONOMY_PIN errors on the pre-repair bytes and PASS "
        "with 11/11 controls on the post-repair bytes, where the four frozen classes remain "
        "separate and each is covered in both polarities. An independent verifier re-derived "
        "8 checks from the rollback snapshots and live files and returned PASS."
    )
    claim_falsifier = (
        "Any live case row whose content (all fields except binding_status) differs from the "
        "rollback snapshot, any row pin unequal to the 12-hex prefix of the taxonomy file "
        "measured on disk, a changed meta record, an orphaned catalog guard reference, a "
        "checker report not bound to the live corpus/catalog/taxonomy hashes, or a checker "
        "verdict other than PASS with 11/11 controls."
    )
    assumptions = [
        "The canonical taxonomy remains research_map/formulation_taxonomy.yaml rev5 at "
        "sha256 0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3.",
        "The 36 case rows' semantics are unchanged; only the revision they bind moved.",
        "The corpus is not listed in artifacts/formulation/FROZEN.json (rev28), so this repair "
        "is not a post-freeze edit of a frozen artifact.",
    ]

    # CF-16 hygiene: the scanner must find nothing in this claim's prose.
    scan_text = "\n".join([claim_statement] + assumptions + [claim_falsifier])
    findings = class_separation.findings_for_text(scan_text, "claim:flash02-f0-rebind-r2")
    if findings:
        print("SELF-REJECT: class-separation findings in own claim prose:")
        for f in findings:
            print("  -", f)
        return 2

    events = []
    for i, (path, atype, desc) in enumerate(ARTIFACTS, start=1):
        p = Path(path)
        if not p.exists():
            print(f"SELF-REJECT: missing artifact {path}")
            return 2
        events.append({
            "event_id": f"flash02-f0rebindr2-artifact-{i:04d}-{ts}",
            "event_type": "artifact",
            "created_at": created,
            "actor": "deepseek-flash-02",
            "node_id": "F0",
            "gate": "G-F0",
            "class_id": CLASS_ID,
            "artifact_type": atype,
            "path": path,
            "sha256": sha256_file(p),
            "validation_status": "unverified",
            "defect_ref": "HF-094C-1",
            "summary": desc,
            "authority_note": "worker event; cannot set node status=done, validation_status=passed, or a gate verdict",
        })

    evidence = [f"{e['path']}#{e['sha256'][:12]}" for e in events]
    events.append({
        "event_id": f"flash02-f0rebindr2-claim-0100b-{ts}",
        "event_type": "claim",
        "created_at": created,
        "actor": "deepseek-flash-02",
        "node_id": "F0",
        "gate": "G-F0",
        "class_id": CLASS_ID,
        "conclusion_type": "formal_model",
        "supersedes_rejected_event_id": f"flash02-f0rebindr2-claim-0100-{ts}",
        "supersede_reason": "previous emission used a non-schema conclusion_type and was rejected at ingest (schemas.py:46); conclusion_type now formal_model with claims_theorem_status false",
        "claims_theorem_status": False,
        "statement": claim_statement,
        "assumptions": assumptions,
        "falsifier": claim_falsifier,
        "evidence_refs": evidence,
        "artifact_refs": [e["path"] for e in events],
    })
    events.append({
        "event_id": f"flash02-f0rebindr2-status-0101-{ts}",
        "event_type": "status",
        "created_at": created,
        "actor": "deepseek-flash-02",
        "node_id": "F0",
        "gate": "G-F0",
        "class_id": CLASS_ID,
        "status": "active",
        "hours": 0.4,
        "summary": (
            "One class-bound task executed and closed: HF-094C-1 repair. Repairing the corpus "
            "moved its hash f0c20b96f76d -> ccf7041bd0ff and the catalog hash 215f6e228250 -> "
            "ccec815ea61d; therefore reviews/verdicts bound to the old hashes (including "
            "reviews/closefind-verify-094.json, itself a revise) are superseded and the lead "
            "must re-review at the new corpus hash. No node status, no validation_status=passed "
            "and no gate verdict is claimed by this worker."
        ),
        "evidence_refs": evidence,
        "next_falsifier": (
            "Re-run: python3 artifacts/flash-02/verify_rebind_r2.py (expect PASS, 8/8) and "
            "python3 artifacts/flash-02/check_taxonomy_cases.py (expect PASS, 11/11 controls); "
            "restore artifacts/flash-02/snapshots/taxonomy_cases.pre-rebind-r2.f0c20b96.jsonl "
            "if any row content differs from the snapshot."
        ),
    })

    # Idempotent append.
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
    OUTBOX.parent.mkdir(parents=True, exist_ok=True)
    with OUTBOX.open("a", encoding="utf-8") as f:
        for e in new:
            f.write(json.dumps(e, ensure_ascii=False, sort_keys=False) + "\n")

    print(f"emitted {len(new)} new events (skipped {len(events) - len(new)} existing)")
    for e in new:
        print(" ", e["event_id"], e["event_type"], e.get("path", ""))
    print(f"outbox: {OUTBOX}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
