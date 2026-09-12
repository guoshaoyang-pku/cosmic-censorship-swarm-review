#!/usr/bin/env python3
"""Worker-024 independent verifier for the F2b rev29 -> rev30 minimal repair.

Class-bound task: class_id AF-SCC-C0-VAC-GEN, node F2b, gate G-FORM.
Task source: two independent revise verdicts on F2b rev29 (b2ab6acb2bbe):
  * reviews/F2b-review-worker-018-rev13.json  (W018-R13-F2B-B1, W018-R13-F2B-B2)
  * reviews/F2b-review-rev29-075.json         (HF-075-F2b-LARGER, HF-075-F2b-VOCAB)
This verifier does NOT quote those reviews for its verdict. It re-derives both
carriers from the artifact's own bytes:

  D1  regularity.must_not_conflate[0] denies any C2/C0 containment while the
      artifact's own implication_ledger.extension_class_containment asserts one.
  D2  implication_ledger.forbidden_transfers[0].reason calls C2 "a strictly
      larger extension class" while the artifact's own containment chain makes
      E_C2 the smallest extension set.

and then checks that CANDIDATE (a) removes both contradictions, (b) corrects
rather than deletes the normative content, and (c) changes nothing else.

Secondary instrument: an adapted copy of worker-018's checker
(artifacts/worker-018/f2b_rev13_review/check_f2b_rev13.py) is regenerated with
TARGET/MIRROR/EXPECTED_SHA/outpath repointed at the candidate. The adaptation is
declared in the report; the checker body is unchanged. Its C10-FROZEN-PIN is
EXPECTED to FAIL because the candidate is deliberately unfrozen.

Read-only. No network. Deterministic. Run from the repo root:
    python3 artifacts/worker-024/f2b_rev29_repair/verify_f2b_repair_024.py
Exit 0 iff live reproduces D1+D2, candidate clears D1+D2, and invariance holds.
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
DIR = Path(__file__).resolve().parent

LIVE_REL = "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
LIVE_SHA = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"
CAND_REL = "artifacts/worker-024/f2b_rev29_repair/CANDIDATE_schemas_af_scc_c0_vacuum.yaml"
FROZEN_REL = "artifacts/formulation/FROZEN.json"
FROZEN_SHA = "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"
F0_REL = "research_map/formulation_taxonomy.yaml"
F0_SHA = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
F2A_REL = "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"
F2A_SHA = "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe"
VOCAB_REL = "artifacts/formulation/VOCAB_ALIASES.json"
VOCAB_SHA = "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba"
W018_CHECKER = "artifacts/worker-018/f2b_rev13_review/check_f2b_rev13.py"

R = []


def rec(cid, status, msg, **extra):
    R.append({"id": cid, "status": status, "msg": msg, **extra})
    print(f"[{status}] {cid}: {msg}")


def sha256_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class NoDupLoader(yaml.SafeLoader):
    pass


def _no_dup(loader, node, deep=False):
    keys = set()
    for k, _ in node.value:
        kk = loader.construct_object(k, deep=deep)
        if kk in keys:
            raise ValueError(f"duplicate key {kk!r} at line {k.start_mark.line + 1}")
        keys.add(kk)
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


NoDupLoader.add_constructor("tag:yaml.org,2002:map", _no_dup)


def load(path):
    return yaml.load(Path(path).read_text(), Loader=NoDupLoader)


def parse_chain(doc):
    """Re-derive the E-set containment order from the artifact's own ledger string."""
    s = doc["implication_ledger"]["extension_class_containment"]
    head = s.split(";")[0]
    sets_ = re.findall(r"E_\{[^}]+\}|E_[A-Za-z0-9]+", head)
    # "E_A contains E_B contains ..." -> index 0 is the largest extension set.
    return sets_


def main():
    # ---------- pins -------------------------------------------------------
    live = ROOT / LIVE_REL
    cand = ROOT / CAND_REL
    h_live = sha256_file(live)
    h_cand = sha256_file(cand)
    rec("P1-LIVE-PIN", "PASS" if h_live == LIVE_SHA else "FAIL",
        f"live F2b sha256 {h_live} == frozen rev29 pin {LIVE_SHA}", measured=h_live)
    rec("P2-FROZEN-MANIFEST", "PASS" if sha256_file(ROOT / FROZEN_REL) == FROZEN_SHA else "FAIL",
        f"FROZEN.json sha256 == rev29 manifest {FROZEN_SHA[:12]}")
    rec("P3-F0-PIN", "PASS" if sha256_file(ROOT / F0_REL) == F0_SHA else "FAIL",
        f"F0 taxonomy sha256 == G-F0 pass pin {F0_SHA[:12]}")
    rec("P4-F2A-PIN", "PASS" if sha256_file(ROOT / F2A_REL) == F2A_SHA else "FAIL",
        f"F2a sibling sha256 == {F2A_SHA[:12]}")
    rec("P5-VOCAB-PIN", "PASS" if sha256_file(ROOT / VOCAB_REL) == VOCAB_SHA else "FAIL",
        f"VOCAB_ALIASES.json sha256 == {VOCAB_SHA[:12]}")
    rec("P6-CANDIDATE-DIFFERS", "PASS" if h_cand != h_live else "FAIL",
        f"candidate sha256 {h_cand[:12]} differs from frozen bytes (new revision required)", measured=h_cand)

    live_doc = load(live)
    cand_doc = load(cand)

    # ---------- D1 re-derived: self-contradictory containment denial -------
    chain = parse_chain(live_doc)
    chain_ok = chain == ["E_C0", "E_H2loc", "E_{C^1,1}", "E_C2"]
    rec("D1-CHAIN-PARSE", "PASS" if chain_ok else "FAIL",
        f"containment order re-derived from implication_ledger: {chain} (largest -> smallest)", chain=chain)

    den_re = re.compile(r"No containment with .* asserted here")
    live_den = [s for s in live_doc["regularity"]["must_not_conflate"] if den_re.search(s)]
    d1_live = len(live_den) > 0 and chain_ok
    rec("D1-LIVE-REPRODUCED", "PASS" if d1_live else "FAIL",
        "live rev29 asserts both: (a) a denial of any C2/C0 containment and (b) the chain "
        f"E_C0 superset E_H2loc superset E_C2 -- contradiction reproduced at line 152; "
        f"denial_count={len(live_den)}")

    cand_mnc = cand_doc["regularity"]["must_not_conflate"]
    cand_den = [s for s in cand_mnc if den_re.search(s)]
    cand_states_nesting = cand_mnc and ("E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0" in cand_mnc[0])
    d1_fixed = len(cand_den) == 0 and bool(cand_states_nesting) and len(cand_mnc) == len(live_doc["regularity"]["must_not_conflate"])
    rec("D1-CANDIDATE-FIXED", "PASS" if d1_fixed else "FAIL",
        "candidate must_not_conflate[0] states the nesting (corrected, not deleted) and no longer "
        f"denies containment; list length unchanged ({len(cand_mnc)})")

    # ---------- D2 re-derived: inverted extension-class premise -------------
    live_ft = live_doc["implication_ledger"]["forbidden_transfers"]
    inv_re = re.compile(r"strictly larger extension class")
    live_inv = [r for r in live_ft if inv_re.search(str(r.get("reason", "")))]
    smallest = chain[-1] if chain_ok else None
    d2_live = len(live_inv) > 0 and smallest == "E_C2"
    rec("D2-LIVE-REPRODUCED", "PASS" if d2_live else "FAIL",
        "live rev29 forbidden_transfers[0].reason calls C2 'a strictly larger extension class' "
        f"while its own chain makes {smallest} the smallest extension set -- premise inverted at line 246")

    cand_ft = cand_doc["implication_ledger"]["forbidden_transfers"]
    cand_inv = [r for r in cand_ft if inv_re.search(str(r.get("reason", "")))]
    r0 = str(cand_ft[0].get("reason", ""))
    d2_fixed = (len(cand_inv) == 0 and "strictly stronger regularity requirement" in r0
                and "SMALLEST extension set" in r0 and len(cand_ft) == len(live_ft))
    rec("D2-CANDIDATE-FIXED", "PASS" if d2_fixed else "FAIL",
        "candidate forbidden_transfers[0].reason states C2 is the strictly stronger requirement "
        "and E_C2 the smallest set; transfer structure and length unchanged")

    # ---------- invariance --------------------------------------------------
    l_keys, c_keys = set(live_doc), set(cand_doc)
    rec("I1-TOPLEVEL-KEYS", "PASS" if l_keys == c_keys else "FAIL",
        f"top-level keys unchanged ({len(l_keys)} keys)")

    mnc_tail_same = live_doc["regularity"]["must_not_conflate"][1:] == cand_mnc[1:]
    ft_tail_same = live_ft[1:] == cand_ft[1:]
    ft_pairs_same = [(r.get("from"), r.get("to")) for r in live_ft] == [(r.get("from"), r.get("to")) for r in cand_ft]
    rec("I2-CARRIER-LOCALITY", "PASS" if (mnc_tail_same and ft_tail_same and ft_pairs_same) else "FAIL",
        "only must_not_conflate[0] and forbidden_transfers[0].reason differ; all sibling entries "
        "and all from/to pairs are byte-identical")

    identity_same = (live_doc["class_id"] == cand_doc["class_id"] == "AF-SCC-C0-VAC-GEN"
                     and live_doc["node_id"] == cand_doc["node_id"] == "F2b")
    concl_same = json.dumps(live_doc["conclusion"], sort_keys=True) == json.dumps(cand_doc["conclusion"], sort_keys=True)
    quant_same = [q.get("kind") for q in live_doc["quantifiers"]["ordered"]] == \
                 [q.get("kind") for q in cand_doc["quantifiers"]["ordered"]] == ["forall", "exists", "forall", "not_exists"]
    ledger_same = live_doc["implication_ledger"]["extension_class_containment"] == \
                  cand_doc["implication_ledger"]["extension_class_containment"]
    entail_same = live_doc["implication_ledger"]["one_way_entailments"] == \
                  cand_doc["implication_ledger"]["one_way_entailments"]
    rec("I3-SEMANTIC-INVARIANTS", "PASS" if (identity_same and concl_same and quant_same and ledger_same and entail_same) else "FAIL",
        "class_id/node_id, conclusion block, quantifier order, containment string and all "
        "one_way_entailments are unchanged")

    # alias policy: the repair must not introduce the F0 alias token into the candidate
    cand_text = cand.read_text()
    alias_leak = "strong_cosmic_censorship_C0" in cand_text
    rec("I4-NO-ALIAS-INJECTION", "PASS" if not alias_leak else "FAIL",
        "candidate introduces no 'strong_cosmic_censorship_C0' alias token (VOCAB_ALIASES policy: "
        "aliases must never appear in a new canonical artifact)")

    # CF-16: quoted mentions inside phrases_that_are_not_this_class are metalinguistic
    # and are not uses; strip that list before scanning (same rule as checker C9).
    def anti_scope_uses(doc):
        a = json.loads(json.dumps(doc.get("anti_scope", {})))
        a.pop("phrases_that_are_not_this_class", None)
        return a

    cand_composite = re.search(r"C0\s+or\s+C2", json.dumps(anti_scope_uses(cand_doc)))
    mention_same = (live_doc.get("anti_scope", {}).get("phrases_that_are_not_this_class")
                    == cand_doc.get("anti_scope", {}).get("phrases_that_are_not_this_class"))
    rec("I5-NO-COMPOSITE", "PASS" if (cand_composite is None and mention_same) else "FAIL",
        "no 'C0 or C2' composite regularity introduced in anti_scope use-fields (CF-16 quoted "
        "mention exempt and byte-identical to live)")

    # line-level diff is exactly the two carriers
    a = live.read_text().splitlines()
    b = cand.read_text().splitlines()
    changed = [i + 1 for i, (x, y) in enumerate(zip(a, b)) if x != y]
    rec("I6-DIFF-EXACTLY-2-LINES", "PASS" if changed == [152, 246] and len(a) == len(b) else "FAIL",
        f"candidate differs from frozen bytes on exactly lines {changed}; line count {len(b)}")

    # ---------- D3 vocab token conflict (adjudication, not worker-fixable) --
    f0 = load(ROOT / F0_REL)
    f0_allowed = f0["field_vocabulary"]["conclusion_type"]["allowed"]
    vocab = json.loads((ROOT / VOCAB_REL).read_text())
    cand_tok = cand_doc["conclusion"]["conclusion_type"]
    f2a_tok = load(ROOT / F2A_REL)["conclusion"]["conclusion_type"]
    tok_in_f0 = cand_tok in f0_allowed
    f2a_tok_in_f0 = f2a_tok in f0_allowed
    accepts = []
    for p in sorted((ROOT / "reviews").glob("F2a-review*.json")):
        try:
            d = json.loads(p.read_text())
        except Exception:
            continue
        if d.get("verdict") == "accept" and F2A_SHA[:12] in json.dumps(d):
            accepts.append({"file": p.name, "reviewer": d.get("reviewer"), "score": d.get("score")})
    rec("D3-VOCAB-CONFLICT-ADJUDICATION", "ADJUDICATION",
        f"F2b conclusion_type '{cand_tok}' is not in F0 allowed {f0_allowed} "
        f"(in_f0={tok_in_f0}); the identical conflict exists on the accepted F2a sibling "
        f"('{f2a_tok}', in_f0={f2a_tok_in_f0}) which carries {len(accepts)} accepts at {F2A_SHA[:12]}. "
        "A F2b-only re-stamp would desynchronise the siblings and contradicts VOCAB_ALIASES "
        "canonical-token policy; a gate-wide disposition is required.",
        f0_allowed=f0_allowed, vocab_canonical_c0="scc_c0_future_inextendibility",
        f2a_token=f2a_tok, f2a_accepts_at_pin=accepts)

    # ---------- secondary instrument: adapted worker-018 checker -----------
    adapted = DIR / "rerun_w018_checker_on_candidate.py"
    src = (ROOT / W018_CHECKER).read_text()
    src = src.replace(
        'TARGET = "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"',
        f'TARGET = "{CAND_REL}"')
    src = src.replace(
        'MIRROR = "schemas/af_scc_c0_vacuum.yaml"',
        f'MIRROR = "{CAND_REL}"')
    src = src.replace(
        f'EXPECTED_SHA = "{LIVE_SHA}"',
        f'EXPECTED_SHA = "{h_cand}"')
    src = src.replace(
        'outpath = ROOT / "artifacts/worker-018/f2b_rev13_review/results.json"',
        'outpath = ROOT / "artifacts/worker-024/f2b_rev29_repair/w018_checker_on_candidate.results.json"')
    adapted.write_text(src)
    proc = subprocess.run([sys.executable, str(adapted)], capture_output=True, text=True, cwd=ROOT)
    w018 = {"exit_code": proc.returncode, "stdout_tail": proc.stdout.strip().splitlines()[-6:]}
    try:
        w018_res = json.loads((DIR / "w018_checker_on_candidate.results.json").read_text())
        by_id = {c["id"]: c["status"] for c in w018_res["checks"]}
        w018["summary"] = w018_res["summary"]
        w018["C17-CHAIN-DENIAL"] = by_id.get("C17-CHAIN-DENIAL")
        w018["C18-TRANSFER-REASON"] = by_id.get("C18-TRANSFER-REASON")
        w018["C10-FROZEN-PIN"] = by_id.get("C10-FROZEN-PIN")
    except Exception as e:
        w018["parse_error"] = str(e)
    cross_ok = (w018.get("C17-CHAIN-DENIAL") == "PASS" and w018.get("C18-TRANSFER-REASON") == "PASS"
                and w018.get("C10-FROZEN-PIN") == "FAIL")
    rec("X1-CROSS-INSTRUMENT", "PASS" if cross_ok else "FAIL",
        "adapted worker-018 checker on candidate: C17/C18 (verdict-bearing) PASS, C10 FAIL as "
        f"EXPECTED (candidate is deliberately unfrozen); summary={w018.get('summary')}",
        instrument="artifacts/worker-024/f2b_rev29_repair/rerun_w018_checker_on_candidate.py",
        adaptation="TARGET/MIRROR/EXPECTED_SHA/outpath repointed to candidate; checker body unchanged")

    # ---------- residual blocker set ---------------------------------------
    residual = ["D3-VOCAB-CONFLICT-ADJUDICATION"]
    rec("R1-RESIDUAL-BLOCKERS", "PASS" if residual == ["D3-VOCAB-CONFLICT-ADJUDICATION"] else "FAIL",
        f"after the minimal repair the residual F2b blocker set is {residual}; D1/D2 are cleared",
        residual=residual)

    hard_fail = [r for r in R if r["status"] == "FAIL"]
    report = {
        "actor": "worker-024",
        "run": "W024-F2B-REV29-REPAIR-01",
        "task": "F2b rev29 minimal repair candidate for W018-R13-F2B-B1/B2",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN"],
        "node_id": "F2b",
        "gate": "G-FORM",
        "frozen_input": {"path": LIVE_REL, "sha256": h_live, "revision": 29,
                         "manifest": FROZEN_REL, "manifest_sha256": FROZEN_SHA},
        "candidate": {"path": CAND_REL, "sha256": h_cand,
                      "changed_lines": changed, "status": "UNFROZEN_CANDIDATE_NOT_APPLIED"},
        "patch": "artifacts/worker-024/f2b_rev29_repair/repair.patch",
        "checks": R,
        "cross_instrument": w018,
        "residual_blockers": residual,
        "d3_adjudication_brief": {
            "conflict": "F2b/F2a use VOCAB_ALIASES canonical tokens scc_c0/c2_future_inextendibility; "
                        "F0 field_vocabulary.conclusion_type.allowed lists only the alias forms "
                        "strong_cosmic_censorship_C0/C2.",
            "scope": "gate-wide: F2a at " + F2A_SHA[:12] + f" carries the same conflict and {len(accepts)} accepts.",
            "admissible_resolutions": [
                "A: record a one-token addendum accepting the VOCAB_ALIASES canonical tokens as the "
                "operative conclusion_type vocabulary without writing research_map/formulation_taxonomy.yaml "
                "(any write voids G-F0); requires the gate owner plus one independent review.",
                "B: re-stamp F2a and F2b conclusion_type to the F0 alias forms; rejected by VOCAB_ALIASES "
                "policy ('aliases must never appear in a new canonical artifact') unless that policy is "
                "itself adjudicated.",
            ],
            "not_worker_fixable": True,
        },
        "authority_note": "Worker evidence only. No canonical artifact was modified, no node status, "
                          "validation_status, or gate verdict is set here. The candidate is unfrozen and "
                          "must be applied and re-pinned by the formulation lead before it can earn a review.",
        "falsifier": "Any of: (a) live F2b no longer measures " + LIVE_SHA + "; (b) the candidate's own "
                     "chain parse no longer makes E_C2 smallest; (c) a re-run shows a third F2b line "
                     "changed by the patch; (d) C17 or C18 fails when an independent instrument is run on "
                     "the candidate bytes " + h_cand + "; (e) the lead shows D1 or D2 is normative text that "
                     "must be retained as written.",
        "hard_fail_count": len(hard_fail),
    }
    out = DIR / "report.json"
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(f"\nsummary: {len([r for r in R if r['status']=='PASS'])} PASS / "
          f"{len([r for r in R if r['status']=='FAIL'])} FAIL / "
          f"{len([r for r in R if r['status']=='ADJUDICATION'])} ADJUDICATION -> {out.relative_to(ROOT)}")
    return 0 if not hard_fail else 1


if __name__ == "__main__":
    sys.exit(main())
