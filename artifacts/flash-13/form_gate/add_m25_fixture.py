#!/usr/bin/env python3
"""Add the single new mutant m25_wcc_binder_unused to the FORM-GATE-01 corpus (revision 1.2).

Why not re-run make_fixtures.py wholesale: that generator is not idempotent for the two
conforming SCC positives (they carry a manual extension_predicate alignment made after the
last generator run, see README F-GATE-2), so a full regeneration would silently revert them.
This helper therefore writes exactly one new mutant from the same in-code base and mutation
used by make_fixtures.py, and appends its manifest entry; every existing fixture byte and
every existing manifest entry is left untouched.  Idempotent: re-running is a no-op when the
file and the manifest entry already match.
"""
from __future__ import annotations

import copy
import hashlib
import json

import yaml

import make_fixtures as mf

NAME = "m25_wcc_binder_unused"
HERE = mf.HERE
FIX = mf.FIX
MANIFEST = FIX / "manifest.json"


def main() -> int:
    bkey, rule, fn, note = mf.mutations(mf.mutant_bases())[NAME]
    data = copy.deepcopy(mf.mutant_bases()[bkey])
    fn(data)
    out = FIX / f"{NAME}.yaml"
    text = (f"# GENERATED mutant for FORM-GATE-01: expected {rule} - {note}\n"
            + yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    sha = hashlib.sha256(text.encode()).hexdigest()

    manifest = json.loads(MANIFEST.read_text())
    entry = {"path": str(out), "class_id": data["class_id"], "expected_rule": rule,
             "note": note, "sha256": sha}
    existing = manifest["mutants"].get(NAME)
    if out.exists() and out.read_text() == text and existing == entry:
        print(f"{NAME}: already present and identical (sha256 {sha[:16]})")
        return 0

    out.write_text(text)
    manifest["mutants"][NAME] = entry
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"{NAME}: wrote {out.name} sha256 {sha[:16]}; "
          f"mutants={len(manifest['mutants'])} positives={len(manifest['positives'])} "
          f"rephrased={len(manifest['rephrased'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
