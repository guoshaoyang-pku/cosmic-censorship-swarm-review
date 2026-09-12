#!/usr/bin/env python3
"""Self-test for the FORM-SEP-04 separation audit (v3): false positives, detection power,
residual blind spots.

Baseline state at v3: the fixtures were regenerated from the rev18 canonical pair (00:05), so the
old H1 converse sentence is no longer cloned into the controls; `repair_copy` is retained only for
legacy inputs that still carry it. The canonical pair is expected to PASS at rev18.

Case expectations:
  canonical_pair                      FAIL with exactly the known rev18 defect:
                                      containment_inversion_in_ledger (C0 ledger reason), plus the
                                      legacy H1 converse kind only if an old clone is passed
  repaired_pair                       PASS  (both known baseline defects repaired; legacy baseline)
  controls on repaired baseline       PASS  (no false positives)
  m12_composite_regularity            FAIL with composite_regularity
  p03_c2_schema_c0_meaning            FAIL with a regularity-separation kind
  m27_prose_converse / m28_...        FAIL with converse_implication_asserted (v3 subject-aware rule)
  p01_scc_schema_wcc_meaning          characterised (family-scope; audit is regularity-scoped)
  p05_scc_i_plus_completeness         characterised (family-scope; audit is regularity-scoped)
Writes artifacts/worker08/c2_c0_separation_selftest.json + .md
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
AUDIT = REPO / "artifacts" / "worker08" / "c2_c0_separation_audit.py"
FIX = REPO / "artifacts" / "formulation" / "fixtures"
OUTDIR = REPO / "artifacts" / "worker08" / "selftest"
REPAIRED_IN = OUTDIR / "repaired_inputs"
OUT_JSON = REPO / "artifacts" / "worker08" / "c2_c0_separation_selftest.json"
OUT_MD = REPO / "artifacts" / "worker08" / "c2_c0_separation_selftest.md"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")

BAD = "a C2-inextendibility proof SUBSUMES this class's conclusion (C0-inextendibility is stronger)"
GOOD = ("a C2-inextendibility proof does NOT subsume this class's conclusion; the implication runs "
        "C0 => C2 only (C0-inextendibility is stronger)")
# second known baseline defect (found by this v3 audit at rev18, reported as a hard failure):
# the C0 ledger reason inverts the frozen containment.
INV_BAD = "C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker"
INV_GOOD = ("C2 is a strictly smaller extension class (E_C2 subset of E_C0), so "
            "C2-inextendibility is strictly weaker")

CANON_C2 = REPO / "artifacts" / "formulation" / "schemas" / "af_scc_c2_vacuum.yaml"
CANON_C0 = REPO / "artifacts" / "formulation" / "schemas" / "af_scc_c0_vacuum.yaml"
REP_DIR = REPO / "artifacts" / "worker08" / "repaired_baseline"
REP_C2 = REP_DIR / "af_scc_c2_vacuum_unchanged.yaml"
REP_C0 = REP_DIR / "af_scc_c0_vacuum_repaired.yaml"


def repair_copy(path: Path) -> Path:
    """Return a copy of path with the two known baseline defects repaired (worker-path only).

    The canonical pair itself is passed through unrepaired by the `canonical` case, so the audit
    still reports the real upstream state there.
    """
    text = path.read_text(encoding="utf-8")
    if BAD not in text and INV_BAD not in text:
        return path
    REPAIRED_IN.mkdir(parents=True, exist_ok=True)
    out = REPAIRED_IN / path.name
    out.write_text(text.replace(BAD, GOOD).replace(INV_BAD, INV_GOOD), encoding="utf-8")
    return out


CASES = [
    ("canonical_pair", CANON_C2, CANON_C0, "canonical",
     "FAIL on H1 if unrepaired; PASS once upstream repair lands"),
    ("repaired_pair", REP_C2, REP_C0, "control", "PASS; repair sufficiency"),
    ("control_reordered_C2_vs_null_C0",
     FIX / "controls" / "null_reordered__AF-SCC-C2-VAC-GEN.yaml",
     FIX / "controls" / "null_unchanged__AF-SCC-C0-VAC-GEN.yaml", "control",
     "PASS; ordering must not matter (same-generation pair)"),
    ("control_old_C2_vs_extra_key_C0",
     FIX / "controls" / "null_reordered__AF-SCC-C2-VAC-GEN.yaml",
     FIX / "controls" / "null_extra_key__AF-SCC-C0-VAC-GEN.yaml", "control",
     "PASS; extra key must not create a separation failure"),
    ("mutant_m12_composite_regularity",
     FIX / "negative" / "m12_composite_regularity.yaml",
     FIX / "controls" / "null_unchanged__AF-SCC-C0-VAC-GEN.yaml", "mutant",
     "FAIL with composite_regularity"),
    ("mutant_m27_prose_converse",
     CANON_C2, FIX / "negative" / "m27_prose_converse_c2_c0.yaml", "probe",
     "FAIL with converse_implication_asserted"),
    ("mutant_m28_prose_converse_follows_from",
     CANON_C2, FIX / "negative" / "m28_prose_converse_reversed.yaml", "probe",
     "FAIL with converse_implication_asserted"),
    ("probe_p03_c2_schema_c0_meaning",
     FIX / "rephrased" / "p03_c2_schema_c0_meaning.yaml",
     FIX / "controls" / "null_unchanged__AF-SCC-C0-VAC-GEN.yaml", "probe",
     "FAIL with conclusion_regularity_axis_violation"),
    ("probe_p01_scc_schema_wcc_meaning",
     FIX / "rephrased" / "p01_scc_schema_wcc_meaning.yaml",
     FIX / "controls" / "null_unchanged__AF-SCC-C0-VAC-GEN.yaml", "probe_out_of_scope",
     "family-scope leak; audit is regularity-scoped"),
    ("probe_p05_scc_i_plus_completeness",
     FIX / "controls" / "null_reordered__AF-SCC-C2-VAC-GEN.yaml",
     FIX / "rephrased" / "p05_scc_i_plus_completeness_rephrased.yaml", "probe_out_of_scope",
     "family-scope leak; audit is regularity-scoped"),
]


def main() -> int:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    results = []
    for name, c2, c0, kind, expectation in CASES:
        if kind == "canonical":
            c2r, c0r = c2, c0
        else:
            c2r, c0r = repair_copy(c2), repair_copy(c0)
        oj, om = OUTDIR / f"{name}.json", OUTDIR / f"{name}.md"
        subprocess.run([sys.executable, str(AUDIT),
                        "--c2", str(c2r), "--c0", str(c0r),
                        "--out-json", str(oj), "--out-md", str(om),
                        "--label", name],
                       capture_output=True, text=True, timeout=300)
        try:
            m = json.loads(oj.read_text())
            verdict = m["verdict"]
            kinds = [f["kind"] for f in m["hard_failures"]]
            observed = "no hard failure" if not kinds else ", ".join(kinds)
        except (OSError, ValueError, KeyError) as e:
            verdict, kinds, observed = "ERROR", [], f"audit failed: {e}"
        if kind in {"control", "canonical"}:
            if kind == "control":
                ok = verdict == "PASS"
            else:
                # canonical pair is measured UNREPAIRED: expected hard failures are exactly the
                # known baseline defects still present in the canonical C0 file
                canon_c2_text = CANON_C2.read_text(encoding="utf-8")
                canon_c0_text = CANON_C0.read_text(encoding="utf-8")
                expected_kinds = []
                if INV_BAD in canon_c0_text or "C2 is a strictly larger extension class" in canon_c2_text:
                    expected_kinds.append("containment_inversion_in_ledger")
                if BAD in canon_c0_text:
                    expected_kinds.append("converse_implication_asserted")
                ok = ((verdict == "PASS" and not expected_kinds)
                      or (verdict == "FAIL" and kinds == expected_kinds))
        elif kind == "mutant":
            ok = verdict == "FAIL" and "composite_regularity" in kinds
        elif kind == "probe":
            if name == "probe_p03_c2_schema_c0_meaning":
                ok = "conclusion_regularity_axis_violation" in kinds
            elif name.startswith("mutant_m27") or name.startswith("mutant_m28"):
                ok = "converse_implication_asserted" in kinds
            else:
                ok = verdict == "FAIL" and any(k != "converse_implication_asserted" for k in kinds)
        else:
            ok = None
        results.append({"case": name, "kind": kind, "expectation": expectation,
                        "verdict": verdict, "hard_failure_kinds": kinds, "observed": observed,
                        "meets_expectation": ok})

    controls_ok = all(r["meets_expectation"] for r in results if r["kind"] == "control")
    canonical_ok = next(r["meets_expectation"] for r in results if r["kind"] == "canonical")
    caught = [r["case"] for r in results if r["kind"] in {"mutant", "probe"} and r["meets_expectation"]]
    missed = [r["case"] for r in results if r["kind"] in {"mutant", "probe"} and r["meets_expectation"] is False]
    family_missed = [r["case"] for r in results if r["kind"] == "probe_out_of_scope"
                     and r["verdict"] == "PASS"]

    report = {
        "selftest": "FORM-SEP-04 audit self-test v3",
        "generated_at": NOW,
        "baseline_note": ("Two known baseline defects exist in the canonical C0 file (the repaired-upstream "
                          "H1 converse and the rev18 containment-premise inversion). Fixture copies are "
                          "patched for both before running, so failures below are attributable to each "
                          "case's own mutation; the `canonical` case is deliberately left unrepaired."),
        "false_positive_check": {"controls_pass": controls_ok,
                                 "canonical_pair_behaves_as_expected": canonical_ok},
        "in_scope_mutant_probe_caught": caught,
        "in_scope_mutant_probe_missed": missed,
        "family_scope_probes_missed_documented": family_missed,
        "repair_sufficiency": {
            "repaired_pair_verdict": next(r["verdict"] for r in results if r["case"] == "repaired_pair"),
            "repair_source": "artifacts/worker08/repaired_baseline/README.json",
        },
        "residual_blind_spots": [
            "family leakage (WCC content inside an SCC schema, or I+ completeness in an SCC conclusion) "
            "is not detected by this regularity-separation audit; p01/p05 pass and remain the lead "
            "gate's / worker-06's responsibility.",
            "sentence-level lexical scan cannot see a leak expressed without any regularity token in a "
            "non-assertive field.",
            "the audit does not verify that the mathematics inside a definition is correct.",
        ],
        "results": results,
    }
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    md = ["# FORM-SEP-04 audit self-test (v3)", "",
          f"Generated {NOW}. Two known canonical-C0 baseline defects (legacy H1 converse, rev18 ledger "
          "containment inversion) are patched in fixture copies so that each case's own mutation is what "
          "is measured; the `canonical` case is left unrepaired and must show the rev18 defect.", "",
          f"- controls pass (no false positives): **{'yes' if controls_ok else 'NO'}**",
          f"- canonical pair behaves as expected (FAIL on the rev18 ledger defect): "
          f"**{'yes' if canonical_ok else 'NO'}**",
          f"- in-scope mutant/probe caught: **{len(caught)}** ({', '.join(caught) or 'none'})",
          f"- in-scope mutant/probe missed: **{len(missed)}** ({', '.join(missed) or 'none'})",
          f"- family-scope probes missed (expected, documented): **{len(family_missed)}** "
          f"({', '.join(family_missed) or 'none'})", "",
          "| case | kind | verdict | observed | meets expectation |", "|---|---|---|---|---|"]
    for r in results:
        md.append(f"| {r['case']} | {r['kind']} | {r['verdict']} | {r['observed']} | "
                  f"{r['meets_expectation']} |")
    md += ["", "## Residual blind spots", ""] + ["- " + b for b in report["residual_blind_spots"]]
    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({"controls_ok": controls_ok, "canonical_ok": canonical_ok,
                      "caught": caught, "missed": missed, "family_missed": family_missed}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
