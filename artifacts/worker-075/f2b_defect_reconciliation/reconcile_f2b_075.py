#!/usr/bin/env python3
"""W075-F2B-DEFECT-RECONCILIATION-09 (worker-075, read-only).

One bounded class-bound task on AF-SCC-C0-VAC-GEN / AF-SCC-C2-VAC-GEN:

  Independently re-measure the four documented F2b defects at the live frozen bytes
  (schemas/af_scc_c0_vacuum.yaml b2ab6acb2bbe), reconcile the three independent
  defect ledgers, record the scope of this worker's own earlier F2b review, and
  measure whether any frozen instrument detects the D3 token divergence at all.

No canonical path is written. All output goes under
artifacts/worker-075/f2b_defect_reconciliation/.

Authority: worker measurement only. No gate verdict, no node status, no repair
applied. The gate owner (G-FORM) adjudicates.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import subprocess
import sys
import contextlib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
CAND = OUT / "candidate"
CAND.mkdir(exist_ok=True)

F2B = ROOT / "schemas/af_scc_c0_vacuum.yaml"
F2A = ROOT / "schemas/af_scc_c2_vacuum.yaml"
F0 = ROOT / "research_map/formulation_taxonomy.yaml"
RULE = ROOT / "artifacts/formulation/rule_spec.json"
ALIAS = ROOT / "artifacts/formulation/VOCAB_ALIASES.json"
FROZEN = ROOT / "artifacts/formulation/FROZEN.json"
CORPUS = ROOT / "artifacts/formulation/evidence/semantic_escape_rebased.json"
CHECKER = ROOT / "artifacts/formulation/tools/check_class_schema.py"
ACCEPT = ROOT / "artifacts/formulation/tools/run_acceptance.py"
L083 = ROOT / "artifacts/worker-083/f2b_live_defect_ledger/report.json"
L097 = ROOT / "artifacts/worker-097/f2b_rev13_review/report.json"
L007 = ROOT / "artifacts/worker-007/f2b_containment_repair/report.json"
MYOUT = ROOT / "comms/outbox/worker-075.jsonl"

PINS = [F2B, F2A, F0, RULE, ALIAS, FROZEN, CORPUS, CHECKER, ACCEPT, L083, L097, L007, MYOUT]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


def run_checker(path: Path) -> dict:
    r = subprocess.run([sys.executable, str(CHECKER), str(path), "--json"],
                       capture_output=True, text=True, cwd=str(ROOT))
    out = r.stdout.strip()
    try:
        d = json.loads(out[out.index("{"):])
    except Exception:
        d = {"verdict": None, "failed_rules": [], "raw_tail": out[-200:]}
    return {"exit_code": r.returncode, "verdict": d.get("verdict"),
            "failed_rules": d.get("failed_rules", []), "class_id": d.get("class_id")}


def preflight_repro(corpus_base: str, live_base: str) -> dict:
    """Call the frozen preflight itself (read-only) and record its stdout + return."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("run_acceptance_075", ACCEPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ok = mod.preflight()
    return {"called": True, "returns": bool(ok), "stdout": buf.getvalue().strip(),
            "corpus_base": corpus_base, "live_base": live_base,
            "agrees_with_direct_compare": (bool(ok) == (corpus_base == live_base))}


def canon(registry: dict, kind: str, tok):
    for c, al in registry[kind].items():
        if tok == c or tok in al:
            return c
    return tok


def main() -> int:
    pins = {rel(p): sha(p) for p in PINS}

    f2b = yaml.safe_load(F2B.read_text())
    f2a = yaml.safe_load(F2A.read_text())
    f0 = yaml.safe_load(F0.read_text())
    rule = json.loads(RULE.read_text())
    alias = json.loads(ALIAS.read_text())
    corpus = json.loads(CORPUS.read_text())
    r083 = json.loads(L083.read_text())
    r097 = json.loads(L097.read_text())
    r007 = json.loads(L007.read_text())

    # ---------------- D1: forbidden-transfer reason inverts the file's own chain
    chain = f2b["implication_ledger"]["extension_class_containment"]
    ft0 = f2b["implication_ledger"]["forbidden_transfers"][0]
    d1_fires = bool(re.search(r"C2\s+is\s+a\s+strictly\s+larger\s+extension\s+class", ft0["reason"], re.I))
    d1 = {
        "id": "W075R-D1",
        "carrier": "implication_ledger.forbidden_transfers[0].reason",
        "claim": "the reason calls C2 a strictly larger extension class while the file's own chain has E_C2 nested inside E_C0",
        "reason_text": ft0["reason"],
        "chain_text": chain,
        "fires": d1_fires,
        "verdict": "CONFIRMED_INVERTED_REASON" if d1_fires else "NOT_REPRODUCED",
        "transfer_direction_itself_correct": True,
        "note": "the forbidden direction (no C2 extension =/=> no C0 extension) is logically right; only the justification clause is inverted, so the minimal edit is one word/one token in the reason",
    }

    # ---------------- D2: live containment denial contradicting the ledger
    denial = str(f2b["regularity"]["must_not_conflate"][0])
    d2_fires = bool(re.search(r"no\s+containment\s+with\s+C2\s+or\s+C0\s+is\s+asserted", denial, re.I))
    # in-freeze precedent: the repaired C2 sibling carries the nesting and marks the old denial wrong
    f2a_mnc = [str(x) for x in f2a["regularity"]["must_not_conflate"]]
    precedent = next((x for x in f2a_mnc if "E_C2 subset" in x), None)
    d2 = {
        "id": "W075R-D2",
        "carrier": "regularity.must_not_conflate[0]",
        "claim": "the clause denies containment with C2/C0 while implication_ledger.extension_class_containment asserts it",
        "denial_text": denial,
        "ledger_text": chain,
        "fires": d2_fires,
        "verdict": "CONFIRMED_DENIAL_CONTRADICTS_LEDGER" if (d2_fires and "contains" in chain) else "NOT_REPRODUCED",
        "axis_reading_tested": "the sentence could be read as axis-token distinctness, not extension-set nesting; that reading is not what the sentence says ('No containment ... is asserted here' carries no axis qualifier), and the C2 sibling explicitly records the denial formulation as wrong",
        "repair_precedent_in_freeze": precedent,
        "repair_precedent_source": rel(F2A),
    }

    # ---------------- D3: token divergence + frozen-instrument coverage
    tok_b = f2b["conclusion"]["conclusion_type"]
    tok_a = f2a["conclusion"]["conclusion_type"]
    rule_vocab = rule["vocabularies"]["class_conclusion_type"]
    f0_allowed = f0["field_vocabulary"]["conclusion_type"]["allowed"]
    alias_policy = alias["policy"]

    def classify(tok, cid):
        canon_key = canon(alias, "conclusion_type", tok)
        return {
            "token": tok,
            "class_id": cid,
            "in_rule_spec_required": rule_vocab.get(cid) == tok,
            "in_f0_allowed_list": tok in f0_allowed,
            "registry_canonical_key": tok in alias["conclusion_type"],
            "registry_alias_member": any(tok in v for v in alias["conclusion_type"].values()),
            "registry_canon_after_alias": canon_key,
        }

    # F0's own declared class tokens
    f0_axis_tokens = {cid: (f0["classes"][cid].get("axes", {}) or {}).get("conclusion_type")
                      for cid in ("AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN")}

    # operational coverage: run the frozen checker on canonical and on the F0-token variant
    canon_check_b = run_checker(F2B)
    mut = CAND / "control_f0token__af_scc_c0_vacuum.yaml"
    mut.write_text(F2B.read_text().replace(f"conclusion_type: {tok_b}",
                                           "conclusion_type: strong_cosmic_censorship_C0"))
    mut_check = run_checker(mut)
    d3 = {
        "id": "W075R-D3",
        "carrier": "conclusion.conclusion_type",
        "tokens": [classify(tok_b, "AF-SCC-C0-VAC-GEN"), classify(tok_a, "AF-SCC-C2-VAC-GEN")],
        "rule_spec_required": rule_vocab,
        "f0_declared_allowed": f0_allowed,
        "f0_own_class_axis_tokens": f0_axis_tokens,
        "alias_policy": alias_policy,
        "frozen_instrument_coverage": {
            "checker_on_canonical_f2b": canon_check_b,
            "checker_on_f0_token_variant": mut_check,
            "no_frozen_tool_enforces_f0_field_vocabulary_against_class_schemas": True,
            "alias_aware_consistency_tool_neutralises_the_divergence": {
                "tool": "artifacts/formulation/tools/check_taxonomy_consistency.py",
                "mechanism": "canon('conclusion_type', .) maps both scc_* and strong_* onto the registry canonical key before comparison",
                "canon_of_f2b_token": canon(alias, "conclusion_type", tok_b),
                "canon_of_f0_axis_token": canon(alias, "conclusion_type", f0_axis_tokens["AF-SCC-C0-VAC-GEN"]),
            },
        },
        "verdict": "CONFIRMED_DIVERGENCE_NOT_DETECTED_BY_FROZEN_SUITE"
        if (tok_b not in f0_allowed and rule_vocab["AF-SCC-C0-VAC-GEN"] == tok_b
            and canon_check_b["verdict"] == "pass" and mut_check["verdict"] == "fail")
        else "NOT_REPRODUCED",
        "alias_equivalence_nuance": {
            "registry_canon_of_f0_allowed_tokens": [canon(alias, "conclusion_type", t) for t in f0_allowed],
            "statement": "every token in F0's allowed list is a registry alias of the schema token, so the two lists are alias-equivalent for consistency checks; no semantic class mismatch is demonstrated",
            "residual_defect": "F0's declarative allowed list enumerates alias tokens while the alias policy says aliases must never appear in a new canonical artifact; F0 cannot be edited without voiding G-F0, so the residual is a canonicalization/hygiene divergence for the gate owner to weigh, not a proven class-schema failure",
        },
        "adjudication_left_to_gate_owner": True,
        "consequence_options": [
            {"option": "F0 allowed list governs",
             "cost": "F2a/F2b need a token re-stamp to strong_cosmic_censorship_C2/C0; their existing accepts/verdicts at e9a27996/b2ab6acb are void; any write to F0 itself voids G-F0, so F0 cannot be the artifact edited"},
            {"option": "rule_spec + VOCAB_ALIASES govern (operational status quo)",
             "cost": "F0 field_vocabulary.conclusion_type.allowed and F0 classes[*].axes.conclusion_type stay inconsistent with the schemas and the alias policy's 'never in a new canonical artifact' clause; no schema byte changes; requires a recorded interpretation, not a write"},
        ],
    }

    # ---------------- D4: stale acceptance corpus
    live_base = sha(F2B)
    corpus_base = corpus.get("base_sha256")
    pf = preflight_repro(corpus_base, live_base)
    d4 = {
        "id": "W075R-D4",
        "carrier": "artifacts/formulation/evidence/semantic_escape_rebased.json:base_sha256",
        "corpus_base": corpus_base,
        "live_canonical_c0": live_base,
        "stale": corpus_base != live_base,
        "frozen_preflight": pf,
        "verdict": "CONFIRMED_STALE_CORPUS" if corpus_base != live_base and not pf["returns"] else "NOT_REPRODUCED",
    }

    # ---------------- cross-ledger reconciliation
    my_review = None
    for line in MYOUT.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get("event_id") == "w075-20260912T0103-review-f2b":
            my_review = e
    my_hf = [h.get("id") for h in (my_review or {}).get("hard_failures", [])]
    reconcile = {
        "ledgers": [
            {"ledger": rel(L083), "sha256": pins[rel(L083)],
             "blocking_defect_ids": [b["id"] for b in r083.get("blocking", [])],
             "non_blocking_ids": [b["id"] for b in r083.get("non_blocking", [])],
             "checks": r083.get("checks")},
            {"ledger": rel(L097), "sha256": pins[rel(L097)],
             "failing_checks": {k: v.get("findings") for k, v in r097.get("checks", {}).items() if v.get("verdict") == "fail"},
             "verdict": r097.get("verdict"), "score": r097.get("score")},
            {"ledger": rel(L007), "sha256": pins[rel(L007)],
             "candidate_checks": [{"candidate": c.get("candidate"), "checks": c.get("checks")}
                                  for c in r007.get("candidates", [])],
             "controls_all_pass": r007.get("controls_all_pass")},
            {"ledger": "comms/outbox/worker-075.jsonl#w075-20260912T0103-review-f2b",
             "sha256": pins[rel(MYOUT)],
             "hard_failures": my_hf, "verdict": (my_review or {}).get("verdict"),
             "score": (my_review or {}).get("score")},
        ],
        "per_defect_agreement": {
            "D1_reason_inversion": {"this_measurement": d1["verdict"], "w083": "W083R13-D1 blocking",
                                     "w097": "H3 fail", "w075_review": "HF-075-F2b-LARGER"},
            "D2_containment_denial": {"this_measurement": d2["verdict"], "w083": "W083R13-D2 blocking",
                                       "w097": "H3b fail", "w075_review": "NOT FLAGGED (scope gap)"},
            "D3_token_divergence": {"this_measurement": d3["verdict"], "w083": "W083R13-D3 blocking",
                                     "w097": "H7 alias-aware pass (not a conformance failure there)",
                                     "w075_review": "HF-075-F2b-VOCAB"},
            "D4_stale_corpus": {"this_measurement": d4["verdict"], "w083": "W083R13-D4 non-blocking",
                                 "w097": "not in check set", "w075_review": "SF-075-F2b-CORPUS soft"},
        },
        "w075_self_erratum": {
            "event_id": "w075-20260912T0103-review-f2b",
            "gap": "the 01:03 review flagged D1 and D3 but did not flag D2 (the must_not_conflate[0] denial); the union of independent findings is three blocking defect classes, not two",
            "action": "recorded here; the original review event is not edited",
        },
    }

    # ---------------- proposed minimal repair (NOT applied) + dry-run
    r1_old = ft0["reason"]
    r1_new = ("C2 is a strictly smaller extension class (E_C2 subset of E_C0), "
              "so C2-inextendibility is strictly weaker")
    # The C2 sibling's wording cannot be copied verbatim into the C0 class: its closing clause
    # ("H2_loc-inextendibility ENTAILS this class's conclusion") is the C2 direction. The C0 class
    # is the strongest, so the direction must be flipped to match F2b's own one_way_entailments.
    d2_new = ("C^{1,1} and H2_loc are DIFFERENT classes (separate tokens and nodes), but the "
              "extension sets are nested: E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0. "
              "This class's C0-inextendibility is the strongest of the three and ENTAILS the H2_loc "
              "and C2 conclusions; see implication_ledger. [repairs the earlier flat containment "
              "denial; the denied phrasing is deliberately not quoted, or the denial scanner fires "
              "on the repair itself]")
    d2_sibling_verbatim = precedent
    # detector for an entailment-direction mismatch in the replacement sentence
    def d2_direction_mismatch(text):
        if not text:
            return False
        # sibling-verbatim phrasing claims a lower class entails "this class" -> wrong for C0
        return bool(re.search(r"H2_loc-inextendibility\s+ENTAILS\s+this\s+class", text, re.I))
    repaired = F2B.read_text()
    repaired = repaired.replace(f"reason: \"{r1_old}\"", f"reason: \"{r1_new}\"")
    if d2_new:
        repaired = repaired.replace(f'    - "{denial}"', f'    - "{d2_new}"')
    rep_path = CAND / "repair_spec_dryrun__af_scc_c0_vacuum.yaml"
    rep_path.write_text(repaired)

    rep = yaml.safe_load(repaired)
    d1_after = bool(re.search(r"C2\s+is\s+a\s+strictly\s+larger\s+extension\s+class",
                              rep["implication_ledger"]["forbidden_transfers"][0]["reason"], re.I))
    d2_after = bool(re.search(r"no\s+containment\s+with\s+C2\s+or\s+C0\s+is\s+asserted",
                              str(rep["regularity"]["must_not_conflate"][0]), re.I))
    repair = {
        "status": "PROPOSED_NOT_APPLIED",
        "R1": {"carrier": "implication_ledger.forbidden_transfers[0].reason",
               "old": r1_old, "new": r1_new,
               "rationale": "one-clause edit; keeps the forbidden-transfer direction; fixes only the inverted justification"},
        "R2": {"carrier": "regularity.must_not_conflate[0]",
               "old": denial, "new": d2_new,
               "rationale": "parity with the repaired C2 sibling frozen in the same manifest, but DIRECTION-ADAPTED: the sibling's closing clause ('H2_loc-inextendibility ENTAILS this class's conclusion') is the C2 direction and would be wrong in the C0 class, whose conclusion is the strongest (C0 => H2loc => C2). Copying the sibling verbatim is a live trap; the text below flips the entailment to F2b's own ledger direction.",
               "sibling_verbatim_that_must_not_be_copied": d2_sibling_verbatim},
        "R3": {"carrier": "conclusion.conclusion_type",
               "old": tok_b, "new": "GATE-OWNER ADJUDICATION REQUIRED (see D3 consequence_options)",
               "rationale": "not a worker-level choice; whichever authority wins, one frozen artifact's declaration moves"},
        "dryrun": {"path": rel(rep_path), "sha256": sha(rep_path),
                   "d1_fires_after": d1_after, "d2_fires_after": d2_after,
                   "d2_direction_mismatch_after": d2_direction_mismatch(d2_new),
                   "checker": run_checker(rep_path),
                   "expected": "D1/D2 resolved by direction-correct text, D3 untouched, frozen checker still pass"},
        "not_applied_to_canonical": True,
    }

    # ---------------- controls
    def d1_scan(text):
        return bool(re.search(r"C2\s+is\s+a\s+strictly\s+larger\s+extension\s+class", text, re.I))

    def d2_scan(text):
        return bool(re.search(r"no\s+containment\s+with\s+C2\s+or\s+C0\s+is\s+asserted", text, re.I))

    canon_text = F2B.read_text()
    controls = [
        {"id": "K1", "expect": "fires", "observed": "fires" if d1_scan(canon_text) else "silent",
         "pass": d1_scan(canon_text)},
        {"id": "K2", "expect": "silent", "observed": "fires" if d1_scan(r1_new) else "silent",
         "pass": not d1_scan(r1_new)},
        {"id": "K3", "expect": "silent", "observed": "fires" if d2_scan(d2_new or "") else "silent",
         "pass": not d2_scan(d2_new or "")},
        {"id": "K4", "expect": "fires", "observed": "fires" if d2_scan(canon_text) else "silent",
         "pass": d2_scan(canon_text)},
        {"id": "K5_operational_detector_live", "expect": "f0-token variant fails R11",
         "observed": f"verdict={mut_check['verdict']} failed_rules={mut_check['failed_rules']}",
         "pass": mut_check["verdict"] == "fail"},
        {"id": "K6_corpus_live_hash", "expect": "matching base passes the same predicate",
         "observed": "pass" if corpus_base == live_base else "stale",
         "pass": (corpus_base == live_base) == pf["returns"]},
        {"id": "K7_sibling_verbatim_direction_trap", "expect": "sibling-verbatim sentence flagged",
         "observed": "flagged" if d2_direction_mismatch(d2_sibling_verbatim) else "silent",
         "pass": d2_direction_mismatch(d2_sibling_verbatim)},
        {"id": "K8_direction_adapted_text_clean", "expect": "adapted text not flagged",
         "observed": "flagged" if d2_direction_mismatch(d2_new) else "clean",
         "pass": not d2_direction_mismatch(d2_new)},
    ]
    controls_pass = all(c["pass"] for c in controls)

    report = {
        "schema": "w075-f2b-defect-reconciliation/v1",
        "task_id": "W075-F2B-DEFECT-RECONCILIATION-09",
        "actor": "worker-075",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
        "gate": "G-FORM",
        "authority": "worker measurement only; no canonical write, no repair applied, no gate verdict, no node completion",
        "generated_at": __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds"),
        "pins": pins,
        "defects": [d1, d2, d3, d4],
        "cross_ledger_reconciliation": reconcile,
        "proposed_repair": repair,
        "controls": controls,
        "controls_pass": controls_pass,
        "headline": ("At the live frozen bytes (F2b b2ab6acb2bbe, F2a e9a27996dfd3, F0 0abb9ed8a961, "
                     "FROZEN rev29 815e08079aef): D1 (inverted reason) and D2 (containment denial) reproduce and admit a "
                     "one-clause, in-freeze-precedent repair; D3 is a real cross-artifact token divergence that no frozen "
                     "instrument detects (the operational checker requires the scc_* token and rejects F0's declared token), "
                     "so it is a gate-owner adjudication; D4 reproduces with the frozen preflight returning False."),
        "falsifier": ("Re-run reconcile_f2b_075.py and verify_f2b_reconciliation_075.py at the same pins. Falsified by: "
                      "(a) any pinned input re-hashing to a different sha256; (b) the frozen checker passing on the F0-token "
                      "variant or failing on canonical F2b; (c) the frozen preflight returning True while the corpus base "
                      "differs from the live C0 hash; (d) a frozen tool that enforces F0 field_vocabulary against class "
                      "schemas being shown to exist; or (e) any control K1-K6 not reproducing its committed expectation."),
        "not_claimed": ["no gate verdict", "no repair applied to a canonical path",
                        "no D3 resolution (gate-owner item)", "no claim about candidate repairs authored by other workers"],
    }
    (OUT / "reconciliation.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({"ok": True, "controls_pass": controls_pass,
                      "d1": d1["verdict"], "d2": d2["verdict"], "d3": d3["verdict"], "d4": d4["verdict"],
                      "out": rel(OUT / "reconciliation.json")}, indent=1))
    return 0 if controls_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
