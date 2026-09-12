#!/usr/bin/env python3
"""W053-F2B-REV30-H2-DIRECTION-01 -- independent, hash-pinned direction audit of the
F2b `regularity.must_not_conflate[0]` replacement across every staged rev30 carrier.

Class: AF-SCC-C0-VAC-GEN (F2b; sibling control AF-SCC-C2-VAC-GEN).  Gate context: G-FORM.
Authority: worker measurement only.  No canonical path is written; no gate verdict, no node
status, no validation_status.  The script reads carriers, snapshots their exact bytes into
this directory, classifies one sentence per carrier, and re-runs the two acceptance tools
that the rev30 rehearsal used (worker08 battery, worker-008 dual) to measure whether they
are blind to an inverted H2 entailment direction.

Why this exists (measured, not assumed):
  * worker-058 rehearsed carrier 84b5d3fa as REV30_FREEZE_REHEARSAL_READY and its owner
    runbook says to copy that file to the canonical path.
  * worker-088's guard classifies 84b5d3fa as H2_INVERTED_ENTAILMENT_DIRECTION and blocks
    it; its own REPORT.md table also prints H2_DENIAL_NO_CONTAINMENT, so the block is
    internally inconsistent and needs a third, from-scratch measurement.
  * worker-076 staged a different composite carrier hours later and passed it through a
    10-check audit; worker-088 never saw it, and worker-075's reconciliation explicitly
    declines to judge other workers' candidates.
  * worker-075's reconciliation proves the trap independently: copying the repaired C2
    sibling sentence verbatim into C0 inverts the entailment (C0 => H2loc => C2).

Ground truth used by the classifier, derived from each document's own
implication_ledger.extension_class_containment chain (not from any prior review):
set order largest -> smallest: E_C0, E_H2loc, E_{C^1,1}, E_C2.  A smaller extension set
means a STRONGER "no extension" statement, so the entailment order is the reverse:
C0-inextendibility => H2_loc-inextendibility => C2-inextendibility.
For class X the correct closing clause asserts "X-inextendibility ENTAILS <next weaker>";
the inverted clause asserts the next weaker class entails X.

Usage: python3 audit_h2_direction_053.py [--generated-at ISO8601] [--emit] [--skip-tools]
Exit: 0 report written; 2 fail-closed (pin/carrier drift or a control not met).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SNAP = HERE / "snapshot"
SCRATCH = HERE / "scratch"

CLASS_OF_FILE = {
    "AF-SCC-C0-VAC-GEN": "C0",
    "AF-SCC-C2-VAC-GEN": "C2",
}
# canonical chain: largest extension set first.  A larger extension set means a WEAKER
# "no extension" statement, so the entailment order (strongest -> weakest) runs in the
# same sequence: C0 => H2LOC => C11 => C2.
SET_ORDER = ["C0", "H2LOC", "C11", "C2"]
ENTAIL_ORDER = ["C0", "H2LOC", "C11", "C2"]

PINS = {
    "schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe",
    "schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd3",
    "artifacts/formulation/FROZEN.json": "815e08079aef",
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a961",
    "artifacts/formulation/rule_spec.json": "40f9bb9e657b",
}
CARRIERS = [
    # id, path, expected sha prefix (None = record whatever is live; still snapshotted)
    ("live_c0_rev29", "schemas/af_scc_c0_vacuum.yaml", "b2ab6acb2bbe"),
    ("c2_sibling_live", "schemas/af_scc_c2_vacuum.yaml", "e9a27996dfd3"),
    ("rehearsed_058_84b5d3fa",
     "artifacts/worker08/rev29_candidate/af_scc_c0_vacuum.repair-candidate.yaml",
     "84b5d3fa29a6"),
    ("composite_076",
     "artifacts/worker-076/f2b_repair_landing_audit/candidate/af_scc_c0_vacuum.repair-minimal.yaml",
     None),
    ("corrected_080_51c253c4",
     "artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_corrected.yaml",
     "51c253c46306"),
    ("nesting_only_080_4951cc96",
     "artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_nesting_only.yaml",
     "4951cc969803"),
    ("cd_repair_022_a110f8",
     "artifacts/worker-022/f2b_cd_repair/candidate/af_scc_c0_vacuum.repair-candidate.yaml",
     "a110f8e875af"),
    ("rev13_integration_044_48cadb",
     "artifacts/worker-044/f2b_rev13_integration/sandbox/schemas/af_scc_c0_vacuum.yaml",
     "48cadb72e507"),
]

BRACKET_RE = re.compile(r"\[[^\]]*\]", re.S)
DENIAL_RE = re.compile(r"no\s+containment\s+with", re.I)
# "<X>-inextendibility ENTAILS this class" (any X)
INV_RE = re.compile(r"\b(H2_?loc|C2|C0|C\^?\{?1,1\}?)-inextendibility\s+ENTAILS\s+this class", re.I)
# "this class's ... ENTAILS ... <Y>" / "C0-inextendibility is the strongest ... ENTAILS"
CORR_RE = re.compile(
    r"this class'?s?\s+(?:C0-)?inextendibility[^.]{0,120}?ENTAILS[^.]{0,60}?(H2_?loc|C2)",
    re.I)
CORR_CONCL_RE = re.compile(
    r"this class'?s?\s+conclusion[^.]{0,120}?ENTAILS[^.]{0,60}?(H2_?loc|C2)",
    re.I)
CORR_STRONG_RE = re.compile(
    r"\b(C0|C2)-inextendibility is the strongest[^.]{0,120}?ENTAILS[^.]{0,60}?(H2_?loc|C2|the)",
    re.I)
SIB_RE = re.compile(r"entails\s+the\s+C2\s+sibling", re.I)
NEST_RE = re.compile(r"E_C2\s+subset of\s+E_\{?C\^?\{?1,1\}?\}?\s+subset of\s+E_H2_?loc\s+subset of\s+E_C0", re.I)
AGNOSTIC_RE = re.compile(r"direction of the induced entailments[^.]*recorded", re.I)
ENTAIL_VERB_RE = re.compile(r"\bENTAILS\b", re.I)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def strip_bracketed(text: str) -> str:
    """Remove bracketed repair notes so quoted/withdrawn denials do not read as live."""
    return BRACKET_RE.sub(" ", text)


def classify(text: str, this_tok: str) -> dict:
    """Classify one must_not_conflate[0] sentence, class-relative."""
    outside = strip_bracketed(text)
    live_denial = bool(DENIAL_RE.search(outside))
    nesting = bool(NEST_RE.search(text))
    this_pos = ENTAIL_ORDER.index(this_tok)
    weaker = ENTAIL_ORDER[this_pos + 1] if this_pos + 1 < len(ENTAIL_ORDER) else None

    inv = INV_RE.search(outside)
    corr = CORR_RE.search(outside) or CORR_CONCL_RE.search(outside) or CORR_STRONG_RE.search(outside)
    sib = SIB_RE.search(outside)
    agnostic = bool(AGNOSTIC_RE.search(outside))
    has_verb = bool(ENTAIL_VERB_RE.search(outside))

    if live_denial:
        cls = "LIVE_DENIAL"
        matched = DENIAL_RE.search(outside).group(0)
        direction = "denies containment that the same file's chain asserts"
    elif inv:
        subj = inv.group(1).upper().replace("_", "")
        subj_pos = ENTAIL_ORDER.index("H2LOC") if "H2" in subj else (
            ENTAIL_ORDER.index("C2") if subj == "C2" else ENTAIL_ORDER.index("C0"))
        # subject entails this class; correct iff subject is strictly stronger (earlier in
        # entailment order).  Adjacency is not required (C11 sits between H2LOC and C2).
        if subj_pos < this_pos:
            cls = "CORRECT_ENTAILMENT"
            direction = f"{subj} => this({this_tok})"
        else:
            cls = "INVERTED_ENTAILMENT"
            direction = f"{subj} => this({this_tok}) but {this_tok} => {subj} is the declared direction"
        matched = inv.group(0)
    elif corr and weaker:
        cls = "CORRECT_ENTAILMENT"
        direction = f"this({this_tok}) => {weaker}"
        matched = corr.group(0)
    elif sib and this_tok == "C2":
        cls = "CORRECT_ENTAILMENT"
        direction = "H2_loc => this(C2)"
        matched = sib.group(0)
    elif has_verb:
        cls = "UNCLASSIFIED_ENTAILMENT"
        direction = "entailment verb present but neither pattern matched"
        matched = ENTAIL_VERB_RE.search(outside).group(0)
    elif agnostic and nesting:
        cls = "AGNOSTIC_NESTING_ONLY"
        direction = "nesting stated; direction deferred to implication_ledger"
        matched = AGNOSTIC_RE.search(outside).group(0)
    elif nesting:
        cls = "NESTING_NO_DIRECTION"
        direction = "nesting stated, no entailment direction"
        matched = NEST_RE.search(outside).group(0)
    else:
        cls = "NO_H2_CLAUSE"
        direction = "no H2_loc sentence found"
        matched = None
    return {
        "classification": cls,
        "class": this_tok,
        "declared_direction": f"{this_tok} => {weaker}" if weaker else None,
        "observed_direction": direction,
        "live_denial": live_denial,
        "nesting_present": nesting,
        "matched_text": matched,
        "sentence": text,
    }


def load_carrier(path: Path) -> tuple[dict, str]:
    raw = path.read_bytes()
    doc = yaml.safe_load(raw)
    if not isinstance(doc, dict):
        raise SystemExit(f"FAIL-CLOSED: {path} is not a YAML mapping")
    return doc, sha256_bytes(raw)


def tool_run(cmd: list[str]) -> dict:
    r = subprocess.run(cmd, capture_output=True, text=True)
    out = {"cmd": cmd, "exit_code": r.returncode, "stdout_tail": r.stdout.strip().splitlines()[-3:]}
    return out


def battery(carrier: Path, label: str) -> dict:
    j = SCRATCH / f"battery_{label}.json"
    m = SCRATCH / f"battery_{label}.md"
    cmd = [sys.executable, str(ROOT / "artifacts/worker08/c2_c0_separation_audit.py"),
           "--c2", str(ROOT / "schemas/af_scc_c2_vacuum.yaml"),
           "--c0", str(carrier), "--out-json", str(j), "--out-md", str(m), "--label", label]
    out = tool_run(cmd)
    verdict, hits = None, None
    if j.exists():
        try:
            d = json.loads(j.read_text())
            verdict = d.get("verdict")
            hits = d.get("checks", {}).get("X3c_containment_inversion", {}).get("hits")
        except Exception:  # noqa: BLE001
            pass
    out.update({"verdict": verdict, "x3c_hits": hits})
    return out


def dual(carrier: Path, label: str, expect_c0: str, expect_c2: str) -> dict:
    j = SCRATCH / f"dual_{label}.json"
    cmd = [sys.executable, str(ROOT / "artifacts/worker-008/f2b_rev11_dualrepair/audit_dual_defect.py"),
           "--c0", str(carrier), "--c2", str(ROOT / "schemas/af_scc_c2_vacuum.yaml"),
           "--expect-c0", expect_c0, "--expect-c2", expect_c2,
           "--label", label, "--json", str(j)]
    out = tool_run(cmd)
    if j.exists():
        try:
            d = json.loads(j.read_text())
            out.update({"verdict": d.get("verdict"), "n_findings": len(d.get("findings", []))})
        except Exception:  # noqa: BLE001
            pass
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--generated-at", default="2026-09-12T01:25:00+08:00")
    ap.add_argument("--emit", action="store_true")
    ap.add_argument("--skip-tools", action="store_true")
    args = ap.parse_args()

    SNAP.mkdir(exist_ok=True)
    SCRATCH.mkdir(exist_ok=True)

    report: dict = {
        "schema": "w053-f2b-h2-direction/v1",
        "task_id": "W053-F2B-REV30-H2-DIRECTION-01",
        "actor": "worker-053",
        "node_id": "F2b",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
        "gate": "G-FORM",
        "generated_at": args.generated_at,
        "authority": "worker measurement only; no canonical write, no gate verdict, no node status, no validation_status",
        "ground_truth_order": {"set_order_largest_first": SET_ORDER, "entailment_order": ENTAIL_ORDER},
        "pins": {}, "carriers": [], "controls": [], "problems": [],
    }

    # ---- pin measurement (fail closed) -------------------------------------------------
    for rel, pref in PINS.items():
        p = ROOT / rel
        if not p.exists():
            report["problems"].append(f"missing pin {rel}")
            continue
        h = sha256_file(p)
        report["pins"][rel] = {"sha256": h, "expected_prefix": pref, "match": h.startswith(pref)}
        if not h.startswith(pref):
            report["problems"].append(f"pin drift {rel}: {h[:16]} !~ {pref}")
    c2_live = report["pins"]["schemas/af_scc_c2_vacuum.yaml"]["sha256"]

    # ---- carriers ----------------------------------------------------------------------
    for cid, rel, pref in CARRIERS:
        p = ROOT / rel
        if not p.exists():
            report["problems"].append(f"missing carrier {cid} at {rel}")
            continue
        doc, live_hash = load_carrier(p)
        snap = SNAP / f"{cid}.{live_hash[:12]}.yaml"
        shutil.copyfile(p, snap)
        snap_hash = sha256_file(snap)
        cls = doc.get("class_id", "")
        if cls not in CLASS_OF_FILE:
            report["problems"].append(f"carrier {cid} has unknown class_id {cls!r}")
            continue
        this_tok = CLASS_OF_FILE[cls]
        mnc = (doc.get("regularity") or {}).get("must_not_conflate") or []
        mnc_idx = next((i for i, s in enumerate(mnc) if isinstance(s, str) and "H2_loc" in s), None)
        sentence = mnc[mnc_idx] if mnc_idx is not None else ""
        res = classify(sentence, this_tok)
        entry = {
            "id": cid, "path": rel, "class_id": cls, "this_class_token": this_tok,
            "live_sha256": live_hash, "snapshot": str(snap.relative_to(ROOT)),
            "snapshot_sha256": snap_hash, "expected_prefix": pref,
            "expected_match": (live_hash.startswith(pref) if pref else None),
            "must_not_conflate_index": mnc_idx,
            "classification": res["classification"], "detail": res,
        }
        if not args.skip_tools:
            entry["acceptance_tools"] = {
                "worker08_battery": battery(snap, cid),
                "worker008_dual": dual(snap, cid, snap_hash, c2_live),
            }
        report["carriers"].append(entry)

    # ---- class-blindness control on the C2 sibling -------------------------------------
    c2doc, c2hash = load_carrier(ROOT / "schemas/af_scc_c2_vacuum.yaml")
    c2mnc = (c2doc.get("regularity") or {}).get("must_not_conflate") or []
    c2sent = next((s for s in c2mnc if isinstance(s, str) and "H2_loc" in s), "")
    report["c2_sibling_control"] = classify(c2sent, "C2")

    # ---- in-memory mutation controls ---------------------------------------------------
    live_c0 = next((c for c in report["carriers"] if c["id"] == "live_c0_rev29"), None)
    base = live_c0["detail"]["sentence"] if live_c0 else ""
    r2_correct = ("H2_loc is a distinct regularity-axis value. The extension sets are nested: "
                  "E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0. This class's "
                  "C0-inextendibility is the strongest of the three and ENTAILS the H2_loc and C2 "
                  "conclusions; see implication_ledger.")
    r2_inverted = ("H2_loc is a distinct regularity-axis value. The extension sets are nested: "
                   "E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0, so "
                   "H2_loc-inextendibility ENTAILS this class's conclusion; see implication_ledger.")
    controls = [
        ("K1_live_c0_denial", base, "C0", "LIVE_DENIAL"),
        ("K2_r2_correct_direction", r2_correct, "C0", "CORRECT_ENTAILMENT"),
        ("K3_r2_inverted_direction", r2_inverted, "C0", "INVERTED_ENTAILMENT"),
        ("K4_sibling_sentence_as_own_C2", c2sent, "C2", "CORRECT_ENTAILMENT"),
        ("K5_sibling_sentence_as_own_C0", c2sent, "C0", "INVERTED_ENTAILMENT"),
        ("K6_agnostic_nesting", ("The extension sets are nested: E_C2 subset of E_{C^1,1} subset "
                                 "of E_H2loc subset of E_C0; the direction of the induced "
                                 "entailments is recorded there."), "C0", "AGNOSTIC_NESTING_ONLY"),
    ]
    for kid, text, tok, expect in controls:
        got = classify(text, tok)["classification"]
        report["controls"].append({"id": kid, "expect": expect, "observed": got, "pass": got == expect})
        if got != expect:
            report["problems"].append(f"control {kid}: expected {expect}, observed {got}")

    # ---- drift re-check ----------------------------------------------------------------
    drift = []
    for cid, rel, pref in CARRIERS:
        p = ROOT / rel
        if p.exists() and any(c["id"] == cid for c in report["carriers"]):
            entry = next(c for c in report["carriers"] if c["id"] == cid)
            now = sha256_file(p)
            if now != entry["snapshot_sha256"]:
                drift.append({"id": cid, "path": rel, "at_snapshot": entry["snapshot_sha256"], "now": now})
    report["carrier_drift_during_run"] = drift
    if drift:
        report["problems"].append(f"carrier bytes moved during run: {[d['id'] for d in drift]}")

    # ---- findings ----------------------------------------------------------------------
    def find(cid: str):
        return next((c for c in report["carriers"] if c["id"] == cid), None)

    findings = []
    rehe = find("rehearsed_058_84b5d3fa")
    if rehe and rehe["classification"] == "INVERTED_ENTAILMENT":
        findings.append({
            "id": "W053-H2-01",
            "severity": "blocking-for-rev30-publication",
            "carrier": rehe["id"], "sha256": rehe["live_sha256"],
            "finding": "the rehearsed rev30 carrier repairs the line-246 premise but its replacement "
                       "must_not_conflate[0] asserts the converse entailment: "
                       "'so H2_loc-inextendibility ENTAILS this class's conclusion', while the file's "
                       "own chain has E_C0 as the largest extension set, so C0-inextendibility is the "
                       "strongest and entails H2_loc-inextendibility, not conversely. It also "
                       "contradicts the retained line-232 declaration ('entails the C2 sibling, not "
                       "this class'). Corroborates worker-088's block with an independent instrument.",
            "falsifier": "re-measure at the same sha256 and show the sentence orders this(C0) => H2_loc, "
                         "or show the file's own chain has E_C0 smaller than E_H2loc",
        })
    comp = find("composite_076")
    if comp and comp["classification"] == "INVERTED_ENTAILMENT":
        findings.append({
            "id": "W053-H2-02",
            "severity": "blocking-for-rev30-publication",
            "carrier": comp["id"], "sha256": comp["live_sha256"],
            "finding": "the worker-076 composite carrier carries the same inverted H2 closing clause "
                       "as the rehearsed carrier and yet passed its own 10-check audit; this carrier "
                       "was not covered by worker-088's guard.",
            "falsifier": "re-measure at the same sha256 and show the sentence orders this(C0) => H2_loc",
        })
    safe = [c["id"] for c in report["carriers"]
            if c["classification"] in ("CORRECT_ENTAILMENT", "AGNOSTIC_NESTING_ONLY") and c["class_id"] == "AF-SCC-C0-VAC-GEN"]
    if safe:
        findings.append({
            "id": "W053-H2-03", "severity": "info",
            "finding": f"direction-clean staged C0 carriers at their measured hashes: {safe}",
            "falsifier": "any of those carriers classifies as live denial or inverted at its measured sha256",
        })
    blind = []
    for c in report["carriers"]:
        if c["classification"] in ("INVERTED_ENTAILMENT", "LIVE_DENIAL"):
            t = c.get("acceptance_tools", {})
            b = (t.get("worker08_battery") or {}).get("verdict")
            d = (t.get("worker008_dual") or {}).get("verdict")
            if b == "PASS" or d == "PASS":
                blind.append({"id": c["id"], "sha256": c["live_sha256"],
                              "battery": b, "dual": d, "classification": c["classification"]})
    if blind:
        findings.append({
            "id": "W053-H2-04", "severity": "process",
            "finding": "acceptance-tool blindness measured: carriers classified INVERTED/LIVE_DENIAL "
                       "by this instrument still return PASS from at least one acceptance tool "
                       "used by the rev30 rehearsal; the tools do not assert the H2 entailment direction.",
            "detail": blind,
            "falsifier": "a re-run of the named tools on the same bytes returning non-PASS, or a tool "
                         "revision that asserts the H2 direction",
        })
    old44 = find("rev13_integration_044_48cadb")
    if old44 and old44["classification"] == "INVERTED_ENTAILMENT":
        findings.append({
            "id": "W053-H2-05", "severity": "process",
            "carrier": old44["id"], "sha256": old44["live_sha256"],
            "finding": "an earlier staged carrier (worker-044 rev13 integration) carries the same "
                       "inverted H2 clause and was adjudicated REPAIR_OK by worker-007's reusable "
                       "predicate; that predicate asserts denial absence, chain order and one-way "
                       "entailment rows but not the direction of the H2 closing clause, so a "
                       "REPAIR_OK from it is not evidence of H2 direction.",
            "falsifier": "worker-007's predicate shown to assert the H2 entailment direction, or the "
                         "carrier shown to order this(C0) => H2_loc at its measured sha256",
        })
    old22 = find("cd_repair_022_a110f8")
    if old22 and old22["classification"] == "NO_H2_CLAUSE":
        findings.append({
            "id": "W053-H2-06", "severity": "info",
            "carrier": old22["id"], "sha256": old22["live_sha256"],
            "finding": "another staged carrier (worker-022) carries no H2 containment/entailment clause "
                       "at all: its H2_loc bullet keeps axis distinctness and a qualified "
                       "'no metric-differentiability containment' note. It is neither inverted nor a "
                       "live flat denial; whether the H2 nesting/entailment statement must be restored "
                       "is an owner adjudication (R06 only requires the list to be non-empty).",
            "falsifier": "the carrier shown to contain an H2 containment/entailment clause at its "
                         "measured sha256, or a gate criterion requiring the H2 nesting sentence",
        })
    report["findings"] = findings
    report["staged_carriers_direction_clean"] = safe
    report["recommendation"] = {
        "do_not_land": [c["id"] for c in report["carriers"] if c["classification"] == "INVERTED_ENTAILMENT"],
        "prefer": safe,
        "owner_condition": "land a direction-adapted H2 clause (worker-075 R2 text, worker-080 corrected, "
                           "or the nesting-only form), keep the line-246 H1 fix, re-freeze with a strictly "
                           "increasing revision, update the worker-058 runbook pointer, and add an H2 "
                           "direction assertion to the acceptance battery/dual tools before dispatch.",
    }
    report["falsifier"] = ("Re-run this script at the same carrier sha256s: any carrier classified "
                           "INVERTED_ENTAILMENT here that orders this(C0) => H2_loc in its own text, "
                           "any control not reproducing its expectation, any pin/carrier hash drift, or "
                           "any acceptance tool returning non-PASS on a flagged carrier voids the "
                           "corresponding finding.")

    out = HERE / "report.json"
    text = json.dumps(report, indent=1, sort_keys=True)
    if args.emit:
        out.write_text(text + "\n")
    print(json.dumps({k: report[k] for k in
                      ("schema", "task_id", "generated_at", "findings", "problems",
                       "staged_carriers_direction_clean", "carrier_drift_during_run")}, indent=1)[:4000])
    for c in report["carriers"]:
        t = c.get("acceptance_tools", {})
        print(f"{c['id']:34s} {c['live_sha256'][:12]}  {c['classification']:24s} "
              f"battery={(t.get('worker08_battery') or {}).get('verdict')} "
              f"dual={(t.get('worker008_dual') or {}).get('verdict')}")
    return 2 if report["problems"] else 0


if __name__ == "__main__":
    sys.exit(main())
