#!/usr/bin/env python3
"""W037-F1-VISIBILITY-03 addendum: re-measure the visibility clauses at the post-emit F1 revision.

The primary adjudication (report.json) binds F1 sha256 b474fbc49cdd (T0==T1 at 2026-09-12T00:31:57+08:00).
The canonical F1 was rewritten again at 00:31:41-ish to rev12 (sha256 cce9c60146d6) and FROZEN.json moved
2554e276a0db -> 5fa3b3bf95f2 while this task's events were being emitted. This script measures the new bytes,
records which needles changed, and states what the rev12 binder repair does and does not fix.

Read-only. Usage: python3 remeasure_rev12.py [--out rev12_remeasure.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CST = timezone(timedelta(hours=8))

F1 = "schemas/af_wcc_vacuum.yaml"
F0 = "research_map/formulation_taxonomy.yaml"
FROZEN = "artifacts/formulation/FROZEN.json"
PRIMARY = "artifacts/worker-037/f1_visibility_equivalence_adjudication/report.json"

OLD = {
    "whole_curve_formal_clause": "not exists q in I+ with gamma subset J^-(q) intersect M.",
    "whole_curve_D5": "gamma([0,T)) is contained in the causal past J^-(q) intersected with M",
    "misclassification_sentence": "requiring the whole geodesic to lie in J^-(q) would misclassify",
}
NEW = {
    "tail_formal_clause": "not exists q in I+ and t0 in [0,T) with gamma([t0,T)) subset J^-(q) intersect M.",
    "tail_D5_binder": "pairs (q,t0) with q a point of I+ and t0 in [0,T) such that the tail",
    "strictness_claim_rev12": "Whole-curve containment gamma([0,T)) subset J^-(q) is strictly STRONGER and is NOT the predicate of this class",
}


def sha(rel: str) -> str:
    h = hashlib.sha256()
    with open(ROOT / rel, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "rev12_remeasure.json"))
    args = ap.parse_args()
    created = datetime.now(CST).strftime("%Y-%m-%dT%H:%M:%S%z")
    t0 = {p: sha(p) for p in (F1, F0, FROZEN, PRIMARY)}
    text = (ROOT / F1).read_text()
    lines = text.splitlines()

    def where(needle: str) -> list[int]:
        return [i for i, l in enumerate(lines, 1) if needle in l]

    primary = json.loads((ROOT / PRIMARY).read_text())
    rec = {
        "actor": "worker-037",
        "task_id": "W037-F1-VISIBILITY-03-ADDENDUM-REV12",
        "created_at": created,
        "class_id": "AF-WCC-VAC-GEN",
        "node_id": "F1",
        "gate": "G-FORM",
        "authority": "independent verification evidence only; no gate verdict, no node status, no canonical edit",
        "question": "After the rev12 rewrite of F1, does the binder repair discharge the W037V2-F1 finding, and do any "
                    "clauses of the primary adjudication need restating against the new bytes?",
        "primary_binding": {
            "report": PRIMARY, "report_sha256": t0[PRIMARY],
            "report_payload_sha256": primary["report_payload_sha256"],
            "F1_at_T0_T1_of_primary": primary["pins"]["T0"][F1],
            "F0_at_T0_T1_of_primary": primary["pins"]["T0"][F0],
            "FROZEN_at_T0_T1_of_primary": primary["pins"]["T0"][FROZEN],
        },
        "pins": {"T0": t0, "T1": None},
        "needles_old_primary_revision": {k: {"present_at_T0_of_primary": True, "present_now": v in text,
                                             "lines_now": where(v)} for k, v in OLD.items()},
        "needles_new_rev12": {k: {"present_now": v in text, "lines_now": where(v)} for k, v in NEW.items()},
        "discharged": {
            "binder_repair_landed": ("not exists q in I+ and t0 in [0,T)" in text),
            "statement": "rev12 replaces the whole-curve formal clause and the D5 reading with the (q,t0) tail binder, "
                         "so the operational recommendation of the primary adjudication and of W037V2-F1 is discharged "
                         "at the new bytes. The equivalence result itself (LEMMA-W026-1) is wording-level and "
                         "revision-independent: it never depended on which of the two equivalent phrasings was used.",
        },
        "not_fixed_by_rev12": {
            "strictness_sentence_at_D5": {
                "present": NEW["strictness_claim_rev12"] in text,
                "lines": where(NEW["strictness_claim_rev12"]),
                "why_false": "under (H) (J^- past-closed, gamma causal) whole-curve and tail containment are EQUIVALENT "
                             "for D4 geodesics, so neither is strictly stronger; the primary adjudication's exhaustive "
                             "finite-model check (389 transitive models, 4082 chains, 0 tail-without-whole) applies "
                             "verbatim to this sentence. The chosen predicate (tail) is correct; the stated relation is not.",
                "severity": "non-blocking (documentation precision; same reader-disagreement risk the schema's own "
                            "schema_falsifiers names)",
            },
            "misclassification_sentence_at_visibility_definition": {
                "present": OLD["misclassification_sentence"] in text,
                "lines": where(OLD["misclassification_sentence"]),
                "why_false": "for a geodesic that starts outside J^-(q) and ends in the black-hole region, both the "
                             "whole-curve and tail readings classify it as not visible, so the sentence does not "
                             "discriminate the two formulations (it is aimed at the B-containment confusion recorded "
                             "in visibility.negation_conclusion, not at the tail/whole distinction).",
                "severity": "non-blocking",
            },
            "recommended_minimal_fix": "state the equivalence once ('whole-curve and tail clauses agree because J^-(q) is "
                                       "past-closed and gamma is causal'), and drop the 'strictly STRONGER' / "
                                       "'would misclassify' justifications.",
        },
        "revision_independent_result": {
            "lemma": "LEMMA-W026-1 confirmed; W037V2-F1 mathematical claim refuted (see primary report)",
            "unchanged_at_rev12": True,
        },
        "drift_disclosure": "F1 b474fbc49cdd -> cce9c60146d6 and FROZEN 2554e276a0db -> 5fa3b3bf95f2 between the "
                            "primary run (00:31:57) and this re-measure, while the primary events were being emitted; "
                            "F0 unchanged at 0abb9ed8a961. Any controller binding must re-pin at the current hashes.",
        "falsifier": "At the measured rev12 bytes: exhibit a D4-admissible causal gamma and q in I+ where the tail "
                     "clause holds while whole-curve containment fails (would make the 'strictly STRONGER' sentence "
                     "true and this note false); or show the primary report's payload hash or pins do not match disk; "
                     "or show F1 does not contain the (q,t0) tail formal clause.",
        "next_falsifier": "Re-run adjudicate_visibility_equivalence.py and this script after the next F1 revision; the "
                          "note is superseded if the strictness/misclassification sentences are replaced by the "
                          "equivalence statement at a new hash.",
    }
    t1 = {p: sha(p) for p in (F1, F0, FROZEN, PRIMARY)}
    rec["pins"]["T1"] = t1
    rec["pins_stable"] = (t0 == t1)
    payload = json.dumps({k: v for k, v in rec.items() if k != "payload_sha256"}, sort_keys=True, separators=(",", ":"))
    rec["payload_sha256"] = hashlib.sha256(payload.encode()).hexdigest()
    out = Path(args.out)
    out.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
    print(f"wrote {out}")
    print(f"F1 now {t0[F1][:12]} (primary bound {rec['primary_binding']['F1_at_T0_T1_of_primary'][:12]}), pins_stable={rec['pins_stable']}")
    print(f"binder repair landed: {rec['discharged']['binder_repair_landed']}")
    print(f"strictness sentence present: {rec['not_fixed_by_rev12']['strictness_sentence_at_D5']['present']} "
          f"at {rec['not_fixed_by_rev12']['strictness_sentence_at_D5']['lines']}")
    if not rec["pins_stable"]:
        print("WARNING: pins moved during re-measure", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
