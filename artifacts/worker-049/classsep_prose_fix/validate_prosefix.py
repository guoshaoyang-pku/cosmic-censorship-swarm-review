#!/usr/bin/env python3
"""Validate the worker-049 prose-mode calibration of the class-separation detector.

Task id: W049-CLASSSEP-PROSEFIX-01
Class binding: AF-SCC-C2-VAC-GEN and AF-SCC-C0-VAC-GEN (the C0/C2 separation
axis); the change touches only mode="prose" so every declaration surface is
byte-for-byte unchanged.

Read-only with respect to every canonical path.  All inputs are snapshotted in
this directory and re-measured at the end of the run; a moved pin voids the
binding rather than the result.

Checks
  A  worker-07 27-fixture corpus: canonical vs patched, both must be 17/0/10/0 PASS.
  B  worker-035 control battery (9 positive / 14 negative): patched must be 23/23.
  C  live-map snapshot: patched must clear every claim prose finding the canonical
     module raises, with 0 added; node/group/portfolio-event findings unchanged.
  D  declaration-invariance: canonical and patched declaration-mode findings are
     identical on every worker-07 fixture and on the live snapshot.
  E  mutation controls: 8 live false-positive mechanisms must clear, 8 genuine
     merge assertions must stay flagged.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

PIN_CANONICAL = "c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920"
PIN_SNAPSHOT = "11311ab3600514cd34ca7332714a4aa27b97e4fdc124f29179122e11f844974d"
PIN_W07 = "d69ad58468be16655921dcf0eab9570fa6e7ccaf828558a45d4b306cce3de452"
PIN_W035 = "ef881c3aa6ef392c2068828b02d6645043913a0ff88ab0487264a6b770c5914d"

CANONICAL = ROOT / "research_map" / "class_separation.py"
PATCHED = HERE / "class_separation_prosefix.py"
SNAPSHOT = HERE / "map_snapshot.json"
W07 = HERE / "worker07_results.json"
W035 = HERE / "worker035_controls.json"


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def score_worker07(mod, results: dict):
    """Replicate runtime/bin/classsep_regression.py scoring with `mod`."""
    tp = fn = tn = fp = 0
    rows = []
    for fx in results["fixtures"]:
        fpth = ROOT / fx["fixture_path"]
        if not fpth.exists():
            rows.append({"id": fx["id"], "class": "MISSING"})
            continue
        m = json.loads(fpth.read_text())
        det = mod.findings_for_map(m)
        for g in m.get("groups", []):
            for n in g.get("nodes", []):
                art = n.get("artifact")
                if art and (ROOT / art).is_file():
                    det += mod.findings_for_text((ROOT / art).read_text(errors="replace"),
                                                 f"artifact {art}")
        got, truth = bool(det), bool(fx["is_class_merge"])
        if truth and got:
            tp += 1; cls = "TP"
        elif truth and not got:
            fn += 1; cls = "FN-MISSED"
        elif not truth and got:
            fp += 1; cls = "FP-SPURIOUS"
        else:
            tn += 1; cls = "TN"
        rows.append({"id": fx["id"], "class": cls, "n_findings": len(det)})
    return {"tp": tp, "fn": fn, "tn": tn, "fp": fp, "rows": rows,
            "verdict": "PASS" if fn == 0 and fp == 0 else "DEFECTIVE"}


def declaration_findings(mod, m: dict):
    """Declaration-mode findings only (groups/nodes/portfolio_events)."""
    out = []
    for gi, g in enumerate(m.get("groups", [])):
        out += mod.findings({"direction": g.get("direction"), "class_id": ""},
                            f"groups[{g.get('id', gi)}]")
        for n in g.get("nodes", []):
            out += mod.findings(n, f"node {n.get('id', '?')}")
    for i, ev in enumerate(m.get("portfolio_events", [])):
        if isinstance(ev, dict):
            out += mod.findings(ev, f"portfolio_events[{i}]")
    return out


def claim_findings(mod, m: dict):
    res = {}
    for i, c in enumerate(m.get("claims", [])):
        if isinstance(c, dict):
            f = mod.findings(c, f"claims[{i}]", mode="prose")
            if f:
                res[i] = f
    return res


def text_flags(mod, text: str):
    """Prose-path flags for a bare statement, via a synthetic claim."""
    return mod.findings_for_map({"claims": [{"statement": text, "class_id": "AF-SCC-C2-VAC-GEN"}]})


CLEAR_CONTROLS = [
    ("M1_CASE_LABEL", "The 2 split rows (TC-F0-N14 C0/C2 merge, TC-F0-N15 WCC/SCC merge) need no new class."),
    ("M2_CASE_LABEL_PAREN", "2 SPLIT_REQUIRED (TC-F0-N14 merged C0/C2 regularities; TC-F0-N15 merged WCC/SCC families)."),
    ("M3_NEGATED_NO", "no C0/C2 merge exists at the formal surface"),
    ("M4_NEGATED_NON", "independent C0/C2 non-merge"),
    ("M5_QUOTED", "the same slot carrying 'C0 or C2 are one class' is flagged"),
    ("M6_CROSS_CLAUSE", "the retired merged file; and, measured during the task, the live C2/C0 components moved"),
    ("M7_META_PATTERN", "R1's merge pattern matches only bare C0/C2 composites"),
    ("M8_RATHER_THAN", "a single-frozen-data-class question rather than a C2/C0 merge"),
    ("M9_CASE_LABEL_MERGED", "2 SPLIT_REQUIRED (TC-F0-N14 merged C0/C2 regularities)"),
    ("M10_QUOTED_NEG", "the live false-positive shape '... merged C0/C2 ...' is NOT cleared"),
]
FLAG_CONTROLS = [
    ("G1", "We treat C0 or C2 as one class in the unified schema."),
    ("G2", "C0/C2 are merged into a single class for the vacuum sector."),
    ("G3", "The two regularities C0 and C2 share one schema."),
    ("G4", "C0 or C2 is one class and must be declared as such."),
    ("G5", "We adopt a single schema for C0/C2."),
    ("G6", "C0/C2 merge is our design."),
    ("G7", "The taxonomy treats C0 and C2 as one class."),
    ("G8", "Both classes are one: C0 and C2."),
    ("G9_SPLIT_WORD_ASSERTION", "Despite the earlier split discussion, C0 and C2 are one class in this schema."),
]


def main() -> int:
    pins_before = {
        "research_map/class_separation.py": sha256_file(CANONICAL),
        "artifacts/worker-049/classsep_prose_fix/map_snapshot.json": sha256_file(SNAPSHOT),
        "artifacts/worker-049/classsep_prose_fix/worker07_results.json": sha256_file(W07),
        "artifacts/worker-049/classsep_prose_fix/worker035_controls.json": sha256_file(W035),
    }
    canonical = load_module(CANONICAL, "cs_canonical")
    patched = load_module(PATCHED, "cs_patched")
    results07 = json.loads(W07.read_text())
    controls035 = json.loads(W035.read_text())
    m = json.loads(SNAPSHOT.read_text())

    # A -- worker-07 corpus
    a_can = score_worker07(canonical, results07)
    a_pat = score_worker07(patched, results07)
    check_a = (a_can["verdict"] == "PASS" and a_pat["verdict"] == "PASS"
               and (a_can["tp"], a_can["fn"], a_can["tn"], a_can["fp"]) == (17, 0, 10, 0)
               and (a_pat["tp"], a_pat["fn"], a_pat["tn"], a_pat["fp"]) == (17, 0, 10, 0))

    # B -- worker-035 control battery
    b_rows = []
    b_ok = 0
    for c in controls035["controls"]:
        txt = c["text"]
        expect_flag = c["expect"].startswith("ASSERTION")
        can_flag = bool(text_flags(canonical, txt))
        pat_flag = bool(text_flags(patched, txt))
        ok = pat_flag == expect_flag
        b_ok += int(ok)
        b_rows.append({"id": c["control_id"], "expect": c["expect"],
                       "canonical_flag": can_flag, "patched_flag": pat_flag, "pass": ok})
    check_b = b_ok == len(controls035["controls"]) == 23

    # C -- live snapshot claims
    can_claims = claim_findings(canonical, m)
    pat_claims = claim_findings(patched, m)
    added = sorted(set(pat_claims) - set(can_claims))
    removed = sorted(set(can_claims) - set(pat_claims))
    check_c = (len(added) == 0 and len(pat_claims) == 0 and len(can_claims) > 0)

    # D -- declaration invariance on the whole snapshot
    decl_can = declaration_findings(canonical, m)
    decl_pat = declaration_findings(patched, m)
    check_d = decl_can == decl_pat

    # D2 -- declaration invariance across every worker-07 fixture
    d2_mismatch = []
    for fx in results07["fixtures"]:
        p = ROOT / fx["fixture_path"]
        if not p.exists():
            continue
        fm = json.loads(p.read_text())
        if declaration_findings(canonical, fm) != declaration_findings(patched, fm):
            d2_mismatch.append(fx["id"])
    check_d2 = not d2_mismatch

    # E -- mutation controls
    e_clear = [{"id": cid, "text": txt[:70],
                "canonical_flag": bool(text_flags(canonical, txt)),
                "patched_flag": bool(text_flags(patched, txt)),
                "pass": not bool(text_flags(patched, txt))}
               for cid, txt in CLEAR_CONTROLS]
    e_flag = [{"id": cid, "text": txt[:70],
               "canonical_flag": bool(text_flags(canonical, txt)),
               "patched_flag": bool(text_flags(patched, txt)),
               "pass": bool(text_flags(patched, txt))}
              for cid, txt in FLAG_CONTROLS]
    check_e = all(r["pass"] for r in e_clear + e_flag)

    # F -- audit_evidence.py section-3 simulation on the snapshot
    def audit_section3(mod):
        hard = []
        hard += [f for f in mod.findings_for_map(m) if not str(f).startswith("CLASSSEP-SOFT:")]
        for g in m.get("groups", []):
            for n in g.get("nodes", []):
                art = n.get("artifact")
                p = ROOT / art if art else None
                if p is not None and p.is_file() and p.stat().st_size < 2_000_000:
                    hard += [f for f in mod.findings_for_text(p.read_text(errors="replace"),
                                                              f"{n['id']} artifact {art}")
                             if not str(f).startswith("CLASSSEP-SOFT:")]
        return hard
    f_can = audit_section3(canonical)
    f_pat = audit_section3(patched)
    check_f = (len(f_can) > 0 and len(f_pat) == 0)

    pins_after = {
        "research_map/class_separation.py": sha256_file(CANONICAL),
        "artifacts/worker-049/classsep_prose_fix/map_snapshot.json": sha256_file(SNAPSHOT),
        "artifacts/worker-049/classsep_prose_fix/worker07_results.json": sha256_file(W07),
        "artifacts/worker-049/classsep_prose_fix/worker035_controls.json": sha256_file(W035),
    }
    drifted = [k for k in pins_before if pins_before[k] != pins_after[k]]
    pin_ok = (pins_before["research_map/class_separation.py"] == PIN_CANONICAL
              and pins_before["artifacts/worker-049/classsep_prose_fix/map_snapshot.json"] == PIN_SNAPSHOT
              and pins_before["artifacts/worker-049/classsep_prose_fix/worker07_results.json"] == PIN_W07
              and pins_before["artifacts/worker-049/classsep_prose_fix/worker035_controls.json"] == PIN_W035)

    report = {
        "schema": "worker-049/classsep-prosefix/v1",
        "task_id": "W049-CLASSSEP-PROSEFIX-01",
        "actor": "worker-049",
        "node_id": "A1",
        "gate": "G-AUDIT",
        "class_id": "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "target_finding": "CF-16: CLASSSEP hard failures on claims[*].statement are prose-mode false positives",
        "instrument": {
            "canonical": {"path": "research_map/class_separation.py", "sha256": pins_before["research_map/class_separation.py"]},
            "patched": {"path": "artifacts/worker-049/classsep_prose_fix/class_separation_prosefix.py",
                        "sha256": sha256_file(PATCHED)},
            "patch_scope": "mode='prose' only; declaration-mode code path unchanged",
            "rule_provenance": "artifacts/worker-035/classsep_hardfail_adjudication/adjudicate_hardfailures.py#sha256:ef881c3aa6ef (controls only; no code imported at runtime)",
        },
        "pins": {
            "map_snapshot": {"path": "artifacts/worker-049/classsep_prose_fix/map_snapshot.json",
                             "sha256": pins_before["artifacts/worker-049/classsep_prose_fix/map_snapshot.json"],
                             "updated_at": m.get("updated_at"), "claims": len(m.get("claims", []))},
            "worker07_corpus": {"path": "artifacts/worker-049/classsep_prose_fix/worker07_results.json",
                                "sha256": pins_before["artifacts/worker-049/classsep_prose_fix/worker07_results.json"]},
            "worker035_controls": {"path": "artifacts/worker-049/classsep_prose_fix/worker035_controls.json",
                                   "sha256": pins_before["artifacts/worker-049/classsep_prose_fix/worker035_controls.json"]},
        },
        "checks": {
            "A_worker07_corpus": {"canonical": a_can, "patched": a_pat, "pass": check_a},
            "B_worker035_controls": {"rows": b_rows, "passed": b_ok,
                                     "total": len(controls035["controls"]), "pass": check_b},
            "C_live_claims": {"canonical_findings": len(can_claims), "patched_findings": len(pat_claims),
                              "claims_cleared": removed, "claims_added": added, "pass": check_c},
            "D_declaration_invariance_snapshot": {"canonical": len(decl_can), "patched": len(decl_pat), "pass": check_d},
            "D2_declaration_invariance_worker07": {"mismatch_fixtures": d2_mismatch, "pass": check_d2},
            "E_mutation_controls": {"clear": e_clear, "flag": e_flag, "pass": check_e},
            "F_audit_section3_simulation": {"canonical_hard": len(f_can), "patched_hard": len(f_pat),
                                             "canonical_first": f_can[:1], "pass": check_f},
        },
        "summary": {
            "live_claim_hard_findings_removed": len(removed),
            "live_claim_hard_findings_remaining": len(pat_claims),
            "worker07_corpus": "17/0/10/0 PASS (canonical and patched)",
            "worker035_controls": f"{b_ok}/{len(controls035['controls'])}",
            "declaration_surfaces_changed": 0,
            "audit_section3_hard_findings": {"canonical": len(f_can), "patched": len(f_pat)},
            "all_pass": bool(check_a and check_b and check_c and check_d and check_d2 and check_e and check_f and pin_ok),
        },
        "pin_drift_during_run": drifted,
        "pin_ok": pin_ok,
        "falsifier": (
            "Falsified by any of: (1) worker-07 corpus score other than 17/0/10/0 for the patched module, "
            "or any FP/FN introduced; (2) any of the 9 worker-035 positive controls not flagged, or any of "
            "the 14 negative controls flagged, by the patched module; (3) any live-snapshot claim finding "
            "present under the patched module, or a finding added on a declaration surface; (4) a declaration-mode "
            "finding differing between canonical and patched on any worker-07 fixture or snapshot node; "
            "(5) any of the 10 false-positive-mechanism controls still flagged, or any of the 9 genuine "
            "assertion controls cleared; (6) any pinned input hash differing from the recorded value. "
            "Falsification of this artifact does not falsify the underlying CF-16 adjudication: it means "
            "this particular calibration is not safe to adopt."
        ),
        "limitations": [
            "A genuine merge assertion placed after a metalinguistic cue in the same clause (e.g. "
            "'the detector flagged this; C0 and C2 are one class') would be cleared by the METALINGUISTIC "
            "guard if the cue falls inside the 55-char lookback. The guard is deliberately conservative: "
            "in prose mode the detector is a hard-failure trigger, so a miss is preferred to a false alarm.",
            "Rules are tuned on the frozen pins; a new prose shape not in the control battery is not covered.",
            "This is a checker calibration, not a gate verdict, not a class-separation verdict, and not "
            "a change to any frozen artifact.",
        ],
        "non_claims": [
            "no gate verdict, no node status, no validation_status=passed",
            "no canonical file edited; the patched module is a proposal staged under artifacts/worker-049/",
            "no mathematical, physical or class-separation claim",
            "no claim that the claims carrying the cleared findings are individually correct",
        ],
    }
    out = HERE / "result.json"
    out.write_text(json.dumps(report, indent=1, sort_keys=False) + "\n")
    print(json.dumps(report["summary"], indent=1))
    print("checks:", {k: v["pass"] for k, v in report["checks"].items()})
    print("pin_ok:", pin_ok, "drift:", drifted)
    print("artifact:", out)
    return 0 if report["summary"]["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
