#!/usr/bin/env python3
"""
W078-F1-REPAIR-VERIFY-01  --  independent, hash-bound verification of the F1 rev12 repair.

Target : schemas/af_wcc_vacuum.yaml
Task   : verify that revision 12 (pin cce9c60146d6...) repairs the independently confirmed
         critical defect HF-06 / HF-15-1 (whole-curve vs tail visibility quantifier) and the
         co-emitted defects (duplicate revised_at, future-dated stamp, unresolved
         class_contract_pointer, undefined AF_{I+}, ill-typed D0 disjunction-under-forall).

Method : pin -> snapshot -> deterministic checks -> test-retest; live/authoring drift is
         measured at start and end and voids the *binding*, not the verdict on pinned bytes.
         A positive control runs the same core predicates against the OLD defective snapshot
         9a8bd4c96800, which must be classified DEFECT; without that the repair verdict is void.

Scope  : structural / contract / semantic-form only.  No truth, non-vacuity, physics or
         citation verdict.  Worker verdict only; sets no gate verdict and no node status.
Author : worker-078 (not an author of the schema or of any F0 artifact)
"""

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta

try:
    import yaml
except Exception as exc:  # pragma: no cover
    print(json.dumps({"error": "PyYAML unavailable: %s" % exc}))
    sys.exit(2)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PIN = "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3"
OLD_PIN = "9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503"
TARGET = "schemas/af_wcc_vacuum.yaml"
AUTHORING = "artifacts/formulation/schemas/af_wcc_vacuum.yaml"
OLD_SNAPSHOT = "artifacts/worker-078/f1_quantifier_adjudication/snapshot/af_wcc_vacuum.9a8bd4c96800.yaml"
SNAPSHOT = "artifacts/worker-078/f1_repair_verify/snapshot/af_wcc_vacuum.cce9c60146d6.yaml"
CANON_F0 = "research_map/formulation_taxonomy.yaml"
AUTH_F0 = "artifacts/formulation/formulation_taxonomy.yaml"
FROZEN = "artifacts/formulation/FROZEN.json"
CSTAMP = "+08:00"


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(p):
    with open(p, "rb") as fh:
        return sha256_bytes(fh.read())


def now_local():
    return datetime.now(timezone(timedelta(hours=8)))


def parse_ts(s):
    if not isinstance(s, str):
        return None
    m = re.match(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(\.\d+)?([+-]\d{2}:?\d{2})$", s.strip())
    if not m:
        return None
    try:
        base = datetime.fromisoformat(m.group(1) + m.group(3))
    except ValueError:
        return None
    return base


def walk_dup_keys(node, path="$"):
    """Yield (dotted path, key) for every duplicate mapping key under a yaml.compose tree."""
    out = []

    def rec(n, p):
        if isinstance(n, yaml.MappingNode):
            seen = {}
            for k, v in n.value:
                key = getattr(k, "value", None)
                if key in seen:
                    out.append(("%s.%s" % (p, key), key))
                else:
                    seen[key] = True
                rec(v, "%s.%s" % (p, key) if key is not None else p)
        elif isinstance(n, yaml.SequenceNode):
            for i, v in enumerate(n.value):
                rec(v, "%s[%d]" % (p, i))

    rec(node, path)
    return out


def resolve_pointer(doc, pointer):
    """Resolve '#a.b.c' inside a loaded YAML doc; returns (ok, detail)."""
    if "#" not in pointer:
        return False, "no '#' anchor in pointer"
    path = pointer.split("#", 1)[1]
    cur = doc
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            where = "top-level keys=%s" % sorted(cur.keys()) if isinstance(cur, dict) else type(cur).__name__
            return False, "segment %r absent (%s)" % (part, where)
    return True, "resolves (%s)" % type(cur).__name__


class Doc(object):
    def __init__(self, path, label):
        with open(path, "rb") as fh:
            self.raw = fh.read()
        self.text = self.raw.decode("utf-8")
        self.lines = self.text.splitlines()
        self.sha = sha256_bytes(self.raw)
        self.label = label
        self.data = yaml.safe_load(self.raw)
        self.compose = yaml.compose(self.raw)

    def line_of(self, pattern, start=1):
        rx = re.compile(pattern)
        for i in range(start - 1, len(self.lines)):
            if rx.search(self.lines[i]):
                return i + 1
        return None

    def all_lines(self, pattern):
        rx = re.compile(pattern)
        return [(i + 1, l.strip()) for i, l in enumerate(self.lines) if rx.search(l)]


def check(checks, cid, label, status, kind, evidence, detail):
    checks.append({
        "id": cid, "label": label, "status": status, "kind": kind,
        "evidence": evidence, "detail": detail,
    })


# --------------------------------------------------------------------------------------
# core predicate: does a document carry the tail-form quantifier repair?
# shared by the target run and the positive control on the defective snapshot.
# --------------------------------------------------------------------------------------
CONTAIN_VERB = r"(?:is\s+)?(?:not\s+)?(?:subset|contained\s+in)\s+(?:the\s+causal\s+past\s+)?J\^-\s*\(q\)"
WHOLE = r"gamma\s*(?:\(\[0,T\)\))?\s*" + CONTAIN_VERB
TAIL = r"gamma\s*\(\[t0,T\)\)\s*" + CONTAIN_VERB


def core_repair_probe(doc):
    """Return per-predicate booleans for the HF-06 repair, independent of doc identity."""
    q = doc.data.get("quantifiers") or {}
    formal = (q.get("formal") or "")
    neg = (q.get("negation") or "")
    d5 = (((q.get("domains") or {}).get("D5") or {}).get("definition") or "")
    vis = (doc.data.get("visibility") or {})
    vis_def = vis.get("definition") or ""
    vis_neg = vis.get("negation_conclusion") or ""
    conc = (doc.data.get("conclusion") or {})
    stmt = conc.get("statement_formal") or ""
    formal_neg_clause = ""
    for ln in formal.splitlines():
        if "not exists" in ln and ("J^-" in ln or "visible" in ln):
            formal_neg_clause = ln.strip()
    return {
        "formal_negative_clause": formal_neg_clause,
        "formal_has_tail": bool(re.search(TAIL, formal, re.I)),
        "formal_has_whole": bool(re.search(WHOLE, formal, re.I)),
        "d5_has_tail": bool(re.search(TAIL, d5, re.I)),
        "d5_has_whole_exclusion": bool(re.search(WHOLE, d5, re.I)) and ("NOT the predicate" in d5 or "STRONGER" in d5),
        "d5_names_pair": bool(re.search(r"\(\s*q\s*,\s*t0\s*\)", d5)),
        "negation_has_tail": bool(re.search(r"tail", neg, re.I)) and bool(re.search(r"visible", neg, re.I)),
        "vis_def_has_tail": bool(re.search(TAIL, vis_def, re.I)),
        "vis_def_has_whole_warning": bool(re.search(r"whole", vis_def, re.I)) and bool(re.search(r"misclassif|would", vis_def, re.I)),
        "vis_neg_has_tail": bool(re.search(TAIL, vis_neg, re.I)),
        "stmt_expands_predicate": "visible_singularity_from_I_plus(M_D)" in stmt,
        "stmt_has_no_visible": "not exists visible_singularity_from_I_plus" in stmt,
    }


def main():
    started = now_local()
    checks = []
    snap_path = os.path.join(ROOT, SNAPSHOT)
    if not os.path.exists(snap_path):
        os.makedirs(os.path.dirname(snap_path), exist_ok=True)
        with open(os.path.join(ROOT, TARGET), "rb") as src, open(snap_path, "wb") as dst:
            dst.write(src.read())
    target = Doc(snap_path, "pinned-snapshot")          # primary: immutable pinned bytes
    live = Doc(os.path.join(ROOT, TARGET), "live-canonical")
    old = Doc(os.path.join(ROOT, OLD_SNAPSHOT), "old-pin-snapshot")

    # ---- binding -----------------------------------------------------------------
    check(checks, "R00", "pinned snapshot bytes equal the declared pin", "PASS" if target.sha == PIN else "FAIL",
          "binding", "%s#%s" % (SNAPSHOT, PIN[:12]), "measured %s" % target.sha)
    check(checks, "R00b", "live canonical equals the pinned snapshot", "PASS" if live.sha == target.sha else "FAIL",
          "binding", "%s#%s" % (TARGET, live.sha[:12]), "live=%s pin=%s" % (live.sha[:12], target.sha[:12]))
    authoring_re = sha256_file(os.path.join(ROOT, AUTHORING))
    check(checks, "R01", "authoring mirror equals canonical at pin", "PASS" if authoring_re == target.sha else "FAIL",
          "binding", "%s#%s" % (AUTHORING, authoring_re[:12]), "canonical %s" % target.sha)
    with open(os.path.join(ROOT, FROZEN)) as fh:
        frozen = json.load(fh)
    fentry = (frozen.get("files") or {}).get(TARGET) or {}
    fpin = fentry.get("sha256")
    check(checks, "R02", "FROZEN manifest entry for F1 equals pin",
          "PASS" if fpin == PIN else "FAIL", "binding",
          "%s#rev%s" % (FROZEN, frozen.get("revision")),
          "manifest=%s measured=%s" % (str(fpin)[:12], PIN[:12]))

    # ---- header hygiene ----------------------------------------------------------
    dups = walk_dup_keys(target.compose)
    check(checks, "R03", "no duplicate top-level YAML mapping keys (strict compose walk)",
          "PASS" if not dups else "FAIL", "data_integrity", "%s#%s" % (TARGET, PIN[:12]),
          "duplicates=%s" % (dups[:8] if dups else "none"))
    f1 = target.data
    fb = f1.get("f0_binding") or {}
    stamps = {"revised_at": f1.get("revised_at"), "authored_at": f1.get("authored_at"),
              "f0_binding.checked_at": fb.get("checked_at")}
    future = []
    for k, v in stamps.items():
        ts = parse_ts(v)
        if ts is not None and ts > started:
            future.append("%s=%s (+%.0fs)" % (k, v, (ts - started).total_seconds()))
    check(checks, "R04", "no machine-readable timestamp ahead of the measurement clock",
          "PASS" if not future else "FAIL", "clock_discipline", "%s#%s" % (TARGET, PIN[:12]),
          "future=%s; measured_at=%s" % (future or "none", started.isoformat()))
    try:
        sys.path.insert(0, os.path.join(ROOT, "research_map"))
        import class_separation as csep
        csep_findings = csep.findings_for_text(target.text, TARGET)
    except Exception as exc:  # canonical helper unavailable -> fall back to a strict phrase scan
        csep_findings = ["helper-unavailable: %s" % exc]
    merge_findings = [f for f in csep_findings if re.search(r"composite|merge", f, re.I)]
    comp_lines = [(i + 1, l.strip()) for i, l in enumerate(target.lines) if re.search(r"C0\s+or\s+C2", l)]
    comp_asserted = [x for x in comp_lines
                     if re.match(r"\s*(class_id|class_ids|classes|class_components|conclusion_type)\s*[:=]", x[1])]
    check(checks, "R05", "single class id AF-WCC-VAC-GEN; no composite C0/C2 merge finding",
          "PASS" if (f1.get("class_id") == "AF-WCC-VAC-GEN" and not merge_findings and not comp_asserted) else "FAIL",
          "class_binding", "%s:3" % TARGET,
          "class_id=%s merge_findings=%s asserted_composite_lines=%s all_composite_lines=%s helper_findings=%s" % (
              f1.get("class_id"), merge_findings or "none", comp_asserted or "none",
              [n for n, _ in comp_lines] or "none", csep_findings or "none"))

    # ---- core quantifier repair (HF-06 / HF-15-1) --------------------------------
    probe = core_repair_probe(target)
    c07 = probe["formal_has_tail"] and not probe["formal_has_whole"]
    check(checks, "R06", "quantifiers.formal negative clause is single-q TAIL containment, not whole-curve",
          "PASS" if c07 else "FAIL", "semantic_form",
          "%s:%s" % (TARGET, target.line_of(r"not exists q in I\+ and t0")),
          "clause=%r tail=%s whole=%s" % (probe["formal_negative_clause"][:160], probe["formal_has_tail"], probe["formal_has_whole"]))
    c08 = probe["d5_has_tail"] and probe["d5_has_whole_exclusion"] and probe["d5_names_pair"]
    check(checks, "R07", "D5 domain is the (q,t0) tail predicate and excludes whole-curve containment",
          "PASS" if c08 else "FAIL", "semantic_form",
          "%s:%s" % (TARGET, target.line_of(r"^\s+D5:")),
          "tail=%s exclusion=%s pair=%s" % (probe["d5_has_tail"], probe["d5_has_whole_exclusion"], probe["d5_names_pair"]))
    c09 = probe["negation_has_tail"]
    check(checks, "R08", "quantifiers.negation negates the tail predicate ('has a tail visible from I+')",
          "PASS" if c09 else "FAIL", "semantic_form",
          "%s:%s" % (TARGET, target.line_of(r"future-inextendible causal geodesic of finite affine length has a tail")),
          "negation_tail_marker=%s" % c09)
    c10 = probe["vis_def_has_tail"] and probe["vis_def_has_whole_warning"] and probe["vis_neg_has_tail"]
    check(checks, "R09", "canonical visibility predicate and its negation both remain tail-based",
          "PASS" if c10 else "FAIL", "semantic_form",
          "%s:%s" % (TARGET, target.line_of(r"^\s+definition: \"a future-inextendible causal geodesic")),
          "def_tail=%s whole_warning=%s neg_tail=%s" % (probe["vis_def_has_tail"], probe["vis_def_has_whole_warning"], probe["vis_neg_has_tail"]))
    c11 = probe["stmt_expands_predicate"] and probe["stmt_has_no_visible"]
    check(checks, "R10", "conclusion.statement_formal expands to the negation of the tail predicate",
          "PASS" if c11 else "FAIL", "semantic_form",
          "%s:%s" % (TARGET, target.line_of(r"^\s+statement_formal:")),
          "expands=%s no_visible=%s" % (probe["stmt_expands_predicate"], probe["stmt_has_no_visible"]))
    ordered = (f1.get("quantifiers") or {}).get("ordered") or []
    binders = [str(x.get("binder")) for x in ordered if isinstance(x, dict)]
    d5_ordered_ok = any(b.strip() == "(q,t0)" for b in binders) and any(
        x.get("domain_id") == "D5" and str(x.get("binder")).strip() == "(q,t0)" for x in ordered if isinstance(x, dict))
    check(checks, "R11", "ordered prefix binds not_exists over the D5 pair (q,t0)",
          "PASS" if d5_ordered_ok else "FAIL", "semantic_form", "%s:48-54" % TARGET,
          "binders=%s" % binders)

    # ---- co-emitted repairs ------------------------------------------------------
    check(checks, "R12", "AF_{I+} symbol is defined in-schema (predicate_abbreviation)",
          "PASS" if (f1.get("i_plus") or {}).get("predicate_abbreviation") else "FAIL",
          "contract", "%s:%s" % (TARGET, target.line_of(r"predicate_abbreviation")),
          "occurrences_in_file=%d" % len(re.findall(r"AF_\{I\+\}", target.text)))
    q = f1.get("quantifiers") or {}
    d0 = ((q.get("domains") or {}).get("D0") or {}).get("definition") or ""
    d0_ok = ("tagged disjoint union" in d0 and "r = smooth" in d0 and "(sobolev,s,delta)" in d0)
    no_pair_binder = not re.search(r"\(s,\s*delta\)", target.text)
    check(checks, "R13", "D0 is a tagged regularity index; no (s,delta) pair binder survives",
          "PASS" if (d0_ok and no_pair_binder) else "FAIL", "semantic_form",
          "%s:%s" % (TARGET, target.line_of(r"^\s+D0:")),
          "tagged_union=%s no_pair_binder=%s" % (d0_ok, no_pair_binder))
    check(checks, "R14", "declared F0 hash equals the measured canonical taxonomy hash",
          "PASS" if fb.get("declared_f0_sha256") == sha256_file(os.path.join(ROOT, CANON_F0)) else "FAIL",
          "cross_artifact", "%s#%s" % (CANON_F0, sha256_file(os.path.join(ROOT, CANON_F0))[:12]),
          "declared=%s" % str(fb.get("declared_f0_sha256"))[:12])
    cdoc = yaml.safe_load(open(os.path.join(ROOT, CANON_F0), "rb"))
    ok_c, det_c = resolve_pointer(cdoc, f1.get("class_contract_pointer") or "")
    check(checks, "R15", "class_contract_pointer resolves in the canonical taxonomy",
          "PASS" if ok_c else "FAIL", "cross_artifact", "%s#%s" % (CANON_F0, sha256_file(os.path.join(ROOT, CANON_F0))[:12]),
          "%s -> %s" % (f1.get("class_contract_pointer"), det_c))
    adoc = yaml.safe_load(open(os.path.join(ROOT, AUTH_F0), "rb"))
    ok_a, det_a = resolve_pointer(adoc, f1.get("class_contract_supplement_pointer") or "")
    check(checks, "R16", "class_contract_supplement_pointer resolves in the authoring supplement",
          "PASS" if ok_a else "FAIL", "cross_artifact", "%s#%s" % (AUTH_F0, sha256_file(os.path.join(ROOT, AUTH_F0))[:12]),
          "%s -> %s" % (f1.get("class_contract_supplement_pointer"), det_a))
    ce_path = os.path.join(ROOT, fb.get("consistency_evidence") or "")
    ce_ok = os.path.exists(ce_path) and sha256_file(ce_path) == fb.get("consistency_evidence_sha256")
    ce_measured = sha256_file(ce_path) if os.path.exists(ce_path) else None
    check(checks, "R17", "declared consistency_evidence exists and its sha256 matches",
          "PASS" if ce_ok else "FAIL", "evidence_binding", str(fb.get("consistency_evidence")),
          "declared=%s measured=%s file_mtime=%s f1_revised_at=%s" % (
              str(fb.get("consistency_evidence_sha256"))[:12], str(ce_measured)[:12],
              datetime.fromtimestamp(os.path.getmtime(ce_path)).isoformat() if ce_measured else "absent",
              f1.get("revised_at")))

    # ---- positive control on the OLD defective bytes -----------------------------
    old_probe = core_repair_probe(old)
    old_pin_ok = old.sha == OLD_PIN
    control_discriminates = (
        not old_probe["formal_has_tail"] and old_probe["formal_has_whole"]
        and old_probe["d5_has_tail"] is False and old_probe["negation_has_tail"] is False
    )
    check(checks, "R18", "CONTROL: identical predicates classify the old defective snapshot as DEFECT",
          "PASS" if (old_pin_ok and control_discriminates) else "FAIL", "control",
          "%s#%s" % (OLD_SNAPSHOT, OLD_PIN[:12]),
          "old tail=%s whole=%s d5_tail=%s neg_tail=%s" % (
              old_probe["formal_has_tail"], old_probe["formal_has_whole"],
              old_probe["d5_has_tail"], old_probe["negation_has_tail"]))

    # ---- end-of-run drift --------------------------------------------------------
    end_live = sha256_file(os.path.join(ROOT, TARGET))
    end_auth = sha256_file(os.path.join(ROOT, AUTHORING))
    end_f0 = sha256_file(os.path.join(ROOT, CANON_F0))
    drift = []
    if end_live != target.sha:
        drift.append("live canonical moved to %s" % end_live)
    if end_auth != target.sha:
        drift.append("authoring mirror moved to %s" % end_auth)
    if end_f0 != fb.get("declared_f0_sha256"):
        drift.append("canonical F0 moved to %s (F1 declared %s)" % (end_f0[:12], str(fb.get("declared_f0_sha256"))[:12]))
    check(checks, "R19", "no drift of live/authoring/F0 bytes during the verification window",
          "PASS" if not drift else "FAIL", "binding", "%s#%s" % (TARGET, PIN[:12]),
          "; ".join(drift) if drift else "stable across the run")

    hard_fail = [c for c in checks if c["status"] == "FAIL" and c["kind"] != "control"]
    control_fail = [c for c in checks if c["status"] == "FAIL" and c["kind"] == "control"]
    if control_fail:
        verdict = "inconclusive"
    elif hard_fail:
        verdict = "revise"
    else:
        verdict = "accept"

    report = {
        "report_id": "W078-F1-REPAIR-VERIFY-01",
        "task_id": "W078-F1-REPAIR-VERIFY-01",
        "worker": "worker-078",
        "kind": "independent class-bound repair verification",
        "reviewer_independence": "worker-078 authored no F0/F1/F2a/F2b artifact and no repair under test; checks are this worker's own",
        "class_id": "AF-WCC-VAC-GEN",
        "node_id": "F1",
        "gate": "G-FORM",
        "started_at": started.isoformat(),
        "finished_at": now_local().isoformat(),
        "target": {
            "path": TARGET,
            "pin": PIN,
            "snapshot": SNAPSHOT,
            "sha256_at_review": target.sha,
            "authoring_mirror_sha256": authoring_re,
            "frozen_revision": frozen.get("revision"),
            "revision_field": f1.get("revision"),
            "live_sha256_at_end": end_live,
            "live_drift": bool(drift),
            "old_pin": OLD_PIN,
            "old_snapshot": OLD_SNAPSHOT,
        },
        "repairs_verified": {
            "HF-06/HF-15-1 whole-curve -> tail quantifier": c07 and c08 and c09 and c10 and c11 and d5_ordered_ok,
            "duplicate revised_at keys collapsed": not dups,
            "future-dated stamp corrected": not future,
            "class_contract_pointer canonical + supplement split": ok_c and ok_a,
            "AF_{I+} defined": bool((f1.get("i_plus") or {}).get("predicate_abbreviation")),
            "D0 retyped (tagged index, no (s,delta) binder)": d0_ok and no_pair_binder,
            "F0 binding refreshed to measured canonical hash": fb.get("declared_f0_sha256") == sha256_file(os.path.join(ROOT, CANON_F0)),
        },
        "checks": checks,
        "counts": {
            "total": len(checks),
            "pass": sum(1 for c in checks if c["status"] == "PASS"),
            "fail": sum(1 for c in checks if c["status"] == "FAIL"),
            "hard_fail": len(hard_fail),
            "control_fail": len(control_fail),
        },
        "verdict": verdict,
        "score": 4.5 if verdict == "accept" else (3.0 if verdict == "revise" else 2.0),
        "binding": ("snapshot-pinned; live canonical and authoring mirror re-measured equal at end of run"
                    if not drift else "VOID: drift observed during the window; verdict binds only to the snapshot"),
        "hard_failures": [{"id": c["id"], "label": c["label"], "detail": c["detail"]} for c in hard_fail],
        "scope_limit": ("Structural / contract / semantic-form verification of the rev12 repair at the pinned "
                        "hash only. Does not assess truth, non-vacuity, physical correctness, citation support, "
                        "or the residual f1_falsifier_tests.jsonl rebinding. Not a gate verdict; sets no node status."),
        "residual_items": [
            "schemas/f1_falsifier_tests.jsonl remains bound to a superseded F1 hash (worker-15 F-15-5); it cannot be cited for this revision until rebound.",
            "class_identity_variants SET equivalence is still recorded UNVERIFIED in the schema (status field at conclusion.equivalent_phrasing); out of scope here.",
        ],
        "next_falsifier": ("Re-measure %s: a sha256 other than %s voids the binding. At the pinned bytes the "
                           "verdict is falsified if any R06-R11 check is shown to misread the tail/whole-curve "
                           "distinction, or if the control (R18) is shown non-discriminating on the old snapshot %s."
                           % (TARGET, PIN, OLD_PIN)),
        "evidence_refs": [
            "%s#%s" % (SNAPSHOT, PIN[:12]),
            "%s#%s" % (TARGET, PIN[:12]),
            "%s#%s" % (CANON_F0, sha256_file(os.path.join(ROOT, CANON_F0))[:12]),
            "%s#%s" % (FROZEN, sha256_file(os.path.join(ROOT, FROZEN))[:12]),
            "%s#%s" % (OLD_SNAPSHOT, OLD_PIN[:12]),
            "artifacts/worker-078/f1_quantifier_adjudication/report.json#f512a5cb6c14",
        ],
    }
    return report


if __name__ == "__main__":
    rep = main()
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "report.json")
    with open(out, "w") as fh:
        json.dump(rep, fh, indent=1, sort_keys=False)
        fh.write("\n")
    print(json.dumps({"verdict": rep["verdict"], "counts": rep["counts"],
                      "binding": rep["binding"], "report": out}, indent=1))
