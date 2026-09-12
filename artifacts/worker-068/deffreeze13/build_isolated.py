#!/usr/bin/env python3
"""W068-FORM-DEFFREEZE-13 corpus builder: mutation-isolated reference escapes (worker-068).

The FORM-HELDOUT-08 reference fixtures under ``heldout3/known_leaks/`` are rev8 documents
compared against the rev11 frozen base, so each one carries the labelled mutation PLUS
incidental rev8->rev11 drift (revision counters, f0 binding hashes, anti_scope /
class_identity_variants edits). A catch measured on those files cannot be attributed to the
labelled mutation site.

This builder starts from the pinned rev11 base and applies ONLY the labelled mutation value
taken from the corresponding reference fixture, producing a mutation-isolated fixture for
each of the four families. It then verifies by structural leaf diff that exactly the intended
path changed (formatting and key order are irrelevant to the diff).

Output: ``isolated/iso_<name>.yaml`` and ``isolated_manifest.json``.
Exit: 0 built (all four verified); 2 precondition failure.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CST = timezone(timedelta(hours=8))

sys.path.insert(0, str(HERE))
from definition_freeze_check import changed_leaves  # noqa: E402

# name -> (class key, base, reference fixture, leaf path, source family)
MUTATIONS = {
    "m04": {
        "class": "C0",
        "reference": "artifacts/worker-068/heldout3/known_leaks/escape_m04_adm_mass_sign_erased.yaml",
        "path": ["data_class", "adm_mass", "sign"],
        "family": "adm-mass-erasure",
        "label": "ADM mass sign erased: the frozen sign statement is replaced by the pre-repair no-sign wording",
    },
    "m16": {
        "class": "C0",
        "reference": "artifacts/worker-068/heldout3/known_leaks/escape_m16_containment_reversal.yaml",
        "path": ["implication_ledger", "extension_class_containment"],
        "family": "containment-reversal",
        "label": "extension-class containment chain reversed in the implication ledger",
    },
    "m25": {
        "class": "W",
        "reference": "artifacts/worker-068/heldout3/known_leaks/escape_m25_wcc_completeness_swap.yaml",
        "path": ["i_plus", "completeness_definition"],
        "family": "completeness-definition-swap",
        "label": "I+ completeness definition replaced by a causal-curve continuation reading",
    },
    "m29": {
        "class": "C0",
        "reference": "artifacts/worker-068/heldout3/known_leaks/escape_m29_data_domain_contradiction.yaml",
        "path": ["quantifiers", "domains", "D2", "definition"],
        "family": "data-domain-contradiction",
        "label": "D2 data domain drops the vacuum requirement (contradicts data_class.equations)",
    },
}
BASES = {
    "W": "artifacts/worker-068/polarity12/shadow/schemas/af_wcc_vacuum.yaml",
    "C2": "artifacts/worker-068/polarity12/shadow/schemas/af_scc_c2_vacuum.yaml",
    "C0": "artifacts/worker-068/polarity12/shadow/schemas/af_scc_c0_vacuum.yaml",
}
CLASS_OF_BASE = {"W": "AF-WCC-VAC-GEN", "C2": "AF-SCC-C2-VAC-GEN", "C0": "AF-SCC-C0-VAC-GEN"}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def get_path(doc, path):
    cur = doc
    for part in path:
        cur = cur[part]
    return cur


def set_path(doc, path, value):
    cur = doc
    for part in path[:-1]:
        cur = cur[part]
    cur[path[-1]] = value


def main() -> int:
    outdir = HERE / "isolated"
    outdir.mkdir(exist_ok=True)
    rows = []
    problems = []
    for name, spec in MUTATIONS.items():
        base_path = ROOT / BASES[spec["class"]]
        ref_path = ROOT / spec["reference"]
        base_doc = yaml.safe_load(base_path.read_bytes())
        ref_doc = yaml.safe_load(ref_path.read_bytes())
        iso_doc = yaml.safe_load(base_path.read_bytes())  # fresh copy
        expected_path = "$." + ".".join(spec["path"])
        if base_doc.get("class_id") != CLASS_OF_BASE[spec["class"]]:
            problems.append(f"{name}: base class_id mismatch")
        if ref_doc.get("class_id") != CLASS_OF_BASE[spec["class"]]:
            problems.append(f"{name}: reference class_id mismatch")
        value = get_path(ref_doc, spec["path"])
        set_path(iso_doc, spec["path"], value)
        iso_path = outdir / f"iso_{name}.yaml"
        iso_path.write_text(yaml.safe_dump(iso_doc, sort_keys=False, default_flow_style=False,
                                           allow_unicode=True, width=1000))
        diffs = changed_leaves(base_doc, iso_doc)
        changed = [d["path"] for d in diffs]
        if changed != [expected_path]:
            problems.append(f"{name}: isolated diff is {changed}, expected exactly [{expected_path}]")
        rows.append({
            "name": name,
            "family": spec["family"],
            "label": spec["label"],
            "class_id": CLASS_OF_BASE[spec["class"]],
            "base": BASES[spec["class"]],
            "base_sha256": sha256_file(base_path),
            "reference": spec["reference"],
            "reference_sha256": sha256_file(ref_path),
            "isolated": str(iso_path.relative_to(ROOT)),
            "isolated_sha256": sha256_file(iso_path),
            "mutated_leaf_path": expected_path,
            "mutated_leaf_group": diffs[0]["group"] if len(diffs) == 1 else None,
            "base_value_preview": diffs[0]["base_preview"] if len(diffs) == 1 else None,
            "mutated_value_preview": diffs[0]["fixture_preview"] if len(diffs) == 1 else None,
            "verified_single_leaf": changed == [expected_path],
        })
    manifest = {
        "corpus_id": "W068-FORM-DEFFREEZE-13-ISOLATED",
        "task_id": "W068-FORM-DEFFREEZE-13",
        "worker": "worker-068",
        "actor": "worker-068",
        "built_at": datetime.now(CST).isoformat(timespec="seconds"),
        "bases": BASES,
        "build_method": ("start from the pinned rev11 base; set the labelled leaf to the value "
                         "read from the heldout3 reference fixture; verify structural leaf diff "
                         "== exactly that leaf"),
        "valid": not problems,
        "problems": problems,
        "mutations": rows,
    }
    (HERE / "isolated_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    print(json.dumps({"valid": manifest["valid"], "problems": problems,
                      "isolated": [{"name": r["name"], "leaf": r["mutated_leaf_path"],
                                    "group": r["mutated_leaf_group"],
                                    "sha256": r["isolated_sha256"][:12]} for r in rows]},
                     indent=2))
    return 0 if manifest["valid"] else 2


if __name__ == "__main__":
    sys.exit(main())
