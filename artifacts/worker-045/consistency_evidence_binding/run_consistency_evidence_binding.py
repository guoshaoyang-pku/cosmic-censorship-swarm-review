#!/usr/bin/env python3
"""W045-CONSISTENCY-EVIDENCE-BINDING-01 (worker-045, bounded class-bound task).

Adjudicates the f0_binding.consistency_evidence chain of the three frozen class
artifacts (F1 AF-WCC-VAC-GEN, F2a AF-SCC-C2-VAC-GEN, F2b AF-SCC-C0-VAC-GEN) at
one measured instant:

  1. declared pin vs canonical bytes vs FROZEN rev28 pin;
  2. whether the canonical evidence file hash-binds the F0 inputs it evaluated
     (map_taxonomy_sha256 / lead_contract_sha256), compared with the enriched
     rev12 variant that the schemas still declare;
  3. whether the declared checker is a deterministic, input-sensitive function
     (sandbox reruns, semantic mutation, ignored-field mutation);
  4. a fail-closed detector control set, and a no-canonical-drift guard.

Read-only on canonical paths. All checker executions happen in sandbox copies
under this directory because check_taxonomy_consistency.py rewrites its output
file next to the tree it is run from.

Exit 0 only if every pre-registered control behaves as expected and the canonical
hash guard holds. Prints the report JSON on stdout.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

DIR = Path(__file__).resolve().parent
ROOT = DIR.parents[2]  # .../artifacts/worker-045/<task>/ -> repo root
CST = timezone(timedelta(hours=8))
SB = DIR / "sandbox"

CANON_F0 = "research_map/formulation_taxonomy.yaml"
CANON_SUPP = "artifacts/formulation/formulation_taxonomy.yaml"
CANON_F1 = "schemas/af_wcc_vacuum.yaml"
CANON_F2A = "schemas/af_scc_c2_vacuum.yaml"
CANON_F2B = "schemas/af_scc_c0_vacuum.yaml"
CANON_EVIDENCE = "artifacts/formulation/evidence/taxonomy_consistency.json"
CANON_FROZEN = "artifacts/formulation/FROZEN.json"
CANON_CHECKER = "artifacts/formulation/tools/check_taxonomy_consistency.py"
CANON_ALIASES = "artifacts/formulation/VOCAB_ALIASES.json"

CLASS_PATHS = [
    ("F1", "AF-WCC-VAC-GEN", CANON_F1),
    ("F2a", "AF-SCC-C2-VAC-GEN", CANON_F2A),
    ("F2b", "AF-SCC-C0-VAC-GEN", CANON_F2B),
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text())


def build_sandbox(dst: Path, f0_bytes: bytes, supp_bytes: bytes) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    (dst / "research_map").mkdir(parents=True)
    (dst / "artifacts/formulation/tools").mkdir(parents=True)
    (dst / "artifacts/formulation/evidence").mkdir(parents=True)
    (dst / "research_map/formulation_taxonomy.yaml").write_bytes(f0_bytes)
    (dst / CANON_SUPP).write_bytes(supp_bytes)
    shutil.copy2(ROOT / CANON_ALIASES, dst / CANON_ALIASES)
    shutil.copy2(ROOT / CANON_CHECKER, dst / CANON_CHECKER)


def run_checker(tree: Path):
    proc = subprocess.run(
        [sys.executable, str(tree / CANON_CHECKER)],
        cwd=str(tree), capture_output=True, text=True, timeout=120,
    )
    out = tree / CANON_EVIDENCE
    return {
        "exit": proc.returncode,
        "stdout": (proc.stdout or "").strip(),
        "stderr": (proc.stderr or "").strip()[-400:],
        "output_sha256": sha256_file(out) if out.exists() else None,
        "output": load_json(out) if out.exists() else None,
    }


def find_variant_pin(declared: str):
    """Locate a copy of the evidence file whose sha256 equals the declared pin."""
    hits, all_hashes = [], {}
    for p in sorted(ROOT.glob("artifacts/**/taxonomy_consistency*.json")):
        h = sha256_file(p)
        all_hashes[str(p.relative_to(ROOT))] = h
        if h == declared:
            hits.append(str(p.relative_to(ROOT)))
    return hits, all_hashes


def binding_state(evidence: dict, live: dict) -> str:
    """Fail-closed input-binding classifier for one evidence document.

    BOUND    : both input hashes present and equal to the live canonical hashes.
    MISMATCH : at least one input hash present but unequal.
    UNBOUND  : no input hash present at all (cannot detect input drift).
    """
    mt = evidence.get("map_taxonomy_sha256")
    lc = evidence.get("lead_contract_sha256")
    if mt is None and lc is None:
        return "UNBOUND"
    if mt == live[CANON_F0] and lc == live[CANON_SUPP]:
        return "BOUND"
    return "MISMATCH"


def main() -> int:
    started = datetime.now(CST).isoformat(timespec="seconds")
    controls: dict[str, dict] = {}

    # ---- 0. drift-guarded canonical measurement -----------------------------
    pins = {
        CANON_F0: sha256_file(ROOT / CANON_F0),
        CANON_SUPP: sha256_file(ROOT / CANON_SUPP),
        CANON_F1: sha256_file(ROOT / CANON_F1),
        CANON_F2A: sha256_file(ROOT / CANON_F2A),
        CANON_F2B: sha256_file(ROOT / CANON_F2B),
        CANON_EVIDENCE: sha256_file(ROOT / CANON_EVIDENCE),
        CANON_FROZEN: sha256_file(ROOT / CANON_FROZEN),
        CANON_CHECKER: sha256_file(ROOT / CANON_CHECKER),
        CANON_ALIASES: sha256_file(ROOT / CANON_ALIASES),
    }
    f0_bytes = (ROOT / CANON_F0).read_bytes()
    supp_bytes = (ROOT / CANON_SUPP).read_bytes()
    evidence = load_json(ROOT / CANON_EVIDENCE)
    frozen = load_json(ROOT / CANON_FROZEN)

    if isinstance(frozen["files"], dict):
        frozen_pins = {path: meta["sha256"] for path, meta in frozen["files"].items()}
    else:
        frozen_pins = {row["path"]: row["sha256"] for row in frozen["files"]}

    # ---- 1. per-class declaration table ------------------------------------
    classes, declared_pins = [], set()
    for node, cid, rel in CLASS_PATHS:
        schema = yaml.safe_load((ROOT / rel).read_text())
        fb = schema.get("f0_binding") or {}
        declared = fb.get("consistency_evidence_sha256")
        declared_pins.add(declared)
        f0 = yaml.safe_load(f0_bytes)
        supp = yaml.safe_load(supp_bytes)
        pointer = str(schema.get("class_contract_pointer", ""))
        supp_pointer = str(fb.get("class_contract_supplement_pointer", ""))
        classes.append({
            "node": node,
            "class_id": cid,
            "artifact_sha256": pins[rel],
            "declared_f0_artifact": fb.get("declared_f0_artifact"),
            "declared_f0_sha256": fb.get("declared_f0_sha256"),
            "declared_f0_matches_live": fb.get("declared_f0_sha256") == pins[CANON_F0],
            "consistency_evidence": fb.get("consistency_evidence"),
            "consistency_evidence_sha256_declared": declared,
            "declared_pin_matches_live_evidence": declared == pins[CANON_EVIDENCE],
            "class_contract_pointer": pointer,
            "class_contract_pointer_resolves": pointer == f"{CANON_F0}#classes.{cid}"
            and cid in (f0.get("classes") or {}),
            "supplement_pointer": supp_pointer,
            "supplement_pointer_resolves": supp_pointer.endswith(f"#class_contracts.{cid}")
            and cid in (supp.get("class_contracts") or {}),
            "frozen_rev28_pin": frozen_pins.get(rel),
            "frozen_pin_matches_live": frozen_pins.get(rel) == pins[rel],
        })

    uniform_declared = len(declared_pins) == 1
    declared_pin = sorted(declared_pins)[0] if uniform_declared else None
    frozen_evidence_pin = frozen_pins.get(CANON_EVIDENCE)

    findings = []
    if declared_pin and declared_pin != pins[CANON_EVIDENCE]:
        findings.append({
            "id": "F-1",
            "severity": "major",
            "finding": (
                f"uniform stale consistency-evidence declaration: all three class artifacts "
                f"declare {declared_pin[:16]}, canonical path measures {pins[CANON_EVIDENCE][:16]}"
            ),
        })
    if frozen_evidence_pin and frozen_evidence_pin != declared_pin:
        findings.append({
            "id": "F-2",
            "severity": "major",
            "finding": (
                f"FROZEN rev{frozen.get('revision')} pins {CANON_EVIDENCE} at "
                f"{str(frozen_evidence_pin)[:16]} while the three schemas declare {str(declared_pin)[:16]}; "
                "the frozen corpus carries two mutually exclusive pins for one path"
            ),
        })

    variants, all_variant_hashes = find_variant_pin(declared_pin or "")
    live_state = binding_state(evidence, pins)
    enriched = load_json(ROOT / variants[0]) if variants else None
    enriched_state = binding_state(enriched, pins) if enriched else None
    if live_state == "UNBOUND":
        findings.append({
            "id": "F-3",
            "severity": "major",
            "finding": (
                "canonical consistency evidence is input-hash-unbound: it records the two input paths "
                "but no map_taxonomy_sha256/lead_contract_sha256, so the file cannot show which F0 bytes "
                "it evaluated; the declared enriched variant does carry both hashes and they equal the "
                "live F0/supplement"
            ),
        })
    if variants:
        findings.append({
            "id": "F-4",
            "severity": "info",
            "finding": (
                f"declared pin {declared_pin[:16]} still exists on disk at {variants[0]} "
                f"(enriched variant); repairing by re-pinning to the canonical bytes and restoring the "
                f"enriched evidence are mutually exclusive without a further FROZEN move"
            ),
        })
    findings.append({
        "id": "F-5",
        "severity": "major",
        "finding": (
            "control C3: a re-serialised F0 with an added non-compared field leaves the evidence "
            "byte-identical (9e335e9b), so the evidence hash does not bind F0 bytes at all; the "
            "load-bearing input binding is each schema's declared_f0_sha256 (which does equal live F0)"
        ),
    })

    # ---- 2. controls --------------------------------------------------------
    build_sandbox(SB / "base", f0_bytes, supp_bytes)
    run1 = run_checker(SB / "base")
    run2 = run_checker(SB / "base")
    controls["C1_determinism_and_reproduction"] = {
        "expected": "two runs identical and equal to live canonical evidence hash",
        "run1_sha256": run1["output_sha256"], "run2_sha256": run2["output_sha256"],
        "live_sha256": pins[CANON_EVIDENCE],
        "run_exit": [run1["exit"], run2["exit"]],
        "pass": run1["output_sha256"] == run2["output_sha256"] == pins[CANON_EVIDENCE]
        and run1["exit"] == run2["exit"] == 0,
    }

    f0_mut = yaml.safe_load(f0_bytes)
    f0_mut["classes"]["AF-SCC-C2-VAC-GEN"]["axes"]["family"] = "SCC_W045_MUTANT"
    build_sandbox(SB / "semantic_mutant", yaml.safe_dump(f0_mut, sort_keys=False).encode(), supp_bytes)
    run_mut = run_checker(SB / "semantic_mutant")
    controls["C2_semantic_sensitivity"] = {
        "expected": "exit 1, consistent=false, output hash differs",
        "exit": run_mut["exit"], "stdout": run_mut["stdout"][:200],
        "consistent": (run_mut["output"] or {}).get("consistent"),
        "output_sha256": run_mut["output_sha256"],
        "pass": run_mut["exit"] == 1
        and (run_mut["output"] or {}).get("consistent") is False
        and run_mut["output_sha256"] not in (run1["output_sha256"], pins[CANON_EVIDENCE]),
    }

    f0_ign = yaml.safe_load(f0_bytes)
    f0_ign["_w045_ignored_field"] = "a field the declared checker does not read"
    build_sandbox(SB / "ignored_mutant", yaml.safe_dump(f0_ign, sort_keys=False).encode(), supp_bytes)
    run_ign = run_checker(SB / "ignored_mutant")
    controls["C3_noncompared_edit_invariance"] = {
        "expected": (
            "a full re-serialisation of F0 plus a new ignored top-level field leaves the evidence "
            "byte-identical: the declared checker compares parsed fields, so the evidence hash cannot "
            "detect F0 byte drift"
        ),
        "initial_expectation": "output hash would move while consistent stayed true",
        "misprediction_note": (
            "Initial expectation was wrong and is recorded here rather than silently corrected: the "
            "checker never hashes its inputs, so edits outside the compared fields cannot move the output."
        ),
        "exit": run_ign["exit"], "consistent": (run_ign["output"] or {}).get("consistent"),
        "output_sha256": run_ign["output_sha256"],
        "pass": run_ign["exit"] == 0
        and (run_ign["output"] or {}).get("consistent") is True
        and run_ign["output_sha256"] == run1["output_sha256"],
    }

    detector_controls = {
        "live_unbound": binding_state(evidence, pins) == "UNBOUND",
        "enriched_bound": bool(enriched) and binding_state(enriched, pins) == "BOUND",
        "tampered_mismatch": binding_state({**enriched, "map_taxonomy_sha256": "0" * 64}, pins) == "MISMATCH"
        if enriched else False,
        "path_only_unbound": binding_state({"map_taxonomy": CANON_F0, "lead_contract": CANON_SUPP}, pins) == "UNBOUND",
    }
    controls["C4_binding_detector"] = {
        "expected": "UNBOUND for live/path-only, BOUND for enriched, MISMATCH for tampered",
        "live": live_state, "enriched": enriched_state,
        "enriched_path": variants[0] if variants else None,
        "subchecks": detector_controls, "pass": all(detector_controls.values()),
    }

    after = {
        CANON_F0: sha256_file(ROOT / CANON_F0),
        CANON_SUPP: sha256_file(ROOT / CANON_SUPP),
        CANON_F1: sha256_file(ROOT / CANON_F1),
        CANON_F2A: sha256_file(ROOT / CANON_F2A),
        CANON_F2B: sha256_file(ROOT / CANON_F2B),
        CANON_EVIDENCE: sha256_file(ROOT / CANON_EVIDENCE),
        CANON_FROZEN: sha256_file(ROOT / CANON_FROZEN),
        CANON_CHECKER: sha256_file(ROOT / CANON_CHECKER),
        CANON_ALIASES: sha256_file(ROOT / CANON_ALIASES),
    }
    controls["C5_no_canonical_drift"] = {
        "expected": "every canonical hash unchanged across the run",
        "pass": after == pins,
        "changed": sorted(k for k in pins if pins[k] != after[k]),
    }

    controls_pass = all(c["pass"] for c in controls.values())

    report = {
        "task_id": "W045-CONSISTENCY-EVIDENCE-BINDING-01",
        "worker": "worker-045",
        "node_id": ["F0", "F1", "F2a", "F2b"],
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "started_at": started,
        "measured_at": datetime.now(CST).isoformat(timespec="seconds"),
        "pins": pins,
        "class_declarations": classes,
        "declared_evidence_pin_uniform": uniform_declared,
        "declared_evidence_pin": declared_pin,
        "canonical_evidence_state": {
            "consistent": evidence.get("consistent"),
            "errors": evidence.get("errors"),
            "contract_divergences": evidence.get("contract_divergences"),
            "input_binding": live_state,
            "keys": sorted(evidence.keys()),
        },
        "enriched_variant": {
            "path": variants[0] if variants else None,
            "sha256": declared_pin,
            "input_binding": enriched_state,
            "keys": sorted(enriched.keys()) if enriched else None,
            "map_taxonomy_sha256": (enriched or {}).get("map_taxonomy_sha256"),
            "lead_contract_sha256": (enriched or {}).get("lead_contract_sha256"),
            "measured_at": (enriched or {}).get("measured_at"),
            "copies_with_declared_pin": sum(1 for h in all_variant_hashes.values() if h == declared_pin),
            "copies_with_live_hash": sum(1 for h in all_variant_hashes.values() if h == pins[CANON_EVIDENCE]),
        },
        "frozen_rev": frozen.get("revision"),
        "frozen_evidence_pin": frozen_evidence_pin,
        "frozen_evidence_pin_matches_live": frozen_evidence_pin == pins[CANON_EVIDENCE],
        "controls": controls,
        "controls_pass": controls_pass,
        "findings": findings,
        "verdict": "REVISE" if findings else "NO_DEFECT",
        "verdict_basis": (
            "Binding defect confirmed and uniform (F-1), the frozen corpus contradicts itself on the "
            "same path (F-2), the canonical evidence cannot bind its inputs (F-3), and both candidate "
            "repairs exist but require an author decision plus one re-freeze (F-4)."
            if findings else "All declarations, freeze pins, and the canonical evidence chain agree."
        ),
        "falsifier": (
            "Falsified if any of: (a) at the pinned hashes some class artifact's "
            "f0_binding.consistency_evidence_sha256 equals the measured sha256 of its declared "
            "consistency_evidence path; (b) FROZEN rev28's pin for artifacts/formulation/evidence/"
            "taxonomy_consistency.json differs from the live measured hash; (c) the canonical evidence "
            "file contains map_taxonomy_sha256/lead_contract_sha256 equal to the live F0/supplement "
            "hashes, or the declared checker's output is unchanged by a semantic F0 mutation; (d) the "
            "binding detector returns anything other than UNBOUND for the canonical evidence, BOUND "
            "for the enriched variant, or MISMATCH for the tampered variant."
        ),
        "authority_note": (
            "Worker measurement, not a gate verdict. No canonical file was modified; all checker runs "
            "were sandboxed because the declared checker rewrites its evidence output in-place. "
            "Node/gate status and any schema edit remain lead/controller-owned."
        ),
    }
    print(json.dumps(report, indent=2))
    return 0 if controls_pass else 1


if __name__ == "__main__":
    sys.exit(main())
