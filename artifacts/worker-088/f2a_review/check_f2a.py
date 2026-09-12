#!/usr/bin/env python3
"""Deterministic F2a frozen-revision review probe (worker-088).

Reads one pinned YAML path and emits a machine-readable check report. No network,
no writes other than the --out JSON. Every claim in the accompanying review is
backed by a field of this report.

Usage:
  python3 artifacts/worker-088/f2a_review/check_f2a.py \
      --artifact schemas/af_scc_c2_vacuum.yaml \
      --out artifacts/worker-088/f2a_review/f2a_check.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
FROZEN_CLASSES = {"AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"}
SIBLINGS = {"F1": "schemas/af_wcc_vacuum.yaml",
            "F2b": "schemas/af_scc_c0_vacuum.yaml"}
CLASS_TOKEN = re.compile(r"AF-[A-Z0-9-]{3,}")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class DuplicateKeyLoader(yaml.SafeLoader):
    """SafeLoader that records duplicate mapping keys instead of silently last-winning."""


def load_yaml_strict(text: str):
    dupes: list[str] = []

    def construct_mapping(loader, node, deep=False):
        keys = []
        for k_node, _ in node.value:
            try:
                keys.append(loader.construct_object(k_node, deep=deep))
            except Exception:
                keys.append("<unhashable>")
        counts = Counter(k for k in keys if isinstance(k, str))
        dupes.extend(f"{k} x{n}" for k, n in counts.items() if n > 1)
        return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)

    DuplicateKeyLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping)
    doc = yaml.load(text, Loader=DuplicateKeyLoader)
    return doc, sorted(set(dupes))


def walk_strings(node, path="$"):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from walk_strings(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk_strings(v, f"{path}[{i}]")
    elif isinstance(node, str):
        yield path, node


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", default="schemas/af_scc_c2_vacuum.yaml")
    ap.add_argument("--out", default="artifacts/worker-088/f2a_review/f2a_check.json")
    args = ap.parse_args()

    art = (ROOT / args.artifact).resolve()
    text = art.read_text()
    h_before = sha256(art)
    doc, dupes = load_yaml_strict(text)
    h_after = sha256(art)

    q = doc.get("quantifiers", {}) or {}
    domains = q.get("domains", {}) or {}
    ordered = q.get("ordered", []) or []
    gen = doc.get("genericity", {}) or {}
    reg = doc.get("regularity", {}) or {}
    dc = doc.get("data_class", {}) or {}
    concl = doc.get("conclusion", {}) or {}
    topo = doc.get("topology", {}) or {}
    ip = doc.get("i_plus", {}) or {}
    vis = doc.get("visibility", {}) or {}
    fals = doc.get("falsifier", {}) or {}

    # --- A. required field matrix (assignment acceptance axes) ---
    required = {
        "quantifiers.formal": bool(q.get("formal")),
        "quantifiers.ordered": bool(ordered),
        "quantifiers.domains": bool(domains),
        "topology.spacetime_dimension": topo.get("spacetime_dimension") == 4,
        "topology.slice_topology": bool(topo.get("slice_topology")),
        "topology.conformal_boundary": bool(topo.get("conformal_boundary")),
        "topology.forbidden": bool(topo.get("forbidden")),
        "regularity.data_regularity": bool(reg.get("data_regularity")),
        "regularity.solution_regularity": bool(reg.get("solution_regularity")),
        "regularity.i_plus_regularity": bool(reg.get("i_plus_regularity")),
        "regularity.extension_regularity": bool(reg.get("extension_regularity")),
        "regularity.must_not_conflate": bool(reg.get("must_not_conflate")),
        "genericity.kind": bool(gen.get("kind")),
        "genericity.ambient_space": bool(gen.get("ambient_space")),
        "genericity.topology_or_measure": bool(gen.get("topology_or_measure")),
        "genericity.generic_set": bool(gen.get("generic_set")),
        "genericity.excluded_set": bool(gen.get("excluded_set")),
        "genericity.transfer_failures": bool(gen.get("transfer_failures")),
        "genericity.is_part_of_class": gen.get("is_part_of_class") is True,
        "genericity.class_change_warning": bool(gen.get("class_change_warning")),
        "i_plus.role": bool(ip.get("role")),
        "i_plus.in_conclusion": ip.get("in_conclusion") is False,
        "visibility.role": bool(vis.get("role")),
        "conclusion.conclusion_type": bool(concl.get("conclusion_type")),
        "conclusion.statement_formal": bool(concl.get("statement_formal")),
        "falsifier.tier_1": bool(fals.get("tier_1")),
    }

    # --- B. binder/domain resolution + D0 disjunction probe ---
    domain_ids = set(domains.keys())
    binder_rows = []
    for row in ordered:
        did = row.get("domain_id") if isinstance(row, dict) else None
        binder_rows.append({
            "kind": row.get("kind") if isinstance(row, dict) else None,
            "binder": row.get("binder") if isinstance(row, dict) else None,
            "domain_id": did,
            "resolves": did in domain_ids,
        })
    unresolved = [r for r in binder_rows if not r["resolves"]]

    d0_def = str((domains.get("D0") or {}).get("definition", ""))
    d0_disjuncts = [s.strip() for s in re.split(r",?\s+or\s+", d0_def) if s.strip()]
    smooth_branch = [s for s in d0_disjuncts if "smooth-with-decay" in s]
    sobolev_branch = [s for s in d0_disjuncts if "Sobolev" in s]
    # the binder is the pair (s,delta); a disjunct is instantiable under that binder only
    # if it supplies numeric regularity parameters.
    smooth_supplies_params = bool(re.search(r"\bs\b\s*[><=]|\bdelta\b\s*(in|[><=])", smooth_branch[0])) if smooth_branch else None
    ambient = str(gen.get("ambient_space", ""))
    tom = str(gen.get("topology_or_measure", ""))
    # The ambient_space field is the object comeagerness is measured in. It is written with the
    # (s,delta) index and names the weighted Sobolev product. Test whether ANY ambient object is
    # defined for the un-parameterised smooth-with-decay branch.
    ambient_defines_smooth_branch = "smooth" in ambient.lower()
    tom_mentions_smooth_frechet = ("frechet" in tom.lower() and "smooth" in tom.lower())
    d0_probe = {
        "d0_definition": d0_def,
        "d0_disjunct_count": len(d0_disjuncts),
        "sobolev_branch": bool(sobolev_branch),
        "smooth_with_decay_branch": bool(smooth_branch),
        "smooth_branch_supplies_s_delta_pair": smooth_supplies_params,
        "formal_binder_is_s_delta": "(s,delta)" in str(q.get("formal", "")),
        "ordered_binder_is_s_delta": any(r.get("binder") == "(s,delta)" for r in binder_rows),
        "ambient_space": ambient[:400],
        "ambient_space_mentions_s_delta_index": "X^{s,delta}" in ambient,
        "ambient_space_defines_smooth_branch": ambient_defines_smooth_branch,
        "topology_or_measure_mentions_smooth_frechet": tom_mentions_smooth_frechet,
        "conclusion_statement_formal": concl.get("statement_formal"),
        "conclusion_uses_d0": "D0" in str(concl.get("statement_formal", "")),
    }
    d0_ill_typed = (bool(smooth_branch) and smooth_supplies_params is False
                    and not ambient_defines_smooth_branch)

    # --- C. class-id token scan ---
    tokens = Counter()
    for path, s in walk_strings(doc):
        for t in CLASS_TOKEN.findall(s):
            tokens[t] += 1
    unknown_tokens = sorted(t for t in tokens if t not in FROZEN_CLASSES)
    file_class = doc.get("class_id")

    # --- D. conclusion identity / inflation guards ---
    inflation = {
        "conclusion_type": concl.get("conclusion_type"),
        "i_plus_role": ip.get("role"),
        "i_plus_in_conclusion": ip.get("in_conclusion"),
        "visibility_role": vis.get("role"),
        "forbidden_strengthenings": concl.get("forbidden_strengthenings"),
        "wcc_tokens_in_conclusion_block": sorted({t for t in CLASS_TOKEN.findall(json.dumps(concl))
                                                  if t != file_class}),
    }

    # --- E. f0 binding resolution ---
    f0 = doc.get("f0_binding", {}) or {}
    f0_path = ROOT / str(f0.get("declared_f0_artifact", ""))
    f0_measured = sha256(f0_path) if f0_path.is_file() else None
    f0_probe = {
        "declared_artifact": f0.get("declared_f0_artifact"),
        "declared_sha256": f0.get("declared_f0_sha256"),
        "measured_sha256": f0_measured,
        "resolves": bool(f0_measured and f0.get("declared_f0_sha256") == f0_measured),
        "class_contract_supplement": f0.get("class_contract_supplement"),
    }

    # --- F. cross-schema data-class comparison ---
    cross = {}
    for node, rel in SIBLINGS.items():
        p = ROOT / rel
        if not p.is_file():
            cross[node] = {"present": False}
            continue
        sib = yaml.safe_load(p.read_text())
        sib_dc = sib.get("data_class", {}) or {}
        sib_d0 = str(((sib.get("quantifiers") or {}).get("domains") or {}).get("D0", {}).get("definition", ""))
        cross[node] = {
            "present": True,
            "path": rel,
            "sha256": sha256(p),
            "data_class_keys": sorted(sib_dc.keys()),
            "data_class_key_diff_vs_this": sorted(set(sib_dc) ^ set(dc)),
            "regularity_class_equal": sib_dc.get("regularity_class") == dc.get("regularity_class"),
            "d0_definition": sib_d0,
            "d0_equal": sib_d0 == d0_def,
        }

    # --- G. frozen class-separation detector (local, deterministic) ---
    sys.path.insert(0, str(ROOT / "research_map"))
    import class_separation as cs  # noqa: E402
    sep_findings = cs.findings_for_text(text, args.artifact)

    # --- H. frozen binding gate ---
    gate = subprocess.run(
        [sys.executable, str(ROOT / "artifacts/formulation/tools/check_class_schema.py"), str(art)],
        cwd=str(ROOT), capture_output=True, text=True)
    gate_report = {"cmd": "python3 artifacts/formulation/tools/check_class_schema.py " + args.artifact,
                   "returncode": gate.returncode,
                   "stdout": gate.stdout.strip()[:2000],
                   "stderr": gate.stderr.strip()[:600],
                   "pass": gate.returncode == 0}

    report = {
        "schema_version": "0.1",
        "artifact_type": "f2a_review_probe",
        "node_id": "F2a",
        "class_id": file_class,
        "gate": "G-FORM",
        "actor": "worker-088",
        "artifact": args.artifact,
        "artifact_sha256": h_before,
        "artifact_bytes": art.stat().st_size,
        "artifact_mtime": art.stat().st_mtime,
        "sha256_after_read": h_after,
        "drifted_during_read": h_before != h_after,
        "yaml_duplicate_keys": dupes,
        "required_fields": required,
        "required_fields_missing": sorted(k for k, v in required.items() if not v),
        "binder_domains": binder_rows,
        "unresolved_binder_domains": unresolved,
        "d0_probe": d0_probe,
        "d0_ill_typed_for_smooth_branch": d0_ill_typed,
        "class_tokens": dict(sorted(tokens.items())),
        "unknown_class_tokens": unknown_tokens,
        "inflation_probe": inflation,
        "f0_binding": f0_probe,
        "cross_schema": cross,
        "class_separation_findings": sep_findings,
        "binding_gate": gate_report,
        "review_history_present": "review_history" in doc,
        "unresolved_items": doc.get("unresolved_items"),
    }
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: report.get(k) for k in (
        "artifact", "artifact_sha256", "drifted_during_read", "yaml_duplicate_keys",
        "required_fields_missing", "d0_ill_typed_for_smooth_branch",
        "unknown_class_tokens", "f0_binding", "binding_gate")}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
