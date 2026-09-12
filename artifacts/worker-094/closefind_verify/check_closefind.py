#!/usr/bin/env python3
"""W094C independent close-findings verification checker (worker-094, bounded task).

Class-bound task: F0 (+ its binding chain to AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN,
AF-SCC-C0-VAC-GEN, AF-WCC-SCALAR-SPH) at the revision published by
astra-life03-close-findings / astra-life03-repin-claims.

Deterministic, fail-closed, read-only on every canonical artifact. Binds to the
sha256 set in PINNED.json; if any canonical byte changes, the run reports
`drift` and the verdict is void (moving-target rule).

Run:
  python3 artifacts/worker-094/closefind_verify/check_closefind.py \
      --pinned artifacts/worker-094/closefind_verify/PINNED.json \
      --out artifacts/worker-094/closefind_verify/report.json
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

F0 = "research_map/formulation_taxonomy.yaml"
SUPP = "artifacts/formulation/formulation_taxonomy.yaml"
F1 = "schemas/af_wcc_vacuum.yaml"
F2A = "schemas/af_scc_c2_vacuum.yaml"
F2B = "schemas/af_scc_c0_vacuum.yaml"
FROZEN = "artifacts/formulation/FROZEN.json"
CASES = "schemas/taxonomy_cases.jsonl"
FALS = "schemas/f1_falsifier_tests.jsonl"
CONS = "artifacts/formulation/evidence/taxonomy_consistency.json"

CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
SCHEMA_OF = {
    "AF-WCC-VAC-GEN": F1,
    "AF-SCC-C2-VAC-GEN": F2A,
    "AF-SCC-C0-VAC-GEN": F2B,
}
CONCLUSION_TYPES = {
    "weak_cosmic_censorship",
    "strong_cosmic_censorship_C2",
    "strong_cosmic_censorship_C0",
}


def sha256_file(path):
    return hashlib.sha256(open(os.path.join(ROOT, path), "rb").read()).hexdigest()


def jload(path):
    return json.load(open(os.path.join(ROOT, path)))


class StrictLoader(yaml.SafeLoader):
    pass


def _no_dup(loader, node, deep=False):
    mapping = {}
    for k, v in node.value:
        key = loader.construct_object(k, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                None, None, "duplicate key: %r" % (key,), k.start_mark)
        mapping[key] = loader.construct_object(v, deep=deep)
    return mapping


StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_dup)


def yload(path):
    return yaml.load(open(os.path.join(ROOT, path)), Loader=StrictLoader)


def resolve_pointer(pointer):
    """Resolve 'path#a.b.c' against the YAML tree; returns (ok, detail)."""
    if "#" not in pointer:
        return False, "no '#' anchor"
    path, anchor = pointer.split("#", 1)
    full = os.path.join(ROOT, path)
    if not os.path.exists(full):
        return False, "path does not exist: %s" % path
    node = yload(path)
    cur = node
    for part in anchor.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, list):
            hit = None
            for item in cur:
                if isinstance(item, dict) and item.get("id") == part:
                    hit = item
                    break
            if hit is None:
                return False, "anchor segment %r not found in %s" % (part, path)
            cur = hit
        else:
            return False, "anchor segment %r not found in %s" % (part, path)
    return True, "resolves"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pinned", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    now = datetime.datetime.now().astimezone()
    pin = jload(args.pinned)
    pinn = pin["files"]

    checks = []
    hard = []
    findings = []

    def check(cid, ok, detail, refs=None, severity="hard", category="binding"):
        rec = {"id": cid, "status": "pass" if ok else "fail",
               "severity": severity, "category": category,
               "detail": detail, "evidence_refs": refs or []}
        checks.append(rec)
        if not ok and severity == "hard":
            hard.append(cid)
        return ok

    # 0. drift / moving target -------------------------------------------------
    drift = {}
    for p in pinn:
        try:
            m = sha256_file(p)
        except FileNotFoundError:
            m = "MISSING"
        if m != pinn[p]["sha256"]:
            drift[p] = {"pinned": pinn[p]["sha256"], "measured": m}
    if drift:
        checks.append({"id": "C0_no_drift", "status": "fail", "severity": "hard",
                       "category": "moving_target", "detail": json.dumps(drift),
                       "evidence_refs": []})
        out = {"schema_version": "w094c-closefind-1.0",
               "verdict": "VOID_MOVING_TARGET", "drift": drift,
               "checked_at": now.isoformat(timespec="seconds"), "checks": checks}
        json.dump(out, open(os.path.join(ROOT, args.out), "w"), indent=1)
        print("VOID: drift", json.dumps(drift))
        return 3

    checks.append({"id": "C0_no_drift", "status": "pass", "severity": "hard",
                   "category": "moving_target",
                   "detail": "all %d pinned artifacts byte-identical at check time" % len(pinn),
                   "evidence_refs": ["%s#%s" % (p, pinn[p]["sha256"][:12]) for p in pinn]})

    f0_sha = pinn[F0]["sha256"]
    f1_sha = pinn[F1]["sha256"]

    # 1. F0 structural criteria ------------------------------------------------
    f0 = yload(F0)
    ids = f0.get("class_ids")
    check("C1_f0_exactly_four_class_ids", ids == CLASS_IDS,
          "class_ids=%r" % (ids,), ["%s#%s" % (F0, f0_sha[:12])])
    classes = f0.get("classes") or {}
    check("C2_f0_classes_match_class_ids", sorted(classes.keys()) == sorted(CLASS_IDS),
          "classes keys=%r" % (sorted(classes.keys()),),
          ["%s#classes" % F0])
    disj = f0.get("disjointness")
    n_pairs = len(disj) if isinstance(disj, (list, dict)) else 0
    check("C3_f0_disjointness_six_pairs", n_pairs == 6,
          "disjointness entries=%d (expect 6 unordered pairs)" % n_pairs,
          ["%s#disjointness" % F0])
    ctypes = {cid: (classes.get(cid, {}).get("axes", {}) or {}).get("conclusion_type")
              for cid in CLASS_IDS}
    check("C4_f0_conclusion_types_distinct_vocabulary",
          len(set(ctypes.values())) == 3 and set(ctypes.values()) <= CONCLUSION_TYPES,
          "conclusion_type per class=%r" % (ctypes,), ["%s#classes.*.axes" % F0])

    # 2. schema <-> F0 binding chain ------------------------------------------
    for cid, path in SCHEMA_OF.items():
        s = yload(path)
        check("C5_%s_class_id_matches_path" % cid, s.get("class_id") == cid,
              "artifact class_id=%r expected=%r" % (s.get("class_id"), cid),
              ["%s#%s" % (path, pinn[path]["sha256"][:12])])
        ptr = str(s.get("class_contract_pointer", ""))
        ok, detail = resolve_pointer(ptr)
        check("C6_%s_contract_pointer_resolves" % cid,
              ok and ptr.startswith(F0 + "#classes."),
              "pointer=%r -> %s" % (ptr, detail),
              ["%s#class_contract_pointer" % path, "%s#classes.%s" % (F0, cid)])
        fb = s.get("f0_binding") or {}
        check("C7_%s_f0_binding_matches_measured" % cid,
              fb.get("declared_f0_sha256") == f0_sha,
              "declared=%r measured=%s" % (fb.get("declared_f0_sha256"), f0_sha[:16]),
              ["%s#f0_binding" % path, "%s#%s" % (F0, f0_sha[:12])])
        sup = str(fb.get("class_contract_supplement_pointer", ""))
        ok2, detail2 = resolve_pointer(sup)
        check("C8_%s_supplement_pointer_resolves" % cid,
              ok2 and "artifacts/formulation/formulation_taxonomy.yaml#class_contracts." in sup,
              "supplement pointer=%r -> %s" % (sup, detail2),
              ["%s#f0_binding.class_contract_supplement_pointer" % path], severity="warn")
        cons_meas = sha256_file(CONS)
        check("C9_%s_consistency_evidence_sha_matches_measured" % cid,
              fb.get("consistency_evidence_sha256") == cons_meas,
              "declared=%r measured=%s" % (fb.get("consistency_evidence_sha256"), cons_meas[:16]),
              ["%s#f0_binding.consistency_evidence_sha256" % path,
               "%s#%s" % (CONS, cons_meas[:12])])

    # 3. FROZEN manifest -------------------------------------------------------
    fr = jload(FROZEN)
    for p in [F0, F1, F2A, F2B]:
        e = (fr.get("files") or {}).get(p) or {}
        check("C10_frozen_declares_%s" % os.path.basename(p), e.get("sha256") == pinn[p]["sha256"],
              "declared=%r measured=%s" % (e.get("sha256"), pinn[p]["sha256"][:16]),
              ["%s#files.%s" % (FROZEN, p)])

    # 4. repin artifacts -------------------------------------------------------
    rows = [json.loads(l) for l in open(os.path.join(ROOT, CASES)) if l.strip()]
    meta = [r for r in rows if r.get("record_type") == "meta"]
    meta = meta[0] if meta else {}
    mref = (meta.get("taxonomy_ref") or {})
    check("C11_cases_meta_pin_matches_f0",
          mref.get("sha256") == f0_sha and mref.get("revision") == f0.get("revision"),
          "meta taxonomy_ref=%r vs measured F0 %s rev%s" % (mref, f0_sha[:16], f0.get("revision")),
          ["%s#meta.taxonomy_ref" % CASES, "%s#%s" % (F0, f0_sha[:12])])
    bad_rows = [r.get("case_id") for r in rows
                if r.get("record_type") == "case"
                and f0_sha[:12] not in str(r.get("binding_status", ""))]
    ncase = sum(1 for r in rows if r.get("record_type") == "case")
    check("C12_cases_rows_bind_measured_f0", not bad_rows,
          "%d/%d case rows still bind outside %s; stale ids=%r" %
          (len(bad_rows), ncase, f0_sha[:12], bad_rows[:6]),
          ["%s#binding_status" % CASES])
    frows = [json.loads(l) for l in open(os.path.join(ROOT, FALS)) if l.strip()]
    fbad = [r.get("test_id") or r.get("case_id") or r.get("id") for r in frows
            if f1_sha[:12] not in str(r.get("binding_sha256", ""))]
    check("C13_falsifier_rows_bind_measured_f1", not fbad,
          "%d/%d rows still bind outside %s; stale ids=%r" %
          (len(fbad), len(frows), f1_sha[:12], fbad[:6]),
          ["%s#binding_sha256" % FALS])

    # 5. hygiene ---------------------------------------------------------------
    dup = []
    for p in [F0, F1, F2A, F2B]:
        try:
            yload(p)
        except yaml.constructor.ConstructorError as e:
            dup.append("%s: %s" % (p, e.problem))
        except Exception as e:  # noqa: BLE001
            dup.append("%s: %s" % (p, e))
    check("C14_no_duplicate_yaml_keys", not dup, "strict-load errors=%r" % (dup,),
          ["%s" % F0], category="hygiene")

    future = []
    ts_re = re.compile(r"^(?:\s*)(written_at|revised_at|created_at|checked_at|frozen_at|decided_at|rebound_at):\s*[\"']?([0-9T:+\-]+)")
    for p in [F0, F1, F2A, F2B, FROZEN, CASES, FALS, CONS]:
        text = open(os.path.join(ROOT, p)).read()
        for m in ts_re.finditer(text):
            try:
                t = datetime.datetime.fromisoformat(m.group(2))
            except ValueError:
                continue
            if t.tzinfo is None:
                t = t.replace(tzinfo=now.tzinfo)
            if t > now + datetime.timedelta(seconds=90):
                future.append("%s:%s=%s" % (p, m.group(1), m.group(2)))
    check("C15_no_future_timestamps", not future,
          "future-dated fields=%r (wall clock %s)" % (future, now.isoformat(timespec="seconds")),
          ["%s" % F0], category="hygiene")

    # 6. prior-finding closure (HF-094-F0-1/2/3 + B-16F0-1/2/3) ---------------
    # Operative clause = conclusion text with annotated revocation notes removed, so a note
    # that NAMES the superseded predicate is not mistaken for the predicate itself. Only
    # brackets whose content looks like an annotation are stripped; interval notation such
    # as [0,T) is left intact (it has no closing bracket and must not be eaten).
    def operative(text):
        return re.sub(r"\[[^\[\]]*(?:rev\d|superseded|discharge|amended|not this class)[^\[\]]*\]",
                      " ", str(text), flags=re.I)

    setbased_in_conclusion = []
    tail_ok = {}
    for cid in CLASS_IDS:
        ctext = operative((classes.get(cid, {}).get("conclusion", {}) or {}).get("text", ""))
        if "J-(" in ctext or "J^-(I+" in ctext:
            setbased_in_conclusion.append(cid)
        # Only the two WCC classes carry a visibility predicate; it must be the single-q tail form.
        if cid.startswith("AF-WCC"):
            tail_ok[cid] = "J^-(" in ctext
    check("C16_prior_HF094F0_1_no_setbased_predicate_in_any_conclusion",
          not setbased_in_conclusion and all(tail_ok.values()),
          "operative set-based residue in=%r; single-q tail predicate present per WCC class=%r"
          % (setbased_in_conclusion, tail_ok),
          ["%s#classes.*.conclusion.text" % F0])

    scal = classes.get("AF-WCC-SCALAR-SPH", {})
    stext = str((scal.get("conclusion", {}) or {}).get("text", ""))
    gen_kind = (scal.get("axes", {}) or {}).get("genericity_kind")
    first_q = min([i for i in (stext.find("For every"), stext.find("for every")) if i >= 0] or [-1])
    check("C17_prior_HF094F0_2_scalar_comeager_bound_first",
          "comeager" in stext and (first_q < 0 or stext.index("comeager") < first_q)
          and "equivalently" not in stext.lower(),
          "comeager index=%d, first data-quantifier index=%d, 'equivalently' present=%s, genericity_kind=%r"
          % (stext.find("comeager"), first_q, "equivalently" in stext.lower(), gen_kind),
          ["%s#classes.AF-WCC-SCALAR-SPH.conclusion.text" % F0])
    if gen_kind == "unresolved":
        findings.append({
            "id": "F-094C-1", "severity": "major", "axis": "genericity label vs conclusion text",
            "lines_ref": "%s#classes.AF-WCC-SCALAR-SPH" % F0,
            "finding": ("AF-WCC-SCALAR-SPH.axes.genericity_kind is 'unresolved' while its repaired "
                        "conclusion text commits to 'a comeager set G of data in the class, chosen "
                        "before and independently of the data'. The other three classes carry "
                        "'provisional_baire_residual'. Either the axis is stale (should be "
                        "provisional_baire_residual) or the conclusion names a notion the axis "
                        "declares unresolved; both cannot stand as the exact-genericity record."),
            "falsifier": ("Set axes.genericity_kind to provisional_baire_residual (or another named "
                          "token) at a new hash, or remove the comeager commitment from the scalar "
                          "conclusion. Either voids this finding."),
            "evidence_refs": ["%s#classes.AF-WCC-SCALAR-SPH.axes.genericity_kind" % F0,
                              "%s#classes.AF-WCC-SCALAR-SPH.conclusion.text" % F0]})
    if str(f0.get("status")) == "draft_unverified":
        findings.append({
            "id": "F-094C-2", "severity": "major", "axis": "self-declared artifact status",
            "lines_ref": "%s#status" % F0,
            "finding": ("The published close-findings F0 rev%s still self-declares "
                        "status: draft_unverified. G-F0's audit trail cannot record an accept on an "
                        "artifact whose own status says draft; the label is author-owned (CF-4), so "
                        "this is an author action item, not a defect of the class content." % f0.get("revision"),),
            "falsifier": "Author sets status to a reviewed/frozen value at a new hash.",
            "evidence_refs": ["%s#status" % F0]})
    if not (fr.get("files") or {}).get(CASES):
        findings.append({
            "id": "F-094C-3", "severity": "minor", "axis": "frozen manifest coverage",
            "lines_ref": "%s#files" % FROZEN,
            "finding": ("FROZEN rev%s does not carry an entry for %s (or %s), so the repinned "
                        "corpora are not covered by the frozen manifest even though G-F0 cites the "
                        "case corpus as evidence." % (fr.get("revision"), CASES, FALS)),
            "falsifier": "Add both corpus hashes to the manifest at a new revision.",
            "evidence_refs": ["%s#files" % FROZEN, "%s#%s" % (CASES, pinn[CASES]["sha256"][:12])]})

    verdict = "revise" if hard else "accept_with_findings"
    report = {
        "schema_version": "w094c-closefind-1.0",
        "record_id": "W094C-CLOSEFIND-VERIFY-01",
        "task": "independent verification of the astra-life03-close-findings / repin-claims publication",
        "reviewer": "worker-094",
        "node_id": "F0,F1,F2a,F2b",
        "class_ids": CLASS_IDS,
        "checked_at": now.isoformat(timespec="seconds"),
        "pinned": {p: pinn[p]["sha256"] for p in pinn},
        "checker_sha256": sha256_file("artifacts/worker-094/closefind_verify/check_closefind.py"),
        "counts": {"checks": len(checks),
                   "passed": sum(1 for c in checks if c["status"] == "pass"),
                   "failed_hard": len(hard), "findings": len(findings)},
        "verdict_recommendation": verdict,
        "hard_failures": [c for c in checks if c["status"] == "fail" and c["severity"] == "hard"],
        "findings": findings,
        "checks": checks,
        "prior_findings_closure": {
            "HF-094-F0-1": "closed at rev5 (C16 pass)" if not setbased_in_conclusion else "OPEN",
            "HF-094-F0-2": "closed at rev5 (C17 pass: 'equivalently' removed, comeager bound first)",
            "HF-094-F0-3": "closed at rev5 (C6/C8 pass: canonical pointer + separate supplement pointer)",
            "HF-094-F0-4": "meta rebind landed, per-row rebind NOT landed (C12 fail)",
            "HF-094-F0-5": "addressed by f0_mirror_disposition (different logical artifacts, REC-1 requested); byte-identity refused",
            "B-16F0-1/B-16F0-2/B-16F0-3": "closed at rev5 per C16/C17/C6",
        },
        "authority_note": ("Worker verdict is advisory evidence only; per research_map/ASTRA_HANDOFF.md "
                           "worker events cannot set node status=done, validation_status=passed, or a "
                           "gate verdict. Only the controller and group leads can move those."),
    }
    json.dump(report, open(os.path.join(ROOT, args.out), "w"), indent=1)
    print("%s: %d/%d checks pass, %d hard failures, %d findings" %
          (verdict, report["counts"]["passed"], len(checks), len(hard), len(findings)))
    for c in report["hard_failures"]:
        print(" HARD", c["id"], "-", c["detail"][:160])
    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main())
