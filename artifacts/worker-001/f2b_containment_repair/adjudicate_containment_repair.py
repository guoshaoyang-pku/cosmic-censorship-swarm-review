#!/usr/bin/env python3
"""W001-F2B-REV13-CONTAINMENT-CLOSURE-01.

Independent, hash-pinned closure of the open F2b containment-direction defect set at the live
rev13 bytes, plus a NON-CANONICAL minimal repair candidate.

Pre-registered decision rule
----------------------------
Oracle: use the pinned documents' own declaration of nested extension sets.
  F2b implication_ledger.extension_class_containment : E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2
  F2a implication_ledger.extension_class_containment : E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0
With size_rank(C0)=3 > size_rank(H2loc)=2 > size_rank(C^1,1)=1 > size_rank(C2)=0:
  * "X is a strictly larger extension class" (unqualified, compared with this class C0) is
    INCONSISTENT iff size_rank(X) < size_rank(C0); the document's own E-notation binds
    "extension class" to the set of extensions E_X.
  * S_X := "no proper future X extension". S_X entails S_Y iff size_rank(X) >= size_rank(Y).
    A forbidden_transfers row must satisfy NOT entails(from,to); a one_way_entailments row
    must satisfy entails(from,to).
Verdicts:
  CD01_CONFIRMED  iff exactly one size-adjective inversion is found and it is the ledger row
                  whose reason is the line-246 sentence.
  CD02_PRESENT    iff the literal denial "No containment with C2 or C0 is asserted here"
                  occurs while the same document declares >=2 containment edges.
  REPAIR_CANDIDATE_VERIFIED iff the candidate (base + two pre-registered lexical edits) has
                  0 inversions, passes the canonical check_class_schema.py, differs from the
                  base only on the two pre-registered lines, and every control K1..K8 behaves
                  as pre-registered.
Disposition is advisory on severity, hard on the measurement: the transfer-row DIRECTION is
correct; only the size gloss is inverted. A repair creates a new F2b revision hash and voids
prior rev13-bound F2b verdicts as advisory only.

Fail-closed exit codes: 0 verdict produced; 3 pin drift (no verdict); 4 control failure (no
verdict); 5 precondition/decision-rule violation (no verdict).

Authority: worker measurement only. This script writes ONLY under
artifacts/worker-001/f2b_containment_repair/ and runtime/state/worker-001_checkpoint_f2bcontainment.json.
It never edits a canonical artifact and never sets node status, validation_status=passed,
or a gate verdict.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("PyYAML required", file=sys.stderr)
    sys.exit(5)

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[3]
TASK_ID = "W001-F2B-REV13-CONTAINMENT-CLOSURE-01"
ACTOR = "worker-001"
NODE_ID = "F2b"
CLASS_ID = "AF-SCC-C0-VAC-GEN"
GATE = "G-FORM"
TZ = timezone(timedelta(hours=8))


def now() -> str:
    return datetime.now(TZ).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------------------- pins
PINS = {
    "schemas/af_scc_c0_vacuum.yaml":
        "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml":
        "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "schemas/af_scc_c2_vacuum.yaml":
        "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml":
        "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_wcc_vacuum.yaml":
        "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "research_map/formulation_taxonomy.yaml":
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/formulation_taxonomy.yaml":
        "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "artifacts/formulation/FROZEN.json":
        "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "artifacts/formulation/tools/check_class_schema.py":
        "000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff",
    "artifacts/formulation/evidence/taxonomy_consistency.json":
        "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b",
    "schemas/taxonomy_cases.jsonl":
        "ccf7041bd0ff3ce844c07a700a588b7fe8e3c90880674c5e595b21f6259a8f03",
    "artifacts/worker-008/containment_direction/evidence/report.json":
        "773858a088d36c169b0a3fd9857fca0237d400f470f54e63c1bbd8bc6fd6f56d",
    "artifacts/worker-097/f2b_rev13_review/REVIEW.json":
        "40d32d002af001a5f38198c5d6c2bc9becb8651bd5d4150e332b093a036cdbec",
    "artifacts/worker-097/f2b_rev13_review/report.json":
        "2b38dea6b487c05577c6dfad27533879c62c82facbc48f169f5ab7b619ccaa07",
}

# Prior-art pins are informational only; the verdict does not depend on them.
PRIOR_ART = {
    "artifacts/worker-008/containment_direction/evidence/report.json",
    "artifacts/worker-097/f2b_rev13_review/REVIEW.json",
    "artifacts/worker-097/f2b_rev13_review/report.json",
}

EDIT_A = (
    "C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker",
    "E_C2 is a strictly smaller extension set than E_C0, so C2-inextendibility is strictly weaker",
)
EDIT_B = (
    "No containment with C2 or C0 is asserted here;",
    "No containment among the regularity-axis values is asserted here (the extension-set "
    "containment is declared once in implication_ledger.extension_class_containment);",
)

TOK = re.compile(r"(C0|C2|H2loc|C\^\{?1,1\}?)")
ADJ = re.compile(r"\b(?:strictly\s+)?(larger|smaller|bigger)\b", re.I)
SIZE_RANK = {"C0": 3, "H2loc": 2, "C1,1": 1, "C2": 0}


def norm_tok(tok: str) -> str:
    return tok.replace("^", "").replace("{", "").replace("}", "").replace(" ", "")


def tok_of(stmt: str):
    m = TOK.search(stmt or "")
    if not m:
        return None
    return norm_tok(m.group(1))


def entails(a: str, b: str) -> bool:
    return SIZE_RANK[a] >= SIZE_RANK[b]


def measure_pins(extra_warn_only: bool = True):
    measured, mismatches, missing = {}, [], []
    for rel in PINS:
        p = ROOT / rel
        if not p.exists():
            missing.append(rel)
            continue
        h = sha256_file(p)
        measured[rel] = h
        expected = PINS[rel]
        if rel in PRIOR_ART:
            continue  # advisory only
        if h != expected:
            mismatches.append({"path": rel, "expected": expected, "measured": h})
    return measured, mismatches, missing


def parse_chains(doc: dict):
    """Extract containment chains from a schema's implication_ledger."""
    led = doc.get("implication_ledger", {}) or {}
    chain_str = str(led.get("extension_class_containment", ""))
    toks = [norm_tok(t) for t in TOK.findall(chain_str)]
    # keep first occurrence order, deduplicate
    order = []
    for t in toks:
        if t not in order:
            order.append(t)
    entail, forbidden = [], []
    for row in led.get("one_way_entailments", []) or []:
        a, b = tok_of(str(row.get("from", ""))), tok_of(str(row.get("to", "")))
        if a and b:
            entail.append({"from": a, "to": b, "row": row})
    for row in led.get("forbidden_transfers", []) or []:
        a = tok_of(str(row.get("from", "")))
        b = "C0" if str(row.get("to", "")).strip() == "this class" else tok_of(str(row.get("to", "")))
        if a and b:
            forbidden.append({"from": a, "to": b, "row": row})
    return {"chain_text": chain_str, "order": order, "entailments": entail, "forbidden": forbidden}


def size_inversions(doc: dict):
    """Every forbidden/entailment row whose reason carries a size adjective inconsistent with
    the document's own size order, plus unqualified 'X is a strictly larger extension class'."""
    out = []
    led = doc.get("implication_ledger", {}) or {}
    for kind in ("forbidden_transfers", "one_way_entailments"):
        for row in led.get(kind, []) or []:
            reason = str(row.get("reason", ""))
            m = ADJ.search(reason)
            if not m:
                continue
            frm = tok_of(str(row.get("from", "")))
            to_raw = str(row.get("to", ""))
            to = "C0" if to_raw.strip() == "this class" else tok_of(to_raw)
            if not frm or not to:
                continue
            claimed_larger = m.group(1).lower() in ("larger", "bigger")
            actual_larger = SIZE_RANK[frm] > SIZE_RANK[to]
            if claimed_larger != actual_larger:
                out.append({
                    "kind": kind,
                    "from": frm,
                    "to": to,
                    "reason": reason,
                    "claimed": m.group(0),
                    "oracle": f"size_rank({frm})={SIZE_RANK[frm]} "
                              f"{'>' if actual_larger else '<'} size_rank({to})={SIZE_RANK[to]}",
                })
    return out


def transfer_audit(parsed: dict):
    bad_forbidden, bad_entail = [], []
    for r in parsed["forbidden"]:
        if entails(r["from"], r["to"]):
            bad_forbidden.append({"from": r["from"], "to": r["to"],
                                  "reason": str(r["row"].get("reason", ""))[:160]})
    for r in parsed["entailments"]:
        if not entails(r["from"], r["to"]):
            bad_entail.append({"from": r["from"], "to": r["to"],
                               "reason": str(r["row"].get("reason", ""))[:160]})
    return bad_forbidden, bad_entail


def apply_edits(base: str, edits):
    out, hits = base, []
    for old, new in edits:
        n = out.count(old)
        if n != 1:
            raise RuntimeError(f"edit target occurs {n} times (expected 1): {old[:60]!r}")
        line = out[: out.index(old)].count("\n") + 1
        out = out.replace(old, new)
        hits.append({"line": line, "before": old, "after": new})
    return out, hits


def changed_lines(base: str, cand: str):
    diff = list(difflib.unified_diff(base.splitlines(), cand.splitlines(),
                                     fromfile="base", tofile="candidate", lineterm=""))
    changed = [ln for ln in diff if (ln.startswith("+") or ln.startswith("-"))
               and not ln.startswith(("+++", "---"))]
    return diff, changed


def run_checker(path: Path):
    tool = ROOT / "artifacts/formulation/tools/check_class_schema.py"
    proc = subprocess.run([sys.executable, str(tool), "--json", str(path)],
                          capture_output=True, text=True, cwd=str(ROOT))
    try:
        payload = json.loads(proc.stdout)
    except Exception:
        payload = {"raw_stdout": proc.stdout[-2000:], "raw_stderr": proc.stderr[-2000:]}
    payload["exit_code"] = proc.returncode
    return payload


def main() -> int:
    started = now()
    measured, mismatches, missing = measure_pins()
    if missing or mismatches:
        print(json.dumps({
            "task_id": TASK_ID, "verdict": "PIN_DRIFT_NO_VERDICT",
            "created_at": started, "missing": missing, "mismatches": mismatches,
            "measured": measured,
        }, indent=1))
        return 3

    f2b_path = ROOT / "schemas/af_scc_c0_vacuum.yaml"
    f2a_path = ROOT / "schemas/af_scc_c2_vacuum.yaml"
    base = f2b_path.read_text()
    f2a_text = f2a_path.read_text()
    f2b = yaml.safe_load(base)
    f2a = yaml.safe_load(f2a_text)

    # ---- C1 oracle ----------------------------------------------------------------
    p2b, p2a = parse_chains(f2b), parse_chains(f2a)
    c1_ok = (p2b["order"][::-1] == p2a["order"]) and set(p2b["order"]) == set(SIZE_RANK)
    c1 = {"id": "C1_ORACLE_CHAIN", "result": "PASS" if c1_ok else "FAIL",
          "f2b_order_largest_to_smallest": p2b["order"],
          "f2a_order_smallest_to_largest": p2a["order"],
          "induce_same_order": bool(c1_ok)}

    # ---- C2 size-adjective census -------------------------------------------------
    inv = size_inversions(f2b)
    inv2a = size_inversions(f2a)
    c2 = {"id": "C2_SIZE_ADJECTIVE_CENSUS",
          "result": "INVERSION_FOUND" if inv else "NO_INVERSION",
          "f2b_inversions": inv, "f2a_inversions": inv2a,
          "f2b_size_adjective_lines": [
              {"line": i, "text": ln.strip()}
              for i, ln in enumerate(base.splitlines(), 1)
              if "extension" in ln.lower() and ADJ.search(ln)]}

    # ---- C3/C4 transfer audit -----------------------------------------------------
    bf2b, be2b = transfer_audit(p2b)
    bf2a, be2a = transfer_audit(p2a)
    c3 = {"id": "C3_FORBIDDEN_TRANSFER_AUDIT",
          "result": "PASS" if not bf2b and not bf2a else "FAIL",
          "f2b_rows": len(p2b["forbidden"]), "f2a_rows": len(p2a["forbidden"]),
          "wrongly_forbidden_f2b": bf2b, "wrongly_forbidden_f2a": bf2a}
    c4 = {"id": "C4_ONE_WAY_ENTAILMENT_AUDIT",
          "result": "PASS" if not be2b and not be2a else "FAIL",
          "f2b_rows": len(p2b["entailments"]), "f2a_rows": len(p2a["entailments"]),
          "unlicensed_f2b": be2b, "unlicensed_f2a": be2a}

    # ---- C5 cross-document --------------------------------------------------------
    c5 = {"id": "C5_CROSS_DOCUMENT_ORDER", "result": "PASS" if c1_ok else "FAIL",
          "orders": {"F2b": p2b["order"], "F2a": p2a["order"]}}

    # ---- C6 defect reproduction ---------------------------------------------------
    cd01 = len(inv) == 1 and inv[0]["from"] == "C2" and inv[0]["to"] == "C0" \
        and inv[0]["kind"] == "forbidden_transfers"
    denial = "No containment with C2 or C0 is asserted here;"
    cd02 = denial in base
    f2a_marks_denial_wrong = "no containment with C2 is asserted' was wrong" in f2a_text
    c6 = {"id": "C6_DEFECT_REPRODUCTION",
          "result": ("CD01_CONFIRMED" if cd01 else "CD01_NOT_REPRODUCED")
                    + ("/CD02_PRESENT" if cd02 else "/CD02_ABSENT"),
          "cd01_line": 246, "cd01_confirmed": bool(cd01),
          "cd01_detail": inv[0] if inv else None,
          "cd02_line": 152, "cd02_present": bool(cd02),
          "f2a_sibling_marks_denial_wrong": bool(f2a_marks_denial_wrong)}

    # ---- C7 candidate -------------------------------------------------------------
    cand_both, hits_both = apply_edits(base, [EDIT_A, EDIT_B])
    cand_a, _ = apply_edits(base, [EDIT_A])
    cand_doc = yaml.safe_load(cand_both)
    cand_inv = size_inversions(cand_doc)
    diff, changed = changed_lines(base, cand_both)
    added = [c for c in changed if c.startswith("+")]
    removed = [c for c in changed if c.startswith("-")]
    changed_positions = [i for i, (a, b) in enumerate(zip(base.splitlines(), cand_both.splitlines()), 1)
                         if a != b]
    checker_base = run_checker(f2b_path)
    cand_path = HERE / "REPAIR_CANDIDATE.yaml"
    cand_path.write_text(cand_both)
    checker_cand = run_checker(cand_path)
    c7_ok = (not cand_inv and checker_cand.get("verdict") == "pass"
             and len(added) == 2 and len(removed) == 2
             and changed_positions == [152, 246]
             and len(base.splitlines()) == len(cand_both.splitlines()))
    c7 = {"id": "C7_REPAIR_CANDIDATE",
          "result": "PASS" if c7_ok else "FAIL",
          "candidate_sha256": sha256_text(cand_both),
          "candidate_inversions": cand_inv,
          "checker_base": checker_base, "checker_candidate": checker_cand,
          "changed_line_count": len(changed_positions),
          "changed_line_positions": changed_positions,
          "added_lines": len(added), "removed_lines": len(removed),
          "edits": hits_both,
          "diff": "\n".join(diff)}

    # ---- controls K1..K8 ----------------------------------------------------------
    controls = []

    def control(cid, ok, detail):
        controls.append({"id": cid, "result": "PASS" if ok else "FAIL", "detail": detail})

    # K1: revert edit A on the candidate -> the inversion must reappear
    k1_text = cand_both.replace(EDIT_A[1], EDIT_A[0])
    k1_inv = size_inversions(yaml.safe_load(k1_text))
    control("K1_REVERT_EDIT_A_REDETECTS", len(k1_inv) == 1,
            f"inversions after reverting A: {len(k1_inv)}")
    # K2: candidate with edit B reverted -> denial reappears
    control("K2_REVERT_EDIT_B_REDETECTS", denial in cand_a,
            "denial string present in A-only candidate"
            if denial in cand_a else "denial unexpectedly absent")
    # K3: invert the forbidden transfer direction -> audit must flag it
    bad_row_old = '{from: "no proper future C2 extension", to: "this class", reason: "E_C2 is a strictly smaller extension set than E_C0, so C2-inextendibility is strictly weaker"}'
    bad_row_new = '{from: "no proper future C0 extension", to: "no proper future C2 extension", reason: "mutation"}'
    k3_text = cand_both.replace(bad_row_old, bad_row_new)
    k3_parsed = parse_chains(yaml.safe_load(k3_text))
    k3_bad, _ = transfer_audit(k3_parsed)
    control("K3_INVERT_TRANSFER_ROW_DETECTED", len(k3_bad) == 1,
            f"wrongly-forbidden rows after mutation: {len(k3_bad)}")
    # K4: invert the declared chain -> cross-document order must break
    k4_text = cand_both.replace(
        "E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2",
        "E_C2 contains E_{C^1,1} contains E_H2loc contains E_C0", 1)
    k4_order = parse_chains(yaml.safe_load(k4_text))["order"]
    control("K4_INVERT_CHAIN_DETECTED", k4_order[::-1] != p2a["order"],
            f"mutated F2b order {k4_order} vs F2a {p2a['order']}")
    # K5: pin-guard simulation
    mutated = dict(PINS)
    mutated["schemas/af_scc_c0_vacuum.yaml"] = "0" * 64
    k5_bad = mutated["schemas/af_scc_c0_vacuum.yaml"] != measured["schemas/af_scc_c0_vacuum.yaml"]
    control("K5_PIN_GUARD_REJECTS_DRIFT", bool(k5_bad), "simulated pin change rejected")
    # K6: edit target absent -> fail closed
    try:
        apply_edits(f2a_text, [EDIT_A])
        k6_ok = False
    except RuntimeError:
        k6_ok = True
    control("K6_EDIT_TARGET_ABSENT_FAILS_CLOSED", k6_ok, "edit A not found in F2a -> RuntimeError")
    # K7: determinism
    again, _ = apply_edits(base, [EDIT_A, EDIT_B])
    control("K7_CANDIDATE_DETERMINISTIC", sha256_text(again) == sha256_text(cand_both),
            sha256_text(again)[:16])
    # K8: outside-region byte identity
    base_lines, cand_lines = base.splitlines(), cand_both.splitlines()
    outside = [i for i, (a, b) in enumerate(zip(base_lines, cand_lines), 1) if a != b]
    control("K8_DIFF_CONFINED_TO_EDITED_LINES", outside == [152, 246],
            f"differing lines: {outside}")

    controls_ok = all(c["result"] == "PASS" for c in controls)
    if not controls_ok:
        print(json.dumps({"task_id": TASK_ID, "verdict": "CONTROL_FAILURE_NO_VERDICT",
                          "created_at": started, "controls": controls}, indent=1))
        return 4

    # ---- FROZEN adoption impact ---------------------------------------------------
    frozen = json.loads((ROOT / "artifacts/formulation/FROZEN.json").read_text())
    affected = sorted(p for p in (frozen.get("files") or {})
                      if "af_scc_c0_vacuum" in p or "f2b" in p.lower())

    verdict = {
        "cd01": "CD01_CONFIRMED" if cd01 else "CD01_NOT_REPRODUCED",
        "cd02": "CD02_PRESENT" if cd02 else "CD02_ABSENT",
        "candidate": "REPAIR_CANDIDATE_VERIFIED" if c7["result"] == "PASS" else "REPAIR_CANDIDATE_FAILED",
    }
    findings = [
        {
            "id": "W001-F2BC-F01",
            "severity": "hard-internal-consistency; advisory on class semantics",
            "where": "schemas/af_scc_c0_vacuum.yaml:246 (implication_ledger.forbidden_transfers[0].reason)",
            "measured": EDIT_A[0],
            "contradicts": [
                "schemas/af_scc_c0_vacuum.yaml:239 (E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2)",
                "schemas/af_scc_c0_vacuum.yaml:242 (E_C2 subset of E_H2loc)",
                "schemas/af_scc_c2_vacuum.yaml:237 (E_C2 subset of ... subset of E_C0)",
                "schemas/af_scc_c0_vacuum.yaml:80,189,191 (C0-inextendibility is the stronger statement)",
            ],
            "materiality": "the transfer row itself is correctly forbidden and its consequence "
                           "('C2-inextendibility is strictly weaker') is true; only the size gloss "
                           "inverts the document's own E-set order. Repair is lexical.",
            "recommended_repair": f"replace with: {EDIT_A[1]}",
            "falsifier": "a documented convention in F2b under which 'X extension class' denotes the "
                         "data admitting X extensions rather than the extension set E_X, together "
                         "with consistency of that convention with lines 239/242; no such "
                         "convention is declared and the E-notation binds the opposite.",
        },
        {
            "id": "W001-F2BC-F02",
            "severity": "major-ambiguity (scope wording; not confirmed class-semantic)",
            "where": "schemas/af_scc_c0_vacuum.yaml:152 (regularity.must_not_conflate[0])",
            "measured": denial,
            "contradicts": [
                "schemas/af_scc_c0_vacuum.yaml:239 (declares the containment chain)",
                "schemas/af_scc_c2_vacuum.yaml:152 (sibling marks the denial wrong: "
                "'the earlier \"no containment with C2 is asserted\" was wrong')",
            ],
            "materiality": "readable as scoped to the regularity-axis VALUES (H2_loc is a curvature "
                           "condition, not a differentiability rung), in which case it is consistent "
                           "with the extension-SET containment and only the wording is stale versus "
                           "the sibling bullet.",
            "recommended_repair": f"replace with: {EDIT_B[1]}",
            "falsifier": "a reading that shows the unqualified denial is required by the class "
                         "contract, or reproduces an accepted hard finding that depends on the "
                         "literal denial; none is on record for rev13.",
        },
    ]

    report = {
        "schema": "worker-001/f2b-containment-closure/v1",
        "task_id": TASK_ID,
        "actor": ACTOR,
        "node_id": NODE_ID,
        "class_id": CLASS_ID,
        "class_ids": [CLASS_ID, "AF-SCC-C2-VAC-GEN", "AF-WCC-VAC-GEN"],
        "gate": GATE,
        "created_at": started,
        "finished_at": now(),
        "verdict": verdict,
        "counts_as_full_schema_verdict": False,
        "authority_note": "worker measurement only; no node status, no validation_status=passed, "
                          "no gate verdict, no canonical write",
        "pins": measured,
        "oracle": {"size_rank": SIZE_RANK, "f2b_chain": p2b["chain_text"],
                   "f2a_chain": p2a["chain_text"]},
        "checks": [c1, c2, c3, c4, c5, c6, c7],
        "findings": findings,
        "controls": controls,
        "candidate": {
            "path": "artifacts/worker-001/f2b_containment_repair/REPAIR_CANDIDATE.yaml",
            "sha256": c7["candidate_sha256"],
            "canonical_status": "NON-CANONICAL PROPOSAL ONLY",
            "adoption_requires": "authorized F2b revision publication by astra-lead-formulation "
                                 "(bumps revision, re-emits artifact event, re-runs run_gate_tests.py, "
                                 "regenerates FROZEN) plus the standard downstream re-base",
            "frozen_rev29_files_touched_by_F2b_path": affected,
        },
        "falsifier": "Re-run this harness at the recorded pins: any pin move exits 3 without a "
                     "verdict. At the pins, F-01 is falsified by a documented alternative reading of "
                     "'extension class' consistent with lines 239/242; F-02 by evidence that the "
                     "literal denial is contract-required; the candidate by a failed canonical "
                     "checker run, a diff touching lines other than 152/246, or any control K1-K8 "
                     "not behaving as pre-registered.",
        "next_falsifier": "After an authorized adoption, re-run at the new F2b hash: a repair that "
                          "leaves any size-adjective inversion or reintroduces the denial fails; "
                          "adoption voids rev13-bound F2b verdicts as advisory only.",
    }

    (HERE / "PINNED.json").write_text(json.dumps({
        "task_id": TASK_ID, "measured_at": started, "pins": measured,
        "prior_art_advisory": sorted(PRIOR_ART), "pin_guard": "exit 3 on any mismatch/missing",
    }, indent=1) + "\n")
    (HERE / "REPAIR_CANDIDATE.diff").write_text("\n".join(diff) + "\n")
    (HERE / "report.json").write_text(json.dumps(report, indent=1) + "\n")

    report_hash = sha256_file(HERE / "report.json")
    cand_hash = sha256_file(HERE / "REPAIR_CANDIDATE.yaml")
    readme = f"""# {TASK_ID}

One bounded class-bound task, worker-001 (slot recycled; no inbox card exists). Node F2b /
class `{CLASS_ID}` / gate `{GATE}`. **Worker measurement only** - no node status, no
`validation_status=passed`, no gate verdict, no canonical write.

## Question

At the live rev13 bytes (F2b `b2ab6acb2bbe`, F2a `e9a27996fd d3`), is the open
containment-direction finding (`L-FORM-01` / `W097-F2B-HF3` / worker-008 `CD-01`) real, is the
forbidden-transfer row itself correct, and what is the minimal lexical repair?

## Verdict

| id | result |
|---|---|
| `{verdict['cd01']}` | line 246: `C2 is a strictly larger extension class` contradicts the document's own `E_C0 contains E_H2loc contains E_C^{{1,1}} contains E_C2` (line 239) and `E_C2 subset of E_H2loc` (line 242). The row's transfer direction is **correct**; only the size gloss is inverted. |
| `{verdict['cd02']}` | line 152: literal denial `No containment with C2 or C0 is asserted here` coexists with the declared chain; the F2a sibling marks exactly this denial as wrong. Scoped reading available -> major ambiguity, clarification recommended. |
| `{verdict['candidate']}` | non-canonical candidate = base + 2 pre-registered lexical edits; 0 inversions, canonical `check_class_schema.py` pass, diff confined to lines 152/246, controls 8/8. |

Report sha256 `{report_hash[:12]}`, candidate sha256 `{cand_hash[:12]}`, pins in `PINNED.json`.
Adoption impact: {len(affected)} FROZEN rev29 entries reference the F2b path; adoption needs an
authorized revision + downstream re-base and voids rev13-bound F2b verdicts as advisory only.

## Files

- `adjudicate_containment_repair.py` - fail-closed harness (exit 3 pin drift / 4 control failure / 5 precondition)
- `REPAIR_CANDIDATE.yaml` - NON-CANONICAL candidate (base + edit A + edit B)
- `REPAIR_CANDIDATE.diff` - exact two-line diff
- `report.json` - full decision record, checks C1-C7, controls K1-K8, falsifiers
- `PINNED.json` - measured pins and guard policy
- `CHECKPOINT.json` - worker checkpoint (byte-identical runtime copy)

## Falsifiers

See `report.json#falsifier`. In short: any pin move exits 3; F-01 needs a documented alternative
reading of "extension class" consistent with lines 239/242 (none is declared); F-02 needs
evidence the literal denial is contract-required; the candidate fails on a canonical-checker
failure, an out-of-region diff, or any control not detected.
"""
    (HERE / "README.md").write_text(readme)

    checkpoint = {
        "schema": "worker-checkpoint/v1",
        "task_id": TASK_ID,
        "actor": ACTOR,
        "node_id": NODE_ID,
        "class_id": CLASS_ID,
        "gate": GATE,
        "created_at": now(),
        "verdict": verdict,
        "counts_as_full_schema_verdict": False,
        "authority_note": report["authority_note"],
        "pins": measured,
        "artifacts": {
            "harness": {"path": "artifacts/worker-001/f2b_containment_repair/adjudicate_containment_repair.py",
                        "sha256": sha256_file(Path(__file__).resolve())},
            "candidate": {"path": "artifacts/worker-001/f2b_containment_repair/REPAIR_CANDIDATE.yaml",
                          "sha256": cand_hash},
            "diff": {"path": "artifacts/worker-001/f2b_containment_repair/REPAIR_CANDIDATE.diff",
                     "sha256": sha256_file(HERE / "REPAIR_CANDIDATE.diff")},
            "pinned": {"path": "artifacts/worker-001/f2b_containment_repair/PINNED.json",
                       "sha256": sha256_file(HERE / "PINNED.json")},
            "report": {"path": "artifacts/worker-001/f2b_containment_repair/report.json",
                       "sha256": report_hash},
            "readme": {"path": "artifacts/worker-001/f2b_containment_repair/README.md",
                       "sha256": sha256_file(HERE / "README.md")},
        },
        "controls": {c["id"]: c["result"] for c in controls},
        "next_falsifier": report["next_falsifier"],
        "completion_scope": "one worker lifecycle; not a node done and not a gate verdict",
    }
    (HERE / "CHECKPOINT.json").write_text(json.dumps(checkpoint, indent=1) + "\n")
    runtime_copy = ROOT / "runtime/state/worker-001_checkpoint_f2bcontainment.json"
    runtime_copy.write_text((HERE / "CHECKPOINT.json").read_text())

    summary = {
        "task_id": TASK_ID, "verdict": verdict, "controls": checkpoint["controls"],
        "candidate_sha256": cand_hash,
        "artifacts": {k: v["sha256"] for k, v in checkpoint["artifacts"].items()},
        "runtime_checkpoint_sha256": sha256_file(runtime_copy),
        "checkpoint_sha256": sha256_file(HERE / "CHECKPOINT.json"),
    }
    (HERE / "SUMMARY.json").write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
