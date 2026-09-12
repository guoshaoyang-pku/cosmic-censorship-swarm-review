#!/usr/bin/env python3
"""W066-F2B-REV29-CONTAINMENT-01 -- independent, order-relative re-base of the F2b
(AF-SCC-C0-VAC-GEN) containment-defect adjudication onto the current FROZEN rev29 pins.

Question measured here (not a mathematics claim): at the live rev13 bytes and the third
FROZEN rev29 write, are the two normative containment defects W066-R12-F2B-H1/H2 still
present, is the 2-edit repair still absent, and are the live bytes the ones FROZEN rev29
actually binds?  Everything runs on the byte copies made by pin.py; any pin move fails
closed.

Run:  python3 rebind.py
Exit: 0 = verdict produced, 2 = pin moved / harness could not run.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))

H1_LIVE = ('- {from: "no proper future C2 extension", to: "this class", reason: '
           '"C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker"}')
H1_FIXED = ('- {from: "no proper future C2 extension", to: "this class", reason: '
            '"C2 is a strictly smaller extension class (E_C2 subset of E_C0), so '
            'C2-inextendibility is strictly weaker"}')
H2_LIVE_FRAG = ("No containment with C2 or C0 is asserted here; the informal phrase "
                "'strictly between' is not used and must not be cited (worker-16 F2b-16-02 accepted).")
H2_FIXED_FRAG = ("The extension sets are nonetheless nested: E_C2 subset of E_{C^1,1} "
                 "subset of E_H2loc subset of E_C0 (see implication_ledger), so "
                 "H2_loc-inextendibility ENTAILS this class's conclusion; the informal "
                 "phrase 'strictly between' is not a class definition and must not be cited "
                 "(worker-16 F2b-16-02 accepted). [R2 major: the earlier 'no containment with "
                 "C2 or C0 is asserted here' was wrong]")

OWN = {"AF-SCC-C0-VAC-GEN": "C0", "AF-SCC-C2-VAC-GEN": "C2", "AF-WCC-VAC-GEN": None}


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_text(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def norm_token(raw: str):
    t = raw.strip().lower().replace("{", "").replace("}", "").replace("^", "")
    t = t.replace("_", "").replace(" ", "").replace("\\", "").replace(",", "")
    if t.endswith("metric"):
        t = t[: -len("metric")]
    if t == "c0":
        return "C0"
    if t.startswith("c2"):
        return "C2"
    if t in ("h2loc", "h2"):
        return "H2LOC"
    if t in ("c11", "c1,1"):
        return "C11"
    return None


def class_token(class_id: str):
    return OWN.get(class_id)


def parse_order(chain_text: str):
    """Reference order taken from the document's own extension_class_containment sentence.
    Returns {token: rank}; rank 0 = largest extension set."""
    head = chain_text.split(";")[0]
    parts = re.split(r"\s+contains\s+", head)
    order = {}
    for i, part in enumerate(parts):
        m = re.search(r"E_?\{?([A-Za-z0-9^_,]+)\}?", part.strip())
        tok = norm_token(m.group(1)) if m else None
        if tok:
            order[tok] = i
    return order


def phrase_token(phr: str):
    m = re.search(r"\bC0\b|\bC2\b|C\^?\{?1,?1\}?|H2_?loc", phr)
    return norm_token(m.group(0)) if m else None


def find_line(text: str, needle: str, start: int = 0):
    pos = text.find(needle, start)
    return text.count("\n", 0, pos) + 1 if pos >= 0 else None


def detect_h1(text: str, own: str, order: dict):
    """A forbidden_transfers reason that asserts a size/containment relation contradicting
    the document's own chain. Order-relative: consistent statements do not fire."""
    findings = []
    doc = yaml.safe_load(text)
    ft = ((doc.get("implication_ledger") or {}).get("forbidden_transfers")) or []
    for i, e in enumerate(ft):
        reason = str(e.get("reason", ""))
        to_tok = own if str(e.get("to", "")).strip() == "this class" else phrase_token(str(e.get("to", "")))
        from_tok = phrase_token(str(e.get("from", "")))
        if not from_tok or not to_tok or from_tok not in order or to_tok not in order:
            continue
        stated, violation = None, False
        m = re.search(r"strictly\s+(larger|smaller)\s+extension\s+class", reason)
        if m:
            stated = m.group(0)
            if m.group(1) == "larger":       # claims E_from superset E_to
                violation = order[from_tok] > order[to_tok]
            else:                             # claims E_from subset E_to
                violation = order[from_tok] < order[to_tok]
        m2 = re.search(r"\(E_?\{?([A-Za-z0-9^_,]+)\}?\s+subset of\s+E_?\{?([A-Za-z0-9^_,]+)\}?\)", reason)
        if m2:
            a, b = norm_token(m2.group(1)), norm_token(m2.group(2))
            stated = m2.group(0)
            if a in order and b in order and order[a] <= order[b]:
                violation = True
        if violation:
            findings.append({
                "kind": "size_premise_inverted",
                "clause": f"implication_ledger.forbidden_transfers[{i}].reason",
                "line": find_line(text, reason[:60]),
                "from_token": from_tok, "to_token": to_tok,
                "stated": stated,
                "derived_order": "E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2",
                "derived": f"E_{from_tok} is the "
                           + ("SMALLER" if order[from_tok] > order[to_tok] else "LARGER")
                           + f" extension set than E_{to_tok}",
            })
    return findings


def detect_h2(text: str, own: str, watch=("C0", "C2", "C11", "H2LOC")):
    """A live (non-bracketed, non-withdrawn) must_not_conflate clause that denies containment
    while the same document asserts it."""
    findings = []
    doc = yaml.safe_load(text)
    mnc = ((doc.get("regularity") or {}).get("must_not_conflate")) or []
    for i, s in enumerate(mnc):
        s = str(s)
        stripped = re.sub(r"\[[^\]]*\]", "", s)  # bracketed corrections are withdrawn, not live
        for m in re.finditer(r"No\s+containment\s+with\s+(.{0,80}?)\s+is\s+asserted", stripped, re.I):
            named = [t for t in (norm_token(x) for x in re.findall(r"C0|C2|C\^?\{?1,?1\}?|H2_?loc", m.group(1), re.I)) if t]
            if own in named or any(t in watch for t in named):
                findings.append({
                    "kind": "false_containment_denial",
                    "clause": f"regularity.must_not_conflate[{i}]",
                    "line": find_line(text, m.group(0)[:40]),
                    "sentence": m.group(0),
                    "named_tokens": named,
                    "live": True,
                })
    return findings


def findings(text: str, class_id: str):
    own = class_token(class_id)
    order = parse_order(str((yaml.safe_load(text).get("implication_ledger") or {}).get("extension_class_containment", "")))
    f = detect_h1(text, own, order) + detect_h2(text, own)
    return sorted(f, key=lambda x: x["kind"]), order


def kinds(fs):
    return sorted({f["kind"] for f in fs})


def leaf_paths(obj, prefix=""):
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(leaf_paths(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(leaf_paths(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = obj
    return out


def main() -> int:
    pins_doc = json.loads((OUT / "evidence" / "pins.json").read_text())
    if not pins_doc.get("all_match"):
        print("PIN FAILURE at entry", json.dumps(pins_doc.get("failures")))
        return 2
    pins = pins_doc["pins"]
    P = OUT / "pinned"
    text = {
        "c0": (P / "c0_canonical__af_scc_c0_vacuum.yaml").read_text(),
        "c0_mirror": (P / "c0_mirror__af_scc_c0_vacuum.yaml").read_text(),
        "c0_rev12": (P / "c0_rev12_archive__c0_live__af_scc_c0_vacuum.yaml").read_text(),
        "c2": (P / "c2_canonical__af_scc_c2_vacuum.yaml").read_text(),
        "f1": (P / "f1_canonical__af_wcc_vacuum.yaml").read_text(),
        "candidate": (P / "candidate_98f9ec83__af_scc_c0_vacuum.yaml").read_text(),
    }
    frozen = json.loads((P / "frozen_manifest__FROZEN.json").read_text())

    checks = []

    def check(cid, desc, expected, observed, ok=None):
        ok = (expected == observed) if ok is None else ok
        checks.append({"check": cid, "description": desc, "expected": expected,
                       "observed": observed, "pass": bool(ok)})
        return bool(ok)

    # C1 target = live rev13, mirror identical, both detectors reproduce H1+H2
    live_fs, live_order = findings(text["c0"], "AF-SCC-C0-VAC-GEN")
    check("C1-mirror-identity", "canonical and mirror C0 bytes are identical",
          True, sha256_text(text["c0"]) == sha256_text(text["c0_mirror"]))
    check("C2-defect-persistence", "live rev13 C0 still yields exactly H1+H2",
          ["false_containment_denial", "size_premise_inverted"], kinds(live_fs))

    # C3 both defect clauses are byte-identical to superseded rev12 (carried over, not new)
    carried = {f["kind"]: (H2_LIVE_FRAG in text["c0_rev12"]) if f["kind"] == "false_containment_denial"
               else (H1_LIVE in text["c0_rev12"]) for f in live_fs}
    check("C3-carried-over", "both defect clauses are byte-identical at rev12 55d0a1ea",
          {"false_containment_denial": True, "size_premise_inverted": True}, carried)

    # C4 repair still absent at live bytes
    check("C4-repair-absent", "neither repair sentence is present in live bytes",
          {"h1_fixed": False, "h2_fixed": False},
          {"h1_fixed": H1_FIXED in text["c0"],
           "h2_fixed": "ENTAILS this class's conclusion" in text["c0"]})

    # C5 rebased candidate: apply the two reference edits to the LIVE rev13 bytes
    rebased = text["c0"].replace(H1_LIVE, H1_FIXED).replace(H2_LIVE_FRAG, H2_FIXED_FRAG)
    rebased_fs, _ = findings(rebased, "AF-SCC-C0-VAC-GEN")
    check("C5-rebased-candidate-clean", "live+2 edits yields a rebased candidate with zero findings",
          [], kinds(rebased_fs))
    check("C6-reference-candidate-clean", "worker-008 candidate 98f9ec83 yields zero findings",
          [], kinds(findings(text["candidate"], "AF-SCC-C0-VAC-GEN")[0]))

    # C7 repair commutes with the rev13 evidence-binding delta: structural diff live->rev12
    # must equal the diff between the rebased candidate and 98f9ec83.
    d_live = leaf_paths(yaml.safe_load(text["c0"]))
    d_rev12 = leaf_paths(yaml.safe_load(text["c0_rev12"]))
    d_reb = leaf_paths(yaml.safe_load(rebased))
    d_cand = leaf_paths(yaml.safe_load(text["candidate"]))
    changed_live = sorted({k for k in set(d_live) | set(d_rev12) if d_live.get(k) != d_rev12.get(k)})
    changed_cand = sorted({k for k in set(d_reb) | set(d_cand) if d_reb.get(k) != d_cand.get(k)})
    check("C7-delta-commutes", "rev12->rev13 changed leaf paths equal rebased-candidate -> 98f9ec83 paths",
          changed_live, changed_cand)
    check("C8-delta-outside-repair", "no rev13 delta path lies in the two repair subtrees",
          [], [p for p in changed_live if p.startswith("implication_ledger") or p.startswith("regularity.must_not_conflate")])

    # C9 siblings carry neither defect kind at their current pins
    c2_fs, _ = findings(text["c2"], "AF-SCC-C2-VAC-GEN")
    f1_fs, _ = findings(text["f1"], "AF-WCC-VAC-GEN")
    check("C9-sibling-c2-clean", "C2 e9a27996 yields neither defect kind", [], kinds(c2_fs))
    check("C10-sibling-f1-clean", "F1 d9cebb94 yields neither defect kind", [], kinds(f1_fs))

    # C11 freeze binding: FROZEN rev29 declares exactly the live class-schema hashes
    declared = frozen.get("files", {})
    measured_hashes = {
        "schemas/af_scc_c0_vacuum.yaml": sha256_file(ROOT / "schemas/af_scc_c0_vacuum.yaml"),
        "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml": sha256_file(ROOT / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"),
        "schemas/af_scc_c2_vacuum.yaml": sha256_file(ROOT / "schemas/af_scc_c2_vacuum.yaml"),
        "schemas/af_wcc_vacuum.yaml": sha256_file(ROOT / "schemas/af_wcc_vacuum.yaml"),
    }
    binding = {}
    for path, h in measured_hashes.items():
        declared_h = (declared.get(path) or {}).get("sha256")
        binding[path] = {"declared": declared_h, "measured": h, "match": declared_h == h}
    check("C11-freeze-binding", "FROZEN rev29 declares the live canonical+mirror class-schema hashes",
          True, all(v["match"] for v in binding.values()))
    check("C12-frozen-rev", "FROZEN revision and frozen_at are the third rev29 write",
          {"revision": 29, "frozen_at": "2026-09-12T00:57:26+08:00"},
          {"revision": frozen.get("revision"), "frozen_at": frozen.get("frozen_at")})

    # C13 F0 + consistency-evidence chain resolves
    f0_live = sha256_file(ROOT / "research_map/formulation_taxonomy.yaml")
    cons_live = sha256_file(ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json")
    c0_doc = yaml.safe_load(text["c0"])["f0_binding"]
    check("C13-f0-chain", "declared F0 hash and consistency evidence both resolve live",
          True, f0_live == c0_doc["declared_f0_sha256"] and cons_live == c0_doc["consistency_evidence_sha256"])

    # controls -- pre-registered before running
    chain_line = str(yaml.safe_load(text["c0"])["implication_ledger"]["extension_class_containment"])
    reversed_text = text["c0"].replace(chain_line, "E_C2 contains E_{C^1,1} contains E_H2loc contains E_C0")
    m8_text = text["c0"].replace(H2_LIVE_FRAG, "")
    controls_spec = [
        ("M1-pristine-live", "live rev13 -> exactly H1+H2", ["false_containment_denial", "size_premise_inverted"], kinds(live_fs)),
        ("M2-reference-candidate", "98f9ec83 -> no findings", [], kinds(findings(text["candidate"], "AF-SCC-C0-VAC-GEN")[0])),
        ("M3-h1-reverted-only", "candidate with H1 edit reverted -> H1 only", ["size_premise_inverted"],
         kinds(findings(text["candidate"].replace(H1_FIXED, H1_LIVE), "AF-SCC-C0-VAC-GEN")[0])),
        ("M4-h2-reverted-only", "candidate with H2 edit reverted -> H2 only", ["false_containment_denial"],
         kinds(findings(text["candidate"].replace(H2_FIXED_FRAG, H2_LIVE_FRAG), "AF-SCC-C0-VAC-GEN")[0])),
        ("M5-bare-denial", "candidate with a bare live denial -> H2", ["false_containment_denial"],
         kinds(findings(text["candidate"].replace(H2_FIXED_FRAG, "No containment with C2 is asserted here."), "AF-SCC-C0-VAC-GEN")[0])),
        ("M6-withdrawn-denial", "candidate with the denial inside a bracketed correction -> no H2", [],
         kinds(findings(text["candidate"].replace(H2_FIXED_FRAG, "[R2 major: the earlier 'no containment with C2 or C0 is asserted here' was wrong]"), "AF-SCC-C0-VAC-GEN")[0])),
        ("M7-reversed-chain", "reversed chain + live reason is order-consistent -> no H1", ["false_containment_denial"],
         kinds(findings(reversed_text, "AF-SCC-C0-VAC-GEN")[0])),
        ("M8-denial-removed", "live with the denial sentence removed -> H1 only", ["size_premise_inverted"],
         kinds(findings(m8_text, "AF-SCC-C0-VAC-GEN")[0])),
    ]
    controls = [{"control": c, "description": d, "expected": e, "observed": o, "matched": e == o}
                for c, d, e, o in controls_spec]

    # exit re-measure: pins must not have moved while the verdict was computed
    moved = []
    for key, rec in pins.items():
        if sha256_file(ROOT / rec["path"]) != rec["expected_sha256"]:
            moved.append(key)
    if moved:
        print("PIN MOVED during run:", moved)
        return 2

    defects = [{"finding": f.get("clause"), "kind": f["kind"], "line": f["line"],
                "detail": f.get("stated") or f.get("sentence")} for f in live_fs]
    report = {
        "task_id": "W066-F2B-REV29-CONTAINMENT-01",
        "actor": "worker-066",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
        "gate": "G-FORM",
        "generated_at": now(),
        "verdict": "revise",
        "score": 2.5,
        "target": {
            "path": "schemas/af_scc_c0_vacuum.yaml",
            "sha256": pins["c0_canonical"]["measured_sha256"],
            "revision": yaml.safe_load(text["c0"]).get("revision"),
            "frozen_revision": frozen.get("revision"),
            "frozen_manifest_sha256": pins["frozen_manifest"]["measured_sha256"],
            "frozen_at": frozen.get("frozen_at"),
        },
        "defects_live": defects,
        "hard_failures": ["W066-R13-F2B-H1", "W066-R13-F2B-H2"],
        "repair_status": "absent; rebased candidate sha256 "
                         + sha256_text(rebased) + " clears both defects",
        "freeze_binding": binding,
        "checks_passed": sum(1 for c in checks if c["pass"]),
        "checks_total": len(checks),
        "controls_matched": sum(1 for c in controls if c["matched"]),
        "controls_total": len(controls),
        "pins_stable_entry_exit": True,
        "falsifier": ("Re-run rebind.py on the same pins. This re-base is falsified if: the live C0 hash is not "
                      "b2ab6acb2bbe; the live rev13 file no longer contains the inverted size premise at "
                      "implication_ledger.forbidden_transfers[0].reason and the live containment denial at "
                      "regularity.must_not_conflate[0]; FROZEN rev29 (815e0807) does not declare the measured "
                      "canonical/mirror hashes; the rebased live+2-edit text is not finding-free; a sibling C2/F1 "
                      "is shown to carry either defect kind at its pin; any pre-registered control departs from its "
                      "expectation; or the two clauses are shown non-normative at the bound hash (rule_spec R06/R16 "
                      "is the standing counter-evidence)."),
        "scope": ("Machine-checker and text-consistency result at pinned bytes only; not a claim about the "
                  "mathematics of C0/C2 inextendibility, not a gate verdict, not a node status."),
    }
    (OUT / "evidence" / "checks.json").write_text(json.dumps(
        {"task_id": report["task_id"], "target_sha256": report["target"]["sha256"],
         "checks": checks, "defects": defects}, indent=1) + "\n")
    (OUT / "evidence" / "controls.json").write_text(json.dumps(
        {"task_id": report["task_id"], "pre_registered": True, "controls": controls}, indent=1) + "\n")
    (OUT / "evidence" / "freeze_binding.json").write_text(json.dumps(
        {"task_id": report["task_id"], "frozen_revision": frozen.get("revision"),
         "frozen_at": frozen.get("frozen_at"), "binding": binding,
         "changed_leaf_paths_rev12_to_rev13": changed_live}, indent=1) + "\n")
    (OUT / "report.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({"verdict": report["verdict"], "defect_kinds": kinds(live_fs),
                      "checks": f'{report["checks_passed"]}/{report["checks_total"]}',
                      "controls": f'{report["controls_matched"]}/{report["controls_total"]}',
                      "rebased_candidate": sha256_text(rebased)[:12]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
