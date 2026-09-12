#!/usr/bin/env python3
"""W026-F1-HF-ADJUDICATE-06 mechanical probe.

Reads ONLY:
  - schemas/af_wcc_vacuum.yaml                (the pinned review target)
  - artifacts/formulation/schemas/af_wcc_vacuum.yaml  (mirror equality check)
  - research_map/formulation_taxonomy.yaml    (canonical F0 contract tree)
  - artifacts/formulation/formulation_taxonomy.yaml   (authoring F0 contract tree)
  - schemas/f1_falsifier_tests.jsonl
  - artifacts/formulation/evidence/taxonomy_consistency.json
  - schemas/semantic_contract_tests/observed_verdicts.json
  - schemas/af_scc_c2_vacuum.yaml, schemas/af_scc_c0_vacuum.yaml   (cross-schema check)
  - artifacts/formulation/tools/check_class_schema.py  (control gate, subprocess)
  - research_map/class_separation.py                   (control detector, imported)

Writes ONLY under artifacts/worker-026/f1_adjudication/:
  snapshot/af_wcc_vacuum.9a8bd4c96800.yaml
  probe_output.json

Exit codes: 0 ok, 3 hash drift (fail-closed, no adjudication), 2 usage/IO error.
"""
from __future__ import annotations

import collections
import datetime as _dt
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "artifacts/worker-026/f1_adjudication"
SNAP = OUT / "snapshot"
TARGET = ROOT / "schemas/af_wcc_vacuum.yaml"
MIRROR = ROOT / "artifacts/formulation/schemas/af_wcc_vacuum.yaml"
EXPECTED = "9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503"
CLASS_ID = "AF-WCC-VAC-GEN"

import yaml  # noqa: E402


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def now_iso() -> str:
    return _dt.datetime.now().astimezone().replace(microsecond=0).isoformat()


class DupLoader(yaml.SafeLoader):
    """SafeLoader that records duplicate mapping keys instead of silently keeping one."""


def _dup_mapping(loader, node, deep=False):
    keys = [loader.construct_object(k, deep=deep) for k, _ in node.value]
    for key, n in collections.Counter(keys).items():
        if n > 1:
            loader._dup_keys.append((key, n))
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


DupLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _dup_mapping)


def dup_load(text: str):
    loader = DupLoader(text)
    loader._dup_keys = []
    try:
        data = loader.get_single_data()
    finally:
        loader.dispose()
    return data, loader._dup_keys


def load_yaml(p: Path):
    return yaml.safe_load(p.read_text())


def main() -> int:
    result: dict = {
        "task_id": "W026-F1-HF-ADJUDICATE-06",
        "worker": "worker-026",
        "probe_started_at": now_iso(),
        "preregistration": "artifacts/worker-026/f1_adjudication/preregistration.json",
        "commands": [],
        "findings": {},
        "errors": [],
    }

    # ---------- hash gate (fail-closed) ----------
    live = sha256_file(TARGET)
    mirror_live = sha256_file(MIRROR)
    result["hash_gate"] = {
        "schemas/af_wcc_vacuum.yaml": live,
        "artifacts/formulation/schemas/af_wcc_vacuum.yaml": mirror_live,
        "expected": EXPECTED,
        "match": live == EXPECTED,
        "mirror_match": mirror_live == EXPECTED,
    }
    if live != EXPECTED or mirror_live != EXPECTED:
        result["abort"] = "HASH_DRIFT: pinned review bytes no longer live; adjudication void (fail-closed)"
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "probe_output.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps({"abort": result["abort"], "live": live, "mirror": mirror_live}))
        return 3

    SNAP.mkdir(parents=True, exist_ok=True)
    snap = SNAP / "af_wcc_vacuum.9a8bd4c96800.yaml"
    snap.write_bytes(TARGET.read_bytes())
    if sha256_file(snap) != EXPECTED:
        result["abort"] = "SNAPSHOT_COPY_MISMATCH"
        (OUT / "probe_output.json").write_text(json.dumps(result, indent=2) + "\n")
        return 3
    result["snapshot"] = {
        "path": str(snap.relative_to(ROOT)),
        "sha256": EXPECTED,
        "bytes": TARGET.stat().st_size,
        "lines": len(TARGET.read_text().splitlines()),
    }

    text = snap.read_text()
    doc = yaml.safe_load(text)

    # ---------- ADJ-1 quantifier: whole-curve vs tail ----------
    q = doc["quantifiers"]
    vis = doc["visibility"]
    result["findings"]["ADJ-1"] = {
        "quantifiers.formal": q.get("formal"),
        "quantifiers.domains.D5.definition": q["domains"]["D5"]["definition"],
        "quantifiers.negation": q.get("negation"),
        "visibility.definition": vis.get("definition"),
        "visibility.negation_conclusion": vis.get("negation_conclusion"),
        "conclusion.statement_formal": doc["conclusion"].get("statement_formal"),
        "raw_line_numbers": {
            needle: [i + 1 for i, line in enumerate(text.splitlines()) if needle in line]
            for needle in [
                "not exists q in I+ with gamma subset J^-(q)",
                "gamma([0,T)) is contained in the causal past J^-(q)",
                "the TAIL gamma([t0,T)) is contained in J^-(q)",
                "for every q in I+ and every t0 in [0,T)",
            ]
        },
        "tail_token_present_in_formal": ("t0" in (q.get("formal") or "")) or ("[" in (q.get("formal") or "") and "T)" in (q.get("formal") or "")),
        "tail_token_present_in_D5": "t0" in (q["domains"]["D5"]["definition"] or ""),
    }

    # ---------- ADJ-2 dangling symbols ----------
    symbol_hits = {}
    for sym in ["AF_{I+}", "complete(I+_D)", "visible_singularity_from_I_plus"]:
        symbol_hits[sym] = [i + 1 for i, line in enumerate(text.splitlines()) if sym in line]
    notation_keys = [k for k in doc.keys() if re.search(r"notation|symbol|glossary", k, re.I)]
    result["findings"]["ADJ-2"] = {
        "symbol_line_hits": symbol_hits,
        "notation_top_level_keys": notation_keys,
        "i_plus_definition_present": bool(doc.get("i_plus", {}).get("definition")),
        "i_plus_completeness_definition_present": bool(doc.get("i_plus", {}).get("completeness_definition")),
        "conclusion_bound_to_statement_formal": "statement_formal" in (doc["conclusion"].get("equivalent_standard_formulation", {}).get("status", "")),
    }

    # ---------- ADJ-3 contract pointer resolution ----------
    canon_tax_p = ROOT / "research_map/formulation_taxonomy.yaml"
    auth_tax_p = ROOT / "artifacts/formulation/formulation_taxonomy.yaml"
    canon_tax = load_yaml(canon_tax_p)
    auth_tax = load_yaml(auth_tax_p)
    pointer = doc.get("class_contract_pointer", "")
    frag_key = pointer.split("#", 1)[1] if "#" in pointer else ""
    frag_parts = frag_key.split(".") if frag_key else []
    canon_contract = canon_tax
    auth_contract = auth_tax
    for part in frag_parts:
        canon_contract = canon_contract.get(part) if isinstance(canon_contract, dict) else None
        auth_contract = auth_contract.get(part) if isinstance(auth_contract, dict) else None
    canon_by_classes = canon_tax.get("classes", {}).get(CLASS_ID)
    auth_by_classes = auth_tax.get("class_contracts", {}).get(CLASS_ID)

    def canon_json(o):
        return json.dumps(o, sort_keys=True, separators=(",", ":"), default=str)

    result["findings"]["ADJ-3"] = {
        "class_contract_pointer": pointer,
        "fragment_key": frag_key,
        "canonical_taxonomy_path": "research_map/formulation_taxonomy.yaml",
        "canonical_taxonomy_sha256": sha256_file(canon_tax_p),
        "authoring_taxonomy_path": "artifacts/formulation/formulation_taxonomy.yaml",
        "authoring_taxonomy_sha256": sha256_file(auth_tax_p),
        "top_level_keys_canonical": sorted(canon_tax.keys()),
        "top_level_keys_authoring": sorted(auth_tax.keys()),
        "pointer_resolves_canonical": canon_contract is not None,
        "pointer_resolves_authoring": auth_contract is not None,
        "canonical_classes_contract_found": canon_by_classes is not None,
        "authoring_class_contracts_contract_found": auth_by_classes is not None,
        "content_equal_canonical_vs_authoring": canon_json(canon_by_classes) == canon_json(auth_by_classes) if (canon_by_classes and auth_by_classes) else None,
        "content_equal_pointer_vs_canonical_classes": canon_json(auth_contract) == canon_json(canon_by_classes) if (auth_contract and canon_by_classes) else None,
    }

    # ---------- ADJ-4 duplicate keys + future timestamps ----------
    _, dups = dup_load(text)
    wall = now_iso()
    kept_revised = doc.get("revised_at")
    kept_checked = doc.get("f0_binding", {}).get("checked_at")
    result["findings"]["ADJ-4"] = {
        "duplicate_keys": [{"key": k, "count": n} for k, n in dups],
        "revised_at_occurrences": len(re.findall(r"^revised_at:", text, re.M)),
        "revised_at_unused_occurrences": len(re.findall(r"^revised_at_unused:", text, re.M)),
        "last_wins_revised_at": kept_revised,
        "last_wins_f0_binding_checked_at": kept_checked,
        "wall_clock_at_probe": wall,
        "revised_at_ahead_of_wall_clock": bool(kept_revised and kept_revised > wall),
        "f0_checked_at_ahead_of_wall_clock": bool(kept_checked and kept_checked > wall),
    }

    # ---------- ADJ-5 falsifier-test binding + consistency-file pinning ----------
    ft = ROOT / "schemas/f1_falsifier_tests.jsonl"
    rows = [json.loads(l) for l in ft.read_text().splitlines() if l.strip()]
    binding = collections.Counter(r.get("binding_sha256") for r in rows)
    prior = collections.Counter(r.get("prior_binding_sha256") for r in rows)
    tc_text = (ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json").read_text()
    result["findings"]["ADJ-5"] = {
        "f1_falsifier_tests_path": "schemas/f1_falsifier_tests.jsonl",
        "f1_falsifier_tests_sha256": sha256_file(ft),
        "rows": len(rows),
        "binding_sha256_distribution": dict(binding),
        "binding_matches_snapshot": list(binding.keys()) == [EXPECTED],
        "prior_binding_sha256_distribution": {str(k): v for k, v in prior.items()},
        "taxonomy_consistency_path": "artifacts/formulation/evidence/taxonomy_consistency.json",
        "taxonomy_consistency_sha256": sha256_bytes(tc_text.encode()),
        "taxonomy_consistency_consistent_field": json.loads(tc_text).get("consistent"),
        "taxonomy_consistency_contains_64hex": bool(re.search(r"[0-9a-f]{64}", tc_text)),
        "taxonomy_consistency_contains_12hex": bool(re.search(r"\b[0-9a-f]{12}\b", tc_text)),
    }

    # ---------- ADJ-6 calibration blocker ----------
    ov = json.loads((ROOT / "schemas/semantic_contract_tests/observed_verdicts.json").read_text())
    result["findings"]["ADJ-6"] = {"validity": ov.get("validity")}

    # ---------- ADJ-7 cross-schema data class ----------
    def dc(p):
        d = load_yaml(ROOT / p)
        rc = d.get("data_class", {}).get("regularity_class", {})
        sv = rc.get("sobolev_variant", {}) if isinstance(rc, dict) else {}
        return {
            "class_id": d.get("class_id"),
            "equations": d.get("data_class", {}).get("equations"),
            "matter": d.get("data_class", {}).get("matter"),
            "cosmological_constant": d.get("data_class", {}).get("cosmological_constant"),
            "regularity_default": rc.get("default") if isinstance(rc, dict) else None,
            "sobolev_s": sv.get("s"),
            "sobolev_delta": sv.get("delta"),
            "sobolev_spaces": sv.get("spaces"),
            "genericity_kind": d.get("genericity", {}).get("kind"),
        }

    f1dc = dc("schemas/af_wcc_vacuum.yaml")
    f2adc = dc("schemas/af_scc_c2_vacuum.yaml")
    f2bdc = dc("schemas/af_scc_c0_vacuum.yaml")
    keys = ["equations", "matter", "cosmological_constant", "regularity_default", "sobolev_s", "sobolev_delta", "genericity_kind"]
    diffs = {k: [f1dc[k], f2adc[k], f2bdc[k]] for k in keys if not (f1dc[k] == f2adc[k] == f2bdc[k])}
    result["findings"]["ADJ-7"] = {"F1": f1dc, "F2a": f2adc, "F2b": f2bdc, "class_relevant_diffs": diffs}

    # ---------- controls: canonical gate + class separation detector ----------
    gate = ROOT / "artifacts/formulation/tools/check_class_schema.py"
    cp = subprocess.run(
        [sys.executable, str(gate), "--json", str(snap)],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    result["commands"].append({
        "argv": ["python3", "artifacts/formulation/tools/check_class_schema.py", "--json", str(snap.relative_to(ROOT))],
        "exit_code": cp.returncode,
        "stdout_sha256": sha256_bytes(cp.stdout.encode()),
        "stdout_head": cp.stdout[:1200],
        "stderr_head": cp.stderr[:400],
    })
    spec = importlib.util.spec_from_file_location("class_separation", ROOT / "research_map/class_separation.py")
    cs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cs)
    cs_findings = cs.findings_for_text(text, "artifact schemas/af_wcc_vacuum.yaml")
    result["commands"].append({
        "argv": ["python3", "-c", "import class_separation; class_separation.findings_for_text(<snapshot text>)"],
        "exit_code": 0,
        "class_separation_findings": cs_findings,
        "class_separation_sha256": sha256_file(ROOT / "research_map/class_separation.py"),
    })

    result["probe_finished_at"] = now_iso()
    result["drift_recheck"] = {
        "schemas/af_wcc_vacuum.yaml": sha256_file(TARGET),
        "artifacts/formulation/schemas/af_wcc_vacuum.yaml": sha256_file(MIRROR),
        "drifted": (sha256_file(TARGET) != EXPECTED) or (sha256_file(MIRROR) != EXPECTED),
    }
    (OUT / "probe_output.json").write_text(json.dumps(result, indent=2, default=str) + "\n")
    print(json.dumps({
        "probe_output": "artifacts/worker-026/f1_adjudication/probe_output.json",
        "sha256": sha256_file(OUT / "probe_output.json"),
        "drifted": result["drift_recheck"]["drifted"],
        "gate_exit": cp.returncode,
        "classsep_findings": cs_findings,
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
