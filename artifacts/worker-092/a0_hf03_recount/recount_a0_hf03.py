#!/usr/bin/env python3
"""W092-A0-HF03-STAGING-RECOUNT-01.

Independent, read-only recount of the A0 HF-03 (unsupported_citation) record counts at
evaluation/A0_detector_scope_adjudication.json#a26be4b85706, with the specific purpose of
adjudicating the contradiction between

  * audit-l06-b3-staging-20260912T005926 (audit lead): "Two un-ingested staging
    contributions carry 12 HF-14 records and 1 HF-03 record", and
  * the adjudication artifact's own record: staging_unresolved = 7 records on
    artifacts/worker-07/ledger_contribution/batches/batch-w07-sources.jsonl.

This script imports NO author code (no audit_lib, no audit_run, no detector).  The two
predicates are re-implemented from their public text:

  implementation reading (what the canonical scan actually does):
      a record is a citation iff it has (resolution_status or status) and (cite_key or
      source_id); it fires HF-03 iff source_meta lacks any of
      matter_model/cosmological_constant/dimension/symmetry, or neither source_meta.formulation
      nor record.formulation is truthy.

  rubric-literal reading (evaluation_rubric.yaml hard_failures[2]):
      "claim cites a citation whose resolution_status in {unresolved, contradicted} or whose
      class metadata mismatches the claim's class" -> we measure the resolution_status
      disjunct directly on the same citation rows, and the class-mismatch disjunct as
      resolution_status normalisation class vs record class_id.

Outputs report.json next to this file.  Writes nothing outside artifacts/worker-092/.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # artifacts/worker-092/a0_hf03_recount -> repo root
ARTIFACT = ROOT / "evaluation/A0_detector_scope_adjudication.json"
RUBRIC = ROOT / "evaluation_rubric.yaml"
AUDIT_OUTBOX = ROOT / "comms/outbox/astra-lead-audit.jsonl"
B3_EVENT_ID = "audit-l06-b3-staging-20260912T005926"

CST = timezone(timedelta(hours=8))
SCOPE_KEYS = ("matter_model", "cosmological_constant", "dimension", "symmetry")
FIXTURE_TOKENS = ("/fixtures/", "/corpus/", "/selftest/", "repaired_inputs")
NORMALIZE = {
    "verified_primary": "verified_primary",
    "verified_api": "verified_secondary",
    "verified_secondary": "verified_secondary",
    "partial": "partial",
    "unresolved": "unresolved",
    "contradicted": "contradicted",
}


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def sha256_text(t: str) -> str:
    return hashlib.sha256(t.encode()).hexdigest()


def iter_objects(p: Path):
    """.jsonl one object per line (lines starting with '{'); .json list or dict."""
    if not p.is_file():
        return
    text = p.read_text(errors="replace")
    if p.suffix == ".jsonl":
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    yield json.loads(line)
                except ValueError:
                    pass
    elif p.suffix == ".json":
        try:
            obj = json.loads(text)
        except ValueError:
            return
        if isinstance(obj, list):
            yield from (o for o in obj if isinstance(o, dict))
        elif isinstance(obj, dict):
            yield obj


def is_fixture(rel: str) -> bool:
    return any(t in rel for t in FIXTURE_TOKENS) or rel.endswith(
        ("EXPECTATIONS.json", "manifest.json"))


def is_citation(rec: dict, rel: str) -> bool:
    if is_fixture(rel):
        return False
    status = rec.get("resolution_status") or rec.get("status")
    return bool(status) and ("cite_key" in rec or "source_id" in rec)


def normalize_status(s: str) -> str:
    return NORMALIZE.get(s.strip().lower().replace("-", "_").replace(" ", "_"), "unresolved")


def hf03_implementation(rec: dict) -> list[str]:
    """Return the missing scope keys under the canonical implementation predicate."""
    meta = rec.get("source_meta") or {}
    if not isinstance(meta, dict):
        meta = {}
    missing = [k for k in SCOPE_KEYS if k not in meta]
    if not meta.get("formulation") and not rec.get("formulation"):
        missing.append("formulation")
    return missing


def hf03_literal_rubric(rec: dict) -> dict:
    """The rubric-literal HF-03 branch measured on one citation row."""
    status = rec.get("resolution_status")
    if status is None and "status" in rec:
        status = normalize_status(str(rec["status"]))
    unresolved_or_contradicted = status in ("unresolved", "contradicted")
    # class-mismatch disjunct: the row's own class metadata vs a claim class carried on the
    # same row (a row with no class token cannot mismatch; recorded as not firing).
    row_classes = rec.get("class_ids") or ([rec["class_id"]] if rec.get("class_id") else [])
    claim_class = rec.get("claim_class_id") or rec.get("claim_class")
    mismatch = bool(claim_class and row_classes and claim_class not in row_classes)
    return {
        "resolution_status": status,
        "fires_resolution_status": bool(unresolved_or_contradicted),
        "fires_class_mismatch": mismatch,
        "fires": bool(unresolved_or_contradicted or mismatch),
    }


def hf14_self_cert(rec: dict) -> bool:
    accepted = (str(rec.get("status", "")).lower() in ("accepted", "passed")
                or rec.get("supports_claim") is True
                or str(rec.get("validation_status", "")).lower() == "passed")
    has_review = bool(rec.get("reviewer_verdicts") or rec.get("review_verdict")
                      or rec.get("reviewed_by"))
    return bool(accepted and not has_review)


def collect(rel: str) -> dict:
    p = ROOT / rel
    cit, recs, hf03_impl, hf03_lit, hf14 = 0, 0, [], [], []
    for obj in iter_objects(p):
        recs += 1
        if is_citation(obj, rel):
            cit += 1
            miss = hf03_implementation(obj)
            if miss:
                hf03_impl.append((obj.get("cite_key") or obj.get("source_id")
                                  or obj.get("title"), miss))
            lit = hf03_literal_rubric(obj)
            if lit["fires"]:
                hf03_lit.append(lit)
        if hf14_self_cert(obj):
            hf14.append(obj.get("theorem_id") or obj.get("claim_id") or obj.get("event_id"))
    return {"path": rel, "exists": p.is_file(),
            "sha256": sha256_file(p) if p.is_file() else None,
            "objects": recs, "citations": cit,
            "hf03_implementation": len(hf03_impl),
            "hf03_literal_rubric": len(hf03_lit),
            "hf14": len(hf14),
            "hf03_first_examples": [list(x) for x in hf03_impl[:3]],
            "hf03_literal_first": hf03_lit[:3]}


def classify(rel: str) -> str:
    if rel in ("ledger/theorems.jsonl", "ledger/citation_audit.csv"):
        return "canonical"
    if rel.startswith(("artifacts/literature/sources/", "artifacts/literature/theorems/",
                       "artifacts/literature/tools/")):
        return "live_build_input"
    if rel in ("artifacts/literature/registry.jsonl", "artifacts/literature/unresolved.jsonl",
               "artifacts/literature/MANIFEST.json", "artifacts/literature/falsifiers.md",
               "artifacts/literature/tag_index.md"):
        return "live_emitted"
    base = rel.rsplit("/", 1)[-1]
    if any(seg in "/" + rel for seg in ("/archive/", "/incoming/")) or \
       any(tok in base for tok in (".pre-", ".prev-", "_snapshot.", ".snapshot-", ".bak")):
        return "historical"
    if any(seg in "/" + rel for seg in ("/snapshot/", "/snapshots/", "/probe/", "/proposed/",
                                        "/staging/", "/scratch/", "/prev/")) or \
       "snapshot" in base:
        return "snapshot_copy"
    if "/ledger_contribution/" in "/" + rel or rel.startswith("artifacts/worker-07/ledger"):
        return "staging_unresolved"
    return "live_other"


def main() -> int:
    art = json.loads(ARTIFACT.read_text())
    declared = art["measured"]["hf03"]
    declared_before = art["measured"]["_hf03_before"]
    pins = art["measured"]["file_pins"]

    out = {
        "task_id": "W092-A0-HF03-STAGING-RECOUNT-01",
        "actor": "worker-092",
        "node_id": "A0",
        "class_id": "GLOBAL",
        "gate": "G-AUDIT",
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "method": "independent stdlib re-implementation; no author code imported",
        "inputs": {
            "adjudication_artifact": {"path": "evaluation/A0_detector_scope_adjudication.json",
                                      "sha256": sha256_file(ARTIFACT)},
            "rubric": {"path": "evaluation_rubric.yaml", "sha256": sha256_file(RUBRIC)},
            "b3_event_id": B3_EVENT_ID,
        },
        "declared": {
            "before_total_records": declared["before_total_records"],
            "after_total_records": declared["after_total_records"],
            "kept": declared["kept"],
            "excluded": declared["excluded"],
            "staging_unresolved": declared["staging_unresolved"],
            "before_files": declared_before,
        },
    }

    # (1) reproduce every per-file HF-03 count in the declared before-map
    measured_files = {}
    for rel, declared_n in sorted(declared_before.items()):
        m = collect(rel)
        m["declared_hf03"] = declared_n
        m["match_declared"] = (m["hf03_implementation"] == declared_n)
        measured_files[rel] = m

    totals = {
        "before_files": len(measured_files),
        "before_records_impl": sum(v["hf03_implementation"] for v in measured_files.values()),
        "staging_records_impl": sum(v["hf03_implementation"]
                                    for k, v in measured_files.items()
                                    if classify(k) == "staging_unresolved"),
        "kept_records_impl": sum(v["hf03_implementation"]
                                 for k, v in measured_files.items()
                                 if classify(k) not in ("historical", "snapshot_copy",
                                                        "staging_unresolved")),
        "excluded_records_impl": sum(v["hf03_implementation"]
                                     for k, v in measured_files.items()
                                     if classify(k) in ("historical", "snapshot_copy")),
        "kept_records_literal_rubric": sum(v["hf03_literal_rubric"]
                                           for k, v in measured_files.items()
                                           if classify(k) not in ("historical", "snapshot_copy",
                                                                  "staging_unresolved")),
        "all_files_match_declared": all(v["match_declared"] for v in measured_files.values()),
        "all_pins_match_live": all(
            pins[rel]["sha256"] == measured_files[rel]["sha256"]
            for rel in measured_files if rel in pins),
    }
    totals["reconciles_194_17_7_218"] = (
        totals["kept_records_impl"] == declared["after_total_records"] == 194
        and totals["excluded_records_impl"] == 17
        and totals["staging_records_impl"] == 7
        and totals["before_records_impl"] == declared["before_total_records"] == 218)
    out["measured"] = {"totals": totals, "per_file": measured_files}

    # (2) the b3 claim, quoted from the audit outbox at the event id
    b3 = None
    for line in AUDIT_OUTBOX.read_text(errors="replace").splitlines():
        line = line.strip()
        if line.startswith("{") and B3_EVENT_ID in line:
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if e.get("event_id") == B3_EVENT_ID:
                b3 = {"event_id": e.get("event_id"), "created_at": e.get("created_at"),
                      "description": e.get("description")}
                break
    staging_file = ("artifacts/worker-07/ledger_contribution/batches/"
                    "batch-w07-sources.jsonl")
    staging_theorems = ("artifacts/worker-07/ledger_contribution/batches/"
                        "batch-w07-theorems.jsonl")
    staging_theorems_measured = collect(staging_theorems)
    out["b3_adjudication"] = {
        "b3_event": b3,
        "b3_says_hf03_records": 1 if (b3 and re.search(r"\b1 HF-03 record", b3["description"] or "")) else None,
        "artifact_says_staging_records": declared["staging_unresolved"].get(
            staging_file, {}).get("records"),
        "independent_staging_hf03": measured_files[staging_file]["hf03_implementation"],
        "independent_staging_hf14_theorems": staging_theorems_measured["hf14"],
        "verdict": ("b3_text_defect_confirmed_7_not_1"
                    if (b3 and re.search(r"\b1 HF-03 record", b3["description"] or "")
                        and measured_files[staging_file]["hf03_implementation"] == 7
                        and declared["staging_unresolved"].get(staging_file, {})
                            .get("records") == 7)
                    else "not_confirmed"),
    }
    out["headline"] = {
        "staging_hf03_records": measured_files[staging_file]["hf03_implementation"],
        "kept_live_hf03_implementation": totals["kept_records_impl"],
        "kept_live_hf03_literal_rubric": totals["kept_records_literal_rubric"],
        "per_file_reproduction": totals["all_files_match_declared"],
        "pin_stability": totals["all_pins_match_live"],
    }
    report = HERE / "report.json"
    text = json.dumps(out, indent=1, sort_keys=True, default=str)
    report.write_text(text + "\n")
    print(json.dumps(out["headline"], indent=1))
    print("report:", report, "sha256:", sha256_file(report))
    return 0 if (totals["all_files_match_declared"] and totals["all_pins_match_live"]) else 1


if __name__ == "__main__":
    sys.exit(main())
