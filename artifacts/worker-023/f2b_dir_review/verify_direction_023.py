#!/usr/bin/env python3
"""Independent verifier for W023-F2B-DIR-REVIEW-01.

Re-derives every load-bearing assertion of reproduce_023.py from raw bytes with
separate code paths (system `patch` for the reconstruction, rank-based direction
rule, fresh regexes, fresh graph parser) and re-executes the frozen controls.
Imports nothing from the runner.

    python3 verify_direction_023.py     # writes verification.json; exit 0/1/2
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
EV = HERE / "evidence"
TZ = timezone(timedelta(hours=8))
NOW = lambda: datetime.now(TZ).isoformat(timespec="seconds")

V1_FILE = HERE / "proposed_af_scc_c0_vacuum_v1_066.yaml"
V2_FILE = HERE / "proposed_af_scc_c0_vacuum_v2_corrected.yaml"
CAND_066_SHA = "84b5d3fa29a677ad157b924675bb5a9c08281395920be0221535465a5da44b40"
LIVE_SHA = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"
COMPOSED_SHA = "48cadb72e507cfcbc469f6519fcc0294bb83f083cc1733521610ff63e5f3c38a"

A_RE = re.compile(r"H2_loc-inextendibility\s+ENTAILS\s+this class's conclusion")
B_RE = re.compile(r"this class's conclusion\s+ENTAILS\s+H2_loc-inextendibility")
RANK = {"C2": 0, "C11": 1, "H2loc": 2, "C0": 3}


def h(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def checks_of(doc_path: Path = None):
    return json.loads((HERE / "report.json").read_text())


def edges_from(doc):
    il = doc.get("implication_ledger") or {}
    return {(r["from"].strip(), r["to"].strip())
            for r in il.get("one_way_entailments", []) if r.get("relation") == "entails"}


def tc(edges):
    cl, changed = set(edges), True
    while changed:
        changed = False
        for a, b in list(cl):
            for c, d in list(cl):
                if b == c and (a, d) not in cl:
                    cl.add((a, d)); changed = True
    return cl


def main() -> int:
    import yaml
    R = []
    def rec(cid, got, want, detail=""):
        R.append({"id": cid, "observed": got, "expected": want,
                  "pass": got == want, "detail": detail})

    live_b = (ROOT / "schemas/af_scc_c0_vacuum.yaml").read_bytes()
    c2_b = (ROOT / "schemas/af_scc_c2_vacuum.yaml").read_bytes()
    f1_b = (ROOT / "schemas/af_wcc_vacuum.yaml").read_bytes()
    composed_b = (ROOT / "artifacts/worker-044/f2b_live_closure_01/sandbox/schemas/af_scc_c0_vacuum.yaml").read_bytes()
    w008_b = (ROOT / "artifacts/worker-008/f2b_rev11_dualrepair/candidate_rev12/af_scc_c0_vacuum.yaml").read_bytes()
    patch_b = (ROOT / "artifacts/worker-066/f2b_repair_prereg/proposed_patch.diff").read_bytes()
    v1_b = V1_FILE.read_bytes()
    v2_b = V2_FILE.read_bytes()

    rec("V0_live_pin", h(live_b), LIVE_SHA)
    rec("V1_runner_v1_matches_declared_066", h(v1_b), CAND_066_SHA)

    # --- independent reconstruction via the system patch tool
    tmp = EV / "verify_patch_tmp"
    if tmp.exists():
        shutil.rmtree(tmp)
    (tmp / "schemas").mkdir(parents=True)
    shutil.copyfile(ROOT / "schemas/af_scc_c0_vacuum.yaml", tmp / "schemas/af_scc_c0_vacuum.yaml")
    pr = subprocess.run(["patch", "-p1", "--no-backup-if-mismatch"],
                        input=patch_b, cwd=tmp, capture_output=True)
    patched = (tmp / "schemas/af_scc_c0_vacuum.yaml").read_bytes()
    rec("V2_system_patch_applies", pr.returncode, 0, pr.stdout.decode()[:120].replace("\n", " "))
    rec("V3_system_patch_hash_equals_066", h(patched), CAND_066_SHA)
    rec("V4_system_patch_equals_runner_v1", patched == v1_b, True)

    doc = {n: yaml.safe_load(b.decode()) for n, b in
           (("live", live_b), ("v1", v1_b), ("v2", v2_b), ("c2", c2_b),
            ("f1", f1_b), ("composed", composed_b), ("w008", w008_b))}

    # --- independent rank-based direction rule
    def ranks(d):
        s = (d.get("implication_ledger") or {}).get("extension_class_containment", "")
        if "E_C2 subset of" in s or "E_C0 contains" in s:
            return dict(RANK)
        return {}

    def form_of(text):
        return "A" if A_RE.search(text) else ("B" if B_RE.search(text) else None)

    def valid(form, d):
        ct = (d.get("conclusion") or {}).get("conclusion_type")
        tok = {"scc_c0_future_inextendibility": "C0",
               "scc_c2_future_inextendibility": "C2"}.get(ct)
        rk = ranks(d)
        if tok is None or not rk:
            return None
        if form == "A":                        # H2loc-inext => concl: need E_concl subset E_H2loc
            return rk[tok] <= rk["H2loc"]
        if form == "B":                        # concl => H2loc-inext: need E_H2loc subset E_concl
            return rk["H2loc"] <= rk[tok]
        return None

    def slot_form(d, raw):
        for i, s in enumerate((d.get("regularity") or {}).get("must_not_conflate", [])):
            f = form_of(s)
            if f:
                return i, f, s
        return None, None, None

    for name, want_form, want_valid in (("v1", "A", False), ("composed", "A", False),
                                        ("w008", "A", False), ("c2", "A", True),
                                        ("v2", "B", True)):
        i, f, s = slot_form(doc[name], None)
        rec(f"V5_{name}_form", f, want_form)
        rec(f"V6_{name}_rank_rule_valid", valid(f, doc[name]), want_valid)
    i, f, s = slot_form(doc["live"], None)
    rec("V7_live_has_no_direction_sentence", f, None)

    # --- entailment-graph cross-check (independent of ranks)
    for name, want in (("v1", False), ("c2", True), ("v2", True)):
        d = doc[name]
        cl = tc(edges_from(d))
        label = {"scc_c0_future_inextendibility": "no proper future C0 metric extension",
                 "scc_c2_future_inextendibility": "no proper future C2 extension"}[
                     d["conclusion"]["conclusion_type"]]
        i, f, s = slot_form(d, None)
        edge = ("no proper future H2_loc extension", label) if f == "A" else (label, "no proper future H2_loc extension")
        rec(f"V8_{name}_graph_rule_valid", edge in cl, want)

    # --- v2 recomputation from live + documented edits
    v1_txt = v1_b.decode()
    rec("V9_v1_sentence_unique", v1_txt.count("so H2_loc-inextendibility ENTAILS this class's conclusion;"), 1)
    v2_re = v1_txt.replace(
        "so H2_loc-inextendibility ENTAILS this class's conclusion;",
        "so this class's conclusion ENTAILS H2_loc-inextendibility and C2-inextendibility, never the reverse;")
    v2_re = v2_re.replace(
        "the earlier 'no containment with C2 or C0 is asserted here' was wrong]",
        "the earlier 'no containment with C2 or C0 is asserted here' was wrong. R3 major: the "
        "first replacement inverted the entailment direction for C0 -- H2_loc-inextendibility is "
        "weaker and entails the C2 sibling, not this class]")
    rec("V10_v2_recomputed_byte_identical", h(v2_re.encode()), h(v2_b))

    # --- v2 fixes the reviewed size-premise defect too
    rec("V11_v2_size_premise_corrected",
        "C2 is a strictly smaller extension class" in v2_re and
        "C2 is a strictly larger extension class" not in v2_re, True)
    rec("V12_v1_size_premise_corrected",
        "C2 is a strictly smaller extension class" in v1_txt, True)

    # --- diff confinement on raw lines
    live_lines = live_b.decode().split("\n")
    for tag, b in (("v1", v1_b), ("v2", v2_b)):
        ls = b.decode().split("\n")
        changed = [i for i, (a, c) in enumerate(zip(live_lines, ls)) if a != c]
        rec(f"V13_{tag}_line_count", len(ls), len(live_lines))
        rec(f"V14_{tag}_changed_lines", changed, [151, 245])

    # --- canonical gate re-execution
    def gate(p):
        r = subprocess.run([sys.executable, str(ROOT / "artifacts/formulation/tools/check_class_schema.py"),
                            "--json", str(p)], capture_output=True, text=True)
        return r.returncode
    rec("V15_gate_live_pass", gate(ROOT / "schemas/af_scc_c0_vacuum.yaml"), 0)
    rec("V16_gate_v1_pass", gate(V1_FILE), 0)
    rec("V17_gate_v2_pass", gate(V2_FILE), 0)
    rec("V18_gate_composed_pass",
        gate(ROOT / "artifacts/worker-044/f2b_live_closure_01/sandbox/schemas/af_scc_c0_vacuum.yaml"), 0)
    rec("V19_gate_empty_item_pass", gate(EV / "mutant_c0_empty_item.yaml"), 0)
    rec("V20_gate_empty_list_fail", gate(EV / "mutant_c0_empty_list.yaml") != 0, True)

    # --- runner report consistency
    rep = checks_of()
    rec("V21_report_all_checks_pass", rep["checks_passed"], rep["checks_total"])
    rec("V22_report_hard_failure", [f["id"] for f in rep["hard_failures"]], ["W023-F2B-DIR1"])
    rec("V23_report_v2_hash_matches_file", rep["corrected_variant"]["sha256"], h(v2_b))
    rec("V24_no_pin_drift_at_exit", rep["pin_drift_at_exit"], [])

    n = sum(1 for r in R if r["pass"])
    out = {
        "task_id": "W023-F2B-DIR-REVIEW-01",
        "verifier": "worker-023 (independent pass, separate code path)",
        "created_at": NOW(),
        "verdict": "PASS" if n == len(R) else "FAIL",
        "checks_passed": n,
        "checks_total": len(R),
        "checks": R,
        "scope": ("independent re-derivation of the direction finding, the 066 candidate "
                  "hash, and the corrected-variant bytes"),
        "falsifier": ("any V-check flipping on the same pins voids this verification; a "
                      "canonical hash move voids the whole packet"),
    }
    (HERE / "verification.json").write_text(json.dumps(out, indent=2, sort_keys=True))
    print(f"verification: {n}/{len(R)} {'PASS' if n == len(R) else 'FAIL'}")
    return 0 if n == len(R) else 1


if __name__ == "__main__":
    sys.exit(main())
