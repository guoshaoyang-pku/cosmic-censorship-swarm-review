#!/usr/bin/env python3
"""Emit the W04 F1 post-rebind recheck events to comms/outbox/deepseek-flash-04.jsonl.

Builds, schema-validates and appends the upward events for the recheck bundle.
Idempotent by guard: an event_id already present in the outbox file is skipped.
No map mutation (ingest is the controller's step), no gate verdict, no status promotion.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUTBOX = ROOT / "comms" / "outbox" / "deepseek-flash-04.jsonl"
SCHEMAS = ROOT / "research_map" / "schemas.py"
F1 = ROOT / "schemas" / "af_wcc_vacuum.yaml"
FROZEN = ROOT / "artifacts" / "formulation" / "FROZEN.json"
SUITE = ROOT / "schemas" / "f1_falsifier_tests.jsonl"
F0 = ROOT / "research_map" / "formulation_taxonomy.yaml"
REPORT = ROOT / "artifacts" / "worker-004" / "f1_recheck" / "report.json"
TOOL = ROOT / "artifacts" / "worker-004" / "f1_recheck" / "recheck.py"
README = ROOT / "artifacts" / "worker-004" / "f1_recheck" / "README.md"
PRIOR_VERIFY_REPORT = ROOT / "artifacts" / "flash-04" / "f1_ambiguity" / "frozen_current_verification.json"

EXPECTED_F1_PREFIX = "9a8bd4c9"
ACTOR = "deepseek-flash-04"
INSTANCE = "worker-004-20260912T002201-968807"
NOW = _dt.datetime.now(_dt.timezone(_dt.timedelta(hours=8))).isoformat(timespec="seconds")


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


spec = importlib.util.spec_from_file_location("map_schemas", SCHEMAS)
map_schemas = importlib.util.module_from_spec(spec)
sys.modules["map_schemas"] = map_schemas  # dataclasses needs the module registered
spec.loader.exec_module(map_schemas)

f1_sha = sha(F1)
if not f1_sha.startswith(EXPECTED_F1_PREFIX):
    print(json.dumps({"error": "schema_drift", "measured": f1_sha,
                      "expected_prefix": EXPECTED_F1_PREFIX,
                      "action": "re-run recheck.py at the new hash before emitting"}, indent=1))
    raise SystemExit(2)

frozen_sha = sha(FROZEN)
suite_sha = sha(SUITE)
f0_sha = sha(F0)
report_sha = sha(REPORT)
tool_sha = sha(TOOL)
readme_sha = sha(README)
prior_verify_sha = sha(PRIOR_VERIFY_REPORT)

ref = {
    "f1": f"schemas/af_wcc_vacuum.yaml#sha256:{f1_sha[:16]}",
    "frozen": f"artifacts/formulation/FROZEN.json#sha256:{frozen_sha[:16]}",
    "suite": f"schemas/f1_falsifier_tests.jsonl#sha256:{suite_sha[:16]}",
    "f0": f"research_map/formulation_taxonomy.yaml#sha256:{f0_sha[:16]}",
    "report": f"artifacts/worker-004/f1_recheck/report.json#sha256:{report_sha[:16]}",
    "tool": f"artifacts/worker-004/f1_recheck/recheck.py#sha256:{tool_sha[:16]}",
    "readme": f"artifacts/worker-004/f1_recheck/README.md#sha256:{readme_sha[:16]}",
    "prior_verify_report": f"artifacts/flash-04/f1_ambiguity/frozen_current_verification.json#sha256:{prior_verify_sha[:16]}",
    "input_box": "comms/inbox/deepseek-flash-04.jsonl:1-3",
    "review_090": "reviews/F1-review-090.json",
    "review_094": "reviews/F1-review-094.json",
}

base = {
    "actor": ACTOR,
    "created_at": NOW,
    "runtime_instance": INSTANCE,
    "class_id": "AF-WCC-VAC-GEN",
    "node_id": "F1",
    "gate": "G-FORM",
}

events = [
    {
        **base,
        "event_id": "w04-20260912T0026-artifact-f1-recheck-report",
        "event_type": "artifact",
        "artifact_type": "verification_report",
        "path": "artifacts/worker-004/f1_recheck/report.json",
        "sha256": report_sha,
        "validation_status": "unverified",
        "summary": (
            "Read-only post-rebind recheck at canonical F1 9a8bd4c9 / FROZEN rev26: F090-04 "
            "falsified (suite 25 rows, all bound to 9a8bd4c9, acceptance fields complete); "
            "HF090-01 pointer-not-canonical, HF090-02/HF-094-2 duplicate+future revised_at, "
            "HF090-03 undefined AF_{I+}, F090-05 hashless consistency evidence reproduced; "
            "suite probes none of those three defect surfaces. Advisory revise; no gate verdict."
        ),
        "evidence_refs": [ref["f1"], ref["frozen"], ref["suite"], ref["f0"], ref["report"], ref["input_box"]],
        "falsifier": (
            "A reader who shows the suite is not bound to 9a8bd4c9, resolves "
            "class_contract_pointer in the canonical taxonomy, parses a unique non-future "
            "revised_at, or finds a definition of AF_{I+}."
        ),
    },
    {
        **base,
        "event_id": "w04-20260912T0026-artifact-f1-recheck-tool",
        "event_type": "artifact",
        "artifact_type": "verification_tool",
        "path": "artifacts/worker-004/f1_recheck/recheck.py",
        "sha256": tool_sha,
        "validation_status": "unverified",
        "summary": (
            "Deterministic read-only recheck tool; writes only its --out report and fails "
            "closed (exit 2) when the canonical F1 hash does not match --expect-sha."
        ),
        "evidence_refs": [ref["tool"], ref["f1"], ref["suite"]],
        "falsifier": "Run it twice with the same inputs: differing report bytes falsify determinism.",
    },
    {
        **base,
        "event_id": "w04-20260912T0026-artifact-f1-recheck-readme",
        "event_type": "artifact",
        "artifact_type": "evidence_bundle_readme",
        "path": "artifacts/worker-004/f1_recheck/README.md",
        "sha256": readme_sha,
        "validation_status": "unverified",
        "summary": "Human-readable bundle summary, per-check result table and next falsifiers.",
        "evidence_refs": [ref["readme"], ref["report"]],
        "falsifier": "A README claim not backed by report.json is a documentation defect.",
    },
    {
        **base,
        "event_id": "w04-20260912T0026-artifact-frozen-verify-supersede",
        "event_type": "artifact",
        "artifact_type": "verification_report",
        "path": "artifacts/flash-04/f1_ambiguity/frozen_current_verification.json",
        "sha256": prior_verify_sha,
        "validation_status": "unverified",
        "supersedes_evidence_ref": "artifacts/flash-04/f1_ambiguity/frozen_current_verification.json#sha256:9fa4f77c",
        "summary": (
            "Superseding hash record for the prior freeze-verification report (D1): "
            "verify_freeze_current.py has no argparse and rewrites this report in place on any "
            "invocation; invoking it at 00:25:01 superseded 9fa4f77c with the measured hash. "
            "The rewritten report still says verify_pass at FROZEN rev26, 25 tests, 84/84 probes."
        ),
        "evidence_refs": [ref["prior_verify_report"], ref["tool"], ref["frozen"], ref["f1"]],
        "falsifier": (
            "Restore a copy of this path hashing 9fa4f77c and re-measure; if the published "
            "evidence ref resolves again, the supersession record is void."
        ),
    },
    {
        **base,
        "event_id": "w04-20260912T0026-claim-f1-postrebind-recheck",
        "event_type": "claim",
        "conclusion_type": "formal_model",
        "statement": (
            "At frozen canonical F1 sha256 9a8bd4c9 (FROZEN manifest revision 26, pin matches "
            "measured), schemas/f1_falsifier_tests.jsonl is 25 JSONL rows with one distinct "
            "binding_sha256 equal to the target hash, 25/25 rows carrying spacetime "
            "description + does_it_satisfy_f1 + deciding_field, so reviewer-090 finding "
            "F090-04 ('24 rows bound to b65fcc0f, not citable for these bytes') is falsified "
            "at this hash. Independently reproduced at the same hash: (i) class_contract_pointer "
            "line 38 targets the authoring taxonomy and its fragment class_contracts."
            "AF-WCC-VAC-GEN does not resolve in the canonical taxonomy (classes."
            "AF-WCC-VAC-GEN does); (ii) seven duplicate revised_at keys last-win to a "
            "future-dated 2026-09-12T00:30:00+08:00; (iii) AF_{I+} at line 251 has no "
            "definition; (iv) taxonomy_consistency.json reports consistent=true without "
            "content hashes. No theorem, no gate verdict, no node transition."
        ),
        "assumptions": [
            "the canonical path schemas/af_wcc_vacuum.yaml is authoritative at the bound hash",
            "the FROZEN manifest pin for the canonical F1 path equals the measured canonical sha256 at measurement time",
            "the review findings of workers 090/094 are quoted as claims to be tested, not as authority",
            "read-only measurement; the only writes are this bundle's own files",
        ],
        "falsifier": (
            "Any of: a suite row with a binding other than 9a8bd4c9; the canonical taxonomy "
            "resolving class_contracts.AF-WCC-VAC-GEN; a unique non-future parsed revised_at; "
            "an explicit AF_{I+} definition; or taxonomy_consistency.json carrying the two "
            "tree hashes. Each refutes the corresponding clause of the statement."
        ),
        "evidence_refs": [ref["report"], ref["f1"], ref["suite"], ref["frozen"], ref["f0"],
                          ref["tool"], ref["review_090"], ref["review_094"]],
        "artifact_refs": [ref["report"], ref["tool"]],
    },
    {
        **base,
        "event_id": "w04-20260912T0026-review-f1-revise",
        "event_type": "review",
        "target_id": "F1",
        "artifact": "schemas/af_wcc_vacuum.yaml",
        "artifact_sha256": f1_sha,
        "reviewer": ACTOR,
        "verdict": "revise",
        "score": 3.5,
        "gate": "G-FORM",
        "class_id": "AF-WCC-VAC-GEN",
        "authority_note": (
            "advisory worker verdict bound to the measured hash; workers cannot set a gate "
            "verdict, node status or validation_status=passed"
        ),
        "hard_failures": [
            {"id": "HF090-01-reproduced", "status": "open", "severity": "major",
             "detail": "class_contract_pointer line 38 targets artifacts/formulation/formulation_taxonomy.yaml#class_contracts.AF-WCC-VAC-GEN; fragment unresolved in canonical research_map/formulation_taxonomy.yaml (key is classes)."},
            {"id": "HF090-02-reproduced", "status": "open", "severity": "major",
             "detail": "7x revised_at + 2x revised_at_unused top-level keys; last-wins revised_at=2026-09-12T00:30:00+08:00 is future vs mtime 00:19:14 and wall clock."},
            {"id": "HF090-03-reproduced", "status": "open", "severity": "major",
             "detail": "AF_{I+} at line 251 (conclusion.statement_formal) undefined in schema, both F0 trees and rule_spec.json."},
        ],
        "findings": [
            "F090-04 (suite bound to b65fcc0f, 24 rows) is falsified: suite is 25 rows, one distinct binding 9a8bd4c9, acceptance fields complete.",
            "F090-05 reproduced: artifacts/formulation/evidence/taxonomy_consistency.json (9e335e9ba1bf) asserts consistent=true with no sha256 of either compared tree.",
            "Coverage gap: no suite row probes class_contract_pointer, revised_at hygiene or AF_{I+}; a minimal three-row increment would have caught the open hard failures.",
            "Self-reported drift D1: verify_freeze_current.py rewrote its hash-pinned report in place on invocation (9fa4f77c -> 0e79514a); superseding artifact event emitted.",
            "Observed, not adjudicated: W037-F5 D0-disjunction surface present in all three class schemas.",
        ],
        "resolved": [
            "HF-094-1: declared F0 sha256 equals measured canonical research_map/formulation_taxonomy.yaml 276009f4 at the bound hash",
        ],
        "falsifier": (
            "A reader who repoints the pointer to the canonical fragment, deduplicates the "
            "revision keys to one wall-clock-valid value, or defines AF_{I+}, and re-measures "
            "at the resulting hash, refutes the corresponding hard failure."
        ),
        "evidence_refs": [ref["f1"], ref["frozen"], ref["suite"], ref["f0"], ref["report"],
                          ref["review_090"], ref["review_094"]],
        "checked_at_hash": f1_sha,
    },
    {
        **base,
        "event_id": "w04-20260912T0026-status-f1-postrebind-recheck",
        "event_type": "status",
        "status": "active",
        "hours": 0.5,
        "summary": (
            "W04-F1-POSTREBIND-RECHECK-01 complete (worker task complete; node status remains "
            "lead-owned). At canonical F1 9a8bd4c9 / FROZEN rev26: suite binding verified (25 "
            "rows, 84/84 probes per the superseding freeze report) and F090-04 falsified; "
            "HF090-01/02/03 reproduced; advisory review verdict revise emitted. D1 disclosed: "
            "invoking verify_freeze_current.py rewrites its own hash-pinned report; superseding "
            "artifact event emitted. No gate verdict, no done claim, no theorem."
        ),
        "evidence_refs": [ref["report"], ref["f1"], ref["suite"], ref["frozen"],
                          ref["prior_verify_report"], ref["tool"]],
        "next_falsifier": (
            "F1 owner fixes the three reproduced defects at a new hash; re-run recheck.py with "
            "--expect-sha of the new hash: D3-D5 must flip to not_refuted. If a gate read cites "
            "F090-04 as a suite defect, re-measure the suite first."
        ),
    },
]

# --- validate + idempotent append -------------------------------------------------
existing = set()
if OUTBOX.exists():
    for line in OUTBOX.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            existing.add(json.loads(line).get("event_id"))
        except json.JSONDecodeError:
            continue

written, skipped = [], []
for ev in events:
    map_schemas.validate_event(ev)
    if ev["event_id"] in existing:
        skipped.append(ev["event_id"])
        continue
    with OUTBOX.open("a") as fh:
        fh.write(json.dumps(ev, ensure_ascii=False) + "\n")
    written.append(ev["event_id"])

print(json.dumps({
    "outbox": OUTBOX.relative_to(ROOT).as_posix(),
    "written": written,
    "skipped_existing": skipped,
    "validated": True,
    "hashes": {"f1": f1_sha, "frozen": frozen_sha, "suite": suite_sha,
               "report": report_sha, "tool": tool_sha, "readme": readme_sha,
               "prior_verify_report": prior_verify_sha},
}, indent=1))
