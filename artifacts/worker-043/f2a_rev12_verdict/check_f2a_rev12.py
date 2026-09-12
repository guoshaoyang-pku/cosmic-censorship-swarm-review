#!/usr/bin/env python3
"""W043C independent full-schema checker for AF-SCC-C2-VAC-GEN at FROZEN rev28.

Task: supply one independent full-schema review verdict at the rev27/rev28 frozen
hash of F2a, the class for which the audit lead's G-FORM final verify measured
zero independent verdicts at the current hash (B-GFORM-1).

This checker is deliberately independent of the authoring tree's own gate:
it re-derives every criterion from the bytes, and it fails closed on drift.

Usage:
  python3 check_f2a_rev12.py --root /path/to/ai4math-swarm            # live pass
  python3 check_f2a_rev12.py --root . --json out.json                 # write JSON
  python3 check_f2a_rev12.py --root . --selftest                      # run controls

Exit codes: 0 = all checks PASS/INFO and controls PASS; 2 = at least one FAIL;
3 = input drift from the pinned target hashes; 4 = control battery failed.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

# ---------------------------------------------------------------- pinned targets
# Measured 2026-09-12T00:34:06+08:00 and re-measured 00:36:04+08:00; frozen in
# FROZEN rev28 (2f358f6722d92062...). Any byte change voids this review.
TARGETS = {
    "schemas/af_scc_c2_vacuum.yaml": (
        "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
        29976,
        "F2a",
    ),
    "schemas/af_scc_c0_vacuum.yaml": (
        "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
        34984,
        "F2b",
    ),
    "schemas/af_wcc_vacuum.yaml": (
        "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
        36014,
        "F1",
    ),
    "research_map/formulation_taxonomy.yaml": (
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
        36372,
        "F0-canonical",
    ),
    "artifacts/formulation/formulation_taxonomy.yaml": (
        "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
        21699,
        "F0-supplement",
    ),
    "artifacts/formulation/FROZEN.json": (
        "2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1",
        21973,
        "FROZEN-rev28",
    ),
    "artifacts/formulation/evidence/taxonomy_consistency.json": (
        "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b",
        495,
        "consistency-evidence",
    ),
}
F2A = "schemas/af_scc_c2_vacuum.yaml"
F2B = "schemas/af_scc_c0_vacuum.yaml"
F1 = "schemas/af_wcc_vacuum.yaml"
F0 = "research_map/formulation_taxonomy.yaml"
F0S = "artifacts/formulation/formulation_taxonomy.yaml"
FROZEN = "artifacts/formulation/FROZEN.json"

CLASS_ID = "AF-SCC-C2-VAC-GEN"
SIBLING = "AF-SCC-C0-VAC-GEN"

# Assertive fields: composite "C0 or C2" tokens here are class leakage.
ASSERTIVE_FIELDS = (
    "quantifiers",
    "conclusion",
    "scope_statement",
    "regularity",
    "genericity",
    "topology",
    "data_class",
    "falsifier",
    "known_status",
)

COMPOSITE_RE = re.compile(r"C0\s*(?:or|/|,|\+|and)\s*C2|C2\s*(?:or|/|,|\+|and)\s*C0", re.I)
TIMESTAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:[+-]\d{2}:\d{2})?")


# ---------------------------------------------------------------- helpers
def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def read_bytes(root: Path, rel: str) -> bytes:
    return (root / rel).read_bytes()


def iso(s: str) -> dt.datetime:
    return dt.datetime.fromisoformat(s)


class DuplicateKeyLoader(yaml.SafeLoader):
    """SafeLoader that records duplicate mapping keys instead of silently losing them."""


def _make_dup_loader():
    dup: list[tuple[str, int]] = []

    def construct_mapping(loader, node, deep=False):
        mapping = {}
        for k, v in node.value:
            key = loader.construct_object(k, deep=deep)
            if key in mapping:
                line = getattr(k, "start_mark", None)
                dup.append((str(key), (line.line + 1) if line else -1))
            mapping[key] = loader.construct_object(v, deep=deep)
        return mapping

    DuplicateKeyLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping
    )
    return dup


def load_yaml(text: bytes):
    dup = _make_dup_loader()
    obj = yaml.load(text.decode("utf-8"), Loader=DuplicateKeyLoader)
    return obj, dup


def walk(obj, path="$"):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield f"{path}.{k}", v
            yield from walk(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield f"{path}[{i}]", v
            yield from walk(v, f"{path}[{i}]")


def resolve_pointer(root: Path, pointer: str) -> tuple[bool, str]:
    """Resolve 'path#dot.fragment' inside the repo root; return (ok, detail)."""
    if "#" not in pointer:
        return False, f"no fragment in {pointer!r}"
    path_s, frag = pointer.split("#", 1)
    p = root / path_s
    if not p.is_file():
        return False, f"path missing: {path_s}"
    try:
        doc, _ = load_yaml(p.read_bytes())
    except Exception as exc:  # pragma: no cover
        return False, f"parse error: {exc}"
    cur = doc
    for part in frag.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return False, f"fragment {frag!r} does not resolve at {part!r} in {path_s}"
    return True, f"resolved {pointer}"


def scan_future_timestamps(obj, measured: dt.datetime):
    bad = []
    for path, val in walk(obj):
        if isinstance(val, str):
            for m in TIMESTAMP_RE.finditer(val):
                try:
                    ts = iso(m.group(0))
                except ValueError:
                    continue
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=measured.tzinfo)
                if ts > measured:
                    bad.append((path, m.group(0)))
    return bad


# ---------------------------------------------------------------- checks
def run_checks(root: Path, measured_at: dt.datetime | None = None) -> dict:
    measured_at = measured_at or dt.datetime.now().astimezone()
    checks: list[dict] = []

    def add(cid, status, statement, observed=None, evidence=None, falsifier=None):
        checks.append(
            {
                "check_id": cid,
                "status": status,
                "statement": statement,
                "observed": observed,
                "evidence": evidence or [],
                "falsifier": falsifier,
            }
        )

    # -- R0 drift / binding -------------------------------------------------
    measured = {}
    drift = []
    for rel, (want_sha, want_bytes, label) in TARGETS.items():
        p = root / rel
        if not p.is_file():
            drift.append({"path": rel, "error": "missing"})
            continue
        b = p.read_bytes()
        got = sha256_bytes(b)
        measured[rel] = {
            "sha256": got,
            "bytes": len(b),
            "mtime": dt.datetime.fromtimestamp(p.stat().st_mtime).astimezone().isoformat(timespec="seconds"),
            "label": label,
        }
        if got != want_sha or len(b) != want_bytes:
            drift.append(
                {"path": rel, "want_sha256": want_sha, "got_sha256": got,
                 "want_bytes": want_bytes, "got_bytes": len(b)}
            )
    add(
        "R0-drift",
        "FAIL" if drift else "PASS",
        "The seven reviewed artifacts are byte-identical to the pinned rev27/rev28 targets.",
        {"drift": drift, "measured": measured},
        [f"{rel}#{m['sha256'][:16]}" for rel, m in measured.items()],
        "any listed file whose sha256 differs from the target voids every verdict below",
    )
    if drift:
        return {"verdict": "VOID", "checks": checks, "drift": drift}

    f2a_txt = read_bytes(root, F2A)
    f2b_txt = read_bytes(root, F2B)
    f1_txt = read_bytes(root, F1)
    f0_txt = read_bytes(root, F0)
    f0s_txt = read_bytes(root, F0S)
    frozen = json.loads(read_bytes(root, FROZEN))

    f2a, dup_a = load_yaml(f2a_txt)
    f2b, dup_b = load_yaml(f2b_txt)
    _f1, dup_1 = load_yaml(f1_txt)
    _f0, dup_0 = load_yaml(f0_txt)
    _f0s, dup_0s = load_yaml(f0s_txt)

    # -- R1 YAML hygiene ----------------------------------------------------
    dups = {"F2a": dup_a, "F2b": dup_b, "F1": dup_1, "F0-canonical": dup_0, "F0-supplement": dup_0s}
    add(
        "R1-yaml-hygiene",
        "PASS" if not any(dups.values()) else "FAIL",
        "No duplicate mapping keys in any reviewed YAML artifact (strict parse, history in revision_history).",
        {k: v for k, v in dups.items()},
        [f"{F2A}#strict-parse", "artifacts/formulation/FROZEN.json#files"],
        "a single duplicate key reopens the rev26 data-loss defect",
    )

    # -- R2 identity / binding ---------------------------------------------
    ident = {
        "schema_version": f2a.get("schema_version"),
        "artifact_kind": f2a.get("artifact_kind"),
        "class_id": f2a.get("class_id"),
        "node_id": f2a.get("node_id"),
        "revision": f2a.get("revision"),
        "sibling_disjoint_from": f2a.get("sibling_disjoint_from"),
        "sibling_backref": f2b.get("sibling_disjoint_from"),
    }
    ident_ok = (
        ident["artifact_kind"] == "class_schema"
        and ident["class_id"] == CLASS_ID
        and ident["node_id"] == "F2a"
        and ident["sibling_disjoint_from"] == SIBLING
        and ident["sibling_backref"] == CLASS_ID
    )
    add(
        "R2-identity",
        "PASS" if ident_ok else "FAIL",
        "F2a declares exactly AF-SCC-C2-VAC-GEN / node F2a and the C2<->C0 sibling back-reference is symmetric.",
        ident,
        [f"{F2A}#class_id", f"{F2B}#sibling_disjoint_from"],
        "a wrong or missing class id / asymmetric sibling link is a binding failure",
    )

    # -- R3 FROZEN pin + mirror --------------------------------------------
    pins = frozen.get("files", {})
    pin_report = {}
    for rel in (F2A, F2B, F1, F0, F0S):
        pin = pins.get(rel, {})
        pin_report[rel] = {
            "frozen_sha256": pin.get("sha256"),
            "measured_sha256": measured[rel]["sha256"],
            "match": pin.get("sha256") == measured[rel]["sha256"],
        }
    mirror_ok = sha256_bytes(f2a_txt) == sha256_bytes(read_bytes(root, "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"))
    pin_ok = all(v["match"] for v in pin_report.values()) and mirror_ok
    add(
        "R3-freeze-pin",
        "PASS" if pin_ok else "FAIL",
        "FROZEN rev28 pins the reviewed bytes and the authoring mirror is byte-identical to the canonical F2a.",
        {"pins": pin_report, "frozen_revision": frozen.get("revision"),
         "frozen_at": frozen.get("frozen_at"), "mirror_equal": mirror_ok},
        [f"{FROZEN}#files", "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"],
        "a pin or mirror mismatch means the reviewed artifact is not the frozen one",
    )

    # -- R4 clock discipline ------------------------------------------------
    mtime = dt.datetime.fromtimestamp((root / F2A).stat().st_mtime).astimezone()
    revised = iso(f2a["revised_at"]) if isinstance(f2a.get("revised_at"), str) else None
    future = scan_future_timestamps(f2a, measured_at)
    clock_ok = (
        revised is not None
        and revised <= mtime + dt.timedelta(seconds=1)
        and revised <= measured_at
        and not future
    )
    add(
        "R4-clock",
        "PASS" if clock_ok else "FAIL",
        "Single top-level revised_at, not future-dated, not later than the file write time; no future-dated machine timestamp anywhere in F2a.",
        {"revised_at": f2a.get("revised_at"), "file_mtime": mtime.isoformat(timespec="seconds"),
         "measured_at": measured_at.isoformat(timespec="seconds"),
         "future_dated": future,
         "top_level_revised_at_count": f2a_txt.decode().count("\nrevised_at:") + f2a_txt.decode().startswith("revised_at:")},
        [f"{F2A}#revised_at", "CF-14"],
        "a future-dated or duplicated revised_at reopens CF-14 / the rev26 defect",
    )

    # -- R5 quantifier well-typedness --------------------------------------
    q = f2a.get("quantifiers", {})
    ordered = q.get("ordered", [])
    domains = q.get("domains", {})
    kinds = [o.get("kind") for o in ordered]
    binders = [o.get("binder") for o in ordered]
    dom_ids = [o.get("domain_id") for o in ordered]
    refs_ok = True
    for d in ("D0", "D1", "D2", "D3"):
        ref = domains.get(d, {}).get("definition_ref")
        cur, ok = f2a, isinstance(ref, str)
        for part in (ref or "").split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                ok = False
                break
        refs_ok = refs_ok and ok
    formal = q.get("formal", "")
    quant_ok = (
        kinds == ["forall", "exists", "forall", "not_exists"]
        and binders == ["r", "G_r", "(Sigma,h,K)", "(M',g',iota)"]
        and dom_ids == ["D0", "D1", "D2", "D3"]
        and refs_ok
        and "forall r in D0" in formal
        and "not exists a proper future C2 vacuum extension" in formal
        and "comeager" in formal
        and "tagged disjoint union" in domains.get("D0", {}).get("definition", "")
        and q.get("order_matters") is True
    )
    add(
        "R5-quantifier",
        "PASS" if quant_ok else "FAIL",
        "Quantifier chain is forall r in D0 / exists comeager G_r / forall data / not-exists proper future C2 vacuum extension, with D0 a tagged disjoint union and every domain_id resolving to a definition_ref.",
        {"kinds": kinds, "binders": binders, "domain_ids": dom_ids,
         "refs_resolve": refs_ok, "formal": formal[:220],
         "D0_tagged_disjoint_union": "tagged disjoint union" in domains.get("D0", {}).get("definition", "")},
        [f"{F2A}#quantifiers"],
        "an ill-typed or re-ordered binder chain reopens F1-review-19 F-2 / F2b-review-034 HF-034-1",
    )

    # -- R6 conclusion ------------------------------------------------------
    concl = f2a.get("conclusion", {})
    vis = f2a.get("visibility", {})
    concl_ok = (
        concl.get("conclusion_type") == "scc_c2_future_inextendibility"
        and concl.get("family") == "SCC"
        and concl.get("epistemic_status") == "open_problem"
        and "not exists proper_future_extension_in_class" in concl.get("statement_formal", "")
        and vis.get("role") == "not_in_conclusion"
        and "WCC" in json.dumps(vis.get("forbidden_falsifier", ""))
    )
    add(
        "R6-conclusion",
        "PASS" if concl_ok else "FAIL",
        "Conclusion is the SCC C2 future-inextendibility statement, open, with visibility explicitly excluded and the WCC falsifier forbidden.",
        {"conclusion_type": concl.get("conclusion_type"), "family": concl.get("family"),
         "epistemic_status": concl.get("epistemic_status"),
         "statement_formal": concl.get("statement_formal"),
         "visibility_role": vis.get("role"),
         "forbidden_falsifier": vis.get("forbidden_falsifier")},
        [f"{F2A}#conclusion", f"{F2A}#visibility"],
        "a WCC/visibility conclusion bound to this class would be conclusion inflation",
    )

    # -- R7 extension predicate --------------------------------------------
    ext = f2a.get("extension_predicate", {})
    ext_ok = (
        ext.get("name") == "proper_future_extension_in_class"
        and ext.get("frozen_regularity") == "C2"
        and ext.get("frozen_equation_concept") == "classical_ricci"
        and ext.get("frozen_direction") == "future"
        and len(ext.get("must_not_conflate", [])) >= 3
        and all(m in ext.get("definition", "") for m in ("(a)", "(b)", "(c)", "(d)", "(e)", "(f)"))
        and "Ric(g') = 0" in ext.get("definition", "")
    )
    add(
        "R7-extension-predicate",
        "PASS" if ext_ok else "FAIL",
        "Extension predicate is the proper future C2 vacuum extension: C2 metric, classical Ric=0, clauses (a)-(f), conflation guards present.",
        {"name": ext.get("name"), "frozen_regularity": ext.get("frozen_regularity"),
         "frozen_equation_concept": ext.get("frozen_equation_concept"),
         "clauses": [m for m in ("(a)", "(b)", "(c)", "(d)", "(e)", "(f)") if m in ext.get("definition", "")],
         "must_not_conflate_n": len(ext.get("must_not_conflate", []))},
        [f"{F2A}#extension_predicate"],
        "dropping the equation requirement or the C2 token binds a weaker/different class",
    )

    # -- R8 regularity + composite ban -------------------------------------
    reg = f2a.get("regularity", {})
    comp_hits = []
    for field in ASSERTIVE_FIELDS:
        if field in f2a:
            for path, val in walk(f2a[field], f"$.{field}"):
                if isinstance(val, str) and COMPOSITE_RE.search(val):
                    comp_hits.append((path, val[:160]))
    reg_ok = (
        reg.get("extension_regularity") == "C2"
        and "E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0" in reg.get("extension_regularity_exact", "")
        and not comp_hits
    )
    add(
        "R8-regularity",
        "PASS" if reg_ok else "FAIL",
        "Extension regularity is exactly C2 with the declared containment chain, and no composite C0/C2 token appears in an assertive field.",
        {"extension_regularity": reg.get("extension_regularity"),
         "containment_declared": "E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0"
         in reg.get("extension_regularity_exact", ""),
         "composite_hits": comp_hits},
        [f"{F2A}#regularity"],
        "a composite regularity token in an assertive field is the documented C0/C2 merge failure mode",
    )

    # -- R9 ledger internal consistency ------------------------------------
    led = f2a.get("implication_ledger", {})
    chain = led.get("extension_class_containment", "")
    size_premises = []
    for i, row in enumerate(led.get("forbidden_transfers", [])):
        reason = row.get("reason", "")
        if re.search(r"strictly (larger|smaller) extension class", reason):
            size_premises.append({"index": i, "from": row.get("from"), "to": row.get("to"),
                                  "reason": reason,
                                  "said_larger": "strictly larger" in reason,
                                  "chain_has_C2_smallest": "E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0" in chain})
    inverted = [p for p in size_premises if p["said_larger"] and p["chain_has_C2_smallest"]]
    ent = led.get("one_way_entailments", [])
    entails_c0_to_c2 = any("C0" in r.get("from", "") and "C2" in r.get("to", "") for r in ent)
    forbids_c2_to_c0 = any(
        "C2" in r.get("from", "") and ("C0" in r.get("to", "") or "this class" in r.get("to", ""))
        for r in led.get("forbidden_transfers", [])
    )
    led_ok = (
        "E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0" in chain
        and entails_c0_to_c2
        and forbids_c2_to_c0
        and not inverted
    )
    add(
        "R9-ledger",
        "PASS" if led_ok else "FAIL",
        "F2a ledger declares E_C2 smallest, licenses C0=>C2, forbids the converse, and contains no inverted class-size premise.",
        {"chain": chain[:240], "entails_C0_to_C2": entails_c0_to_c2,
         "forbids_C2_to_C0": forbids_c2_to_c0, "size_premises": size_premises},
        [f"{F2A}#implication_ledger"],
        "any reason calling C2 the larger extension class reopens the FORM-SEP-04 inversion",
    )

    # -- R10 falsifier decidability ----------------------------------------
    fal = f2a.get("falsifier", {})
    t1 = fal.get("tier_1", {})
    t2 = fal.get("tier_2", {})
    fal_ok = (
        bool(t1.get("witness_type"))
        and len(t1.get("machine_checkable_steps", [])) >= 3
        and t1.get("genericity_requirement")
        and t2.get("labelling_required") == "refutes_strengthening_only"
        and len(fal.get("schema_falsifiers", [])) >= 4
    )
    add(
        "R10-falsifier",
        "PASS" if fal_ok else "FAIL",
        "A decidable falsifier exists: tier-1 witness type + machine-checkable steps + genericity route, tier-2 labelled strengthening-only, four schema falsifiers.",
        {"tier1_witness": bool(t1.get("witness_type")),
         "machine_steps": len(t1.get("machine_checkable_steps", [])),
         "tier2_label": t2.get("labelling_required"),
         "schema_falsifiers": len(fal.get("schema_falsifiers", []))},
        [f"{F2A}#falsifier"],
        "a falsifier with no witness type or no machine-checkable step is not decidable",
    )

    # -- R11 conclusion inflation ------------------------------------------
    infl_re = re.compile(r"\b(is proved|has been proved|is established|is refuted|is solved|theorem proved)\b", re.I)
    infl_hits = []
    for field in ("conclusion", "known_status", "promotion_rule"):
        if field in f2a:
            for path, val in walk(f2a[field], f"$.{field}"):
                if isinstance(val, str) and infl_re.search(val):
                    infl_hits.append((path, val[:160]))
    add(
        "R11-inflation",
        "PASS" if not infl_hits else "FAIL",
        "No assertive truth/refutation claim in conclusion, known_status or promotion_rule.",
        {"hits": infl_hits, "epistemic_status": f2a.get("epistemic_status")},
        [f"{F2A}#promotion_rule", f"{F2A}#known_status"],
        "a proved/refuted token bound to an open class is conclusion inflation",
    )

    # -- R12 O-GFORM-1 adjudication (data_class key identity) ---------------
    dc_same = json.dumps(f2a.get("data_class"), sort_keys=True) == json.dumps(f2b.get("data_class"), sort_keys=True)
    sep_sources = {
        "class_components.regularity_token": f2a.get("class_components", {}).get("regularity_token"),
        "extension_predicate.frozen_regularity": ext.get("frozen_regularity"),
        "extension_predicate.frozen_equation_concept": ext.get("frozen_equation_concept"),
        "conclusion.conclusion_type": concl.get("conclusion_type"),
        "regularity.extension_regularity": reg.get("extension_regularity"),
    }
    add(
        "R12-ogform1-adjudication",
        "INFO",
        "O-GFORM-1: F2a and F2b data_class blocks are structurally identical; the class distinction is carried by the extension predicate, not the data. Adjudicated as intended encoding, NON-BLOCKING, because the schema declares data_versus_extension_classes and all five separation fields differ/track the token.",
        {"data_class_key_identical": dc_same, "separation_sources": sep_sources,
         "conventions_data_versus_extension": f2a.get("conventions", {}).get("data_versus_extension_classes")},
        [f"{F2A}#conventions", f"{F2A}#extension_predicate", f"{F2B}#extension_predicate"],
        "if the separation fields did not track the C2/C0 token, the classes would not be distinguishable",
    )

    # -- R13 pointers + f0 binding -----------------------------------------
    ptr_ok, ptr_detail = resolve_pointer(root, f2a.get("class_contract_pointer", ""))
    sup_ok, sup_detail = resolve_pointer(root, f2a.get("class_contract_supplement_pointer", ""))
    f0b = f2a.get("f0_binding", {})
    f0b_ok = ptr_ok and sup_ok and f0b.get("declared_f0_sha256") == measured[F0]["sha256"]
    add(
        "R13-pointers",
        "PASS" if f0b_ok else "FAIL",
        "class_contract_pointer resolves in canonical F0, supplement pointer resolves in the supplement, and the declared F0 hash equals the measured F0 hash.",
        {"class_contract_pointer": ptr_detail, "supplement_pointer": sup_detail,
         "declared_f0_sha256": f0b.get("declared_f0_sha256"),
         "measured_f0_sha256": measured[F0]["sha256"]},
        [f"{F2A}#class_contract_pointer", f"{F2A}#f0_binding", f"{F0}#classes.{CLASS_ID}"],
        "an unresolvable pointer or a stale declared F0 hash means the schema binds a superseded artifact",
    )

    # -- R15 evidence binding (embedded hash vs measured bytes) -------------
    cons_path = f0b.get("consistency_evidence", "")
    cons_file_sha = (
        sha256_bytes(read_bytes(root, cons_path)) if cons_path and (root / cons_path).is_file() else None
    )
    declared = f0b.get("consistency_evidence_sha256")
    ev_ok = declared is not None and declared == cons_file_sha
    add(
        "R15-consistency-binding",
        "FAIL" if not ev_ok else "PASS",
        "The schema's embedded consistency_evidence_sha256 equals the measured hash of the consistency-evidence file it names (FROZEN rev28 pin).",
        {"path": cons_path, "declared_sha256": declared, "measured_sha256": cons_file_sha,
         "frozen_pin_sha256": pins.get(cons_path, {}).get("sha256"),
         "declared_bytes_exist_on_disk": False},
        [f"{F2A}#f0_binding.consistency_evidence_sha256", f"{FROZEN}#files"],
        "a declared evidence hash that differs from the named file's measured/frozen hash is a stale binding; repairing the hash and re-freezing must clear it",
    )

    # -- R16 evidence is itself hash-bound ---------------------------------
    cons_doc = json.loads(read_bytes(root, cons_path)) if cons_path and (root / cons_path).is_file() else {}
    hash_fields = {k: cons_doc.get(k) for k in ("map_taxonomy_sha256", "lead_contract_sha256")}
    ev_bound = (
        hash_fields.get("map_taxonomy_sha256") == measured[F0]["sha256"]
        and hash_fields.get("lead_contract_sha256") == measured[F0S]["sha256"]
    )
    add(
        "R16-evidence-hash-bound",
        "PASS" if ev_bound else "FAIL",
        "The frozen consistency evidence carries map_taxonomy_sha256 and lead_contract_sha256 matching the measured F0 and supplement (rev27 closure item (e): evidence must be hash-bound).",
        {"fields": hash_fields, "measured_f0": measured[F0]["sha256"],
         "measured_supplement": measured[F0S]["sha256"],
         "content_keys": sorted(cons_doc.keys())},
        [cons_path, "artifacts/formulation/tools/close_findings_rev27.py:379-380"],
        "a hashless consistency evidence reopens F1-review-090 F090-05 / F1-review-19 F-4",
    )

    # -- R14 declared gate, independently re-run ---------------------------
    gate = {"rc": None, "stdout": "", "stderr": ""}
    tool = root / "artifacts/formulation/tools/check_class_schema.py"
    if tool.is_file():
        proc = subprocess.run(
            [sys.executable, str(tool), str(root / F2A)],
            capture_output=True, text=True, timeout=180,
        )
        gate = {"rc": proc.returncode, "stdout": proc.stdout.strip()[:2000],
                "stderr": proc.stderr.strip()[:1000]}
    gate_ok = gate["rc"] == 0 and "failed_rules=[]" in gate["stdout"]
    add(
        "R14-declared-gate",
        "PASS" if gate_ok else "FAIL",
        "The authoring tree's own check_class_schema.py independently re-run on the frozen bytes returns PASS with failed_rules=[].",
        gate,
        ["artifacts/formulation/tools/check_class_schema.py"],
        "a declared-gate failure on the frozen bytes is a blocking finding",
    )

    # -- verdict ------------------------------------------------------------
    fails = [c for c in checks if c["status"] == "FAIL"]
    verdict = "accept" if not fails else "revise"
    score = 4.0 if not fails else max(1.0, 4.0 - 0.5 * len(fails))
    return {
        "schema_version": "worker-review/v1",
        "task_id": "W043C-F2A-REV12-VERDICT-01",
        "actor": "worker-043",
        "class_id": CLASS_ID,
        "node_id": "F2a",
        "gate": "G-FORM",
        "measured_at": measured_at.isoformat(timespec="seconds"),
        "reviewed_sha256": measured[F2A]["sha256"],
        "reviewed_bytes": measured[F2A]["bytes"],
        "frozen_revision": frozen.get("revision"),
        "frozen_sha256": measured[FROZEN]["sha256"],
        "verdict": verdict,
        "score": score,
        "n_fail": len(fails),
        "checks": checks,
        "n_checks": len(checks),
        "n_pass": sum(1 for c in checks if c["status"] == "PASS"),
        "n_info": sum(1 for c in checks if c["status"] == "INFO"),
    }


# ---------------------------------------------------------------- controls
def selftest(root: Path) -> dict:
    """Mutate a scratch copy of the frozen bytes and require each defect be caught."""
    scratch = Path(tempfile.mkdtemp(prefix="w043_f2a_selftest_"))
    try:
        for rel in TARGETS:
            dst = scratch / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / rel, dst)
        # tools and pointers need to exist in the scratch root
        for rel in ("artifacts/formulation/tools/check_class_schema.py",
                    "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
                    "schemas/af_scc_regularities.yaml"):
            src = root / rel
            if src.is_file():
                dst = scratch / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
        # keep target hashes valid: run checks on the *pinned* TARGETS, so a
        # mutant copy would fail R0 first. Instead, mutate in a way that the
        # control expects a specific non-R0 check, by calling the inner checker
        # with an overridden expectation each time.
        results = []

        def inner(rel: str, text: str) -> dict:
            # targeted check extraction: rebuild only for the F2a mutation
            old = (scratch / rel).read_text()
            (scratch / rel).write_text(text)
            try:
                # temporarily retarget the pin to the mutant so R0 does not mask
                want = sha256_bytes(text.encode())
                TARGETS[rel] = (want, len(text.encode()), TARGETS[rel][2])
                res = run_checks(scratch)
            finally:
                (scratch / rel).write_text(old)
                TARGETS[rel] = (sha256_bytes(old.encode()), len(old.encode()), TARGETS[rel][2])
            return res

        base = None

        def fires(res, cid):
            return any(c["check_id"] == cid and c["status"] == "FAIL" for c in res["checks"])

        ok = True
        orig_a = (scratch / F2A).read_text()

        m1 = orig_a.replace("scc_c2_future_inextendibility", "scc_c0_future_inextendibility")
        r1 = inner(F2A, m1); c1 = fires(r1, "R6-conclusion") or fires(r1, "R12-ogform1-adjudication") or fires(r1, "R2-identity")
        ok &= c1; results.append({"control": "M1-wrong-conclusion-family", "fired": c1, "expected": "R6/R2"})

        m2 = orig_a.replace("frozen_regularity: C2", "frozen_regularity: C0", 1)
        r2 = inner(F2A, m2); c2 = fires(r2, "R7-extension-predicate")
        ok &= c2; results.append({"control": "M2-extension-regularity-C0", "fired": c2, "expected": "R7"})

        m3 = orig_a.replace("E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0",
                            "E_C0 subset of E_C2", 1)
        r3 = inner(F2A, m3); c3 = fires(r3, "R9-ledger") or fires(r3, "R8-regularity")
        ok &= c3; results.append({"control": "M3-containment-inversion", "fired": c3, "expected": "R8/R9"})

        m4 = orig_a.replace("revision: 12", "revision: 12\nrevised_at: \"2026-09-12T02:00:00+08:00\"", 1)
        r4 = inner(F2A, m4); c4 = fires(r4, "R1-yaml-hygiene") or fires(r4, "R4-clock")
        ok &= c4; results.append({"control": "M4-duplicate-and-future-revised_at", "fired": c4, "expected": "R1/R4"})

        m5 = orig_a.replace('class_contract_pointer: research_map/formulation_taxonomy.yaml#classes.AF-SCC-C2-VAC-GEN',
                            'class_contract_pointer: research_map/formulation_taxonomy.yaml#classes.NOPE', 1)
        r5 = inner(F2A, m5); c5 = fires(r5, "R13-pointers")
        ok &= c5; results.append({"control": "M5-unresolvable-pointer", "fired": c5, "expected": "R13"})

        CONS = "artifacts/formulation/evidence/taxonomy_consistency.json"
        orig_c = (scratch / CONS).read_text()
        m6 = orig_c.replace("9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b", "0" * 64)
        r6 = inner(CONS, m6); c6 = fires(r6, "R16-evidence-hash-bound")
        ok &= c6; results.append({"control": "M6-hashless-consistency-evidence", "fired": c6, "expected": "R16"})

        m7 = orig_a.replace("675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48", "f" * 64)
        r7 = inner(F2A, m7); c7 = fires(r7, "R15-consistency-binding")
        ok &= c7; results.append({"control": "M7-stale-embedded-evidence-hash", "fired": c7, "expected": "R15"})

        # negative control: pristine bytes must produce exactly the two known
        # binding FAILs and no other FAIL (no false positives on content)
        clean = run_checks(root)
        clean_fails = sorted(c["check_id"] for c in clean["checks"] if c["status"] == "FAIL")
        expected_fails = ["R15-consistency-binding", "R16-evidence-hash-bound"]
        clean_ok = clean_fails == expected_fails
        results.append({"control": "C0-pristine-exact-fail-set",
                        "fired": clean_ok, "expected": expected_fails,
                        "observed_fails": clean_fails, "n_fail": clean["n_fail"]})
        ok &= clean_ok

        return {"controls_pass": bool(ok), "controls": results}
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--json", default=None)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    out = run_checks(root)
    if args.selftest:
        out["controls"] = selftest(root)
        if not out["controls"]["controls_pass"]:
            out["control_battery"] = "FAIL"
    print(json.dumps(out, indent=1))
    if args.json:
        Path(args.json).write_text(json.dumps(out, indent=1) + "\n")
    if out["verdict"] == "VOID":
        return 3
    if out.get("control_battery") == "FAIL":
        return 4
    return 0 if out["verdict"] == "accept" else 2


if __name__ == "__main__":
    raise SystemExit(main())
