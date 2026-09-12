#!/usr/bin/env python3
"""Deterministic F2a rev12 re-verification probe (worker-088, v2, revision-fair).

Purpose: at one frozen F2a hash, test (a) whether the worker-088 hard failure
HF-088-1 (D0 disjunction ill-typed for the smooth-with-decay branch) is repaired,
and (b) every hash-bound binding that a G-FORM reviewer can mechanically resolve:
class-contract pointer, F0 binding, consistency-evidence binding, conclusion-type
vocabulary, canonical binding gate, class separation, and cross-schema alignment.

Read-only apart from the --out JSON. No network. Every review claim maps to a field.

Usage:
  python3 artifacts/worker-088/f2a_review/check_f2a_v2.py \
      --artifact schemas/af_scc_c2_vacuum.yaml \
      --out artifacts/worker-088/f2a_review/f2a_check.rev12.v2.json
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
SIBLINGS = {"F1": "schemas/af_wcc_vacuum.yaml", "F2b": "schemas/af_scc_c0_vacuum.yaml"}
CLASS_TOKEN = re.compile(r"AF-[A-Z0-9-]{3,}")
GATE_TOOL = "artifacts/formulation/tools/check_class_schema.py"
KEY_MANIFEST = "artifacts/formulation/KEY_MANIFEST.json"
CANONICAL_TAXONOMY = "research_map/formulation_taxonomy.yaml"
AUTHORING_TAXONOMY = "artifacts/formulation/formulation_taxonomy.yaml"
VOCAB_ALIASES = "artifacts/formulation/VOCAB_ALIASES.json"
FROZEN = "artifacts/formulation/FROZEN.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class DuplicateKeyLoader(yaml.SafeLoader):
    """SafeLoader that records duplicate mapping keys instead of last-winning."""


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


def resolve_dotted(doc, pointer: str):
    """Resolve 'file#a.b.c' against a parsed YAML doc; return (file, fragment, value, error)."""
    if not pointer or "#" not in pointer:
        return None, None, None, "no fragment in pointer"
    rel, frag = pointer.split("#", 1)
    p = ROOT / rel
    if not p.is_file():
        return rel, frag, None, "file missing"
    d = yaml.safe_load(p.read_text())
    cur = d
    for part in frag.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return rel, frag, None, f"fragment component {part!r} missing"
    return rel, frag, cur, None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", default="schemas/af_scc_c2_vacuum.yaml")
    ap.add_argument("--out", default="artifacts/worker-088/f2a_review/f2a_check.rev12.v2.json")
    args = ap.parse_args()

    art = (ROOT / args.artifact).resolve()
    text = art.read_text()
    h_before = sha256(art)
    doc, dupes = load_yaml_strict(text)

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

    # --- D0 well-typedness: rev12 tagged-union contract (falsifier of HF-088-1) ---
    d0_def = str((domains.get("D0") or {}).get("definition", ""))
    formal = str(q.get("formal", ""))
    ambient = str(gen.get("ambient_space", ""))
    statement = str(concl.get("statement_formal", ""))
    legacy_pair_binder = bool(re.search(r"\(s\s*,\s*delta\)\s+in\s+D0", formal)) or \
        any(str(r.get("binder", "")).strip() == "(s,delta)" for r in ordered if isinstance(r, dict))
    legacy_disjunction = bool(re.search(r"\bor the smooth-with-decay default\b", d0_def))
    tagged_union_declared = bool(re.search(r"tagged disjoint union|tagged union", d0_def, re.I))
    smooth_branch = bool(re.search(r"\br\s*=\s*smooth\b|smooth \(the smooth-with-decay default\)", d0_def, re.I))
    sobolev_branch = bool(re.search(r"r\s*=\s*\(sobolev", d0_def, re.I))
    per_branch_ambient = bool(re.search(r"Frechet|Fréchet", d0_def)) and bool(re.search(r"weighted Sobolev", d0_def))
    ambient_uses_r = "X^r" in ambient
    binder_is_r = any(str(r.get("binder", "")).strip() == "r" for r in ordered if isinstance(r, dict))
    formal_uses_r = bool(re.search(r"forall\s+r\s+in\s+D0", formal))
    d0_probe = {
        "d0_definition": d0_def,
        "legacy_pair_binder_(s,delta)_in_formal_or_ordered": legacy_pair_binder,
        "legacy_disjunction_phrase": legacy_disjunction,
        "tagged_union_declared": tagged_union_declared,
        "smooth_branch_present": smooth_branch,
        "sobolev_branch_present": sobolev_branch,
        "per_branch_ambient_space_in_D0": per_branch_ambient,
        "ambient_space_uses_X^r": ambient_uses_r,
        "formal_uses_forall_r_in_D0": formal_uses_r,
        "ordered_binder_is_r": binder_is_r,
        "conclusion_statement_formal": statement,
        "publication_issue": doc.get("publication_issue"),
    }
    # HF-088-1 stands iff the class cannot be read as ONE typed statement over D0.
    d0_ill_typed = (legacy_pair_binder or legacy_disjunction) and not (
        tagged_union_declared and smooth_branch and sobolev_branch and per_branch_ambient
        and ambient_uses_r and binder_is_r and formal_uses_r)
    hf088_1_repaired = (not d0_ill_typed) and tagged_union_declared and smooth_branch \
        and sobolev_branch and per_branch_ambient and binder_is_r and formal_uses_r

    # --- binders ---
    domain_ids = set(domains.keys())
    binder_rows = [{"kind": r.get("kind"), "binder": r.get("binder"), "domain_id": r.get("domain_id"),
                    "resolves": r.get("domain_id") in domain_ids} for r in ordered if isinstance(r, dict)]
    unresolved = [r for r in binder_rows if not r["resolves"]]

    # --- class tokens ---
    tokens = Counter()
    for _path, s in walk_strings(doc):
        for t in CLASS_TOKEN.findall(s):
            tokens[t] += 1
    unknown_tokens = sorted(t for t in tokens if t not in FROZEN_CLASSES)

    # --- pointers ---
    ccp = str(doc.get("class_contract_pointer", ""))
    ccsp = str(doc.get("class_contract_supplement_pointer", ""))
    f0 = doc.get("f0_binding", {}) or {}
    sup = str(f0.get("class_contract_supplement", ""))
    ccp_file, ccp_frag, ccp_val, ccp_err = resolve_dotted(doc, ccp)
    sup_id = str(doc.get("class_id", ""))
    supplement_pointer_ok = bool(sup) and f"class_contracts.{sup_id}" in ccsp if ccsp else False
    if ccsp:
        _f, _fr, _v, _e = resolve_dotted(doc, ccsp)
        supplement_pointer_resolves = _e is None
    else:
        # rev11 fallback: supplement referenced as bare path
        supplement_path = ROOT / sup
        supplement_pointer_resolves = supplement_path.is_file()
    pointer_probe = {
        "class_contract_pointer": ccp,
        "class_contract_pointer_resolves_in_canonical_taxonomy": ccp_file == CANONICAL_TAXONOMY and ccp_err is None,
        "class_contract_pointer_error": ccp_err,
        "class_contract_pointer_fragment": ccp_frag,
        "class_contract_supplement_pointer": ccsp or None,
        "class_contract_supplement_resolves": supplement_pointer_resolves,
    }

    # --- f0 binding / consistency evidence ---
    f0_path_rel = str(f0.get("declared_f0_artifact", ""))
    f0_path = ROOT / f0_path_rel
    f0_measured = sha256(f0_path) if f0_path.is_file() else None
    ev_rel = str(f0.get("consistency_evidence", ""))
    ev_path = ROOT / ev_rel
    ev_measured = sha256(ev_path) if ev_path.is_file() else None
    ev_declared = f0.get("consistency_evidence_sha256")
    ev_doc = json.loads(ev_path.read_text()) if ev_path.is_file() else {}
    import os
    f0_probe = {
        "declared_f0_artifact": f0_path_rel,
        "declared_f0_sha256": f0.get("declared_f0_sha256"),
        "measured_f0_sha256": f0_measured,
        "f0_resolves": bool(f0_measured and f0.get("declared_f0_sha256") == f0_measured),
        "consistency_evidence": ev_rel,
        "declared_consistency_sha256": ev_declared,
        "measured_consistency_sha256": ev_measured,
        "consistency_evidence_resolves": bool(ev_measured and ev_declared == ev_measured),
        "consistency_evidence_declared_hash_is_None": ev_declared is None,
        "checked_at": f0.get("checked_at"),
        "evidence_mtime": None,
        "evidence_regenerated_after_checked_at": None,
        "consistency_content": {k: ev_doc.get(k) for k in ("consistent", "errors", "contract_divergences")},
        "rule": f0.get("rule"),
    }
    if ev_path.is_file():
        import datetime
        mt = os.path.getmtime(ev_path)
        f0_probe["evidence_mtime"] = datetime.datetime.fromtimestamp(mt).astimezone().isoformat()
        ck = str(f0.get("checked_at", ""))
        try:
            ck_dt = datetime.datetime.fromisoformat(ck)
            f0_probe["evidence_regenerated_after_checked_at"] = mt > ck_dt.timestamp()
        except ValueError:
            f0_probe["evidence_regenerated_after_checked_at"] = None

    # --- conclusion-type vocabulary ---
    f0_tax = yaml.safe_load((ROOT / CANONICAL_TAXONOMY).read_text())
    allowed = ((f0_tax.get("field_vocabulary") or {}).get("conclusion_type") or {}).get("allowed", [])
    this_token = concl.get("conclusion_type")
    alias_doc = {}
    if (ROOT / VOCAB_ALIASES).is_file():
        alias_doc = json.loads((ROOT / VOCAB_ALIASES).read_text())
    alias_map = alias_doc.get("conclusion_type", {}) if isinstance(alias_doc, dict) else {}
    alias_canonical_keys = sorted(alias_map.keys())
    vocab_probe = {
        "conclusion_type": this_token,
        "f0_allowed": allowed,
        "in_f0_allowed": this_token in allowed,
        "vocab_aliases_path": VOCAB_ALIASES if (ROOT / VOCAB_ALIASES).is_file() else None,
        "vocab_aliases_sha256": sha256(ROOT / VOCAB_ALIASES) if (ROOT / VOCAB_ALIASES).is_file() else None,
        "vocab_aliases_canonical_keys": alias_canonical_keys,
        "token_is_alias_canonical_key": this_token in alias_canonical_keys,
        "f0_token_in_alias_values_for_this_token": this_token in alias_map,  # placeholder, refined below
        "alias_policy": alias_doc.get("policy") if isinstance(alias_doc, dict) else None,
    }
    if this_token in alias_map:
        vocab_probe["alias_values_for_this_token"] = alias_map[this_token]
    conclusion_vocab_conflict = (not vocab_probe["in_f0_allowed"]) and this_token in alias_canonical_keys

    # --- inflation guard ---
    inflation = {
        "conclusion_type": this_token,
        "i_plus_in_conclusion": ip.get("in_conclusion"),
        "forbidden_strengthenings": concl.get("forbidden_strengthenings"),
        "foreign_class_tokens_in_conclusion_block": sorted(
            {t for t in CLASS_TOKEN.findall(json.dumps(concl)) if t != doc.get("class_id")}),
        "wcc_strengthening_tokens": sorted({t for t in CLASS_TOKEN.findall(json.dumps(concl))
                                            if t.startswith("AF-WCC")}),
    }

    # --- canonical binding gate ---
    tool = ROOT / GATE_TOOL
    manifest = ROOT / KEY_MANIFEST
    import datetime
    gate = subprocess.run([sys.executable, str(tool), str(art)], cwd=str(ROOT),
                          capture_output=True, text=True)
    gate_report = {
        "cmd": f"python3 {GATE_TOOL} {args.artifact}",
        "returncode": gate.returncode,
        "stdout": gate.stdout.strip()[:2000],
        "stderr": gate.stderr.strip()[:600],
        "pass": gate.returncode == 0 and "PASS" in gate.stdout,
        "tool_path": GATE_TOOL,
        "tool_sha256": sha256(tool) if tool.is_file() else None,
        "key_manifest_path": KEY_MANIFEST,
        "key_manifest_exists": manifest.is_file(),
        "key_manifest_sha256": sha256(manifest) if manifest.is_file() else None,
        "key_manifest_mtime": datetime.datetime.fromtimestamp(os.path.getmtime(manifest)).astimezone().isoformat()
        if manifest.is_file() else None,
        "r22_skipped_if_manifest_absent": not manifest.is_file(),
    }
    m = re.search(r"failed_rules=(\[.*?\])", gate.stdout)
    gate_report["failed_rules"] = json.loads(m.group(1)) if m else None

    # --- class separation ---
    sys.path.insert(0, str(ROOT / "research_map"))
    import class_separation as cs  # noqa: E402
    sep_findings = cs.findings_for_text(text, args.artifact)

    # --- cross schema ---
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
            "revision": sib.get("revision"),
            "class_id": sib.get("class_id"),
            "conclusion_type": (sib.get("conclusion") or {}).get("conclusion_type"),
            "data_class_keys": sorted(sib_dc.keys()),
            "data_class_key_diff_vs_this": sorted(set(sib_dc) ^ set(dc)),
            "regularity_class_equal": sib_dc.get("regularity_class") == dc.get("regularity_class"),
            "d0_definition": sib_d0,
            "d0_equal_to_this": sib_d0 == d0_def,
        }

    # --- frozen manifest pin ---
    frozen_probe = {"path": FROZEN, "present": (ROOT / FROZEN).is_file()}
    if (ROOT / FROZEN).is_file():
        fz = json.loads((ROOT / FROZEN).read_text())
        files = fz.get("files", {})
        frozen_probe["revision"] = fz.get("revision")
        frozen_probe["frozen_at"] = fz.get("frozen_at")
        frozen_probe["pins_canonical_f2a_path"] = args.artifact in files
        pin = files.get(args.artifact, {})
        frozen_probe["pinned_sha256_for_this_path"] = pin.get("sha256")
        frozen_probe["pin_matches_measured"] = pin.get("sha256") == h_before
        frozen_probe["pins_key_manifest"] = KEY_MANIFEST in files

    # --- verdict ---
    hard = []
    major = []
    if d0_ill_typed:
        hard.append("HF-088-F2a-D0: D0 is not a single well-typed parameterised class (legacy (s,delta) disjunction)")
    if not f0_probe["consistency_evidence_resolves"]:
        hard.append("HF-088-F2a-CE: f0_binding.consistency_evidence_sha256 does not resolve to the measured evidence bytes")
    if conclusion_vocab_conflict:
        hard.append("HF-088-F2a-VOC: conclusion_type is not in the bound F0 allowed vocabulary and is an alias-registry canonical key; needs gate-owner adjudication")
    if not pointer_probe["class_contract_pointer_resolves_in_canonical_taxonomy"]:
        hard.append("HF-088-F2a-PTR: class_contract_pointer does not resolve in the canonical taxonomy")
    if not gate_report["pass"]:
        hard.append("HF-088-F2a-GATE: canonical binding gate does not PASS at this hash")
    if sep_findings:
        hard.append("HF-088-F2a-SEP: class-separation detector reports findings")
    if dupes:
        major.append(f"F-088-F2a-DUP: duplicate YAML keys {dupes}")
    if unknown_tokens:
        major.append(f"F-088-F2a-TOK: unknown class-shaped tokens {unknown_tokens}")
    if not f0_probe["f0_resolves"]:
        major.append("F-088-F2a-F0: declared F0 hash does not match the measured canonical taxonomy")
    if required_missing := sorted(k for k, v in required.items() if not v):
        hard.append(f"HF-088-F2a-FIELDS: missing required fields {required_missing}")

    report = {
        "schema_version": "0.2",
        "artifact_type": "f2a_review_probe",
        "probe": "worker-088/check_f2a_v2.py",
        "node_id": "F2a",
        "class_id": doc.get("class_id"),
        "gate": "G-FORM",
        "actor": "worker-088",
        "artifact": args.artifact,
        "artifact_sha256": h_before,
        "artifact_sha256_after": sha256(art),
        "drifted_during_probe": h_before != sha256(art),
        "artifact_bytes": art.stat().st_size,
        "artifact_mtime": datetime.datetime.fromtimestamp(art.stat().st_mtime).astimezone().isoformat(),
        "artifact_revision": doc.get("revision"),
        "yaml_duplicate_keys": dupes,
        "required_fields": required,
        "required_fields_missing": sorted(k for k, v in required.items() if not v),
        "binder_domains": binder_rows,
        "unresolved_binder_domains": unresolved,
        "d0_probe": d0_probe,
        "d0_ill_typed_for_smooth_branch": d0_ill_typed,
        "hf088_1_repaired": hf088_1_repaired,
        "class_tokens": dict(sorted(tokens.items())),
        "unknown_class_tokens": unknown_tokens,
        "pointer_probe": pointer_probe,
        "f0_binding": f0_probe,
        "vocab_probe": vocab_probe,
        "conclusion_vocab_conflict": conclusion_vocab_conflict,
        "inflation_probe": inflation,
        "binding_gate": gate_report,
        "class_separation_findings": sep_findings,
        "cross_schema": cross,
        "frozen_manifest": frozen_probe,
        "hard_failures": hard,
        "major_findings": major,
        "verdict": "accept" if not hard else "revise",
        "review_status": doc.get("review_status"),
    }
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: report[k] for k in (
        "artifact", "artifact_sha256", "artifact_revision", "drifted_during_probe",
        "yaml_duplicate_keys", "required_fields_missing", "d0_ill_typed_for_smooth_branch",
        "hf088_1_repaired", "unknown_class_tokens", "f0_binding", "vocab_probe",
        "conclusion_vocab_conflict", "binding_gate", "class_separation_findings",
        "hard_failures", "major_findings", "verdict")}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
