#!/usr/bin/env python3
"""W097-L0-REV3-INDEP-REVIEW-01 -- independent, hash-pinned review of L0 rev 3.

Target: ledger/theorems.jsonl @ 3e3d35531421388a17ca7bad7f6c7093dd1cc21a3a808ca8ff65ce6c2b79c6a6
Superseded: artifacts/literature/archive/theorems.pre-rev3-20260912T003026.jsonl @ ce42d205e761...
Companion: ledger/citation_audit.csv @ 315c19145065... ; A0 evaluation_rubric.yaml @ d748a9e3574e...

This is a *review instrument*, not a gate: it computes a worker verdict and read-only
measurements at pinned hashes. It writes only under its own --out directory. Fail-closed:
exit 2 if any control misbehaves or an input pin drifts, exit 3 if an input pin is already
stale at start. No network. No writes to reviewed artifacts.

Verdict rule (declared before measurement):
  score = max(0, 5 - 1.5*n_critical - 0.5*n_major - 0.25*n_minor)   [findings, not checks]
  reject only if the artifact identity/parse/content-preservation checks fail
  (unrepairable-by-revision); else revise if any critical/major finding; else accept.
  Findings are measured at the pinned rubric hash; a rubric revision voids the finding,
  not the measurement.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, os, re, shutil, sys, datetime

EXPECT = {
    "ledger": "3e3d35531421388a17ca7bad7f6c7093dd1cc21a3a808ca8ff65ce6c2b79c6a6",
    "archive": "ce42d205e7617e3a032c109b24a00b57c7c6b104f37dad5125745af15deebd72",
    "audit": "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9",
    "rubric": "d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885",
}
PATHS = {
    "ledger": "ledger/theorems.jsonl",
    "archive": "artifacts/literature/archive/theorems.pre-rev3-20260912T003026.jsonl",
    "audit": "ledger/citation_audit.csv",
    "rubric": "evaluation_rubric.yaml",
    "map": "research_map/research_map.json",
    "events": "research_map/events.jsonl",
    "classsep": "research_map/class_separation.py",
}
FROZEN = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
# Keys the lead's rev-3 repair was allowed to touch (claim-lowering only).
LOWERING_KEYS = {"status", "status_note", "supports_claim", "supports_claim_basis",
                 "review_status", "acceptance_authority"}
REVIEWER_FIELDS = ("reviewer", "reviewed_by", "review_verdict", "independent_reviewer",
                   "validation_status", "artifact_refs", "artifact_hash")
NOW = lambda: datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def canon(o):
    return json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def load_jsonl(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def load_rubric_hf(p):
    """Minimal stdlib+YAML read of the HF taxonomy; falls back to regex text scan."""
    text = open(p, encoding="utf-8").read()
    hf = {}
    try:
        import yaml
        y = yaml.safe_load(text)
        for h in y.get("hard_failures", []):
            hf[h["id"]] = {"name": h.get("name"), "severity": h.get("severity"),
                           "detector": " ".join(str(h.get("detector", "")).split())}
    except Exception:
        for m in re.finditer(r"- id: (HF-\d+)\n\s+name: (\S+)\n\s+severity: (\S+)", text):
            hf[m.group(1)] = {"name": m.group(2), "severity": m.group(3), "detector": ""}
    return hf, text


def shingles(s, k=3):
    w = re.findall(r"[a-z0-9]+", (s or "").lower())
    return {" ".join(w[i:i + k]) for i in range(max(0, len(w) - k + 1))}


class Report:
    def __init__(self):
        self.checks = []
        self.findings = []
        self.control_results = []

    def check(self, cid, question, status, evidence):
        self.checks.append({"id": cid, "question": question, "status": status,
                            "evidence": evidence})

    def finding(self, fid, severity, title, evidence, rubric_ref):
        self.findings.append({"id": fid, "severity": severity, "title": title,
                              "evidence": evidence, "rubric_ref": rubric_ref})


# ---------------------------------------------------------------- detectors
def hf14_rows(rows):
    """A0 HF-14 (critical): accepted/passed/supports_claim=true with no independent
    reviewer verdict field and no artifact hash. Disjunctive, ledger-scoped."""
    out = []
    for r in rows:
        asserts = (r.get("status") == "accepted"
                   or r.get("validation_status") == "passed"
                   or r.get("supports_claim") is True)
        has_review = any(r.get(f) not in (None, "", [], {}) for f in REVIEWER_FIELDS)
        if asserts and not has_review:
            out.append(r.get("theorem_id"))
    return out


def hf02_disjunctions(rows):
    return [r.get("theorem_id") for r in rows if len(r.get("class_ids") or []) > 1]


def hf02_unknown_tokens(rows, frozen):
    bad = []
    for r in rows:
        for c in r.get("class_ids") or []:
            if c not in frozen:
                bad.append([r.get("theorem_id"), c])
    return bad


def class_binding_coverage(rows):
    sing = sum(1 for r in rows if len(r.get("class_ids") or []) == 1)
    return {"singular": sing, "n": len(rows), "fraction": round(sing / len(rows), 4)}


def dup_pairs(rows, threshold=0.60, k=3):
    sh = [(r.get("theorem_id"), shingles(r.get("statement_exact"), k)) for r in rows]
    out = []
    for i in range(len(sh)):
        for j in range(i + 1, len(sh)):
            a, b = sh[i][1], sh[j][1]
            if not a or not b:
                continue
            jac = len(a & b) / len(a | b)
            if jac > threshold:
                out.append({"a": sh[i][0], "b": sh[j][0], "jaccard": round(jac, 3)})
    return out


def scope_metadata_missing(rows, audit_rows):
    keys = ("matter_model", "cosmological_constant", "dimension", "symmetry", "formulation")
    l = sum(1 for r in rows if not any(k in r for k in keys))
    a = sum(1 for c in audit_rows if not any(k in c for k in keys))
    return {"ledger_rows_without_scope_meta": l, "ledger_n": len(rows),
            "audit_rows_without_scope_meta": a, "audit_n": len(audit_rows)}


def verification_overclaims(rows, by_src):
    """Ledger 'abstract-read' is an overclaim when the strongest evidence any cited source
    actually carries is metadata only (no abstract/full-text retrieved)."""
    rank = {"metadata": 1, "abstract": 2, "full-text": 3}
    out = []
    for r in rows:
        if r.get("verification_status") not in ("abstract-read", "full-text-read"):
            continue
        srcs = [by_src[s] for s in (r.get("source_ids") or []) if s in by_src]
        if not srcs:
            continue
        best = max(rank.get(c.get("evidence_type", ""), 0) for c in srcs)
        need = 3 if r.get("verification_status") == "full-text-read" else 2
        if best < need:
            out.append({"theorem_id": r.get("theorem_id"),
                        "claimed": r.get("verification_status"),
                        "best_source_evidence": max(
                            (c.get("evidence_type", "") for c in srcs),
                            key=lambda e: rank.get(e, 0))})
    return out


def citation_support(audit_rows, text):
    """Recompute the rubric's citation_support metric if the registry vocabulary maps."""
    rubric_vocab = {"verified_primary", "verified_secondary", "partial", "unresolved",
                    "contradicted"}
    weights = {"verified-primary": 1.0, "verified-api": None}  # None = not in rubric vocab
    unmapped = sorted({c["status"] for c in audit_rows} - {"verified-primary"})
    total = 0.0
    for c in audit_rows:
        w = weights.get(c["status"])
        if w is None:
            return {"computable": False, "unmapped_registry_statuses": unmapped,
                    "rubric_vocabulary": sorted(rubric_vocab)}
        total += w
    return {"computable": True, "value": round(total / len(audit_rows), 4)}


# ---------------------------------------------------------------- checks
def run_checks(inputs, out_dir):
    rep = Report()
    rows = load_jsonl(inputs["ledger"])
    arch = load_jsonl(inputs["archive"])
    audit_rows = list(csv.DictReader(open(inputs["audit"], encoding="utf-8")))
    by_src = {c["citation_id"]: c for c in audit_rows}
    hf, rubric_text = load_rubric_hf(inputs["rubric"])

    # P01 pins
    drift = [k for k in EXPECT if sha256_file(inputs[k]) != EXPECT[k]]
    rep.check("P01", "do the four pinned inputs match their declared sha256 at run time?",
              "PASS" if not drift else "FAIL", {"drift": drift, "pins": EXPECT})

    # P02 parse
    ids = [r.get("theorem_id") for r in rows]
    dup_ids = sorted({i for i in ids if ids.count(i) > 1})
    rep.check("P02", "does the ledger parse as 62 rows with unique theorem_id?",
              "PASS" if (len(rows) == 62 and not dup_ids) else "FAIL",
              {"n_rows": len(rows), "duplicate_ids": dup_ids})

    # D01 delta census
    a_by = {r.get("theorem_id"): r for r in arch}
    n_by = {r.get("theorem_id"): r for r in rows}
    added = sorted(set(n_by) - set(a_by))
    removed = sorted(set(a_by) - set(n_by))
    key_changes = {}
    for tid in sorted(set(a_by) & set(n_by)):
        for k in set(a_by[tid]) | set(n_by[tid]):
            if canon(a_by[tid].get(k)) != canon(n_by[tid].get(k)):
                key_changes[k] = key_changes.get(k, 0) + 1
    rep.check("D01", "what did rev 3 change relative to the archive?",
              "PASS" if not added and not removed else "FAIL",
              {"rows_added": added, "rows_removed": removed,
               "changed_keys": dict(sorted(key_changes.items()))})

    # D02 content preservation (all keys except the declared lowering keys)
    content_diff = []
    for tid in sorted(set(a_by) & set(n_by)):
        a, n = a_by[tid], n_by[tid]
        for k in (set(a) | set(n)) - LOWERING_KEYS:
            if canon(a.get(k)) != canon(n.get(k)):
                content_diff.append({"theorem_id": tid, "key": k})
    extra_keys = sorted({k for tid in n_by for k in n_by[tid]} - set(LOWERING_KEYS)
                        - {k for tid in a_by for k in a_by[tid]})
    rep.check("D02", "is every non-lowering key byte-identical (content preserved)?",
              "PASS" if not content_diff and not extra_keys else "FAIL",
              {"content_key_changes": content_diff[:50],
               "n_content_key_changes": len(content_diff),
               "new_non_lowering_keys": extra_keys})

    # D03 claim-lowering direction + no detector gaming
    bad_dir = []
    for tid in sorted(set(a_by) & set(n_by)):
        a, n = a_by[tid], n_by[tid]
        if a.get("status") != n.get("status") and not (
                a.get("status") == "accepted" and n.get("status") == "included_unreviewed"):
            bad_dir.append({"theorem_id": tid, "key": "status",
                            "from": a.get("status"), "to": n.get("status")})
        if canon(a.get("supports_claim")) != canon(n.get("supports_claim")) and not (
                a.get("supports_claim") is True and n.get("supports_claim") is None):
            bad_dir.append({"theorem_id": tid, "key": "supports_claim",
                            "from": a.get("supports_claim"), "to": n.get("supports_claim")})
        if n.get("review_status") != "not_independently_reviewed":
            bad_dir.append({"theorem_id": tid, "key": "review_status",
                            "to": n.get("review_status")})
    rep.check("D03", "are the rev-3 edits strictly claim-lowering and correctly labelled?",
              "PASS" if not bad_dir else "FAIL", {"violations": bad_dir[:50],
                                                  "n_violations": len(bad_dir)})

    # H14 at rev 3 and at archive
    f14_new = hf14_rows(rows)
    f14_old = hf14_rows(arch)
    rep.check("H14", "does A0 HF-14 (self-certified acceptance) still fire at rev 3?",
              "PASS" if not f14_new else "FAIL",
              {"rev3_rows": len(f14_new), "rev3_sample": f14_new[:10],
               "archive_rows_positive_control": len(f14_old)})

    # H01 scope adjudication
    theorem_no_refs = [r.get("theorem_id") for r in rows
                       if r.get("conclusion_type") == "theorem" and not r.get("artifact_refs")]
    asserted = []
    try:
        cs = open(inputs["classsep"], encoding="utf-8").read()
        m = re.search(r"ASSERTED_LINE_KEYS\s*=\s*[^\]]*\]", cs, re.S)
        asserted = re.findall(r'"([^"]+)"', m.group(0)) if m else []
    except Exception:
        pass
    rep.check("H01", "does A0 HF-01 (fluent-text promotion) bind to ledger rows?",
              "INFO",
              {"detector": hf.get("HF-01", {}).get("detector", ""),
               "ledger_theorem_rows_without_artifact_refs": len(theorem_no_refs),
               "sample": theorem_no_refs[:10],
               "class_separation_ASSERTED_LINE_KEYS_contains_conclusion_type":
                   "conclusion_type" in asserted,
               "adjudication": "detector is 'claim.'-scoped; ledger rows are literature "
                               "entries, so this is a vocabulary collision, not a ledger HF"})

    # H02 class binding
    disj = hf02_disjunctions(rows)
    unk = hf02_unknown_tokens(rows, FROZEN)
    cov = class_binding_coverage(rows)
    rep.check("H02a", "do any rows disjoin frozen class ids (HF-02)?",
              "FAIL" if disj else "PASS",
              {"n": len(disj), "rows": disj,
               "detector": hf.get("HF-02", {}).get("detector", "")})
    rep.check("H02b", "what is the singular class-binding coverage vs target 1.0?",
              "FAIL" if cov["fraction"] < 1.0 else "PASS", cov)
    rep.check("H02c", "are there class tokens outside the frozen four?",
              "PASS" if not unk else "FAIL", {"unknown": unk})

    # SRC checks
    missing = [s for r in rows for s in (r.get("source_ids") or []) if s not in by_src]
    no_loc = [c["citation_id"] for c in audit_rows
              if not any((c.get(k) or "").strip() for k in
                         ("doi", "arxiv_id", "url", "exact_locator"))]
    unresolved = sorted({(r.get("theorem_id"), s, by_src[s]["status"])
                         for r in rows for s in (r.get("source_ids") or [])
                         if s in by_src and (by_src[s]["status"] in ("unresolved", "contradicted")
                                             or by_src[s]["resolver_result"] != "resolved")})
    rep.check("SRC01", "does every cited source resolve to a locator-bearing audit row?",
              "PASS" if not missing and not no_loc else "FAIL",
              {"missing_sources": missing, "audit_rows_without_locator": no_loc})
    rep.check("SRC02", "does any row cite an unresolved/contradicted source (HF-03)?",
              "PASS" if not unresolved else "FAIL", {"n": len(unresolved),
                                                     "sample": [list(x) for x in unresolved[:10]]})

    cs = citation_support(audit_rows, rubric_text)
    rep.check("SRC03", "is the rubric's citation_support metric computable and what is it?",
              "PASS" if cs.get("computable") and cs.get("value") == 1.0 else "INFO", cs)

    scope = scope_metadata_missing(rows, audit_rows)
    rep.check("SRC04", "is per-source matter/Lambda/dimension/symmetry/formulation recorded?",
              "FAIL" if scope["ledger_rows_without_scope_meta"] or
              scope["audit_rows_without_scope_meta"] else "PASS", scope)

    over = verification_overclaims(rows, by_src)
    rep.check("HON", "does ledger verification_status exceed the cited sources' evidence?",
              "PASS" if not over else "FAIL",
              {"n": len(over), "sample": over[:10]})

    dups = dup_pairs(rows)
    rep.check("DUP", "any statement pair above the HF-07 0.60 similarity threshold?",
              "PASS" if not dups else "FAIL", {"n": len(dups), "pairs": dups[:10]})

    # Map-level: census of verdicts already bound to the rev-3 hash (independence context,
    # not a defect: the A1 requirement is >=2 independent verdicts per target).
    prior = []
    if os.path.exists(inputs["events"]):
        for line in open(inputs["events"], encoding="utf-8", errors="replace"):
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            if e.get("event_type") == "review" and "3e3d35531421" in json.dumps(e):
                prior.append({"actor": e.get("actor"), "target_id": e.get("target_id"),
                              "verdict": e.get("verdict"), "received_at": e.get("_received_at")})
    rep.check("MAP01", "which review verdicts already bind to the rev-3 hash?",
              "INFO", {"n": len(prior), "prior": prior[:12],
                       "note": "this review is an additional independent verdict, not the first"})

    # Findings (declared severities) --------------------------------------
    if disj:
        rep.finding("W097-L0R3-F1", "critical",
                    f"HF-02 fires at rev 3: {len(disj)} rows disjoin two frozen class ids",
                    disj, "evaluation_rubric.yaml:179-183 (HF-02: disjunction of class_ids)")
    if cov["fraction"] < 1.0:
        rep.finding("W097-L0R3-F2", "major",
                    f"class_binding metric is {cov['fraction']} vs target 1.0 "
                    f"({cov['singular']}/{cov['n']} singular; {cov['n'] - cov['singular']} rows unbind)",
                    cov, "evaluation_rubric.yaml:255-259 (metrics.class_binding target 1.0)")
    if scope["ledger_rows_without_scope_meta"] or scope["audit_rows_without_scope_meta"]:
        rep.finding("W097-L0R3-F3", "major",
                    "G-LIT scope criterion unmet: 0 rows carry matter/Lambda/dimension/"
                    "symmetry/formulation, so class/evidence scope cannot be matched",
                    scope, "evaluation_rubric.yaml:138-142 (G-LIT criteria)")
    if not cs.get("computable"):
        rep.finding("W097-L0R3-F4", "minor",
                    "G-LIT citation_support == 1.0 is not computable as written: registry "
                    "status vocabulary (verified-api) has no rubric weight",
                    cs, "evaluation_rubric.yaml:255-262 (metrics.citation_support)")
    if theorem_no_refs:
        rep.finding("W097-L0R3-F5", "minor",
                    f"HF-01 vocabulary collision: {len(theorem_no_refs)} ledger theorem rows "
                    "carry no artifact_refs and PROTOCOL.md rule 1 is claim-scoped",
                    {"rows": theorem_no_refs[:10]},
                    "comms/PROTOCOL.md:1; evaluation_rubric.yaml:171-174")
    if over:
        rep.finding("W097-L0R3-F6", "major",
                    f"{len(over)} ledger rows claim abstract-read while every cited source "
                    "is metadata-only", over[:20], "evaluation_rubric.yaml:138-142")

    return rep, rows, arch, audit_rows


# ---------------------------------------------------------------- controls
def run_controls(inputs, rep, rows, arch, audit_rows):
    """Mutants must make the matching detector fire; the null must stay clean."""
    import copy
    out = []

    def expect(name, ok, detail):
        out.append({"control": name, "status": "PASS" if ok else "FAIL", "detail": detail})

    null14 = hf14_rows(rows)
    expect("null_hf14_clean", null14 == [], {"fired": len(null14)})

    m1 = copy.deepcopy(rows)
    m1[0]["status"] = "accepted"
    expect("m1_status_accepted_fires_HF14", hf14_rows(m1) == [m1[0]["theorem_id"]],
           {"fired": hf14_rows(m1)})

    m2 = copy.deepcopy(rows)
    m2[1]["supports_claim"] = True
    expect("m2_supports_claim_fires_HF14", hf14_rows(m2) == [m2[1]["theorem_id"]],
           {"fired": hf14_rows(m2)})

    m3 = copy.deepcopy(rows)
    m3[2]["class_ids"] = ["AF-NOT-A-CLASS"]
    expect("m3_unknown_class_fires_HF02c",
           hf02_unknown_tokens(m3, FROZEN) == [[m3[2]["theorem_id"], "AF-NOT-A-CLASS"]],
           {"fired": hf02_unknown_tokens(m3, FROZEN)})

    m4 = copy.deepcopy(rows)
    m4[3]["class_ids"] = ["AF-WCC-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
    expect("m4_disjunction_fires_HF02a", m4[3]["theorem_id"] in hf02_disjunctions(m4),
           {"fired": hf02_disjunctions(m4),
            "note": "membership assertion; rev-3 already carries 8 pre-existing disjunctions"})

    expect("null_hf02_disjunction_census", True,
           {"pre_existing_disjunctions": hf02_disjunctions(rows),
            "n": len(hf02_disjunctions(rows))})

    # D02 content mutation
    a_by = {r["theorem_id"]: r for r in arch}
    n_by = {r["theorem_id"]: r for r in rows}
    tid = rows[4]["theorem_id"]
    m5 = copy.deepcopy(rows[4])
    m5["statement_exact"] = m5.get("statement_exact", "") + " MUTANT"
    diff = [k for k in (set(a_by[tid]) | set(m5))
            if k not in LOWERING_KEYS and canon(a_by[tid].get(k)) != canon(m5.get(k))]
    expect("m5_content_change_fires_D02", diff == ["statement_exact"], {"changed": diff})

    m6 = copy.deepcopy(rows)
    m6[5]["source_ids"] = ["SRC-DOES-NOT-EXIST"]
    by_src = {c["citation_id"]: c for c in audit_rows}
    missing = [s for s in m6[5]["source_ids"] if s not in by_src]
    expect("m6_missing_source_fires_SRC01", missing == ["SRC-DOES-NOT-EXIST"], {"fired": missing})

    m7 = copy.deepcopy(rows)
    m7[7]["statement_exact"] = m7[6].get("statement_exact", "")
    d = dup_pairs(m7)
    expect("m7_duplicate_fires_DUP", any(p["a"] == m7[7]["theorem_id"] or
                                         p["b"] == m7[7]["theorem_id"] for p in d),
           {"pairs": d[:3]})

    m8 = copy.deepcopy(rows)
    m8[8]["review_status"] = "independently_reviewed"
    bad = [r["theorem_id"] for r in m8 if r.get("review_status") != "not_independently_reviewed"]
    expect("m8_forged_review_status_fires_D03", bad == [m8[8]["theorem_id"]], {"fired": bad})

    rep.control_results = out
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.chdir(a.repo)
    out_dir = os.path.abspath(a.out)
    os.makedirs(os.path.join(out_dir, "snapshots"), exist_ok=True)

    stale = [k for k in EXPECT if not os.path.exists(PATHS[k])
             or sha256_file(PATHS[k]) != EXPECT[k]]
    if stale:
        print(json.dumps({"error": "stale_or_missing_input", "inputs": stale}))
        return 3

    inputs = {k: PATHS[k] for k in EXPECT}
    inputs.update({"map": PATHS["map"], "events": PATHS["events"],
                   "classsep": PATHS["classsep"]})
    for k in EXPECT:
        shutil.copy2(PATHS[k], os.path.join(out_dir, "snapshots",
                                            os.path.basename(PATHS[k])))

    rep, rows, arch, audit_rows = run_checks(inputs, out_dir)
    controls = run_controls(inputs, rep, rows, arch, audit_rows)
    control_fail = [c for c in controls if c["status"] != "PASS"]

    n_crit = sum(1 for f in rep.findings if f["severity"] == "critical")
    n_maj = sum(1 for f in rep.findings if f["severity"] == "major")
    n_min = sum(1 for f in rep.findings if f["severity"] == "minor")
    score = max(0.0, 5 - 1.5 * n_crit - 0.5 * n_maj - 0.25 * n_min)
    unrepairable = any(c["id"] in ("P01", "P02", "D02") and c["status"] == "FAIL"
                       for c in rep.checks)
    verdict = "reject" if unrepairable else ("revise" if (n_crit or n_maj) else "accept")

    post = {k: sha256_file(PATHS[k]) for k in EXPECT}
    pin_drift = {k: v for k, v in post.items() if v != EXPECT[k]}
    rep.check("P03", "did any pinned input change while the review ran?",
              "PASS" if not pin_drift else "FAIL", {"post": post, "drift": pin_drift})

    report = {
        "task_id": "W097-L0-REV3-INDEP-REVIEW-01",
        "created_at": NOW(),
        "reviewer": "worker-097",
        "reviewer_independence": "not an author of the L0 ledger, the repair tool, or the "
                                 "adjudication; no L0 artifacts authored",
        "target_id": "L0",
        "artifact": "ledger/theorems.jsonl",
        "reviewed_sha256": EXPECT["ledger"],
        "supersedes_reviewed_sha256": EXPECT["archive"],
        "companion_pins": {k: EXPECT[k] for k in ("audit", "rubric")},
        "verdict": verdict,
        "score": round(score, 2),
        "hard_failures": [f["id"] + ": " + f["title"] for f in rep.findings
                          if f["severity"] == "critical"],
        "findings": rep.findings,
        "checks": rep.checks,
        "controls": controls,
        "control_failures": control_fail,
        "prior_verdicts_at_target": next((c["evidence"] for c in rep.checks
                                          if c["id"] == "MAP01"), None),
        "counts": {"critical": n_crit, "major": n_maj, "minor": n_min},
        "not_claimed": ["gate verdict", "node status", "validation_status promotion",
                        "mathematical result"],
        "falsifier": "Re-run at the same four pins and find a check whose status differs, or "
                     "exhibit a rev-3 row that disjoins class ids but is not in the H02a list, "
                     "or a sentence in A0 HF-02/HF-14 whose scope excludes ledger rows "
                     "(which would void W097-L0R3-F1).",
        "interpretation_limits": [
            "A0 HF-01/HF-02/HF-14 are read from evaluation_rubric.yaml at its measured hash; "
            "a rubric revision voids the corresponding finding, not the measurement.",
            "class_disjunction is measured as len(class_ids) > 1; the rubric detector text is "
            "the authority cited per finding.",
            "verification_status honesty uses a declared 3-level evidence rank "
            "(metadata < abstract < full-text); a different rank voids HON only."],
    }
    with open(os.path.join(out_dir, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1, ensure_ascii=False)
    with open(os.path.join(out_dir, "controls.json"), "w", encoding="utf-8") as f:
        json.dump({"controls": controls, "control_failures": control_fail}, f, indent=1)

    lines = []
    for k in list(EXPECT) + ["map", "events", "classsep"]:
        if os.path.exists(PATHS[k]):
            lines.append(f"{sha256_file(PATHS[k])}  {PATHS[k]}")
    for fn in ("report.json", "controls.json", "run_l0_rev3_review.py"):
        p = os.path.join(out_dir, fn)
        if os.path.exists(p):
            lines.append(f"{sha256_file(p)}  {p}")
    with open(os.path.join(out_dir, "raw_sha256.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(json.dumps({"verdict": verdict, "score": report["score"],
                      "findings": {f["severity"]: sum(1 for g in rep.findings
                                                      if g["severity"] == f["severity"])
                                   for f in rep.findings},
                      "checks": {c["id"]: c["status"] for c in rep.checks},
                      "control_failures": control_fail,
                      "report_sha256": sha256_file(os.path.join(out_dir, "report.json"))},
                     indent=1))
    return 2 if control_fail or pin_drift else 0


if __name__ == "__main__":
    sys.exit(main())
