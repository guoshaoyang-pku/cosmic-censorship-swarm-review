#!/usr/bin/env python3
"""W028-F1F2A-INTERNAL-CONSISTENCY-01 - independent cross-field consistency sweep.

Read-only instrument. Reads the pinned F1/F2a/F2b schemas, adjudicates every
normative cross-field statement against the extension-set order each document
declares, and reports findings. F2b at b2ab6acb is a KNOWN-DEFECTIVE reference
used as the real (unplanted) positive control; F1 and F2a are the targets.

Defect classes (pre-registered in prereg.json):
  D1 bare containment denial contradicting the document's own assertion
  D2 inverted strictly-larger/smaller extension-class premise
  D3 conclusion block carrying another family's content
  D4 declared E_X subset-of/contains E_Y contradicting the declared order
  D5 implication_ledger row direction not licensed by the declared order

No canonical file is written. Mutant controls are derived from the pinned live
bytes at run time and written only under this artifact directory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))

PINS = {
    "schemas/af_wcc_vacuum.yaml": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "artifacts/formulation/FROZEN.json": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
}
MIRRORS = {
    "schemas/af_wcc_vacuum.yaml": "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml": "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml": "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
}

# extension-set order declared by the documents themselves:
# E_C2 subset E_{C^1,1} subset E_H2loc subset E_C0 (lower regularity = larger set)
RANK = {"C2": 0, "C11": 1, "H2LOC": 2, "C0": 3}
TOKEN_ALIASES = {
    "C2": "C2", "C^2": "C2",
    "C0": "C0", "C^0": "C0",
    "C1": "C1", "C^1": "C1",
    "C11": "C11", "C1,1": "C11", "C^1,1": "C11", "C^{1,1}": "C11",
    "H2LOC": "H2LOC", "H2_LOC": "H2LOC", "H2loc": "H2LOC",
}
E_TOKEN = re.compile(r"E_(\{[^}]*\}|[A-Za-z0-9_^]+)")
DENIAL = re.compile(r"no\s+containment\s+with\s+[A-Za-z0-9^,{}_ ]+?\s+is\s+asserted", re.I)
SIZE_PREMISE = re.compile(r"\b(C0|C2|C\^?\{?1,1\}?|H2_?loc|H2LOC)\s+is\s+a\s+strictly\s+(larger|smaller)\s+extension\s+class", re.I)
STRENGTH_PREMISE = re.compile(r"\b(C0|C2|C\^?\{?1,1\}?|H2_?loc|H2LOC)-inextendibility\s+is\s+(strictly\s+)?(stronger|weaker)\s+than\s+this\s+class", re.I)
LEDGER_TOK = re.compile(r"no\s+proper\s+future\s+(.+?)\s+extension")
COMPOSITE = re.compile(r"\bC0\s+or\s+C2\b|\bC2\s+or\s+C0\b", re.I)

MENTION_PATH_PARTS = {
    "anti_scope", "forbidden_strengthenings", "forbidden_weakenings",
    "must_not_conflate", "unresolved_items", "review_status", "revision_history",
    "known_status", "provenance", "l1_ledger_refs", "phrases_that_are_not_this_class",
    "falsifier",  # failure-mode descriptions, not assertions of the class content
}
CORRECTION_MARKERS = ("wrong", "earlier", "corrected", "was false", "must not be cited",
                      "not equivalent", "correction", "removed")
SCC_INEXT = re.compile(
    r"\b(C2|C0|C\^?\{?1,1\}?|H2_?loc|H2LOC)[- ]?inextendib"
    r"|\binextendib\w*\s+(?:as\s+)?(?:a\s+)?(C2|C0|C\^?\{?1,1\}?|H2_?loc|H2LOC)\b", re.I)


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def norm_token(raw: str):
    t = raw.strip().strip("{}").replace(" ", "")
    return TOKEN_ALIASES.get(t) or TOKEN_ALIASES.get(t.upper()) or TOKEN_ALIASES.get(t.lower())


def walk_strings(obj, path=()):
    """Yield (dotted_path_tuple, string_leaf)."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk_strings(v, path + (str(k),))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_strings(v, path + (str(i),))
    elif isinstance(obj, str):
        yield path, obj


def in_mention_path(path) -> bool:
    return any(part in MENTION_PATH_PARTS for part in path)


def find_line(raw_lines, needle: str):
    needle = needle.strip()
    for i, line in enumerate(raw_lines, 1):
        if needle[:60] and needle[:60] in line:
            return i
    for i, line in enumerate(raw_lines, 1):
        if needle[:25] and needle[:25] in line:
            return i
    return None


def is_quoted_mention(s: str, start: int, end: int) -> bool:
    prefix = s[:start]
    return prefix.count("'") % 2 == 1 or prefix.count('"') % 2 == 1


def is_corrected(s: str, start: int | None = None, end: int | None = None) -> bool:
    """Correction marker must be near the match, not merely somewhere in the string."""
    low = s.lower()
    if start is None:
        return any(m in low for m in CORRECTION_MARKERS)
    window = low[max(0, start - 40): (end or start) + 40]
    return any(m in window for m in CORRECTION_MARKERS)


# ---------------------------------------------------------------- shared checks

def check_containment_pairs(doc, raw_lines):
    """D4: every E_X subset-of/contains E_Y pair must match the declared order."""
    findings = []
    for path, s in walk_strings(doc):
        ms = list(E_TOKEN.finditer(s))
        if len(ms) < 2:
            continue
        for a, b in zip(ms, ms[1:]):
            between = s[a.end():b.start()].lower()
            if "subset" in between:
                rel = "subset"
            elif "contains" in between:
                rel = "contains"
            else:
                continue
            x, y = norm_token(a.group(1)), norm_token(b.group(1))
            xa, ya = a.group(1), b.group(1)
            if x not in RANK or y not in RANK:
                findings.append({
                    "id": "S4-unranked", "defect": "D4", "severity": "info",
                    "path": ".".join(path), "line": find_line(raw_lines, s),
                    "detail": f"containment pair ({xa} {rel} {ya}) uses a token outside the "
                              f"declared chain; recorded, not adjudicated",
                })
                continue
            ok = (RANK[x] < RANK[y]) if rel == "subset" else (RANK[x] > RANK[y])
            if not ok:
                findings.append({
                    "id": "S4-mismatch", "defect": "D4", "severity": "blocking",
                    "path": ".".join(path), "line": find_line(raw_lines, s),
                    "excerpt": s[:180],
                    "detail": f"declared '{xa} {rel} {ya}' contradicts the order "
                              f"E_C2 subset E_C11 subset E_H2LOC subset E_C0 "
                              f"(ranks {x}={RANK[x]}, {y}={RANK[y]})",
                })
    return findings


def check_ledger(doc, raw_lines):
    """D5 + D2: entailment/forbidden row directions and size/strength premises."""
    findings = []
    led = doc.get("implication_ledger") or {}
    for i, row in enumerate(led.get("one_way_entailments") or []):
        frm, to, rel = row.get("from", ""), row.get("to", ""), row.get("relation")
        mf, mt = LEDGER_TOK.search(frm), LEDGER_TOK.search(to)
        if not (mf and mt):
            findings.append({"id": "S5-unparsed", "defect": "D5", "severity": "info",
                             "path": f"implication_ledger.one_way_entailments.{i}",
                             "line": find_line(raw_lines, frm),
                             "detail": f"row not parseable as regularity tokens: {frm!r} -> {to!r}"})
            continue
        x, y = norm_token(mf.group(1).split()[0]), norm_token(mt.group(1).split()[0])
        if x not in RANK or y not in RANK:
            findings.append({"id": "S5-unranked", "defect": "D5", "severity": "info",
                             "path": f"implication_ledger.one_way_entailments.{i}",
                             "line": find_line(raw_lines, frm),
                             "detail": f"unranked token in row {frm!r} -> {to!r}"})
            continue
        if x == y:
            reason = str(row.get("reason", "")).lower()
            if "subset" not in reason and "refine" not in reason and "concept" not in reason:
                findings.append({"id": "S5-same-token", "defect": "D5", "severity": "minor",
                                 "path": f"implication_ledger.one_way_entailments.{i}",
                                 "line": find_line(raw_lines, frm),
                                 "detail": f"same-token entailment without a stated set relation: {frm!r} -> {to!r}"})
            continue
        licensed = RANK[y] < RANK[x]
        if rel == "entails" and not licensed:
            findings.append({"id": "S5-direction", "defect": "D5", "severity": "blocking",
                             "path": f"implication_ledger.one_way_entailments.{i}",
                             "line": find_line(raw_lines, frm), "excerpt": json.dumps(row, ensure_ascii=False)[:180],
                             "detail": f"row marked entails but E_{y} is not strictly inside E_{x}"})
        if rel == "forbidden" and licensed:
            findings.append({"id": "S5-forbidden-licensed", "defect": "D5", "severity": "blocking",
                             "path": f"implication_ledger.one_way_entailments.{i}",
                             "line": find_line(raw_lines, frm),
                             "detail": f"row marked forbidden but E_{y} is strictly inside E_{x}"})
    this_tok = None
    comp = doc.get("class_components") or {}
    if comp.get("regularity_token"):
        this_tok = norm_token(str(comp["regularity_token"]))
    for i, row in enumerate(led.get("forbidden_transfers") or []):
        frm, to = row.get("from", ""), row.get("to", "")
        mf, mt = LEDGER_TOK.search(frm), LEDGER_TOK.search(to)
        x = norm_token(mf.group(1).split()[0]) if mf else None
        y = norm_token(mt.group(1).split()[0]) if mt else None
        if x in RANK and y in RANK and x != y:
            licensed = RANK[y] < RANK[x]
            if licensed:
                findings.append({"id": "S5-forbidden-licensed", "defect": "D5", "severity": "blocking",
                                 "path": f"implication_ledger.forbidden_transfers.{i}",
                                 "line": find_line(raw_lines, frm),
                                 "detail": f"forbidden transfer {frm!r} -> {to!r} is actually licensed"})
        reason = str(row.get("reason", ""))
        low = reason.lower()
        if "licensed" in low and "not " not in low and "never" not in low:
            findings.append({"id": "S6-licensed-reason", "defect": "D2", "severity": "blocking",
                             "path": f"implication_ledger.forbidden_transfers.{i}.reason",
                             "line": find_line(raw_lines, reason[:50]),
                             "excerpt": reason[:180],
                             "detail": "a forbidden-transfer row carries a reason that says the transfer is licensed"})
    return findings


def check_premises(doc, raw_lines):
    """D2: strictly larger/smaller or stronger/weaker premises vs the declared order."""
    findings = []
    comp = doc.get("class_components") or {}
    this_tok = norm_token(str(comp.get("regularity_token") or ""))
    for path, s in walk_strings(doc):
        if "reason" not in path and "note" not in path and "conclusion" not in path and "detail" not in path:
            continue
        for m in SIZE_PREMISE.finditer(s):
            subj = norm_token(m.group(1))
            direction = m.group(2).lower()
            if subj not in RANK or this_tok not in RANK:
                continue
            ok = RANK[subj] > RANK[this_tok] if direction == "larger" else RANK[subj] < RANK[this_tok]
            if not ok:
                findings.append({"id": "S6-size-inverted", "defect": "D2", "severity": "blocking",
                                 "path": ".".join(path), "line": find_line(raw_lines, s),
                                 "excerpt": m.group(0),
                                 "detail": f"'{subj} is a strictly {direction} extension class' contradicts "
                                           f"the declared order (this class {this_tok}, ranks {RANK[subj]} vs {RANK[this_tok]})"})
        for m in STRENGTH_PREMISE.finditer(s):
            subj = norm_token(m.group(1))
            direction = m.group(3).lower()
            if subj not in RANK or this_tok not in RANK:
                continue
            ok = RANK[subj] > RANK[this_tok] if direction == "stronger" else RANK[subj] < RANK[this_tok]
            if not ok:
                findings.append({"id": "S6-strength-inverted", "defect": "D2", "severity": "blocking",
                                 "path": ".".join(path), "line": find_line(raw_lines, s),
                                 "excerpt": m.group(0),
                                 "detail": f"'{subj}-inextendibility is {direction} than this class' contradicts "
                                           f"the declared order (this class {this_tok})"})
    return findings


def check_denials(doc, raw_lines):
    """D1: bare containment denial contradicting the document's own containment rows."""
    findings, mentions = [], []
    for path, s in walk_strings(doc):
        for m in DENIAL.finditer(s):
            if is_quoted_mention(s, m.start(), m.end()) or is_corrected(s, m.start(), m.end()):
                mentions.append({"path": ".".join(path), "line": find_line(raw_lines, s),
                                 "text": m.group(0)[:120]})
                continue
            findings.append({"id": "S7-bare-denial", "defect": "D1", "severity": "blocking",
                             "path": ".".join(path), "line": find_line(raw_lines, s),
                             "excerpt": s[max(0, m.start() - 20):m.end() + 20],
                             "detail": "bare containment denial in a normative string while the same "
                                       "document asserts the containment chain"})
    return findings, mentions


# ---------------------------------------------------------------- WCC / SCC checks

def wcc_checks(doc, raw_lines):
    checks, findings = [], []
    conc = doc.get("conclusion") or {}
    comp = doc.get("class_components") or {}

    def add(cid, ok, detail):
        checks.append({"id": cid, "ok": bool(ok), "detail": detail})

    ct, fam = conc.get("conclusion_type"), conc.get("family")
    add("W1", ct == "weak_cosmic_censorship" and fam == "WCC"
        and comp.get("censorship") == "WCC" and str(comp.get("regularity_token")) in ("none", ""),
        f"conclusion_type={ct!r} family={fam!r} components={comp!r}")
    if not checks[-1]["ok"]:
        findings.append({"id": "W1", "defect": "D3", "severity": "blocking",
                         "path": "conclusion", "line": find_line(raw_lines, "conclusion_type"),
                         "detail": f"WCC conclusion identity broken: {ct!r}/{fam!r}/{comp!r}"})

    ip, vis, sf = doc.get("i_plus") or {}, doc.get("visibility") or {}, str(conc.get("statement_formal", ""))
    w2 = (ip.get("role") == "conclusion" and ip.get("in_conclusion") is True
          and vis.get("role") == "conclusion" and vis.get("in_conclusion") is True
          and "complete(I+_D)" in sf and "visible_singularity_from_I_plus" in sf)
    add("W2", w2, f"i_plus.role={ip.get('role')!r} i_plus.in_conclusion={ip.get('in_conclusion')!r} "
                  f"visibility.role={vis.get('role')!r} visibility.in_conclusion={vis.get('in_conclusion')!r}")
    if not w2:
        findings.append({"id": "W2", "defect": "D3", "severity": "blocking",
                         "path": "i_plus/visibility", "line": find_line(raw_lines, "role: conclusion"),
                         "detail": "WCC conclusion predicates are not both in the conclusion role"})

    fs = " ".join(map(str, conc.get("forbidden_strengthenings") or []))
    fw = " ".join(map(str, conc.get("forbidden_weakenings") or []))
    anti = doc.get("anti_scope") or {}
    antis = json.dumps(anti, ensure_ascii=False)
    w3 = (("C2" in fs or "C0" in fs) and "inextendib" in fs.lower()
          and "inextendib" not in fw.lower()
          and "AF-SCC-C2-VAC-GEN" in antis and "AF-SCC-C0-VAC-GEN" in antis)
    add("W3", w3, f"SCC content in forbidden_strengthenings={'inextendib' in fs.lower()}, "
                  f"in forbidden_weakenings={'inextendib' in fw.lower()}, anti_scope lists both SCC classes="
                  f"{'AF-SCC-C2-VAC-GEN' in antis and 'AF-SCC-C0-VAC-GEN' in antis}")
    if not w3:
        findings.append({"id": "W3", "defect": "D3", "severity": "blocking",
                         "path": "conclusion/anti_scope",
                         "line": find_line(raw_lines, "forbidden_weakenings"),
                         "detail": "SCC content is missing from the forbidden-strengthening set, present in "
                                   "the weakening set, or a sibling class is missing from anti_scope"})

    comp_hits = []
    for path, s in walk_strings(doc):
        for m in COMPOSITE.finditer(s):
            comp_hits.append((".".join(path), find_line(raw_lines, s), m.group(0), in_mention_path(path)))
    bad = [h for h in comp_hits if not h[3]]
    add("W5", not bad, f"composite 'C0 or C2' occurrences={len(comp_hits)}, outside mention containers={len(bad)}")
    if bad:
        findings.append({"id": "W5", "defect": "D3", "severity": "blocking",
                         "path": bad[0][0], "line": bad[0][1], "excerpt": bad[0][2],
                         "detail": "composite regularity asserted outside a mention container"})

    leak = []
    for path, s in walk_strings(doc):
        if in_mention_path(path) or not SCC_INEXT.search(s):
            continue
        if re.search(r"\b(no|not|never|forbid|fail)\b", s, re.I):
            continue
        leak.append((".".join(path), find_line(raw_lines, s), s[:140]))
    add("W6", not leak, f"SCC conclusion tokens in assertion paths outside mention containers={len(leak)}")
    if leak:
        findings.append({"id": "W6", "defect": "D3", "severity": "blocking",
                         "path": leak[0][0], "line": leak[0][1], "excerpt": leak[0][2],
                         "detail": "SCC conclusion content asserted from a WCC assertion path"})
    return checks, findings


def scc_checks(doc, raw_lines):
    checks, findings = [], []
    comp = doc.get("class_components") or {}
    conc = doc.get("conclusion") or {}
    reg = doc.get("regularity") or {}
    tok = norm_token(str(comp.get("regularity_token") or ""))

    def add(cid, ok, detail):
        checks.append({"id": cid, "ok": bool(ok), "detail": detail})

    ct, fam, ext = conc.get("conclusion_type"), conc.get("family"), norm_token(str(reg.get("extension_regularity") or ""))
    w1 = (tok in RANK and ext == tok and fam == "SCC"
          and ct == f"scc_{(tok or '').lower()}_future_inextendibility")
    add("S1", w1, f"components token={tok!r} extension_regularity={ext!r} conclusion_type={ct!r} family={fam!r}")
    if not w1:
        findings.append({"id": "S1", "defect": "D3", "severity": "blocking", "path": "conclusion/regularity",
                         "line": find_line(raw_lines, "conclusion_type"),
                         "detail": f"SCC conclusion identity broken: token={tok!r} ext={ext!r} ct={ct!r}"})

    ip, vis = doc.get("i_plus") or {}, doc.get("visibility") or {}
    sf = str(conc.get("statement_formal", ""))
    w2 = (vis.get("role") == "not_in_conclusion" and ip.get("in_conclusion") is False
          and "complete(I+" not in sf and "visible" not in sf)
    add("S2", w2, f"visibility.role={vis.get('role')!r} i_plus.in_conclusion={ip.get('in_conclusion')!r}")
    if not w2:
        findings.append({"id": "S2", "defect": "D3", "severity": "blocking", "path": "visibility/i_plus",
                         "line": find_line(raw_lines, "role: not_in_conclusion"),
                         "detail": "WCC visibility/I+ content appears in the SCC conclusion role"})

    sol = reg.get("extension_solution_concept")
    add("S3", bool(sol), f"extension_solution_concept={sol!r}")
    if not sol:
        findings.append({"id": "S3", "defect": "D3", "severity": "minor", "path": "regularity",
                         "line": find_line(raw_lines, "extension_solution_concept"),
                         "detail": "extension_solution_concept absent"})

    led = doc.get("implication_ledger") or {}
    chain = str(led.get("extension_class_containment") or "")
    chain_ok = len(E_TOKEN.findall(chain)) >= 2
    add("S4a", chain_ok, f"declared order field tokens={len(E_TOKEN.findall(chain))}")
    if not chain_ok:
        findings.append({"id": "S4a", "defect": "D4", "severity": "blocking",
                         "path": "implication_ledger.extension_class_containment",
                         "line": find_line(raw_lines, "extension_class_containment"),
                         "detail": "the declared extension-set order field is absent or carries no chain"})

    pair_findings = check_containment_pairs(doc, raw_lines)
    mismatches = [f for f in pair_findings if f["id"] == "S4-mismatch"]
    unranked = [f for f in pair_findings if f["id"] == "S4-unranked"]
    add("S4b", not mismatches, f"containment pairs checked; mismatches={len(mismatches)}, unranked-recorded={len(unranked)}")
    findings.extend(pair_findings)

    ledger_findings = check_ledger(doc, raw_lines)
    direction = [f for f in ledger_findings if f["id"].startswith("S5")]
    add("S5", not any(f["severity"] == "blocking" for f in direction),
        f"ledger direction findings={len(direction)}")
    findings.extend(ledger_findings)

    prem = check_premises(doc, raw_lines)
    add("S6", not prem, f"size/strength premise findings={len(prem)}")
    findings.extend(prem)

    den, mentions = check_denials(doc, raw_lines)
    add("S7", not den, f"bare containment denials={len(den)}; quoted/corrected mentions recorded={len(mentions)}")
    findings.extend(den)

    fs = " ".join(map(str, conc.get("forbidden_strengthenings") or []))
    fw = " ".join(map(str, conc.get("forbidden_weakenings") or []))
    s8_bad = []
    if re.search(r"two-sided\s+inextendibility", fw, re.I) and not is_corrected(fw):
        s8_bad.append("two-sided inextendibility listed in forbidden_weakenings without a correction marker")
    own_names = {"C0": ["C0", "C^0"], "C2": ["C2", "C^2"], "C11": ["C^{1,1}", "C^1,1"], "H2LOC": ["H2_loc", "H2LOC"]}
    for alias in own_names.get(tok, []):
        if re.search(rf"\b{re.escape(alias)}\b[^.]*\binextendib", fs, re.I) and "two-sided" not in fs.lower():
            s8_bad.append(f"the class's own token {alias} listed as a forbidden strengthening")
    add("S8", not s8_bad, f"strength-label findings={len(s8_bad)}")
    if s8_bad:
        findings.append({"id": "S8", "defect": "D3", "severity": "blocking",
                         "path": "conclusion.forbidden_strengthenings/weakenings",
                         "line": find_line(raw_lines, "forbidden_weakenings"),
                         "detail": "; ".join(s8_bad)})

    cross = str(led.get("cross_family") or "")
    wcc_row = any("WCC" in json.dumps(r, ensure_ascii=False) for r in (led.get("forbidden_transfers") or []))
    s9 = bool(cross) and wcc_row and ("no" in cross.lower() and "transfer" in cross.lower())
    add("S9", s9, f"cross_family={cross[:60]!r} wcc_row={wcc_row}")
    if not s9:
        findings.append({"id": "S9", "defect": "D3", "severity": "minor", "path": "implication_ledger.cross_family",
                         "line": find_line(raw_lines, "cross_family"),
                         "detail": "cross-family no-transfer statement or WCC forbidden row missing"})
    return checks, findings, mentions


def cross_document(f1, f2a, raw1, raw2):
    checks, findings = [], []
    c1, c2 = f1.get("conclusion") or {}, f2a.get("conclusion") or {}

    def add(cid, ok, detail):
        checks.append({"id": cid, "ok": bool(ok), "detail": detail})

    add("X1", c1.get("conclusion_type") != c2.get("conclusion_type"),
        f"F1={c1.get('conclusion_type')!r} F2a={c2.get('conclusion_type')!r}")
    a1, a2 = json.dumps(f1.get("anti_scope") or {}), json.dumps(f2a.get("anti_scope") or {})
    add("X2", "AF-SCC-C2-VAC-GEN" in a1 and "AF-WCC-VAC-GEN" in a2,
        f"F1 anti_scope names F2a={'AF-SCC-C2-VAC-GEN' in a1}; F2a anti_scope names F1={'AF-WCC-VAC-GEN' in a2}")
    sf1, sf2 = str(c1.get("statement_formal", "")), str(c2.get("statement_formal", ""))
    add("X3", ("inextendib" not in sf1.lower()) and ("visible" not in sf2.lower()),
        "neither formal conclusion asserts the other family's predicate")
    for cid, ok, detail, path, line in [
        ("X1", checks[0]["ok"], checks[0]["detail"], "conclusion", None),
        ("X2", checks[1]["ok"], checks[1]["detail"], "anti_scope", None),
        ("X3", checks[2]["ok"], checks[2]["detail"], "conclusion.statement_formal", None),
    ]:
        if not ok:
            findings.append({"id": cid, "defect": "D3", "severity": "blocking", "path": path,
                             "line": line, "detail": detail})
    return checks, findings


# ---------------------------------------------------------------- run on a doc

def run_role(role, path: Path):
    raw = path.read_text()
    raw_lines = raw.splitlines()
    doc = yaml.safe_load(raw)
    h = sha256_file(path)
    if role == "wcc":
        checks, findings = wcc_checks(doc, raw_lines)
        mentions = []
    elif role == "scc":
        checks, findings, mentions = scc_checks(doc, raw_lines)
    else:
        raise ValueError(role)
    notes = [f for f in findings if f.get("severity") == "info"]
    findings = [f for f in findings if f.get("severity") != "info"]
    return {"role": role, "path": str(path.relative_to(ROOT)), "sha256": h,
            "checks": checks, "findings": findings, "notes": notes, "mentions": mentions,
            "failed_checks": [c["id"] for c in checks if not c["ok"]]}


def mutate(base_text: str, spec: dict) -> str:
    """Apply count-controlled literal replacements, optional whole-line replacements, append."""
    text = base_text
    for old, new, count in spec.get("replace", []):
        if old not in text:
            raise SystemExit(f"control {spec['id']}: anchor not found: {old[:60]!r}")
        text = text.replace(old, new, count)
    for prefix, new_line, count in spec.get("replace_lines", []):
        lines = text.splitlines(keepends=True)
        hits = 0
        for i, line in enumerate(lines):
            if hits >= count:
                break
            if line.startswith(prefix):
                lines[i] = new_line + ("\n" if line.endswith("\n") else "")
                hits += 1
        if hits == 0:
            raise SystemExit(f"control {spec['id']}: line anchor not found: {prefix[:60]!r}")
        text = "".join(lines)
    if spec.get("append"):
        text = text + spec["append"]
    return text


CONTROLS = [
    {"id": "M0-f1-null", "base": "F1", "append": "\n# null control: no semantic change\n", "expect": []},
    {"id": "M1-f1-conclusion-token", "base": "F1", "expect": ["W1"],
     "replace": [("conclusion_type: weak_cosmic_censorship", "conclusion_type: scc_c2_future_inextendibility", 1)]},
    {"id": "M2-f1-scc-as-weakening", "base": "F1", "expect": ["W3"],
     "replace": [('    - "dropping I+ completeness"',
                  '    - "dropping I+ completeness"\n    - "C2 or C0 inextendibility of the maximal development"', 1)]},
    {"id": "M3-f1-iplus-role", "base": "F1", "expect": ["W2"],
     "replace": [("  role: conclusion\n  in_conclusion: true", "  role: assumption\n  in_conclusion: false", 1)]},
    {"id": "M4-f1-composite-asserted", "base": "F1", "expect": ["W5"],
     "replace": [("scope_statement: >\n", "scope_statement: >\n  C0 or C2 composite regularity.\n", 1)]},
    {"id": "M5-f2a-chain-inverted", "base": "F2a", "expect": ["S4"],
     "replace": [("E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0",
                  "E_C0 subset of E_H2loc subset of E_{C^1,1} subset of E_C2", 1)]},
    {"id": "M6-f2a-bare-denial", "base": "F2a", "expect": ["S7"],
     "replace": [('    - "C^{1,1} and H2_loc are DIFFERENT classes',
                  '    - "No containment with C0 is asserted here. C^{1,1} and H2_loc are DIFFERENT classes', 1)]},
    {"id": "M7-f2a-entailment-swapped", "base": "F2a", "expect": ["S5"],
     "replace": [('- {from: "no proper future C0 extension", to: "no proper future C2 extension", relation: entails,',
                  '- {from: "no proper future C2 extension", to: "no proper future C0 extension", relation: entails,', 1)]},
    {"id": "M8-f2a-inverted-premise", "base": "F2a", "expect": ["S6"],
     "replace": [('reason: "the converse containment is false"',
                  'reason: "C0 is a strictly smaller extension class than C2, so the transfer is licensed"', 1)]},
    {"id": "M9-f2a-chain-field-removed", "base": "F2a", "expect": ["S4"],
     "replace_lines": [('  extension_class_containment: "E_C2 subset of E_{C^1,1}',
                        '  extension_class_containment: "REMOVED-FOR-CONTROL"', 1)]},
    {"id": "M10-f2a-visibility-conclusion", "base": "F2a", "expect": ["S2"],
     "replace": [("visibility:\n  role: not_in_conclusion", "visibility:\n  role: conclusion", 1)]},
    {"id": "M11-f2a-null", "base": "F2a", "append": "\n# null control: no semantic change\n", "expect": []},
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT / "report.json"))
    args = ap.parse_args()

    started = now()
    before = {p: {"sha256": sha256_file(ROOT / p), "mtime": (ROOT / p).stat().st_mtime} for p in PINS}
    pin_rows = {p: {"declared": h, "measured": before[p]["sha256"], "match": before[p]["sha256"] == h}
                for p, h in PINS.items()}
    mirror_rows = {}
    for canon, mirror in MIRRORS.items():
        a, b = sha256_file(ROOT / canon), sha256_file(ROOT / mirror)
        mirror_rows[canon] = {"mirror": mirror, "canonical_sha256": a, "mirror_sha256": b, "byte_identical": a == b}

    f1 = run_role("wcc", ROOT / "schemas/af_wcc_vacuum.yaml")
    f2a = run_role("scc", ROOT / "schemas/af_scc_c2_vacuum.yaml")
    f2b = run_role("scc", ROOT / "schemas/af_scc_c0_vacuum.yaml")
    xchecks, xfindings = cross_document(yaml.safe_load((ROOT / "schemas/af_wcc_vacuum.yaml").read_text()),
                                        yaml.safe_load((ROOT / "schemas/af_scc_c2_vacuum.yaml").read_text()),
                                        None, None)

    # control battery: derive mutants from pinned live bytes, run only inside OUT
    ctrl_dir = OUT / "controls"
    ctrl_dir.mkdir(exist_ok=True)
    bases = {"F1": (ROOT / "schemas/af_wcc_vacuum.yaml").read_text(),
             "F2a": (ROOT / "schemas/af_scc_c2_vacuum.yaml").read_text()}
    base_findings = {"F1": [f["id"] for f in f1["findings"]], "F2a": [f["id"] for f in f2a["findings"]]}
    base_failed = {"F1": f1["failed_checks"], "F2a": f2a["failed_checks"]}
    ctrl_rows, ctrl_all_ok = [], True
    for spec in CONTROLS:
        base = spec["base"]
        text = mutate(bases[base], spec)
        cpath = ctrl_dir / f"{spec['id']}.yaml"
        cpath.write_text(text)
        role = "wcc" if base == "F1" else "scc"
        res = run_role(role, cpath)
        failed = res["failed_checks"]
        expect = spec.get("expect") or []
        if expect:
            ok = all(any(f == e or f.startswith(e) for f in failed) for e in expect)
        else:
            ok = sorted(failed) == sorted(base_failed[base])
        ctrl_all_ok = ctrl_all_ok and ok
        ctrl_rows.append({"id": spec["id"], "base": base, "mutation": spec.get("replace", []),
                          "append": spec.get("append"), "expected_failed": expect,
                          "actual_failed": failed, "ok": ok,
                          "findings": [f["id"] for f in res["findings"]]})

    gate_runs = {}
    for label, rel in [("F1", "schemas/af_wcc_vacuum.yaml"), ("F2a", "schemas/af_scc_c2_vacuum.yaml")]:
        cp = subprocess.run([sys.executable, "artifacts/formulation/tools/check_class_schema.py",
                             "--json", rel], cwd=ROOT, capture_output=True, text=True)
        gate_runs[label] = {"cmd": f"check_class_schema.py --json {rel}", "returncode": cp.returncode,
                            "stdout": cp.stdout.strip()[:2000], "stderr": cp.stderr.strip()[:500]}

    after = {p: {"sha256": sha256_file(ROOT / p), "mtime": (ROOT / p).stat().st_mtime} for p in PINS}
    hash_stable = all(before[p]["sha256"] == after[p]["sha256"] and before[p]["mtime"] == after[p]["mtime"] for p in PINS)

    target_findings = f1["findings"] + f2a["findings"]
    blocking = [f for f in target_findings if f["severity"] == "blocking"]
    real_ctrl_ok = any(f["defect"] == "D1" for f in f2b["findings"]) and any(f["defect"] == "D2" for f in f2b["findings"])
    pins_ok = all(r["match"] for r in pin_rows.values())
    if not pins_ok or not hash_stable:
        verdict, score = "inconclusive", 0.0
    elif blocking:
        verdict, score = "revise", 3.0
    elif real_ctrl_ok and ctrl_all_ok:
        verdict, score = "accept", 4.0
    else:
        verdict, score = "revise", 3.0

    report = {
        "schema": "worker-028/internal-consistency/v1",
        "task_id": "W028-F1F2A-INTERNAL-CONSISTENCY-01",
        "actor": "worker-028",
        "created_at": now(),
        "started_at": started,
        "root": str(ROOT),
        "poset": {"order": ["C2", "C11", "H2LOC", "C0"], "rank": RANK,
                  "meaning": "E_C2 subset E_C11 subset E_H2LOC subset E_C0; larger rank = larger extension set = stronger inexistence statement"},
        "pins": pin_rows,
        "mirrors": mirror_rows,
        "runs": {"F1": f1, "F2a": f2a, "K-real-f2b": f2b},
        "cross_document": {"checks": xchecks, "findings": xfindings},
        "controls": {"all_ok": ctrl_all_ok, "rows": ctrl_rows,
                     "base_failed_checks": base_failed, "base_findings": base_findings},
        "gate_runs": gate_runs,
        "hash_stability": {"before": before, "after": after, "unchanged": hash_stable},
        "verdict": {
            "target": verdict, "score": score,
            "counts_as_full_schema_verdict": False,
            "verdict_scope": "cross-field internal consistency classes D1-D5 at the pinned F1/F2a bytes only; "
                             "not a full-schema review, not a gate verdict, not a node status, not review coverage",
            "real_positive_control_fired": real_ctrl_ok,
            "controls_all_ok": ctrl_all_ok,
            "out_of_scope": ["full-schema conformance", "filed F2a blocking item HF-028R-01 (extension category unpinned)",
                             "F2b repair adjudication", "gate verdicts and node states"],
        },
        "falsifier": ("Re-run check_f1f2a_internal.py at the same pins: falsified if any pin moved; if F1 or F2a "
                      "yields a D1-D5 finding; if the F2b real control stops reporting a bare denial and an inverted "
                      "size premise; if any planted control does not fail its declared check id (or a null control "
                      "adds a finding); if canonical hashes or mtimes change across the run."),
    }
    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=1))
    print(json.dumps({"verdict": verdict, "score": score,
                      "F1_findings": [f["id"] for f in f1["findings"]],
                      "F2a_findings": [f["id"] for f in f2a["findings"]],
                      "f2b_control": [f["id"] for f in f2b["findings"]],
                      "controls_all_ok": ctrl_all_ok, "real_control_ok": real_ctrl_ok,
                      "hash_stable": hash_stable, "gate_rc": {k: v["returncode"] for k, v in gate_runs.items()}},
                     ensure_ascii=False))
    return 0 if verdict != "inconclusive" else 2


if __name__ == "__main__":
    sys.exit(main())
