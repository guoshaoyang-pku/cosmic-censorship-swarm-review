#!/usr/bin/env python3
"""Copy the shared fixture corpora into artifacts/flash-11/.../corpus/ (FORM-DIFF-02 D2).

Sources copied (read-only originals never modified):
  w06/       artifacts/worker-06/fixtures/*.json          (16: 4 pos, 12 neg)
  f13/       artifacts/flash-13/f1_gate/fixtures/*.yaml   (7: 1 pos, 6 neg, 1 known blind spot)
  canonical/ artifacts/formulation/schemas/*.yaml         (3: the lead's canonical schemas)
  flash11/   artifacts/flash-11/f1_aux_class_binding/fixtures/*.yaml (21: layout-own controls)

Writes corpus/manifest.json with per-file origin, sha256, expected verdict, and the
aggregate corpus sha256 used by the escape-rate statement.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
CORPUS = HERE / "corpus"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    if CORPUS.exists():
        shutil.rmtree(CORPUS)
    manifest = {"sources": {}, "fixtures": {}}

    def add(group: str, src: Path, dest_name: str, expected: str, note: str = "") -> None:
        (CORPUS / group).mkdir(parents=True, exist_ok=True)
        dst = CORPUS / group / dest_name
        shutil.copy2(src, dst)
        manifest["fixtures"][f"{group}/{dest_name}"] = {
            "origin": str(src.relative_to(REPO)),
            "sha256": sha256(dst),
            "expected": expected,
            "note": note,
        }

    w06 = REPO / "artifacts/worker-06/fixtures"
    for f in sorted(w06.glob("*.json")):
        meta = json.loads(f.read_text()).get("_meta", {})
        add("w06", f, f.name, meta.get("expected", "unknown"), meta.get("purpose", ""))
    manifest["sources"]["w06"] = {"dir": str(w06.relative_to(REPO)), "count": len(list(w06.glob('*.json')))}

    f13 = REPO / "artifacts/flash-13/f1_gate/fixtures"
    f13man = json.loads((f13 / "manifest.json").read_text())
    for f in sorted(p for p in f13.glob("*.yaml")):
        stem = f.stem
        exp = f13man.get(stem, {}).get("expected_verdict", "unknown")
        add("f13", f, f.name, exp, f13man.get(stem, {}).get("note", ""))
    manifest["sources"]["f13"] = {"dir": str(f13.relative_to(REPO)), "count": len(list(f13.glob('*.yaml')))}

    canon = REPO / "artifacts/formulation/schemas"
    for f in sorted(canon.glob("*.yaml")):
        add("canonical", f, f.name, "pass", "lead-formulation canonical schema; expected spec-conformant")
    manifest["sources"]["canonical"] = {"dir": str(canon.relative_to(REPO)), "count": len(list(canon.glob('*.yaml')))}

    mine = HERE / "fixtures"
    exp = json.loads((mine / "EXPECTATIONS.json").read_text())
    for f in sorted(mine.glob("*.yaml")):
        e = exp.get(f.name, {})
        if f.name.startswith("good_"):
            expected = "accept"
        elif f.name.startswith("adv_"):
            expected = "escape"
        elif e.get("verdict") == "ACCEPT":
            expected = "accept"
        elif e.get("verdict") == "REJECT":
            expected = "reject"
        else:
            expected = "unknown"
        add("flash11", f, f.name, expected, e.get("note", ""))
    manifest["sources"]["flash11"] = {"dir": str(mine.relative_to(REPO)), "count": len(list(mine.glob("*.yaml")))}

    # rev4 strengthening probes (FORM-DIFF-02 follow-up)
    probes = HERE / "evidence/probes"
    pman = json.loads((probes / "manifest.json").read_text())
    for item in pman["probes"]:
        f = probes / item["file"]
        expected = "reject" if item.get("expect_fail_rule") else "accept"
        add("rev4probes", f, f.name, expected, f"expected_fail_rule={item.get('expect_fail_rule')}")
    manifest["sources"]["rev4probes"] = {"dir": str(probes.relative_to(REPO)), "count": len(pman["probes"])}

    # aggregate corpus hash: sha256 over sorted "path:sha256" lines
    lines = "\n".join(f"{k}:{v['sha256']}" for k, v in sorted(manifest["fixtures"].items()))
    manifest["corpus_sha256"] = hashlib.sha256(lines.encode()).hexdigest()
    manifest["fixture_count"] = len(manifest["fixtures"])
    (CORPUS / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"corpus: {manifest['fixture_count']} fixtures, sha256={manifest['corpus_sha256'][:16]}...")
    for g, s in manifest["sources"].items():
        print(f"  {g}: {s['count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
