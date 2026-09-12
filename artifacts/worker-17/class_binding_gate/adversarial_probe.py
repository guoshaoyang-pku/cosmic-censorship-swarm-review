#!/usr/bin/env python3
"""Adversarial probes for class_binding_gate.py: where the form-only gate stops.

The self-test proves the gate catches declared mutants. This probe asks the
opposite question: which *sneaky* documents still pass, and why? Those passes are
recorded as declared limits, not hidden, because a gate whose boundary is unknown
cannot be used safely by a review queue.

Writes adversarial_probe_report.json and exits 0 if the observed outcomes match
the declared expectations (the point is the declared boundary, not universal
rejection).
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import class_binding_gate as gate  # noqa: E402
import make_fixtures  # noqa: E402

REPORT = HERE / "adversarial_probe_report.json"


def _probe(name, doc, expected_pass, limit):
    violations = gate.check(doc, source=name)
    codes = sorted({v["code"] for v in violations})
    observed_pass = not violations
    return {
        "probe": name,
        "expected_gate_result": "PASS" if expected_pass else "FAIL",
        "observed_gate_result": "PASS" if observed_pass else "FAIL",
        "observed_codes": codes,
        "matched": observed_pass == expected_pass,
        "declared_limit": limit,
    }


def main():
    base = make_fixtures.good_wcc_vacuum()

    vacuous = copy.deepcopy(base)
    vacuous["visibility"]["visible_predicate"] = "Vis(p) := true for every boundary point"

    incoherent = copy.deepcopy(base)
    incoherent["genericity"]["statement"] = "the conclusion holds for all data with no exceptional set"

    provenance = copy.deepcopy(base)
    provenance["source_refs"] = ["AF-SCC-C2-VAC-GEN: survey of C^2-inextendibility"]

    smuggled = copy.deepcopy(base)
    smuggled["notes"] = "this is the C0 or C2 class, decided later"

    probes = [
        _probe(
            "vacuous_visible_predicate",
            vacuous,
            expected_pass=True,
            limit=(
                "Form-only gate cannot detect semantic vacuity: 'Vis(p) := true' is "
                "non-empty and syntactically a predicate. A human/independent reviewer "
                "must reject vacuous predicates; the gate only forces the slot to exist."
            ),
        ),
        _probe(
            "incoherent_genericity_statement",
            incoherent,
            expected_pass=True,
            limit=(
                "The gate checks slots independently, not cross-slot coherence: an "
                "'open dense' measure slot paired with an 'all data, no exceptions' "
                "statement passes. Coherence needs the A1 review, not this gate."
            ),
        ),
        _probe(
            "cross_class_text_in_source_refs",
            provenance,
            expected_pass=True,
            limit=(
                "source_refs and related_classes are exempt from the leakage scan by "
                "design (provenance and class relations must name other classes). "
                "Exemption is explicit: a reviewer must read those two subtrees."
            ),
        ),
        _probe(
            "c0_or_c2_in_body_text",
            smuggled,
            expected_pass=False,
            limit="Hard decision 1 is enforced globally: any 'C0 or C2' text fails.",
        ),
    ]

    report = {
        "gate": "class_binding_gate.py",
        "purpose": "declared boundary of the form-only gate",
        "all_matched": all(p["matched"] for p in probes),
        "limits_count": sum(1 for p in probes if p["expected_gate_result"] == "PASS"),
        "probes": probes,
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    for p in probes:
        print(
            f"{p['probe']:<38} expected={p['expected_gate_result']:<4} "
            f"observed={p['observed_gate_result']:<4} matched={p['matched']}"
        )
        if p["observed_gate_result"] == "PASS":
            print(f"    declared limit: {p['declared_limit']}")
    print(f"\nall_matched={report['all_matched']}  declared limits={report['limits_count']}")
    print(f"wrote {REPORT}")
    return 0 if report["all_matched"] else 1


if __name__ == "__main__":
    sys.exit(main())
