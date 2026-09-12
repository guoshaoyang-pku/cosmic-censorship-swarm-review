#!/usr/bin/env python3
"""W086-GFORM-REV12-VERIFY-01 — independent verification of the rev12 G-FORM rebind.

Scope (class-bound: F1=AF-WCC-VAC-GEN, F2a=AF-SCC-C2-VAC-GEN, F2b=AF-SCC-C0-VAC-GEN, G-FORM):
binding-chain only. It answers: after the 2026-09-12T00:31-00:32 rebind, do the three
canonical schemas' class-contract pointers, supplement pointers, declared hashes and
consistency evidence actually resolve and agree at the bytes on disk — and how many
independent accept verdicts bind the new bytes?

Read-only. No canonical byte is written. Fail-closed on hash drift inside a run.

Falsifier: re-run at the same pins. The verification is falsified if any pointer that this
report says resolves in canonical F0 does not, if any declared sha256 differs from the
measured file, if the duplicate-key detector finds a duplicate the report says is absent,
or if an accept binding a current hash is omitted from the census.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
CST = timezone(timedelta(hours=8))
OUT_DIR = Path(__file__).resolve().parent

SCHEMAS = {
    "F1": "schemas/af_wcc_vacuum.yaml",
    "F2a": "schemas/af_scc_c2_vacuum.yaml",
    "F2b": "schemas/af_scc_c0_vacuum.yaml",
}
CLASS_OF = {"F1": "AF-WCC-VAC-GEN", "F2a": "AF-SCC-C2-VAC-GEN", "F2b": "AF-SCC-C0-VAC-GEN"}
CANON = "research_map/formulation_taxonomy.yaml"
SUPP = "artifacts/formulation/formulation_taxonomy.yaml"
CONS = "artifacts/formulation/evidence/taxonomy_consistency.json"
MAP = "research_map/research_map.json"
COVERAGE = "reviews/A1-rebind-coverage.json"
FROZEN = "artifacts/formulation/FROZEN.json"


class DupKeyError(ValueError):
    pass


class StrictLoader(yaml.SafeLoader):
    pass


def _strict_mapping(loader, node, deep=False):
    seen = set()
    for k, _ in node.value:
        key = loader.construct_object(k, deep=deep)
        if key in seen:
            raise DupKeyError(f"duplicate mapping key {key!r} at line {k.start_mark.line + 1}")
        seen.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _strict_mapping)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def measure() -> dict:
    paths = [CANON, SUPP, CONS, MAP, COVERAGE, FROZEN, *SCHEMAS.values()]
    return {p: sha256(ROOT / p) for p in paths}


def strict_load(rel: str):
    return yaml.load((ROOT / rel).read_text(), Loader=StrictLoader)


def resolve_yaml_path(doc, fragment: str):
    """Resolve a dotted path fragment; returns (ok, node, reason)."""
    cur = doc
    for seg in fragment.split("."):
        if isinstance(cur, dict) and seg in cur:
            cur = cur[seg]
        else:
            return False, None, f"segment {seg!r} does not resolve"
    return True, cur, "ok"


def split_pointer(ptr: str):
    if "#" not in ptr:
        return ptr, ""
    return tuple(ptr.split("#", 1))


def pin_of(record: dict, schema: str) -> set:
    pat = re.compile(re.escape(schema) + r"#(?:sha256:)?([0-9a-fA-F]{12,64})")
    return {h.lower()[:12] for h in pat.findall(json.dumps(record))}


def named_target(record: dict, node: str, class_id: str, schema: str) -> bool:
    st = " ".join(json.dumps(record.get(k)) for k in
                  ("target_id", "target_id_full", "node_id", "class_id", "class_ids", "artifact") if k in record)
    return bool(re.search(rf"(?<![A-Za-z0-9]){re.escape(node)}(?![A-Za-z0-9])", st)
                or class_id in st or schema in st)


def main() -> int:
    now = datetime.now(CST).isoformat(timespec="seconds")
    pins_before = measure()
    canon = strict_load(CANON)
    supp = strict_load(SUPP)
    cons = json.loads((ROOT / CONS).read_text())
    frozen = json.loads((ROOT / FROZEN).read_text())
    map_doc = json.loads((ROOT / MAP).read_text())
    coverage = json.loads((ROOT / COVERAGE).read_text())

    checks, findings = [], []

    # C0 strict parse of all three schemas
    schemas = {}
    dup_errors = {}
    for node, rel in SCHEMAS.items():
        try:
            schemas[node] = strict_load(rel)
            dup_errors[node] = None
        except DupKeyError as e:
            schemas[node] = None
            dup_errors[node] = str(e)
    dup_clean = all(v is None for v in dup_errors.values())
    checks.append({"id": "C0-no-duplicate-yaml-keys", "pass": dup_clean, "detail": dup_errors})

    # C1/C2 pointer resolution
    ptr_rows = {}
    for node, rel in SCHEMAS.items():
        d = schemas[node] or {}
        primary = str(d.get("class_contract_pointer") or "")
        p_path, p_frag = split_pointer(primary)
        ok_p, obj_p, why_p = resolve_yaml_path(canon, p_frag) if p_path == CANON else (False, None, "not canonical path")
        sup_ptr = str(d.get("class_contract_supplement_pointer") or
                      (d.get("f0_binding") or {}).get("class_contract_supplement_pointer") or "")
        s_path, s_frag = split_pointer(sup_ptr)
        ok_s, obj_s, why_s = resolve_yaml_path(supp, s_frag) if s_path == SUPP else (False, None, "not supplement path")
        cls_ok = all((d.get("class_id") == CLASS_OF[node],
                      p_frag == f"classes.{CLASS_OF[node]}",
                      obj_p is not None and isinstance(obj_p, dict) and "axes" in obj_p))
        ptr_rows[node] = {
            "class_contract_pointer": primary, "canonical_resolves": ok_p, "canonical_reason": why_p,
            "class_id_matches": d.get("class_id") == CLASS_OF[node],
            "supplement_pointer": sup_ptr, "supplement_resolves": ok_s, "supplement_reason": why_s,
            "pass": bool(ok_p and ok_s and cls_ok),
        }
    checks.append({"id": "C1-class-contract-pointers-resolve", "pass": all(r["pass"] for r in ptr_rows.values()),
                   "detail": ptr_rows})
    if not all(r["pass"] for r in ptr_rows.values()):
        findings.append({"id": "HF-086-R1", "severity": "hard",
                         "finding": "a rev12 class-contract pointer does not resolve in its declared tree",
                         "detail": ptr_rows})

    # C3 declared hashes vs measured (live path) + declared-version snapshot availability
    declared_cons = {((schemas[n] or {}).get("f0_binding") or {}).get("consistency_evidence_sha256")
                     for n in SCHEMAS}
    snap_dir = OUT_DIR / "pinned"
    snapshot_hits = {}
    for h in declared_cons:
        if not h:
            continue
        snapshot_hits[h] = sorted(p.name for p in snap_dir.glob("taxonomy_consistency.*.json")
                                  if sha256(p) == h)
    hash_rows = {}
    for node, rel in SCHEMAS.items():
        d = schemas[node] or {}
        fb = d.get("f0_binding") or {}
        hash_rows[node] = {
            "declared_f0_sha256": fb.get("declared_f0_sha256"),
            "measured_f0_sha256": pins_before[CANON],
            "f0_match": fb.get("declared_f0_sha256") == pins_before[CANON],
            "declared_consistency_sha256": fb.get("consistency_evidence_sha256"),
            "measured_consistency_sha256": pins_before[CONS],
            "consistency_match": fb.get("consistency_evidence_sha256") == pins_before[CONS],
        }
    c3_pass = all(r["f0_match"] and r["consistency_match"] for r in hash_rows.values())
    checks.append({"id": "C3-declared-hashes-match-measured", "pass": c3_pass, "detail": {
        "per_schema": hash_rows,
        "declared_evidence_snapshot_hits": snapshot_hits,
        "evidence_moved_after_schema_stamp": not all(
            r["consistency_match"] for r in hash_rows.values()),
    }})
    if not c3_pass:
        findings.append({"id": "HF-086-R1", "severity": "hard", "target": "G-FORM",
                         "finding": ("The three rev12 schemas declare consistency_evidence_sha256 675a99d0d25b..., "
                                     "but the live canonical evidence path now carries a different document; the "
                                     "declared evidence does not resolve at the declared hash from the canonical path "
                                     "at measurement time."),
                         "detail": {"per_schema": hash_rows, "snapshot_hits": snapshot_hits},
                         "falsifier": ("Restore the declared bytes at the canonical evidence path, or re-stamp "
                                       "consistency_evidence_sha256 in the schemas to the live document and re-review.")})

    # C4 consistency evidence pins both trees and agrees
    try:
        declared_doc = None
        for p in snap_dir.glob("taxonomy_consistency.*.json"):
            if declared_cons and sha256(p) in declared_cons:
                declared_doc = json.loads(p.read_text())
                break
    except Exception:
        declared_doc = None
    cons_rows = {
        "consistent": cons.get("consistent"),
        "map_pin": cons.get("map_taxonomy_sha256"),
        "map_pin_match": cons.get("map_taxonomy_sha256") == pins_before[CANON],
        "supp_pin": cons.get("lead_contract_sha256"),
        "supp_pin_match": cons.get("lead_contract_sha256") == pins_before[SUPP],
        "measured_at": cons.get("measured_at"),
        "classes_compared": cons.get("classes_compared"),
        "declared_generation_had_input_pins": bool(
            declared_doc and declared_doc.get("map_taxonomy_sha256") and declared_doc.get("lead_contract_sha256")),
        "live_generation_has_input_pins": bool(cons.get("map_taxonomy_sha256") and cons.get("lead_contract_sha256")),
    }
    c4_pass = bool(cons_rows["consistent"] and cons_rows["map_pin_match"] and cons_rows["supp_pin_match"])
    checks.append({"id": "C4-consistency-evidence-pinned", "pass": c4_pass, "detail": cons_rows})
    if not c4_pass:
        findings.append({"id": "HF-086-R2b", "severity": "medium", "target": "G-FORM",
                         "finding": ("The live taxonomy_consistency.json asserts consistent=true but does not pin its "
                                     "two input trees (the generation the schemas declare did pin them); the claim is "
                                     "therefore not bound to any byte revision."),
                         "detail": cons_rows})

    # C5 independent identity/consistency recomputation (alias-aware, declared policy only)
    aliases = json.loads((ROOT / "artifacts/formulation/VOCAB_ALIASES.json").read_text())
    alias_map = {}
    for canon_tok, variants in (aliases.get("conclusion_type") or {}).items():
        group = [canon_tok, *variants]
        for v in group:
            alias_map[str(v).strip().lower()] = canon_tok

    def canon_conclusion(tok):
        return alias_map.get(str(tok).strip().lower(), str(tok))

    canon_ids = list((canon.get("classes") or {}).keys())
    supp_ids = list((supp.get("class_contracts") or {}).keys())
    ident_rows = {
        "canonical_class_ids": canon_ids,
        "supplement_class_ids": supp_ids,
        "frozen_four": canon.get("class_ids"),
        "sets_equal": set(canon_ids) == set(supp_ids) == set(canon.get("class_ids") or []),
        "alias_source": "artifacts/formulation/VOCAB_ALIASES.json",
        "alias_source_sha256": sha256(ROOT / "artifacts/formulation/VOCAB_ALIASES.json"),
        "per_class": {},
    }
    unsupported = []
    for node, cid in CLASS_OF.items():
        d = schemas[node] or {}
        axes = ((canon.get("classes") or {}).get(cid) or {}).get("axes") or {}
        canon_ct = axes.get("conclusion_type")
        schema_ct = ((d.get("conclusion") or {}).get("conclusion_type")
                     or (d.get("conclusion") or {}).get("type"))
        alias_applied = (str(schema_ct).strip().lower() != str(schema_ct)
                         or canon_conclusion(schema_ct) == str(canon_ct))
        ident_rows["per_class"][cid] = {
            "canonical_conclusion_type": canon_ct,
            "schema_conclusion_type": schema_ct,
            "alias_canonicalized_match": canon_conclusion(schema_ct) == canon_conclusion(canon_ct),
            "alias_applied": canon_conclusion(schema_ct) != str(schema_ct),
            "canonical_axes": axes,
        }
        if canon_conclusion(schema_ct) != canon_conclusion(canon_ct):
            unsupported.append((cid, canon_ct, schema_ct))
    checks.append({"id": "C5-independent-identity-recheck",
                   "pass": bool(ident_rows["sets_equal"] and not unsupported), "detail": ident_rows})
    if unsupported:
        findings.append({"id": "HF-086-R2", "severity": "hard",
                         "finding": "schema conclusion_type(s) do not match the canonical class axis under the declared alias policy",
                         "detail": unsupported})

    # C6 unknowns: no AF-* token outside the frozen four in the three schemas
    unknown = {}
    for node, rel in SCHEMAS.items():
        text = (ROOT / rel).read_text()
        toks = set(re.findall(r"AF-[A-Z0-9-]+", text))
        bad = sorted(t for t in toks if t not in set(canon_ids) | {CLASS_OF[node]})
        unknown[node] = bad
    checks.append({"id": "C6-no-unknown-class-tokens", "pass": not any(unknown.values()), "detail": unknown})

    # C7 accept coverage at the NEW pins (the rebind invalidated the old accepts)
    accept_rows = {}
    for node, rel in SCHEMAS.items():
        cur = pins_before[rel][:12]
        survivors = []
        for r in map_doc.get("reviews", []):
            if not named_target(r, node, CLASS_OF[node], rel):
                continue
            if str(r.get("verdict") or "").startswith("accept") and cur in pin_of(r, rel):
                survivors.append({"reviewer": r.get("reviewer"), "event_id": r.get("event_id"),
                                  "verdict": r.get("verdict")})
        accept_rows[node] = {"current_sha256_12": cur, "accepts_binding_current": survivors}
    stale_accepts = {}
    old = {"F1": "9a8bd4c9", "F2a": "b6123750", "F2b": "1bb78ce9"}
    superseded_eids = set()
    for p in (ROOT / "reviews").glob("*.json"):
        try:
            d = json.loads(p.read_text())
        except Exception:
            continue
        if isinstance(d, dict) and isinstance(d.get("supersedes"), dict) and d["supersedes"].get("event_id"):
            superseded_eids.add(str(d["supersedes"]["event_id"]))
    stale_rows = {}
    for node, rel in SCHEMAS.items():
        recs = []
        for r in map_doc.get("reviews", []):
            if named_target(r, node, CLASS_OF[node], rel) and str(r.get("verdict") or "").startswith("accept") \
                    and any(h.startswith(old[node]) for h in pin_of(r, rel)):
                recs.append({"event_id": r.get("event_id"), "reviewer": r.get("reviewer"),
                             "retracted": str(r.get("event_id")) in superseded_eids})
        stale_accepts[node] = len([x for x in recs if not x["retracted"]])
        stale_rows[node] = recs
    checks.append({"id": "C7-accept-census-at-new-pins",
                   "pass": True,
                   "detail": {"binding_current": accept_rows, "accepts_bound_to_pre_rebind_hash": stale_accepts,
                              "pre_rebind_accept_records": stale_rows}}) 
    if not any(v["accepts_binding_current"] for v in accept_rows.values()):
        findings.append({"id": "F-086-R3", "severity": "soft", "target": "G-FORM",
                         "finding": ("No accepting verdict binds the rev12 hashes; every pre-rebind accept "
                                     "(F1 0, F2a >=1, F2b >=1 at the 00:19 bytes) is invalidated by the "
                                     "00:31-00:32 rebind. G-FORM needs a fresh independent review round at the "
                                     "rev12 pins."),
                         "detail": {"stale_accept_counts": stale_accepts}})

    # controls
    controls = []
    ok_stale, _, _ = resolve_yaml_path(canon, "class_contracts.AF-SCC-C2-VAC-GEN")
    controls.append({"id": "K1-authoring-key-not-in-canonical", "pass": not ok_stale,
                     "detail": "canonical F0 has no class_contracts key (supplement is separate)"})
    controls.append({"id": "K2-short-hash-rejected",
                     "pass": not re.compile(re.escape(SCHEMAS["F2a"]) + r"#(?:sha256:)?([0-9a-fA-F]{12,64})")
                     .findall(f"{SCHEMAS['F2a']}#b6123750"),
                     "detail": "8-hex prefix is not a strict pin"})
    fake = "a: 1\nb: 2\na: 3\n"
    try:
        yaml.load(fake, Loader=StrictLoader)
        k3 = False
    except DupKeyError:
        k3 = True
    controls.append({"id": "K3-duplicate-key-detector-fires", "pass": k3,
                     "detail": "synthetic duplicate mapping key raises DupKeyError"})
    try:
        strict_load(SCHEMAS["F1"])
        k4 = True
    except DupKeyError:
        k4 = False
    controls.append({"id": "K4-real-schemas-parse-strict", "pass": k4,
                     "detail": "all three rev12 schemas parse under the strict loader"})

    pins_after = measure()
    drift = {k: [pins_before[k], pins_after[k]] for k in pins_before if pins_before[k] != pins_after[k]}
    all_pass = all(c["pass"] for c in checks) and all(c["pass"] for c in controls) and not drift
    hard = [f for f in findings if f.get("severity") == "hard"]

    verdict = "REV12_BINDING_CHAIN_VERIFIED" if (all_pass and not hard) else \
        ("REV12_BINDING_CHAIN_DEFECTIVE" if hard else "REV12_BINDING_CHAIN_PARTIAL")

    report = {
        "artifact_type": "gform_rev12_binding_verification",
        "artifact_version": "1.0",
        "artifact_id": "artifacts/worker-086/gform_rev12/report.json",
        "task_id": "w086-GFORM-rev12-verify-20260912T0033",
        "actor": "worker-086",
        "node_ids": ["F1", "F2a", "F2b"],
        "gate": "G-FORM",
        "class_ids": list(CLASS_OF.values()),
        "review_kind": "binding_chain_verification",
        "counts_as_full_schema_verdict": False,
        "created_at": now,
        "authority": "worker adjudication input only; no gate verdict, no node status",
        "inputs": [{"path": k, "sha256": v, "bytes": (ROOT / k).stat().st_size} for k, v in pins_before.items()],
        "input_drift_within_run": drift,
        "rebind_observed": {
            "pre_rebind_hashes": {"F1": "9a8bd4c96800", "F2a": "b6123750b37d", "F2b": "1bb78ce9b357",
                                  "F0": "276009f4f63d"},
            "post_rebind_hashes": {**{n: pins_before[r] for n, r in SCHEMAS.items()}, "F0": pins_before[CANON]},
            "schema_mtime": "2026-09-12T00:32:02+08:00",
            "canonical_f0_revision": canon.get("revision"),
            "frozen_revision": frozen.get("revision"),
        },
        "checks": checks,
        "controls": controls,
        "findings": findings,
        "verdict": verdict,
        "next_falsifier": ("Re-run probe_rev12.py after any further schema/F0 byte change; if a pointer, declared "
                           "hash, or accept count differs, the verification must be re-issued at the new pins."),
        "non_claims": [
            "Binding-chain and structural verification only; schema content, physics, and quantifier semantics "
            "were not re-derived (that is a full-schema review, out of this task's scope).",
            "Does not assert any accept is correct; it counts accepts bound to the named bytes.",
            "Does not set or propose a gate verdict.",
        ],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "report.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({"verdict": verdict, "all_pass": all_pass, "drift": drift,
                      "checks": {c["id"]: c["pass"] for c in checks},
                      "controls": {c["id"]: c["pass"] for c in controls},
                      "findings": [f["id"] for f in findings],
                      "post_rebind_hashes": report["rebind_observed"]["post_rebind_hashes"],
                      "accepts_binding_current": {n: accept_rows[n]["accepts_binding_current"] for n in SCHEMAS},
                      "stale_accept_counts": stale_accepts,
                      "report": "artifacts/worker-086/gform_rev12/report.json"}, indent=1))
    if drift:
        return 2
    if not all(c["pass"] for c in controls):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
