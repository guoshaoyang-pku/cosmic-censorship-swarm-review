#!/usr/bin/env python3
"""W059-GFORM-STAGE2-PIN-CLOSURE-01 — deterministic, read-only measurement of the
executable dependency closure of the two-stage class-schema acceptance pipeline at
FROZEN rev29, and of whether an UNPINNED instrument can move a gate-relevant verdict
while all 50 FROZEN pins stay byte-identical.

Task selection: no assignment card existed in comms/inbox/worker-059.jsonl; one bounded
class-bound task was self-selected from the live formulation-lead blocker
`lead-form-life08-123` (INSTRUMENT GOVERNANCE GAP) and the r3 required-before-proposal item
"pin the stage-2 tool".  Classes: AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN.

Authority: worker measurement only.  No canonical file is written, no node status, no
validation_status=passed, no gate verdict.  All sandbox writes are confined to this
artifact directory.

usage:
  python3 check_stage2_closure.py                 # measure, write report.json, exit 0/1
  python3 check_stage2_closure.py --verify        # re-measure and compare digest to report.json
  python3 check_stage2_closure.py --out PATH      # alternate report path
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
WORK = HERE / "work"
RAW = HERE / "raw"
TRACER = HERE / "trace_run.py"

FROZEN = ROOT / "artifacts" / "formulation" / "FROZEN.json"
RUN_ACCEPT = ROOT / "artifacts" / "formulation" / "tools" / "run_acceptance.py"
STAGE1 = ROOT / "artifacts" / "formulation" / "tools" / "check_class_schema.py"
STAGE2 = ROOT / "artifacts" / "worker-06" / "spec_conformance_audit.py"
RULE_SPEC = ROOT / "artifacts" / "formulation" / "rule_spec.json"
FIXTURES = ROOT / "artifacts" / "worker-06" / "semantic_fixtures"
ARTIFACT_HASHES = ROOT / "runtime" / "state" / "artifact_hashes.json"

CANONICAL = {
    "F1": ROOT / "schemas" / "af_wcc_vacuum.yaml",
    "F2a": ROOT / "schemas" / "af_scc_c2_vacuum.yaml",
    "F2b": ROOT / "schemas" / "af_scc_c0_vacuum.yaml",
}
VARIANTS = {
    "variable_wise": ROOT / "tmp" / "lead-form-life08" / "variant_frozen_variable_wise_intended_correct.yaml",
    "grouped_tuple": ROOT / "tmp" / "lead-form-life08" / "variant_grouped_tuple_intended_correct.yaml",
    "scope_error": ROOT / "tmp" / "lead-form-life08" / "variant_scope_error_negation_binds_q_only.yaml",
}

PATH_RE = re.compile(r"(?:artifacts|schemas|ledger|numerics|evaluation|research_map|tmp)/[A-Za-z0-9_./+-]+")
R03_OLD = (
    "                for b in binders:\n"
    "                    if b not in formal:\n"
    '                        bad.append(f"binder {b!r} absent from formal sentence")\n'
)
R03_NEW = (
    "                for b in binders:\n"
    '                    _toks = [t for t in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", b)]\n'
    "                    if any(t not in formal for t in _toks):\n"
    '                        bad.append(f"binder {b!r} absent from formal sentence")\n'
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def run_traced(target: Path, args: list[str], tag: str) -> tuple[int, list[str]]:
    trace_out = RAW / f"trace_{tag}.json"
    stdout = RAW / f"stdout_{tag}.log"
    stderr = RAW / f"stderr_{tag}.log"
    with open(stdout, "w", encoding="utf-8") as out, open(stderr, "w", encoding="utf-8") as err:
        proc = subprocess.run(
            [sys.executable, str(TRACER), str(ROOT), str(trace_out), str(target), *args],
            cwd=str(ROOT),
            stdout=out,
            stderr=err,
            timeout=900,
        )
    files = json.loads(trace_out.read_text(encoding="utf-8")) if trace_out.exists() else []
    closure = []
    for p in files:
        try:
            rp = Path(p).resolve().relative_to(ROOT)
        except ValueError:
            continue  # e.g. "<string>" or stdlib paths outside the repo
        if str(rp).startswith("artifacts/worker-059/stage2_pin_closure"):
            continue  # this harness's own outputs are not pipeline dependencies
        if not (ROOT / rp).is_file():
            continue  # synthetic code objects such as "<string>" are not files
        closure.append(str(rp))
    return proc.returncode, sorted(set(closure))


def run_plain(target: Path, args: list[str], tag: str) -> int:
    stdout = RAW / f"plain_stdout_{tag}.log"
    stderr = RAW / f"plain_stderr_{tag}.log"
    with open(stdout, "w", encoding="utf-8") as out, open(stderr, "w", encoding="utf-8") as err:
        proc = subprocess.run(
            [sys.executable, str(target), *args],
            cwd=str(ROOT),
            stdout=out,
            stderr=err,
            timeout=900,
        )
    return proc.returncode


def stage2_verdict(target: Path, schema: Path, tag: str) -> dict:
    out_json = RAW / f"verdict_{tag}.json"
    if out_json.exists():
        out_json.unlink()
    rc = run_plain(target, [str(schema), "--json", str(out_json)], tag)
    doc = json.loads(out_json.read_text(encoding="utf-8")) if out_json.exists() else {}
    return {
        "exit": rc,
        "verdict": doc.get("verdict"),
        "failed_rules": doc.get("failed_rules", []),
        "doc_sha256": doc.get("doc_sha256"),
    }


def static_refs(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    found = set()
    for m in PATH_RE.findall(text):
        cand = ROOT / m
        if cand.is_file():
            found.add(rel(cand))
    return sorted(found)


def build_sandbox(name: str) -> Path:
    base = WORK / name
    if base.exists():
        shutil.rmtree(base)
    for src in [STAGE2, STAGE1, RUN_ACCEPT, RULE_SPEC, *CANONICAL.values(), *VARIANTS.values()]:
        dst = base / src.relative_to(ROOT)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    shutil.copytree(FIXTURES, base / FIXTURES.relative_to(ROOT))
    return base


def apply_mutation(tree: Path) -> dict:
    target = tree / STAGE2.relative_to(ROOT)
    text = target.read_text(encoding="utf-8")
    n = text.count(R03_OLD)
    if n != 1:
        return {"applied": False, "occurrences": n}
    target.write_text(text.replace(R03_OLD, R03_NEW), encoding="utf-8")
    return {"applied": True, "occurrences": n, "old": R03_OLD, "new": R03_NEW}


def tree_diff(a: Path, b: Path) -> list[str]:
    out = []
    files_a = sorted(p.relative_to(a) for p in a.rglob("*") if p.is_file())
    files_b = sorted(p.relative_to(b) for p in b.rglob("*") if p.is_file())
    for name in sorted(set(files_a) | set(files_b)):
        pa, pb = a / name, b / name
        if not pa.exists() or not pb.exists() or sha256_file(pa) != sha256_file(pb):
            out.append(str(name))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "report.json"))
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()

    RAW.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)

    frozen_bytes = FROZEN.read_bytes()
    frozen = json.loads(frozen_bytes)
    pins = frozen.get("files") or {}
    artifact_hashes = {}
    if ARTIFACT_HASHES.exists():
        ah = json.loads(ARTIFACT_HASHES.read_text(encoding="utf-8"))
        artifact_hashes = ah if isinstance(ah, dict) else {}

    # ---- 1. pin verification ------------------------------------------------
    drift = []
    for path, meta in sorted(pins.items()):
        want = meta.get("sha256") if isinstance(meta, dict) else meta
        live = ROOT / path
        got = sha256_file(live) if live.is_file() else None
        if got != want:
            drift.append({"path": path, "pinned": want, "measured": got})

    # ---- 2. static closure ---------------------------------------------------
    static_closure = {
        rel(p): {"sha256": sha256_file(p), "refs": static_refs(p)}
        for p in [RUN_ACCEPT, STAGE1, STAGE2]
    }

    # ---- 3. dynamic closure --------------------------------------------------
    canonical_f1 = CANONICAL["F1"]
    rc_stage1, closure_stage1 = run_traced(STAGE1, [str(canonical_f1), "--json"], "stage1_f1")
    rc_stage2, closure_stage2 = run_traced(STAGE2, [str(canonical_f1), "--json", str(RAW / "stage2_f1.json")], "stage2_f1")
    rc_selftest, closure_selftest = run_traced(STAGE2, ["--selftest", "--json", str(RAW / "stage2_selftest.json")], "stage2_selftest")
    dynamic_closure = {
        "stage1": sorted(set(closure_stage1)),
        "stage2_f1": sorted(set(closure_stage2)),
        "stage2_selftest": sorted(set(closure_selftest)),
    }

    # ---- 4. classification ---------------------------------------------------
    closure_all = sorted(
        set(static_closure)
        | {r for v in static_closure.values() for r in v["refs"]}
        | set(closure_stage1)
        | set(closure_stage2)
        | set(closure_selftest)
    )
    def classify(rpath: str, got: str | None = None) -> dict:
        live = ROOT / rpath
        if got is None:
            got = sha256_file(live) if live.is_file() else None
        pinned = rpath in pins
        want = (pins.get(rpath) or {}).get("sha256") if isinstance(pins.get(rpath), dict) else pins.get(rpath)
        tracked = rpath in artifact_hashes
        if pinned and got == want:
            status = "PINNED_OK"
        elif pinned:
            status = "PINNED_STALE"
        elif tracked:
            status = "UNPINNED_TRACKED"
        else:
            status = "UNPINNED_UNTRACKED"
        return {
            "path": rpath,
            "sha256": got,
            "in_frozen": pinned,
            "frozen_sha256": want,
            "in_artifact_hashes": tracked,
            "status": status,
        }

    rows = [classify(rpath) for rpath in closure_all]
    unpinned_code = [
        r["path"]
        for r in rows
        if r["status"].startswith("UNPINNED") and r["path"].endswith(".py")
    ]
    unpinned_all = [r["path"] for r in rows if r["status"].startswith("UNPINNED")]

    # ---- 5. governance observations -----------------------------------------
    preflight_rc = run_plain(RUN_ACCEPT, [], "run_acceptance_preflight")
    preflight_text = (RAW / "plain_stdout_run_acceptance_preflight.log").read_text(encoding="utf-8", errors="replace")
    preflight_text += (RAW / "plain_stderr_run_acceptance_preflight.log").read_text(encoding="utf-8", errors="replace")

    # ---- 6. mutation control -------------------------------------------------
    pristine = build_sandbox("pristine")
    mutated = build_sandbox("mutated")
    mutation = apply_mutation(mutated)
    tree_delta = tree_diff(pristine, mutated)

    cases = {
        "canonical_F1": CANONICAL["F1"],
        "variable_wise": VARIANTS["variable_wise"],
        "grouped_tuple": VARIANTS["grouped_tuple"],
        "scope_error": VARIANTS["scope_error"],
        "leak_sem12": FIXTURES / "sem12_theorem_promotion.yaml",
    }
    baseline, after = {}, {}
    for tag, schema in cases.items():
        baseline[tag] = stage2_verdict(pristine / STAGE2.relative_to(ROOT), schema, f"baseline_{tag}")
        after[tag] = stage2_verdict(mutated / STAGE2.relative_to(ROOT), schema, f"mutated_{tag}")

    # re-verify canonical pins after every mutation run
    drift_after = []
    for path, meta in sorted(pins.items()):
        want = meta.get("sha256") if isinstance(meta, dict) else meta
        live = ROOT / path
        got = sha256_file(live) if live.is_file() else None
        if got != want:
            drift_after.append({"path": path, "pinned": want, "measured": got})

    # ---- 7. expectations, mutants, controls ---------------------------------
    stage2_pinned = rel(STAGE2) in pins
    expectations = [
        {"id": "E1", "statement": "FROZEN revision is 29", "pass": frozen.get("revision") == 29},
        {"id": "E2", "statement": "pin census covers all 50 declared FROZEN pins", "pass": len(pins) == 50},
        {"id": "E3", "statement": "run_acceptance.py is PINNED at live bytes", "pass": rel(RUN_ACCEPT) in pins and sha256_file(RUN_ACCEPT) == pins[rel(RUN_ACCEPT)]["sha256"]},
        {"id": "E4", "statement": "stage-1 check_class_schema.py is PINNED at live bytes", "pass": rel(STAGE1) in pins and sha256_file(STAGE1) == pins[rel(STAGE1)]["sha256"]},
        {"id": "E5", "statement": "stage-2 engine spec_conformance_audit.py is NOT in the FROZEN pin set", "pass": not stage2_pinned},
        {"id": "E6", "statement": "dynamic closure of stage 2 contains the stage-2 engine and rule_spec.json", "pass": rel(STAGE2) in dynamic_closure["stage2_f1"] and rel(RULE_SPEC) in dynamic_closure["stage2_f1"]},
        {"id": "E7", "statement": "stage-2 closure contains at least one unpinned .py dependency", "pass": len(unpinned_code) >= 1},
        {"id": "E8", "statement": "baseline stage 2 rejects the untouched canonical F1 on R03", "pass": baseline["canonical_F1"]["exit"] == 1 and baseline["canonical_F1"]["verdict"] == "reject" and baseline["canonical_F1"]["failed_rules"] == ["R03"]},
        {"id": "E9", "statement": "a one-line edit to the UNPINNED stage-2 engine flips the canonical F1 verdict to accept", "pass": after["canonical_F1"]["exit"] == 0 and after["canonical_F1"]["verdict"] == "accept"},
        {"id": "E10", "statement": "the sandbox mutation runs introduce NO new canonical pin drift (drift_after == drift_before)", "pass": drift_after == drift},
        {"id": "E11", "statement": "mutated engine also accepts the negation-scope-error variant that baseline rejects (no scope discrimination)", "pass": baseline["scope_error"]["verdict"] == "reject" and after["scope_error"]["verdict"] == "accept"},
        {"id": "E12", "statement": "mutation isolation: exactly one sandbox file differs between pristine and mutated trees", "pass": tree_delta == [rel(STAGE2)]},
        {"id": "E13", "statement": "leak control: the mutated engine still rejects sem12_theorem_promotion (mutation is not a blanket disable)", "pass": after["leak_sem12"]["verdict"] == "reject" and after["leak_sem12"]["failed_rules"] == ["R11"]},
        {"id": "E14", "statement": "positive control: the grouped-tuple variant is accepted by both instruments", "pass": baseline["grouped_tuple"]["verdict"] == "accept" and after["grouped_tuple"]["verdict"] == "accept"},
    ]

    # harness mutants / self-tests (must fire)
    m1 = len([d for d in [{"path": "x", "pinned": "a", "measured": "b"}] if d["pinned"] != d["measured"]]) == 1
    m2 = classify("artifacts/worker-059/stage2_pin_closure/not_a_pinned_file.py", got="0" * 64)["status"] == "UNPINNED_UNTRACKED"
    m3 = R03_OLD not in (mutated / STAGE2.relative_to(ROOT)).read_text(encoding="utf-8") and R03_OLD in (pristine / STAGE2.relative_to(ROOT)).read_text(encoding="utf-8")
    mutants = [
        {"id": "M1", "statement": "pin-drift comparator fires on an injected mismatch", "pass": m1},
        {"id": "M2", "statement": "classifier returns UNPINNED_UNTRACKED for an untracked file", "pass": m2},
        {"id": "M3", "statement": "mutation applied to the mutated tree only (pristine retains R03 literal)", "pass": m3},
    ]

    measurement = {
        "task_id": "W059-GFORM-STAGE2-PIN-CLOSURE-01",
        "classes": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "nodes": ["F1", "F2a", "F2b"],
        "gate_context": "G-FORM",
        "inputs": {
            "artifacts/formulation/FROZEN.json": sha256_file(FROZEN),
            "artifacts/formulation/tools/run_acceptance.py": sha256_file(RUN_ACCEPT),
            "artifacts/formulation/tools/check_class_schema.py": sha256_file(STAGE1),
            "artifacts/worker-06/spec_conformance_audit.py": sha256_file(STAGE2),
            "artifacts/formulation/rule_spec.json": sha256_file(RULE_SPEC),
            **{rel(p): sha256_file(p) for p in VARIANTS.values()},
        },
        "frozen_revision": frozen.get("revision"),
        "frozen_pin_count": len(pins),
        "pin_drift_before": drift,
        "pin_drift_after": drift_after,
        "static_closure": static_closure,
        "dynamic_closure": dynamic_closure,
        "classification": rows,
        "unpinned_all": unpinned_all,
        "unpinned_code": unpinned_code,
        "governance": {
            "run_acceptance_pinned": rel(RUN_ACCEPT) in pins,
            "stage1_pinned": rel(STAGE1) in pins,
            "stage2_pinned": stage2_pinned,
            "stage2_depends_on_unpinned_code": sorted(set(unpinned_code)),
            "run_acceptance_preflight_exit": preflight_rc,
            "run_acceptance_preflight_tail": preflight_text.strip().splitlines()[-4:],
            "dynamic_closure_exit_codes": {"stage1_f1": rc_stage1, "stage2_f1": rc_stage2, "stage2_selftest": rc_selftest},
        },
        "mutation": {
            "edit": mutation,
            "isolation_diff": tree_delta,
            "baseline": baseline,
            "after": after,
        },
        "expectations": expectations,
        "mutants": mutants,
        "falsifier": (
            "Re-run this harness at the same input hashes: it is FALSIFIED if the measurement_digest "
            "changes, if any expectation E1-E14 flips, if any FROZEN rev29 pin measures differently, or if the "
            "unpinned stage-2 engine is pinned in a later FROZEN revision without this report being re-issued. "
            "The governance conclusion (an unpinned file can flip a gate-relevant stage-2 verdict with 0/50 pins "
            "moved) is falsified if the canonical F1 verdict after the sandbox R03 edit is not accept."
        ),
    }
    digest = hashlib.sha256(
        json.dumps(measurement, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    report = {
        "schema": "worker-measurement/1",
        "actor": "worker-059",
        "created_at": "2026-09-12T01:24:00+08:00",
        "measured_at": None,  # filled below from wall clock, excluded from digest
        "authority": "worker measurement only; no canonical write, no node status, no gate verdict",
        "measurement": measurement,
        "measurement_digest": digest,
    }
    import datetime

    report["measured_at"] = datetime.datetime.now(
        datetime.timezone(datetime.timedelta(hours=8))
    ).strftime("%Y-%m-%dT%H:%M:%S+08:00")

    # Volatile worktree observations, deliberately OUTSIDE measurement_digest.
    observations = []
    for d in drift:
        live = ROOT / d["path"]
        observations.append(
            {
                "kind": "FROZEN_PIN_DRIFT_AT_MEASUREMENT",
                "path": d["path"],
                "pinned_sha256": d["pinned"],
                "measured_sha256": d["measured"],
                "mtime": datetime.datetime.fromtimestamp(live.stat().st_mtime).strftime("%Y-%m-%dT%H:%M:%S+08:00")
                if live.is_file()
                else None,
                "note": "live byte drift against FROZEN rev29 during the rev14 window; not introduced by this harness (drift_after == drift_before)",
            }
        )
    report["worktree_observations"] = observations

    all_pass = all(e["pass"] for e in expectations) and all(m["pass"] for m in mutants)
    report["expectations_all_pass"] = all_pass

    out_path = Path(args.out)
    if args.verify:
        if not out_path.exists():
            print("VERIFY FAIL: no report to compare")
            return 1
        prev = json.loads(out_path.read_text(encoding="utf-8"))
        prev_digest = prev.get("measurement_digest")
        ok = prev_digest == digest
        print(f"verify: digest {digest[:16]} prev {str(prev_digest)[:16]} -> {'MATCH' if ok else 'MISMATCH'}")
        if not ok:
            return 1
        return 0 if all_pass else 1

    out_path.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")

    print(f"task W059-GFORM-STAGE2-PIN-CLOSURE-01  digest={digest[:16]}")
    print(f"FROZEN rev{frozen.get('revision')} pins={len(pins)} drift_before={len(drift)} drift_after={len(drift_after)}")
    print(f"closure files={len(rows)} unpinned={len(unpinned_all)} unpinned_code={unpinned_code}")
    print(f"stage2_pinned={stage2_pinned} run_acceptance_pinned={rel(RUN_ACCEPT) in pins} preflight_exit={preflight_rc}")
    for tag in cases:
        print(f"  {tag:14s} baseline={baseline[tag]['verdict']:6s}{baseline[tag]['failed_rules']}  mutated={after[tag]['verdict']:6s}{after[tag]['failed_rules']}")
    for e in expectations:
        print(f"  {e['id']:4s} {'PASS' if e['pass'] else 'FAIL'}  {e['statement']}")
    for m in mutants:
        print(f"  {m['id']:4s} {'PASS' if m['pass'] else 'FAIL'}  {m['statement']}")
    print(f"ALL_PASS={all_pass}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
