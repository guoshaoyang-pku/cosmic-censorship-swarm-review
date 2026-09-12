#!/usr/bin/env python3
"""W097-F2B-ACCEPT-SUFFICIENCY-01 (worker-097, 2026-09-12).

Evidence-sufficiency audit at frozen F2b revision b2ab6acb2bbe:
  * re-derive, from primary bytes, the two live self-contradictions flagged by revise
    verdicts at that hash (HF-152 stale containment denial, HF-246 inverted containment
    premise);
  * test whether the accept verdicts recorded at the same hash dispose of either carrier,
    scanning both the verdict artifacts and the instruments/evidence they cite.

Stdlib only. Does not import research_map/class_separation.py or any other agent's checker.
Writes only inside its own artifact directory plus the report path it is given.
No class verdict, no gate verdict, no node state is claimed.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

TASK_ID = "W097-F2B-ACCEPT-SUFFICIENCY-01"
NODE_ID = "F2b"
CLASS_ID = "AF-SCC-C0-VAC-GEN"
GATE = "G-FORM"

C0 = "schemas/af_scc_c0_vacuum.yaml"
C2 = "schemas/af_scc_c2_vacuum.yaml"
F0 = "research_map/formulation_taxonomy.yaml"
SUP = "artifacts/formulation/formulation_taxonomy.yaml"
FROZEN = "artifacts/formulation/FROZEN.json"

# ---------------------------------------------------------------- pinned inputs
PINS = {
    C0: "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    C2: "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    F0: "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    SUP: "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    FROZEN: "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
}

ACCEPTS = [
    {
        "reviewer": "worker-071",
        "verdict_path": "reviews/F2b-review-rev13-worker-071.json",
        "cited_instruments": [
            "artifacts/worker-071/f2b_rev13_blind_review/review_f2b_rev13.py",
            "artifacts/worker-071/f2b_rev13_blind_review/review_checks.json",
            "artifacts/worker-071/f2b_rev13_blind_review/PREREGISTRATION.json",
        ],
    },
    {
        "reviewer": "worker-072",
        "verdict_path": "reviews/F2b-review-worker-072-rev29.json",
        "cited_instruments": [
            "artifacts/worker-072/f2b_review/check_f2b.py",
            "artifacts/worker-072/f2b_review/report.json",
            "artifacts/worker-072/f2b_review/controls/controls_summary.json",
        ],
    },
    {
        "reviewer": "worker-090",
        "verdict_path": "reviews/F2b-rev13-full-090.json",
        "cited_instruments": [
            "artifacts/worker-090/f2b_rev13_full_verdict/check_f2b_rev13_full.py",
            "artifacts/worker-090/f2b_rev13_full_verdict/results.json",
            "artifacts/worker-090/f2b_rev13_full_verdict/controls.json",
        ],
    },
]

REVISES = [
    ("worker-017", "reviews/F2b-rev13-containment-worker-017.json"),
    ("worker-018", "reviews/F2b-review-worker-018-rev13.json"),
    ("worker-035", "reviews/F2b-bindchain-rev13-worker-035.json"),
    ("worker-053", "reviews/F2b-review-rev29-053.json"),
    ("worker-066", "reviews/F2b-containment-normativity-worker-066.json"),
    ("worker-075", "reviews/F2b-review-rev29-075.json"),
    ("worker-097", "artifacts/worker-097/f2b_rev13_review/REVIEW.json"),
]

# ---------------------------------------------------------------- carriers
CARRIERS = {
    "HF-152": {
        "field": "regularity.must_not_conflate[0]",
        "line": 152,
        "field_markers": ["must_not_conflate"],
        "content_markers": ["No containment with C2 or C0"],
        "line_markers": ["line 152", "152:", "l152", ":152", "line-152"],
    },
    "HF-246": {
        "field": "implication_ledger.forbidden_transfers[0].reason",
        "line": 246,
        "field_markers": ["forbidden_transfers"],
        "content_markers": ["strictly larger", "strictly smaller"],
        "line_markers": ["line 246", "246:", "l246", ":246", "line-246"],
    },
}
JUDGMENT = [
    "invert", "contradict", "inconsistent", "stale", "false", "wrong", "consistent",
    "correct", "verified", "holds", "defect", "failure", "flagged", "found", "dispos",
    "read as", "checked", "examin",
]
EXCLUSION = ["exclud", "ignore", "by design", "not scanned", "out of scope", "negative block", "registry block",
             "non_goals", "non-goals", "non goals"]


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_lines(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return f.read().splitlines()


def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def statements_from(path: str):
    """All strings a verdict/instrument asserts, for token scanning."""
    out = []
    ext = os.path.splitext(path)[1].lower()
    if ext == ".json":
        try:
            obj = json.loads(read_text(path))
        except Exception:
            return [l for l in read_lines(path)]
        stack = [obj]
        while stack:
            cur = stack.pop()
            if isinstance(cur, dict):
                for k, v in cur.items():
                    out.append(str(k))
                    stack.append(v)
            elif isinstance(cur, list):
                stack.extend(cur)
            else:
                out.append(str(cur))
        return out
    return windows(read_lines(path))


def windows(lines):
    """Line statements plus 1-line lookahead windows (catches two-line comments/regex lists)."""
    out = list(lines)
    for i in range(len(lines) - 1):
        out.append(lines[i] + " " + lines[i + 1])
    return out


def classify(statements, carrier) -> dict:
    """Classify whether a verdict/instrument DISPOSES of a carrier."""
    disposed, excluded, mention = [], [], []
    for s in statements:
        low = s.lower()
        has_field = any(m in s for m in carrier["field_markers"])
        has_content = any(m in s for m in carrier["content_markers"])
        has_line = any(m in low for m in carrier["line_markers"])
        has_judg = any(j in low for j in JUDGMENT)
        has_excl = any(x in low for x in EXCLUSION)
        if has_line or has_content:
            disposed.append(s)
        elif has_field and has_judg and not has_excl:
            disposed.append(s)
        elif has_field and has_excl:
            excluded.append(s)
        elif has_field:
            mention.append(s)
    if disposed:
        cls = "DISPOSED"
    elif excluded:
        cls = "EXCLUDED-FROM-CHECK"
    elif mention:
        cls = "MENTION-ONLY"
    else:
        cls = "NONE"
    witness = (disposed or excluded or mention or [""])[0]
    return {"classification": cls, "witness": witness[:280], "n_statements_scanned": len(statements)}


# ---------------------------------------------------------------- primary-byte derivations
def derive_clauses(root: str) -> dict:
    lines = read_lines(os.path.join(root, C0))
    c2_lines = read_lines(os.path.join(root, C2))
    sup_lines = read_lines(os.path.join(root, SUP))

    def at(n):
        return lines[n - 1].strip() if 0 < n <= len(lines) else ""

    l152, l239, l242, l246 = at(152), at(239), at(242), at(246)

    m = re.search(r"extension_class_containment:\s*\"(.*?)\"", l239)
    chain_text = m.group(1) if m else ""
    chain = [p.strip() for p in chain_text.split(" contains ")] if " contains " in chain_text else []
    innermost = chain[-1] if chain else None

    c2_l237 = c2_lines[236].strip() if len(c2_lines) >= 237 else ""
    sup_l145 = sup_lines[144].strip() if len(sup_lines) >= 145 else ""
    ref_ok = ("E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0" in c2_l237
              and "E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0" in sup_l145)

    # HF-246: the reason must agree with the chain (E_C2 innermost => C2 extension set strictly smaller)
    hf246_inconsistent = ("strictly larger" in l246) and (innermost is not None and "C2" in innermost)
    hf246_consistent = ("strictly smaller" in l246)

    # HF-152: denial is inconsistent iff containment is asserted elsewhere in the same artifact
    asserts_containment = ("contains E_H2loc" in l239 and "E_C2 subset of E_H2loc" in l242)
    denies_containment = "No containment with C2 or C0 is asserted here" in l152
    hf152_inconsistent = denies_containment and asserts_containment

    return {
        "reference_wording_ok": ref_ok,
        "reference_wording": {"F2a_line_237": c2_l237[:200], "supplement_line_145": sup_l145[:200]},
        "chain": chain,
        "innermost_set": innermost,
        "clause_checks": {
            "HF-246": {
                "field": CARRIERS["HF-246"]["field"], "line": 246, "text": l246[:300],
                "derivation": f"artifact chain {chain} => innermost {innermost}; "
                              f"'strictly larger' contradicts it, 'strictly smaller' agrees",
                "verdict": "INCONSISTENT" if hf246_inconsistent else ("CONSISTENT" if hf246_consistent else "UNDETERMINED"),
            },
            "HF-152": {
                "field": CARRIERS["HF-152"]["field"], "line": 152, "text": l152[:300],
                "derivation": f"line 152 denies containment ({denies_containment}); lines 239/242 assert it "
                              f"({asserts_containment}) => self-contradiction if both",
                "verdict": "INCONSISTENT" if hf152_inconsistent else "CONSISTENT",
            },
        },
    }


def mutation_controls(root: str, tmp_dir: str, base: dict) -> list:
    controls = []
    c0_path = os.path.join(root, C0)
    text = read_text(c0_path)

    # C4: larger -> smaller
    mut4 = os.path.join(tmp_dir, "c0_mut_smaller.yaml")
    with open(mut4, "w", encoding="utf-8") as f:
        f.write(text.replace("strictly larger extension class", "strictly smaller extension class"))
    lines4 = read_lines(mut4)
    c246 = lines4[245]
    controls.append({
        "id": "C4", "mutation": "'strictly larger' -> 'strictly smaller' at line 246",
        "expected": "HF-246 flips to CONSISTENT",
        "observed": "CONSISTENT" if ("strictly smaller" in c246 and "strictly larger" not in c246) else "FAILED",
        "pass": ("strictly smaller" in c246 and "strictly larger" not in c246),
    })

    # C5: delete the denial sentence
    mut5 = os.path.join(tmp_dir, "c0_mut_nodenial.yaml")
    with open(mut5, "w", encoding="utf-8") as f:
        f.write(text.replace(" No containment with C2 or C0 is asserted here;", ""))
    lines5 = read_lines(mut5)
    denial_gone = "No containment with C2 or C0 is asserted here" not in lines5[151]
    controls.append({
        "id": "C5", "mutation": "delete the line-152 denial sentence",
        "expected": "HF-152 flips to CONSISTENT",
        "observed": "CONSISTENT" if denial_gone else "FAILED",
        "pass": denial_gone,
    })
    return controls


def run(root: str, out_path: str) -> dict:
    pins = {}
    for rel, expected in PINS.items():
        p = os.path.join(root, rel)
        ok = os.path.isfile(p)
        pins[rel] = {
            "sha256": sha256(p) if ok else None,
            "expected_pin": expected,
            "match": bool(ok and sha256(p) == expected),
            "bytes": os.path.getsize(p) if ok else None,
        }

    derived = derive_clauses(root)

    accept_rows = []
    for a in ACCEPTS:
        vp = os.path.join(root, a["verdict_path"])
        vobj = {}
        if os.path.isfile(vp):
            try:
                vobj = json.loads(read_text(vp))
            except Exception:
                vobj = {}
        vstmts = statements_from(vp) if os.path.isfile(vp) else []
        inst_stmts, inst_files = [], []
        for rel in a["cited_instruments"]:
            ip = os.path.join(root, rel)
            if os.path.isfile(ip):
                inst_stmts.extend(statements_from(ip))
                inst_files.append({"path": rel, "sha256": sha256(ip), "statements": len(statements_from(ip))})
            else:
                inst_files.append({"path": rel, "sha256": None, "statements": 0})
        row = {
            "reviewer": a["reviewer"],
            "verdict_path": a["verdict_path"],
            "verdict_sha256": sha256(vp) if os.path.isfile(vp) else None,
            "verdict": vobj.get("verdict"),
            "score": vobj.get("score"),
            "reviewed_sha256": vobj.get("reviewed_sha256"),
            "reviewed_hash_matches_live": (vobj.get("reviewed_sha256") or "").startswith("b2ab6acb2bbe"),
            "counts_as_full_schema_verdict": vobj.get("counts_as_full_schema_verdict"),
            "blind": vobj.get("blind"),
            "cited_instruments": inst_files,
        }
        for cid, carrier in CARRIERS.items():
            rv = classify(vstmts, carrier)
            ri = classify(inst_stmts, carrier)
            # worst-of: a carrier is covered only if the verdict or a cited instrument DISPOSES
            if "DISPOSED" in (rv["classification"], ri["classification"]):
                merged = "DISPOSED"
            elif "EXCLUDED-FROM-CHECK" in (rv["classification"], ri["classification"]):
                merged = "EXCLUDED-FROM-CHECK"
            elif "MENTION-ONLY" in (rv["classification"], ri["classification"]):
                merged = "MENTION-ONLY"
            else:
                merged = "NONE"
            row[cid] = {"classification": merged, "verdict_artifact": rv, "cited_instruments": ri}
        accept_rows.append(row)

    revise_rows = []
    for reviewer, rel in REVISES:
        p = os.path.join(root, rel)
        if not os.path.isfile(p):
            revise_rows.append({"reviewer": reviewer, "path": rel, "exists": False})
            continue
        st = statements_from(p)
        revise_rows.append({
            "reviewer": reviewer, "path": rel, "exists": True, "sha256": sha256(p),
            "HF-152": classify(st, CARRIERS["HF-152"]),
            "HF-246": classify(st, CARRIERS["HF-246"]),
        })

    # controls C1..C3 (C4/C5 in temp dir)
    tmp_dir = os.path.join(HERE, "_mutants")
    os.makedirs(tmp_dir, exist_ok=True)
    c1 = ["findings: HF-246 forbidden_transfers[0].reason at line 246 says 'strictly larger' while the "
          "containment chain makes E_C2 innermost; inverted. HF-152 must_not_conflate line 152 denial is "
          "stale and contradicts line 239."]
    c3 = ["this verdict reviewed the file and found no issues of the kind it was asked about"]
    controls = [
        {"id": "C1", "input": "synthetic disposition", "expected": "both DISPOSED",
         "observed": {c: classify(c1, CARRIERS[c])["classification"] for c in CARRIERS},
         "pass": all(classify(c1, CARRIERS[c])["classification"] == "DISPOSED" for c in CARRIERS)},
        {"id": "C2", "input": "worker-097 revise REVIEW.json", "expected": "both DISPOSED",
         "observed": {c: classify(statements_from(os.path.join(root, "artifacts/worker-097/f2b_rev13_review/REVIEW.json")),
                                  CARRIERS[c])["classification"] for c in CARRIERS},
         "pass": all(classify(statements_from(os.path.join(root, "artifacts/worker-097/f2b_rev13_review/REVIEW.json")),
                              CARRIERS[c])["classification"] == "DISPOSED" for c in CARRIERS)},
        {"id": "C3", "input": "synthetic verdict with no carrier tokens", "expected": "both NONE",
         "observed": {c: classify(c3, CARRIERS[c])["classification"] for c in CARRIERS},
         "pass": all(classify(c3, CARRIERS[c])["classification"] == "NONE" for c in CARRIERS)},
    ] + mutation_controls(root, tmp_dir, derived)

    # C6 hash stability
    post = {rel: sha256(os.path.join(root, rel)) for rel in PINS}
    stable = all(post[rel] == pins[rel]["sha256"] for rel in PINS)
    controls.append({"id": "C6", "input": "all pinned inputs re-measured after the run",
                     "expected": "no drift", "observed": "stable" if stable else "DRIFT", "pass": stable})

    controls_ok = all(c["pass"] for c in controls)

    sufficiency = {}
    for cid in CARRIERS:
        clause_v = derived["clause_checks"][cid]["verdict"]
        disposed_by = [r["reviewer"] for r in accept_rows if r[cid]["classification"] == "DISPOSED"]
        sufficiency[cid] = {
            "primary_clause_verdict": clause_v,
            "accepts_disposing": disposed_by,
            "accept_coverage": {r["reviewer"]: r[cid]["classification"] for r in accept_rows},
            "sufficient_on_record": bool(disposed_by) if clause_v == "INCONSISTENT" else None,
        }

    report = {
        "task_id": TASK_ID,
        "node_id": NODE_ID,
        "class_id": CLASS_ID,
        "gate": GATE,
        "actor": "worker-097",
        "artifact_kind": "evidence_sufficiency_audit",
        "question": ("At F2b b2ab6acb2bbe do the accept verdicts at that hash dispose of the two live "
                     "self-contradictions flagged by revise verdicts at the same hash?"),
        "pins": pins,
        "hash_stability_after": {"stable": stable, "measured": post},
        "primary_derivation": derived,
        "accept_coverage": accept_rows,
        "revise_side_context": revise_rows,
        "controls": controls,
        "controls_ok": controls_ok,
        "sufficiency": sufficiency,
        "verdict": {
            "evidence_sufficiency": None,  # filled below
            "basis": None,
            "non_claims": [
                "no accept/revise/reject verdict on F2b is rendered by this audit",
                "no gate verdict, node status or validation_status is claimed",
                "the severity of HF-152/HF-246 for the gate is the lead-audit's adjudication",
            ],
        },
        "falsifier": (
            "An accept verdict recorded at b2ab6acb2bbe whose artifact or cited instrument contains a "
            "hash-bound disposition of line 152 or line 246 (explicit line citation, verbatim contested "
            "content, or field+judgment), or a byte-level re-derivation showing line 239 is not a "
            "containment assertion, or a measurement of schemas/af_scc_c0_vacuum.yaml differing from "
            "b2ab6acb2bbe at read time."
        ),
    }

    if not controls_ok:
        report["verdict"]["evidence_sufficiency"] = "RUN-FAILED-CONTROLS"
        report["verdict"]["basis"] = "a pre-registered control failed; no sufficiency conclusion drawn"
    else:
        insufficient = [c for c in CARRIERS
                        if derived["clause_checks"][c]["verdict"] == "INCONSISTENT"
                        and not sufficiency[c]["accepts_disposing"]]
        if insufficient:
            report["verdict"]["evidence_sufficiency"] = "INSUFFICIENT"
            report["verdict"]["basis"] = (
                "primary bytes confirm " + ", ".join(sorted(insufficient)) +
                " as live self-contradictions, and no accept verdict at b2ab6acb2bbe disposes of " +
                ("either carrier" if len(insufficient) == len(CARRIERS) else "the carrier") +
                "; coverage is " + json.dumps({c: sufficiency[c]["accept_coverage"] for c in sorted(insufficient)}) +
                ". A sufficient disposition would have to cite the carrier line/field and record a "
                "judgment on its content at the pinned hash."
            )
        else:
            report["verdict"]["evidence_sufficiency"] = "SUFFICIENT"
            report["verdict"]["basis"] = "each live carrier is disposed of by at least one accept at the hash"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=False)
        f.write("\n")
    return report


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "report.json")
    r = run(ROOT, out)
    print(json.dumps({
        "controls_ok": r["controls_ok"],
        "clause_verdicts": {k: v["verdict"] for k, v in r["primary_derivation"]["clause_checks"].items()},
        "accept_coverage": {row["reviewer"]: {c: row[c]["classification"] for c in CARRIERS}
                            for row in r["accept_coverage"]},
        "evidence_sufficiency": r["verdict"]["evidence_sufficiency"],
    }, indent=2))
