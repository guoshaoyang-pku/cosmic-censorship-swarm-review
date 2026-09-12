#!/usr/bin/env python3
"""W066-REV25-VERDICT-01 step 1: byte-pin the review targets.

Copies the canonical rev25 inputs (three class schemas, the F0 taxonomy, the variant
registry, the rule spec, the frozen manifest, the two gate tools, the frozen acceptance
evidence and the rebased fixture corpus) into pinned/ and records sha256 + bytes + mtime
for the source and the copy, plus the hash declared by FROZEN.json at snapshot time.

No canonical file is written. The pinned_manifest.json is the binding of every later claim.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PINNED = HERE / "pinned"
CST = timezone(timedelta(hours=8))

TARGETS = {
    "schemas/af_wcc_vacuum.yaml": "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml": "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml": "schemas/af_scc_c0_vacuum.yaml",
    "research_map/formulation_taxonomy.yaml": "f0/formulation_taxonomy.yaml",
    "artifacts/formulation/VARIANT_REGISTRY.json": "f0/VARIANT_REGISTRY.json",
    "artifacts/formulation/rule_spec.json": "tools/rule_spec.json",
    "artifacts/formulation/KEY_MANIFEST.json": "tools/KEY_MANIFEST.json",
    "artifacts/formulation/FROZEN.json": "frozen/FROZEN.json",
    "artifacts/formulation/tools/check_class_schema.py": "tools/check_class_schema.py",
    "artifacts/worker-06/spec_conformance_audit.py": "tools/spec_conformance_audit.py",
    "artifacts/formulation/tools/run_acceptance.py": "tools/run_acceptance.py",
    "artifacts/formulation/evidence/acceptance_pipeline_report.json": "evidence/acceptance_pipeline_report.json",
    "artifacts/formulation/evidence/semantic_escape_rebased.json": "evidence/semantic_escape_rebased.json",
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    frozen = json.loads((ROOT / "artifacts/formulation/FROZEN.json").read_text())
    declarations = frozen.get("files", {})
    for sub in ("schemas", "f0", "tools", "frozen", "evidence", "rebased_fixtures"):
        (PINNED / sub).mkdir(parents=True, exist_ok=True)

    entries = []
    for src, dst in TARGETS.items():
        s = ROOT / src
        d = PINNED / dst
        shutil.copyfile(s, d)
        declared = declarations.get(src, {}).get("sha256")
        entries.append({
            "source": src,
            "pinned": f"pinned/{dst}",
            "sha256_source": sha(s),
            "sha256_pinned": sha(d),
            "bytes": s.stat().st_size,
            "source_mtime_ns": s.stat().st_mtime_ns,
            "frozen_revision_declared": frozen.get("revision"),
            "frozen_declared_sha256": declared,
            "frozen_match": declared == sha(s),
            "class_id": {
                "schemas/af_wcc_vacuum.yaml": "AF-WCC-VAC-GEN",
                "schemas/af_scc_c2_vacuum.yaml": "AF-SCC-C2-VAC-GEN",
                "schemas/af_scc_c0_vacuum.yaml": "AF-SCC-C0-VAC-GEN",
                "research_map/formulation_taxonomy.yaml": "GLOBAL",
            }.get(src, "GLOBAL"),
        })

    # check_class_schema.py resolves SPEC/KEY_MANIFEST at parents[1]; for the pinned copy at
    # pinned/tools/ that is pinned/, so the two files are also placed at the pinned root.
    gate_relative = []
    for name in ("rule_spec.json", "KEY_MANIFEST.json"):
        s = ROOT / "artifacts/formulation" / name
        d = PINNED / name
        shutil.copyfile(s, d)
        gate_relative.append({"source": f"artifacts/formulation/{name}", "pinned": f"pinned/{name}",
                              "sha256_pinned": sha(d), "bytes": d.stat().st_size,
                              "frozen_declared_sha256": declarations.get(f"artifacts/formulation/{name}", {}).get("sha256")})

    corpus_src = ROOT / "artifacts/formulation/evidence/rebased_fixtures"
    corpus_entries = []
    for p in sorted(corpus_src.glob("*.yaml")):
        d = PINNED / "rebased_fixtures" / p.name
        shutil.copyfile(p, d)
        corpus_entries.append({"fixture": p.name, "sha256_source": sha(p), "sha256_pinned": sha(d),
                               "bytes": p.stat().st_size})

    manifest = {
        "task_id": "W066-REV25-VERDICT-01",
        "worker": "worker-066",
        "actor": "worker-066",
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "snapshot_rule": ("a verdict binds bytes, not paths; every later measurement in this task "
                          "uses pinned/ copies and the sha256 recorded here"),
        "frozen_revision_at_snapshot": frozen.get("revision"),
        "frozen_frozen_at": frozen.get("frozen_at"),
        "targets": entries,
        "gate_relative_copies": gate_relative,
        "corpus": {"source_dir": "artifacts/formulation/evidence/rebased_fixtures",
                   "pinned_dir": "pinned/rebased_fixtures",
                   "fixtures": corpus_entries,
                   "controls": [c["fixture"] for c in corpus_entries if c["fixture"].startswith("control_")],
                   "mutants": [c["fixture"] for c in corpus_entries if not c["fixture"].startswith("control_")]},
    }
    out = HERE / "pinned_manifest.json"
    out.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"pinned {len(entries)} targets + {len(corpus_entries)} fixtures -> {out}")
    print("all frozen_match:", all(e["frozen_match"] for e in entries))
    for e in entries:
        print(f"  {e['sha256_pinned'][:12]} {e['source']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
