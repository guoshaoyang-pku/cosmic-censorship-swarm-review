#!/usr/bin/env python3
"""W054-F1-REV12-VERIFY-01 -- independent verification of live canonical F1 rev12.

Target (snapshot taken 2026-09-12T00:32 CST):
  research_map -> schemas/af_wcc_vacuum.yaml
  sha256 cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3

The lead's rev12 delta (revision_history index 10) claims to close the hash-bound findings of
astra-life03-close-findings for F1:
  * HF-06: visibility clause repaired from whole-curve to the canonical tail predicate;
  * F-2: D0 retyped as a tagged regularity index r;
  * AF_{I+} defined;
  * duplicate revised_at keys collapsed into revision_history;
  * class_contract_pointer repointed at the canonical taxonomy (key `classes`), with the
    supplement pointer split into its own field;
  * f0_binding refreshed to the measured canonical F0.

This tool re-tests those claims at the snapshot bytes, independently of the author's checks.
It also confirms that the three content edits proposed by deepseek-flash-15 are the ones that
landed.

Run: python3 artifacts/worker-054/f1_rev12_verify/verify_rev12.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "f1_repair_verify"))
import verify_repair as vr  # noqa: E402  (helpers only; its main() is guarded)

ROOT = HERE.parents[2]
CST = timezone(timedelta(hours=8))
SNAP = HERE / "snapshot"
GATE = HERE / "gate"
SNAP.mkdir(exist_ok=True)
GATE.mkdir(exist_ok=True)

TARGET = SNAP / "af_wcc_vacuum.rev12.cce9c60146d6.yaml"
TARGET_SHA = "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3"
CANON_F0 = SNAP / "formulation_taxonomy.canonical.0abb9ed8.yaml"
CANON_F0_SHA = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
AUTHOR_F0 = SNAP / "formulation_taxonomy.authoring.yaml"
AUTHOR_F0_SHA = "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1"
LIVE_F1 = ROOT / "schemas" / "af_wcc_vacuum.yaml"
LIVE_F0 = ROOT / "research_map" / "formulation_taxonomy.yaml"
LIVE_AUTHOR_F0 = ROOT / "artifacts" / "formulation" / "formulation_taxonomy.yaml"
CONSISTENCY = ROOT / "artifacts" / "formulation" / "evidence" / "taxonomy_consistency.json"
CHECKER = ROOT / "artifacts" / "formulation" / "tools" / "check_class_schema.py"
PROPOSAL_FORMAL = ("not exists q in I+ and t0 in [0,T) with gamma([t0,T)) subset "
                   "J^-(q) intersect M.")

CHECKS: list[dict] = []
RESIDUALS: list[dict] = []


def add(cid, name, status, detail, evidence=None):
    CHECKS.append({"id": cid, "name": name, "status": status, "detail": detail,
                   "evidence": evidence or []})


def main() -> int:
    started = datetime.now(CST).isoformat(timespec="seconds")
    before = {vr.label(p): vr.sha256(p) for p in
              (TARGET, CANON_F0, AUTHOR_F0, vr.MAP, vr.FROZEN)}
    live_before = {"schemas/af_wcc_vacuum.yaml": vr.sha256(LIVE_F1),
                   "research_map/formulation_taxonomy.yaml": vr.sha256(LIVE_F0),
                   "artifacts/formulation/formulation_taxonomy.yaml": vr.sha256(LIVE_AUTHOR_F0)}
    frozen_ok = (before[vr.label(TARGET)] == TARGET_SHA and
                 before[vr.label(CANON_F0)] == CANON_F0_SHA and
                 before[vr.label(AUTHOR_F0)] == AUTHOR_F0_SHA)
    add("R0", "snapshot hashes match the declared rev12/F0 pins", "pass" if frozen_ok else "fail",
        json.dumps({"snapshots": before, "live_observed": live_before,
                    "live_f1_equals_snapshot": live_before["schemas/af_wcc_vacuum.yaml"] == TARGET_SHA}),
        [f"{vr.label(TARGET)}#{TARGET_SHA[:12]}"])

    text = TARGET.read_text()
    doc = yaml.safe_load(text)

    # R1 machine hygiene
    dups = vr.duplicate_top_level_keys(TARGET)
    strict_ok, strict_msg = vr.strict_load(TARGET)
    keys = [k for k, _ in vr.top_level_keys_with_lines(TARGET)]
    r1 = []
    if dups:
        r1.append(f"{len(dups)} duplicate top-level keys remain")
    if not strict_ok:
        r1.append(f"strict loader: {strict_msg}")
    if keys.count("revised_at") != 1:
        r1.append(f"revised_at occurs {keys.count('revised_at')} times")
    if "revised_at_unused" in keys:
        r1.append("legacy key revised_at_unused present")
    if "revision_history" not in keys:
        r1.append("revision_history missing")
    add("R1", "duplicate-key and revision-timestamp hygiene repaired",
        "pass" if not r1 else "fail",
        "; ".join(r1) or f"single revised_at; strict loader OK; {len(keys)} top-level keys",
        [f"{vr.label(TARGET)}#{TARGET_SHA[:12]}"])

    # R2 clock discipline
    eff = str(doc.get("revised_at"))
    try:
        eff_dt = datetime.fromisoformat(eff)
        future = eff_dt > datetime.now(CST) + timedelta(seconds=60)
    except ValueError:
        future = None
    add("R2", "revised_at is wall-clock ordered", "pass" if future is False else "fail",
        json.dumps({"revised_at": eff, "future_dated": future,
                    "evaluated_at": datetime.now(CST).isoformat(timespec="seconds")}))

    # R3 tail predicate landed
    q = doc.get("quantifiers") or {}
    formal = str(q.get("formal", ""))
    d5 = str((q.get("domains") or {}).get("D5", {}).get("definition", ""))
    ordered = [(o.get("kind"), o.get("binder"), o.get("domain_id")) for o in (q.get("ordered") or [])]
    r3 = []
    if not vr.TAIL_FORMAL_RE.search(formal):
        r3.append("quantifiers.formal is not the tail not_exists clause")
    if vr.WHOLE_CURVE_RE.search(formal):
        r3.append("whole-curve containment remains in quantifiers.formal")
    if "pairs (q,t0)" not in d5 or not vr.TAIL_RE.search(d5):
        r3.append("D5 is not the (q,t0) tail-pair domain")
    if "Whole-curve containment" not in d5 or "NOT the predicate" not in d5:
        r3.append("D5 lacks the explicit whole-curve disclaimer")
    if ordered[-1] != ("not_exists", "(q,t0)", "D5"):
        r3.append(f"final binder is {ordered[-1]!r}")
    add("R3", "HF-06 repair landed: formal + D5 + binder use the canonical tail predicate",
        "pass" if not r3 else "fail", "; ".join(r3) or json.dumps(ordered[-1]))

    # R4 D0 retyped
    d0 = str((q.get("domains") or {}).get("D0", {}).get("definition", ""))
    concl = doc.get("conclusion") or {}
    vis = doc.get("visibility") or {}
    r4 = []
    if ordered[0] != ("forall", "r", "D0"):
        r4.append(f"first binder is {ordered[0]!r}, expected forall r in D0")
    if "forall r in D0" not in formal or "X^r_vac(AF)" not in formal:
        r4.append("formal clause does not range over X^r_vac(AF)")
    if "tagged disjoint union" not in d0 or "smooth" not in d0:
        r4.append("D0 is not the tagged regularity index")
    if "(s,delta)" in formal or "(s,delta)" in str(concl.get("statement_formal", "")):
        r4.append("stale (s,delta) binder survives")
    add("R4", "F-2 repair landed: D0 retyped as tagged regularity index r",
        "pass" if not r4 else "fail", "; ".join(r4) or "forall r in D0 over X^r_vac(AF)")

    # R5 AF_{I+} defined
    abbrev = str((doc.get("i_plus") or {}).get("predicate_abbreviation") or "")
    r5 = []
    if "AF_{I+}(M)" not in abbrev or "i_plus.definition" not in abbrev:
        r5.append("predicate_abbreviation does not define AF_{I+}(M) against i_plus.definition")
    if "AF_{I+}(M_D)" not in str(concl.get("statement_formal", "")):
        r5.append("conclusion.statement_formal does not use AF_{I+}(M_D)")
    add("R5", "AF_{I+} symbol now defined in-schema", "pass" if not r5 else "fail",
        "; ".join(r5) or "predicate_abbreviation binds AF_{I+} to i_plus.definition")

    # R6 negation duality + visibility predicate
    neg = str(q.get("negation", ""))
    neg_concl = str(vis.get("negation_conclusion", ""))
    r6 = []
    if "tail visible from I+" not in neg and "visible from I+" not in neg:
        r6.append("quantifiers.negation does not name visibility from I+")
    if not vr.CANON_TAIL_RE.search(str(vis.get("definition", ""))):
        r6.append("visibility.definition is not the canonical tail predicate")
    if "for every q in I+ and every t0 in [0,T)" not in neg_concl:
        r6.append("visibility.negation_conclusion is not the tail-universal negation")
    add("R6", "negation dualises and visibility predicate is the single-q tail reading",
        "pass" if not r6 else "fail", "; ".join(r6) or "not(not exists q,t0: tail⊆) matches negation_conclusion")

    # R7 finite-model equivalence
    fm = vr.finite_model_check()
    add("R7", "finite-model check: landed tail clause == canonical negation; whole-curve witness", 
        "pass" if fm["repaired_vs_canonical_mismatches"] == 0 and fm["pinned_vs_canonical_mismatches"] > 0 else "fail",
        json.dumps(fm))

    # R8 binding pointers and F0 refresh
    pointer = str(doc.get("class_contract_pointer", ""))
    supp = str(doc.get("class_contract_supplement_pointer", ""))
    canon_doc = yaml.safe_load(CANON_F0.read_text())
    author_doc = yaml.safe_load(AUTHOR_F0.read_text())
    p_ok, p_msg = vr.resolve_pointer(canon_doc, pointer)
    s_ok, s_msg = vr.resolve_pointer(author_doc, supp)
    f0b = doc.get("f0_binding") or {}
    declared = str(f0b.get("declared_f0_sha256", ""))
    ev_sha = str(f0b.get("consistency_evidence_sha256", ""))
    ev_measured = vr.sha256(CONSISTENCY) if CONSISTENCY.exists() else None
    r8 = []
    if not p_ok:
        r8.append(f"canonical class_contract_pointer does not resolve: {p_msg}")
    if not pointer.startswith("research_map/"):
        r8.append("class_contract_pointer is not a canonical-path pointer")
    if not s_ok:
        r8.append(f"supplement pointer does not resolve in authoring file: {s_msg}")
    if declared != CANON_F0_SHA:
        r8.append(f"declared F0 {declared[:12]} != measured canonical {CANON_F0_SHA[:12]}")
    if ev_measured and ev_sha and ev_measured != ev_sha:
        r8.append(f"consistency_evidence hash {ev_sha[:12]} != measured {ev_measured[:12]}")
        RESIDUALS.append({
            "id": "R-2", "severity": "major",
            "where": f"{vr.label(TARGET)}:304 (f0_binding)",
            "finding": "declared consistency_evidence_sha256 does not match the measured evidence file",
            "detail": f"declared {ev_sha} vs measured {ev_measured} at "
                      f"artifacts/formulation/evidence/taxonomy_consistency.json",
            "impact": "the binding's evidence reference is not freeze-stable: a gate verdict citing "
                      "this field would cite bytes that are not the ones on disk"})
    add("R8", "class-contract and F0 bindings resolve against the canonical revision",
        "pass" if not r8 else "fail",
        "; ".join(r8) or json.dumps({"canonical_pointer": p_msg, "supplement_pointer": s_msg,
                                     "declared_f0": declared[:12],
                                     "consistency_evidence_sha256": ev_sha[:12]}),
        [f"{vr.label(CANON_F0)}#{CANON_F0_SHA[:12]}"])

    # R9 residual containment scan
    rows = vr.containment_scan(text)
    stale = [r for r in rows if r["form"] == "whole_curve" and r["section"] != "variants"]
    for r in stale:
        RESIDUALS.append({"id": "R-1", "severity": "minor",
                          "where": f"{vr.label(TARGET)}:{r['line']} (section {r['section']})",
                          "finding": "whole-curve containment wording survives outside the repaired slots",
                          "detail": r["text"],
                          "impact": "sufficient-but-stricter witness wording; the class predicate is the tail"})
    add("R9", "containment scan over rev12", "pass" if not stale else "warn",
        json.dumps({"whole_curve_rows": [r for r in rows if r["form"] == "whole_curve"],
                    "tail_rows": len([r for r in rows if r["form"] == "tail"])}))

    # R10 gate
    gate = vr.run_checker(TARGET, GATE / "rev12_check.json", GATE / "rev12_check.stderr.txt")
    add("R10", "canonical gate verdict on the rev12 snapshot",
        "pass" if gate["rc"] == 0 and gate["verdict"] == "pass" else "fail", json.dumps(gate))

    # R11 flash-15 edits landed
    proposal = yaml.safe_load((HERE.parent / "f1_repair_verify" / "snapshot" /
                               "repaired_proposal.303705c46834.yaml").read_text())
    p_formal = str(((proposal.get("quantifiers") or {}).get("formal", ""))).strip()
    p_d5 = str(((proposal.get("quantifiers") or {}).get("domains") or {}).get("D5", {}).get("definition", ""))
    r11 = []
    if PROPOSAL_FORMAL not in p_formal:
        r11.append("candidate proposal formal line not found (comparison base broken)")
    if PROPOSAL_FORMAL not in formal:
        r11.append("rev12 formal line is not byte-identical to the flash-15 proposed clause")
    if "pairs (q,t0)" not in p_d5 or "pairs (q,t0)" not in d5:
        r11.append("D5 pair-domain reading absent in one of the two files")
    add("R11", "the flash-15 content edits are the ones that landed in rev12",
        "pass" if not r11 else "fail", "; ".join(r11) or
        "rev12 formal clause byte-identical to the verified candidate; D5 pair reading preserved")

    # R12 drift
    after = {vr.label(p): vr.sha256(p) for p in (TARGET, CANON_F0, AUTHOR_F0, vr.MAP, vr.FROZEN)}
    drifted = {k: [before[k], after[k]] for k in before if before[k] != after[k]}
    live_after = {"schemas/af_wcc_vacuum.yaml": vr.sha256(LIVE_F1),
                  "research_map/formulation_taxonomy.yaml": vr.sha256(LIVE_F0)}
    add("R12", "no drift of the verified snapshot across the run",
        "pass" if not drifted else "fail",
        json.dumps({"drifted": drifted, "live_before": live_before, "live_after": live_after}))

    failed = [c["id"] for c in CHECKS if c["status"] == "fail"]
    warned = [c["id"] for c in CHECKS if c["status"] == "warn"]
    report = {
        "schema_version": "w054-verify/v1",
        "task_id": "W054-F1-REV12-VERIFY-01",
        "actor": "worker-054",
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-FORM",
        "created_at": started,
        "target": {"path": "schemas/af_wcc_vacuum.yaml", "snapshot": vr.label(TARGET),
                   "sha256": TARGET_SHA, "live_sha256_at_run_start": live_before["schemas/af_wcc_vacuum.yaml"]},
        "context_pins": {"canonical_f0": {"path": vr.label(CANON_F0), "sha256": CANON_F0_SHA},
                         "authoring_f0": {"path": vr.label(AUTHOR_F0), "sha256": AUTHOR_F0_SHA}},
        "checks": CHECKS,
        "residual_findings": RESIDUALS,
        "verdict": {
            "overall": "accept" if not failed else "revise",
            "score": 4.5 if not failed else 3.5,
            "hard_failures": failed,
            "warnings": warned,
            "counts_as_full_schema_verdict": bool(not failed),
            "semantics": "pass" if "R3" not in failed and "R4" not in failed and "R6" not in failed and "R7" not in failed else "fail",
            "binding": "pass" if "R1" not in failed and "R8" not in failed else "fail",
            "scope": "structural + quantifier/binding verification at the pinned hash; "
                     "not a physics or citation verdict, not a gate verdict",
        },
        "falsifier": (
            "Re-run this tool in an unchanged tree. The verification is falsified if (a) the "
            "snapshot hash differs from " + TARGET_SHA[:12] + ", (b) any R1-R8 check fails at "
            "unchanged bytes, (c) a reading is exhibited under which the landed formal clause is "
            "not the negation of the canonical single-q tail predicate, (d) the canonical gate "
            "returns non-pass on the snapshot, or (e) residual R-1 no longer reproduces. Live "
            "drift of schemas/af_wcc_vacuum.yaml away from the snapshot voids this verdict for "
            "any later revision but not for the verified bytes."
        ),
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({"failed": failed, "warned": warned,
                      "verdict": report["verdict"]["overall"], "score": report["verdict"]["score"],
                      "report": vr.rel(HERE / "report.json")}, indent=1))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
