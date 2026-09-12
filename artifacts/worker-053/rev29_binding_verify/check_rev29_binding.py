#!/usr/bin/env python3
"""W053-REV29-BINDING-VERIFY-01 — independent, read-only verification of the CF-20
evidence-binding repair at the FROZEN rev29 pins (classes F1 / F2a / F2b; gate G-FORM).

What this decides (mechanical, declared before the measurement pass):
  C1  FROZEN manifest self-resolves: canonical verify_frozen.py exits 0 (every files[*] pin == disk).
  C2  FROZEN revision >= 29.
  C3  the four repaired paths are pinned in FROZEN at their live bytes:
      schemas/{af_wcc_vacuum,af_scc_c2_vacuum,af_scc_c0_vacuum}.yaml + schemas/taxonomy_cases.jsonl.
  C4  for each of the three class schemas: f0_binding.consistency_evidence_sha256 equals the
      live sha256 of the path named by f0_binding.consistency_evidence (the CF-20 defect).
  C5  for each schema: f0_binding.declared_f0_sha256 == live research_map/formulation_taxonomy.yaml
      == the FROZEN pin (G-F0 canonical bytes untouched).
  C6  schemas/taxonomy_cases.jsonl: meta.taxonomy_ref.sha256 == live F0; every case row's
      binding_status == bound_taxonomy_sha_<live sha12>; zero stale 66bf917bd368 tokens;
      canonical artifacts/flash-02/check_taxonomy_cases.py exits 0 with all its controls detected.
  C7  canonical checkers exit 0: verify_frozen.py, check_class_schema.py (x3), the cases checker.
  C8  schemas/<f>.yaml and artifacts/formulation/schemas/<f>.yaml are byte-identical (mirrors).
  C9  class_contract_supplement_pointer resolves inside the supplement artifact and the
      supplement's FROZEN pin is live.
  C10 recomputed consistency evidence: a staged re-run of check_taxonomy_consistency.py
      (copy, so canonical evidence is never written) reproduces the canonical evidence bytes,
      and reports CONSISTENT.
  C11 drift: every measured input re-measured at the end equals its T0 value.
  C12 registered variant deltas resolve against the live schema bases; the delta/registry
      evidence files are valid and a staged re-run of both variant checkers reproduces them.

VERDICT: PASS iff C1..C11 all hold at the measured pins. The claim is falsified by any failing
check, by a staged-consistency byte mismatch, or by drift between T0 and T1.

This tool never writes a canonical path. It writes only under its own artifact directory
(report, controls, stage mirrors). Worker output: no gate verdict, no node status.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))
HERE = Path(__file__).resolve().parent


def find_root() -> Path:
    for anc in HERE.parents:
        if (anc / "research_map" / "research_map.json").exists() and (anc / "schemas").is_dir():
            return anc
    raise SystemExit("cannot locate swarm root")


ROOT = find_root()

F0_PATH = "research_map/formulation_taxonomy.yaml"
SUPPLEMENT_PATH = "artifacts/formulation/formulation_taxonomy.yaml"
EVIDENCE_PATH = "artifacts/formulation/evidence/taxonomy_consistency.json"
CASES_PATH = "schemas/taxonomy_cases.jsonl"
FROZEN_PATH = "artifacts/formulation/FROZEN.json"
SCHEMAS = ["af_wcc_vacuum.yaml", "af_scc_c2_vacuum.yaml", "af_scc_c0_vacuum.yaml"]
CLASS_OF = {
    "af_wcc_vacuum.yaml": "AF-WCC-VAC-GEN",
    "af_scc_c2_vacuum.yaml": "AF-SCC-C2-VAC-GEN",
    "af_scc_c0_vacuum.yaml": "AF-SCC-C0-VAC-GEN",
}
REPAIRED_PATHS = [f"schemas/{s}" for s in SCHEMAS] + [CASES_PATH]
STALE_TOKEN = "66bf917bd368"
CASES_CHECKER = "artifacts/flash-02/check_taxonomy_cases.py"
CASES_CATALOG = "artifacts/flash-02/leak_rule_catalog.json"
CLASS_CHECKER = "artifacts/formulation/tools/check_class_schema.py"
CONSISTENCY_CHECKER = "artifacts/formulation/tools/check_taxonomy_consistency.py"
VERIFY_FROZEN = "artifacts/formulation/tools/verify_frozen.py"
REGISTRY = "artifacts/formulation/VARIANT_REGISTRY.json"
REGISTRY_CHECKER = "artifacts/formulation/tools/check_variant_registry.py"
DELTA_CHECKER = "artifacts/formulation/tools/check_variant_deltas.py"
DELTA_FILES = [
    "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json",
    "artifacts/formulation/variants/AF-SCC-C0-VAC-GEN.variant-CH.delta.json",
]
DELTA_EVIDENCE = "artifacts/formulation/evidence/variant_delta_check.json"
REGISTRY_EVIDENCE = "artifacts/formulation/evidence/variant_registry_check.json"

# Files whose bytes are measured at T0 and re-measured at T1 (drift guard).
PINNED_INPUTS = [
    FROZEN_PATH, F0_PATH, SUPPLEMENT_PATH, EVIDENCE_PATH, CASES_PATH,
    CLASS_CHECKER, CONSISTENCY_CHECKER, VERIFY_FROZEN, CASES_CHECKER, CASES_CATALOG,
    REGISTRY, REGISTRY_CHECKER, DELTA_CHECKER, DELTA_EVIDENCE, REGISTRY_EVIDENCE,
] + DELTA_FILES + REPAIRED_PATHS + [f"artifacts/formulation/schemas/{s}" for s in SCHEMAS]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def run(cmd, cwd=None):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=300)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def load_yaml(p: Path):
    import yaml
    return yaml.safe_load(p.read_text())


class Result:
    def __init__(self):
        self.checks = []

    def add(self, cid, name, ok, expected, observed, falsifier, severity="blocking"):
        self.checks.append({
            "id": cid, "check": name, "ok": bool(ok), "severity": severity,
            "expected": expected, "observed": observed, "falsifier": falsifier,
        })
        return bool(ok)


def measure_pins() -> dict:
    return {p: sha256_file(ROOT / p) for p in PINNED_INPUTS}


def resolve_pointer(doc, pointer: str):
    """Resolve 'path#a.b.c' inside a loaded YAML document."""
    node = doc
    for seg in pointer.split("."):
        if isinstance(node, dict) and seg in node:
            node = node[seg]
        else:
            return None
    return node


def check_all(root: Path, r: Result, staged_consistency_out: Path | None):
    """Run C1..C10 against `root` (canonical for the real pass, a mutated stage for controls)."""
    frozen = json.loads((root / FROZEN_PATH).read_text())
    rev = frozen.get("revision")

    # C1 FROZEN self-resolves
    rc, out, err = run([sys.executable, str(root / VERIFY_FROZEN)])
    r.add("C1", "FROZEN manifest resolves on disk (verify_frozen.py exit 0)",
          rc == 0, "exit 0", f"exit {rc}: {out or err}"[:300],
          "any files[*] pin that does not equal the live bytes of the path it names")

    # C2 revision
    r.add("C2", "FROZEN revision >= 29", isinstance(rev, int) and rev >= 29,
          ">=29", rev, "a FROZEN manifest at revision < 29")

    # C3 repaired paths pinned and live
    bad = []
    for p in REPAIRED_PATHS:
        rec = frozen.get("files", {}).get(p)
        live = sha256_file(root / p)
        if not rec or rec.get("sha256") != live:
            bad.append({"path": p, "pinned": (rec or {}).get("sha256", "MISSING")[:12], "live": live[:12]})
    r.add("C3", "four repaired paths pinned at live bytes", not bad, "0 mismatches", bad,
          "a repaired path whose FROZEN pin differs from its live bytes")

    # C4 consistency-evidence binding
    bad = []
    for s in SCHEMAS:
        doc = load_yaml(root / "schemas" / s)
        b = (doc or {}).get("f0_binding", {})
        declared = b.get("consistency_evidence_sha256")
        epath = b.get("consistency_evidence")
        live = sha256_file(root / epath) if epath and (root / epath).exists() else None
        if declared != live:
            bad.append({"schema": s, "declared": str(declared)[:12], "live": str(live)[:12], "path": epath})
    r.add("C4", "schemas declare the live consistency-evidence hash (CF-20)", not bad,
          "3/3 declared == live", bad,
          "any schema whose consistency_evidence_sha256 differs from the file it names")

    # C5 F0 binding
    f0_live = sha256_file(root / F0_PATH)
    f0_pin = frozen.get("files", {}).get(F0_PATH, {}).get("sha256")
    bad = []
    for s in SCHEMAS:
        doc = load_yaml(root / "schemas" / s)
        declared = ((doc or {}).get("f0_binding", {}) or {}).get("declared_f0_sha256")
        if declared != f0_live or f0_live != f0_pin:
            bad.append({"schema": s, "declared": str(declared)[:12], "live_f0": f0_live[:12], "frozen": str(f0_pin)[:12]})
    r.add("C5", "schemas declare live F0 and FROZEN pins it", not bad,
          f"3/3 == {f0_live[:12]} == FROZEN pin", bad,
          "any schema whose declared_f0_sha256 != live F0, or a FROZEN F0 pin that drifted (voids G-F0)")

    # C6 taxonomy_cases corpus binding
    raw = (root / CASES_PATH).read_text()
    rows = [json.loads(l) for l in raw.splitlines() if l.strip()]
    meta = rows[0]
    cases = [x for x in rows if x.get("record_type") == "case"]
    want = "bound_taxonomy_sha_" + f0_live[:12]
    bad_rows = [c.get("case_id") for c in cases if c.get("binding_status") != want]
    meta_ok = (meta.get("taxonomy_ref") or {}).get("sha256") == f0_live
    stale = raw.count(STALE_TOKEN)
    rc, out, err = run([
        sys.executable, str(root / CASES_CHECKER),
        "--taxonomy", str(root / F0_PATH), "--cases", str(root / CASES_PATH),
        "--catalog", str(root / CASES_CATALOG),
        "--report", str(staged_consistency_out or (HERE / "cases_check_report.json")),
    ])
    cases_report = None
    rp = staged_consistency_out or (HERE / "cases_check_report.json")
    if rp.exists():
        try:
            cases_report = json.loads(rp.read_text())
        except Exception:  # noqa: BLE001
            cases_report = None
    ctrl_ok = bool(cases_report and cases_report.get("controls_all_detected"))
    ok = (not bad_rows) and meta_ok and stale == 0 and rc == 0 and ctrl_ok
    r.add("C6", "taxonomy_cases rows/meta bound to live F0; stale token absent; checker PASS + controls",
          ok,
          f"36/36 rows == {want}, meta==live, stale=0, checker exit 0, controls detected",
          {"bad_rows": bad_rows, "meta_ok": meta_ok, "stale_token_count": stale,
           "checker_exit": rc, "controls_detected": ctrl_ok,
           "checker_out": out[:200], "err": err[:200]},
          "any row bound to a superseded taxonomy hash, a stale 66bf917b token, or an escaping control")

    # C7 canonical structural checkers
    c7 = {}
    for s in SCHEMAS:
        rc, out, err = run([sys.executable, str(root / CLASS_CHECKER), str(root / "schemas" / s)])
        c7[s] = {"exit": rc, "out": out[:160]}
    ok = all(v["exit"] == 0 for v in c7.values())
    r.add("C7", "canonical check_class_schema.py exit 0 on all three schemas", ok,
          "3/3 exit 0", c7, "a schema the canonical structural gate rejects")

    # C8 mirrors
    bad = []
    for s in SCHEMAS:
        a = sha256_file(root / "schemas" / s)
        b = sha256_file(root / "artifacts" / "formulation" / "schemas" / s)
        if a != b:
            bad.append({"schema": s, "schemas": a[:12], "mirror": b[:12]})
    r.add("C8", "schema mirrors byte-identical", not bad, "3/3 identical", bad,
          "a schema whose two canonical copies diverge")

    # C9 supplement pointer
    bad = []
    sup = load_yaml(root / SUPPLEMENT_PATH)
    for s in SCHEMAS:
        doc = load_yaml(root / "schemas" / s)
        ptr = ((doc or {}).get("f0_binding", {}) or {}).get("class_contract_supplement_pointer")
        spath, _, frag = str(ptr).partition("#")
        sub = spath.split("/", 1)[1] if "/" in spath else spath
        node = resolve_pointer(load_yaml(root / spath), frag)
        if node is None:
            bad.append({"schema": s, "pointer": ptr})
    sup_live = sha256_file(root / SUPPLEMENT_PATH)
    sup_pin = frozen.get("files", {}).get(SUPPLEMENT_PATH, {}).get("sha256")
    ok = (not bad) and sup_live == sup_pin and isinstance(sup, dict)
    r.add("C9", "class_contract_supplement pointers resolve; supplement pin live", ok,
          "3/3 pointers resolve, supplement pin == live", {"bad": bad, "live": sup_live[:12], "pin": str(sup_pin)[:12]},
          "a pointer that does not resolve in the supplement, or a supplement whose FROZEN pin drifted")

    # C10 recomputed consistency evidence (staged; canonical never written)
    stage_ok, stage_detail = False, {}
    if staged_consistency_out is not None:
        stage_root = staged_consistency_out.parent / "consistency_stage"
        build_stage(root, stage_root)
        tool = stage_root / "artifacts/formulation/tools/check_taxonomy_consistency.py"
        rc, out, err = run([sys.executable, str(tool)], cwd=str(stage_root))
        produced = stage_root / EVIDENCE_PATH
        live_evidence = (root / EVIDENCE_PATH)
        byte_match = produced.exists() and live_evidence.exists() and produced.read_bytes() == live_evidence.read_bytes()
        stage_ok = rc == 0 and byte_match
        stage_detail = {"exit": rc, "out": out[:160], "reproduced_bytes_match_canonical": byte_match,
                        "staged_sha": sha256_file(produced)[:12] if produced.exists() else None}
    r.add("C10", "staged consistency re-run reproduces canonical evidence bytes and is CONSISTENT",
          stage_ok, "exit 0 + byte-identical to canonical evidence", stage_detail,
          "a consistency run that reports divergence or reproduces different evidence bytes")

    # C12 registered variants resolve against the repaired bases, and their evidence is live
    c12 = {}
    bad = []
    for rel in DELTA_FILES:
        d = json.loads((root / rel).read_text())
        base = d.get("base", {})
        live_base = sha256_file(root / base.get("artifact", "missing")) if (root / str(base.get("artifact"))).exists() else None
        if base.get("sha256") != live_base:
            bad.append({"delta": Path(rel).name, "declared": str(base.get("sha256"))[:12], "live": str(live_base)[:12],
                        "base_artifact": base.get("artifact")})
    reg_live = json.loads((root / REGISTRY_EVIDENCE).read_text())
    del_live = json.loads((root / DELTA_EVIDENCE).read_text())
    if not del_live.get("valid") or del_live.get("errors"):
        bad.append({"delta_evidence": DELTA_EVIDENCE, "valid": del_live.get("valid"), "errors": del_live.get("errors")})
    if not reg_live.get("valid") or reg_live.get("errors"):
        bad.append({"registry_evidence": REGISTRY_EVIDENCE, "valid": reg_live.get("valid"), "errors": reg_live.get("errors")})
    # staged recompute must reproduce the live evidence bytes
    if staged_consistency_out is not None:
        vstage = staged_consistency_out.parent / "variant_stage"
        build_stage(root, vstage)
        for tool, ev in ((DELTA_CHECKER, DELTA_EVIDENCE), (REGISTRY_CHECKER, REGISTRY_EVIDENCE)):
            rc, out, err = run([sys.executable, str(vstage / tool)], cwd=str(vstage))
            produced = vstage / ev
            live = root / ev
            match = produced.exists() and live.exists() and produced.read_bytes() == live.read_bytes()
            c12[Path(tool).name] = {"exit": rc, "byte_match": match, "out": out[:120]}
            if rc != 0 or not match:
                bad.append({"tool": tool, "exit": rc, "byte_match": match, "err": err[:120]})
    c12["delta_base_pins"] = "live" if not any("delta" in b for b in bad) else "stale"
    r.add("C12", "registered variant deltas resolve against live schema bases; variant evidence live + reproduced",
          not bad,
          "2/2 delta base pins == live schema bytes, delta/registry evidence valid:true, staged recompute byte-identical",
          {"bad": bad, "staged": c12},
          "a registered variant delta whose base.sha256 no longer equals the frozen schema bytes (the live "
          "check_variant_deltas.py then reports valid:false while FROZEN may pin the older valid:true bytes)")


def build_stage(src_root: Path, stage: Path):
    if stage.exists():
        shutil.rmtree(stage)
    for rel in [F0_PATH, SUPPLEMENT_PATH, EVIDENCE_PATH, CASES_PATH, FROZEN_PATH,
                "artifacts/formulation/VOCAB_ALIASES.json", CASES_CATALOG,
                "artifacts/formulation/rule_spec.json", "artifacts/formulation/KEY_MANIFEST.json",
                CASES_CHECKER, CONSISTENCY_CHECKER, VERIFY_FROZEN, CLASS_CHECKER,
                REGISTRY, REGISTRY_CHECKER, DELTA_CHECKER, DELTA_EVIDENCE, REGISTRY_EVIDENCE] + DELTA_FILES:
        dst = stage / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_root / rel, dst)
    for s in REPAIRED_PATHS:
        dst = stage / s
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_root / s, dst)
    for s in SCHEMAS:
        rel = f"artifacts/formulation/schemas/{s}"
        dst = stage / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_root / rel, dst)


def mutate(stage: Path, kind: str):
    if kind == "consistency_pin":
        p = stage / "schemas/af_wcc_vacuum.yaml"
        t = p.read_text().replace("9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b", "0" * 64, 1)
        p.write_text(t)
    elif kind == "stale_case_token":
        p = stage / CASES_PATH
        t = p.read_text().replace("bound_taxonomy_sha_0abb9ed8a961", "bound_taxonomy_sha_66bf917bd368", 1)
        p.write_text(t)
    elif kind == "f0_pin_zero":
        p = stage / "schemas/af_scc_c2_vacuum.yaml"
        t = p.read_text().replace("0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3", "f" * 64, 1)
        p.write_text(t)
    elif kind == "frozen_entry_removed":
        p = stage / FROZEN_PATH
        d = json.loads(p.read_text())
        d["files"].pop("schemas/af_wcc_vacuum.yaml", None)
        p.write_text(json.dumps(d, indent=2) + "\n")
    elif kind == "frozen_pin_mutated":
        p = stage / FROZEN_PATH
        d = json.loads(p.read_text())
        d["files"][F0_PATH]["sha256"] = "f" * 64
        p.write_text(json.dumps(d, indent=2) + "\n")
    elif kind == "revision_downgrade":
        p = stage / FROZEN_PATH
        d = json.loads(p.read_text())
        d["revision"] = 28
        p.write_text(json.dumps(d, indent=2) + "\n")
    elif kind == "mirror_mismatch":
        p = stage / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
        p.write_text(p.read_text() + "# control mutation\n")
    elif kind == "taxonomy_divergence":
        import yaml
        p = stage / F0_PATH
        d = yaml.safe_load(p.read_text())
        d["classes"]["AF-WCC-VAC-GEN"]["axes"]["family"] = "SCC"
        p.write_text(yaml.safe_dump(d, sort_keys=False))
    elif kind == "delta_base_stale":
        p = stage / DELTA_FILES[0]
        p.write_text(p.read_text().replace("d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
                                           "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3", 1))
    else:
        raise SystemExit(f"unknown mutation {kind}")


CONTROLS = [
    ("K1", "consistency_pin", "C4"),
    ("K2", "stale_case_token", "C6"),
    ("K3", "f0_pin_zero", "C5"),
    ("K4", "frozen_entry_removed", "C1"),
    ("K5", "frozen_pin_mutated", "C1"),
    ("K6", "revision_downgrade", "C2"),
    ("K7", "mirror_mismatch", "C8"),
    ("K8", "taxonomy_divergence", "C10"),
    ("K9", "delta_base_stale", "C12"),
]


def run_controls() -> list:
    out = []
    for cid, kind, target in CONTROLS:
        stage = HERE / "stage" / f"control_{cid}"
        build_stage(ROOT, stage)
        mutate(stage, kind)
        r = Result()
        scratch = HERE / "stage" / f"control_{cid}_out"
        scratch.mkdir(parents=True, exist_ok=True)
        try:
            check_all(stage, r, scratch / "report.json")
        except Exception as e:  # noqa: BLE001
            out.append({"id": cid, "mutation": kind, "target_check": target,
                        "detected": False, "error": f"{type(e).__name__}: {e}"})
            continue
        hit = [c for c in r.checks if c["id"] == target]
        detected = bool(hit) and not hit[0]["ok"]
        out.append({"id": cid, "mutation": kind, "target_check": target, "detected": detected,
                    "observed": hit[0]["observed"] if hit else None})
    return out


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", default=str(HERE / "report.json"))
    ap.add_argument("--controls", action="store_true")
    ap.add_argument("--skip-controls", action="store_true")
    ap.add_argument("--prior-report", default=None,
                    help="earlier pass report to embed as prior_pass evidence")
    a = ap.parse_args()

    t0 = now()
    pins0 = measure_pins()
    r = Result()
    check_all(ROOT, r, HERE / "cases_check_report.json")
    t1 = now()
    pins1 = measure_pins()
    drift = {p: {"t0": pins0[p][:12], "t1": pins1[p][:12]} for p in pins0 if pins0[p] != pins1.get(p)}
    r.add("C11", "no drift between T0 and T1 on any measured input", not drift,
          "0 drifted inputs", drift,
          "any input whose bytes moved during the verification window (voids the pinned verdict)")

    controls = [] if a.skip_controls else run_controls()
    controls_ok = (not controls) or all(c["detected"] for c in controls)

    failed = [c["id"] for c in r.checks if not c["ok"]]
    verdict = "PASS" if not failed and controls_ok else "FAIL"

    prior = None
    if a.prior_report and Path(a.prior_report).exists():
        pr = json.loads(Path(a.prior_report).read_text())
        prior = {
            "path": a.prior_report,
            "sha256": sha256_file(Path(a.prior_report)),
            "verdict": pr.get("verdict"),
            "failed_checks": pr.get("failed_checks"),
            "frozen_revision": pr.get("frozen_revision"),
            "frozen_pin": pr.get("pins_t0", {}).get(FROZEN_PATH),
            "key_observation": next((c["observed"] for c in pr.get("checks", []) if c["id"] == "C1"), None),
        }

    report = {
        "task_id": "W053-REV29-BINDING-VERIFY-01",
        "worker": "worker-053",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "nodes": ["F1", "F2a", "F2b"],
        "gate": "G-FORM",
        "created_at": t0,
        "finished_at": now(),
        "verdict": verdict,
        "failed_checks": failed,
        "frozen_revision": json.loads((ROOT / FROZEN_PATH).read_text()).get("revision"),
        "passes": {
            "pass1": prior,
            "pass2": {"started_at": t0, "finished_at": now(), "verdict": verdict,
                      "frozen_pin": pins0[FROZEN_PATH], "failed_checks": failed},
        },
        "pins_t0": pins0,
        "pins_t1": pins1,
        "drift": drift,
        "checks": r.checks,
        "controls": controls,
        "controls_all_detected": controls_ok,
        "falsifier": (
            "Re-measure at the same FROZEN rev29 pins: any of C1-C11 failing, a staged "
            "check_taxonomy_consistency.py run that does not reproduce the canonical evidence bytes, "
            "a case row bound to a superseded taxonomy hash, or any measured input drifting between "
            "T0 and T1 falsifies the PASS. A repaired binding that resolves only at a reconstruction "
            "outside the declared path does not satisfy C4/C10."
        ),
        "does_not_claim": [
            "no gate verdict and no node transition (worker events cannot set done/passed)",
            "no adjudication of class semantics, mathematics or physics",
            "C10 reproduces the canonical consistency evidence bytes; it does not re-adjudicate the D2/D3 divergence texts",
            "the two mirror copies are compared to each other, not re-derived",
        ],
        "authority_note": "worker-level measurement; G-FORM remains pending until the audit lead's r3 review.",
    }
    Path(a.report).write_text(json.dumps(report, indent=2) + "\n")
    print(f"W053-REV29-BINDING-VERIFY-01 verdict: {verdict}")
    for c in r.checks:
        print(f"  {'PASS' if c['ok'] else 'FAIL'} {c['id']} {c['check']}")
    if controls:
        print(f"  controls: {sum(1 for c in controls if c['detected'])}/{len(controls)} detected")
    print(f"  report: {a.report}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
