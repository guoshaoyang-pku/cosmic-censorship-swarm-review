#!/usr/bin/env python3
"""Why the controller's G-LIT 'class-token flag is cleared' message is empty.

Read-only probe. It answers one question mechanically:

  astra_lifecycle.py:349 prints "The ledger class-token flag is cleared at this hash."
  when `ledger_flags` is empty. `ledger_flags` (astra_lifecycle.py:263) is the subset of
  evidence-audit soft findings whose text contains "ledger/", and those findings come from
  class_separation.findings_for_text over each node's artifact (audit_evidence.py:110-119).

So the message is a detector result, not a statement that the ledger was repaired. This probe
measures the detector on the exact tokens the census (class_token_census_rev2.json) flags:

  * class_separation._class_tokens on the four frozen ids and the three non-frozen shorthands;
  * findings_for_text on the two current ledger files;
  * the source line that prints the "cleared" message, with the file hash.

Output is deterministic JSON on stdout; redirect it to detector_blindspot_probe.json.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLASS_SEP = ROOT / "research_map" / "class_separation.py"
LIFECYCLE = ROOT / "research_map" / "astra_lifecycle.py"
AUDIT = ROOT / "research_map" / "audit_evidence.py"
THEOREMS = ROOT / "ledger" / "theorems.jsonl"
CITATIONS = ROOT / "ledger" / "citation_audit.csv"

FROZEN = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
NON_FROZEN = ["AF-SCC", "AF-SCC-C0", "AF-SCC-C2"]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_cs():
    spec = importlib.util.spec_from_file_location("class_separation_probe", CLASS_SEP)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> dict:
    cs = load_cs()
    probe = {t: cs._class_tokens(t) for t in FROZEN + NON_FROZEN}
    findings = {
        "ledger/theorems.jsonl": cs.findings_for_text(THEOREMS.read_text(errors="replace"),
                                                      "ledger/theorems.jsonl"),
        "ledger/citation_audit.csv": cs.findings_for_text(CITATIONS.read_text(errors="replace"),
                                                          "ledger/citation_audit.csv"),
    }
    lifecycle_lines = LIFECYCLE.read_text().splitlines()
    cleared_line = next((i + 1 for i, ln in enumerate(lifecycle_lines)
                         if "class-token flag is cleared" in ln), None)
    flag_line = next((i + 1 for i, ln in enumerate(lifecycle_lines)
                      if "ledger_flags = " in ln), None)
    return {
        "artifact_type": "detector_blindspot_probe",
        "purpose": "Test whether the controller's G-LIT 'class-token flag is cleared' message "
                   "is evidence of ledger repair or an empty detector result.",
        "sources": {
            "research_map/class_separation.py": sha(CLASS_SEP),
            "research_map/astra_lifecycle.py": sha(LIFECYCLE),
            "research_map/audit_evidence.py": sha(AUDIT),
            "ledger/theorems.jsonl": sha(THEOREMS),
            "ledger/citation_audit.csv": sha(CITATIONS),
        },
        "token_probe": probe,
        "token_probe_interpretation": {
            "matched_frozen_ids": [t for t in FROZEN if probe[t]],
            "unmatched_frozen_ids": [t for t in FROZEN if not probe[t]],
            "matched_non_frozen_tokens": [t for t in NON_FROZEN if probe[t]],
            "note": "class_separation._class_tokens matches only ids with four hyphen groups "
                    "after 'AF-'; it cannot see AF-WCC-VAC-GEN, AF-WCC-SCALAR-SPH, or any of "
                    "the three non-frozen shorthand tokens the census flags.",
        },
        "findings_for_text": {k: {"count": len(v), "findings": v} for k, v in findings.items()},
        "ledger_flags_derivation": {
            "soft_findings_filter": "astra_lifecycle.py:%d -> ledger_flags = [s for s in soft "
                                    "if 'ledger/' in s]" % (flag_line or 0),
            "clear_message_line": "astra_lifecycle.py:%d" % (cleared_line or 0),
            "source_of_soft_findings": "audit_evidence.py:110-119 routes class_separation."
                                       "findings_for_text over node artifacts (ledger files are "
                                       "L0/L1 artifacts and are <2MB, so they are scanned)",
            "conclusion": "ledger_flags is empty because _class_tokens cannot match these token "
                          "shapes; the 'cleared' message is therefore a detector blind spot, not "
                          "evidence that the 5 non-frozen occurrences were repaired.",
        },
        "falsifier": "This probe is falsified if class_separation._class_tokens matches one of "
                     "the three non-frozen shorthands, or if findings_for_text on either ledger "
                     "file returns a non-empty list at these hashes, or if the 'cleared' message "
                     "is produced by a different code path than the one cited.",
    }


if __name__ == "__main__":
    print(json.dumps(main(), indent=2, sort_keys=True))
