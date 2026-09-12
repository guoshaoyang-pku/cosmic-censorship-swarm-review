#!/usr/bin/env python3
"""W066-F2B-REPAIR-PREREG-01 -- pre-registered, hash-bound acceptance harness for the
F2b (AF-SCC-C0-VAC-GEN) rev12 containment repair.

Scope: this is a bounded worker lifecycle. It does NOT edit any canonical artifact, does
NOT set a node status or gate verdict, and does NOT re-adjudicate the mathematics of C0.
It measures, on pinned bytes, two text-level defect kinds already adjudicated at
schemas/af_scc_c0_vacuum.yaml#55d0a1ea9bda by worker-066 (W066-R12-F2B-H1/H2):

  H1 size_premise_inverted  -- a `forbidden_transfers` reason asserts a containment/size
                               relation that contradicts the file's own declared
                               extension-class chain.
  H2 false_containment_denial -- a live `must_not_conflate` clause denies containment
                               while the same file asserts it (quoted/withdrawn mentions
                               inside bracketed corrections do not count).

The harness is a fresh re-implementation (plain text + PyYAML structure), independent of
worker-008's `audit_candidate_rev12.py`. It runs against the live rev12 bytes, against the
reference 2-edit candidate 98f9ec83, and against ten pre-registered controls. It writes a
ready-to-apply proposal patch (proposal only; the owner is the only writer of canonical
paths).

Run:  python3 prereg.py            # writes evidence/, report.json, CHECKPOINT.json
Exit: 0 when the pre-registered acceptance verdict was produced (regardless of pass/fail),
      2 when a pin moved or the harness could not run (fail closed).
"""
from __future__ import annotations

import difflib
import hashlib
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))

PINS = {
    "c0_live": {
        "path": "schemas/af_scc_c0_vacuum.yaml",
        "sha256": "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "revision": 12,
    },
    "c2_live": {
        "path": "schemas/af_scc_c2_vacuum.yaml",
        "sha256": "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "revision": 12,
    },
    "f1_live": {
        "path": "schemas/af_wcc_vacuum.yaml",
        "sha256": "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
        "class_id": "AF-WCC-VAC-GEN",
        "revision": 12,
    },
    "candidate_98f9ec83": {
        "path": "artifacts/worker-008/f2b_rev11_dualrepair/candidate_rev12/af_scc_c0_vacuum.yaml",
        "sha256": "98f9ec83c487d6920968f0bdf98e03974813376b6d222b617300525eb13feb1c",
        "class_id": "AF-SCC-C0-VAC-GEN",
    },
}

OWN_TOKEN = {
    "AF-SCC-C0-VAC-GEN": "C0",
    "AF-SCC-C2-VAC-GEN": "C2",
    "AF-WCC-VAC-GEN": None,
}

# H1 reference text (live rev12) and the reference repair semantics.
H1_LIVE = ('- {from: "no proper future C2 extension", to: "this class", reason: '
           '"C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker"}')
H1_FIXED = ('- {from: "no proper future C2 extension", to: "this class", reason: '
            '"C2 is a strictly smaller extension class (E_C2 subset of E_C0), so '
            'C2-inextendibility is strictly weaker"}')
# H2 live sentence fragment and the reference replacement semantics.
H2_LIVE_FRAG = ("No containment with C2 or C0 is asserted here; the informal phrase "
                "'strictly between' is not used and must not be cited (worker-16 F2b-16-02 accepted).")
H2_FIXED_FRAG = ("The extension sets are nonetheless nested: E_C2 subset of E_{C^1,1} "
                 "subset of E_H2loc subset of E_C0 (see implication_ledger), so "
                 "H2_loc-inextendibility ENTAILS this class's conclusion; the informal "
                 "phrase 'strictly between' is not a class definition and must not be cited "
                 "(worker-16 F2b-16-02 accepted). [R2 major: the earlier 'no containment with "
                 "C2 or C0 is asserted here' was wrong]")


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def norm_token(raw: str):
    """Normalise a regularity token from prose/clause text."""
    t = raw.strip().lower()
    t = t.replace("{", "").replace("}", "").replace("^", "").replace("_", "").replace(" ", "")
    t = t.replace("\\", "").replace(",", "")
    if t in ("c0", "c0metric"):
        return "C0"
    if t.startswith("c2"):
        return "C2"
    if t in ("h2loc", "h2locmetric"):
        return "H2LOC"
    if t in ("c11", "c11metric"):
        return "C11"
    return None


def extract_chain(text: str):
    """Return (ranks, evidence) from implication_ledger.extension_class_containment.

    ranks[token] = size rank of the extension SET (larger set -> larger rank).
    """
    m = re.search(r'^implication_ledger:\s*$.*?^  extension_class_containment:\s*"([^"]+)"',
                  text, re.M | re.S)
    if not m:
        m = re.search(r'extension_class_containment:\s*"([^"]+)"', text)
    if not m:
        return None, {"error": "extension_class_containment not found"}
    clause = m.group(1)
    toks = re.findall(r'E_\{?([A-Za-z0-9^,]+)\}?', clause)
    toks = [norm_token(t) for t in toks]
    if len(toks) < 2 or any(t is None for t in toks):
        return None, {"error": f"chain tokens unparsed: {toks}", "clause": clause}
    has_contains = " contains " in clause
    has_subset = " subset of " in clause
    if has_contains and not has_subset:
        order = toks  # descending by set size
        ranks = {t: len(order) - 1 - i for i, t in enumerate(order)}
        kind = "contains-chain (descending)"
    elif has_subset and not has_contains:
        order = toks  # ascending by set size
        ranks = {t: i for i, t in enumerate(order)}
        kind = "subset-chain (ascending)"
    else:
        return None, {"error": "ambiguous chain connectives", "clause": clause}
    if len(set(order)) != len(order):
        return None, {"error": f"duplicate tokens in chain: {order}", "clause": clause}
    return ranks, {"clause": clause, "tokens": toks, "order": order,
                   "kind": kind, "ranks": ranks}


def strip_withdrawn(line: str) -> str:
    """Remove bracketed corrections and quoted fragments explicitly marked wrong."""
    s = re.sub(r'\[[^\]]*\]', ' ', line)
    s = re.sub(r"'[^']*'\s*(?:was|is)\s+wrong", ' ', s)
    s = re.sub(r'"[^"]*"\s*(?:was|is)\s+wrong', ' ', s)
    return s


def line_of(text: str, needle: str) -> int:
    idx = text.find(needle)
    return text[:idx].count("\n") + 1 if idx >= 0 else -1


def audit(text: str, class_id: str, label: str, chain_required: bool = True) -> dict:
    """Run the defect-kind checker. Returns findings + raw observations.

    chain_required=False is for classes with no extension-class chain (F1/WCC): the
    absence of a chain is not a defect there, only the denial sweep runs.
    """
    findings = []
    obs = {}
    own = OWN_TOKEN.get(class_id)
    data = yaml.safe_load(text)
    obs["class_id_measured"] = data.get("class_id")
    obs["revision_measured"] = data.get("revision")
    if obs["class_id_measured"] != class_id:
        findings.append({"kind": "class_binding_mismatch", "line": 1,
                         "detail": f"class_id in file {obs['class_id_measured']} != {class_id}"})

    ranks, chain_info = extract_chain(text)
    obs["chain"] = chain_info
    if ranks is None and chain_required:
        findings.append({"kind": "chain_missing", "line": -1,
                         "detail": chain_info.get("error", "chain unparsed")})
        obs["size_premises"] = []
        obs["denials"] = []
        obs["rows"] = []
        return {"label": label, "findings": sorted(findings, key=lambda f: (f["kind"], f["line"])),
                "observations": obs}
    if ranks is None:
        ranks = {}

    # ---- row-level audit: implication_ledger -------------------------------------
    ledger = (data.get("implication_ledger") or {})
    rows_out = []

    def row_token(raw: str):
        if (raw or "").strip().lower() == "this class":
            return own, "this class"
        m = re.search(r'no proper future (.+?) extension', raw or "")
        if not m:
            return "OTHER", raw
        t = m.group(1)
        tok = norm_token(t)
        if tok is None and "distributional" in t.lower():
            return "DIST_C0", t
        return tok, t

    for kind_key, expect_licensed in (("one_way_entailments", True),
                                      ("forbidden_transfers", False)):
        for i, row in enumerate(ledger.get(kind_key) or []):
            if not isinstance(row, dict):
                continue
            f_raw, t_raw = str(row.get("from", "")), str(row.get("to", ""))
            f_tok, f_disp = row_token(f_raw)
            t_tok, t_disp = row_token(t_raw)
            rec = {"list": kind_key, "index": i, "from": f_raw, "to": t_raw,
                   "from_token": f_tok, "to_token": t_tok,
                   "line": line_of(text, f_raw) if f_raw else -1,
                   "reason": row.get("reason", "")}
            if f_tok == "OTHER" or t_tok == "OTHER":
                rec["licensing"] = "not_a_containment_row"
                rec["verdict"] = "skipped"
                rows_out.append(rec)
                continue
            if t_tok == "DIST_C0":
                licensed = f_tok in ("C0", "DIST_C0")
                rec["licensing"] = "distributional extensions are a subset of continuous ones"
            elif t_tok in ranks and f_tok in ranks:
                licensed = ranks[t_tok] <= ranks[f_tok]
                rec["licensing"] = (f"E_{t_tok} {'subset of' if licensed else 'NOT subset of'} "
                                    f"E_{f_tok} by declared chain ranks "
                                    f"(rank {ranks[t_tok]} vs {ranks[f_tok]})")
            else:
                rec["licensing"] = f"token(s) absent from chain: from={f_tok} to={t_tok}"
                rec["verdict"] = "skipped"
                rows_out.append(rec)
                continue
            rec["licensed"] = licensed
            if expect_licensed and not licensed:
                rec["verdict"] = "INVALID_ENTAILMENT"
                findings.append({"kind": "invalid_entailment", "line": rec["line"],
                                 "detail": f"{kind_key}[{i}] claims entails but {rec['licensing']}"})
            elif (not expect_licensed) and licensed:
                rec["verdict"] = "INVALID_FORBIDDEN"
                findings.append({"kind": "invalid_forbidden_transfer", "line": rec["line"],
                                 "detail": f"{kind_key}[{i}] forbids a licensed transfer: {rec['licensing']}"})
            else:
                rec["verdict"] = "ok"
            # H1: explicit size comparative in the reason, checked against the chain.
            subj, rel = None, None
            m = re.search(r'([A-Za-z0-9_^{},\s]+?)\s+is a strictly (larger|smaller) extension class',
                          rec["reason"])
            if m:
                subj = norm_token(m.group(1))
                rel = m.group(2)
                other = t_tok if subj == f_tok else f_tok
                rec["size_premise"] = {"subject": subj, "claim": rel, "counterpart": other}
                if subj is None or other not in ranks or subj not in ranks:
                    findings.append({"kind": "size_premise_unverifiable", "line": rec["line"],
                                     "detail": f"{kind_key}[{i}] size comparative {m.group(0)!r} "
                                               f"not resolvable against the chain"})
                else:
                    claimed_larger = (rel == "larger")
                    measured_larger = ranks[subj] > ranks[other]
                    if claimed_larger != measured_larger:
                        rec["size_premise"]["verdict"] = "INVERTED"
                        findings.append({"kind": "size_premise_inverted", "line": rec["line"],
                                         "detail": (f"{kind_key}[{i}] reason says {subj} is strictly "
                                                    f"{rel} than {other}, but declared ranks are "
                                                    f"{subj}={ranks[subj]}, {other}={ranks[other]}")})
                    else:
                        rec["size_premise"]["verdict"] = "ok"
            rows_out.append(rec)
    obs["rows"] = rows_out

    # ---- generic size-comparative sweep (whole file) ------------------------------
    prem = []
    for ln, line in enumerate(text.splitlines(), 1):
        for m in re.finditer(r'([A-Za-z0-9_^{},\s]+?)\s+is a strictly (larger|smaller) extension class',
                             line):
            subj = norm_token(m.group(1))
            prem.append({"line": ln, "subject": subj, "claim": m.group(2),
                         "resolved": subj in ranks,
                         "rank": ranks.get(subj),
                         "text": m.group(0).strip()})
    obs["size_premises"] = prem

    # ---- denial sweep -------------------------------------------------------------
    denials = []
    asserts_containment = bool(ledger.get("one_way_entailments")) or bool(ranks)
    for ln, line in enumerate(text.splitlines(), 1):
        live_part = strip_withdrawn(line)
        if re.search(r'\bno\s+containment\b', live_part, re.I):
            withdrawn = live_part.strip() != line.strip()
            rec = {"line": ln, "live": True, "withdrawn_quoted_copy": withdrawn,
                   "excerpt": line.strip()[:220]}
            denials.append(rec)
            if asserts_containment:
                findings.append({"kind": "false_containment_denial", "line": ln,
                                 "detail": ("live clause denies containment while the same file "
                                            "declares an extension-class chain")})
    obs["denials"] = denials

    findings = sorted(findings, key=lambda f: (f["kind"], f["line"]))
    return {"label": label, "findings": findings, "observations": obs}


def kinds(res: dict):
    return sorted({f["kind"] for f in res["findings"]})


def apply_edits(text: str, edits):
    out = text
    for old, new in edits:
        if old not in out:
            raise SystemExit(f"edit anchor not found: {old[:70]!r}")
        out = out.replace(old, new, 1)
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "pinned").mkdir(exist_ok=True)
    (OUT / "evidence").mkdir(exist_ok=True)

    measures = {}
    texts = {}
    for key, pin in PINS.items():
        p = ROOT / pin["path"]
        raw = p.read_bytes()
        text = raw.decode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
        measures[key] = {"path": pin["path"], "expected_sha256": pin["sha256"],
                         "measured_sha256": digest, "match": digest == pin["sha256"],
                         "bytes": len(raw), "mtime": datetime.fromtimestamp(
                             p.stat().st_mtime, CST).isoformat(timespec="seconds")}
        texts[key] = text
        dst = OUT / "pinned" / f"{key}__{Path(pin['path']).name}"
        dst.write_bytes(raw)
    drift = [k for k, v in measures.items() if not v["match"]]
    (OUT / "evidence" / "pins.json").write_text(json.dumps(measures, indent=2) + "\n")

    if drift:
        report = {"task_id": "W066-F2B-REPAIR-PREREG-01", "verdict": "blocked_pin_drift",
                  "drift": drift, "measures": measures, "generated_at": now()}
        (OUT / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
        return 2

    # ---------- primary checks -------------------------------------------------
    live = audit(texts["c0_live"], PINS["c0_live"]["class_id"], "c0_live_rev12")
    cand = audit(texts["candidate_98f9ec83"], PINS["candidate_98f9ec83"]["class_id"],
                 "candidate_98f9ec83")
    c2 = audit(texts["c2_live"], PINS["c2_live"]["class_id"], "c2_live_rev12")
    f1 = audit(texts["f1_live"], PINS["f1_live"]["class_id"], "f1_live_rev12", chain_required=False)
    sib = {"c2_live": c2, "f1_live": f1}

    # ---------- proposal patch (candidate is the reference repair) -------------
    live_text, cand_text = texts["c0_live"], texts["candidate_98f9ec83"]
    diff = "".join(difflib.unified_diff(
        live_text.splitlines(keepends=True), cand_text.splitlines(keepends=True),
        fromfile=f"a/{PINS['c0_live']['path']}", tofile=f"b/{PINS['c0_live']['path']}"))
    (OUT / "proposed_patch.diff").write_text(diff)
    h1_live_ok = H1_LIVE in live_text
    h2_live_ok = H2_LIVE_FRAG in live_text
    h1_fix_ok = H1_FIXED in cand_text
    h2_fix_ok = H2_FIXED_FRAG in cand_text
    reapply = apply_edits(live_text, [(H1_LIVE, H1_FIXED), (H2_LIVE_FRAG, H2_FIXED_FRAG)])
    reapply_hash = sha256_text(reapply)
    proposal = {
        "base": {"path": PINS["c0_live"]["path"], "sha256": PINS["c0_live"]["sha256"]},
        "reference_candidate": {"path": PINS["candidate_98f9ec83"]["path"],
                                "sha256": PINS["candidate_98f9ec83"]["sha256"]},
        "edits": [
            {"leaf_path": "implication_ledger.forbidden_transfers[0].reason",
             "live_semantics": "C2 is a strictly larger extension class ...",
             "proposed_semantics": "C2 is a strictly smaller extension class (E_C2 subset of E_C0) ..."},
            {"leaf_path": "regularity.must_not_conflate[0]",
             "live_semantics": "live denial of C2/C0 containment",
             "proposed_semantics": "declare the nesting chain and the H2_loc entailment; "
                                   "record the earlier denial as wrong"},
        ],
        "anchors_present_on_live": {"H1": h1_live_ok, "H2": h2_live_ok},
        "anchors_present_on_candidate": {"H1_fix": h1_fix_ok, "H2_fix": h2_fix_ok},
        "reapply_to_live_reproduces_candidate_sha256": reapply_hash,
        "reapply_matches_reference_candidate": reapply_hash == PINS["candidate_98f9ec83"]["sha256"],
        "note": ("PROPOSAL ONLY. Canonical writes belong to lead-formulation (owner). "
                 "The owner may apply an equivalent repair; this harness then re-runs."),
    }

    # ---------- pre-registered controls ---------------------------------------
    controls = []

    def add_control(cid, description, result, expected_kinds, extra=None):
        got = kinds(result)
        controls.append({"id": cid, "description": description, "expected_kinds": expected_kinds,
                         "observed_kinds": got, "observed_findings": result["findings"],
                         "matched": got == sorted(expected_kinds), "extra": extra or {}})

    add_control("C1_pristine_live", "live rev12 55d0a1ea must yield exactly both defects",
                live, ["false_containment_denial", "size_premise_inverted"])
    add_control("C2_reference_candidate", "reference 2-edit candidate 98f9ec83 must be clean",
                cand, [])
    c3 = audit(apply_edits(cand_text, [(H1_FIXED, H1_LIVE)]), PINS["c0_live"]["class_id"],
               "ctl03_revert_H1_only")
    add_control("C3_revert_H1_only", "candidate with the repaired H1 reason reverted",
                c3, ["size_premise_inverted"])
    c4 = audit(apply_edits(cand_text, [(H2_FIXED_FRAG, H2_LIVE_FRAG)]), PINS["c0_live"]["class_id"],
               "ctl04_revert_H2_only")
    add_control("C4_revert_H2_only", "candidate with the repaired H2 clause reverted",
                c4, ["false_containment_denial"])
    c5 = audit(apply_edits(cand_text, [(H1_FIXED, H1_LIVE.replace(
        "strictly weaker", "strictly stronger"))]), PINS["c0_live"]["class_id"],
        "ctl05_inverted_other_way")
    add_control("C5_inverted_other_way", "candidate with a still-inverted H1 premise (opposite claim)",
                c5, ["size_premise_inverted"])
    c6_text = apply_edits(cand_text, [(H2_FIXED_FRAG, H2_LIVE_FRAG + " (unbracketed)")])
    c6 = audit(c6_text, PINS["c0_live"]["class_id"], "ctl06_denial_reinserted_live")
    add_control("C6_denial_reinserted", "candidate with the denial re-inserted as a live sentence",
                c6, ["false_containment_denial"])
    c7 = audit(cand_text.replace(
        "E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2",
        "E_C2 contains E_{C^1,1} contains E_H2loc contains E_C0"), PINS["c0_live"]["class_id"],
        "ctl07_reversed_chain")
    add_control("C7_reversed_chain", "candidate with the declared chain direction reversed",
                c7, ["invalid_entailment", "invalid_forbidden_transfer", "size_premise_inverted"])
    add_control("C8_sibling_c2_clean", "C2 rev12 at 5476a3f2 must carry neither defect kind",
                c2, [])
    add_control("C9_sibling_f1_clean", "F1 rev12 at cce9c601 must carry neither defect kind",
                f1, [])
    c10 = audit("schema_version: '1.0'\nclass_id: AF-SCC-C0-VAC-GEN\nrevision: 12\n",
                PINS["c0_live"]["class_id"], "ctl10_gutted_file")
    add_control("C10_gutted_file", "file without the chain must fail closed (non-vacuous checker)",
                c10, ["chain_missing"])

    controls_ok = all(c["matched"] for c in controls)
    live_kinds = kinds(live)
    acceptance = {
        "live_rev12_fails_with_H1_H2": live_kinds == ["false_containment_denial", "size_premise_inverted"],
        "reference_candidate_clean": kinds(cand) == [],
        "sibling_c2_clean": kinds(c2) == [],
        "sibling_f1_clean": kinds(f1) == [],
        "controls_all_matched": controls_ok,
        "three_findings_kinds_absent_from_siblings": all(
            k not in ("size_premise_inverted", "false_containment_denial") for k in kinds(c2) + kinds(f1)),
    }
    verdict = "prereg_ready_live_FAILS_candidate_PASSES" if all(acceptance.values()) \
        else "prereg_INCOMPLETE_or_inconclusive"

    # ---------- evidence files -------------------------------------------------
    checks = {
        "task_id": "W066-F2B-REPAIR-PREREG-01",
        "generated_at": now(),
        "checker": "prereg.py (fresh text+YAML re-implementation)",
        "primary": {"c0_live_rev12": live, "candidate_98f9ec83": cand},
        "siblings": sib,
        "acceptance": acceptance,
        "verdict": verdict,
        "coverage_note": ("H1/H2 definitions are re-implemented from the declared-chain semantics; "
                          "worker-008's checker is used only as an external cross-check, not as "
                          "the instrument."),
    }
    (OUT / "evidence" / "checks.json").write_text(json.dumps(checks, indent=2) + "\n")
    (OUT / "evidence" / "controls.json").write_text(json.dumps(
        {"controls": controls, "all_matched": controls_ok}, indent=2) + "\n")
    (OUT / "evidence" / "sibling_scan.json").write_text(json.dumps(
        {"c2_live": {"sha256": PINS["c2_live"]["sha256"], "findings": c2["findings"],
                     "size_premises": c2["observations"]["size_premises"],
                     "denials": c2["observations"]["denials"]},
         "f1_live": {"sha256": PINS["f1_live"]["sha256"], "findings": f1["findings"],
                     "size_premises": f1["observations"]["size_premises"],
                     "denials": f1["observations"]["denials"]}}, indent=2) + "\n")
    (OUT / "evidence" / "frozen_binding.json").write_text(json.dumps(
        {"frozen_manifest": "artifacts/formulation/FROZEN.json",
         "note": "measured live hashes are compared to the workflow pins; the FROZEN manifest "
                 "is owned by lead-formulation and is not edited here."}, indent=2) + "\n")

    # ---------- report ----------------------------------------------------------
    report = {
        "task_id": "W066-F2B-REPAIR-PREREG-01",
        "actor": "worker-066",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "generated_at": now(),
        "verdict": verdict,
        "live_target": {"path": PINS["c0_live"]["path"], "sha256": PINS["c0_live"]["sha256"],
                        "revision": PINS["c0_live"]["revision"],
                        "finding_kinds": live_kinds,
                        "hard_failures": ["W066-R12-F2B-H1", "W066-R12-F2B-H2"]},
        "reference_candidate": {"path": PINS["candidate_98f9ec83"]["path"],
                                "sha256": PINS["candidate_98f9ec83"]["sha256"],
                                "finding_kinds": kinds(cand),
                                "minimality": "two leaf-path edits; re-applied to live reproduces "
                                              "the candidate hash"},
        "siblings": {"c2": {"sha256": PINS["c2_live"]["sha256"], "finding_kinds": kinds(c2)},
                     "f1": {"sha256": PINS["f1_live"]["sha256"], "finding_kinds": kinds(f1)}},
        "controls": {"count": len(controls), "all_matched": controls_ok,
                     "mismatches": [c["id"] for c in controls if not c["matched"]]},
        "acceptance": acceptance,
        "proposal": proposal,
        "definition_of_done": ("owner applies the proposed patch or an equivalent 2-edit repair, "
                               "bumps revision, publishes, re-freezes; then re-run prereg.py: "
                               "acceptance requires live PASS (zero findings), siblings clean, "
                               "all controls matched."),
        "not_claimed": ["no canonical artifact was written by worker-066",
                        "no gate/node status was moved",
                        "no claim about the mathematics of C0/C2 inextendibility"],
        "falsifier": ("re-run prereg.py on the same pins: this report is falsified if live "
                      "55d0a1ea does not yield exactly the two defect kinds, or the reference "
                      "candidate 98f9ec83 produces any finding, or any control departs from its "
                      "pre-registered expectation, or a third instance of the two defect kinds "
                      "appears in C2/F1 at their pins, or re-applying the two edits to live does "
                      "not reproduce 98f9ec83, or any pinned byte moves mid-run."),
    }
    (OUT / "report.json").write_text(json.dumps(report, indent=2) + "\n")

    checkpoint = {
        "task_id": "W066-F2B-REPAIR-PREREG-01",
        "label": "worker-066-f2b-repair-prereg",
        "generated_at": now(),
        "pins": measures,
        "verdict": verdict,
        "live_finding_kinds": live_kinds,
        "candidate_finding_kinds": kinds(cand),
        "sibling_finding_kinds": {"c2": kinds(c2), "f1": kinds(f1)},
        "controls_all_matched": controls_ok,
        "artifacts": {
            "prereg.py": sha256_file(Path(__file__)),
            "proposed_patch.diff": sha256_file(OUT / "proposed_patch.diff"),
            "README.md": sha256_file(OUT / "README.md") if (OUT / "README.md").exists() else None,
            "evidence/checks.json": sha256_file(OUT / "evidence" / "checks.json"),
            "evidence/controls.json": sha256_file(OUT / "evidence" / "controls.json"),
            "evidence/sibling_scan.json": sha256_file(OUT / "evidence" / "sibling_scan.json"),
            "evidence/pins.json": sha256_file(OUT / "evidence" / "pins.json"),
            "report.json": sha256_file(OUT / "report.json"),
        },
        "next_falsifier": report["falsifier"],
    }
    (OUT / "CHECKPOINT.json").write_text(json.dumps(checkpoint, indent=2) + "\n")

    print(json.dumps({"verdict": verdict, "live": live_kinds, "candidate": kinds(cand),
                      "siblings": {"c2": kinds(c2), "f1": kinds(f1)},
                      "controls_all_matched": controls_ok,
                      "controls": {c["id"]: c["matched"] for c in controls},
                      "proposal_reproduces_candidate": proposal["reapply_matches_reference_candidate"]},
                     indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
