#!/usr/bin/env python3
"""Build the deterministic fixture pin manifest + pin-coverage / transitive-binding audit.

W069-F2B-FIXTURE-PIN-COVERAGE-01. Read-only; writes only fixture_pin_manifest.json here.

Emits:
  files{name -> sha256}, roles, listing_digest_sha256
  frozen_coverage : which of the files FROZEN.files pins (expect 0) and what FROZEN does pin
  transitive_binding : the corpus record's recorded hashes and whether each referenced
                       artifact is itself covered by FROZEN.files
  reader_contract : how run_acceptance.py consumes the directory (glob + preflight)
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CORPUS = ROOT / "artifacts/formulation/evidence/rebased_fixtures"
FROZEN = ROOT / "artifacts/formulation/FROZEN.json"
CORPUS_RECORD = ROOT / "artifacts/formulation/evidence/semantic_escape_rebased.json"
RUN_ACCEPT = ROOT / "artifacts/formulation/tools/run_acceptance.py"
BASE = ROOT / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
FIXTURE_PREFIX = "artifacts/formulation/evidence/rebased_fixtures/"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_checker():
    spec = importlib.util.spec_from_file_location("w069_checker", HERE / "check_fixture_binding.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    chk = load_checker()
    out_path = HERE / "fixture_pin_manifest.json"
    man = chk.build(CORPUS, out_path)
    frozen = json.loads(FROZEN.read_text())
    ffiles = frozen["files"]
    covered = sorted(p for p in ffiles if p.startswith(FIXTURE_PREFIX))
    rec = json.loads(CORPUS_RECORD.read_text())
    refs = {
        "corpus_manifest": rec.get("corpus_manifest"),
        "gate": rec.get("gate"),
        "w06_auditor": rec.get("w06_auditor"),
        "base_schema": rec.get("base_schema"),
        "corpus_record_self": str(CORPUS_RECORD.relative_to(ROOT)),
        "generator": "artifacts/formulation/tools/measure_semantic_escape.py",
    }
    recorded = {
        "corpus_manifest": rec.get("corpus_manifest_sha256"),
        "gate": rec.get("gate_sha256"),
        "w06_auditor": rec.get("w06_sha256"),
        "base_schema": rec.get("base_sha256"),
        "corpus_record_self": sha256_file(CORPUS_RECORD),
        "generator": sha256_file(ROOT / "artifacts/formulation/tools/measure_semantic_escape.py"),
    }
    binding = {}
    for k, rel in refs.items():
        live = None
        p = ROOT / rel
        if p.exists():
            live = sha256_file(p)
        else:
            # corpus record paths may not exist on disk anymore (e.g. base schema moved)
            pass
        binding[k] = {
            "path": rel,
            "recorded_in_corpus_record": recorded[k],
            "live_sha256": live,
            "recorded_matches_live": (recorded[k] == live) if live else None,
            "in_frozen_files": rel in ffiles,
        }
    man["frozen_coverage"] = {
        "frozen_artifact": "artifacts/formulation/FROZEN.json",
        "frozen_sha256": sha256_file(FROZEN),
        "frozen_revision": frozen.get("revision"),
        "n_fixture_files": man["n_files"],
        "n_covered_by_frozen": len(covered),
        "covered": covered,
        "pinned_evidence_entries": sorted(p for p in ffiles if p.startswith("artifacts/formulation/evidence/")),
    }
    man["transitive_binding"] = binding
    man["reader_contract"] = {
        "reader": "artifacts/formulation/tools/run_acceptance.py",
        "reader_sha256": sha256_file(RUN_ACCEPT),
        "enumeration": 'REBASED.glob("*.yaml") at run time (script lines 78-105); contents are not compared to any pin',
        "preflight": "only semantic_escape_rebased.json.base_sha256 vs live canonical C0 (script lines 55-67); no fixture-byte check",
        "canonical_base_live_sha256": sha256_file(BASE),
        "corpus_recorded_base_sha256": rec.get("base_sha256"),
        "corpus_binding_verdict": ("STALE" if rec.get("base_sha256") != sha256_file(BASE) else "CURRENT"),
    }
    man["exposure_summary"] = (
        "The corpus record pins fixture NAMES and generation-time verdicts, not fixture BYTES; "
        "run_acceptance.py re-reads the directory by glob, so at fixed pinned inputs a deleted "
        "mutant weakens the effective corpus while the corpus-level verdict remains PASS "
        "(measured in probe_results.json).")
    out_path.write_text(json.dumps(man, indent=2) + "\n")
    print(json.dumps({"n_files": man["n_files"], "listing_digest_sha256": man["listing_digest_sha256"],
                      "frozen_revision": frozen.get("revision"),
                      "n_covered_by_frozen": len(covered),
                      "corpus_binding_verdict": man["reader_contract"]["corpus_binding_verdict"]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
