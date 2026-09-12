#!/usr/bin/env python3
"""Repair the R03 kind-declaration defect in the FORM-GATE-01 fixture corpus (gate rev1.3).

Measured defect (gate 1.2 could not see it, gate 1.3 semantic R03 does):
  All 35 fixtures in fixtures/ declare quantifiers.ordered[2].kind = "exists" while their own
  quantifiers.formal sentence says "not exists p in VIS with Visible(p)".  A schema whose declared
  quantifier kind contradicts its own formal sentence is not a conforming exemplar under R03
  ("ordered list of {kind, ...}; formal is a single sentence using those binders"); the earlier
  literal-substring test never compared kinds, so the positives passed and every derived mutant
  carried a spurious extra R03 finding.

What this script does
  * reads fixtures/manifest.json and each fixture doc;
  * for every doc whose declared kind sequence has the same length as the keyword sequence found
    in its own quantifiers.formal, rewrites the DECLARED kinds to the sentence's sequence
    (the sentence is what the fixture intends: the class conclusion is "no visible point");
  * leaves every other byte of the logical document untouched, re-serialises YAML deterministically
    (sort_keys=False, no line wrapping) into fixtures_v13/;
  * writes fixtures_v13/manifest.json carrying, per file, legacy path+sha256, repaired sha256, the
    logical diff, and the unchanged expected-rule metadata;
  * refuses (exit 1) if any fixture cannot be aligned or if a repair changes anything other than
    quantifiers.ordered[*].kind.

The legacy corpus is NOT modified.  Legacy bytes + the rev1.2 suite report are archived under
legacy_v12/ for the delta record.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
LEGACY = HERE / "fixtures"
OUT = HERE / "fixtures_v13"


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_gate():
    spec = importlib.util.spec_from_file_location("ccs", HERE / "check_class_schema.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def flatten_kinds(doc):
    q = doc.get("quantifiers") or {}
    ordered = q.get("ordered") or []
    return [str(it.get("kind")) for it in ordered if isinstance(it, dict)], ordered, q


def main() -> int:
    ccs = load_gate()
    manifest = json.loads((LEGACY / "manifest.json").read_text())
    OUT.mkdir(exist_ok=True)
    new_manifest = {"note": "gate rev1.3 repaired corpus; legacy corpus and sha256s retained",
                    "gate_version": ccs.GATE_VERSION, "legacy_manifest_sha256": sha256_file(LEGACY / "manifest.json")}
    repairs, problems = {}, []
    for group in ("positives", "mutants", "rephrased"):
        new_manifest[group] = {}
        for name, meta in manifest[group].items():
            src = Path(meta["path"])
            doc = yaml.safe_load(src.read_text())
            before = copy.deepcopy(doc)
            decl, ordered, q = flatten_kinds(doc)
            seq = [k for (_kw, k, _p) in ccs.r03_keyword_sequence(ccs.r03_normalise(q.get("formal", "")))]
            if decl != seq:
                if len(decl) != len(seq):
                    problems.append(f"{name}: kind lengths differ decl={decl} found={seq}")
                    continue
                for i, it in enumerate([x for x in ordered if isinstance(x, dict)]):
                    if it.get("kind") != seq[i]:
                        repairs.setdefault(name, []).append(
                            {"path": f"quantifiers.ordered[{i}].kind",
                             "from": it.get("kind"), "to": seq[i]})
                        it["kind"] = seq[i]
            # verify the repair is exactly the kind fix
            after = copy.deepcopy(doc)
            b, a = copy.deepcopy(before), copy.deepcopy(after)
            for d in (b, a):
                for it in ((d.get("quantifiers") or {}).get("ordered") or []):
                    it.pop("kind", None)
            if b != a:
                problems.append(f"{name}: repair changed more than ordered[*].kind")
                continue
            dst = OUT / src.name
            dst.write_text(yaml.safe_dump(doc, sort_keys=False, default_flow_style=False,
                                          width=10 ** 9, allow_unicode=True))
            entry = dict(meta)
            entry["legacy_path"] = str(src)
            entry["legacy_sha256"] = sha256_file(src)
            entry["path"] = str(dst)
            entry["sha256"] = sha256_file(dst)
            entry["kind_repair"] = repairs.get(name, [])
            new_manifest[group][name] = entry
    if problems:
        print("REFUSING: corpus problems:")
        for p in problems:
            print("  -", p)
        return 1
    (OUT / "manifest.json").write_text(json.dumps(new_manifest, indent=2, sort_keys=True) + "\n")
    n_fixed = sum(1 for v in new_manifest["positives"].values() if v["kind_repair"])
    n_fixed += sum(1 for v in new_manifest["mutants"].values() if v["kind_repair"])
    n_fixed += sum(1 for v in new_manifest["rephrased"].values() if v["kind_repair"])
    print(f"wrote {OUT}/manifest.json: {n_fixed} fixtures repaired (kind token only), "
          f"{len(problems)} problems")
    return 0


if __name__ == "__main__":
    sys.exit(main())
