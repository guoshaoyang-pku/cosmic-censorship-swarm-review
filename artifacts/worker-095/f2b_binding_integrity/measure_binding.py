#!/usr/bin/env python3
"""W095-F2B-BIND-INTEGRITY-01 - class-bound binding/publication integrity probe for F2b.

Scope: node F2b, class AF-SCC-C0-VAC-GEN, gate G-FORM (FORM-GATE-01).
This probe measures; it does not edit any canonical artifact, does not issue a gate
verdict, and does not claim node completion. Every check emits its own falsifier.

Run:  python3 artifacts/worker-095/f2b_binding_integrity/measure_binding.py
Writes: evidence/raw/*.json, verdict.json (next to this file).
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
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

TASK_ID = "W095-F2B-BIND-INTEGRITY-01"
CLASS_ID = "AF-SCC-C0-VAC-GEN"
NODE_ID = "F2b"
GATE_ID = "G-FORM"
SIBLING = "AF-SCC-C2-VAC-GEN"
SCHEMA_CANON = "schemas/af_scc_c0_vacuum.yaml"
SCHEMA_AUTH = "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"

#: every path this receipt binds to, with the role it plays in the binding chain
SNAPSHOT = {
    "f2b_schema_canonical": SCHEMA_CANON,
    "f2b_schema_authoring": SCHEMA_AUTH,
    "f2a_schema_canonical": "schemas/af_scc_c2_vacuum.yaml",
    "f1_schema_canonical": "schemas/af_wcc_vacuum.yaml",
    "f0_declared": "research_map/formulation_taxonomy.yaml",
    "f0_supplement": "artifacts/formulation/formulation_taxonomy.yaml",
    "frozen_manifest": "artifacts/formulation/FROZEN.json",
    "vocab_aliases": "artifacts/formulation/VOCAB_ALIASES.json",
    "gate_checker_pinned": "artifacts/formulation/tools/check_class_schema.py",
    "gate_checker_flash13": "artifacts/flash-13/form_gate/check_class_schema.py",
    "taxonomy_consistency_checker": "artifacts/formulation/tools/check_taxonomy_consistency.py",
    "taxonomy_consistency_evidence": "artifacts/formulation/evidence/taxonomy_consistency.json",
    "class_separation_tool": "research_map/class_separation.py",
    "map": "research_map/research_map.json",
}

CHECKS: list[dict] = []


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
            "mtime": datetime.fromtimestamp(p.stat().st_mtime, CST).isoformat(timespec="seconds") if exists else None,
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
    consistency_evidence = json.loads((ROOT / SNAPSHOT["taxonomy_consistency_evidence"]).read_text())

    # B1 -- measured snapshot ---------------------------------------------------------------
    missing = [r for r, v in snap.items() if not v["exists"]]
    check("B1-snapshot", "all binding-chain inputs exist and are hashed",
          "pass" if not missing else "fail", "none" if not missing else "blocking",
          {"paths_measured": len(snap), "missing": missing, "measured_at": wall},
          [ref(v["path"], v["sha256"]) for v in snap.values()],
          "any listed input path absent at re-run, or any recorded sha256 not reproducible "
          "byte-for-byte from the path, falsifies this snapshot")

    # B2 -- identity ------------------------------------------------------------------------
    identity = {
        "class_id": schema.get("class_id"),
        "node_id": schema.get("node_id"),
        "revision": schema.get("revision"),
        "owner": schema.get("owner"),
        "authored_by": schema.get("authored_by"),
        "sibling_disjoint_from": schema.get("sibling_disjoint_from"),
    }
    id_ok = identity["class_id"] == CLASS_ID and identity["node_id"] == NODE_ID
    check("B2-identity", "schema binds to exactly the declared class F2b / AF-SCC-C0-VAC-GEN",
          "pass" if id_ok else "fail", "none" if id_ok else "blocking",
          identity, [ref(SCHEMA_CANON, schema_sha_before), f"{SCHEMA_CANON}:3"],
          f"a class_id != {CLASS_ID}, a node_id != {NODE_ID}, or a missing revision falsifies "
          "this identity binding")

    # B3 -- class_contract_pointer resolution ------------------------------------------------
    pointer = schema.get("class_contract_pointer")
    ptr_path, _, ptr_frag = (pointer or "").partition("#")
    canonical_resolves = resolve_fragment(f0, ptr_frag) if ptr_frag else False
    supplement_resolves = resolve_fragment(f0s, ptr_frag) if ptr_frag else False
    canonical_has_root = ptr_frag.split(".")[0] in f0 if ptr_frag else False
    authoring_has_root = ptr_frag.split(".")[0] in f0s if ptr_frag else False
    ptr_detail = {
        "pointer": pointer,
        "pointer_file": ptr_path,
        "pointer_fragment": ptr_frag,
        "resolves_on_declared_canonical_f0": canonical_resolves,
        "resolves_on_authoring_supplement": supplement_resolves,
        "declared_f0_top_level_has_class_contracts": canonical_has_root,
        "supplement_top_level_has_class_contracts": authoring_has_root,
        "declared_f0_top_level_keys_sample": sorted(f0.keys())[:12],
        "gate_status": "OPEN_BINDING_DEFECT",
    }
    dump("pointer_resolution", ptr_detail)
    check("B3-contract-pointer", "class_contract_pointer resolves on the authoritative canonical F0",
          "pass" if canonical_resolves else "fail", "none" if canonical_resolves else "major",
          ptr_detail,
          [f"{SCHEMA_CANON}:36", ref(SNAPSHOT["f0_declared"], snap["f0_declared"]["sha256"]),
           ref(SNAPSHOT["f0_supplement"], snap["f0_supplement"]["sha256"])],
          "add class_contracts.<class_id> to the declared canonical F0 at one published hash, or "
          "repoint class_contract_pointer at canonical classes.<class_id> -- either falsifies the "
          "finding that the declared contract is locatable only in the authoring supplement")

    # B3b -- systemic scope of the pointer defect (all three frozen schemas) -----------------
    matrix = []
    for rel in (SNAPSHOT["f1_schema_canonical"], "schemas/af_scc_c2_vacuum.yaml", SCHEMA_CANON):
        d = yaml.safe_load((ROOT / rel).read_text())
        ptr = d.get("class_contract_pointer")
        _, _, frag = (ptr or "").partition("#")
        matrix.append({
            "schema": rel,
            "class_id": d.get("class_id"),
            "pointer": ptr,
            "resolves_on_canonical": resolve_fragment(f0, frag) if frag else False,
            "resolves_on_supplement": resolve_fragment(f0s, frag) if frag else False,
        })
    dump("pointer_matrix", matrix)
    all_authoring_only = all(m["resolves_on_supplement"] and not m["resolves_on_canonical"] for m in matrix)
    check("B3b-pointer-scope", "pointer defect is systemic across the three frozen schemas, not F2b-local",
          "pass" if all_authoring_only else "fail", "none" if all_authoring_only else "major",
          {"matrix": matrix, "all_authoring_only": all_authoring_only},
          [ref(SCHEMA_CANON, schema_sha_before), "schemas/af_scc_c2_vacuum.yaml",
           "schemas/af_wcc_vacuum.yaml"],
          "any one of the three schemas resolving its pointer on the canonical tree falsifies the "
          "systemic-scope claim")

    # B4 -- conclusion vocabulary under the published alias policy ---------------------------
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

    conc = {
        "schema_token": schema_tok,
        "canonical_f0_token": canonical_tok,
        "authoring_supplement_token": supplement_tok,
        "gate_expected_token(canonical)": None,  # filled from checker source below
        "alias_normalization": {
            "canonical_f0_is_alias": canon("conclusion_type", canonical_tok) is not None
            and canon("conclusion_type", canonical_tok) != canonical_tok,
            "canonical_f0_normalized": canon("conclusion_type", canonical_tok),
            "authoring_is_canonical": canon("conclusion_type", supplement_tok) == supplement_tok,
            "schema_is_canonical": canon("conclusion_type", schema_tok) == schema_tok,
        },
        "genericity": {
            "schema_token": gen_schema,
            "canonical_f0_token": gen_canonical,
            "canonical_f0_is_alias": canon("genericity_kind", gen_canonical) is not None
            and canon("genericity_kind", gen_canonical) != gen_canonical,
            "canonical_f0_normalized": canon("genericity_kind", gen_canonical),
        },
        "consistency_checker_verdict": {
            "consistent": consistency_evidence.get("consistent"),
            "errors": consistency_evidence.get("errors"),
            "classes_compared": consistency_evidence.get("classes_compared"),
            "alias_policy": consistency_evidence.get("alias_policy"),
        },
    }
    gate_src = (ROOT / SNAPSHOT["gate_checker_pinned"]).read_text()
    import re as _re
    m = _re.search(r'"' + CLASS_ID + r'":\s*\{[^}]*?"conclusion_type":\s*"([^"]+)"', gate_src, _re.S)
    if m:
        conc["gate_expected_token(canonical)"] = m.group(1)
    tokens_equivalent = (
        canon("conclusion_type", schema_tok) == canon("conclusion_type", canonical_tok)
        == canon("conclusion_type", supplement_tok)
    )
    canonical_uses_alias = conc["alias_normalization"]["canonical_f0_is_alias"]
    dump("vocabulary", conc)
    check("B4-vocab-equivalence", "conclusion/genericity tokens are alias-equivalent across schema, "
          "declared F0, supplement and gate",
          "pass" if tokens_equivalent else "fail", "none" if tokens_equivalent else "major",
          conc, [f"{SCHEMA_CANON}:216", ref(SNAPSHOT["f0_declared"], snap["f0_declared"]["sha256"]) +
                 " classes." + CLASS_ID + ".axes",
                 ref(SNAPSHOT["vocab_aliases"], snap["vocab_aliases"]["sha256"]),
                 ref(SNAPSHOT["taxonomy_consistency_evidence"],
                     snap["taxonomy_consistency_evidence"]["sha256"])],
          "removing the alias from VOCAB_ALIASES.json, or a consistency run reporting a non-empty "
          "error list, falsifies alias-equivalence")
    check("B4b-canonical-token-hygiene", "canonical F0 uses canonical tokens, not accepted aliases "
          "(policy: aliases must never appear in a new canonical artifact)",
          "pass" if not canonical_uses_alias else "fail", "none" if not canonical_uses_alias else "minor",
          {"canonical_conclusion_token": canonical_tok, "normalized": conc["alias_normalization"]
           ["canonical_f0_normalized"], "canonical_genericity_token": gen_canonical,
           "normalized_genericity": conc["genericity"]["canonical_f0_normalized"]},
          [ref(SNAPSHOT["f0_declared"], snap["f0_declared"]["sha256"]),
           ref(SNAPSHOT["vocab_aliases"], snap["vocab_aliases"]["sha256"])],
          "a canonical F0 revision that stores scc_c0_future_inextendibility / residual_comeager "
          "verbatim falsifies the hygiene finding (the equivalence itself is already established)")

    # B5 -- f0_binding -----------------------------------------------------------------------
    bind = schema.get("f0_binding") or {}
    declared = bind.get("declared_f0_sha256")
    measured_f0 = snap["f0_declared"]["sha256"]
    ev_path = bind.get("consistency_evidence")
    ev_measured = snap["taxonomy_consistency_evidence"]["sha256"]
    frozen_ev_pin = (frozen.get("files", {}).get(ev_path) or {}).get("sha256")
    bind_detail = {
        "declared_f0_artifact": bind.get("declared_f0_artifact"),
        "declared_f0_sha256": declared,
        "measured_canonical_f0_sha256": measured_f0,
        "declared_matches_measured": declared == measured_f0,
        "supplement_artifact": bind.get("class_contract_supplement"),
        "supplement_measured_sha256": snap["f0_supplement"]["sha256"],
        "checked_at": bind.get("checked_at"),
        "consistency_evidence_path": ev_path,
        "consistency_evidence_measured_sha256": ev_measured,
        "consistency_evidence_frozen_pin": frozen_ev_pin,
        "consistency_evidence_pin_matches": ev_measured == frozen_ev_pin,
        "binding_note": bind.get("binding_note"),
    }
    dump("f0_binding", bind_detail)
    bind_ok = declared == measured_f0 and ev_measured == frozen_ev_pin
    check("B5-f0-binding", "f0_binding hash names the measured declared-F0 and the pinned "
          "consistency evidence",
          "pass" if bind_ok else "fail", "none" if bind_ok else "major",
          bind_detail, [f"{SCHEMA_CANON}:314", ref(SNAPSHOT["f0_declared"], measured_f0),
                        ref(SNAPSHOT["taxonomy_consistency_evidence"], ev_measured)],
          "a declared_f0_sha256 that differs from a re-measured research_map/formulation_taxonomy.yaml, "
          "or consistency evidence whose hash is not the FROZEN pin, falsifies this binding")

    # B6 -- publication / freeze pins --------------------------------------------------------
    files = frozen.get("files", {})
    pins = {rel: (files.get(rel) or {}).get("sha256") for rel in (SCHEMA_CANON, SCHEMA_AUTH,
                                                                  SNAPSHOT["f0_declared"],
                                                                  SNAPSHOT["f0_supplement"])}
    pub = {
        "frozen_revision": frozen.get("revision"),
        "frozen_at": frozen.get("frozen_at"),
        "pins": pins,
        "pin_matches_measured": {rel: pins[rel] == snap[role]["sha256"] for rel, role in
                                 ((SCHEMA_CANON, "f2b_schema_canonical"), (SCHEMA_AUTH, "f2b_schema_authoring"),
                                  (SNAPSHOT["f0_declared"], "f0_declared"), (SNAPSHOT["f0_supplement"], "f0_supplement"))},
        "f2b_mirror_equal": snap["f2b_schema_canonical"]["sha256"] == snap["f2b_schema_authoring"]["sha256"],
        "f0_pair_divergent": snap["f0_declared"]["sha256"] != snap["f0_supplement"]["sha256"],
        "logical_artifacts": frozen.get("logical_artifacts"),
        "f0_mirror_adjudication_request": frozen.get("f0_mirror_adjudication_request"),
    }
    sysfix = snap["f2b_schema_canonical"]["sha256"] == snap["f2b_schema_authoring"]["sha256"] \
        and all(pub["pin_matches_measured"].values())
    dump("publication_pins", pub)
    check("B6-publication", "FROZEN manifest pins both F2b paths at the measured bytes; F0 pair "
          "divergence is explicitly adjudicated, not silent",
          "pass" if sysfix else "fail", "none" if sysfix else "major",
          pub, [ref(SNAPSHOT["frozen_manifest"], snap["frozen_manifest"]["sha256"]),
                ref(SCHEMA_CANON, snap["f2b_schema_canonical"]["sha256"]),
                ref(SCHEMA_AUTH, snap["f2b_schema_authoring"]["sha256"])],
          "a FROZEN revision that pins F2b at a different hash than disk, or an F0 pair divergence "
          "without a named adjudication route, falsifies this publication binding")
    check("B6b-f0-role-clarity", "one logical role per F0 path, and the freeze names which path is "
          "authoritative for the class contract",
          "pass" if not pub["f0_pair_divergent"] else "fail",
          "none" if not pub["f0_pair_divergent"] else "major",
          {"divergent": pub["f0_pair_divergent"],
           "logical_artifacts": pub["logical_artifacts"],
           "adjudication": pub["f0_mirror_adjudication_request"]},
          [ref(SNAPSHOT["frozen_manifest"], snap["frozen_manifest"]["sha256"])],
          "one F0 path that carries both the canonical adjudication keys and class_contracts at a "
          "single hash, published byte-identically, falsifies the two-logical-artifacts finding")

    # B7 -- duplicate keys -------------------------------------------------------------------
    dups = yaml_duplicates(schema_text)
    dup_detail = {"count": len(dups), "groups": dups,
                  "revised_at_values_last_wins": schema.get("revised_at")}
    dump("duplicate_keys", dup_detail)
    check("B7-duplicate-keys", "no duplicate YAML mapping keys (a strict reader must see one value)",
          "pass" if not dups else "fail", "none" if not dups else "major",
          dup_detail, [f"{SCHEMA_CANON}:8-25", f"{SCHEMA_CANON}:{dups[0]['lines'][0]}" if dups else SCHEMA_CANON],
          "re-serialising with one revised_at per revision (or a list-valued history) and re-running "
          "this probe to count 0 falsifies the lossy-history finding")

    # B8 -- timestamp discipline (CF-14) -----------------------------------------------------
    mtime = datetime.fromtimestamp(schema_path.stat().st_mtime, CST)
    eff = schema.get("revised_at")
    ts_detail = {"effective_revised_at": eff, "file_mtime": mtime.isoformat(timespec="seconds"),
                 "wall_clock": wall, "future_vs_wall": None, "future_vs_mtime": None}
    try:
        eff_dt = datetime.fromisoformat(str(eff))
        ts_detail["future_vs_wall"] = eff_dt > datetime.now(CST)
        ts_detail["future_vs_mtime"] = eff_dt > mtime
    except (TypeError, ValueError) as e:
        ts_detail["parse_error"] = str(e)
    dump("timestamps", ts_detail)
    future = bool(ts_detail["future_vs_wall"] or ts_detail["future_vs_mtime"])
    check("B8-timestamp-discipline", "effective revised_at is not future-dated relative to mtime/wall",
          "pass" if not future else "fail", "none" if not future else "minor",
          ts_detail, [f"{SCHEMA_CANON}:8-25"],
          "a revision whose effective revised_at is <= file mtime and <= wall clock falsifies the "
          "future-dating observation (CF-14 treats future created_at as advisory for ordering)")

    # B9 -- pinned gate corroboration --------------------------------------------------------
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
    check("B9-gate-corroboration", "pinned FORM-GATE-01 checker passes F2b at the measured hash",
          "pass" if gate_ok else "fail", "none" if gate_ok else "major",
          gate_detail, [ref(SNAPSHOT["gate_checker_pinned"], snap["gate_checker_pinned"]["sha256"]),
                        ref(SCHEMA_CANON, schema_sha_before)],
          "a non-zero exit or a failed rule on the same bytes falsifies the pass; this is a "
          "structural gate result, not a content accept")

    # B10 -- class separation ----------------------------------------------------------------
    spec = importlib.util.spec_from_file_location("class_separation_probe",
                                                  ROOT / SNAPSHOT["class_separation_tool"])
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    txt_findings = mod.findings_for_text(schema_text, SCHEMA_CANON)
    map_doc = json.loads((ROOT / SNAPSHOT["map"]).read_text())
    map_findings = [f for f in mod.findings_for_map(map_doc)
                    if CLASS_ID in json.dumps(f) or SIBLING in json.dumps(f)]
    sep_detail = {"f2b_text_findings": txt_findings, "map_findings_touching_f2b_or_sibling": map_findings,
                  "clean": not txt_findings}
    dump("class_separation", sep_detail)
    check("B10-class-separation", "F2b schema text carries no class-merge / sibling-conflation finding",
          "pass" if not txt_findings else "fail", "none" if not txt_findings else "major",
          sep_detail, [ref(SNAPSHOT["class_separation_tool"], snap["class_separation_tool"]["sha256"]),
                       ref(SCHEMA_CANON, schema_sha_before)],
          "any class_separation finding on the F2b text falsifies the clean-separation check")

    # B11 -- stability during the probe ------------------------------------------------------
    time.sleep(3)
    after = {role: sha256(ROOT / rel) for role, rel in SNAPSHOT.items()}
    drift = {role: {"before": snap[role]["sha256"], "after": after[role]}
             for role in SNAPSHOT if snap[role]["sha256"] != after[role]}
    dump("stability", {"before": {r: snap[r]["sha256"] for r in SNAPSHOT}, "after": after, "drift": drift})
    check("B11-stability", "no binding-chain input changed during the probe",
          "pass" if not drift else "fail", "none" if not drift else "major",
          {"drift": drift, "reviewed_sha256": schema_sha_before, "final_sha256": after["f2b_schema_canonical"]},
          [ref(SCHEMA_CANON, schema_sha_before)],
          "any changed hash makes this receipt bind only to the reviewed hash; a stable re-run with "
          "zero drift falsifies the drift finding")

    # assemble -------------------------------------------------------------------------------
    failures = [c for c in CHECKS if c["status"] == "fail"]
    blocking = [c for c in failures if c["severity"] == "blocking"]
    major = [c for c in failures if c["severity"] == "major"]
    minor = [c for c in failures if c["severity"] == "minor"]
    verdict = "reject" if blocking else ("revise" if (major or minor) else "accept")
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
        "final_sha256": after["f2b_schema_canonical"],
        "verdict": verdict,
        "score_0_5": 2 if verdict == "revise" else (0 if verdict == "reject" else 5),
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
            {"id": "F-BIND-1", "severity": "major",
             "finding": "F2b.class_contract_pointer resolves only in the authoring supplement "
                        "(artifacts/formulation/formulation_taxonomy.yaml#class_contracts."
                        "AF-SCC-C0-VAC-GEN); the declared canonical F0 (research_map/"
                        "formulation_taxonomy.yaml) has no class_contracts key, so the declared "
                        "class contract is not locatable in the authoritative artifact of record. "
                        "Systemic: all three frozen schemas point into the supplement. FROZEN rev26 "
                        "now names the two F0 paths as separate logical artifacts and carries a "
                        "pending controller adjudication request (astra-life02-publish-f0).",
             "evidence": [ref(SCHEMA_CANON, schema_sha_before), f"{SCHEMA_CANON}:36",
                          ref(SNAPSHOT["f0_declared"], snap["f0_declared"]["sha256"]),
                          ref(SNAPSHOT["f0_supplement"], snap["f0_supplement"]["sha256"]),
                          ref(SNAPSHOT["frozen_manifest"], snap["frozen_manifest"]["sha256"])],
             "falsifier": "a published revision in which class_contract_pointer resolves inside the "
                          "authoritative F0 artifact (canonical class_contracts added, or pointer "
                          "repointed at canonical classes.<class_id>) while all pins still match"},
            {"id": "F-VOCAB-1", "severity": "minor",
             "finding": "The declared canonical F0 stores alias tokens "
                        f"({canonical_tok} / {gen_canonical}) where the published policy says "
                        "accepted aliases must never appear in a new canonical artifact. They are "
                        "alias-equivalent to the schema/gate canonical tokens "
                        f"({schema_tok} / {gen_schema}) under VOCAB_ALIASES.json and the taxonomy "
                        "consistency checker reports consistent=true with 0 errors; this is "
                        "vocabulary hygiene, NOT a class-contract contradiction (this corrects the "
                        "stronger reading recorded in w095-20260912T002417-blocker-binding).",
             "evidence": [ref(SNAPSHOT["vocab_aliases"], snap["vocab_aliases"]["sha256"]),
                          ref(SNAPSHOT["taxonomy_consistency_evidence"],
                              snap["taxonomy_consistency_evidence"]["sha256"]),
                          ref(SNAPSHOT["f0_declared"], snap["f0_declared"]["sha256"])],
             "falsifier": "a canonical F0 revision storing the canonical tokens verbatim, or a "
                          "consistency run reporting a conclusion_type divergence"},
            {"id": "F-PROV-1", "severity": "major",
             "finding": f"F2b carries {len(dups)} duplicate mapping-key groups (revised_at x8 at "
                        "lines 8-25, plus definition/status/role/refutes/witness_type collisions). "
                        "PyYAML last-wins silently, so the revision history is not machine-readable. "
                        "Independently reported for F1 (worker-094) and F2a (w095 prior receipt).",
             "evidence": [f"{SCHEMA_CANON}:8-25", f"{SCHEMA_CANON}:59-69", f"{SCHEMA_CANON}:193-206"],
             "falsifier": "a revision with one value per key (or list-valued history) re-probed at "
                          "count 0"},
            {"id": "F-TIME-1", "severity": "minor",
             "finding": f"Effective revised_at {eff} is future-dated relative to file mtime "
                        f"({ts_detail['file_mtime']}) and wall clock ({wall}); consistent with the "
                        "CF-14 advisory on future created_at. Ordering by these stamps is unsafe.",
             "evidence": [f"{SCHEMA_CANON}:8-25", ref(SNAPSHOT["map"], snap["map"]["sha256"])],
             "falsifier": "a revision whose effective revised_at is at or before its file mtime"},
            {"id": "F-PUB-1", "severity": "info",
             "finding": "F2b publication itself is clean: canonical and authoring schema bytes are "
                        f"identical at {schema_sha_before[:12]}, FROZEN rev"
                        f"{frozen.get('revision')} pins both paths at that hash, f0_binding names the "
                        "measured declared-F0, and the alias-normalized consistency evidence is the "
                        "pinned artifact. The single divergent publication pair is F0 (declared vs "
                        "supplement), already covered by F-BIND-1/F-BIND-2 and the freeze's "
                        "adjudication request.",
             "evidence": [ref(SNAPSHOT["frozen_manifest"], snap["frozen_manifest"]["sha256"]),
                          ref(SCHEMA_CANON, schema_sha_before), ref(SCHEMA_AUTH, snap["f2b_schema_authoring"]["sha256"])],
             "falsifier": "a FROZEN revision pinning F2b at a hash other than the measured canonical "
                          "bytes, or an unadjudicated F0 divergence"},
        ],
        "task_falsifier": "A single pass in which (a) F2b.class_contract_pointer resolves on the "
                          "authoritative canonical F0, (b) canonical F0 stores the canonical "
                          "conclusion/genericity tokens, (c) one value per YAML key, (d) FROZEN "
                          "names exactly one authoritative F0 artifact per logical role with all "
                          "pins matching measured bytes, and (e) the pinned gate passes -- would "
                          "falsify this receipt's revise verdict.",
        "stop_rule": "one class-bound receipt + checkpoint; no schema edit, no gate verdict, no node "
                     "completion claim, no duplication of the F2b semantic review owned by worker-096",
        "evidence_refs": [ref(v["path"], v["sha256"]) for v in snap.values()],
        "reproduce_command": "python3 artifacts/worker-095/f2b_binding_integrity/measure_binding.py",
    }
    (HERE / "verdict.json").write_text(json.dumps(verdict_doc, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"task": TASK_ID, "verdict": verdict, "reviewed_sha256": schema_sha_before,
                      "failed": verdict_doc["summary"]["failed_ids"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
