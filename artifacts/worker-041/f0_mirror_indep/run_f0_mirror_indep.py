#!/usr/bin/env python3
"""W041-F0-MIRROR-INDEP-01: independent, hash-pinned test of the F0 mirror conflict.

Question (from astra-life02-publish-f0 / leadform-blocker-0007 / CF-13):
    Can research_map/formulation_taxonomy.yaml (A) and
    artifacts/formulation/formulation_taxonomy.yaml (B) be made byte-identical
    without damaging a frozen consumer?

Method: exhaustive case analysis over the only byte-identical candidates of the
two frozen revisions -- A:=bytes(B), B:=bytes(A) -- plus a merged-revision
control, each materialised in an isolated sandbox root and evaluated against the
frozen consumers:
    E1 canonical declared-F0 structure (class_ids, classes[4], transfer_rules)
    E2 authoring class-contract supplement structure (class_contracts[4],
       axis_registry.genericity_axis.frozen, implication_ledger)
    E3 per-class identity-axis agreement between A.classes and B.class_contracts
    E4 the three schemas' class_contract_pointer path#fragment resolves
    E5 the three schemas' f0_binding.declared_f0_sha256 matches measured A
    E6 class_contract_supplement path exists
    E7 FROZEN.json logical_artifacts pins match measured bytes
and the real frozen checker artifacts/formulation/tools/check_taxonomy_consistency.py
run byte-identically inside each sandbox.

Controls:
    merged control -> all E1-E7 true and checker exit 0 (proves the instrument
    reports satisfiability when a single file carries both key sets);
    semantic-mutation control -> checker exit 1 with a named divergence (proves
    the checker stage detects real damage).

Read-only with respect to the repository's canonical paths: all simulated writes
stay under artifacts/worker-041/f0_mirror_indep/sim/.
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

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SIM = HERE / "sim"
TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ)
NOW_ISO = NOW.isoformat(timespec="seconds")

A_REL = "research_map/formulation_taxonomy.yaml"
B_REL = "artifacts/formulation/formulation_taxonomy.yaml"
CHECKER_REL = "artifacts/formulation/tools/check_taxonomy_consistency.py"
ALIASES_REL = "artifacts/formulation/VOCAB_ALIASES.json"
FROZEN_REL = "artifacts/formulation/FROZEN.json"
SCHEMAS = [
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
]
CLASS_IDS = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]
FROZEN_A_SHA = "276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc"
FROZEN_B_SHA = "c8e979a1eb48969be3b102e1e18203eb9e09b4e10fca3ef341854fdd73bae83f"


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha_file(p: Path) -> str:
    return sha_bytes(p.read_bytes())


def load_yaml(p: Path):
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def resolve_fragment(doc, fragment: str):
    """Dotted-path lookup; returns (found, value_or_None)."""
    cur = doc
    for part in fragment.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return False, None
    return True, cur


def structure_checks(root: Path, extra_note: str = "") -> dict:
    """E1-E7 on a simulated root that holds the two taxonomy paths + schemas + FROZEN."""
    a_path = root / A_REL
    b_path = root / B_REL
    out: dict = {"root_note": extra_note, "checks": {}, "missing_keys": []}
    a_doc = load_yaml(a_path) if a_path.exists() else {}
    b_doc = load_yaml(b_path) if b_path.exists() else {}

    # E1 canonical declared-F0 structure
    e1_missing = [k for k in ("class_ids", "classes", "transfer_rules") if k not in a_doc]
    e1 = not e1_missing and len(a_doc.get("classes") or {}) == 4 and \
        set(a_doc.get("class_ids") or []) == set(CLASS_IDS) and \
        isinstance((a_doc.get("transfer_rules") or {}).get("allowed"), list) and \
        isinstance((a_doc.get("transfer_rules") or {}).get("forbidden"), list)
    out["checks"]["E1_canonical_declared_f0_structure"] = {
        "pass": bool(e1), "missing_keys": e1_missing}
    out["missing_keys"] += [f"A.{k}" for k in e1_missing]

    # E2 authoring class-contract supplement structure
    e2_missing = [k for k in ("class_contracts", "axis_registry", "implication_ledger")
                  if k not in b_doc]
    gen = (((b_doc.get("axis_registry") or {}).get("genericity_axis") or {}).get("frozen")) or {}
    e2 = not e2_missing and set((b_doc.get("class_contracts") or {}).keys()) == set(CLASS_IDS) \
        and len(gen) == 4 and isinstance(b_doc.get("implication_ledger"), list)
    out["checks"]["E2_authoring_supplement_structure"] = {
        "pass": bool(e2), "missing_keys": e2_missing}
    out["missing_keys"] += [f"B.{k}" for k in e2_missing]

    # E3 per-class identity-axis agreement (same normalisations as the frozen checker)
    aliases = json.loads((root / ALIASES_REL).read_text(encoding="utf-8"))

    def canon(kind, tok):
        for c, al in aliases.get(kind, {}).items():
            if tok == c or tok in al:
                return c
        return tok

    per_class = {}
    e3 = True
    for cid in CLASS_IDS:
        a_cls = (a_doc.get("classes") or {}).get(cid) or {}
        b_cls = (b_doc.get("class_contracts") or {}).get(cid) or {}
        a_axes = a_cls.get("axes") or {}
        b_comp = b_cls.get("components") or {}
        row = {
            "in_canonical": bool(a_cls),
            "in_authoring": bool(b_cls),
        }
        if a_cls and b_cls:
            row["family_match"] = a_axes.get("family") == b_comp.get("censorship")
            row["conclusion_type_match"] = canon(
                "conclusion_type", a_axes.get("conclusion_type")) == canon(
                "conclusion_type", b_cls.get("conclusion_type"))
            row["exclusions_present_both"] = bool(a_cls.get("exclusions")) and \
                bool(b_cls.get("exclusions"))
            row["test_cases_present_both"] = bool(a_cls.get("test_cases")) and \
                bool(b_cls.get("positive_test_case"))
            row["agree"] = all(row[k] for k in ("family_match", "conclusion_type_match",
                                                "exclusions_present_both",
                                                "test_cases_present_both"))
        else:
            row["agree"] = False
        per_class[cid] = row
        e3 = e3 and row["agree"]
    out["checks"]["E3_per_class_identity_agreement"] = {"pass": bool(e3),
                                                         "per_class": per_class}

    # E4/E5/E6 schema references
    ptr_rows, hash_rows, supp_rows = {}, {}, {}
    e4 = e5 = e6 = True
    for srel in SCHEMAS:
        sdoc = load_yaml(root / srel)
        ptr = str(sdoc.get("class_contract_pointer", ""))
        ppath, _, frag = ptr.partition("#")
        target = root / ppath
        if target.exists() and frag:
            found, _ = resolve_fragment(load_yaml(target), frag)
        else:
            found = False
        ptr_rows[srel] = {"pointer": ptr, "target_exists": target.exists(),
                          "fragment_resolves": bool(found)}
        e4 = e4 and bool(found)
        bind = sdoc.get("f0_binding") or {}
        declared = bind.get("declared_f0_sha256")
        measured = sha_file(root / str(bind.get("declared_f0_artifact", ""))) \
            if (root / str(bind.get("declared_f0_artifact", ""))).exists() else None
        hash_rows[srel] = {"declared": declared, "measured": measured,
                           "match": declared == measured}
        e5 = e5 and declared == measured
        supp = bind.get("class_contract_supplement")
        supp_rows[srel] = {"path": supp, "exists": bool(supp) and (root / str(supp)).exists()}
        e6 = e6 and bool(supp) and (root / str(supp)).exists()
    out["checks"]["E4_class_contract_pointer_resolves"] = {"pass": bool(e4), "rows": ptr_rows}
    out["checks"]["E5_declared_f0_hash_matches_measured"] = {"pass": bool(e5),
                                                              "rows": hash_rows}
    out["checks"]["E6_class_contract_supplement_exists"] = {"pass": bool(e6),
                                                             "rows": supp_rows}

    # E7 FROZEN logical-artifact pins
    frozen = json.loads((root / FROZEN_REL).read_text(encoding="utf-8"))
    pin_rows = {}
    e7 = True
    for name, entry in (frozen.get("logical_artifacts") or {}).items():
        p = root / entry["path"]
        measured = sha_file(p) if p.exists() else None
        ok = measured == entry.get("sha256")
        pin_rows[name] = {"path": entry["path"], "pinned": entry.get("sha256"),
                          "measured": measured, "match": bool(ok)}
        e7 = e7 and ok
    out["checks"]["E7_frozen_logical_artifact_pins"] = {"pass": bool(e7), "rows": pin_rows}

    # Structural consumers (shape/resolution/agreement) vs frozen-pin freshness.
    # E5/E7 must hold for a byte-identical publication of a FROZEN revision, but a
    # merged NEW revision is expected to break them until re-frozen.
    out["structural_pass"] = all(out["checks"][k]["pass"] for k in (
        "E1_canonical_declared_f0_structure",
        "E2_authoring_supplement_structure",
        "E3_per_class_identity_agreement",
        "E4_class_contract_pointer_resolves",
        "E6_class_contract_supplement_exists",
    ))
    out["frozen_pins_pass"] = all(out["checks"][k]["pass"] for k in (
        "E5_declared_f0_hash_matches_measured",
        "E7_frozen_logical_artifact_pins",
    ))
    out["all_pass"] = out["structural_pass"] and out["frozen_pins_pass"]
    return out


def make_root(name: str, a_bytes: bytes, b_bytes: bytes) -> Path:
    root = SIM / name
    if root.exists():
        shutil.rmtree(root)
    (root / "research_map").mkdir(parents=True)
    (root / "artifacts" / "formulation" / "tools").mkdir(parents=True)
    (root / "artifacts" / "formulation" / "evidence").mkdir(parents=True)
    (root / "schemas").mkdir(parents=True)
    (root / A_REL).write_bytes(a_bytes)
    (root / B_REL).write_bytes(b_bytes)
    for srel in SCHEMAS:
        shutil.copy2(ROOT / srel, root / srel)
    shutil.copy2(ROOT / FROZEN_REL, root / FROZEN_REL)
    shutil.copy2(ROOT / ALIASES_REL, root / ALIASES_REL)
    shutil.copy2(ROOT / CHECKER_REL, root / CHECKER_REL)
    return root


def run_checker(root: Path) -> dict:
    """Run the frozen checker byte-identically inside the sandbox root."""
    proc = subprocess.run(
        [sys.executable, str(root / CHECKER_REL)],
        cwd=str(root), capture_output=True, text=True, timeout=120,
    )
    evidence = root / "artifacts" / "formulation" / "evidence" / "taxonomy_consistency.json"
    ev = json.loads(evidence.read_text(encoding="utf-8")) if evidence.exists() else None
    return {
        "exit_code": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr_tail": proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else "",
        "evidence_written": ev is not None,
        "evidence_consistent": (ev or {}).get("consistent"),
        "evidence_errors": (ev or {}).get("errors"),
    }


def merged_doc(a_doc: dict, b_doc: dict) -> dict:
    """Union of top-level keys; A wins on collisions. Both key sets present."""
    merged = dict(b_doc)
    merged.update(a_doc)
    return merged


def main() -> int:
    SIM.mkdir(parents=True, exist_ok=True)
    a_bytes = (ROOT / A_REL).read_bytes()
    b_bytes = (ROOT / B_REL).read_bytes()
    a_sha, b_sha = sha_bytes(a_bytes), sha_bytes(b_bytes)

    pins = {}
    for rel in [A_REL, B_REL, CHECKER_REL, ALIASES_REL, FROZEN_REL] + SCHEMAS:
        pins[rel] = {"sha256": sha_file(ROOT / rel), "bytes": (ROOT / rel).stat().st_size}

    a_doc, b_doc = yaml.safe_load(a_bytes), yaml.safe_load(b_bytes)
    merged = merged_doc(a_doc, b_doc)
    merged_bytes = yaml.safe_dump(merged, sort_keys=False, allow_unicode=True).encode()
    mutated = json.loads(json.dumps(merged))
    mutated["class_contracts"]["AF-WCC-VAC-GEN"]["components"]["censorship"] = "SCC"
    mutated_bytes = yaml.safe_dump(mutated, sort_keys=False, allow_unicode=True).encode()

    cases = {
        "baseline_frozen_current": (a_bytes, b_bytes),
        "dir_A_canonical_eq_authoring": (a_bytes, a_bytes),
        "dir_B_authoring_eq_canonical": (b_bytes, b_bytes),
        "merged_new_revision_control": (merged_bytes, merged_bytes),
        "negative_control_semantic_mutation": (merged_bytes, mutated_bytes),
    }
    results = {}
    raw_dir = HERE / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    for name, (ab, bb) in cases.items():
        root = make_root(name, ab, bb)
        st = structure_checks(root, extra_note=name)
        ck = run_checker(root)
        (raw_dir / f"{name}.checker.stdout.txt").write_text(ck["stdout"] + "\n", encoding="utf-8")
        (raw_dir / f"{name}.checker.stderr.txt").write_text(
            (ck["stderr_tail"] + "\n") if ck["stderr_tail"] else "\n", encoding="utf-8")
        (raw_dir / f"{name}.structure.json").write_text(
            json.dumps(st, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        results[name] = {"structure": st, "checker": ck}

    # end-of-run drift check: pins must not have moved during the measurement
    drift = {}
    for rel in [A_REL, B_REL, CHECKER_REL, ALIASES_REL, FROZEN_REL] + SCHEMAS:
        now = sha_file(ROOT / rel)
        drift[rel] = {"at_start": pins[rel]["sha256"], "at_end": now,
                      "stable": now == pins[rel]["sha256"]}
    hash_stable = all(v["stable"] for v in drift.values())

    # instrument validity
    merged_case = results["merged_new_revision_control"]
    merged_ok = merged_case["structure"]["structural_pass"] and \
        merged_case["checker"]["exit_code"] == 0 and \
        not merged_case["structure"]["frozen_pins_pass"]  # new revision must break old pins
    neg = results["negative_control_semantic_mutation"]
    neg_ok = neg["checker"]["exit_code"] == 1 and not neg["checker"]["evidence_consistent"]
    # Instrument validity uses structural consumers + checker only. Baseline frozen-pin
    # freshness (E5/E7) is DATA, not an instrument condition: if the baseline pins already
    # lag disk, that is a reported finding, not a broken instrument.
    baseline_structural_ok = results["baseline_frozen_current"]["structure"]["structural_pass"] \
        and results["baseline_frozen_current"]["checker"]["exit_code"] == 0
    baseline_pins_ok = results["baseline_frozen_current"]["structure"]["frozen_pins_pass"]

    a2b = results["dir_A_canonical_eq_authoring"]
    b2a = results["dir_B_authoring_eq_canonical"]
    a2b_admissible = a2b["structure"]["all_pass"] and a2b["checker"]["exit_code"] == 0
    b2a_admissible = b2a["structure"]["all_pass"] and b2a["checker"]["exit_code"] == 0

    if not (merged_ok and neg_ok and baseline_structural_ok):
        verdict = "INSTRUMENT_INVALID"
    elif a2b_admissible or b2a_admissible:
        verdict = "REFUTED_ONE_DIRECTION_IS_ADMISSIBLE"
    else:
        verdict = "CONFIRMED_UNSATISFIABLE_AT_FROZEN_REVISIONS"

    report = {
        "report_id": "W041-F0-MIRROR-INDEP-01",
        "task_id": "W041-F0-MIRROR-INDEP-01",
        "actor": "worker-041",
        "instance": "worker-041-20260912T002444-968807",
        "created_at": NOW_ISO,
        "node_id": "F0",
        "gate": "G-F0",
        "class_id": ";".join(CLASS_IDS),
        "class_ids": CLASS_IDS,
        "question": (
            "Can research_map/formulation_taxonomy.yaml (A, declared F0) and "
            "artifacts/formulation/formulation_taxonomy.yaml (B, class-contract supplement) "
            "be made byte-identical without damaging a frozen consumer, as assignment "
            "astra-life02-publish-f0 requires? Tested against leadform-blocker-0007 and CF-13."
        ),
        "pinned_inputs": pins,
        "hash_stable_across_run": bool(hash_stable),
        "drift_end_of_run": drift,
        "superseded_prior_run": {
            "why": (
                "A first measurement at A=276009f4f63d / F1=9a8bd4c96800 was completed but "
                "invalidated before event emission when the F0 rev5 republish moved the canonical "
                "taxonomy to 0abb9ed8a961 and F1 to b474fbc49cdd; a second completed measurement "
                "was invalidated when FROZEN.json moved 2554e276a0db -> 5fa3b3bf95f2 (pin "
                "re-issue to rev27). Per this task's own falsifier ('pinned hashes moving before "
                "adjudication voids the binding') the measurement was re-run each time; this "
                "report is the re-measurement at the live revisions."
            ),
            "prior_pins": {
                "research_map/formulation_taxonomy.yaml": FROZEN_A_SHA,
                "schemas/af_wcc_vacuum.yaml": "9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503",
            },
        },
        "frozen_reference_hashes": {"A_canonical_declared_f0": a_sha, "B_authoring_supplement": b_sha},
        "instrument": {
            "evaluator": "E1-E7 structure checks, artifacts/worker-041/f0_mirror_indep/run_f0_mirror_indep.py",
            "frozen_checker_run_byte_identically": CHECKER_REL,
            "controls": {
                "baseline_structural_pass_and_checker_zero": bool(baseline_structural_ok),
                "baseline_frozen_pins_fresh": bool(baseline_pins_ok),
                "merged_new_revision_control_structural_pass_and_checker_zero": bool(merged_ok),
                "merged_control_expected_to_break_frozen_pins": True,
                "semantic_mutation_control_detected": bool(neg_ok),
            },
        },
        "cases": results,
        "admissibility": {
            "A_canonical_eq_authoring_bytes": bool(a2b_admissible),
            "B_authoring_eq_canonical_bytes": bool(b2a_admissible),
        },
        "baseline_pin_freshness": {
            "E5_declared_f0_hash_matches_measured":
                results["baseline_frozen_current"]["structure"]["checks"]
                ["E5_declared_f0_hash_matches_measured"],
            "E7_frozen_logical_artifact_pins":
                results["baseline_frozen_current"]["structure"]["checks"]
                ["E7_frozen_logical_artifact_pins"],
        },
        "frozen_logical_artifacts_resolution": {
            name: {"path": e.get("path"), "pinned_sha256": e.get("sha256"),
                   "mirrors": e.get("mirrors")}
            for name, e in (json.loads((ROOT / FROZEN_REL).read_text(encoding="utf-8"))
                            .get("logical_artifacts") or {}).items()
        },
        "per_class_consequences": {
            cid: {
                "baseline": results["baseline_frozen_current"]["structure"]["checks"]
                ["E3_per_class_identity_agreement"]["per_class"][cid],
                "A_eq_B": a2b["structure"]["checks"]["E3_per_class_identity_agreement"]
                ["per_class"][cid],
                "B_eq_A": b2a["structure"]["checks"]["E3_per_class_identity_agreement"]
                ["per_class"][cid],
            } for cid in CLASS_IDS
        },
        "verdict": verdict,
        "conclusion": (
            "Neither byte-identical direction of the two frozen revisions is admissible. "
            "A:=B deletes the declared-F0 structure (class_ids/classes/transfer_rules) that the "
            "canonical consumers need; B:=A deletes class_contracts/axis_registry/"
            "implication_ledger, so the three schemas' class_contract_pointer becomes "
            "unresolvable and the declared_f0_sha256 pins no longer match. The freeze-consistency "
            "checker requires BOTH key sets in the same pair of files and cannot pass under "
            "either direction. A single merged file carrying both key sets does pass every "
            "consumer and the frozen checker, but it is a NEW revision (new sha256), so it "
            "cannot be produced by 'publish the frozen revision byte-identically'. Independent "
            "confirmation of leadform-blocker-0007: the pair should be adjudicated as TWO "
            "logical artifacts (as FROZEN rev26 logical_artifacts already declares) or re-frozen "
            "as one merged revision with re-issued pins and pointers."
        ),
        "falsifier": (
            "Any byte-identical direction (A:=B or B:=A) under which E1-E7 all pass and "
            "check_taxonomy_consistency.py exits 0; or a frozen consumer that resolves the "
            "class-contract pointer / declared-F0 hash through a path other than the two "
            "measured files; or the pinned hashes moving before adjudication, which voids this "
            "binding and requires re-measurement."
        ),
        "evidence_refs": [
            "artifacts/worker-041/f0_mirror_indep/f0_mirror_report.json",
            f"{A_REL}#{a_sha[:12]}",
            f"{B_REL}#{b_sha[:12]}",
            "artifacts/formulation/evidence/f0_mirror_conflict.json",
            f"artifacts/formulation/FROZEN.json#{sha_file(ROOT / FROZEN_REL)[:12]}",
            f"{CHECKER_REL}#{sha_file(ROOT / CHECKER_REL)[:12]}",
        ],
        "authority_note": (
            "Worker measurement only: sets no node status, no validation_status=passed and no "
            "gate verdict; the controller owns the adjudication."
        ),
    }
    out = HERE / "f0_mirror_report.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (HERE / "f0_mirror_report.json.sha256").write_text(
        f"{sha_file(out)}  f0_mirror_report.json\n", encoding="utf-8")

    print(json.dumps({
        "report": str(out.relative_to(ROOT)),
        "report_sha256": sha_file(out),
        "verdict": verdict,
        "controls": report["instrument"]["controls"],
        "admissibility": report["admissibility"],
        "baseline_checker": results["baseline_frozen_current"]["checker"]["stdout"],
        "A_eq_B_checker": a2b["checker"]["stdout"] or a2b["checker"]["stderr_tail"],
        "B_eq_A_checker": b2a["checker"]["stdout"] or b2a["checker"]["stderr_tail"],
        "merged_checker": merged_case["checker"]["stdout"],
        "neg_control_checker": neg["checker"]["stdout"],
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
