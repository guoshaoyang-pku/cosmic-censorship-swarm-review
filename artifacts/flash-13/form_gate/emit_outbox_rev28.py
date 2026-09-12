#!/usr/bin/env python3
"""Emit the rev28 G-CLASSBIND re-verdict events to comms/outbox/deepseek-flash-13.jsonl.

Fail-closed:
  * every artifact is re-hashed and must match the binding record;
  * FROZEN.json must not have drifted since the gate run;
  * every event is validated against research_map/schemas.py before it is written;
  * duplicate event ids abort the whole batch (nothing is written).
Appends only; never rewrites the outbox.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUTBOX = ROOT / "comms" / "outbox" / "deepseek-flash-13.jsonl"
RECORD = HERE / "canonical_recheck_rev28.json"

sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main() -> int:
    rec = json.loads(RECORD.read_text())
    prefix = rec["event_prefix"]
    now = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")

    paths = {
        "gate": ROOT / "artifacts/flash-13/form_gate/check_class_schema.py",
        "gatereport": ROOT / "artifacts/flash-13/form_gate/gate_report_rev28.json",
        "fixturesuite": ROOT / "artifacts/flash-13/form_gate/fixture_suite_report.json",
        "tailprobedriver": ROOT / "artifacts/flash-13/form_gate/f1_tail_visibility_probe.py",
        "tailprobe": ROOT / "artifacts/flash-13/form_gate/f1_tail_visibility_probe_rev28.json",
        "recheck": ROOT / "artifacts/flash-13/form_gate/canonical_recheck_rev28.json",
    }
    shas = {k: sha(p) for k, p in paths.items()}
    fz = ROOT / "artifacts/formulation/FROZEN.json"
    fz_sha = sha(fz)

    # fail closed on drift
    if shas["gatereport"] != rec["artifacts"]["gate_report_rev28.json"]:
        print("ABORT: gate_report_rev28.json changed since the binding record was written")
        return 2
    if shas["fixturesuite"] != rec["artifacts"]["fixture_suite_report.json"]:
        print("ABORT: fixture_suite_report.json changed since the binding record was written")
        return 2
    if shas["tailprobe"] != rec["artifacts"]["f1_tail_visibility_probe_rev28.json"]:
        print("ABORT: probe evidence changed since the binding record was written")
        return 2
    if shas["tailprobedriver"] != rec["artifacts"]["f1_tail_visibility_probe.py"]:
        print("ABORT: probe driver changed since the binding record was written")
        return 2
    if fz_sha != rec["frozen_manifest"]["sha256"]:
        print(f"ABORT: FROZEN.json drifted {rec['frozen_manifest']['sha256'][:12]} -> {fz_sha[:12]}")
        return 2

    cid = ";".join(rec["class_ids"])
    frozen_doc = json.loads(fz.read_text())
    tax_sha = frozen_doc["files"]["research_map/formulation_taxonomy.yaml"]["sha256"]
    ref = {
        "gate": f"artifacts/flash-13/form_gate/check_class_schema.py#{shas['gate'][:16]}",
        "gatereport": f"artifacts/flash-13/form_gate/gate_report_rev28.json#{shas['gatereport'][:16]}",
        "fixturesuite": f"artifacts/flash-13/form_gate/fixture_suite_report.json#{shas['fixturesuite'][:16]}",
        "tailprobedriver": f"artifacts/flash-13/form_gate/f1_tail_visibility_probe.py#{shas['tailprobedriver'][:16]}",
        "tailprobe": f"artifacts/flash-13/form_gate/f1_tail_visibility_probe_rev28.json#{shas['tailprobe'][:16]}",
        "recheck": f"artifacts/flash-13/form_gate/canonical_recheck_rev28.json#{shas['recheck'][:16]}",
        "frozen": f"artifacts/formulation/FROZEN.json#{fz_sha[:16]}",
        "rule_spec": f"artifacts/formulation/rule_spec.json#{rec['published_rule_text']['sha256'][:16]}",
        "taxonomy": f"research_map/formulation_taxonomy.yaml#{tax_sha[:16]}",
    }

    rule_line = "; ".join(
        f"{r['class_id']} {r['sha256'][:12]} {r['verdict'].upper()}"
        + (f" (skip {','.join(k for k, v in r['per_rule'].items() if v == 'skip')})"
           if any(v == 'skip' for v in r['per_rule'].values()) else "")
        for r in rec["results"]
    )
    p = rec["tail_visibility_probe"]

    events = [
        {
            "event_id": f"{prefix}-art-gatereport",
            "event_type": "artifact",
            "created_at": now,
            "actor": "deepseek-flash-13",
            "node_id": "F1",
            "gate": "G-CLASSBIND",
            "artifact_type": "gate_report",
            "class_id": cid,
            "path": "artifacts/flash-13/form_gate/gate_report_rev28.json",
            "sha256": shas["gatereport"],
            "validation_status": "unverified",
            "evidence_refs": [ref["gatereport"], ref["gate"], ref["frozen"], ref["rule_spec"]],
            "note": ("FORM-GATE-01 v1.1 run on the three rev12 canonical schemas; per-class per-rule "
                     "verdicts with json_path; frozen_match=true for all three against FROZEN rev28."),
        },
        {
            "event_id": f"{prefix}-art-fixturesuite",
            "event_type": "artifact",
            "created_at": now,
            "actor": "deepseek-flash-13",
            "node_id": "F1",
            "gate": "G-CLASSBIND",
            "artifact_type": "gate_control_report",
            "class_id": cid,
            "path": "artifacts/flash-13/form_gate/fixture_suite_report.json",
            "sha256": shas["fixturesuite"],
            "validation_status": "unverified",
            "evidence_refs": [ref["fixturesuite"], ref["gate"], ref["rule_spec"]],
            "note": ("Control run: 3/3 conforming fixtures pass; 24/24 single-rule mutants rejected "
                     "(16/24 keyed to exactly one rule; 6 SCC mutants also fire R06); rephrased corpus "
                     "5 caught / 1 documented blind spot; exit 0 conforming / exit 3 canonical absent."),
        },
        {
            "event_id": f"{prefix}-art-tailprobedriver",
            "event_type": "artifact",
            "created_at": now,
            "actor": "deepseek-flash-13",
            "node_id": "F1",
            "gate": "G-CLASSBIND",
            "artifact_type": "probe_driver",
            "class_id": "AF-WCC-VAC-GEN",
            "path": "artifacts/flash-13/form_gate/f1_tail_visibility_probe.py",
            "sha256": shas["tailprobedriver"],
            "validation_status": "unverified",
            "evidence_refs": [ref["tailprobedriver"], ref["tailprobe"], ref["frozen"]],
            "note": ("Re-runnable, deterministic; stdlib+PyYAML; imports no other worker's gate; reads "
                     "only canonical paths; writes only under artifacts/flash-13/."),
        },
        {
            "event_id": f"{prefix}-art-tailprobe",
            "event_type": "artifact",
            "created_at": now,
            "actor": "deepseek-flash-13",
            "node_id": "F1",
            "gate": "G-CLASSBIND",
            "artifact_type": "probe_evidence",
            "class_id": "AF-WCC-VAC-GEN",
            "path": "artifacts/flash-13/form_gate/f1_tail_visibility_probe_rev28.json",
            "sha256": shas["tailprobe"],
            "validation_status": "unverified",
            "evidence_refs": [ref["tailprobe"], ref["tailprobedriver"], ref["frozen"], ref["taxonomy"]],
            "note": (f"Lead-declared F1 next-falsifier probe: {p['checks_passed']}/{p['checks_total']} checks pass; "
                     "class_contract_pointer resolves in the canonical taxonomy; every normative visibility "
                     "slot is the tail form; 0 whole-curve residues flagged, 2 contrast sentences exempted, "
                     "1 registered SET variant context reported; finite-model control 768 models, 0 "
                     "whole=>tail violations, 258 tail-vs-whole classification-divergence witnesses; "
                     "self-controls prove the probe can fail."),
        },
        {
            "event_id": f"{prefix}-art-recheck",
            "event_type": "artifact",
            "created_at": now,
            "actor": "deepseek-flash-13",
            "node_id": "F1",
            "gate": "G-CLASSBIND",
            "artifact_type": "binding_record",
            "class_id": cid,
            "path": "artifacts/flash-13/form_gate/canonical_recheck_rev28.json",
            "sha256": shas["recheck"],
            "validation_status": "unverified",
            "evidence_refs": [ref["recheck"], ref["gatereport"], ref["fixturesuite"],
                              ref["tailprobe"], ref["frozen"]],
            "note": "Binds gate, spec, FROZEN rev28 and all four measurements into one record.",
        },
        {
            "event_id": f"{prefix}-claim",
            "event_type": "claim",
            "created_at": now,
            "actor": "deepseek-flash-13",
            "node_id": "F1",
            "gate": "G-CLASSBIND",
            "class_id": cid,
            "conclusion_type": "stability_result",
            "statement": (
                "At FROZEN revision 28 (2f358f6722d9) the three rev12 canonical class schemas pass all "
                "published R01-R16 checks of FORM-RULE-SPEC v1.2 under the independent FORM-GATE-01 v1.1 "
                f"gate (ad7d120b8449): {rule_line}. The fixture suite keeps its controls (3/3 conforming "
                "pass, 24/24 mutants rejected, exit 3 on absent canonical). The lead-declared F1 next "
                f"falsifier is negative: {p['checks_passed']}/{p['checks_total']} probe checks pass - "
                "class_contract_pointer resolves in canonical taxonomy 0abb9ed8a961; visibility.definition, "
                "visibility.negation_conclusion, quantifiers.formal and domain D5 all carry the tail form; "
                "the written negation has the De Morgan scope of the tail existential; 0 whole-curve "
                "residues remain in normative slots (2 contrast sentences exempted, the registered SET "
                "variant reported separately); over 768 abstract finite models whole-curve containment "
                "implies the tail predicate with 0 violations and 258 models where the two readings "
                "classify the same object differently, so the rev12 whole-curve-to-tail repair is "
                "content-bearing, not cosmetic."
            ),
            "assumptions": [
                "FROZEN rev28 pins the three canonical schema hashes measured here; any republication "
                "invalidates this verdict and requires a re-run",
                "the published rule text is artifacts/formulation/rule_spec.json v1.2 (R01-R16); the gate "
                "is bounded to it (F-GATE-4: the lead tool's R17+ have no published text)",
                "the canonical taxonomy hash 0abb9ed8a961 is the pointer target named by F1 rev12",
                "the tail probe is structural and order-theoretic; it constructs no spacetime and does "
                "not decide whether the tail reading is the physically correct one",
                "the registered class_identity_variants SET slot deliberately keeps the set-based reading "
                "and is excluded from the canonical-predicate residue scan, reported explicitly",
            ],
            "falsifier": rec["falsifier"],
            "evidence_refs": [ref["gatereport"], ref["fixturesuite"], ref["tailprobe"],
                              ref["tailprobedriver"], ref["recheck"], ref["gate"],
                              ref["frozen"], ref["rule_spec"], ref["taxonomy"]],
            "artifact_refs": [
                "artifacts/flash-13/form_gate/gate_report_rev28.json",
                "artifacts/flash-13/form_gate/fixture_suite_report.json",
                "artifacts/flash-13/form_gate/f1_tail_visibility_probe_rev28.json",
                "artifacts/flash-13/form_gate/canonical_recheck_rev28.json",
            ],
            "not_claimed": rec["not_claimed"],
        },
        {
            "event_id": f"{prefix}-status",
            "event_type": "status",
            "created_at": now,
            "actor": "deepseek-flash-13",
            "node_id": "F1",
            "status": "active",
            "hours": 0.5,
            "summary": (
                "CHECKPOINT / G-CLASSBIND rev12 re-verdict closed, unverified pending review. Took ONE "
                "class-bound task: independent executable gate re-verdict at the F1/F2a/F2b rev12 hashes "
                "plus the lead's declared F1 next-falsifier probe. Result: PASS at FROZEN rev28 for all "
                f"three classes ({rule_line}); controls green; tail-visibility probe {p['checks_passed']}/"
                f"{p['checks_total']} with 0 flagged residues; no gate self-pass (proposal pending), no "
                "node completion. F-GATE-4 (unpublished R17+) unchanged and still limits parity."
            ),
            "evidence_refs": [ref["recheck"], ref["gatereport"], ref["tailprobe"], ref["frozen"]],
            "next_falsifier": rec["next_falsifier"],
        },
        {
            "event_id": f"{prefix}-gate-proposal",
            "event_type": "gate",
            "created_at": now,
            "actor": "deepseek-flash-13",
            "gate_id": "G-CLASSBIND",
            "scope": "F1/F2a/F2b rev12 canonical schemas at FROZEN rev28",
            "verdict": "pending",
            "criteria": (
                "PROPOSAL ONLY, not set by this worker. Criteria measured: all published R01-R16 checks "
                "pass on all three canonical schemas under the independent gate (frozen_match=true); "
                "fixture suite controls green; F1 next-falsifier probe green; evidence hash-bound. "
                "Requested: lead-formulation / controller adjudication."
            ),
            "evidence_refs": [ref["recheck"], ref["gatereport"], ref["fixturesuite"], ref["tailprobe"]],
        },
    ]

    for ev in events:
        validate_event(ev)
    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            if line.strip():
                existing.add(json.loads(line).get("event_id"))
    dupes = [e["event_id"] for e in events if e["event_id"] in existing]
    if dupes:
        print(f"ABORT: duplicate event ids {dupes}; nothing written")
        return 2

    with open(OUTBOX, "a") as f:
        for ev in events:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")

    print(json.dumps({
        "appended": len(events),
        "outbox": str(OUTBOX.relative_to(ROOT)),
        "event_ids": [e["event_id"] for e in events],
        "sha256": {k: v for k, v in shas.items()},
        "frozen_sha256": fz_sha,
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
