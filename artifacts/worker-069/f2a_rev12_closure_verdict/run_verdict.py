#!/usr/bin/env python3
"""Runner for W069-F2A-REV12-CLOSURE-VERDICT-01.

Pins the rev12 closure bytes, snapshots them, runs the independent rev12 checker (with its
built-in mutation selftest), adds file-level closure controls (text mutations of the snapshot),
re-runs the canonical repo tools on the pinned bytes, reconciles FROZEN rev27 pins, and writes
report.json + raw/* + SHA256SUMS. Read-only on every canonical path except run_acceptance.py's own
deterministic evidence file, whose bytes are asserted against the FROZEN pin.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
CST = timezone(timedelta(hours=8))
RAW = HERE / "raw"
SNAP = HERE / "snapshot"
CTRL = HERE / "controls"

PIN = {
    "schema": "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
    "f0": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "supplement": "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "registry": "5eb42f9a384a2bb327f1849fa571778fd88a2c5bf90f8a2c92d570383eb1363b",
    "aliases": "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba",
}
FROZEN_REV = 28
ACCEPTANCE_PIN = "9b7d6c8208d3beae2510c5c9c0a4bdaf7ede8adb277cd2a4f6f9cd0fd430f0c6"

CANON = {
    "schema": REPO / "schemas/af_scc_c2_vacuum.yaml",
    "mirror": REPO / "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
    "f0": REPO / "research_map/formulation_taxonomy.yaml",
    "supplement": REPO / "artifacts/formulation/formulation_taxonomy.yaml",
    "registry": REPO / "artifacts/formulation/VARIANT_REGISTRY.json",
    "aliases": REPO / "artifacts/formulation/VOCAB_ALIASES.json",
    "frozen": REPO / "artifacts/formulation/FROZEN.json",
    "acceptance_evidence": REPO / "artifacts/formulation/evidence/acceptance_pipeline_report.json",
}


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def run(cmd: list[str], out_name: str, expect_zero: bool = True, timeout: int = 900) -> dict:
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO, timeout=timeout)
    body = (p.stdout or "") + (("\n[stderr]\n" + p.stderr) if p.stderr else "")
    (RAW / out_name).write_text(body)
    return {"cmd": " ".join(cmd), "exit": p.returncode,
            "stdout_sha256": hashlib.sha256(body.encode()).hexdigest(),
            "raw": f"raw/{out_name}", "expected_exit_zero": expect_zero,
            "ok": (p.returncode == 0) if expect_zero else None}


def snapshot_inputs() -> dict:
    SNAP.mkdir(exist_ok=True)
    files = {
        "af_scc_c2_vacuum.yaml": CANON["schema"],
        "formulation_taxonomy.yaml": CANON["f0"],
        "formulation_taxonomy_supplement.yaml": CANON["supplement"],
        "VARIANT_REGISTRY.json": CANON["registry"],
        "VOCAB_ALIASES.json": CANON["aliases"],
        "FROZEN.json": CANON["frozen"],
    }
    out = {}
    for name, src in files.items():
        dst = SNAP / name
        shutil.copyfile(src, dst)
        out[name] = {"source": str(src.relative_to(REPO)), "snapshot": f"snapshot/{name}",
                     "sha256": sha(dst)}
    return out


def frozen_report() -> dict:
    d = json.loads(CANON["frozen"].read_text())
    entries = d.get("files") or {}
    want = {
        "schemas/af_scc_c2_vacuum.yaml": PIN["schema"],
        "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml": PIN["schema"],
        "research_map/formulation_taxonomy.yaml": PIN["f0"],
        "artifacts/formulation/formulation_taxonomy.yaml": PIN["supplement"],
        "artifacts/formulation/VARIANT_REGISTRY.json": PIN["registry"],
        "artifacts/formulation/VOCAB_ALIASES.json": PIN["aliases"],
        "artifacts/formulation/evidence/acceptance_pipeline_report.json": ACCEPTANCE_PIN,
    }
    rows = []
    for k, v in want.items():
        got = (entries.get(k) or {}).get("sha256")
        rows.append({"path": k, "pinned": v, "frozen": got, "match": got == v})
    return {"revision": d.get("revision"), "frozen_at": d.get("frozen_at"),
            "revision_is_expected": d.get("revision") == FROZEN_REV,
            "entries": rows, "all_pins_match": all(r["match"] for r in rows)}


def file_controls() -> list[dict]:
    CTRL.mkdir(exist_ok=True)
    base = (SNAP / "af_scc_c2_vacuum.yaml").read_text()
    checks = []
    muts = [
        ("CF0_byte_identical", base, None,
         "positive control: identical bytes must pass every check"),
        ("CF1_duplicate_revised_at",
         base.replace('revised_at: "2026-09-12T00:31:41+08:00"',
                      'revised_at: "2026-09-12T00:31:41+08:00"\nrevised_at: "2026-09-12T00:31:42+08:00"', 1),
         "G28", "closure item a: a duplicate revised_at must be caught"),
        ("CF2_future_stamp",
         base.replace('revised_at: "2026-09-12T00:31:41+08:00"',
                      'revised_at: "2030-01-01T00:00:00+08:00"', 1),
         "G29", "closure item a: a future-dated stamp must be caught"),
        ("CF3_pointer_authoring_only",
         base.replace("class_contract_pointer: research_map/formulation_taxonomy.yaml#classes.AF-SCC-C2-VAC-GEN",
                      "class_contract_pointer: artifacts/formulation/formulation_taxonomy.yaml#class_contracts.AF-SCC-C2-VAC-GEN", 1),
         "G23", "closure item b: an authoring-only pointer must be caught"),
        ("CF4_untagged_D0",
         base.replace('definition: "admissible regularity indices, a tagged disjoint union:',
                      'definition: "admissible regularity pairs (s,delta):', 1),
         "G30", "closure item d: an untagged D0 must be caught"),
        ("CF5_dangling_symbol",
         base.replace('statement_formal: "forall r in D0 exists G_r comeager forall D in G_r: not exists proper_future_extension_in_class(MGHD(D))"',
                      'statement_formal: "forall r in D0 exists G_r comeager forall D in G_r: not exists proper_future_extension_in_class(MGHD(D)) with AF_{I+}(M_D) complete"', 1),
         "G31", "closure item c: a dangling AF_{...} symbol must be caught"),
        ("CF6_unmapped_conclusion_token",
         base.replace("conclusion_type: scc_c2_future_inextendibility",
                      "conclusion_type: scc", 1),
         "G25", "alias registry: a rejected/ambiguous token must not resolve"),
    ]
    for cid, text, expect, note in muts:
        p = CTRL / f"{cid}.yaml"
        p.write_text(text)
        r = run([sys.executable, str(HERE / "check_f2a_rev12_independent.py"),
                 "--schema", str(p), "--f0", str(SNAP / "formulation_taxonomy.yaml"),
                 "--supplement", str(SNAP / "formulation_taxonomy_supplement.yaml"),
                 "--registry", str(SNAP / "VARIANT_REGISTRY.json"),
                 "--aliases", str(SNAP / "VOCAB_ALIASES.json"), "--json"],
                f"control_{cid}.json", expect_zero=(expect is None))
        try:
            res = json.loads((RAW / f"control_{cid}.json").read_text())
        except Exception:
            res = {"checks": [], "hard_failures": [], "verdict": "UNPARSED"}
        failed = [c["id"] for c in res.get("checks", []) if not c["ok"]]
        if expect is None:
            ok = res.get("verdict") == "PASS"
        else:
            ok = expect in failed
        checks.append({"id": cid, "note": note, "expected_failing_check": expect,
                       "failed_checks": failed, "verdict": res.get("verdict"),
                       "ok": ok, "changed_from_base": text != base})
    # sanity: every control but CF0 must actually change bytes
    for c in checks:
        if c["id"] != "CF0_byte_identical" and not c["changed_from_base"]:
            c["ok"] = False
    return checks


def main() -> int:
    started = now()
    inputs = snapshot_inputs()
    pre = {k: sha(v) for k, v in CANON.items()}

    # pre-flight: canonical and mirror must agree and match the pin
    preflight = {
        "schema_canonical_matches_pin": pre["schema"] == PIN["schema"],
        "schema_mirror_matches_pin": pre["mirror"] == PIN["schema"],
        "f0_matches_pin": pre["f0"] == PIN["f0"],
        "supplement_matches_pin": pre["supplement"] == PIN["supplement"],
        "registry_matches_pin": pre["registry"] == PIN["registry"],
        "aliases_matches_pin": pre["aliases"] == PIN["aliases"],
    }
    if not all(preflight.values()):
        print(json.dumps({"error": "moving target: pre-flight pin mismatch", "preflight": preflight,
                          "measured": pre}, indent=1))
        return 2

    fz = frozen_report()

    # declared consistency-evidence hash vs the canonical file and the FROZEN pin
    import yaml as _yaml
    _schema_doc = _yaml.safe_load((SNAP / "af_scc_c2_vacuum.yaml").read_text())
    _f0b = _schema_doc.get("f0_binding") or {}
    _declared_ev = str(_f0b.get("consistency_evidence_sha256") or "")
    _ev_path = REPO / str(_f0b.get("consistency_evidence") or "")
    _ev_measured = sha(_ev_path) if _ev_path.is_file() else None
    _ev_frozen = next((r["frozen"] for r in fz["entries"]
                       if r["path"] == "artifacts/formulation/evidence/taxonomy_consistency.json"), None)
    evidence_binding = {"path": str(_ev_path.relative_to(REPO)),
                        "declared": _declared_ev, "measured": _ev_measured, "frozen": _ev_frozen,
                        "declared_matches_disk": bool(_declared_ev and _declared_ev == _ev_measured),
                        "declared_matches_frozen": bool(_declared_ev and _declared_ev == _ev_frozen)}

    tools = {}
    tools["independent_checker_selftest"] = run(
        [sys.executable, str(HERE / "check_f2a_rev12_independent.py"), "--selftest",
         "--schema", str(SNAP / "af_scc_c2_vacuum.yaml"),
         "--f0", str(SNAP / "formulation_taxonomy.yaml"),
         "--supplement", str(SNAP / "formulation_taxonomy_supplement.yaml"),
         "--registry", str(SNAP / "VARIANT_REGISTRY.json"),
         "--aliases", str(SNAP / "VOCAB_ALIASES.json"), "--json"],
        "checker_selftest.json", expect_zero=True)
    tools["structural_gate_snapshot"] = run(
        [sys.executable, str(REPO / "artifacts/formulation/tools/check_class_schema.py"),
         "--json", str(SNAP / "af_scc_c2_vacuum.yaml")], "structural_gate_snapshot.json")
    tools["structural_gate_canonical"] = run(
        [sys.executable, str(REPO / "artifacts/formulation/tools/check_class_schema.py"),
         "--json", str(CANON["schema"])], "structural_gate_canonical.json")
    tools["acceptance"] = run([sys.executable, str(REPO / "artifacts/formulation/tools/run_acceptance.py")],
                              "acceptance_pipeline.txt")
    tools["verify_frozen"] = run([sys.executable, str(REPO / "artifacts/formulation/tools/verify_frozen.py")],
                                 "verify_frozen.txt")
    tools["classsep_regression"] = run([sys.executable, str(REPO / "runtime/bin/classsep_regression.py")],
                                       "classsep_regression.txt")
    tools["audit_evidence_informational"] = run(
        [sys.executable, str(REPO / "research_map/audit_evidence.py")],
        "audit_evidence_stdout.txt", expect_zero=False)

    controls = file_controls()
    acceptance_pin_ok = sha(CANON["acceptance_evidence"]) == ACCEPTANCE_PIN

    selftest = json.loads((RAW / "checker_selftest.json").read_text())
    sg_snap = json.loads((RAW / "structural_gate_snapshot.json").read_text())
    sg_canon = json.loads((RAW / "structural_gate_canonical.json").read_text())
    acc_txt = (RAW / "acceptance_pipeline.txt").read_text()
    vf_txt = (RAW / "verify_frozen.txt").read_text()
    cs_txt = (RAW / "classsep_regression.txt").read_text()

    post = {k: sha(v) for k, v in CANON.items()}
    drift = {k: {"pre": pre[k], "post": post[k], "drifted": pre[k] != post[k]} for k in pre}

    hard = list(selftest["hard_failures"])
    drift_lines = [ln.strip() for ln in vf_txt.splitlines() if ln.strip().startswith("DRIFT")]
    acceptance_ok = "ACCEPTANCE: PASS" in acc_txt
    if drift_lines:
        hard.append({
            "id": "HF-069R-1",
            "severity": "blocking-for-clean-accept",
            "label": "FROZEN rev27 manifest drift, including this schema's declared consistency evidence",
            "detail": (f"verify_frozen.py reports {len(drift_lines)} drift problem(s) at FROZEN revision 27; "
                       f"the F2a schema's f0_binding declares consistency_evidence_sha256 "
                       f"675a99d0d25b2b37 while the file on disk hashes "
                       f"{sha(CANON['acceptance_evidence'].parent / 'taxonomy_consistency.json')[:16]}. "
                       f"Lines: {drift_lines}"),
            "evidence_refs": ["artifacts/worker-069/f2a_rev12_closure_verdict/raw/verify_frozen.txt",
                              "artifacts/formulation/FROZEN.json#rev27"],
            "falsifier": ("regenerate the declared evidence and re-run verify_frozen.py at the same FROZEN revision; "
                          "if it reports 0 problems the finding is a transient mid-freeze state, not a schema defect"),
        })
    if not evidence_binding["declared_matches_disk"]:
        hard.append({
            "id": "HF-069R-3",
            "severity": "blocking-for-clean-accept",
            "label": "declared consistency-evidence hash does not match the canonical evidence file",
            "detail": (f"f0_binding.consistency_evidence_sha256 declares {_declared_ev[:16]} but "
                       f"{evidence_binding['path']} measures {str(_ev_measured)[:16]} "
                       f"(FROZEN pin {str(_ev_frozen)[:16]}); the on-disk evidence contains no sha256 of either "
                       f"compared tree, so the consistency claim remains unbound by hash."),
            "evidence_refs": ["schemas/af_scc_c2_vacuum.yaml:291#5476a3f2",
                              f"{evidence_binding['path']}#{str(_ev_measured)[:12]}",
                              "artifacts/formulation/FROZEN.json#rev28"],
            "falsifier": ("regenerate artifacts/formulation/evidence/taxonomy_consistency.json with the measured "
                          "sha256 of both compared trees, re-pin it in FROZEN, and re-run; if the declared and "
                          "measured hashes then agree the finding is void"),
        })
    if not acceptance_ok:
        pre_lines = [ln.strip() for ln in acc_txt.splitlines() if "PREFLIGHT FAIL" in ln or "corpus base" in ln or "current base" in ln]
        hard.append({
            "id": "HF-069R-2",
            "severity": "blocking-for-clean-accept",
            "label": "two-stage acceptance pipeline fails preflight at the closure revision (stale rebased fixtures)",
            "detail": (f"run_acceptance.py exits before running: {' | '.join(pre_lines)}. The fixtures were not rebased to the "
                       f"rev12 F2b base 55d0a1ea9bda, so the acceptance criterion cannot be reproduced on the frozen bytes."),
            "evidence_refs": ["artifacts/worker-069/f2a_rev12_closure_verdict/raw/acceptance_pipeline.txt"],
            "falsifier": ("rebase the fixtures (artifacts/formulation/tools/measure_semantic_escape.py) and re-run "
                          "run_acceptance.py on the same frozen bytes; an ACCEPTANCE: PASS voids the finding"),
        })
    advisory = [c for c in selftest["checks"] if c["severity"] == "advisory" and not c["ok"]]
    controls_pass = all(c["ok"] for c in controls)
    tools_ok = all(t["ok"] for k, t in tools.items() if k != "audit_evidence_informational")
    verdict = ("accept" if (not hard and selftest["verdict"] == "PASS" and controls_pass
                            and tools_ok and acceptance_pin_ok and not any(d["drifted"] for d in drift.values())
                            and fz["all_pins_match"] and fz["revision_is_expected"])
               else "revise")

    report = {
        "schema_version": "0.1",
        "artifact_type": "independent_schema_verdict",
        "task_id": "W069-F2A-REV12-CLOSURE-VERDICT-01",
        "generated_at": now(),
        "started_at": started,
        "actor": "worker-069",
        "reviewer": "worker-069",
        "node_id": "F2a",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "gate": "G-FORM",
        "target_artifact": "schemas/af_scc_c2_vacuum.yaml",
        "target_sha256": PIN["schema"],
        "revision": 12,
        "request": ("independent full-schema verdict at the astra-life03-close-findings closure revision, "
                    "replacing the worker-069 verdict that bound the superseded rev11 bytes"),
        "verdict": verdict,
        "score": 4.0 if verdict == "accept" else 3.5,
        "hard_failures": hard,
        "advisories": advisory,
        "closure_checks": {c["id"]: c for c in selftest["checks"] if c["id"] in
                           ("G23", "G25", "G28", "G29", "G30", "G31")},
        "preflight": preflight,
        "frozen": fz,
        "consistency_evidence_binding": evidence_binding,
        "inputs": inputs,
        "canonical_pre": pre,
        "canonical_post": post,
        "drift_during_run": drift,
        "acceptance_evidence_pin": {"expected": ACCEPTANCE_PIN, "measured": sha(CANON["acceptance_evidence"]),
                                    "unchanged": acceptance_pin_ok},
        "checks": selftest["checks"],
        "checks_passed": selftest["checks_passed"],
        "checks_total": selftest["checks_total"],
        "controls_selftest": {"passed": selftest.get("controls_passed"),
                              "total": selftest.get("controls_total"), "rows": selftest.get("controls")},
        "controls_file_level": controls,
        "controls_pass": controls_pass,
        "repo_tools": tools,
        "repo_tool_verdicts": {
            "structural_gate_snapshot": sg_snap.get("verdict"),
            "structural_gate_canonical": sg_canon.get("verdict"),
            "acceptance": "PASS" if acceptance_ok else "not PASS",
            "verify_frozen_tail": vf_txt.strip().splitlines()[-1][:160] if vf_txt.strip() else "",
            "verify_frozen_drifts": drift_lines,
            "classsep_regression": "PASS" if "VERDICT: PASS" in cs_txt else "not PASS",
        },
        "independence": {
            "author_of_target": "astra-lead-formulation",
            "reviewer_is_author": False,
            "checks_written_from": "G-FORM criteria + frozen_classes contract, extended with the astra-life03-close-findings acceptance items (a)-(d)",
            "author_self_tests_used_as_evidence": False,
            "controls": f"{selftest.get('controls_passed')}/{selftest.get('controls_total')} doc-level mutations in selftest + "
                        f"{sum(1 for c in controls if c['ok'])}/{len(controls)} file-level closure controls",
        },
        "falsifier": (
            "Re-run artifacts/worker-069/f2a_rev12_closure_verdict/run_verdict.py on byte-identical copies of "
            f"schemas/af_scc_c2_vacuum.yaml (sha256 {PIN['schema']}) and the pinned F0/supplement/registry/aliases. "
            "This verdict is falsified if (a) any check recorded ok=true returns ok=false on those bytes; "
            "(b) any selftest mutation or file-level control escapes its expected failing check; "
            "(c) the canonical schema, F0, supplement, registry, aliases or FROZEN rev27 pin differs from the "
            "values recorded here (drift voids the binding, not the checks); (d) check_class_schema.py, "
            "run_acceptance.py, verify_frozen.py or classsep_regression.py exits non-zero or reports non-pass; or "
            "(e) a reviewer shows the three G25 conclusion tokens denote different conclusions under "
            "VOCAB_ALIASES, which forces revise."
        ),
        "non_claims": [
            "Not a gate verdict: G-FORM and node status remain the controller's and the leads' to set.",
            "Does not re-adjudicate the physics; no claim about strong cosmic censorship.",
            "Binds only the pinned rev12 bytes; a later canonical revision voids it.",
            "The companion-pair F0 divergence (canonical != authoring bytes) is out of scope here and is reported only as measured input hashes.",
        ],
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True))

    lines = []
    for p in sorted(HERE.rglob("*")):
        if p.is_file() and p.name not in ("SHA256SUMS",):
            lines.append(f"{sha(p)}  {p.relative_to(HERE)}")
    (HERE / "SHA256SUMS").write_text("\n".join(lines) + "\n")

    print(json.dumps({"verdict": verdict, "score": report["score"],
                      "hard_failures": [h["id"] for h in hard],
                      "checks": f"{selftest['checks_passed']}/{selftest['checks_total']}",
                      "selftest_controls": f"{selftest.get('controls_passed')}/{selftest.get('controls_total')}",
                      "file_controls": f"{sum(1 for c in controls if c['ok'])}/{len(controls)}",
                      "acceptance": report["repo_tool_verdicts"]["acceptance"],
                      "verify_frozen": report["repo_tool_verdicts"]["verify_frozen_tail"][:80],
                      "classsep": report["repo_tool_verdicts"]["classsep_regression"],
                      "drift": any(d["drifted"] for d in drift.values())}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
