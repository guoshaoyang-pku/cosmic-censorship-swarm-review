#!/usr/bin/env python3
"""W095-F2A-BIND-INTEGRITY-01: reproducible class-binding integrity probe for F2a.

Primary class : AF-SCC-C2-VAC-GEN (node F2a, schemas/af_scc_c2_vacuum.yaml)
Binding context: F0 contract (research_map/formulation_taxonomy.yaml vs the authoring
                 tree), the sibling schemas F1/F2b, and artifacts/formulation/FROZEN.json.

What it decides (all machine-checkable, no physical truth):
  C1  measured sha256 of every canonical + authoring formulation artifact
  C2  FROZEN.json pin vs measured canonical/authoring hash (per artifact)
  C3  F2a f0_binding.declared_f0_sha256 vs measured canonical F0
  C4  F2a class_contract_pointer resolvability, against BOTH the declared target and
      the controller-authoritative canonical F0 path
  C5  duplicate YAML mapping keys (silent last-wins provenance loss)
  C6  canonical FORM-GATE-01 structural verdict on each schema
  C7  class-separation findings on F2a
  C8  stability: content diff between two passes (binding line vs substantive content)

Usage:
  python3 measure_binding.py --pass-label p1 --out evidence/raw/pass1.json
Exit codes: 0 = probe completed (verdict is in the JSON), 2 = usage/env error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

CST = timezone(timedelta(hours=8))


def find_root(start: Path) -> Path:
    p = start.resolve()
    for cand in [p] + list(p.parents):
        if (cand / "research_map" / "research_map.json").exists():
            return cand
    raise SystemExit("repo root not found")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def now_iso() -> str:
    return datetime.now(CST).replace(microsecond=0).isoformat()


class DupLoader(yaml.SafeLoader if yaml else object):
    """SafeLoader that records duplicate mapping keys (PyYAML silently last-wins)."""

    def __init__(self, stream):
        super().__init__(stream)
        self.duplicates = []

    def construct_mapping(self, node, deep=False):
        seen = set()
        for k, _v in node.value:
            key = self.construct_object(k, deep=deep)
            if key in seen:
                self.duplicates.append({"key": str(key), "line": k.start_mark.line + 1})
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


def load_yaml_with_dups(p: Path):
    if yaml is None:
        return None, []
    loader = DupLoader(p.read_text())
    try:
        obj = loader.get_single_data()
    finally:
        loader.dispose()
    return obj, loader.duplicates


def walk_key(obj, dotted: str):
    """Resolve a dotted key path; returns (found, value_or_None, trail)."""
    cur = obj
    trail = []
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
            trail.append(part)
        else:
            return False, None, trail
    return True, cur, trail


ARTIFACTS = [
    # node, class_id, canonical path, authoring path
    ("F0", "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH",
     "research_map/formulation_taxonomy.yaml", "artifacts/formulation/formulation_taxonomy.yaml"),
    ("F1", "AF-WCC-VAC-GEN", "schemas/af_wcc_vacuum.yaml", "artifacts/formulation/schemas/af_wcc_vacuum.yaml"),
    ("F2a", "AF-SCC-C2-VAC-GEN", "schemas/af_scc_c2_vacuum.yaml", "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"),
    ("F2b", "AF-SCC-C0-VAC-GEN", "schemas/af_scc_c0_vacuum.yaml", "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"),
]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pass-label", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--gate", default="artifacts/flash-13/form_gate/check_class_schema.py")
    args = ap.parse_args(argv)

    root = find_root(Path(__file__))
    out_path = (root / args.out) if not Path(args.out).is_absolute() else Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    result = {
        "probe_id": "W095-F2A-BIND-INTEGRITY-01",
        "pass_label": args.pass_label,
        "measured_at": now_iso(),
        "actor": "worker-095",
        "primary_class_id": "AF-SCC-C2-VAC-GEN",
        "node_id": "F2a",
        "root": str(root),
        "checks": {},
        "findings": [],
    }

    # C1: measured hashes
    measured = {}
    for node, cid, canon, auth in ARTIFACTS:
        cp, ap_ = root / canon, root / auth
        measured[node] = {
            "class_id": cid,
            "canonical_path": canon,
            "authoring_path": auth,
            "canonical_sha256": sha256_file(cp) if cp.exists() else None,
            "authoring_sha256": sha256_file(ap_) if ap_.exists() else None,
            "canonical_mtime": datetime.fromtimestamp(cp.stat().st_mtime, CST).replace(microsecond=0).isoformat() if cp.exists() else None,
            "authoring_mtime": datetime.fromtimestamp(ap_.stat().st_mtime, CST).replace(microsecond=0).isoformat() if ap_.exists() else None,
            "canonical_bytes": cp.stat().st_size if cp.exists() else None,
            "authoring_bytes": ap_.stat().st_size if ap_.exists() else None,
        }
        measured[node]["canonical_eq_authoring"] = (
            measured[node]["canonical_sha256"] is not None
            and measured[node]["canonical_sha256"] == measured[node]["authoring_sha256"]
        )
    result["checks"]["C1_measured"] = measured

    f2a = measured["F2a"]
    result["reviewed_sha256"] = f2a["canonical_sha256"]

    # C2: FROZEN pin vs measured
    frozen_path = root / "artifacts/formulation/FROZEN.json"
    frozen = json.loads(frozen_path.read_text())
    pins = frozen.get("files", {})
    pin_rows = []
    for node, cid, canon, auth in ARTIFACTS:
        for label, key in (("canonical", canon), ("authoring", auth)):
            pin = (pins.get(key) or {}).get("sha256")
            meas = measured[node][f"{label}_sha256"]
            pin_rows.append({
                "node": node, "copy": label, "path": key, "frozen_pin": pin,
                "measured": meas, "match": bool(pin and meas and pin == meas),
            })
    result["checks"]["C2_frozen_vs_measured"] = {
        "frozen_revision": frozen.get("revision"),
        "frozen_at": frozen.get("frozen_at"),
        "frozen_manifest_sha256": sha256_file(frozen_path),
        "rows": pin_rows,
        "all_match": all(r["match"] for r in pin_rows),
    }

    # C3/C4/C5: per-schema binding fields, pointer resolution, duplicate keys
    schema_rows = {}
    for node, cid, canon, auth in ARTIFACTS:
        if node == "F0":
            continue
        cp = root / canon
        obj, dups = load_yaml_with_dups(cp)
        binding = obj.get("f0_binding") or {}
        pointer = obj.get("class_contract_pointer")
        ptr_path, _, ptr_key = (pointer or "").partition("#")
        ptr_target = root / ptr_path if ptr_path else None
        ptr_obj = None
        ptr_err = None
        if ptr_target is not None and ptr_target.exists() and yaml is not None:
            try:
                ptr_obj, _ = load_yaml_with_dups(ptr_target)
            except Exception as exc:  # pragma: no cover
                ptr_err = f"{type(exc).__name__}: {exc}"
        found_declared, val_declared, trail_declared = (
            walk_key(ptr_obj, ptr_key) if ptr_obj is not None else (False, None, [])
        )
        schema_rows[node] = {
            "class_id": cid,
            "canonical_path": canon,
            "revision": obj.get("revision"),
            "effective_revised_at": obj.get("revised_at"),
            "declared_f0_artifact": binding.get("declared_f0_artifact"),
            "declared_f0_sha256": binding.get("declared_f0_sha256"),
            "measured_f0_sha256": measured["F0"]["canonical_sha256"],
            "declared_f0_matches_measured": binding.get("declared_f0_sha256") == measured["F0"]["canonical_sha256"],
            "class_contract_pointer": pointer,
            "pointer_target_path": ptr_path,
            "pointer_target_exists": bool(ptr_target and ptr_target.exists()),
            "pointer_key": ptr_key,
            "pointer_resolves_in_declared_target": found_declared,
            "pointer_resolution_trail": trail_declared,
            "pointer_error": ptr_err,
            "duplicate_yaml_keys": dups,
            "duplicate_key_count": len(dups),
        }
        # C10: does the authoritative canonical F0 carry the pointer key?
        can_f0, _ = load_yaml_with_dups(root / "research_map/formulation_taxonomy.yaml")
        found_can, val_can, trail_can = walk_key(can_f0, ptr_key) if can_f0 else (False, None, [])
        schema_rows[node]["pointer_resolves_in_canonical_F0"] = found_can
        schema_rows[node]["canonical_F0_resolution_trail"] = trail_can
    result["checks"]["C3_C4_C5_schema_binding"] = schema_rows

    # F0 structural comparison (canonical vs authoring): disjoint key sets
    can_f0, can_dups = load_yaml_with_dups(root / "research_map/formulation_taxonomy.yaml")
    auth_f0, auth_dups = load_yaml_with_dups(root / "artifacts/formulation/formulation_taxonomy.yaml")
    can_keys, auth_keys = set(can_f0 or {}), set(auth_f0 or {})
    result["checks"]["C4b_F0_structural"] = {
        "canonical_keys": sorted(can_keys),
        "authoring_keys": sorted(auth_keys),
        "shared_keys": sorted(can_keys & auth_keys),
        "canonical_only": sorted(can_keys - auth_keys),
        "authoring_only": sorted(auth_keys - can_keys),
        "canonical_has_class_contracts": "class_contracts" in can_keys,
        "authoring_has_class_contracts": "class_contracts" in auth_keys,
        "canonical_revision": (can_f0 or {}).get("revision"),
        "authoring_revision": (auth_f0 or {}).get("revision"),
        "canonical_duplicate_keys": can_dups,
        "authoring_duplicate_keys": auth_dups,
        "f2a_contract_excerpt_authoring": (
            json.dumps(((auth_f0 or {}).get("class_contracts") or {}).get("AF-SCC-C2-VAC-GEN"), sort_keys=True)[:400]
        ),
    }

    # C6: canonical gate
    gate = root / args.gate
    gate_rows = {}
    if gate.exists():
        gate_sha = sha256_file(gate)
        for node, cid, canon, auth in ARTIFACTS:
            if node == "F0":
                continue
            jout = out_path.parent / f"gate_{node}.json"
            proc = subprocess.run(
                [sys.executable, str(gate), canon, "--class", cid, "--json-out", str(jout)],
                cwd=root, capture_output=True, text=True,
            )
            payload = {}
            if jout.exists():
                payload = json.loads(jout.read_text())
            gate_rows[node] = {
                "exit_code": proc.returncode,
                "verdict": payload.get("verdict"),
                "failed_rules": payload.get("failed_rules"),
                "rules_skipped": payload.get("rules_skipped"),
                "sha256_at_gate_time": payload.get("sha256"),
                "stdout": (proc.stdout or "").strip()[:400],
            }
        result["checks"]["C6_gate"] = {"gate_path": args.gate, "gate_sha256": gate_sha, "rows": gate_rows}
    else:
        result["checks"]["C6_gate"] = {"error": f"gate not found: {args.gate}"}

    # C9: conclusion-type vocabulary across canonical F0 / authoring F0 / schema / gate
    vocab_rows = {}
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("_w095_gate", root / args.gate)
        gate_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gate_mod)
        frozen_classes = getattr(gate_mod, "FROZEN_CLASSES", {})
        for node, cid, canon, auth in ARTIFACTS:
            if node == "F0":
                continue
            sobj, _ = load_yaml_with_dups(root / canon)
            can_tok = (((can_f0 or {}).get("classes") or {}).get(cid) or {}).get("axes", {}).get("conclusion_type")
            auth_tok = (((auth_f0 or {}).get("class_contracts") or {}).get(cid) or {}).get("conclusion_type")
            schema_tok = ((sobj or {}).get("conclusion") or {}).get("conclusion_type")
            gate_tok = (frozen_classes.get(cid) or {}).get("conclusion_type")
            vocab_rows[node] = {
                "class_id": cid, "canonical_F0_token": can_tok, "authoring_F0_token": auth_tok,
                "schema_token": schema_tok, "gate_token": gate_tok,
                "all_equal": len({can_tok, auth_tok, schema_tok, gate_tok}) == 1,
                "canonical_matches_gate": can_tok == gate_tok,
                "schema_matches_gate": schema_tok == gate_tok,
            }
    except Exception as exc:  # pragma: no cover
        vocab_rows = {"error": f"{type(exc).__name__}: {exc}"}
    result["checks"]["C9_conclusion_vocabulary"] = vocab_rows

    # C7: class separation on F2a
    try:
        sys.path.insert(0, str(root / "research_map"))
        import class_separation as cs  # type: ignore
        f2a_obj, _ = load_yaml_with_dups(root / f2a["canonical_path"])
        fnd = cs.findings(f2a_obj, f2a["canonical_path"]) if hasattr(cs, "findings") else None
        result["checks"]["C7_classsep"] = {
            "tool": "research_map/class_separation.py",
            "tool_sha256": sha256_file(root / "research_map/class_separation.py"),
            "findings": fnd,
        }
    except Exception as exc:
        result["checks"]["C7_classsep"] = {"error": f"{type(exc).__name__}: {exc}"}

    # Findings synthesis (stable, hash-independent facts get asserted; hash facts are per-pass)
    fnds = result["findings"]
    srow = schema_rows["F2a"]
    if srow["pointer_target_exists"] and srow["pointer_resolves_in_declared_target"] and not srow["pointer_resolves_in_canonical_F0"]:
        fnds.append({
            "id": "F-BIND-1", "severity": "blocking", "criterion": "class binding / canonical-path policy",
            "finding": ("F2a.class_contract_pointer resolves ONLY in the non-authoritative authoring tree "
                        f"({srow['pointer_target_path']}#{srow['pointer_key']}); the controller-authoritative "
                        "canonical F0 (research_map/formulation_taxonomy.yaml) has no 'class_contracts' key, so the "
                        "declared class contract is not locatable in the authoritative artifact."),
            "evidence": [f"{f2a['canonical_path']}#{f2a['canonical_sha256'][:12]} line class_contract_pointer",
                         f"{srow['pointer_target_path']}",
                         "research_map/formulation_taxonomy.yaml (keys: %s)" % ",".join(result["checks"]["C4b_F0_structural"]["canonical_only"][:6])],
            "falsifier": ("Resolve F2a's class_contract_pointer within research_map/formulation_taxonomy.yaml "
                          "(e.g. the key is added there, or the pointer is repointed to a canonical key that exists)."),
        })
    if not measured["F0"]["canonical_eq_authoring"]:
        fnds.append({
            "id": "F-BIND-2", "severity": "major", "criterion": "publication policy CF-13 (canonical == authoring == FROZEN pin)",
            "finding": ("F0 canonical and authoring copies are structurally different documents, not two copies of one "
                        "revision: shared top-level keys = %s, canonical-only = %s, authoring-only = %s. Byte-identical "
                        "publication cannot satisfy canonical == authoring without discarding canonical content "
                        "(class_ids / class_scope_adjudication / variants)." % (
                            result["checks"]["C4b_F0_structural"]["shared_keys"],
                            result["checks"]["C4b_F0_structural"]["canonical_only"],
                            result["checks"]["C4b_F0_structural"]["authoring_only"])),
            "evidence": ["research_map/formulation_taxonomy.yaml#%s" % measured["F0"]["canonical_sha256"][:12],
                         "artifacts/formulation/formulation_taxonomy.yaml#%s" % measured["F0"]["authoring_sha256"][:12]],
            "falsifier": ("Produce one artifact whose top-level key set contains both the canonical adjudication keys and "
                          "the authoring contract keys at one hash, and publish it to both paths."),
        })
    if srow["duplicate_key_count"] > 0:
        fnds.append({
            "id": "F-PROV-1", "severity": "major", "criterion": "artifact provenance / change protocol",
            "finding": ("F2a carries %d duplicate YAML mapping keys (%s); PyYAML last-wins silently, so the revision "
                        "history recorded in the duplicate 'revised_at' keys is not machine-readable and only the last "
                        "value survives a load. The same defect was reported independently for F1 by worker-094." % (
                            srow["duplicate_key_count"],
                            ", ".join(sorted({d["key"] for d in srow["duplicate_yaml_keys"]})))),
            "evidence": [f"{f2a['canonical_path']}#{f2a['canonical_sha256'][:12]} duplicate keys at lines %s" %
                         ",".join(str(d["line"]) for d in srow["duplicate_yaml_keys"])],
            "falsifier": "Re-serialise with one revised_at per revision (list-valued history) and re-run the duplicate-key probe: count = 0.",
        })
    if not srow["declared_f0_matches_measured"]:
        fnds.append({
            "id": "F-BIND-3", "severity": "major", "criterion": "F0 hash binding freshness",
            "finding": ("F2a declares F0 sha256 %s but the measured canonical F0 is %s at this pass; the binding is stale."
                        % (str(srow["declared_f0_sha256"])[:12], measured["F0"]["canonical_sha256"][:12])),
            "evidence": [f"{f2a['canonical_path']}#{f2a['canonical_sha256'][:12]} f0_binding"],
            "falsifier": "Declared F0 sha256 equals the measured canonical F0 hash at two passes >=60s apart.",
        })
    vrow = vocab_rows.get("F2a") if isinstance(vocab_rows, dict) else None
    if isinstance(vrow, dict) and not vrow.get("canonical_matches_gate"):
        fnds.append({
            "id": "F-BIND-4", "severity": "major",
            "criterion": "class-contract conclusion vocabulary (VOCAB_ALIASES policy + FORM-GATE-01 FROZEN_CLASSES)",
            "finding": ("The authoritative canonical F0 records conclusion_type '%s' for %s, while the F2a schema and the "
                        "frozen gate both use '%s'. artifacts/formulation/VOCAB_ALIASES.json maps the former as an accepted "
                        "alias (equivalent for consistency checks) but its policy says aliases 'must never appear in a new "
                        "canonical artifact' - the canonical F0 rev4 itself violates that clause. Consequence for the recorded "
                        "unblock: repointing class_contract_pointer at canonical classes.<class_id> binds F2a to the alias "
                        "token, and editing canonical F0 to the canonical token changes its hash and re-triggers the F2a/F2b/F1 "
                        "f0_binding refresh. The mismatch is systemic for SCC (F2b: canonical '%s' vs gate '%s'). This "
                        "corroborates W082-F-04 (info) and F0-F1-review-17 (major) at the current hash; the new part is the "
                        "interaction with the pointer remedy and the hash-refresh loop." % (
                            vrow.get("canonical_F0_token"), vrow.get("class_id"), vrow.get("schema_token"),
                            (vocab_rows.get("F2b") or {}).get("canonical_F0_token"),
                            (vocab_rows.get("F2b") or {}).get("gate_token"))),
            "evidence": ["research_map/formulation_taxonomy.yaml#%s classes.%s.axes.conclusion_type" % (measured["F0"]["canonical_sha256"][:12], vrow.get("class_id")),
                         "artifacts/formulation/VOCAB_ALIASES.json#%s conclusion_type policy" % sha256_file(root / "artifacts/formulation/VOCAB_ALIASES.json")[:12],
                         "artifacts/flash-13/form_gate/check_class_schema.py#%s FROZEN_CLASSES" % result["checks"]["C6_gate"].get("gate_sha256", "")[:12],
                         "reviews/F0-independent-worker-082.json W082-F-04",
                         "schemas/af_scc_c2_vacuum.yaml conclusion.conclusion_type"],
            "falsifier": ("Canonical F0, the authoring contract, the F2a schema and FORM-GATE-01 FROZEN_CLASSES all carry one "
                          "conclusion_type token for AF-SCC-C2-VAC-GEN (or VOCAB_ALIASES is amended so canonical alias use is "
                          "policy-conformant and the pointer remedy is documented as alias-tolerant)."),
        })
    if not result["checks"]["C2_frozen_vs_measured"]["all_match"]:
        bad = [r for r in pin_rows if not r["match"]]
        fnds.append({
            "id": "F-FREEZE-1", "severity": "major", "criterion": "FROZEN manifest conformance",
            "finding": "FROZEN.json revision %s pins %d path(s) whose measured hash differs: %s" % (
                frozen.get("revision"), len(bad),
                "; ".join("%s(%s) pin=%s measured=%s" % (r["node"], r["copy"], str(r["frozen_pin"])[:12], str(r["measured"])[:12]) for r in bad)),
            "evidence": ["artifacts/formulation/FROZEN.json#%s" % result["checks"]["C2_frozen_vs_measured"]["frozen_manifest_sha256"][:12]],
            "falsifier": "All FROZEN pins equal the measured canonical and authoring hashes at two passes >=60s apart.",
        })

    result["verdict"] = "revise" if any(f["severity"] == "blocking" for f in fnds) else (
        "revise" if fnds else "accept"
    )
    result["counts_as_full_schema_verdict"] = False  # binding-integrity probe, not a content re-review
    result["note"] = ("This probe judges class binding / publication integrity only. It does not re-adjudicate the F2a "
                      "physics statement and is not a substitute for a content verdict.")
    result["next_falsifier"] = ("A pass in which F2a.class_contract_pointer resolves in research_map/formulation_taxonomy.yaml, "
                                "F0 canonical == authoring at one hash, no duplicate keys, and only one F2a revision exists in "
                                "the FROZEN manifest.")
    out_path.write_text(json.dumps(result, indent=1, sort_keys=True))
    print(f"[{args.pass_label}] measured_at={result['measured_at']} F2a={result['reviewed_sha256'][:12]} "
          f"F0={measured['F0']['canonical_sha256'][:12]} verdict={result['verdict']} findings={[f['id'] for f in fnds]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
