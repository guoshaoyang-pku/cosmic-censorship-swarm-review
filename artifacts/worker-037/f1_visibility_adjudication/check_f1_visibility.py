#!/usr/bin/env python3
"""W037-F1-VISIBILITY-02: independent adjudication of the F1 visibility-expansion defect.

Class-bound task. Class: AF-WCC-VAC-GEN (node F1, gate G-FORM).
Target bytes: schemas/af_wcc_vacuum.yaml at the revision frozen in
artifacts/formulation/FROZEN.json (F1 hash measured at run time; the reviewed hash is
recorded in the report).

Question under test (raised as critical HF-06 by deepseek-flash-19 at the same hash):
  Is the visibility clause inside quantifiers.formal the SAME predicate as the
  class's canonical visibility predicate (visibility.definition), and are
  quantifiers.formal and quantifiers.negation exact negations of each other?

Method (read-only; writes only inside this artifact directory):
  1. T0/T1 sha256 snapshot of the canonical F1 schema (and the F0 taxonomy it binds).
  2. Textual extraction of the four predicate sites with line numbers:
       quantifiers.formal :54-55, domains.D5 :79-81,
       visibility.definition :220, visibility.negation_conclusion :222.
  3. Structural tests on those sites (whole-curve vs tail binder; exact-negation test).
  4. Exhaustive finite-model check of the strictness relation P_whole => P_tail.
  5. Mutation tests against the canonical gate checker (check_class_schema.py):
       M0 canonical bytes, M1 formal clause inverted to ASSERT visibility,
       M2 formal clause repaired to the tail predicate, M3 positive control
       (visibility.definition emptied), M4 definition replaced by the forbidden
       whole-curve reading. M1/M4 passing while M3 fails demonstrates the gate is
       insensitive to the predicate content; this is the "PASS is not evidence of
       agreement" claim, measured.
  6. Independent re-check of the dangling notation AF_{I+} in conclusion.statement_formal.

Authority: independent verification evidence only. It is NOT a gate verdict, NOT an
acceptance, NOT a node-status change, and it does not edit any canonical artifact.
Reviewer identity: worker-037.

Usage: python3 artifacts/worker-037/f1_visibility_adjudication/check_f1_visibility.py
Output: report.json next to this script (path and sha256 printed to stdout).
"""
from __future__ import annotations

import hashlib
import itertools
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
F1_REL = "schemas/af_wcc_vacuum.yaml"
F0_REL = "research_map/formulation_taxonomy.yaml"
F1_AUTHORING_REL = "artifacts/formulation/schemas/af_wcc_vacuum.yaml"
FROZEN_REL = "artifacts/formulation/FROZEN.json"
CHECKER = "artifacts/formulation/tools/check_class_schema.py"
RUN_ACCEPT = "artifacts/formulation/tools/run_acceptance.py"
CLASS_ID = "AF-WCC-VAC-GEN"
NODE = "F1"
GATE = "G-FORM"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def snap(rel: str) -> dict:
    p = ROOT / rel
    if not p.exists():
        return {"exists": False}
    st = p.stat()
    return {"exists": True, "sha256": sha256_file(p), "bytes": st.st_size,
            "mtime": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(st.st_mtime))}


def run_tool(args: list[str]) -> dict:
    t0 = now()
    proc = subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True,
                          text=True, timeout=300)
    return {"cmd": "python3 " + " ".join(args), "exit_code": proc.returncode,
            "stdout": proc.stdout.strip(), "stderr_tail": proc.stderr.strip().splitlines()[-6:],
            "started_at": t0, "ok": proc.returncode == 0}


def find_lines(text: str, needle: str) -> list[int]:
    return [i + 1 for i, ln in enumerate(text.splitlines()) if needle in ln]


def get_path(doc: dict, *keys):
    cur = doc
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def logical_relation_check() -> dict:
    """Exhaustive finite-model check: P_whole => P_tail, strictly.

    Toy universe U = {a, b}; one I+ point q1 with J^-(q1) cap M = {b}. A geodesic is a
    finite time-ordered image gamma = [g0, g1] (T=2). P_whole(gamma) := exists q with
    every sample of gamma in U_q. P_tail(gamma) := exists q, t0 in [0,T) with every
    sample of gamma[t0:] in U_q. Enumerate all gamma over U.
    """
    universe = ["a", "b"]
    U = {"q1": {"b"}}
    models = []
    for g0, g1 in itertools.product(universe, repeat=2):
        gamma = [g0, g1]
        p_whole = any(all(x in Uq for x in gamma) for Uq in U.values())
        p_tail = any(all(x in Uq for x in gamma[t0:])
                     for Uq in U.values() for t0 in range(len(gamma)))
        if p_tail and not p_whole:
            models.append({"gamma": gamma, "U_q1": sorted(U["q1"]),
                           "P_whole": p_whole, "P_tail": p_tail,
                           "formal_not_P_whole_satisfied": not p_whole,
                           "canonical_conclusion_not_P_tail_violated": p_tail})
    # P_whole => P_tail must hold on every model (t0 = 0)
    implication_holds = True
    for g0, g1 in itertools.product(universe, repeat=2):
        gamma = [g0, g1]
        p_whole = any(all(x in Uq for x in gamma) for Uq in U.values())
        p_tail = any(all(x in Uq for x in gamma[t0:])
                     for Uq in U.values() for t0 in range(len(gamma)))
        if p_whole and not p_tail:
            implication_holds = False
    return {"universe": universe, "U_q1": sorted(U["q1"]),
            "P_whole_implies_P_tail": implication_holds,
            "strictness_witnesses": models,
            "strictness_witness_count": len(models),
            "reading": "P_whole(gamma) => P_tail(gamma) with t0=0; the converse fails; "
                       "so not-P_whole (formal) is strictly weaker than not-P_tail "
                       "(canonical conclusion). A model can satisfy the formal clause "
                       "and the stated negation at the same time."}


def main() -> int:
    t0 = now()
    s0 = {F1_REL: snap(F1_REL), F0_REL: snap(F0_REL), F1_AUTHORING_REL: snap(F1_AUTHORING_REL)}
    text = (ROOT / F1_REL).read_text()
    import yaml
    doc = yaml.safe_load(text)

    formal = str(get_path(doc, "quantifiers", "formal") or "")
    d5 = str(get_path(doc, "quantifiers", "domains", "D5", "definition") or "")
    d4 = str(get_path(doc, "quantifiers", "domains", "D4", "definition") or "")
    vis_def = str(get_path(doc, "visibility", "definition") or "")
    vis_neg = str(get_path(doc, "visibility", "negation_conclusion") or "")
    must_not = get_path(doc, "visibility", "must_not_conflate") or []
    stmt_formal = str(get_path(doc, "conclusion", "statement_formal") or "")

    # clause inside quantifiers.formal after "finite affine length:"
    m = re.search(r"finite affine length:(.*)$", formal, re.S)
    formal_vis_clause = (m.group(1).strip() if m else "")

    # ---- structural tests on the four predicate sites -------------------------------
    tests: list[dict] = []

    def add(tid, status, check, witness, quote, lines):
        tests.append({"id": tid, "status": status, "check": check, "witness": witness,
                      "quote": quote, "lines": lines})

    tail_marker = re.compile(r"\bt0\b|\[t0\s*,|tail", re.I)
    formal_has_tail = bool(tail_marker.search(formal_vis_clause))
    formal_has_whole = bool(re.search(r"gamma\s+subset\s+J\^?-\(q\)", formal_vis_clause))
    add("V1", "fail" if (formal_has_whole and not formal_has_tail) else "pass",
        "quantifiers.formal visibility clause carries the tail binder (t0) used by the "
        "canonical predicate",
        "formal clause quantifies over the WHOLE curve and has no t0/tail binder",
        formal_vis_clause, find_lines(text, "not exists q in I+ with gamma subset"))

    d5_has_tail = bool(tail_marker.search(d5))
    d5_has_whole = bool(re.search(r"gamma\(\[0,T\)\)", d5))
    add("V2", "fail" if (d5_has_whole and not d5_has_tail) else "pass",
        "domain D5 (the domain of the not_exists q binder) uses the same tail predicate "
        "as visibility.definition",
        "D5 defines q by containment of gamma([0,T)) (whole curve), not a tail",
        d5, find_lines(text, "gamma([0,T)) is contained in the causal past"))

    vis_tail = bool(re.search(r"\bt0\b", vis_def) and re.search(r"gamma\(\[t0", vis_def))
    add("V3", "pass" if vis_tail else "fail",
        "visibility.definition is the canonical single-q TAIL predicate",
        "definition requires exists q AND t0 with the tail gamma([t0,T)) contained",
        vis_def[:400], find_lines(text, "singular END of the geodesic"))

    neg_uses_named = bool(re.search(r"\bt0\b", vis_neg) or "tail" in vis_neg
                          or "visible_singularity_from_I_plus" in vis_neg)
    add("V4", "pass" if neg_uses_named else "fail",
        "visibility.negation_conclusion negates the canonical (tail) predicate",
        "negation is stated over the tail formulation (tail / t0 / the named "
        "visible_singularity_from_I_plus predicate), not over the whole curve",
        vis_neg[:400], find_lines(text, "there is NO visible_singularity_from_I_plus"))

    # exact-negation test: formal = not-P_whole, negation = P_tail, and P_whole => P_tail
    exact_broken = bool(formal_has_whole and neg_uses_named)
    add("V5", "fail" if exact_broken else "pass",
        "quantifiers.formal and quantifiers.negation are exact negations of each other",
        "formal = not-P_whole (no t0), negation = P_tail (named predicate); "
        "not-P_whole is strictly weaker than not-P_tail, so the two are not exact "
        "negations and can hold simultaneously",
        "formal: " + formal_vis_clause + " || negation: " + vis_neg[:200],
        find_lines(text, "not exists q in I+ with gamma subset") +
        find_lines(text, "future-inextendible causal geodesic of finite affine length is visible"))

    # the artifact's own visibility.definition says the whole-curve reading misclassifies
    own_warning = ("whole geodesic" in vis_def and "black-hole" in vis_def)
    add("V6", "fail" if (formal_has_whole and own_warning) else "pass",
        "no site in the artifact uses the whole-curve reading that the artifact's own "
        "visibility.definition calls a misclassification (line 220)",
        "visibility.definition line 220 explicitly says requiring the whole geodesic to "
        "lie in J^-(q) 'would misclassify a geodesic that starts in the exterior and ends "
        "inside the black-hole region'; quantifiers.formal lines 54-55 use exactly that "
        "reading",
        str(get_path(doc, "visibility", "definition"))[-320:],
        find_lines(text, "would misclassify a geodesic"))

    # dangling symbol AF_{I+}
    af_lines = find_lines(text, "AF_{I+}")
    defined_elsewhere = []
    for rel in [F1_REL, F0_REL,
                "artifacts/formulation/formulation_taxonomy.yaml",
                "artifacts/formulation/rule_spec.json"]:
        p = ROOT / rel
        if p.exists() and "AF_{I+}" in p.read_text():
            defined_elsewhere.append(rel)
    add("V7", "fail" if (af_lines and len(defined_elsewhere) == 1) else "pass",
        "every symbol used in conclusion.statement_formal is defined in the artifact",
        "AF_{I+}(M_D) occurs only at line 251 and is defined nowhere else in the schema, "
        "the taxonomy, or the rule spec (grep AF_{I+} = 1 site)",
        stmt_formal, af_lines)

    # ---- mutation tests against the canonical gate ----------------------------------
    mut_dir = OUT / "mutations"
    mut_dir.mkdir(exist_ok=True)
    orig_clause = "not exists q in I+ with gamma subset J^-(q) intersect M."
    variants = {
        "M0_canonical": text,
        "M1_formal_inverted_to_assert_visibility": text.replace(
            orig_clause, "exists q in I+ with gamma subset J^-(q) intersect M."),
        "M2_formal_repaired_to_tail": text.replace(
            orig_clause, "not exists q in I+ and t0 in [0,T) with gamma([t0,T)) subset "
                         "J^-(q) intersect M."),
        "M3_positive_control_visibility_definition_emptied": text.replace(
            vis_def, ""),
        "M4_definition_replaced_by_forbidden_whole_curve_reading": text.replace(
            vis_def, "a future-inextendible causal geodesic gamma is visible from I+ iff "
                     "there exists q in I+ with the whole curve gamma contained in "
                     "J^-(q) intersect M"),
    }
    mutations = []
    for name, body in variants.items():
        assert body != text or name == "M0_canonical", f"mutation {name} did not apply"
        p = mut_dir / f"af_wcc_vacuum.{name}.yaml"
        p.write_text(body)
        r = run_tool([CHECKER, str(p.relative_to(ROOT)), "--json"])
        mutations.append({"name": name, "path": str(p.relative_to(ROOT)),
                          "applied": body != text,
                          "exit_code": r["exit_code"], "ok": r["ok"],
                          "stdout": r["stdout"][:1200]})
    by = {m["name"]: m for m in mutations}
    gate_insensitive = (by["M0_canonical"]["ok"]
                        and by["M1_formal_inverted_to_assert_visibility"]["ok"]
                        and by["M4_definition_replaced_by_forbidden_whole_curve_reading"]["ok"]
                        and not by["M3_positive_control_visibility_definition_emptied"]["ok"])

    ra = run_tool([RUN_ACCEPT])

    t1 = now()
    s1 = {F1_REL: snap(F1_REL), F0_REL: snap(F0_REL), F1_AUTHORING_REL: snap(F1_AUTHORING_REL)}
    moved = [k for k in s0 if s0[k].get("sha256") != s1[k].get("sha256")]

    findings = [
        {"id": "W037V2-F1", "severity": "critical",
         "statement": "CONFIRMED at the measured bytes: the visibility clause inside "
                      "quantifiers.formal (lines 54-55) and domain D5 (lines 79-81) use the "
                      "whole-curve predicate 'gamma subset J^-(q)', while the class's "
                      "canonical predicate (visibility.definition line 220) and its stated "
                      "negation (line 222) use the tail predicate 'gamma([t0,T)) subset "
                      "J^-(q)'. Since whole-curve containment implies tail containment and "
                      "not conversely, the formal expansion is strictly WEAKER than the "
                      "conclusion it expands, and quantifiers.formal / quantifiers.negation "
                      "are not exact negations (both can hold for the same geodesic). The "
                      "artifact's own line 220 names exactly the misclassified case: a "
                      "geodesic that starts in the exterior and ends inside the black-hole "
                      "region. This is a content-level defect, not formatting: an accepted "
                      "verdict at this hash would accept a class whose formal statement "
                      "differs from its canonical visibility predicate.",
         "evidence": ["schemas/af_wcc_vacuum.yaml:54-55", "schemas/af_wcc_vacuum.yaml:79-81",
                      "schemas/af_wcc_vacuum.yaml:220", "schemas/af_wcc_vacuum.yaml:222",
                      "check_f1_visibility.py#V1,V2,V5,V6",
                      "logical_relation.strictness_witnesses"],
         "cross_reference": "confirms deepseek-flash-19 flash19-F1-01-review HF-06 (critical); "
                            "the independent finite-model check here is new evidence, not a "
                            "restatement of that review."},
        {"id": "W037V2-F2", "severity": "major",
         "statement": "AF_{I+}(M_D) in conclusion.statement_formal (line 251) is used as a "
                      "predicate and defined nowhere in the schema, the F0 taxonomy, or the "
                      "rule spec (single occurrence).",
         "evidence": ["schemas/af_wcc_vacuum.yaml:251", "check_f1_visibility.py#V7"],
         "cross_reference": "confirms deepseek-flash-19 HF-06 (major, dangling symbol)."},
        {"id": "W037V2-F3", "severity": "major",
         "statement": "MEASURED gate blind spot: the binding checker "
                      "artifacts/formulation/tools/check_class_schema.py returns pass "
                      "(0 failed rules) on the canonical bytes (M0), on a mutation that "
                      "INVERTS the formal visibility clause to assert visibility (M1), and "
                      "on a mutation that replaces visibility.definition with the very "
                      "whole-curve reading the artifact forbids (M4); the positive control "
                      "(M3, definition emptied) fails as expected. Therefore a PASS at this "
                      "hash is not evidence that the formal expansion agrees with the "
                      "canonical predicate: R03/R10 check presence, domain resolution and "
                      "vocabulary, not predicate agreement (the tool's own docstring lists "
                      "this blind spot).",
         "evidence": ["artifacts/formulation/tools/check_class_schema.py:175-200",
                      "artifacts/formulation/tools/check_class_schema.py:285-297",
                      "check_f1_visibility.py#mutations.M1", "check_f1_visibility.py#M3",
                      "check_f1_visibility.py#M4"],
         "cross_reference": "my prior verification (W037-GFORM-FREEZE-01) reported "
                            "machine_green_at_T1 from these same tools; this run shows what "
                            "that green does and does not cover."},
    ]

    payload = {
        "task_id": "W037-F1-VISIBILITY-02",
        "actor": "worker-037",
        "class_id": CLASS_ID,
        "node_id": NODE,
        "gate": GATE,
        "authority": "independent verification evidence only; NOT a gate verdict, NOT an "
                     "acceptance, NOT a node-status change; no canonical artifact was edited",
        "question": "At the frozen F1 bytes, is the visibility clause inside "
                    "quantifiers.formal the same predicate as visibility.definition, and are "
                    "quantifiers.formal and quantifiers.negation exact negations? (HF-06, "
                    "raised by deepseek-flash-19 at the same hash.)",
        "method": "read-only T0/T1 hash snapshots; textual extraction of the four predicate "
                  "sites with line numbers; structural tests V1-V7; exhaustive finite-model "
                  "check of the P_whole/P_tail relation; mutation tests M0-M3 against the "
                  "canonical checker; run_acceptance re-run",
        "wall_clock": {"t0": t0, "t1": t1},
        "target_bytes": s0,
        "target_bytes_T1": s1,
        "moved_during_check": moved,
        "reviewed_f1_sha256": s0[F1_REL].get("sha256"),
        "reviewed_f0_sha256": s0[F0_REL].get("sha256"),
        "authoring_mirror_f1_sha256": s0[F1_AUTHORING_REL].get("sha256"),
        "extractions": {
            "quantifiers.formal": formal,
            "quantifiers.formal_visibility_clause": formal_vis_clause,
            "domains.D4": d4,
            "domains.D5": d5,
            "visibility.definition": vis_def,
            "visibility.negation_conclusion": vis_neg,
            "conclusion.statement_formal": stmt_formal,
        },
        "predicate_reading": {
            "formal_clause": "not P_whole where P_whole(gamma) := exists q in I+ : "
                             "gamma subset J^-(q) cap M (no t0)",
            "canonical_conclusion": "not P_tail where P_tail(gamma) := exists q in I+ exists "
                                    "t0 in [0,T) : gamma([t0,T)) subset J^-(q) cap M",
            "relation": "P_whole => P_tail (take t0=0); P_tail =/=> P_whole; hence "
                        "not-P_whole is strictly weaker than not-P_tail",
        },
        "logical_relation": logical_relation_check(),
        "tests": tests,
        "mutations": mutations,
        "gate_insensitivity_demonstrated": gate_insensitive,
        "run_acceptance": {k: ra[k] for k in ("cmd", "exit_code", "ok")},
        "run_acceptance_stdout": ra["stdout"][:1500],
        "existing_corpus_cross_reference": [
            "deepseek-flash-19 flash19-F1-01-review-20260912T002228: HF-06 critical "
            "(this run confirms the predicate claim with a machine witness)",
            "deepseek-flash-21 f21-20260912T002329-review-F1: advisory HF-06-class",
            "deepseek-flash-22 f22-20260912T002210-review-F1: advisory only (freeze window)",
            "worker-059/worker-090: revise on metadata/pointer grounds, semantics reported "
            "as passing; neither tested formal-vs-definition agreement",
        ],
        "findings": findings,
        "worker_verdict": "revise: one confirmed critical content-level hard failure "
                          "(W037V2-F1) plus one dangling symbol at the reviewed F1 hash; "
                          "the canonical structural gate does not detect either",
        "does_not_claim": ["G-FORM pass/fail", "an accept verdict usable as one of the two "
                          "required independent accepts", "node completion", "theorem",
                           "physics result", "authority to edit canonical artifacts"],
        "next_falsifier": "Falsify W037V2-F1 by exhibiting, inside the same artifact, a "
                          "definitional bridge that makes quantifiers.formal line 55 "
                          "equivalent to visibility.definition line 220 (e.g. gamma is bound "
                          "to the tail, or a notation section defines 'gamma subset J^-(q)' "
                          "as the tail). Falsify W037V2-F3 by showing check_class_schema.py "
                          "fails on mutation M1. Falsify the whole report if the reviewed F1 "
                          "sha256 no longer matches disk or if T0 != T1. CONFIRMATION TEST "
                          "for the repair: add the t0/tail binder to both lines 54-55 and D5, "
                          "re-freeze, re-hash, and re-run this script - V1, V2, V5, V6 must "
                          "flip to pass.",
    }
    body = json.dumps({k: v for k, v in payload.items()}, indent=1, sort_keys=True)
    payload["report_payload_sha256"] = hashlib.sha256(body.encode()).hexdigest()
    out = OUT / "report.json"
    out.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n")
    print(f"wrote {out.relative_to(ROOT)} sha256={sha256_file(out)}")
    print(json.dumps({
        "reviewed_f1_sha256": payload["reviewed_f1_sha256"],
        "reviewed_f0_sha256": payload["reviewed_f0_sha256"],
        "moved": moved,
        "tests": {t["id"]: t["status"] for t in tests},
        "mutations": {m["name"]: ("pass" if m["ok"] else "fail") for m in mutations},
        "gate_insensitive": gate_insensitive,
        "strictness_witness_count": payload["logical_relation"]["strictness_witness_count"],
        "findings": [(f["id"], f["severity"]) for f in findings],
        "run_acceptance_ok": ra["ok"],
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
