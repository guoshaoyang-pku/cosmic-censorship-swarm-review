#!/usr/bin/env python3
"""W039-F2A-EXTFREEZE-VERIFY-01 — independent, non-author verification of the
F2a extension-predicate freeze repair specification W047-F2A-EXT-FREEZE-SPEC-02.

Class AF-SCC-C2-VAC-GEN · node F2a · gate G-FORM · actor worker-039.

What this checks (no worker-047 code is imported; the spec is re-executed):
  P1  all pinned inputs re-measured == declared pins (T0)
  P2  every one of the five declared old_text anchors occurs exactly once in live bytes
  P3  rebuilding live bytes from the spec's five (old_text -> new_text) pairs reproduces
      the author's sandbox candidate byte-for-byte
  P4  the unified diff artifact agrees with the live->candidate transition
  P5  the parsed-YAML structural diff is EXACTLY the three declared leaf paths
  P6  my own six axis detectors: baseline 0/6 resolved, candidate 6/6 resolved
  P7  post-repair invariants hold in the intended (author-instrument) reading, and the
      literal reading of spec invariant #8 is measured and reported (see findings)
  P8  six single-axis mutants discriminate; no-op control does not move the axis vector
  P9  degenerate always-resolve / always-unresolve detectors differ from measured vectors
  P10 canonical structural gate (check_class_schema.py) does not regress live -> candidate
  P11 author's report.json/MANIFEST.json cross-check (sha, counts, changed paths)
  P12 all pins byte-stable across the run (T1); zero canonical drift

Exit codes: 0 = SPEC_EXECUTABLE_AND_VERIFIED (findings may be non-blocking),
            1 = SPEC_REVISE (a blocking check failed), 2 = control failure,
            3 = pin drift / precondition failure.
Writes only inside its own --out directory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

# ---------------------------------------------------------------- declared pins
DECLARED = {
    "schemas/af_scc_c2_vacuum.yaml":
        "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_scc_c0_vacuum.yaml":
        "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "artifacts/formulation/FROZEN.json":
        "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "research_map/formulation_taxonomy.yaml":
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
}
SPEC_DIR = "artifacts/worker-047/f2a_ext_freeze_spec"
SPEC = f"{SPEC_DIR}/repair_spec.json"
CAND = f"{SPEC_DIR}/sandbox/root/schemas/af_scc_c2_vacuum.yaml"
PATCH = f"{SPEC_DIR}/sandbox/af_scc_c2_vacuum.repair.patch"
AUTHOR_REPORT = f"{SPEC_DIR}/report.json"
AUTHOR_MANIFEST = f"{SPEC_DIR}/MANIFEST.json"
GATE = "artifacts/formulation/tools/check_class_schema.py"
FROZEN_CAND_PIN = "schemas/af_scc_c2_vacuum.yaml"

EXPECTED_CHANGED = [
    "extension_predicate.definition",
    "falsifier.tier_1.witness_type",
    "topology.extension_topology",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def flatten(obj, prefix=""):
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(flatten(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(flatten(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = json.dumps(obj, sort_keys=True)
    return out


def clause(defn: str, letter: str) -> str:
    m = re.search(r"\(" + letter + r"\)(.*?)(?=\([a-z]\)|$)", defn, re.S)
    return m.group(1).strip() if m else ""


CATEGORY_RE = re.compile(r"(SMOOTH|C-infinity|C\^?\\?infty|C2)(?=[^.]{0,90}4-manifold)")


def category_token(text: str):
    m = CATEGORY_RE.search(text or "")
    return m.group(1) if m else None


def axes(doc, f2b) -> dict:
    """Six independent axis detectors derived from the spec's own defect statement."""
    ep = doc["extension_predicate"]
    defn = ep["definition"]
    c = clause(defn, "c")
    f = clause(defn, "f")
    a = clause(defn, "a")
    topo = str(doc["topology"].get("extension_topology", ""))
    wit = str((doc.get("falsifier") or {}).get("tier_1", {}).get("witness_type", ""))
    f2b_c = clause(f2b["extension_predicate"]["definition"], "c")
    f2b_top = str(f2b["topology"].get("extension_topology", ""))
    f2b_wit = str((f2b.get("falsifier") or {}).get("tier_1", {}).get("witness_type", ""))
    tok_a1 = "C-infinity" if re.search(r"C-?infinity", a, re.I) else None
    tok_a2 = category_token(c)
    tok_a4 = category_token(topo)
    return {
        "A1_iota_differentiability_class":
            bool(tok_a1) and "isometric embedding" in a,
        "A2_Mprime_manifold_category":
            bool(tok_a2),
        "A3_clause_f_interior_future":
            ("int(" in f) and ("non-empty" in f.lower()) and bool(re.search(r"p in int\(", f)),
        "A4_extension_topology_category":
            bool(tok_a4),
        "A5_witness_freezes_same_class":
            ("SMOOTH" in wit) and bool(re.search(r"C-?infinity isometric embedding", wit, re.I))
            and ("interior future point" in wit),
        "A6_sibling_category_uniformity":
            (tok_a1 == "C-infinity" and bool(re.search(r"C-?infinity", f2b_wit, re.I))
             and tok_a2 == category_token(f2b_c) and tok_a4 == category_token(f2b_top)),
        # raw tokens recorded for the report
        "_tokens": {"iota": tok_a1, "Mprime": tok_a2, "ext_topology": tok_a4,
                    "f2b_Mprime": category_token(f2b_c),
                    "f2b_ext_topology": category_token(f2b_top)},
    }


def resolved(ax: dict) -> dict:
    return {k: v for k, v in ax.items() if not k.startswith("_")}


def invariants(doc, text: str) -> dict:
    concl = json.dumps(doc.get("conclusion", {}))
    il = doc.get("implication_ledger", {})
    chain = str(il.get("extension_class_containment", ""))
    anti = json.dumps(doc.get("anti_scope", {}))
    literal = text.count("C0 or C2")
    in_anti = anti.count("C0 or C2")
    return {
        "frozen_regularity_is_C2": doc["extension_predicate"].get("frozen_regularity") == "C2",
        "frozen_equation_is_classical_ricci":
            doc["extension_predicate"].get("frozen_equation_concept") == "classical_ricci",
        "clause_d_still_C2_Lorentzian": "C2 Lorentzian" in clause(doc["extension_predicate"]["definition"], "d"),
        "conclusion_type_unchanged":
            doc["conclusion"].get("conclusion_type") == "scc_c2_future_inextendibility",
        "genericity_kind_unchanged": doc.get("genericity", {}).get("kind") == "residual_comeager",
        "containment_chain_unchanged":
            chain.startswith("E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0"),
        "no_wcc_predicate_in_conclusion":
            ("visible" not in concl.lower()) and ("I^+" not in concl),
        "composite_C0_or_C2_only_in_prohibitions": literal - in_anti == 0,
        "literal_spec_invariant_8_zero_anywhere": literal == 0,
        "_composite_token_total": literal,
        "_composite_token_in_anti_scope": in_anti,
    }


def apply_sites(live_text: str, sites: list) -> tuple:
    out = live_text
    counts = {}
    for s in sites:
        old, new = s["old_text"], s["new_text"]
        n = out.count(old)
        counts[s["site_id"]] = n
        if n == 1:
            out = out.replace(old, new)
    return out, counts


def mutate(live_text: str, sites: list, skip: set) -> str:
    return apply_sites(live_text, [s for s in sites if s["site_id"] not in skip])[0]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[3]
    out_dir = Path(args.out).resolve() if args.out else Path(__file__).resolve().parent
    out_dir.mkdir(parents=True, exist_ok=True)

    checks = {}
    problems = []
    findings = []

    def check(cid, status, detail=None):
        checks[cid] = {"status": status, "detail": detail or {}}
        if status == "fail":
            problems.append(cid)
        return status == "pass"

    # ---- P1 pins T0
    pins_start = {}
    for rel, want in DECLARED.items():
        got = sha256(root / rel)
        pins_start[rel] = {"measured": got, "declared": want, "match": got == want}
    p1 = all(v["match"] for v in pins_start.values())
    check("P1_start_pins_match_declared", "pass" if p1 else "fail", pins_start)
    if not p1:
        report = {"verdict": "PIN_DRIFT_AT_START", "checks": checks}
        (out_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        return 3

    spec = json.loads((root / SPEC).read_text())
    sites = spec["sites"]
    live_text = (root / "schemas/af_scc_c2_vacuum.yaml").read_text()
    cand_text = (root / CAND).read_text()
    live = yaml.safe_load(live_text)
    cand = yaml.safe_load(cand_text)
    f2b = yaml.safe_load((root / "schemas/af_scc_c0_vacuum.yaml").read_text())

    # ---- P2 anchors
    rebuilt, counts = apply_sites(live_text, sites)
    anchor_ok = all(v == 1 for v in counts.values()) and len(counts) == 5
    check("P2_five_anchors_unique_and_applied", "pass" if anchor_ok else "fail",
          {"sites": counts, "expected_sites": 5})

    # ---- P3 byte reconstruction
    recon_sha = hashlib.sha256(rebuilt.encode()).hexdigest()
    cand_sha = sha256(root / CAND)
    p3 = rebuilt == cand_text
    check("P3_spec_reproduces_author_candidate_bytes", "pass" if p3 else "fail",
          {"reconstructed_sha256": recon_sha, "author_candidate_sha256": cand_sha,
           "declared_in_manifest": json.loads((root / AUTHOR_MANIFEST).read_text())
           ["files"][f"sandbox/root/{FROZEN_CAND_PIN}"]["sha256"]})

    # ---- P4 patch artifact consistency
    patch_txt = (root / PATCH).read_text()
    minus = [l[1:] for l in patch_txt.splitlines() if l.startswith("-") and not l.startswith("---")]
    plus = [l[1:] for l in patch_txt.splitlines() if l.startswith("+") and not l.startswith("+++")]
    p4 = all(live_text.count(l) == 1 for l in minus) and all(cand_text.count(l) == 1 for l in plus)
    check("P4_patch_minus_lines_from_live_plus_lines_in_candidate", "pass" if p4 else "fail",
          {"minus_lines": len(minus), "plus_lines": len(plus),
           "minus_all_unique_in_live": all(live_text.count(l) == 1 for l in minus),
           "plus_all_unique_in_candidate": all(cand_text.count(l) == 1 for l in plus)})

    # ---- P5 structural diff
    fl, fc = flatten(live), flatten(cand)
    changed = sorted(k for k in set(fl) | set(fc) if fl.get(k) != fc.get(k))
    p5 = changed == EXPECTED_CHANGED
    check("P5_structural_diff_is_exactly_three_declared_leaves", "pass" if p5 else "fail",
          {"changed_leaf_paths": changed, "expected": EXPECTED_CHANGED})

    # ---- P6 axes
    ax_live, ax_cand = axes(live, f2b), axes(cand, f2b)
    rl, rc = resolved(ax_live), resolved(ax_cand)
    p6 = (sum(rl.values()) == 0) and (sum(rc.values()) == 6)
    check("P6_axes_baseline_0_of_6_candidate_6_of_6", "pass" if p6 else "fail",
          {"baseline_resolved": sum(rl.values()), "candidate_resolved": sum(rc.values()),
           "baseline": rl, "candidate": rc, "tokens": ax_cand["_tokens"]})

    # ---- P7 invariants
    inv = invariants(cand, cand_text)
    intended = {k: v for k, v in inv.items() if not k.startswith("_")}
    p7 = all(v for k, v in intended.items()
             if k != "literal_spec_invariant_8_zero_anywhere")
    check("P7_post_repair_invariants_intended_reading", "pass" if p7 else "fail", intended)
    if not inv["literal_spec_invariant_8_zero_anywhere"]:
        findings.append({
            "id": "W039-EFV-F01",
            "severity": "minor_documentation",
            "blocking": False,
            "statement": ("repair_spec.json invariant_that_must_hold_after_repair[7] reads "
                          "'no C0 or C2 composite token appears anywhere in the file'; the "
                          "repaired bytes contain exactly one such token (and the live bytes "
                          "too), at anti_scope.phrases_that_are_not_this_class[0], where it is "
                          "the prohibited composite regularity this class must not be conflated "
                          "with. The author's own instrument checks the intended confined form "
                          "('only in prohibitions'), and README.md states that form, so this is "
                          "spec-prose over-strong, not a byte defect."),
            "measured": {"literal_occurrences": inv["_composite_token_total"],
                         "in_anti_scope": inv["_composite_token_in_anti_scope"],
                         "outside_anti_scope": inv["_composite_token_total"] - inv["_composite_token_in_anti_scope"]},
            "repair_reading": ("owner should read that invariant as 'no C0 or C2 composite token "
                               "outside anti_scope' before applying; deleting the anti_scope entry "
                               "to satisfy the literal text would be wrong"),
        })

    # ---- P8 mutants
    mutants = {}
    all_ids = [s["site_id"] for s in sites]
    axis_of_site = {"S1": "A1_iota_differentiability_class",
                    "S2": "A2_Mprime_manifold_category",
                    "S3": "A3_clause_f_interior_future",
                    "S4": "A4_extension_topology_category",
                    "S5": "A5_witness_freezes_same_class"}
    ok = True
    for sid in all_ids:
        mt = mutate(live_text, sites, {sid})
        mr = resolved(axes(yaml.safe_load(mt), f2b))
        flipped = not mr[axis_of_site[sid]]
        mutants[sid] = {"axis": axis_of_site[sid], "axis_unresolved_after_revert": flipped,
                        "resolved_count": sum(mr.values())}
        ok = ok and flipped
    noop = resolved(axes(yaml.safe_load(mutate(live_text, sites, set())), f2b))
    mutants["noop_control"] = {"resolved_count": sum(noop.values()),
                               "all_resolved": all(noop.values())}
    ok = ok and all(noop.values())
    check("P8_mutants_discriminate_and_noop_control_clean", "pass" if ok else "fail", mutants)

    # ---- P9 degenerate detectors
    deg = {"always_resolve_differs_from_baseline": any(rl.values()) is False,
           "always_unresolve_differs_from_candidate": all(rc.values()) is True}
    p9 = all(deg.values())
    check("P9_degenerate_detector_controls", "pass" if p9 else "fail", deg)

    # ---- P10 canonical gate, live vs candidate
    gate_out = {}
    for label, path in (("live", root / "schemas/af_scc_c2_vacuum.yaml"),
                        ("candidate", root / CAND)):
        r = subprocess.run([sys.executable, str(root / GATE), "--json", str(path)],
                           capture_output=True, text=True, cwd=str(root))
        s = r.stdout.strip()
        i = s.find("{")
        try:
            d, _ = json.JSONDecoder().raw_decode(s[i:]) if i >= 0 else ({}, 0)
        except Exception:
            d = {}
        gate_out[label] = {"exit": r.returncode, "verdict": d.get("verdict"),
                           "failed_rules": d.get("failed_rules", []),
                           "failure_count": len(d.get("failures", []))}
    p10 = (gate_out["candidate"]["exit"] == 0
           and gate_out["candidate"]["verdict"] == "pass"
           and gate_out["candidate"]["failed_rules"] == []
           and gate_out["live"] == gate_out["candidate"])
    check("P10_structural_gate_no_regression", "pass" if p10 else "fail", gate_out)

    # ---- P11 author cross-check
    rep = json.loads((root / AUTHOR_REPORT).read_text())
    man = json.loads((root / AUTHOR_MANIFEST).read_text())
    xc = {
        "author_verdict": rep.get("verdict"),
        "author_counts": rep.get("counts"),
        "author_changed_paths": rep.get("structural_diff", {}).get("changed_leaf_paths"),
        "author_candidate_sha": man["files"][f"sandbox/root/{FROZEN_CAND_PIN}"]["sha256"],
        "my_candidate_sha": cand_sha,
        "author_baseline_resolved": rep.get("counts", {}).get("axes_resolved_baseline"),
        "author_repaired_resolved": rep.get("counts", {}).get("axes_resolved_repaired"),
        "author_problems": rep.get("problems"),
    }
    p11 = (xc["author_candidate_sha"] == cand_sha
           and xc["author_baseline_resolved"] == 0 and xc["author_repaired_resolved"] == 6
           and xc["author_problems"] == [] and xc["author_changed_paths"] == EXPECTED_CHANGED)
    check("P11_author_report_cross_check", "pass" if p11 else "fail", xc)

    # ---- P12 pins T1
    pins_end = {rel: {"measured": sha256(root / rel), "match": sha256(root / rel) == want}
                for rel, want in DECLARED.items()}
    p12 = all(v["match"] for v in pins_end.values())
    check("P12_end_pins_stable", "pass" if p12 else "fail", pins_end)

    # ---- verdict
    blocking = [c for c, v in checks.items() if v["status"] == "fail"]
    if any(c in blocking for c in ("P1_start_pins_match_declared", "P12_end_pins_stable")):
        verdict, code = "PIN_DRIFT", 3
    elif blocking:
        verdict, code = "SPEC_REVISE", 1
    else:
        verdict, code = "SPEC_EXECUTABLE_AND_VERIFIED", 0

    report = {
        "schema": "w039-f2a-extfreeze-verify/v1",
        "task_id": "W039-F2A-EXTFREEZE-VERIFY-01",
        "actor": "worker-039",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "node_id": "F2a",
        "gate": "G-FORM",
        "target": {"task_id": spec["task_id"], "spec": SPEC, "spec_sha256": sha256(root / SPEC),
                   "candidate": CAND, "candidate_sha256": cand_sha,
                   "author_report": AUTHOR_REPORT, "author_report_sha256": sha256(root / AUTHOR_REPORT),
                   "author_manifest": AUTHOR_MANIFEST,
                   "author_manifest_sha256": sha256(root / AUTHOR_MANIFEST)},
        "authority_note": ("worker deliverable: independent non-author verification of a repair "
                           "specification. It does not edit schemas/af_scc_c2_vacuum.yaml, does "
                           "not set node status, validation_status=passed or any gate verdict, and "
                           "does not commission the repair. The owner (astra-lead-formulation) "
                           "applies or rejects; the r3 F2a cards remain pinned to e9a27996."),
        "pins_start": pins_start,
        "checks": checks,
        "problems": problems,
        "findings": findings,
        "verdict": verdict,
        "counts": {"checks": len(checks),
                   "pass": sum(1 for v in checks.values() if v["status"] == "pass"),
                   "fail": len(blocking),
                   "findings": len(findings)},
        "next_falsifier": ("Re-run this verifier on the same pinned bytes: the verification is "
                           "falsified if (a) the spec no longer rebuilds the author's candidate "
                           "byte-for-byte, (b) the structural diff is not exactly the three declared "
                           "leaves, (c) my baseline/candidate axis counts are not 0/6 and 6/6, "
                           "(d) any single-site revert fails to flip its axis, (e) the canonical "
                           "structural gate regresses live->candidate, or (f) any pinned input "
                           "moves. A repair applied at a different hash voids the pins and requires "
                           "a re-run."),
        "non_claims": [
            "not a schema review verdict; no gate verdict; no node status",
            "verifies the spec's executability, confinement and sibling consistency, not the "
            "mathematical optimality of option A over option B",
            "does not certify the truth of the F2b precedent; it checks that the precedent tokens "
            "cited by the spec are present at the pinned F2b bytes",
        ],
    }
    payload = json.dumps({k: report[k] for k in ("checks", "findings", "problems", "verdict",
                                                 "counts", "pins_start", "target")},
                         sort_keys=True)
    report["deterministic_payload_sha256"] = hashlib.sha256(payload.encode()).hexdigest()
    (out_dir / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    print(f"VERDICT: {verdict}  checks={report['counts']['checks']} "
          f"pass={report['counts']['pass']} fail={report['counts']['fail']} "
          f"findings={report['counts']['findings']}")
    for cid, v in checks.items():
        print(f"  {v['status']:4} {cid}")
    for f in findings:
        print(f"  FINDING {f['id']} [{f['severity']}] {f['statement'][:100]}...")
    return code


if __name__ == "__main__":
    sys.exit(main())
