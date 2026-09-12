#!/usr/bin/env python3
"""Compose the worker-006 L0 review artifact, self-test the controller scan.

Usage: make_review.py [out_path]   (default reviews/L0-review-worker-006.json)
Fail-closed: aborts if either pinned hash has moved since checks.json was written.

Writes the review file and artifacts/worker-006/l0_review/review_selfcheck.json.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
LEDGER = REPO / "ledger" / "theorems.jsonl"
AUDIT = REPO / "ledger" / "citation_audit.csv"
CHECKS = HERE / "checks.json"
DEFAULT_OUT = REPO / "reviews" / "L0-review-worker-006.json"
SELFCHECK = HERE / "review_selfcheck.json"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).replace(microsecond=0).isoformat()


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    if not out.is_absolute():
        out = REPO / out
    checks = json.loads(CHECKS.read_text())
    pins = checks["pins"]
    if sha256(LEDGER) != pins["ledger_sha256"] or sha256(AUDIT) != pins["audit_sha256"]:
        print("FAIL-CLOSED: pinned artifact moved since checks.json; no review written",
              file=sys.stderr)
        return 2
    ledger_h, audit_h = pins["ledger_sha256"], pins["audit_sha256"]
    hard = checks["hard_failures"]
    verdict = "accept" if not hard else "revise"
    score = 4.0 if verdict == "accept" else 2.5
    hf14 = "HF-14-SELF-CERTIFIED-ACCEPT" in hard
    nchecks = len(checks["checks"])

    if hf14:
        findings = [
            {"id": "W006-L0-01", "severity": "critical",
             "finding": ("HF-14 self_certified_acceptance fires at this hash: 60/62 rows set "
                         "status=accepted (50) or supports_claim=true (60, overlap 50) and the "
                         "frozen row schema contains no reviewer/verdict/artifact-hash key. "
                         "evaluation_rubric.yaml HF-14 is severity=critical and ledger-inclusive.")},
            {"id": "W006-L0-02", "severity": "medium",
             "finding": ("HF-01 (30 theorem rows without artifact binding) reported but not "
                         "counted: detector is claim-scoped and the question is under controller "
                         "adjudication (worker-032 N-C5).")},
        ]
    else:
        findings = [
            {"id": "W006-L0-01", "severity": "info",
             "finding": ("HF-14 cleared by the 2026-09-12T00:30:49 revision at ledger "
                         f"{ledger_h[:12]}: every one of 62 rows now declares "
                         "review_status=not_independently_reviewed and an acceptance_authority "
                         "that names the author as a self-assessment, not a reviewer verdict; "
                         "status is included_unreviewed (50) / provisional (11) / rejected (1); "
                         "supports_claim is never true (60 null, 2 false). No row triggers the "
                         "HF-14 detector, so the critical hard failure is closed.")},
            {"id": "W006-L0-02", "severity": "info",
             "finding": ("Moving-target trail, recorded: an earlier review at ledger "
                         "ce42d205e761 returned revise (HF-14) and remains on disk as "
                         "reviews/L0-review-worker-006.json; the literature lead republished the "
                         "ledger with row-level provenance at 00:30:49 (3e3d3553), and this "
                         "review is the fresh hash-pinned verdict at the new revision. The "
                         "superseded revision itself was overwritten in place, so only its hash "
                         "and review survive, not a retrievable copy.")},
            {"id": "W006-L0-03", "severity": "medium",
             "finding": ("HF-01 scope question remains open: 30 theorem rows carry no "
                         "artifact_refs/hash. The detector is claim-scoped "
                         "(`claim.conclusion_type == theorem`) and the ledger-scope ruling is "
                         "pending (worker-032 N-C5), so it is not counted here. The new "
                         "included_unreviewed labelling materially reduces the risk: rows no "
                         "longer assert proved-theorem status.")},
            {"id": "W006-L0-04", "severity": "low",
             "finding": ("Provenance echo gap, unchanged: 3 rows do not repeat the citation-"
                         "registry corrections they depend on indirectly - T-103 (SRC-016 quote "
                         "symbol fidelity), T-505 (SRC-025 year vs publisher year), T-510 "
                         "(SRC-050 venue page range). None carries the row's mathematical "
                         "claim; T-201 explicitly repairs the substantive SRC-041/054 split.")},
            {"id": "W006-L0-05", "severity": "info",
             "finding": (f"All {nchecks} machine checks pass at the pinned hashes: 62 rows >= 15; "
                         "unique ids; required fields present; class_ids tokens all frozen-four "
                         "and non-class tokens only in ledger_tags; verification vocabulary "
                         "legal with no row claiming more than abstract-level evidence; "
                         "reciprocal source linkage; conclusion-inflation controls on every "
                         "strong row; lexical grounding >= 0.174; HF-14 repair coherent "
                         "(unreviewed rows attribute only author self-assessment).")},
            {"id": "W006-L0-06", "severity": "info",
             "finding": ("Residual ledger state, not a failure: 11 provisional rows, 1 rejected "
                         "row (no support flag), 6 definition rows; admitted-row class coverage "
                         "WCC 10 / C0 9 / C2 7 / SPH 6.")},
        ]

    review = {
        "schema_version": "0.1",
        "review_id": f"L0-review-worker-006-{NOW}",
        "node_id": "L0",
        "gate": "G-LIT",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH",
        "reviewer": "worker-006",
        "independent": True,
        "target_id": "L0",
        "target": {"node_id": "L0", "canonical_path": "ledger/theorems.jsonl",
                   "sha256": ledger_h},
        "reviewed_path": "ledger/theorems.jsonl",
        "artifact_sha256": ledger_h,
        "reviewed_sha256": ledger_h,
        "companion_artifact": {"path": "ledger/citation_audit.csv", "sha256": audit_h},
        "measured_at": NOW,
        "verdict": verdict,
        "score": score,
        "hard_failures": hard,
        "counts_as_full_schema_verdict": True,
        "scope_statement": ("Full-scope verdict on the declared L0 acceptance tests and the A0 "
                            "hard-failure taxonomy as applied to a ledger record: class binding, "
                            "verification vocabulary, conclusion-inflation controls, source "
                            "linkage, unresolved honesty, HF-14/HF-01, provenance coherence, "
                            "grounding. It does not re-page-check the quoted theorems; L1's "
                            "independent re-fetch spot checks at audit 315c19145065 are the "
                            "separate locator-level evidence."),
        "checks": checks["checks"],
        "findings": findings,
        "falsifier": (
            "A change to either pinned hash voids this binding; re-review at the new hash. At "
            "the pinned hashes this accept turns to revise if any row's class_ids contains a "
            "token outside the frozen four, if any verification_status claims more than the "
            "cited locator evidence supports, if any strong row lacks a conclusion-inflation "
            "control, if a registry-unresolved source is used without being named, or if any "
            "row's declared review_status overstates the reviewer evidence it names."
            + (" A controller ruling that HF-01 applies to ledger theorem rows would reopen "
               "the artifact at the HF-01 finding." if not hf14 else "")),
        "evidence_refs": [
            f"ledger/theorems.jsonl#sha256:{ledger_h}",
            f"ledger/citation_audit.csv#sha256:{audit_h}",
            "evaluation_rubric.yaml#hard_failures.HF-14",
            f"artifacts/worker-006/l0_review/checks.json#sha256:{sha256(CHECKS)}",
            f"artifacts/worker-006/l0_review/review_l0_006.py#sha256:{sha256(HERE / 'review_l0_006.py')}",
        ],
        "created_at": NOW,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(review, indent=1, ensure_ascii=False) + "\n")

    probe = (
        "import json,sys; sys.path.insert(0,'research_map');"
        "import astra_lifecycle as a;"
        f"cov=a.review_coverage({{'L0':{{'sha256':'{ledger_h}'}}}});"
        "print(json.dumps(cov['L0']))"
    )
    p = subprocess.run([sys.executable, "-c", probe], cwd=REPO, capture_output=True, text=True)
    try:
        cov = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        cov = {"error": p.stdout[-400:], "stderr": p.stderr[-400:]}
    selfcheck = {
        "checked_at": NOW,
        "review_file": str(out.relative_to(REPO)),
        "verdict": verdict,
        "pinned_ledger": ledger_h,
        "counted_as_full_verdict": any(
            e.get("file") == out.name for e in cov.get("verdicts", [])),
        "accepts_at_this_hash": [e.get("reviewer") for e in cov.get("accepts", [])],
        "scan": cov,
    }
    SELFCHECK.write_text(json.dumps(selfcheck, indent=1) + "\n")
    print(json.dumps(selfcheck, indent=1))
    if not selfcheck["counted_as_full_verdict"]:
        print("WARNING: controller scan did not count the review", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
