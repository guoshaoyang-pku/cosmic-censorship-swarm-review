#!/usr/bin/env python3
"""W068-FORM-HELDOUT-09-REPL — independent replication harness for FORM-HELDOUT-09.

Class-bound to AF-WCC-VAC-GEN / AF-SCC-C2-VAC-GEN / AF-SCC-C0-VAC-GEN; node A1;
gate G-CLASSBIND (calibration evidence folded into G-AUDIT).

This script does NOT reuse artifacts/worker-068/heldout3/run_heldout3.py. It is a
second, independent harness that:

  1. re-derives every frozen binding (FROZEN.json, three canonical schemas, both
     stage tools, rule spec) and refuses to proceed on drift;
  2. re-runs both frozen stages directly over all 49 heldout3 fixtures;
  3. compares per-fixture stage verdicts and failed-rule sets with the frozen
     raw_verdicts.json (mismatch count is the replication result);
  4. recomputes all aggregates, per-class rates, per-family rates and the union
     escape-family list from its own verdicts and diffs them against report.json;
  5. builds 3 additional conforming controls (4 -> 7 total, satisfying the
     astra-life03-heldout-09 ">=7 controls that must pass both stages") plus one
     declared format probe that is reported separately and is NOT a control.

Everything is measurement: no gate verdict, no node completion, no theorem.
Independence limit (stated, not hidden): harness-independent, not
agent-independent — the original corpus was also built by worker-068.

Usage: python3 replicate_heldout09.py
Exit: 0 replication completed (match OR mismatch); 2 precondition failure.
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
SRC = ROOT / "artifacts" / "worker-068" / "heldout3"
CTRL_EXT = HERE / "controls_ext"
DIAG = HERE / "diag"
PY = sys.executable
CST = timezone(timedelta(hours=8))
TASK_ID = "W068-FORM-HELDOUT-09-REPL"
CORPUS_ID = "FORM-HELDOUT-09"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run_cmd(args, timeout=180):
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


def stage_verdict(fixture_rel: str, stage: str, manifest: dict, tag: str):
    """Run one frozen stage and return an independently parsed verdict."""
    path = ROOT / fixture_rel
    if stage == "structural":
        r = run_cmd([PY, str(ROOT / manifest["stages"]["structural"]), "--json", str(path)])
        j = parse_json(r["stdout"])
    else:
        out = DIAG / f"{tag}.semantic.json"
        r = run_cmd([PY, str(ROOT / manifest["stages"]["semantic"]), str(path), "--json", str(out)])
        j = parse_json(r["stdout"])
        if j is None and out.exists():
            j = parse_json(out.read_text())
    j = j or {}
    return {
        "exit": r["exit"],
        "verdict": j.get("verdict", "error"),
        "failed_rules": sorted(j.get("failed_rules", []) or []),
        "undecided_rules": sorted(j.get("undecided_rules", []) or []),
        "stderr_tail": r["stderr"][-400:],
    }


def build_extended_controls() -> dict:
    """Three semantics-preserving presentational edits + one declared format probe."""
    src_ctrl = SRC / "controls"
    out = {}
    base_w = (src_ctrl / "ctrl_w_sorted_roundtrip.yaml").read_text()
    base_c2 = (src_ctrl / "ctrl_c2_antiscope_note.yaml").read_text()
    base_c0 = (src_ctrl / "ctrl_c0_variant_registered.yaml").read_text()

    c05 = CTRL_EXT / "c05_comment_prepend.yaml"
    c05.write_text("# HELDOUT-09R conforming control c05: comment prepended, no other change.\n" + base_w)
    out["c05"] = c05

    c06 = CTRL_EXT / "c06_comment_append_blank_eof.yaml"
    c06.write_text(base_c2 + "\n# HELDOUT-09R conforming control c06: comment + blank lines appended at EOF.\n\n\n")
    out["c06"] = c06

    c07 = CTRL_EXT / "c07_renamed_identical_copy.yaml"
    c07.write_bytes((src_ctrl / "ctrl_c0_variant_registered.yaml").read_bytes())
    out["c07"] = c07

    probe = CTRL_EXT / "probe_pyyaml_resorted_c0.yaml"
    try:
        import yaml  # PyYAML present (6.0.3)
        loaded = yaml.safe_load(base_c0)
        probe.write_text(yaml.safe_dump(loaded, sort_keys=True, default_flow_style=False, width=1000))
    except Exception as exc:  # pragma: no cover - recorded, not fatal
        probe.write_text(f"# probe construction failed: {exc}\n")
    out["probe"] = probe
    return out


def main() -> int:
    manifest_path = SRC / "manifest.json"
    raw_path = SRC / "raw_verdicts.json"
    report_path = SRC / "report.json"
    for p in (manifest_path, raw_path, report_path):
        if not p.exists():
            print(f"PRECONDITION FAIL: missing {p}")
            return 2

    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    raw = json.loads(raw_path.read_text())
    report = json.loads(report_path.read_text())
    binding = manifest["frozen_revision_binding"]

    problems: list[str] = []
    evidence: dict = {}

    # ---- 1. binding re-measurement -----------------------------------------
    manifest_sha_now = hashlib.sha256(manifest_bytes).hexdigest()
    evidence["manifest"] = {
        "path": str(manifest_path.relative_to(ROOT)),
        "sha256_now": manifest_sha_now,
        "sha256_recorded_before_run": raw.get("manifest_sha256_before_run"),
        "report_agrees": report.get("manifest_sha256_before_run") == raw.get("manifest_sha256_before_run"),
        "unchanged_since_run": manifest_sha_now == raw.get("manifest_sha256_before_run"),
        "mtime_order": {
            "manifest": datetime.fromtimestamp(manifest_path.stat().st_mtime, CST).isoformat(timespec="seconds"),
            "raw_verdicts": datetime.fromtimestamp(raw_path.stat().st_mtime, CST).isoformat(timespec="seconds"),
            "report": datetime.fromtimestamp(report_path.stat().st_mtime, CST).isoformat(timespec="seconds"),
        },
        "manifest_before_any_stage_run": manifest_path.stat().st_mtime <= raw_path.stat().st_mtime,
    }
    if not evidence["manifest"]["unchanged_since_run"]:
        problems.append("manifest differs from the hash recorded before the frozen run")
    if not evidence["manifest"]["manifest_before_any_stage_run"]:
        problems.append("manifest mtime is not <= raw-verdict mtime (hash ordering unproven)")

    frozen_path = ROOT / binding["frozen_manifest"]
    frozen_sha = sha256_file(frozen_path) if frozen_path.exists() else None
    frozen_now = json.loads(frozen_path.read_text()) if frozen_path.exists() else {}
    frozen_files = frozen_now.get("files", {})
    pinned_content = {rel: pin for rel, pin in binding["schemas"].items()}
    frozen_still_pins_content = {
        rel: frozen_files.get(rel, {}).get("sha256") == pin for rel, pin in pinned_content.items()
    }
    # manifest-level supersession is distinct from content drift: if every content
    # artifact the measurement binds (schemas/stages/rule spec) is unchanged, a later
    # FROZEN revision is a moving-target note, not an invalidation of the measurement.
    manifest_superseded = frozen_sha != binding["frozen_manifest_sha256"]
    content_unchanged_in_new_manifest = all(frozen_still_pins_content.values())
    evidence["frozen_manifest"] = {
        "path": binding["frozen_manifest"],
        "sha256_now": frozen_sha,
        "pinned": binding["frozen_manifest_sha256"],
        "pinned_revision": binding["revision"],
        "revision_now": frozen_now.get("revision"),
        "frozen_at_now": frozen_now.get("frozen_at"),
        "superseded_after_run": manifest_superseded,
        "new_manifest_still_pins_same_schemas": frozen_still_pins_content,
        "rev26_delta_now": frozen_now.get("rev26_delta"),
        "mtime_now": datetime.fromtimestamp(frozen_path.stat().st_mtime, CST).isoformat(timespec="seconds")
        if frozen_path.exists() else None,
        "run_recorded_no_drift_at_run_time": raw.get("canonical_drift_after_build") == {},
    }
    if manifest_superseded and not content_unchanged_in_new_manifest:
        problems.append("FROZEN.json superseded AND the new manifest no longer pins the bound schemas")

    schema_evidence = {}
    for rel, pin in binding["schemas"].items():
        live = sha256_file(ROOT / rel)
        schema_evidence[rel] = {"pinned": pin, "live": live, "match": live == pin}
        if live != pin:
            problems.append(f"canonical schema drift: {rel}")
    evidence["schemas"] = schema_evidence

    stage_evidence = {}
    for key, rel in (("structural", manifest["stages"]["structural"]),
                     ("semantic", manifest["stages"]["semantic"]),
                     ("rule_spec", manifest["stages"]["rule_spec"])):
        live = sha256_file(ROOT / rel)
        pin = manifest["stages"][f"{key}_sha256"]
        stage_evidence[key] = {"path": rel, "pinned": pin, "live": live, "match": live == pin}
        if live != pin:
            problems.append(f"stage tool drift: {rel}")
    evidence["stages"] = stage_evidence

    # ---- 2/3. re-run both stages over every fixture ------------------------
    frozen_by_file = {v["file"]: v for v in raw["fixtures"]}
    if set(frozen_by_file) != {f["file"] for f in manifest["fixtures"]}:
        problems.append("manifest fixture set != frozen raw-verdict fixture set")

    rep_verdicts = []
    mismatches = []
    for fx in manifest["fixtures"]:
        rel = fx["fixture"]
        disk = sha256_file(ROOT / rel)
        if disk != fx["sha256"]:
            problems.append(f"fixture tamper: {rel}")
        tag = Path(rel).stem
        a = stage_verdict(rel, "structural", manifest, tag)
        b = stage_verdict(rel, "semantic", manifest, tag)
        caught_a = a["verdict"] != "pass"
        caught_b = b["verdict"] != "accept"
        escaped = (not caught_a) and (not caught_b)
        fz = frozen_by_file.get(fx["file"], {})
        cmp = {
            "stage_a_verdict": fz.get("stage_a", {}).get("verdict") == a["verdict"],
            "stage_b_verdict": fz.get("stage_b", {}).get("verdict") == b["verdict"],
            "stage_a_failed_rules": sorted(fz.get("stage_a", {}).get("failed_rules", [])) == a["failed_rules"],
            "stage_b_failed_rules": sorted(fz.get("stage_b", {}).get("failed_rules", [])) == b["failed_rules"],
            "caught_stage_a": fz.get("caught_stage_a") == caught_a,
            "caught_stage_b": fz.get("caught_stage_b") == caught_b,
            "escaped_union": fz.get("escaped_union") == escaped,
        }
        if not all(cmp.values()):
            mismatches.append({"file": fx["file"], "class_id": fx["class_id"], "family": fx["family"],
                               "checks": cmp, "frozen": {"stage_a": fz.get("stage_a", {}).get("verdict"),
                                                         "stage_b": fz.get("stage_b", {}).get("verdict"),
                                                         "failed_rules": sorted(fz.get("stage_a", {}).get("failed_rules", []))
                                                         + sorted(fz.get("stage_b", {}).get("failed_rules", []))},
                               "replication": {"stage_a": a["verdict"], "stage_b": b["verdict"],
                                               "failed_rules": a["failed_rules"] + b["failed_rules"]}})
        rep_verdicts.append({
            "fixture": rel, "file": fx["file"], "class_id": fx["class_id"], "family": fx["family"],
            "expectation": fx["expectation"], "sha256": fx["sha256"],
            "stage_a": a, "stage_b": b,
            "caught_stage_a": caught_a, "caught_stage_b": caught_b, "escaped_union": escaped,
            "matches_frozen": all(cmp.values()),
        })

    # ---- 4. recompute aggregates independently -----------------------------
    leaky = [r for r in rep_verdicts if r["expectation"] in ("should_be_caught", "probe")]
    probes = [r for r in rep_verdicts if r["expectation"] == "probe"]
    controls = [r for r in rep_verdicts if r["expectation"] == "must_be_accepted"]
    known = [r for r in rep_verdicts if r["expectation"] == "known_rejected_positive_control"]
    known_esc = [r for r in rep_verdicts if r["expectation"] == "known_escape_reference"]

    escaped_leaky = [r for r in leaky if r["escaped_union"]]

    def rate(rows):
        return (sum(1 for r in rows if r["escaped_union"]) / len(rows)) if rows else None

    per_class: dict = {}
    per_family: dict = {}
    rule_hits: dict = {}
    for r in leaky:
        c = r["class_id"] or "unknown"
        d = per_class.setdefault(c, {"leaky": 0, "escaped": 0, "caught_stage_a": 0, "caught_stage_b": 0})
        d["leaky"] += 1
        d["escaped"] += int(r["escaped_union"])
        d["caught_stage_a"] += int(r["caught_stage_a"])
        d["caught_stage_b"] += int(r["caught_stage_b"])
        f = per_family.setdefault(r["family"], {"count": 0, "escaped": 0, "fixtures": []})
        f["count"] += 1
        f["escaped"] += int(r["escaped_union"])
        f["fixtures"].append(r["file"])
        for rule in (manifest["fixtures"][[x["file"] for x in manifest["fixtures"]].index(r["file"])]
                     .get("expected_catcher_rules") or []):
            if rule == "NONE":
                continue
            fired = rule in (r["stage_a"]["failed_rules"] + r["stage_b"]["failed_rules"])
            d2 = rule_hits.setdefault(rule, {"expected": 0, "fired": 0})
            d2["expected"] += 1
            d2["fired"] += int(fired)
    for c, d in per_class.items():
        d["escape_rate"] = d["escaped"] / d["leaky"]
    escape_families = sorted(
        [{"family": f, "count": d["count"], "escaped": d["escaped"], "fixtures": sorted(d["fixtures"])}
         for f, d in per_family.items() if d["escaped"] > 0],
        key=lambda x: (-x["escaped"], x["family"]))

    rep_aggregates = {
        "leaky": len(leaky),
        "leaky_escaped_union": len(escaped_leaky),
        "union_escape_rate": rate(leaky),
        "caught_stage_a": sum(1 for r in leaky if r["caught_stage_a"]),
        "caught_stage_b": sum(1 for r in leaky if r["caught_stage_b"]),
        "union_caught": sum(1 for r in leaky if not r["escaped_union"]),
        "probes": len(probes),
        "probes_escaped": sum(1 for r in probes if r["escaped_union"]),
        "conforming_controls": len(controls),
        "false_positives": sum(1 for r in controls if r["escaped_union"] is False
                               and (r["caught_stage_a"] or r["caught_stage_b"])),
        "known_rejected_controls": len(known),
        "known_rejected_controls_rejected": sum(1 for r in known if r["caught_stage_a"] or r["caught_stage_b"]),
        "known_escape_references": len(known_esc),
        "known_escape_references_still_escaping": sum(1 for r in known_esc if r["escaped_union"]),
    }
    fro_agg = report.get("aggregates", {})
    agg_diff = {k: {"replication": v, "frozen": fro_agg.get(k)} for k, v in rep_aggregates.items()
                if fro_agg.get(k) != v}
    class_diff = {c: {"replication": d, "frozen": report.get("per_class", {}).get(c)}
                  for c, d in per_class.items() if report.get("per_class", {}).get(c) != d}
    fam_diff = {f: {"replication": {"count": d["count"], "escaped": d["escaped"]},
                    "frozen": {k: v for k, v in report.get("per_family", {}).get(f, {}).items() if k != "fixtures"}}
                for f, d in per_family.items()
                if {k: v for k, v in report.get("per_family", {}).get(f, {}).items() if k != "fixtures"}
                != {"count": d["count"], "escaped": d["escaped"]}}
    fam_list_match = escape_families == report.get("escape_families")
    rule_diff = {r: {"replication": d, "frozen": {k: v for k, v in
                                                  report.get("expected_rule_hit_matrix", {}).get(r, {}).items()
                                                  if k in ("expected", "fired")}}
                 for r, d in rule_hits.items()
                 if {k: v for k, v in report.get("expected_rule_hit_matrix", {}).get(r, {}).items()
                     if k in ("expected", "fired")} != d}
    if agg_diff or class_diff or fam_diff or not fam_list_match or rule_diff:
        problems.append("recomputed aggregates differ from the frozen report")

    # ---- 5. extended controls (3 new conforming + 1 declared format probe) --
    ext = build_extended_controls()
    ext_rows = []
    for key, path in ext.items():
        rel = str(path.relative_to(ROOT))
        a = stage_verdict(rel, "structural", manifest, f"ext_{key}")
        b = stage_verdict(rel, "semantic", manifest, f"ext_{key}")
        accepted = (a["verdict"] == "pass") and (b["verdict"] == "accept")
        ext_rows.append({
            "control": key, "fixture": rel, "sha256": sha256_file(path),
            "is_declared_control": key != "probe",
            "stage_a_verdict": a["verdict"], "stage_b_verdict": b["verdict"],
            "stage_a_failed_rules": a["failed_rules"], "stage_b_failed_rules": b["failed_rules"],
            "accepted_by_both": accepted,
        })
    ext_controls = [r for r in ext_rows if r["is_declared_control"]]
    ext_probe = [r for r in ext_rows if not r["is_declared_control"]]
    controls_total = len(controls) + len(ext_controls)
    if not all(r["accepted_by_both"] for r in ext_controls):
        problems.append("extended conforming control rejected by at least one stage "
                        "(format-sensitivity finding, reported not hidden)")

    control_extension = {
        "task_id": TASK_ID, "created_at": now(),
        "source_controls": [r["file"] for r in controls],
        "added_conforming_controls": ext_controls,
        "declared_format_probe": ext_probe,
        "conforming_controls_before": len(controls),
        "conforming_controls_after": controls_total,
        "meets_ge_7_controls": controls_total >= 7,
        "false_positives_added": sum(1 for r in ext_controls if not r["accepted_by_both"]),
        "falsifier": ("Any extended control that is rejected by either stage is a format-sensitivity "
                      "finding; any control whose edit is shown to change semantics is not a control."),
    }
    (HERE / "control_extension_report.json").write_text(json.dumps(control_extension, indent=2) + "\n")

    # ---- 6. emit replication artifacts -------------------------------------
    replication = {
        "corpus_id": CORPUS_ID,
        "task_id": TASK_ID,
        "worker": "worker-068",
        "actor": "worker-068",
        "created_at": now(),
        "node_id": "A1",
        "gate": "G-CLASSBIND (folded into G-AUDIT as calibration evidence)",
        "class_ids": CLASS_IDS,
        "replicates": {
            "manifest": "artifacts/worker-068/heldout3/manifest.json#" + manifest_sha_now[:12],
            "raw_verdicts": "artifacts/worker-068/heldout3/raw_verdicts.json#" + sha256_file(raw_path)[:12],
            "report": "artifacts/worker-068/heldout3/report.json#" + sha256_file(report_path)[:12],
        },
        "binding_evidence": evidence,
        "method": ("Own harness; no code imported from run_heldout3.py. Both frozen stage tools re-run "
                   "directly on all 49 fixtures; per-fixture verdicts and failed-rule sets compared to "
                   "the frozen raw_verdicts.json; aggregates recomputed from scratch."),
        "fixtures_compared": len(rep_verdicts),
        "per_fixture_mismatches": mismatches,
        "mismatch_count": len(mismatches),
        "aggregates_replication": rep_aggregates,
        "aggregates_frozen": {k: fro_agg.get(k) for k in rep_aggregates},
        "aggregate_diff": agg_diff,
        "per_class_replication": per_class,
        "per_class_diff": class_diff,
        "per_family_diff": fam_diff,
        "escape_families_replication": escape_families,
        "escape_families_match": fam_list_match,
        "rule_hit_diff": rule_diff,
        "control_extension_ref": "artifacts/worker-068/heldout09r/control_extension_report.json",
        "conforming_controls_total": controls_total,
        "manifest_supersession": {
            "detected": manifest_superseded,
            "pinned_at_run": binding["frozen_manifest_sha256"],
            "measured_now": frozen_sha,
            "run_recorded_no_drift_at_run_time": evidence["frozen_manifest"]["run_recorded_no_drift_at_run_time"],
            "new_manifest_still_pins_same_schemas": evidence["frozen_manifest"]["new_manifest_still_pins_same_schemas"],
            "note": ("FROZEN.json rev25 -> rev26 is an F0 publication adjudication request; the three "
                     "class schemas and both stage tools are unchanged, so it is a moving-target note "
                     "for the manifest hash, not a content-drift invalidation of this measurement."
                     if manifest_superseded else "no manifest movement between run and replication"),
        },
        "content_binding_valid": not problems,
        "valid": not problems,
        "problems": problems,
        "verdict": ("not_replicated" if (problems or mismatches)
                    else ("replicated_with_manifest_supersession" if manifest_superseded else "replicated")),
        "limitations": [
            "Harness-independent but NOT agent-independent: the corpus under replication was built by "
            "worker-068, so this is a method replication, not a second-author replication.",
            "The two stage tools are the frozen objects under test; their bytes are re-verified but not "
            "re-implemented.",
            "Acceptance by both stages is evidence about the pipeline only, not a class-truth claim.",
            "No gate verdict, node completion, or validation_status=passed is claimed by this worker.",
        ],
        "falsifier": ("Any per-fixture verdict/rule mismatch against the frozen raw verdicts; any drift in "
                      "the three canonical schemas / both stage tools / the rule spec between build and "
                      "replication; any aggregate or escape-family-list disagreement with the frozen report; "
                      "an independent reviewer showing an extended control is not semantics-preserving."),
        "next_falsifier": ("A second executor (not worker-068, not worker-16) re-runs this harness and "
                           "reproduces mismatch_count=0, or an independent reviewer adjudicates "
                           "c0_03_conclusion_negated to close the polarity blind spot."),
    }
    (HERE / "replication_report.json").write_text(json.dumps(replication, indent=2) + "\n")

    raw_rep = {
        "corpus_id": CORPUS_ID, "task_id": TASK_ID, "actor": "worker-068", "run_at": now(),
        "manifest_sha256_now": manifest_sha_now,
        "frozen_binding": binding,
        "mismatch_count": len(mismatches),
        "valid": not problems,
        "problems": problems,
        "fixtures": rep_verdicts,
    }
    (HERE / "raw_replication_verdicts.json").write_text(json.dumps(raw_rep, indent=2) + "\n")

    print(json.dumps({
        "task_id": TASK_ID,
        "valid": not problems,
        "problems": problems,
        "fixtures_compared": len(rep_verdicts),
        "mismatch_count": len(mismatches),
        "aggregates_replication": rep_aggregates,
        "escape_families_match": fam_list_match,
        "controls_total": controls_total,
        "extended_controls_accepted": [r["control"] for r in ext_controls if r["accepted_by_both"]],
        "probe_accepted": ext_probe[0]["accepted_by_both"] if ext_probe else None,
        "manifest_supersession": replication["manifest_supersession"],
        "verdict": replication["verdict"],
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
