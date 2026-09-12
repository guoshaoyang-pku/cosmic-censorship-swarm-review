#!/usr/bin/env python3
"""Check the F0 open-case disposition matrix against corpus + frozen taxonomy.

Deterministic. Usage:
  python3 artifacts/flash-02/check_open_case_disposition.py

Writes:
  artifacts/flash-02/open_case_disposition_check_report.json

Checks (each error is prefixed with a stable code used by the controls):
  OPEN_CASE_UNCOVERED / EXTRA_CASE_ROW / DUPLICATE_CASE_ROW
  INVALID_DISPOSITION / MISSING_FALSIFIER / MISSING_HYPOTHESIS
  NEW_CLASS_TOKEN / FROZEN_CLASS_MATCH / VOCABULARY_MATCH
  UNRESOLVED_RULE_REF / MISSING_EVIDENCE_HASH
  MISSING_BOUND_PARENT / BAD_FILING_VERDICT / WORKER_ADJUDICATION_CLAIM
  MISSING_REQUESTED_SCOPE / SPURIOUS_REQUESTED_SCOPE / SUMMARY_MISMATCH / BAD_DIRECTIVE

The seven mutation controls at the bottom must each be detected; all seven run
in-memory on deep copies, so the artifact on disk is never mutated.
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CST = timezone(timedelta(hours=8))
CORPUS = ROOT / "schemas" / "taxonomy_cases.jsonl"
TAXONOMY = ROOT / "research_map" / "formulation_taxonomy.yaml"
ARTIFACT = ROOT / "artifacts" / "flash-02" / "open_case_disposition.json"
REPORT = ROOT / "artifacts" / "flash-02" / "open_case_disposition_check_report.json"

AXES = ["family", "matter_model", "symmetry", "asymptotics", "regularity_token",
        "genericity_kind", "conclusion_type"]
DISPOSITIONS = {
    "NEW_CLASS_REQUEST_DEFERRED_TO_HUMAN_PI",
    "SPLIT_REQUIRED",
    "SPLIT_AND_BRIDGE_REQUIRED",
}
FILING_VERDICTS = {"reject", "reject_or_split"}
EXPECTED_FROZEN = {
    "AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def resolve(obj, dotted: str):
    """Resolve a dotted taxonomy ref; list segments match an element's 'id'."""
    cur = obj
    for seg in dotted.split("."):
        if isinstance(cur, dict):
            if seg not in cur:
                raise KeyError(dotted)
            cur = cur[seg]
        elif isinstance(cur, list):
            hit = [x for x in cur if isinstance(x, dict) and x.get("id") == seg]
            if not hit:
                raise KeyError(dotted)
            cur = hit[0]
        else:
            raise KeyError(dotted)
    return cur


def validate(tax: dict, corpus: list[dict], art: dict) -> tuple[list[str], dict]:
    errs: list[str] = []
    meta: dict = {}

    frozen = list(tax.get("class_ids", []))
    meta["frozen_class_ids"] = frozen
    if set(frozen) != EXPECTED_FROZEN or len(frozen) != 4:
        errs.append(f"BAD_FROZEN_SET: taxonomy class_ids={frozen}")

    directive = (tax.get("class_scope_adjudication") or {}).get("directive")
    meta["directive"] = directive
    if directive != "astra-classscope-02":
        errs.append(f"BAD_DIRECTIVE: {directive!r} != 'astra-classscope-02'")

    if set(art.get("frozen_class_ids", [])) != EXPECTED_FROZEN:
        errs.append(f"BAD_FROZEN_SET: artifact frozen_class_ids={art.get('frozen_class_ids')}")

    # Direction compliance: no new AF-* token anywhere in the artifact.
    blob = json.dumps(art)
    import re
    tokens = set(re.findall(r"AF-[A-Z0-9]+(?:-[A-Z0-9]+)*", blob))
    foreign = sorted(t for t in tokens if t not in EXPECTED_FROZEN)
    meta["af_tokens_seen"] = sorted(tokens)
    if foreign:
        errs.append(f"NEW_CLASS_TOKEN: {foreign}")

    corpus_sha = sha256(CORPUS) if CORPUS.exists() else ""
    tax_sha = sha256(TAXONOMY) if TAXONOMY.exists() else ""
    corpus_open = {r["case_id"]: r for r in corpus if r.get("open") is True}
    rows = art.get("rows", [])
    row_ids = [r.get("case_id") for r in rows]

    seen: set = set()
    for cid in row_ids:
        if cid in seen:
            errs.append(f"DUPLICATE_CASE_ROW: {cid}")
        seen.add(cid)
    for cid in sorted(set(corpus_open) - set(row_ids)):
        errs.append(f"OPEN_CASE_UNCOVERED: {cid}")
    for cid in sorted(set(row_ids) - set(corpus_open)):
        errs.append(f"EXTRA_CASE_ROW: {cid}")

    rule_ref_checked = 0
    axis_rows = 0
    matches = 0
    for row in rows:
        cid = row.get("case_id")
        disp = row.get("disposition")
        if disp not in DISPOSITIONS:
            errs.append(f"INVALID_DISPOSITION: {cid} -> {disp!r}")
        if not row.get("falsifier"):
            errs.append(f"MISSING_FALSIFIER: {cid}")
        if not row.get("decisive_hypothesis"):
            errs.append(f"MISSING_HYPOTHESIS: {cid}")
        if row.get("status") != "proposed_not_adjudicated" or row.get("worker_can_adjudicate") is not False:
            errs.append(f"WORKER_ADJUDICATION_CLAIM: {cid} status={row.get('status')!r}")

        parents = row.get("bound_parent_class_ids") or []
        if not parents or any(p not in EXPECTED_FROZEN for p in parents):
            errs.append(f"MISSING_BOUND_PARENT: {cid} -> {parents}")
        if row.get("filing_verdict") not in FILING_VERDICTS:
            errs.append(f"BAD_FILING_VERDICT: {cid} -> {row.get('filing_verdict')!r}")

        if row.get("gap_ref"):
            gap_ids = {g["id"] for g in tax.get("coverage_gaps", [])}
            if row["gap_ref"].split(".")[-1] not in gap_ids:
                errs.append(f"UNRESOLVED_RULE_REF: {cid} gap_ref={row['gap_ref']}")
        for ref in row.get("rule_refs", []):
            try:
                resolve(tax, ref)
                rule_ref_checked += 1
            except KeyError:
                errs.append(f"UNRESOLVED_RULE_REF: {cid} ref={ref}")

        ev = " ".join(row.get("evidence_refs", []))
        if tax_sha[:12] not in ev or corpus_sha[:12] not in ev:
            errs.append(f"MISSING_EVIDENCE_HASH: {cid}")

        # Disposition/scope coupling.
        if disp == "NEW_CLASS_REQUEST_DEFERRED_TO_HUMAN_PI":
            if not row.get("requested_scope"):
                errs.append(f"MISSING_REQUESTED_SCOPE: {cid}")
            if not parents:
                errs.append(f"MISSING_BOUND_PARENT: {cid}")
        else:
            if row.get("requested_scope"):
                errs.append(f"SPURIOUS_REQUESTED_SCOPE: {cid}")

        # Independent axis recomputation against the frozen classes.
        av = row.get("axis_vector")
        if av is not None:
            axis_rows += 1
            matched = []
            for cid2, cls in (tax.get("classes") or {}).items():
                axes = cls.get("axes", {})
                diff = [a for a in AXES if av.get(a) != axes.get(a)]
                if not diff:
                    matched.append(cid2)
            if matched:
                matches += 1
                errs.append(f"FROZEN_CLASS_MATCH: {cid} matches {matched}")
            meta.setdefault("axis_recompute", {})[cid] = {
                "checked": True, "frozen_class_matches": matched,
            }
        else:
            vv = row.get("violated_vocabulary") or []
            if not vv:
                errs.append(f"VOCABULARY_MATCH: {cid} has neither axis_vector nor violated_vocabulary")
            for item in vv:
                axis, value = item.get("axis"), item.get("value")
                allowed = (tax.get("field_vocabulary", {}).get(axis) or {}).get("allowed")
                if allowed is None:
                    errs.append(f"UNRESOLVED_RULE_REF: {cid} vocabulary axis={axis}")
                elif value in allowed:
                    errs.append(f"VOCABULARY_MATCH: {cid} {axis}={value} is in vocabulary")

    counts = {
        "rows": len(rows),
        "open_cases": len(corpus_open),
        "axis_rows_recomputed": axis_rows,
        "frozen_class_matches": matches,
        "rule_refs_resolved": rule_ref_checked,
        "new_class_ids_created": 0,
    }
    summ = art.get("summary", {})
    if (summ.get("open_cases"), summ.get("rows")) != (len(corpus_open), len(rows)):
        errs.append(f"SUMMARY_MISMATCH: {summ} vs corpus_open={len(corpus_open)} rows={len(rows)}")
    meta["counts"] = counts
    return errs, meta


def build_report(tax: dict, corpus: list[dict], art: dict, created_at: str,
                 base_errs: list[str], meta: dict, controls: list[dict]) -> dict:
    all_controls_pass = all(c["detected"] for c in controls)
    verdict = "PASS" if (not base_errs and all_controls_pass) else "FAIL"
    return {
        "report_version": "1.0",
        "artifact_id": "artifacts/flash-02/open_case_disposition_check_report.json",
        "node_id": "F0",
        "gate": "G-F0",
        "assignment_event_id": "asg-2026-09-11-F0-deepseek-flash-02-11",
        "actor": "deepseek-flash-02",
        "created_at": created_at,
        "verdict": verdict,
        "errors": base_errs,
        "inputs": {
            "corpus": {"path": "schemas/taxonomy_cases.jsonl", "sha256": sha256(CORPUS)},
            "taxonomy": {"path": "research_map/formulation_taxonomy.yaml", "sha256": sha256(TAXONOMY)},
            "disposition": {
                "path": "artifacts/flash-02/open_case_disposition.json",
                "sha256": sha256(ARTIFACT),
            },
        },
        "checks": meta,
        "controls": controls,
        "controls_detected": sum(1 for c in controls if c["detected"]),
        "controls_total": len(controls),
        "falsifier": (
            "Any open corpus case uncovered or double-covered, any disposition token outside "
            "the three declared tokens, any AF-* token outside the frozen four, any row whose "
            "axis vector equals a frozen class, or any control mutation not detected."
        ),
        "claims_theorem_status": False,
        "completion_claim": False,
    }


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--created-at", default=None,
                    help="freeze the report created_at (ISO 8601) for byte-reproducible output")
    args = ap.parse_args()

    tax = yaml.safe_load(TAXONOMY.read_text())
    corpus = load_jsonl(CORPUS)
    art = json.loads(ARTIFACT.read_text())

    base_errs, meta = validate(tax, corpus, art)

    controls = []
    mutations = {
        "C1_drop_open_case": lambda a: a["rows"].pop(1),
        "C2_duplicate_case_row": lambda a: a["rows"].append(copy.deepcopy(a["rows"][3])),
        "C3_invalid_disposition": lambda a: a["rows"][0].__setitem__("disposition", "NEW_CLASS_CREATED"),
        "C4_new_class_token": lambda a: a["rows"][0]["bound_parent_class_ids"].append(
            "AF-WCC-SCALAR-SPH-ALT"),
        "C5_missing_falsifier": lambda a: a["rows"][0].__setitem__("falsifier", ""),
        "C6_frozen_class_match": lambda a: a["rows"][0].__setitem__(
            "axis_vector", dict(tax["classes"]["AF-WCC-VAC-GEN"]["axes"])),
        "C7_worker_adjudication_claim": lambda a: a["rows"][0].__setitem__(
            "status", "adjudicated"),
        "C8_missing_requested_scope": lambda a: a["rows"][1].__setitem__("requested_scope", None),
    }
    expected_codes = {
        "C1_drop_open_case": "OPEN_CASE_UNCOVERED",
        "C2_duplicate_case_row": "DUPLICATE_CASE_ROW",
        "C3_invalid_disposition": "INVALID_DISPOSITION",
        "C4_new_class_token": "NEW_CLASS_TOKEN",
        "C5_missing_falsifier": "MISSING_FALSIFIER",
        "C6_frozen_class_match": "FROZEN_CLASS_MATCH",
        "C7_worker_adjudication_claim": "WORKER_ADJUDICATION_CLAIM",
        "C8_missing_requested_scope": "MISSING_REQUESTED_SCOPE",
    }
    for name, mutate in mutations.items():
        mutated = copy.deepcopy(art)
        mutate(mutated)
        errs, _ = validate(tax, corpus, mutated)
        detected = any(e.startswith(expected_codes[name]) for e in errs)
        controls.append({
            "control_id": name,
            "expected_error": expected_codes[name],
            "detected": detected,
            "n_errors": len(errs),
            "sample": [e for e in errs if e.startswith(expected_codes[name])][:2],
        })

    all_controls_pass = all(c["detected"] for c in controls)
    created_at = args.created_at or datetime.now(CST).isoformat(timespec="seconds")
    report = build_report(tax, corpus, art, created_at, base_errs, meta, controls)
    verdict = report["verdict"]
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: report[k] for k in
                      ("verdict", "errors", "controls_detected", "controls_total")}, indent=2))
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
