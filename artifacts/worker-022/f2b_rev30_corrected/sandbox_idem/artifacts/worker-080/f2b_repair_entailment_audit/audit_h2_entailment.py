#!/usr/bin/env python3
"""W080-F2B-REPAIR-H2E-01: audit the F2b (AF-SCC-C0-VAC-GEN) repair candidates for a
repair-introduced entailment-direction defect.

CONTEXT (all read-only; no canonical path is written):
  The live F2b rev13 bytes  schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe  carry two normative
  containment defects found independently by worker-017 and worker-066:
    H1  implication_ledger.forbidden_transfers[0].reason  calls C2 a "strictly larger
        extension class" while the file's own chain makes E_C2 the smallest set.
    H2  regularity.must_not_conflate[0]  denies containment ("No containment with C2 or C0
        is asserted here") while the same file asserts the nested chain.
  A 2-edit repair (H1 wording + H2 wording) is circulating: worker-066's
  f2b_repair_prereg/proposed_patch.diff, worker-066's rebased candidate 84b5d3fa, and
  worker-08's rev29_candidate/af_scc_c0_vacuum.repair-candidate.yaml (byte-identical to
  84b5d3fa).  Both reviewers certified the 2-edit candidate "finding-free" against their
  own defect taxonomy.  Neither taxonomy checks the DIRECTION of an entailment claim.

WHAT THIS HARNESS DECIDES:
  Whether the H2 replacement sentence is consistent with the file's own containment chain
  and with the file's own one_way_entailments / forbidden_weakenings rows.  It is not:
  the replacement asserts "H2_loc-inextendibility ENTAILS this class's conclusion" inside
  the C0 file, where "this class" = AF-SCC-C0-VAC-GEN.  From the file's chain
  E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2, the class conclusion
  (C0-inextendibility) ENTAILS H2_loc-inextendibility, not the reverse; the reverse is a
  forbidden weakening at :232.  The sentence is a near-verbatim copy of the C2 sibling's
  correct sentence, whose truth is class-relative (own = C2).

OUTPUTS (written only under this artifact directory):
  report.json                     full machine report
  staged/candidate_84b5d3fa.yaml  independent re-application of the 2 edits to live bytes
  staged/candidate_corrected.yaml H2 direction corrected; H1 edit unchanged
  staged/candidate_nesting_only.yaml  alternate: nesting + pointer, no entailment claim
  staged/*.sha256                 per-file hashes

DETERMINISM: stdlib only; every input is hashed before and after; the run fails closed
(exit 2) on any pin move.  The canonical structural gate is invoked as a read-only
subprocess; its known blindness to these clauses is re-measured, not assumed.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
STAGED = OUT / "staged"
CST = timezone(timedelta(hours=8))

LIVE_C0 = "schemas/af_scc_c0_vacuum.yaml"
MIRROR_C0 = "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
C2 = "schemas/af_scc_c2_vacuum.yaml"
C2_MIRROR = "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"
F1 = "schemas/af_wcc_vacuum.yaml"
FROZEN = "artifacts/formulation/FROZEN.json"
RULE_SPEC = "artifacts/formulation/rule_spec.json"
GATE = "artifacts/formulation/tools/check_class_schema.py"
REF_CANDIDATE = (
    "artifacts/worker-066/f2b_rev29_containment_binding/"
    "pinned/candidate_98f9ec83__af_scc_c0_vacuum.yaml"
)
W08_CANDIDATE = "artifacts/worker08/rev29_candidate/af_scc_c0_vacuum.repair-candidate.yaml"

PINS = {
    LIVE_C0: "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    MIRROR_C0: "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    C2: "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    C2_MIRROR: "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    F1: "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    FROZEN: "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    RULE_SPEC: "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
    GATE: "000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff",
    REF_CANDIDATE: "98f9ec83c487d6920968f0bdf98e03974813376b6d222b617300525eb13feb1c",
}

CAND_84B5D3FA = "84b5d3fa29a677ad157b924675bb5a9c08281395920be0221535465a5da44b40"

H1_LIVE = (
    '- {from: "no proper future C2 extension", to: "this class", reason: '
    '"C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker"}'
)
H1_FIXED = (
    '- {from: "no proper future C2 extension", to: "this class", reason: '
    '"C2 is a strictly smaller extension class (E_C2 subset of E_C0), so '
    'C2-inextendibility is strictly weaker"}'
)
H2_LIVE_FRAG = (
    "No containment with C2 or C0 is asserted here; the informal phrase "
    "'strictly between' is not used and must not be cited (worker-16 F2b-16-02 accepted)."
)
# Exact H2 replacement used by worker-066's rebased candidate (84b5d3fa) and by
# worker-08's repair candidate (byte-identical).  Reproduced from
# artifacts/worker-066/f2b_rev29_containment_binding/rebind.py H2_FIXED_FRAG.
H2_CAND_FRAG = (
    "The extension sets are nonetheless nested: E_C2 subset of E_{C^1,1} "
    "subset of E_H2loc subset of E_C0 (see implication_ledger), so "
    "H2_loc-inextendibility ENTAILS this class's conclusion; the informal "
    "phrase 'strictly between' is not a class definition and must not be cited "
    "(worker-16 F2b-16-02 accepted). [R2 major: the earlier 'no containment with "
    "C2 or C0 is asserted here' was wrong]"
)
# Corrected replacement: nesting + the DIRECTION THAT THE FILE'S CHAIN SUPPORTS.
H2_CORRECTED_FRAG = (
    "The extension sets are nonetheless nested: E_C2 subset of E_{C^1,1} "
    "subset of E_H2loc subset of E_C0 (see implication_ledger); this class's "
    "conclusion (C0-inextendibility) therefore ENTAILS H2_loc-inextendibility, "
    "and H2_loc-inextendibility entails the C2 sibling's conclusion, not this "
    "class. The informal phrase 'strictly between' is not a class definition "
    "and must not be cited (worker-16 F2b-16-02 accepted). [R2 major: the "
    "earlier 'no containment with C2 or C0 is asserted here' was wrong]"
)
# Alternate minimal replacement: state the nesting, point at the ledger, make no
# entailment claim at all.
H2_NESTING_ONLY_FRAG = (
    "The extension sets are nonetheless nested: E_C2 subset of E_{C^1,1} "
    "subset of E_H2loc subset of E_C0 (see implication_ledger); the direction "
    "of the induced entailments among the corresponding inextendibility "
    "statements is recorded there. The informal phrase 'strictly between' is "
    "not a class definition and must not be cited (worker-16 F2b-16-02 "
    "accepted). [R2 major: the earlier 'no containment with C2 or C0 is "
    "asserted here' was wrong]"
)

SYM_TO_TOKEN = {
    "E_C0": "C0",
    "E_H2loc": "H2LOC",
    "E_{C^1,1}": "C11",
    "E_C2": "C2",
}
INExt = {
    "C0": "C0-inextendibility",
    "H2LOC": "H2_loc-inextendibility",
    "C11": "C^1,1-inextendibility",
    "C2": "C2-inextendibility",
}
CLASS_TOKEN = {"AF-SCC-C0-VAC-GEN": "C0", "AF-SCC-C2-VAC-GEN": "C2"}


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_path(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def read(p: str) -> str:
    return (ROOT / p).read_text(encoding="utf-8")


def line_of(text: str, needle: str) -> int:
    for i, ln in enumerate(text.splitlines(), 1):
        if needle in ln:
            return i
    return -1


def write_staged(name: str, text: str) -> dict:
    STAGED.mkdir(parents=True, exist_ok=True)
    p = STAGED / name
    p.write_text(text, encoding="utf-8")
    h = sha256_path(p)
    (STAGED / (name + ".sha256")).write_text(f"{h}  {name}\n", encoding="utf-8")
    return {"path": str(p.relative_to(ROOT)), "sha256": h, "bytes": len(text.encode())}


# --------------------------------------------------------------------------------------
# containment-order model
# --------------------------------------------------------------------------------------
def derive_order(text: str) -> dict:
    """Parse the file's own extension_class_containment chain (largest set first)."""
    m = re.search(r"extension_class_containment:\s*\"([^\"]+)\"", text)
    if not m:
        raise SystemExit("FAIL-CLOSED: extension_class_containment not found")
    chain = m.group(1)
    order = [s for s in ("E_C0", "E_H2loc", "E_{C^1,1}", "E_C2") if s in chain]
    if order != ["E_C0", "E_H2loc", "E_{C^1,1}", "E_C2"]:
        raise SystemExit(f"FAIL-CLOSED: unexpected chain order: {order}")
    rank = {SYM_TO_TOKEN[s]: i for i, s in enumerate(order)}  # 0 = largest set
    allowed = {
        (a, b)
        for a in rank
        for b in rank
        if rank[a] < rank[b]  # E_a larger; inext(a) entails inext(b)
    }
    return {
        "chain_text": chain,
        "chain_line": line_of(text, "extension_class_containment:"),
        "order_largest_to_smallest": [SYM_TO_TOKEN[s] for s in order],
        "rank": rank,
        "allowed_entailments": sorted(f"{INExt[a]} => {INExt[b]}" for a, b in allowed),
    }


def scan_entailment_claims(text: str, own: str) -> list:
    """Find class-relative entailment claims in the document.

    Two shapes are recognized:
      (i)  "<X>-inextendibility ENTAILS this class's conclusion"        -> X => own
      (ii) "this class's conclusion ... ENTAILS <X>-inextendibility"    -> own => X
    Only H2_loc / C0 / C2 tokens are used in this corpus.
    """
    claims = []
    for i, ln in enumerate(text.splitlines(), 1):
        for m in re.finditer(
            r"(C0|C2|H2_loc)-inextendibility\s+ENTAILS\s+this class'?s conclusion", ln
        ):
            src = "H2LOC" if m.group(1) == "H2_loc" else m.group(1)
            claims.append({"line": i, "shape": "source_entails_class", "source": src, "target": own, "quote": ln.strip()[:220]})
        for m in re.finditer(
            r"this class'?s conclusion[^.\"]{0,80}?ENTAILS\s+(C0|C2|H2_loc)-inextendibility", ln
        ):
            tgt = "H2LOC" if m.group(1) == "H2_loc" else m.group(1)
            claims.append({"line": i, "shape": "class_entails_source", "source": own, "target": tgt, "quote": ln.strip()[:220]})
    return claims


def classify_claims(text: str, own: str, order: dict) -> list:
    rank = order["rank"]
    out = []
    for c in scan_entailment_claims(text, own):
        a, b = c["source"], c["target"]
        ok = (a in rank) and (b in rank) and rank[a] < rank[b]
        out.append({**c, "allowed_by_chain": ok})
    return out


# --------------------------------------------------------------------------------------
# findings
# --------------------------------------------------------------------------------------
def findings_for(text: str, own: str, order: dict) -> list:
    f = []
    # H1: inverted size premise in forbidden_transfers[0].reason
    for i, ln in enumerate(text.splitlines(), 1):
        m = re.search(r"strictly\s+(larger|smaller)\s+extension\s+class", ln)
        if m and "forbidden_transfers" not in ln:
            pass
        if m and "C2" in ln and "strictly larger extension class" in ln:
            f.append({"id": "size_premise_inverted", "severity": "hard", "line": i,
                      "quote": ln.strip()[:240],
                      "why": "calls C2 the larger extension class; chain makes E_C2 smallest"})
    # H2 live: bounded, non-bracketed containment denial in must_not_conflate
    for i, ln in enumerate(text.splitlines(), 1):
        if "must_not_conflate" in ln:
            continue
        if re.search(r"No containment with (C2|C0|C2 or C0)", ln) and ln.strip().startswith("-"):
            f.append({"id": "false_containment_denial", "severity": "hard", "line": i,
                      "quote": ln.strip()[:240],
                      "why": "denies containment the same file asserts in implication_ledger"})
    # H2e: entailment direction claim not supported by the chain
    for c in classify_claims(text, own, order):
        if not c["allowed_by_chain"]:
            f.append({"id": "entailment_direction_inverted", "severity": "hard",
                      "line": c["line"], "quote": c["quote"],
                      "why": (f"claims {INExt[c['source']]} => {INExt[c['target']]} "
                              f"(own={own}); chain allows the opposite direction")})
    # H2e-2: the same file's forbidden_weakenings row contradicts the claim
    fw = [ln for ln in text.splitlines()
          if "substituting H2_loc for C0" in ln and "not this class" in ln]
    claims = classify_claims(text, own, order)
    if fw and any(not c["allowed_by_chain"] for c in claims):
        f.append({"id": "normative_contradiction", "severity": "hard",
                  "line": line_of(text, "substituting H2_loc for C0"),
                  "quote": fw[0].strip()[:240],
                  "why": ("the repaired must_not_conflate clause contradicts this retained "
                          "forbidden_weakenings row in the same document")})
    # dedupe by (id,line)
    seen, uniq = set(), []
    for x in f:
        k = (x["id"], x["line"])
        if k not in seen:
            seen.add(k)
            uniq.append(x)
    return uniq


def kinds(fs: list) -> list:
    return sorted({x["id"] for x in fs})


def run_gate(path: Path) -> dict:
    r = subprocess.run(
        [sys.executable, str(ROOT / GATE), str(path)],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    return {"exit_code": r.returncode, "stdout": r.stdout.strip()[:500],
            "stderr": r.stderr.strip()[:300], "verdict": "pass" if r.returncode == 0 else "fail"}


def main() -> int:
    checks, controls = [], []

    def check(cid, stmt, ok, evidence, falsifier):
        checks.append({"id": cid, "pass": bool(ok), "statement": stmt,
                       "evidence": evidence, "falsifier": falsifier})
        return bool(ok)

    # ---- P: pins ----------------------------------------------------------------
    pins = {}
    for p, want in PINS.items():
        got = sha256_path(ROOT / p)
        pins[p] = {"declared": want, "measured": got, "match": got == want}
    if not all(v["match"] for v in pins.values()):
        print(json.dumps({"FAIL_CLOSED": "pin drift", "pins": pins}, indent=1))
        return 2
    check("P1-pins", "all pinned input bytes match their declared sha256", True,
          {p: v["measured"][:16] for p, v in pins.items()},
          "any input byte moves; the report is void at the moved pin.")
    frozen = json.loads(read(FROZEN))
    fb = frozen.get("files", {}).get(LIVE_C0, {}).get("sha256")
    check("P2-freeze-binds-live", "FROZEN rev29 declares the measured live F2b hash",
          fb == PINS[LIVE_C0],
          {"frozen_revision": frozen.get("revision"), "frozen_declared": fb,
           "measured": PINS[LIVE_C0]},
          "FROZEN declares a different F2b hash or revision.")
    for p in (W08_CANDIDATE,):
        pins[p] = {"declared": None, "measured": sha256_path(ROOT / p), "match": True}

    live = read(LIVE_C0)
    mirror = read(MIRROR_C0)
    check("P3-canonical-mirror", "canonical and authoring-mirror F2b are byte-identical",
          sha256_bytes(live.encode()) == sha256_bytes(mirror.encode()),
          {"canonical": PINS[LIVE_C0], "mirror": PINS[MIRROR_C0]},
          "the two canonical paths diverge.")

    order = derive_order(live)
    check("P4-chain-parse", "F2b extension_class_containment parses to the 4-set chain",
          order["order_largest_to_smallest"] == ["C0", "H2LOC", "C11", "C2"],
          {"line": order["chain_line"], "chain": order["chain_text"]},
          "the chain is absent or orders the extension sets differently.")
    check("P5-derived-entailments",
          "derived closure: the class conclusion entails H2loc-inext; H2loc-inext entails C2-inext",
          "C0-inextendibility => H2_loc-inextendibility" in order["allowed_entailments"]
          and "H2_loc-inextendibility => C2-inextendibility" in order["allowed_entailments"]
          and "H2_loc-inextendibility => C0-inextendibility" not in order["allowed_entailments"],
          {"allowed": order["allowed_entailments"]},
          "the chain yields the opposite entailment order.")

    # ---- candidate reconstruction ----------------------------------------------
    if H1_LIVE not in live or H2_LIVE_FRAG not in live:
        print(json.dumps({"FAIL_CLOSED": "live carriers absent"}, indent=1))
        return 2
    cand = live.replace(H1_LIVE, H1_FIXED).replace(H2_LIVE_FRAG, H2_CAND_FRAG)
    h_cand = sha256_bytes(cand.encode())
    check("R1-candidate-reproduced",
          "live + the 2 published edits reproduces candidate 84b5d3fa exactly",
          h_cand == CAND_84B5D3FA, {"measured": h_cand, "expected": CAND_84B5D3FA},
          "the candidate hash differs; the published candidate is not the 2-edit repair.")
    ref = read(REF_CANDIDATE)
    check("R2-reference-candidate",
          "worker-008 reference candidate 98f9ec83 carries the same H2 replacement sentence",
          H2_CAND_FRAG in ref, {"ref_sha256": PINS[REF_CANDIDATE]},
          "the reference candidate has different H2 wording.")
    w08 = sha256_path(ROOT / W08_CANDIDATE)
    check("R3-worker08-identical",
          "worker-08 rev29 repair candidate is byte-identical to 84b5d3fa",
          w08 == CAND_84B5D3FA, {"worker08_candidate": w08, "rebased": h_cand},
          "worker-08's candidate differs from the rebased candidate.")
    cand_line = line_of(cand, "ENTAILS this class's conclusion")
    check("R4-claim-present",
          "candidate H2 sentence asserts 'H2_loc-inextendibility ENTAILS this class's conclusion'",
          "H2_loc-inextendibility ENTAILS this class's conclusion" in cand,
          {"line": cand_line, "quote": cand.splitlines()[cand_line - 1].strip()[:240]},
          "the candidate does not carry that clause.")

    # ---- defect scan ------------------------------------------------------------
    f_live = findings_for(live, "C0", order)
    f_cand = findings_for(cand, "C0", order)
    f_ref = findings_for(ref, "C0", order)
    check("D1-live-defects", "live rev13 yields exactly the two known defects (no entailment defect yet)",
          kinds(f_live) == ["false_containment_denial", "size_premise_inverted"],
          {"kinds": kinds(f_live), "findings": f_live},
          "live yields a different defect set.")
    check("D2-candidate-new-defect",
          "candidate 84b5d3fa trades H2 for a repair-introduced entailment inversion + normative contradiction",
          kinds(f_cand) == ["entailment_direction_inverted", "normative_contradiction"],
          {"kinds": kinds(f_cand), "findings": f_cand},
          "the candidate is clean under this checker; the finding is then void.")
    check("D3-reference-same-defect",
          "worker-008 reference candidate 98f9ec83 carries the same entailment defect",
          "entailment_direction_inverted" in kinds(f_ref),
          {"kinds": kinds(f_ref)}, "the reference candidate is clean under this checker.")

    # ---- corrected candidates ---------------------------------------------------
    corrected = live.replace(H1_LIVE, H1_FIXED).replace(H2_LIVE_FRAG, H2_CORRECTED_FRAG)
    nesting = live.replace(H1_LIVE, H1_FIXED).replace(H2_LIVE_FRAG, H2_NESTING_ONLY_FRAG)
    f_corr = findings_for(corrected, "C0", order)
    f_nest = findings_for(nesting, "C0", order)
    check("D4-corrected-clean", "corrected H2 wording (explicit right direction) is finding-free",
          kinds(f_corr) == [], {"kinds": kinds(f_corr)},
          "the corrected wording still yields a finding.")
    check("D5-nesting-only-clean", "alternate nesting+pointer wording is finding-free",
          kinds(f_nest) == [], {"kinds": kinds(f_nest)},
          "the alternate wording still yields a finding.")
    # only the two leaf edits differ from live
    dl = [i for i, (a, b) in enumerate(zip(live.splitlines(), corrected.splitlines()), 1) if a != b]
    expect_dl = sorted([line_of(live, "No containment with C2 or C0 is asserted here"),
                        line_of(live, "strictly larger extension class")])
    check("D6-corrected-minimal", "corrected candidate differs from live on exactly the two carrier lines",
          dl == expect_dl, {"changed_lines": dl, "expected": expect_dl},
          "extra lines change.")

    # ---- gate + blindness -------------------------------------------------------
    staged = {
        "candidate_84b5d3fa.yaml": write_staged("candidate_84b5d3fa.yaml", cand),
        "candidate_corrected.yaml": write_staged("candidate_corrected.yaml", corrected),
        "candidate_nesting_only.yaml": write_staged("candidate_nesting_only.yaml", nesting),
    }
    for k, v in staged.items():
        v["gate"] = run_gate(ROOT / v["path"])
    gate_live = run_gate(ROOT / LIVE_C0)
    check("G1-gate-blindness",
          "canonical structural gate passes live, the defective candidate, and both corrected candidates",
          gate_live["verdict"] == "pass"
          and all(staged[k]["gate"]["verdict"] == "pass" for k in staged),
          {"live": gate_live["verdict"],
           **{k: staged[k]["gate"]["verdict"] for k in staged}},
          "the gate distinguishes any of these texts; blindness is then refuted.")

    # ---- controls ---------------------------------------------------------------
    c2 = read(C2)
    c2_own = "AF-SCC-C2-VAC-GEN"
    f_c2 = findings_for(c2, "C2", order)
    c2_inverted = c2.replace(
        "so H2_loc-inextendibility ENTAILS this class's conclusion",
        "so this class's conclusion ENTAILS H2_loc-inextendibility",
    )
    f_c2_inv = findings_for(c2_inverted, "C2", order)
    cand_no_claim = cand.replace(
        ", so H2_loc-inextendibility ENTAILS this class's conclusion", "")
    f_cand_no_claim = findings_for(cand_no_claim, "C0", order)
    live_h1_only = live.replace(H1_LIVE, H1_FIXED)

    def control(cid, expect, got, note=""):
        controls.append({"id": cid, "expected": expect, "observed": got,
                         "pass": expect == got, "note": note})

    control("K1-live", ["false_containment_denial", "size_premise_inverted"], kinds(f_live))
    control("K2-candidate84b5d3fa",
            ["entailment_direction_inverted", "normative_contradiction"], kinds(f_cand))
    control("K3-reference98f9ec83",
            ["entailment_direction_inverted", "normative_contradiction"], kinds(f_ref))
    control("K4-corrected", [], kinds(f_corr))
    control("K5-nesting-only", [], kinds(f_nest))
    control("K6-C2-sibling-class-relative",
            [], kinds(f_c2),
            "the same sentence 'H2_loc-inextendibility ENTAILS this class's conclusion' is TRUE for own=C2")
    control("K7-C2-inverted-direction", ["entailment_direction_inverted"], kinds(f_c2_inv),
            "proves the checker flags the claim in the C2 context too, i.e. it is class-relative")
    control("K8-candidate-claim-deleted", [], kinds(f_cand_no_claim))
    control("K9-live-h1-fixed-only", ["false_containment_denial"],
            kinds(findings_for(live_h1_only, "C0", order)))
    n_ctl = sum(1 for c in controls if c["pass"])
    check("C1-controls", f"all {len(controls)} pre-registered controls match", n_ctl == len(controls),
          {"matched": n_ctl, "total": len(controls)},
          "any control departs from its pre-registered expectation.")

    # ---- post-run stability -----------------------------------------------------
    post = {p: sha256_path(ROOT / p) for p in PINS}
    stable = all(post[p] == PINS[p] for p in PINS)
    check("S1-post-stability", "no pinned byte moved during the run", stable,
          {"post": {p: post[p][:16] for p in PINS}},
          "any pinned input moves mid-run.")

    all_pass = all(c["pass"] for c in checks) and all(c["pass"] for c in controls)
    report = {
        "schema_version": "w080-audit/v1",
        "task_id": "W080-F2B-REPAIR-H2E-01",
        "actor": "worker-080",
        "generated_at": now(),
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
        "gate": "G-FORM",
        "target": {"path": LIVE_C0, "sha256": PINS[LIVE_C0],
                   "repair_candidate": {"path": str((STAGED / "candidate_84b5d3fa.yaml").relative_to(ROOT)),
                                        "sha256": CAND_84B5D3FA},
                   "reference_candidate": {"path": REF_CANDIDATE, "sha256": PINS[REF_CANDIDATE]},
                   "worker08_candidate": {"path": W08_CANDIDATE, "sha256": w08}},
        "pins": pins,
        "containment_model": order,
        "clauses": {
            "live_H1": {"line": line_of(live, "strictly larger extension class"), "quote": H1_LIVE},
            "live_H2": {"line": line_of(live, "No containment with C2 or C0 is asserted here"), "quote": H2_LIVE_FRAG},
            "chain": {"line": order["chain_line"], "quote": order["chain_text"]},
            "forbidden_weakening": {
                "line": line_of(live, "substituting H2_loc for C0"),
                "quote": [ln.strip() for ln in live.splitlines() if "substituting H2_loc for C0" in ln][0]},
            "candidate_H2_claim": {"line": cand_line,
                                   "quote": cand.splitlines()[cand_line - 1].strip()},
        },
        "checks": checks,
        "controls": controls,
        "findings": f_cand,
        "staged_candidates": staged,
        "verdict": ("REVISE the repair candidate at 84b5d3fa: the H1 edit is correct, but the H2 "
                    "replacement asserts 'H2_loc-inextendibility ENTAILS this class's conclusion' "
                    "inside the C0 file, contradicting the file's own chain (:238-243) and its own "
                    "forbidden_weakenings row (:232). Do not land as-is. Two finding-free corrected "
                    "candidates are staged."),
        "severity": "hard" if "entailment_direction_inverted" in kinds(f_cand) else "clean",
        "not_claimed": [
            "no canonical artifact was written or modified by worker-080",
            "no gate verdict, no node status, no validation_status=passed",
            "no claim about the mathematics of C0/C2 inextendibility; this is a text-consistency audit",
            "no claim that worker-017 or worker-066 missed the live defects they found; the finding is "
            "about the repair text, which their defect taxonomies do not cover",
            "no claim about which corrected wording the owner must adopt; two are staged",
        ],
        "next_falsifier": (
            "Re-run this harness at the pinned hashes. It is falsified if: (a) live F2b is not "
            "b2ab6acb2bbe or the FROZEN rev29 manifest does not declare it; (b) live+2 edits does not "
            "reproduce 84b5d3fa; (c) the file's chain can be read as making H2_loc-inextendibility "
            "entail C0-inextendibility, or the retained forbidden_weakenings row can be read as "
            "consistent with the candidate's H2 sentence; (d) the same claim string is not allowed in "
            "the C2 sibling under own=C2 (which would make this checker class-blind); (e) either "
            "corrected candidate yields a finding or fails the canonical gate; or (f) any pinned byte "
            "moves. Landing a repair that drops the entailment claim, or states the direction as "
            "C0-inext => H2loc-inext, voids the corresponding clause."
        ),
        "all_checks_pass": all_pass,
    }
    (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n",
                                     encoding="utf-8")
    print(json.dumps({"task_id": report["task_id"], "verdict": report["verdict"],
                      "findings": kinds(f_cand), "checks_pass": all_pass,
                      "controls": f"{n_ctl}/{len(controls)}",
                      "report_sha256": sha256_path(OUT / "report.json")}, ensure_ascii=False, indent=1))
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
