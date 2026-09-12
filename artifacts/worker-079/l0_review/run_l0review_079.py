#!/usr/bin/env python3
"""W079-L0-BLIND-FULL-REVIEW-01 machine checks (deterministic, fail-closed).

Read-only instrument for the second independent blind full review of L0 at the
announced rev3-final hash. Pre-registration: PREREGISTRATION.json (same dir).

Exit codes
  0  report written, all pins stable, all controls detected
  2  pin drift -> no report written (review void)
  3  a negative control was not detected -> no report written

The report contains no timestamp, so re-running at the same pins must reproduce
l0_machine_checks.json byte-for-byte.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

PINS = {
    "ledger/theorems.jsonl": "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28",
    "ledger/citation_audit.csv": "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9",
    "artifacts/formulation/FROZEN.json": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "schemas/taxonomy_cases.jsonl": "ccf7041bd0ff3ce844c07a700a588b7fe8e3c90880674c5e595b21f6259a8f03",
}
FROZEN_CLASSES = {
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
}
VERIFICATION_VOCAB = {"unverified", "abstract-read", "full-text", "page-checked"}
CONTENT_STATUS_VOCAB = {"verified", "provisional", "rejected"}
HF14_KEYS = ("status", "validation_status", "supports_claim")
REQUIRED_FIELDS = (
    "statement_exact", "assumptions", "does_not_imply", "falsifiers",
    "source_ids", "unresolved", "scope_caveats", "class_ids",
)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_inputs():
    rows = [json.loads(line) for line in (ROOT / "ledger/theorems.jsonl").read_text().splitlines() if line.strip()]
    citations = list(csv.DictReader((ROOT / "ledger/citation_audit.csv").open()))
    return rows, citations


def truthy(v) -> bool:
    return v is not None and v is not False and v != "" and v != [] and v != {}


def checks(rows, citations) -> dict:
    src_ids = {c["citation_id"] for c in citations}
    audit_used = set()
    for c in citations:
        for t in (c.get("used_by_theorems") or "").split(";"):
            t = t.strip()
            if t:
                audit_used.add(t)
    tids = [r.get("theorem_id") for r in rows]

    p2_rows = [r.get("theorem_id") for r in rows if any(truthy(r.get(k)) for k in HF14_KEYS)]
    # class_ids is presence-only here; an empty class_ids list is reported as O2, not a P5 failure.
    missing_fields = sorted(
        f"{r.get('theorem_id')}:{f}"
        for r in rows for f in REQUIRED_FIELDS
        if f not in r or (f != "class_ids" and not r.get(f))
    )
    dangling_fwd = sorted({s for r in rows for s in (r.get("source_ids") or []) if s not in src_ids})
    dangling_rev = sorted(t for t in audit_used if t not in set(tids))
    bad_tokens = sorted(
        {t for r in rows for t in (list(r.get("class_ids") or []) + list(r.get("informs_classes") or []))
         if t not in FROZEN_CLASSES}
    )
    bad_vocab = sorted(
        {str(r.get("verification_status")) for r in rows if r.get("verification_status") not in VERIFICATION_VOCAB}
    )
    bad_content = sorted({str(r.get("content_status")) for r in rows if r.get("content_status") not in CONTENT_STATUS_VOCAB})
    empty_review = sorted(r.get("theorem_id") for r in rows if not r.get("review_status"))
    overstated = sorted(
        r.get("theorem_id") for r in rows
        if r.get("content_status") == "verified" and r.get("verification_status") == "unverified"
    )
    unlabelled = sorted(r.get("theorem_id") for r in rows if not r.get("acceptance_authority"))
    fake_verdict = sorted(
        r.get("theorem_id") for r in rows
        if str(r.get("review_status", "")).startswith("independently_reviewed")
        and not any(k in r for k in ("reviewer", "verdict", "artifact_refs"))
    )
    empty_ids = [r.get("theorem_id") for r in rows if not (r.get("class_ids") or [])]
    informs = [r.get("theorem_id") for r in rows if (r.get("class_ids") or []) == [] and (r.get("informs_classes") or [])]
    neither = [r.get("theorem_id") for r in rows if not (r.get("class_ids") or []) and not (r.get("informs_classes") or [])]
    dual = [r.get("theorem_id") for r in rows if len(r.get("class_ids") or []) >= 2]
    dual_disclaimed = {
        r.get("theorem_id"): bool(r.get("does_not_imply"))
        for r in rows if len(r.get("class_ids") or []) >= 2
    }
    hf01 = [r.get("theorem_id") for r in rows if r.get("conclusion_type") == "theorem" and not r.get("artifact_refs")]

    return {
        "P1_PIN_STABILITY": True,  # established by main() before/after
        "P2_HF14_TRIPLE": {"pass": not p2_rows, "rows": p2_rows},
        "P3_ROW_FLOOR": {"pass": len(rows) >= 15, "rows": len(rows)},
        "P4_UNIQUE_IDS": {"pass": len(tids) == len(set(tids)) and all(tids), "rows": len(rows),
                          "distinct": len(set(tids))},
        "P5_REQUIRED_FIELDS": {"pass": not missing_fields, "missing": missing_fields},
        "P6_VOCAB_VERIFICATION": {"pass": not bad_vocab, "offending": bad_vocab},
        "P7_SOURCE_LINKAGE_FORWARD": {"pass": not dangling_fwd, "dangling": dangling_fwd},
        "P8_SOURCE_LINKAGE_REVERSE": {"pass": not dangling_rev, "dangling": dangling_rev,
                                      "citation_audit_refs": len(audit_used)},
        "P9_CLASS_TOKENS_FROZEN": {"pass": not bad_tokens, "offending": bad_tokens},
        "P10_AXES_VOCAB": {"pass": not bad_content and not empty_review, "content_offending": bad_content,
                           "empty_review_status": empty_review},
        "P11_NO_OVERSTATED_VERIFICATION": {"pass": not overstated, "rows": overstated},
        "P12_SELF_ASSESSMENT_LABELLED": {"pass": not unlabelled and not fake_verdict,
                                         "unlabelled": unlabelled, "fake_verdict": fake_verdict},
        "observations": {
            "O1_DUAL_CLASS_ROWS": {"count": len(dual), "rows": dual,
                                   "own_disclaimer_present": dual_disclaimed},
            "O2_EMPTY_CLASS_IDS": {"count": len(empty_ids), "rows": empty_ids,
                                   "with_informs_classes": informs, "with_neither": neither},
            "O3_RUBRIC_DETECTOR_SCOPE": {"hf01_literal_theorem_rows_without_artifact_refs": hf01,
                                         "hf02_literal_multi_class_rows": dual,
                                         "note": "detector-scope observations only; CF-16 / CLASSSEP calibration is the lead-audit card astra-life05-classsep-calibration"},
        },
        "counts": {
            "rows": len(rows),
            "citation_rows": len(citations),
            "content_status": {v: sum(1 for r in rows if r.get("content_status") == v) for v in sorted(CONTENT_STATUS_VOCAB)},
            "review_status": {v: sum(1 for r in rows if r.get("review_status") == v)
                              for v in sorted({str(r.get("review_status")) for r in rows})},
            "verification_status": {v: sum(1 for r in rows if r.get("verification_status") == v) for v in sorted(VERIFICATION_VOCAB)},
            "class_token_census": {c: sum(1 for r in rows for t in (list(r.get("class_ids") or []) + list(r.get("informs_classes") or [])) if t == c)
                                   for c in sorted(FROZEN_CLASSES)},
        },
    }


def hard_pass(result: dict) -> bool:
    return all(v["pass"] for k, v in result.items() if k.startswith("P") and isinstance(v, dict))


def run_controls(rows, citations) -> dict:
    """Six in-memory mutants; each must make its target check fail."""
    results = {}
    m = [dict(r) for r in rows]
    m[0] = dict(m[0]); m[0]["status"] = "accepted"
    results["M1_truthy_status_detected"] = not checks(m, citations)["P2_HF14_TRIPLE"]["pass"]
    m = [dict(r) for r in rows]
    m[1] = dict(m[1]); m[1]["class_ids"] = list(m[1]["class_ids"]) + ["AF-EXTENSION-LABEL"]
    results["M2_extension_class_token_detected"] = not checks(m, citations)["P9_CLASS_TOKENS_FROZEN"]["pass"]
    m = [dict(r) for r in rows]
    m[2] = dict(m[2]); m[2]["source_ids"] = list(m[2]["source_ids"]) + ["SRC-999"]
    results["M3_dangling_source_id_detected"] = not checks(m, citations)["P7_SOURCE_LINKAGE_FORWARD"]["pass"]
    m = [dict(r) for r in rows]
    m[3] = dict(m[3]); m[3]["falsifiers"] = []
    results["M4_empty_falsifiers_detected"] = not checks(m, citations)["P5_REQUIRED_FIELDS"]["pass"]
    c = [dict(x) for x in citations]
    c[0] = dict(c[0]); c[0]["used_by_theorems"] = (c[0].get("used_by_theorems") or "") + ";T-999"
    results["M5_dangling_used_by_theorems_detected"] = not checks(rows, c)["P8_SOURCE_LINKAGE_REVERSE"]["pass"]
    m = [dict(r) for r in rows]
    m[4] = dict(m[4]); m[4]["content_status"] = "accepted"
    results["M6_off_vocabulary_content_status_detected"] = not checks(m, citations)["P10_AXES_VOCAB"]["pass"]
    return results


def main() -> int:
    before = {p: sha256_file(ROOT / p) for p in PINS}
    drift = {p: (PINS[p], before[p]) for p in PINS if before[p] != PINS[p]}
    if drift:
        print(json.dumps({"status": "PIN_DRIFT", "drift": drift}, indent=1))
        return 2

    rows, citations = load_inputs()
    controls = run_controls(rows, citations)
    if not all(controls.values()):
        print(json.dumps({"status": "CONTROL_FAILURE", "controls": controls}, indent=1))
        return 3

    result = checks(rows, citations)
    result["P1_PIN_STABILITY"] = {"pass": True, "pins": before}
    result["control_pass"] = controls
    result["verdict_recommendation"] = "accept" if hard_pass({k: v for k, v in result.items() if k != "observations"}) else "revise"

    after = {p: sha256_file(ROOT / p) for p in PINS}
    if after != before:
        print(json.dumps({"status": "PIN_DRIFT_DURING_RUN", "before": before, "after": after}, indent=1))
        return 2

    out = HERE / "l0_machine_checks.json"
    out.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"status": "OK", "report": str(out.relative_to(ROOT)),
                      "verdict_recommendation": result["verdict_recommendation"],
                      "report_sha256": sha256_file(out)}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
