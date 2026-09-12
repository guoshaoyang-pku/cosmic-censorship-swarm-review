#!/usr/bin/env python3
"""W050-F2B-REPAIR-CANDIDATE-INDEPENDENT-VERIFY-06.

Independent, non-author, fail-closed verification of the F2b rev13 two-line repair
candidate proposed by worker-001 (artifacts/worker-001/f2b_containment_repair/).
Read-only over every pinned input; writes only inside this artifact directory.

Exit codes: 0 verified, 2 check failure, 3 pin drift (void), 4 control failure.
See PREREGISTRATION.md; instrument frozen before the run.
"""
from __future__ import annotations

import copy
import datetime as _dt
import difflib
import hashlib
import json
import os
import re
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

BASE = "schemas/af_scc_c0_vacuum.yaml"
CAND = "artifacts/worker-001/f2b_containment_repair/REPAIR_CANDIDATE.yaml"
DIFF = "artifacts/worker-001/f2b_containment_repair/REPAIR_CANDIDATE.diff"
F2A = "schemas/af_scc_c2_vacuum.yaml"
F1 = "schemas/af_wcc_vacuum.yaml"
F0 = "research_map/formulation_taxonomy.yaml"
F0_SUP = "artifacts/formulation/formulation_taxonomy.yaml"
FROZEN = "artifacts/formulation/FROZEN.json"
VOCAB = "artifacts/formulation/VOCAB_ALIASES.json"

PINS = {
    BASE: "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    CAND: "90ede5c9516b5b4d18346bed6224561d06194b3c485067976be9aab55dd5a328",
    DIFF: "a45fbae3a8afc01f0e7d5b64bc773a2c34aeb984e734dd092e30dc04f0fd6bde",
    F2A: "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    F1: "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    F0: "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    F0_SUP: "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    FROZEN: "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    VOCAB: "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba",
}

BASE_D1 = "No containment with C2 or C0 is asserted here"
BASE_D2 = "C2 is a strictly larger extension class"
CAND_D1 = "No containment among the regularity-axis values is asserted here"
CAND_D2 = "E_C2 is a strictly smaller extension set than E_C0"
E_RE = re.compile(r"E_(\{[^}]*\}|[A-Za-z0-9^,]+)")
DIR_RE = re.compile(r"(E_\S+)\s+is a strictly (smaller|larger) extension set than\s+(E_\S+)")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now() -> str:
    return _dt.datetime.now(_dt.timezone(_dt.timedelta(hours=8))).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def lines(path: str) -> list:
    return read(path).splitlines()


def pin_guard(pins: dict) -> list:
    bad = []
    for rel, want in pins.items():
        p = ROOT / rel
        if not p.is_file():
            bad.append({"path": rel, "problem": "missing", "want": want})
        else:
            got = sha256(p)
            if got != want:
                bad.append({"path": rel, "problem": "drift", "want": want, "got": got})
    return bad


def norm_token(raw: str) -> str:
    t = raw.strip()
    if t.startswith("{") and t.endswith("}"):
        t = t[1:-1]
    return t.replace("\\", "").strip()


def tok_of(raw: str) -> str:
    t = norm_token(raw)
    return t.rstrip(",.;:")[2:] if t.rstrip(",.;:").startswith("E_") else t.rstrip(",.;:")


def chain_tokens(text: str) -> list:
    return [norm_token(m.group(1)) for m in E_RE.finditer(text)]


def skel(obj):
    if isinstance(obj, dict):
        return {"K": sorted(obj.keys()), "V": {k: skel(v) for k, v in obj.items()}}
    if isinstance(obj, list):
        return {"L": len(obj), "V": [skel(v) for v in obj]}
    return type(obj).__name__


def diff_pairs(base_lines: list, cand_lines: list):
    sm = difflib.SequenceMatcher(None, base_lines, cand_lines, autojunk=False)
    pairs, ops = [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        ops.append({"tag": tag, "base": [i1, i2], "cand": [j1, j2]})
        if tag == "equal":
            continue
        pairs.append({
            "base_line": i1 + 1, "cand_line": j1 + 1,
            "removed": base_lines[i1:i2], "added": cand_lines[j1:j2],
        })
    return ops, pairs


def parse_declared_diff(text: str):
    hunks, cur = [], None
    for ln in text.splitlines():
        if ln.startswith("@@"):
            m = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", ln)
            cur = {"base_start": int(m.group(1)), "cand_start": int(m.group(2)),
                   "removed": [], "added": []}
            hunks.append(cur)
        elif cur is not None and ln.startswith("-") and not ln.startswith("---"):
            cur["removed"].append(ln[1:])
        elif cur is not None and ln.startswith("+") and not ln.startswith("+++"):
            cur["added"].append(ln[1:])
    return hunks


def alias_index(vocab: dict):
    idx = {}
    for canon, aliases in (vocab.get("conclusion_type") or {}).items():
        idx[canon] = canon
        for a in aliases:
            idx[a] = canon
    return idx


def run_checks() -> dict:
    base_txt, cand_txt = read(BASE), read(CAND)
    base_lines, cand_lines = base_txt.splitlines(), cand_txt.splitlines()
    base, cand = yaml.safe_load(base_txt), yaml.safe_load(cand_txt)
    f2a_txt = read(F2A)
    f2a = yaml.safe_load(f2a_txt)
    f0 = yaml.safe_load(read(F0))
    vocab = json.loads(read(VOCAB))
    checks = []

    def add(cid, ok, detail, evidence=None, severity="blocking"):
        checks.append({"id": cid, "ok": bool(ok), "detail": detail,
                       "evidence": evidence or [], "severity": severity})

    # C1 skeleton
    sk_base, sk_cand = skel(base), skel(cand)
    add("C1_key_skeleton", sk_base == sk_cand,
        "recursive key skeleton identical" if sk_base == sk_cand else "key skeleton differs",
        [f"top_keys_base={sorted(base.keys())}", f"top_keys_cand={sorted(cand.keys())}"])

    # C2 diff
    ops, pairs = diff_pairs(base_lines, cand_lines)
    declared = parse_declared_diff(read(DIFF))
    computed_ok = (
        len(pairs) == 2
        and all(p["base_line"] == p["cand_line"] and len(p["removed"]) == 1 and len(p["added"]) == 1
                for p in pairs)
        and [p["base_line"] for p in pairs] == [152, 246]
    )
    decl_ok = (len(declared) == 2
               and all(len(h["removed"]) == 1 and len(h["added"]) == 1 for h in declared))
    match_ok = False
    if computed_ok and decl_ok:
        match_ok = all(
            p["removed"][0] == h["removed"][0] and p["added"][0] == h["added"][0]
            for p, h in zip(pairs, declared))
    add("C2_minimal_two_line_diff", computed_ok and decl_ok and match_ok,
        f"computed pairs at lines {[p['base_line'] for p in pairs]}; declared hunks={len(declared)}; "
        f"declared-matches-computed={match_ok}",
        [f"base152={base_lines[151][:90]}", f"cand152={cand_lines[151][:90]}",
         f"base246={base_lines[245][:90]}", f"cand246={cand_lines[245][:90]}"])

    # C3 D1
    chain = (cand.get("implication_ledger") or {}).get("extension_class_containment", "")
    ctoks = chain_tokens(chain if isinstance(chain, str) else "")
    chain_ok = ctoks == ["C0", "H2loc", "C^1,1", "C2"]
    c3 = (BASE_D1 in base_txt and BASE_D1 not in cand_txt
          and CAND_D1 in cand_lines[151] and "extension_class_containment" in cand_lines[151]
          and chain_ok)
    add("C3_D1_denial_removed_and_deferred", c3,
        f"base carrier present={BASE_D1 in base_txt}; cand carrier absent={BASE_D1 not in cand_txt}; "
        f"deferral phrase present={CAND_D1 in cand_lines[151]}; chain={ctoks}",
        [f"cand:152={cand_lines[151]}", f"cand:239={chain[:120]}"])

    # C4 D2
    ft = (cand.get("implication_ledger") or {}).get("forbidden_transfers") or []
    reason = ft[0].get("reason", "") if ft else ""
    m = DIR_RE.search(reason)
    rank = {t: i for i, t in enumerate(ctoks)}  # C0=0 largest ... C2=3 smallest
    dir_ok = False
    if m:
        subj, rel, obj = tok_of(m.group(1)), m.group(2), tok_of(m.group(3))
        if subj in rank and obj in rank:
            dir_ok = (rel == "smaller" and rank[subj] > rank[obj]) or (rel == "larger" and rank[subj] < rank[obj])
    c4 = (BASE_D2 in base_txt and BASE_D2 not in cand_txt and CAND_D2 in reason and dir_ok)
    add("C4_D2_direction_corrected", c4,
        f"base carrier present={BASE_D2 in base_txt}; cand carrier absent={BASE_D2 not in cand_txt}; "
        f"parsed direction={'%s %s %s' % (m.group(1), m.group(2), m.group(3)) if m else 'none'}; rank={rank}",
        [f"cand:246={reason}"])

    # C5 D3 classification
    idx = alias_index(vocab)
    allowed = ((f0.get("field_vocabulary") or {}).get("conclusion_type") or {}).get("allowed") or []
    sup = yaml.safe_load(read(F0_SUP))
    sup_allowed = ((sup.get("field_vocabulary") or {}).get("conclusion_type") or {}).get("allowed") or []
    tok = (cand.get("conclusion") or {}).get("conclusion_type")
    f2a_tok = (f2a.get("conclusion") or {}).get("conclusion_type")
    in_canon = tok in (vocab.get("conclusion_type") or {})
    in_f0 = tok in allowed or tok in sup_allowed
    bridge = idx.get(tok)
    f2a_in_canon = f2a_tok in (vocab.get("conclusion_type") or {})
    f2a_in_f0 = f2a_tok in allowed or f2a_tok in sup_allowed
    f2a_bridge = idx.get(f2a_tok)
    sym = (in_canon == f2a_in_canon) and (in_f0 == f2a_in_f0) and (bool(bridge) == bool(f2a_bridge))
    d3_status = ("resolved_in_f0" if in_f0 else
                 ("global_symmetric_representation_divergence" if sym else "asymmetric_divergence"))
    add("C5_D3_symmetric_classification", sym,
        f"token={tok} vocab_canonical={in_canon} f0_allowed={in_f0} alias_bridge={bridge}; "
        f"f2a_token={f2a_tok} f2a_vocab_canonical={f2a_in_canon} f2a_f0_allowed={f2a_in_f0} "
        f"f2a_alias_bridge={f2a_bridge}; status={d3_status}",
        [f"f0_allowed={allowed}", f"f0_supplement_allowed={sup_allowed}"],
        severity="residual-classification")

    # C6 residual carriers (amendment A2: "strictly between" counts only outside the quoted
    # prohibition sentence that the base file itself mandates)
    bad = [s for s in ("No containment with C2 or C0", "strictly larger extension class")
           if s in cand_txt]
    if re.search(r"(?<![\"'])\bstrictly between\b(?![\"'])", cand_txt):
        bad.append("strictly between (unquoted)")
    add("C6_no_residual_adverse_carriers", not bad,
        f"residual carriers found={bad}", [f"cand_sha={PINS[CAND]}"])

    # C7 cross-sibling
    f2a_chain = (f2a.get("implication_ledger") or {}).get("extension_class_containment", "")
    f2a_toks = chain_tokens(f2a_chain if isinstance(f2a_chain, str) else "")
    f2a_ok = f2a_toks[:1] == ["C2"] and f2a_toks[-1:] == ["C0"] and set(f2a_toks) == set(ctoks)
    line152_denies = bool(re.search(r"no containment[^.]*with (C2|C0)", cand_lines[151], re.I))
    c7 = f2a_ok and not line152_denies and dir_ok and chain_ok
    add("C7_cross_sibling_agreement", c7,
        f"f2a_chain={f2a_toks}; cand_chain={ctoks}; line152_denies_extension_containment={line152_denies}",
        [f"f2a:237={f2a_chain[:110]}"])

    # C8 determinism
    rerun_pairs = diff_pairs(base_lines, cand_lines)[1]
    det = json.dumps(rerun_pairs, sort_keys=True) == json.dumps(pairs, sort_keys=True)
    add("C8_deterministic_rediff", det, f"second diff identical={det}")

    # C9 structural invariants
    b_reg = (base.get("regularity") or {}).get("must_not_conflate") or []
    c_reg = (cand.get("regularity") or {}).get("must_not_conflate") or []
    b_led = base.get("implication_ledger") or {}
    c_led = cand.get("implication_ledger") or {}
    inv = {
        "must_not_conflate_len": [len(b_reg), len(c_reg)],
        "one_way_entailments_len": [len(b_led.get("one_way_entailments") or []),
                                    len(c_led.get("one_way_entailments") or [])],
        "forbidden_transfers_len": [len(b_led.get("forbidden_transfers") or []),
                                    len(c_led.get("forbidden_transfers") or [])],
        "conclusion_type_same": (base.get("conclusion") or {}).get("conclusion_type")
                                == (cand.get("conclusion") or {}).get("conclusion_type"),
        "extension_class_containment_same": b_led.get("extension_class_containment")
                                            == c_led.get("extension_class_containment"),
    }
    inv_ok = (inv["must_not_conflate_len"][0] == inv["must_not_conflate_len"][1]
              and inv["one_way_entailments_len"][0] == inv["one_way_entailments_len"][1]
              and inv["forbidden_transfers_len"][0] == inv["forbidden_transfers_len"][1]
              and inv["conclusion_type_same"] and inv["extension_class_containment_same"])
    add("C9_structural_invariants", inv_ok, json.dumps(inv))

    return {"checks": checks, "d3_status": d3_status,
            "pairs": pairs, "chain": ctoks, "f2a_chain": f2a_toks, "diff_ops": ops}


def run_controls(diff_ops_expected: dict) -> list:
    controls = []

    def add(cid, ok, detail):
        controls.append({"id": cid, "ok": bool(ok), "detail": detail})

    base_txt, cand_txt = read(BASE), read(CAND)
    cand_lines = cand_txt.splitlines()
    base_lines = base_txt.splitlines()

    # K1/K2/K3 in-memory mutations, evaluated with the same predicates as C3/C4
    a = list(cand_lines); a[151] = base_lines[151]
    k1 = ("No containment with C2 or C0" in "\n".join(a)) and (CAND_D1 not in a[151])
    add("K1_revert_edit_A_redetects_D1", k1, "reverted line 152 re-contains the base denial")

    b = list(cand_lines); b[245] = base_lines[245]
    k2 = ("strictly larger extension class" in b[245]) and (CAND_D2 not in b[245])
    add("K2_revert_edit_B_redetects_D2", k2, "reverted line 246 re-contains the inverted reason")

    c = list(cand_lines); c[245] = c[245].replace("strictly smaller", "strictly larger")
    m = DIR_RE.search(c[245])
    k3 = bool(m) and m.group(2) == "larger"
    add("K3_invert_edit_B_detected", k3, "inverted 'smaller'->'larger' is parsed as a violation")

    # K4 pin guard rejects a wrong pin
    wrong = dict(PINS); wrong[CAND] = "0" * 64
    bad = pin_guard(wrong)
    add("K4_pin_guard_rejects_drift", len(bad) == 1 and bad[0]["path"] == CAND,
        f"pin guard mismatches={len(bad)}")

    # K5 delete line 152 -> diff no longer two 1-for-1 pairs at 152/246
    d = list(cand_lines); del d[151]
    _, p5 = diff_pairs(base_lines, d)
    k5 = not (len(p5) == 2 and [x["base_line"] for x in p5] == [152, 246]
              and all(len(x["removed"]) == 1 and len(x["added"]) == 1 for x in p5))
    add("K5_deleted_edit_line_detected", k5, f"diff pairs after deletion={[(x['base_line'], x['cand_line']) for x in p5]}")

    # K6 drop implication_ledger key -> skeleton differs
    cand = yaml.safe_load(cand_txt); mut = copy.deepcopy(cand); mut.pop("implication_ledger", None)
    k6 = skel(mut) != skel(yaml.safe_load(base_txt))
    add("K6_key_loss_detected", k6, "dropping implication_ledger changes the key skeleton")

    return controls


def main() -> int:
    started = now()
    bad = pin_guard(PINS)
    if bad:
        print(json.dumps({"event": "pin_drift", "mismatches": bad}, indent=1))
        return 3

    res = run_checks()
    controls = run_controls(res)
    ended = now()
    bad_end = pin_guard(PINS)

    checks_ok = all(c["ok"] for c in res["checks"])
    controls_ok = all(c["ok"] for c in controls)
    if bad_end:
        verdict, code = "VOID_INPUT_DRIFT", 3
    elif not controls_ok:
        verdict, code = "INSTRUMENT_CONTROL_FAILURE", 4
    elif not checks_ok:
        verdict, code = "CANDIDATE_REJECTED", 2
    else:
        verdict, code = "CANDIDATE_VERIFIED_MINIMAL_FIX", 0

    report = {
        "schema": "worker-050/f2b-repair-candidate-verify/v1",
        "task_id": "W050-F2B-REPAIR-CANDIDATE-INDEPENDENT-VERIFY-06",
        "actor": "worker-050",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "created_at": started,
        "finished_at": ended,
        "verdict": verdict,
        "exit_code": code,
        "counts_as_full_schema_verdict": False,
        "authority_note": ("Worker measurement only: no canonical write, no validation_status=passed, "
                           "no node done, no gate verdict. Instrument independent of worker-001's harness; "
                           "worker-050 authored the D1/D2/D3 defect list (disclosed)."),
        "instrument_amendments": [
            {"id": "A1", "check": "C4_D2_direction_corrected",
             "before": "object token parsed as 'E_C0,' from the trailing comma; rank lookup failed",
             "after": "tok_of() strips trailing ,.;: before the rank lookup",
             "effect": "instrument measurement artifact removed; predicate semantics unchanged",
             "run1_result": "false failure of C4 (and of dependent C7)",
             "disclosed_in": "INSTRUMENT_AMENDMENTS.md; run1 preserved as report.run1.json"},
            {"id": "A2", "check": "C6_no_residual_adverse_carriers",
             "before": "raw substring 'strictly between' counted, including the quoted prohibition "
                       "sentence that the base file itself mandates",
             "after": "counts only unquoted occurrences, via negative quote lookarounds",
             "effect": "false positive removed; predicate semantics unchanged (pre-registration VF3)",
             "run1_result": "false failure of C6",
             "disclosed_in": "INSTRUMENT_AMENDMENTS.md; run1 preserved as report.run1.json"},
        ],
        "subject": {"base": BASE, "candidate": CAND, "declared_diff": DIFF,
                    "candidate_is_non_canonical": True},
        "pins": PINS,
        "pin_stability": {"start_ok": not bad, "end_ok": not bad_end, "end_mismatches": bad_end},
        "checks": res["checks"],
        "controls": controls,
        "D1_D2_fixed": all(c["ok"] for c in res["checks"] if c["id"] in ("C3_D1_denial_removed_and_deferred",
                                                                        "C4_D2_direction_corrected")),
        "diff_pairs": res["pairs"],
        "chain_rank_largest_first": res["chain"],
        "f2a_chain_rank_smallest_first": res["f2a_chain"],
        "residuals": [{
            "id": "W050-R1-D3",
            "status": res["d3_status"],
            "detail": ("candidate conclusion_type token is VOCAB-canonical and unchanged by the candidate; "
                       "its absence from F0's declared allowed list is symmetric with F2a, so it is a global "
                       "F0/VOCAB reconciliation item, not an F2b-specific defect and outside the candidate's "
                       "declared two-line scope"),
        }],
        "falsifiers": [
            "VF1 any pinned input moves (exit 3, measurement void)",
            "VF2 an independent reader reproduces a base->candidate diff other than the two declared hunks",
            "VF3 candidate denies extension-set containment or states the E_C2/E_C0 order backwards",
            "VF4 F2a is in a different F0-vocabulary representation state than F2b",
            "VF5 re-running this script on identical bytes yields a different report",
        ],
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    with (HERE / "per_check.jsonl").open("w", encoding="utf-8") as fh:
        for c in res["checks"] + controls:
            fh.write(json.dumps(c, sort_keys=True) + "\n")
    (HERE / "inputs.json").write_text(json.dumps(
        {"measured_at": started, "pins": {k: sha256(ROOT / k) for k in PINS}}, indent=1), encoding="utf-8")

    print(json.dumps({"verdict": verdict, "exit_code": code,
                      "checks_failed": [c["id"] for c in res["checks"] if not c["ok"]],
                      "controls_failed": [c["id"] for c in controls if not c["ok"]],
                      "d3_status": res["d3_status"]}, indent=1))
    return code


if __name__ == "__main__":
    sys.exit(main())
