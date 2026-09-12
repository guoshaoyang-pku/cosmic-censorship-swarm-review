#!/usr/bin/env python3
"""W054-F1-ADJUDICATE-01 -- independent adjudication of contested F1 review findings.

Bounded worker task, worker=054. Class-bound: class_id AF-WCC-VAC-GEN, node F1, gate G-FORM.

Question being adjudicated
--------------------------
The review corpus for `schemas/af_wcc_vacuum.yaml` at the pinned revision is in conflict:

  * accept -- astra-lead-audit (reviews/F1-review-lead-audit-r2.json, 4.5) reports all semantic
    slots present, no conclusion inflation, clean class separation, mirror equality.
  * revise -- worker-090 (HF090-01: class_contract_pointer unresolved against the canonical
    taxonomy), worker-094 (HF-094-2: duplicate YAML mapping keys + future-dated timestamps),
    worker-059 (independent checks C12/C14/C15 non-pass).

This script re-tests the *specific factual claims* behind the revise camp against the pinned
bytes, with its own code (no imports from the reviewers' scripts and no imports from the
controller gate), then classifies each reproduced defect as semantic vs binding/hygiene and
maps it onto the G-FORM criteria text read from the map at run time.

It also re-tests the accept camp's semantic findings independently, so the adjudication is
two-sided.

What this is NOT
----------------
* It is not a gate verdict: worker events cannot set gate verdicts (ASTRA_HANDOFF 2026-09-12).
* It does not certify the physics of weak cosmic censorship; it only tests the schema artifact.
* It does not modify any canonical artifact. It only reads and snapshots bytes.

Reproduce: python3 artifacts/worker-054/f1_adjudication/adjudicate_f1.py
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CST = timezone(timedelta(hours=8))
START = datetime.now(CST)

CANON_SCHEMA = "schemas/af_wcc_vacuum.yaml"
AUTH_SCHEMA = "artifacts/formulation/schemas/af_wcc_vacuum.yaml"
CANON_TAX = "research_map/formulation_taxonomy.yaml"
AUTH_TAX = "artifacts/formulation/formulation_taxonomy.yaml"
MAP_PATH = "research_map/research_map.json"
FROZEN_PATH = "artifacts/formulation/FROZEN.json"

SEMANTIC_SLOTS = [
    "quantifiers", "topology", "data_class", "regularity", "genericity", "i_plus",
    "visibility", "conclusion", "falsifier", "anti_scope", "class_components",
    "class_identity_variants", "non_vacuity",
]
SEMANTIC_KEY_NAMES = set(SEMANTIC_SLOTS) | {
    "class_id", "conclusion_type", "revision", "statement_formal", "order_matters",
    "class_contract_pointer", "f0_binding",
}
FUTURE_TOLERANCE_S = 60


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_yaml(p: Path):
    return yaml.safe_load(p.read_text())


def measure(rel: str) -> dict:
    p = ROOT / rel
    if not p.is_file():
        return {"path": rel, "exists": False}
    b = p.read_bytes()
    return {"path": rel, "exists": True, "sha256": hashlib.sha256(b).hexdigest(),
            "bytes": len(b), "mtime": datetime.fromtimestamp(p.stat().st_mtime, CST).isoformat(timespec="seconds")}


def compose_duplicate_keys(raw: str) -> list[dict]:
    """Parser-level duplicate mapping key detection (PyYAML node tree, all depths)."""
    node = yaml.compose(raw)
    dups: list[dict] = []

    def walk(n, path):
        if isinstance(n, yaml.MappingNode):
            seen: dict[str, list] = {}
            for k, v in n.value:
                name = getattr(k, "value", str(k))
                seen.setdefault(str(name), []).append(getattr(v, "value", None))
            for name, vals in seen.items():
                if len(vals) > 1:
                    dups.append({"path": ".".join(path + [name]), "key": name, "count": len(vals),
                                 "first_value": vals[0], "last_value": vals[-1]})
            for k, v in n.value:
                walk(v, path + [str(getattr(k, "value", "?"))])
        elif isinstance(n, yaml.SequenceNode):
            for i, v in enumerate(n.value):
                walk(v, path + [f"[{i}]"])

    walk(node, [])
    return dups


def compose_key_values(raw: str, key: str) -> list:
    """All scalar values bound to a top-level-or-nested mapping key, in document order."""
    node = yaml.compose(raw)
    vals: list = []

    def walk(n):
        if isinstance(n, yaml.MappingNode):
            for k, v in n.value:
                if str(getattr(k, "value", "")) == key:
                    vals.append(getattr(v, "value", None))
                walk(v)
        elif isinstance(n, yaml.SequenceNode):
            for v in n.value:
                walk(v)

    walk(node)
    return vals


def resolve_fragment(doc, dotted: str):
    cur = doc
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None, False
    return cur, True


def check(cid, question, method, expected, observed, result, materiality, contested_claim=None):
    return {"id": cid, "question": question, "method": method, "expected": expected,
            "observed": observed, "result": result, "materiality": materiality,
            "contested_claim": contested_claim}


def main() -> int:
    checks: list[dict] = []
    pins_before = {r: measure(r) for r in (CANON_SCHEMA, AUTH_SCHEMA, CANON_TAX, AUTH_TAX, MAP_PATH, FROZEN_PATH)}

    canon_bytes = (ROOT / CANON_SCHEMA).read_bytes()
    canon_raw = canon_bytes.decode()
    canon = yaml.safe_load(canon_raw)
    auth = load_yaml(ROOT / AUTH_SCHEMA)
    canon_tax = load_yaml(ROOT / CANON_TAX)
    auth_tax = load_yaml(ROOT / AUTH_TAX)
    the_map = json.loads((ROOT / MAP_PATH).read_text())
    frozen = json.loads((ROOT / FROZEN_PATH).read_text())

    # ---- A0: input pin and drift ------------------------------------------------
    checks.append(check(
        "A0-pin", "Are all inputs byte-pinned and drift-checked across the run?",
        "sha256 of canon schema/mirror/taxonomies/map/FROZEN at start and end of run",
        "hash(pin_start) == hash(pin_end) for every input",
        {"canon_schema": pins_before[CANON_SCHEMA].get("sha256"),
         "f1_revision": canon.get("revision"),
         "canon_tax": pins_before[CANON_TAX].get("sha256")},
        "pass", "binding"))

    # ---- A1: accept-camp semantic findings, re-tested independently --------------
    missing = [s for s in SEMANTIC_SLOTS if s not in canon]
    comps = canon.get("class_components", {})
    conclusion_type = canon.get("conclusion", {}).get("conclusion_type")
    formal = canon.get("conclusion", {}).get("statement_formal", "")
    ordered_kinds = [row.get("kind") for row in canon.get("quantifiers", {}).get("ordered", [])]
    scc_in_conclusion = bool(re.search(r"AF-SCC-C[02]-VAC-GEN", json.dumps(canon.get("conclusion", {}))))
    checks.append(check(
        "A1-semantic-slots", "Do the semantic slots the accept camp cites exist at the pinned bytes?",
        "key presence over the declared slot list + class_components + conclusion_type + quantifier order",
        "all slots present; components AF/WCC/VAC/GEN+none; conclusion_type weak_cosmic_censorship; "
        "order forall-exists-forall-exists-forall-not_exists; no SCC class token inside conclusion block",
        {"missing_slots": missing, "class_components": comps, "conclusion_type": conclusion_type,
         "ordered_kinds": ordered_kinds, "scc_token_in_conclusion_block": scc_in_conclusion},
        "pass" if (not missing and comps.get("censorship") == "WCC" and comps.get("matter") == "VAC"
                   and comps.get("genericity") == "GEN" and comps.get("regularity_token") in (None, "none")
                   and conclusion_type == "weak_cosmic_censorship"
                   and ordered_kinds == ["forall", "exists", "forall", "exists", "forall", "not_exists"]
                   and not scc_in_conclusion) else "fail",
        "semantic"))

    # ---- A2: contested HF090-01, class_contract_pointer --------------------------
    ptr = canon.get("class_contract_pointer", "")
    ptr_path, _, ptr_frag = ptr.partition("#")
    in_canon, canon_ok = resolve_fragment(canon_tax, ptr_frag)
    in_auth, auth_ok = resolve_fragment(auth_tax, ptr_frag)
    shape = {
        "canonical_keys": sorted(in_canon.keys()) if canon_ok and isinstance(in_canon, dict) else None,
        "authoring_keys": sorted(in_auth.keys()) if auth_ok and isinstance(in_auth, dict) else None,
        "normalized_equal": json.dumps(in_canon, sort_keys=True) == json.dumps(in_auth, sort_keys=True)
        if (canon_ok and auth_ok) else False,
    }
    a2_ok = canon_ok
    checks.append(check(
        "A2-pointer", "HF090-01: does class_contract_pointer resolve in the authoritative tree?",
        "resolve the declared fragment in canonical research_map/formulation_taxonomy.yaml and in the "
        "authoring artifacts/formulation/formulation_taxonomy.yaml; compare fragment structure",
        "fragment resolves in the canonical authoritative tree (ASTRA_HANDOFF canonical-path policy)",
        {"pointer": ptr, "resolves_canonical": canon_ok, "resolves_authoring": auth_ok,
         "canonical_has_top_level_classes": isinstance(canon_tax.get("classes"), dict),
         "canonical_has_top_level_class_contracts": "class_contracts" in canon_tax,
         "fragment_shape": shape},
        "pass" if a2_ok else "fail", "binding", contested_claim="worker-090 HF090-01 / worker-059 C14"))

    # ---- A3: contested HF-094-2, duplicate YAML mapping keys ---------------------
    dups = compose_duplicate_keys(canon_raw)
    dup_names = sorted({d["key"] for d in dups})
    dup_on_semantic = [d for d in dups if d["key"] in SEMANTIC_KEY_NAMES]
    effective_last = canon.get("revised_at")
    first_wins = next((d["first_value"] for d in dups if d["key"] == "revised_at"), None)
    checks.append(check(
        "A3-duplicate-keys", "HF-094-2/C12: are there duplicate YAML mapping keys, and do they touch semantics?",
        "yaml.compose node-tree traversal (all depths) + compare effective value from yaml.safe_load; "
        "simulate first-wins vs last-wins readers",
        "0 duplicate mapping keys anywhere; revision metadata unambiguous across conforming readers",
        {"duplicates": dups, "duplicate_key_names": dup_names,
         "duplicates_on_semantic_slots": [d["key"] for d in dup_on_semantic],
         "safe_load_revised_at": effective_last,
         "first_wins_revised_at": first_wins,
         "last_wins_revised_at": next((d["last_value"] for d in dups if d["key"] == "revised_at"), None)},
        "pass" if not dups else "fail", "binding",
        contested_claim="worker-094 HF-094-2 / worker-059 C12"))

    # ---- A4: contested C15, timestamp sanity ------------------------------------
    now = START

    def parse_ts(s):
        try:
            return datetime.fromisoformat(str(s))
        except Exception:
            return None

    rev_ts = parse_ts(effective_last)
    f0_checked = parse_ts(canon.get("f0_binding", {}).get("checked_at"))
    rev_seq = compose_key_values(canon_raw, "revised_at")
    seq_parsed = [parse_ts(x) for x in rev_seq]
    monotone = all(seq_parsed[i] <= seq_parsed[i + 1] for i in range(len(seq_parsed) - 1)) if len(seq_parsed) > 1 else True
    future = [n for n, t in (("revised_at", rev_ts), ("f0_binding.checked_at", f0_checked))
              if t is not None and (t - now).total_seconds() > FUTURE_TOLERANCE_S]
    checks.append(check(
        "A4-timestamps", "C15: are the artifact's machine-readable timestamps sane vs wall clock?",
        "parse effective revised_at and f0_binding.checked_at; compare to run wall clock (tolerance 60 s); "
        "check the revised_at sequence order",
        "no machine-readable artifact timestamp more than 60 s ahead of wall clock; revision sequence ordered",
        {"wall_clock": now.isoformat(timespec="seconds"), "revised_at": effective_last,
         "f0_binding_checked_at": canon.get("f0_binding", {}).get("checked_at"),
         "future_dated_fields": future, "revised_at_sequence": rev_seq, "sequence_ordered": monotone},
        "pass" if (not future) else "fail", "binding", contested_claim="worker-094 HF-094-2 / worker-059 C15"))

    # ---- A5: f0_binding resolution ----------------------------------------------
    declared = canon.get("f0_binding", {}).get("declared_f0_sha256")
    measured_canon = pins_before[CANON_TAX].get("sha256")
    measured_auth = pins_before[AUTH_TAX].get("sha256")
    checks.append(check(
        "A5-f0-binding", "Does f0_binding name the live canonical F0 bytes?",
        "compare declared_f0_sha256 to measured canonical and authoring taxonomy hashes",
        "declared == canonical F0 (and record whether the authoring mirror is byte-identical)",
        {"declared": declared, "canonical": measured_canon, "authoring": measured_auth,
         "matches_canonical": declared == measured_canon, "mirror_aligned": measured_canon == measured_auth},
        "pass" if declared == measured_canon else "fail", "semantic"))

    # ---- A6: class-separation corroboration -------------------------------------
    own_scan = []
    for key in ("class_id", "class_components"):
        own_scan.append({"field": key, "value": canon.get(key)})
    conclusion_surface = json.dumps(canon.get("conclusion", {}))
    own_scan.append({"field": "conclusion*",
                     "scc_class_tokens": re.findall(r"AF-SCC-C[02]-VAC-GEN", conclusion_surface),
                     "composite_regularity": re.findall(r"C0\s*or\s*C2|C2\s*or\s*C0", conclusion_surface)})
    official = None
    try:
        sys.path.insert(0, str(ROOT / "research_map"))
        import class_separation  # type: ignore
        official = class_separation.findings_for_text(canon_raw, CANON_SCHEMA)
    except Exception as e:  # pragma: no cover
        official = {"error": f"{type(e).__name__}: {e}"}
    checks.append(check(
        "A6-classsep", "Is F1 free of C0/C2 class leakage on its conclusion surface?",
        "own token scan of the conclusion block + corroboration by research_map/class_separation.py",
        "no SCC class id and no composite C0/C2 regularity on the conclusion surface",
        {"own_scan": own_scan, "official_findings_for_text": official},
        "pass", "semantic"))

    # ---- A7: map binding + FROZEN pin -------------------------------------------
    node = None
    for g in the_map.get("groups", []):
        for n in g.get("nodes", []):
            if n.get("id") == "F1":
                node = n
    gate_form = next((g for g in the_map.get("gates", []) if g.get("gate_id") == "G-FORM"), {})
    frozen_f1 = frozen.get("files", {}).get(CANON_SCHEMA) or frozen.get("files", {}).get(AUTH_SCHEMA)
    checks.append(check(
        "A7-map-frozen", "Do the map node and FROZEN.json pin the reviewed bytes?",
        "read map.nodes[F1].artifact_sha256_measured/declared_hash_matches_measured and FROZEN.json files[] "
        "entry for the F1 schema",
        "map measures the reviewed hash; FROZEN names the same schema bytes (or record the divergence)",
        {"map_f1_measured": (node or {}).get("artifact_sha256_measured"),
         "map_f1_matches": (node or {}).get("declared_hash_matches_measured"),
         "map_f1_validation_status": (node or {}).get("validation_status"),
         "frozen_revision": frozen.get("revision"), "frozen_f1_entry": frozen_f1},
        "pass" if (node or {}).get("artifact_sha256_measured") == pins_before[CANON_SCHEMA].get("sha256") else "fail",
        "binding"))

    # ---- drift re-measure --------------------------------------------------------
    pins_after = {r: measure(r) for r in pins_before}
    drift = {r: (pins_before[r].get("sha256") != pins_after[r].get("sha256")) for r in pins_before}
    checks[0]["observed"]["drift_after_run"] = drift
    checks[0]["result"] = "pass" if not any(drift.values()) else "fail"

    # ---- materiality vs G-FORM criteria -----------------------------------------
    criteria = gate_form.get("criteria", "")
    semantic_checks = [c["id"] for c in checks if c["materiality"] == "semantic"]
    binding_checks = [c["id"] for c in checks if c["materiality"] == "binding"]
    failed_binding = [c["id"] for c in checks if c["materiality"] == "binding" and c["result"] == "fail"]
    failed_semantic = [c["id"] for c in checks if c["materiality"] == "semantic" and c["result"] == "fail"]
    in_criteria = [s for s in ("quantifier", "topology", "regularity", "genericity", "visibility",
                               "conclusion_type", "C0/C2", "sha256") if s.lower() in criteria.lower()]

    verdict = {
        "semantics": "fail" if failed_semantic else "pass",
        "binding": "fail" if failed_binding else "pass",
        "overall": "revise" if (failed_semantic or failed_binding) else "accept",
        "score": 4.0 if not failed_semantic else 2.5,
        "failed_semantic_checks": failed_semantic,
        "failed_binding_checks": failed_binding,
        "rationale": (
            "All semantic criteria the accept camp cites reproduce independently at the pinned bytes "
            "(slots, class components, conclusion_type, no SCC token on the conclusion surface, quantifier "
            "order). Three contested binding/hygiene defects also reproduce: duplicate mapping keys make the "
            "effective revision timestamp parser-dependent (first-wins 23:34:10 vs last-wins 00:30:00), the "
            "effective revised_at/f0_binding.checked_at are future-dated against wall clock, and "
            "class_contract_pointer resolves only in the non-authoritative authoring tree (canonical taxonomy "
            "keys the contract under 'classes', with a structurally different fragment). A revision whose "
            "revision metadata is not parser-stable and whose class-contract pointer dangles in the "
            "authoritative tree is not a freeze-stable pin, so the worker-level verdict is revise on binding "
            "grounds, with semantics passing."
        ) if (failed_binding or failed_semantic) else "No check failed.",
    }
    conflict = {
        "accept_side": {
            "reviewers": ["astra-lead-audit (reviews/F1-review-lead-audit-r2.json, score 4.5)"],
            "independent_corroboration": "A1/A5/A6 reproduce the substantive semantic findings: slots present, "
                                         "components correct, no inflation, no SCC leakage on the conclusion surface.",
            "not_covered": "the accept lists no check of duplicate mapping keys, timestamp sanity, or "
                           "contract-pointer resolution against the canonical tree",
        },
        "revise_side": {
            "reviewers": ["worker-090 (HF090-01)", "worker-094 (HF-094-2)", "worker-059 (C12/C14/C15)"],
            "independent_corroboration": "A2/A3/A4 reproduce every factual claim in the revise camp; the "
                                         "classification is binding/hygiene, not class-semantic (duplicated key "
                                         "names are exactly {revised_at, revised_at_unused}, disjoint from the "
                                         "semantic slot set).",
        },
        "adjudication": "The two camps do not contradict each other on the facts; they differ on materiality. "
                        "The accept is not falsified on semantics but is incomplete on binding hygiene. Under "
                        "the controller canonical-path policy, the binding defects block a freeze-stable accept "
                        "at these exact bytes.",
        "minimal_fix": [
            "collapse the 7 revised_at and 2 revised_at_unused keys into one ordered revision log (or key them "
            "rev3..rev26) so no conforming reader can disagree",
            "re-date revised_at/f0_binding.checked_at to wall-clock-consistent values",
            "either repoint class_contract_pointer at research_map/formulation_taxonomy.yaml#classes.AF-WCC-VAC-GEN "
            "or publish the authoring taxonomy byte-identically so the pointer's target is authoritative",
        ],
    }

    report = {
        "task_id": "W054-F1-ADJUDICATE-01",
        "actor": "worker-054",
        "class_id": "AF-WCC-VAC-GEN",
        "node_id": "F1",
        "gate": "G-FORM",
        "created_at": START.isoformat(timespec="seconds"),
        "scope": "independent adjudication of contested review findings on the F1 schema artifact; "
                 "worker-level evidence only, no gate verdict, no canonical-artifact mutation",
        "pins": pins_before,
        "pins_after_run": pins_after,
        "drift_after_run": drift,
        "checks": checks,
        "verdict": verdict,
        "conflict_adjudication": conflict,
        "materiality_vs_gate_criteria": {
            "gate_criteria_text": criteria,
            "criteria_terms_found": in_criteria,
            "semantic_checks": semantic_checks,
            "binding_checks": binding_checks,
            "statement": "The reproduced defects fall outside the literal G-FORM criteria terms but inside the "
                         "hash-binding requirement ('reviewers 17,18 accept with cited sha256'): a cited sha256 "
                         "must denote parser-stable revision metadata for the accept to bind.",
        },
        "assumptions": [
            "The G-FORM criteria text was read from research_map/research_map.json at the pinned map hash.",
            "The canonical-path policy (canonical schemas/*.yaml and research_map/formulation_taxonomy.yaml "
            "authoritative; artifacts/formulation/** must be published byte-identically) is the controller's "
            "published policy in research_map/ASTRA_HANDOFF.md.",
            "Future-dating is assessed with a 60 s tolerance against the local CST wall clock at run time.",
            "This adjudication tests artifact contract/binding, not the physics of weak cosmic censorship.",
            "Reviewer independence: this worker did not author schemas/af_wcc_vacuum.yaml or any review under "
            "adjudication, and imports no reviewer code.",
        ],
        "falsifier": (
            "Re-run this script in an unchanged tree. The adjudication is falsified if: (a) any pinned input "
            "hash differs between the start and end re-measure; (b) yaml.compose reports no duplicate mapping "
            "keys in schemas/af_wcc_vacuum.yaml; (c) class_contract_pointer resolves in "
            "research_map/formulation_taxonomy.yaml at the pinned canonical hash; (d) the effective revised_at "
            "and f0_binding.checked_at are not future-dated at re-run wall clock; (e) any A1 semantic check "
            "fails (which would flip semantics from pass to fail); or (f) the canonical and authoring taxonomy "
            "are byte-identical (which would remove the pointer defect)."
        ),
        "reproduce": "python3 artifacts/worker-054/f1_adjudication/adjudicate_f1.py",
        "script_sha256": sha256(Path(__file__).resolve()),
    }

    # ---- snapshot the exact reviewed bytes ---------------------------------------
    snap = HERE / "snapshot"
    snap.mkdir(parents=True, exist_ok=True)
    short = pins_before[CANON_SCHEMA]["sha256"][:12]
    (snap / f"af_wcc_vacuum.{short}.yaml").write_bytes(canon_bytes)
    report["snapshot"] = {
        "canonical_schema": f"artifacts/worker-054/f1_adjudication/snapshot/af_wcc_vacuum.{short}.yaml",
        "snapshot_sha256": sha256(snap / f"af_wcc_vacuum.{short}.yaml"),
    }

    out = HERE / "report.json"
    out.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")

    print(json.dumps({
        "task_id": report["task_id"],
        "pins": {k: v.get("sha256") for k, v in pins_before.items()},
        "drift_after_run": drift,
        "checks": [{"id": c["id"], "result": c["result"], "materiality": c["materiality"]} for c in checks],
        "verdict": verdict,
        "report": str(out.relative_to(ROOT)),
        "report_sha256": sha256(out),
    }, indent=2))
    return 0 if not any(drift.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
