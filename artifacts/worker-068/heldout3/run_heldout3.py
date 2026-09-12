#!/usr/bin/env python3
"""W068-FORM-HELDOUT-09 runner.

Runs the two live class-binding stages over the corpus:
  stage A (structural): artifacts/formulation/tools/check_class_schema.py --json FIXTURE
  stage B (semantic):   artifacts/worker-06/spec_conformance_audit.py FIXTURE --json OUT

A leaky fixture "escapes" iff BOTH stages accept it. A conforming control is a false
positive iff either stage rejects it. Known-leak positive controls must still be
rejected, otherwise the measurement is declared INVALID (dead evaluator).

Writes raw_verdicts.json and report.json. Never sets a map gate verdict or a node
status; every output is a measurement for the lead/controller to adjudicate.

Usage: python3 run_heldout3.py
Exit: 0 run completed (valid or not); 2 precondition failure.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
CST = timezone(timedelta(hours=8))
MANIFEST = HERE / "manifest.json"
DIAG = HERE / "diag"
PY = sys.executable


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run_cmd(args, timeout=120):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout, cwd=str(ROOT))
        return {"exit": p.returncode, "stdout": p.stdout, "stderr": p.stderr[-4000:]}
    except subprocess.TimeoutExpired:
        return {"exit": 124, "stdout": "", "stderr": f"timeout after {timeout}s"}


def parse_json(text):
    try:
        return json.loads(text)
    except Exception:
        return None


def main() -> int:
    manifest_bytes = MANIFEST.read_bytes()
    manifest_sha_before = hashlib.sha256(manifest_bytes).hexdigest()
    m = json.loads(manifest_bytes)
    binding = m["frozen_revision_binding"]

    # ---- preconditions -------------------------------------------------------
    invalid_reasons = []
    drift = {}
    for rel, expected in binding["schemas"].items():
        live = sha256_file(ROOT / rel)
        if live != expected:
            drift[rel] = {"frozen": expected, "live": live}
    if drift:
        invalid_reasons.append(f"canonical schema drift after build: {sorted(drift)}")
    frozen_now = sha256_file(ROOT / binding["frozen_manifest"])
    if frozen_now != binding["frozen_manifest_sha256"]:
        invalid_reasons.append(
            f"FROZEN manifest changed after build: {binding['frozen_manifest_sha256'][:12]} -> {frozen_now[:12]}")

    results = []
    for fx in m["fixtures"]:
        path = ROOT / fx["fixture"]
        disk_sha = sha256_file(path)
        if disk_sha != fx["sha256"]:
            invalid_reasons.append(f"fixture hash mismatch (tamper): {fx['fixture']}")

        a = run_cmd([PY, str(ROOT / m["stages"]["structural"]), "--json", str(path)])
        a_json = parse_json(a["stdout"])
        a_verdict = (a_json or {}).get("verdict", "error")
        a_rules = (a_json or {}).get("failed_rules", [])
        a_failures = (a_json or {}).get("failures", [])

        diag_out = DIAG / (Path(fx["fixture"]).stem + ".semantic.json")
        b = run_cmd([PY, str(ROOT / m["stages"]["semantic"]), str(path), "--json", str(diag_out)])
        b_json = parse_json(b["stdout"]) or {}
        b_verdict = b_json.get("verdict", "error")
        b_rules = b_json.get("failed_rules", [])
        b_checks = b_json.get("checks", [])

        caught_a = a_verdict != "pass"
        caught_b = b_verdict != "accept"
        escaped = (not caught_a) and (not caught_b)
        results.append({
            "fixture": fx["fixture"],
            "file": fx["file"],
            "class_id": fx["class_id"],
            "family": fx["family"],
            "expectation": fx["expectation"],
            "origin": fx["origin"],
            "expected_catcher_rules": fx["expected_catcher_rules"],
            "leak_claim": fx["leak_claim"],
            "sha256": fx["sha256"],
            "stage_a": {"exit": a["exit"], "verdict": a_verdict, "failed_rules": a_rules,
                        "failures": a_failures[:6], "stderr": a["stderr"][-800:]},
            "stage_b": {"exit": b["exit"], "verdict": b_verdict, "failed_rules": b_rules,
                        "undecided_rules": b_json.get("undecided_rules", []),
                        "rejected_checks": [c for c in b_checks if c.get("verdict") not in ("pass", "exempt")][:8],
                        "stderr": b["stderr"][-800:]},
            "caught_stage_a": caught_a,
            "caught_stage_b": caught_b,
            "caught_union": caught_a or caught_b,
            "escaped_union": escaped,
        })

    leaky = [r for r in results if r["expectation"] in ("should_be_caught", "probe")]
    probes = [r for r in results if r["expectation"] == "probe"]
    controls = [r for r in results if r["expectation"] == "must_be_accepted"]
    known = [r for r in results if r["expectation"] == "known_rejected_positive_control"]
    known_escapes = [r for r in results if r["expectation"] == "known_escape_reference"]

    def rate(rows, key="escaped_union"):
        n = len(rows)
        return (sum(1 for r in rows if r[key]) / n) if n else None

    # per-class escape rate over leaky fixtures
    per_class = {}
    for r in leaky:
        c = r["class_id"] or "unknown"
        per_class.setdefault(c, {"leaky": 0, "escaped": 0, "caught_stage_a": 0, "caught_stage_b": 0})
        per_class[c]["leaky"] += 1
        per_class[c]["escaped"] += int(r["escaped_union"])
        per_class[c]["caught_stage_a"] += int(r["caught_stage_a"])
        per_class[c]["caught_stage_b"] += int(r["caught_stage_b"])
    for c, d in per_class.items():
        d["escape_rate"] = d["escaped"] / d["leaky"]

    # per-family
    per_family = {}
    for r in leaky:
        f = r["family"]
        per_family.setdefault(f, {"count": 0, "escaped": 0, "fixtures": []})
        per_family[f]["count"] += 1
        per_family[f]["fixtures"].append(r["file"])
        per_family[f]["escaped"] += int(r["escaped_union"])
    escape_families = sorted(
        [{"family": f, **{k: v for k, v in d.items() if k != "fixtures"}, "fixtures": d["fixtures"]}
         for f, d in per_family.items() if d["escaped"] > 0],
        key=lambda x: (-x["escaped"], x["family"]))

    # expected-rule hit matrix
    rule_hits = {}
    for r in leaky:
        for rule in r["expected_catcher_rules"]:
            if rule == "NONE":
                continue
            fired = rule in (r["stage_a"]["failed_rules"] + r["stage_b"]["failed_rules"])
            d = rule_hits.setdefault(rule, {"expected": 0, "fired": 0, "missed_fixtures": []})
            d["expected"] += 1
            if fired:
                d["fired"] += 1
            else:
                if r["escaped_union"]:
                    d["missed_fixtures"].append(r["file"])
    for rule, d in rule_hits.items():
        d["fired_rate"] = d["fired"] / d["expected"]

    escaped_leaky = [r for r in leaky if r["escaped_union"]]
    false_positives = [r for r in controls if not (r["stage_a"]["verdict"] == "pass" and r["stage_b"]["verdict"] == "accept")]
    known_accepted = [r for r in known if not (r["caught_union"])]
    if known_accepted:
        invalid_reasons.append(
            "KNOWN-REJECTED POSITIVE CONTROLS ACCEPTED (evaluator dead): " + ", ".join(r["file"] for r in known_accepted))

    valid = not invalid_reasons

    raw = {
        "corpus_id": m["corpus_id"],
        "task_id": m["task_id"],
        "actor": "worker-068",
        "run_at": datetime.now(CST).isoformat(timespec="seconds"),
        "manifest_sha256_before_run": manifest_sha_before,
        "frozen_revision_binding": binding,
        "canonical_drift_after_build": drift,
        "stage_hashes": {"structural": m["stages"]["structural_sha256"], "semantic": m["stages"]["semantic_sha256"],
                         "rule_spec": m["stages"]["rule_spec_sha256"]},
        "valid": valid,
        "invalid_reasons": invalid_reasons,
        "fixtures": results,
    }
    (HERE / "raw_verdicts.json").write_text(json.dumps(raw, indent=2) + "\n")

    report = {
        "corpus_id": m["corpus_id"],
        "task_id": m["task_id"],
        "worker": "worker-068",
        "actor": "worker-068",
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "manifest_sha256_before_run": manifest_sha_before,
        "frozen_revision_binding": binding,
        "valid": valid,
        "invalid_reasons": invalid_reasons,
        "stages": raw["stage_hashes"],
        "counts": m["counts"],
        "aggregates": {
            "leaky": len(leaky),
            "leaky_escaped_union": len(escaped_leaky),
            "union_escape_rate": rate(leaky),
            "caught_stage_a": sum(1 for r in leaky if r["caught_stage_a"]),
            "caught_stage_b": sum(1 for r in leaky if r["caught_stage_b"]),
            "union_caught": sum(1 for r in leaky if r["caught_union"]),
            "probes": len(probes),
            "probes_escaped": sum(1 for r in probes if r["escaped_union"]),
            "conforming_controls": len(controls),
            "false_positives": len(false_positives),
            "known_rejected_controls": len(known),
            "known_rejected_controls_rejected": sum(1 for r in known if r["caught_union"]),
            "known_escape_references": len(known_escapes),
            "known_escape_references_still_escaping": sum(1 for r in known_escapes if r["escaped_union"]),
        },
        "per_class": per_class,
        "per_family": per_family,
        "escape_families": escape_families,
        "expected_rule_hit_matrix": rule_hits,
        "escaped_fixtures": [
            {
                "fixture": r["fixture"],
                "class_id": r["class_id"],
                "family": r["family"],
                "expectation": r["expectation"],
                "leak_claim": r["leak_claim"],
                "expected_catcher_rules": r["expected_catcher_rules"],
                "stage_a": r["stage_a"]["verdict"],
                "stage_b": r["stage_b"]["verdict"],
                "undecided_rules_stage_b": r["stage_b"]["undecided_rules"],
                "why_not_caught": "no rule in the union of stage A failed and stage B had no rejecting check",
            }
            for r in escaped_leaky
        ],
        "false_positive_fixtures": [
            {"fixture": r["fixture"], "stage_a": r["stage_a"], "stage_b": r["stage_b"]} for r in false_positives
        ],
        "known_leak_control_results": [
            {"fixture": r["fixture"], "family": r["family"], "stage_a": r["stage_a"]["verdict"],
             "stage_b": r["stage_b"]["verdict"], "caught_union": r["caught_union"]} for r in known
        ],
        "known_escape_reference_results": [
            {"fixture": r["fixture"], "family": r["family"], "stage_a": r["stage_a"]["verdict"],
             "stage_b": r["stage_b"]["verdict"], "escaped_union": r["escaped_union"],
             "note": "escape at the current revision replicates the FORM-HELDOUT-08 family" if r["escaped_union"]
                     else "now caught at the current revision; the HELDOUT-08 family no longer reproduces"}
            for r in known_escapes
        ],
        "limitations": [
            "Author-built corpus: the leak labels are the author's, calibrated only by the rule spec; an independent reviewer must adjudicate them before escape families are cited.",
            "Stage B is worker-06's semantic auditor, not the F2 gate; a fixture accepted by both stages is an escape from this pipeline, not proof that the schema is class-correct.",
            "The corpus is bound to one FROZEN revision; any republish invalidates the measurement (the runner records drift and voids the run).",
            "This is measurement only: no gate verdict, no node completion, no theorem.",
        ],
        "next_falsifier": "A later FROZEN revision in which the same fixture text is accepted by both stages, or an independent reviewer classifying an escaped fixture as a non-leak (corpus over-claim), invalidates the corresponding escape family.",
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=2) + "\n")

    print(json.dumps({
        "valid": valid,
        "invalid_reasons": invalid_reasons,
        "union_escape_rate": rate(leaky),
        "escaped": len(escaped_leaky),
        "of": len(leaky),
        "false_positives": len(false_positives),
        "known_rejected_controls_rejected": f"{sum(1 for r in known if r['caught_union'])}/{len(known)}",
        "known_escape_references_still_escaping": f"{sum(1 for r in known_escapes if r['escaped_union'])}/{len(known_escapes)}",
        "stage_a_caught": sum(1 for r in leaky if r["caught_stage_a"]),
        "stage_b_caught": sum(1 for r in leaky if r["caught_stage_b"]),
        "escaped_files": [r["file"] for r in escaped_leaky],
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
