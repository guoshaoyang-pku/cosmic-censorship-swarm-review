#!/usr/bin/env python3
"""Emit the worker-031 L1 spot-check artifact + hash sidecars from comparison.json.

Reproduce:
    python3 artifacts/worker-031/l1_spotcheck/run_spotcheck_031.py
    python3 artifacts/worker-031/l1_spotcheck/emit_artifact_031.py
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> dict:
    cmp = json.loads((HERE / "comparison.json").read_text())
    checks = cmp["checks"]
    evidence_files = {}
    for p in sorted(HERE.rglob("*")):
        if p.is_file() and p.suffix not in (".pyc",):
            evidence_files[str(p.relative_to(HERE))] = sha256_file(p)

    artifact = {
        "schema_version": "0.1",
        "artifact_type": "l1_refetch_spotcheck",
        "artifact_id": "artifacts/worker-031/l1_spotcheck/spotcheck-l1-031.json",
        "node_id": "L1",
        "gate": "G-LIT",
        "class_ids": ["AF-WCC-SCALAR-SPH", "AF-SCC-C0-VAC-GEN", "AF-WCC-VAC-GEN"],
        "actor": "worker-031",
        "reviewer": "worker-031",
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "assignment_ref": "astra-life02-l1-spotcheck",
        "check_number": 5,
        "authority": ("worker evidence only; no gate verdict, no node status, no theorem claim. "
                      "The literature lead owns the ledger; this file does not edit it."),
        "independence": {
            "independent_of": [
                "artifacts/worker-07/l1_spotcheck/spotcheck-l1-07.json",
                "artifacts/worker-086/l1_spotcheck/spotcheck-l1-086.json",
                "reviews/L1-spotcheck-10.json",
                "reviews/L1-spotcheck-11.json",
                "artifacts/literature/reviews/L1-spotcheck-rev2.json",
            ],
            "identity_note": ("worker-031 is distinct from deepseek-flash-07 and worker-086; no ledger text was "
                              "used as evidence, only the frozen ledger rows as the claim under test."),
            "sampling_rule_frozen_before_fetch": True,
            "sampling_rule": ("rows 91 and 94 chosen from the rows not covered by flash-07's pre-declared "
                              "every-8th sample of frame 41-95 (41,49,57,65,73,80,81,89) and outside "
                              "worker-086's frame 1-40; both carry frozen-class mappings and resolvable primary locators."),
        },
        "inputs": {
            "ledger/citation_audit.csv": {
                "sha256_pinned": cmp["pinned_inputs"]["ledger/citation_audit.csv"],
                "sha256_before_fetch": cmp["inputs_before_fetch"]["ledger/citation_audit.csv"],
                "sha256_after_fetch": cmp["inputs_after_fetch"]["ledger/citation_audit.csv"],
                "data_rows": 97,
                "stable_during_check": cmp["inputs_before_fetch"] == cmp["inputs_after_fetch"] == cmp["pinned_inputs"],
            },
            "ledger/theorems.jsonl": {
                "sha256_pinned": cmp["pinned_inputs"]["ledger/theorems.jsonl"],
                "sha256_before_fetch": cmp["inputs_before_fetch"]["ledger/theorems.jsonl"],
                "sha256_after_fetch": cmp["inputs_after_fetch"]["ledger/theorems.jsonl"],
                "stable_during_check": cmp["inputs_before_fetch"] == cmp["inputs_after_fetch"] == cmp["pinned_inputs"],
            },
        },
        "checks": checks,
        "controls": cmp["controls"],
        "controls_pass": cmp["controls_pass"],
        "findings": [
            {
                "finding_id": "W031-F1",
                "severity": "locator-quality (not a content mismatch)",
                "citation_id": "SRC-091",
                "detail": ("exact_locator is 'https://export.arxiv.org/api/query?search_query=au:Hintz&sortBy=submittedDate', "
                           "an arXiv API search query rather than an exact locator. The row's url/evidence_url "
                           "https://arxiv.org/abs/2606.28008 resolves HTTP 200 and its content matches the row. "
                           "Same finding class as worker-086's SRC-009/SRC-016/SRC-017/SRC-033 findings; remedy is to "
                           "replace exact_locator with the abs URL."),
                "evidence_refs": ["artifacts/worker-031/l1_spotcheck/fetch/src-091.abs.html"],
            },
            {
                "finding_id": "W031-F2",
                "severity": "transcription artifact (not a content mismatch)",
                "citation_id": "SRC-091",
                "detail": ("the evidence_excerpt appends ' 285 pages.' after the closing quote of the abstract; that text is "
                           "not part of the abstract on the fetched locator. All three quoted fragments match the live "
                           "abstract once the closing-quote tail is excluded; recorded so the checker's trimming rule is visible."),
                "evidence_refs": ["artifacts/worker-031/l1_spotcheck/comparison.json"],
            },
            {
                "finding_id": "W031-F3",
                "severity": "corroboration",
                "citation_id": "SRC-094",
                "detail": ("Crossref 10.12942/lrr-2007-5 corroborates title, both authors, Living Reviews in Relativity "
                           "vol 10 (2007); 'Living Reviews in Relativity 10:5' is consistent with article 5 of volume 10."),
                "evidence_refs": ["artifacts/worker-031/l1_spotcheck/fetch/crossref_lrr.json"],
            },
        ],
        "hard_failures": [],
        "summary": {
            "targets": len(checks),
            "verdicts": {v: sum(1 for c in checks if c["verdict"] == v) for v in ("MATCH", "PARTIAL", "FAIL")},
            "class_coverage": sorted({c["class_mapping"] for c in checks}),
            "fetched_http_200": sum(1 for c in checks if c["fetch"]["http_status"] == 200),
            "contradictions_found": 0,
            "ledger_stable_during_check": cmp["ledger_stable_during_check"],
            "controls_pass": cmp["controls_pass"],
        },
        "falsifier": ("Re-fetching https://arxiv.org/abs/0711.4620 or https://arxiv.org/abs/2606.28008 and finding "
                      "the quoted fragments, title, authors, arXiv id or date absent/different falsifies this check. "
                      "A ledger revision in which rows 91/94 no longer carry these class mappings, or a "
                      "ledger/citation_audit.csv sha256 other than 315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9, "
                      "voids the binding of this spot check."),
        "stop_rule": "Two targets checked; no further fetches. Do not edit ledger files (literature lead owns them).",
        "gate_verdict_claimed": False,
        "node_status_claimed": False,
        "completion_claim": False,
        "method": ("curl -L --max-time 40 fetched raw bytes of each locator into fetch/; sha256 over the raw bytes; "
                   "metadata read from the fetched page's citation_* meta tags; ledger claims read from the frozen CSV row; "
                   "normalized comparison (lowercase, LaTeX stripped, whitespace collapsed) with quoted-fragment substring "
                   "checks; two negative controls (a different paper must MISMATCH, a non-resolving id must be HTTP 404) "
                   "must pass or the run is INVALID. Full code: run_spotcheck_031.py; raw output: comparison.json."),
        "evidence_files": evidence_files,
    }

    out = HERE / "spotcheck-l1-031.json"
    out.write_text(json.dumps(artifact, indent=2, sort_keys=True))
    digest = sha256_file(out)
    (HERE / "spotcheck-l1-031.json.sha256").write_text(f"{digest}  spotcheck-l1-031.json\n")
    print(json.dumps({"artifact": str(out.relative_to(ROOT)), "sha256": digest,
                      "verdicts": artifact["summary"]["verdicts"],
                      "controls_pass": artifact["controls_pass"]}, indent=2))
    return artifact


if __name__ == "__main__":
    main()
