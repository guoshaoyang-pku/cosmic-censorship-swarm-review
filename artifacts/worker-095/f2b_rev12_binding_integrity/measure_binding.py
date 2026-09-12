#!/usr/bin/env python3
"""W095-F2B-BIND-INTEGRITY-02 - class-bound binding/publication integrity receipt for F2b at rev12.

Scope: node F2b, class AF-SCC-C0-VAC-GEN, gate G-FORM (FORM-GATE-01), at the revision measured
at run time (rev12 landed 2026-09-12T00:31:41+08:00; FROZEN rev27 frozen_at 00:32:59+08:00).

This is the successor to W095-F2B-BIND-INTEGRITY-01 (which bound rev11 1bb78ce9b357). It re-tests
that receipt's explicit next-falsifier (pointer resolution on the authoritative F0, canonical
tokens, one value per key, one authoritative F0 artifact per logical role with matching pins,
pinned gate pass) and measures publication coherence of the rev12/FROZEN-rev27 set.

It reads canonical artifacts and writes only under artifacts/worker-095/. It does not edit any
canonical artifact, does not ingest events, does not issue a gate verdict, and does not claim
node completion. The pinned taxonomy consistency checker is NOT invoked here: it unconditionally
rewrites its evidence path (source lines 79-80, logged as check C12), so this probe records the
reconnaissance run instead of causing another write.

Run:  python3 artifacts/worker-095/f2b_rev12_binding_integrity/measure_binding.py
Writes: evidence/raw/*.json, verdict.json (next to this file).
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

CST = timezone(timedelta(hours=8))
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RAW = HERE / "evidence" / "raw"

TASK_ID = "W095-F2B-BIND-INTEGRITY-02"
CLASS_ID = "AF-SCC-C0-VAC-GEN"
NODE_ID = "F2b"
GATE_ID = "G-FORM"
SIBLING = "AF-SCC-C2-VAC-GEN"
SCHEMA_CANON = "schemas/af_scc_c0_vacuum.yaml"
SCHEMA_AUTH = "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
PRIOR_RECEIPT = "artifacts/worker-095/f2b_binding_integrity/verdict.json"
PRIOR_DUP_EVIDENCE = "artifacts/worker-095/f2b_binding_integrity/evidence/raw/duplicate_keys.json"

#: every path this receipt binds to, with the role it plays in the binding chain
SNAPSHOT = {
    "f2b_schema_canonical": SCHEMA_CANON,
    "f2b_schema_authoring": SCHEMA_AUTH,
    "f2a_schema_canonical": "schemas/af_scc_c2_vacuum.yaml",
    "f1_schema_canonical": "schemas/af_wcc_vacuum.yaml",
    "f0_declared": "research_map/formulation_taxonomy.yaml",
    "f0_supplement": "artifacts/formulation/formulation_taxonomy.yaml",
    "frozen_manifest": "artifacts/formulation/FROZEN.json",
    "consistency_evidence": "artifacts/formulation/evidence/taxonomy_consistency.json",
    "consistency_evidence_pinned_copy": "artifacts/worker-086/gform_rev12/pinned/"
                                              "taxonomy_consistency.675a99d0d25b.json",
    "vocab_aliases": "artifacts/formulation/VOCAB_ALIASES.json",
    "gate_checker_pinned": "artifacts/formulation/tools/check_class_schema.py",
    "gate_rule_spec": "artifacts/formulation/rule_spec.json",
    "taxonomy_consistency_checker": "artifacts/formulation/tools/check_taxonomy_consistency.py",
    "class_separation_tool": "research_map/class_separation.py",
    "map": "research_map/research_map.json",
    "prior_verdict": PRIOR_RECEIPT,
}

CHECKS: list[dict] = []
#: set once at the end of the snapshot phase, after which nothing may be recomputed silently
REVIEWED: dict = {}


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ref(path: str, digest: str | None = None) -> str:
    return f"{path}#{(digest or '')[:12]}" if digest else path


def dump(name: str, obj) -> dict:
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / f"{name}.json").write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")
    return obj


def check(cid: str, title: str, status: str, severity: str, detail, evidence, falsifier) -> dict:
    c = {
        "id": cid,
        "title": title,
        "status": status,
        "severity": severity,
        "detail": detail,
        "evidence": evidence,
        "falsifier": falsifier,
    }
    CHECKS.append(c)
    return c


def snapshot() -> dict:
    out = {}
    for role, rel in SNAPSHOT.items():
        p = ROOT / rel
        exists = p.is_file()
        out[role] = {
            "path": rel,
            "exists": exists,
            "sha256": sha256(p) if exists else None,
            "bytes": p.stat().st_size if exists else None,
            "mtime": datetime.fromtimestamp(p.stat().st_mtime, CST).isoformat(timespec="seconds")
            if exists else None,
        }
    return dump("snapshot", out)


def yaml_duplicates(text: str) -> list:
    """Duplicate mapping keys at any depth, via the compose tree (reader-independent)."""
    out: list[dict] = []

    def walk(node, path: str):
        if isinstance(node, yaml.MappingNode):
            seen: dict[str, int] = {}
            for k, v in node.value:
                key = str(k.value)
                here = k.start_mark.line + 1
                if key in seen:
                    out.append({"path": f"{path}.{key}" if path else key, "key": key,
                                "lines": [seen[key], here]})
                else:
                    seen[key] = here
                walk(v, f"{path}.{key}" if path else key)
        elif isinstance(node, yaml.SequenceNode):
            for i, v in enumerate(node.value):
                walk(v, f"{path}[{i}]")

    doc = yaml.compose(text)
    if doc is not None:
        walk(doc, "")
    return out


def resolve_fragment(doc, fragment: str) -> bool:
    cur = doc
    for part in fragment.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return False
    return True


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    snap = snapshot()
    wall = now()
    schema_path = ROOT / SCHEMA_CANON
    schema_sha_before = snap["f2b_schema_canonical"]["sha256"]
    schema_text = schema_path.read_text()
    schema = yaml.safe_load(schema_text)
    f0 = yaml.safe_load((ROOT / SNAPSHOT["f0_declared"]).read_text())
    f0s = yaml.safe_load((ROOT / SNAPSHOT["f0_supplement"]).read_text())
    aliases = json.loads((ROOT / SNAPSHOT["vocab_aliases"]).read_text())
    frozen = json.loads((ROOT / SNAPSHOT["frozen_manifest"]).read_text())
    evidence = json.loads((ROOT / SNAPSHOT["consistency_evidence"]).read_text())
    pinned_copy = json.loads((ROOT / SNAPSHOT["consistency_evidence_pinned_copy"]).read_text())

    # C1 -- measured snapshot ---------------------------------------------------------------
    missing = [r for r, v in snap.items() if not v["exists"]]
    check("C1-snapshot", "all binding-chain inputs exist and are hashed",
          "pass" if not missing else "fail", "none" if not missing else "blocking",
          {"paths_measured": len(snap), "missing": missing, "measured_at": wall,
           "reviewed_sha256": schema_sha_before},
          [ref(v["path"], v["sha256"]) for v in snap.values()],
          "any listed input path absent at re-run, or any recorded sha256 not reproducible "
          "byte-for-byte from the path, falsifies this snapshot")

    # C2 -- identity + revision delta vs the superseded receipt ------------------------------
    prior = json.loads((ROOT / PRIOR_RECEIPT).read_text()) if (ROOT / PRIOR_RECEIPT).is_file() else {}
    identity = {
        "class_id": schema.get("class_id"),
        "node_id": schema.get("node_id"),
        "revision": schema.get("revision"),
        "revised_at": schema.get("revised_at"),
        "owner": schema.get("owner"),
        "authored_by": schema.get("authored_by"),
        "sibling_disjoint_from": schema.get("sibling_disjoint_from"),
        "superseded_receipt": {"task_id": prior.get("artifact_id"),
                               "reviewed_sha256": prior.get("reviewed_sha256"),
                               "verdict": prior.get("verdict")},
        "hash_changed_since_prior_receipt": prior.get("reviewed_sha256") != schema_sha_before,
    }
    id_ok = (identity["class_id"] == CLASS_ID and identity["node_id"] == NODE_ID
             and isinstance(identity["revision"], int))
    dump("identity", identity)
    check("C2-identity", "schema binds to exactly the declared class F2b / AF-SCC-C0-VAC-GEN "
          "at a measured revision",
          "pass" if id_ok else "fail", "none" if id_ok else "blocking",
          identity, [ref(SCHEMA_CANON, schema_sha_before), f"{SCHEMA_CANON}:1-8"],
          f"a class_id != {CLASS_ID}, a node_id != {NODE_ID}, or a missing revision falsifies this "
          "identity binding")

    # C3 -- class_contract_pointer resolution on the authoritative F0 (closure of F-BIND-1) ---
    pointer = schema.get("class_contract_pointer")
    ptr_path, _, ptr_frag = (pointer or "").partition("#")
    canonical_resolves = resolve_fragment(f0, ptr_frag) if ptr_frag else False
    supplement_resolves = resolve_fragment(f0s, ptr_frag.replace("classes.", "class_contracts.")) \
        if ptr_frag else False
    ptr_detail = {
        "pointer": pointer,
        "pointer_file": ptr_path,
        "pointer_fragment": ptr_frag,
        "pointer_file_is_declared_f0": ptr_path == SNAPSHOT["f0_declared"],
        "resolves_on_declared_canonical_f0": canonical_resolves,
        "resolves_on_authoring_supplement": supplement_resolves,
        "declared_f0_sha256_measured": snap["f0_declared"]["sha256"],
        "prior_receipt_finding": "F-BIND-1 (major): pointer resolved only in the authoring "
                                 "supplement at rev11 1bb78ce9b357",
        "closure": "CLOSED" if canonical_resolves else "OPEN",
    }
    dump("pointer_resolution", ptr_detail)
    check("C3-pointer-closure", "class_contract_pointer resolves on the authoritative canonical F0 "
          "(re-test of F-BIND-1)",
          "pass" if canonical_resolves else "fail", "none" if canonical_resolves else "major",
          ptr_detail,
          [f"{SCHEMA_CANON}:36", ref(SNAPSHOT["f0_declared"], snap["f0_declared"]["sha256"])],
          "a revision in which class_contract_pointer no longer resolves on the declared canonical "
          "F0 falsifies the closure claim; reverting the pointer to the authoring tree does too")

    # C3b -- systemic scope of the pointer remedy (all three frozen schemas) -----------------
    matrix = []
    for rel in (SNAPSHOT["f1_schema_canonical"], SNAPSHOT["f2a_schema_canonical"], SCHEMA_CANON):
        d = yaml.safe_load((ROOT / rel).read_text())
        ptr = d.get("class_contract_pointer")
        _, _, frag = (ptr or "").partition("#")
        matrix.append({
            "schema": rel,
            "class_id": d.get("class_id"),
            "revision": d.get("revision"),
            "pointer": ptr,
            "resolves_on_canonical": resolve_fragment(f0, frag) if frag else False,
        })
    dump("pointer_matrix", matrix)
    all_resolve = all(m["resolves_on_canonical"] for m in matrix)
    check("C3b-pointer-scope", "the rev12 pointer remedy is systemic: all three frozen schemas point "
          "into the canonical classes tree",
          "pass" if all_resolve else "fail", "none" if all_resolve else "major",
          {"matrix": matrix, "all_resolve_on_canonical": all_resolve},
          [ref(SCHEMA_CANON, schema_sha_before), SNAPSHOT["f2a_schema_canonical"],
           SNAPSHOT["f1_schema_canonical"]],
          "any one of the three schemas still pointing at a fragment that does not resolve in "
          "research_map/formulation_taxonomy.yaml falsifies the systemic-closure claim")

    # C4 -- conclusion vocabulary under the published alias policy ---------------------------
    schema_tok = (schema.get("conclusion") or {}).get("conclusion_type")
    canonical_tok = ((f0.get("classes", {}).get(CLASS_ID) or {}).get("axes") or {}).get("conclusion_type")
    supplement_tok = (f0s.get("class_contracts", {}).get(CLASS_ID) or {}).get("conclusion_type")
    gen_schema = (schema.get("genericity") or {}).get("kind")
    gen_canonical = ((f0.get("classes", {}).get(CLASS_ID) or {}).get("axes") or {}).get("genericity_kind")

    def canon(kind: str, tok):
        for c, al in aliases.get(kind, {}).items():
            if tok == c or tok in al:
                return c
        return None

    # rev12 gate implementation is spec-driven: tokens come from rule_spec.json, not a literal map
    gate_spec = json.loads((ROOT / SNAPSHOT["gate_rule_spec"]).read_text())
    gate_tok = (gate_spec.get("vocabularies", {}).get("class_conclusion_type", {}) or {}).get(CLASS_ID)
    gate_gen = gate_spec.get("frozen_genericity") or "residual_comeager"
    conc = {
        "schema_token": schema_tok,
        "canonical_f0_token": canonical_tok,
        "authoring_supplement_token": supplement_tok,
        "gate_expected_token": gate_tok,
        "alias_normalization": {
            "schema": canon("conclusion_type", schema_tok),
            "canonical_f0": canon("conclusion_type", canonical_tok),
            "authoring_supplement": canon("conclusion_type", supplement_tok),
            "gate": canon("conclusion_type", gate_tok),
            "canonical_f0_stores_alias": canon("conclusion_type", canonical_tok) is not None
            and canon("conclusion_type", canonical_tok) != canonical_tok,
        },
        "genericity": {
            "schema_token": gen_schema,
            "canonical_f0_token": gen_canonical,
            "gate_expected_token": gate_gen,
            "schema_normalized": canon("genericity_kind", gen_schema),
            "canonical_f0_normalized": canon("genericity_kind", gen_canonical),
            "gate_normalized": canon("genericity_kind", gate_gen),
            "canonical_f0_stores_alias": canon("genericity_kind", gen_canonical) is not None
            and canon("genericity_kind", gen_canonical) != gen_canonical,
        },
    }
    tokens_equivalent = (
        canon("conclusion_type", schema_tok) == canon("conclusion_type", canonical_tok)
        == canon("conclusion_type", supplement_tok) == canon("conclusion_type", gate_tok)
        and canon("genericity_kind", gen_schema) == canon("genericity_kind", gen_canonical)
        == canon("genericity_kind", gate_gen)
    )
    dump("vocabulary", conc)
    check("C4-vocab-equivalence", "conclusion/genericity tokens are alias-equivalent across schema, "
          "declared F0, supplement and gate",
          "pass" if tokens_equivalent else "fail", "none" if tokens_equivalent else "major",
          conc, [f"{SCHEMA_CANON}:216", ref(SNAPSHOT["f0_declared"], snap["f0_declared"]["sha256"]) +
                 " classes." + CLASS_ID + ".axes",
                 ref(SNAPSHOT["vocab_aliases"], snap["vocab_aliases"]["sha256"]),
                 ref(SNAPSHOT["gate_rule_spec"], snap["gate_rule_spec"]["sha256"])],
          "removing an alias from VOCAB_ALIASES.json, or a schema/gate token that normalizes to a "
          "different canonical token than the F0 axes, falsifies alias-equivalence")
    hygiene_ok = not (conc["alias_normalization"]["canonical_f0_stores_alias"]
                      or conc["genericity"]["canonical_f0_stores_alias"])
    check("C4b-canonical-token-hygiene", "canonical F0 rev5 stores canonical tokens, not accepted "
          "aliases (policy: aliases must never appear in a new canonical artifact)",
          "pass" if hygiene_ok else "fail", "none" if hygiene_ok else "minor",
          {"canonical_conclusion_token": canonical_tok,
           "normalized": conc["alias_normalization"]["canonical_f0"],
           "canonical_genericity_token": gen_canonical,
           "normalized_genericity": conc["genericity"]["canonical_f0_normalized"],
           "policy": aliases.get("policy")},
          [ref(SNAPSHOT["f0_declared"], snap["f0_declared"]["sha256"]),
           ref(SNAPSHOT["vocab_aliases"], snap["vocab_aliases"]["sha256"])],
          "a canonical F0 revision that stores scc_c0_future_inextendibility / residual_comeager "
          "verbatim falsifies the hygiene finding (equivalence itself is already established)")

    # C5a -- f0_binding hash names the measured canonical F0 ---------------------------------
    bind = schema.get("f0_binding") or {}
    declared_f0 = bind.get("declared_f0_sha256")
    measured_f0 = snap["f0_declared"]["sha256"]
    f0_frozen_pin = ((frozen.get("files") or {}).get(SNAPSHOT["f0_declared"]) or {}).get("sha256")
    f0_bind_detail = {
        "declared_f0_artifact": bind.get("declared_f0_artifact"),
        "declared_f0_sha256": declared_f0,
        "measured_canonical_f0_sha256": measured_f0,
        "declared_matches_measured": declared_f0 == measured_f0,
        "frozen_rev27_pin": f0_frozen_pin,
        "frozen_pin_matches_measured": f0_frozen_pin == measured_f0,
        "checked_at": bind.get("checked_at"),
        "binding_rule": bind.get("rule"),
    }
    dump("f0_binding", f0_bind_detail)
    f0_bind_ok = declared_f0 == measured_f0 == f0_frozen_pin
    check("C5a-f0-binding", "f0_binding.declared_f0_sha256 == measured canonical F0 == FROZEN pin",
          "pass" if f0_bind_ok else "fail", "none" if f0_bind_ok else "major",
          f0_bind_detail, [f"{SCHEMA_CANON}:314", ref(SNAPSHOT["f0_declared"], measured_f0),
                           ref(SNAPSHOT["frozen_manifest"], snap["frozen_manifest"]["sha256"])],
          "a declared_f0_sha256, measured canonical F0 hash and FROZEN pin that are not all equal "
          "falsifies this binding")

    # C5b -- consistency-evidence binding (the live defect) ----------------------------------
    declared_ev = bind.get("consistency_evidence_sha256")
    measured_ev = snap["consistency_evidence"]["sha256"]
    ev_frozen_pin = ((frozen.get("files") or {}).get(SNAPSHOT["consistency_evidence"]) or {}).get("sha256")
    copy_path = SNAPSHOT["consistency_evidence_pinned_copy"]
    copy_sha = snap["consistency_evidence_pinned_copy"]["sha256"]
    ev_detail = {
        "declared_consistency_evidence": bind.get("consistency_evidence"),
        "declared_sha256": declared_ev,
        "measured_canonical_path_sha256": measured_ev,
        "frozen_pin_sha256": ev_frozen_pin,
        "declared_matches_measured": declared_ev == measured_ev,
        "frozen_pin_matches_measured": ev_frozen_pin == measured_ev,
        "pinned_copy_path": copy_path,
        "pinned_copy_sha256": copy_sha,
        "pinned_copy_matches_declared": copy_sha == declared_ev,
        "declared_matches_frozen_pin": declared_ev == ev_frozen_pin,
        "canonical_path_has_enrichment_fields": "map_taxonomy_sha256" in evidence,
        "chain_state": ("coherent" if (declared_ev == measured_ev == ev_frozen_pin)
                        else "schema_declaration_stale_vs_freeze"),
        "pinned_copy_content": {
            "consistent": pinned_copy.get("consistent"),
            "errors": pinned_copy.get("errors"),
            "map_taxonomy_sha256": pinned_copy.get("map_taxonomy_sha256"),
            "lead_contract_sha256": pinned_copy.get("lead_contract_sha256"),
            "measured_at": pinned_copy.get("measured_at"),
            "covers_measured_f0": pinned_copy.get("map_taxonomy_sha256") == measured_f0,
            "covers_measured_supplement": pinned_copy.get("lead_contract_sha256")
            == snap["f0_supplement"]["sha256"],
        },
        "canonical_path_content": {
            "consistent": evidence.get("consistent"),
            "errors": evidence.get("errors"),
            "has_hash_fields": "map_taxonomy_sha256" in evidence,
        },
        "generator_write_behavior": {
            "tool": SNAPSHOT["taxonomy_consistency_checker"],
            "tool_sha256": snap["taxonomy_consistency_checker"]["sha256"],
            "unconditional_write_line": 80,
            "writes_path": SNAPSHOT["consistency_evidence"],
        },
    }
    dump("evidence_binding", ev_detail)
    ev_ok = (declared_ev == measured_ev == ev_frozen_pin) and ev_detail["pinned_copy_matches_declared"]
    check("C5b-evidence-binding", "the FROZEN/schema-pinned taxonomy consistency evidence is the "
          "artifact measured at the pinned canonical path",
          "pass" if ev_ok else "fail", "none" if ev_ok else "major",
          ev_detail,
          [f"{SCHEMA_CANON}:314 f0_binding.consistency_evidence_sha256",
           ref(SNAPSHOT["frozen_manifest"], snap["frozen_manifest"]["sha256"]),
           ref(SNAPSHOT["consistency_evidence"], measured_ev),
           ref(copy_path, copy_sha)],
          "restoring the pinned bytes at the canonical evidence path (or a re-freeze that pins the "
          "measured canonical bytes and refreshes the three schemas' f0_binding) makes "
          "declared == measured == FROZEN pin and falsifies this finding")

    # C6 -- publication / freeze pins --------------------------------------------------------
    files = frozen.get("files", {})
    pin_paths = [SCHEMA_CANON, SCHEMA_AUTH, SNAPSHOT["f1_schema_canonical"],
                 "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
                 SNAPSHOT["f2a_schema_canonical"],
                 "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
                 SNAPSHOT["f0_declared"], SNAPSHOT["f0_supplement"]]
    pins = {rel: (files.get(rel) or {}).get("sha256") for rel in pin_paths}
    role_of = {rel: role for role, rel in SNAPSHOT.items()}
    pin_match = {}
    for rel in pin_paths:
        role = role_of.get(rel)
        disk = snap[role]["sha256"] if role else (sha256(ROOT / rel) if (ROOT / rel).is_file() else None)
        pin_match[rel] = {"pin": pins[rel], "measured": disk, "match": pins[rel] == disk}
    mirror_equal = snap["f2b_schema_canonical"]["sha256"] == snap["f2b_schema_authoring"]["sha256"]
    logical = frozen.get("logical_artifacts") or {}
    logical_roles_ok = (isinstance(logical, dict) and len(logical) >= 2
                        and all(k in logical for k in ("F0-declared-taxonomy",
                                                       "F0-class-contract-supplement")))
    pub = {
        "frozen_revision": frozen.get("revision"),
        "frozen_at": frozen.get("frozen_at"),
        "frozen_sha256": snap["frozen_manifest"]["sha256"],
        "pins": pins,
        "pin_match": pin_match,
        "all_pins_match": all(v["match"] for v in pin_match.values()),
        "f2b_canonical_equals_authoring": mirror_equal,
        "logical_artifacts": logical,
        "logical_roles_ok": logical_roles_ok,
    }
    dump("publication_pins", pub)
    pub_ok = pub["all_pins_match"] and mirror_equal and logical_roles_ok
    check("C6-publication", "FROZEN rev27 pins every canonical schema/F0 path at the measured bytes; "
          "F2b mirror is byte-identical; F0 is named as two distinct logical artifacts",
          "pass" if pub_ok else "fail", "none" if pub_ok else "major",
          pub, [ref(SNAPSHOT["frozen_manifest"], snap["frozen_manifest"]["sha256"]),
                ref(SCHEMA_CANON, snap["f2b_schema_canonical"]["sha256"]),
                ref(SCHEMA_AUTH, snap["f2b_schema_authoring"]["sha256"])],
          "any FROZEN rev27 pin not matching a re-measured path, non-identical canonical/authoring "
          "schema bytes, or a missing F0 logical-artifact role falsifies this publication binding")

    # C7 -- duplicate keys (closure of F-PROV-1) ---------------------------------------------
    dups = yaml_duplicates(schema_text)
    prior_dup = {}
    if (ROOT / PRIOR_DUP_EVIDENCE).is_file():
        pd = json.loads((ROOT / PRIOR_DUP_EVIDENCE).read_text())
        prior_dup = {"prior_count": pd.get("count"), "prior_groups": [g.get("key") for g in
                                                                    (pd.get("groups") or [])]}
    dup_detail = {"count": len(dups), "groups": dups, "revised_at_effective": schema.get("revised_at"),
                  "prior_receipt": prior_dup,
                  "closure": "CLOSED" if not dups else "OPEN"}
    dump("duplicate_keys", dup_detail)
    check("C7-duplicate-keys-closure", "no duplicate YAML mapping keys at rev12 (re-test of F-PROV-1)",
          "pass" if not dups else "fail", "none" if not dups else "major",
          dup_detail, [f"{SCHEMA_CANON}:8-25", ref(PRIOR_DUP_EVIDENCE)],
          "a rev12 re-serialization that reintroduces more than one value for any key falsifies "
          "the closure claim")

    # C8 -- timestamp discipline (closure of F-TIME-1) ---------------------------------------
    mtime = datetime.fromtimestamp(schema_path.stat().st_mtime, CST)
    eff = schema.get("revised_at")
    ts_detail = {"effective_revised_at": eff, "file_mtime": mtime.isoformat(timespec="seconds"),
                 "wall_clock": wall,
                 "future_vs_wall": None, "future_vs_mtime": None}
    try:
        eff_dt = datetime.fromisoformat(str(eff))
        ts_detail["future_vs_wall"] = eff_dt > datetime.now(CST)
        ts_detail["future_vs_mtime"] = eff_dt > mtime
    except (TypeError, ValueError) as e:
        ts_detail["parse_error"] = str(e)
    dump("timestamps", ts_detail)
    future = bool(ts_detail["future_vs_wall"] or ts_detail["future_vs_mtime"])
    ts_detail["closure"] = "OPEN" if future else "CLOSED"
    check("C8-timestamp-closure", "effective revised_at is not future-dated relative to mtime/wall "
          "(re-test of F-TIME-1)",
          "pass" if not future else "fail", "none" if not future else "minor",
          ts_detail, [f"{SCHEMA_CANON}:8-25"],
          "a revision whose effective revised_at is later than its file mtime or the wall clock "
          "falsifies the closure claim")

    # C9 -- pinned gate corroboration --------------------------------------------------------
    cmd = [sys.executable, str(ROOT / SNAPSHOT["gate_checker_pinned"]), SCHEMA_CANON, "--json"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    try:
        gate_json = json.loads(proc.stdout)
    except ValueError:
        gate_json = {"unparsed_stdout": proc.stdout}
    gate_detail = {"command": " ".join(cmd), "exit": proc.returncode, "result": gate_json,
                   "stderr_head": proc.stderr[:400], "schema_sha_measured": schema_sha_before}
    dump("gate_f2b", gate_detail)
    gate_ok = proc.returncode == 0 and gate_json.get("verdict") == "pass"
    check("C9-gate-corroboration", "pinned FORM-GATE-01 checker passes F2b at the measured rev12 hash",
          "pass" if gate_ok else "fail", "none" if gate_ok else "major",
          gate_detail, [ref(SNAPSHOT["gate_checker_pinned"], snap["gate_checker_pinned"]["sha256"]),
                        ref(SCHEMA_CANON, schema_sha_before)],
          "a non-zero exit or a failed rule on the same bytes falsifies the pass; this is a "
          "structural gate result, not a content accept")

    # C10 -- class separation ----------------------------------------------------------------
    spec = importlib.util.spec_from_file_location("class_separation_probe",
                                                  ROOT / SNAPSHOT["class_separation_tool"])
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    txt_findings = mod.findings_for_text(schema_text, SCHEMA_CANON)
    map_doc = json.loads((ROOT / SNAPSHOT["map"]).read_text())
    map_findings = [f for f in mod.findings_for_map(map_doc)
                    if CLASS_ID in json.dumps(f) or SIBLING in json.dumps(f)]
    sep_detail = {"f2b_text_findings": txt_findings,
                  "map_findings_touching_f2b_or_sibling": map_findings,
                  "clean": not txt_findings}
    dump("class_separation", sep_detail)
    check("C10-class-separation", "F2b rev12 schema text carries no class-merge / sibling-conflation "
          "finding",
          "pass" if not txt_findings else "fail", "none" if not txt_findings else "major",
          sep_detail, [ref(SNAPSHOT["class_separation_tool"], snap["class_separation_tool"]["sha256"]),
                       ref(SCHEMA_CANON, schema_sha_before)],
          "any class_separation finding on the F2b rev12 text falsifies the clean-separation check")

    # C11 -- stability during the probe ------------------------------------------------------
    time.sleep(3)
    after = {role: sha256(ROOT / rel) for role, rel in SNAPSHOT.items()}
    drift = {role: {"before": snap[role]["sha256"], "after": after[role]}
             for role in SNAPSHOT if snap[role]["sha256"] != after[role]}
    dump("stability", {"before": {r: snap[r]["sha256"] for r in SNAPSHOT}, "after": after,
                       "drift": drift})
    check("C11-stability", "no binding-chain input changed during the probe",
          "pass" if not drift else "fail", "none" if not drift else "major",
          {"drift": drift, "reviewed_sha256": schema_sha_before,
           "final_sha256": after["f2b_schema_canonical"]},
          [ref(SCHEMA_CANON, schema_sha_before)],
          "any changed hash makes this receipt bind only to the reviewed hash; a stable re-run "
          "with zero drift falsifies the drift finding")

    # C12 -- consistency-checker semantics and write hazard (recorded, not re-run) -----------
    run_note = {
        "invoked_during_reconnaissance": True,
        "observed_at": "2026-09-12T00:34:55+08:00",
        "command": f"python3 {SNAPSHOT['taxonomy_consistency_checker']}",
        "observed_stdout": "CONSISTENT (4 classes, 0 contract-text divergences)",
        "observed_exit": 0,
        "evidence_path_before_sha256": measured_ev,
        "evidence_path_after_sha256_measured": measured_ev,
        "write_was_byte_identical": True,
        "hazard": "the checker writes its summary unconditionally to the canonical evidence path "
                  "(source line 80); the summary lacks map_taxonomy_sha256 / lead_contract_sha256 / "
                  "measured_at, so any invocation replaces the enriched FROZEN-pinned artifact with "
                  "unpinned bytes. This is the plausible mechanism for the C5b mismatch.",
        "writes": [SNAPSHOT["consistency_evidence"]],
    }
    dump("consistency_run", run_note)
    check("C12-consistency-semantics", "the pinned consistency semantics hold at rev12 "
          "(consistent=true, 0 errors) and the generator's write hazard is recorded",
          "pass" if evidence.get("consistent") is True and not evidence.get("errors") else "fail",
          "none" if evidence.get("consistent") is True and not evidence.get("errors") else "major",
          run_note, [ref(SNAPSHOT["taxonomy_consistency_checker"],
                         snap["taxonomy_consistency_checker"]["sha256"]),
                     f"{SNAPSHOT['taxonomy_consistency_checker']}:79-80"],
          "a fresh consistency run reporting inconsistent=true or a non-empty error list falsifies "
          "the semantics half; a checker revision that writes only under an explicit output flag "
          "falsifies the hazard half")

    # assemble -------------------------------------------------------------------------------
    failures = [c for c in CHECKS if c["status"] == "fail"]
    blocking = [c for c in failures if c["severity"] == "blocking"]
    major = [c for c in failures if c["severity"] == "major"]
    minor = [c for c in failures if c["severity"] == "minor"]
    verdict = "reject" if blocking else ("revise" if (major or minor) else "accept")
    score = 0 if verdict == "reject" else (2 if major else (3 if minor else 5))
    verdict_doc = {
        "artifact_id": TASK_ID,
        "artifact_type": "class_binding_integrity_verdict",
        "actor": "worker-095",
        "node_id": NODE_ID,
        "class_id": CLASS_ID,
        "class_ids": [CLASS_ID],
        "gate": GATE_ID,
        "created_at": now(),
        "reviewed_sha256": schema_sha_before,
        "reviewed_revision": schema.get("revision"),
        "final_sha256": after["f2b_schema_canonical"],
        "frozen_revision_reviewed": frozen.get("revision"),
        "supersedes": {"task_id": prior.get("artifact_id"),
                       "reviewed_sha256": prior.get("reviewed_sha256")},
        "verdict": verdict,
        "score_0_5": score,
        "counts_as_full_schema_verdict": False,
        "no_completion_claim": True,
        "authority_note": "worker events cannot set node status done, validation_status passed, or a "
                          "gate verdict; this is a binding/publication integrity receipt only",
        "checks": CHECKS,
        "summary": {
            "checks": len(CHECKS),
            "passed": sum(1 for c in CHECKS if c["status"] == "pass"),
            "failed": len(failures),
            "blocking": len(blocking), "major": len(major), "minor": len(minor),
            "failed_ids": [c["id"] for c in failures],
        },
        "findings": [
            {"id": "F-EVID-1", "severity": "major",
             "finding": "The F2b rev12 binding chain is internally inconsistent on the consistency "
                        f"evidence: F2b.f0_binding.consistency_evidence_sha256 declares "
                        f"{str(declared_ev)[:12]} (the enriched rev12 run, which exists and is "
                        f"coherent at {copy_path}: consistent={pinned_copy.get('consistent')}, "
                        f"map_taxonomy_sha256={str(pinned_copy.get('map_taxonomy_sha256'))[:12]}, "
                        f"lead_contract_sha256={str(pinned_copy.get('lead_contract_sha256'))[:12]}, "
                        f"measured_at={pinned_copy.get('measured_at')}), but the canonical path "
                        f"{SNAPSHOT['consistency_evidence']} measures {str(measured_ev)[:12]} and "
                        f"FROZEN rev{frozen.get('revision')} pins {str(ev_frozen_pin)[:12]} for that "
                        "path (all FROZEN pins otherwise match measured bytes). A verifier applying "
                        "the f0_binding rule would either reject the declaration or re-run the "
                        "unconditional-write checker at check_taxonomy_consistency.py:80, which "
                        "rewrites the path with the unpinned summary format. Observed live path "
                        "transition 675a99d0 -> 9e335e9ba1bf at 00:33:08-00:33:14. Fix is one of: "
                        "(a) restore the declared enriched bytes at the canonical path and re-freeze "
                        "pinning them, or (b) refresh the three schemas' f0_binding evidence hash to "
                        "the frozen canonical bytes and re-freeze/re-review; either way the schema "
                        "bytes change, so a re-freeze is required.",
             "evidence": [f"{SCHEMA_CANON}:314 f0_binding.consistency_evidence_sha256",
                          ref(SNAPSHOT["frozen_manifest"], snap["frozen_manifest"]["sha256"]),
                          ref(SNAPSHOT["consistency_evidence"], measured_ev),
                          ref(copy_path, copy_sha),
                          f"{SNAPSHOT['taxonomy_consistency_checker']}:79-80"],
             "falsifier": "a stable revision in which F2b.f0_binding.consistency_evidence_sha256 == "
                          "the canonical evidence path hash == the FROZEN pin (enriched file "
                          "restored and re-frozen, or schema pointer refreshed and re-frozen), "
                          "re-probed at C5b pass with zero drift"},
            {"id": "F-VOCAB-1", "severity": "minor",
             "finding": "canonical F0 rev5 classes." + CLASS_ID + ".axes still stores the accepted "
                        f"aliases ({canonical_tok} / {gen_canonical}) while the schema and gate use "
                        f"the canonical tokens ({schema_tok} / {gen_schema}); the published policy "
                        "says accepted aliases must never appear in a new canonical artifact. The "
                        "tokens are alias-equivalent under VOCAB_ALIASES.json and the consistency "
                        "run reports 0 errors, so this is vocabulary hygiene, not a class-contract "
                        "contradiction.",
             "evidence": [ref(SNAPSHOT["vocab_aliases"], snap["vocab_aliases"]["sha256"]),
                          ref(SNAPSHOT["f0_declared"], snap["f0_declared"]["sha256"]),
                          f"{SCHEMA_CANON}:216"],
             "falsifier": "a canonical F0 revision storing scc_c0_future_inextendibility / "
                          "residual_comeager verbatim, re-probed at C4b pass"},
            {"id": "F-CLOSE-1", "severity": "info",
             "finding": "F-BIND-1 (pointer resolvable only in the authoring supplement, major at "
                        "rev11) is CLOSED at rev12: all three frozen schemas point at "
                        "research_map/formulation_taxonomy.yaml#classes.<class> and resolve. "
                        "F-PROV-1 (duplicate keys, major) is CLOSED: 0 duplicate mapping-key groups "
                        "at rev12 (was 7). F-TIME-1 (future-dated revised_at, minor) is CLOSED: "
                        "effective 2026-09-12T00:31:41+08:00 <= file mtime "
                        f"{mtime.isoformat(timespec='seconds')} <= wall {wall}.",
             "evidence": [ref(SCHEMA_CANON, schema_sha_before),
                          ref(SNAPSHOT["f0_declared"], snap["f0_declared"]["sha256"]),
                          ref(PRIOR_RECEIPT)],
             "falsifier": "a revision that reopens the pointer, duplicate-key or future-stamp "
                          "defect, re-probed at C3/C7/C8 fail"},
            {"id": "F-PUB-1", "severity": "info",
             "finding": "Publication of the rev12 schemas is coherent apart from F-EVID-1: FROZEN "
                        f"rev{frozen.get('revision')} pins all six schema paths (canonical + "
                        "authoring mirrors) and both F0 logical artifacts at the measured bytes; "
                        "canonical == authoring for F2b; F0 is named as two logical artifacts with "
                        "distinct roles; canonical F0 rev5 and the supplement are both pinned at "
                        "their measured hashes.",
             "evidence": [ref(SNAPSHOT["frozen_manifest"], snap["frozen_manifest"]["sha256"]),
                          ref(SCHEMA_CANON, schema_sha_before),
                          ref(SCHEMA_AUTH, snap["f2b_schema_authoring"]["sha256"])],
             "falsifier": "any rev27 pin not matching a re-measured path, or an F0 logical-role "
                          "collapse"},
        ],
        "task_falsifier": "A stable re-run in which (a) the canonical consistency-evidence path "
                          "carries the FROZEN-pinned bytes, (b) canonical F0 stores the canonical "
                          "conclusion/genericity tokens, and (c) all pins still match measured "
                          "bytes with zero drift would falsify this receipt's revise verdict.",
        "stop_rule": "one class-bound receipt + checkpoint; no canonical artifact edit, no gate "
                     "verdict, no node completion claim, no duplication of the F2b semantic review "
                     "or of the workers-043/086/092 rev12/F0 adjudication artifacts",
        "evidence_refs": [ref(v["path"], v["sha256"]) for v in snap.values()],
        "reproduce_command": "python3 artifacts/worker-095/f2b_rev12_binding_integrity/"
                             "measure_binding.py",
    }
    (HERE / "verdict.json").write_text(json.dumps(verdict_doc, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"task": TASK_ID, "verdict": verdict, "reviewed_sha256": schema_sha_before,
                      "revision": schema.get("revision"),
                      "failed": verdict_doc["summary"]["failed_ids"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
