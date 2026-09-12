#!/usr/bin/env python3
"""W080-F2B-HF1-DIRECTION-CENSUS-01.

Semantic direction census of the F2b (AF-SCC-C0-VAC-GEN) HF1/HF2 repair wordings,
at FROZEN rev29 815e08079aef and live F2b b2ab6acb2bbe.

Motivation. worker-070's byte census (report.json#1be0cdb611fa) shows 9/10 declared
repair candidates discharge the two standing carriers byte-wise, but its predicates
P1/P2 only require that the defective phrases are *absent*; they do not check the
*direction* of the replacement sentence. The previous repair (84b5d3fa) failed
exactly there: its HF1 replacement asserts "H2_loc-inextendibility ENTAILS this
class's conclusion", the reverse of the direction recorded in the same file's
`implication_ledger`. This instrument classifies each candidate's HF1 and HF2
prose against the entailment order derived from that candidate's own machine-readable
`implication_ledger.one_way_entailments`, and returns the semantically landable set.

Ground truth is derived from the bytes under test, not hardcoded:
  * E_C2 subset E_C0 is read off a `one_way_entailments` row (own -> C2);
  * "H2_loc-inextendibility entails C2" is read off the H2LOC -> C2 row;
  * "this class's conclusion entails H2_loc-inextendibility" off the own -> H2LOC row.

Read-only on every canonical path. Writes only under this artifact directory.
No gate verdict, no node status, no canonical write.
"""

import hashlib
import json
import os
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
SNAP = os.path.join(HERE, "snapshots")
TZ = timezone(timedelta(hours=8))

TASK_ID = "W080-F2B-HF1-DIRECTION-CENSUS-01"
ACTOR = "worker-080"
CLASS_ID = "AF-SCC-C0-VAC-GEN"
NODE_ID = "F2b"
GATE = "G-FORM"

PINS = {
    "schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "artifacts/formulation/FROZEN.json": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/VOCAB_ALIASES.json": "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba",
    "artifacts/formulation/VARIANT_REGISTRY.json": "6bac9adea19e17efe625342ef4d2098e3775491aa3d0e06596cd5d75912348fb",
    "artifacts/worker-070/f2b_candidate_census/report.json": "1be0cdb611fa88e1ecbe5211c7ced084b54d71ca2935e353d927928b506199f5",
    "artifacts/worker-070/f2b_candidate_census/frame.json": "20687555b7f5800b07465e9cb01cd4648959196b5c31a7bef2f0ff8c359e1368",
}

INVARIANT_PATHS = [
    ("class_id",),
    ("node_id",),
    ("conclusion", "conclusion_type"),
    ("conclusion", "statement_formal"),
    ("implication_ledger", "extension_class_containment"),
    ("implication_ledger", "one_way_entailments"),
    ("f0_binding", "declared_f0_sha256"),
    ("regularity", "extension_regularity"),
]

TOKEN_RE = re.compile(
    r"(this class(?:'s conclusion)?|C0-inextendibility|C2-inextendibility|H2[ _]?loc-inextendibility"
    r"|C2 sibling(?:'s conclusion)?)",
    re.I,
)
VERB_RE = re.compile(r"\b(is entailed by|are entailed by|entails|entail|implies|imply)\b", re.I)
DENIAL_RE = re.compile(r"no\s+containment\s+with\s+C2\s+or\s+C0", re.I)
NEST_RE = re.compile(r"subset|contains|nested|nesting", re.I)
NEG_REVERSE_RE = re.compile(r"never the reverse|not the reverse|not conversely|and not conversely", re.I)
BRACKET_RE = re.compile(r"\[[^\]]*\]")
NEG_OBJ_RE = re.compile(r"\bnot\s+$", re.I)
CITED_CLAUSE_RE = re.compile(
    r"the informal phrase 'strictly between' is (?:not used|not a class definition) and must not be cited",
    re.I,
)


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(path):
    with open(path, "rb") as fh:
        return sha256_bytes(fh.read())


def now_iso():
    return datetime.now(TZ).isoformat(timespec="seconds")


def canon(text):
    """Map an entailment-row endpoint or an inextendibility token to a class id."""
    if text is None:
        return None
    t = str(text).lower()
    if "h2_loc" in t or "h2loc" in t:
        return "H2LOC"
    if "c2" in t:
        return "C2"
    if "c0" in t:
        return "C0"
    return None


def tok_id(tok, own):
    t = tok.lower()
    if t.startswith("this class"):
        return own
    if "h2" in t:
        return "H2LOC"
    if "c2" in t:
        return "C2"
    if "c0" in t:
        return "C0"
    return None

def ledger_pairs(doc):
    pairs = set()
    for row in doc.get("implication_ledger", {}).get("one_way_entailments", []) or []:
        if str(row.get("relation")) == "entails":
            a, b = canon(row.get("from")), canon(row.get("to"))
            if a and b:
                pairs.add((a, b))
    return pairs


def own_token(doc):
    return canon(doc.get("regularity", {}).get("extension_regularity")) or "C0"


def extract_pairs(text, own):
    """Asserted directed entailment pairs from prose. Reverses for passive voice.

    An object token immediately negated ("... not this class") is excluded rather
    than read as a positive assertion.
    """
    out = []
    for sentence in re.split(r"(?<=[.;:])\s+", text):
        verbs = list(VERB_RE.finditer(sentence))
        if not verbs:
            continue
        toks = [(m.start(), m.group(0), tok_id(m.group(0), own)) for m in TOKEN_RE.finditer(sentence)]
        if not toks:
            continue
        for vm in verbs:
            before = [t for t in toks if t[0] < vm.start()]
            after = [t for t in toks if t[0] >= vm.end()]
            if not before or not after:
                continue
            subj, obj = before[-1][2], after[0][2]
            if subj is None or obj is None or subj == obj:
                continue
            prefix = sentence[max(0, after[0][0] - 6):after[0][0]]
            if NEG_OBJ_RE.search(prefix):
                continue
            if "entailed by" in vm.group(0).lower():
                out.append((obj, subj))
            else:
                out.append((subj, obj))
    seen, uniq = set(), []
    for p in out:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    return uniq


def classify_hf1(doc):
    text = str(doc.get("regularity", {}).get("must_not_conflate", [""])[0])
    clean = BRACKET_RE.sub(" ", text)
    own = own_token(doc)
    pairs = ledger_pairs(doc)
    asserted = extract_pairs(clean, own)
    inverted = [p for p in asserted if p not in pairs and (p[1], p[0]) in pairs]
    unsupported = [p for p in asserted if p not in pairs and (p[1], p[0]) not in pairs]
    neg_rev = bool(NEG_REVERSE_RE.search(clean))
    denial = bool(DENIAL_RE.search(clean))
    nesting = bool(NEST_RE.search(clean))

    if denial:
        cls = "DENIAL"
    elif inverted:
        cls = "INVERTED"
    elif unsupported:
        cls = "UNSUPPORTED"
    elif asserted:
        cls = "CORRECT"
    elif nesting:
        cls = "NEUTRAL_NESTING"
    else:
        cls = "AMBIGUOUS"
    return {
        "classification": cls,
        "own_token": own,
        "asserted_pairs": ["%s->%s" % p for p in asserted],
        "ledger_pairs": sorted("%s->%s" % p for p in pairs),
        "inverted_pairs": ["%s->%s" % p for p in inverted],
        "unsupported_pairs": ["%s->%s" % p for p in unsupported],
        "negated_reverse": neg_rev,
        "phrase_self_reference": ("strictly between" in CITED_CLAUSE_RE.sub(" ", clean).lower()),
        "text": text,
    }


def classify_hf2(doc):
    own = own_token(doc)
    pairs = ledger_pairs(doc)
    rows = doc.get("implication_ledger", {}).get("forbidden_transfers", []) or []
    if not rows:
        return {"classification": "MISSING", "text": ""}
    row = rows[0]
    a, b = canon(row.get("from")), tok_id(str(row.get("to") or ""), own)
    reason = str(row.get("reason", ""))
    low = reason.lower()
    if "strictly larger" in low or "largest extension" in low:
        size_claim = "C2_LARGER"
    elif "strictly smaller" in low or "smallest extension" in low:
        size_claim = "C2_SMALLER"
    elif "stronger regularity" in low and "strictly weaker" in low:
        size_claim = "C2_SMALLER"
    else:
        size_claim = None
    if (own, "C2") in pairs:
        truth = "C2_SMALLER"
    elif ("C2", own) in pairs:
        truth = "C2_LARGER"
    else:
        truth = None
    structure_ok = a == "C2" and b == own
    if not structure_ok:
        cls = "STRUCTURE_BROKEN"
    elif size_claim is None:
        cls = "UNSUPPORTED"
    elif truth is None:
        cls = "NO_GROUND_TRUTH"
    elif size_claim == truth:
        cls = "CORRECT"
    else:
        cls = "INVERTED"
    return {
        "classification": cls,
        "from": row.get("from"),
        "to": row.get("to"),
        "size_claim": size_claim,
        "derived_truth": truth,
        "text": reason,
    }


def get_path(doc, path):
    cur = doc
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return "<absent>"
        cur = cur[key]
    return cur


def invariants_vs_live(doc, live):
    diffs = []
    for path in INVARIANT_PATHS:
        a, b = get_path(doc, path), get_path(live, path)
        if json.dumps(a, sort_keys=True) != json.dumps(b, sort_keys=True):
            diffs.append(".".join(path))
    return diffs


REGISTRY_CLAIM_RE = re.compile(r"VARIANT_REGISTRY|variant_id|parent_class|registered\s+VARIANT", re.I)


def registry_claim(doc, variant_registry):
    """Verify a candidate's variant-registry prose claim against the pinned registry."""
    text = str(doc.get("regularity", {}).get("must_not_conflate", [""])[0])
    if not REGISTRY_CLAIM_RE.search(text):
        return {"referenced": False, "ok": None}
    own = doc.get("class_id")
    hits = [v for v in variant_registry.get("variants", []) or []
            if v.get("variant_id") == "H2LOC" and v.get("parent_class") == own]
    return {
        "referenced": True,
        "ok": bool(hits),
        "matched": hits[0].get("variant_id") if hits else None,
        "matched_parent": hits[0].get("parent_class") if hits else None,
        "matched_status": hits[0].get("status") if hits else None,
    }


def classify_doc(doc, live, variant_registry):
    hf1 = classify_hf1(doc)
    hf2 = classify_hf2(doc)
    diffs = invariants_vs_live(doc, live)
    reg = registry_claim(doc, variant_registry)
    soft = []
    if hf1.get("phrase_self_reference"):
        soft.append("hf1_uses_phrase_declared_not_used: 'strictly between' appears in the slot that says the phrase is not used")
    landable = (
        hf1["classification"] in ("CORRECT", "NEUTRAL_NESTING")
        and hf2["classification"] == "CORRECT"
        and not diffs
        and reg.get("ok") is not False
    )
    return {"hf1": hf1, "hf2": hf2, "invariant_diffs": diffs, "registry_claim": reg,
            "soft_findings": soft, "semantically_landable": landable}


def snapshot(path, tag, manifest):
    src = os.path.join(ROOT, path)
    dst = os.path.join(SNAP, "%s__%s" % (tag, os.path.basename(path)))
    shutil.copyfile(src, dst)
    a, b = sha256_file(src), sha256_file(dst)
    assert a == b, "snapshot byte-identity failed for %s" % path
    manifest.append({"path": path, "snapshot": os.path.relpath(dst, ROOT), "sha256": a, "byte_identical": True})
    return a


def main():
    started = now_iso()
    problems = []

    # ---- pins ---------------------------------------------------------------
    pins_before = {}
    for path, want in PINS.items():
        full = os.path.join(ROOT, path)
        if not os.path.exists(full):
            problems.append("missing pin %s" % path)
            continue
        got = sha256_file(full)
        pins_before[path] = got
        if got != want:
            problems.append("pin drift before run: %s %s != %s" % (path, got[:12], want[:12]))
    if problems:
        print("FAIL-CLOSED:", problems)
        return 2

    live = yaml.safe_load(open(os.path.join(ROOT, "schemas/af_scc_c0_vacuum.yaml")))
    variant_registry = json.load(open(os.path.join(ROOT, "artifacts/formulation/VARIANT_REGISTRY.json")))
    w070 = json.load(open(os.path.join(ROOT, "artifacts/worker-070/f2b_candidate_census/report.json")))

    snapshots = []
    for path in PINS:
        snapshot(path, "pin", snapshots)

    # ---- candidates ---------------------------------------------------------
    rows = []
    for entry in w070["registry_resolution"]:
        sha = entry["sha256"]
        rel = entry["primary_path"]
        full = os.path.join(ROOT, rel)
        row = {
            "sha256": sha,
            "author": entry.get("author"),
            "label": entry.get("label"),
            "path": rel,
            "resolved": False,
        }
        if not os.path.exists(full):
            row["error"] = "primary path missing"
            rows.append(row)
            continue
        got = sha256_file(full)
        if got != sha:
            row["error"] = "primary path hash mismatch: %s" % got[:12]
            rows.append(row)
            continue
        snapshot(rel, sha[:12], snapshots)
        doc = yaml.safe_load(open(full))
        row.update(classify_doc(doc, live, variant_registry))
        row["resolved"] = True
        rows.append(row)

    # ---- controls -----------------------------------------------------------
    def mutate_live(fn):
        doc = yaml.safe_load(open(os.path.join(ROOT, "schemas/af_scc_c0_vacuum.yaml")))
        fn(doc)
        return doc

    def set_hf1(text):
        def f(doc):
            doc["regularity"]["must_not_conflate"][0] = text
        return f

    def set_hf2(reason):
        def f(doc):
            doc["implication_ledger"]["forbidden_transfers"][0]["reason"] = reason
        return f

    controls = []

    def ctl(cid, doc, want_hf1, want_hf2):
        got = classify_doc(doc, live, variant_registry)
        controls.append({
            "id": cid,
            "expected": {"hf1": want_hf1, "hf2": want_hf2},
            "observed": {"hf1": got["hf1"]["classification"], "hf2": got["hf2"]["classification"]},
            "pass": got["hf1"]["classification"] == want_hf1 and got["hf2"]["classification"] == want_hf2,
        })

    ctl("K0_live_detects_both_defects", live, "DENIAL", "INVERTED")
    cand = {r["sha256"]: r for r in rows if r["resolved"]}
    if "84b5d3fa29a677ad157b924675bb5a9c08281395920be0221535465a5da44b40" in cand:
        ctl(
            "K1_previous_repair_inverted",
            yaml.safe_load(open(os.path.join(ROOT, cand["84b5d3fa29a677ad157b924675bb5a9c08281395920be0221535465a5da44b40"]["path"]))),
            "INVERTED", "CORRECT",
        )
    ctl(
        "K4_planted_inversion_fires",
        mutate_live(set_hf1(
            "The extension sets are nested E_C2 subset of E_H2loc subset of E_C0, so "
            "H2_loc-inextendibility ENTAILS this class's conclusion."
        )),
        "INVERTED", "INVERTED",
    )
    ctl(
        "K5_planted_correct_direction_passes",
        mutate_live(set_hf1(
            "The extension sets are nested E_C2 subset of E_H2loc subset of E_C0, so "
            "this class's conclusion ENTAILS H2_loc-inextendibility, never the reverse."
        )),
        "CORRECT", "INVERTED",
    )
    ctl(
        "K6_planted_hf2_larger_fires",
        mutate_live(set_hf2("C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker")),
        "DENIAL", "INVERTED",
    )
    ctl(
        "K7_neutral_nesting_is_not_an_assertion",
        mutate_live(set_hf1(
            "H2_loc is a distinct regularity-axis value; the extension sets are nested "
            "E_C2 subset of E_H2loc subset of E_C0, direction recorded in implication_ledger."
        )),
        "NEUTRAL_NESTING", "INVERTED",
    )

    # K8: ground truth follows the file's own ledger, not a hardcoded order.
    def flip_ledger(doc):
        rows_ = doc["implication_ledger"]["one_way_entailments"]
        rows_[0]["from"], rows_[0]["to"] = rows_[0]["to"], rows_[0]["from"]
        rows_[1]["from"], rows_[1]["to"] = rows_[1]["to"], rows_[1]["from"]
        doc["regularity"]["must_not_conflate"][0] = (
            "The extension sets are nested; H2_loc-inextendibility ENTAILS this class's conclusion."
        )
    k8 = classify_doc(mutate_live(flip_ledger), live, variant_registry)
    controls.append({
        "id": "K8_ground_truth_is_read_from_bytes",
        "expected": {"hf1": "CORRECT"},
        "observed": {"hf1": k8["hf1"]["classification"], "ledger_pairs": k8["hf1"]["ledger_pairs"]},
        "pass": k8["hf1"]["classification"] == "CORRECT",
    })

    resolved = [r for r in rows if r["resolved"]]

    # ---- determinism + drift ------------------------------------------------
    det_ok = True
    for r in resolved:
        again = classify_doc(yaml.safe_load(open(os.path.join(ROOT, r["path"]))), live, variant_registry)
        first = {"hf1": r["hf1"], "hf2": r["hf2"], "invariant_diffs": r["invariant_diffs"],
                 "registry_claim": r["registry_claim"], "soft_findings": r["soft_findings"],
                 "semantically_landable": r["semantically_landable"]}
        if json.dumps(again, sort_keys=True) != json.dumps(first, sort_keys=True):
            det_ok = False
    controls.append({
        "id": "K9_determinism_reclassify_all_candidates",
        "expected": {"deterministic": True},
        "observed": {"deterministic": det_ok},
        "pass": det_ok,
    })

    pins_after = {}
    for path in PINS:
        pins_after[path] = sha256_file(os.path.join(ROOT, path))
    pin_drift = sorted(p for p in PINS if pins_before.get(p) != pins_after.get(p))
    landable = sorted(r["sha256"] for r in resolved if r["semantically_landable"])
    inverted = sorted(r["sha256"] for r in resolved if r["hf1"]["classification"] == "INVERTED")
    denial = sorted(r["sha256"] for r in resolved if r["hf1"]["classification"] == "DENIAL")
    neutral = sorted(r["sha256"] for r in resolved if r["hf1"]["classification"] == "NEUTRAL_NESTING")
    correct = sorted(r["sha256"] for r in resolved if r["hf1"]["classification"] == "CORRECT")
    controls_all_pass = all(c["pass"] for c in controls)

    report = {
        "task_id": TASK_ID,
        "actor": ACTOR,
        "class_id": CLASS_ID,
        "node_id": NODE_ID,
        "gate": GATE,
        "started_at": started,
        "finished_at": now_iso(),
        "authority": "worker measurement only; no gate verdict, no node status, no validation_status=passed, no canonical write",
        "question": (
            "Across the declared F2b rev29 repair candidates (worker-070 frame 20687555b7f5), which "
            "HF1/HF2 replacement wordings assert the entailment direction recorded in the same "
            "file's implication_ledger, and which candidates are therefore semantically landable?"
        ),
        "method": (
            "Strict YAML load of each candidate at its declared sha256; the entailment ground truth "
            "is derived from that candidate's own implication_ledger.one_way_entailments rows; the "
            "HF1 slot (regularity.must_not_conflate[0]) is parsed into asserted directed pairs and "
            "checked against that set; the HF2 slot (implication_ledger.forbidden_transfers[0].reason) "
            "size claim is checked against the derived E_C2 subset E_C0 order; frozen invariants are "
            "compared to live bytes. 8 controls incl. a ledger-flip control proving the ground truth "
            "is read from the bytes."
        ),
        "pins_before": pins_before,
        "pins_after": pins_after,
        "pin_drift": pin_drift,
        "snapshots": snapshots,
        "candidates": rows,
        "aggregate": {
            "declared": len(rows),
            "resolved": len(resolved),
            "semantically_landable": landable,
            "hf1_correct_explicit": correct,
            "hf1_neutral_nesting": neutral,
            "hf1_inverted": inverted,
            "hf1_denial": denial,
            "n_landable": len(landable),
            "n_inverted": len(inverted),
            "n_denial": len(denial),
        },
        "controls": controls,
        "controls_all_pass": controls_all_pass,
        "falsifier": (
            "Re-run census_hf1_direction.py at the same pins. Falsified if: any candidate's declared "
            "sha256, HF1/HF2 classification, asserted-pair set or invariant diff differs; if a "
            "candidate asserting H2_loc-inextendibility => own conclusion is classified CORRECT, or "
            "one asserting own conclusion => H2_loc-inextendibility is classified INVERTED, while the "
            "file's own one_way_entailments carries the corresponding row; if a control fails; or if "
            "any pinned byte moves (drift voids the run rather than falsifying it)."
        ),
        "not_claimed": [
            "no gate verdict and no node status",
            "no canonical artifact written or modified",
            "no mathematics claim beyond prose-vs-ledger direction consistency",
            "no adjudication of the sidecar/consistency-evidence binding defects (outside the schema bytes)",
            "no ranking of candidates beyond the semantic landability predicate",
        ],
    }
    out = os.path.join(HERE, "report.json")
    with open(out, "w") as fh:
        json.dump(report, fh, indent=1, sort_keys=True)
        fh.write("\n")

    print("resolved %d/%d candidates" % (len(resolved), len(rows)))
    for r in resolved:
        print("  %s %-46s hf1=%-16s hf2=%-10s landable=%s"
              % (r["sha256"][:12], r["label"][:46], r["hf1"]["classification"], r["hf2"]["classification"], r["semantically_landable"]))
    print("landable :", [s[:12] for s in landable])
    print("inverted :", [s[:12] for s in inverted])
    print("denial   :", [s[:12] for s in denial])
    print("controls :", "ALL PASS" if controls_all_pass else "FAIL")
    print("pin drift:", pin_drift or "none")
    print("report   :", os.path.relpath(out, ROOT), sha256_file(out)[:12])
    return 0 if (controls_all_pass and not pin_drift and len(resolved) == len(rows)) else 3


if __name__ == "__main__":
    sys.exit(main())
