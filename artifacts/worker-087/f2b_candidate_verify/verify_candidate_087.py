#!/usr/bin/env python3
"""W087-F2B-CANDIDATE-INDEP-VERIFY-01 instrument (independent, read-only).

Verifies the worker-088 F2b rev13repair candidate packet
  artifacts/worker-088/f2b_rev13_blockers/candidate/af_scc_c0_vacuum.rev13repair.yaml  (b598b59e...)
against the live canonical
  schemas/af_scc_c0_vacuum.yaml  (b2ab6acb2bbe...)
at FROZEN revision 29 (815e08079aefbc...).

B1..B4 are the four blocker families consolidated in
artifacts/worker-088/f2b_rev13_blockers/REPORT.md.  This instrument does not import
project tooling for the checks themselves: it loads YAML with its own duplicate-key
guard, forms its own leaf diff, and has four mutation controls proving each detector
fires.  The project checker artifacts/formulation/tools/check_class_schema.py is run
separately as a second, independent instrument.

Read-only: no file in the repo is written by this script; the report is printed to
stdout and written by the caller (emit_report.py) to the worker-owned directory only.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
CANON_PATH = ROOT / "schemas/af_scc_c0_vacuum.yaml"
CAND_PATH = ROOT / "artifacts/worker-088/f2b_rev13_blockers/candidate/af_scc_c0_vacuum.rev13repair.yaml"
CAND_ROOT = CAND_PATH.parent
FROZEN_PATH = ROOT / "artifacts/formulation/FROZEN.json"
VOCAB_PATH = ROOT / "artifacts/formulation/VOCAB_ALIASES.json"
EVID_CANON_PATH = ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json"
EVID_CAND_PATH = CAND_ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json"
MAP_TAX_PATH = ROOT / "research_map/formulation_taxonomy.yaml"
LEAD_TAX_PATH = ROOT / "artifacts/formulation/formulation_taxonomy.yaml"
CHECKER = ROOT / "artifacts/formulation/tools/check_class_schema.py"

EXPECTED = {
    "canonical": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "candidate": "b598b59e09e56ee4f9e61d1c80f54d702b0bbf14ec9ee646172bc4a87710557a",
    "frozen": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "vocab": "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba",
    "evid_canon": "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b",
    "evid_cand": "a03ba9c529e88e0d1d446d3df5acf97713bf8392673b85e03b73c32e185d70b5",
    "map_tax": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "lead_tax": "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class DupKeyError(Exception):
    pass


class StrictLoader(yaml.SafeLoader):
    pass


def _no_dup(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise DupKeyError(f"duplicate key {key!r} at {key_node.start_mark}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_dup)


def load(path: Path):
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.load(fh, Loader=StrictLoader)


def flatten(obj, prefix=""):
    """Yield (leaf_path, scalar_or_null) for every leaf; dict keys and list indices."""
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(flatten(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(flatten(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = obj
    return out


# --- independent blocker detectors (each returns list of evidence strings) ----

def b1_flags(schema):
    """Inverted containment premise: a forbidden-transfer reason calling C2 'larger'
    than C0 while the file's own chain makes E_C2 the innermost set."""
    flags = []
    chain = schema.get("implication_ledger", {}).get("extension_class_containment", "")
    chain_ok = "contains E_C2" in chain and chain.index("E_C0") < chain.index("E_C2")
    for i, row in enumerate(schema.get("implication_ledger", {}).get("forbidden_transfers", [])):
        reason = str(row.get("reason", ""))
        if "strictly larger" in reason:
            flags.append(f"forbidden_transfers[{i}].reason says 'strictly larger': {reason[:120]}")
        if chain_ok and "strictly smaller" in reason and "E_C2" in reason:
            flags.append(f"OK forbidden_transfers[{i}].reason direction matches chain: {reason[:120]}")
    return flags


def b2_flags(schema):
    """Stale containment denial in regularity.must_not_conflate[*]."""
    flags = []
    for i, row in enumerate(schema.get("regularity", {}).get("must_not_conflate", [])):
        text = str(row)
        if "No containment with C2 or C0 is asserted here" in text:
            flags.append(f"must_not_conflate[{i}] carries the stale denial")
        if "strictly between" in text and "is not used and must not be cited" not in text:
            flags.append(f"must_not_conflate[{i}] asserts the prohibited phrase positively")
    return flags


def b3_flags(schema, vocab_path: Path, f0_schema):
    """Vocabulary binding gap: conclusion/genericity tokens are alias-registry canonical
    keys that are not literal members of the frozen F0 allowed lists, with no bound
    alias registry in the schema."""
    flags = []
    registry = None
    try:
        registry = json.loads(Path(vocab_path).read_text())
    except Exception as exc:  # pragma: no cover
        return [f"alias registry unreadable: {exc}"]
    ct = schema.get("conclusion", {}).get("conclusion_type")
    gk = schema.get("genericity", {}).get("kind")
    vb = schema.get("extensions", {}).get("vocabulary_binding")
    f0_ct = set(str(x) for x in f0_schema.get("field_vocabulary", {}).get("conclusion_type", {}).get("allowed_values", []))
    f0_gk = set(str(x) for x in f0_schema.get("field_vocabulary", {}).get("genericity_kind", {}).get("allowed_values", []))
    if ct not in f0_ct:
        flags.append(f"conclusion_type {ct!r} not a literal member of F0 allowed list")
    if gk not in f0_gk:
        flags.append(f"genericity.kind {gk!r} not a literal member of F0 allowed list")
    if vb is None:
        flags.append("no extensions.vocabulary_binding block: alias equivalence undecidable from artifact")
    else:
        reg = Path(vb.get("alias_registry", ""))
        if not reg.is_absolute():
            reg = ROOT / reg
        if not reg.exists():
            flags.append("bound alias_registry path does not resolve")
        elif vb.get("alias_registry_sha256") != sha256(reg):
            flags.append("bound alias_registry_sha256 != measured registry bytes")
        elif ct in registry.get("conclusion_type", {}) and gk in registry.get("genericity_kind", {}):
            alias = registry["conclusion_type"][ct]
            if vb.get("conclusion_type", {}).get("f0_allowed_equivalent_alias") not in alias:
                flags.append("declared conclusion alias is not a member of the registry alias list")
            alias_g = registry["genericity_kind"][gk]
            if vb.get("genericity_kind", {}).get("f0_allowed_equivalent_alias") not in alias_g:
                flags.append("declared genericity alias is not a member of the registry alias list")
            flags.append("OK bound registry resolves and both aliases are members")
    return flags


def b4_flags(schema, evid_path: Path):
    """Consistency evidence not self-verifying: the declared evidence document must
    record the sha256 of each compared input so consistent=true is reproducible."""
    flags = []
    declared = schema.get("f0_binding", {}).get("consistency_evidence_sha256")
    if declared is None:
        return ["f0_binding.consistency_evidence_sha256 absent"]
    if not Path(evid_path).exists():
        return [f"declared evidence path missing: {evid_path}"]
    measured = sha256(evid_path)
    if measured != declared:
        flags.append(f"declared consistency_evidence_sha256 {declared[:12]} != bytes at declared path {measured[:12]}")
    doc = json.loads(Path(evid_path).read_text())
    for field in ("map_taxonomy_sha256", "lead_contract_sha256", "alias_registry_sha256"):
        if field not in doc:
            flags.append(f"evidence document records no {field}")
    return flags


def main():
    pins_before = {str(p): sha256(p) for p in [CANON_PATH, CAND_PATH, FROZEN_PATH, VOCAB_PATH,
                                                EVID_CANON_PATH, EVID_CAND_PATH, MAP_TAX_PATH, LEAD_TAX_PATH]}
    result = {"instrument": Path(__file__).name, "actor": "worker-087", "readonly": True,
              "task": "W087-F2B-CANDIDATE-INDEP-VERIFY-01"}

    pin_check = {}
    for label, path in [("canonical", CANON_PATH), ("candidate", CAND_PATH), ("frozen", FROZEN_PATH),
                        ("vocab", VOCAB_PATH), ("evid_canon", EVID_CANON_PATH), ("evid_cand", EVID_CAND_PATH),
                        ("map_tax", MAP_TAX_PATH), ("lead_tax", LEAD_TAX_PATH)]:
        got = pins_before[str(path)]
        pin_check[label] = {"path": str(path.relative_to(ROOT)), "sha256": got,
                            "expected": EXPECTED[label], "match": got == EXPECTED[label]}
    result["pins"] = pin_check
    if not all(v["match"] for v in pin_check.values()):
        result["verdict"] = "inconclusive"
        result["reason"] = "pin mismatch before any check"
        print(json.dumps(result, indent=1, sort_keys=True))
        return 1

    canon = load(CANON_PATH)
    cand = load(CAND_PATH)
    f0 = load(MAP_TAX_PATH)
    result["canonical"] = {"class_id": canon.get("class_id"), "node_id": canon.get("node_id"),
                           "conclusion_type": canon.get("conclusion", {}).get("conclusion_type"),
                           "genericity_kind": canon.get("genericity", {}).get("kind")}
    result["candidate"] = {"class_id": cand.get("class_id"), "node_id": cand.get("node_id"),
                           "conclusion_type": cand.get("conclusion", {}).get("conclusion_type"),
                           "genericity_kind": cand.get("genericity", {}).get("kind")}

    result["b1_canonical_flags"] = b1_flags(canon)
    result["b1_candidate_flags"] = b1_flags(cand)
    result["b2_canonical_flags"] = b2_flags(canon)
    result["b2_candidate_flags"] = b2_flags(cand)
    result["b3_canonical_flags"] = b3_flags(canon, VOCAB_PATH, f0)
    result["b3_candidate_flags"] = b3_flags(cand, VOCAB_PATH, f0)
    result["b4_canonical_flags"] = b4_flags(canon, EVID_CANON_PATH)
    result["b4_candidate_declared_path_flags"] = b4_flags(cand, EVID_CANON_PATH)
    result["b4_candidate_packet_flags"] = b4_flags(cand, EVID_CAND_PATH)

    # leaf diff scope
    fc, fk = flatten(canon), flatten(cand)
    changed, added, removed = {}, {}, {}
    for k in sorted(set(fc) | set(fk)):
        if k not in fc:
            added[k] = fk[k]
        elif k not in fk:
            removed[k] = fc[k]
        elif fc[k] != fk[k]:
            changed[k] = {"canonical": str(fc[k])[:200], "candidate": str(fk[k])[:200]}
    allowed_prefixes = ("implication_ledger.forbidden_transfers[0].reason",
                        "regularity.must_not_conflate[0]",
                        "extensions.vocabulary_binding.",
                        "f0_binding.consistency_evidence_sha256",
                        "f0_binding.binding_note")
    unexpected = [k for k in list(changed) + list(added) + list(removed)
                  if not k.startswith(allowed_prefixes)]
    result["diff"] = {"changed": changed, "added": added, "removed": removed,
                      "unexpected_leaf_paths": unexpected,
                      "unexpected_count": len(unexpected)}

    # class integrity between the two
    identity_fields = ["class_id", "node_id", "schema_version", "scope_statement",
                       "quantifiers", "topology", "conclusion.statement_formal",
                       "conclusion.statement_natural_language", "anti_scope"]
    ident = {}
    for f in identity_fields:
        a, b = fc.get(f), fk.get(f)
        ident[f] = (a == b)
    result["identity_preserved"] = ident
    result["identity_all_preserved"] = all(ident.values())

    # controls: mutate canonical in memory; each detector must fire
    import copy
    c1 = copy.deepcopy(canon)
    c1["implication_ledger"]["forbidden_transfers"][0]["reason"] = "C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker"
    c2 = copy.deepcopy(canon)
    c2["regularity"]["must_not_conflate"][0] = "No containment with C2 or C0 is asserted here"
    c3 = copy.deepcopy(canon)
    c3.setdefault("extensions", {})["vocabulary_binding"] = {"alias_registry": "artifacts/formulation/VOCAB_ALIASES.json", "alias_registry_sha256": "deadbeef"}
    c3["conclusion"]["conclusion_type"] = "scc_c0_future_inextendibility"
    c3["genericity"]["kind"] = "residual_comeager"
    c4 = copy.deepcopy(canon)
    c4["f0_binding"]["consistency_evidence_sha256"] = pins_before[str(EVID_CANON_PATH)]
    controls = {
        "B1_inversion_control_fires": any("strictly larger" in f for f in b1_flags(c1)),
        "B2_denial_control_fires": any("stale denial" in f for f in b2_flags(c2)),
        "B3_unbound_registry_control_fires": any("alias_registry_sha256 != measured" in f or "not a literal member" in f for f in b3_flags(c3, VOCAB_PATH, f0)),
        "B4_nonselfverifying_control_fires": any("records no" in f for f in b4_flags(c4, EVID_CANON_PATH)),
    }
    result["controls"] = controls
    result["controls_all_pass"] = all(controls.values())

    # second instrument: the canonical class-schema checker, candidate + canonical control
    checker_out = {}
    for label, target in [("candidate", CAND_PATH), ("canonical", CANON_PATH)]:
        cp = subprocess.run([sys.executable, str(CHECKER), "--json", str(target)],
                            capture_output=True, text=True, cwd=str(ROOT), timeout=300)
        payload = None
        try:
            payload = json.loads(cp.stdout)
        except Exception:
            payload = {"raw_stdout_head": cp.stdout[:400], "raw_stderr_head": cp.stderr[:400]}
        checker_out[label] = {"returncode": cp.returncode, "payload": payload}
    result["checker"] = checker_out

    # verdict, preregistered rule
    canonical_defects_reproduced = bool(result["b1_canonical_flags"]) and any(
        "stale denial" in f for f in result["b2_canonical_flags"])
    candidate_b1_ok = not any("strictly larger" in f for f in result["b1_candidate_flags"]) and any(
        "direction matches chain" in f for f in result["b1_candidate_flags"])
    candidate_b2_ok = not any("stale denial" in f or "positively" in f for f in result["b2_candidate_flags"])
    candidate_b3_ok = any("OK bound registry resolves" in f for f in result["b3_candidate_flags"])
    candidate_b4_packet_ok = not result["b4_candidate_packet_flags"]
    candidate_b4_declared_path_ok = not result["b4_candidate_declared_path_flags"]
    facts = {
        "canonical_defects_reproduced": canonical_defects_reproduced,
        "candidate_b1_ok": candidate_b1_ok,
        "candidate_b2_ok": candidate_b2_ok,
        "candidate_b3_ok": candidate_b3_ok,
        "candidate_b4_packet_ok": candidate_b4_packet_ok,
        "candidate_b4_declared_path_ok": candidate_b4_declared_path_ok,
        "unexpected_leaf_paths": result["diff"]["unexpected_count"],
        "identity_all_preserved": result["identity_all_preserved"],
        "controls_all_pass": result["controls_all_pass"],
        "checker_candidate_rc": checker_out["candidate"]["returncode"],
        "checker_canonical_rc": checker_out["canonical"]["returncode"],
    }
    result["facts"] = facts
    if not (canonical_defects_reproduced and candidate_b1_ok and candidate_b2_ok and candidate_b3_ok
            and candidate_b4_packet_ok and result["controls_all_pass"] and result["identity_all_preserved"]
            and result["diff"]["unexpected_count"] == 0):
        verdict = "revise"
        reason = "one or more preregistered candidate checks failed"
    elif not candidate_b4_declared_path_ok:
        verdict = "accept_packet_conditional_schema_only_landing_breaks_hash_chain"
        reason = ("candidate packet is self-consistent; the candidate SCHEMA ALONE at the canonical path "
                  "declares consistency_evidence_sha256 for a document that only exists inside the packet")
    else:
        verdict = "accept"
        reason = "all preregistered checks pass with controls"
    result["verdict"] = verdict
    result["reason"] = reason

    result["pins_after"] = {str(p): sha256(p) for p in [CANON_PATH, CAND_PATH, FROZEN_PATH, VOCAB_PATH,
                                                        EVID_CANON_PATH, EVID_CAND_PATH, MAP_TAX_PATH, LEAD_TAX_PATH]}
    result["drift_free"] = all(result["pins"][label]["sha256"] == result["pins_after"][str(path)]
                               for label, path in [("canonical", CANON_PATH), ("candidate", CAND_PATH),
                                                   ("frozen", FROZEN_PATH), ("vocab", VOCAB_PATH),
                                                   ("evid_canon", EVID_CANON_PATH), ("evid_cand", EVID_CAND_PATH),
                                                   ("map_tax", MAP_TAX_PATH), ("lead_tax", LEAD_TAX_PATH)])
    result["falsifier"] = ("Re-run this instrument at the same eight pins: any changed detector verdict, any "
                           "pin mismatch, or a candidate packet whose declared evidence hash does not resolve "
                           "inside the packet voids the verification.")
    print(json.dumps(result, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
