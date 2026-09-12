#!/usr/bin/env python3
"""POST-HOC boundary probes for FORM-PROBE-10 (explicitly NOT part of the frozen corpus).

The frozen run found 11/12 mutants escape; the single catch (m03) was R09's negation-aware
scan for the stem "complete" in i_plus.definition.  These two probes were authored AFTER
seeing that result and are reported separately, never merged into the pre-registered
aggregates.  They test whether the catch was the concept or the token:

  h01  completeness stated with NO occurrence of "complete"/"completeness"
  h02  H2_loc-style regularity stated with none of the R31 tokens

Outputs posthoc_report.json.  Usage: python3 posthoc_probes.py
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
C0 = ROOT / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
OUT = HERE / "fixtures_posthoc"

import run_probes as R  # noqa: E402


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main() -> int:
    OUT.mkdir(exist_ok=True)
    d = copy.deepcopy(yaml.safe_load(C0.read_text()))

    a = copy.deepcopy(d)
    a["i_plus"]["definition"] = str(a["i_plus"]["definition"]) + (
        " Each null generator of the boundary is defined for arbitrarily large values of its "
        "affine parameter, and no generator terminates at a finite parameter value.")
    pa = OUT / "h01_completeness_synonym_in_c0_iplus_definition.yaml"
    pa.write_text(yaml.safe_dump(a, sort_keys=False, allow_unicode=True, width=1000))

    b = copy.deepcopy(d)
    b["conclusion"]["statement_natural_language"] = str(b["conclusion"]["statement_natural_language"]) + (
        " The metric is assumed to have square-integrable second weak derivatives on compact sets.")
    pb = OUT / "h02_h2loc_synonym_in_c0_conclusion.yaml"
    pb.write_text(yaml.safe_dump(b, sort_keys=False, allow_unicode=True, width=1000))

    rows = []
    for p in (pa, pb):
        rows.append({"fixture": p.stem, "path": str(p.relative_to(ROOT)), "sha256": sha(p),
                     "A": R.stage_a(p), "B": R.stage_b(p),
                     "Bp": R.stage_b(p, R.GATE_BP, label="Bp_semantic_calibrated"),
                     "Bh": R.stage_b(p, R.GATE_B, hardened=True, label="Bh_semantic_hardened")})
    rep = {
        "corpus_id": "FORM-PROBE-10-POSTHOC",
        "status": "POST-HOC - authored after the frozen run; NOT part of the pre-registered aggregates",
        "trigger": ("frozen run: m03 (completeness with the word 'complete') caught by stage A R09; "
                    "m04 (completeness under i_plus.extensions) escaped. These probes separate "
                    "concept-detection from token-detection."),
        "rows": rows,
        "finding": [
            {"fixture": r["fixture"],
             "escaped_both": (not r["A"]["caught"]) and (not r["Bp"]["caught"]),
             "A": r["A"]["verdict"], "A_rules": r["A"]["failed_rules"],
             "Bp": r["Bp"]["verdict"], "Bh": r["Bh"]["verdict"], "Bh_rules": r["Bh"]["failed_rules"]}
            for r in rows],
    }
    (HERE / "posthoc_report.json").write_text(json.dumps(rep, indent=2) + "\n")
    for r in rep["finding"]:
        print(f"{r['fixture']:52} A={r['A']:5}{str(r['A_rules']):10} B'={r['Bp']:7} "
              f"Bh={r['Bh']:7}{str(r['Bh_rules']):10} escaped_both={r['escaped_both']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
