#!/usr/bin/env python3
"""W003-C0-REV12-CONTRACT-CONSISTENCY-01  (worker-003, bounded read-only probe)

Independent, hash-pinned adjudication of the three CONTESTED order/containment
defects in the frozen AF-SCC-C0-VAC-GEN class schema
(schemas/af_scc_c0_vacuum.yaml, sha256 55d0a1ea...), cross-checked against the
sibling AF-SCC-C2-VAC-GEN schema (5476a3f2...) -- the same author's own
adjudication precedent -- and against five independent detector/review reports.

The dispute being adjudicated
-----------------------------
  worker-008 (FORM-SEP-04 X3c + fail-closed dual-defect checker) reports TWO
    defects: C0:151 false containment denial, C0:245 inverted size premise.
  worker-058 (order/strength sweep + rev12 delta cert) reports TWO defects:
    C0:245 inverted size premise, C0:234 strengthening/weakening bucket mislabel.
  worker-096 (independent F2b review) reports only C0:245 plus a binding-hash
    defect; it does not flag 151 or 234.
The three reports therefore disagree on the C0 defect set.  This probe decides
each contested line with decidable text operations only.

Findings (see report.json for verdicts):
  F1  C0:245  "C2 is a strictly larger extension class" contradicts the file's
              own declared chain (extension_class_containment, C0:238) and the
              file's own weaker/stronger rule (C0:224).  The sentence's
              CONSEQUENCE ("C2-inextendibility is strictly weaker") is correct,
              so the defect is a premise-only token inversion.
  F2  C0:234  "replacing future by two-sided direction" sits in
              forbidden_weakenings while C0:225 puts the same substitution in
              forbidden_strengthenings as a "stronger statement"; C2:232 records
              that the earlier revision "mislabelled it here as a weakening".
  F3  C0:151  a LIVE containment denial ("No containment with C2 or C0 is
              asserted here") coexists with the chain declared at C0:238; C2:151
              records that this exact phrasing "was wrong" [R2 major] and
              replaced it with the nesting statement. C0 never received the
              replacement. Scope caveat: "here" admits an entry-local reading,
              which is reported, not hidden.
  F4          of five C2 [R2]-adjudicated superseded phrasings, exactly two did
              not propagate into C0 (P1 -> F3, P2 -> F2); three did propagate
              (P3 chain, P4 entailment placement, P5 dense_escape label).

Method: stdlib only; every input is pinned by sha256 and re-measured at the end
(drift => exit 3, fail-closed, no verdict).  Controls: 2 sensitivity rewrites,
3 propagation controls, specificity scan on the sibling, cross-detector matrix.

Exit codes: 0 = every declared expectation matched; 2 = expectation mismatch;
3 = input hash drift (void run).

Authority: worker evidence only.  No gate verdict, no node transition, no
validation_status promotion.  Interpretation of repairs is owned by
astra-lead-formulation; gate adjudication by astra-lead-audit / astra.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


PINS = {
    "schemas/af_scc_c0_vacuum.yaml":
        "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
    "schemas/af_scc_c2_vacuum.yaml":
        "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
    "artifacts/formulation/FROZEN.json":
        "2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1",
    "artifacts/worker08/rev28_live/f2b_dual_defect_rev28_live.json":
        "e36a7caba557dffc8c41a053ca77b422ff0745bcf8e711a98069f1d0f2709727",
    "artifacts/worker08/rev28_live/form_sep_04_rev28_bundle.json":
        "eb9e91664bd6dc2a68ebe6a52f7677733ebe67146e7f23364dcfa105bfb88915",
    "artifacts/worker-058/rev27_cert/rev12_delta_cert.json":
        "a47f68bfd99ddafd050e84d48480baae028e620c3c63e6ba1911ee7456c6751b",
    "artifacts/worker-058/rev27_cert/sweep_rev27.json":
        "db27bfe64e81f9e7a53777692d29aa8cd4bdf6550b401461743f9eba757ce9ee",
    "artifacts/worker-096/f2b_rev12_gate_review/report.json":
        "f48102b3036abf91de313b3dcb35234d1e4862aca34348b16dee4596ddcec89c",
}

# ---------------------------------------------------------------------------
# text helpers (no YAML dependency; line numbers are part of the evidence)
# ---------------------------------------------------------------------------
KEY_RE = re.compile(r"^(\s*)([A-Za-z_][A-Za-z0-9_]*):")
TOK_RE = re.compile(r"E_(?:\{C\^1,1\}|C\^1,1|C0|C2|H2loc)")
TOK_MAP = {"E_C0": "C0", "E_C2": "C2", "E_H2loc": "H2LOC",
           "E_{C^1,1}": "C11", "E_C^1,1": "C11"}
EXPECTED_CHAIN = ["C0", "H2LOC", "C11", "C2"]  # descending extension-set size


def indent_of(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def section_of(lines: list[str], idx: int) -> str | None:
    """Nearest enclosing top-level key for the list item at 0-based idx."""
    ind = indent_of(lines[idx])
    for j in range(idx - 1, -1, -1):
        s = lines[j]
        if not s.strip() or s.lstrip().startswith("#"):
            continue
        m = KEY_RE.match(s)
        if m and len(m.group(1)) < ind:
            return m.group(2)
    return None


def live(line: str) -> str:
    """Drop [revision notes] and 'quoted prior text' before scanning live prose."""
    s = re.sub(r"\[[^\]]*\]", " ", line)
    s = re.sub(r"'[^']*'", " ", s)
    return s


def key_line(text: str, key: str) -> tuple[int, str] | None:
    for i, l in enumerate(text.splitlines()):
        m = KEY_RE.match(l)
        if m and m.group(2) == key:
            return i + 1, l
    return None


def parse_chain(text: str) -> list[str] | None:
    """Parse extension_class_containment into descending-size class tokens."""
    hit = key_line(text, "extension_class_containment")
    if not hit:
        return None
    line = hit[1]
    toks = [TOK_MAP[t] for t in TOK_RE.findall(line)]
    if len(toks) < 4:
        return None
    if " subset of " in line:
        return list(reversed(toks))
    if " contains " in line:
        return toks
    return None


# ---------------------------------------------------------------------------
# checks
# ---------------------------------------------------------------------------
def check_size_premise(text: str, file_class: str) -> list[dict]:
    """F1: 'X is a strictly larger/smaller extension class' vs the file chain."""
    chain = parse_chain(text) or []
    rank = {t: i for i, t in enumerate(chain)}  # 0 = largest extension set
    out = []
    lines = text.splitlines()
    for i, l in enumerate(lines):
        if section_of(lines, i) != "forbidden_transfers":
            continue
        reason_m = re.search(r"reason:\s*\"([^\"]*)\"", l)
        from_m = re.search(r"from:\s*\"([^\"]*)\"", l)
        if not reason_m:
            continue
        reason = reason_m.group(1)
        m = re.search(r"\b(C0|C2|H2_loc|C\^1,1|C1)\b\s+is a strictly (larger|smaller) extension class",
                      reason)
        if not m:
            continue
        subj = {"H2_loc": "H2LOC", "C^1,1": "C11", "C1": "C11"}.get(m.group(1), m.group(1))
        if subj not in rank or file_class not in rank:
            continue
        claims_larger = m.group(2) == "larger"
        consistent = (rank[subj] < rank[file_class]) if claims_larger else (rank[subj] > rank[file_class])
        if not consistent:
            out.append({
                "line": i + 1,
                "section": "implication_ledger.forbidden_transfers",
                "subject": subj,
                "file_class": file_class,
                "claim": m.group(0),
                "declared_ranks": {"largest_extension_set": chain[0], "rank": rank},
                "from": from_m.group(1) if from_m else None,
            })
    return out


def check_denial(text: str) -> list[dict]:
    """F3: LIVE 'no containment with ...' inside must_not_conflate."""
    out = []
    lines = text.splitlines()
    for i, l in enumerate(lines):
        if section_of(lines, i) != "must_not_conflate":
            continue
        lt = live(l)
        if re.search(r"no containment with", lt, re.I):
            out.append({"line": i + 1, "text": l.strip(),
                        "denied_tokens": sorted(set(re.findall(r"C2|C0|H2_loc|H2loc", lt)))})
    return out


def check_buckets(text: str) -> tuple[dict, list[dict]]:
    """F2: same direction token in forbidden_strengthenings AND -weakenings."""
    buckets: dict[str, list[dict]] = {
        "forbidden_strengthenings": [], "forbidden_strengthenings_addition": [],
        "forbidden_weakenings": [],
    }
    lines = text.splitlines()
    for i, l in enumerate(lines):
        s = section_of(lines, i)
        if s in buckets and l.strip().startswith("-"):
            buckets[s].append({"line": i + 1, "text": l.strip()})
    pat = {
        "two-sided": r"two-sided|two sided|TWOSIDED",
    }
    collisions = []
    strong = buckets["forbidden_strengthenings"] + buckets["forbidden_strengthenings_addition"]
    weak = buckets["forbidden_weakenings"]
    for key, rx in pat.items():
        in_s = [b for b in strong if re.search(rx, b["text"], re.I)]
        in_w = [b for b in weak if re.search(rx, b["text"], re.I)]
        if in_s and in_w:
            collisions.append({"token": key,
                               "strengthening_lines": [b["line"] for b in in_s],
                               "weakening_lines": [b["line"] for b in in_w]})
    return buckets, collisions


def forbidden_transfer_rows(text: str) -> list[dict]:
    rows = []
    lines = text.splitlines()
    for i, l in enumerate(lines):
        if section_of(lines, i) != "forbidden_transfers":
            continue
        fm = re.search(r"from:\s*\"([^\"]*)\"", l)
        tm = re.search(r"to:\s*\"([^\"]*)\"", l)
        if fm:
            rows.append({"line": i + 1, "from": fm.group(1),
                         "to": tm.group(1) if tm else None, "text": l.strip()})
    return rows


def check_propagation(c0: str, c2: str) -> tuple[list[dict], dict]:
    """F4: which C2 [R2]-adjudicated superseded phrasings remain in C0?"""
    c0_lines = c0.splitlines()
    c2_lines = c2.splitlines()
    c0_chain = parse_chain(c0)
    _, c0_col = check_buckets(c0)
    c0_denials = check_denial(c0)
    c0_rows = forbidden_transfer_rows(c0)
    c2_live_151 = live(c2_lines[150])

    residuals = {
        "c0_live_denial": len(c0_denials) > 0,
        "c0_two_sided_in_weakenings": any(
            c["token"] == "two-sided" for c in c0_col),
        "c0_chain_order_wrong": c0_chain != EXPECTED_CHAIN,
        "c0_h2loc_to_c2_forbidden": any(
            "H2_loc" in r["from"] and "C2" in (r["to"] or "") for r in c0_rows),
        "c0_dense_escape_mislabelled_incomparable": any(
            "dense_escape" in l and "incomparable" in live(l) and "strictly_weaker" not in l
            for l in c0_lines),
    }
    comparators = [
        {"id": "P1", "c2_line": 151,
         "superseded": "no containment with C2 is asserted",
         "c2_note_ok": ("was wrong" in c2_lines[150]
                        and "no containment with C2 is asserted" in c2_lines[150]
                        and "nested" in c2_lines[150]),
         "residual_key": "c0_live_denial", "maps_to": "F3"},
        {"id": "P2", "c2_line": 232,
         "superseded": "mislabelled it here as a weakening",
         "c2_note_ok": ("mislabelled it here as a weakening" in c2_lines[231]
                        and "STRONGER" in c2_lines[231]),
         "residual_key": "c0_two_sided_in_weakenings", "maps_to": "F2"},
        {"id": "P3", "c2_line": 236,
         "superseded": "the earlier revision had the H2_loc ordering wrong",
         "c2_note_ok": "the earlier revision had the H2_loc ordering wrong" in c2_lines[235],
         "residual_key": "c0_chain_order_wrong", "maps_to": "chain"},
        {"id": "P4", "c2_line": 240,
         "superseded": "this entailment was wrongly listed as forbidden",
         "c2_note_ok": "this entailment was wrongly listed as forbidden" in c2_lines[239],
         "residual_key": "c0_h2loc_to_c2_forbidden", "maps_to": "entailment placement"},
        {"id": "P5", "c2_line": 174,
         "superseded": "was off-vocabulary and mislabelled incomparable",
         "c2_note_ok": "was off-vocabulary and mislabelled incomparable" in c2_lines[173],
         "residual_key": "c0_dense_escape_mislabelled_incomparable", "maps_to": "dense_escape label"},
    ]
    for c in comparators:
        c["c0_residual"] = residuals[c["residual_key"]]
        c["status"] = "residual-in-C0" if c["c0_residual"] else "propagated"
    # the C2 sibling's live must_not_conflate entry must be clean (specificity)
    assert_specificity = {
        "c2_live_denial_free": not re.search(r"no containment with", c2_live_151, re.I),
        "c2_has_nesting_statement": "extension sets are nested" in c2_live_151,
    }
    return comparators, {"residuals": residuals, "specificity": assert_specificity}


def xref() -> dict:
    r = ROOT
    d = json.loads((r / "artifacts/worker08/rev28_live/f2b_dual_defect_rev28_live.json").read_text())
    w008_dual = sorted({(int(f["line"]), f["kind"]) for f in d["findings"]})
    b = json.loads((r / "artifacts/worker08/rev28_live/form_sep_04_rev28_bundle.json").read_text())
    hits = [h for hf in b["form_sep_04"]["hard_failures"] for h in hf.get("hits", [])]
    w008_sep = sorted({(h.get("classification"), h.get("path")) for h in hits})
    s = json.loads((r / "artifacts/worker-058/rev27_cert/sweep_rev27.json").read_text())
    w058_sweep = sorted({int(f["line"]) for f in s["hard_findings"]})
    q = json.loads((r / "artifacts/worker-058/rev27_cert/rev12_delta_cert.json").read_text())
    w058_delta = sorted({int(f["line"]) for f in q["hard_findings"]})
    w = json.loads((r / "artifacts/worker-096/f2b_rev12_gate_review/report.json").read_text())
    w096_lines: set[int] = set()
    for f in w["findings"]:
        if f.get("severity") == "hard" or f.get("id") in w["hard_failures"]:
            blob = f"{f.get('evidence', '')} {f.get('statement', '')}"
            for grp in re.findall(r"lines?\s+([\d,\s]+)", blob):
                w096_lines.update(int(x) for x in re.findall(r"\d+", grp))
    matrix: dict[int, list[str]] = {}
    for line in (151, 234, 245):
        src = []
        if any(l == line for l, _ in w008_dual):
            src.append("w008_dual_defect")
        if line == 245 and w008_sep:
            src.append("w008_form_sep_04_X3c")
        if line in w058_sweep:
            src.append("w058_sweep_rev27")
        if line in w058_delta:
            src.append("w058_rev12_delta")
        if line in w096_lines:
            src.append("w096_f2b_review")
        matrix[line] = src
    return {
        "w008_dual_defect_findings": [list(x) for x in w008_dual],
        "w008_form_sep_04_hits": [list(x) for x in w008_sep],
        "w058_sweep_hard_lines": w058_sweep,
        "w058_rev12_delta_hard_lines": w058_delta,
        "w096_review_hard_lines": sorted(w096_lines),
        "per_line_sources": {str(k): v for k, v in matrix.items()},
    }


def sensitivity(c0: str, c2: str) -> dict:
    """Repaired C0 must go clean; an inverted C2 chain must trip the control."""
    repaired = c0.replace("C2 is a strictly larger extension class",
                          "C2 is a strictly smaller extension class")
    repaired = "\n".join(l for l in repaired.splitlines()
                         if "replacing future by two-sided direction" not in l)
    repaired = repaired.replace(
        "No containment with C2 or C0 is asserted here",
        "the extension sets are nested: E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0")
    rep_d1 = check_size_premise(repaired, "C0")
    rep_d2 = check_denial(repaired)
    _, rep_col = check_buckets(repaired)
    bad_c2 = c2.replace(
        "E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0",
        "E_C2 contains E_{C^1,1} contains E_H2loc contains E_C0")
    return {
        "repaired_C0": {"size_premise_findings": len(rep_d1), "denial_findings": len(rep_d2),
                        "bucket_collisions": len(rep_col)},
        "inverted_C2_chain_parsed": parse_chain(bad_c2),
        "inverted_C2_control_trips": parse_chain(bad_c2) != EXPECTED_CHAIN,
    }


# ---------------------------------------------------------------------------
def main() -> int:
    t0 = {p: sha256(ROOT / p) for p in PINS}
    drift = {p: (t0[p] != want) for p, want in PINS.items()}
    if any(drift.values()):
        print(json.dumps({"exit": 3, "drift": {k: v for k, v in drift.items() if v},
                          "measured": t0}, indent=2))
        return 3

    c0 = (ROOT / "schemas/af_scc_c0_vacuum.yaml").read_text()
    c2 = (ROOT / "schemas/af_scc_c2_vacuum.yaml").read_text()

    d1_c0 = check_size_premise(c0, "C0")
    d1_c2 = check_size_premise(c2, "C2")
    d2_c0 = check_denial(c0)
    d2_c2 = check_denial(c2)
    buckets_c0, col_c0 = check_buckets(c0)
    buckets_c2, col_c2 = check_buckets(c2)
    comparators, prop = check_propagation(c0, c2)
    xr = xref()
    sens = sensitivity(c0, c2)

    c0_225_stronger = any("two-sided" in b["text"] and "stronger" in b["text"]
                          for b in buckets_c0["forbidden_strengthenings"])
    c0_224_weaker_rule = "[R2-11 mislabel repaired]" in c0 and "WEAKER statements, listed under forbidden_weakenings" in c0
    c2_232_note = "mislabelled it here as a weakening" in c2

    expectations = [
        {"id": "CHAIN-CONCORD", "expect": True,
         "observed": parse_chain(c0) == EXPECTED_CHAIN == parse_chain(c2)},
        {"id": "D1-C0-INVERSION-AT-245", "expect": True,
         "observed": len(d1_c0) == 1 and d1_c0[0]["line"] == 245
                     and d1_c0[0]["subject"] == "C2" and "larger" in d1_c0[0]["claim"]},
        {"id": "D1-C2-CLEAN", "expect": 0, "observed": len(d1_c2)},
        {"id": "D1-C0-CONSEQUENCE-OK", "expect": True,
         "observed": "C2-inextendibility is strictly weaker" in c0},
        {"id": "D2-C0-LIVE-DENIAL-AT-151", "expect": True,
         "observed": len(d2_c0) == 1 and d2_c0[0]["line"] == 151},
        {"id": "D2-C2-LIVE-DENIAL-FREE", "expect": 0, "observed": len(d2_c2)},
        {"id": "D2-C2-PRECEDENT-PRESENT", "expect": True,
         "observed": ("no containment with C2 is asserted" in c2 and "was wrong" in c2)},
        {"id": "D3-C0-COLLISION-225-234", "expect": True,
         "observed": len(col_c0) == 1 and col_c0[0]["strengthening_lines"] == [225]
                     and col_c0[0]["weakening_lines"] == [234]},
        {"id": "D3-C2-NO-COLLISION", "expect": 0, "observed": len(col_c2)},
        {"id": "D3-C0-225-LABELS-STRONGER", "expect": True, "observed": c0_225_stronger},
        {"id": "D3-C0-224-WEAKER-RULE", "expect": True, "observed": c0_224_weaker_rule},
        {"id": "D3-C2-232-MISLABEL-NOTE", "expect": True, "observed": c2_232_note},
        {"id": "D4-RESIDUAL-COUNT-2", "expect": 2,
         "observed": sum(1 for c in comparators if c["c0_residual"])},
        {"id": "D4-P1-RESIDUAL", "expect": True,
         "observed": next(c for c in comparators if c["id"] == "P1")["c0_residual"]},
        {"id": "D4-P2-RESIDUAL", "expect": True,
         "observed": next(c for c in comparators if c["id"] == "P2")["c0_residual"]},
        {"id": "D4-P3-P4-P5-PROPAGATED", "expect": True,
         "observed": all(not next(c for c in comparators if c["id"] == k)["c0_residual"]
                         for k in ("P3", "P4", "P5"))},
        {"id": "XREF-245-FIVE-SOURCES", "expect": 5,
         "observed": len(xr["per_line_sources"]["245"])},
        {"id": "XREF-151-SINGLE-SOURCE", "expect": ["w008_dual_defect"],
         "observed": xr["per_line_sources"]["151"]},
        {"id": "XREF-234-TWO-SOURCES", "expect": ["w058_sweep_rev27", "w058_rev12_delta"],
         "observed": xr["per_line_sources"]["234"]},
        {"id": "SENS-REPAIRED-C0-CLEAN", "expect": True,
         "observed": sens["repaired_C0"] == {"size_premise_findings": 0, "denial_findings": 0,
                                             "bucket_collisions": 0}},
        {"id": "SENS-INVERTED-C2-TRIPS", "expect": True,
         "observed": sens["inverted_C2_control_trips"]},
        {"id": "SPEC-C2-NESTING-PRESENT", "expect": True,
         "observed": prop["specificity"]["c2_has_nesting_statement"]
                     and prop["specificity"]["c2_live_denial_free"]},
    ]
    passed = sum(1 for e in expectations if e["observed"] == e["expect"])

    findings = [
        {
            "id": "W003-CC-01", "line": 245, "kind": "size_premise_inverted",
            "severity": "hard", "verdict": "CONFIRMED",
            "statement": ("implication_ledger.forbidden_transfers[0].reason asserts 'C2 is a strictly "
                          "larger extension class'; the file's own extension_class_containment (C0:238) "
                          "and one_way_entailments (C0:240-242) declare E_C2 subset E_H2loc subset E_C0, "
                          "and C0:224 states C2/C1/H2_loc claims are WEAKER statements. The premise is "
                          "inverted. The row's consequence ('C2-inextendibility is strictly weaker') is "
                          "CORRECT under the declared chain, so the repair is the single token "
                          "'larger'->'smaller' and the transfer ban itself is unaffected."),
            "cross_detectors": ["w008_dual_defect", "w008_form_sep_04_X3c",
                                "w058_sweep_rev27", "w058_rev12_delta", "w096_f2b_review"],
            "falsifier": ("An extension-set reading under which E_C2 strictly contains E_C0 while "
                          "C0:238/C0:240-242 and C2:236 keep their present text; or a revision of C0 "
                          "that removes the 'strictly larger' token."),
        },
        {
            "id": "W003-CC-02", "line": 234, "kind": "strength_bucket_mismatch",
            "severity": "hard", "verdict": "CONFIRMED",
            "statement": ("conclusion.forbidden_weakenings[5] lists 'replacing future by two-sided "
                          "direction' while conclusion.forbidden_strengthenings (C0:225) lists the same "
                          "substitution as 'two-sided inextendibility (different, stronger statement)'. "
                          "C0:224's own rule sends WEAKER statements to forbidden_weakenings; two-sided "
                          "inextendibility is strictly stronger (it also forbids past extensions). The "
                          "sibling C2:232 records the identical classification as a repaired mislabel: "
                          "'An earlier revision mislabelled it here as a weakening' [R2 minor]. The "
                          "weakenings entry is the erroneous one."),
            "cross_detectors": ["w058_sweep_rev27", "w058_rev12_delta"],
            "falsifier": ("A reading in which 'replacing future by two-sided direction' weakens the "
                          "class conclusion, or a revision of C2:232 showing the mislabel note refers to "
                          "a different item."),
        },
        {
            "id": "W003-CC-03", "line": 151, "kind": "false_containment_denial",
            "severity": "hard-with-scope-caveat", "verdict": "CONFIRMED-PATTERN",
            "statement": ("regularity.must_not_conflate[0] carries the LIVE sentence 'No containment "
                          "with C2 or C0 is asserted here' while extension_class_containment (C0:238) "
                          "declares containment of H2_loc with both. The sibling C2:151 records that this "
                          "exact phrasing 'was wrong' [R2 major] and replaces it with the positive nesting "
                          "statement; C0 claims the R2 containment-chain correction (C0:14 index-5 delta, "
                          "C0:238 [R2 major]) but never received the C2:151 replacement. SCOPE CAVEAT: "
                          "'here' admits an entry-local reading (no containment is asserted within this "
                          "entry); that reading is recorded, and this finding claims stale/unpropagated "
                          "R2 text, not mathematical falsity."),
            "cross_detectors": ["w008_dual_defect"],
            "falsifier": ("A revision of C0:151 that carries the C2:151 nesting sentence, or evidence "
                          "that the C2:151 note refers to a different sentence than C0:151's."),
        },
    ]

    t1 = {p: sha256(ROOT / p) for p in PINS}
    drift_after = {p: t1[p] != t0[p] for p in PINS}
    verdict = ("ADJUDICATED: 245 hard (5/5 sources agree), 234 hard (worker-058 only; adjudicated "
               "against the C2:232 precedent), 151 hard-with-scope-caveat (worker-008 only; "
               "adjudicated against the C2:151 [R2 major] precedent). Union defect set = 3.")
    report = {
        "task_id": "W003-C0-REV12-CONTRACT-CONSISTENCY-01",
        "worker": "worker-003",
        "artifact": "c0_contract_consistency_report",
        "created_at": now(),
        "probe_path": str(Path(__file__).resolve().relative_to(ROOT)),
        "probe_sha256": sha256(Path(__file__).resolve()),
        "question": ("Which of the contested C0 order/containment defects at FROZEN rev28 "
                     "(55d0a1ea) are genuine class-contract-text defects: 245 (008+058+096), "
                     "234 (058 only), 151 (008 only)?"),
        "pins": PINS,
        "drift": {"t0": t0, "t1": t1, "consistent": t0 == t1, "any_drift": any(drift_after.values())},
        "checks": expectations,
        "expectations": {"passed": passed, "total": len(expectations),
                         "all_ok": passed == len(expectations)},
        "findings": findings,
        "cross_reference_matrix": xr,
        "propagation_comparators": comparators,
        "sensitivity": sens,
        "bucket_inventory": {"C0": buckets_c0, "C2": buckets_c2},
        "verdict": verdict,
        "repair_set_implied": [
            {"line": 245, "op": "'strictly larger extension class' -> 'strictly smaller extension class'",
             "class_id": "AF-SCC-C0-VAC-GEN", "source": "cross-detector consensus"},
            {"line": 234, "op": "remove 'replacing future by two-sided direction' from forbidden_weakenings "
                                "(already registered as a strengthening at C0:225 / C2:232 variant)",
             "class_id": "AF-SCC-C0-VAC-GEN", "source": "C2:232 [R2 minor] precedent + worker-058"},
            {"line": 151, "op": "replace the denial with the C2:151 nesting statement, or qualify it as "
                                "entry-local and non-normative",
             "class_id": "AF-SCC-C0-VAC-GEN", "source": "C2:151 [R2 major] precedent + worker-008"},
        ],
        "authority_note": ("Worker evidence only. No gate verdict, no node completion, no "
                           "validation_status promotion; repairs are owned by lead-formulation and any "
                           "G-FORM adjudication by astra-lead-audit / astra."),
        "falsifier": ("Re-run this probe at the pinned hashes. Falsified if any declared expectation "
                      "fails on identical bytes, the repaired-C0 control does not go clean, the "
                      "inverted-C2 control does not trip, or any input hash drifts (drift voids the run "
                      "rather than falsifying it)."),
        "next_falsifier": ("At the next C0 freeze, re-run against the new sha256: the three findings "
                           "should disappear if the implied repair set is applied; any surviving "
                           "finding falsifies that repair."),
        "exit_code": 0 if passed == len(expectations) and not any(drift_after.values()) else 2,
    }
    if any(drift_after.values()):
        print(json.dumps({"exit": 3, "drift_after": drift_after}, indent=2))
        return 3
    (HERE / "report.json").write_text(json.dumps(report, indent=2, sort_keys=False))
    print(json.dumps({"exit": report["exit_code"],
                      "expectations": report["expectations"],
                      "verdict": verdict,
                      "finding_lines": [f["line"] for f in findings],
                      "report": str((HERE / "report.json").relative_to(ROOT))}, indent=2))
    return report["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
