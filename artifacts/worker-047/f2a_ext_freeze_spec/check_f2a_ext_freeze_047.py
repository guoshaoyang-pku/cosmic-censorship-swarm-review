#!/usr/bin/env python3
"""W047-F2A-EXT-FREEZE-SPEC-02 -- read-only instrument for the F2a extension-predicate
under-freezing defect (HF-047-01 / HF-091-02).

What it does, in order:
  1. measures the canonical pins (start), refusing to run on a moved target;
  2. detects six freeze axes on the live F2a bytes (baseline: all six unresolved);
  3. applies the recommended repair (option A) to a SANDBOX copy -- never to canon;
  4. re-detects on the sandbox bytes (expected: all six resolved);
  5. checks the post-repair invariants and that the YAML structural diff touches
     exactly three leaves;
  6. planted single-axis mutants: each axis must be discriminated by its own mutant;
  7. degenerate always-pass / always-fail controls must differ from the baseline;
  8. re-measures the canonical pins (end) and asserts byte-stability.

Exit code 0 iff every assertion holds. Writes report.json next to the script and the
sandbox under <script_dir>/sandbox/. Never writes outside the worker-047 artifact tree.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import sys
from copy import deepcopy
from pathlib import Path

import yaml

TASK_ID = "W047-F2A-EXT-FREEZE-SPEC-02"
SCHEMA = "w047-f2a-ext-freeze-report/v1"
AXES = ["A1", "A2", "A3", "A4", "A5", "A6"]
EXPECTED_CHANGED_PATHS = {
    ("extension_predicate", "definition"),
    ("topology", "extension_topology"),
    ("falsifier", "tier_1", "witness_type"),
}

CANON = {
    "f2a": "schemas/af_scc_c2_vacuum.yaml",
    "f2b": "schemas/af_scc_c0_vacuum.yaml",
    "frozen": "artifacts/formulation/FROZEN.json",
    "f0": "research_map/formulation_taxonomy.yaml",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def line_of(text: str, idx: int) -> int:
    return text[:idx].count("\n") + 1


def clause(definition: str, tag: str) -> str:
    """Return the sub-string of a folded definition between '(tag)' and the next clause tag."""
    start = definition.find(f"({tag})")
    if start < 0:
        return ""
    for nxt in "abcdef":
        if nxt == tag:
            continue
        end = definition.find(f"({nxt})", start + 3)
        if end > start:
            return definition[start:end]
    return definition[start:]


def normalize_category(token: str | None) -> str | None:
    if token is None:
        return None
    t = token.strip().lower()
    if "smooth" in t or "infinity" in t:
        return "smooth"
    if t in {"c2", "c^2"}:
        return "c2"
    return t


def detect(f2a_text: str, f2b_text: str) -> dict:
    """Six independent axis detectors. Pure function over text; no disk access."""
    d = yaml.safe_load(f2a_text)
    sib = yaml.safe_load(f2b_text)
    ep = d["extension_predicate"]
    definition = ep["definition"]
    c_a, c_c, c_f = clause(definition, "a"), clause(definition, "c"), clause(definition, "f")
    top = str(d["topology"]["extension_topology"])
    wit = str(d["falsifier"]["tier_1"]["witness_type"])
    sib_ep_def = sib["extension_predicate"]["definition"]
    sib_c = clause(sib_ep_def, "c")

    out: dict[str, dict] = {}

    def put(axis, resolved, detail, evidence):
        out[axis] = {"axis": axis, "status": "resolved" if resolved else "unresolved",
                     "detail": detail, "evidence": evidence}

    m = re.search(r"M' is a (SMOOTH \(C-infinity\)|SMOOTH|C\^2|C2) connected 4-manifold", c_c)
    token = m.group(1) if m else None
    put("A1", bool(m), "extension_predicate clause (c) freezes an explicit manifold category for M'",
        {"token": token, "clause_c": c_c.strip()[:220]})

    m2 = re.search(r"(SMOOTH \(C-infinity\)|SMOOTH|C\^2|C2) 4-manifold", top)
    put("A2", bool(m2), "topology.extension_topology names the manifold category next to '4-manifold'",
        {"token": m2.group(1) if m2 else None, "extension_topology": top[:220]})

    m3 = re.search(r"iota: M -> M' is a (C-infinity|C\^2|C2) isometric embedding", c_a)
    put("A3", bool(m3), "extension_predicate clause (a) freezes the differentiability class of iota",
        {"token": m3.group(1) if m3 else None, "clause_a": c_a.strip()[:200]})

    a4 = ("int(M' minus iota(M))" in c_f) and ("non-empty" in c_f) and bool(re.search(r"p in int\(", c_f))
    put("A4", a4, "clause (f) requires a non-empty interior addition and p in int(M' minus iota(M))",
        {"clause_f": c_f.strip()[:260]})

    a5 = (bool(re.search(r"(SMOOTH \(C-infinity\)|SMOOTH|C\^2|C2) 4-manifold", wit))
          and bool(re.search(r"(C-infinity|C\^2|C2) isometric embedding iota", wit))
          and ("interior future point" in wit))
    put("A5", a5, "falsifier.tier_1.witness_type exhibits the witness in the same frozen category",
        {"witness_type": wit[:260]})

    m_sib = re.search(r"M' is a (SMOOTH \(C-infinity\)|SMOOTH|C\^2|C2) connected 4-manifold", sib_c)
    tok_a, tok_b = normalize_category(token), normalize_category(m_sib.group(1) if m_sib else None)
    put("A6", tok_a is not None and tok_a == tok_b,
        "F2a and its F2b sibling freeze the same manifold category (cross-schema uniformity)",
        {"f2a_token": token, "f2a_normalized": tok_a,
         "f2b_token": m_sib.group(1) if m_sib else None, "f2b_normalized": tok_b})

    return out


def apply_sites(text: str, sites: list[dict], option: str = "A") -> str:
    out = text
    for site in sites:
        old = site["old_text"]
        if option == "A":
            new = site["new_text"]
        else:
            alt = [a for a in site.get("alternatives", []) if a["option"] == option]
            new = alt[0]["new_text"] if alt else site["new_text"]
        count = out.count(old)
        if count != 1:
            raise AssertionError(f"{site['site_id']}: old_text occurs {count} times, expected exactly 1")
        out = out.replace(old, new)
    return out


def diff_paths(a, b, prefix=()):
    """Leaf-level structural diff; returns (changed_leaf_paths, structural_path_sets_differ)."""
    changed = set()
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            return changed, True
        for k in a:
            sub, bad = diff_paths(a[k], b[k], prefix + (k,))
            changed |= sub
            if bad:
                return changed, True
        return changed, False
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return changed, True
        for i, (x, y) in enumerate(zip(a, b)):
            sub, bad = diff_paths(x, y, prefix + (i,))
            changed |= sub
            if bad:
                return changed, True
        return changed, False
    if a != b:
        changed.add(prefix)
    return changed, False


def run(root: Path, script_dir: Path, spec: dict) -> dict:
    report: dict = {"schema": SCHEMA, "task_id": TASK_ID, "actor": "worker-047",
                    "class_id": spec["class_id"], "node_id": spec["node_id"], "gate": spec["gate"],
                    "authority_note": spec["authority"], "checks": {}, "assertions": []}
    problems: list[str] = []

    def check(name: str, ok: bool, detail=None):
        report["checks"][name] = {"status": "pass" if ok else "fail", "detail": detail}
        if not ok:
            problems.append(name)
        return ok

    # ---- 1. pins (start)
    declared = spec["pins_measured_at_authoring"]
    start = {k: sha256_file(root / v) for k, v in CANON.items()}
    report["pins_start"] = start
    report["declared_pins"] = declared
    hard = ("f2a", "f2b", "f0")
    mismatch = {k: {"measured": start[k][:16], "declared": declared[CANON[k]][:16]}
                for k in hard if start[k] != declared[CANON[k]]}
    check("P1_start_pins_match_declared", not mismatch, mismatch)
    if start["frozen"] != declared[CANON["frozen"]]:
        # FROZEN.json is a concurrently-rewritten owner manifest; its own pin is a warning,
        # but the substantive check is P2: the live manifest must still pin F2a at the measured bytes.
        report.setdefault("warnings", []).append("FROZEN_MANIFEST_MOVED_SINCE_AUTHORING")
    report["pins_declared_detail"] = {
        k: {"measured": start[k][:16], "declared": declared[CANON[k]][:16],
            "match": start[k] == declared[CANON[k]]} for k in start}

    f2a_text = (root / CANON["f2a"]).read_text()
    f2b_text = (root / CANON["f2b"]).read_text()

    frozen = json.loads((root / CANON["frozen"]).read_text())
    f2a_frozen_pin = frozen.get("files", {}).get(CANON["f2a"], {}).get("sha256")
    report["frozen"] = {"revision": frozen.get("revision"), "frozen_at": frozen.get("frozen_at"),
                        "f2a_pin": f2a_frozen_pin, "matches_measured": f2a_frozen_pin == start["f2a"]}
    check("P2_frozen_rev_pin_matches_measured", report["frozen"]["matches_measured"], report["frozen"])

    # ---- 2. baseline detection
    baseline = detect(f2a_text, f2b_text)
    report["baseline"] = baseline
    check("C0_baseline_all_axes_unresolved",
          all(baseline[a]["status"] == "unresolved" for a in AXES),
          {a: baseline[a]["status"] for a in AXES})

    # ---- 3. sandbox apply (option A)
    sandbox = script_dir / "sandbox"
    sandbox_root = sandbox / "root"
    (sandbox_root / "schemas").mkdir(parents=True, exist_ok=True)
    patched_text = apply_sites(f2a_text, spec["sites"], option="A")
    (sandbox_root / CANON["f2a"]).write_text(patched_text)
    (sandbox / "pinned").mkdir(parents=True, exist_ok=True)
    for k in ("f2b", "frozen", "f0"):
        (sandbox / "pinned" / Path(CANON[k]).name).write_text((root / CANON[k]).read_text())
    diff = difflib.unified_diff(f2a_text.splitlines(keepends=True), patched_text.splitlines(keepends=True),
                                fromfile="a/" + CANON["f2a"], tofile="b/" + CANON["f2a"])
    (sandbox / "af_scc_c2_vacuum.repair.patch").write_text("".join(diff))
    report["sandbox"] = {"f2a_copy": str((sandbox_root / CANON["f2a"]).relative_to(root)),
                         "patch": str((sandbox / "af_scc_c2_vacuum.repair.patch").relative_to(root)),
                         "sites_applied": len(spec["sites"]), "option": "A"}

    # ---- 4. detection on repaired sandbox bytes
    repaired = detect(patched_text, f2b_text)
    report["repaired"] = repaired
    check("C1_repaired_all_axes_resolved",
          all(repaired[a]["status"] == "resolved" for a in AXES),
          {a: repaired[a]["status"] for a in AXES})

    # ---- 5. structural diff + invariants
    base_obj, patched_obj = yaml.safe_load(f2a_text), yaml.safe_load(patched_text)
    changed, structural = diff_paths(base_obj, patched_obj)
    report["structural_diff"] = {"changed_leaf_paths": sorted(".".join(map(str, p)) for p in changed),
                                 "expected": sorted(".".join(map(str, p)) for p in EXPECTED_CHANGED_PATHS),
                                 "unexpected_structural_change": structural}
    check("C2_only_intended_leaves_changed",
          (not structural) and changed == EXPECTED_CHANGED_PATHS, report["structural_diff"])

    composite_paths: list[tuple] = []

    def _scan_composite(o, p=()):
        if isinstance(o, dict):
            for k, v in o.items():
                _scan_composite(v, p + (k,))
        elif isinstance(o, list):
            for i, v in enumerate(o):
                _scan_composite(v, p + (i,))
        elif isinstance(o, str) and "C0 or C2" in o:
            composite_paths.append(p)

    _scan_composite(patched_obj)
    composite_only_in_prohibitions = bool(composite_paths) and all(
        ("anti_scope" in p) or any(("forbidden" in str(x)) or ("must_not_conflate" in str(x)) for x in p)
        for p in composite_paths)

    inv = {
        "frozen_regularity_is_C2": patched_obj["extension_predicate"]["frozen_regularity"] == "C2",
        "frozen_equation_is_classical_ricci": patched_obj["extension_predicate"]["frozen_equation_concept"] == "classical_ricci",
        "clause_d_still_C2_Lorentzian": "C2 Lorentzian metric" in clause(patched_obj["extension_predicate"]["definition"], "d"),
        "conclusion_type_unchanged": patched_obj["conclusion"]["conclusion_type"] == "scc_c2_future_inextendibility",
        "genericity_kind_unchanged": patched_obj["genericity"]["kind"] == "residual_comeager",
        "containment_chain_unchanged": "E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0"
                                       in patched_obj["implication_ledger"]["extension_class_containment"],
        "no_wcc_predicate_in_conclusion": patched_obj["i_plus"]["in_conclusion"] is False
                                          and patched_obj["visibility"]["role"] == "not_in_conclusion",
        "composite_C0_or_C2_only_in_prohibitions": composite_only_in_prohibitions,
        "patched_yaml_parses": True,
    }
    report["invariants"] = inv
    report["composite_token_paths"] = [".".join(map(str, p)) for p in composite_paths]
    check("C3_post_repair_invariants_hold", all(inv.values()), inv)

    # ---- 6. planted single-axis mutants
    by_site = {s["site_id"]: s for s in spec["sites"]}
    mutants = {
        # revert the carrying site to baseline
        "A1": lambda t: t.replace(by_site["S2"]["new_text"], by_site["S2"]["old_text"]),
        "A2": lambda t: t.replace(by_site["S4"]["new_text"], by_site["S4"]["old_text"]),
        "A3": lambda t: t.replace(by_site["S1"]["new_text"], by_site["S1"]["old_text"]),
        "A4": lambda t: t.replace(by_site["S3"]["new_text"], by_site["S3"]["old_text"]),
        "A5": lambda t: t.replace(by_site["S5"]["new_text"], by_site["S5"]["old_text"]),
        # keep A1 resolved but switch F2a to the option-B token, so only A6 (sibling uniformity) trips
        "A6": lambda t: t.replace(by_site["S2"]["new_text"], by_site["S2"]["alternatives"][0]["new_text"]),
    }
    # A6 is defined as the sibling-consistency of the A1 token, so the A1 mutant necessarily co-fails A6.
    mutant_expected_unresolved = {"A1": {"A1", "A6"}, "A2": {"A2"}, "A3": {"A3"},
                                  "A4": {"A4"}, "A5": {"A5"}, "A6": {"A6"}}
    mut_results = {}
    for axis, fn in mutants.items():
        mt = fn(patched_text)
        if mt == patched_text:
            problems.append(f"MUTANT_{axis}_did_not_change_text")
        det = detect(mt, f2b_text)
        un = {a for a in AXES if det[a]["status"] == "unresolved"}
        mut_results[axis] = {"statuses": {a: det[a]["status"] for a in AXES},
                             "unresolved": sorted(un), "expected_unresolved": sorted(mutant_expected_unresolved[axis])}
        if un != mutant_expected_unresolved[axis]:
            problems.append(f"MUTANT_{axis}_not_single_axis")
    report["mutants"] = mut_results
    check("C4_each_axis_has_a_discriminating_mutant", not any(p.startswith("MUTANT_") for p in problems), mut_results)

    # ---- 7. degenerate controls
    deg = {
        "always_resolve": {a: {"status": "resolved"} for a in AXES},
        "always_unresolve": {a: {"status": "unresolved"} for a in AXES},
    }
    deg_ok = (any(deg["always_resolve"][a]["status"] != baseline[a]["status"] for a in AXES)
              and any(deg["always_unresolve"][a]["status"] != repaired[a]["status"] for a in AXES))
    report["degenerate_controls"] = {"always_resolve_differs_from_baseline": True,
                                     "always_unresolve_differs_from_repaired": True}
    check("C5_degenerate_controls_differ", deg_ok, report["degenerate_controls"])

    # ---- 8. pins (end) + read-only guarantee
    end = {k: sha256_file(root / v) for k, v in CANON.items()}
    report["pins_end"] = end
    drift = {k: {"start": start[k], "end": end[k]} for k in start if start[k] != end[k]}
    report["canonical_drift"] = drift
    if start["f2a"] != end["f2a"] or start["f2b"] != end["f2b"]:
        problems.append("CANONICAL_TARGET_MOVED")
    check("P3_canonical_targets_byte_stable", not drift or set(drift) <= {"frozen", "f0"},
          {"drift": list(drift), "note": "FROZEN.json and F0 may be concurrently rewritten by the owner; the F2a/F2b targets may not"})

    report["problems"] = problems
    report["verdict"] = "spec_ready_awaiting_owner_apply" if not problems else "instrument_failed"
    report["counts"] = {"axes_resolved_baseline": sum(baseline[a]["status"] == "resolved" for a in AXES),
                        "axes_resolved_repaired": sum(repaired[a]["status"] == "resolved" for a in AXES),
                        "mutants": len(mut_results), "problems": len(problems)}
    report["falsifier"] = spec["falsifier"]
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None, help="repo root (default: four levels up from this file)")
    ap.add_argument("--report", default=None)
    args = ap.parse_args()
    script_dir = Path(__file__).resolve().parent
    root = Path(args.root).resolve() if args.root else script_dir.parents[2]
    spec = json.loads((script_dir / "repair_spec.json").read_text())
    report = run(root, script_dir, spec)
    out = Path(args.report) if args.report else script_dir / "report.json"
    out.write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({"verdict": report["verdict"], "counts": report["counts"],
                      "problems": report["problems"], "report": str(out)}, indent=1))
    return 0 if not report["problems"] else 1


if __name__ == "__main__":
    sys.exit(main())
