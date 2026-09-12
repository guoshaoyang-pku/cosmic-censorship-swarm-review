#!/usr/bin/env python3
"""W035-F0-CLASSSEP-REPAIR-01 -- deterministic repair check for the sole hard
class-separation failure in research_map.json.

Task (class-bound): the map's own claim `flash02-opencase-claim-0010b-20260912T0015`
describes two *negative composite-filing* taxonomy cases (TC-F0-N14, TC-F0-N15) whose
disposition is reject_split_required, i.e. the two frozen SCC classes and the WCC/SCC
families stay distinct. Its prose shorthand "C0/C2 merge" is read by the project's own
detector (research_map/class_separation.py) as asserting a composite class, which is the
single remaining hard failure in runtime/state/checkpoints/ckpt-20260912-001747.json.

This script:
  1. pins the canonical research_map.json by sha256,
  2. reproduces the hard finding on the pinned bytes,
  3. builds a minimal, meaning-preserving rewording of only that statement,
  4. proves the reworded map clears the finding while a genuine merge still fires
     (negative control), and that nothing else in the map changed,
  5. runs the project's own audit_evidence.audit() on an original and a patched copy
     (never on the canonical map) to show the hard failure disappears.

It never writes research_map.json. Offline, deterministic, no network.

Usage: python3 run_repair_check.py
Exit 0 = all checks pass AND canonical map byte-unchanged by this run.
"""
from __future__ import annotations

import copy
import difflib
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ART = Path(__file__).resolve().parent
ROOT = ART.parents[2]
sys.path.insert(0, str(ROOT / "research_map"))
import class_separation as cs  # noqa: E402
import audit_evidence  # noqa: E402

CST = timezone(timedelta(hours=8))
MAP = ROOT / "research_map" / "research_map.json"
TARGET_EVENT_ID = "flash02-opencase-claim-0010b-20260912T0015"
TASK_ID = "W035-F0-CLASSSEP-REPAIR-01"

ORIGINAL_TAIL = ("the 2 split rows (TC-F0-N14 C0/C2 merge, TC-F0-N15 WCC/SCC merge) "
                 "need no new class and are decidable by the formulation lead now.")

REPAIRED_TAIL = ("the 2 split rows are negative composite filings dispositioned "
                 "reject_split_required - TC-F0-N14 (a C0-vs-C2 composite filing) and "
                 "TC-F0-N15 (a WCC-vs-SCC composite filing) - which keeps "
                 "AF-SCC-C0-VAC-GEN and AF-SCC-C2-VAC-GEN as two distinct classes and "
                 "WCC distinct from SCC; neither row needs a new class id and both are "
                 "decidable by the formulation lead now.")

# negative control: a genuine merge assertion in the same slot must still be detected
NEG_CONTROL_TAIL = ("the 2 split rows (TC-F0-N14 C0/C2 merge, TC-F0-N15 WCC/SCC merge) "
                    "are one merged class and are decidable by the formulation lead now.")

# content invariants the rewording must preserve (substrings of both original and repaired)
PRESERVED = [
    "9 open=true",
    "7 deferred new-class requests",
    "2 split dispositions",
    "with 0 new class ids introduced",
    "0/9 rows matching a frozen class on recomputation",
    "TC-F0-N14",
    "TC-F0-N15",
    "astra-classscope-02",
    "decidable by the formulation lead now",
]
# the repaired text must additionally assert separation explicitly
MUST_ASSERT = ["reject_split_required", "distinct"]
# composites that must not survive in the repaired text as raw merge shorthand
MUST_ABSENT = ["C0/C2", "C2/C0", "C0 or C2", "C2 or C0"]


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def hard(findings: list) -> list:
    return [f for f in findings if not str(f).startswith("CLASSSEP-SOFT:")]


def locate_claim(m: dict) -> int:
    idx = [i for i, c in enumerate(m.get("claims", []))
           if isinstance(c, dict) and c.get("event_id") == TARGET_EVENT_ID]
    if len(idx) != 1:
        raise SystemExit(f"PRECONDITION: expected exactly 1 claim {TARGET_EVENT_ID}, found {idx}")
    return idx[0]


def diff_paths(a, b, path=""):
    """Yield JSON-ish paths where two decoded documents differ."""
    if type(a) is not type(b):
        yield path or "/"
        return
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                yield f"{path}/{k}"
            else:
                yield from diff_paths(a[k], b[k], f"{path}/{k}")
    elif isinstance(a, list):
        if len(a) != len(b):
            yield path or "/"
            return
        for i, (x, y) in enumerate(zip(a, b)):
            yield from diff_paths(x, y, f"{path}/{i}")
    elif a != b:
        yield path or "/"


def main() -> int:
    checks: list[dict] = []

    def check(name: str, ok: bool, observed):
        checks.append({"check": name, "pass": bool(ok), "observed": observed})
        return bool(ok)

    map_before = MAP.read_bytes()
    pre_sha = sha256_bytes(map_before)
    m = json.loads(map_before)

    i = locate_claim(m)
    c = m["claims"][i]
    orig_stmt = c["statement"]
    check("precondition_exactly_one_target_claim", True, {"event_id": TARGET_EVENT_ID, "claims_index": i})
    check("precondition_original_tail_present_once",
          orig_stmt.count(ORIGINAL_TAIL) == 1, {"count": orig_stmt.count(ORIGINAL_TAIL)})

    # 1. reproduce the hard finding on the pinned bytes
    f_orig = cs.findings_for_map(m)
    h_orig = hard(f_orig)
    check("reproduce_single_hard_classsep_finding_on_pinned_map",
          len(h_orig) == 1 and f"claims[{i}].statement" in h_orig[0] and "C0/C2" in h_orig[0],
          {"map_sha256": pre_sha, "hard_findings": h_orig, "soft_findings":
           [f for f in f_orig if f not in h_orig]})

    # 2. project-native baseline audit on the canonical bytes (read-only call)
    a_orig = audit_evidence.audit(MAP)
    check("project_audit_baseline_contains_this_hard_failure",
          any("claims" in x and "C0/C2" in x for x in a_orig["hard"]),
          {"audit_hard": a_orig["hard"], "audit_soft": a_orig["soft"]})

    # 3. minimal, meaning-preserving rewording
    repaired_stmt = orig_stmt.replace(ORIGINAL_TAIL, REPAIRED_TAIL)
    check("rewording_changes_exactly_one_clause",
          repaired_stmt != orig_stmt and repaired_stmt.count(REPAIRED_TAIL) == 1
          and repaired_stmt.replace(REPAIRED_TAIL, "") == orig_stmt.replace(ORIGINAL_TAIL, ""),
          {"changed_chars": len(repaired_stmt) - len(orig_stmt)})

    m_rep = copy.deepcopy(m)
    m_rep["claims"][i]["statement"] = repaired_stmt
    diff = list(diff_paths(m, m_rep))
    check("minimality_only_target_statement_path_changed",
          diff == [f"/claims/{i}/statement"], {"changed_paths": diff})

    f_rep = cs.findings_for_map(m_rep)
    h_rep = hard(f_rep)
    check("repaired_map_clears_the_hard_classsep_finding",
          h_rep == [], {"hard_findings": h_rep, "soft_findings":
                        [f for f in f_rep if f not in h_rep]})

    # 4. content invariants preserved
    missing = [t for t in PRESERVED if t not in repaired_stmt]
    check("content_invariants_preserved", not missing, {"missing": missing})
    absent = [t for t in MUST_ASSERT if t not in repaired_stmt]
    check("separation_asserted_explicitly", not absent, {"missing": absent})
    still = [t for t in MUST_ABSENT if t in repaired_stmt]
    check("raw_merge_shorthand_removed", not still, {"still_present": still})
    check("class_ids_and_conclusion_type_untouched",
          m_rep["claims"][i]["class_ids"] == c["class_ids"]
          and m_rep["claims"][i]["conclusion_type"] == c["conclusion_type"],
          {"class_ids": c["class_ids"], "conclusion_type": c["conclusion_type"]})

    # 5. negative control: a genuine merge assertion must still be flagged
    m_neg = copy.deepcopy(m)
    m_neg["claims"][i]["statement"] = orig_stmt.replace(ORIGINAL_TAIL, NEG_CONTROL_TAIL)
    h_neg = hard(cs.findings_for_map(m_neg))
    check("negative_control_genuine_merge_still_flagged",
          len(h_neg) >= 1 and f"claims[{i}].statement" in h_neg[0],
          {"negative_control_findings": h_neg})

    # 6. project-native acceptance test on a patched COPY (canonical map never written)
    proposed_dir = ART / "proposed"
    proposed_dir.mkdir(exist_ok=True)
    patched_path = proposed_dir / "research_map.patched.json"
    patched_path.write_text(json.dumps(m_rep, indent=2, sort_keys=True) + "\n")
    a_rep = audit_evidence.audit(patched_path)
    classsep_gone = not any("claims" in x and "C0/C2" in x for x in a_rep["hard"])
    no_new_hard = len(a_rep["hard"]) <= len(a_orig["hard"])
    check("project_audit_on_patched_copy_removes_this_hard_failure_and_adds_none",
          classsep_gone and no_new_hard,
          {"audit_hard_before": a_orig["hard"], "audit_hard_after": a_rep["hard"],
           "patched_copy": str(patched_path.relative_to(ROOT))})

    # 7. canonical map byte-unchanged by this run
    map_after = MAP.read_bytes()
    check("canonical_map_byte_unchanged_by_this_run",
          sha256_bytes(map_after) == pre_sha,
          {"map_sha256_before": pre_sha, "map_sha256_after": sha256_bytes(map_after)})

    unified = "".join(difflib.unified_diff(
        orig_stmt.splitlines(keepends=True), repaired_stmt.splitlines(keepends=True),
        fromfile=f"claims[{i}].statement (original)", tofile=f"claims[{i}].statement (proposed)"))

    proposal = {
        "task_id": TASK_ID,
        "worker": "worker-035",
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "precondition_map_sha256": pre_sha,
        "map_updated_at_measured": m.get("updated_at"),
        "target": {
            "kind": "map_claim_statement",
            "claim_event_id": TARGET_EVENT_ID,
            "claims_index_measured": i,
            "node_id": c.get("node_id"),
            "gate": c.get("gate"),
            "class_id": c.get("class_id"),
            "class_ids": c.get("class_ids"),
            "conclusion_type": c.get("conclusion_type"),
        },
        "defect": {
            "source": "research_map/class_separation.py findings_for_map (prose mode)",
            "rule": "R1 composite C0/C2 merge assertion (regex _MERGE_PAT + _MERGE_ASSERT)",
            "finding": h_orig[0] if h_orig else None,
            "why_it_is_prose_only": (
                "TC-F0-N14 as filed is a negative composite case (as_filed_class_id=COMPOSITE_C0_C2, "
                "expected_resolution=reject_split_required); the claim's shorthand 'C0/C2 merge' "
                "names the case, not an accepted class fusion. The detector cannot see that the "
                "surrounding clause says 'split rows', because the merge assertion sits inside the "
                "match window and takes precedence."),
            "rule_is_not_weakened": "negative control in this run still flags a genuine merge",
        },
        "repair": {
            "field": f"/claims/{i}/statement",
            "original_statement": orig_stmt,
            "proposed_statement": repaired_stmt,
            "unified_diff": unified,
            "patch_pointer": f"/claims/{i}/statement",
            "target_by_event_id_not_index": True,
        },
        "acceptance_test": [
            "controller replaces the statement of claim event_id %s with proposed_statement "
            "(re-locate the index by event_id; the index may shift as claims are appended)" % TARGET_EVENT_ID,
            "python3 research_map/audit_evidence.py exits 0 (baseline had exactly this 1 hard finding)",
            "python3 research_map/validate_map.py still reports VALID",
        ],
        "falsifiers": [
            "precondition stale: research_map.json sha256 differs from %s when the patch is applied" % pre_sha,
            "any CLASSSEP hard or soft finding on the patched map",
            "any change outside /claims/<target>/statement (patch not minimal)",
            "the negative-control merge text is NOT flagged (detector weakened)",
            "research_map/validate_map.py no longer VALID after the patch",
        ],
        "non_claims": [
            "not a gate verdict; cannot move G-F0 or any gate",
            "does not set validation_status=passed",
            "does not edit research_map.json; the canonical map was only read",
            "does not adjudicate the taxonomy cases themselves; it preserves the authoring claim's meaning",
        ],
        "evidence_refs": [
            "research_map/research_map.json#sha256:" + pre_sha[:12],
            "research_map/class_separation.py",
            "runtime/state/checkpoints/ckpt-20260912-001747.json",
            "artifacts/worker-035/f0-claim36-classsep-repair/verification.json",
            "artifacts/worker-035/f0-claim36-classsep-repair/proposed/research_map.patched.json",
        ],
    }
    (ART / "proposal.json").write_text(json.dumps(proposal, indent=1, sort_keys=True) + "\n")

    patch = {
        "task_id": TASK_ID,
        "op": "replace",
        "path": f"/claims/{i}/statement",
        "precondition_map_sha256": pre_sha,
        "target_claim_event_id": TARGET_EVENT_ID,
        "target_by_event_id_not_index": True,
        "value": repaired_stmt,
        "expected_effect": "audit_evidence.py hard findings drops by exactly this one classsep item",
    }
    (proposed_dir / "map_patch_claim_statement.json").write_text(
        json.dumps(patch, indent=1, sort_keys=True) + "\n")

    verification = {
        "task_id": TASK_ID,
        "worker": "worker-035",
        "created_at": proposal["created_at"],
        "map_sha256": pre_sha,
        "map_updated_at_measured": m.get("updated_at"),
        "target_claim_event_id": TARGET_EVENT_ID,
        "checks": checks,
        "passed": all(x["pass"] for x in checks),
        "counts": {
            "checks_total": len(checks),
            "checks_passed": sum(1 for x in checks if x["pass"]),
            "baseline_hard_findings": len(a_orig["hard"]),
            "patched_hard_findings": len(a_rep["hard"]),
            "baseline_soft_findings": len(a_orig["soft"]),
            "patched_soft_findings": len(a_rep["soft"]),
        },
        "falsifiers": proposal["falsifiers"],
        "non_claims": proposal["non_claims"],
    }
    (ART / "verification.json").write_text(json.dumps(verification, indent=1, sort_keys=True) + "\n")

    print(json.dumps({"task_id": TASK_ID, "passed": verification["passed"],
                      "counts": verification["counts"],
                      "failed_checks": [x for x in checks if not x["pass"]],
                      "map_sha256": pre_sha}, indent=2))
    return 0 if verification["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
