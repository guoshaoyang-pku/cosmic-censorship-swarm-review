#!/usr/bin/env python3
"""FORM-DIFF-02 differential agreement matrix (D2/D3/D4).

Runs four independently written class-binding gates on the corpus copy built by
build_corpus.py:
  flash11   : this directory's check_schema.py (layout auto: own / R01-R16 canonical)
  flash13   : artifacts/flash-13/f1_gate/check_schema.py
  w06       : artifacts/worker-06/check_class_binding.py
  canonical : artifacts/formulation/tools/check_class_schema.py

Normalised verdicts: accept | reject | inconclusive | crash | error.
Per fixture x per implementation the matrix records verdict + rule/check ids.
Every disagreement against the fixture's expected verdict is emitted as a finding
with a minimal repro command. Rule-id crosswalk maps each implementation's ids to
the canonical R01-R16 where the mapping is unambiguous.

Outputs: differential_matrix.json (this directory).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
CORPUS = HERE / "corpus"
OUT = HERE / "differential_matrix.json"

IMPLS = {
    "flash11": {
        "cmd": [sys.executable, str(HERE / "check_schema.py"), "{f}", "--json"],
        "cwd": str(HERE),
    },
    "flash13": {
        "cmd": [sys.executable, str(REPO / "artifacts/flash-13/f1_gate/check_schema.py"), "{f}", "--json-out", "{json}"],
        "cwd": str(REPO / "artifacts/flash-13/f1_gate"),
    },
    "w06": {
        "cmd": [sys.executable, str(REPO / "artifacts/worker-06/check_class_binding.py"), "{f}", "--json", "{json}"],
        "cwd": str(REPO / "artifacts/worker-06"),
    },
    "canonical": {
        "cmd": [sys.executable, str(REPO / "artifacts/formulation/tools/check_class_schema.py"), "{f}", "--json"],
        "cwd": str(REPO / "artifacts/formulation/tools"),
    },
}


def run_impl(name: str, fixture: Path) -> dict:
    spec = IMPLS[name]
    with tempfile.TemporaryDirectory() as td:
        jpath = Path(td) / "out.json"
        cmd = [c.format(f=str(fixture), json=str(jpath)) for c in spec["cmd"]]
        try:
            proc = subprocess.run(cmd, cwd=spec["cwd"], capture_output=True, text=True, timeout=90)
        except subprocess.TimeoutExpired:
            return {"verdict": "error", "rule_ids": [], "detail": "timeout(90s)", "exit": None}
        raw = proc.stdout.strip()
        payload = None
        if jpath.exists():
            try:
                payload = json.loads(jpath.read_text())
            except json.JSONDecodeError:
                payload = None
        if payload is None and raw.startswith(("{", "[")):
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = None
        if payload is None:
            crash = "Traceback" in proc.stderr
            return {
                "verdict": "crash" if crash else "error",
                "rule_ids": [],
                "detail": (proc.stderr.strip().splitlines() or [""])[-1][:200],
                "exit": proc.returncode,
            }
        return normalize(name, payload, proc.returncode)


def normalize(name: str, payload, exit_code) -> dict:
    if name == "flash11":
        rec = payload[0] if isinstance(payload, list) else payload
        v = "accept" if rec.get("verdict") == "ACCEPT" else ("reject" if rec.get("verdict") == "REJECT" else "error")
        return {"verdict": v, "rule_ids": rec.get("failed_codes", []), "detail": rec.get("layout", ""), "exit": exit_code}
    if name == "flash13":
        v = "accept" if payload.get("verdict") == "accept" else ("reject" if payload.get("verdict") == "reject" else "error")
        return {"verdict": v, "rule_ids": [f.get("rule") for f in payload.get("failed_rules", [])], "detail": f"gate={payload.get('gate')}", "exit": exit_code}
    if name == "w06":
        raw_v = payload.get("verdict")
        v = {"pass": "accept", "fail": "reject", "inconclusive": "inconclusive"}.get(raw_v, "error")
        ids = [c.get("check_id") for c in payload.get("checks", []) if c.get("verdict") == "fail"]
        return {"verdict": v, "rule_ids": ids, "detail": f"rules={payload.get('rules_version')}", "exit": exit_code}
    if name == "canonical":
        v = "accept" if payload.get("verdict") == "pass" else ("reject" if payload.get("verdict") == "fail" else "error")
        return {"verdict": v, "rule_ids": payload.get("failed_rules", []), "detail": "", "exit": exit_code}
    return {"verdict": "error", "rule_ids": [], "detail": "unknown impl", "exit": exit_code}


EXPECT_MAP = {"fail": "reject", "pass": "accept", "accept": "accept", "reject": "reject", "escape": "accept", "unknown": "unknown"}


def classify(row_fixture: str, expected: str, name: str, verdict: dict, failed_ids: list[str]) -> str:
    if verdict["verdict"] == "crash":
        return "gate_robustness_crash"
    if verdict["verdict"] == "error":
        return "gate_error"
    if expected == "reject" and verdict["verdict"] == "accept":
        return "false_negative"
    if expected in ("accept", "pass", "escape") and verdict["verdict"] == "reject":
        return "false_positive_or_version_skew"
    if verdict["verdict"] == "reject" and failed_ids and failed_ids[0] in ("R01", "R02") and not row_fixture.startswith("canonical/"):
        return "format_dominated_reject"
    return ""


def main() -> int:
    manifest = json.loads((CORPUS / "manifest.json").read_text())
    fixtures = manifest["fixtures"]
    matrix = []
    findings = []
    leaky_fixtures: dict[str, list[str]] = {}
    per_impl_stats: dict[str, dict] = {k: {"evaluated": 0, "accept": 0, "reject": 0, "inconclusive": 0, "crash": 0, "error": 0} for k in IMPLS}

    for rel, meta in sorted(fixtures.items()):
        fpath = CORPUS / rel
        verdicts = {}
        for name in IMPLS:
            r = run_impl(name, fpath)
            verdicts[name] = r
            per_impl_stats[name]["evaluated"] += 1
            per_impl_stats[name][r["verdict"]] = per_impl_stats[name].get(r["verdict"], 0) + 1
        expected = meta["expected"]
        expected_binary = EXPECT_MAP.get(expected, "unknown")
        disagreements = []
        for name, r in verdicts.items():
            if expected == "escape":
                # documented leak: rejecting it is an improvement, accepting it is a known escape.
                # Neither is a disagreement; acceptances are collected in leaky_fixtures below.
                continue
            if expected_binary != "unknown" and r["verdict"] != expected_binary:
                disagreements.append(name)
        # known-leaky fixtures: expected reject, or documented escapes (my adv_*)
        if expected == "reject" or expected == "escape":
            leaky_fixtures[rel] = [name for name, r in verdicts.items() if r["verdict"] == "accept"]
        row = {
            "fixture": rel,
            "origin": meta["origin"],
            "expected": expected,
            "sha256": meta["sha256"],
            "verdicts": verdicts,
            "disagrees_with_expected": disagreements,
            "disagreement_classes": {n: classify(rel, expected, n, verdicts[n], verdicts[n]["rule_ids"]) for n in disagreements},
        }
        matrix.append(row)
        if disagreements:
            findings.append(
                {
                    "finding_id": f"FD-{len(findings)+1:02d}",
                    "fixture": rel,
                    "expected": expected,
                    "disagreeing_implementations": disagreements,
                    "disagreement_classes": row["disagreement_classes"],
                    "verdicts": {k: v["verdict"] for k, v in verdicts.items()},
                    "failed_rule_ids": {k: verdicts[k]["rule_ids"] for k in disagreements},
                    "repro": " ".join(IMPLS[disagreements[0]]["cmd"]).replace("{f}", str(fpath)).replace("{json}", "/tmp/out.json"),
                }
            )

    # D4: escape rates on the worker-06 semantic corpus (negatives) and false negatives (positives)
    w06_rows = [r for r in matrix if r["fixture"].startswith("w06/")]
    w06_neg = [r for r in w06_rows if EXPECT_MAP.get(r["expected"]) == "reject"]
    w06_pos = [r for r in w06_rows if EXPECT_MAP.get(r["expected"]) == "accept"]
    escape_rates = {}
    for name in IMPLS:
        accepted_neg = sum(1 for r in w06_neg if r["verdicts"][name]["verdict"] == "accept")
        rejected_pos = sum(1 for r in w06_pos if r["verdicts"][name]["verdict"] != "accept")
        pos_breakdown = {}
        for r in w06_pos:
            v = r["verdicts"][name]["verdict"]
            pos_breakdown[v] = pos_breakdown.get(v, 0) + 1
        escape_rates[name] = {
            "escape_rate_on_w06_negatives": round(accepted_neg / len(w06_neg), 4) if w06_neg else None,
            "escaped": accepted_neg,
            "negatives": len(w06_neg),
            "false_negative_rate_on_w06_positives": round(rejected_pos / len(w06_pos), 4) if w06_pos else None,
            "false_negatives": rejected_pos,
            "positive_verdict_breakdown": pos_breakdown,
            "positives": len(w06_pos),
            "corpus_sha256": manifest["corpus_sha256"],
            "caveat": "rejections of w06 flat-layout fixtures are format-dominated (R01/R02 identity rules fail first); the 0 escape rate is a verdict-level number, not evidence of semantic discrimination",
        }

    # FORM-DIFF-02 falsifier: >=2 independent implementations accept a fixture that is in fact leaky
    falsifier = {
        "statement": "Two independent implementations agree on a mutant that is in fact leaky (both false-negative) -> differential testing insufficient for that leak class.",
        "known_leaky_fixtures": len(leaky_fixtures),
        "fixtures_with_2plus_accepting_impls": {k: v for k, v in leaky_fixtures.items() if len(v) >= 2},
        "single_implementation_blind_spots": {k: v for k, v in leaky_fixtures.items() if len(v) == 1},
        "fired": any(len(v) >= 2 for v in leaky_fixtures.values()),
    }

    # group-level agreement for the canonical schemas
    canon_rows = [r for r in matrix if r["fixture"].startswith("canonical/")]
    canonical_agreement = {
        "fixtures": len(canon_rows),
        "per_implementation_accept": {name: sum(1 for r in canon_rows if r["verdicts"][name]["verdict"] == "accept") for name in IMPLS},
        "unanimous": all(len(set(r["verdicts"][n]["verdict"] for n in IMPLS)) == 1 for r in canon_rows) if canon_rows else None,
    }

    # quantify format dominance: rejections whose first failed rule is an identity/format rule
    fmt = {}
    for name in IMPLS:
        rej = fmt_rows = 0
        for r in matrix:
            v = r["verdicts"][name]
            if v["verdict"] != "reject":
                continue
            rej += 1
            ids = v["rule_ids"][:2] if v["rule_ids"] else []
            if any(x in ("R01", "R02", "single_class_id", "declared_artifact_matches") for x in ids):
                fmt_rows += 1
        fmt[name] = {"rejections": rej, "format_dominated": fmt_rows,
                     "share": round(fmt_rows / rej, 3) if rej else None}
    # robustness: crashes by origin
    crash_by_origin = {}
    for r in matrix:
        for name, v in r["verdicts"].items():
            if v["verdict"] == "crash":
                key = (name, r["fixture"].split("/")[0])
                crash_by_origin[str(key)] = crash_by_origin.get(str(key), 0) + 1

    report = {
        "task_id": "FORM-DIFF-02",
        "node_id": "F1",
        "gate": "G-CLASSBIND",
        "group_id": "formulation",
        "worker": "deepseek-flash-11",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "unverified draft; disagreements are the deliverable (D3)",
        "corpus": {"manifest": "corpus/manifest.json", "fixture_count": manifest["fixture_count"], "corpus_sha256": manifest["corpus_sha256"]},
        "implementations": {
            "flash11": "artifacts/flash-11/f1_aux_class_binding/check_schema.py (own layout + independent R01-R16 canonical mode)",
            "flash13": "artifacts/flash-13/f1_gate/check_schema.py (WP13-F1-GATE v0.1)",
            "w06": "artifacts/worker-06/check_class_binding.py (w06-draft-1)",
            "canonical": "artifacts/formulation/tools/check_class_schema.py (FORM-RULE-SPEC 1.0)",
        },
        "independence": "D1: no implementation imports another; each is invoked as a subprocess on the corpus copy",
        "rule_id_crosswalk": {
            "flash11_own": ["CLASS_ID", "CONJUNCTION", "QUANTIFIERS", "TOPOLOGY", "DATA_CLASS", "MATTER", "GENERICITY", "I_PLUS", "INEXTENDIBILITY", "CONCLUSION_TYPE", "SCOPE_SEPARATION", "FILENAME_CLASS"],
            "flash11_canonical": [f"R{i:02d}" for i in range(1, 17)],
            "note": "R-ids are canonical; flash13 and canonical use R-ids; w06 uses check_ids; crosswalk by rule intent is in README.md",
        },
        "per_implementation_stats": per_impl_stats,
        "format_dominated_rejections": fmt,
        "crash_counts_by_impl_and_origin": crash_by_origin,
        "canonical_schema_agreement": canonical_agreement,
        "escape_rates_on_w06_corpus": escape_rates,
        "findings": findings,
        "finding_classes": {
            c: sum(1 for f in findings if c in f["disagreement_classes"].values())
            for c in ["gate_robustness_crash", "false_negative", "false_positive_or_version_skew", "format_dominated_reject", "gate_error"]
        },
        "falsifier_check": falsifier,
        "matrix": matrix,
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"matrix: {len(matrix)} fixtures x {len(IMPLS)} implementations")
    for name, s in per_impl_stats.items():
        print(f"  {name:10s} accept={s['accept']:2d} reject={s['reject']:2d} inconclusive={s['inconclusive']} crash={s['crash']} error={s['error']}")
    print(f"findings: {len(findings)}")
    for f in findings[:8]:
        print(f"  {f['finding_id']} {f['fixture']} expected={f['expected']} offenders={f['disagreeing_implementations']}")
    print("canonical schema agreement:", canonical_agreement)
    for n, e in escape_rates.items():
        print(f"  {n:10s} w06 escape_rate={e['escape_rate_on_w06_negatives']} false_neg_rate={e['false_negative_rate_on_w06_positives']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
