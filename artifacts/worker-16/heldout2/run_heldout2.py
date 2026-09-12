#!/usr/bin/env python3
"""FORM-HELDOUT-08 single frozen measurement run (worker-16).

Stage A (structural):  python3 artifacts/formulation/tools/check_class_schema.py --json FIXTURE
Stage B (semantic):    python3 artifacts/worker-06/spec_conformance_audit.py FIXTURE

The manifest is hashed BEFORE any stage runs; fixture hashes are re-verified against the
manifest; controls (3 frozen canonical copies + 2 conforming + 2 negated-phrase) must be
accepted by BOTH stages or valid=false (H5).  Every mutant and control is run exactly once;
no fixture is rewritten after a verdict is observed.

Usage: python3 run_heldout2.py
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
MANIFEST = HERE / "manifest.json"
STRUCT_GATE = ROOT / "artifacts" / "formulation" / "tools" / "check_class_schema.py"
SEM_GATE = ROOT / "artifacts" / "worker-06" / "spec_conformance_audit.py"
CST = timezone(timedelta(hours=8))

# Pre-registered (written before the run) hypothesis for why neither stage covers the axis.
FAMILY_RATIONALES = {
    "excluded-set-erasure":
        "neither stage inspects genericity.excluded_set beyond presence, so erasing the Kerr exclusion leaves the generic quantifier ungrounded",
    "vacuity-status-overclaim":
        "non_vacuity.status is not read by either stage (R08/R14 check condition and witness_type only), so the membership overclaim is invisible",
    "adm-mass-erasure":
        "R05 checks only that adm_mass exists; the sign field is never compared with the positive-mass theorem",
    "data-regularity-lowered":
        "R05 checks the presence of a Sobolev index s but not its numeric threshold, so s >= 2 passes where the frozen class requires s > 5/2",
    "iplus-regularity-lowered":
        "regularity.i_plus_regularity is required only to be present; the frozen k >= 3 is never compared",
    "equation-axis-smuggle":
        "data_class.equations must exist but its content is never compared to matter=none or to the vacuum conclusion",
    "development-topology-weakened":
        "R04 checks dimension, slice, boundary and forbidden entries but not development_topology, so dropping global hyperbolicity is invisible",
    "end-structure-contradiction":
        "R04 validates slice_topology for the one-end declaration but never cross-checks topology.end_structure",
    "negation-weakened":
        "R03 requires quantifiers.negation to be non-empty; neither stage checks that it still asserts non-meagerness rather than one extendible datum",
    "formal-quantifier-kind-mismatch":
        "the semantic stage checks that binders occur in the formal sentence, not that their kinds match the ordered list; the structural stage never compares the two",
    "containment-reversal":
        "R16 only cross-checks the one_way_entailments rows; implication_ledger.extension_class_containment is not validated",
    "equivalence-inflation":
        "equivalent_rephrasings is outside both the R31 foreign-regularity path list and the semantic stage's declare_paths, so a weaker sibling statement can be declared equivalent",
    "known-obstruction-omitted":
        "conclusion.known_obstruction is not a required key in either stage, so deleting the Kerr obstruction is invisible",
    "source-status-flip":
        "R15 keys on the top-level provenance.citation_status; per-source status is not checked, so marking one source verified launders status",
    "epistemic-status-inflation":
        "both stages look only for the literal label 'theorem' (or a theorem conclusion_type), so 'conditional_theorem' without artifact_refs passes",
    "falsifier-family-mixup":
        "visibility.forbidden_falsifier is exempt from the leakage scans and is not part of R10's required content checks",
    "completeness-definition-swap":
        "WCC checks only that i_plus.role=conclusion and that completeness_definition is non-empty; the generator-completeness content is not validated",
    "visibility-negation-weakened":
        "R10 requires visibility.negation_conclusion to be present but not that it keeps the J^-(q) tail formulation",
    "schema-falsifier-erased":
        "falsifier.schema_falsifiers is not a required field in R14, so the class self-guards can be deleted",
    "genericity-ambient-space-collapse":
        "R07 requires genericity.ambient_space to be present and R25 checks only generic_set; the constraint-manifold restriction is never validated",
    "data-domain-contradiction":
        "R03 resolves D2 and checks it is non-vague, but never cross-checks the domain against data_class.matter/equations, so dropping vacuumness passes",
}


def now():
    return datetime.now(CST).isoformat(timespec="seconds")


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run_stage_a(target: Path):
    proc = subprocess.run([sys.executable, str(STRUCT_GATE), "--json", str(target)],
                          capture_output=True, text=True, timeout=300)
    try:
        rep = json.loads(proc.stdout[proc.stdout.index("{"):])
    except (ValueError, json.JSONDecodeError):
        rep = {}
    return {"exit": proc.returncode,
            "verdict": rep.get("verdict"),
            "escaped": proc.returncode == 0 and rep.get("verdict") == "pass",
            "failed_rules": rep.get("failed_rules", []),
            "failures": rep.get("failures", []),
            "stderr": proc.stderr.strip()[:200]}


def run_stage_b(target: Path):
    proc = subprocess.run([sys.executable, str(SEM_GATE), str(target)],
                          capture_output=True, text=True, timeout=300)
    try:
        rep = json.loads(proc.stdout[proc.stdout.index("{"):])
    except (ValueError, json.JSONDecodeError):
        rep = {}
    verdict = rep.get("verdict")
    escaped = (verdict == "accept") if verdict else (proc.returncode == 0)
    return {"exit": proc.returncode,
            "verdict": verdict,
            "escaped": escaped,
            "failed_rules": rep.get("failed_rules", []),
            "stderr": proc.stderr.strip()[:200]}


def main():
    if not MANIFEST.exists():
        print("manifest missing; run build_corpus.py --freeze first")
        return 2
    manifest_sha = sha(MANIFEST)          # HASHED BEFORE ANY STAGE RUN
    manifest = json.loads(MANIFEST.read_text())

    # integrity: fixture and base bytes must match the manifest recorded before the run
    entries = manifest["mutants"] + manifest["controls"]
    tampered = [e["fixture"] for e in entries
                if not (ROOT / e["path"]).exists() or sha(ROOT / e["path"]) != e["sha256"]]
    for b in manifest["bases"].values():
        if sha(ROOT / b["path"]) != b["sha256"]:
            tampered.append(b["path"])
    if tampered:
        print("TAMPERED/MISSING:", tampered)

    # controls: 3 frozen canonical copies + 4 authored controls
    controls = []
    for e in manifest["controls"]:
        a, b = run_stage_a(ROOT / e["path"]), run_stage_b(ROOT / e["path"])
        controls.append({"fixture": e["fixture"], "kind": e["kind"], "class_id": e["class_id"],
                         "stage_a": a, "stage_b": b,
                         "accepted_both": a["escaped"] and b["escaped"]})
    for rel in manifest["frozen_canonical_controls"]:
        a, b = run_stage_a(ROOT / rel), run_stage_b(ROOT / rel)
        controls.append({"fixture": Path(rel).name, "kind": "frozen-canonical", "path": rel,
                         "stage_a": a, "stage_b": b,
                         "accepted_both": a["escaped"] and b["escaped"]})
    controls_ok = all(c["accepted_both"] for c in controls) and not tampered

    # mutants: exactly one run each
    results = []
    for e in manifest["mutants"]:
        a, b = run_stage_a(ROOT / e["path"]), run_stage_b(ROOT / e["path"])
        results.append({
            "fixture": e["fixture"], "family": e["family"], "rephrased": e["rephrased"],
            "class_id": e["class_id"], "mutation_id": e["mutation_id"],
            "stage_a": a, "stage_b": b,
            "structural_escape": a["escaped"], "semantic_escape": b["escaped"],
            "union_escape": a["escaped"] and b["escaped"],
        })
    n = len(results)
    esc = [r for r in results if r["union_escape"]]
    by_family = {}
    for r in esc:
        by_family.setdefault(r["family"], []).append(r)
    escape_families = []
    for fam in sorted(by_family):
        rows = by_family[fam]
        escape_families.append({
            "family": fam,
            "count": len(rows),
            "example_name": rows[0]["fixture"],
            "one_sentence_reason": FAMILY_RATIONALES.get(fam, "no rule in either stage inspects this axis"),
            "fixtures": [r["fixture"] for r in rows],
        })
    caught_families = sorted({r["family"] for r in results} - set(by_family))

    # live-path drift observation (excluded from the validity decision)
    live = []
    for rel in manifest.get("live_canonical_controls", []):
        a, b = run_stage_a(ROOT / rel), run_stage_b(ROOT / rel)
        live.append({"path": rel, "sha256_now": sha(ROOT / rel),
                     "frozen_sha256": manifest["bases"].get(
                         {v["live_path"]: k for k, v in manifest["bases"].items()}.get(rel, ""), {}
                     ).get("sha256"),
                     "stage_a": a, "stage_b": b,
                     "accepted_both": a["escaped"] and b["escaped"]})

    report = {
        "corpus_id": "FORM-HELDOUT-08",
        "assignment": manifest["assignment"],
        "task_id": "FORM-HELDOUT-08",
        "worker": "worker-16",
        "actor": "deepseek-flash-16",
        "generated_at": now(),
        "manifest_sha256_before_run": manifest_sha,
        "valid": bool(controls_ok),
        "invalid_reasons": ([] if controls_ok else
                            (["tampered or missing fixtures: " + ", ".join(tampered)] if tampered else [])
                            + [f"control {c['fixture']} rejected by a stage" for c in controls
                               if not c["accepted_both"]]),
        "frozen_revision_binding": manifest["frozen_revision_binding"],
        "stages": {"structural": {"gate": "artifacts/formulation/tools/check_class_schema.py",
                                  "sha256": sha(STRUCT_GATE)},
                   "semantic": {"gate": "artifacts/worker-06/spec_conformance_audit.py",
                                "sha256": sha(SEM_GATE)}},
        "corpus": {"mutants": n,
                   "families": len({r["family"] for r in results}),
                   "rephrased": sum(1 for r in results if r["rephrased"]),
                   "controls": len(controls)},
        "aggregates": {
            "structural_escape": round(sum(1 for r in results if r["structural_escape"]) / n, 4),
            "semantic_escape": round(sum(1 for r in results if r["semantic_escape"]) / n, 4),
            "union_escape": round(len(esc) / n, 4),
            "structural_caught": n - sum(1 for r in results if r["structural_escape"]),
            "semantic_caught": n - sum(1 for r in results if r["semantic_escape"]),
            "union_caught": n - len(esc),
        },
        "escape_families": escape_families,
        "caught_families": caught_families,
        "controls_detail": controls,
        "live_canonical_drift_check": live,
        "measurement_rule": "union escape = accepted by BOTH stages; controls (3 frozen canonical + 2 conforming + 2 negated-phrase) must be accepted by both stages or valid=false",
        "caveat": ("the corpus was authored after the report of FORM-HELDOUT-07; R26-R31 were "
                   "derived from that report's family list, so these numbers are out-of-sample "
                   "only for the axes that R26-R31 do not already cover. The live canonical paths "
                   "drifted after FROZEN rev19 and are NOT used as bases; the frozen rev13 bytes "
                   "were taken from the verified worker-11 snapshot."),
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    (HERE / "raw_verdicts.json").write_text(json.dumps(
        {"manifest_sha256_before_run": manifest_sha, "controls": controls,
         "results": results, "live_canonical_drift_check": live}, indent=2) + "\n")
    a = report["aggregates"]
    print(f"valid={report['valid']} | structural escape {a['structural_escape']} | "
          f"semantic escape {a['semantic_escape']} | union escape {a['union_escape']}")
    print(f"controls ok: {controls_ok} | tampered: {tampered}")
    print("escape families:", [(f["family"], f["count"]) for f in escape_families])
    print("caught families:", caught_families)
    return 0 if report["valid"] else 5


if __name__ == "__main__":
    sys.exit(main())
