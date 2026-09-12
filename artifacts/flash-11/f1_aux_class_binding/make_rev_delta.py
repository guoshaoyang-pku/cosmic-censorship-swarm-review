#!/usr/bin/env python3
"""FORM-DIFF-02 verdict-delta report between two differential matrices (deltas only).

Usage:
  python3 make_rev_delta.py <baseline_matrix.json> <new_matrix.json> <out.json> \
      --baseline-label rev5 --new-label rev19

Reads two matrices produced by differential_matrix.py and writes one JSON delta
report. Nothing is re-derived: every field is a comparison of the two inputs plus
provenance hashes of the canonical artifact set each was run against.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]

CANON_FILES = [
    "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
    "artifacts/formulation/rule_spec.json",
    "artifacts/formulation/tools/check_class_schema.py",
]
IMPLS = ["flash11", "flash13", "w06", "canonical"]


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def canonical_hashes() -> dict:
    out = {}
    for rel in CANON_FILES:
        p = REPO / rel
        out[rel] = {"sha256": sha256(p), "bytes": p.stat().st_size}
    return out


def frozen_manifest() -> dict:
    p = REPO / "artifacts/formulation/FROZEN.json"
    m = json.loads(p.read_text())
    return {"path": str(p.relative_to(REPO)), "sha256": sha256(p), "revision": m.get("revision"), "frozen_at": m.get("frozen_at")}


def canonical_copies_in_corpus() -> dict:
    out = {}
    for f in sorted((HERE / "corpus/canonical").glob("*.yaml")):
        out[f"corpus/canonical/{f.name}"] = sha256(f)[:16]
    return out


def row_index(matrix: dict) -> dict:
    return {r["fixture"]: r for r in matrix["matrix"]}


def findings_index(matrix: dict) -> dict:
    return {f"{f['fixture']}|{','.join(f['disagreeing_implementations'])}": f for f in matrix["findings"]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("baseline")
    ap.add_argument("new")
    ap.add_argument("out")
    ap.add_argument("--baseline-label", default="baseline")
    ap.add_argument("--new-label", default="new")
    ap.add_argument("--rebased-probes", default=None,
                    help="optional evidence/rev19_rebased_probes.json to attach and to interpret the R12 deltas")
    a = ap.parse_args()

    base = json.loads(Path(a.baseline).read_text())
    new = json.loads(Path(a.new).read_text())
    bi, ni = row_index(base), row_index(new)

    verdict_deltas = []
    ruleid_deltas = []
    for fx in sorted(set(bi) | set(ni)):
        b, n = bi.get(fx), ni.get(fx)
        if b is None or n is None:
            verdict_deltas.append({"fixture": fx, "impl": "*", "from": "absent", "to": "absent-in-one-matrix",
                                   "present_in": {"baseline": b is not None, "new": n is not None}})
            continue
        for impl in IMPLS:
            bv = b["verdicts"][impl]
            nv = n["verdicts"][impl]
            if bv["verdict"] != nv["verdict"]:
                verdict_deltas.append({
                    "fixture": fx, "impl": impl,
                    "from": bv["verdict"], "to": nv["verdict"],
                    "from_rule_ids": bv["rule_ids"], "to_rule_ids": nv["rule_ids"],
                })
            elif bv["rule_ids"] != nv["rule_ids"]:
                ruleid_deltas.append({
                    "fixture": fx, "impl": impl, "verdict": nv["verdict"],
                    "from": bv["rule_ids"], "to": nv["rule_ids"],
                })

    bfind, nfind = findings_index(base), findings_index(new)
    stats_delta = {}
    for impl in IMPLS:
        bs, ns = base["per_implementation_stats"][impl], new["per_implementation_stats"][impl]
        stats_delta[impl] = {k: {"baseline": bs.get(k), "new": ns.get(k), "delta": (ns.get(k, 0) - bs.get(k, 0))}
                             for k in ["accept", "reject", "inconclusive", "crash", "error"]}

    fmt_delta = {}
    for impl in IMPLS:
        bf = base["format_dominated_rejections"][impl]
        nf = new["format_dominated_rejections"][impl]
        fmt_delta[impl] = {"baseline": bf, "new": nf}

    esc_delta = {}
    for impl in IMPLS:
        be = base["escape_rates_on_w06_corpus"][impl]
        ne = new["escape_rates_on_w06_corpus"][impl]
        esc_delta[impl] = {
            "escape_rate_on_w06_negatives": {"baseline": be["escape_rate_on_w06_negatives"], "new": ne["escape_rate_on_w06_negatives"]},
            "false_negative_rate_on_w06_positives": {"baseline": be["false_negative_rate_on_w06_positives"], "new": ne["false_negative_rate_on_w06_positives"]},
            "positive_verdict_breakdown": {"baseline": be["positive_verdict_breakdown"], "new": ne["positive_verdict_breakdown"]},
        }

    report = {
        "artifact": "FORM-DIFF-02 verdict-delta report",
        "task_id": "FORM-DIFF-02",
        "node_id": "F1",
        "gate": "G-CLASSBIND",
        "group_id": "formulation",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "worker": "deepseek-flash-11",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "baseline_label": a.baseline_label,
        "new_label": a.new_label,
        "status": "unverified draft; deltas only; disagreements are the deliverable (D3)",
        "inputs": {
            "baseline_matrix": {"path": a.baseline, "sha256": sha256(Path(a.baseline))},
            "new_matrix": {"path": a.new, "sha256": sha256(Path(a.new))},
        },
        "provenance": {
            "frozen_manifest": frozen_manifest(),
            "canonical_artifact_hashes_at_run": canonical_hashes(),
            "canonical_copies_inside_corpus": canonical_copies_in_corpus(),
        },
        "corpus": {
            "baseline": base["corpus"], "new": new["corpus"],
            "fixture_count_baseline": base["corpus"]["fixture_count"],
            "fixture_count_new": new["corpus"]["fixture_count"],
        },
        "single_variable_note": "fixture corpora (w06/f13/flash11/rev4probes) are byte-identical across the two runs; only corpus/canonical/* (the frozen schemas) and the canonical tool revision changed",
        "verdict_deltas": verdict_deltas,
        "ruleid_deltas": ruleid_deltas,
        "stats_delta": stats_delta,
        "format_dominated_delta": fmt_delta,
        "escape_rate_delta": esc_delta,
        "findings_delta": {
            "baseline_count": len(base["findings"]),
            "new_count": len(new["findings"]),
            "new_findings": [v for k, v in nfind.items() if k not in bfind],
            "resolved_findings": [v for k, v in bfind.items() if k not in nfind],
        },
        "falsifier_check": {
            "statement": base["falsifier_check"]["statement"],
            "baseline": base["falsifier_check"],
            "new": new["falsifier_check"],
        },
        "format_dominated_caveat": (
            "Verdict-level numbers are not semantic discrimination: most rejections are identity/layout-driven "
            "(share per implementation recorded in format_dominated_delta). The w06 escape rate of 0.0 is "
            "verdict-level only; format-dominated rejections invalidate it as evidence of semantic coverage."
        ),
    }
    if a.rebased_probes:
        rb = json.loads(Path(a.rebased_probes).read_text())
        report["r12_isolated_test"] = {
            "path": a.rebased_probes,
            "sha256": sha256(Path(a.rebased_probes)),
            "why": rb.get("why"),
            "probe_results": [
                {
                    "file": p["file"],
                    "sha256": p["sha256"],
                    "expect_fail_rule": p["expect_fail_rule"],
                    "verdicts": {k: {"verdict": v["verdict"], "rule_ids": v["rule_ids"]} for k, v in p["verdicts"].items()},
                    "canonical_isolates_expected": p["canonical_isolates_expected"],
                    "flash11_isolates_expected": p["flash11_isolates_expected"],
                }
                for p in rb["probes"]
            ],
        }
        report["corrected_interpretation"] = (
            "The two canonical verdict deltas in this report are R28 true positives on STALE fixtures, not the R12 "
            "strengthening: the rev4-era probes were deepcopies of the rev4 canonical WCC schema and inherited a "
            "'transfers' row inside transfer_failures that R28 now rejects. On the rebased probes (built from the "
            "frozen revision at run time), canonical accepts the R12 leak probe again with zero failed rules, so "
            "FD-13 (canonical-only false negative on R12) REMAINS OPEN; the rebased R12 control is accepted by both "
            "canonical and flash11 (no false positive), and rebased R09/R15/R16 probes are caught by canonical with "
            "the expected rule id. Claiming 'canonical FD-13 closed' from the stale-probe deltas would be wrong."
        )
        report["targeted_rule_proposal"] = (
            "Canonical R12 still does not scan the non_vacuity.condition assertive path for foreign inextendibility "
            "(rebased probe_r12_leak_in_nonvacuity_path.yaml: canonical accept, flash11 reject R12). Proposed: extend "
            "the R12 path list with non_vacuity.condition (and sibling assertive fields) and re-run both probes; the "
            "falsifier re-fires if canonical then accepts the leak or rejects the control."
        )
    Path(a.out).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"deltas: {len(verdict_deltas)} verdict, {len(ruleid_deltas)} rule-id")
    for d in verdict_deltas:
        print(f"  {d['fixture']} [{d['impl']}] {d['from']} -> {d['to']}")
    print("falsifier fired (new):", new["falsifier_check"]["fired"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
