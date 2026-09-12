#!/usr/bin/env python3
"""Class-bound F0 contract-binding drift check (worker-05, node F2a).

Why this exists
---------------
Every canonical class schema carries an `f0_binding` block that pins the F0
taxonomy by sha256 and points at a class contract.  The artifact's own rule is
explicit: "if the declared F0 artifact changes hash, refresh this binding and
re-run the consistency check before any gate verdict".  The frozen binding gate
(check_class_schema.py, R01-R16) does not read those bytes, and
verify_frozen.py only checks FROZEN.json against disk.  No tool checked whether
a schema's *declared* cross-artifact binding resolves against the authoritative
(canonical) file, so a schema can pass the gate while bound to a dead revision.

Checks per schema (hard = fails the schema):
  B1 declared_f0_sha256 == sha256(canonical F0)                  [hard]
  B2 declared_f0_sha256 == sha256(authoring supplement F0)       [info]
  B3 class_contract_pointer file exists                          [hard]
  B4 class_contract_pointer anchor resolves in canonical F0, or an
     equivalent per-class container exists (layout drift -> warn) [hard/warn]
  B5 class_contract_pointer anchor resolves in supplement F0     [info]
  B6 consistency_evidence file exists                            [hard]
  B7 consistency_evidence binds the declared revision by exact full string [hard]
  B8 consistency_evidence binds the measured supplement revision full-string [hard]
     (B7/B8 fail when the evidence records no full sha256 for that input, so it
      cannot discharge the artifact's own refresh rule)

Falsifier for this checker: a schema whose declared F0 hash equals the measured
canonical F0 hash and whose pointer anchor resolves in the canonical file is
reported FAIL, or a schema with a stale hash is reported PASS.

Usage:
  python3 check_class_binding_drift.py [--json REPORT] [--selftest]
Exit 0 iff every schema passes; 1 on drift; 2 on usage/parse error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]

CANONICAL_F0 = "research_map/formulation_taxonomy.yaml"
SUPPLEMENT_F0 = "artifacts/formulation/formulation_taxonomy.yaml"
SCHEMAS = {
    "AF-WCC-VAC-GEN": "schemas/af_wcc_vacuum.yaml",
    "AF-SCC-C2-VAC-GEN": "schemas/af_scc_c2_vacuum.yaml",
    "AF-SCC-C0-VAC-GEN": "schemas/af_scc_c0_vacuum.yaml",
}

# Hard checks per schema; B2/B5 are recorded but do not fail a schema.
HARD_CHECKS = ("B1", "B3", "B4", "B6", "B7", "B8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def resolve_anchor(doc, anchor: str):
    """Resolve 'classes.AF-SCC-C2-VAC-GEN' against a parsed YAML document."""
    node = doc
    for part in anchor.split("."):
        if not isinstance(node, dict) or part not in node:
            return False, f"missing key {part!r} in anchor {anchor!r}"
        node = node[part]
    return True, "resolved"


def check_binding(root: Path, class_id: str, rel: str) -> dict:
    schema_path = root / rel
    rec: dict = {
        "class_id": class_id,
        "schema_path": rel,
        "checks": [],
        "hard_failures": [],
        "warnings": [],
    }
    if not schema_path.exists():
        rec["hard_failures"].append(f"{rel} missing")
        rec["verdict"] = "fail"
        return rec
    rec["schema_sha256"] = sha256_file(schema_path)
    doc = load_yaml(schema_path)
    fb = (doc or {}).get("f0_binding") or {}
    declared = fb.get("declared_f0_sha256")
    declared_artifact = fb.get("declared_f0_artifact")
    pointer = doc.get("class_contract_pointer")
    evidence = fb.get("consistency_evidence")

    canon = root / CANONICAL_F0
    supp = root / SUPPLEMENT_F0
    canon_sha = sha256_file(canon) if canon.exists() else None
    supp_sha = sha256_file(supp) if supp.exists() else None

    def add(cid, ok, detail, hard, warn=False):
        status = "pass" if ok else ("warn" if warn else "fail")
        rec["checks"].append({"check": cid, "status": status,
                              "hard": hard, "detail": detail})
        if not ok:
            if hard and not warn:
                rec["hard_failures"].append(f"{cid}: {detail}")
            if warn:
                rec["warnings"].append(f"{cid}: {detail}")

    add("B1", declared is not None and declared == canon_sha,
        f"declared={declared} canonical={canon_sha}", True)
    add("B2", declared is not None and declared == supp_sha,
        f"declared={declared} supplement={supp_sha}", False)

    pointer_file, _, pointer_anchor = (pointer or "").partition("#")
    pfile = root / pointer_file if pointer_file else None
    add("B3", bool(pointer_file) and pfile.exists(),
        f"pointer={pointer!r} file_exists={bool(pfile and pfile.exists())}", True)

    canon_ok = supp_ok = False
    class_containers: list[str] = []
    if pfile and pfile.exists() and pointer_anchor:
        pdoc = load_yaml(pfile)
        # canonical anchor: the contract must resolve in the authoritative file
        canon_doc = load_yaml(canon) if canon.exists() else {}
        canon_ok, canon_msg = resolve_anchor(canon_doc, pointer_anchor)
        supp_ok, supp_msg = resolve_anchor(pdoc, pointer_anchor)
        if isinstance(canon_doc, dict):
            for key, value in canon_doc.items():
                if isinstance(value, dict) and class_id in value:
                    class_containers.append(f"{key}.{class_id}")
    else:
        canon_msg = "pointer file or anchor absent"
        supp_msg = "pointer file or anchor absent"
    # The pointer may name an authoring layout while canonical F0 stores the same
    # contract under a different container; that is publication drift (warn), not
    # an unresolvable contract (fail).
    add("B4", canon_ok,
        f"anchor={pointer_anchor!r} in {CANONICAL_F0}: {canon_msg}; "
        f"equivalent class entries in canonical={class_containers}",
        True, warn=bool(class_containers))
    add("B5", supp_ok,
        f"anchor={pointer_anchor!r} in {SUPPLEMENT_F0}: {supp_msg}", False)

    ev = root / evidence if evidence else None
    ev_exists = bool(ev and ev.exists())
    add("B6", ev_exists, f"evidence={evidence!r} exists={ev_exists}", True)

    bound = False
    ev_sha = None
    if ev_exists:
        ev_sha = sha256_file(ev)
        try:
            ev_doc = json.loads(ev.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            ev_doc = None
            add("B7", False, f"evidence unparseable: {exc}", True)
            add("B8", False, f"evidence unparseable: {exc}", True)
        else:
            blob = json.dumps(ev_doc)
            bound = bool(declared) and (declared in blob)
            add("B7", bound,
                f"evidence_sha256={ev_sha} full_canonical_revision={bound} "
                f"(exact full-string match required)",
                True)
            supp_bound = bool(supp_sha) and (supp_sha in blob)
            add("B8", supp_bound,
                f"measured_supplement={supp_sha} recorded={supp_bound}", True)
    else:
        add("B7", False, "no evidence file to bind", True)
        add("B8", False, "no evidence file to bind", True)

    rec.update({
        "declared_f0_artifact": declared_artifact,
        "declared_f0_sha256": declared,
        "canonical_f0_sha256": canon_sha,
        "supplement_f0_sha256": supp_sha,
        "class_contract_pointer": pointer,
        "consistency_evidence": evidence,
        "consistency_evidence_sha256": ev_sha,
        "verdict": "fail" if rec["hard_failures"] else "pass",
    })
    return rec


def run(root: Path) -> dict:
    schemas = [check_binding(root, cid, rel) for cid, rel in SCHEMAS.items()]
    return {
        "checker": "check_class_binding_drift.py",
        "canonical_f0": CANONICAL_F0,
        "supplement_f0": SUPPLEMENT_F0,
        "schemas": schemas,
        "verdict": "fail" if any(s["verdict"] == "fail" for s in schemas) else "pass",
    }


def _write_fixture(root: Path, declared: str, anchor: str, bound: bool) -> None:
    (root / CANONICAL_F0).parent.mkdir(parents=True, exist_ok=True)
    (root / SUPPLEMENT_F0).parent.mkdir(parents=True, exist_ok=True)
    (root / "schemas").mkdir(parents=True, exist_ok=True)
    (root / CANONICAL_F0).write_text(
        "classes:\n  AF-SCC-C2-VAC-GEN:\n    conclusion: {type: t}\n", encoding="utf-8")
    (root / SUPPLEMENT_F0).write_text(
        "class_contracts:\n  AF-SCC-C2-VAC-GEN:\n    conclusion_type: t\n", encoding="utf-8")
    ev = root / "artifacts/formulation/evidence/taxonomy_consistency.json"
    ev.parent.mkdir(parents=True, exist_ok=True)
    supp_sha = sha256_file(root / SUPPLEMENT_F0)
    ev.write_text(json.dumps({"declared_sha256": declared if bound else None,
                              "input_sha256": {SUPPLEMENT_F0: supp_sha}}),
                  encoding="utf-8")
    (root / SCHEMAS["AF-SCC-C2-VAC-GEN"]).write_text(
        "f0_binding:\n"
        f"  declared_f0_artifact: {CANONICAL_F0}\n"
        f"  declared_f0_sha256: {declared}\n"
        "  consistency_evidence: artifacts/formulation/evidence/taxonomy_consistency.json\n"
        f"class_contract_pointer: \"{SUPPLEMENT_F0}#{anchor}\"\n",
        encoding="utf-8")


def _c2_record(root: Path) -> dict:
    return next(s for s in run(root)["schemas"] if s["class_id"] == "AF-SCC-C2-VAC-GEN")


def selftest() -> int:
    """Four fixtures: clean -> pass; each planted defect -> caught. Null control included."""
    tmp = Path(tempfile.mkdtemp(prefix="binding_drift_selftest_"))
    failures = []
    try:
        # control: declared == canonical, anchor resolves in canonical, evidence hash-bound
        _write_fixture(tmp, "PLACEHOLDER", "classes.AF-SCC-C2-VAC-GEN", True)
        good = sha256_file(tmp / CANONICAL_F0)
        _write_fixture(tmp, good, "classes.AF-SCC-C2-VAC-GEN", True)
        if _c2_record(tmp)["verdict"] != "pass":
            failures.append("NULL CONTROL failed: " + json.dumps(_c2_record(tmp)["hard_failures"]))
        # mutant 1: stale declared hash
        _write_fixture(tmp, "0" * 64, "classes.AF-SCC-C2-VAC-GEN", True)
        if _c2_record(tmp)["verdict"] != "fail":
            failures.append("mutant stale-hash not caught")
        # mutant 2: anchor absent from canonical
        _write_fixture(tmp, good, "classes.AF-SCC-C2-VAC-GEN", True)
        (tmp / CANONICAL_F0).write_text("classes: {}\n", encoding="utf-8")
        if _c2_record(tmp)["verdict"] != "fail":
            failures.append("mutant missing-anchor not caught")
        # mutant 3: unbound evidence
        _write_fixture(tmp, good, "classes.AF-SCC-C2-VAC-GEN", False)
        if _c2_record(tmp)["verdict"] != "fail":
            failures.append("mutant unbound-evidence not caught")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if failures:
        print("SELFTEST FAIL: " + "; ".join(failures))
        return 1
    print("SELFTEST PASS: null control clean; 3/3 planted binding defects caught")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", dest="report", default=None)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--root", default=str(ROOT))
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    root = Path(args.root).resolve()
    report = run(root)
    report["measured_at"] = __import__("datetime").datetime.now().astimezone().isoformat()
    text = json.dumps(report, indent=1, ensure_ascii=False)
    if args.report:
        Path(args.report).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if report["verdict"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
