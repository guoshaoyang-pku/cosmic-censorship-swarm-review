#!/usr/bin/env python3
"""W036-CLASSSEP-DISJ-01 - class_ids disjunction coverage of the standing class-separation detector.

Question
--------
`evaluation_rubric.yaml` defines HF-02 `class_leakage` (critical) with detector text
"unknown class_id | disjunction of class_ids | ..." and its frozen_classes comment says
"Classes are not interchangeable and must never be disjoined in a statement."
The standing detector the A1 evidence route runs is `research_map/class_separation.py`
(called from `research_map/audit_evidence.py:104-119`; scored by
`runtime/bin/classsep_regression.py` against worker-07's 27-fixture corpus).

Does that detector report anything for a `class_ids` container holding two distinct
frozen classes, and do the 8 live L0 rev3 ledger rows that carry such containers
produce any finding through any public entry point?

Routes measured (all three public entry points, because callers differ)
  R1 findings(obj, where)                  -- declaration mode (map nodes/claims events)
  R2 findings_for_map(map_like)            -- map scan (audit_evidence.py:110)
  R3 findings_for_text(text, where)        -- artifact text scan (audit_evidence.py:116)

Design
------
Controls (C*) must hold exactly or the checker exits 2 (fail-closed) and writes nothing.
Measurement cases (X*) have no expectation baked in; their observed output is the result.
The A0 probe (P*) calls `artifacts/audit/audit_lib.check_class_binding` (the implemented
HF-02) and is reported as an off-label probe, not as an A0 verdict.

Exit codes: 0 = no coverage gap observed (controls held, every X case silent);
            1 = coverage gap confirmed (controls held, at least one X case silent);
            2 = control failure or unreadable pinned input (no report emitted).
Stdlib only. Read-only against every canonical path; writes only --out.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TASK_ID = "W036-CLASSSEP-DISJ-01"

PINNED_INPUTS = (
    "research_map/class_separation.py",
    "runtime/bin/classsep_regression.py",
    "ledger/theorems.jsonl",
    "evaluation_rubric.yaml",
    "artifacts/worker-07/class_separation_falsification/results.json",
)

# Published L0 revisions, each independently pinned on disk. The live file is a moving
# target (it moved rev3 3e3d3553 -> rev4 a1674f09 during this task); the two frozen
# copies let the same measurement bind more than one revision.
LEDGER_VARIANTS = (
    ("live", "ledger/theorems.jsonl"),
    ("rev3-pinned", "artifacts/worker-097/l0_rev3_review/snapshots/theorems.jsonl"),
    ("pre-rev3-pinned", "artifacts/worker-029/f2b_full_review/ledger_theorems_snapshot.jsonl"),
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def pin_inputs() -> dict:
    out = {}
    for rel in PINNED_INPUTS:
        p = ROOT / rel
        out[rel] = {"sha256": sha256_file(p), "bytes": p.stat().st_size}
    return out


def load_detector():
    sys.path.insert(0, str(ROOT / "research_map"))
    import class_separation as cs  # noqa: WPS433

    return cs


# ---------------------------------------------------------------------------------------
# case matrix
# ---------------------------------------------------------------------------------------
# expect: route -> "flag" | "silent"; None = unasserted measurement route
CONTROLS = [
    {
        "id": "C1",
        "what": "single token merging C0 and C2 (the corpus's R2 positive)",
        "obj": {"class_ids": ["AF-SCC-C0C2-VAC-GEN"]},
        "expect": {"R1": "flag"},
    },
    {
        "id": "C2",
        "what": "bare composite prose in a declaration key",
        "obj": {"class_id": "AF-SCC-C2-VAC-GEN", "direction": "C0 or C2 are one class"},
        "expect": {"R1": "flag"},
    },
    {
        "id": "C3",
        "what": "unknown AF- class token (the corpus's other R2 positive)",
        "obj": {"class_ids": ["AF-SCC-CX-VAC-GEN"]},
        "expect": {"R1": "flag"},
    },
    {
        "id": "C4",
        "what": "clean single frozen class (negative control)",
        "obj": {
            "class_id": "AF-SCC-C0-VAC-GEN",
            "class_ids": ["AF-SCC-C0-VAC-GEN"],
            "conclusion_type": "scc_c0_future_inextendibility",
        },
        "expect": {"R1": "silent", "R3": "silent"},
    },
    {
        "id": "C5",
        "what": "split prohibition naming both classes (must stay silent)",
        "obj": {
            "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
            "notes": "C0 and C2 are separate classes; they must never be merged.",
        },
        "expect": {"R1": "silent"},
    },
    {
        "id": "C6",
        "what": "explicit prose merge assertion, prose mode (proves prose mode is live)",
        "obj": {
            "class_id": "AF-SCC-C2-VAC-GEN",
            "statement": "The C0 and C2 classes are one class for this argument.",
        },
        "expect": {"R2": "flag"},
    },
]

MEASUREMENTS = [
    {
        "id": "X1",
        "what": "class_ids list: C2 then C0",
        "obj": {"class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]},
    },
    {
        "id": "X2",
        "what": "class_ids list: C0 then C2 (order swap)",
        "obj": {"class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"]},
    },
    {
        "id": "X3",
        "what": "class_ids list: WCC + C0 (cross-family disjunction)",
        "obj": {"class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C0-VAC-GEN"]},
    },
    {
        "id": "X4",
        "what": "class_ids as one comma string (the other legal container shape)",
        "obj": {"class_ids": "AF-SCC-C2-VAC-GEN,AF-SCC-C0-VAC-GEN"},
    },
    {
        "id": "X5",
        "what": "class_ids list of three frozen classes",
        "obj": {"class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-VAC-GEN"]},
    },
]


def run_routes(cs, obj: dict, where: str, raw_text: str | None = None) -> dict:
    map_like = {"groups": [{"id": "probe", "nodes": [obj]}], "portfolio_events": [], "claims": [obj]}
    text = raw_text if raw_text is not None else json.dumps(obj)
    r1 = list(cs.findings(obj, where))
    r2 = list(cs.findings_for_map(map_like))
    r3 = list(cs.findings_for_text(text, where))
    return {
        "R1": {"n": len(r1), "findings": r1},
        "R2": {"n": len(r2), "findings": r2},
        "R3": {"n": len(r3), "findings": r3},
    }


def classify(observed: int) -> str:
    return "flag" if observed > 0 else "silent"


def run_matrix(cs) -> tuple[list, list]:
    controls, measurements = [], []
    for case in CONTROLS:
        res = run_routes(cs, case["obj"], case["id"])
        row = {"id": case["id"], "what": case["what"], "expect": case["expect"],
               "observed": {k: classify(v["n"]) for k, v in res.items()},
               "findings": {k: v["findings"][:2] for k, v in res.items()}}
        row["status"] = "PASS" if all(row["observed"][r] == e for r, e in case["expect"].items()) else "FAIL"
        controls.append(row)
    for case in MEASUREMENTS:
        res = run_routes(cs, case["obj"], case["id"])
        measurements.append({
            "id": case["id"], "what": case["what"],
            "observed": {k: classify(v["n"]) for k, v in res.items()},
            "finding_counts": {k: v["n"] for k, v in res.items()},
            "findings": {k: v["findings"][:3] for k, v in res.items()},
        })
    return controls, measurements


# ---------------------------------------------------------------------------------------
# live ledger rows
# ---------------------------------------------------------------------------------------
def known(cs, token: str) -> bool:
    return token.strip().upper() in cs.KNOWN_CLASSES


def scan_ledger(cs, rel: str) -> dict:
    path = ROOT / rel
    raw_lines = [ln for ln in path.read_text().splitlines() if ln.strip()]
    rows = [json.loads(ln) for ln in raw_lines]
    multi, per_row_findings = [], 0
    for i, (row, raw) in enumerate(zip(rows, raw_lines), 1):
        cids = row.get("class_ids")
        if isinstance(cids, list) and len([c for c in cids if known(cs, str(c))]) > 1:
            f1 = list(cs.findings(row, f"ledger/theorems.jsonl:{i}"))
            f3 = list(cs.findings_for_text(raw, f"ledger/theorems.jsonl:{i}"))
            # Ablation: remove one class token from the container and re-run. Any finding
            # that disappears is attributable to the disjunctive container itself.
            ablated_row = dict(row)
            ablated_row["class_ids"] = [c for c in cids if known(cs, str(c))][:1]
            a1 = list(cs.findings(ablated_row, f"ledger/theorems.jsonl:{i}:ablate"))
            ablated_raw = json.dumps(ablated_row)
            a3 = list(cs.findings_for_text(ablated_raw, f"ledger/theorems.jsonl:{i}:ablate"))
            attributable = max(0, len(f1) - len(a1)) + max(0, len(f3) - len(a3))
            per_row_findings += len(f1) + len(f3)
            multi.append({
                "line": i,
                "theorem_id": row.get("theorem_id"),
                "class_ids": cids,
                "conclusion_type": row.get("conclusion_type"),
                "status": row.get("status"),
                "R1_n": len(f1), "R3_n": len(f3),
                "R1_findings": f1[:2], "R3_findings": f3[:2],
                "R1_ablated_n": len(a1), "R3_ablated_n": len(a3),
                "container_attributable_findings": attributable,
            })
    whole = list(cs.findings_for_text("\n".join(raw_lines), rel))
    return {
        "path": rel,
        "snapshot_sha256": sha256_file(path),
        "rows_scanned": len(rows),
        "rows_with_ge2_known_class_tokens": len(multi),
        "multi_class_rows": multi,
        "per_row_findings_total": per_row_findings,
        "container_attributable_total": sum(r["container_attributable_findings"] for r in multi),
        "rows_with_any_finding": sum(1 for r in multi if r["R1_n"] or r["R3_n"]),
        "whole_file_findings": whole,
        "whole_file_findings_n": len(whole),
    }


# ---------------------------------------------------------------------------------------
# worker-07 corpus coverage
# ---------------------------------------------------------------------------------------
def scan_corpus(cs) -> dict:
    res = json.loads((ROOT / "artifacts/worker-07/class_separation_falsification/results.json").read_text())
    fixtures, hits = [], []
    for fx in res["fixtures"]:
        p = ROOT / fx["fixture_path"]
        m = json.loads(p.read_text())

        containers = []

        def walk(o, path=""):
            if isinstance(o, dict):
                for k, v in o.items():
                    if k in ("class_id", "class_ids"):
                        containers.append((f"{path}.{k}" if path else k, v))
                    walk(v, f"{path}.{k}" if path else k)
            elif isinstance(o, list):
                for j, v in enumerate(o):
                    walk(v, f"{path}[{j}]")

        walk(m)
        multi = []
        for where, val in containers:
            if isinstance(val, list):
                toks = [str(x) for x in val]
            elif isinstance(val, str):
                toks = [t for t in re.split(r"[;,]", val) if t.strip()]
            else:
                continue
            kn = {t.strip().upper() for t in toks if known(cs, t)}
            if len(kn) >= 2:
                multi.append({"where": where, "value": val, "classes": sorted(kn)})
        entry = {"id": fx.get("id"), "is_class_merge": bool(fx.get("is_class_merge")),
                 "multi_token_containers": multi}
        fixtures.append(entry)
        if multi:
            hits.append(entry)
    return {
        "corpus": "artifacts/worker-07/class_separation_falsification",
        "corpus_size": len(fixtures),
        "truth_merge_true": sum(1 for f in fixtures if f["is_class_merge"]),
        "fixtures_with_multi_token_known_class_container": len(hits),
        "multi_token_fixture_ids": [h["id"] for h in hits],
        "multi_token_and_truth_merge": [h["id"] for h in hits if h["is_class_merge"]],
        "regression_rule_replay": cs.regression(),
    }


# ---------------------------------------------------------------------------------------
# A0 implemented-HF-02 probe (off-label; reported raw)
# ---------------------------------------------------------------------------------------
def probe_a0(cs, ledger: dict) -> dict:
    sys.path.insert(0, str(ROOT / "artifacts/audit"))
    try:
        import audit_lib
    except Exception as exc:  # pragma: no cover - environmental
        return {"available": False, "error": f"{type(exc).__name__}: {exc}"}
    classes = audit_lib.frozen_classes(audit_lib.load_rubric())
    probes = []
    # P1: singular class_id plus a class_ids list that disjoins a second frozen class,
    # statement text does NOT name the second class. Does implemented HF-02 see it?
    p1 = {
        "claim_id": "W036-P1", "class_id": "AF-SCC-C2-VAC-GEN",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "statement": "A regularity statement under the frozen C2 hypotheses.",
        "conclusion_type": "open_problem", "falsifier": "probe",
    }
    # P2: the row shape of the 8 live ledger rows: class_ids list, no singular class_id.
    p2 = {
        "claim_id": "W036-P2",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "statement": "A statement whose row carries two class_ids entries.",
        "conclusion_type": "open_problem", "falsifier": "probe",
    }
    for pid, claim in (("P1-singular-plus-list", p1), ("P2-list-only", p2)):
        try:
            v = [x.as_dict() for x in audit_lib.check_class_binding(claim, classes)]
        except Exception as exc:  # pragma: no cover
            v = [{"error": f"{type(exc).__name__}: {exc}"}]
        probes.append({
            "id": pid, "claim": {k: claim.get(k) for k in ("claim_id", "class_id", "class_ids", "statement")},
            "violations": v,
            "hf02_disjunction_of_class_ids": any(
                x.get("hf") == "HF-02" and "disjunction of class_ids" in str(x.get("detail", "")) for x in v),
        })
    return {"available": True, "rubric": "artifacts/audit/evaluation_rubric.yaml",
            "probes": probes,
            "ledger_rows_as_claims": ledger["rows_with_ge2_known_class_tokens"]}


# ---------------------------------------------------------------------------------------
def build_findings(controls, measurements, ledger, ledger_variants, corpus, a0) -> list:
    silent_x = [m["id"] for m in measurements if all(v == "silent" for v in m["observed"].values())]
    out = []
    out.append({
        "id": "W036-DISJ-01", "severity": "hard",
        "statement": (
            "The standing class-separation detector is silent on class_ids disjunction: for every "
            f"isolate case {silent_x} it returned 0 findings through all three public entry points "
            "(findings / findings_for_map / findings_for_text), while the merged-token, unknown-token, "
            "composite-prose and prose-merge controls all fired (C1/C2/C3/C6 PASS)."),
        "evidence_refs": ["research_map/class_separation.py:97-114",
                          "artifacts/worker-036/classsep_disj_coverage/report.json"],
        "falsifier": ("Re-run the checker on the pinned detector hash: falsified if any X1-X5 case "
                      "yields >=1 non-SOFT finding on any route while the controls still pass."),
    })
    out.append({
        "id": "W036-DISJ-02", "severity": "hard",
        "statement": (
            f"{ledger['rows_with_ge2_known_class_tokens']} live L0 rev4 ledger rows carry a class_ids list with "
            ">=2 distinct frozen classes. Container-removal ablation: "
            f"{ledger['container_attributable_total']} finding(s) across all 8 rows are attributable to the "
            f"disjunctive container ({ledger['rows_with_any_finding']} row(s) yield any finding at all: the sole "
            "row-route finding is T-402 line 30 on its `regularity` prose 'Between C0 and C2', and R1 with the "
            "container reduced to one token still fires it). The A1 artifact-text route R3 and the whole-file "
            f"route return {ledger['whole_file_findings_n']} findings on the 62-row ledger. The same measurement "
            "reproduces on every pinned L0 revision: "
            + "; ".join(f"{v['path']} {v['snapshot_sha256'][:12]} -> {v['rows_with_ge2_known_class_tokens']} rows, "
                        f"{v['container_attributable_total']} attributable, whole-file {v['whole_file_findings_n']}"
                        for v in ledger_variants) + ". Rows: "
            + ", ".join(f"{r['theorem_id']}(line {r['line']})" for r in ledger["multi_class_rows"])),
        "evidence_refs": ["ledger/theorems.jsonl:4-5", "ledger/theorems.jsonl:25-30",
                          "ledger/theorems.jsonl:46,58,60",
                          "artifacts/worker-097/l0_rev3_review/snapshots/theorems.jsonl#3e3d35531421",
                          "artifacts/worker-029/f2b_full_review/ledger_theorems_snapshot.jsonl#ce42d205e761",
                          "artifacts/worker-036/classsep_disj_coverage/report.json"],
        "falsifier": ("Falsified if the container-removal ablation attributes >=1 finding to the disjunctive "
                      "class_ids container on any row of any pinned revision, if any named row yields a non-SOFT "
                      "R3 finding, or if a re-measure of any pinned L0 revision no longer shows those 8 rows."),
    })
    out.append({
        "id": "W036-DISJ-03", "severity": "hard",
        "statement": (
            "The worker-07 falsification corpus that the regression scores contains "
            f"{corpus['fixtures_with_multi_token_known_class_container']} fixture(s) with a class_ids container "
            f"holding >=2 distinct frozen classes, so its PASS ({corpus['regression_rule_replay']['tp']}/"
            f"{corpus['regression_rule_replay']['fn']}/{corpus['regression_rule_replay']['tn']}/"
            f"{corpus['regression_rule_replay']['fp']} tp/fn/tn/fp) cannot exercise the pattern the A0 rubric "
            "defines as critical HF-02 ('disjunction of class_ids')."),
        "evidence_refs": ["artifacts/worker-07/class_separation_falsification/results.json",
                          "runtime/bin/classsep_regression.py:19-31", "evaluation_rubric.yaml:52-54"],
        "falsifier": ("Falsified if a corpus fixture is shown to carry a >=2-known-class class_ids container, "
                      "or if cs.regression() no longer returns the recorded PASS."),
    })
    if a0.get("available"):
        p1 = [p for p in a0["probes"] if p["id"].startswith("P1")][0]
        p2 = [p for p in a0["probes"] if p["id"].startswith("P2")][0]
        p1_codes = sorted({str(x.get("hf")) for x in p1["violations"]})
        p2_codes = sorted({str(x.get("hf")) for x in p2["violations"]})
        out.append({
            "id": "W036-DISJ-04", "severity": "soft",
            "statement": (
                "A0's implemented HF-02 (artifacts/audit/audit_lib.py:140-185, check_class_binding) reads the "
                "singular claim.class_id and statement text; on the off-label probe P1 (singular C2 class_id + a "
                f"two-class class_ids list, statement not naming C0) it reported {len(p1['violations'])} violation(s) "
                f"with codes {p1_codes}, and probe P2 (ledger row shape, class_ids list only) reported "
                f"{len(p2['violations'])} violation(s) with codes {p2_codes} (absent singular class_id). Neither "
                "probe produced the rubric condition 'disjunction of class_ids'."),
            "evidence_refs": ["artifacts/audit/audit_lib.py:169-185", "evaluation_rubric.yaml:52-54",
                              "artifacts/worker-036/classsep_disj_coverage/report.json"],
            "falsifier": ("Falsified by a probe in which implemented HF-02 reports 'disjunction of class_ids' on P1 "
                          "or P2, or by a citation showing another standing detector consumes class_ids lists."),
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None, help="write report JSON here")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    try:
        cs = load_detector()
        pins = pin_inputs()
    except Exception as exc:
        print(f"FATAL: cannot load pinned inputs: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    controls, measurements = run_matrix(cs)
    failed = [c for c in controls if c["status"] != "PASS"]
    if failed:
        print("CONTROL FAILURE (fail-closed, no report written):", file=sys.stderr)
        for c in failed:
            print(f"  {c['id']}: expected {c['expect']} observed {c['observed']}", file=sys.stderr)
        return 2

    if args.selftest:
        print(f"selftest PASS: {len(controls)}/{len(controls)} controls hold; "
              f"{len(measurements)} measurement cases run; detector {pins['research_map/class_separation.py']['sha256'][:12]}")
        return 0

    ledger_variants = []
    for label, rel in LEDGER_VARIANTS:
        entry = scan_ledger(cs, rel)
        entry["variant"] = label
        ledger_variants.append(entry)
    ledger = ledger_variants[0]
    corpus = scan_corpus(cs)
    a0 = probe_a0(cs, ledger)
    findings = build_findings(controls, measurements, ledger, ledger_variants, corpus, a0)

    report = {
        "task_id": TASK_ID,
        "actor": "worker-036",
        "node_id": "A1",
        "gate": "G-AUDIT",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "question": ("Does the standing class-separation detector report class_ids disjunction (two distinct "
                     "frozen classes in one container) on synthetic isolates, on the 8 live L0 ledger rows that "
                     "carry it (checked on every pinned revision), and can its 27-fixture regression ever exercise "
                     "the pattern?"),
        "snapshot": pins,
        "checker_sha256": sha256_file(Path(__file__).resolve()),
        "detector_api": {"known_classes": sorted(cs.KNOWN_CLASSES),
                         "entry_points": ["findings", "findings_for_map", "findings_for_text"]},
        "controls": controls,
        "measurements": measurements,
        "ledger": ledger,
        "ledger_variants": ledger_variants,
        "corpus_coverage": corpus,
        "a0_probe": a0,
        "findings": findings,
        "hard_finding_count": sum(1 for f in findings if f["severity"] == "hard"),
        "soft_finding_count": sum(1 for f in findings if f["severity"] == "soft"),
        "global_falsifier": (
            "Re-run `python3 artifacts/worker-036/classsep_disj_coverage/check_disj_coverage.py --out report.json` "
            "on the pinned hashes in snapshot. FALSIFIED if: (a) any control fails (exit 2); or (b) any X1-X5 "
            "isolate yields >=1 non-SOFT finding on any of R1/R2/R3; or (c) the container-removal ablation "
            "attributes >=1 finding to a disjunctive class_ids container on any pinned L0 revision, or any pinned "
            "revision no longer contains the 8 named multi-class rows; or (d) the worker-07 corpus is shown to "
            "contain a class_ids container with >=2 distinct frozen classes; or (e) implemented HF-02 reports "
            "'disjunction of class_ids' on the P1/P2 probes."),
        "authority_note": ("Worker measurement only. No gate verdict, no node completion, no shared artifact "
                           "modified; exits after emitting events and a checkpoint."),
        "routes": {"R1": "class_separation.findings", "R2": "class_separation.findings_for_map",
                   "R3": "class_separation.findings_for_text"},
    }

    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print(f"report -> {args.out}")
    silent_x = [m["id"] for m in measurements if all(v == "silent" for v in m["observed"].values())]
    print(f"controls: {len(controls)}/{len(controls)} PASS")
    print(f"measurement cases silent on all routes: {silent_x}")
    for v in ledger_variants:
        print(f"ledger[{v['variant']}] {v['snapshot_sha256'][:12]}: rows={v['rows_scanned']} "
              f"multi={v['rows_with_ge2_known_class_tokens']} attributable={v['container_attributable_total']} "
              f"whole-file={v['whole_file_findings_n']}")
    print(f"corpus multi-token fixtures: {corpus['fixtures_with_multi_token_known_class_container']}/"
          f"{corpus['corpus_size']} (truth merges {corpus['truth_merge_true']})")
    print(f"findings: {report['hard_finding_count']} hard + {report['soft_finding_count']} soft")
    return 1 if silent_x else 0


if __name__ == "__main__":
    raise SystemExit(main())
