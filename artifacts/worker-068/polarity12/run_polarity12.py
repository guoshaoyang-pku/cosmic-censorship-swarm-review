#!/usr/bin/env python3
"""W068-FORM-POLARITY-12 runner (worker-068, bounded task).

Runs the two pinned class-binding stages (structural + semantic) over the fresh
three-class FORM-POLARITY-12 corpus on a fully pinned rev11 shadow, then applies the
candidate conclusion-freeze rule R-CAND (freeze_statements / freeze_full / negation_only)
to (a) the new corpus and (b) the union of the three earlier pinned corpora
(FORM-HELDOUT-09, FORM-POLARITY-10, FORM-POLARITY-11), and reports catch / false-positive
counts. Measurement only: never sets a map gate verdict or node status.

  stage A: <shadow>/artifacts/formulation/tools/check_class_schema.py --json FIXTURE
  stage B: <shadow>/artifacts/worker-06/spec_conformance_audit.py FIXTURE --spec SPEC

A probe escapes iff BOTH stages accept it. An arm is informative iff the unmutated
identity control is accepted by both stages. Validity requires no shadow/fixture drift
between build and run and all known-rejected liveness controls rejected by >=1 stage.

Usage: python3 run_polarity12.py
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
ROOT = HERE.parents[2]
CST = timezone(timedelta(hours=8))
MANIFEST = HERE / "manifest.json"
SHADOW = HERE / "shadow"
PY = sys.executable

STAGE_A = SHADOW / "artifacts" / "formulation" / "tools" / "check_class_schema.py"
STAGE_B = SHADOW / "artifacts" / "worker-06" / "spec_conformance_audit.py"
SPEC = SHADOW / "artifacts" / "formulation" / "rule_spec.json"

sys.path.insert(0, str(HERE))
import conclusion_freeze_check as rfc  # noqa: E402


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run_cmd(args, timeout=180):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout, cwd=str(ROOT))
        return {"exit": p.returncode, "stdout": p.stdout, "stderr": p.stderr[-1500:]}
    except subprocess.TimeoutExpired:
        return {"exit": 124, "stdout": "", "stderr": f"timeout after {timeout}s"}


def parse_json(text):
    try:
        return json.loads(text)
    except Exception:
        return None


def stage_a(fixture: Path) -> dict:
    r = run_cmd([PY, str(STAGE_A), "--json", str(fixture)])
    j = parse_json(r["stdout"]) or {}
    return {"tool": str(STAGE_A.relative_to(ROOT)), "exit": r["exit"], "verdict": j.get("verdict"),
            "failed_rules": j.get("failed_rules", []),
            "failures": [{"rule": f.get("rule"), "msg": str(f.get("msg"))[:200]} for f in j.get("failures", [])],
            "parse_ok": bool(j), "stderr": r["stderr"]}


def stage_b(fixture: Path) -> dict:
    r = run_cmd([PY, str(STAGE_B), str(fixture), "--spec", str(SPEC)])
    j = parse_json(r["stdout"]) or {}
    return {"tool": str(STAGE_B.relative_to(ROOT)), "exit": r["exit"], "verdict": j.get("verdict"),
            "failed_rules": j.get("failed_rules", []),
            "fail_details": [c for c in (j.get("checks", []) or []) if c.get("verdict") == "fail"][:6],
            "parse_ok": bool(j), "stderr": r["stderr"]}


def accepted(a: dict, b: dict) -> bool:
    return a.get("verdict") == "pass" and b.get("verdict") == "accept"


def rejected(a: dict, b: dict) -> bool:
    return a.get("verdict") != "pass" or b.get("verdict") != "accept"


# ---------------------------------------------------------------- union corpora
UNION = {
    "heldout3": {
        "manifest": "artifacts/worker-068/heldout3/manifest.json",
        "raw": "artifacts/worker-068/heldout3/raw_verdicts.json",
        "list_key": "fixtures",
        "escape_field": "escaped_union",
        "bases": {"W": "artifacts/worker-068/heldout3/bases/af_wcc_vacuum.yaml",
                  "C2": "artifacts/worker-068/heldout3/bases/af_scc_c2_vacuum.yaml",
                  "C0": "artifacts/worker-068/heldout3/bases/af_scc_c0_vacuum.yaml"},
        "base_note": "own rev11 bases",
    },
    "polarity10": {
        "manifest": "artifacts/worker-068/polarity10/manifest.json",
        "raw": "artifacts/worker-068/polarity10/raw_verdicts.json",
        "list_key": "fixtures",
        "escape_field": "escaped_union",
        "bases": {"W": "artifacts/worker-068/polarity10/bases/af_wcc_vacuum.yaml",
                  "C2": "artifacts/worker-068/polarity10/bases/af_scc_c2_vacuum.yaml",
                  "C0": "artifacts/worker-068/polarity10/bases/af_scc_c0_vacuum.yaml"},
        "base_note": "own rev12 bases",
    },
    "polarity11": {
        "manifest": "artifacts/worker-068/polarity11/manifest.json",
        "raw": "artifacts/worker-068/polarity11/raw_verdicts.json",
        "list_key": "results",
        "escape_field": "escaped",
        "bases": {"W": "artifacts/worker-068/polarity11/shadow/schemas/af_wcc_vacuum.yaml",
                  "C2": "artifacts/worker-068/polarity10/bases/af_scc_c2_vacuum.yaml",
                  "C0": "artifacts/worker-068/polarity10/bases/af_scc_c0_vacuum.yaml"},
        "base_note": "own W shadow base; C2/C0 from polarity10 (polarity11 is W-only except C0 liveness copies)",
    },
}

VARIANT_KEYS = ("freeze_statements", "freeze_full", "negation_only")


def classify(expectation: str, escaped: bool) -> str:
    if expectation == "must_be_accepted":
        return "conforming_control"
    if expectation == "known_rejected_positive_control":
        return "known_rejected_liveness"
    if expectation == "known_escape_reference":
        return "escape_reference"
    return "escape" if escaped else "caught_probe"


CLASS_OF_BASE = {"W": "AF-WCC-VAC-GEN", "C2": "AF-SCC-C2-VAC-GEN", "C0": "AF-SCC-C0-VAC-GEN"}


def leaf_diffs(a, b, prefix="$") -> list:
    """Changed leaf paths between two parsed YAML documents (sorted, capped)."""
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            out += leaf_diffs(a.get(k), b.get(k), f"{prefix}.{k}")
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f"{prefix}[len {len(a)}->{len(b)}]")
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                out += leaf_diffs(x, y, f"{prefix}[{i}]")
    elif a != b:
        out.append(prefix)
    return out[:60]


def main() -> int:
    if not MANIFEST.is_file():
        print("manifest.json missing; run build_corpus12.py first", file=sys.stderr)
        return 2
    manifest_sha = sha256_file(MANIFEST)
    m = json.loads(MANIFEST.read_text())
    invalid = []

    shadow_before = {rel: sha256_file(ROOT / rel) for rel in m["shadow_pins"]}
    for rel, meta in m["shadow_pins"].items():
        if shadow_before[rel] != meta["sha256"]:
            invalid.append(f"pinned shadow drift at start: {rel}")
    fixture_hashes_before = {}
    for f in m["fixtures"]:
        p = ROOT / f["fixture"]
        if not p.is_file():
            invalid.append(f"missing fixture {f['fixture']}")
            continue
        fixture_hashes_before[f["fixture"]] = sha256_file(p)
        if fixture_hashes_before[f["fixture"]] != f["sha256"]:
            invalid.append(f"fixture tamper at start: {f['fixture']}")

    # ------------------------------------------------------------ stage runs
    results = []
    for f in m["fixtures"]:
        p = ROOT / f["fixture"]
        a = stage_a(p)
        b = stage_b(p)
        escaped = accepted(a, b)
        results.append({**{k: f[k] for k in ("fixture", "file", "base", "class_id", "family", "op_id",
                                             "op_kind", "expectation", "expected_catcher_rules", "sha256")},
                        "stage_a": a, "stage_b": b, "escaped": escaped,
                        "caught_stage_a": a.get("verdict") != "pass",
                        "caught_stage_b": b.get("verdict") != "accept",
                        "catch_rules": sorted(set(a.get("failed_rules", []) + b.get("failed_rules", [])))})

    arm = {}
    for cls, fname in (("AF-WCC-VAC-GEN", "ctrl_w_identity.yaml"),
                       ("AF-SCC-C2-VAC-GEN", "ctrl_c2_identity.yaml"),
                       ("AF-SCC-C0-VAC-GEN", "ctrl_c0_identity.yaml")):
        r = next((x for x in results if x["file"] == fname), None)
        arm[cls] = {"identity_fixture": fname, "escaped": bool(r and r["escaped"]),
                    "informative": bool(r and r["escaped"])}
    liveness = [x for x in results if x["expectation"] == "known_rejected_positive_control"]
    if not all(rejected(x["stage_a"], x["stage_b"]) for x in liveness):
        invalid.append("known-rejected liveness control accepted")

    # ------------------------------------------------------------ candidate rule on new corpus
    check_rows = []
    for f in m["fixtures"]:
        fx = ROOT / f["fixture"]
        base = ROOT / f["base_path"]
        fx_doc = rfc.yaml.safe_load(fx.read_bytes())
        base_doc = rfc.yaml.safe_load(base.read_bytes())
        checks = {v: rfc.check(fx_doc, base_doc, v) for v in VARIANT_KEYS}
        check_rows.append({**{k: f[k] for k in ("fixture", "file", "base", "class_id", "family", "op_id",
                                                "op_kind", "expectation")},
                           "checks": {v: {"verdict": c["verdict"], "flags": c["flags"]} for v, c in checks.items()}})

    def new_metric(variant, role_filter, predicate=None):
        rows = [r for r in check_rows if role_filter(r)]
        flagged = [r for r in rows if r["checks"][variant]["verdict"] == "FLAG"]
        if predicate:
            flagged = [r for r in flagged if predicate(r)]
        return {"n": len(rows), "flagged": len(flagged), "files": [r["file"] for r in flagged]}

    content_ops = [r for r in check_rows if r["op_kind"] in ("common", "W", "C0", "sub")]
    substitution_ops = [r for r in check_rows if r["op_kind"] == "sub"]
    polarity_ops = [r for r in check_rows if r["op_kind"] in ("common", "W", "C0") and (r["op_id"] or "").startswith("p")]
    identity = [r for r in check_rows if r["expectation"] == "must_be_accepted"]
    stage_escapes = [r for r in results if r["escaped"] and r["expectation"] == "should_be_caught"]
    content_escapes = [r for r in stage_escapes if r["op_kind"] in ("common", "W", "C0", "sub")]
    new_metrics = {
        "stage": {
            "total": len(results),
            "escapes": len(stage_escapes),
            "escapes_by_class": {c: sum(1 for r in stage_escapes if r["class_id"] == c)
                                 for c in ("AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN")},
            "polarity_probes": {"n": len(polarity_ops),
                                "escapes": sum(1 for r in stage_escapes if r["op_kind"] in ("common", "W", "C0"))},
            "substitution_probes": {"n": len(substitution_ops),
                                    "escapes": sum(1 for r in stage_escapes if r["op_kind"] == "sub")},
            "content_probe_escapes": {"n": len(content_escapes),
                                      "files": [r["file"] for r in content_escapes]},
            "known_rejected_rejected": f"{sum(1 for x in liveness if rejected(x['stage_a'], x['stage_b']))}/{len(liveness)}",
        },
        "candidate_rule": {
            v: {
                "content_probes": new_metric(v, lambda r: r["op_kind"] in ("common", "W", "C0", "sub")),
                "substitution_probes": new_metric(v, lambda r: r["op_kind"] == "sub"),
                "polarity_probes": new_metric(v, lambda r: r["op_kind"] in ("common", "W", "C0") and (r["op_id"] or "").startswith("p")),
                "conforming_controls": new_metric(v, lambda r: r["expectation"] == "must_be_accepted"),
                "known_rejected_flagged": new_metric(v, lambda r: r["expectation"] == "known_rejected_positive_control"),
            } for v in VARIANT_KEYS
        },
    }

    # ------------------------------------------------------------ union-corpus evaluation
    union_out = {}
    pooled = {v: {"escapes": {"n": 0, "flagged": 0}, "conforming_controls": {"n": 0, "flagged": 0},
                  "known_rejected": {"n": 0, "flagged": 0}, "escape_references": {"n": 0, "flagged": 0},
                  "caught_probes": {"n": 0, "flagged": 0}} for v in VARIANT_KEYS}
    per_corpus_escape_files = {}
    for corp, cfg in UNION.items():
        raw = json.loads((ROOT / cfg["raw"]).read_text())
        entries = raw[cfg["list_key"]]
        bases = {k: rfc.yaml.safe_load((ROOT / v).read_bytes()) for k, v in cfg["bases"].items()}
        rows = []
        for e in entries:
            fx = ROOT / e["fixture"]
            fx_doc = rfc.yaml.safe_load(fx.read_bytes())
            cid = e.get("class_id") or fx_doc.get("class_id")
            base_key = e.get("base")
            if base_key not in bases:
                base_key = next((k for k, v in CLASS_OF_BASE.items() if v == cid), None)
            if base_key is None:
                continue
            checks = {v: rfc.check(fx_doc, bases[base_key], v) for v in VARIANT_KEYS}
            escaped = bool(e.get(cfg["escape_field"]))
            role = classify(e.get("expectation", ""), escaped)
            row = {"fixture": e["fixture"], "file": e["file"], "family": e.get("family"), "role": role,
                   "class_id": cid, "escaped": escaped, "resolved_base": cfg["bases"][base_key],
                   "changed_leaf_paths": leaf_diffs(bases[base_key], fx_doc),
                   "checks": {v: {"verdict": c["verdict"], "flags": c["flags"]} for v, c in checks.items()}}
            rows.append(row)
            bucket = {"conforming_control": "conforming_controls", "known_rejected_liveness": "known_rejected",
                      "escape_reference": "escape_references", "escape": "escapes",
                      "caught_probe": "caught_probes"}[role]
            for v in VARIANT_KEYS:
                pooled[v][bucket]["n"] += 1
                if row["checks"][v]["verdict"] == "FLAG":
                    pooled[v][bucket]["flagged"] += 1
        per_corpus_escape_files[corp] = [r["file"] for r in rows if r["role"] in ("escape", "escape_reference")]
        union_out[corp] = {
            "base_note": cfg["base_note"],
            "n": len(rows),
            "role_counts": {role: sum(1 for r in rows if r["role"] == role) for role in
                            ("conforming_control", "known_rejected_liveness", "escape_reference", "escape", "caught_probe")},
            "escape_files": per_corpus_escape_files[corp],
            "rows": rows,
        }
    for v in VARIANT_KEYS:
        pooled[v]["escapes"]["files_caught"] = None  # filled below
    # explicit catch lists for the report, split by role, plus the content axis of each escape
    catch_lists = {}
    axis_table = []
    for corp, out in union_out.items():
        for r in out["rows"]:
            if r["role"] not in ("escape", "escape_reference"):
                continue
            stmt_changed = any(f["field"].startswith("conclusion.statement") for f in r["checks"]["freeze_statements"]["flags"])
            other = [p for p in r["changed_leaf_paths"] if not p.startswith("$.conclusion.statement")]
            axis_table.append({"corpus": corp, "file": r["file"], "role": r["role"],
                               "class_id": r["class_id"], "family": r["family"],
                               "conclusion_statement_changed": stmt_changed,
                               "other_changed_leaf_paths": other[:12],
                               "other_changed_leaf_count": len(other)})
    for v in VARIANT_KEYS:
        caught, missed = [], []
        for corp, out in union_out.items():
            for r in out["rows"]:
                if r["role"] in ("escape", "escape_reference"):
                    (caught if r["checks"][v]["verdict"] == "FLAG" else missed).append(f"{corp}:{r['file']}")
        catch_lists[v] = {"caught": caught, "missed": missed,
                          "catch_rate": (len(caught) / (len(caught) + len(missed))) if (caught or missed) else None}
    stmt_axis = [a for a in axis_table if a["conclusion_statement_changed"]]
    def_axis = [a for a in axis_table if not a["conclusion_statement_changed"]]
    axis_summary = {
        "escape_instances_total": len(axis_table),
        "conclusion_statement_axis": {
            "n": len(stmt_axis), "files": [f"{a['corpus']}:{a['file']}" for a in stmt_axis],
            "freeze_statements_caught": sum(1 for a in stmt_axis
                                            if any(f"{a['corpus']}:{a['file']}" in catch_lists[v]["caught"] for v in ("freeze_statements",))),
        },
        "non_statement_axis": {
            "n": len(def_axis),
            "files": [f"{a['corpus']}:{a['file']}" for a in def_axis],
            "changed_paths": {f"{a['corpus']}:{a['file']}": a["other_changed_leaf_paths"] for a in def_axis},
            "freeze_statements_caught": sum(1 for a in def_axis
                                            if f"{a['corpus']}:{a['file']}" in catch_lists["freeze_statements"]["caught"]),
        },
        "table": axis_table,
    }

    # ------------------------------------------------------------ post-run pins
    shadow_after = {rel: sha256_file(ROOT / rel) for rel in m["shadow_pins"]}
    fixture_hashes_after = {f["fixture"]: sha256_file(ROOT / f["fixture"]) for f in m["fixtures"]}
    if shadow_after != shadow_before:
        invalid.append("pinned shadow drift during run")
    if fixture_hashes_after != fixture_hashes_before:
        invalid.append("fixture drift during run")

    findings = [
        {"finding_id": "W068-P12-F1", "kind": "stage-blind-spot-generalised",
         "statement": ("On the fully pinned three-class shadow, conclusion-statement content substitutions that "
                       "contain no negation marker are accepted by both stages. The content axis is unchecked "
                       "for all three classes, not only for lexical negation flips."),
         "evidence": new_metrics["stage"],
         "falsifier": "An independent re-run of the pinned shadow in which any substitution probe is rejected by stage A or stage B."},
        {"finding_id": "W068-P12-F2", "kind": "candidate-rule-measurement",
         "statement": ("The candidate conclusion-freeze rule (freeze_statements) flags every conclusion-statement "
                       "content probe on the new corpus and every conclusion-statement escape in the union of the "
                       "three earlier corpora, without flagging any conforming control. It does NOT catch escapes "
                       "carried by definitional/other leaves that leave the conclusion statements unchanged."),
         "evidence": {"new_corpus": new_metrics["candidate_rule"]["freeze_statements"],
                      "union": {v: pooled[v] for v in VARIANT_KEYS},
                      "union_catch_lists": catch_lists, "escape_axes": axis_summary},
         "falsifier": "Any conforming control flagged by freeze_statements, or any conclusion-statement escape from the union corpora that it does not flag."},
        {"finding_id": "W068-P12-F3", "kind": "narrow-rule-insufficiency",
         "statement": ("The negation-only baseline variant (negation-marker count comparison) does not see "
                       "non-negation content substitutions; on this corpus it catches the polarity family and "
                       "misses the substitution family."),
         "evidence": {v: new_metrics["candidate_rule"][v] for v in VARIANT_KEYS},
         "falsifier": "A negation-only implementation that flags the substitution probes, or a freeze implementation that misses them."},
        {"finding_id": "W068-P12-F4", "kind": "escape-axis-decomposition",
         "statement": ("The union-corpus escape instances split into two axes: conclusion-statement content "
                       "(freeze_statements catches all of them) and non-statement/definitional content "
                       "(freeze_statements catches none of them; the FORM-HELDOUT-08 reference escapes are of "
                       "this second kind). A complete content-freeze rule needs both a conclusion-statement "
                       "freeze and a definition freeze for the symbols the conclusion depends on."),
         "evidence": axis_summary,
         "falsifier": "An independent leaf-level re-diff showing an escape classified here as non-statement actually changes a conclusion statement, or vice versa."},
    ]

    report = {
        "corpus_id": m["corpus_id"],
        "task_id": m["task_id"],
        "worker": "worker-068",
        "actor": "worker-068",
        "node_id": "A1",
        "gate": "G-CLASSBIND (folded into G-AUDIT as calibration evidence)",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "question": m["question"],
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "manifest_sha256_before_run": manifest_sha,
        "binding": {
            "shadow_pins": {rel: meta["sha256"] for rel, meta in m["shadow_pins"].items()},
            "bases": m["bases"],
            "note": "shadow only; the live tree is not read by this measurement",
        },
        "valid": not invalid,
        "invalid_reasons": invalid,
        "arm_calibration": arm,
        "new_corpus": {"counts": m["counts"], "metrics": new_metrics,
                       "rows": [{k: r[k] for k in ("file", "class_id", "family", "op_id", "op_kind",
                                                   "expectation", "escaped", "catch_rules")} for r in results]},
        "candidate_rule": {"implementation": "artifacts/worker-068/polarity12/conclusion_freeze_check.py",
                           "variants": list(VARIANT_KEYS),
                           "new_corpus": new_metrics["candidate_rule"],
                           "union_corpora": {v: {"pooled": pooled[v], "catch_lists": catch_lists[v]} for v in VARIANT_KEYS},
                           "union_per_corpus": union_out,
                           "union_escape_files": per_corpus_escape_files,
                           "union_escape_axes": axis_summary},
        "findings": findings,
        "limitations": [
            "Author-built corpus: the new probes are worker-068's, calibrated only by the pinned rule spec; an independent reviewer must adjudicate each probe as a genuine class-contract violation.",
            "The union-corpus evaluation re-uses worker-068-built corpora; it is a re-analysis at pinned bytes, not an independent corpus.",
            "freeze_statements flags ANY statement-content change; legitimate post-freeze revisions require re-freezing the class contract. The rule decides content invariance, not mathematics.",
            "The negation_only baseline uses a declared 15-token marker vocabulary; a richer lexical polarity classifier (e.g. worker-003's four-criterion C0 check) may catch some substitution probes it misses.",
            "Worker-068 is the author of the corpora and of this rule candidate; independent replication is required before adoption.",
        ],
        "non_claims": [
            "Not a gate verdict and not a node transition; A1/G-CLASSBIND/G-FORM remain owned by the controller/leads.",
            "No claim about the truth of any class or of cosmic censorship.",
            "No claim that R-CAND is adopted; it is a measured candidate for owner adjudication.",
            "This worker does not claim node completion, validation_status=passed, or any gate verdict.",
        ],
        "falsifier": m["falsifier"],
        "next_falsifier": ("An independent executor (not worker-068) re-runs the pinned shadow and reproduces the "
                           "per-probe verdicts; an independent reviewer adjudicating that a substitution probe is not "
                           "a class-contract violation; or an owner-adopted stage revision at a new hash that rejects "
                           "a probe reported here as escaping."),
    }

    (HERE / "raw_verdicts.json").write_text(json.dumps(
        {"corpus_id": m["corpus_id"], "task_id": m["task_id"], "actor": "worker-068",
         "run_at": report["generated_at"], "manifest_sha256_before_run": manifest_sha,
         "shadow_inputs_before": shadow_before, "shadow_inputs_after": shadow_after,
         "fixture_hashes_before": fixture_hashes_before, "fixture_hashes_after": fixture_hashes_after,
         "valid": report["valid"], "invalid_reasons": invalid, "results": results}, indent=2, sort_keys=True))

    checkpoint = {
        "checkpoint_id": "w068-ckpt-polarity12-1",
        "task_id": m["task_id"],
        "worker": "worker-068",
        "created_at": report["generated_at"],
        "manifest_sha256": manifest_sha,
        "valid": report["valid"],
        "summary": {
            "new_corpus_escapes": new_metrics["stage"]["escapes"],
            "substitution_escapes": new_metrics["stage"]["substitution_probes"]["escapes"],
            "polarity_escapes": new_metrics["stage"]["polarity_probes"]["escapes"],
            "freeze_flag_content_probes": new_metrics["candidate_rule"]["freeze_statements"]["content_probes"]["flagged"],
            "freeze_fp_controls": new_metrics["candidate_rule"]["freeze_statements"]["conforming_controls"]["flagged"],
            "union_escape_catch_freeze": {v: catch_lists[v]["catch_rate"] for v in VARIANT_KEYS},
            "union_control_fp_freeze": pooled["freeze_statements"]["conforming_controls"]["flagged"],
        },
        "artifacts": {p.name: sha256_file(p) for p in sorted(HERE.iterdir()) if p.is_file()},
    }
    (HERE / "checkpoint.json").write_text(json.dumps(checkpoint, indent=2, sort_keys=True))
    (HERE / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True))

    print(json.dumps({"valid": report["valid"], "invalid_reasons": invalid,
                      "new_corpus": new_metrics["stage"],
                      "candidate_rule_new": new_metrics["candidate_rule"],
                      "union_catch_rates": {v: catch_lists[v]["catch_rate"] for v in VARIANT_KEYS},
                      "union_pooled": pooled}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
