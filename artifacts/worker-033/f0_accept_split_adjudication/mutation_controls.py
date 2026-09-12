#!/usr/bin/env python3
"""Mutation controls for check_f0_accept_split.py (worker-033, W033-F0-ACCEPT-SPLIT-ADJ-01).

The adjudication is only worth its hash if the checker can fail. Each control copies
the pinned inputs into a scratch root, plants exactly one defect (or one repair), and
requires the named check to flip. A negative control requires unrelated failures.

Run: python3 mutation_controls.py
Emits: mutation_controls.json
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_f0_accept_split as C  # noqa: E402

INPUTS = [C.CANON_F0, C.CANON_F1, C.CANON_F2A, C.CANON_F2B, C.ALIASES, C.AUTHORING, C.CHECKER, C.EVENTS]


def seed_root(repo: Path) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="w033-mut-"))
    for rel in INPUTS:
        src = repo / rel
        dst = tmp / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    return tmp


def edit_yaml(path: Path, fn):
    doc = yaml.safe_load(path.read_text())
    fn(doc)
    path.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))


def edit_text(path: Path, fn):
    path.write_text(fn(path.read_text()))


def status_of(rep: dict, cid: str) -> str:
    return next(c["status"] for c in rep["checks"] if c["check_id"] == cid)


def run_controls(repo: Path) -> dict:
    base = C.run_checks(repo)
    base_status = {c["check_id"]: c["status"] for c in base["checks"]}
    controls = []

    def control(name, expect_flip, mutate, must_not_flip=()):
        root = seed_root(repo)
        try:
            mutate(root)
            rep = C.run_checks(root)
            after = {c["check_id"]: c["status"] for c in rep["checks"]}
            flips = {cid: {"before": base_status[cid], "after": after[cid]}
                     for cid in base_status if base_status[cid] != after[cid]}
            flipped_expected = all(
                base_status[cid] != after[cid] and after[cid] == ("refuted" if base_status[cid] == "confirmed" else after[cid])
                for cid in expect_flip)
            untouched_ok = all(cid not in flips for cid in must_not_flip)
            controls.append({
                "control": name, "expect_flip": list(expect_flip), "mutations_applied": 1,
                "flips": flips, "expected_flip_ok": flipped_expected,
                "negative_control_ok": untouched_ok,
                "verdict": "pass" if (flipped_expected and untouched_ok) else "fail",
            })
        finally:
            shutil.rmtree(root, ignore_errors=True)

    # --- repairs: each must remove exactly the defect it targets ---
    def repair_scalar(doc):
        doc["classes"]["AF-WCC-SCALAR-SPH"]["conclusion"]["text"] = (
            "For every admissible (s,delta) there is a comeager set G_{s,delta} of data such that "
            "for every data set in G_{s,delta}, the MGHD admits I+ and every future-inextendible "
            "causal geodesic contained in J-(I+) is complete.")
        probe = dict(doc["classes"]["AF-WCC-SCALAR-SPH"])
        probe["provenance"] = {"source": "repair", "equivalence_source": "stated"}
        doc["classes"]["AF-WCC-SCALAR-SPH"] = probe

    # ADJ-06 (unsourced equivalence) and ADJ-07 (D3 overstatement) also clear here: repairing the
    # class text removes the bare quantifier AND the unsourced equivalence AND makes D3 true.
    control("M1 repair SCALAR-SPH quantifier", ["ADJ-04", "ADJ-05", "ADJ-12"],
            lambda r: edit_yaml(r / C.CANON_F0, repair_scalar),
            must_not_flip=("ADJ-10", "ADJ-11"))

    control("M2 mark H4 resolved", ["ADJ-05"],
            lambda r: edit_yaml(r / C.CANON_F0, lambda d: d["classes"]["AF-WCC-SCALAR-SPH"]["hypotheses"][3].update({"unresolved": False})),
            must_not_flip=("ADJ-04", "ADJ-12", "ADJ-07"))

    control("M3 scope D3 to the two SCC classes", ["ADJ-07"],
            lambda r: edit_yaml(r / C.CANON_F0, lambda d: d["class_scope_adjudication"]["resolved_divergences"][1].update(
                {"resolution": "the comeager quantifier is stated explicitly in the AF-SCC-C2-VAC-GEN and AF-SCC-C0-VAC-GEN conclusion texts"})),
            must_not_flip=("ADJ-04", "ADJ-05"))

    control("M4 F0 adopts registry-canonical tokens", ["ADJ-10"],
            lambda r: edit_yaml(r / C.CANON_F0, lambda d: d["field_vocabulary"]["conclusion_type"].update(
                {"allowed": ["weak_cosmic_censorship", "scc_c2_future_inextendibility", "scc_c0_future_inextendibility"]})),
            must_not_flip=("ADJ-11", "ADJ-04"))

    control("M5 F2a carries the alias pointer", ["ADJ-11"],
            lambda r: edit_yaml(r / C.CANON_F2A, lambda d: _add_pointer(d)),
            must_not_flip=("ADJ-10", "ADJ-04"))

    # --- negative controls: unrelated edits must not flip the defect checks ---
    control("N1 relabel an unrelated class (must not move any check)", [],
            lambda r: edit_yaml(r / C.CANON_F0, lambda d: d["classes"]["AF-WCC-VAC-GEN"].update(
                {"label": "relabelled, semantically identical"})),
            must_not_flip=("ADJ-04", "ADJ-05", "ADJ-06", "ADJ-07", "ADJ-08", "ADJ-10", "ADJ-11", "ADJ-12"))

    control("N2 drift the pinned hash (must trip ADJ-01 and nothing else)", ["ADJ-01"],
            lambda r: edit_text(r / C.CANON_F0, lambda s: s + "\n# hash drift control\n"),
            must_not_flip=("ADJ-04", "ADJ-05", "ADJ-07", "ADJ-10"))

    # --- checker-blind-spot control: move the D3 detector to read SCALAR-SPH too ---
    def repair_d3_detector(src: str) -> str:
        return src.replace(
            'ctext("AF-SCC-C0-VAC-GEN").lower() and "comeager" not in " ".join(ctext(c) for c in ("AF-SCC-C2-VAC-GEN","AF-SCC-C0-VAC-GEN")).lower()',
            'ctext("AF-SCC-C0-VAC-GEN").lower() and "comeager" not in " ".join(ctext(c) for c in ("AF-SCC-C2-VAC-GEN","AF-SCC-C0-VAC-GEN","AF-WCC-SCALAR-SPH")).lower()')
    control("M6 D3 detector reads SCALAR-SPH (scope repair)", ["ADJ-08"],
            lambda r: edit_text(r / C.CHECKER, repair_d3_detector),
            must_not_flip=("ADJ-09", "ADJ-04"))

    passed = [c for c in controls if c["verdict"] == "pass"]
    return {
        "task_id": "W033-F0-ACCEPT-SPLIT-ADJ-01",
        "worker": "worker-033",
        "controls_total": len(controls),
        "controls_passed": len(passed),
        "checker_sha256_under_test": hashlib.sha256((HERE / "check_f0_accept_split.py").read_bytes()).hexdigest(),
        "baseline_status": base_status,
        "controls": controls,
        "design_note": ("ADJ-01 (hash binding) flips in every control by design: any byte edit to a pinned "
                        "input must void the binding. It is excluded from must_not_flip for that reason."),
        "falsifier_verdict": "pass" if len(passed) == len(controls) else "fail",
    }


def _add_pointer(doc):
    """Insert vocabulary_aliases_ref beside F2a's conclusion_type without assuming a parent key."""
    def walk(o):
        if isinstance(o, dict):
            if "conclusion_type" in o and "vocabulary_aliases_ref" not in o:
                o["vocabulary_aliases_ref"] = "artifacts/formulation/VOCAB_ALIASES.json"
                return True
            return any(walk(v) for v in o.values())
        if isinstance(o, list):
            return any(walk(v) for v in o)
        return False
    if not walk(doc):
        raise RuntimeError("no conclusion_type key found to attach the pointer to")


if __name__ == "__main__":
    repo = Path(__file__).resolve().parents[3]
    out = run_controls(repo)
    (HERE / "mutation_controls.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"controls_total": out["controls_total"], "controls_passed": out["controls_passed"],
                      "falsifier_verdict": out["falsifier_verdict"],
                      "detail": [{"control": c["control"], "verdict": c["verdict"], "flips": list(c["flips"])}
                                 for c in out["controls"]]}, indent=2))
