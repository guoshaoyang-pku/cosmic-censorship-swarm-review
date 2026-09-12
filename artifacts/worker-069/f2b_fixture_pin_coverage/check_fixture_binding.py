#!/usr/bin/env python3
"""Fail-closed binding checker for the generated acceptance fixture directory.

Why this exists (W069-F2B-FIXTURE-PIN-COVERAGE-01):
  artifacts/formulation/tools/run_acceptance.py re-reads
  artifacts/formulation/evidence/rebased_fixtures/*.yaml by glob at run time, so the
  acceptance verdict depends on the directory CONTENTS, while the pinned corpus record
  (artifacts/formulation/evidence/semantic_escape_rebased.json) records only fixture
  names, mutation specs and generation-time verdicts. This checker binds the bytes.

Contract:
  * exit 0 only when the directory exactly matches the manifest: same name set, same
    sha256 per file, manifest listing digest self-consistent;
  * every failure mode (missing / extra / modified / digest mismatch / stale corpus base)
    is reported in JSON and exits non-zero (fail closed);
  * runs read-only: it never writes to the directory or to the manifest.

Usage:
  python3 check_fixture_binding.py --build --dir <D> --out <M>
  python3 check_fixture_binding.py --verify --dir <D> --manifest <M> [--json]
  python3 check_fixture_binding.py --verify --dir <D> --manifest <M> \
      --corpus-record <R> --canonical-base <B> [--json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

SCHEMA_VERSION = "w069.fixture_binding.v1"
GLOB = "*.yaml"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def listing_digest(files: dict[str, str]) -> str:
    """Deterministic digest over the sorted name -> sha256 map (no file contents)."""
    canon = json.dumps({k: files[k] for k in sorted(files)}, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canon.encode()).hexdigest()


def role_of(name: str) -> str:
    return "control" if name.startswith("control_") else "mutant"


def build(d: Path, out: Path) -> dict:
    names = sorted(p.name for p in d.glob(GLOB))
    files = {n: sha256_file(d / n) for n in names}
    man = {
        "schema_version": SCHEMA_VERSION,
        "artifact": "artifacts/worker-069/f2b_fixture_pin_coverage/fixture_pin_manifest.json",
        "fixture_dir": str(d),
        "glob": GLOB,
        "n_files": len(files),
        "roles": {n: role_of(n) for n in names},
        "files": files,
        "listing_digest_sha256": listing_digest(files),
    }
    out.write_text(json.dumps(man, indent=2) + "\n")
    return man


def verify(d: Path, manifest: dict, corpus_record: Path | None, canonical_base: Path | None) -> dict:
    res: dict = {"schema_version": SCHEMA_VERSION, "dir": str(d), "ok": False,
                 "missing": [], "extra": [], "modified": [], "digest_ok": None,
                 "corpus_record": None, "canonical_base_sha256": None, "reasons": []}
    if manifest.get("schema_version") != SCHEMA_VERSION:
        res["reasons"].append(f"manifest schema_version {manifest.get('schema_version')!r} != {SCHEMA_VERSION!r}")
        return res
    declared: dict[str, str] = manifest.get("files", {})
    if listing_digest(declared) != manifest.get("listing_digest_sha256"):
        res["digest_ok"] = False
        res["reasons"].append("manifest listing digest does not match its own files map")
    else:
        res["digest_ok"] = True
    on_disk = sorted(p.name for p in d.glob(manifest.get("glob", GLOB)))
    res["missing"] = sorted(set(declared) - set(on_disk))
    res["extra"] = sorted(set(on_disk) - set(declared))
    for n in sorted(set(declared) & set(on_disk)):
        if sha256_file(d / n) != declared[n]:
            res["modified"].append(n)
    if res["missing"]:
        res["reasons"].append(f"missing {len(res['missing'])} declared fixture(s): {res['missing'][:5]}")
    if res["extra"]:
        res["reasons"].append(f"{len(res['extra'])} undeclared fixture(s) present: {res['extra'][:5]}")
    if res["modified"]:
        res["reasons"].append(f"{len(res['modified'])} modified fixture(s): {res['modified'][:5]}")
    if corpus_record is not None and canonical_base is not None:
        rec = json.loads(Path(corpus_record).read_text())
        live = sha256_file(Path(canonical_base))
        res["corpus_record"] = str(corpus_record)
        res["corpus_recorded_base_sha256"] = rec.get("base_sha256")
        res["canonical_base_sha256"] = live
        if rec.get("base_sha256") != live:
            res["reasons"].append(
                f"stale corpus: record base {str(rec.get('base_sha256'))[:12]} != live canonical base {live[:12]}")
    res["ok"] = not res["reasons"]
    res["verdict"] = "PASS" if res["ok"] else "FAIL"
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--dir", required=True)
    ap.add_argument("--out")
    ap.add_argument("--manifest")
    ap.add_argument("--corpus-record")
    ap.add_argument("--canonical-base")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    d = Path(a.dir)
    if a.build:
        if not a.out:
            print("--build requires --out", file=sys.stderr)
            return 2
        man = build(d, Path(a.out))
        print(json.dumps({"built": man["n_files"], "listing_digest_sha256": man["listing_digest_sha256"]}, indent=2))
        return 0
    if not a.manifest:
        print("--verify requires --manifest", file=sys.stderr)
        return 2
    res = verify(d, json.loads(Path(a.manifest).read_text()),
                 Path(a.corpus_record) if a.corpus_record else None,
                 Path(a.canonical_base) if a.canonical_base else None)
    if a.json:
        print(json.dumps(res, indent=2))
    else:
        print(f"FIXTURE-BINDING: {res['verdict']}")
        for r in res["reasons"]:
            print(f"  - {r}")
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
