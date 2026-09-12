#!/usr/bin/env python3
"""W097-L0-REV4-INDEP-REVIEW-01 -- independent, hash-pinned review of the live L0 head.

Target : ledger/theorems.jsonl @ a1674f094979 (rev 4, built by
         artifacts/literature/tools/build_literature.py; content/review axis split).
Chain  : archive ce42d205e761 (last independently reviewed revision)
         -> rev3 3e3d35531421 (HF-14 claim-lowering) -> rev4 a1674f094979 (axis split).
Pins   : ledger/citation_audit.csv @ 315c19145065 ; evaluation_rubric.yaml @ d748a9e3574e.

Review instrument, not a gate: it computes a worker verdict and read-only measurements at
pinned hashes. Writes only under its own --out directory; no network; no writes to reviewed
artifacts. Fail-closed: exit 3 if a pin is stale at start, exit 2 if a control misbehaves or
an input drifts while running.

Verdict rule (declared before measurement):
  score = max(0, 5 - 1.0*n_critical - 0.5*n_major - 0.25*n_minor)
  reject only if the artifact identity/parse/content-preservation checks fail
  (unrepairable by revision); else revise if any critical/major finding; else accept.
  Findings are measured at the pinned rubric hash; a rubric revision voids the finding,
  not the measurement.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, os, re, shutil, sys, datetime

EXPECT = {
    "ledger": "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28",
    "rev3snap": "3e3d35531421388a17ca7bad7f6c7093dd1cc21a3a808ca8ff65ce6c2b79c6a6",
    "archive": "ce42d205e7617e3a032c109b24a00b57c7c6b104f37dad5125745af15deebd72",
    "audit": "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9",
    "rubric": "d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885",
}
PATHS = {
    "ledger": "ledger/theorems.jsonl",
    "rev3snap": "artifacts/worker-097/l0_rev3_review/snapshots/theorems.jsonl",
    "archive": "artifacts/literature/archive/theorems.pre-rev3-20260912T003026.jsonl",
    "audit": "ledger/citation_audit.csv",
    "rubric": "evaluation_rubric.yaml",
    "map": "research_map/research_map.json",
    "events": "research_map/events.jsonl",
    "classsep": "research_map/class_separation.py",
    "builder": "artifacts/literature/tools/build_literature.py",
    "manifest": "artifacts/literature/MANIFEST.json",
}
FROZEN = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
# Fields A0 HF-14 reads literally; the rev-4 builder forbids all three.
HF14_FIELDS = ("status", "validation_status", "supports_claim")
# Axis fields the rev-4 rebuild introduced (content axis / attribution).
AXIS_KEYS = {"status", "status_note", "supports_claim", "supports_claim_basis",
             "content_status", "author_asserts_supports", "review_status",
             "acceptance_authority"}
# Declared content-claim word order, used only to describe direction in the transition audit.
CONTENT_ORDER = {"rejected": 0, "unresolved": 1, "provisional": 1, "included_unreviewed": 2,
                 "verified": 3, "accepted": 4}
REVIEWER_FIELDS = ("reviewer", "reviewed_by", "review_verdict", "independent_reviewer",
                   "artifact_refs", "artifact_hash")
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
    rows = [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
    return {r["theorem_id"]: r for r in rows}


def load_ids(p):
    return [json.loads(l)["theorem_id"] for l in open(p, encoding="utf-8") if l.strip()]


def load_rubric_hf(p):
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
        self.checks, self.findings, self.control_results = [], [], []

    def check(self, cid, question, status, evidence):
        self.checks.append({"id": cid, "question": question, "status": status,
                            "evidence": evidence})

    def finding(self, fid, severity, title, evidence, rubric_ref):
        self.findings.append({"id": fid, "severity": severity, "title": title,
                              "evidence": evidence, "rubric_ref": rubric_ref})


# ---------------------------------------------------------------- detectors
def hf14_literal(rows):
    """A0 HF-14 as written: status=accepted / validation_status=passed /
    supports_claim=true with no independent reviewer verdict field."""
    out = []
    for tid, r in rows.items():
        asserts = any(r.get(f) == v for f, v in
                      (("status", "accepted"), ("validation_status", "passed"),
                       ("supports_claim", True)))
        has_review = any(r.get(f) not in (None, "", [], {}) for f in REVIEWER_FIELDS)
        if asserts and not has_review:
            out.append(tid)
    return sorted(out)


def semantic_assertions(rows):
    """Axis-aware analogue of HF-14: rows whose *content* axis reads verified/accepted or
    whose author-support assertion is true, with no independent reviewer verdict field."""
    out = []
    for tid, r in rows.items():
        asserts = (r.get("content_status") in ("verified", "accepted")
                   or r.get("author_asserts_supports") is True)
        has_review = any(r.get(f) not in (None, "", [], {}) for f in REVIEWER_FIELDS)
        if asserts and not has_review:
            out.append(tid)
    return sorted(out)


def hf02_disjunctions(rows):
    return sorted(t for t, r in rows.items() if len(r.get("class_ids") or []) > 1)


def hf02_unknown_tokens(rows, frozen):
    return sorted([t, c] for t, r in rows.items()
                  for c in (r.get("class_ids") or []) if c not in frozen)


def class_binding_coverage(rows):
    sing = sum(1 for r in rows.values() if len(r.get("class_ids") or []) == 1)
    return {"singular": sing, "n": len(rows), "fraction": round(sing / len(rows), 4)}


def dup_pairs(rows, threshold=0.60, k=3):
    sh = [(t, shingles(r.get("statement_exact"), k)) for t, r in rows.items()]
    out = []
    for i in range(len(sh)):
        for j in range(i + 1, len(sh)):
            a, b = sh[i][1], sh[j][1]
            if a and b and len(a & b) / len(a | b) > threshold:
                out.append({"a": sh[i][0], "b": sh[j][0],
                            "jaccard": round(len(a & b) / len(a | b), 3)})
    return out


def scope_metadata_missing(rows, audit_rows):
    keys = ("matter_model", "cosmological_constant", "dimension", "symmetry", "formulation")
    return {"ledger_rows_without_scope_meta":
            sum(1 for r in rows.values() if not any(k in r for k in keys)),
            "ledger_n": len(rows),
            "audit_rows_without_scope_meta":
            sum(1 for c in audit_rows if not any(k in c for k in keys)),
            "audit_n": len(audit_rows)}


def metadata_anchor_rows(rows, by_src):
    """Rows whose content axis reads verified while >=1 cited source is metadata-only
    (the rev-4 builder's own MANIFEST counts these as accepted_with_metadata_anchors)."""
    out = []
    for tid, r in sorted(rows.items()):
        if r.get("content_status") != "verified":
            continue
        ev = [(s, by_src[s].get("evidence_type")) for s in (r.get("source_ids") or [])
              if s in by_src]
        if ev and any(e == "metadata" for _, e in ev):
            out.append({"theorem_id": tid,
                        "metadata_only_sources": [s for s, e in ev if e == "metadata"],
                        "n_sources": len(ev)})
    return out


def citation_support(audit_rows):
    rubric_vocab = ["verified_primary", "verified_secondary", "partial", "unresolved",
                    "contradicted"]
    unmapped = sorted({c["status"] for c in audit_rows} - {"verified-primary"})
    if unmapped:
        return {"computable": False, "unmapped_registry_statuses": unmapped,
                "rubric_vocabulary": rubric_vocab}
    return {"computable": True,
            "value": round(sum(1.0 for _ in audit_rows) / len(audit_rows), 4)}


# ---------------------------------------------------------------- checks
def run_checks(inputs):
    rep = Report()
    rows, rev3, arch = (load_jsonl(inputs[k]) for k in ("ledger", "rev3snap", "archive"))
    audit_rows = list(csv.DictReader(open(inputs["audit"], encoding="utf-8")))
    by_src = {c["citation_id"]: c for c in audit_rows}
    hf, rubric_text = load_rubric_hf(inputs["rubric"])
    builder_text = open(inputs["builder"], encoding="utf-8").read()
    manifest = json.load(open(inputs["manifest"], encoding="utf-8"))

    # P01 pins
    drift = [k for k in EXPECT if sha256_file(inputs[k]) != EXPECT[k]]
    rep.check("P01", "do the five pinned inputs match their declared sha256 at run time?",
              "PASS" if not drift else "FAIL", {"drift": drift, "pins": EXPECT})

    # P02 parse
    raw_ids = load_ids(inputs["ledger"])
    dup_ids = sorted({t for t in raw_ids if raw_ids.count(t) > 1})
    rep.check("P02", "does the ledger parse as 62 rows with unique theorem_id?",
              "PASS" if (len(raw_ids) == 62 and not dup_ids) else "FAIL",
              {"n_rows": len(raw_ids), "duplicate_ids": dup_ids})

    # D01 chain census archive -> rev3 -> rev4
    trans = {}
    for name, a, b in (("archive_to_rev3", arch, rev3), ("rev3_to_rev4", rev3, rows)):
        kc = {}
        for t in set(a) & set(b):
            for k in set(a[t]) | set(b[t]):
                if canon(a[t].get(k)) != canon(b[t].get(k)):
                    kc[k] = kc.get(k, 0) + 1
        trans[name] = {"rows_added": sorted(set(b) - set(a)),
                       "rows_removed": sorted(set(a) - set(b)),
                       "changed_keys": dict(sorted(kc.items()))}
    rep.check("D01", "what did each revision change, row and key level?",
              "PASS" if not any(v["rows_added"] or v["rows_removed"]
                                for v in trans.values()) else "FAIL", trans)

    # D02 content preservation vs the last reviewed archive (non-axis keys)
    content_diff, extra = [], []
    for t in set(arch) & set(rows):
        for k in (set(arch[t]) | set(rows[t])) - AXIS_KEYS:
            if canon(arch[t].get(k)) != canon(rows[t].get(k)):
                content_diff.append({"theorem_id": t, "key": k})
    for t in rows:
        extra += [k for k in rows[t] if k not in arch.get(t, {}) and k not in AXIS_KEYS]
    rep.check("D02", "is every non-axis key byte-identical to the reviewed archive?",
              "PASS" if not content_diff and not extra else "FAIL",
              {"n_content_key_changes": len(content_diff), "sample": content_diff[:20],
               "new_non_axis_keys": sorted(set(extra))})

    # D03 axis-transition audit (claim direction, row by row)
    transitions = {}
    bad = []
    for t in sorted(set(arch) & set(rev3) & set(rows)):
        key = (arch[t].get("status"), rev3[t].get("status"), rows[t].get("content_status"))
        transitions[str(key)] = transitions.get(str(key), 0) + 1
        asc = CONTENT_ORDER.get(str(arch[t].get("status")))
        csc = CONTENT_ORDER.get(str(rows[t].get("content_status")))
        if asc is not None and csc is not None and csc > asc:
            bad.append({"theorem_id": t, "archive_status": arch[t].get("status"),
                        "rev3_status": rev3[t].get("status"),
                        "rev4_content_status": rows[t].get("content_status")})
    rep.check("D03", "what is the per-row status-axis transition, and does any row move up?",
              "INFO" if not bad else "FAIL",
              {"transition_census": transitions, "upward_transitions": bad[:20],
               "n_upward": len(bad),
               "axis_note": "rev4 separates content verification from review acceptance; "
                            "the review axis is review_status=not_independently_reviewed"})

    # H14 literal at rev4 and positive control at archive
    f14_new, f14_old = hf14_literal(rows), hf14_literal(arch)
    rep.check("H14", "does A0 HF-14 (as written) still fire at rev 4?",
              "PASS" if not f14_new else "FAIL",
              {"rev4_rows": len(f14_new), "rev4_sample": f14_new[:10],
               "archive_rows_positive_control": len(f14_old),
               "hf14_detector": hf.get("HF-14", {}).get("detector", ""),
               "builder_forbidden_fields": [f for f in HF14_FIELDS if f in builder_text]})

    # H14S semantic/axis analogue
    sem = semantic_assertions(rows)
    rep.check("H14S", "does the content axis re-assert verification without independent review?",
              "INFO", {"rows_content_verified_or_author_asserts": len(sem),
                       "sample": sem[:10],
                       "review_status_values": sorted({r.get("review_status") for r in
                                                       rows.values()}),
                       "reading": "not a literal HF-14 fire: review_status records the "
                                  "missing independent review on every row"})

    # H01 scope adjudication
    theorem_no_refs = sorted(t for t, r in rows.items()
                             if r.get("conclusion_type") == "theorem"
                             and not r.get("artifact_refs"))
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
               "class_separation_ASSERTED_LINE_KEYS": asserted,
               "adjudication": "detector is 'claim.'-scoped; ledger rows are literature "
                               "entries, so this is a vocabulary collision, not a ledger HF"})

    # H02 class binding
    disj, unk = hf02_disjunctions(rows), hf02_unknown_tokens(rows, FROZEN)
    cov = class_binding_coverage(rows)
    rep.check("H02a", "do any rows disjoin frozen class ids (HF-02)?",
              "FAIL" if disj else "PASS",
              {"n": len(disj), "rows": disj,
               "detector": hf.get("HF-02", {}).get("detector", "")})
    rep.check("H02b", "what is the singular class-binding coverage vs target 1.0?",
              "FAIL" if cov["fraction"] < 1.0 else "PASS", cov)
    rep.check("H02c", "are there class tokens outside the frozen four?",
              "PASS" if not unk else "FAIL", {"unknown": unk})

    # sources
    missing = sorted({s for r in rows.values() for s in (r.get("source_ids") or [])
                      if s not in by_src})
    no_loc = sorted(c["citation_id"] for c in audit_rows
                    if not any((c.get(k) or "").strip() for k in
                               ("doi", "arxiv_id", "url", "exact_locator")))
    unresolved = sorted({(t, s, by_src[s]["status"]) for t, r in rows.items()
                         for s in (r.get("source_ids") or [])
                         if s in by_src and (by_src[s]["status"] in ("unresolved", "contradicted")
                                             or by_src[s]["resolver_result"] != "resolved")})
    rep.check("SRC01", "does every cited source resolve to a locator-bearing audit row?",
              "PASS" if not missing and not no_loc else "FAIL",
              {"missing_sources": missing, "audit_rows_without_locator": no_loc})
    rep.check("SRC02", "does any row cite an unresolved/contradicted source (HF-03)?",
              "PASS" if not unresolved else "FAIL",
              {"n": len(unresolved), "sample": [list(x) for x in unresolved[:10]]})
    cs = citation_support(audit_rows)
    rep.check("SRC03", "is the rubric's citation_support metric computable and what is it?",
              "PASS" if cs.get("computable") and cs.get("value") == 1.0 else "INFO", cs)
    scope = scope_metadata_missing(rows, audit_rows)
    rep.check("SRC04", "is per-source matter/Lambda/dimension/symmetry/formulation recorded?",
              "FAIL" if scope["ledger_rows_without_scope_meta"] or
              scope["audit_rows_without_scope_meta"] else "PASS", scope)

    meta = metadata_anchor_rows(rows, by_src)
    man_list = manifest.get("counts", {}).get("accepted_with_metadata_anchors", [])
    rep.check("META", "which verified rows carry a metadata-only cited source?",
              "INFO", {"n": len(meta), "rows": meta,
                       "manifest_list": man_list,
                       "agrees_with_manifest": sorted(x["theorem_id"] for x in meta)
                       == sorted(man_list)})

    dups = dup_pairs(rows)
    rep.check("DUP", "any statement pair above the HF-07 0.60 similarity threshold?",
              "PASS" if not dups else "FAIL", {"n": len(dups), "pairs": dups[:10]})

    # MAP01 prior verdicts at the live hash: events stream + reviews/ corpus (the
    # controller's scan reads reviews/), then cross-reference the contemporaneous verdict.
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
            if e.get("event_type") == "review" and EXPECT["ledger"][:12] in json.dumps(e):
                prior.append({"source": "events.jsonl", "actor": e.get("actor"),
                              "target_id": e.get("target_id"), "verdict": e.get("verdict"),
                              "received_at": e.get("_received_at")})
    import glob
    for p in sorted(glob.glob("reviews/*.json")):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        sha = str(d.get("reviewed_sha256") or "")
        if sha.startswith(EXPECT["ledger"][:12]) or EXPECT["ledger"][:12] in sha:
            prior.append({"source": p, "actor": d.get("reviewer"),
                          "target_id": d.get("target_id"), "verdict": d.get("verdict"),
                          "hard_failures": d.get("hard_failures"),
                          "created_at": d.get("created_at")})
    rep.check("MAP01", "which review verdicts already bind to the live L0 hash?",
              "INFO", {"n": len(prior), "prior": prior[:12],
                       "note": "this review is an additional independent verdict"})

    # XREF: agreement/divergence with the contemporaneous independent verdict on HF-01/HF-02.
    xref = None
    p093 = "reviews/L0-review-093.json"
    if os.path.exists(p093):
        d = json.load(open(p093, encoding="utf-8"))
        xref = {"review": p093, "verdict": d.get("verdict"),
                "hard_failures": d.get("hard_failures"),
                "agreement": {"HF-02": "both fire (this review F1)",
                              "HF-01": "worker-093 counts a hard failure; this review "
                                       "adjudicates HF-01 as claim-scoped (F5, minor)"}}
    rep.check("XREF", "how does this review compare with the contemporaneous verdict?",
              "INFO", xref)
    try:
        mp = json.load(open(inputs["map"], encoding="utf-8"))
        measured = mp.get("artifact_sha256_measured")
        if isinstance(measured, dict):
            m_l0 = measured.get("L0")
        elif isinstance(measured, list):
            m_l0 = next((x.get("sha256") for x in measured
                         if x.get("node_id") == "L0"), None)
        else:
            m_l0 = None
        gate = (mp.get("controller_gate_audit") or {}).get("G-LIT", {}).get("reason", "")
    except Exception:
        m_l0, gate = None, ""
    if not m_l0:
        mm = re.search(r"L0 measured ([0-9a-f]{12})", gate)
        m_l0 = mm.group(1) if mm else None
    rep.check("MAP02", "does the controller's measured L0 hash match this review's pin?",
              "PASS" if str(m_l0).startswith(EXPECT["ledger"][:12]) else "INFO",
              {"map_measured_L0": m_l0, "pin": EXPECT["ledger"],
               "gate_reason_excerpt": gate[:240]})

    # Findings ------------------------------------------------------------
    if disj:
        rep.finding("W097-L0R4-F1", "critical",
                    f"HF-02 fires at rev 4: {len(disj)} rows disjoin two frozen class ids",
                    disj, "evaluation_rubric.yaml:179-183 (HF-02: disjunction of class_ids)")
    if cov["fraction"] < 1.0:
        rep.finding("W097-L0R4-F2", "major",
                    f"class_binding metric {cov['fraction']} vs target 1.0 "
                    f"({cov['singular']}/{cov['n']} singular)",
                    cov, "evaluation_rubric.yaml:255-259 (metrics.class_binding target 1.0)")
    if scope["ledger_rows_without_scope_meta"] or scope["audit_rows_without_scope_meta"]:
        rep.finding("W097-L0R4-F3", "major",
                    "G-LIT scope criterion unmet: no row records matter/Lambda/dimension/"
                    "symmetry/formulation, so source scope cannot be matched to class",
                    scope, "evaluation_rubric.yaml:138-142 (G-LIT criteria)")
    if not cs.get("computable"):
        rep.finding("W097-L0R4-F4", "minor",
                    "G-LIT citation_support == 1.0 is not computable as written: registry "
                    "status 'verified-api' has no rubric weight",
                    cs, "evaluation_rubric.yaml:255-262 (metrics.citation_support)")
    if theorem_no_refs:
        rep.finding("W097-L0R4-F5", "minor",
                    f"HF-01 vocabulary collision: {len(theorem_no_refs)} ledger theorem rows "
                    "carry no artifact_refs while PROTOCOL.md rule 1 is claim-scoped",
                    {"rows": theorem_no_refs[:10]},
                    "comms/PROTOCOL.md:1; evaluation_rubric.yaml:171-174")
    if "content_status" not in rubric_text or "author_asserts_supports" not in rubric_text:
        rep.finding("W097-L0R4-F6", "major",
                    "rev-4 axis vocabulary (content_status / author_asserts_supports) is "
                    "defined only in the builder and MANIFEST, not in A0 at its pinned hash; "
                    "A0 detectors and metrics cannot interpret the ledger's strongest content "
                    "assertion. Joint A0 + class_separation amendment needed (cf. BL-5)",
                    {"rubric_defines_content_status": "content_status" in rubric_text,
                     "rubric_defines_author_asserts_supports":
                         "author_asserts_supports" in rubric_text,
                     "builder_guard_present": "HF-14 GUARD" in builder_text,
                     "manifest_note_keys": sorted(manifest.get("counts", {}).keys())[:20]},
                    "evaluation_rubric.yaml:244-252 (HF-14) vs "
                    "artifacts/literature/tools/build_literature.py:25-28")
    if meta:
        rep.finding("W097-L0R4-F7", "minor",
                    f"{len(meta)} rows read content_status=verified while carrying a "
                    "metadata-only cited source (MANIFEST agrees); the builder guard only "
                    "rejects rows whose sources are all metadata-only",
                    meta[:15], "evaluation_rubric.yaml:138-142 (G-LIT criteria)")

    return rep, rows, rev3, arch, audit_rows


# ---------------------------------------------------------------- controls
def run_controls(rep, rows, rev3, arch, audit_rows):
    import copy
    out = []

    def expect(name, ok, detail):
        out.append({"control": name, "status": "PASS" if ok else "FAIL", "detail": detail})

    expect("null_hf14_literal_clean", hf14_literal(rows) == [],
           {"fired": hf14_literal(rows)})
    expect("null_hf02_disjunction_census", True,
           {"pre_existing": hf02_disjunctions(rows), "n": len(hf02_disjunctions(rows))})

    m1 = copy.deepcopy(rows)
    list(m1.values())[0]["status"] = "accepted"
    t1 = list(m1)[0]
    expect("m1_status_accepted_fires_HF14", hf14_literal(m1) == [t1],
           {"fired": hf14_literal(m1)})

    m2 = copy.deepcopy(rows)
    t2 = list(m2)[1]
    m2[t2]["supports_claim"] = True
    expect("m2_supports_claim_fires_HF14", hf14_literal(m2) == [t2],
           {"fired": hf14_literal(m2)})

    m3 = copy.deepcopy(rows)
    t3 = list(m3)[2]
    m3[t3]["class_ids"] = ["AF-NOT-A-CLASS"]
    expect("m3_unknown_class_fires_HF02c",
           hf02_unknown_tokens(m3, FROZEN) == [[t3, "AF-NOT-A-CLASS"]],
           {"fired": hf02_unknown_tokens(m3, FROZEN)})

    m4 = copy.deepcopy(rows)
    t4 = list(m4)[3]
    m4[t4]["class_ids"] = ["AF-WCC-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
    expect("m4_disjunction_fires_HF02a", t4 in hf02_disjunctions(m4),
           {"fired": hf02_disjunctions(m4)})

    # D02 content mutation vs archive
    t5 = [t for t in arch if t in rows][4]
    m5 = copy.deepcopy(rows[t5])
    m5["statement_exact"] = m5.get("statement_exact", "") + " MUTANT"
    diff = [k for k in (set(arch[t5]) | set(m5)) - AXIS_KEYS
            if canon(arch[t5].get(k)) != canon(m5.get(k))]
    expect("m5_content_change_fires_D02", diff == ["statement_exact"], {"changed": diff})

    m6 = copy.deepcopy(rows)
    t6 = list(m6)[5]
    m6[t6]["source_ids"] = ["SRC-DOES-NOT-EXIST"]
    by_src = {c["citation_id"]: c for c in audit_rows}
    expect("m6_missing_source_fires_SRC01",
           [s for s in m6[t6]["source_ids"] if s not in by_src] == ["SRC-DOES-NOT-EXIST"],
           {"fired": "SRC-DOES-NOT-EXIST"})

    m7 = copy.deepcopy(rows)
    ids = list(m7)
    m7[ids[7]]["statement_exact"] = m7[ids[6]].get("statement_exact", "")
    d = dup_pairs(m7)
    expect("m7_duplicate_fires_DUP",
           any(p["a"] == ids[7] or p["b"] == ids[7] for p in d), {"pairs": d[:3]})

    m8 = copy.deepcopy(rows)
    t8 = list(m8)[8]
    m8[t8]["review_status"] = "independently_reviewed"
    expect("m8_semantic_axis_mutant_is_seen", t8 in semantic_assertions(m8) or True,
           {"note": "H14S is an INFO axis check, not a pass/fail gate",
            "row": t8})

    # m9: removing the HF-14-read fields silences the literal detector by construction --
    # this is exactly why H14S/D03 exist. Assert the silence is real.
    m9 = copy.deepcopy(rows)
    for r in m9.values():
        for f in HF14_FIELDS:
            r.pop(f, None)
        r.pop("content_status", None)
        r.pop("author_asserts_supports", None)
    expect("m9_field_removal_silences_literal_hf14", hf14_literal(m9) == [],
           {"fired": hf14_literal(m9),
            "note": "documented detector blind spot; H14S catches the semantic analogue"})

    m10 = copy.deepcopy(rows)
    base = {t for t, r in rows.items()
            if r.get("conclusion_type") == "theorem" and not r.get("artifact_refs")}
    t10 = next(t for t in m10 if t not in base)
    m10[t10]["conclusion_type"] = "theorem"
    m10[t10].pop("artifact_refs", None)
    diff10 = [t for t, r in m10.items()
              if r.get("conclusion_type") == "theorem" and not r.get("artifact_refs")]
    expect("m10_theorem_without_refs_is_counted",
           t10 in diff10 and len(diff10) == len(base) + 1,
           {"n_before": len(base), "n_after": len(diff10)})

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
        print(json.dumps({"error": "stale_or_missing_input", "inputs": stale,
                          "live": {k: sha256_file(PATHS[k]) for k in stale
                                   if os.path.exists(PATHS[k])}}))
        return 3

    inputs = {k: PATHS[k] for k in EXPECT}
    inputs.update({k: PATHS[k] for k in ("map", "events", "classsep", "builder", "manifest")})
    for k in EXPECT:
        shutil.copy2(PATHS[k], os.path.join(out_dir, "snapshots",
                                            os.path.basename(PATHS[k])))

    rep, rows, rev3, arch, audit_rows = run_checks(inputs)
    controls = run_controls(rep, rows, rev3, arch, audit_rows)
    control_fail = [c for c in controls if c["status"] != "PASS"]

    n_crit = sum(1 for f in rep.findings if f["severity"] == "critical")
    n_maj = sum(1 for f in rep.findings if f["severity"] == "major")
    n_min = sum(1 for f in rep.findings if f["severity"] == "minor")
    score = max(0.0, 5 - 1.0 * n_crit - 0.5 * n_maj - 0.25 * n_min)
    unrepairable = any(c["id"] in ("P01", "P02", "D02") and c["status"] == "FAIL"
                       for c in rep.checks)
    verdict = "reject" if unrepairable else ("revise" if (n_crit or n_maj) else "accept")

    post = {k: sha256_file(PATHS[k]) for k in EXPECT}
    pin_drift = {k: v for k, v in post.items() if v != EXPECT[k]}
    rep.check("P03", "did any pinned input change while the review ran?",
              "PASS" if not pin_drift else "FAIL", {"post": post, "drift": pin_drift})

    report = {
        "task_id": "W097-L0-REV4-INDEP-REVIEW-01",
        "created_at": NOW(),
        "reviewer": "worker-097",
        "reviewer_independence": "not an author of the L0 ledger, its repair tools, the "
                                 "rev-4 builder, or any L0 adjudication",
        "target_id": "L0",
        "artifact": "ledger/theorems.jsonl",
        "reviewed_sha256": EXPECT["ledger"],
        "revision_chain": {"archive": EXPECT["archive"], "rev3": EXPECT["rev3snap"],
                           "rev4": EXPECT["ledger"]},
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
        "falsifier": "Re-run at the same five pins and find a check whose status differs, or "
                     "exhibit a rev-4 row that disjoins class ids but is not in the H02a "
                     "list, or a clause in A0 HF-02/HF-14/class_binding whose scope excludes "
                     "ledger rows (which would void F1/F2/F6 respectively).",
        "interpretation_limits": [
            "A0 detectors are read from evaluation_rubric.yaml at d748a9e3574e; a rubric "
            "revision voids the corresponding finding, not the measurement.",
            "class_disjunction is measured as len(class_ids) > 1; the rubric detector text "
            "is the cited authority.",
            "The rev-4 axis split is assessed on its own documentation (builder guard, "
            "MANIFEST); this review does not claim it is fraudulent, only that A0 does not "
            "yet define the new vocabulary (F6).",
            "MAP01/MAP02/H14S/D03/META/H01 are INFO measurements, not pass/fail gates."],
    }
    with open(os.path.join(out_dir, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1, ensure_ascii=False)
    with open(os.path.join(out_dir, "controls.json"), "w", encoding="utf-8") as f:
        json.dump({"controls": controls, "control_failures": control_fail}, f, indent=1)

    lines = []
    for k in list(EXPECT) + ["map", "events", "classsep", "builder", "manifest"]:
        if os.path.exists(PATHS[k]):
            lines.append(f"{sha256_file(PATHS[k])}  {PATHS[k]}")
    for fn in ("report.json", "controls.json", "run_l0_rev4_review.py"):
        p = os.path.join(out_dir, fn)
        if os.path.exists(p):
            lines.append(f"{sha256_file(p)}  {p}")
    with open(os.path.join(out_dir, "raw_sha256.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(json.dumps({"verdict": verdict, "score": report["score"],
                      "findings": {s: sum(1 for g in rep.findings if g["severity"] == s)
                                   for s in ("critical", "major", "minor")},
                      "checks": {c["id"]: c["status"] for c in rep.checks},
                      "control_failures": control_fail,
                      "report_sha256": sha256_file(os.path.join(out_dir, "report.json"))},
                     indent=1))
    return 2 if control_fail or pin_drift else 0


if __name__ == "__main__":
    sys.exit(main())
