#!/usr/bin/env python3
"""W043D step 1 - byte-exact reconstruction of the declared consistency evidence.

Every rev12 class schema (F1/F2a/F2b) declares

    f0_binding.consistency_evidence_sha256 = 675a99d0d25b2b37...
    f0_binding.consistency_evidence        = artifacts/formulation/evidence/taxonomy_consistency.json

but the canonical path currently measures 9e335e9ba1bfcf77... (495 B): the lean
document written by artifacts/formulation/tools/check_taxonomy_consistency.py:80.
Worker-086 (reviews/G-FORM-evidence-collision-086.json, F-086-C1) reports that the
lean document plus three insertion-ordered fields reconstructs the declared bytes
exactly.  This script re-derives that reconstruction independently and fails closed
if any input moved.

Usage:
  python3 reconstruct_declared_evidence.py [--root REPO] [--out DIR]

Writes (under the task raw/ dir unless --out overrides):
  reconstruction.json                      - inputs, rule, hash, byte length
  evidence_restored_675a99d0.json          - the reconstructed declared bytes

Read-only on the shared tree; writes only under the task directory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

TASK_DIR = Path(__file__).resolve().parent
DEFAULT_ROOT = TASK_DIR.parents[2]

F0 = "research_map/formulation_taxonomy.yaml"
F0S = "artifacts/formulation/formulation_taxonomy.yaml"
CONS = "artifacts/formulation/evidence/taxonomy_consistency.json"
DECLARED = "675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48"
LEAN = "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b"
DECLARED_AT = "2026-09-12T00:32:02+08:00"
# close_findings_rev27.py:379-381 insertion order, json.dumps(..., indent=2) + "\n"
FIELDS = ("map_taxonomy_sha256", "lead_contract_sha256", "measured_at")
EXPECTED_BYTES = 728


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def reconstruct(lean: dict, f0_sha: str, f0s_sha: str, measured_at: str) -> bytes:
    """Insertion-ordered repair exactly as close_findings_rev27.py builds it."""
    doc = dict(lean)
    doc["map_taxonomy_sha256"] = f0_sha
    doc["lead_contract_sha256"] = f0s_sha
    doc["measured_at"] = measured_at
    return (json.dumps(doc, indent=2) + "\n").encode()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    ap.add_argument("--out", default=str(TASK_DIR / "raw"))
    args = ap.parse_args()
    root = Path(args.root).resolve()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    f0_sha = sha256_file(root / F0)
    f0s_sha = sha256_file(root / F0S)
    lean_bytes = (root / CONS).read_bytes()
    lean_sha = sha256_bytes(lean_bytes)
    lean = json.loads(lean_bytes)

    fixed = reconstruct(lean, f0_sha, f0s_sha, DECLARED_AT)
    fixed_sha = sha256_bytes(fixed)
    alt_at = reconstruct(lean, f0_sha, f0s_sha, "2026-09-12T00:32:03+08:00")
    alt_sha = sha256_bytes(alt_at)
    no_pins = json.dumps(lean, indent=2).encode()
    no_pins_sha = sha256_bytes(no_pins)
    rev = dict(lean)
    rev["measured_at"] = DECLARED_AT
    rev["lead_contract_sha256"] = f0s_sha
    rev["map_taxonomy_sha256"] = f0_sha
    reversed_sha = sha256_bytes((json.dumps(rev, indent=2) + "\n").encode())

    report = {
        "task_id": "W043D-R2-DURABILITY-01",
        "step": "reconstruct_declared_evidence",
        "root": str(root),
        "inputs": {
            F0: {"sha256": f0_sha},
            F0S: {"sha256": f0s_sha},
            CONS: {"sha256": lean_sha, "bytes": len(lean_bytes)},
        },
        "declared_sha256": DECLARED,
        "declared_measured_at": DECLARED_AT,
        "rule": (
            "lean canonical document (9e335e9b) + insertion-ordered "
            "{map_taxonomy_sha256 = measured F0 canonical, lead_contract_sha256 = measured "
            "F0 supplement, measured_at = 2026-09-12T00:32:02+08:00}; "
            "json.dumps(indent=2) + trailing newline"
        ),
        "reconstructed_sha256": fixed_sha,
        "reconstructed_bytes": len(fixed),
        "reconstruction_matches_declared": fixed_sha == DECLARED,
        "byte_length_matches": len(fixed) == EXPECTED_BYTES,
        "canonical_path_still_lean": lean_sha == LEAN,
        "f0_hash_current": f0_sha,
        "f0s_hash_current": f0s_sha,
        "controls": {
            "K1_measured_at_plus_1s_changes_hash": alt_sha != fixed_sha,
            "K2_hashless_document_changes_hash": no_pins_sha != fixed_sha,
            "K3_insertion_order_sensitive": reversed_sha != fixed_sha,
        },
        "non_claims": [
            "measurement only; no canonical file was written",
            "the reconstruction reproduces the declared generation, it does not re-run the "
            "current close_findings_rev27.py producer (worker-086 HF-086-R4 producer drift)",
        ],
    }
    (out / "evidence_restored_675a99d0.json").write_bytes(fixed)
    (out / "reconstruction.json").write_text(json.dumps(report, indent=2) + "\n")

    ok = (
        report["reconstruction_matches_declared"]
        and report["byte_length_matches"]
        and all(report["controls"].values())
    )
    print(json.dumps({k: report[k] for k in (
        "reconstructed_sha256", "reconstructed_bytes",
        "reconstruction_matches_declared", "byte_length_matches",
        "canonical_path_still_lean", "controls")}, indent=1))
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
