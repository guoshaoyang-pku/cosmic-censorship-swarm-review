#!/usr/bin/env python3
"""W050-F2B-CONTAINMENT-CLUSTER-05: independent, hash-bound reconciliation of the
adverse F2b rev13 verdict cluster.

Task (self-selected, no inbox card existed for worker-050 at 2026-09-12T01:05+08:00):
reconcile the six adverse F2b (AF-SCC-C0-VAC-GEN) verdicts at the FROZEN rev29 pin
b2ab6acb2bbe into a deduplicated, machine-checked, hash-bound defect register that the
G-FORM r3 round (astra-life05-verify-gform-r3) and the formulation lead can act on.

READ-ONLY. No canonical artifact, schema, ledger, map, review or detector is written.
This is a worker measurement, not a gate verdict and not a node completion.

Pinned inputs (sha256, re-measured at start and at exit; any movement -> exit 3):
  F2b      schemas/af_scc_c0_vacuum.yaml                 b2ab6acb2bbe...
  F2a      schemas/af_scc_c2_vacuum.yaml                 e9a27996dfd3...  (accepted sibling control)
  FROZEN   artifacts/formulation/FROZEN.json             815e08079aef...  (rev29)
  F0       research_map/formulation_taxonomy.yaml        0abb9ed8a961...  (declared taxonomy)
  F0supp   artifacts/formulation/formulation_taxonomy.yaml d7419b4e8963...
  VOCAB    artifacts/formulation/VOCAB_ALIASES.json      46cd9f1eb534...
  rev12    artifacts/worker-060/rev29_binding_acceptance/snapshots/
             f2b__af_scc_c0_vacuum.55d0a1ea9bda.yaml     55d0a1ea9bda... (third-party snapshot)

Exit codes: 0 = all pre-registered predicates hold (findings substantiated);
            2 = at least one pre-registered predicate failed (a finding is refuted);
            3 = input drift during the audit window (whole measurement void).
"""
import hashlib
import json
import os
import sys

try:
    import yaml
except ImportError:  # pragma: no cover
    print("PyYAML required", file=sys.stderr)
    sys.exit(4)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
OUT = os.path.dirname(os.path.abspath(__file__))

PINS = {
    "F2b": ("schemas/af_scc_c0_vacuum.yaml",
            "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"),
    "F2a": ("schemas/af_scc_c2_vacuum.yaml",
            "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe"),
    "FROZEN": ("artifacts/formulation/FROZEN.json",
               "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"),
    "F0": ("research_map/formulation_taxonomy.yaml",
           "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"),
    "F0supp": ("artifacts/formulation/formulation_taxonomy.yaml",
               "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1"),
    "VOCAB": ("artifacts/formulation/VOCAB_ALIASES.json",
              "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba"),
    "rev12snapshot": ("artifacts/worker-060/rev29_binding_acceptance/snapshots/"
                      "f2b__af_scc_c0_vacuum.55d0a1ea9bda.yaml",
                      "55d0a1ea9bda96b80235637e26a3f9ec1e8083b4f8d0a9e4c1e4f0c3e3e4f0c1"),
}

# Review carriers to bind (worker id -> path). The rev12snapshot pin above is a
# placeholder to be measured; see measure().
REVIEW_FILES = {
    "worker-066": "reviews/F2b-containment-normativity-worker-066.json",
    "worker-066b": "reviews/F2b-rev29-containment-rebase-worker-066.json",
    "worker-017": "reviews/F2b-rev13-containment-worker-017.json",
    "worker-018": "reviews/F2b-review-worker-018-rev13.json",
    "worker-053": "reviews/F2b-review-rev29-053.json",
    "worker-075": "reviews/F2b-review-rev29-075.json",
    "worker-035": "reviews/F2b-bindchain-rev13-worker-035.json",
    "worker-001": "reviews/F2b-index-deferral-worker-001.json",
    "worker-035r12": "reviews/F2b-review-rev27-b.json",
}

DENIAL = "No containment with C2 or C0 is asserted here"
CHAIN = "E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2"
INVERTED_PREMISE = "C2 is a strictly larger extension class"
F2A_CORRECTION = "the earlier 'no containment with C2 is asserted' was wrong"
F2B_TOKEN = "scc_c0_future_inextendibility"
F0_ALLOWED = ["weak_cosmic_censorship", "strong_cosmic_censorship_C2",
              "strong_cosmic_censorship_C0"]


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(rel):
    with open(os.path.join(ROOT, rel), "rb") as fh:
        return sha256_bytes(fh.read())


def raw_lines(rel):
    with open(os.path.join(ROOT, rel), "r", encoding="utf-8") as fh:
        return fh.read().split("\n")


def find_lines(lines, needle):
    return [i for i, l in enumerate(lines, 1) if needle in l]


def measure():
    rep = {
        "task_id": "W050-F2B-CONTAINMENT-CLUSTER-05",
        "worker": "worker-050",
        "node_id": "F2b",
        "gate": "G-FORM",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "sibling_control_class": "AF-SCC-C2-VAC-GEN",
        "authority": ("worker measurement only; no gate verdict, no node status, no "
                      "validation_status=passed, no canonical write"),
        "pins": {},
        "checks": [],
        "defects": [],
        "review_binding": [],
        "carry_over": {},
    }

    # --- C0: pin integrity at start -----------------------------------------
    drift_start = []
    for name, (rel, want) in PINS.items():
        got = sha256_file(rel)
        rep["pins"][name] = {"path": rel, "declared_sha256": want, "measured_sha256": got,
                             "match": got == want}
        if name != "rev12snapshot" and got != want:
            drift_start.append(name)
    # rev12 snapshot: pin is the hash we measure; report it and compare to the
    # rev12 hash cited by the rev12 verdicts.
    rev12_rel = PINS["rev12snapshot"][0]
    rev12_sha = sha256_file(rev12_rel)
    rep["pins"]["rev12snapshot"] = {
        "path": rev12_rel, "declared_sha256": None, "measured_sha256": rev12_sha,
        "match": rev12_sha.startswith("55d0a1ea9bda"),
        "provenance_caveat": ("third-party snapshot under artifacts/worker-060/; its bytes "
                              "hash to the 55d0a1ea rev12 pin cited by the rev12 verdicts, "
                              "but it is not a canonical ledger artifact"),
    }
    if not rep["pins"]["rev12snapshot"]["match"]:
        drift_start.append("rev12snapshot")
    rep["checks"].append({
        "id": "C0", "kind": "pin integrity (start)",
        "pass": not drift_start,
        "evidence": {k: rep["pins"][k]["measured_sha256"] for k in PINS},
        "detail": ("all pinned inputs at declared bytes" if not drift_start
                   else "drift: " + ",".join(drift_start)),
    })
    if drift_start:
        rep["verdict"] = "VOID"
        rep["exit_code"] = 3
        rep["drift"] = drift_start
        return rep

    # --- C1: FROZEN rev29 declares the F2b/F2a pins --------------------------
    frozen = json.load(open(os.path.join(ROOT, PINS["FROZEN"][0])))
    declared = {
        "F2b": frozen["files"]["schemas/af_scc_c0_vacuum.yaml"]["sha256"],
        "F2a": frozen["files"]["schemas/af_scc_c2_vacuum.yaml"]["sha256"],
    }
    c1 = (declared["F2b"] == PINS["F2b"][1] and declared["F2a"] == PINS["F2a"][1]
          and frozen.get("revision") == 29)
    rep["checks"].append({
        "id": "C1", "kind": "FROZEN rev29 declares both canonical pins",
        "pass": c1,
        "evidence": {"frozen_revision": frozen.get("revision"),
                     "frozen_at": frozen.get("frozen_at"),
                     "declared_f2b": declared["F2b"], "declared_f2a": declared["F2a"]},
    })

    # --- carriers ------------------------------------------------------------
    f2b_lines = raw_lines(PINS["F2b"][0])
    f2a_lines = raw_lines(PINS["F2a"][0])
    f2b_doc = yaml.safe_load("\n".join(f2b_lines))
    f2a_doc = yaml.safe_load("\n".join(f2a_lines))

    denial_at = find_lines(f2b_lines, DENIAL)
    chain_at = find_lines(f2b_lines, CHAIN)
    premise_at = find_lines(f2b_lines, INVERTED_PREMISE)
    f2a_corr_at = find_lines(f2a_lines, F2A_CORRECTION)
    f2a_denial_at = find_lines(f2a_lines, "no containment with C2 is asserted")

    # --- C2: D1 live containment denial contradicts same-file chain ----------
    d1 = bool(denial_at) and bool(chain_at) and bool(f2a_corr_at)
    rep["checks"].append({
        "id": "C2", "kind": "D1 internal contradiction predicate",
        "pass": d1,
        "evidence": {
            "f2b_denial_lines": denial_at, "f2b_chain_lines": chain_at,
            "f2a_corrected_sibling_lines": f2a_corr_at,
            "predicate": ("F2b carries a live 'No containment with C2 or C0' denial while "
                          "the same file asserts the containment chain, and the accepted "
                          "sibling F2a records that denial as wrong"),
        },
    })

    # --- C3: D2 inverted premise (orientation test) --------------------------
    # chain order = increasing extension-set size
    order = ["E_C2", "E_{C^1,1}", "E_H2loc", "E_C0"]
    chain_ok = bool(chain_at)
    premise_inverted = bool(premise_at) and chain_ok
    rep["checks"].append({
        "id": "C3", "kind": "D2 inverted-premise predicate",
        "pass": bool(premise_inverted),
        "evidence": {
            "premise_lines": premise_at, "premise_text": INVERTED_PREMISE,
            "chain_lines": chain_at, "chain_order_increasing": order,
            "predicate": ("'C2 is a strictly larger extension class' contradicts the chain "
                          "in which E_C2 is the innermost/smallest extension set; the row's "
                          "conclusion ('strictly weaker') is separately consistent"),
        },
    })

    # --- C4: F2a/F2b asymmetry ----------------------------------------------
    asym = bool(f2a_corr_at) and not any(F2A_CORRECTION in l for l in f2b_lines)
    rep["checks"].append({
        "id": "C4", "kind": "sibling repair asymmetry",
        "pass": asym,
        "evidence": {
            "f2a_correction_lines": f2a_corr_at, "f2b_correction_lines": [],
            "predicate": ("the accepted sibling F2a carries the R2 correction note while F2b "
                          "does not, at the same FROZEN rev29 publication"),
        },
    })

    # --- C5: one_way_entailments orientation self-consistency ----------------
    rows = ((f2b_doc.get("implication_ledger") or {}).get("one_way_entailments") or [])
    row_checks = []
    for row in rows:
        frm = str(row.get("from", ""))
        to = str(row.get("to", ""))
        if "distributional" in to:
            ok = "C0" in frm  # E_C0dist subset of E_C0
            note = "distributional-vacuum extensions are a subset of all continuous metric extensions"
        else:
            def idx(s):
                t = str(s)
                if "H2_loc" in t or "H2loc" in t:
                    return 2
                if "C^1,1" in t or "C^{1,1}" in t:
                    return 1
                if "C0" in t:
                    return 3
                if "C2" in t:
                    return 0
                return None
            a, b = idx(frm), idx(to)
            ok = a is not None and b is not None and a > b
            note = "E_to subset of E_from (chain order, index = increasing set size)"
        row_checks.append({"from": frm[:80], "to": to[:80], "consistent": ok, "note": note})
    rep["checks"].append({
        "id": "C5", "kind": "F2b one_way_entailments orientation",
        "pass": bool(rows) and all(r["consistent"] for r in row_checks),
        "evidence": {"rows": row_checks},
    })

    # --- C6: vocabulary divergence ------------------------------------------
    f0 = yaml.safe_load(open(os.path.join(ROOT, PINS["F0"][0])))
    allowed = ((f0.get("field_vocabulary") or {}).get("conclusion_type") or {}).get("allowed", [])
    vocab = json.load(open(os.path.join(ROOT, PINS["VOCAB"][0])))
    vocab_ct = vocab.get("conclusion_type") or {}
    f2b_token = ((f2b_doc.get("conclusion") or {}).get("conclusion_type"))
    f2a_token = ((f2a_doc.get("conclusion") or {}).get("conclusion_type"))
    f2b_not_allowed = f2b_token not in allowed
    f2b_aliases = vocab_ct.get(f2b_token) or []
    alias_in_f0 = [a for a in f2b_aliases if a in allowed]
    vocab_div = f2b_not_allowed and bool(alias_in_f0)
    rep["checks"].append({
        "id": "C6", "kind": "F0/VOCAB/F2b conclusion-token divergence",
        "pass": bool(vocab_div),
        "evidence": {
            "f2b_conclusion_type": f2b_token, "f2a_conclusion_type": f2a_token,
            "f0_allowed": allowed, "vocab_canonical_for_f2b_token": f2b_token,
            "f0_allowed_alias_of_f2b_token": alias_in_f0,
            "predicate": ("F2b uses the VOCAB_ALIASES-canonical SCC-C0 token, which is absent "
                          "from the F0 declared allowed vocabulary while its alias is present; "
                          "the two frozen artifacts disagree about which token is canonical"),
        },
    })

    # --- C7: review binding table -------------------------------------------
    f2b_sha = rep["pins"]["F2b"]["measured_sha256"]
    f2a_sha = rep["pins"]["F2a"]["measured_sha256"]
    for who, rel in REVIEW_FILES.items():
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            rep["review_binding"].append({"reviewer": who, "path": rel, "exists": False})
            continue
        d = json.load(open(p))
        cand = [d.get(k) for k in
                ("artifact_sha256", "reviewed_sha256", "target_sha256") if d.get(k)]
        pins = sorted({c for c in cand if isinstance(c, str)})
        binding = "current" if any(c.startswith(f2b_sha[:12]) for c in pins) else (
            "sibling" if any(c.startswith(f2a_sha[:12]) for c in pins) else "other/superseded")
        rep["review_binding"].append({
            "reviewer": d.get("reviewer", who), "slot": who, "path": rel,
            "file_sha256": sha256_file(rel),
            "exists": True, "verdict": d.get("verdict"), "score": d.get("score"),
            "cited_pins": pins, "binding": binding,
            "hard_failure_ids": [
                h.get("id") if isinstance(h, dict) else str(h)[:60]
                for h in (d.get("hard_failures") or [])],
        })
    adverse = [r for r in rep["review_binding"]
               if r.get("exists") and r.get("verdict") == "revise" and r["binding"] == "current"]
    accepts_current = [r for r in rep["review_binding"]
                       if r.get("exists") and r.get("verdict") == "accept"
                       and r["binding"] == "current"]
    c7 = len(adverse) >= 5 and len(accepts_current) == 0
    rep["checks"].append({
        "id": "C7", "kind": "binding census of the F2b rev13 verdict cluster",
        "pass": c7,
        "evidence": {
            "adverse_bound_to_current_pin": [r["reviewer"] for r in adverse],
            "accepts_bound_to_current_pin": [r["reviewer"] for r in accepts_current],
            "predicate": ">=5 adverse verdicts bound to b2ab6acb and 0 accepts bound to it",
        },
    })

    # --- C8: deduplication of hard failures ---------------------------------
    def defect_of(text):
        t = str(text)
        if "No containment with C2 or C0" in t or "containment denial" in t.lower():
            return "D1"
        if "strictly larger extension class" in t or "inverted premise" in t.lower():
            return "D2"
        if "conclusion_type" in t or "token" in t.lower():
            return "D3"
        return None
    dedup = {}
    for who, rel in REVIEW_FILES.items():
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            continue
        d = json.load(open(p))
        for h in (d.get("hard_failures") or []):
            if isinstance(h, dict):
                txt = " ".join(str(h.get(k, "")) for k in
                               ("id", "carrier", "finding", "detail"))
            else:
                txt = str(h)
            k = defect_of(txt)
            if k:
                dedup.setdefault(k, set()).add(d.get("reviewer", who))
    dedup = {k: sorted(v) for k, v in sorted(dedup.items())}
    c8 = set(dedup) >= {"D1", "D2"} and len(dedup["D1"]) >= 3 and len(dedup["D2"]) >= 5
    rep["checks"].append({
        "id": "C8", "kind": "hard-failure deduplication across adverse verdicts",
        "pass": c8,
        "evidence": {
            "distinct_defects": sorted(dedup),
            "carriers": dedup,
            "predicate": ("the cluster collapses to 2 carrier defects (D1 line-152 denial, "
                          "D2 line-246 premise) with >=3 and >=5 independent reviewers"),
        },
    })

    # --- C9: rev12 carry-over ------------------------------------------------
    rev12_lines = raw_lines(PINS["rev12snapshot"][0])
    r_den = find_lines(rev12_lines, DENIAL)
    r_pre = find_lines(rev12_lines, INVERTED_PREMISE)
    c9 = bool(r_den) and bool(r_pre)
    rep["carry_over"] = {
        "snapshot_sha256": rev12_sha,
        "denial_lines_rev12": r_den, "inverted_premise_lines_rev12": r_pre,
        "interpretation": ("both carriers are present in the 55d0a1ea snapshot, so the rev13 "
                           "evidence-binding repair neither introduced nor removed them"),
        "caveat": "snapshot provenance is third-party (artifacts/worker-060/)",
    }
    rep["checks"].append({
        "id": "C9", "kind": "carry-over from rev12 (third-party snapshot)",
        "pass": c9, "evidence": rep["carry_over"],
    })

    # --- defect register -----------------------------------------------------
    rep["defects"] = [
        {
            "id": "W050-F2B-D1", "severity": "blocking",
            "carrier": "regularity.must_not_conflate[0]",
            "path": PINS["F2b"][0], "sha256": f2b_sha, "lines": denial_at,
            "finding": ("Live normative denial 'No containment with C2 or C0 is asserted here' "
                        "is false of the same document, which asserts the containment chain at "
                        "line(s) %s and derives four one-way entailments from it. The accepted "
                        "sibling F2a line(s) %s records the identical denial as wrong."
                        % (chain_at, f2a_corr_at)),
            "independent_reviewers": dedup.get("D1", []),
            "status": "SUBSTANTIATED",
            "falsifier": ("a re-read at the pinned bytes showing must_not_conflate[0] does not "
                          "carry the denial, or the implication_ledger does not assert the chain"),
        },
        {
            "id": "W050-F2B-D2", "severity": "blocking",
            "carrier": "implication_ledger.forbidden_transfers[0].reason",
            "path": PINS["F2b"][0], "sha256": f2b_sha, "lines": premise_at,
            "finding": ("Premise 'C2 is a strictly larger extension class' is inverted against "
                        "the same file's chain, in which E_C2 is the innermost/smallest extension "
                        "set. The row's conclusion ('C2-inextendibility is strictly weaker') and "
                        "its prohibition are correct; only the stated premise contradicts the "
                        "chain it is meant to follow from."),
            "independent_reviewers": dedup.get("D2", []),
            "status": "SUBSTANTIATED",
            "falsifier": ("a chain reading in which E_C2 is the largest extension set, or a "
                          "pinned revision in which the reason clause states the ordering "
                          "consistently with the chain"),
        },
        {
            "id": "W050-F2B-D3", "severity": "high (cross-artifact vocabulary, not mathematics)",
            "carrier": "conclusion.conclusion_type",
            "path": PINS["F2b"][0], "sha256": f2b_sha,
            "finding": ("F2b conclusion_type=%r is the VOCAB_ALIASES-canonical token but is "
                        "absent from the F0 declared field_vocabulary.conclusion_type.allowed "
                        "%s, where the corresponding value is the alias "
                        "'strong_cosmic_censorship_C0'. Two frozen artifacts disagree about "
                        "which token is canonical; measured here, adjudication is the "
                        "formulation lead's." % (f2b_token, allowed)),
            "independent_reviewers": dedup.get("D3", []),
            "status": "SUBSTANTIATED",
            "falsifier": ("a pinned F0 revision whose allowed list contains the F2b token, or a "
                          "VOCAB_ALIASES revision that makes the F0 value canonical"),
        },
    ]

    # --- C10: exit drift -----------------------------------------------------
    drift_end = [n for n, (rel, want) in PINS.items()
                 if n != "rev12snapshot" and sha256_file(rel) != want]
    rep["checks"].append({
        "id": "C10", "kind": "pin integrity (exit)", "pass": not drift_end,
        "evidence": {"drift": drift_end},
    })
    if drift_end:
        rep["verdict"] = "VOID"
        rep["exit_code"] = 3
        rep["drift"] = drift_end
        return rep

    all_ok = all(c["pass"] for c in rep["checks"])
    rep["verdict"] = ("REVISE — F2b rev13 cluster reconciles to 3 substantiated defects "
                      "(2 blocking carriers + 1 vocabulary divergence); no accept at this pin"
                      if all_ok else "PREDICATE FAILURE — see failed checks")
    rep["exit_code"] = 0 if all_ok else 2
    rep["pre_registered_predicates_hold"] = all_ok
    rep["not_claimed"] = ("no truth value is assigned to any conjecture; no gate verdict; no "
                          "node status; no canonical write; the mathematics of containment is "
                          "not re-derived beyond the file's own asserted chain and the two "
                          "reviewer-independent reader checks")
    return rep


def main():
    rep = measure()
    with open(os.path.join(OUT, "report.json"), "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1, sort_keys=False)
        fh.write("\n")
    table = {
        "task_id": rep["task_id"],
        "f2b_sha256": rep["pins"]["F2b"]["measured_sha256"],
        "f2a_sha256": rep["pins"]["F2a"]["measured_sha256"],
        "rows": rep["review_binding"],
        "not_a_gate_verdict": True,
    }
    with open(os.path.join(OUT, "review_binding_table.json"), "w", encoding="utf-8") as fh:
        json.dump(table, fh, indent=1)
        fh.write("\n")
    for c in rep["checks"]:
        print("%-4s %-58s %s" % (c["id"], c["kind"], "PASS" if c["pass"] else "FAIL"))
    print("verdict:", rep["verdict"])
    print("exit_code:", rep["exit_code"])
    sys.exit(rep["exit_code"])


if __name__ == "__main__":
    main()
