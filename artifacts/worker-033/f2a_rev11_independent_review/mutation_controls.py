#!/usr/bin/env python3
"""Falsifier controls for check_f2a_class_binding.py (worker-033).

A checker that cannot be made to fail on a planted defect proves nothing. Each
control plants exactly one defect (or repairs one) in a copy of the pinned
bytes and records whether the targeted check flips as predicted. Two positive
controls repair defects and must flip fail -> pass; the baseline run must show
the same statuses as report.json.

Run:  python3 mutation_controls.py --out mutation_controls.json
"""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
import tempfile
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_f2a_class_binding as chk  # noqa: E402

MEAS = "2026-09-12T00:19:48+08:00"
F2A = "schemas_af_scc_c2_vacuum.yaml"
F0 = "research_map_formulation_taxonomy.yaml"


def load(p: Path):
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def dump(obj, p: Path):
    p.write_text(yaml.safe_dump(obj, sort_keys=False, allow_unicode=True, width=1000),
                 encoding="utf-8")


def status_of(result, check_id):
    for c in result["checks"]:
        if c["check_id"] == check_id:
            return c["status"]
    return "absent"


def run(base: Path, mutations, tmp: Path):
    """mutations: (f2a_dict_mutator|None, f0_dict_mutator|None, text_edits)"""
    d = tmp
    for f in base.iterdir():
        if f.is_file():
            shutil.copy2(f, d / f.name)
    f2a_obj = load(base / F2A)
    f0_obj = load(base / F0)
    f2a_mut, f0_mut, text_edits = mutations
    if f2a_mut:
        f2a_mut(f2a_obj)
    if f0_mut:
        f0_mut(f0_obj)
    dump(f2a_obj, d / F2A)
    dump(f0_obj, d / F0)
    if text_edits:
        raw = (d / F2A).read_text(encoding="utf-8")
        for old, new in text_edits:
            raw = raw.replace(old, new)
        (d / F2A).write_text(raw, encoding="utf-8")
    return chk.run_checks(
        d / F2A, d / F0,
        base / "artifacts_formulation_formulation_taxonomy.yaml",
        base / "artifacts_formulation_VOCAB_ALIASES.json",
        MEAS, repo_root=base,
    )


def main() -> int:
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--pinned", default=str(here / "pinned"))
    ap.add_argument("--out", default=str(here / "mutation_controls.json"))
    args = ap.parse_args()
    base = Path(args.pinned)

    controls = []

    def add(cid, desc, mutations, expectations):
        with tempfile.TemporaryDirectory() as td:
            res = run(base, mutations, Path(td))
        observed = {k: status_of(res, k) for k in expectations}
        ok = observed == expectations
        controls.append({
            "control_id": cid,
            "planted_defect": desc,
            "expected": expectations,
            "observed": observed,
            "control_passed": ok,
            "checker_verdict_under_mutation": res["proposed_verdict"],
        })

    def m_class_id(o):
        o["class_id"] = "AF-SCC-C0-VAC-GEN"

    def m_regularity_component(o):
        o["class_components"]["regularity_token"] = "C0"

    def m_composite(o):
        o["quantifiers"]["formal"] = o["quantifiers"]["formal"] + " C0 or C2"

    def m_drop_predicate(o):
        o.pop("extension_predicate", None)

    def m_bad_domain_ref(o):
        o["quantifiers"]["formal"] = o["quantifiers"]["formal"].replace("D0", "D9")

    def m_matter_leak(o):
        o["genericity"]["excluded_set"] = (
            "meager; fine-tuned threshold data of type-II critical collapse"
        )

    def m_bad_pointer(o):
        o["class_contract_pointer"] = (
            "artifacts/formulation/does_not_exist.yaml#class_contracts.AF-SCC-C2-VAC-GEN"
        )

    def m_drop_d0(o):
        o["quantifiers"]["domains"].pop("D0", None)

    def m_repair_vocab(o):
        o["conclusion"]["conclusion_type"] = "strong_cosmic_censorship_C2"

    def m_repair_formal(o):
        o["conclusion"]["statement_formal"] = o["quantifiers"]["formal"]

    def m_canonical_gains_contracts(o):
        o["class_contracts"] = {
            "AF-SCC-C2-VAC-GEN": {"conclusion_type": "scc_c2_future_inextendibility"}
        }

    add("M1", "class_id rewritten to the sibling C0 class", (m_class_id, None, None),
        {"ID-01": "fail", "ID-02": "pass"})
    add("M1b", "class_components.regularity_token rewritten to C0 while class_id stays C2",
        (m_regularity_component, None, None), {"ID-02": "fail"})
    add("M2", "'C0 or C2' composite pasted into quantifiers.formal", (m_composite, None, None),
        {"LEAK-01": "fail"})
    add("M3", "extension_predicate block deleted (HF-2 regression)", (m_drop_predicate, None, None),
        {"DEF-03": "fail"})
    add("M4", "formal sentence references undefined domain D9", (m_bad_domain_ref, None, None),
        {"DEF-02": "fail"})
    add("M5", "flash-19 HF-3 matter leak reinserted in genericity.excluded_set",
        (m_matter_leak, None, None), {"LEAK-02": "fail"})
    add("M6", "class_contract_pointer pointed at a nonexistent file", (m_bad_pointer, None, None),
        {"PTR-01": "fail"})
    add("M7", "revision timestamp moved to 2099 (clock-discipline defect)",
        (None, None, [("2026-09-12T00:30:00+08:00", "2099-01-01T00:00:00+08:00")]),
        {"TIME-01": "fail"})
    add("M8", "D0 block deleted (HF-1 regression)", (m_drop_d0, None, None),
        {"DEF-01": "fail", "DEF-02": "fail"})
    add("M9", "positive control: conclusion_type repaired to the canonical F0 token",
        (m_repair_vocab, None, None), {"VOC-01": "pass", "VOC-03": "pass"})
    add("M10", "positive control: conclusion.statement_formal made identical to "
               "quantifiers.formal", (m_repair_formal, None, None), {"FORM-01": "pass"})
    add("M11", "positive control: canonical F0 taxonomy gains class_contracts",
        (None, m_canonical_gains_contracts, None), {"PTR-02": "pass"})

    with tempfile.TemporaryDirectory() as td:
        baseline = run(base, (None, None, None), Path(td))
    baseline_status = {c["check_id"]: c["status"] for c in baseline["checks"]}

    out = {
        "controls_script": "mutation_controls.py",
        "measurement_time": MEAS,
        "baseline_verdict": baseline["proposed_verdict"],
        "baseline_status": baseline_status,
        "controls": controls,
        "all_controls_passed": all(c["control_passed"] for c in controls),
    }
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    for c in controls:
        flag = "OK " if c["control_passed"] else "BAD"
        print(f"{flag} {c['control_id']:4s} expected={c['expected']} observed={c['observed']}")
    print(f"baseline verdict={baseline['proposed_verdict']} "
          f"all_controls_passed={out['all_controls_passed']}")
    return 0 if out["all_controls_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
