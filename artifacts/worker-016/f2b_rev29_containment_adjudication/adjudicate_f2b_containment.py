#!/usr/bin/env python3
"""W16-F2B-REV29-CONTAINMENT-ADJUDICATION-01.

Independent, deterministic, read-only adjudication of the adverse F2b verdicts cited
against the frozen rev29 pin, plus a repair-adequacy test of the four circulating
repair candidates.

Carriers adjudicated at the frozen pin:
  H1  implication_ledger.forbidden_transfers[0].reason  ("strictly larger")
  H2  regularity.must_not_conflate[0]                   ("No containment with C2 or C0 is asserted")
  V1  conclusion.conclusion_type                        (alias token vs F0 allowed list)
Repair-adequacy carrier (only meaningful for candidate bytes):
  H3  must_not_conflate[0] replacement asserting "H2_loc-inextendibility ENTAILS this class"
      -- true in the C2 sibling, false in the C0 file per its own chain / forbidden_weakenings.

Worker-level measurement only: no gate verdict, no node status, no canonical write.
Class: AF-SCC-C0-VAC-GEN (sibling control AF-SCC-C2-VAC-GEN). Gate: G-FORM. Node: F2b.

Pre-registered expectations (declared before the run, recorded in results.json):
  frozen / null copy          H1 fire, H2 fire, H3 clean, V1 divergence
  circulating 84b5d3fa        H1 clean, H2 clean, H3 FIRE (repair-induced)
  rev12 98f9ec83              H1 clean, H2 clean, H3 FIRE (repair-induced)
  corrected 51c253c4          H1 clean, H2 clean, H3 clean
  nesting 4951cc96            H1 clean, H2 clean, H3 clean
  synthetic re-inversion      H1 fires again
  synthetic denial insert     H2 fires again
  synthetic corrected flip    H3 clean (a landable one-line variant exists)

Exit code: 0 if every pre-registered expectation holds, 2 otherwise (run invalid).
"""
import datetime
import hashlib
import json
import os
import re
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = HERE
TASK_ID = "W16-F2B-REV29-CONTAINMENT-ADJUDICATION-01"
CLASS_ID = "AF-SCC-C0-VAC-GEN"
SIBLING_CLASS_ID = "AF-SCC-C2-VAC-GEN"
NODE_ID = "F2b"
GATE = "G-FORM"
ACTOR = "worker-016"

NOW = datetime.datetime.now().astimezone()
TS = NOW.strftime("%Y-%m-%dT%H:%M:%S%z")
TS = TS[:-2] + ":" + TS[-2:]

F2B = "schemas/af_scc_c0_vacuum.yaml"
F2B_MIRROR = "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
F2A = "schemas/af_scc_c2_vacuum.yaml"
FROZEN = "artifacts/formulation/FROZEN.json"
F0 = "research_map/formulation_taxonomy.yaml"
VOCAB = "artifacts/formulation/VOCAB_ALIASES.json"

DECLARED = {
    F2B: "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    F2B_MIRROR: "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    F2A: "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    FROZEN: "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    F0: "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    VOCAB: "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba",
}

W29 = "artifacts/worker-029/f2b_repair_candidate_verify/pinned/"
CANDIDATES = {
    "circulating_84b5d3fa": {
        "path": "artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_84b5d3fa.yaml",
        "declared_sha256": "84b5d3fa29a677ad157b924675bb5a9c08281395920be0221535465a5da44b40",
        "producer": "worker-080",
        "pinned_copy": W29 + "cand_circulating_84b5d3fa.yaml",
    },
    "rev12_98f9ec83": {
        "path": "artifacts/worker-066/f2b_rev29_containment_binding/pinned/candidate_98f9ec83__af_scc_c0_vacuum.yaml",
        "declared_sha256": "98f9ec83c487d6920968f0bdf98e03974813376b6d222b617300525eb13feb1c",
        "producer": "worker-066",
        "pinned_copy": W29 + "cand_rev12_98f9ec83.yaml",
    },
    "corrected_51c253c4": {
        "path": W29 + "cand_corrected_51c253c4.yaml",
        "declared_sha256": "51c253c463067e253dd32705f84d8ee089761439023acbbf1dd6660766191b7a",
        "producer": "worker-029",
        "pinned_copy": None,
    },
    "nesting_4951cc96": {
        "path": W29 + "cand_nesting_4951cc96.yaml",
        "declared_sha256": "4951cc96980329962829c2440c9e5c7f8ff5852eefd56aa48acfeeae8fb6505f",
        "producer": "worker-029",
        "pinned_copy": None,
    },
}

PREREGISTERED = {
    "frozen": {"H1_fires": True, "H2_fires": True, "H3_fires": False, "V1_divergence": True},
    "null_copy": {"H1_fires": True, "H2_fires": True, "H3_fires": False},
    "circulating_84b5d3fa": {"H1_fires": False, "H2_fires": False, "H3_fires": True},
    "rev12_98f9ec83": {"H1_fires": False, "H2_fires": False, "H3_fires": True},
    "corrected_51c253c4": {"H1_fires": False, "H2_fires": False, "H3_fires": False},
    "nesting_4951cc96": {"H1_fires": False, "H2_fires": False, "H3_fires": False},
    "synthetic_reinversion": {"H1_fires": True},
    "synthetic_denial": {"H2_fires": True},
    "synthetic_corrected_flip": {"H1_fires": False, "H2_fires": False, "H3_fires": False},
}


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def read_bytes(rel):
    with open(os.path.join(ROOT, rel), "rb") as fh:
        return fh.read()


def measure(rel):
    return sha256_bytes(read_bytes(rel))


def line_of(raw, needle):
    for i, ln in enumerate(raw.splitlines(), 1):
        if needle in ln:
            return i, ln.strip()
    return None, None


def chain_tokens(text):
    return re.findall(r"E_(?:\{[^}]*\}|[A-Za-z0-9_]+)", text)


def e_c2_position(chain_text):
    toks = chain_tokens(chain_text)
    if "E_C2" not in toks:
        return toks, "ambiguous"
    idx = toks.index("E_C2")
    has_contains = bool(re.search(r"\bcontains\b", chain_text, re.I))
    has_subset = bool(re.search(r"\bsubset\b", chain_text, re.I))
    if has_contains and not has_subset:
        rank = "smallest" if idx == len(toks) - 1 else ("largest" if idx == 0 else "middle")
    elif has_subset and not has_contains:
        rank = "smallest" if idx == 0 else ("largest" if idx == len(toks) - 1 else "middle")
    else:
        rank = "ambiguous"
    return toks, rank


def check_h1(doc, raw):
    rows = [r for r in doc["implication_ledger"]["forbidden_transfers"]
            if r.get("from") == "no proper future C2 extension" and r.get("to") == "this class"]
    if not rows:
        return {"id": "H1", "carrier": "implication_ledger.forbidden_transfers[0].reason",
                "fires": False, "error": "row not found"}
    reason = rows[0].get("reason", "")
    chain = doc["implication_ledger"]["extension_class_containment"]
    toks, rank = e_c2_position(chain)
    says_larger = bool(re.search(r"\blarger\b", reason, re.I))
    says_smaller = bool(re.search(r"\bsmaller\b", reason, re.I))
    fires = (says_larger and rank == "smallest") or (says_smaller and rank == "largest")
    ln, _ = line_of(raw, "forbidden_transfers")
    ln_reason, _ = line_of(raw, reason[:48])
    return {
        "id": "H1",
        "carrier": "implication_ledger.forbidden_transfers[0].reason",
        "line": ln_reason or ln,
        "fires": bool(fires),
        "premise_word": "larger" if says_larger else ("smaller" if says_smaller else None),
        "chain_tokens": toks,
        "e_c2_rank_in_chain": rank,
        "quote_reason": reason,
        "quote_chain": chain,
        "reading": ("reason premise is inverted against the file's own declared nesting "
                    "(E_C2 is the smallest extension set, so 'larger' is wrong)")
        if fires else "reason premise agrees with the declared nesting",
    }


def check_h2(doc, raw):
    entries = [e for e in doc["regularity"]["must_not_conflate"] if isinstance(e, str)]
    h2_entries = [e for e in entries if "H2_loc" in e]
    denial_entry = None
    denial_text = None
    for e in h2_entries:
        stripped = re.sub(r"\[[^\]]*\]", "", e)  # drop bracketed historical notes
        m = re.search(r"no\s+containment\s+with\s+(C2|C0|C\^?1,?1)", stripped, re.I)
        if m:
            denial_entry, denial_text = e, m.group(0)
            break
    chain = doc["implication_ledger"]["extension_class_containment"]
    entail = doc["implication_ledger"]["one_way_entailments"]
    entail_h2 = [r for r in entail if "H2_loc" in str(r.get("from", "")) or "H2_loc" in str(r.get("to", ""))]
    containment_asserted = ("E_H2loc" in chain_tokens(chain)) or bool(entail_h2)
    fires = denial_entry is not None and containment_asserted
    ln, _ = line_of(raw, "must_not_conflate")
    return {
        "id": "H2",
        "carrier": "regularity.must_not_conflate[0]",
        "line": ln,
        "fires": bool(fires),
        "denial_phrase": denial_text,
        "containment_asserted_elsewhere": containment_asserted,
        "n_h2_entailment_rows": len(entail_h2),
        "quote_entry": denial_entry,
        "reading": ("normative must_not_conflate denial contradicts the same file's asserted "
                    "containment chain / entailment rows") if fires else
                   "no containment denial remains in the normative list",
    }


def check_h3(doc, raw):
    """Repair-induced reversal: replacement says H2_loc-inextendibility entails THIS class."""
    entries = [e for e in doc["regularity"]["must_not_conflate"] if isinstance(e, str)]
    fired = None
    for e in entries:
        if "H2_loc" in e and re.search(r"H2_loc[- ]inextendibility\s+ENTAILS\s+this class", e, re.I):
            fired = e
            break
    fw = (doc.get("forbidden_weakenings")
          or (doc.get("conclusion") or {}).get("forbidden_weakenings") or [])
    fw_h2 = [r for r in fw if isinstance(r, str) and "H2_loc" in r]
    fw_says_weaker = any(re.search(r"H2_loc-inextendibility is weaker", r, re.I) for r in fw_h2)
    chain = doc["implication_ledger"]["extension_class_containment"]
    entail = doc["implication_ledger"]["one_way_entailments"]
    c0_to_h2 = [r for r in entail
                if "C0" in str(r.get("from", "")) and "H2_loc" in str(r.get("to", ""))
                and str(r.get("relation")) == "entails"]
    fires = fired is not None and fw_says_weaker and bool(c0_to_h2)
    ln, _ = line_of(raw, "must_not_conflate")
    return {
        "id": "H3",
        "carrier": "regularity.must_not_conflate[0] (repair replacement)",
        "line": ln,
        "fires": bool(fires),
        "quote_entry": fired,
        "forbidden_weakenings_says_h2loc_weaker": fw_says_weaker,
        "c0_entails_h2loc_rows": len(c0_to_h2),
        "quote_forbidden_weakenings": fw_h2[0] if fw_h2 else None,
        "reading": ("replacement asserts H2_loc-inextendibility entails the C0 conclusion; the "
                    "same file states H2_loc-inextendibility is weaker and that C0 entails "
                    "H2_loc, so the replacement is true of the C2 sibling but false here")
        if fires else "no reversed H2_loc entailment in the normative list",
    }


def check_v1(doc, f0, vocab):
    token = doc["conclusion"]["conclusion_type"]
    allowed = list(f0.get("field_vocabulary", {}).get("conclusion_type", {}).get("allowed", []))
    alias_map = vocab.get("conclusion_type", {})
    is_alias = token in alias_map and token not in allowed
    return {
        "id": "V1",
        "carrier": "conclusion.conclusion_type",
        "token": token,
        "f0_allowed": allowed,
        "vocab_alias_of": alias_map.get(token),
        "vocab_policy": vocab.get("policy"),
        "divergence": bool(is_alias),
    }


def flatten(o, prefix=""):
    out = {}
    if isinstance(o, dict):
        for k, v in o.items():
            out.update(flatten(v, "%s.%s" % (prefix, k) if prefix else str(k)))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            out.update(flatten(v, "%s[%d]" % (prefix, i)))
    else:
        out[prefix] = o
    return out


def diff_paths(a, b):
    fa, fb = flatten(a), flatten(b)
    changed = []
    for k in sorted(set(fa) | set(fb)):
        if fa.get(k, "<absent>") != fb.get(k, "<absent>"):
            kind = "prose_or_ledger" if any(s in k for s in (
                "must_not_conflate", "forbidden_transfers", "forbidden_weakenings",
                "one_way_entailments", "revision_history", "notes", "changelog")) else (
                "formal" if k.startswith("conclusion") or k.startswith("topology")
                or k.startswith("genericity") or k.startswith("regularity.extension")
                else "other")
            changed.append({"path": k, "kind": kind,
                            "frozen": str(fa.get(k, "<absent>"))[:160],
                            "candidate": str(fb.get(k, "<absent>"))[:160]})
    return changed


def evaluate(label, raw_bytes, f0, vocab, prereg):
    raw = raw_bytes.decode("utf-8")
    doc = yaml.safe_load(raw)
    h1 = check_h1(doc, raw)
    h2 = check_h2(doc, raw)
    h3 = check_h3(doc, raw)
    v1 = check_v1(doc, f0, vocab)
    actual = {"H1_fires": h1["fires"], "H2_fires": h2["fires"],
              "H3_fires": h3["fires"], "V1_divergence": v1["divergence"]}
    expected = {k: v for k, v in prereg.items() if k in actual}
    ok = all(actual[k] == v for k, v in expected.items())
    return {
        "label": label,
        "sha256_measured": sha256_bytes(raw_bytes),
        "H1": h1, "H2": h2, "H3": h3, "V1": v1,
        "preregistered": expected,
        "preregistered_holds": ok,
    }


def build_cluster_table():
    """Census of adverse verdicts bound to the frozen pin (read-only).

    carriers_claimed is a keyword-derived lower bound over hard_failure text; ids-only
    entries produce no carrier mapping.
    """
    import glob
    rows = []
    for p in sorted(glob.glob(os.path.join(ROOT, "reviews", "*.json"))):
        try:
            with open(p, "r", encoding="utf-8") as fh:
                blob = fh.read()
            d = json.loads(blob)
        except Exception:
            continue
        if not isinstance(d, dict) or "b2ab6acb2bbe" not in blob:
            continue
        verdict = str(d.get("verdict") or "").lower()
        if verdict not in ("revise", "reject"):
            continue
        created = str(d.get("created_at") or "")
        if created and created < "2026-09-12T00:50":
            continue
        hf = d.get("hard_failures") or []
        ids, carriers = [], set()
        for item in hf if isinstance(hf, list) else []:
            if isinstance(item, dict):
                if item.get("id"):
                    ids.append(str(item["id"]))
                f = str(item.get("field") or "")
                it = json.dumps(item).lower()
                if "forbidden_transfers" in f or "larger" in it:
                    carriers.add("H1_line246_larger")
                if "must_not_conflate" in f:
                    carriers.add("H2_line152_denial")
                if "conclusion" in f or "vocab" in it or "token" in it:
                    carriers.add("V1_conclusion_token")
                if "entails this class" in it or "direction" in it:
                    carriers.add("H3_repair_direction")
            elif isinstance(item, str):
                ids.append(item)
                it = item.lower()
                if "larger" in it:
                    carriers.add("H1_line246_larger")
                if "must_not_conflate" in it:
                    carriers.add("H2_line152_denial")
                if "entails this class" in it or "direction" in it:
                    carriers.add("H3_repair_direction")
        rows.append({
            "file": os.path.relpath(p, ROOT),
            "reviewer": d.get("reviewer") or d.get("actor"),
            "created_at": created,
            "verdict": verdict,
            "score": d.get("score"),
            "hard_failure_ids": ids,
            "carriers_claimed": sorted(carriers),
        })
    rows.sort(key=lambda r: (r["created_at"], r["file"]))
    carrier_counts = {}
    for r in rows:
        for c in r["carriers_claimed"]:
            carrier_counts[c] = carrier_counts.get(c, 0) + 1
    return {
        "pin": DECLARED[F2B],
        "window_start": "2026-09-12T00:50:00+08:00",
        "carrier_derivation": "keyword scan of hard_failure text; ids-only entries map to no carrier (lower bound)",
        "n_adverse_verdicts": len(rows),
        "carrier_counts": carrier_counts,
        "verdicts": rows,
    }


def main():
    results = {
        "task_id": TASK_ID,
        "actor": ACTOR,
        "class_id": CLASS_ID,
        "sibling_control_class_id": SIBLING_CLASS_ID,
        "node_id": NODE_ID,
        "gate": GATE,
        "generated_at": TS,
        "authority": ("worker measurement / adjudication evidence only; no node status, no "
                      "validation_status=passed, no gate verdict, no canonical write"),
        "pins_declared": DECLARED,
        "pins_measured": {},
    }
    pin_ok = True
    for rel, decl in DECLARED.items():
        try:
            meas = measure(rel)
        except Exception as exc:
            meas = "ERROR:%s" % exc
        results["pins_measured"][rel] = {"declared": decl, "measured": meas,
                                         "match": meas == decl}
        pin_ok = pin_ok and meas == decl
    results["pins_all_match"] = pin_ok
    if not pin_ok:
        results["exit_code"] = 2
        results["fatal"] = "pin mismatch; adjudication is not bound to the intended bytes"
        with open(os.path.join(OUT, "results.json"), "w", encoding="utf-8") as fh:
            json.dump(results, fh, indent=1)
            fh.write("\n")
        print("FATAL: pin mismatch")
        return 2

    f0 = yaml.safe_load(read_bytes(F0))
    vocab = json.loads(read_bytes(VOCAB))
    c0_raw = read_bytes(F2B)
    c2_raw = read_bytes(F2A)
    c2_doc = yaml.safe_load(c2_raw.decode("utf-8"))
    c0_doc = yaml.safe_load(c0_raw.decode("utf-8"))

    c2_chain = c2_doc["implication_ledger"]["extension_class_containment"]
    c2_toks, c2_rank = e_c2_position(c2_chain)
    c2_mnc = " ".join(e for e in c2_doc["regularity"]["must_not_conflate"] if isinstance(e, str))
    results["sibling_c2_control"] = {
        "path": F2A,
        "sha256": DECLARED[F2A],
        "chain_tokens": c2_toks,
        "e_c2_rank_in_chain": c2_rank,
        "chain_quote": c2_chain,
        "records_denial_as_corrected_error": bool(
            re.search(r"earlier\s+'no containment with C2 is asserted'\s+was wrong", c2_mnc, re.I)),
        "c2_conclusion_token": c2_doc["conclusion"]["conclusion_type"],
        "class_relativity_control": ("the identical H2_loc 'ENTAILS this class' sentence is true "
                                     "in the C2 sibling (E_C2 subset of E_H2loc) and false in the "
                                     "C0 file (E_H2loc subset of E_C0)"),
    }

    evaluations = []
    evaluations.append(evaluate("frozen", c0_raw, f0, vocab, PREREGISTERED["frozen"]))

    ctrl_dir = os.path.join(OUT, "controls")
    os.makedirs(ctrl_dir, exist_ok=True)
    with open(os.path.join(ctrl_dir, "null_copy_frozen.yaml"), "wb") as fh:
        fh.write(c0_raw)
    evaluations.append(evaluate("null_copy", c0_raw, f0, vocab, PREREGISTERED["null_copy"]))

    for name, spec in CANDIDATES.items():
        raw = read_bytes(spec["path"])
        meas = sha256_bytes(raw)
        ev = evaluate(name, raw, f0, vocab, PREREGISTERED[name])
        ev["candidate_path"] = spec["path"]
        ev["candidate_declared_sha256"] = spec["declared_sha256"]
        ev["candidate_hash_match"] = meas == spec["declared_sha256"]
        ev["producer"] = spec["producer"]
        if spec.get("pinned_copy"):
            pin_raw = read_bytes(spec["pinned_copy"])
            ev["pinned_copy"] = spec["pinned_copy"]
            ev["pinned_copy_byte_identical"] = pin_raw == raw
        ev["structural_diff_vs_frozen"] = diff_paths(c0_doc, yaml.safe_load(raw.decode("utf-8")))
        ev["formal_field_changes"] = [c for c in ev["structural_diff_vs_frozen"]
                                      if c["kind"] == "formal"]
        evaluations.append(ev)

    base = read_bytes(CANDIDATES["circulating_84b5d3fa"]["path"]).decode("utf-8")
    reinv = base.replace(
        "C2 is a strictly smaller extension class (E_C2 subset of E_C0)",
        "C2 is a strictly larger extension class (E_C2 subset of E_C0)", 1)
    assert reinv != base, "synthetic re-inversion string not found"
    evaluations.append(evaluate("synthetic_reinversion", reinv.encode("utf-8"), f0, vocab,
                                PREREGISTERED["synthetic_reinversion"]))
    den = base.replace(
        "The extension sets are nonetheless nested:",
        "No containment with C2 or C0 is asserted here. The extension sets are nonetheless nested:", 1)
    assert den != base, "synthetic denial string not found"
    evaluations.append(evaluate("synthetic_denial", den.encode("utf-8"), f0, vocab,
                                PREREGISTERED["synthetic_denial"]))
    flip = base.replace(
        "so H2_loc-inextendibility ENTAILS this class's conclusion",
        "so this class's conclusion ENTAILS H2_loc-inextendibility", 1)
    assert flip != base, "synthetic correction string not found"
    evaluations.append(evaluate("synthetic_corrected_flip", flip.encode("utf-8"), f0, vocab,
                                PREREGISTERED["synthetic_corrected_flip"]))

    results["evaluations"] = evaluations
    controls_ok = all(e["preregistered_holds"] for e in evaluations)
    results["pre_registered_predicates_hold"] = controls_ok

    frozen = evaluations[0]
    cand_by_label = {e["label"]: e for e in evaluations}
    findings = [
        {
            "id": "W16-F2B-REV29-H1",
            "carrier": "implication_ledger.forbidden_transfers[0].reason",
            "line": frozen["H1"]["line"],
            "status": "CONFIRMED" if frozen["H1"]["fires"] else "REFUTED",
            "severity_recommendation": "blocking-for-clean-accept",
            "basis": ("frozen text calls C2 the %s extension class while the same file's "
                      "extension_class_containment orders %s; the sibling C2 artifact records the "
                      "canonical ordering E_C2 subset E_{C^1,1} subset E_H2loc subset E_C0"
                      % (frozen["H1"]["premise_word"], " superset ".join(frozen["H1"]["chain_tokens"]))),
            "falsifier": ("a frozen revision in which forbidden_transfers[0].reason calls C2 the "
                          "smaller extension class (or states E_C2 subset of E_C0)"),
            "repaired_by": [lbl for lbl, e in cand_by_label.items()
                            if lbl in CANDIDATES and not e["H1"]["fires"]],
        },
        {
            "id": "W16-F2B-REV29-H2",
            "carrier": "regularity.must_not_conflate[0]",
            "line": frozen["H2"]["line"],
            "status": "CONFIRMED" if frozen["H2"]["fires"] else "REFUTED",
            "severity_recommendation": "blocking-for-clean-accept",
            "basis": ("the normative entry denies 'no containment with C2 or C0' for H2_loc while "
                      "the same file asserts %d H2_loc entailment row(s) and the sibling C2 "
                      "artifact marks that exact denial as a corrected error"
                      % frozen["H2"]["n_h2_entailment_rows"]),
            "authorship_disclosure": ("the frozen entry cites worker-16 F2b-16-02; at the rev29 "
                                      "canonical ordering that earlier accepted wording is "
                                      "superseded, so this finding is recorded as a worker-16 "
                                      "self-correction, not a third-party accusation"),
            "falsifier": ("a frozen revision whose must_not_conflate list no longer denies H2_loc "
                          "containment"),
            "repaired_by": [lbl for lbl, e in cand_by_label.items()
                            if lbl in CANDIDATES and not e["H2"]["fires"]],
        },
        {
            "id": "W16-F2B-REV29-H3",
            "carrier": "regularity.must_not_conflate[0] (repair replacement only)",
            "line": frozen["H3"]["line"],
            "status": ("CONFIRMED-IN-CANDIDATES"
                       if any(cand_by_label[l]["H3"]["fires"] for l in
                              ("circulating_84b5d3fa", "rev12_98f9ec83")) else "REFUTED"),
            "severity_recommendation": "blocking-for-landing-the-circulating-candidates",
            "basis": ("candidates 84b5d3fa and 98f9ec83 replace the denial with an assertion that "
                      "H2_loc-inextendibility ENTAILS this class's conclusion; the same file states "
                      "H2_loc-inextendibility is weaker and lists C0 => H2_loc as the entailment, so "
                      "the replacement is true of the C2 sibling and false in the C0 file "
                      "(class-relativity control)"),
            "independent_of": "worker-029 review F2b-repair-candidate-verify-worker-029.json (raised first)",
            "falsifier": ("a candidate whose H2_loc replacement keeps the entailment direction "
                          "C0 => H2_loc (or makes no entailment claim)"),
            "closed_by": [lbl for lbl in ("corrected_51c253c4", "nesting_4951cc96")
                          if not cand_by_label[lbl]["H3"]["fires"]],
        },
        {
            "id": "W16-F2B-REV29-V1",
            "carrier": "conclusion.conclusion_type",
            "status": "CONFIRMED-DIVERGENCE" if frozen["V1"]["divergence"] else "REFUTED",
            "severity_recommendation": "non-blocking (severity already adjudicated by worker-066)",
            "basis": ("token '%s' is an accepted alias of '%s' but is absent from the F0 allowed "
                      "list %s; VOCAB policy forbids alias tokens in a new canonical artifact"
                      % (frozen["V1"]["token"], frozen["V1"]["vocab_alias_of"],
                         frozen["V1"]["f0_allowed"])),
            "falsifier": ("an F0/VOCAB revision that re-stamps '%s' as canonical, or a frozen "
                          "artifact using one of %s" % (frozen["V1"]["token"],
                                                        frozen["V1"]["f0_allowed"])),
            "repaired_by": [lbl for lbl, e in cand_by_label.items()
                            if lbl in CANDIDATES and not e["V1"]["divergence"]],
        },
    ]
    results["findings"] = findings
    results["repair_adequacy"] = {}
    for lbl in CANDIDATES:
        e = cand_by_label[lbl]
        landable = (not e["H1"]["fires"]) and (not e["H2"]["fires"]) and (not e["H3"]["fires"])
        results["repair_adequacy"][lbl] = {
            "producer": e["producer"],
            "hash_match": e.get("candidate_hash_match"),
            "pinned_copy_byte_identical": e.get("pinned_copy_byte_identical"),
            "closes_H1": not e["H1"]["fires"],
            "closes_H2": not e["H2"]["fires"],
            "introduces_H3": e["H3"]["fires"],
            "closes_V1": not e["V1"]["divergence"],
            "landable_under_this_checker": landable,
            "formal_field_changes": e.get("formal_field_changes"),
            "changed_paths": [c["path"] for c in e.get("structural_diff_vs_frozen", [])],
        }
    results["adjudication"] = {
        "H1": findings[0]["status"],
        "H2": findings[1]["status"],
        "H3": findings[2]["status"],
        "V1": findings[3]["status"],
        "landable_candidates": [lbl for lbl, a in results["repair_adequacy"].items()
                                if a["landable_under_this_checker"]],
        "not_landable_candidates": [lbl for lbl, a in results["repair_adequacy"].items()
                                    if not a["landable_under_this_checker"]],
        "summary": ("at the frozen rev29 pin the adverse H1/H2 carriers are reproduced; the two "
                    "circulating repairs close them but introduce a reversed H2_loc entailment "
                    "(H3), independently reproduced here; the corrected/nesting candidates are "
                    "finding-free under this checker; no candidate re-stamps the V1 alias token"),
        "gate_effect": ("worker-level evidence for astra-life05-verify-gform-r3; worker-016 does "
                        "not move G-FORM and adopts no candidate"),
    }
    results["cluster_table"] = build_cluster_table()
    results["exit_code"] = 0 if controls_ok else 2
    results["not_claimed"] = [
        "no node completion", "no theorem", "no gate verdict",
        "no canonical artifact write", "no adoption of any repair candidate",
    ]

    with open(os.path.join(OUT, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=1)
        fh.write("\n")
    with open(os.path.join(OUT, "cluster_table.json"), "w", encoding="utf-8") as fh:
        json.dump(results["cluster_table"], fh, indent=1)
        fh.write("\n")

    print("pins_all_match:", pin_ok)
    for e in evaluations:
        print("%-24s H1=%s H2=%s H3=%s prereg_ok=%s" % (
            e["label"], e["H1"]["fires"], e["H2"]["fires"], e["H3"]["fires"],
            e["preregistered_holds"]))
    print("findings:", {f["id"]: f["status"] for f in findings})
    print("landable:", results["adjudication"]["landable_candidates"],
          "| not:", results["adjudication"]["not_landable_candidates"])
    print("exit_code:", results["exit_code"])
    return results["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
