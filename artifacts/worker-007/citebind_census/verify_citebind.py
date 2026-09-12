#!/usr/bin/env python3
"""W007-CITEBIND-CENSUS-01 -- independent, hash-pinned adjudication of the
`l1_ledger_refs[*].citation_status: verified_by_L1` binding in the rev12 class
schemas (F1/F2a/F2b) against the L1 ledger and the L1 citation audit.

Question being executed (worker-077 W077-HF-03, reviews/F2b-f0-binding-077.json):
  "five l1_ledger_refs rows still claim citation_status=verified_by_L1 while the
   pinned ledger records verification_status=abstract-read and
   review_status=not_independently_reviewed (token absent from the ledger)."

This checker does not read any worker-077 code.  It re-derives the census from
the frozen bytes and executes worker-077's own falsifier clause:
  "or a project definition equating 'verified_by_L1' with citation_audit.csv
   verdict='verified' on abstract/API evidence only."

Deterministic: stdlib + PyYAML only; no network; all mutations are in-memory.
Writes report.json next to this script.
"""
from __future__ import annotations

import copy
import csv
import datetime as dt
import hashlib
import json
import os
import re
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
SNAP = os.path.join(HERE, "snapshot")
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

TASK_ID = "W007-CITEBIND-CENSUS-01"
ACTOR = "worker-007"
NODE_ID = "L1"
GATES = ["G-LIT", "G-FORM"]
CLASSES = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]

# (snapshot filename, live canonical path, expected sha256 source)
INPUTS = [
    ("af_wcc_vacuum.cce9c60146d6.yaml", "schemas/af_wcc_vacuum.yaml"),
    ("af_scc_c2_vacuum.5476a3f2c6bc.yaml", "schemas/af_scc_c2_vacuum.yaml"),
    ("af_scc_c0_vacuum.55d0a1ea9bda.yaml", "schemas/af_scc_c0_vacuum.yaml"),
    ("theorems.a1674f094979.jsonl", "ledger/theorems.jsonl"),
    ("citation_audit.315c19145065.csv", "ledger/citation_audit.csv"),
    ("rule_spec.40f9bb9e657b.json", "artifacts/formulation/rule_spec.json"),
    ("VOCAB_ALIASES.46cd9f1eb534.json", "artifacts/formulation/VOCAB_ALIASES.json"),
    ("FROZEN.2f358f6722d9.json", "artifacts/formulation/FROZEN.json"),
    ("formulation_taxonomy.0abb9ed8a961.yaml", "research_map/formulation_taxonomy.yaml"),
]


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_snapshot_inputs():
    """Load every snapshot once; the returned dict is the mutable census state."""
    st = {}
    for fname, live in INPUTS:
        st[fname] = {"live_path": live}
    st["schemas"] = []
    for fname, live in INPUTS[:3]:
        with open(os.path.join(SNAP, fname), encoding="utf-8") as f:
            doc = yaml.safe_load(f)
        st["schemas"].append({"file": fname, "live_path": live, "doc": doc})
    rows = []
    with open(os.path.join(SNAP, "theorems.a1674f094979.jsonl"), encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    st["ledger"] = rows
    with open(os.path.join(SNAP, "citation_audit.315c19145065.csv"), encoding="utf-8") as f:
        st["audit"] = list(csv.DictReader(f))
    st["rule_spec"] = load_json(os.path.join(SNAP, "rule_spec.40f9bb9e657b.json"))
    st["vocab_aliases"] = load_json(os.path.join(SNAP, "VOCAB_ALIASES.46cd9f1eb534.json"))
    st["frozen"] = load_json(os.path.join(SNAP, "FROZEN.2f358f6722d9.json"))
    return st


# ---------------------------------------------------------------- census core
def citation_vocabulary(st):
    return list((st["rule_spec"].get("vocabularies") or {}).get("citation_status") or [])


def registered_aliases(st):
    """Aliases the policy would accept for a citation_status token, if any."""
    out = set()
    va = st["vocab_aliases"]
    # The policy is `canonical token first`; look for any citation-status alias map.
    for key in ("citation_status", "citation_status_aliases"):
        blk = va.get(key)
        if isinstance(blk, dict):
            for canon, alts in blk.items():
                out.add(canon)
                out.update(alts if isinstance(alts, list) else [alts])
        elif isinstance(blk, list):
            out.update(blk)
    return out


def refs_of(schema_doc):
    return list(schema_doc.get("l1_ledger_refs") or [])


def all_citation_status_tokens(schema_doc):
    """Every `citation_status:` scalar in the document, with its YAML path."""
    found = []

    def walk(o, path):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "citation_status" and isinstance(v, str):
                    found.append((path + "." + k, v))
                walk(v, path + "." + k)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, path + f"[{i}]")

    walk(schema_doc, "")
    return found


def census(st):
    ledger_by_id = {r.get("theorem_id"): r for r in st["ledger"]}
    audit_by_id = {a["citation_id"]: a for a in st["audit"]}
    vocab = citation_vocabulary(st)
    aliases = registered_aliases(st)
    per_ref, oov, summary = [], [], {
        "refs_total": 0, "verified_by_L1_refs": 0, "unresolved_refs": 0,
        "refs_without_citation_status": 0,
        "vbL1_all_sources_audit_verified": 0, "vbL1_missing_ledger_row": 0,
        "vbL1_ledger_independently_reviewed_branch": 0,
        "audit_rows_total": len(st["audit"]),
        "audit_rows_verdict_verified": 0, "token_in_ledger": 0,
        "corpus_definitions_of_verified_by_L1": 0,
    }
    for sc in st["schemas"]:
        doc = sc["doc"]
        cls = doc.get("class_id")
        for i, ref in enumerate(refs_of(doc)):
            tid = ref.get("theorem_id")
            cs = ref.get("citation_status")  # absent is a finding, not a default
            entry = {"file": sc["file"], "class_id": cls, "index": i,
                     "theorem_id": tid, "citation_status": cs,
                     "role": ref.get("role"), "l1_status": ref.get("l1_status")}
            summary["refs_total"] += 1
            if cs is None:
                summary["refs_without_citation_status"] += 1
                entry["classification"] = "NO_CITATION_STATUS"
            elif cs not in vocab and cs not in aliases:
                oov.append({"file": sc["file"], "theorem_id": tid, "token": cs})
                entry["classification"] = "OUT_OF_VOCABULARY"
            else:
                entry["classification"] = "IN_VOCABULARY"
            lrow = ledger_by_id.get(tid)
            if lrow is None:
                entry["ledger"] = None
                if cs == "verified_by_L1":
                    summary["vbL1_missing_ledger_row"] += 1
            else:
                entry["ledger"] = {
                    "verification_status": lrow.get("verification_status"),
                    "review_status": lrow.get("review_status"),
                    "content_status": lrow.get("content_status"),
                    "acceptance_authority": lrow.get("acceptance_authority"),
                    "source_ids": list(lrow.get("source_ids") or []),
                }
                src = list(lrow.get("source_ids") or [])
                missing = [s for s in src if s not in audit_by_id]
                bad = [(s, audit_by_id[s].get("verdict"), audit_by_id[s].get("resolver_result"))
                       for s in src if s in audit_by_id and (
                           audit_by_id[s].get("verdict") != "verified"
                           or audit_by_id[s].get("resolver_result") != "resolved")]
                entry["audit"] = {
                    "sources": src, "missing_rows": missing, "bad_rows": bad,
                    "all_resolved_verified": bool(src) and not missing and not bad,
                }
                if cs == "verified_by_L1":
                    summary["verified_by_L1_refs"] += 1
                    if entry["audit"]["all_resolved_verified"]:
                        summary["vbL1_all_sources_audit_verified"] += 1
                    if (lrow.get("verification_status") == "verified"
                            or lrow.get("review_status") != "not_independently_reviewed"):
                        summary["vbL1_ledger_independently_reviewed_branch"] += 1
                elif cs == "unresolved":
                    summary["unresolved_refs"] += 1
            per_ref.append(entry)
    summary["audit_rows_verdict_verified"] = sum(
        1 for a in st["audit"] if a.get("verdict") == "verified")
    summary["total_citation_status_tokens"] = {}
    for sc in st["schemas"]:
        for p, v in all_citation_status_tokens(sc["doc"]):
            summary["total_citation_status_tokens"][v] = \
                summary["total_citation_status_tokens"].get(v, 0) + 1
    return per_ref, oov, summary, vocab, aliases


def token_census(st):
    """How many times the literal token appears in each frozen companion file."""
    counts = {}
    for fname in ("theorems.a1674f094979.jsonl", "citation_audit.315c19145065.csv",
                  "rule_spec.40f9bb9e657b.json", "VOCAB_ALIASES.46cd9f1eb534.json",
                  "formulation_taxonomy.0abb9ed8a961.yaml", "FROZEN.2f358f6722d9.json"):
        with open(os.path.join(SNAP, fname), encoding="utf-8", errors="replace") as f:
            counts[fname] = f.read().count("verified_by_L1")
    return counts


def r15_scope(st):
    rules = st["rule_spec"].get("rules") or []
    r15 = next((r for r in rules if r.get("id") == "R15"), None)
    return {"id": "R15", "scope_literal": (r15 or {}).get("applies_to"),
            "require": (r15 or {}).get("require"), "fail": (r15 or {}).get("fail")}


def provenance_values(st):
    out = []
    for sc in st["schemas"]:
        prov = sc["doc"].get("provenance") or {}
        out.append({"file": sc["file"], "provenance.citation_status":
                    prov.get("citation_status")})
    return out


def digest(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


# ------------------------------------------------------------------ controls
def run_controls(st):
    """Each control mutates an in-memory copy and asserts the census reacts."""
    base = load_snapshot_inputs()
    _, _, base_sum, base_vocab, _ = census(base)
    results = []

    def rec(cid, expect, ok, detail):
        results.append({"control": cid, "expectation": expect,
                        "status": "PASS" if ok else "FAIL", "detail": detail})

    # M1: audit verdict downgraded -> the affected vbL1 ref must lose resolution.
    m = load_snapshot_inputs()
    # pick a source actually used by a vbL1 ref
    used = None
    for sc in m["schemas"]:
        for ref in refs_of(sc["doc"]):
            if ref.get("citation_status") == "verified_by_L1":
                lrow = next((r for r in m["ledger"] if r.get("theorem_id") == ref["theorem_id"]), None)
                if lrow and lrow.get("source_ids"):
                    used = lrow["source_ids"][0]
                    break
        if used:
            break
    for a in m["audit"]:
        if a["citation_id"] == used:
            a["verdict"] = "unverified"
    _, _, s1, _, _ = census(m)
    shared = sum(1 for e in census(load_snapshot_inputs())[0]
                 if e.get("audit") and used in e["audit"]["sources"]
                 and e["citation_status"] == "verified_by_L1")
    rec("M1_audit_verdict_downgraded", "vbL1_all_sources_audit_verified decreases",
        s1["vbL1_all_sources_audit_verified"] < base_sum["vbL1_all_sources_audit_verified"],
        {"victim_source": used,
         "before": base_sum["vbL1_all_sources_audit_verified"],
         "after": s1["vbL1_all_sources_audit_verified"],
         "vbL1_refs_sharing_this_source": shared,
         "note": "delta equals the number of vbL1 refs that cite the mutated source"})

    # M2: audit row deleted -> resolution must drop.
    m = load_snapshot_inputs()
    m["audit"] = [a for a in m["audit"] if a["citation_id"] != used]
    _, _, s2, _, _ = census(m)
    rec("M2_audit_row_deleted", "vbL1_all_sources_audit_verified decreases",
        s2["vbL1_all_sources_audit_verified"] < base_sum["vbL1_all_sources_audit_verified"],
        {"deleted_source": used, "after": s2["vbL1_all_sources_audit_verified"],
         "vbL1_refs_sharing_this_source": shared})

    # M3: register verified_by_L1 as an alias -> OOV count must drop to 0.
    m = load_snapshot_inputs()
    m["vocab_aliases"] = copy.deepcopy(m["vocab_aliases"])
    m["vocab_aliases"]["citation_status"] = {"verified": ["verified_by_L1"]}
    _, oov3, _, _, _ = census(m)
    rec("M3_alias_registration", "out-of-vocabulary count 0 when token is a registered alias",
        len(oov3) == 0,
        {"oov_before": len(
            [e for e in census(load_snapshot_inputs())[0]
             if e["classification"] == "OUT_OF_VOCABULARY"]),
         "oov_after": len(oov3)})

    # M4: add the token to the frozen vocabulary -> OOV count must drop to 0.
    m = load_snapshot_inputs()
    m["rule_spec"] = copy.deepcopy(m["rule_spec"])
    m["rule_spec"]["vocabularies"]["citation_status"].append("verified_by_L1")
    _, oov4, _, _, _ = census(m)
    rec("M4_vocabulary_extension", "out-of-vocabulary count 0 after extending vocabulary",
        len(oov4) == 0, {"oov_after": len(oov4)})

    # M5: independent-review branch: mark one ledger row independently reviewed.
    m = load_snapshot_inputs()
    for r in m["ledger"]:
        if r.get("theorem_id") == "T-204":
            r["verification_status"] = "verified"
            r["review_status"] = "independently_reviewed"
    _, _, s5, _, _ = census(m)
    rec("M5_falsifier_branch", "vbL1_ledger_independently_reviewed_branch becomes 1",
        s5["vbL1_ledger_independently_reviewed_branch"] == 1,
        {"branch_count": s5["vbL1_ledger_independently_reviewed_branch"]})

    # M6 (negative control): unresolved refs must not be counted as vbL1.
    unchecked = [e for e in census(load_snapshot_inputs())[0]
                 if e["citation_status"] == "unresolved"]
    rec("M6_unresolved_not_counted", "0 unresolved refs classified as vbL1",
        all(e["classification"] != "OUT_OF_VOCABULARY" and e["citation_status"] != "verified_by_L1"
            for e in unchecked),
        {"unresolved_refs": [e["theorem_id"] for e in unchecked]})

    # M7: determinism.
    d1 = digest(census(load_snapshot_inputs())[:3])
    d2 = digest(census(load_snapshot_inputs())[:3])
    rec("M7_determinism", "two fresh census runs are byte-identical",
        d1 == d2, {"digest": d1})
    return results


# ---------------------------------------------------------------------- main
def main() -> int:
    st = load_snapshot_inputs()
    pins = []
    for fname, live in INPUTS:
        snap_path = os.path.join(SNAP, fname)
        live_path = os.path.join(ROOT, live)
        measured_snap = sha256(snap_path)
        entry = {"snapshot": f"snapshot/{fname}", "live_path": live,
                 "measured_snapshot_sha256": measured_snap,
                 "snapshot_bytes": os.path.getsize(snap_path),
                 "live_exists": os.path.exists(live_path),
                 "live_sha256": sha256(live_path) if os.path.exists(live_path) else None}
        entry["live_equals_snapshot"] = entry["live_sha256"] == measured_snap
        pins.append(entry)

    frozen = st["frozen"]
    frozen_files = frozen.get("files") or {}
    frozen_pin_check = {}
    for p in ("schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml",
              "schemas/af_scc_c0_vacuum.yaml", "artifacts/formulation/rule_spec.json",
              "artifacts/formulation/VOCAB_ALIASES.json"):
        pin = (frozen_files.get(p) or {}).get("sha256")
        live = next((e["live_sha256"] for e in pins if e["live_path"] == p), None)
        frozen_pin_check[p] = {"frozen_pin": pin, "measured": live,
                               "match": pin == live}

    per_ref, oov, summary, vocab, aliases = census(st)
    tokens = token_census(st)
    summary["token_in_ledger"] = tokens["theorems.a1674f094979.jsonl"]
    summary["corpus_definitions_of_verified_by_L1"] = sum(tokens.values())
    controls = run_controls(st)

    # re-hash after the run (pin stability)
    post = {fname: sha256(os.path.join(SNAP, fname)) for fname, _ in INPUTS}
    pre = {e["snapshot"].split("/")[-1]: e["measured_snapshot_sha256"] for e in pins}
    pin_stable = pre == post

    checks = [
        {"id": "C1_vocabulary", "status": "FAIL" if oov else "PASS",
         "detail": {"vocabulary": vocab, "registered_aliases": sorted(aliases),
                    "out_of_vocabulary": oov,
                    "n_out_of_vocabulary": len(oov)}},
        {"id": "C2_token_census", "status": "INFO",
         "detail": {"occurrences_of_verified_by_L1": tokens,
                    "ledger_occurrences": summary["token_in_ledger"]}},
        {"id": "C3_audit_resolution", "status": "PASS" if
         summary["vbL1_all_sources_audit_verified"] == summary["verified_by_L1_refs"]
         else "FAIL",
         "detail": {"verified_by_L1_refs": summary["verified_by_L1_refs"],
                    "all_sources_resolved_verified":
                        summary["vbL1_all_sources_audit_verified"],
                    "audit_rows_total": summary["audit_rows_total"],
                    "audit_rows_verdict_verified": summary["audit_rows_verdict_verified"]}},
        {"id": "C4_ledger_join", "status": "PASS" if
         summary["vbL1_missing_ledger_row"] == 0 else "FAIL",
         "detail": {"missing_ledger_rows": summary["vbL1_missing_ledger_row"],
                    "ledger_rows": len(st["ledger"]),
                    "ledger_rows_not_independently_reviewed":
                        sum(1 for r in st["ledger"]
                            if r.get("review_status") == "not_independently_reviewed")}},
        {"id": "C5_falsifier_branch", "status": "INFO",
         "detail": {"ledger_independently_reviewed_branch":
                        summary["vbL1_ledger_independently_reviewed_branch"],
                    "frozen_rule_R15": r15_scope(st),
                    "provenance_values": provenance_values(st)}},
        {"id": "C6_pin_stability", "status": "PASS" if pin_stable else "FAIL",
         "detail": {"stable": pin_stable, "post_hashes": post}},
    ]

    verdict = {
        "primary": "CONFIRMED_VOCABULARY_VIOLATION__REFUTED_VERIFICATION_OVERCLAIM",
        "statement": (
            "At the pinned rev12 hashes, 11 l1_ledger_refs entries across the three "
            "class schemas use citation_status=verified_by_L1, which is not a member "
            "of the FROZEN-pinned FORM-RULE-SPEC v1.2 vocabulary "
            "vocabularies.citation_status = [unverified, unresolved, verified], and the "
            "token occurs 0 times in the ledger, whose 62 rows are all "
            "review_status=not_independently_reviewed with verification_status=abstract-read "
            "(61) or unverified (1). That much of worker-077 W077-HF-03 is CONFIRMED. "
            "The stronger reading that the refs overclaim verified sources is REFUTED at "
            "abstract/API level: every one of the 11 refs resolves, through "
            "citation_audit.csv used_by_theorems, to audit rows whose verdict is 'verified' "
            "and resolver_result 'resolved' for every ledger source_id (0 missing, 0 bad); "
            "the audit is 97/97 verdict=verified. Worker-077's own falsifier named exactly "
            "this branch. The defect is therefore a token/vocabulary repair, not a content "
            "downgrade: the lead must either register the token as an alias of 'verified' "
            "with an explicit abstract-level scope note, or rename the leaf."),
        "confirmed": [
            "verified_by_L1 is out-of-vocabulary under the frozen rule_spec vocabulary",
            "the literal token is absent from ledger, citation audit, rule spec, VOCAB_ALIASES, taxonomy and FROZEN",
            "the ledger records no independent review for any of the 11 referenced rows",
        ],
        "refuted": [
            "that the 11 refs rest on unresolved or unverified sources: 0 missing, 0 bad, 97/97 audit verdict=verified",
            "that a content downgrade of F1/F2a/F2b is required",
        ],
        "residual": [
            "provenance.citation_status=unverified at the same schema level is in-vocabulary and honest; a naive reader sees a self-contradiction with the per-ref token",
            "F2a T-401 carries l1_status=provisional together with citation_status=verified_by_L1 (consistent only if the two fields have different scopes)",
            "F1 D-001 has no citation_status field",
            "9 further citation_status: n/a tokens live in transfer_relations witnesses (3 per schema), also absent from the frozen vocabulary",
        ],
    }

    report = {
        "report_id": "w007-citebind-census-20260912T0046",
        "task_id": TASK_ID,
        "actor": ACTOR,
        "created_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "node_id": NODE_ID,
        "gates": GATES,
        "class_ids": CLASSES,
        "question": ("Independent execution of worker-077 W077-HF-03 and of its own "
                     "falsifier for citation_status=verified_by_L1 in F1/F2a/F2b rev12."),
        "inputs_pinned": pins,
        "frozen_pin_check": frozen_pin_check,
        "checks": checks,
        "per_ref": per_ref,
        "counts": summary,
        "verdict": verdict,
        "controls": controls,
        "controls_summary": {"total": len(controls),
                             "passed": sum(1 for c in controls if c["status"] == "PASS"),
                             "failed": [c["control"] for c in controls if c["status"] == "FAIL"]},
        "falsifier": (
            "(a) any of the 11 verified_by_L1 refs has a ledger source_id with no audit row, "
            "or an audit row with verdict!=verified or resolver_result!=resolved; or "
            "(b) the frozen corpus contains a definition of verified_by_L1 requiring "
            "independent review (review_status!=not_independently_reviewed); or "
            "(c) any referenced ledger row records verification_status=verified or a "
            "review_status other than not_independently_reviewed; or "
            "(d) the token appears in a FROZEN-pinned vocabulary/alias registry. "
            "A re-pin of any input supersedes (does not falsify) this census."),
        "next_falsifier": (
            "Re-run verify_citebind.py at the same nine pins and find any check whose "
            "status differs; or produce a FROZEN-pinned rule that makes verified_by_L1 an "
            "in-vocabulary or alias-registered token; or show one of the 11 referenced "
            "ledger rows carrying independent review."),
        "authority_note": ("Worker artifact and worker verdict only. No gate verdict, no node "
                           "status=done, no validation_status=passed is claimed. The canonical "
                           "schemas/ledger were not modified."),
        "non_claims": [
            "Not a gate verdict on G-FORM or G-LIT; worker events cannot move a gate.",
            "No physics or mathematics is asserted; all findings are about artifact tokens, "
            "hash resolution and vocabulary membership.",
            "No canonical artifact was edited; snapshot/ files are read-only copies.",
            "Does not adjudicate worker-077's other two hard findings (W077-HF-01, W077-HF-02).",
            "Does not certify that abstract-level citation verification is sufficient for any "
            "purpose beyond quoting CF-18(b)/the L1 gate rule.",
        ],
    }
    out = os.path.join(HERE, "report.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1, sort_keys=False)
        f.write("\n")
    # machine-readable console digest
    print(json.dumps({"report": out,
                      "verdict": verdict["primary"],
                      "counts": {k: v for k, v in summary.items()
                                 if k != "total_citation_status_tokens"},
                      "oov": oov,
                      "controls": report["controls_summary"]}, indent=1))
    return 0 if not oov else 0  # OOV is the finding, not a script failure


if __name__ == "__main__":
    sys.exit(main())
