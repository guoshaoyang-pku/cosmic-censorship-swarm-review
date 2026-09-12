#!/usr/bin/env python3
"""Independent F2a (AF-SCC-C2-VAC-GEN) review probes for worker-086.

Read-only. Emits artifacts/worker-086/f2a_review/probe_report.json.
Every finding in reviews/F2a-review-086.json is reproduced by a probe id here.
Run:  python3 artifacts/worker-086/f2a_review/probe_f2a.py
"""
from __future__ import annotations

import collections
import datetime
import hashlib
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SCHEMA = ROOT / "schemas/af_scc_c2_vacuum.yaml"
CANON_TAX = ROOT / "research_map/formulation_taxonomy.yaml"
AUTH_TAX = ROOT / "artifacts/formulation/formulation_taxonomy.yaml"
F1 = ROOT / "schemas/af_wcc_vacuum.yaml"
F2B = ROOT / "schemas/af_scc_c0_vacuum.yaml"
GATE = ROOT / "artifacts/formulation/tools/check_class_schema.py"
OUT = ROOT / "artifacts/worker-086/f2a_review/probe_report.json"
VARIANT_REGISTRY = ROOT / "artifacts/formulation/VARIANT_REGISTRY.json"


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def now() -> str:
    return datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()


def load_dupaware(path: pathlib.Path):
    """Parse YAML while recording duplicate mapping keys."""
    import yaml

    dups: dict[str, list[int]] = collections.defaultdict(list)

    class L(yaml.SafeLoader):
        pass

    def construct_mapping(loader, node, deep=False):
        seen = collections.Counter()
        for k, _v in node.value:
            key = loader.construct_object(k, deep=deep)
            seen[key] += 1
            if seen[key] > 1:
                dups[str(key)].append(k.start_mark.line + 1)
        return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)

    L.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping)
    data = yaml.load(path.read_text(), Loader=L)
    return data, {k: v for k, v in dups.items()}


def resolve_fragment(path: pathlib.Path, fragment: str):
    import yaml

    cur = yaml.safe_load(path.read_text())
    for part in fragment.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return {"resolves": False, "missing_at": part}
    return {"resolves": True, "type": type(cur).__name__}


def main() -> int:
    r: dict = {"probe": "worker-086/F2a-independent-review",
               "started_at": now(), "read_only": True}

    # P1: hash binding + stability window (two samples)
    before = {str(p.relative_to(ROOT)): {"sha256": sha(p), "bytes": p.stat().st_size,
                                         "mtime": datetime.datetime.fromtimestamp(
                                             p.stat().st_mtime).astimezone().replace(
                                             microsecond=0).isoformat()}
              for p in (SCHEMA, F1, F2B, CANON_TAX, AUTH_TAX)}
    r["P1_target_binding"] = {"sampled_at": now(), "before": before,
                              "target_key": "schemas/af_scc_c2_vacuum.yaml"}
    target = before["schemas/af_scc_c2_vacuum.yaml"]["sha256"]

    # P2: duplicate YAML mapping keys + effective/future-dated timestamps
    data, dups = load_dupaware(SCHEMA)
    r["P2_yaml_hygiene"] = {
        "duplicate_keys": dups,
        "duplicate_key_count": sum(len(v) for v in dups.values()),
        "effective_revised_at": data.get("revised_at"),
        "f0_binding_checked_at": (data.get("f0_binding") or {}).get("checked_at"),
        "wall_clock_at_probe": now(),
        "future_dated_revised_at": bool(
            data.get("revised_at") and data["revised_at"] > now()),
        "revision": data.get("revision"),
    }

    # P3: class_contract_pointer fragment resolution against both trees
    pointer = data.get("class_contract_pointer", "")
    path_part, _, frag = pointer.partition("#")
    r["P3_class_contract_pointer"] = {
        "pointer": pointer,
        "canonical": resolve_fragment(CANON_TAX, frag),
        "authoring": resolve_fragment(AUTH_TAX, frag),
        "canonical_sha256": sha(CANON_TAX),
        "authoring_sha256": sha(AUTH_TAX),
        "byte_identical": sha(CANON_TAX) == sha(AUTH_TAX),
    }

    # P4: class-token census and composite-regularity scan with prohibition context
    raw = SCHEMA.read_text()
    lines = raw.splitlines()
    tokens = sorted(set(re.findall(r"AF-[A-Z0-9-]+", raw)))
    composites = []
    for i, line in enumerate(lines, 1):
        if re.search(r"C0\s*(or|/|,)\s*C2|C2\s*(or|/|,)\s*C0", line):
            composites.append({"line": i, "text": line.strip()[:160],
                               "under_prohibition": "composite regularity" in line})
    r["P4_class_tokens"] = {"tokens": tokens, "composite_occurrences": composites}

    # P5: extension_predicate clauses (a)-(f) + D3 resolution + statement_formal symbol
    ext = data.get("extension_predicate") or {}
    defn = str(ext.get("definition", ""))
    conclusion = data.get("conclusion") or {}
    r["P5_extension_predicate"] = {
        "name": ext.get("name"),
        "frozen_regularity": ext.get("frozen_regularity"),
        "frozen_equation_concept": ext.get("frozen_equation_concept"),
        "clauses_present": {c: bool(re.search(r"\(%s\)" % c, defn)) for c in "abcdef"},
        "conclusion_type": conclusion.get("conclusion_type"),
        "i_plus_role": (data.get("i_plus") or {}).get("role"),
        "i_plus_in_conclusion": (data.get("i_plus") or {}).get("in_conclusion"),
        "visibility_role": (data.get("visibility") or {}).get("role"),
        "forbidden_strengthenings": conclusion.get("forbidden_strengthenings"),
        "D3_definition_ref": ((data.get("quantifiers") or {}).get("domains") or {}).get(
            "D3", {}).get("definition_ref"),
        "D3_ref_resolves": ((data.get("quantifiers") or {}).get("domains") or {}).get(
            "D3", {}).get("definition_ref") == "extension_predicate",
        "statement_formal": (data.get("conclusion") or {}).get("statement_formal"),
        "statement_formal_uses_predicate_name": ext.get("name", "") in str(
            (data.get("conclusion") or {}).get("statement_formal", "")),
    }

    # P6: quantifier consistency (no D_gen residue; D0 defined; ordered binders match formal)
    q = data.get("quantifiers") or {}
    formal = str(q.get("formal", ""))
    r["P6_quantifiers"] = {
        "formal": formal,
        "ordered_kinds": [b.get("kind") for b in q.get("ordered", [])],
        "D0_defined": "D0" in (q.get("domains") or {}),
        "D_gen_residue_in_statement_formal": "D_gen" in str(
            (data.get("conclusion") or {}).get("statement_formal", "")),
        "formal_matches_statement": ("exists G_{s,delta}" in formal
                                     and "comeager" in formal
                                     and "not exists a proper future C2 vacuum extension" in formal),
    }

    # P7: shared data-class block across F1/F2a/F2b (load-bearing fields vs annotations)
    def data_class(p):
        import yaml
        d = yaml.safe_load(p.read_text())
        dc = d.get("data_class") or {}
        rc = dc.get("regularity_class") or {}
        sv = rc.get("sobolev_variant") or {}
        ad = dc.get("asymptotic_decay") or {}
        return {
            "load_bearing": {
                "default": (rc.get("default") or "").split(":")[0].strip(),
                "sobolev_s": sv.get("s"), "sobolev_delta": sv.get("delta"),
                "spaces_core": re.sub(r"\s*\(.*\)\s*$", "", sv.get("spaces") or "").strip(),
                "decay_metric": ad.get("metric"),
                "decay_K": ad.get("second_fundamental_form"),
                "parity": (ad.get("parity_conditions") or "").split(";")[0].strip(),
            },
            "annotations": {"sob_status": sv.get("status"), "parity_note": ad.get("parity_conditions")},
        }
    dc_all = {"F1": data_class(F1), "F2a": data_class(SCHEMA), "F2b": data_class(F2B)}
    lb = [json.dumps(v["load_bearing"], sort_keys=True) for v in dc_all.values()]
    r["P7_data_class_shared"] = dict(dc_all)
    r["P7_data_class_shared"]["load_bearing_identical"] = len(set(lb)) == 1
    r["P7_data_class_shared"]["annotation_differences"] = {
        "F1": dc_all["F1"]["annotations"], "F2a": dc_all["F2a"]["annotations"]}

    # P8: f0_binding declared hash vs measured canonical + variant registry coverage
    declared = (data.get("f0_binding") or {}).get("declared_f0_sha256")
    import yaml
    canon = yaml.safe_load(CANON_TAX.read_text())
    canon_variants = sorted({v.get("variant_id") for v in (canon.get("variants") or [])
                             if isinstance(v, dict)})
    reg = json.loads(VARIANT_REGISTRY.read_text())
    reg_ids = sorted({v.get("variant_id") for v in (reg.get("variants") or [])
                      if isinstance(v, dict)})
    cited = set(re.findall(r"variant_id[:\s]+([A-Z0-9]+)", raw))
    cited |= set(re.findall(r"variant-([A-Z0-9]+)\.delta", raw))
    cited = sorted(cited)
    r["P8_bindings"] = {
        "declared_f0_sha256": declared,
        "measured_canonical_f0_sha256": sha(CANON_TAX),
        "declared_matches": declared == sha(CANON_TAX),
        "canonical_inline_variants": canon_variants,
        "variant_registry_ids": reg_ids,
        "variants_cited_in_f2a": cited,
        "cited_absent_from_canonical": [v for v in cited if v not in canon_variants],
    }

    # P9: canonical binding gate, run live
    cp = subprocess.run([sys.executable, str(GATE), str(SCHEMA)], cwd=ROOT,
                        capture_output=True, text=True, timeout=180)
    r["P9_binding_gate"] = {"cmd": f"python3 {GATE.relative_to(ROOT)} {SCHEMA.relative_to(ROOT)}",
                            "exit_code": cp.returncode,
                            "stdout_tail": cp.stdout.strip().splitlines()[-3:],
                            "verdict": "PASS" if cp.returncode == 0 and "PASS" in cp.stdout else "FAIL"}

    # P10: class-separation checker (finding-level) on the target text
    sys.path.insert(0, str(ROOT / "research_map"))
    import class_separation  # noqa: E402
    r["P10_class_separation"] = {"findings": class_separation.findings_for_text(raw, "F2a")}

    # P11: second hash sample = stability window
    after = {str(p.relative_to(ROOT)): sha(p) for p in (SCHEMA, CANON_TAX, AUTH_TAX)}
    r["P11_stability"] = {"sampled_at": now(), "after": after,
                          "target_stable": after["schemas/af_scc_c2_vacuum.yaml"] == target,
                          "taxonomy_pair_stable": after[str(CANON_TAX.relative_to(ROOT))]
                          == before[str(CANON_TAX.relative_to(ROOT))]["sha256"]}

    # P12: D0 domain typing (disjunctive regularity domain vs (s,delta) binder)
    d0 = ((q.get("domains") or {}).get("D0") or {}).get("definition", "")
    ambient = str((data.get("genericity") or {}).get("ambient_space", ""))
    topo = str((data.get("genericity") or {}).get("topology_or_measure", ""))
    r["P12_D0_typing"] = {
        "D0_definition": d0,
        "D0_disjunct_count": len([p for p in re.split(r"\bor\b", d0) if p.strip()]),
        "smooth_with_decay_branch_present": "smooth-with-decay" in d0,
        "smooth_branch_supplies_s_delta_pair": bool(
            re.search(r"smooth-with-decay[^,;]*s\s*>", d0)),
        "binder": [b for b in q.get("ordered", []) if b.get("domain_id") == "D0"],
        "ambient_space_uses_s_delta": "X^{s,delta}" in ambient,
        "ambient_space_defines_smooth_branch_set": bool(
            re.search(r"smooth-with-decay[^.]*\b(set|manifold|space)\b", ambient)),
        "frechet_topology_named_without_ambient_set": (
            "Frechet" in topo and "smooth-with-decay" in topo and "X^{s,delta}" not in topo),
    }

    r["finished_at"] = now()
    r["verdict_inputs"] = {
        "HF-A1_extension_predicate": "resolved" if all(
            r["P5_extension_predicate"]["clauses_present"].values())
        and r["P5_extension_predicate"]["D3_ref_resolves"] else "open",
        "HF-A2_disjunctive_domain": "resolved" if not r["P6_quantifiers"][
            "D_gen_residue_in_statement_formal"] and r["P6_quantifiers"]["D0_defined"] else "open",
        "HF-A3_shared_data_class": "resolved" if r["P7_data_class_shared"][
            "load_bearing_identical"] else "open",
        "HF-A4_binding_gate": r["P9_binding_gate"]["verdict"].lower(),
        "pointer_resolves_against_canonical": r["P3_class_contract_pointer"]["canonical"]["resolves"],
        "yaml_hygiene_defect": r["P2_yaml_hygiene"]["duplicate_key_count"] > 0,
        "cited_variants_absent_from_canonical": r["P8_bindings"]["cited_absent_from_canonical"],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(r, indent=1, sort_keys=False) + "\n")
    print(json.dumps({k: r[k] for k in ("P2_yaml_hygiene", "P3_class_contract_pointer",
                                        "P7_data_class_shared", "P8_bindings",
                                        "P9_binding_gate", "P10_class_separation",
                                        "P11_stability", "verdict_inputs")}, indent=1)[:4000])
    print("\nwrote", OUT.relative_to(ROOT), "sha256", sha(OUT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
