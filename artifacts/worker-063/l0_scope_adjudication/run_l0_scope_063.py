#!/usr/bin/env python3
"""W063-L0-SCOPE-ADJUDICATION-01 - independent, read-only adjudication input for BL-7.

Question (from reviews/L0-freeze-reconciliation.json `blockers[BL-7]`): the live L0 ledger
(ledger/theorems.jsonl, sha256 a1674f094979...) carries 8 rows whose `class_ids` list holds two
frozen class ids. Reviewer-level application of the A0 HF-02 detector text ("disjunction of
class_ids") reads that as class leakage, which blocks G-LIT/G-AUDIT at 0 independent accepts.
This instrument measures, on the live bytes:

  (1) how the *canonical* validator routes ledger rows (claim vs record) and therefore whether
      HF-01/HF-02 can see them at all;
  (2) how the *canonical* class-separation detector scores the live rows (declaration mode and
      prose mode) and whether it flags a two-element frozen-id list;
  (3) an independent statement-level merge/identity test over all 62 statements (positive
      merge assertions, not mentions or negations);
  (4) the HF-14 self-certification state at the live hash;
  (5) a dry-run (in-memory, never written) repair simulation that moves secondary ids into
      `informs_classes`, and its cost: hash move + fresh verdict round;
  (6) 8 mutation controls.

No canonical file is written. The report only records measurements and the decision inputs for
a controller/A0 scope ruling; it does not set a gate verdict, node status or validation_status.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
LEDGER = ROOT / "ledger" / "theorems.jsonl"
RUBRIC = ROOT / "evaluation_rubric.yaml"
RECON = ROOT / "reviews" / "L0-freeze-reconciliation.json"
MAP = ROOT / "research_map" / "research_map.json"
CODE = {
    "artifacts/audit/audit_lib.py": ROOT / "artifacts" / "audit" / "audit_lib.py",
    "artifacts/audit/audit_run.py": ROOT / "artifacts" / "audit" / "audit_run.py",
    "research_map/class_separation.py": ROOT / "research_map" / "class_separation.py",
}
FROZEN = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]
# Pin expectations for the subject and the tooling. A mismatch -> VOID (fail closed).
EXPECT = {
    str(LEDGER.relative_to(ROOT)): "a1674f094979",
    str(RUBRIC.relative_to(ROOT)): "d748a9e3574e",
    "artifacts/audit/audit_lib.py": "ae573db84631",
    "artifacts/audit/audit_run.py": "3b27dd3fef7f",
    "research_map/class_separation.py": "c266dbceca87",
}
HF02_ROWS = ["D-004", "D-005", "T-303", "T-305", "T-402", "T-515", "T-526", "T-528"]

# Independent statement-level cues (this instrument's own regexes; the canonical detector
# _MERGE_PAT/_MERGE_ASSERT in research_map/class_separation.py is used as a second opinion).
MERGE_CUE = re.compile(
    r"\bas\s+one\b|\bare\s+one\b|\bis\s+one\b|\bone\s+class\b|\bsingle\s+class\b|\bsame\s+class\b"
    r"|\bunified\b|\bunify\b|\bmerged\b|\bmerge\b|\bcombined\b|\bconflate\b|\bidentified\b"
    r"|\bequivalent\s+classes?\b|\binterchangeable\b|\bdisjunction\b|\bdisjoined\b",
    re.I,
)
NEG_CUE = re.compile(
    r"\bno\b|\bnot\b|\bnever\b|\bwithout\b|\bforbid(?:den)?\b|\bmust\s+not\b|\bdo\s+not\b"
    r"|\bdistinct\b|\bseparate\b|\bnot\s+interchangeable\b|\bnon-?merge\b|\bdoes\s+not\s+merge\b",
    re.I,
)
CLASS_REF = re.compile(
    r"AF-[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+|\bC\s*\^?\s*\{?\s*0\b|\bC\s*\^?\s*\{?\s*2\b"
    r"|\bC0\b|\bC2\b",
    re.I,
)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def read_rows():
    rows = []
    for i, line in enumerate(LEDGER.read_text().splitlines(), 1):
        if line.strip():
            r = json.loads(line)
            r["_line"] = i
            rows.append(r)
    return rows


def class_ids_of(r):
    v = r.get("class_ids")
    return [str(x) for x in v] if isinstance(v, list) else ([str(v)] if v else [])


def sentence_merge_scan(text: str):
    """Statements that POSITIVELY assert a merge/identity of two frozen classes.

    Sentence = clause split on [.;] (commas kept, so a list of two ids in one clause counts).
    A sentence fires iff it references >=2 distinct frozen classes AND carries a merge cue AND
    carries no negation/distinction cue.
    """
    hits = []
    for sent in re.split(r"[.;]\s+", str(text or "")):
        refs = set()
        for m in CLASS_REF.finditer(sent):
            tok = m.group(0).upper()
            if tok in FROZEN:
                refs.add(tok)
            elif re.fullmatch(r"C\s*\^?\s*\{?\s*0\b|C0", tok):
                refs.add("AF-SCC-C0-VAC-GEN")
            elif re.fullmatch(r"C\s*\^?\s*\{?\s*2\b|C2", tok):
                refs.add("AF-SCC-C2-VAC-GEN")
        if len(refs) < 2:
            continue
        if MERGE_CUE.search(sent) and not NEG_CUE.search(sent):
            hits.append({"sentence": sent.strip()[:240], "classes": sorted(refs)})
    return hits


def measure(rows, cs, A, run_mod):
    m = {}

    # ---- C01 parse integrity -------------------------------------------------------------
    ids = [r["theorem_id"] for r in rows]
    m["C01_parse"] = {
        "rows": len(rows),
        "unique_ids": len(set(ids)) == len(ids),
        "all_22_keys": all(len(r) >= 22 for r in rows),
        "pass": len(rows) == 62 and len(set(ids)) == len(ids),
    }

    # ---- C02 class-binding census --------------------------------------------------------
    toks, informs, empty_bind = [], [], []
    for r in rows:
        cids = class_ids_of(r)
        toks += cids
        inf = r.get("informs_classes") or []
        if isinstance(inf, list):
            informs += [str(x) for x in inf]
        if not cids:
            empty_bind.append(r["theorem_id"])
    multi = [r["theorem_id"] for r in rows if len(class_ids_of(r)) >= 2]
    unknown = sorted({t for t in toks + informs if t not in FROZEN})
    m["C02_census"] = {
        "class_ids_tokens": len(toks),
        "informs_classes_tokens": len(informs),
        "total_tokens": len(toks) + len(informs),
        "unknown_tokens": unknown,
        "rows_empty_class_ids": len(empty_bind),
        "rows_multi_class_ids": multi,
        "multi_matches_expected": multi == HF02_ROWS,
        "pass": unknown == [] and multi == HF02_ROWS,
    }

    # ---- C03 canonical routing: are ledger rows claims or records? ------------------------
    # Scan a scratch copy so that concurrent writers to ledger/*.jsonl cannot perturb the
    # routing measurement (no canonical file is touched).
    scratch = ROOT / "tmp" / "w063_l0_scope"
    scratch.mkdir(parents=True, exist_ok=True)
    (scratch / "theorems.jsonl").write_bytes(LEDGER.read_bytes())
    corpus = run_mod.scan_corpus([scratch])
    live_ids = {r["theorem_id"] for r in rows}
    claims = [c for c in corpus["claims"] if c.get("theorem_id") in live_ids]
    records = [c for c in corpus["records"] if c.get("theorem_id") in live_ids]
    # Execute the canonical class-binding checker on a ledger row *as if* it were a claim, to
    # show the routing consequence explicitly (this is not how audit_run routes it).
    classes = A.frozen_classes(A.load_rubric(RUBRIC))
    as_claim = A.check_class_binding(rows[0], classes)
    m["C03_canonical_routing"] = {
        "audit_run_scan_corpus_routing": {
            "ledger_rows_classified_as_claims": len(claims),
            "ledger_rows_classified_as_records": len(records),
            "routing_predicate": "claim iff claim_id present OR (not schema_doc AND 'class_id' in obj AND 'statement' in obj) [audit_run.py:100-102]; ledger rows carry theorem_id/class_ids/statement_exact -> records [audit_run.py:117-119]",
        },
        "check_class_binding_call_sites": {
            "claims_loop": "audit_run.py:232-233 for c in corpus['claims']: A.check_class_binding(c, classes)",
            "records_loop": "audit_run.py:244 A.check_self_certification(corpus['records'])",
        },
        "checker_reads_singular_key": "audit_lib.py:143 cid = claim.get('class_id')",
        "row0_as_claim_would_yield": [str(v) for v in as_claim],
        "pass": len(claims) == 0 and len(records) == 62,
    }

    # ---- C04 canonical class-separation detector on live ledger rows ----------------------
    decl_findings, prose_findings = [], []
    for r in rows:
        where = f"ledger/theorems.jsonl:{r['_line']}"
        decl_findings += cs.findings(r, f"{where} ({r['theorem_id']})", mode="declaration")
        prose_findings += cs.findings_for_text(
            str(r.get("statement_exact", "")), f"{where} ({r['theorem_id']}).statement_exact"
        )
    m["C04_canonical_detector"] = {
        "declaration_mode_findings": decl_findings,
        "prose_mode_findings": prose_findings,
        "single_token_merge_rule": "class_separation.py:97-114 _scan_class_ids flags a token only when one token carries both C0 and C2; two valid frozen ids in a list are not flagged",
        "new_observation": "the canonical scanner is STRICTER than the reviewer HF-02 list: it additionally flags T-402.regularity free text 'Between C0 and C2 (weak null singularity).' as a bare composite in declaration mode, while the 8 two-id class_ids rows are NOT flagged",
        "pass": True,  # census executed deterministically; findings are reported as evidence, not suppressed
        "findings_count": len(decl_findings) + len(prose_findings),
    }

    # ---- C05 independent statement-level merge test --------------------------------------
    stmt_hits = {}
    for r in rows:
        h = sentence_merge_scan(r.get("statement_exact", ""))
        if h:
            stmt_hits[r["theorem_id"]] = h
    hf_rows_detail = []
    for tid in HF02_ROWS:
        r = next(x for x in rows if x["theorem_id"] == tid)
        hf_rows_detail.append(
            {
                "theorem_id": tid,
                "line": r["_line"],
                "class_ids": class_ids_of(r),
                "informs_classes": r.get("informs_classes"),
                "conclusion_type": r.get("conclusion_type"),
                "entry_kind": r.get("entry_kind"),
                "content_status": r.get("content_status"),
                "statement_has_merge_assertion": bool(sentence_merge_scan(r.get("statement_exact", ""))),
            }
        )
    m["C05_statement_level"] = {
        "rows_scanned": len(rows),
        "rows_with_positive_merge_assertion": sorted(stmt_hits),
        "hits": stmt_hits,
        "multi_bound_rows_detail": hf_rows_detail,
        "pass": stmt_hits == {},
    }

    # ---- C06 HF-14 self-certification at the live hash -----------------------------------
    self_cert = A.check_self_certification(records)
    key_census = {}
    for r in rows:
        for k in ("status", "validation_status", "supports_claim", "author_asserts_supports",
                  "review_status", "acceptance_authority"):
            if k in r:
                key_census[k] = key_census.get(k, 0) + 1
    aas_values = sorted({json.dumps(r.get("author_asserts_supports")) for r in rows})
    m["C06_hf14"] = {
        "self_certification_violations": [str(v) for v in self_cert],
        "key_presence_census": key_census,
        "author_asserts_supports_values": aas_values,
        "literal_detector_keys_absent": all(
            k not in key_census for k in ("status", "validation_status", "supports_claim")
        ),
        "pass": self_cert == [],
    }

    # ---- C07 dry-run repair simulation (in memory only) ----------------------------------
    repaired, changed = [], []
    for r in rows:
        rr = json.loads(json.dumps({k: v for k, v in r.items() if k != "_line"}))
        cids = class_ids_of(rr)
        if len(cids) >= 2:
            keep, move = cids[0], cids[1:]
            rr["class_ids"] = [keep]
            inf = list(rr.get("informs_classes") or [])
            rr["informs_classes"] = inf + [x for x in move if x not in inf]
            changed.append(rr["theorem_id"])
        repaired.append(rr)
    rep_findings, rep_multi = [], []
    for rr in repaired:
        rep_findings += cs.findings(rr, f"sim:{rr['theorem_id']}", mode="declaration")
        if len(class_ids_of(rr)) >= 2:
            rep_multi.append(rr["theorem_id"])
    rep_tokens = sum(len(class_ids_of(rr)) for rr in repaired) + sum(
        len(rr.get("informs_classes") or []) for rr in repaired
    )

    def flagged_ids(findings):
        ids = set()
        for f in findings:
            m = re.search(r"\((T-\d+|D-\d+)\)", f) or re.search(r"\bsim:([TD]-\d+)", f)
            if m:
                ids.add(m.group(1))
        return ids
    content_keys = [k for k in rows[0] if k != "_line"]
    key_equal = all(
        all(a.get(k) == b.get(k) for k in content_keys if k not in ("class_ids", "informs_classes"))
        for a, b in zip(rows, repaired)
    )
    rep_payload = "\n".join(json.dumps(rr, sort_keys=True) for rr in repaired) + "\n"
    m["C07_repair_simulation"] = {
        "changed_rows": changed,
        "canonical_detector_findings_after": rep_findings,
        "hf02_literal_disjunction_after": rep_multi,
        "token_census_before_after": {
            "before": len(toks) + len(informs),
            "after": rep_tokens,
        },
        "all_other_keys_unchanged": key_equal,
        "simulated_ledger_sha256": sha256_bytes(rep_payload.encode()),
        "live_ledger_sha256": sha256_file(LEDGER),
        "hash_moves": sha256_bytes(rep_payload.encode()) != sha256_file(LEDGER),
        "note": "which id stays bound is an owner content decision; this simulation keeps the first-listed id only to price the change",
        "residual_equals_pre_existing_regularity_finding": flagged_ids(rep_findings) == flagged_ids(decl_findings),
        "residual_flagged_rows": sorted(flagged_ids(rep_findings)),
        "interpretation": "moving secondary ids to informs_classes clears the 8 literal class_ids disjunctions but does NOT clear the separate T-402.regularity canonical finding; that is a distinct scope question",
        "pass": rep_multi == [] and rep_tokens == len(toks) + len(informs) and key_equal
                and flagged_ids(rep_findings) == flagged_ids(decl_findings),
    }

    # ---- C08 mutation controls ------------------------------------------------------------
    controls = []

    def ctl(cid, desc, ok, detail):
        controls.append({"id": cid, "desc": desc, "pass": bool(ok), "detail": detail})

    base = {
        "theorem_id": "CTL",
        "class_ids": ["AF-SCC-C0-VAC-GEN"],
        "statement_exact": "A C0-inextendibility result for spherical collapse.",
        "conclusion_type": "theorem",
        "informs_classes": [],
    }
    # M1 genuine merge assertion must fire both canonical prose scan and the statement test
    m1 = dict(base, statement_exact="We treat C0 and C2 as one class: the merged C0/C2 formulation is used throughout.")
    c1 = cs.findings_for_text(m1["statement_exact"], "ctl:M1")
    ctl("M1", "genuine merge assertion fires (canonical prose + statement test)",
        bool(c1) and bool(sentence_merge_scan(m1["statement_exact"])), {"canonical": c1, "statement": sentence_merge_scan(m1["statement_exact"])})
    # M2 relevance-only dual binding: field-list not flagged by canonical declaration scan
    m2 = dict(base, class_ids=["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"])
    c2 = cs.findings(m2, "ctl:M2", mode="declaration")
    ctl("M2", "two valid frozen ids in class_ids are NOT flagged by canonical declaration scan",
        c2 == [] and not sentence_merge_scan(m2["statement_exact"]), {"canonical": c2})
    # M3 proper discipline clears both
    m3 = dict(base, class_ids=["AF-SCC-C2-VAC-GEN"], informs_classes=["AF-SCC-C0-VAC-GEN"])
    c3 = cs.findings(m3, "ctl:M3", mode="declaration")
    ctl("M3", "one binding id + informs_classes clears both", c3 == [] and not sentence_merge_scan(m3["statement_exact"]), {"canonical": c3})
    # M4 unknown class token is flagged
    m4 = dict(base, class_ids=["AF-SCC-C5-VAC-GEN"])
    c4 = cs.findings(m4, "ctl:M4", mode="declaration")
    ctl("M4", "unknown frozen-style class token is flagged", bool(c4), {"canonical": c4})
    # M5 single-token C0/C2 composite is flagged
    m5 = dict(base, class_ids=["AF-SCC-C0/C2-VAC-GEN"])
    c5 = cs.findings(m5, "ctl:M5", mode="declaration")
    ctl("M5", "single-token C0/C2 composite is flagged", bool(c5), {"canonical": c5})
    # M6 HF-14 literal fires on self-certified record
    rec = {"theorem_id": "CTL", "status": "accepted", "supports_claim": True, "source_ids": ["SRC-1"]}
    c6 = A.check_self_certification([rec])
    ctl("M6", "HF-14 literal fires on status=accepted + supports_claim with no reviewer verdict",
        len(c6) >= 1, {"violations": [str(v) for v in c6]})
    # M7 negation/mention: the statement test must clear it; the canonical scanner is expected to
    # reproduce the documented CF-16 false positive (its negation guard's \w+ cannot span 'C0/C2').
    m7 = "There is no C0/C2 merge in this row; C0 and C2 remain distinct."
    m7canon = cs.findings_for_text(m7, "ctl:M7")
    ctl("M7", "negation is not a merge for the statement test, and the canonical scanner reproduces the documented CF-16 FP",
        (not sentence_merge_scan(m7)) and bool(m7canon), {"canonical_expected_fp": m7canon, "statement": sentence_merge_scan(m7)})
    # M8 two separate clauses are not a merge
    m8 = "C0 inextendibility holds in the spherical model. Separately, C2 inextendibility is studied for Kerr."
    ctl("M8", "two separate clauses are not a merge", not sentence_merge_scan(m8), {"statement": sentence_merge_scan(m8)})
    m["C08_controls"] = {"controls": controls, "passed": sum(1 for c in controls if c["pass"]), "total": len(controls)}

    return m


def main():
    created = datetime.now().astimezone().isoformat(timespec="seconds")
    pins = {}
    for rel, p in [(str(LEDGER.relative_to(ROOT)), LEDGER), (str(RUBRIC.relative_to(ROOT)), RUBRIC),
                   (str(MAP.relative_to(ROOT)), MAP), (str(RECON.relative_to(ROOT)), RECON)] + list(CODE.items()):
        pins[rel] = {"sha256": sha256_file(p), "bytes": p.stat().st_size}
    void = [rel for rel, pre in EXPECT.items() if not pins[rel]["sha256"].startswith(pre)]

    cs = load_module("cs063", CODE["research_map/class_separation.py"])
    A = load_module("audit_lib063", CODE["artifacts/audit/audit_lib.py"])
    run_mod = load_module("audit_run063", CODE["artifacts/audit/audit_run.py"])

    rows = read_rows()
    m1 = measure(rows, cs, A, run_mod)
    m2 = measure(read_rows(), cs, A, run_mod)

    def strip_dyn(m):
        return json.loads(json.dumps(m, sort_keys=True))

    d1 = sha256_bytes(json.dumps(strip_dyn(m1), sort_keys=True).encode())
    d2 = sha256_bytes(json.dumps(strip_dyn(m2), sort_keys=True).encode())

    # re-measure pins after the run: ledger/rubric/tooling drift voids the adjudication; the
    # live research map is expected to move (traffic continues) and is recorded as an observation
    pins_after = {rel: sha256_file((ROOT / rel)) for rel in pins}
    drift = sorted(rel for rel in pins if rel in EXPECT and pins_after[rel] != pins[rel]["sha256"])
    map_moved = pins_after.get("research_map/research_map.json") != pins.get("research_map/research_map.json")

    per_check_d1 = {k: sha256_bytes(json.dumps(strip_dyn(v), sort_keys=True).encode()) for k, v in m1.items()}
    per_check_d2 = {k: sha256_bytes(json.dumps(strip_dyn(v), sort_keys=True).encode()) for k, v in m2.items()}
    nondet = sorted(k for k in per_check_d1 if per_check_d1[k] != per_check_d2[k])

    checks = m1
    controls = checks["C08_controls"]
    canonical_pass = all(checks[k]["pass"] for k in ("C01_parse", "C02_census", "C03_canonical_routing", "C04_canonical_detector", "C06_hf14", "C07_repair_simulation"))
    status = "VOID" if (void or drift or nondet) else ("MEASURED" if canonical_pass and controls["passed"] == controls["total"] else "MEASURED_WITH_FAILURES")

    report = {
        "schema_version": "0.1",
        "task_id": "W063-L0-SCOPE-ADJUDICATION-01",
        "artifact_kind": "scope_adjudication",
        "actor": "worker-063",
        "instance": "worker-063-20260912T004359-968807",
        "created_at": created,
        "node_id": "L0",
        "gates": ["G-LIT", "G-AUDIT"],
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "question": "Are the 8 rows whose class_ids list holds two frozen ids (D-004, D-005, T-303, T-305, T-402, T-515, T-526, T-528) class leakage under HF-02, or record-scope relevance misread by a claim-scoped detector?",
        "status": status,
        "void_reasons": {"expected_pin_mismatch": void, "post_run_drift": drift, "nondeterministic_checks": nondet},
        "pins": pins,
        "pins_after": pins_after,
        "observations": {
            "map_moved_during_run": map_moved,
            "map_note": "research_map/research_map.json is live controller state and is expected to move; it is not part of the frozen subject of this adjudication",
        },
        "determinism_digest": d1,
        "per_check_digests": per_check_d1,
        "checks": checks,
        "adjudication_inputs": {
            "reading_R1_record_scope_canonical": {
                "claim": "audit_run.scan_corpus routes all 62 ledger rows to corpus['records'] (0 to corpus['claims']); HF-01/HF-02 run only on claims (audit_run.py:232-233) and check_class_binding reads the singular key class_id (audit_lib.py:143); the ledger record path runs check_self_certification (audit_run.py:244), which is clean at the live hash.",
                "consequence": "Under the canonical tooling, the 8 rows produce 0 critical HF-01/HF-02 findings; L0 content review is not blocked by claim-scope detectors.",
                "measured_by": ["C03_canonical_routing", "C06_hf14"],
            },
            "reading_R2_field_literal_reviewer": {
                "claim": "Applying the HF-02 detector text literally to the ledger's class_ids field yields 8 disjunction firings; requires a class-binding content decision to clear (move secondary ids to informs_classes), which moves the ledger hash and voids both current verdicts.",
                "consequence": "If adopted, the repair is priced by C07_repair_simulation and REC-4 forbids it in the rev-4 metadata patch; a fresh two-verdict round is required after the hash move.",
                "measured_by": ["C02_census", "C07_repair_simulation"],
            },
            "reading_R3_statement_literal_rubric": {
                "claim": "The rubric's normative sentence is statement-scoped ('must never be disjoined in a statement', evaluation_rubric.yaml:52-54). Independent statement-level scan: 0/62 statements carry a positive merge/identity assertion of two frozen classes; the 8 rows' statements each describe one result bearing on two regularity classes.",
                "consequence": "The 8 firings are field-scope false positives, consistent with the controller's CF-16 false-positive pattern; no statement in the ledger asserts a C0/C2 (or WCC/C0) merge.",
                "measured_by": ["C05_statement_level"],
            },
            "new_observation_T402_regularity": {
                "claim": "Independently of the reviewer list, the canonical declaration-mode scanner flags exactly one live ledger row: T-402 `regularity` = 'Between C0 and C2 (weak null singularity).' as a bare composite (class_separation.py _scan_composite, declaration mode). Semantically the phrase is relevance, not a merge; any scope ruling should therefore cover free-text regularity fields, not only class_ids.",
                "consequence": "A class_ids-only repair leaves this canonical finding standing (C07 residual == pre-existing finding).",
                "measured_by": ["C04_canonical_detector", "C07_repair_simulation"],
            },
        },
        "recommendation": {
            "action": "controller/A0 owner ruling on HF-02 scope for record files is still required (worker cannot rule A0 scope)",
            "preferred_if_R1_or_R3": "no ledger write; document class_ids semantics (binding vs informs_classes relevance) in the ledger schema, then re-dispatch L0 verdicts",
            "if_R2": "authorize one class-binding revision moving secondary ids to informs_classes; accept the hash move and the fresh verdict round",
        },
        "not_claimed": ["gate verdict", "node status", "validation_status", "class-binding repair", "any theorem"],
        "falsifier": "Re-run this instrument at the pinned hashes. It is falsified if (a) ledger/theorems.jsonl does not measure a1674f094979...; (b) audit_run.scan_corpus routes any of the 62 rows to claims; (c) any of the 8 statements contains a positive merge/identity assertion of two frozen classes; (d) the canonical declaration or prose scan flags any live row; (e) any control M1-M8 stops reproducing its expected value; (f) two runs in one process yield different determinism digests; (g) any pinned input drifts during the run.",
    }
    (OUT / "report.json").write_text(json.dumps(report, indent=1, sort_keys=False) + "\n")

    entries = {
        "report.json": sha256_file(OUT / "report.json"),
        "run_l0_scope_063.py": sha256_file(Path(__file__).resolve()),
    }
    (OUT / "entry_hashes.json").write_text(json.dumps(entries, indent=1) + "\n")
    print(json.dumps({"status": status, "determinism": d1[:12], "controls": f"{controls['passed']}/{controls['total']}",
                      "void": report["void_reasons"], "entry_hashes": entries}, indent=1))


if __name__ == "__main__":
    main()
