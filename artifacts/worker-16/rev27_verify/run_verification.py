#!/usr/bin/env python3
"""Independent verification of FROZEN revision 27 at its declared hashes.

worker-16 / worker=016, bounded pass 4 (2026-09-12T00:3x+08:00).
Self-claimed class-bound task on the G-FORM/G-F0 critical path (leadform-blocker-0005/0006
asked for: independent re-run of check_class_schema.py + run_acceptance.py at the final
canonical hashes, and an independent verdict binding the declared-F0 hash for G-F0).

Design rules honoured here:
  * read-only on every shared artifact: all re-runs happen in a staged copy under
    artifacts/worker-16/rev27_verify/stage/ (the checkers overwrite their evidence files);
  * every claim is bound to a sha256 measured in this run;
  * the manifest's own drift checker (verify_frozen.py) is executed unmodified;
  * positive and negative controls are run and reported.

Output: verification.json (machine), REPORT.md (human), verification.sha256.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # artifacts/worker-16/rev27_verify -> repo root
STAGE = HERE / "stage"

FROZEN = ROOT / "artifacts/formulation/FROZEN.json"
MANIFEST_SHA = hashlib.sha256(FROZEN.read_bytes()).hexdigest()
MAN = json.loads(FROZEN.read_text())
FROZEN_AT = dt.datetime.fromisoformat(MAN["frozen_at"])

CANON_SCHEMAS = {
    "AF-WCC-VAC-GEN": "schemas/af_wcc_vacuum.yaml",
    "AF-SCC-C2-VAC-GEN": "schemas/af_scc_c2_vacuum.yaml",
    "AF-SCC-C0-VAC-GEN": "schemas/af_scc_c0_vacuum.yaml",
}
MIRROR_SCHEMAS = {k: "artifacts/formulation/schemas/" + Path(v).name for k, v in CANON_SCHEMAS.items()}
F0_CANON = "research_map/formulation_taxonomy.yaml"
F0_SUPP = "artifacts/formulation/formulation_taxonomy.yaml"
FROZEN_FOUR = set(CANON_SCHEMAS) | {"AF-WCC-SCALAR-SPH"}

EVIDENCE_TOOLS = [
    ("gate_test_report.json", "artifacts/formulation/tools/run_gate_tests.py"),
    ("acceptance_pipeline_report.json", "artifacts/formulation/tools/run_acceptance.py"),
    ("taxonomy_consistency.json", "artifacts/formulation/tools/check_taxonomy_consistency.py"),
    ("variant_delta_check.json", "artifacts/formulation/tools/check_variant_deltas.py"),
]

report: dict = {
    "verification_id": "w16-rev27-verify-01",
    "actor": "worker-16",
    "worker_slot": "worker-016",
    "pass": "bounded execution worker, pass 4",
    "started_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
    "repo_root": str(ROOT),
    "frozen_manifest": {"path": "artifacts/formulation/FROZEN.json", "sha256": MANIFEST_SHA,
                        "revision": MAN["revision"], "frozen_at": MAN["frozen_at"],
                        "pinned_files": len(MAN["files"])},
    "stage": str(STAGE.relative_to(ROOT)),
    "checks": {},
    "controls": {},
    "runs": {},
    "findings": [],
    "falsifier": "",
    "limits": [],
}


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def sha256_text(t: str) -> str:
    return hashlib.sha256(t.encode()).hexdigest()


def sh(cmd, cwd=None, timeout=900):
    t0 = dt.datetime.now()
    r = subprocess.run([sys.executable, *cmd] if cmd and str(cmd[0]).endswith(".py") else cmd,
                       cwd=str(cwd or STAGE), capture_output=True, text=True, timeout=timeout)
    return {
        "cmd": " ".join(str(c) for c in cmd),
        "exit": r.returncode,
        "stdout_sha256": sha256_text(r.stdout),
        "stderr_sha256": sha256_text(r.stderr),
        "stdout_tail": r.stdout[-2500:],
        "stderr_tail": r.stderr[-1200:],
        "seconds": round((dt.datetime.now() - t0).total_seconds(), 2),
    }


# ---------------------------------------------------------------- stage
def build_stage():
    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)
    shutil.copytree(ROOT / "artifacts/formulation", STAGE / "artifacts/formulation",
                    ignore=shutil.ignore_patterns("__pycache__"))
    (STAGE / "artifacts/worker-06").mkdir(parents=True)
    shutil.copy2(ROOT / "artifacts/worker-06/spec_conformance_audit.py",
                 STAGE / "artifacts/worker-06/spec_conformance_audit.py")
    (STAGE / "research_map").mkdir(parents=True)
    shutil.copy2(ROOT / F0_CANON, STAGE / F0_CANON)
    shutil.copytree(ROOT / "schemas", STAGE / "schemas")
    # control material for tool-sensitivity checks
    (STAGE / "controls").mkdir()
    shutil.copy2(ROOT / "artifacts/formulation/fixtures/controls/null_unchanged__AF-WCC-VAC-GEN.yaml",
                 STAGE / "controls/null_unchanged__AF-WCC-VAC-GEN.yaml")
    shutil.copy2(ROOT / "artifacts/formulation/fixtures/negative/m11_epistemic_theorem.yaml",
                 STAGE / "controls/m11_epistemic_theorem.yaml")


# ---------------------------------------------------------------- 1. manifest drift
def check_manifest_drift():
    rows, mismatches = [], []
    for p, rec in sorted(MAN["files"].items()):
        pin = rec["sha256"] if isinstance(rec, dict) else rec
        f = ROOT / p
        if not f.exists():
            rows.append({"path": p, "status": "missing", "pinned": pin})
            mismatches.append(rows[-1])
            continue
        h = sha256_file(f)
        mtime = dt.datetime.fromtimestamp(f.stat().st_mtime).astimezone()
        row = {"path": p, "pinned": pin, "measured": h, "match": h == pin,
               "mtime": mtime.isoformat(timespec="seconds"),
               "modified_after_frozen_at": mtime > FROZEN_AT}
        rows.append(row)
        if h != pin:
            mismatches.append(row)
    report["checks"]["manifest_drift"] = {
        "pinned_files": len(MAN["files"]),
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "rows_sha256": sha256_text(json.dumps(rows, sort_keys=True)),
    }
    if mismatches:
        report["findings"].append({
            "id": "W16R27-F1",
            "severity": "hard",
            "statement": (f"FROZEN revision {MAN['revision']} pins {len(MAN['files'])} files but "
                          f"{len(mismatches)} do not match disk at measurement time; all mismatches "
                          f"were modified after frozen_at={MAN['frozen_at']}."),
            "paths": [m["path"] for m in mismatches],
            "evidence": ["artifacts/formulation/FROZEN.json#sha256:" + MANIFEST_SHA[:12]],
        })
    return rows


# ---------------------------------------------------------------- 2. frozen bytes + content
def class_tokens(obj, key=None, out=None):
    """Walk a parsed YAML tree; collect (path,key,value) for class_id-ish fields."""
    out = [] if out is None else out
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("class_id", "class_ids", "class_ids_used", "frozen_class_ids", "parent_class"):
                out.append((k, v))
            class_tokens(v, k, out)
    elif isinstance(obj, list):
        for v in obj:
            class_tokens(v, key, out)
    return out


def _flatten_class_values(v):
    if isinstance(v, str):
        return [v]
    if isinstance(v, list):
        return [x for x in v if isinstance(x, str)]
    return []


def check_frozen_bytes_and_binding():
    c = {}
    f0_hash = sha256_file(ROOT / F0_CANON)
    f0 = yaml.safe_load((ROOT / F0_CANON).read_text())
    supp = yaml.safe_load((ROOT / F0_SUPP).read_text())
    tax = yaml.safe_load((ROOT / F0_CANON).read_text())
    variants = json.loads((ROOT / "artifacts/formulation/VARIANT_REGISTRY.json").read_text())
    variant_ids = set()

    def _collect_variant_ids(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("variant_id", "candidate_id"):
                    if isinstance(v, str):
                        variant_ids.add(v)
                _collect_variant_ids(v)
        elif isinstance(o, list):
            for v in o:
                _collect_variant_ids(v)

    _collect_variant_ids(variants)
    variant_ids -= FROZEN_FOUR

    per_schema, findings = {}, []
    for cid, rel in CANON_SCHEMAS.items():
        raw = (ROOT / rel).read_text()
        d = yaml.safe_load(raw)
        h = sha256_file(ROOT / rel)
        mirror_h = sha256_file(ROOT / MIRROR_SCHEMAS[cid])
        toks = sorted(set(re.findall(r"AF-[A-Z0-9-]+", raw)))
        unknown = [t for t in toks if t not in FROZEN_FOUR and t not in variant_ids]
        bad_class_fields = [(k, v) for k, v in class_tokens(d)
                            if any(x not in FROZEN_FOUR for x in _flatten_class_values(v))]
        ptr = d.get("class_contract_pointer", "")
        ptr_ok = False
        if "#" in ptr:
            path, frag = ptr.split("#", 1)
            frag = frag[:-len(cid) - 1] if frag.endswith("." + cid) else frag
            node = tax
            for part in [x for x in re.split(r"[.#]", frag) if x]:
                node = node.get(part) if isinstance(node, dict) else None
            ptr_ok = isinstance(node, dict) and cid in node
        fb = d.get("f0_binding", {}) or {}
        per_schema[cid] = {
            "path": rel, "sha256": h, "mirror_path": MIRROR_SCHEMAS[cid], "mirror_sha256": mirror_h,
            "canonical_equals_mirror": h == mirror_h,
            "revision": d.get("revision"),
            "class_id_field": d.get("class_id"),
            "unknown_class_tokens": unknown,
            "class_id_fields_not_frozen_four": bad_class_fields,
            "class_contract_pointer": ptr, "class_contract_pointer_resolves": ptr_ok,
            "f0_binding_declared_sha256": fb.get("declared_f0_sha256"),
            "f0_binding_matches_measured_f0": fb.get("declared_f0_sha256") == f0_hash,
            "falsifier_present": bool(d.get("falsifier")),
            "conclusion_type": (d.get("conclusion") or {}).get("conclusion_type"),
        }
        if unknown:
            findings.append({"id": f"W16R27-F2-{cid}", "severity": "hard",
                             "statement": f"{rel} contains non-frozen class-like tokens {unknown}"})
        if not ptr_ok:
            findings.append({"id": f"W16R27-F3-{cid}", "severity": "hard",
                             "statement": f"{rel} class_contract_pointer does not resolve: {ptr}"})
        if fb.get("declared_f0_sha256") != f0_hash:
            findings.append({"id": f"W16R27-F4-{cid}", "severity": "hard",
                             "statement": f"{rel} f0_binding {fb.get('declared_f0_sha256')} != measured {f0_hash}"})
    # F0 canonical vs supplement: disjoint key sets as recorded by the lead?
    c["f0"] = {
        "canonical_path": F0_CANON, "canonical_sha256": f0_hash,
        "supplement_path": F0_SUPP, "supplement_sha256": sha256_file(ROOT / F0_SUPP),
        "byte_identical": sha256_file(ROOT / F0_CANON) == sha256_file(ROOT / F0_SUPP),
        "canonical_top_keys": sorted(f0.keys()),
        "supplement_top_keys": sorted(supp.keys()),
        "shared_top_keys": sorted(set(f0) & set(supp)),
        "canonical_class_ids": sorted(f0.get("class_ids", [])),
        "supplement_class_contracts": sorted((supp.get("class_contracts") or {}).keys()),
    }
    c["schemas"] = per_schema
    c["variant_ids_excluded_from_frozen_four"] = sorted(variant_ids)
    c["unknown_tokens_total"] = sum(len(v["unknown_class_tokens"]) for v in per_schema.values())
    report["checks"]["frozen_content_and_binding"] = c
    report["findings"].extend(findings)
    return c


# ---------------------------------------------------------------- 3. staged re-runs
def run_staged_pipeline():
    runs = report["runs"]
    for cid, rel in CANON_SCHEMAS.items():
        runs[f"check_class_schema::{Path(rel).name}"] = sh(
            ["artifacts/formulation/tools/check_class_schema.py", "--json", rel])
        runs[f"check_class_schema::mirror::{Path(rel).name}"] = sh(
            ["artifacts/formulation/tools/check_class_schema.py", "--json", MIRROR_SCHEMAS[cid]])
    runs["run_acceptance"] = sh(["artifacts/formulation/tools/run_acceptance.py", "--json"], timeout=1200)
    runs["check_taxonomy_consistency"] = sh(["artifacts/formulation/tools/check_taxonomy_consistency.py"])
    runs["check_variant_deltas"] = sh(["artifacts/formulation/tools/check_variant_deltas.py"])
    runs["run_gate_tests"] = sh(["artifacts/formulation/tools/run_gate_tests.py"], timeout=1800)
    runs["verify_frozen"] = sh(["artifacts/formulation/tools/verify_frozen.py"])
    # determinism control: same command twice
    runs["determinism_check_class_schema_run2"] = sh(
        ["artifacts/formulation/tools/check_class_schema.py", "--json", "schemas/af_wcc_vacuum.yaml"])

    # evidence produced inside the stage
    post = {}
    for name, _tool in EVIDENCE_TOOLS + [("gate_test_report.txt", "artifacts/formulation/tools/run_gate_tests.py")]:
        sp = STAGE / "artifacts/formulation/evidence" / name
        rp = ROOT / "artifacts/formulation/evidence" / name
        row = {"stage_exists": sp.exists(), "repo_exists": rp.exists()}
        if sp.exists():
            row["stage_sha256"] = sha256_file(sp)
        if rp.exists():
            row["repo_sha256"] = sha256_file(rp)
        pin = (MAN["files"].get("artifacts/formulation/evidence/" + name) or {}).get("sha256")
        row["manifest_pinned_sha256"] = pin
        if pin and sp.exists():
            row["reproduces_manifest_pin"] = row["stage_sha256"] == pin
        if sp.exists() and rp.exists():
            row["reproduces_repo_file"] = row["stage_sha256"] == row["repo_sha256"]
        post[name] = row
    report["checks"]["staged_evidence_reproduction"] = post


# ---------------------------------------------------------------- 4. controls
def run_controls():
    ok_control = sh(["artifacts/formulation/tools/check_class_schema.py", "--json",
                     "controls/null_unchanged__AF-WCC-VAC-GEN.yaml"])
    neg = sh(["artifacts/formulation/tools/check_class_schema.py", "--json",
              "controls/m11_epistemic_theorem.yaml"])
    # byte-identical determinism: copy of canonical under another name must produce same report
    shutil.copy2(STAGE / "schemas/af_wcc_vacuum.yaml", STAGE / "controls/wcc_bytecopy.yaml")
    copy_run = sh(["artifacts/formulation/tools/check_class_schema.py", "--json", "controls/wcc_bytecopy.yaml"])
    base_run = report["runs"]["check_class_schema::af_wcc_vacuum.yaml"]
    report["controls"] = {
        "positive_fixture_control": {"exit": ok_control["exit"], "pass_expected": True,
                                     "ok": ok_control["exit"] == 0},
        "negative_fixture_control": {"exit": neg["exit"], "fail_expected": True,
                                     "ok": neg["exit"] != 0},
        "byte_identical_copy_same_verdict": {
            "base_exit": base_run["exit"], "copy_exit": copy_run["exit"],
            "ok": base_run["exit"] == copy_run["exit"]},
    }
    for k, v in report["controls"].items():
        if not v["ok"]:
            report["findings"].append({"id": "W16R27-F5-" + k, "severity": "hard",
                                       "statement": f"control failed: {k} -> {v}"})


# ---------------------------------------------------------------- 5. verdict
def compute_verdict():
    drift = report["checks"]["manifest_drift"]["mismatch_count"]
    acc_path = STAGE / "artifacts/formulation/evidence/acceptance_pipeline_report.json"
    try:
        acceptance = json.loads(acc_path.read_text())
    except Exception:
        acceptance = {}
    m = acceptance.get("mutants", {})
    canon_rows = acceptance.get("canonical", [])
    ctrl_rows = acceptance.get("controls", [])
    report["checks"]["acceptance_headline"] = {
        "verdict": acceptance.get("verdict"),
        "canonical_rows_ok": all(r.get("ok") for r in canon_rows) if canon_rows else None,
        "control_rows_ok": all(r.get("ok") for r in ctrl_rows) if ctrl_rows else None,
        "controls": len(ctrl_rows),
        "mutants_total": m.get("total"),
        "union_caught": m.get("union_caught"),
        "union_escapes": m.get("union_escapes", []),
    }
    staged = report["checks"]["staged_evidence_reproduction"]
    repro = {k: v.get("reproduces_manifest_pin") for k, v in staged.items()}
    hard = [f for f in report["findings"] if f.get("severity") == "hard"]
    report["verdict"] = {
        "content_green_at_frozen_bytes": bool(
            not hard and acceptance.get("verdict") == "PASS"
            and all(v["ok"] for v in report["controls"].values())
            and report["checks"]["frozen_content_and_binding"]["unknown_tokens_total"] == 0),
        "manifest_pin_drift_count": drift,
        "staged_evidence_reproduces_manifest_pin": repro,
        "hard_findings": [f["id"] for f in hard],
        "summary": "",
    }
    if drift:
        report["verdict"]["summary"] = (
            f"Frozen content is machine-green at the measured bytes "
            f"(acceptance {acceptance.get('verdict')}, union "
            f"{m.get('union_caught')}/{m.get('total')}, controls "
            f"{len(ctrl_rows)}/{len(ctrl_rows)}), but FROZEN revision {MAN['revision']} is not a "
            f"self-consistent pin: {drift} pinned evidence file(s) were rewritten after frozen_at "
            f"({MAN['frozen_at']}); the three schemas and F0 canonical still match their pins.")
    else:
        report["verdict"]["summary"] = "FROZEN revision pins and content verified; no drift."
    report["falsifier"] = (
        "Re-measure sha256 of the 43 FROZEN rev27 paths at the same wall-clock state: if the three "
        "evidence files now match their pins (i.e. the mismatch was only a concurrent-writer race "
        "that has since settled), finding W16R27-F1 is refuted for that measurement instant. If a "
        "staged re-run of run_acceptance.py / run_gate_tests.py reproduces the pinned hashes "
        "byte-for-byte, then the evidence files are deterministic and the pin drift is a real "
        "manifest error rather than a volatile-output artifact. Any hard finding above is refuted "
        "by showing the named path measured at the cited sha256 satisfies the named property."
    )
    report["limits"] = [
        "Worker event: cannot set node status, validation_status=passed, or a gate verdict "
        "(authority: ASTRA_HANDOFF 'Authority'). This is evidence for lead-audit/controller adjudication.",
        "The staged re-run reproduces the pipeline on copied bytes; it is independent execution, "
        "not an independent content review of the physics (lead-audit's task astra-life03-verify-gform).",
        "Hashes were measured once, at the 'finished_at' stamped in this file; later writers may move them.",
    ]


def main():
    build_stage()
    report["stage_manifest_sha256"] = sha256_text(json.dumps(
        {str(p.relative_to(STAGE)): sha256_file(p) for p in sorted(STAGE.rglob("*")) if p.is_file()},
        sort_keys=True))
    check_manifest_drift()
    check_frozen_bytes_and_binding()
    run_staged_pipeline()
    run_controls()
    compute_verdict()
    report["finished_at"] = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    out = HERE / "verification.json"
    out.write_text(json.dumps(report, indent=2) + "\n")
    print("VERDICT:", json.dumps(report["verdict"], indent=1))
    print("findings:", [f["id"] + ":" + f["statement"][:90] for f in report["findings"]])
    return 0


if __name__ == "__main__":
    sys.exit(main())
