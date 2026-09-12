#!/usr/bin/env python3
"""W087-GFORM-REV14-LANDING-ATTEST-01 checker.

Read-only on every canonical path. Writes only under
artifacts/worker-087/rev14_landing_attest/.

Measures, at T1:
  H1  rev29 pin drift set vs the lead's declared landing scope (rollback pre-images)
  H2  schema mirror-pair byte equality (schemas/X vs artifacts/formulation/schemas/X)
  H3  rebased f1-suite per-row binding vs live bytes (F1 d9cebb9404b2)
  H4  corpus declared binding_frozen_revision vs on-disk FROZEN.revision
  H5  unchanged-scope control: F1 / F0 canonical / FROZEN.json stable T0->T1
  C1  pinned verify_frozen.py instrument (independent)
  C2  two-run determinism of the comparators
  C3  mutant-copy positive control for the corpus comparator
  C4  parse/well-formedness control (yaml/json loads only)
See PREREGISTRATION.json for hypotheses, predictions and falsifiers.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
T1 = HERE / "T1"
T1.mkdir(exist_ok=True)

MEASURED = [
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
    "schemas/f1_falsifier_tests.jsonl",
    "schemas/taxonomy_cases.jsonl",
    "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
    "artifacts/formulation/FROZEN.json",
    "artifacts/formulation/VARIANT_REGISTRY.json",
    "artifacts/formulation/rule_spec.json",
    "artifacts/formulation/tools/run_acceptance.py",
    "artifacts/formulation/tools/check_class_schema.py",
    "artifacts/formulation/tools/verify_frozen.py",
    "artifacts/formulation/tools/check_variant_registry.py",
    "artifacts/formulation/tools/check_conclusion_type_crosswalk.py",
    "artifacts/worker-06/spec_conformance_audit.py",
    "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json",
    "artifacts/formulation/variants/AF-SCC-C0-VAC-GEN.variant-CH.delta.json",
    "artifacts/formulation/CONCLUSION_TYPE_CROSSWALK.json",
]


def sha(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def snapshot(paths) -> dict:
    out = {}
    for p in paths:
        f = ROOT / p
        if f.exists():
            out[p] = {"sha256": sha(p), "bytes": f.stat().st_size}
        else:
            out[p] = {"sha256": None, "bytes": None, "missing": True}
    return out


def frozen() -> dict:
    return json.loads((ROOT / "artifacts/formulation/FROZEN.json").read_text())


def drift_table() -> dict:
    man = frozen()
    rows = {}
    for p, rec in man["files"].items():
        f = ROOT / p
        if not f.exists():
            rows[p] = {"pin": rec["sha256"], "live": None, "status": "MISSING"}
            continue
        live = sha(p)
        rows[p] = {
            "pin": rec["sha256"],
            "live": live,
            "status": "MATCH" if live == rec["sha256"] else "DRIFT",
        }
    return {"revision": man["revision"], "n_files": len(man["files"]), "rows": rows}


def landing_scope() -> list:
    scopes = set()
    for f in sorted((ROOT / "artifacts/formulation/rollback").glob("*.pre-rev14.*.rollback")):
        head = f.name.split(".pre-rev14.")[0]
        scopes.add(head.replace("__", "/"))
    return sorted(scopes)


def compare_corpus(corpus_path: Path) -> dict:
    """Per-row binding check of an f1_falsifier_tests.jsonl copy against live schema bytes."""
    rows = []
    text = corpus_path.read_text()
    for i, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        r = json.loads(line)
        ref = str(r.get("binding_ref", ""))
        m = re.match(r"^([^#]+)#sha256:([0-9a-f]+)$", ref)
        ref_path = m.group(1) if m else None
        ref_hash = m.group(2) if m else None
        live = sha(ref_path) if ref_path and (ROOT / ref_path).exists() else None
        declared = r.get("binding_sha256")
        rows.append({
            "line": i,
            "test_id": r.get("test_id"),
            "class_id": r.get("class_id"),
            "binding_ref_path": ref_path,
            "binding_ref_hash_prefix": (ref_hash or "")[:16] or None,
            "declared_sha256": declared,
            "live_sha256": live,
            "ref_matches_live_path": bool(live) and (ref_hash or "").startswith(live[: len(ref_hash or "")]),
            "declared_matches_live": bool(live) and declared == live,
            "binding_frozen_revision": r.get("binding_frozen_revision"),
        })
    stale = [r for r in rows if not (r["ref_matches_live_path"] and r["declared_matches_live"])]
    revs = sorted({r["binding_frozen_revision"] for r in rows})
    return {
        "path": str(corpus_path),
        "n_rows": len(rows),
        "n_stale": len(stale),
        "stale_test_ids": [r["test_id"] for r in stale],
        "declared_revisions": revs,
        "rows": rows,
    }


def parse_checks() -> dict:
    out = {}
    try:
        import yaml  # noqa: PLC0415
        for p in ["schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml", "schemas/af_scc_c0_vacuum.yaml"]:
            try:
                yaml.safe_load((ROOT / p).read_text())
                out[p] = "yaml:ok"
            except Exception as e:  # noqa: BLE001
                out[p] = f"yaml:FAIL:{type(e).__name__}"
    except Exception as e:  # noqa: BLE001
        out["yaml_module"] = f"unavailable:{type(e).__name__}"
    try:
        n = len([l for l in (ROOT / "schemas/f1_falsifier_tests.jsonl").read_text().splitlines() if l.strip()])
        [json.loads(l) for l in (ROOT / "schemas/f1_falsifier_tests.jsonl").read_text().splitlines() if l.strip()]
        out["schemas/f1_falsifier_tests.jsonl"] = f"jsonl:ok:{n}"
    except Exception as e:  # noqa: BLE001
        out["schemas/f1_falsifier_tests.jsonl"] = f"jsonl:FAIL:{type(e).__name__}"
    return out


def run_verify_frozen() -> dict:
    tool = ROOT / "artifacts/formulation/tools/verify_frozen.py"
    r = subprocess.run([sys.executable, str(tool)], capture_output=True, text=True)
    return {"cmd": "python3 artifacts/formulation/tools/verify_frozen.py",
            "exit": r.returncode, "stdout": r.stdout, "stderr": r.stderr}


def main() -> int:
    import time
    started = time.time()
    T0 = json.loads((HERE / "T0/pins_T0.json").read_text())
    t1_snapshot = snapshot(MEASURED)
    (T1 / "pins_T1.json").write_text(json.dumps(
        {"captured_at": subprocess.run(["date", "-Iseconds"], capture_output=True, text=True).stdout.strip(),
         "files": [{"path": p, "sha256": v["sha256"], "bytes": v["bytes"]} for p, v in t1_snapshot.items()]},
        indent=2))

    # C1 independent pinned instrument
    c1 = run_verify_frozen()
    # H1
    dt = drift_table()
    scope = landing_scope()
    drift = sorted([p for p, r in dt["rows"].items() if r["status"] != "MATCH"])
    collateral = sorted(set(drift) - set(scope))
    missing_scope = sorted(set(scope) - set(drift))
    c1_lines = [l for l in c1["stdout"].splitlines() if l.strip().startswith(("DRIFT", "MISSING"))]
    c1_paths = sorted({l.split()[1].rstrip(":") for l in c1_lines if len(l.split()) > 1})
    rev_at_t1 = dt["revision"]
    if rev_at_t1 != 29:
        h1_verdict = "VOID_AT_T1_FROZEN_REV30"
    else:
        h1_verdict = "CONFIRMED" if (not collateral and not missing_scope and c1_paths == drift and c1["exit"] == 1) else "NOT_CONFIRMED"
    h1 = {
        "verdict": h1_verdict,
        "scope_n": len(scope), "drift_n": len(drift),
        "drift_paths": drift, "collateral": collateral, "scope_paths_that_did_not_drift": missing_scope,
        "verify_frozen_exit": c1["exit"], "verify_frozen_drift_paths": c1_paths,
        "recomputation_agrees_with_instrument": c1_paths == drift,
        "revision_at_T1": dt["revision"],
    }
    # H2
    mirrors = {}
    for name in ["af_wcc_vacuum.yaml", "af_scc_c2_vacuum.yaml", "af_scc_c0_vacuum.yaml"]:
        a, b = f"schemas/{name}", f"artifacts/formulation/schemas/{name}"
        mirrors[name] = {"a": t1_snapshot[a]["sha256"], "b": t1_snapshot[b]["sha256"],
                         "identical": t1_snapshot[a]["sha256"] == t1_snapshot[b]["sha256"]}
    h2 = {"verdict": "CONFIRMED" if all(m["identical"] for m in mirrors.values()) else "NOT_CONFIRMED",
          "pairs": mirrors}
    # H3 + C2 + C3
    corpus = ROOT / "schemas/f1_falsifier_tests.jsonl"
    cmp1 = compare_corpus(corpus)
    cmp2 = compare_corpus(corpus)
    c2_digest = hashlib.sha256(json.dumps(cmp1, sort_keys=True).encode()).hexdigest()
    c2_digest_b = hashlib.sha256(json.dumps(cmp2, sort_keys=True).encode()).hexdigest()
    c2 = {"verdict": "CONFIRMED" if c2_digest == c2_digest_b else "NOT_CONFIRMED",
          "digest_a": c2_digest, "digest_b": c2_digest_b}
    # C3 mutant positive control (sandbox copy)
    sb = HERE / "sandbox"
    sb.mkdir(exist_ok=True)
    mutant = sb / "f1_falsifier_tests.mutant.jsonl"
    lines = [l for l in corpus.read_text().splitlines() if l.strip()]
    r0 = json.loads(lines[0])
    r0["binding_sha256"] = "0" * 64
    lines[0] = json.dumps(r0, ensure_ascii=False)
    mutant.write_text("\n".join(lines) + "\n")
    cmp_mut = compare_corpus(mutant)
    c3 = {"verdict": "CONFIRMED" if (cmp_mut["n_stale"] == 1 and cmp_mut["stale_test_ids"] == [r0.get("test_id")]) else "NOT_CONFIRMED",
          "mutated_test_id": r0.get("test_id"), "mutant_stale_n": cmp_mut["n_stale"],
          "mutant_stale_ids": cmp_mut["stale_test_ids"], "base_stale_n": cmp1["n_stale"]}
    h3 = {"verdict": "CONFIRMED" if (cmp1["n_rows"] == 25 and cmp1["n_stale"] == 0 and c3["verdict"] == "CONFIRMED") else "NOT_CONFIRMED",
          "n_rows": cmp1["n_rows"], "n_stale": cmp1["n_stale"], "stale_test_ids": cmp1["stale_test_ids"],
          "declared_revisions": cmp1["declared_revisions"],
          "all_rows_bind_live_F1": cmp1["n_stale"] == 0,
          "rows": cmp1["rows"]}
    # H4
    man = frozen()
    rev30_keys = [k for k in man.keys() if "rev30" in k]
    declared_revs = cmp1["declared_revisions"]
    h4 = {"verdict": "CONFIRMED" if (man["revision"] == 29 and not rev30_keys and declared_revs == [30]) else "NOT_CONFIRMED",
          "on_disk_frozen_revision": man["revision"], "rev30_keys_present": rev30_keys,
          "corpus_declared_revisions": declared_revs,
          "gap": (declared_revs == [30] and man["revision"] != 30)}
    # H5 / H6 (T0 vs T1)
    t0map = {f["path"]: f.get("sha256") for f in T0["files"]}
    t1map = {p: v["sha256"] for p, v in t1_snapshot.items()}
    moved = sorted([p for p in MEASURED if t0map.get(p) != t1map.get(p)])
    controls = ["schemas/af_wcc_vacuum.yaml", "research_map/formulation_taxonomy.yaml", "artifacts/formulation/FROZEN.json"]
    ctrl_moved = [p for p in controls if t0map.get(p) != t1map.get(p)]
    expected_movers = set(scope) | {"artifacts/formulation/CONCLUSION_TYPE_CROSSWALK.json"}
    h5 = {"verdict": "CONFIRMED" if not ctrl_moved and t1map["schemas/af_wcc_vacuum.yaml"] == dt["rows"]["schemas/af_wcc_vacuum.yaml"]["pin"] else "NOT_CONFIRMED",
          "f1_sha256_T1": t1map["schemas/af_wcc_vacuum.yaml"], "f1_rev29_pin": dt["rows"]["schemas/af_wcc_vacuum.yaml"]["pin"],
          "f0_canonical_sha256_T1": sha("research_map/formulation_taxonomy.yaml"),
          "control_files_moved": ctrl_moved}
    h6 = {"verdict": "CONFIRMED" if not [p for p in moved if p not in expected_movers] else "NOT_CONFIRMED",
          "moved_paths_T0_T1": moved, "explained_by_landing_scope": sorted(set(moved) & expected_movers),
          "unexplained_moves": [p for p in moved if p not in expected_movers]}

    report = {
        "task_id": "W087-GFORM-REV14-LANDING-ATTEST-01",
        "worker": "worker-087",
        "node_id": "F1,F2a,F2b",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate": "G-FORM",
        "kind": "binding/temporal-consistency attestation, not a gate verdict",
        "T0_captured_at": T0["captured_at"],
        "T1_captured_at": json.loads((T1 / "pins_T1.json").read_text())["captured_at"],
        "elapsed_s": round(time.time() - started, 3),
        "frozen_revision_at_T1": dt["revision"],
        "frozen_sha256_at_T1": sha("artifacts/formulation/FROZEN.json"),
        "hypotheses": {"H1": h1, "H2": h2, "H3": h3, "H4": h4, "H5": h5, "H6": h6},
        "controls": {"C1_verify_frozen": c1, "C2_determinism": c2, "C3_mutant_positive_control": c3,
                     "C4_parse": parse_checks()},
        "declared_landing_scope": scope,
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    (HERE / "runs.json").write_text(json.dumps({"verify_frozen": c1, "corpus_rows": cmp1["rows"],
                                                "drift_rows": dt["rows"]}, indent=2) + "\n")
    for k, v in report["hypotheses"].items():
        print(f"{k}: {v['verdict']}")
    print("frozen revision T1:", dt["revision"], "| drift:", len(drift), "| collateral:", len(collateral))
    print("verify_frozen exit:", c1["exit"], "| instrument paths == recomputation:", c1_paths == drift)
    print("corpus rows:", cmp1["n_rows"], "stale:", cmp1["n_stale"], "declared revs:", declared_revs)
    print("moved T0->T1:", moved)
    return 0


if __name__ == "__main__":
    sys.exit(main())
