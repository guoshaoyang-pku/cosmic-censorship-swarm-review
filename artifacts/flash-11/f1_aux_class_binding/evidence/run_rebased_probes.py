#!/usr/bin/env python3
"""Run the four independent gates on the rebased rev19 probes, using the exact same
subprocess + normalisation path as differential_matrix.py (imported, not re-implemented).

Output: evidence/rev19_rebased_probes.json
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent          # .../f1_aux_class_binding/evidence
GATE = HERE.parent                              # .../f1_aux_class_binding
sys.path.insert(0, str(GATE))
import differential_matrix as dm  # noqa: E402

PROBES = HERE / "probes_rev19"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    man = json.loads((PROBES / "manifest.json").read_text())
    rows = []
    for item in man["probes"]:
        f = PROBES / item["file"]
        verdicts = {name: dm.run_impl(name, f) for name in dm.IMPLS}
        exp = item.get("expect_fail_rule")
        canon = verdicts["canonical"]
        flash11 = verdicts["flash11"]
        rows.append({
            "file": f"evidence/probes_rev19/{item['file']}",
            "sha256": sha256(f),
            "expect_fail_rule": exp,
            "verdicts": verdicts,
            "canonical_isolates_expected": (exp in canon["rule_ids"]) if exp else canon["verdict"] == "accept",
            "flash11_isolates_expected": (exp in flash11["rule_ids"]) if exp else flash11["verdict"] == "accept",
        })
        print(f"{item['file']:52s} " + " ".join(f"{n}={v['verdict']}({','.join(v['rule_ids'][:2])})" for n, v in verdicts.items()))

    out = {
        "artifact": "rev19 rebased-probe results",
        "why": ("rev4-era probes were deepcopies of the rev4 canonical WCC schema and inherited a "
                "transfer-container defect; R28 rejects the stale copies, which confounds the R12 measurement. "
                "These probes are rebuilt from the frozen rev19 schemas so R12 is measured in isolation."),
        "probe_dir": "evidence/probes_rev19",
        "probes": rows,
    }
    (HERE / "rev19_rebased_probes.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print("wrote evidence/rev19_rebased_probes.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
