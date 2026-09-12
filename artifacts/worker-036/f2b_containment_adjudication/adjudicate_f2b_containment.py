#!/usr/bin/env python3
"""W036-F2B-CONTAINMENT-ADJUDICATION-01

Bounded, class-bound worker measurement (worker-036, node F2b, class
AF-SCC-C0-VAC-GEN, gate G-FORM, context only -- issues no gate verdict).

Question taken with no inbox card: two worker artifacts disagree on how many
*containment-premise* defects are live in the canonical F2b schema
(schemas/af_scc_c0_vacuum.yaml) at FROZEN rev29:

  * worker-060 (containment_semantics_sweep, pinned FROZEN rev28, F2b
    55d0a1ea9bda): 40 checks, 1 failed -> one defect (PR-F2B-245, the
    "C2 is a strictly larger extension class" premise at forbidden_transfers[0]).
  * worker-066 (f2b_rev29_containment_binding, pinned FROZEN rev29, F2b
    b2ab6acb2bbe): exactly two defects (false containment denial at
    must_not_conflate[0] + the same inverted size premise).

This script adjudicates the disagreement at the *current canonical rev29 bytes*
with an independently written detector, and verifies worker-066's claimed
2-edit repair candidate (sha256 84b5d3fa29a6...) by reconstructing it from
live bytes using that worker's declared edit specification and re-measuring.

Fails closed: any input hash that differs from the pins below, at entry or at
exit, aborts with exit 2 (a moving target is not adjudicable).

Usage:  python3 adjudicate_f2b_containment.py [--stamp ISO8601]
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # artifacts/worker-036/<task>/ -> repo root
PINNED = HERE / "pinned"

# ---------------------------------------------------------------- pins ----
PINS = {
    "schemas/af_scc_c0_vacuum.yaml":
        "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml":
        "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "schemas/af_scc_c2_vacuum.yaml":
        "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_wcc_vacuum.yaml":
        "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "artifacts/formulation/FROZEN.json":
        "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    # worker-066's pinned FROZEN-rev28 archive of the same path (rev12 bytes)
    "artifacts/worker-066/f2b_rev29_containment_binding/pinned/"
    "c0_rev12_archive__c0_live__af_scc_c0_vacuum.yaml":
        "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
    # worker-066's edit specification source (read, not trusted)
    "artifacts/worker-066/f2b_rev29_containment_binding/rebind.py":
        None,  # measured and recorded, not pinned
}

CANDIDATE_SHA256 = (
    "84b5d3fa29a677ad157b924675bb5a9c08281395920be0221535465a5da44b40"
)

# worker-066's declared 2-edit specification, copied verbatim from
# artifacts/worker-066/f2b_rev29_containment_binding/rebind.py lines 29-38
# (quoted in report.json as the reconstruction recipe; the resulting candidate
# is then re-measured independently).
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

# Extension-set rank: higher rank == more admissible extensions == weaker
# inexistence statement. Frozen by F2b implication_ledger.extension_class_containment.
RANK = {"C2": 0, "C1,1": 1, "H2loc": 2, "C0": 3, "WCC": None, "SCALAR": None}

TOKEN_PATTERNS = [
    ("C2", r"C2"),
    ("C0", r"C0"),
    ("H2loc", r"H2_?loc"),
    ("C1,1", r"C\^?\{?1,1\}?"),
]

# ------------------------------------------------------------- utilities ---

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def now_stamp() -> str:
    from datetime import datetime, timedelta, timezone
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def line_of(text: str, needle: str) -> int:
    return text[: text.index(needle)].count("\n") + 1


def all_strings(node, path="$"):
    """Yield (json-pointer-ish path, string) for every scalar string in a YAML doc."""
    if isinstance(node, dict):
        for k, v in node.items():
            yield from all_strings(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from all_strings(v, f"{path}[{i}]")
    elif isinstance(node, str):
        yield path, node


def deep_diff(a, b, path="") -> list[str]:
    """Paths where two parsed YAML documents differ."""
    out: list[str] = []

    def child(key):
        return f"{path}.{key}" if path else str(key)

    if type(a) is not type(b):
        return [f"{path} (type {type(a).__name__} -> {type(b).__name__})"]
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                out.append(f"{child(k)} (added)")
            elif k not in b:
                out.append(f"{child(k)} (removed)")
            else:
                out += deep_diff(a[k], b[k], child(k))
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append(f"{path} (len {len(a)} -> {len(b)})")
        for i, (x, y) in enumerate(zip(a, b)):
            out += deep_diff(x, y, f"{path}[{i}]")
    elif a != b:
        out.append(path)
    return out


# ------------------------------------------------------------- detector ----
# Independently written, deliberately different from both worker-060's
# size-comparative detector and worker-066's token rules: this detector works
# from (a) explicit denial phrases and (b) explicit comparative class-size
# premises, and adjudicates each against the chain declared in the file itself.

DENIAL_RE = re.compile(r"(?i)\bno\s+containment\b|\bno\s+inclusion\b")
DENIAL_SCOPED_RE = re.compile(
    r"(?i)\b(?:does|do|is|are)\s+not\s+contained\b")
CLASS_CONTEXT_RE = re.compile(r"(?i)\bclass(?:es)?\b|\bextension")
COMPARATIVE_RE = re.compile(
    r"(?i)(?P<tok>C2|C0|H2_?loc|C\^?\{?1,1\}?)\s+is\s+a\s+strictly\s+"
    r"(?P<cmp>larger|bigger|smaller|weaker|stronger)\s+extension\s+class")
CORRECTION_NOTE_RE = re.compile(r"\[[^\]]*\]")


def _excluded_spans(text: str):
    """Character spans of correction notes: [R2 major: ... was wrong]."""
    return [m.span() for m in CORRECTION_NOTE_RE.finditer(text)]


def _in_spans(pos: int, spans) -> bool:
    return any(s <= pos < e for s, e in spans)


def detect(text: str, enclosing_row=None, parse=None):
    """Return (defects, excluded_mentions).

    enclosing_row: for a forbidden_transfers/one_way_entailments row, a dict
    with the row's `from`/`to` fields so a bare comparative can be adjudicated.
    parse: parsed YAML doc of the same file (used to re-derive the chain).
    """
    defects, excluded = [], []
    spans = _excluded_spans(text)

    # R1: containment denial ('no containment' / 'no inclusion' are the
    # document's technical terms; a bare 'not contained' only counts when the
    # window is talking about classes or extensions, which keeps measure-theory
    # uses such as F1 'not contained in any countable union ...' out)
    denial_hits = list(DENIAL_RE.finditer(text))
    for m in DENIAL_SCOPED_RE.finditer(text):
        win0 = text[max(0, m.start() - 200):m.end() + 200]
        if CLASS_CONTEXT_RE.search(win0):
            denial_hits.append(m)
    for m in denial_hits:
        if _in_spans(m.start(), spans):
            excluded.append({"rule": "R1", "kind": "quoted_correction_record",
                             "quote": text[max(0, m.start() - 40):m.end() + 40]})
            continue
        # named chain tokens in the same sentence window
        win = text[max(0, m.start() - 160):m.end() + 160]
        toks = [name for name, pat in TOKEN_PATTERNS
                if re.search(pat, win) and RANK.get(name) is not None]
        defects.append({
            "rule": "R1",
            "kind": "false_containment_denial",
            "quote": text[max(0, m.start() - 60):m.end() + 80].strip(),
            "tokens": sorted(set(toks)),
            "why": ("the sentence denies containment involving "
                    + "/".join(sorted(set(toks)) or ["chain classes"])
                    + " while the file's own implication_ledger declares "
                      "E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0"),
        })

    # R2: inverted class-size premise
    for m in COMPARATIVE_RE.finditer(text):
        if _in_spans(m.start(), spans):
            excluded.append({"rule": "R2", "kind": "quoted_correction_record",
                             "quote": text[max(0, m.start() - 40):m.end() + 40]})
            continue
        tok = m.group("tok")
        cmp_ = m.group("cmp").lower()
        # normalise token
        name = None
        for cand, pat in TOKEN_PATTERNS:
            if re.fullmatch(pat, tok, flags=re.I):
                name = cand
                break
        if name is None or RANK.get(name) is None:
            continue
        # context target: the row this premise belongs to, else 'this class'
        target = None
        if enclosing_row:
            if enclosing_row.get("from", "").find(name) >= 0:
                target = enclosing_row.get("to")
            elif enclosing_row.get("to", "").find(name) >= 0:
                target = enclosing_row.get("from")
        ctx = text[max(0, m.start() - 200):m.end() + 200]
        target_name = None
        if target and "this class" in str(target):
            target_name = "C0"          # F2b is the C0 schema
        elif target:
            for cand, pat in TOKEN_PATTERNS:
                if re.search(pat, str(target)) and cand != name:
                    target_name = cand
                    break
        if target_name is None:
            for cand, pat in TOKEN_PATTERNS:
                if cand != name and re.search(pat, ctx):
                    target_name = cand
                    break
        if target_name is None or RANK.get(target_name) is None:
            continue
        rank_a, rank_b = RANK[name], RANK[target_name]
        wants_larger = cmp_ in ("larger", "bigger")
        consistent = (rank_a > rank_b) if wants_larger else (rank_a < rank_b)
        if not consistent:
            defects.append({
                "rule": "R2",
                "kind": "size_premise_inverted",
                "quote": m.group(0).strip(),
                "tokens": [name, target_name],
                "why": (f"{name} (extension-set rank {rank_a}) called a strictly "
                        f"{cmp_} extension class than {target_name} (rank {rank_b}); "
                        "the file's chain orders E_C2 subset of E_H2loc subset of E_C0"),
            })
    return defects, excluded


def detect_doc(parsed):
    """Full-document sweep: every string, with row context where available."""
    defects, excluded, scanned = [], [], 0
    rows = []
    il = (parsed or {}).get("implication_ledger") or {}
    for key in ("forbidden_transfers", "one_way_entailments"):
        for r in il.get(key) or []:
            if isinstance(r, dict):
                rows.append(r)
    # map row -> reason substring index for context attribution
    for path, s in all_strings(parsed):
        scanned += 1
        row = None
        for r in rows:
            if isinstance(r.get("reason"), str) and r["reason"] in s:
                row = r
                break
        d, e = detect(s, enclosing_row=row, parse=parsed)
        for x in d:
            x["path"] = path[2:] if path.startswith("$.") else path
        defects += d
        excluded += e
    return defects, excluded, scanned


# ---------------------------------------------------------------- main -----

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stamp", default=now_stamp())
    args = ap.parse_args()
    stamp = args.stamp

    # pin check at entry
    measured_entry = {}
    for rel in PINS:
        p = ROOT / rel
        if not p.exists():
            print(f"PIN-MISSING {rel}", file=sys.stderr)
            return 2
        measured_entry[rel] = sha256_file(p)
        if PINS[rel] is not None and measured_entry[rel] != PINS[rel]:
            print(f"PIN-DRIFT {rel}: {measured_entry[rel]} != {PINS[rel]}", file=sys.stderr)
            return 2

    c0_text = (ROOT / "schemas/af_scc_c0_vacuum.yaml").read_text()
    c0_mirror = (ROOT / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml").read_text()
    c2_text = (ROOT / "schemas/af_scc_c2_vacuum.yaml").read_text()
    f1_text = (ROOT / "schemas/af_wcc_vacuum.yaml").read_text()
    rev12_text = (ROOT / "artifacts/worker-066/f2b_rev29_containment_binding/pinned/"
                         "c0_rev12_archive__c0_live__af_scc_c0_vacuum.yaml").read_text()
    frozen = json.loads((ROOT / "artifacts/formulation/FROZEN.json").read_text())
    c0 = yaml.safe_load(c0_text)
    c2 = yaml.safe_load(c2_text)

    checks: list[dict] = []

    def check(cid, desc, expected, observed):
        ok = expected == observed
        checks.append({"check": cid, "description": desc, "expected": expected,
                       "observed": observed, "pass": bool(ok)})
        return ok

    # ---- A. chain declared by the file itself -----------------------------
    chain_line = c0["implication_ledger"]["extension_class_containment"]
    chain_ok = ("E_C0 contains E_H2loc" in chain_line
                and "E_{C^1,1}" in chain_line and "E_C2" in chain_line)
    check("A1-chain-declared", "F2b declares E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2",
          True, chain_ok)
    check("A2-chain-direction", "extension sets shrink as regularity rises (rank C2 < C1,1 < H2loc < C0)",
          True, RANK["C2"] < RANK["C1,1"] < RANK["H2loc"] < RANK["C0"])

    # sibling correction record proves the intended reading of the denial slot
    c2_slot = c2["regularity"]["must_not_conflate"][1]
    check("A3-sibling-correction-record",
          "F2a's same slot records the earlier denial as wrong and states the nesting",
          True, ("earlier 'no containment with C2 is asserted' was wrong" in c2_slot
                 and "E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0" in c2_slot))

    # ---- B. detector on live rev29 bytes ---------------------------------
    live_defects, live_excluded, live_scanned = detect_doc(c0)
    live_kinds = sorted(d["kind"] for d in live_defects)
    check("B1-live-defect-count", "live F2b rev29 yields exactly the two defect kinds",
          ["false_containment_denial", "size_premise_inverted"], live_kinds)

    d1 = next((d for d in live_defects if d["kind"] == "false_containment_denial"), None)
    d2 = next((d for d in live_defects if d["kind"] == "size_premise_inverted"), None)
    check("B2-d1-slot", "denial located in regularity.must_not_conflate[0]",
          "regularity.must_not_conflate[0]", d1["path"] if d1 else None)
    check("B3-d2-slot", "inversion located in implication_ledger.forbidden_transfers[0].reason",
          "implication_ledger.forbidden_transfers[0].reason", d2["path"] if d2 else None)

    # ---- C. sibling / cross-file coverage sweep --------------------------
    c2_defects, c2_excluded, c2_scanned = detect_doc(c2)
    f1_defects, f1_excluded, f1_scanned = detect_doc(yaml.safe_load(f1_text))
    check("C1-sibling-f2a-clean", "F2a rev13 carries neither defect kind", [], sorted(
        d["kind"] for d in c2_defects))
    check("C2-f1-clean", "F1 rev13 carries neither defect kind", [], sorted(
        d["kind"] for d in f1_defects))
    check("C3-quoted-mention-specificity",
          "F2a's quoted correction record is excluded, not counted as a defect",
          True, len(c2_excluded) >= 1 and not c2_defects)
    check("C4-coverage-scan", "full-string sweep scanned every scalar of all three schemas",
          True, live_scanned > 300 and c2_scanned > 250 and f1_scanned > 250)

    # ---- D. rev12 -> rev29 carry-over ------------------------------------
    carried = {
        "denial": H2_LIVE_FRAG in rev12_text and H2_LIVE_FRAG in c0_text,
        "inversion": H1_LIVE in rev12_text and H1_LIVE in c0_text,
    }
    check("D1-carried-over", "both defect clauses are byte-identical at rev12 and rev29",
          {"denial": True, "inversion": True}, carried)
    rev12_defects, _, _ = detect_doc(yaml.safe_load(rev12_text))
    check("D2-rev12-same-kinds", "rev12 archive yields the same two defect kinds",
          ["false_containment_denial", "size_premise_inverted"],
          sorted(d["kind"] for d in rev12_defects))

    # ---- E. repair-candidate reconstruction and verification -------------
    recipe_applicable = (H1_LIVE in c0_text) and (H2_LIVE_FRAG in c0_text)
    check("E1-recipe-applicable", "both declared live fragments are present verbatim",
          True, recipe_applicable)
    candidate = c0_text.replace(H1_LIVE, H1_FIXED).replace(H2_LIVE_FRAG, H2_FIXED_FRAG)
    cand_hash = sha256_bytes(candidate.encode())
    check("E2-candidate-hash", "reconstructed 2-edit candidate equals worker-066's claimed sha256",
          CANDIDATE_SHA256, cand_hash)

    diff_lines = [l for l in difflib.unified_diff(
        c0_text.splitlines(), candidate.splitlines(), lineterm="", n=0)
        if l.startswith(("+", "-")) and not l.startswith(("+++", "---"))]

    def change_regions(lines):
        regions, prev_plus = 0, False
        for l in lines:
            is_plus = l.startswith("+")
            if is_plus and not prev_plus:
                regions += 1
            prev_plus = is_plus
        return regions

    check("E3-minimal-2-regions", "live -> candidate changes exactly two line regions",
          2, change_regions(diff_lines))
    check("E3b-changed-lines", "the two regions are 2 physical lines each (denial block wraps)",
          4, len(diff_lines))

    parsed_diff = deep_diff(c0, yaml.safe_load(candidate))
    check("E4-parsed-diff-scope",
          "parsed-YAML diff is exactly the two normative slots",
          ["implication_ledger.forbidden_transfers[0].reason",
           "regularity.must_not_conflate[0]"],
          sorted(parsed_diff))

    cand_defects, cand_excluded, cand_scanned = detect_doc(yaml.safe_load(candidate))
    check("E5-candidate-clean", "candidate yields zero defects under this detector",
          [], sorted(d["kind"] for d in cand_defects))
    check("E6-candidate-quoted-mention-retained",
          "candidate keeps the historical note as a quoted mention (excluded, not a defect)",
          True, any(e["kind"] == "quoted_correction_record" for e in cand_excluded))

    # necessity: revert each edit on the candidate and require the matching defect back
    only_h1 = c0_text.replace(H1_LIVE, H1_FIXED)
    only_h2 = c0_text.replace(H2_LIVE_FRAG, H2_FIXED_FRAG)
    n_only_h1 = sorted(d["kind"] for d in detect_doc(yaml.safe_load(only_h1))[0])
    n_only_h2 = sorted(d["kind"] for d in detect_doc(yaml.safe_load(only_h2))[0])
    check("E7-necessity-h1", "fixing only the size premise leaves the denial defect",
          ["false_containment_denial"], n_only_h1)
    check("E8-necessity-h2", "fixing only the denial leaves the inverted premise",
          ["size_premise_inverted"], n_only_h2)

    # sensitivity: re-insert each live clause into the candidate
    reinstate_d = candidate.replace(H2_FIXED_FRAG, H2_LIVE_FRAG)
    reinstate_i = candidate.replace(H1_FIXED, H1_LIVE)
    check("E9-sensitivity-denial", "re-inserting the denial fires exactly that rule",
          ["false_containment_denial"],
          sorted(d["kind"] for d in detect_doc(yaml.safe_load(reinstate_d))[0]))
    check("E10-sensitivity-inversion", "re-inserting the inversion fires exactly that rule",
          ["size_premise_inverted"],
          sorted(d["kind"] for d in detect_doc(yaml.safe_load(reinstate_i))[0]))

    # ---- F. adjudication of the W060-vs-W066 count disagreement ----------
    w060_report = ROOT / "artifacts/worker-060/containment_semantics_sweep/REPORT.md"
    w060_evidence = ROOT / "artifacts/worker-060/containment_semantics_sweep/evidence.json"
    w060 = {"report": str(w060_report.relative_to(ROOT)),
            "report_sha256": sha256_file(w060_report),
            "evidence_sha256": sha256_file(w060_evidence)}
    w060_check_ids = []
    try:
        ev = json.loads(w060_evidence.read_text())
        w060_check_ids = [c.get("check_id") for c in ev.get("checks", [])]
    except Exception as exc:  # pragma: no cover
        w060["evidence_read_error"] = str(exc)
    w060_has_denial_rule = any(
        "DENIAL" in (c or "").upper() or "CONTAINMENT-NEG" in (c or "").upper()
        for c in w060_check_ids)
    check("F1-w060-detector-scope",
          "worker-060's published check set contains no containment-denial rule",
          False, w060_has_denial_rule)
    w060["check_ids"] = w060_check_ids
    w060["reported_failing_checks"] = ["PR-F2B-245"]
    w060["detector_scope_note"] = (
        "worker-060's evidence.json has no check id targeting a containment denial; "
        "its 14 curated prose rows cover PR-F2B-238/245/SUB/DIST only, and its "
        "generalised detector CS-01/CS-02 is size-comparative. Its single failed "
        "check PR-F2B-245 is the same inverted premise this measurement confirms. "
        "The 1-vs-2 difference is therefore detector coverage, not a factual "
        "contradiction: at rev29 the denial clause is a second, independently "
        "detectable defect of the 'false containment denial' kind.")

    # ---- report ----------------------------------------------------------
    report = {
        "task_id": "W036-F2B-CONTAINMENT-ADJUDICATION-01",
        "actor": "worker-036",
        "generated_at": stamp,
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
        "gate": "G-FORM",
        "authority": ("worker measurement and text-consistency adjudication only. No canonical "
                      "path written; no gate verdict; no node status; no validation_status. The "
                      "candidate is evidence for the owning lead, not an applied repair."),
        "scope": ("Text/consistency semantics of the pinned bytes only; not a claim about the "
                  "mathematics of C0/C2 inextendibility."),
        "inputs": {rel: {"sha256": h, "bytes": (ROOT / rel).stat().st_size}
                   for rel, h in measured_entry.items()},
        "canonical_live": {
            "path": "schemas/af_scc_c0_vacuum.yaml",
            "sha256": measured_entry["schemas/af_scc_c0_vacuum.yaml"],
            "mirror_identical": sha256_bytes(c0_mirror.encode()) == measured_entry[
                "schemas/af_scc_c0_vacuum.yaml"],
            "frozen_revision": frozen.get("revision"),
            "frozen_manifest_sha256": measured_entry["artifacts/formulation/FROZEN.json"],
        },
        "chain": {
            "declared": chain_line,
            "rank": RANK,
            "meaning": "higher rank = larger admissible-extension set = weaker inexistence statement",
        },
        "detector": {
            "rules": [
                "R1 false_containment_denial: a containment-denial phrase naming a chain "
                "class, outside a [..] correction note",
                "R2 size_premise_inverted: 'X is a strictly larger/smaller extension class' "
                "whose comparator contradicts the file's own chain ranks",
            ],
            "exclusion": "quoted mentions inside [R2 ... was wrong] correction records",
        },
        "findings": [
            ({"id": "W036-F2B-D1", "kind": d1["kind"], "locator": d1["path"],
              "line": line_of(c0_text, H2_LIVE_FRAG), "quote": H2_LIVE_FRAG,
              "contradiction": d1["why"], "severity": "hard (textual consistency; G-FORM item)"}
             if d1 else None),
            ({"id": "W036-F2B-D2", "kind": d2["kind"], "locator": d2["path"],
              "line": line_of(c0_text, H1_LIVE), "quote": H1_LIVE,
              "contradiction": d2["why"], "severity": "hard (textual consistency; G-FORM item)"}
             if d2 else None),
        ],
        "adjudication": {
            "question": ("Are there one (worker-060) or two (worker-066) containment-premise "
                         "defects live in canonical F2b at FROZEN rev29?"),
            "verdict": "two",
            "deciding_evidence": [
                "The file declares E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2 "
                "(implication_ledger.extension_class_containment), so a denial of containment "
                "with C2/C0 is false under the file's own glossary.",
                "The sibling C2 schema's same slot carries the explicit correction record "
                "'the earlier \"no containment with C2 is asserted\" was wrong' plus the "
                "nesting statement -- the project already settled the intended reading.",
                "The denial clause is byte-identical at rev12 55d0a1ea and rev29 b2ab6acb: "
                "carried over, not introduced by rev13.",
            ],
            "steelman_of_one_defect_reading": (
                "'here' could be scoped to the regularity axis (the entry's first sentence "
                "concerns H2_loc as a regularity-axis value, and the banned phrase 'strictly "
                "between' is an axis-ordering phrase). Under that reading the clause denies an "
                "axis ordering, not extension-set nesting."),
            "why_steelman_does_not_clear_the_clause": (
                "The denial sentence is unqualified and uses the document's technical term "
                "'containment', which everywhere else in this file denotes extension-set "
                "inclusion; no axis-scoping qualifier is attached. An ordinary reader applying "
                "the file's own glossary is licensed to read it as a containment denial, and "
                "the sibling's correction record makes the intended reading determinate. At "
                "minimum the clause is a live equivocation in a frozen artifact."),
            "either_way": ("Under both readings the owning lead's 2-edit repair (or an "
                           "equivalent disambiguation) is required before this slot can be "
                           "read as finding-free."),
        },
        "count_disagreement": {
            "worker_060": w060,
            "worker_066_reported_defects": 2,
            "this_measurement_defects_at_rev29": 2,
            "resolution": ("worker-060's 1-count is a detector-coverage artifact: its published "
                           "check set implements no denial rule (verified from its own "
                           "evidence.json check ids), while its PR-F2B-245 inversion is "
                           "independently reproduced here. Both artifacts are consistent about "
                           "the inversion; this measurement supplies the missing denial-rule "
                           "coverage at the current pins."),
        },
        "repair_verification": {
            "candidate_sha256": cand_hash,
            "claimed_by": "worker-066 (W066-F2B-REV29-CONTAINMENT-01)",
            "claimed_sha256": CANDIDATE_SHA256,
            "hash_match": cand_hash == CANDIDATE_SHA256,
            "recipe_source": ("artifacts/worker-066/f2b_rev29_containment_binding/rebind.py "
                              "H1_LIVE/H1_FIXED/H2_LIVE_FRAG/H2_FIXED_FRAG (declared edit spec, "
                              "re-applied here to live bytes)"),
            "changed_lines": diff_lines,
            "parsed_diff_paths": parsed_diff,
            "candidate_defect_kinds": sorted(d["kind"] for d in cand_defects),
            "single_edit_only_h1_kinds": n_only_h1,
            "single_edit_only_h2_kinds": n_only_h2,
            "verdict": ("reconstruction equals the claimed candidate hash; the candidate is a "
                        "2-line, 2-slot repair that removes both defect kinds and preserves "
                        "every other parsed YAML path, with the historical note retained as a "
                        "quoted mention. This verifies the candidate's textual effect only; it "
                        "is not a gate verdict and not an approval of the mathematics."),
        },
        "controls": checks,
        "coverage": {"F2b_strings_scanned": live_scanned,
                     "F2a_strings_scanned": c2_scanned,
                     "F1_strings_scanned": f1_scanned,
                     "sweep_hits": {"F2b": len(live_defects), "F2a": len(c2_defects),
                                    "F1": len(f1_defects)},
                     "excluded_quoted_mentions": {
                         "F2b": len(live_excluded), "F2a": len(c2_excluded),
                         "F1": len(f1_excluded)}},
        "falsifier": (
            "Re-run adjudicate_f2b_containment.py at the pinned hashes. The claim is "
            "FALSIFIED if (a) either pinned canonical schema or the FROZEN rev29 manifest "
            "moves (void, not falsified), (b) F2b's implication_ledger does not declare "
            "E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2, (c) the F2a sibling slot "
            "does not carry the correction record that the earlier denial was wrong, "
            "(d) either defect clause is absent from rev29 or is licensed as correct by the "
            "file's own glossary, or (e) the 2-edit candidate is not exactly 84b5d3fa29a6 or "
            "changes any parsed path beyond the two named slots."),
        "next_falsifier": (
            "For the owning lead: a landed repair at a new revision must be re-measured at its "
            "own hash; a third defect kind in the same slots would falsify the repair's "
            "sufficiency, and any change to the two cited lines that reintroduces a "
            "denial/inversion is caught by controls E9/E10."),
        "pins_stable_entry_exit": None,
        "checks_passed": sum(1 for c in checks if c["pass"]),
        "checks_total": len(checks),
    }

    # pin check at exit
    measured_exit = {rel: sha256_file(ROOT / rel) for rel in PINS}
    report["pins_stable_entry_exit"] = measured_exit == measured_entry
    if not report["pins_stable_entry_exit"]:
        print("PIN-DRIFT during run; refusing to write report", file=sys.stderr)
        return 2

    # persist pinned copies for reproducibility
    PINNED.mkdir(parents=True, exist_ok=True)
    for rel in PINS:
        dst = PINNED / rel.replace("/", "__")
        dst.write_bytes((ROOT / rel).read_bytes())

    (HERE / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print(json.dumps({
        "task_id": report["task_id"],
        "checks": f"{report['checks_passed']}/{report['checks_total']}",
        "defects": sorted(d["kind"] for d in live_defects),
        "candidate_sha256": cand_hash,
        "hash_match": report["repair_verification"]["hash_match"],
        "report": str((HERE / "report.json").relative_to(ROOT)),
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
