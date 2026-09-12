#!/usr/bin/env python3
"""W068-FORM-REV13-REMEASURE-14 corpus builder (worker-068, bounded class-bound task).

Pins the live rev13 canonical schemas, the two class-binding stage instruments and the four
FORM-HELDOUT-08 reference mutations, snapshots them, and builds a fixture corpus:

  base_<K>.yaml            untouched rev13 base (baseline)
  ctrl_identity_<K>.yaml   byte-identical copy of the base (arm-informativeness control)
  ctrl_format_<K>.yaml     comment-prepended, structurally identical copy (false-positive ctl)
  iso_m04/m16/m29 (C0), iso_m25 (W)   rev13 base with exactly one declared leaf replaced by
                                       the value taken from the corresponding reference file

Construction is accepted only when a structural leaf diff shows exactly the declared path.
Nothing outside artifacts/worker-068/rev13remeasure14/ is written.

Exit 0 built; 2 precondition failure (pin mismatch / construction failure).
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CST = timezone(timedelta(hours=8))
SNAP = HERE / "snapshot"
FIX = HERE / "fixtures"

sys.path.insert(0, str(ROOT / "artifacts" / "worker-068" / "deffreeze13"))
from definition_freeze_check import changed_leaves  # noqa: E402

SCHEMAS = {
    "W": "schemas/af_wcc_vacuum.yaml",
    "C2": "schemas/af_scc_c2_vacuum.yaml",
    "C0": "schemas/af_scc_c0_vacuum.yaml",
}
CLASS_OF_BASE = {"W": "AF-WCC-VAC-GEN", "C2": "AF-SCC-C2-VAC-GEN", "C0": "AF-SCC-C0-VAC-GEN"}
SNAP_INSTRUMENTS = {
    "artifacts/formulation/tools/check_class_schema.py": "artifacts/formulation/tools/check_class_schema.py",
    "artifacts/formulation/KEY_MANIFEST.json": "artifacts/formulation/KEY_MANIFEST.json",
    "artifacts/formulation/rule_spec.json": "artifacts/formulation/rule_spec.json",
    "artifacts/worker-06/spec_conformance_audit.py": "artifacts/worker-06/spec_conformance_audit.py",
}
MUTATIONS = {
    "iso_m04": {
        "class_key": "C0",
        "leaf_path": ["data_class", "adm_mass", "sign"],
        "source": "artifacts/worker-068/heldout3/known_leaks/escape_m04_adm_mass_sign_erased.yaml",
        "family": "adm-mass-erasure",
    },
    "iso_m16": {
        "class_key": "C0",
        "leaf_path": ["implication_ledger", "extension_class_containment"],
        "source": "artifacts/worker-068/heldout3/known_leaks/escape_m16_containment_reversal.yaml",
        "family": "containment-reversal",
    },
    "iso_m29": {
        "class_key": "C0",
        "leaf_path": ["quantifiers", "domains", "D2", "definition"],
        "source": "artifacts/worker-068/heldout3/known_leaks/escape_m29_data_domain_contradiction.yaml",
        "family": "data-domain-contradiction",
    },
    "iso_m25": {
        "class_key": "W",
        "leaf_path": ["i_plus", "completeness_definition"],
        "source": "artifacts/worker-068/heldout3/known_leaks/escape_m25_wcc_completeness_swap.yaml",
        "family": "completeness-definition-swap",
    },
}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def get_path(doc: dict, path: list):
    node = doc
    for key in path:
        if not isinstance(node, dict) or key not in node:
            return None, False
        node = node[key]
    return node, True


def set_path(doc: dict, path: list, value) -> None:
    node = doc
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value


def main() -> int:
    pre = json.loads((HERE / "PREREGISTRATION.json").read_text())
    pins = pre["pins"]
    now = datetime.now(CST).isoformat(timespec="seconds")
    problems: list = []

    # 1. verify live sources against preregistered pins
    live_pins = {}
    for rel, want in pins["canonical_schemas"].items():
        live_pins[rel] = want
    for rel, want in pins["instruments"].items():
        live_pins[rel] = want
    for rel, want in pins["mutation_sources"].items():
        live_pins[rel] = want
    measured = {}
    for rel, want in live_pins.items():
        p = ROOT / rel
        got = sha256_file(p) if p.exists() else None
        measured[rel] = got
        if got != want:
            problems.append(f"pin mismatch {rel}: declared {want} measured {got}")
    if problems:
        print(json.dumps({"verdict": "PRECONDITION_FAILED", "problems": problems}, indent=1))
        return 2

    # 2. snapshot pinned inputs (idempotent, byte copy)
    if SNAP.exists():
        shutil.rmtree(SNAP)
    (SNAP / "schemas").mkdir(parents=True)
    for key, rel in SCHEMAS.items():
        dst = SNAP / "schemas" / Path(rel).name
        shutil.copyfile(ROOT / rel, dst)
    for src_rel, dst_rel in SNAP_INSTRUMENTS.items():
        dst = SNAP / dst_rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / src_rel, dst)
    (SNAP / "artifacts" / "worker-068").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "artifacts/worker-068/deffreeze13/definition_freeze_check.py",
                    SNAP / "artifacts/worker-068/definition_freeze_check.py")

    snapshots = {}
    for key, rel in SCHEMAS.items():
        src = ROOT / rel
        dst = SNAP / "schemas" / Path(rel).name
        snapshots[f"schemas/{Path(rel).name}"] = {
            "source": rel, "source_sha256": sha256_file(src), "snapshot_sha256": sha256_file(dst),
        }
    for src_rel, dst_rel in SNAP_INSTRUMENTS.items():
        snapshots[dst_rel] = {
            "source": src_rel, "source_sha256": sha256_file(ROOT / src_rel),
            "snapshot_sha256": sha256_file(SNAP / dst_rel),
        }

    # 3. build fixture corpus
    if FIX.exists():
        shutil.rmtree(FIX)
    FIX.mkdir(parents=True)
    fixtures = []
    base_docs = {}
    for key, rel in SCHEMAS.items():
        src = SNAP / "schemas" / Path(rel).name
        raw = src.read_bytes()
        base_path = FIX / f"base_{key}.yaml"
        base_path.write_bytes(raw)
        base_docs[key] = yaml.safe_load(raw)
        fixtures.append({
            "name": f"base_{key}.yaml", "role": "base", "class_id": CLASS_OF_BASE[key],
            "class_key": key, "base": None, "leaf_path": None, "transplantable": True,
            "sha256": sha256_file(base_path),
        })
        ident = FIX / f"ctrl_identity_{key}.yaml"
        ident.write_bytes(raw)
        fixtures.append({
            "name": f"ctrl_identity_{key}.yaml", "role": "identity_control",
            "class_id": CLASS_OF_BASE[key], "class_key": key, "base": f"base_{key}.yaml",
            "leaf_path": None, "transplantable": True, "sha256": sha256_file(ident),
        })
        fmt = FIX / f"ctrl_format_{key}.yaml"
        fmt.write_bytes(
            b"# W068-FORM-REV13-REMEASURE-14 formatting control: comment added, structure identical\n"
            + raw)
        fixtures.append({
            "name": f"ctrl_format_{key}.yaml", "role": "formatting_control",
            "class_id": CLASS_OF_BASE[key], "class_key": key, "base": f"base_{key}.yaml",
            "leaf_path": None, "transplantable": True, "sha256": sha256_file(fmt),
        })

    for name, spec in MUTATIONS.items():
        key = spec["class_key"]
        ref_doc = yaml.safe_load((ROOT / spec["source"]).read_bytes())
        value, ok = get_path(ref_doc, spec["leaf_path"])
        base_doc = base_docs[key]
        _, base_has = get_path(base_doc, spec["leaf_path"])
        entry = {
            "name": f"{name}.yaml", "role": "isolated_mutation",
            "class_id": CLASS_OF_BASE[key], "class_key": key, "base": f"base_{key}.yaml",
            "leaf_path": spec["leaf_path"], "family": spec["family"], "source": spec["source"],
            "transplantable": bool(ok and base_has),
        }
        if not entry["transplantable"]:
            entry["reason"] = "declared leaf path absent from reference or rev13 base"
            fixtures.append(entry)
            continue
        doc = yaml.safe_load((SNAP / "schemas" / Path(SCHEMAS[key]).name).read_bytes())
        set_path(doc, spec["leaf_path"], value)
        out = FIX / entry["name"]
        out.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=1000))
        diffs = changed_leaves(base_doc, yaml.safe_load(out.read_bytes()))
        declared = "$." + ".".join(spec["leaf_path"])
        entry["changed_leaves"] = [d["path"] for d in diffs]
        entry["declared_path"] = declared
        entry["sha256"] = sha256_file(out)
        if len(diffs) != 1 or diffs[0]["path"] != declared:
            entry["transplantable"] = False
            entry["reason"] = f"structural diff {[d['path'] for d in diffs]} != [{declared}]"
        fixtures.append(entry)

    manifest = {
        "schema": "worker-068/rev13remeasure14/corpus-manifest/v1",
        "task_id": pre["task_id"],
        "created_at": now,
        "preregistration_sha256": sha256_file(HERE / "PREREGISTRATION.json"),
        "snapshots": snapshots,
        "fixtures": fixtures,
        "live_source_hashes_at_build": measured,
    }
    (HERE / "manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=False) + "\n")
    bad = [f["name"] for f in fixtures if not f.get("transplantable")]
    print(json.dumps({
        "verdict": "BUILT" if not bad else "BUILT_WITH_EXCLUSIONS",
        "fixtures": len(fixtures), "excluded": bad,
        "manifest_sha256": sha256_file(HERE / "manifest.json"),
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
