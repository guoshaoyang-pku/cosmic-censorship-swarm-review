#!/usr/bin/env python3
"""W060-F2B-REV12-CLOSURE-VERIFY-01.

Independent, hash-pinned closure verification of the canonical F2b class schema
`schemas/af_scc_c0_vacuum.yaml` (class AF-SCC-C0-VAC-GEN) at the revision published
with FROZEN.json revision 27 (revised_at 2026-09-12T00:31:41+08:00).

The question this task answers: at the new canonical bytes, which of the hash-bound
blocking findings recorded against the previous F2b revision (1bb78ce9b357) are
actually CLOSED, and which survive?  Additionally: do the G-FORM structural criteria
still hold at the new bytes?

This is worker evidence only.  It emits no gate verdict, no node completion, and no
validation_status promotion; controller and group leads own those.

Checks (all at one pinned sha256):
  A  pin binding + before/after stability (moving-target guard)
  CL1 duplicate top-level YAML mapping keys (rev11 finding: revised_at x7, revised_at_unused x2)
  CL2 clock discipline: revised_at not future-dated vs wall clock, and <= FROZEN frozen_at
  CL3 class_contract_pointer authority: resolves inside the canonical taxonomy, and its
      declared F0 pin equals the measured canonical taxonomy hash
  CL4 containment-direction consistency inside implication_ledger (rev11 finding:
      forbidden_transfers[0].reason "C2 is a strictly larger extension class")
  CL5 class separation detector + standing regression
  CL6 G-FORM structural field presence + C0-only conclusion identity + no asserted composite
  CL7 publication binding: canonical == authoring == FROZEN.json manifest entry
  CL8 declared consistency-evidence hash resolves on disk
  CTL mutation controls M1-M6 + positive control P0

Usage:
  python3 verify_f2b_rev12.py --pin <sha256> [--canonical schemas/af_scc_c0_vacuum.yaml]
                              [--out evidence.json]
Exit codes: 0 no hard finding (verdict PASS); 1 hard finding survives (verdict REVISE);
            2 hash drift from the pin (verdict MOVING_TARGET, no closure claim made).
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research_map"))
import class_separation as cs  # noqa: E402

import yaml  # noqa: E402

CLASS_ID = "AF-SCC-C0-VAC-GEN"
SIBLING = "AF-SCC-C2-VAC-GEN"
NODE_ID = "F2b"
GATE = "G-FORM"
CANONICAL = "schemas/af_scc_c0_vacuum.yaml"
AUTHORING = "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
SIBLING_PATH = "schemas/af_scc_c2_vacuum.yaml"
TAXONOMY = "research_map/formulation_taxonomy.yaml"
FROZEN = "artifacts/formulation/FROZEN.json"

GATE_FIELDS = {
    "quantifiers": [
        "quantifiers.formal", "quantifiers.ordered", "quantifiers.quantifier_class",
        "quantifiers.negation", "quantifiers.domains.D0.definition",
        "quantifiers.domains.D1.definition", "quantifiers.domains.D2.definition",
        "quantifiers.domains.D3.definition",
    ],
    "topology": [
        "topology.spacetime_dimension", "topology.slice_topology", "topology.end_structure",
        "topology.conformal_boundary", "topology.I_plus_topology",
        "topology.extension_topology", "topology.forbidden",
    ],
    "regularity": [
        "regularity.data_regularity", "regularity.solution_regularity",
        "regularity.i_plus_regularity", "regularity.extension_regularity",
        "regularity.extension_regularity_exact", "regularity.must_not_conflate",
    ],
    "genericity": [
        "genericity.kind", "genericity.ambient_space", "genericity.topology_or_measure",
        "genericity.generic_set", "genericity.excluded_set", "genericity.is_part_of_class",
        "genericity.class_change_warning",
    ],
    "i_plus": ["i_plus.role", "i_plus.in_conclusion", "i_plus.definition", "i_plus.forbidden"],
    "visibility": [
        "visibility.role", "visibility.reason", "visibility.visible_singularity_is_wcc",
        "visibility.forbidden_falsifier",
    ],
    "conclusion_type": ["conclusion.conclusion_type"],
    "extension_predicate": ["extension_predicate.name", "extension_predicate.definition"],
    "data_class": ["data_class"],
    "non_vacuity": ["non_vacuity"],
}

COMPOSITE = re.compile(
    r"c\s*0\s*(?:or|and|/|,|\+|\s)\s*c\s*2"
    r"|c\s*2\s*(?:or|and|/|,|\+|\s)\s*c\s*0"
    r"|c0c2|c2c0", re.I)
DENIAL = re.compile(
    r"\b(no|not|never|nor|without|must\s+not|may\s+not|do(?:es)?\s+not|is\s+not|"
    r"are\s+not|cannot|prohibit\w*|forbid\w*|excluded?)\b", re.I)
KEYLINE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:")
NEGATIVE_KEYS = re.compile(
    r"(not_this_class|phrases_that_are_not|forbidden|must_not|anti_scope|must_not_conflate)", re.I)
MERGE_ASSERT = re.compile(
    r"\b(is|are|form|constitute|share|belongs?\s+to)\b[^.]{0,40}\b(one|a\s+single|the\s+same)\b"
    r"[^.]{0,30}\bclass\b", re.I)


def _nearest_key(lines, upto):
    for j in range(upto - 1, max(-1, upto - 40), -1):
        if j < 0:
            break
        m = KEYLINE.match(lines[j])
        if m and not lines[j].lstrip().startswith("-"):
            return m.group(1)
    return None


def classify_composites(text):
    """Classify every composite C0/C2 occurrence: only assertions / bare composites fail."""
    lines = text.splitlines()
    rows = []
    for i, line in enumerate(lines, 1):
        for m in COMPOSITE.finditer(line):
            win = line[max(0, m.start() - 100):m.end() + 100]
            if MERGE_ASSERT.search(win):
                kind = "assertion"
            elif DENIAL.search(win):
                kind = "denial_context"
            elif NEGATIVE_KEYS.search(_nearest_key(lines, i) or ""):
                kind = "negative_section"
            else:
                kind = "bare_composite"
            rows.append({"line": i, "match": m.group(0), "kind": kind,
                         "context": win.strip()[:180]})
    return rows

C2_LARGER = re.compile(
    r"c\s*2\s+is\s+a\s+strictly\s+larger\s+extension\s+class"
    r"|\bc\s*2\s+extension\s+class\s+is\s+strictly\s+larger", re.I)
C2_SMALLER = re.compile(
    r"c\s*2\s+is\s+a\s+strictly\s+smaller\s+extension\s+class"
    r"|\bc\s*2\s+extension\s+class\s+is\s+strictly\s+smaller", re.I)
CONTAINMENT_C0_HAS_C2 = re.compile(
    r"E_?\{?C0\}?\s+contains\b[^.]*E_?\{?C\s*\^?\{?1,1", re.I)
F2A_C2_SUBSET_C0 = re.compile(r"E_?\{?C2\}?\s+subset\s+of\s+E_?\{?C0", re.I)


def now() -> str:
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def get(d, path, default=None):
    cur = d
    for k in path.split("."):
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def parse_ts(s):
    try:
        return _dt.datetime.fromisoformat(str(s))
    except Exception:
        return None


def top_level_duplicate_keys(text: str):
    """Return {key: [line numbers]} for duplicate keys in the root YAML mapping."""
    node = yaml.compose(text)
    if not isinstance(node, yaml.MappingNode):
        return {}
    seen = {}
    for k_node, _v in node.value:
        k = getattr(k_node, "value", None)
        seen.setdefault(k, []).append(k_node.start_mark.line + 1)
    return {k: lines for k, lines in seen.items() if len(lines) > 1}


def gate_fields(doc):
    out, missing = {}, []
    for section, paths in GATE_FIELDS.items():
        miss = [p for p in paths if get(doc, p) in (None, "", [], {})]
        out[section] = {"missing": miss, "ok": not miss}
        missing += miss
    out["ok"] = not missing
    out["missing"] = missing
    return out


def composites_in(text):
    return [(i, m.group(0)) for i, line in enumerate(text.splitlines(), 1)
            for m in COMPOSITE.finditer(line)]


def run_checks(text, doc, *, frozen, taxonomy_sha, taxonomy_doc, sibling_text,
               authoring_sha, canonical_sha, consistency_measured_sha, wall):
    """All closure checks as a dict of {id: (ok, detail)}. Pure function over inputs,
    so mutation controls can call it on modified text/doc."""
    c = {}

    dup = top_level_duplicate_keys(text)
    raw_counts = {
        "revised_at": len(re.findall(r"(?m)^revised_at\s*:", text)),
        "revised_at_unused": len(re.findall(r"(?m)^revised_at_unused\s*:", text)),
    }
    c["CL1_duplicate_top_level_keys"] = (
        not dup and raw_counts["revised_at"] == 1 and raw_counts["revised_at_unused"] == 0,
        {"duplicate_keys": dup, "raw_top_level_counts": raw_counts,
         "closed_finding": "rev11 revised_at x7 duplicate + revised_at_unused x2"})

    rev = parse_ts(get(doc, "revised_at"))
    frozen_at = parse_ts(frozen.get("frozen_at"))
    c["CL2_clock_discipline"] = (
        rev is not None and rev <= wall and (frozen_at is None or rev <= frozen_at),
        {"revised_at": get(doc, "revised_at"), "wall_clock_at_check": wall.isoformat(),
         "frozen_at": frozen.get("frozen_at"),
         "closed_finding": "rev11 effective revised_at 00:30:00 was future-dated at review"})

    ptr = str(get(doc, "class_contract_pointer", ""))
    ptr_path, _, ptr_anchor = ptr.partition("#")
    resolved = None
    try:
        if ptr_path.split("/")[0] == "research_map" and ptr_anchor.startswith("classes."):
            resolved = get(taxonomy_doc, ptr_anchor)
    except Exception:
        resolved = None
    declared_f0 = get(doc, "f0_binding.declared_f0_sha256")
    supp = str(get(doc, "class_contract_supplement_pointer", ""))
    supp_path, _, supp_anchor = supp.partition("#")
    supp_resolved = None
    try:
        if supp_path and supp_anchor:
            supp_doc = yaml.safe_load((ROOT / supp_path).read_text())
            supp_resolved = get(supp_doc, supp_anchor)
    except Exception:
        supp_resolved = None
    c["CL3_pointer_authority"] = (
        resolved is not None and declared_f0 == taxonomy_sha,
        {"class_contract_pointer": ptr, "pointer_resolves_in_canonical": resolved is not None,
         "measured_canonical_taxonomy_sha256": taxonomy_sha,
         "f0_binding_declared_sha256": declared_f0,
         "supplement_pointer": supp, "supplement_resolves_in_authoring": supp_resolved is not None,
         "closed_finding": "rev11 pointer resolved into the authoring tree with no hash pin"})

    cont = str(get(doc, "implication_ledger.extension_class_containment", ""))
    reasons = []
    for key in ("implication_ledger.forbidden_transfers", "implication_ledger.one_way_entailments"):
        for i, row in enumerate(get(doc, key, []) or []):
            if isinstance(row, dict):
                reasons.append((f"{key}[{i}]", str(row.get("reason", "")),
                                str(row.get("from", "")), str(row.get("to", ""))))
    larger = [(k, r) for k, r, _f, _t in reasons if C2_LARGER.search(r)]
    smaller = [(k, r) for k, r, _f, _t in reasons if C2_SMALLER.search(r)]
    # containment direction derivable from own line or from the sibling C2 schema
    c0_has_c2 = bool(CONTAINMENT_C0_HAS_C2.search(cont))
    sib_says = bool(F2A_C2_SUBSET_C0.search(sibling_text))
    direction_known = c0_has_c2 or sib_says
    contradiction = bool(larger) if direction_known else None
    c["CL4_containment_direction"] = (
        (contradiction is False) if direction_known else False,
        {"containment_line": cont,
         "derived_ordering": "E_C0 >= E_C2 (C2 is the strictly smaller extension class)"
                             if direction_known else "not derivable",
         "larger_claims": [{"where": k, "reason": r} for k, r in larger],
         "smaller_claims": [{"where": k, "reason": r} for k, r in smaller],
         "sibling_agrees_C2_subset_C0": sib_says,
         "surviving_finding": ("forbidden_transfers[0].reason asserts C2 is a strictly larger "
                               "extension class, contradicting this file's own "
                               "extension_class_containment and the sibling C2 schema")
                              if contradiction else None})

    hard = cs.findings_for_text(text, CANONICAL)
    reg = cs.regression()
    c["CL5_class_separation"] = (
        not hard and bool(reg.get("verdict") == "PASS"),
        {"detector_findings": hard, "regression": reg})

    gf = gate_fields(doc)
    ctype = str(get(doc, "conclusion.conclusion_type", ""))
    comp = classify_composites(text)
    bad_comp = [x for x in comp if x["kind"] in ("assertion", "bare_composite")]
    identity_ok = ("c2" not in ctype.lower()) and ("scc_c0" in ctype.lower())
    c["CL6_structural_and_identity"] = (
        gf["ok"] and identity_ok and not bad_comp,
        {"gate_fields": gf, "conclusion_type": ctype, "c0_only_identity": identity_ok,
         "composite_occurrences": comp,
         "asserted_or_bare_composites": bad_comp,
         "benign_composites": [x for x in comp if x["kind"] not in ("assertion", "bare_composite")]})

    manifest = (frozen.get("files") or {}).get(CANONICAL, {}).get("sha256")
    manifest_auth = (frozen.get("files") or {}).get(AUTHORING, {}).get("sha256")
    c["CL7_publication_binding"] = (
        canonical_sha == authoring_sha == manifest == manifest_auth,
        {"canonical_sha256": canonical_sha, "authoring_sha256": authoring_sha,
         "frozen_manifest_canonical": manifest, "frozen_manifest_authoring": manifest_auth,
         "frozen_revision": frozen.get("revision"),
         "closed_finding": "rev11 round published dual-tree/canonical mismatches"})

    consistency_path = get(doc, "f0_binding.consistency_evidence")
    declared_ce = get(doc, "f0_binding.consistency_evidence_sha256")
    c["CL8_consistency_evidence"] = (
        bool(consistency_measured_sha) and declared_ce == consistency_measured_sha,
        {"consistency_evidence_path": consistency_path,
         "consistency_evidence_sha256_declared": declared_ce,
         "consistency_evidence_sha256_measured_at_check_instant": consistency_measured_sha,
         "consistency_evidence_mtime":
             _dt.datetime.fromtimestamp((ROOT / str(consistency_path)).stat().st_mtime).astimezone().isoformat(timespec="seconds")
             if consistency_path and (ROOT / str(consistency_path)).exists() else None,
         "schema_revised_at": get(doc, "revised_at"),
         "note": "the evidence file is regenerated by the formulation pipeline and is itself a "
                 "moving artifact; declared-vs-measured comparison is single-instant",
         "resolves_on_disk": bool(consistency_measured_sha) and declared_ce == consistency_measured_sha})

    return {k: {"ok": bool(v[0]), "detail": v[1]} for k, v in c.items()}


def mutate(text, kind, real_consistency_sha=None):
    if kind == "M1_duplicate_revised_at":
        return text.replace('revised_at: "2026-09-12T00:31:41+08:00"',
                            'revised_at: "2026-09-12T00:31:41+08:00"\n'
                            'revised_at: "2026-09-12T00:31:42+08:00"', 1)
    if kind == "M2_future_revised_at":
        return text.replace('revised_at: "2026-09-12T00:31:41+08:00"',
                            'revised_at: "2099-01-01T00:00:00+08:00"', 1)
    if kind == "M3_authoring_pointer":
        return text.replace(
            "class_contract_pointer: research_map/formulation_taxonomy.yaml#classes.AF-SCC-C0-VAC-GEN",
            "class_contract_pointer: artifacts/formulation/formulation_taxonomy.yaml#class_contracts.AF-SCC-C0-VAC-GEN", 1)
    if kind == "M4_corrected_containment":
        return text.replace("C2 is a strictly larger extension class",
                            "C2 is a strictly smaller extension class")
    if kind == "M5_composite_conclusion":
        return text.replace("conclusion_type: scc_c0_future_inextendibility",
                            "conclusion_type: scc_c0_or_c2_future_inextendibility", 1)
    if kind == "M6_missing_visibility":
        return re.sub(r"(?m)^visibility:\n(?:[ \t].*\n)*", "", text, count=1)
    if kind == "M7_consistency_pin":
        declared = re.search(r'consistency_evidence_sha256:\s*"([0-9a-f]{64})"', text)
        if declared and real_consistency_sha:
            return text.replace(declared.group(1), real_consistency_sha)
        return text
    raise ValueError(kind)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pin", required=True)
    ap.add_argument("--canonical", default=CANONICAL)
    ap.add_argument("--out", default=str(Path(__file__).parent / "evidence.json"))
    args = ap.parse_args()

    canonical = ROOT / args.canonical
    authoring = ROOT / AUTHORING
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    wall = _dt.datetime.now().astimezone()
    t0 = now()

    body = canonical.read_bytes()
    measured0 = sha256_bytes(body)
    if measured0 != args.pin.lower():
        drift = {"task_id": "W060-F2B-REV12-CLOSURE-VERIFY-01", "actor": "worker-060",
                 "started_at": t0, "finished_at": now(), "verdict": "MOVING_TARGET",
                 "pinned_sha256": args.pin.lower(), "measured_sha256": measured0,
                 "note": "canonical bytes differ from the pin; no closure claim is made"}
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(drift, indent=1) + "\n")
        print(json.dumps(drift, indent=1))
        return 2

    text = body.decode("utf-8")
    doc = yaml.safe_load(text)
    frozen = json.loads((ROOT / FROZEN).read_text())
    taxonomy_sha = sha256_file(ROOT / TAXONOMY)
    taxonomy_doc = yaml.safe_load((ROOT / TAXONOMY).read_text())
    sibling_text = (ROOT / SIBLING_PATH).read_text()
    authoring_sha = sha256_file(authoring)
    consistency_path = get(doc, "f0_binding.consistency_evidence")
    consistency_measured_sha = (
        sha256_file(ROOT / str(consistency_path))
        if consistency_path and (ROOT / str(consistency_path)).exists() else None)

    checks = run_checks(text, doc, frozen=frozen, taxonomy_sha=taxonomy_sha,
                        taxonomy_doc=taxonomy_doc, sibling_text=sibling_text,
                        authoring_sha=authoring_sha, canonical_sha=measured0,
                        consistency_measured_sha=consistency_measured_sha, wall=wall)

    # --- controls -------------------------------------------------------------
    def expect(kind, check_id, want_ok):
        mtext = mutate(text, kind, real_consistency_sha=consistency_measured_sha)
        mdoc = yaml.safe_load(mtext)
        mres = run_checks(mtext, mdoc, frozen=frozen, taxonomy_sha=taxonomy_sha,
                          taxonomy_doc=taxonomy_doc, sibling_text=sibling_text,
                          authoring_sha=authoring_sha, canonical_sha=measured0,
                          consistency_measured_sha=consistency_measured_sha, wall=wall)
        got = mres[check_id]["ok"]
        return {"mutant": kind, "check": check_id, "expected_ok": want_ok,
                "observed_ok": got, "flipped": got == want_ok,
                "name": "flips_to_expected_state"}

    controls = [
        expect("M1_duplicate_revised_at", "CL1_duplicate_top_level_keys", False),
        expect("M2_future_revised_at", "CL2_clock_discipline", False),
        expect("M3_authoring_pointer", "CL3_pointer_authority", False),
        expect("M4_corrected_containment", "CL4_containment_direction", True),
        expect("M5_composite_conclusion", "CL6_structural_and_identity", False),
        expect("M6_missing_visibility", "CL6_structural_and_identity", False),
        expect("M7_consistency_pin", "CL8_consistency_evidence", True),
    ]
    controls_ok = all(x["flipped"] for x in controls)
    p0 = {k: v["ok"] for k, v in checks.items()}

    failed = [k for k, v in checks.items() if not v["ok"]]
    hard_findings = []
    if not checks["CL4_containment_direction"]["ok"]:
        hard_findings.append({
            "id": "HF-060-F2B-1",
            "severity": "hard",
            "gate_relevance": "G-FORM class-conclusion/transfer hygiene at the asserted "
                              "transfer surface (implication_ledger.forbidden_transfers)",
            "axis": "internal semantic consistency of the C0/C2 extension-class ordering",
            "finding": ("implication_ledger.forbidden_transfers[0].reason states 'C2 is a "
                        "strictly larger extension class', which contradicts this file's own "
                        "extension_class_containment (E_C0 contains ... E_C2) and the sibling "
                        "C2 schema (E_C2 subset of E_C0). The sentence's conclusion "
                        "('C2-inextendibility is strictly weaker') is correct; its stated "
                        "premise is inverted."),
            "line": next((i for i, l in enumerate(text.splitlines(), 1)
                          if C2_LARGER.search(l)), None),
            "repair": "replace 'strictly larger' with 'strictly smaller'",
            "falsifier": ("show an extension-set reading under which the C2 extension class is "
                          "strictly larger than the C0 extension class, i.e. E_C2 strictly "
                          "contains E_C0 with the file's own definitions of C0/C2 metric "
                          "extensions"),
            "survives_from": "worker-058 / worker-008 finding at rev11 "
                             "(implication_ledger.forbidden_transfers[0].reason, then line 251)",
        })
    if not checks["CL8_consistency_evidence"]["ok"]:
        d8 = checks["CL8_consistency_evidence"]["detail"]
        hard_findings.append({
            "id": "HF-060-F2B-2",
            "severity": "minor",
            "gate_relevance": "G-FORM evidence binding: f0_binding declares a hash pin that does "
                              "not resolve to the file on disk at review time",
            "axis": "declared-vs-measured hash binding of consistency evidence",
            "finding": (f"f0_binding.consistency_evidence_sha256 is "
                        f"{str(d8['consistency_evidence_sha256_declared'])[:12]} but "
                        f"{d8['consistency_evidence_path']} measures "
                        f"{str(d8['consistency_evidence_sha256_measured_at_check_instant'])[:12]} "
                        f"on disk (mtime {d8['consistency_evidence_mtime']}, schema revised_at "
                        f"{d8['schema_revised_at']}); the evidence file was regenerated after "
                        "the schema wrote the pin, or the pin was stale at publication"),
            "repair": "re-run the consistency check at the current schema hash and refresh "
                      "f0_binding.consistency_evidence_sha256 (do not relax the check)",
            "falsifier": ("at schema sha256 " + measured0 + ", show that "
                          f"{d8['consistency_evidence_path']} measures "
                          f"{d8['consistency_evidence_sha256_declared']}"),
        })

    verdict = "REVISE" if hard_findings else "PASS"
    final_sha = sha256_file(canonical)
    stable = final_sha == measured0

    snapdir = out_path.parent / "snapshots"
    snapdir.mkdir(parents=True, exist_ok=True)
    snapshot = snapdir / f"af_scc_c0_vacuum.{measured0[:12]}.yaml"
    if not snapshot.exists():
        shutil.copyfile(canonical, snapshot)

    ev = {
        "task_id": "W060-F2B-REV12-CLOSURE-VERIFY-01",
        "actor": "worker-060",
        "role": "bounded_execution_worker",
        "node_id": NODE_ID,
        "class_id": CLASS_ID,
        "gate": GATE,
        "started_at": t0,
        "finished_at": now(),
        "wall_clock_at_check": wall.isoformat(),
        "canonical_path": args.canonical,
        "pinned_sha256": args.pin.lower(),
        "measured_sha256": measured0,
        "final_measured_sha256": final_sha,
        "stable_during_run": stable,
        "snapshot_path": str(snapshot.relative_to(ROOT)),
        "snapshot_sha256": sha256_file(snapshot),
        "frozen_revision": frozen.get("revision"),
        "frozen_frozen_at": frozen.get("frozen_at"),
        "verdict": verdict,
        "failed_checks": failed,
        "hard_findings": hard_findings,
        "closure": {
            "closed": [k for k, v in checks.items() if v["ok"]],
            "survives": [k for k, v in checks.items() if not v["ok"]],
        },
        "checks": checks,
        "controls": controls,
        "controls_ok": controls_ok,
        "positive_control_p0": p0,
        "falsifier": (
            "At the reviewed sha256, the closure claim is refuted by any of: (a) a duplicate "
            "top-level YAML key or revised_at_unused present; (b) revised_at later than the "
            "run wall clock or later than FROZEN.frozen_at; (c) class_contract_pointer not "
            "resolving under research_map/formulation_taxonomy.yaml#classes.<CLASS> or its "
            "declared F0 hash differing from the measured canonical taxonomy hash; (d) a "
            "containment-direction contradiction (C2 called strictly larger while E_C0 is "
            "declared to contain E_C2); (e) a class-separation finding or a failing standing "
            "regression; (f) a missing G-FORM criterion block or a non-C0 conclusion identity; "
            "(g) canonical != authoring != FROZEN manifest; (h) hash drift during the window."
        ),
        "next_falsifier": (
            "Re-run with --pin <new canonical sha256>. This closure matrix binds only "
            f"{measured0[:12]}; it does not transfer to any other revision."
        ),
        "authority_note": (
            "Worker evidence only. No gate verdict, no node completion, no validation_status "
            "promotion. The surviving item is a schema-hygiene repair owned by lead-formulation; "
            "whether it blocks G-FORM is the audit lead's / controller's call."
        ),
        "detector_refs": [
            "research_map/class_separation.py",
            "research_map/formulation_taxonomy.yaml#" + taxonomy_sha[:12],
            SIBLING_PATH + "#" + sha256_file(ROOT / SIBLING_PATH)[:12],
            "reviews/F2b-review-18.json",
            "runtime/state/current_checkpoint.json",
        ],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(ev, indent=1) + "\n")
    print(json.dumps({k: ev[k] for k in (
        "task_id", "node_id", "class_id", "measured_sha256", "verdict",
        "failed_checks", "hard_findings", "controls_ok")}, indent=1))
    return 0 if verdict == "PASS" and stable else (2 if not stable else 1)


if __name__ == "__main__":
    raise SystemExit(main())
