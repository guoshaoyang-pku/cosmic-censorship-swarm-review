#!/usr/bin/env python3
"""Supplement to W044-F2B-INDEP-VERDICT-01.

Runs on the pinned snapshot written by verify_f2b.py and appends three families of checks that
the main battery does not cover, then refreshes the drift checks against wall clock:

  YAML-*  document integrity: duplicate mapping keys (several reviewers reported duplicate
          top-level `revised_at`), and whether a strict duplicate-rejecting parse succeeds.
  XREF-*  cross-artifact binding: does `class_contract_pointer` resolve inside the AUTHORITATIVE
          canonical taxonomy, does the declared f0 sha256 match, does the canonical class entry
          agree with the schema's regularity/family.
  DRIFT-* re-measured after the supplement so the emitted verdict is not bound to bytes that
          moved while the report was being assembled.

Rewrites report.json in place (the report is the final artifact; its sha256 is taken by the
emitter afterwards). Never edits canonical artifacts.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))
C0 = "AF-SCC-C0-VAC-GEN"
TARGET = "schemas/af_scc_c0_vacuum.yaml"
TAXONOMY = "research_map/formulation_taxonomy.yaml"
AUTHORING_TAX = "artifacts/formulation/formulation_taxonomy.yaml"
FROZEN = "artifacts/formulation/FROZEN.json"
FROZEN_FILES = [TARGET, "schemas/af_scc_c2_vacuum.yaml", "schemas/af_wcc_vacuum.yaml", TAXONOMY]
AUTHORING_OF = {
    TARGET: "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml": "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_wcc_vacuum.yaml": "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
    TAXONOMY: AUTHORING_TAX,
}


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class _DupLoader(yaml.SafeLoader):
    pass


def duplicate_keys(text: str) -> list:
    """All repeated mapping keys with their line numbers, per mapping scope."""
    dups: list = []

    def cm(loader, node, deep=False):
        seen = []
        for k, _v in node.value:
            key = loader.construct_object(k, deep=deep)
            if key in seen:
                dups.append({"key": str(key), "line": k.start_mark.line + 1})
            else:
                seen.append(key)
        return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)

    _DupLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, cm)
    yaml.load(text, Loader=_DupLoader)
    return dups


def main() -> int:
    rp = OUT / "report.json"
    rep = json.loads(rp.read_text())
    if "settled_revision" not in rep:
        print("no pinned revision in report (moving-target blocker); supplement not applicable")
        return 0
    checks = rep["checks"]
    sys.path.insert(0, str(ROOT / "research_map"))
    import class_separation as cs  # noqa: E402
    snap = ROOT / rep["settled_revision"]["snapshot_path"]
    text = snap.read_text()
    doc = yaml.safe_load(text)
    snap_sha = rep["settled_revision"]["snapshot_sha256"]
    new = []

    def check(cid, desc, expected, observed, ok, evidence, severity="hard"):
        new.append({"check_id": cid, "description": desc, "expected": expected, "observed": observed,
                    "ok": bool(ok), "severity": severity, "evidence": evidence})

    # ---- YAML integrity ------------------------------------------------------
    dups = duplicate_keys(text)
    check("YAML-01", "pinned snapshot has no duplicate YAML mapping keys (strict document integrity)",
          "0 duplicates", {"count": len(dups), "duplicates": dups[:12]}, len(dups) == 0,
          [f"{rep['settled_revision']['snapshot_path']}#{snap_sha[:16]}"],
          severity="soft")
    # Do duplicated top-level keys carry the same value? If not, the effective document depends on
    # parser semantics (safe_load last-wins), so the revision is ambiguous to any other reader.
    root = yaml.compose(text)
    top_values: dict = {}
    if isinstance(root, yaml.MappingNode):
        for k_node, v_node in root.value:
            k = k_node.value
            v = v_node.value if isinstance(v_node, yaml.ScalarNode) else f"<{type(v_node).__name__}>"
            top_values.setdefault(k, []).append(str(v))
    ambiguous = {k: v for k, v in top_values.items() if len(set(v)) > 1}
    check("YAML-02", "duplicate top-level keys do not carry conflicting values (effective revision is parser-independent)",
          "no conflicting duplicates", {"duplicated_keys": {k: v for k, v in top_values.items() if len(v) > 1},
                                        "conflicting": ambiguous},
          len(ambiguous) == 0,
          [f"{rep['settled_revision']['snapshot_path']}#{snap_sha[:16]}"], severity="soft")

    # ---- XREF: authoritative-taxonomy binding --------------------------------
    tax_sha = sha(ROOT / TAXONOMY)
    tax = yaml.safe_load((ROOT / TAXONOMY).read_text())
    ptr = doc.get("class_contract_pointer", "")
    fragment = ptr.split("#", 1)[1] if "#" in ptr else ""
    resolvable = False
    node = tax
    try:
        for part in [p for p in fragment.split(".") if p]:
            node = node[part]
        resolvable = True
    except (KeyError, TypeError):
        resolvable = False
    auth_resolvable = None
    if (ROOT / AUTHORING_TAX).is_file():
        try:
            anode = yaml.safe_load((ROOT / AUTHORING_TAX).read_text())
            for part in [p for p in fragment.split(".") if p]:
                anode = anode[part]
            auth_resolvable = True
        except (KeyError, TypeError, yaml.YAMLError):
            auth_resolvable = False
    check("XREF-01", "class_contract_pointer resolves inside the AUTHORITATIVE canonical taxonomy",
          f"fragment '{fragment}' resolvable", {"resolvable_canonical": resolvable,
          "resolvable_authoring": auth_resolvable,
          "canonical_top_level_keys": list(tax.keys()),
          "canonical_has_class_contracts": "class_contracts" in tax,
          "canonical_class_ids": list((tax.get("classes") or {}).keys()) if isinstance(tax.get("classes"), dict) else None},
          resolvable, [f"{TAXONOMY}#{tax_sha[:16]}", f"{TARGET}:class_contract_pointer"])
    ptr_path = ptr.split("#", 1)[0]
    check("XREF-02", "class_contract_pointer path target agrees with the canonical-path policy",
          TAXONOMY, {"pointer_path": ptr_path, "authoring_path_differs_from_canonical":
                     sha(ROOT / AUTHORING_TAX) != tax_sha if (ROOT / AUTHORING_TAX).is_file() else None},
          ptr_path == TAXONOMY, ["research_map/ASTRA_HANDOFF.md:18-21", f"{TARGET}:class_contract_pointer"],
          severity="soft")
    declared = (doc.get("f0_binding") or {}).get("declared_f0_sha256")
    check("XREF-03", "f0_binding.declared_f0_sha256 equals the canonical taxonomy hash at supplement time",
          tax_sha, declared, declared == tax_sha,
          [f"{TAXONOMY}#{tax_sha[:16]}", f"{TARGET}:f0_binding.declared_f0_sha256"])
    axes = ((tax.get("classes") or {}).get(C0) or {}).get("axes", {})
    check("XREF-04", "canonical taxonomy class entry agrees with the schema (family SCC, regularity C0)",
          {"family": "SCC", "regularity_token": "C0"},
          {"family": axes.get("family"), "regularity_token": axes.get("regularity_token")},
          axes.get("family") == "SCC" and axes.get("regularity_token") == "C0",
          [f"{TAXONOMY}#{tax_sha[:16]}", f"{TARGET}:conclusion.family"])

    # ---- CS: class-separation checker discriminating-power probes -------------
    # The canonical schemas keep their asserted declarations in NESTED mappings
    # (regularity.extension_regularity_exact, conclusion.statement_natural_language, ...).
    # findings_for_text() only scans flat `key: value` lines whose key is in ASSERTED_LINE_KEYS
    # and never calls _scan_conclusion(), so a leak placed where the schemas actually store
    # their declarations is invisible to it. These probes isolate that boundary.
    probe_specs = {
        "A_flat_regularity_composite":
            "class_id: AF-SCC-C0-VAC-GEN\nregularity: C0 or C2 nondegenerate metric\n",
        "B_flat_conclusion_wcc":
            "class_id: AF-SCC-C0-VAC-GEN\nconclusion: The singularity is visible from future null infinity and the "
            "weak cosmic censorship conjecture fails.\n",
        "C_nested_regularity_composite":
            "class_id: AF-SCC-C0-VAC-GEN\nregularity:\n  extension_regularity_exact: C0 or C2 nondegenerate metric\n",
        "D_nested_conclusion_wcc":
            "class_id: AF-SCC-C0-VAC-GEN\nconclusion:\n  statement_natural_language: The singularity is visible from "
            "future null infinity and the weak cosmic censorship conjecture fails.\n",
    }
    probe_dir = OUT / "mutations"
    probe_dir.mkdir(exist_ok=True)
    obs, prov = {}, {}
    for name, txt in probe_specs.items():
        p = probe_dir / f"cs_probe_{name}.yaml"
        p.write_text(txt)
        obs[name] = cs.findings_for_text(txt, name)
        prov[name] = f"{p.relative_to(ROOT)}#{sha(p)[:16]}"
    map_obj = {"class_id": C0, "conclusion": "The singularity is visible from I+ and weak cosmic censorship fails."}
    mp = probe_dir / "cs_probe_E_map_object_wcc_conclusion.json"
    mp.write_text(json.dumps(map_obj, indent=1))
    obs["E_map_object_wcc_conclusion"] = cs.findings(map_obj, "E")
    prov["E_map_object_wcc_conclusion"] = f"{mp.relative_to(ROOT)}#{sha(mp)[:16]}"

    check("CS-01", "checker POSITIVE CONTROL: flat top-level composite regularity IS flagged by findings_for_text",
          ">=1 finding", obs["A_flat_regularity_composite"][:2], len(obs["A_flat_regularity_composite"]) >= 1,
          [prov["A_flat_regularity_composite"]])
    check("CS-02", "checker POSITIVE CONTROL: WCC conclusion on an SCC class IS flagged by the map-object scanner",
          ">=1 finding", obs["E_map_object_wcc_conclusion"][:2], len(obs["E_map_object_wcc_conclusion"]) >= 1,
          [prov["E_map_object_wcc_conclusion"]])
    check("CS-03", "checker BLIND SPOT: nested regularity composite is flagged by findings_for_text",
          ">=1 finding", obs["C_nested_regularity_composite"][:2],
          len(obs["C_nested_regularity_composite"]) >= 1, [prov["C_nested_regularity_composite"]],
          severity="checker")
    check("CS-04", "checker BLIND SPOT: nested conclusion WCC sentence is flagged by findings_for_text",
          ">=1 finding", obs["D_nested_conclusion_wcc"][:2], len(obs["D_nested_conclusion_wcc"]) >= 1,
          [prov["D_nested_conclusion_wcc"]], severity="checker")
    check("CS-05", "checker BLIND SPOT: flat top-level WCC conclusion is flagged by findings_for_text",
          ">=1 finding", obs["B_flat_conclusion_wcc"][:2], len(obs["B_flat_conclusion_wcc"]) >= 1,
          [prov["B_flat_conclusion_wcc"]], severity="checker")

    # ---- DRIFT refresh -------------------------------------------------------
    fz = json.loads((ROOT / FROZEN).read_text())
    target_now = sha(ROOT / TARGET)
    for c in checks:
        if c["check_id"] == "DRIFT-01":
            c["observed"] = {"post_supplement": target_now, "snapshot": snap_sha, "matches": target_now == snap_sha,
                             "rechecked_at": now()}
            c["ok"] = target_now == snap_sha
        if c["check_id"] == "DRIFT-02":
            post = {}
            ok_all = True
            for rel in FROZEN_FILES:
                disk = sha(ROOT / rel)
                pin = (fz.get("files", {}).get(rel) or {}).get("sha256")
                auth = sha(ROOT / AUTHORING_OF[rel])
                ok_all = ok_all and disk == pin and auth == disk
                post[rel] = {"canonical": disk, "pin": pin, "pin_matches": disk == pin,
                             "authoring": auth, "authoring_matches": auth == disk}
            c["observed"] = {"frozen_revision": fz.get("revision"), "files": post, "rechecked_at": now()}
            c["ok"] = ok_all

    rep["checks"] = checks + new
    rep["supplement"] = {"script": "artifacts/worker-044/f2b_independent_verdict/supplement_checks.py",
                         "script_sha256": sha(Path(__file__)), "ran_at": now(),
                         "new_check_ids": [c["check_id"] for c in new]}

    # MUT-03/MUT-04 in the main battery tested the SCHEMA with leak mutations; a miss is a defect in
    # the checker, not in the schema. Reclassify them as checker-axis and carry one consolidated hard
    # finding for the verification method the map relies on.
    for c in rep["checks"]:
        if c["check_id"] in {"MUT-03", "MUT-04"}:
            c["severity"] = "checker"
    cs_blind = any(not c["ok"] for c in rep["checks"]
                   if c["check_id"] in {"MUT-03", "MUT-04", "CS-03", "CS-04", "CS-05"})
    hard = [c["check_id"] for c in rep["checks"] if not c["ok"] and c["severity"] == "hard"]
    if cs_blind:
        hard.append("CLASSSEP-TEXT-NESTED-BLINDSPOT")
    sem_ok = next((c["ok"] for c in rep["checks"] if c["check_id"] == "SEM-01"), True)
    sep_fail = any(c["check_id"].startswith("SEP-") and not c["ok"] for c in rep["checks"])
    gate_fail = any(c["check_id"] in {"GATE-01", "GATE-03", "GATE-04"} and not c["ok"] for c in rep["checks"])
    drift_void = "DRIFT-01" in hard or "DRIFT-02" in hard
    if rep.get("publication_unsettled") is not None or rep.get("moving_target") is not None:
        verdict, score = "inconclusive", 0
        if "PUBLICATION-BINDING-UNSETTLED" not in hard:
            hard = hard + ["PUBLICATION-BINDING-UNSETTLED"]
    elif drift_void:
        verdict, score = "inconclusive", 0
    elif sep_fail or not sem_ok:
        verdict, score = "revise", 2
    elif gate_fail or hard:
        verdict, score = "revise", 3
    else:
        verdict, score = "accept", 4.5
    rep["checker_findings"] = {
        "text_scanner_nested_blindspot": cs_blind,
        "positive_controls_passed": obs["A_flat_regularity_composite"] != [] and obs["E_map_object_wcc_conclusion"] != [],
        "probe_observations": {k: v[:2] for k, v in obs.items()},
        "scope": "class_separation.findings_for_text (artifact-text path). The schema content itself is not "
                 "shown defective on this axis by the independent SEP-02..SEP-06 assertions; the point is that "
                 "a clean findings_for_text result is not load-bearing evidence for nested-field class binding.",
    }
    rep["summary"] = {"total": len(rep["checks"]), "pass": sum(1 for c in rep["checks"] if c["ok"]),
                      "fail": sum(1 for c in rep["checks"] if not c["ok"]),
                      "hard_failures": hard, "verdict": verdict, "score": score}
    rp.write_text(json.dumps(rep, indent=2, sort_keys=True))
    print(json.dumps({"checks_added": [c["check_id"] for c in new],
                      "duplicates": len(dups), "xref_resolvable": resolvable,
                      "classsep_text_blindspot": cs_blind,
                      "verdict": verdict, "hard_failures": hard, "report_sha256": sha(rp)}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
