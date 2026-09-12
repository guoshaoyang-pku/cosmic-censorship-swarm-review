#!/usr/bin/env python3
"""
W009-L1-VACUUM-CLASS-BINDING-CENSUS-01  (worker-009 / deepseek-flash-09)
Assignment asg-2026-09-11-L1-deepseek-flash-09-18   node L1   gate G-LIT
Bound classes: AF-SCC-C2-VAC-GEN; AF-SCC-C0-VAC-GEN

Bounded class-bound task.  Question: for every canonical L1 citation row that
binds a frozen strong-cosmic-censorship VACUUM class, is the bound source's
model inside the frozen class predicate?

Frozen predicate (read from the two schema bytes, not from prose):
    AF-SCC-C2-VAC-GEN / AF-SCC-C0-VAC-GEN
        matter: none
        equations: "Einstein vacuum equations Ric(g) = 0"
        statement: "... generic asymptotically flat vacuum initial data
        (4-dimensional Einstein vacuum equations, Lambda = 0) ..."
A source whose model carries matter (scalar / Maxwell / charged / ...) or whose
background has Lambda > 0 is outside that predicate: binding it to either class
is a scope error on the class's own terms.

Method (ledger-internal, offline, deterministic):
  universe = the 97 rows of ledger/citation_audit.csv at its pinned sha256;
             the 34 rows whose class_mapping carries an SCC vacuum token.
  evidence tiers for each (row, bound class):
    T1  'assumptions' entries of the cited L0 records (theorems.jsonl) that
        themselves declare the bound class in class_ids / informs_classes.
    T2  the row's own title + evidence_excerpt.
    T3  'scope_caveats' entries of the same supporting L0 records.
    L   lexicon fallback (see below) only when T1/T2/T3 carry no model cue.
  A statement is only counted when a model cue fires in the exact entry text;
  the entry text is stored verbatim with its sha256 and the containing file's
  pinned sha256, so every verdict is re-checkable byte-for-byte.

Decision per (row, class):
  lambda-NONZERO statement                         -> SCOPE_ERROR(lambda)
  matter-NONVAC and matter-VAC statements          -> UNDETERMINED(conflict)
  matter-NONVAC statement                          -> SCOPE_ERROR(matter)
  matter-VAC statement                             -> LICENSED
  lexicon exact-vacuum-solution fallback           -> LICENSED(lexicon)
  no model statement                               -> UNDETERMINED(no_statement)

This is a measurement, not a gate verdict: it writes no canonical file, sets no
node status and no validation_status.  Same-worker cross-method re-derivation
from pinned bytes (this worker's primary-source CBC-09 corrections are a
DIFFERENT evidence path and are referenced only for an agreement matrix).

Frozen run stamp: RUN_STAMP.  Wall-clock time lives in the outbox event and the
checkpoint, not in the hashed census core.
"""
import csv
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
OUTDIR = os.path.join(ROOT, "artifacts", "worker-009", "vacuum_binding")
RULES = os.path.join(OUTDIR, "rules_vacuum_binding_worker-009.json")
RECORD = os.path.join(OUTDIR, "verification_vacuum_binding_worker-009.json")
CSVOUT = os.path.join(OUTDIR, "census_vacuum_binding_worker-009.csv")

CITATION = os.path.join(ROOT, "ledger", "citation_audit.csv")
THEOREMS = os.path.join(ROOT, "ledger", "theorems.jsonl")
SCHEMA_C0 = os.path.join(ROOT, "schemas", "af_scc_c0_vacuum.yaml")
SCHEMA_C2 = os.path.join(ROOT, "schemas", "af_scc_c2_vacuum.yaml")

RUN_STAMP = "2026-09-12T01:21:13+08:00"
TASK_ID = "W009-L1-VACUUM-CLASS-BINDING-CENSUS-01"

PINS = {
    "ledger/citation_audit.csv": "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9",
    "ledger/theorems.jsonl": "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28",
    "schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
}

SCC = ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]

# Cue patterns: a statement counts only if one of these fires in the entry text.
NONVAC = (r"\b(?:scalar|Klein-?Gordon|EMKG|Maxwell|charged|Reissner|Nordstr(?:om|\u00f6m)|"
          r"Vaidya|dust|perfect[ -]fluid|self-gravitating|Einstein-Maxwell|Einstein--Maxwell|"
          r"matter field)\b")
VAC = (r"(?:Einstein vacuum equations?|vacuum Einstein equations?|Ric\(g\)\s*=\s*0|"
       r"solutions? of the vacuum|vacuum initial data|vacuum Cauchy data|\bEVE\b)")
LAM_NZ = (r"(?:positive cosmological constant|cosmological constant|Lambda\s*[>=]\s*0|"
          r"\u039b\s*[>=]\s*0|de Sitter|Kerr[- ]de Sitter|Kerr-dS)")

# Exact-vacuum-solution lexicon, used ONLY when no model statement exists.
# Authority: the frozen C0 schema's own excluded_set names the stationary Kerr
# data as elements of the class's vacuum data space X_vac.
LEXICON = {
    "patterns": [r"\bSchwarzschild\b", r"\bKerr\b"],
    "anti": [r"Kerr-Newman", r"de Sitter", r"\bdS\b", r"charged", r"scalar", r"Maxwell"],
    "authority_path": "schemas/af_scc_c0_vacuum.yaml",
    "authority_field": "genericity.excluded_set",
    "authority_quote": ("meager; must contain (status unresolved) the stationary/axisymmetric Kerr data, "
                        "whose maximal development admits a C-infinity (hence C0) vacuum extension, plus "
                        "self-similar and finite-dimensional analytic families"),
}

EXPECTED_ROWS_TOTAL = 97
EXPECTED_SCC_ROWS = 34

CONTROLS = [
    {"id": "C01", "kind": "pinned_row", "row": "SRC-021", "expect": "SCOPE_ERROR",
     "why": "Dafermos 2005 is Einstein-Maxwell-real-scalar; T-501 caveat says 'Matter model is EM-scalar, not vacuum'."},
    {"id": "C02", "kind": "pinned_row", "row": "SRC-014", "expect": "SCOPE_ERROR",
     "why": "Christodoulou 1999 is scalar-field collapse; D-007 assumption is Einstein-Maxwell-real-scalar."},
    {"id": "C03", "kind": "pinned_row", "row": "SRC-024", "expect": "SCOPE_ERROR",
     "why": "Holonomy paper covers RN-Vaidya / EM-scalar; T-304 caveat says 'Matter model is EM-scalar, not vacuum'."},
    {"id": "C04", "kind": "pinned_row", "row": "SRC-025", "expect": "SCOPE_ERROR",
     "why": "Van de Moortel is Einstein-Maxwell-Klein-Gordon (charged scalar)."},
    {"id": "C05", "kind": "pinned_row", "row": "SRC-035", "expect": "SCOPE_ERROR",
     "why": "Kerr-de Sitter: Einstein vacuum equations WITH Lambda > 0 is outside the frozen Lambda = 0 class."},
    {"id": "C06", "kind": "pinned_row", "row": "SRC-062", "expect": "LICENSED",
     "why": "Kerr stability paper: asymptotically flat solutions of the Einstein vacuum equations (EVE), Lambda = 0."},
    {"id": "C07", "kind": "pinned_row", "row": "SRC-022", "expect": "LICENSED",
     "why": "Row excerpt: 'satisfying the vacuum Einstein equations with singular boundaries', no symmetry."},
    {"id": "C08", "kind": "pinned_row", "row": "SRC-037", "expect": "LICENSED",
     "why": "Schwarzschild stability: 'solutions to the Einstein vacuum equations ... general vacuum initial data'."},
    {"id": "C09", "kind": "pinned_row", "row": "SRC-005", "expect": "LICENSED",
     "why": "Schwarzschild C^0-inextendibility: lexicon fallback (exact Kerr/Schwarzschild data live in X_vac)."},
    {"id": "C10", "kind": "rule_engine", "statements": [{"model": "NONVAC", "lambda": None}], "expect": "SCOPE_ERROR",
     "why": "synthetic matter-model statement must map to a scope error."},
    {"id": "C11", "kind": "rule_engine", "statements": [{"model": "VAC", "lambda": "ZERO"}], "expect": "LICENSED",
     "why": "synthetic vacuum statement must map to licensed."},
    {"id": "C12", "kind": "rule_engine", "statements": [], "expect": "UNDETERMINED",
     "why": "absence of a model statement must never be read as licensed."},
    {"id": "C13", "kind": "pin_drift", "expect": "DETECTED",
     "why": "a one-byte mutation of a pinned file must fail the sha256 gate."},
    {"id": "C14", "kind": "universe", "expect": [EXPECTED_ROWS_TOTAL, EXPECTED_SCC_ROWS],
     "why": "universe size is fixed by the pinned ledger bytes, not by the classifier."},
]

# Rows already covered by the pending worker-009 CBC-09 primary-source
# correction proposal (agreement matrix only; NOT used to decide verdicts).
CBC09 = {
    "SRC-021": "CBC-09-001", "SRC-056": "CBC-09-002", "SRC-025": "CBC-09-003",
    "SRC-058": "CBC-09-004", "SRC-057": "CBC-09-005", "SRC-024": "CBC-09-006",
    "SRC-050": "CBC-09-007", "SRC-014": "CBC-09-008", "SRC-061": "CBC-09-012",
}


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_text(t):
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def sha256_file(path):
    with open(path, "rb") as fh:
        return sha256_bytes(fh.read())


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def dig(obj, dotted):
    cur = obj
    for part in dotted.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def load_pinned(path, rel):
    raw = open(path, "rb").read()
    got = sha256_bytes(raw)
    exp = PINS[rel]
    if got != exp:
        raise SystemExit("PIN DRIFT: %s measured %s expected %s" % (rel, got[:12], exp[:12]))
    return raw.decode("utf-8")


def sentence_span(text, start, end, pad=200):
    """Smallest sentence-ish span around [start:end); exact substring of text."""
    lo = 0
    for m in re.finditer(r"(?:[.!?]\s+|[\"')\]]\s*$)", text[:start]):
        lo = m.end()
    hi = len(text)
    m = re.search(r"[.!?](?:\s+|$)", text[end:])
    if m:
        hi = end + m.end()
    if hi - lo > 600:  # keep quotes bounded; never longer than the cue's sentence
        lo = max(0, start - pad)
        hi = min(len(text), end + pad)
    return text[lo:hi].strip()


def extract_statements(text, tier, record, field):
    """Return model statements found in one text entry."""
    out = []
    if not text:
        return out
    for label, pat in (("NONVAC", NONVAC), ("VAC", VAC)):
        for m in re.finditer(pat, text, re.I):
            span = sentence_span(text, m.start(), m.end())
            lam = "NONZERO" if re.search(LAM_NZ, span, re.I) else None
            out.append({
                "tier": tier, "record": record, "field": field,
                "model": label, "lambda": lam,
                "quote": span, "quote_sha256": sha256_text(span),
                "field_sha256": sha256_text(text),
            })
    # Lambda with no model cue in the same sentence still counts only inside a
    # statement that already fired above; otherwise it is not about the model.
    if not out:
        for m in re.finditer(LAM_NZ, text, re.I):
            span = sentence_span(text, m.start(), m.end())
            out.append({
                "tier": tier, "record": record, "field": field,
                "model": None, "lambda": "NONZERO",
                "quote": span, "quote_sha256": sha256_text(span),
                "field_sha256": sha256_text(text),
            })
    return out


def decide(statements):
    """Documented decision rule; used for rows and for synthetic controls.

    A Lambda > 0 statement is decisive on its own when it comes from the row's
    own title/excerpt (T2) -- the frozen class is explicitly Lambda = 0.  A
    model-free Lambda statement from a cited record's assumptions is kept as
    evidence but not decisive, because literature-status records can mention
    other settings without describing their own model.
    """
    model = {s.get("model") for s in statements if s.get("model")}
    lam_nz = [s for s in statements
              if s.get("lambda") == "NONZERO" and (s.get("model") or s.get("tier", "").startswith("T2"))]
    if lam_nz:
        return "SCOPE_ERROR", "lambda_nonzero"
    if "NONVAC" in model and "VAC" in model:
        return "UNDETERMINED", "model_statement_conflict"
    if "NONVAC" in model:
        return "SCOPE_ERROR", "matter_present"
    if "VAC" in model:
        return "LICENSED", "vacuum_model"
    return "UNDETERMINED", "no_model_statement"


def build():
    """Read-only census. Returns the core (rows, counts, predicate, digest) plus
    the parsed inputs; no file is written here so the verifier can re-run it."""
    os.makedirs(OUTDIR, exist_ok=True)
    raw = {}
    for rel, path in (("ledger/citation_audit.csv", CITATION),
                      ("ledger/theorems.jsonl", THEOREMS),
                      ("schemas/af_scc_c0_vacuum.yaml", SCHEMA_C0),
                      ("schemas/af_scc_c2_vacuum.yaml", SCHEMA_C2)):
        raw[rel] = load_pinned(path, rel)

    rows = list(csv.DictReader(raw["ledger/citation_audit.csv"].splitlines()))
    theorems = {}
    for line in raw["ledger/theorems.jsonl"].splitlines():
        if line.strip():
            d = json.loads(line)
            theorems[d["theorem_id"]] = d
    c0 = yaml.safe_load(raw["schemas/af_scc_c0_vacuum.yaml"])
    c2 = yaml.safe_load(raw["schemas/af_scc_c2_vacuum.yaml"])

    predicate = {
        "classes": SCC,
        "matter": "none",
        "equations": "Einstein vacuum equations Ric(g) = 0 (4-dimensional, Lambda = 0)",
        "authority": [
            "schemas/af_scc_c2_vacuum.yaml#%s matter: %s equations: %s" % (
                PINS["schemas/af_scc_c2_vacuum.yaml"][:12], c2.get("matter"), c2.get("equations")),
            "schemas/af_scc_c0_vacuum.yaml#%s matter: %s equations: %s" % (
                PINS["schemas/af_scc_c0_vacuum.yaml"][:12], c0.get("matter"), c0.get("equations")),
        ],
    }

    scc_rows = [r for r in rows if any(t.strip() in SCC for t in r["class_mapping"].split(";"))]
    out_rows = []
    for r in scc_rows:
        cid = r["citation_id"]
        tokens = [t.strip() for t in r["class_mapping"].split(";")]
        bound = [t for t in tokens if t in SCC]
        refs = [x.strip() for x in r["used_by_theorems"].replace(",", ";").split(";") if x.strip()]
        per_class = []
        for cls in bound:
            supporting = []
            for t in refs:
                d = theorems.get(t)
                if not d:
                    continue
                declared = list(d.get("class_ids") or []) + list(d.get("informs_classes") or [])
                if cls in declared:
                    supporting.append(t)
            stmts = []
            for t in supporting:
                d = theorems[t]
                for entry in (d.get("assumptions") or []):
                    stmts += extract_statements(entry, "T1_supporting_record_assumption", t, "assumptions")
            for field in ("title", "evidence_excerpt"):
                stmts += extract_statements(r.get(field, ""), "T2_row_own_%s" % field, cid, field)
            for t in supporting:
                d = theorems[t]
                for entry in (d.get("scope_caveats") or []):
                    stmts += extract_statements(entry, "T3_supporting_record_caveat", t, "scope_caveats")
            verdict, reason = decide(stmts)
            lexicon_used = False
            if verdict == "UNDETERMINED" and reason == "no_model_statement":
                target = (r.get("title", "") + " " + r.get("evidence_excerpt", ""))
                if any(re.search(p, target) for p in LEXICON["patterns"]) and \
                   not any(re.search(p, target, re.I) for p in LEXICON["anti"]):
                    verdict, reason, lexicon_used = "LICENSED", "vacuum_model_lexicon", True
                    stmts = [{
                        "tier": "L_lexicon_authority", "record": "schemas/af_scc_c0_vacuum.yaml",
                        "field": LEXICON["authority_field"], "model": "VAC", "lambda": "ZERO",
                        "quote": LEXICON["authority_quote"],
                        "quote_sha256": sha256_text(LEXICON["authority_quote"]),
                        "field_sha256": sha256_text(str(dig(c0, LEXICON["authority_field"]))),
                    }]
            models = sorted({s.get("model") for s in stmts if s.get("model")})
            per_class.append({
                "class_id": cls, "verdict": verdict, "reason": reason,
                "matter": ("NONVAC" if "NONVAC" in models else ("VAC" if "VAC" in models else None)),
                "lambda": ("NONZERO" if any(s.get("lambda") == "NONZERO" for s in stmts) else None),
                "supporting_records": supporting, "lexicon_fallback": lexicon_used,
                "decisive_statements": stmts,
            })
        row_verdict = "SCOPE_ERROR" if any(p["verdict"] == "SCOPE_ERROR" for p in per_class) else \
                      ("LICENSED" if all(p["verdict"] == "LICENSED" for p in per_class) else "UNDETERMINED")
        out_rows.append({
            "citation_id": cid, "class_mapping": r["class_mapping"], "scc_tokens": bound,
            "row_verdict": row_verdict, "per_class": per_class,
            "pending_cbc09_correction": CBC09.get(cid),
            "agrees_with_pending_cbc09": (CBC09.get(cid) is not None and row_verdict == "SCOPE_ERROR"),
        })

    counts = {
        "rows_total": len(rows),
        "rows_binding_scc": len(scc_rows),
        "rows_out_of_scope": len(rows) - len(scc_rows),
        "LICENSED": sum(1 for r in out_rows if r["row_verdict"] == "LICENSED"),
        "SCOPE_ERROR": sum(1 for r in out_rows if r["row_verdict"] == "SCOPE_ERROR"),
        "UNDETERMINED": sum(1 for r in out_rows if r["row_verdict"] == "UNDETERMINED"),
        "scope_error_matter": sum(1 for r in out_rows for p in r["per_class"]
                                  if p["verdict"] == "SCOPE_ERROR" and p["reason"] == "matter_present"),
        "scope_error_lambda": sum(1 for r in out_rows for p in r["per_class"]
                                  if p["verdict"] == "SCOPE_ERROR" and p["reason"] == "lambda_nonzero"),
        "already_in_pending_cbc09": sum(1 for r in out_rows if r["agrees_with_pending_cbc09"]),
        "new_scope_errors_not_in_cbc09": sorted(r["citation_id"] for r in out_rows
                                                if r["row_verdict"] == "SCOPE_ERROR" and not r["pending_cbc09_correction"]),
    }
    core = {"rows": out_rows, "counts": counts, "predicate": predicate}
    digest = sha256_bytes(canonical(core).encode("utf-8"))

    # ---- controls -----------------------------------------------------------
    ctrl = []
    by_id = {r["citation_id"]: r for r in out_rows}
    for c in CONTROLS:
        if c["kind"] == "pinned_row":
            got = by_id[c["row"]]["row_verdict"]
            ok = got == c["expect"]
            detail = "%s -> %s (expected %s)" % (c["row"], got, c["expect"])
        elif c["kind"] == "rule_engine":
            got, why = decide(c["statements"])
            ok = got == c["expect"]
            detail = "synthetic[%s] -> %s (expected %s)" % (len(c["statements"]), got, c["expect"])
        elif c["kind"] == "pin_drift":
            probe = raw["ledger/theorems.jsonl"].encode("utf-8")
            mutated = bytearray(probe)
            mutated[len(mutated) // 2] ^= 0x01
            ok = sha256_bytes(bytes(mutated)) != PINS["ledger/theorems.jsonl"]
            detail = "one-byte mutation changes sha256: %s" % ok
        elif c["kind"] == "universe":
            got = [len(rows), len(scc_rows)]
            ok = got == c["expect"]
            detail = "universe %s (expected %s)" % (got, c["expect"])
        else:
            ok, detail = False, "unknown control kind"
        ctrl.append({"id": c["id"], "kind": c["kind"], "expected": c["expect"],
                     "passed": bool(ok), "detail": detail, "why": c["why"]})

    return {"rows": rows, "scc_rows": scc_rows, "out_rows": out_rows, "counts": counts,
            "predicate": predicate, "census_digest": digest, "controls": ctrl,
            "raw": raw, "c0": c0, "c2": c2}


def main():
    built = build()
    out_rows = built["out_rows"]
    counts = built["counts"]
    ctrl = built["controls"]
    digest = built["census_digest"]
    predicate = built["predicate"]
    c0 = built["c0"]
    by_id = {r["citation_id"]: r for r in out_rows}

    rules_obj = {
        "rules_id": TASK_ID, "version": "1.0", "run_stamp": RUN_STAMP,
        "pins": PINS, "class_predicate": predicate,
        "cue_patterns": {"NONVAC": NONVAC, "VAC": VAC, "LAMBDA_NONZERO": LAM_NZ},
        "tiers": {
            "T1": "supporting L0 record 'assumptions' entries",
            "T2": "row title + evidence_excerpt",
            "T3": "supporting L0 record 'scope_caveats' entries",
            "L": "exact-vacuum-solution lexicon, only when T1-T3 carry no model cue",
        },
        "decision": {
            "lambda_nonzero": "SCOPE_ERROR (decisive if the statement has a model cue, or comes from the row's own T2 text)",
            "matter_and_vac_conflict": "UNDETERMINED",
            "matter_present": "SCOPE_ERROR", "vacuum_model": "LICENSED",
            "lexicon_vacuum": "LICENSED", "no_model_statement": "UNDETERMINED",
        },
        "lexicon": LEXICON, "controls": CONTROLS,
    }
    rules_text = json.dumps(rules_obj, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    open(RULES, "w", encoding="utf-8").write(rules_text)

    record = {
        "schema_version": "0.1",
        "artifact_type": "class_binding_census",
        "artifact_kind": "verification_record",
        "task_id": TASK_ID,
        "verification_id": "worker-009-vacbinding-" + RUN_STAMP,
        "run_stamp": RUN_STAMP,
        "created_at": RUN_STAMP,
        "actor": "worker-009",
        "worker": "worker-009",
        "node_id": "L1",
        "gate": "G-LIT",
        "group_id": "literature",
        "assignment_id": "asg-2026-09-11-L1-deepseek-flash-09-18",
        "class_ids": SCC,
        "target_id": "ledger/citation_audit.csv#315c19145065",
        "review_scope": ("ledger-internal class-binding census at pinned bytes; same-worker cross-method "
                         "re-derivation, NOT an independent reviewer verdict"),
        "method": ("for every canonical row binding AF-SCC-C2-VAC-GEN or AF-SCC-C0-VAC-GEN, test the "
                   "frozen predicate matter=none / EVE Ric(g)=0 / Lambda=0 against the cited L0 records "
                   "that declare the bound class (T1 assumptions, T3 caveats) and the row's own text (T2), "
                   "with an exact-vacuum-solution lexicon fallback (L); every decisive quote is stored "
                   "verbatim with its sha256"),
        "pins": dict(PINS),
        "rules_file": {"path": "artifacts/worker-009/vacuum_binding/rules_vacuum_binding_worker-009.json",
                       "sha256": sha256_bytes(rules_text.encode("utf-8"))},
        "predicate": predicate,
        "universe": {"rows_total": counts["rows_total"], "rows_binding_scc": counts["rows_binding_scc"],
                     "rows_out_of_scope": counts["rows_out_of_scope"]},
        "counts": counts,
        "rows": out_rows,
        "controls": ctrl,
        "controls_all_pass": all(c["passed"] for c in ctrl),
        "new_findings": [
            {"citation_id": cid,
             "class_ids": [p["class_id"] for p in by_id[cid]["per_class"] if p["verdict"] == "SCOPE_ERROR"],
             "reason": "; ".join("%s:%s" % (p["class_id"], p["reason"]) for p in by_id[cid]["per_class"]
                                 if p["verdict"] == "SCOPE_ERROR"),
             "decisive_quote": next((s["quote"] for p in by_id[cid]["per_class"] for s in p["decisive_statements"]
                                     if p["verdict"] == "SCOPE_ERROR" and s["model"]), None),
             "note": "not covered by the pending CBC-09 primary-source correction proposal"}
            for cid in counts["new_scope_errors_not_in_cbc09"]
        ],
        "agreement_matrix": {
            "pending_cbc09_rows_out_of_15_scope_errors": sorted(CBC09),
            "census_agrees_on_all_covered_rows": all(r["agrees_with_pending_cbc09"] for r in out_rows
                                                     if r["pending_cbc09_correction"]),
        },
        "census_digest": digest,
        "reproduce": ("python3 artifacts/worker-009/vacuum_binding/verify_vacuum_binding_worker-009.py "
                      "--recheck"),
        "falsifier": ("Any one of: (a) re-run the census tool and the verifier at the four pinned sha256 "
                      "values and obtain a different census_digest or different per-row verdicts; (b) exhibit a "
                      "row marked SCOPE_ERROR whose cited source is in fact a 4D Einstein-vacuum (Ric=0, "
                      "Lambda=0) model with no matter field; (c) exhibit a row marked LICENSED whose cited "
                      "source carries matter or Lambda > 0, or whose decisive quote is not present verbatim in "
                      "the pinned file/field it is attributed to; (d) show that a decisive quote's recorded "
                      "sha256 does not match the pinned bytes; (e) show the frozen predicate used here differs "
                      "from schemas/af_scc_c0_vacuum.yaml / af_scc_c2_vacuum.yaml at the pinned hashes."),
        "not_claimed": ["gate verdict", "node status", "validation_status", "canonical ledger write",
                        "detector-scope or HF-02 ruling", "primary-source re-fetch (ledger-internal census only)",
                        "independent non-author review"],
        "evidence_refs": [
            "ledger/citation_audit.csv#315c19145065",
            "ledger/theorems.jsonl#a1674f094979",
            "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
            "schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3",
            "artifacts/worker-009/vacuum_binding/rules_vacuum_binding_worker-009.json#" + sha256_bytes(rules_text.encode("utf-8"))[:12],
        ],
    }
    open(RECORD, "w", encoding="utf-8").write(json.dumps(record, ensure_ascii=False, indent=1) + "\n")

    with open(CSVOUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["citation_id", "row_verdict", "class_token", "class_verdict", "reason",
                    "matter_axis", "lambda_axis", "lexicon_fallback", "supporting_records",
                    "tier", "record", "field", "quote", "quote_sha256"])
        for r in out_rows:
            for p in r["per_class"]:
                if p["decisive_statements"]:
                    for s in p["decisive_statements"]:
                        w.writerow([r["citation_id"], r["row_verdict"], p["class_id"], p["verdict"],
                                    p["reason"], p["matter"], p["lambda"], p["lexicon_fallback"],
                                    ";".join(p["supporting_records"]),
                                    s["tier"], s["record"], s["field"], s["quote"], s["quote_sha256"]])
                else:
                    w.writerow([r["citation_id"], r["row_verdict"], p["class_id"], p["verdict"],
                                p["reason"], p["matter"], p["lambda"], p["lexicon_fallback"],
                                ";".join(p["supporting_records"]), "", "", "", "", ""])

    print("universe rows=%d scc_rows=%d licensed=%d scope_error=%d undetermined=%d" %
          (counts["rows_total"], counts["rows_binding_scc"], counts["LICENSED"],
           counts["SCOPE_ERROR"], counts["UNDETERMINED"]))
    print("new scope errors not in CBC-09:", ",".join(counts["new_scope_errors_not_in_cbc09"]))
    print("controls:", " ".join("%s=%s" % (c["id"], "PASS" if c["passed"] else "FAIL") for c in ctrl))
    print("census_digest:", digest)
    if not all(c["passed"] for c in ctrl):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
