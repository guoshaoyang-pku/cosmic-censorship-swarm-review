#!/usr/bin/env python3
"""
W009-L1-VACUUM-CLASS-BINDING-CENSUS-01 -- reproducibility verifier.

Read-only.  Re-runs the census from the four pinned files and checks:
  D1  census_digest recomputes to the hash recorded in the record;
  D2  per-row verdicts and counts match the record;
  D3  every decisive quote is a verbatim substring of the field it is
      attributed to, and its recorded sha256 matches;
  D4  the four input files still hash to their pins after the check;
  D5  all controls still pass;
  D6  the CSV companion has one group per (row, bound class).

Exit 0 = PASS, 1 = FAIL.  --recheck is accepted for the record's reproduce
command; the tool is always read-only.
"""
import argparse
import csv
import hashlib
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
CENSUS_PY = os.path.join(HERE, "census_vacuum_binding_worker-009.py")
RECORD = os.path.join(HERE, "verification_vacuum_binding_worker-009.json")
CSVOUT = os.path.join(HERE, "census_vacuum_binding_worker-009.csv")


def load_module():
    spec = importlib.util.spec_from_file_location("w009_census", CENSUS_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sha256_text(t):
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--recheck", action="store_true")
    args = ap.parse_args()

    mod = load_module()
    built = mod.build()
    rec = json.load(open(RECORD, encoding="utf-8"))
    checks = []

    def chk(name, ok, detail):
        checks.append({"check": name, "passed": bool(ok), "detail": detail})

    chk("D1_census_digest", built["census_digest"] == rec["census_digest"],
        "recomputed %s recorded %s" % (built["census_digest"][:16], rec["census_digest"][:16]))
    chk("D2_counts", built["counts"] == rec["counts"],
        "counts equal" if built["counts"] == rec["counts"] else "count mismatch")

    recorded = {r["citation_id"]: r for r in rec["rows"]}
    recomputed = {r["citation_id"]: r for r in built["out_rows"]}
    chk("D2_row_set", set(recorded) == set(recomputed),
        "%d rows recorded, %d recomputed" % (len(recorded), len(recomputed)))
    vmis = [cid for cid in recorded if cid in recomputed
            and recorded[cid]["row_verdict"] != recomputed[cid]["row_verdict"]]
    chk("D2_verdicts", not vmis, "verdict mismatches: %s" % (vmis or "none"))

    # D3: every decisive quote binds to the pinned field bytes.
    raw_rows = {r["citation_id"]: r for r in built["rows"]}
    theorems = {}
    for line in built["raw"]["ledger/theorems.jsonl"].splitlines():
        if line.strip():
            d = json.loads(line)
            theorems[d["theorem_id"]] = d
    quote_fail = []
    n_quotes = 0
    for r in rec["rows"]:
        for p in r["per_class"]:
            for s in p["decisive_statements"]:
                n_quotes += 1
                tier = s["tier"]
                if tier.startswith("T1") or tier.startswith("T3"):
                    field_vals = theorems.get(s["record"], {}).get(s["field"])
                    pool = " || ".join(field_vals) if isinstance(field_vals, list) else str(field_vals)
                elif tier.startswith("T2"):
                    pool = raw_rows.get(r["citation_id"], {}).get(s["field"], "")
                elif tier.startswith("L_"):
                    pool = str(mod.dig(built["c0"], s["field"]))
                else:
                    pool = ""
                if s["quote"] not in pool:
                    quote_fail.append("%s/%s/%s: quote not in %s" % (r["citation_id"], p["class_id"], s["record"], s["field"]))
                if sha256_text(s["quote"]) != s["quote_sha256"]:
                    quote_fail.append("%s/%s: quote_sha256 mismatch" % (r["citation_id"], p["class_id"]))
    chk("D3_quote_binding", not quote_fail, "%d quotes checked; %s" % (n_quotes, quote_fail[:4] or "all bind"))

    # D4: pins unmoved after the read-only check.
    post = {}
    for rel in mod.PINS:
        path = {"ledger/citation_audit.csv": mod.CITATION, "ledger/theorems.jsonl": mod.THEOREMS,
                "schemas/af_scc_c0_vacuum.yaml": mod.SCHEMA_C0,
                "schemas/af_scc_c2_vacuum.yaml": mod.SCHEMA_C2}[rel]
        post[rel] = hashlib.sha256(open(path, "rb").read()).hexdigest()
    chk("D4_pins_stable", post == mod.PINS,
        "all four pins unchanged" if post == mod.PINS else "PIN MOVED: %s" % post)

    # D5: controls.
    ctrl_ok = all(c["passed"] for c in built["controls"]) and built["controls"] == rec["controls"]
    chk("D5_controls", ctrl_ok,
        "%d/%d controls pass%s" % (sum(1 for c in built["controls"] if c["passed"]), len(built["controls"]),
                                   "" if built["controls"] == rec["controls"] else " (control record mismatch)"))

    # D6: CSV one group per (row, class).
    with open(CSVOUT, newline="", encoding="utf-8") as fh:
        crows = list(csv.DictReader(fh))
    groups = {(r["citation_id"], r["class_token"]) for r in crows}
    expect = {(r["citation_id"], p["class_id"]) for r in rec["rows"] for p in r["per_class"]}
    chk("D6_csv_groups", groups == expect, "%d csv groups vs %d expected" % (len(groups), len(expect)))

    allok = all(c["passed"] for c in checks)
    print(json.dumps({"artifact": "verify_vacuum_binding_worker-009", "verdict": "PASS" if allok else "FAIL",
                      "checks": checks, "census_digest": built["census_digest"],
                      "quotes_checked": n_quotes}, ensure_ascii=False, indent=1))
    return 0 if allok else 1


if __name__ == "__main__":
    sys.exit(main())
