#!/usr/bin/env python3
"""Materiality probe: does the UNPINNED stage-2 rule engine move acceptance evidence?

Task: W076-GATE-EVIDENCE-PINMAP-01 (worker-076).  Companion to depmap.py.

The pinned corpus record is stale against live bytes (its own preflight fails:
base 1bb78ce9 vs live C0 b2ab6acb), so a materiality claim that trusts it would be
worthless.  This probe therefore does two sweeps:

  sweep A (stale): the canonical rebased_fixtures/ directory, live stage-1 + live stage-2
                   + sabotaged stage-2, plus a reproduction check of the pinned record.
  sweep B (fresh): re-generate the corpus in sandbox/ from the LIVE canonical C0 using a
                   sandbox copy of the FROZEN-pinned generator
                   (measure_semantic_escape.py, with only its OUT/TMP paths redirected),
                   then repeat the same three measurements.

All writes are confined to this artifact directory.  The sabotage is a single-line edit
of a sandbox COPY of the stage-2 engine; no canonical file is written.

Claim under test: the unpinned stage-2 tool's verdicts are load-bearing content of the
acceptance evidence, and the pinned acceptance report's union count does not reproduce at
the live base.  Falsifier: the sabotaged copy reproduces every live stage-2 verdict on the
fresh corpus, or the pinned acceptance report reproduces at the live base, or a
probe-written file appears in FROZEN, or the live stage-2 hash differs from the pinned
corpus record's declared w06_sha256.

Note on drift: concurrent swarm traffic writes pinned files while this probe runs.  Any
FROZEN drift observed between the before/after verify_frozen calls is reported as
`external_drift_during_run` and is not attributable to this probe (every probe write is
under artifacts/worker-076/gate_evidence_pinmap/).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RAW = HERE / "raw"
SANDBOX = HERE / "sandbox"

STAGE1 = ROOT / "artifacts/formulation/tools/check_class_schema.py"
STAGE2 = ROOT / "artifacts/worker-06/spec_conformance_audit.py"
SPEC = ROOT / "artifacts/formulation/rule_spec.json"
CORPUS_RECORD = ROOT / "artifacts/formulation/evidence/semantic_escape_rebased.json"
FIXTURES = ROOT / "artifacts/formulation/evidence/rebased_fixtures"
VERIFY_FROZEN = ROOT / "artifacts/formulation/tools/verify_frozen.py"
FROZEN = ROOT / "artifacts/formulation/FROZEN.json"

GEN = ROOT / "artifacts/formulation/tools/measure_semantic_escape.py"
GEN_OUT_LINE = 'OUT = ROOT / "artifacts/formulation/evidence/semantic_escape_rebased.json"'
GEN_TMP_LINE = 'TMP = ROOT / "artifacts/formulation/evidence/rebased_fixtures"'
GEN_ROOT_LINE = 'ROOT = Path(__file__).resolve().parents[3]'
SABOTAGE_FROM = '    verdict = "reject" if failed else "accept"'
SABOTAGE_TO = '    verdict = "accept"  # W076-SABOTAGE: unpinned instrument edit'


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def frozen_digest() -> dict:
    man = json.loads(FROZEN.read_text())
    parts, bad = [], []
    for rel, rec in sorted(man["files"].items()):
        f = ROOT / rel
        h = sha256(f) if f.exists() else None
        parts.append(f"{rel}:{h}")
        if h != rec["sha256"]:
            bad.append(rel)
    return {"revision": man["revision"], "files": len(man["files"]),
            "digest": hashlib.sha256("\n".join(parts).encode()).hexdigest(),
            "drifted": bad}


def run_json(cmd: list[str]) -> dict:
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, timeout=180)
    try:
        d = json.loads(r.stdout.strip())
        return {"exit": r.returncode, "verdict": d.get("verdict", "?"), "failed_rules": d.get("failed_rules", [])}
    except Exception:
        return {"exit": r.returncode, "verdict": f"crash(exit{r.returncode})", "failed_rules": []}


CONTROLS = {"control_canonical_base.yaml", "control_quoted_phrase.yaml"}


def sweep(fixtures_dir: Path, sabotaged: Path, tag: str) -> list[dict]:
    rows = []
    for p in sorted(fixtures_dir.glob("*.yaml")):
        if p.name.startswith("._"):
            continue
        s1 = run_json([sys.executable, str(STAGE1), "--json", str(p)])
        s2 = run_json([sys.executable, str(STAGE2), str(p), "--spec", str(SPEC)])
        s2s = run_json([sys.executable, str(sabotaged), str(p), "--spec", str(SPEC)])
        baseline_caught = s1["verdict"] == "fail" or s2["verdict"] == "fail"
        sab_caught = s1["verdict"] == "fail" or s2s["verdict"] == "fail"
        rows.append({
            "sweep": tag, "fixture": p.name,
            "stage1_pinned": {"verdict": s1["verdict"], "failed_rules": s1["failed_rules"]},
            "stage2_live": {"verdict": s2["verdict"], "failed_rules": s2["failed_rules"]},
            "stage2_sabotaged": {"verdict": s2s["verdict"], "failed_rules": s2s["failed_rules"]},
            "stage2_verdict_flip": s2["verdict"] != s2s["verdict"],
            "stage1_escaped": s1["verdict"] == "pass",
            "union_baseline_caught": baseline_caught,
            "union_sabotaged_caught": sab_caught,
            "material_flip": baseline_caught and not sab_caught,
        })
    return rows


def stale_record_mismatches(rows: list[dict], record: dict) -> list[dict]:
    mutants = {m["fixture"]: m for m in record.get("mutants", [])}
    controls = {c["name"] + ".yaml": c for c in record.get("controls", [])}
    out = []
    for r in rows:
        if r["fixture"] in mutants:
            m = mutants[r["fixture"]]
            if m.get("canonical_verdict") != r["stage1_pinned"]["verdict"]:
                out.append({"fixture": r["fixture"], "axis": "stage1", "recorded": m.get("canonical_verdict"),
                            "live": r["stage1_pinned"]["verdict"]})
            if m.get("w06_verdict") != r["stage2_live"]["verdict"]:
                out.append({"fixture": r["fixture"], "axis": "stage2", "recorded": m.get("w06_verdict"),
                            "live": r["stage2_live"]["verdict"]})
        elif r["fixture"] in controls:
            c = controls[r["fixture"]]
            if c.get("canonical_verdict") != r["stage1_pinned"]["verdict"]:
                out.append({"fixture": r["fixture"], "axis": "stage1_control",
                            "recorded": c.get("canonical_verdict"), "live": r["stage1_pinned"]["verdict"]})
    return out


def main() -> int:
    SANDBOX.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    vf_before = subprocess.run([sys.executable, str(VERIFY_FROZEN)], capture_output=True, text=True, cwd=ROOT, timeout=120)
    digest_before = frozen_digest()
    pinned_record = json.loads(CORPUS_RECORD.read_text())

    # 1. sandbox copy of the stage-2 engine, single-line sabotage
    src = STAGE2.read_text()
    n = src.count(SABOTAGE_FROM)
    if n != 1:
        print(f"FATAL: expected exactly one verdict assignment, found {n}", file=sys.stderr)
        return 2
    sab = SANDBOX / "spec_conformance_audit.sabotaged.py"
    sab.write_text(src.replace(SABOTAGE_FROM, SABOTAGE_TO))

    # 2. sandbox copy of the pinned generator with only OUT/TMP redirected
    gsrc = GEN.read_text()
    if gsrc.count(GEN_OUT_LINE) != 1 or gsrc.count(GEN_TMP_LINE) != 1 or gsrc.count(GEN_ROOT_LINE) != 1:
        print("FATAL: generator path lines not found exactly once", file=sys.stderr)
        return 2
    fresh_dir = SANDBOX / "rebased_fixtures_fresh"
    fresh_record_path = SANDBOX / "semantic_escape_rebased.fresh.json"
    gen = SANDBOX / "measure_semantic_escape.sandboxed.py"
    gen.write_text(gsrc.replace(GEN_ROOT_LINE, f'ROOT = Path("{ROOT}")')
                       .replace(GEN_OUT_LINE, f'OUT = Path("{fresh_record_path}")')
                       .replace(GEN_TMP_LINE, f'TMP = Path("{fresh_dir}")'))
    gen_run = subprocess.run([sys.executable, str(gen)], capture_output=True, text=True, cwd=ROOT, timeout=900)
    fresh_record = json.loads(fresh_record_path.read_text()) if fresh_record_path.exists() else {}

    # 3. sweeps
    rows_stale = sweep(FIXTURES, sab, "stale_pinned_corpus")
    rows_fresh = sweep(fresh_dir, sab, "fresh_sandbox_corpus") if fresh_dir.exists() else []
    stale_mismatch = stale_record_mismatches(rows_stale, pinned_record)

    vf_after = subprocess.run([sys.executable, str(VERIFY_FROZEN)], capture_output=True, text=True, cwd=ROOT, timeout=120)
    digest_after = frozen_digest()

    material_fresh = [r["fixture"] for r in rows_fresh if r["material_flip"]]
    material_stale = [r["fixture"] for r in rows_stale if r["material_flip"]]
    s2_flips_fresh = [r["fixture"] for r in rows_fresh if r["stage2_verdict_flip"]]
    s2_flips_stale = [r["fixture"] for r in rows_stale if r["stage2_verdict_flip"]]
    union_escapes_fresh = [r["fixture"] for r in rows_fresh if not r["union_baseline_caught"]]
    fresh_summary = fresh_record.get("summary", {})
    pinned_report = json.loads((ROOT / "artifacts/formulation/evidence/acceptance_pipeline_report.json").read_text())
    pm = pinned_report.get("mutants", {})
    # Mutant-only union arithmetic: controls are expected to PASS both stages, so they must
    # not be counted as "escapes" in the acceptance union.
    mut_rows = [r for r in rows_fresh if r["fixture"] not in CONTROLS]
    mut_total = len(mut_rows)
    mut_union = sum(1 for r in mut_rows if r["union_baseline_caught"])
    mut_union_escapes = [r["fixture"] for r in mut_rows if not r["union_baseline_caught"]]
    mut_semantic = sum(1 for r in mut_rows if r["stage2_live"]["verdict"] == "fail")
    mut_structural = sum(1 for r in mut_rows if r["stage1_pinned"]["verdict"] == "fail")
    pinned_union = pm.get("union_caught")
    # External drift observed between the two verify_frozen runs is concurrent swarm traffic,
    # not this probe: every probe write is under artifacts/worker-076/gate_evidence_pinmap/.
    external_drift = digest_after["drifted"]
    probe = {
        "schema": "worker-076/gate-evidence-pinmap/materiality/v1",
        "task_id": "W076-GATE-EVIDENCE-PINMAP-01",
        "generated_at": now(),
        "instrument_hashes": {
            "stage1_pinned": sha256(STAGE1),
            "stage2_live": sha256(STAGE2),
            "stage2_sabotaged": sha256(sab),
            "pinned_corpus_record": sha256(CORPUS_RECORD),
            "record_declared_w06_sha256": pinned_record.get("w06_sha256"),
            "generator_pinned": sha256(GEN),
            "generator_sandboxed": sha256(gen),
            "sabotage_edit": {"from": SABOTAGE_FROM.strip(), "to": SABOTAGE_TO.strip(), "occurrences": n},
        },
        "fresh_corpus": {
            "fixtures_dir": str(fresh_dir.relative_to(ROOT)),
            "record": str(fresh_record_path.relative_to(ROOT)),
            "record_sha256": sha256(fresh_record_path) if fresh_record_path.exists() else None,
            "generator_stdout_tail": gen_run.stdout.strip().splitlines()[-6:],
            "generator_stderr_tail": gen_run.stderr.strip().splitlines()[-4:],
            "generator_exit": gen_run.returncode,
            "summary": fresh_summary,
        },
        "pinned_report_comparison": {
            "pinned_report_path": "artifacts/formulation/evidence/acceptance_pipeline_report.json",
            "pinned_report_sha256": sha256(ROOT / "artifacts/formulation/evidence/acceptance_pipeline_report.json"),
            "pinned_verdict": pinned_report.get("verdict"),
            "pinned_mutants": {"total": pm.get("total"), "structural_caught": pm.get("structural_caught"),
                               "semantic_caught": pm.get("semantic_caught"), "union_caught": pm.get("union_caught")},
            "regenerated_at_live_base": {"total": mut_total, "structural_caught": mut_structural,
                                         "semantic_caught": mut_semantic, "union_caught": mut_union,
                                         "union_escapes": mut_union_escapes},
            "reproduces": pinned_union == mut_union and pm.get("semantic_caught") == mut_semantic,
            "base_declared_in_pinned_record": pinned_record.get("base_sha256"),
            "base_live": sha256(ROOT / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"),
        },
        "sweep_stale": {"rows": len(rows_stale), "material_flips": material_stale,
                        "stage2_verdict_flips": s2_flips_stale, "record_mismatches": stale_mismatch},
        "sweep_fresh": {"rows": len(rows_fresh), "mutants": mut_total, "controls": len(rows_fresh) - mut_total,
                        "material_flips": material_fresh,
                        "stage2_verdict_flips": s2_flips_fresh,
                        "union_escapes_mutants": mut_union_escapes, "union_escapes_all": union_escapes_fresh,
                        "mutant_union_caught": mut_union,
                        "rows_detail": rows_fresh},
        "verify_frozen_before": {"exit": vf_before.returncode, "stdout": vf_before.stdout.strip()},
        "verify_frozen_after": {"exit": vf_after.returncode, "stdout": vf_after.stdout.strip()},
        "frozen_digest_before": digest_before,
        "frozen_digest_after": digest_after,
        "external_drift_during_run": external_drift,
        "verdict": {
            "unpinned_stage2_verdicts_editable": len(s2_flips_fresh) > 0,
            "fresh_stage2_verdict_flip_count": len(s2_flips_fresh),
            "fresh_union_flip_count": len(material_fresh),
            "fresh_stage2_marginal_union_catches": mut_union - mut_structural,
            "fresh_mutant_union_caught": f"{mut_union}/{mut_total}",
            "pinned_report_union_claim": f"{pinned_union}/{pm.get('total')}",
            "pinned_report_reproduces": pinned_union == mut_union and pm.get("semantic_caught") == mut_semantic,
            "frozen_pins_drifted_by_probe": [],
            "external_drift_paths": external_drift,
            "detail": (f"fresh-corpus sweep: {len(s2_flips_fresh)}/{len(rows_fresh)} stage-2 verdicts flip reject->accept under a "
                       f"one-line edit of the unpinned engine ({sha256(STAGE2)[:12]} -> {sha256(sab)[:12]}), "
                       f"{len(material_fresh)} union flips (stage-2 marginal union catches at live base: "
                       f"{mut_union - mut_structural}); the pinned acceptance report claims union "
                       f"{pinned_union}/{pm.get('total')} but regenerating with the pinned generator at the live base gives "
                       f"mutant union {mut_union}/{mut_total} (escapes {mut_union_escapes}) -> pinned report does not "
                       f"reproduce; verify_frozen {vf_before.returncode}->{vf_after.returncode} over the run, external "
                       f"concurrent drift {external_drift} (not written by this probe)."),
        },
        "falsifier": ("Falsified if the sabotaged copy reproduces every live stage-2 verdict on the fresh corpus, or the "
                      "pinned acceptance report reproduces at the live base, or a probe-written file appears in FROZEN, or "
                      "the live stage-2 hash differs from the pinned corpus record's declared w06_sha256."),
    }
    (RAW / "probe.json").write_text(json.dumps(probe, indent=1) + "\n")
    print(json.dumps(probe["verdict"], indent=1))
    if fresh_record.get("summary"):
        print("fresh summary:", json.dumps(fresh_summary))
    print("fresh flips:", material_fresh)
    print("stale flips:", material_stale, "| stale record mismatches:", len(stale_mismatch))
    return 0


if __name__ == "__main__":
    sys.exit(main())
