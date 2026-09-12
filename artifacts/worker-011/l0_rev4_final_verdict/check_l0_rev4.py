#!/usr/bin/env python3
"""W011-L0-REV4-FINAL-VERDICT-02 instrument.

Independent, read-only, deterministic verdict on the L0 literature ledger
(`ledger/theorems.jsonl`) at the announced FINAL rev-4 bytes, against the
pinned rubric's G-LIT criteria and the hard-failure detectors, scoped to the
class binding and honesty fields.  It is written from scratch (no import of
any other worker's checker) and pins every input by sha256.

Fail-closed: any pin mismatch (input moved) exits 3 and reports UNMEASURED;
it never writes into a canonical artifact.

Run:  python3 artifacts/worker-011/l0_rev4_final_verdict/check_l0_rev4.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import yaml
except Exception as exc:  # pragma: no cover
    print(json.dumps({"fatal": "pyyaml unavailable", "error": str(exc)}))
    sys.exit(2)

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
OUT = HERE.parent
CST = timezone(timedelta(hours=8))

FROZEN = (
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
)
FROZEN_SET = set(FROZEN)
CONCLUSION_TYPES = {
    "theorem", "conditional_theorem", "stability_result", "counterexample",
    "numerical_evidence", "formal_model", "open_problem",
}

# Expected pins (measured before the run; re-measured after to detect drift).
PINS = {
    "ledger/theorems.jsonl":
        "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28",
    "ledger/citation_audit.csv":
        "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9",
    "evaluation_rubric.yaml":
        "d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885",
    "artifacts/literature/registry.jsonl":
        "ea02d1943fda50e5e1c7ce10fe2a1cd6e7784a2c9f2467c7cb8597c63442652d",
}

# Quantity patterns for the G-LIT criterion "quantitative claims (rates,
# exponents, codimension) carry a quantity_check".  Deliberately narrow and
# auditable.  NARROW = an asserted bound/rate/codimension; the extra entries in
# FULL also match a bare regularity-class mention (C^2, L^2_loc), which is the
# theorem's setting rather than a claimed quantity; the two tiers are reported
# separately so the reader can see the sensitivity band.
NARROW_PATTERNS = [
    (r"\bs\s*[<>=]\s*[0-9]", "exponent inequality (s > n)"),
    (r"(?i)\bcodim(ension)?\b", "codimension"),
    (r"(?i)\bexponent\b", "exponent word"),
    (r"(?i)\bdecay rate\b|\bprice'?s?[- ]law\b", "rate"),
    (r"\b\d+\s*pp\.", "page count as a stated quantity"),
]
FULL_PATTERNS = NARROW_PATTERNS + [
    (r"[A-Za-z]\^\{?[0-9]", "regularity exponent (X^n / X^{...})"),
    (r"\b[LCHW]\^s\b", "symbolic exponent L^s"),
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


class Unmeasured(Exception):
    pass


def main() -> int:
    raw: dict[str, bytes] = {}
    pins_before: dict[str, str] = {}
    for rel, expected in PINS.items():
        p = ROOT / rel
        if not p.is_file():
            print(json.dumps({"verdict": "UNMEASURED", "reason": f"missing {rel}"}))
            return 3
        b = p.read_bytes()
        raw[rel] = b
        got = hashlib.sha256(b).hexdigest()
        pins_before[rel] = got
        if got != expected:
            print(json.dumps({"verdict": "UNMEASURED", "reason": f"pin mismatch {rel}",
                              "expected": expected, "measured": got}))
            return 3

    rubric = yaml.safe_load(raw["evaluation_rubric.yaml"].decode())
    rows = [json.loads(l) for l in raw["ledger/theorems.jsonl"].decode().splitlines() if l.strip()]
    audit = list(csv.DictReader(raw["ledger/citation_audit.csv"].decode().splitlines()))
    registry = [json.loads(l) for l in raw["artifacts/literature/registry.jsonl"].decode().splitlines() if l.strip()]

    checks: list[dict] = []
    controls: list[dict] = []

    def check(cid, name, ok, observed, expected, falsifier, firing=None, evidence=None):
        checks.append({
            "id": cid, "name": name, "status": "PASS" if ok else "FAIL",
            "expected": expected, "observed": observed,
            "firing_rows": firing or [], "falsifier": falsifier,
            "evidence": evidence or [],
        })
        return ok

    # ---- K01 structure -------------------------------------------------
    ids = [r.get("theorem_id") for r in rows]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    check("K01", "ledger parses as JSONL; 62 rows; unique theorem_id",
          len(rows) == 62 and not dup,
          {"rows": len(rows), "duplicate_ids": dup}, {"rows": 62, "duplicate_ids": []},
          "A parse error, a row count != 62, or a duplicate theorem_id at the pinned bytes.",
          evidence=["ledger/theorems.jsonl#a1674f094979"])

    required = ("theorem_id", "statement_exact", "source_ids", "assumptions",
                "conclusion_type", "does_not_imply", "unresolved", "falsifiers",
                "topology", "regularity", "genericity", "content_status",
                "review_status", "acceptance_authority")
    missing = {r.get("theorem_id"): [k for k in required if k not in r] for r in rows}
    missing = {k: v for k, v in missing.items() if v}
    check("K02", "every row carries the required literature-row fields",
          not missing, missing, {},
          "Any row missing a required field; the list is the falsifier set.",
          firing=sorted(missing))

    # ---- K03 frozen class tokens in class-bearing fields ----------------
    tok_re = re.compile(r"\bAF-[A-Z0-9-]+\b")
    class_keys = ("class_ids", "informs_classes")
    foreign: dict[str, list[str]] = {}
    prose_mentions: dict[str, list[str]] = {}
    for r in rows:
        for k in class_keys:
            for t in (r.get(k) or []):
                if t not in FROZEN_SET:
                    foreign.setdefault(r["theorem_id"], []).append(t)
        blob = json.dumps(r, ensure_ascii=False)
        bad_prose = sorted({t for t in tok_re.findall(blob) if t not in FROZEN_SET})
        if bad_prose:
            prose_mentions[r["theorem_id"]] = bad_prose
    check("K03", "class-bearing fields contain only the four frozen class tokens",
          not foreign, {"foreign_tokens": foreign, "prose_prefix_mentions": prose_mentions}, {},
          "Any token outside the frozen four inside class_ids or informs_classes. Prose "
          "prefix mentions (e.g. 'AF-SCC-C2' as shorthand) are recorded, not counted.",
          firing=sorted(foreign))

    # ---- K04 HF-02 disjunction (literal census) ------------------------
    disj = [r["theorem_id"] for r in rows
            if len([t for t in (r.get("class_ids") or []) if t in FROZEN_SET]) > 1]
    check("K04", "HF-02 literal census: rows with >1 frozen token in class_ids",
          True, {"count": len(disj), "rows": disj}, {"count": 0},
          "Falsified as a *finding* only by an audit-lead scope ruling that the "
          "HF-02 'disjunction of class_ids' clause is claim/schema-scoped, or by a "
          "ledger revision that removes the multi-token arrays.",
          firing=disj,
          evidence=["evaluation_rubric.yaml#d748a9e3574e hard_failures[HF-02]"])

    # ---- K05 class scope recorded (soft census) ------------------------
    unbound = [r["theorem_id"] for r in rows
               if not (r.get("class_ids") or r.get("informs_classes"))]
    check("K05", "class scope recorded per row (soft census; class-external rows allowed)",
          True, {"count": len(unbound), "rows": unbound}, {"count": len(unbound)},
          "Soft finding only: if a row with no class token is in fact class-internal, "
          "the L0 assignment's per-row class binding is unmet for that row.",
          firing=unbound)

    # ---- K06 HF-14 literal census --------------------------------------
    support_keys = ("author_asserts_supports", "supports_claim", "claims_theorem_status")
    hf14 = []
    for r in rows:
        asserts = any(r.get(k) is True for k in support_keys)
        has_verdict = bool(r.get("reviewer_verdict") or r.get("review_verdict")
                           or r.get("artifact_refs") or r.get("artifact_sha256"))
        has_reviewer = bool(r.get("reviewer"))
        if asserts and not has_verdict and not has_reviewer:
            hf14.append(r["theorem_id"])
    check("K06", "HF-14 literal census: self-certified support, no reviewer verdict, no artifact hash",
          True, {"count": len(hf14), "of_rows": len(rows), "rows": hf14}, {"count": 0},
          "Discharged if the audit lead rules HF-14 claim-scoped (its detector text "
          "names ledger records explicitly), or if rows carrying a truthy support "
          "assertion also carry an independent reviewer verdict and an artifact hash.",
          firing=hf14,
          evidence=["evaluation_rubric.yaml#d748a9e3574e hard_failures[HF-14]"])

    # ---- K07 HF-04 / G-LIT quantity_check (three-tier census) ----------
    def qty_hits(r, fields, patterns=FULL_PATTERNS):
        text = " ".join(str(r.get(k, "")) for k in fields)
        return sorted({why for pat, why in patterns if re.search(pat, text)})

    q_narrow, q_rows, q_broad = [], [], []
    for r in rows:
        if r.get("quantity_check"):
            continue
        if qty_hits(r, ("statement_exact", "label"), NARROW_PATTERNS):
            q_narrow.append(r["theorem_id"])
        if qty_hits(r, ("statement_exact", "label")):
            q_rows.append({"row": r["theorem_id"],
                           "patterns": qty_hits(r, ("statement_exact", "label"))})
        if qty_hits(r, ("statement_exact", "label", "regularity")):
            q_broad.append(r["theorem_id"])
    any_qc = any("quantity_check" in r for r in rows)
    check("K07", "HF-04 / G-LIT criterion 4: quantity-bearing rows carry quantity_check",
          True,
          {"tierC_asserted_bound_or_rate_rows": len(q_narrow),
           "tierA_statement_or_label_rows": len(q_rows),
           "tierB_incl_regularity_rows": len(q_broad),
           "any_quantity_check_field": any_qc, "tierC_rows": q_narrow,
           "tierA_detail": q_rows},
          {"tierC_asserted_bound_or_rate_rows": 0, "any_quantity_check_field": True},
          "Discharged if a quantity_check field or evidence ref exists for each "
          "quantity-bearing row, or the audit lead rules G-LIT criterion 4 "
          "claim-scoped. Tier C counts asserted bounds/rates/codimensions; tier A also "
          "counts bare regularity-class mentions; tier B adds the regularity field.",
          firing=q_narrow,
          evidence=["evaluation_rubric.yaml#d748a9e3574e gates[G-LIT].criteria[3]",
                    "evaluation_rubric.yaml#d748a9e3574e hard_failures[HF-04]"])

    # ---- K08 HF-01 literal census --------------------------------------
    thm = [r["theorem_id"] for r in rows
           if r.get("conclusion_type") == "theorem" and not r.get("artifact_refs")]
    check("K08", "HF-01 literal census: conclusion_type=theorem with no artifact_refs",
          True, {"count": len(thm), "rows": thm}, {"count": 0},
          "Discharged if the audit lead rules HF-01 claim-scoped (detector text begins "
          "'claim.conclusion_type'), or if theorem rows gain artifact_refs.",
          firing=thm,
          evidence=["evaluation_rubric.yaml#d748a9e3574e hard_failures[HF-01]"])

    # ---- K09 citation resolution ---------------------------------------
    used = sorted({s for r in rows for s in (r.get("source_ids") or [])})
    have = {a["citation_id"] for a in audit}
    absent = [s for s in used if s not in have]
    bad_res = [a["citation_id"] for a in audit
               if a.get("resolver_result") not in ("resolved",)
               or a.get("verdict") not in ("verified",)]
    check("K09", "every used source resolves in citation_audit.csv with resolver_result=resolved",
          not absent and not bad_res,
          {"used_sources": len(used), "absent": absent, "non_resolved": bad_res},
          {"used_sources": len(used), "absent": [], "non_resolved": []},
          "A used source_id absent from the audit, or any audit row not resolved/verified.",
          firing=absent + bad_res)

    # ---- K10 source scope fields (G-LIT criterion 3) --------------------
    scope_words = ("matter", "lambda", "cosmolog", "dimension", "symmetr", "formulation")
    audit_cols = {c.lower() for c in audit[0].keys()} if audit else set()
    reg_cols = {c.lower() for r in registry for c in r.keys()}
    audit_scope = sorted(c for c in audit_cols if any(w in c for w in scope_words))
    reg_scope = sorted(c for c in reg_cols if any(w in c for w in scope_words))
    check("K10", "G-LIT criterion 3: matter/Lambda/dimension/symmetry/formulation recorded per source",
          bool(audit_scope or reg_scope),
          {"audit_scope_columns": audit_scope, "registry_scope_columns": reg_scope},
          {"audit_scope_columns": ">=1", "registry_scope_columns": ">=1"},
          "Discharged if any pinned source registry/audit column explicitly records "
          "matter model, Lambda, dimension, symmetry or formulation; the class_mapping "
          "column alone does not record the source's scope.",
          evidence=["evaluation_rubric.yaml#d748a9e3574e gates[G-LIT].criteria[2]",
                    "evaluation_rubric.yaml#d748a9e3574e verifiers.literature.checks"])

    # ---- K11 honesty fields --------------------------------------------
    no_unres = [r["theorem_id"] for r in rows if not r.get("unresolved")]
    spoof = [r["theorem_id"] for r in rows
             if r.get("review_status") not in ("not_independently_reviewed",)
             and not r.get("reviewer_verdict")]
    check("K11", "honesty fields: non-empty unresolved[]; no unbacked review claim",
          not no_unres and not spoof,
          {"empty_unresolved": no_unres, "unbacked_review_claim": spoof,
           "review_status_values": sorted({r.get("review_status") for r in rows})},
          {"empty_unresolved": [], "unbacked_review_claim": []},
          "Any row with an empty unresolved list, or a review_status claiming review "
          "without a reviewer verdict field.",
          firing=no_unres + spoof)

    # ---- K12 conclusion_type vocabulary ---------------------------------
    bad_ct = sorted({r["theorem_id"] for r in rows
                     if r.get("conclusion_type") not in CONCLUSION_TYPES})
    check("K12", "conclusion_type vocabulary (schemas.py claim vocabulary)",
          not bad_ct, bad_ct, [],
          "Any conclusion_type outside the seven-value vocabulary.",
          firing=bad_ct)

    # ---- planted controls (in-memory mutants only) ----------------------
    def mutate_foreign(rs):
        rs[0]["class_ids"] = ["AF-NEW-CLASS"]
        return rs

    def mutate_dup(rs):
        rs[1]["theorem_id"] = rs[0]["theorem_id"]
        return rs

    def mutate_unres(rs):
        rs[2]["unresolved"] = []
        return rs

    def mutate_qc(rs):
        for r in rs:
            if qty_hits(r, ("statement_exact", "label")):
                r["quantity_check"] = "present"
                break
        return rs

    def mutate_support(rs):
        for r in rs:
            r["author_asserts_supports"] = False
        return rs

    def mutate_unresolve_audit(au):
        au[0]["resolver_result"] = "unresolved"
        return au

    def mutate_review_spoof(rs):
        rs[3]["review_status"] = "independently_reviewed"
        return rs

    import copy as _copy
    ctl_specs = [
        ("CTL-1", "foreign AF-* token in class_ids fires K03", mutate_foreign, "K03"),
        ("CTL-2", "duplicate theorem_id fires K01", mutate_dup, "K01"),
        ("CTL-3", "empty unresolved[] fires K11", mutate_unres, "K11"),
        ("CTL-4", "adding quantity_check clears one K07 row", mutate_qc, "K07"),
        ("CTL-5", "clearing all support assertions shrinks K06 to 0", mutate_support, "K06"),
        ("CTL-6", "unresolved audit row fires K09", mutate_unresolve_audit, "K09"),
        ("CTL-7", "review_status spoof fires K11", mutate_review_spoof, "K11"),
    ]
    for cid, desc, fn, target in ctl_specs:
        if target == "K09":
            au2 = fn(_copy.deepcopy(audit))
            fired = bool([a["citation_id"] for a in au2
                          if a.get("resolver_result") not in ("resolved",)
                          or a.get("verdict") not in ("verified",)])
        else:
            rs2 = fn(_copy.deepcopy(rows))
            if target == "K03":
                fired = any(
                    t not in FROZEN_SET
                    for r in rs2 for t in tok_re.findall(json.dumps(r, ensure_ascii=False)))
            elif target == "K01":
                i2 = [r.get("theorem_id") for r in rs2]
                fired = len(i2) != 62 or len(set(i2)) != len(i2)
            elif target == "K11":
                fired = any(not r.get("unresolved") for r in rs2) or any(
                    r.get("review_status") not in ("not_independently_reviewed",)
                    and not r.get("reviewer_verdict") for r in rs2)
            elif target == "K07":
                q2 = [r for r in rs2 if qty_hits(r, ("statement_exact", "label"))
                      and not r.get("quantity_check")]
                fired = len(q2) < len(q_rows)
            elif target == "K06":
                h2 = [r["theorem_id"] for r in rs2
                      if any(r.get(k) is True for k in support_keys)
                      and not (r.get("reviewer_verdict") or r.get("review_verdict")
                               or r.get("artifact_refs") or r.get("artifact_sha256"))
                      and not r.get("reviewer")]
                fired = len(h2) < len(hf14)
            else:
                fired = False
        controls.append({"id": cid, "mutation": desc, "detected": bool(fired)})

    all_controls_detected = all(c["detected"] for c in controls)

    # ---- drift re-hash ---------------------------------------------------
    pins_after = {rel: sha256_file(ROOT / rel) for rel in PINS}
    drift = {rel: {"before": pins_before[rel], "after": pins_after[rel]}
             for rel in PINS if pins_before[rel] != pins_after[rel]}

    # ---- verdict ---------------------------------------------------------
    hard = []
    if hf14:
        hard.append({
            "id": "V-011-L0-01", "hard_failure": "HF-14", "severity": "critical",
            "finding": f"{len(hf14)} of {len(rows)} ledger rows set a truthy support "
                       f"assertion (author_asserts_supports) with no independent reviewer "
                       f"verdict field and no artifact hash; review_status is "
                       f"'not_independently_reviewed' on all {len(rows)} rows. HF-14's own "
                       f"detector text names ledger records.",
            "rows": hf14,
            "falsifier": "Produce one row whose support assertion is backed by an "
                         "independent reviewer verdict field plus an artifact hash, or an "
                         "audit-lead scope ruling that HF-14 does not apply to ledger rows.",
        })
    if q_narrow:
        hard.append({
            "id": "V-011-L0-02", "hard_failure": "HF-04", "severity": "major",
            "finding": f"{len(q_narrow)} rows assert a bound/rate/codimension in "
                       f"statement_exact or label and no quantity_check field exists "
                       f"anywhere in the ledger (sensitivity: {len(q_rows)} rows if bare "
                       f"regularity-class mentions count, {len(q_broad)} if the regularity "
                       f"field is also counted); G-LIT criterion 4 and "
                       f"verifiers.literature.checks require a quantity_check for "
                       f"quantitative claims.",
            "rows": q_narrow,
            "tierA_rows_if_regularity_mentions_counted": [d["row"] for d in q_rows],
            "tierB_rows_if_regularity_counted": q_broad,
            "falsifier": "Add a quantity_check (field or evidence ref) to each listed row "
                         "and re-run; or rule G-LIT criterion 4 claim-scoped; or show that "
                         "the listed statements carry no quantity under the rubric's "
                         "rate/exponent/codimension reading.",
        })
    if not (audit_scope or reg_scope):
        hard.append({
            "id": "V-011-L0-03", "hard_failure": None, "severity": "blocking-criterion",
            "finding": "G-LIT criterion 3 ('matter/Lambda/dimension/symmetry of the source "
                       "explicitly recorded') is not met at either pinned source artifact: "
                       "registry.jsonl and citation_audit.csv record class_mapping only.",
            "rows": [],
            "falsifier": "Show a pinned column carrying matter/Lambda/dimension/symmetry/"
                         "formulation per source; class_mapping alone does not count.",
        })
    soft = []
    if disj:
        soft.append({
            "id": "V-011-L0-04", "hard_failure": "HF-02 (scope-disputed)",
            "finding": f"{len(disj)} rows carry >1 frozen token in class_ids. Literal HF-02 "
                       f"firing; the ledger's own does_not_imply fields disclaim the union "
                       f"readings, and a tested staged repair exists "
                       f"(artifacts/worker-025/l0_hf02_staged/staged/theorems.hf02-staged.jsonl"
                       f"#b3ab6a1a6357). The accept at this hash does not discharge this.",
            "rows": disj,
            "falsifier": "An audit-lead scope ruling that the HF-02 disjunction clause is "
                         "claim/schema-scoped; or publish the staged repair and re-review.",
        })
    if thm:
        soft.append({
            "id": "V-011-L0-05", "hard_failure": "HF-01 (scope-disputed)",
            "finding": f"{len(thm)} rows use conclusion_type=theorem and the ledger row "
                       f"schema has no artifact_refs field (field absent from all 62 rows). "
                       f"Detector text begins 'claim.conclusion_type', so a claim-scoped "
                       f"reading is defensible; recorded, not silently counted.",
            "rows": thm,
            "falsifier": "An audit-lead ruling either way; if ledger-scoped, theorem rows "
                         "need artifact_refs.",
        })
    if unbound:
        soft.append({
            "id": "V-011-L0-06", "hard_failure": None, "severity": "minor",
            "finding": f"{len(unbound)} rows carry no class token in class_ids or "
                       f"informs_classes; several are class-external by design (e.g. dust "
                       f"counterexamples), so this is recorded as a scope note, not a hard "
                       f"failure.",
            "rows": unbound,
            "falsifier": "Show a listed row that is class-internal under the frozen taxonomy.",
        })

    verdict = "revise" if (hard or soft) else "accept"
    if not all_controls_detected:
        verdict = "inconclusive"

    report = {
        "task_id": "W011-L0-REV4-FINAL-VERDICT-02",
        "generated_at": now(),
        "instrument": "artifacts/worker-011/l0_rev4_final_verdict/check_l0_rev4.py",
        "scope": "Independent blind G-LIT/L0 verdict at the announced rev-4 ledger bytes: "
                 "identity, class binding, honesty fields, citation resolution, rubric "
                 "hard-failure literal censuses, and the task-type scope of each detector.",
        "blind": "No prior L0 verdict at these bytes was authored by worker-011; the prior "
                 "worker-011 L0 verdict bound the voided ce42d205 bytes and is superseded.",
        "pins_before": pins_before,
        "pins_after": pins_after,
        "drift": drift,
        "rubric_quotes": {
            "G-LIT criteria": rubric["gates"][1]["criteria"],
            "literature verifier checks": rubric["verifiers"]["literature"]["checks"],
            "schema_formulation verifier checks": rubric["verifiers"]["schema_formulation"]["checks"],
            "HF-01": rubric["hard_failures"][0],
            "HF-02": rubric["hard_failures"][1],
            "HF-04": rubric["hard_failures"][3],
            "HF-14": [h for h in rubric["hard_failures"] if h["id"] == "HF-14"][0],
        },
        "checks": checks,
        "controls": controls,
        "all_controls_detected": all_controls_detected,
        "hard_findings": hard,
        "soft_findings": soft,
        "counts": {
            "rows": len(rows), "theorem_rows": len(thm), "hf14_rows": len(hf14),
            "quantity_rows_without_check_tierC": len(q_narrow),
            "quantity_rows_without_check_tierA": len(q_rows),
            "quantity_rows_without_check_tierB": len(q_broad),
            "disjunction_rows": len(disj),
            "unbound_rows": len(unbound), "used_sources": len(used),
            "audit_rows": len(audit), "registry_rows": len(registry),
        },
        "verdict": verdict,
        "score": 3.0 if verdict == "revise" else (4.0 if verdict == "accept" else 2.0),
        "verdict_scope": "G-LIT criteria at the pinned bytes plus the class-binding and "
                         "honesty fields. Excludes per-row mathematical entailment and live "
                         "re-fetch (documented blind spots).",
        "documented_blind_spots": [
            "No per-row semantic entailment check that a quoted source entails the row's "
            "statement.",
            "No live re-fetch: resolution is measured against the pinned citation_audit.csv.",
            "No judgement on the mathematical truth or scope of any individual theorem row.",
        ],
        "falsifier": "Re-run this instrument at the same four pins: any check that flips, "
                     "any control not detected, or any pin drift (ledger, audit, rubric, "
                     "registry) falsifies the report. The HF-14/HF-04 findings are "
                     "discharged only by the stated scope rulings or by a repaired ledger.",
        "non_claims": [
            "Not a gate verdict; a worker cannot set a gate verdict or a node status.",
            "Not a theorem claim.",
            "Does not adjudicate the HF-02/HF-01 scope question; it exposes the firing sets "
            "for the audit lead's ruling.",
        ],
    }

    run_log = {
        "verdict": verdict, "score": report["score"],
        "checks": {c["id"]: c["status"] for c in checks},
        "controls_detected": f"{sum(1 for c in controls if c['detected'])}/{len(controls)}",
        "hard": [h["id"] for h in hard], "soft": [s["id"] for s in soft],
        "drift": drift,
    }
    (OUT / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    (OUT / "run.log").write_text(json.dumps(run_log, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(run_log, indent=1, ensure_ascii=False))
    return 0 if verdict != "inconclusive" else 2


if __name__ == "__main__":
    raise SystemExit(main())
