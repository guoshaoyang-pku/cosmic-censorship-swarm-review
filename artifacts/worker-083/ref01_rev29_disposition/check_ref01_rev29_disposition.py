#!/usr/bin/env python3
"""W083-REF01-REV29-DISPOSITION-01: disposition of the W083-REF-01 defect at FROZEN rev29.

Defect under measurement (first reported by worker-083, task W083-REV12-CLOSURE-EVIDENCE-FIXPOINT-01,
event w083-20260912T004419-claim-001): the pinned rev27 closure record
artifacts/formulation/evidence/close_findings_rev27_report.json declares post-write sha256 values
for 8 artifacts, and 7 of the 8 matched neither the frozen schema pins nor disk bytes at emit time;
the pinned procedure artifacts/formulation/tools/close_findings_rev27.py exits non-zero under
--dry-run at the frozen bytes.

This instrument re-measures that defect at the CURRENT frozen generation (FROZEN rev29
815e08079aef) and emits a per-entry disposition. It is read-only, stdlib-only and deterministic.

Exit codes:
  0  all hard checks pass and all controls behave as pre-registered
  1  at least one hard check or control failed
  2  pin drift: a bound input moved between the start and end of the run (measurement void)
  3  a required input is missing/unparseable

Usage:
  python3 check_ref01_rev29_disposition.py            # measure, write report.json + evidence.json
  python3 check_ref01_rev29_disposition.py --no-scan  # skip the content-hash recoverability scan
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "artifacts/worker-083/ref01_rev29_disposition"

# ---------------------------------------------------------------- pre-registered pins
FROZEN_PIN = "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"
FROZEN_REV = 29
REPORT_PIN = "dab1d49b9985416504239154fa8af0ec94147ee4ebae0cd7732001ccead69972"
TOOL_PIN = "0234cd3cbda491ae353e4972dda8a8fe95ae39d2fe2b4968639dc2fcad845371"
SCHEMA_PINS = {
    "schemas/af_wcc_vacuum.yaml": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
}
CONSISTENCY_PIN = "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b"
GATE_TEST_REPORT_PIN = "26540a6b43cc"
INTERMEDIATE_PREFIXES = ["b474fbc4", "a7ccae4d", "b71ec02c", "f3c119a8"]

FROZEN_PATH = "artifacts/formulation/FROZEN.json"
REPORT_PATH = "artifacts/formulation/evidence/close_findings_rev27_report.json"
TOOL_PATH = "artifacts/formulation/tools/close_findings_rev27.py"
CONSISTENCY_PATH = "artifacts/formulation/evidence/taxonomy_consistency.json"
GATE_TEST_REPORT_PATH = "artifacts/formulation/evidence/gate_test_report.json"

SCAN_SKIP_DIRS = {".git", "tmp", "node_modules", "__pycache__", ".cache", ".dsh"}
SCAN_MAX_BYTES = 4 * 1024 * 1024

# guarded paths for the tool write-probe: all 8 declared entries + report + tool + FROZEN + consistency
GUARDED = [
    "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/evidence/taxonomy_consistency.json",
    "schemas/af_wcc_vacuum.yaml",
    "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
    REPORT_PATH,
    TOOL_PATH,
    FROZEN_PATH,
    GATE_TEST_REPORT_PATH,
]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def strict_json(path):
    """Parse JSON and reject duplicate object keys."""
    dup = []

    def hook(pairs):
        seen = set()
        for k, _ in pairs:
            if k in seen:
                dup.append(k)
            seen.add(k)
        return dict(pairs)

    with open(path, "r", encoding="utf-8") as fh:
        obj = json.load(fh, object_pairs_hook=hook)
    return obj, dup


def measure(path):
    p = ROOT / path
    if not p.exists():
        return {"path": path, "exists": False}
    st = p.stat()
    return {
        "path": path,
        "exists": True,
        "sha256": sha256_file(p),
        "bytes": st.st_size,
        "mtime": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(st.st_mtime)),
    }


def classify(declared, frozen_pin, live, copy_paths):
    if live is None:
        return "MISSING_PATH"
    if declared == live and declared == frozen_pin:
        return "CURRENT"
    if declared == frozen_pin and declared != live:
        return "PIN_ONLY"
    if declared != live and declared != frozen_pin:
        return "HISTORICAL_COPY" if copy_paths else "STALE_DECLARED"
    return "OTHER"


def build_entries(report, frozen, copies_by_hash):
    entries = []
    for path, meta in sorted(report["files"].items()):
        declared = meta.get("sha256")
        live = sha256_file(ROOT / path) if (ROOT / path).exists() else None
        pin_meta = frozen["files"].get(path)
        pin = pin_meta["sha256"] if isinstance(pin_meta, dict) else pin_meta
        copies = list(copies_by_hash.get(declared, []))
        entries.append({
            "path": path,
            "declared": declared,
            "frozen_rev29_pin": pin,
            "live": live,
            "declared_matches_live": declared == live,
            "declared_matches_pin": declared == pin,
            "copies_of_declared_bytes": copies,
            "classification": classify(declared, pin, live, copies),
        })
    return entries


def recoverability_scan(prefixes):
    """Content-hash every reasonable file in the repo; return copies of the four intermediates."""
    hits = {p: [] for p in prefixes}
    files = 0
    total = 0
    skipped_big = 0
    for dp, dn, fn in os.walk(ROOT):
        dn[:] = [d for d in dn if d not in SCAN_SKIP_DIRS]
        for name in fn:
            p = Path(dp) / name
            try:
                if p.is_symlink() or not p.is_file():
                    continue
                size = p.stat().st_size
            except OSError:
                continue
            if size > SCAN_MAX_BYTES:
                skipped_big += 1
                continue
            try:
                h = sha256_file(p)
            except OSError:
                continue
            files += 1
            total += size
            for pref in prefixes:
                if h.startswith(pref):
                    hits[pref].append(str(p.relative_to(ROOT)))
    return {"scan_files": files, "scan_bytes": total, "skipped_over_4MB": skipped_big,
            "hits": {k: v for k, v in hits.items()}}


def grep_prefixes(prefixes, scope):
    out = {p: [] for p in prefixes}
    for base in scope:
        b = ROOT / base
        if not b.exists():
            continue
        for dp, dn, fn in os.walk(b):
            dn[:] = [d for d in dn if d not in SCAN_SKIP_DIRS]
            for name in fn:
                p = Path(dp) / name
                if p.is_symlink() or not p.is_file():
                    continue
                try:
                    if p.stat().st_size > SCAN_MAX_BYTES:
                        continue
                    blob = p.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                for pref in prefixes:
                    if pref in blob:
                        out[pref].append(str(p.relative_to(ROOT)))
    return out


def tool_probe():
    before = {p: sha256_file(ROOT / p) for p in GUARDED if (ROOT / p).exists()}
    r = subprocess.run(
        [sys.executable, TOOL_PATH, "--dry-run"],
        cwd=str(ROOT), capture_output=True, text=True, timeout=120,
    )
    after = {p: sha256_file(ROOT / p) for p in GUARDED if (ROOT / p).exists()}
    changed = [p for p in before if before.get(p) != after.get(p)]
    return {
        "cmd": f"python3 {TOOL_PATH} --dry-run",
        "exit_code": r.returncode,
        "stderr_head": (r.stderr or "").strip().splitlines()[:3],
        "stdout_head": (r.stdout or "").strip().splitlines()[:3],
        "changed_files": changed,
        "guard_note": "all 12 guarded paths hashed before/after the probe",
    }


def core_measurement(do_scan):
    """All static measurements. Deterministic given unchanged inputs."""
    frozen, frozen_dup = strict_json(ROOT / FROZEN_PATH)
    report, report_dup = strict_json(ROOT / REPORT_PATH)

    pins = {
        "frozen": measure(FROZEN_PATH),
        "report": measure(REPORT_PATH),
        "tool": measure(TOOL_PATH),
        "consistency": measure(CONSISTENCY_PATH),
        "gate_test_report": measure(GATE_TEST_REPORT_PATH),
    }
    for p in SCHEMA_PINS:
        pins[p] = measure(p)

    copies_by_hash = {p: [] for p in INTERMEDIATE_PREFIXES}
    if do_scan:
        scan = recoverability_scan(INTERMEDIATE_PREFIXES)
        for pref, paths in scan["hits"].items():
            copies_by_hash[pref] = paths
    else:
        scan = {"scan_files": 0, "scan_bytes": 0, "skipped_over_4MB": 0,
                "hits": {k: [] for k in INTERMEDIATE_PREFIXES}, "skipped": True}

    entries = build_entries(report, frozen, copies_by_hash)

    checks = []

    def check(cid, expected, observed, ok, note=""):
        checks.append({"id": cid, "expected": expected, "observed": observed,
                       "pass": bool(ok), "note": note})

    check("E1_frozen_rev29_live",
          f"{FROZEN_PATH} sha256=={FROZEN_PIN[:14]} and revision=={FROZEN_REV}",
          f"sha256={(pins['frozen'].get('sha256') or 'MISSING')[:14]} revision={frozen.get('revision')}",
          pins["frozen"].get("sha256") == FROZEN_PIN and frozen.get("revision") == FROZEN_REV)
    check("E2_report_pinned",
          f"{REPORT_PATH} sha256=={REPORT_PIN[:14]} and strict-parse (no duplicate keys)",
          f"sha256={(pins['report'].get('sha256') or 'MISSING')[:14]} dup_keys={report_dup}",
          pins["report"].get("sha256") == REPORT_PIN and not report_dup)
    check("E2b_report_in_frozen",
          "FROZEN.files[report].sha256 == report live sha256",
          str(frozen["files"].get(REPORT_PATH, {}).get("sha256", "ABSENT"))[:14],
          (isinstance(frozen["files"].get(REPORT_PATH), dict)
           and frozen["files"][REPORT_PATH]["sha256"] == pins["report"].get("sha256")))

    n_cur = sum(1 for e in entries if e["classification"] == "CURRENT")
    n_stale = sum(1 for e in entries if e["classification"] == "STALE_DECLARED")
    other = [e["classification"] for e in entries if e["classification"] not in ("CURRENT", "STALE_DECLARED")]
    check("E3_disposition_shape",
          "exactly 1 CURRENT + 7 STALE_DECLARED, other classes empty",
          f"CURRENT={n_cur} STALE_DECLARED={n_stale} other={other}",
          n_cur == 1 and n_stale == 7 and not other)

    moved = [e["path"] for e in entries if e["frozen_rev29_pin"] != e["live"]]
    check("E4_rev29_pins_current_bytes",
          "for all 8 declared paths, live bytes == FROZEN rev29 pin (no freeze breach)",
          f"moved={moved}", not moved)

    probe = tool_probe()
    stderr_txt = " ".join(probe["stderr_head"])
    check("E5_tool_fails_closed",
          "pinned tool --dry-run exits non-zero with ASSERT FAIL and writes nothing",
          f"exit={probe['exit_code']} changed={probe['changed_files']} stderr={stderr_txt[:120]!r}",
          probe["exit_code"] != 0 and "ASSERT FAIL" in stderr_txt and not probe["changed_files"])

    check("E7_intermediates_unrecoverable",
          f"0 content-hash copies of {INTERMEDIATE_PREFIXES} in scan set",
          f"scan_files={scan['scan_files']} hits=" +
          json.dumps({k: len(v) for k, v in scan["hits"].items()}),
          all(not v for v in scan["hits"].values()))

    gate_test, gate_test_dup = strict_json(ROOT / GATE_TEST_REPORT_PATH)
    declared_live = set((gate_test.get("canonical_sha256") or {}).values())
    missing_live = [s for s in SCHEMA_PINS.values() if s not in declared_live]
    check("E6_gate_test_report_carries_live_binding",
          f"{GATE_TEST_REPORT_PATH} bytes==FROZEN pin {GATE_TEST_REPORT_PIN} and declares all three "
          "rev13 schema hashes",
          f"sha256={(pins['gate_test_report'].get('sha256') or 'MISSING')[:14]} "
          f"missing={len(missing_live)}",
          (pins["gate_test_report"].get("sha256", "").startswith(GATE_TEST_REPORT_PIN)
           and not missing_live))

    # consumers / registry observations (NOT part of the hard pass, moving targets)
    registry_hits = []
    reg = ROOT / "runtime/state/artifact_hashes.json"
    if reg.exists():
        blob = reg.read_text(encoding="utf-8", errors="ignore")
        registry_hits = [p for p in INTERMEDIATE_PREFIXES if p in blob]
    grep_scope = ["schemas", "research_map", "artifacts/formulation", "reviews", "runtime/state"]
    grepped = grep_prefixes(INTERMEDIATE_PREFIXES, grep_scope)
    self_prefix = "artifacts/worker-083/ref01_rev29_disposition/"
    citations = {}
    for pref, paths in grepped.items():
        keep = [p for p in paths if p != REPORT_PATH and not p.startswith(self_prefix)]
        citations[pref] = sorted(keep)
    map_obj, map_dup = strict_json(ROOT / "research_map/research_map.json")
    map_sha = sha256_file(ROOT / "research_map/research_map.json")
    gate_refs = {}
    for g in map_obj.get("gates", []):
        gate_refs[g.get("gate_id")] = [r for r in g.get("evidence_refs", [])
                                       if "close_findings_rev27" in r or "closefind" in r]
    all_gate_refs = [r for g in map_obj.get("gates", []) for r in g.get("evidence_refs", [])]
    citing_files = sorted({p for paths in citations.values() for p in paths})
    cited_in_live_refs = sorted({p for p in citing_files
                                 if any(r.split("#")[0] == p for r in all_gate_refs)})
    operative_cited = any(r.split("#")[0] == GATE_TEST_REPORT_PATH for r in all_gate_refs)

    canonical = {
        "frozen_pin": FROZEN_PIN,
        "report_pin": REPORT_PIN,
        "tool_pin": TOOL_PIN,
        "entries": [{k: e[k] for k in ("path", "declared", "frozen_rev29_pin", "live", "classification")}
                    for e in entries],
        "checks": [{k: c[k] for k in ("id", "pass")} for c in checks],
    }
    digest = hashlib.sha256(json.dumps(canonical, sort_keys=True).encode()).hexdigest()

    return {
        "pins": pins,
        "frozen_dup_keys": frozen_dup,
        "report_dup_keys": report_dup,
        "entries": entries,
        "checks": checks,
        "tool_probe": probe,
        "scan": scan,
        "observations": {
            "registry_hits": registry_hits,
            "grep_prefix_hits": grepped,
            "intermediate_citations_excluding_report_and_self": citations,
            "citing_files_in_live_map_gate_refs": cited_in_live_refs,
            "gate_test_report_named_in_live_gate_refs": operative_cited,
            "map_sha256": map_sha,
            "map_duplicate_keys": map_dup,
            "gate_refs_naming_closure_report": gate_refs,
            "report_path_excluded_from_grep_self_reference": REPORT_PATH,
        },
        "canonical_digest_sha256": digest,
    }


def synthetic_controls(frozen):
    """Detector sensitivity controls on in-memory copies of the report."""
    report, _ = strict_json(ROOT / REPORT_PATH)
    controls = []

    def classify_all(rep):
        live_map = {p: sha256_file(ROOT / p) for p in rep["files"] if (ROOT / p).exists()}
        pin_map = {}
        for p in rep["files"]:
            pm = frozen["files"].get(p)
            pin_map[p] = pm["sha256"] if isinstance(pm, dict) else pm
        return [classify(m["sha256"], pin_map[p], live_map.get(p), []) for p, m in sorted(rep["files"].items())]

    c1 = json.loads(json.dumps(report))
    c1["files"]["schemas/af_wcc_vacuum.yaml"]["sha256"] = SCHEMA_PINS["schemas/af_wcc_vacuum.yaml"]
    r1 = classify_all(c1)
    controls.append({"id": "C1_live_value_mutation", "expected": "CURRENT count 2 (F0 + F1)",
                     "observed": f"CURRENT={r1.count('CURRENT')} STALE={r1.count('STALE_DECLARED')}",
                     "pass": r1.count("CURRENT") == 2})

    c2 = json.loads(json.dumps(report))
    d = c2["files"]["schemas/af_scc_c0_vacuum.yaml"]["sha256"]
    c2["files"]["schemas/af_scc_c0_vacuum.yaml"]["sha256"] = ("0" if d[0] != "0" else "1") + d[1:]
    r2 = classify_all(c2)
    controls.append({"id": "C2_one_digit_perturbation", "expected": "CURRENT still 1, perturbed entry STALE_DECLARED",
                     "observed": f"CURRENT={r2.count('CURRENT')} F2b={r2[sorted(c2['files']).index('schemas/af_scc_c0_vacuum.yaml')]}",
                     "pass": r2.count("CURRENT") == 1 and r2[sorted(c2["files"]).index("schemas/af_scc_c0_vacuum.yaml")] == "STALE_DECLARED"})

    c3 = json.loads(json.dumps(report))
    c3["files"]["artifacts/formulation/evidence/does_not_exist_083.json"] = {"sha256": "de" * 32}
    r3 = classify_all(c3)
    controls.append({"id": "C3_missing_path", "expected": "MISSING_PATH count 1",
                     "observed": f"MISSING_PATH={r3.count('MISSING_PATH')}",
                     "pass": r3.count("MISSING_PATH") == 1})

    c6 = json.loads(json.dumps(report))
    live_map = {p: sha256_file(ROOT / p) for p in c6["files"] if (ROOT / p).exists()}
    for p in c6["files"]:
        c6["files"][p]["sha256"] = live_map[p]
    r6 = classify_all(c6)
    controls.append({"id": "C6_all_live_positive_control", "expected": "8/8 CURRENT reachable",
                     "observed": f"CURRENT={r6.count('CURRENT')}",
                     "pass": r6.count("CURRENT") == len(c6["files"])})

    # C4: pin-guard unit test on the drift detector used by main()
    before = {"x": "a" * 64}
    c4 = pin_moved(before, {"x": "b" * 64})
    controls.append({"id": "C4_drift_detector", "expected": "in-memory pin mutation trips the drift guard",
                     "observed": f"pin_moved={c4}", "pass": bool(c4)})

    return controls


def pin_moved(before, after):
    return [k for k in before if before.get(k) != after.get(k)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-scan", action="store_true")
    args = ap.parse_args()

    missing = [p for p in (FROZEN_PATH, REPORT_PATH, TOOL_PATH) if not (ROOT / p).exists()]
    if missing:
        print("MISSING INPUTS:", missing)
        return 3

    before_guard = {p: sha256_file(ROOT / p) for p in GUARDED if (ROOT / p).exists()}
    m1 = core_measurement(do_scan=not args.no_scan)
    controls = synthetic_controls(strict_json(ROOT / FROZEN_PATH)[0])

    # C5 is the real write-guard observation from the tool probe
    controls.append({"id": "C5_tool_write_guard",
                     "expected": "0 of 12 guarded paths changed by the dry-run probe",
                     "observed": f"changed={m1['tool_probe']['changed_files']}",
                     "pass": not m1["tool_probe"]["changed_files"]})

    # determinism: re-run the static core, compare digest
    m2 = core_measurement(do_scan=False)
    controls.append({"id": "C7_determinism", "expected": "static canonical digest reproduces",
                     "observed": f"{m1['canonical_digest_sha256'][:14]} vs {m2['canonical_digest_sha256'][:14]}",
                     "pass": m1["canonical_digest_sha256"] == m2["canonical_digest_sha256"]})

    # drift guard over the bound inputs
    after = {p: sha256_file(ROOT / p) for p in GUARDED if (ROOT / p).exists()}
    drift = pin_moved(before_guard, after)

    hard_pass = all(c["pass"] for c in m1["checks"]) and all(c["pass"] for c in controls)

    report = {
        "audit_id": "W083-REF01-REV29-DISPOSITION-01",
        "actor": "worker-083",
        "gate": "G-FORM",
        "node_id": "F0,F1,F2a,F2b",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "defect_id": "W083-REF-01",
        "prior_report": "artifacts/worker-083/rev12_evidence_fixpoint/REPORT.md",
        "pins": m1["pins"],
        "duplicate_keys": {"frozen": m1["frozen_dup_keys"], "report": m1["report_dup_keys"]},
        "classification_rule": {
            "CURRENT": "declared == live bytes == FROZEN rev29 pin",
            "STALE_DECLARED": "declared != live bytes, declared != FROZEN pin, no copy in scan set",
            "HISTORICAL_COPY": "declared bytes recovered somewhere in the scan set",
            "PIN_ONLY": "declared == pin but != live (would be a freeze breach)",
            "MISSING_PATH": "declared path absent from disk",
        },
        "entries": m1["entries"],
        "checks": m1["checks"],
        "controls": controls,
        "tool_probe": m1["tool_probe"],
        "recoverability_scan": m1["scan"],
        "observations": m1["observations"],
        "drift": drift,
        "canonical_digest_sha256": m1["canonical_digest_sha256"],
        "verdict": ("PASS_REF01_DISPOSITION" if hard_pass and not drift else
                    ("DRIFT_VOID" if drift else "FAIL")),
        "falsifier": ("Exhibit (i) bytes matching one of b474fbc4/a7ccae4d/b71ec02c/f3c119a8 in a "
                      "canonical or archived artifact; or (ii) a FROZEN generation whose pinned rev27 "
                      "closure record declares the rev29 schema/taxonomy_consistency pins; or (iii) a "
                      "dry-run of the pinned tool that exits 0 with changed:false on every audited path; "
                      "or (iv) a post-measurement write to the report path that supersedes the declared "
                      "block. Any byte change among the bound inputs voids this measurement (re-run and "
                      "compare canonical_digest_sha256)."),
        "limits": [
            "artifact/evidence measurement only; no mathematics claim, no schema-content claim, no gate verdict",
            "workers cannot set node status, gate verdict or validation_status; canonical bytes untouched",
            "the consumer/ref observations are timestamped moving-target reads, not part of the hard pass",
        ],
    }

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    evidence = {
        "audit_id": report["audit_id"],
        "created_at": report["created_at"],
        "pins_at_start": m1["pins"],
        "pins_at_end": after,
        "tool_probe_transcript": {
            "cmd": m1["tool_probe"]["cmd"],
            "exit_code": m1["tool_probe"]["exit_code"],
            "stderr_head": m1["tool_probe"]["stderr_head"],
            "stdout_head": m1["tool_probe"]["stdout_head"],
            "changed_files": m1["tool_probe"]["changed_files"],
        },
        "scan_roots": "repo root minus " + ", ".join(sorted(SCAN_SKIP_DIRS)) + " and files >4MB",
        "scan_result": m1["scan"],
        "observations": m1["observations"],
        "canonical_digest_sha256": m1["canonical_digest_sha256"],
    }
    (OUT / "evidence.json").write_text(json.dumps(evidence, indent=1, sort_keys=True) + "\n")

    print(json.dumps({"verdict": report["verdict"], "digest": report["canonical_digest_sha256"],
                      "checks": {c["id"]: c["pass"] for c in report["checks"]},
                      "controls": {c["id"]: c["pass"] for c in controls},
                      "drift": drift}, indent=1))
    if drift:
        print("DRIFT:", drift)
        return 2
    return 0 if hard_pass else 1


if __name__ == "__main__":
    sys.exit(main())
