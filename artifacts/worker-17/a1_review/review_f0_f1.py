#!/usr/bin/env python3
"""Independent A1 review checks for F0 and F1 (reviewer: deepseek-flash-17).

This script is review tooling, not a gate. It produces evidence for
reviews/F0-F1-review-17.json:

  * F0 acceptance criteria from the lead's assignment (comms/inbox/
    astra-lead-formulation.jsonl, event asg-2026-09-11-F0-astra-lead-formulation-00);
  * class-leakage / conclusion-inflation scans with prohibition-context exemptions;
  * cross-candidate conflict detection (two divergent F0 taxonomy files);
  * map<->artifact sha256 binding check;
  * F1 content checks mapped from the assignment acceptance text, since F1's slot
    names differ from this reviewer's gate vocabulary;
  * a measured false-positive report of class_binding_gate.py on the real F1 file.

Run: python3 review_f0_f1.py
Writes: review_findings.json (same directory).
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
F0_PATH = ROOT / "research_map" / "formulation_taxonomy.yaml"
F0R_PATH = ROOT / "artifacts" / "formulation" / "formulation_taxonomy.yaml"
F1_PATH = ROOT / "schemas" / "af_wcc_vacuum.yaml"
MAP_PATH = ROOT / "research_map" / "research_map.json"
OUT = HERE / "review_findings.json"

FROZEN = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]

# Merge patterns: wider than the taxonomy's own G3 (which misses C^{0}/C^{2} braces).
MERGE = re.compile(
    r"C\s*\^?\s*\{?\s*0\s*\}?\s*(?:or|and|/|\+)\s*C\s*\^?\s*\{?\s*2\s*\}?"
    r"|C\s*\^?\s*\{?\s*2\s*\}?\s*(?:or|and|/|\+)\s*C\s*\^?\s*\{?\s*0\s*\}?",
    re.I,
)
NEG = re.compile(r"never|not\b|no\b|forbid|avoid|separate|split|distinct|reject|leak|ban|must not", re.I)
INEXT = re.compile(r"inextendib", re.I)
VISIBLE = re.compile(r"visible|predictab", re.I)
C_TOKEN = re.compile(r"\bC\s*\^?\s*[02]\b")

checks = []


def record(cid, status, detail, evidence=None, severity=None):
    entry = {"check": cid, "status": status, "detail": detail}
    if evidence:
        entry["evidence"] = evidence
    if severity:
        entry["severity"] = severity
    checks.append(entry)
    return entry


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path):
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def leaves(obj, path=()):
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield from leaves(value, path + (str(key),))
    elif isinstance(obj, (list, tuple)):
        for index, value in enumerate(obj):
            yield from leaves(value, path + (str(index),))
    else:
        yield path, obj


def merge_scan(doc, label):
    asserted, exempt = [], []
    for path, value in leaves(doc):
        if not isinstance(value, str):
            continue
        root = path[0] if path else ""
        in_prohibition_block = root == "guards" or path[:2] == ("transfer_rules", "forbidden")
        for match in MERGE.finditer(value):
            ctx = value[max(0, match.start() - 140): match.start()]
            target = exempt if (in_prohibition_block or NEG.search(ctx)) else asserted
            target.append(f"{'.'.join(path)}: {value[max(0, match.start()-50):match.end()+30]!r}")
    return asserted, exempt


def main():
    f0 = load(F0_PATH)
    f0r = load(F0R_PATH)
    f1 = load(F1_PATH)
    mapping = json.loads(MAP_PATH.read_text())
    f0_sha, f0r_sha, f1_sha = sha256(F0_PATH), sha256(F0R_PATH), sha256(F1_PATH)

    # ---------------- F0 acceptance criteria ----------------
    record("f0.exists_parses_sha", "pass", "F0 declared artifact exists and parses as a mapping",
           f"research_map/formulation_taxonomy.yaml#{f0_sha[:12]} ({F0_PATH.stat().st_size} bytes)")
    record("f0.accept.class_ids_exact",
           "pass" if sorted(f0.get("class_ids", [])) == sorted(FROZEN) else "fail",
           f"class_ids == frozen four: {f0.get('class_ids')}")
    keys = sorted(f0.get("classes", {}).keys())
    record("f0.accept.classes_keys_exact",
           "pass" if keys == sorted(FROZEN) else "fail", f"classes keys: {keys}")

    per_class = {}
    for cid in FROZEN:
        c = f0.get("classes", {}).get(cid, {})
        tc = c.get("test_cases", {})
        ok = (
            bool(c.get("hypotheses"))
            and bool(c.get("exclusions"))
            and bool(c.get("conclusion", {}).get("type"))
            and bool(tc.get("positive"))
            and any(k.startswith("negative") for k in tc)
        )
        per_class[cid] = {
            "hypotheses": len(c.get("hypotheses", [])),
            "exclusions": len(c.get("exclusions", [])),
            "conclusion_type": c.get("conclusion", {}).get("type"),
            "positive_case": bool(tc.get("positive")),
            "negative_cases": sorted(k for k in tc if k.startswith("negative")),
            "ok": ok,
        }
    record("f0.accept.per_class_complete",
           "pass" if all(v["ok"] for v in per_class.values()) else "fail",
           "each class has hypotheses + exclusions + conclusion_type + positive + negative test case",
           json.dumps(per_class, sort_keys=True))
    prov = f0.get("provenance", {})
    record("f0.accept.provenance_reconstructed",
           "pass" if "reconstruct" in str(prov.get("status", "")) and not f0.get("claims_theorem_status") else "fail",
           f"provenance.status={prov.get('status')!r}; claims_theorem_status={f0.get('claims_theorem_status')!r}")

    # vocabulary conformance of axes
    vocab = f0.get("field_vocabulary", {})
    bad_axes = []
    for cid in FROZEN:
        axes = f0["classes"][cid].get("axes", {})
        for axis, value in axes.items():
            allowed = vocab.get(axis, {}).get("allowed")
            if allowed is not None and value not in allowed:
                bad_axes.append(f"{cid}.{axis}={value!r} not in {allowed}")
        fam = axes.get("family")
        if fam == "WCC" and axes.get("regularity_token") is not None:
            bad_axes.append(f"{cid}: WCC with regularity_token {axes.get('regularity_token')!r}")
        if fam == "SCC" and axes.get("regularity_token") not in ("C0", "C2"):
            bad_axes.append(f"{cid}: SCC without single C0/C2 token")
    record("f0.axes_vocab_conform", "pass" if not bad_axes else "fail",
           "axis values conform to field_vocabulary and the G2 regularity rule", json.dumps(bad_axes))

    # disjointness: all 6 pairs present, each differs on a declared decisive axis
    pairs = {}
    for row in f0.get("disjointness", []):
        p = tuple(row["pair"])
        pairs[tuple(sorted(p))] = row
    missing, weak = [], []
    for i in range(len(FROZEN)):
        for j in range(i + 1, len(FROZEN)):
            key = tuple(sorted((FROZEN[i], FROZEN[j])))
            if key not in pairs:
                missing.append(list(key)); continue
            row = pairs[key]
            differs = False
            for axis in row.get("decisive_axes", []):
                a = f0["classes"][key[0]].get("axes", {}).get(axis)
                b = f0["classes"][key[1]].get("axes", {}).get(axis)
                if a != b:
                    differs = True
            if not differs:
                weak.append(list(key))
    record("f0.disjointness_all_pairs",
           "pass" if not missing and not weak else "fail",
           f"6 unordered pairs present and each separated on a declared decisive axis; missing={missing} weak={weak}",
           f"disjointness entries: {len(pairs)}/6")

    # merge scan on both candidates
    f0_asserted, f0_exempt = merge_scan(f0, "F0")
    f0r_asserted, f0r_exempt = merge_scan(f0r, "F0-R")
    record("f0.merge_scan_no_asserted_merge",
           "pass" if not f0_asserted else "fail",
           f"asserted C0/C2 merges in F0 body: {len(f0_asserted)}; prohibition-context matches exempted: {len(f0_exempt)}",
           json.dumps(f0_asserted[:5]))
    def bare_label(match_str):
        value = match_str.split(": ", 1)[-1].strip().strip("'\"")
        return MERGE.fullmatch(value.strip()) is not None

    f0r_genuine = [m for m in f0r_asserted if bare_label(m)]
    record("f0r.merge_scan_no_asserted_merge",
           "fail" if f0r_genuine else "pass",
           f"F0-R merge-pattern matches: {len(f0r_asserted)} outside prohibition blocks "
           f"(+{len(f0r_exempt)} prohibition-context). Matches inside exclusion/contrast sentences are "
           "prohibitions; matches on a whole stripped value are genuine banned composite labels.",
           json.dumps({"matches": f0r_asserted, "genuine_banned_labels": f0r_genuine}, indent=2))

    # conclusion-family separation inside F0 (ignore 'future-inextendible geodesic', standard WCC wording)
    leaks = []
    for cid in FROZEN:
        c = f0["classes"][cid]
        text = str(c.get("conclusion", {}).get("text", ""))
        fam = c["axes"]["family"]
        if fam == "WCC":
            for match in INEXT.finditer(text):
                window = text[max(0, match.start() - 30): match.end() + 30]
                if "geodesic" not in window:
                    leaks.append(f"{cid}: WCC conclusion asserts spacetime inextendibility: {window!r}")
        if fam == "SCC" and VISIBLE.search(text.split("forbidden_inflation")[0]):
            leaks.append(f"{cid}: SCC conclusion asserts visibility/predictability")
        if c.get("conclusion", {}).get("type") != c["axes"].get("conclusion_type"):
            leaks.append(f"{cid}: conclusion.type != axes.conclusion_type")
    record("f0.conclusion_family_separation", "pass" if not leaks else "fail",
           "no WCC spacetime-inextendibility or SCC visibility conclusion inflation "
           "(matches followed by 'geodesic' are WCC standard wording, not leakage)",
           json.dumps(leaks))

    # cross-candidate duplication + vocabulary conflict
    f0r_exists = F0R_PATH.exists()
    record("f0.candidate_duplication",
           "fail" if not f0r_exists or f0_sha != f0r_sha else "pass",
           "TWO divergent artifacts both claim node F0; F1/F2 reviewers cannot know which class semantics bind"
           if f0r_exists and f0_sha != f0r_sha else "single F0 candidate on disk",
           json.dumps({
               "candidate_A": {"path": "research_map/formulation_taxonomy.yaml", "sha256": f0_sha,
                               "lines": len(F0_PATH.read_text().splitlines())},
               "candidate_B": ({"path": "artifacts/formulation/formulation_taxonomy.yaml", "sha256": f0r_sha,
                                "lines": len(F0R_PATH.read_text().splitlines())} if f0r_exists else None),
               "identical": f0r_exists and f0_sha == f0r_sha,
           }, indent=2))
    f0_ctypes = sorted({f0["classes"][c]["axes"]["conclusion_type"] for c in FROZEN})
    f0r_ctypes = sorted({v.get("conclusion_type") for v in f0r.get("class_contracts", {}).values()})
    f0_gen = sorted({f0["classes"][c]["axes"]["genericity_kind"] for c in FROZEN})
    f0r_gen = sorted(set(f0r.get("axis_registry", {}).get("genericity_axis", {}).get("frozen", {}).values()))
    record("f0.candidate_vocabulary_conflict",
           "pass" if f0_ctypes == f0r_ctypes else "fail",
           "conclusion_type / genericity token vocabularies differ between the two F0 candidates",
           json.dumps({"F0_conclusion_types": f0_ctypes, "F0R_conclusion_types": f0r_ctypes,
                       "F0_genericity": f0_gen, "F0R_genericity": f0r_gen}, indent=2))

    # WCC black-hole-region clause: the concrete cross-candidate contradiction
    wcc_text = f0["classes"]["AF-WCC-VAC-GEN"]["conclusion"]["text"]
    f0r_wcc = f0r["class_contracts"]["AF-WCC-VAC-GEN"]
    record("f0.wcc_conclusion_predicate_conflict",
           "fail",
           "AF-WCC-VAC-GEN conclusion differs across the two F0 candidates: candidate A asserts the "
           "black-hole region has non-empty interior as 'equivalent' to WCC; candidate B explicitly "
           "lists black-hole formation as a non-goal and drops the clause",
           json.dumps({
               "F0_clause_present": "non-empty interior" in wcc_text,
               "F0R_non_goals": f0r_wcc.get("non_goals"),
               "F0R_conclusion_predicate": f0r_wcc.get("conclusion_predicate"),
           }, indent=2))

    # map <-> artifact sha256 binding
    f0_node = None
    for group in mapping.get("groups", []):
        for node in group.get("nodes", []):
            if node["id"] == "F0":
                f0_node = node
    recorded = (f0_node or {}).get("artifact_sha256")
    record("f0.map_sha256_binding",
           "pass" if recorded == f0_sha else "fail",
           "map F0.artifact_sha256 must equal sha256 of the declared artifact path",
           json.dumps({"declared_path": (f0_node or {}).get("artifact"),
                       "recorded_sha256": recorded, "actual_sha256": f0_sha,
                       "map_updated_at": mapping.get("updated_at")}, indent=2))

    # independence of the machine validation artifact
    tax_val = ROOT / "artifacts" / "worker-01" / "taxonomy_validation.json"
    val = json.loads(tax_val.read_text()) if tax_val.exists() else {}
    record("f0.machine_validation_independence",
           "fail",
           "the only machine acceptance run for F0 was produced by worker-01, the same worker that "
           "authored F0 (authored_by: deepseek-flash-01); this is self-validation, not an independent check",
           json.dumps({"validation_artifact": "artifacts/worker-01/taxonomy_validation.json",
                       "validated_file": val.get("file"), "verdict": val.get("verdict"),
                       "checks_passed": val.get("checks_passed"), "f0_authored_by": f0.get("authored_by")}, indent=2))

    # hand findings on F0 (line-referenced)
    f0_hand = [
        {"severity": "major", "line": 173,
         "finding": "AF-SCC-C2 exclusions call a C0-inextendibility claim a 'higher regularity token'; "
                    "C0 is LOWER regularity and a STRONGER conclusion. The taxonomy itself says so at "
                    "field_vocabulary.regularity_token.meaning_C0. Wording can mis-file a C0 result.",
         "fix": "replace with 'a stronger conclusion at lower regularity (C0), which belongs to AF-SCC-C0-VAC-GEN'"},
        {"severity": "major", "line": 103,
         "finding": "AF-WCC-VAC-GEN conclusion asserts geodesic completeness in J-(I+) is 'equivalent' to "
                    "the black-hole-region-interior condition. No proof or source is attached, and F0-R "
                    "contradicts it by listing black-hole formation as a non-goal.",
         "fix": "delete 'equivalently' and keep one predicate, or attach a proof/source and reconcile with F0-R"},
        {"severity": "major", "lines": "408-409",
         "finding": "guard G3 regex does not cover braced/superscript spellings such as 'C^{0} or C^{2}'; "
                    "a rephrased merge passes downstream linters built from it.",
         "fix": "normalize regularity tokens (strip ^ and braces) before matching, and add a normalization test"},
        {"severity": "minor", "line": 172,
         "finding": "exclusion parenthetical 'electrovacuum, where exact charged black holes provide smooth "
                    "extensions' is an unmarked literature claim inside a definitional list; the artifact "
                    "contract says literature claims stay unresolved.",
         "fix": "move to known_obstruction with literature_status unresolved_pending_L0_L1"},
        {"severity": "minor", "lines": "77,146,213",
         "finding": "axes.genericity_kind is fixed to baire_residual for the three vacuum classes while "
                    "genericity_value_status is provisional_owned_by_F1/F2 and Q1 lists the notion as open; "
                    "machine checks would treat the provisional value as frozen.",
         "fix": "set genericity_kind to 'unresolved' until F1/F2 freeze it, or mark the axis value provisional in a machine-readable way"},
        {"severity": "minor", "lines": "7, 443",
         "finding": "content timestamps run ahead of filesystem mtime (created_at 23:25 vs mtime 23:22:13); "
                    "do not use content timestamps for ordering evidence, cite sha256",
         "fix": "record both authored_at (declared) and written_at (observed) or drop content timestamps"},
    ]
    record("f0.hand_findings", "fail", f"{len(f0_hand)} findings from independent reading", json.dumps(f0_hand, indent=2))

    # ---------------- F1 checks ----------------
    record("f1.exists_parses_sha", "pass", "F1 declared artifact exists and parses as a mapping",
           f"schemas/af_wcc_vacuum.yaml#{f1_sha[:12]} ({F1_PATH.stat().st_size} bytes)")

    sys.path.insert(0, str(ROOT / "artifacts" / "worker-17" / "class_binding_gate"))
    import class_binding_gate as gate  # noqa: E402
    raw = gate.check(f1, source="schemas/af_wcc_vacuum.yaml")
    from collections import Counter
    counts = Counter(v["code"] for v in raw)
    shape_codes = {"R_REQUIRED", "R_VISIBILITY", "R_EMPTY"}
    shape = sum(counts[c] for c in shape_codes)
    semantic = {c: n for c, n in counts.items() if c not in shape_codes}
    record("f1.gate_raw_measurement", "fail" if raw else "pass",
           "reviewer gate applied unchanged to the real F1 artifact: results are dominated by slot-name "
           "vocabulary mismatch, so raw violations are NOT treated as F1 defects",
           json.dumps({"total_violations": len(raw), "shape_vocabulary_violations": shape,
                       "other_violations": semantic,
                       "false_positive_classes": [
                           "slot names differ: quantifiers.forall/exists vs for_all/there_exists; i_plus outside topology; data_class.weighted_norm vs space/weights; genericity.kind vs measure_or_topology; evidence_refs vs source_refs",
                           "class_separation.frozen_class_ids is a declaration list, not leakage",
                           "evidence_refs.excluded_on_scope_grounds is citation text, not leakage",
                           "C^2 development regularity is legitimate for a WCC schema; the blanket C0/C2 ban is wrong outside extension-conclusion context",
                       ]}, indent=2))

    q = f1.get("quantifiers", {})
    record("f1.content_exact_quantifiers",
           "pass" if all(q.get(k) for k in ("forall", "exists", "order", "logical_form")) else "fail",
           "explicit universal + existential quantifiers, ordered form, and negation over singular boundary",
           f"quantifier_order_status={q.get('quantifier_order_status')}")
    topo = f1.get("topology", {})
    i_plus_present = bool(f1.get("i_plus"))
    i_minus = bool(re.search(r"\bI\s*-|past null infinity|scri\s*-", F1_PATH.read_text()))
    i0 = bool(re.search(r"\bi0\b|spatial infinity", F1_PATH.read_text()))
    record("f1.accept.topology_includes_Im_i0",
           "fail" if not (i_minus and i0) else "pass",
           "lead acceptance asks topology to declare globally hyperbolic AF 3+1 with I+/I-/i0; "
           f"present: globally_hyperbolic={'globally hyperbolic' in str(topo)}, I+={i_plus_present}, I-={i_minus}, i0={i0}",
           "F1 topology lines 93-99; i_plus section lines 124-140")
    dc = f1.get("data_class", {})
    s_named = bool(re.search(r"5/2|s\s*>", str(dc)))
    delta_named = bool(re.search(r"delta", str(dc)))
    record("f1.accept.weighted_data_class",
           "pass" if s_named and delta_named else "fail",
           f"weighted data class names s ({s_named}) and delta ({delta_named}); revision 2 proposes "
           f"(s, delta) = (4, 1/2+eps) with status {dc.get('weighted_spaces_proposal_status')!r}",
           json.dumps({"regularity": dc.get("regularity"), "weighted_norm": dc.get("weighted_norm"),
                       "proposal_status": dc.get("weighted_spaces_proposal_status")}, indent=2))
    gen = f1.get("genericity", {})
    gen_status = gen.get("genericity_status")
    record("f1.accept.genericity_open_dense_named_topology",
           "pass" if gen.get("kind") and gen.get("topology_name") else "fail",
           "genericity names an open-dense/Baire notion AND a topology (revision 2); it is a proposal, "
           f"status={gen_status!r}, so G-FORM cannot pass until A1 accepts",
           json.dumps({"kind": gen.get("kind"), "topology_name": gen.get("topology_name"),
                       "status": gen_status, "proposal_status": gen.get("kind_proposal_status")}, indent=2))
    vis = f1.get("i_plus", {}).get("visibility", {})
    record("f1.visibility_definition_vs_negation",
           "fail",
           "definition asserts an 'iff ... equivalently' between p in J^-(I+) and a curve whose past "
           "accumulates on p; formal_negation uses only the J^- membership. curve_class and set_vs_point "
           "are flagged unresolved, but this definition-level equivalence is still asserted, not flagged.",
           json.dumps({"definition": vis.get("definition"), "formal_negation": vis.get("formal_negation"),
                       "visibility_status": vis.get("visibility_status")}, indent=2))
    concl = f1.get("conclusion", {})
    conc_text = str(concl.get("statement", ""))
    family_ok = concl.get("family") == "weak_cosmic_censorship"
    lit = concl.get("type")
    record("f1.accept.conclusion_type_literal",
           "fail" if lit != "weak_cosmic_censorship" else "pass",
           "lead acceptance says conclusion_type=weak_cosmic_censorship; the draft sets conclusion.type="
           f"{lit!r} (conjecture is open) and carries the WCC family separately. Defensible semantics, "
           "literal acceptance mismatch, and a third vocabulary alongside F0 and A0.",
           json.dumps({"conclusion.type": lit, "asserted_if_proved": concl.get("asserted_conclusion_type_if_proved"),
                       "family": concl.get("family"),
                       "A0_rubric_conclusion_primary": "future_asymptotic_predictability",
                       "F0_conclusion_type": "weak_cosmic_censorship"}, indent=2))
    record("f1.conclusion_equivalence_asserted_but_unverified",
           "fail" if "equivalently" in conc_text else "pass",
           "conclusion.statement asserts 'equivalently, every future-directed causal curve that reaches I+ "
           "is complete to the past' (causal-CURVE reading), while i_plus.visibility.curve_class adopts the "
           "geodesic reading as the revision-2 proposal and the statement's equivalence to the F0 form is "
           "recorded as unverified",
           json.dumps({"visibility_curve_class": vis.get("curve_class"),
                       "f0_equivalent_form_equivalence": "unverified per conclusion.f0_equivalent_form"}, indent=2))
    record("f1.statement_vs_curve_class_consistency",
           "fail",
           "internal mismatch in revision 2: conclusion.statement quantifies over causal CURVES, while "
           "i_plus.visibility.curve_class proposes geodesic completeness 'aligned with the F0 conclusion'. "
           "A reader cannot tell which predicate G-FORM is freezing.",
           json.dumps({"statement_excerpt": conc_text[-140:], "curve_class": vis.get("curve_class"),
                       "divergence_from_f0": vis.get("divergence_from_f0")}, indent=2))
    scc_hits = []
    for match in re.finditer(r"inextendib|C\s*\^?\s*[02]\b", json.dumps({"q": q, "c": concl})):
        window = json.dumps({"q": q, "c": concl})[max(0, match.start() - 30): match.end() + 30]
        if "geodesic" in window and match.group(0).lower().startswith("inextendib"):
            continue  # standard WCC wording: future-inextendible causal geodesic
        scc_hits.append(window)
    record("f1.no_scc_content_in_conclusion_or_quantifiers",
           "pass" if not scc_hits else "fail",
           "conclusion and quantifier fields contain no SCC extension-regularity token "
           "(matches on 'future-inextendible ... geodesic' are standard WCC wording and are exempted); "
           "class_separation.frozen_class_ids lists the other class ids by design and is not leakage",
           json.dumps(scc_hits[:3]))
    record("f1.linter_driven_wording",
           "fail",
           "conclusion.f0_equivalent_form records that the F0-canonical wording was kept OUT of "
           "conclusion.statement because the candidate linter flags the regularity word as an SCC token "
           "(DIV-2 / G-FORM-TOKEN). A tool false positive is now shaping the formulation text; this "
           "reviewer's own gate made the same class of error on this file.",
           json.dumps({"f0_equivalent_form": concl.get("f0_equivalent_form"),
                       "recommended_fix": "fix the linter (context-aware token rule), then restore the F0 "
                                          "wording or file the equivalence as a lemma; do not let token "
                                          "matching choose the predicate"}, indent=2))
    record("f1.accept.non_goals",
           "pass" if concl.get("forbidden_imports") else "fail",
           "explicit non-goals / forbidden imports present",
           f"{len(concl.get('forbidden_imports', []))} entries")
    fals = f1.get("falsifier", {})
    record("f1.falsifier_present",
           "pass" if fals.get("class_level") and fals.get("schema_level") else "fail",
           "class-level falsifier is an open set of visible-singularity data in D_gen; schema-level "
           "falsifier is two-reader non-equivalence; nearest witness membership in D_gen not established",
           json.dumps({"class_level": fals.get("class_level"), "nearest_known_witness": fals.get("nearest_known_witness")}, indent=2))
    dep0 = f1.get("dependencies", [{}])[0]
    dep_status = dep0.get("status_at_revision_2") or dep0.get("status_at_draft_time")
    record("f1.f0_dependency_binding",
           "pass" if dep0.get("sha256") == f0_sha else "fail",
           "revision 2 binds F1 to the F0 artifact by sha256 and marks it draft_unverified; any F0 change "
           "invalidates the binding. Residual: the competing F0-R artifact is not referenced.",
           json.dumps({"status": dep_status, "bound_sha256": dep0.get("sha256"),
                       "actual_F0_sha256": f0_sha, "consequence": dep0.get("consequence")}, indent=2))
    notes = ROOT / "artifacts" / "flash-03" / "F1_notes.md"
    record("f1.self_check_evidence_exists",
           "pass" if notes.exists() else "fail",
           "self-run linter evidence referenced by the draft exists on disk (self-check, not independent)",
           f"artifacts/flash-03/F1_notes.md#{sha256(notes)[:12]}" if notes.exists() else None)
    record("f1.citations_deferred_to_L1",
           "pass",
           "7 primary sources carry verified_via locators and 3 refs are excluded on scope grounds; "
           "primary verification is L1's gate, not performed here",
           f"{len(f1.get('evidence_refs', {}).get('primary_sources_verified_2026_09_11', []))} sources listed")

    f1_hand = [
        {"severity": "major", "lines": "conclusion.statement / i_plus.visibility.curve_class",
         "finding": "statement uses causal curves while curve_class proposes geodesic completeness; both "
                    "cannot be the frozen predicate. 'equivalently' still asserts an unverified equivalence.",
         "fix": "pick one curve class in statement AND curve_class, and drop 'equivalently' or file it as a lemma"},
        {"severity": "major", "lines": "conclusion.f0_equivalent_form",
         "finding": "the F0-canonical WCC wording was removed from the statement because a linter flags "
                    "'inextendible' as an SCC token; tool vocabulary is now driving the physics statement.",
         "fix": "fix the linter's context rule and restore the F0 wording, or record the divergence as a "
                "class-level lemma with the linter finding attached"},
        {"severity": "major", "lines": "topology 93-99",
         "finding": "I- and i0 are absent though the lead acceptance names them; WCC needs I+, but the "
                    "acceptance line is unmet as written.",
         "fix": "declare I- and i0, or record the acceptance-line deviation explicitly"},
        {"severity": "minor", "lines": "conclusion.type",
         "finding": "conclusion.type=open_problem is semantically right (conjecture open) but mismatches the "
                    "lead's literal acceptance and the F0/A0 conclusion vocabularies.",
         "fix": "freeze one conclusion vocabulary across F0, F1, A0; record truth status separately"},
        {"severity": "minor", "lines": "genericity / data_class (revision 2)",
         "finding": "genericity topology and (s, delta)=(4, 1/2+eps) are proposals with status "
                    "proposed_pending_A1; the file is now reviewable but not freezable.",
         "fix": "A1 verdicts on kind_proposal_status and weighted_spaces_proposal_status"},
    ]
    record("f1.hand_findings", "fail", f"{len(f1_hand)} findings from independent reading", json.dumps(f1_hand, indent=2))

    report = {
        "reviewer": "deepseek-flash-17",
        "reviewed_at": "2026-09-11T23:2x+08:00",
        "targets": {
            "F0": {"path": "research_map/formulation_taxonomy.yaml", "sha256": f0_sha,
                   "revision": f0.get("revision"), "status": f0.get("status")},
            "F0_competing": {"path": "artifacts/formulation/formulation_taxonomy.yaml", "sha256": f0r_sha,
                             "revision": f0r.get("revision"), "status": "remediation_unreviewed"},
            "F1": {"path": "schemas/af_wcc_vacuum.yaml", "sha256": f1_sha,
                   "revision": f1.get("revision"), "validation_status": f1.get("validation_status"),
                   "superseded_revision_reviewed": "revision 1, sha256 eb0d69fab32be640d40032fc8258a0760d068399d7ca0039a2676a1be86dbdc7"},
        },
        "check_counts": {
            "total": len(checks),
            "pass": sum(1 for c in checks if c["status"] == "pass"),
            "fail": sum(1 for c in checks if c["status"] == "fail"),
        },
        "checks": checks,
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"F0 sha256 {f0_sha}")
    print(f"F0-R sha256 {f0r_sha}")
    print(f"F1 sha256 {f1_sha}")
    for c in checks:
        print(f"  [{c['status']:4}] {c['check']}: {c['detail'][:120]}")
    print(f"\n{report['check_counts']['pass']} pass / {report['check_counts']['fail']} fail "
          f"of {report['check_counts']['total']} checks -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
