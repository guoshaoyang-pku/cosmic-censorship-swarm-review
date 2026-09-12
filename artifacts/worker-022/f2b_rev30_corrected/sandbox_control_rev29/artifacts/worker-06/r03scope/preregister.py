#!/usr/bin/env python3
"""Pre-registration for W006-R03-SCOPE-01 (scope-safety of published R03 repairs).

Everything below is fixed and hashed BEFORE any fixture is scored: the pinned input bytes,
the candidate tool set, the declared per-candidate semantics, the corpus manifest, the
hypotheses, the decision rule and the falsifier. The runner refuses to emit if the corpus
or any pin drifts afterwards.

Run order: make_fixtures.py -> preregister.py -> run_scope.py.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
CST = timezone(timedelta(hours=8))

PINS = {
    "schemas/af_wcc_vacuum.yaml": "d9cebb9404b2",
    "schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd3",
    "schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe",
    "artifacts/formulation/rule_spec.json": "40f9bb9e657b",
    "artifacts/formulation/FROZEN.json": "815e08079aef",
    "artifacts/worker-06/spec_conformance_audit.py": "c79d8ab8440a",
    "artifacts/worker-06/r03v2/audit_r03v2.py": "e41a4b23a840",
    "artifacts/worker-06/r03v2/r03v2_rule.py": None,  # measured here, no external pin
    "artifacts/worker-004/f1_r03_repair/patched/spec_conformance_audit.py": "645eb16a0060",
    "artifacts/worker-064/r03_cause/work/cand_E3/artifacts/worker-06/spec_conformance_audit.py": "3f69bc1eb27a",
}

CANDIDATES = {
    "frozen": {
        "path": "artifacts/worker-06/spec_conformance_audit.py",
        "rule": "accept iff the literal binder string `(q,t0)` is a substring of "
                "quantifiers.formal; no scope or order check",
    },
    "cand_r03v2": {
        "path": "artifacts/worker-06/r03v2/audit_r03v2.py",
        "rule": "binder-head co-binding: some quantifier clause head contains the binder "
                "identifiers in order, each within span=80 of the previous; the head ends at "
                "the first top-level `() : ; , with such-that where of letting` token",
    },
    "cand_004": {
        "path": "artifacts/worker-004/f1_r03_repair/patched/spec_conformance_audit.py",
        "rule": "every alphanumeric component of the binder must occur anywhere in "
                "quantifiers.formal as a whole word; no order or scope check",
    },
    "cand_E3": {
        "path": "artifacts/worker-064/r03_cause/work/cand_E3/artifacts/worker-06/"
                "spec_conformance_audit.py",
        "rule": "literal binder substring, else every comma-separated component must occur "
                "anywhere in quantifiers.formal as a substring; no order or scope check",
    },
}

QUESTION = (
    "On a fresh pre-registered scope-safety corpus at the live FROZEN rev29 bytes, does any "
    "published R03 repair separate CORRECT composite-binder renderings (must accept) from "
    "SCOPE-ERRONEOUS renderings where the negated quantifier does not bind every declared "
    "variable (must reject), and what are each candidate's false positives / false negatives?"
)
HYPOTHESES = {
    "H1": "cand_E3 accepts every scope-error fixture whose variable names occur as substrings, "
          "because its fallback test has no order or scope component (the lead's lifecycle-08 "
          "finding generalises beyond the single probe variant).",
    "H2": "cand_004 accepts every scope-error fixture whose variable names occur as whole words "
          "somewhere in the sentence, for the same reason.",
    "H3": "cand_r03v2 rejects the scope-error fixtures because a late-bound variable falls "
          "outside the quantifier clause's binder head, while still accepting every correct "
          "rendering whose identifiers stay within span=80; its two declared residues "
          "(comma-coordinated, ~140-char span) remain and are scored as edge probes only.",
    "H4": "frozen is scope-unsafe in both directions: it false-rejects correct renderings that "
          "do not repeat the literal tuple token, and false-accepts scope errors that contain "
          "the token non-bindingly.",
}

DECISION_RULE = (
    "Primary counts use scored fixtures only (6 pos / 8 neg). FP = scored positive rejected; "
    "FN = scored negative accepted. Edge probes and the canonical control are reported but not "
    "counted. A candidate is 'scope-safe on this corpus' iff FP = 0 and FN = 0. If cand_r03v2 "
    "has FP = FN = 0, its binder-head locality already implements the scope requirement of the "
    "lead's option A-prime on this corpus and no additional grouping requirement is needed; if "
    "it has any primary miss, the miss is the deliverable (a candidate R03-v3 must be written "
    "and calibrated on a NEW corpus, never this one)."
)
FALSIFIER = (
    "Any pinned input byte or fixture byte drifts between pre-registration and the run -> "
    "measurement VOID. Any fixture that fails a non-R03 rule under any candidate -> corpus "
    "format-dominated, measurement INVALID. Frozen control check not reproduced on the live "
    "canonicals (C0/C2 accept, WCC reject R03) -> INVALID. Raw auditor JSON not reproducible "
    "from the recorded commands -> INVALID. Standing falsifier for a candidate row: a later "
    "held-out scope corpus on which that candidate accepts a genuine scope error or rejects a "
    "genuine correct rendering."
)


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    manifest_path = HERE / "fixture_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    pins_measured = {rel: sha256(ROOT / rel) for rel in PINS}
    pin_report = {}
    for rel, prefix in PINS.items():
        got = pins_measured[rel]
        pin_report[rel] = {
            "sha256": got,
            "prefix": got[:12],
            "declared_prefix": prefix,
            "match": (prefix is None) or got.startswith(prefix),
        }
    mismatches = [r for r, v in pin_report.items() if not v["match"]]
    if mismatches:
        raise SystemExit(f"FATAL pin mismatch at pre-registration: {mismatches}")
    pre = {
        "task_id": "W006-R03-SCOPE-01",
        "worker": "worker-006",
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "node_id": "A1",
        "gate": "G-CLASSBIND",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "question": QUESTION,
        "hypotheses": HYPOTHESES,
        "candidates": CANDIDATES,
        "pins": pin_report,
        "instrument_governance_note": (
            "The stage-2 rule engine is NOT pinned in artifacts/formulation/FROZEN.json "
            "(lead lifecycle-08 blocker lead-form-20260912T011516-123). This pre-registration "
            "therefore pins every candidate tool by its own sha256 above; the frozen file is "
            "never written."),
        "corpus": {
            "manifest": "artifacts/worker-06/r03scope/fixture_manifest.json",
            "manifest_sha256": sha256(manifest_path),
            "fixtures": len(manifest["fixtures"]),
            "scored_pos": sum(1 for f in manifest["fixtures"] if f["scored"] and f["category"] == "pos"),
            "scored_neg": sum(1 for f in manifest["fixtures"] if f["scored"] and f["category"] == "neg"),
            "edges": sum(1 for f in manifest["fixtures"] if f["category"] == "edge"),
            "controls": sum(1 for f in manifest["fixtures"] if f["category"] == "control"),
            "freshness": "no fixture is reused from W006-R03-CAND-HEADTOHEAD-01, the R03-v2 "
                         "calibration set, the worker-004 calibration set or the shielded "
                         "heldout corpora; every mutant is single-target surgery on "
                         "quantifiers.formal of the live canonical WCC",
        },
        "controls": {
            "canonical_schemas": ["schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml",
                                  "schemas/af_scc_c0_vacuum.yaml"],
            "expected_frozen": "C0 accept, C2 accept, WCC reject on R03 only",
            "expected_repairs": "all three canonical schemas accepted",
        },
        "measurement_plan": [
            "run every candidate tool over every fixture with identical commands",
            "run every candidate tool over the three live canonical schemas",
            "reject a fixture as format-dominated if any candidate reports a non-R03 failure",
            "require non-R03 failed-rule sets identical across candidates per file",
            "re-measure all pins and all fixture hashes after the run",
        ],
        "decision_rule": DECISION_RULE,
        "falsifier": FALSIFIER,
        "scoring_note": (
            "Declared expectations per fixture x candidate are in fixture_manifest.json and were "
            "written from the rule semantics above before any fixture was scored. They are not "
            "used to compute FP/FN; FP/FN are computed from category (pos must accept, neg must "
            "reject). Expectations only expose surprises."),
        "not_claimed": "no gate verdict, no node completion, no theorem, no physics result, "
                       "no adoption recommendation; worker evidence only",
    }
    out = HERE / "preregistration.json"
    out.write_text(json.dumps(pre, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "preregistration": str(out),
        "preregistration_sha256": sha256(out),
        "corpus_manifest_sha256": pre["corpus"]["manifest_sha256"],
        "pins_ok": len(pin_report),
        "mismatches": mismatches,
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
